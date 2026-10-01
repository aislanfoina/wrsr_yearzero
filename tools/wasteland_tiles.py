"""Procedural terrain tiles for the post-strike map: dead grass, fallout dust and
scorched ground, each with a bump (normal) map in the same DDS layout as the
vanilla tiles_normal set (1024^2, DXT1 diffuse, DXT5 bump, full mip chain).

    python tools/wasteland_tiles.py build/tiles
"""
import os
import sys

import numpy as np
from PIL import Image

TOOLS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, TOOLS)
from tradepost_textures import _tile_noise, save_dds_mips  # noqa: E402


def _norm01(a):
    return (a - a.min()) / (a.max() - a.min() + 1e-9)


def _rgb(base, tint, amount):
    out = np.zeros(base.shape + (3,), dtype=np.float32)
    for c in range(3):
        out[..., c] = base * tint[c] * amount
    return out


def _to_img(arr):
    return Image.fromarray(np.clip(arr * 255, 0, 255).astype(np.uint8), 'RGB')


def _normal_map(height, strength=2.0):
    """Tangent-space normal map from a height field, encoded like the vanilla bumps
    (RGB = xyz * 0.5 + 0.5, alpha = height for DXT5)."""
    gy, gx = np.gradient(height)
    nx = -gx * strength
    ny = -gy * strength
    nz = np.ones_like(height)
    l = np.sqrt(nx * nx + ny * ny + nz * nz)
    rgb = np.stack([nx / l, ny / l, nz / l], -1) * 0.5 + 0.5
    rgba = np.concatenate([rgb, _norm01(height)[..., None]], -1)
    return Image.fromarray(np.clip(rgba * 255, 0, 255).astype(np.uint8), 'RGBA')


def dead_grass(n=1024, seed=11):
    rs = np.random.RandomState(seed)
    low = _tile_noise(n, 6, octaves=5)
    fine = _tile_noise(n, 48, octaves=3)
    tufts = _tile_noise(n, 160, octaves=2)
    h = 0.55 * low + 0.3 * fine + 0.15 * tufts
    h = _norm01(h)
    # straw yellow-brown with bare dirt patches
    straw = np.array([0.62, 0.53, 0.30])
    dirt = np.array([0.36, 0.29, 0.20])
    dark = np.array([0.24, 0.20, 0.14])
    t = _norm01(low)
    col = straw[None, None] * (1 - t[..., None]) + dirt[None, None] * t[..., None]
    col = col * (0.75 + 0.5 * h[..., None])
    col = np.where((tufts > 0.62)[..., None], col * 0.7 + dark[None, None] * 0.3, col)
    col += (rs.rand(n, n, 3) - 0.5) * 0.04
    return _to_img(col), h


def fallout_dust(n=1024, seed=23):
    rs = np.random.RandomState(seed)
    low = _tile_noise(n, 5, octaves=4)
    cracks = _tile_noise(n, 22, octaves=3)
    crackline = np.abs(cracks - 0.5) < 0.012
    fine = _tile_noise(n, 90, octaves=2)
    h = _norm01(0.6 * low + 0.4 * fine)
    h = np.where(crackline, h * 0.45, h)
    pale = np.array([0.66, 0.60, 0.48])
    grey = np.array([0.47, 0.45, 0.41])
    t = _norm01(low)
    col = pale[None, None] * (1 - t[..., None]) + grey[None, None] * t[..., None]
    col = col * (0.8 + 0.35 * h[..., None])
    col = np.where(crackline[..., None], col * 0.55, col)
    col += (rs.rand(n, n, 3) - 0.5) * 0.03
    return _to_img(col), h


def scorched(n=1024, seed=37):
    rs = np.random.RandomState(seed)
    low = _tile_noise(n, 7, octaves=5)
    clumps = _tile_noise(n, 30, octaves=3)
    fine = _tile_noise(n, 120, octaves=2)
    h = _norm01(0.5 * low + 0.3 * clumps + 0.2 * fine)
    black = np.array([0.09, 0.08, 0.07])
    ash = np.array([0.30, 0.29, 0.27])
    ember = np.array([0.38, 0.16, 0.06])
    t = _norm01(clumps)
    col = black[None, None] * (1 - t[..., None]) + ash[None, None] * t[..., None]
    col = col * (0.7 + 0.5 * h[..., None])
    col = np.where((fine > 0.78)[..., None], col * 0.5 + ember[None, None] * 0.5, col)
    col += (rs.rand(n, n, 3) - 0.5) * 0.03
    return _to_img(col), h


TILES = {'wl_dead': dead_grass, 'wl_dust': fallout_dust, 'wl_scorched': scorched}


def main(outdir):
    os.makedirs(outdir, exist_ok=True)
    for name, fn in TILES.items():
        img, h = fn()
        img.save(os.path.join(outdir, name + '.png'))
        save_dds_mips(img, os.path.join(outdir, name + '.dds'), 'DXT1')
        save_dds_mips(_normal_map(h, 1.6), os.path.join(outdir, name + 'bump.dds'), 'DXT5')
        print(name, os.path.getsize(os.path.join(outdir, name + '.dds')), os.path.getsize(os.path.join(outdir, name + 'bump.dds')))


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else 'build/tiles')
