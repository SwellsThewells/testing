extends SceneTree
# Converts imported (exported) resources back to source assets.
# Reads a JSON job list from the path given after "--jobs".

func _write_bytes(path, bytes):
	var f = File.new()
	if f.open(path, File.WRITE) != OK:
		return false
	f.store_buffer(bytes)
	f.close()
	return true

func _mesh_to_obj(mesh, dst):
	var lines = PoolStringArray()
	lines.append("# Recovered from Godot imported mesh")
	var base = 1
	for s in range(mesh.get_surface_count()):
		var arr = mesh.surface_get_arrays(s)
		var verts = arr[Mesh.ARRAY_VERTEX]
		var norms = arr[Mesh.ARRAY_NORMAL]
		var uvs = arr[Mesh.ARRAY_TEX_UV]
		var idx = arr[Mesh.ARRAY_INDEX]
		var has_n = norms != null and norms.size() == verts.size()
		var has_uv = uvs != null and uvs.size() == verts.size()
		lines.append("o surface_%d" % s)
		for v in verts:
			lines.append("v %s %s %s" % [str(v.x), str(v.y), str(v.z)])
		if has_uv:
			for uv in uvs:
				lines.append("vt %s %s" % [str(uv.x), str(1.0 - uv.y)])
		if has_n:
			for n in norms:
				lines.append("vn %s %s %s" % [str(n.x), str(n.y), str(n.z)])
		var tri = []
		if idx != null and idx.size() > 0:
			tri = idx
		else:
			tri = range(verts.size())
		var i = 0
		while i + 2 < tri.size():
			var f = "f"
			# Godot uses clockwise winding; OBJ is counter-clockwise.
			for k in [tri[i], tri[i + 2], tri[i + 1]]:
				var n = k + base
				if has_uv and has_n:
					f += " %d/%d/%d" % [n, n, n]
				elif has_uv:
					f += " %d/%d" % [n, n]
				elif has_n:
					f += " %d//%d" % [n, n]
				else:
					f += " %d" % n
			lines.append(f)
			i += 3
		base += verts.size()
	var file = File.new()
	if file.open(dst, File.WRITE) != OK:
		return false
	file.store_string(lines.join("\n") + "\n")
	file.close()
	return true

func _init():
	var args = OS.get_cmdline_args()
	var jobs_path = ""
	for i in range(args.size()):
		if args[i] == "--jobs":
			jobs_path = args[i + 1]
	var f = File.new()
	f.open(jobs_path, File.READ)
	var jobs = parse_json(f.get_as_text())
	f.close()
	var failed = 0
	for job in jobs:
		var res = ResourceLoader.load(job.src, "", true)
		var ok = false
		if res == null:
			printerr("LOAD FAILED: ", job.src)
		elif job.kind == "texture":
			var img = res.get_data()
			if img != null and img.is_compressed():
				img.decompress()
			if img != null and not img.is_compressed():
				if job.dst.ends_with(".jpg") or job.dst.ends_with(".jpeg"):
					ok = img.save_png(job.dst + ".tmp.png") == OK
				else:
					ok = img.save_png(job.dst) == OK
		elif job.kind == "wav":
			ok = res.save_to_wav(job.dst) == OK
		elif job.kind == "rawdata":
			ok = _write_bytes(job.dst, res.data)
		elif job.kind == "obj":
			ok = _mesh_to_obj(res, job.dst)
		elif job.kind == "info":
			print("INFO ", job.src, " ", res.get_class())
			ok = true
		if not ok:
			failed += 1
			printerr("FAILED: ", job.kind, " ", job.src)
		else:
			print("OK ", job.dst)
	print("DONE failed=", failed)
	quit()
