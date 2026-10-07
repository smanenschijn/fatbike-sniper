"""Build the Dutch shopping square (plein) with streets, church, terraces and props.

Layout (meters, +Y = north). The player sits on the terrace of Café 't Pleintje on the
south side, looking north over the square. See DESIGN.md for the entry roads.

Run:  Blender -b -P blender/build_square.py [-- --no-render]
"""
import math
import os
import random
import sys

import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(__file__))
import lib  # noqa: E402
import textures  # noqa: E402
from lib import (box, cyl, ico, join, material, sphere, torus, tube, text_mesh,  # noqa: E402
                 extrude_profile, instance)

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
V = Vector
rng = random.Random(42)
M = {}


# ================================================================ materials

def make_materials():
    tx = textures.ensure(os.path.join(ROOT, 'assets', 'textures'))
    t = lambda name, key, rough=0.85, ns=1.0: lib.tex_material(name, *tx[key], rough=rough, normal_strength=ns)
    M.update({
        'klinkers': t('Klinkers', 'klinkers', 0.85, 1.2),
        'tegels': t('Stoeptegels', 'stoeptegels', 0.9, 0.8),
        'brick_red': t('BrickRed', 'brick_red', 0.85, 1.0),
        'brick_brown': t('BrickBrown', 'brick_brown', 0.85, 1.0),
        'brick_yellow': t('BrickYellow', 'brick_yellow', 0.85, 1.0),
        'roof_red': t('RoofRed', 'roof_red', 0.7, 1.0),
        'roof_dark': t('RoofDark', 'roof_dark', 0.55, 1.0),
        'plaster_cream': material('PlasterCream', '#efe4cc', rough=0.9),
        'plaster_white': material('PlasterWhite', '#f3f0e8', rough=0.9),
        'plaster_sand': material('PlasterSand', '#dcc59c', rough=0.9),
        'plaster_blue': material('PlasterBlue', '#c3d0d4', rough=0.9),
        'stone': material('StoneWhite', '#e9e3d6', rough=0.75),
        'stone_dark': material('StoneDark', '#77736b', rough=0.85),
        'curb': material('Curb', '#9c9a94', rough=0.85),
        'glass': material('Glass', '#26384a', rough=0.04, metal=0.3, coat=1.0),
        'frame_white': material('FrameWhite', '#f4f2ec', rough=0.4),
        'frame_green': material('FrameGreen', '#1f4a35', rough=0.4, coat=0.3),
        'frame_cream': material('FrameCream', '#ece2c4', rough=0.45),
        'door_green': material('DoorGreen', '#1d4a33', rough=0.35, coat=0.5),
        'door_red': material('DoorRed', '#7c1d22', rough=0.35, coat=0.5),
        'door_blue': material('DoorBlue', '#1c3556', rough=0.35, coat=0.5),
        'door_black': material('DoorBlack', '#1b1b1d', rough=0.3, coat=0.5),
        'door_yellow': material('DoorOchre', '#c08a28', rough=0.35, coat=0.5),
        'shutter_green': material('ShutterGreen', '#2a6a3f', rough=0.45),
        'shutter_red': material('ShutterRed', '#9a2a25', rough=0.45),
        'sign_black': material('SignBlack', '#1c1c1e', rough=0.35, coat=0.4),
        'sign_green': material('SignGreen', '#23493a', rough=0.35, coat=0.4),
        'sign_red': material('SignRed', '#6e1a1c', rough=0.35, coat=0.4),
        'sign_blue': material('SignBlue', '#1d3557', rough=0.35, coat=0.4),
        'gold': material('GoldLeaf', '#e7c35a', rough=0.25, metal=1.0),
        'white': material('SignWhite', '#fbfaf5', rough=0.4),
        'wood': material('Wood', '#6b4a2c', rough=0.7),
        'wood_light': material('WoodLight', '#a87c4f', rough=0.65),
        'iron': material('Iron', '#1b1c1e', rough=0.45, metal=0.6),
        'bronze': material('Bronze', '#7d5a30', rough=0.35, metal=1.0),
        'copper': material('CopperGreen', '#5f9f88', rough=0.6, metal=0.3),
        'water': material('Water', '#3f93b8', rough=0.03, coat=1.0, emission='#2f7fa8', strength=0.15),
        'leaf': material('Leaves', '#56882c', rough=0.75, sheen=0.4),
        'leaf_dark': material('LeavesDark', '#3b6522', rough=0.75, sheen=0.4),
        'leaf_light': material('LeavesLight', '#73a33a', rough=0.75, sheen=0.4),
        'stone_warm': material('StoneWarm', '#cdc3ae', rough=0.8),
        'bark': material('Bark', '#4a3c30', rough=0.95),
        'flower_red': material('FlowerRed', '#d8282a', rough=0.6),
        'flower_pink': material('FlowerPink', '#ea6aa4', rough=0.6),
        'flower_white': material('FlowerWhite', '#f6f3ea', rough=0.6),
        'flower_yellow': material('FlowerYellow', '#f2c425', rough=0.6),
        'fab_cream': material('FabricCream', '#f3ead6', rough=0.8, sheen=0.5),
        'fab_red': material('FabricRed', '#c8302a', rough=0.8, sheen=0.5),
        'fab_green': material('FabricGreen', '#2d6a45', rough=0.8, sheen=0.5),
        'fab_blue': material('FabricBlue', '#2b5a8c', rough=0.8, sheen=0.5),
        'fab_orange': material('FabricOrange', '#f08a24', rough=0.8, sheen=0.5),
        'fab_yellow': material('FabricYellow', '#f4cf3a', rough=0.8, sheen=0.5),
        'marble': material('Marble', '#f1efe9', rough=0.2),
        'rattan': material('Rattan', '#b88a52', rough=0.7),
        'bollard': material('Bollard', '#5b2a1f', rough=0.45, metal=0.4),
        'bin_green': material('BinGreen', '#2f5e3a', rough=0.5, metal=0.3),
        'lamp_glow': material('LampGlass', '#fff4d8', rough=0.1, emission='#ffe2a8', strength=1.5),
        'clock': material('ClockFace', '#f4f1e6', rough=0.4),
        'rubber': material('BikeRubber', '#151515', rough=0.85),
        'chrome': material('BikeChrome', '#cfd2d6', rough=0.15, metal=1.0),
        'bike_black': material('OmafietsBlack', '#18191b', rough=0.35, coat=0.5),
        'bike_green': material('OmafietsGreen', '#24503b', rough=0.35, coat=0.5),
        'bike_blue': material('OmafietsBlue', '#2d5d8f', rough=0.35, coat=0.5),
        'bike_red': material('OmafietsRed', '#9b2b26', rough=0.35, coat=0.5),
        'flag_red': material('FlagRed', '#ae1c28', rough=0.8, sheen=0.4),
        'flag_white': material('FlagWhite', '#ffffff', rough=0.8, sheen=0.4),
        'flag_blue': material('FlagBlue', '#21468b', rough=0.8, sheen=0.4),
    })


WALLS = ['brick_red'] * 5 + ['brick_brown'] * 3 + ['brick_yellow'] * 2 + ['plaster_cream', 'plaster_white', 'plaster_sand', 'plaster_blue']
FRAMES = ['frame_white'] * 6 + ['frame_green', 'frame_cream']
DOORS = ['door_green', 'door_red', 'door_blue', 'door_black', 'door_yellow']
SIGNS = ['sign_black', 'sign_green', 'sign_red', 'sign_blue']
AWNINGS = [('fab_red', 'fab_cream'), ('fab_green', 'fab_cream'), ('fab_blue', 'fab_cream'),
           ('fab_orange', 'fab_cream'), ('fab_yellow', 'fab_cream'), ('fab_red', 'fab_red')]
SHOPS = ['IJSSALON', 'BAKKERIJ', 'BLOEMEN', 'KAASHANDEL', 'BOEKHANDEL', 'FRITUUR', 'SLAGERIJ', 'DROGISTERIJ',
         'SCHOENEN', 'EETCAFE', 'LUNCHROOM', 'VISHANDEL', 'KAPSALON', 'OPTIEK', 'SNOEPWINKEL', 'FIETSENMAKER',
         'KOFFIEBAR', 'WIJNHANDEL', 'BRILLEN', 'POFFERTJES', 'STROOPWAFELS', 'SPEELGOED', 'TABAK', 'BAR DE ZON']
GABLES = ['stepped', 'stepped', 'neck', 'neck', 'bell', 'bell', 'spout', 'cornice']


# ================================================================ house parts (local: facade at y=0 facing -Y, x in [0, w])

def window(xc, zc, ww, wh, frame, shutters=None, flowers=False):
    p = [box('glass', (ww, 0.03, wh), (xc, -0.015, zc), M['glass'], smooth=False)]
    f, fd = 0.075, 0.07
    p.append(box('frame', (ww + 2 * f, fd, f), (xc, -fd / 2, zc + wh / 2 + f / 2), M[frame], smooth=False))
    p.append(box('frame', (ww + 2 * f, fd, f), (xc, -fd / 2, zc - wh / 2 - f / 2), M[frame], smooth=False))
    for s in (-1, 1):
        p.append(box('frame', (f, fd, wh), (xc + s * (ww / 2 + f / 2), -fd / 2, zc), M[frame], smooth=False))
    tz = zc + wh * 0.16
    p.append(box('transom', (ww, 0.05, 0.05), (xc, -0.04, tz), M[frame], smooth=False))
    p.append(box('mullion', (0.05, 0.05, wh), (xc, -0.04, zc), M[frame], smooth=False))
    top_h = zc + wh / 2 - tz
    for s in (-1, 1):  # small panes ('roedes') in the upper sash
        p.append(box('roede', (0.025, 0.04, top_h), (xc + s * ww / 4, -0.035, tz + top_h / 2), M[frame], smooth=False))
    p.append(box('sill', (ww + 0.3, 0.16, 0.07), (xc, -0.08, zc - wh / 2 - f - 0.035), M['stone'], smooth=False))
    p.append(box('lintel', (ww + 0.36, 0.06, 0.2), (xc, -0.03, zc + wh / 2 + f + 0.1), M['stone'], smooth=False))
    if shutters:
        sw = ww / 2 + 0.04
        for s in (-1, 1):
            cx = xc + s * (ww / 2 + f + sw / 2 + 0.02)
            p.append(box('shutter', (sw, 0.045, wh + 0.1), (cx, -0.03, zc), M[shutters], smooth=False))
            diag = math.atan2(sw, wh + 0.1)
            L = math.hypot(sw, wh + 0.1) * 0.95
            for d in (-1, 1):
                p.append(box('shutter_x', (0.035, 0.05, L), (cx, -0.035, zc), M['white'], rot=(0, d * diag, 0), smooth=False))
    if flowers:
        bz = zc - wh / 2 - f + 0.08
        p.append(box('flowerbox', (ww + 0.15, 0.24, 0.2), (xc, -0.2, bz), M['wood'], smooth=False))
        fm = rng.choice(['flower_red', 'flower_red', 'flower_pink', 'flower_white'])
        for i in range(9):
            x = xc + (i / 8 - 0.5) * ww
            p.append(ico('leafs', rng.uniform(0.07, 0.1), (x, -0.2 + rng.uniform(-0.05, 0.05), bz + 0.13), M['leaf'], subdiv=1))
            p.append(ico('bloom', rng.uniform(0.045, 0.065), (x + rng.uniform(-0.05, 0.05), -0.25, bz + 0.2 + rng.uniform(0, 0.06)),
                         M[fm], subdiv=1))
    return p


def door(xc, wd, hd, mat, frame):
    p = [box('door', (wd, 0.06, hd), (xc, -0.03, hd / 2 + 0.15), M[mat], smooth=False)]
    for i in range(2):  # raised panels
        p.append(box('panel', (wd * 0.7, 0.03, hd * 0.32), (xc, -0.07, 0.15 + hd * (0.25 + i * 0.42)), M[mat], smooth=False))
    p.append(box('knob', (0.05, 0.06, 0.05), (xc + wd * 0.35, -0.1, 0.15 + hd * 0.5), M['gold'], smooth=False))
    p.append(box('fanlight', (wd, 0.03, 0.45), (xc, -0.015, hd + 0.15 + 0.3), M['glass'], smooth=False))
    p.append(box('fanframe', (wd + 0.16, 0.07, 0.08), (xc, -0.035, hd + 0.15 + 0.04), M[frame], smooth=False))
    p.append(box('fanframe', (wd + 0.16, 0.07, 0.08), (xc, -0.035, hd + 0.15 + 0.56), M[frame], smooth=False))
    for s in (-1, 1):
        p.append(box('doorframe', (0.08, 0.07, hd + 0.6), (xc + s * (wd / 2 + 0.04), -0.035, (hd + 0.6) / 2 + 0.15), M[frame], smooth=False))
    p.append(box('step', (wd + 0.4, 0.4, 0.15), (xc, -0.2, 0.075), M['stone'], smooth=False))
    return p


def shopfront(w, gf, name, frame_mat, sign_mat, awning):
    p = []
    p.append(box('pui', (w - 0.3, 0.1, gf - 0.35), (w / 2, -0.05, (gf - 0.35) / 2), M[frame_mat], smooth=False))
    gx0, gx1 = 0.45, w - 1.7
    p.append(box('etalage', (gx1 - gx0, 0.04, gf - 1.75), ((gx0 + gx1) / 2, -0.12, 0.6 + (gf - 1.75) / 2), M['glass'], smooth=False))
    p.append(box('etalage_sill', (gx1 - gx0 + 0.1, 0.16, 0.08), ((gx0 + gx1) / 2, -0.16, 0.56), M['stone'], smooth=False))
    nb = max(1, int((gx1 - gx0) / 1.4))
    for i in range(1, nb):
        x = gx0 + (gx1 - gx0) * i / nb
        p.append(box('etalage_bar', (0.06, 0.06, gf - 1.75), (x, -0.15, 0.6 + (gf - 1.75) / 2), M[frame_mat], smooth=False))
    dx = w - 1.05
    p.append(box('shopdoor', (0.9, 0.04, 2.35), (dx, -0.12, 1.2), M['glass'], smooth=False))
    p.append(box('shopdoor_bar', (0.9, 0.05, 0.08), (dx, -0.14, 1.0), M[frame_mat], smooth=False))
    # sign board with the shop name
    sz = gf - 0.5
    p.append(box('sign', (w - 0.5, 0.08, 0.5), (w / 2, -0.14, sz), M[sign_mat], smooth=False))
    size = min(0.33, (w - 0.9) / (0.68 * max(4, len(name))))
    p.append(text_mesh('signtext', name, size, (w / 2, -0.19, sz), mat=M['gold' if rng.random() < 0.5 else 'white'], extrude=0.012))
    if awning:
        c1, c2 = awning
        top = gf - 0.85
        ang = math.radians(24)
        depth = 1.35
        aw = w - 0.7
        k = max(4, int(aw / 0.32))
        for i in range(k):
            x = 0.35 + aw * (i + 0.5) / k
            m = M[c1 if i % 2 == 0 else c2]
            p.append(box('awning', (aw / k + 0.002, depth, 0.025),
                         (x, -depth / 2 * math.cos(ang) - 0.1, top - depth / 2 * math.sin(ang)), m, rot=(ang, 0, 0), smooth=False))
            p.append(box('valance', (aw / k + 0.002, 0.02, 0.22),
                         (x, -depth * math.cos(ang) - 0.11, top - depth * math.sin(ang) - 0.11), m, smooth=False))
        for s in (0.4, w - 0.4):
            p.append(tube('awning_arm', (s, -0.1, top - 0.7), (s, -depth * math.cos(ang) - 0.1, top - depth * math.sin(ang)), 0.015, M['iron'], seg=6))
    return p


def gable_profile(style, w, rh):
    if style == 'stepped':
        n = 4 if w > 6 else 3
        tw = w * 0.2
        sx, sz = (w - tw) / 2 / n, rh / (n + 1)
        left = [(0, 0)]
        for i in range(n):
            left += [(i * sx, (i + 1) * sz), ((i + 1) * sx, (i + 1) * sz)]
        left += [(n * sx, rh)]
        right = [(w - x, z) for x, z in reversed(left)]
        return left + right, (sx, sz, n)
    if style == 'spout':
        return [(0, 0), (w * 0.38, rh), (w * 0.62, rh), (w, 0)], None
    if style == 'neck':
        nk = 0.27
        pts = [(0, 0)]
        for i in range(1, 9):  # concave shoulder
            t = i / 8
            pts.append((w * nk * t, rh * 0.45 * math.sin(t * math.pi / 2) ** 2))
        pts += [(w * nk, rh * 0.86), (w * 0.5, rh), (w * (1 - nk), rh * 0.86)]
        for i in range(8, 0, -1):
            t = i / 8
            pts.append((w * (1 - nk * t), rh * 0.45 * math.sin(t * math.pi / 2) ** 2))
        pts.append((w, 0))
        return pts, nk
    if style == 'bell':
        nk = 0.24
        pts = [(0, 0)]
        for i in range(1, 11):  # S-curve flank
            t = i / 10
            pts.append((w * nk * (1 - math.cos(t * math.pi)) / 2, rh * 0.72 * t))
        r = w * (0.5 - nk)
        for i in range(1, 12):  # round crown
            a = math.pi - math.pi * i / 12
            pts.append((w / 2 + r * math.cos(a), rh * 0.72 + r * 0.9 * math.sin(a)))
        for x, z in reversed(pts[1:11]):
            pts.append((w - x, z))
        pts.append((w, 0))
        return pts, nk
    return None, None


def pitched_roof(w, y0, y1, H, rr, roof_mat, wall_mat, eave=0.25):
    """Ridge along Y from y0 to y1 over x in [0, w]."""
    p = []
    L = y1 - y0
    mass = extrude_profile('roofmass', [(0, H), (w, H), (w / 2, H + rr)], L, M[wall_mat])
    mass.location = (0, y0 + L / 2, 0)
    p.append(mass)
    a = math.atan2(rr, w / 2)
    sl = math.hypot(w / 2, rr)
    for s in (-1, 1):
        n = V((s * math.sin(a), 0, math.cos(a)))
        c = V((w / 2 + s * w / 4, y0 + L / 2, H + rr / 2)) + n * 0.07
        c += V((s * math.cos(a), 0, -math.sin(a))) * (eave / 2)
        p.append(box('roof', (sl + eave, L + 0.15, 0.12), c, M[roof_mat], rot=(0, s * a, 0), smooth=False))
    p.append(cyl('ridge', 0.09, L + 0.15, (w / 2, y0 + L / 2, H + rr + 0.06), M[roof_mat], rot=(math.pi / 2, 0, 0), seg=8))
    return p


def house(name, w, d, floors, style, wall, frame, shop=None, roof=None, shutters=None):
    gf, fh = 3.9, 3.05
    H = gf + floors * fh
    p = [box('body', (w, d, H), (w / 2, d / 2, H / 2), M[wall], smooth=False)]
    p.append(box('plinth', (w, 0.08, 0.45), (w / 2, -0.04, 0.225), M['stone_dark'], smooth=False))
    p.append(box('band', (w, 0.12, 0.16), (w / 2, -0.06, gf), M['stone'], smooth=False))
    ncols = max(1, int(round(w / 1.8)))
    ww = min(1.05, w / ncols * 0.56)
    flowers = rng.random() < 0.4
    for i in range(floors):
        wh = 1.8 if i < floors - 1 else 1.55
        zc = gf + i * fh + fh * 0.5
        for j in range(ncols):
            p += window(w * (j + 0.5) / ncols, zc, ww, wh, frame, shutters, flowers and i == 0)
    if shop:
        p += shopfront(w, gf, shop['name'], shop['frame'], shop['sign'], shop['awning'])
    else:
        dxc = w - 0.9 if w > 3.5 else w / 2
        p += door(dxc, 1.0, 2.35, rng.choice(DOORS), frame)
        if w > 3.5:
            free = w - 1.9
            n = max(1, int(round(free / 1.9)))
            for j in range(n):
                p += window(0.3 + free * (j + 0.5) / n, 1.95, min(1.1, free / n * 0.6), 2.0, frame, shutters)

    roof = roof or rng.choice(['roof_red', 'roof_red', 'roof_dark'])
    rh = {'stepped': 0.85, 'spout': 0.8, 'neck': 1.05, 'bell': 0.95}.get(style, 0) * w
    pts, info = gable_profile(style, w, rh)
    if pts:
        g = extrude_profile('gable', [(x, H + z) for x, z in pts], 0.3, M[wall])
        g.location = (0, 0.15, 0)
        p.append(g)
        p += pitched_roof(w, 0.3, d, H, min(rh * 0.92, w * 0.75), roof, wall)
        if style == 'stepped':
            sx, sz, n = info
            for i in range(n):
                for x in (i * sx + sx / 2, w - i * sx - sx / 2):
                    p.append(box('stepcap', (sx + 0.08, 0.38, 0.08), (x, 0.15, H + (i + 1) * sz + 0.04), M['stone'], smooth=False))
            p.append(box('topcap', (w * 0.2 + 0.1, 0.4, 0.1), (w / 2, 0.15, H + rh + 0.05), M['stone'], smooth=False))
        elif style == 'neck':
            p.append(box('pediment', (w * 0.5, 0.36, 0.12), (w / 2, 0.12, H + rh * 0.86), M['stone'], smooth=False))
            for s in (-1, 1):
                p.append(sphere('volute', 0.22, (w / 2 + s * w * 0.31, -0.02, H + rh * 0.42), M['stone'], scale=(1, 0.5, 1), seg=16, rings=8))
                p.append(sphere('vase', 0.14, (w / 2 + s * w * 0.48, 0.0, H + 0.2), M['stone'], seg=12, rings=8))
        elif style == 'bell':
            p.append(sphere('crown', 0.16, (w / 2, 0.0, H + rh * 0.72 + (w * (0.5 - info)) * 0.9 + 0.12), M['stone'], seg=12, rings=8))
        elif style == 'spout':
            p.append(box('spoutcap', (w * 0.28, 0.38, 0.1), (w / 2, 0.15, H + rh + 0.05), M['stone'], smooth=False))
        if rh > 2.6:
            p += window(w / 2, H + rh * 0.32, min(0.85, w * 0.17), 1.25, frame)
            p.append(box('hoist', (0.14, 0.8, 0.14), (w / 2, -0.35, H + rh * (0.62 if style != 'neck' else 0.7)), M['wood'], smooth=False))
    else:  # flat cornice
        p.append(box('cornice', (w + 0.2, 0.5, 0.5), (w / 2, -0.1, H - 0.1), M['stone'], smooth=False))
        p.append(box('cornice2', (w + 0.3, 0.6, 0.12), (w / 2, -0.12, H + 0.2), M['stone'], smooth=False))
        for i in range(int(w / 0.35)):
            p.append(box('dentil', (0.12, 0.1, 0.12), (0.2 + i * 0.35, -0.38, H - 0.4), M['stone'], smooth=False))
        p += pitched_roof(w, 1.0, d, H + 0.25, w * 0.35, roof, wall)
    o = join(p, name)
    return o, H


# ================================================================ rows of houses

BUILDINGS = []


def row(a, b, facing, depth=10.0, floors=(2, 4), shop_chance=0.6, widths=(4.8, 7.4), sidewalk=True, prefix='House'):
    """Fill the facade line a->b with houses facing `facing` (2D unit vector)."""
    a, b, f = V(a), V(b), V(facing).normalized()
    ang = math.atan2(f.y, f.x) + math.pi / 2
    lx = V((math.cos(ang), math.sin(ang)))
    if (b - a).dot(lx) < 0:
        a, b = b, a
    L = (b - a).length
    ws = []
    while sum(ws) < L - widths[1]:
        ws.append(rng.uniform(*widths))
    rest = L - sum(ws)
    if rest < widths[0] * 0.8 and ws:
        ws[-1] += rest
    else:
        ws.append(rest)
    off = 0.0
    for w in ws:
        shop = None
        if rng.random() < shop_chance:
            shop = {'name': SHOPS.pop(0) if SHOPS else 'WINKEL', 'frame': rng.choice(['frame_green', 'door_black', 'door_red', 'door_blue', 'frame_cream']),
                    'sign': rng.choice(SIGNS), 'awning': rng.choice(AWNINGS) if rng.random() < 0.7 else None}
        o, _ = house(f'{prefix}_{len(BUILDINGS):02d}', w, depth, rng.randint(*floors), rng.choice(GABLES), rng.choice(WALLS),
                     rng.choice(FRAMES), shop=shop, shutters=rng.choice([None, None, None, 'shutter_green', 'shutter_red']))
        pos = a + lx * off
        o.location = (pos.x, pos.y, 0)
        o.rotation_euler = (0, 0, ang)
        lib.box_uv(o, 2.0)
        BUILDINGS.append(o)
        off += w
    if sidewalk:
        mid = (a + b) / 2 + f * 1.0
        sw = box('sidewalk', (L, 2.0, 0.1), (mid.x, mid.y, 0.05), M['tegels'], rot=(0, 0, ang), smooth=False)
        cm = (a + b) / 2 + f * 2.05
        curb = box('curb', (L, 0.14, 0.12), (cm.x, cm.y, 0.06), M['curb'], rot=(0, 0, ang), smooth=False)
        SIDEWALKS.extend([sw, curb])


SIDEWALKS = []


def cafe_pleintje():
    """The player's café, behind the player on the south side."""
    w = 8.0
    o, H = house('Cafe_Pleintje', w, 10, 2, 'cornice', 'brick_brown', 'frame_cream',
                 shop={'name': "CAFE 'T PLEINTJE", 'frame': 'frame_green', 'sign': 'sign_green', 'awning': ('fab_green', 'fab_cream')})
    ang = math.pi  # faces +Y
    o.location = (w / 2, -14, 0)
    o.rotation_euler = (0, 0, ang)
    lib.box_uv(o, 2.0)
    BUILDINGS.append(o)
    SIDEWALKS.append(box('sidewalk', (w, 2.0, 0.1), (0, -13, 0.05), M['tegels'], smooth=False))


# ================================================================ church

CHURCH_OFFSET = (4.0, 10.5, 0.0)


def church():
    p = []
    wall, trim = 'brick_brown', 'stone'
    # nave: long side faces the square (south, y=17.5)
    x0, x1, y0, y1, H = 9.5, 22.5, 17.5, 27.5, 11.0
    p.append(box('nave', (x1 - x0, y1 - y0, H), ((x0 + x1) / 2, (y0 + y1) / 2, H / 2), M[wall], smooth=False))
    roof = pitched_roof(y1 - y0, 0, x1 - x0, H, 6.5, 'roof_dark', wall, eave=0.5)
    r = join(roof, 'nave_roof_tmp')
    r.data.transform(Matrix.Rotation(-math.pi / 2, 4, 'Z'))
    r.location = (x0, y1, 0)
    p.append(r)
    for i in range(4):  # tall pointed windows + buttresses
        xc = x0 + 1.8 + i * 3.1
        # equilateral pointed (gothic) arch
        arch = [(-0.7, 0), (0.7, 0)]
        arch += [(-0.7 + 1.4 * math.cos(math.radians(a)), 4.2 + 1.4 * math.sin(math.radians(a))) for a in range(0, 60, 6)]
        arch += [(0.0, 4.2 + 1.4 * math.sin(math.radians(60)))]
        arch += [(0.7 - 1.4 * math.cos(math.radians(a)), 4.2 + 1.4 * math.sin(math.radians(a))) for a in range(54, -1, -6)]
        g = extrude_profile('cwindow', arch, 0.05, M['glass'])
        g.location = (xc, y0 - 0.03, 3.2)
        p.append(g)
        p.append(box('tracery', (0.08, 0.08, 5.3), (xc, y0 - 0.07, 3.2 + 2.65), M[trim], smooth=False))
        p.append(box('tracery', (1.4, 0.08, 0.08), (xc, y0 - 0.07, 3.2 + 3.0), M[trim], smooth=False))
        p.append(box('csill', (1.7, 0.25, 0.12), (xc, y0 - 0.12, 3.15), M[trim], smooth=False))
        bx = xc + 1.55
        if bx < x1 - 0.3:
            p.append(box('buttress', (0.6, 0.9, 7.5), (bx, y0 - 0.45, 3.75), M[wall], smooth=False))
            p.append(box('buttress_cap', (0.7, 1.0, 0.15), (bx, y0 - 0.45, 7.55), M[trim], rot=(math.radians(-20), 0, 0), smooth=False))
    p.append(box('cornice', (x1 - x0, 0.35, 0.3), ((x0 + x1) / 2, y0 - 0.15, H), M[trim], smooth=False))

    # tower
    tx, ty, tw = 7.6, 21.0, 4.6
    z = 0.0
    for i, (h, ww) in enumerate(((11, tw), (8, tw - 0.5), (8, tw - 1.0))):
        p.append(box('tower', (ww, ww, h), (tx, ty, z + h / 2), M[wall], smooth=False))
        p.append(box('tower_band', (ww + 0.25, ww + 0.25, 0.3), (tx, ty, z + h), M[trim], smooth=False))
        if i == 0:  # entrance portal facing the square
            p.append(box('portal', (1.8, 0.1, 3.2), (tx, ty - ww / 2 - 0.05, 1.6), M['door_black'], smooth=False))
            p.append(box('portal_frame', (2.4, 0.2, 0.35), (tx, ty - ww / 2 - 0.1, 3.4), M[trim], smooth=False))
        for s in (-1, 1):
            for fdir in ('x', 'y'):
                off = ww / 2 + 0.03
                if i == 2:  # belfry louvres
                    for k in range(5):
                        lz = z + 2.0 + k * 0.5
                        loc = (tx + s * off, ty, lz) if fdir == 'x' else (tx, ty + s * off, lz)
                        size = (0.06, 1.3, 0.12) if fdir == 'x' else (1.3, 0.06, 0.12)
                        p.append(box('louvre', size, loc, M['wood'], smooth=False))
                    # clock faces
                    cz = z + 6.2
                    loc = (tx + s * (off + 0.02), ty, cz) if fdir == 'x' else (tx, ty + s * (off + 0.02), cz)
                    rot = (0, math.pi / 2, 0) if fdir == 'x' else (math.pi / 2, 0, 0)
                    p.append(cyl('clock', 0.85, 0.06, loc, M['clock'], rot=rot, seg=32))
                    p.append(torus('clock_ring', 0.85, 0.06, loc, M['gold'], rot=rot, segU=32, segV=6))
                    hand_off = V((s * 0.05, 0, 0)) if fdir == 'x' else V((0, s * 0.05, 0))
                    p.append(box('hand_h', (0.06, 0.06, 0.5) if fdir == 'x' else (0.06, 0.06, 0.5), V(loc) + hand_off + V((0, 0, 0.22)), M['iron'], smooth=False))
                    p.append(box('hand_m', (0.05, 0.6, 0.05) if fdir == 'x' else (0.6, 0.05, 0.05), V(loc) + hand_off + V((0, 0, 0)) +
                                 (V((0, 0.28, 0)) if fdir == 'x' else V((0.28, 0, 0))), M['iron'], smooth=False))
                elif i == 1:
                    loc = (tx + s * off, ty, z + 4) if fdir == 'x' else (tx, ty + s * off, z + 4)
                    size = (0.05, 0.6, 2.2) if fdir == 'x' else (0.6, 0.05, 2.2)
                    p.append(box('slit', size, loc, M['glass'], smooth=False))
        z += h
    # spire with corner pinnacles, orb and weathercock
    p.append(cyl('spire', 2.3, 15.0, (tx, ty, z + 7.5), M['copper'], seg=8, r2=0.05, smooth=False))
    for sx in (-1, 1):
        for sy in (-1, 1):
            p.append(cyl('pinnacle', 0.3, 2.2, (tx + sx * 1.6, ty + sy * 1.6, z + 1.1), M['copper'], seg=8, r2=0.02, smooth=False))
    p.append(sphere('orb', 0.28, (tx, ty, z + 15.2), M['gold'], seg=16, rings=8))
    p.append(tube('rod', (tx, ty, z + 15), (tx, ty, z + 16.6), 0.04, M['gold'], seg=6))
    cock = extrude_profile('cock', [(-0.5, 0), (0.4, 0), (0.55, 0.35), (0.25, 0.3), (0.1, 0.65), (-0.2, 0.4), (-0.55, 0.6)], 0.04, M['gold'])
    cock.location = (tx, ty, z + 16.6)
    p.append(cock)
    o = join(p, 'Church')
    o.location = CHURCH_OFFSET  # set back behind the north row so the tower rises above the rooftops
    lib.box_uv(o, 2.0)
    return o


# ================================================================ props (one mesh each, instanced)

def prop_tree():
    p = [tube('trunk', (0, 0, 0), (0, 0, 3.4), 0.2, M['bark'], r2=0.13, seg=10)]
    for a in range(4):
        ang = a * math.pi / 2 + 0.4
        p.append(tube('branch', (0, 0, 2.6), (math.cos(ang) * 1.1, math.sin(ang) * 1.1, 4.3), 0.08, M['bark'], r2=0.04, seg=6))
    blobs = []
    greens = ['leaf', 'leaf', 'leaf_dark', 'leaf_light']
    for i in range(34):
        d = V((rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(-0.7, 1))).normalized() * rng.uniform(0.75, 1.0)
        c = V((0, 0, 5.3)) + V((d.x * 2.2, d.y * 2.2, d.z * 1.7))
        blobs.append(ico('canopy', rng.uniform(0.7, 1.1), c, M[greens[i % 4]], subdiv=2))
    can = join(blobs, 'canopy_tmp')
    tex = bpy.data.textures.new('LeafNoise', 'CLOUDS')
    tex.noise_scale = 0.28
    d = can.modifiers.new('leafy', 'DISPLACE')
    d.texture = tex
    d.strength = 0.3
    p.append(can)
    p.append(box('grate', (1.4, 1.4, 0.04), (0, 0, 0.02), M['iron'], smooth=False))
    return join(p, 'Tree')


def prop_parasol(fabric):
    p = [tube('pole', (0, 0, 0), (0, 0, 2.55), 0.025, M['wood_light'], seg=8),
         cyl('canopy', 1.55, 0.5, (0, 0, 2.45), M[fabric], seg=8, r2=0.04, smooth=False),
         cyl('valance', 1.56, 0.2, (0, 0, 2.12), M[fabric], seg=8, caps=False, smooth=False),
         sphere('finial', 0.05, (0, 0, 2.72), M['wood_light'], seg=8, rings=4),
         cyl('base', 0.28, 0.08, (0, 0, 0.04), M['iron'], seg=12)]
    return join(p, f'Parasol_{fabric}')


def prop_table(r=0.33, name='BistroTable'):
    p = [cyl('top', r, 0.03, (0, 0, 0.74), M['marble'], seg=24),
         tube('leg', (0, 0, 0), (0, 0, 0.73), 0.03, M['iron'], seg=8)]
    for a in range(4):
        ang = a * math.pi / 2
        p.append(tube('foot', (0, 0, 0.03), (math.cos(ang) * 0.25, math.sin(ang) * 0.25, 0.01), 0.018, M['iron'], seg=6))
    return join(p, name)


def prop_chair():
    """Rattan bistro chair, facing +X."""
    p = [cyl('seat', 0.21, 0.04, (0, 0, 0.46), M['rattan'], seg=16)]
    for sx in (-1, 1):
        for sy in (-1, 1):
            p.append(tube('leg', (sx * 0.14, sy * 0.14, 0.45), (sx * 0.18, sy * 0.18, 0), 0.014, M['wood'], seg=6))
    back = torus('back', 0.2, 0.018, (-0.02, 0, 0.62), M['wood'], segU=16, segV=6, arc=(math.radians(110), math.radians(250)))
    p.append(back)
    p.append(_scale(torus('backrest', 0.2, 0.02, (-0.02, 0, 0.82), M['rattan'], segU=16, segV=6, arc=(math.radians(110), math.radians(250))), (1, 1, 2.5)))
    for a in (150, 210):
        r = math.radians(a)
        p.append(tube('backpost', (math.cos(r) * 0.2 - 0.02, math.sin(r) * 0.2, 0.47), (math.cos(r) * 0.21 - 0.03, math.sin(r) * 0.21, 0.86), 0.013, M['wood'], seg=6))
    return join(p, 'BistroChair')


def _scale(o, s):
    o.scale = s
    return o


def prop_omafiets(frame):
    p = []
    for x in (-0.55, 0.55):
        w = torus('wheel', 0.33, 0.02, (x, 0, 0.35), M['rubber'], segU=32, segV=6, rot=(math.pi / 2, 0, 0))
        p.append(w)
        p.append(torus('rim', 0.3, 0.008, (x, 0, 0.35), M['chrome'], segU=32, segV=4, rot=(math.pi / 2, 0, 0)))
        p.append(_scale(torus('fender', 0.36, 0.02, (x, 0, 0.35), M[frame], segU=16, segV=4, rot=(math.pi / 2, 0, 0),
                              arc=(math.radians(20 if x > 0 else 0), math.radians(160 if x > 0 else 180))), (1, 1, 1)))
    bb, seat, head = V((0.0, 0, 0.33)), V((-0.15, 0, 0.85)), V((0.42, 0, 0.92))
    F = M[frame]
    p += [tube('t', (-0.55, 0, 0.35), bb, 0.016, F, seg=8), tube('t', bb, seat, 0.02, F, seg=8),
          tube('t', (-0.55, 0, 0.35), seat, 0.014, F, seg=8), tube('t', bb + V((0.05, 0, 0.05)), head + V((0, 0, -0.12)), 0.022, F, seg=8),
          tube('t', (0.0, 0, 0.55), head + V((0, 0, -0.02)), 0.02, F, seg=8), tube('fork', head, (0.55, 0, 0.35), 0.016, F, seg=8),
          tube('stem', head, head + V((-0.03, 0, 0.18)), 0.014, M['chrome'], seg=6)]
    bar = head + V((-0.03, 0, 0.18))
    for s in (-1, 1):
        p.append(tube('bar', bar, bar + V((-0.22, s * 0.28, 0.02)), 0.011, M['chrome'], seg=6))
    p.append(box('saddle', (0.26, 0.14, 0.07), seat + V((0, 0, 0.06)), M['rubber'], smooth=False))
    p.append(box('rack', (0.4, 0.16, 0.02), (-0.5, 0, 0.72), M['chrome'], smooth=False))
    p.append(tube('rackstay', (-0.55, 0, 0.35), (-0.62, 0, 0.72), 0.008, M['chrome'], seg=4))
    p.append(box('chainguard', (0.6, 0.03, 0.1), (-0.27, -0.06, 0.34), F, smooth=False))
    p.append(cyl('lamp', 0.05, 0.08, head + V((0.06, 0, -0.08)), M['chrome'], rot=(0, math.pi / 2, 0), seg=10))
    return join(p, f'Omafiets_{frame}')


def prop_lamp():
    p = [cyl('base', 0.2, 0.5, (0, 0, 0.25), M['iron'], seg=12, r2=0.12),
         tube('pole', (0, 0, 0.5), (0, 0, 4.0), 0.07, M['iron'], r2=0.05, seg=10),
         sphere('knob', 0.09, (0, 0, 4.0), M['iron'], seg=10, rings=6),
         box('lantern', (0.32, 0.32, 0.45), (0, 0, 4.35), M['lamp_glow'], smooth=False),
         cyl('roof', 0.3, 0.25, (0, 0, 4.7), M['iron'], seg=4, r2=0.03, rot=(0, 0, math.pi / 4), smooth=False),
         box('lantern_base', (0.36, 0.36, 0.05), (0, 0, 4.12), M['iron'], smooth=False)]
    for s in (-1, 1):
        p.append(_scale(torus('scroll', 0.2, 0.018, (s * 0.2, 0, 3.75), M['iron'], segU=12, segV=4, rot=(math.pi / 2, 0, 0)), (1, 1, 1)))
        # hanging summer flower basket
        c = V((s * 0.55, 0, 3.2))
        p.append(tube('basket_arm', (s * 0.05, 0, 3.6), c + V((0, 0, 0.4)), 0.015, M['iron'], seg=6))
        p.append(sphere('basket', 0.25, c, M['bark'], scale=(1, 1, 0.6), seg=12, rings=6))
        for i in range(14):
            d = V((rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(-0.6, 0.8))).normalized()
            p.append(ico('bloom', rng.uniform(0.06, 0.09), c + d * 0.27, M[rng.choice(['flower_red', 'flower_pink', 'flower_white', 'leaf'])], subdiv=1))
    return join(p, 'StreetLamp')


def prop_bollard():
    p = [cyl('body', 0.07, 0.75, (0, 0, 0.375), M['bollard'], seg=12, r2=0.06),
         sphere('top', 0.075, (0, 0, 0.78), M['bollard'], seg=12, rings=6)]
    for z in (0.5, 0.6):
        p.append(torus('ring', 0.066, 0.01, (0, 0, z), M['bollard'], segU=12, segV=4))
    return join(p, 'Amsterdammertje')


def prop_bench():
    p = []
    for i in range(3):
        p.append(box('slat', (1.8, 0.12, 0.04), (0, -0.15 + i * 0.15, 0.45), M['wood_light'], smooth=False))
    for i in range(2):
        p.append(box('backslat', (1.8, 0.03, 0.12), (0, 0.24, 0.62 + i * 0.17), M['wood_light'], rot=(math.radians(-12), 0, 0), smooth=False))
    for s in (-0.8, 0.8):
        p.append(box('side', (0.06, 0.55, 0.45), (s, 0, 0.225), M['iron'], smooth=False))
        p.append(box('sideback', (0.06, 0.06, 0.5), (s, 0.25, 0.65), M['iron'], rot=(math.radians(-12), 0, 0), smooth=False))
    return join(p, 'Bench')


def prop_bin():
    return join([cyl('bin', 0.24, 0.85, (0, 0, 0.45), M['bin_green'], seg=16),
                 cyl('lid', 0.27, 0.06, (0, 0, 0.9), M['bin_green'], seg=16),
                 tube('post', (0, 0.26, 0), (0, 0.26, 1.0), 0.03, M['iron'], seg=6)], 'Bin')


def prop_planter():
    p = [cyl('pot', 0.55, 0.5, (0, 0, 0.25), M['stone'], seg=16, r2=0.62)]
    p.append(cyl('soil', 0.57, 0.02, (0, 0, 0.5), M['bark'], seg=16))
    for i in range(16):
        a, r = rng.uniform(0, 2 * math.pi), rng.uniform(0, 0.45)
        p.append(ico('leaf', rng.uniform(0.12, 0.18), (math.cos(a) * r, math.sin(a) * r, 0.6), M['leaf'], subdiv=1))
    for i in range(22):
        a, r = rng.uniform(0, 2 * math.pi), rng.uniform(0, 0.48)
        p.append(ico('bloom', rng.uniform(0.05, 0.08), (math.cos(a) * r, math.sin(a) * r, 0.68 + rng.uniform(0, 0.12)),
                     M[rng.choice(['flower_red', 'flower_red', 'flower_pink', 'flower_yellow', 'flower_white'])], subdiv=1))
    return join(p, 'Planter')


def prop_rack():
    p = []
    for i in range(6):
        p.append(torus('hoop', 0.35, 0.02, (i * 0.7, 0, 0.35), M['chrome'], segU=12, segV=4, rot=(math.pi / 2, 0, 0),
                       arc=(0, math.pi)))
    return join(p, 'BikeRack')


def fountain():
    p = [cyl('basin', 3.3, 0.6, (0, 0, 0.3), M['stone_warm'], seg=8, smooth=False),
         cyl('basin_cap', 3.45, 0.12, (0, 0, 0.62), M['stone_warm'], seg=8, smooth=False),
         cyl('water', 3.05, 0.04, (0, 0, 0.5), M['water'], seg=8, smooth=False),
         cyl('pedestal', 0.65, 1.3, (0, 0, 0.65), M['stone_warm'], seg=8, smooth=False),
         cyl('bowl', 0.35, 0.4, (0, 0, 1.45), M['stone_warm'], seg=16, r2=1.4),
         cyl('bowl_water', 1.32, 0.03, (0, 0, 1.63), M['water'], seg=16),
         tube('column', (0, 0, 1.6), (0, 0, 2.9), 0.22, M['stone_warm'], r2=0.16, seg=12),
         cyl('bowl2', 0.15, 0.25, (0, 0, 2.95), M['stone_warm'], seg=16, r2=0.6),
         cyl('bowl2_water', 0.58, 0.02, (0, 0, 3.06), M['water'], seg=16)]
    # bronze figure on top: a cheerful classic cyclist, the anti-fatbiker
    p.append(sphere('statue_body', 0.18, (0, 0, 3.55), M['bronze'], scale=(1, 0.8, 1.4)))
    p.append(sphere('statue_head', 0.13, (0, 0, 3.9), M['bronze']))
    p.append(cyl('statue_hat', 0.16, 0.04, (0, 0, 4.0), M['bronze'], seg=16))
    p.append(cyl('statue_hat_top', 0.1, 0.12, (0, 0, 4.07), M['bronze'], seg=16))
    for s in (-1, 1):
        p.append(tube('statue_arm', (0, s * 0.15, 3.65), (0.25, s * 0.25, 3.45), 0.045, M['bronze'], seg=8))
        p.append(tube('statue_leg', (0, s * 0.08, 3.35), (0.05, s * 0.1, 3.08), 0.06, M['bronze'], seg=8))
    p.append(torus('statue_wheel', 0.25, 0.02, (0.35, 0, 3.3), M['bronze'], rot=(math.pi / 2, 0, 0), segU=24, segV=4))
    p.append(torus('statue_wheel', 0.25, 0.02, (-0.35, 0, 3.3), M['bronze'], rot=(math.pi / 2, 0, 0), segU=24, segV=4))
    for i in range(8):  # spouts
        a = i * math.pi / 4
        p.append(tube('spout', (math.cos(a) * 1.25, math.sin(a) * 1.25, 1.62), (math.cos(a) * 1.5, math.sin(a) * 1.5, 1.58), 0.03, M['bronze'], seg=6))
    return join(p, 'Fountain')


def flag(base, out_dir):
    """Dutch flag on an angled pole sticking out of a facade."""
    base, d = V(base), V((out_dir[0], out_dir[1], 0)).normalized()
    tip = base + d * 2.0 + V((0, 0, 1.4))
    p = [tube('flagpole', base, tip, 0.025, M['wood_light'], seg=6), sphere('flagknob', 0.04, tip, M['gold'], seg=8, rings=4)]
    pole_dir = (tip - base).normalized()
    ang = math.atan2(d.y, d.x)
    for i, m in enumerate(('flag_red', 'flag_white', 'flag_blue')):
        c = base + pole_dir * 1.5 - V((0, 0, 0.17 + i * 0.3))
        fl = box('flag', (1.2, 0.015, 0.3), c, M[m], smooth=False)
        fl.rotation_euler = (0, -math.atan2(pole_dir.z, math.hypot(pole_dir.x, pole_dir.y)) * 0.25, ang)
        p.append(fl)
    return join(p, 'Flag')


def bunting(a, b, sag=1.0, name='Bunting'):
    a, b = V(a), V(b)
    p = []
    n = int((b - a).length / 0.5)
    pts = []
    for i in range(n + 1):
        t = i / n
        pts.append(a.lerp(b, t) - V((0, 0, sag * 4 * t * (1 - t))))
    for i in range(n):
        p.append(tube('string', pts[i], pts[i + 1], 0.008, M['iron'], seg=4))
    d = (b - a).normalized()
    ang = math.atan2(d.y, d.x)
    cols = ['fab_red', 'fab_yellow', 'fab_blue', 'fab_green', 'fab_orange', 'flag_white']
    for i in range(n):
        tri = extrude_profile('pennant', [(-0.17, 0), (0.17, 0), (0, -0.38)], 0.01, M[cols[i % len(cols)]])
        mid = (pts[i] + pts[i + 1]) / 2
        tri.location = mid
        tri.rotation_euler = (0, 0, ang)
        p.append(tri)
    return join(p, name)


# ================================================================ scene assembly

def build():
    lib.reset_scene()
    make_materials()
    root = lib.empty('Square')
    groups = {k: lib.empty(k, parent=root) for k in ('Ground', 'Buildings', 'Props', 'Markers')}

    # --- ground
    ground = box('Ground_Klinkers', (140, 95, 0.2), (0, 15, -0.1), M['klinkers'], smooth=False)
    lib.box_uv(ground, 2.0)
    lib.set_parent(ground, groups['Ground'])

    # --- square facades
    D = 10.0
    row((-22, -14), (-4, -14), (0, 1), D, prefix='Square')
    cafe_pleintje()
    row((4, -14), (22, -14), (0, 1), D, prefix='Square')
    row((-22, -14), (-22, -8), (1, 0), D, prefix='Square')
    row((-22, -1), (-22, 16), (1, 0), D, prefix='Square')
    row((22, -14), (22, -8), (-1, 0), D, prefix='Square')
    row((22, -1), (22, 6), (-1, 0), D, prefix='Square')
    row((22, 8.5), (22, 16), (-1, 0), D, prefix='Square')
    row((-22, 16), (-14.5, 16), (0, -1), D, prefix='Square')
    row((-12, 16), (-5, 16), (0, -1), D, prefix='Square')
    # --- streets (start past the corner houses' depth)
    S = 22 + D + 0.2
    row((-S, -8), (-60, -8), (0, 1), 9, shop_chance=0.35, prefix='StreetW')
    row((-S, -1), (-60, -1), (0, -1), 9, shop_chance=0.35, prefix='StreetW')
    row((-60, -8), (-60, -1), (1, 0), 9, shop_chance=0.0, prefix='StreetW')
    row((S, -8), (60, -8), (0, 1), 9, shop_chance=0.35, prefix='StreetE')
    row((S, -1), (60, -1), (0, -1), 9, shop_chance=0.35, prefix='StreetE')
    row((60, -8), (60, -1), (-1, 0), 9, shop_chance=0.0, prefix='StreetE')
    row((-5, 16 + D + 0.2), (-5, 56), (1, 0), 9, shop_chance=0.4, prefix='StreetN')
    row((5, 16), (22, 16), (0, -1), D, prefix='Square')
    row((5, 37), (5, 56), (-1, 0), 9, shop_chance=0.4, prefix='StreetN')
    row((-5, 56), (5, 56), (0, -1), 9, shop_chance=0.0, prefix='StreetN')
    row((-14.5, 16 + D + 0.2), (-14.5, 42), (1, 0), 8, floors=(2, 3), shop_chance=0.2, widths=(4.0, 5.5), prefix='AlleyNW')
    row((-12, 16 + D + 0.2), (-12, 42), (-1, 0), 8, floors=(2, 3), shop_chance=0.2, widths=(4.0, 5.5), prefix='AlleyNW')
    row((-14.5, 42), (-12, 42), (0, -1), 8, floors=(2, 2), shop_chance=0.0, widths=(2.5, 2.5), sidewalk=False, prefix='AlleyNW')
    row((S, 6), (46, 6), (0, 1), 8, floors=(2, 3), shop_chance=0.2, widths=(4.0, 5.5), prefix='AlleyE')
    row((S, 8.5), (46, 8.5), (0, -1), 8, floors=(2, 3), shop_chance=0.2, widths=(4.0, 5.5), prefix='AlleyE')
    row((46, 6), (46, 8.5), (-1, 0), 8, floors=(2, 2), shop_chance=0.0, widths=(2.5, 2.5), sidewalk=False, prefix='AlleyE')
    ch = church()
    for o in BUILDINGS + [ch]:
        lib.set_parent(o, groups['Buildings'])
    for o in SIDEWALKS:
        lib.box_uv(o, 1.8)
    sw = join(SIDEWALKS, 'Ground_Sidewalks')
    lib.box_uv(sw, 1.8)
    # curbs got the tile texture too; fine at this scale
    lib.set_parent(sw, groups['Ground'])

    # --- props
    props = []
    P = lambda src, loc, rz=0.0, s=1.0: props.append(instance(src, src.name + '_i', loc, rz, s))
    tree, lamp, bollard, bench, binm, planter, rack = (prop_tree(), prop_lamp(), prop_bollard(), prop_bench(),
                                                         prop_bin(), prop_planter(), prop_rack())
    table, chair = prop_table(), prop_chair()
    parasols = {f: prop_parasol(f) for f in ('fab_cream', 'fab_red', 'fab_green', 'fab_blue')}
    bikes = [prop_omafiets(f) for f in ('bike_black', 'bike_green', 'bike_blue', 'bike_red')]
    templates = [tree, lamp, bollard, bench, binm, planter, rack, table, chair] + list(parasols.values()) + bikes

    for x, y in ((-17, -10.5), (-17.5, 11), (17, -10.5), (17.5, 12.5), (-9, 12.5), (13.5, 11.5)):
        P(tree, (x, y, 0), rng.uniform(0, 6.28), rng.uniform(0.9, 1.1))
    for y in (24, 32, 40, 48):
        P(tree, (-3.2, y, 0), rng.uniform(0, 6.28), 0.85)
    for x, y in ((-12, -10.5), (12, -10.5), (-19.5, 3), (19.5, 3), (-8, 13.5), (9, 13.5), (-19.5, -6), (19.5, -6)):
        P(lamp, (x, y, 0))
    for x in range(-58, -33, 2):
        P(bollard, (x, -5.8, 0)); P(bollard, (x, -3.2, 0))
    for x in range(34, 59, 2):
        P(bollard, (x, -5.8, 0)); P(bollard, (x, -3.2, 0))
    for y in range(28, 55, 2):
        P(bollard, (-2.8, y, 0)); P(bollard, (2.8, y, 0))
    for x, y in ((-6, -9.6), (6, -9.6), (-19.8, 7), (19.8, -11)):
        P(binm, (x, y, 0))
    fo = fountain()
    fo.location = (0, 3, 0)
    props.append(fo)
    # bike racks with parked omafietsen
    for (x, y, rz) in ((-19.6, -11.8, math.pi / 2),):
        P(rack, (x, y, 0), rz)
        for i in range(6):
            if rng.random() < 0.8:
                off = V((math.cos(rz), math.sin(rz))) * (i * 0.7)
                P(rng.choice(bikes), (x + off.x, y + off.y, 0), rz + math.pi / 2 + rng.uniform(-0.08, 0.08))

    # terraces: (centre, facing angle of the facade normal, n tables, parasol fabric)
    def terrace(cx, cy, along, n, fabric, skip=()):
        ax = V((math.cos(along), math.sin(along)))
        for i in range(n):
            if i in skip:
                continue
            c = V((cx, cy)) + ax * ((i - (n - 1) / 2) * 1.9)
            P(table, (c.x, c.y, 0))
            for s in (-1, 1):
                q = c + ax * (s * 0.55)
                P(chair, (q.x, q.y, 0), along + (math.pi if s > 0 else 0))
            if i % 2 == 0:
                P(parasols[fabric], (c.x, c.y, 0), rng.uniform(0, 1))

    terrace(0, -10.9, 0.0, 5, 'fab_green', skip=(2,))          # player's café (middle table is the player's own)
    terrace(-19.0, 9.0, math.pi / 2, 4, 'fab_red')               # west side
    terrace(19.0, 1.5, math.pi / 2, 3, 'fab_blue')               # east
    # the player's own table + chair (chair hidden in-game, the camera sits there)
    small = prop_table(0.23, 'PlayerTableMesh')
    templates.append(small)
    pt = instance(small, 'Player_Table', (-0.38, -11.0, 0)); props.append(pt)
    pc = instance(chair, 'Player_Chair', (0, -11.55, 0), math.pi / 2); props.append(pc)
    pp = instance(parasols['fab_green'], 'Player_Parasol', (-1.1, -11.6, 0)); props.append(pp)

    # festive details
    flags = [flag((-17.0, 15.95, 5.0), (0, -1)), flag((-21.9, 4.0, 5.2), (1, 0)), flag((21.9, -11.0, 5.0), (-1, 0)),
             flag((-4.9, 30, 5.0), (1, 0)), flag((10.0, -13.9, 5.0), (0, 1))]
    props += flags
    props.append(bunting((-5, 17.5, 7.0), (5, 17.5, 7.0), 1.0, 'Bunting_N'))
    props.append(bunting((-23, -8, 6.5), (-23, -1, 6.5), 0.8, 'Bunting_W'))
    props.append(bunting((23, -8, 6.5), (23, -1, 6.5), 0.8, 'Bunting_E'))
    props.append(bunting((-14.5, 28, 5.5), (-12, 28, 5.5), 0.4, 'Bunting_Alley'))

    for o in props:
        lib.set_parent(o, groups['Props'])
    # templates live at the origin; keep them out of the export
    for t in templates:
        t.location = (0, 0, -100)

    # --- markers for the game
    markers = {
        'PlayerEye': (0, -11.55, 1.2),
        'Spawn_West': (-56, -4.5, 0), 'Spawn_East': (56, -4.5, 0), 'Spawn_North': (0, 52, 0),
        'Spawn_AlleyNW': (-13.25, 38, 0), 'Spawn_AlleyE': (42, 7.25, 0),
        'Square_Center': (0, 3, 0),
    }
    for name, loc in markers.items():
        lib.empty(name, loc, parent=groups['Markers'])
    return root, templates


def main():
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    root, templates = build()
    scene = bpy.context.scene
    objs = [root] + list(root.children_recursive)
    meshes = [o for o in objs if o.type == 'MESH']
    print(f'[square] buildings: {len(BUILDINGS)}, objects: {len(objs)}, triangles: {lib.tri_count(meshes)}')
    out = os.path.join(ROOT, 'assets', 'models', 'square.glb')
    lib.export_glb(out, objs)
    print(f'[square] exported {out} ({os.path.getsize(out) / 1e6:.1f} MB)')
    for t in templates:
        t.hide_render = True
    if '--no-render' in argv:
        return
    stage = lib.preview_stage(scene, size=(1600, 900))
    bpy.data.objects['PreviewGround'].hide_render = True
    sun = bpy.data.objects['Sun']
    sun.rotation_euler = (math.radians(58), 0, math.radians(-40))
    sun.data.energy = 6.5
    bpy.data.objects['Fill'].hide_render = True
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ROOT, 'blender', 'square.blend'))
    rdir = os.path.join(ROOT, 'renders', 'square')
    eye = V((0, -11.55, 1.2))
    shots = [
        ('01_player_view', eye, eye + V((0, 10, -0.6)), 20),
        ('02_overview', (0, -26, 34), (0, 8, 0), 24),
        ('03_look_left', eye, eye + V((-10, 4, -0.3)), 22),
        ('04_look_right', eye, eye + V((10, 4, -0.3)), 22),
        ('05_north_street', (1.5, 6, 1.7), (0, 30, 4), 24),
        ('06_facades', (-4, 4, 1.7), (-13, 16, 5), 28),
        ('07_player_up', eye, eye + V((2, 10, 2.2)), 20),
    ]
    for name, loc, tgt, lens in shots:
        lib.render(scene, lib.camera('Cam_' + name, tuple(loc), tuple(tgt), lens), os.path.join(rdir, name + '.png'))


if __name__ == '__main__':
    main()
