class_name Config
## Game constants (port of src/config.js). Blender coordinates convert to Godot as (x, z, -y).


static func B(x: float, y: float, z: float = 0.0) -> Vector3:
	return Vector3(x, z, -y)


const ROUND_OPTIONS := [60, 180, 300]
const GRAVITY := 9.8
const FOV := 62.0
const ZOOM_FOV := 16.0
const MOUSE_SENS := 0.0022
const TOUCH_SENS := 0.0055
const YAW_LIMIT := deg_to_rad(115.0)
const PITCH_MIN := deg_to_rad(-40.0)
const PITCH_MAX := deg_to_rad(55.0)

const LEVELS := {
	"easy": {"label": "Makkelijk", "windup": 0.95, "spawn": 1.35, "alive": 0.7, "attack": 0.5, "speed": 0.88, "accuracy": 0.35, "retaliate": 0.4, "hearts": 5, "bt_fill": 1.35, "score": 0.8, "boss_hp": 0.7},
	"normal": {"label": "Normaal", "windup": 0.75, "spawn": 1.0, "alive": 1.0, "attack": 1.0, "speed": 1.0, "accuracy": 0.6, "retaliate": 0.7, "hearts": 3, "bt_fill": 1.0, "score": 1.0, "boss_hp": 1.0},
	# chill: no hearts, nobody throws, endless ammo. Just shooting.
	"chill": {"label": "Chill", "chill": true, "windup": 0.75, "spawn": 0.85, "alive": 1.2, "attack": 0.0, "speed": 1.0, "accuracy": 0.0, "retaliate": 0.0, "hearts": 0, "bt_fill": 1.5, "score": 1.0, "boss_hp": 0.8},
	"hard": {"label": "Moeilijk", "windup": 0.55, "spawn": 0.72, "alive": 1.3, "attack": 1.5, "speed": 1.15, "accuracy": 0.8, "retaliate": 0.9, "hearts": 3, "bt_fill": 0.8, "score": 1.3, "boss_hp": 1.35},
}

const BULLET_TIME := {"duration": 4.5, "scale": 0.2, "fill_kill": 0.2, "fill_head": 0.12, "fill_knife": 0.2, "bonus": 1.5}

const SCORE := {"kill": 100, "headshot": 50, "multi": 100, "knife": 150, "boss": 500, "wheelie_mul": 2,
	"rocket": 200, "boss_hit": 10, "boss_part": 500, "boss_head": 2000, "boss_win": 5000, "boss_heart": 1000}

## The playable squares. All share one frame: the player sits at B(0, -11.55) looking north (+Y in Blender).
## center/ring: the loop riders circle; entries: where they come from (spawn -> optional via points -> mouth of the square);
## boss: where FATBIKETRON stands and which entry each of his five bikes rides in from.
static var MAPS := {
	"pleintje": {
		"label": "'T PLEINTJE", "sub": "Het oude dorpsplein met de kerk en de fontein",
		"model": "res://assets/models/square.glb", "legend": "Legende van 't Pleintje",
		"center": B(0, 3), "ring": 9.5, "sun": Vector3(-0.8, 0.5, -0.33),
		"entries": [
			{"name": "west", "spawn": B(-56, -4.5), "mouth": B(-21, -4.5), "weight": 3.0},
			{"name": "east", "spawn": B(56, -4.5), "mouth": B(21, -4.5), "weight": 3.0},
			{"name": "north", "spawn": B(0, 52), "mouth": B(0, 15), "weight": 3.0},
			{"name": "alleyNW", "spawn": B(-13.25, 38), "mouth": B(-13.25, 15), "weight": 1.5},
			{"name": "alleyE", "spawn": B(42, 7.25), "mouth": B(21, 7.25), "weight": 1.5},
		],
		"boss_spot": Vector3(3.0, 0, -10.5), "boss_x": Vector2(0.0, 9.0), "boss_z": Vector2(-12.5, -7.0),
		"boss_entries": {"LegL": "east", "LegR": "west", "Torso": "north", "ArmL": "alleyE", "ArmR": "alleyNW"},
	},
	"donut": {
		"label": "HENRI DONUTPLEIN", "sub": "Nijverdal: de galerij, het gemeentehuis en een ijsje bij Henri",
		"model": "res://assets/models/dunant.glb", "legend": "Legende van het Donutplein",
		"center": B(-1.5, 3.5), "ring": 9.5, "tight_routes": true, "sun": Vector3(-0.55, 0.55, 0.62),
		"entries": [
			# the red road between the tower and the shop row
			{"name": "west", "spawn": B(-18.5, 58), "mouth": B(-18.5, 17), "weight": 2.5},
			# down the market road, then left into the gallery and out through one of its arches
			{"name": "galerij", "spawn": B(12.2, 58), "via": [B(12.2, 25.5), B(7.9, 22.1)], "mouth": B(-1.2, 22.1), "weight": 3.0},
			{"name": "markt", "spawn": B(12.2, 58), "mouth": B(12.2, 17), "weight": 2.0},
			# the road between the gemeentehuis and the apartments
			{"name": "oost", "spawn": B(56, 19.5), "mouth": B(15.5, 19.5), "weight": 1.5},
		],
		"boss_spot": Vector3(0.0, 0, -10.0), "boss_x": Vector2(2.0, 6.0), "boss_z": Vector2(-11.5, -8.5),
		"boss_entries": {"LegL": "oost", "LegR": "west", "Torso": "galerij", "ArmL": "markt", "ArmR": "west"},
	},
}
const MAP_ORDER := ["pleintje", "donut"]

## The adventure mode: survive on 't Pleintje, walk the streets to the Henri Donutplein, survive there and meet
## FATBIKETRON, all in one world. Three models side by side, each in its own frame (Blender x, y): 't Pleintje
## at the origin, the streets (route.glb, blender/build_route.py) at FRAMES.route, the Donutplein at
## FRAMES.donut. The walk is one continuous path through those frames.
## Riders: [delay, type, path, attacks?]; a path point [x, y, h] makes the rider jump from the previous point
## to this one, h metres high; a path {"loop": [cx, cy, rx, ry, laps], "from": [...], "to": [...]} circles.
const ADVENTURE := {
	"square_time": 60.0,
	"rockets": 8,
	"speed": 3.3,
	"frames": {"pleintje": [0.0, 0.0], "route": [0.0, 70.0], "donut": [-76.0, 222.5]},
	"walk": [
		# stand up from the café table, past the fountain into the north street ...
		["pleintje", [[0, -11.55], [0.9, -9.6], [5.6, -3.0], [6.2, 7.0], [2.6, 14.0], [0, 19.5], [0, 40]]],
		# ... the streets ...
		["route", [[0, -14], [0, 31], [0.8, 35.5], [3.5, 38.3], [8, 39.6], [15, 39.8], [18.4, 40.6], [20, 43], [20, 51],
			[20, 56], [20, 94], [20, 105], [20, 109], [20, 128], [20, 150], [20, 165], [18, 170], [13, 172], [-16, 172]]],
		# ... in along the Donutplein's east road and sit down at Henri's
		["donut", [[50, 19.5], [30, 19.5], [15.5, 19.5], [7, 10], [2.5, 0], [0.8, -8.5], [0, -11.55]]],
	],
	"end_look": ["donut", [0, 10]],
	"leave": ["pleintje", [0, 24]],      # no more square riders from here
	"arrive": ["donut", [34, 19.5]],     # the Donutplein's riders start here
	"hide_pleintje": ["route", [10, 39.6]],
	"show_donut": ["route", [20, 75]],
	"water": ["route", [-65, 42, 65, 50], -0.95],   # the gracht: things that fall in splash
	"stops": [
		{"at": [12, 39.7], "look": [16, 47], "min": 14.0, "max": 32.0, "title": "HINDERLAAG BIJ DE GRACHT!", "riders": [
			# over the bridge, one after the other
			[0.5, "normal", [[20, 74], [20, 56], [20, 44], [18.5, 41.0], [12, 37.3], [-40, 37.3]], true],
			[1.3, "normal", [[20.8, 76], [20.8, 56], [21, 44], [21.5, 41], [27, 37.6], [58, 37.6]], true],
			[2.1, "duo", [[19.4, 78], [19.4, 56], [19.5, 44], [18, 40.8], [10, 37.4], [-40, 37.4]], true],
			[2.9, "normal", [[20.5, 80], [20.5, 56], [20.5, 44], [22, 41], [28, 37.6], [58, 37.6]], true],
			# jumpers: off the ramps on the far quay, over the water
			[5.0, "normal", [[-32, 53], [-4, 53], [3.5, 53.4], [5, 52.2], [5, 50.3], [5, 40.4, 2.8], [3, 38.2], [-6, 37.4], [-40, 37.4]], true],
			[5.5, "normal", [[44, 52.2], [-58, 52.2]], true],
			[6.3, "normal", [[46, 53], [34, 53], [30.5, 53.4], [29, 52.2], [29, 50.3], [29, 40.4, 2.8], [31, 38.2], [40, 37.4], [58, 37.4]], true],
			[7.6, "wheelie", [[-32, 53], [-4, 53], [3.5, 53.4], [5, 52.2], [5, 50.3], [5, 40.4, 3.4], [3, 38.2], [-6, 37.4], [-40, 37.4]], false],
			[8.8, "duo", [[46, 53], [34, 53], [30.5, 53.4], [29, 52.2], [29, 50.3], [29, 40.4, 2.6], [31, 38.2], [40, 37.4], [58, 37.4]], true],
			[9.6, "normal", [[-36, 52.2], [58, 52.2]], true],
			# the pincer: along the quay from both sides, then two speaker bosses over the bridge
			[11.5, "normal", [[-34, 37.3], [8, 37.3], [13, 37.2], [58, 37.2]], true],
			[11.5, "normal", [[44, 37.6], [24, 37.6], [18, 37.5], [-58, 37.5]], true],
			[12.6, "duo", [[-36, 38.0], [6, 38.0], [11, 37.1], [58, 37.1]], true],
			[13.5, "boss", [[46, 52.2], [24, 52.2], [20.5, 50], [20.5, 44], [22, 41], [28, 37.6], [58, 37.6]], true],
			[15.0, "boss", [[-30, 52.2], [16, 52.2], [19.5, 50], [19.5, 44], [18, 41], [10, 37.6], [-58, 37.6]], true],
			[16.0, "wheelie", [[46, 53], [34, 53], [30.5, 53.4], [29, 52.2], [29, 50.3], [29, 40.4, 3.4], [31, 38.2], [40, 37.4], [58, 37.4]], false],
		]},
		{"at": [20, 109], "look": [20, 120], "min": 14.0, "max": 34.0, "title": "HINDERLAAG IN DE SPEELTUIN!", "riders": [
			# from three streets at once
			[0.5, "normal", [[-20, 116], [6, 116], [12, 116], [16, 119], [24, 120], [30, 116], [56, 116]], true],
			[0.5, "normal", [[56, 116], [34, 116], [27, 114], [23, 113], [15, 112.5], [8, 116], [-20, 116]], true],
			[1.2, "duo", [[20, 150], [20, 128], [20, 121], [23, 117], [30, 116], [56, 116]], true],
			[2.0, "normal", [[19, 150], [19, 128], [18, 118], [13, 113], [7, 116], [-20, 116]], true],
			# the merry-go-round: a ring of riders around the playground
			[5.0, "normal", {"loop": [20, 119, 10.5, 6.5, 1.5], "from": [[-20, 116], [6, 116]], "to": [[34, 116], [56, 116]]}, true],
			[5.6, "normal", {"loop": [20, 119, 10.5, 6.5, 1.5], "from": [[-20, 116], [6, 116]], "to": [[34, 116], [56, 116]]}, true],
			[6.2, "duo", {"loop": [20, 119, 10.5, 6.5, 1.5], "from": [[-20, 116], [6, 116]], "to": [[34, 116], [56, 116]]}, true],
			[6.8, "normal", {"loop": [20, 119, 10.5, 6.5, 1.5], "from": [[-20, 116], [6, 116]], "to": [[34, 116], [56, 116]]}, true],
			[7.4, "wheelie", {"loop": [20, 119, 10.5, 6.5, 1.5], "from": [[-20, 116], [6, 116]], "to": [[34, 116], [56, 116]]}, false],
			# stunt hops over the grass
			[10.0, "wheelie", [[56, 116], [34, 116], [29, 116], [24, 117, 1.4], [16, 117, 1.4], [8, 116], [-20, 116]], false],
			[10.8, "normal", [[20, 150], [20, 128], [26, 124], [27, 118, 1.2], [25, 113], [30, 116], [56, 116]], true],
			# finale: two speaker bosses circling, with company
			[13.0, "boss", {"loop": [20, 119, 11, 7, 1.0], "from": [[-20, 116], [6, 116]], "to": [[34, 116], [56, 116]]}, true],
			[13.0, "boss", {"loop": [20, 119, 11, 7, 1.0], "from": [[56, 116], [34, 116]], "to": [[6, 116], [-20, 116]], "ccw": true}, true],
			[14.0, "duo", [[20, 150], [20, 128], [20, 122], [14, 116], [7, 116], [-20, 116]], true],
			[15.0, "duo", [[-20, 116], [6, 116], [14, 113.5], [26, 113.5], [34, 116], [56, 116]], true],
			[16.5, "normal", [[19, 150], [19, 128], [24, 120], [33, 116], [56, 116]], true],
		]},
	],
	"events": [
		# the Winkelstraat: busy from the start. Head-on traffic, riders out of both alleys (and across from one
		# alley to the other), overtakers ringing their bells, then the quay
		{"at": [0, -13], "riders": [[0.0, "normal", [[2.2, 36], [2.2, 10], [2.4, -40]], true],
			[1.4, "normal", [[-2.0, 36], [-2.0, 10], [-2.2, -40]], false],
			[2.6, "wheelie", [[1.0, 37], [1.0, 10], [1.4, -40]], false]]},
		{"at": [0, -7], "riders": [[0.0, "normal", [[1.6, -40], [1.8, -12], [2.2, 10], [2.2, 30], [4, 37.5], [40, 37.5]], false],
			[0.6, "normal", [[-1.6, -40], [-1.8, -12], [-2.0, 10], [-1.6, 31], [-4, 37.6], [-40, 37.6]], true]]},
		{"at": [0, -4], "riders": [[0.0, "normal", [[2.2, 36], [2.2, 10], [2.4, -40]], true],
			[0.8, "duo", [[-36, 9.75], [-6, 9.75], [0, 13], [6, 19.75], [36, 19.75]], false]]},
		{"at": [0, 3], "riders": [[0.0, "normal", [[-36, 9.75], [-6, 9.75], [-2.2, 6.5], [-2.2, -40]], true],
			[1.0, "normal", [[36, 19.75], [6, 19.75], [0, 15], [-6, 9.75], [-36, 9.75]], false],
			[2.0, "wheelie", [[-2.2, 37], [-2.2, 10], [-2.4, -40]], false]]},
		{"at": [0, 8], "riders": [[0.0, "normal", [[36, 19.75], [6, 19.75], [2.2, 16], [2.2, -40]], true],
			[1.2, "duo", [[36, 19.75], [6, 19.75], [2.4, 15], [2.4, -40]], true],
			[2.2, "normal", [[1.8, -40], [2.0, 0], [-1.8, 24], [-1.6, 31], [-4, 38.2], [-40, 38.2]], false]]},
		{"at": [0, 13], "riders": [[0.0, "boss", [[-40, 37.8], [-4, 37.8], [-1.0, 33], [-1.0, 10], [-1.4, -40]], true],
			[1.5, "normal", [[-36, 9.75], [-6, 9.75], [0, 13], [6, 19.75], [36, 19.75]], true]]},
		{"at": [0, 15], "riders": [[0.0, "wheelie", [[-58, 38.6], [-3, 38.6], [-1.8, 33], [-1.8, -40]], false],
			[1.5, "normal", [[58, 38.2], [4, 38.2], [2.2, 33], [2.2, -40]], true],
			[2.4, "duo", [[36, 19.75], [6, 19.75], [2.0, 23], [2.0, 30], [5, 37.4], [40, 37.4]], true]]},
		{"at": [0, 24], "riders": [[0.0, "normal", [[58, 52.2], [-58, 52.2]], true],
			[1.2, "normal", [[-58, 52.6], [58, 52.6]], false],
			[2.5, "normal", [[-58, 38.4], [-6, 38.4], [-2.0, 34], [-2.0, -40]], true]]},
		# the quay: traffic both ways, and the far quay across the water
		{"at": [2.5, 37.8], "riders": [[0.0, "normal", [[40, 37.2], [10, 37.2], [-40, 37.2]], true],
			[0.8, "wheelie", [[-40, 52.4], [40, 52.4]], false],
			[1.8, "duo", [[-40, 37.4], [-10, 37.4], [-2, 37.0], [6, 37.2], [40, 37.2]], false]]},
		{"at": [7, 39.5], "riders": [[0.0, "normal", [[36, 37.4], [14, 37.4], [-40, 37.4]], true],
			[1.0, "normal", [[40, 52.2], [-40, 52.2]], true]]},
		# the Woonstraat: across the crossroads, head-on out of the gate, out of the side street
		{"at": [20, 52], "riders": [[0.0, "normal", [[-25, 68.2], [55, 68.2]], true],
			[1.4, "normal", [[55, 69.6], [-25, 69.6]], true]]},
		{"at": [20, 62], "riders": [[0.0, "normal", [[20, 103], [18.0, 90], [18.0, 52], [18, 44], [17, 40], [-58, 37.8]], true],
			[0.9, "duo", [[20, 103], [22, 90], [22, 52], [22, 44], [23, 40], [58, 37.8]], true]]},
		{"at": [20, 72], "riders": [[0.0, "normal", [[55, 82.5], [26, 82.5], [22, 79], [22, 52], [22.5, 44], [24, 40], [58, 37.8]], true],
			[1.6, "wheelie", [[20, 103], [17.6, 92], [17.6, 52], [18, 44], [17, 40], [-58, 37.8]], false]]},
		{"at": [20, 82], "riders": [[0.0, "boss", [[20, 128], [20, 104], [18, 92], [17.8, 52], [18, 44], [17, 40], [-58, 37.8]], true]]},
		# the way out: head-on down the exit street
		{"at": [20, 132], "riders": [[0.0, "normal", [[-10, 172], [14, 172], [21.8, 166], [21.8, 125], [26, 117], [56, 116]], true],
			[1.0, "duo", [[-14, 172.8], [14, 172.8], [18.2, 166], [18.2, 125], [14, 117], [-20, 116]], true]]},
		# the street to the Donutplein: out of the square, head-on
		{"at": [20, 160], "riders": [[0.0, "normal", [[-40, 171], [10, 171], [20.8, 168], [20.8, 125], [26, 117], [56, 116]], true],
			[1.2, "wheelie", [[-40, 173], [10, 173], [19, 168], [19, 125], [14, 117], [-20, 116]], false]]},
		{"at": [10, 172], "riders": [[0.0, "boss", [[-50, 173], [12, 173], [21, 166], [21, 125], [26, 117], [56, 116]], true]]},
	],
}

## Blender [x, y] in an adventure frame to a Godot position.
static func AP(frame: String, p: Array) -> Vector3:
	var o: Array = ADVENTURE.frames[frame]
	return B(p[0] + o[0], p[1] + o[1])

static var map_id := "pleintje"
static var MAP: Dictionary = MAPS.pleintje
static var RING_RADIUS := 9.5
static var FOUNTAIN := B(0, 3)
static var ATTACK_Z := B(0, -8.2).z
static var ENTRIES: Array = MAPS.pleintje.entries
static var OFFSET := Vector3.ZERO


## Make `id` the square riders and the boss use. `offset` (Godot) moves its data along with a square that
## isn't at the origin (the adventure world).
static func use_map(id: String, offset := Vector3.ZERO) -> void:
	if not MAPS.has(id):
		id = "pleintje"
	map_id = id
	OFFSET = offset
	MAP = MAPS[id] if offset == Vector3.ZERO else _shifted(MAPS[id], offset)
	FOUNTAIN = MAP.center
	RING_RADIUS = MAP.ring
	ENTRIES = MAP.entries
	ATTACK_Z = B(0, -8.2).z + offset.z


static func _shifted(m: Dictionary, o: Vector3) -> Dictionary:
	var s := m.duplicate(true)
	s.center += o
	s.boss_spot += o   # boss_x / boss_z stay relative to the square: the boss adds OFFSET himself (|x| mirrors)
	for e in s.entries:
		e.spawn += o
		e.mouth += o
		if e.has("via"):
			e.via = e.via.map(func(v): return v + o)
	return s

## Blender [x, y] points to Godot positions on the ground.
static func BP(pts: Array) -> Array:
	return pts.map(func(p): return B(p[0], p[1]))


static func is_touch() -> bool:
	return OS.has_feature("mobile") or DisplayServer.is_touchscreen_available() and not OS.has_feature("pc") or OS.get_cmdline_user_args().has("--touch")


static func difficulty(t: float, level: Dictionary) -> Dictionary:
	var touch_mul := 0.75 if is_touch() else 1.0
	return {
		"spawn_interval": lerpf(1.9, 0.5, t) * level.spawn,
		"max_alive": maxi(3, roundi(lerpf(5, 18, t) * level.alive * touch_mul)),
		"attack_chance": minf(0.85, lerpf(0.12, 0.45, t) * level.attack),
		"speed_mul": lerpf(1.0, 1.35, t) * level.speed,
	}


## Ramps up over ~90 s, then (in longer rounds) breathes in waves.
static func round_intensity(elapsed: float, round_time: float) -> float:
	var ramp := minf(1.0, elapsed / minf(round_time, 90.0))
	if round_time <= 60.0 or elapsed < 90.0:
		return ramp
	var wave := 0.5 + 0.5 * sin(((elapsed - 90.0) / 50.0) * TAU - PI / 2.0)
	return 0.7 + 0.3 * (1.0 - wave) + minf(0.15, (elapsed - 90.0) / 1200.0)


const PALETTES := {
	"skin": ["#f6d7c3", "#efc3a4", "#e6b18f", "#d9a07a", "#c98d62", "#b77a52", "#a06640", "#8a5536", "#6f4330", "#5a3526", "#46291d"],
	"hair_young": ["#1d1714", "#1d1714", "#3b2a20", "#5a3d2b", "#7a5236", "#a5774c", "#d8b276", "#e8d3a0", "#9c3b22", "#c25a2c", "#ff6fb5", "#5ec8ff"],
	"hair_grey": ["#d8d8d8", "#e8e8e8", "#bdbdbd", "#f2efe8", "#a8a8a8"],
	"top": ["#1a1a20", "#e9e9ec", "#c8302a", "#2b5a8c", "#2d6a45", "#f4cf3a", "#f08a24", "#ff6fb5", "#7a5cff", "#5d6066", "#6b1d2a", "#35c2c2"],
	"cardigan": ["#d98aa8", "#8aa8d9", "#c9b48a", "#9c6b8a", "#7a9a6a"],
	"trackpants": ["#1a1a20", "#5d6066", "#1e2a4a", "#6b1d2a", "#e9e9ec", "#2d6a45"],
	"jeans": ["#2b4a7a", "#3b5f94", "#1f2f4f", "#6f8fb8", "#2a2a2e"],
	"leggings": ["#1a1a20", "#2a2a3a", "#5d6066", "#6b1d2a", "#2b4a7a"],
	"shorts": ["#c9b48a", "#2b4a7a", "#1a1a20", "#6b7b4a", "#d6d0c4", "#c8302a", "#3b5f94"],
	"skirt": ["#6b1d2a", "#2b4a7a", "#4a5a3a", "#5a3a5a", "#7a6a5a"],
	"cap": ["#c8302a", "#1a1a20", "#2b5a8c", "#f4cf3a", "#e9e9ec", "#2d6a45", "#f08a24"],
	"flatcap": ["#6b5a48", "#4a4a4a", "#7a6a5a", "#3a4a5a"],
	"shoe": ["#f7f7f5", "#f7f7f5", "#f7f7f5", "#1a1a20", "#c8302a", "#35c2ff", "#ffd23f"],
}

const BIKE_COLORS := [
	["#2a2c30", "#ff7a1a"], ["#2a2c30", "#35c2ff"], ["#d8d8dc", "#ff3b6b"], ["#264d32", "#ffd23f"],
	["#8a1c22", "#f2f2f2"], ["#1d2f55", "#7cff6b"], ["#f2e6d0", "#2b5a8c"], ["#ff8fb8", "#ffffff"],
]

const SHOUTS := {
	"any": ["Opzij!", "Tring tring!", "Kijk uit, ik heb haast!", "Fietspad? Nooit van gehoord!", "Ik ga 40, hoor!", "Haha, mis!",
		"Jij raakt niks!", "Dit is mijn plein!", "Rot op met je ijsje!", "Gas erop!", "Brrrrrr!", "Ik heb voorrang!", "Aan de kant!"],
	"teen": ["Bro, rustig!", "Skrrrt!", "Dit gaat op TikTok!", "Mam, kijk!", "Wacht, ik film dit!", "Check deze wheelie!", "Ik heb geen rijbewijs nodig!"],
	"adult": ["Ik moet naar m'n werk!", "Ik heb nog een call!", "Even de kids ophalen!", "Zo, dat scheelt fietsen!"],
	"senior": ["Aan de kant, jongeman!", "Vroeger reden we gewoon op de fiets!", "Mijn kleinzoon heeft hem afgesteld!",
		"Ik ben op weg naar de bingo!", "Ik heb voorrang, ik ben 78!", "Hoe rem je met dit ding?!", "Waar zit de bel?!"],
}
const PAIN_SHOUTS := ["AUW!", "HÉ!", "Mijn fiets!", "Dat doet pijn, zeg!", "Au, m'n heup!"]
const THROW_SHOUTS := ["Pak aan!", "Vang dan!", "Hier, voor jou!", "Opgepast!"]
const BOSS_SHOUTS := ["VOLUME OMHOOG!", "BASSSSS!", "Hoor je dat?!", "Plein is van mij!"]
