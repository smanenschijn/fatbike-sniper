extends Node
## Autoload "Sfx": sound effects (pre-rendered synth WAVs), the soundtrack, and the bullet-time "slowed" mix.

const NAMES := ["katapult", "shotgun", "sniper", "bazooka", "explosion", "hit", "hit_head", "knock_off", "bell", "whoosh",
	"clank", "hurt", "click", "reload", "empty", "cheer", "tick", "go", "end", "bullet_in", "bullet_out", "ready", "warn",
	"roar", "stomp", "rumble", "transform", "clank_heavy", "rocket", "rev"]

var _streams := {}
var _pool: Array[AudioStreamPlayer] = []
var _next := 0
var music: AudioStreamPlayer
var muted := false
var _sfx_bus := 0
var _music_bus := 0
var _music_pitch := 1.0
var _music_tween: Tween


func _ready() -> void:
	_sfx_bus = _make_bus("SFX", -4.0)
	_music_bus = _make_bus("Music", -7.0)
	for n in NAMES:
		var path := "res://assets/sfx/%s.wav" % n
		if ResourceLoader.exists(path):
			_streams[n] = load(path)
	for i in 16:
		var p := AudioStreamPlayer.new()
		p.bus = "SFX"
		add_child(p)
		_pool.append(p)
	music = AudioStreamPlayer.new()
	music.bus = "Music"
	var song = load("res://assets/audio/fatbike-flow.mp3")
	if song is AudioStreamMP3:
		song.loop = true
	music.stream = song
	add_child(music)
	var cfg := ConfigFile.new()
	if cfg.load("user://settings.cfg") == OK:
		muted = cfg.get_value("audio", "music_muted", false)
	AudioServer.set_bus_mute(_music_bus, muted)


func _make_bus(bus_name: String, volume_db: float) -> int:
	AudioServer.add_bus()
	var idx := AudioServer.bus_count - 1
	AudioServer.set_bus_name(idx, bus_name)
	AudioServer.set_bus_volume_db(idx, volume_db)
	var lp := AudioEffectLowPassFilter.new()
	lp.cutoff_hz = 20000.0
	AudioServer.add_bus_effect(idx, lp)
	AudioServer.set_bus_effect_enabled(idx, 0, false)
	var rev := AudioEffectReverb.new()
	rev.room_size = 0.8
	rev.wet = 0.35
	AudioServer.add_bus_effect(idx, rev)
	AudioServer.set_bus_effect_enabled(idx, 1, false)
	return idx


func play(n: String, volume_db := 0.0, pitch := 1.0) -> void:
	if not _streams.has(n):
		return
	var p := _pool[_next]
	_next = (_next + 1) % _pool.size()
	p.stream = _streams[n]
	p.volume_db = volume_db
	p.pitch_scale = pitch * randf_range(0.97, 1.03)
	p.play()


# ------------------------------------------------------------ named helpers (mirror src/audio.js)

func shot(kind: String) -> void: play(kind)
func explosion(dist := 10.0) -> void: play("explosion", clampf(-dist / 8.0, -10.0, 2.0))
func hit(head := false) -> void: play("hit_head" if head else "hit")
func knock_off() -> void: play("knock_off", -2.0)
func bell(pan := 0.0) -> void: play("bell", -6.0)
func whoosh() -> void: play("whoosh")
func clank() -> void: play("clank")
func hurt() -> void: play("hurt")
func click() -> void: play("click")
func reload() -> void: play("reload")
func empty() -> void: play("empty")
func cheer() -> void: play("cheer")
func tick() -> void: play("tick")
func go() -> void: play("go")
func end_round() -> void: play("end")
func bullet_in() -> void: play("bullet_in")
func bullet_out() -> void: play("bullet_out")
func ready_sound() -> void: play("ready")
func warn() -> void: play("warn", 2.0)
func roar() -> void: play("roar", 3.0)
func stomp(dist := 20.0) -> void: play("stomp", clampf(4.0 - dist / 6.0, -8.0, 3.0), randf_range(0.9, 1.05))
func rumble() -> void: play("rumble", 2.0)
func transform() -> void: play("transform", -2.0)
func clank_heavy() -> void: play("clank_heavy", 0.0, randf_range(0.85, 1.1))
func rocket() -> void: play("rocket", -1.0)
func rev() -> void: play("rev", -4.0, randf_range(0.85, 1.15))


# ------------------------------------------------------------ music

func start_music() -> void:
	if music.stream and not music.playing:
		music.play()


## Title screen: the song "from inside the café". In game: full.
func set_intensity(level: String) -> void:
	var muffled := level == "title"
	AudioServer.set_bus_effect_enabled(_music_bus, 0, muffled)
	(AudioServer.get_bus_effect(_music_bus, 0) as AudioEffectLowPassFilter).cutoff_hz = 1400.0


## Bullet time: slowed + reverb on the music, muffled effects.
func set_slow(on: bool) -> void:
	music.pitch_scale = 0.62 if on else _music_pitch
	AudioServer.set_bus_effect_enabled(_music_bus, 1, on)
	AudioServer.set_bus_effect_enabled(_music_bus, 0, on)
	(AudioServer.get_bus_effect(_music_bus, 0) as AudioEffectLowPassFilter).cutoff_hz = 1100.0
	AudioServer.set_bus_effect_enabled(_sfx_bus, 0, on)
	(AudioServer.get_bus_effect(_sfx_bus, 0) as AudioEffectLowPassFilter).cutoff_hz = 1800.0


## Fade the soundtrack out (and stop it), e.g. before the boss arrives.
func fade_music_out(secs := 1.5) -> void:
	if _music_tween:
		_music_tween.kill()
	_music_tween = create_tween()
	_music_tween.tween_property(music, "volume_db", -40.0, secs)
	_music_tween.tween_callback(music.stop)


## Restart the soundtrack. The boss fight plays it a little lower and slower.
func restart_music(boss := false) -> void:
	if _music_tween:
		_music_tween.kill()
	_music_pitch = 0.9 if boss else 1.0
	music.pitch_scale = _music_pitch
	music.volume_db = 0.0
	if music.stream and not music.playing:
		music.play()


func toggle_mute() -> bool:
	muted = not muted
	AudioServer.set_bus_mute(_music_bus, muted)
	var cfg := ConfigFile.new()
	cfg.load("user://settings.cfg")
	cfg.set_value("audio", "music_muted", muted)
	cfg.save("user://settings.cfg")
	return muted
