#!/usr/bin/env python3
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from base64 import b64decode
from datetime import datetime
from html import escape
import os
from urllib.parse import parse_qs
import subprocess

from config import API_USAGE_FILE
from settings import MASKED_API_KEY, load_settings, save_settings
from state import read_json

HOST = "0.0.0.0"
PORT = 8080
WEB_USER = os.getenv("WEB_USER", "flight")
WEB_PASSWORD = os.getenv("WEB_PASSWORD", "flight")


def masked_key(value):
    if not value:
        return ""
    return MASKED_API_KEY


def usage_text():
    usage = read_json(API_USAGE_FILE)
    if not usage:
        return "<p>AirLabs quota: no successful API response yet.</p>"

    remaining = usage.get("limits_total")
    monthly = usage.get("limits_by_month")
    minute = usage.get("limits_by_minute")
    hour = usage.get("limits_by_hour")
    updated_at = usage.get("updated_at")

    updated = "unknown"
    if updated_at:
        try:
            updated = datetime.fromtimestamp(int(updated_at)).strftime("%Y-%m-%d %H:%M")
        except (TypeError, ValueError):
            pass

    parts = []
    if remaining is not None and monthly is not None:
        parts.append(f"{remaining} of {monthly} monthly requests remaining")
    elif remaining is not None:
        parts.append(f"{remaining} requests remaining")

    if hour is not None:
        parts.append(f"{hour}/hour")
    if minute is not None:
        parts.append(f"{minute}/minute")

    detail = "; ".join(parts) if parts else "latest limits unavailable"
    return f"<p>AirLabs quota: {escape(detail)}. Updated {escape(updated)}.</p>"


def page(message=""):
    settings = load_settings()
    api_key = escape(masked_key(settings.get("api_key", "")))
    flight = escape(settings.get("flight_number", ""))
    message_html = f"<p>{escape(message)}</p>" if message else ""
    usage_html = usage_text()
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Flight Display</title>
<style>
body {{ font-family: system-ui, sans-serif; max-width: 520px; margin: 32px auto; padding: 0 16px; }}
label {{ display: block; margin: 16px 0 6px; font-weight: 700; }}
input {{ box-sizing: border-box; width: 100%; padding: 10px; font-size: 16px; }}
button {{ margin-top: 18px; padding: 10px 14px; font-size: 16px; }}
p {{ background: #f1f1f1; padding: 10px; }}
</style>
</head>
<body>
<h1>Flight Display</h1>
{message_html}
{usage_html}
<form method="post">
<label for="flight_number">Flight number</label>
<input id="flight_number" name="flight_number" value="{flight}" placeholder="BA123 or BAW123" required>
<label for="api_key">AirLabs API key</label>
<input id="api_key" name="api_key" value="{api_key}" autocomplete="off" required>
<button type="submit">Save and refresh</button>
</form>
</body>
</html>"""


class Handler(BaseHTTPRequestHandler):
    def authenticated(self):
        header = self.headers.get("Authorization", "")
        if not header.startswith("Basic "):
            return False

        try:
            user, password = b64decode(header[6:]).decode("utf-8").split(":", 1)
        except Exception:
            return False

        return user == WEB_USER and password == WEB_PASSWORD

    def require_auth(self):
        self.send_response(401)
        self.send_header("WWW-Authenticate", 'Basic realm="Flight Display"')
        self.end_headers()

    def do_GET(self):
        if not self.authenticated():
            self.require_auth()
            return
        self.respond(page())

    def do_POST(self):
        if not self.authenticated():
            self.require_auth()
            return

        length = int(self.headers.get("Content-Length", "0"))
        form = parse_qs(self.rfile.read(length).decode("utf-8"))
        current = load_settings()
        api_key = form.get("api_key", [""])[0].strip()
        if api_key == MASKED_API_KEY:
            api_key = current.get("api_key", "")
        save_settings(
            {
                "api_key": api_key,
                "flight_number": form.get("flight_number", [""])[0],
            }
        )
        subprocess.run(["systemctl", "start", "flight-display.service"], check=False)
        self.respond(page("Saved. Display refresh requested."))

    def respond(self, content):
        body = content.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        return


def main():
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()


if __name__ == "__main__":
    main()
