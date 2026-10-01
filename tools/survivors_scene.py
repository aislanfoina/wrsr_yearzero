"""The survivors kit: Mercenary Camp, Distress Beacon, Survivor Shelter.

    blender -b --python tools/survivors_scene.py -- <texdir> <kitdir> <previewdir>

One workshop item with three buildings sharing a material folder, like the
map kit. Each is a vanilla type doing a vanilla job under a wasteland skin:

    Mercenary Camp    $TYPE_STORAGE holding food, meat, clothes, alcohol - the
                      survivors plugin pays mercenaries out of it
    Distress Beacon   $TYPE_BROADCAST $SUBTYPE_RADIO - a radio station
    Survivor Shelter  $TYPE_HOTEL - where survivors (tourists) stay
"""
import math
import os
import shutil
import sys

import bpy

TOOLS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, TOOLS)
import nmf  # noqa: E402
from mmkit import *  # noqa: E402,F401,F403
import mmkit  # noqa: E402

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
TEXDIR = argv[0] if len(argv) > 0 else 'build/textures'
KITDIR = argv[1] if len(argv) > 1 else 'mod/buildings/survivors_kit'
PREVIEW = argv[2] if len(argv) > 2 else 'build/survivors'
ITEM_ID = 9000006


def tent(b, center, size, yaw=0.0, mat=TARP):
    """Ridge tent: two leaning tarp panels on a pole, guy ropes, a rag door."""
    x, y, z = center
    w, h, d = size
    for s in (-1, 1):
        b.box(mat, (x + s * w * 0.27, y + h * 0.5, z), (w * 0.62, 0.05, d), yaw=yaw, roll=s * 62)
    b.rod(IRON, (x, y, z - d / 2), (x, y + h, z - d / 2), 0.04)
    b.rod(IRON, (x, y, z + d / 2), (x, y + h, z + d / 2), 0.04)
    b.beam(IRON, (x, y + h, z - d / 2), (x, y + h, z + d / 2), 0.04)
    for s in (-1, 1):
        b.rod(IRON, (x + s * w * 0.5, y + h * 0.35, z), (x + s * (w * 0.5 + 1.2), y, z), 0.015, segs=4)
    b.box(RED, (x, y + h * 0.35, z + d / 2 + 0.03), (w * 0.35, h * 0.7, 0.03), yaw=yaw)


def mercenary_camp(b):
    R = b.R
    b.box(GROUND, (0, -0.25, 0), (30, 0.5, 24))
    # fence with a gate at +Z
    b.wall_run(-14, -11, 14, -11, base_h=3.4)
    b.wall_run(14, -11, 14, 11, base_h=3.4)
    b.wall_run(-14, 11, -14, -11, base_h=3.4)
    b.wall_run(14, 11, 4, 11, base_h=3.4); b.wall_run(-4, 11, -14, 11, base_h=3.4)
    for tx in (-5.2, 5.2):
        b.box(RUST, (tx, 2.2, 11), (2.0, 4.4, 2.0)); b.spikes(tx, 4.4, 11, 4, spread=0.8)
    b.beam(IRON, (-5.2, 5.2, 11), (5.2, 5.2, 11), 0.2)
    b.box(RUST, (0, 4.6, 11), (7.0, 1.2, 0.12)); b.text(GLOW, 'MERCS', (0, 4.2, 11.08), 0.9, 0.08)
    b.skull((0, 5.6, 11), 0.7)
    # the store: containers with the goods, under a canopy - the storage itself
    for k, (mat, name) in enumerate(((RED, 'food'), (CORR, 'meat'), (RUST, 'clothes'), (IRON, 'alcohol'))):
        cx = -9 + k * 4.2
        b.container((cx, 1.25, -6.5), R.uniform(-3, 3), mat, size=(3.6, 2.5, 6.0))
        b.box(WOOD, (cx, 2.6, -3.3), (2.2, 0.5, 0.08)); b.text(BONE, name.upper(), (cx, 2.45, -3.25), 0.4, 0.04)
    for xx in (-11.5, 8.5):
        b.rod(IRON, (xx, -0.2, -9.5), (xx, 5.0, -9.5), 0.14); b.rod(IRON, (xx, -0.2, -3.0), (xx, 5.0, -3.0), 0.14)
    b.box(CORR, (-1.5, 5.1, -6.3), (21.0, 0.06, 7.5), pitch=-4)
    # tents and shacks
    tent(b, (-9, 0, 4), (3.6, 2.4, 4.5), yaw=8)
    tent(b, (-4, 0, 6), (3.0, 2.2, 4.0), yaw=-6, mat=RED)
    tent(b, (6, 0, 6.5), (3.6, 2.4, 4.5), yaw=15)
    b.shack((10.5, 0, 1.0), (4.5, 2.6, 3.6), yaw=-12)
    # fighting pit: tyre ring with a fire barrel, benches
    for k in range(12):
        a = k * 30.0
        b.tyre_stack(3.2 * math.cos(math.radians(a)), 3.2 * math.sin(math.radians(a)) - 1.0, 2)
    b.cyl(IRON, (0, 0, -1.0), 0.32, 0.9, segs=10); b.fire.append((0, 0.9, -1.0))
    b.cyl(GLOW, (0, 0.92, -1.0), 0.28, 0.06, segs=10)
    for s in (-1, 1):
        b.box(WOOD, (s * 5.5, 0.45, -1.0), (0.5, 0.08, 3.0)); b.box(WOOD, (s * 5.5, 0.2, -1.0), (0.3, 0.4, 0.3))
    # weapon racks: rods leaning on a frame, spikes, a drum row
    b.beam(IRON, (-12.5, 1.6, 8.5), (-6.5, 1.6, 8.5), 0.06); b.rod(IRON, (-12.5, 0, 8.5), (-12.5, 1.7, 8.5), 0.05); b.rod(IRON, (-6.5, 0, 8.5), (-6.5, 1.7, 8.5), 0.05)
    for k in range(9):
        b.rod(IRON, (-12.2 + k * 0.7, 0, 8.7), (-12.2 + k * 0.7 + R.uniform(-0.2, 0.2), 1.9, 8.2), 0.025, segs=4)
    for k in range(5):
        b.drum((9.5 + (k % 3) * 0.7, 0, -1.0 + (k // 3) * 0.7 + 7.0), yaw=R.uniform(0, 360))
    b.blob(IRON, (12.0, 0, 7.5), (1.6, 0.8, 1.4), jitter=0.3)
    b.flag(-13.2, 3.4, -10.4, mat=RED); b.flag(13.2, 3.4, 10.4, mat=RED)
    b.lamp(-3.0, 4.5, 9.5, arm=0.8, yaw=0); b.lamp(12.0, 4.0, -8.0, arm=0.8, yaw=180)
    b.tyre_stack(12.5, -10.0, 3); b.tyre_stack(-12.8, 6.5, 2)
    return 'Mercenary Camp'


def distress_beacon(b):
    R = b.R
    b.box(GROUND, (0, -0.25, 0), (26, 0.5, 26))
    b.wall_run(-12, -12, 12, -12, base_h=3.0); b.wall_run(12, -12, 12, 12, base_h=3.0)
    b.wall_run(12, 12, 3, 12, base_h=3.0); b.wall_run(-3, 12, -12, 12, base_h=3.0); b.wall_run(-12, 12, -12, -12, base_h=3.0)
    # the mast: a lattice tower with guy wires, dishes and a beacon light
    H_ = 34.0
    for px, pz in ((-1.8, -1.8), (1.8, -1.8), (-1.8, 1.8), (1.8, 1.8)):
        b.rod(IRON, (px, -0.2, pz), (px * 0.35, H_, pz * 0.35), 0.16, segs=8)
    for hh in range(3, int(H_), 3):
        s = 1.8 * (1 - 0.65 * hh / H_)
        for (a, c) in (((-1, -1), (1, -1)), ((1, -1), (1, 1)), ((1, 1), (-1, 1)), ((-1, 1), (-1, -1))):
            b.beam(IRON, (a[0] * s, hh, a[1] * s), (c[0] * s, hh, c[1] * s), 0.07)
        s2 = 1.8 * (1 - 0.65 * (hh + 3) / H_)
        b.beam(IRON, (-s, hh, -s), (s2, hh + 3, -s2), 0.05); b.beam(IRON, (s, hh, s), (-s2, hh + 3, s2), 0.05)
    b.rod(IRON, (0, H_, 0), (0, H_ + 6, 0), 0.06)
    b.box(GLOW, (0, H_ + 6.2, 0), (0.5, 0.5, 0.5)); b.box(RED, (0, H_ + 5.0, 0), (0.25, 1.4, 0.25))
    for k in range(4):
        a = k * 90 + 45
        b.rod(IRON, (0.6 * math.cos(math.radians(a)), H_ - 2, 0.6 * math.sin(math.radians(a))),
              (10.5 * math.cos(math.radians(a)), 0.2, 10.5 * math.sin(math.radians(a))), 0.025, segs=4)
        b.box(CONCRETE, (10.5 * math.cos(math.radians(a)), 0.4, 10.5 * math.sin(math.radians(a))), (1.2, 0.8, 1.2))
    for hh, ang, r in ((12.0, 30.0, 1.4), (20.0, 200.0, 1.1), (27.0, 110.0, 0.9)):
        x, z = 1.3 * math.cos(math.radians(ang)), 1.3 * math.sin(math.radians(ang))
        b.beam(IRON, (0, hh, 0), (x * 1.6, hh + 0.4, z * 1.6), 0.08)
        b.cyl(IRON, (x * 1.6, hh + 0.4, z * 1.6), r, 0.4, segs=12, r2=0.15, pitch=-40, yaw=ang)
    # the bunker: half-sunk container with generators, cables up the mast
    b.container((-6.5, 0.9, 4.0), 0, RUST, size=(6.0, 2.0, 2.4))
    b.box(CONCRETE, (-6.5, 0.15, 4.0), (7.5, 0.3, 4.0))
    b.box(IRON, (-6.5, 2.2, 4.0), (6.2, 0.4, 2.6)); b.blob(GRAVEL, (-6.5, 2.2, 4.0), (3.4, 0.9, 1.6), jitter=0.2)
    b.box(IRON, (-4.0, 1.0, 5.26), (0.9, 1.6, 0.05)); b.box(GLOW, (-3.5, 1.2, 5.28), (0.5, 0.4, 0.02))
    for k in range(2):
        gx = 6.0 + k * 3.0
        b.box(RED, (gx, 0.7, -5.0), (2.4, 1.4, 1.4)); b.cyl(IRON, (gx + 0.8, 1.4, -5.0), 0.12, 1.6, segs=8)
        b.box(STRIPES, (gx - 0.6, 1.45, -5.0), (0.9, 0.1, 1.3))
        b.fire.append((gx, 0.8, -5.0))
    b.rod(IRON, (-3.5, 2.4, 4.0), (0.5, 8.0, 0.5), 0.03, segs=4); b.rod(IRON, (6.0, 1.5, -5.0), (0.4, 6.0, -0.4), 0.03, segs=4)
    for k in range(6):
        b.drum((9.5 + (k % 3) * 0.7, 0, 3.0 + (k // 3) * 0.7), yaw=R.uniform(0, 360))
    b.fire.append((10.2, 0.5, 3.3))
    b.box(RUST, (0, 3.4, 12.0), (7.0, 1.4, 0.12)); b.text(GLOW, 'BEACON', (0, 3.0, 12.08), 0.9, 0.08)
    b.skull((-3.9, 3.7, 12.0), 0.5); b.skull((3.9, 3.7, 12.0), 0.5)
    b.flag(11.5, 3.0, -11.5, mat=RED); b.flag(-11.5, 3.0, 11.5, mat=TARP)
    b.lamp(-9.5, 4.0, -9.0, arm=0.8, yaw=0); b.lamp(9.5, 4.0, 9.5, arm=0.8, yaw=180)
    b.tyre_stack(-10.5, -6.0, 3); b.blob(IRON, (9.5, 0, -10.0), (2.0, 0.9, 1.7), jitter=0.3)
    return 'Distress Beacon'


def survivor_shelter(b):
    R = b.R
    b.box(GROUND, (0, -0.25, 0), (34, 0.5, 26))
    b.wall_run(-16, -12, 16, -12, base_h=3.2); b.wall_run(16, -12, 16, 12, base_h=3.2)
    b.wall_run(16, 12, 4, 12, base_h=3.2); b.wall_run(-4, 12, -16, 12, base_h=3.2); b.wall_run(-16, 12, -16, -12, base_h=3.2)
    # the hall: three containers end to end under a big tarp roof, plus bunk tents
    for k in range(3):
        b.container((-8 + k * 6.3, 1.25, -6), R.uniform(-2, 2), R.choice([RED, CORR, RUST]))
    b.box(WOOD, (-2, 2.6, -2.5), (20, 0.1, 1.2))      # a boardwalk along the doors
    for xx in (-12, -2, 8):
        b.rod(IRON, (xx, -0.2, -9.5), (xx, 5.8, -9.5), 0.14); b.rod(IRON, (xx, -0.2, -2.0), (xx, 5.8, -2.0), 0.14)
    b.box(TARP, (-2, 5.9, -5.9), (22, 0.06, 8.5), pitch=-5)
    for xx in (-12, -2, 8):
        b.beam(IRON, (xx, 5.8, -9.5), (xx, 5.8, -2.0), 0.12)
    for k in range(5):
        tent(b, (-12 + k * 6.0, 0, 5.0), (3.4, 2.3, 4.2), yaw=R.uniform(-10, 10), mat=R.choice([TARP, TARP, RED]))
    # water tower with a queue of drums, latrine shack, a cook fire
    for px, pz in ((-1.0, -1.0), (1.0, -1.0), (-1.0, 1.0), (1.0, 1.0)):
        b.rod(IRON, (13.0 + px, -0.2, -8.0 + pz), (13.0 + px * 0.8, 6.0, -8.0 + pz * 0.8), 0.1)
    b.cyl(RUST, (13.0, 6.0, -8.0), 1.4, 2.0, segs=14); b.cyl(IRON, (13.0, 8.0, -8.0), 1.45, 0.4, segs=14, r2=0.2)
    b.rod(IRON, (13.0, 6.0, -8.0), (13.0, 1.0, -8.0), 0.04); b.box(IRON, (13.0, 0.9, -7.2), (0.3, 0.3, 0.3))
    for k in range(4):
        b.drum((11.0 + k * 0.7, 0, -5.0), yaw=R.uniform(0, 360))
    b.shack((13.0, 0, 4.0), (2.4, 2.4, 2.4), yaw=5)
    b.cyl(IRON, (0, 0, 9.5), 0.32, 0.9, segs=10); b.fire.append((0, 0.9, 9.5)); b.cyl(GLOW, (0, 0.92, 9.5), 0.28, 0.06, segs=10)
    for k in range(6):
        a = k * 60
        b.box(WOOD, (2.2 * math.cos(math.radians(a)), 0.25, 9.5 + 2.2 * math.sin(math.radians(a))), (1.2, 0.5, 0.35), yaw=-a)
    # gate sign
    for tx in (-5.2, 5.2):
        b.box(CORR, (tx, 2.0, 12), (1.8, 4.0, 1.8)); b.spikes(tx, 4.0, 12, 3, spread=0.6)
    b.beam(IRON, (-5.2, 4.8, 12), (5.2, 4.8, 12), 0.18)
    b.box(RUST, (0, 4.2, 12), (7.0, 1.2, 0.12)); b.text(GLOW, 'SHELTER', (0, 3.8, 12.08), 0.85, 0.08)
    b.skull((0, 5.2, 12), 0.6)
    b.lamp(-6.5, 4.5, 10.5, arm=0.8, yaw=0); b.lamp(6.5, 4.5, 10.5, arm=0.8, yaw=180); b.lamp(-14.5, 4.0, -9.5, arm=0.8, yaw=0)
    b.flag(15.3, 3.2, -11.3, mat=RED); b.flag(-15.3, 3.2, 11.3, mat=TARP)
    b.tyre_stack(-14.5, 8.0, 3); b.tyre_stack(14.5, 9.5, 2); b.blob(RUST, (-14.0, 0, -8.5), (1.8, 0.8, 1.6), jitter=0.3)
    return 'Survivor Shelter'


# ------------------------------------------------------------------ inis --

COST = ['-------', '$COST_WORK SOVIET_CONSTRUCTION_GROUNDWORKS 0.0', '$COST_WORK_BUILDING_ALL', '$COST_RESOURCE_AUTO ground_asphalt 0.03',
        '------------------', '$COST_WORK SOVIET_CONSTRUCTION_STEEL_LAYING 1.0', '$COST_WORK_BUILDING_ALL', '$COST_RESOURCE_AUTO wall_steel 0.2',
        '-----------------------', '']


def ini_camp():
    return '\r\n'.join(['$NAME_STR "Mercenary Camp"', '',
        '; A warehouse for what mercenaries are paid in. The survivors plugin recognises',
        '; any storage holding food, meat, clothes and alcohol as a camp: a mercenary',
        '; only arrives at the border if a camp can pay, and the wage is taken from it',
        '; in kind instead of money.', ''] + COST + [
        '$TYPE_STORAGE',
        '$STORAGE_SPECIAL RESOURCE_TRANSPORT_COVERED 60 food',
        '$STORAGE_SPECIAL RESOURCE_TRANSPORT_COOLER  30 meat',
        '$STORAGE_SPECIAL RESOURCE_TRANSPORT_COVERED 30 clothes',
        '$STORAGE_SPECIAL RESOURCE_TRANSPORT_COVERED 30 alcohol', '',
        '$VEHICLE_STATION -2.0 0 -1.5  -2.0 0 8.5',
        '$VEHICLE_STATION  2.0 0 -1.5   2.0 0 8.5', '',
        '$CONNECTIONS_ROAD_DEAD_SQUARE', '-15.5 12.5', '15.5 -12.5', '',
        '$CONNECTION_ROAD', '0.0 0.0 14.0', '0.0 0.0 12.5',
        '$CONNECTION_PEDESTRIAN', '-6.5 0.0 12.5', '-6.5 0.0 14.0', '',
        'end', ''])


def ini_beacon():
    return '\r\n'.join(['$NAME_STR "Distress Beacon"', '',
        '; A radio station. The distress call carries as far as the loyalty broadcast',
        '; does, and the "distress broadcast" research doubles the survivors who answer.', ''] + COST + [
        '$TYPE_BROADCAST', '$SUBTYPE_RADIO',
        '$WORKERS_NEEDED 12',
        '$PROFESORS_NEEDED 2', '',
        '$VEHICLE_STATION 0.0 0 4.0  0.0 0 10.0', '',
        '$CONNECTIONS_ROAD_DEAD_SQUARE', '-13.5 13.5', '13.5 -13.5', '',
        '$CONNECTION_ROAD', '0.0 0.0 15.0', '0.0 0.0 13.5',
        '$CONNECTION_PEDESTRIAN', '-6.0 0.0 13.5', '-6.0 0.0 15.0', '',
        'end', ''])


def ini_shelter():
    return '\r\n'.join(['$NAME_STR "Survivor Shelter"', '',
        '; A hotel: where survivors (the game\'s tourists) stay while they decide.', ''] + COST + [
        '$TYPE_HOTEL',
        '$WORKERS_NEEDED 8',
        '$CITIZEN_ABLE_SERVE 3',
        '$ELETRIC_WITHOUT_WORKING_FACTOR 0.5',
        '$ELETRIC_WITHOUT_LIGHTING_FACTOR 0.2',
        '$ATTRACTIVE_SCORE 1.6',
        '$ATTRACTIVE_FACTOR_SIGHT 0.25', '$ATTRACTIVE_FACTOR_SIGHT_ADD 0.35',
        '$ATTRACTIVE_FACTOR_NATURE 0.25', '$ATTRACTIVE_FACTOR_NATURE_ADD 0.25',
        '$ATTRACTIVE_FACTOR_POLLUTION 0.25', '$ATTRACTIVE_FACTOR_POLLUTION_ADD 0.25',
        '$STORAGE_DEMAND_HOTEL RESOURCE_TRANSPORT_COVERED 16',
        '$STORAGE_DEMAND_HOTEL RESOURCE_TRANSPORT_COOLER 2', '',
        '$VEHICLE_STATION -2.0 0 -1.0  -2.0 0 9.5',
        '$VEHICLE_STATION  2.0 0 -1.0   2.0 0 9.5', '',
        '$CONNECTIONS_ROAD_DEAD_SQUARE', '-17.5 13.5', '17.5 -13.5', '',
        '$CONNECTION_ROAD', '0.0 0.0 15.0', '0.0 0.0 13.5',
        '$CONNECTION_PEDESTRIAN', '-7.0 0.0 13.5', '-7.0 0.0 15.0',
        '$CONNECTION_PEDESTRIAN', '7.0 0.0 13.5', '7.0 0.0 15.0', '',
        'end', ''])


ASSETS = [('mercenary_camp', mercenary_camp, ini_camp, (-40.0, 24.0, 44.0), (0.0, 2.0, -1.0)),
          ('distress_beacon', distress_beacon, ini_beacon, (-30.0, 22.0, 46.0), (0.0, 12.0, 0.0)),
          ('survivor_shelter', survivor_shelter, ini_shelter, (-40.0, 24.0, 46.0), (0.0, 2.0, -1.0))]

RENDERCONFIG = '''$TYPE_WORKSHOP
 MODEL model.nmf
 MATERIAL ../material/%(n)s.mtl
 MATERIALEMISSIVE ../material/%(n)s_e.mtl
 LIFE 2200.000000
 EXPLOSION_GROUP 0
 DERBIS_FALLING_FX buildingfall1 1.000000
 DERBIS_FALLED_FX buildingfall2 1.400000
 DERBIS_FALLED_SFX collapse
 DERBIS_NUM 6
 DERBIS_FALLING_FX_MAXTIME 3.000000
 DERBIS_SCALE 0.700000
 DERBIS_MESH buildings/buildingwreck1.nmf buildings/buildingwreck.mtl
 END
'''.replace('\n', '\r\n')


def main():
    mmkit.clear_scene()
    os.makedirs(KITDIR, exist_ok=True); os.makedirs(PREVIEW, exist_ok=True)
    matdir = os.path.join(KITDIR, 'material'); os.makedirs(matdir, exist_ok=True)
    for name in MATS + ['tp_black']:
        shutil.copy(os.path.join(TEXDIR, name + '.dds'), os.path.join(matdir, name + '.dds'))
    bmats = mmkit.blender_materials(TEXDIR)
    mmkit.lighting()
    cfg = ['$ITEM_ID %d' % ITEM_ID, '', '$ITEM_TYPE WORKSHOP_ITEMTYPE_BUILDING', '', '$VISIBILITY 2', '']
    for key, fn, ini, cam, tgt in ASSETS:
        b = Builder(seed=hash(key) & 0xFFFF)
        title = fn(b)
        shapes, used = b.export_shapes()
        model = nmf.Model(); model.materials = used; model.shapes = shapes
        adir = os.path.join(KITDIR, key); os.makedirs(adir, exist_ok=True)
        nmf.write(model, os.path.join(adir, 'model.nmf'))
        bbox = mmkit.model_bbox(shapes)
        mmkit.write_bbox_file(os.path.join(adir, 'building.bbox'), shapes)
        mmkit.write_fire_file(os.path.join(adir, 'building.fire'), b.fire)
        mmkit.write_text(os.path.join(adir, 'building.ini'), ini())
        mmkit.write_text(os.path.join(adir, 'renderconfig.ini'), RENDERCONFIG % {'n': key})
        mmkit.write_text(os.path.join(matdir, key + '.mtl'), mmkit.mtl_text(used, ''))
        mmkit.write_text(os.path.join(matdir, key + '_e.mtl'), mmkit.mtl_text(used, '', emissive=True))
        cfg.append('$OBJECT_BUILDING %s' % key)
        obs = b.preview_objects(bmats, key)
        mmkit.render(os.path.join(PREVIEW, key + '.png'), cam, tgt, (1400, 900), samples=32)
        pos, t2 = mmkit.frame_camera(bbox, azimuth_deg=-30, elevation_deg=34, fill=1.05)
        mmkit.render(os.path.join(PREVIEW, key + '_icon.png'), pos, t2, (384, 384), transparent=True, samples=24)
        mmkit.save_scaled_png(os.path.join(PREVIEW, key + '_icon.png'), os.path.join(adir, 'imagegui.png'), 96, 96)
        for ob in obs:
            bpy.data.objects.remove(ob)
        b.free()
        print('%-18s %-18s tris=%5d nodes=%d bbox=%s fire=%d' % (key, title, sum(s.nt for s in shapes), len(shapes), ['%.1f' % v for v in bbox], len(b.fire)))
    cfg += ['', '$ITEM_NAME "Survivors Kit"', '', '$ITEM_DESC "Mercenary Camp, Distress Beacon and Survivor Shelter for the wasteland population game."', '', '$END', '']
    mmkit.write_text(os.path.join(KITDIR, 'workshopconfig.ini'), '\r\n'.join(cfg))
    print('survivors kit done')


main()
