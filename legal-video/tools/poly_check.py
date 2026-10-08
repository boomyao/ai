"""Decide how the TTS actually pronounced a polyphonic character.

For each probe we re-synthesize the line with the character replaced by
unambiguous homophones of each candidate reading, then compare log-mel
spectrograms (DTW) around the word. The closest variant is the reading used.

  python3 tools/poly_check.py
"""
import asyncio
import json
import os
import ssl
import subprocess
import tempfile
from pathlib import Path

import edge_tts
import edge_tts.communicate as comm_mod
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
VO = json.loads((ROOT / 'build' / 'vo.json').read_text(encoding='utf-8'))
comm_mod._SSL_CTX = ssl.create_default_context(cafile='/root/.ccr/ca-bundle.crt')
VOICE = 'zh-CN-YunjianNeural'
SR = 16000

# (line id, word as it appears in the say text, {reading: replacement word})
PROBES = [
    ('t01', '宁可', {'ning4': '佞可', 'ning2': '柠可'}),
    ('e26', '宁可', {'ning4': '佞可', 'ning2': '柠可'}),
    ('w01', '宁可', {'ning4': '佞可', 'ning2': '柠可'}),
    ('k05', '口供', {'gong4': '口贡', 'gong1': '口工'}),
    ('k13', '口供', {'gong4': '口贡', 'gong1': '口工'}),
    ('k20', '口供', {'gong4': '口贡', 'gong1': '口工'}),
    ('c18', '当成', {'dang4': '荡成', 'dang1': '裆成'}),
    ('h07', '血型', {'xue4': '谑型', 'xie3': '写型'}),
]


async def synth(text, rate):
    c = edge_tts.Communicate(text, VOICE, rate=rate, proxy=os.environ.get('HTTPS_PROXY'), boundary='WordBoundary')
    audio = b''
    words = []
    async for ch in c.stream():
        if ch['type'] == 'audio':
            audio += ch['data']
        elif ch['type'] == 'WordBoundary':
            s = ch['offset'] / 1e7
            words.append((s, s + ch['duration'] / 1e7, ch['text']))
    with tempfile.NamedTemporaryFile(suffix='.mp3') as f:
        f.write(audio)
        f.flush()
        raw = subprocess.run(
            ['ffmpeg', '-v', 'error', '-i', f.name, '-ac', '1', '-ar', str(SR), '-f', 'f32le', '-'],
            check=True,
            capture_output=True,
        ).stdout
    return np.frombuffer(raw, dtype=np.float32), words


def logmel(x):
    n_fft, hop = 512, 160
    win = np.hanning(n_fft)
    frames = [x[i : i + n_fft] * win for i in range(0, len(x) - n_fft, hop)]
    if not frames:
        return np.zeros((1, 40))
    spec = np.abs(np.fft.rfft(np.array(frames), axis=1)) ** 2
    fmax = SR / 2
    mel = lambda f: 2595 * np.log10(1 + f / 700)
    imel = lambda m: 700 * (10 ** (m / 2595) - 1)
    pts = imel(np.linspace(mel(60), mel(fmax), 42))
    bins = np.floor((n_fft + 1) * pts / SR).astype(int)
    fb = np.zeros((40, spec.shape[1]))
    for m in range(1, 41):
        a, b, c = bins[m - 1], bins[m], bins[m + 1]
        for k in range(a, b):
            fb[m - 1, k] = (k - a) / max(1, b - a)
        for k in range(b, c):
            fb[m - 1, k] = (c - k) / max(1, c - b)
    out = np.log(spec @ fb.T + 1e-8)
    return out - out.mean(axis=0)


def dtw(a, b):
    n, m = len(a), len(b)
    cost = np.sqrt(((a[:, None, :] - b[None, :, :]) ** 2).sum(-1))
    D = np.full((n + 1, m + 1), np.inf)
    D[0, 0] = 0
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            D[i, j] = cost[i - 1, j - 1] + min(D[i - 1, j], D[i, j - 1], D[i - 1, j - 1])
    return D[n, m] / (n + m)


def window(x, words, target, pad=0.25):
    # find the token span covering the target word's characters
    joined = ''
    spans = []
    for s, e, t in words:
        spans.append((len(joined), len(joined) + len(t), s, e))
        joined += t
    i = joined.find(target)
    if i < 0:
        return x
    cover = [sp for sp in spans if sp[1] > i and sp[0] < i + len(target)]
    s, e = cover[0][2] - pad, cover[-1][3] + pad
    return x[max(0, int(s * SR)) : int(e * SR)]


async def main():
    for lid, word, variants in PROBES:
        v = VO[lid]
        base_text = v['say']
        x0, w0 = await synth(base_text, v['rate'])
        seg0 = logmel(window(x0, w0, word))
        scores = {}
        for reading, rep in variants.items():
            xv, wv = await synth(base_text.replace(word, rep, 1), v['rate'])
            scores[reading] = dtw(seg0, logmel(window(xv, wv, rep)))
        best = min(scores, key=scores.get)
        detail = '  '.join(f'{k}={s:.3f}' for k, s in scores.items())
        print(f'{lid} {word}: TTS reads as {best}   ({detail})')


if __name__ == "__main__":
    asyncio.run(main())
