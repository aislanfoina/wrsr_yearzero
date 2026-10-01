"""README pictures for Republic in Ruins: the buildings and vehicles on wasteland terrain - dust,
dead grass and scorched patches under a hazy sky, dead trees - built from the mod's own files.

    blender -b --python tools/yearzero_readme_scene.py -- <outdir> [outpost,buildings,vehicles]

Buildings come from mod/buildings/<kit>/<object>/model.nmf with the kit textures
(build/textures/tp_*.png, tools/tradepost_textures.py); vehicles from
mod/vehicles/<key>/<key>/main.nmf with their skins (build/vehicles/<key>/, tools/vehicle_skins.py;
its manifest.json says which material wears which skin). Shared terrain, sky and camera helpers
are in tools/readme_scene.py. tools/yearzero_readme_images.py mirrors the renders the way the
game shows models and composes the README images.
"""
import json
import math
import os
import random
import sys

import bpy
import bmesh

TOOLS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, TOOLS)
import nmf  # noqa: E402
import mmkit  # noqa: E402
import readme_scene as RS  # noqa: E402
from mmkit import G  # noqa: E402

ROOT = os.path.dirname(TOOLS)
argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
OUT = argv[0] if argv else os.path.join(ROOT, 'build', 'yearzero_readme')
ONLY = set(argv[1].split(',')) if len(argv) > 1 and argv[1] else None
TEX = os.path.join(ROOT, 'build', 'textures')
SKINS = os.path.join(ROOT, 'build', 'vehicles')
MEDIA = os.environ.get('WRSR_GAME', r'C:\Program Files (x86)\Steam\steamapps\common\SovietRepublic') + r'\media_soviet'

HORIZON = (0.74, 0.66, 0.54)          # dust haze
ZENITH = (0.46, 0.48, 0.52)           # a grey sky that never quite clears
DUST = [(0.32, (0.10, 0.08, 0.05)), (0.48, (0.21, 0.16, 0.09)), (0.60, (0.17, 0.16, 0.08)), (0.70, (0.04, 0.035, 0.03))]

KITS = {'madmax_kit': ['mm_scrap_wall', 'mm_wall_tower', 'mm_watchtower', 'mm_shanty', 'mm_fuel_depot', 'mm_wreck_yard',
                       'mm_ruin_block', 'mm_road_wreck', 'mm_totem', 'mm_windpump', 'mm_barricade', 'mm_skull_gate'],
        'fallout_kit': ['dtf_station', 'radiology_board', 'recovery_center'],
        'survivors_kit': ['mercenary_camp', 'distress_beacon', 'survivor_shelter'],
        'trade_post': ['trade_post'], 'goods_post': ['goods_post'], 'junk_post': ['junk_post'],
        'scrap_center': ['scrap_center'], 'scrap_dock': ['scrap_dock']}
KIT_OF = {o: k for k, objs in KITS.items() for o in objs}
ROAD = ['interceptor', 'nux', 'buzzard', 'warrig', 'raider', 'warbus', 'geiger', 'quarantine']
RAIL = ['warloco', 'shunter', 'warflat', 'warhopper', 'wartank', 'warbox', 'prisoncar']
WATER = ['rustbarge', 'guzzotanker', 'raidership', 'skimmer']

_mats = {}


def material(name):
    """A kit texture by material name (tp_rust ...), or a neutral grey."""
    if name in _mats:
        return _mats[name]
    png = os.path.join(TEX, name + '.png')
    if os.path.exists(png):
        m = mmkit.image_material('yz_' + name, png, roughness=0.8)
        if name == 'tp_glow':
            nt = m.node_tree
            b = nt.nodes.get('Principled BSDF')
            nt.links.new(nt.nodes.get('Image Texture').outputs['Color'], b.inputs['Emission Color'])
            b.inputs['Emission Strength'].default_value = 2.0
    else:
        m = RS.flat_material('yz_grey_' + name, (0.45, 0.43, 0.40))
    _mats[name] = m
    return m


def vehicle_material(key, man, variant, name):
    """A vehicle material: its skin for this paint scheme, else the vanilla texture the .mtl names,
    else the kit texture of the same name."""
    for sub in man['subs']:
        if sub['name'] != name:
            continue
        skin = sub['skins'].get(variant)
        if skin:
            png = os.path.join(SKINS, key, skin.replace('.dds', '.png'))
            if os.path.exists(png):
                return mmkit.image_material('yz_%s_%s_%s' % (key, name, variant), png, roughness=0.7)
        tex = sub.get('tex', {}).get('0')
        if tex:
            p = os.path.join(MEDIA, tex[1].replace('/', os.sep))
            if os.path.exists(p):
                return mmkit.image_material('yz_van_%s' % tex[1].replace('/', '_'), p, roughness=0.6)
        return RS.flat_material('yz_vgrey', (0.35, 0.34, 0.32))
    return material(name)


def place(obs, x=0.0, z=0.0, yaw=0.0, y=0.0):
    """Game position (x, y, z) and a turn about the vertical axis (radians)."""
    for ob in obs:
        ob.location = G(x, y, z)
        ob.rotation_euler = (0.0, 0.0, yaw)
    return obs


def building(obj):
    kit = KIT_OF[obj]
    model = nmf.read(os.path.join(ROOT, 'mod', 'buildings', kit, obj, 'model.nmf'))
    obs = mmkit.add_nmf_object(model, obj, lambda i: material(model.materials[i]))
    return obs, mmkit.model_bbox(model.shapes)


def vehicle(key, variant=None):
    """A vehicle (the rig with its tanker behind), in its first paint scheme unless told otherwise."""
    man = json.load(open(os.path.join(SKINS, key, 'manifest.json')))
    man = man.get(key, man)
    variant = variant or man['variants'][0]
    folder = os.path.join(ROOT, 'mod', 'vehicles', key, key)
    model = nmf.read(os.path.join(folder, 'main.nmf'))
    obs = mmkit.add_nmf_object(model, key, lambda i: vehicle_material(key, man, variant, model.materials[i]))
    bbox = mmkit.model_bbox(model.shapes)
    joint = os.path.join(folder, 'joint.nmf')
    if os.path.exists(joint):
        tm = nmf.read(joint)
        tobs = mmkit.add_nmf_object(tm, key + '_trailer', lambda i: vehicle_material(key, man, variant, tm.materials[i]))
        tb = mmkit.model_bbox(tm.shapes)
        dz = (bbox[2] + 1.5) - tb[5]                  # its nose 1.5 m over the tractor's tail, as the previews hang it
        empty = bpy.data.objects.new(key + '_rig', None)
        bpy.context.scene.collection.objects.link(empty)
        for ob in tobs:
            ob.location = G(0.0, 0.0, dz)
        for ob in obs + tobs:
            ob.parent = empty
        bbox = (min(bbox[0], tb[0]), min(bbox[1], tb[1]), tb[2] + dz, max(bbox[3], tb[3]), max(bbox[4], tb[4]), bbox[5])
        return [empty], bbox, obs + tobs
    return obs, bbox, obs


def dead_trees(clear, seed=3, clusters=40, reach=2400.0):
    """Burnt forest: bare trunks with a few broken branches, in thin clusters. clear = game (x0, x1, z0, z1)."""
    rnd = random.Random(seed)
    bm = bmesh.new()
    x0, x1, z0, z1 = clear
    placed = 0
    for _ in range(clusters * 6):
        if placed >= clusters:
            break
        cx, cz = rnd.uniform(-reach, reach), rnd.uniform(-reach, reach)
        if x0 - 60 < cx < x1 + 60 and z0 - 60 < cz < z1 + 60:
            continue
        placed += 1
        rad = rnd.uniform(30, 90)
        for _t in range(int(rad * rnd.uniform(0.25, 0.5))):
            tx, tz = cx + rnd.gauss(0, rad * 0.5), cz + rnd.gauss(0, rad * 0.5)
            if x0 - 20 < tx < x1 + 20 and z0 - 20 < tz < z1 + 20:
                continue
            h = rnd.uniform(6.0, 13.0)
            parts = [(0.0, 0.0, h, 0.28, 0.0)]
            for _b in range(rnd.randint(1, 3)):
                parts.append((rnd.uniform(0, 6.28), rnd.uniform(0.4, 0.8) * h, rnd.uniform(1.5, 3.5), 0.1, rnd.uniform(0.6, 1.0)))
            for ang, base, length, r, tilt in parts:
                cone = bmesh.ops.create_cone(bm, cap_ends=True, segments=5, radius1=r, radius2=r * 0.25, depth=length)
                for v in cone['verts']:
                    v.co.z += length / 2
                    if tilt:
                        # lean the branch out along ang, then lift it to its height on the trunk
                        y, zz = v.co.z * math.sin(tilt), v.co.z * math.cos(tilt)
                        v.co.x, v.co.y, v.co.z = v.co.x + y * math.cos(ang), v.co.y + y * math.sin(ang), zz + base
                    v.co.x += tx
                    v.co.y -= tz
    me = bpy.data.meshes.new('deadwood')
    bm.to_mesh(me)
    bm.free()
    me.materials.append(RS.flat_material('yz_deadwood', (0.16, 0.13, 0.10)))
    ob = bpy.data.objects.new('deadwood', me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def water(size=3000.0):
    me = bpy.data.meshes.new('water')
    h = size / 2
    me.from_pydata([(-h, -h, 0.05), (h, -h, 0.05), (h, h, 0.05), (-h, h, 0.05)], [], [(0, 1, 2, 3)])
    m = bpy.data.materials.new('yz_water')
    m.use_nodes = True
    b = m.node_tree.nodes.get('Principled BSDF')
    b.inputs['Base Color'].default_value = (0.10, 0.13, 0.12, 1.0)
    b.inputs['Roughness'].default_value = 0.15
    me.materials.append(m)
    ob = bpy.data.objects.new('water', me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def track(length, z=0.0):
    """Ballast, sleepers and two rails along game z, rail tops at 0."""
    b = mmkit.Builder(seed=1, mats=['yz_gravel', 'yz_sleeper', 'yz_rail'], tile={'yz_gravel': 4.0, 'yz_sleeper': 2.0, 'yz_rail': 2.0})
    b.box(0, (0.0, -0.35, z), (4.0, 0.3, length))
    n = int(length / 0.9)
    for i in range(n):
        b.box(1, (0.0, -0.15, z - length / 2 + i * 0.9), (2.6, 0.14, 0.25))
    for x in (-0.76, 0.76):
        b.box(2, (x, -0.06, z), (0.08, 0.14, length))
    mats = [RS.flat_material('yz_gravel', (0.28, 0.26, 0.23)), RS.flat_material('yz_sleeper', (0.18, 0.13, 0.09)),
            RS.flat_material('yz_rail', (0.30, 0.28, 0.27))]
    obs = b.preview_objects(mats, 'track')
    b.free()
    return obs


def clear(obs):
    seen = set()
    for ob in obs:
        try:
            name = ob.name
        except ReferenceError:            # already gone (a rig's parts and its empty share the list)
            continue
        if name not in seen and name in bpy.data.objects:
            seen.add(name)
            bpy.data.objects.remove(bpy.data.objects[name], do_unlink=True)


# ------------------------------------------------------------------ scenes --

def tiles_buildings():
    for obj in KIT_OF:
        obs, bbox = building(obj)
        trees = dead_trees((bbox[0], bbox[3], bbox[2], bbox[5]), seed=sum(map(ord, obj)))
        pos, tgt = mmkit.frame_camera(bbox, azimuth_deg=-35, elevation_deg=24, fill=0.95)
        RS.render(os.path.join(OUT, 'b_%s.png' % obj), pos, tgt, (1000, 640), samples=32)
        clear(obs + [trees])


def tiles_vehicles():
    for key in ROAD + RAIL + WATER:
        roots, bbox, parts = vehicle(key)
        extra = []
        if key in RAIL:
            extra += track(bbox[5] - bbox[2] + 40.0, z=(bbox[2] + bbox[5]) / 2)
        if key in WATER:
            extra.append(water())
        trees = dead_trees((bbox[0] - 40, bbox[3] + 40, bbox[2] - 40, bbox[5] + 40), seed=sum(map(ord, key)))
        fb = (bbox[0], max(bbox[1], 0.0), bbox[2], bbox[3], bbox[4], bbox[5])
        pos, tgt = mmkit.frame_camera(fb, azimuth_deg=-40, elevation_deg=16, fill=1.05)
        RS.render(os.path.join(OUT, 'v_%s.png' % key), pos, tgt, (1000, 640), samples=32)
        clear(parts + roots + extra + [trees])


def outpost():
    """A trading outpost on a dirt road: camp, trade post, shelter and beacon on one side, the scrap
    center across the road, walls and towers round it, ruins beyond, the war party on the road."""
    road_half, gap, space = 6.0, 5.0, 10.0
    north = ['mm_watchtower', 'mercenary_camp', 'trade_post', 'survivor_shelter', 'distress_beacon', 'mm_wall_tower']
    south = ['mm_fuel_depot', 'scrap_center', 'mm_shanty', 'junk_post']
    obs, placed = [], []
    for row, turn in ((north, False), (south, True)):
        cursor = 0.0
        for obj in row:
            o, bb = building(obj)
            if not turn:
                x, z = cursor - bb[0], -(road_half + gap) - bb[5]
                cursor = x + bb[3] + space
            else:
                x, z = cursor + bb[3], road_half + gap + bb[5]
                cursor = x - bb[0] + space
            placed.append((obj, o, x, z, turn, bb))
    xs = [x + (b[0] if not t else -b[3]) for _o, _obs, x, _z, t, b in placed] + \
         [x + (b[3] if not t else -b[0]) for _o, _obs, x, _z, t, b in placed]
    shift = -(min(xs) + max(xs)) / 2
    length = max(xs) - min(xs)
    for obj, o, x, z, turn, bb in placed:
        place(o, x + shift, z, math.pi if turn else 0.0)
        obs += o
    # the gate across the road's west end, ruins and wrecks out in the dust
    o, bb = building('mm_skull_gate')
    obs += place(o, -length / 2 - 18.0, 0.0, math.pi / 2)
    rnd = random.Random(7)
    for i, obj in enumerate(['mm_ruin_block', 'mm_wreck_yard', 'mm_ruin_block', 'mm_road_wreck', 'mm_totem', 'mm_windpump',
                             'mm_scrap_wall', 'mm_ruin_block', 'mm_barricade', 'mm_shanty']):
        o, bb = building(obj)
        ang = -2.6 + i * 0.55
        r = rnd.uniform(140, 260)
        obs += place(o, r * math.cos(ang), -abs(r * math.sin(ang)) - 60.0, rnd.uniform(0, 6.28))
    # the road and the war party on it, heading east (game +x)
    rb = mmkit.Builder(seed=2, mats=['yz_dirt'], tile={'yz_dirt': 6.0})
    rb.box(0, (0.0, -0.12, 0.0), (length + 400.0, 0.3, road_half * 2))
    obs += rb.preview_objects([RS.flat_material('yz_dirt', (0.22, 0.19, 0.14))], 'road')
    rb.free()
    for key, x, lane in (('warrig', -0.18, -2.5), ('interceptor', 0.02, 2.4), ('raider', 0.2, -2.5), ('buzzard', 0.32, 2.4),
                         ('warbus', -0.4, 2.6)):
        roots, bbox, parts = vehicle(key)
        place(roots, x * length, lane, math.pi / 2)
        obs += parts + roots
    trees = dead_trees((-length / 2 - 40, length / 2 + 40, -300, 60), seed=9, clusters=60)
    cam = (-0.22 * length, 0.34 * length, 0.62 * length)
    RS.render(os.path.join(OUT, 'outpost.png'), cam, (0.05 * length, 2.0, -0.12 * length), (1600, 900), samples=48, fov=46)
    clear(obs + [trees])


def main():
    os.makedirs(OUT, exist_ok=True)
    mmkit.clear_scene()
    sun = mmkit.lighting(sun_energy=4.0)
    sun.data.color = (1.0, 0.86, 0.68)
    sun.rotation_euler = (math.radians(58), math.radians(10), math.radians(-40))
    RS.sky(HORIZON, ZENITH)
    RS.terrain(colors=DUST, haze_color=HORIZON)
    for name, fn in (('outpost', outpost), ('buildings', tiles_buildings), ('vehicles', tiles_vehicles)):
        if not ONLY or name in ONLY:
            fn()


main()
