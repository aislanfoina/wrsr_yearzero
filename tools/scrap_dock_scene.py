"""The Ship Breakers: the Scrap Center's dock variant for ships.

    blender -b --python tools/scrap_dock_scene.py -- <texdir> <outdir> <previewdir>

$TYPE_SCRAPYARD + $SUBTYPE_SHIP, in the vanilla ship-scrapping facility's
frame: land at -X, quay edge at x ~ 27, three 233 m berths along +X at
z = 0 and +-60, trucks loop on the quay along Z around x = 0, the road comes
in from -X. Everything the game needs (berths, harbor depth keys, stations)
is copied from scrapyard_ship.ini; only the look is ours. The scrap_center
plugin grants blueprints here too - it hooks every scrapyard.
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
OUTDIR = argv[1] if len(argv) > 1 else 'mod/buildings/scrap_dock/scrap_dock'
PREVIEW = argv[2] if len(argv) > 2 else 'build'

QUAY_X = 27.0          # land ends here; berths start at 27.82
LAND_X = -8.0
HZ = 92.0              # quay length, covers the outer berths' start
TRUCK_X = -0.39        # vanilla truck bays run along Z here; keep x -7..4 clear


def hulk(b, cx, cz, length, beam, height, yaw, tilt, cut_from, mat=RUST):
    """A ship hull hauled up the beach, stern end cut open to the ribs."""
    R = b.R
    M = rot(0, yaw, tilt)

    def P(x, y, z):
        v = M @ Vector((x, -z, y))
        return (cx + v.x, y * 0 + v.z, cz - v.y)

    # keel/bottom, sides as tapered slabs, deck; the last `cut_from` metres
    # of length are ribs only
    solid = length * (1.0 - cut_from)
    x0 = -length / 2
    b.box(mat, P(x0 + solid / 2, height * 0.5, 0), (solid, height, beam), yaw=yaw, roll=tilt)
    # bow taper
    b.box(mat, P(x0 - 3.0, height * 0.55, 0), (7.0, height * 0.95, beam * 0.55), yaw=yaw + 12, roll=tilt)
    b.box(mat, P(x0 - 3.0, height * 0.55, 0), (7.0, height * 0.95, beam * 0.55), yaw=yaw - 12, roll=tilt)
    # superstructure and funnel near the bow
    b.box(CORR, P(x0 + solid * 0.25, height + 1.6, 0), (7.0, 3.2, beam * 0.7), yaw=yaw, roll=tilt)
    b.box(IRON, P(x0 + solid * 0.25, height + 3.9, 0), (6.5, 1.4, beam * 0.5), yaw=yaw, roll=tilt)
    b.cyl(IRON, P(x0 + solid * 0.36, height + 3.2, 0), 0.9, 3.5, segs=10, yaw=yaw)
    b.rod(IRON, P(x0 + solid * 0.12, height + 3.2, 0), P(x0 + solid * 0.12, height + 9.0, 0), 0.08)
    # ribs where the stern was cut away
    nrib = max(3, int(length * cut_from / 2.4))
    for i in range(nrib):
        x = x0 + solid + 1.2 + i * 2.4
        for s in (-1, 1):
            b.beam(IRON, P(x, 0.4, s * beam * 0.5), P(x, height * 0.95, s * beam * 0.46), 0.18)
        b.beam(IRON, P(x, 0.3, -beam * 0.5), P(x, 0.3, beam * 0.5), 0.2)
    b.beam(IRON, P(x0 + solid, height * 0.9, -beam * 0.48), P(x0 + length, height * 0.6, -beam * 0.44), 0.16)
    b.beam(IRON, P(x0 + solid, height * 0.9, beam * 0.48), P(x0 + length, height * 0.6, beam * 0.44), 0.16)
    # torn plates hanging off, torch glow on the cut edge
    for k in range(4):
        b.box(RUST, P(x0 + solid + R.uniform(-1, 3), height * R.uniform(0.3, 0.8), R.choice((-1, 1)) * beam * 0.52), (2.2, 1.6, 0.06),
              yaw=yaw + R.uniform(-25, 25), pitch=R.uniform(-30, 30))
    for k in range(3):
        b.box(GLOW, P(x0 + solid + 0.05, height * (0.25 + 0.3 * k), 0), (0.08, 0.12, beam * 0.92), yaw=yaw, roll=tilt)
    b.fire.append(P(x0 + solid, height * 0.5, 0))
    # plates and scrap on the ground beside it
    for k in range(6):
        b.box(mat, P(x0 + solid + R.uniform(-4, 6), 0.05 + 0.08 * k, R.choice((-1, 1)) * (beam * 0.5 + R.uniform(1.5, 4))), (3.0, 0.08, 2.0),
              yaw=yaw + R.uniform(-40, 40))


def build(b):
    R = b.R
    # quay platform, seawall face, and a beach slope under the hulks
    b.box(GROUND, ((LAND_X + QUAY_X) / 2, -0.25, 0), (QUAY_X - LAND_X, 0.5, HZ * 2))
    b.box(CONCRETE, (QUAY_X - 0.6, -2.5, 0), (1.2, 5.6, HZ * 2))
    for z in range(-88, 89, 8):
        b.cyl(IRON, (QUAY_X + 0.3, -2.0, z), 0.32, 2.4, segs=8)                 # bollard posts
        b.torus(TIRE, (QUAY_X + 0.55, -0.9 - (z % 16 == 0) * 0.6, z + 3.0), 0.55, 0.2, axis='x')   # tyre fenders
    b.box(GRAVEL, (QUAY_X - 14, 0.02, 66), (26, 0.06, 40))
    b.box(GRAVEL, (QUAY_X - 14, 0.02, -66), (26, 0.06, 40))

    # ---- the hulks on the beach (outside the berth lanes, which start at x 27.8)
    hulk(b, 11.0, 66.0, 34.0, 9.0, 6.5, yaw=6, tilt=7, cut_from=0.45)
    hulk(b, 12.0, -64.0, 24.0, 7.0, 5.0, yaw=-8, tilt=-5, cut_from=0.7, mat=IRON)
    # winch house and cables that dragged them up
    b.box(IRON, (-4.0, 1.2, 66.0), (3.0, 2.4, 3.0)); b.cyl(IRON, (-4.0, 2.4, 66.0), 0.9, 1.2, segs=10, pitch=90)
    b.rod(IRON, (-2.5, 1.6, 66.0), (-6.0, 3.0, 66.0), 0.04, segs=4)
    b.box(IRON, (-4.0, 1.2, -64.0), (3.0, 2.4, 3.0)); b.cyl(IRON, (-4.0, 2.4, -64.0), 0.9, 1.2, segs=10, pitch=90)

    # ---- jetties with derricks between the berths (the fingers of the basin)
    for zj in (-30.0, 30.0):
        for x in range(30, 121, 10):
            for s in (-1, 1):
                b.rod(IRON, (x, -6.0, zj + s * 2.2), (x, 1.2, zj + s * 2.2), 0.28, segs=8)
            b.beam(IRON, (x, 0.9, zj - 2.6), (x, 0.9, zj + 2.6), 0.25)
        b.box(WOOD, (75.0, 1.35, zj), (94.0, 0.2, 6.0))
        b.beam(IRON, (28.0, 1.5, zj - 3.0), (122.0, 1.5, zj - 3.0), 0.08); b.beam(IRON, (28.0, 1.5, zj + 3.0), (122.0, 1.5, zj + 3.0), 0.08)
        for k in range(3):
            xd = 50.0 + k * 30.0
            b.rod(IRON, (xd, 1.4, zj), (xd, 12.0, zj), 0.16, segs=8)
            b.beam(IRON, (xd, 11.6, zj), (xd + 6.0, 6.0, zj + (2.6 if k % 2 else -2.6)), 0.14)
            b.rod(IRON, (xd, 12.0, zj), (xd + 6.0, 6.0, zj + (2.6 if k % 2 else -2.6)), 0.03, segs=4)
            b.rod(IRON, (xd + 6.0, 6.0, zj + (2.6 if k % 2 else -2.6)), (xd + 6.0, 3.0, zj + (2.6 if k % 2 else -2.6)), 0.03, segs=4)
            b.box(RUST, (xd + 6.0, 2.6, zj + (2.6 if k % 2 else -2.6)), (1.4, 0.8, 1.2), yaw=R.uniform(-30, 30))
            b.lamp(xd - 4.0, 5.0, zj + 2.4)
        b.box(RUST, (121.5, 2.6, zj), (0.16, 2.2, 5.6), roll=2)
        b.spikes(121.5, 3.8, zj, 5, spread=2.4)
        b.flag(121.5, 3.6, zj - 2.6, mat=RED)
        b.drum((40.0, 1.45, zj - 1.8)); b.drum((41.0, 1.45, zj - 2.2), yaw=40)
        b.tyre_stack(60.0, zj + 1.9, 2); b.tyre_stack(95.0, zj - 1.9, 3)

    # ---- the cutting hall on the quay: open gantry shed over a scrap floor
    hx0, hx1, hz0, hz1 = 6.0, 24.0, -22.0, 22.0
    for zz in (hz0, (hz0 + hz1) / 2, hz1):
        for xx in (hx0, hx1):
            b.rod(IRON, (xx, -0.2, zz), (xx, 9.0, zz), 0.22, segs=8)
        b.beam(RED, (hx0, 9.2, zz), (hx1, 9.2, zz), 0.5, 0.8)
    for xx in (hx0, hx1):
        b.beam(IRON, (xx, 9.0, hz0), (xx, 9.0, hz1), 0.24)
        b.beam(IRON, (xx, 3.0, hz0), (xx, 7.5, (hz0 + hz1) / 2), 0.1); b.beam(IRON, (xx, 7.5, (hz0 + hz1) / 2), (xx, 3.0, hz1), 0.1)
    for k in range(5):
        zs = hz0 + k * (hz1 - hz0) / 4
        b.box(R.choice([CORR, RUST, TARP]), ((hx0 + hx1) / 2, 9.7 + R.uniform(-0.1, 0.2), zs + (hz1 - hz0) / 8), (hx1 - hx0 + 1.0, 0.06, (hz1 - hz0) / 4 - 0.4),
              pitch=R.uniform(-5, 5), roll=R.uniform(-3, 3))
    # travelling hoist with a hull plate in the magnet
    b.box(IRON, ((hx0 + hx1) / 2 + 2.0, 8.6, 4.0), (1.6, 0.8, 4.0))
    b.rod(IRON, ((hx0 + hx1) / 2 + 2.0, 8.2, 4.0), ((hx0 + hx1) / 2 + 2.0, 4.6, 4.0), 0.04)
    b.cyl(IRON, ((hx0 + hx1) / 2 + 2.0, 4.0, 4.0), 1.0, 0.6, segs=12)
    b.box(RUST, ((hx0 + hx1) / 2 + 2.0, 3.4, 4.0), (4.0, 0.1, 2.6), yaw=20, roll=8)
    # scrap floor: plates, ribs, a stripped superstructure, drums, torches
    for k in range(14):
        b.box(R.choice([RUST, IRON, CORR]), (R.uniform(hx0 + 1, hx1 - 1), 0.05 + 0.07 * (k % 4), R.uniform(hz0 + 1, hz1 - 1)), (R.uniform(1.5, 3.5), 0.08, R.uniform(1.0, 2.5)),
              yaw=R.uniform(0, 180))
    b.blob(IRON, (hx1 - 3.0, 0, hz1 - 4.0), (3.0, 1.5, 2.6), jitter=0.3)
    b.blob(RUST, (hx0 + 3.0, 0, hz0 + 4.0), (2.4, 1.2, 2.2), jitter=0.3)
    b.box(CORR, (hx1 - 4.0, 1.4, -10.0), (5.0, 2.8, 4.0), yaw=15); b.box(IRON, (hx1 - 4.0, 3.2, -10.0), (4.0, 0.9, 3.0), yaw=15)
    for k in range(4):
        b.drum((hx0 + 1.5 + k * 0.7, 0, hz1 - 1.5), yaw=R.uniform(0, 360))
    for x, z in ((hx0 + 4, -3), (hx1 - 6, 8), (hx0 + 9, -14)):
        b.cyl(GLOW, (x, 0.15, z), 0.14, 0.05, segs=8)
        b.lamp(x, 8.4, z)
    b.fire.append((hx0 + 4, 0.6, -3)); b.fire.append((hx1 - 6, 0.6, 8))

    # ---- blueprint office on the seawall, sign facing the water
    ox, oz = 18.0, -32.0
    for px, pz in ((-2.7, -1.0), (2.7, -1.0), (-2.7, 1.0), (2.7, 1.0)):
        b.rod(IRON, (ox + px, -0.2, oz + pz), (ox + px, 3.0, oz + pz), 0.12)
    b.container((ox, 4.25, oz), 0, RED)
    b.box(IRON, (ox + 3.02, 4.4, oz), (0.05, 1.2, 2.0)); b.box(GLOW, (ox + 3.04, 4.4, oz), (0.02, 1.0, 1.8))
    b.box(WOOD, (ox, 2.9, oz), (6.6, 0.15, 3.2))
    b.box(RUST, (ox + 3.1, 6.0, oz), (0.1, 0.8, 5.2))
    b.text(GLOW, 'BLUEPRINTS', (ox + 3.18, 5.75, oz), 0.62, 0.06, yaw=90)
    b.rod(IRON, (ox - 2.8, 5.5, oz + 1.0), (ox - 2.8, 9.5, oz + 1.0), 0.05)
    b.cyl(IRON, (ox - 2.8, 9.5, oz + 1.0), 0.9, 0.35, segs=12, r2=0.1, pitch=-45)
    for k in range(7):
        b.beam(IRON, (ox - 3.5, 0.2 + k * 0.42, oz - 0.5), (ox - 2.3, 0.2 + k * 0.42, oz - 0.5), 0.05)
    b.rod(IRON, (ox - 3.5, 0, oz - 0.5), (ox - 3.5, 3.1, oz - 0.5), 0.05); b.rod(IRON, (ox - 2.3, 0, oz - 0.5), (ox - 2.3, 3.1, oz - 0.5), 0.05)

    # ---- the big sign on the seawall for ships coming in, and a skull totem
    for zz in (34.0, 46.0):
        b.rod(IRON, (QUAY_X - 3.0, -0.2, zz), (QUAY_X - 3.0, 12.0, zz), 0.16, segs=8)
    b.beam(IRON, (QUAY_X - 3.0, 12.0, 34.0), (QUAY_X - 3.0, 12.0, 46.0), 0.2)
    b.box(RUST, (QUAY_X - 3.0, 9.0, 40.0), (0.16, 2.6, 13.0), pitch=2)
    b.box(STRIPES, (QUAY_X - 3.0, 7.6, 40.0), (0.2, 0.2, 13.0), pitch=2)
    b.text(GLOW, 'SHIP BREAKERS', (QUAY_X - 2.88, 8.3, 40.0), 1.4, 0.1, yaw=90)
    b.skull((QUAY_X - 3.0, 12.4, 40.0), 1.1)
    b.spikes(QUAY_X - 3.0, 12.2, 40.0, 8, spread=5.0)
    b.rod(IRON, (QUAY_X - 4.0, -0.2, -44.0), (QUAY_X - 4.0, 7.0, -44.0), 0.12)
    b.skull((QUAY_X - 4.0, 7.3, -44.0), 0.7); b.skull((QUAY_X - 4.0, 5.0, -44.0), 0.5, yaw=90)
    for k in range(3):
        b.torus(TIRE, (QUAY_X - 4.0, 0.2 + k * 0.38, -44.0), 0.5, 0.2)
    b.flag(QUAY_X - 4.0, 7.2, -44.0, h=3.0, mat=RED)

    # ---- landward fence with a gate for the road at x -4, z 0
    b.wall_run(LAND_X, 4.0, LAND_X, HZ - 1.0, base_h=4.0)
    b.wall_run(LAND_X, -HZ + 1.0, LAND_X, -4.0, base_h=4.0)
    for tz in (-5.5, 5.5):
        for k in range(3):
            b.box(R.choice([RED, RUST, CORR]), (LAND_X + R.uniform(-0.1, 0.1), 1.2 + k * 2.4, tz), (3.0, 2.4, 3.0), yaw=R.uniform(-4, 4))
        b.spikes(LAND_X, 7.4, tz, 5, spread=1.2)
    b.beam(IRON, (LAND_X, 8.0, -7.0), (LAND_X, 8.0, 7.0), 0.24)
    b.box(RUST, (LAND_X, 6.9, 0), (0.16, 1.6, 8.0), pitch=2)
    b.text(GLOW, 'SCRAP', (LAND_X - 0.1, 6.4, 0), 1.1, 0.08, yaw=-90)
    b.lamp(LAND_X + 1.5, 5.0, -9.0, arm=0.9, yaw=90); b.lamp(LAND_X + 1.5, 5.0, 9.0, arm=0.9, yaw=90)
    b.wall_run(LAND_X, HZ - 1.0, QUAY_X - 20.0, HZ - 1.0, base_h=3.6)
    b.wall_run(QUAY_X - 20.0, -HZ + 1.0, LAND_X, -HZ + 1.0, base_h=3.6)

    # ---- more yard dressing on the quay strip north and south of the hall
    for k in range(7):
        b.tyre_stack(6.0 + k * 2.6 + R.uniform(-0.3, 0.3), 30.0 + R.uniform(-1.5, 1.5), R.randint(1, 4))
    b.car_wreck((14.0, 0, -28.0), 70, 0, RUST)
    b.blob(IRON, (8.0, 0, 40.0), (3.0, 1.4, 2.6), jitter=0.3); b.blob(RUST, (20.0, 0, -50.0), (2.6, 1.1, 2.4), jitter=0.3)
    b.cyl(RUST, (20.0, 0, 52.0), 1.4, 4.5, segs=12); b.cyl(IRON, (20.0, 4.5, 52.0), 1.45, 0.5, segs=12, r2=0.2)
    b.cyl(IRON, (23.0, 0, -80.0), 0.5, 9.0, segs=10); b.cyl(IRON, (23.0, 9.0, -80.0), 0.75, 0.5, segs=10, r2=0.15)
    for k in range(6):
        b.drum((6.0 + k * 0.7 + R.uniform(-0.1, 0.1), 0, -30.0 + (k % 2) * 0.6), yaw=R.uniform(0, 360))
    b.fire.append((6.5, 0.5, -29.7))
    # cables
    b.rod(IRON, (hx1, 9.0, hz0), (QUAY_X - 3.0, 11.5, 34.0), 0.03, segs=4)
    b.rod(IRON, (hx1, 9.0, hz1), (ox - 2.8, 9.0, oz + 1.0), 0.03, segs=4)


def building_ini():
    lines = [
        '$NAME_STR "Ship Breakers"',
        '',
        '; The Scrap Center\'s dock: a vanilla ship-scrapping facility with a wasteland',
        '; yard on it. Send a ship here with "Send to scrapyard"; the scrap_center plugin',
        '; marks its blueprint as owned while it is being cut up. Berths, harbor keys',
        '; and truck bays are the vanilla ship scrapyard\'s.',
        '',
        '-------',
        '$COST_WORK SOVIET_CONSTRUCTION_GROUNDWORKS 0.0',
        '$COST_WORK_BUILDING_ALL',
        '$COST_RESOURCE_AUTO ground_asphalt 0.05',
        '------------------',
        '$COST_WORK SOVIET_CONSTRUCTION_SKELETON_CASTING 1.0',
        '$COST_WORK_BUILDING_ALL',
        '$COST_RESOURCE_AUTO wall_concrete 0.3',
        '$COST_RESOURCE_AUTO wall_steel 0.4',
        '-----------------------',
        '',
        '$TYPE_SCRAPYARD',
        '$SUBTYPE_SHIP',
        '$AMBIENT_SFX amb_separation_recycling',
        '',
        '$WORKERS_NEEDED 60',
        '',
        '$STORAGE_EXPORT_SPECIAL RESOURCE_TRANSPORT_OPEN 80 steel',
        '$STORAGE_EXPORT_SCRAPYARD RESOURCE_TRANSPORT_COVERED 40',
        '$STORAGE_EXPORT_SPECIAL RESOURCE_TRANSPORT_GRAVEL 80 waste_steel',
        '$STORAGE_EXPORT RESOURCE_TRANSPORT_WASTE 100',
        '',
        '',
        '$SHIP_STATION 27.8238 0 0.0 260.7546 0 0.0',
        '$SHIP_STATION 27.8238 0 60.0 260.7546 0 60.0',
        '$SHIP_STATION 27.8238 0 -60.0 260.7546 0 -60.0',
        '',
        '$VEHICLE_STATION -0.3866 0 1.9821    -0.3866 0 21.4433',
        '$VEHICLE_STATION -0.3866 0 -1.9821    -0.3866 0 -21.4433',
        '',
        '$HARBOR_OVER_WATER_FROM -22',
        '$HARBOR_OVER_TERRAIN_FROM -10',
        '',
        '$CONNECTION_ROAD',
        '-4.1118 0 0.1030',
        '-3.1118 0 0.1030',
        '$CONNECTION_ROAD_DEAD',
        '-4.1118 0 0.1030',
        '$CONNECTION_ROAD_DEAD',
        '5.1118 0 0.1030',
        '',
        '$CONNECTIONS_ROAD_DEAD_SQUARE',
        '2.7230 -27.5160',
        '-3.2814 27.9257',
        '',
        '$PARTICLE factory_small_gray 23.0 9.6 -80.0 1 1',
        '$PARTICLE factory_small_gray 10.0 4.0 -3.0 1 1',
        '$PARTICLE factory_small_gray 11.0 5.0 66.0 1 1',
        '',
        '$TEXT_CAPTION',
        '24.0 8.3 46.0',
        '24.0 8.3 34.0',
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

WORKSHOPCONFIG = '''$ITEM_ID 9000004

$ITEM_TYPE WORKSHOP_ITEMTYPE_BUILDING

$VISIBILITY 2
$OBJECT_BUILDING scrap_dock

$ITEM_NAME "Ship Breakers"

$ITEM_DESC "The Scrap Center's dock. Send any ship here to cut it up on the beach - and learn how to build it."

$END
'''.replace('\n', '\r\n')


def main():
    mmkit.clear_scene()
    os.makedirs(OUTDIR, exist_ok=True)
    os.makedirs(PREVIEW, exist_ok=True)
    b = Builder(seed=1981)
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
    b.preview_objects(bmats, 'dock')
    # a water plane for the renders only
    me = bpy.data.meshes.new('water')
    me.from_pydata([(-20, -400, -0.4), (400, -400, -0.4), (400, 400, -0.4), (-20, 400, -0.4)], [], [(0, 1, 2, 3)])
    wm = bpy.data.materials.new('water'); wm.use_nodes = True
    bsdf = wm.node_tree.nodes['Principled BSDF']
    bsdf.inputs['Base Color'].default_value = (0.10, 0.16, 0.16, 1.0); bsdf.inputs['Roughness'].default_value = 0.15
    me.materials.append(wm)
    wob = bpy.data.objects.new('water', me); bpy.context.scene.collection.objects.link(wob)
    mmkit.lighting()
    mmkit.render(os.path.join(PREVIEW, 'scrapdock_preview.png'), (110.0, 48.0, 120.0), (20.0, 2.0, 5.0), (1600, 1000), fov=44)
    mmkit.render(os.path.join(PREVIEW, 'scrapdock_beach.png'), (48.0, 12.0, 96.0), (10.0, 3.0, 60.0), (1600, 1000), fov=48)
    mmkit.render(os.path.join(PREVIEW, 'scrapdock_quay.png'), (-30.0, 16.0, 40.0), (14.0, 3.0, 0.0), (1600, 1000), fov=50)
    mmkit.render(os.path.join(PREVIEW, 'scrapdock_icon.png'), (90.0, 60.0, 110.0), (14.0, 2.0, 0.0), (384, 384), fov=40, transparent=True, samples=32)
    mmkit.save_scaled_png(os.path.join(PREVIEW, 'scrapdock_icon.png'), os.path.join(OUTDIR, 'imagegui.png'), 96, 96)
    mmkit.lighting(night=True)
    mmkit.render(os.path.join(PREVIEW, 'scrapdock_night.png'), (95.0, 20.0, 70.0), (16.0, 4.0, 10.0), (1600, 1000), fov=46)
    print('ship breakers: %d nodes, %d tris, bbox %s, %d fire points' % (
        len(shapes), sum(s.nt for s in shapes), ['%.1f' % v for v in bbox], len(b.fire)))
    print('done')


main()
