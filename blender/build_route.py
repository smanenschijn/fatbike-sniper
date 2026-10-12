"""Build the walking route of the adventure mode: the streets between 't Pleintje and the Henri Donutplein.

Same frame as the squares (meters, +Y = "ahead"). You walk (route in godot/scripts/config.gd, ROUTE):
  1. the Winkelstraat north from (0, -6), with an alley on the left (y 8..11.5) and one on the right (y 18..21.5)
  2. right along the south quay of the gracht (y 38..42) to the bridge at x = 20   -> ambush 1 at the bridge
  3. over the bridge and north up the Woonstraat (x 15..25), crossings at y 66..71 (both sides) and y 80..85 (right)
  4. through the gate building (y 96..104) onto the Speelpleintje (y 104..128)       -> ambush 2
  5. north up the exit street (x 17..23), then left into the street (y 168.5..175.5) that becomes the
     Donutplein's east road (that square is placed at DONUT in this frame; see ADVENTURE in config.gd).
The south end is open: 't Pleintje's north street runs straight into the Winkelstraat (this model sits at
(0, 70) in the frame of 't Pleintje).

Run:  Blender -b -P blender/build_route.py [-- --no-render]
"""
import math
import os
import random
import sys

import bpy
from mathutils import Vector

sys.path.insert(0, os.path.dirname(__file__))
import lib  # noqa: E402
import build_square as sq  # noqa: E402  (rows of houses, windows, props)
import build_dunant as dn  # noqa: E402  (materials, frame/put helpers)
from lib import box, cyl, ico, join, material, sphere, tube, torus, text_mesh, extrude_profile, instance  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
V = Vector
rng = random.Random(11)
M = sq.M
EXTRA = []  # loose buildings that aren't made by sq.row

GRACHT = (42.0, 50.0)       # water between these y
BRIDGE_X = (17.5, 22.5)
RAMPS = (5.0, 29.0)         # jump ramps on the north quay (riders leap the gracht in the bridge ambush)
DONUT = (-76.0, 152.5)      # where the Donutplein's origin sits in this frame


def make_materials():
    dn.make_materials()
    M.update({
        'grass': material('Grass', '#5f8c3c', rough=0.95),
        'rubber_tiles': material('RubberTiles', '#b4573f', rough=0.95),
        'sand': material('Sand', '#e3cf98', rough=1.0),
        'water_deep': material('GrachtWater', '#2f4a45', rough=0.04, metal=0.2, coat=1.0),
        'quay_brick': material('QuayBrick', '#6e3f2e', rough=0.9),
        'bridge_white': material('BridgeWhite', '#f1efe8', rough=0.5),
        'hull_green': material('HullGreen', '#2f5b3f', rough=0.5, coat=0.6),
        'hull_blue': material('HullBlue', '#24456e', rough=0.5, coat=0.6),
        'deck_wood': material('DeckWood', '#9a7148', rough=0.7),
        'play_red': material('PlayRed', '#d8382f', rough=0.5),
        'play_yellow': material('PlayYellow', '#f2c230', rough=0.5),
        'play_blue': material('PlayBlue', '#2e7fd0', rough=0.5),
        'steel': material('Steel', '#9aa0a6', rough=0.35, metal=0.8),
    })


# ================================================================ helpers

def row(a, b, facing, depth=9.0, **kw):
    kw.setdefault('prefix', 'Route')
    sq.row(a, b, facing, depth, **kw)


def placed(parts, name, a, b, facing):
    """Join facade-local parts (facade at y=0 facing -Y, x along it) and place them on the line a->b."""
    origin, ang, L = dn.frame(a, b, facing)
    o = join(parts, name)
    dn.put(o, origin, ang)
    lib.box_uv(o, 2.0)
    EXTRA.append(o)
    return o, L


def gate_building():
    """The 'poort': a narrow brick building over the street with a round archway, a date stone and lanterns."""
    L, D, H = 10.0, 8.0, 10.5
    xa, xb, zs = 3.0, 7.0, 2.6     # arch opening (x) and its springing height
    W = M['brick_brown']
    p = []
    prof = [(0, 0), (xa, 0), (xa, zs)] + dn.arch_pts(xa, xb, zs)[1:-1] + [(xb, zs), (xb, 0), (L, 0), (L, H), (0, H)]
    wall = extrude_profile('gate_wall', prof, D, W)
    wall.location = (0, D / 2, 0)
    p.append(wall)
    # passage vault + paving
    vault = extrude_profile('vault', [(xa, zs)] + dn.arch_pts(xa, xb, zs)[1:-1] + [(xb, zs), (xb, zs + 2.2), (xa, zs + 2.2)],
                            D - 0.1, M['ceiling'])
    vault.location = (0, D / 2, -0.04)
    p.append(vault)
    for y in (0.0, D):   # stone arch rings and keystones on both faces
        ring = [(x, z) for x, z in dn.arch_pts(xa - 0.35, xb + 0.35, zs)]
        inner = list(reversed(dn.arch_pts(xa, xb, zs)))
        r = extrude_profile('arch_ring', ring + inner, 0.12, M['stone'])
        r.location = (0, y + (-0.06 if y == 0 else 0.06), 0)
        p.append(r)
        p.append(box('keystone', (0.5, 0.2, 0.7), (L / 2, y + (-0.08 if y == 0 else 0.08), zs + 2.05), M['stone'], smooth=False))
    p.append(box('band', (L, 0.14, 0.18), (L / 2, -0.07, 5.0), M['stone'], smooth=False))
    p.append(box('cornice', (L + 0.3, 0.6, 0.35), (L / 2, D / 2, H + 0.1), M['stone'], smooth=False))
    p.append(box('roof', (L + 0.1, D + 0.1, 0.1), (L / 2, D / 2, H + 0.3), M['stone_dark'], smooth=False))
    for y, sgn in ((0.0, 1), (D, -1)):
        for xc in (2.0, 5.0, 8.0):
            for zc in ((8.9,) if xc == 5.0 else (6.4, 8.9)):
                wp = sq.window(xc, zc, 0.95, 1.6, 'frame_white', shutters='shutter_green' if xc != 5.0 else None)
                if sgn < 0:
                    for o in wp:
                        o.location = (L - o.location.x, D - o.location.y, o.location.z)
                        o.rotation_euler.z += math.pi
                p += wp
        for xc in (1.4, 8.6):
            lx = xc if sgn > 0 else L - xc
            ly = y - 0.25 * sgn
            p.append(box('lantern', (0.22, 0.22, 0.38), (lx, ly, 3.3), M['lamp_glow'], smooth=False))
            p.append(box('lantern_cap', (0.3, 0.3, 0.06), (lx, ly, 3.52), M['iron'], smooth=False))
            p.append(box('lantern_arm', (0.04, 0.3, 0.04), (lx, y - 0.1 * sgn, 3.6), M['iron'], smooth=False))
    p.append(box('datestone', (1.6, 0.06, 0.55), (L / 2, -0.05, 5.65), M['stone_warm'], smooth=False))
    p.append(text_mesh('datetext', 'ANNO 1652', 0.22, (L / 2, -0.09, 5.65), mat=M['stone_dark'], extrude=0.01))
    p.append(box('streetsign', (1.6, 0.04, 0.32), (L / 2, -0.04, 6.5), M['white'], smooth=False))
    p.append(text_mesh('streetsign_t', 'POORTSTEEG', 0.16, (L / 2, -0.07, 6.5), mat=M['sign_blue'], extrude=0.008))
    return p


def quay(y0, y1, x0, x1, name):
    """A quay wall along the water (top at street level), with a stone coping."""
    p = [box(name + '_wall', (x1 - x0, abs(y1 - y0), 1.7), ((x0 + x1) / 2, (y0 + y1) / 2, -0.85), M['quay_brick'], smooth=False),
         box(name + '_coping', (x1 - x0, abs(y1 - y0) + 0.1, 0.12), ((x0 + x1) / 2, (y0 + y1) / 2, 0.04), M['stone'], smooth=False)]
    return p


def bridge():
    """Brick arch bridge over the gracht with white railings (deck flush with the street so riders can cross)."""
    x0, x1 = BRIDGE_X
    y0, y1 = GRACHT[0] - 0.4, GRACHT[1] + 0.4
    p = [box('bridge_deck', (x1 - x0, y1 - y0, 0.3), ((x0 + x1) / 2, (y0 + y1) / 2, -0.15), M['klinkers'], smooth=False)]
    # the arch seen from the water: a profile in the YZ plane, extruded along X
    span0, span1 = GRACHT[0] + 0.6, GRACHT[1] - 0.6
    arc = [(span0 + (span1 - span0) * i / 16, -1.8 + 1.3 * math.sin(math.pi * i / 16)) for i in range(1, 16)]
    pts = [(y0, -0.3), (y0, -1.8), (span0, -1.8)] + arc + [(span1, -1.8), (y1, -1.8), (y1, -0.3)]
    arch = extrude_profile('bridge_arch', [(y, z) for y, z in pts], x1 - x0, M['quay_brick'])
    arch.rotation_euler = (0, 0, math.pi / 2)
    arch.location = ((x0 + x1) / 2, 0, 0)
    p.append(arch)
    for x in (x0 + 0.1, x1 - 0.1):
        p.append(box('rail_top', (0.1, y1 - y0, 0.08), (x, (y0 + y1) / 2, 1.0), M['bridge_white'], smooth=False))
        p.append(box('rail_mid', (0.06, y1 - y0, 0.05), (x, (y0 + y1) / 2, 0.55), M['bridge_white'], smooth=False))
        n = 13
        for i in range(n + 1):
            y = y0 + (y1 - y0) * i / n
            p.append(box('rail_post', (0.1, 0.1, 1.0), (x, y, 0.5), M['bridge_white'], smooth=False))
        for y in (y0, y1):
            p.append(box('rail_end', (0.3, 0.3, 1.25), (x, y, 0.62), M['bridge_white'], smooth=False))
            p.append(sphere('rail_ball', 0.16, (x, y, 1.35), M['bridge_white'], seg=12, rings=6))
    return join(p, 'Bridge')


def boat(name, hull, L=6.5, Wd=2.1, cabin=True):
    p = [sphere('hull', 1.0, (0, 0, 0), M[hull], scale=(L / 2, Wd / 2, 0.55), seg=24, rings=10),
         box('deck', (L * 0.86, Wd * 0.82, 0.06), (0, 0, 0.18), M['deck_wood'], smooth=False),
         box('gunwale', (L * 0.9, Wd * 0.92, 0.12), (0, 0, 0.12), M['white'], smooth=False)]
    for i in range(3):
        p.append(box('bench', (0.3, Wd * 0.75, 0.25), (-L * 0.25 + i * L * 0.2, 0, 0.32), M['deck_wood'], smooth=False))
    if cabin:
        p.append(box('cabin', (L * 0.3, Wd * 0.7, 0.8), (L * 0.18, 0, 0.6), M['white'], smooth=False))
        p.append(box('cabin_win', (L * 0.31, Wd * 0.72, 0.25), (L * 0.18, 0, 0.75), M['glass'], smooth=False))
        p.append(box('cabin_roof', (L * 0.34, Wd * 0.76, 0.06), (L * 0.18, 0, 1.03), M[hull], smooth=False))
    p.append(cyl('outboard', 0.18, 0.6, (-L / 2 - 0.1, 0, 0.3), M['iron'], seg=10))
    return join(p, name)


def prop_slide():
    p = []
    for x in (-0.45, 0.45):
        for y in (0.0, 0.9):
            p.append(tube('post', (x, y, 0), (x, y, 2.3), 0.05, M['steel'], seg=8))
    p.append(box('platform', (1.0, 1.0, 0.08), (0, 0.45, 1.6), M['wood_light'], smooth=False))
    p.append(cyl('roof', 0.85, 0.7, (0, 0.45, 2.65), M['play_red'], seg=4, r2=0.02, rot=(0, 0, math.pi / 4), smooth=False))
    for i in range(6):   # ladder
        p.append(box('rung', (0.8, 0.05, 0.05), (0, 1.0 + i * 0.12, 0.25 + i * 0.25), M['steel'], smooth=False))
    for x in (-0.42, 0.42):
        p.append(tube('ladder_rail', (x, 1.0, 0), (x, 1.75, 1.75), 0.03, M['steel'], seg=6))
    ang = math.atan2(1.55, 2.6)
    p.append(box('slide', (0.7, 3.0, 0.05), (0, -1.3, 0.85), M['play_yellow'], rot=(-ang, 0, 0), smooth=False))
    for x in (-0.37, 0.37):
        p.append(box('slide_side', (0.05, 3.0, 0.22), (x, -1.3, 0.95), M['play_yellow'], rot=(-ang, 0, 0), smooth=False))
    return join(p, 'Slide')


def prop_swing():
    p = []
    for x in (-1.6, 1.6):
        for s in (-1, 1):
            p.append(tube('aframe', (x, s * 0.9, 0), (x, 0, 2.4), 0.06, M['play_blue'], seg=8))
    p.append(tube('beam', (-1.7, 0, 2.4), (1.7, 0, 2.4), 0.07, M['play_blue'], seg=10))
    for x in (-0.7, 0.7):
        for s in (-0.22, 0.22):
            p.append(tube('chain', (x + s, 0, 2.38), (x + s, 0, 0.55), 0.012, M['steel'], seg=4))
        p.append(box('seat', (0.5, 0.2, 0.04), (x, 0, 0.53), M['rubber'], smooth=False))
    return join(p, 'Swing')


def prop_sandbox():
    p = [box('sand', (3.0, 3.0, 0.1), (0, 0, 0.05), M['sand'], smooth=False)]
    for s in (-1, 1):
        p.append(box('edge', (3.2, 0.2, 0.3), (0, s * 1.5, 0.15), M['wood'], smooth=False))
        p.append(box('edge', (0.2, 3.2, 0.3), (s * 1.5, 0, 0.15), M['wood'], smooth=False))
    p.append(cyl('bucket', 0.12, 0.18, (0.6, -0.4, 0.19), M['play_red'], seg=10, r2=0.09))
    p.append(cyl('bucket', 0.12, 0.18, (-0.5, 0.5, 0.19), M['play_blue'], seg=10, r2=0.09))
    return join(p, 'Sandbox')


def prop_seesaw():
    p = [box('base', (0.3, 0.6, 0.45), (0, 0, 0.22), M['play_red'], smooth=False),
         box('plank', (3.2, 0.25, 0.08), (0, 0, 0.5), M['play_yellow'], rot=(0, math.radians(12), 0), smooth=False)]
    for x in (-1.3, 1.3):
        z = 0.5 + math.sin(math.radians(-12)) * x
        p.append(tube('grip', (x, -0.15, z + 0.05), (x, -0.15, z + 0.3), 0.025, M['steel'], seg=6))
        p.append(tube('grip', (x, 0.15, z + 0.05), (x, 0.15, z + 0.3), 0.025, M['steel'], seg=6))
    return join(p, 'Seesaw')


# ================================================================ build

def build():
    lib.reset_scene()
    make_materials()
    sq.BUILDINGS.clear()
    sq.SIDEWALKS.clear()
    root = lib.empty('Route')
    groups = {k: lib.empty(k, parent=root) for k in ('Ground', 'Buildings', 'Props', 'Markers')}

    # --- ground: klinkers on both sides of the gracht, the water in between, the playground in the north
    g0, g1 = GRACHT
    s0 = -7.5                       # 't Pleintje's ground ends here
    dn_y = DONUT[1] - 50.0          # the Donutplein's ground starts here (west of x = DONUT x + 80)
    dn_x = DONUT[0] + 80.0
    g = [box('Ground_South', (130, g0 - s0, 0.2), (0, (g0 + s0) / 2, -0.1), M['klinkers'], smooth=False),
         box('Ground_North_E', (65 - dn_x, 195 - g1, 0.2), ((65 + dn_x) / 2, (195 + g1) / 2, -0.1), M['klinkers'], smooth=False),
         box('Ground_North_W', (dn_x + 65, dn_y - g1, 0.2), ((dn_x - 65) / 2, (dn_y + g1) / 2, -0.1), M['klinkers'], smooth=False),
         box('Shopstreet_Tiles', (6.0, 51, 0.04), (0, 11.5, 0.0), M['tegels'], smooth=False),
         box('Playground_Grass', (24.0, 20.0, 0.05), (20.0, 116.0, 0.0), M['grass'], smooth=False),
         box('Playground_Path', (4.0, 24.0, 0.07), (20.0, 116.0, 0.0), M['tegels'], smooth=False),
         box('Playground_PathX', (28.0, 4.0, 0.07), (20.0, 116.0, 0.0), M['tegels'], smooth=False),
         box('Rubber_Slide', (4.5, 6.5, 0.06), (13.5, 122.0, 0.0), M['rubber_tiles'], smooth=False),
         box('Rubber_Swing', (5.0, 4.0, 0.06), (26.0, 123.5, 0.0), M['rubber_tiles'], smooth=False),
         box('Rubber_Seesaw', (4.5, 3.0, 0.06), (13.5, 109.5, 0.0), M['rubber_tiles'], smooth=False)]
    for o in g:
        lib.box_uv(o, 2.0)
    water = [box('Gracht_Bed', (130, g1 - g0, 0.2), (0, (g0 + g1) / 2, -1.8), M['stone_dark'], smooth=False),
             box('Gracht_Water', (130, g1 - g0, 0.04), (0, (g0 + g1) / 2, -0.95), M['water_deep'], smooth=False)]
    water += quay(g0 - 0.5, g0, -65, 65, 'QuaySouth') + quay(g1, g1 + 0.5, -65, 65, 'QuayNorth')
    for o in g + water:
        lib.set_parent(o, groups['Ground'])

    # --- 1. the Winkelstraat (shops on both sides, alleys left and right)
    row((-5, -14), (-5, 8), (1, 0), 10, floors=(2, 3), shop_chance=0.85, prefix='Winkel')
    row((-5, 11.5), (-5, 36), (1, 0), 10, floors=(2, 3), shop_chance=0.85, prefix='Winkel')
    row((5, -14), (5, 18), (-1, 0), 10, floors=(2, 3), shop_chance=0.85, prefix='Winkel')
    row((5, 21.5), (5, 36), (-1, 0), 10, floors=(2, 3), shop_chance=0.85, prefix='Winkel')
    # alley left (west), alley right (east)
    row((-15.2, 8), (-38, 8), (0, 1), 7, floors=(2, 3), shop_chance=0.1, widths=(4.0, 5.5), prefix='SteegW')
    row((-15.2, 11.5), (-38, 11.5), (0, -1), 7, floors=(2, 3), shop_chance=0.1, widths=(4.0, 5.5), prefix='SteegW')
    row((-38, 8), (-38, 11.5), (1, 0), 7, floors=(2, 2), shop_chance=0.0, widths=(3.5, 3.5), sidewalk=False, prefix='SteegW')
    row((15.2, 18), (38, 18), (0, 1), 7, floors=(2, 3), shop_chance=0.1, widths=(4.0, 5.5), prefix='SteegE')
    row((15.2, 21.5), (38, 21.5), (0, -1), 7, floors=(2, 3), shop_chance=0.1, widths=(4.0, 5.5), prefix='SteegE')
    row((38, 18), (38, 21.5), (-1, 0), 7, floors=(2, 2), shop_chance=0.0, widths=(3.5, 3.5), sidewalk=False, prefix='SteegE')

    # --- 2. the gracht: tall canal houses on both quays, closed off at both ends
    row((-60, 36), (-5, 36), (0, 1), 10, floors=(3, 4), shop_chance=0.15, prefix='Gracht')
    row((5, 36), (60, 36), (0, 1), 10, floors=(3, 4), shop_chance=0.15, prefix='Gracht')
    row((-60, 55), (15, 55), (0, -1), 10, floors=(3, 4), shop_chance=0.1, prefix='Gracht')
    row((25, 55), (60, 55), (0, -1), 10, floors=(3, 4), shop_chance=0.1, prefix='Gracht')
    row((-60, 30), (-60, 62), (1, 0), 9, shop_chance=0.0, sidewalk=False, prefix='Gracht')
    row((60, 30), (60, 62), (-1, 0), 9, shop_chance=0.0, sidewalk=False, prefix='Gracht')

    # --- 3. the Woonstraat: terraced houses, a crossroads and a side street on the right
    row((15, 55), (15, 66), (1, 0), 9, floors=(2, 3), shop_chance=0.15, prefix='Woon')
    row((15, 71), (15, 96), (1, 0), 9, floors=(2, 3), shop_chance=0.05, prefix='Woon')
    row((25, 55), (25, 66), (-1, 0), 9, floors=(2, 3), shop_chance=0.15, prefix='Woon')
    row((25, 71), (25, 80), (-1, 0), 9, floors=(2, 3), shop_chance=0.05, prefix='Woon')
    row((25, 85), (25, 96), (-1, 0), 9, floors=(2, 3), shop_chance=0.05, prefix='Woon')
    for (xa, xb) in ((5.8, -26), (34.2, 56)):   # the crossroads (y 66..71), both ways
        row((xa, 66), (xb, 66), (0, 1), 7, floors=(2, 3), shop_chance=0.1, widths=(4.0, 6.0), prefix='Kruis')
        row((xa, 71), (xb, 71), (0, -1), 7, floors=(2, 3), shop_chance=0.1, widths=(4.0, 6.0), prefix='Kruis')
        row((xb, 66), (xb, 71), (1 if xb < 0 else -1, 0), 7, floors=(2, 2), shop_chance=0.0, widths=(5, 5), sidewalk=False, prefix='Kruis')
    row((34.2, 80), (56, 80), (0, 1), 7, floors=(2, 3), shop_chance=0.0, widths=(4.0, 6.0), prefix='Zij')
    row((34.2, 85), (56, 85), (0, -1), 7, floors=(2, 3), shop_chance=0.0, widths=(4.0, 6.0), prefix='Zij')
    row((56, 80), (56, 85), (-1, 0), 7, floors=(2, 2), shop_chance=0.0, widths=(5, 5), sidewalk=False, prefix='Zij')

    # --- 4. the gate building and the Speelpleintje behind it
    placed(gate_building(), 'Poort', (15, 96), (25, 96), (0, -1))
    row((6, 104), (15, 104), (0, 1), 7, floors=(2, 3), shop_chance=0.0, sidewalk=False, prefix='Speel')
    row((25, 104), (34, 104), (0, 1), 7, floors=(2, 3), shop_chance=0.0, sidewalk=False, prefix='Speel')
    row((6, 104), (6, 113), (1, 0), 9, floors=(2, 3), shop_chance=0.2, prefix='Speel')
    row((6, 119), (6, 128), (1, 0), 9, floors=(2, 3), shop_chance=0.2, prefix='Speel')
    row((34, 104), (34, 113), (-1, 0), 9, floors=(2, 3), shop_chance=0.2, prefix='Speel')
    row((34, 119), (34, 128), (-1, 0), 9, floors=(2, 3), shop_chance=0.2, prefix='Speel')
    row((6, 128), (17, 128), (0, -1), 9, floors=(2, 3), shop_chance=0.3, prefix='Speel')
    row((23, 128), (34, 128), (0, -1), 9, floors=(2, 3), shop_chance=0.3, prefix='Speel')
    for (xa, xb) in ((-3.2, -22), (43.2, 62)):  # side streets off the playground (y 113..119)
        row((xa, 113), (xb, 113), (0, 1), 7, floors=(2, 3), shop_chance=0.0, widths=(4.0, 6.0), prefix='SpeelZij')
        row((xa, 119), (xb, 119), (0, -1), 7, floors=(2, 3), shop_chance=0.0, widths=(4.0, 6.0), prefix='SpeelZij')
        row((xb, 113), (xb, 119), (1 if xb < 0 else -1, 0), 7, floors=(2, 2), shop_chance=0.0, widths=(6, 6), sidewalk=False, prefix='SpeelZij')
    # the way out north, then left into the street that becomes the Donutplein's east road
    ey0, ey1 = DONUT[1] + 16.0, DONUT[1] + 23.0
    ex = DONUT[0] + 60.0
    row((17, 137.2), (17, ey0 - 9.0), (1, 0), 8, floors=(2, 3), shop_chance=0.4, prefix='Uit')
    row((23, 137.2), (23, ey1), (-1, 0), 8, floors=(2, 3), shop_chance=0.4, prefix='Uit')
    row((ex, ey0), (17, ey0), (0, 1), 9, floors=(2, 3), shop_chance=0.3, prefix='Oost')
    row((ex, ey1), (23, ey1), (0, -1), 9, floors=(2, 3), shop_chance=0.3, prefix='Oost')

    EXTRA.append(bridge())
    for o in sq.BUILDINGS + EXTRA:
        lib.set_parent(o, groups['Buildings'])
    sw = join(sq.SIDEWALKS, 'Ground_Sidewalks')
    lib.box_uv(sw, 1.8)
    lib.set_parent(sw, groups['Ground'])

    # --- props
    props = []
    P = lambda src, loc, rz=0.0, s=1.0: props.append(instance(src, src.name + '_i', loc, rz, s))
    tree, lamp, bollard, bench, binm, planter, rack = (sq.prop_tree(), sq.prop_lamp(), sq.prop_bollard(), sq.prop_bench(),
                                                         sq.prop_bin(), sq.prop_planter(), sq.prop_rack())
    bikes = [sq.prop_omafiets(f) for f in ('bike_black', 'bike_green', 'bike_blue', 'bike_red')]
    slide, swing, sandbox, seesaw = prop_slide(), prop_swing(), prop_sandbox(), prop_seesaw()
    boats = [boat('Sloep_Green', 'hull_green'), boat('Sloep_Blue', 'hull_blue', 5.5, 1.9, cabin=False)]
    templates = [tree, lamp, bollard, bench, binm, planter, rack, slide, swing, sandbox, seesaw] + bikes + boats

    # Winkelstraat: planters, lamps, bins, bunting overhead, a bike leaning here and there
    for y in (-2.0, 14.0, 27.0):
        P(planter, (-2.6, y, 0)); P(planter, (2.6, y + 5, 0))
    for y in (2.0, 22.0):
        P(lamp, (-2.9, y, 0)); P(lamp, (2.9, y + 6, 0))
    for y in (6.0, 30.5):
        P(binm, (2.8, y, 0))
    for y in (3.0, 16.0, 29.0):
        props.append(sq.bunting((-5, y, 6.4), (5, y + 1.5, 6.4), 0.9, f'Bunting_{y:.0f}'))
    for (x, y, rz) in ((-3.4, 5.0, math.pi / 2), (3.5, 12.5, math.pi / 2), (-3.4, 24.0, math.pi / 2)):
        P(rng.choice(bikes), (x, y, 0), rz + rng.uniform(-0.1, 0.1))

    # the gracht: trees and bollards along both quays, bikes against the bridge, boats on the water
    near_ramp = lambda x, d: any(abs(x - rx) < d for rx in RAMPS)
    for x in range(-55, 58, 8):
        if not (BRIDGE_X[0] - 3 < x < BRIDGE_X[1] + 3) and abs(x) > 4 and not near_ramp(x, 3.5):
            P(tree, (x, g0 - 0.9, 0), rng.uniform(0, 6.28), rng.uniform(0.85, 1.0))
        if not (BRIDGE_X[0] - 3 < x + 4 < BRIDGE_X[1] + 3) and not near_ramp(x + 4, 3.5):
            P(tree, (x + 4, g1 + 1.4, 0), rng.uniform(0, 6.28), rng.uniform(0.85, 1.0))
    for x in range(-58, 60, 2):
        if not (BRIDGE_X[0] - 0.5 < x < BRIDGE_X[1] + 0.5) and not near_ramp(x, 2.0):
            P(bollard, (x, g0 - 0.35, 0)); P(bollard, (x, g1 + 0.35, 0))
    for rx in RAMPS:   # a plywood jump ramp on the north quay, pointing over the water
        ramp = extrude_profile('ramp', [(g1 + 2.6, 0.0), (g1 + 0.1, 0.0), (g1 + 0.1, 0.75)], 2.2, M['deck_wood'])
        ramp.rotation_euler = (0, 0, math.pi / 2)
        ramp.location = (rx, 0, 0)
        stripes = [ramp]
        for k in (-1, 1):
            stripes.append(box('ramp_stripe', (0.12, 2.6, 0.02), (rx + k * 0.8, g1 + 1.35, 0.39), M['play_yellow'],
                               rot=(math.atan2(0.75, 2.5), 0, 0), smooth=False))
        props.append(join(stripes, f'JumpRamp_{rx:.0f}'))
    for (x, y) in ((-20, g0 - 1.6), (34, g0 - 1.6), (8, g1 + 1.6), (40, g1 + 1.6)):
        P(lamp, (x, y, 0))
    for (x, y) in ((-10, g0 - 2.8), (30, g1 + 2.6)):
        P(bench, (x, y, 0), 0.0 if y < 45 else math.pi)
    for k in range(4):   # bikes parked on the quay next to the bridge
        P(bikes[k % 4], (BRIDGE_X[0] - 6.5 - k * 0.75, g0 - 1.1, 0), math.pi / 2 + rng.uniform(-0.12, 0.12))
    for (x, b, rz) in ((-12.0, 0, 0.02), (6.0, 1, -0.03), (38.0, 0, 0.05), (-36.0, 1, 0.0)):
        P(boats[b], (x, g0 + 1.5 if b == 0 else g1 - 1.4, -0.9), rz)

    # Woonstraat: trees in the pavement, parked bikes, bins
    for y in (60.0, 76.0, 90.0):
        P(tree, (16.6, y, 0), rng.uniform(0, 6.28), 0.8); P(tree, (23.4, y + 3, 0), rng.uniform(0, 6.28), 0.8)
    for (x, y) in ((16.3, 74.0), (23.7, 62.0), (23.7, 88.0)):
        P(rng.choice(bikes), (x, y, 0), math.pi / 2 + rng.uniform(-0.1, 0.1))
    for (x, y) in ((16.4, 92.5), (23.6, 72.6)):
        P(binm, (x, y, 0))

    # Speelpleintje: slide, swings, sandbox, seesaw, benches round the edge, trees on the grass
    P(slide, (14.5, 122.0, 0), 0.0)
    P(swing, (26.0, 123.5, 0), 0.0)
    P(sandbox, (25.5, 109.5, 0))
    P(seesaw, (14.0, 109.5, 0), 0.3)
    for (x, y) in ((9.5, 108.0), (9.5, 124.0), (30.5, 108.0), (30.5, 124.0)):
        P(tree, (x, y, 0), rng.uniform(0, 6.28), 0.9)
    for (x, y, rz) in ((8.2, 116.0, -math.pi / 2), (31.8, 116.0, math.pi / 2)):
        P(bench, (x, y, 0), rz)
    for (x, y) in ((11.0, 105.5), (29.0, 126.5)):
        P(lamp, (x, y, 0))
    P(binm, (12.0, 113.0, 0))

    for o in props:
        lib.set_parent(o, groups['Props'])
    for t in templates:
        t.location = (0, 0, -100)

    # --- markers for the game
    markers = {'PlayerEye': (0, -6, 1.6), 'Bridge': ((BRIDGE_X[0] + BRIDGE_X[1]) / 2, 46, 0), 'Playground': (20, 116, 0)}
    for name, loc in markers.items():
        lib.empty(name, loc, parent=groups['Markers'])
    return root, templates


def main():
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    root, templates = build()
    scene = bpy.context.scene
    objs = [root] + list(root.children_recursive)
    meshes = [o for o in objs if o.type == 'MESH']
    print(f'[route] buildings: {len(sq.BUILDINGS) + len(EXTRA)}, objects: {len(objs)}, triangles: {lib.tri_count(meshes)}')
    out = os.path.join(ROOT, 'assets', 'models', 'route.glb')
    lib.export_glb(out, objs)
    print(f'[route] exported {out} ({os.path.getsize(out) / 1e6:.1f} MB)')
    for t in templates:
        t.hide_render = True
    if '--no-render' in argv:
        return
    lib.preview_stage(scene, size=(1600, 900))
    bpy.data.objects['PreviewGround'].hide_render = True
    sun = bpy.data.objects['Sun']
    sun.rotation_euler = (math.radians(55), 0, math.radians(-40))
    sun.data.energy = 6.0
    bpy.data.objects['Fill'].hide_render = True
    rdir = os.path.join(ROOT, 'renders', 'route')
    shots = [
        ('01_overview', (-30, -30, 90), (15, 60, 0), 22),
        ('02_winkelstraat', (0, -6, 1.6), (0, 30, 2.0), 22),
        ('03_gracht', (2, 39.5, 1.6), (20, 46, 1.0), 22),
        ('04_bridge_ambush', (15, 39.5, 1.6), (20, 52, 1.5), 22),
        ('05_woonstraat', (20, 54, 1.6), (20, 96, 2.5), 22),
        ('06_poort', (20, 88, 1.6), (20, 104, 2.5), 22),
        ('07_speelplein', (20, 106, 1.6), (20, 128, 1.5), 20),
        ('08_ramps', (15, 39.8, 1.6), (12, 50, 1.0), 20),
        ('09_east', (20, 150, 1.6), (12, 172, 1.5), 22),
    ]
    if 'one' in argv:
        shots = shots[:2]
    picks = [a for a in argv if a[:2].isdigit()]
    if picks:
        shots = [s for s in shots if s[0][:2] in picks]
    for name, loc, tgt, lens in shots:
        lib.render(scene, lib.camera('Cam_' + name, tuple(loc), tuple(tgt), lens), os.path.join(rdir, name + '.png'))


if __name__ == '__main__':
    main()
