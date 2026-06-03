#!/usr/bin/env python3
import json
import logging

from config import LAST_FLIGHT_FILE, LAST_RENDER_FILE, LOG_DIR, STATE_DIR
from display import display_image
from flight import fetch_flight
from renderer import render_flight, render_status
from settings import load_settings


def setup_logging():
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        filename=LOG_DIR / "flight.log",
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )


def load_last_flight():
    if not LAST_FLIGHT_FILE.exists():
        return None
    try:
        return json.loads(LAST_FLIGHT_FILE.read_text(encoding="utf-8"))
    except Exception:
        return None


def save_last_flight(data):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    LAST_FLIGHT_FILE.write_text(
        json.dumps(data, ensure_ascii=False, sort_keys=True),
        encoding="utf-8",
    )


def changed(old, new):
    if not old:
        return True
    keys = [
        "flight_number",
        "status",
        "delay_minutes",
        "arrival_time",
        "latitude",
        "longitude",
        "altitude_ft",
        "speed_kt",
        "heading",
        "country",
        "capital",
    ]
    return any(old.get(key) != new.get(key) for key in keys)


def show_status(title, lines):
    image = render_status(title, lines)
    image.save(LAST_RENDER_FILE)
    display_image(image)


def main():
    setup_logging()
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    settings = load_settings()

    try:
        data = fetch_flight(settings)
    except Exception as exc:
        logging.exception("Flight update failed")
        if LAST_RENDER_FILE.exists():
            logging.info("Keeping last successful render after update failure.")
            return

        flight = settings.get("flight_number") or "not set"
        show_status(
            "Flight Pending",
            [
                f"Flight: {flight}",
                type(exc).__name__[:30],
                str(exc)[:30],
            ],
        )
        return

    previous = load_last_flight()
    if not changed(previous, data):
        logging.info("Flight unchanged. Skipping display refresh.")
        return

    image = render_flight(data)
    image.save(LAST_RENDER_FILE)
    display_image(image)
    save_last_flight(data)
    logging.info("Display updated: %s", data)


if __name__ == "__main__":
    main()
