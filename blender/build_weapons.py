"""First-person weapon viewmodels (with hands) + the ice cream on the player's table.

Viewmodel space: camera at the origin looking +X, +Z up. Each weapon is modelled in its own
frame (barrel along +X, origin at the trigger/grip) and its root is placed in camera space.
Separate named parts can be animated in-game (pump, bolt, bands, rocket, stone, shell).

Run:  Blender -b -P blender/build_weapons.py [-- --no-render]
"""
import math
import os
import sys

import bpy
from mathutils import Euler, Vector

sys.path.insert(0, os.path.dirname(__file__))
import lib  # noqa: E402
from lib import (basis, box, capsule, cyl, extrude_profile, join, lathe, material, orient_basis,  # noqa: E402
                 sphere, subsurf, text_mesh, torus, tube)

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
V = Vector
M = {}


def make_materials():
    M.update({
        'skin': material('PlayerSkin', '#e2ab86', rough=0.5, sss=0.1),
        'nail': material('Nail', '#f0c9b4', rough=0.3),
        'watch_strap': material('WatchStrap', '#1c1c1c', rough=0.6),
        'watch_face': material('WatchFace', '#f4f1e8', rough=0.2),
        'steel': material('GunSteel', '#2c2f34', rough=0.32, metal=0.85),
        'steel_light': material('GunSteelLight', '#9aa0a8', rough=0.25, metal=1.0),
        'blued': material('GunBlued', '#1e2430', rough=0.28, metal=0.9),
        'wood': material('GunWood', '#8a5229', rough=0.45, coat=0.6),
        'wood_dark': material('GunWoodDark', '#5a3218', rough=0.5, coat=0.5),
        'polymer': material('GunPolymer', '#2a2c2a', rough=0.6),
        'rubber': material('GunRubber', '#151515', rough=0.85),
        'olive': material('Olive', '#5f6e3b', rough=0.55, metal=0.2),
        'olive_dark': material('OliveDark', '#434e2a', rough=0.6, metal=0.2),
        'yellow': material('HazardYellow', '#f4c430', rough=0.5),
        'black': material('HazardBlack', '#161616', rough=0.5),
        'rocket': material('RocketRed', '#d9442b', rough=0.35, coat=0.5),
        'white': material('RocketWhite', '#f5f3ec', rough=0.4),
        'brass': material('Brass', '#d2aa45', rough=0.25, metal=1.0),
        'shell_red': material('ShellRed', '#c2262a', rough=0.4, coat=0.3),
        'lens': material('ScopeLens', '#2e6a9e', rough=0.03, metal=0.4, coat=1.0, emission='#1a4a7a', strength=0.3),
        'band': material('SlingBand', '#e0a83a', rough=0.5),
        'leather': material('Leather', '#6e3f20', rough=0.7),
        'stone': material('SlingStone', '#8c8a83', rough=0.85),
        'sling_wood': material('SlingWood', '#a46a35', rough=0.55, coat=0.3),
        'tape': material('GripTape', '#c43a2a', rough=0.7),
        # ice cream
        'glass': material('CoupeGlass', '#dff2ff', rough=0.03, coat=1.0),
        'strawberry': material('Strawberry', '#f28fb0', rough=0.65, sss=0.2),
        'vanilla': material('Vanilla', '#fbefc8', rough=0.65, sss=0.2),
        'chocolate': material('Chocolate', '#6b3b22', rough=0.55, sss=0.1),
        'sauce': material('ChocoSauce', '#3e1f10', rough=0.15, coat=0.8),
        'cream': material('WhippedCream', '#fffdf6', rough=0.6, sss=0.2),
        'cherry': material('Cherry', '#c8102e', rough=0.12, coat=1.0),
        'wafer': material('Wafer', '#dca35c', rough=0.7),
        'umbrella_a': material('UmbrellaPink', '#ff4fa3', rough=0.6),
        'umbrella_b': material('UmbrellaTeal', '#1fc2b8', rough=0.6),
        'spoon': material('Spoon', '#d8dade', rough=0.15, metal=1.0),
        'stem': material('CherryStem', '#5a7a2a', rough=0.7),
    })
    g = M['glass']
    b = next(n for n in g.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    b.inputs['Alpha'].default_value = 0.28
    for attr, val in (('surface_render_method', 'BLENDED'), ('blend_method', 'BLEND')):
        if hasattr(g, attr):
            try:
                setattr(g, attr, val)
            except TypeError:
                pass


# ================================================================ hands

def grip_hand(c, axis, palm, grip_r, wrap_via, elbow, watch=False):
    """A hand wrapped around a cylindrical grip, plus forearm to `elbow`."""
    c, axis, wrap_via, elbow = V(c), V(axis).normalized(), V(wrap_via), V(elbow)
    R = basis(palm, axis)
    px, py = R.col[0].to_3d(), R.col[1].to_3d()
    sign = 1 if py.dot(wrap_via) > 0 else -1
    sk = M['skin']
    p = []
    palm_c = c + px * (grip_r + 0.02)
    p.append(orient_basis(sphere('palm', 0.05, mat=sk, scale=(0.5, 0.95, 1.15), seg=20, rings=12), R, palm_c))
    widths = (0.0115, 0.012, 0.0115, 0.0098)
    for i, w in enumerate(widths):
        off = (i - 1.5) * 0.024
        arc = (0.15, 3.5) if sign > 0 else (-3.5, -0.15)
        f = torus('finger', grip_r + w * 0.9, w, mat=sk, segU=14, segV=8, arc=arc)
        orient_basis(f, R, c + axis * off)
        p.append(f)
        end_a = arc[1] if sign > 0 else arc[0]
        tip = c + axis * off + (px * math.cos(end_a) + py * math.sin(end_a)) * (grip_r + w * 0.9)
        p.append(sphere('tip', w, tip, sk, seg=10, rings=6))
        knuckle_a = (1.6 if sign > 0 else -1.6)
        kn = c + axis * off + (px * math.cos(knuckle_a) + py * math.sin(knuckle_a)) * (grip_r + w * 1.5)
        p.append(sphere('knuckle', w * 1.15, kn, sk, seg=10, rings=6))
    # thumb wraps the other way, over the top of the grip
    t0 = palm_c - axis * 0.035 + py * (-sign) * 0.015
    t1 = c - axis * 0.05 + (px * math.cos(-sign * 1.9) + py * math.sin(-sign * 1.9)) * (grip_r + 0.012)
    p.append(capsule('thumb', t0, t1, 0.014, 0.012, sk))
    # wrist + forearm
    fdir = (elbow - palm_c).normalized()
    wrist = palm_c + fdir * 0.07
    p.append(capsule('wrist', palm_c + fdir * 0.01, wrist, 0.036, 0.032, sk))
    p.append(capsule('forearm', wrist, elbow, 0.033, 0.045, sk))
    if watch:
        w = torus('watch_strap', 0.036, 0.008, mat=M['watch_strap'], segU=24, segV=6, rz=0.012)
        orient_basis(w, basis(px, fdir), wrist + fdir * 0.02)
        p.append(w)
        top = wrist + fdir * 0.02 - px * 0.038
        face = cyl('watch_face', 0.018, 0.01, mat=M['watch_face'], seg=20)
        orient_basis(face, basis(fdir, -px), top)
        p.append(face)
        bez = torus('watch_bezel', 0.018, 0.004, mat=M['steel_light'], segU=20, segV=6)
        orient_basis(bez, basis(fdir, -px), top - px * 0.004)
        p.append(bez)
    return p


def fist(c, fwd, up, elbow):
    """Closed fist (e.g. pinching the slingshot pouch)."""
    c, elbow = V(c), V(elbow)
    R = basis(V(up), V(fwd))
    sk = M['skin']
    p = [orient_basis(sphere('fist', 0.045, mat=sk, scale=(1.0, 0.85, 1.1), seg=20, rings=12), R, c)]
    f, u = V(fwd).normalized(), V(up).normalized()
    s = f.cross(u)
    for i in range(4):
        p.append(sphere('knuckle', 0.014, c + f * 0.04 + s * ((i - 1.5) * 0.02) + u * 0.01, sk, seg=10, rings=6))
    p.append(capsule('thumb', c + u * 0.03 - s * 0.03, c + f * 0.05 + u * 0.015, 0.014, 0.012, sk))
    fdir = (elbow - c).normalized()
    wrist = c + fdir * 0.07
    p.append(capsule('wrist', c, wrist, 0.035, 0.032, sk))
    p.append(capsule('forearm', wrist, elbow, 0.033, 0.045, sk))
    return p


# ================================================================ weapons (local frame: +X forward)

def katapult():
    W = M['sling_wood']
    frame = [capsule('handle', (0, 0, -0.1), (0, 0, 0.02), 0.017, 0.02, W)]
    for i in range(5):  # red grip tape wraps
        frame.append(torus('tape', 0.0195, 0.004, (0, 0, -0.085 + i * 0.018), M['tape'], segU=16, segV=6))
    frame.append(sphere('yoke', 0.026, (0, 0, 0.03), W, scale=(1, 1.3, 1)))
    tips = []
    for s in (-1, 1):
        a, b, c = V((0, s * 0.012, 0.035)), V((0.005, s * 0.05, 0.09)), V((0.0, s * 0.07, 0.17))
        frame.append(capsule('prong', a, b, 0.016, 0.014, W))
        frame.append(capsule('prong', b, c, 0.014, 0.012, W))
        frame.append(torus('prong_wrap', 0.0135, 0.004, c - V((0, 0, 0.02)), M['band'], segU=12, segV=6))
        tips.append(c - V((0, 0, 0.02)))
    pouch_c = V((-0.17, 0, 0.115))
    bands = []
    for s, t in zip((-1, 1), tips):
        bands.append(tube('band', t, pouch_c + V((0, s * 0.022, 0)), 0.0055, M['band'], seg=8))
    pouch = [sphere('pouch', 0.03, pouch_c, M['leather'], scale=(0.5, 1.1, 0.8))]
    stone = [sphere('stone', 0.018, pouch_c + V((0.012, 0, 0)), M['stone'], scale=(1, 1, 0.9), seg=16, rings=8)]
    parts = {'Katapult_Frame': frame, 'Katapult_Bands': bands, 'Katapult_Pouch': pouch, 'Katapult_Stone': stone}
    # cartoon-size the slingshot around the gripping hand
    K, pivot = 2.0, V((0, 0, -0.045))
    for objs in parts.values():
        for o in objs:
            o.location = pivot + (V(o.location) - pivot) * K
            o.scale = V(o.scale) * K
    pouch_c = pivot + (pouch_c - pivot) * K
    hands = (grip_hand((0, 0, -0.045), (0, 0, -1), (0, 1, 0), 0.02, (1, 0, 0), (-0.27, 0.13, -0.33), watch=True)
             + fist(pouch_c + V((-0.035, 0, -0.005)), (1, 0, 0), (0, 0, 1), (-0.42, -0.22, -0.2)))
    return parts, hands


def shotgun():
    S, Wd = M['steel'], M['wood']
    body = [cyl('barrel', 0.019, 0.66, (0.44, 0, 0.06), S, rot=(0, math.pi / 2, 0), seg=20),
            cyl('muzzle', 0.022, 0.03, (0.77, 0, 0.06), M['blued'], rot=(0, math.pi / 2, 0), seg=20),
            sphere('bead', 0.006, (0.775, 0, 0.083), M['brass'], seg=8, rings=4),
            box('rib', (0.6, 0.012, 0.006), (0.46, 0, 0.081), S),
            cyl('magtube', 0.016, 0.6, (0.4, 0, 0.022), S, rot=(0, math.pi / 2, 0), seg=16),
            cyl('magcap', 0.019, 0.025, (0.71, 0, 0.022), M['blued'], rot=(0, math.pi / 2, 0), seg=16),
            box('receiver', (0.25, 0.052, 0.095), (0.055, 0, 0.042), S, bevel=0.01, segs=2),
            box('ejection_port', (0.07, 0.054, 0.025), (0.08, 0, 0.06), M['blued'], bevel=0.003)]
    stock = extrude_profile('stock', [(-0.06, 0.075), (-0.4, 0.05), (-0.42, -0.085), (-0.36, -0.095), (-0.12, -0.025),
                                      (-0.07, -0.1), (-0.035, -0.1), (-0.06, -0.02), (-0.06, 0.02)], 0.048, Wd)
    stock.modifiers.new('bevel', 'BEVEL').width = 0.01
    body.append(stock)
    body.append(box('buttpad', (0.02, 0.05, 0.145), (-0.415, 0, -0.018), M['rubber'], rot=(0, -0.12, 0), bevel=0.006))
    body.append(torus('guard', 0.032, 0.005, (-0.005, 0, -0.01), S, rot=(math.pi / 2, 0, 0), segU=20, segV=6, arc=(math.pi, 2 * math.pi)))
    body.append(box('trigger', (0.008, 0.008, 0.03), (0.0, 0, -0.012), M['steel_light'], rot=(0, 0.3, 0)))
    for i in range(4):  # side-saddle with red shells
        body.append(cyl('saddle_shell', 0.011, 0.06, (0.03 + i * 0.026, -0.033, 0.04), M['shell_red'], seg=12))
        body.append(cyl('saddle_brass', 0.0115, 0.015, (0.03 + i * 0.026, -0.033, 0.005), M['brass'], seg=12))
    pump = [cyl('pump', 0.03, 0.2, (0.42, 0, 0.022), M['wood_dark'], rot=(0, math.pi / 2, 0), seg=20)]
    for i in range(7):
        pump.append(torus('groove', 0.03, 0.004, (0.35 + i * 0.024, 0, 0.022), M['wood_dark'], rot=(0, math.pi / 2, 0), segU=20, segV=4))
    shell = [cyl('shell', 0.011, 0.06, (0, 0, 0.03), M['shell_red'], seg=12), cyl('shell_brass', 0.0118, 0.016, (0, 0, -0.005), M['brass'], seg=12)]
    for o in shell:  # spare shell for ejection, parked out of sight under the receiver
        o.location = V(o.location) + V((0.06, 0, 0.02))
    parts = {'Shotgun_Body': body, 'Shotgun_Pump': pump, 'Shotgun_Shell': shell}
    hands = (grip_hand((-0.055, 0, -0.045), (-0.4, 0, -1), (0, -1, 0), 0.022, (1, 0, 0), (-0.32, -0.2, -0.3))
             + grip_hand((0.43, 0, 0.022), (1, 0, 0), (0, 0, -1), 0.03, (0, -1, 0), (0.16, 0.06, -0.32), watch=True))
    return parts, hands


def sniper():
    S, P = M['blued'], M['polymer']
    body = [cyl('barrel', 0.022, 0.8, (0.6, 0, 0.03), S, r2=0.015, rot=(0, math.pi / 2, 0), seg=20),
            box('brake', (0.07, 0.04, 0.034), (1.02, 0, 0.03), M['steel'], bevel=0.006)]
    for i in range(3):
        body.append(box('brake_port', (0.012, 0.042, 0.02), (1.0 + i * 0.018, 0, 0.032), M['black']))
    body.append(cyl('receiver', 0.03, 0.27, (0.07, 0, 0.035), M['steel'], rot=(0, math.pi / 2, 0), seg=20))
    # scope
    sc = [cyl('scope_tube', 0.022, 0.3, (0.08, 0, 0.11), M['black'], rot=(0, math.pi / 2, 0), seg=24),
          cyl('scope_obj', 0.024, 0.11, (0.27, 0, 0.11), M['black'], r2=0.036, rot=(0, math.pi / 2, 0), seg=24),
          cyl('scope_eye', 0.03, 0.08, (-0.11, 0, 0.11), M['black'], r2=0.023, rot=(0, math.pi / 2, 0), seg=24),
          cyl('lens_front', 0.032, 0.004, (0.326, 0, 0.11), M['lens'], rot=(0, math.pi / 2, 0), seg=24),
          cyl('lens_back', 0.026, 0.004, (-0.152, 0, 0.11), M['lens'], rot=(0, math.pi / 2, 0), seg=24),
          cyl('turret_top', 0.014, 0.03, (0.08, 0, 0.14), M['black'], seg=16),
          cyl('turret_side', 0.014, 0.03, (0.08, -0.028, 0.11), M['black'], rot=(math.pi / 2, 0, 0), seg=16)]
    for x in (0.0, 0.16):
        sc.append(box('ring_mount', (0.025, 0.05, 0.05), (x, 0, 0.075), M['steel'], bevel=0.005))
        sc.append(torus('ring', 0.024, 0.005, (x, 0, 0.11), M['steel'], rot=(0, math.pi / 2, 0), segU=20, segV=6))
    body += sc
    stock = extrude_profile('stock', [(0.0, 0.05), (-0.46, 0.06), (-0.49, -0.11), (-0.43, -0.12), (-0.15, -0.045),
                                      (-0.1, -0.12), (-0.06, -0.12), (-0.04, -0.03), (0.48, -0.025), (0.48, 0.01), (0.0, 0.01)], 0.055, P)
    stock.modifiers.new('bevel', 'BEVEL').width = 0.012
    body.append(stock)
    body.append(box('cheek', (0.2, 0.05, 0.03), (-0.3, 0, 0.075), P, bevel=0.01))
    body.append(box('buttpad', (0.022, 0.056, 0.18), (-0.485, 0, -0.03), M['rubber'], bevel=0.006))
    body.append(box('mag', (0.07, 0.04, 0.06), (0.1, 0, -0.045), M['steel'], bevel=0.005))
    body.append(torus('guard', 0.03, 0.005, (0.0, 0, -0.03), M['steel'], rot=(math.pi / 2, 0, 0), segU=20, segV=6, arc=(math.pi, 2 * math.pi)))
    body.append(box('trigger', (0.008, 0.008, 0.03), (0.005, 0, -0.03), M['steel_light'], rot=(0, 0.3, 0)))
    for s in (-1, 1):  # folded bipod
        body.append(tube('bipod', (0.44, s * 0.018, -0.03), (0.2, s * 0.02, -0.04), 0.007, M['steel'], seg=8))
    body.append(box('bipod_mount', (0.03, 0.05, 0.02), (0.45, 0, -0.035), M['steel']))
    bolt = [tube('bolt_arm', (0.03, -0.028, 0.04), (0.03, -0.07, 0.02), 0.007, M['steel_light'], seg=8),
            sphere('bolt_knob', 0.014, (0.03, -0.075, 0.017), M['steel_light'], seg=12, rings=6)]
    parts = {'Sniper_Body': body, 'Sniper_Bolt': bolt}
    hands = (grip_hand((-0.075, 0, -0.07), (-0.35, 0, -1), (0, -1, 0), 0.022, (1, 0, 0), (-0.33, -0.22, -0.3))
             + grip_hand((0.33, 0, -0.012), (1, 0, 0), (0, 0, -1), 0.03, (0, -1, 0), (0.12, 0.07, -0.33), watch=True))
    return parts, hands


def bazooka():
    O, Od = M['olive'], M['olive_dark']
    body = [cyl('tube', 0.065, 1.15, (0.05, 0, 0), O, rot=(0, math.pi / 2, 0), seg=32, caps=False),
            cyl('tube_inner', 0.058, 1.15, (0.05, 0, 0), M['black'], rot=(0, math.pi / 2, 0), seg=24, caps=False),
            cyl('muzzle', 0.065, 0.1, (0.67, 0, 0), Od, r2=0.085, rot=(0, math.pi / 2, 0), seg=32, caps=False),
            cyl('venturi', 0.085, 0.14, (-0.58, 0, 0), Od, r2=0.065, rot=(0, math.pi / 2, 0), seg=32, caps=False)]
    for x in (-0.4, -0.15, 0.25, 0.5):
        body.append(torus('band', 0.066, 0.008, (x, 0, 0), Od, rot=(0, math.pi / 2, 0), segU=32, segV=6))
    for i in range(6):  # hazard stripes near the muzzle
        body.append(torus('stripe', 0.0655, 0.006, (0.53 + i * 0.016, 0, 0), M['yellow' if i % 2 == 0 else 'black'],
                          rot=(0, math.pi / 2, 0), segU=32, segV=4, rz=0.008))
    body.append(text_mesh('stencil', 'BOEM!', 0.06, (0.1, -0.066, 0.0), mat=M['yellow'], extrude=0.002))
    # pistol grip + trigger, front grip, shoulder pad, sights
    body.append(box('grip_mount', (0.08, 0.04, 0.04), (0.02, 0, -0.07), Od, bevel=0.008))
    body.append(capsule('pistol_grip', (0.02, 0, -0.08), (-0.01, 0, -0.18), 0.022, 0.024, M['rubber'], sxy=(1.2, 0.9)))
    body.append(torus('guard', 0.03, 0.005, (0.065, 0, -0.085), Od, rot=(math.pi / 2, 0, 0), segU=16, segV=6, arc=(math.pi, 2 * math.pi)))
    body.append(box('trigger', (0.008, 0.01, 0.03), (0.065, 0, -0.095), M['red_trigger'] if 'red_trigger' in M else M['rocket']))
    body.append(box('fgrip_mount', (0.06, 0.04, 0.04), (0.33, 0, -0.07), Od, bevel=0.008))
    body.append(capsule('front_grip', (0.33, 0, -0.08), (0.33, 0, -0.17), 0.022, 0.022, M['rubber']))
    body.append(box('shoulder_pad', (0.22, 0.08, 0.03), (-0.25, 0, -0.07), M['rubber'], bevel=0.012))
    body.append(box('sight_base', (0.05, 0.02, 0.03), (0.45, 0.06, 0.05), Od, bevel=0.004))
    body.append(torus('sight_frame', 0.035, 0.005, (0.45, 0.075, 0.1), M['black'], rot=(0, math.pi / 2, 0), segU=20, segV=6))
    body.append(tube('sight_post', (0.45, 0.075, 0.065), (0.45, 0.075, 0.095), 0.003, M['black'], seg=6))
    body.append(box('rear_sight', (0.02, 0.025, 0.04), (-0.05, 0.06, 0.06), M['black'], bevel=0.003))
    rocket = [cyl('rocket_body', 0.055, 0.12, (0.7, 0, 0), M['olive_dark'], rot=(0, math.pi / 2, 0), seg=24),
              cyl('warhead', 0.06, 0.12, (0.82, 0, 0), M['rocket'], r2=0.03, rot=(0, math.pi / 2, 0), seg=24),
              sphere('nose', 0.031, (0.88, 0, 0), M['rocket'], scale=(1.2, 1, 1), seg=20, rings=10),
              cyl('fuze', 0.012, 0.03, (0.915, 0, 0), M['white'], rot=(0, math.pi / 2, 0), seg=12),
              torus('rocket_band', 0.058, 0.006, (0.78, 0, 0), M['white'], rot=(0, math.pi / 2, 0), segU=24, segV=4)]
    for i in range(4):  # tail fins (inside the tube while loaded)
        a = i * math.pi / 2
        rocket.append(box('fin', (0.08, 0.004, 0.05), (0.62, math.cos(a) * 0.03, math.sin(a) * 0.03), M['olive_dark'], rot=(a, 0, 0)))
    parts = {'Bazooka_Body': body, 'Bazooka_Rocket': rocket}
    hands = (grip_hand((0.005, 0, -0.13), (-0.25, 0, -1), (0, -1, 0), 0.024, (1, 0, 0), (-0.16, -0.24, -0.42))
             + grip_hand((0.33, 0, -0.125), (0, 0, -1), (0, 1, 0), 0.022, (1, 0, 0), (0.12, 0.22, -0.44), watch=True))
    return parts, hands


# Viewmodel placement in camera space (camera looks +X): (location, rotation)
VIEWMODELS = {
    'katapult': (katapult, (0.78, 0.03, -0.33), (0, 0.08, 0.0)),
    'shotgun': (shotgun, (0.46, -0.2, -0.25), (0, -0.02, 0.035)),
    'sniper': (sniper, (0.44, -0.18, -0.23), (0, -0.015, 0.03)),
    'bazooka': (bazooka, (0.02, -0.27, -0.11), (0, -0.01, 0.11)),
}


def build_viewmodel(key):
    fn, loc, rot = VIEWMODELS[key]
    parts, hands = fn()
    root = lib.empty(f'VM_{key.capitalize()}')
    for name, objs in parts.items():
        o = join(objs, name)
        lib.set_parent(o, root)
    arms = join(hands, f'{key.capitalize()}_Arms')
    subsurf(arms, 1)
    lib.set_parent(arms, root)
    root.location = loc
    root.rotation_euler = rot
    return root


# ================================================================ ice cream

def ijsje():
    S = 1.05  # cartoon scale
    p = []
    glass = lathe('coupe', [(0.0, 0.0), (0.04, 0.0), (0.042, 0.004), (0.012, 0.012), (0.007, 0.045), (0.009, 0.06),
                            (0.03, 0.066), (0.05, 0.08), (0.062, 0.1), (0.066, 0.112), (0.064, 0.114)], M['glass'], seg=40)
    p_glass = [glass]
    scoops = []
    for (x, y, z, m) in ((0.022, 0.016, 0.115, 'strawberry'), (-0.024, 0.014, 0.115, 'vanilla'), (0.0, -0.026, 0.115, 'chocolate'),
                         (0.0, 0.0, 0.15, 'vanilla')):
        scoops.append(sphere('scoop', 0.036, (x, y, z), M[m], scale=(1, 1, 0.92), seg=24, rings=12))
        scoops.append(torus('scoop_rim', 0.033, 0.008, (x, y, z - 0.012), M[m], segU=20, segV=6))
    top = [torus('sauce', 0.03, 0.007, (0, 0, 0.168), M['sauce'], segU=24, segV=6)]
    for i in range(6):
        a = i * math.pi / 3
        top.append(capsule('drip', (math.cos(a) * 0.031, math.sin(a) * 0.031, 0.165), (math.cos(a) * 0.036, math.sin(a) * 0.036, 0.145 - (i % 2) * 0.01),
                           0.005, 0.0045, M['sauce']))
    for i in range(4):  # whipped cream swirl
        r = 0.026 - i * 0.006
        top.append(torus('cream', r, 0.011 - i * 0.0015, (0, 0, 0.18 + i * 0.012), M['cream'], segU=20, segV=8))
    top.append(sphere('cherry', 0.013, (0.0, 0.0, 0.232), M['cherry'], seg=16, rings=8))
    top.append(tube('cherry_stem', (0, 0, 0.243), (0.012, 0.004, 0.27), 0.0018, M['stem'], seg=6))
    wafer = extrude_profile('wafer_fan', [(-0.025, 0), (0.025, 0), (0.0, 0.07)], 0.006, M['wafer'])
    wafer.location = (0.03, -0.02, 0.15)
    wafer.rotation_euler = (0.2, -0.3, 0.5)
    top.append(wafer)
    top.append(tube('wafer_roll', (-0.03, -0.005, 0.14), (-0.06, -0.02, 0.22), 0.006, M['wafer'], seg=12))
    umb = [tube('umb_stick', (0.03, 0.025, 0.13), (0.055, 0.04, 0.26), 0.0015, M['wafer'], seg=6)]
    for i in range(8):
        umb.append(_umb_panel(i, V((0.055, 0.04, 0.26))))
    spoon = [tube('spoon_handle', (-0.05, 0.03, 0.13), (-0.075, 0.045, 0.25), 0.003, M['spoon'], seg=8),
             sphere('spoon_bowl', 0.01, (-0.045, 0.027, 0.12), M['spoon'], scale=(1, 0.7, 1.5), seg=12, rings=6)]
    parts = {'IJsje_Glass': p_glass, 'IJsje_Scoops': scoops, 'IJsje_Topping': top + umb, 'IJsje_Spoon': spoon}
    root = lib.empty('IJsje')
    for name, objs in parts.items():
        for o in objs:
            o.location = V(o.location) * S
            o.scale = V(o.scale) * S
        lib.set_parent(join(objs, name), root)
    return root


def _umb_panel(i, apex):
    a0, a1 = i * math.pi / 4, (i + 1) * math.pi / 4
    r, drop = 0.045, 0.014
    pts = [apex, apex + V((math.cos(a0) * r, math.sin(a0) * r, -drop)), apex + V((math.cos(a1) * r, math.sin(a1) * r, -drop))]
    import bmesh
    bm = bmesh.new()
    vs = [bm.verts.new(p) for p in pts]
    bm.faces.new(vs)
    return lib.obj_from_bm(bm, 'umb_panel', M['umbrella_a' if i % 2 else 'umbrella_b'], smooth=False)


# ================================================================ main

def main():
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    lib.reset_scene()
    make_materials()
    out_dir = os.path.join(ROOT, 'assets', 'models', 'weapons')
    os.makedirs(out_dir, exist_ok=True)
    roots = {k: build_viewmodel(k) for k in VIEWMODELS}
    ice = ijsje()
    for k, r in roots.items():
        objs = [r] + list(r.children_recursive)
        print(f'[weapons] {k}: {lib.tri_count([o for o in objs if o.type == "MESH"])} tris, parts {[o.name for o in r.children]}')
        lib.export_glb(os.path.join(out_dir, f'{k}.glb'), objs)
    lib.export_glb(os.path.join(ROOT, 'assets', 'models', 'ijsje.glb'), [ice] + list(ice.children_recursive))
    if '--no-render' in argv:
        return

    scene = bpy.context.scene
    lib.preview_stage(scene, size=(1600, 900))
    rdir = os.path.join(ROOT, 'renders', 'weapons')
    os.makedirs(rdir, exist_ok=True)

    # --- product sheet: all weapons side by side on a dark backdrop (arms hidden)
    bpy.data.objects['PreviewGround'].hide_render = True
    backdrop = box('Backdrop', (6, 0.02, 4), (0.6, 0.6, 0.6), material('Backdrop', '#1d1e24', rough=0.9))
    saved = {k: (r.location.copy(), r.rotation_euler.copy()) for k, r in roots.items()}
    layout = {'sniper': ((-0.2, 0, 1.25), (0, 0, 0)), 'bazooka': ((-0.15, 0, 0.85), (0, 0, 0)),
              'shotgun': ((-0.25, 0, 0.45), (0, 0, 0)), 'katapult': ((1.15, 0, 0.42), (0, 0, math.pi / 2))}
    for k, (loc, rot) in layout.items():
        roots[k].location, roots[k].rotation_euler = loc, rot
        bpy.data.objects[f'{k.capitalize()}_Arms'].hide_render = True
    ice.location = (1.15, 0, 0.75)
    ice.scale = (2.2, 2.2, 2.2)
    cam = lib.camera('Cam_sheet', (0.45, -3.2, 0.95), (0.45, 0, 0.9), 50)
    cam.data.type = 'ORTHO'
    cam.data.ortho_scale = 2.1
    lib.render(scene, cam, os.path.join(rdir, '00_sheet.png'))
    backdrop.hide_render = True
    for k, r in roots.items():
        r.location, r.rotation_euler = saved[k]
        bpy.data.objects[f'{k.capitalize()}_Arms'].hide_render = False
    ice.scale = (1, 1, 1)

    # --- first-person views inside the real square
    bpy.ops.import_scene.gltf(filepath=os.path.join(ROOT, 'assets', 'models', 'square.glb'))
    eye_obj = bpy.data.objects.get('PlayerEye')
    eye = eye_obj.matrix_world.translation.copy() if eye_obj else V((0, -11.55, 1.2))
    chair = bpy.data.objects.get('Player_Chair')
    if chair:
        chair.hide_render = True
    table = bpy.data.objects.get('Player_Table')
    tpos = table.matrix_world.translation if table else V((0.2, -11.0, 0))
    ice.location = (tpos.x, tpos.y, 0.755)
    rig = lib.empty('CameraRig', eye)
    rig.rotation_euler = (0, 0, math.pi / 2)  # camera-space +X -> world +Y (north)
    camd = bpy.data.cameras.new('FPCam')
    camd.sensor_fit = 'VERTICAL'
    camd.angle_y = math.radians(62)
    camd.clip_start = 0.02
    fpcam = lib.link(bpy.data.objects.new('FPCam', camd))
    fpcam.parent = rig
    fpcam.rotation_euler = (math.pi / 2, 0, -math.pi / 2)  # look along rig +X with +Z up
    for r in roots.values():
        r.parent = rig
    sun = bpy.data.objects['Sun']
    sun.rotation_euler = (math.radians(58), 0, math.radians(-40))
    sun.data.energy = 6.5
    bpy.data.objects['Fill'].hide_render = True
    for i, k in enumerate(VIEWMODELS):
        for k2, r in roots.items():
            for o in [r] + list(r.children_recursive):
                o.hide_render = (k2 != k)
        lib.render(scene, fpcam, os.path.join(rdir, f'{i + 1:02d}_fp_{k}.png'))
    rig.rotation_euler = (0, 0.55, math.pi / 2 + 0.5)  # glance down-left at the ice cream
    for r in roots.values():
        for o in [r] + list(r.children_recursive):
            o.hide_render = True
    lib.render(scene, fpcam, os.path.join(rdir, '05_fp_ijsje.png'))


if __name__ == '__main__':
    main()
