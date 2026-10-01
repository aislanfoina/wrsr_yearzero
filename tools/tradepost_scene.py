"""Build the Survival Trade Post - Apocalypseburg / Mad Max style - and export it.

    blender -b --python tools/tradepost_scene.py -- <texdir> <builddir> <previewdir>

Everything is built in GAME coordinates (X east, Y up, Z south toward the
road) and converted to Blender's Z-up on placement; the export applies
3DIVISION's own -90 degrees-about-X convention, so what the game shows is
exactly what the preview render shows.

Footprint from building.ini: x -26..24, z -15..15, the road enters at +Z
around x = 0.4, and the two truck bays run along Z at x = -3.2 and 4.2.
"""
import math
import os
import random
import shutil
import sys

import bpy
import bmesh
from mathutils import Matrix, Vector

TOOLS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, TOOLS)
import nmf  # noqa: E402

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
TEXDIR = argv[0] if len(argv) > 0 else 'build/textures'
OUTDIR = argv[1] if len(argv) > 1 else 'mod/buildings/trade_post/trade_post'
PREVIEW = argv[2] if len(argv) > 2 else 'build'

R = random.Random(20260918)

# --------------------------------------------------------------- materials --

MATS = ['tp_rust', 'tp_corrugated', 'tp_tarp', 'tp_wood', 'tp_ground', 'tp_tire',
        'tp_stripes', 'tp_redpaint', 'tp_iron', 'tp_gravel', 'tp_brick', 'tp_cement', 'tp_glow']
# metres covered by one repeat of the texture
TILE = {'tp_rust': 4.0, 'tp_corrugated': 2.2, 'tp_tarp': 2.5, 'tp_wood': 2.0, 'tp_ground': 9.0,
        'tp_tire': 0.6, 'tp_stripes': 1.2, 'tp_redpaint': 2.5, 'tp_iron': 2.0, 'tp_gravel': 3.0,
        'tp_brick': 1.6, 'tp_cement': 1.2, 'tp_glow': 1.0}
RUST, CORR, TARP, WOOD, GROUND, TIRE, STRIPES, RED, IRON, GRAVEL, BRICK, CEMENT, GLOW = range(13)
WALLMATS = [CORR] * 5 + [RUST] * 3 + [WOOD] * 2
JUNKMATS = [RUST, RED, IRON, CORR]

master = {i: bmesh.new() for i in range(len(MATS))}
fire_points = []   # game coords


# ------------------------------------------------------------- transforms --

def G(x, y, z):
    """Game (x, up, z) -> Blender (x, -z, up)."""
    return Vector((x, -z, y))


def rot(pitch=0.0, yaw=0.0, roll=0.0):
    """Game-axis rotations in degrees -> Blender matrix.
    yaw about game Y (= Blender Z), pitch about game X (= Blender X),
    roll about game Z (= Blender -Y)."""
    return (Matrix.Rotation(math.radians(yaw), 4, 'Z')
            @ Matrix.Rotation(math.radians(pitch), 4, 'X')
            @ Matrix.Rotation(math.radians(-roll), 4, 'Y'))


def _finish(bm, ret, mat, smooth):
    faces = set()
    for v in ret['verts']:
        for f in v.link_faces:
            faces.add(f)
    for f in faces:
        f.material_index = mat
        f.smooth = smooth
    return faces


# ------------------------------------------------------------- primitives --

def box(mat, center, size, yaw=0.0, pitch=0.0, roll=0.0, smooth=False):
    """Axis box in game units: size = (x extent, height, z extent)."""
    bm = master[mat]
    M = Matrix.Translation(G(*center)) @ rot(pitch, yaw, roll) @ Matrix.Diagonal((size[0], size[2], size[1], 1.0))
    ret = bmesh.ops.create_cube(bm, size=1.0, matrix=M)
    _finish(bm, ret, mat, smooth)


def cyl(mat, base, radius, height, segs=12, r2=None, yaw=0.0, pitch=0.0, roll=0.0, smooth=True, caps=True):
    """Vertical cylinder (or cone when r2 differs) standing on its base point;
    tilt it with pitch/roll."""
    bm = master[mat]
    M = (Matrix.Translation(G(*base)) @ rot(pitch, yaw, roll) @ Matrix.Translation((0, 0, height / 2.0)))
    ret = bmesh.ops.create_cone(bm, cap_ends=caps, cap_tris=False, segments=segs,
                                radius1=radius, radius2=radius if r2 is None else r2, depth=height, matrix=M)
    faces = _finish(bm, ret, mat, smooth)
    # caps flat, sides smooth
    for f in faces:
        if len(f.verts) == segs:
            f.smooth = False


def beam(mat, p0, p1, w, h=None, roll=0.0):
    """Box spanning two game points, w wide, h tall (defaults to w)."""
    h = w if h is None else h
    a, b = G(*p0), G(*p1)
    d = b - a
    L = d.length
    if L < 1e-6:
        return
    q = d.normalized().to_track_quat('X', 'Z')
    M = (Matrix.Translation((a + b) / 2.0) @ q.to_matrix().to_4x4()
         @ Matrix.Rotation(math.radians(roll), 4, 'X') @ Matrix.Diagonal((L, w, h, 1.0)))
    bm = master[mat]
    ret = bmesh.ops.create_cube(bm, size=1.0, matrix=M)
    _finish(bm, ret, mat, False)


def rod(mat, p0, p1, radius, segs=6):
    """Cylinder spanning two game points (poles, pipes, cables)."""
    a, b = G(*p0), G(*p1)
    d = b - a
    L = d.length
    if L < 1e-6:
        return
    q = d.normalized().to_track_quat('Z', 'Y')
    M = Matrix.Translation((a + b) / 2.0) @ q.to_matrix().to_4x4()
    bm = master[mat]
    ret = bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=segs,
                                radius1=radius, radius2=radius, depth=L, matrix=M)
    faces = _finish(bm, ret, mat, True)
    for f in faces:
        if len(f.verts) == segs:
            f.smooth = False


def torus(mat, center, R_, r, segs=12, rings=6, axis='up', yaw=0.0):
    """axis 'up' = tyre lying flat, 'x' = wheel rolling along z."""
    bm = master[mat]
    verts = []
    for i in range(segs):
        a = 2 * math.pi * i / segs
        for j in range(rings):
            b = 2 * math.pi * j / rings
            x = (R_ + r * math.cos(b)) * math.cos(a)
            y = (R_ + r * math.cos(b)) * math.sin(a)
            z = r * math.sin(b)
            verts.append(bm.verts.new((x, y, z)))
    faces = []
    for i in range(segs):
        for j in range(rings):
            v0 = verts[i * rings + j]; v1 = verts[((i + 1) % segs) * rings + j]
            v2 = verts[((i + 1) % segs) * rings + (j + 1) % rings]; v3 = verts[i * rings + (j + 1) % rings]
            f = bm.faces.new((v0, v1, v2, v3))
            f.material_index = mat; f.smooth = True
            faces.append(f)
    M = Matrix.Translation(G(*center)) @ rot(yaw=yaw)
    if axis == 'x':
        M = M @ Matrix.Rotation(math.radians(90), 4, 'Y')
    elif axis == 'z':
        M = M @ Matrix.Rotation(math.radians(90), 4, 'X')
    bmesh.ops.transform(bm, matrix=M, verts=verts)


def blob(mat, center, size, jitter=0.25, subdiv=1, yaw=0.0):
    """Squashed, dented icosphere - scrap piles and sacks."""
    bm = master[mat]
    ret = bmesh.ops.create_icosphere(bm, subdivisions=subdiv, radius=1.0)
    for v in ret['verts']:
        v.co += Vector((R.uniform(-jitter, jitter), R.uniform(-jitter, jitter), R.uniform(-jitter, jitter) * 0.5))
    M = Matrix.Translation(G(*center)) @ rot(yaw=yaw) @ Matrix.Diagonal((size[0], size[2], size[1], 1.0))
    bmesh.ops.transform(bm, matrix=M, verts=ret['verts'])
    _finish(bm, ret, mat, True)


def text(mat, body, pos, size, extrude, yaw=0.0):
    cu = bpy.data.curves.new('sign', 'FONT')
    cu.body = body
    cu.size = size
    cu.extrude = extrude
    cu.resolution_u = 3
    cu.align_x = 'CENTER'
    ob = bpy.data.objects.new('sign', cu)
    bpy.context.scene.collection.objects.link(ob)
    dg = bpy.context.evaluated_depsgraph_get()
    ev = ob.evaluated_get(dg)
    me = ev.to_mesh()
    # text lies in its XY plane facing +Z; stand it up facing game +Z (= Blender -Y), mirrored
    # left-right because the engine shows every model mirrored (Space Race kit, seen in game 2026-09-29)
    M = Matrix.Translation(G(*pos)) @ rot(yaw=yaw) @ Matrix.Rotation(math.radians(90), 4, 'X') @ Matrix.Diagonal((-1.0, 1.0, 1.0, 1.0))
    bm = master[mat]
    vmap = {}
    for v in me.vertices:
        vmap[v.index] = bm.verts.new(M @ v.co)
    for p in me.polygons:
        try:
            f = bm.faces.new([vmap[i] for i in reversed(p.vertices)])   # the mirror flips the winding
            f.material_index = mat
            f.smooth = False
        except ValueError:
            pass
    ev.to_mesh_clear()
    bpy.data.objects.remove(ob)
    bpy.data.curves.remove(cu)


# ----------------------------------------------------------------- pieces --

def spikes(x, y, z, n, spread=0.8, h=0.7):
    for _ in range(n):
        cyl(IRON, (x + R.uniform(-spread, spread), y, z + R.uniform(-0.05, 0.05)), 0.05, h * R.uniform(0.7, 1.3),
            segs=4, r2=0.0, pitch=R.uniform(-20, 20), roll=R.uniform(-20, 20), smooth=False)


def wall_run(x0, z0, x1, z1, base_h=4.6, panel=2.2):
    dx, dz = x1 - x0, z1 - z0
    L = math.hypot(dx, dz)
    ux, uz = dx / L, dz / L          # along
    nx, nz = -uz, ux                 # normal (left of direction) - trace runs so this faces inward
    yaw = math.degrees(math.atan2(-uz, ux))
    n = int(L / panel + 0.999)
    step = L / n
    # framing rails on the inside
    for hgt in (1.5, 3.2):
        beam(IRON, (x0 + nx * 0.14, hgt, z0 + nz * 0.14), (x1 + nx * 0.14, hgt, z1 + nz * 0.14), 0.12)
    for i in range(n):
        t = (i + 0.5) * step
        cx, cz = x0 + ux * t, z0 + uz * t
        h = base_h + R.uniform(-0.6, 0.9)
        mat = R.choice(WALLMATS)
        lean = R.uniform(-3.5, 3.5)
        # pitch is about the panel's own long axis (applied before yaw): the lean
        box(mat, (cx, h / 2 - 0.25, cz), (step + 0.05, h + 0.25, 0.08), yaw=yaw, pitch=lean)
        if R.random() < 0.7:
            spikes(cx, h - 0.2, cz, R.randint(1, 3), spread=step * 0.4)
        if i % 2 == 0:
            rod(IRON, (cx + nx * 0.16, -0.2, cz + nz * 0.16), (cx + nx * 0.16, h + 0.3, cz + nz * 0.16), 0.09)


def container(center, yaw, mat, size=(6.0, 2.5, 2.4)):
    box(mat, center, size, yaw=yaw)
    # door end ribs
    box(IRON, (center[0], center[1], center[2]), (size[0] + 0.06, 0.08, size[2] + 0.06), yaw=yaw)


def drum(center, yaw=0.0, lying=False):
    mat = R.choice([RUST, RED, STRIPES, IRON, IRON])
    if lying:
        cyl(mat, (center[0], center[1] + 0.3, center[2]), 0.3, 0.9, segs=10, yaw=yaw, pitch=90)
    else:
        cyl(mat, center, 0.3, 0.9, segs=10, yaw=yaw)


def tyre_stack(x, z, n, R_=0.5, r=0.2):
    yaw = R.uniform(0, 360)
    for i in range(n):
        torus(TIRE, (x + R.uniform(-0.06, 0.06), r + i * (2 * r - 0.02), z + R.uniform(-0.06, 0.06)), R_, r, yaw=yaw)


def lamp(x, y, z, arm=0.0, yaw=0.0):
    cyl(IRON, (x, 0, z), 0.09, y, segs=6)
    hx = x + arm * math.cos(math.radians(yaw))
    hz = z - arm * math.sin(math.radians(yaw))
    if arm:
        beam(IRON, (x, y - 0.1, z), (hx, y, hz), 0.08)
    box(IRON, (hx, y - 0.12, hz), (0.5, 0.18, 0.5))
    box(GLOW, (hx, y - 0.25, hz), (0.36, 0.08, 0.36))


def flag(x, y, z, h=2.6, mat=TARP):
    rod(IRON, (x, y, z), (x, y + h, z), 0.035)
    box(mat, (x + 0.6, y + h - 0.35, z), (1.2, 0.7, 0.03), roll=R.uniform(-15, 15), yaw=R.uniform(-25, 25))


def car_wreck(center, yaw, tilt, mat):
    """tilt rolls the car nose-up about its own width axis."""
    x, y, z = center
    box(mat, (x, y + 0.9, z), (4.2, 1.1, 1.7), yaw=yaw, roll=tilt)
    box(IRON, (x - 0.3, y + 1.75, z), (2.4, 0.75, 1.55), yaw=yaw, roll=tilt)   # cabin / glass
    M = rot(0, yaw, tilt)
    for sx, sz in ((1.4, 0.95), (1.4, -0.95), (-1.4, 0.95), (-1.4, -0.95)):
        off = M @ Vector((sx, -sz, 0.35))   # Blender vector
        torus(TIRE, (x + off.x, y + off.z, z - off.y), 0.36, 0.14, segs=10, rings=6, axis='z', yaw=yaw)


# ------------------------------------------------------------------ scene --

def build():
    # ground slab: hides the terrain seam and reads as packed dirt/asphalt
    box(GROUND, (-1.0, -0.25, 0.0), (50.0, 0.6, 30.0))

    # ---- perimeter walls (gap for the gate x -7..8 at z=+15)
    wall_run(-26, -15, 24, -15)
    wall_run(-26, 15, -26, -15)
    wall_run(24, -15, 24, 15)
    wall_run(-7.4, 15, -26, 15)
    wall_run(24, 15, 8.4, 15)

    # ---- corner bastions of stacked containers
    for (cx, cz, yaw) in ((-23, -12.5, 0), (21, -12.5, 0), (-23, 12.5, 0), (21, 12.5, 0)):
        container((cx, 1.25, cz), yaw + R.uniform(-8, 8), R.choice([RUST, RED, CORR]))
        container((cx + R.uniform(-0.4, 0.4), 3.75, cz + R.uniform(-0.3, 0.3)), yaw + R.uniform(-12, 12), R.choice([RUST, RED, CORR]))
        spikes(cx, 5.0, cz, 6, spread=2.5, h=0.9)
        flag(cx + 2.4, 5.0, cz - 0.6, mat=R.choice([TARP, RED]))
        tyre_stack(cx + R.uniform(-3.5, 3.5), cz + (-1 if cz < 0 else 1) * -3.2, R.randint(2, 4))

    # ---- gate towers
    for tx in (-9.8, 10.8):
        for lvl, mat in enumerate((RUST, CORR, RED)):
            box(mat, (tx + R.uniform(-0.15, 0.15), 1.2 + lvl * 2.4, 14.0 + R.uniform(-0.15, 0.15)), (3.2, 2.4, 3.2), yaw=R.uniform(-4, 4))
        # front spikes and a welded X
        for yy in (3.0, 5.4):
            for k in range(4):
                cyl(IRON, (tx - 1.2 + k * 0.8, yy, 15.62), 0.06, 0.8, segs=4, r2=0.0, pitch=90, smooth=False)
        beam(IRON, (tx - 1.3, 0.6, 15.7), (tx + 1.3, 6.8, 15.7), 0.18)
        beam(IRON, (tx + 1.3, 0.6, 15.7), (tx - 1.3, 6.8, 15.7), 0.18)
        # crow's nest
        box(WOOD, (tx, 7.35, 14.0), (3.8, 0.2, 3.8))
        for px, pz in ((-1.8, -1.8), (1.8, -1.8), (-1.8, 1.8), (1.8, 1.8)):
            rod(IRON, (tx + px, 7.4, 14 + pz), (tx + px, 8.5, 14 + pz), 0.05)
            rod(IRON, (tx + px, 7.4, 14 + pz), (tx + px, 10.2, 14 + pz), 0.07)
        for (a, b) in (((-1.8, -1.8), (1.8, -1.8)), ((1.8, -1.8), (1.8, 1.8)), ((1.8, 1.8), (-1.8, 1.8)), ((-1.8, 1.8), (-1.8, -1.8))):
            beam(IRON, (tx + a[0], 8.5, 14 + a[1]), (tx + b[0], 8.5, 14 + b[1]), 0.06)
        box(R.choice([CORR, TARP]), (tx, 10.3, 14.0), (4.2, 0.07, 4.2), pitch=R.uniform(-10, 10), roll=R.uniform(-8, 8))
        spikes(tx, 10.35, 14.0, 5, spread=1.8, h=0.8)
        flag(tx + 1.9, 10.3, 14.0 - 1.9, h=3.0, mat=RED)
    # searchlight on the east tower
    rod(IRON, (10.8, 7.5, 14.0), (10.8, 8.4, 14.0), 0.06)
    cyl(IRON, (10.8, 8.4, 14.0), 0.32, 0.55, segs=10, pitch=60)
    cyl(GLOW, (10.8, 8.42, 14.0), 0.26, 0.6, segs=10, pitch=60)

    # ---- gate truss and hanging sign
    for zz in (13.0, 15.0):
        beam(IRON, (-9.8, 8.9, zz), (10.8, 8.9, zz), 0.28)
    for k in range(11):
        xx = -9.8 + k * 2.06
        beam(IRON, (xx, 8.9, 13.0), (xx, 8.9, 15.0), 0.16)
        if k < 10:
            beam(IRON, (xx, 8.9, 13.0), (xx + 2.06, 8.9, 15.0), 0.08)
    beam(IRON, (-9.8, 9.6, 13.0), (10.8, 9.6, 13.0), 0.14)
    beam(IRON, (-9.8, 9.6, 15.0), (10.8, 9.6, 15.0), 0.14)
    for k in range(6):
        xx = -9.8 + k * 4.12
        beam(IRON, (xx, 8.9, 13.0), (xx + 2.06, 9.6, 13.0), 0.08)
        beam(IRON, (xx + 2.06, 9.6, 13.0), (xx + 4.12, 8.9, 13.0), 0.08) if k < 5 else None
    # the sign: rusty plate on chains, slightly askew, lit letters
    box(RUST, (0.5, 7.1, 14.0), (11.5, 2.5, 0.16), roll=2.5)
    box(STRIPES, (0.5, 5.75, 14.0), (11.5, 0.22, 0.2), roll=2.5)
    rod(IRON, (-4.2, 8.3, 14.0), (-4.3, 8.9, 14.0), 0.035)
    rod(IRON, (5.2, 8.35, 14.0), (5.3, 8.9, 14.0), 0.035)
    rod(IRON, (-4.2, 8.3, 14.0), (5.2, 8.35, 14.0), 0.05)
    text(GLOW, 'TRADE POST', (0.5, 6.35, 14.12), 1.55, 0.12)
    # barrier arm raised beside the east tower, counterweight down
    cyl(IRON, (9.0, 0, 15.9), 0.16, 1.3, segs=8)
    box(STRIPES, (9.0, 1.3 + 2.85, 15.9 + 0.93), (0.16, 0.16, 6.0), pitch=-72)
    box(IRON, (9.0, 0.9, 16.6), (0.5, 0.5, 0.8))
    # tyre barricades flanking the gate approach
    tyre_stack(-8.6, 16.6, 3); tyre_stack(-7.4, 16.2, 2)
    tyre_stack(11.0, 16.4, 3); tyre_stack(9.6, 17.2, 2)

    # ---- loading canopy over the truck bays
    for zz in (-9.0, -3.5, 2.0, 7.5):
        for xx in (-6.9, 7.9):
            rod(IRON, (xx, -0.2, zz), (xx, 6.4, zz), 0.15, segs=8)
        beam(IRON, (-6.9, 6.4, zz), (7.9, 6.4, zz), 0.22)
    for xx in (-6.9, 7.9):
        beam(IRON, (xx, 6.4, -9.0), (xx, 6.4, 7.5), 0.22)
    for i in range(4):
        z0 = -10.4 + i * 4.6
        for j, (xa, xb) in enumerate(((-7.6, 0.6), (0.4, 8.6))):
            mat = R.choice([CORR, CORR, TARP, RUST])
            box(mat, ((xa + xb) / 2, 6.75 + R.uniform(-0.12, 0.2), z0 + 2.3), (xb - xa, 0.06, 4.9),
                pitch=R.uniform(-7, 7), roll=R.uniform(-4, 4) + (3 if j == 0 else -3))
    for zz in (-6.0, 4.5):
        for xx in (-3.2, 4.2):
            rod(IRON, (xx, 6.35, zz), (xx, 5.6, zz), 0.03)
            box(IRON, (xx, 5.5, zz), (0.45, 0.16, 0.45))
            box(GLOW, (xx, 5.4, zz), (0.34, 0.06, 0.34))

    # ---- east block: trade shed built out of a bus wreck and scrap
    wall_run(10.5, 6.0, 23.0, 6.0, base_h=4.2)
    wall_run(23.0, 6.0, 23.0, -12.5, base_h=4.2)
    wall_run(23.0, -12.5, 10.5, -12.5, base_h=4.2)
    wall_run(10.5, -12.5, 10.5, -6.0, base_h=4.2)
    wall_run(10.5, 0.5, 10.5, 6.0, base_h=4.2)
    # roof: two slabs meeting on a ridge along z
    box(RUST, (13.5, 5.35, -3.25), (6.6, 0.1, 19.2), roll=17)
    box(CORR, (20.0, 5.35, -3.25), (6.6, 0.1, 19.2), roll=-17)
    beam(IRON, (16.75, 6.4, 6.4), (16.75, 6.4, -12.9), 0.2)
    spikes(16.75, 6.5, -3.0, 8, spread=9.0, h=0.7)
    # trade counter in the shed's opening, with an awning
    box(WOOD, (10.5, 0.55, -2.75), (0.9, 1.1, 4.8))
    box(WOOD, (10.5, 1.12, -2.75), (1.4, 0.08, 5.2))
    box(TARP, (9.6, 3.1, -2.75), (2.6, 0.05, 5.6), roll=-14)
    rod(IRON, (8.4, -0.1, -0.2), (8.4, 2.8, -0.2), 0.05)
    rod(IRON, (8.4, -0.1, -5.3), (8.4, 2.8, -5.3), 0.05)
    lamp(9.4, 3.6, -2.75)
    # the bus, nosed into the north wall
    box(RED, (16.5, 1.5, 7.9), (10.6, 2.9, 2.6), yaw=6)
    box(IRON, (16.5, 2.25, 7.9), (10.7, 0.9, 2.66), yaw=6)
    box(RUST, (16.5, 3.05, 7.9), (9.0, 0.25, 2.2), yaw=6)
    for sx, sz in ((-3.6, 1.25), (-3.6, -1.25), (3.4, 1.25), (3.4, -1.25)):
        torus(TIRE, (16.5 + sx, 0.45, 7.9 + sz), 0.5, 0.2, axis='z', yaw=6)
    drum((21.9, 0, 9.1)); drum((21.2, 0, 9.6), yaw=30); drum((22.2, 0, 10.0), lying=True, yaw=20)
    # chimney, water tank, fuel tanks
    cyl(IRON, (21.5, 6.2, -9.5), 0.35, 3.4, segs=10)
    cyl(IRON, (21.5, 9.6, -9.5), 0.7, 0.5, segs=10, r2=0.1)
    for px, pz in ((-1.1, -1.1), (1.1, -1.1), (-1.1, 1.1), (1.1, 1.1)):
        rod(IRON, (14.0 + px, -0.2, -9.8 + pz), (14.0 + px * 0.8, 7.2, -9.8 + pz * 0.8), 0.1)
    for hh in (2.5, 5.0):
        for (a, b) in (((-1.1, -1.1), (1.1, -1.1)), ((1.1, -1.1), (1.1, 1.1)), ((1.1, 1.1), (-1.1, 1.1)), ((-1.1, 1.1), (-1.1, -1.1))):
            beam(IRON, (14.0 + a[0], hh, -9.8 + a[1]), (14.0 + b[0], hh, -9.8 + b[1]), 0.08)
    cyl(RUST, (14.0, 7.2, -9.8), 1.5, 2.3, segs=14)
    cyl(IRON, (14.0, 9.5, -9.8), 1.55, 0.6, segs=14, r2=0.2)
    cyl(RUST, (12.0, 1.15, -14.3), 0.85, 4.2, segs=12, pitch=90)   # pitch 90 lays it along +z
    for zz in (-13.4, -11.0):
        beam(IRON, (11.0, 0.0, zz), (13.0, 0.0, zz), 0.3, 0.6)
    box(STRIPES, (12.0, 1.15, -12.2), (1.75, 1.75, 0.3))
    fire_points.append((12.0, 1.2, -14.2))
    drum((11.0, 0, -12.9), lying=True, yaw=80); drum((11.8, 0, -11.9)); drum((12.4, 0, -12.5), yaw=15)
    fire_points.append((11.9, 0.5, -12.4))
    # watchtower in the NE corner
    tx, tz = 20.8, 10.6
    for px, pz in ((-1.5, -1.5), (1.5, -1.5), (-1.5, 1.5), (1.5, 1.5)):
        rod(IRON, (tx + px, -0.2, tz + pz), (tx + px * 0.7, 12.0, tz + pz * 0.7), 0.13, segs=8)
    for k, hh in enumerate((3.0, 6.0, 9.0)):
        s = 1.5 - 0.3 * (hh / 12.0) * 1.5
        s = 1.5 * (1 - 0.3 * hh / 12.0)
        for (a, b) in (((-1, -1), (1, -1)), ((1, -1), (1, 1)), ((1, 1), (-1, 1)), ((-1, 1), (-1, -1))):
            beam(IRON, (tx + a[0] * s, hh, tz + a[1] * s), (tx + b[0] * s, hh, tz + b[1] * s), 0.09)
        s2 = 1.5 * (1 - 0.3 * (hh + 3) / 12.0)
        beam(IRON, (tx - s, hh, tz - s), (tx + s2, hh + 3, tz - s2), 0.07)
        beam(IRON, (tx + s, hh, tz + s), (tx - s2, hh + 3, tz + s2), 0.07)
    box(WOOD, (tx, 12.1, tz), (3.4, 0.2, 3.4))
    for px, pz in ((-1.6, -1.6), (1.6, -1.6), (-1.6, 1.6), (1.6, 1.6)):
        rod(IRON, (tx + px, 12.1, tz + pz), (tx + px, 14.4, tz + pz), 0.06)
    for (a, b) in (((-1.6, -1.6), (1.6, -1.6)), ((1.6, -1.6), (1.6, 1.6)), ((1.6, 1.6), (-1.6, 1.6)), ((-1.6, 1.6), (-1.6, -1.6))):
        beam(IRON, (tx + a[0], 13.1, tz + a[1]), (tx + b[0], 13.1, tz + b[1]), 0.05)
    cyl(CORR, (tx, 14.4, tz), 2.7, 1.5, segs=4, r2=0.05, yaw=45, smooth=False)
    rod(IRON, (tx - 1.2, 14.4, tz + 1.2), (tx - 1.2, 19.5, tz + 1.2), 0.05)
    flag(tx - 1.2, 16.5, tz + 1.2, h=2.5, mat=RED)
    rod(IRON, (tx + 1.1, 14.0, tz - 1.1), (tx + 1.1, 15.6, tz - 1.1), 0.07)
    cyl(IRON, (tx + 1.1, 15.6, tz - 1.1), 1.1, 0.45, segs=12, r2=0.15, pitch=-50)
    cyl(IRON, (tx + 0.9, 12.3, tz + 0.5), 0.28, 0.5, segs=8, pitch=-70)
    cyl(GLOW, (tx + 0.9, 12.32, tz + 0.5), 0.22, 0.55, segs=8, pitch=-70)
    # cables stringing the towers together
    rod(IRON, (10.8, 10.4, 14.0), (tx - 1.0, 12.4, tz + 0.5), 0.03, segs=4)
    rod(IRON, (-9.8, 10.4, 14.0), (-6.9, 6.5, 7.5), 0.03, segs=4)
    rod(IRON, (10.8, 10.4, 14.0), (7.9, 6.5, 7.5), 0.03, segs=4)

    # ---- west block: the stockyard
    cyl(GRAVEL, (-17.5, 0, 6.5), 4.6, 2.9, segs=18, r2=0.4)
    cyl(GRAVEL, (-21.5, 0, 11.0), 2.6, 1.7, segs=14, r2=0.3)
    for i in range(3):
        for j in range(2):
            x = -13.6 + i * 1.35; z = -3.6 + j * 1.25
            box(WOOD, (x, 0.07, z), (1.3, 0.14, 1.15))
            box(BRICK, (x, 0.14 + 0.5, z), (1.15, 1.0, 1.0), yaw=R.uniform(-3, 3))
    for k in range(3):
        yaw = 0 if k % 2 == 0 else 90
        box(WOOD, (-19.5, 0.3 + k * 0.6, -7.0), (4.2 if yaw == 0 else 1.5, 0.55, 1.5 if yaw == 0 else 4.2), yaw=R.uniform(-2, 2))
    for k in range(6):
        rod(IRON, (-12.5 + (k % 3) * 0.25, 0.35 + (k // 3) * 0.2, 7.0), (-12.5 + (k % 3) * 0.25, 0.35 + (k // 3) * 0.2, 13.0), 0.09)
    box(WOOD, (-12.3, 0.12, 8.0), (1.2, 0.24, 0.3)); box(WOOD, (-12.3, 0.12, 12.0), (1.2, 0.24, 0.3))
    for k in range(3):
        box(IRON, (-15.0, 0.15 + k * 0.3, 10.0 + k * 0.1), (0.3, 0.3, 6.0), yaw=R.uniform(-2, 2))
    # cement sacks under a lean-to
    for px, pz in ((-24.2, -1.6), (-20.2, -1.6), (-24.2, 1.6), (-20.2, 1.6)):
        rod(IRON, (px, -0.2, pz), (px, 3.2 if pz < 0 else 2.6, pz), 0.08)
    box(TARP, (-22.2, 3.0, 0.0), (4.6, 0.05, 3.9), pitch=9)
    for i in range(4):
        for j in range(3):
            for k in range(2):
                blob(CEMENT, (-23.4 + i * 0.85, 0.2 + k * 0.36, -1.1 + j * 0.75), (0.5, 0.2, 0.36), jitter=0.12, yaw=R.uniform(-15, 15))
    # scrap crane wreck
    box(IRON, (-11.5, 0.35, -11.5), (3.6, 0.7, 0.8), yaw=15); box(IRON, (-11.5, 0.35, -9.9), (3.6, 0.7, 0.8), yaw=15)
    box(RED, (-11.5, 1.4, -10.7), (3.0, 1.4, 2.4), yaw=15)
    box(RUST, (-12.4, 2.8, -10.7), (1.6, 1.4, 1.6), yaw=15)
    beam(RUST, (-11.0, 2.2, -10.7), (-5.5, 7.6, -11.6), 0.5)
    rod(IRON, (-5.5, 7.6, -11.6), (-5.4, 4.6, -11.6), 0.03)
    box(IRON, (-5.4, 4.3, -11.6), (0.25, 0.45, 0.25))
    fire_points.append((-11.5, 1.0, -10.7))
    # wrecked cars: one nosed up into the west wall, one flipped by the gate
    car_wreck((-24.6, 0.4, 2.0), 95, 38, RED)
    car_wreck((-8.5, 0.0, -13.0), 20, 0, RUST)
    # scrap piles
    blob(IRON, (-23.5, 0, -12.5), (2.6, 1.1, 2.2), jitter=0.3)
    blob(RUST, (-7.8, 0, 12.6), (1.8, 0.9, 1.6), jitter=0.3)
    blob(IRON, (12.3, 0, 12.8), (2.2, 0.9, 1.8), jitter=0.3, yaw=40)
    blob(RUST, (22.6, 0, 1.5), (1.6, 0.8, 1.9), jitter=0.3)
    # drums
    for k in range(5):
        drum((-9.0 + k * 0.65 + R.uniform(-0.1, 0.1), 0, 9.0 + (k % 2) * 0.6), yaw=R.uniform(0, 360))
    drum((-20.5, 0, -12.0)); drum((-19.8, 0, -12.5), yaw=40); drum((-21.0, 0, -12.9), lying=True)
    fire_points.append((-8.0, 0.5, 9.3))
    # junk wind turbine on a mast
    rod(IRON, (-24.6, -0.2, -6.0), (-24.6, 9.5, -6.0), 0.1)
    box(IRON, (-24.6, 9.5, -6.0), (0.5, 0.4, 0.4))
    for k in range(3):
        a = k * 120.0
        box(IRON, (-24.9, 9.5 + 1.2 * math.cos(math.radians(a)), -6.0 + 1.2 * math.sin(math.radians(a))),
            (0.1, 2.4, 0.3), pitch=a)
    # lamp posts at the bays and gate approach
    lamp(-7.6, 5.4, 11.2, arm=0.9, yaw=0)
    lamp(8.6, 5.4, 11.2, arm=0.9, yaw=180)
    lamp(-7.8, 5.0, -10.6, arm=0.9, yaw=0)
    lamp(8.8, 5.0, -10.6, arm=0.9, yaw=180)
    lamp(-16.0, 5.8, 0.6, arm=1.0, yaw=90)
    # a few more tyres scattered in the yard
    tyre_stack(-9.5, 2.0, 4); tyre_stack(-16.5, -13.0, 2); tyre_stack(9.4, 9.5, 3); tyre_stack(-22.5, 6.5, 2)


# ----------------------------------------------------------------- export --

def box_uv(bm, tile):
    uv_lay = bm.loops.layers.uv.get('uv') or bm.loops.layers.uv.new('uv')
    bm.normal_update()
    for f in bm.faces:
        n = f.normal
        ax = max(range(3), key=lambda i: abs(n[i]))
        for l in f.loops:
            p = l.vert.co
            if ax == 2:      # horizontal face (Blender Z up)
                u, v = p.x, p.y
            elif ax == 0:    # faces +-X
                u, v = p.y, p.z
            else:            # faces +-Y
                u, v = p.x, p.z
            l[uv_lay].uv = (u / tile, v / tile)


def export_nmf(path):
    model = nmf.Model()
    model.magic = nmf.MAGIC_NATIVE
    used = []
    total_tris = total_verts = 0
    for mi, name in enumerate(MATS):
        bm = master[mi]
        if not bm.faces:
            continue
        bmesh.ops.triangulate(bm, faces=bm.faces[:])
        box_uv(bm, TILE[name])
        me = bpy.data.meshes.new('exp_' + name)
        bm.to_mesh(me)
        me.calc_tangents(uvmap='uv')
        uvd = me.uv_layers['uv'].data
        cn = me.corner_normals
        mat_index = len(used)
        used.append(name)
        # dedupe per material; split shapes at the u16 limit
        shapes = []
        vmap = {}
        cur = nmf.Shape('%s_%d' % (name, len(shapes)))
        for poly in me.polygons:
            keys = []
            for li in poly.loop_indices:
                l = me.loops[li]
                p = me.vertices[l.vertex_index].co
                n = cn[li].vector
                t = l.tangent
                b = l.bitangent
                uv = uvd[li].uv
                if t.length < 1e-6:
                    t = n.orthogonal().normalized()
                    b = n.cross(t)
                # Blender (x, y, z) -> game (x, z, -y); v flipped as the official exporter does
                key = (round(p.x, 4), round(p.z, 4), round(-p.y, 4),
                       round(n.x, 3), round(n.z, 3), round(-n.y, 3),
                       round(uv.x, 4), round(1.0 - uv.y, 4))
                keys.append((key, t, b))
            if len(vmap) + 3 > 65535:
                shapes.append(cur)
                cur = nmf.Shape('%s_%d' % (name, len(shapes)))
                vmap = {}
            for key, t, b in keys:
                idx = vmap.get(key)
                if idx is None:
                    idx = len(vmap)
                    vmap[key] = idx
                    cur.pos += [key[0], key[1], key[2]]
                    cur.nrm += [key[3], key[4], key[5]]
                    cur.tan += [t.x, t.z, -t.y]
                    cur.bin += [b.x, b.z, -b.y]
                    cur.uv += [key[6], key[7]]
                cur.indices.append(idx)
        shapes.append(cur)
        for s in shapes:
            s.subsets = [(0, len(s.indices), mat_index)]
            model.shapes.append(s)
            total_tris += s.nt
            total_verts += s.nv
        bpy.data.meshes.remove(me)
    model.materials = used
    size = nmf.write(model, path)
    nodes = [(s.name, s.bbox) for s in model.shapes]
    xs = [b[0] for _, b in nodes] + [b[3] for _, b in nodes]
    ys = [b[1] for _, b in nodes] + [b[4] for _, b in nodes]
    zs = [b[2] for _, b in nodes] + [b[5] for _, b in nodes]
    print('nmf: %d shapes, %d materials, %d tris, %d verts, %d bytes, bbox %s' % (
        len(model.shapes), len(used), total_tris, total_verts, size,
        ['%.1f' % v for v in (min(xs), min(ys), min(zs), max(xs), max(ys), max(zs))]))
    return used, nodes


def write_sidecars(outdir, used, nodes):
    import struct
    # building.bbox mirrors the mesh: u32 count, then per node
    # {char[512] name, u32 nodeIndex, float[6] box}, exactly as vanilla does.
    with open(os.path.join(outdir, 'building.bbox'), 'wb') as f:
        f.write(struct.pack('<I', len(nodes)))
        for i, (name, bbox) in enumerate(nodes):
            f.write(name.encode('latin1').ljust(512, b'\x00'))
            f.write(struct.pack('<I', i))
            f.write(struct.pack('<6f', *bbox))
    # building.fire: u32 count, then {u32 0, float[3]} per fire point
    with open(os.path.join(outdir, 'building.fire'), 'wb') as f:
        f.write(struct.pack('<I', len(fire_points)))
        for p in fire_points:
            f.write(struct.pack('<Ifff', 0, *p))
    # materials: diffuse in slot 0 relative to the mtl, engine blanks for the rest.
    # The _e variant is the night-time set, where slot 1 is the emissive map.
    for suffix, emissive in (('', False), ('_e', True)):
        lines = []
        for name in used:
            lines.append('$SUBMATERIAL %s' % name)
            lines.append('$TEXTURE_MTL 0 %s.dds' % name)
            if emissive:
                lines.append('$TEXTURE_MTL 1 %s.dds' % ('tp_glow' if name == 'tp_glow' else 'tp_black'))
            else:
                lines.append('$TEXTURE 1 buildings/blankspecular.dds')
            lines.append('$TEXTURE 2 buildings/blankbump.dds')
            lines.append('')
            lines.append('$DIFFUSECOLOR 0.9 0.9 0.9 1.0')
            lines.append('$SPECULARCOLOR 0.35 0.35 0.35 1.0')
            lines.append('$AMBIENTCOLOR 1.0 1.0 1.0 1.0')
            lines.append('')
            lines.append('$SPECULARPOWER 2.000000')
            lines.append('')
        lines.append('$END')
        lines.append('')
        with open(os.path.join(outdir, 'material%s.mtl' % suffix), 'w', newline='\r\n') as f:
            f.write('\n'.join(lines))
    for name in used + ['tp_black']:
        shutil.copy(os.path.join(TEXDIR, name + '.dds'), os.path.join(outdir, name + '.dds'))


# ---------------------------------------------------------------- preview --

def blender_materials():
    mats = []
    for name in MATS:
        m = bpy.data.materials.new(name)
        m.use_nodes = True
        nt = m.node_tree
        bsdf = nt.nodes.get('Principled BSDF')
        tex = nt.nodes.new('ShaderNodeTexImage')
        tex.image = bpy.data.images.load(os.path.abspath(os.path.join(TEXDIR, name + '.png')))
        nt.links.new(tex.outputs['Color'], bsdf.inputs['Base Color'])
        bsdf.inputs['Roughness'].default_value = 0.85
        if name == 'tp_glow':
            nt.links.new(tex.outputs['Color'], bsdf.inputs['Emission Color'])
            bsdf.inputs['Emission Strength'].default_value = 6.0
        mats.append(m)
    return mats


def scene_objects(mats):
    for mi, name in enumerate(MATS):
        bm = master[mi]
        if not bm.faces:
            continue
        me = bpy.data.meshes.new('view_' + name)
        bm.to_mesh(me)
        for m in mats:
            me.materials.append(m)
        ob = bpy.data.objects.new('view_' + name, me)
        bpy.context.scene.collection.objects.link(ob)


def render(path, cam_pos, target, res, fov=42.0, transparent=False, samples=48):
    sc = bpy.context.scene
    cam = bpy.data.cameras.new('cam')
    cam.angle = math.radians(fov)
    co = bpy.data.objects.new('cam', cam)
    sc.collection.objects.link(co)
    co.location = G(*cam_pos)
    co.rotation_euler = (G(*target) - co.location).to_track_quat('-Z', 'Y').to_euler()
    sc.camera = co
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.resolution_percentage = 100
    sc.render.film_transparent = transparent
    sc.render.image_settings.file_format = 'PNG'
    sc.render.image_settings.color_mode = 'RGBA' if transparent else 'RGB'
    sc.render.filepath = os.path.abspath(path)
    try:
        sc.render.engine = 'BLENDER_EEVEE'
        sc.eevee.taa_render_samples = samples
        bpy.ops.render.render(write_still=True)
    except Exception as e:
        print('eevee failed (%s), falling back to cycles' % e)
        sc.render.engine = 'CYCLES'
        sc.cycles.samples = 64
        sc.cycles.use_denoising = True
        bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(co)
    bpy.data.cameras.remove(cam)


def lighting(night=False):
    sc = bpy.context.scene
    sun = bpy.data.lights.get('sun') or bpy.data.lights.new('sun', 'SUN')
    sun.energy = 0.06 if night else 4.5
    sun.angle = math.radians(2.0)
    if night:
        sun.color = (0.55, 0.65, 1.0)
    so = bpy.data.objects.get('sun')
    if so is None:
        so = bpy.data.objects.new('sun', sun)
        sc.collection.objects.link(so)
    so.rotation_euler = (math.radians(52), math.radians(12), math.radians(-35))
    w = sc.world or bpy.data.worlds.new('World')
    sc.world = w
    w.use_nodes = True
    bg = w.node_tree.nodes.get('Background')
    if bg:
        bg.inputs[0].default_value = (0.03, 0.04, 0.08, 1.0) if night else (0.55, 0.47, 0.36, 1.0)
        bg.inputs[1].default_value = 0.6 if night else 0.9
    for m in bpy.data.materials:
        if m.name == 'tp_glow' and m.use_nodes:
            m.node_tree.nodes['Principled BSDF'].inputs['Emission Strength'].default_value = 14.0 if night else 6.0


def main():
    # start from an empty scene
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob)
    os.makedirs(OUTDIR, exist_ok=True)
    os.makedirs(PREVIEW, exist_ok=True)

    build()
    # preview geometry first (export triangulates the bmeshes in place, which is fine for viewing too)
    used, nodes = export_nmf(os.path.join(OUTDIR, 'model.nmf'))
    write_sidecars(OUTDIR, used, nodes)

    mats = blender_materials()
    scene_objects(mats)
    lighting()
    render(os.path.join(PREVIEW, 'tradepost_preview.png'), (-34.0, 22.0, 52.0), (0.0, 3.0, 0.0), (1600, 1000))
    render(os.path.join(PREVIEW, 'tradepost_gate.png'), (14.0, 6.0, 34.0), (0.0, 5.0, 8.0), (1600, 1000), fov=50)
    render(os.path.join(PREVIEW, 'tradepost_icon.png'), (-30.0, 30.0, 44.0), (-1.0, 2.0, 0.0), (384, 384), fov=44, transparent=True, samples=32)
    lighting(night=True)
    render(os.path.join(PREVIEW, 'tradepost_night.png'), (18.0, 7.0, 38.0), (0.0, 5.0, 6.0), (1600, 1000), fov=48)
    im = bpy.data.images.load(os.path.abspath(os.path.join(PREVIEW, 'tradepost_icon.png')))
    im.scale(96, 96)
    im.save(filepath=os.path.abspath(os.path.join(OUTDIR, 'imagegui.png')))
    print('done')


main()
