"""Assemble the soundtrack from the timeline cues.

  python3 tools/mix.py [--cues out/cues.json] [--out out/mix.wav] [--to SECONDS]

Voice lines are placed where the scenes put them, sound effects come from
build/sfx, music cues are composed/rendered per segment (tools/music.py) and
cross-faded. Music ducks under the narration; the master is loudness-
normalised and peak-limited.
"""
import argparse
import json
from pathlib import Path

import numpy as np
import pyloudnorm as pyln
import soundfile as sf
from scipy import signal

import music

ROOT = Path(__file__).resolve().parent.parent
SR = 48000

SFX_GAIN_DB = {
    'key': -24,
    'tick': -8,
    'pop': -21,
    'pin': -17,
    'hit': -7,
    'knock': -9,
    'siren': -20,
    'stop': -11,
    'gavel': -4,
    'boom': -6,
    'whoosh': -17,
    'paper': -15,
    'stamp': -9,
    'buzz': -19,
    'rewind': -15,
    'boil': -21,
    'splash': -18,
    'thud': -11,
    'scribble': -23,
    'riser': -10,
    'bell': -9,
    'heartbeat': -9,
    'shutter': -17,
    'chime': -17,
    'swell': -15,
    'door': -8,
    'light': -19,
}
# relative level of each music mood (dB) on top of the common bed level
MOOD_DB = {
    'tick': -2,
    'tension': 0,
    'drone': -2,
    'ancient': -1,
    'tang': -1,
    'theme': 1,
    'think': -1,
    'resolve': -1,
    'dark': -2,
    'light': -2,
    'law': -1,
    'interrogation': -1,
    'insight': -1,
    'elegy': 0,
    'void': -3,
    'hope': 1,
    'outro': 0,
}
VO_LUFS = -17.0
BED_LUFS = -21.0  # music bed level before ducking
DUCK_DB = 8.0
MASTER_LUFS = -15.0


def db(x):
    return 10 ** (x / 20)


def load_mono(path):
    x, sr = sf.read(path, dtype='float32', always_2d=True)
    assert sr == SR, (path, sr)
    return x.mean(axis=1)


def place(buf, x, at):
    i = int(round(at * SR))
    if i >= len(buf):
        return
    if i < 0:
        x = x[-i:]
        i = 0
    n = min(len(x), len(buf) - i)
    buf[i : i + n] += x[:n]


def smooth(env, attack, release):
    """One-pole smoothing with different attack/release (seconds)."""
    a_att = np.exp(-1 / (attack * SR))
    a_rel = np.exp(-1 / (release * SR))
    out = np.empty_like(env)
    y = 0.0
    for i, v in enumerate(env):
        a = a_att if v > y else a_rel
        y = a * y + (1 - a) * v
        out[i] = y
    return out


def smooth_fast(env, attack, release, hop=48):
    """Decimated version of smooth() for long signals."""
    e = env[::hop]
    a_att = np.exp(-hop / (attack * SR))
    a_rel = np.exp(-hop / (release * SR))
    out = np.empty_like(e)
    y = 0.0
    for i, v in enumerate(e):
        a = a_att if v > y else a_rel
        y = a * y + (1 - a) * v
        out[i] = y
    return np.interp(np.arange(len(env)), np.arange(len(e)) * hop, out)


def limiter(x, ceiling_db=-1.5, lookahead=0.005, release=0.08):
    ceil = db(ceiling_db)
    peak = np.max(np.abs(x), axis=1)
    la = int(lookahead * SR)
    # running max over the lookahead window
    from scipy.ndimage import maximum_filter1d

    pk = maximum_filter1d(peak, size=2 * la + 1)
    gain = np.minimum(1.0, ceil / np.maximum(pk, 1e-9))
    # smooth: instant attack (already looked ahead), slow release
    g = 1 - smooth_fast(1 - gain, 0.0005, release)
    g = np.minimum(g, gain)
    return x * g[:, None]


def music_bed(cues, total):
    mcues = sorted([c for c in cues if c['type'] == 'music'], key=lambda c: c['at'])
    bed = np.zeros((int(total * SR), 2), dtype=np.float32)
    meter = pyln.Meter(SR)
    for i, c in enumerate(mcues):
        if c['mood'] == 'silence':
            continue
        start = c['at']
        nxt = mcues[i + 1] if i + 1 < len(mcues) else None
        end = nxt['at'] if nxt else total
        xfade = nxt['fade'] if nxt else 2.0
        seg_dur = end - start + xfade
        sc = music.compose(c['mood'], seg_dur, seed=i + 1)
        x = music.render(sc, tail=3.0 if not nxt else 0.5)
        # loudness-normalise the cue on its main body
        body = x[: int(min(len(x), seg_dur * SR))]
        try:
            lufs = meter.integrated_loudness(body.astype(np.float64))
        except ValueError:
            lufs = -70
        if np.isfinite(lufs) and lufs > -70:
            x = x * db(BED_LUFS + MOOD_DB.get(c['mood'], 0) - lufs) * db(20 * np.log10(max(c.get('gain', 1), 1e-6)))
        n = len(x)
        t = np.arange(n) / SR
        fade_in = max(c['fade'], 0.02)
        env = np.clip(t / fade_in, 0, 1)
        if nxt:
            fo_start = end - start
            env *= np.clip(1 - (t - fo_start) / max(xfade, 0.02), 0, 1)
        else:
            env *= np.clip(1 - (t - (total - start - 3.0)) / 3.0, 0, 1)
        x = x * env[:, None]
        k = int(start * SR)
        m = min(n, len(bed) - k)
        if m > 0:
            bed[k : k + m] += x[:m]
        print(f"  music {c['mood']:14s} {start:7.2f}–{end:7.2f}s")
    return bed


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--cues', default=str(ROOT / 'out' / 'cues.json'))
    ap.add_argument('--out', default=str(ROOT / 'out' / 'mix.wav'))
    ap.add_argument('--to', type=float, default=None)
    a = ap.parse_args()
    info = json.loads(Path(a.cues).read_text(encoding='utf-8'))
    total = info['total'] if a.to is None else min(a.to, info['total'])
    cues = [c for c in info['cues'] if c['at'] < total]
    n = int((total + 0.5) * SR)

    # ---- voice
    vo = np.zeros(n, dtype=np.float32)
    vo_mask = np.zeros(n, dtype=np.float32)
    for c in cues:
        if c['type'] != 'vo':
            continue
        x = load_mono(ROOT / c['file'])
        place(vo, x, c['at'])
        i0 = int(max(0, c['at'] - 0.12) * SR)
        i1 = int(min(total, c['at'] + c['dur'] + 0.25) * SR)
        vo_mask[i0:i1] = 1.0
    sos = signal.butter(2, 75, btype='high', fs=SR, output='sos')
    vo = signal.sosfilt(sos, vo).astype(np.float32)
    meter = pyln.Meter(SR)
    active = vo[vo_mask > 0]
    if len(active) > SR:
        lufs = meter.integrated_loudness(active.astype(np.float64))
        vo *= db(VO_LUFS - lufs)
    vo_st = np.stack([vo, vo], axis=1)

    # ---- sfx
    idx = json.loads((ROOT / 'build' / 'sfx' / 'index.json').read_text())
    cache = {}
    counts = {}
    fx = np.zeros((n, 2), dtype=np.float32)
    for c in cues:
        if c['type'] != 'sfx':
            continue
        name = c['name']
        files = idx[name]
        k = counts.get(name, 0)
        counts[name] = k + 1
        v = c.get('v', k) % len(files)
        f = files[v]
        if f not in cache:
            x, sr = sf.read(ROOT / 'build' / 'sfx' / f, dtype='float32', always_2d=True)
            cache[f] = x
        x = cache[f].copy()
        if c.get('dur'):
            m = int(c['dur'] * SR)
            x = x[:m]
            fl = min(len(x), int(0.6 * SR))
            x[-fl:] *= np.linspace(1, 0, fl)[:, None]
        x *= db(SFX_GAIN_DB.get(name, -15)) * c.get('gain', 1)
        i = int(round(c['at'] * SR))
        if i >= n:
            continue
        m = min(len(x), n - i)
        fx[i : i + m] += x[:m]

    # ---- music
    bed = music_bed(cues, total + 0.5)
    bed = bed[:n]
    if len(bed) < n:
        bed = np.concatenate([bed, np.zeros((n - len(bed), 2), dtype=np.float32)])
    duck = smooth_fast(vo_mask, 0.08, 0.45)
    bed *= db(-DUCK_DB * duck)[:, None]

    master = vo_st + fx + bed
    lufs = meter.integrated_loudness(master.astype(np.float64))
    master *= db(MASTER_LUFS - lufs)
    master = limiter(master, -1.5)
    # final short fades
    f = int(0.02 * SR)
    master[:f] *= np.linspace(0, 1, f)[:, None]
    master[-int(0.5 * SR):] *= np.linspace(1, 0, int(0.5 * SR))[:, None]
    out_lufs = meter.integrated_loudness(master.astype(np.float64))
    sf.write(a.out, master.astype(np.float32), SR, subtype='FLOAT')
    print(f'wrote {a.out}: {len(master) / SR:.1f}s, {out_lufs:.1f} LUFS, peak {20 * np.log10(np.abs(master).max()):.1f} dBFS')
    # stems for inspection
    stem_dir = ROOT / 'out' / 'stems'
    stem_dir.mkdir(exist_ok=True)
    for name, x in [('vo', vo_st), ('sfx', fx), ('music', bed)]:
        sf.write(stem_dir / f'{name}.wav', x.astype(np.float32), SR, subtype='FLOAT')


if __name__ == '__main__':
    main()
