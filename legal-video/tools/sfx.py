"""Procedural sound-effects library (all original, synthesized with numpy).

  python3 tools/sfx.py            # writes build/sfx/<name>.wav (+ variants)

Every effect is a function f(rng, **kw) -> stereo float array at 48 kHz.
Variants (key presses, ticks…) are produced with different seeds so repeated
sounds never feel copy-pasted.
"""
import json
import zlib
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy import signal

SR = 48000
ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'build' / 'sfx'


# ---------------------------------------------------------------------------
# helpers

def t_axis(dur):
    return np.arange(int(dur * SR)) / SR


def env_exp(dur, decay, attack=0.002):
    t = t_axis(dur)
    a = np.clip(t / max(attack, 1e-4), 0, 1)
    return a * np.exp(-t / decay)


def bandpass(x, lo, hi, order=2):
    sos = signal.butter(order, [lo, hi], btype='band', fs=SR, output='sos')
    return signal.sosfilt(sos, x)


def lowpass(x, f, order=2):
    sos = signal.butter(order, f, btype='low', fs=SR, output='sos')
    return signal.sosfilt(sos, x)


def highpass(x, f, order=2):
    sos = signal.butter(order, f, btype='high', fs=SR, output='sos')
    return signal.sosfilt(sos, x)


def resonator(x, f, q):
    b, a = signal.iirpeak(f, q, fs=SR)
    return signal.lfilter(b, a, x)


def modes(dur, freqs, decays, amps, rng=None, detune=0.0):
    t = t_axis(dur)
    y = np.zeros_like(t)
    for f, d, a in zip(freqs, decays, amps):
        if rng is not None and detune:
            f *= 1 + (rng.random() - 0.5) * detune
        y += a * np.sin(2 * np.pi * f * t + (rng.random() * 6.28 if rng is not None else 0)) * np.exp(-t / d)
    return y


def pad(x, dur):
    n = int(dur * SR)
    if len(x) >= n:
        return x[:n]
    return np.concatenate([x, np.zeros(n - len(x))])


def mix(*parts):
    n = max(len(p) for p in parts)
    out = np.zeros(n)
    for p in parts:
        out[: len(p)] += p
    return out


def norm(x, peak=0.9):
    m = np.max(np.abs(x)) + 1e-9
    return x * (peak / m)


def stereo(x, width=0.0, rng=None, pan=0.0):
    """Mono → stereo with optional decorrelated width and constant-power pan."""
    l = x.copy()
    r = x.copy()
    if width > 0:
        d = int(0.00045 * SR)
        r = np.concatenate([np.zeros(d), x[:-d]]) * 1.0
        l = l * (1 - width * 0.3) + r * width * 0.3
    ang = (pan + 1) * np.pi / 4
    return np.stack([l * np.cos(ang) * 1.414, r * np.sin(ang) * 1.414], axis=1)


_IR = {}


def reverb_ir(seconds=2.2, damp=0.6, seed=3, predelay=0.012):
    key = (seconds, damp, seed, predelay)
    if key in _IR:
        return _IR[key]
    rng = np.random.default_rng(seed)
    n = int(seconds * SR)
    t = np.arange(n) / SR
    chans = []
    for c in range(2):
        noise = rng.standard_normal(n)
        # frequency-dependent decay: split into bands with different T60
        lo = lowpass(noise, 800) * np.exp(-t * 6.9 / seconds)
        mid = bandpass(noise, 800, 4000) * np.exp(-t * 6.9 / (seconds * (1 - damp * 0.5)))
        hi = highpass(noise, 4000) * np.exp(-t * 6.9 / (seconds * (1 - damp * 0.85)))
        ir = lo + 0.8 * mid + 0.5 * hi
        pre = int(predelay * SR)
        ir = np.concatenate([np.zeros(pre), ir])
        # a few early reflections
        for k in range(6):
            pos = pre + int(rng.uniform(0.004, 0.045) * SR)
            ir[pos] += rng.uniform(0.3, 0.7) * (1 if rng.random() > 0.5 else -1)
        chans.append(ir / np.sqrt(np.sum(ir ** 2)))
    _IR[key] = np.stack(chans, axis=1)
    return _IR[key]


def add_reverb(st, wet=0.25, seconds=2.2, damp=0.6):
    ir = reverb_ir(seconds, damp)
    out = np.zeros((st.shape[0] + ir.shape[0] - 1, 2))
    for c in range(2):
        out[:, c] = signal.fftconvolve(st[:, c], ir[:, c])
    dry = np.zeros_like(out)
    dry[: st.shape[0]] = st
    return dry * (1 - wet * 0.5) + out * wet


# ---------------------------------------------------------------------------
# effects

def fx_key(rng):
    d = 0.09
    click = bandpass(rng.standard_normal(int(0.004 * SR)), 2000, 6000) * 0.9
    thock = modes(d, [170 + rng.random() * 40, 1150 + rng.random() * 200], [0.012, 0.006], [0.8, 0.35], rng)
    clack = resonator(rng.standard_normal(int(d * SR)) * env_exp(d, 0.004), 2600 + rng.random() * 600, 8) * 0.5
    x = mix(click, thock, clack)
    return add_reverb(stereo(norm(x, 0.5), 0.3, pan=(rng.random() - 0.5) * 0.3), wet=0.12, seconds=0.6)


def fx_tick(rng, tock=False):
    d = 0.12
    f = 2400 if tock else 3100
    burst = rng.standard_normal(int(0.0015 * SR))
    x = resonator(pad(burst, d), f + rng.random() * 80, 30) * 2.0
    x += resonator(pad(burst, d), f * 2.31, 40) * 0.8
    x += modes(d, [900], [0.01], [0.15], rng)
    return add_reverb(stereo(norm(x, 0.6), 0.2), wet=0.18, seconds=0.9)


def fx_pop(rng):
    d = 0.16
    t = t_axis(d)
    f = 520 + 600 * np.exp(-t / 0.018)
    ph = 2 * np.pi * np.cumsum(f) / SR
    x = np.sin(ph) * env_exp(d, 0.045, 0.002)
    x += bandpass(rng.standard_normal(len(t)), 3000, 8000) * env_exp(d, 0.003) * 0.15
    return add_reverb(stereo(norm(x, 0.55), 0.3), wet=0.15, seconds=0.8)


def fx_pin(rng):
    d = 0.45
    t = t_axis(d)
    f = 380 + 1200 * np.exp(-t / 0.05)
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * env_exp(d, 0.08) * 0.6
    x += modes(d, [95], [0.12], [0.9], rng)
    return add_reverb(stereo(norm(x, 0.7), 0.3), wet=0.2, seconds=1.2)


def fx_hit(rng):
    d = 2.6
    t = t_axis(d)
    f = 42 + 50 * np.exp(-t / 0.08)
    sub = np.sin(2 * np.pi * np.cumsum(f) / SR) * env_exp(d, 0.7, 0.003)
    sub = np.tanh(sub * 2.2) / np.tanh(2.2)
    air = lowpass(rng.standard_normal(len(t)), 1800) * env_exp(d, 0.09) * 0.5
    crack = bandpass(rng.standard_normal(len(t)), 1500, 7000) * env_exp(d, 0.012) * 0.4
    x = mix(sub, air, crack)
    return add_reverb(stereo(norm(x, 0.95), 0.5), wet=0.3, seconds=3.0)


def fx_knock(rng):
    out = np.zeros(int(1.2 * SR))
    for i, at in enumerate([0.0, 0.21, 0.4]):
        d = 0.35
        x = modes(d, [150, 330, 620, 980], [0.05, 0.03, 0.018, 0.01], [1.0, 0.6, 0.35, 0.2], rng, detune=0.04)
        x += lowpass(rng.standard_normal(int(d * SR)), 2500) * env_exp(d, 0.006) * 0.8
        x *= 0.9 + 0.2 * rng.random()
        k = int(at * SR)
        out[k : k + len(x)] += x
    return add_reverb(stereo(norm(out, 0.9), 0.4), wet=0.35, seconds=1.4, damp=0.7)


def fx_siren(rng):
    d = 3.2
    t = t_axis(d)
    f = 760 + 220 * (0.5 + 0.5 * np.sign(np.sin(2 * np.pi * 1.1 * t)))
    f = lowpass(f, 12)
    ph = 2 * np.pi * np.cumsum(f) / SR
    x = (np.sin(ph) + 0.35 * np.sin(2 * ph) + 0.15 * np.sin(3 * ph)) * 0.5
    x = bandpass(x, 400, 2500)
    e = np.clip(t / 0.8, 0, 1) * np.clip((d - t) / 1.2, 0, 1)
    x *= e
    st = stereo(norm(x, 0.5), 0.6, pan=0.25)
    return add_reverb(st, wet=0.6, seconds=3.0, damp=0.8)


def fx_stop(rng):
    d = 1.4
    clunk = modes(d, [110, 260, 780, 1430], [0.18, 0.08, 0.03, 0.02], [1, 0.6, 0.3, 0.2], rng)
    click = bandpass(rng.standard_normal(int(0.01 * SR)), 1000, 6000) * 0.6
    x = mix(clunk, click)
    return add_reverb(stereo(norm(x, 0.85), 0.3), wet=0.35, seconds=2.4)


def fx_gavel(rng):
    d = 1.8
    wood = modes(d, [230, 510, 960, 1650, 2700], [0.07, 0.04, 0.025, 0.012, 0.008], [1, 0.7, 0.45, 0.25, 0.12], rng, detune=0.03)
    t = t_axis(d)
    f = 55 + 60 * np.exp(-t / 0.04)
    thump = np.sin(2 * np.pi * np.cumsum(f) / SR) * env_exp(d, 0.22, 0.001) * 1.2
    crack = bandpass(rng.standard_normal(len(t)), 1200, 8000) * env_exp(d, 0.008) * 1.2
    x = np.tanh(mix(wood, thump, crack) * 1.4)
    return add_reverb(stereo(norm(x, 0.98), 0.4), wet=0.32, seconds=2.8, damp=0.5)


def fx_boom(rng):
    d = 5.0
    t = t_axis(d)
    f = 34 + 40 * np.exp(-t / 0.12)
    sub = np.sin(2 * np.pi * np.cumsum(f) / SR) * env_exp(d, 1.4, 0.004)
    sub = np.tanh(sub * 1.8) / np.tanh(1.8)
    rumble = lowpass(rng.standard_normal(len(t)), 220) * env_exp(d, 0.9, 0.01) * 1.5
    air = bandpass(rng.standard_normal(len(t)), 300, 3000) * env_exp(d, 0.25, 0.002) * 0.25
    x = mix(sub, rumble, air)
    return add_reverb(stereo(norm(x, 0.95), 0.6), wet=0.35, seconds=4.5, damp=0.7)


def fx_whoosh(rng, dur=0.9, rise=True):
    t = t_axis(dur)
    n = rng.standard_normal(len(t))
    p = t / dur
    fc = 300 * (12 ** (p if rise else 1 - p))
    # time-varying band-pass via short blocks
    y = np.zeros_like(n)
    blk = 512
    zi = None
    for i in range(0, len(n), blk):
        c = float(fc[i])
        sos = signal.butter(2, [c * 0.6, min(c * 1.6, SR / 2 - 100)], btype='band', fs=SR, output='sos')
        if zi is None:
            zi = signal.sosfilt_zi(sos) * 0
        y[i : i + blk], zi = signal.sosfilt(sos, n[i : i + blk], zi=zi)
    e = np.sin(np.pi * p) ** 1.6
    st = stereo(norm(y * e, 0.6), 0.8)
    # pan sweep
    pan = (p - 0.5) * 1.2
    st[:, 0] *= np.cos((pan + 1) * np.pi / 4) * 1.414
    st[:, 1] *= np.sin((pan + 1) * np.pi / 4) * 1.414
    return add_reverb(st, wet=0.25, seconds=1.5)


def fx_paper(rng):
    d = 0.7
    t = t_axis(d)
    n = bandpass(rng.standard_normal(len(t)), 1800, 9000)
    am = np.zeros_like(t)
    for _ in range(14):
        c = rng.uniform(0.02, 0.55)
        am += np.exp(-((t - c) ** 2) / (2 * rng.uniform(0.004, 0.02) ** 2)) * rng.uniform(0.3, 1)
    x = n * am * np.clip((d - t) / 0.2, 0, 1)
    return add_reverb(stereo(norm(x, 0.45), 0.6), wet=0.2, seconds=0.9)


def fx_stamp(rng):
    d = 0.9
    t = t_axis(d)
    f = 70 + 90 * np.exp(-t / 0.03)
    thump = np.sin(2 * np.pi * np.cumsum(f) / SR) * env_exp(d, 0.09, 0.001)
    slap = bandpass(rng.standard_normal(len(t)), 500, 5000) * env_exp(d, 0.02) * 0.9
    x = mix(thump, slap)
    return add_reverb(stereo(norm(x, 0.95), 0.3), wet=0.22, seconds=1.4)


def fx_buzz(rng):
    d = 0.42
    t = t_axis(d)
    out = np.zeros_like(t)
    for at, f in [(0.0, 330), (0.11, 247)]:
        k = int(at * SR)
        tt = t[: len(t) - k]
        tone = signal.sawtooth(2 * np.pi * f * tt) * np.exp(-tt / 0.07) * np.clip(tt / 0.004, 0, 1)
        out[k:] += lowpass(tone, 1800) * 0.5
    out += modes(d, [80], [0.06], [0.6], rng)
    return add_reverb(stereo(norm(out, 0.5), 0.3), wet=0.15, seconds=0.8)


def fx_rewind(rng):
    d = 3.6
    t = t_axis(d)
    p = t / d
    f = 1800 * (0.12 ** p) + 60 * np.sin(2 * np.pi * 13 * t)
    tone = np.sin(2 * np.pi * np.cumsum(f) / SR) * 0.25
    n = bandpass(rng.standard_normal(len(t)), 600, 6000) * (0.5 + 0.5 * np.sin(2 * np.pi * 23 * t))
    x = (tone + n * 0.35) * np.sin(np.pi * p) ** 0.8
    return add_reverb(stereo(norm(x, 0.5), 0.7), wet=0.35, seconds=2.0)


def fx_boil(rng, dur=6.0):
    t = t_axis(dur)
    bed = lowpass(rng.standard_normal(len(t)), 500) * 0.25
    x = bed.copy()
    nb = int(dur * 22)
    for _ in range(nb):
        at = rng.uniform(0, dur - 0.1)
        bd = rng.uniform(0.02, 0.06)
        tt = t_axis(bd)
        f0 = rng.uniform(300, 900)
        f = f0 * (1 + 2.5 * tt / bd)
        b = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.sin(np.pi * tt / bd) * rng.uniform(0.2, 0.6)
        k = int(at * SR)
        x[k : k + len(b)] += b
    e = np.clip(t / 0.8, 0, 1) * np.clip((dur - t) / 1.0, 0, 1)
    return add_reverb(stereo(norm(x * e, 0.5), 0.8), wet=0.25, seconds=1.2)


def fx_splash(rng):
    d = 1.4
    t = t_axis(d)
    n = rng.standard_normal(len(t))
    x = bandpass(n, 300, 3500) * env_exp(d, 0.18, 0.01)
    x += lowpass(n, 300) * env_exp(d, 0.1) * 0.5
    for _ in range(30):
        at = rng.uniform(0.05, 0.9)
        bd = rng.uniform(0.015, 0.04)
        tt = t_axis(bd)
        f = rng.uniform(500, 1500) * (1 + 2 * tt / bd)
        b = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.sin(np.pi * tt / bd) * 0.2
        k = int(at * SR)
        x[k : k + len(b)] += b
    return add_reverb(stereo(norm(x, 0.6), 0.7), wet=0.3, seconds=1.5)


def fx_thud(rng):
    d = 0.8
    t = t_axis(d)
    f = 60 + 70 * np.exp(-t / 0.025)
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * env_exp(d, 0.12, 0.001)
    x += lowpass(rng.standard_normal(len(t)), 1200) * env_exp(d, 0.012) * 0.5
    return add_reverb(stereo(norm(x, 0.9), 0.3), wet=0.25, seconds=1.6)


def fx_scribble(rng):
    d = 0.22
    t = t_axis(d)
    n = bandpass(rng.standard_normal(len(t)), 2500, 9000)
    am = 0.5 + 0.5 * np.sin(2 * np.pi * rng.uniform(25, 45) * t + rng.random() * 6)
    x = n * am * np.sin(np.pi * t / d)
    return stereo(norm(x, 0.35), 0.3, pan=(rng.random() - 0.5) * 0.4)


def fx_riser(rng, dur=2.6):
    t = t_axis(dur)
    p = t / dur
    f = 90 * (14 ** p)
    tone = (np.sin(2 * np.pi * np.cumsum(f) / SR) + 0.5 * np.sin(2 * np.pi * np.cumsum(f * 1.5) / SR)) * 0.25
    n = highpass(rng.standard_normal(len(t)), 800) * 0.4
    n = lowpass(n, 9000)
    x = (tone + n * p) * (p ** 2.2)
    x[-int(0.01 * SR):] *= np.linspace(1, 0, int(0.01 * SR))
    return add_reverb(stereo(norm(x, 0.8), 0.8), wet=0.2, seconds=1.5)


def fx_bell(rng):
    d = 9.0
    f0 = 196.0
    partials = [0.5, 1.0, 1.183, 1.506, 2.0, 2.514, 2.662, 3.011, 4.166]
    amps = [0.55, 1.0, 0.7, 0.45, 0.6, 0.25, 0.2, 0.18, 0.1]
    decs = [4.5, 3.6, 2.8, 2.2, 2.0, 1.4, 1.2, 1.0, 0.7]
    x = modes(d, [f0 * p for p in partials], decs, amps, rng, detune=0.002)
    t = t_axis(d)
    x *= np.clip(t / 0.003, 0, 1)
    x += bandpass(rng.standard_normal(len(t)), 800, 5000) * env_exp(d, 0.01) * 0.3
    st = stereo(norm(x, 0.7), 0.5)
    return add_reverb(st, wet=0.45, seconds=5.0, damp=0.6)


def fx_heartbeat(rng):
    out = np.zeros(int(1.0 * SR))
    for at, a in [(0.0, 1.0), (0.24, 0.7)]:
        d = 0.35
        t = t_axis(d)
        f = 48 + 30 * np.exp(-t / 0.03)
        x = np.sin(2 * np.pi * np.cumsum(f) / SR) * env_exp(d, 0.09, 0.004) * a
        k = int(at * SR)
        out[k : k + len(x)] += x
    out = lowpass(out, 180)
    return stereo(norm(out, 0.9), 0.0)


def fx_shutter(rng):
    d = 0.3
    x = np.zeros(int(d * SR))
    for at in [0.0, 0.06]:
        c = bandpass(rng.standard_normal(int(0.012 * SR)), 1500, 9000) * env_exp(0.012, 0.004)
        k = int(at * SR)
        x[k : k + len(c)] += c
    x += modes(d, [700, 1900], [0.02, 0.01], [0.3, 0.2], rng)
    return add_reverb(stereo(norm(x, 0.5), 0.3), wet=0.15, seconds=0.7)


def fx_chime(rng):
    d = 3.0
    base = 880
    x = modes(d, [base, base * 2.76, base * 5.4, base * 1.5], [1.4, 0.6, 0.3, 1.0], [1, 0.3, 0.12, 0.5], rng, detune=0.003)
    t = t_axis(d)
    x *= np.clip(t / 0.002, 0, 1)
    return add_reverb(stereo(norm(x, 0.4), 0.5), wet=0.45, seconds=3.0)


def fx_swell(rng, dur=2.4):
    t = t_axis(dur)
    p = t / dur
    n = highpass(rng.standard_normal(len(t)), 2500) * 0.5 + bandpass(rng.standard_normal(len(t)), 400, 2500) * 0.3
    x = n * (p ** 3)
    x[-int(0.02 * SR):] *= np.linspace(1, 0, int(0.02 * SR))
    return add_reverb(stereo(norm(x, 0.5), 0.9), wet=0.3, seconds=2.0)


def fx_door(rng):
    """Heavy metal cell door slam."""
    d = 3.5
    x = modes(d, [61, 143, 287, 455, 812, 1311, 2240], [0.9, 0.7, 0.5, 0.35, 0.25, 0.15, 0.08], [1, 0.8, 0.6, 0.45, 0.3, 0.2, 0.12], rng, detune=0.02)
    t = t_axis(d)
    x *= np.clip(t / 0.002, 0, 1)
    x += lowpass(rng.standard_normal(len(t)), 3000) * env_exp(d, 0.03) * 0.8
    x = np.tanh(x * 1.5)
    return add_reverb(stereo(norm(x, 0.9), 0.5), wet=0.45, seconds=3.5, damp=0.4)


def fx_light(rng):
    """Light switching off: relay click + low hum release."""
    d = 0.6
    x = bandpass(rng.standard_normal(int(0.006 * SR)), 1500, 7000)
    x = pad(x, d)
    t = t_axis(d)
    x += np.sin(2 * np.pi * 100 * t) * np.exp(-t / 0.12) * 0.12
    return add_reverb(stereo(norm(x, 0.4), 0.3), wet=0.2, seconds=1.0)


EFFECTS = {
    'key': (fx_key, 12),
    'tick': (fx_tick, 2),
    'pop': (fx_pop, 4),
    'pin': (fx_pin, 1),
    'hit': (fx_hit, 1),
    'knock': (fx_knock, 1),
    'siren': (fx_siren, 1),
    'stop': (fx_stop, 1),
    'gavel': (fx_gavel, 2),
    'boom': (fx_boom, 2),
    'whoosh': (fx_whoosh, 3),
    'paper': (fx_paper, 4),
    'stamp': (fx_stamp, 3),
    'buzz': (fx_buzz, 1),
    'rewind': (fx_rewind, 1),
    'boil': (fx_boil, 1),
    'splash': (fx_splash, 1),
    'thud': (fx_thud, 4),
    'scribble': (fx_scribble, 8),
    'riser': (fx_riser, 1),
    'bell': (fx_bell, 1),
    'heartbeat': (fx_heartbeat, 1),
    'shutter': (fx_shutter, 2),
    'chime': (fx_chime, 2),
    'swell': (fx_swell, 1),
    'door': (fx_door, 1),
    'light': (fx_light, 4),
}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    index = {}
    for name, (fn, nvar) in EFFECTS.items():
        files = []
        for v in range(nvar):
            rng = np.random.default_rng(1000 + v * 17 + zlib.crc32(name.encode()) % 1000)
            kw = {}
            if name == 'tick':
                kw['tock'] = v == 1
            x = fn(rng, **kw)
            x = highpass(x.T, 25).T  # remove DC / sub-sonic rumble
            x = (x / (np.max(np.abs(x)) + 1e-9) * 0.89).astype(np.float32)  # peak -1 dBFS
            f = OUT / f'{name}_{v}.wav'
            sf.write(f, x, SR, subtype='FLOAT')
            files.append(f.name)
        index[name] = files
        print(f'{name:10s} {nvar} variant(s)  {len(x) / SR:.2f}s')
    (OUT / 'index.json').write_text(json.dumps(index, indent=1))


if __name__ == '__main__':
    main()
