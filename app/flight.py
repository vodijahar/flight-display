import re

from config import AIRLABS_URL
from geo import enrich_position
from net import get_json


def first(value, default=""):
    return value if value not in (None, "") else default


def compact(value):
    return str(value or "").strip().upper().replace(" ", "")


def flight_param(flight_number):
    value = compact(flight_number)
    if re.fullmatch(r"[A-Z]{3}\d+[A-Z]?", value):
        return "flight_icao", value
    return "flight_iata", value


def number(value):
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def integer(value):
    value = number(value)
    if value is None:
        return None
    return int(round(value))


def feet_from_meters(value):
    value = number(value)
    if value is None:
        return None
    return int(round(value * 3.28084))


def time_text(value):
    if not value:
        return "--:--"
    text = str(value)
    if len(text) >= 16 and text[4:5] == "-" and text[13:14] == ":":
        return text[11:16]
    return text[:5]


def status_text(data):
    status = compact(data.get("status")).replace("_", " ")
    if not status:
        return "UNKNOWN"
    return status


def delay_minutes(data):
    for key in ("arr_delayed", "dep_delayed", "delayed"):
        delay = integer(data.get(key))
        if delay is not None:
            return delay
    return None


def delay_text(delay):
    if delay is None:
        return "Delay --"
    if delay <= 0:
        return "On time"
    return f"Delay {delay}m"


def normalize_flight(data, requested_flight):
    lat = number(data.get("lat"))
    lon = number(data.get("lng"))
    speed_kmh = number(data.get("speed"))
    location = enrich_position(lat, lon)
    delay = delay_minutes(data)

    return {
        "flight_number": first(data.get("flight_iata"), requested_flight),
        "flight_icao": first(data.get("flight_icao"), ""),
        "status": status_text(data),
        "delay_minutes": delay,
        "delay_text": delay_text(delay),
        "departure_code": first(data.get("dep_iata"), "?"),
        "arrival_code": first(data.get("arr_iata"), "?"),
        "departure_time": time_text(first(data.get("dep_estimated"), data.get("dep_time"))),
        "arrival_time": time_text(first(data.get("arr_estimated"), data.get("arr_time"))),
        "terminal": first(data.get("arr_terminal"), "-"),
        "gate": first(data.get("arr_gate"), "-"),
        "latitude": lat,
        "longitude": lon,
        "altitude_ft": feet_from_meters(data.get("alt")),
        "speed_kt": integer(speed_kmh * 0.539957 if speed_kmh is not None else None),
        "heading": integer(data.get("dir")),
        "country": location["country"],
        "country_code": location["country_code"],
        "capital": location["capital"],
    }


def response_payload(raw):
    data = raw.get("response", raw) if isinstance(raw, dict) else raw
    if isinstance(data, list):
        return data[0] if data else None
    if isinstance(data, dict):
        return data
    return None


def fetch_flight(settings):
    flight_number = compact(settings["flight_number"])
    api_key = settings["api_key"]

    if not flight_number:
        raise RuntimeError("No flight number configured.")
    if not api_key:
        raise RuntimeError("No AirLabs API key configured.")

    key, value = flight_param(flight_number)
    raw = get_json(
        AIRLABS_URL,
        params={
            "api_key": api_key,
            key: value,
        },
        timeout=20,
    )
    if isinstance(raw, dict) and raw.get("error"):
        error = raw["error"]
        if isinstance(error, dict):
            raise RuntimeError(error.get("message") or str(error))
        raise RuntimeError(str(error))

    data = response_payload(raw)
    if not data:
        raise RuntimeError(f"No AirLabs data found for {flight_number}.")

    return normalize_flight(data, flight_number)
