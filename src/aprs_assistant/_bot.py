# SPDX-FileCopyrightText: 2024-present Adam Fourney <adam.fourney@gmail.com>
#
# SPDX-License-Identifier: MIT
import re
import os
import sys
import time
import hashlib
import json
import datetime

from ._constants import CHATS_DIR, LABELED_DIR, SESSION_TIMEOUT
from ._gpt import gpt
from ._location import get_position
from ._bing import bing_search
from ._bandcond import get_band_conditions
from ._weather import get_weather

from ._tool_definitions import (
    TOOL_WEB_SEARCH,
    TOOL_USER_WEATHER,
    TOOL_BAND_CONDITIONS,
)

MAX_MESSAGES = 20

def generate_reply(fromcall, message):

    message = message.strip()
    if len(message) == 0:
        return "..."

    # Meta-commands
    if message.lower() in ["r", "c", "clr", "reset", "clear"]:
        _reset_chat_history(fromcall)
        return "Chat cleared."

    if message.lower() in ["good bot", "gb"]:
        _apply_label(fromcall, "good")
        return "Chat labeled as good."

    if message.lower() in ["bad bot", "bb"]:
        _apply_label(fromcall, "bad")
        return "Chat labeled as bad."

    # Chat
    messages = _load_chat_history(fromcall)
    messages.append({ "role": "user", "content": message })
    response = _generate_reply(fromcall, messages)
    messages.append({ "role": "assistant", "content": response })
    _save_chat_history(fromcall, messages)
    return response


def _generate_reply(fromcall, messages):

    # Truncate the chat history
    inner_messages = [ m for m in messages ] # clone
    if len(inner_messages) > MAX_MESSAGES:
        inner_messages = inner_messages[-1*MAX_MESSAGES:] 

    # Generate the system message
    dts = datetime.datetime.now()

    position = get_position(fromcall)
    position_str = ""
    if position is not None:
        position_str = " Their last known position is:\n\n" + json.dumps(position, indent=4)

    system_message = {
        "role": "system", 
        "content": f"""You are an AI HAM radio operator, with call sign APNGIX. You were created by KK7CMT. You are at home, in your cozy ham shack, monitoring the gobal APRS network. You have a computer and high-speed access to the internet. You and answering questions from other human operators in the field who lack an internet connection. To this end, you are relaying vital information. Questions can be about anything -- not just HAM radio.  You are familiar with HAM conventions and shorthands like QSO, CQ, and 73. The current date and time is {dts}. In all interactions, following US FCC guidelines, you will refrain from using profane or obscene language and avoid expressing overtly political commentary or opinion (reporting news is fine).

At present, you are exchanging messages with the owner of callsign {fromcall}.{position_str}
""",
    }
    inner_messages.insert(0, system_message)

    # Begin answering the question
    message = inner_messages.pop()["content"]
    print(f"Message: {message}") 

    # Let's guess the intent
    inner_messages.append({"role": "user", "content": f"{fromcall} wrote \"{message}\". What are they likely asking?"})
    response = gpt(inner_messages)
    print(response.content)
    inner_messages.append(response)

    # Determine if it can be answered directly or if we should search
    tools = [TOOL_BAND_CONDITIONS]

    # API key needed for web search
    if len(os.environ.get("BING_API_KEY", "").strip()) > 0:
        tools.append(TOOL_WEB_SEARCH)
    
    # Some tools only become available when we have a position
    if position is not None:
        tools.append(TOOL_USER_WEATHER)

    inner_messages.append({ "role": "user", "content": f"Based on this, invoke any tools or functions that might be helpful to answer {fromcall}'s question OR just answer directly (e.g., if it's just chit-chat)" })
    response = gpt(
        inner_messages,
        tools=tools,
    )
    inner_messages.append(response)

    # Handle any tool call results
    if response.tool_calls:
        for tool_call in response.tool_calls:
            function_name = tool_call.function.name
            args = json.loads(tool_call.function.arguments)
            print(f"Calling: {function_name}")

            # Step 3: Call the function and retrieve results. Append the results to the messages list.
            if function_name == TOOL_WEB_SEARCH["function"]["name"]:
                results = bing_search(args["query"])
            elif function_name == TOOL_BAND_CONDITIONS["function"]["name"]:
                results = get_band_conditions()
            elif function_name == TOOL_USER_WEATHER["function"]["name"]:
                country_code = position.get("address", {}).get("country_code", "")
                results = get_weather(lat=position["latitude"], lon=position["longitude"], metric=False if country_code == "us" else True)
            else:
                results = f"Unknown function: {function_name}"

            print(f"Results:\n{results}")

            inner_messages.append({
                "role":"tool",
                "tool_call_id":tool_call.id,
                "name": tool_call.function.name,
                "content": results
            })

    inner_messages.append({ "role": "user", "content": f"Given these results, write an answer to {fromcall}'s original question \"{message}\", exactly as you would write it to them, verbatim. Your response must be as helpful and succinct as possible; at most 10 words can be sent in an APRS response. Remember, {fromcall} does not have access to the internet -- that's why they are using APRS. So do not direct them to websites, and instead convey the most important information directly."})
    reply = gpt(inner_messages).content

    if len(reply) > 70: 
        reply = reply[0:70]

    return reply.rstrip()

def _load_chat_history(callsign):
    fname = _get_chat_file(callsign)
    if os.path.isfile(fname):
        with open(fname, "rt") as fh:
            history = json.loads(fh.read())

            # Check for timeouts
            if history["time"] + SESSION_TIMEOUT < time.time():
                print(f"{callsign}'s session timed out. Starting new session.")
                _reset_chat_history(callsign)
                return []
            else:
                return history["messages"]
    else:
        print(f"{callsign}'s history is empty. Starting new session.")
        return []


def _save_chat_history(callsign, messages):
    os.makedirs(CHATS_DIR, exist_ok=True)
    fname = _get_chat_file(callsign)
    with open(fname, "wt") as fh:
        fh.write(json.dumps({ 
            "version": 1,
            "callsign": callsign,
            "time": time.time(),
            "messages": messages, 
        }, indent=4))


def _get_chat_file(callsign):
    m = re.search(r"^[A-Za-z0-9\-]+$", callsign)
    if m:
        return os.path.join(CHATS_DIR, callsign + ".json")
    else:
        callhash = hashlib.md5(callsign.encode()).hexdigest().lower()
        return os.path.join(CHATS_DIR, callhash + ".json")


def _reset_chat_history(callsign):
    fname = _get_chat_file(callsign)
    if os.path.isfile(fname):
        newname = fname + "." + str(int(time.time() * 1000))
        os.rename(fname, newname)


def _apply_label(callsign, label):
    fname = _get_chat_file(callsign)
    if os.path.isfile(fname):
        os.makedirs(LABELED_DIR, exist_ok=True)

        # Read the chat file (for copying)
        with open(fname, "rt") as fh:
            text = fh.read()

        # Create a unique filename for the labeled chat
        text_hash = hashlib.md5(text.encode()).hexdigest().lower()
        labeled_fname = label + "__" + text_hash + ".json"
        labeled_fname = os.path.join(LABELED_DIR, labeled_fname)

        # Copy to the the labeled chat file
        with open(labeled_fname, "wt") as fh:
            fh.write(text)
