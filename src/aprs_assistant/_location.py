# SPDX-FileCopyrightText: 2024-present Adam Fourney <adam.fourney@gmail.com>
#
# SPDX-License-Identifier: MIT
import requests
import json
import os
import re
import maidenhead
from urllib.parse import urlencode

from ._cache import read_cache, write_cache
from ._constants import USER_AGENT, SECONDS_IN_MINUTE, SECONDS_IN_WEEK


def get_position(callsign):
    positions = aprsfi_get_positions(aprsfi_get_targets(callsign))

    if positions is None or len(positions) == 0:
        return None

    # Get the latest position
    latest_position = positions[0]
    for i in range(1, len(positions)):
        if float(positions[i]["lasttime"]) > float(latest_position["lasttime"]):
            latest_position = positions[i]

    lat = float(latest_position["lat"])
    lon = float(latest_position["lng"])

    location_data = reverse_geocode(lat, lon)

    result = {
        "latitude": lat,
        "longitude": lon,
        "maidenhead_gridsquare": maidenhead.to_maiden(lat, lon, 4),
    }

    if "speed" in latest_position:
        result["speed_in_kph"] = float(latest_position["speed"])
    if "altitude" in latest_position:
        result["altitude_in_meters"] = float(latest_position["altitude"])
    if "course" in latest_position:
        result["heading_in_degrees"] = float(latest_position["course"])

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


def aprsfi_get_targets(callsign):
    # No disambiguation for now
    return [callsign]


def aprsfi_get_positions(callsigns):
    """
    Get the latest position of one or more callsigns.
    """
    assert isinstance(callsigns, list)

    cache_key = f"aprsfi_get_position:{','.join(callsigns)}"
    cached_data = read_cache(cache_key)
    if cached_data is not None:
        return cached_data
    else:
        data = _aprsfi_get_positions(callsigns)
        write_cache(cache_key, data, expires_in=SECONDS_IN_MINUTE * 5)
        return data


def _aprsfi_get_positions(callsigns):
    assert isinstance(callsigns, list)

    api_key = os.environ.get("APRSFI_API_KEY", "").strip()
    if api_key == "":
        return None

    headers = {"User-Agent": USER_AGENT}
    response = requests.get(
        f"https://api.aprs.fi/api/get?name={','.join(callsigns)}&what=loc&apikey={api_key}&format=json",
        headers=headers,
        stream=False,
    )
    response.raise_for_status()
    response_data = response.json()

    if response_data.get("result") == "ok":
        return response_data["entries"]

    return None


def reverse_geocode(lat, lon):
    cache_key = f"reverse_geocode:{lat}:{lon}"
    cached_data = read_cache(cache_key)
    if cached_data is not None:
        return cached_data
    else:
        data = _reverse_geocode(lat, lon)
        write_cache(cache_key, data, expires_in=2 * SECONDS_IN_WEEK)
        return data


def _reverse_geocode(lat, lon):
    headers = {"User-Agent": USER_AGENT}
    response = requests.get(
        f"https://nominatim.openstreetmap.org/reverse?lat={lat}&lon={lon}&format=jsonv2",
        headers=headers,
        stream=False,
    )
    response.raise_for_status()
    return response.json()


def geocode(
    query=None, street=None, city=None, state=None, country=None, postalcode=None
):
    # Non-empty query
    if query is not None and len(query.strip()) > 0:
        result = _geocode(query=query)
        if result is not None:
            return result

    # Try with everything
    result = _geocode(
        street=street, city=city, state=state, country=country, postalcode=postalcode
    )
    if result is not None:
        return result

    # Try without the city -- it can sometimes be wrong
    result = _geocode(
        street=street, state=state, country=country, postalcode=postalcode
    )
    if result is not None:
        return result

    # If we have a zipcode, just use that at this point
    result = _geocode(country=country, postalcode=postalcode)
    if result is not None:
        return result

    # Just query it
    new_query = (
        ("" if city is None else city)
        + " "
        + ("" if state is None else state)
        + " "
        + ("" if country is None else country)
    )
    new_query = re.sub(r"\s+", " ", new_query).strip()

    result = _geocode(query=new_query)
    if result is not None:
        return result


def _geocode(
    query=None, street=None, city=None, state=None, country=None, postalcode=None
):
    cache_key = f"_geocode:{query}:{street}:{city}:{state}:{country}:{postalcode}"
    cached_data = read_cache(cache_key)
    if cached_data is not None:
        return cached_data
    else:
        data = _geocode_attempt(
            query=query,
            street=street,
            city=city,
            state=state,
            country=country,
            postalcode=postalcode,
        )
        write_cache(cache_key, data, expires_in=52 * SECONDS_IN_WEEK)
        return data


def _geocode_attempt(
    query=None, street=None, city=None, state=None, country=None, postalcode=None
):
    args = {}
    if street:
        args["street"] = street.strip()
    if city:
        args["city"] = city.strip()
    if state:
        args["state"] = state.strip()
    if country:
        args["country"] = country.strip()
    if postalcode:
        args["postalcode"] = postalcode.strip()

    if query is not None and len(args) > 0:
        raise ValueError("geocode() cannot be given both a query and an address")

    if query:
        args["q"] = query.strip()

    if len(args) == 0:
        return None

    headers = {"User-Agent": USER_AGENT}
    response = requests.get(
        "https://nominatim.openstreetmap.org/search.php?format=jsonv2&"
        + urlencode(args),
        headers=headers,
        stream=False,
    )

    response.raise_for_status()
    if response.text is None or response.text.strip() == "":
        return None

    response_json = json.loads(response.text)
    if isinstance(response_json, list) and len(response_json) > 0:
        return response_json[0]
    else:  # Return None rather than empty lists or dictionaries
        return None
