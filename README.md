# Flight Display

Raspberry Pi Zero W / Zero 2 W flight tracker for a Waveshare 2.13" e-paper display.

## Features

- Waveshare 2.13" e-paper V2/V3/V4 support
- Flight number and AirLabs API key configured from a local web interface
- Timer-driven display updates
- Position, route, delay status, ETA, and approximate country/capital context
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

Default web login:

```text
flight / flight
```

Change `WEB_USER` and `WEB_PASSWORD` in `flight-display.env` before first boot, or in `/etc/default/flight-display` later.

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
