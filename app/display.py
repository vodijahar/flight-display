from config import DISPLAY_ROTATE, WAVESHARE_DRIVER


def prepare_image(image):
    if DISPLAY_ROTATE == "90":
        return image.rotate(90, expand=True)
    if DISPLAY_ROTATE == "180":
        return image.rotate(180, expand=True)
    if DISPLAY_ROTATE == "270":
        return image.rotate(270, expand=True)
    return image


def get_driver():
    try:
        if WAVESHARE_DRIVER == "V4":
            from waveshare_epd import epd2in13_V4

            return epd2in13_V4
        if WAVESHARE_DRIVER == "V3":
            from waveshare_epd import epd2in13_V3

            return epd2in13_V3
        if WAVESHARE_DRIVER == "V2":
            from waveshare_epd import epd2in13_V2

            return epd2in13_V2
    except ImportError as exc:
        raise RuntimeError(
            "Waveshare e-Paper Python library is missing from the image."
        ) from exc

    raise RuntimeError(
        f"Unsupported WAVESHARE_DRIVER={WAVESHARE_DRIVER!r}; use V2, V3, or V4."
    )


def display_image(image):
    epd = get_driver().EPD()
    epd.init()
    epd.Clear(0xFF)
    epd.display(epd.getbuffer(prepare_image(image)))
    epd.sleep()
