extends SceneTree

const MAX_ARTIFACT_BYTES := 32 * 1024 * 1024
const MAX_VERTICES := 100000
const MAX_FACES := 200000
const BONE_COUNT := 18
const MAX_WEIGHT_ROW := 4
const TOLERANCE := 2.0e-5
const WEIGHT_TOLERANCE := 1.0e-6
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
	var exit_code := _run_crosscheck()
	quit(exit_code)


func _run_crosscheck() -> int:
	var options = _parse_arguments()
	if options.is_empty():
		return _fail_exit()
	var validated = JSON.parse_string(options.validated_json)
	if typeof(validated) != TYPE_DICTIONARY:
		return _fail("validated projection payload is not an object")
	if not _validate_options_against_projection(options, validated):
		return _fail_exit()
	if get_root().get_child_count() != 0:
		return _fail("the disposable scene root was not empty before instantiation")

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

	if get_root().get_child_count() != 2:
		_release_profiles(loaded_profiles)
		return _fail("exactly two profile roots were not instantiated")
	if not _check_separation(loaded_profiles):
		_release_profiles(loaded_profiles)
		return _fail_exit()

	var report := _build_report(options, validated, loaded_profiles)
	_release_profiles(loaded_profiles)
	if get_root().get_child_count() != 0:
		return _fail("temporary profile roots were not released")
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
		var profile := _profile_payload(validated, profile_id)
		if profile.is_empty() or typeof(profile.get("artifacts", null)) != TYPE_ARRAY or profile.artifacts.size() != ARTIFACT_NAMES.size():
			_failure = "validated projection does not contain six artifacts for profile %s" % profile_id
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
		var expected_bytes := int(artifact.get("bytes", -1))
		if bytes.is_empty() and expected_bytes != 0:
			return {}
		if bytes.size() != expected_bytes:
			_failure = "%s %s byte count disagrees with validated view" % [profile_id, relative_path]
			return {}
		if _sha256(bytes) != String(artifact.get("sha256", "")):
			_failure = "%s %s hash disagrees with validated view" % [profile_id, relative_path]
			return {}
		artifact_bytes[relative_path] = bytes

	var neutral_path := profile_id + "/neutral.ply"
	var posed_path := profile_id + "/posed.ply"
	var neutral = _parse_ply(artifact_bytes.get(neutral_path, PackedByteArray()), "%s neutral.ply" % profile_id)
	var posed = _parse_ply(artifact_bytes.get(posed_path, PackedByteArray()), "%s posed.ply" % profile_id)
	var skeleton = _parse_json(artifact_bytes.get(profile_id + "/skeleton.json", PackedByteArray()), "%s skeleton.json" % profile_id)
	var weights = _parse_json(artifact_bytes.get(profile_id + "/weights.json", PackedByteArray()), "%s weights.json" % profile_id)
	var neutral_proxies = _parse_json(artifact_bytes.get(profile_id + "/proxies-neutral.json", PackedByteArray()), "%s proxies-neutral.json" % profile_id)
	var posed_proxies = _parse_json(artifact_bytes.get(profile_id + "/proxies-posed.json", PackedByteArray()), "%s proxies-posed.json" % profile_id)
	var metrics_bytes = _read_bytes(gallery_path.path_join(profile_id + "/metrics.json"), "%s metrics.json" % profile_id)
	var metrics = _parse_json(metrics_bytes, "%s metrics.json" % profile_id)
	if neutral.is_empty() or posed.is_empty() or skeleton.is_empty() or weights.is_empty() or neutral_proxies.is_empty() or posed_proxies.is_empty() or metrics.is_empty():
		return {}
	if metrics != profile_payload.get("metrics", {}):
		_failure = "%s loaded metrics disagree with the validator-backed metrics projection" % profile_id
		return {}
	var structural = _validate_structural_records(profile_id, neutral, posed, metrics, skeleton, weights, neutral_proxies, posed_proxies)
	if structural.is_empty():
		return {}

	var mesh := ArrayMesh.new()
	var arrays: Array = []
	arrays.resize(Mesh.ARRAY_MAX)
	arrays[Mesh.ARRAY_VERTEX] = posed.vertices
	arrays[Mesh.ARRAY_NORMAL] = posed.normals
	arrays[Mesh.ARRAY_INDEX] = posed.indices
	mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arrays)
	if mesh.get_surface_count() != 1:
		_failure = "%s posed mesh did not create exactly one surface" % profile_id
		return {}

	var root := Node3D.new()
	root.name = "Profile_%s" % profile_id
	root.position = translation
	get_root().add_child(root)
	var mesh_instance := MeshInstance3D.new()
	mesh_instance.name = "PosedMesh"
	mesh_instance.mesh = mesh
	root.add_child(mesh_instance)
	var body := StaticBody3D.new()
	body.name = "PosedCollisionProxies"
	root.add_child(body)

	var proxy_aabb := AABB()
	var has_proxy_bounds := false
	for proxy in posed_proxies.proxies:
		var start_value = _vector3(proxy.a, "%s posed proxy a" % profile_id)
		var end_value = _vector3(proxy.b, "%s posed proxy b" % profile_id)
		if start_value == null or end_value == null:
			return _profile_failure(root, "%s posed proxy endpoint is invalid" % profile_id)
		var start: Vector3 = start_value
		var end: Vector3 = end_value
		var radius := float(proxy.radius)
		var segment := end - start
		var segment_length := segment.length()
		if not is_finite(segment_length) or segment_length <= 1.0e-12 or not is_finite(radius) or radius <= 0.0:
			return _profile_failure(root, "%s contains an invalid posed capsule segment" % profile_id)
		var direction := segment / segment_length
		var basis := Basis(Quaternion(Vector3.UP, direction))
		var shape := CapsuleShape3D.new()
		shape.radius = radius
		shape.height = segment_length + 2.0 * radius
		var collision := CollisionShape3D.new()
		collision.name = "PosedCapsule_%s" % String(proxy.bone_id)
		collision.shape = shape
		collision.transform = Transform3D(basis, (start + end) * 0.5)
		body.add_child(collision)
		if abs(collision.transform.basis.y.normalized().dot(direction) - 1.0) > TOLERANCE:
			return _profile_failure(root, "%s posed capsule positive-Y alignment is invalid" % profile_id)
		if abs(shape.height - (segment_length + 2.0 * radius)) > TOLERANCE:
			return _profile_failure(root, "%s posed capsule height rule is invalid" % profile_id)
		var proxy_min := Vector3(min(start.x, end.x) - radius, min(start.y, end.y) - radius, min(start.z, end.z) - radius)
		var proxy_max := Vector3(max(start.x, end.x) + radius, max(start.y, end.y) + radius, max(start.z, end.z) + radius)
		var proxy_box := AABB(proxy_min, proxy_max - proxy_min)
		if not has_proxy_bounds:
			proxy_aabb = proxy_box
			has_proxy_bounds = true
		else:
			proxy_aabb = proxy_aabb.merge(proxy_box)

	if root.get_child_count() != 2 or body.get_child_count() != BONE_COUNT:
		return _profile_failure(root, "%s does not have one posed mesh and 18 collision children" % profile_id)
	if not (mesh_instance.mesh is ArrayMesh):
		return _profile_failure(root, "%s mesh instance does not consume an ArrayMesh" % profile_id)
	for child in body.get_children():
		if not (child is CollisionShape3D) or not (child.shape is CapsuleShape3D):
			return _profile_failure(root, "%s collision child is not a CapsuleShape3D" % profile_id)
	if _count_skeleton_nodes(root) != 0:
		return _profile_failure(root, "%s unexpectedly instantiated Skeleton3D nodes" % profile_id)

	var local_aabb: AABB = mesh.get_aabb()
	if not _aabb_matches(local_aabb, posed.aabb):
		return _profile_failure(root, "%s posed ArrayMesh AABB differs from posed PLY" % profile_id)
	return {
		"profile_id": profile_id,
		"candidate_profile_sha256": String(profile_payload.get("candidate_profile_sha256", "")),
		"root": root,
		"metrics": metrics,
		"posed_mesh_aabb": _aabb_json(local_aabb),
		"posed_proxy_aabb": _aabb_json(proxy_aabb),
		"profile_translation": _vector_json(translation),
		"counts": {
			"neutral_vertex_count": int(neutral.vertices.size()),
			"posed_vertex_count": int(posed.vertices.size()),
			"face_count": int(posed.indices.size() / 3),
			"bone_count": int(BONE_COUNT),
			"proxy_count": int(BONE_COUNT),
			"weight_vertex_count": int(weights.vertex_count),
			"influence_count": int(_influence_count(weights.influences)),
		},
		"node_counts": {
			"profile_root": 1,
			"mesh_instance_3d": 1,
			"static_body_3d": 1,
			"collision_shape_3d": int(BONE_COUNT),
			"skeleton_3d": 0,
			"total_profile_nodes": int(1 + 1 + 1 + BONE_COUNT),
		},
		"crosscheck": structural.crosscheck,
	}


func _validate_structural_records(profile_id: String, neutral: Dictionary, posed: Dictionary, metrics: Dictionary, skeleton: Dictionary, weights: Dictionary, neutral_proxies: Dictionary, posed_proxies: Dictionary) -> Dictionary:
	if metrics.get("profile_id", "") != profile_id or metrics.get("format", "") != "creature-kernel.disposable-structural-embodiment-gallery.v1":
		_failure = "%s metrics lineage is invalid" % profile_id
		return {}
	if int(metrics.get("neutral_vertex_count", -1)) != neutral.vertices.size() or int(metrics.get("posed_vertex_count", -1)) != posed.vertices.size():
		_failure = "%s metrics vertex counts are invalid" % profile_id
		return {}
	if neutral.vertices.size() != posed.vertices.size() or neutral.indices.size() != posed.indices.size() or neutral.indices != posed.indices:
		_failure = "%s neutral and posed mesh counts or face indices differ" % profile_id
		return {}
	if int(metrics.get("face_count", -1)) != posed.indices.size() / 3:
		_failure = "%s metrics face count is invalid" % profile_id
		return {}
	if not _bounds_match(metrics.get("neutral_bounds", {}), neutral.aabb) or not _bounds_match(metrics.get("posed_bounds", {}), posed.aabb):
		_failure = "%s mesh bounds do not match metrics" % profile_id
		return {}
	var changed := false
	for vertex_index in range(neutral.vertices.size()):
		if neutral.vertices[vertex_index] != posed.vertices[vertex_index] or neutral.normals[vertex_index] != posed.normals[vertex_index]:
			changed = true
			break
	if not changed:
		_failure = "%s has no changed vertex or normal between neutral and posed PLY" % profile_id
		return {}

	if typeof(skeleton) != TYPE_DICTIONARY or skeleton.get("profile_id", "") != profile_id or skeleton.get("format", "") != "creature-kernel.disposable-structural-embodiment-gallery.v1":
		_failure = "%s skeleton lineage is invalid" % profile_id
		return {}
	var neutral_state = skeleton.get("neutral", {})
	var posed_state = skeleton.get("posed", {})
	if typeof(neutral_state) != TYPE_DICTIONARY or typeof(posed_state) != TYPE_DICTIONARY:
		_failure = "%s skeleton states are invalid" % profile_id
		return {}
	var neutral_bones = neutral_state.get("bones", [])
	var posed_bones = posed_state.get("bones", [])
	if typeof(neutral_bones) != TYPE_ARRAY or typeof(posed_bones) != TYPE_ARRAY or neutral_bones.size() != BONE_COUNT or posed_bones.size() != BONE_COUNT:
		_failure = "%s skeleton states must contain exactly 18 bones" % profile_id
		return {}
	if int(metrics.get("bone_count", -1)) != BONE_COUNT:
		_failure = "%s metrics bone count is not 18" % profile_id
		return {}
	var bone_ids := {}
	for bone_index in range(BONE_COUNT):
		var neutral_bone = neutral_bones[bone_index]
		var posed_bone = posed_bones[bone_index]
		if typeof(neutral_bone) != TYPE_DICTIONARY or typeof(posed_bone) != TYPE_DICTIONARY:
			_failure = "%s skeleton bone record is invalid" % profile_id
			return {}
		var bone_id: String = String(neutral_bone.get("id", ""))
		if bone_id == "" or bone_ids.has(bone_id) or String(posed_bone.get("id", "")) != bone_id:
			_failure = "%s skeleton bone IDs differ or are duplicated" % profile_id
			return {}
		if neutral_bone.get("parent", null) != posed_bone.get("parent", null):
			_failure = "%s neutral and posed skeleton parents differ" % profile_id
			return {}
		var neutral_length := float(neutral_bone.get("length", -1.0))
		var posed_length := float(posed_bone.get("length", -1.0))
		if not is_finite(neutral_length) or not is_finite(posed_length) or abs(neutral_length - posed_length) > TOLERANCE or neutral_length <= 0.0:
			_failure = "%s neutral and posed skeleton lengths differ or are invalid" % profile_id
			return {}
		bone_ids[bone_id] = true
	for neutral_bone in neutral_bones:
		var parent = neutral_bone.get("parent", null)
		if parent != null and not bone_ids.has(String(parent)):
			_failure = "%s skeleton parent is unknown" % profile_id
			return {}

	var skin = posed_state.get("skin", {})
	if typeof(skin) != TYPE_DICTIONARY or skin.size() != BONE_COUNT:
		_failure = "%s posed skeleton does not publish 18 skin matrices" % profile_id
		return {}
	var skin_matrices := {}
	for bone_id in bone_ids:
		if not skin.has(bone_id):
			_failure = "%s posed skeleton skin matrix is missing for %s" % [profile_id, bone_id]
			return {}
		var matrix = _matrix(skin[bone_id], "%s posed skin %s" % [profile_id, bone_id])
		if matrix.is_empty():
			return {}
		skin_matrices[bone_id] = matrix

	if typeof(weights) != TYPE_DICTIONARY or weights.get("format", "") != "creature-kernel.disposable-structural-embodiment-gallery.v1" or weights.get("profile_id", "") != profile_id or int(weights.get("vertex_count", -1)) != neutral.vertices.size():
		_failure = "%s weights lineage is invalid" % profile_id
		return {}
	var rows = weights.get("influences", [])
	if typeof(rows) != TYPE_ARRAY or rows.size() != neutral.vertices.size():
		_failure = "%s weights do not cover every vertex" % profile_id
		return {}
	for row_index in range(rows.size()):
		var row = rows[row_index]
		if typeof(row) != TYPE_ARRAY or row.size() < 1 or row.size() > MAX_WEIGHT_ROW:
			_failure = "%s weight row %d does not contain one to four influences" % [profile_id, row_index]
			return {}
		var total := 0.0
		for influence in row:
			if typeof(influence) != TYPE_DICTIONARY:
				_failure = "%s weight row %d has an invalid influence" % [profile_id, row_index]
				return {}
			var influence_bone := String(influence.get("bone_id", ""))
			var weight_value = influence.get("weight", -1.0)
			var weight_type := typeof(weight_value)
			if weight_type != TYPE_INT and weight_type != TYPE_FLOAT:
				_failure = "%s weight row %d has an unknown bone or invalid weight" % [profile_id, row_index]
				return {}
			var weight := float(weight_value)
			if not bone_ids.has(influence_bone) or not is_finite(weight) or weight < 0.0:
				_failure = "%s weight row %d has an unknown bone or invalid weight" % [profile_id, row_index]
				return {}
			total += weight
		if abs(total - 1.0) > WEIGHT_TOLERANCE:
			_failure = "%s weight row %d is not normalized" % [profile_id, row_index]
			return {}

	var neutral_proxy_list = neutral_proxies.get("proxies", [])
	var posed_proxy_list = posed_proxies.get("proxies", [])
	if typeof(neutral_proxies) != TYPE_DICTIONARY or typeof(posed_proxies) != TYPE_DICTIONARY or neutral_proxies.get("format", "") != "creature-kernel.disposable-structural-embodiment-gallery.v1" or posed_proxies.get("format", "") != "creature-kernel.disposable-structural-embodiment-gallery.v1" or neutral_proxies.get("profile_id", "") != profile_id or posed_proxies.get("profile_id", "") != profile_id or neutral_proxies.get("state", "") != "neutral" or posed_proxies.get("state", "") != "posed" or neutral_proxies.get("radius_transform", "") != "unchanged" or posed_proxies.get("radius_transform", "") != "unchanged":
		_failure = "%s proxy lineage is invalid" % profile_id
		return {}
	if typeof(neutral_proxy_list) != TYPE_ARRAY or typeof(posed_proxy_list) != TYPE_ARRAY or neutral_proxy_list.size() != BONE_COUNT or posed_proxy_list.size() != BONE_COUNT or int(metrics.get("proxy_count", -1)) != BONE_COUNT:
		_failure = "%s proxy count is not 18" % profile_id
		return {}
	var neutral_by_bone := {}
	var posed_by_bone := {}
	for proxy_index in range(BONE_COUNT):
		var neutral_proxy = neutral_proxy_list[proxy_index]
		var posed_proxy = posed_proxy_list[proxy_index]
		if typeof(neutral_proxy) != TYPE_DICTIONARY or typeof(posed_proxy) != TYPE_DICTIONARY:
			_failure = "%s proxy record is invalid" % profile_id
			return {}
		var neutral_bone_id := String(neutral_proxy.get("bone_id", ""))
		var posed_bone_id := String(posed_proxy.get("bone_id", ""))
		if neutral_bone_id == "" or neutral_bone_id != posed_bone_id or not bone_ids.has(neutral_bone_id) or neutral_by_bone.has(neutral_bone_id):
			_failure = "%s neutral and posed proxy bone coverage differs" % profile_id
			return {}
		if neutral_proxy.get("kind", "") != "capsule" or posed_proxy.get("kind", "") != "capsule":
			_failure = "%s proxy kind is not capsule" % profile_id
			return {}
		var neutral_radius := float(neutral_proxy.get("radius", -1.0))
		var posed_radius := float(posed_proxy.get("radius", -1.0))
		if not is_finite(neutral_radius) or neutral_radius <= 0.0 or not is_finite(posed_radius) or abs(neutral_radius - posed_radius) > 1.0e-12:
			_failure = "%s proxy radius changed or is invalid" % profile_id
			return {}
		for field_name in PROXY_LINEAGE_FIELDS:
			if not neutral_proxy.has(field_name) or not posed_proxy.has(field_name) or neutral_proxy[field_name] != posed_proxy[field_name]:
				_failure = "%s proxy lineage field differs: %s" % [profile_id, field_name]
				return {}
		if _vector3(neutral_proxy.get("a", []), "%s neutral proxy a" % profile_id) == null or _vector3(neutral_proxy.get("b", []), "%s neutral proxy b" % profile_id) == null or _vector3(posed_proxy.get("a", []), "%s posed proxy a" % profile_id) == null or _vector3(posed_proxy.get("b", []), "%s posed proxy b" % profile_id) == null:
			return {}
		neutral_by_bone[neutral_bone_id] = neutral_proxy
		posed_by_bone[posed_bone_id] = posed_proxy
	for bone_id in bone_ids:
		if not neutral_by_bone.has(bone_id) or not posed_by_bone.has(bone_id):
			_failure = "%s proxies do not cover every bone" % profile_id
			return {}

	var recomputed = _recompute_pose(profile_id, neutral, posed, rows, skin_matrices, neutral_by_bone, posed_by_bone)
	if recomputed.is_empty():
		return {}
	return {
		"skin_matrices": skin_matrices,
		"crosscheck": recomputed,
	}


func _recompute_pose(profile_id: String, neutral: Dictionary, posed: Dictionary, rows: Array, skin_matrices: Dictionary, neutral_by_bone: Dictionary, posed_by_bone: Dictionary) -> Dictionary:
	var neutral_vertices: PackedVector3Array = neutral.vertices
	var neutral_normals: PackedVector3Array = neutral.normals
	var posed_vertices: PackedVector3Array = posed.vertices
	var posed_normals: PackedVector3Array = posed.normals
	for vertex_index in range(neutral_vertices.size()):
		var expected_point := Vector3.ZERO
		var expected_normal := Vector3.ZERO
		for influence in rows[vertex_index]:
			var bone_id := String(influence.bone_id)
			var weight := float(influence.weight)
			var point_value = _matrix_point(skin_matrices[bone_id], neutral_vertices[vertex_index], "%s vertex %d" % [profile_id, vertex_index])
			var normal_value = _matrix_direction(skin_matrices[bone_id], neutral_normals[vertex_index], "%s normal %d" % [profile_id, vertex_index])
			if point_value == null or normal_value == null:
				return {}
			expected_point += (point_value as Vector3) * weight
			expected_normal += (normal_value as Vector3) * weight
		if expected_point.distance_to(posed_vertices[vertex_index]) > TOLERANCE:
			_failure = "%s posed vertex %d differs from independent weighted skin recomputation" % [profile_id, vertex_index]
			return {}
		if expected_normal.length() <= 1.0e-12 or expected_normal.normalized().distance_to(posed_normals[vertex_index]) > TOLERANCE:
			_failure = "%s posed normal %d differs from independent weighted skin recomputation" % [profile_id, vertex_index]
			return {}

	for bone_id in neutral_by_bone:
		var neutral_proxy = neutral_by_bone[bone_id]
		var posed_proxy = posed_by_bone[bone_id]
		for endpoint in ["a", "b"]:
			var neutral_endpoint = _vector3(neutral_proxy[endpoint], "%s neutral proxy %s" % [profile_id, endpoint])
			var posed_endpoint = _vector3(posed_proxy[endpoint], "%s posed proxy %s" % [profile_id, endpoint])
			if neutral_endpoint == null or posed_endpoint == null:
				return {}
			var expected_endpoint = _matrix_point(skin_matrices[bone_id], neutral_endpoint as Vector3, "%s proxy %s" % [profile_id, endpoint])
			if expected_endpoint == null or (expected_endpoint as Vector3).distance_to(posed_endpoint as Vector3) > TOLERANCE:
				_failure = "%s posed proxy %s for %s differs from its published skin matrix" % [profile_id, endpoint, bone_id]
				return {}

	return {
		"tolerance": TOLERANCE,
		"posed_vertices_recomputed": int(posed_vertices.size()),
		"posed_normals_recomputed": int(posed_normals.size()),
		"posed_proxy_endpoints_recomputed": int(BONE_COUNT * 2),
		"neutral_and_posed_faces_identical": true,
		"at_least_one_vertex_or_normal_changed": true,
		"bone_ids_parents_lengths_identical": true,
		"weights_validated": true,
		"posed_bounds_match_metrics": true,
		"posed_proxy_separation_checked": true,
		"skeleton_3d_or_skin_binding": false,
	}


func _matrix(value, where: String) -> Array:
	if typeof(value) != TYPE_ARRAY or value.size() != 16:
		_failure = "%s is not a 4x4 matrix" % where
		return []
	var result: Array = []
	for item in value:
		var item_type := typeof(item)
		if item_type != TYPE_INT and item_type != TYPE_FLOAT:
			_failure = "%s contains a non-numeric matrix value" % where
			return []
		var numeric := float(item)
		if not is_finite(numeric):
			_failure = "%s contains a non-finite matrix value" % where
			return []
		result.append(numeric)
	if abs(result[12]) > TOLERANCE or abs(result[13]) > TOLERANCE or abs(result[14]) > TOLERANCE or abs(result[15] - 1.0) > TOLERANCE:
		_failure = "%s is not an affine column-vector matrix" % where
		return []
	return result


func _matrix_vector(matrix: Array, vector: Vector4) -> Vector4:
	return Vector4(
		matrix[0] * vector.x + matrix[1] * vector.y + matrix[2] * vector.z + matrix[3] * vector.w,
		matrix[4] * vector.x + matrix[5] * vector.y + matrix[6] * vector.z + matrix[7] * vector.w,
		matrix[8] * vector.x + matrix[9] * vector.y + matrix[10] * vector.z + matrix[11] * vector.w,
		matrix[12] * vector.x + matrix[13] * vector.y + matrix[14] * vector.z + matrix[15] * vector.w
	)


func _matrix_point(matrix: Array, point: Vector3, where: String) -> Variant:
	var result := _matrix_vector(matrix, Vector4(point.x, point.y, point.z, 1.0))
	if not is_finite(result.x) or not is_finite(result.y) or not is_finite(result.z) or abs(result.w - 1.0) > TOLERANCE:
		_failure = "%s matrix point result is invalid" % where
		return null
	return Vector3(result.x, result.y, result.z)


func _matrix_direction(matrix: Array, direction: Vector3, where: String) -> Variant:
	var result := _matrix_vector(matrix, Vector4(direction.x, direction.y, direction.z, 0.0))
	if not is_finite(result.x) or not is_finite(result.y) or not is_finite(result.z) or abs(result.w) > TOLERANCE:
		_failure = "%s matrix direction result is invalid" % where
		return null
	return Vector3(result.x, result.y, result.z)


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
	var value := _canonical_integer(line.substr(prefix.length()), where)
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
	return (minimum as Vector3).distance_to(aabb.position) <= TOLERANCE and (maximum as Vector3).distance_to(aabb.end) <= TOLERANCE


func _aabb_matches(left: AABB, right: AABB) -> bool:
	return left.position.distance_to(right.position) <= TOLERANCE and left.end.distance_to(right.end) <= TOLERANCE


func _aabb_json(aabb: AABB) -> Dictionary:
	return {"min": _vector_json(aabb.position), "max": _vector_json(aabb.end)}


func _vector_json(value: Vector3) -> Array[float]:
	return [value.x, value.y, value.z]


func _influence_count(rows) -> int:
	var total := 0
	for row in rows:
		total += row.size()
	return total


func _count_skeleton_nodes(node: Node) -> int:
	var total := 0
	for child in node.get_children():
		if child is Skeleton3D:
			total += 1
		total += _count_skeleton_nodes(child)
	return total


func _check_separation(loaded_profiles: Array[Dictionary]) -> bool:
	var first: Dictionary = loaded_profiles[0]
	var second: Dictionary = loaded_profiles[1]
	var first_max := float(first.posed_mesh_aabb.max[0]) + TRANSLATIONS[0].x
	var second_min := float(second.posed_mesh_aabb.min[0]) + TRANSLATIONS[1].x
	var first_proxy_max := float(first.posed_proxy_aabb.max[0]) + TRANSLATIONS[0].x
	var second_proxy_min := float(second.posed_proxy_aabb.min[0]) + TRANSLATIONS[1].x
	if first_max >= second_min or first_proxy_max >= second_proxy_min:
		_failure = "fixed host-only translations do not separate the two posed avatars"
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
			"posed_mesh_aabb": profile.posed_mesh_aabb,
			"posed_proxy_aabb": profile.posed_proxy_aabb,
			"profile_translation": profile.profile_translation,
			"counts": profile.counts,
			"node_counts": profile.node_counts,
			"crosscheck": profile.crosscheck,
		})
	return {
		"schema": "creature-kernel.disposable-godot-posed-structural-crosscheck.v1",
		"status": "success",
		"boundary": "host_local_posed_structural_crosscheck",
		"claims": ["host-local posed structural consumption"],
		"scope_flags": {
			"physics_stepping": false,
			"animation": false,
			"semantic_pose_injection": false,
			"contact": false,
			"deformation": false,
			"render_output": false,
			"adapter": false,
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
			"scope": "host_local_posed_structural_crosscheck",
			"profile_translations": [[-8.0, 0.0, 0.0], [8.0, 0.0, 0.0]],
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
	push_error("posed structural cross-check failed: %s" % _failure)
	return 1
