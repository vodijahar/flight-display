#!/usr/bin/env python3
import subprocess

SETUP_CONNECTION = "flight-display-setup"
SETUP_SSID = "FlightDisplay-Setup"
SETUP_PASSWORD = "flightdisplay"
WIFI_CONNECTION = "flight-display-wifi"
WIFI_IFACE = "wlan0"


def run_nmcli(*args, check=False):
    return subprocess.run(
        ["nmcli", *args],
        check=check,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        text=True,
    )


def has_network():
    result = subprocess.run(
        ["nm-online", "-q", "--timeout=10"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    return result.returncode == 0


def stop_setup_ap():
    run_nmcli("connection", "down", SETUP_CONNECTION)


def start_setup_ap():
    run_nmcli("radio", "wifi", "on")
    run_nmcli("connection", "delete", SETUP_CONNECTION)
    result = run_nmcli(
        "device",
        "wifi",
        "hotspot",
        "ifname",
        WIFI_IFACE,
        "con-name",
        SETUP_CONNECTION,
        "ssid",
        SETUP_SSID,
        "password",
        SETUP_PASSWORD,
    )
    if result.returncode == 0:
        run_nmcli(
            "connection",
            "modify",
            SETUP_CONNECTION,
            "ipv4.method",
            "shared",
            "ipv4.addresses",
            "192.168.4.1/24",
        )
        run_nmcli("connection", "up", SETUP_CONNECTION)
    return result.returncode == 0


def ensure_setup_network():
    if has_network():
        stop_setup_ap()
        return
    start_setup_ap()


def configure_wifi(ssid, password="", country="", hidden=False):
    ssid = str(ssid or "").strip()
    password = str(password or "").strip()
    country = str(country or "").strip().upper()

    if not ssid:
        raise RuntimeError("Wi-Fi SSID is required.")

    if country and len(country) == 2:
        subprocess.run(
            ["raspi-config", "nonint", "do_wifi_country", country],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            text=True,
        )

    run_nmcli("radio", "wifi", "on")
    run_nmcli("connection", "delete", WIFI_CONNECTION)
    run_nmcli(
        "connection",
        "add",
        "type",
        "wifi",
        "ifname",
        WIFI_IFACE,
        "con-name",
        WIFI_CONNECTION,
        "ssid",
        ssid,
        check=True,
    )
    run_nmcli("connection", "modify", WIFI_CONNECTION, "connection.autoconnect", "yes")

    if password:
        run_nmcli(
            "connection",
            "modify",
            WIFI_CONNECTION,
            "wifi-sec.key-mgmt",
            "wpa-psk",
            "wifi-sec.psk",
            password,
        )

    if hidden:
        run_nmcli("connection", "modify", WIFI_CONNECTION, "wifi.hidden", "yes")

    stop_setup_ap()
    result = run_nmcli("connection", "up", WIFI_CONNECTION)
    if result.returncode != 0:
        start_setup_ap()
        raise RuntimeError("Could not connect to Wi-Fi.")


def main():
    ensure_setup_network()


if __name__ == "__main__":
    main()
