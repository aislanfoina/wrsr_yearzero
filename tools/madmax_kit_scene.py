"""The Mad Max map kit: a dozen monument-type decorations for a wasteland map.

    blender -b --python tools/madmax_kit_scene.py -- <texdir> <kitdir> <previewdir>

One workshop item, many buildings (as vanilla ports mods do), sharing the
texture set in <kitdir>/material. Each asset is a $TYPE_MONUMENT: placeable
anywhere in the map editor, no workers, no function - just the look.
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
KITDIR = argv[1] if len(argv) > 1 else 'mod/buildings/madmax_kit'
PREVIEW = argv[2] if len(argv) > 2 else 'build/kit'
ITEM_ID = 9000002


# ------------------------------------------------------------------ assets --

def scrap_wall(b):
    b.wall_run(-12, 0.2, 12, 0.2, base_h=4.8)
    for x in (-9, -2, 5, 10):
        b.tyre_stack(x + b.R.uniform(-1, 1), -1.3, b.R.randint(2, 4))
    b.rod(IRON, (6, 0, -0.6), (6, 5.2, -0.6), 0.05); b.rod(IRON, (6.5, 0, -0.6), (6.5, 5.2, -0.6), 0.05)
    for k in range(9):
        b.beam(IRON, (6, 0.5 + k * 0.55, -0.6), (6.5, 0.5 + k * 0.55, -0.6), 0.04)
    b.flag(-10, 4.6, 0.0, mat=RED)
    b.box(GROUND, (0, -0.25, -0.4), (25, 0.5, 4.5))
    return (0.0, 0.0, -2.5), 'Scrap Wall'


def wall_tower(b):
    for lvl, mat in enumerate((RUST, CORR, RED)):
        b.box(mat, (b.R.uniform(-0.15, 0.15), 1.25 + lvl * 2.5, b.R.uniform(-0.15, 0.15)), (4.0, 2.5, 4.0), yaw=b.R.uniform(-4, 4))
    b.box(WOOD, (0, 7.65, 0), (4.8, 0.2, 4.8))
    for px, pz in ((-2.3, -2.3), (2.3, -2.3), (-2.3, 2.3), (2.3, 2.3)):
        b.rod(IRON, (px, 7.7, pz), (px, 10.6, pz), 0.07)
        b.rod(IRON, (px, 7.7, pz), (px, 8.8, pz), 0.05)
    for (a, c) in (((-2.3, -2.3), (2.3, -2.3)), ((2.3, -2.3), (2.3, 2.3)), ((2.3, 2.3), (-2.3, 2.3)), ((-2.3, 2.3), (-2.3, -2.3))):
        b.beam(IRON, (a[0], 8.8, a[1]), (c[0], 8.8, c[1]), 0.06)
    b.box(CORR, (0, 10.7, 0), (5.4, 0.07, 5.4), pitch=8, roll=-5)
    b.spikes(0, 10.75, 0, 8, spread=2.4, h=0.8)
    b.beam(IRON, (-2.0, 0.5, 2.05), (2.0, 7.2, 2.05), 0.18); b.beam(IRON, (2.0, 0.5, 2.05), (-2.0, 7.2, 2.05), 0.18)
    b.skull((0, 6.3, 2.2), 0.6)
    b.flag(2.4, 10.7, -2.4, h=3.2, mat=RED)
    b.tyre_stack(-3.2, 2.2, 3); b.tyre_stack(3.1, -2.6, 2)
    b.box(GROUND, (0, -0.25, 0), (7, 0.5, 7))
    return (0.0, 0.0, -3.5), 'Wall Tower'


def watchtower(b):
    for px, pz in ((-1.6, -1.6), (1.6, -1.6), (-1.6, 1.6), (1.6, 1.6)):
        b.rod(IRON, (px, -0.2, pz), (px * 0.7, 13.0, pz * 0.7), 0.14, segs=8)
    for hh in (3.0, 6.0, 9.0):
        s = 1.6 * (1 - 0.3 * hh / 13.0)
        for (a, c) in (((-1, -1), (1, -1)), ((1, -1), (1, 1)), ((1, 1), (-1, 1)), ((-1, 1), (-1, -1))):
            b.beam(IRON, (a[0] * s, hh, a[1] * s), (c[0] * s, hh, c[1] * s), 0.09)
        s2 = 1.6 * (1 - 0.3 * (hh + 3) / 13.0)
        b.beam(IRON, (-s, hh, -s), (s2, hh + 3, -s2), 0.07)
        b.beam(IRON, (s, hh, s), (-s2, hh + 3, s2), 0.07)
    b.box(WOOD, (0, 13.1, 0), (3.6, 0.2, 3.6))
    for px, pz in ((-1.7, -1.7), (1.7, -1.7), (-1.7, 1.7), (1.7, 1.7)):
        b.rod(IRON, (px, 13.1, pz), (px, 15.6, pz), 0.06)
    for (a, c) in (((-1.7, -1.7), (1.7, -1.7)), ((1.7, -1.7), (1.7, 1.7)), ((1.7, 1.7), (-1.7, 1.7)), ((-1.7, 1.7), (-1.7, -1.7))):
        b.beam(IRON, (a[0], 14.1, a[1]), (c[0], 14.1, c[1]), 0.05)
    b.cyl(CORR, (0, 15.6, 0), 2.9, 1.6, segs=4, r2=0.05, yaw=45, smooth=False)
    b.rod(IRON, (-1.3, 15.6, 1.3), (-1.3, 20.5, 1.3), 0.05)
    b.flag(-1.3, 17.5, 1.3, h=2.5, mat=RED)
    b.rod(IRON, (1.2, 15.2, -1.2), (1.2, 16.9, -1.2), 0.07)
    b.cyl(IRON, (1.2, 16.9, -1.2), 1.1, 0.45, segs=12, r2=0.15, pitch=-50)
    b.cyl(IRON, (0.9, 13.3, 0.5), 0.28, 0.5, segs=8, pitch=70)
    b.cyl(GLOW, (0.9, 13.32, 0.5), 0.22, 0.55, segs=8, pitch=70)
    b.skull((0, 3.2, 1.9), 0.5)
    b.drum((-2.4, 0, 2.2)); b.drum((-1.8, 0, 2.7), yaw=30)
    b.fire.append((-2.1, 0.5, 2.4))
    b.box(GROUND, (0, -0.25, 0), (7, 0.5, 7))
    return (0.0, 0.0, -3.5), 'Watchtower'


def shanty(b):
    R = b.R
    for (x, z, w, h, d, yaw) in ((-7, -4, 4.5, 2.6, 3.5, 8), (-1, -5.5, 3.6, 2.4, 3.0, -12), (5.5, -3.5, 5.0, 2.8, 4.0, 4),
                                 (-6.5, 4.5, 3.8, 2.5, 3.2, -25), (6, 4.5, 4.2, 2.7, 3.6, 18)):
        b.shack((x, 0, z), (w, h, d), yaw=yaw)
    b.cyl(IRON, (0, 0, 0), 0.32, 0.9, segs=10)
    b.fire.append((0, 0.9, 0))
    for k in range(5):
        a = k * 72 + 20
        b.tyre_stack(1.6 * math.cos(math.radians(a)), 1.6 * math.sin(math.radians(a)), 1)
    b.drum((-3.2, 0, 0.5)); b.drum((-2.6, 0, 1.1), yaw=40); b.drum((2.8, 0, 0.4), lying=True, yaw=70)
    b.blob(IRON, (9.5, 0, 0), (1.8, 0.8, 1.6), jitter=0.3); b.blob(RUST, (-10, 0, 1), (1.6, 0.7, 1.4), jitter=0.3)
    b.rod(IRON, (-4.2, 0, 7.0), (-4.2, 5.0, 7.0), 0.06); b.rod(IRON, (4.2, 0, 7.0), (4.2, 5.0, 7.0), 0.06)
    b.rod(IRON, (-4.2, 4.9, 7.0), (4.2, 4.7, 7.0), 0.02)
    for k in range(5):
        b.box(R.choice([TARP, RED, WOOD]), (-3.2 + k * 1.6, 4.4, 7.0), (0.35, 0.5, 0.02), roll=R.uniform(-30, 30))
    b.lamp(7.5, 3.8, 0.0, arm=0.8, yaw=180)
    b.tyre_stack(-9, -7, 3); b.tyre_stack(9, 7.5, 2)
    b.box(GROUND, (0, -0.25, 0), (24, 0.5, 18))
    return (0.0, 0.0, -9.0), 'Shanty Cluster'


def fuel_depot(b):
    for zz in (-3.0, 1.5):
        b.cyl(RUST, (-3.5, 1.3, zz), 1.1, 7.0, segs=14, pitch=90, yaw=90)
        for xx in (-2.0, 4.0):
            b.beam(IRON, (xx, 0.0, zz - 1.2), (xx, 0.0, zz + 1.2), 0.35, 0.7)
        b.box(STRIPES, (0.0, 1.3, zz), (0.4, 2.3, 2.3))
    b.cyl(RUST, (6.5, 0, -1.0), 1.6, 5.5, segs=14)
    b.cyl(IRON, (6.5, 5.5, -1.0), 1.65, 0.5, segs=14, r2=0.3)
    b.rod(IRON, (8.0, 0, 0.4), (8.0, 5.9, 0.4), 0.06)
    for k in range(10):
        b.beam(IRON, (7.85, 0.5 + k * 0.55, 0.4), (8.15, 0.5 + k * 0.55, 0.4), 0.04)
    b.box(IRON, (2.5, 0.6, 5.0), (0.7, 1.2, 0.5)); b.box(RED, (2.5, 1.35, 5.0), (0.6, 0.3, 0.45))
    b.rod(IRON, (2.9, 1.0, 5.0), (3.6, 0.3, 5.6), 0.03)
    b.box(GLOW, (2.5, 0.9, 5.26), (0.3, 0.2, 0.02))
    for k in range(7):
        b.drum((-8.5 + (k % 4) * 0.7, 0, 4.0 + (k // 4) * 0.7), yaw=b.R.uniform(0, 360))
    b.drum((-6, 0, 6.2), lying=True, yaw=25)
    b.rod(IRON, (9.5, 0, 5.0), (9.5, 5.0, 5.0), 0.1)
    b.skull((9.5, 5.3, 5.0), 0.6)
    for k in range(3):
        b.torus(TIRE, (9.5, 0.2 + k * 0.38, 5.0), 0.5, 0.2)
    b.spikes(9.5, 4.6, 5.0, 4, spread=0.5)
    b.lamp(-8.5, 4.5, -5.5, arm=0.9, yaw=0)
    b.wall_run(-10.5, -6.5, 10.5, -6.5, base_h=3.6)
    b.fire.append((-3.5, 1.5, -3.0)); b.fire.append((6.5, 3.0, -1.0)); b.fire.append((-7.5, 0.5, 4.3))
    b.box(GROUND, (0, -0.25, 0), (22, 0.5, 14))
    return (0.0, 0.0, -7.0), 'Fuel Depot'


def wreck_yard(b):
    R = b.R
    for k in range(3):
        b.box(R.choice([RED, RUST, IRON]), (-6 + R.uniform(-0.2, 0.2), 0.45 + k * 0.9, -4), (4.0, 0.8, 1.7), yaw=R.uniform(-6, 6))
    for k in range(4):
        b.box(R.choice([RED, RUST, IRON, CORR]), (-1 + R.uniform(-0.2, 0.2), 0.4 + k * 0.8, -5), (3.8, 0.7, 1.6), yaw=R.uniform(-8, 8) + 90)
    b.car_wreck((5.0, 0, -3.5), 35, 0, RED)
    b.car_wreck((8.5, 0, 3.0), -70, 25, RUST)
    b.car_wreck((-8, 0, 4.5), 110, 0, IRON)
    for k in range(9):
        b.tyre_stack(-4 + R.uniform(-3, 3), 5.5 + R.uniform(-2, 2), R.randint(1, 4))
    b.blob(IRON, (2, 0, 6), (2.6, 1.2, 2.2), jitter=0.3); b.blob(RUST, (-3, 0, -0.5), (1.9, 0.9, 1.7), jitter=0.3)
    # gantry crane with a magnet
    for xx in (-10.5, 10.5):
        b.rod(IRON, (xx, -0.2, -8), (xx, 8.0, -8), 0.14, segs=8); b.rod(IRON, (xx, -0.2, 8), (xx, 8.0, 8), 0.14, segs=8)
        b.beam(IRON, (xx, 8.0, -8), (xx, 8.0, 8), 0.25)
    b.beam(IRON, (-10.5, 8.2, 1.0), (10.5, 8.2, 1.0), 0.3)
    b.box(IRON, (2.0, 7.6, 1.0), (1.6, 0.8, 1.2))
    b.rod(IRON, (2.0, 7.2, 1.0), (2.0, 3.6, 1.0), 0.03)
    b.cyl(IRON, (2.0, 3.0, 1.0), 0.7, 0.5, segs=12)
    b.drum((10, 0, -5)); b.drum((10.6, 0, -4.4), yaw=50)
    b.fire.append((10.3, 0.5, -4.7))
    b.box(GROUND, (0, -0.25, 0), (24, 0.5, 18))
    return (0.0, 0.0, -9.0), 'Wreck Yard'


def ruin_block(b):
    R = b.R
    W, D, floors = 20.0, 12.0, 3
    fh = 3.0
    # floor slabs, the top one collapsed
    for k in range(floors):
        if k < floors - 1:
            b.box(CONCRETE, (0, fh * (k + 1), 0), (W, 0.3, D))
    b.box(CONCRETE, (-3, fh * floors - 1.2, 1.5), (11, 0.3, 8), roll=-14, pitch=6)
    # walls as panels with gaps (windows and blown-out sections)
    for k in range(floors):
        y = fh * k
        for (x0, z0, x1, z1) in ((-W / 2, -D / 2, W / 2, -D / 2), (W / 2, -D / 2, W / 2, D / 2), (W / 2, D / 2, -W / 2, D / 2), (-W / 2, D / 2, -W / 2, -D / 2)):
            L = math.hypot(x1 - x0, z1 - z0); n = int(L / 2.0)
            ux, uz = (x1 - x0) / L, (z1 - z0) / L
            yaw = math.degrees(math.atan2(-uz, ux))
            for i in range(n):
                if R.random() < 0.3 + 0.22 * k:
                    continue
                t = (i + 0.5) * L / n
                cx, cz = x0 + ux * t, z0 + uz * t
                hh = fh if R.random() < 0.55 else R.uniform(0.6, 2.2)
                mat = BRICK if R.random() < 0.45 else CONCRETE if R.random() < 0.6 else IRON   # IRON = fire-blackened
                b.box(mat, (cx, y + hh / 2, cz), (L / n + 0.02, hh, 0.35), yaw=yaw, pitch=R.uniform(-2, 2) if hh < fh else 0)
                if hh >= fh and R.random() < 0.55:
                    b.box(IRON, (cx, y + 1.6, cz), (1.2, 1.3, 0.38), yaw=yaw)   # dark window hole
                    if R.random() < 0.5:
                        b.box(IRON, (cx, y + 2.6, cz), (1.5, 0.5, 0.4), yaw=yaw)   # soot above the window
    # columns
    for x in (-W / 2 + 0.3, -3.3, 3.3, W / 2 - 0.3):
        for z in (-D / 2 + 0.3, D / 2 - 0.3):
            b.box(CONCRETE, (x, fh * floors / 2, z), (0.5, fh * floors, 0.5))
    # rebar sticking out of the broken top
    for k in range(18):
        b.spike(IRON, (R.uniform(-W / 2, W / 2), fh * floors - 0.3, R.uniform(-D / 2, D / 2)), (R.uniform(-0.4, 0.4), 1, R.uniform(-0.4, 0.4)), R.uniform(0.6, 1.6), radius=0.03)
    # rubble, inside and spilling out the front
    for k in range(10):
        b.blob(CONCRETE if k % 2 else BRICK, (R.uniform(-W / 2 - 1, W / 2 + 1), 0, R.uniform(D / 2 - 1, D / 2 + 3)), (R.uniform(1.5, 3.0), R.uniform(0.6, 1.4), R.uniform(1.2, 2.4)), jitter=0.3)
    for k in range(5):
        b.blob(CONCRETE, (R.uniform(-W / 2 + 2, W / 2 - 2), 0, R.uniform(-D / 2 + 1, D / 2 - 1)), (R.uniform(1.5, 2.5), R.uniform(0.5, 1.0), R.uniform(1.2, 2.0)), jitter=0.3)
    b.blob(CONCRETE, (-W / 2 - 1.5, 0, -2), (2.5, 1.0, 3.0), jitter=0.3)
    # a broken slab leaning against the side, and a burnt bus shell in front
    b.box(CONCRETE, (W / 2 + 1.6, 1.6, -3), (0.3, 4.5, 5.0), roll=-28)
    b.box(IRON, (-4, 1.2, D / 2 + 4.5), (8.0, 2.4, 2.4), yaw=12)
    b.box(RUST, (-4, 2.45, D / 2 + 4.5), (7.0, 0.1, 2.0), yaw=12)
    b.car_wreck((6, 0, D / 2 + 3.5), 15, 0, RUST)
    b.drum((-8, 0, D / 2 + 2.5)); b.fire.append((-8, 0.5, D / 2 + 2.5))
    b.fire.append((2, fh * 2 + 0.5, 0))
    b.box(GROUND, (0, -0.25, 1.0), (W + 6, 0.5, D + 8))
    return (0.0, 0.0, -D / 2 - 5.0), 'Ruined Block'


def road_wreck(b):
    # jack-knifed truck: cab + trailer, cars piled behind
    b.box(RED, (-6, 1.5, 2), (2.6, 2.6, 4.0), yaw=35)
    b.box(IRON, (-6, 2.3, 2), (2.65, 0.9, 2.0), yaw=35)
    for sx, sz in ((-1.0, 1.4), (1.0, 1.4), (-1.0, -1.4), (1.0, -1.4)):
        M = rot(0, 35, 0)
        off = M @ Vector((sx, -sz, 0.55))
        b.torus(TIRE, (-6 + off.x, 0.55, 2 - off.y), 0.55, 0.22, axis='z', yaw=35)
    b.box(CORR, (2.5, 1.8, -1.0), (10.0, 2.8, 2.5), yaw=-8, roll=18)
    b.box(IRON, (2.5, 0.4, -1.0), (9.5, 0.4, 2.4), yaw=-8, roll=18)
    for k in range(4):
        b.torus(TIRE, (5.5 + k * 0.9, 0.5, 0.6), 0.5, 0.2, axis='z', yaw=-8)
    b.car_wreck((9.5, 0, 3.0), 60, 0, RUST)
    b.car_wreck((-11, 0.3, -1.5), -20, 15, IRON)
    for k in range(5):
        b.drum((3 + k * 0.8, 0, 2.8 + (k % 2) * 0.5), lying=(k % 2 == 0), yaw=b.R.uniform(0, 360))
    b.blob(IRON, (-1, 0, 3.5), (2.0, 0.8, 1.6), jitter=0.3)
    b.tyre_stack(-9, 4, 2); b.tyre_stack(12, -2, 3)
    b.fire.append((-6, 2.0, 2)); b.fire.append((4, 0.4, 2.9))
    b.box(GROUND, (0, -0.25, 0), (28, 0.5, 12))
    return (0.0, 0.0, -6.0), 'Road Wreck'


def totem(b):
    b.rod(IRON, (0, -0.2, 0), (0, 7.5, 0), 0.14, segs=8)
    for k in range(4):
        b.torus(TIRE, (0, 0.2 + k * 0.38, 0), 0.55, 0.2)
    b.skull((0, 3.2, 0), 0.7); b.skull((0, 5.2, 0), 0.55, yaw=90); b.skull((0, 7.7, 0), 0.8)
    for k, (a, txt) in enumerate(((20, 'GUZZOLINE'), (-60, 'NO TRESPASS'), (130, 'CITADEL'))):
        y = 2.2 + k * 1.1
        b.box(RUST if k % 2 else WOOD, (0.7 * math.cos(math.radians(a)), y, -0.7 * math.sin(math.radians(a))), (1.6, 0.36, 0.05), yaw=a, roll=b.R.uniform(-8, 8))
    b.spikes(0, 7.9, 0, 6, spread=0.35, h=0.9)
    for k in range(3):
        a = k * 120 + 40
        b.rod(IRON, (0, 6.5, 0), (1.9 * math.cos(math.radians(a)), 0.1, 1.9 * math.sin(math.radians(a))), 0.02, segs=4)
    b.blob(BONE, (1.2, 0, 0.8), (0.6, 0.3, 0.5), jitter=0.2)
    b.box(GROUND, (0, -0.25, 0), (4.5, 0.5, 4.5))
    return (0.0, 0.0, -2.2), 'Skull Totem'


def windpump(b):
    for px, pz in ((-1.4, -1.4), (1.4, -1.4), (-1.4, 1.4), (1.4, 1.4)):
        b.rod(IRON, (px, -0.2, pz), (px * 0.35, 11.0, pz * 0.35), 0.09)
    for hh in (2.5, 5.0, 7.5, 10.0):
        s = 1.4 * (1 - 0.65 * hh / 11.0)
        for (a, c) in (((-1, -1), (1, -1)), ((1, -1), (1, 1)), ((1, 1), (-1, 1)), ((-1, 1), (-1, -1))):
            b.beam(IRON, (a[0] * s, hh, a[1] * s), (c[0] * s, hh, c[1] * s), 0.06)
    b.rod(IRON, (0, 10.8, 0), (0, 11.6, 1.2), 0.08)
    b.box(IRON, (0, 11.6, 1.3), (0.5, 0.5, 0.5))
    # radial blades: each box's long axis (y) is rotated about the rotor axis (x)
    for k in range(8):
        a = k * 45.0
        b.box(RUST if k % 2 else CORR, (0, 11.6 + 1.05 * math.cos(math.radians(a)), 1.5 - 1.05 * math.sin(math.radians(a))), (0.04, 2.0, 0.5), pitch=a)
    b.torus(IRON, (0, 11.6, 1.5), 2.05, 0.03, segs=16, rings=4, axis='z')
    b.box(RED, (0, 11.6, -1.2), (1.2, 0.9, 0.05))
    b.cyl(RUST, (3.0, 0, 0), 1.3, 2.4, segs=12)
    b.rod(IRON, (0, 0.2, 0), (2.4, 2.0, 0), 0.05)
    b.drum((-2.6, 0, 2.2)); b.tyre_stack(3.2, 2.6, 2)
    b.box(GROUND, (0.5, -0.25, 0), (8, 0.5, 6))
    return (0.0, 0.0, -3.0), 'Junk Windpump'


def barricade(b):
    R = b.R
    b.container((-4.5, 1.25, 0.3), 6, RUST)
    b.container((4.8, 1.25, -0.2), -5, RED)
    b.box(CORR, (0.2, 1.0, 0.0), (3.2, 2.0, 0.08), yaw=4, pitch=-8)
    for k in range(9):
        b.tyre_stack(-7 + k * 1.75 + R.uniform(-0.3, 0.3), 1.6 + R.uniform(-0.2, 0.2), R.randint(2, 4))
    b.spikes(-4.5, 2.55, 0.3, 6, spread=2.6); b.spikes(4.8, 2.55, -0.2, 6, spread=2.6)
    for k in range(6):
        b.spike(IRON, (-7 + k * 2.8, 0.2, 2.2), (0, 0.5, 1), 1.1, radius=0.06)
    b.flag(-7.6, 2.5, 0.3, mat=RED)
    b.blob(IRON, (8.5, 0, 1.5), (1.4, 0.7, 1.2), jitter=0.3)
    b.box(GROUND, (0, -0.25, 0.6), (18, 0.5, 5))
    return (0.0, 0.0, -2.0), 'Tyre Barricade'


def scrap_gatehouse(b):
    """A gate arch with no road through it - a landmark to put beside a road."""
    for tx in (-7, 7):
        for lvl, mat in enumerate((RUST, CORR, RED)):
            b.box(mat, (tx, 1.2 + lvl * 2.4, 0), (3.0, 2.4, 3.0), yaw=b.R.uniform(-4, 4))
        b.box(WOOD, (tx, 7.35, 0), (3.6, 0.2, 3.6))
        b.spikes(tx, 7.4, 0, 6, spread=1.5)
        b.beam(IRON, (tx - 1.3, 0.6, 1.6), (tx + 1.3, 6.8, 1.6), 0.18); b.beam(IRON, (tx + 1.3, 0.6, 1.6), (tx - 1.3, 6.8, 1.6), 0.18)
    for zz in (-0.9, 0.9):
        b.beam(IRON, (-7, 8.6, zz), (7, 8.6, zz), 0.26)
    for k in range(8):
        xx = -7 + k * 2.0
        b.beam(IRON, (xx, 8.6, -0.9), (xx, 8.6, 0.9), 0.14)
        if k < 7:
            b.beam(IRON, (xx, 8.6, -0.9), (xx + 2.0, 8.6, 0.9), 0.07)
    b.box(RUST, (0, 6.9, 0), (8.0, 2.2, 0.16), roll=2)
    b.box(STRIPES, (0, 5.75, 0), (8.0, 0.2, 0.2), roll=2)
    b.skull((0, 7.0, 0.35), 1.3)
    b.spikes(0, 8.0, 0, 10, spread=3.8, h=0.9)
    b.flag(7.5, 7.4, -1.5, h=3.0, mat=RED); b.flag(-7.5, 7.4, 1.5, h=2.6, mat=TARP)
    b.tyre_stack(-9.3, 1.5, 3); b.tyre_stack(9.4, -1.6, 2)
    b.box(GROUND, (0, -0.25, 0), (20, 0.5, 6))
    return (0.0, 0.0, -3.0), 'Skull Gate'


ASSETS = [
    ('mm_scrap_wall', scrap_wall), ('mm_wall_tower', wall_tower), ('mm_watchtower', watchtower),
    ('mm_shanty', shanty), ('mm_fuel_depot', fuel_depot), ('mm_wreck_yard', wreck_yard),
    ('mm_ruin_block', ruin_block), ('mm_road_wreck', road_wreck), ('mm_totem', totem),
    ('mm_windpump', windpump), ('mm_barricade', barricade), ('mm_skull_gate', scrap_gatehouse),
]


# ------------------------------------------------------------------ files --

def building_ini(name, ped, bbox):
    x, y, z = ped
    return '\r\n'.join([
        '$NAME_STR "%s"' % name,
        '',
        '; Mad Max map kit. A monument: placeable anywhere, no workers, no function.',
        '$TYPE_MONUMENT',
        '$MONUMENT_GOVERNMENT_LOYALTY_RADIUS 0',
        '$MONUMENT_GOVERNMENT_LOYALTY_STRENGTH 0',
        '-------',
        '$COST_WORK SOVIET_CONSTRUCTION_GROUNDWORKS 0.0',
        '$COST_WORK_BUILDING_ALL',
        '$COST_RESOURCE_AUTO ground_asphalt 0.02',
        '------------------',
        '$COST_WORK SOVIET_CONSTRUCTION_SKELETON_CASTING 1.0',
        '$COST_WORK_BUILDING_ALL',
        '$COST_RESOURCE_AUTO wall_concrete 0.4', '$COST_RESOURCE_AUTO wall_steel 0.4',
        '-----------------------',
        '$CONNECTION_PEDESTRIAN',
        '%.2f 0.0 %.2f' % (x, z - 1.0),
        '%.2f 0.0 %.2f' % (x, z + 1.0),
        '',
        'end', ''])


RENDERCONFIG = '''$TYPE_WORKSHOP
 MODEL model.nmf
 MATERIAL ../material/%(n)s.mtl
 MATERIALEMISSIVE ../material/%(n)s_e.mtl
 LIFE 1800.000000
 EXPLOSION_GROUP 0
 DERBIS_FALLING_FX buildingfall1 1.000000
 DERBIS_FALLED_FX buildingfall2 1.400000
 DERBIS_FALLED_SFX collapse
 DERBIS_NUM 6
 DERBIS_FALLING_FX_MAXTIME 3.000000
 DERBIS_SCALE 0.600000
 DERBIS_MESH buildings/buildingwreck1.nmf buildings/buildingwreck.mtl
 END
'''.replace('\n', '\r\n')


def main():
    mmkit.clear_scene()
    os.makedirs(KITDIR, exist_ok=True)
    os.makedirs(PREVIEW, exist_ok=True)
    matdir = os.path.join(KITDIR, 'material')
    os.makedirs(matdir, exist_ok=True)
    for name in MATS + ['tp_black']:
        shutil.copy(os.path.join(TEXDIR, name + '.dds'), os.path.join(matdir, name + '.dds'))
    bmats = mmkit.blender_materials(TEXDIR)
    mmkit.lighting()
    cfg_lines = ['$ITEM_ID %d' % ITEM_ID, '', '$ITEM_TYPE WORKSHOP_ITEMTYPE_BUILDING', '', '$VISIBILITY 2', '']
    summary = []
    for key, fn in ASSETS:
        b = Builder(seed=hash(key) & 0xFFFF)
        ped, title = fn(b)
        shapes, used = b.export_shapes()
        model = nmf.Model()
        model.materials = used
        model.shapes = shapes
        adir = os.path.join(KITDIR, key)
        os.makedirs(adir, exist_ok=True)
        nmf.write(model, os.path.join(adir, 'model.nmf'))
        bbox = mmkit.model_bbox(shapes)
        mmkit.write_bbox_file(os.path.join(adir, 'building.bbox'), shapes)
        mmkit.write_fire_file(os.path.join(adir, 'building.fire'), b.fire)
        mmkit.write_text(os.path.join(adir, 'building.ini'), building_ini(title, ped, bbox))
        mmkit.write_text(os.path.join(adir, 'renderconfig.ini'), RENDERCONFIG % {'n': key})
        mmkit.write_text(os.path.join(matdir, key + '.mtl'), mmkit.mtl_text(used, ''))
        mmkit.write_text(os.path.join(matdir, key + '_e.mtl'), mmkit.mtl_text(used, '', emissive=True))
        cfg_lines.append('$OBJECT_BUILDING %s' % key)
        # preview + icon
        obs = b.preview_objects(bmats, key)
        pos, tgt = mmkit.frame_camera(bbox, azimuth_deg=-38, elevation_deg=26)
        mmkit.render(os.path.join(PREVIEW, key + '.png'), pos, tgt, (900, 620), samples=32)
        pos, tgt = mmkit.frame_camera(bbox, azimuth_deg=-30, elevation_deg=34, fill=1.05)
        mmkit.render(os.path.join(PREVIEW, key + '_icon.png'), pos, tgt, (384, 384), transparent=True, samples=24)
        mmkit.save_scaled_png(os.path.join(PREVIEW, key + '_icon.png'), os.path.join(adir, 'imagegui.png'), 96, 96)
        for ob in obs:
            bpy.data.objects.remove(ob)
        b.free()
        tris = sum(s.nt for s in shapes)
        summary.append('%-16s %-16s tris=%5d nodes=%2d bbox=%s' % (key, title, tris, len(shapes), ['%.1f' % v for v in bbox]))
    cfg_lines += ['', '$ITEM_NAME "Mad Max Map Kit"', '', '$ITEM_DESC "Wasteland decorations: walls, towers, shanties, wrecks, ruins, totems."', '', '$END', '']
    mmkit.write_text(os.path.join(KITDIR, 'workshopconfig.ini'), '\r\n'.join(cfg_lines))
    print('\n'.join(summary))
    print('kit done')


main()
