# APRS Assistant

[![PyPI - Version](https://img.shields.io/pypi/v/aprs-assistant.svg)](https://pypi.org/project/aprs-assistant)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/aprs-assistant.svg)](https://pypi.org/project/aprs-assistant)

An LLM-based assistant for the Automatic Packet Reporting System (APRS).

#### Note: This library provides core functionality for an LLM-based APRS chatbot, but does not itself directly handle APRS messaging (RX, or TX). For this, a library like [apsd](https://github.com/craigerl/aprsd) is needed. Instructions for connecting the assistant to the APRS network are forthcoming in a future update.

-----

## Installation

```console
pip install aprs-assistant
```

## API Keys
At a minimum, this library requires setting an OpenAI API key. Bing and APRS.fi API keys are also used to support various tools and services. Set the, as environment variable in bash, as follows:

```console
export OPENAI_API_KEY=<YOUR_KEY>
export BING_API_KEY=<YOUR_KEY>
export APRSFI_API_KEY=<YOUR_KEY>
```

## Running Local Chat
The library supports local chats (e.g., for debugging) as follows:

```console
python -m aprs-assistant <YOUR_CALLSIGN>
```

Type `exit` or press `Ctrl-D` to exit.


## Integration
To integrate `aprs-assistant` into your application, simply use:

```
from aprs_assistant import generate_reply

sender_callsign = "NOCALL"
message = "What's the weather?"
response = generate_reply(sender_callsign, message)

print(response)
```

Note: `response` can be None


## License

`aprs-assistant` is distributed under the terms of the [MIT](https://spdx.org/licenses/MIT.html) license.
