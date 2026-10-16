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
var settings := {"round_time": 60, "level": "normal", "boss": true, "map": "pleintje"}
var adventure := false   # the last started mode ("OPNIEUW" replays it)
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
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--map="):
			settings.map = a.substr(6)
	Config.use_map(settings.map)
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
	# Web: the browser hands us a canvas at the screen's full pixel density (a retina laptop: ~5 megapixels).
	# Render the 3D world at no more than WEB_3D_PIXELS so the GPU keeps up; the HUD stays sharp.
	if OS.has_feature("web"):
		get_viewport().size_changed.connect(_fit_3d_resolution)
		_fit_3d_resolution()

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
	hud.mode_selected.connect(_choose_mode)
	hud.back_pressed.connect(_back_home)
	hud.menu_pressed.connect(_back_to_menu)
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
	hud.show_home()
	hud.sync_options(settings)
	game.state = "idle"
	game.phase = ""
	game.view_yaw = 0.0
	adventure = false
	if Config.map_id != settings.map or world.is_adventure():   # back from the adventure
		Config.use_map(settings.map)
		riders.clear()
		effects.water = []
		world.load_map()
	world.eye = world.seat
	world.hold_ijsje(null)
	riders.player_eye = world.eye
	hud.title_scores(_load_scores(), _mode_label())
	game.boss.reset()
	world.fold_parasol(false)
	world.set_dusk(false, 0.01)
	Sfx.restart_music(false)
	Sfx.set_intensity("title")


## Title step 1 -> 2: classic or the story (adventure), then its options.
func _choose_mode(adv: bool) -> void:
	adventure = adv
	Sfx.click()
	hud.show_setup(adv)
	hud.title_scores(_load_scores(), _mode_label())


## MENU from the pause or end screen: back to the options of the mode you were playing.
func _back_to_menu() -> void:
	var adv := adventure
	show_title()
	_choose_mode(adv)


func _back_home() -> void:
	adventure = false
	Sfx.click()
	hud.show_home()


func start_game() -> void:
	hud.show_title(false)
	hud.hide_end()
	hud.show_pause(false)
	hud.show_game(true)
	inp.yaw = 0.0
	inp.pitch = -0.05
	inp.zoom_toggle = false
	game.reset(settings.round_time, settings.level, settings.boss, adventure)
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
	var scale: float = 2.2 if adventure else {60: 1.0, 180: 2.2, 300: 3.2}.get(int(settings.round_time), 1.0)
	hud.show_end(reason, _rank(score / scale), _mode_label(), score, stats, qualifies)
	hud.show_end_scores(list)


func _rank(score: float) -> String:
	if score < 400: return "Terrasganger"
	if score < 1200: return "Buurtwacht"
	if score < 2500: return "Fatbike Verdelger"
	if score < 4500: return "Schrik van het Plein"
	return Config.MAP.legend


func _mode_label() -> String:
	if adventure:
		return "CAMPAGNE · %s%s" % [Config.LEVELS[settings.level].label, "" if settings.boss else " · zonder eindbaas"]
	return "%s · %d min · %s%s" % [Config.MAP.label, settings.round_time / 60, Config.LEVELS[settings.level].label, "" if settings.boss else " · zonder eindbaas"]


func _on_option(key: String, value) -> void:
	if key == "map" and value != settings.map:
		Config.use_map(value)
		riders.clear()
		world.load_map()
	settings[key] = value
	_save_settings()
	Sfx.click()
	hud.sync_options(settings)
	hud.title_scores(_load_scores(), _mode_label())


# ------------------------------------------------------------ persistence

## Separate hall of fame per square and with/without the end boss (the boss is worth a lot of points).
## The original square keeps its old keys so existing scores stay.
func _mode_key() -> String:
	if adventure:
		return "adventure_%s%s" % [settings.level, "" if settings.boss else "_noboss"]
	var prefix = "" if settings.map == "pleintje" else settings.map + "_"
	return "%s%d_%s%s" % [prefix, settings.round_time, settings.level, "" if settings.boss else "_noboss"]


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
		settings.boss = bool(cfg.get_value("round", "boss", true))
		var mp = cfg.get_value("round", "map", "pleintje")
		if Config.MAPS.has(mp):
			settings.map = mp


func _save_settings() -> void:
	var cfg = ConfigFile.new()
	cfg.load(SETTINGS_FILE)
	cfg.set_value("round", "round_time", settings.round_time)
	cfg.set_value("round", "level", settings.level)
	cfg.set_value("round", "boss", settings.boss)
	cfg.set_value("round", "map", settings.map)
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
		elif e.keycode == KEY_ESCAPE and mode == "title" and hud.on_sub_page():
			_back_home()
	elif e is InputEventKey and not e.pressed:
		inp.keys_down.erase(e.keycode)
	if mode != "playing":
		return
	if e is InputEventMouseMotion and Input.mouse_mode == Input.MOUSE_MODE_CAPTURED:
		var s = Config.MOUSE_SENS * inp.sens_scale
		inp.yaw = clampf(inp.yaw - e.relative.x * s, -game.yaw_limit(), game.yaw_limit())
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
		inp.yaw = clampf(inp.yaw - e.relative.x * s, -game.yaw_limit(), game.yaw_limit())
		inp.pitch = clampf(inp.pitch - e.relative.y * s, Config.PITCH_MIN, Config.PITCH_MAX)


func _notification(what: int) -> void:
	if what == NOTIFICATION_APPLICATION_FOCUS_OUT and mode == "playing" and _auto.is_empty():
		pause()


const WEB_3D_PIXELS := 2.2e6


func _fit_3d_resolution() -> void:
	var px := DisplayServer.window_get_size()
	get_viewport().scaling_3d_scale = clampf(sqrt(WEB_3D_PIXELS / maxf(1.0, px.x * px.y)), 0.35, 1.0)


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
		camera.rotation = Vector3(inp.pitch, inp.yaw + game.view_yaw, 0)
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
	for th in riders.threats() + game.boss.threats():
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
		elif a == "--adventure":
			adventure = true
			_auto.play = true
		elif a.begins_with("--phase="):   # jump ahead in the adventure: walk_out | route | walk_in | square2
			adventure = true
			_auto.phase = a.substr(8)
		elif a.begins_with("--routeat="):  # with --phase=route: skip to this many metres along the walk
			_auto.route_at = float(a.substr(10))
		elif a == "--boom":   # perf test: a bazooka explosion in front of you every 1.5 s, frame-time stats per second
			_auto.boom = 0.0
			_auto.play = true
		elif a == "--god":   # can't lose hearts (smoke tests)
			_auto.god = true
		elif a == "--noboss":
			settings.boss = false
		elif a == "--boss":
			_auto.boss = true
		elif a == "--bossfight":
			_auto.boss = true
			_auto.skip_intro = true
		elif a.begins_with("--shots="):   # extra screenshots at these seconds: <autoshot>_<t>.png
			_auto.shots = Array(a.substr(8).split(",")).map(func(x): return float(x))
		elif a.begins_with("--wait="):
			_auto.wait = float(a.substr(7))
		elif a.begins_with("--menu="):   # open the title's second step: klassiek | campagne | info
			if a.substr(7) == "info":
				hud.show_info(true)
			else:
				_choose_mode(a.substr(7) == "campagne")
		elif a.begins_with("--map="):   # pleintje | donut
			settings.map = a.substr(6)
		elif a.begins_with("--level="):   # easy | normal | hard | chill
			settings.level = a.substr(8)
		elif a.begins_with("--weapon="):   # start with this weapon (1 = katapult ... 5 = ijsmachine)
			_auto.weapon = int(a.substr(9)) - 1
	if _auto.has("shot"):
		_auto.t = 0.0
		_auto.wait = _auto.get("wait", 6.0)
		if _auto.get("play", false) or _auto.get("boss", false) or _auto.has("phase"):
			start_game()


func _auto_step(dt: float) -> void:
	if not _auto.has("shot"):
		return
	_auto.t += dt
	if _auto.has("weapon") and mode == "playing" and game.state == "playing":
		weapons.select(_auto.weapon, true)
		_auto.erase("weapon")
	if _auto.has("boom") and mode == "playing" and game.state == "playing":
		var vrid := get_viewport().get_viewport_rid()
		if not _auto.has("perf"):
			RenderingServer.viewport_set_measure_render_time(vrid, true)
			_auto.perf = []
			_auto.calls = 0
		_auto.boom += dt
		_auto.perf.append(dt)
		_auto.calls = maxi(_auto.calls, int(Performance.get_monitor(Performance.RENDER_TOTAL_DRAW_CALLS_IN_FRAME)))
		if _auto.boom > 1.5:
			_auto.boom = 0.0
			var fwd := Vector3(-sin(game.view_yaw), 0, -cos(game.view_yaw))
			game._explode(world.eye + fwd * randf_range(12.0, 25.0) + Vector3(randf_range(-4, 4), -world.eye.y, 0), {"w": weapons.list[3]})
		if _auto.perf.size() >= 60:
			var f: Array = _auto.perf
			print("[perf] avg=%.1fms max=%.1fms draw_calls<=%d render_cpu=%.1fms triangles=%dk" % [f.reduce(func(a, b): return a + b) / f.size() * 1000.0,
				f.max() * 1000.0, _auto.calls, RenderingServer.viewport_get_measured_render_time_cpu(vrid), Performance.get_monitor(Performance.RENDER_TOTAL_PRIMITIVES_IN_FRAME) / 1000])
			_auto.perf = []
			_auto.calls = 0
	if _auto.get("god", false) and mode == "playing":
		game.hearts = maxi(game.hearts, 2)
	if _auto.has("phase") and game.state == "playing" and not _auto.has("phase_done"):
		_auto.phase_done = true
		match _auto.phase:
			"walk_out":
				game.time = 0.05
			"route", "walk_in", "square2":
				# --routeat: metres past the end of 't Pleintje's north street
				game._start_walk_out()
				var at: float = game._marks.leave + _auto.get("route_at", 0.0)
				if _auto.phase == "walk_in":
					at = game._marks.arrive - 4.0
				elif _auto.phase == "square2":
					at = game.rail.length
				game.rail.dist = at
				for ev in game.rail.events:
					ev.fired = ev.d < at - 25.0
				for st in game.rail.stops:
					st.done = st.d < at - 0.5
	if _auto.get("boss", false) and game.state == "playing" and not _auto.has("boss_started"):
		_auto.boss_started = true
		game.time = 0.05
	if _auto.get("skip_intro", false) and game.state == "boss_intro" and game.boss.state == "intro" and game.boss._intro.get("stage", "") != "card":
		game.boss.skip_intro()
	if _auto.get("play", false) and mode == "playing" and game.state == "boss":
		# aim at a random boss part and fire now and then
		var part = ["LegL", "LegR", "Torso", "ArmL", "ArmR", "Head"].filter(func(k): return game.boss.parts[k].alive and (k != "Head" or game.boss.head_open))
		if not part.is_empty():
			if not _auto.has("part") or not game.boss.parts[_auto.part].alive or fmod(_auto.t, 4.0) < dt:
				_auto.part = part.pick_random()
			var d = (game.boss._part_center(_auto.part) - world.eye).normalized()
			inp.yaw = atan2(-d.x, -d.z) - game.view_yaw
			inp.pitch = asin(d.y)
			if fmod(_auto.t, 0.5) < dt:
				inp.fire_pressed = true
				inp.fire_down = true
	elif _auto.get("play", false) and mode == "playing" and game.state == "playing":
		# aim at the nearest rider and fire every now and then
		var best = null
		for r in riders.list:
			var p: Vector3 = (r.root as Node3D).position
			var fwd := Vector3(-sin(game.view_yaw), 0, -cos(game.view_yaw))
			if (p - world.eye).dot(fwd) > 4 and r.alive and (best == null or p.distance_to(world.eye) < best.root.position.distance_to(world.eye)):
				best = r
		if best != null:
			var t: Vector3 = (best.model as Node3D).global_transform * Vector3(-0.07, 1.17, 0)
			var d = (t - world.eye).normalized()
			inp.yaw = wrapf(atan2(-d.x, -d.z) - game.view_yaw, -PI, PI)
			inp.pitch = asin(d.y)
			if weapons.current().get("auto", false):
				inp.fire_down = not _auto.get("knife", false)
			elif fmod(_auto.t, 1.2) < dt and not _auto.get("knife", false):
				inp.fire_pressed = true
		elif weapons.current().get("auto", false):
			inp.fire_down = false
	if _auto.get("knife", false) and game.state == "playing" and _auto.t > _auto.wait - 2.0 and not _auto.has("knife_done"):
		_auto.knife_done = true
		var near = riders.list.filter(func(r): return r.alive and (r.root as Node3D).position.distance_to(world.eye) < 30)
		if not near.is_empty():
			riders.start_windup(near[0], true)
	if _auto.get("bullet", false) and mode == "playing" and game.state == "playing" and _auto.t > _auto.wait - 1.2 and not game.bt.active:
		game.bt.meter = 1.0
		game.start_bullet_time()
	for st in _auto.get("shots", []).duplicate():
		if _auto.t >= st:
			_auto.shots.erase(st)
			get_viewport().get_texture().get_image().save_png(_auto.shot.replace(".png", "_%d.png" % int(st * 10)))
	if _auto.t >= _auto.wait:
		_auto.erase("play")
		var img = get_viewport().get_texture().get_image()
		img.save_png(_auto.shot)
		print("[auto] screenshot saved to ", _auto.shot, " riders=", riders.list.size(), " score=", game.score, " stats=", game.stats)
		get_tree().quit()
