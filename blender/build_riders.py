"""A mixed crowd of fatbikers: men and women, teens to grandparents, different hair, headwear and clothes.

Exports `assets/models/riders.glb` containing:
- `Bike`           the fatbike (shared by everyone)
- `Bike_Basket`    optional front basket (grandma's)
- `Rider_<id>`     one rider per variant, with the same part names the game expects
                   (Rider_Head, Rider_Hair, Rider_Torso, Rider_ArmL/R, Rider_LegL/R, Rider_Knife, Rider_Sunglasses)
                   and variant metadata as glTF extras (sex, age, top, bottom, hairGroup, basket).

Colours for skin, hair, clothes, caps and shoes are randomised in-game per rider (material names
Skin/SkinShade/Hair/Brow/Top/TopTrim/Bottom/BottomTrim/Cap/Shoe), so a few shapes give a very varied crowd.

Run:  Blender -b -P blender/build_riders.py [-- --no-render]
"""
import math
import os
import random
import sys

import bmesh
import bpy
from mathutils import Vector

sys.path.insert(0, os.path.dirname(__file__))
import lib  # noqa: E402
import build_fatbiker as fb  # noqa: E402  (bike + shared rider geometry)
from lib import box, capsule, cyl, ico, join, material, sphere, subsurf, torus, tube  # noqa: E402
from build_fatbiker import (AXIS, CHEST, FWD, HC, HEAD_R, HEAD_SCALE, HIP, HS, TORSO_ANG,  # noqa: E402
                            _orient_torus, _scaled, hv, stripes)

ROOT = fb.ROOT
V = Vector

# ------------------------------------------------------------------------------------------- variants
VARIANTS = [
    dict(id='V01', sex='m', age='adult', hair='broccoli', top='tracksuit', bottom='trackpants', facial='goatee', chain=True),
    dict(id='V02', sex='m', age='adult', hair='short', cap='back', top='tshirt', bottom='shorts', facial='stubble'),
    dict(id='V03', sex='m', age='teen', hair='buzz', headphones=True, top='tank', bottom='shorts', shoes='color', braces=True),
    dict(id='V04', sex='m', age='adult', hair='bald', top='tank', bottom='jeans', facial='beard', build='big'),
    dict(id='V05', sex='m', age='senior', hair='horseshoe', cap='flat', glasses=True, facial='moustache', top='polo',
         bottom='shorts', shoes='sandals', build='belly'),
    dict(id='V06', sex='f', age='teen', hair='ponytail', top='tshirt', bottom='shorts', shoes='color', braces=True, earrings=True),
    dict(id='V07', sex='f', age='adult', hair='long', top='tank', bottom='jeans', earrings=True),
    dict(id='V08', sex='f', age='adult', hair='bun', top='tracksuit', bottom='trackpants', earrings=True),
    dict(id='V09', sex='f', age='senior', hair='perm', glasses=True, top='cardigan', bottom='skirt', shoes='granny', basket=True),
    dict(id='V10', sex='f', age='adult', hair='bob', cap='front', top='tshirt', bottom='leggings'),
    dict(id='V11', sex='m', age='adult', hair='manbun', facial='beard', top='tshirt', bottom='shorts'),
    dict(id='V12', sex='f', age='teen', hair='pigtails', headphones=True, top='tracksuit', bottom='leggings', shoes='color'),
]

HAIR_GROUP = {'senior': 'grey', 'teen': 'young', 'adult': 'young'}


def mats():
    base = fb.mats()
    base.update({
        # recoloured in-game
        'skin': material('Skin', '#c98d62', rough=0.55, sss=0.08),
        'skin_dark': material('SkinShade', '#a8694a', rough=0.6),
        'hair': material('Hair', '#3a2a20', rough=0.75),
        'brow': material('Brow', '#2a1d16', rough=0.8),
        'top': material('Top', '#2b5a8c', rough=0.7),
        'trim': material('TopTrim', '#f4f4f4', rough=0.5),
        'bottom': material('Bottom', '#2b4a7a', rough=0.75),
        'btrim': material('BottomTrim', '#f4f4f4', rough=0.5),
        'cap': material('Cap', '#c8302a', rough=0.6),
        'shoe': material('Shoe', '#f7f7f5', rough=0.45),
        # fixed
        'lips': material('Lips', '#b8505e', rough=0.35),
        'sock': material('Sock', '#f2f0ea', rough=0.85),
        'leather': material('ShoeLeather', '#6b4429', rough=0.5),
        'glasses': material('GlassesFrame', '#3a2a1e', rough=0.3, coat=0.5),
        'phones': material('Headphones', '#1c1c1f', rough=0.35),
        'phones_pad': material('HeadphonePad', '#e23b6b', rough=0.6),
        'braces': material('Braces', '#b8bec8', rough=0.2, metal=1.0),
        'button': material('Button', '#f2ead8', rough=0.4),
        'wicker': material('Wicker', '#b8874f', rough=0.8),
        'bread': material('Baguette', '#d9a25a', rough=0.7),
        'leaf': material('BasketLeaf', '#4f8a2c', rough=0.7),
        'flower': material('BasketFlower', '#ff5a8a', rough=0.6),
    })
    return base


# ------------------------------------------------------------------------------------------- helpers

def shell(name, mat, keep, k=1.02, center=None, scale=None, seg=48, rings=24):
    """A cut-out spherical shell around the head (hair caps, bobs, ...). keep(x, y, z) uses unit coords."""
    c = center or HC
    o = sphere(name, HEAD_R * k, c, mat, scale=scale or HEAD_SCALE, seg=seg, rings=rings)
    bm = bmesh.new()
    bm.from_mesh(o.data)
    R = HEAD_R * k
    kill = [v for v in bm.verts if not keep(v.co.x / R, v.co.y / R, v.co.z / R)]
    bmesh.ops.delete(bm, geom=kill, context='VERTS')
    bm.to_mesh(o.data)
    bm.free()
    return o


def no_ears(x, y, z):
    return not (abs(x) < 0.25 and abs(y) > 0.75 and -0.35 < z < 0.25)


def florets(mat, n, keep, r=(0.03, 0.045), subdiv=2, lift=0.0, spread=1.0):
    out = []
    tries = 0
    while len(out) < n and tries < 20000:
        tries += 1
        d = V((random.uniform(-1, 1), random.uniform(-1, 1), random.uniform(-1, 1)))
        if not 0.2 < d.length <= 1:
            continue
        d.normalize()
        if not keep(d):
            continue
        base = hv(-0.005, 0, 0.06 + lift) + V((d.x, d.y * 0.95, d.z * 0.85)) * HEAD_R * spread
        pos = base + d * random.uniform(0.0, 0.015)
        out.append(ico('curl', random.uniform(*r), pos, mat, subdiv=subdiv))
    return join(out, 'curls_tmp')


# ------------------------------------------------------------------------------------------- head

def build_head(M, v):
    female, age = v['sex'] == 'f', v['age']
    sk, sd = M['skin'], M['skin_dark']
    p = [sphere('head', HEAD_R, HC, sk, scale=HEAD_SCALE * (0.97 if female else 1), seg=48, rings=24)]
    jaw = (0.93, 1.0, 0.72) if female else (1.0, 1.1, 0.78)
    if v.get('build') == 'big':
        jaw = (1.08, 1.22, 0.85)
    p.append(sphere('jaw', 0.14 * HS, hv(0.03, 0, -0.085), sk, scale=jaw))
    for s in (-1, 1):
        p.append(sphere('cheek', 0.05 * HS, hv(0.1, s * 0.085, -0.035), sk))
    p.append(sphere('brow_ridge', 0.05 * HS, hv(0.135, 0, 0.075), sk, scale=(0.7, 2.6, 0.6)))
    nose = 0.04 if female else (0.05 if age == 'senior' else 0.046)
    p.append(sphere('nose', nose * HS, hv(0.19, 0, -0.012), sk, scale=(1.0, 0.9, 0.85)))
    p.append(sphere('nose_bridge', 0.026 * HS, hv(0.172, 0, 0.03), sk, scale=(1, 0.9, 1.6)))
    for s in (-1, 1):
        p.append(sphere('ear', 0.05 * HS, hv(-0.01, s * 0.168, -0.005), sk, scale=(0.55, 0.35, 1.1 if age == 'senior' else 1)))
        p.append(sphere('ear_in', 0.03 * HS, hv(-0.004, s * 0.178, -0.005), sd, scale=(0.5, 0.2, 0.8)))
        if v.get('earrings'):
            p.append(torus('earring', 0.018 * HS, 0.003 * HS, hv(0.0, s * 0.176, -0.075), M['gold'], rot=(math.pi / 2, 0, 0), segU=16, segV=6))
        e = hv(0.138, s * 0.066, 0.03)
        er = (0.05 if age == 'teen' else 0.045) * HS
        p.append(sphere('eye', er, e, M['eye'], scale=(0.75, 1, 0.85)))
        p.append(sphere('iris', 0.024 * HS, e + V((0.029, -s * 0.004, -0.004)) * HS, M['iris'], scale=(0.45, 1, 1)))
        p.append(sphere('pupil', 0.011 * HS, e + V((0.038, -s * 0.004, -0.004)) * HS, M['pupil'], scale=(0.4, 1, 1)))
        p.append(sphere('glint', 0.004 * HS, e + V((0.041, 0, 0.006)) * HS, M['eye']))
        p.append(sphere('eyelid', er * 1.08, e + V((0.0, 0, 0.022)) * HS, sk, scale=(0.78, 1.04, 0.62), rot=(s * math.radians(22), 0, 0)))
        if female:  # lashes on the outer upper lid
            for k in range(3):
                a = e + V((0.03, s * (0.012 + k * 0.012), 0.024 - k * 0.003)) * HS
                p.append(tube('lash', a, a + V((0.012, s * 0.012, 0.012)) * HS, 0.0028 * HS, M['pupil'], seg=5))
        if age == 'senior':  # bags under the eyes
            p.append(sphere('eyebag', 0.03 * HS, e + V((0.01, 0, -0.035)) * HS, sd, scale=(0.5, 1.2, 0.4)))
        # angry eyebrows (thinner for women)
        bz = hv(0.168, s * 0.07, 0.083)
        rot = (s * math.radians(22 if female else 26), math.radians(-14), 0)
        th = 0.016 if female else 0.026
        p.append(box('brow', (0.03 * HS, 0.085 * HS, th * HS), bz, M['brow'], rot=rot, bevel=0.006))
    # snarl
    m = hv(0.158, 0, -0.092)
    p.append(sphere('mouth', 0.05 * HS, m, M['mouth'], scale=(0.4, 1.75 if not female else 1.55, 0.62)))
    p.append(box('teeth_top', (0.02 * HS, 0.13 * HS, 0.02 * HS), m + V((0.008, 0, 0.0115)) * HS, M['teeth'], bevel=0.006, segs=3))
    p.append(box('teeth_bot', (0.02 * HS, 0.12 * HS, 0.018 * HS), m + V((0.007, 0, -0.0115)) * HS, M['teeth'], bevel=0.006, segs=3))
    if v.get('braces'):
        p.append(box('braces', (0.006 * HS, 0.125 * HS, 0.005 * HS), m + V((0.019, 0, 0.012)) * HS, M['braces'], bevel=0.002))
    lip = M['lips'] if female else sd
    p.append(sphere('lip_top', 0.05 * HS, m + V((0.014, 0, 0.03)) * HS, lip, scale=(0.3, 1.7, 0.2 if female else 0.17)))
    p.append(sphere('lip_bot', 0.05 * HS, m + V((0.012, 0, -0.03)) * HS, lip, scale=(0.3, 1.55, 0.24 if female else 0.19)))
    if age == 'senior':  # smile lines
        for s in (-1, 1):
            p.append(tube('fold', hv(0.17, s * 0.05, -0.03), hv(0.16, s * 0.085, -0.11), 0.004 * HS, sd, seg=5))
    facial = v.get('facial')
    if facial == 'goatee':
        p.append(sphere('goatee', 0.035 * HS, hv(0.14, 0, -0.17), M['hair'], scale=(0.55, 1.1, 0.7)))
    elif facial == 'stubble':
        p.append(sphere('stubble', 0.13 * HS, hv(0.045, 0, -0.1), M['skin_dark'], scale=(1.02, 1.12, 0.76)))
    elif facial == 'beard':
        # a shell hugging the jaw from ear to ear, open around the mouth
        jc, jr = hv(0.03, 0, -0.085), 0.14 * HS * 1.07
        beard = sphere('beard', jr, jc, M['hair'], scale=(jaw[0] * 1.02, jaw[1] * 1.02, jaw[2] * 1.05), seg=40, rings=20)
        bm = bmesh.new()
        bm.from_mesh(beard.data)
        kill = [q for q in bm.verts if q.co.z / jr > 0.15 or q.co.x / jr < -0.35
                or (q.co.x / jr > 0.55 and q.co.z / jr > -0.45 and abs(q.co.y / jr) < 0.55)]
        bmesh.ops.delete(bm, geom=kill, context='VERTS')
        bm.to_mesh(beard.data)
        bm.free()
        p.append(beard)
        p.append(capsule('moustache', hv(0.18, -0.06, -0.06), hv(0.18, 0.06, -0.06), 0.016 * HS, 0.016 * HS, M['hair']))
    elif facial == 'moustache':
        for s in (-1, 1):
            p.append(capsule('moustache', hv(0.185, 0, -0.058), hv(0.17, s * 0.075, -0.075), 0.022 * HS, 0.012 * HS, M['hair']))
    if v.get('glasses'):
        for s in (-1, 1):
            p.append(torus('lens_rim', 0.038 * HS, 0.005 * HS, hv(0.19, s * 0.066, 0.03), M['glasses'], rot=(0, math.pi / 2, 0), segU=24, segV=6))
            p.append(tube('temple', hv(0.185, s * 0.1, 0.035), hv(0.0, s * 0.158, 0.035), 0.004 * HS, M['glasses'], seg=6))
        p.append(tube('bridge', hv(0.195, -0.028, 0.035), hv(0.195, 0.028, 0.035), 0.004 * HS, M['glasses'], seg=6))
    neck_r = 0.06 if female else (0.08 if v.get('build') == 'big' else 0.07)
    p.append(capsule('neck', (0.0, 0, 1.31), (0.045, 0, 1.45), neck_r, neck_r * 0.97, sk))
    o = join(p, 'Rider_Head', pivot=(0.02, 0, 1.38))
    subsurf(o, 1)
    return o


# ------------------------------------------------------------------------------------------- hair & headwear

def build_hair(M, v):
    random.seed(hash(v['id']) & 0xffff)
    style, H = v['hair'], M['hair']
    p = []
    if style == 'broccoli':
        fade = shell('fade', M['fade'], lambda x, y, z: z > -0.12 and x < 0.02 + max(0.0, z - 0.2) * 2.0, k=1.012)
        p.append(fade)
        p.append(sphere('hair_base', HEAD_R * 0.98, hv(-0.005, 0, 0.085), H, scale=(1.02, 0.97, 0.8)))
        p.append(florets(H, 230, lambda d: d.z >= (0.38 if d.x > 0.4 else 0.12), r=(0.026, 0.044), lift=0.025))
    elif style in ('short', 'buzz', 'long', 'ponytail', 'bun', 'manbun', 'pigtails'):
        k = 1.01 if style == 'buzz' else 1.03
        hairline = 0.5 if style != 'buzz' else 0.58
        p.append(shell('cap_hair', H, lambda x, y, z: z > -0.2 and (x < 0.3 or z > hairline) and no_ears(x, y, z), k=k))
        if style == 'long':
            p.append(sphere('back', 0.17 * HS, hv(-0.11, 0, -0.14), H, scale=(0.55, 1.0, 1.6)))
            for s in (-1, 1):
                p.append(sphere('lock', 0.07 * HS, hv(-0.03, s * 0.155, -0.11), H, scale=(0.75, 0.45, 1.7)))
            p.append(sphere('bangs', 0.08 * HS, hv(0.12, 0.05, 0.13), H, scale=(0.6, 1.3, 0.45), rot=(0.35, 0, 0)))
        elif style == 'ponytail':
            p.append(torus('tie', 0.035 * HS, 0.012 * HS, hv(-0.18, 0, 0.06), M['cap'], rot=(0, math.pi / 2, 0), segU=16, segV=6))
            for k2, (x, z, r) in enumerate(((-0.23, 0.02, 0.055), (-0.27, -0.06, 0.05), (-0.29, -0.15, 0.04))):
                p.append(sphere('tail', r * HS, hv(x, 0, z), H, scale=(0.9, 0.9, 1.45)))
        elif style == 'bun':
            p.append(sphere('bun', 0.075 * HS, hv(-0.07, 0, 0.215), H))
            p.append(torus('bun_tie', 0.05 * HS, 0.01 * HS, hv(-0.06, 0, 0.18), M['cap'], segU=16, segV=6))
        elif style == 'manbun':
            p.append(sphere('bun', 0.06 * HS, hv(-0.16, 0, 0.13), H))
        elif style == 'pigtails':
            for s in (-1, 1):
                start = hv(-0.06, s * 0.16, 0.0)
                p.append(torus('tie', 0.028 * HS, 0.009 * HS, start, M['cap'], rot=(math.pi / 2, 0, 0), segU=12, segV=6))
                step = V((-0.015, s * 0.025, -0.07)) * HS
                for k2 in range(5):
                    p.append(sphere('braid', (0.036 - k2 * 0.004) * HS, start + step * (k2 + 0.6), H))
                p.append(sphere('tuft', 0.03 * HS, start + step * 5.6, H, scale=(1, 1, 1.4)))
    elif style == 'bob':
        p.append(shell('bob', H, lambda x, y, z: z > -0.62 and not (x > 0.22 and z < 0.45), k=1.08,
                       center=hv(-0.01, 0, -0.01), scale=(1.02, 1.05, 1.06)))
    elif style == 'horseshoe':
        p.append(shell('horseshoe', H, lambda x, y, z: -0.25 < z < 0.3 and x < 0.15 and no_ears(x, y, z), k=1.02))
    elif style == 'perm':
        p.append(sphere('perm_base', HEAD_R * 0.97, hv(-0.01, 0, 0.06), H, scale=(1.03, 1.0, 0.85)))
        p.append(florets(H, 160, lambda d: d.z > -0.25 and not (d.x > 0.45 and d.z < 0.55) and not (abs(d.y) > 0.8 and d.z < 0.2 and abs(d.x) < 0.3),
                         r=(0.032, 0.045), subdiv=1, spread=1.02))
    # bald: no hair object at all (nothing flies off but the dignity)

    cap = v.get('cap')
    if cap in ('back', 'front'):
        dome = shell('cap_dome', M['cap'], lambda x, y, z: z > 0.05, k=1.07, center=hv(-0.005, 0, 0.03), scale=(1.04, 1.0, 0.85))
        p.append(dome)
        sgn = 1 if cap == 'front' else -1
        brim = cyl('brim', 0.105 * HS, 0.012, hv(sgn * 0.21, 0, 0.075), M['cap'], seg=32, rot=(0, sgn * math.radians(8), 0))
        brim.scale = (1.0, 1.15, 1)
        p.append(brim)
        p.append(sphere('cap_button', 0.014 * HS, hv(-0.005, 0, 0.23), M['cap']))
        p.append(torus('cap_band', HEAD_R * 1.03, 0.006, hv(-0.005, 0, 0.065), M['trim'], segU=40, segV=6))
    elif cap == 'flat':
        dome = shell('flatcap', M['cap'], lambda x, y, z: z > 0.0, k=1.08, center=hv(0.02, 0, 0.09), scale=(1.15, 1.04, 0.55))
        p.append(dome)
        p.append(box('flat_brim', (0.07 * HS, 0.19 * HS, 0.012), hv(0.21, 0, 0.1), M['cap'], rot=(0, math.radians(12), 0), bevel=0.006))
    if v.get('headphones'):
        band = torus('phones_band', HEAD_R * 1.1, 0.012, HC + V((0, 0, 0.005)), M['phones'], segU=32, segV=8,
                     arc=(0, math.pi), rot=(math.pi / 2, 0, math.pi / 2))
        band.scale = (1, 0.95, 1.05)
        p.append(band)
        for s in (-1, 1):
            p.append(cyl('cup', 0.058 * HS, 0.045, hv(-0.01, s * 0.185, -0.005), M['phones'], rot=(math.pi / 2, 0, 0), seg=24))
            p.append(cyl('pad', 0.045 * HS, 0.02, hv(-0.01, s * 0.212, -0.005), M['phones_pad'], rot=(math.pi / 2, 0, 0), seg=24))
    if not p:
        return None
    return join(p, 'Rider_Hair', pivot=HC)


# ------------------------------------------------------------------------------------------- body

def build_torso(M, v):
    female = v['sex'] == 'f'
    top = v['top']
    T, TR = M['top'], M['trim']
    rb, rc = (0.155, 0.175) if female else (0.16, 0.19)
    sxy = (0.85, 1.08) if female else (0.85, 1.2)
    if v.get('build') == 'big':
        rb, rc, sxy = 0.18, 0.21, (0.9, 1.25)
    p = [capsule('torso', HIP, CHEST, rb, rc, T, sxy=sxy, seg=32, rings=16, rot_y_only=True)]
    p.append(sphere('pelvis', 0.15, (-0.19, 0, 0.93), M['bottom'], scale=(1.0, 1.25 if female else 1.15, 0.72)))
    neck_base = CHEST + AXIS * 0.15
    if female:  # modest cartoon bust
        for s in (-1, 1):
            p.append(sphere('bust', 0.058, CHEST + FWD * 0.105 - AXIS * 0.03 + V((0, s * 0.068, 0)), T, scale=(0.6, 1.1, 0.85), rot=(0, TORSO_ANG, 0)))
    if v.get('build') == 'belly':
        p.append(sphere('belly', 0.19, HIP + FWD * 0.09 + AXIS * 0.08, T, scale=(1.0, 1.15, 1.0)))
    if top == 'tracksuit':
        z1 = HIP + FWD * rb * sxy[0] - AXIS * 0.06
        z2 = CHEST + FWD * rc * sxy[0] + AXIS * 0.07
        p.append(tube('zip', z1, z2, 0.005, M['chrome'], seg=6))
        p.append(torus('collar', 0.088, 0.034, neck_base, T, rot=(0, TORSO_ANG + 0.3, 0), segU=32, segV=10))
        p.append(torus('collar_stripe', 0.1, 0.005, neck_base + AXIS * 0.02, TR, rot=(0, TORSO_ANG + 0.3, 0), segU=32, segV=6))
        for s in (-1, 1):
            a = HIP - AXIS * 0.04 + V((0, s * rb * sxy[1], 0))
            b = CHEST + AXIS * 0.05 + V((0, s * rc * sxy[1] * 0.95, 0))
            p += stripes('side_stripe', a, b, 0.0, 0.0, (0, s, 0), TR, width=0.011, spread=0)
    elif top in ('tshirt', 'tank'):
        p.append(torus('neckline', 0.08, 0.014, neck_base - AXIS * 0.01, T, rot=(0, TORSO_ANG + 0.3, 0), segU=32, segV=8))
        if top == 'tank':
            p.append(sphere('decollete', 0.06, neck_base + FWD * 0.085 - AXIS * 0.06, M['skin'], scale=(0.45, 1.5, 1.0), rot=(0, TORSO_ANG, 0)))
        else:  # a little chest print
            p.append(cyl('print', 0.05, 0.01, CHEST + FWD * (rc * sxy[0] + 0.004) + AXIS * 0.0, TR, rot=(0, math.pi / 2 + TORSO_ANG, 0), seg=5))
    elif top == 'polo':
        for s in (-1, 1):
            p.append(box('collar_flap', (0.07, 0.07, 0.012), neck_base + FWD * 0.06 + V((0, s * 0.045, 0)), TR,
                         rot=(s * 0.5, TORSO_ANG - 0.9, 0), bevel=0.004))
        for k in range(3):
            p.append(sphere('button', 0.008, neck_base + FWD * (0.085 + k * 0.004) - AXIS * (0.04 + k * 0.035), M['button']))
    elif top == 'cardigan':
        p.append(box('blouse', (0.03, 0.09, 0.3), CHEST + FWD * (rc * sxy[0] - 0.006) - AXIS * 0.05, TR, rot=(0, TORSO_ANG, 0), bevel=0.01))
        for k in range(4):
            p.append(sphere('button', 0.01, CHEST + FWD * (rc * sxy[0] + 0.01) - AXIS * (0.12 - k * 0.07) + V((0, 0.05, 0)), M['button']))
        p.append(torus('collar', 0.085, 0.022, neck_base, T, rot=(0, TORSO_ANG + 0.3, 0), segU=32, segV=8))
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
    if v['bottom'] == 'skirt':
        p.append(sphere('skirt', 0.26, (-0.06, 0, 0.88), M['bottom'], scale=(1.25, 1.05, 0.48)))
        p.append(_scaled(torus('hem', 0.24, 0.014, (-0.04, 0, 0.83), M['bottom'], segU=40, segV=6), (1.25, 1.05, 1)))
    return join(p, 'Rider_Torso', pivot=HIP)


def build_arm(M, v, s):
    side = 'L' if s > 0 else 'R'
    female = v['sex'] == 'f'
    k = 0.87 if female else (1.12 if v.get('build') == 'big' else 1.0)
    top = v['top']
    sleeve = {'tracksuit': 'long', 'cardigan': 'long', 'tshirt': 'short', 'polo': 'short', 'tank': 'none'}[top]
    sh = V((-0.005, s * (0.2 if female else 0.215), 1.30))
    el = V((0.14, s * 0.37, 1.15))
    wr = V((0.295, s * 0.355, 1.115))
    grip = V((0.33, s * 0.35, 1.105))
    T, SK = M['top'], M['skin']
    p = []
    if sleeve == 'long':
        p.append(sphere('shoulder', 0.078 * k, sh, T))
        p.append(capsule('upper', sh, el, 0.072 * k, 0.06 * k, T))
        p.append(sphere('elbow', 0.06 * k, el, T))
        p.append(capsule('fore', el, wr, 0.06 * k, 0.05 * k, T))
        p.append(_orient_torus(torus('cuff', 0.047 * k, 0.013, wr, T, segU=24, segV=6), el, wr))
        if top == 'tracksuit':
            p += stripes('upper_stripe', sh, el, 0.072 * k, 0.06 * k, (0, s, 0.5), M['trim'])
            p += stripes('fore_stripe', el, wr, 0.06 * k, 0.05 * k, (0, s, 0.7), M['trim'])
    else:
        p.append(sphere('shoulder', 0.07 * k, sh, T if sleeve == 'short' else SK))
        p.append(capsule('upper', sh, el, 0.064 * k, 0.052 * k, SK))
        p.append(sphere('elbow', 0.052 * k, el, SK))
        p.append(capsule('fore', el, wr, 0.052 * k, 0.04 * k, SK))
        if sleeve == 'short':
            mid = sh.lerp(el, 0.5)
            p.append(capsule('sleeve', sh, mid, 0.08 * k, 0.074 * k, T))
            p.append(_orient_torus(torus('sleeve_hem', 0.072 * k, 0.008, mid, M['trim'] if top == 'polo' else T, segU=24, segV=6), sh, el))
    p.append(sphere('fist', 0.05 * (0.92 if female else 1), grip + V((-0.005, 0, 0.012)), SK, scale=(1.15, 0.95, 0.9)))
    for i in range(4):
        p.append(sphere('knuckle', 0.017, grip + V((0.035, s * (-0.03 + i * 0.02), 0.02)), SK))
    p.append(sphere('thumb', 0.018, grip + V((0.02, -s * 0.045, 0.04)), SK, scale=(1.4, 1, 1)))
    return join(p, f'Rider_Arm{side}', pivot=sh)


def build_leg(M, v, s):
    side = 'L' if s > 0 else 'R'
    female = v['sex'] == 'f'
    k = 0.88 if female else (1.12 if v.get('build') == 'big' else 1.0)
    bottom = v['bottom']
    hip = V((-0.17, s * 0.11, 0.93))
    if s < 0:
        knee, ankle = V((0.17, s * 0.19, 0.80)), V((0.155, s * 0.15, 0.40))
    else:
        knee, ankle = V((0.02, s * 0.2, 0.72)), V((-0.165, s * 0.15, 0.39))
    B, SK = M['bottom'], M['skin']
    p = []
    if bottom in ('trackpants', 'jeans', 'leggings'):
        kk = k * (0.86 if bottom == 'leggings' else 1.0)
        p.append(capsule('thigh', hip, knee, 0.09 * kk, 0.074 * kk, B))
        p.append(sphere('knee', 0.074 * kk, knee, B))
        p.append(capsule('shin', knee, ankle, 0.072 * kk, 0.058 * kk, B))
        if bottom == 'trackpants':
            p += stripes('thigh_stripe', hip, knee, 0.09 * kk, 0.074 * kk, (0, s, 0.2), M['btrim'])
            p += stripes('shin_stripe', knee, ankle, 0.072 * kk, 0.058 * kk, (0, s, 0), M['btrim'])
            p.append(_orient_torus(torus('cuff', 0.062 * kk, 0.016, ankle, B, segU=24, segV=6), knee, ankle))
        elif bottom == 'jeans':
            p.append(_orient_torus(torus('cuff', 0.064 * kk, 0.018, ankle + (knee - ankle).normalized() * 0.03, B, segU=24, segV=6), knee, ankle))
            p += stripes('seam', hip, knee, 0.09 * kk, 0.074 * kk, (0, s, 0), M['btrim'], width=0.004, spread=0)
    else:  # bare legs: shorts / skirt (with tights for the skirt)
        legmat = SK
        p.append(capsule('thigh', hip, knee, 0.082 * k, 0.066 * k, legmat))
        p.append(sphere('knee', 0.066 * k, knee, legmat))
        p.append(capsule('shin', knee, ankle, 0.064 * k, 0.05 * k, legmat))
        if bottom == 'shorts':
            p.append(capsule('shorts', hip, hip.lerp(knee, 0.62), 0.1 * k, 0.088 * k, B))
            p.append(_orient_torus(torus('shorts_hem', 0.085 * k, 0.01, hip.lerp(knee, 0.62), B, segU=24, segV=6), hip, knee))
    shoes = v.get('shoes', 'sneakers' if bottom != 'skirt' else 'granny')
    shoe_c = ankle + V((0.04, 0, -0.045))
    if shoes in ('sneakers', 'color'):
        if bottom in ('shorts',):
            p.append(_orient_torus(torus('sock', 0.05 * k, 0.014, ankle + V((0, 0, 0.02)), M['sock'], segU=20, segV=6), knee, ankle))
        p.append(subsurf(box('shoe', (0.24, 0.1, 0.085), shoe_c, M['shoe'], bevel=0.03, segs=2), 1))
        p.append(box('sole', (0.25, 0.108, 0.03), shoe_c + V((0.0, 0, -0.045)), M['sole'], bevel=0.01))
        p.append(box('shoe_stripe', (0.12, 0.103, 0.012), shoe_c + V((-0.01, 0, 0.005)), M['btrim'], bevel=0.004))
        p.append(sphere('toe', 0.05, shoe_c + V((0.1, 0, -0.005)), M['shoe'], scale=(0.8, 1.0, 0.75)))
        for i in range(3):
            p.append(box('lace', (0.012, 0.06, 0.008), shoe_c + V((0.02 + i * 0.03, 0, 0.045)), M['sock'], bevel=0.003))
    elif shoes == 'sandals':  # the classic: white socks in sandals
        p.append(capsule('sock', ankle + V((0, 0, 0.09)), shoe_c + V((0.06, 0, -0.01)), 0.055, 0.048, M['sock']))
        p.append(box('sandal_sole', (0.25, 0.1, 0.03), shoe_c + V((0.0, 0, -0.045)), M['leather'], bevel=0.01))
        for i in range(3):
            p.append(box('strap', (0.03, 0.11, 0.06), shoe_c + V((-0.06 + i * 0.07, 0, -0.01)), M['leather'], bevel=0.008))
    else:  # granny shoes
        p.append(subsurf(box('shoe', (0.23, 0.095, 0.075), shoe_c, M['leather'], bevel=0.03, segs=2), 1))
        p.append(box('sole', (0.24, 0.1, 0.025), shoe_c + V((0.0, 0, -0.042)), M['rubber'], bevel=0.008))
        p.append(box('buckle', (0.02, 0.104, 0.02), shoe_c + V((0.02, 0, 0.02)), M['gold'], bevel=0.004))
    return join(p, f'Rider_Leg{side}', pivot=hip)


def build_basket(M):
    p = [box('basket', (0.24, 0.34, 0.17), (0.62, 0, 1.0), M['wicker'], bevel=0.02)]
    for k in range(5):
        p.append(box('weave', (0.245, 0.345, 0.01), (0.62, 0, 0.93 + k * 0.035), M['seat'], bevel=0.003))
    p.append(tube('basket_strut', (0.55, 0, 0.92), (0.5, 0, 0.78), 0.012, M['chrome'], seg=8))
    p.append(capsule('baguette', (0.58, -0.1, 1.04), (0.72, -0.05, 1.28), 0.03, 0.028, M['bread']))
    for k in range(7):
        a = k / 7 * math.pi * 2
        c = V((0.63 + math.cos(a) * 0.05, 0.07 + math.sin(a) * 0.06, 1.1 + random.uniform(0, 0.05)))
        p.append(ico('leaf', 0.035, c, M['leaf'], subdiv=1))
        p.append(ico('flower', 0.025, c + V((0.01, 0, 0.03)), M['flower'], subdiv=1))
    return join(p, 'Bike_Basket')


# ------------------------------------------------------------------------------------------- assemble

def build_rider(M, v):
    root = lib.empty(f"Rider_{v['id']}")
    for key in ('sex', 'age', 'top', 'bottom', 'hair'):
        root[key] = v[key]
    root['hairGroup'] = HAIR_GROUP[v['age']]
    root['basket'] = bool(v.get('basket'))
    root['cap'] = v.get('cap', '')
    parts = [build_torso(M, v), build_head(M, v), build_hair(M, v), fb.build_knife(M),
             build_arm(M, v, 1), build_arm(M, v, -1), build_leg(M, v, 1), build_leg(M, v, -1)]
    if not v.get('glasses'):  # prescription glasses are already part of the face
        parts.append(fb.build_sunglasses(M))
    for o in parts:
        if o is not None:
            lib.set_parent(o, root)
    for o in root.children:  # unique part names inside Blender; the game strips the suffix
        o.name = o.name.split('.')[0]
    return root


def build():
    lib.reset_scene()
    M = mats()
    bike = lib.empty('Bike')
    frame, bar = fb.build_frame(M), fb.build_handlebar(M)
    wf = fb.build_wheel('Bike_WheelFront', M)
    wf.location = fb.FRONT_AXLE
    wr = fb.build_wheel('Bike_WheelRear', M, rear=True)
    wr.location = fb.REAR_AXLE
    crank = fb.build_crank(M)
    for o in (frame, bar, wf, wr, crank):
        lib.set_parent(o, bike)
    basket = build_basket(M)
    riders = [build_rider(M, v) for v in VARIANTS]
    return M, bike, basket, riders


# ------------------------------------------------------------------------------------------- preview

PREVIEW_SKIN = ['#f3d2bd', '#8a5536', '#d9a07a', '#5a3a28', '#e8bfa0', '#b07250', '#efc8ad', '#6a4330', '#c48a62', '#f1cdb4', '#7d4c33', '#d39770']
PREVIEW_HAIR = ['#1d1714', '#3b2a20', '#c8a060', '#1d1714', '#d8d8d8', '#9c3b22', '#3b2a20', '#e0b96c', '#e6e6e6', '#2b2b2b', '#5a3d2b', '#ff6fb5']
PREVIEW_TOP = ['#1a1a20', '#c8302a', '#f4cf3a', '#e9e9ec', '#2d6a45', '#7a5cff', '#2b5a8c', '#ff6fb5', '#b05a7a', '#f08a24', '#5d6066', '#2b5a8c']
PREVIEW_BOTTOM = ['#1a1a20', '#c9b48a', '#2b4a7a', '#2b4a7a', '#c9b48a', '#1a1a20', '#3b5f94', '#5d6066', '#4a5a3a', '#1a1a20', '#6b7b4a', '#1e2a4a']


def preview_colors(riders):
    """Give each preview rider its own colours (render only; the export keeps shared materials)."""
    for i, root in enumerate(riders):
        cmap = {'Skin': PREVIEW_SKIN[i], 'Hair': PREVIEW_HAIR[i], 'Brow': PREVIEW_HAIR[i], 'Top': PREVIEW_TOP[i],
                'Bottom': PREVIEW_BOTTOM[i], 'Cap': PREVIEW_TOP[(i + 5) % 12]}
        for o in root.children_recursive:
            if o.type != 'MESH':
                continue
            for slot in o.material_slots:
                if slot.material and slot.material.name in cmap:
                    m = slot.material.copy()
                    rgb = lib.hex_rgb(cmap[slot.material.name])
                    b = next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
                    b.inputs['Base Color'].default_value = (*rgb, 1)
                    slot.link = 'OBJECT'
                    slot.material = m


def main():
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    M, bike, basket, riders = build()
    scene = bpy.context.scene
    objs = [bike, basket] + list(bike.children_recursive)
    for r in riders:
        objs += [r] + list(r.children_recursive)
    meshes = [o for o in objs if o.type == 'MESH']
    print(f'[riders] variants: {len(riders)}, triangles: {lib.tri_count(meshes)}')
    for r in riders:
        print(f'[riders] {r.name}: {lib.tri_count([o for o in r.children_recursive if o.type == "MESH"])} tris')
    out = os.path.join(ROOT, 'assets', 'models', 'riders.glb')
    lib.export_glb(out, objs)
    print(f'[riders] exported {out}')
    if '--no-render' in argv:
        return

    # lineup: every variant on its own (linked) bike, in two rows
    preview_colors(riders)
    lib.preview_stage(scene, size=(1920, 1080))
    bike_parts = list(bike.children)
    for i, r in enumerate(riders):
        row, col = divmod(i, 6)
        x, y = (col - 2.5) * 1.5, row * 2.4
        rot = math.radians(-35)
        r.location = (x, y, 0)
        r.rotation_euler = (0, 0, rot)
        holder = lib.empty(f'BikeCopy_{i}', (x, y, 0))
        holder.rotation_euler = (0, 0, rot)
        for part in bike_parts:
            c = part.copy()
            lib.link(c)
            c.parent = holder
        if VARIANTS[i].get('basket'):
            bc = basket.copy()
            lib.link(bc)
            bc.parent = holder
    for i, r in enumerate(riders):
        sg = next((o for o in r.children if o.name.startswith('Rider_Sunglasses')), None)
        if sg and i % 3:
            sg.hide_render = True
    bike.hide_render = True
    for o in bike.children_recursive:
        o.hide_render = True
    basket.hide_render = True
    rdir = os.path.join(ROOT, 'renders', 'riders')
    os.makedirs(rdir, exist_ok=True)
    lib.render(scene, lib.camera('Cam_lineup', (1.2, -9.5, 3.4), (0.2, 1.4, 1.0), 38), os.path.join(rdir, '01_lineup.png'))
    # face close-ups, one row of six heads at a time
    for row in range(2):
        cam = lib.camera(f'Cam_faces{row}', (0.6, -4.6 + row * 2.4, 1.75), (0.0, row * 2.4, 1.5), 50)
        lib.render(scene, cam, os.path.join(rdir, f'0{row + 2}_faces_row{row + 1}.png'))


if __name__ == '__main__':
    main()
