"""Parse script.md into build/lines.json.

Line grammar (see script.md):
  ## sceneId | 标题
  id | 旁白文本 | +0.8 | say=… | rate=-6%
  > visual note (ignored by the voice pipeline, kept for reference)
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'script.md'
OUT = ROOT / 'build' / 'lines.json'

LINE_RE = re.compile(r'^([a-z]+\d+)\s*\|\s*(.+)$')


def parse(text):
    scenes = []
    cur = None
    notes = []
    in_body = False
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith('## 事实核查'):
            break
        m = re.match(r'^##\s+([a-z0-9]+)\s*\|\s*(.+)$', line)
        if m:
            cur = {'id': m.group(1), 'title': m.group(2).strip(), 'lines': []}
            scenes.append(cur)
            in_body = True
            notes = []
            continue
        if not in_body or cur is None:
            continue
        if line.startswith('>'):
            notes.append(line[1:].strip())
            continue
        m = LINE_RE.match(line)
        if not m:
            continue
        lid, rest = m.group(1), m.group(2)
        parts = [p.strip() for p in rest.split(' | ')]
        item = {'id': lid, 'text': parts[0], 'say': None, 'pause': 0.0, 'rate': '+0%', 'notes': notes}
        notes = []
        for p in parts[1:]:
            if re.fullmatch(r'\+\d+(\.\d+)?', p):
                item['pause'] = float(p[1:])
            elif p.startswith('say='):
                item['say'] = p[4:]
            elif p.startswith('rate='):
                item['rate'] = p[5:]
            else:
                raise ValueError(f'unknown option {p!r} in {lid}')
        cur['lines'].append(item)
    return scenes


def main():
    scenes = parse(SRC.read_text(encoding='utf-8'))
    ids = [l['id'] for s in scenes for l in s['lines']]
    dup = {i for i in ids if ids.count(i) > 1}
    if dup:
        sys.exit(f'duplicate ids: {sorted(dup)}')
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(scenes, ensure_ascii=False, indent=1), encoding='utf-8')
    if '--stats' in sys.argv:
        total_chars = 0
        total_est = 0.0
        for s in scenes:
            chars = sum(len(re.sub(r'[\s，。：；？！、“”‘’（）《》—…·,.:;?!]', '', l['text'])) for l in s['lines'])
            pauses = sum(l['pause'] for l in s['lines'])
            est = chars / 4.2 + pauses + 0.25 * len(s['lines'])
            total_chars += chars
            total_est += est
            print(f"{s['id']:6s} {s['title']:14s} lines={len(s['lines']):3d} chars={chars:4d} est={est/60:5.2f} min")
        print(f'TOTAL chars={total_chars} est={total_est/60:.2f} min (+ title/chapter cards)')


if __name__ == '__main__':
    main()
