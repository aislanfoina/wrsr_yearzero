"""The Scrap Center: a wasteland breaker's yard that is a vanilla scrapyard.

    blender -b --python tools/scrap_center_scene.py -- <texdir> <outdir> <previewdir>

$TYPE_SCRAPYARD, laid out like the vanilla large scrapping facility: road
bays for vehicles that drive in, a pass-through rail siding for trains, and a
vehicles-as-cargo intake. The scrap_center plugin adds the blueprint reward.

Game coordinates throughout: X east, Y up, Z south toward the road.
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
OUTDIR = argv[1] if len(argv) > 1 else 'mod/buildings/scrap_center/scrap_center'
PREVIEW = argv[2] if len(argv) > 2 else 'build'

# ------------------------------------------------------------------ layout --
HX, HZ = 31.0, 26.0            # half extents of the yard
RAIL_Z = -18.0                 # the siding runs along X here
BAYS = (-7.0, 0.0, 7.0)        # truck bays, along Z
BAY_FAR, BAY_NEAR = -6.0, 14.0
GATE = 10.0                    # half width of the gate at +Z


def build(b):
    R = b.R
    # ground, with a ballast strip for the siding
    b.box(GROUND, (0, -0.25, 0), (HX * 2 + 2, 0.5, HZ * 2 + 2))
    b.box(GRAVEL, (0, 0.02, RAIL_Z), (HX * 2 + 2, 0.06, 5.0))

    # ---- perimeter, open at the gate and where the siding crosses
    b.wall_run(-HX, -HZ, HX, -HZ)                         # back (north)
    b.wall_run(HX, -HZ, HX, RAIL_Z - 3.2)                 # east, north of the siding
    b.wall_run(HX, RAIL_Z + 3.2, HX, HZ)                  # east, south of it
    b.wall_run(-GATE, HZ, -HX, HZ)                        # front west of the gate
    b.wall_run(HX, HZ, GATE, HZ)                          # front east of the gate
    b.wall_run(-HX, HZ, -HX, RAIL_Z + 3.2)                # west
    b.wall_run(-HX, RAIL_Z - 3.2, -HX, -HZ)
    for (x, z) in ((-HX + 2, -HZ + 2), (HX - 2, -HZ + 2), (-HX + 2, HZ - 2), (HX - 2, HZ - 2)):
        b.spikes(x, 5.0, z, 4, spread=1.5)
        b.flag(x, 4.8, z, mat=R.choice([RED, TARP]))

    # ---- gate: two crushed-car pillars and a beam with the sign
    for tx in (-GATE - 1.5, GATE + 1.5):
        for k in range(5):
            b.box(R.choice([RED, RUST, IRON, CORR]), (tx + R.uniform(-0.15, 0.15), 0.4 + k * 0.8, HZ - 1.0), (2.0, 0.75, 4.0), yaw=R.uniform(-5, 5))
        b.spikes(tx, 4.4, HZ - 1.0, 5, spread=1.2)
    b.beam(IRON, (-GATE - 2.5, 6.8, HZ - 1.0), (GATE + 2.5, 6.8, HZ - 1.0), 0.3)
    b.beam(IRON, (-GATE - 2.5, 7.6, HZ - 1.0), (GATE + 2.5, 7.6, HZ - 1.0), 0.16)
    for k in range(8):
        x0 = -GATE - 2.5 + k * (2 * GATE + 5) / 8
        b.beam(IRON, (x0, 6.8, HZ - 1.0), (x0 + (2 * GATE + 5) / 8, 7.6, HZ - 1.0), 0.07)
    b.box(RUST, (0, 5.6, HZ - 1.0), (13.0, 2.0, 0.16), roll=1.5)
    b.box(STRIPES, (0, 4.5, HZ - 1.0), (13.0, 0.2, 0.2), roll=1.5)
    b.text(GLOW, 'SCRAP CENTER', (0, 5.0, HZ - 0.88), 1.35, 0.1)
    b.skull((0, 7.0, HZ - 0.7), 1.0)
    b.lamp(-GATE - 3.8, 5.5, HZ - 3.0, arm=0.9, yaw=0)
    b.lamp(GATE + 3.8, 5.5, HZ - 3.0, arm=0.9, yaw=180)
    b.tyre_stack(-GATE - 4.5, HZ + 1.5, 3); b.tyre_stack(GATE + 4.8, HZ + 1.2, 2)

    # ---- cutting canopy over the far end of the bays (the "disassembly floor")
    for zz in (BAY_FAR - 2.0, BAY_FAR + 4.0):
        for xx in (BAYS[0] - 3.0, BAYS[-1] + 3.0):
            b.rod(IRON, (xx, -0.2, zz), (xx, 6.8, zz), 0.16, segs=8)
        b.beam(IRON, (BAYS[0] - 3.0, 6.8, zz), (BAYS[-1] + 3.0, 6.8, zz), 0.24)
    for xx in (BAYS[0] - 3.0, BAYS[-1] + 3.0):
        b.beam(IRON, (xx, 6.8, BAY_FAR - 2.0), (xx, 6.8, BAY_FAR + 4.0), 0.24)
    for j, (xa, xb) in enumerate(((BAYS[0] - 3.5, -0.2), (0.2, BAYS[-1] + 3.5))):
        b.box(R.choice([CORR, RUST, TARP]), ((xa + xb) / 2, 7.15 + R.uniform(-0.1, 0.2), BAY_FAR + 1.0), (xb - xa, 0.06, 7.0),
              pitch=R.uniform(-6, 6), roll=(3 if j == 0 else -3))
    for x in BAYS:
        b.rod(IRON, (x, 6.7, BAY_FAR + 1.0), (x, 5.9, BAY_FAR + 1.0), 0.03)
        b.box(IRON, (x, 5.8, BAY_FAR + 1.0), (0.45, 0.16, 0.45))
        b.box(GLOW, (x, 5.7, BAY_FAR + 1.0), (0.34, 0.06, 0.34))
        # a half-stripped wreck on the floor of each bay, tools around it
        b.box(R.choice([RED, RUST, IRON]), (x + R.uniform(-0.3, 0.3), 0.45, BAY_FAR + 1.0 + R.uniform(-0.5, 0.5)), (1.6, 0.7, 3.6), yaw=R.uniform(-8, 8))
        b.drum((x - 2.2, 0, BAY_FAR + 3.0), yaw=R.uniform(0, 360))
        b.cyl(GLOW, (x + 0.9, 0.15, BAY_FAR - 0.5), 0.12, 0.05, segs=8)      # torch glow on the ground
    b.fire.append((BAYS[0], 0.6, BAY_FAR + 1.0)); b.fire.append((BAYS[-1], 0.6, BAY_FAR + 1.0))

    # ---- gantry crane over the siding, magnet holding a crushed car
    gx0, gx1 = -14.0, 14.0
    for xx in (gx0, gx1):
        for zz in (RAIL_Z - 4.5, RAIL_Z + 4.5):
            b.rod(IRON, (xx, -0.2, zz), (xx, 11.0, zz), 0.2, segs=8)
        b.beam(IRON, (xx, 11.0, RAIL_Z - 4.5), (xx, 11.0, RAIL_Z + 4.5), 0.3)
        b.beam(IRON, (xx, 3.5, RAIL_Z - 4.5), (xx, 7.5, RAIL_Z + 4.5), 0.1)
        b.beam(IRON, (xx, 7.5, RAIL_Z - 4.5), (xx, 3.5, RAIL_Z + 4.5), 0.1)
    for zz in (RAIL_Z - 4.5, RAIL_Z + 4.5):
        b.beam(RED, (gx0, 11.2, zz), (gx1, 11.2, zz), 0.45, 0.7)
    for k in range(9):
        xx = gx0 + k * (gx1 - gx0) / 8
        b.beam(IRON, (xx, 11.2, RAIL_Z - 4.5), (xx, 11.2, RAIL_Z + 4.5), 0.12)
    tx = -3.0
    b.box(IRON, (tx, 11.8, RAIL_Z), (2.2, 1.0, 10.0))
    b.box(RUST, (tx, 12.7, RAIL_Z), (1.6, 0.8, 1.6))
    b.rod(IRON, (tx, 11.3, RAIL_Z), (tx, 6.2, RAIL_Z), 0.04)
    b.cyl(IRON, (tx, 5.6, RAIL_Z), 1.2, 0.6, segs=14)
    b.box(RUST, (tx, 4.9, RAIL_Z + 0.2), (3.6, 0.6, 1.7), yaw=12, roll=6)   # the flattened car on the magnet
    b.rod(IRON, (gx1, 11.0, RAIL_Z + 4.5), (gx1, 12.6, RAIL_Z + 4.5), 0.05)
    b.flag(gx1, 11.0, RAIL_Z + 4.5, h=2.4, mat=RED)
    # a wrecked wagon beside the siding, off the track
    b.box(RUST, (-22.0, 1.4, RAIL_Z - 5.2), (7.0, 2.2, 2.4), yaw=4, roll=9)
    for k in range(4):
        b.torus(TIRE, (-24.5 + k * 1.7, 0.5, RAIL_Z - 4.1), 0.45, 0.16, axis='z')

    # ---- car crusher: a portal press with rams, a flattened car half out
    cx, cz = 18.0, -2.0
    for xx in (cx - 2.6, cx + 2.6):
        for zz in (cz - 2.2, cz + 2.2):
            b.box(IRON, (xx, 2.6, zz), (0.6, 5.2, 0.6))
    b.box(RED, (cx, 5.4, cz), (6.4, 0.8, 5.4))
    b.box(IRON, (cx, 4.5, cz), (5.0, 1.0, 4.4))
    for xx in (cx - 1.5, cx + 1.5):
        b.cyl(IRON, (xx, 3.2, cz), 0.32, 1.3, segs=10)
        b.cyl(STRIPES, (xx, 2.9, cz), 0.22, 0.35, segs=10)
    b.box(RUST, (cx, 0.75, cz), (5.2, 1.5, 4.6))
    b.box(IRON, (cx + 1.5, 0.3, cz + 3.5), (3.0, 0.5, 1.6), yaw=-8)   # what comes out
    b.box(IRON, (cx + 4.2, 1.5, cz - 1.0), (1.2, 3.0, 1.0)); b.box(RED, (cx + 4.2, 3.2, cz - 1.0), (1.0, 0.4, 0.8))
    b.rod(IRON, (cx + 3.4, 2.2, cz - 1.0), (cx + 2.6, 4.3, cz - 1.0), 0.06)
    b.fire.append((cx + 4.2, 1.6, cz - 1.0))
    # conveyor from the crusher to the scrap heap
    b.beam(IRON, (cx + 2.0, 1.0, cz + 4.0), (cx + 6.0, 4.0, cz + 11.0), 1.2, 0.3)
    for k in range(6):
        t = k / 5.0
        b.rod(IRON, (cx + 2.0 + 4.0 * t, 0.0, cz + 4.0 + 7.0 * t), (cx + 2.0 + 4.0 * t, 0.85 + 3.0 * t, cz + 4.0 + 7.0 * t), 0.05)
    b.blob(IRON, (cx + 7.0, 0, cz + 14.0), (3.4, 1.8, 3.0), jitter=0.3)
    b.blob(RUST, (cx + 4.0, 0, cz + 15.5), (2.4, 1.1, 2.2), jitter=0.3)

    # ---- crushed-car stacks and scrap rows, west side
    for col in range(3):
        for k in range(R.randint(3, 6)):
            b.box(R.choice([RED, RUST, IRON, CORR, IRON]), (-22.0 + col * 4.6 + R.uniform(-0.2, 0.2), 0.35 + k * 0.7, -6.0 + R.uniform(-0.2, 0.2)),
                  (3.8, 0.6, 1.7), yaw=R.uniform(-6, 6))
    for k in range(5):
        b.box(R.choice([RED, RUST, IRON]), (-24.0 + k * 3.2, 0.35, 2.5 + (k % 2) * 0.8), (2.8, 0.7, 1.6), yaw=90 + R.uniform(-8, 8))
    b.blob(IRON, (-25.0, 0, 9.0), (3.0, 1.4, 2.6), jitter=0.3)
    b.blob(RUST, (-19.5, 0, 10.0), (2.2, 1.0, 2.0), jitter=0.3)
    for k in range(8):
        b.tyre_stack(-27.0 + k * 2.1 + R.uniform(-0.3, 0.3), 16.0 + R.uniform(-1.0, 1.0), R.randint(1, 4))
    b.car_wreck((-14.0, 0, 18.0), 25, 0, RUST)
    b.car_wreck((-20.0, 0.3, 20.5), -55, 22, RED)

    # ---- blueprint office: a container on stilts with a drafting-table window and a sign
    ox, oz = 19.0, 16.0
    for px, pz in ((-2.7, -1.0), (2.7, -1.0), (-2.7, 1.0), (2.7, 1.0)):
        b.rod(IRON, (ox + px, -0.2, oz + pz), (ox + px, 3.0, oz + pz), 0.12)
    b.container((ox, 4.25, oz), 0, RED)
    b.box(IRON, (ox, 4.4, oz - 1.22), (3.0, 1.2, 0.05))                       # window
    b.box(GLOW, (ox, 4.4, oz - 1.24), (2.8, 1.0, 0.02))
    b.box(WOOD, (ox, 2.9, oz), (6.6, 0.15, 3.2))
    for k in range(7):
        b.beam(IRON, (ox - 3.5, 0.2 + k * 0.42, oz + 0.5), (ox - 3.5 + 1.2, 0.2 + k * 0.42, oz + 0.5), 0.05)
    b.rod(IRON, (ox - 3.5, 0, oz + 0.5), (ox - 3.5, 3.1, oz + 0.5), 0.05); b.rod(IRON, (ox - 2.3, 0, oz + 0.5), (ox - 2.3, 3.1, oz + 0.5), 0.05)
    b.box(RUST, (ox, 6.0, oz - 1.0), (5.2, 0.8, 0.1))
    b.text(GLOW, 'BLUEPRINTS', (ox, 5.75, oz - 1.08), 0.62, 0.06)
    b.rod(IRON, (ox + 2.8, 5.5, oz + 1.0), (ox + 2.8, 9.5, oz + 1.0), 0.05)
    b.cyl(IRON, (ox + 2.8, 9.5, oz + 1.0), 0.9, 0.35, segs=12, r2=0.1, pitch=-45)   # a dish, because somebody is listening
    b.lamp(ox - 4.5, 4.5, oz - 3.0, arm=0.8, yaw=0)
    b.drum((ox + 3.6, 0, oz + 2.2)); b.drum((ox + 4.2, 0, oz + 2.8), yaw=45)

    # ---- chimney / burn barrel corner, water tank, totem
    b.cyl(IRON, (26.0, 0, -22.0), 0.5, 9.0, segs=10)
    b.cyl(IRON, (26.0, 9.0, -22.0), 0.75, 0.5, segs=10, r2=0.15)
    for k in range(3):
        b.beam(IRON, (26.0, 2.5 + k * 2.5, -22.0), (24.0, 0.2 + k * 2.5, -20.0), 0.05)
    for px, pz in ((-1.1, -1.1), (1.1, -1.1), (-1.1, 1.1), (1.1, 1.1)):
        b.rod(IRON, (-26.0 + px, -0.2, -20.0 + pz), (-26.0 + px * 0.8, 6.5, -20.0 + pz * 0.8), 0.1)
    b.cyl(RUST, (-26.0, 6.5, -20.0), 1.5, 2.2, segs=14)
    b.cyl(IRON, (-26.0, 8.7, -20.0), 1.55, 0.5, segs=14, r2=0.2)
    b.rod(IRON, (8.0, -0.2, 20.0), (8.0, 6.5, 20.0), 0.12)
    b.skull((8.0, 6.8, 20.0), 0.6); b.skull((8.0, 4.6, 20.0), 0.45, yaw=90)
    for k in range(3):
        b.torus(TIRE, (8.0, 0.2 + k * 0.38, 20.0), 0.5, 0.2)
    b.spikes(8.0, 7.0, 20.0, 5, spread=0.4)
    b.lamp(-9.0, 5.2, 8.0, arm=0.9, yaw=0); b.lamp(9.0, 5.2, 8.0, arm=0.9, yaw=180)
    b.lamp(24.0, 5.5, 6.0, arm=1.0, yaw=90)
    for k in range(6):
        b.drum((-8.5 + k * 0.7 + R.uniform(-0.1, 0.1), 0, -22.5 + (k % 2) * 0.6), yaw=R.uniform(0, 360))
    b.fire.append((-8.0, 0.5, -22.2))
    # cables
    b.rod(IRON, (gx1, 11.0, RAIL_Z - 4.5), (26.0, 8.5, -22.0), 0.03, segs=4)
    b.rod(IRON, (gx0, 11.0, RAIL_Z + 4.5), (BAYS[0] - 3.0, 6.9, BAY_FAR - 2.0), 0.03, segs=4)
    b.rod(IRON, (BAYS[-1] + 3.0, 6.9, BAY_FAR + 4.0), (ox + 2.8, 9.0, oz + 1.0), 0.03, segs=4)


# ------------------------------------------------------------------ files --

def building_ini():
    lines = [
        '$NAME_STR "Scrap Center"',
        '',
        '; A wasteland breaker\'s yard, built as a vanilla SCRAPYARD so the game does the',
        '; hard part: "Send to scrapyard" on any vehicle, and it drives (or rides the',
        '; siding) here and gets taken apart into scrap metal. The scrap_center plugin',
        '; adds the reward: while a vehicle is being disassembled, its blueprint is',
        '; marked as owned, so a production line can build that type from then on.',
        ';',
        '; Storages and vehicle stations mirror the vanilla large scrapping facility.',
        '',
        '-------',
        '$COST_WORK SOVIET_CONSTRUCTION_GROUNDWORKS 0.0',
        '$COST_WORK_BUILDING_ALL',
        '$COST_RESOURCE_AUTO ground_asphalt 0.05',
        '------------------',
        '$COST_WORK SOVIET_CONSTRUCTION_STEEL_LAYING 1.0',
        '$COST_WORK_BUILDING_ALL',
        '$COST_RESOURCE_AUTO wall_steel 0.4',
        '-----------------------',
        '',
        '$TYPE_SCRAPYARD',
        '$SUBTYPE_AIRPLANE',
        '',
        '$WORKERS_NEEDED 30',
        '',
        '; vehicles delivered as cargo (brand-new ones straight off a production line)',
        '$STORAGE_IMPORT RESOURCE_TRANSPORT_VEHICLES 10',
        '',
        '; what comes off the yard floor',
        '$STORAGE_EXPORT_SCRAPYARD RESOURCE_TRANSPORT_OPEN 40',
        '$STORAGE_EXPORT_SCRAPYARD RESOURCE_TRANSPORT_COVERED 20',
        '$STORAGE_EXPORT_SPECIAL RESOURCE_TRANSPORT_GRAVEL 40 waste_steel',
        '$STORAGE_EXPORT_SPECIAL RESOURCE_TRANSPORT_GRAVEL 30 waste_aluminium',
        '$STORAGE_EXPORT RESOURCE_TRANSPORT_WASTE 50',
        '',
        '',
        '; road vehicles park in the bays under the cutting canopy',
    ]
    for x in BAYS:
        lines.append('$VEHICLE_STATION %.2f 0 %.2f  %.2f 0 %.2f' % (x, BAY_FAR, x, BAY_NEAR))
    lines += [
        '',
        '; the siding: trains enter one side and leave the other',
        '$CONNECTION_RAIL_ALLOWPASS',
        '%.1f 0.0 %.1f' % (-HX - 1.0, RAIL_Z),
        '%.1f 0.0 %.1f' % (-HX + 1.0, RAIL_Z),
        '$CONNECTION_RAIL_ALLOWPASS',
        '%.1f 0.0 %.1f' % (HX + 1.0, RAIL_Z),
        '%.1f 0.0 %.1f' % (HX - 1.0, RAIL_Z),
        '$CONNECTIONS_SPACE',
        '0.0 0.0',
        '%.1f %.1f' % (-HX - 1.0, HX + 1.0),
        '------------------',
        '$CONNECTIONS_ROAD_DEAD_SQUARE',
        '%.1f %.1f' % (-HX - 1.0, HZ + 1.0),
        '%.1f %.1f' % (HX + 1.0, -HZ - 1.0),
        '',
        '$CONNECTION_ROAD',
        '0.0 0.0 %.1f' % (HZ + 3.0),
        '0.0 0.0 %.1f' % (HZ + 2.0),
        '$CONNECTION_ADVANCED_POINT  0.0 0.0 %.1f' % (BAY_NEAR + 4.0),
        '$CONNECTION_PEDESTRIAN',
        '%.1f 0.0 %.1f' % (-GATE + 1.5, HZ + 2.0),
        '%.1f 0.0 %.1f' % (-GATE + 1.5, HZ + 3.0),
        '',
        '$PARTICLE factory_small_gray 26.0 9.6 -22.0 1 1',
        '$PARTICLE factory_small_gray %.1f 2.0 %.1f 1 1' % (BAYS[0], BAY_FAR + 1.0),
        '$PARTICLE factory_small_gray %.1f 2.0 %.1f 1 1' % (BAYS[-1], BAY_FAR + 1.0),
        '',
        '$TEXT_CAPTION',
        '-6.0 6.0 %.1f' % (HZ - 0.8),
        '6.0 6.0 %.1f' % (HZ - 0.8),
        '',
        'end', '']
    return '\r\n'.join(lines)


RENDERCONFIG = '''$TYPE_WORKSHOP
 MODEL model.nmf
 MATERIAL material.mtl
 MATERIALEMISSIVE material_e.mtl
 LIFE 3000.000000
 EXPLOSION_GROUP 0
 DERBIS_FALLING_FX buildingfall1 1.000000
 DERBIS_FALLED_FX buildingfall2 1.400000
 DERBIS_FALLED_SFX collapse
 DERBIS_NUM 10
 DERBIS_FALLING_FX_MAXTIME 3.000000
 DERBIS_SCALE 1.000000
 DERBIS_MESH buildings/buildingwreck1.nmf buildings/buildingwreck.mtl
 END
'''.replace('\n', '\r\n')

WORKSHOPCONFIG = '''$ITEM_ID 9000003

$ITEM_TYPE WORKSHOP_ITEMTYPE_BUILDING

$VISIBILITY 2
$OBJECT_BUILDING scrap_center

$ITEM_NAME "Scrap Center"

$ITEM_DESC "A wasteland breaker's yard. Send any vehicle here to take it apart - and learn how to build it."

$END
'''.replace('\n', '\r\n')


def main():
    mmkit.clear_scene()
    os.makedirs(OUTDIR, exist_ok=True)
    os.makedirs(PREVIEW, exist_ok=True)
    b = Builder(seed=1979)
    build(b)
    shapes, used = b.export_shapes()
    model = nmf.Model()
    model.materials = used
    model.shapes = shapes
    nmf.write(model, os.path.join(OUTDIR, 'model.nmf'))
    bbox = mmkit.model_bbox(shapes)
    mmkit.write_bbox_file(os.path.join(OUTDIR, 'building.bbox'), shapes)
    mmkit.write_fire_file(os.path.join(OUTDIR, 'building.fire'), b.fire)
    mmkit.write_text(os.path.join(OUTDIR, 'building.ini'), building_ini())
    mmkit.write_text(os.path.join(OUTDIR, 'renderconfig.ini'), RENDERCONFIG)
    mmkit.write_text(os.path.join(OUTDIR, 'material.mtl'), mmkit.mtl_text(used, ''))
    mmkit.write_text(os.path.join(OUTDIR, 'material_e.mtl'), mmkit.mtl_text(used, '', emissive=True))
    mmkit.write_text(os.path.join(os.path.dirname(OUTDIR), 'workshopconfig.ini'), WORKSHOPCONFIG)
    for name in used + ['tp_black']:
        shutil.copy(os.path.join(TEXDIR, name + '.dds'), os.path.join(OUTDIR, name + '.dds'))

    bmats = mmkit.blender_materials(TEXDIR)
    obs = b.preview_objects(bmats, 'scrap')
    mmkit.lighting()
    mmkit.render(os.path.join(PREVIEW, 'scrapcenter_preview.png'), (-48.0, 30.0, 62.0), (0.0, 3.0, -2.0), (1600, 1000))
    mmkit.render(os.path.join(PREVIEW, 'scrapcenter_gate.png'), (16.0, 6.0, 44.0), (0.0, 5.0, 10.0), (1600, 1000), fov=50)
    mmkit.render(os.path.join(PREVIEW, 'scrapcenter_yard.png'), (30.0, 14.0, -40.0), (-2.0, 3.0, -8.0), (1600, 1000), fov=48)
    mmkit.render(os.path.join(PREVIEW, 'scrapcenter_icon.png'), (-40.0, 38.0, 54.0), (-1.0, 2.0, 0.0), (384, 384), fov=46, transparent=True, samples=32)
    mmkit.save_scaled_png(os.path.join(PREVIEW, 'scrapcenter_icon.png'), os.path.join(OUTDIR, 'imagegui.png'), 96, 96)
    mmkit.lighting(night=True)
    mmkit.render(os.path.join(PREVIEW, 'scrapcenter_night.png'), (20.0, 8.0, 46.0), (0.0, 5.0, 8.0), (1600, 1000), fov=48)
    print('scrap center: %d nodes, %d tris, bbox %s, %d fire points' % (
        len(shapes), sum(s.nt for s in shapes), ['%.1f' % v for v in bbox], len(b.fire)))
    print('done')


main()
