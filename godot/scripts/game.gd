class_name Game
extends Node
## Round logic: shooting, projectiles, explosions, scoring, bullet time, hearts. Port of src/game.js.

signal ended(reason: String, score: int, stats: Dictionary)

const MULTI_NAMES := {2: "DUBBEL!", 3: "TRIPLE!", 4: "QUADRA!", 5: "MEGA!"}

var world: World
var riders: Riders
var weapons: Weapons
var effects: Effects
var hud: Hud
var camera: Camera3D

var state = "idle"  # idle | countdown | playing | boss_intro | boss | boss_won | fireworks | ended
var round_time := 60.0
var level: Dictionary = Config.LEVELS.normal
var level_key := "normal"
var time := 60.0
var score := 0
var hearts := 3
var max_hearts := 3
var stats := {}
var countdown := 0.0
var last_count := 99
var next_refill := 60.0
var bt := {"meter": 0.0, "active": false, "t": 0.0, "scale": 1.0}
var projectiles: Array = []
var tracers: Array = []
var boss: Fatbiketron
var market: Market
var _round_id := 0
var _tip_t := 0.0
var boss_on := true
var _show := {}   # fireworks show: {t, next, launched}
# adventure mode: square1 -> walk_out -> route -> walk_in -> square2 -> (leg 2: the same walk phases) -> square3
# (then the boss or fireworks)
var adventure := false
var phase := ""
var leg := 1          # which walk: 1 = 't Pleintje -> Donutplein, 2 = Donutplein -> Wollahbi
var _coaster_t := 0.0 # next fatbiker on the roller coaster
var rail: Rail
var view_yaw := 0.0   # the walking direction; the player's own look (inp.yaw) is relative to it
var _marks := {}      # distances along the walk where things change (see _start_walk)

const NO_SPAWN := {"spawn_interval": 99.0, "max_alive": 0, "attack_chance": 0.0, "speed_mul": 1.0}


func setup(w: World, r: Riders, wp: Weapons, fx: Effects, h: Hud, cam: Camera3D) -> void:
	world = w
	riders = r
	weapons = wp
	effects = fx
	hud = h
	camera = cam
	weapons.fire_hitscan.connect(fire_hitscan)
	weapons.fire_projectile.connect(fire_projectile)
	weapons.eject_shell.connect(_eject_shell)
	weapons.empty_mag.connect(func(): hud.message("LEEG!", 0.5))
	riders.player_hit.connect(on_player_hit)
	for n in [_stone(), _ice_scoop(Weapons.ICE_FLAVOURS[0]), _tracer_line(Vector3.ZERO, Vector3.FORWARD), riders._safety_flag()]:
		effects.warm(n)   # materials of their own: compile them before the first shot
	market = Market.new()
	world.add_child(market)
	market.setup(world, riders, effects)
	boss = Fatbiketron.new()
	world.add_child(boss)
	boss.setup(self, riders, effects, world.eye)
	boss.player_hit.connect(on_player_hit)


func reset(p_round_time: float, p_level: String, p_boss := true, p_adventure := false) -> void:
	boss_on = p_boss
	adventure = p_adventure
	phase = "square1" if adventure else ""
	leg = 1
	_coaster_t = 6.0
	rail = null
	view_yaw = 0.0
	riders.clear()
	effects.clear()
	market.clear()
	effects.water = []
	if adventure:
		p_round_time = Config.ADVENTURE.square_time
		Config.use_map("pleintje")
		world.load_adventure()   # the whole walk lives in one world, no loading on the way
		var w: Array = Config.ADVENTURE.water
		var a := Config.AP(w[0], [w[1][0], w[1][1]])
		var b := Config.AP(w[0], [w[1][2], w[1][3]])
		effects.water = [[Rect2(Vector2(minf(a.x, b.x), minf(a.z, b.z)), Vector2(absf(b.x - a.x), absf(b.z - a.z))), w[2]]]
		world.show_model("donut", false)
		world.show_model("wollahbi", false)
	elif world.is_adventure():
		world.load_map()
	world.hold_ijsje(null)
	hud.fade(0.0, 0.01)
	_set_player(world.seat, Vector3.ZERO, Vector3.FORWARD)
	round_time = p_round_time
	level_key = p_level
	level = Config.LEVELS[p_level]
	max_hearts = level.hearts
	riders.peaceful = level.get("chill", false)
	weapons.infinite = level.get("chill", false)
	riders.settings = {"accuracy": level.accuracy, "windup": level.windup}
	boss.settings = {"accuracy": level.accuracy, "windup": level.windup, "hp": level.boss_hp, "speed": level.speed,
		"peaceful": level.get("chill", false)}
	boss.reset()
	world.fold_parasol(false)
	world.set_dusk(false, 0.01)
	_show = {}
	_round_id += 1
	hud.show_boss(false)
	hud.set_cinematic(false)
	Sfx.restart_music(false)
	world.reset_ijsje()
	next_refill = 60.0
	riders.clear()
	effects.clear()
	for p in projectiles:
		p.node.queue_free()
	projectiles.clear()
	weapons.reset(Config.ADVENTURE.rockets if adventure else {60: 5, 180: 12, 300: 18}.get(int(round_time), 5))
	_end_bullet_time(true)
	bt = {"meter": 0.0, "active": false, "t": 0.0, "scale": 1.0}
	Sfx.set_intensity("game")
	score = 0
	time = round_time
	hearts = max_hearts
	stats = {"shots": 0, "hits": 0, "kills": 0, "headshots": 0, "knives": 0, "best_multi": 1, "bosses": 0,
		"boss_parts": 0, "boss_win": false, "boss_on": boss_on, "adventure": adventure, "ambushes": 0}
	countdown = 3.6
	last_count = 99
	state = "countdown"
	hud.set_hearts(hearts, max_hearts)
	hud.set_score(0)
	hud.set_time(time)


func elapsed() -> float:
	return round_time - time


func time_scale() -> float:
	return bt.scale


func bullet_amount() -> float:
	return (1.0 - bt.scale) / (1.0 - Config.BULLET_TIME.scale)


func pts(n: float) -> int:
	return roundi(n * level.score)


# ------------------------------------------------------------ bullet time

func fill_meter(x: float) -> void:
	if bt.active or state != "playing":
		return
	var was: float = bt.meter
	bt.meter = minf(1.0, was + x * level.bt_fill)
	if was < 1.0 and bt.meter >= 1.0:
		Sfx.ready_sound()
		effects.popup_screen("BULLET TIME KLAAR!" if Config.is_touch() else "BULLET TIME KLAAR! [B]", "bonus", 0.5, 0.78, 1.6)


func start_bullet_time() -> void:
	if bt.active or bt.meter < 1.0 or state != "playing":
		return
	bt.active = true
	bt.t = Config.BULLET_TIME.duration
	Sfx.bullet_in()
	Sfx.set_slow(true)
	hud.set_bullet(true)


func _end_bullet_time(silent := false) -> void:
	if not bt.active:
		return
	bt.active = false
	bt.meter = 0.0
	if not silent:
		Sfx.bullet_out()
	Sfx.set_slow(false)
	hud.set_bullet(false)


# ------------------------------------------------------------ shooting

func fire_hitscan(w: Dictionary, origin: Vector3, dirs: Array, muzzle) -> void:
	stats.shots += 1
	var per_rider = {}
	var boss_hits = {}
	var any_hit = false
	var first_end = null
	for dir in dirs:
		var wh = world.raycast(origin, dir, w.range)
		var limit: float = wh.distance if not wh.is_empty() else w.range
		var rh = riders.raycast(origin, dir, limit)
		var kh = riders.raycast_knives(origin, dir, limit)
		if not kh.is_empty() and (rh.is_empty() or kh[0].t < rh[0].t):
			_knife_shot(kh[0].knife)
			any_hit = true
			continue
		var mh = market.raycast(origin, dir, limit)
		if not mh.is_empty() and (rh.is_empty() or mh.t < rh[0].t):
			_produce_shot(mh.item)
			any_hit = true
			continue
		var ph = boss.raycast_projectiles(origin, dir, limit)
		var bh = boss.raycast(origin, dir, limit)
		if not ph.is_empty() and (bh.is_empty() or ph[0].t < bh.t):
			_boss_proj_shot(ph[0].proj)
			any_hit = true
			continue
		if not bh.is_empty() and (rh.is_empty() or bh.t < rh[0].t):
			var be: Dictionary = boss_hits.get(bh.part, {"dmg": 0.0, "point": bh.point})
			be.dmg += w.damage
			boss_hits[bh.part] = be
			if first_end == null:
				first_end = bh.point
			continue
		var hits = []
		if w.has("pierce"):
			var seen = {}
			for h in rh:
				if not seen.has(h.rider.id):
					seen[h.rider.id] = true
					hits.append(h)
			hits = hits.slice(0, w.pierce)
		elif not rh.is_empty():
			hits = [rh[0]]
		for h in hits:
			var e: Dictionary = per_rider.get(h.rider.id, {"rider": h.rider, "dmg": 0.0, "head": false, "point": h.point, "dir": dir})
			e.dmg = minf(e.dmg + w.damage, w.get("max_per_rider", INF))
			e.head = e.head or h.part == "head"
			per_rider[h.rider.id] = e
		var end_pt: Vector3
		if not hits.is_empty() and not w.has("pierce"):
			end_pt = hits[0].point
		elif not wh.is_empty():
			end_pt = wh.position
		else:
			end_pt = origin + dir * limit
		if first_end == null:
			first_end = end_pt
		if hits.is_empty() and not wh.is_empty():
			effects.puff(wh.position, Color("d8cbb5"), 1 if w.pellets > 1 else 4, 0.25 if w.pellets > 1 else 0.5)
			market.shot(wh.collider, wh.position, dir)
	if muzzle != null:
		effects.muzzle_flash(muzzle, 0.7 if w.key == "shotgun" else 0.55)
		if w.key == "sniper" and first_end != null:
			_tracer(muzzle, first_end)
	for part in boss_hits:
		var be: Dictionary = boss_hits[part]
		var dmg: float = minf(be.dmg, 4.0) * (1.5 if part == "Head" and w.key == "sniper" else 1.0)
		if _boss_hit(part, dmg, be.point):
			any_hit = true
	var kills = []
	for id in per_rider:
		var e: Dictionary = per_rider[id]
		var r: Dictionary = e.rider
		any_hit = true
		hud.hit(e.head)
		Sfx.hit(e.head)
		var power = 9.0 if w.key == "shotgun" else (8.0 if w.key == "sniper" else 5.0)
		if riders.damage(r, e.dmg, e.dir, power):
			kills.append({"rider": r, "head": e.head, "point": e.point})
	if not kills.is_empty():
		_score_kills(kills)
		for k in kills:   # knocked off next to a stall: the goods go with him
			market.bump(k.point, 1.0, 5.0)
	_after_shot(any_hit)


func fire_projectile(w: Dictionary, muzzle: Vector3, origin: Vector3, fwd: Vector3) -> void:
	stats.shots += 1
	var wh = world.raycast(origin, fwd, 250.0)
	var rh = riders.raycast(origin, fwd, wh.distance if not wh.is_empty() else 250.0)
	var aim_dist: float = rh[0].t if not rh.is_empty() else (wh.distance if not wh.is_empty() else 120.0)
	var bh0 = boss.raycast(origin, fwd, aim_dist)
	if not bh0.is_empty():
		aim_dist = bh0.t
	var aim = origin + fwd * aim_dist
	var p: Dictionary = w.projectile
	if not rh.is_empty() and rh[0].rider.alive:  # arcade lead
		var r: Dictionary = rh[0].rider
		var rv = Vector3(cos(r.yaw), 0, -sin(r.yaw)) * r.speed
		var base = aim
		for i in 2:
			aim = base + rv * (aim.distance_to(muzzle) / p.speed)
	var dir = (aim - muzzle).normalized()
	if w.has("spread"):   # spray around the (lead-corrected) aim point
		dir = Weapons._jitter(dir, w.spread)
	var T = aim.distance_to(muzzle) / p.speed
	var vel = dir * p.speed + Vector3(0, 0.5 * p.gravity * T, 0)
	var node: Node3D
	if w.key == "bazooka":
		node = Node3D.new()
		var rocket: Node3D = w.parts.rocket.duplicate()
		rocket.visible = true
		rocket.transform = Transform3D.IDENTITY
		rocket.position = Vector3(-0.78, 0, 0)
		node.add_child(rocket)
		effects.puff(muzzle - fwd * 1.2, Color("cccccc"), 6, 0.8)
		effects.flash_light(muzzle, Color("ffaa55"), 5.0, 0.1)
	elif p.has("ice"):
		var flavour: String = Weapons.ICE_FLAVOURS.pick_random()
		node = _ice_scoop(flavour)
		world.add_child(node)
		node.global_position = muzzle
		projectiles.append({"node": node, "vel": vel, "w": w, "age": 0.0, "trail": 0.0, "hit_any": false, "flavour": flavour})
		return
	else:
		node = _stone()
	world.add_child(node)
	node.global_position = muzzle
	projectiles.append({"node": node, "vel": vel, "w": w, "age": 0.0, "trail": 0.0, "hit_any": false})


## A catapult stone.
func _stone() -> MeshInstance3D:
	var mi = MeshInstance3D.new()
	var sm = SphereMesh.new()
	sm.radius = 0.06
	sm.height = 0.12
	mi.mesh = sm
	var mat = StandardMaterial3D.new()
	mat.albedo_color = Color("8c8a83")
	mat.roughness = 0.85
	mi.material_override = mat
	return mi


var _ice_mesh: SphereMesh
var _ice_mats := {}


## One scoop of ice cream (shared mesh, one material per flavour).
func _ice_scoop(flavour: String) -> MeshInstance3D:
	if _ice_mesh == null:
		_ice_mesh = SphereMesh.new()
		_ice_mesh.radius = 0.085
		_ice_mesh.height = 0.15
		_ice_mesh.radial_segments = 12
		_ice_mesh.rings = 6
	if not _ice_mats.has(flavour):
		var m := StandardMaterial3D.new()
		m.albedo_color = Color(flavour)
		m.roughness = 0.6
		m.rim_enabled = true
		m.rim = 0.4
		_ice_mats[flavour] = m
	var mi := MeshInstance3D.new()
	mi.mesh = _ice_mesh
	mi.material_override = _ice_mats[flavour]
	mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	return mi


func _update_projectiles(dt: float) -> void:
	for i in range(projectiles.size() - 1, -1, -1):
		var p: Dictionary = projectiles[i]
		var d: Dictionary = p.w.projectile
		var node: Node3D = p.node
		p.age += dt
		var prev = node.global_position
		p.vel.y -= d.gravity * dt
		var next: Vector3 = prev + p.vel * dt
		var seg = next - prev
		var length = seg.length()
		var dir = seg / maxf(length, 0.0001)
		if p.w.key == "bazooka":
			node.basis = Basis(Quaternion(Vector3.RIGHT, dir))
			p.trail -= dt
			if p.trail <= 0:
				p.trail = 0.025
				effects.smoke_trail(prev)
		else:
			node.rotation.x += dt * 15.0
		var wh = world.raycast(prev, dir, length + d.radius)
		var rh = riders.raycast(prev, dir, wh.distance if not wh.is_empty() else length + d.radius, 0.2)
		var kh = riders.raycast_knives(prev, dir, length + 0.2)
		var mh = market.raycast(prev, dir, length + 0.2)
		if not mh.is_empty():
			_produce_shot(mh.item)
			p.hit_any = true
		var ph = boss.raycast_projectiles(prev, dir, length + 0.4)
		var bh = boss.raycast(prev, dir, wh.distance if not wh.is_empty() else length + d.radius)
		var done = false
		if not kh.is_empty():
			_knife_shot(kh[0].knife)
			p.hit_any = true
		if not ph.is_empty():
			var at: Vector3 = (ph[0].proj.node as Node3D).global_position
			_boss_proj_shot(ph[0].proj)
			p.hit_any = true
			if d.has("explode"):
				_explode(at, p)
			done = true
		elif not bh.is_empty() and (rh.is_empty() or bh.t < rh[0].t):
			if d.has("explode"):
				_explode(bh.point, p)
			elif _boss_hit(bh.part, d.damage * d.get("boss_mul", 1.0), bh.point):
				p.hit_any = true
			if d.has("ice"):
				_ice_splat(p, bh.point, true)
			done = true
		elif not rh.is_empty():
			var h: Dictionary = rh[0]
			if d.has("explode"):
				_explode(h.point, p)
			else:
				p.hit_any = true
				hud.hit(h.part == "head")
				Sfx.hit(h.part == "head")
				if d.has("ice"):
					_ice_splat(p, h.point, true)
					riders.freeze(h.rider, h.point, Color(p.flavour), _ice_scoop(p.flavour))
				if riders.damage(h.rider, d.damage, dir, 6.0, not d.has("ice")):
					_score_kills([{"rider": h.rider, "head": h.part == "head", "point": h.point}])
			done = true
		elif not wh.is_empty() or next.y < 0 or p.age > 4.0:
			var at: Vector3 = wh.position if not wh.is_empty() else next
			if not wh.is_empty() and not d.has("explode"):
				market.shot(wh.collider, at, dir)
			if d.has("explode"):
				_explode(at, p)
			elif d.has("ice"):
				_ice_splat(p, at, false)
			else:
				effects.puff(at, Color("b9a98f"), 3, 0.3)
			done = true
		if done:
			node.queue_free()
			projectiles.remove_at(i)
			if not d.has("explode"):
				_after_shot(p.hit_any)
		else:
			node.global_position = next


func _ice_splat(p: Dictionary, at: Vector3, hit: bool) -> void:
	effects.splat(at, Color(p.flavour), hit)
	if hit or randf() < 0.3:
		Sfx.splat(at.distance_to(camera.global_position))


func _explode(point: Vector3, p: Dictionary) -> void:
	effects.explosion(point)
	Sfx.explosion(point.distance_to(camera.global_position))
	var R: float = p.w.projectile.explode
	market.bump(point, R, 9.0)
	var kills = []
	for r in riders.in_radius(point, R):
		var dir: Vector3 = (r.root as Node3D).position - point
		dir.y = 0
		if dir.length_squared() < 0.01:
			dir = Vector3(randf() - 0.5, 0, randf() - 0.5)
		r.hp = 0
		riders.knock_off(r, dir.normalized(), 10.0, true)
		kills.append({"rider": r, "head": false, "point": (r.root as Node3D).position + Vector3(0, 1.2, 0)})
	for k in riders.knives.duplicate():
		if (k.mesh as Node3D).global_position.distance_to(point) < R:
			_knife_shot(k)
	for bp in boss.projectiles.duplicate():
		if (bp.node as Node3D).global_position.distance_to(point) < R:
			_boss_proj_shot(bp)
	var boss_hit = false
	for part in boss.parts_in_radius(point, R):
		boss_hit = _boss_hit(part, 7.0, point) or boss_hit
	if not kills.is_empty():
		hud.hit(false)
		_score_kills(kills)
	_after_shot(not kills.is_empty() or boss_hit)


func _after_shot(hit: bool) -> void:
	if hit:
		stats.hits += 1
	elif state == "playing" and randf() < level.retaliate:
		riders.retaliate()


func _produce_shot(f: Dictionary) -> void:
	var at: Vector3 = (f.node as Node3D).global_position
	var res: Array = market.pop(f)
	var n := pts(res[0])
	_add_score(n, at, "%s +%d" % [res[1], n], "bonus")


func _knife_shot(k: Dictionary) -> void:
	var pos: Vector3 = (k.mesh as Node3D).global_position
	riders.destroy_knife(k)
	stats.knives += 1
	fill_meter(Config.BULLET_TIME.fill_knife)
	var kp = pts(Config.SCORE.knife)
	_add_score(kp, pos, "MES GERAAKT! +%d" % kp, "bonus")
	Sfx.clank()
	hud.hit(false)


# ------------------------------------------------------------ boss

func _boss_proj_shot(p: Dictionary) -> void:
	var rocket: bool = p.kind == "rocket"
	var pos = boss.destroy_projectile(p)
	stats.knives += 1
	fill_meter(Config.BULLET_TIME.fill_knife)
	var kp = pts(Config.SCORE.rocket if rocket else Config.SCORE.knife)
	_add_score(kp, pos, ("RAKET NEERGESCHOTEN! +%d" if rocket else "BAND GERAAKT! +%d") % kp, "bonus")
	hud.hit(false)


## Damage one boss part; returns true when it counted as a hit.
func _boss_hit(part: String, dmg: float, point: Vector3) -> bool:
	var res: Dictionary = boss.damage(part, dmg, point)
	match res.result:
		"hit":
			hud.hit(part == "Head")
			Sfx.hit(part == "Head")
			_add_score(pts(Config.SCORE.boss_hit * dmg), point)
			fill_meter(0.02 * dmg)
			return true
		"armor":
			hud.hit(false)
			Sfx.clank()
			return false
		"broken", "dead":
			var head = res.result == "dead"
			var p = pts((Config.SCORE.boss_head if head else Config.SCORE.boss_part) * (Config.BULLET_TIME.bonus if bt.active else 1.0))
			stats.boss_parts += 1
			hud.hit(true)
			Sfx.hit(true)
			Sfx.cheer()
			fill_meter(0.35)
			_add_score(p, point, "+%d" % p, "bonus")
			if not head:
				effects.popup_screen("%s ERAF!" % Fatbiketron.PART_NAMES[part], "big", 0.5, 0.3, 1.6)
				if boss.bikes_left() == 0:
					effects.popup_screen("HET HOOFD IS KWETSBAAR!", "bonus", 0.5, 0.42, 2.2)
			return true
	return false


# ------------------------------------------------------------ survived without the boss: fireworks

const SHOW_LENGTH := 7.5


func start_fireworks() -> void:
	view_yaw = 0.0
	state = "fireworks"
	time = 0.0
	hud.set_time(0)
	_end_bullet_time(true)
	bt.scale = 1.0
	riders.flee(["VUURWERK!", "OEEEH!", "MOOI HOOR!", "IK BEN BANG VOOR KNALLEN!", "AAAH, MIJN OREN!"])
	hud.message("OVERLEEFD!", 1.8)
	Sfx.cheer()
	world.fold_parasol(true)
	world.set_dusk(true)
	_show = {"t": 0.0, "next": 1.2}


func _step_fireworks(dt: float, inp) -> void:
	_show.t += dt
	riders.step(dt, NO_SPAWN, elapsed())
	weapons.step(dt, inp)
	_update_projectiles(dt)
	# look up at the sky above the square
	inp.yaw = lerp_angle(inp.yaw, 0.0, minf(1.0, dt * 1.5))
	inp.pitch = lerpf(inp.pitch, 0.32, minf(1.0, dt * 1.5))
	if _show.t >= _show.next and _show.t < SHOW_LENGTH - 1.8:
		_show.next += randf_range(0.25, 0.6)
		var from = Vector3(world.seat.x + randf_range(-16, 16), 2.0, world.seat.z + randf_range(-41.5, -27.5))
		effects.firework(from, randf_range(17, 27), ["ball", "ball", "ring", "willow"].pick_random())
		if randf() < 0.25:  # sometimes a pair
			effects.firework(from + Vector3(randf_range(-4, 4), 0, 0), randf_range(17, 27), "ball")
	if _show.t >= SHOW_LENGTH:
		end_round("OVERLEEFD!")


func start_boss() -> void:
	view_yaw = 0.0
	boss.player_eye = world.eye
	state = "boss_intro"
	time = 0.0
	hud.set_time(0)
	_end_bullet_time(true)
	bt.scale = 1.0
	riders.flee()
	hud.message("TIJD OP!", 1.3)
	Sfx.end_round()
	Sfx.fade_music_out(1.6)
	hud.set_cinematic(true)
	weapons.root.visible = false
	world.fold_parasol(true)
	boss.start_intro()


func _step_boss_intro(dt: float, inp) -> void:
	riders.step(dt, NO_SPAWN, elapsed())
	boss.step(dt)
	var d: Vector3 = (boss.cam_focus - camera.global_position).normalized()
	inp.yaw = lerp_angle(inp.yaw, atan2(-d.x, -d.z), minf(1.0, dt * 2.2))
	inp.pitch = lerpf(inp.pitch, asin(d.y), minf(1.0, dt * 2.2))
	inp.zoom_toggle = false
	weapons.root.visible = false
	if inp.fire_pressed or inp.keys_pressed.has(KEY_SPACE) or inp.keys_pressed.has(KEY_ENTER):
		boss.skip_intro()
	hud.set_score(score)


## Called by the boss when its name card appears.
func boss_card() -> void:
	hud.boss_card("FATBIKETRON", "5 fatbikes · 1 doel: jouw ijsje")


## Called by the boss when the intro is over.
func boss_fight_start() -> void:
	state = "boss"
	hud.set_cinematic(false)
	hud.show_boss(true)
	Sfx.restart_music(true)
	Sfx.go()
	var healed = hearts < max_hearts
	if healed:
		hearts += 1
		hud.set_hearts(hearts, max_hearts)
	world.reset_ijsje()
	weapons.add_rockets(3)
	hud.message("VERSLA HEM!", 1.2)
	effects.popup_screen("OBER: VERS IJSJE%s + 3 RAKETTEN!" % (" +1 ♥" if healed else ""), "bonus", 0.5, 0.72, 2.6)


## Called by the boss when it has fallen apart.
func boss_defeated() -> void:
	if state != "boss":
		return
	state = "boss_won"
	stats.boss_win = true
	var bonus = pts(Config.SCORE.boss_win + Config.SCORE.boss_heart * hearts)
	score += bonus
	hud.show_boss(false)
	effects.popup_screen("FATBIKETRON VERSLAGEN!", "big", 0.5, 0.3, 2.6)
	effects.popup_screen("BONUS +%d" % bonus, "bonus", 0.5, 0.45, 2.6)
	Sfx.cheer()
	var id = _round_id
	get_tree().create_timer(2.8).timeout.connect(func(): if id == _round_id and state == "boss_won": end_round("PLEIN BEVRIJD!"))


func _eject_shell(shell: Node3D) -> void:
	if shell == null:
		return
	var c: Node3D = shell.duplicate()
	c.visible = true
	world.add_child(c)
	c.global_transform = shell.global_transform
	var right = camera.global_basis.x
	effects.add_debris(c, c.global_position, right * 2.5 + Vector3(0, 2.5, 0), Vector3(randf() * 20, randf() * 20, 0), {"radius": 0.02, "life": 1.5, "bounce": 0.5})


func _tracer(from: Vector3, to: Vector3) -> void:
	var mi := _tracer_line(from, to)
	world.add_child(mi)
	tracers.append({"node": mi, "age": 0.0})


func _tracer_line(from: Vector3, to: Vector3) -> MeshInstance3D:
	var mi = MeshInstance3D.new()
	var im = ImmediateMesh.new()
	im.surface_begin(Mesh.PRIMITIVE_LINES)
	im.surface_add_vertex(from)
	im.surface_add_vertex(to)
	im.surface_end()
	mi.mesh = im
	var m = StandardMaterial3D.new()
	m.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	m.albedo_color = Color("fff2b0")
	m.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	mi.material_override = m
	return mi


# ------------------------------------------------------------ scoring

func _add_score(n: int, pos: Vector3, text := "", cls := "") -> void:
	score = maxi(0, score + n)
	if text != "":
		effects.popup_world(pos + Vector3(0, 0.6, 0), text, cls, 1.1)


func _score_kills(kills: Array) -> void:
	var bodies = 0
	for k in kills:
		var r: Dictionary = k.rider
		var n = 2 if r.type == "duo" else 1
		bodies += n
		var points: float = Config.SCORE.boss if r.type == "boss" else Config.SCORE.kill * n * (Config.SCORE.wheelie_mul if r.type == "wheelie" else 1)
		if r.get("air", false):
			points += Config.SCORE.coaster
		if k.head:
			points += Config.SCORE.headshot
		if bt.active:
			points = roundf(points * Config.BULLET_TIME.bonus)
		var p = pts(points)
		fill_meter(Config.BULLET_TIME.fill_kill * n + (Config.BULLET_TIME.fill_head if k.head else 0.0))
		stats.kills += n
		if k.head:
			stats.headshots += 1
		if r.type == "boss":
			stats.bosses += 1
		var label = ("SPEAKER-BAAS! +%d" % p) if r.type == "boss" else (("HEADSHOT! +%d" % p) if k.head else "+%d" % p)
		if r.get("air", false):
			label = "VAN DE ACHTBAAN! +%d" % p
		if bt.active:
			label = "SLOWMO " + label
		_add_score(p, k.point, label, "bonus" if k.head or r.type == "boss" or r.get("air", false) else "")
	if bodies >= 2:
		var bonus = pts(Config.SCORE.multi * (bodies - 1))
		score += bonus
		stats.best_multi = maxi(stats.best_multi, bodies)
		effects.popup_screen("%s +%d" % [MULTI_NAMES[mini(bodies, 5)], bonus], "big", 0.5, 0.3, 1.3)
		Sfx.cheer()


func on_player_hit(knife_vel: Vector3, reason := "NEERGESTOKEN!") -> void:
	if state != "playing" and state != "boss":
		return
	if level.get("chill", false):   # can't be hit: nothing to lose
		return
	hearts -= 1
	hud.set_hearts(hearts, max_hearts)
	hud.hurt()
	effects.add_shake(1.0)
	Sfx.hurt()
	var fell = world.ijsje_fall.is_empty()
	effects.popup_screen("NEE, MIJN IJSJE!" if fell else ("AUWW! LAATSTE LEVEN!" if hearts == 1 else "AU!"), "bad", 0.5, 0.55, 1.0)
	if fell:
		world.knock_over_ijsje(Vector3(knife_vel.x, 0, knife_vel.z).normalized())
	if hearts <= 0:
		end_round(reason)


# ------------------------------------------------------------ loop

func step(dt: float, inp) -> void:
	# riders only throw from where you can aim, with a margin so the throw isn't on the very edge of the view
	riders.cone_yaw = view_yaw
	riders.cone_half = yaw_limit() - deg_to_rad(30.0 if rail and rail.stop != null else 15.0)
	riders.throw_gap = 1.0 if rail else 0.0
	for i in range(tracers.size() - 1, -1, -1):
		var t: Dictionary = tracers[i]
		t.age += dt
		(t.node as GeometryInstance3D).transparency = t.age / 0.18
		if t.age > 0.18:
			t.node.queue_free()
			tracers.remove_at(i)
	if state == "countdown":
		countdown -= dt
		var c = ceili(countdown - 0.6)
		if c != last_count:
			last_count = c
			if c > 0:
				hud.message(str(c), 0.8)
				Sfx.tick()
			else:
				hud.message("SCHIETEN!", 0.9)
				Sfx.go()
		if countdown <= 0.6:
			state = "playing"
		weapons.step(dt, inp)
		return
	if state == "boss_intro":
		_step_boss_intro(dt, inp)
		return
	if state == "fireworks":
		_step_fireworks(dt, inp)
		return
	if state != "playing" and state != "boss" and state != "boss_won":
		return
	var fighting: bool = state != "playing"
	if inp.keys_pressed.has(KEY_B) or inp.keys_pressed.has(KEY_SPACE):
		start_bullet_time()
	if bt.active:
		bt.t -= dt
		if bt.t <= 0:
			_end_bullet_time()
	var target: float = Config.BULLET_TIME.scale if bt.active else 1.0
	bt.scale += (target - bt.scale) * minf(1.0, dt * 9.0)
	if absf(bt.scale - target) < 0.002:
		bt.scale = target
	var gdt: float = dt * bt.scale
	world.set_time_scale(bt.scale)
	hud.set_meter(bt.t / Config.BULLET_TIME.duration if bt.active else bt.meter, bt.active)

	var walking := phase == "walk_out" or phase == "route" or phase == "walk_in"
	if fighting:
		riders.step(gdt, NO_SPAWN, elapsed())
		boss.step(gdt)
		if state == "boss":
			hud.set_boss(boss.bar_state())
	elif walking:
		_step_walk(gdt, inp)
	else:
		var prev_sec = ceili(time)
		time -= gdt
		if ceili(time) != prev_sec and time <= 5 and time > 0:
			Sfx.tick()
		var intensity := Config.round_intensity(elapsed(), round_time)
		var later := phase == "square2" or phase == "square3"
		if later:   # the later squares of the adventure start busy
			intensity = maxf(intensity, 0.55 if phase == "square2" else 0.65)
		var diff = Config.difficulty(intensity, level)
		if round_time > 60 and elapsed() >= next_refill and time > 5:
			next_refill += 60
			var healed = hearts < max_hearts
			if healed:
				hearts += 1
				hud.set_hearts(hearts, max_hearts)
			world.reset_ijsje()
			effects.popup_screen("OBER: NIEUW IJSJE! +1 ♥" if healed else "OBER: NIEUW IJSJE!", "bonus", 0.5, 0.7, 2.0)
			Sfx.ready_sound()
		riders.step(gdt, diff, elapsed() + (60.0 if later else 0.0))
		_step_coaster(gdt)
	weapons.step(dt, inp)
	weapons.try_fire(inp)
	_update_projectiles(dt * maxf(bt.scale, 0.5))
	hud.set_score(score)
	if phase == "square2" or phase == "square3":   # just sat down: turn back to the square
		view_yaw = lerp_angle(view_yaw, 0.0, minf(1.0, dt * 2.0))
	if not fighting and not walking:
		hud.set_time(time)
		if time <= 0:
			if phase == "square1":
				_start_walk_out(1)
			elif phase == "square2":
				_start_walk_out(2)
			elif boss_on:
				start_boss()
			else:
				start_fireworks()


# ------------------------------------------------------------ adventure mode

## How far the player may look away from the walking direction.
func yaw_limit() -> float:
	if rail and rail.stop != null:
		return deg_to_rad(85.0)
	if rail:
		return deg_to_rad(62.0)
	return Config.YAW_LIMIT


func _set_player(eye: Vector3, vel: Vector3, fwd: Vector3) -> void:
	world.eye = eye
	riders.player_eye = eye
	riders.player_vel = vel
	riders.player_fwd = fwd


## A rider spec from Config.ADVENTURE: [delay, type, path, attacks?, frame?] (frame defaults to the route).
func _spawn_scripted(spec: Array) -> Dictionary:
	var frame: String = spec[4] if spec.size() > 4 else "route"
	var pts := []
	var hops := []
	var path = spec[2]
	if path is Dictionary:
		path = _loop_path(path)
	for p in path:
		var v := Config.AP(frame, p)
		if p.size() > 2 and not pts.is_empty():
			hops.append([pts[-1], v, float(p[2])])
		pts.append(v)
	var chance := minf(0.95, 0.55 + 0.3 * level.attack)
	return riders.spawn_path(spec[1], pts, level.speed, 17.0 if spec[3] and randf() < chance else 0.0, hops)


## {"loop": [cx, cy, rx, ry, laps], "from": [...], "to": [...], "ccw"?} -> points: in, round and round, out.
func _loop_path(d: Dictionary) -> Array:
	var c: Array = d.loop
	var pts: Array = d.from.duplicate()
	var last: Array = pts[-1]
	var a0 := atan2((last[1] - c[1]) / c[3], (last[0] - c[0]) / c[2])
	var dir := -1.0 if d.get("ccw", false) else 1.0
	var n := int(12 * c[4])
	for i in range(1, n + 1):
		var a := a0 - dir * TAU * i / 12.0
		pts.append([c[0] + cos(a) * c[2], c[1] + sin(a) * c[3]])
	pts.append_array(d.to)
	return pts


## The walks between the squares. Leg 1 is the top level of Config.ADVENTURE (frames route/pleintje/donut),
## leg 2 is ADVENTURE.leg2. Returns the walk's data with the frames filled in.
func _leg_data(n: int) -> Dictionary:
	var A: Dictionary = Config.ADVENTURE
	if n == 1:
		return {"from": "pleintje", "to": "donut", "frame": "route", "walk": A.walk, "end_look": A.end_look, "leave": A.leave,
			"arrive": A.arrive, "hide": A.hide_pleintje, "show": A.show_donut, "stops": A.stops, "events": A.events,
			"title": "IJSJE MEE, OP NAAR HET DONUTPLEIN!"}
	var d: Dictionary = A.leg2.duplicate()
	d.merge({"from": "donut", "to": "wollahbi", "frame": "donut", "title": "IJSJE MEE, OP NAAR WOLLAHBI!"})
	return d


## A rider list with each spec's frame attached (for _spawn_scripted).
static func _with_frame(riders: Array, frame: String) -> Array:
	return riders.map(func(rd): return rd.slice(0, 4) + [frame])


func _start_walk_out(n := 1) -> void:
	leg = n
	phase = "walk_out"
	time = 0.0
	_end_bullet_time(true)
	bt.scale = 1.0
	var L := _leg_data(n)
	var pts := []
	for seg in L.walk:
		for p in seg[1]:
			pts.append(Config.AP(seg[0], p))
	var stops := []
	for st in L.stops:
		var fr: String = st.get("frame", L.frame)
		stops.append({"at": Config.AP(fr, st.at), "look": Config.AP(fr, st.look), "min": st.min, "max": st.max,
			"title": st.title, "riders": _with_frame(st.riders, fr)})
	var events := []
	for ev in L.events:
		var fr: String = ev.get("frame", L.frame)
		events.append({"at": Config.AP(fr, ev.at), "riders": _with_frame(ev.riders, fr)})
	rail = Rail.new({"pts": pts, "speed": L.get("speed", Config.ADVENTURE.speed), "end_look": Config.AP(L.end_look[0], L.end_look[1]),
		"stops": stops, "events": events}, _spawn_scripted)
	_marks = {"from": L.from, "to": L.to, "speed": L.get("speed", Config.ADVENTURE.speed)}
	for k in ["leave", "arrive", "hide", "show"]:
		_marks[k] = rail.offset_of(Config.AP(L[k][0], L[k][1]))
	world.hold_ijsje(camera)
	hud.message("OPSTAAN!", 1.3)
	effects.popup_screen(L.title, "bonus", 0.5, 0.7, 2.4)
	Sfx.go()


func _step_walk(gdt: float, inp) -> void:
	var ev := rail.step(gdt)
	_set_player(rail.eye, rail.vel, rail.forward())
	view_yaw = rail.view_yaw
	# keep the player's look inside the cone around the walking direction
	var lim := yaw_limit()
	inp.yaw = move_toward(inp.yaw, clampf(inp.yaw, -lim, lim), gdt * 2.5)
	match ev:
		"stop":
			_ambush_start()
		"go", "go_clean":
			stats.ambushes += 1
			if hearts < max_hearts:   # made it through: a breather
				hearts += 1
				hud.set_hearts(hearts, max_hearts)
				effects.popup_screen("+1 ♥", "bonus", 0.5, 0.5, 1.8)
			if ev == "go_clean":
				var bonus := pts(1500)
				score += bonus
				effects.popup_screen("HINDERLAAG OVERLEEFD!", "big", 0.5, 0.3, 2.2)
				effects.popup_screen("+%d" % bonus, "bonus", 0.5, 0.42, 2.2)
				Sfx.cheer()
			else:
				effects.popup_screen("DOORLOPEN!", "bonus", 0.5, 0.36, 1.4)
	# the world along the way: squares and streets switch over without a break
	var d := rail.dist
	if phase == "walk_out" and d >= _marks.leave:
		phase = "route"
	if phase == "route" and d >= _marks.arrive:
		phase = "walk_in"
		Config.use_map(_marks.to, Config.AP(_marks.to, [0, 0]))
	rail.speed = _marks.speed * (1.0 if phase == "route" else 1.3)   # brisker across the squares
	world.show_model(_marks.from, d < _marks.hide)
	world.show_model(_marks.to, d >= _marks.show)
	var diff = NO_SPAWN
	if phase == "walk_out":   # the square keeps going behind you, a bit calmer
		diff = Config.difficulty(0.6, level)
		diff.spawn_interval *= 1.6
	elif phase == "walk_in":
		diff = Config.difficulty(0.3, level)
	riders.step(gdt, diff, round_time)
	if rail.stop != null:
		hud.set_timer_text("NOG %d" % rail.stop_left())
	else:
		hud.set_timer_text("%d m" % ceili(rail.remaining()))
	if rail.done:
		_sit_down()


## Now and then a fatbiker rides the roller coaster (one lap from the station): shoot him off for a bonus.
func _step_coaster(gdt: float) -> void:
	var c := world.coaster()
	if c == null:
		return
	_coaster_t -= gdt
	if _coaster_t > 0.0:
		return
	var start := c.lift_offset()   # at the foot of the lift, so you see him climb
	# he rides slower than the train: only set off once the train is well ahead, so it never catches him up
	var ahead := fposmod(c.head - start, c.length)
	if ahead < 40.0 or ahead > c.length * 0.6:
		return
	_coaster_t = randf_range(10.0, 16.0)
	var track := c.path_points(start, c.length - 10.0)
	var r := riders.spawn_rails(["normal", "normal", "wheelie", "duo"].pick_random(), track, func(d): return c.speed_at(start + d) * 0.75)
	effects.bubble(r.root, Vector3(0, 2.5, 0), ["JIHAAA!", "Kijk mij nou!", "Zonder handen!", "Fatbike-achtbaan!"].pick_random(), false, 4.0)
	effects.popup_screen("FATBIKER OP DE ACHTBAAN! +%d" % pts(Config.SCORE.coaster), "bonus", 0.5, 0.2, 2.4)
	Sfx.warn()


## An ambush begins: a bit of spectacle and the means to deal with it.
func _ambush_start() -> void:
	effects.popup_screen(rail.stop.title, "big", 0.5, 0.3, 2.4)
	Sfx.warn()
	Sfx.roar()
	effects.add_shake(0.6)
	weapons.add_rockets(2)
	if not bt.active:
		bt.meter = 1.0
		hud.set_meter(1.0, false)
	effects.popup_screen("+2 RAKETTEN · BULLET TIME KLAAR!", "bonus", 0.5, 0.72, 2.4)


func _sit_down() -> void:
	phase = "square2" if leg == 1 else "square3"
	rail = null
	world.activate(_marks.to)
	for id in world.models:
		world.show_model(id, id == _marks.to)
	_set_player(world.seat, Vector3.ZERO, Vector3.FORWARD)
	world.hold_ijsje(null)
	world.reset_ijsje()
	var healed = hearts < max_hearts
	if healed:
		hearts += 1
		hud.set_hearts(hearts, max_hearts)
	time = Config.ADVENTURE.square_time
	round_time = time
	next_refill = INF
	effects.popup_screen("%s: VERS IJSJE!%s" % ["HENRI" if leg == 1 else "IJSKIOSK", " +1 ♥" if healed else ""], "bonus", 0.5, 0.7, 2.4)
	hud.message("SCHIETEN!", 0.9)
	Sfx.ready_sound()


func end_round(reason: String) -> void:
	if state == "ended":
		return
	state = "ended"
	hud.show_boss(false)
	hud.set_cinematic(false)
	_end_bullet_time(true)
	bt.scale = 1.0
	Sfx.restart_music(false)
	Sfx.set_intensity("title")
	Sfx.end_round()
	ended.emit(reason, score, stats)
