"""Find law-related videos in the 每周必看 archive and summarise patterns."""
import json
import re
import statistics
import sys
import time
from collections import Counter
from pathlib import Path

D = Path(__file__).resolve().parent
data = json.loads((D / 'mustwatch.json').read_text())
vids = [dict(v, issue=int(k), iname=x['name']) for k, x in data.items() for v in x['videos']]

LAW = re.compile(
    r'法律|法院|法官|律师|罗翔|刑法|民法|判决|判了|宣判|起诉|官司|诉讼|犯罪|罪犯|嫌疑人|凶手|命案|悬案|冤案|案件|大案|奇案|劫案|诈骗|骗局|反诈|警察|警方|刑警|法医|监狱|坐牢|死刑|无期|违法|合法|非法|维权|赔偿|侵权|版权|合同|证据|张三|正当防卫|偷|盗'
)
LAW_OWNERS = {'罗翔说刑法', '法山叔', '法律考察员'}


def is_law(v):
    return bool(LAW.search(v['title'])) or v['owner'] in LAW_OWNERS or v.get('tname') in ('社科·法律·心理',)


L = [v for v in vids if is_law(v)]
print(f"{len(data)} issues, {len(vids)} videos; law-related: {len(L)} ({len(L) / len(vids):.1%})")
print('median views all:', int(statistics.median(v['view'] for v in vids)), ' law:', int(statistics.median(v['view'] for v in L)))
print('\ntop owners among law-related:')
for o, n in Counter(v['owner'] for v in L).most_common(25):
    print(f'  {n:3d} {o}')
print('\ntop 80 law-related by views:')
for v in sorted(L, key=lambda v: -v['view'])[:80]:
    y = time.strftime('%Y-%m', time.localtime(v['pubdate'])) if v.get('pubdate') else '?'
    print(f"{v['view'] / 1e4:7.0f}万 {v['like'] / 1e4:5.0f}万赞 {y} {v['owner'][:9]:9s} [{v['tname']}] {v['title'][:58]}")
json.dump(sorted(L, key=lambda v: -v['view']), open(D / 'law_videos.json', 'w'), ensure_ascii=False, indent=0)
