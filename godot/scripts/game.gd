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

var state = "idle"  # idle | countdown | playing | ended
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


func reset(p_round_time: float, p_level: String) -> void:
	round_time = p_round_time
	level_key = p_level
	level = Config.LEVELS[p_level]
	max_hearts = level.hearts
	riders.settings = {"accuracy": level.accuracy}
	world.reset_ijsje()
	next_refill = 60.0
	riders.clear()
	effects.clear()
	for p in projectiles:
		p.node.queue_free()
	projectiles.clear()
	weapons.reset({60: 5, 180: 12, 300: 18}.get(int(round_time), 5))
	_end_bullet_time(true)
	bt = {"meter": 0.0, "active": false, "t": 0.0, "scale": 1.0}
	Sfx.set_intensity("game")
	score = 0
	time = round_time
	hearts = max_hearts
	stats = {"shots": 0, "hits": 0, "kills": 0, "headshots": 0, "knives": 0, "best_multi": 1, "bosses": 0}
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
	if muzzle != null:
		effects.muzzle_flash(muzzle, 0.7 if w.key == "shotgun" else 0.55)
		if w.key == "sniper" and first_end != null:
			_tracer(muzzle, first_end)
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
	_after_shot(any_hit)


func fire_projectile(w: Dictionary, muzzle: Vector3, origin: Vector3, fwd: Vector3) -> void:
	stats.shots += 1
	var wh = world.raycast(origin, fwd, 250.0)
	var rh = riders.raycast(origin, fwd, wh.distance if not wh.is_empty() else 250.0)
	var aim_dist: float = rh[0].t if not rh.is_empty() else (wh.distance if not wh.is_empty() else 120.0)
	var aim = origin + fwd * aim_dist
	var p: Dictionary = w.projectile
	if not rh.is_empty() and rh[0].rider.alive:  # arcade lead
		var r: Dictionary = rh[0].rider
		var rv = Vector3(cos(r.yaw), 0, -sin(r.yaw)) * r.speed
		var base = aim
		for i in 2:
			aim = base + rv * (aim.distance_to(muzzle) / p.speed)
	var dir = (aim - muzzle).normalized()
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
	else:
		var mi = MeshInstance3D.new()
		var sm = SphereMesh.new()
		sm.radius = 0.06
		sm.height = 0.12
		mi.mesh = sm
		var mat = StandardMaterial3D.new()
		mat.albedo_color = Color("8c8a83")
		mat.roughness = 0.85
		mi.material_override = mat
		node = mi
	world.add_child(node)
	node.global_position = muzzle
	projectiles.append({"node": node, "vel": vel, "w": w, "age": 0.0, "trail": 0.0, "hit_any": false})


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
		var done = false
		if not kh.is_empty():
			_knife_shot(kh[0].knife)
			p.hit_any = true
		if not rh.is_empty():
			var h: Dictionary = rh[0]
			if d.has("explode"):
				_explode(h.point, p)
			else:
				p.hit_any = true
				hud.hit(h.part == "head")
				Sfx.hit(h.part == "head")
				if riders.damage(h.rider, d.damage, dir, 6.0):
					_score_kills([{"rider": h.rider, "head": h.part == "head", "point": h.point}])
			done = true
		elif not wh.is_empty() or next.y < 0 or p.age > 4.0:
			var at: Vector3 = wh.position if not wh.is_empty() else next
			if d.has("explode"):
				_explode(at, p)
			else:
				effects.puff(at, Color("d8cbb5"), 3, 0.35)
			done = true
		if done:
			node.queue_free()
			projectiles.remove_at(i)
			if not d.has("explode"):
				_after_shot(p.hit_any)
		else:
			node.global_position = next


func _explode(point: Vector3, p: Dictionary) -> void:
	effects.explosion(point)
	Sfx.explosion(point.distance_to(camera.global_position))
	var R: float = p.w.projectile.explode
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
	if not kills.is_empty():
		hud.hit(false)
		_score_kills(kills)
	_after_shot(not kills.is_empty())


func _after_shot(hit: bool) -> void:
	if hit:
		stats.hits += 1
	elif state == "playing" and randf() < level.retaliate:
		riders.retaliate()


func _knife_shot(k: Dictionary) -> void:
	var pos: Vector3 = (k.mesh as Node3D).global_position
	riders.destroy_knife(k)
	stats.knives += 1
	fill_meter(Config.BULLET_TIME.fill_knife)
	var kp = pts(Config.SCORE.knife)
	_add_score(kp, pos, "MES GERAAKT! +%d" % kp, "bonus")
	Sfx.clank()
	hud.hit(false)


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
	world.add_child(mi)
	tracers.append({"node": mi, "age": 0.0})


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
		if bt.active:
			label = "SLOWMO " + label
		_add_score(p, k.point, label, "bonus" if k.head or r.type == "boss" else "")
	if bodies >= 2:
		var bonus = pts(Config.SCORE.multi * (bodies - 1))
		score += bonus
		stats.best_multi = maxi(stats.best_multi, bodies)
		effects.popup_screen("%s +%d" % [MULTI_NAMES[mini(bodies, 5)], bonus], "big", 0.5, 0.3, 1.3)
		Sfx.cheer()


func on_player_hit(knife_vel: Vector3) -> void:
	if state != "playing":
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
		end_round("NEERGESTOKEN!")


# ------------------------------------------------------------ loop

func step(dt: float, inp) -> void:
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
	if state != "playing":
		return
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
	hud.set_meter(bt.t / Config.BULLET_TIME.duration if bt.active else bt.meter, bt.active)

	var prev_sec = ceili(time)
	time -= gdt
	if ceili(time) != prev_sec and time <= 5 and time > 0:
		Sfx.tick()
	var diff = Config.difficulty(Config.round_intensity(elapsed(), round_time), level)
	if round_time > 60 and elapsed() >= next_refill and time > 5:
		next_refill += 60
		var healed = hearts < max_hearts
		if healed:
			hearts += 1
			hud.set_hearts(hearts, max_hearts)
		world.reset_ijsje()
		effects.popup_screen("OBER: NIEUW IJSJE! +1 ♥" if healed else "OBER: NIEUW IJSJE!", "bonus", 0.5, 0.7, 2.0)
		Sfx.ready_sound()
	riders.step(gdt, diff, elapsed())
	weapons.step(dt, inp)
	weapons.try_fire(inp)
	_update_projectiles(dt * maxf(bt.scale, 0.5))
	hud.set_score(score)
	hud.set_time(time)
	if time <= 0:
		end_round("TIJD OP!")


func end_round(reason: String) -> void:
	if state == "ended":
		return
	state = "ended"
	_end_bullet_time(true)
	bt.scale = 1.0
	Sfx.set_intensity("title")
	Sfx.end_round()
	ended.emit(reason, score, stats)
