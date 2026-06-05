from config import (
    AIRLABS_API_KEY,
    DEFAULT_FLIGHT_NUMBER,
    SETTINGS_FILE,
)
from state import read_json, write_json

MASKED_API_KEY = "********"


def clean_api_key(value):
    return "".join(ch for ch in str(value or "").strip() if ch.isprintable())


def clean_flight_number(value):
    return "".join(ch for ch in str(value or "").strip().upper() if ch.isalnum())


def default_settings():
    return {
        "api_key": AIRLABS_API_KEY,
        "flight_number": DEFAULT_FLIGHT_NUMBER,
    }


def load_settings():
    settings = default_settings()
    settings.update(read_json(SETTINGS_FILE))
    settings["api_key"] = clean_api_key(settings.get("api_key", ""))
    settings["flight_number"] = clean_flight_number(settings.get("flight_number", ""))
    return settings


def save_settings(settings):
    clean = {
        "api_key": clean_api_key(settings.get("api_key", "")),
        "flight_number": clean_flight_number(settings.get("flight_number", "")),
    }
    write_json(SETTINGS_FILE, clean)
    return clean
