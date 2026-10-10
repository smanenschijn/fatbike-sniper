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
	"hard": {"label": "Moeilijk", "windup": 0.55, "spawn": 0.72, "alive": 1.3, "attack": 1.5, "speed": 1.15, "accuracy": 0.8, "retaliate": 0.9, "hearts": 3, "bt_fill": 0.8, "score": 1.3, "boss_hp": 1.35},
}

const BULLET_TIME := {"duration": 4.5, "scale": 0.2, "fill_kill": 0.2, "fill_head": 0.12, "fill_knife": 0.2, "bonus": 1.5}

const SCORE := {"kill": 100, "headshot": 50, "multi": 100, "knife": 150, "boss": 500, "wheelie_mul": 2,
	"rocket": 200, "boss_hit": 10, "boss_part": 500, "boss_head": 2000, "boss_win": 5000, "boss_heart": 1000}

const RING_RADIUS := 9.5
static var FOUNTAIN := B(0, 3)
static var ATTACK_Z := B(0, -8.2).z

static var ENTRIES := [
	{"name": "west", "spawn": B(-56, -4.5), "mouth": B(-21, -4.5), "weight": 3.0},
	{"name": "east", "spawn": B(56, -4.5), "mouth": B(21, -4.5), "weight": 3.0},
	{"name": "north", "spawn": B(0, 52), "mouth": B(0, 15), "weight": 3.0},
	{"name": "alleyNW", "spawn": B(-13.25, 38), "mouth": B(-13.25, 15), "weight": 1.5},
	{"name": "alleyE", "spawn": B(42, 7.25), "mouth": B(21, 7.25), "weight": 1.5},
]

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
