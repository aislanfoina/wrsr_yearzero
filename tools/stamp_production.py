"""Stamp the [production] rates from mod/plugins/trade_post/trade_post.ini into the
trade posts' building.ini files (a production rate lives in building.ini and only
the game's own parser reads that file). Run by build.ps1 -Install.

    python tools/stamp_production.py
"""
import glob
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INI = os.path.join(ROOT, 'mod', 'plugins', 'trade_post', 'trade_post.ini')
POSTS = ('trade_post', 'goods_post', 'junk_post')


def read_rates():
    rates = {}
    section = None
    for raw in open(INI, encoding='utf-8', errors='ignore'):
        line = raw.split(';', 1)[0].strip()
        if not line:
            continue
        if line.startswith('['):
            section = line.strip('[]').lower()
            continue
        if section == 'production' and '=' in line:
            k, v = [x.strip() for x in line.split('=', 1)]
            try:
                rates[k] = float(v)
            except ValueError:
                pass
    return rates


def main():
    rates = read_rates()
    for post in POSTS:
        for path in glob.glob(os.path.join(ROOT, 'mod', 'buildings', post, '*', 'building.ini')):
            t = open(path, 'rb').read().decode('utf-8', 'replace')
            n = 0

            def sub(m):
                nonlocal n
                res = m.group(1)
                if res in rates:
                    n += 1
                    return '$PRODUCTION %s %.2f' % (res, rates[res])
                return m.group(0)
            t2 = re.sub(r'\$PRODUCTION (\w+) [\d.]+', sub, t)
            if t2 != t:
                open(path, 'wb').write(t2.encode())
            print('%-12s %d rates stamped' % (post, n))


if __name__ == '__main__':
    main()
