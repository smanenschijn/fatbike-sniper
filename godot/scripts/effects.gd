class_name Effects
extends Node3D
## Slapstick debris physics, billboard particles, light flashes and screen-space popups / speech bubbles.

var camera: Camera3D
var popup_layer: Control
var shake := 0.0

var _debris: Array = []
var _particles: Array = []
var _pools := {}   # material name -> MultiMeshInstance3D: all billboard particles of one kind in one draw call
var _lights: Array = []
var _popups: Array = []
var _fireworks: Array = []
var _quad := QuadMesh.new()
var _mats := {}
var _font: Font
var _font_ui: Font


func setup(cam: Camera3D, layer: Control, font: Font, font_ui: Font) -> void:
	camera = cam
	popup_layer = layer
	_font = font
	_font_ui = font_ui
	_mats.puff = _billboard(_radial_tex(Color(1, 1, 1, 0.9), Color(1, 1, 1, 0)), false)
	_mats.fire = _billboard(_radial_tex(Color(1, 0.95, 0.7, 1), Color(1, 0.5, 0.1, 0)), true)
	_mats.flash = _billboard(_star_tex(), true)
	_mats.star = _billboard(_star_tex(Color("ffd23f")), false)
	_mats.fire.render_priority = 1   # glow on top of the smoke
	_mats.flash.render_priority = 2
	for k in ["puff", "fire", "flash"]:
		var mm := MultiMesh.new()
		mm.transform_format = MultiMesh.TRANSFORM_3D
		mm.use_colors = true
		mm.mesh = _quad
		mm.instance_count = 64
		mm.visible_instance_count = 0
		var mmi := MultiMeshInstance3D.new()
		mmi.multimesh = mm
		mmi.material_override = _mats[k]
		mmi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		add_child(mmi)
		_pools[k] = mmi
	_warm = 3


## The web build (WebGL) compiles a shader the first time something is drawn with it, and the game stands still
## meanwhile: the first shot, explosion or ice splat froze it. So draw every effect once, tiny (and the particles nearly
## transparent), right at the camera while the title screen loads (a few frames, so it survives the camera settling).
var _warm := 0
var _warm_nodes: Array = []


## Draw `node` (e.g. a projectile with a material of its own) once at the camera too, then free it.
func warm(node: Node3D) -> void:
	add_child(node)
	node.scale = Vector3.ONE * 0.002   # sub-pixel: no `transparency`, that would compile another variant
	_warm_nodes.append(node)


func _warm_up() -> void:
	_warm -= 1
	var at := camera.global_position - camera.global_basis.z * 1.5
	for k in _pools:
		_spawn(k, Color(1, 1, 1, 0.004), 0.002, at, Vector3.ZERO, 0.2)
	if _warm == 2:
		var mi := MeshInstance3D.new()   # the stars around a dazed rider: same texture trick, but not instanced
		mi.mesh = _quad
		mi.material_override = _mats.star
		warm(mi)
		for spec in [[_font, 96], [_font, 72], [_font, 44], [_font, 34], [_font, 26], [_font_ui, 17]]:   # glyphs of popups and bubbles
			var lb := _label("BOEM!0123456789", spec[1], Color.WHITE, 8, spec[0] == _font_ui)
			lb.modulate.a = 0.004
			_warm_nodes.append(lb)
	for n in _warm_nodes:
		if n is Node3D:
			(n as Node3D).global_position = at
	if _warm == 0:
		for n in _warm_nodes:
			n.queue_free()
		_warm_nodes.clear()


# ------------------------------------------------------------ textures / materials

func _radial_tex(inner: Color, outer: Color) -> Texture2D:
	var g = Gradient.new()
	g.set_color(0, inner)
	g.set_color(1, outer)
	var t = GradientTexture2D.new()
	t.gradient = g
	t.fill = GradientTexture2D.FILL_RADIAL
	t.fill_from = Vector2(0.5, 0.5)
	t.fill_to = Vector2(1.0, 0.5)
	t.width = 64
	t.height = 64
	return t


func _star_tex(col := Color(1, 0.95, 0.65)) -> Texture2D:
	var img = Image.create(64, 64, false, Image.FORMAT_RGBA8)
	for y in 64:
		for x in 64:
			var d = Vector2(x - 31.5, y - 31.5)
			var a = atan2(d.y, d.x)
			var r = d.length() / 32.0
			var spike = 0.45 + 0.55 * pow(absf(cos(a * 2.5)), 6.0)
			var v = clampf((spike - r) * 6.0, 0.0, 1.0)
			img.set_pixel(x, y, Color(col.r, col.g, col.b, v))
	return ImageTexture.create_from_image(img)


func _billboard(tex: Texture2D, additive: bool) -> StandardMaterial3D:
	var m = StandardMaterial3D.new()
	m.albedo_texture = tex
	m.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	m.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	m.billboard_mode = BaseMaterial3D.BILLBOARD_ENABLED
	m.vertex_color_use_as_albedo = true   # the per-particle tint comes in as the MultiMesh instance colour
	m.vertex_color_is_srgb = true
	m.no_depth_test = false
	m.disable_receive_shadows = true
	if additive:
		m.blend_mode = BaseMaterial3D.BLEND_MODE_ADD
	return m


# ------------------------------------------------------------ debris

## Turn `node` into a tumbling rigid body around `center` (world space).
func add_debris(node: Node3D, center: Vector3, vel: Vector3, ang: Vector3, opts := {}) -> Node3D:
	var g = Node3D.new()
	add_child(g)
	g.global_position = center
	node.reparent(g, true)
	for mi in node.find_children("*", "GeometryInstance3D", true, false):
		(mi as GeometryInstance3D).cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	var d := {"g": g, "vel": vel, "ang": ang, "radius": opts.get("radius", 0.3), "life": opts.get("life", 3.2),
		"age": 0.0, "bounce": opts.get("bounce", 0.38), "stars": opts.get("stars", false), "landed": false,
		"gravity": opts.get("gravity", 1.0)}
	if opts.has("on_land"):
		d.on_land = opts.on_land
	if opts.has("limbs"):   # a rider: flails in the air, lands flat on the ground like a starfish
		d.body = node
		d.lie_radius = opts.get("lie_radius", 0.22)
		d.limbs = []
		for l in opts.limbs:
			var n: Node3D = l.node
			var q := n.quaternion
			d.limbs.append({"node": n, "kind": l.kind, "rest_dir": (l.rest_dir as Vector3).normalized(), "rest_q": q, "q": q,
				"side": signf(n.position.z) if absf(n.position.z) > 0.01 else 1.0, "phase": randf() * TAU, "speed": randf_range(11.0, 14.0),
				"sprawl": randf_range(-0.25, 0.25)})
	_debris.append(d)
	return g


## Arms windmill and legs kick while a rider flies; once he is down they splay out (and a leg twitches).
func _flail(d: Dictionary, dt: float) -> void:
	var t: float = d.age
	var down: bool = d.landed
	for l in d.limbs:
		var side: float = l.side
		var dir: Vector3
		if l.kind == "arm":
			if down:
				dir = Vector3(l.sprawl, 0.6, side)
			else:
				var a: float = l.phase + t * l.speed * side   # the arms go round in opposite directions: extra silly
				var spread := 0.85 + 0.4 * sin(t * 9.0 + l.phase)
				dir = Vector3(sin(a), cos(a), 0) * cos(spread) + Vector3(0, 0, side * sin(spread))
		else:
			if down:
				var twitch := 0.0
				if l.side > 0 and fmod(t + l.phase, 1.1) < 0.25:
					twitch = sin(t * 40.0) * 0.35
				dir = Vector3(0.2 + l.sprawl + twitch, -1.0, side * 0.5)
			else:
				var kick := sin(t * l.speed * 0.8 + (0.0 if side > 0 else PI)) * 0.9
				dir = Basis(Vector3.BACK, kick) * (l.rest_dir as Vector3) + Vector3(0, 0, side * 0.35)
		var target: Quaternion = Quaternion(l.rest_dir, dir.normalized()) * (l.rest_q as Quaternion)
		if down:
			l.q = (l.q as Quaternion).slerp(target, 1.0 - exp(-9.0 * dt))
		else:   # follow the flailing exactly (smoothing would average the circles away), blending in from the riding pose
			l.q = (l.rest_q as Quaternion).slerp(target, minf(1.0, t / 0.1))
		(l.node as Node3D).quaternion = l.q
	if down:
		# roll onto back or belly: the body's up axis goes flat on the ground
		var g: Node3D = d.g
		var up: Vector3 = (d.body as Node3D).global_basis.y.normalized()
		var flat := Vector3(up.x, 0, up.z)
		if flat.length() < 0.15:   # landed upright or on his head: tip over along the chest
			var x: Vector3 = (d.body as Node3D).global_basis.x
			flat = Vector3(x.x, 0, x.z)
		if flat.length() > 0.01:
			var k := 1.0 - exp(-8.0 * dt)
			g.basis = Basis(Quaternion.IDENTITY.slerp(Quaternion(up, flat.normalized()), k)) * g.basis
		d.radius = lerpf(d.radius, d.lie_radius, 1.0 - exp(-6.0 * dt))


## Water surfaces (the adventure's gracht): [Rect2 on x/z, surface height]. Debris that lands there splashes and sinks.
var water: Array = []


func water_level(p: Vector3):
	for w in water:
		if (w[0] as Rect2).has_point(Vector2(p.x, p.z)):
			return w[1]
	return null


func splash(pos: Vector3) -> void:
	for i in 10:
		_spawn("puff", Color(0.85, 0.95, 1.0, 0.9), randf_range(0.3, 0.6), pos + Vector3(randf_range(-0.4, 0.4), 0.1, randf_range(-0.4, 0.4)),
			Vector3(randf_range(-1.5, 1.5), randf_range(3.5, 6.5), randf_range(-1.5, 1.5)), randf_range(0.6, 1.0), 1.6, 9.0, 0.6)
	puff(pos + Vector3(0, 0.1, 0), Color(0.8, 0.9, 0.95, 0.8), 6, 0.8)
	Sfx.play("knock_off", 0.0, 0.55)


func _update_debris(dt: float) -> void:
	for i in range(_debris.size() - 1, -1, -1):
		var d: Dictionary = _debris[i]
		var g: Node3D = d.g
		d.age += dt
		var wl = water_level(g.position)
		if d.has("limbs"):
			_flail(d, dt)
		if d.get("sinking", false):
			g.position += Vector3(d.vel.x * 0.2, -0.6, d.vel.z * 0.2) * dt
			if d.age > d.life:
				g.queue_free()
				_debris.remove_at(i)
			continue
		d.vel.y -= Config.GRAVITY * 1.5 * d.gravity * dt
		g.position += d.vel * dt
		var w: float = d.ang.length()
		if w > 0.0001:
			g.basis = Basis(d.ang / w, w * dt) * g.basis
		if wl != null and g.position.y < float(wl) + 0.1:
			d.sinking = true
			d.life = d.age + 2.5
			splash(Vector3(g.position.x, float(wl), g.position.z))
			continue
		if wl == null and g.position.y < d.radius:
			g.position.y = d.radius
			if d.vel.y < -1.5 and not d.landed:
				d.landed = true
				puff(Vector3(g.position.x, 0.1, g.position.z), Color("8a7a6a"), 4, 0.5)
				if d.stars:
					stars(g.position + Vector3(0, d.radius + 0.4, 0))
				if d.has("limbs"):
					d.ang = Vector3.ZERO
				if d.has("on_land"):
					d.on_land.call()
			d.vel.y = absf(d.vel.y) * d.bounce
			d.vel.x *= 0.72
			d.vel.z *= 0.72
			d.ang *= 0.7
		if d.age > d.life - 0.8:
			g.position.y -= dt * 0.8
		if d.age > d.life:
			g.queue_free()
			_debris.remove_at(i)


# ------------------------------------------------------------ particles

func _spawn(mat: String, col: Color, size: float, pos: Vector3, vel: Vector3, life: float, grow := 1.0, gravity := 0.0, drag := 1.0) -> void:
	_particles.append({"mat": mat, "col": col, "pos": pos, "vel": vel, "life": life, "age": 0.0, "grow": grow, "base": size, "gravity": gravity, "drag": drag})


func puff(pos: Vector3, col := Color("d8d0c0"), n := 5, size := 0.6) -> void:
	for i in n:
		var c = col
		c.a = 0.55
		c = c.darkened(0.12)
		_spawn("puff", c, size * randf_range(0.6, 1.2), pos + Vector3(randf_range(-0.2, 0.2), randf() * 0.3, randf_range(-0.2, 0.2)),
			Vector3(randf_range(-0.75, 0.75), randf_range(0.5, 1.5), randf_range(-0.75, 0.75)), randf_range(0.6, 1.1), 2.2, 0.0, 0.92)


## A scoop of ice cream goes splat: blobs in its flavour and a little frosty cloud.
func splat(pos: Vector3, col: Color, big := false) -> void:
	for i in (6 if big else 3):
		var c := col
		c.a = 0.95
		_spawn("puff", c, randf_range(0.1, 0.22) * (1.3 if big else 1.0), pos,
			Vector3(randf_range(-2.2, 2.2), randf_range(0.8, 3.2), randf_range(-2.2, 2.2)), randf_range(0.35, 0.6), 0.8, 9.0, 0.97)
	_spawn("puff", Color(0.88, 0.96, 1.0, 0.5), 0.4 if big else 0.2, pos, Vector3(0, 0.4, 0), 0.45, 1.8)


func muzzle_flash(pos: Vector3, size := 0.5) -> void:
	_spawn("flash", Color(1, 1, 1, 1), size, pos, Vector3.ZERO, 0.06, 1.4)
	flash_light(pos, Color("ffcc66"), 4.0, 0.07)


func flash_light(pos: Vector3, col: Color, energy: float, life: float, rng := 12.0) -> void:
	# The web build (WebGL / Compatibility renderer) draws every mesh a light touches once more, and the first light
	# stalls on a shader compile: the flash sprites carry the effect there on their own.
	if OS.has_feature("web"):
		return
	var l = OmniLight3D.new()
	l.light_color = col
	l.light_energy = energy
	l.omni_range = rng
	add_child(l)
	l.global_position = pos
	_lights.append({"l": l, "life": life, "age": 0.0, "e0": energy})


func smoke_trail(pos: Vector3) -> void:
	_spawn("puff", Color(0.75, 0.75, 0.75, 0.6), 0.35, pos, Vector3(0, 0.4, 0), 0.9, 3.0)


## Exhaust of FATBIKETRON's leg boosters: embers and smoke from the flame tip, a ring of dust when it hits the ground.
func thruster(tip: Vector3, vel: Vector3, ground_y: float, power: float) -> void:
	_spawn("fire", Color("ffb040"), randf_range(0.35, 0.6) * power, tip, vel + Vector3(randf_range(-1, 1), 0, randf_range(-1, 1)), 0.18, 1.6)
	if randf() < 0.35:
		_spawn("fire", Color("ffd060"), 0.08, tip, Vector3(randf_range(-4, 4), randf_range(2, 6), randf_range(-4, 4)), 0.6, 0.5, Config.GRAVITY)
	if tip.y - ground_y < 0.9:
		var a := randf() * TAU
		var out := Vector3(cos(a), 0, sin(a))
		_spawn("puff", Color(0.72, 0.66, 0.58, 0.55), randf_range(0.5, 0.9), Vector3(tip.x, ground_y + 0.25, tip.z) + out * 0.4,
			out * randf_range(3.0, 5.0) * power + Vector3(0, 0.6, 0), randf_range(0.6, 1.0), 2.6, 0.0, 0.93)
	elif randf() < 0.4:
		_spawn("puff", Color(0.5, 0.48, 0.46, 0.5), 0.5, tip, vel * 0.3 + Vector3(0, 0.8, 0), 0.9, 2.5, 0.0, 0.95)


func explosion(pos: Vector3) -> void:
	for i in 14:
		_spawn("fire", Color("ffa030") if i % 3 else Color("fff0a0"), randf_range(1.2, 2.2),
			pos + Vector3(randf_range(-0.6, 0.6), randf() * 1.2, randf_range(-0.6, 0.6)),
			Vector3(randf_range(-3.5, 3.5), randf() * 6, randf_range(-3.5, 3.5)), randf_range(0.45, 0.75), 3.0, 0.0, 0.85)
	for i in 16:
		_spawn("puff", Color(0.29, 0.27, 0.25, 0.85), randf_range(1.5, 2.5),
			pos + Vector3(randf_range(-1, 1), randf() * 1.5, randf_range(-1, 1)),
			Vector3(randf_range(-1.5, 1.5), randf_range(1.5, 4), randf_range(-1.5, 1.5)), randf_range(1.6, 2.6), 2.8, 0.0, 0.95)
	for i in 20:
		_spawn("fire", Color("ffd060"), 0.15, pos, Vector3(randf_range(-9, 9), randf_range(4, 14), randf_range(-9, 9)), 0.9, 0.5, Config.GRAVITY)
	flash_light(pos + Vector3(0, 1, 0), Color("ff9a40"), 12.0, 0.35, 30.0)
	popup_world(pos + Vector3(0, 2, 0), "BOEM!", "boem", 0.9)
	add_shake(0.8)


# ------------------------------------------------------------ fireworks

const FIREWORK_COLORS := [Color("ff3b6b"), Color("ffd23f"), Color("35c2ff"), Color("7cff6b"), Color("ff8a1f"), Color("c77dff"), Color("ffffff")]


## Launch a firework rocket from `from`; it bursts around height `burst_y` (kind: "ball" | "ring" | "willow").
func firework(from: Vector3, burst_y: float, kind := "ball", col: Color = FIREWORK_COLORS.pick_random()) -> void:
	var vel = Vector3(randf_range(-1.5, 1.5), sqrt(2.0 * 4.0 * maxf(1.0, burst_y - from.y)) , randf_range(-1.5, 1.5))
	_fireworks.append({"pos": from, "vel": vel, "kind": kind, "col": col, "trail": 0.0})
	Sfx.launch()


func _burst(pos: Vector3, kind: String, col: Color) -> void:
	var n = 70 if kind != "ring" else 48
	var col2: Color = FIREWORK_COLORS.pick_random()
	var axis = Vector3(randf_range(-0.4, 0.4), 1, randf_range(-0.4, 0.4)).normalized()
	for i in n:
		var dir: Vector3
		if kind == "ring":
			var a = TAU * i / n
			dir = Basis(Vector3.RIGHT, 1.2) * Vector3(cos(a), 0, sin(a))
			dir = Basis(axis, randf()) * dir
		else:
			dir = Vector3(randf_range(-1, 1), randf_range(-1, 1), randf_range(-1, 1)).normalized()
		var willow = kind == "willow"
		var speed = randf_range(9, 13) if not willow else randf_range(5, 7.5)
		var c = col if i % 4 else col2
		_spawn("fire", c, 1.0 if not willow else 0.75, pos, dir * speed, randf_range(1.3, 1.8) if not willow else randf_range(2.2, 2.8),
			0.35, 3.0 if not willow else 5.5, 0.955 if not willow else 0.975)
	_spawn("flash", Color(col.r, col.g, col.b, 1), 6.0, pos, Vector3.ZERO, 0.15, 1.5)
	flash_light(pos, col, 10.0, 0.5, 60.0)
	Sfx.firework(camera.global_position.distance_to(pos) if camera else 30.0)


func _update_fireworks(dt: float) -> void:
	for i in range(_fireworks.size() - 1, -1, -1):
		var f: Dictionary = _fireworks[i]
		f.vel.y -= 4.0 * dt
		f.pos += f.vel * dt
		f.trail -= dt
		if f.trail <= 0:
			f.trail = 0.02
			_spawn("fire", Color("ffe3a0"), 0.3, f.pos, Vector3(randf_range(-0.3, 0.3), -1.0, randf_range(-0.3, 0.3)), 0.35, 0.3)
		if f.vel.y <= 1.0:
			_burst(f.pos, f.kind, f.col)
			_fireworks.remove_at(i)


func stars(pos: Vector3) -> void:
	var nodes = []
	for i in 5:
		var mi = MeshInstance3D.new()
		mi.mesh = _quad
		mi.material_override = _mats.star
		mi.scale = Vector3.ONE * 0.28
		add_child(mi)
		nodes.append(mi)
	_particles.append({"ring": nodes, "center": pos, "age": 0.0, "life": 1.6})


func _update_particles(dt: float) -> void:
	for i in range(_particles.size() - 1, -1, -1):
		var p: Dictionary = _particles[i]
		p.age += dt
		var k: float = p.age / p.life
		if p.has("ring"):
			var ring: Array = p.ring
			for j in ring.size():
				var a: float = p.age * 5.0 + float(j) / ring.size() * TAU
				(ring[j] as Node3D).global_position = p.center + Vector3(cos(a) * 0.45, sin(p.age * 6.0 + j) * 0.06, sin(a) * 0.45)
				(ring[j] as GeometryInstance3D).transparency = maxf(0.0, (k - 0.7) / 0.3)
			if k >= 1.0:
				for n in ring:
					n.queue_free()
				_particles.remove_at(i)
			continue
		if k >= 1.0:
			_particles.remove_at(i)
			continue
		p.vel.y -= p.gravity * dt
		p.vel *= pow(p.drag, dt * 60.0)
		p.pos += p.vel * dt
	_draw_particles()
	for i in range(_lights.size() - 1, -1, -1):
		var l: Dictionary = _lights[i]
		l.age += dt
		(l.l as OmniLight3D).light_energy = l.e0 * maxf(0.0, 1.0 - l.age / l.life)
		if l.age >= l.life:
			l.l.queue_free()
			_lights.remove_at(i)


## Write the live particles into their MultiMeshes (one draw call per kind), rebuilt every frame.
func _draw_particles() -> void:
	var counts := {}
	for k in _pools:
		counts[k] = 0
	for p in _particles:
		if not p.has("ring"):
			counts[p.mat] += 1
	for k in _pools:
		var mm: MultiMesh = (_pools[k] as MultiMeshInstance3D).multimesh
		if counts[k] > mm.instance_count:
			mm.instance_count = nearest_po2(counts[k])
		mm.visible_instance_count = counts[k]
		(_pools[k] as MultiMeshInstance3D).visible = counts[k] > 0
		counts[k] = 0
	var boxes := {}
	for p in _particles:
		if p.has("ring"):
			continue
		var k: String = p.mat
		var mm: MultiMesh = (_pools[k] as MultiMeshInstance3D).multimesh
		var i: int = counts[k]
		counts[k] = i + 1
		var t: float = minf(p.age / p.life, 1.0)
		mm.set_instance_transform(i, Transform3D(Basis.from_scale(Vector3.ONE * p.base * (1.0 + (p.grow - 1.0) * t)), p.pos))
		# no fade-out: the old per-node `transparency` fade never showed on these alpha materials, and this keeps that look
		mm.set_instance_color(i, p.col)
		var box := AABB(p.pos - Vector3.ONE, Vector3.ONE * 2.0)   # billboards drop the scale: always a 1 m quad
		boxes[k] = boxes[k].merge(box) if boxes.has(k) else box
	for k in boxes:
		(_pools[k] as MultiMeshInstance3D).custom_aabb = boxes[k]   # tight bounds: right culling and depth sorting


# ------------------------------------------------------------ popups / bubbles (screen space)

func _label(text: String, size: int, col: Color, outline := 8, ui := false) -> Label:
	var lb = Label.new()
	lb.text = text
	lb.add_theme_font_override("font", _font_ui if ui else _font)
	lb.add_theme_font_size_override("font_size", size)
	lb.add_theme_color_override("font_color", col)
	lb.add_theme_color_override("font_outline_color", Color("121216"))
	lb.add_theme_constant_override("outline_size", outline)
	lb.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	popup_layer.add_child(lb)
	return lb


func popup_world(pos: Vector3, text: String, cls := "", life := 1.0) -> void:
	var size = 34
	var col = Color.WHITE
	match cls:
		"boem":
			size = 96
			col = Color("ff8a1f")
		"bonus":
			col = Color("ffd23f")
		"bad":
			col = Color("e63946")
	_popups.append({"lb": _label(text, size, col), "pos": pos, "age": 0.0, "life": life, "rise": 1.2})


func popup_screen(text: String, cls := "", x := 0.5, y := 0.42, life := 1.0) -> void:
	var size = 44
	var col = Color.WHITE
	match cls:
		"big":
			size = 72
			col = Color("ffd23f")
		"bonus":
			col = Color("ffd23f")
		"bad":
			col = Color("e63946")
	_popups.append({"lb": _label(text, size, col), "screen": Vector2(x, y), "age": 0.0, "life": life, "rise": 0.04})


func bubble(target: Node3D, offset: Vector3, text: String, warn := false, life := 1.8) -> void:
	var panel = PanelContainer.new()
	var sb = StyleBoxFlat.new()
	sb.bg_color = Color("e63946") if warn else Color.WHITE
	sb.border_color = Color("121216")
	sb.set_border_width_all(3)
	sb.set_corner_radius_all(14)
	sb.content_margin_left = 12
	sb.content_margin_right = 12
	sb.content_margin_top = 4
	sb.content_margin_bottom = 4
	panel.add_theme_stylebox_override("panel", sb)
	var lb = Label.new()
	lb.text = text
	lb.add_theme_font_override("font", _font if warn else _font_ui)
	lb.add_theme_font_size_override("font_size", 26 if warn else 17)
	lb.add_theme_color_override("font_color", Color.WHITE if warn else Color("121216"))
	panel.add_child(lb)
	popup_layer.add_child(panel)
	_popups.append({"lb": panel, "follow": target, "offset": offset, "age": 0.0, "life": life, "bubble": true})


func _update_popups(dt: float) -> void:
	var vs = popup_layer.get_viewport_rect().size
	for i in range(_popups.size() - 1, -1, -1):
		var p: Dictionary = _popups[i]
		p.age += dt
		var k: float = p.age / p.life
		var c: Control = p.lb
		if p.has("screen"):
			c.position = Vector2(p.screen.x * vs.x, (p.screen.y - p.rise * k) * vs.y) - c.size / 2.0
		else:
			var wp: Vector3
			if p.has("follow"):
				if not is_instance_valid(p.follow) or not (p.follow as Node3D).is_inside_tree():
					p.age = p.life
					wp = Vector3.ZERO
				else:
					wp = (p.follow as Node3D).global_position + p.offset
			else:
				wp = p.pos + Vector3(0, p.rise * k, 0)
			var behind = camera.is_position_behind(wp)
			c.visible = not behind
			if not behind:
				var sp = camera.unproject_position(wp)
				if p.get("bubble", false):
					var s = clampf(14.0 / camera.global_position.distance_to(wp), 0.55, 1.2)
					c.scale = Vector2.ONE * s
					c.position = sp - Vector2(c.size.x * s / 2.0, c.size.y * s)
				else:
					c.position = sp - c.size / 2.0
		c.modulate.a = 1.0 - (k - 0.75) / 0.25 if k > 0.75 else 1.0
		if k >= 1.0:
			c.queue_free()
			_popups.remove_at(i)


func add_shake(a: float) -> void:
	shake = minf(1.2, shake + a)


func clear() -> void:
	for d in _debris:
		d.g.queue_free()
	for p in _particles:
		if p.has("ring"):
			for n in p.ring:
				n.queue_free()
	for l in _lights:
		l.l.queue_free()
	for p in _popups:
		p.lb.queue_free()
	_debris.clear()
	_particles.clear()
	_draw_particles()
	_fireworks.clear()
	_lights.clear()
	_popups.clear()
	shake = 0.0


func step(dt: float) -> void:
	if _warm > 0:
		_warm_up()
	_update_debris(dt)
	_update_particles(dt)
	_update_fireworks(dt)
	_update_popups(dt)
	shake = maxf(0.0, shake - dt * 2.5)
