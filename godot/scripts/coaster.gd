class_name Coaster
extends Node3D
## The roller coaster of a square (Wollahbi): the track comes from the model's Track_### markers (in order of
## travel, '_lift' on the chain lift, '_station' in the station), the train is copies of its CoasterCar.
## The train runs on its own; Game sends a fatbiker over the rails now and then (path_points / speed_at).

const CARS := 5
const CAR_GAP := 2.6
const LIFT_SPEED := 4.0
const STATION_SPEED := 3.2

var curve: Curve3D
var length := 0.0
var head := 0.0               # distance of the first car along the track
var time_scale := 1.0         # bullet time slows the train too
var _offsets: PackedFloat32Array = []
var _kinds: PackedStringArray = []   # per marker: "lift" | "station" | ""
var _top := 0.0
var _cars: Array = []


## Builds the coaster of `model`, or returns null when it has no track.
static func from_model(model: Node3D) -> Coaster:
	var marks := model.find_children("Track_*", "Node3D", true, false)
	if marks.size() < 8:
		return null
	marks.sort_custom(func(a, b): return String(a.name) < String(b.name))
	var c := Coaster.new()
	model.add_child(c)
	c._build(marks, model.find_child("CoasterCar", true, false) as Node3D)
	return c


func _build(marks: Array, car: Node3D) -> void:
	var pts := []
	for m in marks:
		pts.append(to_local((m as Node3D).global_position))
	pts.append(pts[0])   # closed
	curve = Riders.smooth_curve(pts)
	curve.up_vector_enabled = true
	length = curve.get_baked_length()
	for i in marks.size():
		var nm := String(marks[i].name)
		_offsets.append(curve.get_closest_offset(pts[i]))
		_kinds.append("lift" if nm.ends_with("_lift") else ("station" if nm.ends_with("_station") else ""))
		_top = maxf(_top, (pts[i] as Vector3).y)
	if car:
		car.visible = false
		for i in CARS:
			var c := car.duplicate() as Node3D
			c.visible = true
			add_child(c)
			_cars.append(c)
	head = length * 0.5
	_place()


## Speed of the train (or a fatbiker on the rails) at a distance along the track: slow up the chain lift and
## through the station, otherwise what's left of the height it fell from.
func speed_at(d: float) -> float:
	d = fposmod(d, length)
	var i := _offsets.bsearch(d) - 1
	var kind := _kinds[clampi(i, 0, _kinds.size() - 1)]
	if kind == "lift":
		return LIFT_SPEED
	if kind == "station":
		return STATION_SPEED
	var y := curve.sample_baked(d).y
	return clampf(sqrt(2.0 * 9.8 * maxf(0.0, _top + 1.0 - y)) * 0.9, 6.0, 24.0)


## Position and orientation (model faces +X, as the cars and the fatbikers do) at a distance along the track.
func frame_at(d: float) -> Transform3D:
	d = fposmod(d, length)
	var p := curve.sample_baked(d, true)
	var fwd := (curve.sample_baked(fposmod(d + 0.4, length), true) - curve.sample_baked(fposmod(d - 0.4, length), true)).normalized()
	var up := curve.sample_baked_up_vector(d, true)
	up = (up - fwd * up.dot(fwd)).normalized()
	return global_transform * Transform3D(Basis(fwd, up, fwd.cross(up)), p)


## World points along the track from `from` for `dist` metres, for a rider riding it.
func path_points(from: float, dist: float, step := 1.5) -> Array:
	var out := []
	var d := 0.0
	while d <= dist:
		out.append(global_transform * curve.sample_baked(fposmod(from + d, length), true))
		d += step
	return out


## Where the station starts: riders on the rails set off from here.
func station_offset() -> float:
	for i in _kinds.size():
		if _kinds[i] == "station":
			return _offsets[i]
	return 0.0


## The train's first car (world), e.g. for screams.
func train_position() -> Vector3:
	return frame_at(head).origin


func _process(dt: float) -> void:
	if curve == null or not is_visible_in_tree():
		return
	head = fposmod(head + speed_at(head) * dt * time_scale, length)
	_place()


func _place() -> void:
	for i in _cars.size():
		(_cars[i] as Node3D).global_transform = frame_at(head - i * CAR_GAP)
