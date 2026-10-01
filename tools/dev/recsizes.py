"""Does the size of a buildings_game.bin record depend on the building's $TYPE?
Groups record sizes by ident in the source map and in the user's saves and prints
the $TYPE of each ident (vanilla/DLC/CWC/mod inis), then lists the kit entries
whose donor type differs from the target type."""
import glob
import os
import re
import sys
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import mapio  # noqa: E402

GAME = r'C:\Program Files (x86)\Steam\steamapps\common\SovietRepublic\media_soviet'
SRC = r'C:\Program Files (x86)\Steam\steamapps\workshop\content\784150\3753525456'


def type_of_ini(path):
    try:
        for line in open(path, encoding='utf-8', errors='replace'):
            t = line.split()
            if t and t[0].startswith('$TYPE_'):
                return t[0]
    except OSError:
        return None
    return None


def ini_for(ident):
    if '/' in ident:
        item, obj = ident.split('/', 1)
        for base in (os.path.join(GAME, 'workshop_wip'), r'C:\Program Files (x86)\Steam\steamapps\workshop\content\784150'):
            p = os.path.join(base, item, obj, 'building.ini')
            if os.path.exists(p):
                return p
        return None
    p = os.path.join(GAME, 'buildings_types', ident + '.ini')
    if os.path.exists(p):
        return p
    m = re.match(r'DLC(\d)_(.*)', ident)
    if m:
        for p in glob.glob(os.path.join(GAME, 'dlc' + m.group(1), 'buildings_types', m.group(2), 'building.ini')):
            return p
        for p in glob.glob(os.path.join(GAME, 'dlc' + m.group(1), '**', m.group(2), 'building.ini'), recursive=True):
            return p
    m = re.match(r'CWC_(.*)', ident)
    if m:
        for p in glob.glob(os.path.join(GAME, 'cwc', '**', m.group(1), 'building.ini'), recursive=True):
            return p
    return None


def sizes(folder):
    types, _ = mapio.read_buildings(os.path.join(folder, 'buildings.bin'))
    recs = mapio.split_records(os.path.join(folder, 'buildings_game.bin'), types, strict=False)
    by = defaultdict(list)
    for r in recs:
        by[r.ident].append(len(r.raw))
    return by


folders = [SRC] + sorted(glob.glob(os.path.join(GAME, 'save', '*')), key=os.path.getmtime)[-4:]
allby = defaultdict(list)
for f in folders:
    try:
        by = sizes(f)
    except Exception as e:  # noqa: BLE001
        print('skip', os.path.basename(f), e)
        continue
    print('%-28s records %d idents %d' % (os.path.basename(f), sum(len(v) for v in by.values()), len(by)))
    for k, v in by.items():
        allby[k] += v

rows = []
for ident, v in allby.items():
    p = ini_for(ident)
    rows.append((type_of_ini(p) if p else '?', ident, min(v), max(v), len(v)))
rows.sort()
print('\n%-36s %-34s %6s %6s %5s' % ('$TYPE', 'ident', 'min', 'max', 'n'))
for t, ident, lo, hi, n in rows:
    print('%-36s %-34s %6d %6d %5d' % (t, ident, lo, hi, n))

print('\n== size range per $TYPE')
per = defaultdict(list)
for t, ident, lo, hi, n in rows:
    per[t] += [lo, hi]
for t in sorted(per):
    print('%-36s %6d .. %6d' % (t, min(per[t]), max(per[t])))

print('\n== kit: target type vs donor type')
import importlib.util
spec = importlib.util.spec_from_file_location('yz', os.path.join(ROOT, 'tools', 'yearzero.py'))
yz = importlib.util.module_from_spec(spec)
spec.loader.exec_module(yz)
donor_sizes = {os.path.basename(p)[:-4]: os.path.getsize(p) for p in glob.glob(os.path.join(ROOT, 'build', 'donors', '*.bin'))}
seen = set()
for ident, donor, *_ in yz.KIT + [(n, 'eletric_transformator_customin') for n, _ in yz.RUIN_MIX] + [(n, 'eletric_transformator_customin') for n, _ in yz.DECOR]:
    if (ident, donor) in seen:
        continue
    seen.add((ident, donor))
    ti = ini_for(yz.game_ident(ident))
    di = ini_for(donor)
    tt, dt = type_of_ini(ti) if ti else '?', type_of_ini(di) if di else '?'
    flag = '' if tt == dt else '   <-- DIFFERENT'
    print('%-26s %-36s donor %-32s %-36s size %s%s' % (ident, tt, donor, dt, donor_sizes.get(donor), flag))
