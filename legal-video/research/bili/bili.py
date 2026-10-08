"""Small Bilibili web-API client with buvid cookies and WBI signing."""
import hashlib
import hmac
import json
import random
import string
import os
import ssl
import time
import urllib.parse
import urllib.request

CTX = ssl.create_default_context(cafile='/root/.ccr/ca-bundle.crt')
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36'
TAB = [46, 47, 18, 2, 53, 8, 23, 32, 15, 50, 10, 31, 58, 3, 45, 35, 27, 43, 5, 49, 33, 9, 42, 19, 29, 28, 14, 39, 12, 38, 41, 13, 37, 48, 7, 16, 24, 55, 40, 61, 26, 17, 0, 1, 60, 51, 30, 4, 22, 25, 54, 21, 56, 59, 6, 63, 57, 62, 11, 36, 20, 34, 44, 52]
_state = {'cookie': '', 'mixin': None}


def _open(url, cookie=True):
    headers = {'User-Agent': UA, 'Referer': 'https://www.bilibili.com/', 'Accept': 'application/json, text/plain, */*'}
    if cookie and _state['cookie']:
        headers['Cookie'] = _state['cookie']
    req = urllib.request.Request(url, headers=headers)
    handlers = [urllib.request.HTTPSHandler(context=CTX)]
    if os.environ.get('HTTPS_PROXY'):
        handlers.append(urllib.request.ProxyHandler({'https': os.environ['HTTPS_PROXY']}))
    with urllib.request.build_opener(*handlers).open(req, timeout=30) as r:
        return r.read()


def get(url):
    return json.loads(_open(url).decode('utf-8'))


def init():
    if _state['cookie']:
        return
    spi = json.loads(_open('https://api.bilibili.com/x/frontend/finger/spi', cookie=False))['data']
    ts = int(time.time())
    uuid = '-'.join(''.join(random.choices('0123456789ABCDEF', k=n)) for n in (8, 4, 4, 4, 12)) + f'{ts % 100000:05d}infoc'
    _state['cookie'] = f"buvid3={spi['b_3']}; buvid4={spi['b_4']}; b_nut={ts}; _uuid={uuid}; CURRENT_FNVAL=4048"
    try:
        sign = hmac.new(b'XgwSnGZ1p', f'ts{ts}'.encode(), hashlib.sha256).hexdigest()
        url = f'https://api.bilibili.com/bapis/bilibili.api.ticket.v1.Ticket/GenWebTicket?key_id=ec02&hexsign={sign}&context[ts]={ts}&csrf='
        req = urllib.request.Request(url, data=b'', method='POST', headers={'User-Agent': UA, 'Cookie': _state['cookie']})
        handlers = [urllib.request.HTTPSHandler(context=CTX)]
        if os.environ.get('HTTPS_PROXY'):
            handlers.append(urllib.request.ProxyHandler({'https': os.environ['HTTPS_PROXY']}))
        with urllib.request.build_opener(*handlers).open(req, timeout=30) as r:
            tk = json.loads(r.read())['data']
        _state['cookie'] += f"; bili_ticket={tk['ticket']}; bili_ticket_expires={tk['created_at'] + tk['ttl']}"
    except Exception as e:  # ticket is optional
        print('ticket failed', e)
    nav = get('https://api.bilibili.com/x/web-interface/nav')['data']['wbi_img']
    img = nav['img_url'].rsplit('/', 1)[1].split('.')[0]
    sub = nav['sub_url'].rsplit('/', 1)[1].split('.')[0]
    orig = img + sub
    _state['mixin'] = ''.join(orig[i] for i in TAB)[:32]


def wbi(url, params):
    init()
    p = dict(params)
    p['wts'] = int(time.time())
    p = {k: ''.join(c for c in str(v) if c not in "!'()*") for k, v in sorted(p.items())}
    q = urllib.parse.urlencode(p)
    w = hashlib.md5((q + _state['mixin']).encode()).hexdigest()
    return get(f'{url}?{q}&w_rid={w}')


def search(keyword, order='click', page=1, duration=0):
    """order: totalrank | click | pubdate | dm | stow ; duration 0 all, 4 = >60min, 3 = 30-60, 2 = 10-30, 1 = <10"""
    d = wbi('https://api.bilibili.com/x/web-interface/wbi/search/type', {'search_type': 'video', 'keyword': keyword, 'order': order, 'page': page, 'duration': duration})
    if d.get('code') != 0:
        raise RuntimeError(d)
    out = []
    for v in d['data'].get('result') or []:
        out.append({
            'bvid': v['bvid'],
            'title': v['title'].replace('<em class="keyword">', '').replace('</em>', ''),
            'author': v['author'],
            'play': v['play'],
            'like': v.get('like'),
            'fav': v.get('favorites'),
            'danmaku': v.get('video_review'),
            'review': v.get('review'),
            'duration': v['duration'],
            'pubdate': time.strftime('%Y-%m-%d', time.localtime(v['pubdate'])),
            'pic': 'https:' + v['pic'] if v['pic'].startswith('//') else v['pic'],
            'tag': v.get('tag', '')[:80],
            'typename': v.get('typename'),
        })
    return out


if __name__ == '__main__':
    import sys
    init()
    for kw in sys.argv[1:]:
        res = search(kw)
        print(f'== {kw}: {len(res)}')
        for v in res[:20]:
            print(f"{v['play']:>9} ▶  {v['like'] or 0:>7} 👍  {v['pubdate']}  {v['author'][:10]:10s}  {v['title'][:60]}")
