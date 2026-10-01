"""Print printable-string context around byte patterns in a binary.

Used to read Republic Mod Loader's own messages, which are the only
documentation of where it looks for plugins.
"""
import re, sys

RUN = re.compile(rb'[\x20-\x7e]{8,}')


def contexts(data, needle, before=140, after=200, limit=5):
    for i, m in enumerate(re.finditer(re.escape(needle), data)):
        if i >= limit:
            break
        s, e = max(0, m.start() - before), min(len(data), m.end() + after)
        yield ' | '.join(r.decode('latin1') for r in RUN.findall(data[s:e]))


if __name__ == '__main__':
    data = open(sys.argv[1], 'rb').read()
    for pat in sys.argv[2:]:
        needle = pat.encode('latin1').decode('unicode_escape').encode('latin1')
        hits = len(re.findall(re.escape(needle), data))
        print(f'##### {pat}  hits={hits}')
        for c in contexts(data, needle):
            print('    ', c[:400])
        print()
