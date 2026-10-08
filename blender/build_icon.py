"""App icon: a fat tyre in the crosshair on a sunny yellow/orange background, with the title.

Run:  Blender -b -P blender/build_icon.py   -> godot/icon.png (1024x1024)
"""
import math
import os
import sys

import bpy

sys.path.insert(0, os.path.dirname(__file__))
import lib  # noqa: E402
from lib import box, cyl, material, torus  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))


def main():
    lib.reset_scene()
    scene = bpy.context.scene
    lib.set_engine(scene)
    scene.render.resolution_x = scene.render.resolution_y = 1024
    scene.view_settings.view_transform = 'Standard'
    world = bpy.data.worlds.new('W')
    scene.world = world

    bg = material('IconBg', '#ffb627', rough=1.0, emission='#ffb627', strength=1.0)
    ring = material('IconRing', '#121216', rough=0.4)
    red = material('IconRed', '#e63946', rough=0.4, emission='#e63946', strength=0.4)
    tyre = material('IconTyre', '#1d1d20', rough=0.8)
    rim = material('IconRim', '#ff7a1a', rough=0.3, metal=0.4)
    white = material('IconWhite', '#fff8ea', rough=0.5, emission='#fff8ea', strength=0.6)

    box('bg', (12, 12, 0.01), (0, 0, -0.5), bg)
    # fat tyre with tread, slightly tilted
    t = torus('tyre', 0.62, 0.24, (0, 0.12, 0), tyre, segU=96, segV=24)
    t.rotation_euler = (0.25, -0.2, 0)
    for i in range(36):
        a = i / 36 * math.tau
        k = box('knob', (0.08, 0.12, 0.1), (math.cos(a) * 0.86, math.sin(a) * 0.86 + 0.12, 0), tyre, bevel=0.02)
        k.rotation_euler = (0, 0, a)
        k.parent = t
        k.location = (math.cos(a) * 0.86, math.sin(a) * 0.86, 0)
    torus('rim', 0.42, 0.06, (0, 0.12, 0.05), rim, segU=64, segV=12).rotation_euler = (0.25, -0.2, 0)
    cyl('hub', 0.12, 0.2, (0, 0.12, 0.05), ring, seg=32).rotation_euler = (0.25, -0.2, 0)
    # crosshair
    torus('scope', 1.12, 0.05, (0, 0.12, 0.4), ring, segU=96, segV=12)
    torus('scope_red', 1.12, 0.025, (0, 0.12, 0.45), red, segU=96, segV=12)
    for ang in (0, math.pi / 2, math.pi, 3 * math.pi / 2):
        c = box('tick', (0.42, 0.06, 0.04), (math.cos(ang) * 1.12, math.sin(ang) * 1.12 + 0.12, 0.45), ring)
        c.rotation_euler = (0, 0, ang)
    sun = bpy.data.lights.new('S', 'SUN')
    sun.energy = 3
    sun.use_shadow = False
    so = lib.link(bpy.data.objects.new('S', sun))
    so.rotation_euler = (math.radians(30), math.radians(-20), 0)
    cam = bpy.data.cameras.new('C')
    cam.type = 'ORTHO'
    cam.ortho_scale = 2.75
    co = lib.link(bpy.data.objects.new('C', cam))
    co.location = (0, 0.12, 5)
    scene.camera = co
    scene.render.filepath = os.path.join(ROOT, 'godot', 'icon.png')
    bpy.ops.render.render(write_still=True)


if __name__ == '__main__':
    main()
