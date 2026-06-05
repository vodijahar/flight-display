#!/usr/bin/env python3
import socket

from renderer import render_status
from display import display_image
from config import LAST_RENDER_FILE, STATE_DIR


def ip_address():
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            return sock.getsockname()[0]
    except Exception:
        pass

    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            address = info[4][0]
            if not address.startswith("127."):
                return address
    except Exception:
        pass

    return "No IP yet"


def main():
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    ip = ip_address()
    image = render_status(
        "Flight Display",
        [
            "Screen OK",
            f"IP {ip}",
            f"http://{ip}:8080" if ip != "No IP yet" else "Open web UI on port 8080",
            "Set flight number",
        ],
    )
    image.save(LAST_RENDER_FILE)
    display_image(image)


if __name__ == "__main__":
    main()
