#!/bin/bash
#
# Trigger device to reboot into U-Boot TFTP flash mode via CPSPR register.
#
# Usage:
#   mai_auto_flash.sh [NIC] [ADB_SERIAL]    # original mode: encode host IP to CPSPR
#   mai_auto_flash.sh <ADB_SERIAL>          # simple mode: fixed CPSPR 0x00000909
#
# When called with a single argument that looks like a device serial (contains
# ':' or starts with 'cam'/'hm'), uses simple mode with fixed CPSPR value.
# This is compatible with wuxiaoliang's flash_6801 skill convention.
#
# CPSPR register sequence:
#   0x10000038 <- 0x5a5a   (unlock)
#   0x10000034 <- VALUE    (IP encoding: 0xXXYY0909 = x.x.XX.YY, or 0x00000909 fixed)
#   0x10000038 <- 0xa5a5   (lock)
#   reboot
#
# After reboot, U-Boot detects CPSPR flag -> enters TFTP mode -> pulls
# auto_update_tftp.txt from host TFTP server -> flashes partitions -> reset.
# Device reboots -> adbd starts -> reports back to host via adbd_report.conf.

DEFAULT_NIC=$(ls /sys/class/net/ | grep -E '^(en|eth)' | head -1)

# Detect mode: if first arg looks like a serial (has ':' or known prefix),
# use simple mode (fixed CPSPR, no NIC needed)
SIMPLE_MODE=false
if [ $# -eq 1 ]; then
    case "$1" in
        *:*|cam_*|hm[0-9]*|HM[0-9]*|CAM_*)
            SIMPLE_MODE=true
            ADB_SERIAL="$1"
            ;;
    esac
fi

if [ "$SIMPLE_MODE" = "true" ]; then
    # Simple mode: fixed CPSPR, rely on adbd_report.conf for device reconnect
    VALUE="0x00000909"
    echo "Mode: simple (fixed CPSPR)"
    echo "ADB serial: $ADB_SERIAL"
    echo "CPSPR value: $VALUE"
    ADB="adb -s $ADB_SERIAL"
else
    # Original mode: encode host IP to CPSPR
    NIC=${1:-${DEFAULT_NIC:-eth0}}
    ADB_SERIAL=$2

    ip_str=$(ip -4 addr show "$NIC" 2>/dev/null | grep -oP 'inet \K[0-9.]+')
    if [ -z "$ip_str" ]; then
        echo "Error: cannot get IPv4 address from interface '$NIC'"
        exit 1
    fi

    v3=$(echo "$ip_str" | cut -d. -f3)
    v4=$(echo "$ip_str" | cut -d. -f4)

    VALUE=$(printf "0x%02x%02x0909" "$v3" "$v4")
    echo "Mode: IP-encoded"
    echo "NIC: $NIC, IP: $ip_str"
    echo "CPSPR value: $VALUE"

    if [ -n "$ADB_SERIAL" ]; then
        ADB="adb -s $ADB_SERIAL"
    else
        ADB="adb"
    fi
fi

echo "Triggering reboot into TFTP flash mode..."
$ADB shell "devmem 0x10000038 32 0x5a5a && devmem 0x10000034 32 $VALUE && devmem 0x10000038 32 0xa5a5 && reboot"
