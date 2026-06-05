from datetime import datetime, timezone
import re

from config import AIRLABS_URL
from geo import enrich_position
from net import get_json


def first(value, default=""):
    return value if value not in (None, "") else default


def first_of(*values, default=""):
    for value in values:
        if value not in (None, ""):
            return value
    return default


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


def local_time_text(*values):
    for value in values:
        text = str(value or "").strip()
        if not text:
            continue

        for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M:%S%z"):
            try:
                parsed = datetime.strptime(text, fmt)
                if parsed.tzinfo is None:
                    parsed = parsed.replace(tzinfo=timezone.utc)
                return parsed.astimezone().strftime("%H:%M")
            except ValueError:
                pass

        try:
            local_time = datetime.fromtimestamp(int(text), timezone.utc).astimezone()
            return local_time.strftime("%H:%M")
        except ValueError:
            pass

    return "--:--"


def airport_time_text(value):
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
        "tracked_flight": requested_flight,
        "flight_number": first(data.get("flight_iata"), requested_flight),
        "flight_icao": first(data.get("flight_icao"), ""),
        "status": status_text(data),
        "delay_minutes": delay,
        "delay_text": delay_text(delay),
        "departure_code": first(data.get("dep_iata"), "?"),
        "arrival_code": first(data.get("arr_iata"), "?"),
        "departure_time": local_time_text(
            data.get("dep_estimated_utc"),
            data.get("dep_actual_utc"),
            data.get("dep_time_utc"),
            data.get("dep_estimated_ts"),
            data.get("dep_actual_ts"),
            data.get("dep_time_ts"),
        ),
        "arrival_time": local_time_text(
            data.get("arr_estimated_utc"),
            data.get("arr_actual_utc"),
            data.get("arr_time_utc"),
            data.get("arr_estimated_ts"),
            data.get("arr_actual_ts"),
            data.get("arr_time_ts"),
        ),
        "departure_airport_time": airport_time_text(
            first_of(
                data.get("dep_estimated"),
                data.get("dep_actual"),
                data.get("dep_time"),
            )
        ),
        "arrival_airport_time": airport_time_text(
            first_of(
                data.get("arr_estimated"),
                data.get("arr_actual"),
                data.get("arr_time"),
            )
        ),
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


def api_usage(raw):
    if not isinstance(raw, dict):
        return {}

    request = raw.get("request") or {}
    fields = (
        "limits_by_hour",
        "limits_by_minute",
        "limits_by_month",
        "limits_total",
    )
    return {
        key: integer(request.get(key))
        for key in fields
        if request.get(key) not in (None, "")
    }


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

    flight = normalize_flight(data, flight_number)
    flight["api_usage"] = api_usage(raw)
    return flight
