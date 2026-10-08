"""Render the game's synth sound effects (same recipes as src/audio.js) to WAV files for Godot.

Run:  python3 scripts/gen_sfx.py   -> godot/assets/sfx/*.wav
"""
import math
import os
import random
import struct
import wave

RATE = 22050
OUT = os.path.join(os.path.dirname(__file__), '..', 'godot', 'assets', 'sfx')
random.seed(3)


class Buf:
    def __init__(self, seconds):
        self.d = [0.0] * int(seconds * RATE)

    def add(self, start, samples, pan=0):
        i0 = int(start * RATE)
        for i, s in enumerate(samples):
            if i0 + i < len(self.d):
                self.d[i0 + i] += s


def env(n, attack, dur):
    """exp attack then exponential decay to ~0 at dur (like setTarget/exponentialRamp)."""
    out = []
    a = max(1, int(attack * RATE))
    for i in range(n):
        if i < a:
            out.append(i / a)
        else:
            k = (i - a) / max(1, n - a)
            out.append(math.exp(-5.5 * k))
    return out


def sweep(f0, f1, n):
    if f1 is None:
        return [f0] * n
    return [f0 * (f1 / f0) ** (i / max(1, n - 1)) for i in range(n)]


def biquad(x, kind, freqs, q=0.7):
    y = []
    x1 = x2 = y1 = y2 = 0.0
    b0 = b1 = b2 = a1 = a2 = 0.0
    for i, s in enumerate(x):
        if i % 16 == 0:
            f = min(freqs[i], RATE * 0.45)
            w = 2 * math.pi * f / RATE
            al = math.sin(w) / (2 * q)
            c = math.cos(w)
            if kind == 'lowpass':
                b0, b1, b2 = (1 - c) / 2, 1 - c, (1 - c) / 2
            elif kind == 'highpass':
                b0, b1, b2 = (1 + c) / 2, -(1 + c), (1 + c) / 2
            else:  # bandpass (constant peak)
                b0, b1, b2 = al, 0.0, -al
            a0 = 1 + al
            a1, a2 = -2 * c / a0, (1 - al) / a0
            b0, b1, b2 = b0 / a0, b1 / a0, b2 / a0
        o = b0 * s + b1 * x1 + b2 * x2 - a1 * y1 - a2 * y2
        x2, x1, y2, y1 = x1, s, y1, o
        y.append(o)
    return y


def noise(dur, kind='lowpass', freq=1000, freq_end=None, q=0.7, gain=1.0, attack=0.002):
    n = int(dur * RATE)
    x = [random.uniform(-1, 1) for _ in range(n)]
    y = biquad(x, kind, sweep(freq, freq_end, n), q)
    e = env(n, attack, dur)
    return [y[i] * e[i] * gain for i in range(n)]


def tone(freq, dur, wave_='sine', freq_end=None, gain=0.5, attack=0.005):
    n = int(dur * RATE)
    fs = sweep(freq, freq_end, n)
    e = env(n, attack, dur)
    out, ph = [], 0.0
    for i in range(n):
        ph += fs[i] / RATE
        p = ph % 1.0
        if wave_ == 'sine':
            v = math.sin(2 * math.pi * p)
        elif wave_ == 'square':
            v = 1.0 if p < 0.5 else -1.0
        elif wave_ == 'sawtooth':
            v = 2 * p - 1
        else:  # triangle
            v = 4 * abs(p - 0.5) - 1
        out.append(v * e[i] * gain)
    return out


SOUNDS = {
    'katapult': (0.3, [(0, noise(0.12, 'bandpass', 2500, 600, 2, 0.5)), (0, tone(500, 0.12, 'triangle', 120, 0.35))]),
    'shotgun': (0.7, [(0, noise(0.45, 'lowpass', 2200, 300, gain=1.0)), (0, tone(120, 0.25, 'sine', 40, 0.9)),
                      (0.35, noise(0.05, 'highpass', 3000, gain=0.4)), (0.5, noise(0.05, 'highpass', 2500, gain=0.4))]),
    'sniper': (1.1, [(0, noise(0.08, 'highpass', 1500, gain=1.0)), (0, noise(0.9, 'lowpass', 1200, 200, gain=0.6, attack=0.01)),
                     (0, tone(90, 0.3, 'sine', 35, 0.8)), (0.55, noise(0.04, 'highpass', 4000, gain=0.3))]),
    'bazooka': (1.0, [(0, noise(0.9, 'bandpass', 400, 2500, 1.2, 0.9, 0.02)), (0, tone(70, 0.4, 'sine', 30, 0.8))]),
    'explosion': (1.8, [(0, noise(1.6, 'lowpass', 900, 60, gain=1.2)), (0, tone(65, 1.0, 'sine', 25, 1.0)), (0, noise(0.3, 'highpass', 2000, gain=0.4))]),
    'hit': (0.25, [(0, tone(320, 0.14, 'square', 90, 0.18)), (0, noise(0.06, 'bandpass', 1200, gain=0.4))]),
    'hit_head': (0.35, [(0, tone(320, 0.14, 'square', 90, 0.18)), (0, noise(0.06, 'bandpass', 1200, gain=0.4)), (0.03, tone(1760, 0.25, 'triangle', None, 0.25))]),
    'knock_off': (0.6, [(0.05, tone(200, 0.35, 'sawtooth', 60, 0.15)), (0.25, noise(0.25, 'lowpass', 800, 150, gain=0.5))]),
    'bell': (0.75, [(0, tone(2100, 0.5, 'sine', None, 0.18)), (0, tone(2650, 0.4, 'sine', None, 0.1)),
                    (0.14, tone(2100, 0.5, 'sine', None, 0.16)), (0.14, tone(2650, 0.4, 'sine', None, 0.08))]),
    'whoosh': (0.45, [(0, noise(0.4, 'bandpass', 600, 2600, 3, 0.35, 0.15))]),
    'clank': (0.2, [(0, tone(900, 0.15, 'square', 500, 0.12)), (0, noise(0.08, 'highpass', 3000, gain=0.3))]),
    'hurt': (0.4, [(0, tone(220, 0.35, 'sawtooth', 70, 0.3)), (0, noise(0.2, 'lowpass', 600, gain=0.5))]),
    'click': (0.05, [(0, noise(0.03, 'highpass', 3000, gain=0.3))]),
    'reload': (0.35, [(0, noise(0.03, 'highpass', 3000, gain=0.3)), (0.25, noise(0.05, 'highpass', 2200, gain=0.3))]),
    'empty': (0.08, [(0, tone(1500, 0.05, 'square', None, 0.08))]),
    'cheer': (1.3, [(i * 0.05, noise(1.1, 'bandpass', 900 + i * 350, None, 4, 0.12, 0.25)) for i in range(4)]),
    'tick': (0.08, [(0, tone(1000, 0.06, 'square', None, 0.1))]),
    'go': (0.6, [(0, tone(660, 0.15, 'square', None, 0.15)), (0.15, tone(990, 0.4, 'square', None, 0.15))]),
    'end': (1.0, [(i * 0.18, tone(f, 0.3, 'square', None, 0.12)) for i, f in enumerate((523, 440, 349, 262))]),
    'bullet_in': (1.3, [(0, tone(320, 0.9, 'sawtooth', 60, 0.25, 0.02)), (0, noise(1.0, 'bandpass', 3000, 200, 2, 0.5, 0.05)), (0, tone(55, 1.2, 'sine', None, 0.6, 0.05))]),
    'bullet_out': (0.6, [(0, tone(80, 0.5, 'sawtooth', 400, 0.2, 0.02)), (0, noise(0.5, 'bandpass', 300, 3000, 2, 0.35, 0.05))]),
    'ready': (0.3, [(0, tone(880, 0.18, 'triangle', None, 0.12)), (0.09, tone(1320, 0.18, 'triangle', None, 0.12))]),
}


def write(name, samples):
    peak = max(1e-6, max(abs(s) for s in samples))
    g = min(1.0, 0.9 / peak) if peak > 0.9 else 1.0
    with wave.open(os.path.join(OUT, f'{name}.wav'), 'wb') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(b''.join(struct.pack('<h', int(max(-1, min(1, s * g)) * 32000)) for s in samples))


def main():
    os.makedirs(OUT, exist_ok=True)
    for name, (dur, layers) in SOUNDS.items():
        b = Buf(dur)
        for t, s in layers:
            b.add(t, s)
        write(name, b.d)
    print(f'wrote {len(SOUNDS)} sounds to {os.path.abspath(OUT)}')


if __name__ == '__main__':
    main()
