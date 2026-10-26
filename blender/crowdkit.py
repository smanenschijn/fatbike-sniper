"""Crowd material kit: the fatbikers' glow-up toolbox.

The riders are recoloured in-game per material (Skin/Top/Bottom/...), so their detail can't live in a baked
colour atlas like the weapons'. Instead:
- bake_ao() bakes ambient occlusion + cavity into a vertex colour layer ('Col'); the glTF exports it as
  COLOR_0 and Godot multiplies it with the (recoloured) albedo.
- fabric() puts a near-white tiling weave texture (+ normal map) on a material, which also survives
  recolouring because Godot multiplies albedo_color with the texture.
- sweep() builds smooth limbs, fingers, brows and folds: a tube along a Catmull-Rom curve whose radius
  can vary along the curve and around it.

Material names with a suffix after '_' (e.g. 'Top_Rib') take their in-game colour from the part before it.
"""
import math
import os

import bmesh
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

import lib
import textures

V = Vector
VC = 'Col'


# ---------------------------------------------------------------- sweep

def _catmull(pts, t):
    """Point on a uniform Catmull-Rom curve through pts, t in [0, 1]."""
    n = len(pts) - 1
    if n == 1:
        return pts[0].lerp(pts[1], t)
    f = min(t * n, n - 1e-9)
    i = int(f)
    u = f - i
    p0 = pts[max(i - 1, 0)] if i > 0 else pts[0] * 2 - pts[1]
    p1, p2 = pts[i], pts[i + 1]
    p3 = pts[i + 2] if i + 2 <= n else pts[n] * 2 - pts[n - 1]
    return 0.5 * ((2 * p1) + (-p0 + p2) * u + (2 * p0 - 5 * p1 + 4 * p2 - p3) * u * u + (-p0 + 3 * p1 - 3 * p2 + p3) * u ** 3)


def frames(pts, samples, up=None):
    """[(centre, tangent, normal, binormal, t)] along the curve; normal starts toward `up` (parallel transport)."""
    pts = [V(p) for p in pts]
    cs = [_catmull(pts, i / (samples - 1)) for i in range(samples)]
    out = []
    n = None
    for i, c in enumerate(cs):
        a, b = cs[max(i - 1, 0)], cs[min(i + 1, samples - 1)]
        tg = (b - a).normalized()
        if n is None:
            h = V(up) if up is not None else (V((0, 0, 1)) if abs(tg.z) < 0.9 else V((1, 0, 0)))
            n = (h - tg * h.dot(tg)).normalized()
        else:
            n = (n - tg * n.dot(tg)).normalized()
        out.append((c, tg, n, tg.cross(n), i / (samples - 1)))
    return out


def _radius_fn(radius):
    if callable(radius):
        return radius
    if isinstance(radius, (int, float)):
        return lambda t, a: radius
    rs = list(radius)

    def f(t, a):
        x = t * (len(rs) - 1)
        i = min(int(x), len(rs) - 2)
        u = x - i
        u = u * u * (3 - 2 * u)
        return rs[i] * (1 - u) + rs[i + 1] * u
    return f


def surface(fr, radius, t_index, ang):
    """A point on a sweep's surface (for stripes/seams that follow it)."""
    c, tg, n, b, t = fr[t_index]
    return c + (n * math.cos(ang) + b * math.sin(ang)) * _radius_fn(radius)(t, ang)


def sweep(name, pts, radius, mat=None, seg=20, samples=24, caps=(True, True), up=None, cap_rings=5):
    """Tube along a smooth curve through pts. radius: number, list (per control point) or f(t, angle).
    Angle 0 points along the frame normal (toward `up` at the start)."""
    fr = frames(pts, samples, up)
    rf = _radius_fn(radius)
    bm = bmesh.new()
    rings = []

    def ring(c, n, b, t, scale=1.0, push=V((0, 0, 0))):
        return [bm.verts.new(c + push + (n * math.cos(2 * math.pi * k / seg) + b * math.sin(2 * math.pi * k / seg))
                             * rf(t, 2 * math.pi * k / seg) * scale) for k in range(seg)]

    c0, tg0, n0, b0, t0 = fr[0]
    poles = [None, None]
    if caps[0]:
        for j in range(cap_rings, 0, -1):
            phi = math.pi / 2 * j / (cap_rings + 0.0)
            if j == cap_rings:
                poles[0] = bm.verts.new(c0 - tg0 * rf(t0, 0) * 1.0)
                continue
            rings.append(ring(c0, n0, b0, t0, math.cos(phi), -tg0 * rf(t0, 0) * math.sin(phi)))
    for c, tg, n, b, t in fr:
        rings.append(ring(c, n, b, t))
    c1, tg1, n1, b1, t1 = fr[-1]
    if caps[1]:
        for j in range(1, cap_rings + 1):
            phi = math.pi / 2 * j / cap_rings
            if j == cap_rings:
                poles[1] = bm.verts.new(c1 + tg1 * rf(t1, 0))
                continue
            rings.append(ring(c1, n1, b1, t1, math.cos(phi), tg1 * rf(t1, 0) * math.sin(phi)))
    for r0, r1 in zip(rings, rings[1:]):
        for k in range(seg):
            k2 = (k + 1) % seg
            bm.faces.new((r0[k], r0[k2], r1[k2], r1[k]))
    if poles[0]:
        for k in range(seg):
            bm.faces.new((poles[0], rings[0][(k + 1) % seg], rings[0][k]))
    if poles[1]:
        for k in range(seg):
            bm.faces.new((poles[1], rings[-1][k], rings[-1][(k + 1) % seg]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return lib.obj_from_bm(bm, name, mat)


def bumps(t, centres, width, amp):
    """Sum of gaussian bumps along t: folds, bunching, knuckles."""
    return sum(amp * math.exp(-((t - c) / width) ** 2) for c in centres)


# ---------------------------------------------------------------- mesh helpers

def remesh(o, voxel, smooth=4, ratio=None):
    """Voxel-remesh (smooth union of overlapping blobs), relax, optionally decimate. Keeps the first material."""
    m = o.modifiers.new('remesh', 'REMESH')
    m.mode = 'VOXEL'
    m.voxel_size = voxel
    m.use_smooth_shade = True
    if smooth:
        s = o.modifiers.new('smooth', 'SMOOTH')
        s.factor = 0.8
        s.iterations = smooth
    if ratio:
        d = o.modifiers.new('decimate', 'DECIMATE')
        d.ratio = ratio
    keep = next((m for m in o.data.materials if m), None)
    lib.bake(o)
    o.data.materials.clear()     # joined into an empty mesh => slot 0 is empty; the remesh puts every face there
    o.data.materials.append(keep)
    o.data.polygons.foreach_set('use_smooth', [True] * len(o.data.polygons))
    return o


def conform(o, target, offset=0.002):
    """Shrink-wrap a flat decal (text, patch) onto a surface."""
    m = o.modifiers.new('wrap', 'SHRINKWRAP')
    m.target = target
    m.wrap_method = 'NEAREST_SURFACEPOINT'
    m.wrap_mode = 'OUTSIDE_SURFACE'
    m.offset = offset
    return lib.bake(o)


def dense(o, cuts=2):
    bm = bmesh.new()
    bm.from_mesh(o.data)
    bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=cuts, use_grid_fill=True)
    bm.to_mesh(o.data)
    bm.free()
    return o


# ---------------------------------------------------------------- ambient occlusion in vertex colours

def _hemisphere(k):
    """k cosine-weighted directions around +Z (deterministic spiral)."""
    out = []
    ga = math.pi * (3 - math.sqrt(5))
    for i in range(k):
        r = math.sqrt((i + 0.5) / k)
        a = i * ga
        out.append((r * math.cos(a), r * math.sin(a), math.sqrt(max(0.0, 1 - r * r))))
    return np.array(out)


def _world_mesh(objs):
    verts, polys = [], []
    for o in objs:
        if o.type != 'MESH':
            continue
        mw = o.matrix_world
        base = len(verts)
        verts += [mw @ v.co for v in o.data.vertices]
        polys += [[base + i for i in p.vertices] for p in o.data.polygons]
    return verts, polys


def bake_ao(targets, occluders, rays=32, dist=0.22, strength=0.8, cavity=1.6, ground=0.0, floor=0.25):
    """Bake AO (+ crease darkening) of every target into vertex colour 'Col'. Occluders include the targets."""
    bpy.context.view_layer.update()
    for o in set(targets) | set(occluders):
        if o.type == 'MESH':
            lib.bake(o)
    verts, polys = _world_mesh(occluders)
    if ground is not None:
        b = len(verts)
        verts += [V((-20, -20, ground)), V((20, -20, ground)), V((20, 20, ground)), V((-20, 20, ground))]
        polys.append([b, b + 1, b + 2, b + 3])
    bvh = BVHTree.FromPolygons(verts, polys, all_triangles=False)
    hemi = _hemisphere(rays)
    for o in targets:
        if o.type != 'MESH':
            continue
        me = o.data
        n_v = len(me.vertices)
        co = np.empty(n_v * 3)
        nor = np.empty(n_v * 3)
        me.vertices.foreach_get('co', co)
        me.vertices.foreach_get('normal', nor)
        mw = np.array(o.matrix_world)
        co = co.reshape(-1, 3) @ mw[:3, :3].T + mw[:3, 3]
        nm = np.linalg.inv(mw[:3, :3]).T
        nor = nor.reshape(-1, 3) @ nm.T
        nor /= np.maximum(np.linalg.norm(nor, axis=1, keepdims=True), 1e-9)
        helper = np.where(np.abs(nor[:, 2:3]) < 0.9, np.array([[0, 0, 1.0]]), np.array([[1.0, 0, 0]]))
        tx = np.cross(nor, helper)
        tx /= np.linalg.norm(tx, axis=1, keepdims=True)
        ty = np.cross(nor, tx)
        dirs = hemi[None, :, 0:1] * tx[:, None] + hemi[None, :, 1:2] * ty[:, None] + hemi[None, :, 2:3] * nor[:, None]
        origin = co + nor * 0.0015
        occ = np.zeros(n_v)
        rc = bvh.ray_cast
        for i in range(n_v):
            org = V(origin[i])
            s = 0.0
            for d in dirs[i]:
                hit = rc(org, V(d), dist)
                if hit[0] is not None:
                    s += 1.0 - hit[3] / dist
            occ[i] = s / rays
        ao = 1.0 - strength * occ
        # creases: neighbours sitting above the vertex' tangent plane => concave
        bm = bmesh.new()
        bm.from_mesh(me)
        bm.verts.ensure_lookup_table()
        cav = np.ones(n_v)
        for v in bm.verts:
            if not v.link_edges:
                continue
            c = sum(v.normal.dot((e.other_vert(v).co - v.co).normalized()) for e in v.link_edges) / len(v.link_edges)
            cav[v.index] = 1.0 - min(0.5, max(0.0, c) * cavity)
        bm.free()
        val = np.clip(ao * cav, floor, 1.0)
        attr = me.color_attributes.get(VC) or me.color_attributes.new(VC, 'FLOAT_COLOR', 'POINT')
        cols = np.repeat(val, 4).reshape(-1, 4)
        cols[:, 3] = 1.0
        attr.data.foreach_set('color', cols.ravel())
        me.color_attributes.active_color = attr
        me.attributes.default_color_name = VC


def solid_vc(objs, value=1.0):
    """Plain white vertex colour (for meshes that share an AO material but get no bake)."""
    for o in objs:
        if o.type != 'MESH':
            continue
        lib.bake(o)
        me = o.data
        attr = me.color_attributes.get(VC) or me.color_attributes.new(VC, 'FLOAT_COLOR', 'POINT')
        attr.data.foreach_set('color', [value, value, value, 1.0] * len(me.vertices))
        me.color_attributes.active_color = attr
        me.attributes.default_color_name = VC


# ---------------------------------------------------------------- materials

def _bsdf(m):
    return next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')


def use_ao(m):
    """Multiply the material's base colour with the 'Col' vertex colours (exported as COLOR_0)."""
    if m.get('ao'):
        return m
    nt = m.node_tree
    b = _bsdf(m)
    sock = b.inputs['Base Color']
    vc = nt.nodes.new('ShaderNodeVertexColor')
    vc.layer_name = VC
    mix = nt.nodes.new('ShaderNodeMix')
    mix.data_type = 'RGBA'
    mix.blend_type = 'MULTIPLY'
    mix.inputs['Factor'].default_value = 1.0
    if sock.links:
        nt.links.new(sock.links[0].from_socket, mix.inputs[6])
    else:
        mix.inputs[6].default_value = sock.default_value[:]
    nt.links.new(vc.outputs['Color'], mix.inputs[7])
    nt.links.new(mix.outputs[2], sock)
    m['ao'] = True
    return m


def fabric(m, kind, normal_strength=0.6):
    """Near-white tiling fabric detail: base colour = texture x colour (both survive glTF + recolouring)."""
    if m.get('fabric'):
        return m
    cp, npth = FABRIC_PATHS[kind]
    nt = m.node_tree
    b = _bsdf(m)
    tex = nt.nodes.new('ShaderNodeTexImage')
    tex.image = bpy.data.images.load(cp, check_existing=True)
    mix = nt.nodes.new('ShaderNodeMix')
    mix.data_type = 'RGBA'
    mix.blend_type = 'MULTIPLY'
    mix.inputs['Factor'].default_value = 1.0
    nt.links.new(tex.outputs['Color'], mix.inputs[6])
    mix.inputs[7].default_value = b.inputs['Base Color'].default_value[:]
    nt.links.new(mix.outputs[2], b.inputs['Base Color'])
    nimg = bpy.data.images.load(npth, check_existing=True)
    nimg.colorspace_settings.name = 'Non-Color'
    tn = nt.nodes.new('ShaderNodeTexImage')
    tn.image = nimg
    nmap = nt.nodes.new('ShaderNodeNormalMap')
    nmap.inputs['Strength'].default_value = normal_strength
    nt.links.new(tn.outputs['Color'], nmap.inputs['Color'])
    nt.links.new(nmap.outputs['Normal'], b.inputs['Normal'])
    m['fabric'] = kind
    return m


def variant(m, suffix, **overrides):
    """A copy of a recolourable material that keeps its in-game colour key (Top -> Top_Rib)."""
    name = f'{m.name}_{suffix}'
    if name in bpy.data.materials:
        return bpy.data.materials[name]
    c = m.copy()
    c.name = name
    b = _bsdf(c)
    for k, v in overrides.items():
        b.inputs[k].default_value = v
    return c


# ---------------------------------------------------------------- fabric textures (numpy, tileable)

FABRIC_SIZE = 512
FABRIC_TILE = {'tricot': 0.08, 'twill': 0.1}   # metres per texture tile (box_uv)


def _tricot(rng, size):
    """Tracksuit polyester: fine diagonal knit + soft mottling."""
    px = np.arange(size) / size
    X, Y = np.meshgrid(px, px)
    k = 48
    knit = 0.5 + 0.5 * np.sin(2 * np.pi * k * (X + Y)) * np.sin(2 * np.pi * k * (X - Y))
    mott = textures._noise(rng, size, 16)
    hgt = knit * 0.6 + mott * 0.4
    v = 0.9 + 0.08 * knit + 0.06 * (mott - 0.5)
    return np.repeat(v[..., None], 3, axis=2), hgt


def _twill(rng, size):
    """Cotton twill / jersey for trousers and shirts."""
    px = np.arange(size) / size
    X, Y = np.meshgrid(px, px)
    tw = 0.5 + 0.5 * np.sin(2 * np.pi * 64 * (X * 2 + Y))
    grain = rng.random((size, size))
    mott = textures._noise(rng, size, 32)
    hgt = tw * 0.7 + grain * 0.3
    v = 0.88 + 0.07 * tw + 0.05 * (grain - 0.5) + 0.06 * (mott - 0.5)
    return np.repeat(v[..., None], 3, axis=2), hgt


FABRICS = {'tricot': _tricot, 'twill': _twill}
FABRIC_PATHS = {}


def ensure_fabrics(out_dir, force=False):
    os.makedirs(out_dir, exist_ok=True)
    for i, (name, fn) in enumerate(FABRICS.items()):
        cp, npth = os.path.join(out_dir, f'fabric_{name}.png'), os.path.join(out_dir, f'fabric_{name}_n.png')
        if force or not (os.path.exists(cp) and os.path.exists(npth)):
            rgb, hgt = fn(np.random.default_rng(300 + i), FABRIC_SIZE)
            textures._save(f'fabric_{name}', rgb, cp)
            textures._save(f'fabric_{name}_n', textures._normal_from_height(hgt, 3.0), npth)
        FABRIC_PATHS[name] = (cp, npth)
    return FABRIC_PATHS


def fabric_uv(objs):
    """Box-project UVs at the right weave scale for the fabric on each object's first textured material."""
    for o in objs:
        if o.type != 'MESH':
            continue
        kinds = [m.get('fabric') for m in o.data.materials if m and m.get('fabric')]
        lib.box_uv(o, tile=FABRIC_TILE[kinds[0]] if kinds else 0.1)
