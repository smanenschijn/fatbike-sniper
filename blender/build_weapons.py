"""First-person weapon viewmodels (with hands) + the ice cream on the player's table.

Viewmodel space: camera at the origin looking +X, +Z up. Each weapon is modelled in its own
frame (barrel along +X, origin at the trigger/grip) and its root is placed in camera space.
Separate named parts can be animated in-game (pump, bolt, bands, rocket, stone, shell).

Run:  Blender -b -P blender/build_weapons.py [-- --no-render]
"""
import math
import os
import sys

import bmesh
import bpy
from mathutils import Euler, Vector

sys.path.insert(0, os.path.dirname(__file__))
import lib  # noqa: E402
import vmkit  # noqa: E402
from lib import (basis, box, capsule, cyl, extrude_profile, join, lathe, material, orient_basis,  # noqa: E402
                 place, sphere, subsurf, text_mesh, torus, tube)

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
V = Vector
M = {}


def make_materials():
    S = vmkit.smart
    M.update({
        'skin': S('PlayerSkin', '#e2ab86', 'skin', rough=0.5, bevel=0.003),
        'nail': S('Nail', '#f3d2c0', 'plain', rough=0.25, dirt=0.3),
        'hoodie': S('Hoodie', '#2f4878', 'fabric', rough=0.9, bevel=0.006),
        'hoodie_rib': S('HoodieRib', '#253a62', 'fabric', rough=0.9, bevel=0.002),
        'watch_strap': S('WatchStrap', '#1c1c1c', 'rubber', rough=0.6),
        'watch_face': S('WatchFace', '#f4f1e8', 'plain', rough=0.2),
        'steel': S('GunSteel', '#2c2f34', 'metal', rough=0.32, metal=0.85),
        'steel_light': S('GunSteelLight', '#9aa0a8', 'metal', rough=0.25, metal=1.0),
        'blued': S('GunBlued', '#1e2430', 'metal', rough=0.28, metal=0.9),
        'wood': S('GunWood', '#8a5229', 'wood', rough=0.38),
        'wood_dark': S('GunWoodDark', '#5a3218', 'wood', rough=0.45),
        'polymer': S('GunPolymer', '#2a2c2a', 'polymer', rough=0.6),
        'rubber': S('GunRubber', '#151515', 'rubber', rough=0.85),
        'olive': S('Olive', '#5f6e3b', 'paint', rough=0.55, bevel=0.006),
        'olive_dark': S('OliveDark', '#434e2a', 'paint', rough=0.6, bevel=0.006),
        'yellow': S('HazardYellow', '#f4c430', 'paint', rough=0.5),
        'black': S('HazardBlack', '#161616', 'plain', rough=0.5),
        'rocket': S('RocketRed', '#d9442b', 'paint', rough=0.35),
        'white': S('RocketWhite', '#f5f3ec', 'paint', rough=0.4),
        'brass': S('Brass', '#d2aa45', 'metal', rough=0.25, metal=1.0),
        'shell_red': S('ShellRed', '#c2262a', 'polymer', rough=0.4),
        'lens': material('ScopeLens', '#2e6a9e', rough=0.03, metal=0.4, coat=1.0, emission='#1a4a7a', strength=0.3),
        'band': S('SlingBand', '#e0a83a', 'plain', rough=0.5),
        'leather': S('Leather', '#6e3f20', 'rubber', rough=0.7),
        'stone': S('SlingStone', '#8c8a83', 'polymer', rough=0.85),
        'sling_wood': S('SlingWood', '#a46a35', 'wood', rough=0.5, wear=0.55, grain='Y'),
        'tape': S('GripTape', '#c43a2a', 'fabric', rough=0.7),
        # sniper
        'sn_metal': S('SniperMetal', '#24282f', 'metal', rough=0.34, metal=0.9),
        'sn_steel': S('SniperSteel', '#3b4048', 'metal', rough=0.3, metal=0.95),
        'sn_scope': S('SniperScope', '#1b1d21', 'metal', rough=0.45, metal=0.55),
        'sn_stock': S('SniperStock', '#b8986a', 'polymer', rough=0.55, bevel=0.006),
        'sn_orange': S('SniperOrange', '#f07a1e', 'paint', rough=0.4),
        'sn_grip': S('SniperGrip', '#2b2a27', 'rubber', rough=0.8),
        'sn_lens': material('SniperLens', '#1f2f6a', rough=0.04, metal=0.6, coat=1.0, emission='#2a1f5a', strength=0.15),
        'sign_red': S('SignRed', '#d4202a', 'plain', rough=0.35, dirt=0.4),
        'sign_white': S('SignWhite', '#f4f2ea', 'plain', rough=0.35, dirt=0.4),
        'ink': S('Ink', '#16171a', 'plain', rough=0.5, dirt=0.0),
        'scratch': S('Scratch', '#efe4c8', 'plain', rough=0.5, dirt=0.0),
        'stencil': S('StencilWhite', '#ece8dc', 'plain', rough=0.6, dirt=0.3),
        'flag_blue': S('FlagBlue', '#21468b', 'plain', rough=0.6, dirt=0.3),
        'duct': S('DuctTape', '#a3a8ad', 'fabric', rough=0.45, bevel=0.002),
        'twine': S('Twine', '#c9a66b', 'fabric', rough=0.8, bevel=0.002),
        'cord': S('Paracord', '#c8362a', 'fabric', rough=0.75, bevel=0.002),
        'soot': S('Soot', '#1a1714', 'plain', rough=0.95, dirt=0.0),
        'frost': S('Frost', '#e3f4ff', 'polymer', rough=0.6, dirt=0.2),
        'coolant': S('Coolant', '#6fcbea', 'paint', rough=0.25),
        'waffle': S('WaffleCone', '#d9a050', 'waffle', rough=0.7),
        'canvas': S('Canvas', '#8c8458', 'fabric', rough=0.85, bevel=0.003),
        'cable': S('Cable', '#202124', 'rubber', rough=0.5, bevel=0.002),
        'knot': S('WoodKnot', '#5b3216', 'wood', rough=0.6),
        'pebble': S('Pebble', '#8f8b84', 'polymer', rough=0.75, wear=0.3),
        'spr_pink': S('SprinklePink', '#ff5fa2', 'plain', rough=0.4, dirt=0.0),
        'spr_yellow': S('SprinkleYellow', '#ffd23f', 'plain', rough=0.4, dirt=0.0),
        'spr_blue': S('SprinkleBlue', '#3fa7ff', 'plain', rough=0.4, dirt=0.0),
        'spr_white': S('SprinkleWhite', '#fffaf0', 'plain', rough=0.4, dirt=0.0),
        'spr_green': S('SprinkleGreen', '#7bd36a', 'plain', rough=0.4, dirt=0.0),
        'choco_dip': S('ChocoDip', '#4a2614', 'plain', rough=0.2, dirt=0.3),
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
        # ice cream machine gun
        'mint': S('IceMint', '#8fdcc0', 'paint', rough=0.35),
        'mint_dark': S('IceMintDark', '#5bb79a', 'paint', rough=0.4),
        'pink': S('IcePink', '#ff7fae', 'paint', rough=0.35),
        'cream_paint': S('IceCream', '#fff1d0', 'paint', rough=0.4),
        'pistachio': material('Pistachio', '#a9d86e', rough=0.65, sss=0.2),
        'lemon': material('Lemon', '#f8e36a', rough=0.65, sss=0.2),
        'chrome': S('Chrome', '#d9dde3', 'metal', rough=0.12, metal=1.0),
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
        rad = px * math.cos(end_a) + py * math.sin(end_a)
        curl = (py * math.cos(end_a) - px * math.sin(end_a)) * sign
        nail = sphere('nail', w * 0.72, mat=M['nail'], scale=(1.0, 1.3, 0.32), seg=12, rings=6)
        p.append(orient_basis(nail, basis(axis, rad), tip + rad * w * 0.78 - curl * w * 0.35))
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
    p += sleeve(wrist, elbow, cuff_at=0.055 if watch else 0.03)
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


def shaped_cyl(name, length, radius, mat=None, seg=32, rings=12, caps=True):
    """Cylinder along local Z (centred); radius(t, a) with t 0..1 along the length and a the angle."""
    bm = bmesh.new()
    grid = []
    for i in range(rings + 1):
        t = i / rings
        z = (t - 0.5) * length
        row = []
        for j in range(seg):
            a = 2 * math.pi * j / seg
            r = radius(t, a)
            row.append(bm.verts.new((r * math.cos(a), r * math.sin(a), z)))
        grid.append(row)
    for a, b in zip(grid, grid[1:]):
        for j in range(seg):
            k = (j + 1) % seg
            bm.faces.new((a[j], a[k], b[k], b[j]))
    if caps:
        bm.faces.new(list(reversed(grid[0])))
        bm.faces.new(grid[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return lib.obj_from_bm(bm, name, mat)


def sweep(name, pts, r, mat=None, seg=10, caps=True, up=None, flat=1.0):
    """Tube along a polyline. r: radius or r(t). up: keeps the cross-section's width axis (straps); flat squashes it."""
    pts = [V(p) for p in pts]
    n_pts = len(pts)
    bm = bmesh.new()
    rings = []
    nrm = None
    for i, p in enumerate(pts):
        t = (pts[min(i + 1, n_pts - 1)] - pts[max(i - 1, 0)]).normalized()
        ref = V(up) if up is not None else (nrm if nrm is not None else t.orthogonal())
        nrm = (ref - t * ref.dot(t)).normalized()
        b = t.cross(nrm)
        rr = r(i / (n_pts - 1)) if callable(r) else r
        rings.append([bm.verts.new(p + (nrm * math.cos(a) + b * math.sin(a) * flat) * rr)
                      for a in (2 * math.pi * j / seg for j in range(seg))])
    for ra, rb in zip(rings, rings[1:]):
        for j in range(seg):
            k = (j + 1) % seg
            bm.faces.new((ra[j], ra[k], rb[k], rb[j]))
    if caps:
        bm.faces.new(list(reversed(rings[0])))
        bm.faces.new(rings[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return lib.obj_from_bm(bm, name, mat)


def bezier(p0, p1, p2, p3, n=24):
    p0, p1, p2, p3 = V(p0), V(p1), V(p2), V(p3)
    return [p0 * (1 - t) ** 3 + p1 * 3 * t * (1 - t) ** 2 + p2 * 3 * t * t * (1 - t) + p3 * t ** 3
            for t in (i / (n - 1) for i in range(n))]


def helix(p1, p2, r, turns, n_per_turn=16, phase=0.0):
    """Points spiralling around the segment p1 -> p2 (cord wraps, coiled cables)."""
    p1, p2 = V(p1), V(p2)
    ax = (p2 - p1).normalized()
    u = ax.orthogonal().normalized()
    w = ax.cross(u)
    n = max(2, int(turns * n_per_turn))
    return [p1 + (p2 - p1) * (i / n) + (u * math.cos(phase + turns * 2 * math.pi * i / n)
                                         + w * math.sin(phase + turns * 2 * math.pi * i / n)) * r for i in range(n + 1)]


def arc_shell(name, r, thick, length, a0, a1, mat=None, seg=24, rings=2):
    """Part of a thick-walled tube along local Z (angles a0..a1), e.g. a barrel heat shield."""
    bm = bmesh.new()
    grid = []
    for i in range(rings + 1):
        z = (i / rings - 0.5) * length
        row = []
        for j in range(seg + 1):
            a = a0 + (a1 - a0) * j / seg
            row.append((bm.verts.new((r * math.cos(a), r * math.sin(a), z)),
                        bm.verts.new(((r - thick) * math.cos(a), (r - thick) * math.sin(a), z))))
        grid.append(row)
    for ra, rb in zip(grid, grid[1:]):
        for j in range(seg):
            bm.faces.new((ra[j][0], ra[j + 1][0], rb[j + 1][0], rb[j][0]))
            bm.faces.new((rb[j][1], rb[j + 1][1], ra[j + 1][1], ra[j][1]))
        for j in (0, seg):
            bm.faces.new((ra[j][0], rb[j][0], rb[j][1], ra[j][1]))
    for row in (grid[0], grid[-1]):
        for j in range(seg):
            bm.faces.new((row[j][0], row[j][1], row[j + 1][1], row[j + 1][0]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return lib.obj_from_bm(bm, name, mat)


def lumpy(name, r, loc, mat, amp=0.12, freq=2.5, seed=0, scale=(1, 1, 1), seg=24, rings=12):
    """A sphere with noise displacement (pebbles, ice-cream scoops)."""
    from mathutils import noise
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=rings, radius=r)
    off = V((seed * 7.31, seed * 3.17, seed * 5.53))
    for v in bm.verts:
        d = v.co.normalized()
        v.co = d * r * (1 + amp * noise.noise(d * freq + off))
    return place(lib.obj_from_bm(bm, name, mat), loc, None, scale)


def tube_text(body, size, x, R, phi, mat, extrude=0.0006):
    """Stencil text lying on a tube along X (radius R), at angle phi from +Y towards +Z; reads front-to-back from +Y."""
    rot = (Euler((phi, 0, 0)).to_matrix() @ Euler(SIDE_Y).to_matrix()).to_euler()
    pos = V((x, math.cos(phi) * (R + extrude), math.sin(phi) * (R + extrude)))
    return text_mesh('stencil', body, size, pos, rot=rot, mat=mat, extrude=extrude)


def tube_decal(o, x, R, phi, lift=0.0006):
    """Lay a flat object (made in the XY plane, facing +Z) on a tube along X at angle phi."""
    o.rotation_euler = (Euler((phi - math.pi / 2, 0, 0)).to_matrix() @ o.rotation_euler.to_matrix()).to_euler()
    o.location = (x, math.cos(phi) * (R + lift), math.sin(phi) * (R + lift))
    return o


def sign(c, r, rot, kind='25'):
    """Round Dutch road-sign sticker in the XY plane rotated by `rot`: '25' speed limit or 'fiets' (no bicycles)."""
    R = Euler(rot).to_matrix()
    c = V(c)
    nz = R @ V((0, 0, 1))

    def flat(o, lift):
        o.rotation_euler = rot
        o.location = c + nz * lift
        return o
    out = [flat(cyl('sign_ring', r, 0.0012, mat=M['sign_red'], seg=40), 0.0),
           flat(cyl('sign_disc', r * 0.78, 0.0012, mat=M['sign_white'], seg=40), 0.0004)]
    if kind == 'fiets':   # little black bicycle: two wheels, frame, saddle, handlebar
        s = r * 0.26
        for wx in (-1, 1):
            w = torus('sign_wheel', s, s * 0.16, mat=M['ink'], segU=24, segV=4, rz=s * 0.05)
            out.append(flat(w, 0.0009))
            w.location = c + nz * 0.0009 + R @ V((wx * s * 1.15, -s * 0.25, 0))
        for (x0, y0), (x1, y1) in (((-1.15, -0.25), (0.0, -0.25)), ((0.0, -0.25), (0.55, 0.55)), ((-1.15, -0.25), (-0.4, 0.55)),
                                   ((-0.4, 0.55), (0.55, 0.55)), ((0.55, 0.55), (1.15, -0.25)), ((0.55, 0.55), (0.45, 0.9))):
            a, b = c + R @ V((x0 * s, y0 * s, 0)), c + R @ V((x1 * s, y1 * s, 0))
            out.append(tube('sign_bar', a + nz * 0.0009, b + nz * 0.0009, s * 0.09, M['ink'], seg=6))
    return out


def sleeve(wrist, elbow, cuff_at=0.03):
    """Pushed-up hoodie sleeve: ribbed cuff, a rolled lip and bunched fleece up to (past) the elbow."""
    wrist, elbow = V(wrist), V(elbow)
    f = (elbow - wrist).normalized()
    a = wrist + f * cuff_at
    end = elbow + f * 0.06
    L = (end - a).length
    p = [capsule('forearm', wrist - f * 0.02, a + f * 0.06, 0.032, 0.036, M['skin'])]
    cuff = shaped_cyl('cuff', 0.04, lambda t, ang: 0.038 * (1 + 0.035 * math.cos(ang * 22)) * (1 + 0.08 * t),
                      M['hoodie_rib'], seg=88, rings=4, caps=False)
    p.append(lib.orient(cuff, a, a + f * 0.04))
    lip = torus('sleeve_lip', 0.043, 0.011, mat=M['hoodie'], segU=40, segV=10)
    p.append(lib.orient(lip, a + f * 0.04, a + f * 0.05))

    def bunch(t, ang):   # tilted folds, strongest near the cuff where the sleeve is pushed up
        x = t * L
        fold = max(0.0, math.sin(x / 0.034 * 2 * math.pi + 0.9 * math.cos(ang) + 0.5 * math.sin(2 * ang + 1.3)))
        return (0.05 + 0.016 * t) * (1 + 0.09 * fold * (1.2 - t) + 0.015 * math.sin(3 * ang + x * 40))
    body = shaped_cyl('sleeve', L - 0.04, bunch, M['hoodie'], seg=48, rings=64)
    p.append(lib.orient(body, a + f * 0.04, end))
    return p


# ================================================================ weapons (local frame: +X forward)

def katapult():
    """Hand-carved forked branch: grain and a knot, red paracord grip, latex tubing tied with twine,
    a stitched leather pouch with a pebble, carved tally notches and a Dutch-flag ribbon."""
    W = M['sling_wood']
    frame = []
    # handle + fork as one grown branch: a swept handle and two curved prongs that thin towards the tips
    frame.append(sweep('handle', bezier((0, 0, -0.108), (0.002, 0, -0.06), (-0.002, 0, 0.0), (0, 0, 0.032), 16),
                       lambda t: 0.0185 + 0.0035 * t + 0.0015 * math.sin(t * 9), W, seg=20))
    frame.append(sphere('handle_end', 0.0186, (0, 0, -0.108), W, scale=(1, 1, 0.7), seg=20, rings=10))
    frame.append(sphere('yoke', 0.024, (0, 0, 0.034), W, scale=(0.95, 1.35, 1.05), seg=24, rings=12))
    tips, prongs = [], {}
    for s in (-1, 1):
        pts = prongs[s] = bezier((0, s * 0.008, 0.035), (0.004, s * 0.045, 0.06), (0.004, s * 0.07, 0.11), (0.0, s * 0.072, 0.178), 24)
        frame.append(sweep('prong', pts, lambda t: 0.0165 - 0.005 * t + 0.0012 * math.sin(t * 7 + s), W, seg=18))
        frame.append(sphere('prong_tip', 0.0118, pts[-1], W, scale=(1, 1, 0.75), seg=16, rings=8))
        tie = pts[-1] - V((0, 0, 0.022))
        # groove + twine lashing where the tubing is tied on
        frame.append(sweep('lashing', helix(tie - V((0, 0, 0.008)), tie + V((0, 0, 0.008)), 0.0135, 4, 12),
                           0.0022, M['twine'], seg=6))
        tips.append(tie)
    frame.append(sphere('knot', 0.0065, (-0.0175, 0.004, -0.035), M['knot'], scale=(0.6, 1, 1.4), seg=12, rings=8))
    frame.append(torus('knot_ring', 0.0065, 0.0016, (-0.0172, 0.004, -0.035), M['knot'], rot=(0, -math.pi / 2, 0), segU=16, segV=4))
    # red paracord wrapped round the grip, with a knot at each end
    frame.append(sweep('cord', helix((0, 0, -0.098), (0, 0, -0.012), 0.0222, 13, 16), 0.0033, M['cord'], seg=8))
    for z in (-0.099, -0.011):
        frame.append(sphere('cord_knot', 0.006, (0.018, 0.008, z), M['cord'], scale=(1, 1.2, 0.9), seg=10, rings=6))
    # tally notches carved into the back of the right prong (the side facing the player)
    for i in range(4):
        z = 0.085 + i * 0.011
        frame.append(box('notch', (0.004, 0.017, 0.0025), (-0.013, -0.058 - i * 0.0012, z), M['knot'], rot=(0.15, 0, 0), bevel=0.001, segs=1))
    # Dutch flag ribbon tied below the left tip
    rib_at = prongs[1][14]
    frame.append(sweep('ribbon_tie', helix(rib_at - V((0, 0, 0.004)), rib_at + V((0, 0, 0.004)), 0.0152, 2, 10), 0.002, M['sign_white'], seg=6))
    for i, m in enumerate(('sign_red', 'sign_white', 'flag_blue')):
        path = [rib_at + V((-0.008, 0.011, -0.002 - i * 0.0055)) + V((-0.008 * t, 0.022 * t, -0.03 * t * t))
                for t in (k / 8 for k in range(9))]
        frame.append(sweep('ribbon', path, 0.0028, M[m], seg=6, up=(0, 0, 1), flat=0.25))

    pouch_c = V((-0.17, 0, 0.115))
    bands = []
    for s, t in zip((-1, 1), tips):   # latex tubing, slightly thicker at the fork
        end = pouch_c + V((0.0, s * 0.026, 0))
        bands.append(sweep('band', [t + (end - t) * (k / 8) for k in range(9)], lambda u: 0.0062 - 0.0016 * u, M['band'], seg=10))
        bands.append(sweep('band_tie', helix(end + (t - end).normalized() * 0.004, end + (t - end).normalized() * 0.012,
                                             0.0058, 2, 10), 0.0016, M['twine'], seg=6))
    # leather pouch: a cupped strip around the pebble, stitched along both edges
    pouch = []
    cup = [pouch_c + V((-0.006 - 0.012 * math.cos(math.pi * (k / 16 - 0.5)), 0.028 * math.sin(math.pi * (k / 16 - 0.5)), 0)) for k in range(17)]
    pouch.append(sweep('pouch', cup, 0.016, M['leather'], seg=12, up=(0, 0, 1), flat=0.22))
    for k in range(1, 16, 2):
        for dz in (-0.0125, 0.0125):
            p = cup[k] + V((0, 0, dz))
            pouch.append(box('stitch', (0.0035, 0.0085, 0.0012), p, M['twine'], rot=(0, 0, math.atan2(cup[k + 1].y - cup[k - 1].y, cup[k + 1].x - cup[k - 1].x)), segs=1))
    stone = [lumpy('stone', 0.018, pouch_c + V((0.012, 0, 0)), M['pebble'], amp=0.14, freq=1.8, seed=3, scale=(1, 1.05, 0.88), seg=20, rings=10)]
    parts = {'Katapult_Frame': frame, 'Katapult_Bands': bands, 'Katapult_Pouch': pouch, 'Katapult_Stone': stone}
    # cartoon-size the slingshot around the gripping hand
    K, pivot = 2.0, V((0, 0, -0.045))
    for objs in parts.values():
        for o in objs:
            o.location = pivot + (V(o.location) - pivot) * K
            o.scale = V(o.scale) * K
    pouch_c = pivot + (pouch_c - pivot) * K
    hands = (grip_hand((0, 0, -0.045), (0, 0, -1), (0, 1, 0), 0.02, (1, 0, 0), (-0.27, 0.13, -0.33), watch=True)
             + grip_hand(pouch_c + V((-0.03, 0, 0.0)), (0, 0, -1), (0, -1, 0), 0.012, (1, 0, 0), (-0.42, -0.22, -0.2)))
    return parts, hands


def shell_round(name, c, axis_rot=(0, 0, 0), L=0.06):
    """12-gauge shell along local +Z from c: red ribbed hull, star crimp, brass head with rim and primer."""
    R = Euler(axis_rot).to_matrix()
    c = V(c)

    def at(o, dz):
        o.rotation_euler = axis_rot
        o.location = c + R @ V((0, 0, dz))
        return o
    hull = shaped_cyl(name + '_hull', L, lambda t, a: 0.0108 * (1 + 0.025 * math.cos(a * 14)), M['shell_red'], seg=56, rings=2, caps=False)
    crimp = shaped_cyl(name + '_crimp', 0.004, lambda t, a: 0.0108 * (1 - 0.35 * t * (0.6 + 0.4 * math.cos(a * 6))), M['shell_red'], seg=48, rings=2)
    return [at(hull, L / 2), at(crimp, L + 0.002),
            at(cyl(name + '_head', 0.0113, 0.016, mat=M['brass'], seg=28), 0.006),
            at(cyl(name + '_rim', 0.0125, 0.0025, mat=M['brass'], seg=28), -0.0008),
            at(cyl(name + '_primer', 0.0035, 0.001, mat=M['steel_light'], seg=16), -0.0025)]


def shotgun():
    """Pump gun 'Omafiets 12': ventilated heat shield, milled receiver with a side-saddle on the player's side,
    grooved walnut pump, a duct-taped stock and a 'no bicycles' sticker."""
    S, Wd = M['steel'], M['wood']
    body = [cyl('barrel', 0.019, 0.66, (0.44, 0, 0.06), S, rot=RX, seg=32),
            cyl('muzzle', 0.0215, 0.03, (0.77, 0, 0.06), M['blued'], rot=RX, seg=32),
            cyl('bore', 0.0145, 0.004, (0.7855, 0, 0.06), M['black'], rot=RX, seg=24),
            cyl('magtube', 0.016, 0.6, (0.4, 0, 0.022), S, rot=RX, seg=24),
            cyl('magcap', 0.0185, 0.03, (0.715, 0, 0.022), M['blued'], rot=RX, seg=24),
            torus('cap_loop', 0.008, 0.0022, (0.725, 0, 0.004), S, rot=(math.pi / 2, 0, 0), segU=16, segV=6),
            box('barrel_clamp', (0.025, 0.03, 0.06), (0.69, 0, 0.041), M['blued'], bevel=0.006)]
    # ventilated heat shield over the barrel with a sight rib and a fat brass bead
    body.append(place(arc_shell('heat_shield', 0.026, 0.0025, 0.42, math.pi - 1.9, math.pi + 1.9, S, seg=36), (0.5, 0, 0.06), RX))
    for i in range(7):
        for phi in (-0.75, 0.75):
            d = V((0, math.sin(phi), math.cos(phi)))
            body.append(box('vent', (0.03, 0.0085, 0.003), V((0.33 + i * 0.05, 0, 0.06)) + d * 0.0262, M['black'],
                            rot=(-phi, 0, 0), bevel=0.004, segs=2))
    body.append(bevelled(box('rib', (0.44, 0.01, 0.006), (0.5, 0, 0.0885), S), 0.002))
    body.append(sphere('bead', 0.0055, (0.718, 0, 0.096), M['brass'], seg=12, rings=8))
    # receiver: milled panel, pins, engraving, safety, ejection port
    body.append(bevelled(box('receiver', (0.25, 0.052, 0.095), (0.055, 0, 0.042), S), 0.01))
    body.append(bevelled(box('panel', (0.17, 0.004, 0.022), (0.06, 0.0262, 0.0745), M['blued']), 0.0015))
    body.append(text_mesh('engraving', 'OMAFIETS 12  -  BEL NIET AAN', 0.0085, (0.06, 0.0286, 0.0745), rot=SIDE_Y, mat=M['scratch'], extrude=0.0004))
    for x, z in ((-0.045, 0.012), (0.15, 0.012), (-0.045, 0.075), (0.16, 0.075)):
        body.append(screw((x, 0.026, z), 0.0042, mat=M['steel_light']))
    body.append(box('ejection_port', (0.07, 0.004, 0.025), (0.08, -0.0262, 0.06), M['black'], bevel=0.003))
    body.append(cyl('safety', 0.005, 0.06, (-0.03, 0, 0.0), M['sign_red'], rot=(math.pi / 2, 0, 0), seg=12))
    # side-saddle on the player's side with four shells
    body.append(bevelled(box('saddle', (0.115, 0.006, 0.05), (0.07, 0.029, 0.03), M['polymer']), 0.003))
    for i in range(4):
        body += shell_round('saddle', (0.031 + i * 0.026, 0.0435, 0.002), L=0.056)
    body.append(bevelled(box('saddle_band', (0.112, 0.006, 0.012), (0.07, 0.053, 0.032), M['polymer']), 0.002))
    # walnut stock with a duct-tape repair, a sticker and a sling stud
    stock = extrude_profile('stock', [(-0.06, 0.075), (-0.4, 0.05), (-0.42, -0.085), (-0.36, -0.095), (-0.12, -0.025),
                                      (-0.07, -0.1), (-0.035, -0.1), (-0.06, -0.02), (-0.06, 0.02)], 0.048, Wd)
    body.append(bevelled(stock, 0.011, 4))
    body.append(bevelled(box('buttpad', (0.022, 0.052, 0.148), (-0.417, 0, -0.018), M['rubber'], rot=(0, -0.12, 0)), 0.007))
    body.append(box('spacer', (0.004, 0.05, 0.146), (-0.404, 0, -0.018), M['black'], rot=(0, -0.12, 0), bevel=0.0015, segs=1))
    tape = shaped_cyl('duct', 0.045, lambda t, a: 1.0 + 0.012 * math.sin(a * 5 + t * 9) + 0.006 * math.sin(a * 13), M['duct'], seg=48, rings=6)
    tape.scale = (0.057, 0.0272, 1.0)   # wraps the stock wrist (an oval section)
    body.append(place(tape, (-0.155, 0, 0.018), (0, math.pi / 2 + 0.12, 0)))
    body.append(box('tape_flap', (0.018, 0.0012, 0.022), (-0.133, 0.0282, -0.032), M['duct'], rot=(0.25, 0.5, 0), bevel=0.001, segs=1))
    body.append(text_mesh('tape_txt', 'v. KEES', 0.0095, (-0.155, 0.0281, 0.03), rot=(math.pi / 2, 0.12, math.pi), mat=M['ink'], extrude=0.0003))
    body += sign((-0.3, 0.0245, -0.012), 0.03, SIDE_Y, kind='fiets')
    body.append(torus('swivel', 0.009, 0.0022, (-0.37, 0, -0.095), S, rot=(math.pi / 2, 0, 0.3), segU=16, segV=6))
    body.append(torus('guard', 0.032, 0.0055, (-0.005, 0, -0.01), S, rot=(math.pi / 2, 0, 0), segU=24, segV=8, arc=(math.pi, 2 * math.pi), rz=0.009))
    body.append(box('trigger', (0.008, 0.009, 0.03), (0.0, 0, -0.012), M['steel_light'], rot=(0, 0.3, 0), bevel=0.003))
    # grooved walnut pump (animated)
    pump = [shaped_cyl('pump', 0.2, lambda t, a: 0.03 * (1 - 0.1 * max(0.0, math.cos(t * 2 * math.pi * 8)) ** 4 * (0.1 < t < 0.9))
                       * (1 - 0.06 * (1 - math.sin(math.pi * t)) ** 6), M['wood_dark'], seg=40, rings=96)]
    pump[0].location, pump[0].rotation_euler = (0.42, 0, 0.022), RX
    pump.append(cyl('pump_cap', 0.022, 0.012, (0.525, 0, 0.022), M['blued'], rot=RX, seg=24))
    shell = shell_round('shell', (0.0, 0, 0.0), L=0.056)
    for o in shell:  # spare shell for ejection, parked out of sight under the receiver
        o.location = V(o.location) + V((0.06, 0, 0.015))
    parts = {'Shotgun_Body': body, 'Shotgun_Pump': pump, 'Shotgun_Shell': shell}
    hands = (grip_hand((-0.055, 0, -0.045), (-0.4, 0, -1), (0, -1, 0), 0.022, (1, 0, 0), (-0.32, -0.2, -0.3))
             + grip_hand((0.43, 0, 0.022), (1, 0, 0), (0, 0, -1), 0.03, (0, -1, 0), (0.16, 0.06, -0.32), watch=True))
    return parts, hands


RX = (0, math.pi / 2, 0)        # local Z -> +X (barrel axis)
SIDE_Y = (math.pi / 2, 0, math.pi)   # text on the +Y side (the side the player sees), reading front-to-back


def bevelled(o, width, segs=3):
    m = o.modifiers.new('bevel', 'BEVEL')
    m.width = width
    m.segments = segs
    m.limit_method = 'ANGLE'
    return o


def screw(loc, r=0.0045, axis='Y', mat=None):
    """Hex-socket screw head poking out along +axis."""
    rot = {'Y': (-math.pi / 2, 0, 0), 'Z': (0, 0, 0), 'X': RX}[axis]
    return cyl('screw', r, 0.003, loc, mat or M['sn_steel'], rot=rot, seg=12)


def knurled(name, r, depth, loc, mat, rot=RX, ridges=28, amp=0.06):
    return place(shaped_cyl(name, depth, lambda t, a: r * (1 - amp * (0.5 + 0.5 * math.cos(a * ridges))), mat,
                            seg=ridges * 4, rings=1), loc, rot)


def sniper():
    Mt, St, Sc, Pk = M['sn_metal'], M['sn_steel'], M['sn_scope'], M['sn_stock']
    body = []
    # --- barrel: tapered and fluted, with a chunky three-port muzzle brake
    def fluted(t, a):
        r = 0.023 + (0.016 - 0.023) * t
        zone = max(0.0, min(1.0, (t - 0.18) / 0.06, (0.9 - t) / 0.06))
        return r * (1 - 0.13 * zone * max(0.0, math.cos(a * 6)) ** 6)
    body.append(place(shaped_cyl('barrel', 0.8, fluted, Mt, seg=72, rings=40), (0.6, 0, 0.03), RX))
    body.append(cyl('barrel_nut', 0.027, 0.035, (0.215, 0, 0.03), St, rot=RX, seg=6))
    body.append(bevelled(box('brake', (0.085, 0.046, 0.04), (1.035, 0, 0.03), St, bevel=0.0), 0.007))
    for i in range(3):
        body.append(box('brake_port', (0.013, 0.05, 0.026), (1.008 + i * 0.022, 0, 0.03), M['black'], bevel=0.003))
    body.append(cyl('bore', 0.0065, 0.004, (1.077, 0, 0.03), M['black'], rot=RX, seg=16))
    body.append(cyl('brake_crown', 0.018, 0.006, (1.077, 0, 0.03), St, rot=RX, seg=24))

    # --- receiver: flat-sided action with a picatinny rail, screws and an engraving
    body.append(bevelled(box('receiver', (0.3, 0.058, 0.062), (0.07, 0, 0.034), St), 0.012))
    body.append(cyl('bolt_shroud', 0.024, 0.06, (-0.1, 0, 0.04), St, rot=RX, seg=24))
    body.append(cyl('shroud_cap', 0.018, 0.012, (-0.135, 0, 0.04), M['sn_orange'], rot=RX, seg=24))
    body.append(box('ejection_port', (0.08, 0.004, 0.026), (0.07, -0.029, 0.045), M['black'], bevel=0.002))
    body.append(bevelled(box('rail', (0.34, 0.026, 0.01), (0.08, 0, 0.07), Mt), 0.002))
    for i in range(15):
        body.append(box('rail_tooth', (0.009, 0.03, 0.007), (-0.075 + i * 0.022, 0, 0.078), Mt, bevel=0.0015, segs=1))
    for x in (-0.04, 0.17):
        body.append(screw((x, 0.0295, 0.022)))
    body.append(text_mesh('engraving', 'HOLLANDS GLORIE', 0.0105, (0.065, 0.0293, 0.036), rot=SIDE_Y,
                          mat=M['scratch'], extrude=0.0004))
    body.append(text_mesh('serial', 'NR. 1234-FB', 0.007, (0.065, 0.0293, 0.024), rot=SIDE_Y,
                          mat=M['scratch'], extrude=0.0004))

    # --- scope: matte tube, knurled turrets, sunshade, flip-up cap, recessed coated lenses
    axz = 0.118
    sc = [cyl('scope_tube', 0.021, 0.3, (0.08, 0, axz), Sc, rot=RX, seg=40),
          cyl('scope_bell', 0.021, 0.1, (0.28, 0, axz), Sc, r2=0.034, rot=RX, seg=40),
          cyl('obj_housing', 0.035, 0.05, (0.355, 0, axz), Sc, rot=RX, seg=40),
          cyl('sunshade', 0.034, 0.07, (0.415, 0, axz), Sc, rot=RX, seg=40, caps=False),
          cyl('sunshade_in', 0.031, 0.07, (0.415, 0, axz), M['black'], rot=RX, seg=32, caps=False),
          torus('shade_lip', 0.0325, 0.0028, (0.45, 0, axz), Sc, rot=RX, segU=40, segV=6),
          cyl('lens_front', 0.031, 0.003, (0.383, 0, axz), M['sn_lens'], rot=RX, seg=32),
          torus('obj_band', 0.0352, 0.0035, (0.335, 0, axz), M['sn_orange'], rot=RX, segU=40, segV=6),
          cyl('ocular_neck', 0.021, 0.05, (-0.095, 0, axz), Sc, r2=0.026, rot=RX, seg=40),
          knurled('ocular', 0.029, 0.045, (-0.14, 0, axz), Sc, ridges=30),
          cyl('eyecup', 0.03, 0.028, (-0.178, 0, axz), M['rubber'], rot=RX, seg=40, caps=False),
          torus('eyecup_lip', 0.028, 0.004, (-0.192, 0, axz), M['rubber'], rot=RX, segU=40, segV=6),
          cyl('lens_back', 0.025, 0.003, (-0.165, 0, axz), M['sn_lens'], rot=RX, seg=32),
          # turret saddle with elevation (top), windage (right) and a big parallax knob on the player's side
          cyl('saddle', 0.03, 0.07, (0.08, 0, axz), Sc, rot=RX, seg=40),
          cyl('elev_base', 0.017, 0.014, (0.08, 0, axz + 0.034), Sc, seg=32),
          knurled('elev_cap', 0.019, 0.022, (0.08, 0, axz + 0.052), Sc, rot=(0, 0, 0), ridges=26),
          cyl('elev_top', 0.0165, 0.003, (0.08, 0, axz + 0.0635), M['sn_orange'], seg=32),
          knurled('wind_cap', 0.016, 0.022, (0.08, -0.044, axz), Sc, rot=(math.pi / 2, 0, 0), ridges=24),
          knurled('parallax', 0.021, 0.018, (0.08, 0.04, axz), Sc, rot=(math.pi / 2, 0, 0), ridges=30),
          cyl('parallax_face', 0.017, 0.003, (0.08, 0.05, axz), M['sn_orange'], rot=(math.pi / 2, 0, 0), seg=32)]
    for i in range(12):   # white ticks around the elevation cap
        a = i * 2 * math.pi / 12
        sc.append(box('tick', (0.003, 0.0012, 0.008 if i % 3 == 0 else 0.005),
                      (0.08 + math.cos(a) * 0.0195, math.sin(a) * 0.0195, axz + 0.05), M['stencil'], rot=(0, 0, a), segs=1))
    # flip cap, swung open to the far side so it doesn't block the view
    hinge = V((0.448, -0.036, axz))
    sc.append(cyl('cap_hinge', 0.0045, 0.018, hinge, M['sn_orange'], seg=12))
    swing = -math.radians(115)
    n = V((math.cos(swing), math.sin(swing), 0))
    off = V((0.006, 0.036, 0))
    off = V((off.x * math.cos(swing) - off.y * math.sin(swing), off.x * math.sin(swing) + off.y * math.cos(swing), 0))
    cup = lathe('flip_cap', [(0.0, 0.0), (0.035, 0.0), (0.037, 0.003), (0.037, 0.013), (0.033, 0.013), (0.033, 0.004), (0.0, 0.004)],
                M['sn_orange'], seg=40)
    sc.append(orient_basis(cup, basis((0, 0, 1), -n), hinge + off))
    for x in (0.0, 0.16):   # rings clamped on the rail
        sc.append(bevelled(box('ring_base', (0.03, 0.04, 0.02), (x, 0, 0.086), Mt), 0.004))
        sc.append(torus('ring', 0.0245, 0.0055, (x, 0, axz), Mt, rot=RX, segU=40, segV=8, rz=0.013))
        sc.append(screw((x, 0.0215, 0.088), 0.004))
        for s in (-1, 1):
            sc.append(screw((x, s * 0.028, axz + 0.012), 0.0035, mat=Mt))
    body += sc

    # --- stock: sand polymer, stippled grip panel, orange adjustable cheek riser, spacer'd butt pad
    stock = extrude_profile('stock', [(0.0, 0.05), (-0.46, 0.06), (-0.49, -0.11), (-0.43, -0.12), (-0.15, -0.045),
                                      (-0.1, -0.12), (-0.06, -0.12), (-0.04, -0.03), (0.48, -0.025), (0.5, -0.005),
                                      (0.48, 0.01), (0.0, 0.01)], 0.055, Pk)
    bevelled(stock, 0.012, 4)
    body.append(stock)
    for s in (-1, 1):
        panel = extrude_profile('grip_panel', [(-0.13, -0.05), (-0.098, -0.108), (-0.07, -0.108), (-0.057, -0.042)], 0.004, M['sn_grip'])
        panel.location = (0, s * 0.0285, 0)
        body.append(bevelled(panel, 0.0015, 2))
        fpanel = extrude_profile('fore_panel', [(0.27, -0.02), (0.42, -0.018), (0.42, 0.004), (0.27, 0.004)], 0.004, M['sn_grip'])
        fpanel.location = (0, s * 0.0285, 0)
        body.append(bevelled(fpanel, 0.0015, 2))
    for i in range(3):   # forend vents
        body.append(box('vent', (0.026, 0.06, 0.007), (0.44 + i * 0.016, 0, -0.008), M['black'], bevel=0.003, rot=(0, 0.5, 0)))
    body.append(bevelled(box('cheek', (0.2, 0.046, 0.026), (-0.3, 0, 0.082), M['sn_orange']), 0.01))
    for x in (-0.36, -0.24):
        body.append(cyl('cheek_post', 0.005, 0.03, (x, 0, 0.062), M['sn_steel'], seg=12))
        body.append(knurled('cheek_knob', 0.009, 0.012, (x, 0.032, 0.062), M['sn_grip'], rot=(math.pi / 2, 0, 0), ridges=12, amp=0.12))
    body.append(bevelled(box('spacer', (0.008, 0.056, 0.178), (-0.477, 0, -0.03), M['black']), 0.002))
    body.append(bevelled(box('buttpad', (0.022, 0.058, 0.182), (-0.492, 0, -0.03), M['rubber'], rot=(0, -0.02, 0)), 0.008))
    for z in (-0.09, -0.06, -0.03, 0.0, 0.03):
        body.append(box('pad_rib', (0.004, 0.06, 0.006), (-0.504, 0, z), M['rubber'], bevel=0.002, segs=1))
    body.append(torus('swivel', 0.009, 0.0022, (-0.38, 0, -0.1), M['sn_steel'], rot=(math.pi / 2, 0, 0.5), segU=16, segV=6))
    body.append(torus('swivel', 0.009, 0.0022, (0.46, 0, -0.035), M['sn_steel'], rot=(math.pi / 2, 0, 0), segU=16, segV=6))

    # --- magazine, trigger, folded bipod
    body.append(bevelled(box('mag', (0.075, 0.042, 0.07), (0.1, 0, -0.05), M['sn_metal']), 0.006))
    body.append(bevelled(box('mag_plate', (0.082, 0.046, 0.01), (0.1, 0, -0.087), M['sn_orange']), 0.003))
    body.append(box('mag_release', (0.012, 0.05, 0.008), (0.05, 0, -0.03), M['sn_steel'], bevel=0.002))
    body.append(torus('guard', 0.03, 0.006, (0.0, 0, -0.03), Mt, rot=(math.pi / 2, 0, 0), segU=24, segV=8, arc=(math.pi, 2 * math.pi), rz=0.009))
    body.append(box('trigger', (0.008, 0.01, 0.03), (0.005, 0, -0.03), M['sn_orange'], rot=(0, 0.3, 0), bevel=0.003))
    for s in (-1, 1):
        body.append(tube('bipod', (0.45, s * 0.019, -0.032), (0.22, s * 0.021, -0.042), 0.0075, Mt, seg=12))
        body.append(tube('bipod_inner', (0.26, s * 0.021, -0.041), (0.18, s * 0.022, -0.044), 0.0055, St, seg=12))
        body.append(sphere('bipod_foot', 0.011, (0.175, s * 0.022, -0.044), M['rubber'], seg=12, rings=8))
        body.append(place(torus('bipod_spring', 0.0085, 0.0017, (0.0, 0, 0.0), St, segU=16, segV=4), (0.43, s * 0.019, -0.033), RX))
    body.append(bevelled(box('bipod_mount', (0.035, 0.05, 0.022), (0.455, 0, -0.035), Mt), 0.004))

    # --- humour on the player's side: a 25 km/h sign sticker and scratched tally marks of fatbikes stopped
    body += sign(V((-0.33, 0.0283, -0.02)), 0.028, SIDE_Y)
    body.append(text_mesh('sign_25', '25', 0.026, (-0.33, 0.0298, -0.022), rot=SIDE_Y, mat=M['ink'], extrude=0.0004))
    body.append(text_mesh('sign_txt', 'NIET VOOR FATBIKES', 0.0075, (-0.33, 0.0283, 0.024), rot=SIDE_Y, mat=M['ink'], extrude=0.0004))
    for g in range(3):   # three groups of five (gate) + two strays
        gx = -0.24 + g * 0.032
        n = 5 if g < 2 else 2
        for i in range(min(n, 4)):
            body.append(box('tally', (0.0016, 0.0012, 0.022), (gx + i * 0.0055, 0.0283, 0.008), M['scratch'], rot=(0, 0.06, 0), segs=1))
        if n == 5:
            body.append(box('tally', (0.0016, 0.0012, 0.027), (gx + 0.008, 0.0283, 0.008), M['scratch'], rot=(0, -1.0, 0), segs=1))

    # --- bolt (animated): handle on the right with a big tactical knob
    bolt = [tube('bolt_arm', (0.03, -0.028, 0.045), (0.03, -0.072, 0.024), 0.0065, M['sn_steel'], seg=12),
            cyl('bolt_root', 0.012, 0.014, (0.03, -0.03, 0.045), M['sn_steel'], rot=(math.pi / 2, 0, 0), seg=16),
            knurled('bolt_knob', 0.014, 0.024, (0.03, -0.083, 0.02), M['sn_grip'], rot=(math.pi / 2 + 0.4, 0, 0), ridges=14, amp=0.1)]
    parts = {'Sniper_Body': body, 'Sniper_Bolt': bolt}
    hands = (grip_hand((-0.075, 0, -0.07), (-0.35, 0, -1), (0, -1, 0), 0.022, (1, 0, 0), (-0.33, -0.22, -0.3))
             + grip_hand((0.33, 0, -0.012), (1, 0, 0), (0, 0, -1), 0.03, (0, -1, 0), (0.12, 0.07, -0.33), watch=True))
    return parts, hands


def bazooka():
    """'BOEM!' launcher: chipped olive paint, riveted bands, stencils and a warning sticker on the player's side,
    a duct-taped crack, canvas strap, firing box with cable, a sooty venturi and a striped 'TOET!' rocket."""
    O, Od = M['olive'], M['olive_dark']
    R = 0.065
    body = [cyl('tube', R, 1.15, (0.05, 0, 0), O, rot=RX, seg=56, caps=False),
            cyl('tube_inner', 0.058, 1.15, (0.05, 0, 0), M['black'], rot=RX, seg=32, caps=False)]
    muzzle = lathe('muzzle', [(0.0645, 0.0), (0.067, 0.006), (0.071, 0.06), (0.085, 0.094), (0.088, 0.1), (0.082, 0.102),
                              (0.064, 0.064), (0.058, 0.0)], Od, seg=56)
    body.append(place(muzzle, (0.62, 0, 0), RX))
    venturi = lathe('venturi', [(0.0645, 0.0), (0.068, -0.006), (0.072, -0.035), (0.089, -0.13), (0.091, -0.142), (0.085, -0.144),
                                (0.0835, -0.138)], Od, seg=56)
    soot = lathe('soot', [(0.0828, -0.137), (0.0628, -0.03), (0.0575, 0.0)], M['soot'], seg=48)
    for o in (venturi, soot):
        body.append(place(o, (-0.5, 0, 0), RX))
    # bands with rivets
    for x in (-0.4, -0.15, 0.25, 0.5):
        body.append(torus('band', R + 0.0012, 0.008, (x, 0, 0), Od, rot=RX, segU=56, segV=8, rz=0.011))
        for k in range(14):
            a = k * 2 * math.pi / 14
            body.append(sphere('rivet', 0.0036, (x, math.cos(a) * (R + 0.0085), math.sin(a) * (R + 0.0085)), M['steel'], seg=10, rings=6))
    for i in range(6):  # hazard stripes near the muzzle
        body.append(torus('stripe', R + 0.0005, 0.006, (0.53 + i * 0.016, 0, 0), M['yellow' if i % 2 == 0 else 'black'],
                          rot=RX, segU=56, segV=4, rz=0.008))
    # stencils on the player's side
    body.append(tube_text('BOEM!', 0.055, 0.09, R, 0.42, M['yellow'], extrude=0.0012))
    body.append(tube_text('ACHTERKANT HEET!', 0.0135, -0.285, R, 0.62, M['yellow']))
    body.append(tube_text('NIET IN DE HUISKAMER AFVUREN', 0.008, -0.285, R, 0.38, M['stencil']))
    body.append(tube_text('M-25 FATBIKE-STOPPER', 0.0085, 0.38, R, 0.75, M['stencil']))
    body.append(tube_decal(cyl('warn_edge', 0.03, 0.0012, mat=M['black'], seg=3, rot=(0, 0, -math.pi / 2)), 0.38, R, 0.32))
    body.append(tube_decal(cyl('warn', 0.024, 0.0012, mat=M['yellow'], seg=3, rot=(0, 0, -math.pi / 2)), 0.38, R, 0.32, lift=0.0011))
    body.append(tube_decal(text_mesh('warn_mark', '!', 0.026, rot=(0, 0, math.pi), mat=M['ink'], extrude=0.0003), 0.381, R, 0.32, lift=0.0018))
    # duct tape over a crack, with a marker note
    tape = shaped_cyl('duct', 0.05, lambda t, a: (R + 0.0016) * (1 + 0.012 * math.sin(a * 6 + t * 7) + 0.006 * math.sin(a * 17)), M['duct'], seg=64, rings=6)
    body.append(place(tape, (-0.03, 0, 0), (0.05, math.pi / 2, 0)))
    body.append(tube_text('PLAKT WEL', 0.011, -0.03, R + 0.0025, 0.5, M['ink'], extrude=0.0003))
    # pistol grip with finger grooves, trigger, front grip, firing box + cable
    body.append(bevelled(box('grip_mount', (0.08, 0.04, 0.04), (0.02, 0, -0.07), Od), 0.008))
    body.append(capsule('pistol_grip', (0.02, 0, -0.08), (-0.01, 0, -0.18), 0.022, 0.024, M['rubber'], sxy=(1.2, 0.9)))
    for i in range(3):
        body.append(sphere('finger_ridge', 0.007, (0.034 - i * 0.009, 0, -0.115 - i * 0.025), M['rubber'], scale=(1, 2.4, 1), seg=12, rings=6))
    body.append(torus('guard', 0.03, 0.0055, (0.065, 0, -0.085), Od, rot=(math.pi / 2, 0, 0), segU=20, segV=8, arc=(math.pi, 2 * math.pi), rz=0.009))
    body.append(box('trigger', (0.009, 0.011, 0.03), (0.065, 0, -0.095), M['rocket'], bevel=0.003))
    body.append(bevelled(box('fgrip_mount', (0.06, 0.04, 0.04), (0.33, 0, -0.07), Od), 0.008))
    body.append(capsule('front_grip', (0.33, 0, -0.08), (0.33, 0, -0.17), 0.022, 0.022, M['rubber']))
    body.append(bevelled(box('firing_box', (0.075, 0.032, 0.05), (-0.075, 0.045, -0.06), Od), 0.007))
    body.append(cyl('box_knob', 0.008, 0.012, (-0.06, 0.064, -0.055), M['rocket'], rot=(math.pi / 2, 0, 0), seg=16))
    for x in (-0.1, -0.05):
        body.append(screw((x, 0.0615, -0.04), 0.0035, mat=M['steel']))
    body.append(sweep('cable', bezier((-0.112, 0.05, -0.065), (-0.2, 0.06, -0.11), (-0.36, 0.05, -0.1), (-0.45, 0.035, -0.06), 20),
                      0.0045, M['cable'], seg=8))
    body.append(bevelled(box('contact', (0.04, 0.03, 0.025), (-0.46, 0.025, -0.06), Od), 0.005))
    # canvas strap hanging on the player's side between two swivels
    for x in (0.27, -0.42):
        body.append(torus('swivel', 0.011, 0.0025, (x, R + 0.006, -0.03), M['steel'], rot=(0, 0, 0), segU=16, segV=6))
    body.append(sweep('strap', bezier((0.27, R + 0.012, -0.038), (0.16, R + 0.03, -0.16), (-0.3, R + 0.03, -0.16), (-0.42, R + 0.012, -0.038), 28),
                      0.013, M['canvas'], seg=12, up=(0, 0, 1), flat=0.16))
    body.append(bevelled(box('buckle', (0.03, 0.006, 0.032), (-0.09, R + 0.034, -0.15), M['steel']), 0.003))
    # padded canvas shoulder rest
    body.append(bevelled(box('shoulder_pad', (0.22, 0.085, 0.032), (-0.25, 0, -0.072), M['canvas']), 0.014, 4))
    for i in range(10):
        body.append(box('pad_stitch', (0.008, 0.0012, 0.0012), (-0.345 + i * 0.021, 0.0428, -0.072), M['twine'], segs=1))
    # sights: flip-up frame with crosshair and an orange dot, peep sight at the back
    body.append(bevelled(box('sight_base', (0.05, 0.02, 0.03), (0.45, 0.06, 0.05), Od), 0.004))
    body.append(torus('sight_frame', 0.035, 0.0045, (0.45, 0.075, 0.1), M['black'], rot=RX, segU=40, segV=8))
    for rot in ((0, 0, 0), (math.pi / 2, 0, 0)):
        body.append(box('cross', (0.002, 0.066, 0.0018), (0.45, 0.075, 0.1), M['black'], rot=rot, segs=1))
    body.append(sphere('sight_dot', 0.0045, (0.448, 0.075, 0.1), M['sn_orange'], seg=12, rings=8))
    body.append(tube('sight_post', (0.45, 0.075, 0.065), (0.45, 0.075, 0.066), 0.003, M['black'], seg=6))
    body.append(bevelled(box('rear_sight', (0.02, 0.025, 0.03), (-0.05, 0.06, 0.055), M['black']), 0.003))
    body.append(torus('peep', 0.008, 0.0028, (-0.05, 0.075, 0.075), M['black'], rot=RX, segU=20, segV=6))
    # rocket: ogive warhead with a white band and 'TOET!' stencil, fuze, tail fins inside the tube
    rocket = [cyl('rocket_body', 0.055, 0.12, (0.7, 0, 0), M['olive_dark'], rot=RX, seg=32),
              place(lathe('warhead', [(0.0, 0.0), (0.06, 0.0), (0.06, 0.04), (0.054, 0.085), (0.04, 0.125), (0.02, 0.152), (0.012, 0.158), (0.0, 0.16)],
                          M['rocket'], seg=40), (0.76, 0, 0), RX),
              cyl('fuze', 0.0105, 0.02, (0.926, 0, 0), M['steel_light'], rot=RX, seg=16),
              sphere('fuze_tip', 0.008, (0.937, 0, 0), M['brass'], seg=12, rings=6),
              torus('rocket_band', 0.06, 0.0045, (0.79, 0, 0), M['white'], rot=RX, segU=40, segV=6, rz=0.008),
              tube_text('TOET!', 0.0115, 0.812, 0.0585, 0.4, M['white'], extrude=0.0015)]
    for i in range(4):  # tail fins (inside the tube while loaded)
        a = i * math.pi / 2
        rocket.append(box('fin', (0.08, 0.004, 0.05), (0.62, math.cos(a) * 0.03, math.sin(a) * 0.03), M['olive_dark'], rot=(a, 0, 0)))
    parts = {'Bazooka_Body': body, 'Bazooka_Rocket': rocket}
    hands = (grip_hand((0.005, 0, -0.13), (-0.25, 0, -1), (0, -1, 0), 0.024, (1, 0, 0), (-0.16, -0.24, -0.42))
             + grip_hand((0.33, 0, -0.125), (0, 0, -1), (0, 1, 0), 0.022, (1, 0, 0), (0.12, 0.22, -0.44), watch=True))
    return parts, hands


def ijsmachine():
    """A stubby six-barrel gatling in ice-cream-cart colours: a striped paper cup of lumpy scoops with sprinkles
    on top, star-nozzle muzzles with frost, a frozen coolant line and waffle-cone grips."""
    import random
    rnd = random.Random(7)
    Mi, Pk, Cr, Ch = M['mint'], M['pink'], M['cream_paint'], M['chrome']
    axis_z = 0.0
    hub = V((0.0, 0, axis_z))
    body = [bevelled(box('housing', (0.27, 0.12, 0.13), (0.0, 0, 0.005), Mi), 0.025, 4),
            bevelled(box('housing_top', (0.2, 0.09, 0.03), (-0.01, 0, 0.075), M['mint_dark']), 0.012),
            cyl('motor', 0.05, 0.08, (-0.17, 0, 0.0), Pk, rot=RX, seg=40),
            cyl('motor_cap', 0.042, 0.02, (-0.215, 0, 0.0), Ch, rot=RX, seg=40),
            cyl('collar_rear', 0.064, 0.03, (0.15, 0, axis_z), Ch, rot=RX, seg=48)]
    # a little waffle cone on the motor's back end, pointing at the player
    cone = lathe('back_cone', [(0.034, 0.0), (0.0, 0.07)], M['waffle'], seg=32)
    body.append(place(cone, (-0.225, 0, 0.0), (0, -math.pi / 2, 0)))
    body.append(torus('back_cone_rim', 0.034, 0.005, (-0.225, 0, 0.0), M['choco_dip'], rot=RX, segU=32, segV=8))
    for i in range(3):  # cream stripes like an ice-cream van
        body.append(bevelled(box('stripe', (0.018, 0.122, 0.132), (-0.08 + i * 0.07, 0, 0.005), Cr), 0.02, 2))
    for i in range(5):  # cooling fins on the motor
        body.append(torus('fin', 0.05, 0.006, (-0.2 + i * 0.016, 0, 0.0), M['mint_dark'], rot=RX, segU=40, segV=8))
    for x, z in ((-0.115, 0.045), (0.115, 0.045), (-0.115, -0.04), (0.115, -0.04)):
        body.append(screw((x, 0.0605, z), 0.0045, mat=Ch))
    # striped paper cup with a scalloped rim on top, holding the scoops
    tub = lathe('tub', [(0.0, 0.0), (0.055, 0.0), (0.058, 0.004), (0.072, 0.07), (0.068, 0.07), (0.0, 0.012)], Cr, seg=56)
    tub.location = (-0.01, 0, 0.095)
    tub_parts = [tub]
    for k in range(12):
        a = k * 2 * math.pi / 12
        rm = 0.0655
        tub_parts.append(box('cup_stripe', (0.0022, 0.013, 0.066), (-0.01 + math.cos(a) * rm, math.sin(a) * rm, 0.131), Pk,
                             rot=(0, 0.2, a), segs=1))
    rim = shaped_cyl('cup_rim', 0.008, lambda t, a: 0.0745 + 0.004 * abs(math.cos(a * 8)), Pk, seg=96, rings=2, caps=False)
    rim.location = (-0.01, 0, 0.167)
    tub_parts.append(rim)
    tub_parts.append(torus('cup_lip', 0.072, 0.0035, (-0.01, 0, 0.171), Pk, segU=64, segV=6))
    body += tub_parts
    # frozen coolant line from the cup down the player's side to the front collar
    pipe = bezier((-0.075, 0.03, 0.075), (0.02, 0.085, 0.08), (0.26, 0.08, 0.04), (0.405, 0.062, 0.03), 26)
    body.append(sweep('coolant', pipe, 0.0075, M['coolant'], seg=12))
    for k in (5, 11, 17, 22):
        d = (pipe[k + 1] - pipe[k - 1]).normalized()
        body.append(lib.orient(lumpy('frost_ring', 1.0, (0, 0, 0), M['frost'], amp=0.15, freq=3, seed=k, scale=(0.011, 0.011, 0.007), seg=16, rings=8),
                               pipe[k] - d * 0.001, pipe[k] + d * 0.001))
    # grips: waffle-cone pistol grip and a cone-shaped front grip dipped in chocolate
    body.append(tube('grip_mount', (-0.02, 0, -0.04), (0.04, 0, -0.06), 0.022, M['mint_dark'], seg=16))
    body.append(capsule('pistol_grip', (0.02, 0, -0.07), (-0.01, 0, -0.17), 0.022, 0.024, M['waffle'], sxy=(1.2, 0.9)))
    body.append(torus('guard', 0.03, 0.0055, (0.065, 0, -0.075), Ch, rot=(math.pi / 2, 0, 0), segU=20, segV=8, arc=(math.pi, 2 * math.pi), rz=0.009))
    body.append(box('trigger', (0.009, 0.011, 0.03), (0.065, 0, -0.085), Pk, bevel=0.003))
    body.append(cyl('collar_front', 0.062, 0.035, (0.42, 0, axis_z), Pk, rot=RX, seg=48))
    body.append(tube('fgrip_mount', (0.42, 0, -0.055), (0.42, 0, -0.075), 0.02, Ch, seg=16))
    fcone = lathe('front_grip', [(0.0, 0.0), (0.027, 0.0), (0.0135, -0.095), (0.006, -0.103), (0.0, -0.105)], M['waffle'], seg=32)
    body.append(place(fcone, (0.42, 0, -0.072), None))
    body.append(lumpy('grip_dip', 0.028, (0.42, 0, -0.075), M['choco_dip'], amp=0.08, freq=4, seed=2, scale=(1, 1, 0.35), seg=24, rings=10))
    # stencils on both sides, a slogan on the player's side
    body.append(text_mesh('stencil', 'IJSKOUD!', 0.032, (0.0, 0.0612, 0.012), rot=SIDE_Y, mat=Pk, extrude=0.002))
    body.append(text_mesh('stencil2', 'IJSKOUD!', 0.032, (0.0, -0.0612, 0.012), mat=Pk, extrude=0.002))
    body.append(text_mesh('slogan', '2 BOLLEN = 1 FATBIKER', 0.0095, (0.0, 0.0628, -0.03), rot=SIDE_Y, mat=M['choco_dip'], extrude=0.0012))
    # the scoops heaped in the cup (hidden when the gun is empty): lumpy, with sprinkles and a cherry on top
    scoops = []
    flav = ['strawberry', 'vanilla', 'chocolate', 'pistachio', 'lemon', 'strawberry', 'pistachio']
    spots = [(0.025, 0.02, 0.172), (-0.03, 0.025, 0.17), (0.0, -0.03, 0.17), (-0.04, -0.02, 0.168), (0.035, -0.022, 0.168),
             (0.0, 0.005, 0.2), (-0.015, 0.0, 0.205)]
    spr = ['spr_pink', 'spr_yellow', 'spr_blue', 'spr_white', 'spr_green']
    for n, ((x, y, z), m) in enumerate(zip(spots, flav)):
        c = V((x - 0.01, y, z))
        scoops.append(lumpy('scoop', 0.032, c, M[m], amp=0.1, freq=2.2, seed=n + 1, scale=(1, 1, 0.9), seg=28, rings=14))
        scoops.append(lumpy('scoop_rim', 1.0, c - V((0, 0, 0.012)), M[m], amp=0.12, freq=5, seed=n + 11, scale=(0.034, 0.034, 0.009), seg=28, rings=8))
        for _ in range(8):   # hagelslag on the upper half
            th, ph = rnd.uniform(0, 2 * math.pi), rnd.uniform(0.15, 1.0)
            d = V((math.cos(th) * math.cos(ph), math.sin(th) * math.cos(ph), math.sin(ph)))
            p = c + V((d.x * 0.033, d.y * 0.033, d.z * 0.03))
            t = d.cross(V((rnd.uniform(-1, 1), rnd.uniform(-1, 1), rnd.uniform(-1, 1)))).normalized() * 0.0042
            scoops.append(capsule('sprinkle', p - t, p + t, 0.0017, 0.0017, M[rnd.choice(spr)], seg=8, rings=4))
    top = V((-0.025, 0.0, 0.238))
    scoops.append(sphere('cherry', 0.012, top, M['cherry'], seg=16, rings=8))
    scoops.append(sweep('cherry_stem', bezier(top + V((0, 0, 0.01)), top + V((0, 0, 0.02)), top + V((0.006, 0, 0.03)), top + V((0.014, 0.004, 0.034)), 8),
                        0.0016, M['stem'], seg=6))
    K, pivot = 0.75, V((-0.01, 0, 0.09))  # a smaller cup keeps the view clear
    for o in tub_parts + scoops:
        o.location = pivot + (V(o.location) - pivot) * K
        o.scale = V(o.scale) * K
    # the spinning barrels (origin on the spin axis): chrome tubes, frosty tips, star nozzles in scoop flavours
    barrels = [cyl('spindle', 0.014, 0.5, (0.4, 0, axis_z), Ch, rot=RX, seg=24),
               cyl('plate_rear', 0.05, 0.012, (0.18, 0, axis_z), Ch, rot=RX, seg=6),
               cyl('plate_mid', 0.048, 0.012, (0.5, 0, axis_z), Pk, rot=RX, seg=6),
               cyl('plate_front', 0.05, 0.014, (0.62, 0, axis_z), Ch, rot=RX, seg=6)]
    mats = ['strawberry', 'vanilla', 'chocolate', 'pistachio', 'lemon', 'vanilla']
    for i in range(6):
        a = i * math.pi / 3
        y, z = math.cos(a) * 0.034, axis_z + math.sin(a) * 0.034
        barrels.append(cyl('barrel', 0.013, 0.47, (0.405, y, z), Ch, rot=RX, seg=24))
        frost = shaped_cyl('frost', 0.06, lambda t, ang, i=i: 0.0148 * (1 + 0.08 * math.sin(ang * 5 + i) * math.sin(t * 9 + i) + 0.04 * math.cos(ang * 11)),
                           M['frost'], seg=32, rings=10)
        barrels.append(place(frost, (0.575, y, z), RX))
        star = shaped_cyl('nozzle', 0.032, lambda t, ang: 0.0165 * (1 - 0.18 * max(0.0, math.cos(ang * 8)) ** 2) * (1 - 0.15 * t), M[mats[i]], seg=64, rings=3)
        barrels.append(place(star, (0.641, y, z), RX))
        barrels.append(cyl('bore', 0.0075, 0.004, (0.6575, y, z), M['black'], rot=RX, seg=16))
    parts = {'IJs_Body': body, 'IJs_Scoops': (scoops, V((-0.01, 0, 0.12))), 'IJs_Barrels': (barrels, hub)}
    hands = (grip_hand((0.005, 0, -0.12), (-0.25, 0, -1), (0, -1, 0), 0.024, (1, 0, 0), (-0.16, -0.24, -0.42))
             + grip_hand((0.42, 0, -0.125), (0, 0, -1), (0, 1, 0), 0.022, (1, 0, 0), (0.2, 0.22, -0.44), watch=True))
    return parts, hands


# Viewmodel placement in camera space (camera looks +X): (location, rotation)
VIEWMODELS = {
    'katapult': (katapult, (0.78, 0.03, -0.33), (0, 0.08, 0.0)),
    'shotgun': (shotgun, (0.46, -0.2, -0.25), (0, -0.02, 0.035)),
    'sniper': (sniper, (0.44, -0.18, -0.23), (0, -0.015, 0.03)),
    'bazooka': (bazooka, (0.02, -0.27, -0.11), (0, -0.01, 0.11)),
    'ijsmachine': (ijsmachine, (0.52, -0.23, -0.26), (0, -0.04, 0.065)),
}


def build_viewmodel(key):
    fn, loc, rot = VIEWMODELS[key]
    parts, hands = fn()
    root = lib.empty(f'VM_{key.capitalize()}')
    for name, objs in parts.items():
        pivot = (0, 0, 0)
        if isinstance(objs, tuple):
            objs, pivot = objs
        o = join(objs, name, pivot)
        lib.set_parent(o, root)
    for o in hands:   # smooth the hands; the sleeves are dense enough already
        if not o.name.startswith(('cuff', 'sleeve')):
            lib.bake(subsurf(o, 1))
    arms = join(hands, f'{key.capitalize()}_Arms')
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

CLOSEUPS = {   # name: (camera, target, ortho scale or None for a 50 mm perspective)
    'katapult': (('side', (0.0, 3.0, 1.15), (0.0, 0, 1.15), 0.7), ('34', (-0.9, 0.7, 1.3), (0.0, 0, 1.15), None),
                 ('detail', (-0.5, -0.3, 1.45), (0.0, 0, 1.3), None)),
}


def sheet_closeups(key, root, rdir):
    """Product shots of one weapon (arms hidden) from the player's side, 3/4 front and over the shoulder."""
    saved = (root.location.copy(), root.rotation_euler.copy())
    root.location, root.rotation_euler = (0, 0, 1.0), (0, 0, 0)
    arms = bpy.data.objects[f'{key.capitalize()}_Arms']
    arms.hide_render = True
    bd = box('Backdrop_close', (10, 0.02, 6), (0.3, -1.6, 1.0), material('Backdrop', '#1d1e24', rough=0.9))
    shots = CLOSEUPS.get(key) or (('side', (0.3, 3.0, 1.03), (0.3, 0, 1.03), 1.75),
             ('34', (1.75, 1.0, 1.35), (0.45, 0, 1.03), None),
             ('detail', (-0.35, 0.55, 1.3), (0.15, 0, 1.08), None))
    for name, loc, tgt, ortho in shots:
        cam = lib.camera(f'Cam_{name}', loc, tgt, 50)
        if ortho:
            cam.data.type = 'ORTHO'
            cam.data.ortho_scale = ortho
        lib.render(bpy.context.scene, cam, os.path.join(rdir, f'{key}_{name}.png'))
    arms.hide_render = False
    cam = lib.camera('Cam_hands', (0.3, 0.75, 1.15), (-0.12, -0.08, 0.86), 40)
    lib.render(bpy.context.scene, cam, os.path.join(rdir, f'{key}_hands.png'))
    bd.hide_render = True
    root.location, root.rotation_euler = saved



def main():
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    only = next((a.split('=', 1)[1] for a in argv if a.startswith('--only=')), None)
    lib.reset_scene()
    make_materials()
    out_dir = os.path.join(ROOT, 'assets', 'models', 'weapons')
    tex_dir = os.path.join(ROOT, 'renders', 'weapons', 'bake')   # baked maps for inspection; the GLB embeds WebP copies
    os.makedirs(out_dir, exist_ok=True)
    roots = {k: build_viewmodel(k) for k in VIEWMODELS if not only or k == only}
    ice = ijsje()
    for k, r in roots.items():
        meshes = [o for o in r.children_recursive if o.type == 'MESH']
        if '--no-bake' not in argv:
            vmkit.bake_weapon(k, meshes, tex_dir, size=2048 if k in ('sniper', 'bazooka') else 1024)
        print(f'[weapons] {k}: {lib.tri_count(meshes)} tris, parts {[o.name for o in r.children]}')
        lib.export_glb(os.path.join(out_dir, f'{k}.glb'), [r] + list(r.children_recursive), images='WEBP')
    if not only:
        lib.export_glb(os.path.join(ROOT, 'assets', 'models', 'ijsje.glb'), [ice] + list(ice.children_recursive))
    if '--no-render' in argv:
        return

    scene = bpy.context.scene
    lib.preview_stage(scene, size=(1600, 900))
    rdir = os.path.join(ROOT, 'renders', 'weapons')
    os.makedirs(rdir, exist_ok=True)

    # --- product sheet: all weapons side by side on a dark backdrop (arms hidden)
    bpy.data.objects['PreviewGround'].hide_render = True
    if only:   # close-up turntable shots of just this weapon instead
        sheet_closeups(only, roots[only], rdir)
    backdrop = box('Backdrop', (6, 0.02, 4), (0.6, 0.6, 0.6), material('Backdrop', '#1d1e24', rough=0.9))
    saved = {k: (r.location.copy(), r.rotation_euler.copy()) for k, r in roots.items()}
    layout = {'sniper': ((-0.2, 0, 1.25), (0, 0, 0)), 'bazooka': ((-0.15, 0, 0.85), (0, 0, 0)),
              'shotgun': ((-0.25, 0, 0.45), (0, 0, 0)), 'katapult': ((1.15, 0, 0.42), (0, 0, math.pi / 2)),
              'ijsmachine': ((1.25, 0, 1.3), (0, 0, 0))}
    for k, (loc, rot) in layout.items():
        if k not in roots:
            continue
        roots[k].location, roots[k].rotation_euler = loc, rot
        bpy.data.objects[f'{k.capitalize()}_Arms'].hide_render = True
    ice.location = (1.15, 0, 0.75)
    ice.scale = (2.2, 2.2, 2.2)
    cam = lib.camera('Cam_sheet', (0.6, -3.2, 0.95), (0.6, 0, 0.9), 50)
    cam.data.type = 'ORTHO'
    cam.data.ortho_scale = 2.6
    if not only:
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
        if only and k != only:
            continue
        for k2, r in roots.items():
            for o in [r] + list(r.children_recursive):
                o.hide_render = (k2 != k)
        lib.render(scene, fpcam, os.path.join(rdir, f'{i + 1:02d}_fp_{k}.png'))
    if only:
        return
    rig.rotation_euler = (0, 0.55, math.pi / 2 + 0.5)  # glance down-left at the ice cream
    for r in roots.values():
        for o in [r] + list(r.children_recursive):
            o.hide_render = True
    lib.render(scene, fpcam, os.path.join(rdir, '05_fp_ijsje.png'))


if __name__ == '__main__':
    main()
