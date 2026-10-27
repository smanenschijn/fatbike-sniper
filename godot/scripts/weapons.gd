class_name Weapons
extends Node3D
## First-person weapons: viewmodels on the camera, firing, reloads, zoom and procedural animation. Port of src/weapons.js.

signal fire_hitscan(w: Dictionary, origin: Vector3, dirs: Array, muzzle)
signal fire_projectile(w: Dictionary, muzzle: Vector3, origin: Vector3, fwd: Vector3)
signal eject_shell(shell: Node3D)
signal empty_mag

var DEFS = [
	{"key": "katapult", "name": "KATAPULT", "mag": -1, "reserve": -1, "fire_delay": 0.3, "reload": 0.0, "kind": "projectile",
		"projectile": {"speed": 65.0, "gravity": 6.0, "radius": 0.12, "damage": 1.0}, "muzzle": Config.B(0, 0, 0.36), "kick": 0.35,
		"offset": Vector3(0, -0.11, 0.13)},
	{"key": "shotgun", "name": "SHOTGUN", "mag": 6, "reserve": -1, "fire_delay": 0.85, "reload": 1.7, "kind": "hitscan",
		"pellets": 10, "spread": 0.075, "range": 32.0, "damage": 1.0, "max_per_rider": 2.0, "muzzle": Config.B(0.8, 0, 0.06), "kick": 1.0},
	{"key": "sniper", "name": "SNIPER", "mag": 5, "reserve": -1, "fire_delay": 1.05, "reload": 2.1, "kind": "hitscan",
		"pellets": 1, "spread": 0.0, "range": 400.0, "damage": 3.0, "pierce": 6, "muzzle": Config.B(1.07, 0, 0.03), "kick": 1.2, "zoom": true},
	{"key": "bazooka", "name": "BAZOOKA", "mag": 1, "reserve": 5, "fire_delay": 0.6, "reload": 2.4, "kind": "projectile",
		"projectile": {"speed": 30.0, "gravity": 1.2, "radius": 0.2, "damage": 3.0, "explode": 5.0}, "muzzle": Config.B(0.95, 0, 0), "kick": 1.6},
	# full auto: hold to spin the barrels up; a scoop slows (brain freeze), two knock a rider off
	{"key": "ijsmachine", "name": "IJSMACHINE", "mag": 60, "reserve": -1, "fire_delay": 0.075, "slow_delay": 0.2, "reload": 2.2,
		"kind": "projectile", "auto": true, "spread": 0.012, "burst": 7,
		"projectile": {"speed": 58.0, "gravity": 5.0, "radius": 0.14, "damage": 0.5, "boss_mul": 0.5, "ice": true},
		"muzzle": Config.B(0.66, 0, 0), "kick": 0.12},
]
const ICE_FLAVOURS := ["f28fb0", "fbefc8", "6b3b22", "a9d86e", "f8e36a"]

var camera: Camera3D
var list: Array = []
var index := 0
var switch_t := 1.0
var pending := -1
var kick := 0.0
var zoom := 0.0
var time := 0.0
var root: Node3D
var infinite := false   # chill level: never empty, never reload
var spin := 0.0        # ijsmachine barrel speed 0..1
var _burst_left := 0   # touch: a tap fires a short burst ...
var _burst_dir := Vector3.ZERO   # ... at the tapped spot


func setup(cam: Camera3D) -> void:
	camera = cam
	root = Node3D.new()
	root.rotation.y = PI / 2  # viewmodel space (+X forward) -> camera space (-Z forward)
	camera.add_child(root)
	for d in DEFS:
		var model: Node3D = load("res://assets/models/weapons/%s.glb" % d.key).instantiate()
		for gi in model.find_children("*", "GeometryInstance3D", true, false):
			(gi as GeometryInstance3D).cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
			(gi as GeometryInstance3D).extra_cull_margin = 2.0
		var vm: Node3D = model.get_child(0) if model.get_child_count() > 0 else model
		var holder = Node3D.new()
		holder.add_child(model)
		holder.visible = false
		root.add_child(holder)
		var w: Dictionary = d.duplicate(true)
		w.holder = holder
		w.vm = vm
		w.ammo = d.mag
		w.reserve_left = d.reserve
		w.cooldown = 0.0
		w.reloading = 0.0
		w.anim = 0.0
		w.ejected = false
		w.parts = {}
		w.base = {}
		for pair in [["pump", "Shotgun_Pump"], ["shell", "Shotgun_Shell"], ["bolt", "Sniper_Bolt"], ["rocket", "Bazooka_Rocket"],
				["pouch", "Katapult_Pouch"], ["stone", "Katapult_Stone"], ["bands", "Katapult_Bands"], ["draw", "Katapult_DrawArm"],
				["barrels", "IJs_Barrels"], ["scoops", "IJs_Scoops"]]:
			var n = model.find_child(pair[1], true, false) as Node3D
			if n:
				w.parts[pair[0]] = n
				w.base[pair[0]] = n.position
		if w.parts.has("shell"):
			w.parts.shell.visible = false
		if w.parts.has("bands"):   # where the tubing is tied to the fork (+X end): it stretches from there
			var bm = w.parts.bands.find_children("*", "MeshInstance3D", true, true)
			var bands_mi: MeshInstance3D = w.parts.bands if w.parts.bands is MeshInstance3D else (bm[0] if not bm.is_empty() else null)
			if bands_mi:
				var bb: AABB = bands_mi.get_aabb()
				w.base.bands_tip = bb.end.x
				w.base.bands_len = bb.size.x
		list.append(w)
	current().holder.visible = true


func current() -> Dictionary:
	return list[index]


func reset(rockets := 5) -> void:
	for w in list:
		w.ammo = w.mag
		w.reserve_left = rockets if w.key == "bazooka" else w.reserve
		w.cooldown = 0.0
		w.reloading = 0.0
		w.anim = 0.0
		if w.parts.has("rocket"):
			w.parts.rocket.visible = true
	spin = 0.0
	_burst_left = 0
	select(0, true)


func add_rockets(count: int) -> void:
	for w in list:
		if w.key == "bazooka":
			w.reserve_left += count


func select(i: int, instant := false) -> void:
	if i == index and not instant:
		return
	current().reloading = 0.0
	_burst_left = 0
	if instant:
		for k in list.size():
			list[k].holder.visible = k == i
		index = i
		switch_t = 1.0
		pending = -1
		return
	pending = i


func start_reload() -> void:
	var w = current()
	if w.reloading > 0 or w.mag < 0 or w.ammo >= w.mag or w.reserve_left == 0:
		return
	w.reloading = w.reload
	Sfx.reload()


func muzzle_world() -> Vector3:
	var w = current()
	return (w.vm as Node3D).to_global(w.muzzle)


func try_fire(inp) -> bool:
	var w = current()
	if switch_t < 1.0 or pending >= 0 or w.cooldown > 0 or w.reloading > 0:
		return false
	if w.mag >= 0 and w.ammo <= 0:
		if inp.fire_pressed:
			Sfx.empty()
		if w.reserve_left != 0:
			start_reload()
		else:
			empty_mag.emit()
		return false
	var auto: bool = w.get("auto", false)
	if auto and inp.fire_pressed and not inp.fire_down:   # a touch tap: a short burst at the tapped spot
		_burst_left = w.burst
		_burst_dir = inp.aim_direction(camera)
	var bursting: bool = auto and _burst_left > 0 and not inp.fire_down
	if not inp.fire_pressed and not inp.fire_down and not bursting:
		return false
	if not inp.fire_pressed and not auto and w.key != "katapult":
		return false
	if w.mag >= 0 and not infinite:
		w.ammo -= 1
	w.cooldown = w.fire_delay
	if auto:   # slow at first, full rate once the barrels have spun up
		w.cooldown = lerpf(w.slow_delay, w.fire_delay, spin)
	w.anim = 1.0
	kick = minf(1.6, kick + w.kick)
	Sfx.shot(w.key)
	var origin = camera.global_position
	var fwd: Vector3 = inp.aim_direction(camera)
	if bursting:
		_burst_left -= 1
		fwd = _burst_dir
	if w.kind == "hitscan":
		var dirs = []
		var spread: float = 0.0 if zoom > 0.5 else w.spread
		for i in w.pellets:
			dirs.append(fwd if (i == 0 and w.pellets > 1) else _jitter(fwd, spread))
		fire_hitscan.emit(w, origin, dirs, null if zoom > 0.5 else muzzle_world())
	else:
		fire_projectile.emit(w, muzzle_world(), origin, fwd)
		if w.parts.has("rocket"):
			w.parts.rocket.visible = false
	if w.mag >= 0 and w.ammo <= 0 and w.reserve_left != 0:
		get_tree().create_timer(maxf(0.15, w.fire_delay * 0.6)).timeout.connect(start_reload)
	return true


func step(dt: float, inp) -> void:
	time += dt
	var w = current()
	for k in list.size():
		if inp.keys_pressed.has(KEY_1 + k):
			select(k)
	if inp.wheel != 0:
		select(posmod(index + inp.wheel, list.size()))
	if inp.keys_pressed.has(KEY_R):
		start_reload()

	if pending >= 0:
		switch_t = maxf(0.0, switch_t - dt * 6.0)
		if switch_t == 0.0:
			w.holder.visible = false
			index = pending
			pending = -1
			current().holder.visible = true
			w = current()
	else:
		switch_t = minf(1.0, switch_t + dt * 5.0)

	for x in list:
		x.cooldown = maxf(0.0, x.cooldown - dt)
		if infinite and x.cooldown <= 0.0 and x.parts.has("rocket"):   # the next rocket is simply there
			x.parts.rocket.visible = true
		x.anim = maxf(0.0, x.anim - dt / maxf(0.2, x.fire_delay))
	if w.reloading > 0:
		w.reloading -= dt
		if w.reloading <= 0:
			var need: int = w.mag - w.ammo
			var take: int = need if w.reserve_left < 0 else mini(need, w.reserve_left)
			w.ammo += take
			if w.reserve_left > 0:
				w.reserve_left -= take
			w.reloading = 0.0
			if w.parts.has("rocket"):
				w.parts.rocket.visible = true
			Sfx.click()

	# sniper zoom
	var want_zoom: bool = w.get("zoom", false) and inp.zoom_held and switch_t == 1.0 and w.reloading <= 0
	zoom += ((1.0 if want_zoom else 0.0) - zoom) * minf(1.0, dt * 14.0)
	camera.fov = lerpf(Config.FOV, Config.ZOOM_FOV, zoom)
	inp.sens_scale = camera.fov / Config.FOV
	root.visible = zoom < 0.6

	# procedural animation
	kick = maxf(0.0, kick - dt * 5.0)
	var lower = 1.0 - (1.0 - (1.0 - switch_t) * (1.0 - switch_t))
	var reload_dip = sin(PI * (1.0 - w.reloading / w.reload)) if w.reloading > 0 else 0.0
	var sway = sin(time * 1.6) * 0.004
	var h: Node3D = w.holder
	h.position = Vector3(-kick * 0.07, -lower * 0.35 - reload_dip * 0.12 + sway + kick * 0.015, cos(time * 0.8) * 0.003)
	if w.has("offset"):
		h.position += w.offset
	h.rotation = Vector3(reload_dip * 0.5, 0, kick * 0.12 - lower * 0.6 - reload_dip * 0.25)

	# ijsmachine: the barrels spin up while the trigger is held and wind down after
	var spinning: bool = w.get("auto", false) and (inp.fire_down or _burst_left > 0) and w.reloading <= 0 and pending < 0 and w.ammo != 0
	spin = clampf(spin + dt * (2.2 if spinning else -1.4), 0.0, 1.0)
	if not w.get("auto", false):
		_burst_left = 0
	if w.parts.has("barrels"):
		w.parts.barrels.rotate_object_local(Vector3.RIGHT, -dt * 38.0 * spin)
		var full: float = clampf(float(w.ammo) / w.mag, 0.0, 1.0) if w.reloading <= 0 else 0.0
		w.parts.scoops.visible = full > 0.0
		w.parts.scoops.scale = Vector3(1, lerpf(0.45, 1.0, full), 1)
		if spin > 0.05:   # a heavy gun rattles
			h.position += Vector3(randf_range(-1, 1), randf_range(-1, 1), randf_range(-1, 1)) * 0.0025 * spin

	var a: float = w.anim
	var p: Dictionary = w.parts
	var s = (1.0 - a) * 2.0 if a > 0.5 else a * 2.0
	if p.has("pump"):
		p.pump.position = w.base.pump + Vector3(-0.08 * s, 0, 0)
		if a > 0.45 and a < 0.5 and not w.ejected:
			w.ejected = true
			eject_shell.emit(p.shell)
		if a < 0.1:
			w.ejected = false
	if p.has("bolt"):
		p.bolt.position = w.base.bolt + Vector3(-0.07 * s, 0.02 * s, 0)
	if p.has("pouch"):
		var snap = 1.0 if a > 0.75 else ((a - 0.4) / 0.35 if a > 0.4 else 0.0)
		var fork = Vector3(0.34, 0, 0)
		p.pouch.position = w.base.pouch + fork * snap
		p.stone.position = w.base.stone + fork * snap
		p.stone.visible = a < 0.4
		# the tubing follows the pouch: shorter (slack) as the pouch flies to the fork, stretched again as it's drawn
		var bl: float = w.base.get("bands_len", 0.0)
		if bl > 0.0:
			var k := clampf((bl - fork.x * snap) / bl, 0.04, 1.0)
			p.bands.scale = Vector3(k, 1, 1)
			p.bands.position = w.base.bands + Vector3(w.base.bands_tip * (1.0 - k), 0, 0)
			p.bands.visible = snap < 0.97
		else:
			p.bands.visible = snap < 0.5
		if p.has("draw"):
			# the drawing hand: lets go (a little flick back), reaches forward for the pouch at the fork,
			# then pulls it back with the new stone
			var reach := 0.0
			if a > 0.85:
				reach = 0.0
			elif a > 0.75:
				reach = 1.0 - (a - 0.75) / 0.1
			else:
				reach = snap
			reach = reach * reach * (3.0 - 2.0 * reach)
			var flick := sin(clampf((1.0 - a) / 0.15, 0.0, 1.0) * PI) if a > 0.85 else 0.0
			p.draw.position = w.base.draw + fork * reach + Vector3(-0.03, -0.015, 0) * flick + Vector3(0, 0.02, 0) * sin(reach * PI)


func hud_state() -> Dictionary:
	var w = current()
	return {
		"index": index, "key": w.key, "zoom": zoom > 0.6,
		"reload": (1.0 - w.reloading / w.reload) if w.reloading > 0 else -1.0,
		"list": list.map(func(x): return {"name": x.name, "ammo": x.ammo, "reserve": x.reserve_left, "mag": -1 if infinite else x.mag}),
	}


static func _jitter(dir: Vector3, spread: float) -> Vector3:
	if spread <= 0.0:
		return dir
	var up = Vector3.UP if absf(dir.y) < 0.99 else Vector3.RIGHT
	var right = dir.cross(up).normalized()
	var up2 = right.cross(dir).normalized()
	var r = sqrt(randf()) * spread
	var a = randf() * TAU
	return (dir + right * cos(a) * r + up2 * sin(a) * r).normalized()
