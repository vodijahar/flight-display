#!/usr/bin/env bash
set -uo pipefail

STAMP="/var/lib/flight-display/.firstboot_done"
LOG_DIR="/var/log/flight-display"
LOG_FILE="${LOG_DIR}/firstboot.log"

mkdir -p /var/lib/flight-display "${LOG_DIR}"
exec > >(tee -a "${LOG_FILE}") 2>&1
trap 'echo "[!] First boot command failed at line ${LINENO}; continuing where possible"' ERR

echo "[+] Flight display first boot starting"

if [ -f "${STAMP}" ]; then
    echo "[+] First boot already completed"
    exit 0
fi

echo "[+] Installing default config"
if [ -f /boot/flight-display.env ]; then
    install -m 0600 /boot/flight-display.env /etc/default/flight-display
elif [ -f /boot/firmware/flight-display.env ]; then
    install -m 0600 /boot/firmware/flight-display.env /etc/default/flight-display
elif [ ! -f /etc/default/flight-display ]; then
    install -m 0600 /dev/null /etc/default/flight-display
    cat > /etc/default/flight-display <<'EOF'
WAVESHARE_DRIVER=V4
DISPLAY_ROTATE=0
DEVICE_HOSTNAME=flight-display
SSH_USER=flight
SSH_PASSWORD=flight
WEB_USER=flight
WEB_PASSWORD=flight
EOF
fi

set -a
. /etc/default/flight-display
set +a

configure_ssh_user() {
    local user_name="${SSH_USER:-flight}"
    local user_password="${SSH_PASSWORD:-flight}"
    local groups

    if ! printf '%s' "${user_name}" | grep -Eq '^[a-z_][a-z0-9_-]{0,31}$'; then
        echo "[!] Invalid SSH_USER '${user_name}'; skipping SSH user setup"
        return
    fi
    if [ -z "${user_password}" ]; then
        echo "[!] Empty SSH_PASSWORD; skipping SSH user setup"
        return
    fi

    groups="$(getent group sudo adm dialout video gpio i2c spi 2>/dev/null | cut -d: -f1 | paste -sd, -)"
    if id "${user_name}" >/dev/null 2>&1; then
        echo "[+] Updating SSH user ${user_name}"
    elif [ -n "${groups}" ]; then
        useradd -m -s /bin/bash -G "${groups}" "${user_name}"
    else
        useradd -m -s /bin/bash "${user_name}"
    fi

    printf '%s:%s\n' "${user_name}" "${user_password}" | chpasswd
    passwd -u "${user_name}" >/dev/null 2>&1 || true
    mkdir -p /etc/ssh/sshd_config.d
    cat > /etc/ssh/sshd_config.d/99-flight-display.conf <<'EOF'
PasswordAuthentication yes
PermitRootLogin no
EOF
    systemctl enable ssh || true
    systemctl restart ssh || true
}

configure_hostname() {
    local device_hostname="${DEVICE_HOSTNAME:-flight-display}"

    if ! printf '%s' "${device_hostname}" | grep -Eq '^[A-Za-z0-9][A-Za-z0-9-]{0,62}$'; then
        echo "[!] Invalid DEVICE_HOSTNAME '${device_hostname}'; skipping hostname setup"
        return
    fi

    printf '%s\n' "${device_hostname}" > /etc/hostname
    if grep -q '^127\.0\.1\.1' /etc/hosts; then
        sed -i "s/^127\.0\.1\.1.*/127.0.1.1\t${device_hostname}/" /etc/hosts
    else
        printf '127.0.1.1\t%s\n' "${device_hostname}" >> /etc/hosts
    fi
    hostnamectl set-hostname "${device_hostname}" || true
}

configure_wifi() {
    if [ -z "${WIFI_SSID:-}" ]; then
        echo "[+] No WIFI_SSID configured"
        return
    fi

    if [ -n "${WIFI_COUNTRY:-}" ] && command -v raspi-config >/dev/null 2>&1; then
        raspi-config nonint do_wifi_country "${WIFI_COUNTRY}" || true
    fi

    nmcli radio wifi on || true
    nmcli connection delete flight-display-wifi >/dev/null 2>&1 || true
    nmcli connection add type wifi ifname wlan0 con-name flight-display-wifi ssid "${WIFI_SSID}" || true
    nmcli connection modify flight-display-wifi connection.autoconnect yes || true

    if [ -n "${WIFI_PASSWORD:-}" ]; then
        nmcli connection modify flight-display-wifi wifi-sec.key-mgmt wpa-psk wifi-sec.psk "${WIFI_PASSWORD}" || true
    fi
    if [ "${WIFI_HIDDEN:-0}" = "1" ]; then
        nmcli connection modify flight-display-wifi wifi.hidden yes || true
    fi

    nmcli connection up flight-display-wifi || true
}

wait_for_network() {
    echo "[+] Waiting for network"
    if command -v nm-online >/dev/null 2>&1; then
        nm-online -q --timeout=45 || true
    fi

    for _ in $(seq 1 12); do
        if /usr/bin/python3 - <<'PY' >/dev/null 2>&1
from urllib.request import urlopen
urlopen("https://airlabs.co", timeout=5).close()
PY
        then
            echo "[+] Network check passed"
            return
        fi
        sleep 5
    done

    echo "[!] Network check failed; flight update will retry on timer"
}

configure_ssh_user
configure_hostname
configure_wifi

echo "[+] Starting web UI"
systemctl enable flight-web.service || true
systemctl start flight-web.service || true

echo "[+] Checking runtime"
if ! /usr/bin/python3 -c 'from PIL import Image; import spidev; import RPi.GPIO' >/dev/null 2>&1; then
    echo "[!] Runtime packages missing; rebuild the image with embedded dependencies"
fi
if [ ! -f /usr/share/fonts/truetype/dejavu/DejaVuSans.ttf ] || [ ! -f /usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf ]; then
    echo "[!] DejaVu fonts missing; install fonts-dejavu-core for correctly sized text"
fi
if ! PYTHONPATH=/opt/flight-display/app /usr/bin/python3 -c 'from waveshare_epd import epd2in13_V4' >/dev/null 2>&1; then
    echo "[!] Waveshare driver missing; rebuild the image with vendored waveshare_epd"
fi

echo "[+] Running display test"
/usr/bin/python3 /opt/flight-display/app/firstboot_test.py || true

echo "[+] Enabling services"
systemctl enable flight-display.timer || true
wait_for_network
systemctl start flight-display.service || true

touch "${STAMP}"
echo "[+] First boot complete"
