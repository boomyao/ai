"""Scan every narration line for risky polyphonic characters and check, by
re-synthesis, which reading the TTS actually used.

For a character c with expected reading r (from pypinyin's phrase-aware
conversion of the say text), we synthesize the line with c replaced by an
unambiguous homophone for r and for each alternative reading, then compare
log-mel spectrograms around c (DTW). If an alternative is closer than the
expected reading, the line is flagged.

  python3 tools/poly_scan.py [ids...]
"""
import asyncio
import json
import sys
from pathlib import Path

import numpy as np
from pypinyin import Style, pinyin

sys.path.insert(0, str(Path(__file__).resolve().parent))
from poly_check import SR, dtw, logmel, synth  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
VO = json.loads((ROOT / 'build' / 'vo.json').read_text(encoding='utf-8'))

# char -> {reading: unambiguous homophone}
HOMO = {
    '供': {'gong4': '贡', 'gong1': '工'},
    '宁': {'ning4': '佞', 'ning2': '柠'},
    '当': {'dang4': '荡', 'dang1': '裆'},
    '血': {'xue4': '谑', 'xie3': '写'},
    '重': {'zhong4': '众', 'chong2': '虫'},
    '扎': {'za1': '匝', 'zha1': '渣'},
    '还': {'hai2': '孩', 'huan2': '环'},
    '长': {'chang2': '尝', 'zhang3': '掌'},
    '种': {'zhong3': '肿', 'zhong4': '众'},
    '为': {'wei4': '未', 'wei2': '围'},
    '处': {'chu3': '楚', 'chu4': '触'},
    '调': {'diao4': '掉', 'tiao2': '条'},
    '传': {'zhuan4': '撰', 'chuan2': '船'},
    '差': {'cha4': '岔', 'cha1': '插'},
    '担': {'dan4': '淡', 'dan1': '丹'},
    '结': {'jie2': '洁', 'jie1': '接'},
    '落': {'luo4': '洛', 'la4': '腊'},
    '恶': {'e4': '饿', 'wu4': '误'},
    '都': {'dou1': '兜', 'du1': '督'},
    '只': {'zhi3': '纸', 'zhi1': '织'},
    '尽': {'jin4': '进', 'jin3': '紧'},
    '分': {'fen1': '芬', 'fen4': '奋'},
    '间': {'jian1': '坚', 'jian4': '见'},
    '弹': {'dan4': '蛋', 'tan2': '谈'},
    '几': {'ji3': '挤', 'ji1': '机'},
    '应': {'ying1': '英', 'ying4': '硬'},
    '中': {'zhong1': '钟', 'zhong4': '众'},
    '相': {'xiang1': '香', 'xiang4': '象'},
    '将': {'jiang1': '江', 'jiang4': '酱'},
    '正': {'zheng4': '证', 'zheng1': '争'},
    '背': {'bei4': '被', 'bei1': '杯'},
    '和': {'he2': '河', 'huo2': '活', 'he4': '贺'},
    '好': {'hao3': '郝', 'hao4': '号'},
    '数': {'shu4': '树', 'shu3': '鼠'},
    '称': {'cheng1': '撑', 'chen4': '趁'},
    '要': {'yao4': '药', 'yao1': '腰'},
    '朝': {'chao2': '潮', 'zhao1': '招'},
    '看': {'kan4': '瞰', 'kan1': '刊'},
    '教': {'jiao4': '叫', 'jiao1': '交'},
    '便': {'bian4': '变', 'pian2': '骈'},
    '系': {'xi4': '戏', 'ji4': '记'},
    '曾': {'ceng2': '层', 'zeng1': '增'},
    '冲': {'chong1': '充', 'chong4': '铳'},
    '倒': {'dao3': '岛', 'dao4': '到'},
    '载': {'zai3': '宰', 'zai4': '再'},
    '露': {'lu4': '路', 'lou4': '漏'},
    '量': {'liang4': '亮', 'liang2': '粮'},
    '难': {'nan2': '男', 'nan4': '腩'},
    '没': {'mei2': '梅', 'mo4': '莫'},
    '空': {'kong1': '箜', 'kong4': '控'},
    '着': {'zhuo2': '濯', 'zhao2': '招'},
    '藏': {'cang2': '仓', 'zang4': '葬'},
    '挣': {'zheng4': '证', 'zheng1': '争'},
    '率': {'lv4': '律', 'shuai4': '帅'},
    '似': {'si4': '四', 'shi4': '是'},
    '降': {'jiang4': '酱', 'xiang2': '祥'},
    '参': {'can1': '餐', 'shen1': '身'},
    '仇': {'chou2': '愁', 'qiu2': '球'},
    '观': {'guan1': '关', 'guan4': '贯'},
    '更': {'geng4': '亘', 'geng1': '耕'},
}


def expected_readings(say):
    py = pinyin(say, style=Style.TONE3, heteronym=False, neutral_tone_with_five=True)
    out = []
    i = 0
    for ch in say:
        out.append(py[i][0] if i < len(py) else '')
        i += 1
    return out


def char_window(words, say, idx, pad=0.22):
    """Time window of character index idx (in say, punctuation removed)."""
    clean = [c for c in say if '一' <= c <= '鿿']
    times = [None] * len(clean)
    pos = 0
    for s, e, tok in words:
        tc = [c for c in tok if '一' <= c <= '鿿']
        if not tc:
            continue
        k = pos
        while k < len(clean) and clean[k : k + len(tc)] != tc:
            k += 1
        if k >= len(clean):
            continue
        for j in range(len(tc)):
            times[k + j] = (s + (e - s) * j / len(tc), s + (e - s) * (j + 1) / len(tc))
        pos = k + len(tc)
    t = times[idx] or (0, 0.3)
    return max(0, t[0] - pad), t[1] + pad


async def check_line(lid, sem, results):
    v = VO[lid]
    say = v['say']
    exp = expected_readings(say)
    # map index in say → index among CJK chars
    cjk_idx = {}
    n = 0
    for i, ch in enumerate(say):
        if '一' <= ch <= '鿿':
            cjk_idx[i] = n
            n += 1
    probes = []
    for i, ch in enumerate(say):
        if ch in HOMO and exp[i] in HOMO[ch] and len(HOMO[ch]) > 1:
            probes.append(i)
    if not probes:
        return
    import soundfile as sf

    x0, sr = sf.read(ROOT / v['file'], dtype='float32')
    if sr != SR:
        n0 = int(len(x0) * SR / sr)
        x0 = np.interp(np.linspace(0, len(x0) - 1, n0), np.arange(len(x0)), x0).astype(np.float32)
    for i in probes:
        ch = say[i]
        r = exp[i]
        ci = cjk_idx[i]
        a, b = char_window(v['words'], say, ci)
        seg0 = logmel(x0[int(a * SR) : int(b * SR)])
        scores = {}
        async with sem:
            for reading, rep in HOMO[ch].items():
                if rep == ch:
                    continue
                text = say[:i] + rep + say[i + 1 :]
                xv, wv = await synth(text, v['rate'])
                av, bv = char_window(wv, text, ci)
                scores[reading] = dtw(seg0, logmel(xv[int(av * SR) : int(bv * SR)]))
        best = min(scores, key=scores.get)
        ok = best == r
        margin = sorted(scores.values())[1] - min(scores.values()) if len(scores) > 1 else 0
        results.append({'id': lid, 'char': ch, 'pos': i, 'expected': r, 'best': best, 'scores': scores, 'ok': ok, 'margin': margin, 'ctx': say[max(0, i - 4) : i + 5]})
        flag = 'ok' if ok else '!!'
        print(f"{flag} {lid} {say[max(0, i - 4):i]}[{ch}]{say[i + 1:i + 5]}  expected {r}, TTS ≈ {best}  " + ' '.join(f'{k}={s:.2f}' for k, s in scores.items()), flush=True)


async def main():
    ids = sys.argv[1:] or list(VO)
    sem = asyncio.Semaphore(4)
    results = []
    await asyncio.gather(*(check_line(lid, sem, results) for lid in ids))
    (ROOT / 'build' / 'poly_report.json').write_text(json.dumps(results, ensure_ascii=False, indent=1), encoding='utf-8')
    bad = [r for r in results if not r['ok']]
    print(f'{len(results)} polyphones checked, {len(bad)} flagged')


if __name__ == '__main__':
    asyncio.run(main())
