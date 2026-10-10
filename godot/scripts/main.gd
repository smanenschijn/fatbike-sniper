extends Node3D
## Boot, input, screens and the main loop. Port of src/main.js + src/input.js.

class InputState:
	var yaw = 0.0
	var pitch = -0.05
	var sens_scale = 1.0
	var fire_down = false
	var fire_pressed = false
	var aim_held = false
	var zoom_toggle = false
	var keys_pressed = {}
	var keys_down = {}
	var wheel = 0
	var pending_aim = null  # screen position for the next shot (touch taps)

	var zoom_held: bool:
		get:
			return aim_held or zoom_toggle or keys_down.has(KEY_SHIFT)

	func aim_direction(cam: Camera3D) -> Vector3:
		if pending_aim != null:
			return cam.project_ray_normal(pending_aim)
		return -cam.global_basis.z

	func end_frame() -> void:
		fire_pressed = false
		keys_pressed.clear()
		wheel = 0
		pending_aim = null

const HS_FILE := "user://highscores.cfg"
const SETTINGS_FILE := "user://settings.cfg"

var world: World
var effects: Effects
var riders: Riders
var weapons: Weapons
var hud: Hud
var game: Game
var camera: Camera3D
var inp := InputState.new()
var mode := "title"  # title | playing | paused | ended
var settings := {"round_time": 60, "level": "normal"}
var touch := false
var demo_t := 0.0
var last_score := {}
var _look_touch := -1
var _look_start := {}
var _auto := {}
var _post: ColorRect
var _post_mat: ShaderMaterial
var _bt_was := false
var _wave := -1.0
var _post_t := 0.0


func _ready() -> void:
	touch = Config.is_touch()
	_load_settings()
	world = World.new()
	add_child(world)
	camera = Camera3D.new()
	camera.fov = Config.FOV
	camera.near = 0.02
	camera.far = 1500.0
	camera.rotation_order = EULER_ORDER_YXZ
	add_child(camera)
	camera.position = world.eye
	camera.current = true

	# bullet-time post-process: a full-screen shader between the 3D view and the HUD
	var post_layer = CanvasLayer.new()
	post_layer.layer = 0
	add_child(post_layer)
	_post = ColorRect.new()
	_post.set_anchors_preset(Control.PRESET_FULL_RECT)
	_post.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_post_mat = ShaderMaterial.new()
	_post_mat.shader = load("res://scripts/bullet_time.gdshader")
	_post.material = _post_mat
	_post.visible = false
	post_layer.add_child(_post)

	hud = Hud.new()
	add_child(hud)
	effects = Effects.new()
	add_child(effects)
	effects.setup(camera, hud.popups, hud.font, hud.font_ui)
	riders = Riders.new()
	world.add_child(riders)
	riders.setup(effects, world.eye)
	weapons = Weapons.new()
	add_child(weapons)
	weapons.setup(camera)
	game = Game.new()
	add_child(game)
	game.setup(world, riders, weapons, effects, hud, camera)
	game.ended.connect(_on_ended)

	hud.start_pressed.connect(start_game)
	hud.menu_pressed.connect(show_title)
	hud.resume_pressed.connect(resume)
	hud.option_changed.connect(_on_option)
	hud.music_toggle.connect(func(): Sfx.toggle_mute())
	hud.save_name.connect(_save_name)
	hud.touch_fire.connect(_on_touch_fire)
	hud.touch_key.connect(func(code): inp.keys_pressed[code] = true)
	hud.touch_zoom_toggle.connect(func(): inp.zoom_toggle = not inp.zoom_toggle)

	Sfx.set_intensity("title")
	Sfx.start_music()
	show_title()
	_parse_auto_args()


func _on_touch_fire(down: bool) -> void:
	inp.fire_down = down
	if down:
		inp.fire_pressed = true
		inp.pending_aim = null


# ------------------------------------------------------------ screens

func show_title() -> void:
	mode = "title"
	Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
	hud.show_game(false)
	hud.show_pause(false)
	hud.hide_end()
	hud.show_title(true)
	hud.sync_options(settings)
	hud.title_scores(_load_scores(), _mode_label())
	game.state = "idle"
	Sfx.set_intensity("title")


func start_game() -> void:
	hud.show_title(false)
	hud.hide_end()
	hud.show_pause(false)
	hud.show_game(true)
	inp.yaw = 0.0
	inp.pitch = -0.05
	inp.zoom_toggle = false
	game.reset(settings.round_time, settings.level)
	mode = "playing"
	if not touch:
		Input.mouse_mode = Input.MOUSE_MODE_CAPTURED


func pause() -> void:
	mode = "paused"
	Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
	hud.show_pause(true)


func resume() -> void:
	hud.show_pause(false)
	mode = "playing"
	if not touch:
		Input.mouse_mode = Input.MOUSE_MODE_CAPTURED


func _on_ended(reason: String, score: int, stats: Dictionary) -> void:
	mode = "ended"
	Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
	last_score = {"score": score}
	await get_tree().create_timer(1.3).timeout
	hud.show_game(false)
	var list = _load_scores()
	var qualifies = score > 0 and (list.size() < 10 or score > list[list.size() - 1].score)
	var scale: float = {60: 1.0, 180: 2.2, 300: 3.2}.get(int(settings.round_time), 1.0)
	hud.show_end(reason, _rank(score / scale), _mode_label(), score, stats, qualifies)
	hud.show_end_scores(list)


func _rank(score: float) -> String:
	if score < 400: return "Terrasganger"
	if score < 1200: return "Buurtwacht"
	if score < 2500: return "Fatbike Verdelger"
	if score < 4500: return "Schrik van het Plein"
	return "Legende van 't Pleintje"


func _mode_label() -> String:
	return "%d min · %s" % [settings.round_time / 60, Config.LEVELS[settings.level].label]


func _on_option(key: String, value) -> void:
	settings[key] = value
	_save_settings()
	Sfx.click()
	hud.sync_options(settings)
	hud.title_scores(_load_scores(), _mode_label())


# ------------------------------------------------------------ persistence

func _mode_key() -> String:
	return "%d_%s" % [settings.round_time, settings.level]


func _load_scores() -> Array:
	var cfg = ConfigFile.new()
	if cfg.load(HS_FILE) != OK:
		return []
	return cfg.get_value("scores", _mode_key(), [])


func _save_name(name: String) -> void:
	if last_score.is_empty():
		return
	if name == "":
		name = "Anoniem"
	var cfg = ConfigFile.new()
	cfg.load(HS_FILE)
	var list: Array = cfg.get_value("scores", _mode_key(), [])
	list.append({"name": name, "score": last_score.score})
	list.sort_custom(func(a, b): return a.score > b.score)
	list = list.slice(0, 10)
	cfg.set_value("scores", _mode_key(), list)
	cfg.save(HS_FILE)
	var idx = -1
	for i in list.size():
		if list[i].name == name and list[i].score == last_score.score:
			idx = i
			break
	hud.show_end_scores(list, idx)
	last_score = {}


func _load_settings() -> void:
	var cfg = ConfigFile.new()
	if cfg.load(SETTINGS_FILE) == OK:
		var rt = cfg.get_value("round", "round_time", 60)
		var lv = cfg.get_value("round", "level", "normal")
		if rt in Config.ROUND_OPTIONS:
			settings.round_time = rt
		if Config.LEVELS.has(lv):
			settings.level = lv


func _save_settings() -> void:
	var cfg = ConfigFile.new()
	cfg.load(SETTINGS_FILE)
	cfg.set_value("round", "round_time", settings.round_time)
	cfg.set_value("round", "level", settings.level)
	cfg.save(SETTINGS_FILE)


# ------------------------------------------------------------ input

func _unhandled_input(e: InputEvent) -> void:
	if e is InputEventKey and e.pressed and not e.echo:
		inp.keys_pressed[e.keycode] = true
		inp.keys_down[e.keycode] = true
		if e.keycode == KEY_M:
			Sfx.toggle_mute()
		if e.keycode == KEY_F11 or (e.keycode == KEY_F and e.meta_pressed):
			var fs := DisplayServer.window_get_mode() == DisplayServer.WINDOW_MODE_FULLSCREEN
			DisplayServer.window_set_mode(DisplayServer.WINDOW_MODE_WINDOWED if fs else DisplayServer.WINDOW_MODE_FULLSCREEN)
		if e.keycode == KEY_ESCAPE and mode == "playing":
			pause()
	elif e is InputEventKey and not e.pressed:
		inp.keys_down.erase(e.keycode)
	if mode != "playing":
		return
	if e is InputEventMouseMotion and Input.mouse_mode == Input.MOUSE_MODE_CAPTURED:
		var s = Config.MOUSE_SENS * inp.sens_scale
		inp.yaw = clampf(inp.yaw - e.relative.x * s, -Config.YAW_LIMIT, Config.YAW_LIMIT)
		inp.pitch = clampf(inp.pitch - e.relative.y * s, Config.PITCH_MIN, Config.PITCH_MAX)
	elif e is InputEventMouseButton and not touch:
		if Input.mouse_mode != Input.MOUSE_MODE_CAPTURED and e.pressed:
			Input.mouse_mode = Input.MOUSE_MODE_CAPTURED
			return
		match e.button_index:
			MOUSE_BUTTON_LEFT:
				inp.fire_down = e.pressed
				if e.pressed:
					inp.fire_pressed = true
			MOUSE_BUTTON_RIGHT:
				inp.aim_held = e.pressed
			MOUSE_BUTTON_WHEEL_UP:
				if e.pressed:
					inp.wheel -= 1
			MOUSE_BUTTON_WHEEL_DOWN:
				if e.pressed:
					inp.wheel += 1
	# touch: one finger drags the view, a quick tap fires at the tapped spot
	elif e is InputEventScreenTouch:
		if e.pressed and _look_touch == -1:
			_look_touch = e.index
			_look_start = {"pos": e.position, "t": Time.get_ticks_msec(), "moved": 0.0}
		elif not e.pressed and e.index == _look_touch:
			_look_touch = -1
			if _look_start.moved < 14.0 and Time.get_ticks_msec() - _look_start.t < 350:
				inp.pending_aim = e.position
				inp.fire_pressed = true
	elif e is InputEventScreenDrag and e.index == _look_touch:
		_look_start.moved += e.relative.length()
		var s = Config.TOUCH_SENS * inp.sens_scale
		inp.yaw = clampf(inp.yaw - e.relative.x * s, -Config.YAW_LIMIT, Config.YAW_LIMIT)
		inp.pitch = clampf(inp.pitch - e.relative.y * s, Config.PITCH_MIN, Config.PITCH_MAX)


func _notification(what: int) -> void:
	if what == NOTIFICATION_APPLICATION_FOCUS_OUT and mode == "playing" and _auto.is_empty():
		pause()


# ------------------------------------------------------------ loop

const DEMO_DIFF := {"spawn_interval": 1.4, "max_alive": 8, "attack_chance": 0.0, "speed_mul": 1.1}


func _process(delta: float) -> void:
	var dt = minf(delta, 0.05)
	if mode == "title" or mode == "ended":
		demo_t += dt
		riders.step(dt, DEMO_DIFF, 30.0)
		camera.rotation = Vector3(-0.08 + sin(demo_t * 0.15) * 0.05, sin(demo_t * 0.12) * 0.6, 0)
		weapons.root.visible = false
	elif mode == "playing":
		if touch and inp.keys_pressed.has(KEY_ESCAPE):
			pause()
		game.step(dt, inp)
		camera.rotation = Vector3(inp.pitch, inp.yaw, 0)
		if inp.pending_aim == null:
			hud.set_aim(null)
	if mode == "playing" or mode == "paused":
		hud.set_weapons(weapons.hud_state())
		hud.set_threats(_screen_threats())
	var bt: float = game.bullet_amount() if mode == "playing" or mode == "paused" else 0.0
	_apply_bullet_look(bt, dt)
	camera.position = world.eye
	if effects.shake > 0:
		var s = effects.shake * effects.shake * 0.06
		camera.position += Vector3(randf_range(-0.5, 0.5) * s, randf_range(-0.5, 0.5) * s, 0)
		camera.rotation.z = randf_range(-0.5, 0.5) * s * 0.5
	if mode != "paused":
		var wdt = dt * game.time_scale() if mode == "playing" else dt
		effects.step(wdt)
	inp.end_frame()
	_auto_step(dt)


## Project the riders' threats to screen space for the HUD (rings on screen, arrows on the edge).
func _screen_threats() -> Array:
	var out = []
	var vs := get_viewport().get_visible_rect().size
	for th in riders.threats():
		var behind := camera.is_position_behind(th.pos)
		var sp := camera.unproject_position(th.pos)
		if behind:
			sp = vs - sp  # mirror so the arrow points the right way
		var onscreen := not behind and sp.x > 0 and sp.y > 0 and sp.x < vs.x and sp.y < vs.y
		out.append({"screen": sp, "onscreen": onscreen, "kind": th.kind, "urgency": th.urgency})
	return out


## Bullet-time look: post shader (grade, fringe, vignette, grain, speed lines) + a ripple when it starts.
func _apply_bullet_look(amount: float, dt: float) -> void:
	var active: bool = game.bt.active and mode == "playing"
	if active and not _bt_was:
		_wave = 0.0  # time ripple
	_bt_was = active
	if _wave >= 0.0:
		_wave += dt * 2.6
		if _wave > 1.4:
			_wave = -1.0
	_post_t += dt
	_post.visible = amount > 0.001 or _wave >= 0.0
	if _post.visible:
		_post_mat.set_shader_parameter("amount", amount)
		_post_mat.set_shader_parameter("wave", _wave)
		_post_mat.set_shader_parameter("time_s", _post_t)
	# focus: a slight zoom-in while time crawls
	if mode == "playing":
		camera.fov -= 6.0 * amount * (camera.fov / Config.FOV)


# ------------------------------------------------------------ automation (screenshots / smoke tests)
# Usage: Godot --path godot -- --autoshot=/tmp/shot.png [--autoplay] [--wait=6]

func _parse_auto_args() -> void:
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--autoshot="):
			_auto.shot = a.substr(11)
		elif a == "--autoplay":
			_auto.play = true
		elif a == "--knife":
			_auto.knife = true
		elif a == "--bullet":
			_auto.bullet = true
		elif a.begins_with("--wait="):
			_auto.wait = float(a.substr(7))
	if _auto.has("shot"):
		_auto.t = 0.0
		_auto.wait = _auto.get("wait", 6.0)
		if _auto.get("play", false):
			start_game()


func _auto_step(dt: float) -> void:
	if not _auto.has("shot"):
		return
	_auto.t += dt
	if _auto.get("play", false) and mode == "playing":
		# aim at the nearest rider and fire every now and then
		var best = null
		for r in riders.list:
			var p: Vector3 = (r.root as Node3D).position
			if p.z < world.eye.z - 4 and (best == null or p.distance_to(world.eye) < best.root.position.distance_to(world.eye)):
				best = r
		if best != null:
			var t: Vector3 = (best.model as Node3D).global_transform * Vector3(-0.07, 1.17, 0)
			var d = (t - world.eye).normalized()
			inp.yaw = atan2(-d.x, -d.z)
			inp.pitch = asin(d.y)
			if fmod(_auto.t, 1.2) < dt and not _auto.get("knife", false):
				inp.fire_pressed = true
	if _auto.get("knife", false) and game.state == "playing" and _auto.t > _auto.wait - 2.0 and not _auto.has("knife_done"):
		_auto.knife_done = true
		var near = riders.list.filter(func(r): return r.alive and (r.root as Node3D).position.distance_to(world.eye) < 30)
		if not near.is_empty():
			riders.start_windup(near[0], true)
	if _auto.get("bullet", false) and mode == "playing" and game.state == "playing" and _auto.t > _auto.wait - 1.2 and not game.bt.active:
		game.bt.meter = 1.0
		game.start_bullet_time()
	if _auto.t >= _auto.wait:
		_auto.erase("play")
		var img = get_viewport().get_texture().get_image()
		img.save_png(_auto.shot)
		print("[auto] screenshot saved to ", _auto.shot, " riders=", riders.list.size(), " score=", game.score)
		get_tree().quit()
