"""One-off inputs for tools/yearzero.py, regenerable from the game files:

  build/aabbs.json      local model bounding boxes (game axes) for every ident the
                        converter places: kit buildings from mod/buildings, vanilla
                        and DLC3 donors from media_soviet
  build/nk_roadpts.npy  points of the source map's roads (float3 triples in road.bin
                        that sit on the terrain) used to lay the kit out
  build/nk_pts.npy      (x, z) of every placed building in the source map

    python tools/map_prep.py
"""
import glob
import json
import os
import struct
import sys

import numpy as np

TOOLS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, TOOLS)
import nmf  # noqa: E402
import mapio  # noqa: E402

ROOT = os.path.dirname(TOOLS)
M = os.environ.get('WRSR_GAME', r'C:\Program Files (x86)\Steam\steamapps\common\SovietRepublic').rstrip('/\\') + '/media_soviet/'
SRC = os.environ.get('WRSR_WORKSHOP', r'C:\Program Files (x86)\Steam\steamapps\workshop\content\784150').rstrip('/\\') + '/3753525456/'
BUILD = os.path.join(ROOT, 'build')

VANILLA = ['muddy_depot', 'muddy_demolition', 'muddy_openstorage', 'muddy_gravelstorage', 'garage_tiny', 'waste_gravelrecycling',
           'waste_steelrecycling', 'waste_storage_basic_small', 'field_small', 'food_factory', 'hotel_hutnik_small', 'animal_farm',
           'slaughterhouse', 'clothing_factory']
DLC3 = {'DLC3_h_farm': 'h_farm', 'DLC3_distillery_small': 'distillery_small', 'DLC3_clothing_factory': 'clothing_factory',
        'DLC3_h_woodcutting_post': 'h_woodcutting_post', 'DLC3_h_technical_services': 'h_technical_services',
        'DLC3_h_repair_station': 'h_repair_station'}
DLC2 = {'DLC2_chatrc1': 'chatrc1', 'DLC2_chatrc2': 'chatrc2', 'DLC2_chatrc3': 'chatrc3', 'DLC2_temple1': 'temple1'}


def model_aabb(path):
    m = nmf.read(path)
    lo = [1e9] * 3
    hi = [-1e9] * 3
    for s in m.shapes:
        if not s.pos:
            continue
        W = s.world
        P = np.array(s.pos, dtype=np.float64).reshape(-1, 3)
        Wm = np.array(W, dtype=np.float64).reshape(4, 4)
        Pw = P @ Wm[:3, :3] + Wm[3, :3]
        lo = np.minimum(lo, Pw.min(0))
        hi = np.maximum(hi, Pw.max(0))
    return [float(v) for v in lo], [float(v) for v in hi]


def aabbs():
    out = {}
    for k in glob.glob(os.path.join(ROOT, 'mod', 'buildings', '*', '*', 'model.nmf')):
        out[os.path.basename(os.path.dirname(k))] = model_aabb(k)
    for ident in VANILLA:
        p = M + 'buildings/%s.nmf' % ident
        if os.path.exists(p):
            out[ident] = model_aabb(p)
    for ident, short in DLC3.items():
        files = [f for f in glob.glob(M + 'dlc3/buildings/%s/*.nmf' % short) if 'lod' not in os.path.basename(f).lower()]
        if files:
            out[ident] = model_aabb(max(files, key=os.path.getsize))
    for ident, short in DLC2.items():
        p = M + 'dlc2/buildings/%s/%s.nmf' % (short, short)
        if os.path.exists(p):
            out[ident] = model_aabb(p)
    json.dump(out, open(os.path.join(BUILD, 'aabbs.json'), 'w'))
    return out


def road_points():
    d = open(SRC + 'road.bin', 'rb').read()
    f = np.frombuffer(d[:len(d) // 4 * 4], dtype='<f4')
    h = open(SRC + 'heightmap.dds', 'rb').read()[128:]
    H = np.frombuffer(h[:2048 * 2048 * 4], dtype='<f4').reshape(2048, 2048)
    inb = np.abs(f) < 9990
    c = np.where(inb[:-2] & (f[1:-1] > -10) & (f[1:-1] < 1300) & inb[2:])[0]
    X, Y, Z = f[c], f[c + 1], f[c + 2]
    col = np.clip(((X + 10000) / 20000 * 2047).astype(int), 0, 2047)
    row = np.clip(((Z + 10000) / 20000 * 2047).astype(int), 0, 2047)
    ok = np.abs(Y - (H[row, col] * 1250 - 5)) < 4.0
    P = np.stack([X[ok], Y[ok], Z[ok]], 1)
    key = np.round(P[:, [0, 2]]).astype(np.int64)
    _, idx = np.unique(key[:, 0] * 100000 + key[:, 1], return_index=True)
    P = P[idx]
    np.save(os.path.join(BUILD, 'nk_roadpts.npy'), P)
    return len(P)


def building_points():
    types, _ = mapio.read_buildings(SRC + 'buildings.bin')
    P = np.array([(fr.pos[0], fr.pos[2]) for frs in types.values() for fr in frs])
    np.save(os.path.join(BUILD, 'nk_pts.npy'), P)
    return len(P)


if __name__ == '__main__':
    os.makedirs(BUILD, exist_ok=True)
    a = aabbs()
    print('aabbs', len(a))
    print('road points', road_points())
    print('building points', building_points())
