from pathlib import Path
import os
from urllib.parse import urlparse


def env_int(name, default, minimum=1):
    try:
        return max(minimum, int(os.getenv(name, str(default))))
    except ValueError:
        return default


def env_https_url(name, default):
    value = os.getenv(name, default).strip()
    parsed = urlparse(value)
    if parsed.scheme != "https" or not parsed.netloc:
        return default
    return value

APP_DIR = Path("/opt/flight-display/app")
STATE_DIR = Path("/var/lib/flight-display")
LOG_DIR = Path("/var/log/flight-display")

SETTINGS_FILE = STATE_DIR / "settings.json"
LAST_FLIGHT_FILE = STATE_DIR / "last_flight.json"
LAST_RENDER_FILE = STATE_DIR / "last_render.png"
LOCATION_CACHE_FILE = STATE_DIR / "location_cache.json"
CLOCK_STATE_FILE = STATE_DIR / "clock_state.json"
API_USAGE_FILE = STATE_DIR / "api_usage.json"
UPDATE_LOCK_FILE = STATE_DIR / "update.lock"

WIDTH = 250
HEIGHT = 122

WAVESHARE_DRIVER = os.getenv("WAVESHARE_DRIVER", "V4").strip().upper()
DISPLAY_ROTATE = os.getenv("DISPLAY_ROTATE", "0").strip()

DEFAULT_FLIGHT_NUMBER = os.getenv("FLIGHT_NUMBER", "").strip().upper()
AIRLABS_API_KEY = os.getenv("AIRLABS_API_KEY", "").strip()
AIRLABS_URL = env_https_url("AIRLABS_URL", "https://airlabs.co/api/v9/flight")
NOMINATIM_REVERSE_URL = env_https_url(
    "NOMINATIM_REVERSE_URL", "https://nominatim.openstreetmap.org/reverse"
)
RESTCOUNTRIES_URL = env_https_url(
    "RESTCOUNTRIES_URL", "https://restcountries.com/v3.1/alpha"
)
FLIGHT_POLL_SECONDS = env_int("FLIGHT_POLL_SECONDS", 600, minimum=60)
