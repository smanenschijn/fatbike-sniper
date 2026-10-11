"""Build the Henri Donutplein, after the Henri Dunantplein in Nijverdal.

Same frame as build_square.py (meters, +Y = north): the player sits at (0, -11.55) on the terrace of
Eetcafe 't Donutje on the south side, looking north at the gemeentehuis with its row of tall brick arches.
West: the orange-red apartment block with a shop gallery (arcade) at street level, which riders use as a
shortcut, and the octagonal corner tower with its mint-green crown. East: a light modern block.

Entries (see godot/scripts/config.gd): west street, the gallery from the north, the north alley, east street.

Run:  Blender -b -P blender/build_dunant.py [-- --no-render]
"""
import math
import os
import random
import sys

import bpy
from mathutils import Vector

sys.path.insert(0, os.path.dirname(__file__))
import lib  # noqa: E402
import textures  # noqa: E402
import build_square as sq  # noqa: E402  (materials, windows, shopfronts and props)
from lib import box, cyl, ico, join, material, sphere, tube, text_mesh, extrude_profile, instance  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
V = Vector
rng = random.Random(7)
M = sq.M
BUILDINGS = []

SHOPS = ['DE DONUTFABRIEK', 'REGGEDAL IJS', 'BAKKERIJ BERTUS', 'BOEKHANDEL', 'KAPSALON KNIP', 'DROGISTERIJ',
         'SLAGERIJ TWENTE', 'BLOEMEN', 'OPTIEK', 'SCHOENEN', 'KAASHANDEL', 'LUNCHROOM', 'SPEELGOED', 'FIETSHOP',
         'JUWELIER', 'BRILLEN', 'TASSEN', 'SNACKBAR', 'KRUIDENIER', 'WOLWINKEL', 'PARFUMERIE', 'BOETIEK',
         'TELEFOONWINKEL', 'HOEDEN', 'REISBUREAU', 'DIERENWINKEL']


def make_materials():
    sq.make_materials()
    tx = textures.ensure(os.path.join(ROOT, 'assets', 'textures'))
    t = lambda name, key, rough=0.85, ns=1.0: lib.tex_material(name, *tx[key], rough=rough, normal_strength=ns)
    M.update({
        'slabs': t('SlabsGrey', 'slabs_grey', 0.75, 0.7),
        'pavers': t('PaversSalmon', 'pavers_salmon', 0.85, 1.0),
        'brick_orange': t('BrickOrange', 'brick_orange', 0.85, 1.0),
        'glass_blue': material('GlassBlue', '#2b465e', rough=0.05, metal=0.5, coat=1.0),
        'mullion': material('MullionGrey', '#34373c', rough=0.4, metal=0.6),
        'metal_roof': material('MetalRoof', '#4b4f55', rough=0.45, metal=0.6),
        'skylight': material('Skylight', '#d5e2ea', rough=0.15, metal=0.2),
        'mint': material('MintPanel', '#8cc4a4', rough=0.55),
        'stucco': material('Stucco', '#e6ddcb', rough=0.9),
        'stucco_dark': material('StuccoGrey', '#8c8a85', rough=0.85),
        'gravel': material('RoofGravel', '#5f5c57', rough=1.0),
        'hvac': material('HVAC', '#a3a6a9', rough=0.5, metal=0.4),
        'ceiling': material('ArcadeCeiling', '#ece6da', rough=0.9),
        'fab_black': material('FabricBlack', '#26272a', rough=0.8, sheen=0.5),
        'flag_lilac': material('FlagLilac', '#b67cbf', rough=0.8, sheen=0.4),
        'flag_orange': material('FlagOrange', '#f47a1f', rough=0.8, sheen=0.4),
        'bench_wood': material('BenchWood', '#a07a50', rough=0.7),
        'dark_band': material('SlabDark', '#3f4043', rough=0.8),
        'wet': material('WetBrick', '#4a3a30', rough=0.08, coat=1.0),
        'jet': material('WaterJet', '#d8eef8', rough=0.05, emission='#bfe6ff', strength=0.4),
        'rock': material('Boulder', '#8e9095', rough=0.9),
        'grey_brick': material('GreyBrick', '#3e4045', rough=0.85),
        'beige_grey': material('BeigeGrey', '#bdb7ab', rough=0.9),
        'stripe_brown': material('StripeBrown', '#5a3424', rough=0.85),
        'cheese': material('Cheese', '#f0b93a', rough=0.5),
    })


# ================================================================ helpers

def frame(a, b, facing):
    """Facade line a->b facing `facing`: (origin, rotation, length). Local frame: facade at y=0 facing -Y, x along it."""
    a, b, f = V(a), V(b), V(facing).normalized()
    ang = math.atan2(f.y, f.x) + math.pi / 2
    lx = V((math.cos(ang), math.sin(ang)))
    if (b - a).dot(lx) < 0:
        a, b = b, a
    return a, ang, (b - a).length


def put(o, origin, ang, z=0.0):
    o.location = (origin.x, origin.y, z)
    o.rotation_euler = (0, 0, ang)
    return o


def shifted(parts, dx=0.0, dy=0.0, dz=0.0):
    for o in parts:
        o.location = (o.location.x + dx, o.location.y + dy, o.location.z + dz)
    return parts


def arch_pts(xa, xb, zs, steps=14, up=True):
    """Semicircle over [xa, xb] springing at zs, left to right."""
    cx, r = (xa + xb) / 2, (xb - xa) / 2
    return [(cx - r * math.cos(math.pi * i / steps), zs + r * math.sin(math.pi * i / steps)) for i in range(steps + 1)]


def balcony(xc, z, w):
    p = [box('balc_slab', (w, 1.1, 0.16), (xc, -0.55, z), M['stone'], smooth=False),
         box('balc_rail', (w, 0.05, 0.06), (xc, -1.08, z + 1.0), M['iron'], smooth=False)]
    for s in (-1, 1):
        p.append(box('balc_rail', (0.05, 1.1, 0.06), (xc + s * (w / 2 - 0.03), -0.55, z + 1.0), M['iron'], smooth=False))
    n = int(w / 0.2)
    for i in range(n + 1):
        p.append(box('baluster', (0.025, 0.025, 0.92), (xc - w / 2 + 0.06 + (w - 0.12) * i / n, -1.07, z + 0.54), M['iron'], smooth=False))
    return p


def roof_clutter(L, D, H):
    """Gravel roof with a brick parapet and the grey service boxes you see in the aerial photo."""
    p = [box('roof_gravel', (L, D, 0.08), (L / 2, D / 2, H + 0.04), M['gravel'], smooth=False),
         box('parapet', (L, 0.3, 0.55), (L / 2, 0.15, H + 0.27), M['brick_orange'], smooth=False),
         box('coping', (L + 0.05, 0.4, 0.08), (L / 2, 0.15, H + 0.58), M['stone'], smooth=False)]
    for _ in range(int(L / 6)):
        x, y = rng.uniform(1.5, L - 1.5), rng.uniform(D * 0.35, D - 1.5)
        s = rng.uniform(0.6, 1.3)
        p.append(box('hvac', (s * 1.4, s, s * 0.9), (x, y, H + s * 0.45), M['hvac'], smooth=False))
    return p


# ================================================================ the gallery block (red apartments over shops)

def galerij(name, a, b, facing, depth=13.0, floors=4, arcade=True, bay=4.4, shops=None, brick='brick_orange',
            awnings=True, shop_chance=1.0, flags=()):
    """Orange-red 90s apartment block: shops at street level (behind an arched gallery when `arcade`),
    balconies and bay windows above, mint-green trim and a gravel roof."""
    origin, ang, L = frame(a, b, facing)
    GF = 4.4 if arcade else 4.0
    FH = 2.9
    H = GF + floors * FH
    AD = 3.6  # gallery depth
    nb = max(1, round(L / bay))
    pitch = L / nb
    p = []
    W = M[brick]
    if arcade:
        p.append(box('upper', (L, depth, H - GF), (L / 2, depth / 2, (GF + H) / 2), W, smooth=False))
        p.append(box('lower', (L, depth - AD, GF), (L / 2, AD + (depth - AD) / 2, GF / 2), W, smooth=False))
        p.append(box('arcade_ceiling', (L, AD, 0.06), (L / 2, AD / 2, GF - 0.03), M['ceiling'], smooth=False))
        p.append(box('arcade_floor', (L, AD, 0.05), (L / 2, AD / 2, 0.025), M['tegels'], smooth=False))
        pw = 0.8
        xs = [min(max(i * pitch, pw / 2), L - pw / 2) for i in range(nb + 1)]
        for x in xs:
            p.append(box('pillar', (pw, 0.7, GF), (x, 0.35, GF / 2), W, smooth=False))
            p.append(box('pillar_foot', (pw + 0.08, 0.78, 0.35), (x, 0.35, 0.175), M['stone_dark'], smooth=False))
            p.append(box('pillar_cap', (pw + 0.1, 0.8, 0.14), (x, 0.35, GF * 0.52), M['stone'], smooth=False))
        for i in range(nb):
            xa, xb = xs[i] + pw / 2, xs[i + 1] - pw / 2
            r = (xb - xa) / 2
            zs = GF - 0.35 - r
            sp = extrude_profile('spandrel', [(xa, GF), (xa, zs)] + arch_pts(xa, xb, zs)[1:-1] + [(xb, zs), (xb, GF)], 0.7, W)
            sp.location = (0, 0.35, 0)
            p.append(sp)
            p.append(sphere('arcade_lamp', 0.16, ((xa + xb) / 2, AD / 2, GF - 0.12), M['lamp_glow'], scale=(1, 1, 0.5), seg=12, rings=6))
    else:
        p.append(box('body', (L, depth, H), (L / 2, depth / 2, H / 2), W, smooth=False))
        p.append(box('plinth', (L, 0.08, 0.45), (L / 2, -0.04, 0.225), M['stone_dark'], smooth=False))
    p.append(box('band', (L, 0.14, 0.18), (L / 2, -0.07, GF + 0.05), M['stone'], smooth=False))

    # shops at street level
    shop_y = AD if arcade else 0.0
    for i in range(nb):
        x0 = i * pitch
        if rng.random() > shop_chance:
            sh = sq.door(pitch / 2, 1.0, 2.35, rng.choice(sq.DOORS), 'frame_white')
            sh += sq.window(pitch * 0.22, 1.9, 0.9, 1.8, 'frame_white')
            p += shifted(sh, x0, shop_y)
            continue
        nm = (shops or SHOPS).pop(0) if (shops or SHOPS) else 'WINKEL'
        aw = rng.choice(sq.AWNINGS) if (awnings and not arcade and rng.random() < 0.6) else None
        sh = sq.shopfront(pitch, 3.6 if arcade else GF, nm, rng.choice(['door_black', 'frame_green', 'door_blue', 'mullion']),
                          rng.choice(sq.SIGNS), aw)
        p += shifted(sh, x0, shop_y)

    # floors above: a rhythm of window bays, balconies and projecting bay windows
    kinds = ['win', 'balc', 'win', 'oriel'] if L > 10 else ['win', 'balc']
    off = rng.randrange(len(kinds))
    for i in range(nb):
        xc = (i + 0.5) * pitch
        kind = kinds[(i + off) % len(kinds)]
        if kind == 'oriel' and floors >= 3:
            z0, z1 = GF + 0.15, GF + (floors - 1) * FH
            ow = pitch - 1.2
            p.append(box('oriel', (ow, 0.8, z1 - z0), (xc, -0.4, (z0 + z1) / 2), W, smooth=False))
            p.append(box('oriel_cap', (ow + 0.15, 0.95, 0.12), (xc, -0.45, z1 + 0.06), M['mint'], smooth=False))
            for f in range(floors - 1):
                zc = GF + f * FH + FH * 0.52
                p += shifted(sq.window(xc, zc, ow * 0.62, 1.55, 'frame_white'), 0, -0.8)
        for f in range(floors):
            zc = GF + f * FH + FH * 0.52
            if kind == 'oriel' and floors >= 3 and f < floors - 1:
                continue
            if kind == 'balc':
                p += sq.window(xc - 0.55, zc - 0.25, 0.85, 2.0, 'frame_white')
                p += sq.window(xc + 0.75, zc, 0.8, 1.4, 'frame_white')
                p += balcony(xc, GF + f * FH + 0.08, pitch - 0.9)
            else:
                ww = min(1.0, pitch * 0.22)
                for s in (-1, 1):
                    p += sq.window(xc + s * pitch * 0.22, zc, ww, 1.5, 'frame_white')
        # mint panel + steel beam on the top floor, as on the real building
        if i % 2 == 0:
            p.append(box('mint_panel', (0.5, 0.06, FH * 0.7), (i * pitch + 0.45, -0.03, H - FH * 0.5), M['mint'], smooth=False))
        p.append(box('roof_beam', (0.12, 1.5, 0.12), (i * pitch + 0.2, -0.6, H + 0.75), M['iron'], rot=(math.radians(-28), 0, 0), smooth=False))
    p.append(box('top_trim', (L, 0.12, 0.35), (L / 2, -0.06, H - 0.18), M['mint'], smooth=False))
    p += roof_clutter(L, depth, H)
    o = join(p, name)
    put(o, origin, ang)
    lib.box_uv(o, 2.0)
    BUILDINGS.append(o)
    # Dutch flags out of a few windows (world space)
    lx = V((math.cos(ang), math.sin(ang)))
    out = V((math.sin(ang), -math.cos(ang)))
    flag_objs = []
    for t, fz in flags:
        base = origin + lx * (t * L) + out * 0.05
        flag_objs.append(sq.flag((base.x, base.y, fz), (out.x, out.y)))
    return o, H, flag_objs


def corner_tower(c, r=4.3, H=16.0):
    """Octagonal corner tower: brick with windows, a mint-green glass crown and a copper-green spire roof."""
    c = V(c)
    p = []
    rot = math.pi / 8  # flat faces on the axes
    ap = r * math.cos(math.pi / 8)
    fw = 2 * r * math.sin(math.pi / 8)
    p.append(cyl('tower', r, H, (c.x, c.y, H / 2), M['brick_orange'], seg=8, rot=(0, 0, rot), smooth=False))
    p.append(cyl('tower_band', r * 1.02, 0.18, (c.x, c.y, 4.45), M['stone'], seg=8, rot=(0, 0, rot), smooth=False))
    for k in (-2, -1, 0, 1, 2):  # south .. north faces (the west ones are inside the block)
        th = k * math.pi / 4
        face = []
        if k in (-1, 0, 1):
            face += sq.shopfront(fw, 4.0, 'DE DONUTFABRIEK' if k == 0 else ('KOFFIE' if k == 1 else 'DONUTS'),
                                 'mullion', 'sign_red', ('fab_red', 'fab_cream') if k == 0 else None)
            face = shifted(face, -fw / 2)
        for f in range(4):
            zc = 4.4 + f * 2.9 + 1.5
            face += sq.window(0, zc, min(1.3, fw * 0.4), 1.6, 'frame_white')
        if k == 0:
            face += balcony(0, 4.4 + 2 * 2.9 + 0.08, fw - 0.4)
        fo = join(face, 'tower_face')
        fo.location = (c.x + ap * math.cos(th), c.y + ap * math.sin(th), 0)
        fo.rotation_euler = (0, 0, th + math.pi / 2)
        p.append(fo)
    # mint crown with a ribbon of glass, then the copper roof
    p.append(cyl('crown', r * 0.93, 3.0, (c.x, c.y, H + 1.5), M['mint'], seg=8, rot=(0, 0, rot), smooth=False))
    p.append(cyl('crown_glass', r * 0.945, 1.5, (c.x, c.y, H + 1.55), M['glass'], seg=8, rot=(0, 0, rot), smooth=False))
    p.append(cyl('crown_eave', r * 1.03, 0.2, (c.x, c.y, H + 3.05), M['white'], seg=8, rot=(0, 0, rot), smooth=False))
    p.append(cyl('tower_roof', r * 1.0, 3.4, (c.x, c.y, H + 3.15 + 1.7), M['copper'], seg=8, r2=0.25, rot=(0, 0, rot), smooth=False))
    p.append(sphere('tower_knob', 0.3, (c.x, c.y, H + 6.75), M['copper'], seg=12, rings=6))
    p.append(cyl('parapet', r * 1.01, 0.4, (c.x, c.y, H + 0.2), M['brick_orange'], seg=8, rot=(0, 0, rot), smooth=False))
    o = join(p, 'Galerij_Tower')
    lib.box_uv(o, 2.0)
    BUILDINGS.append(o)
    return o


# ================================================================ gemeentehuis

def gemeentehuis(a, b, facing, depth=16.0, n=6):
    """Town hall: a row of tall brick arches with recessed blue glass, barrel-vaulted metal roofs behind."""
    origin, ang, L = frame(a, b, facing)
    pitch = L / n
    pw = 1.0
    zs = 8.4
    xs = [min(max(i * pitch, pw / 2), L - pw / 2) for i in range(n + 1)]
    rmax = max((xs[i + 1] - xs[i] - pw) / 2 for i in range(n))
    top = zs + rmax + 1.5
    W = M['brick_orange']
    p = [box('gh_body', (L, depth - 1.4, top - 0.3), (L / 2, 1.4 + (depth - 1.4) / 2, (top - 0.3) / 2), W, smooth=False)]
    for x in xs:
        p.append(box('gh_pilaster', (pw, 1.4, top), (x, 0.7, top / 2), W, smooth=False))
        p.append(box('gh_foot', (pw + 0.1, 1.5, 0.5), (x, 0.7, 0.25), M['stone_dark'], smooth=False))
    p.append(box('gh_coping', (L + 0.3, 1.7, 0.25), (L / 2, 0.75, top + 0.12), M['stone'], smooth=False))
    names = {0: 'BIBLIOTHEEK', 2: 'GEMEENTEHUIS', 4: 'CULTUURHUIS'}
    for i in range(n):
        xa, xb = xs[i] + pw / 2, xs[i + 1] - pw / 2
        cx, r = (xa + xb) / 2, (xb - xa) / 2
        arc = arch_pts(xa, xb, zs, 20)
        sp = extrude_profile('gh_spandrel', [(xa, top), (xa, zs)] + arc[1:-1] + [(xb, zs), (xb, top)], 1.4, W)
        sp.location = (0, 0.7, 0)
        p.append(sp)
        # brick arch ring standing a little proud
        ring_out = arch_pts(xa - 0.05, xb + 0.05, zs, 20)
        ring_in = arch_pts(xa + 0.3, xb - 0.3, zs, 20)
        rg = extrude_profile('gh_archring', ring_out + list(reversed(ring_in)), 0.2, M['brick_red'])
        rg.location = (0, -0.08, 0)
        p.append(rg)
        g = extrude_profile('gh_glass', [(xa, 0.0), (xb, 0.0)] + arc[::-1], 0.06, M['glass_blue'])
        g.location = (0, 1.38, 0)
        p.append(g)
        # mullions follow the arch
        for k in range(1, 4):
            x = xa + (xb - xa) * k / 4
            h = zs + math.sqrt(max(0.0, r * r - (x - cx) ** 2))
            p.append(box('gh_mullion', (0.09, 0.12, h), (x, 1.3, h / 2), M['mullion'], smooth=False))
        for z in (4.3, 6.4, zs):
            p.append(box('gh_transom', (xb - xa, 0.12, 0.09 if z != 4.3 else 0.35), (cx, 1.3, z), M['mullion'], smooth=False))
        if i in names:
            p.append(text_mesh('gh_name', names[i], 0.42, (cx, -0.03, zs + r + 0.75), mat=M['white'], extrude=0.02))
        if i == 2:  # main entrance: glass doors under a canopy
            p.append(box('gh_canopy', (xb - xa + 0.4, 2.2, 0.2), (cx, -0.4, 3.4), M['mullion'], smooth=False))
            p.append(box('gh_doors', (2.4, 0.08, 2.6), (cx, 1.25, 1.3), M['glass'], smooth=False))
            p.append(box('gh_mat', (2.8, 1.6, 0.03), (cx, 0.4, 0.015), M['iron'], smooth=False))
        elif i >= 4:  # café / culture house with awnings and a terrace
            tilt = math.radians(22)
            dep = 1.6
            for j in range(6):
                x = xa + 0.2 + (xb - xa - 0.4) * (j + 0.5) / 6
                p.append(box('gh_awning', ((xb - xa - 0.4) / 6 + 0.002, dep, 0.025),
                             (x, -dep / 2 * math.cos(tilt) + 0.1, 3.8 - dep / 2 * math.sin(tilt)),
                             M['fab_yellow' if j % 2 == 0 else 'fab_cream'], rot=(tilt, 0, 0), smooth=False))
        # barrel vault per bay
        rb = pitch / 2 - 0.05
        p.append(cyl('gh_vault', rb, depth - 1.6, (cx, 1.5 + (depth - 1.6) / 2, top - 0.3), M['metal_roof'], rot=(math.pi / 2, 0, 0), seg=24))
        p.append(box('gh_skylight', (0.7, depth - 2.4, 0.06), (cx, 1.9 + (depth - 2.4) / 2, top - 0.3 + rb), M['skylight'], smooth=False))
    # flagpoles in front of the arches: NL, the gemeente's lilac banner, Koningsdag orange
    fl = []
    for j, (x, kind) in enumerate(((pitch * 0.6, 'nl'), (pitch * 1.2, 'lilac'), (pitch * 1.8, 'orange'))):
        y = -1.3
        fl.append(tube('flagpole', (x, y, 0), (x, y, 10.5), 0.07, M['white'], r2=0.05, seg=10))
        fl.append(sphere('flagknob', 0.1, (x, y, 10.55), M['gold'], seg=10, rings=6))
        fl.append(box('flagfoot', (0.35, 0.35, 0.3), (x, y, 0.15), M['stone_dark'], smooth=False))
        if kind == 'nl':
            for k, m in enumerate(('flag_red', 'flag_white', 'flag_blue')):
                fl.append(box('flag', (1.7, 0.02, 0.38), (x + 0.9, y, 10.0 - k * 0.38), M[m], smooth=False))
        else:
            fl.append(box('banner', (0.9, 0.02, 3.2), (x + 0.5, y, 8.6), M['flag_' + kind], smooth=False))
            fl.append(box('banner_bar', (1.0, 0.05, 0.05), (x + 0.5, y, 10.2), M['white'], smooth=False))
    p.append(join(fl, 'Gemeentehuis_Flags'))
    o = join(p, 'Gemeentehuis')
    put(o, origin, ang)
    lib.box_uv(o, 2.0)
    BUILDINGS.append(o)
    return o


# ================================================================ light modern block (east side)

def modern_block(name, a, b, facing, depth=14.0, floors=2, shops=('DROGIST', 'BLOEMEN', 'HEMDEN & CO'), cone=False):
    origin, ang, L = frame(a, b, facing)
    GF, FH = 4.0, 3.2
    H = GF + floors * FH
    p = [box('body', (L, depth, H), (L / 2, depth / 2, H / 2), M['stucco'], smooth=False),
         box('gf_glass', (L - 0.6, 0.06, GF - 0.8), (L / 2, -0.03, (GF - 0.8) / 2 + 0.3), M['glass'], smooth=False),
         box('plinth', (L, 0.1, 0.3), (L / 2, -0.05, 0.15), M['stucco_dark'], smooth=False),
         box('canopy', (L, 1.8, 0.28), (L / 2, -0.9, GF - 0.2), M['white'], smooth=False)]
    for k in range(int(L / 2.4) + 1):
        p.append(box('gf_post', (0.1, 0.1, GF - 0.5), (min(L - 0.3, 0.3 + k * 2.4), -0.08, (GF - 0.5) / 2), M['mullion'], smooth=False))
    seg = L / len(shops)
    for i, nm in enumerate(shops):
        p.append(text_mesh('canopy_sign', nm, 0.34, (seg * (i + 0.5), -1.82, GF - 0.2), mat=M['sign_blue'], extrude=0.015))
    if cone:  # giant ice cream on the canopy above the middle shop
        cx = L / 2
        p.append(cyl('cone', 0.45, 1.4, (cx, -0.9, GF + 0.7), M['wood_light'], r2=0.05, rot=(math.pi, 0, 0), seg=16))
        for k, (dx, dz, m) in enumerate(((-0.2, 1.55, 'flower_pink'), (0.22, 1.55, 'fab_cream'), (0.0, 1.9, 'wood'))):
            p.append(sphere('scoop', 0.36, (cx + dx, -0.9, GF + dz), M[m], seg=16, rings=8))
        p.append(sphere('cherry', 0.1, (cx, -0.9, GF + 2.3), M['flower_red'], seg=10, rings=6))
    for f in range(floors):
        z = GF + f * FH + FH * 0.55
        p.append(box('ribbon', (L - 1.0, 0.08, 1.5), (L / 2, -0.02, z), M['glass'], smooth=False))
        p.append(box('ribbon_sill', (L - 0.9, 0.25, 0.08), (L / 2, -0.12, z - 0.78), M['white'], smooth=False))
        for k in range(int((L - 1.0) / 1.6) + 1):
            p.append(box('ribbon_mullion', (0.08, 0.1, 1.5), (0.5 + min(k * 1.6, L - 1.0), -0.05, z), M['white'], smooth=False))
    p += [box('roof_gravel', (L, depth, 0.08), (L / 2, depth / 2, H + 0.04), M['gravel'], smooth=False),
          box('parapet', (L, 0.25, 0.7), (L / 2, 0.12, H + 0.35), M['stucco'], smooth=False)]
    for k in range(int(L / 1.2)):  # glass balustrade posts of the roof terrace
        p.append(box('rail_post', (0.05, 0.05, 1.0), (0.4 + k * 1.2, 1.2, H + 0.5), M['chrome'], smooth=False))
    p.append(box('rail_top', (L - 0.6, 0.06, 0.06), (L / 2, 1.2, H + 1.0), M['chrome'], smooth=False))
    o = join(p, name)
    put(o, origin, ang)
    lib.box_uv(o, 2.0)
    BUILDINGS.append(o)
    return o


# ================================================================ low shop houses (the row from the street photo)

def shop_house(name, a, b, facing, wall, shops, floors=2, depth=11.0, frames='frame_white', fascia='sign_black',
               wood_fascia=False, eave=False, win_canopies=False, planters=False):
    """Two-storey shop building: big glass shop windows under a fascia with the shop names, flat roof."""
    origin, ang, L = frame(a, b, facing)
    GF, FH = 3.8, 3.0
    H = GF + floors * FH
    W = M[wall]
    p = [box('body', (L, depth, H), (L / 2, depth / 2, H / 2), W, smooth=False),
         box('plinth', (L, 0.08, 0.35), (L / 2, -0.04, 0.175), M['stone_dark'], smooth=False)]
    seg = L / len(shops)
    for i, nm in enumerate(shops):
        x0, x1 = i * seg + 0.3, (i + 1) * seg - 0.3
        xc = (x0 + x1) / 2
        p.append(box('shopglass', (x1 - x0, 0.06, GF - 1.3), (xc, -0.04, 0.35 + (GF - 1.3) / 2), M['glass'], smooth=False))
        for k in range(int((x1 - x0) / 1.6) + 1):
            p.append(box('shop_mullion', (0.07, 0.1, GF - 1.3), (x0 + min(k * 1.6, x1 - x0), -0.07, 0.35 + (GF - 1.3) / 2), M['mullion'], smooth=False))
        p.append(box('shopdoor', (1.0, 0.05, 2.3), (x1 - 0.8, -0.09, 1.2), M['glass'], smooth=False))
        if planters:  # wooden ledge under the window, as at the gift shop
            p.append(box('ledge', (x1 - x0 - 1.4, 0.45, 0.45), (x0 + (x1 - x0 - 1.4) / 2, -0.25, 0.225), M['wood_light'], smooth=False))
        if wood_fascia:
            fz = GF - 0.55
            p.append(box('wood_fascia', (seg, 0.9, 0.8), (i * seg + seg / 2, -0.45, fz), M['wood_light'], smooth=False))
            for k in range(4):
                p.append(box('wood_slat', (seg, 0.92, 0.04), (i * seg + seg / 2, -0.46, fz - 0.3 + k * 0.2), M['wood'], smooth=False))
            p.append(box('sign_plate', (2.4, 0.05, 0.5), (xc, -0.93, fz), M['sign_blue'], smooth=False))
            p.append(text_mesh('signtext', nm, min(0.3, 2.2 / (0.62 * max(4, len(nm)))), (xc, -0.97, fz), mat=M['white'], extrude=0.012))
            for k in range(3):  # cut-out butterflies on the fascia
                bx = i * seg + seg * (0.15 + 0.35 * k)
                for s in (-1, 1):
                    p.append(sphere('butterfly', 0.14, (bx + s * 0.1, -0.93, fz + 0.45), M['fab_blue'], scale=(1, 0.2, 1.3), seg=8, rings=4))
        else:
            p.append(box('fascia', (seg, 0.25, 0.6), (i * seg + seg / 2, -0.12, GF - 0.45), M[fascia], smooth=False))
            p.append(text_mesh('signtext', nm, min(0.36, (seg - 0.8) / (0.62 * max(4, len(nm)))), (xc, -0.26, GF - 0.45),
                               mat=M['white'], extrude=0.012))
    p.append(box('band', (L, 0.12, 0.12), (L / 2, -0.06, GF), M['stone'], smooth=False))
    ncols = max(1, int(L / 3.2))
    for f in range(floors):
        zc = GF + f * FH + FH * 0.5
        for j in range(ncols):
            xc = L * (j + 0.5) / ncols
            p += sq.window(xc, zc, min(1.9, L / ncols * 0.6), 1.45, frames)
            if win_canopies:
                p.append(box('win_canopy', (min(1.9, L / ncols * 0.6) + 0.4, 0.5, 0.06), (xc, -0.25, zc + 0.95), M['frame_white'], smooth=False))
    if eave:  # deep flat eave with rafters, like the optician's building
        p.append(box('eave', (L + 0.6, 1.4, 0.14), (L / 2, -0.4, H + 0.35), M['frame_white'], smooth=False))
        for k in range(int(L / 0.9)):
            p.append(box('rafter', (0.08, 1.2, 0.14), (0.3 + k * 0.9, -0.5, H + 0.2), M['wood'], smooth=False))
        p.append(box('roof_wall', (L, 0.25, 1.0), (L / 2, 1.5, H + 0.8), W, smooth=False))
    else:
        p.append(box('parapet_cap', (L + 0.1, 0.35, 0.12), (L / 2, 0.1, H + 0.06), M['stone'], smooth=False))
    p.append(box('roof_gravel', (L, depth, 0.06), (L / 2, depth / 2, H + 0.03), M['gravel'], smooth=False))
    o = join(p, name)
    put(o, origin, ang)
    lib.box_uv(o, 2.0)
    BUILDINGS.append(o)
    return o


def floor_fountain(c, w=2.2, l=8.0, jets=9):
    """Fountain jets in a wet brick strip with a slot drain (the street photo)."""
    c = V(c)
    p = [box('ff_wet', (w, l, 0.02), (c.x, c.y, 0.045), M['wet'], smooth=False),
         box('ff_drain', (0.12, l - 0.6, 0.025), (c.x, c.y, 0.05), M['iron'], smooth=False)]
    for i in range(jets):
        y = c.y - l / 2 + 0.6 + (l - 1.2) * i / (jets - 1)
        h = rng.uniform(0.35, 0.6)
        x = c.x + 0.35
        p.append(cyl('ff_nozzle', 0.05, 0.02, (x, y, 0.055), M['chrome'], seg=8))
        p.append(cyl('ff_jet', 0.022, h, (x, y, 0.06 + h / 2), M['jet'], r2=0.012, seg=8))
        p.append(sphere('ff_spray', 0.07, (x, y, 0.06 + h), M['jet'], seg=8, rings=4))
    return join(p, 'FloorFountain')


def boulder(name, r, seed):
    o = ico(name, r, (0, 0, r * 0.55), M['rock'], scale=(1.25, 1.0, 0.8), subdiv=3)
    tex = bpy.data.textures.new(name + 'Noise', 'CLOUDS')
    tex.noise_scale = 0.5
    d = o.modifiers.new('rocky', 'DISPLACE')
    d.texture = tex
    d.strength = r * 0.35
    d.texture_coords = 'GLOBAL' if seed % 2 else 'LOCAL'
    return join([o], name)


def prop_market_stall(kind, c1, c2='fab_cream'):
    """Market stall facing -Y: table with goods, striped sloping canopy and a name board."""
    p = [box('ms_table', (2.8, 1.0, 0.08), (0, -0.4, 0.85), M['wood_light'], smooth=False),
         box('ms_skirt', (2.8, 0.03, 0.75), (0, -0.92, 0.45), M[c1], smooth=False)]
    for x in (-1.3, 1.3):
        p.append(box('ms_leg', (0.06, 0.06, 0.85), (x, 0.0, 0.42), M['iron'], smooth=False))
    for x in (-1.45, 1.45):
        p.append(tube('ms_pole', (x, -1.05, 0), (x, -1.05, 3.0), 0.03, M['iron'], seg=6))
        p.append(tube('ms_pole', (x, 0.95, 0), (x, 0.95, 2.6), 0.03, M['iron'], seg=6))
    tilt = math.atan2(0.4, 2.0)
    for k in range(8):
        x = -1.6 + 3.2 * (k + 0.5) / 8
        p.append(box('ms_canopy', (3.2 / 8 + 0.002, 2.3, 0.03), (x, -0.05, 2.82), M[c1 if k % 2 == 0 else c2], rot=(-tilt, 0, 0), smooth=False))
        p.append(box('ms_valance', (3.2 / 8 + 0.002, 0.02, 0.25), (x, -1.2, 2.92), M[c1 if k % 2 == 0 else c2], smooth=False))
    names = {'fruit': 'FRUIT', 'kaas': 'KAAS', 'bloemen': 'BLOEMEN', 'wafels': 'STROOPWAFELS'}
    p.append(box('ms_board', (1.9, 0.04, 0.4), (0, -1.23, 2.55), M['white'], smooth=False))
    p.append(text_mesh('ms_name', names[kind], 0.24 if kind != 'wafels' else 0.19, (0, -1.26, 2.55), mat=M['sign_red'], extrude=0.01))
    if kind == 'fruit':
        for j, m in enumerate(('flower_red', 'fab_orange', 'leaf_light', 'flower_yellow')):
            cx = -1.05 + j * 0.7
            p.append(box('ms_crate', (0.6, 0.45, 0.16), (cx, -0.5, 0.97), M['wood'], smooth=False))
            for _ in range(10):
                p.append(sphere('ms_fruit', 0.065, (cx + rng.uniform(-0.22, 0.22), -0.5 + rng.uniform(-0.15, 0.15), 1.1), M[m], seg=8, rings=5))
    elif kind == 'kaas':
        for j in range(5):
            for h in range(2 if j % 2 else 3):
                p.append(cyl('ms_cheese', 0.22, 0.12, (-1.1 + j * 0.55, -0.45, 0.95 + h * 0.125), M['cheese'], seg=16))
    elif kind == 'bloemen':
        for j in range(6):
            cx = -1.15 + j * 0.46
            p.append(cyl('ms_bucket', 0.15, 0.3, (cx, -0.45, 1.04), M['iron'], r2=0.18, seg=10))
            m = ('flower_red', 'flower_pink', 'flower_yellow', 'flower_white')[j % 4]
            for _ in range(7):
                p.append(ico('ms_bloom', 0.06, (cx + rng.uniform(-0.12, 0.12), -0.45 + rng.uniform(-0.12, 0.12), 1.3 + rng.uniform(0, 0.15)), M[m], subdiv=1))
    else:
        for j in range(6):
            for h in range(4):
                p.append(cyl('ms_wafel', 0.14, 0.02, (-1.15 + j * 0.46, -0.45, 0.91 + h * 0.022), M['wood_light'], seg=14))
    return join(p, 'MarketStall_' + kind)


def prop_lamp_modern():
    p = [tube('pole', (0, 0, 0), (0, 0, 5.2), 0.07, M['iron'], r2=0.05, seg=10),
         cyl('head', 0.22, 0.35, (0, 0, 5.35), M['iron'], r2=0.3, seg=12),
         cyl('glow', 0.24, 0.06, (0, 0, 5.17), M['lamp_glow'], seg=12),
         cyl('cap', 0.12, 0.12, (0, 0, 5.58), M['iron'], seg=10)]
    return join(p, 'LampModern')


# ================================================================ props

def prop_planter_bench():
    """Wooden planter box with a seat rim and flowers, like the ones along the gallery."""
    p = [box('pb_box', (2.4, 1.2, 0.55), (0, 0, 0.275), M['bench_wood'], smooth=False),
         box('pb_rim', (2.6, 1.4, 0.07), (0, 0, 0.58), M['wood'], smooth=False),
         box('pb_soil', (2.2, 1.0, 0.04), (0, 0, 0.6), M['bark'], smooth=False)]
    for i in range(int(2.4 / 0.3)):
        p.append(box('pb_slat', (0.02, 1.22, 0.5), (-1.2 + 0.15 + i * 0.3, 0, 0.27), M['wood'], smooth=False))
    for _ in range(30):
        x, y = rng.uniform(-1.0, 1.0), rng.uniform(-0.45, 0.45)
        p.append(ico('pb_leaf', rng.uniform(0.12, 0.2), (x, y, 0.72), M[rng.choice(['leaf', 'leaf_dark'])], subdiv=1))
    for _ in range(36):
        x, y = rng.uniform(-1.05, 1.05), rng.uniform(-0.5, 0.5)
        p.append(ico('pb_bloom', rng.uniform(0.05, 0.08), (x, y, 0.82 + rng.uniform(0, 0.15)),
                     M[rng.choice(['flower_red', 'flower_pink', 'flower_yellow', 'flower_white'])], subdiv=1))
    return join(p, 'PlanterBench')


def pendant_line(a, b, n=3, sag=0.6, name='LampLine'):
    """Steel cable across the square with hanging lamps (photo 3)."""
    a, b = V(a), V(b)
    p = []
    pts = [a.lerp(b, i / 16) - V((0, 0, sag * 4 * (i / 16) * (1 - i / 16))) for i in range(17)]
    for i in range(16):
        p.append(tube('cable', pts[i], pts[i + 1], 0.012, M['iron'], seg=4))
    for k in range(n):
        t = (k + 1) / (n + 1)
        c = a.lerp(b, t) - V((0, 0, sag * 4 * t * (1 - t)))
        p.append(tube('drop', c, c - V((0, 0, 0.5)), 0.01, M['iron'], seg=4))
        p.append(cyl('shade', 0.36, 0.3, c - V((0, 0, 0.65)), M['mullion'], r2=0.08, seg=16))
        p.append(sphere('bulb', 0.13, c - V((0, 0, 0.82)), M['lamp_glow'], seg=10, rings=6))
    return join(p, name)


# ================================================================ scene assembly

def build():
    lib.reset_scene()
    make_materials()
    root = lib.empty('Square')
    groups = {k: lib.empty(k, parent=root) for k in ('Ground', 'Buildings', 'Props', 'Markers')}

    # Game frame (player looks +Y): ahead = the gallery, right = the gemeentehuis, left = the street from the
    # photo with the floor fountain, behind = the ijssalon where you sit. (In Nijverdal you look west.)

    # --- ground: street klinkers everywhere, grey slabs on the square, salmon pavers along the gallery,
    #     warm klinkers with brown stripes on the fountain side
    g = [box('Ground_Klinkers', (160, 130, 0.2), (0, 15, -0.1), M['klinkers'], smooth=False),
         box('Square_Slabs', (28.0, 34.0, 0.06), (2.0, 3.0, 0.0), M['slabs'], smooth=False),
         box('Gallery_Pavers', (19.8, 3.6, 0.07), (-1.4, 18.2, 0.0), M['pavers'], smooth=False),
         box('Road_Klinkers', (7.5, 6.0, 0.08), (12.25, 17.0, 0.0), M['klinkers'], smooth=False),
         box('Fountain_Klinkers', (4.4, 24.0, 0.07), (-9.8, -2.0, 0.0), M['klinkers'], smooth=False)]
    for o in g:
        lib.box_uv(o, 2.0)
    stripes = []
    for y in range(-13, 10, 3):
        stripes.append(box('stripe', (4.4, 0.16, 0.02), (-9.8, y + 0.5, 0.04), M['stripe_brown'], smooth=False))
    for x in (-11.2, -8.4):
        stripes.append(box('stripe', (0.16, 24.0, 0.02), (x, -2.0, 0.04), M['stripe_brown'], smooth=False))
    g.append(join(stripes, 'Ground_Stripes'))
    for o in g:
        lib.set_parent(o, groups['Ground'])

    # --- ahead: the gallery block with the corner tower on the left, its wing along the west street
    galerij('Galerij', (-11.3, 20), (8.5, 20), (0, -1), floors=4, arcade=True,
            flags=((0.3, 7.4), (0.75, 10.3)))
    # beyond the gallery's end: the red market road (x 8.5..16), then the gemeentehuis on the corner
    galerij('Road_W', (8.5, 35), (8.5, 60), (1, 0), depth=12, floors=3, arcade=False, brick='brick_red', shop_chance=0.5)
    galerij('Road_E', (16, 17), (16, 60), (-1, 0), depth=12, floors=3, arcade=False, brick='brick_brown', shop_chance=0.5)
    galerij('Cap_N', (0, 62), (25, 62), (0, -1), depth=10, floors=3, arcade=False, brick='brick_red', shop_chance=0.0)
    corner_tower((-15.3, 23.9))
    galerij('Galerij_West', (-19.6, 20), (-60, 20), (0, -1), depth=12, floors=4, arcade=False, flags=((0.2, 7.0),))
    galerij('Street_W_S', (-12, 10), (-60, 10), (0, 1), depth=12, floors=3, arcade=False, brick='brick_red', shop_chance=0.5)
    galerij('Cap_W', (-60, 10), (-60, 20), (1, 0), depth=10, floors=3, arcade=False, brick='brick_brown', shop_chance=0.0)

    # --- left: the shop row from the street photo (near -> far)
    shop_house('Left_Eetcafe', (-12, -14), (-12, -5), (1, 0), 'grey_brick', ['EETCAFE GULLE GOZER', 'WAFELHUIS'],
               frames='frame_white')
    shop_house('Left_Kado', (-12, -5), (-12, 2), (1, 0), 'beige_grey', ['KADO KABINET'], wood_fascia=True, planters=True,
               frames='frame_white')
    shop_house('Left_Optiek', (-12, 2), (-12, 10), (1, 0), 'brick_red', ['OUDE LAARS OPTIEK'], frames='frame_green',
               eave=True, win_canopies=True, fascia='sign_black')

    # --- behind: the modern block with the ijssalon you sit in front of
    modern_block('IJssalon_Block', (16, -14), (-14, -14), (0, 1), floors=2, shops=('SCHOENEN', 'IJSSALON HENRI', 'KAPPER'),
                 cone=True)

    # --- right: the gemeentehuis, the alley behind it, streets beyond
    gemeentehuis((16, -13), (16, 16), (-1, 0))

    for o in BUILDINGS:
        lib.set_parent(o, groups['Buildings'])

    # --- props
    props = []
    P = lambda src, loc, rz=0.0, s=1.0: props.append(instance(src, src.name + '_i', loc, rz, s))
    tree, binm, rack = sq.prop_tree(), sq.prop_bin(), sq.prop_rack()
    table, chair = sq.prop_table(), sq.prop_chair()
    pbench, lamp = prop_planter_bench(), prop_lamp_modern()
    parasols = {f: sq.prop_parasol(f) for f in ('fab_cream', 'fab_black')}
    bikes = [sq.prop_omafiets(f) for f in ('bike_black', 'bike_green', 'bike_blue', 'bike_red')]
    templates = [tree, binm, rack, table, chair, pbench, lamp] + list(parasols.values()) + bikes

    for x, y, s in ((10.5, -11.4, 1.05), (-9.3, -12.0, 0.95)):
        P(tree, (x, y, 0), rng.uniform(0, 6.28), s)
    for x, y, rz in ((-8.0, 15.6, 0.0), (12.4, -12.6, 0.0)):
        P(pbench, (x, y, 0), rz)
    for x, y in ((-6.2, -10.0), (6.0, -10.0), (14.6, 4.0), (-8.6, 2.4)):
        P(binm, (x, y, 0))
    for x, y in ((-8.3, -4.0), (-8.6, 7.0), (14.6, 1.0)):
        P(lamp, (x, y, 0))
    # bike parking in front of the ijssalon block
    for (x, y, rz) in ((5.6, -13.0, 0.0),):
        P(rack, (x, y, 0), rz)
        for i in range(6):
            if rng.random() < 0.85:
                off = V((math.cos(rz), math.sin(rz))) * (i * 0.7)
                P(rng.choice(bikes), (x + off.x, y + off.y, 0), rz + math.pi / 2 + rng.uniform(-0.08, 0.08))

    # the floor fountain and the big boulders (left)
    ff = floor_fountain((-10.0, 2.0))
    props.append(ff)
    for k, (x, y, r) in enumerate(((-8.8, -6.0, 0.55), (-10.9, -8.7, 0.6), (-11.2, -3.6, 0.5), (-9.0, 8.0, 0.65))):
        b = boulder(f'Boulder_{k}', r, k)
        b.location = (x, y, 0)
        b.rotation_euler = (0, 0, rng.uniform(0, 6.28))
        props.append(b)

    def terrace(cx, cy, along, n, fabric, skip=(), gap=1.9, umbrellas=None):
        ax = V((math.cos(along), math.sin(along)))
        for i in range(n):
            if i in skip:
                continue
            c = V((cx, cy)) + ax * ((i - (n - 1) / 2) * gap)
            P(table, (c.x, c.y, 0))
            for s in (-1, 1):
                q = c + ax * (s * 0.55)
                P(chair, (q.x, q.y, 0), along + (math.pi if s > 0 else 0))
            if (i % 2 == 0) if umbrellas is None else (i in umbrellas):
                P(parasols[fabric], (c.x, c.y, 0), rng.uniform(0, 1))

    terrace(0, -10.9, 0.0, 5, 'fab_cream', skip=(2,))           # IJssalon Henri (the middle table is yours)
    terrace(1.0, 17.5, 0.0, 7, 'fab_cream', skip=(3,), umbrellas=(0, 6))  # in front of the gallery, gap for riders
    terrace(14.6, -7.5, math.pi / 2, 4, 'fab_black')             # gemeentehuis café, on your side of the square

    # the market on the red road between the gallery and the gemeentehuis, with a lane down the middle
    stalls = {k: prop_market_stall(k, c) for k, c in (('fruit', 'fab_red'), ('kaas', 'fab_yellow'), ('bloemen', 'fab_green'),
                                                       ('wafels', 'fab_blue'))}
    templates += list(stalls.values())
    kinds = list(stalls)
    for j, y in enumerate((27.5, 31.0, 34.5, 38.0, 41.5)):
        P(stalls[kinds[j % 4]], (9.75, y, 0), math.pi / 2)
    for j, y in enumerate((21.0, 24.5, 28.0, 31.5, 35.0, 38.5)):
        P(stalls[kinds[(j + 2) % 4]], (14.65, y, 0), -math.pi / 2)
    small = sq.prop_table(0.23, 'PlayerTableMesh')
    templates.append(small)
    props.append(instance(small, 'Player_Table', (-0.38, -11.0, 0)))
    props.append(instance(chair, 'Player_Chair', (0, -11.55, 0), math.pi / 2))
    props.append(instance(parasols['fab_cream'], 'Player_Parasol', (-1.1, -11.6, 0)))

    # hanging lamps across the square and some Koningsdag bunting
    props.append(pendant_line((-12.0, 0.5, 6.6), (16.0, 0.5, 7.4), 3, name='LampLine_S'))
    props.append(pendant_line((-12.0, 8.5, 6.6), (16.0, 8.5, 7.4), 3, name='LampLine_N'))
    props.append(sq.bunting((-12.0, 9.6, 6.6), (16.0, 12.5, 7.2), 1.2, 'Bunting_N'))

    for o in props:
        lib.set_parent(o, groups['Props'])
    for t in templates:
        t.location = (0, 0, -100)

    # --- markers for the game (same names as the old square)
    markers = {
        'PlayerEye': (0, -11.55, 1.2),
        'Spawn_West': (-56, 15, 0), 'Spawn_Markt': (12.2, 58, 0),
        'Square_Center': (3, 3.5, 0),
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
    print(f'[dunant] buildings: {len(BUILDINGS)}, objects: {len(objs)}, triangles: {lib.tri_count(meshes)}')
    out = os.path.join(ROOT, 'assets', 'models', 'dunant.glb')
    lib.export_glb(out, objs)
    print(f'[dunant] exported {out} ({os.path.getsize(out) / 1e6:.1f} MB)')
    for t in templates:
        t.hide_render = True
    if '--no-render' in argv:
        return
    lib.preview_stage(scene, size=(1600, 900))
    bpy.data.objects['PreviewGround'].hide_render = True
    sun = bpy.data.objects['Sun']
    sun.rotation_euler = (math.radians(55), 0, math.radians(-150))
    sun.data.energy = 6.0
    bpy.data.objects['Fill'].hide_render = True
    rdir = os.path.join(ROOT, 'renders', 'dunant')
    eye = V((0, -11.55, 1.2))
    shots = [
        ('01_player_view', eye, eye + V((0, 10, 0.5)), 20),
        ('02_overview', (-8, -34, 36), (2, 8, 0), 24),
        ('03_look_left', eye, eye + V((-10, 2, 0.2)), 22),
        ('04_look_right', eye, eye + V((10, 3, 0.3)), 22),
        ('05_gallery', (4.3, 10.0, 1.7), (-6, 21, 4.0), 24),
        ('06_in_arcade', (7.8, 22.0, 1.6), (-10, 22.0, 1.6), 22),
        ('07_market', (12.2, 15.0, 1.7), (12.2, 40, 1.5), 22),
    ]
    if 'one' in argv:
        shots = shots[:2]
    for name, loc, tgt, lens in shots:
        lib.render(scene, lib.camera('Cam_' + name, tuple(loc), tuple(tgt), lens), os.path.join(rdir, name + '.png'))


if __name__ == '__main__':
    main()
