class_name Effects
extends Node3D
## Slapstick debris physics, billboard particles, light flashes and screen-space popups / speech bubbles.

var camera: Camera3D
var popup_layer: Control
var shake := 0.0

var _debris: Array = []
var _particles: Array = []
var _lights: Array = []
var _popups: Array = []
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
	_debris.append({"g": g, "vel": vel, "ang": ang, "radius": opts.get("radius", 0.3), "life": opts.get("life", 3.2),
		"age": 0.0, "bounce": opts.get("bounce", 0.38), "stars": opts.get("stars", false), "landed": false})
	return g


func _update_debris(dt: float) -> void:
	for i in range(_debris.size() - 1, -1, -1):
		var d: Dictionary = _debris[i]
		var g: Node3D = d.g
		d.age += dt
		d.vel.y -= Config.GRAVITY * 1.5 * dt
		g.position += d.vel * dt
		var w: float = d.ang.length()
		if w > 0.0001:
			g.basis = Basis(d.ang / w, w * dt) * g.basis
		if g.position.y < d.radius:
			g.position.y = d.radius
			if d.vel.y < -1.5 and not d.landed:
				d.landed = true
				puff(Vector3(g.position.x, 0.1, g.position.z), Color("8a7a6a"), 4, 0.5)
				if d.stars:
					stars(g.position + Vector3(0, d.radius + 0.4, 0))
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
	var mi = MeshInstance3D.new()
	mi.mesh = _quad
	mi.material_override = _mats[mat]
	mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	add_child(mi)
	mi.global_position = pos
	mi.scale = Vector3.ONE * size
	# per-instance tint via a tiny material override copy (cheap at our counts)
	var m: StandardMaterial3D = _mats[mat].duplicate()
	m.albedo_color = col
	mi.material_override = m
	_particles.append({"n": mi, "vel": vel, "life": life, "age": 0.0, "grow": grow, "base": size, "gravity": gravity, "drag": drag, "alpha": col.a})


func puff(pos: Vector3, col := Color("d8d0c0"), n := 5, size := 0.6) -> void:
	for i in n:
		var c = col
		c.a = 0.8
		_spawn("puff", c, size * randf_range(0.6, 1.2), pos + Vector3(randf_range(-0.2, 0.2), randf() * 0.3, randf_range(-0.2, 0.2)),
			Vector3(randf_range(-0.75, 0.75), randf_range(0.5, 1.5), randf_range(-0.75, 0.75)), randf_range(0.6, 1.1), 2.2, 0.0, 0.92)


func muzzle_flash(pos: Vector3, size := 0.5) -> void:
	_spawn("flash", Color(1, 1, 1, 1), size, pos, Vector3.ZERO, 0.06, 1.4)
	flash_light(pos, Color("ffcc66"), 4.0, 0.07)


func flash_light(pos: Vector3, col: Color, energy: float, life: float, rng := 12.0) -> void:
	var l = OmniLight3D.new()
	l.light_color = col
	l.light_energy = energy
	l.omni_range = rng
	add_child(l)
	l.global_position = pos
	_lights.append({"l": l, "life": life, "age": 0.0, "e0": energy})


func smoke_trail(pos: Vector3) -> void:
	_spawn("puff", Color(0.75, 0.75, 0.75, 0.6), 0.35, pos, Vector3(0, 0.4, 0), 0.9, 3.0)


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
		var n: MeshInstance3D = p.n
		p.vel.y -= p.gravity * dt
		p.vel *= pow(p.drag, dt * 60.0)
		n.position += p.vel * dt
		n.scale = Vector3.ONE * p.base * (1.0 + (p.grow - 1.0) * k)
		n.transparency = clampf(k, 0.0, 1.0)
		if k >= 1.0:
			n.queue_free()
			_particles.remove_at(i)
	for i in range(_lights.size() - 1, -1, -1):
		var l: Dictionary = _lights[i]
		l.age += dt
		(l.l as OmniLight3D).light_energy = l.e0 * maxf(0.0, 1.0 - l.age / l.life)
		if l.age >= l.life:
			l.l.queue_free()
			_lights.remove_at(i)


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
		else:
			p.n.queue_free()
	for l in _lights:
		l.l.queue_free()
	for p in _popups:
		p.lb.queue_free()
	_debris.clear()
	_particles.clear()
	_lights.clear()
	_popups.clear()
	shake = 0.0


func step(dt: float) -> void:
	_update_debris(dt)
	_update_particles(dt)
	_update_popups(dt)
	shake = maxf(0.0, shake - dt * 2.5)
