#!/usr/bin/env python3
"""NFC-triggered MP3 player. Persistent mpg123 -R keeps ALSA open so pause doesn't click."""
import json
import os
import subprocess
import time
from pathlib import Path

import serial
from adafruit_pn532.uart import PN532_UART

HERE = Path(__file__).parent
MAPPING_PATH = HERE / "mapping.json"
CTL_FIFO = "/tmp/lydbox.ctl"
MISS_TOLERANCE = 3
POLL_TIMEOUT = 0.1
IDLE_SLEEP = 0.2
UART_DEV = "/dev/serial0"
UART_BAUD = 115200

def init_pn532(uart, attempts=3):
    last = None
    for _ in range(attempts):
        try:
            pn = PN532_UART(uart, debug=False)
            pn.SAM_configuration()
            return pn
        except RuntimeError as e:
            last = e
            time.sleep(0.5)
    raise last

def uid_hex(uid):
    return "".join(f"{b:02X}" for b in uid)

def start_mpg123():
    return subprocess.Popen(
        ["mpg123", "-R", "-o", "alsa", "-a", "default"],
        stdin=subprocess.PIPE,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        text=True,
    )

def send(mpg, cmd):
    if mpg.poll() is None and mpg.stdin:
        try:
            mpg.stdin.write(cmd + "\n")
            mpg.stdin.flush()
        except BrokenPipeError:
            pass

def setup_fifo():
    try:
        os.mkfifo(CTL_FIFO, 0o660)
    except FileExistsError:
        pass
    return os.open(CTL_FIFO, os.O_RDWR | os.O_NONBLOCK)

def drain_fifo(fd):
    try:
        data = os.read(fd, 4096)
    except BlockingIOError:
        return []
    if not data:
        return []
    return [c.strip() for c in data.decode(errors="ignore").split("\n") if c.strip()]

def main():
    uart = serial.Serial(UART_DEV, baudrate=UART_BAUD, timeout=1)
    pn = init_pn532(uart)
    mapping = json.loads(MAPPING_PATH.read_text()) if MAPPING_PATH.exists() else {}
    mpg = start_mpg123()
    ctl_fd = setup_fifo()
    print(f"loaded {len(mapping)} UID(s), mpg123 pid={mpg.pid}, ctl={CTL_FIFO}", flush=True)

    loaded_uid = None
    held_uid = None
    paused = False
    misses = 0

    try:
        while True:
            for cmd in drain_fifo(ctl_fd):
                if cmd == "pause" and loaded_uid is not None:
                    send(mpg, "P")
                    paused = not paused
                    print("paused" if paused else "resumed", flush=True)

            uid = pn.read_passive_target(timeout=POLL_TIMEOUT)
            seen = uid_hex(uid) if uid else None
            time.sleep(IDLE_SLEEP)

            if seen is not None and seen == held_uid:
                misses = 0
                continue

            if seen is None:
                misses += 1
                if misses < MISS_TOLERANCE:
                    continue
                if held_uid is not None:
                    print("released", flush=True)
                    held_uid = None
                    if loaded_uid is not None and not paused:
                        send(mpg, "P")
                        paused = True
                continue

            misses = 0

            if seen == loaded_uid:
                held_uid = seen
                if paused:
                    send(mpg, "P")
                    paused = False
                    print(f"resumed {seen}", flush=True)
                continue

            held_uid = seen
            path = mapping.get(seen)
            if path and Path(path).is_file():
                if paused:
                    send(mpg, "P")
                    paused = False
                send(mpg, f"LOAD {path}")
                loaded_uid = seen
                print(f"playing {seen}: {path}", flush=True)
            else:
                if paused:
                    send(mpg, "P")
                    paused = False
                send(mpg, "S")
                loaded_uid = None
                msg = f"missing file: {path}" if path else f"no mapping for {seen}"
                print(msg, flush=True)
    finally:
        send(mpg, "Q")
        try:
            mpg.wait(timeout=2)
        except subprocess.TimeoutExpired:
            mpg.kill()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
