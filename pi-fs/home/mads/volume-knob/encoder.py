#!/usr/bin/env python3
"""KY-040 rotary encoder -> ALSA 'Master' softvol control for lydbox."""
import signal
import alsaaudio
from gpiozero import RotaryEncoder, Button

CARD_INDEX = 1
MIXER_NAME = "Master"
STEP_PERCENT = 3

def prime_softvol():
    try:
        pcm = alsaaudio.PCM(alsaaudio.PCM_PLAYBACK, device="default")
        pcm.close()
    except alsaaudio.ALSAAudioError:
        pass

def mixer():
    return alsaaudio.Mixer(MIXER_NAME, cardindex=CARD_INDEX)

def get_volume():
    return mixer().getvolume()[0]

def set_volume(v):
    v = max(0, min(100, int(v)))
    mixer().setvolume(v)
    print(f"volume={v}", flush=True)

def adjust(delta):
    set_volume(get_volume() + delta)

_pre_mute = [60]
def toggle_mute():
    v = get_volume()
    if v > 0:
        _pre_mute[0] = v
        set_volume(0)
    else:
        set_volume(_pre_mute[0])

def main():
    prime_softvol()
    enc = RotaryEncoder(17, 27, max_steps=0)
    enc.when_rotated_clockwise = lambda: adjust(STEP_PERCENT)
    enc.when_rotated_counter_clockwise = lambda: adjust(-STEP_PERCENT)
    btn = Button(22, bounce_time=0.05)
    btn.when_pressed = toggle_mute
    print(f"volume-knob ready: vol={get_volume()}%", flush=True)
    signal.pause()

if __name__ == "__main__":
    main()
