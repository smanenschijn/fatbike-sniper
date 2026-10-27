"""FATBIKETRON: the end boss, a hunched combiner robot built from five taken-apart fatbikes.

Glow-up (2026-10-27): finer articulation (hinged jaw, wrists, claw fingers, ankles, hydraulics across every big
joint), a bigger head with extra eyes and a spoke crest, dorsal spikes, glowing vents, smoking exhaust stacks and
baked AO in the vertex colours (crowdkit).

Every limb is made from the parts of one fatbike in one team colour: fenders become armour blades and
spikes, batteries armour plates, handlebars horns, crank arms claws, wheels feet, hip discs and a
shield. Behind the armour sits a gunmetal skeleton with bronze gears and chains. Shooting a limb
knocks all its bike parts off; the skeleton stays. The head wears a broccoli haircut made of fatbike
tyres and the right forearm carries a rocket launcher.

Exports `assets/models/boss.glb` (faces +X, feet on the ground):
- `Boss`
  - `Boss_Hips`                         pelvis pivot
    - `Boss_Pelvis`
    - `Boss_Leg{L,R}_Pivot`             hip    -> `Boss_Leg?_Frame_Upper`, `Boss_Bike_Leg?_Upper`
      - `Boss_Knee{L,R}`                knee   -> `Boss_Leg?_Frame_Lower`, `Boss_Bike_Leg?_Lower` (shin)
        - `Boss_Ankle{L,R}`             ankle  -> `Boss_Leg?_Frame_Foot` (claw toes), `Boss_Bike_Leg?_Foot` (wheels)
    - `Boss_Spine`                      waist pivot (rest pose leans forward)
      - `Boss_Chest`, `Boss_Core` (glowing chest light), `Boss_Bike_Torso`
      - `Boss_Arm{L,R}_Pivot`           shoulder -> `Boss_Arm?_Frame_Upper`, `Boss_Bike_Arm?_Upper`
        - `Boss_Elbow{L,R}`             elbow  -> `Boss_Arm?_Frame_Lower`, `Boss_Bike_Arm?_Lower` (+ `Boss_Launcher`,
                                                  `Boss_Muzzle_0..5` on the right)
          - `Boss_Wrist{L,R}`           wrist  -> `Boss_Bike_Arm?_Hand`
            - `Boss_Finger{L,R}{0..3}`  claw fingers (3 + thumb) -> `Boss_Bike_Arm?_Finger?`
      - `Boss_Neck`                     -> `Boss_Head`, `Boss_Hair` (scaled up)
        - `Boss_Jaw`                    -> `Boss_HeadJaw`
      - `Boss_Exhaust_{0,1}`            tips of the exhaust stacks (smoke)
  - `Boss_Piston{A,B}_<joint>`          hydraulic rams across hips, knees, ankles, shoulders, elbows, neck and jaw:
                                        sleeve and rod on the two sides of the joint, re-aimed at each other in-game
- `Boss_Rocket`                         projectile template (points +X)

Every node whose name starts with `Boss_Bike_<Limb>` belongs to that limb's bike.

Run:  Blender -b -P blender/build_boss.py [-- --no-render]
"""
import math
import os
import random
import sys

import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(__file__))
import lib  # noqa: E402
import build_fatbiker as fb  # noqa: E402
import crowdkit as ck  # noqa: E402
from lib import box, capsule, cyl, join, material, sphere, torus, tube  # noqa: E402

ROOT = fb.ROOT
V = Vector
random.seed(11)

WHEEL_S = 2.2                       # wheels are the real fatbike wheel, scaled
WHEEL_R = 0.345 * WHEEL_S
LEAN = math.radians(16)             # hunched forward

# five bikes, five colours (frame, accent) -- the combiner team
TEAM = {
    'Torso': ('#24262b', '#ff7a1a'),
    'LegL': ('#1d2f55', '#7cff6b'),
    'LegR': ('#7a1820', '#f2f2f2'),
    'ArmL': ('#243f2d', '#ffd23f'),
    'ArmR': ('#c9c9cf', '#ff3b6b'),
}


def mats():
    M = fb.mats()
    M.update({
        'metal': material('BossMetal', '#3e434c', rough=0.4, metal=0.85),
        'dark': material('BossDark', '#18191d', rough=0.5, metal=0.6),
        'bronze': material('BossBronze', '#7a5234', rough=0.38, metal=0.9),
        'joint': material('BossJoint', '#a3abb5', rough=0.22, metal=1.0),
        'tape': material('DuctTape', '#b7bac0', rough=0.65, metal=0.2),
        'eye': material('BossEye', '#ff1a10', rough=0.2, emission='#ff2a1a', strength=24),
        'core': material('BossCore', '#ffe9b0', rough=0.1, emission='#ffcf6a', strength=8),
        'mouth': material('BossMouth', '#120808', rough=0.6),
        'fang': material('BossFang', '#e9e4d6', rough=0.3, metal=0.3),
        'rocket': material('RocketRed', '#e63946', rough=0.35, coat=0.5),
        'rocket_w': material('RocketWhite', '#f4f4f4', rough=0.35),
        'flame': material('RocketFlame', '#ffb03a', rough=0.5, emission='#ff8a1f', strength=10),
        'glow': material('BossGlow', '#ff5a1a', rough=0.3, emission='#ff4a10', strength=7),
        'cable': material('BossCable', '#15171a', rough=0.7),
    })
    return M


def team(M, limb):
    frame, accent = TEAM[limb]
    m = dict(M)
    m['frame'] = material(f'BossFrame_{limb}', frame, rough=0.4, metal=0.4, coat=0.35)
    m['accent'] = material(f'BossAccent_{limb}', accent, rough=0.35, coat=0.5)
    return m


# ================================================================ placement helpers

def put(o, loc, R=None, scale=1.0):
    """Set an object's world matrix from a location, a 3x3 rotation and a uniform scale."""
    R = R if R is not None else Matrix.Identity(3)
    o.matrix_world = Matrix.Translation(V(loc)) @ R.to_4x4() @ Matrix.Scale(scale, 4)
    return o


def rot_between(a, b):
    return V(a).normalized().rotation_difference(V(b).normalized()).to_matrix()


def decimate(o, ratio):
    d = o.modifiers.new('decimate', 'DECIMATE')
    d.ratio = ratio
    return lib.bake(o)


def lerp(a, b, t):
    return V(a).lerp(V(b), t)


# ================================================================ fatbike parts

_wheel_cache = {}


def wheel(m, limb, center, axle):
    """The real fatbike wheel (axle along local Y), scaled up and turned so its axle points along `axle`."""
    if limb not in _wheel_cache:
        _wheel_cache[limb] = decimate(fb.build_wheel(f'tmpl_wheel_{limb}', m, rear=True), 0.28)
    o = lib.link(bpy.data.objects.new('wheel', _wheel_cache[limb].data.copy()))
    return put(o, center, rot_between((0, 1, 0), axle), WHEEL_S)


def blade(m, center, axis, start, sweep_deg, R, width, thick=0.06, spike=0.45, mat=None, spike_start=0.0):
    """A fender turned into an armour blade: an arc of ribbon around `axis`, starting at direction `start`,
    sweeping `sweep_deg` (right-handed), with a spike continuing from the end."""
    mat = mat or m['frame']
    sw = math.radians(sweep_deg)
    arc = (0.0, sw) if sw > 0 else (sw, 0.0)
    parts = [torus('fender', R, thick, mat=mat, segU=28, segV=6, arc=arc, rz=width / 2),
             torus('trim', R + thick * 0.8, thick * 0.35, mat=m['accent'], segU=28, segV=4, arc=arc, rz=width * 0.08)]

    def tip(a, length, direction):
        p = V((R * math.cos(a), R * math.sin(a), 0))
        t = V((-math.sin(a), math.cos(a), 0)) * direction
        c = cyl('spike', min(width * 0.3, thick * 2.6), length, mat=mat, r2=0.0, seg=5, smooth=False)
        lib.orient(c, p, p + t * length)
        c.scale = (1.0, 0.45, 1.0)
        return c

    sgn = 1 if sw > 0 else -1
    if spike:
        parts.append(tip(sw, spike, sgn))
    if spike_start:
        parts.append(tip(0.0, spike_start, -sgn))
    return put(join(parts, 'blade'), center, lib.basis(start, axis))


def battery(m, a, b, width=0.42, depth=0.3, outward=(0, 0, 1)):
    """E-bike battery as an armour plate between a and b, its flat side facing `outward`."""
    a, b = V(a), V(b)
    d = b - a
    L = d.length
    parts = [box('battery', (L, width, depth), mat=m['frame'], bevel=0.06, segs=3),
             box('stripe', (L * 0.75, width * 1.02, depth * 0.2), (0, 0, depth * 0.18), m['accent']),
             box('lock', (0.08, width * 1.04, 0.08), (-L * 0.4, 0, 0), m['chrome'], bevel=0.015)]
    x = d.normalized()
    z = V(outward).normalized()
    z = (z - x * z.dot(x)).normalized()
    return put(join(parts, 'battery'), (a + b) / 2, Matrix((x, z.cross(x), z)).transposed())


def frame_tube(m, a, b, r=0.1, mat=None):
    return capsule('frame_tube', a, b, r, r * 0.9, mat or m['frame'], seg=12, rings=6)


def gear(M, center, axis, r, teeth=14, mat=None):
    """Chainring / sprocket: an exposed bronze gear."""
    mat = mat or M['bronze']
    parts = [cyl('gear', r, 0.06, mat=mat, seg=32), cyl('gear_hub', r * 0.3, 0.12, mat=M['joint'], seg=12)]
    for i in range(teeth):
        a = 2 * math.pi * i / teeth
        t = box('tooth', (r * 0.18, r * 0.16, 0.06), (math.cos(a) * r * 1.04, math.sin(a) * r * 1.04, 0), mat, smooth=False)
        t.rotation_euler = (0, 0, a)
        parts.append(t)
    for i in range(5):
        a = 2 * math.pi * i / 5 + 0.3
        parts.append(box('gear_hole', (r * 0.28, r * 0.2, 0.065), (math.cos(a) * r * 0.62, math.sin(a) * r * 0.62, 0),
                         M['dark'], rot=(0, 0, a), smooth=False))
    return put(join(parts, 'gear'), center, rot_between((0, 0, 1), axis))


def disc(M, center, axis, r):
    parts = [cyl('disc', r, 0.025, mat=M['steel'], seg=28), cyl('disc_hub', r * 0.35, 0.06, mat=M['dark'], seg=12)]
    for i in range(6):
        a = 2 * math.pi * i / 6
        parts.append(cyl('disc_hole', r * 0.09, 0.03, (math.cos(a) * r * 0.68, math.sin(a) * r * 0.68, 0), M['dark'], seg=8))
    return put(join(parts, 'disc'), center, rot_between((0, 0, 1), axis))


def chain(M, pts, r=0.035):
    return [tube('chain', a, b, r, M['dark'], seg=6) for a, b in zip(pts, pts[1:])]


def seat(m, center, length_dir, up):
    o = lib.subsurf(box('seat', (0.95, 0.38, 0.14), mat=m['seat'], bevel=0.05, segs=3), 1)
    trim = box('seat_trim', (0.97, 0.39, 0.03), (0, 0, -0.06), m['accent'], bevel=0.01)
    return put(join([o, trim], 'seat'), center, lib.basis(length_dir, up))


def horn(m, a, b, c):
    """Handlebar half as a horn: bar a->b->c, grip at c, brake lever as a barb."""
    a, b, c = V(a), V(b), V(c)
    d = (c - b).normalized()
    tip = cyl('grip_tip', 0.07, 0.35, mat=m['accent'], r2=0.0, seg=8)
    lib.orient(tip, c + d * 0.4, c + d * 0.75)
    return [tube('bar', a, b, 0.07, m['chrome'], seg=12), sphere('bar_joint', 0.07, b, m['chrome'], seg=12, rings=6),
            tube('bar', b, c, 0.065, m['chrome'], seg=12),
            capsule('grip', c, c + d * 0.4, 0.1, 0.07, m['rubber'], seg=12, rings=6), tip,
            tube('lever', c - d * 0.1, c - d * 0.1 + (b - a).normalized() * 0.45 + V((0, 0, -0.15)), 0.03, m['rim'], seg=6)]


def claw(M, m, wrist, fwd, side, down):
    """A hand: pedal palm + three crank-arm fingers and a thumb, with brake-lever talons.
    Returns (palm parts, [(finger base, finger parts), ...])."""
    fwd, side, down = V(fwd).normalized(), V(side).normalized(), V(down).normalized()
    fwd = (fwd - down * fwd.dot(down)).normalized()
    palm = put(box('palm', (0.55, 0.5, 0.35), mat=M['dark'], bevel=0.06), wrist + down * 0.15, lib.basis(fwd, -down))
    pedal = put(box('pedal', (0.5, 0.52, 0.08), mat=m['rubber'], bevel=0.02), wrist + down * 0.1 + fwd * 0.3,
                lib.basis(fwd, -down))
    parts = [palm, pedal, sphere('wrist_ball', 0.2, wrist, M['joint'], seg=14, rings=8)]
    fingers = []
    for off in (-0.2, 0.0, 0.2, None):
        if off is None:   # thumb, on the inner side
            base = wrist + down * 0.2 - side * 0.3 + fwd * 0.1
            d1 = (fwd * 0.5 - side * 0.6 + down * 0.4).normalized()
            d2 = (fwd * 0.8 + down * 0.6).normalized()
            l1, l2 = 0.35, 0.3
        else:
            base = wrist + down * 0.3 + fwd * 0.22 + side * off
            d1 = (fwd * 0.7 + down * 0.7 + side * off).normalized()
            d2 = (fwd * 0.2 + down * 1.0).normalized()
            l1, l2 = 0.5, 0.42
        k = base + d1 * l1
        tipp = k + d2 * l2
        talon = cyl('talon', 0.075, 0.46, mat=M['chrome'], r2=0.0, seg=6)
        lib.orient(talon, tipp, tipp + (d2 + fwd * 0.3).normalized() * 0.46)
        fingers.append((base, [sphere('knuckle', 0.1, base, M['joint'], seg=10, rings=6),
                               tube('crank_arm', base, k, 0.075, m['rim'], seg=8), sphere('knuckle', 0.09, k, M['joint'], seg=10, rings=6),
                               tube('crank_arm', k, tipp, 0.065, m['rim'], seg=8), talon]))
    return parts, fingers


# ================================================================ skeleton helpers

def bone(M, a, b, r=0.17):
    return [capsule('bone', a, b, r, r * 0.85, M['metal'], seg=14, rings=6)]


def piston(M, a, b, r=0.07):
    a, b = V(a), V(b)
    mid = lerp(a, b, 0.55)
    return [tube('piston_sleeve', a, mid, r * 1.7, M['dark'], seg=12), tube('piston_rod', mid, b, r, M['joint'], seg=10)]


def ball(M, c, r):
    return [sphere('joint', r, c, M['joint'], seg=20, rings=10)]


# ================================================================ layout (upright, before the lean)

HIP_Z = 4.25
SPINE = V((-0.25, 0, 4.75))
NECK = V((0.15, 0, 8.05))
HEAD_C = V((0.5, 0, 8.55))


def leg_points(s):
    return V((-0.25, s * 0.95, HIP_Z)), V((0.6, s * 1.55, 2.45)), V((0.2, s * 1.95, WHEEL_R))


def arm_points(s):
    return V((-0.1, s * 1.55, 7.45)), V((0.0, s * 2.35, 5.45)), V((0.55, s * 2.55, 3.75))


# ================================================================ limbs

def build_leg(M, s):
    limb = 'LegL' if s > 0 else 'LegR'
    m = team(M, limb)
    hip, knee, foot = leg_points(s)
    out = V((0, s, 0))
    thigh = knee - hip

    # skeleton
    up = bone(M, hip, knee, 0.22) + ball(M, hip, 0.42) + piston(M, hip + V((-0.35, 0, -0.2)), knee + V((-0.3, 0, 0.2)))
    lo = bone(M, knee, foot + V((-0.2, 0, 0.25)), 0.2) + ball(M, knee, 0.36)
    lo += piston(M, knee + V((-0.35, 0, -0.1)), foot + V((-0.55, 0, 0.5)))
    ankle = foot + V((-0.25, 0, 0.35))
    ft = [box('ankle', (0.55, 0.55, 0.5), ankle, M['dark'], bevel=0.08), sphere('ankle_ball', 0.3, ankle, M['joint'], seg=16, rings=8)]
    for k in (-1, 1):   # a pair of claw toes in front of the wheels
        t0 = foot + V((0.55, k * 0.35, -0.1))
        tc = cyl('toe', 0.12, 0.55, mat=M['chrome'], r2=0.0, seg=6)
        lib.orient(tc, t0, t0 + V((0.9, k * 0.15, -0.35)).normalized() * 0.55)
        ft.append(tc)
    lo.append(gear(M, knee + out * 0.32, out, 0.42))

    fwd = V((1, 0, 0))
    # bike, upper: hip guard blade over a chainring, battery as front thigh plate, frame tubes, seat on the outer thigh
    bu = [gear(M, hip + out * 0.45, out, 0.55, mat=M['chrome']),
          blade(m, hip + V((-0.1, 0, -0.25)), (0, 0, 1), (1, s * 0.35, 0), s * 150, 0.82, 0.95, thick=0.09, spike=0.0),
          battery(m, hip + thigh * 0.12 + V((0.32, 0, 0)), hip + thigh * 0.88 + V((0.3, 0, 0)), width=0.8, depth=0.34,
                  outward=(1, s * 0.25, 0.3)),
          frame_tube(m, hip + V((0.1, s * 0.3, -0.2)), knee + V((0.0, s * 0.25, 0.3)), 0.13),
          frame_tube(m, hip + V((0.1, -s * 0.25, -0.2)), knee + V((0.0, -s * 0.2, 0.25)), 0.11),
          seat(m, lerp(hip, knee, 0.5) + out * 0.38, thigh, (0, s, 0))]
    bu += chain(M, [hip + out * 0.3 + V((0, 0, 0.35)), knee + out * 0.36 + V((0, 0, 0.4))])
    # bike, lower: big kneepad blade, shin plate, fork tubes, both wheels side by side as a tread foot under a boot fender
    shin_a, shin_b = knee + V((0.3, 0, -0.35)), foot + V((0.55, 0, 0.75))
    bl = [blade(m, knee + V((0.05, 0, 0.05)), out, (0.0, 0, 1), 130, 0.62, 1.2, thick=0.1, spike=0.6),
          battery(m, shin_a, shin_b, width=1.15, depth=0.36, outward=(1, 0, 0.3)),
          ]
    bf = [blade(m, foot, out, (-0.85, 0, 0.5), 150, WHEEL_R + 0.18, 1.6, thick=0.08, spike=0.8, spike_start=0.45)]
    for k in (-1, 1):
        bl.append(frame_tube(m, knee + V((0.0, k * 0.3, -0.1)), foot + V((-0.1, k * 0.55, 0.1)), 0.1))
        bf.append(wheel(m, limb, foot + V((0, k * 0.42, 0)), out))
    bf.append(disc(M, foot + out * 0.78, out, 0.36))
    bl += chain(M, [knee + out * 0.36, foot + out * 0.78])

    return hip, knee, ankle, (join(up, f'Boss_{limb}_Frame_Upper', pivot=hip), join(bu, f'Boss_Bike_{limb}_Upper', pivot=hip)), \
        (join(lo, f'Boss_{limb}_Frame_Lower', pivot=knee), join(bl, f'Boss_Bike_{limb}_Lower', pivot=knee)), \
        (join(ft, f'Boss_{limb}_Frame_Foot', pivot=ankle), join(bf, f'Boss_Bike_{limb}_Foot', pivot=ankle))


def build_pelvis(M):
    p = [box('pelvis', (1.0, 1.4, 0.75), (-0.3, 0, HIP_Z + 0.1), M['metal'], bevel=0.12),
         tube('hip_axle', (-0.25, -0.95, HIP_Z), (-0.25, 0.95, HIP_Z), 0.2, M['joint'], seg=16),
         gear(M, (0.22, 0, HIP_Z + 0.05), (1, 0, 0), 0.32)]
    # waist: a column of brake discs and bronze spacers, flanked by pistons
    for i in range(5):
        z = HIP_Z + 0.5 + i * 0.2
        p.append(cyl('waist_disc', 0.5 - 0.03 * (i % 2), 0.06, (-0.25, 0, z), M['steel'] if i % 2 else M['bronze'], seg=24))
        p.append(cyl('waist_spacer', 0.32, 0.16, (-0.25, 0, z + 0.1), M['dark'], seg=16))
    for k in (-1, 1):
        p += piston(M, (-0.25, k * 0.55, HIP_Z + 0.3), (-0.2, k * 0.6, HIP_Z + 1.6), 0.06)
        p.append(box('vent', (0.6, 0.04, 0.05), (-0.3, k * 0.71, HIP_Z + 0.15), M['glow']))
    return join(p, 'Boss_Pelvis', pivot=(-0.25, 0, HIP_Z))


def build_torso(M):
    m = team(M, 'Torso')
    c = V((-0.15, 0, 6.75))
    sk = [box('chest', (1.6, 2.2, 2.3), c, M['metal'], bevel=0.18),
          box('ribcage', (0.5, 1.5, 1.2), c + V((0.75, 0, -0.65)), M['dark'], bevel=0.1)]
    # bronze innards showing between the plates
    sk += [gear(M, c + V((0.98, s * 0.42, -0.75)), (1, 0, 0), 0.38) for s in (-1, 1)]
    sk += [gear(M, c + V((1.02, 0, -0.35)), (1, 0, 0), 0.25)]
    sk += chain(M, [c + V((1.0, -0.42, -0.4)), c + V((1.05, 0, -0.15)), c + V((1.0, 0.42, -0.4)),
                    c + V((1.0, 0.42, -1.1)), c + V((1.0, -0.42, -1.1)), c + V((1.0, -0.42, -0.4))])
    for s in (-1, 1):
        sk += piston(M, c + V((0.6, s * 0.95, -1.1)), c + V((0.6, s * 1.05, 0.7)), 0.06)
        sk += ball(M, arm_points(s)[0], 0.48)
    sk.append(box('neck_block', (0.7, 0.8, 0.5), NECK + V((-0.15, 0, -0.1)), M['dark'], bevel=0.08))
    for s in (-1, 1):
        for k in range(4):   # glowing vents along the flanks and the back
            sk.append(box('vent', (0.5, 0.04, 0.05), c + V((0.1, s * 1.11, -0.5 + k * 0.18)), M['glow']))
            sk.append(box('vent', (0.04, 0.5, 0.05), c + V((-0.81, s * 0.5, -0.6 + k * 0.18)), M['glow']))
        # exhaust stacks: two chrome pipes from the back past the shoulders
        e0, e1, e2 = c + V((-0.85, s * 0.55, -0.6)), c + V((-1.15, s * 0.65, 0.4)), c + V((-1.2, s * 0.7, 1.75))
        sk += [tube('exhaust', e0, e1, 0.13, M['chrome'], seg=12), sphere('exhaust_bend', 0.13, e1, M['chrome'], seg=12, rings=6),
               tube('exhaust', e1, e2, 0.13, M['chrome'], seg=12),
               cyl('exhaust_tip', 0.16, 0.25, e2 + V((0, 0, 0.1)), M['dark'], r2=0.2, seg=12)]
        sk += [tube('cable', c + V((0.4, s * 0.9, 0.9)), arm_points(s)[0] + V((0.25, -s * 0.1, -0.35)), 0.06, M['cable'], seg=8)]
    for k, (z, l) in enumerate(((0.2, 1.3), (0.75, 1.9), (1.25, 1.6))):   # dorsal spikes: brake-disc fins on the back
        for s in (-1, 1):
            base = c + V((-0.75, s * 0.32, z))
            sp = cyl('dorsal', 0.2, l, mat=M['chrome'], r2=0.0, seg=6, smooth=False)
            lib.orient(sp, base, base + V((-0.55, s * 0.35, 1.0)).normalized() * l)
            sk.append(sp)
            sk.append(cyl('dorsal_base', 0.26, 0.2, base, M['dark'], rot=(0, math.radians(-30), 0), seg=8))
    sk += bone(M, NECK, NECK + V((0.2, 0, 0.35)), 0.2)
    chest = join(sk, 'Boss_Chest', pivot=SPINE)

    # the chest light: a giant fatbike headlight
    cz = c + V((0.98, 0, 0.05))
    q = [cyl('core_body', 0.36, 0.3, cz - V((0.1, 0, 0)), M['dark'], rot=(0, math.pi / 2, 0), seg=32),
         torus('core_ring', 0.36, 0.05, cz + V((0.06, 0, 0)), M['joint'], rot=(0, math.pi / 2, 0), segU=32, segV=6),
         cyl('core_lens', 0.31, 0.05, cz + V((0.05, 0, 0)), M['core'], rot=(0, math.pi / 2, 0), seg=32)]
    core = join(q, 'Boss_Core', pivot=cz)

    # torso bike: pec blades, battery sternum, handlebar horns, back wheels like turbines, seat as spine plate
    b = []
    for s in (-1, 1):
        b.append(battery(m, c + V((0.98, s * 0.12, 1.0)), c + V((0.86, s * 1.05, 0.5)), width=0.75, depth=0.28,
                         outward=(1, s * 0.15, 0.45)))
        b.append(blade(m, c + V((-0.2, s * 0.9, 0.55)), (1, 0, 0), (0, -s * 0.5, 1), -s * 70, 0.75, 1.3, thick=0.09, spike=0.0))
        b.append(frame_tube(m, c + V((0.82, s * 0.25, -1.15)), c + V((0.75, s * 1.05, -0.05)), 0.1))
        b.append(frame_tube(m, c + V((0.7, s * 0.2, -1.2)), c + V((0.35, s * 1.15, 0.6)), 0.09))
        b += horn(m, NECK + V((0.1, s * 0.55, -0.15)), NECK + V((0.35, s * 0.95, 0.5)), NECK + V((0.75, s * 1.0, 0.95)))
        b.append(wheel(m, 'Torso', c + V((-1.1, s * 0.62, 0.6)), (-1, s * 0.55, 0.25)))
    b.append(seat(m, c + V((-0.85, 0, -0.5)), (0, 0, 1), (-1, 0, 0)))
    b.append(gear(M, c + V((-1.25, 0, 0.6)), (-1, 0, 0), 0.34, mat=M['chrome']))
    exhausts = [c + V((-1.2, s * 0.7, 2.0)) for s in (1, -1)]
    return chest, core, join(b, 'Boss_Bike_Torso', pivot=SPINE), exhausts


def build_arm(M, s):
    limb = 'ArmL' if s > 0 else 'ArmR'
    m = team(M, limb)
    sho, elbow, wrist = arm_points(s)
    out = V((0, s, 0))

    up = bone(M, sho, elbow, 0.2) + ball(M, elbow, 0.34) + piston(M, sho + V((0.3, 0, -0.3)), elbow + V((0.3, 0, 0.25)))
    lo = bone(M, elbow, wrist, 0.17) + ball(M, wrist, 0.22) + piston(M, elbow + V((-0.25, 0, 0)), wrist + V((-0.25, 0, 0.2)))
    lo.append(gear(M, elbow + out * 0.32, out, 0.36))

    # upper arm: shoulder wheel under a stack of pauldron blades, battery bicep, frame tube
    bu = [wheel(m, limb, sho + out * 0.45 + V((0, 0, -0.1)), out)]
    # pauldron: two caps sweeping from behind over the shoulder to the front, spikes on top
    for R, w, dy, dz in ((1.15, 1.15, 0.35, 0.0), (0.9, 0.8, 0.95, -0.35)):
        bu.append(blade(m, sho + V((0, s * dy, dz)), (0, s, 0), (-0.75, 0, 0.65), s * 150, R, w, thick=0.1, spike=0.0))
    for k, (dx, dy, l) in enumerate(((-0.35, 0.3, 0.9), (0.15, 0.55, 1.1), (0.55, 0.85, 0.7))):
        base = sho + V((dx, s * dy, 1.0 - 0.15 * k))
        sp = cyl('spike', 0.13, l, mat=m['frame'], r2=0.0, seg=5, smooth=False)
        lib.orient(sp, base, base + V((-0.35, s * 0.45, 1.0)).normalized() * l)
        bu.append(sp)
    bu.append(battery(m, lerp(sho, elbow, 0.25) + out * 0.25, lerp(sho, elbow, 0.92) + out * 0.25, width=0.5, depth=0.3,
                      outward=(0.3, s, 0)))
    bu.append(frame_tube(m, sho + V((0.3, s * 0.1, -0.4)), elbow + V((0.25, 0, 0.2)), 0.1))
    bu += chain(M, [sho + out * 0.35, elbow + out * 0.36])

    # forearm: fork tubes, a blade on the elbow, claw
    bl = [frame_tube(m, elbow + V((0.15, k * 0.18, 0)), wrist + V((0, k * 0.2, 0.1)), 0.085) for k in (-1, 1)]
    bl.append(blade(m, elbow + V((-0.1, s * 0.1, 0.1)), out, (-0.3, 0, 1), 60, 0.55, 0.45, thick=0.07, spike=0.6))
    fdir = (wrist - elbow).normalized()
    palm, fingers = claw(M, m, wrist + fdir * 0.15, (1, 0, 0), out, fdir)
    hand = join(palm, f'Boss_Bike_{limb}_Hand', pivot=wrist)
    fingers = [(base, join(fp, f'Boss_Bike_{limb}_Finger{i}', pivot=base)) for i, (base, fp) in enumerate(fingers)]
    launcher = muzzles = None
    if s > 0:   # left forearm: a wheel strapped on as a buzzsaw shield
        mid = lerp(elbow, wrist, 0.5)
        bl.append(wheel(m, limb, mid + out * 0.55, out))
        bl.append(blade(m, mid + out * 0.5, out, (-1, 0, 0.4), 140, WHEEL_R + 0.15, 0.4, thick=0.06, spike=0.5))
    else:       # right: wheel as an elbow disc, launcher on the forearm
        bl.append(wheel(m, limb, elbow + out * 0.6, out))
        launcher, muzzles = build_launcher(M, m, elbow, wrist, s)

    return sho, elbow, wrist, (join(up, f'Boss_{limb}_Frame_Upper', pivot=sho), join(bu, f'Boss_Bike_{limb}_Upper', pivot=sho)), \
        (join(lo, f'Boss_{limb}_Frame_Lower', pivot=elbow), join(bl, f'Boss_Bike_{limb}_Lower', pivot=elbow)), launcher, muzzles, \
        hand, fingers


def build_launcher(M, m, elbow, wrist, s):
    """Six-tube rocket pod on top of the right forearm; muzzles point along the forearm, past the claw."""
    d = (wrist - elbow).normalized()
    up = V((0, 0, 1))
    up = (up - d * up.dot(d)).normalized()
    side = up.cross(d)
    c = lerp(elbow, wrist, 0.45) + up * 0.62
    L = 2.1
    R = Matrix((d, side, up)).transposed()   # local X along the forearm
    p = [box('pod', (L, 0.95, 0.75), mat=M['dark'], bevel=0.08),
         box('pod_stripe', (0.22, 0.97, 0.77), (L / 2 - 0.35, 0, 0), m['accent'], bevel=0.03),
         box('pod_stripe', (0.22, 0.97, 0.77), (-L / 2 + 0.3, 0, 0), m['accent'], bevel=0.03),
         box('sight', (0.5, 0.12, 0.25), (0.2, 0.3, 0.45), M['dark'], bevel=0.03),
         cyl('sight_lens', 0.07, 0.03, (0.46, 0.3, 0.48), M['eye'], rot=(0, math.pi / 2, 0), seg=10)]
    local_muzzles = []
    for i in range(6):
        col, row = i % 3, i // 3
        y, z = (col - 1) * 0.29, (row - 0.5) * 0.32
        x1 = L / 2 + 0.12
        p.append(tube('tube', (-L / 2 + 0.2, y, z), (x1, y, z), 0.13, M['metal'], seg=14))
        p.append(cyl('tube_hole', 0.1, 0.02, (x1 + 0.005, y, z), M['mouth'], rot=(0, math.pi / 2, 0), seg=14))
        p.append(sphere('warhead', 0.1, (x1 - 0.1, y, z), M['rocket'], seg=10, rings=6))
        local_muzzles.append(V((x1 + 0.12, y, z)))
    for x in (-0.4, 0.45):   # duct-tape straps
        p.append(box('strap', (0.16, 1.0, 1.3), (x, 0, -0.35), M['tape'], bevel=0.03))
    pod = put(join(p, 'Boss_Launcher'), c, R)
    return pod, [c + R @ lm for lm in local_muzzles]


# ================================================================ head & hair

JAW_HINGE = HEAD_C + V((-0.12, 0, -0.2))
HEAD_SCALE_UP = 1.3


def build_head(M):
    """Upper skull (Boss_Head) and a hinged jaw (Boss_HeadJaw). Slanted visor eyes, a second pair of small eyes
    below, glowing cheek vents, long upper fangs, a crest of spokes."""
    c = HEAD_C
    p = [box('cranium', (0.95, 0.92, 0.7), c + V((-0.08, 0, 0.12)), M['metal'], bevel=0.14, segs=3)]
    face = lib.extrude_profile('face', [(-0.35, 0.3), (0.42, 0.22), (0.58, 0.05), (0.56, -0.18), (0.3, -0.24),
                                        (-0.15, -0.28), (-0.4, -0.2)], 0.8, M['metal'])
    face.location = c
    p.append(face)
    for s_ in (-1, 1):
        p.append(box('brow', (0.38, 0.44, 0.14), c + V((0.42, s_ * 0.21, 0.23)), M['dark'], bevel=0.03,
                     rot=(s_ * math.radians(30), math.radians(-14), 0)))
        p.append(box('socket', (0.08, 0.32, 0.13), c + V((0.55, s_ * 0.19, 0.07)), M['mouth'], bevel=0.02,
                     rot=(s_ * math.radians(24), 0, 0)))
        p.append(box('eye', (0.08, 0.27, 0.06), c + V((0.585, s_ * 0.19, 0.075)), M['eye'], bevel=0.015,
                     rot=(s_ * math.radians(24), 0, 0)))
        p.append(box('eye2', (0.06, 0.09, 0.05), c + V((0.585, s_ * 0.13, -0.06)), M['eye'], bevel=0.012,
                     rot=(s_ * math.radians(15), 0, 0)))
        p.append(box('cheek', (0.32, 0.12, 0.3), c + V((0.3, s_ * 0.42, -0.1)), M['dark'], bevel=0.04,
                     rot=(s_ * math.radians(-12), 0, 0)))
        for k in range(3):   # glowing cheek vents
            p.append(box('vent', (0.18, 0.03, 0.03), c + V((0.3, s_ * 0.485, -0.02 - k * 0.07)), M['glow'],
                         rot=(s_ * math.radians(-12), 0, 0)))
        p.append(disc(M, c + V((-0.05, s_ * 0.47, -0.02)), (0, s_, 0), 0.24))
        for k in range(3):   # upper fangs, long and hooked forward
            y = s_ * (0.07 + k * 0.1)
            p.append(cyl('fang', 0.05, 0.3 - k * 0.07, c + V((0.53, y, -0.32)), M['fang'], rot=(math.pi, math.radians(-12), 0),
                         r2=0.0, seg=6))
    p.append(box('upper_mouth', (0.16, 0.66, 0.12), c + V((0.47, 0, -0.24)), M['mouth'], bevel=0.03))
    p.append(box('nose_ridge', (0.2, 0.12, 0.35), c + V((0.55, 0, 0.0)), M['metal'], bevel=0.04, rot=(0, math.radians(15), 0)))
    for k in range(5):   # crest: chrome spokes raking back over the skull
        base = c + V((0.25 - k * 0.2, 0, 0.42 - k * 0.02))
        sp = cyl('crest', 0.06, 0.55 - k * 0.04, mat=M['chrome'], r2=0.0, seg=5, smooth=False)
        lib.orient(sp, base, base + V((-0.75, 0, 0.6)).normalized() * (0.55 - k * 0.04))
        p.append(sp)
    head = join(p, 'Boss_Head', pivot=NECK)

    j = [box('jaw', (0.62, 0.7, 0.2), c + V((0.25, 0, -0.42)), M['dark'], bevel=0.05),
         box('lower_mouth', (0.14, 0.6, 0.1), c + V((0.48, 0, -0.34)), M['mouth'], bevel=0.03),
         box('chin', (0.3, 0.42, 0.16), c + V((0.48, 0, -0.5)), M['metal'], bevel=0.05, rot=(0, math.radians(-10), 0))]
    for s_ in (-1, 1):
        j.append(box('jaw_arm', (0.5, 0.1, 0.16), JAW_HINGE + V((0.18, s_ * 0.38, -0.12)), M['metal'], bevel=0.03,
                     rot=(0, math.radians(25), 0)))
        j.append(sphere('jaw_hinge', 0.1, JAW_HINGE + V((0, s_ * 0.4, 0)), M['joint'], seg=12, rings=6))
        for k in range(3):
            y = s_ * (0.09 + k * 0.1)
            j.append(cyl('fang', 0.045, 0.18 - k * 0.03, c + V((0.5, y, -0.34)), M['fang'], r2=0.0, seg=6))
    jaw = join(j, 'Boss_HeadJaw', pivot=JAW_HINGE)
    return head, jaw


def build_hair(M):
    """Broccoli haircut: a lumpy dome of fatbike tyres with team-colour rims."""
    c = HEAD_C + V((-0.12, 0, 0.5))
    R = V((0.78, 0.82, 0.55))
    accents = [team(M, k)['accent'] for k in TEAM]
    p = []
    n = 40
    golden = math.pi * (3 - math.sqrt(5))
    for i in range(n):
        zz = 1 - (i + 0.5) / n * 1.15
        if zz < -0.12:
            continue
        rr = math.sqrt(max(0.0, 1 - zz * zz))
        th = golden * i
        nrm = V((math.cos(th) * rr, math.sin(th) * rr, zz))
        pos = c + V((nrm.x * R.x, nrm.y * R.y, max(nrm.z, -0.05) * R.z + 0.1))
        size = random.uniform(0.7, 0.95) * (1.0 if zz > 0.2 else 0.85)
        axis = (nrm + V((random.uniform(-.3, .3), random.uniform(-.3, .3), random.uniform(-.2, .3)))).normalized()
        parts = [torus('tyre', 0.24 * size, 0.1 * size, mat=M['tyre'], segU=24, segV=8, rz=0.085 * size),
                 cyl('rim', 0.15 * size, 0.1 * size, mat=accents[i % len(accents)], seg=14),
                 cyl('hub', 0.05 * size, 0.14 * size, mat=M['chrome'], seg=8)]
        for k in range(12):
            a = 2 * math.pi * k / 12
            kn = box('knob', (0.05 * size, 0.06 * size, 0.1 * size), mat=M['tyre'], smooth=False)
            kn.location = (math.cos(a) * 0.335 * size, math.sin(a) * 0.335 * size, 0)
            kn.rotation_euler = (0, 0, a)
            parts.append(kn)
        t = decimate(join(parts, 'floret'), 0.6)
        t.data.transform(axis.to_track_quat('Z', 'Y').to_matrix().to_4x4())
        t.location = pos
        p.append(t)
    return join(p, 'Boss_Hair', pivot=NECK)


# ================================================================ rocket

def build_rocket(M):
    p = [capsule('body', (-0.45, 0, 0), (0.25, 0, 0), 0.16, 0.16, M['rocket_w'], seg=20, rings=10),
         cyl('nose', 0.16, 0.38, (0.45, 0, 0), M['rocket'], rot=(0, math.pi / 2, 0), r2=0.01, seg=20),
         torus('band', 0.16, 0.03, (0.05, 0, 0), M['rocket'], rot=(0, math.pi / 2, 0), segU=20, segV=6),
         cyl('nozzle', 0.11, 0.16, (-0.6, 0, 0), M['dark'], rot=(0, math.pi / 2, 0), r2=0.14, seg=16),
         cyl('flame', 0.12, 0.5, (-0.92, 0, 0), M['flame'], rot=(0, -math.pi / 2, 0), r2=0.0, seg=16)]
    for k in range(4):
        a = k * math.pi / 2
        p.append(box('fin', (0.3, 0.03, 0.22), (-0.42, math.cos(a) * 0.2, math.sin(a) * 0.2), M['rocket'],
                     rot=(a, 0, 0), bevel=0.01))
    return join(p, 'Boss_Rocket')


# ================================================================ assemble

def pivot(name, loc, parent):
    """Empty at a world position (lib.empty would treat loc as parent-relative)."""
    e = lib.empty(name, loc)
    lib.set_parent(e, parent)
    return e


def cross_piston(M, name, a, pa, b, pb, r=0.08):
    """A hydraulic ram across a joint: the sleeve hangs on pivot `pa` at a, the rod on pivot `pb` at b. Both sit
    on an empty (Boss_PistonA_<name> / Boss_PistonB_<name>) whose +Y points at the other end; the game re-aims
    them every frame, so the rod slides in and out of the sleeve as the joint bends."""
    a, b = V(a), V(b)
    D = (b - a).length
    for tag, at, to, parent, mesh in (('A', a, b, pa, 'sleeve'), ('B', b, a, pb, 'rod')):
        e = lib.empty(f'Boss_Piston{tag}_{name}')
        e.empty_display_size = 0.15
        d = (to - at).normalized()
        e.matrix_world = Matrix.Translation(at) @ rot_between((0, 1, 0), d).to_4x4()
        lib.set_parent(e, parent)
        if mesh == 'sleeve':
            parts = [tube('sleeve', at, at + d * D * 0.62, r * 1.7, M['dark'], seg=12),
                     sphere('mount', r * 2.0, at, M['joint'], seg=12, rings=6),
                     torus('band', r * 1.75, r * 0.35, at + d * D * 0.55, M['bronze'], segU=16, segV=4)]
        else:
            parts = [tube('rod', at, at + d * D * 0.62, r, M['joint'], seg=10), sphere('mount', r * 1.8, at, M['joint'], seg=12, rings=6)]
        o = join(parts, f'Boss_Piston_{name}_{tag}', pivot=at)
        lib.set_parent(o, e)


def build():
    lib.reset_scene()
    M = mats()
    root = lib.empty('Boss')
    hips = pivot('Boss_Hips', (-0.25, 0, HIP_Z), root)
    lib.set_parent(build_pelvis(M), hips)

    legs = {}
    for s in (1, -1):
        hip, knee, ankle, upper, lower, foot = build_leg(M, s)
        side = 'L' if s > 0 else 'R'
        pv = pivot(f'Boss_Leg{side}_Pivot', hip, hips)
        kn = pivot(f'Boss_Knee{side}', knee, pv)
        an = pivot(f'Boss_Ankle{side}', ankle, kn)
        for o in upper:
            lib.set_parent(o, pv)
        for o in lower:
            lib.set_parent(o, kn)
        for o in foot:
            lib.set_parent(o, an)
        legs[s] = (hip, knee, ankle, pv, kn, an)

    spine = pivot('Boss_Spine', SPINE, hips)
    chest, core, torso_bike, exhausts = build_torso(M)
    for o in (chest, core, torso_bike):
        lib.set_parent(o, spine)
    for i, e in enumerate(exhausts):
        lib.set_parent(lib.empty(f'Boss_Exhaust_{i}', e), spine)

    arms = {}
    for s in (1, -1):
        sho, elbow, wrist, upper, lower, launcher, muzzles, hand, fingers = build_arm(M, s)
        side = 'L' if s > 0 else 'R'
        pv = pivot(f'Boss_Arm{side}_Pivot', sho, spine)
        el = pivot(f'Boss_Elbow{side}', elbow, pv)
        wr = pivot(f'Boss_Wrist{side}', wrist, el)
        for o in upper:
            lib.set_parent(o, pv)
        for o in lower:
            lib.set_parent(o, el)
        lib.set_parent(hand, wr)
        for i, (base, f) in enumerate(fingers):
            fp = pivot(f'Boss_Finger{side}{i}', base, wr)
            lib.set_parent(f, fp)
        if launcher:
            lib.set_parent(launcher, el)
            for i, mz in enumerate(muzzles):
                lib.set_parent(lib.empty(f'Boss_Muzzle_{i}', mz), el)
        wr.scale = (1.3, 1.3, 1.3)   # big claws
        arms[s] = (sho, elbow, wrist, pv, el, wr)

    neck = pivot('Boss_Neck', NECK, spine)
    head, jaw = build_head(M)
    lib.set_parent(head, neck)
    jp = pivot('Boss_Jaw', JAW_HINGE, neck)
    lib.set_parent(jaw, jp)
    lib.set_parent(build_hair(M), neck)
    neck.scale = (HEAD_SCALE_UP,) * 3   # a bigger, meaner head
    # hydraulics across every big joint (re-aimed by the game every frame)
    for s, side in ((1, 'L'), (-1, 'R')):
        hip, knee, ankle, pv, kn, an = legs[s]
        foot = leg_points(s)[2]
        cross_piston(M, f'Hip{side}', hip + V((0.45, s * 0.25, 0.55)), hips, lerp(hip, knee, 0.5) + V((0.38, s * 0.1, 0.0)), pv, 0.09)
        cross_piston(M, f'Knee{side}', lerp(hip, knee, 0.55) + V((-0.32, 0, -0.1)), pv, lerp(knee, foot, 0.4) + V((-0.35, 0, 0.0)), kn, 0.09)
        cross_piston(M, f'Ankle{side}', lerp(knee, foot, 0.55) + V((-0.38, s * 0.2, 0.0)), kn, ankle + V((-0.3, s * 0.2, 0.1)), an, 0.06)
        sho, elbow, wrist, apv, el, wr = arms[s]
        cross_piston(M, f'Shoulder{side}', sho + V((0.35, -s * 0.55, -0.85)), spine, lerp(sho, elbow, 0.35) + V((0.3, 0, 0)), apv, 0.08)
        cross_piston(M, f'Elbow{side}', lerp(sho, elbow, 0.5) + V((-0.3, 0, 0)), apv, lerp(elbow, wrist, 0.45) + V((-0.28, 0, 0)), el, 0.08)
        cross_piston(M, f'Neck{side}', NECK + V((-0.3, s * 0.35, -0.55)), spine, HEAD_C + V((-0.45, s * 0.32, -0.05)), neck, 0.07)
        cross_piston(M, f'Jaw{side}', HEAD_C + V((-0.25, s * 0.47, 0.1)), neck, JAW_HINGE + V((0.3, s * 0.45, -0.25)), jp, 0.045)

    # rest pose: hunched, arms hanging forward of the body, head pushed forward and level
    spine.rotation_euler = (0, LEAN, 0)
    neck.rotation_euler = (0, -LEAN * 0.7, 0)
    for s, (sho, elbow, wrist, pv, el, wr) in arms.items():
        pv.rotation_euler = (s * math.radians(8), -LEAN * 0.6, 0)

    for o in list(bpy.data.objects):   # drop the wheel templates
        if o.name.startswith('tmpl_wheel'):
            bpy.data.objects.remove(o)
    rocket = build_rocket(M)
    rocket.location = (0, 8, 1)

    # material kit: baked AO / crease darkening in vertex colours (Godot multiplies it in)
    bpy.context.view_layer.update()
    meshes = [o for o in root.children_recursive if o.type == 'MESH']
    for m in bpy.data.materials:
        if m.node_tree and any(nd.type == 'BSDF_PRINCIPLED' for nd in m.node_tree.nodes):
            ck.use_ao(m)
    ck.bake_ao(meshes, meshes, rays=20, dist=0.8, strength=0.6, cavity=1.0, floor=0.4)
    ck.solid_vc([rocket])
    return root, rocket


def main():
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    root, rocket = build()
    scene = bpy.context.scene
    objs = [root] + list(root.children_recursive) + [rocket]
    meshes = [o for o in objs if o.type == 'MESH']
    print(f'[boss] triangles: {lib.tri_count(meshes)}')
    for o in meshes:
        print(f'[boss]   {o.name}: {lib.tri_count([o])}')
    bpy.context.view_layer.update()
    top = max((o.matrix_world @ V(c)).z for o in meshes if o is not rocket for c in o.bound_box)
    print(f'[boss] height: {top:.2f} m')
    out = os.path.join(ROOT, 'assets', 'models', 'boss.glb')
    lib.export_glb(out, objs)
    print(f'[boss] exported {out}')
    if '--no-render' in argv:
        return

    rocket.hide_render = True
    lib.preview_stage(scene, size=(1600, 1200))
    scene.objects['PreviewGround'].scale = (3, 3, 1)
    rdir = os.path.join(ROOT, 'renders', 'boss')
    os.makedirs(rdir, exist_ok=True)
    lib.render(scene, lib.camera('Cam_hero', (15, -10, 2.2), (0, 0, 5.0), 30), os.path.join(rdir, '01_hero.png'))
    lib.render(scene, lib.camera('Cam_front', (24, 0, 1.6), (0, 0, 5.0), 30), os.path.join(rdir, '02_player_view.png'))
    lib.render(scene, lib.camera('Cam_head', (6.5, -3.0, 9.0), (1.2, 0, 8.3), 45), os.path.join(rdir, '03_head.png'))
    lib.render(scene, lib.camera('Cam_back', (-14, 11, 6), (0, 0, 4.8), 32), os.path.join(rdir, '04_back.png'))
    scene.objects['Boss_ArmR_Pivot'].rotation_euler = (math.radians(-10), math.radians(-70), math.radians(-15))
    scene.objects['Boss_ElbowR'].rotation_euler = (0, math.radians(-25), 0)
    scene.objects['Boss_Spine'].rotation_euler = (0, LEAN, math.radians(-12))
    lib.render(scene, lib.camera('Cam_attack', (15, -4, 2.0), (0, -1.0, 6.0), 30), os.path.join(rdir, '05_attack.png'))


if __name__ == '__main__':
    main()
