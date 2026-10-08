class_name Hud
extends CanvasLayer
## HUD + menus (title, pause, end) built in code, styled like the web version.

signal start_pressed
signal menu_pressed
signal resume_pressed
signal option_changed(key: String, value)
signal touch_fire(down: bool)
signal touch_key(code: int)
signal touch_zoom_toggle
signal music_toggle
signal save_name(name: String)

const INK := Color("121216")
const YELLOW := Color("ffd23f")
const ORANGE := Color("ff8a1f")
const RED := Color("e63946")
const PANEL := Color(0.07, 0.07, 0.09, 0.85)

var font: Font
var font_ui: Font
var root: Control
var game_ui: Control
var popups: Control
var title_screen: Control
var end_screen: Control
var pause_screen: Control

var _score: Label
var _timer: Label
var _hearts: HBoxContainer
var _crosshair: Crosshair
var _hit: Crosshair
var _hit_t := 0.0
var _scope: Control
var _weapons: HBoxContainer
var _reload: Control
var _reload_bar: ColorRect
var _meter_fill: ColorRect
var _meter_box: PanelContainer
var _center: Label
var _center_t := 0.0
var _damage: ColorRect
var _letterbox: Array = []
var _bt_banner: Label
var _zoom_btn: Button
var _last := {}
var _opt_buttons := {}
var _hs_title: VBoxContainer
var _hs_mode: Label
var _end_reason: Label
var _end_rank: Label
var _end_mode: Label
var _end_score: Label
var _end_stats: GridContainer
var _name_row: HBoxContainer
var _name_edit: LineEdit
var _hs_end: VBoxContainer
var touch := false


func _ready() -> void:
	font = load("res://assets/fonts/Bangers-Regular.ttf")
	font_ui = load("res://assets/fonts/Nunito.ttf")
	touch = Config.is_touch()
	root = Control.new()
	root.set_anchors_preset(Control.PRESET_FULL_RECT)
	root.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(root)
	_build_game_ui()
	popups = _full(root)
	_build_title()
	_build_pause()
	_build_end()


# ------------------------------------------------------------ helpers

func _full(parent: Node) -> Control:
	var c = Control.new()
	c.set_anchors_preset(Control.PRESET_FULL_RECT)
	c.mouse_filter = Control.MOUSE_FILTER_IGNORE
	parent.add_child(c)
	return c


func _label(text: String, size: int, col := Color.WHITE, outline := 10, ui := false) -> Label:
	var lb = Label.new()
	lb.text = text
	lb.add_theme_font_override("font", font_ui if ui else font)
	lb.add_theme_font_size_override("font_size", size)
	lb.add_theme_color_override("font_color", col)
	lb.add_theme_color_override("font_outline_color", INK)
	lb.add_theme_constant_override("outline_size", outline)
	lb.add_theme_color_override("font_shadow_color", INK)
	lb.add_theme_constant_override("shadow_offset_x", 3 if outline > 0 else 0)
	lb.add_theme_constant_override("shadow_offset_y", 3 if outline > 0 else 0)
	lb.mouse_filter = Control.MOUSE_FILTER_IGNORE
	return lb


func _panel(col := PANEL, border := INK, radius := 14) -> PanelContainer:
	var p = PanelContainer.new()
	var sb = StyleBoxFlat.new()
	sb.bg_color = col
	sb.border_color = border
	sb.set_border_width_all(3)
	sb.set_corner_radius_all(radius)
	sb.content_margin_left = 14
	sb.content_margin_right = 14
	sb.content_margin_top = 8
	sb.content_margin_bottom = 8
	sb.shadow_color = INK
	sb.shadow_offset = Vector2(4, 4)
	p.add_theme_stylebox_override("panel", sb)
	p.mouse_filter = Control.MOUSE_FILTER_IGNORE
	return p


func _button(text: String, size := 40, secondary := false) -> Button:
	var b = Button.new()
	b.text = text
	b.add_theme_font_override("font", font)
	b.add_theme_font_size_override("font_size", size)
	for st in ["font_color", "font_hover_color", "font_pressed_color", "font_focus_color"]:
		b.add_theme_color_override(st, INK)
	for state_name in ["normal", "hover", "pressed", "focus"]:
		var sb = StyleBoxFlat.new()
		sb.bg_color = Color("fff8ea") if secondary else (ORANGE if state_name == "pressed" else YELLOW)
		if state_name == "hover" and not secondary:
			sb.bg_color = Color("ffde66")
		sb.border_color = INK
		sb.set_border_width_all(4)
		sb.set_corner_radius_all(14)
		sb.shadow_color = INK
		sb.shadow_offset = Vector2(2, 2) if state_name == "pressed" else Vector2(5, 5)
		sb.content_margin_left = 30
		sb.content_margin_right = 30
		sb.content_margin_top = 4
		sb.content_margin_bottom = 4
		b.add_theme_stylebox_override(state_name, sb)
	b.focus_mode = Control.FOCUS_NONE
	return b


func _logo(parent: Node) -> void:
	var v = VBoxContainer.new()
	v.alignment = BoxContainer.ALIGNMENT_CENTER
	v.add_theme_constant_override("separation", -40)
	v.rotation = deg_to_rad(-4)
	var l1 = _label("FATBIKE", 120, Color.WHITE, 16)
	var l2 = _label("SNIPER", 150, YELLOW, 16)
	l1.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	l2.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	v.add_child(l1)
	v.add_child(l2)
	parent.add_child(v)


func _screen() -> Control:
	var bg = ColorRect.new()
	bg.color = Color(0, 0, 0, 0.62)
	bg.set_anchors_preset(Control.PRESET_FULL_RECT)
	root.add_child(bg)
	var scroll = ScrollContainer.new()
	scroll.set_anchors_preset(Control.PRESET_FULL_RECT)
	scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	bg.add_child(scroll)
	var center = CenterContainer.new()
	center.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	center.size_flags_vertical = Control.SIZE_EXPAND_FILL
	center.custom_minimum_size = Vector2(0, 0)
	scroll.add_child(center)
	var v = VBoxContainer.new()
	v.alignment = BoxContainer.ALIGNMENT_CENTER
	v.add_theme_constant_override("separation", 16)
	center.add_child(v)
	bg.set_meta("content", v)
	bg.resized.connect(func(): center.custom_minimum_size = bg.size)
	return bg


# ------------------------------------------------------------ in-game HUD

func _build_game_ui() -> void:
	game_ui = _full(root)
	game_ui.visible = false
	_damage = ColorRect.new()
	_damage.set_anchors_preset(Control.PRESET_FULL_RECT)
	_damage.color = Color(0.9, 0.12, 0.16, 0.0)
	_damage.mouse_filter = Control.MOUSE_FILTER_IGNORE
	game_ui.add_child(_damage)
	_scope = ScopeOverlay.new()
	_scope.set_anchors_preset(Control.PRESET_FULL_RECT)
	_scope.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_scope.visible = false
	game_ui.add_child(_scope)
	for i in 2:
		var bar = ColorRect.new()
		bar.color = Color.BLACK
		bar.mouse_filter = Control.MOUSE_FILTER_IGNORE
		bar.set_anchors_preset(Control.PRESET_TOP_WIDE if i == 0 else Control.PRESET_BOTTOM_WIDE)
		bar.custom_minimum_size = Vector2(0, 0)
		game_ui.add_child(bar)
		_letterbox.append(bar)
	_bt_banner = _label("BULLET TIME", 52, Color("7cf0ff"), 10)
	_bt_banner.set_anchors_preset(Control.PRESET_CENTER_TOP)
	_bt_banner.position.y = 70
	_bt_banner.modulate.a = 0.0
	game_ui.add_child(_bt_banner)

	var score_box = VBoxContainer.new()
	score_box.position = Vector2(24, 12)
	score_box.add_theme_constant_override("separation", -10)
	score_box.add_child(_label("SCORE", 22, YELLOW, 6))
	_score = _label("0", 60, Color.WHITE, 10)
	score_box.add_child(_score)
	game_ui.add_child(score_box)

	_timer = _label("60", 70, Color.WHITE, 12)
	_timer.set_anchors_preset(Control.PRESET_CENTER_TOP)
	_timer.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_timer.grow_horizontal = Control.GROW_DIRECTION_BOTH
	_timer.position.y = 6
	game_ui.add_child(_timer)

	_hearts = HBoxContainer.new()
	_hearts.set_anchors_preset(Control.PRESET_TOP_RIGHT)
	_hearts.grow_horizontal = Control.GROW_DIRECTION_BEGIN
	_hearts.position = Vector2(-24, 20)
	_hearts.add_theme_constant_override("separation", 8)
	game_ui.add_child(_hearts)

	_crosshair = Crosshair.new()
	_crosshair.set_anchors_preset(Control.PRESET_CENTER)
	game_ui.add_child(_crosshair)
	_hit = Crosshair.new()
	_hit.mode = "hit"
	_hit.set_anchors_preset(Control.PRESET_CENTER)
	_hit.modulate.a = 0.0
	game_ui.add_child(_hit)

	_center = _label("", 120, YELLOW, 16)
	_center.set_anchors_preset(Control.PRESET_CENTER)
	_center.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_center.grow_horizontal = Control.GROW_DIRECTION_BOTH
	_center.grow_vertical = Control.GROW_DIRECTION_BOTH
	_center.position.y = -140
	game_ui.add_child(_center)

	_reload = VBoxContainer.new()
	_reload.set_anchors_preset(Control.PRESET_CENTER)
	_reload.grow_horizontal = Control.GROW_DIRECTION_BOTH
	_reload.position = Vector2(-60, 70)
	var rb_bg = ColorRect.new()
	rb_bg.color = Color(0, 0, 0, 0.5)
	rb_bg.custom_minimum_size = Vector2(120, 10)
	_reload_bar = ColorRect.new()
	_reload_bar.color = YELLOW
	_reload_bar.size = Vector2(0, 10)
	rb_bg.add_child(_reload_bar)
	_reload.add_child(rb_bg)
	var rl = _label("HERLADEN", 22, Color.WHITE, 6)
	rl.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_reload.add_child(rl)
	_reload.visible = false
	game_ui.add_child(_reload)

	_weapons = HBoxContainer.new()
	_weapons.set_anchors_preset(Control.PRESET_BOTTOM_RIGHT)
	_weapons.grow_horizontal = Control.GROW_DIRECTION_BEGIN
	_weapons.grow_vertical = Control.GROW_DIRECTION_BEGIN
	_weapons.position = Vector2(-20, -20)
	_weapons.add_theme_constant_override("separation", 8)
	_weapons.alignment = BoxContainer.ALIGNMENT_END
	game_ui.add_child(_weapons)

	_meter_box = _panel()
	_meter_box.set_anchors_preset(Control.PRESET_BOTTOM_LEFT)
	_meter_box.grow_vertical = Control.GROW_DIRECTION_BEGIN
	_meter_box.position = Vector2(20, -20)
	var mv = VBoxContainer.new()
	mv.add_child(_label("BULLET TIME" + ("" if touch else "  [B]"), 22, Color.WHITE, 6))
	var mbg = ColorRect.new()
	mbg.color = Color(0, 0, 0, 0.55)
	mbg.custom_minimum_size = Vector2(170, 12)
	_meter_fill = ColorRect.new()
	_meter_fill.color = Color("35c2ff")
	_meter_fill.size = Vector2(0, 12)
	mbg.add_child(_meter_fill)
	mv.add_child(mbg)
	_meter_box.add_child(mv)
	game_ui.add_child(_meter_box)
	if touch:
		_meter_box.mouse_filter = Control.MOUSE_FILTER_STOP
		_meter_box.gui_input.connect(func(e): if e is InputEventScreenTouch and e.pressed: touch_key.emit(KEY_B))
		_build_touch_buttons()


func _build_touch_buttons() -> void:
	var fire = _button("VUUR", 34)
	fire.set_anchors_preset(Control.PRESET_BOTTOM_RIGHT)
	fire.custom_minimum_size = Vector2(130, 130)
	fire.position = Vector2(-160, -260)
	fire.button_down.connect(func(): touch_fire.emit(true))
	fire.button_up.connect(func(): touch_fire.emit(false))
	game_ui.add_child(fire)
	var reload = _button("R", 26, true)
	reload.set_anchors_preset(Control.PRESET_BOTTOM_RIGHT)
	reload.position = Vector2(-110, -360)
	reload.button_down.connect(func(): touch_key.emit(KEY_R))
	game_ui.add_child(reload)
	_zoom_btn = _button("ZOOM", 24, true)
	_zoom_btn.set_anchors_preset(Control.PRESET_BOTTOM_RIGHT)
	_zoom_btn.position = Vector2(-330, -200)
	_zoom_btn.button_down.connect(func(): touch_zoom_toggle.emit())
	game_ui.add_child(_zoom_btn)
	var pause = _button("II", 22, true)
	pause.set_anchors_preset(Control.PRESET_CENTER_TOP)
	pause.position = Vector2(110, 14)
	pause.button_down.connect(func(): touch_key.emit(KEY_ESCAPE))
	game_ui.add_child(pause)


func show_game(on: bool) -> void:
	game_ui.visible = on


func set_score(s: int) -> void:
	if _last.get("score") == s:
		return
	_last.score = s
	_score.text = str(s)


func set_time(t: float) -> void:
	var s = maxi(0, ceili(t))
	if _last.get("time") == s:
		return
	_last.time = s
	_timer.text = ("%d:%02d" % [s / 60, s % 60]) if s >= 60 else str(s)
	_timer.add_theme_color_override("font_color", RED if s <= 10 else Color.WHITE)


func set_hearts(n: int, max_n: int) -> void:
	var key = "%d/%d" % [n, max_n]
	if _last.get("hearts") == key:
		return
	_last.hearts = key
	for c in _hearts.get_children():
		c.queue_free()
	for i in max_n:
		var h = HeartIcon.new()
		h.lost = i >= n
		_hearts.add_child(h)


func set_weapons(st: Dictionary) -> void:
	var key = str(st.list) + str(st.index)
	if _last.get("weapons") != key:
		_last.weapons = key
		for c in _weapons.get_children():
			c.queue_free()
		for i in st.list.size():
			var w: Dictionary = st.list[i]
			var active: bool = i == st.index
			var p = _panel(PANEL, YELLOW if active else INK, 12)
			p.modulate.a = 1.0 if active else 0.6
			var v = VBoxContainer.new()
			v.add_theme_constant_override("separation", -6)
			var ammo = "∞" if w.mag < 0 else ("%d/%s" % [w.ammo, "∞" if w.reserve < 0 else str(w.reserve)])
			for t in [[str(i + 1), 14, YELLOW], [w.name, 22, Color.WHITE], [ammo, 24, YELLOW]]:
				var lb = _label(t[0], t[1], t[2], 4)
				lb.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
				v.add_child(lb)
			p.add_child(v)
			p.custom_minimum_size = Vector2(96, 0)
			if touch:
				p.mouse_filter = Control.MOUSE_FILTER_STOP
				var idx = i
				p.gui_input.connect(func(e): if e is InputEventScreenTouch and e.pressed: touch_key.emit(KEY_1 + idx))
			_weapons.add_child(p)
	_crosshair.mode = st.key
	_crosshair.visible = not st.zoom
	_crosshair.queue_redraw()
	_scope.visible = st.zoom
	_reload.visible = st.reload >= 0
	if st.reload >= 0:
		_reload_bar.size.x = 120 * st.reload
	if _zoom_btn:
		_zoom_btn.visible = st.key == "sniper"


func set_aim(pos) -> void:
	for c in [_crosshair, _hit]:
		if pos == null:
			c.set_anchors_preset(Control.PRESET_CENTER)
			c.position = c.get_parent_area_size() / 2.0
		else:
			c.position = pos
	(_scope as ScopeOverlay).center = pos


func set_meter(v: float, active: bool) -> void:
	_meter_fill.size.x = 170 * clampf(v, 0, 1)
	var ready = not active and v >= 1.0
	_meter_fill.color = Color("ff6bf0") if ready else Color("35c2ff")
	_meter_box.scale = Vector2.ONE * (1.0 + (0.04 * sin(Time.get_ticks_msec() * 0.01) if ready else 0.0))


func set_bullet(on: bool) -> void:
	var tw = create_tween().set_parallel()
	for i in 2:
		var bar: ColorRect = _letterbox[i]
		tw.tween_property(bar, "custom_minimum_size:y", root.size.y * 0.07 if on else 0.0, 0.35)
	tw.tween_property(_bt_banner, "modulate:a", 1.0 if on else 0.0, 0.3)


func hit(head: bool) -> void:
	_hit.head = head
	_hit.queue_redraw()
	_hit_t = 0.25


func hurt() -> void:
	_damage.color.a = 0.45


func message(text: String, secs := 0.9) -> void:
	_center.text = text
	_center_t = secs
	_center.scale = Vector2.ONE * 1.6
	_center.pivot_offset = _center.size / 2.0
	create_tween().tween_property(_center, "scale", Vector2.ONE, 0.2)


func _process(dt: float) -> void:
	_hit_t = maxf(0.0, _hit_t - dt)
	_hit.modulate.a = _hit_t / 0.25
	_damage.color.a = maxf(0.0, _damage.color.a - dt * 1.2)
	if _center_t > 0:
		_center_t -= dt
		if _center_t <= 0:
			_center.text = ""


# ------------------------------------------------------------ menus

func _build_title() -> void:
	title_screen = _screen()
	var v: VBoxContainer = title_screen.get_meta("content")
	_logo(v)
	var tag = _label("ZIT. RICHT. SCHIET. HOEVEEL KUN JIJ ER NEERHALEN?", 32, Color.WHITE, 6)
	tag.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	v.add_child(tag)
	var opts = HBoxContainer.new()
	opts.alignment = BoxContainer.ALIGNMENT_CENTER
	opts.add_theme_constant_override("separation", 16)
	for group in [["TIJD", "round_time", [[60, "1 MIN"], [180, "3 MIN"], [300, "5 MIN"]]],
			["NIVEAU", "level", [["easy", "MAKKELIJK"], ["normal", "NORMAAL"], ["hard", "MOEILIJK"]]]]:
		var p = _panel()
		p.mouse_filter = Control.MOUSE_FILTER_PASS
		var h = HBoxContainer.new()
		h.add_child(_label(group[0], 22, YELLOW, 4))
		_opt_buttons[group[1]] = []
		for o in group[2]:
			var b = _button(o[1], 22, true)
			var key: String = group[1]
			var val = o[0]
			b.set_meta("value", val)
			b.pressed.connect(func(): option_changed.emit(key, val))
			h.add_child(b)
			_opt_buttons[group[1]].append(b)
		p.add_child(h)
		opts.add_child(p)
	v.add_child(opts)
	var start = _button("SPELEN", 48)
	start.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
	start.pressed.connect(func(): start_pressed.emit())
	v.add_child(start)
	var cards = HBoxContainer.new()
	cards.alignment = BoxContainer.ALIGNMENT_CENTER
	cards.add_theme_constant_override("separation", 16)
	var controls = "Slepen: rondkijken\nTik op een fatbiker: schieten\nVUUR: schiet op het vizier\nWapens aantikken, ZOOM voor de sniper\nBullet time: knop linksonder" if touch \
		else "Muis: richten\nLinkermuisknop: schieten\nRechtermuisknop of Shift: inzoomen\n1-4 of scrollwiel: wapen wisselen\nR: herladen   Esc: pauze   M: muziek\nB of spatie: bullet time"
	cards.add_child(_card("BESTURING", controls))
	cards.add_child(_card("PUNTEN", "Fatbiker van z'n fiets +100\nHeadshot +50   Wheelie-gozer x2\nMeerdere in één schot +100 per extra\nMes uit de lucht schieten +150\nSpeaker-baas +500 (3 treffers)"))
	var hs = _card("HALL OF FAME", "")
	_hs_title = VBoxContainer.new()
	_hs_mode = _label("", 14, Color("c8bfae"), 0, true)
	hs.get_child(0).add_child(_hs_mode)
	hs.get_child(0).add_child(_hs_title)
	cards.add_child(hs)
	v.add_child(cards)
	var music = _button("♪ MUZIEK", 20, true)
	music.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
	music.pressed.connect(func(): music_toggle.emit())
	v.add_child(music)


func _card(title: String, body: String) -> PanelContainer:
	var p = _panel()
	p.custom_minimum_size = Vector2(300, 0)
	var v = VBoxContainer.new()
	v.add_child(_label(title, 28, YELLOW, 4))
	if body != "":
		v.add_child(_label(body, 16, Color("fff8ea"), 0, true))
	p.add_child(v)
	return p


func sync_options(settings: Dictionary) -> void:
	for key in _opt_buttons:
		for b in _opt_buttons[key]:
			var on: bool = b.get_meta("value") == settings[key]
			b.modulate = Color(1, 1, 1, 1) if on else Color(1, 1, 1, 0.55)
			b.add_theme_color_override("font_color", ORANGE.darkened(0.3) if on else INK)


func render_scores(box: VBoxContainer, list: Array, mode_label: String, highlight := -1) -> void:
	for c in box.get_children():
		c.queue_free()
	if box == _hs_title:
		_hs_mode.text = mode_label
	if list.is_empty():
		box.add_child(_label("Nog geen scores. Wees de eerste!", 15, Color("c8bfae"), 0, true))
		return
	for i in list.size():
		var e: Dictionary = list[i]
		var lb = _label("%d. %s  —  %d" % [i + 1, e.name, e.score], 16, YELLOW if i == highlight else Color("fff8ea"), 0, true)
		box.add_child(lb)


func show_title(on: bool) -> void:
	title_screen.visible = on


func _build_pause() -> void:
	pause_screen = _screen()
	var v: VBoxContainer = pause_screen.get_meta("content")
	v.add_child(_label("GEPAUZEERD", 90, YELLOW, 12))
	var b = _button("VERDER", 40)
	b.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
	b.pressed.connect(func(): resume_pressed.emit())
	v.add_child(b)
	var m = _button("MENU", 24, true)
	m.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
	m.pressed.connect(func(): menu_pressed.emit())
	v.add_child(m)
	pause_screen.visible = false


func show_pause(on: bool) -> void:
	pause_screen.visible = on


func _build_end() -> void:
	end_screen = _screen()
	var v: VBoxContainer = end_screen.get_meta("content")
	_end_reason = _label("TIJD OP!", 90, YELLOW, 12)
	_end_rank = _label("", 44, Color.WHITE, 8)
	_end_mode = _label("", 16, Color("c8bfae"), 0, true)
	_end_score = _label("0", 110, ORANGE, 12)
	for lb in [_end_reason, _end_rank, _end_mode, _end_score]:
		lb.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		v.add_child(lb)
	var sp = _panel()
	_end_stats = GridContainer.new()
	_end_stats.columns = 3
	_end_stats.add_theme_constant_override("h_separation", 30)
	sp.add_child(_end_stats)
	sp.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
	v.add_child(sp)
	_name_row = HBoxContainer.new()
	_name_row.alignment = BoxContainer.ALIGNMENT_CENTER
	_name_edit = LineEdit.new()
	_name_edit.placeholder_text = "Jouw naam"
	_name_edit.max_length = 14
	_name_edit.custom_minimum_size = Vector2(240, 0)
	_name_edit.add_theme_font_override("font", font)
	_name_edit.add_theme_font_size_override("font_size", 28)
	_name_row.add_child(_name_edit)
	var save = _button("OPSLAAN", 26)
	save.pressed.connect(func(): save_name.emit(_name_edit.text.strip_edges()))
	_name_edit.text_submitted.connect(func(t): save_name.emit(t.strip_edges()))
	_name_row.add_child(save)
	v.add_child(_name_row)
	_hs_end = VBoxContainer.new()
	_hs_end.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
	v.add_child(_hs_end)
	var row = HBoxContainer.new()
	row.alignment = BoxContainer.ALIGNMENT_CENTER
	row.add_theme_constant_override("separation", 16)
	var menu = _button("MENU", 26, true)
	menu.pressed.connect(func(): menu_pressed.emit())
	var again = _button("NOG EEN KEER", 40)
	again.pressed.connect(func(): start_pressed.emit())
	row.add_child(menu)
	row.add_child(again)
	v.add_child(row)
	end_screen.visible = false


func show_end(reason: String, rank: String, mode_label: String, score: int, stats: Dictionary, qualifies: bool) -> void:
	_end_reason.text = reason
	_end_rank.text = rank
	_end_mode.text = mode_label
	_end_score.text = str(score)
	for c in _end_stats.get_children():
		c.queue_free()
	var acc = roundi(100.0 * stats.hits / stats.shots) if stats.shots > 0 else 0
	for pair in [["Van de fiets", stats.kills], ["Headshots", stats.headshots], ["Nauwkeurigheid", "%d%%" % acc],
			["Messen geraakt", stats.knives], ["Beste combo", "%dx" % stats.best_multi], ["Speaker-bazen", stats.bosses]]:
		var v = VBoxContainer.new()
		v.add_child(_label(pair[0], 15, Color("fff8ea"), 0, true))
		v.add_child(_label(str(pair[1]), 28, YELLOW, 4))
		_end_stats.add_child(v)
	_name_row.visible = qualifies
	_name_edit.text = ""
	end_screen.visible = true


func show_end_scores(list: Array, highlight := -1) -> void:
	render_scores(_hs_end, list, "", highlight)
	_name_row.visible = false if highlight >= 0 else _name_row.visible


func hide_end() -> void:
	end_screen.visible = false


func title_scores(list: Array, mode_label: String) -> void:
	render_scores(_hs_title, list, mode_label)


# ------------------------------------------------------------ small drawn widgets

class HeartIcon extends Control:
	var lost = false

	func _init() -> void:
		custom_minimum_size = Vector2(44, 40)
		mouse_filter = Control.MOUSE_FILTER_IGNORE

	func _draw() -> void:
		var col = Color("e63946") if not lost else Color(0.9, 0.2, 0.25, 0.25)
		var pts = PackedVector2Array()
		for i in 64:
			var t = float(i) / 64.0 * TAU
			var x = 16.0 * pow(sin(t), 3)
			var y = -(13.0 * cos(t) - 5.0 * cos(2 * t) - 2.0 * cos(3 * t) - cos(4 * t))
			pts.append(Vector2(22 + x * 1.2, 20 + y * 1.2))
		var shadow = PackedVector2Array()
		for p in pts:
			shadow.append(p + Vector2(3, 3))
		draw_colored_polygon(shadow, Color("121216"))
		draw_colored_polygon(pts, col)
		pts.append(pts[0])
		draw_polyline(pts, Color("121216"), 2.5, true)


class Crosshair extends Control:
	var mode = "katapult"
	var head = false

	func _init() -> void:
		mouse_filter = Control.MOUSE_FILTER_IGNORE

	func _draw() -> void:
		var ink = Color("121216")
		if mode == "hit":
			var c = Color("e63946") if head else Color.WHITE
			for s in [Vector2(1, 1), Vector2(1, -1), Vector2(-1, 1), Vector2(-1, -1)]:
				draw_line(s * 8, s * 20, ink, 7)
				draw_line(s * 8, s * 20, c, 4)
			return
		if mode == "shotgun":
			draw_arc(Vector2.ZERO, 34, 0, TAU, 48, ink, 6)
			draw_arc(Vector2.ZERO, 34, 0, TAU, 48, Color.WHITE, 3)
			draw_circle(Vector2.ZERO, 4, Color.WHITE)
			return
		if mode == "bazooka":
			for i in 12:
				var a = float(i) / 12.0 * TAU
				draw_arc(Vector2.ZERO, 26, a, a + 0.3, 6, Color("ffd23f"), 3)
		for d in [Vector2.UP, Vector2.DOWN, Vector2.LEFT, Vector2.RIGHT]:
			draw_line(d * 6, d * 17, ink, 6)
			draw_line(d * 6, d * 17, Color.WHITE, 3)


class ScopeOverlay extends Control:
	var center = null

	func _draw() -> void:
		var c: Vector2 = center if center != null else size / 2.0
		var r = size.y * 0.34
		var w = size.length() * 2.0
		draw_arc(c, r + w / 2.0, 0, TAU, 128, Color.BLACK, w)
		draw_arc(c, r, 0, TAU, 96, Color("111111"), 8)
		draw_line(c + Vector2(-r, 0), c + Vector2(r, 0), Color("111111"), 2)
		draw_line(c + Vector2(0, -r), c + Vector2(0, r), Color("111111"), 2)

	func _process(_dt: float) -> void:
		if visible:
			queue_redraw()
