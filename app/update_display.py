#!/usr/bin/env python3
import logging
from datetime import datetime
from time import time

from config import (
    API_USAGE_FILE,
    CLOCK_STATE_FILE,
    FLIGHT_POLL_SECONDS,
    LAST_FLIGHT_FILE,
    LAST_RENDER_FILE,
    LOG_DIR,
    STATE_DIR,
    UPDATE_LOCK_FILE,
)
from display import display_image, display_image_partial
from flight import fetch_flight
from renderer import render_clock, render_flight, render_status
from settings import load_settings
from state import lock_file, read_json, write_json


def setup_logging():
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        filename=LOG_DIR / "flight.log",
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )


def load_last_flight():
    return read_json(LAST_FLIGHT_FILE, default=None)


def save_last_flight(data):
    data = dict(data)
    data["fetched_at"] = int(time())
    write_json(LAST_FLIGHT_FILE, data)


def save_api_usage(data):
    usage = data.get("api_usage") or {}
    if not usage:
        return
    usage = dict(usage)
    usage["updated_at"] = int(time())
    write_json(API_USAGE_FILE, usage)


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


def same_flight(old, settings):
    if not old:
        return False
    flight_number = settings.get("flight_number")
    return flight_number in {
        old.get("tracked_flight"),
        old.get("flight_number"),
        old.get("flight_icao"),
    }


def is_landed(data):
    status = str(data.get("status", "")).strip().lower().replace("_", " ")
    return status in {"landed", "arrived", "arrival", "completed"}


def poll_due(previous):
    if not previous:
        return True
    fetched_at = previous.get("fetched_at")
    if not fetched_at:
        return True
    return time() - int(fetched_at) >= FLIGHT_POLL_SECONDS


def load_clock_state():
    return read_json(CLOCK_STATE_FILE)


def save_clock_state(text, flight_number):
    write_json(CLOCK_STATE_FILE, {"time": text, "flight_number": flight_number})


def clear_clock_state():
    try:
        CLOCK_STATE_FILE.unlink()
    except FileNotFoundError:
        pass


def log_flight(prefix, data):
    logging.info(
        "%s: %s %s>%s %s ETA %s",
        prefix,
        data.get("flight_number"),
        data.get("departure_code"),
        data.get("arrival_code"),
        data.get("status"),
        data.get("arrival_time"),
    )


def show_clock(flight_number):
    image, text = render_clock(datetime.now())
    state = load_clock_state()
    if state.get("time") == text and state.get("flight_number") == flight_number:
        logging.info("Clock unchanged. Skipping display refresh.")
        return

    image.save(LAST_RENDER_FILE)
    if state.get("flight_number") == flight_number:
        display_image_partial(image)
        logging.info("Clock partial update: %s", text)
    else:
        display_image(image)
        logging.info("Clock full update: %s", text)
    save_clock_state(text, flight_number)


def main():
    setup_logging()
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    with lock_file(UPDATE_LOCK_FILE):
        settings = load_settings()
        previous = load_last_flight()

        if same_flight(previous, settings) and is_landed(previous):
            show_clock(settings["flight_number"])
            return

        if same_flight(previous, settings) and not poll_due(previous):
            logging.info("Flight poll not due. Skipping API request.")
            return

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

        clear_clock_state()
        save_api_usage(data)

        if is_landed(data):
            save_last_flight(data)
            show_clock(settings["flight_number"])
            log_flight("Flight landed. Switching to clock mode", data)
            return

        if not changed(previous, data):
            logging.info("Flight unchanged. Skipping display refresh.")
            save_last_flight(data)
            return

        image = render_flight(data)
        image.save(LAST_RENDER_FILE)
        display_image(image)
        save_last_flight(data)
        log_flight("Display updated", data)


if __name__ == "__main__":
    main()
