"""Shared helpers for building Fatbike Sniper models in Blender (run headless).

Conventions: meters, +Z up, models face +X (forward). Every model is built from
separate parts which are joined into named objects that the game can address
individually (e.g. Rider_Head for headshots, Rider_Hair flying off).
"""
import math

import bmesh
import bpy
from mathutils import Matrix, Vector


# ---------------------------------------------------------------- scene

def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def link(obj, coll=None):
    (coll or bpy.context.scene.collection).objects.link(obj)
    return obj


def empty(name, loc=(0, 0, 0), parent=None):
    o = link(bpy.data.objects.new(name, None))
    o.location = loc
    o.empty_display_size = 0.2
    if parent:
        o.parent = parent
    return o


def set_parent(child, parent):
    bpy.context.view_layer.update()
    mw = child.matrix_world.copy()
    child.parent = parent
    child.matrix_world = mw


# ---------------------------------------------------------------- materials

def hex_rgb(h):
    """sRGB hex -> linear RGB tuple."""
    h = h.lstrip('#')
    out = []
    for i in (0, 2, 4):
        c = int(h[i:i + 2], 16) / 255
        out.append(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4)
    return tuple(out)


def _principled(m):
    try:
        m.use_nodes = True
    except AttributeError:
        pass
    nt = m.node_tree
    bsdf = next((n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED'), None)
    if bsdf is None:
        nt.nodes.clear()
        bsdf = nt.nodes.new('ShaderNodeBsdfPrincipled')
        out = nt.nodes.new('ShaderNodeOutputMaterial')
        nt.links.new(bsdf.outputs[0], out.inputs[0])
    return bsdf


def material(name, color, rough=0.5, metal=0.0, sheen=0.0, coat=0.0,
             emission=None, strength=0.0, sss=0.0):
    if name in bpy.data.materials:
        return bpy.data.materials[name]
    m = bpy.data.materials.new(name)
    b = _principled(m)
    rgb = hex_rgb(color)
    m.diffuse_color = (*rgb, 1)
    vals = {
        'Base Color': (*rgb, 1), 'Roughness': rough, 'Metallic': metal,
        'Sheen Weight': sheen, 'Coat Weight': coat, 'Subsurface Weight': sss,
    }
    if emission:
        vals['Emission Color'] = (*hex_rgb(emission), 1)
        vals['Emission Strength'] = strength
    for k, v in vals.items():
        if k in b.inputs:
            b.inputs[k].default_value = v
    return m


# ---------------------------------------------------------------- meshes

def obj_from_bm(bm, name, mat=None, smooth=True):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    if smooth:
        me.polygons.foreach_set('use_smooth', [True] * len(me.polygons))
    if mat:
        me.materials.append(mat)
    return link(bpy.data.objects.new(name, me))


def place(o, loc=None, rot=None, scale=None):
    if loc is not None:
        o.location = loc
    if rot is not None:
        o.rotation_euler = rot
    if scale is not None:
        o.scale = scale
    return o


def sphere(name, r, loc=(0, 0, 0), mat=None, scale=None, rot=None, seg=32, rings=16):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=rings, radius=r)
    return place(obj_from_bm(bm, name, mat), loc, rot, scale)


def ico(name, r, loc=(0, 0, 0), mat=None, scale=None, subdiv=2):
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=subdiv, radius=r)
    return place(obj_from_bm(bm, name, mat), loc, None, scale)


def box(name, size, loc=(0, 0, 0), mat=None, rot=None, bevel=0.0, segs=3, smooth=True):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=Vector(size), verts=bm.verts)
    o = place(obj_from_bm(bm, name, mat, smooth), loc, rot)
    if bevel:
        m = o.modifiers.new('bevel', 'BEVEL')
        m.width = bevel
        m.segments = segs
        m.limit_method = 'NONE'
        try:
            m.harden_normals = True
        except AttributeError:
            pass
    return o


def cyl(name, r, depth, loc=(0, 0, 0), mat=None, rot=None, seg=24, r2=None, caps=True, smooth=True):
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=caps, segments=seg, radius1=r,
                          radius2=r if r2 is None else r2, depth=depth)
    return place(obj_from_bm(bm, name, mat, smooth), loc, rot)


def orient(o, p1, p2):
    """Point the object's local +Z from p1 to p2, centred between them."""
    p1, p2 = Vector(p1), Vector(p2)
    d = p2 - p1
    o.location = (p1 + p2) / 2
    o.rotation_mode = 'QUATERNION'
    o.rotation_quaternion = d.to_track_quat('Z', 'X' if abs(d.normalized().x) < 0.9 else 'Y')
    return o


def tube(name, p1, p2, r, mat=None, r2=None, seg=16, caps=True):
    d = (Vector(p2) - Vector(p1)).length
    return orient(cyl(name, r, d, mat=mat, r2=r2, seg=seg, caps=caps), p1, p2)


def capsule(name, p1, p2, r1, r2=None, mat=None, sxy=(1, 1), seg=24, rings=16, rot_y_only=False):
    """Capsule between p1 (radius r1) and p2 (radius r2). sxy scales the cross-section."""
    r2 = r1 if r2 is None else r2
    p1, p2 = Vector(p1), Vector(p2)
    L = (p2 - p1).length
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=rings, radius=1.0)
    for v in bm.verts:
        c = v.co
        if c.z >= -1e-6:
            v.co = Vector((c.x * r2 * sxy[0], c.y * r2 * sxy[1], c.z * r2 + L / 2))
        else:
            v.co = Vector((c.x * r1 * sxy[0], c.y * r1 * sxy[1], c.z * r1 - L / 2))
    o = obj_from_bm(bm, name, mat)
    if rot_y_only:
        d = p2 - p1
        o.location = (p1 + p2) / 2
        o.rotation_euler = (0, math.atan2(d.x, d.z), 0)
        return o
    return orient(o, p1, p2)


def torus(name, R, r, loc=(0, 0, 0), mat=None, rot=None, segU=48, segV=12,
          arc=(0.0, 2 * math.pi), rz=None):
    """Torus around local Z. `rz` stretches the tube along Z (for fenders/tyres)."""
    rz = r if rz is None else rz
    closed = abs(arc[1] - arc[0] - 2 * math.pi) < 1e-6
    nu = segU if closed else segU + 1
    bm = bmesh.new()
    grid = []
    for i in range(nu):
        u = arc[0] + (arc[1] - arc[0]) * i / segU
        row = []
        for j in range(segV):
            v = 2 * math.pi * j / segV
            rr = R + r * math.cos(v)
            row.append(bm.verts.new((rr * math.cos(u), rr * math.sin(u), rz * math.sin(v))))
        grid.append(row)
    for i in range(segU):
        a, b = grid[i], grid[(i + 1) % nu]
        for j in range(segV):
            k = (j + 1) % segV
            bm.faces.new((a[j], b[j], b[k], a[k]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return place(obj_from_bm(bm, name, mat), loc, rot)


def extrude_profile(name, pts, thickness, mat=None, smooth=False):
    """Extrude a closed XZ-profile along Y (centered)."""
    bm = bmesh.new()
    front = [bm.verts.new((x, -thickness / 2, z)) for x, z in pts]
    back = [bm.verts.new((x, thickness / 2, z)) for x, z in pts]
    bm.faces.new(front)
    bm.faces.new(list(reversed(back)))
    n = len(pts)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((front[i], back[i], back[j], front[j]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return obj_from_bm(bm, name, mat, smooth)


# ---------------------------------------------------------------- modifiers / joining

def subsurf(o, levels=1):
    m = o.modifiers.new('subsurf', 'SUBSURF')
    m.levels = levels
    m.render_levels = levels
    return o


def bake(o):
    """Apply all modifiers into the mesh data."""
    if o.type != 'MESH' or not o.modifiers:
        return o
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(o.evaluated_get(dg))
    o.modifiers.clear()
    o.data = me
    return o


def join(objs, name, pivot=(0, 0, 0)):
    """Join meshes into a fresh object whose origin sits at `pivot` (identity rotation)."""
    objs = [bake(o) for o in objs]
    target = link(bpy.data.objects.new(name, bpy.data.meshes.new(name)))
    target.location = pivot
    bpy.context.view_layer.update()
    with bpy.context.temp_override(active_object=target, object=target,
                                   selected_objects=[target] + objs,
                                   selected_editable_objects=[target] + objs):
        bpy.ops.object.join()
    return target


def transform_mesh(o, matrix):
    o.data.transform(matrix)
    o.data.update()
    return o


ROT_X90 = Matrix.Rotation(math.pi / 2, 4, 'X')


def tri_count(objs):
    dg = bpy.context.evaluated_depsgraph_get()
    total = 0
    for o in objs:
        if o.type == 'MESH':
            me = o.evaluated_get(dg).to_mesh()
            me.calc_loop_triangles()
            total += len(me.loop_triangles)
            o.evaluated_get(dg).to_mesh_clear()
    return total


# ---------------------------------------------------------------- preview rendering

def set_engine(scene):
    for eng in ('BLENDER_EEVEE_NEXT', 'BLENDER_EEVEE'):
        try:
            scene.render.engine = eng
            return eng
        except TypeError:
            continue
    scene.render.engine = 'CYCLES'
    return 'CYCLES'


def preview_stage(scene, size=(1280, 960)):
    """Sunny Dutch-square preview: brick pavement, warm sun, blue sky."""
    set_engine(scene)
    scene.render.resolution_x, scene.render.resolution_y = size
    scene.render.resolution_percentage = 100
    ee = scene.eevee
    for attr, val in (('taa_render_samples', 64), ('use_raytracing', True),
                      ('use_shadows', True), ('use_gtao', True)):
        if hasattr(ee, attr):
            setattr(ee, attr, val)
    try:
        scene.view_settings.view_transform = 'AgX'
        scene.view_settings.look = 'AgX - Medium High Contrast'
    except TypeError:
        pass

    world = bpy.data.worlds.new('Sky')
    scene.world = world
    try:
        world.use_nodes = True
    except AttributeError:
        pass
    bg = next(n for n in world.node_tree.nodes if n.type == 'BACKGROUND')
    bg.inputs['Color'].default_value = (*hex_rgb('#a8c8ea'), 1)
    bg.inputs['Strength'].default_value = 0.75

    # klinkers (brick pavement)
    pave = bpy.data.materials.new('Pavement')
    _principled(pave)
    nt = pave.node_tree
    bsdf = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
    brick = nt.nodes.new('ShaderNodeTexBrick')
    brick.inputs['Color1'].default_value = (*hex_rgb('#a8553a'), 1)
    brick.inputs['Color2'].default_value = (*hex_rgb('#8a4430'), 1)
    brick.inputs['Mortar'].default_value = (*hex_rgb('#b8ab98'), 1)
    coords = nt.nodes.new('ShaderNodeTexCoord')
    nt.links.new(coords.outputs['Object'], brick.inputs['Vector'])
    brick.inputs['Scale'].default_value = 2.6
    brick.inputs['Brick Width'].default_value = 0.5
    brick.inputs['Row Height'].default_value = 0.25
    brick.inputs['Mortar Size'].default_value = 0.012
    nt.links.new(brick.outputs['Color'], bsdf.inputs['Base Color'])
    bsdf.inputs['Roughness'].default_value = 0.8
    plane = box('PreviewGround', (40, 40, 0.02), (0, 0, -0.01), pave, smooth=False)

    sun = bpy.data.lights.new('Sun', 'SUN')
    sun.energy = 5.5
    sun.color = (1.0, 0.88, 0.72)
    sun.angle = math.radians(2.5)
    so = link(bpy.data.objects.new('Sun', sun))
    so.rotation_euler = (math.radians(50), math.radians(8), math.radians(-35))

    fill = bpy.data.lights.new('Fill', 'AREA')
    fill.energy = 250
    fill.size = 4
    fill.color = (0.8, 0.88, 1.0)
    fo = link(bpy.data.objects.new('Fill', fill))
    fo.location = (-3, 3, 3)
    fo.rotation_euler = (math.radians(55), 0, math.radians(-135))
    return [plane, so, fo]


def camera(name, loc, target, lens=50):
    cam = bpy.data.cameras.new(name)
    cam.lens = lens
    o = link(bpy.data.objects.new(name, cam))
    o.location = loc
    tgt = empty(name + '_target', target)
    c = o.constraints.new('TRACK_TO')
    c.target = tgt
    c.track_axis = 'TRACK_NEGATIVE_Z'
    c.up_axis = 'UP_Y'
    return o


def render(scene, cam, path):
    scene.camera = cam
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)


def export_glb(path, objects):
    bpy.ops.object.select_all(action='DESELECT')
    for o in objects:
        o.select_set(True)
    bpy.ops.export_scene.gltf(filepath=path, export_format='GLB', use_selection=True,
                              export_apply=True, export_yup=True)


# ---------------------------------------------------------------- textured materials / UVs / text / instances

def tex_material(name, color_png, normal_png=None, rough=0.8, normal_strength=1.0):
    if name in bpy.data.materials:
        return bpy.data.materials[name]
    m = bpy.data.materials.new(name)
    b = _principled(m)
    nt = m.node_tree
    img = bpy.data.images.load(color_png, check_existing=True)
    t = nt.nodes.new('ShaderNodeTexImage')
    t.image = img
    nt.links.new(t.outputs['Color'], b.inputs['Base Color'])
    b.inputs['Roughness'].default_value = rough
    if normal_png:
        nimg = bpy.data.images.load(normal_png, check_existing=True)
        nimg.colorspace_settings.name = 'Non-Color'
        tn = nt.nodes.new('ShaderNodeTexImage')
        tn.image = nimg
        nm = nt.nodes.new('ShaderNodeNormalMap')
        nm.inputs['Strength'].default_value = normal_strength
        nt.links.new(tn.outputs['Color'], nm.inputs['Color'])
        nt.links.new(nm.outputs['Normal'], b.inputs['Normal'])
    return m


def box_uv(o, tile=2.0):
    """World-space box projection, so textures keep real-world scale across objects."""
    bpy.context.view_layer.update()
    me = o.data
    uv = me.uv_layers.get('UVMap') or me.uv_layers.new(name='UVMap')
    mw = o.matrix_world
    nm = mw.to_3x3()
    verts = me.vertices
    for poly in me.polygons:
        n = nm @ poly.normal
        ax = max(range(3), key=lambda i: abs(n[i]))
        for li in poly.loop_indices:
            p = mw @ verts[me.loops[li].vertex_index].co
            if ax == 2:
                u, v = p.x, p.y
            elif ax == 0:
                u, v = p.y * (1 if n.x > 0 else -1), p.z
            else:
                u, v = p.x * (-1 if n.y > 0 else 1), p.z
            uv.data[li].uv = (u / tile, v / tile)
    return o


def text_mesh(name, body, size, loc=(0, 0, 0), rot=(math.pi / 2, 0, 0), mat=None, extrude=0.015):
    """Text converted to a mesh object (faces -Y by default, reads along +X)."""
    cu = bpy.data.curves.new(name, 'FONT')
    cu.body = body
    cu.size = size
    cu.extrude = extrude
    cu.align_x = 'CENTER'
    cu.align_y = 'CENTER'
    tmp = link(bpy.data.objects.new(name + '_curve', cu))
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(tmp.evaluated_get(dg))
    bpy.data.objects.remove(tmp)
    if mat:
        me.materials.clear()
        me.materials.append(mat)
    o = link(bpy.data.objects.new(name, me))
    return place(o, loc, rot)


def instance(src, name, loc, rot_z=0.0, scale=1.0, coll=None):
    """Linked duplicate (shares mesh data => glTF instancing)."""
    o = link(bpy.data.objects.new(name, src.data), coll)
    o.location = loc
    o.rotation_euler = (0, 0, rot_z)
    o.scale = (scale, scale, scale)
    return o


def collection(name, parent=None):
    c = bpy.data.collections.new(name)
    (parent or bpy.context.scene.collection).children.link(c)
    return c


def move_to(o, coll):
    for c in list(o.users_collection):
        c.objects.unlink(o)
    coll.objects.link(o)
    return o


def lathe(name, profile, mat=None, seg=32, smooth=True):
    """Revolve a list of (radius, z) points around Z."""
    bm = bmesh.new()
    rings = []
    for r, z in profile:
        rings.append([bm.verts.new((r * math.cos(2 * math.pi * i / seg), r * math.sin(2 * math.pi * i / seg), z))
                      for i in range(seg)])
    for a, b in zip(rings, rings[1:]):
        for i in range(seg):
            j = (i + 1) % seg
            bm.faces.new((a[i], a[j], b[j], b[i]))
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return obj_from_bm(bm, name, mat, smooth)


def basis(x_dir, z_dir):
    """Rotation matrix whose local Z = z_dir and local X ~ x_dir."""
    z = Vector(z_dir).normalized()
    x = Vector(x_dir)
    x = (x - z * x.dot(z)).normalized()
    y = z.cross(x)
    return Matrix((x, y, z)).transposed()


def orient_basis(o, R, loc):
    o.rotation_mode = 'QUATERNION'
    o.rotation_quaternion = R.to_quaternion()
    o.location = loc
    return o
