class_name World
extends Node3D
## The square you play on (see Config.MAPS): model, sky, sun, collision for shots, markers and the ice cream on the table.

var eye = Vector3(0, 1.2, 11.55)
var seat = Vector3(0, 1.2, 11.55)   # PlayerEye of the loaded map (eye moves while walking in the adventure)
var env: Environment
var ijsje: Node3D
var parasols: Array = []
var sun: DirectionalLight3D
var _dusk_tween: Tween
var _ijs_init := {}
var ijsje_fall := {}
var _ijs_bits: Array = []


var square: Node3D
var models := {}   # adventure world: frame id -> model (all three squares/streets loaded side by side)


func _ready() -> void:
	_build_environment()
	ijsje = load("res://assets/models/ijsje.glb").instantiate()
	add_child(ijsje)
	ijsje.position = Config.B(-0.38, -11.0, 0.755)
	_ijs_init.basis = ijsje.basis
	_ijs_init.parts = []
	for n in ["IJsje_Scoops", "IJsje_Topping"]:
		var p = ijsje.find_child(n, true, false) as Node3D
		if p:
			_ijs_init.parts.append({"node": p, "parent": p.get_parent(), "xf": p.transform})
	load_map()


## (Re)load the square from Config.MAP: model, collision, the parasols at your table and the sun.
func load_map() -> void:
	_unload()
	square = _instance(Config.MAP.model, Vector3.ZERO)
	_merge_static(square)
	_sit_at(square)
	sun.look_at_from_position((Config.MAP.sun as Vector3).normalized() * 80.0, Vector3.ZERO, Vector3.UP)
	if not ijsje_fall.is_empty():
		reset_ijsje()


func is_adventure() -> bool:
	return not models.is_empty()


## The roller coaster of the square you sit at (Wollahbi), or null.
func coaster() -> Coaster:
	return square.get_meta("coaster") if square and square.has_meta("coaster") else null


## Bullet time slows the coasters down too.
func set_time_scale(ts: float) -> void:
	for m in ([square] if models.is_empty() else models.values()):
		if m and m.has_meta("coaster"):
			(m.get_meta("coaster") as Coaster).time_scale = ts


## The adventure world: 't Pleintje, the streets, the Donutplein and Wollahbi side by side (Config.ADVENTURE.frames),
## with the houses that close off the squares' streets taken away so the walk runs straight through.
func load_adventure() -> void:
	_unload()
	models.pleintje = _instance(Config.MAPS.pleintje.model, Config.AP("pleintje", [0, 0]))
	models.route = _instance("res://assets/models/route.glb", Config.AP("route", [0, 0]))
	models.donut = _instance(Config.MAPS.donut.model, Config.AP("donut", [0, 0]))
	models.wollahbi = _instance(Config.MAPS.wollahbi.model, Config.AP("wollahbi", [0, 0]))
	# 't Pleintje's north street is closed by a row at y = 56; the Donutplein's east road by "Cap_E"
	for n in models.pleintje.find_children("StreetN_*", "Node3D", true, false):
		var gp := (n as Node3D).global_position
		if absf(gp.z + 56.0) < 0.5 and gp.x > -5.5 and gp.x < 5.5:
			n.queue_free()
	# ... and the market road north to Wollahbi by "Cap_N"
	for nm in ["Cap_E", "Cap_N"]:
		var cap = models.donut.find_child(nm, true, false)
		if cap:
			cap.queue_free()
	for m in models.values():
		_merge_static(m)
	square = models.pleintje
	_sit_at(square)
	sun.look_at_from_position((Config.MAPS.pleintje.sun as Vector3).normalized() * 80.0, Vector3.ZERO, Vector3.UP)
	if not ijsje_fall.is_empty():
		reset_ijsje()


## Adventure: make this square the one you sit at (seat, parasols).
func activate(id: String) -> void:
	square = models[id]
	_sit_at(square)


func show_model(id: String, on: bool) -> void:
	if models.has(id):
		(models[id] as Node3D).visible = on


func _unload() -> void:
	for m in models.values():
		remove_child(m)
		m.queue_free()
	if square and not models.values().has(square):
		remove_child(square)
		square.queue_free()
	models.clear()
	square = null


func _instance(path: String, at: Vector3) -> Node3D:
	var m: Node3D = load(path).instantiate()
	m.position = at
	add_child(m)
	var chair = m.find_child("Player_Chair", true, false)
	if chair:
		chair.free()
	# static collision for shots (trimesh per mesh)
	for mi in m.find_children("*", "MeshInstance3D", true, false):
		var mesh = mi as MeshInstance3D
		mesh.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_ON
		mesh.create_trimesh_collision()
	var c := Coaster.from_model(m)
	if c:
		m.set_meta("coaster", c)
	return m


const MERGE_CELL := 32.0


## Fewer draw calls (the web build is limited by them): glue the model's static meshes together per material,
## per MERGE_CELL x MERGE_CELL metres so far-away blocks still get culled. The original MeshInstance3D nodes stay,
## without a mesh, so their collision bodies and names (markers) keep working. Parasols keep their own meshes (they fold).
## Web only for now: the merged blocks lose Godot's automatic LODs, a fair trade in WebGL but untested on the phone apps.
func _merge_static(m: Node3D) -> void:
	if not OS.has_feature("web"):
		return
	var inv := m.global_transform.affine_inverse()
	var groups := {}
	for node in m.find_children("*", "MeshInstance3D", true, false):
		var mi := node as MeshInstance3D
		if mi.mesh == null or mi.skin != null or _keep_separate(mi, m):
			continue
		if range(mi.mesh.get_surface_count()).any(func(si): return mi.mesh.surface_get_primitive_type(si) != Mesh.PRIMITIVE_TRIANGLES):
			continue
		var xf := inv * mi.global_transform
		var cell := Vector2i(floori(xf.origin.x / MERGE_CELL), floori(xf.origin.z / MERGE_CELL))
		for si in mi.mesh.get_surface_count():
			var mat := mi.get_active_material(si)
			var fmt: int = mi.mesh.surface_get_format(si) & (Mesh.ARRAY_FORMAT_TANGENT | Mesh.ARRAY_FORMAT_COLOR | Mesh.ARRAY_FORMAT_TEX_UV | Mesh.ARRAY_FORMAT_TEX_UV2)
			var key := "%d|%d|%d|%d" % [mat.get_instance_id() if mat else 0, cell.x, cell.y, fmt]
			if not groups.has(key):
				groups[key] = {"mat": mat, "parts": []}
			groups[key].parts.append([mi.mesh, si, xf])
		mi.mesh = null
	for g in groups.values():
		var st := SurfaceTool.new()
		for part in g.parts:
			st.append_from(part[0], part[1], part[2])
		var merged := MeshInstance3D.new()
		merged.mesh = st.commit()
		merged.material_override = g.mat
		merged.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_ON
		m.add_child(merged)


func _keep_separate(n: Node, root: Node) -> bool:
	while n and n != root:
		if n.is_queued_for_deletion() or not (n as Node3D).visible or "Parasol" in n.name or n is Coaster:
			return true
		n = n.get_parent()
	return false


func _sit_at(m: Node3D) -> void:
	var eye_node = m.find_child("PlayerEye", true, false)
	if eye_node:
		eye = (eye_node as Node3D).global_position
	seat = eye
	parasols.clear()
	for pn in m.find_children("*Parasol*", "Node3D", true, false):
		if (pn as Node3D).global_position.distance_to(Vector3(eye.x, 0, eye.z)) < 6.0:
			parasols.append(pn)


func _build_environment() -> void:
	var env = Environment.new()
	var sky_mat = ProceduralSkyMaterial.new()
	sky_mat.sky_top_color = Color("4d86c8")
	sky_mat.sky_horizon_color = Color("c9dcef")
	sky_mat.ground_horizon_color = Color("c9dcef")
	sky_mat.ground_bottom_color = Color("6d5a4a")
	sky_mat.sun_angle_max = 20.0
	sky_mat.sun_curve = 0.12
	var sky = Sky.new()
	sky.sky_material = sky_mat
	env.background_mode = Environment.BG_SKY
	env.sky = sky
	env.ambient_light_source = Environment.AMBIENT_SOURCE_SKY
	env.ambient_light_energy = 0.75
	env.reflected_light_source = Environment.REFLECTION_SOURCE_SKY
	env.tonemap_mode = Environment.TONE_MAPPER_ACES
	env.tonemap_exposure = 1.0
	env.glow_enabled = true
	env.glow_intensity = 0.35
	env.glow_hdr_threshold = 1.4
	env.fog_enabled = true
	env.fog_light_color = Color("cfe0ee")
	env.fog_density = 0.0035
	env.fog_sky_affect = 0.0
	self.env = env
	var we = WorldEnvironment.new()
	we.environment = env
	add_child(we)

	sun = DirectionalLight3D.new()
	sun.light_color = Color("ffe2b8")
	sun.light_energy = 2.2
	sun.shadow_enabled = true
	sun.directional_shadow_max_distance = 70.0
	sun.directional_shadow_mode = DirectionalLight3D.SHADOW_PARALLEL_2_SPLITS
	add_child(sun)


## Nearest world hit along a ray: {"position", "normal"} or {}.
func raycast(origin: Vector3, dir: Vector3, far: float) -> Dictionary:
	var q = PhysicsRayQueryParameters3D.create(origin, origin + dir * far)
	var hit = get_world_3d().direct_space_state.intersect_ray(q)
	if hit.is_empty():
		return {}
	return {"position": hit.position, "normal": hit.normal, "distance": origin.distance_to(hit.position)}


## The waiter folds the terrace parasols so you can look up at the boss (and opens them again later).
func fold_parasol(folded: bool) -> void:
	var target = Vector3(0.1, 1.0, 0.1) if folded else Vector3.ONE
	for p in parasols:
		if (p as Node3D).scale.is_equal_approx(target):
			continue
		create_tween().tween_property(p, "scale", target, 0.6).set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_IN if folded else Tween.EASE_OUT)


## Evening falls for the fireworks show (and lifts again for the next round).
func set_dusk(on: bool, secs := 1.5) -> void:
	if _dusk_tween:
		_dusk_tween.kill()
	_dusk_tween = create_tween().set_parallel()
	_dusk_tween.tween_property(env, "background_energy_multiplier", 0.18 if on else 1.0, secs)
	_dusk_tween.tween_property(env, "ambient_light_energy", 0.3 if on else 0.75, secs)
	_dusk_tween.tween_property(sun, "light_energy", 0.35 if on else 2.2, secs)
	_dusk_tween.tween_property(env, "fog_light_color", Color("1c2238") if on else Color("cfe0ee"), secs)


## Adventure mode: carry the ice cream in your left hand while walking (holder = the camera), or put it back
## on your table (holder = null).
func hold_ijsje(holder: Node3D) -> void:
	if holder:
		if ijsje.get_parent() != holder:
			ijsje.reparent(holder, false)
		ijsje.position = Vector3(-0.33, -0.36, -0.62)
	else:
		if ijsje.get_parent() != self:
			ijsje.reparent(self, false)
		ijsje.position = seat + Vector3(-0.38, -0.445, -0.55)   # on your table
	ijsje.basis = _ijs_init.basis.scaled(Vector3.ONE * (0.7 if holder else 1.0))


func knock_over_ijsje(from_dir: Vector3) -> void:
	if not ijsje_fall.is_empty():
		return
	var axis = Vector3(from_dir.z, 0, -from_dir.x).normalized()
	if axis.length() < 0.1:
		axis = Vector3.RIGHT
	ijsje_fall = {"t": 0.0, "axis": axis, "basis": ijsje.basis}
	_ijs_bits.clear()
	for p in _ijs_init.parts:
		var n: Node3D = p.node
		n.reparent(self, true)
		_ijs_bits.append({"node": n, "vel": Vector3(from_dir.x * 1.2 + randf_range(-0.5, 0.5), randf_range(2, 3), from_dir.z * 1.2 + randf_range(-0.5, 0.5)),
			"spin": Vector3(randf() * 8, randf() * 8, randf() * 8)})


func reset_ijsje() -> void:
	ijsje.basis = _ijs_init.basis
	for p in _ijs_init.parts:
		var n: Node3D = p.node
		if n.get_parent() != p.parent:
			n.reparent(p.parent, false)
		n.transform = p.xf
	ijsje_fall = {}
	_ijs_bits.clear()


func _process(dt: float) -> void:
	if ijsje_fall.is_empty():
		return
	var f = ijsje_fall
	f.t = minf(1.0, f.t + dt * 3.0)
	ijsje.basis = Basis(f.axis, PI / 2.0 * _ease_out_bounce(f.t)) * f.basis
	for b in _ijs_bits:
		var n: Node3D = b.node
		if n.position.y <= 0.02 and b.vel.y <= 0:
			continue
		b.vel.y -= 9.8 * dt
		n.position += b.vel * dt
		n.rotation += b.spin * dt
		if n.position.y < 0.02:
			n.position.y = 0.02
			b.vel = Vector3.ZERO


static func _ease_out_bounce(x: float) -> float:
	var n1 = 7.5625
	var d1 = 2.75
	if x < 1.0 / d1:
		return n1 * x * x
	if x < 2.0 / d1:
		x -= 1.5 / d1
		return n1 * x * x + 0.75
	if x < 2.5 / d1:
		x -= 2.25 / d1
		return n1 * x * x + 0.9375
	x -= 2.625 / d1
	return n1 * x * x + 0.984375
