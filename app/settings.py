import json

from config import (
    AIRLABS_API_KEY,
    DEFAULT_FLIGHT_NUMBER,
    SETTINGS_FILE,
    STATE_DIR,
)


def default_settings():
    return {
        "api_key": AIRLABS_API_KEY,
        "flight_number": DEFAULT_FLIGHT_NUMBER,
    }


def load_settings():
    settings = default_settings()
    if SETTINGS_FILE.exists():
        try:
            settings.update(json.loads(SETTINGS_FILE.read_text(encoding="utf-8")))
        except Exception:
            pass
    settings["api_key"] = str(settings.get("api_key", "")).strip()
    settings["flight_number"] = str(settings.get("flight_number", "")).strip().upper()
    return settings


def save_settings(settings):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    clean = {
        "api_key": str(settings.get("api_key", "")).strip(),
        "flight_number": str(settings.get("flight_number", "")).strip().upper(),
    }
    SETTINGS_FILE.write_text(
        json.dumps(clean, ensure_ascii=False, sort_keys=True),
        encoding="utf-8",
    )
    SETTINGS_FILE.chmod(0o600)
    return clean
