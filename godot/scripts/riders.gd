class_name Riders
extends Node3D
## Fatbikers: spawning, routes around the fountain, the mixed crowd, hit tests, knock-offs and knives.
## Port of src/riders.js.

signal player_hit(knife_vel: Vector3)

const RING_NODES := 12
# Hit spheres in model space (+X forward): [centre, radius, part, who]
const DRIVER_SPHERES := [
	[Vector3(0.075, 1.6, 0), 0.27, "head", "driver"],
	[Vector3(-0.07, 1.17, 0), 0.3, "body", "driver"],
	[Vector3(-0.12, 0.88, 0), 0.28, "body", "driver"],
	[Vector3(0.42, 0.5, 0), 0.4, "bike", "driver"],
	[Vector3(-0.45, 0.5, 0), 0.4, "bike", "driver"],
]
const PASSENGER_OFFSET := Vector3(-0.36, 0.02, 0)
# Fallback variant metadata (glTF extras), keyed by id.
const VARIANT_META := {
	"V01": {"age": "adult", "top": "tracksuit", "bottom": "trackpants", "hairGroup": "young", "cap": "", "basket": false},
	"V02": {"age": "adult", "top": "tshirt", "bottom": "shorts", "hairGroup": "young", "cap": "back", "basket": false},
	"V03": {"age": "teen", "top": "tank", "bottom": "shorts", "hairGroup": "young", "cap": "", "basket": false},
	"V04": {"age": "adult", "top": "tank", "bottom": "jeans", "hairGroup": "young", "cap": "", "basket": false},
	"V05": {"age": "senior", "top": "polo", "bottom": "shorts", "hairGroup": "grey", "cap": "flat", "basket": false},
	"V06": {"age": "teen", "top": "tshirt", "bottom": "shorts", "hairGroup": "young", "cap": "", "basket": false},
	"V07": {"age": "adult", "top": "tank", "bottom": "jeans", "hairGroup": "young", "cap": "", "basket": false},
	"V08": {"age": "adult", "top": "tracksuit", "bottom": "trackpants", "hairGroup": "young", "cap": "", "basket": false},
	"V09": {"age": "senior", "top": "cardigan", "bottom": "skirt", "hairGroup": "grey", "cap": "", "basket": true},
	"V10": {"age": "adult", "top": "tshirt", "bottom": "leggings", "hairGroup": "young", "cap": "front", "basket": false},
	"V11": {"age": "adult", "top": "tshirt", "bottom": "shorts", "hairGroup": "young", "cap": "", "basket": false},
	"V12": {"age": "teen", "top": "tracksuit", "bottom": "leggings", "hairGroup": "young", "cap": "", "basket": false},
}

var effects: Effects
var world: World   # line-of-sight checks: riders only throw when they can see you, knives stop at walls
var player_eye := Vector3.ZERO
var player_vel := Vector3.ZERO   # the player walks in the adventure mode: knives lead the target
var player_fwd := Vector3.FORWARD
# Where the player can aim (set by Game every frame): riders only throw from inside this cone, so every
# knife can be seen coming and shot down.
var cone_yaw := 0.0
var cone_half := PI
var peaceful := false   # chill level: nobody throws
var throw_gap := 0.0   # > 0: one throw at a time, at least this many seconds apart (adventure walk)
var _throw_cd := 0.0
var settings := {"accuracy": 0.6, "windup": 0.75}
var list: Array = []
var knives: Array = []
var spawn_timer := 1.0
var retaliate_cooldown := 0.0
var _next_id := 0
var force_variant := ""   # dev: everybody is this variant (e.g. "V01", via --rider=V01)

var _bike_tpl: Node3D
var _basket_tpl: Node3D
var _variants: Array = []  # [{node, id, meta}]
var _knife_tpl: Node3D
var _anim_libs := {}   # rigged variants: {id: {"legs", "upper"}} (RiderAnim)
var _boombox_tpl: Node3D
var _mat_cache := {}
var _blob_mesh: QuadMesh
var _blob_mat: StandardMaterial3D


func setup(fx: Effects, eye: Vector3) -> void:
	effects = fx
	player_eye = eye
	var lib: Node3D = load("res://assets/models/riders.glb").instantiate()
	add_child(lib)
	lib.visible = false
	# the Blender export bakes ambient occlusion into vertex colours (COLOR_0): multiply it into every material
	for mi in lib.find_children("*", "MeshInstance3D", true, false):
		var mesh = (mi as MeshInstance3D).mesh
		for s in mesh.get_surface_count():
			var mat = mesh.surface_get_material(s) as BaseMaterial3D
			if mat:
				mat.vertex_color_use_as_albedo = true
	for n in lib.find_children("*", "", true, false):
		var nm = String(n.name)
		if (nm.begins_with("Rider_") or nm.begins_with("Bike_")) and not _is_variant(nm):
			var clean = _strip_suffix(nm)
			if clean != nm:
				n.name = clean
	for c in lib.find_children("*", "Node3D", true, false):
		var nm = String(c.name)
		if nm == "Bike":
			_bike_tpl = c
		elif nm == "Bike_Basket":
			_basket_tpl = c
		elif _is_variant(nm):
			var id = nm.substr(6)
			var meta: Dictionary = VARIANT_META.get(id, VARIANT_META.V01)
			if c.has_meta("extras"):
				var ex = c.get_meta("extras")
				if ex is Dictionary and ex.has("age"):
					meta = ex
			_variants.append({"node": c, "id": id, "meta": meta})
	_anim_libs = RiderAnim.libraries(lib)
	_knife_tpl = (_variants[0].node as Node3D).find_child("Rider_Knife", true, false).duplicate()
	_knife_tpl.transform = Transform3D.IDENTITY
	_knife_tpl.scale = Vector3.ONE * 1.6
	_boombox_tpl = _make_boombox()
	_blob_mesh = QuadMesh.new()
	_blob_mesh.size = Vector2(1.7, 1.7)
	_blob_mat = StandardMaterial3D.new()
	var g = Gradient.new()
	g.set_color(0, Color(0, 0, 0, 0.55))
	g.set_color(1, Color(0, 0, 0, 0))
	var t = GradientTexture2D.new()
	t.gradient = g
	t.fill = GradientTexture2D.FILL_RADIAL
	t.fill_from = Vector2(0.5, 0.5)
	t.fill_to = Vector2(1.0, 0.5)
	_blob_mat.albedo_texture = t
	_blob_mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	_blob_mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED


static func _is_variant(nm: String) -> bool:
	return nm.begins_with("Rider_V") and nm.substr(7).is_valid_int()


static func _strip_suffix(nm: String) -> String:
	var re = RegEx.new()
	re.compile("[._]?\\d{3}$")
	return re.sub(nm, "")


# ------------------------------------------------------------ construction

func _variant_mat(mat: Material, col: String) -> Material:
	var key = "%d%s" % [mat.get_instance_id(), col]
	if not _mat_cache.has(key):
		var m: Material = mat.duplicate()
		if m is BaseMaterial3D:
			(m as BaseMaterial3D).albedo_color = Color(col)
		_mat_cache[key] = m
	return _mat_cache[key]


func _paint(node: Node, colors: Dictionary) -> void:
	for mi in node.find_children("*", "MeshInstance3D", true, false):
		var m = mi as MeshInstance3D
		m.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		if m.mesh == null:
			continue
		for s in m.mesh.get_surface_count():
			var mat = m.mesh.surface_get_material(s)
			if mat == null:
				continue
			var key = mat.resource_name.get_slice("_", 0)   # "Top_Rib" takes the colour of "Top"
			if colors.has(key):
				m.set_surface_override_material(s, _variant_mat(mat, colors[key]))


static func _shade(hex: String, f: float) -> String:
	var c = Color(hex)
	return "#" + Color(c.r * f, c.g * f, c.b * f).to_html(false)


func _person(exclude := "") -> Dictionary:
	var pool = _variants.filter(func(v): return v.id != exclude)
	if force_variant != "":
		pool = _variants.filter(func(v): return v.id == force_variant)
	var v: Dictionary = pool.pick_random()
	var meta: Dictionary = v.meta
	var light = func(c): return c in ["#e9e9ec", "#f4cf3a", "#d6d0c4", "#c9b48a"]
	var P = Config.PALETTES
	var skin: String = P.skin.pick_random()
	var hair: String = (P.hair_grey if meta.hairGroup == "grey" else P.hair_young).pick_random()
	var top: String = (P.cardigan if meta.top == "cardigan" else P.top).pick_random()
	var bottom: String = P.get(meta.bottom, P.shorts).pick_random()
	return {
		"id": v.id, "meta": meta, "shades": randf() < 0.4,
		"colors": {
			"Skin": skin, "SkinShade": _shade(skin, 0.8), "Hair": hair, "Brow": _shade(hair, 0.85 if meta.hairGroup == "grey" else 0.7),
			"Top": top, "TopTrim": "#1a1a20" if light.call(top) else "#f4f4f4", "Bottom": bottom, "BottomTrim": "#1a1a20" if light.call(bottom) else "#f4f4f4",
			"Cap": (P.flatcap if meta.cap == "flat" else P.cap).pick_random(), "Shoe": P.shoe.pick_random(),
		},
	}


## A bare (riderless) fatbike in the given colours, e.g. for the boss intro.
func make_bike(frame: String, accent: String) -> Node3D:
	var holder = Node3D.new()
	var bike: Node3D = _bike_tpl.duplicate()
	bike.transform = Transform3D.IDENTITY
	bike.visible = true
	_paint(bike, {"BikeFrame": frame, "BikeAccent": accent})
	for mi in bike.find_children("*", "GeometryInstance3D", true, false):
		(mi as GeometryInstance3D).cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_ON
	holder.add_child(bike)
	return holder


## Everybody off the square, fast (the boss is coming). Knives in the air are dropped.
func flee(lines := ["WEGWEZEN!", "HIJ KOMT ERAAN!", "MAMAAA!", "RENNEN!"]) -> void:
	for r in list:
		r.speed = maxf(r.speed * 2.6, 18.0)
		r.attack_point = null
		r.windup = 0.0
		effects.bubble(r.root, Vector3(0, 2.5, 0), lines.pick_random(), false, 1.6)
	for k in knives:
		k.mesh.queue_free()
	knives.clear()


func _build(type: String) -> Dictionary:
	var driver = _person()
	var people = [driver]
	if type == "duo":
		people.append(_person(driver.id))
	var bike_col: Array = Config.BIKE_COLORS.pick_random()
	var model = Node3D.new()
	model.position = Vector3(0.58, 0, 0)
	var anims := []
	var bike: Node3D = _bike_tpl.duplicate()
	bike.transform = Transform3D.IDENTITY
	_paint(bike, {"BikeFrame": bike_col[0], "BikeAccent": bike_col[1]})
	model.add_child(bike)
	if driver.meta.get("basket", false) and _basket_tpl:
		var b: Node3D = _basket_tpl.duplicate()
		b.transform = Transform3D.IDENTITY
		bike.add_child(b)
	for i in people.size():
		var p: Dictionary = people[i]
		var src: Node3D = _variants.filter(func(v): return v.id == p.id)[0].node
		var r: Node3D = src.duplicate()
		r.transform = Transform3D.IDENTITY
		r.name = "Rider" if i == 0 else "Passenger"
		if i > 0:
			r.position = PASSENGER_OFFSET
			var k = r.find_child("Rider_Knife", true, false)
			if k:
				k.visible = false
		_paint(r, p.colors)
		var shades = r.find_child("Rider_Sunglasses", true, false)
		if shades:
			shades.visible = p.shades
		if _anim_libs.has(p.id):
			var a := RiderAnim.attach(r, _anim_libs[p.id], bike.find_child("Bike_Crank", true, false) if i == 0 else null)
			r.set_meta("anim", a)
			anims.append(a)
		model.add_child(r)
	var pivot = Node3D.new()
	pivot.position = Vector3(-0.58, 0, 0)
	pivot.rotation_order = EULER_ORDER_XZY
	pivot.add_child(model)
	var root = Node3D.new()
	root.add_child(pivot)
	var blob = MeshInstance3D.new()
	blob.mesh = _blob_mesh
	blob.material_override = _blob_mat
	blob.rotation.x = -PI / 2
	blob.scale = Vector3(1.5, 0.6, 1)
	blob.position.y = 0.03
	blob.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	root.add_child(blob)
	var boombox: Node3D = null
	if type == "boss":
		boombox = _boombox_tpl.duplicate()
		boombox.position = Vector3(-0.52 + 0.58, 1.02, 0)
		pivot.add_child(boombox)
		root.scale = Vector3.ONE * 1.25
	return {"root": root, "pivot": pivot, "model": model, "bike": bike, "blob": blob, "boombox": boombox, "age": driver.meta.age, "anims": anims}


# ------------------------------------------------------------ routes

func _ring_point(i: int, R: float) -> Vector3:
	var a = float(posmod(i, RING_NODES)) / RING_NODES * TAU
	return Vector3(Config.FOUNTAIN.x + cos(a) * R, 0, Config.FOUNTAIN.z + sin(a) * R)


func _nearest_ring(p: Vector3, R: float) -> int:
	var best = 0
	var bd = INF
	for i in RING_NODES:
		var d = _ring_point(i, R).distance_squared_to(p)
		if d < bd:
			bd = d
			best = i
	return best


func _weighted_entry(exclude) -> Dictionary:
	var pool = Config.ENTRIES.filter(func(e): return e != exclude)
	var total = 0.0
	for e in pool:
		total += e.weight
	var r = randf() * total
	for e in pool:
		r -= e.weight
		if r <= 0:
			return e
	return pool[0]


func _route(entry: Dictionary, exit: Dictionary, attack: bool) -> Dictionary:
	var R = Config.RING_RADIUS + randf_range(-1.6, 1.6)
	var pts: Array[Vector3] = [entry.spawn]
	pts.append_array(entry.get("via", []))
	pts.append(entry.mouth)
	var first_free = pts.size()  # points before this follow the street exactly
	var dir = 1 if randf() < 0.5 else -1
	var i = _nearest_ring(entry.mouth, R)
	for s in 2 + randi() % 6:
		pts.append(_ring_point(i, R))
		i += dir
	var attack_point = null
	if attack:
		var front = RING_NODES / 4
		for g in RING_NODES:
			if posmod(i, RING_NODES) == front:
				break
			pts.append(_ring_point(i, R))
			i += dir
		attack_point = Vector3(Config.OFFSET.x + randf_range(-3.5, 3.5), 0, Config.ATTACK_Z)
		pts.append(attack_point)
		i += dir
	var exit_node = _nearest_ring(exit.mouth, R)
	for g in RING_NODES:
		if posmod(i, RING_NODES) == exit_node:
			break
		pts.append(_ring_point(i, R))
		i += dir
	pts.append(_ring_point(exit_node, R))
	pts.append(exit.mouth)
	var exit_via: Array = exit.get("via", []).duplicate()
	exit_via.reverse()
	pts.append_array(exit_via)
	var last_free = pts.size() - exit_via.size()
	pts.append(exit.spawn)
	for k in range(first_free, last_free - 1):
		pts[k] += Vector3(randf_range(-0.6, 0.6), 0, randf_range(-0.6, 0.6))
	return {"curve": smooth_curve(pts, Config.MAP.get("tight_routes", false)), "attack_point": attack_point}


## Catmull-Rom through the points as a bezier Curve3D. `tight` keeps the curve from overshooting where a
## long street meets a short hop (e.g. out of the gallery).
static func smooth_curve(pts: Array, tight := false) -> Curve3D:
	var curve = Curve3D.new()
	curve.bake_interval = 0.25
	for k in pts.size():
		var prev: Vector3 = pts[maxi(k - 1, 0)]
		var nxt: Vector3 = pts[mini(k + 1, pts.size() - 1)]
		var tng = (nxt - prev) * 0.5 / 3.0
		if tight and k > 0 and k < pts.size() - 1:
			var lim = minf(pts[k].distance_to(prev), pts[k].distance_to(nxt)) * 0.4
			if tng.length() > lim:
				tng = tng.normalized() * lim
		curve.add_point(pts[k], -tng, tng)
	return curve


# ------------------------------------------------------------ spawning / update

func spawn(type: String, diff: Dictionary) -> Dictionary:
	var entry = _weighted_entry(null)
	var exit = _weighted_entry(entry)
	var attack = (type == "normal" or type == "duo") and randf() < diff.attack_chance
	var route = _route(entry, exit, attack)
	var r = _spawn_on(type, route.curve, route.attack_point, diff.speed_mul)
	# entries with a "hop" [from, to, height]: jump that bit (over the turnstiles), whichever way they ride it
	var c: Curve3D = route.curve
	var hops := []
	for e in [entry, exit]:
		if e.has("hop"):
			var a := c.get_closest_offset(e.hop[0])
			var b := c.get_closest_offset(e.hop[1])
			hops.append([minf(a, b), maxf(a, b), e.hop[2]])
	r.hops = hops
	if entry.has("shouts") and type != "boss":
		effects.bubble(r.root, Vector3(0, 2.5, 0), (entry.shouts as Array).pick_random(), false, 3.0)
	return r


## A scripted rider (adventure mode): rides the given points (Godot coords). With `attack_near` > 0 it winds
## up a throw once it gets that close to the (walking) player while in front of them and in sight.
## hops: [[from, to, height]] jumps between two of the points.
func spawn_path(type: String, pts: Array, speed_mul: float, attack_near := 0.0, hops := []) -> Dictionary:
	var curve := smooth_curve(pts, true)
	var r = _spawn_on(type, curve, null, speed_mul)
	r.attack_near = attack_near if type != "wheelie" else 0.0
	r.hops = hops.map(func(h): return [curve.get_closest_offset(h[0]), curve.get_closest_offset(h[1]), h[2]])
	return r


## A fatbiker on the roller coaster: rides the track points (Godot coords, from Coaster.path_points) at the
## coaster's speed (speed_at: distance along these points -> m/s), upside down through the loop. Never throws.
func spawn_rails(type: String, pts: Array, speed_at: Callable) -> Dictionary:
	var curve := smooth_curve(pts)
	curve.up_vector_enabled = true
	var r = _spawn_on(type, curve, null, 1.0)
	r.air = true
	r.speed_at = speed_at
	r.hit_pad = 0.6   # far away, high up and fast: forgiving
	(r.blob as Node3D).visible = false
	(r.root as Node3D).scale = Vector3.ONE * 2.0   # and big, so you spot him
	(r.pivot as Node3D).add_child(_safety_flag())
	_place(r, 0.0)
	return r


var _flag_mat: StandardMaterial3D


## A tall pole with a bright orange pennant on the back of the bike (as on kids' bikes): easy to spot.
func _safety_flag() -> Node3D:
	var n := Node3D.new()
	n.position = Vector3(-0.15, 0.6, 0)
	if _flag_mat == null:
		_flag_mat = StandardMaterial3D.new()
		_flag_mat.albedo_color = Color("ff6a00")
		_flag_mat.emission_enabled = true
		_flag_mat.emission = Color("ff6a00")
		_flag_mat.emission_energy_multiplier = 1.5
	var mat := _flag_mat
	var pole := MeshInstance3D.new()
	var pm := CylinderMesh.new()
	pm.top_radius = 0.02
	pm.bottom_radius = 0.02
	pm.height = 1.8
	pole.mesh = pm
	pole.position.y = 0.9
	pole.material_override = mat
	n.add_child(pole)
	var flag := MeshInstance3D.new()
	var fm := PrismMesh.new()
	fm.size = Vector3(0.45, 0.6, 0.02)
	flag.mesh = fm
	flag.rotation.z = -PI / 2
	flag.position = Vector3(-0.3, 1.55, 0)
	flag.material_override = mat
	n.add_child(flag)
	return n


## Is this position inside the player's aiming cone?
func in_cone(p: Vector3) -> bool:
	var d := Vector3(p.x - player_eye.x, 0, p.z - player_eye.z)
	if d.length() < 0.5:
		return false
	return absf(wrapf(atan2(-d.x, -d.z) - cone_yaw, -PI, PI)) <= cone_half


## May this rider throw now: in sight and where the player can aim at it?
func can_throw(r: Dictionary) -> bool:
	return in_cone((r.root as Node3D).position) and sees_player(r)


## May a new throw start now (one at a time while throw_gap is set)?
func _may_start_throw(r: Dictionary) -> bool:
	if peaceful:
		return false
	if throw_gap > 0.0 and (_throw_cd > 0.0 or list.any(func(x): return x.get("windup", 0.0) > 0.0)):
		return false
	return can_throw(r)


## Can this rider see the player (nothing solid between its head and the player's eye)?
func sees_player(r: Dictionary) -> bool:
	if world == null:
		return true
	var head: Vector3 = (r.root as Node3D).position + Vector3(0, 1.5, 0)
	var to := head - player_eye
	return world.raycast(player_eye, to.normalized(), maxf(0.0, to.length() - 0.7)).is_empty()


func _spawn_on(type: String, curve: Curve3D, attack_point, speed_mul: float) -> Dictionary:
	var m = _build(type)
	var base: float = {"normal": randf_range(6.5, 8.8), "duo": randf_range(5.8, 7.0), "wheelie": randf_range(11, 13), "boss": randf_range(4.8, 5.6)}[type]
	var spheres = DRIVER_SPHERES.duplicate()
	if type == "duo":
		for s in DRIVER_SPHERES.slice(0, 3):
			spheres.append([s[0] + PASSENGER_OFFSET, s[1], s[2], "passenger"])
	if type == "boss":
		spheres.append([Vector3(-0.52, 1.02, 0), 0.32, "body", "driver"])
	_next_id += 1
	var r = m.merged({
		"id": _next_id, "type": type, "curve": curve, "len": curve.get_baked_length(), "dist": 0.0,
		"speed": base * speed_mul, "alive": true, "attack_point": attack_point, "thrown": false, "attack_near": 0.0,
		"knife_cooldown": randf_range(1, 3), "hp": 3 if type == "boss" else 1, "shout_timer": randf_range(1.5, 4),
		"bell_timer": randf_range(2, 6), "yaw": 0.0, "roll": 0.0, "wheelie": 0.42 if type == "wheelie" else 0.0,
		"bob": randf() * 10.0, "spheres": spheres,
	})
	add_child(r.root)
	_place(r, 0.0)
	list.append(r)
	if type == "boss":
		effects.bubble(r.root, Vector3(0, 2.9, 0), Config.BOSS_SHOUTS.pick_random(), false, 2.2)
	return r


func _place(r: Dictionary, dt: float) -> void:
	var curve: Curve3D = r.curve
	var d: float = minf(r.dist, r.len - 0.01)
	if r.get("air", false):   # on the rails: follow the track's own up (loops included)
		var p3 := curve.sample_baked(d, true)
		var fwd := (curve.sample_baked(minf(d + 0.4, r.len), true) - curve.sample_baked(maxf(d - 0.4, 0.0), true)).normalized()
		var up := curve.sample_baked_up_vector(d, true)
		up = (up - fwd * up.dot(fwd)).normalized()
		(r.root as Node3D).transform = Transform3D(Basis(fwd, up, fwd.cross(up)).scaled((r.root as Node3D).scale), p3 + up * 0.15)
		r.yaw = atan2(-fwd.z, fwd.x)
		r.bob += dt * r.speed * 1.3
		return
	var p = curve.sample_baked(d, true)
	var ahead = curve.sample_baked(minf(d + 0.4, r.len), true)
	var t = ahead - p
	if t.length() < 0.001:
		t = Vector3(cos(r.yaw), 0, -sin(r.yaw))
	var root: Node3D = r.root
	var hop_y := 0.0
	var hop_pitch := 0.0
	for h in r.get("hops", []):
		if d >= h[0] and d <= h[1] and h[1] > h[0]:
			var ht: float = (d - h[0]) / (h[1] - h[0])
			hop_y = 4.0 * h[2] * ht * (1.0 - ht)
			hop_pitch = 0.45 * (1.0 - 2.0 * ht)
	root.position = Vector3(p.x, hop_y, p.z)
	var yaw = atan2(-t.z, t.x)
	var dy = wrapf(yaw - r.yaw, -PI, PI)
	r.yaw = yaw
	root.rotation.y = yaw
	if dt > 0:
		var target_roll = clampf((dy / dt) * r.speed * 0.045, -0.4, 0.4)
		r.roll += (target_roll - r.roll) * minf(1.0, dt * 5.0)
	r.bob += dt * r.speed * 1.3
	var pivot: Node3D = r.pivot
	pivot.rotation = Vector3(-r.roll, 0, r.wheelie + hop_pitch + (sin(r.bob * 0.6) * 0.06 if r.wheelie > 0 else 0.0))
	(r.model as Node3D).position.y = absf(sin(r.bob)) * 0.02
	if r.boombox:
		(r.boombox as Node3D).scale = Vector3.ONE * (1.0 + maxf(0.0, sin(Time.get_ticks_msec() * 0.0126)) * 0.12)


func step(dt: float, diff: Dictionary, elapsed: float) -> void:
	retaliate_cooldown -= dt
	_throw_cd -= dt
	spawn_timer -= dt
	if spawn_timer <= 0 and list.size() < diff.max_alive:
		spawn_timer = diff.spawn_interval * randf_range(0.7, 1.3)
		var type = "normal"
		var roll = randf()
		var has_boss = list.any(func(x): return x.type == "boss")
		if elapsed > 25 and not has_boss and roll < 0.1:
			type = "boss"
		elif elapsed > 15 and roll < 0.24:
			type = "wheelie"
		elif elapsed > 8 and roll < 0.36:
			type = "duo"
		spawn(type, diff)
		if elapsed > 20 and randf() < 0.3:
			spawn("normal", diff)

	for i in range(list.size() - 1, -1, -1):
		var r: Dictionary = list[i]
		r.knife_cooldown -= dt
		var speed: float = r.speed
		if r.has("speed_at"):
			speed = r.speed_at.call(r.dist)
		if r.attack_point != null and not r.thrown:
			var ap: Vector3 = r.attack_point
			var d = Vector2(r.root.position.x - ap.x, r.root.position.z - ap.z).length()
			if d < 6:
				speed *= 0.65
			if d < 2.5 and _may_start_throw(r):
				start_windup(r, randf() < settings.accuracy)
		elif r.attack_near > 0.0 and not r.thrown and r.alive and (r.root as Node3D).position.y < 0.3:
			var to: Vector3 = (r.root as Node3D).position - Vector3(player_eye.x, 0, player_eye.z)
			if to.length() < r.attack_near and to.dot(player_fwd) > 3.0 and _may_start_throw(r):
				start_windup(r, randf() < settings.accuracy)
		if r.get("freeze", 0.0) > 0.0:   # brain freeze
			r.freeze -= dt
			speed *= 0.4
		if r.get("windup", 0.0) > 0.0:  # winding up for a throw: slow down, then let go
			speed *= 0.5
			r.windup -= dt
			if r.windup <= 0.0:
				_release_knife(r)
		r.dist += speed * dt
		if r.dist >= r.len:
			r.root.queue_free()
			list.remove_at(i)
			continue
		_place(r, dt)
		var w = (speed / 0.33) * dt
		for wn in ["Bike_WheelFront", "Bike_WheelRear"]:
			var wheel = (r.bike as Node3D).find_child(wn, true, false) as Node3D
			if wheel:
				wheel.rotate_object_local(Vector3(0, 0, 1), -w)
		for a in r.anims:
			RiderAnim.ride(a, speed)
		var dist: float = (r.root as Node3D).position.distance_to(player_eye)
		r.shout_timer -= dt
		if r.shout_timer <= 0:
			r.shout_timer = randf_range(4, 8)
			if dist < 40:
				var lines: Array = Config.BOSS_SHOUTS if r.type == "boss" else (Config.SHOUTS.get(r.age, Config.SHOUTS.any) if randf() < 0.55 else Config.SHOUTS.any)
				effects.bubble(r.root, Vector3(0, 2.5, 0), lines.pick_random())
				if not r.anims.is_empty() and randf() < 0.6:
					RiderAnim.react(r.anims[0], "ShakeFist")
		r.bell_timer -= dt
		if r.bell_timer <= 0:
			r.bell_timer = randf_range(4, 9)
			if dist < 35:
				Sfx.bell(clampf((r.root.position.x - player_eye.x) / 20.0, -1, 1))
	_update_knives(dt)


# ------------------------------------------------------------ hit tests

## All rider hits along a ray, sorted by distance: [{rider, t, point, part, who}]
func raycast(origin: Vector3, dir: Vector3, max_dist := 300.0, pad := 0.0) -> Array:
	var hits = []
	for r in list:
		if not r.alive:
			continue
		var oc: Vector3 = (r.root as Node3D).position + Vector3(0, 1, 0) - origin
		var tc = oc.dot(dir)
		if tc < -3 or tc > max_dist + 3 or oc.length_squared() - tc * tc > 9.0:
			continue
		var xf: Transform3D = (r.model as Node3D).global_transform
		var scale: float = (r.root as Node3D).scale.x
		var best = null
		for s in r.spheres:
			var c: Vector3 = xf * (s[0] as Vector3) - origin
			var rad: float = s[1] * scale + pad + r.get("hit_pad", 0.0)
			var tca = c.dot(dir)
			var d2 = c.length_squared() - tca * tca
			if d2 > rad * rad:
				continue
			var thc = sqrt(rad * rad - d2)
			var t = tca - thc
			if t < 0:
				t = tca + thc
			if t < 0 or t > max_dist:
				continue
			if best == null or t < best.t:
				best = {"rider": r, "t": t, "part": s[2], "who": s[3]}
		if best != null:
			best.point = origin + dir * best.t
			hits.append(best)
	hits.sort_custom(func(a, b): return a.t < b.t)
	return hits


func in_radius(center: Vector3, radius: float) -> Array:
	return list.filter(func(r): return r.alive and (r.root as Node3D).position.distance_to(center) < radius + 0.6 * (r.root as Node3D).scale.x)


# ------------------------------------------------------------ damage / slapstick

func damage(r: Dictionary, amount: float, dir: Vector3, power: float, shout := true) -> bool:
	if not r.alive:
		return false
	r.hp -= amount
	if r.hp > 0 and not shout:
		return false
	if r.hp > 0:
		var lines = Config.PAIN_SHOUTS.duplicate()
		if r.type == "boss":
			lines.append("Mijn speaker!")
		effects.bubble(r.root, Vector3(0, 2.9, 0), lines.pick_random(), false, 1.2)
		for a in r.anims:
			RiderAnim.react(a, "Shock")
		return false
	knock_off(r, dir, power, false)
	return true


const FREEZE_SHOUTS := ["BREINVRIES!", "BRRRR!", "KOUD, KOUD, KOUD!", "AAH, MIJN HOOFD!", "IJSKOUD!", "Is dit aardbei?!"]


## Hit by a scoop of ice cream: brain freeze (slow for a moment) and the scoop sticks where it landed.
func freeze(r: Dictionary, point: Vector3, col: Color, scoop: Node3D) -> void:
	if not r.alive:
		scoop.queue_free()
		return
	if r.get("freeze", 0.0) <= 0.0 and r.hp > 0.5:   # don't shout when this scoop knocks him off anyway
		effects.bubble(r.root, Vector3(0, 2.9, 0), FREEZE_SHOUTS.pick_random(), false, 1.2)
	r.freeze = 1.4
	var stuck: Array = r.get("stuck", [])
	if stuck.size() >= 5:
		scoop.queue_free()
		return
	var model: Node3D = r.model
	model.add_child(scoop)
	scoop.global_position = point
	scoop.scale = Vector3(1.0, 0.7, 1.0)
	stuck.append(scoop)
	r.stuck = stuck


const HANG := 0.65   # riders (and their hair) fall at reduced gravity: a long, flailing flight

func knock_off(r: Dictionary, dir: Vector3, power := 6.0, explode := false) -> void:
	r.alive = false
	var model: Node3D = r.model
	var root: Node3D = r.root
	var fwd = Vector3(cos(r.yaw), 0, -sin(r.yaw))
	var carry = fwd * r.speed * 0.5
	var flat = Vector3(dir.x, 0, dir.z)
	var push = (flat.normalized() if flat.length() > 0.01 else fwd) * power
	var rand_ang = func(s): return Vector3(randf_range(-s, s), randf_range(-s, s), randf_range(-s, s))
	for nm in ["Rider", "Passenger"]:
		var body = model.find_child(nm, false, false) as Node3D
		if body == null:
			continue
		var hair = body.find_child("Rider_Hair", true, false) as Node3D
		var head = body.find_child("Rider_Head", true, false) as Node3D
		if hair and head:
			var hc = head.global_transform * Vector3(0.05, 0.25, 0)
			effects.add_debris(hair, hc, push * 0.5 + Vector3(randf_range(-1, 1), randf_range(7, 8.5), randf_range(-1, 1)), rand_ang.call(12.0), {"radius": 0.18, "life": 4.2, "bounce": 0.5, "gravity": HANG})
		var center = body.global_transform * Vector3(-0.1, 1.1, 0)
		var up = randf_range(9, 10.5) if explode else randf_range(6.5, 7.5)
		var vel = (push + carry) * 0.7 + Vector3(0, up, 0)
		# a backflip in the direction he flies (head first), with a bit of twist: no random tumbling
		var flat_v = Vector3(vel.x, 0, vel.z)
		var axis = Vector3.UP.cross(flat_v.normalized()) if flat_v.length() > 0.1 else Vector3.UP.cross(fwd)
		var spin = axis * randf_range(3.5, 5.0) * (1.7 if explode else 1.0) + Vector3(0, randf_range(-2.5, 2.5), 0) + rand_ang.call(0.8)
		var limbs = []
		var anim: Dictionary = body.get_meta("anim", {})
		for ln in ([] if anim else ["Rider_ArmL", "Rider_ArmR", "Rider_LegL", "Rider_LegR"]):
			var n = body.find_child(ln, true, false) as Node3D
			if n == null:
				continue
			var right = n.position.z > 0
			var arm = ln.begins_with("Rider_Arm")
			# rest direction shoulder -> wrist / hip -> ankle (model space, see blender/build_riders.py)
			var rest = Vector3(0.3, -0.185, 0.155 if right else -0.155) if arm else (Vector3(0.325, -0.53, 0.04) if right else Vector3(0.005, -0.54, -0.04))
			limbs.append({"node": n, "kind": "arm" if arm else "leg", "rest_dir": rest})
		var opts := {"radius": 0.42 * root.scale.x, "lie_radius": 0.24 * root.scale.x, "life": 4.6, "stars": true, "limbs": limbs, "gravity": HANG}
		if anim:   # rigged: the skeleton flails and lands as a starfish (RiderAnim), the debris only flies and rolls him over
			RiderAnim.knocked(anim)
			opts.on_land = RiderAnim.landed.bind(anim)
		effects.add_debris(body, center, vel, spin, opts)
	if r.boombox:
		var bb: Node3D = r.boombox
		effects.add_debris(bb, bb.global_position, push + Vector3(0, 7, 0), rand_ang.call(10.0), {"radius": 0.25, "life": 3.4})
	if explode:
		for nm in ["Bike_WheelFront", "Bike_WheelRear", "Bike_Handlebar"]:
			var part = (r.bike as Node3D).find_child(nm, true, false) as Node3D
			if part == null:
				continue
			var c = part.global_position
			var out = Vector3(c.x - root.position.x, 0, c.z - root.position.z).normalized() * randf_range(5, 9)
			effects.add_debris(part, c, out + Vector3(0, randf_range(7, 12), 0), rand_ang.call(15.0), {"radius": 0.32, "life": 3.4, "bounce": 0.55})
	(r.blob as Node3D).queue_free()
	var bc = root.position + Vector3(0, 0.45, 0)
	var tumble = fwd * randf_range(-7, 7) + Vector3(0, randf_range(-2, 2), 0)
	effects.add_debris(root, bc, carry * 1.3 + push * 0.3 + Vector3(0, 8 if explode else 2, 0), tumble, {"radius": 0.4, "life": 3.6, "bounce": 0.3})
	Sfx.knock_off()
	for o in list:   # the others get a fright
		if o.id != r.id and not o.anims.is_empty() and (o.root as Node3D).position.distance_to(root.position) < 12.0:
			RiderAnim.react(o.anims[0], "Shock")
	for i in list.size():
		if list[i].id == r.id:
			list.remove_at(i)
			break


# ------------------------------------------------------------ knives

## Telegraph a throw: a red "!" and a warning beep, the knife leaves after `settings.windup` seconds.
## Knock the rider off in time and nothing is thrown.
func start_windup(r: Dictionary, accurate: bool) -> void:
	if r.get("windup", 0.0) > 0.0:
		return
	r.windup = settings.windup
	r.windup_total = settings.windup
	r.windup_accurate = accurate
	r.thrown = true
	r.knife_cooldown = randf_range(3, 5) + settings.windup
	effects.bubble(r.root, Vector3(0, 2.7, 0), "!", true, settings.windup + 0.15)
	Sfx.warn()
	if not r.anims.is_empty():
		RiderAnim.windup(r.anims[0], settings.windup)


func _release_knife(r: Dictionary) -> void:
	r.windup = 0.0
	var thrown := can_throw(r)
	if not r.anims.is_empty():
		RiderAnim.throw(r.anims[0], thrown)
	if not thrown:   # rode out of your aim or behind something while winding up: no throw
		r.thrown = r.attack_point != null
		return
	throw_knife(r, r.get("windup_accurate", true))


func throw_knife(r: Dictionary, accurate: bool) -> void:
	var from: Vector3 = (r.model as Node3D).global_transform * Vector3(0.25, 1.4, -0.25)
	var target = player_eye
	# lead a walking player: where will they be when the knife arrives?
	target += player_vel * clampf(from.distance_to(target) / 12.0, 1.1, 2.2)
	if accurate:
		target += Vector3(randf_range(-0.15, 0.15), randf_range(-0.1, 0.1), 0)
	else:
		target += Vector3(randf_range(-1, 1), randf_range(0.2, 1.4), 0).normalized() * randf_range(1.1, 1.9)
	var T = clampf(from.distance_to(target) / 12.0, 1.1, 2.2)  # a bit slower: time to react
	var vel = (target - from) / T + Vector3(0, 0.5 * Config.GRAVITY * T, 0)
	var mesh: Node3D = _knife_tpl.duplicate()
	add_child(mesh)
	mesh.global_position = from
	mesh.look_at(target, Vector3.UP)
	mesh.rotate_object_local(Vector3.UP, PI / 2)
	knives.append({"mesh": mesh, "vel": vel, "age": 0.0, "spin": randf_range(14, 20)})
	r.thrown = true
	r.knife_cooldown = randf_range(3, 5)
	_throw_cd = throw_gap
	effects.bubble(r.root, Vector3(0, 2.6, 0), Config.THROW_SHOUTS.pick_random(), true, 1.3)
	Sfx.whoosh()


func retaliate() -> void:
	if retaliate_cooldown > 0:
		return
	var cands = list.filter(func(r): return r.alive and r.knife_cooldown <= 0 and r.type != "wheelie" and (r.root as Node3D).position.distance_to(player_eye) < 42 and _may_start_throw(r))
	if cands.is_empty():
		return
	start_windup(cands.pick_random(), randf() < settings.accuracy - 0.05)
	retaliate_cooldown = 1.4 + settings.windup


func raycast_knives(origin: Vector3, dir: Vector3, max_dist := 300.0) -> Array:
	var out = []
	for k in knives:
		var c: Vector3 = (k.mesh as Node3D).global_position - origin
		var tca = c.dot(dir)
		if tca < 0 or tca > max_dist:
			continue
		if c.length_squared() - tca * tca < 0.7 * 0.7:  # generous: knives are meant to be shot down
			out.append({"knife": k, "t": tca})
	out.sort_custom(func(a, b): return a.t < b.t)
	return out


func destroy_knife(k: Dictionary) -> void:
	var mesh: Node3D = k.mesh
	effects.puff(mesh.global_position, Color("fff0c0"), 4, 0.3)
	effects.add_debris(mesh, mesh.global_position, k.vel * -0.3 + Vector3(randf_range(-2, 2), 5, randf_range(-2, 2)),
		Vector3(randf_range(-20, 20), randf_range(-20, 20), 0), {"radius": 0.05, "life": 2.0})
	knives.erase(k)


func _update_knives(dt: float) -> void:
	for i in range(knives.size() - 1, -1, -1):
		var k: Dictionary = knives[i]
		var mesh: Node3D = k.mesh
		k.age += dt
		k.vel.y -= Config.GRAVITY * dt
		var step: Vector3 = k.vel * dt
		if world and k.age > 0.08:   # a wall or tree in the way: the knife clatters off it
			var wh := world.raycast(mesh.global_position, step.normalized(), step.length())
			if not wh.is_empty():
				Sfx.clank()
				effects.puff(wh.position, Color("fff0c0"), 3, 0.25)
				mesh.queue_free()
				knives.remove_at(i)
				continue
		mesh.global_position += step
		mesh.rotate_object_local(Vector3(0, 0, 1), -k.spin * dt)
		if mesh.global_position.distance_to(player_eye) < 0.6:
			var v: Vector3 = k.vel
			mesh.queue_free()
			knives.remove_at(i)
			player_hit.emit(v)
			continue
		var flat_v := Vector3(k.vel.x, 0, k.vel.z).normalized()
		var past: float = (mesh.global_position - player_eye).dot(flat_v)  # > 0 once it flew past the player
		if mesh.global_position.y < 0.05 or k.age > 4 or past > 3.0:
			if past > -1.0:
				Sfx.clank()
			mesh.queue_free()
			knives.remove_at(i)


## Everything that threatens the player right now, for the HUD:
## [{pos, kind ("knife" | "windup"), urgency 0..1}]
func threats() -> Array:
	var out = []
	for k in knives:
		var p: Vector3 = (k.mesh as Node3D).global_position
		out.append({"pos": p, "kind": "knife", "urgency": clampf(1.0 - p.distance_to(player_eye) / 30.0, 0.0, 1.0)})
	for r in list:
		if r.alive and r.get("windup", 0.0) > 0.0:
			var p: Vector3 = (r.model as Node3D).global_transform * Vector3(0.0, 2.2, 0.0)
			out.append({"pos": p, "kind": "windup", "urgency": 1.0 - r.windup / maxf(0.01, r.windup_total)})
	return out


func clear() -> void:
	for r in list:
		r.root.queue_free()
	for k in knives:
		k.mesh.queue_free()
	list.clear()
	knives.clear()
	spawn_timer = 1.0


# ------------------------------------------------------------ boombox

func _make_boombox() -> Node3D:
	var g = Node3D.new()
	var body = StandardMaterial3D.new()
	body.albedo_color = Color("2b2d33")
	body.roughness = 0.4
	var chrome = StandardMaterial3D.new()
	chrome.albedo_color = Color("d8d8d8")
	chrome.metallic = 1.0
	chrome.roughness = 0.15
	var cone = StandardMaterial3D.new()
	cone.albedo_color = Color("111111")
	var neon = StandardMaterial3D.new()
	neon.albedo_color = Color("ff2bd0")
	neon.emission_enabled = true
	neon.emission = Color("ff2bd0")
	neon.emission_energy_multiplier = 3.0
	var box = MeshInstance3D.new()
	var bm = BoxMesh.new()
	bm.size = Vector3(0.34, 0.3, 0.6)
	box.mesh = bm
	box.material_override = body
	g.add_child(box)
	for s in [-1, 1]:
		for z in [-0.16, 0.16]:
			var ring = MeshInstance3D.new()
			var tm = TorusMesh.new()
			tm.inner_radius = 0.085
			tm.outer_radius = 0.115
			ring.mesh = tm
			ring.material_override = chrome
			ring.position = Vector3(s * 0.172, 0, z)
			ring.rotation.z = PI / 2
			var c = MeshInstance3D.new()
			var cm = CylinderMesh.new()
			cm.top_radius = 0.095
			cm.bottom_radius = 0.095
			cm.height = 0.01
			c.mesh = cm
			c.material_override = cone
			c.position = Vector3(s * 0.171, 0, z)
			c.rotation.z = PI / 2
			g.add_child(ring)
			g.add_child(c)
	var strip = MeshInstance3D.new()
	var sm = BoxMesh.new()
	sm.size = Vector3(0.35, 0.03, 0.5)
	strip.mesh = sm
	strip.material_override = neon
	strip.position.y = -0.1
	g.add_child(strip)
	return g
