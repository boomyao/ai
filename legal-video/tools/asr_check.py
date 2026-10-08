"""Transcribe every synthesized line with a local Paraformer model and flag
lines whose recognized pinyin differs from the intended reading.

  python3 tools/asr_check.py [ids...]
"""
import difflib
import json
import re
import sys
from pathlib import Path

import numpy as np
import sherpa_onnx
import soundfile as sf
from pypinyin import Style, lazy_pinyin

ROOT = Path(__file__).resolve().parent.parent
MODEL = ROOT / 'assets' / 'asr' / 'sherpa-onnx-paraformer-zh-2024-03-09'
VO = json.loads((ROOT / 'build' / 'vo.json').read_text(encoding='utf-8'))

CN_NUM = str.maketrans('0123456789', '零一二三四五六七八九')


def norm(s):
    s = s.translate(CN_NUM)
    return re.sub(r'[^一-鿿]', '', s)


def py(s):
    return lazy_pinyin(s, style=Style.TONE3, neutral_tone_with_five=True)


def main():
    rec = sherpa_onnx.OfflineRecognizer.from_paraformer(
        paraformer=str(MODEL / 'model.int8.onnx'), tokens=str(MODEL / 'tokens.txt'), num_threads=4
    )
    ids = sys.argv[1:] or list(VO)
    report = []
    bad = 0
    for lid in ids:
        v = VO[lid]
        x, sr = sf.read(ROOT / v['file'], dtype='float32')
        if sr != 16000:
            n = int(len(x) * 16000 / sr)
            x = np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x).astype(np.float32)
        st = rec.create_stream()
        st.accept_waveform(16000, x)
        rec.decode_stream(st)
        hyp = norm(st.result.text)
        ref = norm(v['say'])
        a, b = py(ref), py(hyp)
        sm = difflib.SequenceMatcher(a=a, b=b, autojunk=False)
        diffs = []
        for op, i1, i2, j1, j2 in sm.get_opcodes():
            if op != 'equal':
                diffs.append(f"{op}: {ref[i1:i2]}({' '.join(a[i1:i2])}) -> {hyp[j1:j2]}({' '.join(b[j1:j2])})")
        flag = '!!' if diffs else 'ok'
        if diffs:
            bad += 1
        report.append({'id': lid, 'ref': ref, 'hyp': hyp, 'diffs': diffs})
        print(f'{flag} {lid}: {hyp}')
        for d in diffs:
            print('     ', d)
    (ROOT / 'build' / 'asr_report.json').write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding='utf-8')
    print(f'{bad}/{len(ids)} lines with differences')


if __name__ == '__main__':
    main()
