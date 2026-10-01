"""Pull donor building records (game-side state) out of local saves/maps so the
map converter can clone them under new idents. Read-only on the sources.

    python tools/donors.py            -> build/donors/<ident>.bin + .frag + meta.json
"""
import os
import sys
import json

TOOLS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, TOOLS)
import mapio  # noqa: E402

ROOT = os.path.dirname(TOOLS)
S = os.environ.get('WRSR_GAME', r'C:\Program Files (x86)\Steam\steamapps\common\SovietRepublic').rstrip('/\\') + '/media_soviet/save/'
M = os.environ.get('WRSR_GAME', r'C:\Program Files (x86)\Steam\steamapps\common\SovietRepublic').rstrip('/\\') + '/media_soviet/'
OUT = os.path.join(ROOT, 'build', 'donors')

WANT = {  # ident -> candidate source folders (first that has it wins)
    'muddy_depot': [S + '12884 - b31', S + '10314 - b5', S + '10813 - a58'],
    'muddy_demolition': [S + '12884 - b31', S + '15800 - a21'],
    'muddy_openstorage': [S + '12884 - b31', S + '10314 - b5'],
    'muddy_gravelstorage': [S + '17062 - b19', S + '17133 - b13'],
    'garage_tiny': [S + '10813 - a58', M + 'campaign1'],
    'waste_gravelrecycling': [S + '10813 - a58', S + '11786 - a40'],
    'waste_steelrecycling': [S + '10813 - a58', S + '11786 - a40'],
    'waste_storage_basic_small': [S + '12884 - b31', S + '12008 - a31'],
    'DLC3_h_farm': [S + '12884 - b31', S + '15800 - a21'],
    'field_small': [M + 'dlc3/terrains/moscow', M + 'campaign2'],
    'DLC3_distillery_small': [S + '12884 - b31'],
    'DLC3_clothing_factory': [S + '12884 - b31'],
    'food_factory': [S + '12347 - My republic11'],
    'hotel_hutnik_small': [S + '12347 - My republic11'],
    'CWC_scrapping_facility1': [S + '14894 - a67', S + '18852 - a68'],
    'DLC3_h_repair_station': [S + '12884 - b31'],
    'DLC3_h_technical_services': [S + '12884 - b31', S + '15800 - a21'],
    'DLC3_open_storage_basic': [S + '12884 - b31'],
    'MIRRORZ_DLC4_monument': [M + 'dlc4/terrains/northkorea'],
    'livestock_storage': [S + '10813 - a58'],
    'DLC3_h_woodcutting_post': [S + '12884 - b31'],
    'DLC3_brick_factory_small': [S + '12884 - b31'],
    'DLC3_coal_processing': [S + '12884 - b31'],
    'muddy_busstop': [S + '13025 - My republic6'],
    'shop_grocerystore': [S + '10813 - a58'],
    'rozhlas_v2': [S + '10813 - a58', S + '11786 - a40', S + '12270 - a50'],   # TYPE_BROADCAST donor for the distress beacon
}


def main():
    os.makedirs(OUT, exist_ok=True)
    cache = {}
    meta = {}
    for ident, srcs in WANT.items():
        for src in srcs:
            if not os.path.isdir(src):
                continue
            if src not in cache:
                try:
                    types, _ = mapio.read_buildings(src + '/buildings.bin')
                    recs = mapio.split_records(src + '/buildings_game.bin', types, strict=False)
                    recs = [r for r in recs if r.safe]
                    cache[src] = (types, recs)
                except Exception as e:  # noqa: BLE001
                    print('  split failed for', src, e)
                    cache[src] = None
                    continue
            if cache[src] is None:
                continue
            types, recs = cache[src]
            cands = [r for r in recs if r.ident == ident]
            if not cands:
                continue
            # header words +0x408/+0x40C/+0x414 count lists (building+0x860/+0x718/+0x880) whose entries the
            # game resolves by index into global tables; a clone carrying them crashes the autosave. Prefer a
            # candidate without any, then the smallest record (fewest dynamic entries).
            clean = [r for r in cands if not (r.u32(0x408) or r.u32(0x40C) or r.u32(0x414))]
            if not clean:
                print('%-28s WARNING: every candidate in %s carries external references; skipping this source' % (ident, src[-30:]))
                continue
            r = min(clean, key=lambda r: len(r.raw))
            # a trailing fragment-less helper record (ident 'temp', fragment index 0xFFFFFFFF) is invisible to the
            # anchor splitter; cut it off so the clone is exactly one building
            o = bytes(r.raw).find(b'\0temp\0', 0x548)
            while o != -1:
                o += 1
                if o + 0x3E0 <= len(r.raw) and r.u32(o + 0x3D8) == 0xFFFFFFFF:
                    r = mapio.Rec(bytes(r.raw[:o]))
                    break
                o = bytes(r.raw).find(b'\0temp\0', o)
            frag = types[ident][r.fragidx]
            open(os.path.join(OUT, ident + '.bin'), 'wb').write(bytes(r.raw))
            open(os.path.join(OUT, ident + '.frag'), 'wb').write(frag.pack())
            meta[ident] = {'src': src, 'size': len(r.raw), 'n_in_src': len(cands), 'pos': r.pos, 'rot': r.rotstep,
                           'rotf': r.f32(mapio.Rec.ROTF), 'aabb': frag.aabb, 'extra': frag.extra}
            print('%-28s from %-45s size=%6d (of %d) rot=%3d rotf=%.3f aabb=%s' % (
                ident, src[-45:], len(r.raw), len(cands), r.rotstep, r.f32(mapio.Rec.ROTF), [round(v, 1) for v in frag.aabb]))
            break
        else:
            print('%-28s NOT FOUND' % ident)
    json.dump(meta, open(os.path.join(OUT, 'meta.json'), 'w'), indent=1)


if __name__ == '__main__':
    main()
