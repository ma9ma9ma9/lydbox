#!/usr/bin/env python3
"""Continuously print NTAG/Mifare UIDs read via the PN532 over UART (HSU mode)."""
import time

import serial
from adafruit_pn532.uart import PN532_UART

UART_DEV = "/dev/serial0"
UART_BAUD = 115200


def init_pn532(uart, attempts=3):
    last_err = None
    for _ in range(attempts):
        try:
            pn = PN532_UART(uart, debug=False)
            pn.SAM_configuration()
            return pn
        except RuntimeError as e:
            last_err = e
            time.sleep(0.5)
    raise last_err


def main():
    uart = serial.Serial(UART_DEV, baudrate=UART_BAUD, timeout=1)
    pn = init_pn532(uart)
    ic, ver, rev, _ = pn.firmware_version
    print(f"PN532 firmware v{ver}.{rev} (IC 0x{ic:02X})", flush=True)
    last = None
    while True:
        uid = pn.read_passive_target(timeout=0.3)
        cur = list(uid) if uid is not None else None
        if cur != last:
            if cur is None:
                print("[removed]", flush=True)
            else:
                print("UID: " + ":".join(f"{b:02X}" for b in uid), flush=True)
            last = cur


if __name__ == "__main__":
    main()
