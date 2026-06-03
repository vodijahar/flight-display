from datetime import datetime

from PIL import Image, ImageDraw, ImageFont

from config import WIDTH, HEIGHT

FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_BOLD_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


def load_font(path, size):
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()


FONT_BIG = load_font(FONT_BOLD_PATH, 26)
FONT_HEAD = load_font(FONT_BOLD_PATH, 16)
FONT_TEXT = load_font(FONT_PATH, 12)
FONT_SMALL = load_font(FONT_PATH, 10)


def time_text(value):
    if not value:
        return "--:--"
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).strftime("%H:%M")
    except Exception:
        return value[11:16] if len(value) >= 16 else value


def base_image(title):
    image = Image.new("1", (WIDTH, HEIGHT), 255)
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, WIDTH - 1, HEIGHT - 1), outline=0)
    draw.rectangle((0, 0, WIDTH - 1, 23), fill=0)
    draw.text((7, 3), title[:24], font=FONT_HEAD, fill=255)
    return image, draw


def draw_map(draw, lat, lon):
    left, top, right, bottom = 166, 30, 240, 78
    draw.rectangle((left, top, right, bottom), outline=0)
    draw.line((left, top + 24, right, top + 24), fill=0)
    draw.line((left + 37, top, left + 37, bottom), fill=0)

    if lat is None or lon is None:
        draw.text((left + 15, top + 17), "NO POS", font=FONT_SMALL, fill=0)
        return

    x = left + int((lon + 180) / 360 * (right - left))
    y = top + int((90 - lat) / 180 * (bottom - top))
    x = max(left + 2, min(right - 2, x))
    y = max(top + 2, min(bottom - 2, y))
    draw.ellipse((x - 3, y - 3, x + 3, y + 3), fill=0)


def render_flight(data):
    image, draw = base_image(data["flight_number"])
    route = f'{data["departure_code"]}>{data["arrival_code"]}'
    status = data["status"].replace("_", " ")
    delay = data["delay_text"]
    eta = data["arrival_time"]
    altitude = data["altitude_ft"]
    speed = data["speed_kt"]
    country = data.get("country") or "Unknown"
    capital = data.get("capital") or "Unknown"

    draw.text((8, 30), route[:10], font=FONT_BIG, fill=0)
    draw_map(draw, data["latitude"], data["longitude"])
    draw.text((8, 62), f"{status[:10]} {delay}"[:22], font=FONT_HEAD, fill=0)
    draw.text(
        (8, 84),
        f"ETA {eta}  Gate {data['gate']}"[:32],
        font=FONT_TEXT,
        fill=0,
    )
    draw.text(
        (8, 104),
        f'Alt {altitude if altitude is not None else "-"}ft Spd {speed if speed is not None else "-"}kt',
        font=FONT_SMALL,
        fill=0,
    )
    draw.text(
        (141, 84),
        f"Over {country}"[:22],
        font=FONT_SMALL,
        fill=0,
    )
    draw.text(
        (141, 104),
        f"Cap {capital}"[:22],
        font=FONT_SMALL,
        fill=0,
    )
    return image


def render_status(title, lines):
    image, draw = base_image(title)
    y = 34
    for line in lines[:5]:
        draw.text((8, y), str(line)[:32], font=FONT_TEXT, fill=0)
        y += 18
    return image
