class_name Market
extends Node3D
## The market on the Henri Donutplein: a vendor behind every stall (Stall_<kind>_<n> in dunant.glb) who shouts
## their wares, ducks when a fatbiker comes tearing past and shakes a fist afterwards. Riders that crash past a
## stall, a shot into a stall and explosions next to one send the goods flying; shoot the flying produce for a
## little bonus. Vendors can't be hit (they have no collision), bullets fly through them.

const VENDOR_DROP := 0.195   # the standing pose's soles sit this far above the rig's origin (blender/rig_v2.py)
const CRATE_H := 0.22
const VENDOR_RANGE := 32.0
const MAX_VENDORS := 6
const MAX_VENDORS_WEB := 4
const RAM_DIST := 2.4        # a rider this close to a stall's table may crash into it
const DUCK_DIST := 4.0
const STALL_COOLDOWN := 4.0
const MAX_FLYING := 90
const BONUS := 25

const SHOUTS := {
	"fruit": ["HANDJESAPPELS! 3 KILO EEN TIENTJE!", "PROEVEN MAG, STELEN NIET!", "BANANEN! KROMMER KRIJG JE ZE NIET!",
		"SINAASAPPELS, ZO SAPPIG!"],
	"groente": ["VERSE SLA! NET GEPLUKT!", "WORTELTJES VOOR DE OGEN!", "TOMATEN! ROOD ALS EEN FATBIKER!",
		"KOMKOMMERS, TWEE HALEN EEN BETALEN!"],
	"kaas": ["JONG BELEGEN, OUD BELEGEN!", "STUKJE PROEVEN, MEVROUW?", "KAAS! ECHTE BOERENKAAS!", "NOG EVEN EEN PLAKJE?"],
	"bloemen": ["TULPEN UIT NIJVERDAL!", "BOSJE BLOEMEN VOOR MOEDER?", "TWEE BOS VOOR EEN VIJFJE!"],
	"wafels": ["WARME STROOPWAFELS!", "VERS VAN HET IJZER!", "WAFELS! GEEN FATBIKES!"],
}
const DUCK_LINES := ["KIJK UIT!", "MIJN KRAAM!", "NIET WEER!", "HÉ, IDIOOT!", "BUKKEN!"]
const ANGRY_LINES := ["DAT BETAAL JE!", "IK BEL DE WIJKAGENT!", "PLOEGENDE BOEREN!", "LOOP NAAR DE PINDAKAAS!",
	"FATBIKERS, ALTIJD FATBIKERS!", "MIJN HANDJESAPPELS!"]
const BONUS_LABEL := {"fruit": "FRUITSALADE!", "groente": "GROENTESOEP!", "kaas": "KAASSCHAAF!", "bloemen": "BOEKETJE!",
	"wafels": "STROOPWAFEL!"}

var world: World
var riders: Riders
var effects: Effects
var player_eye := Vector3.ZERO

var stalls: Array = []     # [{node, kind, table: Vector3, front: Vector3, cd, vendor}]
var flying: Array = []     # [{node, vel, spin, life, r, kind, col, landed}]
var _rammed := {}          # "rider id|stall index" -> true: one try per pass
var _meshes := {}          # kind -> [[Mesh, Material, radius, Color]]
var _active: Array = []    # the stalls whose vendor is shown and animated
var _pick_t := 0.0
var _crate_mesh: BoxMesh
var _crate_mat: StandardMaterial3D


func setup(w: World, r: Riders, fx: Effects) -> void:
	world = w
	riders = r
	effects = fx
	_build_meshes()
	for kind in _meshes:   # compile the produce materials on the title screen (WebGL)
		for m in _meshes[kind]:
			var mi := MeshInstance3D.new()
			mi.mesh = m[0]
			mi.material_override = m[1]
			effects.warm(mi)
	world.loaded.connect(scan)
	scan()


## Find the stalls of the loaded world and put a vendor behind each one.
func scan() -> void:
	clear()
	for s in stalls:
		if is_instance_valid(s.vendor.root):
			s.vendor.root.queue_free()
	stalls.clear()
	var roots: Array = world.models.values() if world.is_adventure() else [world.square]
	for m in roots:
		if m == null:
			continue
		for n in (m as Node).find_children("Stall_*", "Node3D", true, false):
			var node := n as Node3D
			if not String(node.name).begins_with("Stall_") or node.get_parent().name.begins_with("Stall_"):
				continue
			var kind := String(node.name).get_slice("_", 1)
			if not _meshes.has(kind):
				continue
			var xf := node.global_transform
			var front := xf.basis.z.normalized()   # Blender's -Y: the side the customers stand on
			var st := {"node": node, "kind": kind, "table": xf * Vector3(0, 0.95, 0.4), "front": front, "cd": randf() * 2.0}
			st.vendor = _vendor(node, kind)
			stalls.append(st)


func clear() -> void:
	for f in flying:
		if is_instance_valid(f.node):
			f.node.queue_free()
	flying.clear()
	_rammed.clear()


# ------------------------------------------------------------ vendors

func _vendor(stall: Node3D, kind: String) -> Dictionary:
	var p: Dictionary = riders._person()
	var src: Node3D = riders._variants.filter(func(v): return v.id == p.id)[0].node
	var body: Node3D = src.duplicate()
	body.visible = true
	riders._paint(body, p.colors)
	for nm in ["Rider_Knife", "Rider_Phone", "Rider_LegL", "Rider_LegR"]:   # the legs are behind the table anyway
		var k = body.find_child(nm, true, false)
		if k:
			(k as Node3D).visible = false
	var shades = body.find_child("Rider_Sunglasses", true, false)
	if shades:
		shades.visible = p.shades and randf() < 0.5
	var root := Node3D.new()
	root.name = "Vendor"
	stall.add_child(root)
	# behind the table, facing the customers (+X of the model along the stall's front)
	root.transform = Transform3D(Basis(Vector3.UP, -PI / 2.0), Vector3(0, CRATE_H - VENDOR_DROP, -0.45))
	body.transform = Transform3D.IDENTITY
	root.add_child(body)
	var crate := MeshInstance3D.new()   # they're short, so they stand on a crate behind the table
	crate.mesh = _crate_mesh
	crate.material_override = _crate_mat
	crate.position = Vector3(-0.12, VENDOR_DROP - CRATE_H / 2.0, 0)
	root.add_child(crate)
	var v := {"root": root, "body": body, "kind": kind, "state": "stand", "t": randf_range(2.0, 7.0), "calm": 0.0}
	var libs: Dictionary = riders._anim_libs.get(p.id, {})
	if libs.is_empty():
		return v
	var skel := body.find_child("Skeleton3D", true, false) as Skeleton3D
	for part in ["legs", "upper"]:
		var ap := AnimationPlayer.new()
		ap.add_animation_library("", libs[part])
		ap.playback_default_blend_time = 0.2
		skel.get_parent().add_child(ap)
		ap.play("Stand")
		ap.seek(randf() * ap.current_animation_length)
		v[part] = ap
	return v


func _play(v: Dictionary, legs: String, upper: String, then_stand := false) -> void:
	if not v.has("legs"):
		return
	(v.legs as AnimationPlayer).play(legs, 0.15)
	var up: AnimationPlayer = v.upper
	up.play(upper, 0.15)
	up.clear_queue()
	if then_stand:
		up.queue("Stand")


func _duck(st: Dictionary) -> void:
	var v: Dictionary = st.vendor
	if v.state == "duck":
		return
	v.state = "duck"
	v.calm = 0.0
	_play(v, "Duck", "Duck")
	if randf() < 0.5:
		effects.bubble(v.root, Vector3(0, 1.9, 0), DUCK_LINES.pick_random(), false, 1.2)


func _get_up(st: Dictionary) -> void:
	var v: Dictionary = st.vendor
	v.state = "stand"
	v.t = randf_range(4.0, 8.0)
	_play(v, "Stand", "ShakeFist", true)
	effects.bubble(v.root, Vector3(0, 1.9, 0), ANGRY_LINES.pick_random(), false, 1.8)


# ------------------------------------------------------------ the chaos

## Send a stall's goods flying: `push` is the main direction (a rider's speed, a shot's direction).
func burst(st: Dictionary, push: Vector3, n := 12) -> void:
	if st.cd > 0.0:
		return
	st.cd = STALL_COOLDOWN
	_duck(st)
	var table: Vector3 = st.table
	effects.puff(table, Color("e8dcc4"), 3, 0.6)
	Sfx.play("knock_off", 0.0, 0.9)
	var kinds: Array = _meshes[st.kind]
	for i in n:
		if flying.size() >= MAX_FLYING:
			_remove(0)
		var m: Array = kinds.pick_random()
		var mi := MeshInstance3D.new()
		mi.mesh = m[0]
		mi.material_override = m[1]
		mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		add_child(mi)
		mi.global_position = table + Vector3(randf_range(-1.0, 1.0), randf_range(0.0, 0.2), randf_range(-1.0, 1.0)) * 0.6
		mi.rotation = Vector3(randf() * TAU, randf() * TAU, randf() * TAU)
		var vel := push * randf_range(0.5, 1.1) + Vector3(randf_range(-2.5, 2.5), randf_range(4.5, 8.5), randf_range(-2.5, 2.5))
		flying.append({"node": mi, "vel": vel, "spin": Vector3(randf_range(-9, 9), randf_range(-9, 9), randf_range(-9, 9)),
			"life": randf_range(5.0, 7.0), "r": m[2], "kind": st.kind, "col": m[3], "landed": false})


func _stall_near(p: Vector3, dist: float) -> Dictionary:
	var best := {}
	var bd := dist
	for st in stalls:
		var d := Vector2(p.x - st.table.x, p.z - st.table.z).length()
		if d < bd:
			bd = d
			best = st
	return best


## A bullet or stone hit `collider`: if that is a stall, the goods fly away from the shot.
func shot(collider: Object, point: Vector3, dir: Vector3) -> bool:
	var n = collider
	while n and n is Node and not String((n as Node).name).begins_with("Stall_"):
		n = (n as Node).get_parent()
	if n == null or not n is Node:
		return false
	for st in stalls:
		if st.node == n:
			burst(st, Vector3(dir.x, 0, dir.z).normalized() * 3.0, 9)
			return true
	return false


## Explosions and riders knocked off next to a stall.
func bump(point: Vector3, radius: float, power := 6.0) -> void:
	for st in stalls:
		var to: Vector3 = st.table - point
		if to.length() < radius + 1.5:
			burst(st, Vector3(to.x, 0, to.z).normalized() * power, 16)
	for f in flying:   # and the produce already in the air gets blown further
		var to2: Vector3 = (f.node as Node3D).global_position - point
		if to2.length() < radius + 2.0:
			f.vel += to2.normalized() * power + Vector3(0, power * 0.6, 0)
			f.landed = false


## Flying produce along a ray: {t, item} of the nearest, or {}.
func raycast(origin: Vector3, dir: Vector3, max_dist: float) -> Dictionary:
	var best := {}
	for f in flying:
		if f.landed:
			continue
		var c: Vector3 = (f.node as Node3D).global_position - origin
		var tc := c.dot(dir)
		if tc < 0.0 or tc > max_dist:
			continue
		var r: float = f.r + 0.18   # a little generous: they're small and fast
		if c.length_squared() - tc * tc > r * r:
			continue
		if best.is_empty() or tc < best.t:
			best = {"t": tc, "item": f}
	return best


## Shot out of the air: splat. Returns [points, label] for the score popup.
func pop(f: Dictionary) -> Array:
	var at: Vector3 = (f.node as Node3D).global_position
	effects.splat(at, f.col, false)
	var i := flying.find(f)
	if i >= 0:
		_remove(i)
	return [BONUS, BONUS_LABEL.get(f.kind, "FRUITSALADE!")]


func _remove(i: int) -> void:
	var f: Dictionary = flying[i]
	if is_instance_valid(f.node):
		f.node.queue_free()
	flying.remove_at(i)


func step(dt: float) -> void:
	if stalls.is_empty() and flying.is_empty():
		return
	# riders tearing past: a crash into the stall (once per rider per stall), vendors duck
	for r in riders.list:
		if not r.alive:
			continue
		var pos: Vector3 = (r.root as Node3D).global_position
		var fwd := Vector3(cos(r.yaw), 0, -sin(r.yaw))
		for i in stalls.size():
			var st: Dictionary = stalls[i]
			var d := Vector2(pos.x - st.table.x, pos.z - st.table.z).length()
			if d < DUCK_DIST:
				_duck(st)
				st.vendor.calm = 0.0
			if d < RAM_DIST:
				var key := "%d|%d" % [r.id, i]
				if not _rammed.has(key):
					_rammed[key] = true
					if pos.y > 0.4 or randf() < 0.55:   # jumpers always clip it
						burst(st, fwd * float(r.speed) * 0.55)
	_pick_t -= dt
	if _pick_t <= 0.0:
		_pick_t = 0.5
		var near := stalls.filter(func(s2): return (s2.table as Vector3).distance_to(player_eye) < VENDOR_RANGE)
		near.sort_custom(func(a, b): return (a.table as Vector3).distance_to(player_eye) < (b.table as Vector3).distance_to(player_eye))
		_active = near.slice(0, MAX_VENDORS_WEB if OS.has_feature("web") else MAX_VENDORS)
	for st in stalls:
		st.cd = maxf(0.0, st.cd - dt)
		var v: Dictionary = st.vendor
		if not is_instance_valid(v.root):
			continue
		# out of sight, out of mind: only the few nearest vendors live, the others are hidden with their skeletons
		# standing still (skinning a character is about as expensive as a rider, in WebGL above all)
		var on: bool = _active.has(st)
		if on != v.get("on", true):
			v.on = on
			(v.root as Node3D).visible = on
			for k in ["legs", "upper"]:
				if v.has(k):
					(v[k] as AnimationPlayer).active = on
		if not on:
			continue
		if v.state == "duck":
			v.calm += dt
			if v.calm > 1.0:
				_get_up(st)
			continue
		v.t -= dt
		if v.t <= 0.0:
			v.t = randf_range(5.0, 10.0)
			var near: bool = (v.root as Node3D).global_position.distance_to(player_eye) < 45.0
			if near and (v.root as Node3D).is_visible_in_tree():
				_play(v, "Stand", "Shout", true)
				effects.bubble(v.root, Vector3(0, 1.9, 0), (SHOUTS[st.kind] as Array).pick_random(), false, 2.2)
	# produce: tumbling, bouncing once or twice, then lying around for a bit and sinking away
	for i in range(flying.size() - 1, -1, -1):
		var f: Dictionary = flying[i]
		var n: Node3D = f.node
		f.life -= dt
		if f.life <= 0.0 or not is_instance_valid(n):
			_remove(i)
			continue
		if f.landed:
			if f.life < 0.8:
				n.position.y -= dt * 0.25
			continue
		f.vel.y -= Config.GRAVITY * 1.1 * dt
		n.global_position += f.vel * dt
		n.rotation += f.spin * dt
		var floor_y: float = f.r
		if n.global_position.y < floor_y:
			n.global_position.y = floor_y
			if absf(f.vel.y) < 2.0:
				f.landed = true
				continue
			f.vel = Vector3(f.vel.x * 0.5, absf(f.vel.y) * 0.35, f.vel.z * 0.5)
			f.spin *= 0.5


# ------------------------------------------------------------ produce meshes (shared, cheap)

func _mat(hex: String, rough := 0.5) -> StandardMaterial3D:
	var m := StandardMaterial3D.new()
	m.albedo_color = Color(hex)
	m.roughness = rough
	return m


func _sphere(r: float, hex: String, squash := 1.0) -> Array:
	var s := SphereMesh.new()
	s.radius = r
	s.height = r * 2.0 * squash
	s.radial_segments = 10
	s.rings = 6
	return [s, _mat(hex), r, Color(hex)]


func _cyl(r_top: float, r_bot: float, h: float, hex: String) -> Array:
	var c := CylinderMesh.new()
	c.top_radius = r_top
	c.bottom_radius = r_bot
	c.height = h
	c.radial_segments = 10
	c.rings = 1
	return [c, _mat(hex), maxf(maxf(r_top, r_bot), h * 0.5), Color(hex)]


func _build_meshes() -> void:
	_crate_mesh = BoxMesh.new()
	_crate_mesh.size = Vector3(0.5, CRATE_H, 0.6)
	_crate_mat = _mat("#8a6a44", 0.8)
	_meshes = {
		"fruit": [_sphere(0.08, "#d8282a"), _sphere(0.085, "#f08a24"), _sphere(0.075, "#7cb83a"), _sphere(0.08, "#f2c425", 1.6)],
		"groente": [_sphere(0.075, "#e0302a"), _sphere(0.13, "#86c044"), _cyl(0.005, 0.035, 0.24, "#f08a24"), _cyl(0.04, 0.04, 0.28, "#2f6a2a")],
		"kaas": [_cyl(0.2, 0.2, 0.12, "#f2c14a"), _cyl(0.12, 0.12, 0.09, "#e8b03a")],
		"bloemen": [_sphere(0.07, "#ea6aa4"), _sphere(0.07, "#d8282a"), _sphere(0.07, "#f2c425"), _cyl(0.01, 0.01, 0.35, "#4f8a2c")],
		"wafels": [_cyl(0.14, 0.14, 0.025, "#b8763a"), _cyl(0.14, 0.14, 0.025, "#a8682e")],
	}
