extends Node
## Headless check that rider routes on the Henri Donutplein miss the gallery pillars, market stalls and walls.
## Run: Godot --headless --path godot res://tests/route_check.tscn


func _rects() -> Array:
	var out = []  # Blender-coordinate rectangles [x0, x1, y0, y1, name], padded by half a bike width
	var pitch = (8.5 + 11.3) / 4.0
	for i in 5:
		var x = clampf(-11.3 + i * pitch, -11.3 + 0.4, 8.5 - 0.4)
		out.append([x - 0.4, x + 0.4, 20.0, 20.7, "pillar %d" % i])
	for y in [27.5, 31.0, 34.5, 38.0, 41.5]:
		out.append([8.75, 10.85, y - 1.6, y + 1.6, "stall W %.1f" % y])
	for y in [21.0, 24.5, 28.0, 31.5, 35.0, 38.5]:
		out.append([13.55, 15.75, y - 1.6, y + 1.6, "stall E %.1f" % y])
	out.append([-11.3, 8.5, 23.4, 34.0, "gallery shops"])
	out.append([-4.0, 8.5, 35.0, 60.0, "road W buildings"])
	out.append([16.0, 28.0, 17.0, 60.0, "road E buildings"])
	out.append([16.0, 40.0, -14.0, 16.0, "gemeentehuis"])
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
