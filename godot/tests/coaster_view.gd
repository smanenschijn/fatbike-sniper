extends Node3D
## Screenshots of the Wollahbi coaster train at a few points of the ride (lift, drop, loop) from a free camera.
## Run: Godot --path godot res://tests/coaster_view.tscn -- --out=/tmp/coaster


func _ready() -> void:
	var out := "/tmp/coaster"
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--out="):
			out = a.substr(6)
	Config.use_map("wollahbi")
	var w := World.new()
	add_child(w)
	var cam := Camera3D.new()
	cam.fov = 38.0
	add_child(cam)
	cam.current = true
	var c := w.coaster()
	c.time_scale = 0.0
	# [fraction of the track, camera (Blender x, y, z)]
	var views := [[0.17, Vector3(-4, 30, 6)], [0.33, Vector3(-6, 28, 8)], [0.45, Vector3(4, 28, 6)], [0.5, Vector3(4, 28, 6)],
		[0.55, Vector3(4, 28, 6)], [0.62, Vector3(30, 30, 5)]]
	for i in views.size():
		c.head = c.length * views[i][0]
		c._place()
		var b: Vector3 = views[i][1]
		cam.look_at_from_position(Config.B(b.x, b.y, b.z), c.train_position())
		for f in 4:
			await get_tree().process_frame
		get_viewport().get_texture().get_image().save_png("%s_%d.png" % [out, i])
	get_tree().quit()
