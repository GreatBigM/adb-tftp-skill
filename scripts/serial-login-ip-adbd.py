#!/usr/bin/env python3
"""
Serial login + static IP + adbd restart for HM6502/Ingenic devices.
Steps: blind login (30 bursts) -> verify via timestamp echo -> set eth0 IP -> start adbd
"""
import serial, time, subprocess, sys

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
        print(f'LOGIN_FAILED')
        return False
    print(f'LOGIN_OK timestamp={ts}')
    ser.read(ser.in_waiting)
    return True

def send_cmd(ser, cmd, delay=2.5):
    ser.write(f'{cmd}\r'.encode())
    time.sleep(delay)
    buf = bytearray()
    deadline = time.time() + delay
    while time.time() < deadline:
        if ser.in_waiting:
            buf.extend(ser.read(ser.in_waiting))
        else:
            time.sleep(0.02)
    return buf.decode(errors='replace')

if __name__ == '__main__':
    reset_port()
    ser = serial.Serial(DEVICE, BAUD, timeout=0.2)
    time.sleep(0.3)
    ser.read(ser.in_waiting)

    if not login(ser):
        sys.exit(1)

    # Set static IP
    out = send_cmd(ser, 'ifconfig eth0 172.17.150.200 netmask 255.255.254.0 up')
    print(f'IP_SET|{out.strip()[-200:]}')

    # Verify IP
    out = send_cmd(ser, 'ifconfig eth0 | grep "inet addr" > /tmp/_ip_check; cat /tmp/_ip_check')
    print(f'IP_CHECK|{out.strip()[-200:]}')

    # Restart adbd
    out = send_cmd(ser, 'killall adbd 2>/dev/null; adbd &')
    print(f'ADBD_START|{out.strip()[-200:]}')

    # Verify adbd
    out = send_cmd(ser, 'ps | grep adbd | grep -v grep > /tmp/_adbd_check; cat /tmp/_adbd_check')
    print(f'ADBD_CHECK|{out.strip()[-200:]}')

    ser.close()
    print('STEP1_DONE')
