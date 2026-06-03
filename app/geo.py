import json

from config import LOCATION_CACHE_FILE, NOMINATIM_REVERSE_URL, RESTCOUNTRIES_URL, STATE_DIR
from net import get_json

USER_AGENT = "flight-display/1.0"


def load_cache():
    if not LOCATION_CACHE_FILE.exists():
        return {}
    try:
        return json.loads(LOCATION_CACHE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_cache(cache):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    LOCATION_CACHE_FILE.write_text(
        json.dumps(cache, ensure_ascii=False, sort_keys=True),
        encoding="utf-8",
    )


def country_from_position(lat, lon):
    data = get_json(
        NOMINATIM_REVERSE_URL,
        params={
            "format": "jsonv2",
            "lat": f"{lat:.5f}",
            "lon": f"{lon:.5f}",
            "zoom": 3,
            "addressdetails": 1,
        },
        timeout=10,
        headers={"User-Agent": USER_AGENT},
    )
    address = data.get("address") or {}
    return {
        "country": address.get("country") or "Unknown",
        "country_code": str(address.get("country_code") or "").upper(),
    }


def capital_for_country(country_code):
    if not country_code:
        return "Unknown"

    data = get_json(
        f"{RESTCOUNTRIES_URL}/{country_code}",
        params={"fields": "name,capital"},
        timeout=10,
        headers={"User-Agent": USER_AGENT},
    )
    item = data[0] if isinstance(data, list) and data else data
    capitals = item.get("capital") or []
    return capitals[0] if capitals else "Unknown"


def enrich_position(lat, lon):
    unknown = {"country": "Unknown", "country_code": "", "capital": "Unknown"}
    if lat is None or lon is None:
        return unknown

    key = f"{lat:.1f},{lon:.1f}"
    cache = load_cache()
    if key in cache:
        return {**unknown, **cache[key]}

    try:
        country = country_from_position(lat, lon)
        country["capital"] = capital_for_country(country["country_code"])
    except Exception:
        return unknown

    cache[key] = country
    save_cache(cache)
    return {**unknown, **country}
