"""Build the Wollahbi square: the entrance plaza of a theme park, after the Walibi entrance.

Same frame as the other squares (meters, +Y = ahead): you sit at (0, -11.55) on the terrace of the ice cream kiosk
on the south side, looking north at the yellow art-deco gate with the big red W. In front of you the round
fountain with its arching jets and a ring of red geraniums; left and right the red/yellow ticket buildings with
their dark drum towers, the turnstile roofs in between. Behind the gate: the park with the roller coaster
"De Gillende Gozer" (lift hill, drop, looping), towering over the gate.

Entries (see godot/scripts/config.gd): through the gate and both turnstile lanes from the park promenade
(y 33..38), and the lanes west and east (y 0.5..6).
The game reads the coaster from the markers Track_### (every ~2 m, in order of travel; '_lift' on the
chain lift, '_station' in the station) and animates copies of CoasterCar along it.

Adventure mode: this model sits north-east of the Donutplein (see ADVENTURE.frames in config.gd). You arrive
up the Donutplein's market road (x = -57.8 here), walk the park promenade east (y = 30) and turn south
through the gate. Everything west of x = -45 below y = 20 is the Donutplein's own ground.

Run:  Blender -b -P blender/build_wollahbi.py [-- --no-render]
"""
import math
import os
import random
import sys

import bpy
from mathutils import Vector

sys.path.insert(0, os.path.dirname(__file__))
import lib  # noqa: E402
import build_square as sq  # noqa: E402  (props)
import build_dunant as dn  # noqa: E402  (helpers, market props)
import build_route as rt  # noqa: E402  (materials)
from lib import box, cyl, ico, join, material, sphere, tube, torus, text_mesh, extrude_profile, instance  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
V = Vector
rng = random.Random(23)
M = sq.M
BUILDINGS = []

FOUNTAIN = V((0.0, 2.0))
GATE_Y = 18.0          # front face of the gate / turnstile line
PROM = (28.0, 38.0)    # the park promenade behind the gate (walk at y 30, rider lanes at y 33..38)


def make_materials():
    rt.make_materials()
    M.update({
        'w_yellow': material('WollahbiYellow', '#f5b62a', rough=0.55),
        'w_yellow_lt': material('WollahbiYellowLight', '#f8cc4a', rough=0.6),
        'w_red': material('WollahbiRed', '#d6261c', rough=0.4, coat=0.3),
        'w_darkred': material('WollahbiDarkRed', '#8c1912', rough=0.45),
        'w_olive': material('WollahbiOlive', '#9aa63a', rough=0.55),
        'w_slate': material('WollahbiSlate', '#34363b', rough=0.5, metal=0.3),
        'w_silver': material('WollahbiSilver', '#c9ccd1', rough=0.3, metal=0.8),
        'pool': material('PoolWater', '#3cbab2', rough=0.03, coat=1.0, emission='#2a9a96', strength=0.12),
        'pool_floor': material('PoolFloor', '#2a8790', rough=0.6),
        'foam': material('Foam', '#f2fbfd', rough=0.3, emission='#dff3ff', strength=0.25),
        'hedge': material('Hedge', '#3d6b2a', rough=0.9, sheen=0.3),
        'track': material('TrackRed', '#d42a1f', rough=0.35, metal=0.4),
        'support': material('CoasterSupport', '#ecebe6', rough=0.4, metal=0.3),
        'car_blue': material('CarBlue', '#2468d0', rough=0.3, coat=0.8),
        'skin_a': material('GuestSkinA', '#e7b48f', rough=0.6),
        'skin_b': material('GuestSkinB', '#8a5536', rough=0.6),
    })


def place_at(o, c):
    o.location = (c.x, c.y, 0)
    return o


def ok(o, tile=2.0):
    lib.box_uv(o, tile)
    return o


# ================================================================ the gate

def w_logo(name, width, z, y, mat, outline=None, out_dir=-1):
    """The big W of the logo (in the XZ plane at depth y), on a slightly bigger outline just behind it."""
    s = width / 6.0
    pts = [(-3, 4), (-1.9, 4), (-1.2, 1.7), (-0.45, 4), (0.45, 4), (1.2, 1.7), (1.9, 4), (3, 4),
           (1.8, 0), (0.8, 0), (0, 2.3), (-0.8, 0), (-1.8, 0)]
    w = extrude_profile(name, [(x * s, z + h * s) for x, h in pts], 0.25, M[mat])
    w.location = (0, y, 0)
    p = [w]
    if outline:
        k = 1.13
        o = extrude_profile(name + '_outline', [(x * s * k, z + (2 + (h - 2) * k) * s) for x, h in pts], 0.2, M[outline])
        o.location = (0, y - out_dir * 0.1, 0)
        p.append(o)
    return p


def gate():
    """Stepped yellow art-deco tower with a round arch you can ride through, red pilaster stripes, the W and the name."""
    y0, y1 = GATE_Y, GATE_Y + 4.0
    D = y1 - y0
    hw, aw, zs = 5.0, 2.6, 6.0      # half width, half arch width, arch springing height
    arch = dn.arch_pts(-aw, aw, zs, 18)
    # silhouette: shoulders, then the stepped crown with a rounded top
    top = [(hw, 11.0), (4.2, 11.0), (4.2, 13.0), (3.4, 13.0), (3.4, 15.0), (2.6, 15.0), (2.6, 16.6)]
    crown = [(2.6 * math.cos(math.pi * i / 10), 16.6 + 1.6 * math.sin(math.pi * i / 10)) for i in range(1, 10)]
    left = [(-x, z) for x, z in reversed(top)]
    prof = [(-hw, 0), (-aw, 0), (-aw, zs)] + arch[1:-1] + [(aw, zs), (aw, 0), (hw, 0)] + top + crown + left
    p = []
    body = extrude_profile('gate_body', prof, D, M['w_yellow'])
    body.location = (0, (y0 + y1) / 2, 0)
    p.append(body)
    # lower fins either side, stepping down
    for s in (-1, 1):
        for (x0, x1, h) in ((hw, hw + 0.9, 9.0), (hw + 0.9, hw + 1.7, 6.2)):
            p.append(box('gate_fin', (x1 - x0, D - 0.6, h), (s * (x0 + x1) / 2, (y0 + y1) / 2, h / 2), M['w_yellow'], smooth=False))
            p.append(box('fin_cap', (x1 - x0 + 0.1, D - 0.5, 0.2), (s * (x0 + x1) / 2, (y0 + y1) / 2, h + 0.1), M['w_yellow_lt'], smooth=False))
        # red stripes on the pilasters (both faces)
        for yy in (y0 - 0.04, y1 + 0.04):
            for x, z0, z1 in ((3.6, 0.6, 11.0), (4.4, 0.6, 10.2), (hw + 0.45, 0.6, 8.6)):
                p.append(box('gate_stripe', (0.22, 0.08, z1 - z0), (s * x, yy, (z0 + z1) / 2), M['w_red'], smooth=False))
            p.append(box('crown_stripe', (0.18, 0.08, 4.0), (s * 3.0, yy, 13.6), M['w_red'], smooth=False))
    # olive band round the arch and an olive reveal inside, a darker plinth
    for yy, sgn in ((y0, -1), (y1, 1)):
        ring = extrude_profile('arch_band', dn.arch_pts(-aw - 0.45, aw + 0.45, zs, 18) + list(reversed(arch)), 0.14, M['w_olive'])
        ring.location = (0, yy + 0.07 * sgn, 0)
        p.append(ring)
        for s in (-1, 1):
            p.append(box('arch_jamb', (0.45, 0.14, zs), (s * (aw + 0.22), yy + 0.07 * sgn, zs / 2), M['w_olive'], smooth=False))
    vault = extrude_profile('gate_vault', [(-aw, zs)] + arch[1:-1] + [(aw, zs), (aw, zs + 3.0), (-aw, zs + 3.0)], D - 0.1, M['w_yellow_lt'])
    vault.location = (0, (y0 + y1) / 2, -0.03)
    p.append(vault)
    p.append(box('gate_plinth', (2 * hw + 3.6, D + 0.3, 0.45), (0, (y0 + y1) / 2, 0.22), M['w_darkred'], smooth=False))
    # the logo and the name, front and back
    for yy, sgn in ((y0, -1), (y1, 1)):
        for o in w_logo('gate_W', 6.2, 11.4, yy + 0.2 * sgn, 'w_red', 'w_darkred', sgn):
            p.append(o)
        t = text_mesh('gate_name', 'WOLLAHBI', 1.55, (0, yy + 0.1 * sgn, 9.45), mat=M['w_red'], extrude=0.08)
        if sgn > 0:
            t.rotation_euler.z = math.pi
        p.append(t)
        t2 = text_mesh('gate_name_shadow', 'WOLLAHBI', 1.55, (0.07 * -sgn, yy + 0.04 * sgn, 9.38), mat=M['w_darkred'], extrude=0.04)
        if sgn > 0:
            t2.rotation_euler.z = math.pi
        p.append(t2)
    o = ok(join(p, 'Gate'))
    BUILDINGS.append(o)
    # flower boxes at the foot of the gate (as on the photo)
    fl = []
    for s in (-1, 1):
        cx = s * (hw + 1.5)
        fl.append(box('gate_planter', (3.0, 1.0, 0.5), (cx, y0 - 0.9, 0.25), M['w_yellow'], smooth=False))
        for _ in range(26):
            fl.append(ico('gp_leaf', rng.uniform(0.1, 0.16), (cx + rng.uniform(-1.3, 1.3), y0 - 0.9 + rng.uniform(-0.35, 0.35), 0.58), M['leaf'], subdiv=1))
        for _ in range(26):
            fl.append(ico('gp_bloom', rng.uniform(0.05, 0.08), (cx + rng.uniform(-1.35, 1.35), y0 - 0.9 + rng.uniform(-0.4, 0.4), 0.66 + rng.uniform(0, 0.1)),
                          M[rng.choice(['flower_red', 'flower_red', 'flower_yellow'])], subdiv=1))
    BUILDINGS.append(join(fl, 'Gate_Flowers'))
    return o


def turnstiles(s):
    """Between the gate and a ticket building: a dark canopy with silver trim over rows of turnstiles,
    with a lane in the middle (x = 10) the riders use."""
    x0, x1 = s * 6.8, s * 16.0
    xa, xb = min(x0, x1), max(x0, x1)
    L = xb - xa
    cx = (xa + xb) / 2
    y0, y1 = GATE_Y - 0.5, GATE_Y + 4.5
    p = [box('ts_roof', (L, y1 - y0, 1.8), (cx, (y0 + y1) / 2, 4.9), M['w_slate'], smooth=False),
         box('ts_trim', (L + 0.1, 0.1, 0.25), (cx, y0 - 0.05, 4.1), M['w_silver'], smooth=False),
         box('ts_trim', (L + 0.1, 0.1, 0.12), (cx, y0 - 0.05, 5.7), M['w_silver'], smooth=False),
         box('ts_trim_b', (L + 0.1, 0.1, 0.25), (cx, y1 + 0.05, 4.1), M['w_silver'], smooth=False),
         box('ts_floor', (L, y1 - y0, 0.06), (cx, (y0 + y1) / 2, 0.04), M['slabs'], smooth=False)]
    for x in (xa + 0.2, xb - 0.2):
        for y in (y0 + 0.2, y1 - 0.2):
            p.append(tube('ts_post', (x, y, 0), (x, y, 4.0), 0.1, M['w_silver'], seg=10))
    lane = s * 10.0
    for k in range(int(L / 1.1) + 1):
        x = xa + 0.6 + k * 1.1
        if abs(x - lane) < 1.6 or x > xb - 0.4:
            continue
        y = GATE_Y + 2.0
        p.append(box('ts_body', (0.3, 0.9, 1.0), (x, y, 0.5), M['w_silver'], smooth=False))
        for a in range(3):
            ang = a * 2 * math.pi / 3
            p.append(tube('ts_arm', (x + 0.15, y, 0.85), (x + 0.15 + 0.5 * math.cos(ang) * 0.3, y + 0.5 * math.cos(ang),
                                                            0.85 + 0.5 * math.sin(ang)), 0.025, M['w_silver'], seg=6))
        p.append(tube('ts_rail', (x - 0.4, y - 0.6, 0.95), (x - 0.4, y + 0.6, 0.95), 0.03, M['w_silver'], seg=6))
    # a red banner on the barrier in front: the coaster is open
    bx = s * 13.0
    p.append(box('banner', (2.6, 0.06, 0.9), (bx, y0 - 1.6, 0.85), M['w_red'], smooth=False))
    for x in (bx - 1.25, bx + 1.25):
        p.append(tube('banner_leg', (x, y0 - 1.6, 0), (x, y0 - 1.6, 1.3), 0.03, M['w_silver'], seg=6))
    p.append(text_mesh('banner_t', 'ACHTBAAN OPEN', 0.22, (bx, y0 - 1.64, 0.9), mat=M['white'], extrude=0.01))
    o = ok(join(p, 'Turnstiles_' + ('E' if s > 0 else 'W')))
    BUILDINGS.append(o)
    return o


def ticket_building(s):
    """Red/yellow ticket office: yellow ground floor with ticket windows, a red band, red upper storey with a
    yellow stripe, a dark cornice, and a dark drum tower with ribbon windows at the inner corner."""
    xi, xo = s * 16.0, s * 34.0
    xa, xb = min(xi, xo), max(xi, xo)
    L = xb - xa
    cx = (xa + xb) / 2
    y0, y1 = 6.5, 24.0
    cy = (y0 + y1) / 2
    D = y1 - y0
    p = [box('tb_lower', (L, D, 4.0), (cx, cy, 2.0), M['w_yellow'], smooth=False),
         box('tb_band', (L + 0.4, D + 0.4, 0.6), (cx, cy, 4.3), M['w_red'], smooth=False),
         box('tb_upper', (L, D, 3.2), (cx, cy, 6.2), M['w_red'], smooth=False),
         box('tb_stripe', (L - 2.0, 0.1, 0.9), (cx, y0 - 0.05, 6.1), M['w_yellow_lt'], smooth=False),
         box('tb_stripe_s', (0.1, D - 2.0, 0.9), (xi - s * 0.05, cy, 6.1), M['w_yellow_lt'], smooth=False),
         box('tb_cornice', (L + 0.6, D + 0.6, 0.35), (cx, cy, 7.95), M['w_slate'], smooth=False),
         box('tb_cornice_trim', (L + 0.7, D + 0.7, 0.08), (cx, cy, 7.75), M['w_silver'], smooth=False),
         box('tb_plinth', (L + 0.1, D + 0.1, 0.35), (cx, cy, 0.17), M['w_darkred'], smooth=False),
         box('tb_roof', (L, D, 0.1), (cx, cy, 8.15), M['gravel'], smooth=False)]
    # ticket windows with a W board above each, facing the plaza
    n = 4
    for k in range(n):
        x = xa + L * (k + 0.5) / n
        p.append(box('tw_glass', (1.6, 0.06, 1.3), (x, y0 - 0.03, 1.75), M['glass'], smooth=False))
        p.append(box('tw_frame', (1.9, 0.12, 0.12), (x, y0 - 0.06, 2.45), M['w_red'], smooth=False))
        p.append(box('tw_sill', (1.9, 0.5, 0.08), (x, y0 - 0.25, 1.05), M['w_silver'], smooth=False))
        p.append(box('tw_board', (1.0, 0.06, 0.8), (x, y0 - 0.05, 3.2), M['w_red'], smooth=False))
        for o in w_logo('tw_W', 0.7, 2.95, y0 - 0.12, 'w_yellow_lt'):
            o.location.x += x
            o.scale.y = 0.2
            p.append(o)
    p.append(text_mesh('tb_name', 'KASSA', 0.55, (cx, y0 - 0.12, 6.1), mat=M['w_red'], extrude=0.03))
    # yellow awning over the outer windows
    p.append(box('tb_awning', (L * 0.45, 1.6, 0.12), (xo - s * L * 0.25, y0 - 0.8, 3.55), M['w_yellow_lt'], rot=(math.radians(-12), 0, 0), smooth=False))
    # the drum tower at the inner corner
    tx, ty = xi + s * 2.6, y0 + 3.4
    p.append(cyl('drum', 3.0, 9.6, (tx, ty, 4.8), M['w_slate'], seg=24))
    for z in (5.3, 7.3):
        p.append(cyl('drum_glass', 3.04, 1.2, (tx, ty, z), M['glass'], seg=24))
    for z in (4.6, 6.6, 8.6, 9.6):
        p.append(cyl('drum_ring', 3.1, 0.12, (tx, ty, z), M['w_silver'], seg=24))
    p.append(cyl('drum_cap', 3.2, 0.3, (tx, ty, 9.75), M['w_slate'], seg=24))
    p.append(cyl('drum_base', 3.08, 4.0, (tx, ty, 2.0), M['w_yellow'], seg=24))
    p.append(cyl('drum_band', 3.25, 0.6, (tx, ty, 4.3), M['w_red'], seg=24))
    o = ok(join(p, 'Kassa_' + ('E' if s > 0 else 'W')))
    BUILDINGS.append(o)
    return o


def queue_wall(s):
    """The curved low yellow wall with a railing in front of a ticket building (the queue on the photo)."""
    p = []
    c = V((s * 21.0, 6.5))
    R = 4.0
    pts = []
    for i in range(13):
        a = math.pi + math.pi * i / 12
        pts.append(c + V((math.cos(a) * R * 1.6, math.sin(a) * R * 0.55)))
    for a, b in zip(pts, pts[1:]):
        m = (a + b) / 2
        d = b - a
        p.append(box('qw', (d.length + 0.05, 0.35, 0.9), (m.x, m.y, 0.45), M['w_yellow'], rot=(0, 0, math.atan2(d.y, d.x)), smooth=False))
        p.append(box('qw_cap', (d.length + 0.05, 0.45, 0.08), (m.x, m.y, 0.94), M['w_darkred'], rot=(0, 0, math.atan2(d.y, d.x)), smooth=False))
        p.append(tube('qw_rail', (a.x, a.y, 1.6), (b.x, b.y, 1.6), 0.03, M['w_silver'], seg=6))
        p.append(tube('qw_post', (a.x, a.y, 0.98), (a.x, a.y, 1.6), 0.03, M['w_silver'], seg=6))
    o = ok(join(p, 'QueueWall_' + ('E' if s > 0 else 'W')))
    BUILDINGS.append(o)
    return o


# ================================================================ the plaza

def fountain():
    """Round pool with a yellow rim, a ring of nozzles shooting arcs towards a brass dome, red geraniums round it."""
    c = FOUNTAIN
    ring = lambda nm, r0, r1, h, m: place_at(lib.lathe(nm, [(r0, 0.0), (r0, h), (r1, h), (r1, 0.0)], M[m], seg=48, smooth=False), c)
    p = [ring('fo_curb', 5.3, 5.75, 0.3, 'w_yellow'),
         cyl('fo_soil', 5.35, 0.36, (c.x, c.y, 0.18), M['bark'], seg=48),
         ring('fo_rim', 3.6, 4.1, 0.6, 'w_yellow'),
         cyl('fo_floor', 3.65, 0.4, (c.x, c.y, 0.22), M['pool_floor'], seg=48),
         cyl('fo_water', 3.66, 0.04, (c.x, c.y, 0.44), M['pool'], seg=48),
         sphere('fo_dome', 1.15, (c.x, c.y, 0.45), M['gold'], scale=(1, 1, 0.5), seg=24, rings=10),
         cyl('fo_foam', 1.6, 0.03, (c.x, c.y, 0.47), M['foam'], seg=24)]
    n = 24
    for i in range(n):
        a = 2 * math.pi * i / n
        d = V((math.cos(a), math.sin(a)))
        base = V((c.x, c.y, 0)) + V((d.x, d.y, 0)) * 3.55
        base.z = 0.6
        p.append(cyl('fo_nozzle', 0.06, 0.16, (base.x, base.y, 0.62), M['w_silver'], seg=8))
        pts = []
        for k in range(9):
            t = k / 8
            r = 3.55 - 2.3 * t
            pts.append(V((c.x + d.x * r, c.y + d.y * r, 0.68 + 1.9 * 4 * t * (1 - t) * 0.6 + (0.0 if t < 0.5 else -0.35 * (t - 0.5)))))
        for a1, a2 in zip(pts, pts[1:]):
            p.append(tube('fo_jet', a1, a2, 0.035, M['jet'], seg=6))
        p.append(sphere('fo_splash', 0.13, pts[-1], M['foam'], seg=8, rings=4))
    # geraniums and leaves in the ring
    for _ in range(170):
        a, r = rng.uniform(0, 2 * math.pi), rng.uniform(4.25, 5.2)
        p.append(ico('fo_leaf', rng.uniform(0.13, 0.2), (c.x + math.cos(a) * r, c.y + math.sin(a) * r, 0.42), M[rng.choice(['leaf', 'leaf_dark'])], subdiv=1))
    for _ in range(140):
        a, r = rng.uniform(0, 2 * math.pi), rng.uniform(4.25, 5.2)
        p.append(ico('fo_bloom', rng.uniform(0.06, 0.09), (c.x + math.cos(a) * r, c.y + math.sin(a) * r, 0.58 + rng.uniform(0, 0.1)), M['flower_red'], subdiv=1))
    return join(p, 'Fountain')


def kiosk():
    """The ice cream kiosk you sit in front of (faces +Y): striped awning, a counter, a giant cone on the roof."""
    x0, x1, y0, y1 = -7.0, 7.0, -21.0, -15.0
    cx = (x0 + x1) / 2
    L = x1 - x0
    H = 4.2
    p = [box('ki_body', (L, y1 - y0, H), (cx, (y0 + y1) / 2, H / 2), M['w_yellow'], smooth=False),
         box('ki_band', (L + 0.2, (y1 - y0) + 0.2, 0.5), (cx, (y0 + y1) / 2, H - 0.25), M['w_red'], smooth=False),
         box('ki_counter', (L - 3.0, 0.5, 1.1), (cx, y1 + 0.25, 0.55), M['w_red'], smooth=False),
         box('ki_window', (L - 3.0, 0.06, 1.5), (cx, y1 + 0.03, 1.95), M['glass'], smooth=False),
         box('ki_roof', (L + 0.3, (y1 - y0) + 0.3, 0.15), (cx, (y0 + y1) / 2, H + 0.07), M['w_slate'], smooth=False)]
    tilt = math.radians(20)
    for k in range(14):
        x = x0 + L * (k + 0.5) / 14
        p.append(box('ki_awning', (L / 14 + 0.002, 2.0, 0.03), (x, y1 + 0.95, H - 0.75 - 0.95 * math.sin(tilt)),
                     M['w_red' if k % 2 == 0 else 'fab_cream'], rot=(tilt, 0, 0), smooth=False))
    p.append(text_mesh('ki_name', 'IJSKIOSK DE LOOPING', 0.42, (cx, y1 + 0.13, H - 0.25), rot=(math.pi / 2, 0, math.pi), mat=M['white'], extrude=0.02))
    # the giant cone on the roof
    p.append(cyl('ki_cone', 0.8, 2.4, (cx, (y0 + y1) / 2, H + 1.4), M['wood_light'], r2=0.08, rot=(math.pi, 0, 0), seg=16))
    for dx, dz, m in ((-0.35, 2.7, 'flower_pink'), (0.38, 2.7, 'fab_cream'), (0.0, 3.25, 'wood')):
        p.append(sphere('ki_scoop', 0.62, (cx + dx, (y0 + y1) / 2, H + dz), M[m], seg=16, rings=8))
    p.append(sphere('ki_cherry', 0.17, (cx, (y0 + y1) / 2, H + 3.95), M['flower_red'], seg=10, rings=6))
    o = ok(join(p, 'IJskiosk'))
    BUILDINGS.append(o)
    return o


def pavilion(name, xa, xb, ya, yb, facing, title, wall='w_yellow', H=5.0):
    """Simple park building (shop / snack bar / toilets): yellow with a red band and a sign on the facing side."""
    cx, cy = (xa + xb) / 2, (ya + yb) / 2
    p = [box('pv_body', (xb - xa, yb - ya, H), (cx, cy, H / 2), M[wall], smooth=False),
         box('pv_band', (xb - xa + 0.2, yb - ya + 0.2, 0.6), (cx, cy, H - 0.3), M['w_red'], smooth=False),
         box('pv_roof', (xb - xa + 0.4, yb - ya + 0.4, 0.2), (cx, cy, H + 0.1), M['w_slate'], smooth=False),
         box('pv_plinth', (xb - xa + 0.05, yb - ya + 0.05, 0.35), (cx, cy, 0.17), M['w_darkred'], smooth=False)]
    fx, fy = facing
    if fx:   # facade at x = xb (fx > 0) or xa
        x = xb if fx > 0 else xa
        L = yb - ya
        for k in range(int(L / 3.2)):
            y = ya + 1.6 + k * 3.2
            p.append(box('pv_win', (0.06, 2.0, 2.0), (x + 0.03 * fx, y, 1.6), M['glass'], smooth=False))
        p.append(text_mesh('pv_sign', title, 0.5, (x + 0.12 * fx, cy, H - 0.3), rot=(math.pi / 2, 0, -fx * math.pi / 2), mat=M['white'], extrude=0.02))
    else:
        y = yb if fy > 0 else ya
        L = xb - xa
        for k in range(int(L / 3.2)):
            x = xa + 1.6 + k * 3.2
            p.append(box('pv_win', (2.0, 0.06, 2.0), (x, y + 0.03 * fy, 1.6), M['glass'], smooth=False))
        p.append(text_mesh('pv_sign', title, 0.5, (cx, y + 0.12 * fy, H - 0.3), rot=(math.pi / 2, 0, math.pi if fy > 0 else 0), mat=M['white'], extrude=0.02))
    o = ok(join(p, name))
    BUILDINGS.append(o)
    return o


def hedge(name, xa, xb, ya, yb, h=2.2):
    o = box(name, (xb - xa, yb - ya, h), ((xa + xb) / 2, (ya + yb) / 2, h / 2), M['hedge'], bevel=0.25, segs=2)
    return ok(join([o], name), 1.0)


def fence(name, a, b, h=1.3, step=2.5):
    """Yellow park fence: posts and two rails."""
    a, b = V(a), V(b)
    L = (b - a).length
    d = (b - a).normalized()
    p = []
    for k in range(int(L / step) + 1):
        q = a + d * min(k * step, L)
        p.append(box('fe_post', (0.12, 0.12, h), (q.x, q.y, h / 2), M['w_yellow'], smooth=False))
    for z in (h * 0.4, h * 0.9):
        p.append(tube('fe_rail', (a.x, a.y, z), (b.x, b.y, z), 0.04, M['w_red'], seg=6))
    return join(p, name)


# ================================================================ the roller coaster

def _catmull(pts, per=24):
    """Closed Catmull-Rom spline through pts -> dense list of points."""
    out = []
    n = len(pts)
    for i in range(n):
        p0, p1, p2, p3 = pts[i - 1], pts[i], pts[(i + 1) % n], pts[(i + 2) % n]
        for k in range(per):
            t = k / per
            t2, t3 = t * t, t * t * t
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
    return out


def _resample(dense, step):
    out = [dense[0]]
    acc = 0.0
    for a, b in zip(dense + dense[:1], dense[1:] + dense[:1]):
        seg = (b - a).length
        while acc + seg >= step:
            t = (step - acc) / seg
            a = a.lerp(b, t)
            seg = (b - a).length
            out.append(a)
            acc = 0.0
        acc += seg
    if (out[-1] - out[0]).length < step * 0.5:
        out.pop()
    return out


def coaster_path():
    """Control points of 'De Gillende Gozer', in order of travel (closed):
    station (north, heading west) -> lift hill towards you (x = -22) -> crest, turning east -> the drop along
    y = 44 behind the gate -> vertical loop (x 12..28) -> airtime hill up the east side -> back into the station."""
    c = [(22, 88, 1.8), (8, 88, 1.8), (-6, 88, 1.8), (-16, 86.5, 2.4), (-21, 81, 3.5),
         (-22, 74, 6.5), (-22, 64, 15.5), (-22, 56, 24.0), (-22, 51, 29.0),
         (-21.2, 47.2, 31.0), (-18, 44.6, 31.0), (-14, 44, 29.5),
         (-8, 44, 22.0), (-2, 44, 12.5), (4, 44, 5.0), (10, 44, 2.6), (15, 44, 2.5)]
    x0, y0, z0, R = 20.0, 44.0, 2.5, 8.0
    for i in range(16):
        th = 2 * math.pi * i / 16
        c.append((x0 + R * math.sin(th), y0 + 3.0 * th / (2 * math.pi), z0 + R * (1 - math.cos(th))))
    c += [(25, 47, 2.5), (30, 48, 2.6), (36, 52, 3.6), (39.5, 58, 6.5), (40.5, 65, 10.0), (40, 71, 9.5),
          (38.5, 77, 5.5), (35, 83, 3.0), (29, 87, 2.0)]
    pts = _resample(_catmull([V(p) for p in c]), 0.5)
    # rotation-minimising frames, starting upright
    frames = []
    up = V((0, 0, 1))
    for i, q in enumerate(pts):
        t = (pts[(i + 1) % len(pts)] - pts[i - 1]).normalized()
        up = (up - t * up.dot(t)).normalized()
        side = t.cross(up).normalized()
        frames.append((q, t, side, up))
    return frames


def is_lift(q):
    return q.x < -18.5 and 49.0 < q.y < 82.0 and q.z < 30.5


def is_station(q):
    return q.y > 86.5 and -8.0 < q.x < 24.0


def coaster():
    frames = coaster_path()
    n = len(frames)
    rails, ties, spine, sup = [], [], [], []
    G = 0.55   # half gauge
    for i in range(n):
        q, t, sd, up = frames[i]
        q2, t2, sd2, up2 = frames[(i + 1) % n]
        for s in (-1, 1):
            rails.append(tube('rail', q + sd * (s * G), q2 + sd2 * (s * G), 0.07, M['track'], seg=6, caps=False))
        spine.append(tube('spine', q - up * 0.55, q2 - up2 * 0.55, 0.2, M['track'], seg=6, caps=False))
        if i % 2 == 0:
            o = box('tie', (0.1, 2 * G + 0.25, 0.1), (0, 0, 0), M['track'], smooth=False)
            lib.orient_basis(o, lib.basis(t, up), q - up * 0.2)
            ties.append(o)
            o = box('web', (0.08, 0.1, 0.45), (0, 0, 0), M['track'], smooth=False)
            lib.orient_basis(o, lib.basis(t, up), q - up * 0.38)
            ties.append(o)
        if i % 8 == 0:
            low = q - up * 0.7
            if up.z > 0.6 and low.z > 1.0 and not is_station(q):
                feet = [V((low.x, low.y, 0))]
                if low.z > 12:   # tall: an A-frame across the track
                    feet = [V((low.x, low.y, 0)) + sd * (s * (1.2 + low.z * 0.08)) for s in (-1, 1)]
                    mid = low - V((0, 0, low.z * 0.5))
                    sup.append(tube('brace', mid + sd * (1.2 + low.z * 0.04), mid - sd * (1.2 + low.z * 0.04), 0.08, M['support'], seg=6))
                for f in feet:
                    f.z = 0
                    sup.append(tube('leg', low, f, 0.2, M['support'], seg=8))
                    sup.append(cyl('footing', 0.45, 0.3, (f.x, f.y, 0.15), M['stone_dark'], seg=8))
            elif abs(up.z) < 0.45 and q.z > 4.0:   # the sides of the loop
                sup.append(tube('leg', q - up * 0.5, V((q.x, q.y, 0)), 0.22, M['support'], seg=8))
                sup.append(cyl('footing', 0.45, 0.3, (q.x, q.y, 0.15), M['stone_dark'], seg=8))
    objs = [join(rails, 'Coaster_Rails'), join(spine + ties, 'Coaster_Spine'), join(sup, 'Coaster_Supports')]

    # the station: platform, a roof and the name board facing the gate
    st = [box('st_platform', (34, 3.5, 1.2), (8, 90.6, 0.6), M['stone'], smooth=False),
          box('st_roof', (36, 7.5, 0.35), (8, 89.0, 5.6), M['w_red'], smooth=False),
          box('st_back', (34, 0.4, 5.4), (8, 92.6, 2.7), M['w_yellow'], smooth=False),
          box('st_board', (12, 0.2, 1.6), (8, 85.3, 6.6), M['w_yellow'], smooth=False)]
    for x in (-8.5, -1.5, 5.5, 12.5, 19.5, 24.5):
        st.append(tube('st_col', (x, 85.6, 0), (x, 85.6, 5.5), 0.15, M['w_silver'], seg=8))
    st.append(text_mesh('st_name', 'DE GILLENDE GOZER', 0.95, (8, 85.15, 6.6), mat=M['w_red'], extrude=0.04))
    objs.append(ok(join(st, 'Coaster_Station')))
    return objs, frames


def coaster_car():
    """One car of the train, facing +X, origin on the track centre: blue body, red nose, four guests with their
    arms in the air."""
    p = [box('car_body', (2.3, 1.5, 0.55), (0, 0, 0.55), M['car_blue'], bevel=0.12, segs=2),
         box('car_nose', (0.4, 1.5, 0.45), (1.25, 0, 0.5), M['w_red'], bevel=0.12, segs=2),
         box('car_chassis', (2.0, 1.2, 0.2), (0, 0, 0.2), M['iron'], smooth=False)]
    for x in (-0.75, 0.75):
        for y in (-0.62, 0.62):
            p.append(cyl('car_wheel', 0.12, 0.1, (x, y, 0.08), M['w_silver'], rot=(math.pi / 2, 0, 0), seg=10))
    for row, x in enumerate((0.35, -0.6)):
        p.append(box('car_seatback', (0.12, 1.3, 0.55), (x - 0.35, 0, 1.05), M['w_red'], smooth=False))
        for k, y in enumerate((-0.35, 0.35)):
            skin = M['skin_a' if (row + k) % 2 == 0 else 'skin_b']
            shirt = M[('fab_yellow', 'fab_green', 'fab_orange', 'flag_white')[row * 2 + k]]
            p.append(lib.capsule('guest_body', (x - 0.1, y, 0.8), (x - 0.12, y, 1.25), 0.2, 0.18, shirt, seg=10, rings=6))
            p.append(sphere('guest_head', 0.17, (x - 0.12, y, 1.52), skin, seg=12, rings=8))
            p.append(sphere('guest_hair', 0.175, (x - 0.16, y, 1.58), M[('wood', 'bark', 'flower_yellow', 'iron')[row * 2 + k]],
                            scale=(1, 1, 0.7), seg=12, rings=6))
            for s in (-1, 1):
                hand = (x - 0.05, y + s * 0.32, 2.05)
                p.append(tube('guest_arm', (x - 0.1, y + s * 0.18, 1.3), hand, 0.05, shirt, seg=6))
                p.append(sphere('guest_hand', 0.07, hand, skin, seg=8, rings=4))
    return join(p, 'CoasterCar')


# ================================================================ scene assembly

def build():
    lib.reset_scene()
    make_materials()
    sq.BUILDINGS.clear()
    sq.SIDEWALKS.clear()
    root = lib.empty('Square')
    groups = {k: lib.empty(k, parent=root) for k in ('Ground', 'Buildings', 'Props', 'Markers', 'Coaster')}

    # --- ground. The plaza paving lies a little proud (covers the Donutplein's ground in the adventure);
    #     the park's base ground starts at y = 20, where the Donutplein's ends.
    g = [box('Plaza_Pavers', (105.0, 48.0, 0.07), (7.5, -2.0, 0.0), M['pavers'], smooth=False),
         box('Park_Grass', (150.0, 82.0, 0.2), (0.0, 61.0, -0.1), M['grass'], smooth=False),
         box('Promenade', (132.0, PROM[1] - PROM[0], 0.07), (0.0, sum(PROM) / 2, 0.0), M['pavers'], smooth=False),
         box('Park_Path_N', (5.0, 50.0, 0.07), (0.0, 63.0, 0.0), M['tegels'], smooth=False),
         box('Gate_Path', (8.0, 6.0, 0.07), (0.0, 25.0, 0.0), M['pavers'], smooth=False),
         box('Walk_Path', (8.0, 26.0, 0.07), (-57.8, 15.0, 0.0), M['pavers'], smooth=False),
         box('Under_Kiosk', (20.0, 10.0, 0.07), (0.0, -21.0, 0.0), M['pavers'], smooth=False)]
    for o in g:
        ok(o)
        lib.set_parent(o, groups['Ground'])

    # --- the gate, the turnstiles and the ticket buildings either side
    gate()
    for s in (-1, 1):
        turnstiles(s)
        ticket_building(s)
        queue_wall(s)
    # behind you: the ice cream kiosk, with lower buildings either side; the plaza's corners
    kiosk()
    pavilion('Toiletten_W', -22.0, -7.0, -24.0, -15.0, (0, 1), 'TOILETTEN', H=4.0)
    pavilion('EHBO_E', 7.0, 22.0, -24.0, -15.0, (0, 1), 'EHBO  ·  LOCKERS', H=4.0)
    pavilion('Souvenirs_W', -34.0, -22.0, -24.0, 0.5, (1, 0), 'SOUVENIRS', H=6.0)
    pavilion('Patat_E', 22.0, 34.0, -24.0, 0.5, (-1, 0), 'PATATPALEIS', H=6.0)
    # the lanes west and east (y 0.5..6) run between hedges
    hd = [hedge('Hedge_LaneW_S', -45.0, -34.0, -0.6, 0.5), hedge('Hedge_LaneW_N', -45.0, -34.0, 6.0, 7.2),
          hedge('Hedge_LaneE_S', 34.0, 60.0, -0.6, 0.5), hedge('Hedge_LaneE_N', 34.0, 60.0, 6.0, 7.2),
          hedge('Hedge_E', 60.0, 61.2, -26.0, 20.0, 2.6),
          # the park: along the walk from the Donutplein, behind the ticket buildings, round the park
          hedge('Hedge_Walk_E', -45.0, -34.0, 20.0, 21.0), hedge('Hedge_Park_W', -67.0, -66.0, 2.0, 100.0),
          hedge('Hedge_Park_E', 66.0, 67.0, 20.0, 100.0), hedge('Hedge_Park_N', -67.0, 67.0, 100.0, 101.0),
          hedge('Hedge_Prom_W', -66.0, -6.0, 38.6, 39.6, 1.2), hedge('Hedge_Prom_E', 6.0, 66.0, 38.6, 39.6, 1.2),
          hedge('Hedge_Prom_SW', -53.0, -34.0, 26.6, 27.4, 1.2), hedge('Hedge_Prom_SE', 34.0, 66.0, 26.6, 27.4, 1.2)]
    BUILDINGS.extend(hd)
    BUILDINGS.append(fence('Fence_Kassa_W', (-34.0, 24.0), (-34.0, 20.0)))
    for o in BUILDINGS:
        lib.set_parent(o, groups['Buildings'])

    # --- the coaster
    cobjs, frames = coaster()
    for o in cobjs:
        lib.set_parent(o, groups['Coaster'])
    car = coaster_car()

    # --- props
    props = [fountain()]
    P = lambda src, loc, rz=0.0, s=1.0: props.append(instance(src, src.name + '_i', loc, rz, s))
    tree, binm, bench, lamp = sq.prop_tree(), sq.prop_bin(), sq.prop_bench(), dn.prop_lamp_modern()
    table, chair = sq.prop_table(), sq.prop_chair()
    parasols = {f: sq.prop_parasol(f) for f in ('fab_red', 'fab_yellow')}
    templates = [tree, binm, bench, lamp, table, chair, car] + list(parasols.values())

    for x, y in ((-8.0, 16.5), (9.5, 4.0), (-12.5, -4.0), (12.5, -8.0)):
        P(binm, (x, y, 0))
    for x, y, rz in ((-13.5, 13.0, 0.0), (13.5, -4.0, math.pi), (-13.5, -8.0, 0.0)):
        P(bench, (x, y, 0), rz)
    for x, y in ((-15.0, -12.0), (15.0, -12.0), (-12.0, 4.0), (12.0, 10.0)):
        P(lamp, (x, y, 0))
    # the park: trees round the promenade and the coaster
    for k in range(34):
        x, y = rng.uniform(-62, 62), rng.uniform(41, 97)
        if (abs(x) < 4 or -26 < x < 44 and 40 < y < 95 or abs(x + 22) < 6) and rng.random() < 0.9:
            continue
        P(tree, (x, y, 0), rng.uniform(0, 6.28), rng.uniform(0.9, 1.3))
    for x in (-60, -48, -40, 40, 48, 58):
        P(tree, (x, 23.5, 0), rng.uniform(0, 6.28), 1.1)
    for x in (-50.0, -30.0, -12.0, 12.0, 30.0, 50.0):
        P(lamp, (x, 27.4, 0))

    def terrace(cx, cy, n, gap=1.9, skip=(), umbrellas=(0, 2, 4)):
        for i in range(n):
            if i in skip:
                continue
            x = cx + (i - (n - 1) / 2) * gap
            P(table, (x, cy, 0))
            for s in (-1, 1):
                P(chair, (x + s * 0.55, cy, 0), math.pi if s > 0 else 0)
            if i in umbrellas:
                P(parasols['fab_red' if i % 4 == 0 else 'fab_yellow'], (x, cy, 0), rng.uniform(0, 1))

    terrace(0, -10.9, 5, skip=(2,))            # the middle table is yours
    terrace(0, -13.3, 6, gap=2.2, umbrellas=(1, 4))
    small = sq.prop_table(0.23, 'PlayerTableMesh')
    templates.append(small)
    props.append(instance(small, 'Player_Table', (-0.38, -11.0, 0)))
    props.append(instance(chair, 'Player_Chair', (0, -11.55, 0), math.pi / 2))
    # no parasol over your own table here: it would hide the lift hill (and the fatbikers riding it)

    # flags round the gate and bunting over the plaza
    for x, y in ((-8.0, 24.0), (8.0, 24.0), (-3.5, 30.0), (3.5, 30.0)):
        fl = [tube('flagpole', (x, y, 0), (x, y, 9.0), 0.07, M['white'], r2=0.05, seg=10),
              sphere('flagknob', 0.1, (x, y, 9.05), M['gold'], seg=10, rings=6),
              box('flag', (1.6, 0.02, 1.0), (x + 0.85, y, 8.3), M['w_red' if x < 0 else 'w_yellow'], smooth=False)]
        props.append(join(fl, 'Flag'))
    props.append(sq.bunting((-16.0, 6.5, 4.6), (16.0, 6.5, 4.6), 1.4, 'Bunting_N'))
    props.append(sq.bunting((-22.0, -14.5, 4.0), (-7.0, 1.0, 4.4), 1.0, 'Bunting_W'))
    props.append(sq.bunting((22.0, -14.5, 4.0), (7.0, 1.0, 4.4), 1.0, 'Bunting_E'))

    for o in props:
        lib.set_parent(o, groups['Props'])
    for t in templates:
        t.location = (0, 0, -100)
    car.location = (0, 0, -100)
    lib.set_parent(car, groups['Props'])   # the game copies it into trains

    # --- markers: the player, the square, and the coaster track
    markers = {'PlayerEye': (0, -11.55, 1.2), 'Square_Center': (FOUNTAIN.x, FOUNTAIN.y, 0)}
    for name, loc in markers.items():
        lib.empty(name, loc, parent=groups['Markers'])
    for k, i in enumerate(range(0, len(frames), 4)):
        q = frames[i][0]
        suffix = '_lift' if is_lift(q) else ('_station' if is_station(q) else '')
        lib.empty('Track_%03d%s' % (k, suffix), tuple(q), parent=groups['Markers'])
    return root, templates


def main():
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    root, templates = build()
    scene = bpy.context.scene
    objs = [root] + list(root.children_recursive)
    meshes = [o for o in objs if o.type == 'MESH']
    print(f'[wollahbi] buildings: {len(BUILDINGS)}, objects: {len(objs)}, triangles: {lib.tri_count(meshes)}')
    out = os.path.join(ROOT, 'assets', 'models', 'wollahbi.glb')
    lib.export_glb(out, objs)
    print(f'[wollahbi] exported {out} ({os.path.getsize(out) / 1e6:.1f} MB)')
    for t in templates:
        t.hide_render = True
    if '--no-render' in argv:
        return
    lib.preview_stage(scene, size=(1600, 900))
    bpy.data.objects['PreviewGround'].hide_render = True
    sun = bpy.data.objects['Sun']
    sun.rotation_euler = (math.radians(50), 0, math.radians(-150))
    sun.data.energy = 6.0
    bpy.data.objects['Fill'].hide_render = True
    rdir = os.path.join(ROOT, 'renders', 'wollahbi')
    eye = V((0, -11.55, 1.2))
    shots = [
        ('01_player_view', eye, eye + V((0, 10, 1.4)), 20),
        ('02_overview', (-30, -40, 45), (5, 35, 5), 22),
        ('03_photo', (0, -6.5, 1.8), (0, 20, 7.5), 16),
        ('04_coaster', (-55, 15, 14), (5, 62, 12), 22),
        ('05_walk_in', (-50, 30, 1.6), (0, 26, 5.0), 22),
        ('06_through_gate', (0, 32, 1.6), (0, 0, 1.5), 22),
        ('07_look_left', eye, eye + V((-10, 4, 0.8)), 22),
        ('08_look_right', eye, eye + V((10, 4, 0.8)), 22),
    ]
    picks = [a for a in argv if a[:2].isdigit()]
    if picks:
        shots = [s for s in shots if s[0][:2] in picks]
    for name, loc, tgt, lens in shots:
        lib.render(scene, lib.camera('Cam_' + name, tuple(loc), tuple(tgt), lens), os.path.join(rdir, name + '.png'))


if __name__ == '__main__':
    main()
