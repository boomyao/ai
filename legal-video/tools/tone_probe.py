"""Print the F0 contour of a word inside a synthesized line, to check tones of
polyphonic characters that ASR cannot disambiguate.

  python3 tools/tone_probe.py k20:口供 t01:宁可 ...
"""
import json
import sys
from pathlib import Path

import numpy as np
import soundfile as sf

ROOT = Path(__file__).resolve().parent.parent
VO = json.loads((ROOT / 'build' / 'vo.json').read_text(encoding='utf-8'))


def yin_f0(x, sr, t0, t1, hop=0.01, fmin=60, fmax=300):
    out = []
    w = int(0.04 * sr)
    tmin, tmax = int(sr / fmax), int(sr / fmin)
    t = t0
    while t < t1:
        i = int(t * sr)
        seg = x[i : i + w + tmax]
        if len(seg) < w + tmax:
            break
        d = np.array([np.sum((seg[:w] - seg[tau : tau + w]) ** 2) for tau in range(tmax + 1)])
        cmnd = d.copy()
        cmnd[1:] = d[1:] * np.arange(1, tmax + 1) / np.maximum(np.cumsum(d[1:]), 1e-12)
        cmnd[0] = 1
        tau = None
        for k in range(tmin, tmax):
            if cmnd[k] < 0.15 and cmnd[k] < cmnd[k + 1]:
                tau = k
                break
        rms = np.sqrt(np.mean(seg[:w] ** 2))
        out.append((round(t, 2), round(sr / tau, 1) if tau and rms > 0.01 else None))
        t += hop
    return out


def main():
    for arg in sys.argv[1:]:
        lid, word = arg.split(':')
        v = VO[lid]
        x, sr = sf.read(ROOT / v['file'], dtype='float32')
        hits = [w for w in v['words'] if word in w[2] or w[2] in word and len(w[2]) > 1]
        if not hits:
            print(lid, word, 'token not found; tokens:', [w[2] for w in v['words']])
            continue
        s, e, tok = hits[0]
        # locate the target characters inside the token proportionally
        pos = tok.find(word[0]) if word[0] in tok else 0
        n = max(1, len(tok))
        per = (e - s) / n
        print(f'{lid} token={tok} [{s:.2f}-{e:.2f}]')
        for ci, ch in enumerate(tok):
            cs, ce = s + ci * per, s + (ci + 1) * per
            f0 = [f for _, f in yin_f0(x, sr, cs, ce) if f]
            if f0:
                q = np.array(f0)
                k = max(1, len(q) // 3)
                print(f'   {ch}: start {np.median(q[:k]):6.1f}  mid {np.median(q[k:2*k] if len(q) > 2 else q):6.1f}  end {np.median(q[-k:]):6.1f}  (n={len(q)})')
            else:
                print(f'   {ch}: unvoiced')


if __name__ == '__main__':
    main()
