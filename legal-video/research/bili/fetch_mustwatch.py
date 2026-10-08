"""Download every issue of Bilibili's 每周必看 (weekly must-watch) list."""
import json
import os
import ssl
import sys
import time
import urllib.request
from pathlib import Path

OUT = Path(__file__).resolve().parent / 'mustwatch.json'
CTX = ssl.create_default_context(cafile='/root/.ccr/ca-bundle.crt')
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36'


COOKIE = ''


def get(url):
    headers = {'User-Agent': UA, 'Referer': 'https://www.bilibili.com/'}
    if COOKIE:
        headers['Cookie'] = COOKIE
    req = urllib.request.Request(url, headers=headers)
    proxy = os.environ.get('HTTPS_PROXY')
    handlers = [urllib.request.HTTPSHandler(context=CTX)]
    if proxy:
        handlers.append(urllib.request.ProxyHandler({'https': proxy}))
    opener = urllib.request.build_opener(*handlers)
    with opener.open(req, timeout=30) as r:
        return json.loads(r.read().decode('utf-8'))


def main():
    global COOKIE
    spi = get('https://api.bilibili.com/x/frontend/finger/spi')['data']
    COOKIE = f"buvid3={spi['b_3']}; buvid4={spi['b_4']}"
    issues = get('https://api.bilibili.com/x/web-interface/popular/series/list')['data']['list']
    data = json.loads(OUT.read_text()) if OUT.exists() else {}
    for it in issues:
        n = str(it['number'])
        if n in data:
            continue
        for attempt in range(4):
            try:
                d = get(f'https://api.bilibili.com/x/web-interface/popular/series/one?number={n}')
                if d.get('code') != 0:
                    raise RuntimeError(d.get('message'))
                vids = d['data']['list']
                data[n] = {
                    'name': it['name'],
                    'subject': it.get('subject'),
                    'videos': [
                        {
                            'bvid': v['bvid'],
                            'title': v['title'],
                            'owner': v['owner']['name'],
                            'tname': v.get('tname'),
                            'view': v['stat']['view'],
                            'like': v['stat']['like'],
                            'coin': v['stat'].get('coin'),
                            'fav': v['stat'].get('favorite'),
                            'danmaku': v['stat'].get('danmaku'),
                            'reply': v['stat'].get('reply'),
                            'share': v['stat'].get('share'),
                            'duration': v.get('duration'),
                            'pubdate': v.get('pubdate'),
                            'pic': v.get('pic'),
                            'desc': (v.get('desc') or '')[:200],
                            'rcmd_reason': v.get('rcmd_reason'),
                        }
                        for v in vids
                    ],
                }
                break
            except Exception as e:
                print('retry', n, e, file=sys.stderr, flush=True)
                time.sleep(60 * (attempt + 1))
                spi = get('https://api.bilibili.com/x/frontend/finger/spi')['data']
                COOKIE = f"buvid3={spi['b_3']}; buvid4={spi['b_4']}"
        time.sleep(5)
        if int(n) % 5 == 0:
            OUT.write_text(json.dumps(data, ensure_ascii=False))
            print('issue', n, 'videos so far', sum(len(x['videos']) for x in data.values()), flush=True)
    OUT.write_text(json.dumps(data, ensure_ascii=False))
    print('issues', len(data), 'videos', sum(len(x['videos']) for x in data.values()))


if __name__ == '__main__':
    main()
