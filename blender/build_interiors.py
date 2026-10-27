"""Shop and window interiors, rendered once into texture atlases for the facades.

The houses are solid blocks, so there is nothing behind the glass. Instead every shop window shows a little
rendered 3D interior of its kind of shop (cheese wheels, loaves, flowers, shoes, bikes, a café, ...) and every
house window a room behind it (vitrage, curtains, plants, a lamp). Zero runtime cost: one texture per atlas.

Writes to assets/textures:
  shop_interiors.png    SHOP_KINDS cells (SHOP_COLS x SHOP_ROWS), see shop_kind() for the name -> kind mapping
  window_interiors.png  WINDOW_CELLS cells (WIN_COLS x WIN_ROWS)

Run:  Blender -b -P blender/build_interiors.py
"""
import math
import os
import random
import sys

import bpy
import numpy as np
from mathutils import Vector

sys.path.insert(0, os.path.dirname(__file__))
import lib  # noqa: E402
from lib import box, capsule, cyl, ico, material, sphere, text_mesh, torus, tube  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
V = Vector
rng = random.Random(5)

SHOP_KINDS = ['bakery', 'cheese', 'flowers', 'books', 'fashion', 'shoes', 'cafe', 'snackbar', 'icecream', 'butcher',
              'fish', 'drogist', 'optics', 'candy', 'bikes', 'kapper', 'wine', 'coffee', 'travel', 'generic']
SHOP_COLS, SHOP_ROWS, SHOP_CELL = 5, 4, 384
WIN_COLS, WIN_ROWS, WIN_W, WIN_H = 4, 2, 256, 384
WINDOW_CELLS = WIN_COLS * WIN_ROWS

KEYWORDS = [  # first match wins
    ('bakery', ('BAKKER', 'DONUT', 'WAFEL', 'POFFERTJES', 'LUNCHROOM')),
    ('cheese', ('KAAS', 'KRUIDENIER')), ('flowers', ('BLOEM', 'FRUIT')), ('books', ('BOEK', 'BIBLIOTHEEK', 'KADO', 'CULTUUR')),
    ('fashion', ('BOETIEK', 'HEMDEN', 'HOEDEN', 'TASSEN', 'WOL')), ('shoes', ('SCHOEN', 'LAARS')),
    ('optics', ('OPTIEK', 'BRILLEN', 'JUWELIER', 'TELEFOON')), ('cafe', ('EETCAFE', 'BAR ', 'BAR')),
    ('snackbar', ('FRITUUR', 'SNACK')), ('icecream', ('IJS',)), ('butcher', ('SLAGER',)), ('fish', ('VIS',)),
    ('drogist', ('DROGIST', 'PARFUM')), ('candy', ('SNOEP', 'SPEELGOED', 'DIEREN', 'TABAK')), ('bikes', ('FIETS',)),
    ('kapper', ('KAP',)), ('wine', ('WIJN',)), ('coffee', ('KOFFIE',)), ('travel', ('REIS',)),
]


def shop_kind(name):
    """Which interior a shop called `name` gets (index into SHOP_KINDS)."""
    up = name.upper()
    for kind, keys in KEYWORDS:
        if any(k in up for k in keys):
            return SHOP_KINDS.index(kind)
    return SHOP_KINDS.index('generic')


def shop_uv(name):
    """UV rect (u0, v0, u1, v1) of a shop's interior in the atlas."""
    i = shop_kind(name)
    c, r = i % SHOP_COLS, i // SHOP_COLS
    return (c / SHOP_COLS, 1 - (r + 1) / SHOP_ROWS, (c + 1) / SHOP_COLS, 1 - r / SHOP_ROWS)


def window_uv(i):
    i %= WINDOW_CELLS
    c, r = i % WIN_COLS, i // WIN_COLS
    return (c / WIN_COLS, 1 - (r + 1) / WIN_ROWS, (c + 1) / WIN_COLS, 1 - r / WIN_ROWS)


# ================================================================ materials

def mats():
    m = lambda name, col, **kw: material(name, col, **kw)
    return {
        'wall': m('I_Wall', '#e8dcc4', rough=0.9), 'wall_green': m('I_WallGreen', '#5f8a6a', rough=0.9),
        'wall_blue': m('I_WallBlue', '#7fa0c0', rough=0.9), 'wall_tile': m('I_Tile', '#f2f2ee', rough=0.3),
        'wall_dark': m('I_WallDark', '#3a3430', rough=0.9), 'wall_pink': m('I_WallPink', '#e8b4c0', rough=0.9),
        'floor': m('I_Floor', '#8a6a4a', rough=0.6), 'floor_tile': m('I_FloorTile', '#c8c2b8', rough=0.4),
        'wood': m('I_Wood', '#7a5434', rough=0.6), 'wood_l': m('I_WoodLight', '#c49a68', rough=0.6),
        'white': m('I_White', '#f6f4ee', rough=0.4), 'steel': m('I_Steel', '#c8ccd2', rough=0.2, metal=1.0),
        'black': m('I_Black', '#1c1c1e', rough=0.4), 'glass': m('I_Glass', '#d8eef2', rough=0.05),
        'lamp': m('I_Lamp', '#fff2d0', emission='#ffe6b0', strength=8), 'screen': m('I_Screen', '#203040', emission='#7fd0ff', strength=2),
        'red': m('I_Red', '#c8302a', rough=0.5), 'yellow': m('I_Yellow', '#f2c425', rough=0.5), 'orange': m('I_Orange', '#f08a24', rough=0.5),
        'green': m('I_Green', '#3f8a3a', rough=0.6), 'blue': m('I_Blue', '#2b5a8c', rough=0.5), 'pink': m('I_Pink', '#ea6aa4', rough=0.5),
        'purple': m('I_Purple', '#7a4ab0', rough=0.5), 'brown': m('I_Brown', '#8a5a30', rough=0.6), 'crust': m('I_Crust', '#c8873e', rough=0.7),
        'cheese': m('I_Cheese', '#f2c14a', rough=0.5), 'rind': m('I_Rind', '#d8a02a', rough=0.5, coat=0.6),
        'meat': m('I_Meat', '#c2414a', rough=0.5), 'fat': m('I_Fat', '#f2dcd0', rough=0.5), 'ice': m('I_Ice', '#eaf6fa', rough=0.2),
        'fishm': m('I_Fish', '#5f7f9f', rough=0.25, metal=0.4), 'leaf': m('I_Leaf', '#4f8a2c', rough=0.7),
        'cream': m('I_Cream', '#f6ead0', rough=0.5), 'choc': m('I_Choc', '#5a3420', rough=0.5), 'gold': m('I_Gold', '#e7c35a', rough=0.25, metal=1.0),
        'bottle_g': m('I_BottleGreen', '#1f4a2a', rough=0.1, coat=1.0), 'bottle_r': m('I_BottleRed', '#6a1020', rough=0.1, coat=1.0),
        'poster_sun': m('I_PosterSun', '#ffb03a', emission='#ffb03a', strength=0.4), 'poster_sea': m('I_PosterSea', '#2fa0d8', emission='#2fa0d8', strength=0.3),
        'chalk': m('I_Chalk', '#22302a', rough=0.8), 'mirror': m('I_Mirror', '#c8d8e0', rough=0.02, metal=1.0),
        'skin': m('I_Skin', '#e8c8a8', rough=0.6), 'velvet': m('I_Velvet', '#3a1020', rough=0.9),
    }


PALETTE = ['red', 'yellow', 'orange', 'green', 'blue', 'pink', 'purple', 'white']


# ================================================================ room + furniture

def room(M, wall='wall', floor='floor', lamps=3):
    """Back wall at y=1.4, side walls at x=+-1.7, ceiling at 2.8; seen from y=-2.6."""
    p = [box('back', (3.6, 0.1, 3.0), (0, 1.45, 1.4), M[wall], smooth=False),
         box('floor', (3.6, 4.0, 0.1), (0, 0, -0.05), M[floor], smooth=False),
         box('ceil', (3.6, 4.0, 0.1), (0, 0, 2.85), M['white'], smooth=False)]
    for s in (-1, 1):
        p.append(box('side', (0.1, 4.0, 3.0), (s * 1.75, 0, 1.4), M[wall], smooth=False))
    for i in range(lamps):
        x = (i - (lamps - 1) / 2) * 1.1
        p += [tube('cord', (x, 0.5, 2.8), (x, 0.5, 2.35), 0.01, M['black'], seg=6),
              cyl('shade', 0.2, 0.18, (x, 0.5, 2.3), M['black'], r2=0.06, seg=16),
              sphere('bulb', 0.08, (x, 0.5, 2.2), M['lamp'], seg=12, rings=6)]
    return p


def shelves(M, x0, x1, levels=(0.35, 0.8, 1.25, 1.7), y=1.2, depth=0.4, mat='wood'):
    p = [box('upright', (0.05, depth, 2.1), (x, y, 1.05), M[mat], smooth=False) for x in (x0, x1)]
    for z in levels:
        p.append(box('shelf', (x1 - x0, depth, 0.04), ((x0 + x1) / 2, y, z), M[mat], smooth=False))
    return p, [(x0 + 0.08, x1 - 0.08, z + 0.02, y) for z in levels]


def fill(slots, item, gap):
    """Place item(x, y, z) along each shelf slot every `gap` metres."""
    p = []
    for xa, xb, z, y in slots:
        n = max(1, int((xb - xa) / gap))
        for i in range(n):
            x = xa + (i + 0.5) * (xb - xa) / n
            p += item(x, y - 0.05, z, i)
    return p


def counter(M, x, y, w, h=0.95, top='wood_l', front='wood'):
    return [box('counter', (w, 0.6, h), (x, y, h / 2), M[front], bevel=0.02),
            box('counter_top', (w + 0.06, 0.66, 0.05), (x, y, h + 0.02), M[top], smooth=False)]


def podium(M, w=2.6, y=-1.2, h=0.4, mat='white'):
    """The window display just behind the glass."""
    return [box('podium', (w, 0.6, h), (0, y, h / 2), M[mat], bevel=0.02)]


def sign(M, text, z, mat='black', txt='white', size=0.16, y=1.38):
    return [box('board', (len(text) * size * 0.75 + 0.3, 0.04, size * 1.8), (0, y, z), M[mat], smooth=False),
            text_mesh('txt', text, size, (0, y - 0.03, z), mat=M[txt], extrude=0.005)]


# ================================================================ products

def loaf(M, x, y, z, i):
    r = rng.random()
    if r < 0.4:
        return [capsule('loaf', (x - 0.1, y, z + 0.07), (x + 0.1, y, z + 0.07), 0.07, mat=M['crust'], sxy=(1, 0.8), seg=12, rings=6)]
    if r < 0.7:
        return [sphere('bol', 0.08, (x, y, z + 0.06), M['crust'], scale=(1, 1, 0.7), seg=12, rings=6)]
    return [torus('donut', 0.06, 0.03, (x, y, z + 0.035), M['crust'], segU=14, segV=8),
            torus('icing', 0.06, 0.027, (x, y, z + 0.045), M[rng.choice(['pink', 'choc', 'white', 'yellow'])], segU=14, segV=8, rz=0.02)]


def cheese(M, x, y, z, i):
    big = i % 2 == 0
    r, h = (0.15, 0.1) if big else (0.09, 0.07)
    p = [cyl('wheel', r, h, (x, y, z + h / 2), M['rind'], seg=20)]
    if not big and rng.random() < 0.5:
        p.append(box('wedge', (0.1, 0.08, 0.06), (x + 0.06, y - 0.12, z + 0.03), M['cheese'], rot=(0, 0, 0.5), smooth=False))
    return p


def flowers(M, x, y, z, i):
    col = PALETTE[i % 7]
    p = [cyl('bucket', 0.09, 0.18, (x, y, z + 0.09), M['steel'], seg=12)]
    for k in range(6):
        a = k / 6 * math.tau
        tip = V((x + math.cos(a) * 0.06, y + math.sin(a) * 0.05, z + 0.32 + rng.uniform(0, 0.06)))
        p += [tube('stem', (x, y, z + 0.15), tip, 0.006, M['leaf'], seg=4), ico('bloom', 0.04, tip, M[col], subdiv=1)]
    return p


def fruit(M, x, y, z, i):
    col = ['red', 'green', 'orange', 'yellow'][i % 4]
    p = [box('crate', (0.3, 0.25, 0.1), (x, y, z + 0.05), M['wood_l'], smooth=False)]
    for k in range(6):
        p.append(sphere('fruit', 0.045, (x - 0.09 + (k % 3) * 0.09, y - 0.05 + (k // 3) * 0.1, z + 0.12), M[col], seg=10, rings=5))
    return p


def books(M, x, y, z, i):
    p = []
    for k in range(7):
        h = rng.uniform(0.18, 0.28)
        p.append(box('book', (0.035, 0.18, h), (x - 0.12 + k * 0.04, y, z + h / 2), M[rng.choice(PALETTE)], smooth=False))
    return p


def shirt(M, x, y, z, i):
    col = M[rng.choice(PALETTE)]
    return [box('shirt', (0.06, 0.32, 0.42), (x, y, z), col, bevel=0.02), tube('hanger', (x, y, z + 0.21), (x, y, z + 0.3), 0.008, M['steel'], seg=4)]


def shoe(M, x, y, z, i):
    col = M[rng.choice(['red', 'white', 'black', 'brown', 'blue'])]
    return [capsule('shoe', (x - 0.06, y - 0.04 + d * 0.0, z + 0.04), (x + 0.07, y - 0.04, z + 0.03), 0.04, mat=col, sxy=(0.8, 1), seg=10, rings=5)
            for d in (0,)] + [capsule('shoe2', (x - 0.06, y + 0.05, z + 0.04), (x + 0.07, y + 0.05, z + 0.03), 0.04, mat=col, sxy=(0.8, 1), seg=10, rings=5)]


def bottle(M, x, y, z, i, kinds=('bottle_g', 'bottle_r')):
    m = M[kinds[i % len(kinds)]]
    return [cyl('bottle', 0.035, 0.22, (x, y, z + 0.11), m, seg=10), cyl('neck', 0.012, 0.08, (x, y, z + 0.26), m, seg=8)]


def small_bottle(M, x, y, z, i):
    m = M[PALETTE[i % 8]]
    return [cyl('tube', 0.03, 0.14, (x, y, z + 0.07), m, seg=10), cyl('cap', 0.02, 0.03, (x, y, z + 0.155), M['white'], seg=8)]


def jar(M, x, y, z, i):
    p = [cyl('jar', 0.07, 0.2, (x, y, z + 0.1), M['glass'], seg=14)]
    for k in range(5):
        p.append(sphere('sweet', 0.025, (x + rng.uniform(-0.03, 0.03), y + rng.uniform(-0.03, 0.03), z + 0.04 + k * 0.03),
                        M[rng.choice(PALETTE)], seg=8, rings=4))
    return p


def toy(M, x, y, z, i):
    if i % 3 == 0:
        return [sphere('ball', 0.08, (x, y, z + 0.08), M[rng.choice(PALETTE)], seg=12, rings=6)]
    if i % 3 == 1:   # teddy
        return [sphere('teddy', 0.08, (x, y, z + 0.08), M['brown'], seg=10, rings=5), sphere('teddy_head', 0.06, (x, y, z + 0.2), M['brown'], seg=10, rings=5)]
    return [box('toybox', (0.18, 0.12, 0.16), (x, y, z + 0.08), M[rng.choice(PALETTE)], bevel=0.01)]


def glasses(M, x, y, z, i):
    p = [box('stand', (0.02, 0.02, 0.1), (x, y, z + 0.05), M['white'], smooth=False)]
    for s in (-1, 1):
        p.append(torus('lens', 0.03, 0.006, (x + s * 0.035, y - 0.02, z + 0.12), M[rng.choice(['black', 'gold', 'red', 'blue'])],
                       rot=(math.pi / 2, 0, 0), segU=12, segV=4))
    return p


# ================================================================ scenes per kind

def scene(M, kind):
    p = []
    if kind == 'bakery':
        p += room(M, 'wall', 'floor_tile')
        for x0, x1 in ((-1.6, -0.2), (0.2, 1.6)):
            sh, slots = shelves(M, x0, x1)
            p += sh + fill(slots, lambda x, y, z, i: loaf(M, x, y, z, i), 0.24)
        p += counter(M, 0, 0.2, 2.4, top='glass') + podium(M, mat='wood_l')
        p += fill([(-1.1, 1.1, 0.4, -1.1)], lambda x, y, z, i: loaf(M, x, y, z, i + 1), 0.22)
        p += sign(M, 'VERS GEBAKKEN', 2.2)
    elif kind == 'cheese':
        p += room(M, 'wall_dark', 'floor')
        for x0, x1 in ((-1.6, -0.2), (0.2, 1.6)):
            sh, slots = shelves(M, x0, x1)
            p += sh + fill(slots, lambda x, y, z, i: cheese(M, x, y, z, i), 0.32)
        p += podium(M, mat='wood') + fill([(-1.1, 1.1, 0.4, -1.1)], lambda x, y, z, i: cheese(M, x, y, z, 0), 0.4)
        p += sign(M, 'BOEREN KAAS', 2.2, 'cheese', 'black')
    elif kind == 'flowers':
        p += room(M, 'wall_green', 'floor_tile')
        for row, (z, y) in enumerate(((0.0, 0.9), (0.3, 0.3), (0.0, -1.1))):
            p += box('step', (3.2, 0.4, z + 0.05), (0, y, (z + 0.05) / 2), M['wood'], smooth=False),
            p += fill([(-1.4, 1.4, z + 0.05, y + 0.05)], lambda x, y_, z_, i, r=row: flowers(M, x, y_, z_, i + r * 3), 0.3)
        p += fill([(-1.4, 1.4, 1.2, 1.3)], lambda x, y, z, i: fruit(M, x, y, z, i), 0.4)
    elif kind == 'books':
        p += room(M, 'wall', 'floor')
        for x0, x1 in ((-1.6, -0.55), (-0.5, 0.5), (0.55, 1.6)):
            sh, slots = shelves(M, x0, x1, levels=(0.3, 0.75, 1.2, 1.65, 2.1))
            p += sh + fill(slots, lambda x, y, z, i: books(M, x, y, z, i), 0.3)
        p += podium(M) + fill([(-1.0, 1.0, 0.4, -1.1)], lambda x, y, z, i: [box('stack', (0.22, 0.16, 0.12), (x, y, z + 0.06), M[rng.choice(PALETTE)], bevel=0.01)], 0.4)
    elif kind == 'fashion':
        p += room(M, 'wall_pink', 'floor')
        for xr in (-0.9, 0.9):
            p += [tube('rail', (xr - 0.6, 0.9, 1.6), (xr + 0.6, 0.9, 1.6), 0.015, M['steel'], seg=6)]
            p += fill([(xr - 0.55, xr + 0.55, 1.35, 0.95)], lambda x, y, z, i: shirt(M, x, y, z, i), 0.12)
        for x in (-0.8, 0.8):   # mannequins in the window
            p += [capsule('body', (x, -1.1, 0.5), (x, -1.1, 1.3), 0.17, mat=M[rng.choice(PALETTE)], seg=12, rings=6),
                  sphere('head', 0.11, (x, -1.1, 1.55), M['white'], seg=12, rings=6), cyl('stand', 0.15, 0.04, (x, -1.1, 0.02), M['black'], seg=12)]
        p += sign(M, 'SALE -50%', 2.2, 'red')
    elif kind == 'shoes':
        p += room(M, 'wall', 'floor')
        for x0, x1 in ((-1.6, -0.2), (0.2, 1.6)):
            sh, slots = shelves(M, x0, x1, mat='white')
            p += sh + fill(slots, lambda x, y, z, i: shoe(M, x, y, z, i), 0.3)
        p += podium(M, mat='black') + fill([(-1.1, 1.1, 0.4, -1.1)], lambda x, y, z, i: shoe(M, x, y, z, i), 0.35)
    elif kind in ('cafe', 'coffee'):
        p += room(M, 'wall_dark' if kind == 'cafe' else 'wall', 'floor', lamps=4)
        p += counter(M, 0.6, 0.7, 2.0)
        sh, slots = shelves(M, -0.4, 1.6, levels=(1.3, 1.75), y=1.3, depth=0.2)
        p += sh + fill(slots, lambda x, y, z, i: bottle(M, x, y, z, i, ('bottle_g', 'bottle_r', 'gold')), 0.12)
        if kind == 'coffee':
            p += [box('espresso', (0.5, 0.35, 0.4), (0.9, 0.7, 1.2), M['steel'], bevel=0.03)]
            p += sign(M, 'KOFFIE 2,50', 2.25, 'chalk')
        for x in (-1.0, 0.0):   # bistro tables in front
            p += [cyl('table', 0.3, 0.03, (x, -0.6, 0.74), M['white'], seg=16), tube('leg', (x, -0.6, 0), (x, -0.6, 0.73), 0.025, M['black'], seg=6)]
            for s in (-1, 1):
                p += [box('chair', (0.38, 0.38, 0.04), (x + s * 0.45, -0.6, 0.45), M['wood'], smooth=False),
                      box('chair_back', (0.04, 0.38, 0.45), (x + s * 0.64, -0.6, 0.7), M['wood'], smooth=False)]
    elif kind in ('snackbar', 'icecream'):
        p += room(M, 'wall_tile', 'floor_tile')
        p += counter(M, 0, 0.3, 3.0, top='steel', front='red' if kind == 'snackbar' else 'pink')
        if kind == 'snackbar':
            p += [box('fryer', (0.8, 0.4, 0.5), (-0.8, 1.1, 1.1), M['steel'], bevel=0.02)]
            p += sign(M, 'FRIETJE 3,-', 2.2, 'black', 'yellow')
            p += sign(M, 'KROKET 2,-', 1.75, 'black', 'yellow')
        else:   # ice cream vitrine: tubs of colours
            for k in range(8):
                p.append(box('tub', (0.3, 0.25, 0.08), (-1.2 + k * 0.34, 0.25, 1.0), M[PALETTE[k]], bevel=0.02))
            p += sign(M, 'SCHEPIJS', 2.2, 'pink', 'white')
    elif kind in ('butcher', 'fish'):
        p += room(M, 'wall_tile', 'floor_tile')
        p += counter(M, 0, 0.3, 3.0, top='glass', front='white')
        item = (lambda x, y, z, i: [sphere('meat', 0.08, (x, y, z + 0.05), M['meat' if i % 3 else 'fat'], scale=(1.4, 1, 0.6), seg=10, rings=5)]) \
            if kind == 'butcher' else \
            (lambda x, y, z, i: [capsule('fish', (x - 0.14, y, z + 0.05), (x + 0.14, y, z + 0.05), 0.05, mat=M['fishm'], sxy=(1, 0.5), seg=10, rings=5)])
        p += [box('bed', (2.8, 0.5, 0.04), (0, 0.3, 0.98), M['ice' if kind == 'fish' else 'white'], smooth=False)]
        p += fill([(-1.3, 1.3, 1.0, 0.3)], item, 0.18)
        if kind == 'butcher':
            p += [sphere('ham', 0.12, (-1.2 + k * 0.4, 1.2, 2.0), M['meat'], scale=(0.8, 0.8, 1.4), seg=10, rings=6) for k in range(7)]
        p += sign(M, 'VERS!' if kind == 'fish' else 'SLAVINKEN 4 VOOR 5', 1.75, 'blue' if kind == 'fish' else 'red')
    elif kind == 'drogist':
        p += room(M, 'wall_blue', 'floor_tile')
        for x0, x1 in ((-1.6, -0.2), (0.2, 1.6)):
            sh, slots = shelves(M, x0, x1, mat='white')
            p += sh + fill(slots, lambda x, y, z, i: small_bottle(M, x, y, z, i), 0.1)
        p += sign(M, '1+1 GRATIS', 2.2, 'red')
    elif kind == 'optics':
        p += room(M, 'wall', 'floor')
        sh, slots = shelves(M, -1.6, 1.6, levels=(0.6, 1.0, 1.4, 1.8), mat='white')
        p += sh + fill(slots, lambda x, y, z, i: glasses(M, x, y, z, i), 0.2)
        p += [box('mirror', (0.6, 0.04, 1.0), (1.2, 1.38, 1.3), M['mirror'], smooth=False)]
    elif kind == 'candy':
        p += room(M, 'wall_pink', 'floor')
        for x0, x1 in ((-1.6, -0.2), (0.2, 1.6)):
            sh, slots = shelves(M, x0, x1)
            p += sh + fill(slots, lambda x, y, z, i: (jar if i % 2 else toy)(M, x, y, z, i), 0.22)
        p += podium(M) + fill([(-1.1, 1.1, 0.4, -1.1)], lambda x, y, z, i: toy(M, x, y, z, i), 0.3)
    elif kind == 'bikes':
        p += room(M, 'wall', 'floor_tile')
        for k, x in enumerate((-1.0, 0.0, 1.0)):
            col = M[['red', 'blue', 'green'][k]]
            for wx in (-0.42, 0.42):
                p.append(torus('wheel', 0.3, 0.025, (x * 0.5 + wx * 0.0, -0.4 + wx, 0.33), M['black'], rot=(0, math.pi / 2, 0), segU=24, segV=6))
            p += [tube('top', (x * 0.5, -0.6, 0.85), (x * 0.5, 0.2, 0.85), 0.025, col, seg=8),
                  tube('down', (x * 0.5, -0.5, 0.85), (x * 0.5, 0.0, 0.35), 0.025, col, seg=8)]
        p += [tube('hook_rail', (-1.6, 1.3, 2.0), (1.6, 1.3, 2.0), 0.02, M['steel'], seg=6)]
        p += [torus('hung_wheel', 0.3, 0.025, (-1.2 + k * 0.6, 1.3, 1.65), M['black'], rot=(math.pi / 2, 0, 0), segU=24, segV=6) for k in range(5)]
        p += sign(M, 'BAND PLAKKEN 5,-', 2.4, 'yellow', 'black')
    elif kind == 'kapper':
        p += room(M, 'wall', 'floor_tile')
        for x in (-1.0, 0.0, 1.0):
            p += [box('mirror', (0.7, 0.04, 0.9), (x, 1.38, 1.5), M['mirror'], smooth=False),
                  box('seat', (0.5, 0.5, 0.15), (x, 0.6, 0.6), M['red'], bevel=0.04), box('back', (0.5, 0.1, 0.6), (x, 0.85, 0.95), M['red'], bevel=0.04),
                  cyl('pole', 0.05, 0.5, (x, 0.6, 0.27), M['steel'], seg=8)]
        p += [cyl('barber_pole', 0.08, 1.2, (-1.5, -1.0, 1.2), M['red'], seg=12), cyl('barber_w', 0.085, 0.3, (-1.5, -1.0, 1.4), M['white'], seg=12)]
    elif kind == 'wine':
        p += room(M, 'wall_dark', 'floor')
        sh, slots = shelves(M, -1.6, 1.6, levels=(0.3, 0.7, 1.1, 1.5, 1.9))
        p += sh + fill(slots, lambda x, y, z, i: bottle(M, x, y, z, i), 0.1)
        p += podium(M, mat='wood') + [box('barrel', (0.5, 0.5, 0.6), (0.9, -1.1, 0.7), M['brown'], bevel=0.1)]
    elif kind == 'travel':
        p += room(M, 'wall', 'floor')
        for k, (x, mat, txt) in enumerate(((-1.0, 'poster_sun', 'ZON!'), (0.0, 'poster_sea', 'ZEE!'), (1.0, 'poster_sun', 'MALLORCA'))):
            p += [box('poster', (0.8, 0.03, 1.1), (x, 1.38, 1.5), M[mat], smooth=False),
                  text_mesh('ptxt', txt, 0.13, (x, 1.35, 1.75), mat=M['white'], extrude=0.004)]
        p += counter(M, 0, 0.4, 2.0, top='white', front='blue')
        p += [box('monitor', (0.4, 0.05, 0.3), (0.3, 0.4, 1.2), M['screen'], smooth=False)]
    else:   # generic: shelves of boxes
        p += room(M, 'wall', 'floor')
        for x0, x1 in ((-1.6, -0.2), (0.2, 1.6)):
            sh, slots = shelves(M, x0, x1)
            p += sh + fill(slots, lambda x, y, z, i: [box('box', (0.2, 0.2, 0.2), (x, y, z + 0.1), M[rng.choice(PALETTE)], bevel=0.01)], 0.26)
    return p


# ================================================================ house windows

def window_scene(M, i):
    """A room seen through a window: wall + a few things, then curtains / vitrage / blinds on top."""
    walls = ['wall', 'wall_blue', 'wall_green', 'wall_pink', 'wall', 'wall_dark', 'wall', 'wall_blue']
    p = [box('back', (3.0, 0.1, 3.0), (0, 1.6, 1.3), M[walls[i]], smooth=False),
         box('floor', (3.0, 3.0, 0.1), (0, 0.5, -0.05), M['floor'], smooth=False),
         box('ceil', (3.0, 3.0, 0.1), (0, 0.5, 2.65), M['white'], smooth=False)]
    for s in (-1, 1):
        p.append(box('side', (0.1, 3.0, 3.0), (s * 1.2, 0.5, 1.3), M[walls[i]], smooth=False))
    # a picture, a lamp, a bookcase or a plant in the room
    if i % 2 == 0:
        p += [box('frame', (0.6, 0.04, 0.45), (0.2, 1.55, 1.5), M['gold'], smooth=False),
              box('picture', (0.52, 0.03, 0.37), (0.2, 1.53, 1.5), M[rng.choice(['blue', 'green', 'orange'])], smooth=False)]
    else:
        sh, slots = shelves(M, -0.9, 0.1, levels=(0.4, 0.9, 1.4), y=1.4, depth=0.3)
        p += sh + fill(slots, lambda x, y, z, k: books(M, x, y, z, k), 0.3)
    p += [tube('cord', (0.3, 0.8, 2.6), (0.3, 0.8, 2.15), 0.01, M['black'], seg=6),
          cyl('shade', 0.22, 0.2, (0.3, 0.8, 2.1), M[rng.choice(['white', 'yellow', 'green'])], r2=0.08, seg=16),
          sphere('bulb', 0.07, (0.3, 0.8, 2.0), M['lamp'], seg=10, rings=5)]
    style = i % 4
    sill = 0.25
    if style == 0:   # Dutch vitrage: a white sheer over the lower half
        p += [box('vitrage', (2.4, 0.02, 1.0), (0, -0.4, sill + 0.5), M['white'], smooth=False)]
        for k in range(9):
            p.append(box('lace', (0.05, 0.01, 0.95), (-1.0 + k * 0.25, -0.415, sill + 0.5), M['cream'], smooth=False))
    elif style == 1:   # curtains, open
        for s in (-1, 1):
            for k in range(4):
                p.append(capsule('curtain', (s * (0.75 + k * 0.08), -0.35, sill), (s * (0.75 + k * 0.08), -0.35, 2.4), 0.07,
                                 mat=M[['red', 'green', 'blue', 'orange'][i // 4 + (i % 2)]], seg=8, rings=4))
    elif style == 2:   # half-closed blinds
        for k in range(12):
            p.append(box('slat', (2.4, 0.02, 0.05), (0, -0.38, 2.3 - k * 0.07), M['white'], rot=(0.5, 0, 0), smooth=False))
    else:   # a plant on the sill and a cat
        p += [cyl('pot', 0.12, 0.18, (-0.4, -0.3, sill + 0.09), M['orange'], seg=12)]
        for k in range(8):
            p.append(ico('leaf', 0.09, (-0.4 + rng.uniform(-0.15, 0.15), -0.3, sill + 0.25 + rng.uniform(0, 0.35)), M['leaf'], subdiv=1))
        p += [sphere('cat', 0.12, (0.4, -0.3, sill + 0.12), M['black'], scale=(1.3, 1, 0.9), seg=12, rings=6),
              sphere('cat_head', 0.08, (0.55, -0.32, sill + 0.24), M['black'], seg=10, rings=5)]
    p += [box('sill', (2.6, 0.4, 0.06), (0, -0.3, sill), M['white'], smooth=False)]
    return p


# ================================================================ render + atlas

def render_cells(builders, w, h, cam_loc, cam_target, lens):
    scene = bpy.context.scene
    lib.set_engine(scene)
    scene.render.resolution_x, scene.render.resolution_y = w, h
    scene.render.film_transparent = False
    ee = scene.eevee
    for attr, val in (('taa_render_samples', 32), ('use_raytracing', True), ('use_shadows', True), ('use_gtao', True)):
        if hasattr(ee, attr):
            setattr(ee, attr, val)
    try:
        scene.view_settings.view_transform = 'AgX'
        scene.view_settings.look = 'AgX - Medium High Contrast'
    except TypeError:
        pass
    world = bpy.data.worlds.new('W')
    scene.world = world
    bg = next(n for n in world.node_tree.nodes if n.type == 'BACKGROUND')
    bg.inputs['Color'].default_value = (0.6, 0.6, 0.6, 1)
    bg.inputs['Strength'].default_value = 0.6
    light = bpy.data.lights.new('fill', 'AREA')
    light.energy, light.size = 400, 3.0
    lo = lib.link(bpy.data.objects.new('fill', light))
    lo.location, lo.rotation_euler = (0, -1.5, 2.6), (math.radians(30), 0, 0)
    cam = lib.camera('cam', cam_loc, cam_target, lens)
    scene.camera = cam
    out = []
    tmp = os.path.join(ROOT, 'renders', 'interiors')
    os.makedirs(tmp, exist_ok=True)
    for k, build in enumerate(builders):
        objs = build()
        path = os.path.join(tmp, f'cell_{w}_{k:02d}.png')
        lib.render(scene, cam, path)
        img = bpy.data.images.load(path)
        out.append(np.array(img.pixels[:]).reshape(h, w, 4)[:, :, :3])
        bpy.data.images.remove(img)
        for o in objs:
            bpy.data.objects.remove(o, do_unlink=True)
    return out


def atlas(cells, cols, rows, path, name):
    h, w, _ = cells[0].shape
    grid = np.zeros((rows * h, cols * w, 3))
    for i, c in enumerate(cells):
        cx, r = i % cols, i // cols
        # image rows go bottom-up in Blender pixels: row 0 of the atlas is the top
        grid[(rows - 1 - r) * h:(rows - r) * h, cx * w:(cx + 1) * w] = c
    import textures
    textures._save(name, grid, path)


def main():
    lib.reset_scene()
    M = mats()
    tex = os.path.join(ROOT, 'assets', 'textures')
    shops = render_cells([lambda k=k: scene(M, k) for k in SHOP_KINDS], SHOP_CELL, SHOP_CELL, (0, -2.7, 1.25), (0, 1.0, 1.05), 26)
    atlas(shops, SHOP_COLS, SHOP_ROWS, os.path.join(tex, 'shop_interiors.png'), 'shop_interiors')
    wins = render_cells([lambda i=i: window_scene(M, i) for i in range(WINDOW_CELLS)], WIN_W, WIN_H, (0, -2.4, 1.3), (0, 1.0, 1.25), 30)
    atlas(wins, WIN_COLS, WIN_ROWS, os.path.join(tex, 'window_interiors.png'), 'window_interiors')
    print('[interiors] written')


if __name__ == '__main__':
    main()
