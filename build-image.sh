#!/usr/bin/env bash
set -euo pipefail

if [ $# -lt 1 ]; then
    echo "Usage: $0 /path/to/base-raspios-lite.img[.xz]"
    exit 1
fi

BASE_IMG="$1"
ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
OUT_DIR="${ROOT_DIR}/out"
WORK_IMG="${OUT_DIR}/flight-display.img"
BASE_WORK_IMG="${OUT_DIR}/base-raspios-lite.img"

BOOT_MNT="$(mktemp -d)"
ROOT_MNT="$(mktemp -d)"
LOOP_DEV=""
QEMU_ARM_STATIC="/usr/bin/qemu-arm-static"

cleanup() {
    set +e
    sync
    mountpoint -q "${ROOT_MNT}/dev/pts" && sudo umount "${ROOT_MNT}/dev/pts"
    mountpoint -q "${ROOT_MNT}/dev" && sudo umount "${ROOT_MNT}/dev"
    mountpoint -q "${ROOT_MNT}/proc" && sudo umount "${ROOT_MNT}/proc"
    mountpoint -q "${ROOT_MNT}/sys" && sudo umount "${ROOT_MNT}/sys"
    [ -f "${ROOT_MNT}/usr/bin/qemu-arm-static" ] && sudo rm -f "${ROOT_MNT}/usr/bin/qemu-arm-static"
    mountpoint -q "${BOOT_MNT}" && sudo umount "${BOOT_MNT}"
    mountpoint -q "${ROOT_MNT}" && sudo umount "${ROOT_MNT}"
    [ -n "${LOOP_DEV}" ] && sudo losetup -d "${LOOP_DEV}"
    rm -rf "${BOOT_MNT}" "${ROOT_MNT}"
}
trap cleanup EXIT

mkdir -p "${OUT_DIR}"

echo "[+] Copying base image"
if [[ "${BASE_IMG}" == *.xz ]]; then
    xz -dc "${BASE_IMG}" > "${BASE_WORK_IMG}"
    cp "${BASE_WORK_IMG}" "${WORK_IMG}"
else
    cp "${BASE_IMG}" "${WORK_IMG}"
fi

echo "[+] Attaching image as loop device"
LOOP_DEV="$(sudo losetup --find --partscan --show "${WORK_IMG}")"

echo "[+] Mounting boot and root partitions"
sudo mount "${LOOP_DEV}p1" "${BOOT_MNT}"
sudo mount "${LOOP_DEV}p2" "${ROOT_MNT}"

echo "[+] Installing runtime packages into image"
[ -x "${QEMU_ARM_STATIC}" ] && sudo cp "${QEMU_ARM_STATIC}" "${ROOT_MNT}/usr/bin/qemu-arm-static"
sudo mount --bind /dev "${ROOT_MNT}/dev"
sudo mount --bind /dev/pts "${ROOT_MNT}/dev/pts"
sudo mount -t proc proc "${ROOT_MNT}/proc"
sudo mount -t sysfs sys "${ROOT_MNT}/sys"
sudo chroot "${ROOT_MNT}" /bin/bash -c '
    set -euo pipefail
    export DEBIAN_FRONTEND=noninteractive
    apt-get update
    apt-get install -y --no-install-recommends \
        python3 \
        python3-pil \
        python3-spidev \
        python3-rpi.gpio \
        fonts-dejavu-core \
        openssh-server \
        network-manager \
        dnsmasq-base
    apt-get clean
    rm -rf /var/lib/apt/lists/*
'

echo "[+] Installing flight app"
sudo mkdir -p "${ROOT_MNT}/opt/flight-display/app"
sudo rsync -a "${ROOT_DIR}/app/" "${ROOT_MNT}/opt/flight-display/app/"

echo "[+] Installing systemd units"
for unit in flight-setup.service flight-display.service flight-display.timer flight-web.service; do
    sudo install -m 0644 "${ROOT_DIR}/systemd/${unit}" "${ROOT_MNT}/etc/systemd/system/${unit}"
done

echo "[+] Installing default environment"
sudo install -m 0600 /dev/null "${ROOT_MNT}/etc/default/flight-display"
sudo tee "${ROOT_MNT}/etc/default/flight-display" >/dev/null <<'EOF'
WAVESHARE_DRIVER=V4
DISPLAY_ROTATE=0
DEVICE_HOSTNAME=flight-display
SSH_USER=flight
SSH_PASSWORD=flight
WEB_USER=flight
WEB_PASSWORD=flight
FLIGHT_POLL_SECONDS=600
EOF
if [ -f "${ROOT_DIR}/image/flight-display.env" ]; then
    sudo install -m 0600 "${ROOT_DIR}/image/flight-display.env" \
        "${ROOT_MNT}/etc/default/flight-display"
fi

echo "[+] Creating SSH user"
sudo chroot "${ROOT_MNT}" /bin/bash -c '
    set -euo pipefail
    set -a
    . /etc/default/flight-display
    set +a

    user_name="${SSH_USER:-flight}"
    user_password="${SSH_PASSWORD:-flight}"

    if ! printf "%s" "${user_name}" | grep -Eq "^[a-z_][a-z0-9_-]{0,31}$"; then
        echo "Invalid SSH_USER ${user_name}" >&2
        exit 1
    fi

    groups="$(getent group sudo adm dialout video gpio i2c spi 2>/dev/null | cut -d: -f1 | paste -sd, -)"
    if ! id "${user_name}" >/dev/null 2>&1; then
        if [ -n "${groups}" ]; then
            useradd -m -s /bin/bash -G "${groups}" "${user_name}"
        else
            useradd -m -s /bin/bash "${user_name}"
        fi
    fi

    printf "%s:%s\n" "${user_name}" "${user_password}" | chpasswd
    passwd -u "${user_name}" >/dev/null 2>&1 || true
    mkdir -p /etc/ssh/sshd_config.d
    cat > /etc/ssh/sshd_config.d/99-flight-display.conf <<EOF
PasswordAuthentication yes
PermitRootLogin no
EOF
'

echo "[+] Enabling services"
sudo mkdir -p "${ROOT_MNT}/etc/systemd/system/multi-user.target.wants"
sudo ln -sf /etc/systemd/system/flight-setup.service \
    "${ROOT_MNT}/etc/systemd/system/multi-user.target.wants/flight-setup.service"
sudo ln -sf /etc/systemd/system/flight-web.service \
    "${ROOT_MNT}/etc/systemd/system/multi-user.target.wants/flight-web.service"
sudo mkdir -p "${ROOT_MNT}/etc/systemd/system/timers.target.wants"
sudo ln -sf /etc/systemd/system/flight-display.timer \
    "${ROOT_MNT}/etc/systemd/system/timers.target.wants/flight-display.timer"

echo "[+] Enabling SSH service"
if [ -f "${ROOT_MNT}/lib/systemd/system/ssh.service" ]; then
    sudo ln -sf /lib/systemd/system/ssh.service \
        "${ROOT_MNT}/etc/systemd/system/multi-user.target.wants/ssh.service"
elif [ -f "${ROOT_MNT}/usr/lib/systemd/system/ssh.service" ]; then
    sudo ln -sf /usr/lib/systemd/system/ssh.service \
        "${ROOT_MNT}/etc/systemd/system/multi-user.target.wants/ssh.service"
fi

echo "[+] Creating runtime directories"
sudo mkdir -p "${ROOT_MNT}/var/lib/flight-display" "${ROOT_MNT}/var/log/flight-display"

echo "[+] Enabling SPI"
if [ -f "${BOOT_MNT}/config.txt" ] && ! sudo grep -q '^dtparam=spi=on' "${BOOT_MNT}/config.txt"; then
    echo 'dtparam=spi=on' | sudo tee -a "${BOOT_MNT}/config.txt" >/dev/null
fi

echo "[+] Enabling SSH"
sudo touch "${BOOT_MNT}/ssh"

sync

echo "[+] Compressing image"
xz -T0 -z -3 -f "${WORK_IMG}"

echo "[+] Done"
echo "[+] Output: ${WORK_IMG}.xz"
