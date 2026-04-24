#!/usr/bin/env python3
"""Continuously print NTAG/Mifare UIDs read via the PN532 on I2C."""
import time
import board
import busio
from adafruit_pn532.i2c import PN532_I2C

def init_pn532(i2c, attempts=3):
    last_err = None
    for n in range(attempts):
        try:
            pn = PN532_I2C(i2c, debug=False)
            pn.SAM_configuration()
            return pn
        except RuntimeError as e:
            last_err = e
            time.sleep(0.5)
    raise last_err

def main():
    i2c = busio.I2C(board.SCL, board.SDA)
    pn = init_pn532(i2c)
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
