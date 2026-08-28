---
name: adb-debug
description: "ADB device status but commands fail with error device not found - HTTP wget fallback and serial base64 push"
category: embedded-dev-loop
---

# Embedded ADB Recovery

Supplements `adb-debug` for the failure mode not covered there: ADB connects showing `device` status, but every command immediately returns `error: device not found`.

## Failure Mode: Device Status But Commands Fail

### Symptoms

```
$ adb connect 172.17.150.200
connected to 172.17.150.200:5555

$ adb devices
172.17.150.200:5555    device      # Shows device, not offline

$ adb shell 'echo OK'
error: device not found               # Every command fails immediately

$ adb push file /tmp/
error: device not found
```

### Key Difference From Offline

| Mode | `adb devices` Output | Typical Recovery |
|------|---------------------|-----------------|
| offline | `... offline` | `adb kill-server; reconnect` usually works |
| **device-but-fail** | `... device` | `adb kill-server` + restart adbd **usually fails** |

### Diagnosis

1. Serial: verify adbd alive: `ps | grep adbd`
   - adbd PID exists -> ADB transport layer stuck, not process crash
   - adbd missing -> init killed it (check `reap service adbd, crash too many times!`)
2. Serial: verify network: `ping <host_ip> -c 3`
   - ping works -> ADB channel unrecoverable, abandon repair
3. Do NOT retry repeatedly - kill-server + reconnect fails after 2 tries

### Root Cause (HM6502 specific)

- adbd killed by init restart limiter (`reap service adbd, crash too many times!`)
- PID survives but socket handles closed or transport layer zombie
- eth0 ADB transport stuck: `adb connect` handshake passes, data channel blocks

## Recovery A: HTTP wget Fallback (preferred)

When ADB channel is unrecoverable, use HTTP for file transfer:

```bash
# Host: start HTTP server in the binaries directory
cd /path/to/binaries && python3 -m http.server 8888 &

# Device (via serial): wget download
wget -q http://<host_ip>:8888/iperf3 -O /tmp/iperf3
chmod +x /tmp/iperf3
```

Find host IP: `ip addr show | grep "inet " | grep -v 127.0.0.1`

## Recovery B: Serial Base64 Push (no-network fallback)

For devices without wget/busybox wget:

```python
import base64, time

with open('iperf3', 'rb') as f:
    b64 = base64.b64encode(f.read()).decode()

# Chunked write (500 chars per chunk to avoid serial truncation)
chunk_size = 500
ser.write(b'echo -n "" > /tmp/iperf3.b64\r')
time.sleep(0.3)
for i in range(0, len(b64), chunk_size):
    ser.write(f'echo -n "{b64[i:i+chunk_size]}" >> /tmp/iperf3.b64\r'.encode())
    time.sleep(0.03)
    if ser.in_waiting:
        ser.read(ser.in_waiting)

# Base64 decode
ser.write(b'cat /tmp/iperf3.b64 | base64 -d > /tmp/iperf3 && chmod +x /tmp/iperf3 && echo PUSH_OK\r')
```

Time estimate: 833KB binary ~ 1700 serial writes ~ 2 minutes.

## Prevention

1. Verify ADB channel (serial push test) before relying on ADB for large transfers
2. Prefer HTTP wget over ADB push for large files when ADB is flaky
3. Set up HTTP server on host BEFORE attempting ADB push (have fallback ready)
