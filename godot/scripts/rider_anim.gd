class_name RiderAnim
extends RefCounted
## Skeleton animations of the rigged (glow-up) riders, see blender/rig_v2.py.
## Two AnimationPlayers per rider: "Legs" pedals (and turns the crank along), "Upper" rides, reacts and throws.
## The GLB's animations key every bone, so each player gets a copy with only its own bones' tracks.

const LEG_BONES := ["hips", "thigh.L", "shin.L", "foot.L", "thigh.R", "shin.R", "foot.R"]
const LOOPS := ["Pedal", "Ride", "Phone", "Flail", "Stand"]
const WHEEL_R := 0.33
const GEAR := 2.5          # wheel turns per crank turn: lazy e-bike pedalling
const PHONE_CHANCE := 0.2
# the knife in the right fist (hand bone: +Y runs from the wrist to the knuckles)
const KNIFE_IN_HAND := Transform3D(Basis(Vector3(0, 1, 0), Vector3(-1, 0, 0), Vector3(0, 0, 1)), Vector3(0, 0.07, 0.02))


## {variant id: {"legs": AnimationLibrary, "upper": AnimationLibrary}} from the GLB's AnimationPlayer ("V01_Pedal", ...).
static func libraries(lib: Node) -> Dictionary:
	var out := {}
	for ap in lib.find_children("*", "AnimationPlayer", true, false):
		for full in (ap as AnimationPlayer).get_animation_list():
			var cut := String(full).find("_")
			if cut < 0:
				continue
			var id := String(full).substr(0, cut)
			var nm := String(full).substr(cut + 1)
			if not out.has(id):
				out[id] = {"legs": AnimationLibrary.new(), "upper": AnimationLibrary.new()}
			var src: Animation = (ap as AnimationPlayer).get_animation(full)
			for part in ["legs", "upper"]:
				var a: Animation = src.duplicate()
				for t in range(a.get_track_count() - 1, -1, -1):
					var bone := String(a.track_get_path(t)).get_slice(":", 1)
					if (bone in LEG_BONES) != (part == "legs"):
						a.remove_track(t)
					else:
						a.track_set_path(t, NodePath("Skeleton3D:" + bone))
				a.loop_mode = Animation.LOOP_LINEAR if nm in LOOPS else Animation.LOOP_NONE
				(out[id][part] as AnimationLibrary).add_animation(nm, a)
	return out


## Give a freshly duplicated rider its players. driver: pedals and turns `crank`; a passenger just sits.
static func attach(body: Node3D, libs: Dictionary, crank: Node3D) -> Dictionary:
	var skel := body.find_child("Skeleton3D", true, false) as Skeleton3D
	var rig := skel.get_parent() as Node3D   # "Rig", "Rig_001", ... (Blender keeps names unique)
	var legs := AnimationPlayer.new()
	var upper := AnimationPlayer.new()
	legs.name = "Legs"
	upper.name = "Upper"
	legs.add_animation_library("", libs.legs)
	upper.add_animation_library("", libs.upper)
	upper.playback_default_blend_time = 0.2
	rig.add_child(legs)
	rig.add_child(upper)
	var a := {"body": body, "legs": legs, "upper": upper, "skel": skel, "crank": crank, "idle": "Ride",
		"phone": body.find_child("Rider_Phone", true, false), "knife": body.find_child("Rider_Knife", true, false)}
	a.knife_home = (a.knife as Node3D).get_parent()
	a.knife_xf = (a.knife as Node3D).transform
	var hand := BoneAttachment3D.new()
	hand.bone_name = "hand.R"
	skel.add_child(hand)
	a.hand = hand
	if crank:
		legs.play("Pedal")
	if crank and randf() < PHONE_CHANCE:
		a.idle = "Phone"
	upper.play(a.idle)
	upper.seek(randf() * upper.current_animation_length)
	(a.phone as Node3D).visible = a.idle == "Phone"
	return a


## Every frame while riding: pedal at the bike's speed, crank in step with the feet.
static func ride(a: Dictionary, speed: float) -> void:
	if a.crank == null:
		return
	var legs: AnimationPlayer = a.legs
	legs.speed_scale = speed / (TAU * WHEEL_R) / GEAR
	if legs.current_animation == "Pedal":
		(a.crank as Node3D).rotation.z = -TAU * legs.current_animation_position / legs.current_animation_length


## A one-shot upper-body reaction ("ShakeFist", "Shock"), then back to riding (or phoning).
static func react(a: Dictionary, nm: String) -> void:
	var up: AnimationPlayer = a.upper
	if a.get("down", false) or up.current_animation in ["Windup", "Throw", "ShakeFist", "Shock"]:
		return
	up.play(nm, 0.12)
	up.queue(a.idle)


## Pull the knife from the waistband and cock it: lasts `duration` seconds, the knife changes hands halfway.
static func windup(a: Dictionary, duration: float) -> void:
	a.idle = "Ride"
	(a.phone as Node3D).visible = false
	var up: AnimationPlayer = a.upper
	up.play("Windup", 0.1, up.get_animation("Windup").length / maxf(duration, 0.1))
	var knife: Node3D = a.knife
	knife.get_tree().create_timer(duration * 0.45, false).timeout.connect(func():
		if is_instance_valid(knife) and not a.get("down", false) and up.current_animation == "Windup":
			knife.reparent(a.hand, false)
			knife.transform = KNIFE_IN_HAND
			knife.visible = true)


## Let go: the thrown knife is a separate mesh, so the one in the fist disappears; a new one turns up in the waistband.
static func throw(a: Dictionary, thrown: bool) -> void:
	var up: AnimationPlayer = a.upper
	if thrown:
		up.play("Throw", 0.05)
		(a.knife as Node3D).visible = false
	else:
		up.play(a.idle, 0.3)
	up.queue(a.idle)
	var knife: Node3D = a.knife
	knife.get_tree().create_timer(1.2, false).timeout.connect(func():
		if is_instance_valid(knife) and not a.get("down", false):
			knife.reparent(a.knife_home, false)
			knife.transform = a.knife_xf
			knife.visible = true)


## Knocked off: windmill and kick in the air; `landed` lies him down like a starfish.
static func knocked(a: Dictionary) -> void:
	a.down = true
	for p in [a.legs, a.upper]:
		(p as AnimationPlayer).speed_scale = 1.0
		(p as AnimationPlayer).clear_queue()
		(p as AnimationPlayer).play("Flail", 0.08)


static func landed(a: Dictionary) -> void:
	for p in [a.legs, a.upper]:
		(p as AnimationPlayer).play("Splat", 0.25)
