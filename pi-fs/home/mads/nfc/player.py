#!/usr/bin/env python3
"""NFC-triggered MP3 player. Reads UIDs from PN532, plays mapped file via mpg123."""
import json
import subprocess
import time
from pathlib import Path

import board
import busio
from adafruit_pn532.i2c import PN532_I2C

HERE = Path(__file__).parent
MAPPING_PATH = HERE / "mapping.json"
PLAYER_CMD = ["mpg123", "-o", "alsa", "-a", "default", "-q"]
MISS_TOLERANCE = 3

def init_pn532(i2c, attempts=3):
    last = None
    for _ in range(attempts):
        try:
            pn = PN532_I2C(i2c, debug=False)
            pn.SAM_configuration()
            return pn
        except RuntimeError as e:
            last = e
            time.sleep(0.5)
    raise last

def uid_hex(uid):
    return "".join(f"{b:02X}" for b in uid)

def stop(proc):
    if not proc or proc.poll() is not None:
        return
    proc.terminate()
    try:
        proc.wait(1)
    except subprocess.TimeoutExpired:
        proc.kill()

def main():
    i2c = busio.I2C(board.SCL, board.SDA)
    pn = init_pn532(i2c)
    mapping = json.loads(MAPPING_PATH.read_text()) if MAPPING_PATH.exists() else {}
    print(f"loaded {len(mapping)} UID mapping(s)", flush=True)

    held = None
    misses = 0
    proc = None

    while True:
        uid = pn.read_passive_target(timeout=0.3)
        seen = uid_hex(uid) if uid else None

        if seen is not None and seen == held:
            misses = 0
            continue

        if seen is None:
            misses += 1
            if misses < MISS_TOLERANCE:
                continue
            if held is not None:
                print("released", flush=True)
                stop(proc)
                proc = None
                held = None
            continue

        misses = 0
        if held is not None:
            stop(proc)
            proc = None
        held = seen
        path = mapping.get(seen)
        if path and Path(path).is_file():
            print(f"playing {seen}: {path}", flush=True)
            proc = subprocess.Popen(PLAYER_CMD + [path])
        elif path:
            print(f"mapped but missing file: {path}", flush=True)
        else:
            print(f"no mapping for {seen}", flush=True)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
