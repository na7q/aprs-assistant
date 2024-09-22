# SPDX-FileCopyrightText: 2024-present Adam Fourney <adam.fourney@gmail.com>
#
# SPDX-License-Identifier: MIT
import os
import json
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from openai import AzureOpenAI, OpenAI

_oai_client = None

def gpt(messages, model="gpt-4o-2024-08-06", json_mode=False, **kwargs):
    global _oai_client

    if _oai_client is None:
        _oai_client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

    kwargs["model"] = model
    kwargs["messages"] = messages

    if json_mode == False:
        response = _oai_client.chat.completions.create(**kwargs)
        return response.choices[0].message.content
    else:
        kwargs["response_format"] = {"type": "json_object"}
        response = _oai_client.chat.completions.create(**kwargs)
        return json.loads(response.choices[0].message.content)
