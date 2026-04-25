#!/usr/bin/env python3
"""Trigger graceful shutdown when UPS HAT battery is too low for the boost to keep up.

Reads bus voltage from the INA219 on the Waveshare UPS HAT (C). With a single
18650 cell, the boost converter cuts out near 3.0 V — shutting down at 3.3 V
gives ~30 s of margin for systemd to stop services and sync the filesystem.
"""
import subprocess
import sys

import smbus

INA219_ADDR = 0x43
BUS_VOLTAGE_REG = 0x02
THRESHOLD_V = 3.30


def read_voltage(bus: smbus.SMBus) -> float:
    raw = bus.read_word_data(INA219_ADDR, BUS_VOLTAGE_REG)
    raw = ((raw & 0xFF) << 8) | (raw >> 8)
    return (raw >> 3) * 0.004


bus = smbus.SMBus(1)
voltage = read_voltage(bus)
print(f"battery {voltage:.3f}V (threshold {THRESHOLD_V:.2f}V)")

# Guard against a stuck-bus reading triggering a false shutdown on a healthy battery.
if voltage < 1.0 or voltage > 5.5:
    print("INA219 reading out of plausible range — ignoring", file=sys.stderr)
    sys.exit(0)

if voltage < THRESHOLD_V:
    print("battery low — initiating shutdown", file=sys.stderr)
    subprocess.run(["/usr/sbin/poweroff"], check=False)
