extends Node
## Headless check that rider routes on the Henri Donutplein miss the gallery pillars, market stalls and walls.
## Run: Godot --headless --path godot res://tests/route_check.tscn


func _rects() -> Array:
	var out = []  # Blender-coordinate rectangles [x0, x1, y0, y1, name]; see blender/build_dunant.py
	var pitch = 15.5 / 4.0
	for i in 5:
		var x = clampf(-7.0 + i * pitch, -7.0 + 0.4, 8.5 - 0.4)
		out.append([x - 0.4, x + 0.4, 20.0, 20.7, "pillar %d" % i])
	for y in [27.5, 31.0, 34.5, 38.0, 41.5]:
		out.append([8.75, 10.85, y - 1.6, y + 1.6, "stall W %.1f" % y])
	for y in [26.5, 30.0, 33.5, 37.0, 40.5]:
		out.append([13.55, 15.75, y - 1.6, y + 1.6, "stall E %.1f" % y])
	out.append([-7.0, 8.5, 23.4, 34.0, "gallery shops"])
	out.append([-15.0, -7.0, 19.9, 28.0, "tower"])
	out.append([-15.0, -3.0, 29.0, 60.0, "west road E buildings"])
	out.append([-34.0, -22.0, -14.0, 60.0, "shop row / west road W buildings"])
	out.append([-4.0, 8.5, 35.0, 60.0, "market road W buildings"])
	out.append([16.0, 28.0, 23.0, 60.0, "market road E buildings"])
	out.append([16.0, 32.0, -14.0, 16.0, "gemeentehuis"])
	out.append([28.0, 60.0, 23.0, 35.0, "east road N buildings"])
	out.append([32.0, 60.0, 4.0, 16.0, "east road S buildings"])
	out.append([-22.0, 16.0, -26.0, -14.0, "ijssalon block"])
	return out


func _ready() -> void:
	Config.use_map("donut")
	var riders = Riders.new()
	var rects = _rects()
	var bad = {}
	var n = 400
	for t in n:
		var entry = riders._weighted_entry(null)
		var exit = riders._weighted_entry(entry)
		var r = riders._route(entry, exit, randf() < 0.4)
		var c: Curve3D = r.curve
		var L = c.get_baked_length()
		var d = 0.0
		while d < L:
			var p = c.sample_baked(d)
			var bx = p.x
			var by = -p.z
			for q in rects:
				var pad = 0.35
				if bx > q[0] - pad and bx < q[1] + pad and by > q[2] - pad and by < q[3] + pad:
					var key = "%s (%s -> %s)" % [q[4], entry.name, exit.name]
					bad[key] = bad.get(key, 0) + 1
			d += 0.25
	print("routes: ", n, " collisions: ", bad.size())
	for k in bad:
		print("  ", k, " x", bad[k])
	riders.free()
	get_tree().quit()
