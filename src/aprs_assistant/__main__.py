# SPDX-FileCopyrightText: 2024-present Adam Fourney <adam.fourney@gmail.com>
#
# SPDX-License-Identifier: MIT
import sys
import json
from ._bot import generate_reply
from ._bing import bing_search

fromcall = sys.argv[1]
while True:
    request = input(f"{fromcall}: ").strip()
    if len(request) == 0:
        continue
    if request == "quit" or request == "exit":
        break
    response = generate_reply(fromcall, request)
    print(f"\nAPNGIX: {response}\n")
