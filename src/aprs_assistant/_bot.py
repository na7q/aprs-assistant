# SPDX-FileCopyrightText: 2024-present Adam Fourney <adam.fourney@gmail.com>
#
# SPDX-License-Identifier: MIT
import re
import os
import time
import hashlib
import json
import datetime

from ._constants import CHATS_DIR
from ._gpt import gpt
from ._location import get_position
from ._bing import bing_search

MAX_MESSAGES = 20

def generate_reply(fromcall, message):

    message = message.strip()
    if len(message) == 0:
        return "..."

    if message.lower() in ["reset", "clear"]:
        _reset_chat_history(fromcall)
        return "Chat cleared."

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
    print(response)
    inner_messages.append({"role": "assistant", "content": response})

    # Determine if it can be answered directly or if we should search
    inner_messages.append({ "role": "user", "content": "Based on this, could you answer directly, or would you want to search the web for information first? Most question benefit from search (even if just to verify). Only chit-chat or general knowledge should be answered directly. Answer either 'DIRECT' or 'SEARCH'" })
    response = gpt(inner_messages)
    print(response)
    inner_messages.append({"role": "assistant", "content": response})

    # Search if needed, otherwise answer directly
    reply = "..."
    if "SEARCH" in response:
        inner_messages.append({ "role": "user", "content": "What one standalone query would you issue? Write your answer in perfect JSON, following this schema: { \"query\": QUERY, \"justification\": JUSTIFICATION }" }) 
        standalone_question = gpt(inner_messages, json_mode=True)["query"]
        print(f"Searching: {standalone_question}")
        results = bing_search(standalone_question)
        print(results)
        inner_messages.append({ "role": "user", "content": "Here are the results of that web search: " + results })
        inner_messages.append({ "role": "user", "content": f"Given these results, write an answer to {fromcall}'s original question \"{message}\", exactly as you would write it to them, verbatim. Your response must be as helpful and succinct as possible; at most 10 words can be sent in an APRS response. Remember, {fromcall} does not have access to the internet -- that's why they are using APRS. So do not direct them to websites, and instead convey the most important information directly."})
        reply = gpt(inner_messages)
    else:
        inner_messages.pop()
        inner_messages.pop()
        inner_messages.append({ "role": "user", "content": f"Given this intent, write an answer to {fromcall}'s original question \"{message}\", exactly as you would write it to them, verbatim. Your response must be as helpful and succinct as possible; at most 10 words can be sent in an APRS response. Remember, {fromcall} does not have access to the internet -- that's why they are using APRS. So do not direct them to websites, and instead convey the most important information directly."})
        reply = gpt(inner_messages)

    if len(reply) > 70: 
        reply = reply[0:70]

    return reply.rstrip()

def _load_chat_history(callsign):
    fname = _get_chat_file(callsign)
    if os.path.isfile(fname):
        with open(fname, "rt") as fh:
            return json.loads(fh.read())["messages"]
    else:
        return []


def _save_chat_history(callsign, messages):
    os.makedirs(CHATS_DIR, exist_ok=True)
    fname = _get_chat_file(callsign)
    with open(fname, "wt") as fh:
        fh.write(json.dumps({ "callsign": callsign, "time": time.time(), "messages": messages }, indent=4))


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
