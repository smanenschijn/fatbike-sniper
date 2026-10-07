"""Build the fatbiker (rider + fatbike) from separate parts, export GLB and render previews.

Run:  Blender -b -P blender/build_fatbiker.py [-- --no-render]
"""
import math
import os
import random
import sys

import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(__file__))
import lib  # noqa: E402
from lib import (box, capsule, cyl, ico, join, material, sphere, subsurf, torus,  # noqa: E402
                 transform_mesh, tube, ROT_X90)

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
V = Vector
random.seed(7)


# ================================================================ materials

def mats():
    return {
        'skin': material('Skin', '#c98d62', rough=0.55, sss=0.08),
        'skin_dark': material('SkinShade', '#a8694a', rough=0.6),
        'hair': material('HairBlack', '#171311', rough=0.8, sheen=0.15),
        'fade': material('HairFade', '#4a3a32', rough=0.95),
        'suit': material('TracksuitBlack', '#1a1a20', rough=0.45, sheen=0.3),
        'stripe': material('TracksuitStripe', '#f4f4f4', rough=0.4),
        'sneaker': material('Sneaker', '#f7f7f5', rough=0.45),
        'sole': material('Sole', '#d9d4ca', rough=0.7),
        'eye': material('EyeWhite', '#ffffff', rough=0.15),
        'iris': material('Iris', '#7a4a22', rough=0.2),
        'pupil': material('Pupil', '#050505', rough=0.05),
        'brow': material('Brow', '#15100d', rough=0.8),
        'mouth': material('MouthInside', '#5a1c1e', rough=0.6),
        'teeth': material('Teeth', '#fff8e6', rough=0.25),
        'gold': material('Gold', '#ffc44d', rough=0.22, metal=1.0),
        'steel': material('Steel', '#d4d8de', rough=0.15, metal=1.0),
        'knife_grip': material('KnifeGrip', '#1d1d1d', rough=0.5),
        'shades': material('ShadesFrame', '#0c0c0c', rough=0.2, coat=0.6),
        'lens': material('ShadesLens', '#101826', rough=0.05, metal=0.6),
        'frame': material('BikeFrame', '#2a2c30', rough=0.42, metal=0.35, coat=0.3),
        'tyre': material('Tyre', '#1a1a1a', rough=0.88),
        'rim': material('Rim', '#3a3b3e', rough=0.35, metal=0.7),
        'accent': material('BikeAccent', '#ff7a1a', rough=0.35, coat=0.5),
        'chrome': material('Chrome', '#dadada', rough=0.12, metal=1.0),
        'seat': material('Seat', '#201b18', rough=0.55, sheen=0.2),
        'rubber': material('Rubber', '#111111', rough=0.8),
        'light': material('HeadLight', '#ffffff', rough=0.1, emission='#fff4d6', strength=6),
        'tail': material('TailLight', '#ff2a1a', rough=0.1, emission='#ff2a1a', strength=4),
        'screen': material('Display', '#0a1a22', rough=0.1, emission='#3fd0ff', strength=1.5),
    }


# ================================================================ bike

R_AXLE = 0.33
FRONT_AXLE = V((0.60, 0, R_AXLE))
REAR_AXLE = V((-0.58, 0, R_AXLE))
BB = V((0.0, 0, 0.30))


def build_wheel(name, M, rear=False):
    """Wheel built flat (axis = Z) then rotated so the axle is the Y axis."""
    p = []
    tyre_R, tyre_r = 0.25, 0.08
    p.append(torus(name + '_tyre', tyre_R, tyre_r, mat=M['tyre'], segU=64, segV=16, rz=0.075))
    # tread knobs, two staggered rows
    knobs = []
    n = 44
    for i in range(n):
        for row in (-1, 1):
            a = 2 * math.pi * (i + (0.5 if row > 0 else 0)) / n
            k = box(f'{name}_knob', (0.022, 0.036, 0.04), mat=M['tyre'], bevel=0.006, segs=1)
            k.location = (math.cos(a) * 0.325, math.sin(a) * 0.325, row * 0.032)
            k.rotation_euler = (0, 0, a)
            knobs.append(k)
    p += knobs
    # sidewall accent ring
    for z in (-0.05, 0.05):
        p.append(torus(name + '_wall', 0.255, 0.006, (0, 0, z), M['accent'], segU=64, segV=6))
    # rim + accent edges
    p.append(torus(name + '_rim', 0.19, 0.025, mat=M['rim'], segU=64, segV=10, rz=0.055))
    for z in (-0.052, 0.052):
        p.append(torus(name + '_rimedge', 0.205, 0.007, (0, 0, z), M['accent'], segU=64, segV=6))
    # hub (fat motor hub in the rear)
    hub_r = 0.075 if rear else 0.04
    p.append(cyl(name + '_hub', hub_r, 0.11 if rear else 0.13, mat=M['rim'], seg=32))
    p.append(cyl(name + '_axle', 0.012, 0.2, mat=M['chrome'], seg=12))
    # spokes
    for i in range(24):
        a = 2 * math.pi * i / 24
        z = 0.035 if i % 2 else -0.035
        a2 = a + (0.25 if i % 2 else -0.25)
        p1 = (math.cos(a) * hub_r * 0.9, math.sin(a) * hub_r * 0.9, z)
        p2 = (math.cos(a2) * 0.17, math.sin(a2) * 0.17, z * 0.4)
        p.append(tube(name + '_spoke', p1, p2, 0.0035, M['chrome'], seg=6))
    # brake disc (left), sprocket (right, rear only)
    p.append(cyl(name + '_disc', 0.085, 0.004, (0, 0, -0.07), M['steel'], seg=40))
    p.append(cyl(name + '_disc_hub', 0.03, 0.012, (0, 0, -0.07), M['rim'], seg=16))
    if rear:
        p.append(cyl(name + '_sprocket', 0.05, 0.012, (0, 0, 0.068), M['chrome'], seg=24))
    w = join(p, name)
    transform_mesh(w, ROT_X90)
    return w


def build_crank(M):
    p = [cyl('ring', 0.095, 0.008, mat=M['chrome'], seg=40),
         torus('ring_teeth', 0.095, 0.006, mat=M['rim'], segU=40, segV=6)]
    for i in range(5):
        a = 2 * math.pi * i / 5
        p.append(tube('ring_arm', (0, 0, 0.006), (math.cos(a) * 0.08, math.sin(a) * 0.08, 0.006),
                      0.008, M['rim'], seg=6))
    for o in p:  # ring sits on the right side of the bike (-Y)
        o.location = V(o.location) + V((0, 0, 0.09))
    ring = join(p, 'ring_tmp')
    transform_mesh(ring, ROT_X90)

    q = [ring, cyl('bb_axle', 0.022, 0.24, mat=M['chrome'], rot=(math.pi / 2, 0, 0), seg=16)]
    for side, dirx in ((-1, 1), (1, -1)):  # right crank forward, left crank back
        y = side * 0.11
        q.append(box('crank', (0.18, 0.018, 0.03), (dirx * 0.08, y, 0), M['rim'], bevel=0.008))
        pedal = (dirx * 0.17, side * 0.15, 0)
        q.append(box('pedal', (0.1, 0.09, 0.022), pedal, M['rubber'], bevel=0.006))
        q.append(box('pedal_refl', (0.012, 0.07, 0.012), (pedal[0] + 0.05, pedal[1], 0), M['accent']))
    crank = join(q, 'Bike_Crank')
    crank.location = BB
    return crank


def build_frame(M):
    p = []
    F = M['frame']
    ht_b, ht_t = V((0.50, 0, 0.72)), V((0.45, 0, 0.93))
    beam_f, beam_r = V((0.47, 0, 0.83)), V((-0.10, 0, 0.66))
    p.append(tube('headtube', ht_b, ht_t, 0.042, F, seg=24))
    p.append(capsule('topbeam', beam_r, beam_f, 0.045, 0.045, F))
    p.append(capsule('downtube', (0.05, 0, 0.33), (0.49, 0, 0.76), 0.04, 0.038, F))
    p.append(capsule('seattube', BB, (-0.12, 0, 0.72), 0.036, 0.034, F))
    p.append(sphere('bb_shell', 0.055, BB, F, scale=(1, 1.4, 1)))
    for s in (-1, 1):
        p.append(capsule('chainstay', (0.0, s * 0.05, 0.30), REAR_AXLE + V((0, s * 0.08, 0)), 0.02, 0.016, F))
        p.append(capsule('seatstay', (-0.11, s * 0.035, 0.68), REAR_AXLE + V((0, s * 0.08, 0)), 0.018, 0.015, F))
        p.append(box('dropout', (0.06, 0.012, 0.05), REAR_AXLE + V((0, s * 0.085, 0)), F, bevel=0.01))
    # battery on the top beam
    d = beam_f - beam_r
    ang = math.atan2(d.z, d.x)
    mid = (beam_f + beam_r) / 2 + V((-math.sin(ang), 0, math.cos(ang))) * 0.06
    p.append(box('battery', (0.40, 0.12, 0.09), mid, F, rot=(0, -ang, 0), bevel=0.03, segs=4))
    p.append(box('battery_stripe', (0.30, 0.125, 0.012), mid + V((0, 0, 0.012)), M['accent'], rot=(0, -ang, 0)))
    p.append(box('battery_lock', (0.03, 0.13, 0.03), mid + V((-0.15, 0, 0)), M['chrome'], rot=(0, -ang, 0), bevel=0.006))

    # fork (steers, but kept with frame for now)
    for s in (-1, 1):
        p.append(capsule('fork', (0.50, s * 0.085, 0.72), FRONT_AXLE + V((0, s * 0.085, 0)), 0.026, 0.02, F))
    p.append(box('fork_crown', (0.08, 0.22, 0.04), (0.50, 0, 0.72), F, rot=(0, math.radians(-15), 0), bevel=0.012))
    # big round headlight on the crown
    p.append(cyl('headlight_body', 0.07, 0.07, (0.57, 0, 0.80), F, rot=(0, math.pi / 2, 0), seg=32))
    p.append(cyl('headlight_lens', 0.058, 0.01, (0.607, 0, 0.80), M['light'], rot=(0, math.pi / 2, 0), seg=32))
    p.append(torus('headlight_ring', 0.064, 0.008, (0.606, 0, 0.80), M['chrome'], rot=(0, math.pi / 2, 0), segU=32, segV=8))

    # fenders (built flat around the axle, rotated into the wheel plane)
    for name, axle, arc in (('fender_f', FRONT_AXLE, (math.radians(25), math.radians(150))),
                            ('fender_r', REAR_AXLE, (math.radians(40), math.radians(195)))):
        fe = torus(name, 0.37, 0.012, mat=F, segU=40, segV=10, arc=arc, rz=0.085)
        transform_mesh(fe, ROT_X90)
        fe.location = axle
        p.append(fe)
    p.append(box('tail_light', (0.03, 0.08, 0.035), REAR_AXLE + V((-0.34, 0, 0.17)), M['tail'], rot=(0, math.radians(-55), 0), bevel=0.01))
    for s in (-1, 1):  # fender stays
        p.append(tube('stay', FRONT_AXLE + V((0, s * 0.09, 0)), FRONT_AXLE + V((0.2, s * 0.09, 0.27)), 0.006, M['chrome'], seg=6))
        p.append(tube('stay', REAR_AXLE + V((0, s * 0.09, 0)), REAR_AXLE + V((-0.26, s * 0.09, 0.22)), 0.006, M['chrome'], seg=6))

    # long banana seat + struts
    p.append(subsurf(box('seat', (0.52, 0.2, 0.07), (-0.22, 0, 0.82), M['seat'], bevel=0.03, segs=3), 1))
    p.append(box('seat_trim', (0.53, 0.205, 0.012), (-0.22, 0, 0.792), M['accent'], bevel=0.004))
    p.append(box('seat_base', (0.48, 0.16, 0.02), (-0.22, 0, 0.775), F, bevel=0.006))
    for s in (-1, 1):
        p.append(tube('seat_strut', (-0.42, s * 0.06, 0.77), REAR_AXLE + V((0.02, s * 0.085, 0.03)), 0.011, F, seg=10))
    p.append(tube('seat_post', (-0.12, 0, 0.70), (-0.13, 0, 0.78), 0.025, M['chrome'], seg=16))

    # chain (right side)
    y = -0.09
    for dz in (0.095, -0.095):
        p.append(tube('chain', BB + V((0, y, dz)), REAR_AXLE + V((0, y + 0.02, dz * 0.53)), 0.006, M['rim'], seg=6))
    return join(p, 'Bike_Frame')


def build_handlebar(M):
    p = []
    stem_b, stem_t = V((0.45, 0, 0.93)), V((0.41, 0, 1.06))
    p.append(tube('stem', stem_b, stem_t, 0.024, M['frame'], seg=16))
    p.append(box('stem_clamp', (0.06, 0.06, 0.05), stem_t, M['frame'], bevel=0.012))
    for s in (-1, 1):
        a, b, c = stem_t, V((0.39, s * 0.17, 1.075)), V((0.33, s * 0.33, 1.10))
        p.append(tube('bar', a, b, 0.014, M['chrome'], seg=12))
        p.append(tube('bar', b, c, 0.014, M['chrome'], seg=12))
        p.append(sphere('bar_joint', 0.014, b, M['chrome'], seg=12, rings=6))
        g1, g2 = c, c + V((-0.015, s * 0.11, 0.005))
        p.append(capsule('grip', g1, g2, 0.022, 0.022, M['rubber'], seg=16, rings=8))
        p.append(cyl('grip_cap', 0.024, 0.012, g2 + V((0, s * 0.01, 0)), M['accent'], rot=(math.pi / 2, 0, 0), seg=16))
        p.append(tube('lever', c + V((0.02, -s * 0.04, -0.005)), c + V((0.08, s * 0.08, -0.03)), 0.006, M['rim'], seg=6))
    p.append(box('display', (0.03, 0.08, 0.05), stem_t + V((0.0, 0, 0.04)), M['frame'], bevel=0.01, rot=(0, math.radians(-25), 0)))
    p.append(box('display_screen', (0.006, 0.065, 0.035), stem_t + V((-0.016, 0, 0.042)), M['screen'], rot=(0, math.radians(-25), 0)))
    # left mirror + bell
    m0 = V((0.36, 0.26, 1.09))
    p.append(tube('mirror_stalk', m0, m0 + V((-0.02, 0.04, 0.17)), 0.006, M['chrome'], seg=6))
    p.append(cyl('mirror', 0.04, 0.012, m0 + V((-0.02, 0.05, 0.2)), M['frame'], rot=(0, math.pi / 2, 0.3), seg=24))
    p.append(sphere('bell', 0.022, (0.37, -0.22, 1.10), M['chrome'], scale=(1, 1, 0.6)))
    return join(p, 'Bike_Handlebar')


# ================================================================ rider

# Key joints. The rider hunches forward over the bars, elbows out.
HIP = V((-0.17, 0, 0.97))
CHEST = V((-0.03, 0, 1.22))
TORSO_ANG = math.atan2(CHEST.x - HIP.x, CHEST.z - HIP.z)
FWD = V((math.cos(TORSO_ANG), 0, -math.sin(TORSO_ANG)))    # torso-local forward
AXIS = (CHEST - HIP).normalized()                          # torso-local up
HC = V((0.075, 0, 1.57))                                   # head centre
HEAD_R = 0.2
HEAD_SCALE = V((1.0, 0.92, 1.05))
HS = HEAD_R / 0.18                                          # face offsets were designed for r=0.18


def hv(x, y, z):
    """Point relative to the head centre, in head-design units."""
    return HC + V((x, y, z)) * HS


def stripes(name, p1, p2, r1, r2, outward, mat, width=0.009, spread=0.18):
    """Two white tracksuit stripes running along the outside of a limb."""
    p1, p2 = V(p1), V(p2)
    d = (p2 - p1).normalized()
    out = V(outward)
    n = (out - d * out.dot(d)).normalized()
    res = []
    for ang in ((-spread, spread) if spread else (0,)):
        nn = (Matrix.Rotation(ang, 3, d) @ n)
        res.append(tube(name, p1 + nn * (r1 * 0.97), p2 + nn * (r2 * 0.97), width, mat, seg=8))
    return res


def limb(name, a, b, ra, rb, M, outward):
    return [capsule(name, a, b, ra, rb, M['suit'])] + stripes(name + '_stripe', a, b, ra, rb, outward, M['stripe'])


def _orient_torus(o, a, b):
    d = (V(b) - V(a)).normalized()
    o.rotation_mode = 'QUATERNION'
    o.rotation_quaternion = d.to_track_quat('Z', 'X')
    return o


def _scaled(o, s):
    o.scale = s
    return o


def build_head(M):
    p = []
    sk = M['skin']
    p.append(sphere('head', HEAD_R, HC, sk, scale=HEAD_SCALE, seg=48, rings=24))
    p.append(sphere('jaw', 0.14 * HS, hv(0.03, 0, -0.085), sk, scale=(1, 1.1, 0.78)))
    p.append(sphere('cheek', 0.05 * HS, hv(0.1, 0.085, -0.035), sk))
    p.append(sphere('cheek', 0.05 * HS, hv(0.1, -0.085, -0.035), sk))
    p.append(sphere('brow_ridge', 0.05 * HS, hv(0.135, 0, 0.075), sk, scale=(0.7, 2.6, 0.6)))
    p.append(sphere('nose', 0.046 * HS, hv(0.19, 0, -0.012), sk, scale=(1.0, 0.9, 0.85)))
    p.append(sphere('nose_bridge', 0.026 * HS, hv(0.172, 0, 0.03), sk, scale=(1, 0.9, 1.6)))
    for s in (-1, 1):
        p.append(sphere('ear', 0.05 * HS, hv(-0.01, s * 0.168, -0.005), sk, scale=(0.55, 0.35, 1)))
        p.append(sphere('ear_in', 0.03 * HS, hv(-0.004, s * 0.178, -0.005), M['skin_dark'], scale=(0.5, 0.2, 0.8)))
        e = hv(0.138, s * 0.066, 0.03)
        er = 0.045 * HS
        p.append(sphere('eye', er, e, M['eye'], scale=(0.75, 1, 0.85)))
        p.append(sphere('iris', 0.024 * HS, e + V((0.029, -s * 0.004, -0.004)) * HS, M['iris'], scale=(0.45, 1, 1)))
        p.append(sphere('pupil', 0.011 * HS, e + V((0.038, -s * 0.004, -0.004)) * HS, M['pupil'], scale=(0.4, 1, 1)))
        p.append(sphere('glint', 0.004 * HS, e + V((0.041, -s * 0.0, 0.006)) * HS, M['eye']))
        # heavy upper lid, inner corner lowest => angry squint
        p.append(sphere('eyelid', er * 1.08, e + V((0.0, 0, 0.022)) * HS, sk, scale=(0.78, 1.04, 0.62),
                        rot=(s * math.radians(22), 0, 0)))
        # angry eyebrows, inner end low. The left one has the iconic shaved slit.
        bz = hv(0.168, s * 0.07, 0.083)
        rot = (s * math.radians(26), math.radians(-14), 0)
        dy = V((0, math.cos(math.radians(26)), math.sin(math.radians(26)) * s)) * s
        if s > 0:
            p.append(box('brow', (0.032 * HS, 0.05 * HS, 0.026 * HS), bz - dy * 0.018 * HS, M['brow'], rot=rot, bevel=0.009))
            p.append(box('brow', (0.032 * HS, 0.024 * HS, 0.026 * HS), bz + dy * 0.032 * HS, M['brow'], rot=rot, bevel=0.009))
        else:
            p.append(box('brow', (0.032 * HS, 0.09 * HS, 0.026 * HS), bz, M['brow'], rot=rot, bevel=0.009))
    # wide grimace with clenched teeth (two rows, dark gap between them)
    m = hv(0.158, 0, -0.092)
    p.append(sphere('mouth', 0.05 * HS, m, M['mouth'], scale=(0.4, 1.75, 0.62)))
    p.append(box('teeth_top', (0.02 * HS, 0.13 * HS, 0.02 * HS), m + V((0.008, 0, 0.0115)) * HS, M['teeth'], bevel=0.006, segs=3))
    p.append(box('teeth_bot', (0.02 * HS, 0.12 * HS, 0.018 * HS), m + V((0.007, 0, -0.0115)) * HS, M['teeth'], bevel=0.006, segs=3))
    p.append(sphere('lip_top', 0.05 * HS, m + V((0.014, 0, 0.03)) * HS, M['skin_dark'], scale=(0.3, 1.8, 0.17)))
    p.append(sphere('lip_bot', 0.05 * HS, m + V((0.012, 0, -0.03)) * HS, M['skin_dark'], scale=(0.3, 1.65, 0.19)))
    p.append(sphere('goatee', 0.035 * HS, hv(0.14, 0, -0.17), M['fade'], scale=(0.55, 1.1, 0.7)))
    p.append(capsule('neck', (0.0, 0, 1.31), (0.045, 0, 1.45), 0.07, 0.068, sk))
    o = join(p, 'Rider_Head', pivot=(0.02, 0, 1.38))
    subsurf(o, 1)
    return o


def build_hair(M):
    import bmesh
    p = []
    # skin fade: shell on the sides/back of the head, open at the face
    fade = sphere('fade', HEAD_R * 1.012, HC, M['fade'], scale=HEAD_SCALE, seg=64, rings=32)
    bm = bmesh.new()
    bm.from_mesh(fade.data)
    R = HEAD_R * 1.012
    kill = [v for v in bm.verts if v.co.z / R < -0.12 or v.co.x / R > 0.02 + max(0.0, v.co.z / R - 0.2) * 2.0]
    bmesh.ops.delete(bm, geom=kill, context='VERTS')
    bm.to_mesh(fade.data)
    bm.free()
    p.append(fade)

    # broccoli: a solid black base dome covered in curly florets, spilling over the forehead
    p.append(sphere('hair_base', HEAD_R * 0.98, hv(-0.005, 0, 0.085), M['hair'], scale=(1.02, 0.97, 0.8)))
    florets = []
    tries = 0
    while len(florets) < 230 and tries < 10000:
        tries += 1
        d = V((random.uniform(-1, 1), random.uniform(-1, 1), random.uniform(-1, 1)))
        if not 0.2 < d.length <= 1:
            continue
        d.normalize()
        if d.z < (0.38 if d.x > 0.4 else 0.12):
            continue
        base = hv(-0.005, 0, 0.085) + V((d.x * 1.0, d.y * 0.95, d.z * 0.8)) * HEAD_R * 0.98
        pos = base + d * random.uniform(0.005, 0.022) + V((0, 0, 0.02 * d.z))
        r = random.uniform(0.026, 0.044) * (0.6 + 0.4 * min(1.0, d.z / 0.45))  # smaller curls low on the sides
        florets.append(ico('floret', r, pos, M['hair'], scale=(1, 1, random.uniform(0.8, 1.05)), subdiv=2))
    top = join(florets, 'florets_tmp')
    p.append(top)
    return join(p, 'Rider_Hair', pivot=HC)


def build_sunglasses(M):
    p = []
    for s in (-1, 1):
        c = hv(0.188, s * 0.066, 0.035)
        p.append(box('lens', (0.012 * HS, 0.078 * HS, 0.048 * HS), c, M['lens'], bevel=0.012, segs=3, rot=(0, 0, -s * 0.15)))
        p.append(box('rim', (0.012 * HS, 0.085 * HS, 0.013 * HS), c + V((0.002, 0, 0.026)) * HS, M['shades'], bevel=0.004,
                     rot=(0, 0, -s * 0.15)))
        p.append(tube('arm', c + V((-0.01, s * 0.04, 0.02)) * HS, hv(0.0, s * 0.158, 0.035), 0.005, M['shades'], seg=6))
    p.append(box('bridge', (0.012 * HS, 0.04 * HS, 0.008 * HS), hv(0.195, 0, 0.05), M['shades'], bevel=0.003))
    return join(p, 'Rider_Sunglasses', pivot=HC)


def build_torso(M):
    p = []
    rb, rc, sxy = 0.16, 0.19, (0.85, 1.2)
    p.append(capsule('torso', HIP, CHEST, rb, rc, M['suit'], sxy=sxy, seg=32, rings=16, rot_y_only=True))
    p.append(sphere('pelvis', 0.15, (-0.19, 0, 0.93), M['suit'], scale=(1.0, 1.15, 0.72)))
    # zipper + pull
    z1 = HIP + FWD * rb * sxy[0] - AXIS * 0.06
    z2 = CHEST + FWD * rc * sxy[0] + AXIS * 0.07
    p.append(tube('zip', z1, z2, 0.005, M['chrome'], seg=6))
    p.append(box('zip_pull', (0.006, 0.014, 0.03), CHEST + FWD * (rc * sxy[0] + 0.005) + AXIS * 0.03, M['chrome'],
                 rot=(0, TORSO_ANG, 0), bevel=0.003))
    # collar and waistband
    neck_base = CHEST + AXIS * 0.15
    p.append(torus('collar', 0.088, 0.034, neck_base, M['suit'], rot=(0, TORSO_ANG + 0.3, 0), segU=32, segV=10))
    p.append(torus('collar_stripe', 0.1, 0.005, neck_base + AXIS * 0.02, M['stripe'], rot=(0, TORSO_ANG + 0.3, 0), segU=32, segV=6))
    # stripes down the sides of the jacket
    for s in (-1, 1):
        side_a = HIP - AXIS * 0.04 + V((0, s * rb * sxy[1], 0))
        side_b = CHEST + AXIS * 0.05 + V((0, s * rc * sxy[1] * 0.95, 0))
        p += stripes('side_stripe', side_a, side_b, 0.0, 0.0, (0, s, 0), M['stripe'], width=0.011, spread=0)
    # chunky gold chain + pendant
    links = []
    n = 46
    for i in range(n):
        a = 2 * math.pi * i / n
        links.append(torus('link', 0.009, 0.0028, (math.cos(a) * 0.105, math.sin(a) * 0.112, 0), M['gold'], segU=10, segV=5,
                           rot=(math.pi / 2 if i % 2 else 0, 0, a + math.pi / 2)))
    chain = join(links, 'chain_tmp')
    chain.location = neck_base + FWD * 0.02 - AXIS * 0.02
    chain.rotation_euler = (0, TORSO_ANG + 0.55, 0)
    p.append(chain)
    bpy.context.view_layer.update()
    front = chain.matrix_world @ V((0.105, 0, 0))
    p.append(sphere('pendant', 0.024, front + FWD * 0.008 - AXIS * 0.025, M['gold'], scale=(0.35, 1, 1.15), rot=(0, TORSO_ANG, 0)))
    return join(p, 'Rider_Torso', pivot=HIP)


def build_arm(M, s):
    side = 'L' if s > 0 else 'R'
    sh = V((-0.005, s * 0.215, 1.30))
    el = V((0.14, s * 0.37, 1.15))
    wr = V((0.295, s * 0.355, 1.115))
    grip = V((0.33, s * 0.35, 1.105))
    p = [sphere('shoulder', 0.078, sh, M['suit'])]
    p += limb('upper', sh, el, 0.072, 0.06, M, (0, s, 0.5))
    p.append(sphere('elbow', 0.06, el, M['suit']))
    p += limb('fore', el, wr, 0.06, 0.05, M, (0, s, 0.7))
    p.append(_orient_torus(torus('cuff', 0.047, 0.013, wr, M['suit'], segU=24, segV=6), el, wr))
    p.append(sphere('fist', 0.05, grip + V((-0.005, 0, 0.012)), M['skin'], scale=(1.15, 0.95, 0.9)))
    for i in range(4):
        p.append(sphere('knuckle', 0.017, grip + V((0.035, s * (-0.03 + i * 0.02), 0.02)), M['skin']))
    p.append(sphere('thumb', 0.018, grip + V((0.02, -s * 0.045, 0.04)), M['skin'], scale=(1.4, 1, 1)))
    return join(p, f'Rider_Arm{side}', pivot=sh)


def build_leg(M, s):
    side = 'L' if s > 0 else 'R'
    hip = V((-0.17, s * 0.11, 0.93))
    if s < 0:   # right foot forward on the pedal
        knee, ankle = V((0.17, s * 0.19, 0.80)), V((0.155, s * 0.15, 0.40))
    else:       # left foot back
        knee, ankle = V((0.02, s * 0.2, 0.72)), V((-0.165, s * 0.15, 0.39))
    p = []
    p += limb('thigh', hip, knee, 0.09, 0.074, M, (0, s, 0.2))
    p.append(sphere('knee', 0.074, knee, M['suit']))
    p += limb('shin', knee, ankle, 0.072, 0.06, M, (0, s, 0))
    p.append(_orient_torus(torus('cuff', 0.062, 0.016, ankle, M['suit'], segU=24, segV=6), knee, ankle))
    shoe_c = ankle + V((0.04, 0, -0.045))
    p.append(subsurf(box('shoe', (0.24, 0.1, 0.085), shoe_c, M['sneaker'], bevel=0.03, segs=2), 1))
    p.append(box('sole', (0.25, 0.108, 0.03), shoe_c + V((0.0, 0, -0.045)), M['sole'], bevel=0.01))
    p.append(box('shoe_stripe', (0.12, 0.103, 0.012), shoe_c + V((-0.01, 0, 0.005)), M['suit'], bevel=0.004))
    p.append(sphere('toe', 0.05, shoe_c + V((0.1, 0, -0.005)), M['sneaker'], scale=(0.8, 1.0, 0.75)))
    for i in range(3):
        p.append(box('lace', (0.012, 0.06, 0.008), shoe_c + V((0.02 + i * 0.03, 0, 0.045)), M['stripe'], bevel=0.003))
    return join(p, f'Rider_Leg{side}', pivot=hip)


def build_knife(M):
    """Full knife (thrown in-game), tucked blade-down in the waistband."""
    p = []
    blade = lib.extrude_profile('blade', [(0.0, -0.014), (0.12, -0.016), (0.175, 0.0), (0.13, 0.014), (0.0, 0.015)],
                                0.005, M['steel'])
    blade.modifiers.new('bevel', 'BEVEL').width = 0.002
    p.append(blade)
    p.append(box('guard', (0.012, 0.03, 0.05), (-0.006, 0, 0), M['steel'], bevel=0.003))
    p.append(capsule('grip', (-0.012, 0, 0), (-0.11, 0, 0), 0.015, 0.016, M['knife_grip'], sxy=(1, 0.75)))
    p.append(sphere('pommel', 0.017, (-0.115, 0, 0), M['steel'], scale=(0.6, 0.8, 1)))
    k = join(p, 'Rider_Knife')
    k.location = HIP + FWD * 0.125 + V((0, -0.12, 0)) + AXIS * 0.02
    k.rotation_euler = (0, math.pi / 2 + TORSO_ANG, math.radians(-8))
    return k


# ================================================================ assemble

def build():
    lib.reset_scene()
    M = mats()
    root = lib.empty('Fatbiker')
    bike = lib.empty('Bike', parent=root)
    rider = lib.empty('Rider', parent=root)

    frame = build_frame(M)
    bar = build_handlebar(M)
    wf = build_wheel('Bike_WheelFront', M)
    wf.location = FRONT_AXLE
    wr = build_wheel('Bike_WheelRear', M, rear=True)
    wr.location = REAR_AXLE
    crank = build_crank(M)
    for o in (frame, bar, wf, wr, crank):
        lib.set_parent(o, bike)

    parts = [build_torso(M), build_head(M), build_hair(M), build_sunglasses(M), build_knife(M),
             build_arm(M, 1), build_arm(M, -1), build_leg(M, 1), build_leg(M, -1)]
    for o in parts:
        lib.set_parent(o, rider)
    return root


def main():
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    root = build()
    scene = bpy.context.scene
    model_objs = [root] + list(root.children_recursive)
    meshes = [o for o in model_objs if o.type == 'MESH']
    print(f'[fatbiker] parts: {sorted(o.name for o in meshes)}')
    print(f'[fatbiker] triangles: {lib.tri_count(meshes)}')

    out = os.path.join(ROOT, 'assets', 'models', 'fatbiker.glb')
    lib.export_glb(out, model_objs)
    print(f'[fatbiker] exported {out}')

    if '--no-render' in argv:
        return
    lib.preview_stage(scene)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ROOT, 'blender', 'fatbiker.blend'))
    rdir = os.path.join(ROOT, 'renders', 'fatbiker')
    shades = bpy.data.objects['Rider_Sunglasses']
    shots = [
        ('01_hero', (2.4, -2.0, 1.35), (0.0, 0, 0.85), 45, False),
        ('02_side', (0.0, -3.6, 0.95), (0.0, 0, 0.75), 45, False),
        ('03_face', tuple(HC + V((1.1, -0.6, 0.05))), tuple(HC - V((0, 0, 0.04))), 85, False),
        ('04_rear', (-2.3, 1.9, 1.5), (0.0, 0, 0.8), 45, False),
        ('05_shades', tuple(HC + V((1.2, -0.8, 0.0))), tuple(HC - V((0, 0, 0.1))), 60, True),
    ]
    for name, loc, tgt, lens, show_shades in shots:
        shades.hide_render = not show_shades
        render(scene, lib.camera('Cam_' + name, loc, tgt, lens), os.path.join(rdir, name + '.png'))


def render(scene, cam, path):
    lib.render(scene, cam, path)


if __name__ == '__main__':
    main()
