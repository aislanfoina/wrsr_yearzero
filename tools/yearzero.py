"""Korea Year Zero - turn the "North Korea map - Early start version" workshop
map (3753525456) into a post-nuclear-strike survival start.

What it does to a copy of the map folder:
  terrain   wasteland tile palette (custom tiles shipped with the map), mask
            repainted with scorched/fallout rings around the strike points,
            trees thinned and retyped to dry species, cleared inside the rings
  buildings huts inside each strike's inner radius become Mad-Max ruins (record
            replaced in place, no index shifts); the start kit (motor pool,
            repair station, demolition/salvage office, recycling plants, storages,
            trade post, scrap center, survivors' camp/beacon/shelter, farm+fields,
            food/alcohol/meat/clothes plants, woodcutting) is appended next to the
            roads east of the capital, cloned from donor records (tools/donors.py)
  scenario  a WORKSHOP_ITEMTYPE_SCRIPT item with the start script (money, no
            immigrant purchase, blueprints, wrecked trucks in the motor pool)

    python tools/yearzero.py            # writes media_soviet/workshop_wip/9000007 (+9000008)
"""
import glob
import json
import math
import os
import random
import shutil
import struct
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

TOOLS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, TOOLS)
import mapio  # noqa: E402

ROOT = os.path.dirname(TOOLS)
# override with the WRSR_GAME and WRSR_WORKSHOP environment variables
GAME = os.environ.get('WRSR_GAME', 'C:/Program Files (x86)/Steam/steamapps/common/SovietRepublic').rstrip('/\\') + '/media_soviet/'
SRC = os.environ.get('WRSR_WORKSHOP', 'C:/Program Files (x86)/Steam/steamapps/workshop/content/784150').rstrip('/\\') + '/3753525456/'
MAP_ID = 9000007
SCEN_ID = 9000008
OUT = GAME + 'workshop_wip/%d/' % MAP_ID
SCEN_OUT = GAME + 'workshop_wip/%d/' % SCEN_ID


def data(name):
    """An input made by the prep tools: build/<name> when they have run here (map_prep.py, donors.py),
    else the copy the repository ships in data/yearzero/<name>."""
    p = os.path.join(ROOT, 'build', name)
    return p if os.path.exists(p) else os.path.join(ROOT, 'data', 'yearzero', name)


DONORS = data('donors')
AABBS = json.load(open(data('aabbs.json')))
TILES = os.path.join(ROOT, 'build', 'tiles')
# the scenario's picture: our own preview if there is one, else the source map's
PREVIEW = data('nk_preview.png') if os.path.exists(data('nk_preview.png')) else SRC + 'previewimage.png'

WORLD = 20000.0
GRID = 2048
HSCALE = 1250.0
HOFF = -5.0
STEPS = 128

STRIKES = [
    dict(name='Capital', gz=(-3709.0, -3717.0), inner=120.0, scorch=480.0, ash=1150.0),
    dict(name='East port', gz=(3940.0, 758.0), inner=75.0, scorch=380.0, ash=900.0),
    dict(name='North gate town', gz=(2400.0, -5207.0), inner=65.0, scorch=330.0, ash=800.0),
]
RUIN_MIX = [('mm_road_wreck', 3), ('mm_barricade', 3), ('mm_scrap_wall', 2), ('mm_totem', 2), ('mm_wreck_yard', 2),
            ('mm_shanty', 2), ('mm_ruin_block', 2), ('mm_fuel_depot', 1)]
# a record's layout is per $TYPE (recsizes.py): the mm_* pieces are TYPE_MONUMENT, so their donor must be one too
RUIN_DONOR = 'MIRRORZ_DLC4_monument'
RUIN_FRACTION = 0.55   # share of struck huts that get a ruin piece; the rest become bare ground (a totem-less empty lot is
                       # not possible without index shifts, so the remainder gets the smallest piece, a totem, flagged hidden)

# (ident, donor ident, road-side local direction, zone, caption)
# donors must share the target TYPE and carry no external references: the distillery record from save b31 has 10
# entries in the building+0x880 list (resolved through a global table with no bounds check) and crashed the autosave
KIT = [
    ('scrap_center', 'CWC_scrapping_facility1', (0, 1), 'industrial', 'Scrap Center'),
    ('muddy_depot', 'muddy_depot', (1, 0), 'industrial', 'Salvage motor pool'),
    ('DLC3_h_repair_station', 'DLC3_h_repair_station', (0, 1), 'industrial', 'Vehicle repair yard'),
    ('muddy_demolition', 'muddy_demolition', (1, 0), 'industrial', 'Salvage crew office'),
    ('waste_gravelrecycling', 'waste_gravelrecycling', (0, -1), 'industrial', 'Rubble crusher'),
    ('waste_steelrecycling', 'waste_steelrecycling', (0, -1), 'industrial', 'Scrap smelter'),
    ('waste_storage_basic_small', 'waste_storage_basic_small', (-1, 0), 'industrial', 'Rubble dump'),
    ('muddy_openstorage', 'muddy_openstorage', (1, 0), 'industrial', 'Salvage yard'),
    ('muddy_gravelstorage', 'muddy_gravelstorage', (1, 0), 'industrial', 'Gravel heap'),
    ('trade_post', 'DLC3_clothing_factory', (0, 1), 'town', 'Survival Trade Post'),
    ('mercenary_camp', 'muddy_openstorage', (0, 1), 'town', 'Mercenary Camp'),
    ('distress_beacon', 'rozhlas_v2', (0, 1), 'town', 'Distress Beacon'),
    ('survivor_shelter', 'hotel_hutnik_small', (0, 1), 'town', 'Survivor Shelter'),
    ('DLC3_h_farm', 'DLC3_h_farm', (0, 1), 'farm', 'Farm'),
    ('field_small', 'field_small', None, 'farm', 'Field'),
    ('field_small', 'field_small', None, 'farm', 'Field'),
    ('food_factory', 'food_factory', (0, -1), 'farm', 'Food plant'),
    ('DLC3_distillery_small', 'DLC3_clothing_factory', (0, 1), 'farm', 'Distillery'),
    ('animal_farm', 'DLC3_clothing_factory', (1, 0), 'farm', 'Animal pens'),
    ('slaughterhouse', 'DLC3_clothing_factory', (0, 1), 'farm', 'Slaughterhouse'),
    ('clothing_factory', 'DLC3_clothing_factory', (-1, 0), 'farm', 'Clothing workshop'),
    ('DLC3_h_woodcutting_post', 'DLC3_h_woodcutting_post', (0, 1), 'farm', 'Woodcutters'),
]
DECOR = [('mm_watchtower', 'industrial'), ('mm_skull_gate', 'town'), ('mm_wall_tower', 'town'), ('mm_watchtower', 'farm'),
         ('mm_windpump', 'farm')]
# where each zone's road runs, as an angular sector (degrees, 0 = +x, counter-clockwise towards +z) and distance band from the capital
ZONES = {'industrial': dict(sector=(-55.0, -15.0), dist=(600.0, 1350.0)),
         'town': dict(sector=(10.0, 60.0), dist=(420.0, 820.0)),
         'farm': dict(sector=(60.0, 125.0), dist=(380.0, 1500.0))}
VEHICLES_IN_DEPOT = ['warrig', 'raider', 'buzzard']


def wip_index():
    """object folder -> workshop_wip item id, from every item's workshopconfig.ini. The game
    registers a workshop building or vehicle type under the ident '<item id>/<object>'
    (SOVIET64.exe 0x11DD82, sprintf("%llu/%s")); saves confirm it ('1873180745/Transformer')."""
    idx = {}
    for cfg in glob.glob(GAME + 'workshop_wip/*/workshopconfig.ini'):
        try:
            item = int(os.path.basename(os.path.dirname(cfg)))
        except ValueError:
            continue
        for line in open(cfg, encoding='utf-8', errors='replace'):
            t = line.split()
            if len(t) >= 2 and t[0] in ('$OBJECT_BUILDING', '$OBJECT_VEHICLE'):
                idx[t[1]] = item
    return idx


WIP = wip_index()


def game_ident(name):
    """the ident the game uses for a type: '<item id>/<object>' for our WIP objects, unchanged for vanilla/DLC"""
    return '%d/%s' % (WIP[name], name) if name in WIP else name
BLUEPRINTS = ['warrig', 'raider']


# ------------------------------------------------------------------ helpers --
def wpx(x, z):
    """world (x, z) -> heightmap/mask pixel (col, row); verified against placed buildings"""
    return int((x + WORLD / 2) / WORLD * (GRID - 1)), int((z + WORLD / 2) / WORLD * (GRID - 1))


def rot_xz(x, z, step):
    a = step * 2 * math.pi / STEPS
    c, s = math.cos(a), math.sin(a)
    return x * c + z * s, -x * s + z * c


def world_aabb(ident, pos, step):
    lo, hi = AABBS[ident]
    xs, zs = [], []
    for x in (lo[0], hi[0]):
        for z in (lo[2], hi[2]):
            rx, rz = rot_xz(x, z, step)
            xs.append(rx)
            zs.append(rz)
    return [min(xs) + pos[0], lo[1] + pos[1], min(zs) + pos[2], max(xs) + pos[0], hi[1] + pos[1], max(zs) + pos[2]]


def step_for_direction(local_dir, world_dir):
    """rotation step that maps a local xz direction onto a world xz direction"""
    best, berr = 0, 1e9
    wx, wz = world_dir
    n = math.hypot(wx, wz) or 1.0
    wx, wz = wx / n, wz / n
    for k in range(STEPS):
        rx, rz = rot_xz(local_dir[0], local_dir[1], k)
        err = (rx - wx) ** 2 + (rz - wz) ** 2
        if err < berr:
            best, berr = k, err
    return best


class Terrain:
    def __init__(self, folder):
        self.hh, self.hpix, h, w, fcc, bpp = mapio.read_dds_raw(folder + 'heightmap.dds')
        self.H = np.frombuffer(self.hpix[:GRID * GRID * 4], dtype='<f4').reshape(GRID, GRID).copy()
        self.mh, mpix, h, w, fcc, bpp = mapio.read_dds_raw(folder + 'mask.dds')
        self.M = np.frombuffer(mpix[:GRID * GRID * 4], dtype=np.uint8).reshape(GRID, GRID, 4).copy()

    def height(self, x, z):
        c, r = wpx(x, z)
        return float(self.H[r, c]) * HSCALE + HOFF

    def slope(self, x, z, r_m=20.0):
        c, r = wpx(x, z)
        k = max(1, int(r_m / (WORLD / GRID)))
        blk = self.H[max(0, r - k):r + k + 1, max(0, c - k):c + k + 1] * HSCALE
        return float(blk.max() - blk.min())

    def flatten(self, aabb, y, margin=0.0):
        c0, r0 = wpx(aabb[0] - margin, aabb[2] - margin)
        c1, r1 = wpx(aabb[3] + margin, aabb[5] + margin)
        self.H[r0:r1 + 1, c0:c1 + 1] = (y - HOFF) / HSCALE

    def write(self, folder):
        mapio.write_dds_raw(folder + 'heightmap.dds', self.hh, self.H.astype('<f4').tobytes())
        mapio.write_dds_raw(folder + 'mask.dds', self.mh, self.M.tobytes())


# ----------------------------------------------------------------- terrain ---
def paint_strikes(terr):
    """mask channels (memory order): 0=R tile2 (fallout dust), 1=G tile3 (scorched), 2=B tile4 (rock), 3=A"""
    yy, xx = np.mgrid[0:GRID, 0:GRID]
    wx = xx / (GRID - 1) * WORLD - WORLD / 2
    wz = yy / (GRID - 1) * WORLD - WORLD / 2
    rng = np.random.RandomState(7)
    noise = np.array(Image.fromarray((rng.rand(128, 128) * 255).astype(np.uint8)).resize((GRID, GRID), Image.BILINEAR)) / 255.0
    noise2 = np.array(Image.fromarray((rng.rand(512, 512) * 255).astype(np.uint8)).resize((GRID, GRID), Image.BILINEAR)) / 255.0
    scorch = np.zeros((GRID, GRID), np.float32)
    dust = np.zeros((GRID, GRID), np.float32)
    for s in STRIKES:
        d = np.hypot(wx - s['gz'][0], wz - s['gz'][1])
        dj = d * (0.85 + 0.3 * noise)  # ragged edges
        sc = np.clip(1.0 - (dj - s['inner'] * 0.6) / (s['scorch'] - s['inner'] * 0.6), 0, 1)
        du = np.clip(1.0 - (dj - s['scorch'] * 0.8) / (s['ash'] - s['scorch'] * 0.8), 0, 1)
        scorch = np.maximum(scorch, sc ** 1.3)
        dust = np.maximum(dust, du * (0.55 + 0.45 * noise2))
    land = terr.H > 0.0005
    scorch *= land
    dust *= land
    M = terr.M.astype(np.float32)
    rock = M[..., 2] / 255.0
    g = scorch
    r = np.clip(dust - g, 0, 1) * 0.9
    rock = rock * (1 - g)
    total = np.clip(r + g + rock, 0, 1)
    M[..., 0] = r * 255
    M[..., 1] = g * 255
    M[..., 2] = rock * 255
    # keep the sum at or below 255 like the vanilla masks
    over = total > 1
    M[over, 0:3] /= total[over, None]
    terr.M = np.clip(M, 0, 255).astype(np.uint8)


def write_materials(folder):
    rel = 'workshop_wip/%d/tiles/' % MAP_ID
    for fn in ('material.mtl', 'material_fall.mtl', 'material_winter.mtl'):
        txt = mapio.read_mtl(SRC + fn)
        mapping = {5: rel + 'wl_dead.dds', 6: rel + 'wl_deadbump.dds', 7: rel + 'wl_dust.dds', 8: rel + 'wl_dustbump.dds',
                   9: rel + 'wl_scorched.dds', 10: rel + 'wl_scorchedbump.dds', 19: 'tiles_normal/newdesert4_fall.dds'}
        if fn == 'material_winter.mtl':
            mapping[19] = 'tiles_normal/grass2_snow.dds'
        open(folder + fn, 'w', newline='').write(mapio.set_textures(txt, mapping))
    os.makedirs(folder + 'tiles', exist_ok=True)
    for f in os.listdir(TILES):
        if f.endswith('.dds'):
            shutil.copy(os.path.join(TILES, f), folder + 'tiles/' + f)


def convert_trees(folder):
    types = mapio.read_trees(SRC + 'trees.bin')
    rng = np.random.RandomState(3)
    out = {}
    # (target type, keep fraction) per source type; several targets split the survivors
    plan = {
        'pine1': [('pine1', 0.18), ('afghan_pine_kriak1', 0.22)], 'pine2': [('pine2', 0.18), ('afghan_pine_kriak2', 0.22)],
        'pine3': [('pine3', 0.15), ('afghan_pine_kriak1', 0.25)], 'pine4': [('pine4', 0.15), ('afghan_pine_kriak2', 0.25)],
        'strom': [('afghan_leaved1a', 0.30), ('afghan_leaved2a', 0.15)], 'topol': [('afghan_leaved1b', 0.6)],
        'kriak': [('afghan_kriak1a', 0.40), ('kriak', 0.10)], 'kriak3': [('afghan_kriak3a', 0.40), ('kriak3', 0.10)],
        'afghan_leaved1a': [('afghan_leaved1a', 0.7)], 'afghan_leaved2a': [('afghan_leaved2a', 0.7)],
        'afghan_leaved1b': [('afghan_leaved1b', 0.7)], 'afghan_leaved2b': [('afghan_leaved2b', 0.7)],
        'afghan_pine_kriak1': [('afghan_pine_kriak1', 0.8)], 'afghan_pine_kriak2': [('afghan_pine_kriak2', 0.8)],
        'broadbush1': [('broadbush1', 0.5)], 'broadbush2': [('broadbush2', 0.5)], 'broadbush3': [('broadbush3', 0.5)],
    }
    for name, recs in types.items():
        n = len(recs) // mapio.TREE_REC
        if n == 0:
            continue
        pos = mapio.tree_positions(recs)
        keep = np.ones(n, bool)
        for s in STRIKES:
            d = np.hypot(pos[:, 0] - s['gz'][0], pos[:, 2] - s['gz'][1])
            keep &= d > s['scorch']
            keep &= ~((d <= s['ash']) & (rng.rand(n) < 0.8))
        u = rng.rand(n)
        acc = 0.0
        arr = np.frombuffer(bytes(recs), dtype=np.uint8).reshape(n, mapio.TREE_REC)
        for target, frac in plan.get(name, [(name, 0.5)]):
            sel = keep & (u >= acc) & (u < acc + frac)
            acc += frac
            out.setdefault(target, bytearray()).extend(arr[sel].tobytes())
    total = sum(len(v) // mapio.TREE_REC for v in out.values())
    mapio.write_trees(folder + 'trees.bin', out)
    return total


# --------------------------------------------------------------- buildings ---
def load_donor(ident):
    raw = open(os.path.join(DONORS, ident + '.bin'), 'rb').read()
    # a fragment-less helper record (ident 'temp', fragment index 0xFFFFFFFF) can trail the donor: the
    # anchor splitter cannot see it, but the game reads it as one more building and deletes it
    o = raw.find(b'\x00temp\x00', 0x548)
    while o != -1:
        o += 1
        if o + 0x3E0 <= len(raw) and struct.unpack_from('<I', raw, o + 0x3D8)[0] == 0xFFFFFFFF:
            raw = raw[:o]
            break
        o = raw.find(b'\x00temp\x00', o)
    return mapio.Rec(raw)


def make_record(donor_ident, ident, pos, step, fragidx, city):
    r = load_donor(donor_ident)
    r.ident = ident
    r.set_pos(pos)
    r.set_rot(step, step * 2 * math.pi / STEPS)
    r.set_fragidx(fragidx)
    r.set_u32(0x100, city)
    return r


def make_frag(ident, pos, step):
    f = mapio.Frag()
    f.pos = list(pos)
    f.rot = step
    f.aabb = world_aabb(ident, pos, step)
    f.flag = 1
    return f


def road_points_in(zone, gz):
    pts = np.load(data('nk_roadpts.npy'))
    dx, dz = pts[:, 0] - gz[0], pts[:, 2] - gz[1]
    d = np.hypot(dx, dz)
    ang = np.degrees(np.arctan2(dz, dx))
    a0, a1 = zone['sector']
    sel = (d >= zone['dist'][0]) & (d <= zone['dist'][1]) & (ang >= a0) & (ang <= a1)
    p = pts[sel]
    order = np.argsort(np.hypot(p[:, 0] - gz[0], p[:, 2] - gz[1]))
    return p[order]


def layout_zone(zone_name, entries, gz, terr, occupied, avoid_pts):
    """Place buildings one after another along the zone's road, on the side away
    from the capital. Returns list of (ident, pos, step, road_side)."""
    road = road_points_in(ZONES[zone_name], gz)
    if len(road) < 5:
        raise RuntimeError('no road in zone ' + zone_name)
    # drop isolated points (extraction noise), then walk the road by chaining nearest points
    d2 = ((road[:, None, 0] - road[None, :, 0]) ** 2 + (road[:, None, 2] - road[None, :, 2]) ** 2)
    dense = (d2 < 60.0 ** 2).sum(1) >= 3
    road = road[dense]
    chain = [road[0]]
    rest = list(range(1, len(road)))
    while rest:
        last = chain[-1]
        j = min(rest, key=lambda i: (road[i][0] - last[0]) ** 2 + (road[i][2] - last[2]) ** 2)
        rest.remove(j)
        if math.hypot(road[j][0] - last[0], road[j][2] - last[2]) > 150:
            continue   # a different road; skip it
        chain.append(road[j])
    chain = np.array(chain)
    seg = np.diff(chain[:, [0, 2]], axis=0)
    seglen = np.hypot(seg[:, 0], seg[:, 1])
    cum = np.concatenate([[0], np.cumsum(seglen)])
    total = cum[-1]

    def at(s):
        i = min(np.searchsorted(cum, s), len(seg) - 1)
        i = max(i, 0)
        t = 0 if seglen[i] == 0 else (s - cum[i]) / seglen[i]
        p = chain[i, [0, 2]] + seg[i] * t
        tang = seg[i] / (seglen[i] or 1)
        return p, tang

    placed = []
    s = 40.0
    for ident, donor, road_dir, zone, caption in entries:
        lo, hi = AABBS[ident]
        along = max(hi[0] - lo[0], hi[2] - lo[2])
        depth = along
        tries = 0
        while s < total - 20 and tries < 60:
            p, tang = at(s)
            nrm = np.array([-tang[1], tang[0]])
            # side away from the capital first, the near side on odd tries
            if np.dot(nrm, p - np.array(gz)) < 0:
                nrm = -nrm
            if tries % 2 == 1:
                nrm = -nrm
            if road_dir is None:   # fields: no road stub, put them a bit further out
                step = step_for_direction((1, 0), (tang[0], tang[1]))
                ext = 26.0
            else:
                step = step_for_direction(road_dir, (-nrm[0], -nrm[1]))
                ext = 0.0
            # distance from road centreline to building centre: half depth along the normal + road half width
            lo2, hi2 = AABBS[ident]
            corners = [rot_xz(x, z, step) for x in (lo2[0], hi2[0]) for z in (lo2[2], hi2[2])]
            proj = [c[0] * (-nrm[0]) + c[1] * (-nrm[1]) for c in corners]
            reach = max(proj)   # how far the box extends towards the road
            centre = p + nrm * (reach + 6.0 + ext)
            pos = (float(centre[0]), 0.0, float(centre[1]))
            box = world_aabb(ident, pos, step)
            ok = terr.slope(pos[0], pos[2], max(box[3] - box[0], box[5] - box[2]) / 2) < 14.0
            ok = ok and terr.height(pos[0], pos[2]) > 1.5
            ok = ok and all(not (box[0] < o[3] + 4 and box[3] > o[0] - 4 and box[2] < o[5] + 4 and box[5] > o[2] - 4) for o in occupied)
            ok = ok and all(math.hypot(pos[0] - q[0], pos[2] - q[1]) > 22 for q in avoid_pts)
            if ok:
                y = terr.height(pos[0], pos[2])
                pos = (pos[0], y, pos[2])
                box = world_aabb(ident, pos, step)
                occupied.append(box)
                placed.append((ident, donor, pos, step, caption))
                s += along + 18.0
                break
            if tries % 2 == 1:
                s += 12.0
            tries += 1
        else:
            print('   could not place', ident, 'in', zone_name)
    return placed


def convert_buildings(folder, terr):
    types, trailer = mapio.read_buildings(SRC + 'buildings.bin')
    recs = mapio.split_records(SRC + 'buildings_game.bin', types)
    rng = random.Random(42)
    huts = [i for i, r in enumerate(recs) if r.ident.startswith('DLC2_chatrc')]
    hutpos = [(recs[i].pos[0], recs[i].pos[2]) for i in huts]
    # --- strikes: replace huts in place ------------------------------------
    removed = {}   # type -> set of fragment indices removed
    ruins = 0
    weights = [w for _, w in RUIN_MIX]
    for s in STRIKES:
        for i in huts:
            r = recs[i]
            if math.hypot(r.pos[0] - s['gz'][0], r.pos[2] - s['gz'][1]) > s['inner']:
                continue
            piece = rng.choices([n for n, _ in RUIN_MIX], weights)[0] if rng.random() < RUIN_FRACTION else rng.choice(['mm_barricade', 'mm_totem', 'mm_scrap_wall', 'mm_road_wreck'])
            removed.setdefault(r.ident, set()).add(r.fragidx)
            pos = (r.pos[0], r.pos[1], r.pos[2])
            step = r.rotstep
            city = r.u32(0x100)
            types.setdefault(piece, []).append(make_frag(piece, pos, step))
            recs[i] = make_record(RUIN_DONOR, piece, pos, step, len(types[piece]) - 1, city)
            ruins += 1
    # renumber fragment indices of the hut types after removals
    for tname, gone in removed.items():
        keep = [i for i in range(len(types[tname])) if i not in gone]
        remap = {old: new for new, old in enumerate(keep)}
        types[tname] = [types[tname][i] for i in keep]
        for r in recs:
            if r.ident == tname:
                r.set_fragidx(remap[r.fragidx])
    # --- start kit ---------------------------------------------------------
    gz = STRIKES[0]['gz']
    capital_city = max(set(recs[i].u32(0x100) for i in huts if math.hypot(recs[i].pos[0] - gz[0], recs[i].pos[2] - gz[1]) < 300),
                       key=lambda c: sum(1 for i in huts if recs[i].u32(0x100) == c))
    occupied = [r_aabb for r_aabb in (world_aabb_of(recs[i], types) for i in range(len(recs)) if abs(recs[i].pos[0] - gz[0]) < 1500 and abs(recs[i].pos[2] - gz[1]) < 1500)]
    placed_all = []
    kit_by_zone = {}
    for e in KIT:
        kit_by_zone.setdefault(e[3], []).append(e)
    for zone, entries in kit_by_zone.items():
        placed = layout_zone(zone, entries, gz, terr, occupied, hutpos)
        placed_all += placed
        print('   zone %-10s placed %d/%d' % (zone, len(placed), len(entries)))
    index_of = {}
    for ident, donor, pos, step, caption in placed_all:
        types.setdefault(ident, []).append(make_frag(ident, pos, step))
        r = make_record(donor, ident, pos, step, len(types[ident]) - 1, capital_city)
        recs.append(r)
        index_of.setdefault(ident, []).append(len(recs) - 1)
        box = world_aabb(ident, pos, step)
        terr.flatten(box, pos[1], margin=3.0)
    # decor towers near the zones
    for ident, zone in DECOR:
        road = road_points_in(ZONES[zone], gz)
        if len(road) == 0:
            continue
        p = road[min(3, len(road) - 1)]
        pos = (float(p[0]) + 30.0, 0.0, float(p[2]) + 30.0)
        pos = (pos[0], terr.height(pos[0], pos[2]), pos[2])
        step = rng.randrange(STEPS)
        types.setdefault(ident, []).append(make_frag(ident, pos, step))
        recs.append(make_record(RUIN_DONOR, ident, pos, step, len(types[ident]) - 1, capital_city))
    # the layout code works with plain object names; the game wants '<item id>/<object>' for workshop types
    for r in recs:
        if r.ident in WIP:
            r.ident = game_ident(r.ident)
    types = {game_ident(k): v for k, v in types.items()}
    mapio.write_buildings(folder + 'buildings.bin', types, trailer)
    mapio.write_records(folder + 'buildings_game.bin', recs)
    return dict(ruins=ruins, kit=[(i, d, p, s, c) for i, d, p, s, c in placed_all], index_of=index_of, total=len(recs))


def world_aabb_of(rec, types):
    fr = types[rec.ident][rec.fragidx] if rec.ident in types and rec.fragidx < len(types[rec.ident]) else None
    if fr:
        return fr.aabb
    p = rec.pos
    return [p[0] - 8, p[1], p[2] - 8, p[0] + 8, p[1] + 5, p[2] + 8]


def clear_trees_under(folder, boxes):
    types = mapio.read_trees(folder + 'trees.bin')
    out = {}
    for name, recs in types.items():
        n = len(recs) // mapio.TREE_REC
        if n == 0:
            continue
        pos = mapio.tree_positions(recs)
        keep = np.ones(n, bool)
        for b in boxes:
            keep &= ~((pos[:, 0] > b[0] - 6) & (pos[:, 0] < b[3] + 6) & (pos[:, 2] > b[2] - 6) & (pos[:, 2] < b[5] + 6))
        arr = np.frombuffer(bytes(recs), dtype=np.uint8).reshape(n, mapio.TREE_REC)
        out[name] = bytearray(arr[keep].tobytes())
    mapio.write_trees(folder + 'trees.bin', out)



def write_pollution(folder):
    """Initial radiation in the game's 100x100 air-pollution grid (12-byte cells:
    radioactivity, pollution, bookkeeping; x-major, 200 m). The fallout plugin
    keeps it topped up afterwards; this makes the craters hot from the first second."""
    W = 100
    cells = np.zeros((W * W, 3), np.float32)
    cell = WORLD / W
    for xi in range(W):
        for zi in range(W):
            x = -WORLD / 2 + (xi + 0.5) * cell
            z = -WORLD / 2 + (zi + 0.5) * cell
            f = 0.0
            for s in STRIKES:
                d2 = (x - s['gz'][0]) ** 2 + (z - s['gz'][1]) ** 2
                sig = s['scorch'] * 0.7
                f = max(f, 1.5 * math.exp(-d2 / (sig * sig)))
            cells[xi * W + zi, 0] = f
    with open(folder + 'pollution.bin', 'wb') as fh:
        fh.write(struct.pack('<I', W * W))
        fh.write(cells.astype('<f4').tobytes())


# ---------------------------------------------------------------- scenario ---
def write_scenario(depot_index):
    os.makedirs(SCEN_OUT + 'yearzero', exist_ok=True)
    open(SCEN_OUT + 'workshopconfig.ini', 'w', newline='').write('\r\n'.join([
        '$ITEM_ID %d' % SCEN_ID, '', '$ITEM_TYPE WORKSHOP_ITEMTYPE_SCRIPT', '', '$VISIBILITY 2', '',
        '$ITEM_NAME "Korea Year Zero - start conditions"', '',
        '$ITEM_DESC "Scenario for the Korea Year Zero map: no people for sale, blueprints only from the scrap center, wrecked trucks in the motor pool."', '', '$END', '']))
    open(SCEN_OUT + 'script.ini', 'w', newline='').write('\r\n'.join([
        '$NAME_STR "Korea Year Zero"',
        '$DESCRIPTION_STR "The strike came at dawn. Three towns are craters, the rest is ash and silence. Rebuild from the rubble: repair the salvage trucks, crush the ruins into gravel and steel, feed the survivors, and call the wastes to come home."',
        '$END_TEXT_STR "The republic stands again."',
        '$AVAILABLE_ON_ALL_MAPS', '$END', '']))
    # the map auto-starts the scenario exactly like campaign1/stats.ini does
    open(OUT + 'stats.ini', 'w', newline='').write('$ScenarioAutoStart yearzero yearzero\r\n')
    open(SCEN_OUT + 'yearzero/script.ini', 'w', newline='').write('\r\n'.join([
        '$RUNSCRIPT start.txt', '$NAME_STR "Year Zero"',
        '$DESCRIPTION_STR "Salvage, recycle, farm. Then coal, bricks, concrete - and steel."',
        '$TREEXPOS 0', '$STARTUNLOCKED', '$END', '']))
    lines = ['include("SOVIETInstructions.txt");', '', 'defineVariable(int, winexi);', 'defineVariable(int, reunified);',
             'defineVariable(int, npeople);', 'defineVariable(int, i);', 'defineVariable(int, cnt);', 'defineVariable(float, sum);', 'defineVariable(float, avg);',
             'defineVariable(Person, p);', '', 'defineFunction(main, void)', '{',
             '\t// nobody sells people in the wasteland; survivors come on their own',
             '\tPermissions_ImmigrantAllowPurchaseRUB(0, 1.0);', '\tPermissions_ImmigrantAllowPurchaseUSD(0, 1.0);',
             '\t// no new vehicles from the border - blueprints come from the scrap center',
             '\tPermissions_VehicleAllowPurchaseRUB(0, 0, 0, 0, 0);', '\tPermissions_VehicleAllowPurchaseUSD(0, 0, 0, 0, 0);',
             '\tPermissions_BlueprintAllowRUB(0, 1, 1.0);', '\tPermissions_BlueprintAllowUSD(0, 1, 1.0);',
             '\t// border trade is expensive; the trade post is the way',
             '\tPermissions_ResourcesAllowPurchaseRUB(1, 1, 4.0);', '\tPermissions_ResourcesAllowPurchaseUSD(1, 1, 4.0);',
             '\tMoney_SetRUB(120000);', '\tMoney_SetUSD(4000);']
    for v in BLUEPRINTS:
        lines.append('\tScenario_AddRoadVehicleBlueprint("%s");' % game_ident(v))
    if depot_index is not None:
        for v in VEHICLES_IN_DEPOT:
            lines.append('\tScenario_AddRoadVehicleToBuilding(%d, "%s");' % (depot_index, game_ident(v)))
    lines += ['\tScenario_WindowWithImageLeft("Year Zero", "The strike came at dawn. What is left of the republic is a ring of huts around three craters. The salvage motor pool east of the capital still has a few trucks - get them to the repair yard. Then put the salvage crews on the ruins: the crusher turns rubble into gravel, the smelter turns scrap into steel. Feed the survivors and they will stay. Broadcast the distress call and more will come.", "yearzero.png", 3);',
              '\twinexi = 1;', '\twhile (winexi) { Scenario_WindowExists(winexi); }',
              '\tScenario_ObjectiveCreate("yz_salvage", "Salvage", "Repair the trucks in the motor pool, then put the salvage crews on the ruins. The crusher turns rubble into gravel, the smelter turns scrap into steel.");',
              '\tScenario_ObjectiveCreate("yz_fallout", "Fallout", "The craters are hot. Citizens who live, work or scavenge in the zones pick up a dose. Build a Decontamination Task Force with Geiger patrols, a Radiology Board with physicians, and a Recovery Center. Demolishing the ruins cools the zones.");',
              '\tScenario_ObjectiveCreate("yz_survivors", "Survivors", "Feed the huts and they stay. Run the Distress Beacon and more come in from the wastes - screen them, some arrive hot.");',
              '\tScenario_ObjectiveCreate("yz_reunify", "Reunification", "Earn the trust of the people: when average loyalty to the new republic passes 75 percent, the North Koreans become united Koreans.");',
              '\t// the reunification watch: average loyalty (fStatusSoviet) sampled over the citizens, twice a minute',
              '\treunified = 0;',
              '\twhile (!reunified)',
              '\t{',
              '\t\tScript_Sleep(30.0);',
              '\t\tPerson_GetNumberOfPeople(npeople);',
              '\t\tif (npeople > 200)',
              '\t\t{',
              '\t\t\tsum = 0.0; cnt = 0; i = 0;',
              '\t\t\twhile (i < npeople)',
              '\t\t\t{',
              '\t\t\t\tp.GetDataByIndex(i);',
              '\t\t\t\tif (p.nValidRead) { sum = sum + p.fStatusSoviet; cnt = cnt + 1; }',
              '\t\t\t\ti = i + 7;',
              '\t\t\t}',
              '\t\t\tif (cnt > 0) { avg = sum / cnt; }',
              '\t\t\tif (avg > 0.75) { reunified = 1; }',
              '\t\t}',
              '\t}',
              '\tScenario_ObjectiveSetCompleted("yz_reunify", 0, 1);',
              '\tScenario_WindowWithImageLeft("Reunification", "The people have chosen. Three craters, a ring of huts, and a republic that earned their trust: from today there are no North Koreans here, only Koreans.", "yearzero.png", 3);',
              '}', '']
    open(SCEN_OUT + 'yearzero/start.txt', 'w', newline='').write('\r\n'.join(lines))
    shutil.copy(PREVIEW, SCEN_OUT + 'yearzero/yearzero.png')
    shutil.copy(PREVIEW, SCEN_OUT + 'previewimage.png')
    # the scenario enumerator looks for icon.png/end.png beside each script.ini
    for f in ('icon.png', 'end.png', 'yearzero/icon.png'):
        shutil.copy(PREVIEW, SCEN_OUT + f)


# ---------------------------------------------------------------- preview ----
def write_preview(folder, terr):
    H = terr.H
    land = H > 0.0005
    shade = np.clip(H / max(H.max(), 1e-6), 0, 1) ** 0.6
    img = np.zeros((GRID, GRID, 3), np.float32)
    img[..., 0] = 0.45 + 0.35 * shade
    img[..., 1] = 0.40 + 0.30 * shade
    img[..., 2] = 0.30 + 0.20 * shade
    M = terr.M.astype(np.float32) / 255
    img = img * (1 - M[..., 1:2]) + np.array([0.12, 0.10, 0.09])[None, None] * M[..., 1:2]
    img = img * (1 - 0.5 * M[..., 0:1]) + np.array([0.62, 0.58, 0.48])[None, None] * 0.5 * M[..., 0:1]
    img[~land] = (0.16, 0.22, 0.27)
    im = Image.fromarray((np.clip(img, 0, 1) * 255).astype(np.uint8)).resize((512, 512), Image.LANCZOS)
    dr = ImageDraw.Draw(im)
    for s in STRIKES:
        c, r = wpx(*s['gz'])
        c, r = c / GRID * 512, r / GRID * 512
        dr.ellipse([c - 5, r - 5, c + 5, r + 5], outline=(255, 90, 40), width=2)
    im.save(folder + 'previewimage.png')


def write_config(folder):
    open(folder + 'workshopconfig.ini', 'w', newline='').write('\r\n'.join([
        '$ITEM_ID %d' % MAP_ID, '', '$ITEM_TYPE WORKSHOP_ITEMTYPE_LANDSCAPE', '', '$VISIBILITY 2', '',
        '$ITEM_NAME "Korea Year Zero"', '',
        '$ITEM_DESC "North Korea after the strike. Three towns are craters, the survivors hold the huts around them. Start kit east of the capital: motor pool, repair yard, salvage office, rubble crusher, scrap smelter, trade post, scrap center, survivors camp, farm. Built on BATON\'s North Korea map - Early start version (3753525456) and the World Maps DLC."', '', '$END', '']))


def main():
    if os.path.isdir(OUT):
        shutil.rmtree(OUT)
    shutil.copytree(SRC, OUT)
    for f in ('collision.dta',):   # regenerated by the engine from the edited heightmap
        if os.path.exists(OUT + f):
            os.remove(OUT + f)
    terr = Terrain(SRC)
    print('terrain: painting strikes')
    paint_strikes(terr)
    write_materials(OUT)
    print('trees: retyping/thinning')
    n = convert_trees(OUT)
    print('   trees left', n)
    print('buildings')
    info = convert_buildings(OUT, terr)
    print('   ruins placed', info['ruins'], 'records', info['total'])
    boxes = [world_aabb(i, p, s) for i, d, p, s, c in info['kit']]
    clear_trees_under(OUT, boxes)
    terr.write(OUT)
    write_pollution(OUT)
    write_preview(OUT, terr)
    write_config(OUT)
    depot = info['index_of'].get('muddy_depot', [None])[0]
    write_scenario(depot)
    # the map's stats.ini auto-starts scenarios/yearzero/yearzero, so the scenario is installed there too
    scen_dir = GAME + 'scenarios/yearzero/'
    if os.path.isdir(scen_dir):
        shutil.rmtree(scen_dir)
    shutil.copytree(SCEN_OUT, scen_dir)
    os.remove(scen_dir + 'workshopconfig.ini')
    os.makedirs(os.path.join(ROOT, 'build'), exist_ok=True)
    json.dump({'kit': [(i, d, list(p), s, c) for i, d, p, s, c in info['kit']], 'index_of': info['index_of'], 'ruins': info['ruins']},
              open(os.path.join(ROOT, 'build', 'yearzero_layout.json'), 'w'), indent=1)
    print('written', OUT, 'and', SCEN_OUT)


if __name__ == '__main__':
    main()
