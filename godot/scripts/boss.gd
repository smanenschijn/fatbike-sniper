class_name Fatbiketron
extends Node3D
## FATBIKETRON, the end boss after the round timer.
## Intro: five giant riderless fatbikes ride in, circle, leap up and burst into the robot's parts.
## Fight: procedural animation (stomping walk, breathing, aiming), six shootable parts (every limb's bike
## falls off, the head can only be hit when all five bikes are gone), rockets and thrown tyres that can
## be shot out of the air.

signal player_hit(vel: Vector3, reason: String)

const SPOT := Vector3(-6.0, 0, -10.0)
const AREA_X := Vector2(5.0, 8.5)      # stays beside the fountain (|x| between these)
const AREA_Z := Vector2(-11.5, -8.5)
const MODEL_SCALE := 1.3
const BIKE_SCALE := 2.2
const BIKES := ["LegL", "LegR", "Torso", "ArmL", "ArmR"]
const PARTS := ["LegL", "LegR", "Torso", "ArmL", "ArmR", "Head"]
const PART_NAMES := {"LegL": "LINKERBEEN", "LegR": "RECHTERBEEN", "Torso": "ROMP", "ArmL": "LINKERARM", "ArmR": "RAKETARM", "Head": "HOOFD"}
const BAR_NAMES := {"LegL": "BEEN L", "LegR": "BEEN R", "Torso": "ROMP", "ArmL": "ARM L", "ArmR": "RAKETARM", "Head": "HOOFD"}
const TEAM := {"LegL": ["#1d2f55", "#7cff6b"], "LegR": ["#7a1820", "#f2f2f2"], "Torso": ["#24262b", "#ff7a1a"],
	"ArmL": ["#243f2d", "#ffd23f"], "ArmR": ["#c9c9cf", "#ff3b6b"], "Head": ["#1f2227", "#e63946"]}
const ENTRY_FOR := {"LegL": "east", "LegR": "west", "Torso": "north", "ArmL": "alleyE", "ArmR": "alleyNW"}
const HP := {"bike": 14.0, "Head": 22.0}
const SHOUTS := ["IK BEN FATBIKETRON!", "HET PLEIN IS VAN ONS!", "TRING TRING, STERVELING!", "GEEF DAT IJSJE!",
	"FIETSPAD? IK BEN HET FIETSPAD!", "25 KM/U IS VOOR WATJES!"]
const PAIN := ["MIJN ACCU!", "AU, MIJN SPATBORD!", "WIE SLOOPT MIJN STUUR?!", "DIT IS GARANTIE!", "KRAS OP MIJN LAK!"]
const RAGE := ["NU BEN IK BOOS!", "ZONDER FIETSEN BEN IK NOG STEEDS GROOT!", "IK HEB GEEN TRAPONDERSTEUNING NODIG!"]

# Hit capsules in the local space of a pivot node: [node, a, b, radius, part]. s = +1 left (-Z), -1 right (+Z).
static func _capsules() -> Array:
	var out = []
	for side in ["L", "R"]:
		var s = 1.0 if side == "L" else -1.0
		out.append(["Boss_Leg%s_Pivot" % side, Vector3.ZERO, Vector3(0.85, -1.8, -s * 0.6), 0.8, "Leg" + side])
		out.append(["Boss_Knee" + side, Vector3(0.05, 0.1, 0), Vector3(-0.4, -1.69, -s * 0.4), 0.85, "Leg" + side])
		out.append(["Boss_Knee" + side, Vector3(-1.25, -1.75, -s * 0.4), Vector3(0.65, -1.75, -s * 0.4), 0.7, "Leg" + side])
		out.append(["Boss_Arm%s_Pivot" % side, Vector3(-0.05, 0.6, -s * 0.45), Vector3(0.1, -2.0, -s * 0.8), 0.9, "Arm" + side])
		out.append(["Boss_Elbow" + side, Vector3.ZERO, Vector3(0.75, -2.6, -s * 0.25), 0.65, "Arm" + side])
	out.append(["Boss_ElbowR", Vector3(0.3, -0.2, 0.3), Vector3(1.3, -1.8, 0.5), 0.6, "ArmR"])
	out.append(["Boss_ElbowL", Vector3(0.15, -0.85, -0.55), Vector3(0.45, -0.85, -0.55), 0.75, "ArmL"])
	out.append(["Boss_Spine", Vector3(0.3, 0.9, 0), Vector3(0.2, 2.9, 0), 1.35, "Torso"])
	out.append(["Boss_Hips", Vector3(0, 0, -0.7), Vector3(0, 0, 0.7), 0.6, "Torso"])
	out.append(["Boss_Neck", Vector3(0.4, 0.3, 0), Vector3(0.2, 1.2, 0), 0.85, "Head"])
	return out

var game  # Game (untyped: Game also refers to us)
var riders: Riders
var effects: Effects
var player_eye := Vector3.ZERO
var settings := {"accuracy": 0.6, "windup": 0.75, "hp": 1.0, "speed": 1.0}

var state := "hidden"  # hidden | intro | fight | dying | dead
var model: Node3D
var n := {}            # pivot / mesh nodes by name
var rest := {}         # rest transforms of the pivots
var parts := {}        # part -> {hp, max, alive, meshes: [MeshInstance3D]}
var caps: Array = []
var projectiles: Array = []
var head_open := false
var rage := false

var _scene: PackedScene
var _lib: Node3D
var _rocket_tpl: Node3D
var _flash_mat: StandardMaterial3D
var _flash := {}       # part -> seconds left
var _t := 0.0
var _shout_t := 4.0
var _pain_t := 0.0
var _tip_t := 0.0

# movement / animation
var _yaw := 0.0
var _target := SPOT
var _move_t := 0.0
var _phase := 0.0
var _moving := false
var _lift := {"L": 0.0, "R": 0.0}
var _aim := 0.0         # right arm raised at the player (0..1)
var _throw := 0.0       # left arm angle for the tyre throw (radians, forward/up)
var _elbow_l := 0.0
var _flinch := 0.0
var _stagger := 0.0
var _kneel := 0.0
var _attack := {}
var _attack_cd := 3.0
var _held_tyre: Node3D = null

# intro
var _intro := {}
var _bikes: Array = []
var _assembly: Array = []
var cam_focus := SPOT + Vector3(0, 3, 0)

# dying
var _die := {}


func setup(g, r: Riders, fx: Effects, eye: Vector3) -> void:
	game = g
	riders = r
	effects = fx
	player_eye = eye
	_scene = load("res://assets/models/boss.glb")
	_flash_mat = StandardMaterial3D.new()
	_flash_mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	_flash_mat.albedo_color = Color(1, 0.95, 0.85, 0.55)
	_flash_mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	_flash_mat.blend_mode = BaseMaterial3D.BLEND_MODE_ADD
	_build_model()


## A fresh robot every fight (shot-off parts end up as debris and get freed).
func _build_model() -> void:
	if _lib:
		_lib.queue_free()
	_lib = _scene.instantiate()
	add_child(_lib)
	model = _lib.find_child("Boss", true, false)
	model.scale = Vector3.ONE * MODEL_SCALE
	_rocket_tpl = _lib.find_child("Boss_Rocket", true, false)
	_rocket_tpl.visible = false
	n.clear()
	rest.clear()
	caps.clear()
	for c in model.find_children("*", "Node3D", true, false):
		n[String(c.name)] = c
	for k in ["Boss_Hips", "Boss_LegL_Pivot", "Boss_KneeL", "Boss_LegR_Pivot", "Boss_KneeR", "Boss_Spine",
			"Boss_ArmL_Pivot", "Boss_ElbowL", "Boss_ArmR_Pivot", "Boss_ElbowR", "Boss_Neck"]:
		rest[k] = (n[k] as Node3D).transform
	for c in _capsules():
		caps.append({"node": n[c[0]], "a": c[1], "b": c[2], "r": c[3], "part": c[4]})
	for mi in model.find_children("*", "MeshInstance3D", true, false):
		(mi as GeometryInstance3D).cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_ON
		mi.set_meta("home", mi.transform)
	model.visible = false


# ------------------------------------------------------------ lifecycle

func reset() -> void:
	state = "hidden"
	for p in projectiles:
		p.node.queue_free()
	projectiles.clear()
	for b in _bikes:
		if is_instance_valid(b.node):
			b.node.queue_free()
	_bikes.clear()
	_assembly.clear()
	_held_tyre = null
	_build_model()
	parts.clear()
	for k in PARTS:
		var mx: float = (HP.Head if k == "Head" else HP.bike) * settings.hp
		parts[k] = {"hp": mx, "max": mx, "alive": true, "meshes": _meshes_for(k)}
	parts["Skeleton"] = {"hp": 0.0, "max": 0.0, "alive": true, "meshes": _skeleton_meshes()}
	head_open = false
	rage = false
	_attack = {}
	_attack_cd = 3.5
	_aim = 0.0
	_throw = 0.0
	_elbow_l = 0.0
	_kneel = 0.0
	_stagger = 0.0
	_flinch = 0.0
	_lift = {"L": 0.0, "R": 0.0}
	_flash.clear()
	_die = {}
	_intro = {}
	var to_player = player_eye - SPOT
	_yaw = atan2(-to_player.z, to_player.x)
	model.position = SPOT
	model.rotation = Vector3(0, _yaw, 0)
	_target = SPOT
	_eye_glow(1.0)


func _meshes_for(part: String) -> Array:
	var out = []
	for k in n:
		var node = n[k]
		if not node is MeshInstance3D:
			continue
		if part == "Head" and (k == "Boss_Head" or k == "Boss_Hair"):
			out.append(node)
		elif k.begins_with("Boss_Bike_" + part):
			out.append(node)
	return out


func _skeleton_meshes() -> Array:
	var out = []
	for k in n:
		var node = n[k]
		if node is MeshInstance3D and not k.begins_with("Boss_Bike_") and k != "Boss_Head" and k != "Boss_Hair":
			out.append(node)
	return out


func bikes_left() -> int:
	return BIKES.filter(func(k): return parts[k].alive).size()


func total_hp() -> float:
	var t = 0.0
	for k in PARTS:
		t += parts[k].hp
	return t


func total_max() -> float:
	var t = 0.0
	for k in PARTS:
		t += parts[k].max
	return t


## For the HUD boss bar: [{name, frac, color, alive, locked}]
func bar_state() -> Array:
	var out = []
	for k in PARTS:
		var p: Dictionary = parts[k]
		out.append({"name": BAR_NAMES[k], "frac": p.hp / p.max, "color": Color(TEAM[k][1]), "alive": p.alive,
			"locked": k == "Head" and not head_open})
	return out


# ------------------------------------------------------------ intro

func start_intro() -> void:
	reset()
	state = "intro"
	_intro = {"t": 0.0, "stage": "wait", "rumbled": false, "assembled": 0}
	cam_focus = SPOT + Vector3(0, 3, 0)
	var i = 0
	for k in BIKES:
		var entry: Dictionary = Config.ENTRIES.filter(func(e): return e.name == ENTRY_FOR[k])[0]
		var col: Array = TEAM[k]
		var bike: Node3D = riders.make_bike(col[0], col[1])
		bike.scale = Vector3.ONE * BIKE_SCALE
		add_child(bike)
		bike.visible = false
		var a = PI / 2 + (i - 2) * 0.62  # gather on an arc in front of the spot
		var gather = SPOT + Vector3(cos(a) * 6.0, 0, sin(a) * 6.0)
		var pts: Array[Vector3] = [entry.spawn, entry.mouth, gather]
		_bikes.append({"part": k, "node": bike, "pts": pts, "d": 0.0, "start": 2.4 + i * 0.35, "speed": 21.0,
			"arrived": false, "ang": a, "R": 6.0, "revved": false})
		i += 1


func skip_intro() -> void:
	if state != "intro" or _intro.stage == "card":
		return
	for b in _bikes:
		b.node.queue_free()
	_bikes.clear()
	_assembly.clear()
	model.visible = true
	for k in parts:
		for mi in parts[k].meshes:
			mi.transform = mi.get_meta("home")
			mi.visible = true
	_intro.stage = "card"
	_intro.t = 0.0
	_intro.card_shown = false


func _path_point(pts: Array, d: float) -> Dictionary:
	for i in pts.size() - 1:
		var seg: float = pts[i].distance_to(pts[i + 1])
		if d <= seg or i == pts.size() - 2:
			var k = clampf(d / seg, 0, 1)
			return {"pos": pts[i].lerp(pts[i + 1], k), "dir": (pts[i + 1] - pts[i]).normalized(), "done": d >= seg and i == pts.size() - 2}
		d -= seg
	return {"pos": pts[-1], "dir": Vector3.FORWARD, "done": true}


func _face(node: Node3D, dir: Vector3) -> void:
	node.rotation.y = atan2(-dir.z, dir.x)


func _step_intro(dt: float) -> void:
	_intro.t += dt
	var t: float = _intro.t
	match _intro.stage:
		"wait", "ride":
			if t > 1.4 and not _intro.rumbled:
				_intro.rumbled = true
				Sfx.rumble()
				effects.add_shake(0.35)
				effects.popup_screen("WAT IS DAT GELUID?!", "", 0.5, 0.3, 1.8)
			var all_in = true
			for b in _bikes:
				if t < b.start:
					all_in = false
					continue
				var node: Node3D = b.node
				if not node.visible:
					node.visible = true
					Sfx.rev()
				if not b.arrived:
					b.d += b.speed * dt
					var pp = _path_point(b.pts, b.d)
					node.position = pp.pos
					_face(node, pp.dir)
					_spin_wheels(node, b.speed * dt)
					if pp.done:
						b.arrived = true
						effects.puff(node.position, Color("b9a98f"), 4, 1.2)
					all_in = false if not pp.done else all_in
			cam_focus = SPOT + Vector3(0, 1.5, 0)
			if all_in and t > 3.0:
				_intro.stage = "circle"
				_intro.t = 0.0
				Sfx.rev()
		"circle":
			for b in _bikes:
				b.ang += dt * 2.2
				b.R = lerpf(6.0, 5.0, minf(1.0, t / 1.4))
				var node: Node3D = b.node
				node.position = SPOT + Vector3(cos(b.ang) * b.R, 0, sin(b.ang) * b.R)
				_face(node, Vector3(-sin(b.ang), 0, cos(b.ang)))
				node.rotation.x = -0.35
				_spin_wheels(node, 14.0 * dt)
			if fmod(t, 0.5) < dt:
				effects.puff(SPOT + Vector3(randf_range(-4, 4), 0.2, randf_range(-4, 4)), Color("b9a98f"), 3, 1.5)
			if t > 1.5:
				_start_leap()
		"leap":
			_step_leap(dt)
		"card":
			cam_focus = cam_focus.lerp(model.position + Vector3(0, 6.5, 0), minf(1.0, dt * 2.5))
			if not _intro.get("card_shown", false):
				_intro.card_shown = true
				_eye_glow(4.0)
				Sfx.roar()
				effects.add_shake(1.1)
				game.boss_card()
				effects.bubble(n.Boss_Neck, Vector3(0, 3.2, 0), "HET PLEIN IS VAN ONS!", true, 2.6)
			_eye_glow(lerpf(4.0, 1.0, minf(1.0, t / 2.0)))
			if t > 3.2:
				state = "fight"
				game.boss_fight_start()


func _spin_wheels(bike: Node3D, dist: float) -> void:
	for wn in ["Bike_WheelFront", "Bike_WheelRear"]:
		var w = bike.find_child(wn, true, false) as Node3D
		if w:
			w.rotate_object_local(Vector3(0, 0, 1), -dist / (0.33 * BIKE_SCALE))


func _start_leap() -> void:
	_intro.stage = "leap"
	_intro.t = 0.0
	model.visible = true
	Sfx.transform()
	# skeleton grows out of the ground, bike parts and head wait for their bike
	for k in parts:
		for mi in parts[k].meshes:
			(mi as Node3D).visible = k == "Skeleton"
	for mi in parts.Skeleton.meshes:
		_assembly.append({"node": mi, "t": 0.0, "dur": 0.7, "delay": randf() * 0.25, "from": SPOT + Vector3(0, -1, 0), "grow": true})
	var order = ["LegL", "LegR", "Torso", "ArmL", "ArmR"]
	for i in _bikes.size():
		var b: Dictionary = _bikes[i]
		b.leap_t = -0.5 - order.find(b.part) * 0.38
		b.from = (b.node as Node3D).position
		b.to = _part_center(b.part)
		b.burst = false


func _step_leap(dt: float) -> void:
	var t: float = _intro.t
	cam_focus = cam_focus.lerp(SPOT + Vector3(0, 5.5, 0), minf(1.0, dt * 2.0))
	for b in _bikes:
		if b.burst:
			continue
		b.leap_t += dt
		var node: Node3D = b.node
		if b.leap_t < 0:
			continue
		var k = minf(1.0, b.leap_t / 0.7)
		var p: Vector3 = (b.from as Vector3).lerp(b.to, k)
		p.y += sin(k * PI) * 3.0
		node.position = p
		node.rotation += Vector3(dt * 9.0, dt * 4.0, dt * 6.0)
		if k >= 1.0:
			b.burst = true
			node.visible = false
			effects.puff(p, Color("fff0c0"), 8, 1.4)
			effects.flash_light(p, Color("ffd27a"), 8.0, 0.25, 20.0)
			effects.add_shake(0.35)
			Sfx.clank_heavy()
			for mi in parts[b.part].meshes:
				mi.visible = true
				_assembly.append({"node": mi, "t": 0.0, "dur": 0.45, "delay": randf() * 0.1, "from": p})
			_intro.assembled += 1
	_step_assembly(dt)
	if _intro.assembled == BIKES.size() and not _intro.has("head_t"):
		_intro.head_t = 0.0
	if _intro.has("head_t"):
		_intro.head_t += dt
		if _intro.head_t > 0.5 and not _intro.get("head_dropped", false):
			_intro.head_dropped = true
			for mi in parts.Head.meshes:
				mi.visible = true
				_assembly.append({"node": mi, "t": 0.0, "dur": 0.5, "delay": 0.0, "from": _head_pos() + Vector3(0, 7, 0), "no_spin": true})
		if _intro.head_t > 1.15 and _assembly.is_empty():
			Sfx.clank_heavy()
			effects.add_shake(0.6)
			for b in _bikes:
				b.node.queue_free()
			_bikes.clear()
			_intro.stage = "card"
			_intro.t = 0.0


## Parts fly from where their bike burst to their place on the robot.
func _step_assembly(dt: float) -> void:
	for i in range(_assembly.size() - 1, -1, -1):
		var a: Dictionary = _assembly[i]
		var mi: MeshInstance3D = a.node
		if a.delay > 0:
			a.delay -= dt
			mi.scale = Vector3.ONE * 0.001
			continue
		a.t += dt
		var k = minf(1.0, a.t / a.dur)
		var e = 1.0 + 2.2 * pow(k - 1.0, 3) + 1.2 * pow(k - 1.0, 2)  # ease out back
		var parent: Node3D = mi.get_parent()
		var from_local: Vector3 = parent.global_transform.affine_inverse() * (a.from as Vector3)
		var xf: Transform3D = mi.get_meta("home")
		if a.get("grow", false):
			mi.transform = xf
			mi.scale = Vector3.ONE * maxf(0.001, e)
		else:
			var spin = Basis.IDENTITY if a.get("no_spin", false) else Basis(Vector3(1, 0.4, 0.2).normalized(), (1.0 - k) * 5.0)
			mi.transform = Transform3D(spin * xf.basis, from_local.lerp(xf.origin, e))
			mi.scale = xf.basis.get_scale() * lerpf(0.35, 1.0, minf(1.0, k * 1.5))
		if k >= 1.0:
			mi.transform = xf
			_assembly.remove_at(i)


func _part_center(part: String) -> Vector3:
	var pts = []
	for c in caps:
		if c.part == part:
			pts.append((c.node as Node3D).global_transform * ((c.a + c.b) * 0.5))
	var s = Vector3.ZERO
	for p in pts:
		s += p
	return s / maxf(1, pts.size())


func _head_pos() -> Vector3:
	return (n.Boss_Neck as Node3D).global_transform * Vector3(0.3, 0.7, 0)


func _eye_glow(mult: float) -> void:
	var head: MeshInstance3D = n.Boss_Head
	for s in head.mesh.get_surface_count():
		var m = head.mesh.surface_get_material(s)
		if m and m.resource_name == "BossEye" and m is StandardMaterial3D:
			if not m.has_meta("e0"):
				m.set_meta("e0", (m as StandardMaterial3D).emission_energy_multiplier)
			(m as StandardMaterial3D).emission_energy_multiplier = m.get_meta("e0") * mult


# ------------------------------------------------------------ update

func step(dt: float) -> void:
	if state == "hidden" or state == "dead":
		_update_projectiles(dt)
		return
	_t += dt
	for k in _flash.keys():
		_flash[k] -= dt
		if _flash[k] <= 0:
			_flash.erase(k)
			for mi in parts[k].meshes:
				if is_instance_valid(mi):
					mi.material_overlay = null
	if state == "intro":
		_step_intro(dt)
		_pose(dt)
		return
	if state == "dying":
		_step_dying(dt)
		_pose(dt)
		_update_projectiles(dt)
		return
	_step_fight(dt)
	_pose(dt)
	_update_projectiles(dt)


func _step_fight(dt: float) -> void:
	var speed_mul: float = settings.speed * (1.35 if rage else 1.0)
	# shouting
	_shout_t -= dt
	_pain_t -= dt
	_tip_t -= dt
	if _shout_t <= 0:
		_shout_t = randf_range(6, 10)
		effects.bubble(n.Boss_Neck, Vector3(0, 3.2, 0), (RAGE if rage else SHOUTS).pick_random(), false, 2.2)
	# movement: lumber to a new spot now and then, not while attacking
	_move_t -= dt
	if _move_t <= 0 and _attack.is_empty():
		_move_t = randf_range(3.5, 6.0)
		var side = signf(model.position.x) if randf() < 0.45 else -signf(model.position.x)
		_target = Vector3(side * randf_range(AREA_X.x, AREA_X.y), 0, randf_range(AREA_Z.x, AREA_Z.y))
	var to = _target - model.position
	to.y = 0
	_moving = to.length() > 0.3 and _attack.get("kind", "") != "rocket"
	if _moving:
		_phase += dt * 2.6 * speed_mul
		var lifted = maxf(_lift.L, _lift.R)
		model.position += to.normalized() * minf(to.length(), dt * 2.3 * speed_mul * (0.4 + lifted))
	elif _lift.L > 0.02 or _lift.R > 0.02:
		_phase += dt * 2.6  # finish the step
	var s = sin(_phase)
	var new_l = maxf(0.0, s) if _moving or _lift.L > 0.02 else 0.0
	var new_r = maxf(0.0, -s) if _moving or _lift.R > 0.02 else 0.0
	for side in ["L", "R"]:
		var nv = new_l if side == "L" else new_r
		if _lift[side] > 0.05 and nv <= 0.0:
			_stomp(side)
		_lift[side] = nv
	# face the player
	var d = player_eye - model.position
	var want = atan2(-d.z, d.x)
	_yaw = lerp_angle(_yaw, want, minf(1.0, dt * 2.0))
	model.rotation.y = _yaw
	# attacks
	_step_attack(dt, speed_mul)


func _stomp(side: String) -> void:
	var foot: Vector3 = (n["Boss_Knee" + side] as Node3D).global_transform * Vector3(-0.3, -1.9, 0)
	foot.y = 0.1
	effects.puff(foot, Color("9a8a78"), 5, 1.4)
	var dist = foot.distance_to(player_eye)
	effects.add_shake(clampf(9.0 / dist, 0.1, 0.45))
	Sfx.stomp(dist)


# ------------------------------------------------------------ attacks

func _step_attack(dt: float, speed_mul: float) -> void:
	if _attack.is_empty():
		_attack_cd -= dt * speed_mul
		_aim = move_toward(_aim, 0.0, dt * 1.6)
		_throw = move_toward(_throw, 0.0, dt * 2.5)
		_elbow_l = move_toward(_elbow_l, 0.0, dt * 2.5)
		if _attack_cd <= 0:
			var kind = "rocket" if randf() < 0.62 else "tyre"
			_attack = {"kind": kind, "stage": "raise", "t": 0.0, "fired": 0}
			var broken = 5 - bikes_left()
			_attack.count = 1 + int(broken >= 2) + int(broken >= 4) + int(rage)
		return
	var a := _attack
	a.t += dt
	var windup: float = settings.windup
	if a.kind == "rocket":
		match a.stage:
			"raise":
				_aim = minf(1.0, a.t / 0.6)
				if a.t >= 0.6:
					_next_stage("windup")
					effects.bubble(n.Boss_ElbowR, Vector3(0.8, 0.3, 0.4), "!", true, windup * 1.3 + 0.3)
					Sfx.warn()
			"windup":
				if a.t >= windup * 1.3 + 0.2:
					_next_stage("fire")
			"fire":
				if a.t >= 0.32 * a.fired:
					_fire_rocket(a.fired)
					a.fired += 1
					if a.fired >= a.count:
						_next_stage("recover")
			"recover":
				_aim = maxf(0.0, 1.0 - a.t / 0.8)
				if a.t >= 0.8:
					_end_attack()
	else:
		match a.stage:
			"raise":  # reach up into the broccoli
				_throw = lerpf(0.0, 2.75, minf(1.0, a.t / 0.6))
				_elbow_l = lerpf(0.0, 1.2, minf(1.0, a.t / 0.6))
				if a.t >= 0.6:
					_grab_tyre()
					_next_stage("windup")
					effects.bubble(n.Boss_ElbowL, Vector3(0.5, -2.2, 0), "!", true, windup + 0.35)
					Sfx.warn()
			"windup":
				_throw = 2.75 + sin(a.t * 10.0) * 0.05
				if a.t >= windup + 0.2:
					_next_stage("throw")
			"throw":
				var k = minf(1.0, a.t / 0.22)
				_throw = lerpf(2.75, 0.9, k)
				_elbow_l = lerpf(1.2, 0.1, k)
				if k >= 0.6 and _held_tyre:
					_release_tyre()
				if a.t >= 0.22:
					_next_stage("recover")
			"recover":
				if a.t >= 0.6:
					_end_attack()


func _next_stage(s: String) -> void:
	_attack.stage = s
	_attack.t = 0.0


func _end_attack() -> void:
	_attack = {}
	var base = randf_range(2.6, 4.2) - (5 - bikes_left()) * 0.25
	_attack_cd = maxf(1.2, base * (0.6 if rage else 1.0))


func _muzzle(i: int) -> Vector3:
	return (n["Boss_Muzzle_%d" % (i % 6)] as Node3D).global_position


func _fire_rocket(i: int) -> void:
	var from = _muzzle(i * 2 + randi() % 2)
	var shoulder: Vector3 = (n.Boss_ArmR_Pivot as Node3D).global_position
	var accurate = randf() < settings.accuracy + 0.15
	var target = player_eye + Vector3(randf_range(-0.2, 0.2), randf_range(-0.1, 0.2), 0)
	if not accurate:
		target += Vector3(randf_range(-1, 1), randf_range(-0.2, 1.0), 0).normalized() * randf_range(2.2, 3.5)
	var node: Node3D = _rocket_tpl.duplicate()
	node.visible = true
	node.scale = Vector3.ONE * 1.5
	add_child(node)
	node.global_position = from
	var dir = (from - shoulder).normalized()
	var spd = 11.0 * settings.speed * (1.15 if rage else 1.0)
	projectiles.append({"kind": "rocket", "node": node, "vel": dir * spd, "speed": spd, "target": target, "age": 0.0,
		"trail": 0.0, "accurate": accurate})
	effects.puff(from, Color("dddddd"), 5, 0.8)
	effects.flash_light(from, Color("ffaa55"), 6.0, 0.12, 15.0)
	Sfx.rocket()


func _grab_tyre() -> void:
	var t = Node3D.new()
	var tyre = MeshInstance3D.new()
	var tm = TorusMesh.new()
	tm.inner_radius = 0.2
	tm.outer_radius = 0.45
	tyre.mesh = tm
	var rubber = StandardMaterial3D.new()
	rubber.albedo_color = Color("1a1a1a")
	rubber.roughness = 0.9
	tyre.material_override = rubber
	tyre.rotation.x = PI / 2
	t.add_child(tyre)
	var rim = MeshInstance3D.new()
	var cm = CylinderMesh.new()
	cm.top_radius = 0.24
	cm.bottom_radius = 0.24
	cm.height = 0.14
	rim.mesh = cm
	var rm = StandardMaterial3D.new()
	rm.albedo_color = Color(TEAM[BIKES.pick_random()][1])
	rm.roughness = 0.35
	rim.material_override = rm
	rim.rotation.x = PI / 2
	t.add_child(rim)
	(n.Boss_ElbowL as Node3D).add_child(t)
	t.position = Vector3(0.75, -2.4, -0.25)
	_held_tyre = t
	effects.puff(_head_pos() + Vector3(0, 0.6, 0), Color("333333"), 3, 0.6)


func _release_tyre() -> void:
	var t := _held_tyre
	_held_tyre = null
	var from = t.global_position
	t.reparent(self, true)
	var accurate = randf() < settings.accuracy + 0.1
	var target = player_eye + Vector3(randf_range(-0.15, 0.15), randf_range(-0.1, 0.1), 0)
	if not accurate:
		target += Vector3(randf_range(-1, 1), randf_range(0.3, 1.2), 0).normalized() * randf_range(1.8, 2.8)
	var T = clampf(from.distance_to(target) / 13.0, 1.5, 2.3)
	var vel = (target - from) / T + Vector3(0, 0.5 * Config.GRAVITY * T, 0)
	projectiles.append({"kind": "tyre", "node": t, "vel": vel, "age": 0.0, "spin": randf_range(8, 12), "accurate": accurate, "bounced": false})
	Sfx.whoosh()


func _update_projectiles(dt: float) -> void:
	for i in range(projectiles.size() - 1, -1, -1):
		var p: Dictionary = projectiles[i]
		var node: Node3D = p.node
		p.age += dt
		var prev = node.global_position
		if p.kind == "rocket":
			var want: Vector3 = ((p.target as Vector3) - prev).normalized() * p.speed
			if prev.distance_to(p.target) > 3.0:
				p.vel = (p.vel as Vector3).lerp(want, minf(1.0, dt * 1.6))
			p.trail -= dt
			if p.trail <= 0:
				p.trail = 0.03
				effects.smoke_trail(prev)
		else:
			p.vel.y -= Config.GRAVITY * dt
			node.rotate_object_local(Vector3(0, 0, 1), -p.spin * dt)
		var next: Vector3 = prev + p.vel * dt
		if p.kind == "rocket":
			node.basis = Basis(Quaternion(Vector3.RIGHT, (p.vel as Vector3).normalized())).scaled(Vector3.ONE * 1.5)
		node.global_position = next
		if next.distance_to(player_eye) < (1.1 if p.kind == "rocket" else 0.8):
			_remove_projectile(i)
			if p.kind == "rocket":
				effects.explosion(player_eye + (prev - player_eye).normalized() * 2.2)
				Sfx.explosion(2.0)
			else:
				Sfx.clank_heavy()
			player_hit.emit(p.vel, "OPGEBLAZEN!" if p.kind == "rocket" else "OMVERGEROLD!")
			continue
		# near the player only the player counts (the terrace furniture would eat every rocket)
		var far = next.distance_to(player_eye) > 3.0
		var wh = game.world.raycast(prev, (next - prev).normalized(), prev.distance_to(next) + 0.1) if far and prev.distance_to(next) > 0.0001 else {}
		var gone = p.age > 7.0 or next.z > player_eye.z + 4.0
		if p.kind == "rocket":
			if not wh.is_empty() or next.y < 0.1 or gone:
				var at: Vector3 = wh.position if not wh.is_empty() else next
				_remove_projectile(i)
				effects.explosion(at)
				Sfx.explosion(at.distance_to(player_eye))
		else:
			if (not wh.is_empty() or next.y < 0.45) and not p.bounced and not gone:
				p.bounced = true
				p.vel = Vector3(p.vel.x * 0.5, absf(p.vel.y) * 0.45, p.vel.z * 0.5)
				node.global_position = Vector3(next.x, maxf(next.y, 0.45), next.z)
				Sfx.clank()
			elif gone or (p.bounced and next.y < 0.3):
				effects.puff(next, Color("8a7a6a"), 3, 0.6)
				_remove_projectile(i)


func _remove_projectile(i: int) -> void:
	projectiles[i].node.queue_free()
	projectiles.remove_at(i)


## Rockets and tyres along a ray (they are meant to be shot down): [{proj, t}]
func raycast_projectiles(origin: Vector3, dir: Vector3, max_dist := 300.0) -> Array:
	var out = []
	for p in projectiles:
		var c: Vector3 = (p.node as Node3D).global_position - origin
		var tca = c.dot(dir)
		if tca < 0 or tca > max_dist:
			continue
		var r = 1.0 if p.kind == "rocket" else 0.85
		if c.length_squared() - tca * tca < r * r:
			out.append({"proj": p, "t": tca})
	out.sort_custom(func(a, b): return a.t < b.t)
	return out


func destroy_projectile(p: Dictionary) -> Vector3:
	var i = projectiles.find(p)
	var pos: Vector3 = (p.node as Node3D).global_position
	if i < 0:
		return pos
	if p.kind == "rocket":
		_remove_projectile(i)
		effects.explosion(pos)
		Sfx.explosion(pos.distance_to(player_eye))
	else:
		var node: Node3D = p.node
		projectiles.remove_at(i)
		effects.add_debris(node, pos, (p.vel as Vector3) * -0.25 + Vector3(randf_range(-2, 2), 6, 0), Vector3(randf() * 10, randf() * 10, 0), {"radius": 0.45, "life": 2.5, "bounce": 0.5})
		Sfx.clank()
	return pos


## Everything that threatens the player, for the HUD markers: [{pos, kind, urgency}]
func threats() -> Array:
	var out = []
	if state != "fight" and state != "dying":
		return out
	for p in projectiles:
		var pos: Vector3 = (p.node as Node3D).global_position
		out.append({"pos": pos, "kind": "knife", "urgency": clampf(1.0 - pos.distance_to(player_eye) / 30.0, 0.0, 1.0)})
	if _attack.get("stage", "") == "windup":
		var total: float = settings.windup * (1.3 if _attack.kind == "rocket" else 1.0) + 0.2
		var pos: Vector3 = _muzzle(0) if _attack.kind == "rocket" else (n.Boss_ElbowL as Node3D).global_transform * Vector3(0.75, -2.4, -0.25)
		out.append({"pos": pos, "kind": "windup", "urgency": clampf(_attack.t / total, 0.0, 1.0)})
	return out


# ------------------------------------------------------------ hit tests / damage

## Nearest hit on the boss along a ray: {part, t, point} or {}.
func raycast(origin: Vector3, dir: Vector3, max_dist := 300.0) -> Dictionary:
	if state != "fight":
		return {}
	var best = {}
	for c in caps:
		var xf: Transform3D = (c.node as Node3D).global_transform
		var t = _ray_capsule(origin, dir, xf * (c.a as Vector3), xf * (c.b as Vector3), c.r * MODEL_SCALE)
		if t >= 0 and t <= max_dist and (best.is_empty() or t < best.t):
			best = {"part": c.part, "t": t}
	if not best.is_empty():
		best.point = origin + dir * best.t
	return best


static func _ray_capsule(o: Vector3, d: Vector3, a: Vector3, b: Vector3, r: float) -> float:
	var ab = b - a
	var w0 = o - a
	var B = d.dot(ab)
	var C = ab.dot(ab)
	var D = d.dot(w0)
	var E = ab.dot(w0)
	var denom = C - B * B
	var u = 0.5
	if denom > 1e-6:
		u = (E - B * D) / denom
	u = clampf(u, 0.0, 1.0)
	var oc = a + ab * u - o
	var tca = oc.dot(d)
	var d2 = oc.length_squared() - tca * tca
	if d2 > r * r:
		return -1.0
	var thc = sqrt(r * r - d2)
	var t = tca - thc
	if t < 0:
		t = tca + thc
	return t


## Parts within an explosion radius.
func parts_in_radius(point: Vector3, radius: float) -> Array:
	var out = []
	if state != "fight":
		return out
	for c in caps:
		if out.has(c.part):
			continue
		var xf: Transform3D = (c.node as Node3D).global_transform
		var a = xf * (c.a as Vector3)
		var b = xf * (c.b as Vector3)
		var ab = b - a
		var u = clampf((point - a).dot(ab) / maxf(ab.length_squared(), 1e-6), 0, 1)
		if (a + ab * u).distance_to(point) < radius + c.r * MODEL_SCALE:
			out.append(c.part)
	return out


## Damage a part. Returns {"result": "hit" | "armor" | "broken" | "dead" | "none", "part"}.
func damage(part: String, amount: float, point: Vector3) -> Dictionary:
	if state != "fight":
		return {"result": "none"}
	var p: Dictionary = parts[part]
	if part == "Head" and not head_open:
		effects.puff(point, Color("ffd27a"), 2, 0.3)
		if _tip_t <= 0:
			_tip_t = 4.0
			effects.popup_world(point, "PANTSER! SCHIET EERST DE FIETSEN ERAF", "bad", 1.6)
		return {"result": "armor", "part": part}
	if not p.alive:
		effects.puff(point, Color("ffd27a"), 2, 0.3)
		return {"result": "armor", "part": part}
	p.hp = maxf(0.0, p.hp - amount)
	_flash_part(part)
	_flinch = minf(1.0, _flinch + 0.25 + amount * 0.05)
	effects.puff(point, Color("ffcf8a"), 3, 0.5)
	if _pain_t <= 0 and randf() < 0.35:
		_pain_t = 3.0
		effects.bubble(n.Boss_Neck, Vector3(0, 3.2, 0), PAIN.pick_random(), false, 1.4)
	if p.hp > 0:
		return {"result": "hit", "part": part}
	p.alive = false
	if part == "Head":
		_start_dying()
		return {"result": "dead", "part": part}
	_break_bike(part)
	return {"result": "broken", "part": part}


func _flash_part(part: String) -> void:
	_flash[part] = 0.08
	for mi in parts[part].meshes:
		if is_instance_valid(mi) and model.is_ancestor_of(mi):
			mi.material_overlay = _flash_mat


func _break_bike(part: String) -> void:
	var center = _part_center(part)
	for mi in parts[part].meshes:
		mi.material_overlay = null
		var aabb: AABB = (mi as MeshInstance3D).get_aabb()
		var c: Vector3 = mi.global_transform * aabb.get_center()
		# fly sideways and away from the player, never into the camera
		var out = c - model.global_position
		out.y = 0
		var away = model.global_position - player_eye
		away.y = 0
		var push = out.normalized() * randf_range(3, 6) + away.normalized() * randf_range(2, 4)
		effects.add_debris(mi, c, push + Vector3(0, randf_range(7, 11), 0),
			Vector3(randf_range(-4, 4), randf_range(-4, 4), randf_range(-4, 4)), {"radius": 0.7, "life": 5.0, "bounce": 0.3})
	effects.explosion(center)
	Sfx.explosion(center.distance_to(player_eye))
	Sfx.clank_heavy()
	effects.add_shake(0.6)
	_stagger = 1.0
	if part.begins_with("Leg"):
		_kneel = minf(1.0, _kneel + 0.35)
	if bikes_left() == 0:
		head_open = true
		rage = true
		_eye_glow(2.5)
		Sfx.roar()
		effects.add_shake(0.8)
		effects.bubble(n.Boss_Neck, Vector3(0, 3.2, 0), RAGE.pick_random(), true, 2.4)
		_attack_cd = minf(_attack_cd, 1.5)


func _start_dying() -> void:
	state = "dying"
	_attack = {}
	_die = {"t": 0.0, "next": 0.25, "collapsed": false}
	if _held_tyre:
		_held_tyre.queue_free()
		_held_tyre = null
	var hp = _head_pos()
	for mi in parts.Head.meshes:
		mi.material_overlay = null
		effects.add_debris(mi, hp, Vector3(randf_range(-2, 2), 14, 0) + (player_eye - hp).normalized() * 1.5,
			Vector3(randf_range(-6, 6), randf_range(-6, 6), randf_range(-6, 6)), {"radius": 0.9, "life": 6.0, "bounce": 0.45})
	effects.explosion(hp)
	Sfx.explosion(5.0)
	Sfx.roar()
	effects.add_shake(1.2)


func _step_dying(dt: float) -> void:
	_die.t += dt
	_kneel = minf(1.0, _kneel + dt * 0.5)
	_flinch = 0.6 + sin(_die.t * 30.0) * 0.3
	_aim = move_toward(_aim, 0.0, dt * 2.0)
	_throw = move_toward(_throw, 0.0, dt * 2.0)
	if _die.t >= _die.next and _die.t < 2.6:
		_die.next += randf_range(0.18, 0.35)
		var c = caps.pick_random()
		var xf: Transform3D = (c.node as Node3D).global_transform
		var at = xf * (c.a as Vector3).lerp(c.b, randf())
		effects.explosion(at)
		Sfx.explosion(at.distance_to(player_eye) + 6.0)
	if _die.t >= 2.7 and not _die.collapsed:
		_die.collapsed = true
		for mi in parts.Skeleton.meshes:
			if not is_instance_valid(mi) or not model.is_ancestor_of(mi):
				continue
			var aabb: AABB = (mi as MeshInstance3D).get_aabb()
			var c: Vector3 = mi.global_transform * aabb.get_center()
			var out = c - model.global_position
			out.y = 0
			effects.add_debris(mi, c, out.normalized() * randf_range(2, 6) + Vector3(0, randf_range(4, 9), 0),
				Vector3(randf_range(-5, 5), randf_range(-5, 5), randf_range(-5, 5)), {"radius": 0.6, "life": 5.5, "bounce": 0.3})
		var base = model.global_position + Vector3(0, 3, 0)
		effects.explosion(base)
		effects.explosion(base + Vector3(0, 3, 0))
		Sfx.explosion(10.0)
		effects.add_shake(1.2)
	if _die.t >= 3.2:
		state = "dead"
		game.boss_defeated()


# ------------------------------------------------------------ procedural pose

func _pose(dt: float) -> void:
	_flinch = move_toward(_flinch, 0.0, dt * 2.5)
	_stagger = move_toward(_stagger, 0.0, dt * 1.5)
	var t = _t
	var breathe = sin(t * 1.7)
	var sway = sin(_phase) if _moving else 0.0
	var lift_max = maxf(_lift.L, _lift.R)
	var stag = sin(t * 18.0) * _stagger * 0.12
	# hips: bob with the steps, roll towards the planted foot, sink when kneeling
	var hips: Node3D = n.Boss_Hips
	var hr: Transform3D = rest.Boss_Hips
	hips.position = hr.origin + Vector3(0, lift_max * 0.18 - _kneel * 1.1 + breathe * 0.03, 0)
	hips.basis = hr.basis * Basis(Vector3.RIGHT, sway * 0.06 + stag)
	for side in ["L", "R"]:
		var lift: float = _lift[side]
		var kneel_bend = _kneel * (0.9 if side == "L" else 0.5)
		var leg: Node3D = n["Boss_Leg%s_Pivot" % side]
		leg.basis = (rest["Boss_Leg%s_Pivot" % side] as Transform3D).basis * Basis(Vector3(0, 0, 1), lift * 0.55 + kneel_bend * 0.8)
		var knee: Node3D = n["Boss_Knee" + side]
		knee.basis = (rest["Boss_Knee" + side] as Transform3D).basis * Basis(Vector3(0, 0, 1), -lift * 1.0 - kneel_bend * 1.4)
	# spine: breathing, flinch back when hit, twist into the rocket aim
	var spine: Node3D = n.Boss_Spine
	spine.basis = (rest.Boss_Spine as Transform3D).basis * Basis(Vector3.UP, _aim * 0.25 + stag) \
		* Basis(Vector3(0, 0, 1), breathe * 0.025 + _flinch * 0.12 - _kneel * 0.15)
	# head: look at the player, shake when hurt
	var neck: Node3D = n.Boss_Neck
	neck.basis = (rest.Boss_Neck as Transform3D).basis * Basis(Vector3.UP, sin(t * 0.7) * 0.15 + sin(t * 40.0) * _flinch * 0.05) \
		* Basis(Vector3(0, 0, 1), -0.05 + breathe * 0.02 + _kneel * 0.2)
	# left arm: swing, or the tyre throw
	var arm_l: Node3D = n.Boss_ArmL_Pivot
	arm_l.basis = (rest.Boss_ArmL_Pivot as Transform3D).basis * Basis(Vector3(0, 0, 1), -sway * 0.12 + sin(t * 1.3) * 0.05 + _throw)
	(n.Boss_ElbowL as Node3D).basis = (rest.Boss_ElbowL as Transform3D).basis * Basis(Vector3(0, 0, 1), _elbow_l + 0.1 + _flinch * 0.2)
	# right arm: swing, blended with aiming the launcher at the player
	var arm_r: Node3D = n.Boss_ArmR_Pivot
	var rr: Transform3D = rest.Boss_ArmR_Pivot
	var idle = rr.basis * Basis(Vector3(0, 0, 1), sway * 0.12 + sin(t * 1.3 + 1.0) * 0.05)
	arm_r.basis = idle
	(n.Boss_ElbowR as Node3D).basis = (rest.Boss_ElbowR as Transform3D).basis * Basis(Vector3(0, 0, 1), 0.15 * (1.0 - _aim))
	if _aim > 0.001:
		var parent_g: Basis = (arm_r.get_parent() as Node3D).global_basis
		var m_local: Vector3 = (n.Boss_ElbowR as Node3D).transform * ((n.Boss_Muzzle_1 as Node3D).position + (n.Boss_Muzzle_4 as Node3D).position) * 0.5
		var cur: Vector3 = (parent_g * idle * m_local).normalized()
		var want: Vector3 = (player_eye - arm_r.global_position).normalized()
		var q = Quaternion(cur, want)
		var aimed: Basis = parent_g.inverse() * (Basis(q) * (parent_g * idle))
		arm_r.basis = Basis(idle.get_rotation_quaternion().slerp(aimed.get_rotation_quaternion(), _aim))
