"""Skeleton + animations for the glow-up riders.

- Arms, legs and torso are skinned to one armature ('Rig'); head, hair, sunglasses, the knife and the phone hang
  rigidly on a bone (they become BoneAttachment3D nodes in Godot, so the hair can still fly off).
- Weights come from the joint planes of each limb chain (smooth band around elbow/knee/wrist), no heat solve.
- Animations are posed procedurally: hands and feet follow IK targets, spine and head get direct rotations.
  Every frame is evaluated with the constraints on, then written as plain FK keys (an own 'visual bake').

Animations (30 fps), named '<variant>_<name>':
  Pedal     one crank revolution (legs + hips); Godot scales its speed with the bike and turns the crank along
  Ride      subtle upper-body loop (breathing, looking around)
  ShakeFist right fist off the bar and shaken at you
  Shock     both hands off the bars, leaning back
  Phone     left hand to the ear with a phone (loop; the Phone prop is shown by the game)
  Windup    right hand pulls the knife from the waistband and cocks it behind the head (holds the last pose)
  Throw     the arm whips forward and returns to the bar
  Flail     arms windmilling, legs kicking (in the air after a hit)
  Splat     lying like a starfish (after landing)
"""
import math

import bpy
from mathutils import Euler, Matrix, Quaternion, Vector

import lib
import rider_v2 as r2
from build_fatbiker import AXIS, CHEST, HC, HIP

V = Vector
FPS = 30
BB = V((0.0, 0, 0.30))       # bottom bracket (crank axle)
CRANK = 0.17
PEDAL_Y = 0.15
ANKLE_OVER_PEDAL = V((-0.015, 0, 0.10))
SIDES = (('L', 1), ('R', -1))
LIMB_BONES = ('upper_arm', 'forearm', 'hand', 'thigh', 'shin', 'foot')


# ------------------------------------------------------------------------------------------- armature

def _bones(v):
    neck = CHEST + AXIS * 0.15
    mid = HIP.lerp(CHEST, 0.5)
    b = {'hips': (V((-0.2, 0, 0.86)), HIP, None), 'spine': (HIP, mid, 'hips'), 'chest': (mid, neck, 'spine'),
         'head': (neck, HC + V((0, 0, 0.2)), 'chest')}
    for side, s in SIDES:
        J = r2.joints(v, s)
        b[f'upper_arm.{side}'] = (J['sh'], J['el'], 'chest')
        b[f'forearm.{side}'] = (J['el'], J['wrist'], f'upper_arm.{side}')
        b[f'hand.{side}'] = (J['wrist'], J['knuck'], f'forearm.{side}')
        b[f'thigh.{side}'] = (J['hip'], J['knee'], 'hips')
        b[f'shin.{side}'] = (J['knee'], J['ankle'], f'thigh.{side}')
        b[f'foot.{side}'] = (J['ankle'], J['toe'], f'shin.{side}')
    return b


def build_rig(v, root):
    arm = bpy.data.armatures.new(f"Rig_{v['id']}")
    rig = lib.link(bpy.data.objects.new('Rig', arm))
    lib.set_parent(rig, root)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode='EDIT')
    spec = _bones(v)
    for name, (h, t, parent) in spec.items():
        eb = arm.edit_bones.new(name)
        eb.head, eb.tail = h, t
        # local Z points forward (or up for the arm/leg chains), so X is the bend axis
        eb.align_roll(V((1, 0, 0)) if name in ('hips', 'spine', 'chest', 'head') or name.startswith(('thigh', 'shin', 'foot'))
                      else V((0, 0, 1)))
        if parent:
            eb.parent = arm.edit_bones[parent]
            eb.use_connect = (eb.head - arm.edit_bones[parent].tail).length < 1e-4
    bpy.ops.object.mode_set(mode='OBJECT')
    for pb in rig.pose.bones:
        pb.rotation_mode = 'QUATERNION'
    rig['spec'] = {k: [list(h), list(t)] for k, (h, t, p) in spec.items()}
    return rig


def _smooth(x, b):
    u = min(1.0, max(0.0, (x + b) / (2 * b)))
    return u * u * (3 - 2 * u)


def skin_chain(o, chain, blends):
    """Weights along a bone chain [(bone, head, tail), ...]: each joint plane blends over +-blend metres."""
    groups = [o.vertex_groups.get(n) or o.vertex_groups.new(name=n) for n, h, t in chain]
    joints = []
    for i in range(len(chain) - 1):
        d = ((chain[i][2] - chain[i][1]).normalized() + (chain[i + 1][2] - chain[i + 1][1]).normalized()).normalized()
        joints.append((chain[i][2], d, blends[i]))
    mw = o.matrix_world
    for vtx in o.data.vertices:
        p = mw @ vtx.co
        f = [_smooth((p - J).dot(n), b) for J, n, b in joints]
        acc = 1.0
        for i, g in enumerate(groups):
            w = acc * (1 - f[i]) if i < len(f) else acc
            if i < len(f):
                acc *= f[i]
            if w > 1e-3:
                g.add([vtx.index], w, 'REPLACE')


def attach(o, rig, bone):
    """Rigid child of a bone, keeping its world transform."""
    bpy.context.view_layer.update()
    mw = o.matrix_world.copy()
    o.parent = rig
    o.parent_type = 'BONE'
    o.parent_bone = bone
    bpy.context.view_layer.update()
    o.matrix_world = mw


def build_phone(M):
    p = [lib.box('phone', (0.075, 0.012, 0.15), (0, 0, 0), M['phones'], bevel=0.008),
         lib.box('screen', (0.06, 0.004, 0.12), (0, -0.007, 0.005), M['screen'], bevel=0.003)]
    return lib.join(p, 'Rider_Phone')


def rig_rider(M, v, root):
    """Turn a freshly built v2 rider (parts under `root`) into a rigged one. Returns the armature."""
    rig = build_rig(v, root)
    spec = {k: (V(h), V(t)) for k, (h, t) in rig['spec'].items()}
    parts = {o.name.split('.')[0]: o for o in root.children if o is not rig}
    for side, s in SIDES:
        a = parts[f'Rider_Arm{side}']
        skin_chain(a, [(f'{n}.{side}', *spec[f'{n}.{side}']) for n in ('upper_arm', 'forearm', 'hand')], [0.06, 0.025])
        lg = parts[f'Rider_Leg{side}']
        skin_chain(lg, [(f'{n}.{side}', *spec[f'{n}.{side}']) for n in ('thigh', 'shin', 'foot')], [0.06, 0.03])
    skin_chain(parts['Rider_Torso'], [(n, *spec[n]) for n in ('hips', 'spine', 'chest')], [0.05, 0.07])
    for n in ('Rider_ArmL', 'Rider_ArmR', 'Rider_LegL', 'Rider_LegR', 'Rider_Torso'):
        lib.set_parent(parts[n], rig)
    for n, bone in (('Rider_Head', 'head'), ('Rider_Hair', 'head'), ('Rider_Sunglasses', 'head'), ('Rider_Knife', 'hips')):
        if n in parts:
            attach(parts[n], rig, bone)
    phone = build_phone(M)
    J = r2.joints(v, 1)
    phone.location = J['gc'] + V((0, -0.02, 0.06))
    attach(phone, rig, 'hand.L')
    phone.hide_render = True
    make_actions(v, rig)
    return rig


def bind(rig):
    """Add the armature modifiers (after the AO bake, which applies every modifier)."""
    for o in rig.children:
        if o.type == 'MESH' and o.parent_type == 'OBJECT' and o.vertex_groups:
            m = o.modifiers.new('rig', 'ARMATURE')
            m.object = rig


# ------------------------------------------------------------------------------------------- posing

class Poser:
    """IK targets for hands and feet + direct rotations for the spine; evaluates and bakes frames."""

    def __init__(self, v, rig):
        self.v, self.rig = v, rig
        self.rest = {}
        bpy.context.view_layer.update()
        for pb in rig.pose.bones:
            self.rest[pb.name] = rig.matrix_world @ pb.bone.matrix_local
        self.targets = {}
        cons = []
        for side, s in SIDES:
            for limb, lower, end in (('arm', 'forearm', 'hand'), ('leg', 'shin', 'foot')):
                t = lib.empty(f'T_{end}.{side}')
                t.matrix_world = self.rest[f'{end}.{side}']
                pole = lib.empty(f'P_{lower}.{side}')
                bpy.context.view_layer.update()
                mid = self.rest[f'{lower}.{side}'].translation
                bend = (mid - (self.rest[f'{"upper_arm" if limb == "arm" else "thigh"}.{side}'].translation
                               + self.rest[f'{end}.{side}'].translation) / 2)
                pole.location = mid + bend.normalized() * 0.5
                ik = rig.pose.bones[f'{lower}.{side}'].constraints.new('IK')
                ik.target, ik.pole_target, ik.chain_count = t, pole, 2
                cr = rig.pose.bones[f'{end}.{side}'].constraints.new('COPY_ROTATION')
                cr.target = t
                self.targets[f'{end}.{side}'] = t
                self.targets[f'pole_{lower}.{side}'] = pole
                cons.append((ik, f'{lower}.{side}'))
        for ik, bone in cons:
            ik.pole_angle = self._best_pole(ik, bone)

    def _best_pole(self, ik, bone):
        """The pole angle that reproduces the rest pose (no twist)."""
        best, err = 0.0, 1e9
        for deg in range(-180, 180, 3):
            ik.pole_angle = math.radians(deg)
            bpy.context.view_layer.update()
            pb = self.rig.pose.bones[bone]
            e = sum(abs(a - b) for ra, rb in zip(self.rig.matrix_world @ pb.matrix, self.rest[bone]) for a, b in zip(ra, rb))
            if e < err:
                best, err = math.radians(deg), e
        return best

    def set(self, pose):
        """pose: {'hand.L': (offset, euler), 'foot.R': (absolute_pos, euler), 'spine': euler, ...}."""
        for name, val in self.targets.items():
            if name.startswith('pole'):
                continue
            off, rot = pose.get(name, (V((0, 0, 0)), (0, 0, 0)))
            rest = self.rest[name]
            pos = off if pose.get(name + '#abs') else rest.translation + V(off)
            R = rest.to_quaternion()
            val.matrix_world = Matrix.LocRotScale(pos, Euler(rot, 'XYZ').to_quaternion() @ R, V((1, 1, 1)))
        for b in ('hips', 'spine', 'chest', 'head'):
            e = pose.get(b, (0, 0, 0))
            self.rig.pose.bones[b].rotation_quaternion = Euler(e, 'XYZ').to_quaternion()
        hip_off = pose.get('hips_loc', (0, 0, 0))
        self.rig.pose.bones['hips'].location = hip_off
        bpy.context.view_layer.update()

    def bake(self, name, frames, pose_fn, loop=False):
        """Evaluate pose_fn(t in [0,1]) per frame, store FK, then key it into a new action stashed on the NLA."""
        rig = self.rig
        n = frames + (0 if loop else 1)
        samples = []
        for f in range(n):
            self.set(pose_fn(f / frames))
            samples.append({pb.name: pb.matrix.copy() for pb in rig.pose.bones})
        muted = []
        for pb in rig.pose.bones:
            for c in pb.constraints:
                if not c.mute:
                    c.mute = True
                    muted.append(c)
        act = bpy.data.actions.new(f"{self.v['id']}_{name}")
        rig.animation_data_create()
        rig.animation_data.action = act
        for f, mats in enumerate(samples + ([samples[0]] if loop else [])):
            for pb in rig.pose.bones:   # parents first (pose.bones is in hierarchy order)
                pb.matrix = mats[pb.name]
                bpy.context.view_layer.update()
            for pb in rig.pose.bones:
                pb.keyframe_insert('rotation_quaternion', frame=f + 1)
                if pb.name == 'hips':
                    pb.keyframe_insert('location', frame=f + 1)
        for c in muted:
            c.mute = False
        track = rig.animation_data.nla_tracks.new()
        track.name = act.name
        strip = track.strips.new(act.name, 1, act)
        strip.name = act.name
        track.mute = True
        rig.animation_data.action = None
        return act

    def clear(self):
        for pb in self.rig.pose.bones:
            for c in list(pb.constraints):
                pb.constraints.remove(c)
            pb.matrix_basis = Matrix.Identity(4)
        for t in self.targets.values():
            bpy.data.objects.remove(t)


# ------------------------------------------------------------------------------------------- animations

def pedal_feet(t, side):
    """Ankle position on the pedal circle; t=0 is the rest pose (right pedal forward)."""
    ph = -2 * math.pi * t + (math.pi if side == 'L' else 0.0)
    return BB + V((math.cos(ph) * CRANK, (1 if side == 'L' else -1) * PEDAL_Y, math.sin(ph) * CRANK)) + ANKLE_OVER_PEDAL


def make_actions(v, rig):
    P = Poser(v, rig)
    sin, cos, pi = math.sin, math.cos, math.pi

    def riding(t, **extra):
        """Base: feet on the pedals at crank phase t, slight bob."""
        p = {}
        for side, s in SIDES:
            p[f'foot.{side}'] = (pedal_feet(t, side), (0, 0, 0))
            p[f'foot.{side}#abs'] = True
        p.update(extra)
        return p

    def pedal(t):
        return riding(t, hips=(0, 0, 0.04 * sin(2 * pi * t)), hips_loc=(0, 0.006 * abs(sin(2 * pi * t)), 0),
                      spine=(0, 0, -0.03 * sin(2 * pi * t)))
    P.bake('Pedal', 30, pedal, loop=True)

    def ride(t):
        a = 2 * pi * t
        return riding(0, spine=(0.02 * sin(a), 0, 0), chest=(0.025 * sin(a + 0.6), 0, 0.03 * sin(a * 2)),
                      head=(0.04 * sin(a + 1.2), 0, 0.12 * sin(a)))
    P.bake('Ride', 90, ride, loop=True)

    J = {s: r2.joints(v, sg) for s, sg in SIDES}

    def env(t, a, b):
        """0 -> 1 between a and b, back to 0 at the end (ease in/out)."""
        if t < a:
            return _ease(t / a)
        if t > b:
            return _ease((1 - t) / (1 - b))
        return 1.0

    def shake(t):
        k = env(t, 0.22, 0.75)
        wob = sin(t * 2 * pi * 5) * 0.06 * (1 if 0.22 < t < 0.8 else 0)
        fist = J['R']['sh'] + V((0.12, -0.12, 0.28)) - J['R']['wrist']
        return riding(0, **{'hand.R': (fist * k + V((wob, 0, abs(wob))), (0, -1.6 * k, 0.5 * k)),
                            'chest': (-0.1 * k, 0, -0.15 * k), 'spine': (0.05 * k, 0, 0), 'head': (0.1 * k, 0, 0.15 * k)})
    P.bake('ShakeFist', 40, shake)

    def shock(t):
        k = env(t, 0.15, 0.6)
        out = {}
        for side, s in SIDES:
            lift = J[side]['sh'] + V((0.05, s * 0.18, 0.22)) - J[side]['wrist']
            out[f'hand.{side}'] = (lift * k, (s * 0.8 * k, -1.2 * k, 0))
        return riding(0, spine=(-0.2 * k, 0, 0), chest=(-0.15 * k, 0, 0), head=(-0.25 * k, 0, 0), **out)
    P.bake('Shock', 30, shock)

    def phone(t):
        ear = HC + V((0.0, 0.16, -0.05)) - J['L']['wrist']
        return riding(0, **{'hand.L': (ear, (0.4, -1.9, -0.6)), 'head': (0, 0, 0.25 + 0.05 * sin(2 * pi * t)),
                            'chest': (0, 0, 0.08)})
    P.bake('Phone', 60, phone, loop=True)

    waist = HIP + V((0.12, -0.15, 0.0))
    cocked = J['R']['sh'] + V((-0.12, -0.08, 0.3))

    def windup(t):
        if t < 0.45:   # reach down to the waistband
            k = _ease(t / 0.45)
            pos = J['R']['wrist'].lerp(waist, k)
            rot = (0, 0.6 * k, 0)
        else:          # pull up and cock it behind the head
            k = _ease((t - 0.45) / 0.55)
            pos = waist.lerp(cocked, k)
            rot = (0, 0.6 - 2.4 * k, 0.4 * k)
        lean = _ease(min(1.0, t / 0.6))
        return riding(0, **{'hand.R': (pos - J['R']['wrist'], rot), 'chest': (-0.08 * lean, 0, -0.35 * lean),
                            'head': (0, 0, 0.2 * lean)})
    P.bake('Windup', 22, windup)

    def throw(t):
        if t < 0.3:    # whip forward
            k = _ease(t / 0.3)
            pos = cocked.lerp(J['R']['sh'] + V((0.45, 0.05, -0.05)), k)
            rot = (0, -1.8 + 1.6 * k, 0.4 - 0.4 * k)
            ch = -0.35 + 0.6 * k
        else:          # back on the bar
            k = _ease((t - 0.3) / 0.7)
            pos = (J['R']['sh'] + V((0.45, 0.05, -0.05))).lerp(J['R']['wrist'], k)
            rot = (0, -0.2 + 0.2 * k, 0)
            ch = 0.25 * (1 - k)
        return riding(0, **{'hand.R': (pos - J['R']['wrist'], rot), 'chest': (0, 0, ch)})
    P.bake('Throw', 24, throw)

    def flail(t):
        out = {}
        for side, s in SIDES:
            a = 2 * pi * t * 2 * s + (0 if side == 'L' else 1.3)
            c = J[side]['sh'] + V((0, s * 0.12, 0))
            hand = c + V((cos(a) * 0.4, s * 0.22, sin(a) * 0.4))
            out[f'hand.{side}'] = (hand - J[side]['wrist'], (sin(a) * 0.8, cos(a), 0))
            kick = sin(2 * pi * t * 3 + (0 if side == 'L' else pi))
            foot = J[side]['hip'] + V((0.25 + 0.2 * kick, s * 0.18, -0.45 + 0.12 * kick))
            out[f'foot.{side}'] = (foot, (0, kick * 0.6, 0))
            out[f'foot.{side}#abs'] = True
        return dict(out, spine=(0.1 * sin(2 * pi * t * 2), 0, 0.15 * sin(2 * pi * t)), head=(0.2 * sin(2 * pi * t * 3), 0, 0.3 * sin(2 * pi * t * 2)))
    P.bake('Flail', 30, flail, loop=True)

    def splat(t):
        out = {}
        for side, s in SIDES:
            hand = J[side]['sh'] + V((-0.05, s * 0.55, 0.12))
            out[f'hand.{side}'] = (hand - J[side]['wrist'], (0, -1.2, s * 0.6))
            foot = J[side]['hip'] + V((-0.1, s * 0.3, -0.62))
            out[f'foot.{side}'] = (foot, (0, 0.9, 0))
            out[f'foot.{side}#abs'] = True
        return dict(out, spine=(-0.25, 0, 0), chest=(-0.2, 0, 0), head=(-0.2, 0, 0.3))
    P.bake('Splat', 1, splat)
    P.clear()


def _ease(x):
    x = min(1.0, max(0.0, x))
    return x * x * (3 - 2 * x)
