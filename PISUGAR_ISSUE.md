# PiSugar 3 — I²C peripheral is silent (chip provides power but doesn't respond on bus)

## Hardware

- Raspberry Pi Zero 2W
- Debian 13 (trixie), 64-bit (aarch64), kernel 6.12
- PiSugar 3 board, 1200 mAh LiPo built-in (board condition unknown; battery is new)
- PN532 NFC reader on I²C bus 1, address `0x24`, jumper-wired to GPIO 2 (SDA, header pin 3), GPIO 3 (SCL, pin 5), 3.3 V (pin 17). Jumpers exit the header sideways, not under the PiSugar HAT.
- Adafruit I²S Speaker Bonnet, KY-040 rotary encoder (these are not on I²C)

## Symptom

PiSugar 3 powers the Pi correctly. The Pi boots, all services run, wifi auto-connects, audio plays, NFC works. The PiSugar's blue LED is solid (MCU alive, providing power, not in fault state).

But the PiSugar's onboard battery-management chip does **not** acknowledge on the I²C bus at its expected address `0x57`. Installing the official `pisugar-power-manager` package (v2.3.2) and running `pisugar-server` produces an endless stream of:

```
[WARN  pisugar_server] Poll error: I/O error: Remote I/O error (os error 121), retry after 1s
[INFO  pisugar_core] Init rtc...
[INFO  pisugar_core::model] Binding rtc i2c bus=1 addr=87
```

(`addr=87` decimal = `0x57` hex.) `pisugar-server` reports `battery: I2C not connected` for every query.

## What works on the same I²C bus

- `sudo i2cdetect -y 1` shows the PN532 at `0x24` whenever the PN532 is connected — bus 1 is electrically healthy
- `dmesg | grep -i i2c` shows zero I²C errors
- `dtparam=i2c_arm=on` is set in `/boot/firmware/config.txt` (default 100 kHz clock)
- Pi runs on PiSugar battery for hours without brown-outs

## What I tried (none of these changed the result)

1. Multiple HAT reseats with even pressure on both ends of the GPIO header
2. Visual inspection of GPIO pins on both Pi and PiSugar sides — no bent / missing pins, no foreign material
3. **Removed the PN532 board entirely**, leaving only the PiSugar on the bus → bus completely empty, no `0x57`
4. Probed alternate PiSugar/Li-ion-IC addresses: `0x55`, `0x56`, `0x57`, `0x75` — all silent
5. `sudo i2cdetect -y -a 1` (full address range) — only `0x24` visible (when PN532 connected)
6. Direct `sudo i2cget -y 1 0x57 0x22` and `0x23` — both fail with `Error: Read failed`
7. Connected USB power to wake the chip from any potential shipping / deep-sleep mode → re-scanned after ~30 s → no change
8. Re-routed PN532 jumpers so they exit sideways from the header rather than under the PiSugar body (in case wires were physically blocking I²C pin contact) → PN532 still visible, PiSugar still silent
9. Reboot after every meaningful change

## What I couldn't test

- No oscilloscope / logic analyzer — can't observe actual SDA/SCL line activity
- `pisugar-programmer` (the official firmware-reflash tool) only communicates over the same I²C that's broken, so it's unusable as a recovery path
- I don't have a known-good second PiSugar 3 to compare against

## Working theory

The PiSugar 3's MCU is partly alive (drives LED, controls the boost converter providing 5 V to the Pi), but the chip's I²C peripheral does not assert on the bus. Most likely a board-level fault — bad solder joint on the chip's SDA/SCL traces, or a damaged/never-functional I²C peripheral on the MCU itself. RMA seems the most practical path.

## Questions for an outside opinion

- Is there a known PiSugar 3 firmware mode where I²C stays disabled until something specific (button press pattern, GPIO state, USB charge sequence) wakes it?
- Any Debian Trixie 64-bit / Pi Zero 2W kernel-level quirk known to silently disable an I²C peripheral on a HAT while leaving bus 1 itself functional?
- Any documented way to communicate with the PiSugar 3's MCU outside of I²C (UART, SWD test pads, button-trigger commands)?
- Is there a `dtoverlay` (besides `dtparam=i2c_arm=on`) that PiSugar 3 actually requires?

## Current state

- Pi runs on PiSugar 3 power without issue, but with no battery monitoring or graceful low-battery shutdown
- `pisugar-server.service` is disabled to stop the per-second log spam
- Original Waveshare UPS HAT (C) + INA219-based monitoring stack is the available fallback if PiSugar can't be revived
