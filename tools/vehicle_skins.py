"""Mad Max paint variants for vanilla vehicles.

For each vehicle: decode the vanilla diffuse, work out from the mesh which
texture pixels are hood / roof / sides / front / back (so decals land on body
panels and windows stay black), then weather it into a few variants:

    wasteland   rust, dust, chips, grime streaks
    warboy      the above plus chalk-white smears, a skull, a V8 mark, tallies
    black       matte-black repaint (the Interceptor)

Writes build/vehicles/<key>/skin_<sub>_<variant>.{png,dds} and a manifest the
Blender step reads. Run with the system Python (needs PIL + numpy):

    python tools/vehicle_skins.py build/vehicles
"""
import json
import math
import os
import re
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

TOOLS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, TOOLS)
import nmf  # noqa: E402
import tradepost_textures as tt  # noqa: E402

MEDIA = os.environ.get('WRSR_GAME', r'C:\Program Files (x86)\Steam\steamapps\common\SovietRepublic').rstrip('/\\') + '/media_soviet/'
VEH = MEDIA + 'vehicles/'

# key -> vanilla folder, display name, variants (first is material.mtl), item id
VEHICLES = {
    'interceptor': dict(src='personal_s110r', name='Wasteland Interceptor', variants=['black', 'wasteland', 'warboy'], item=9000011,
                        desc='A pursuit coupe that outlived the police force. Supercharged, side-piped, and last of the V8s.'),
    'nux': dict(src='personal_m21', name='War Boy Coupe', variants=['warboy', 'wasteland', 'black'], item=9000012,
                desc='Chalk-white and chrome. Witness the fuel tanks.'),
    'buzzard': dict(src='personal_trabi', name='Buzzard Spike Car', variants=['wasteland', 'warboy'], item=9000013,
                    desc='Two-stroke terror of the salt flats. Every panel is a weapon.'),
    'warrig': dict(src='oil_t815_trail', name='War Rig', variants=['wasteland', 'warboy'], item=9000014, joint=True,
                   desc='Tatra 815 tractor and tanker. Guzzoline for the Citadel.'),
    'raider': dict(src='covered_gz_66', name='Raider Truck', variants=['wasteland', 'warboy'], item=9000015,
                   desc='4x4 raid truck with a turret ring and armour plate. Carries whatever it takes.'),
    'warbus': dict(src='bus_ikr_55', name='Wasteland War Bus', variants=['wasteland', 'warboy'], item=9000016,
                   desc='Barred windows, a fighting platform on the roof, a plow up front. Fifty souls.'),
    # ---- rail
    'warloco': dict(base='trains', src='russian_loco_m62', name='Iron Hog Locomotive', variants=['warboy', 'wasteland', 'black'], item=9000021,
                    desc='M62 diesel with a plow, armour over the cab and a cage on the roof. It does not stop for anything.'),
    'shunter': dict(base='trains', src='russian_loco_cme3', name='Scrap Shunter', variants=['wasteland', 'warboy'], item=9000022,
                    desc='CME3 yard engine, caged and spiked. Drags the wrecks in.'),
    'warflat': dict(base='trains', src='russian_vagon_open', name='Battle Flatcar', variants=['wasteland', 'warboy'], item=9000023,
                    desc='A flatcar with a gun nest, a chained-down wreck and sandbags. Carries anything you can lash to it.'),
    'warhopper': dict(base='trains', src='russian_vagon_gravel', name='Armoured Hopper', variants=['wasteland', 'warboy'], item=9000024,
                      desc='Open hopper plated over, spikes on the rim, a lookout at one end. Gravel for the walls.'),
    'wartank': dict(base='trains', src='russian_vagon_tank', name='Guzzoline Tank Car', variants=['warboy', 'wasteland'], item=9000025,
                    desc='Every drop is a war. Skull on the end, catwalk cage on top.'),
    'warbox': dict(base='trains', src='russian_vagon_covered', name='War Boy Boxcar', variants=['warboy', 'wasteland'], item=9000026,
                   desc='Plated boxcar with firing slits and a fighting platform on the roof. Barracks on rails.'),
    'prisoncar': dict(base='trains', src='russian_vagon_passanger', name='Prison Car', variants=['wasteland', 'warboy'], item=9000027,
                      desc='Barred windows, plated ends, a watch platform on the roof. Passengers, willing or not.'),
    # ---- ships
    'rustbarge': dict(base='ships', src='small_barge', name='Rust Barge', variants=['wasteland', 'warboy'], item=9000031,
                      desc='River barge with a ram on the bow, spikes on the gunwales and a cage over the wheelhouse.'),
    'guzzotanker': dict(base='ships', src='type587', name='Guzzoline Tanker', variants=['warboy', 'wasteland'], item=9000032,
                        desc='Type-587 tanker under new ownership. Skull on the bow, plates on the hull, a nest on the bridge.'),
    'raidership': dict(base='ships', src='ighnatov', name='Raider Freighter', variants=['wasteland', 'warboy'], item=9000033,
                       desc='A cargo ship turned raiding base: spiked bow, a watchtower on deck, plates along the hull.'),
    'skimmer': dict(base='ships', src='meteor', name='Wasteland Skimmer', variants=['warboy', 'wasteland', 'black'], item=9000034,
                    desc='Meteor hydrofoil, caged and spiked. Nothing on the water is faster.'),
    # ---- contamination kit (police car / prison bus skills kept)
    'geiger': dict(src='z_police_vz2109', name='Geiger Patrol', variants=['wasteland', 'black'], item=9000017, keep_skill=True,
                   desc='VAZ-2109 with a dish on the roof and a counter on the dash. Sent to every contamination report.'),
    'quarantine': dict(src='z_police_b1000_prison', name='Quarantine Bus', variants=['wasteland', 'warboy'], item=9000018, keep_skill=True,
                       desc='B1000 with barred windows and a tank on the roof. Takes the contaminated to the Recovery Center and the convalescent crews to work.'),
}

rng = np.random.default_rng(3)


# -------------------------------------------------------------- mtl parse --

def parse_mtl(path):
    """-> list of {name, tex: {slot: (kind, path)}, lines}"""
    subs = []
    cur = None
    for raw in open(path, encoding='utf-8', errors='ignore').read().splitlines():
        line = raw.strip()
        m = re.match(r'\$SUBMATERIAL\s+(\S+)', line)
        if m:
            cur = {'name': m.group(1), 'tex': {}, 'extra': []}
            subs.append(cur)
            continue
        if cur is None:
            continue
        m = re.match(r'\$(TEXTURE_MTL|TEXTURE)\s+(\d+)\s+(\S+)', line)
        if m:
            cur['tex'][int(m.group(2))] = (m.group(1), m.group(3))
            continue
        if line.startswith('$END'):
            break
        if line.startswith('$'):
            cur['extra'].append(line)
    return subs


def resolve_tex(folder, kind, path):
    if kind == 'TEXTURE_MTL':
        return os.path.join(folder, path)
    p = os.path.join(MEDIA, path)
    if os.path.exists(p):
        return p
    p2 = os.path.join(MEDIA, 'buildings', path)
    return p2 if os.path.exists(p2) else p


def media_path(folder, kind, path):
    """The same texture, as a path usable from another item folder."""
    if kind == 'TEXTURE':
        return ('TEXTURE', path)
    rel = os.path.relpath(os.path.join(folder, path), MEDIA).replace(os.sep, '/')
    return ('TEXTURE', rel)


# ---------------------------------------------------------------- masks ----

CLASSES = ['hood', 'roof', 'trunk', 'side', 'front', 'back', 'bottom']


def uv_masks(models, mat_index, size):
    """Rasterise the triangles of material mat_index into per-class masks."""
    W, H = size
    masks = {c: Image.new('L', (W, H), 0) for c in CLASSES}
    draws = {c: ImageDraw.Draw(masks[c]) for c in CLASSES}
    # vehicle extent for hood/roof/trunk split
    zs = [z for m in models for s in m.shapes if s.node_type == 0 for z in s.pos[2::3]]
    zmin, zmax = min(zs), max(zs)
    for m in models:
        for s in m.shapes:
            if s.node_type != 0 or s.name.lower().startswith('tire'):
                continue
            for first, count, mat in s.subsets:
                if mat != mat_index:
                    continue
                for t in range(first // 3, (first + count) // 3):
                    a, b, c = s.indices[3 * t], s.indices[3 * t + 1], s.indices[3 * t + 2]
                    P = [s.pos[3 * i:3 * i + 3] for i in (a, b, c)]
                    e1 = [P[1][i] - P[0][i] for i in range(3)]
                    e2 = [P[2][i] - P[0][i] for i in range(3)]
                    n = (e1[1] * e2[2] - e1[2] * e2[1], e1[2] * e2[0] - e1[0] * e2[2], e1[0] * e2[1] - e1[1] * e2[0])
                    L = math.sqrt(sum(v * v for v in n)) or 1.0
                    n = [v / L for v in n]
                    cz = sum(p[2] for p in P) / 3.0
                    f = (cz - zmin) / max(1e-6, zmax - zmin)
                    if n[1] > 0.6:
                        cls = 'hood' if f > 0.62 else 'trunk' if f < 0.3 else 'roof'
                    elif n[1] < -0.6:
                        cls = 'bottom'
                    elif abs(n[0]) > 0.7:
                        cls = 'side'
                    elif n[2] > 0.7:
                        cls = 'front'
                    elif n[2] < -0.7:
                        cls = 'back'
                    else:
                        continue
                    poly = [((s.uv[2 * i] % 1.0) * W, (s.uv[2 * i + 1] % 1.0) * H) for i in (a, b, c)]
                    # skip triangles that wrap around the texture edge
                    if max(p[0] for p in poly) - min(p[0] for p in poly) > W * 0.6 or max(p[1] for p in poly) - min(p[1] for p in poly) > H * 0.6:
                        continue
                    draws[cls].polygon(poly, fill=255)
    return {c: np.asarray(masks[c]).astype(np.float32) / 255.0 for c in CLASSES}


def largest_region(mask, min_frac=0.004):
    """Bounding box (x0, y0, x1, y1) of the largest connected blob of a mask."""
    H, W = mask.shape
    small = np.asarray(Image.fromarray((mask * 255).astype(np.uint8)).resize((256, 256), Image.BOX)) > 96
    lab = np.zeros(small.shape, np.int32)
    best = None; bestn = 0; cur = 0
    for y in range(256):
        for x in range(256):
            if small[y, x] and lab[y, x] == 0:
                cur += 1
                stack = [(y, x)]; lab[y, x] = cur; n = 0
                ys = [y]; xs = [x]
                while stack:
                    cy, cx = stack.pop(); n += 1
                    for ny, nx in ((cy - 1, cx), (cy + 1, cx), (cy, cx - 1), (cy, cx + 1)):
                        if 0 <= ny < 256 and 0 <= nx < 256 and small[ny, nx] and lab[ny, nx] == 0:
                            lab[ny, nx] = cur; stack.append((ny, nx)); ys.append(ny); xs.append(nx)
                if n > bestn:
                    bestn = n; best = (min(xs), min(ys), max(xs) + 1, max(ys) + 1)
    if best is None or bestn < 256 * 256 * min_frac:
        return None
    return (best[0] * W / 256.0, best[1] * H / 256.0, best[2] * W / 256.0, best[3] * H / 256.0)


# ------------------------------------------------------------ weathering ---

def noise(n, cells, octaves=4, p=0.5):
    return tt._tile_noise(n, cells, octaves, p)


def weather(img, rust=0.5, dust=0.5, desat=0.4, dark=0.18, chips=0.3, protect=None):
    H, W, _ = img.shape
    n = max(H, W)
    lum = img.mean(-1)
    if protect is None:
        protect = lum < 0.09
    keep = (~protect)[..., None].astype(np.float32)
    g = lum[..., None]
    out = img * (1 - desat) + g * desat
    out = out * (1 - dark)
    # dust: warm low-frequency multiply, heavier low on the texture
    d = noise(n, 6, 4)[:H, :W]
    tint = np.array([1.0, 0.93, 0.82], np.float32)
    out = out * (1 - dust * 0.35 * (1 - d)[..., None] * keep) * (1 - dust * 0.15 * keep) + out * tint * dust * 0.15 * keep
    # rust patches
    r = noise(n, 9, 5)[:H, :W]
    fine = noise(n, 60, 2)[:H, :W]
    m = np.clip((r - (0.72 - 0.25 * rust)) * 4.0, 0, 1) * keep[..., 0]
    rustcol = np.stack([0.42 + 0.25 * fine, 0.20 + 0.12 * fine, 0.08 + 0.05 * fine], -1)
    out = out * (1 - m[..., None] * 0.85) + rustcol * (m[..., None] * 0.85)
    # paint chips: small bright/dark speckles
    c = noise(n, 80, 2)[:H, :W]
    chipm = ((c > 0.74) & (protect == False)).astype(np.float32) * chips
    out = out * (1 - chipm[..., None]) + np.array([0.35, 0.3, 0.26], np.float32) * chipm[..., None]
    # grime streaks running down
    streak = np.cumsum(noise(n, 40, 2)[:H, :W] - 0.5, axis=0)
    streak = tt._norm(np.mod(streak, 5.0))
    sm = ((streak > 0.82).astype(np.float32) * 0.35 * keep[..., 0])
    out = out * (1 - sm[..., None] * 0.6)
    return np.clip(out, 0, 1)


def matte_black(img, protect=None):
    lum = img.mean(-1)
    if protect is None:
        protect = lum < 0.09
    mx = img.max(-1); mn = img.min(-1)
    sat = (mx - mn) / np.maximum(mx, 1e-6)
    paint = (~protect) & ((sat > 0.12) | (lum > 0.32))
    out = img.copy()
    out[paint] = img[paint] * 0.16 + 0.035
    return out


def chalk(img, masks, protect, strength=0.55):
    H, W, _ = img.shape
    n = max(H, W)
    where = np.clip(masks['side'] + masks['hood'] + masks['roof'] + masks['trunk'] + masks['front'], 0, 1)
    s = noise(n, 5, 4)[:H, :W]
    s2 = noise(n, 30, 2)[:H, :W]
    m = np.clip((s - 0.52) * 5, 0, 1) * where * (~protect) * strength
    col = np.stack([0.86 + 0.1 * s2, 0.85 + 0.1 * s2, 0.80 + 0.1 * s2], -1)
    return img * (1 - m[..., None]) + col * m[..., None]


# ---------------------------------------------------------------- decals ---

def _font(size):
    for f in ('impact.ttf', 'arialbd.ttf', 'arial.ttf'):
        p = os.path.join('C:/Windows/Fonts', f)
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def draw_skull(d, cx, cy, s, col=(235, 230, 215, 235)):
    if s < 10:
        return
    d.ellipse([cx - s * 0.5, cy - s * 0.62, cx + s * 0.5, cy + s * 0.22], fill=col)
    d.rectangle([cx - s * 0.34, cy + 0.1 * s, cx + s * 0.34, cy + s * 0.5], fill=col)
    for ex in (-0.2, 0.2):
        d.ellipse([cx + ex * s - s * 0.13, cy - s * 0.25, cx + ex * s + s * 0.13, cy + s * 0.0], fill=(15, 12, 10, 255))
    d.polygon([(cx, cy + 0.02 * s), (cx - s * 0.07, cy + 0.2 * s), (cx + s * 0.07, cy + 0.2 * s)], fill=(15, 12, 10, 255))
    for k in range(-3, 4):
        d.line([(cx + k * s * 0.09, cy + s * 0.3), (cx + k * s * 0.09, cy + s * 0.5)], fill=(15, 12, 10, 255), width=max(1, int(s * 0.02)))


def draw_v8(d, cx, cy, s):
    if s < 14:
        return
    d.rounded_rectangle([cx - s * 0.5, cy - s * 0.32, cx + s * 0.5, cy + s * 0.32], radius=s * 0.1, outline=(240, 235, 220, 240), width=max(2, int(s * 0.05)))
    f = _font(max(8, int(s * 0.5)))
    d.text((cx, cy), 'V8', font=f, fill=(240, 235, 220, 240), anchor='mm')


def draw_tally(d, cx, cy, s, groups=3):
    for g in range(groups):
        x0 = cx - s * 0.5 + g * s * 0.38
        for k in range(4):
            d.line([(x0 + k * s * 0.07, cy - s * 0.15), (x0 + k * s * 0.07, cy + s * 0.15)], fill=(20, 18, 16, 230), width=max(1, int(s * 0.025)))
        d.line([(x0 - s * 0.03, cy + s * 0.12), (x0 + s * 0.27, cy - s * 0.12)], fill=(20, 18, 16, 230), width=max(1, int(s * 0.025)))


def draw_stripes_band(d, box, s):
    x0, y0, x1, y1 = box
    cy = (y0 + y1) / 2
    band = (y0, y1) if (y1 - y0) < s * 1.5 else (cy - s * 0.35, cy + s * 0.35)
    d.rectangle([x0, band[0], x1, band[1]], fill=(30, 28, 26, 230))
    step = s * 0.35
    x = x0 - (band[1] - band[0])
    while x < x1:
        d.polygon([(x, band[1]), (x + step, band[1]), (x + step + (band[1] - band[0]), band[0]), (x + (band[1] - band[0]), band[0])], fill=(225, 185, 35, 230))
        x += step * 2
    d.rectangle([x0, band[0] - 3, x1, band[0]], fill=(20, 18, 16, 230))
    d.rectangle([x0, band[1], x1, band[1] + 3], fill=(20, 18, 16, 230))


def decals(img, masks, kind, seed):
    """Composite RGBA decals into the body regions. Returns float RGB."""
    H, W, _ = img.shape
    base = Image.fromarray((np.clip(img, 0, 1) * 255).astype(np.uint8), 'RGB').convert('RGBA')
    layer = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    R = np.random.default_rng(seed)
    hood = largest_region(masks['hood'])
    side = largest_region(masks['side'])
    trunk = largest_region(masks['trunk'])
    roof = largest_region(masks['roof'])
    front = largest_region(masks['front'])
    if kind == 'warboy':
        for box in (hood, roof):
            if box:
                s = min(box[2] - box[0], box[3] - box[1]) * 0.55
                draw_skull(d, (box[0] + box[2]) / 2, (box[1] + box[3]) / 2, s)
        if side:
            s = min(side[2] - side[0], side[3] - side[1]) * 0.5
            draw_v8(d, side[0] + (side[2] - side[0]) * 0.3, (side[1] + side[3]) / 2, s * 0.8)
            draw_tally(d, side[0] + (side[2] - side[0]) * 0.72, (side[1] + side[3]) / 2, s * 0.9)
        if trunk:
            s = min(trunk[2] - trunk[0], trunk[3] - trunk[1]) * 0.5
            draw_v8(d, (trunk[0] + trunk[2]) / 2, (trunk[1] + trunk[3]) / 2, s)
        if front:
            s = min(front[2] - front[0], front[3] - front[1]) * 0.45
            draw_skull(d, (front[0] + front[2]) / 2, (front[1] + front[3]) / 2, s)
    elif kind == 'wasteland':
        if side:
            s = min(side[2] - side[0], side[3] - side[1]) * 0.5
            draw_tally(d, side[0] + (side[2] - side[0]) * 0.7, (side[1] + side[3]) / 2, s * 0.8, groups=2)
        if hood:
            s = min(hood[2] - hood[0], hood[3] - hood[1]) * 0.4
            draw_v8(d, (hood[0] + hood[2]) / 2, (hood[1] + hood[3]) / 2, s * 0.8)
    elif kind == 'stripes':
        if side:
            s = min(side[2] - side[0], side[3] - side[1]) * 0.5
            draw_stripes_band(d, side, s)
    # blend only where not glass
    la = np.asarray(layer).astype(np.float32) / 255.0
    lum = img.mean(-1)
    a = la[..., 3:4] * (lum > 0.09)[..., None]
    out = img * (1 - a) + la[..., :3] * a
    return out


# ------------------------------------------------------------------ main ----

def build_variant(base, masks, variant, seed, tank=False):
    protect = base.mean(-1) < 0.09
    if variant == 'black':
        img = matte_black(base, protect)
        img = weather(img, rust=0.05, dust=0.3, desat=0.0, dark=0.05, chips=0.1, protect=protect)
    elif variant == 'warboy':
        img = weather(base, rust=0.4, dust=0.45, desat=0.5, dark=0.15, protect=protect)
        img = chalk(img, masks, protect)
        img = decals(img, masks, 'stripes' if tank else 'warboy', seed)
        if tank:
            img = decals(img, masks, 'warboy', seed + 1)
    else:
        img = weather(base, rust=0.6, dust=0.6, desat=0.45, dark=0.2, protect=protect)
        img = decals(img, masks, 'stripes' if tank else 'wasteland', seed)
    return img


def process(key, cfg, outroot):
    folder = os.path.join(MEDIA, cfg.get('base', 'vehicles'), cfg['src'])
    subs = parse_mtl(os.path.join(folder, 'material.mtl'))
    models = [nmf.read(os.path.join(folder, 'main.nmf'))]
    if cfg.get('joint'):
        models.append(nmf.read(os.path.join(folder, 'joint.nmf')))
    out = os.path.join(outroot, key)
    os.makedirs(out, exist_ok=True)
    manifest = {'src': cfg['src'], 'base': cfg.get('base', 'vehicles'), 'name': cfg['name'], 'desc': cfg.get('desc', ''), 'item': cfg['item'],
                'variants': cfg['variants'], 'joint': bool(cfg.get('joint')), 'keep_skill': bool(cfg.get('keep_skill')), 'subs': []}
    for si, sub in enumerate(subs):
        kind, path = sub['tex'].get(0, (None, None))
        entry = {'name': sub['name'], 'extra': sub['extra'], 'tex': {}, 'skins': {}}
        for slot, (k, p) in sub['tex'].items():
            entry['tex'][slot] = media_path(folder, k, p)
        if path:
            src = resolve_tex(folder, kind, path)
            base = np.asarray(Image.open(src).convert('RGB')).astype(np.float32) / 255.0
            H, W, _ = base.shape
            # which material index does this submaterial map to? by name, else by order
            names = [n.lower() for n in models[0].materials]
            mi = names.index(sub['name'].lower()) if sub['name'].lower() in names else min(si, len(names) - 1)
            masks = uv_masks(models, mi, (W, H))
            tank = any(k in sub['name'].lower() for k in ('oil', 'tank', 'cistern')) or 'cistern' in path.lower() or 'prives' in path.lower()
            for vi, variant in enumerate(cfg['variants']):
                img = build_variant(base, masks, variant, seed=100 * vi + si, tank=tank)
                fn = 'skin_%s_%s' % (sub['name'].replace('.', '_').replace(':', '_'), variant)
                im = Image.fromarray((np.clip(img, 0, 1) * 255).astype(np.uint8), 'RGB')
                im.save(os.path.join(out, fn + '.png'))
                tt.save_dds_mips(im, os.path.join(out, fn + '.dds'), 'DXT1')
                entry['skins'][variant] = fn + '.dds'
            print('  %-22s %s %dx%d -> %d variants%s' % (sub['name'], os.path.basename(src), W, H, len(cfg['variants']), ' (tank)' if tank else ''))
        manifest['subs'].append(entry)
    json.dump(manifest, open(os.path.join(out, 'manifest.json'), 'w'), indent=1)
    return manifest


ONLY = set(k for k in os.environ.get('MM_ONLY', '').split(',') if k)


def main(outroot):
    os.makedirs(outroot, exist_ok=True)
    allm = {}
    for key, cfg in VEHICLES.items():
        if ONLY and key not in ONLY:
            continue
        print('==', key, cfg['src'])
        allm[key] = process(key, cfg, outroot)
    json.dump(allm, open(os.path.join(outroot, 'manifest.json'), 'w'), indent=1)


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else 'build/vehicles')
