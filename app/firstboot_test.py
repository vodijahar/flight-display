#!/usr/bin/env python3
from renderer import render_status
from display import display_image
from config import LAST_RENDER_FILE, STATE_DIR


def main():
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    image = render_status(
        "Flight Display",
        ["Screen OK", "Open web UI on port 8080", "Set flight number"],
    )
    image.save(LAST_RENDER_FILE)
    display_image(image)


if __name__ == "__main__":
    main()
