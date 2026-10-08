"""Synthesize every narration line with edge-tts and record word timings.

  python3 tools/tts.py            # synthesize missing lines (cached by content hash)
  python3 tools/tts.py --force    # re-synthesize everything

Outputs build/vo/<hash>.wav (48 kHz mono, silence-trimmed) and build/vo.json:
  { id: { file, dur, words: [[start, end, token], ...], text, say } }
"""
import asyncio
import hashlib
import json
import os
import ssl
import subprocess
import sys
from pathlib import Path

import edge_tts
import edge_tts.communicate as comm_mod
import numpy as np
import soundfile as sf

ROOT = Path(__file__).resolve().parent.parent
LINES = ROOT / 'build' / 'lines.json'
VO_DIR = ROOT / 'build' / 'vo'
OUT = ROOT / 'build' / 'vo.json'

VOICE = 'zh-CN-YunjianNeural'
PITCH = '+0Hz'
SR = 48000
CA = '/root/.ccr/ca-bundle.crt'
if os.path.exists(CA):
    comm_mod._SSL_CTX = ssl.create_default_context(cafile=CA)


def key_for(say, rate):
    h = hashlib.sha1(f'{VOICE}|{rate}|{PITCH}|{say}'.encode()).hexdigest()[:16]
    return h


async def synth(say, rate, mp3_path):
    for attempt in range(5):
        try:
            c = edge_tts.Communicate(
                say, VOICE, rate=rate, pitch=PITCH, proxy=os.environ.get('HTTPS_PROXY'), boundary='WordBoundary'
            )
            words = []
            with open(mp3_path, 'wb') as f:
                async for ch in c.stream():
                    if ch['type'] == 'audio':
                        f.write(ch['data'])
                    elif ch['type'] == 'WordBoundary':
                        s = ch['offset'] / 1e7
                        words.append([s, s + ch['duration'] / 1e7, ch['text']])
            return words
        except Exception as e:  # network hiccups
            print('  retry', attempt + 1, repr(e)[:120])
            await asyncio.sleep(2 ** attempt)
    raise RuntimeError(f'TTS failed: {say}')


def decode_trim(mp3_path, wav_path):
    raw = subprocess.run(
        ['ffmpeg', '-v', 'error', '-i', str(mp3_path), '-ac', '1', '-ar', str(SR), '-f', 'f32le', '-'],
        check=True,
        capture_output=True,
    ).stdout
    x = np.frombuffer(raw, dtype=np.float32).copy()
    win = int(0.01 * SR)
    n = len(x) // win
    rms = np.sqrt(np.mean(x[: n * win].reshape(n, win) ** 2, axis=1) + 1e-12)
    db = 20 * np.log10(rms)
    loud = np.where(db > -42)[0]
    if len(loud) == 0:
        a, b = 0, len(x)
    else:
        a = max(0, loud[0] * win - int(0.03 * SR))
        b = min(len(x), (loud[-1] + 1) * win + int(0.12 * SR))
    y = x[a:b]
    fade = int(0.01 * SR)
    y[:fade] *= np.linspace(0, 1, fade)
    y[-fade:] *= np.linspace(1, 0, fade)
    sf.write(wav_path, y, SR, subtype='FLOAT')
    return a / SR, len(y) / SR


async def main():
    force = '--force' in sys.argv
    scenes = json.loads(LINES.read_text(encoding='utf-8'))
    VO_DIR.mkdir(parents=True, exist_ok=True)
    old = json.loads(OUT.read_text(encoding='utf-8')) if OUT.exists() else {}
    result = {}
    jobs = []
    sem = asyncio.Semaphore(4)

    async def run(line):
        say = line['say'] or line['text']
        rate = line['rate']
        k = key_for(say, rate)
        wav = VO_DIR / f'{k}.wav'
        meta = VO_DIR / f'{k}.json'
        if not force and wav.exists() and meta.exists():
            m = json.loads(meta.read_text(encoding='utf-8'))
        else:
            async with sem:
                mp3 = VO_DIR / f'{k}.mp3'
                words = await synth(say, rate, mp3)
                off, dur = decode_trim(mp3, wav)
                m = {
                    'file': f'build/vo/{k}.wav',
                    'dur': round(dur, 4),
                    'words': [[round(s - off, 4), round(e - off, 4), t] for s, e, t in words],
                    'say': say,
                    'rate': rate,
                }
                meta.write_text(json.dumps(m, ensure_ascii=False), encoding='utf-8')
                mp3.unlink()
                print(f"  {line['id']}: {dur:5.2f}s  {say}")
        m = dict(m)
        m['text'] = line['text']
        result[line['id']] = m

    for s in scenes:
        for line in s['lines']:
            jobs.append(run(line))
    await asyncio.gather(*jobs)
    ordered = {l['id']: result[l['id']] for s in scenes for l in s['lines']}
    OUT.write_text(json.dumps(ordered, ensure_ascii=False, indent=0), encoding='utf-8')
    write_data_js(scenes, ordered)
    tot = sum(v['dur'] for v in ordered.values())
    chars = sum(len(v['text']) for v in ordered.values())
    print(f'{len(ordered)} lines, speech {tot / 60:.2f} min, {chars / tot:.2f} chars/s (incl. punctuation)')
    stale = set(old) - set(ordered)
    if stale:
        print('removed lines:', sorted(stale))


def write_data_js(scenes, vo):
    lines = {}
    for s in scenes:
        for l in s['lines']:
            lines[l['id']] = {'text': l['text'], 'pause': l['pause'], 'scene': s['id']}
    voj = {k: {'file': v['file'], 'dur': v['dur'], 'words': v['words'], 'say': v['say']} for k, v in vo.items()}
    js = 'window.LINES = ' + json.dumps(lines, ensure_ascii=False) + ';\n'
    js += 'window.VO = ' + json.dumps(voj, ensure_ascii=False) + ';\n'
    (ROOT / 'build' / 'data.js').write_text(js, encoding='utf-8')


if __name__ == '__main__':
    if '--data-only' in sys.argv:
        scenes = json.loads(LINES.read_text(encoding='utf-8'))
        write_data_js(scenes, json.loads(OUT.read_text(encoding='utf-8')))
    else:
        asyncio.run(main())
