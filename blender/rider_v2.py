"""Glow-up rider parts (Fortnite-ish): smooth swept limbs with folds, gripping hands with fingers, ribbed cuffs,
chunky sneakers, a sculpted (voxel-remeshed) head, a lumpy broccoli and prints on the tracksuit.

Same part names, pivots and pose as build_riders.py, so the game keeps working. Variants opt in with v2=True.
"""
import math
import random

import bpy
from mathutils import Matrix, Vector

import crowdkit as ck
import lib
from build_fatbiker import AXIS, CHEST, FWD, HC, HEAD_R, HEAD_SCALE, HIP, HS, TORSO_ANG, hv
from lib import capsule, ico, join, sphere, torus, tube

V = Vector


def ellipse(w, h):
    """Radius of an ellipse at angle a: h along the frame normal (a=0), w across it."""
    return lambda a: 1.0 / math.sqrt((math.cos(a) / h) ** 2 + (math.sin(a) / w) ** 2)


def lerp_list(vals, t):
    x = t * (len(vals) - 1)
    i = min(int(x), len(vals) - 2)
    u = x - i
    u = u * u * (3 - 2 * u)
    return vals[i] * (1 - u) + vals[i + 1] * u


def angle_of(fr, i, direction):
    """Angle around the sweep at sample i that points toward `direction`."""
    c, tg, n, b, t = fr[i]
    d = V(direction)
    return math.atan2(d.dot(b), d.dot(n))


def flat_strip(name, fr, radius, ang, t0, t1, mat, width=0.009, height=0.0035, n=24):
    """A flat raised band on a sweep's surface (tracksuit stripes, seams)."""
    k = len(fr) - 1
    pts, outs = [], []
    for j in range(n):
        idx = round((t0 + (t1 - t0) * j / (n - 1)) * k)
        pts.append(ck.surface(fr, radius, idx, ang))
        c, tg, nn, b, t = fr[idx]
        outs.append(nn * math.cos(ang) + b * math.sin(ang))
    return ck.sweep(name, pts, lambda t, a: ellipse(width, height)(a), mat, seg=8, samples=n, caps=(True, True),
                    up=outs[0], cap_rings=2)


# ------------------------------------------------------------------------------------------- hands

def build_hand(M, s, gc, female=False):
    """A fist around the handlebar grip. gc: point on the grip axis under the middle of the hand."""
    SK = M['skin']
    k = 0.9 if female else 1.0
    ga = V((-0.015, s * 0.11, 0.005)).normalized()           # grip axis, pointing outward
    ef = (V((1, 0, 0)) - ga * ga.x).normalized()               # forward around the grip
    eu = ga.cross(ef) * s                                       # up around the grip
    if eu.z < 0:
        eu = -eu

    def around(u, th, R):
        th = math.radians(th)
        return gc + ga * u + (ef * math.cos(th) + eu * math.sin(th)) * R

    p = []
    rg = 0.022
    wrist = gc + ef * -0.075 + eu * 0.03
    knuck = gc + ef * -0.012 + eu * 0.04
    # back of the hand: a flattened slab from wrist to knuckles
    p.append(ck.sweep('palm', [wrist, wrist.lerp(knuck, 0.55), knuck],
                      lambda t, a: ellipse(lerp_list([0.036, 0.046, 0.05], t) * k, lerp_list([0.026, 0.026, 0.02], t) * k)(a),
                      SK, seg=16, samples=10, up=eu))
    # fingers: index (inside) -> pinky (outside), curled over the top and around the front
    for i in range(4):
        u = (-0.031 + i * 0.0205) * k
        rf = (0.0125 - (0.0022 if i == 3 else 0.0)) * k
        R = rg + rf * 0.95
        angs = [140, 112, 78, 40, 4, -30] if i < 3 else [138, 110, 76, 40, 6]
        pts = [around(u, a, R + (0.012 if j == 0 else 0.0)) for j, a in enumerate(angs)]
        rad = lambda t, a, rf=rf: rf * (1.0 + ck.bumps(t, [0.18, 0.5], 0.08, 0.12) - 0.12 * t)
        p.append(ck.sweep('finger', pts, rad, SK, seg=10, samples=14, up=eu))
    # thumb: from the palm's inside edge, under the grip
    t0 = gc + ga * (-0.05 * k) + ef * -0.045 + eu * 0.012
    p.append(ck.sweep('thumb', [t0, around(-0.05 * k, 190, 0.036), around(-0.045 * k, 235, 0.034), around(-0.036 * k, 275, 0.032)],
                      lambda t, a: 0.0145 * k * (1 - 0.18 * t), SK, seg=10, samples=12, up=-ef))
    return p, wrist


# ------------------------------------------------------------------------------------------- arms

def build_arm(M, v, s):
    side = 'L' if s > 0 else 'R'
    female = v['sex'] == 'f'
    k = 0.87 if female else (1.12 if v.get('build') == 'big' else 1.0)
    T, TR = M['top'], M['trim']
    sh = V((-0.005, s * (0.2 if female else 0.215), 1.30))
    el = V((0.14, s * 0.37, 1.15))
    gc = V((0.327, s * 0.378, 1.101))
    hand, wrist = build_hand(M, s, gc, female)
    fd = (wrist - el).normalized()
    cuff = wrist - fd * 0.045
    sh_in = sh - V((0.0, s * 0.04, -0.02))
    pts = [sh_in, sh, el, cuff]
    fr = ck.frames(pts, 64, up=V((0, 0, 1)))
    a_in = angle_of(fr, round(0.62 * 63), (sh + cuff) / 2 - el)     # inside of the elbow
    a_out = angle_of(fr, round(0.5 * 63), V((0, s, 0.6)))

    def sleeve(t, a):
        base = lerp_list([0.072, 0.08, 0.07, 0.062, 0.058], t) * k
        inner = max(0.0, math.cos(a - a_in))
        folds = ck.bumps(t, [0.56, 0.62, 0.68], 0.022, 0.09) * (0.25 + 0.75 * inner)
        bunch = ck.bumps(t, [0.83, 0.89, 0.94], 0.02, 0.07) * (0.75 + 0.25 * math.sin(3 * a + t * 17))
        return base * (1 + folds + bunch + 0.012 * math.sin(2 * a + 9 * t))

    p = [ck.sweep('sleeve', pts, sleeve, T, seg=24, samples=64, caps=(True, False), up=V((0, 0, 1)))]
    if v['top'] == 'tracksuit':
        for d in (-0.2, 0.2):
            p.append(flat_strip('stripe', fr, sleeve, a_out + d, 0.12, 0.8, TR))
    # ribbed cuff + bare wrist into the hand
    rib = M['top_rib']
    p.append(ck.sweep('cuff', [cuff - fd * 0.005, cuff + fd * 0.035],
                      lambda t, a: 0.056 * k * (1 + 0.045 * math.cos(14 * a)), rib, seg=56, samples=4, caps=(False, False)))
    p.append(ck.sweep('wrist', [cuff, wrist + fd * 0.01], [0.042 * k, 0.04 * k], M['skin'], seg=16, samples=6, caps=(False, True)))
    p += hand
    return join(p, f'Rider_Arm{side}', pivot=sh)


# ------------------------------------------------------------------------------------------- legs & shoes

def build_sneaker(M, origin, s):
    """Chunky sneaker from two sweeps (upper + sole); origin = middle of the sole's underside, +X forward."""
    up = V((0, 0, 1))

    def upper(t, a):
        w = lerp_list([0.044, 0.05, 0.052, 0.046, 0.036], t)
        h = lerp_list([0.06, 0.062, 0.045, 0.032, 0.024], t)
        if math.cos(a) < 0:
            h = min(h, 0.03)
        return ellipse(w, h)(a)

    p = [ck.sweep('upper', [V((-0.115, 0, 0.075)), V((-0.03, 0, 0.08)), V((0.07, 0, 0.065)), V((0.125, 0, 0.052))],
                  upper, M['shoe'], seg=24, samples=24, up=up)]
    p.append(ck.sweep('sole', [V((-0.13, 0, 0.024)), V((0.0, 0, 0.022)), V((0.135, 0, 0.03))],
                      lambda t, a: ellipse(lerp_list([0.054, 0.058, 0.05], t), 0.024)(a), M['sole'], seg=24, samples=16, up=up))
    p.append(ck.sweep('midline', [V((-0.135, 0, 0.04)), V((0.0, 0, 0.038)), V((0.14, 0, 0.045))],
                      lambda t, a: ellipse(lerp_list([0.056, 0.06, 0.051], t), 0.006)(a), M['btrim'], seg=24, samples=16, up=up))
    p.append(torus('collar', 0.04, 0.013, (-0.08, 0, 0.128), M['sole'], rot=(0, math.radians(-10), 0), segU=24, segV=8))
    p[-1].scale = (1.3, 1.1, 1)
    p.append(lib.box('tongue', (0.05, 0.06, 0.03), (-0.03, 0, 0.13), M['shoe'], rot=(0, math.radians(-35), 0), bevel=0.012))
    for i in range(4):
        x = 0.06 - i * 0.028
        z = 0.108 + i * 0.008
        p.append(lib.box('lace', (0.01, 0.062, 0.008), (x, 0, z), M['sock'], rot=(0, math.radians(-20), 0), bevel=0.003))
    # lightning bolt on both sides (the "BLIKSEM" brand)
    bolt = [(-0.07, 0.1), (0.0, 0.07), (-0.02, 0.065), (0.06, 0.045), (-0.005, 0.08), (0.015, 0.085)]
    for sy in (-1, 1):
        b = lib.extrude_profile('bolt', bolt, 0.006, M['btrim'])
        b.location = (0, sy * 0.05, 0)
        p.append(b)
    shoe = join(p, 'shoe_tmp')
    shoe.location = origin
    return shoe


def build_leg(M, v, s):
    side = 'L' if s > 0 else 'R'
    female = v['sex'] == 'f'
    k = 0.88 if female else (1.12 if v.get('build') == 'big' else 1.0)
    hip = V((-0.17, s * 0.11, 0.93))
    if s < 0:
        knee, ankle = V((0.17, s * 0.19, 0.80)), V((0.155, s * 0.15, 0.40))
    else:
        knee, ankle = V((0.02, s * 0.2, 0.72)), V((-0.165, s * 0.15, 0.39))
    B = M['bottom']
    hem = ankle + (knee - ankle).normalized() * 0.025
    pts = [hip, knee, hem]
    fr = ck.frames(pts, 64, up=V((1, 0, 0)))
    a_back = angle_of(fr, 32, (hip + hem) / 2 - knee)     # hollow of the knee
    a_out = angle_of(fr, 20, V((0, s, 0.3)))

    def trouser(t, a):
        base = lerp_list([0.1, 0.092, 0.08, 0.072, 0.07], t) * k
        back = max(0.0, math.cos(a - a_back))
        folds = ck.bumps(t, [0.46, 0.52, 0.58], 0.025, 0.08) * (0.2 + 0.8 * back)
        bunch = ck.bumps(t, [0.8, 0.86, 0.92], 0.022, 0.08) * (0.7 + 0.3 * math.sin(3 * a + t * 13))
        return base * (1 + folds + bunch + 0.015 * math.sin(2 * a + 7 * t))

    p = [ck.sweep('trousers', pts, trouser, B, seg=24, samples=64, caps=(True, False), up=V((1, 0, 0)))]
    if v['bottom'] == 'trackpants':
        for d in (-0.2, 0.2):
            p.append(flat_strip('stripe', fr, trouser, a_out + d, 0.04, 0.78, M['btrim']))
    p.append(ck.sweep('cuff', [hem + (knee - ankle).normalized() * 0.005, ankle - (knee - ankle).normalized() * 0.02],
                      lambda t, a: 0.064 * k * (1 + 0.045 * math.cos(14 * a)), M['bottom_rib'], seg=56, samples=4, caps=(False, False)))
    shoe_c = ankle + V((0.04, 0, -0.045))
    p.append(build_sneaker(M, shoe_c - V((0, 0, 0.06)), s))
    return join(p, f'Rider_Leg{side}', pivot=hip)


# ------------------------------------------------------------------------------------------- torso

def _decal(name, body, size, target, centre, outward, up, mat, extrude=0.0025):
    o = lib.text_mesh(name, body, size, rot=(0, 0, 0), mat=mat, extrude=extrude)
    lib.bake(o)
    x = up.cross(outward)
    R = lib.basis(x, outward)
    lib.orient_basis(o, R, centre + outward * 0.01)
    bpy.context.view_layer.update()
    o.data.transform(o.matrix_world)
    o.matrix_world = Matrix.Identity(4)
    return ck.conform(o, target, 0.0015)


def build_torso(M, v):
    T, TR = M['top'], M['trim']
    big = v.get('build') == 'big'
    sx, sy = (0.88, 1.25) if big else (0.85, 1.2)
    pts = [HIP - AXIS * 0.05, HIP + AXIS * 0.07, CHEST - AXIS * 0.02, CHEST + AXIS * 0.07]
    fr = ck.frames(pts, 56, up=FWD)

    def body(t, a):
        R = lerp_list([0.165, 0.165, 0.178, 0.19, 0.185], t) * (1.12 if big else 1.0)
        r = R * ellipse(sy, sx)(a)
        front = max(0.0, math.cos(a))
        folds = ck.bumps(t, [0.2, 0.3, 0.4], 0.035, 0.035) * front ** 2
        chest = ck.bumps(t, [0.72], 0.12, 0.05) * front
        return r * (1 + folds + chest + 0.01 * math.sin(3 * a + 8 * t))

    torso = ck.sweep('torso', pts, body, T, seg=40, samples=56, caps=(False, True), up=FWD)
    p = [torso]
    p.append(sphere('pelvis', 0.15, (-0.19, 0, 0.93), M['bottom'], scale=(1.0, 1.15, 0.72)))
    # ribbed waistband
    p.append(ck.sweep('waistband', [HIP - AXIS * 0.075, HIP - AXIS * 0.02],
                      lambda t, a: body(0.02, a) * 1.03 * (1 + 0.02 * math.cos(44 * a)), M['top_rib'],
                      seg=88, samples=4, caps=(False, False), up=FWD))
    neck_base = CHEST + AXIS * 0.15
    if v['top'] == 'tracksuit':
        # stand-up collar, zip with puller, zipped pockets, prints
        p.append(ck.sweep('collar', [neck_base - AXIS * 0.03, neck_base + AXIS * 0.045 + FWD * 0.012],
                          lambda t, a: ellipse(0.088, 0.082)(a) * (1 + 0.04 * t), M['top_rib'], seg=40, samples=6,
                          caps=(False, False), up=FWD))
        n = len(fr) - 1
        zp = [ck.surface(fr, body, i, 0.0) + FWD * 0.002 for i in range(2, n - 6, 4)]
        p.append(ck.sweep('zip', zp, lambda t, a: ellipse(0.007, 0.0035)(a), M['chrome'], seg=8, samples=40, up=FWD))
        top = zp[-1]
        p.append(lib.box('zip_pull', (0.008, 0.016, 0.034), top - AXIS * 0.03 + FWD * 0.006, M['chrome'],
                         rot=(0, TORSO_ANG, 0), bevel=0.003))
        for sgn in (-1, 1):
            a = sgn * 1.05
            p.append(flat_strip('pocket', fr, body, a, 0.14, 0.34, M['chrome'], width=0.0045, height=0.0035, n=8))
        # shoulder stripes continue the sleeves' stripes over the top
        for sgn in (-1, 1):
            for d in (-0.012, 0.012):
                a = neck_base + V((d * 3, sgn * 0.09, -0.02))
                b = V((-0.005 + d * 3, sgn * 0.21, 1.33))
                p.append(tube('shoulder_stripe', a, b, 0.0055, TR, seg=6))
        up = AXIS
        chest_pt = ck.surface(fr, body, round(0.66 * n), -0.5)
        out = (chest_pt - fr[round(0.66 * n)][0]).normalized()
        p.append(_decal('logo', 'ABIBAS', 0.032, torso, chest_pt, out, up, TR))
        back_c = ck.surface(fr, body, round(0.62 * n), math.pi)
        bout = (back_c - fr[round(0.62 * n)][0]).normalized()
        p.append(_decal('back_print', 'KONING', 0.075, torso, back_c + up * 0.04, bout, up, TR, extrude=0.003))
        p.append(_decal('back_print2', 'VAN HET PLEIN', 0.034, torso, back_c - up * 0.035, bout, up, TR, extrude=0.003))
    if v.get('chain'):
        links = []
        for i in range(46):
            a = 2 * math.pi * i / 46
            links.append(torus('link', 0.009, 0.0028, (math.cos(a) * 0.105, math.sin(a) * 0.112, 0), M['gold'], segU=10, segV=5,
                               rot=(math.pi / 2 if i % 2 else 0, 0, a + math.pi / 2)))
        chain = join(links, 'chain_tmp')
        chain.location = neck_base + FWD * 0.02 - AXIS * 0.02
        chain.rotation_euler = (0, TORSO_ANG + 0.55, 0)
        p.append(chain)
        bpy.context.view_layer.update()
        hang = chain.matrix_world @ V((0.105, 0, 0))
        euro = lib.text_mesh('pendant', '€', 0.075, rot=(0, 0, 0), mat=M['gold'], extrude=0.006)
        lib.orient_basis(euro, lib.basis(AXIS.cross(FWD), FWD), hang + FWD * 0.012 - AXIS * 0.035)
        p.append(euro)
    return join(p, 'Rider_Torso', pivot=HIP)


# ------------------------------------------------------------------------------------------- head

def build_head(M, v):
    female, age = v['sex'] == 'f', v['age']
    sk, sd = M['skin'], M['skin_dark']
    skin = [sphere('head', HEAD_R, HC, sk, scale=HEAD_SCALE * (0.97 if female else 1), seg=48, rings=24)]
    jaw = (1.0, 1.12, 0.8)
    skin.append(sphere('jaw', 0.14 * HS, hv(0.03, 0, -0.085), sk, scale=jaw))
    skin.append(sphere('chin', 0.05 * HS, hv(0.13, 0, -0.15), sk, scale=(0.8, 1.3, 0.9)))
    for s in (-1, 1):
        skin.append(sphere('cheek', 0.052 * HS, hv(0.105, s * 0.085, -0.04), sk))
        skin.append(sphere('cheekbone', 0.04 * HS, hv(0.11, s * 0.1, 0.0), sk, scale=(0.8, 1.2, 0.7)))
    skin.append(sphere('brow_ridge', 0.05 * HS, hv(0.135, 0, 0.075), sk, scale=(0.75, 2.6, 0.6)))
    skin.append(sphere('nose', 0.05 * HS, hv(0.19, 0, -0.015), sk, scale=(1.0, 0.95, 0.85)))
    for s in (-1, 1):
        skin.append(sphere('nostril_wing', 0.024 * HS, hv(0.175, s * 0.033, -0.03), sk))
    skin.append(sphere('nose_bridge', 0.026 * HS, hv(0.172, 0, 0.03), sk, scale=(1, 0.9, 1.6)))
    eyes = []
    for s in (-1, 1):
        e = hv(0.138, s * 0.066, 0.03)
        er = 0.045 * HS
        skin.append(sphere('eyelid', er * 1.08, e + V((0.0, 0, 0.022)) * HS, sk, scale=(0.78, 1.04, 0.62), rot=(s * math.radians(22), 0, 0)))
        skin.append(sphere('lowerlid', er * 1.0, e + V((0.004, 0, -0.024)) * HS, sk, scale=(0.72, 1.0, 0.4)))
        eyes.append((s, e, er))
    neck_r = 0.07
    skin.append(capsule('neck', (0.0, 0, 1.31), (0.045, 0, 1.45), neck_r, neck_r * 0.97, sk))
    face = join(skin, 'skin_tmp')
    ck.remesh(face, 0.005, smooth=6, ratio=0.4)
    p = [face]
    for s, e, er in eyes:
        p.append(sphere('eye', er, e, M['eye'], scale=(0.75, 1, 0.85)))
        p.append(sphere('iris', 0.024 * HS, e + V((0.029, -s * 0.004, -0.004)) * HS, M['iris'], scale=(0.45, 1, 1)))
        p.append(sphere('pupil', 0.011 * HS, e + V((0.038, -s * 0.004, -0.004)) * HS, M['pupil'], scale=(0.4, 1, 1)))
        p.append(sphere('glint', 0.004 * HS, e + V((0.041, 0, 0.006)) * HS, M['eye']))
        p.append(sphere('ear', 0.05 * HS, hv(-0.01, s * 0.168, -0.005), sk, scale=(0.55, 0.35, 1.0)))
        p.append(sphere('ear_in', 0.03 * HS, hv(-0.004, s * 0.178, -0.005), sd, scale=(0.5, 0.2, 0.8)))
        p.append(sphere('nostril', 0.011 * HS, hv(0.19, s * 0.022, -0.046), sd, scale=(1.0, 0.8, 0.5)))
        # chunky, angry brows: thick at the nose, tapering up and out
        bp = [hv(0.178, s * 0.016, 0.066), hv(0.17, s * 0.06, 0.088), hv(0.145, s * 0.112, 0.09)]
        p.append(ck.sweep('brow', bp, lambda t, a: ellipse(0.011 * HS * (1 - 0.45 * t), 0.017 * HS * (1 - 0.5 * t))(a),
                          M['brow'], seg=12, samples=12, up=V((0, 0, 1))))
    m = hv(0.158, 0, -0.092)
    p.append(sphere('mouth', 0.05 * HS, m, M['mouth'], scale=(0.4, 1.75, 0.62)))
    p.append(sphere('tongue', 0.032 * HS, m + V((0.0, 0.01, -0.016)) * HS, M['tongue'], scale=(0.6, 1.3, 0.45)))
    p.append(lib.box('teeth_top', (0.02 * HS, 0.13 * HS, 0.02 * HS), m + V((0.008, 0, 0.0115)) * HS, M['teeth'], bevel=0.006, segs=3))
    p.append(lib.box('teeth_bot', (0.02 * HS, 0.12 * HS, 0.018 * HS), m + V((0.007, 0, -0.0115)) * HS, M['teeth'], bevel=0.006, segs=3))
    p.append(sphere('lip_top', 0.05 * HS, m + V((0.014, 0, 0.03)) * HS, sd, scale=(0.3, 1.7, 0.17)))
    p.append(sphere('lip_bot', 0.05 * HS, m + V((0.012, 0, -0.03)) * HS, sd, scale=(0.3, 1.55, 0.19)))
    if v.get('facial') == 'goatee':
        gp = [hv(0.172, 0, -0.14), hv(0.166, 0, -0.168), hv(0.145, 0, -0.192)]
        p.append(ck.sweep('goatee', gp, lambda t, a: ellipse(0.03 * HS * (1 - 0.4 * t), 0.016 * HS)(a), M['hair'],
                          seg=14, samples=10, up=V((1, 0, 0))))
        for s in (-1, 1):  # thin moustache that joins the goatee
            mp = [hv(0.19, 0, -0.06), hv(0.18, s * 0.06, -0.075), hv(0.165, s * 0.075, -0.12)]
            p.append(ck.sweep('moustache', mp, lambda t, a: 0.007 * HS * (1 - 0.4 * t), M['hair'], seg=8, samples=10))
    o = join(p, 'Rider_Head', pivot=(0.02, 0, 1.38))
    return o


# ------------------------------------------------------------------------------------------- hair

def build_hair(M, v):
    random.seed(11)
    H = M['hair']
    p = []
    if v['hair'] == 'broccoli':
        from build_riders import shell
        p.append(shell('fade', M['fade'], lambda x, y, z: z > -0.12 and x < 0.02 + max(0.0, z - 0.2) * 2.0, k=1.012))
        blobs = [sphere('hair_base', HEAD_R * 0.98, hv(-0.005, 0, 0.085), H, scale=(1.02, 0.97, 0.8))]
        tries = 0
        while len(blobs) < 260 and tries < 20000:
            tries += 1
            d = V((random.uniform(-1, 1), random.uniform(-1, 1), random.uniform(-1, 1)))
            if not 0.2 < d.length <= 1:
                continue
            d.normalize()
            if d.z < (0.4 if d.x > 0.4 else 0.14):
                continue
            pos = hv(-0.005, 0, 0.085) + V((d.x, d.y * 0.95, d.z * 0.85)) * HEAD_R * 1.0 + d * random.uniform(0.0, 0.02)
            blobs.append(ico('curl', random.uniform(0.022, 0.042), pos, H, subdiv=2))
        broc = join(blobs, 'broc_tmp')
        ck.remesh(broc, 0.0055, smooth=2, ratio=0.25)
        p.append(broc)
        # a shaved line in the fade (left side)
        line = []
        for f in (55, 75, 95, 115, 132):
            ph, ps = math.radians(f), math.radians(-6 + (f - 55) * 0.08)
            d = V((math.cos(ph) * math.cos(ps), math.sin(ph) * math.cos(ps), math.sin(ps)))
            line.append(HC + V((d.x * HEAD_SCALE.x, d.y * HEAD_SCALE.y, d.z * HEAD_SCALE.z)) * HEAD_R * 1.016)
        p.append(ck.sweep('shaved_line', line, lambda t, a: ellipse(0.005, 0.0022)(a), M['skin'], seg=8, samples=16))
    if not p:
        return None
    return join(p, 'Rider_Hair', pivot=HC)
