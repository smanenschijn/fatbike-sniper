"""Viewmodel material kit: 'smart' procedural materials, baked into one texture set per weapon.

Kit materials compute colour / roughness / metallic / normal with Cycles-only nodes: Bevel for rounded,
light-catching edges, AO for dirt in the seams, noise for chipped paint and scratches. None of that survives
glTF, so bake_weapon() unwraps all parts of a weapon into one atlas, bakes every channel to an image and
swaps in a single textured material (one draw call per part in Godot).
"""
import math
import os

import bpy

import lib

SOCK = {}            # material name -> {'color': socket, 'rough': socket, 'metal': socket}
KEEP = {'ScopeLens', 'SniperLens'}   # glassy materials that keep their own (unbaked) material


def _io(sockets, ident):
    return next(s for s in sockets if s.identifier == ident)


class _Graph:
    def __init__(self, m):
        self.nt = m.node_tree

    def node(self, kind, **props):
        n = self.nt.nodes.new(kind)
        for k, v in props.items():
            setattr(n, k, v)
        return n

    def put(self, sock, v):
        if isinstance(v, bpy.types.NodeSocket):
            self.nt.links.new(v, sock)
        elif isinstance(v, (tuple, list)) and len(v) == 3:
            sock.default_value = (*v, 1.0)
        else:
            sock.default_value = v

    def obj(self, scale=1.0):
        tc = self.node('ShaderNodeTexCoord').outputs['Object']
        if scale == 1.0:
            return tc
        n = self.node('ShaderNodeVectorMath', operation='SCALE')
        self.put(n.inputs[0], tc)
        self.put(n.inputs['Scale'], scale)
        return n.outputs[0]

    def noise(self, vec, scale, detail=4.0, rough=0.55):
        n = self.node('ShaderNodeTexNoise')
        self.put(n.inputs['Vector'], vec)
        n.inputs['Scale'].default_value = scale
        n.inputs['Detail'].default_value = detail
        n.inputs['Roughness'].default_value = rough
        return n.outputs['Fac']

    def math(self, op, a, b=0.0, clamp=False):
        n = self.node('ShaderNodeMath', operation=op, use_clamp=clamp)
        self.put(n.inputs[0], a)
        self.put(n.inputs[1], b)
        return n.outputs[0]

    def remap(self, x, a, b, c=0.0, d=1.0):
        n = self.node('ShaderNodeMapRange', clamp=True)
        self.put(n.inputs['Value'], x)
        n.inputs['From Min'].default_value = a
        n.inputs['From Max'].default_value = b
        n.inputs['To Min'].default_value = c
        n.inputs['To Max'].default_value = d
        return n.outputs['Result']

    def mix(self, fac, a, b, blend='MIX'):
        n = self.node('ShaderNodeMix', data_type='RGBA', blend_type=blend)
        self.put(_io(n.inputs, 'Factor_Float'), fac)
        self.put(_io(n.inputs, 'A_Color'), a)
        self.put(_io(n.inputs, 'B_Color'), b)
        return _io(n.outputs, 'Result_Color')

    def edge(self, radius):
        """~1 on convex/concave edges (where the bevelled normal bends away), 0 on flat faces."""
        bev = self.node('ShaderNodeBevel', samples=8)
        bev.inputs['Radius'].default_value = radius
        geo = self.node('ShaderNodeNewGeometry')
        dot = self.node('ShaderNodeVectorMath', operation='DOT_PRODUCT')
        self.put(dot.inputs[0], bev.outputs['Normal'])
        self.put(dot.inputs[1], geo.outputs['Normal'])
        return self.remap(_io(dot.outputs, 'Value'), 0.8, 0.995, 1.0, 0.0), bev.outputs['Normal']

    def cavity(self, dist):
        ao = self.node('ShaderNodeAmbientOcclusion', samples=16, only_local=True)
        ao.inputs['Distance'].default_value = dist
        return ao.outputs['AO']

    def bump(self, height, strength, normal, dist=0.001):
        n = self.node('ShaderNodeBump')
        n.inputs['Strength'].default_value = strength
        n.inputs['Distance'].default_value = dist
        self.put(n.inputs['Height'], height)
        self.put(n.inputs['Normal'], normal)
        return n.outputs['Normal']


def _lighter(rgb, k):
    return tuple(c + (1 - c) * k for c in rgb)


def smart(name, color, kind='paint', rough=0.5, metal=0.0, bevel=0.004, wear=1.0, coat=0.0, dirt=1.0, grain='Z'):
    """A kit material. kind: paint (chips to bare metal) | metal | wood | polymer | rubber | fabric | skin | plain."""
    if name in bpy.data.materials:
        return bpy.data.materials[name]
    m = bpy.data.materials.new(name)
    bsdf = lib._principled(m)
    g = _Graph(m)
    base = lib.hex_rgb(color)
    m.diffuse_color = (*base, 1)
    p = g.obj()
    edge, bev_n = g.edge(bevel)
    breakup = g.noise(g.obj(), 55.0, 6.0, 0.6)
    # worn edges: the bevel mask, eaten into by noise so it reads as chips rather than an outline
    worn = g.remap(g.math('MULTIPLY', edge, g.math('ADD', breakup, 0.15)), 0.32, 0.5, 0.0, wear)
    tone = g.mix(g.remap(g.noise(p, 7.0, 2.0), 0.3, 0.7, 0.0, 0.5), base, tuple(c * 0.82 for c in base))
    col, r, mt, height, hstr = tone, rough, metal, None, 0.0

    if kind == 'paint':       # chipped paint over steel (bazooka, accents)
        chip = g.math('MULTIPLY', worn, 0.9)
        col = g.mix(chip, tone, lib.hex_rgb('#b9bec6'))
        r = g.mix(chip, (rough,) * 3, (0.3,) * 3)
        mt = g.math('MAXIMUM', chip, metal)
        height, hstr = g.math('MULTIPLY', chip, -1.0), 0.25
    elif kind == 'metal':     # polished edges, scratches, faint smudges
        col = g.mix(g.math('MULTIPLY', worn, 0.7), tone, _lighter(base, 0.4))
        scratch = g.remap(g.noise(g.obj(), 90.0, 8.0, 0.75), 0.55, 0.72, 0.0, 0.18)
        smudge = g.remap(g.noise(p, 9.0, 3.0), 0.35, 0.75, -0.08, 0.12)
        r = g.math('ADD', g.math('ADD', rough, scratch), g.math('SUBTRACT', smudge, g.math('MULTIPLY', worn, 0.15)))
    elif kind == 'wood':      # grain lines along the part (bands vary across it: Z for stocks along X), varnished
        wave = g.node('ShaderNodeTexWave', wave_type='BANDS', bands_direction=grain, wave_profile='SAW')
        g.put(wave.inputs['Vector'], p)
        wave.inputs['Scale'].default_value = 9.0
        wave.inputs['Distortion'].default_value = 7.0
        wave.inputs['Detail'].default_value = 3.0
        grain = wave.outputs['Fac']
        col = g.mix(g.remap(grain, 0.1, 0.9, 0.0, 0.75), tone, tuple(c * 0.6 for c in base))
        col = g.mix(g.math('MULTIPLY', worn, 0.6), col, _lighter(base, 0.35))
        height, hstr = grain, 0.08
    elif kind == 'polymer':   # fine stipple, lighter worn edges
        col = g.mix(g.math('MULTIPLY', worn, 0.55), tone, _lighter(base, 0.3))
        height, hstr = g.noise(g.obj(), 420.0, 2.0), 0.12
    elif kind == 'rubber':
        col = g.mix(g.math('MULTIPLY', worn, 0.35), tone, _lighter(base, 0.2))
        height, hstr = g.noise(g.obj(), 260.0, 3.0), 0.35
    elif kind == 'fabric':    # fleece: soft fuzz, sun-faded highlights on the folds
        col = g.mix(g.math('MULTIPLY', edge, 0.35), tone, _lighter(base, 0.25))
        height, hstr = g.noise(g.obj(), 700.0, 4.0, 0.7), 0.3
    elif kind == 'waffle':    # ice-cream-cone diamond grid
        lines = []
        for ang in (0.7854, -0.7854):
            mp = g.node('ShaderNodeMapping')
            g.put(mp.inputs['Vector'], p)
            mp.inputs['Rotation'].default_value = (0.0, ang, 0.0)
            w = g.node('ShaderNodeTexWave', wave_type='BANDS', bands_direction='X', wave_profile='SIN')
            g.put(w.inputs['Vector'], mp.outputs['Vector'])
            w.inputs['Scale'].default_value = 40.0   # bands period = 2*pi / (20 * scale) m: ~8 mm cells
            w.inputs['Distortion'].default_value = 0.0
            lines.append(g.remap(w.outputs['Fac'], 0.78, 0.97, 0.0, 1.0))
        grid = g.math('MAXIMUM', lines[0], lines[1])
        col = g.mix(grid, tone, tuple(c * 0.62 for c in base))
        col = g.mix(g.math('MULTIPLY', worn, 0.4), col, _lighter(base, 0.3))
        height, hstr = g.math('SUBTRACT', 1.0, grid), 0.6
    elif kind == 'skin':      # flushed knuckles and creases
        col = tone
        height, hstr = g.noise(g.obj(), 300.0, 3.0), 0.05

    # dirt in seams and creases
    if dirt:
        cav = g.remap(g.cavity(0.025), 0.25, 1.0, 1.0 - 0.6 * dirt, 1.0)
        tint = lib.hex_rgb('#b3574a') if kind == 'skin' else (0.25, 0.22, 0.2)
        shade = g.mix(g.math('SUBTRACT', 1.0, cav), (1.0, 1.0, 1.0), tint)
        col = g.mix(1.0, col, shade, blend='MULTIPLY')

    def scalar(v):
        if isinstance(v, bpy.types.NodeSocket):
            if v.type == 'RGBA':   # a colour-mixed scalar
                n = g.node('ShaderNodeRGBToBW')
                g.put(n.inputs[0], v)
                return n.outputs[0]
            return v
        n = g.node('ShaderNodeValue')
        n.outputs[0].default_value = v
        return n.outputs[0]

    r, mt = scalar(r), scalar(mt)
    normal = g.bump(height, hstr, bev_n) if height is not None else bev_n
    g.put(bsdf.inputs['Base Color'], col)
    g.put(bsdf.inputs['Roughness'], r)
    g.put(bsdf.inputs['Metallic'], mt)
    g.put(bsdf.inputs['Normal'], normal)
    if coat:
        bsdf.inputs['Coat Weight'].default_value = coat
    SOCK[name] = {'color': col, 'rough': r, 'metal': mt}
    return m


# ---------------------------------------------------------------- baking

def _gpu(scene):
    scene.render.engine = 'CYCLES'
    try:
        prefs = bpy.context.preferences.addons['cycles'].preferences
        prefs.compute_device_type = 'METAL'
        prefs.get_devices()
        for d in prefs.devices:
            d.use = True
        scene.cycles.device = 'GPU'
    except Exception:  # noqa: BLE001 - fall back to CPU
        scene.cycles.device = 'CPU'


def _channel_socket(m, ch):
    """Socket feeding channel `ch` of material m (kit materials expose them; plain ones use the BSDF values)."""
    if m.name in SOCK:
        return SOCK[m.name][ch]
    bsdf = next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    inp = bsdf.inputs[{'color': 'Base Color', 'rough': 'Roughness', 'metal': 'Metallic'}[ch]]
    if inp.is_linked:
        return inp.links[0].from_socket
    if ch == 'color':
        n = m.node_tree.nodes.new('ShaderNodeRGB')
        n.outputs[0].default_value = inp.default_value
    else:
        n = m.node_tree.nodes.new('ShaderNodeValue')
        n.outputs[0].default_value = inp.default_value
    return n.outputs[0]


def unwrap(objs, margin=0.006):
    """One shared UV atlas for all objects (multi-object edit mode packs their islands together)."""
    for o in objs:
        me = o.data
        for uv in list(me.uv_layers):
            me.uv_layers.remove(uv)
        uv = me.uv_layers.new(name='UVMap')
        me.uv_layers.active = uv
        uv.active_render = True
    vl = bpy.context.view_layer
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:
        o.select_set(True)
    vl.objects.active = objs[0]
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(60), island_margin=margin, area_weight=0.0,
                             correct_aspect=True, scale_to_bounds=False)
    try:   # a fixed fraction of the atlas: the default 'scaled' margin shrinks to nothing around tiny islands (stencil letters)
        bpy.ops.uv.pack_islands(rotate=True, margin_method='FRACTION', margin=margin)
    except (TypeError, RuntimeError):
        bpy.ops.uv.pack_islands(rotate=True, margin=margin)
    bpy.ops.object.mode_set(mode='OBJECT')


def bake_weapon(key, objs, tex_dir, size=2048, samples=24):
    """Bake all `objs` into one texture set and give them a single material `VM_<key>`."""
    scene = bpy.context.scene
    prev_engine = scene.render.engine
    _gpu(scene)
    scene.cycles.samples = samples
    scene.render.bake.margin = 16
    unwrap(objs)
    mats = []
    for o in objs:
        for m in o.data.materials:
            if m and m not in mats:
                mats.append(m)
    targets = {}
    for m in mats:
        n = m.node_tree.nodes.new('ShaderNodeTexImage')
        n.name = 'BakeTarget'
        targets[m] = n

    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]

    os.makedirs(tex_dir, exist_ok=True)
    imgs = {}
    for ch, srgb in (('color', True), ('rough', False), ('metal', False), ('normal', False)):
        img = bpy.data.images.new(f'{key}_{ch}', size, size, alpha=False, float_buffer=False)
        img.colorspace_settings.name = 'sRGB' if srgb else 'Non-Color'
        if ch == 'normal':
            img.generated_color = (0.5, 0.5, 1.0, 1.0)
        for m, n in targets.items():
            n.image = img
            m.node_tree.nodes.active = n
        if ch == 'normal':
            bpy.ops.object.bake(type='NORMAL', normal_space='TANGENT', margin=16, use_clear=False)
        else:
            restore = []
            for m in mats:
                nt = m.node_tree
                out = next(x for x in nt.nodes if x.type == 'OUTPUT_MATERIAL' and x.is_active_output)
                prev = out.inputs['Surface'].links[0].from_socket if out.inputs['Surface'].is_linked else None
                em = nt.nodes.new('ShaderNodeEmission')
                nt.links.new(_channel_socket(m, ch), em.inputs['Color'])
                nt.links.new(em.outputs[0], out.inputs['Surface'])
                restore.append((nt, out, prev, em))
            bpy.ops.object.bake(type='EMIT', margin=16, use_clear=True)
            for nt, out, prev, em in restore:
                nt.nodes.remove(em)
                if prev is not None:
                    nt.links.new(prev, out.inputs['Surface'])
        img.filepath_raw = os.path.join(tex_dir, f'{key}_{ch}.png')
        img.file_format = 'PNG'
        img.save()
        imgs[ch] = img
    for m, n in targets.items():
        m.node_tree.nodes.remove(n)
    scene.render.engine = prev_engine

    vm = bpy.data.materials.new(f'VM_{key}')
    b = lib._principled(vm)
    nt = vm.node_tree
    for ch, inp in (('color', 'Base Color'), ('rough', 'Roughness'), ('metal', 'Metallic')):
        t = nt.nodes.new('ShaderNodeTexImage')
        t.image = imgs[ch]
        nt.links.new(t.outputs['Color'], b.inputs[inp])
    t = nt.nodes.new('ShaderNodeTexImage')
    t.image = imgs['normal']
    nm = nt.nodes.new('ShaderNodeNormalMap')
    nt.links.new(t.outputs['Color'], nm.inputs['Color'])
    nt.links.new(nm.outputs['Normal'], b.inputs['Normal'])

    # one baked material per part (+ any glassy KEEP material)
    for o in objs:
        me = o.data
        old = list(me.materials)
        new = [vm] + [m for m in dict.fromkeys(old) if m and m.name in KEEP]
        remap = [new.index(m) if (m and m.name in KEEP) else 0 for m in old]
        idx = [0] * len(me.polygons)
        me.polygons.foreach_get('material_index', idx)
        idx = [remap[i] if i < len(remap) else 0 for i in idx]
        me.materials.clear()
        for m in new:
            me.materials.append(m)
        me.polygons.foreach_set('material_index', idx)
        me.update()
    return vm
