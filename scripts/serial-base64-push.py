#!/usr/bin/env python3
"""
Push binary files to an embedded device via serial using base64 encoding.
Fallback when ADB push is unavailable or unreliable.

Usage: python3 serial-base64-push.py <local_file> <remote_path>

Supports large files (chunked at 500 chars per echo to avoid serial truncation).
On-device decoding uses 'base64 -d' (busybox compatible).
"""
import serial, time, subprocess, sys, base64, os

BAUD = 921600
DEVICE = '/dev/ttyUSB0'

def reset_port():
    subprocess.run(['stty', '-F', DEVICE, str(BAUD),
        'cs8', '-cstopb', '-parenb', 'raw', '-echo', '-echoe', '-echok'],
        capture_output=True)
    time.sleep(0.3)

def login(ser):
    for i in range(30):
        ser.write(b'root\r')
        time.sleep(0.03)
        ser.write(b'\r')
        time.sleep(0.03)
    ts = str(int(time.time()))
    ser.write(f'echo L_{ts}\r'.encode())
    time.sleep(2)
    buf = bytearray()
    deadline = time.time() + 3
    while time.time() < deadline:
        if ser.in_waiting:
            buf.extend(ser.read(ser.in_waiting))
        else:
            time.sleep(0.02)
    if f'L_{ts}' not in buf.decode(errors='replace'):
        print('LOGIN_FAILED', file=sys.stderr)
        return False
    print(f'LOGIN_OK ts={ts}', file=sys.stderr)
    ser.read(ser.in_waiting)
    return True

def push_file(ser, local_path, remote_path):
    with open(local_path, 'rb') as f:
        b64 = base64.b64encode(f.read()).decode()
    total_chunks = (len(b64) + 499) // 500
    print(f'Pushing {local_path} -> {remote_path} ({total_chunks} chunks)', file=sys.stderr)
    ser.write(f'echo -n "" > {remote_path}.b64\r'.encode())
    time.sleep(0.3)
    ser.read(ser.in_waiting)
    chunk_size = 500
    for i in range(0, len(b64), chunk_size):
        chunk = b64[i:i+chunk_size]
        ser.write(f'echo -n "{chunk}" >> {remote_path}.b64\r'.encode())
        time.sleep(0.03)
        if ser.in_waiting:
            ser.read(ser.in_waiting)
    ser.write(f'cat {remote_path}.b64 | base64 -d > {remote_path} && chmod +x {remote_path} && rm {remote_path}.b64 && echo PUSH_OK\r'.encode())
    time.sleep(3)
    buf = bytearray()
    deadline = time.time() + 5
    while time.time() < deadline:
        if ser.in_waiting:
            buf.extend(ser.read(ser.in_waiting))
        else:
            time.sleep(0.02)
    result = buf.decode(errors='replace')
    if 'PUSH_OK' in result:
        print(f'PUSH_OK -> {remote_path}', file=sys.stderr)
        return True
    print(f'PUSH_FAILED|{result[-300:]}', file=sys.stderr)
    return False

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print(f'Usage: {sys.argv[0]} <local_file> <remote_path>', file=sys.stderr)
        sys.exit(1)
    local_file = sys.argv[1]
    remote_path = sys.argv[2]
    reset_port()
    ser = serial.Serial(DEVICE, BAUD, timeout=0.2)
    time.sleep(0.3)
    ser.read(ser.in_waiting)
    if not login(ser):
        sys.exit(1)
    push_file(ser, local_file, remote_path)
    ser.close()
