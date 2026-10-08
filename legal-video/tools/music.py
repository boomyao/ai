"""Original score, composed in code and rendered with a General MIDI SoundFont.

Each music cue on the timeline names a mood; compose(mood, dur) writes notes
for exactly that duration, render() plays them through tinysoundfont, and
mix.py crossfades the cues into one bed.

  python3 tools/music.py demo <mood> [seconds]   # render one mood to build/music_<mood>.wav
"""
import sys
from pathlib import Path

import numpy as np
import soundfile as sf
import tinysoundfont

ROOT = Path(__file__).resolve().parent.parent
SF2 = str(ROOT / 'assets' / 'sf2' / 'MuseScore_General.sf2')
SR = 48000

PROG = {
    'piano': 0,
    'celesta': 8,
    'musicbox': 10,
    'vib': 11,
    'cello': 42,
    'contrabass': 43,
    'trem': 44,
    'pizz': 45,
    'harp': 46,
    'timp': 47,
    'strings': 48,
    'slow': 49,
    'choir': 52,
    'oohs': 53,
    'horn': 60,
    'brass': 61,
    'flute': 73,
    'shaku': 77,
    'pad': 89,
    'bowed': 92,
    'halo': 94,
    'atmos': 99,
    'koto': 107,
    'taiko': 116,
}

# pitch helpers -------------------------------------------------------------
NAMES = {'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11}


def P(name):
    """'D4' → 62, 'Bb2' → 46, 'C#5' → 73."""
    n = NAMES[name[0]]
    i = 1
    while i < len(name) and name[i] in '#b':
        n += 1 if name[i] == '#' else -1
        i += 1
    return n + 12 * (int(name[i:]) + 1)


CHORDS = {
    # name: (bass, [voicing around D3-A3], [upper arpeggio tones])
    'Dm': ('D2', ['D3', 'F3', 'A3'], ['D4', 'F4', 'A4', 'D5']),
    'Bb': ('Bb1', ['D3', 'F3', 'Bb3'], ['Bb3', 'D4', 'F4', 'Bb4']),
    'F': ('F2', ['C3', 'F3', 'A3'], ['C4', 'F4', 'A4', 'C5']),
    'C': ('C2', ['E3', 'G3', 'C4'], ['C4', 'E4', 'G4', 'C5']),
    'Gm': ('G2', ['D3', 'G3', 'Bb3'], ['G3', 'Bb3', 'D4', 'G4']),
    'A': ('A1', ['C#3', 'E3', 'A3'], ['A3', 'C#4', 'E4', 'A4']),
    'Asus': ('A1', ['D3', 'E3', 'A3'], ['A3', 'D4', 'E4', 'A4']),
    'Am': ('A1', ['C3', 'E3', 'A3'], ['A3', 'C4', 'E4', 'A4']),
    'Eb': ('Eb2', ['Eb3', 'G3', 'Bb3'], ['Eb4', 'G4', 'Bb4', 'Eb5']),
    'Cm': ('C2', ['Eb3', 'G3', 'C4'], ['C4', 'Eb4', 'G4', 'C5']),
    'G': ('G1', ['D3', 'G3', 'B3'], ['G3', 'B3', 'D4', 'G4']),
    'D': ('D2', ['D3', 'F#3', 'A3'], ['D4', 'F#4', 'A4', 'D5']),
    'Em': ('E2', ['E3', 'G3', 'B3'], ['E4', 'G4', 'B4', 'E5']),
    'Bm': ('B1', ['D3', 'F#3', 'B3'], ['B3', 'D4', 'F#4', 'B4']),
    'D/F#': ('F#2', ['D3', 'F#3', 'A3'], ['D4', 'F#4', 'A4', 'D5']),
    'Dsus': ('D2', ['D3', 'G3', 'A3'], ['D4', 'G4', 'A4', 'D5']),
    'Fmaj7': ('F2', ['C3', 'E3', 'A3'], ['C4', 'E4', 'F4', 'A4']),
    'Bbmaj7': ('Bb1', ['D3', 'F3', 'A3'], ['Bb3', 'D4', 'F4', 'A4']),
}


class Score:
    def __init__(self, dur, seed=1):
        self.dur = dur
        self.ev = []  # (t, kind, chan, a, b)
        self.chan = {}
        self.rng = np.random.default_rng(seed)

    def inst(self, name, prog, vol=100, pan=64, rev=40, chorus=0):
        ch = len(self.chan)
        if ch >= 9:
            ch += 1  # skip GM drum channel 9
        self.chan[name] = (ch, PROG[prog] if isinstance(prog, str) else prog)
        self.cc(name, 0, 7, vol)
        self.cc(name, 0, 10, pan)
        self.cc(name, 0, 91, rev)
        self.cc(name, 0, 93, chorus)
        self.cc(name, 0, 11, 127)
        return name

    def note(self, name, t, d, pitch, vel):
        if t >= self.dur:
            return
        if isinstance(pitch, str):
            pitch = P(pitch)
        ch = self.chan[name][0]
        vel = int(np.clip(vel, 1, 127))
        self.ev.append((t, 1, ch, pitch, vel))
        self.ev.append((t + d, 0, ch, pitch, 0))

    def cc(self, name, t, ctrl, val):
        ch = self.chan[name][0]
        self.ev.append((t, 2, ch, ctrl, int(np.clip(val, 0, 127))))

    def ramp(self, name, t0, t1, v0, v1, ctrl=11, step=0.05, curve=1.0):
        n = max(1, int((t1 - t0) / step))
        for i in range(n + 1):
            p = i / n
            self.cc(name, t0 + p * (t1 - t0), ctrl, v0 + (v1 - v0) * (p ** curve))


def render(score, tail=4.0, gain=-6.0):
    s = tinysoundfont.Synth(gain=gain, samplerate=SR)
    sfid = s.sfload(SF2, max_voices=256)
    for name, (ch, prog) in score.chan.items():
        s.program_select(ch, sfid, 0, prog)
    # note-offs before note-ons at the same instant, CCs first
    order = {2: 0, 0: 1, 1: 2}
    evs = sorted(score.ev, key=lambda e: (e[0], order[e[1]]))
    total = int((score.dur + tail) * SR)
    out = np.zeros((total, 2), dtype=np.float32)
    pos = 0
    i = 0
    while pos < total:
        nxt = int(evs[i][0] * SR) if i < len(evs) else total
        nxt = min(max(nxt, pos), total)
        if nxt > pos:
            buf = np.frombuffer(s.generate(nxt - pos), dtype=np.float32).reshape(-1, 2)
            out[pos:nxt] = buf
            pos = nxt
        while i < len(evs) and int(evs[i][0] * SR) <= pos:
            t, kind, ch, a, b = evs[i]
            if kind == 1:
                s.noteon(ch, a, b)
            elif kind == 0:
                s.noteoff(ch, a)
            else:
                s.control_change(ch, a, b)
            i += 1
        if i >= len(evs) and pos < total:
            buf = np.frombuffer(s.generate(total - pos), dtype=np.float32).reshape(-1, 2)
            out[pos:] = buf
            pos = total
    return out


# ---------------------------------------------------------------------------
# building blocks


def bars(dur, bar):
    return int(np.ceil(dur / bar))


def pad_layer(sc, name, prog, chords, bar, per, dur, vel=60, octave=0, swell=True):
    """Sustained chord pad, `per` bars per chord."""
    t = 0.0
    k = 0
    while t < dur:
        c = CHORDS[chords[k % len(chords)]]
        d = bar * per
        for p in c[1]:
            sc.note(name, t, d + 0.05, P(p) + 12 * octave, vel)
        t += d
        k += 1


def bass_layer(sc, name, chords, bar, per, dur, vel=70, octave=0, pattern=None):
    t = 0.0
    k = 0
    while t < dur:
        c = CHORDS[chords[k % len(chords)]]
        root = P(c[0]) + 12 * octave
        d = bar * per
        if pattern is None:
            sc.note(name, t, d, root, vel)
        else:
            for off, ln, v in pattern(bar, per):
                sc.note(name, t + off, ln, root, vel * v)
        t += d
        k += 1


def arp_layer(sc, name, chords, bar, per, dur, step, order, vel=58, octave=0, humanize=0.012, start=0.0, accent=1.18):
    t = start
    k = int(start // (bar * per))
    while t < dur:
        c = CHORDS[chords[k % len(chords)]]
        tones = [P(p) + 12 * octave for p in c[2]]
        n = int(round(bar * per / step))
        for j in range(n):
            tt = t + j * step
            if tt >= dur:
                break
            p = tones[order[j % len(order)] % len(tones)] + 12 * (order[j % len(order)] // len(tones))
            v = vel * (accent if j % 4 == 0 else 1.0) * (0.92 + 0.16 * sc.rng.random())
            sc.note(name, tt + sc.rng.normal(0, humanize), step * 1.6, p, v)
        t += bar * per
        k += 1


def melody(sc, name, notes, t0, beat, vel=72, transpose=0):
    """notes: list of (pitch|None, beats)."""
    t = t0
    for p, b in notes:
        if p is not None:
            sc.note(name, t, b * beat * 0.98, P(p) + transpose, vel * (0.92 + 0.12 * sc.rng.random()))
        t += b * beat
    return t


THEME = [('A4', 2), ('D5', 1), ('C5', 1), ('A4', 4), ('F4', 2), ('G4', 1), ('A4', 1), ('D4', 4), ('C5', 2), ('F5', 1), ('E5', 1), ('C5', 4), ('E4', 2), ('F4', 1), ('G4', 1), ('A4', 4)]


# ---------------------------------------------------------------------------
# moods


def m_tick(sc, dur):
    sc.inst('bass', 'contrabass', vol=92, rev=60)
    sc.inst('pad', 'atmos', vol=70, rev=90)
    sc.inst('bowed', 'bowed', vol=60, rev=100)
    sc.note('bass', 0.0, dur + 1, 'D1', 64)
    sc.note('pad', 0.0, dur + 1, 'D3', 50)
    sc.note('pad', 0.0, dur + 1, 'A3', 44)
    sc.ramp('pad', 0, min(6, dur), 40, 110)
    sc.note('bowed', dur * 0.45, dur, 'Eb4', 42)
    sc.ramp('bowed', dur * 0.45, dur, 30, 100)


def m_tension(sc, dur):
    sc.inst('low', 'cello', vol=105, rev=40)
    sc.inst('cb', 'contrabass', vol=100, rev=40)
    sc.inst('hi', 'trem', vol=88, rev=70)
    sc.inst('timp', 'timp', vol=110, rev=70)
    step = 0.25
    n = int(dur / step)
    for j in range(n):
        t = j * step
        p = t / dur
        acc = 1.0 if j % 4 == 0 else 0.72
        sc.note('low', t, step * 0.6, 'D2', (62 + 50 * p) * acc)
        if j % 2 == 0:
            sc.note('cb', t, step * 0.8, 'D1', (60 + 50 * p) * acc)
    sc.note('hi', 0, dur * 0.5, 'A4', 50)
    sc.note('hi', dur * 0.5, dur * 0.5 + 0.2, 'Bb4', 58)
    sc.note('hi', dur * 0.7, dur * 0.3 + 0.2, 'E5', 52)
    sc.ramp('hi', 0, dur, 40, 127, curve=1.6)
    for j in range(int(dur)):
        sc.note('timp', j + 0.0, 0.6, 'D2', 50 + 60 * j / dur)
    # final timpani roll
    t = dur - 2.0
    while t < dur - 0.05:
        sc.note('timp', t, 0.1, 'A1', 60 + 50 * (t - (dur - 2)) / 2)
        t += 0.06


def m_drone(sc, dur):
    sc.inst('s', 'slow', vol=88, rev=110)
    sc.inst('cb', 'contrabass', vol=90, rev=80)
    sc.inst('pad', 'halo', vol=72, rev=110)
    for p, v in [('D2', 54), ('A2', 46), ('Eb3', 34)]:
        sc.note('s', 0, dur + 1, p, v)
    sc.note('cb', 0, dur + 1, 'D1', 58)
    sc.note('pad', 0.5, dur, 'D4', 36)
    sc.ramp('s', 0, 3, 30, 100)


def m_ancient(sc, dur):
    bar = 4.0  # 60 bpm, 4/4
    prog = ['Dm', 'Bb', 'Gm', 'A']
    sc.inst('choir', 'choir', vol=92, rev=110)
    sc.inst('s', 'slow', vol=85, rev=100)
    sc.inst('cb', 'contrabass', vol=95, rev=70)
    sc.inst('timp', 'timp', vol=105, rev=90)
    pad_layer(sc, 's', 'slow', prog, bar, 1, dur, vel=52)
    pad_layer(sc, 'choir', 'choir', prog, bar, 1, dur, vel=46, octave=1)
    bass_layer(sc, 'cb', prog, bar, 1, dur, vel=66, octave=0)
    for k in range(bars(dur, bar)):
        sc.note('timp', k * bar, 1.5, 'D2' if k % 4 != 3 else 'A1', 70 if k % 2 == 0 else 55)
        sc.note('timp', k * bar + 2.5, 0.8, 'D2', 40)
    sc.ramp('choir', 0, min(8, dur), 50, 115)


def m_tang(sc, dur):
    bar = 4.0
    sc.inst('koto', 'koto', vol=92, rev=80, pan=50)
    sc.inst('shaku', 'shaku', vol=78, rev=100, pan=78)
    sc.inst('s', 'slow', vol=78, rev=100)
    sc.inst('cb', 'contrabass', vol=88, rev=70)
    sc.note('cb', 0, dur + 1, 'D1', 60)
    sc.note('s', 0, dur + 1, 'D3', 44)
    sc.note('s', 0, dur + 1, 'A3', 40)
    pent = ['D4', 'F4', 'G4', 'A4', 'C5', 'D5']
    pattern = [0, 2, 3, 5, 3, 2, 1, 0, 0, 3, 4, 3]
    t = 0.5
    j = 0
    while t < dur:
        sc.note('koto', t, 0.9, pent[pattern[j % len(pattern)]], 70 + 10 * (j % 3 == 0))
        t += 0.5 if j % 6 != 5 else 1.0
        j += 1
    phr = [('A4', 3), ('G4', 1), ('F4', 2), ('D4', 6), ('C5', 3), ('A4', 1), ('G4', 2), ('A4', 6)]
    t = 2.0
    while t < dur - 2:
        t = melody(sc, 'shaku', phr, t, 0.5, vel=60) + 2.0


def m_theme(sc, dur):
    beat = 60 / 72
    bar = beat * 4
    prog = ['Dm', 'Dm', 'Bb', 'Bb', 'F', 'F', 'C', 'C']
    sc.inst('hit', 'brass', vol=110, rev=70)
    sc.inst('timp', 'timp', vol=120, rev=90)
    sc.inst('s', 'slow', vol=95, rev=100)
    sc.inst('cb', 'contrabass', vol=92, rev=70)
    sc.inst('horn', 'horn', vol=92, rev=100)
    sc.inst('pno', 'piano', vol=96, rev=80)
    # opening hit
    for p in ['D2', 'A2', 'D3', 'F3', 'A3', 'D4']:
        sc.note('hit', 0, 1.6, p, 118)
    for k in range(6):
        sc.note('timp', k * 0.05, 0.3, 'D2', 120 - k * 6)
    pad_layer(sc, 's', 'slow', prog, bar, 1, dur, vel=58)
    sc.ramp('s', 0.6, 4.0, 40, 120)
    bass_layer(sc, 'cb', prog, bar, 1, dur, vel=64)
    t = 2.2
    while t < dur - 4:
        t = melody(sc, 'horn', THEME, t, beat, vel=74) + bar
    arp_layer(sc, 'pno', prog, bar, 1, dur, beat / 2, [0, 1, 2, 1, 3, 1, 2, 1], vel=44, start=bar * 2)


def m_think(sc, dur, major=False):
    beat = 60 / 84
    bar = beat * 4
    prog = ['F', 'C', 'Dm', 'Bb'] if major else ['Dm', 'Bb', 'F', 'C']
    sc.inst('pno', 'piano', vol=100, rev=70)
    sc.inst('s', 'slow', vol=80, rev=100)
    sc.inst('cb', 'contrabass', vol=82, rev=60)
    arp_layer(sc, 'pno', prog, bar, 1, dur, beat / 2, [0, 1, 2, 3, 2, 1, 2, 1], vel=50)
    bass_layer(sc, 'pno', prog, bar, 1, dur, vel=56, octave=1)
    if dur > bar * 4:
        pad_layer(sc, 's', 'slow', prog, bar, 1, dur, vel=42)
        sc.ramp('s', 0, bar * 4, 0, 0, step=1)
        sc.ramp('s', bar * 4, bar * 8, 0, 100)
    bass_layer(sc, 'cb', prog, bar, 1, dur, vel=50)


def m_resolve(sc, dur):
    m_think(sc, dur, major=True)


def m_dark(sc, dur):
    sc.inst('pno', 'piano', vol=96, rev=110)
    sc.inst('s', 'slow', vol=78, rev=110)
    sc.inst('cb', 'contrabass', vol=90, rev=80)
    sc.note('cb', 0, dur + 1, 'D1', 56)
    sc.note('s', 0, dur + 1, 'D3', 36)
    sc.note('s', 0, dur + 1, 'Eb3', 26)
    t = 0.4
    seq = ['D3', 'A2', 'F3', 'E3', 'D3', 'A2', 'C3', 'Bb2']
    j = 0
    while t < dur:
        sc.note('pno', t, 3.0, seq[j % len(seq)], 52 if j % 2 == 0 else 44)
        t += 1.8
        j += 1


def m_light(sc, dur):
    beat = 60 / 96
    bar = beat * 4
    prog = ['F', 'Bb', 'F', 'C']
    sc.inst('pizz', 'pizz', vol=100, rev=60)
    sc.inst('cel', 'celesta', vol=80, rev=80)
    sc.inst('cb', 'pizz', vol=95, rev=50)
    arp_layer(sc, 'pizz', prog, bar, 1, dur, beat / 2, [0, 2, 1, 2, 3, 2, 1, 2], vel=56, octave=0, humanize=0.006)
    bass_layer(sc, 'cb', prog, bar, 1, dur, vel=70, octave=1, pattern=lambda b, per: [(0, b / 4, 1.0), (b / 2, b / 4, 0.8)])
    mel = [('C5', 1), ('A4', 1), ('F4', 2), ('Bb4', 1), ('D5', 1), ('F5', 2), ('A4', 1), ('C5', 1), ('F5', 2), ('E5', 2), ('C5', 2)]
    t = bar
    while t < dur - bar:
        t = melody(sc, 'cel', mel, t, beat, vel=54) + bar


def m_law(sc, dur):
    beat = 60 / 64
    bar = beat * 4
    prog = ['Bb', 'F', 'C', 'Dm']
    sc.inst('s', 'slow', vol=92, rev=100)
    sc.inst('horn', 'horn', vol=80, rev=100)
    sc.inst('cb', 'contrabass', vol=86, rev=70)
    pad_layer(sc, 's', 'slow', prog, bar, 1, dur, vel=56)
    pad_layer(sc, 'horn', 'horn', prog, bar, 2, dur, vel=40, octave=0)
    bass_layer(sc, 'cb', prog, bar, 1, dur, vel=58)
    sc.ramp('s', 0, 2.5, 50, 115)


def m_interrogation(sc, dur):
    beat = 60 / 70
    sc.inst('cb', 'pizz', vol=100, rev=60)
    sc.inst('hi', 'trem', vol=70, rev=100)
    sc.inst('cel', 'celesta', vol=60, rev=100)
    sc.inst('low', 'slow', vol=80, rev=100)
    t = 0.0
    j = 0
    while t < dur:
        sc.note('cb', t, 0.3, 'D2' if j % 8 != 7 else 'Eb2', 76 if j % 4 == 0 else 58)
        t += beat
        j += 1
    sc.note('hi', 0, dur + 1, 'A5', 40)
    sc.note('hi', dur * 0.5, dur * 0.5 + 1, 'Bb5', 36)
    sc.ramp('hi', 0, dur, 50, 110)
    sc.note('low', 0, dur + 1, 'D2', 48)
    sc.note('low', 0, dur + 1, 'Ab2', 34)
    t = 1.0
    while t < dur:
        sc.note('cel', t, 0.4, 'A6', 30)
        t += beat * 2


def m_insight(sc, dur):
    beat = 60 / 78
    bar = beat * 4
    prog = ['Dm', 'Bb', 'Gm', 'A', 'Dm', 'Bb', 'F', 'C']
    sc.inst('pno', 'piano', vol=100, rev=80)
    sc.inst('s', 'slow', vol=84, rev=100)
    sc.inst('cb', 'contrabass', vol=82, rev=70)
    arp_layer(sc, 'pno', prog, bar, 1, dur, beat / 2, [0, 2, 1, 2, 3, 2, 1, 2], vel=48)
    pad_layer(sc, 's', 'slow', prog, bar, 1, dur, vel=46)
    bass_layer(sc, 'cb', prog, bar, 1, dur, vel=54)


ELEGY = [('A4', 3), ('G4', 1), ('F4', 2), ('E4', 2), ('D4', 6), (None, 2), ('F4', 3), ('E4', 1), ('D4', 2), ('C4', 2), ('A3', 6), (None, 2)]


def m_elegy(sc, dur):
    beat = 60 / 56
    bar = beat * 4
    prog = ['Dm', 'Bb', 'Gm', 'Asus', 'Dm', 'Bb', 'F', 'A']
    sc.inst('pno', 'piano', vol=104, rev=100)
    sc.inst('s', 'slow', vol=76, rev=110)
    arp_layer(sc, 'pno', prog, bar, 1, dur, beat, [0, 1, 2, 1], vel=40, octave=-1, humanize=0.02, accent=1.25)
    t = bar * 2
    while t < dur - bar:
        t = melody(sc, 'pno', ELEGY, t, beat, vel=58, transpose=0) + bar
    if dur > bar * 6:
        pad_layer(sc, 's', 'slow', prog, bar, 1, dur, vel=40)
        sc.ramp('s', 0, bar * 4, 0, 0, step=1)
        sc.ramp('s', bar * 4, bar * 8, 0, 95)


def m_void(sc, dur):
    sc.inst('pad', 'halo', vol=80, rev=120)
    sc.inst('s', 'slow', vol=70, rev=120)
    sc.note('pad', 0, dur + 1, 'D3', 40)
    sc.note('s', 0, dur + 1, 'A5', 26)
    sc.ramp('s', 0, dur, 40, 90)


def m_hope(sc, dur):
    beat = 60 / 70
    bar = beat * 4
    prog = ['Bb', 'F', 'C', 'Dm', 'Bb', 'F', 'Gm', 'Asus', 'Bb', 'F', 'C', 'C', 'G', 'D/F#', 'Em', 'A', 'D', 'D']
    sc.inst('pno', 'piano', vol=100, rev=90)
    sc.inst('s', 'slow', vol=96, rev=100)
    sc.inst('cb', 'contrabass', vol=88, rev=70)
    sc.inst('horn', 'horn', vol=84, rev=100)
    arp_layer(sc, 'pno', prog, bar, 1, dur, beat / 2, [0, 1, 2, 3, 2, 1, 2, 1], vel=46)
    pad_layer(sc, 's', 'slow', prog, bar, 1, dur, vel=54)
    bass_layer(sc, 'cb', prog, bar, 1, dur, vel=60)
    sc.ramp('s', 0, dur, 50, 122, curve=1.4)
    t = bar * 4
    if dur > bar * 6:
        melody(sc, 'horn', THEME, t, beat, vel=64)


def m_outro(sc, dur):
    beat = 60 / 66
    bar = beat * 4
    prog = ['D', 'G', 'D', 'A', 'D']
    sc.inst('pno', 'piano', vol=96, rev=100)
    sc.inst('s', 'slow', vol=80, rev=110)
    arp_layer(sc, 'pno', prog, bar, 1, dur, beat, [0, 1, 2, 3], vel=40, humanize=0.02)
    pad_layer(sc, 's', 'slow', prog, bar, 1, dur, vel=44)
    sc.ramp('s', max(0, dur - 4), dur, 100, 0)
    sc.ramp('pno', max(0, dur - 4), dur, 127, 0)


MOODS = {
    'tick': m_tick,
    'tension': m_tension,
    'drone': m_drone,
    'ancient': m_ancient,
    'tang': m_tang,
    'theme': m_theme,
    'think': m_think,
    'resolve': m_resolve,
    'dark': m_dark,
    'light': m_light,
    'law': m_law,
    'interrogation': m_interrogation,
    'insight': m_insight,
    'elegy': m_elegy,
    'void': m_void,
    'hope': m_hope,
    'outro': m_outro,
}


def compose(mood, dur, seed=1):
    sc = Score(dur, seed)
    MOODS[mood](sc, dur)
    return sc


if __name__ == '__main__':
    if sys.argv[1] == 'demo':
        mood = sys.argv[2]
        dur = float(sys.argv[3]) if len(sys.argv) > 3 else 30
        x = render(compose(mood, dur))
        x = x / (np.abs(x).max() + 1e-9) * 0.89
        f = ROOT / 'build' / f'music_{mood}.wav'
        sf.write(f, x, SR, subtype='FLOAT')
        print(f, f'{len(x) / SR:.1f}s')
