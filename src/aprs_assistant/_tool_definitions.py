TOOL_WEB_SEARCH = {
    "type": "function",
    "function": {
        "name": "web_search",
        "description": "Perform a Bing web search. Useful when answering most user questions.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The web search query to use.",
                },
            },
            "required": ["query"],
        },
    },
}

TOOL_BAND_CONDITIONS = {
    "type": "function",
    "function": {
        "name": "radio_band_conditions",
        "description": "Lookup the latest HF and VHF band conditions, as well as other solar and space weather conditions that may impact radio operations.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
}
