"""Procedural tiling textures (color + normal) generated with numpy and saved as PNG.

Procedural Blender shader nodes don't survive glTF export, so every textured surface
in the game uses one of these images instead.
"""
import os

import bpy
import numpy as np

SIZE = 1024


def _save(name, rgb, path):
    h, w, _ = rgb.shape
    rgba = np.concatenate([np.clip(rgb, 0, 1), np.ones((h, w, 1))], axis=2).astype(np.float32)
    img = bpy.data.images.new(name, w, h, alpha=False)
    img.pixels.foreach_set(rgba.ravel())
    img.filepath_raw = path
    img.file_format = 'PNG'
    img.save()
    bpy.data.images.remove(img)


def _normal_from_height(hgt, strength):
    dx = (np.roll(hgt, -1, axis=1) - np.roll(hgt, 1, axis=1)) * strength
    dy = (np.roll(hgt, -1, axis=0) - np.roll(hgt, 1, axis=0)) * strength
    n = np.stack([-dx, -dy, np.ones_like(hgt)], axis=2)
    n /= np.linalg.norm(n, axis=2, keepdims=True)
    return n * 0.5 + 0.5


def _noise(rng, size, scale):
    """Cheap smooth value noise (tileable) via upsampled random grid."""
    g = rng.random((scale, scale))
    reps = size // scale
    up = np.kron(g, np.ones((reps, reps)))
    # box-blur a few times for smoothness (wrap around => stays tileable)
    for _ in range(3):
        up = (up + np.roll(up, reps // 2, 0) + np.roll(up, -reps // 2, 0)
              + np.roll(up, reps // 2, 1) + np.roll(up, -reps // 2, 1)) / 5
    return up


def bricks(rng, tile_m, bw, bh, mortar, colors, mortar_rgb, offset=0.5, var=0.12, bevel=0.15,
           size=SIZE, rotate=False):
    """Running-bond bricks. Returns (rgb, height). tile_m/bw and tile_m/bh must be integers."""
    px = (np.arange(size) + 0.5) / size * tile_m
    X, Y = np.meshgrid(px, px)
    if rotate:
        X, Y = Y, X
    row = np.floor(Y / bh).astype(int)
    xs = (X + (row % 2) * offset * bw) % tile_m
    col = np.floor(xs / bw).astype(int)
    lx, ly = xs - col * bw, Y - row * bh
    m = mortar / 2
    edge = np.minimum.reduce([lx - m, bw - m - lx, ly - m, bh - m - ly])
    is_brick = edge > 0
    nr, nc = int(round(tile_m / bh)) + 1, int(round(tile_m / bw)) + 2
    pick = rng.integers(0, len(colors), (nr, nc))
    shade = 1 + rng.uniform(-var, var, (nr, nc))
    pal = np.array(colors)
    base = pal[pick[row % nr, col % nc]] * shade[row % nr, col % nc][..., None]
    grain = (_noise(rng, size, 64) - 0.5) * 0.12 + (rng.random((size, size)) - 0.5) * 0.06
    rgb = np.where(is_brick[..., None], base * (1 + grain[..., None]),
                   np.array(mortar_rgb) * (1 + grain[..., None] * 0.6))
    hgt = np.clip(edge / (min(bw, bh) * bevel), 0, 1)
    hgt = np.where(is_brick, 0.35 + 0.65 * np.sqrt(hgt), 0.0) + grain * 0.15
    return rgb, hgt


def roof_tiles(rng, colors, size=SIZE, cols=7, rows=8):
    px = (np.arange(size) + 0.5) / size
    X, Y = np.meshgrid(px, px)
    row = np.floor(Y * rows).astype(int)
    xs = (X + (row % 2) * 0.5 / cols) % 1
    col = np.floor(xs * cols).astype(int)
    lx, ly = xs * cols - col, Y * rows - row
    # each tile: rounded wave across, darker toward the overlap at the top
    wave = 0.55 + 0.45 * np.sin(lx * np.pi)
    overlap = 0.65 + 0.35 * (1 - ly)
    pick = rng.integers(0, len(colors), (rows + 1, cols + 1))
    shade = 1 + rng.uniform(-0.1, 0.1, (rows + 1, cols + 1))
    base = np.array(colors)[pick[row, col % (cols + 1)]] * shade[row, col % (cols + 1)][..., None]
    grain = (_noise(rng, size, 64) - 0.5) * 0.15
    rgb = base * (wave * overlap)[..., None] * (1 + grain[..., None])
    hgt = wave * (1 - ly) * 0.8 + grain
    return rgb, hgt


def srgb(h):
    h = h.lstrip('#')
    return [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]


SPECS = {
    # Dutch klinkers on the square: mixed red/brown/grey clinkers, sandy joints. 2 m tile.
    'klinkers': lambda r: bricks(r, 2.0, 0.2, 0.1, 0.008,
                                 [srgb(c) for c in ('#9c4a32', '#8a3f2c', '#a85a3c', '#7a3a2a', '#93503a', '#a5583a', '#8f6656')],
                                 srgb('#b5a58a'), var=0.07, bevel=0.25, rotate=True),
    'stoeptegels': lambda r: bricks(r, 1.8, 0.3, 0.3, 0.006,
                                    [srgb(c) for c in ('#a9a69f', '#b3b0a8', '#9d9a93')], srgb('#7e7b75'),
                                    offset=0.0, var=0.05, bevel=0.06),
    'brick_red': lambda r: bricks(r, 2.0, 0.2222, 0.0625, 0.011,
                                  [srgb(c) for c in ('#a3482f', '#953f2b', '#b05434', '#8a3a28')], srgb('#d8d0c0')),
    'brick_brown': lambda r: bricks(r, 2.0, 0.2222, 0.0625, 0.011,
                                    [srgb(c) for c in ('#5e3326', '#6b3a2a', '#523026', '#74412e')], srgb('#c9c0b0')),
    'brick_yellow': lambda r: bricks(r, 2.0, 0.2222, 0.0625, 0.011,
                                     [srgb(c) for c in ('#c9a66b', '#d1b07a', '#bf9a60', '#c4a070')], srgb('#efe8da')),
    'roof_red': lambda r: roof_tiles(r, [srgb(c) for c in ('#b5512e', '#a94a2a', '#c05a33')]),
    'roof_dark': lambda r: roof_tiles(r, [srgb(c) for c in ('#3b3d42', '#34363a', '#43454a')]),
}

NORMAL_STRENGTH = {'roof_red': 6, 'roof_dark': 6}


def ensure(out_dir, force=False):
    """Generate all textures that don't exist yet. Returns {name: (color_path, normal_path)}."""
    os.makedirs(out_dir, exist_ok=True)
    paths = {}
    for i, (name, fn) in enumerate(SPECS.items()):
        cp, np_ = os.path.join(out_dir, f'{name}.png'), os.path.join(out_dir, f'{name}_n.png')
        if force or not (os.path.exists(cp) and os.path.exists(np_)):
            rng = np.random.default_rng(100 + i)
            rgb, hgt = fn(rng)
            _save(name, rgb, cp)
            _save(name + '_n', _normal_from_height(hgt, NORMAL_STRENGTH.get(name, 10)), np_)
        paths[name] = (cp, np_)
    return paths
