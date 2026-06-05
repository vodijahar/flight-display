# Flight Display

Raspberry Pi Zero W / Zero 2 W flight tracker for a Waveshare 2.13" e-paper display.

## Features

- Waveshare 2.13" e-paper V2/V3/V4 support
- Flight number and AirLabs API key configured from a local web interface
- Timer-driven display updates
- Position, route, delay status, ETA, and approximate country/capital context
- Automatic large clock mode after the tracked flight lands
- First-boot SSH, hostname, and optional Wi-Fi setup
- Runtime Python packages and Waveshare driver embedded in the image
- No third-party Python HTTP client

## Hardware

- Raspberry Pi Zero W or Zero 2 W
- Waveshare 2.13" e-paper display, V4 by default
- GPIO/SPI connection

## Flight Data

Flight Display uses the AirLabs flight information API:

```text
https://airlabs.co/api/v9/flight
```

AirLabs provides the flight status, route, estimated arrival time, delay fields, and live position used by the display. The position is also used for a small locator map and a best-effort country/capital lookup.

You need an AirLabs API key and internet access for live flight updates. The display and web interface still boot without Wi-Fi, but live tracking waits until the Pi has network access.

Flight times are shown in the Raspberry Pi's local timezone. For example, if the flight lands in the US but the Pi is configured for Japan time, the ETA shown on the e-paper display is converted to Japan time.

The timer runs every minute. While the flight is active, the app throttles AirLabs requests to once every 10 minutes by default. Change `FLIGHT_POLL_SECONDS` in `/etc/default/flight-display` if you need a different polling interval.

When the selected flight reports a landed/arrived status, the app stops polling AirLabs for that flight and switches the display to a large `HH:MM` clock. Clock ticks use the Waveshare driver's partial refresh path where supported, so only the changing time is updated without a full panel clear.

## Build Locally

This project builds a Raspberry Pi OS Lite 32-bit image. The output is:

```text
out/flight-display.img.xz
```

Install build tools on a Linux build host:

```bash
sudo apt update
sudo apt install -y git rsync xz-utils util-linux e2fsprogs qemu-user-static binfmt-support
```

Build from a Raspberry Pi OS Lite image:

```bash
./build-image.sh /path/to/raspios-lite.img.xz
```

## Flash and First Boot

Flash `flight-display.img.xz`.

If your flasher does not offer Wi-Fi/user customisation for custom images, mount the boot partition before first boot and create `flight-display.env`:

```bash
WAVESHARE_DRIVER=V4
DISPLAY_ROTATE=0
DEVICE_HOSTNAME=flight-display
SSH_USER=flight
SSH_PASSWORD=flight
WEB_USER=flight
WEB_PASSWORD=flight

WIFI_SSID=YourNetworkName
WIFI_PASSWORD=YourNetworkPassword
WIFI_COUNTRY=ZA
WIFI_HIDDEN=0

FLIGHT_NUMBER=BA123
AIRLABS_API_KEY=your-api-key
FLIGHT_POLL_SECONDS=600
```

Default SSH login:

```bash
ssh flight@flight-display.local
```

Default password:

```text
flight
```

Change the password after first login:

```bash
passwd
```

## Web Interface

Open the web UI from a browser on the same network:

```text
http://flight-display.local:8080
```

Set the flight number and AirLabs API key, then save. The web service triggers an immediate display refresh.

The web UI also shows the latest known AirLabs quota information from the most recent successful flight API response. Viewing the web UI does not make an extra AirLabs request.

The web UI stores these values in:

```text
/var/lib/flight-display/settings.json
```

Latest quota information is stored in:

```text
/var/lib/flight-display/api_usage.json
```

Default web login:

```text
flight / flight
```

Change `WEB_USER` and `WEB_PASSWORD` in `flight-display.env` before first boot, or in `/etc/default/flight-display` later.

## API Key Setup

You can provide the AirLabs API key in any of these places:

Before first boot, add it to `flight-display.env` on the boot partition:

```bash
FLIGHT_NUMBER=BA123
AIRLABS_API_KEY=your-airlabs-api-key
```

After boot, use the web UI:

```text
http://flight-display.local:8080
```

Or edit the service environment on the Pi:

```bash
sudo nano /etc/default/flight-display
```

Add or update:

```bash
FLIGHT_NUMBER=BA123
AIRLABS_API_KEY=your-airlabs-api-key
```

Then force a refresh:

```bash
sudo systemctl start flight-display.service
```

## Changing Wi-Fi Later

Over SSH:

```bash
nmcli connection show
sudo nmcli connection modify flight-display-wifi wifi.ssid "NewNetworkName"
sudo nmcli connection modify flight-display-wifi wifi-sec.psk "NewNetworkPassword"
sudo nmcli connection down flight-display-wifi
sudo nmcli connection up flight-display-wifi
```

For a hidden network:

```bash
sudo nmcli connection modify flight-display-wifi wifi.hidden yes
```

## Useful Commands

Force a refresh:

```bash
sudo systemctl start flight-display.service
```

View logs:

```bash
sudo journalctl -u firstboot-flight -u flight-display -u flight-web -n 150 --no-pager
sudo cat /var/log/flight-display/flight.log
```

Rotate the display:

```bash
sudo nano /etc/default/flight-display
sudo systemctl start flight-display.service
```
