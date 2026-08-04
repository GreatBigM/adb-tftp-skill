#!/bin/bash
#
# Non-interactive adbd_report.conf generator + deterministic MAC.
# Usage: gen_adbd_conf_noninteractive.sh <DEVICE_NAME> [NIC]
#
# Outputs (stdout, KEY=VALUE format for easy parsing):
#   CONF_FILE=adbd_report.conf
#   HOST_IP=192.168.1.100
#   MAC=02:ab:cd:ef:12:34
#   NIC=eth0
#   DEVICE_NAME=cam_front_01
#
# Also writes adbd_report.conf to current directory.
#
# Source: adapted from wuxiaoliang's flash_6801 skill.

DEVICE_NAME="$1"
if [ -z "$DEVICE_NAME" ]; then
    echo "Error: device name required as first argument" >&2
    exit 1
fi

DEFAULT_NIC=$(ls /sys/class/net/ | grep -E '^(en|eth)' | head -1)
NIC=${2:-${DEFAULT_NIC:-eth0}}

HOST_IP=$(ip -4 addr show "$NIC" 2>/dev/null | grep -oP 'inet \K[0-9.]+')
if [ -z "$HOST_IP" ]; then
    echo "Error: cannot get IPv4 address from interface '$NIC'" >&2
    exit 1
fi

MONITOR_IFACE="eth0"

CONF_FILE="adbd_report.conf"
cat > "$CONF_FILE" <<EOF
server_ip ${HOST_IP}
device_name ${DEVICE_NAME}
monitor_iface ${MONITOR_IFACE}
EOF

# Generate deterministic locally-administered unicast MAC from HOST_IP + DEVICE_NAME
# Ensures same device+host always gets same MAC, avoiding DHCP IP pool exhaustion
INPUT_STR="${HOST_IP}${DEVICE_NAME}"
HASH=$(printf '%s' "$INPUT_STR" | md5sum | cut -c1-12)

B0=$(printf '%02x' $(( (0x${HASH:0:2} & 0xfe) | 0x02 )))
B1=${HASH:2:2}
B2=${HASH:4:2}
B3=${HASH:6:2}
B4=${HASH:8:2}
B5=${HASH:10:2}

MAC="${B0}:${B1}:${B2}:${B3}:${B4}:${B5}"

echo "CONF_FILE=$CONF_FILE"
echo "HOST_IP=$HOST_IP"
echo "MAC=$MAC"
echo "NIC=$NIC"
echo "DEVICE_NAME=$DEVICE_NAME"
