"""Mad Max vehicles: vanilla meshes with welded-on scrap, plus the skins.

    blender -b --python tools/madmax_vehicles.py -- <texdir> <skindir> <outroot> <previewdir>

Reads <skindir>/manifest.json (from vehicle_skins.py). For every vehicle it
loads the vanilla main.nmf (and the trailer joint for the rig), probes the
body for hood/roof heights, builds add-ons in vehicle space (x right, y up,
z forward), appends them as extra nodes, and writes a complete workshop
vehicle item under <outroot>/<key>/ with one material_N.mtl per skin.
"""
import json
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
SKINDIR = argv[1] if len(argv) > 1 else 'build/vehicles'
OUTROOT = argv[2] if len(argv) > 2 else 'mod/vehicles'
PREVIEW = argv[3] if len(argv) > 3 else 'build/vehicles'
MEDIA = os.environ.get('WRSR_GAME', r'C:\Program Files (x86)\Steam\steamapps\common\SovietRepublic').rstrip('/\\') + '/media_soviet/'
VEH = MEDIA + 'vehicles/'


# ---------------------------------------------------------------- probes ---

class Body:
    """Vanilla mesh measurements, tyres excluded."""

    def __init__(self, model):
        self.pts = []
        for s in model.shapes:
            if s.node_type != 0 or s.name.lower().startswith('tire'):
                continue
            self.pts += [(s.pos[3 * i], s.pos[3 * i + 1], s.pos[3 * i + 2]) for i in range(s.nv)]
        xs = [p[0] for p in self.pts]; ys = [p[1] for p in self.pts]; zs = [p[2] for p in self.pts]
        self.bbox = (min(xs), min(ys), min(zs), max(xs), max(ys), max(zs))
        self.hw = max(abs(self.bbox[0]), abs(self.bbox[3]))

    def top(self, z0, z1, xmax=0.4, pct=1.0):
        """Height of the body's upper surface in a z slice. pct < 1 ignores
        small protrusions (vents, aerials) by taking a percentile."""
        ys = sorted(p[1] for p in self.pts if z0 <= p[2] <= z1 and abs(p[0]) <= xmax)
        if not ys:
            return self.bbox[4]
        return ys[min(len(ys) - 1, int(len(ys) * pct))] if pct < 1.0 else ys[-1]

    def side(self, z0, z1, y0, y1):
        xs = [abs(p[0]) for p in self.pts if z0 <= p[2] <= z1 and y0 <= p[1] <= y1]
        return max(xs) if xs else self.hw


# --------------------------------------------------------------- add-ons ---

def bullbar(b, body, zf, y0=0.35, y1=0.95, w=None):
    w = w or body.side(zf - 1.0, zf, y0, y1) * 0.85
    for x in (-w, w):
        b.rod(IRON, (x, y0, zf), (x, y1, zf), 0.05)
        b.rod(IRON, (x, y0, zf - 0.35), (x, y0, zf), 0.05)
    for y in (y0 + 0.05, (y0 + y1) / 2, y1 - 0.05):
        b.rod(IRON, (-w, y, zf), (w, y, zf), 0.05)
    for k in range(4):
        b.spike(IRON, (-w * 0.75 + k * w * 0.5, (y0 + y1) / 2, zf + 0.02), (0, 0, 1), 0.35, radius=0.035)


def exhaust_stacks(b, x, y0, z, h=1.6, r=0.06):
    for sx in (-x, x):
        b.rod(IRON, (sx, y0, z), (sx, y0 + h, z), r, segs=8)
        b.rod(IRON, (sx, y0 + h, z), (sx, y0 + h + 0.12, z - 0.12), r * 1.15, segs=8)


def roof_cage(b, hw, y, z0, z1, h=0.35, r=0.03):
    for x in (-hw, hw):
        for z in (z0, z1):
            b.rod(IRON, (x, y - 0.05, z), (x, y + h, z), r)
        b.rod(IRON, (x, y + h, z0), (x, y + h, z1), r)
    for z in (z0, z1):
        b.rod(IRON, (-hw, y + h, z), (hw, y + h, z), r)


def side_spikes(b, body, n, ylo, yhi, zlo, zhi, length=0.35):
    R = b.R
    for k in range(n):
        z = zlo + (zhi - zlo) * (k + 0.5) / n
        for sgn in (-1, 1):
            y = R.uniform(ylo, yhi)
            x = body.side(z - 0.2, z + 0.2, y - 0.1, y + 0.1)
            b.spike(IRON, (sgn * (x - 0.02), y, z), (sgn, R.uniform(-0.2, 0.3), R.uniform(-0.2, 0.2)), length * R.uniform(0.8, 1.3), radius=0.04)


def plow(b, body, zf, y0=0.2, h=1.1, w=None, tilt=18):
    w = w or body.hw * 0.95
    b.box(RUST, (0, y0 + h / 2, zf + 0.25), (w * 2, h, 0.08), pitch=-tilt)
    for k in range(5):
        b.spike(IRON, (-w * 0.8 + k * w * 0.4, y0 + h * 0.75, zf + 0.28 + h * 0.3 * math.sin(math.radians(tilt))), (0, 0.35, 1), 0.4, radius=0.04)
    for x in (-w * 0.6, w * 0.6):
        b.rod(IRON, (x, y0 + 0.3, zf - 0.3), (x, y0 + h * 0.5, zf + 0.2), 0.05)


def side_plates(b, body, y0, y1, z0, z1, n=2, mat=RUST):
    for sgn in (-1, 1):
        for k in range(n):
            za = z0 + (z1 - z0) * k / n
            zb = z0 + (z1 - z0) * (k + 1) / n
            x = body.side(za, zb, y0, y1) + 0.03
            b.box(mat, (sgn * x, (y0 + y1) / 2, (za + zb) / 2), (0.05, y1 - y0, (zb - za) - 0.08), yaw=0, pitch=b.R.uniform(-2, 2))
            for r in range(3):
                b.box(IRON, (sgn * (x + 0.02), y0 + (y1 - y0) * (r + 0.5) / 3, za + 0.15), (0.03, 0.06, 0.06))


def interceptor(b, body):
    bb = body.bbox
    zf = bb[5]
    hood_y = body.top(zf - 1.45, zf - 0.95, 0.25, pct=0.9)
    roof_y = body.top(-0.3, 0.6, 0.3, pct=0.97)
    # a fastback: the glass runs to the tail, so the "trunk" is the tail edge
    trunk_y = body.top(bb[2] + 0.05, bb[2] + 0.3, 0.3, pct=0.6)
    # supercharger through the bonnet, well forward of the glass
    zs = zf - 1.2
    b.cyl(IRON, (0, hood_y + 0.08, zs), 0.14, 0.5, segs=10, pitch=90)
    b.box(IRON, (0, hood_y + 0.26, zs + 0.28), (0.46, 0.14, 0.3))
    b.box(RUST, (0, hood_y + 0.34, zs + 0.36), (0.34, 0.06, 0.46), pitch=-8)
    for x in (-0.18, 0.18):
        b.cyl(IRON, (x, hood_y + 0.02, zs - 0.15), 0.09, 0.06, segs=10)
    b.rod(RUST, (0, hood_y + 0.08, zs), (0, hood_y + 0.08, zs - 0.4), 0.06, segs=8)
    # side pipes
    for sgn in (-1, 1):
        x = body.side(-1.2, 0.4, 0.3, 0.5) + 0.06
        for k in range(4):
            b.rod(IRON, (sgn * x, 0.42 - k * 0.02, 0.5 - k * 0.12), (sgn * (x + 0.02), 0.34, -1.5), 0.035, segs=6)
    bullbar(b, body, zf + 0.12, 0.3, 0.75)
    # ducktail spoiler flush with the tail edge
    b.box(IRON, (0, trunk_y + 0.06, bb[2] + 0.18), (1.35, 0.04, 0.42), pitch=-14)
    for x in (-0.55, 0.55):
        b.box(IRON, (x, trunk_y - 0.04, bb[2] + 0.2), (0.05, 0.16, 0.3), pitch=-14)
    b.cyl(RUST, (0.32, trunk_y - 0.12, bb[2] - 0.02), 0.12, 0.5, segs=10, pitch=90)
    b.skull((0, hood_y + 0.1, zf - 0.55), 0.16)


def nux(b, body):
    bb = body.bbox
    zf = bb[5]
    hood_y = body.top(zf - 1.2, zf - 0.5, 0.3, pct=0.97)
    roof_y = body.top(-0.4, 0.5, 0.3, pct=0.97)
    trunk_y = body.top(bb[2] + 0.2, bb[2] + 0.8, 0.3, pct=0.97)
    roof_cage(b, 0.55, roof_y, -0.7, 0.7, h=0.4)
    b.torus(TIRE, (0, roof_y + 0.55, 0.0), 0.36, 0.13, axis='x')
    side_spikes(b, body, 5, 0.55, 0.95, bb[2] + 0.8, zf - 0.8)
    for x in (-0.3, 0.3):
        b.cyl(RUST, (x, trunk_y + 0.05, bb[2] + 0.25), 0.2, 0.9, segs=10, pitch=90)
        b.box(STRIPES, (x, trunk_y + 0.05, bb[2] + 0.7), (0.42, 0.42, 0.08))
    exhaust_stacks(b, 0.5, roof_y - 0.5, -0.9, h=1.0, r=0.05)
    b.skull((0, hood_y + 0.14, zf - 0.35), 0.2)
    bullbar(b, body, zf + 0.1, 0.3, 0.8)
    for x in (-0.4, 0.4):
        b.rod(IRON, (x, 0.45, zf + 0.1), (x + 0.1, 0.1, zf + 0.35), 0.015, segs=4)
    b.box(IRON, (0, hood_y + 0.02, zf - 1.1), (0.7, 0.05, 0.5))
    b.rod(IRON, (0, hood_y + 0.02, zf - 1.1), (0, hood_y + 0.3, zf - 1.1), 0.05, segs=8)


def buzzard(b, body):
    bb = body.bbox
    zf = bb[5]
    roof_y = body.top(-0.5, 0.5, 0.3)
    hood_y = body.top(zf - 1.2, zf - 0.5, 0.3)
    R = b.R
    side_spikes(b, body, 7, 0.35, 1.05, bb[2] + 0.3, zf - 0.3, length=0.45)
    for k in range(8):
        b.spike(IRON, (R.uniform(-0.45, 0.45), roof_y - 0.02, R.uniform(-0.6, 0.6)), (R.uniform(-0.4, 0.4), 1, R.uniform(-0.4, 0.4)), R.uniform(0.35, 0.6), radius=0.04)
    for k in range(6):
        b.spike(IRON, (R.uniform(-0.5, 0.5), R.uniform(0.4, 0.9), bb[2] - 0.02), (R.uniform(-0.3, 0.3), R.uniform(-0.2, 0.3), -1), R.uniform(0.35, 0.55), radius=0.04)
    for k in range(6):
        b.spike(IRON, (R.uniform(-0.5, 0.5), R.uniform(0.35, 0.8), zf + 0.02), (R.uniform(-0.3, 0.3), R.uniform(-0.2, 0.3), 1), R.uniform(0.35, 0.55), radius=0.04)
    roof_cage(b, 0.5, roof_y, -0.55, 0.55, h=0.3)
    plow(b, body, zf + 0.05, 0.25, 0.8, w=body.hw * 0.9, tilt=25)
    b.box(RUST, (0, roof_y - 0.25, bb[2] + 0.35), (0.9, 0.35, 0.05), pitch=-30)
    b.cyl(RUST, (0, roof_y + 0.02, -0.1), 0.16, 0.6, segs=10, pitch=90)


def warrig(b, body):
    bb = body.bbox
    zf = bb[5]
    cab_roof = body.top(zf - 2.2, zf - 0.6, 0.6)
    tank_top = body.top(bb[2] + 1.0, zf - 3.0, 0.6)
    plow(b, body, zf + 0.35, 0.5, 1.5, w=body.hw * 0.98, tilt=20)
    exhaust_stacks(b, body.hw - 0.25, cab_roof - 1.3, zf - 2.5, h=3.0, r=0.09)
    b.skull((0, cab_roof - 0.5, zf + 0.1), 0.4)
    b.spikes(0, cab_roof, zf - 1.4, 5, spread=body.hw * 0.7, h=0.5)
    b.cyl(IRON, (body.hw * 0.5, cab_roof, zf - 1.5), 0.25, 0.4, segs=8, pitch=60)
    b.cyl(GLOW, (body.hw * 0.5, cab_roof + 0.02, zf - 1.5), 0.2, 0.42, segs=8, pitch=60)
    # crow's nest on the tank
    zc = (bb[2] + 1.0 + zf - 3.0) / 2
    b.box(WOOD, (0, tank_top + 0.1, zc), (1.6, 0.08, 1.6))
    for px, pz in ((-0.75, -0.75), (0.75, -0.75), (-0.75, 0.75), (0.75, 0.75)):
        b.rod(IRON, (px, tank_top + 0.1, zc + pz), (px, tank_top + 1.1, zc + pz), 0.03)
    for (a, c) in (((-0.75, -0.75), (0.75, -0.75)), ((0.75, -0.75), (0.75, 0.75)), ((0.75, 0.75), (-0.75, 0.75)), ((-0.75, 0.75), (-0.75, -0.75))):
        b.beam(IRON, (a[0], tank_top + 1.1, zc + a[1]), (c[0], tank_top + 1.1, zc + c[1]), 0.03)
    b.spikes(0, tank_top + 1.1, zc, 4, spread=0.7, h=0.4)
    side_plates(b, body, 0.9, 2.0, bb[2] + 0.6, zf - 3.2, n=2)
    for sgn in (-1, 1):
        for k in range(5):
            z = bb[2] + 1.0 + k * (zf - 4.0 - bb[2]) / 5
            b.spike(IRON, (sgn * (body.side(z - 0.2, z + 0.2, 2.0, 2.6) - 0.02), 2.3, z), (sgn, 0.4, 0), 0.5, radius=0.05)


def warrig_trailer(b, body):
    bb = body.bbox
    top = bb[4]
    R = b.R
    for sgn in (-1, 1):
        for k in range(6):
            z = bb[2] + 0.6 + k * (bb[5] - bb[2] - 1.2) / 5
            b.spike(IRON, (sgn * (body.side(z - 0.2, z + 0.2, top - 1.0, top - 0.2) - 0.02), top - 0.6, z), (sgn, 0.5, 0), 0.5, radius=0.05)
    side_plates(b, body, 0.8, 1.7, bb[2] + 0.6, bb[5] - 0.6, n=3, mat=CORR)
    zr = bb[2] + 0.5
    b.box(WOOD, (0, top - 0.3, zr + 0.6), (2.0, 0.08, 1.2))
    for px, pz in ((-0.95, 0.05), (0.95, 0.05), (-0.95, 1.15), (0.95, 1.15)):
        b.rod(IRON, (px, top - 0.3, zr + pz), (px, top + 0.7, zr + pz), 0.03)
    b.beam(IRON, (-0.95, top + 0.7, zr + 0.05), (0.95, top + 0.7, zr + 0.05), 0.03)
    b.beam(IRON, (-0.95, top + 0.7, zr + 1.15), (0.95, top + 0.7, zr + 1.15), 0.03)
    b.skull((0, top + 0.5, bb[2] - 0.05), 0.4, yaw=180)
    b.spikes(0, top + 0.1, bb[5] - 1.0, 6, spread=0.9, h=0.5)
    for k in range(3):
        b.rod(IRON, (R.uniform(-1.0, 1.0), top - 0.5, R.uniform(bb[2] + 1, bb[5] - 1)), (R.uniform(-1.1, 1.1), 0.6, R.uniform(bb[2] + 1, bb[5] - 1)), 0.015, segs=4)
    b.flag(0.8, top + 0.2, bb[5] - 1.2, h=1.8, mat=RED)


def raider(b, body):
    bb = body.bbox
    zf = bb[5]
    cab_roof = body.top(zf - 1.6, zf - 0.3, 0.5)
    bed_top = body.top(bb[2] + 0.5, zf - 2.2, 0.6)
    bullbar(b, body, zf + 0.15, 0.55, 1.35)
    b.torus(IRON, (0, cab_roof + 0.05, zf - 1.0), 0.45, 0.05, segs=14, rings=6)
    b.rod(IRON, (0, cab_roof + 0.05, zf - 1.0), (0, cab_roof + 0.55, zf - 1.0), 0.05)
    b.rod(IRON, (0, cab_roof + 0.55, zf - 1.0), (0.3, cab_roof + 0.75, zf + 0.1), 0.045, segs=8)
    b.box(IRON, (0, cab_roof + 0.5, zf - 1.15), (0.45, 0.2, 0.35))
    side_plates(b, body, 0.9, 1.9, zf - 1.9, zf - 0.4, n=1)
    b.cyl(IRON, (-body.hw * 0.6, cab_roof + 0.02, zf - 0.6), 0.2, 0.3, segs=8, pitch=70)
    b.cyl(GLOW, (-body.hw * 0.6, cab_roof + 0.04, zf - 0.6), 0.16, 0.32, segs=8, pitch=70)
    roof_cage(b, body.hw * 0.9, bed_top, bb[2] + 0.4, zf - 2.3, h=0.35, r=0.035)
    for k in range(3):
        b.cyl(b.R.choice([RUST, STRIPES, RED]), (-0.6 + k * 0.6, bed_top + 0.35, bb[2] + 1.2), 0.28, 0.85, segs=10, pitch=90)
    b.torus(TIRE, (0.7, bed_top + 0.5, bb[2] + 2.6), 0.5, 0.2, axis='x')
    b.spikes(0, bed_top + 0.3, zf - 2.4, 5, spread=body.hw * 0.8, h=0.45)
    b.skull((0, cab_roof - 0.6, zf + 0.05), 0.3)


def warbus(b, body):
    bb = body.bbox
    zf = bb[5]
    roof = body.top(-2.0, 2.0, 0.5, pct=0.9)
    win_lo, win_hi = roof - 1.6, roof - 0.7
    plow(b, body, zf + 0.3, 0.4, 1.4, w=body.hw * 0.98, tilt=18)
    for sgn in (-1, 1):
        x = body.side(bb[2] + 2, zf - 2, win_lo, win_hi) + 0.05
        for y in (win_lo + 0.15, (win_lo + win_hi) / 2, win_hi - 0.15):
            b.rod(IRON, (sgn * x, y, bb[2] + 1.0), (sgn * x, y, zf - 1.5), 0.025, segs=6)
        z = bb[2] + 1.0
        while z < zf - 1.5:
            b.rod(IRON, (sgn * x, win_lo - 0.1, z), (sgn * x, win_hi + 0.1, z), 0.025, segs=6)
            z += 0.9
    # roof fighting platform on short legs (the roof is crowned)
    L = (zf - bb[2]) * 0.6
    b.box(WOOD, (0, roof + 0.22, 0.0), (body.hw * 1.6, 0.1, L))
    for px, pz in ((-body.hw * 0.8, -L / 2), (body.hw * 0.8, -L / 2), (-body.hw * 0.8, L / 2), (body.hw * 0.8, L / 2),
                   (-body.hw * 0.8, 0), (body.hw * 0.8, 0)):
        b.rod(IRON, (px, body.top(pz - 0.3, pz + 0.3, body.hw, pct=0.5) - 0.1, pz), (px, roof + 0.22, pz), 0.04)
    for px, pz in ((-body.hw * 0.8, -L / 2), (body.hw * 0.8, -L / 2), (-body.hw * 0.8, L / 2), (body.hw * 0.8, L / 2)):
        b.rod(IRON, (px, roof + 0.2, pz), (px, roof + 1.2, pz), 0.04)
    for (a, c) in (((-body.hw * 0.8, -L / 2), (body.hw * 0.8, -L / 2)), ((body.hw * 0.8, -L / 2), (body.hw * 0.8, L / 2)),
                   ((body.hw * 0.8, L / 2), (-body.hw * 0.8, L / 2)), ((-body.hw * 0.8, L / 2), (-body.hw * 0.8, -L / 2))):
        b.beam(IRON, (a[0], roof + 1.2, a[1]), (c[0], roof + 1.2, c[1]), 0.035)
    b.spikes(0, roof + 1.2, 0, 8, spread=L * 0.45, h=0.5)
    b.skull((0, roof - 0.9, zf + 0.15), 0.45)
    exhaust_stacks(b, body.hw - 0.3, roof - 1.0, bb[2] + 0.8, h=1.8, r=0.07)
    for k in range(6):
        b.beam(IRON, (body.hw * 0.5, roof - 2.0 + k * 0.45, bb[2] - 0.05), (body.hw * 0.5 + 0.4, roof - 2.0 + k * 0.45, bb[2] - 0.05), 0.03)
    b.rod(IRON, (body.hw * 0.5, roof - 2.2, bb[2] - 0.05), (body.hw * 0.5, roof + 0.3, bb[2] - 0.05), 0.03)
    b.rod(IRON, (body.hw * 0.5 + 0.4, roof - 2.2, bb[2] - 0.05), (body.hw * 0.5 + 0.4, roof + 0.3, bb[2] - 0.05), 0.03)
    b.flag(-body.hw * 0.7, roof + 1.2, -L / 2, h=2.0, mat=RED)


# ------------------------------------------------------------------ rail ---

def zspikes(b, x, y, z, n, spread=0.8, h=0.7):
    """spikes() scatters along X, which is right for a wall and wrong for a
    vehicle: here the scatter runs along the length (Z)."""
    R = b.R
    for _ in range(n):
        b.cyl(IRON, (x + R.uniform(-0.05, 0.05), y, z + R.uniform(-spread, spread)), 0.05, h * R.uniform(0.7, 1.3),
              segs=4, r2=0.0, pitch=R.uniform(-20, 20), roll=R.uniform(-20, 20), smooth=False)


def roof_platform(b, body, z0, z1, hw, h=1.0, spikes=6, ladder_z=None):
    """Wooden fighting platform on short legs over a crowned roof, railed and spiked."""
    y = body.top(z0, z1, hw, pct=0.97)
    b.box(WOOD, (0, y + 0.22, (z0 + z1) / 2), (hw * 2, 0.1, z1 - z0))
    for px in (-hw * 0.9, hw * 0.9):
        for pz in (z0 + 0.2, (z0 + z1) / 2, z1 - 0.2):
            b.rod(IRON, (px, body.top(pz - 0.3, pz + 0.3, hw, pct=0.5) - 0.1, pz), (px, y + 0.22, pz), 0.04)
    for px in (-hw * 0.9, hw * 0.9):
        for pz in (z0 + 0.2, z1 - 0.2):
            b.rod(IRON, (px, y + 0.2, pz), (px, y + 0.2 + h, pz), 0.04)
        b.beam(IRON, (px, y + 0.2 + h, z0 + 0.2), (px, y + 0.2 + h, z1 - 0.2), 0.035)
    for pz in (z0 + 0.2, z1 - 0.2):
        b.beam(IRON, (-hw * 0.9, y + 0.2 + h, pz), (hw * 0.9, y + 0.2 + h, pz), 0.035)
    zspikes(b, 0, y + 0.2 + h, (z0 + z1) / 2, spikes, spread=(z1 - z0) * 0.45, h=0.5)
    if ladder_z is not None:
        x = body.side(ladder_z - 0.3, ladder_z + 0.3, 0.5, y) + 0.05
        for k in range(int((y - 0.3) / 0.45)):
            b.beam(IRON, (x, 0.3 + k * 0.45, ladder_z), (x + 0.4, 0.3 + k * 0.45, ladder_z), 0.03)
        b.rod(IRON, (x, 0.2, ladder_z), (x, y + 0.3, ladder_z), 0.03); b.rod(IRON, (x + 0.4, 0.2, ladder_z), (x + 0.4, y + 0.3, ladder_z), 0.03)
    return y


def firing_slits(b, body, y, z0, z1, n):
    for sgn in (-1, 1):
        for k in range(n):
            z = z0 + (z1 - z0) * (k + 0.5) / n
            x = body.side(z - 0.3, z + 0.3, y - 0.2, y + 0.2) + 0.02
            b.box(IRON, (sgn * x, y, z), (0.03, 0.14, 0.7))


def warloco(b, body):
    bb = body.bbox
    zf, zb = bb[5], bb[2]
    roof = body.top(-6, 6, 0.8, pct=0.9)
    plow(b, body, zf + 0.3, 0.5, 1.7, w=body.hw * 0.98, tilt=22)
    b.skull((0, 3.4, zf + 0.15), 0.5)
    # armour over the cab glass, a slit left to see out of
    for z0, z1 in ((zf - 3.6, zf - 0.6), (zb + 0.6, zb + 3.6)):
        side_plates(b, body, 2.4, roof - 0.5, z0, z1, n=1)
    b.box(IRON, (0, 3.1, zf + 0.06), (2.4, 1.3, 0.08)); b.box(GLOW, (0, 3.1, zf + 0.12), (1.6, 0.1, 0.02))
    b.box(IRON, (0, 3.1, zb - 0.06), (2.4, 1.3, 0.08))
    roof_cage(b, body.hw * 0.85, roof, zb + 1.0, zf - 1.0, h=0.5, r=0.04)
    zspikes(b, 0, roof + 0.5, 0, 10, spread=6.5, h=0.5)
    exhaust_stacks(b, 0.8, roof - 0.4, -2.0, h=1.9, r=0.12)
    side_spikes(b, body, 8, 1.4, 3.4, zb + 1.5, zf - 1.5, length=0.45)
    b.cyl(IRON, (body.hw * 0.4, roof + 0.05, zf - 2.5), 0.26, 0.4, segs=8, pitch=60)
    b.cyl(GLOW, (body.hw * 0.4, roof + 0.07, zf - 2.5), 0.2, 0.42, segs=8, pitch=60)
    b.flag(-body.hw * 0.7, roof + 0.4, zb + 1.5, h=2.0, mat=RED)
    for k in range(3):
        b.cyl(b.R.choice([RUST, STRIPES]), (body.hw * 0.75 * (1 if k % 2 else -1), 1.9, -5.0 + k * 1.2), 0.28, 0.85, segs=10)


def shunter(b, body):
    bb = body.bbox
    zf, zb = bb[5], bb[2]
    # long hood forward, cab at the back
    hood = body.top(-2, 6, 0.6, pct=0.9)
    cab = body.top(zb + 1, zb + 4, 0.6, pct=0.97)
    plow(b, body, zf + 0.25, 0.5, 1.5, w=body.hw * 0.95, tilt=20)
    b.skull((0, 2.6, zf + 0.15), 0.45)
    roof_cage(b, body.hw * 0.8, cab, zb + 0.8, zb + 4.2, h=0.55, r=0.04)
    zspikes(b, 0, cab + 0.55, zb + 2.5, 5, spread=1.4, h=0.5)
    side_plates(b, body, 2.2, cab - 0.4, zb + 0.8, zb + 4.2, n=1)
    for k in range(4):
        b.cyl(b.R.choice([RUST, STRIPES, RED]), (body.hw * 0.72 * (1 if k % 2 else -1), hood - 1.4, -1.0 + k * 1.6), 0.26, 0.8, segs=10)
    exhaust_stacks(b, 0.35, hood - 0.2, 2.0, h=1.6, r=0.1)
    side_spikes(b, body, 6, 1.2, 2.8, zb + 1, zf - 1, length=0.4)
    b.cyl(IRON, (0, cab + 0.05, zb + 2.0), 0.24, 0.4, segs=8, pitch=60)
    b.cyl(GLOW, (0, cab + 0.07, zb + 2.0), 0.18, 0.42, segs=8, pitch=60)
    b.flag(body.hw * 0.6, hood, zf - 1.5, h=1.8, mat=TARP)


def warflat(b, body):
    bb = body.bbox
    deck = body.top(-6, 6, 0.6, pct=0.5) + 0.05
    L = bb[5] - bb[2]
    # a wreck chained down at the front, a gun nest at the back
    b.car_wreck((0, deck, L * 0.22), 90, 0, RUST)
    for sx in (-1.2, 1.2):
        b.rod(IRON, (sx, deck + 1.0, L * 0.22), (sx * 1.3, deck - 0.4, L * 0.22 + 1.6), 0.025, segs=4)
    for k in range(8):
        a = k * 45.0
        b.blob(TARP, (1.6 * math.cos(math.radians(a)), deck, -L * 0.25 + 1.6 * math.sin(math.radians(a))), (0.8, 0.3, 0.55), jitter=0.15, yaw=a)
    b.cyl(IRON, (0, deck, -L * 0.25), 0.5, 0.9, segs=10)
    b.box(IRON, (0, deck + 1.05, -L * 0.25), (0.5, 0.3, 0.7))
    b.rod(IRON, (0, deck + 1.1, -L * 0.25), (0.15, deck + 1.35, -L * 0.25 + 1.6), 0.05, segs=8)
    for sgn in (-1, 1):
        for k in range(6):
            z = bb[2] + 1.0 + k * (L - 2.0) / 5
            b.spike(IRON, (sgn * (body.hw - 0.05), deck + 0.1, z), (sgn, 0.6, 0), 0.5, radius=0.045)
    b.drum((-1.1, deck, L * 0.02)); b.drum((-0.5, deck, L * 0.05), yaw=40); b.drum((1.0, deck, -L * 0.05), lying=True, yaw=80)
    b.tyre_stack(1.1, L * 0.05, 2)
    b.flag(-body.hw * 0.8, deck, -L * 0.45, h=1.8, mat=RED)


def warhopper(b, body):
    bb = body.bbox
    zf, zb = bb[5], bb[2]
    rim = body.top(-3, 3, 0.4, pct=0.9)
    side_plates(b, body, 1.6, rim - 0.5, zb + 0.6, zf - 0.6, n=2)
    for sgn in (-1, 1):
        for k in range(7):
            z = zb + 0.8 + k * (zf - zb - 1.6) / 6
            x = body.side(z - 0.3, z + 0.3, rim - 0.6, rim)
            b.spike(IRON, (sgn * (x - 0.05), rim - 0.05, z), (sgn * 0.5, 1, 0), 0.55, radius=0.045)
    # lookout at one end
    for px in (-0.6, 0.6):
        b.rod(IRON, (px, rim - 1.5, zb + 0.4), (px, rim + 1.6, zb + 0.4), 0.05)
    b.box(WOOD, (0, rim + 0.3, zb + 0.9), (1.6, 0.08, 1.2))
    b.beam(IRON, (-0.6, rim + 1.6, zb + 0.4), (0.6, rim + 1.6, zb + 0.4), 0.03)
    b.skull((0, rim - 0.2, zf + 0.12), 0.45)
    b.flag(0.7, rim + 0.3, zb + 1.2, h=1.6, mat=TARP)


def wartank(b, body):
    bb = body.bbox
    zf, zb = bb[5], bb[2]
    top = body.top(-2, 2, 0.4, pct=0.97)
    # catwalk cage along the top of the tank
    for px in (-0.7, 0.7):
        for z in (zb + 1.5, 0, zf - 1.5):
            b.rod(IRON, (px, top - 0.3, z), (px, top + 0.9, z), 0.035)
        b.beam(IRON, (px, top + 0.9, zb + 1.5), (px, top + 0.9, zf - 1.5), 0.03)
    b.box(WOOD, (0, top + 0.02, 0), (1.3, 0.06, zf - zb - 3.0))
    zspikes(b, 0, top + 0.9, 0, 6, spread=(zf - zb) * 0.35, h=0.45)
    # the tank's end caps, skull forward
    b.skull((0, top - 1.4, zf - 0.4), 0.6)
    b.skull((0, top - 1.4, zb + 0.4), 0.45, yaw=180)
    for sgn in (-1, 1):
        for k in range(5):
            z = zb + 1.2 + k * (zf - zb - 2.4) / 4
            x = body.side(z - 0.3, z + 0.3, top - 2.2, top - 1.2)
            b.spike(IRON, (sgn * (x - 0.03), top - 1.7, z), (sgn, 0.3, 0), 0.4, radius=0.04)
    b.drum((0.9, 1.3, zf - 0.6), yaw=20); b.drum((-0.9, 1.3, zb + 0.6), yaw=60)
    b.flag(0.8, top + 0.9, zf - 1.5, h=1.6, mat=RED)


def warbox(b, body):
    bb = body.bbox
    zf, zb = bb[5], bb[2]
    roof = roof_platform(b, body, zb + 2.0, zf - 2.0, body.hw * 0.85, h=1.0, spikes=8, ladder_z=zb + 1.0)
    side_plates(b, body, 1.4, 3.0, zb + 0.6, zf - 0.6, n=3, mat=RUST)
    firing_slits(b, body, 2.6, zb + 1.0, zf - 1.0, 5)
    b.rod(IRON, (body.hw * 0.5, roof - 0.5, zb + 2.5), (body.hw * 0.5, roof + 1.6, zb + 2.5), 0.09, segs=8)
    b.cyl(IRON, (body.hw * 0.5, roof + 1.6, zb + 2.5), 0.16, 0.2, segs=8, r2=0.05)
    b.skull((0, 2.4, zf + 0.12), 0.5)
    b.flag(-body.hw * 0.7, roof + 1.2, zf - 2.2, h=1.6, mat=RED)


def prisoncar(b, body):
    bb = body.bbox
    zf, zb = bb[5], bb[2]
    roof = body.top(-8, 8, 0.6, pct=0.9)
    win_lo, win_hi = roof - 2.0, roof - 1.0
    for sgn in (-1, 1):
        x = body.side(zb + 2, zf - 2, win_lo, win_hi) + 0.05
        for y in (win_lo + 0.15, (win_lo + win_hi) / 2, win_hi - 0.15):
            b.rod(IRON, (sgn * x, y, zb + 1.5), (sgn * x, y, zf - 1.5), 0.025, segs=6)
        z = zb + 1.5
        while z < zf - 1.5:
            b.rod(IRON, (sgn * x, win_lo - 0.1, z), (sgn * x, win_hi + 0.1, z), 0.025, segs=6)
            z += 0.9
    roof_platform(b, body, -4.0, 4.0, body.hw * 0.8, h=1.0, spikes=6)
    side_plates(b, body, 1.2, roof - 2.3, zb + 0.5, zb + 3.5, n=1); side_plates(b, body, 1.2, roof - 2.3, zf - 3.5, zf - 0.5, n=1)
    b.box(IRON, (0, 2.6, zf + 0.06), (2.6, 2.4, 0.08)); b.box(IRON, (0, 2.6, zb - 0.06), (2.6, 2.4, 0.08))
    b.skull((0, 3.2, zf + 0.15), 0.5)
    side_spikes(b, body, 6, 1.0, 1.6, zb + 2, zf - 2, length=0.35)
    b.flag(body.hw * 0.7, roof + 1.2, zb + 4.5, h=1.6, mat=TARP)


# ----------------------------------------------------------------- ships ---

def gunwale_spikes(b, body, y, z0, z1, n, length=0.6):
    for sgn in (-1, 1):
        for k in range(n):
            z = z0 + (z1 - z0) * (k + 0.5) / n
            x = body.side(z - 0.5, z + 0.5, y - 0.4, y + 0.4)
            b.spike(IRON, (sgn * (x - 0.05), y, z), (sgn, 0.35, 0), length, radius=0.05)


def bow_ram(b, body, zf, y0, h, w, tilt=15):
    b.box(RUST, (0, y0 + h / 2, zf + 0.3), (w, h, 0.12), pitch=-tilt)
    for k in range(5):
        b.spike(IRON, (-w * 0.4 + k * w * 0.2, y0 + h * 0.7, zf + 0.35), (0, 0.3, 1), 0.7, radius=0.06)
    b.spike(IRON, (0, y0 + h * 0.35, zf + 0.35), (0, 0.05, 1), 2.5, radius=0.14, segs=6)


def crow_nest(b, x, y, z, size=1.4, h=1.1):
    b.box(WOOD, (x, y, z), (size, 0.08, size))
    for px, pz in ((-size / 2, -size / 2), (size / 2, -size / 2), (-size / 2, size / 2), (size / 2, size / 2)):
        b.rod(IRON, (x + px, y, z + pz), (x + px, y + h, z + pz), 0.03)
    for (a, c) in (((-1, -1), (1, -1)), ((1, -1), (1, 1)), ((1, 1), (-1, 1)), ((-1, 1), (-1, -1))):
        b.beam(IRON, (x + a[0] * size / 2, y + h, z + a[1] * size / 2), (x + c[0] * size / 2, y + h, z + c[1] * size / 2), 0.03)
    zspikes(b, x, y + h, z, 4, spread=size * 0.4, h=0.4)


def rustbarge(b, body):
    bb = body.bbox
    zf, zb = bb[5], bb[2]
    gun = body.top(-8, 8, body.hw * 0.9, pct=0.4)          # gunwale height amidships
    wheel = body.top(zb + 1.5, zb + 8.0, 1.5, pct=0.97)     # wheelhouse top, aft
    bow_ram(b, body, zf - 0.6, 0.6, 2.6, body.hw * 1.3, tilt=18)
    gunwale_spikes(b, body, gun + 0.2, zb + 9, zf - 4, 8)
    roof_cage(b, 1.8, wheel, zb + 2.0, zb + 7.5, h=0.5, r=0.04)
    zspikes(b, 0, wheel + 0.5, zb + 4.5, 5, spread=2.2, h=0.5)
    for sgn in (-1, 1):
        for k in range(4):
            z = zb + 8 + k * (zf - zb - 12) / 3
            x = body.side(z - 0.5, z + 0.5, 0.0, 1.5) + 0.05
            b.torus(TIRE, (sgn * x, 0.9, z), 0.55, 0.2, axis='x')
    b.skull((0, gun + 1.0, zf - 1.2), 0.7)
    b.rod(IRON, (0, wheel, zb + 4.5), (0, wheel + 5.0, zb + 4.5), 0.06)
    b.flag(0, wheel + 3.0, zb + 4.5, h=2.0, mat=RED)
    b.cyl(IRON, (1.2, wheel + 0.05, zb + 6.5), 0.3, 0.5, segs=8, pitch=60); b.cyl(GLOW, (1.2, wheel + 0.07, zb + 6.5), 0.24, 0.52, segs=8, pitch=60)
    for k in range(5):
        b.drum((-2.5 + k * 1.2, gun - 0.9, 2.0 + (k % 2) * 1.0), yaw=b.R.uniform(0, 360))
    b.blob(IRON, (1.5, gun - 1.0, 8.0), (3.0, 1.2, 2.6), jitter=0.3)


def guzzotanker(b, body):
    bb = body.bbox
    zf, zb = bb[5], bb[2]
    deck = body.top(-20, 20, body.hw * 0.5, pct=0.35)
    bridge = body.top(zb + 3, zb + 16, 2.0, pct=0.97)
    b.skull((0, deck + 2.5, zf - 3.0), 1.8)
    for k in range(9):
        b.spike(IRON, (-4.0 + k * 1.0, deck + 1.2, zf - 1.0 - abs(4 - k) * 0.9), (0, 0.4, 1), 2.0, radius=0.12, segs=6)
    gunwale_spikes(b, body, deck + 0.6, zb + 18, zf - 8, 14, length=0.9)
    side_plates(b, body, deck - 3.5, deck - 0.5, zb + 18, zf - 10, n=6, mat=CORR)
    crow_nest(b, 0, bridge + 0.1, zb + 9.5, size=3.0, h=1.4)
    b.rod(IRON, (0, bridge, zb + 9.5), (0, bridge + 9.0, zb + 9.5), 0.12, segs=8)
    crow_nest(b, 0, bridge + 6.0, zb + 9.5, size=1.6, h=1.0)
    b.flag(0, bridge + 8.0, zb + 9.5, h=3.0, mat=RED)
    for sgn in (-1, 1):
        b.cyl(IRON, (sgn * 4.0, bridge + 0.1, zb + 6.0), 0.5, 0.8, segs=10, pitch=60); b.cyl(GLOW, (sgn * 4.0, bridge + 0.12, zb + 6.0), 0.4, 0.82, segs=10, pitch=60)
    # a cage catwalk down the deck pipes
    for px in (-1.6, 1.6):
        for z in range(int(zb + 18), int(zf - 8), 8):
            b.rod(IRON, (px, deck, z), (px, deck + 2.2, z), 0.05)
        b.beam(IRON, (px, deck + 2.2, zb + 18), (px, deck + 2.2, zf - 8), 0.05)
    zspikes(b, 0, deck + 2.2, 0, 12, spread=(zf - zb) * 0.3, h=0.6)
    for k in range(6):
        b.drum((b.R.uniform(-3, 3), deck, b.R.uniform(zb + 20, zf - 12)), yaw=b.R.uniform(0, 360))


def raidership(b, body):
    bb = body.bbox
    zf, zb = bb[5], bb[2]
    deck = body.top(-15, 15, body.hw * 0.5, pct=0.35)
    bridge = body.top(zb + 3, zb + 14, 2.0, pct=0.97)
    b.skull((0, deck + 3.0, zf - 4.0), 1.6)
    for k in range(7):
        b.spike(IRON, (-3.0 + k * 1.0, deck + 1.0, zf - 1.5 - abs(3 - k) * 1.0), (0, 0.4, 1), 2.2, radius=0.12, segs=6)
    gunwale_spikes(b, body, deck + 0.6, zb + 16, zf - 8, 12, length=0.9)
    side_plates(b, body, deck - 3.0, deck - 0.4, zb + 16, zf - 9, n=5, mat=RUST)
    # watchtower amidships
    tx, tz = 0.0, 5.0
    for px, pz in ((-2.0, -2.0), (2.0, -2.0), (-2.0, 2.0), (2.0, 2.0)):
        b.rod(IRON, (tx + px, deck, tz + pz), (tx + px * 0.6, deck + 12.0, tz + pz * 0.6), 0.14, segs=8)
    for hh in (3.0, 6.0, 9.0):
        s = 2.0 * (1 - 0.4 * hh / 12.0)
        for (a, c) in (((-1, -1), (1, -1)), ((1, -1), (1, 1)), ((1, 1), (-1, 1)), ((-1, 1), (-1, -1))):
            b.beam(IRON, (tx + a[0] * s, deck + hh, tz + a[1] * s), (tx + c[0] * s, deck + hh, tz + c[1] * s), 0.08)
    crow_nest(b, tx, deck + 12.1, tz, size=3.4, h=1.3)
    b.cyl(CORR, (tx, deck + 13.4, tz), 2.6, 1.4, segs=4, r2=0.05, yaw=45, smooth=False)
    b.flag(tx - 1.4, deck + 13.4, tz + 1.4, h=3.0, mat=RED)
    crow_nest(b, 0, bridge + 0.1, zb + 8.0, size=3.0, h=1.4)
    for sgn in (-1, 1):
        b.cyl(IRON, (sgn * 3.5, bridge + 0.1, zb + 5.0), 0.5, 0.8, segs=10, pitch=60); b.cyl(GLOW, (sgn * 3.5, bridge + 0.12, zb + 5.0), 0.4, 0.82, segs=10, pitch=60)
    for k in range(4):
        b.car_wreck((b.R.uniform(-4, 4), deck, zf - 14 - k * 7), b.R.uniform(0, 180), 0, b.R.choice([RUST, RED, IRON]))
    for k in range(8):
        b.drum((b.R.uniform(-5, 5), deck, b.R.uniform(zb + 18, zf - 10)), yaw=b.R.uniform(0, 360))


def skimmer(b, body):
    bb = body.bbox
    zf, zb = bb[5], bb[2]
    roof = body.top(-6, 4, 1.0, pct=0.9)
    deck = body.top(-6, 6, body.hw * 0.7, pct=0.4)
    bow_ram(b, body, zf - 0.4, deck - 0.4, 1.6, body.hw * 0.9, tilt=25)
    gunwale_spikes(b, body, deck + 0.3, zb + 4, zf - 3, 8, length=0.6)
    roof_cage(b, body.hw * 0.6, roof, zb + 6, zf - 6, h=0.45, r=0.04)
    zspikes(b, 0, roof + 0.45, -1.0, 8, spread=5.0, h=0.5)
    exhaust_stacks(b, body.hw * 0.5, roof - 1.0, zb + 2.5, h=2.2, r=0.14)
    b.skull((0, deck + 0.9, zf - 2.0), 0.6)
    b.cyl(IRON, (0, roof + 0.05, zf - 6.5), 0.3, 0.5, segs=8, pitch=60); b.cyl(GLOW, (0, roof + 0.07, zf - 6.5), 0.24, 0.52, segs=8, pitch=60)
    b.flag(-body.hw * 0.5, roof + 0.4, zb + 3.0, h=1.8, mat=RED)
    b.flag(body.hw * 0.5, roof + 0.4, zb + 3.0, h=1.5, mat=TARP)


def geiger(b, body):
    """Police VAZ: roof rack with a Geiger dish and whip antenna, a light bar, bull bar, counter box on the bonnet."""
    bb = body.bbox
    zf = bb[5]
    roof_y = body.top(-0.6, 0.6, 0.3, pct=0.98)
    hood_y = body.top(zf - 1.0, zf - 0.4, 0.3, pct=0.98)
    roof_cage(b, 0.55, roof_y, -0.7, 0.7, h=0.25)
    b.box(RED, (0, roof_y + 0.32, 0.1), (0.9, 0.14, 0.22)); b.box(GLOW, (0, roof_y + 0.32, 0.1), (0.5, 0.16, 0.24))
    b.rod(IRON, (0.35, roof_y + 0.25, -0.5), (0.35, roof_y + 1.0, -0.5), 0.03)
    b.cyl(IRON, (0.35, roof_y + 1.0, -0.5), 0.32, 0.12, segs=12, r2=0.05, pitch=-35, yaw=20)
    b.rod(IRON, (-0.4, roof_y + 0.25, -0.6), (-0.55, roof_y + 1.6, -0.9), 0.015, segs=4)
    b.box(STRIPES, (0, hood_y + 0.05, zf - 0.7), (0.5, 0.12, 0.35)); b.box(GLOW, (0, hood_y + 0.12, zf - 0.7), (0.3, 0.02, 0.2))
    bullbar(b, body, zf + 0.05, 0.3, 0.75)
    side_plates(b, body, 0.35, 0.8, bb[2] + 0.4, zf - 0.6, n=1, mat=STRIPES)
    b.box(RUST, (0, roof_y - 0.2, bb[2] + 0.15), (0.6, 0.25, 0.25))


def quarantine(b, body):
    """Prison bus: barred windows, a roof tank with a trefoil, hazard stripes, a plow, a rear ladder."""
    bb = body.bbox
    zf = bb[5]
    roof_y = body.top(-1.0, 1.0, 0.6, pct=0.98)
    win_lo, win_hi = roof_y - 1.4, roof_y - 0.35
    for sgn in (-1, 1):
        n = 9
        for k in range(n):
            z = bb[2] + 0.8 + k * (zf - 1.6 - bb[2]) / (n - 1)
            x = sgn * (body.side(z - 0.2, z + 0.2, win_lo, win_hi) + 0.03)
            b.rod(IRON, (x, win_lo, z), (x, win_hi, z), 0.02, segs=4)
        x = sgn * (body.side(bb[2] + 0.8, zf - 1.6, win_lo, win_hi) + 0.05)
        b.beam(IRON, (x, (win_lo + win_hi) / 2, bb[2] + 0.8), (x, (win_lo + win_hi) / 2, zf - 1.6), 0.02)
    side_plates(b, body, 0.3, 0.7, bb[2] + 0.5, zf - 0.8, n=2, mat=STRIPES)
    b.cyl(RUST, (0, roof_y + 0.35, -0.5), 0.55, 2.4, segs=12, pitch=90)
    b.box(RED, (0, roof_y + 0.95, -0.5), (0.7, 0.1, 0.7)); b.cyl(GLOW, (0, roof_y + 1.0, -0.5), 0.2, 0.06, segs=10)
    b.box(GLOW, (0.3, roof_y + 0.9, 1.4), (0.3, 0.16, 0.3)); b.box(RED, (-0.3, roof_y + 0.9, 1.4), (0.3, 0.16, 0.3))
    plow(b, body, zf + 0.1, 0.3, 1.0, w=body.hw * 0.95, tilt=22)
    b.rod(IRON, (body.hw * 0.6, 0.5, bb[2] - 0.05), (body.hw * 0.6, roof_y, bb[2] - 0.05), 0.03)
    b.rod(IRON, (body.hw * 0.6 - 0.35, 0.5, bb[2] - 0.05), (body.hw * 0.6 - 0.35, roof_y, bb[2] - 0.05), 0.03)
    for k in range(6):
        y = 0.7 + k * (roof_y - 0.9) / 5
        b.beam(IRON, (body.hw * 0.6 - 0.35, y, bb[2] - 0.05), (body.hw * 0.6, y, bb[2] - 0.05), 0.02)


ADDONS = {'geiger': geiger, 'quarantine': quarantine, 'interceptor': interceptor, 'nux': nux, 'buzzard': buzzard, 'warrig': warrig, 'raider': raider, 'warbus': warbus,
          'warloco': warloco, 'shunter': shunter, 'warflat': warflat, 'warhopper': warhopper, 'wartank': wartank, 'warbox': warbox, 'prisoncar': prisoncar,
          'rustbarge': rustbarge, 'guzzotanker': guzzotanker, 'raidership': raidership, 'skimmer': skimmer}
TRAILER_ADDONS = {'warrig': warrig_trailer}


# ----------------------------------------------------------------- files ---

def mtl_block(name, tex, extra):
    lines = ['$SUBMATERIAL %s' % name]
    for slot in sorted(tex):
        kind, path = tex[slot]
        lines.append('$%s %d %s' % (kind, slot, path))
    lines += extra if extra else ['$DIFFUSECOLOR 0.75 0.75 0.75 1.0', '$SPECULARCOLOR 0.3 0.3 0.3 1.0',
                                   '$AMBIENTCOLOR 0.7 0.7 0.7 1.0', '$SPECULARPOWER 2.0']
    lines.append('')
    return lines


def write_materials(itemdir, man, used_kit):
    for vi, variant in enumerate(man['variants']):
        lines = []
        for sub in man['subs']:
            tex = {int(k): tuple(v) for k, v in sub['tex'].items()}
            if variant in sub['skins']:
                tex[0] = ('TEXTURE_MTL', sub['skins'][variant])
            lines += mtl_block(sub['name'], tex, sub['extra'])
        for name in used_kit:
            lines += mtl_block(name, {0: ('TEXTURE_MTL', name + '.dds'), 1: ('TEXTURE', 'buildings/blankspecular.dds'), 2: ('TEXTURE', 'buildings/blankbump.dds')}, None)
        lines += ['$END', '']
        fn = 'material.mtl' if vi == 0 else 'material_%d.mtl' % vi
        mmkit.write_text(os.path.join(itemdir, fn), '\r\n'.join(lines))


def write_script(itemdir, man, src_folder, key):
    src = open(os.path.join(src_folder, 'script.ini'), encoding='utf-8', errors='ignore').read()
    out = []
    for raw in src.splitlines():
        line = raw.strip()
        if line.startswith('$NAME ') or line.startswith('$NAME\t'):
            out.append('$NAME_STR "%s"' % man['name'])
            continue
        if line.startswith('$DESCRIPTION'):
            out.append('$DESCRIPTION_STR "%s"' % man['desc'])
            continue
        if line.startswith('$FAMILY'):
            continue
        if line.startswith('$AVAILABLE'):
            out.append('$AVAILABLE 1950 3000')
            continue
        if line.startswith('$JOINT'):
            parts = line.split()
            out.append('$JOINT joint.nmf %s' % ' '.join(parts[2:]))
            continue
        if line.startswith('$SKILL_POLICE') and not man.get('keep_skill'):
            continue
        out.append(raw.rstrip())
    mmkit.write_text(os.path.join(itemdir, 'script.ini'), '\r\n'.join(out) + '\r\n')


def merge(vanilla, addon_shapes, addon_used, used_all, mtl_names):
    """Vanilla nodes + add-on nodes over ONE material list: the .mtl's
    submaterials in order, then every kit material the item uses.

    Vanilla subsets are remapped by material name; a vanilla name the .mtl
    does not carry (the M21's 'wire_087225087' vs 'lambert1') maps by index,
    which is what the engine itself falls back to."""
    base = list(mtl_names)
    remap = {}
    for i, n in enumerate(vanilla.materials):
        if n in base:
            remap[i] = base.index(n)
        elif i < len(base):
            remap[i] = i
        else:
            base.append(n)
            remap[i] = len(base) - 1
    model = nmf.Model()
    model.magic = vanilla.magic
    model.materials = base + used_all
    model.shapes = []
    for s in vanilla.shapes:
        s.subsets = [(f, c, remap.get(m, m)) for f, c, m in s.subsets]
        model.shapes.append(s)
    for s in addon_shapes:
        s.subsets = [(f, c, len(base) + used_all.index(addon_used[m])) for f, c, m in s.subsets]
        model.shapes.append(s)
    return model


def preview_materials(man, skindir, variant, kit_bmats):
    """material index -> Blender material for a given variant."""
    subs = man['subs']

    def lookup(mi):
        if mi < len(subs):
            sub = subs[mi]
            skin = sub['skins'].get(variant)
            if skin:
                return mmkit.image_material('veh_%s_%s' % (sub['name'], variant), os.path.join(skindir, skin.replace('.dds', '.png')))
            return kit_bmats[IRON]
        return kit_bmats[mi - len(subs)]
    return lookup


ONLY = set(k for k in os.environ.get('MM_ONLY', '').split(',') if k)


def main():
    mmkit.clear_scene()
    allm = json.load(open(os.path.join(SKINDIR, 'manifest.json')))
    kit_bmats = mmkit.blender_materials(TEXDIR)
    mmkit.lighting(sun_energy=3.5)
    summary = []
    for key, man in allm.items():
        if ONLY and key not in ONLY:
            continue
        src_folder = os.path.join(MEDIA, man.get('base', 'vehicles'), man['src'])
        vanilla = nmf.read(os.path.join(src_folder, 'main.nmf'))
        body = Body(vanilla)
        mtl_names = [s['name'] for s in man['subs']]
        b = Builder(seed=hash(key) & 0xFFFF)
        ADDONS[key](b, body)
        shapes, used_kit = b.export_shapes(prefix='mm_')
        jshapes, jused, vj, bj = [], [], None, None
        if man.get('joint'):
            vj = nmf.read(os.path.join(src_folder, 'joint.nmf'))
            bj = Builder(seed=7)
            TRAILER_ADDONS[key](bj, Body(vj))
            jshapes, jused = bj.export_shapes(prefix='mmj_')
        used_all = list(used_kit) + [n for n in jused if n not in used_kit]
        model = merge(vanilla, shapes, used_kit, used_all, mtl_names)
        itemdir = os.path.join(OUTROOT, key, key)
        os.makedirs(itemdir, exist_ok=True)
        nmf.write(model, os.path.join(itemdir, 'main.nmf'))
        bbox = mmkit.model_bbox(model.shapes)
        trailer_model = None
        if vj is not None:
            trailer_model = merge(vj, jshapes, jused, used_all, mtl_names)
            nmf.write(trailer_model, os.path.join(itemdir, 'joint.nmf'))
        with open(os.path.join(itemdir, 'bbox.bin'), 'wb') as f:
            import struct
            f.write(struct.pack('<6f', *bbox))
        for name in used_all:
            shutil.copy(os.path.join(TEXDIR, name + '.dds'), os.path.join(itemdir, name + '.dds'))
        for sub in man['subs']:
            for variant, fn in sub['skins'].items():
                shutil.copy(os.path.join(SKINDIR, key, fn), os.path.join(itemdir, fn))
        write_materials(itemdir, man, used_all)
        write_script(itemdir, man, src_folder, key)
        mmkit.write_text(os.path.join(OUTROOT, key, 'workshopconfig.ini'), '\r\n'.join([
            '$ITEM_ID %d' % man['item'], '', '$ITEM_TYPE WORKSHOP_ITEMTYPE_VEHICLE', '', '$VISIBILITY 2',
            '$OBJECT_VEHICLE %s' % key, '', '$ITEM_NAME "%s"' % man['name'], '', '$ITEM_DESC "%s"' % man['desc'], '', '$END', '']))
        # ---- previews per variant
        for vi, variant in enumerate(man['variants']):
            lookup = preview_materials(man, os.path.join(SKINDIR, key), variant, kit_bmats)
            obs = mmkit.add_nmf_object(model, 'veh', lookup)
            if trailer_model is not None:
                tobs = mmkit.add_nmf_object(trailer_model, 'trl', lookup)
                tb = mmkit.model_bbox(trailer_model.shapes)
                # hang the trailer off the back: its nose 1.5 m over the tractor's tail
                dz = (bbox[2] + 1.5) - tb[5]
                for ob in tobs:
                    ob.location.y = -dz   # game +z is Blender -y
                obs += tobs
                fb = (min(bbox[0], tb[0]), min(bbox[1], tb[1]), tb[2] + dz, max(bbox[3], tb[3]), max(bbox[4], tb[4]), bbox[5])
            else:
                fb = bbox
            pos, tgt = mmkit.frame_camera(fb, azimuth_deg=-38, elevation_deg=22, fill=1.0)
            pfx = os.path.join(PREVIEW, key, 'preview' + ('' if vi == 0 else '_%d' % vi))
            mmkit.render(pfx + '.png', pos, tgt, (512, 512), fov=38, transparent=True, samples=32)
            L = fb[5] - fb[2]
            cz = (fb[2] + fb[5]) / 2; cy = (fb[1] + fb[4]) / 2
            mmkit.render(pfx + '_side.png', (L * 3, cy, cz), (0, cy, cz), (512, 256), transparent=True, samples=32, ortho=L * 1.15)
            if vi == 0:
                pos, tgt = mmkit.frame_camera(fb, azimuth_deg=-42, elevation_deg=18, fill=0.95)
                mmkit.render(os.path.join(PREVIEW, key, 'beauty.png'), pos, tgt, (1100, 700), fov=36, samples=48)
            for ob in obs:
                bpy.data.objects.remove(ob)
        b.free()
        if bj is not None:
            bj.free()
        tris = sum(s.nt for s in shapes) + sum(s.nt for s in jshapes)
        summary.append('%-12s %-24s addon tris=%5d kit mats=%s bbox=%s' % (key, man['name'], tris, used_all, ['%.1f' % v for v in bbox]))
    print('\n'.join(summary))
    print('vehicles done')


main()
