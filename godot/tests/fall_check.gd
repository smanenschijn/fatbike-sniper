extends Node3D
## Visual check of the knock-off fall: one rider shot off its bike, screenshots every 0.12 s.
## Run: Godot --path godot res://tests/fall_check.tscn -- --out=/tmp/fall [--explode] [--seed=3]

var out := "/tmp/fall"
var explode := false
var front := false
var t := 0.0
var shots := 0
var riders: Riders
var fx: Effects


func _ready() -> void:
	var sd := 1
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--out="):
			out = a.substr(6)
		elif a == "--explode":
			explode = true
		elif a == "--front":   # the player's view: from where the shot came
			front = true
		elif a.begins_with("--seed="):
			sd = int(a.substr(7))
	seed(sd)
	var cam := Camera3D.new()
	add_child(cam)
	if front:
		cam.look_at_from_position(Vector3(9.0, 1.6, 0.5), Vector3(-2.0, 0.9, 0))
	else:
		cam.look_at_from_position(Vector3(-4.0, 2.5, 11.0), Vector3(-4.0, 2.2, 0))
	cam.fov = 60
	var sun := DirectionalLight3D.new()
	sun.rotation = Vector3(-0.9, 0.5, 0)
	add_child(sun)
	var env := WorldEnvironment.new()
	env.environment = Environment.new()
	env.environment.background_mode = Environment.BG_COLOR
	env.environment.background_color = Color("9cc7e8")
	env.environment.ambient_light_color = Color(0.7, 0.7, 0.75)
	env.environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	add_child(env)
	var ground := MeshInstance3D.new()
	var pm := PlaneMesh.new()
	pm.size = Vector2(200, 200)
	ground.mesh = pm
	var gm := StandardMaterial3D.new()
	gm.albedo_color = Color("b9a58a")
	ground.material_override = gm
	add_child(ground)
	var layer := Control.new()
	add_child(layer)
	fx = Effects.new()
	add_child(fx)
	fx.setup(cam, layer, ThemeDB.fallback_font, ThemeDB.fallback_font)
	riders = Riders.new()
	add_child(riders)
	riders.setup(fx, Vector3(0, 1.6, 10))
	var m = riders._build("duo" if sd % 2 == 0 else "normal")
	add_child(m.root)
	var r = {"id": 1, "alive": true, "yaw": 0.0, "speed": 6.0, "type": "normal"}
	r.merge(m)
	await get_tree().create_timer(0.5).timeout
	riders.knock_off(r, Vector3(-1, 0, 0), 6.0, explode)
	t = 0.0
	shots = 1


func _process(dt: float) -> void:
	fx.step(dt)
	if shots == 0:
		return
	t += dt
	if t >= shots * 0.15:
		get_viewport().get_texture().get_image().save_png("%s_%02d.png" % [out, shots])
		shots += 1
	if shots > 40:
		get_tree().quit()
