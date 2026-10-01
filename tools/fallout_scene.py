"""The contamination kit: Decontamination Task Force, Radiology Board, Recovery Center.

    blender -b --python tools/fallout_scene.py -- <texdir> <kitdir> <previewdir>

Three vanilla types under wasteland skins, driven by the fallout plugin's dose
instead of crime:

    DTF Station       $TYPE_POLICE_STATION - Geiger patrols sweep and screen cases
    Radiology Board   $TYPE_COURT_HOUSE   - physicians assess the dose, set quarantine
    Recovery Center   $TYPE_PRISON        - quarantine beds, medics, convalescent crews
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
KITDIR = argv[1] if len(argv) > 1 else 'mod/buildings/fallout_kit'
PREVIEW = argv[2] if len(argv) > 2 else 'build/fallout'
ITEM_ID = 9000009


def trefoil(b, center, r=1.0, yaw=0.0, mat=GLOW, back=RED):
    """The radiation sign: a disc with three blades, stood upright facing +z."""
    x, y, z = center
    b.cyl(back, (x, y, z), r * 1.05, 0.08, segs=18, pitch=90, yaw=yaw)
    b.cyl(mat, (x, y, z + 0.06), r * 0.22, 0.06, segs=12, pitch=90, yaw=yaw)
    for k in range(3):
        a = math.radians(90 + k * 120 + yaw)
        bx, by = x + r * 0.55 * math.cos(a), y + r * 0.55 * math.sin(a)
        b.box(mat, (bx, by, z + 0.06), (r * 0.42, r * 0.62, 0.06), yaw=-(90 + k * 120))


def hazard_post(b, x, z, h=2.2):
    b.rod(IRON, (x, -0.2, z), (x, h, z), 0.05)
    b.box(STRIPES, (x, h - 0.35, z), (0.7, 0.7, 0.06))


def tent(b, center, size, yaw=0.0, mat=TARP):
    x, y, z = center
    w, h, d = size
    for s in (-1, 1):
        b.box(mat, (x + s * w * 0.27, y + h * 0.5, z), (w * 0.62, 0.05, d), yaw=yaw, roll=s * 62)
    b.rod(IRON, (x, y, z - d / 2), (x, y + h, z - d / 2), 0.04)
    b.rod(IRON, (x, y, z + d / 2), (x, y + h, z + d / 2), 0.04)
    b.beam(IRON, (x, y + h, z - d / 2), (x, y + h, z + d / 2), 0.04)


def dtf_station(b):
    R = b.R
    b.box(GROUND, (0, -0.25, 0), (30, 0.5, 26))
    b.wall_run(-14, -12, 14, -12, base_h=3.0); b.wall_run(-14, 12, -14, -12, base_h=3.0)
    b.wall_run(14, -12, 14, 6, base_h=3.0); b.wall_run(-14, 12, -6, 12, base_h=3.0)
    # the garage: four open bays under a corrugated roof, the patrol stations are in front (+z side)
    for k in range(4):
        cx = -10.5 + k * 5.0
        b.rod(IRON, (cx - 2.0, -0.2, -10.0), (cx - 2.0, 4.2, -10.0), 0.14); b.rod(IRON, (cx - 2.0, -0.2, -2.0), (cx - 2.0, 4.0, -2.0), 0.14)
        b.box(CORR, (cx, 2.2, -6.5), (0.08, 4.4, 7.5))
        b.box(STRIPES, (cx, 4.35, -2.0), (4.6, 0.5, 0.08))
    b.rod(IRON, (9.5, -0.2, -10.0), (9.5, 4.2, -10.0), 0.14); b.rod(IRON, (9.5, -0.2, -2.0), (9.5, 4.0, -2.0), 0.14)
    b.box(CORR, (-0.5, 4.5, -6.2), (21.0, 0.08, 8.8), pitch=-3)
    b.box(RUST, (-0.5, 4.9, -10.3), (21.0, 0.9, 0.12)); b.text(GLOW, 'D T F', (-0.5, 4.6, -10.22), 0.7, 0.06)
    # the office: two stacked containers with a stair, a dish and the Geiger mast
    b.container((9.0, 1.25, 6.0), 0, RUST, size=(6.0, 2.5, 2.4)); b.container((9.0, 3.75, 6.0), 4, CORR, size=(6.0, 2.5, 2.4))
    b.box(IRON, (5.4, 2.6, 6.0), (1.0, 0.08, 2.6)); b.rod(IRON, (5.0, -0.2, 7.2), (5.0, 2.6, 7.2), 0.05); b.rod(IRON, (5.0, -0.2, 4.8), (5.0, 2.6, 4.8), 0.05)
    for k in range(6):
        b.box(WOOD, (6.0 + k * 0.35, 0.3 + k * 0.42, 6.0), (0.35, 0.06, 2.4))
    b.rod(IRON, (11.0, 5.0, 4.8), (11.0, 12.0, 4.8), 0.07)
    b.cyl(IRON, (11.0, 11.0, 4.8), 1.1, 0.25, segs=14, r2=0.1, pitch=-35, yaw=30)
    b.rod(IRON, (11.0, 12.0, 4.8), (11.0, 13.2, 4.8), 0.03); b.box(GLOW, (11.0, 13.3, 4.8), (0.25, 0.25, 0.25))
    for k in range(4):
        b.beam(IRON, (11.0, 5.0 + k * 1.8, 4.8), (11.0 + 0.6 * (1 if k % 2 else -1), 5.0 + k * 1.8 + 0.3, 4.8 + 0.6), 0.03)
    # decontamination line: a pipe frame with shower heads and drums, a trough, a tyre barricade around it
    for xx in (-10.0, -6.5, -3.0):
        b.rod(IRON, (xx, -0.2, 8.0), (xx, 3.0, 8.0), 0.06); b.rod(IRON, (xx, -0.2, 3.5), (xx, 3.0, 3.5), 0.06)
        b.beam(IRON, (xx, 3.0, 8.0), (xx, 3.0, 3.5), 0.05)
    b.beam(IRON, (-10.0, 3.0, 8.0), (-3.0, 3.0, 8.0), 0.05); b.beam(IRON, (-10.0, 3.0, 3.5), (-3.0, 3.0, 3.5), 0.05)
    for k in range(6):
        b.cyl(IRON, (-9.5 + k * 1.3, 2.9, 5.75), 0.12, 0.3, segs=8, pitch=90)
    b.box(CONCRETE, (-6.5, 0.15, 5.75), (8.0, 0.3, 5.0)); b.box(IRON, (-6.5, 0.5, 5.75), (7.2, 0.4, 3.8)); b.box(TARP, (-6.5, 0.72, 5.75), (6.8, 0.05, 3.4))
    for k in range(5):
        b.drum((-12.3, 0, 2.0 + k * 0.75), yaw=R.uniform(0, 360))
    b.cyl(RUST, (0.5, 0, 9.5), 1.0, 2.6, segs=12); b.cyl(IRON, (0.5, 2.6, 9.5), 1.05, 0.3, segs=12, r2=0.2)
    trefoil(b, (0.5, 1.4, 10.55), r=0.7)
    for xx, zz in ((-13.0, 11.0), (13.0, -11.0), (13.0, 8.5)):
        hazard_post(b, xx, zz)
    # gate sign on +z with stripes, lamps, a flag and a burnt patrol wreck
    for tx in (-4.0, 4.0):
        b.box(CORR, (tx, 2.0, 12), (1.6, 4.0, 1.6)); b.spikes(tx, 4.0, 12, 3, spread=0.5)
    b.beam(IRON, (-4.0, 4.7, 12), (4.0, 4.7, 12), 0.16)
    b.box(STRIPES, (0, 4.15, 12), (6.5, 1.0, 0.12)); b.text(GLOW, 'SWEEP', (0, 3.85, 12.08), 0.7, 0.06)
    trefoil(b, (0, 5.4, 12.0), r=0.55)
    b.lamp(-5.5, 4.4, 10.8, arm=0.8, yaw=0); b.lamp(5.5, 4.4, 10.8, arm=0.8, yaw=180); b.lamp(-13.5, 3.8, -9.5, arm=0.8, yaw=0)
    b.flag(13.3, 3.0, -11.3, mat=RED)
    b.car_wreck((-11.5, 0, -1.0), 25, 4, RUST)
    b.tyre_stack(12.5, 10.5, 3); b.blob(IRON, (-12.5, 0, 10.0), (1.5, 0.7, 1.3), jitter=0.3)
    return 'Decontamination Task Force'


def radiology_board(b):
    R = b.R
    b.box(GROUND, (0, -0.25, 0), (26, 0.5, 24))
    b.wall_run(-12, -11, 12, -11, base_h=3.0); b.wall_run(12, -11, 12, 11, base_h=3.0)
    b.wall_run(-12, 11, -12, -11, base_h=3.0); b.wall_run(12, 11, 4, 11, base_h=3.0); b.wall_run(-4, 11, -12, 11, base_h=3.0)
    # the lab: a half-buried concrete bunker with a sandbag skirt and a dome of ribs
    b.box(CONCRETE, (0, 1.6, -3.0), (13.0, 3.2, 9.0))
    b.box(CEMENT, (0, 3.25, -3.0), (13.4, 0.15, 9.4))
    for k in range(9):
        a = k * 20 - 80
        b.beam(IRON, (5.4 * math.cos(math.radians(a)), 3.3, -3.0 + 3.6 * math.sin(math.radians(a))), (0, 7.2, -3.0), 0.06)
    b.cyl(TARP, (0, 3.3, -3.0), 5.2, 0.06, segs=18, r2=0.4)
    b.cyl(IRON, (0, 3.3, -3.0), 0.5, 4.0, segs=10, r2=0.3); b.box(GLOW, (0, 7.5, -3.0), (0.35, 0.35, 0.35))
    for k in range(18):
        a = k * 20
        b.box(GRAVEL, (7.0 * math.cos(math.radians(a)), 0.45, -3.0 + 5.0 * math.sin(math.radians(a))), (1.4, 0.9, 0.9), yaw=-a)
    # door with a light, a window strip with bars, the sign
    b.box(IRON, (0, 1.0, 1.55), (1.6, 2.0, 0.08)); b.box(GLOW, (0, 2.4, 1.55), (0.4, 0.2, 0.06))
    for xx in (-4.5, 4.5):
        b.box(GLOW, (xx, 2.2, 1.55), (2.4, 0.5, 0.05))
        for k in range(5):
            b.rod(IRON, (xx - 1.0 + k * 0.5, 1.9, 1.62), (xx - 1.0 + k * 0.5, 2.5, 1.62), 0.02, segs=4)
    b.box(RUST, (0, 3.9, 1.6), (9.0, 1.0, 0.12)); b.text(GLOW, 'RADIOLOGY', (0, 3.6, 1.68), 0.62, 0.06)
    trefoil(b, (-6.0, 2.0, 1.6), r=0.6); trefoil(b, (6.0, 2.0, 1.6), r=0.6)
    # the isotope shed: a caged container with drums and a heavy padlock, hazard posts
    b.container((-8.5, 1.25, 6.0), 6, IRON, size=(5.0, 2.5, 2.4))
    for k in range(7):
        b.rod(IRON, (-11.0 + k * 0.85, -0.2, 7.3), (-11.0 + k * 0.85, 2.8, 7.3), 0.03, segs=4)
    b.beam(IRON, (-11.0, 2.8, 7.3), (-6.0, 2.8, 7.3), 0.03)
    for k in range(4):
        b.drum((-5.0 + (k % 2) * 0.7, 0, 5.2 + (k // 2) * 0.7), yaw=R.uniform(0, 360))
    hazard_post(b, -11.5, 4.5); hazard_post(b, -3.5, 8.5)
    # patients' bench row and a waiting tent, a generator, a water butt
    for k in range(4):
        b.box(WOOD, (5.0 + k * 1.6, 0.45, 5.0), (1.3, 0.08, 0.5)); b.box(WOOD, (5.0 + k * 1.6, 0.2, 5.0), (0.2, 0.45, 0.4))
    tent(b, (8.5, 0, 8.0), (4.0, 2.4, 3.2), yaw=-4)
    b.box(RED, (10.0, 0.7, -9.0), (2.4, 1.4, 1.4)); b.cyl(IRON, (10.8, 1.4, -9.0), 0.12, 1.6, segs=8); b.fire.append((10.0, 0.8, -9.0))
    b.cyl(RUST, (-9.5, 0, -8.5), 0.9, 2.0, segs=12); b.cyl(IRON, (-9.5, 2.0, -8.5), 0.95, 0.25, segs=12, r2=0.2)
    # gate on +z
    for tx in (-3.5, 3.5):
        b.box(CORR, (tx, 1.9, 11), (1.5, 3.8, 1.5)); b.spikes(tx, 3.8, 11, 3, spread=0.5)
    b.beam(IRON, (-3.5, 4.4, 11), (3.5, 4.4, 11), 0.14)
    b.box(STRIPES, (0, 3.9, 11), (5.6, 0.9, 0.12))
    b.lamp(-5.0, 4.2, 9.8, arm=0.8, yaw=0); b.lamp(5.0, 4.2, 9.8, arm=0.8, yaw=180)
    b.flag(11.5, 3.0, -10.5, mat=TARP); b.tyre_stack(11.0, 9.5, 2)
    return 'Radiology Board'


def recovery_center(b):
    R = b.R
    b.box(GROUND, (0, -0.25, 0), (44, 0.5, 34))
    # double fence with towers, gate on +z, bus stations along the inside of the gate
    b.wall_run(-21, -16, 21, -16, base_h=3.6); b.wall_run(21, -16, 21, 16, base_h=3.6); b.wall_run(-21, 16, -21, -16, base_h=3.6)
    b.wall_run(21, 16, 6, 16, base_h=3.6); b.wall_run(-6, 16, -21, 16, base_h=3.6)
    for tx, tz in ((-20, -15), (20, -15), (-20, 15), (20, 15)):
        for px, pz in ((-0.8, -0.8), (0.8, -0.8), (-0.8, 0.8), (0.8, 0.8)):
            b.rod(IRON, (tx + px, -0.2, tz + pz), (tx + px * 0.7, 6.5, tz + pz * 0.7), 0.09)
        b.box(WOOD, (tx, 6.6, tz), (2.4, 0.1, 2.4)); b.box(CORR, (tx, 8.4, tz), (2.8, 0.06, 2.8), pitch=6)
        for k in range(4):
            b.rod(IRON, (tx - 1.2 + (k % 2) * 2.4, 6.6, tz - 1.2 + (k // 2) * 2.4), (tx - 1.2 + (k % 2) * 2.4, 8.3, tz - 1.2 + (k // 2) * 2.4), 0.05)
        b.lamp(tx, 8.0, tz, arm=0.9, yaw=45)
    # the ward: a long tarp hall over container ends, cots visible as boxes, a medics' hut
    for k in range(4):
        b.container((-12.0 + k * 6.3, 1.25, -9.0), R.uniform(-2, 2), R.choice([RED, CORR, RUST]))
    for xx in (-15.0, -9.0, -3.0, 3.0, 9.0):
        b.rod(IRON, (xx, -0.2, -12.5), (xx, 6.2, -12.5), 0.14); b.rod(IRON, (xx, -0.2, -3.0), (xx, 6.2, -3.0), 0.14)
        b.beam(IRON, (xx, 6.2, -12.5), (xx, 6.2, -3.0), 0.12)
    b.box(TARP, (-3.0, 6.3, -7.75), (26.0, 0.06, 10.5), pitch=-4)
    for k in range(6):
        b.box(WOOD, (-13.0 + k * 3.2, 0.5, -4.5), (1.8, 0.35, 0.8)); b.box(BONE, (-13.0 + k * 3.2, 0.72, -4.5), (1.7, 0.1, 0.7))
    b.shack((13.5, 0, -8.0), (5.0, 2.8, 4.0), yaw=6)
    b.box(GLOW, (13.5, 1.8, -5.9), (0.9, 0.4, 0.05)); b.box(RED, (13.5, 2.9, -8.0), (1.6, 0.35, 0.05))
    # quarantine tents in rows behind a rope line, hazard posts, a shower line and drums
    for k in range(6):
        tent(b, (-14.0 + k * 5.2, 0, 4.0), (3.6, 2.3, 4.0), yaw=R.uniform(-8, 8), mat=R.choice([TARP, TARP, RED]))
    for k in range(7):
        hazard_post(b, -16.0 + k * 5.2, 8.0, h=1.4)
    b.beam(RED, (-16.0, 1.2, 8.0), (15.2, 1.2, 8.0), 0.02)
    for xx in (10.0, 14.0):
        b.rod(IRON, (xx, -0.2, 2.0), (xx, 3.0, 2.0), 0.06); b.rod(IRON, (xx, -0.2, 6.0), (xx, 3.0, 6.0), 0.06)
        b.beam(IRON, (xx, 3.0, 2.0), (xx, 3.0, 6.0), 0.05)
    b.beam(IRON, (10.0, 3.0, 2.0), (14.0, 3.0, 2.0), 0.05); b.beam(IRON, (10.0, 3.0, 6.0), (14.0, 3.0, 6.0), 0.05)
    for k in range(4):
        b.cyl(IRON, (10.5 + k * 1.0, 2.9, 4.0), 0.12, 0.3, segs=8, pitch=90)
    b.box(CONCRETE, (12.0, 0.15, 4.0), (5.0, 0.3, 5.0)); b.box(TARP, (12.0, 0.5, 4.0), (4.4, 0.05, 4.4))
    for k in range(8):
        b.drum((16.5 + (k % 2) * 0.7, 0, 0.0 + (k // 2) * 0.75), yaw=R.uniform(0, 360))
    # water tower, a cook fire ring, a burnt-out bus as the morgue
    for px, pz in ((-1.0, -1.0), (1.0, -1.0), (-1.0, 1.0), (1.0, 1.0)):
        b.rod(IRON, (-17.0 + px, -0.2, -12.0 + pz), (-17.0 + px * 0.8, 6.0, -12.0 + pz * 0.8), 0.1)
    b.cyl(RUST, (-17.0, 6.0, -12.0), 1.4, 2.0, segs=14); b.cyl(IRON, (-17.0, 8.0, -12.0), 1.45, 0.4, segs=14, r2=0.2)
    b.cyl(IRON, (16.5, 0, -12.5), 0.32, 0.9, segs=10); b.fire.append((16.5, 0.9, -12.5)); b.cyl(GLOW, (16.5, 0.92, -12.5), 0.28, 0.06, segs=10)
    b.car_wreck((-17.5, 0, 11.5), 80, 3, IRON)
    # gate: two pylons, stripes, a trefoil and the sign; bus stations run in from the gate
    for tx in (-6.0, 6.0):
        b.box(CORR, (tx, 2.4, 16), (2.0, 4.8, 2.0)); b.spikes(tx, 4.8, 16, 4, spread=0.7)
    b.beam(IRON, (-6.0, 5.6, 16), (6.0, 5.6, 16), 0.2)
    b.box(STRIPES, (0, 5.0, 16), (8.0, 1.2, 0.12)); b.text(GLOW, 'RECOVERY', (0, 4.6, 16.08), 0.8, 0.06)
    trefoil(b, (0, 6.5, 16.0), r=0.8)
    b.lamp(-7.5, 5.2, 14.5, arm=0.9, yaw=0); b.lamp(7.5, 5.2, 14.5, arm=0.9, yaw=180)
    b.flag(-20.3, 3.6, -15.3, mat=RED); b.flag(20.3, 3.6, 15.3, mat=TARP)
    b.tyre_stack(19.0, 13.0, 3); b.tyre_stack(-19.5, -2.0, 2); b.blob(RUST, (18.5, 0, -14.0), (2.0, 0.9, 1.7), jitter=0.3)
    return 'Recovery Center'


# ------------------------------------------------------------------ inis --

COST = ['-------', '$COST_WORK SOVIET_CONSTRUCTION_GROUNDWORKS 0.0', '$COST_WORK_BUILDING_ALL', '$COST_RESOURCE_AUTO ground_asphalt 0.03',
        '------------------', '$COST_WORK SOVIET_CONSTRUCTION_STEEL_LAYING 1.0', '$COST_WORK_BUILDING_ALL', '$COST_RESOURCE_AUTO wall_steel 0.2',
        '-----------------------', '']


def ini_dtf():
    return '\r\n'.join(['$NAME_STR "Decontamination Task Force"', '',
        '; A police station. Its cars are Geiger patrols: they drive to a contamination',
        '; report (a "crime" raised by the fallout plugin from radiation dose), sweep the',
        '; site and screen the household. Unswept cases keep contaminating the area.', ''] + COST + [
        '$TYPE_POLICE_STATION',
        '$WORKERS_NEEDED 12',
        '$PROFESORS_NEEDED 8',
        '$WORKING_VEHICLES_NEEDED 4',
        '$STORAGE_FUEL RESOURCE_TRANSPORT_OIL 15.00', '',
        '$VEHICLE_STATION -10.5 0 -9.0  -10.5 0 -2.5',
        '$VEHICLE_STATION  -5.5 0 -9.0   -5.5 0 -2.5',
        '$VEHICLE_STATION  -0.5 0 -9.0   -0.5 0 -2.5',
        '$VEHICLE_STATION   4.5 0 -9.0    4.5 0 -2.5', '',
        '$CONNECTIONS_ROAD_DEAD_SQUARE', '-15.5 13.5', '15.5 -13.5', '',
        '$CONNECTION_ROAD', '0.0 0.0 14.5', '0.0 0.0 13.0',
        '$CONNECTION_PEDESTRIAN', '-7.0 0.0 13.0', '-7.0 0.0 14.5', '',
        'end', ''])


def ini_board():
    return '\r\n'.join(['$NAME_STR "Radiology Board"', '',
        '; A courthouse. Physicians (professors) assess each screened case and set the',
        '; quarantine length; an overloaded board drops cases, which stay contaminated.', ''] + COST + [
        '$TYPE_COURT_HOUSE',
        '$WORKERS_NEEDED 12',
        '$PROFESORS_NEEDED 8', '',
        '$VEHICLE_STATION 0.0 0 3.5  0.0 0 9.5', '',
        '$CONNECTIONS_ROAD_DEAD_SQUARE', '-13.5 12.5', '13.5 -12.5', '',
        '$CONNECTION_ROAD', '0.0 0.0 13.5', '0.0 0.0 12.0',
        '$CONNECTION_PEDESTRIAN', '-6.0 0.0 12.0', '-6.0 0.0 13.5', '',
        'end', ''])


def ini_recovery():
    return '\r\n'.join(['$NAME_STR "Recovery Center"', '',
        '; A prison. Beds are quarantine capacity, wardens are medics, security is',
        '; containment (breaches send patients home still hot), the prison bus is the',
        '; quarantine bus that takes convalescent crews to work.', ''] + COST + [
        '$TYPE_PRISON',
        '$WORKERS_NEEDED 30',
        '$CITIZEN_ABLE_SERVE 3',
        '$STORAGE_DEMAND_PRISON RESOURCE_TRANSPORT_COVERED 30',
        '$STORAGE_DEMAND_PRISON RESOURCE_TRANSPORT_COOLER 8',
        '$QUALITY_OF_LIVING 0.50',
        '$STATION_NOT_BLOCK', '',
        '$VEHICLE_STATION -3.0 0 3.0  -3.0 0 14.0',
        '$VEHICLE_STATION  3.0 0 3.0   3.0 0 14.0', '',
        '$CONNECTIONS_ROAD_DEAD_SQUARE', '-22.5 17.5', '22.5 -17.5', '',
        '$CONNECTION_ROAD', '0.0 0.0 18.5', '0.0 0.0 17.0',
        '$CONNECTION_PEDESTRIAN', '-9.0 0.0 17.0', '-9.0 0.0 18.5',
        '$CONNECTION_PEDESTRIAN', '9.0 0.0 17.0', '9.0 0.0 18.5', '',
        'end', ''])


ASSETS = [('dtf_station', dtf_station, ini_dtf, (-38.0, 24.0, 44.0), (0.0, 2.0, -1.0)),
          ('radiology_board', radiology_board, ini_board, (-34.0, 22.0, 40.0), (0.0, 2.0, -1.0)),
          ('recovery_center', recovery_center, ini_recovery, (-52.0, 30.0, 58.0), (0.0, 2.0, -1.0))]

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
        print('%-18s %-28s tris=%5d nodes=%d bbox=%s fire=%d' % (key, title, sum(s.nt for s in shapes), len(shapes), ['%.1f' % v for v in bbox], len(b.fire)))
    cfg += ['', '$ITEM_NAME "Contamination Kit"', '', '$ITEM_DESC "Decontamination Task Force, Radiology Board and Recovery Center: the police, court and prison of a republic where the crime is radiation."', '', '$END', '']
    mmkit.write_text(os.path.join(KITDIR, 'workshopconfig.ini'), '\r\n'.join(cfg))
    print('contamination kit done')


main()
