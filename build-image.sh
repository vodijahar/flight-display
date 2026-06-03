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
        fonts-dejavu-core
    apt-get clean
    rm -rf /var/lib/apt/lists/*
'

echo "[+] Installing flight app"
sudo mkdir -p "${ROOT_MNT}/opt/flight-display/app"
sudo rsync -a "${ROOT_DIR}/app/" "${ROOT_MNT}/opt/flight-display/app/"

echo "[+] Installing firstboot script"
sudo install -m 0755 "${ROOT_DIR}/image/firstboot.sh" \
    "${ROOT_MNT}/usr/local/sbin/firstboot-flight.sh"

echo "[+] Installing systemd units"
for unit in firstboot-flight.service flight-display.service flight-display.timer flight-web.service; do
    sudo install -m 0644 "${ROOT_DIR}/systemd/${unit}" "${ROOT_MNT}/etc/systemd/system/${unit}"
done

echo "[+] Enabling firstboot service"
sudo mkdir -p "${ROOT_MNT}/etc/systemd/system/multi-user.target.wants"
sudo ln -sf /etc/systemd/system/firstboot-flight.service \
    "${ROOT_MNT}/etc/systemd/system/multi-user.target.wants/firstboot-flight.service"

echo "[+] Creating runtime directories"
sudo mkdir -p "${ROOT_MNT}/var/lib/flight-display" "${ROOT_MNT}/var/log/flight-display"

echo "[+] Enabling SPI"
if [ -f "${BOOT_MNT}/config.txt" ] && ! sudo grep -q '^dtparam=spi=on' "${BOOT_MNT}/config.txt"; then
    echo 'dtparam=spi=on' | sudo tee -a "${BOOT_MNT}/config.txt" >/dev/null
fi

echo "[+] Enabling SSH"
sudo touch "${BOOT_MNT}/ssh"

echo "[+] Copying optional flight-display.env"
if [ -f "${ROOT_DIR}/image/flight-display.env" ]; then
    sudo cp "${ROOT_DIR}/image/flight-display.env" "${BOOT_MNT}/flight-display.env"
fi

sync

echo "[+] Compressing image"
xz -T0 -z -3 -f "${WORK_IMG}"

echo "[+] Done"
echo "[+] Output: ${WORK_IMG}.xz"
