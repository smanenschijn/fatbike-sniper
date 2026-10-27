"""Glow-up rider parts (Fortnite-ish): smooth swept limbs with folds, gripping hands with fingers, ribbed cuffs,
chunky sneakers / socks-in-sandals / granny shoes, sculpted (voxel-remeshed) heads, lumpy curls and Dutch prints.

Covers every option of the VARIANTS in build_riders.py (tops, bottoms, shoes, facial hair, glasses, braces, ...).
Same part names, pivots and pose as the classic builders, so the game keeps working. Variants opt in with v2=True.
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


def flat_strip(name, fr, radius, ang, t0, t1, mat, width=0.009, height=0.0035, n=16):
    """A flat raised band on a sweep's surface (tracksuit stripes, seams)."""
    k = len(fr) - 1
    pts, outs = [], []
    for j in range(n):
        idx = round((t0 + (t1 - t0) * j / (n - 1)) * k)
        pts.append(ck.surface(fr, radius, idx, ang))
        c, tg, nn, b, t = fr[idx]
        outs.append(nn * math.cos(ang) + b * math.sin(ang))
    return ck.sweep(name, pts, lambda t, a: ellipse(width, height)(a), mat, seg=6, samples=n, caps=(True, True),
                    up=outs[0], cap_rings=2)


# ------------------------------------------------------------------------------------------- hands

def hand_frame(s, gc):
    """Grip axis (outward), forward and up around the grip, wrist and knuckle points."""
    ga = V((-0.015, s * 0.11, 0.005)).normalized()
    ef = (V((1, 0, 0)) - ga * ga.x).normalized()
    eu = ga.cross(ef) * s
    if eu.z < 0:
        eu = -eu
    return ga, ef, eu, gc + ef * -0.075 + eu * 0.03, gc + ef * -0.012 + eu * 0.04


def joints(v, s):
    """Rest-pose joint positions of one side (s=+1 left/+Y, -1 right): shared by the mesh builders and the rig."""
    female = v['sex'] == 'f'
    gc = V((0.327, s * 0.378, 1.101))
    ga, ef, eu, wrist, knuck = hand_frame(s, gc)
    hip = V((-0.17, s * 0.11, 0.93))
    if s < 0:
        knee, ankle = V((0.17, s * 0.19, 0.80)), V((0.155, s * 0.15, 0.40))
    else:
        knee, ankle = V((0.02, s * 0.2, 0.72)), V((-0.165, s * 0.15, 0.39))
    return {'sh': V((-0.005, s * (0.2 if female else 0.215), 1.30)), 'el': V((0.14, s * 0.37, 1.15)), 'gc': gc,
            'wrist': wrist, 'knuck': knuck, 'hip': hip, 'knee': knee, 'ankle': ankle,
            'toe': ankle + V((0.16, 0, -0.08))}


def build_hand(M, s, gc, female=False):
    """A fist around the handlebar grip. gc: point on the grip axis under the middle of the hand."""
    SK = M['skin']
    k = 0.9 if female else 1.0
    ga, ef, eu, wrist, knuck = hand_frame(s, gc)

    def around(u, th, R):
        th = math.radians(th)
        return gc + ga * u + (ef * math.cos(th) + eu * math.sin(th)) * R

    p = []
    rg = 0.022
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
        p.append(ck.sweep('finger', pts, rad, SK, seg=8, samples=10, up=eu))
    # thumb: from the palm's inside edge, under the grip
    t0 = gc + ga * (-0.05 * k) + ef * -0.045 + eu * 0.012
    p.append(ck.sweep('thumb', [t0, around(-0.05 * k, 190, 0.036), around(-0.045 * k, 235, 0.034), around(-0.036 * k, 275, 0.032)],
                      lambda t, a: 0.0145 * k * (1 - 0.18 * t), SK, seg=8, samples=10, up=-ef))
    return p, wrist


# ------------------------------------------------------------------------------------------- arms

SLEEVE = {'tracksuit': 'long', 'cardigan': 'long', 'tshirt': 'short', 'polo': 'short', 'tank': 'none'}


def _limb_k(v):
    return 0.87 if v['sex'] == 'f' else (1.12 if v.get('build') == 'big' else 1.0)


def build_arm(M, v, s):
    side = 'L' if s > 0 else 'R'
    female = v['sex'] == 'f'
    k = _limb_k(v)
    T, TR, SK = M['top'], M['trim'], M['skin']
    sleeve_kind = SLEEVE[v['top']]
    J = joints(v, s)
    sh, el, gc = J['sh'], J['el'], J['gc']
    hand, wrist = build_hand(M, s, gc, female)
    fd = (wrist - el).normalized()
    cuff = wrist - fd * 0.045
    sh_in = sh - V((0.0, s * 0.04, -0.02))
    pts = [sh_in, sh, el, cuff]
    fr = ck.frames(pts, 44, up=V((0, 0, 1)))
    a_in = angle_of(fr, round(0.62 * 43), (sh + cuff) / 2 - el)     # inside of the elbow
    a_out = angle_of(fr, round(0.5 * 43), V((0, s, 0.6)))
    p = []
    if sleeve_kind == 'long':
        loose = 1.12 if v['top'] == 'cardigan' else 1.0

        def sleeve(t, a):
            base = lerp_list([0.072, 0.08, 0.07, 0.062, 0.058], t) * k * loose
            inner = max(0.0, math.cos(a - a_in))
            folds = ck.bumps(t, [0.56, 0.62, 0.68], 0.022, 0.09) * (0.25 + 0.75 * inner)
            bunch = ck.bumps(t, [0.83, 0.89, 0.94], 0.02, 0.07) * (0.75 + 0.25 * math.sin(3 * a + t * 17))
            return base * (1 + folds + bunch + 0.012 * math.sin(2 * a + 9 * t))

        p.append(ck.sweep('sleeve', pts, sleeve, T, seg=18, samples=44, caps=(True, False), up=V((0, 0, 1))))
        if v['top'] == 'tracksuit':
            for d in (-0.2, 0.2):
                p.append(flat_strip('stripe', fr, sleeve, a_out + d, 0.12, 0.8, TR))
        p.append(ck.sweep('cuff', [cuff - fd * 0.005, cuff + fd * 0.035],
                          lambda t, a: 0.056 * k * loose * (1 + 0.045 * math.cos(14 * a)), M['top_rib'], seg=42, samples=3,
                          caps=(False, False)))
    else:
        # bare arm: shoulder, a bit of biceps, elbow, forearm tapering into the wrist
        def arm(t, a):
            base = lerp_list([0.066, 0.064, 0.056, 0.05, 0.044], t) * k
            muscle = ck.bumps(t, [0.3], 0.1, 0.06 if not female else 0.02) * max(0.0, math.cos(a - a_out + 0.6))
            elbow = ck.bumps(t, [0.64], 0.04, 0.05) * max(0.0, -math.cos(a - a_in))
            return base * (1 + muscle + elbow)

        p.append(ck.sweep('arm', pts, arm, SK, seg=16, samples=36, caps=(True, False), up=V((0, 0, 1))))
        if sleeve_kind == 'short':   # a short sleeve over the upper arm, with a hem
            fs = ck.frames([sh_in, sh, sh.lerp(el, 0.5)], 16, up=V((0, 0, 1)))

            def short(t, a):
                return lerp_list([0.078, 0.084, 0.08], t) * k * (1 + 0.025 * math.sin(3 * a + 5 * t))

            p.append(ck.sweep('sleeve', [sh_in, sh, sh.lerp(el, 0.5)], short, T, seg=18, samples=16, caps=(True, False),
                              up=V((0, 0, 1))))
            hem_mat = TR if v['top'] == 'polo' else M['top_rib']
            c, tg = fs[-1][0], fs[-1][1]
            p.append(ck.sweep('hem', [c - tg * 0.012, c + tg * 0.004], lambda t, a: short(1.0, a) * 1.02, hem_mat,
                              seg=18, samples=3, caps=(False, False), up=V((0, 0, 1))))
    p.append(ck.sweep('wrist', [cuff, wrist + fd * 0.01], [0.042 * k, 0.04 * k], SK, seg=16, samples=6, caps=(False, True)))
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
                  upper, M['shoe'], seg=16, samples=16, up=up)]
    p.append(ck.sweep('sole', [V((-0.13, 0, 0.024)), V((0.0, 0, 0.022)), V((0.135, 0, 0.03))],
                      lambda t, a: ellipse(lerp_list([0.054, 0.058, 0.05], t), 0.024)(a), M['sole'], seg=16, samples=10, up=up))
    p.append(ck.sweep('midline', [V((-0.135, 0, 0.04)), V((0.0, 0, 0.038)), V((0.14, 0, 0.045))],
                      lambda t, a: ellipse(lerp_list([0.056, 0.06, 0.051], t), 0.006)(a), M['btrim'], seg=16, samples=10, up=up))
    p.append(torus('collar', 0.04, 0.013, (-0.08, 0, 0.128), M['sole'], rot=(0, math.radians(-10), 0), segU=16, segV=6))
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


def _foot_sweep(name, mat, w=0.046, h=0.042, lift=0.0):
    """A plain foot / sock / leather shoe body along +X (heel -> toe)."""
    def f(t, a):
        ww = lerp_list([w * 0.85, w, w * 1.05, w * 0.8], t)
        hh = lerp_list([h * 1.2, h, h * 0.75, h * 0.55], t)
        if math.cos(a) < 0:
            hh = min(hh, 0.026)
        return ellipse(ww, hh)(a)
    return ck.sweep(name, [V((-0.11, 0, 0.07 + lift)), V((-0.02, 0, 0.07 + lift)), V((0.07, 0, 0.055 + lift)), V((0.12, 0, 0.048 + lift))],
                    f, mat, seg=16, samples=14, up=V((0, 0, 1)))


def build_sandal(M, origin):
    """The classic: white socks in sandals."""
    p = [_foot_sweep('sock_foot', M['sock'])]
    p.append(ck.sweep('sandal_sole', [V((-0.13, 0, 0.018)), V((0.0, 0, 0.016)), V((0.14, 0, 0.02))],
                      lambda t, a: ellipse(lerp_list([0.05, 0.056, 0.05], t), 0.016)(a), M['leather'], seg=16, samples=10,
                      up=V((0, 0, 1))))
    for x, z in ((-0.07, 0.075), (0.0, 0.08), (0.07, 0.07)):
        p.append(ck.sweep('strap', [V((x, -0.056, 0.03)), V((x, 0, z + 0.03)), V((x, 0.056, 0.03))],
                          lambda t, a: ellipse(0.012, 0.004)(a), M['leather'], seg=8, samples=8, up=V((1, 0, 0))))
        p.append(lib.box('buckle', (0.016, 0.006, 0.014), (x, 0.052, 0.045), M['gold'], bevel=0.002))
    shoe = join(p, 'shoe_tmp')
    shoe.location = origin
    return shoe


def build_granny_shoe(M, origin):
    p = [_foot_sweep('granny', M['leather'], w=0.048, h=0.045)]
    p.append(ck.sweep('granny_sole', [V((-0.12, 0, 0.016)), V((0.0, 0, 0.014)), V((0.13, 0, 0.018))],
                      lambda t, a: ellipse(lerp_list([0.05, 0.054, 0.048], t), 0.016)(a), M['rubber'], seg=16, samples=10,
                      up=V((0, 0, 1))))
    p.append(lib.box('heel', (0.06, 0.08, 0.03), (-0.09, 0, 0.012), M['rubber'], bevel=0.008))
    p.append(lib.box('strap', (0.02, 0.1, 0.012), (0.03, 0, 0.098), M['leather'], bevel=0.005))
    p.append(lib.box('buckle', (0.022, 0.012, 0.022), (0.03, 0.05, 0.09), M['gold'], bevel=0.003))
    shoe = join(p, 'shoe_tmp')
    shoe.location = origin
    return shoe


def build_leg(M, v, s):
    side = 'L' if s > 0 else 'R'
    k = _limb_k(v)
    J = joints(v, s)
    hip, knee, ankle = J['hip'], J['knee'], J['ankle']
    B, SK = M['bottom'], M['skin']
    bottom = v['bottom']
    dn = (knee - ankle).normalized()
    hem = ankle + dn * 0.025
    pts = [hip, knee, hem]
    fr = ck.frames(pts, 44, up=V((1, 0, 0)))
    a_back = angle_of(fr, 22, (hip + hem) / 2 - knee)     # hollow of the knee
    a_out = angle_of(fr, 14, V((0, s, 0.3)))
    p = []
    if bottom in ('trackpants', 'jeans', 'leggings'):
        tight = {'trackpants': 1.0, 'jeans': 0.93, 'leggings': 0.78}[bottom]
        fold = {'trackpants': 1.0, 'jeans': 0.7, 'leggings': 0.15}[bottom]

        def trouser(t, a):
            base = lerp_list([0.1, 0.092, 0.08, 0.072, 0.07], t) * k * tight
            back = max(0.0, math.cos(a - a_back))
            folds = ck.bumps(t, [0.46, 0.52, 0.58], 0.025, 0.08) * (0.2 + 0.8 * back) * fold
            bunch = ck.bumps(t, [0.8, 0.86, 0.92], 0.022, 0.08) * (0.7 + 0.3 * math.sin(3 * a + t * 13)) * fold
            return base * (1 + folds + bunch + 0.015 * math.sin(2 * a + 7 * t) * fold)

        p.append(ck.sweep('trousers', pts, trouser, B, seg=18, samples=44, caps=(True, False), up=V((1, 0, 0))))
        if bottom == 'trackpants':
            for d in (-0.2, 0.2):
                p.append(flat_strip('stripe', fr, trouser, a_out + d, 0.04, 0.78, M['btrim']))
            p.append(ck.sweep('cuff', [hem + dn * 0.005, ankle - dn * 0.02],
                              lambda t, a: 0.064 * k * (1 + 0.045 * math.cos(14 * a)), M['bottom_rib'], seg=42, samples=3,
                              caps=(False, False)))
        elif bottom == 'jeans':   # outer seam + a rolled-up hem
            p.append(flat_strip('seam', fr, trouser, a_out, 0.03, 0.95, M['btrim'], width=0.004, height=0.002))
            p.append(ck.sweep('rollup', [hem + dn * 0.03, hem - dn * 0.01],
                              lambda t, a: trouser(1.0, a) * 1.1 * (1 + 0.03 * math.sin(5 * a)), B, seg=18, samples=4,
                              caps=(False, False)))
        else:
            p.append(ck.sweep('ankle', [hem + dn * 0.01, ankle - dn * 0.02], [0.05 * k, 0.046 * k], SK, seg=14, samples=4,
                              caps=(False, False)))
    else:
        # bare legs (shorts, or a skirt hiding the top)
        def leg(t, a):
            base = lerp_list([0.085, 0.078, 0.066, 0.06, 0.048], t) * k
            calf = ck.bumps(t, [0.68], 0.1, 0.12) * max(0.0, math.cos(a - a_back))
            return base * (1 + calf + ck.bumps(t, [0.5], 0.04, 0.05) * max(0.0, -math.cos(a - a_back)))

        p.append(ck.sweep('leg', [hip, knee, ankle - dn * 0.02], leg, SK, seg=16, samples=36, caps=(True, False), up=V((1, 0, 0))))
        if bottom == 'shorts':
            # follow the leg's own curve (frames of the leg sweep), a size looser
            ns = round(0.4 * (len(fr) - 1))
            sp = [fr[i][0] for i in range(0, ns + 1, 2)]
            p.append(ck.sweep('shorts', sp, lambda t, a: lerp_list([0.112, 0.108, 0.104], t) * k
                              * (1 + 0.03 * math.sin(3 * a + 6 * t)), B, seg=18, samples=12, caps=(True, False), up=V((1, 0, 0))))
            hd = fr[ns][1]
            end = sp[-1]
            p.append(ck.sweep('shorts_hem', [end - hd * 0.014, end + hd * 0.004], lambda t, a: 0.108 * k, M['bottom_rib'],
                              seg=18, samples=3, caps=(False, False), up=V((1, 0, 0))))
    shoes = v.get('shoes', 'sneakers' if bottom != 'skirt' else 'granny')
    shoe_o = ankle + V((0.04, 0, -0.105))
    if shoes in ('sneakers', 'color'):
        if bottom in ('shorts', 'skirt'):   # a ribbed white sock above the sneaker
            p.append(ck.sweep('sock', [ankle + dn * 0.07, ankle - dn * 0.02], lambda t, a: 0.05 * k * (1 + 0.04 * math.cos(12 * a)),
                              M['sock'], seg=36, samples=4, caps=(False, False)))
        p.append(build_sneaker(M, shoe_o, s))
    elif shoes == 'sandals':
        p.append(ck.sweep('sock', [ankle + dn * 0.12, ankle - dn * 0.04], lambda t, a: 0.054 * k * (1 + 0.04 * math.cos(12 * a)),
                          M['sock'], seg=36, samples=4, caps=(False, False)))
        p.append(build_sandal(M, shoe_o))
    else:
        p.append(build_granny_shoe(M, shoe_o))
    return join(p, f'Rider_Leg{side}', pivot=hip)


# ------------------------------------------------------------------------------------------- torso

# Chest / back prints per variant (TopTrim colour: contrasts with the shirt in-game)
PRINTS = {
    'V01': ('ABIBAS', 'KONING', 'VAN HET PLEIN'),
    'V02': ('PATAT', 'MET', 'MAYO'),
    'V03': ('SKATE OF NIET', None, None),
    'V04': ('SPORTSCHOOL', 'BIJNA', 'ELKE DAG'),
    'V05': ('', None, None),
    'V06': ('NIJVERDAL', 'NO', 'STRESS'),
    'V07': ('GOOD VIBES', None, None),
    'V08': ('ABIBAS', 'QUEEN', 'VAN DE WIJK'),
    'V09': ('', None, None),
    'V10': ('FATBIKE GANG', 'RIJDEN', 'NIET TRAPPEN'),
    'V11': ('HAVERMELK', 'SLOW', 'LIVING'),
    'V12': ('ABIBAS', 'BRUH', None),
}


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
    top, female = v['top'], v['sex'] == 'f'
    big, belly = v.get('build') == 'big', v.get('build') == 'belly'
    sx, sy = (0.88, 1.25) if big else ((0.85, 1.08) if female else (0.85, 1.2))
    size = 1.12 if big else (0.94 if female else 1.0)
    pts = [HIP - AXIS * 0.05, HIP + AXIS * 0.07, CHEST - AXIS * 0.02, CHEST + AXIS * 0.07]
    fr = ck.frames(pts, 40, up=FWD)
    n = len(fr) - 1
    loose = 1.04 if top == 'cardigan' else 1.0

    def body(t, a):
        R = lerp_list([0.165, 0.165, 0.178, 0.19, 0.185], t) * size * loose
        r = R * ellipse(sy, sx)(a)
        front = max(0.0, math.cos(a))
        folds = ck.bumps(t, [0.2, 0.3, 0.4], 0.035, 0.035) * front ** 2
        chest = ck.bumps(t, [0.72], 0.12, 0.05 if not female else 0.02) * front
        extra = 0.0
        if female:   # a modest cartoon bust
            extra += ck.bumps(t, [0.68], 0.09, 0.32) * sum(math.exp(-((a - c) / 0.4) ** 2) for c in (-0.55, 0.55))
        if belly:
            extra += ck.bumps(t, [0.3], 0.16, 0.38) * front ** 1.5
        return r * (1 + folds + chest + extra + 0.01 * math.sin(3 * a + 8 * t))

    torso = ck.sweep('torso', pts, body, T, seg=32, samples=40, caps=(False, True), up=FWD)
    p = [torso]
    p.append(sphere('pelvis', 0.15 * (1.08 if big or belly else 1.0), (-0.19, 0, 0.93), M['bottom'],
                    scale=(1.0, 1.25 if female else 1.15, 0.72), seg=20, rings=10))
    neck_base = CHEST + AXIS * 0.15
    hem_mat = M['top_rib'] if top in ('tracksuit', 'cardigan') else T
    p.append(ck.sweep('waistband', [HIP - AXIS * 0.075, HIP - AXIS * 0.02],
                      lambda t, a: body(0.02, a) * 1.03 * (1 + (0.02 * math.cos(44 * a) if hem_mat != T else 0.0)), hem_mat,
                      seg=66, samples=3, caps=(False, False), up=FWD))
    up = AXIS

    def surf(t, a):
        i = round(t * n)
        pt = ck.surface(fr, body, i, a)
        return pt, (pt - fr[i][0]).normalized()

    if top == 'tracksuit':
        # stand-up collar, zip with puller, zipped pockets
        p.append(ck.sweep('collar', [neck_base - AXIS * 0.03, neck_base + AXIS * 0.045 + FWD * 0.012],
                          lambda t, a: ellipse(0.088, 0.082)(a) * size * (1 + 0.04 * t), M['top_rib'], seg=40, samples=6,
                          caps=(False, False), up=FWD))
        zp = [ck.surface(fr, body, i, 0.0) + FWD * 0.002 for i in range(2, n - 6, 4)]
        p.append(ck.sweep('zip', zp, lambda t, a: ellipse(0.007, 0.0035)(a), M['chrome'], seg=6, samples=24, up=FWD))
        p.append(lib.box('zip_pull', (0.008, 0.016, 0.034), zp[-1] - AXIS * 0.03 + FWD * 0.006, M['chrome'],
                         rot=(0, TORSO_ANG, 0), bevel=0.003))
        for sgn in (-1, 1):
            p.append(flat_strip('pocket', fr, body, sgn * 1.05, 0.14, 0.34, M['chrome'], width=0.0045, height=0.0035, n=8))
            for d in (-0.012, 0.012):   # shoulder stripes continue the sleeves' stripes over the top
                p.append(tube('shoulder_stripe', neck_base + V((d * 3, sgn * 0.09, -0.02)),
                              V((-0.005 + d * 3, sgn * 0.21 * size, 1.33)), 0.0055, TR, seg=6))
    elif top in ('tshirt', 'tank'):
        deep = 0.05 if top == 'tank' else 0.0
        p.append(ck.sweep('neckline', [neck_base - AXIS * (0.035 + deep), neck_base - AXIS * (0.01 + deep)],
                          lambda t, a: ellipse(0.088, 0.08 + deep * 0.6)(a) * size, M['top_rib'], seg=36, samples=3,
                          caps=(False, False), up=FWD))
    elif top == 'polo':
        for sgn in (-1, 1):
            p.append(lib.box('collar_flap', (0.075, 0.075, 0.012), neck_base + FWD * 0.06 + V((0, sgn * 0.045, 0)), TR,
                             rot=(sgn * 0.5, TORSO_ANG - 0.9, 0), bevel=0.006))
        p.append(ck.sweep('collar', [neck_base - AXIS * 0.02, neck_base + AXIS * 0.03],
                          lambda t, a: ellipse(0.085, 0.08)(a), TR, seg=32, samples=4, caps=(False, False), up=FWD))
        for i in range(3):
            pt, out = surf(0.9 - i * 0.07, 0.0)
            p.append(sphere('button', 0.009, pt + out * 0.004, M['button'], seg=10, rings=5))
        pt, out = surf(0.72, -0.55)   # the little croc... a frikandel
        p.append(capsule('frikandel', pt + up * 0.0 - V((0, 0.018, 0)), pt + V((0, 0.018, 0)), 0.006, 0.006, M['leaf'],
                         seg=8, rings=4))
    elif top == 'cardigan':
        # an open cardigan over a blouse, with buttons and a soft collar
        p.append(flat_strip('blouse', fr, body, 0.0, 0.04, 0.96, TR, width=0.055, height=0.005, n=14))
        for sgn in (-1, 1):
            p.append(flat_strip('placket', fr, body, sgn * 0.42, 0.05, 0.9, M['top_rib'], width=0.014, height=0.006, n=12))
            for i in range(4):
                bp, bo = surf(0.2 + i * 0.18, sgn * 0.42)
                p.append(sphere('button', 0.011, bp + bo * 0.006, M['button'], seg=10, rings=5))
        p.append(torus('collar', 0.09, 0.024, neck_base, T, rot=(0, TORSO_ANG + 0.3, 0), segU=32, segV=8))
    # prints
    chest_txt, back1, back2 = PRINTS.get(v['id'], ('', None, None))
    if chest_txt and top != 'cardigan':
        cp, co = surf(0.66, -0.5 if top == 'tracksuit' else 0.0)
        p.append(_decal('logo', chest_txt, 0.032 if top == 'tracksuit' else 0.036, torso, cp + (up * 0.0), co, up, TR))
    if back1:
        bc, bo = surf(0.62, math.pi)
        p.append(_decal('back_print', back1, 0.075, torso, bc + up * 0.04, bo, up, TR, extrude=0.003))
        if back2:
            p.append(_decal('back_print2', back2, 0.034, torso, bc - up * 0.035, bo, up, TR, extrude=0.003))
    if v.get('chain'):
        links = []
        for i in range(34):
            a = 2 * math.pi * i / 34
            links.append(torus('link', 0.012, 0.0034, (math.cos(a) * 0.105, math.sin(a) * 0.112, 0), M['gold'], segU=8, segV=4,
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
    if v['bottom'] == 'skirt':
        p.append(ck.sweep('skirt', [V((-0.12, 0, 0.98)), V((-0.06, 0, 0.84)), V((-0.02, 0, 0.78))],
                          lambda t, a: lerp_list([0.2, 0.27, 0.31], t) * ellipse(1.05, 1.0)(a) * (1 + 0.04 * math.sin(7 * a)),
                          M['bottom'], seg=40, samples=10, caps=(True, False), up=V((1, 0, 0))))
    return join(p, 'Rider_Torso', pivot=HIP)


# ------------------------------------------------------------------------------------------- head

def build_head(M, v):
    female, age = v['sex'] == 'f', v['age']
    big = v.get('build') == 'big'
    sk, sd = M['skin'], M['skin_dark']
    skin = [sphere('head', HEAD_R, HC, sk, scale=HEAD_SCALE * (0.97 if female else 1), seg=48, rings=24)]
    jaw = (0.93, 1.0, 0.74) if female else ((1.08, 1.22, 0.86) if big else (1.0, 1.12, 0.8))
    skin.append(sphere('jaw', 0.14 * HS, hv(0.03, 0, -0.085), sk, scale=jaw))
    skin.append(sphere('chin', 0.05 * HS, hv(0.13, 0, -0.15), sk, scale=(0.75, 1.1, 0.85) if female else (0.8, 1.3, 0.9)))
    for s in (-1, 1):
        skin.append(sphere('cheek', 0.052 * HS, hv(0.105, s * 0.085, -0.04), sk))
        skin.append(sphere('cheekbone', 0.04 * HS, hv(0.11, s * 0.1, 0.0), sk, scale=(0.8, 1.2, 0.7)))
    skin.append(sphere('brow_ridge', 0.05 * HS, hv(0.135, 0, 0.075), sk, scale=(0.75, 2.6, 0.5 if female else 0.6)))
    nose = 0.042 if female else (0.058 if age == 'senior' else 0.05)
    skin.append(sphere('nose', nose * HS, hv(0.19, 0, -0.015), sk, scale=(1.0, 0.95, 0.85 if age != 'senior' else 1.0)))
    for s in (-1, 1):
        skin.append(sphere('nostril_wing', nose * 0.48 * HS, hv(0.175, s * 0.033, -0.03), sk))
    skin.append(sphere('nose_bridge', 0.026 * HS, hv(0.172, 0, 0.03), sk, scale=(1, 0.9, 1.6)))
    eyes = []
    er = (0.05 if age == 'teen' else 0.045) * HS
    for s in (-1, 1):
        e = hv(0.138, s * 0.066, 0.03)
        skin.append(sphere('eyelid', er * 1.08, e + V((0.0, 0, 0.022)) * HS, sk, scale=(0.78, 1.04, 0.62),
                           rot=(s * math.radians(22 if not female else 14), 0, 0)))
        skin.append(sphere('lowerlid', er * 1.0, e + V((0.004, 0, -0.024)) * HS, sk, scale=(0.72, 1.0, 0.4)))
        if age == 'senior':
            skin.append(sphere('eyebag', er * 0.7, e + V((0.008, 0, -0.04)) * HS, sk, scale=(0.6, 1.15, 0.45)))
        eyes.append((s, e))
    neck_r = 0.06 if female else (0.08 if big else 0.07)
    skin.append(capsule('neck', (0.0, 0, 1.31), (0.045, 0, 1.45), neck_r, neck_r * 0.97, sk))
    face = join(skin, 'skin_tmp')
    ck.remesh(face, 0.005, smooth=6, target=5500)
    p = [face]
    for s, e in eyes:
        p.append(sphere('eye', er, e, M['eye'], scale=(0.75, 1, 0.85), seg=20, rings=10))
        p.append(sphere('iris', 0.024 * HS, e + V((0.029, -s * 0.004, -0.004)) * HS, M['iris'], scale=(0.45, 1, 1), seg=16, rings=8))
        p.append(sphere('pupil', 0.011 * HS, e + V((0.038, -s * 0.004, -0.004)) * HS, M['pupil'], scale=(0.4, 1, 1), seg=12, rings=6))
        p.append(sphere('glint', 0.004 * HS, e + V((0.041, 0, 0.006)) * HS, M['eye'], seg=8, rings=4))
        ear_z = 1.15 if age == 'senior' else 1.0
        p.append(sphere('ear', 0.05 * HS, hv(-0.01, s * 0.168, -0.005), sk, scale=(0.55, 0.35, ear_z), seg=16, rings=10))
        p.append(sphere('ear_in', 0.03 * HS, hv(-0.004, s * 0.178, -0.005), sd, scale=(0.5, 0.2, 0.8 * ear_z), seg=12, rings=6))
        p.append(sphere('nostril', 0.011 * HS, hv(0.19, s * 0.022, -0.046), sd, scale=(1.0, 0.8, 0.5), seg=10, rings=5))
        if female:   # lashes flicking out at the outer corner
            for i in range(3):
                a = e + V((0.03, s * (0.014 + i * 0.012), 0.022 - i * 0.003)) * HS
                p.append(ck.sweep('lash', [a, a + V((0.008, s * 0.008, 0.008)) * HS, a + V((0.012, s * 0.016, 0.01)) * HS],
                                  lambda t, a2: 0.003 * HS * (1 - 0.6 * t), M['pupil'], seg=5, samples=5))
        # angry brows: thick at the nose, tapering up and out (thinner, less of a scowl for the women)
        bp = [hv(0.178, s * 0.016, 0.066), hv(0.17, s * 0.06, 0.088), hv(0.145, s * 0.112, 0.09)]
        th = 0.55 if female else (0.8 if age == 'teen' else 1.0)
        p.append(ck.sweep('brow', bp, lambda t, a, th=th: ellipse(0.011 * HS * (1 - 0.45 * t), 0.017 * HS * th * (1 - 0.5 * t))(a),
                          M['brow'], seg=12, samples=12, up=V((0, 0, 1))))
        if v.get('earrings'):
            p.append(torus('earring', 0.02 * HS, 0.0035 * HS, hv(0.0, s * 0.176, -0.08), M['gold'], rot=(math.pi / 2, 0, 0), segU=16, segV=6))
        if age == 'senior':   # smile lines
            p.append(ck.sweep('fold', [hv(0.17, s * 0.05, -0.03), hv(0.168, s * 0.075, -0.07), hv(0.155, s * 0.085, -0.11)],
                              lambda t, a: 0.0045 * HS, sd, seg=6, samples=8))
    m = hv(0.158, 0, -0.092)
    lip = M['lips'] if female else sd
    p.append(sphere('mouth', 0.05 * HS, m, M['mouth'], scale=(0.4, 1.55 if female else 1.75, 0.62), seg=20, rings=10))
    p.append(sphere('tongue', 0.032 * HS, m + V((0.0, 0.01, -0.016)) * HS, M['tongue'], scale=(0.6, 1.3, 0.45), seg=16, rings=8))
    p.append(lib.box('teeth_top', (0.02 * HS, 0.13 * HS, 0.02 * HS), m + V((0.008, 0, 0.0115)) * HS, M['teeth'], bevel=0.006, segs=3))
    p.append(lib.box('teeth_bot', (0.02 * HS, 0.12 * HS, 0.018 * HS), m + V((0.007, 0, -0.0115)) * HS, M['teeth'], bevel=0.006, segs=3))
    if v.get('braces'):
        p.append(lib.box('braces', (0.006 * HS, 0.125 * HS, 0.005 * HS), m + V((0.019, 0, 0.012)) * HS, M['braces'], bevel=0.002))
        for i in range(6):
            p.append(lib.box('bracket', (0.006 * HS, 0.01 * HS, 0.009 * HS), m + V((0.02, -0.05 + i * 0.02, 0.012)) * HS,
                             M['braces'], bevel=0.001))
    p.append(sphere('lip_top', 0.05 * HS, m + V((0.014, 0, 0.03)) * HS, lip, scale=(0.3, 1.7, 0.2 if female else 0.17), seg=20, rings=10))
    p.append(sphere('lip_bot', 0.05 * HS, m + V((0.012, 0, -0.03)) * HS, lip, scale=(0.3, 1.55, 0.24 if female else 0.19), seg=20, rings=10))
    facial = v.get('facial')
    if facial == 'goatee':
        gp = [hv(0.172, 0, -0.14), hv(0.166, 0, -0.168), hv(0.145, 0, -0.192)]
        p.append(ck.sweep('goatee', gp, lambda t, a: ellipse(0.03 * HS * (1 - 0.4 * t), 0.016 * HS)(a), M['hair'],
                          seg=14, samples=10, up=V((1, 0, 0))))
        for s in (-1, 1):  # thin moustache that joins the goatee
            mp = [hv(0.19, 0, -0.06), hv(0.18, s * 0.06, -0.075), hv(0.165, s * 0.075, -0.12)]
            p.append(ck.sweep('moustache', mp, lambda t, a: 0.007 * HS * (1 - 0.4 * t), M['hair'], seg=8, samples=10))
    elif facial == 'stubble':
        st = sphere('stubble', 0.14 * HS * 1.03, hv(0.03, 0, -0.085), M['skin_dark'], scale=(jaw[0] * 1.02, jaw[1] * 1.02, jaw[2] * 1.03),
                    seg=32, rings=16)
        _cut(st, lambda x, y, z: z < 0.15 and x > -0.3 and not (x > 0.55 and z > -0.4 and abs(y) < 0.5))
        p.append(st)
    elif facial == 'beard':
        jr = 0.14 * HS * 1.07
        beard_blobs = [sphere('beard', jr, hv(0.03, 0, -0.085), M['hair'], scale=(jaw[0] * 1.02, jaw[1] * 1.02, jaw[2] * 1.05), seg=40, rings=20)]
        _cut(beard_blobs[0], lambda x, y, z: z < 0.15 and x > -0.35 and not (x > 0.55 and z > -0.45 and abs(y) < 0.55))
        p += beard_blobs
        for s in (-1, 1):
            mp = [hv(0.19, 0, -0.058), hv(0.183, s * 0.05, -0.068), hv(0.17, s * 0.085, -0.09)]
            p.append(ck.sweep('moustache', mp, lambda t, a: 0.016 * HS * (1 - 0.3 * t), M['hair'], seg=10, samples=10))
    elif facial == 'moustache':   # a proper walrus
        for s in (-1, 1):
            mp = [hv(0.192, 0, -0.055), hv(0.185, s * 0.045, -0.062), hv(0.172, s * 0.085, -0.085)]
            p.append(ck.sweep('moustache', mp, lambda t, a: ellipse(0.022 * HS * (1 - 0.5 * t), 0.014 * HS)(a), M['hair'],
                              seg=12, samples=12, up=V((0, 0, 1))))
    if v.get('glasses'):
        for s in (-1, 1):
            p.append(torus('lens_rim', 0.038 * HS, 0.005 * HS, hv(0.19, s * 0.066, 0.03), M['glasses'], rot=(0, math.pi / 2, 0), segU=24, segV=6))
            p.append(tube('temple', hv(0.185, s * 0.1, 0.035), hv(0.0, s * 0.158, 0.035), 0.004 * HS, M['glasses'], seg=6))
        p.append(tube('bridge', hv(0.195, -0.028, 0.035), hv(0.195, 0.028, 0.035), 0.004 * HS, M['glasses'], seg=6))
    return join(p, 'Rider_Head', pivot=(0.02, 0, 1.38))


def _cut(o, keep):
    """Delete the vertices of a sphere-ish shell outside keep(x, y, z) (unit coords around its centre)."""
    import bmesh
    bm = bmesh.new()
    bm.from_mesh(o.data)
    R = max(o.dimensions) / 2 / max(o.scale)
    kill = [q for q in bm.verts if not keep(q.co.x / R, q.co.y / R, q.co.z / R)]
    bmesh.ops.delete(bm, geom=kill, context='VERTS')
    bm.to_mesh(o.data)
    bm.free()


# ------------------------------------------------------------------------------------------- hair

def _curls(M, n, keep, centre, r, spread=1.0, lift=0.0):
    blobs = [sphere('hair_base', HEAD_R * 0.98, centre, M['hair'], scale=(1.02, 0.97, 0.82))]
    tries = 0
    while len(blobs) < n and tries < 20000:
        tries += 1
        d = V((random.uniform(-1, 1), random.uniform(-1, 1), random.uniform(-1, 1)))
        if not 0.2 < d.length <= 1:
            continue
        d.normalize()
        if not keep(d):
            continue
        pos = centre + V((d.x, d.y * 0.95, d.z * 0.85)) * HEAD_R * spread + d * random.uniform(0.0, 0.02) + V((0, 0, lift))
        blobs.append(ico('curl', random.uniform(*r), pos, M['hair'], subdiv=2))
    o = join(blobs, 'curls_tmp')
    ck.remesh(o, 0.0055, smooth=2, target=4000)
    return o


def build_hair(M, v):
    """Broccoli and perm are rebuilt as one lumpy, remeshed mass; the other styles, caps and headphones come from
    the classic builder (their smooth shells already work with the AO)."""
    random.seed(11)
    style = v['hair']
    if style not in ('broccoli', 'perm'):
        import build_riders
        return build_riders.build_hair(M, v)
    p = []
    if style == 'broccoli':
        from build_riders import shell
        p.append(shell('fade', M['fade'], lambda x, y, z: z > -0.12 and x < 0.02 + max(0.0, z - 0.2) * 2.0, k=1.012))
        p.append(_curls(M, 260, lambda d: d.z >= (0.4 if d.x > 0.4 else 0.14), hv(-0.005, 0, 0.085), (0.022, 0.042)))
        line = []   # a shaved line in the fade (left side)
        for f in (55, 75, 95, 115, 132):
            ph, ps = math.radians(f), math.radians(-6 + (f - 55) * 0.08)
            d = V((math.cos(ph) * math.cos(ps), math.sin(ph) * math.cos(ps), math.sin(ps)))
            line.append(HC + V((d.x * HEAD_SCALE.x, d.y * HEAD_SCALE.y, d.z * HEAD_SCALE.z)) * HEAD_R * 1.016)
        p.append(ck.sweep('shaved_line', line, lambda t, a: ellipse(0.005, 0.0022)(a), M['skin'], seg=8, samples=16))
    else:   # granny perm: tight curls all round, clear of the face and ears
        p.append(_curls(M, 220, lambda d: d.z > -0.25 and not (d.x > 0.45 and d.z < 0.55) and not (abs(d.y) > 0.8 and d.z < 0.2 and abs(d.x) < 0.3),
                        hv(-0.01, 0, 0.06), (0.026, 0.04), spread=1.03))
    return join(p, 'Rider_Hair', pivot=HC)
