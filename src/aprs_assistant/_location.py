# SPDX-FileCopyrightText: 2024-present Adam Fourney <adam.fourney@gmail.com>
#
# SPDX-License-Identifier: MIT
import requests
import json
import os
import maidenhead

from ._cache import read_cache, write_cache
from ._constants import SECONDS_IN_MINUTE, SECONDS_IN_WEEK

def get_position(callsign):
    aprsfi_data = aprsfi_get_position(callsign)

    if aprsfi_data is None:
        return None

    lat = float(aprsfi_data["lat"])
    lon = float(aprsfi_data["lng"])

    location_data = reverse_location(lat, lon)

    result = { 
        "latitude": lat,
        "longitude": lon,
        "maidenhead_gridsquare": maidenhead.to_maiden(lat, lon, 4)
    }

    if "speed" in aprsfi_data:
        result["speed_in_kph"] = int(aprsfi_data["speed"])
    if "altitude" in aprsfi_data:
        result["altitude_in_meters"] = int(aprsfi_data["altitude"])
    if "course" in aprsfi_data:
        result["heading_in_degrees"] = int(aprsfi_data["course"])

    if "name" in location_data and len(location_data["name"]) > 0:
        result["name"] = location_data["name"]
    if "display_name" in location_data and len(location_data["display_name"]) > 0:
        result["description"] = location_data["display_name"]
    if "address" in location_data:
        result["address"] = location_data["address"]

    types = list()
    if "category" in location_data:
        types.append(location_data["category"])
    if "address_type" in location_data:
        types.append(location_data["address_type"])
    if "type" in location_data:
        types.append(location_data["type"])
    types = list(set(types))

    if len(types) > 0:
        result["category"] = ", ".join(types)

    return result


def aprsfi_get_position(callsign):
    cache_key = f"aprsfi_get_position:{callsign}"
    cached_data = read_cache(cache_key)
    if cached_data is not None:
        return cached_data
    else:
        data = _aprsfi_get_position(callsign)
        write_cache(cache_key, data, expires_in=SECONDS_IN_MINUTE*5)
        return data


def _aprsfi_get_position(callsign):
    api_key = os.environ.get("APRSFI_API_KEY", "").strip()
    if api_key == "":
        return None
    
    headers = { "User-Agent": "aprsd_gpt_plugin" }
    response = requests.get(
        f"https://api.aprs.fi/api/get?name={callsign}&what=loc&apikey={api_key}&format=json",
        headers=headers,
        stream=False
    )
    response.raise_for_status()
    response_data = response.json()

    if response_data.get("result") == "ok" and len(response_data["entries"]) > 0:
        return response_data["entries"][0]

    return None


def reverse_location(lat, lon):
    cache_key = f"reverse_location:{lat}:{lon}"
    cached_data = read_cache(cache_key)
    if cached_data is not None:
        return cached_data
    else:
        data = _reverse_location(lat, lon)
        write_cache(cache_key, data, expires_in=2*SECONDS_IN_WEEK)
        return data


def _reverse_location(lat, lon):
    headers = { "User-Agent": "aprsd_gpt_plugin" }
    response = requests.get(
        f"https://nominatim.openstreetmap.org/reverse?lat={lat}&lon={lon}&format=jsonv2",
        headers=headers,
        stream=False
    )
    response.raise_for_status()
    return response.json()
