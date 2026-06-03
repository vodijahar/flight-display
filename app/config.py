from pathlib import Path
import os

APP_DIR = Path("/opt/flight-display/app")
STATE_DIR = Path("/var/lib/flight-display")
LOG_DIR = Path("/var/log/flight-display")

SETTINGS_FILE = STATE_DIR / "settings.json"
LAST_FLIGHT_FILE = STATE_DIR / "last_flight.json"
LAST_RENDER_FILE = STATE_DIR / "last_render.png"
LOCATION_CACHE_FILE = STATE_DIR / "location_cache.json"

WIDTH = 250
HEIGHT = 122

WAVESHARE_DRIVER = os.getenv("WAVESHARE_DRIVER", "V4").strip().upper()
DISPLAY_ROTATE = os.getenv("DISPLAY_ROTATE", "0").strip()

DEFAULT_FLIGHT_NUMBER = os.getenv("FLIGHT_NUMBER", "").strip().upper()
AIRLABS_API_KEY = os.getenv("AIRLABS_API_KEY", "").strip()
AIRLABS_URL = os.getenv("AIRLABS_URL", "https://airlabs.co/api/v9/flight").strip()
NOMINATIM_REVERSE_URL = os.getenv(
    "NOMINATIM_REVERSE_URL", "https://nominatim.openstreetmap.org/reverse"
).strip()
RESTCOUNTRIES_URL = os.getenv(
    "RESTCOUNTRIES_URL", "https://restcountries.com/v3.1/alpha"
).strip()
