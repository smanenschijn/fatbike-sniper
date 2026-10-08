class_name World
extends Node3D
## The Dutch square: model, sky, sun, collision for shots, markers and the ice cream on the table.

const SUN_DIR := Vector3(-0.8, 0.5, -0.33)

var eye = Vector3(0, 1.2, 11.55)
var env: Environment
var ijsje: Node3D
var _ijs_init := {}
var ijsje_fall := {}
var _ijs_bits: Array = []


func _ready() -> void:
	_build_environment()
	var square: Node3D = load("res://assets/models/square.glb").instantiate()
	add_child(square)
	var eye_node = square.find_child("PlayerEye", true, false)
	if eye_node:
		eye = (eye_node as Node3D).global_position
	var chair = square.find_child("Player_Chair", true, false)
	if chair:
		chair.queue_free()
	# static collision for shots (trimesh per mesh)
	for mi in square.find_children("*", "MeshInstance3D", true, false):
		var m = mi as MeshInstance3D
		m.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_ON
		if m.get_parent() and m.get_parent().name == "Player_Chair":
			continue
		m.create_trimesh_collision()

	ijsje = load("res://assets/models/ijsje.glb").instantiate()
	add_child(ijsje)
	ijsje.position = Config.B(-0.38, -11.0, 0.755)
	_ijs_init.basis = ijsje.basis
	_ijs_init.parts = []
	for n in ["IJsje_Scoops", "IJsje_Topping"]:
		var p = ijsje.find_child(n, true, false) as Node3D
		if p:
			_ijs_init.parts.append({"node": p, "parent": p.get_parent(), "xf": p.transform})


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

	var sun = DirectionalLight3D.new()
	sun.light_color = Color("ffe2b8")
	sun.light_energy = 2.2
	sun.shadow_enabled = true
	sun.directional_shadow_max_distance = 70.0
	sun.directional_shadow_mode = DirectionalLight3D.SHADOW_PARALLEL_2_SPLITS
	add_child(sun)
	sun.look_at_from_position(SUN_DIR.normalized() * 80.0, Vector3.ZERO, Vector3.UP)


## Nearest world hit along a ray: {"position", "normal"} or {}.
func raycast(origin: Vector3, dir: Vector3, far: float) -> Dictionary:
	var q = PhysicsRayQueryParameters3D.create(origin, origin + dir * far)
	var hit = get_world_3d().direct_space_state.intersect_ray(q)
	if hit.is_empty():
		return {}
	return {"position": hit.position, "normal": hit.normal, "distance": origin.distance_to(hit.position)}


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
