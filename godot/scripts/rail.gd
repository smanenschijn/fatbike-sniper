class_name Rail
extends RefCounted
## On-rails walking for the adventure mode: moves the player's eye along one continuous path (built by
## Game from Config.ADVENTURE), turns the view with the street, halts at ambush stops and lets scripted
## riders loose on the way. Positions are Godot world coordinates; rider specs are handed back to `spawn`.

const EYE := 1.6           # standing eye height (seated is 1.2)
const LOOK_AHEAD := 6.0

var curve: Curve3D
var length := 0.0
var dist := 0.0
var speed := 2.9
var cur_speed := 0.0
var eye := Vector3.ZERO
var vel := Vector3.ZERO
var view_yaw := 0.0
var done := false
var stop = null            # the active ambush stop (Dictionary) or null
var stops: Array = []
var events: Array = []
var pending: Array = []    # rider specs waiting to be spawned: {t, spec, stop}
var _t := 0.0
var _bob := 0.0
var _end_look = null
var _spawn: Callable       # (spec) -> rider Dictionary


## cfg: {pts: [Vector3], speed, end_look?: Vector3, stops: [{at, look, min, max, title, riders}], events: [{at, riders}]}
func _init(cfg: Dictionary, spawn: Callable) -> void:
	_spawn = spawn
	curve = Riders.smooth_curve(cfg.pts, true)
	length = curve.get_baked_length()
	speed = cfg.speed
	_end_look = cfg.get("end_look")
	for st in cfg.get("stops", []):
		stops.append({"d": offset_of(st.at), "look": st.look, "min": st.min, "max": st.max, "title": st.title,
			"riders": st.riders, "t": 0.0, "done": false, "spawned": []})
	for ev in cfg.get("events", []):
		events.append({"d": offset_of(ev.at), "riders": ev.riders, "fired": false})
	var p0 := curve.sample_baked(0.0)
	view_yaw = _yaw_to(curve.sample_baked(minf(LOOK_AHEAD, length)) - p0)
	eye = p0 + Vector3(0, 1.2, 0)


## Distance along the walk of the point nearest to `p`.
func offset_of(p: Vector3) -> float:
	return curve.get_closest_offset(p)


static func _yaw_to(d: Vector3) -> float:
	return atan2(-d.x, -d.z)


## Flat forward direction of the view.
func forward() -> Vector3:
	return Vector3(-sin(view_yaw), 0, -cos(view_yaw))


func remaining() -> float:
	return maxf(0.0, length - dist)


## Riders of the current ambush still to come or still riding.
func stop_left() -> int:
	if stop == null:
		return 0
	var n := pending.filter(func(p): return p.stop == stop).size()
	return n + stop.spawned.filter(func(r): return r.alive and r.dist < r.len).size()


## Advance; returns "" | "stop" (an ambush begins) | "go" (walking on) | "go_clean" (every ambush rider down).
func step(dt: float) -> String:
	_t += dt
	var result := ""
	for i in range(pending.size() - 1, -1, -1):
		var p: Dictionary = pending[i]
		p.t -= dt
		if p.t <= 0.0:
			pending.remove_at(i)
			var r: Dictionary = _spawn.call(p.spec)
			if p.stop != null:
				p.stop.spawned.append(r)
	for ev in events:
		if not ev.fired and dist >= ev.d:
			ev.fired = true
			_queue(ev.riders, null)

	var target := speed
	if stop != null:
		target = 0.0
		stop.t += dt
		var left := stop_left()
		if stop.t >= stop.max or (stop.t >= stop.min and left == 0):
			stop.done = true
			result = "go_clean" if stop.spawned.all(func(r): return not r.alive) else "go"
			stop = null
	else:
		for st in stops:
			if st.done:
				continue
			var ahead: float = st.d - dist
			if ahead <= 0.15:
				stop = st
				dist = st.d
				cur_speed = 0.0
				target = 0.0
				_queue(st.riders, st)
				result = "stop"
			elif ahead < 2.5:
				target = speed * maxf(0.4, ahead / 2.5)
			break
	cur_speed = move_toward(cur_speed, target, dt * (3.0 if target > cur_speed else 6.0))
	var prev := eye
	dist = minf(length, dist + cur_speed * dt)
	done = dist >= length - 0.01

	# view: along the street, at the ambush while stopped, at the square when sitting down
	var p := curve.sample_baked(dist)
	var look: Vector3 = curve.sample_baked(minf(dist + LOOK_AHEAD, length)) - p
	if stop != null:
		look = (stop.look as Vector3) - p
	elif _end_look != null and length - dist < 3.0:
		look = (_end_look as Vector3) - p
	if look.length() > 0.3:
		view_yaw = lerp_angle(view_yaw, _yaw_to(look), minf(1.0, dt * 2.4))
	# stand up at the start, sit down at the end, and bob a little while walking
	var h := lerpf(1.2, EYE, minf(1.0, _t / 1.2))
	h = lerpf(1.2, h, clampf((length - dist) / 1.5, 0.0, 1.0))
	var walk := cur_speed / speed
	_bob += cur_speed * dt * 2.3
	eye = p + Vector3(0, h + absf(sin(_bob)) * 0.05 * walk, 0)
	vel = (eye - prev) / maxf(dt, 0.001)
	vel.y = 0.0
	return result


func _queue(riders: Array, st) -> void:
	for rd in riders:
		pending.append({"t": float(rd[0]), "spec": rd, "stop": st})
