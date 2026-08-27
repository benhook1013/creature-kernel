extends SceneTree

const MAX_ARTIFACT_BYTES := 32 * 1024 * 1024
const MAX_VERTICES := 100000
const MAX_FACES := 200000
const MAX_BONES := 64
const MAX_PROXIES := 64
const EPSILON := 1.0e-5
const TRANSLATIONS := [Vector3(-8.0, 0.0, 0.0), Vector3(8.0, 0.0, 0.0)]
const ARTIFACT_NAMES := [
	"neutral.ply",
	"posed.ply",
	"skeleton.json",
	"weights.json",
	"proxies-neutral.json",
	"proxies-posed.json",
]
const PROXY_LINEAGE_FIELDS := ["owned_part", "partition_rule", "partition_vertex_count", "radius_rule"]

var _failure := ""


func _init() -> void:
	var exit_code := _run_smoke()
	quit(exit_code)


func _run_smoke() -> int:
	var options = _parse_arguments()
	if options.is_empty():
		return _fail_exit()

	var validated = JSON.parse_string(options.validated_json)
	if typeof(validated) != TYPE_DICTIONARY:
		return _fail("validated projection payload is not an object")
	if not _validate_options_against_projection(options, validated):
		return _fail_exit()

	var loaded_profiles: Array[Dictionary] = []
	for index in range(2):
		var profile_id: String = options.profile_ids[index]
		var profile_payload: Dictionary = _profile_payload(validated, profile_id)
		if profile_payload.is_empty():
			return _fail_exit()
		var loaded = _load_profile(options.gallery_path, profile_id, profile_payload, TRANSLATIONS[index])
		if loaded.is_empty():
			_release_profiles(loaded_profiles)
			return _fail_exit()
		loaded_profiles.append(loaded)

	if not _check_separation(loaded_profiles):
		_release_profiles(loaded_profiles)
		return _fail_exit()

	var report := _build_report(options, validated, loaded_profiles)
	_release_profiles(loaded_profiles)
	if not _write_report(options.report_path, report):
		return _fail_exit()
	return 0


func _parse_arguments() -> Dictionary:
	var arguments := OS.get_cmdline_user_args()
	var result := {
		"gallery_path": "",
		"profile_ids": [],
		"report_path": "",
		"validated_json": "",
	}
	var index := 0
	while index < arguments.size():
		var argument: String = arguments[index]
		if argument == "--gallery" or argument == "--report" or argument == "--validated-json" or argument == "--profile-id":
			if index + 1 >= arguments.size():
				_failure = "missing value after %s" % argument
				return {}
			var value: String = arguments[index + 1]
			if argument == "--gallery":
				result.gallery_path = value
			elif argument == "--report":
				result.report_path = value
			elif argument == "--validated-json":
				result.validated_json = value
			else:
				result.profile_ids.append(value)
			index += 2
		else:
			_failure = "unsupported user argument: %s" % argument
			return {}
	return result


func _validate_options_against_projection(options: Dictionary, validated: Dictionary) -> bool:
	if options.gallery_path == "" or options.report_path == "" or options.validated_json == "":
		_failure = "gallery, report, and validated projection arguments are required"
		return false
	if options.profile_ids.size() != 2 or options.profile_ids[0] == options.profile_ids[1]:
		_failure = "exactly two distinct profile IDs are required"
		return false
	if not validated.has("profile_ids") or typeof(validated.profile_ids) != TYPE_ARRAY or validated.profile_ids.size() != 2:
		_failure = "validated projection must contain exactly two selected profile IDs"
		return false
	if validated.profile_ids != options.profile_ids:
		_failure = "selected profile IDs disagree with the validated projection"
		return false
	if validated.get("godot_version", "") != "4.7.2.stable.official.ed1daf0bf":
		_failure = "validated Godot version is not the pinned launcher version"
		return false
	if not validated.has("profiles") or typeof(validated.profiles) != TYPE_ARRAY or validated.profiles.size() != 2:
		_failure = "validated projection must contain exactly two profile records"
		return false
	for profile_id in options.profile_ids:
		if _profile_payload(validated, profile_id).is_empty():
			_failure = "validated projection does not contain profile %s" % profile_id
			return false
	return true


func _profile_payload(validated: Dictionary, profile_id: String) -> Dictionary:
	for profile in validated.profiles:
		if typeof(profile) == TYPE_DICTIONARY and profile.get("profile_id", "") == profile_id:
			return profile
	return {}


func _load_profile(gallery_path: String, profile_id: String, profile_payload: Dictionary, translation: Vector3) -> Dictionary:
	var artifact_bytes: Dictionary = {}
	var artifacts = profile_payload.get("artifacts", [])
	if typeof(artifacts) != TYPE_ARRAY or artifacts.size() != ARTIFACT_NAMES.size():
		_failure = "%s validated artifact list is incomplete" % profile_id
		return {}
	for artifact_index in range(ARTIFACT_NAMES.size()):
		var artifact = artifacts[artifact_index]
		if typeof(artifact) != TYPE_DICTIONARY:
			_failure = "%s has an invalid validated artifact record" % profile_id
			return {}
		var relative_path: String = artifact.get("path", "")
		var expected_path: String = profile_id + "/" + ARTIFACT_NAMES[artifact_index]
		if relative_path != expected_path or relative_path.is_absolute_path():
			_failure = "%s has an unsafe or reordered validated artifact path" % profile_id
			return {}
		var bytes = _read_bytes(gallery_path.path_join(relative_path), "%s %s" % [profile_id, relative_path])
		if bytes.is_empty() and int(artifact.get("bytes", -1)) != 0:
			return {}
		if bytes.size() != int(artifact.get("bytes", -1)):
			_failure = "%s %s byte count disagrees with validated view" % [profile_id, relative_path]
			return {}
		var digest := _sha256(bytes)
		if digest != String(artifact.get("sha256", "")):
			_failure = "%s %s hash disagrees with validated view" % [profile_id, relative_path]
			return {}
		artifact_bytes[relative_path] = bytes

	var neutral_path := profile_id + "/neutral.ply"
	var neutral = _parse_ply(artifact_bytes.get(neutral_path, PackedByteArray()), "%s neutral.ply" % profile_id)
	if neutral.is_empty():
		return {}
	var metrics_bytes = _read_bytes(gallery_path.path_join(profile_id + "/metrics.json"), "%s %s/metrics.json" % [profile_id, profile_id])
	if metrics_bytes.is_empty():
		return {}
	var metrics = _parse_json(metrics_bytes, "%s metrics.json" % profile_id)
	var skeleton = _parse_json(artifact_bytes.get(profile_id + "/skeleton.json", PackedByteArray()), "%s skeleton.json" % profile_id)
	var weights = _parse_json(artifact_bytes.get(profile_id + "/weights.json", PackedByteArray()), "%s weights.json" % profile_id)
	var proxies = _parse_json(artifact_bytes.get(profile_id + "/proxies-neutral.json", PackedByteArray()), "%s proxies-neutral.json" % profile_id)
	if metrics.is_empty() or skeleton.is_empty() or weights.is_empty() or proxies.is_empty():
		return {}
	if metrics != profile_payload.get("metrics", {}):
		_failure = "%s loaded metrics disagree with the validator-backed metrics projection" % profile_id
		return {}
	if not _validate_structural_records(profile_id, neutral, metrics, skeleton, weights, proxies):
		return {}

	var mesh := ArrayMesh.new()
	var arrays: Array = []
	arrays.resize(Mesh.ARRAY_MAX)
	arrays[Mesh.ARRAY_VERTEX] = neutral.vertices
	arrays[Mesh.ARRAY_NORMAL] = neutral.normals
	arrays[Mesh.ARRAY_INDEX] = neutral.indices
	mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arrays)
	if mesh.get_surface_count() != 1:
		_failure = "%s mesh did not create exactly one surface" % profile_id
		return {}

	var root := Node3D.new()
	root.name = "Profile_%s" % profile_id
	root.position = translation
	get_root().add_child(root)
	var mesh_instance := MeshInstance3D.new()
	mesh_instance.name = "NeutralMesh"
	mesh_instance.mesh = mesh
	root.add_child(mesh_instance)
	var body := StaticBody3D.new()
	body.name = "NeutralCollisionProxies"
	root.add_child(body)

	var proxy_aabb := AABB()
	var has_proxy_bounds := false
	for proxy in proxies.proxies:
		var start_value = _vector3(proxy.a, "%s proxy a" % profile_id)
		var end_value = _vector3(proxy.b, "%s proxy b" % profile_id)
		if start_value == null or end_value == null:
			return _profile_failure(root, "%s proxy endpoint is not a valid finite vector" % profile_id)
		var start: Vector3 = start_value
		var end: Vector3 = end_value
		var radius := float(proxy.radius)
		var segment := end - start
		var segment_length := segment.length()
		if not is_finite(segment_length) or segment_length <= 1.0e-12 or not is_finite(radius) or radius <= 0.0:
			return _profile_failure(root, "%s contains an invalid capsule segment" % profile_id)
		var direction := segment / segment_length
		var basis := Basis(Quaternion(Vector3.UP, direction))
		var shape := CapsuleShape3D.new()
		shape.radius = radius
		shape.height = segment_length + 2.0 * radius
		var collision := CollisionShape3D.new()
		collision.name = "Capsule_%s" % String(proxy.bone_id)
		collision.shape = shape
		collision.transform = Transform3D(basis, (start + end) * 0.5)
		body.add_child(collision)
		if abs(collision.transform.basis.y.normalized().dot(direction) - 1.0) > EPSILON:
			return _profile_failure(root, "%s capsule positive-Y alignment is invalid" % profile_id)
		if abs(shape.height - (segment_length + 2.0 * radius)) > EPSILON:
			return _profile_failure(root, "%s capsule height rule is invalid" % profile_id)
		var proxy_min := Vector3(min(start.x, end.x) - radius, min(start.y, end.y) - radius, min(start.z, end.z) - radius)
		var proxy_max := Vector3(max(start.x, end.x) + radius, max(start.y, end.y) + radius, max(start.z, end.z) + radius)
		var proxy_box := AABB(proxy_min, proxy_max - proxy_min)
		if not has_proxy_bounds:
			proxy_aabb = proxy_box
			has_proxy_bounds = true
		else:
			proxy_aabb = proxy_aabb.merge(proxy_box)

	var local_aabb: AABB = mesh.get_aabb()
	if not _aabb_matches(local_aabb, neutral.aabb):
		return _profile_failure(root, "%s ArrayMesh AABB differs from parsed neutral PLY" % profile_id)
	return {
		"profile_id": profile_id,
		"candidate_profile_sha256": String(profile_payload.get("candidate_profile_sha256", "")),
		"root": root,
		"metrics": metrics,
		"mesh_aabb": _aabb_json(local_aabb),
		"proxy_aabb": _aabb_json(proxy_aabb),
		"profile_translation": _vector_json(translation),
		"counts": {
			"vertex_count": int(neutral.vertices.size()),
			"face_count": int(neutral.indices.size() / 3),
			"bone_count": int(skeleton.neutral.bones.size()),
			"proxy_count": int(proxies.proxies.size()),
			"weight_vertex_count": int(weights.vertex_count),
			"influence_count": int(_influence_count(weights.influences)),
		},
		"proxy_segments": {
			"segment_count": int(proxies.proxies.size()),
			"radius_count": int(proxies.proxies.size()),
			"capsule_height_rule": "segment_length + 2*radius",
			"positive_y_alignment_checked": true,
		},
		"node_counts": {
			"profile_root": 1,
			"mesh_instance_3d": 1,
			"static_body_3d": 1,
			"collision_shape_3d": int(proxies.proxies.size()),
			"total_profile_nodes": int(3 + proxies.proxies.size()),
		},
		"translated_mesh_aabb": _aabb_json(AABB(local_aabb.position + translation, local_aabb.size)),
		"translated_proxy_aabb": _aabb_json(AABB(proxy_aabb.position + translation, proxy_aabb.size)),
	}


func _validate_structural_records(profile_id: String, neutral: Dictionary, metrics: Dictionary, skeleton: Dictionary, weights: Dictionary, proxies: Dictionary) -> bool:
	if metrics.get("profile_id", "") != profile_id or metrics.get("format", "") != "creature-kernel.disposable-structural-embodiment-gallery.v1":
		_failure = "%s metrics lineage is invalid" % profile_id
		return false
	if int(metrics.get("neutral_vertex_count", -1)) != neutral.vertices.size() or int(metrics.get("posed_vertex_count", -1)) != neutral.vertices.size():
		_failure = "%s metrics vertex count is invalid" % profile_id
		return false
	if int(metrics.get("face_count", -1)) != neutral.indices.size() / 3:
		_failure = "%s metrics face count is invalid" % profile_id
		return false
	if int(metrics.get("bone_count", -1)) <= 0 or int(metrics.get("bone_count", -1)) > MAX_BONES:
		_failure = "%s metrics bone count is invalid" % profile_id
		return false
	if int(metrics.get("proxy_count", -1)) <= 0 or int(metrics.get("proxy_count", -1)) > MAX_PROXIES:
		_failure = "%s metrics proxy count is invalid" % profile_id
		return false
	var neutral_state = skeleton.get("neutral", null)
	var posed_state = skeleton.get("posed", null)
	if not skeleton.has("profile_id") or skeleton.profile_id != profile_id or not skeleton.has("neutral") or not skeleton.has("posed") or typeof(neutral_state) != TYPE_DICTIONARY or typeof(posed_state) != TYPE_DICTIONARY:
		_failure = "%s skeleton lineage or state records are invalid" % profile_id
		return false
	if typeof(neutral_state.get("bones", null)) != TYPE_ARRAY or typeof(posed_state.get("bones", null)) != TYPE_ARRAY:
		_failure = "%s skeleton bones are invalid" % profile_id
		return false
	if neutral_state.bones.size() != int(metrics.bone_count) or posed_state.bones.size() != int(metrics.bone_count):
		_failure = "%s skeleton bone count is invalid" % profile_id
		return false
	var bone_ids := {}
	for bone in neutral_state.bones:
		if typeof(bone) != TYPE_DICTIONARY or not bone.has("id") or bone_ids.has(bone.id):
			_failure = "%s skeleton bone IDs are invalid" % profile_id
			return false
		bone_ids[bone.id] = true
	if typeof(weights.get("influences", null)) != TYPE_ARRAY or weights.get("profile_id", "") != profile_id or int(weights.get("vertex_count", -1)) != neutral.vertices.size():
		_failure = "%s weights are invalid" % profile_id
		return false
	if weights.influences.size() != neutral.vertices.size():
		_failure = "%s weights do not cover every vertex" % profile_id
		return false
	for row in weights.influences:
		if typeof(row) != TYPE_ARRAY or row.is_empty():
			_failure = "%s contains an empty weight row" % profile_id
			return false
		var total := 0.0
		for influence in row:
			if typeof(influence) != TYPE_DICTIONARY or not bone_ids.has(influence.get("bone_id", "")):
				_failure = "%s contains an invalid weight bone" % profile_id
				return false
			var weight_value = influence.get("weight", -1.0)
			var weight_type := typeof(weight_value)
			if weight_type != TYPE_INT and weight_type != TYPE_FLOAT:
				_failure = "%s contains an invalid weight value" % profile_id
				return false
			var weight := float(weight_value)
			if not is_finite(weight) or weight < 0.0:
				_failure = "%s contains an invalid weight value" % profile_id
				return false
			total += weight
		if abs(total - 1.0) > 1.0e-6:
			_failure = "%s contains a non-normalized weight row" % profile_id
			return false
	if typeof(proxies) != TYPE_DICTIONARY or proxies.get("format", "") != "creature-kernel.disposable-structural-embodiment-gallery.v1" or proxies.get("profile_id", "") != profile_id or proxies.get("state", "") != "neutral" or proxies.get("radius_transform", "") != "unchanged":
		_failure = "%s neutral proxies are invalid" % profile_id
		return false
	if typeof(proxies.get("proxies", null)) != TYPE_ARRAY:
		_failure = "%s neutral proxies are invalid" % profile_id
		return false
	if proxies.proxies.size() != int(metrics.proxy_count):
		_failure = "%s proxy count is invalid" % profile_id
		return false
	var proxy_bones := {}
	for proxy in proxies.proxies:
		if typeof(proxy) != TYPE_DICTIONARY or not proxy.has("bone_id") or proxy.get("kind", "") != "capsule" or proxy_bones.has(proxy.get("bone_id", "")) or not bone_ids.has(proxy.get("bone_id", "")):
			_failure = "%s proxy bone coverage is invalid" % profile_id
			return false
		proxy_bones[proxy.bone_id] = true
		for field_name in PROXY_LINEAGE_FIELDS:
			if not proxy.has(field_name):
				_failure = "%s proxy lineage field is missing: %s" % [profile_id, field_name]
				return false
		if not proxy.has("a") or not proxy.has("b") or not proxy.has("radius") or not is_finite(float(proxy.radius)) or float(proxy.radius) <= 0.0:
			_failure = "%s proxy record is invalid" % profile_id
			return false
	if proxy_bones.size() != bone_ids.size():
		_failure = "%s proxy records do not cover every bone" % profile_id
		return false
	if not _bounds_match(metrics.get("neutral_bounds", {}), neutral.aabb):
		_failure = "%s metrics neutral bounds differ from parsed PLY" % profile_id
		return false
	return true


func _parse_ply(bytes: PackedByteArray, where: String) -> Dictionary:
	if bytes.is_empty() or bytes.size() > MAX_ARTIFACT_BYTES:
		_failure = "%s is empty or oversized" % where
		return {}
	for byte in bytes:
		if byte > 127:
			_failure = "%s is not ASCII" % where
			return {}
	var text := bytes.get_string_from_ascii()
	if not text.ends_with("\n") or text.contains("\r"):
		_failure = "%s is not canonical newline-terminated ASCII" % where
		return {}
	var lines := text.split("\n", true)
	if lines.size() < 13 or lines[lines.size() - 1] != "":
		_failure = "%s has an incomplete fixed PLY record stream" % where
		return {}
	if lines[0] != "ply" or lines[1] != "format ascii 1.0" or lines[3] != "property float x" or lines[4] != "property float y" or lines[5] != "property float z" or lines[6] != "property float nx" or lines[7] != "property float ny" or lines[8] != "property float nz" or lines[10] != "property list uchar int vertex_indices" or lines[11] != "end_header":
		_failure = "%s has an unsupported fixed PLY schema" % where
		return {}
	var vertex_count := _canonical_count(lines[2], "element vertex ", MAX_VERTICES, where + " vertex count")
	var face_count := _canonical_count(lines[9], "element face ", MAX_FACES, where + " face count")
	if vertex_count < 0 or face_count < 0 or lines.size() != 12 + vertex_count + face_count + 1:
		_failure = "%s has an invalid record count" % where
		return {}
	var vertices := PackedVector3Array()
	var normals := PackedVector3Array()
	var indices := PackedInt32Array()
	var lower := Vector3(INF, INF, INF)
	var upper := Vector3(-INF, -INF, -INF)
	for index in range(vertex_count):
		var fields := lines[12 + index].split(" ", false)
		if fields.size() != 6:
			_failure = "%s vertex %d does not have six fields" % [where, index]
			return {}
		var values: Array[float] = []
		for field in fields:
			var value := float(field)
			if not is_finite(value):
				_failure = "%s vertex %d contains a non-finite value" % [where, index]
				return {}
			values.append(value)
		var point := Vector3(values[0], values[1], values[2])
		var normal := Vector3(values[3], values[4], values[5])
		if normal.length() <= 1.0e-12:
			_failure = "%s vertex %d has a zero normal" % [where, index]
			return {}
		vertices.append(point)
		normals.append(normal)
		lower.x = min(lower.x, point.x)
		lower.y = min(lower.y, point.y)
		lower.z = min(lower.z, point.z)
		upper.x = max(upper.x, point.x)
		upper.y = max(upper.y, point.y)
		upper.z = max(upper.z, point.z)
	for index in range(face_count):
		var fields := lines[12 + vertex_count + index].split(" ", false)
		if fields.size() != 4 or fields[0] != "3":
			_failure = "%s face %d is not triangular" % [where, index]
			return {}
		var face: Array[int] = []
		for field_index in range(1, 4):
			var parsed := _canonical_integer(fields[field_index], where + " face index")
			if parsed < 0 or parsed >= vertex_count:
				_failure = "%s face %d has an invalid vertex index" % [where, index]
				return {}
			face.append(parsed)
		if face[0] == face[1] or face[1] == face[2] or face[0] == face[2]:
			_failure = "%s face %d is degenerate" % [where, index]
			return {}
		indices.append(face[0])
		indices.append(face[1])
		indices.append(face[2])
	return {"vertices": vertices, "normals": normals, "indices": indices, "aabb": AABB(lower, upper - lower)}


func _canonical_count(line: String, prefix: String, maximum: int, where: String) -> int:
	if not line.begins_with(prefix):
		_failure = "%s has an invalid count prefix" % where
		return -1
	var raw := line.substr(prefix.length())
	var value := _canonical_integer(raw, where)
	if value <= 0 or value > maximum:
		_failure = "%s is outside its bounded positive range" % where
		return -1
	return value


func _canonical_integer(raw: String, where: String) -> int:
	if raw == "" or (raw.length() > 1 and raw.begins_with("0")) or raw.find("-") >= 0 or raw.find("+") >= 0:
		_failure = "%s is not a canonical non-negative integer" % where
		return -1
	var value := int(raw)
	if str(value) != raw:
		_failure = "%s is not a canonical integer" % where
		return -1
	return value


func _read_bytes(path: String, where: String) -> PackedByteArray:
	var file := FileAccess.open(path, FileAccess.READ)
	if file == null:
		_failure = "%s cannot be opened: %s" % [where, path]
		return PackedByteArray()
	if file.get_length() > MAX_ARTIFACT_BYTES:
		_failure = "%s is oversized" % where
		return PackedByteArray()
	return file.get_buffer(file.get_length())


func _parse_json(bytes: PackedByteArray, where: String) -> Dictionary:
	if bytes.is_empty():
		_failure = "%s is empty" % where
		return {}
	var value = JSON.parse_string(bytes.get_string_from_utf8())
	if typeof(value) != TYPE_DICTIONARY:
		_failure = "%s is not a JSON object" % where
		return {}
	return value


func _sha256(bytes: PackedByteArray) -> String:
	var context := HashingContext.new()
	context.start(HashingContext.HASH_SHA256)
	context.update(bytes)
	return context.finish().hex_encode()


func _vector3(value, where: String) -> Variant:
	if typeof(value) != TYPE_ARRAY or value.size() != 3:
		_failure = "%s is not a three-vector" % where
		return null
	for item in value:
		var item_type := typeof(item)
		if item_type != TYPE_INT and item_type != TYPE_FLOAT:
			_failure = "%s contains a non-finite value" % where
			return null
		var numeric := float(item)
		if not is_finite(numeric):
			_failure = "%s contains a non-finite value" % where
			return null
	var result := Vector3(float(value[0]), float(value[1]), float(value[2]))
	return result


func _bounds_match(value, aabb: AABB) -> bool:
	if typeof(value) != TYPE_DICTIONARY or not value.has("min") or not value.has("max"):
		return false
	var minimum = _vector3(value.min, "metrics min")
	var maximum = _vector3(value.max, "metrics max")
	if minimum == null or maximum == null:
		return false
	return (minimum as Vector3).distance_to(aabb.position) <= EPSILON and (maximum as Vector3).distance_to(aabb.end) <= EPSILON


func _aabb_matches(left: AABB, right: AABB) -> bool:
	return left.position.distance_to(right.position) <= EPSILON and left.end.distance_to(right.end) <= EPSILON


func _aabb_json(aabb: AABB) -> Dictionary:
	return {"min": _vector_json(aabb.position), "max": _vector_json(aabb.end)}


func _vector_json(value: Vector3) -> Array[float]:
	return [value.x, value.y, value.z]


func _influence_count(rows) -> int:
	var total := 0
	for row in rows:
		total += row.size()
	return total


func _check_separation(loaded_profiles: Array[Dictionary]) -> bool:
	var first: Dictionary = loaded_profiles[0]
	var second: Dictionary = loaded_profiles[1]
	var first_mesh_max := float(first.translated_mesh_aabb.max[0])
	var second_mesh_min := float(second.translated_mesh_aabb.min[0])
	var first_proxy_max := float(first.translated_proxy_aabb.max[0])
	var second_proxy_min := float(second.translated_proxy_aabb.min[0])
	if first_mesh_max >= second_mesh_min or first_proxy_max >= second_proxy_min:
		_failure = "fixed host-only translations do not separate the two avatars"
		return false
	return true


func _build_report(options: Dictionary, validated: Dictionary, loaded_profiles: Array[Dictionary]) -> Dictionary:
	var candidate_hashes := {}
	var profiles: Array[Dictionary] = []
	for profile in loaded_profiles:
		candidate_hashes[profile.profile_id] = profile.candidate_profile_sha256
		profiles.append({
			"profile_id": profile.profile_id,
			"candidate_profile_sha256": profile.candidate_profile_sha256,
			"metrics": profile.metrics,
			"mesh_aabb": profile.mesh_aabb,
			"proxy_aabb": profile.proxy_aabb,
			"profile_translation": profile.profile_translation,
			"counts": profile.counts,
			"proxy_segments": profile.proxy_segments,
			"node_counts": profile.node_counts,
			"translated_mesh_aabb": profile.translated_mesh_aabb,
			"translated_proxy_aabb": profile.translated_proxy_aabb,
		})
	return {
		"schema": "creature-kernel.disposable-godot-host-load-smoke.v1",
		"status": "success",
		"boundary": "host_only_smoke",
		"host_only_smoke": {
			"boundary": "host_only_smoke",
			"scope": "load two validated neutral structural profiles and instantiate temporary mesh/collision nodes",
			"physics_stepping": false,
			"visual_output": false,
			"claims": [],
		},
		"godot_version": validated.godot_version,
		"godot_engine_version_string": Engine.get_version_info().get("string", ""),
		"profile_ids": options.profile_ids,
		"candidate_profile_sha256": candidate_hashes,
		"validated_gallery": {
			"projection_contract": validated.projection_contract,
			"manifest_sha256": validated.manifest_sha256,
			"manifest_bytes": validated.manifest_bytes,
			"pose_id": validated.pose_id,
			"pose_sha256": validated.pose_sha256,
			"boundary": validated.boundary,
		},
		"artifact_hash_identities": {
			loaded_profiles[0].profile_id: _profile_payload(validated, loaded_profiles[0].profile_id).artifacts,
			loaded_profiles[1].profile_id: _profile_payload(validated, loaded_profiles[1].profile_id).artifacts,
		},
		"coordinate_rule": {
			"kind": "disposable_host_local_identity",
			"mapping": "CK XYZ -> Godot XYZ: x->x, y->y, z->z",
			"scope": "host_only_smoke",
		},
		"profiles": profiles,
	}


func _write_report(path: String, report: Dictionary) -> bool:
	if not _failure.is_empty():
		return false
	var file := FileAccess.open(path, FileAccess.WRITE)
	if file == null:
		_failure = "report cannot be opened for writing: %s" % path
		return false
	file.store_string(JSON.stringify(report) + "\n")
	file.flush()
	var error := file.get_error()
	file.close()
	if error != OK:
		_failure = "report cannot be written: %s" % path
		return false
	return true


func _profile_failure(root: Node3D, message: String) -> Dictionary:
	if is_instance_valid(root):
		root.free()
	_failure = message
	return {}


func _release_profiles(profiles: Array[Dictionary]) -> void:
	for profile in profiles:
		var root = profile.get("root")
		if root is Node3D and is_instance_valid(root):
			root.free()
	profiles.clear()


func _fail(message: String) -> int:
	_failure = message
	return _fail_exit()


func _fail_exit() -> int:
	push_error("structural gallery host-load smoke failed: %s" % _failure)
	return 1
