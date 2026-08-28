extends SceneTree

const MAX_ARTIFACT_BYTES := 32 * 1024 * 1024
const MAX_VERTICES := 100000
const MAX_FACES := 200000
const BONE_COUNT := 18
const PROXY_COUNT := 18
const MAX_WEIGHT_ROW := 4
const TOLERANCE := 2.0e-5
const NORMAL_TOLERANCE := 3.0e-4
const POSE_QUATERNION_TOLERANCE := 1.0e-7
const WEIGHT_TOLERANCE := 1.0e-6
const TRANSLATIONS := [Vector3(-8.0, 0.0, 0.0), Vector3(8.0, 0.0, 0.0)]
const EXPECTED_GODOT_VERSION := "4.7.2.stable.official.ed1daf0bf"
const GALLERY_FORMAT := "creature-kernel.disposable-structural-embodiment-gallery.v1"
const POSE_FORMAT := "creature-kernel.disposable-structural-embodiment-shared-pose.v1"
const POSE_FILE := "structural_embodiment_shared_pose.json"
const REPORT_SCHEMA := "creature-kernel.disposable-godot-skeletal-pose-smoke.v1"
const REPORT_BOUNDARY := "host_local_skeleton3d_skin_pose_binding"
const CARRIER_SCHEMA := "creature-kernel.disposable-engine-neutral-avatar-input.v1"
const CARRIER_BOUNDARY := "experiment_input_only_no_runtime_package_or_adapter_contract"
const CARRIER_ROOT_METADATA_KEYS := [
	"ck_experiment_instance_id",
	"ck_profile_id",
	"ck_candidate_profile_sha256",
]
const ARTIFACT_NAMES := [
	"neutral.ply",
	"posed.ply",
	"skeleton.json",
	"weights.json",
	"proxies-neutral.json",
	"proxies-posed.json",
]
const PROXY_LINEAGE_FIELDS := ["owned_part", "partition_rule", "partition_vertex_count", "radius_rule"]
const POSE_RECIPE := [
	{"kind": "synthetic-root", "role": null, "anchors": [], "axis": "identity", "angle": 0.0},
	{"kind": "joint", "role": "spine", "anchors": [], "axis": "identity", "angle": 0.0},
	{"kind": "joint", "role": "neck_base", "anchors": [], "axis": "x", "angle": 2.0},
	{"kind": "joint", "role": "head_base", "anchors": [], "axis": "x", "angle": 2.0},
	{"kind": "joint", "role": "shoulder", "anchors": ["left"], "axis": "z", "angle": 6.0},
	{"kind": "joint", "role": "shoulder", "anchors": ["right"], "axis": "z", "angle": -6.0},
	{"kind": "joint", "role": "elbow", "anchors": ["left"], "axis": "z", "angle": -8.0},
	{"kind": "joint", "role": "elbow", "anchors": ["right"], "axis": "z", "angle": 8.0},
	{"kind": "joint", "role": "wrist", "anchors": ["left"], "axis": "identity", "angle": 0.0},
	{"kind": "joint", "role": "wrist", "anchors": ["right"], "axis": "identity", "angle": 0.0},
	{"kind": "joint", "role": "hip", "anchors": ["left"], "axis": "z", "angle": 5.0},
	{"kind": "joint", "role": "hip", "anchors": ["right"], "axis": "z", "angle": -5.0},
	{"kind": "joint", "role": "knee", "anchors": ["left"], "axis": "z", "angle": -6.0},
	{"kind": "joint", "role": "knee", "anchors": ["right"], "axis": "z", "angle": 6.0},
	{"kind": "joint", "role": "ankle", "anchors": ["left"], "axis": "identity", "angle": 0.0},
	{"kind": "joint", "role": "ankle", "anchors": ["right"], "axis": "identity", "angle": 0.0},
	{"kind": "joint", "role": "base", "anchors": ["tail"], "axis": "x", "angle": 4.0},
	{"kind": "joint", "role": "segment", "anchors": ["tail"], "axis": "x", "angle": 4.0},
]

var _failure := ""


func _init() -> void:
	call_deferred("_run_deferred")


func _run_deferred() -> void:
	var exit_code: int = await _run_smoke()
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
	var pose = _load_shared_pose(options.gallery_path, validated)
	if pose.is_empty():
		return _fail_exit()
	if get_root().get_child_count() != 0:
		return _fail("the disposable scene root was not empty before instantiation")

	var loaded_profiles: Array[Dictionary] = []
	var carrier_avatar_records: Array = options.get("carrier_avatar_records", [])
	for index in range(2):
		var profile_id: String = options.profile_ids[index]
		var profile_payload: Dictionary = _profile_payload(validated, profile_id)
		var carrier_record: Dictionary = {}
		if options.has("carrier_avatar_records"):
			carrier_record = carrier_avatar_records[index]
		var loaded = _load_profile(options.gallery_path, profile_id, profile_payload, TRANSLATIONS[index], pose, index, carrier_record)
		if loaded.is_empty():
			_release_profiles(loaded_profiles)
			return _fail_exit()
		loaded_profiles.append(loaded)

	if get_root().get_child_count() != 2 or not _check_neutral_separation(loaded_profiles):
		_release_profiles(loaded_profiles)
		return _fail_exit()

	var neutral_updates := _watch_skeleton_updates(loaded_profiles, "neutral")
	if neutral_updates.is_empty():
		_release_profiles(loaded_profiles)
		return _fail_exit()
	for profile in loaded_profiles:
		profile.skeleton.reset_bone_poses()
	if not await _wait_for_skeleton_updates(neutral_updates, "neutral"):
		_release_profiles(loaded_profiles)
		return _fail_exit()
	for profile in loaded_profiles:
		if not _capture_neutral(profile):
			_release_profiles(loaded_profiles)
			return _fail_exit()

	var posed_updates := _watch_skeleton_updates(loaded_profiles, "posed")
	if posed_updates.is_empty():
		_release_profiles(loaded_profiles)
		return _fail_exit()
	for profile in loaded_profiles:
		if not _apply_shared_pose(profile, pose):
			_release_profiles(loaded_profiles)
			return _fail_exit()
	if not await _wait_for_skeleton_updates(posed_updates, "posed"):
		_release_profiles(loaded_profiles)
		return _fail_exit()
	for profile in loaded_profiles:
		if not _capture_posed(profile):
			_release_profiles(loaded_profiles)
			return _fail_exit()

	if not _check_posed_separation(loaded_profiles):
		_release_profiles(loaded_profiles)
		return _fail_exit()
	var report := _build_report(options, validated, loaded_profiles)
	_release_profiles(loaded_profiles)
	if report.is_empty():
		if _failure.is_empty():
			_failure = "runtime evidence report is empty"
		return _fail_exit()
	if get_root().get_child_count() != 0:
		return _fail("temporary profile roots were not released")
	if not _write_report(options.report_path, report):
		return _fail_exit()
	return 0


func _watch_skeleton_updates(profiles: Array[Dictionary], where: String) -> Dictionary:
	var observed := {}
	for profile in profiles:
		var profile_id: String = profile.profile_id
		observed[profile_id] = false
		var callback := _record_skeleton_update.bind(observed, profile_id)
		if profile.skeleton.skeleton_updated.connect(callback, CONNECT_ONE_SHOT) != OK:
			_failure = "%s could not watch %s Skeleton3D update" % [profile_id, where]
			return {}
	return observed


func _record_skeleton_update(observed: Dictionary, profile_id: String) -> void:
	observed[profile_id] = true


func _wait_for_skeleton_updates(observed: Dictionary, where: String) -> bool:
	for _attempt in range(4):
		await process_frame
		if observed.values().all(func(value): return value == true):
			return true
	_failure = "%s Skeleton3D update did not reach every profile within four process frames" % where
	return false


func _parse_arguments() -> Dictionary:
	var arguments := OS.get_cmdline_user_args()
	var result := {
		"gallery_path": "",
		"carrier_avatar_records_json": "",
		"carrier_identity_json": "",
		"profile_ids": [],
		"report_path": "",
		"validated_json": "",
	}
	var index := 0
	while index < arguments.size():
		var argument: String = arguments[index]
		if argument == "--gallery" or argument == "--report" or argument == "--validated-json" or argument == "--carrier-identity-json" or argument == "--carrier-avatar-records-json" or argument == "--profile-id":
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
			elif argument == "--carrier-identity-json":
				result.carrier_identity_json = value
			elif argument == "--carrier-avatar-records-json":
				result.carrier_avatar_records_json = value
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
	if validated.get("profile_ids", []) != options.profile_ids:
		_failure = "selected profile IDs disagree with the validated projection"
		return false
	if validated.get("godot_version", "") != EXPECTED_GODOT_VERSION:
		_failure = "validated Godot version is not the pinned launcher version"
		return false
	if typeof(validated.get("profiles", null)) != TYPE_ARRAY or validated.profiles.size() != 2:
		_failure = "validated projection must contain exactly two profile records"
		return false
	for profile_id in options.profile_ids:
		var profile := _profile_payload(validated, profile_id)
		if profile.is_empty() or typeof(profile.get("artifacts", null)) != TYPE_ARRAY or profile.artifacts.size() != ARTIFACT_NAMES.size():
			_failure = "validated projection does not contain six artifacts for profile %s" % profile_id
			return false
	if typeof(validated.get("pose_sha256", null)) != TYPE_STRING or String(validated.pose_sha256).length() != 64:
		_failure = "validated projection pose identity is invalid"
		return false
	if (options.carrier_identity_json == "") != (options.carrier_avatar_records_json == ""):
		_failure = "carrier identity and per-avatar records must be supplied together"
		return false
	if options.carrier_identity_json != "":
		var carrier_identity = JSON.parse_string(options.carrier_identity_json)
		if not _validate_carrier_identity(carrier_identity):
			return false
		options["carrier_identity"] = carrier_identity
		var carrier_avatar_records = JSON.parse_string(options.carrier_avatar_records_json)
		if not _validate_carrier_avatar_records(carrier_avatar_records, options, validated):
			return false
		options["carrier_avatar_records"] = carrier_avatar_records
	return true


func _validate_carrier_identity(value) -> bool:
	var keys := ["sha256", "byte_count_decimal", "schema", "boundary", "experiment_instance_ids"]
	if typeof(value) != TYPE_DICTIONARY or value.size() != keys.size():
		_failure = "validated carrier identity must contain exactly five fields"
		return false
	for key in keys:
		if not value.has(key):
			_failure = "validated carrier identity is missing %s" % key
			return false
	if typeof(value.sha256) != TYPE_STRING or String(value.sha256).length() != 64:
		_failure = "validated carrier SHA-256 identity is invalid"
		return false
	if not _is_canonical_carrier_byte_count(value.byte_count_decimal):
		_failure = "validated carrier byte count is invalid"
		return false
	if typeof(value.schema) != TYPE_STRING or value.schema != CARRIER_SCHEMA:
		_failure = "validated carrier schema is unsupported"
		return false
	if typeof(value.boundary) != TYPE_STRING or value.boundary != CARRIER_BOUNDARY:
		_failure = "validated carrier boundary is unsupported"
		return false
	if typeof(value.experiment_instance_ids) != TYPE_ARRAY or value.experiment_instance_ids.size() != 2:
		_failure = "validated carrier must identify exactly two experiment instances"
		return false
	if typeof(value.experiment_instance_ids[0]) != TYPE_STRING or typeof(value.experiment_instance_ids[1]) != TYPE_STRING or not _is_safe_instance_id(String(value.experiment_instance_ids[0])) or not _is_safe_instance_id(String(value.experiment_instance_ids[1])) or value.experiment_instance_ids[0] == value.experiment_instance_ids[1]:
		_failure = "validated carrier experiment instance identities are invalid"
		return false
	return true


func _is_safe_instance_id(value: String) -> bool:
	if value.is_empty() or value.length() > 64:
		return false
	for index in range(value.length()):
		var code := value.unicode_at(index)
		if index == 0:
			if code < 97 or code > 122:
				return false
		elif not ((code >= 97 and code <= 122) or (code >= 48 and code <= 57) or code == 45):
			return false
	return true


func _validate_carrier_avatar_records(value, options: Dictionary, validated: Dictionary) -> bool:
	if typeof(value) != TYPE_ARRAY or value.size() != 2:
		_failure = "validated carrier must contain exactly two per-avatar records"
		return false
	if not options.has("carrier_identity"):
		_failure = "validated carrier per-avatar records require carrier identity"
		return false
	var identity: Dictionary = options.carrier_identity
	var seen := {}
	for index in range(2):
		var record = value[index]
		if typeof(record) != TYPE_DICTIONARY or record.size() != 3:
			_failure = "validated carrier per-avatar record %d must contain exactly three fields" % index
			return false
		for key in ["instance_id", "profile_id", "candidate_profile_sha256"]:
			if not record.has(key) or typeof(record[key]) != TYPE_STRING:
				_failure = "validated carrier per-avatar record %d is missing %s" % [index, key]
				return false
		var instance_id := String(record.instance_id)
		var profile_id := String(record.profile_id)
		var candidate_hash := String(record.candidate_profile_sha256)
		if not _is_safe_instance_id(instance_id) or seen.has(instance_id):
			_failure = "validated carrier per-avatar instance identities are not unique and safe"
			return false
		seen[instance_id] = true
		if instance_id != String(identity.experiment_instance_ids[index]) or profile_id != String(options.profile_ids[index]):
			_failure = "validated carrier per-avatar records are reordered or swapped"
			return false
		var profile := _profile_payload(validated, profile_id)
		if profile.is_empty() or candidate_hash != String(profile.get("candidate_profile_sha256", "")):
			_failure = "validated carrier per-avatar candidate identity does not match the projection"
			return false
	return true


func _is_canonical_carrier_byte_count(value) -> bool:
	if typeof(value) != TYPE_STRING:
		return false
	var text := String(value)
	if text.is_empty() or text.length() > 7 or text.begins_with("0"):
		return false
	for index in range(text.length()):
		var code := text.unicode_at(index)
		if code < 48 or code > 57:
			return false
	var byte_count := text.to_int()
	return byte_count > 0 and byte_count <= 4194304 and str(byte_count) == text


func _profile_payload(validated: Dictionary, profile_id: String) -> Dictionary:
	for profile in validated.profiles:
		if typeof(profile) == TYPE_DICTIONARY and profile.get("profile_id", "") == profile_id:
			return profile
	return {}


func _load_shared_pose(gallery_path: String, validated: Dictionary) -> Dictionary:
	var path := gallery_path.path_join(POSE_FILE)
	var bytes := _read_bytes(path, "shared pose")
	if bytes.is_empty():
		return {}
	if _sha256(bytes) != String(validated.pose_sha256):
		_failure = "shared pose hash disagrees with the validated gallery identity"
		return {}
	var value := _parse_json(bytes, "shared pose")
	if value.is_empty() or value.get("format", "") != POSE_FORMAT or value.get("version", -1) != 1 or value.get("pose_id", "") != String(validated.pose_id):
		_failure = "shared pose identity is invalid"
		return {}
	if value.get("pose_id", "") != "shared-structural-pose-v1":
		_failure = "shared pose ID is not the frozen structural pose"
		return {}
	var convention = value.get("convention", null)
	if typeof(convention) != TYPE_DICTIONARY or convention.get("vectors", "") != "column" or convention.get("bind_transform", "") != "bone-local-plus-y-with-deterministic-up-fallback" or convention.get("skin_transform", "") != "posed-world-times-inverse-neutral-world" or convention.get("rotation_storage", "") != "xyzw":
		_failure = "shared pose transform convention is unsupported"
		return {}
	if value.get("solver", {}) != {"contact": false, "ik": false}:
		_failure = "shared pose must explicitly disable IK and contact"
		return {}
	var rules = value.get("rules", null)
	if typeof(rules) != TYPE_ARRAY or rules.size() != BONE_COUNT:
		_failure = "shared pose must contain exactly 18 rules"
		return {}
	var normalized: Array[Dictionary] = []
	var selectors := {}
	for index in range(BONE_COUNT):
		var rule = rules[index]
		var expected: Dictionary = POSE_RECIPE[index]
		if typeof(rule) != TYPE_DICTIONARY:
			_failure = "shared pose rule %d is not an object" % index
			return {}
		if rule.get("kind", "") != expected.kind or rule.get("role", null) != expected.role or rule.get("anchors", []) != expected.anchors or rule.get("axis", "") != expected.axis or abs(float(rule.get("angle_degrees", INF)) - float(expected.angle)) > 1.0e-12:
			_failure = "shared pose rule %d does not match the exact recipe" % index
			return {}
		var selector := _selector(String(rule.kind), rule.role, rule.anchors)
		if selectors.has(selector):
			_failure = "shared pose contains duplicate selectors"
			return {}
		selectors[selector] = true
		var quaternion = _quaternion_from_rule(rule)
		if quaternion == null:
			return {}
		normalized.append({
			"selector": selector,
			"rotation": quaternion,
		})
	if selectors.size() != BONE_COUNT:
		_failure = "shared pose does not cover the exact 18-rule inventory"
		return {}
	return {"rules": normalized}


func _selector(kind: String, role, anchors) -> String:
	var role_text := "" if role == null else String(role)
	var anchor_text := ",".join(PackedStringArray(anchors))
	return "%s|%s|%s" % [kind, role_text, anchor_text]


func _quaternion_from_rule(rule: Dictionary) -> Variant:
	var raw = rule.get("rotation_xyzw", null)
	if typeof(raw) != TYPE_ARRAY or raw.size() != 4:
		_failure = "shared pose quaternion is not a four-vector"
		return null
	var values: Array[float] = []
	for item in raw:
		if typeof(item) == TYPE_BOOL or not is_finite(float(item)):
			_failure = "shared pose quaternion contains a non-finite value"
			return null
		values.append(float(item))
	var quaternion := Quaternion(values[0], values[1], values[2], values[3])
	if abs(quaternion.length() - 1.0) > 2.0e-14:
		_failure = "shared pose quaternion is not normalized"
		return null
	var axis: String = String(rule.axis)
	var angle := deg_to_rad(float(rule.angle_degrees))
	var expected := Quaternion.IDENTITY if axis == "identity" else Quaternion(Vector3.RIGHT if axis == "x" else Vector3(0.0, 0.0, 1.0), angle)
	if _quaternion_error(quaternion, expected) > POSE_QUATERNION_TOLERANCE:
		_failure = "shared pose quaternion is not bound to its recipe"
		return null
	return quaternion


func _quaternion_error(left: Quaternion, right: Quaternion) -> float:
	return max(abs(left.x - right.x), abs(left.y - right.y), abs(left.z - right.z), abs(left.w - right.w))


func _load_profile(gallery_path: String, profile_id: String, profile_payload: Dictionary, translation: Vector3, pose: Dictionary, avatar_index: int, carrier_record: Dictionary = {}) -> Dictionary:
	var artifact_bytes: Dictionary = {}
	var artifacts = profile_payload.get("artifacts", [])
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
		var bytes := _read_bytes(gallery_path.path_join(relative_path), "%s %s" % [profile_id, relative_path])
		var expected_bytes := int(artifact.get("bytes", -1))
		if bytes.is_empty() and expected_bytes != 0:
			return {}
		if bytes.size() != expected_bytes or _sha256(bytes) != String(artifact.get("sha256", "")):
			_failure = "%s %s does not match the validated artifact identity" % [profile_id, relative_path]
			return {}
		artifact_bytes[relative_path] = bytes

	var neutral = _parse_ply(artifact_bytes.get(profile_id + "/neutral.ply", PackedByteArray()), "%s neutral.ply" % profile_id)
	var posed = _parse_ply(artifact_bytes.get(profile_id + "/posed.ply", PackedByteArray()), "%s posed.ply" % profile_id)
	var skeleton = _parse_json(artifact_bytes.get(profile_id + "/skeleton.json", PackedByteArray()), "%s skeleton.json" % profile_id)
	var weights = _parse_json(artifact_bytes.get(profile_id + "/weights.json", PackedByteArray()), "%s weights.json" % profile_id)
	var neutral_proxies = _parse_json(artifact_bytes.get(profile_id + "/proxies-neutral.json", PackedByteArray()), "%s proxies-neutral.json" % profile_id)
	var posed_proxies = _parse_json(artifact_bytes.get(profile_id + "/proxies-posed.json", PackedByteArray()), "%s proxies-posed.json" % profile_id)
	var metrics := _parse_json(_read_bytes(gallery_path.path_join(profile_id + "/metrics.json"), "%s metrics.json" % profile_id), "%s metrics.json" % profile_id)
	if neutral.is_empty() or posed.is_empty() or skeleton.is_empty() or weights.is_empty() or neutral_proxies.is_empty() or posed_proxies.is_empty() or metrics.is_empty():
		return {}
	if metrics != profile_payload.get("metrics", {}):
		_failure = "%s loaded metrics disagree with the validated projection" % profile_id
		return {}
	var structural := _validate_structural_records(profile_id, neutral, posed, metrics, skeleton, weights, neutral_proxies, posed_proxies)
	if structural.is_empty():
		return {}

	var root := Node3D.new()
	if carrier_record.is_empty():
		root.name = "Profile_%s" % profile_id
	else:
		var instance_id := String(carrier_record.instance_id)
		root.name = _safe_avatar_root_name(avatar_index, instance_id)
		root.set_meta("ck_experiment_instance_id", instance_id)
		root.set_meta("ck_profile_id", String(carrier_record.profile_id))
		root.set_meta("ck_candidate_profile_sha256", String(carrier_record.candidate_profile_sha256))
	root.position = translation
	get_root().add_child(root)
	var skeleton_node := Skeleton3D.new()
	skeleton_node.name = "Skeleton3D"
	skeleton_node.modifier_callback_mode_process = Skeleton3D.MODIFIER_CALLBACK_MODE_PROCESS_MANUAL
	root.add_child(skeleton_node)
	var ordered_bones: Array = structural.ordered_bones
	var bone_indices := {}
	for bone in ordered_bones:
		var bone_id: String = String(bone.id)
		var bone_index := skeleton_node.add_bone(bone_id)
		if bone_index < 0 or bone_index != bone_indices.size():
			return _profile_failure(root, "%s could not add its ordered Skeleton3D bones" % profile_id)
		bone_indices[bone_id] = bone_index
		var parent = bone.get("parent", null)
		if parent != null:
			if not bone_indices.has(String(parent)):
				return _profile_failure(root, "%s Skeleton3D parent order is invalid" % profile_id)
			skeleton_node.set_bone_parent(bone_index, int(bone_indices[String(parent)]))
		var local_bind: Array = structural.local_bind[bone_id]
		skeleton_node.set_bone_rest(bone_index, _transform_from_matrix(local_bind))
		skeleton_node.set_bone_pose(bone_index, Transform3D.IDENTITY)
		skeleton_node.set_bone_meta(bone_index, "ck_bone_id", bone_id)

	var skin := Skin.new()
	var skin_bind_indices := {}
	for bone in ordered_bones:
		var bone_id: String = String(bone.id)
		var bone_index: int = int(bone_indices[bone_id])
		var bind_world: Array = structural.bind_world[bone_id]
		skin.add_bind(bone_index, _transform_from_matrix(bind_world).affine_inverse())
		skin_bind_indices[bone_id] = skin.get_bind_count() - 1
	if skin.get_bind_count() != BONE_COUNT:
		return _profile_failure(root, "%s Skin did not create exactly 18 binds" % profile_id)

	var mesh := ArrayMesh.new()
	var arrays: Array = []
	arrays.resize(Mesh.ARRAY_MAX)
	arrays[Mesh.ARRAY_VERTEX] = neutral.vertices
	arrays[Mesh.ARRAY_NORMAL] = neutral.normals
	arrays[Mesh.ARRAY_INDEX] = neutral.indices
	var bone_slots := PackedInt32Array()
	var weight_slots := PackedFloat32Array()
	for row in weights.influences:
		for influence_index in range(MAX_WEIGHT_ROW):
			if influence_index < row.size():
				var influence = row[influence_index]
				bone_slots.append(int(bone_indices[String(influence.bone_id)]))
				weight_slots.append(float(influence.weight))
			else:
				bone_slots.append(0)
				weight_slots.append(0.0)
	arrays[Mesh.ARRAY_BONES] = bone_slots
	arrays[Mesh.ARRAY_WEIGHTS] = weight_slots
	mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arrays)
	if mesh.get_surface_count() != 1:
		return _profile_failure(root, "%s ArrayMesh did not create exactly one skinned surface" % profile_id)

	var mesh_instance := MeshInstance3D.new()
	mesh_instance.name = "SkinnedMesh"
	mesh_instance.mesh = mesh
	root.add_child(mesh_instance)
	mesh_instance.skin = skin
	mesh_instance.skeleton = mesh_instance.get_path_to(skeleton_node)
	var skin_reference = skeleton_node.register_skin(skin)
	if skin_reference == null or not skin_reference.get_skeleton().is_valid():
		return _profile_failure(root, "%s could not retain a valid SkinReference" % profile_id)
	var body := StaticBody3D.new()
	body.name = "PosedCollisionProxies"
	root.add_child(body)
	return {
		"profile_id": profile_id,
		"candidate_profile_sha256": String(profile_payload.get("candidate_profile_sha256", "")),
		"root": root,
		"skeleton": skeleton_node,
		"skin": skin,
		"skin_reference": skin_reference,
		"mesh": mesh,
		"mesh_instance": mesh_instance,
		"body": body,
		"metrics": metrics,
		"neutral": neutral,
		"posed": posed,
		"weights": weights,
		"neutral_proxies": neutral_proxies,
		"posed_proxies": posed_proxies,
		"bone_indices": bone_indices,
		"skin_bind_indices": skin_bind_indices,
		"ordered_bones": ordered_bones,
		"structural": structural,
		"expected_translation": translation,
		"pose_rules_validated": pose.rules.size() == BONE_COUNT,
	}


func _validate_structural_records(profile_id: String, neutral: Dictionary, posed: Dictionary, metrics: Dictionary, skeleton: Dictionary, weights: Dictionary, neutral_proxies: Dictionary, posed_proxies: Dictionary) -> Dictionary:
	if metrics.get("profile_id", "") != profile_id or metrics.get("format", "") != GALLERY_FORMAT or int(metrics.get("bone_count", -1)) != BONE_COUNT or int(metrics.get("proxy_count", -1)) != PROXY_COUNT:
		_failure = "%s metrics lineage or exact bone/proxy counts are invalid" % profile_id
		return {}
	if int(metrics.get("neutral_vertex_count", -1)) != neutral.vertices.size() or int(metrics.get("posed_vertex_count", -1)) != posed.vertices.size() or neutral.vertices.size() != posed.vertices.size() or neutral.indices != posed.indices or int(metrics.get("face_count", -1)) != posed.indices.size() / 3:
		_failure = "%s mesh counts or shared face indices are invalid" % profile_id
		return {}
	if not _bounds_match(metrics.get("neutral_bounds", {}), neutral.aabb) or not _bounds_match(metrics.get("posed_bounds", {}), posed.aabb):
		_failure = "%s mesh bounds do not match metrics" % profile_id
		return {}
	var changed := false
	for index in range(neutral.vertices.size()):
		if neutral.vertices[index] != posed.vertices[index] or neutral.normals[index] != posed.normals[index]:
			changed = true
			break
	if not changed:
		_failure = "%s has no published neutral-to-posed change" % profile_id
		return {}
	if skeleton.get("format", "") != GALLERY_FORMAT or skeleton.get("profile_id", "") != profile_id:
		_failure = "%s skeleton lineage is invalid" % profile_id
		return {}
	var neutral_state = skeleton.get("neutral", null)
	var posed_state = skeleton.get("posed", null)
	if typeof(neutral_state) != TYPE_DICTIONARY or typeof(posed_state) != TYPE_DICTIONARY:
		_failure = "%s skeleton states are invalid" % profile_id
		return {}
	var neutral_bones = neutral_state.get("bones", null)
	var posed_bones = posed_state.get("bones", null)
	if typeof(neutral_bones) != TYPE_ARRAY or typeof(posed_bones) != TYPE_ARRAY or neutral_bones.size() != BONE_COUNT or posed_bones.size() != BONE_COUNT:
		_failure = "%s skeleton states must contain exactly 18 bones" % profile_id
		return {}
	var bone_ids := {}
	for index in range(BONE_COUNT):
		var neutral_bone = neutral_bones[index]
		var posed_bone = posed_bones[index]
		if typeof(neutral_bone) != TYPE_DICTIONARY or typeof(posed_bone) != TYPE_DICTIONARY:
			_failure = "%s skeleton bone record is invalid" % profile_id
			return {}
		var bone_id := String(neutral_bone.get("id", ""))
		if bone_id == "" or bone_ids.has(bone_id) or String(posed_bone.get("id", "")) != bone_id or neutral_bone.get("parent", null) != posed_bone.get("parent", null):
			_failure = "%s skeleton IDs or parents differ" % profile_id
			return {}
		var neutral_length := float(neutral_bone.get("length", -1.0))
		var posed_length := float(posed_bone.get("length", -1.0))
		if not is_finite(neutral_length) or neutral_length <= 0.0 or not is_finite(posed_length) or abs(neutral_length - posed_length) > TOLERANCE:
			_failure = "%s skeleton bone lengths are invalid" % profile_id
			return {}
		bone_ids[bone_id] = neutral_bone
	for bone_id in bone_ids:
		var parent = bone_ids[bone_id].get("parent", null)
		if parent != null and not bone_ids.has(String(parent)):
			_failure = "%s skeleton has an unknown parent" % profile_id
			return {}
	var bind_world = neutral_state.get("bind_world", null)
	var local_bind = neutral_state.get("bind_parent_local", null)
	var published_skin = posed_state.get("skin", null)
	var published_posed_world = posed_state.get("posed_world", null)
	if typeof(bind_world) != TYPE_DICTIONARY or typeof(local_bind) != TYPE_DICTIONARY or typeof(published_skin) != TYPE_DICTIONARY or typeof(published_posed_world) != TYPE_DICTIONARY or bind_world.size() != BONE_COUNT or local_bind.size() != BONE_COUNT or published_skin.size() != BONE_COUNT or published_posed_world.size() != BONE_COUNT:
		_failure = "%s published bind/pose matrices are incomplete" % profile_id
		return {}
	var bind_world_matrices := {}
	var local_bind_matrices := {}
	var skin_matrices := {}
	var posed_world_matrices := {}
	for bone_id in bone_ids:
		bind_world_matrices[bone_id] = _matrix(bind_world.get(bone_id, []), "%s bind world %s" % [profile_id, bone_id])
		local_bind_matrices[bone_id] = _matrix(local_bind.get(bone_id, []), "%s local bind %s" % [profile_id, bone_id])
		skin_matrices[bone_id] = _matrix(published_skin.get(bone_id, []), "%s skin %s" % [profile_id, bone_id])
		posed_world_matrices[bone_id] = _matrix(published_posed_world.get(bone_id, []), "%s posed world %s" % [profile_id, bone_id])
		if bind_world_matrices[bone_id].is_empty() or local_bind_matrices[bone_id].is_empty() or skin_matrices[bone_id].is_empty() or posed_world_matrices[bone_id].is_empty():
			return {}
	var rows = weights.get("influences", null)
	if weights.get("format", "") != GALLERY_FORMAT or weights.get("profile_id", "") != profile_id or int(weights.get("vertex_count", -1)) != neutral.vertices.size() or typeof(rows) != TYPE_ARRAY or rows.size() != neutral.vertices.size():
		_failure = "%s weights do not cover the neutral mesh" % profile_id
		return {}
	for row_index in range(rows.size()):
		var row = rows[row_index]
		if typeof(row) != TYPE_ARRAY or row.size() < 1 or row.size() > MAX_WEIGHT_ROW:
			_failure = "%s weight row %d does not contain one to four influences" % [profile_id, row_index]
			return {}
		var total := 0.0
		for influence in row:
			if typeof(influence) != TYPE_DICTIONARY or not bone_ids.has(String(influence.get("bone_id", ""))) or typeof(influence.get("weight", null)) == TYPE_BOOL or not is_finite(float(influence.get("weight", -1.0))) or float(influence.weight) < 0.0:
				_failure = "%s weight row %d has an invalid influence" % [profile_id, row_index]
				return {}
			total += float(influence.weight)
		if abs(total - 1.0) > WEIGHT_TOLERANCE:
			_failure = "%s weight row %d is not normalized" % [profile_id, row_index]
			return {}

	var neutral_proxy_list = neutral_proxies.get("proxies", null)
	var posed_proxy_list = posed_proxies.get("proxies", null)
	if neutral_proxies.get("format", "") != GALLERY_FORMAT or posed_proxies.get("format", "") != GALLERY_FORMAT or neutral_proxies.get("profile_id", "") != profile_id or posed_proxies.get("profile_id", "") != profile_id or neutral_proxies.get("state", "") != "neutral" or posed_proxies.get("state", "") != "posed" or typeof(neutral_proxy_list) != TYPE_ARRAY or typeof(posed_proxy_list) != TYPE_ARRAY or neutral_proxy_list.size() != PROXY_COUNT or posed_proxy_list.size() != PROXY_COUNT:
		_failure = "%s proxy lineage or exact count is invalid" % profile_id
		return {}
	var neutral_by_bone := {}
	var posed_by_bone := {}
	for index in range(PROXY_COUNT):
		var neutral_proxy = neutral_proxy_list[index]
		var posed_proxy = posed_proxy_list[index]
		if typeof(neutral_proxy) != TYPE_DICTIONARY or typeof(posed_proxy) != TYPE_DICTIONARY:
			_failure = "%s proxy record is invalid" % profile_id
			return {}
		var bone_id := String(neutral_proxy.get("bone_id", ""))
		if bone_id == "" or bone_id != String(posed_proxy.get("bone_id", "")) or not bone_ids.has(bone_id) or neutral_by_bone.has(bone_id):
			_failure = "%s proxy bone coverage is invalid" % profile_id
			return {}
		if neutral_proxy.get("kind", "") != "capsule" or posed_proxy.get("kind", "") != "capsule" or abs(float(neutral_proxy.get("radius", -1.0)) - float(posed_proxy.get("radius", -1.0))) > 1.0e-12 or float(neutral_proxy.get("radius", -1.0)) <= 0.0:
			_failure = "%s proxy radius or kind is invalid" % profile_id
			return {}
		for field_name in PROXY_LINEAGE_FIELDS:
			if not neutral_proxy.has(field_name) or not posed_proxy.has(field_name) or neutral_proxy[field_name] != posed_proxy[field_name]:
				_failure = "%s proxy lineage differs for %s" % [profile_id, bone_id]
				return {}
		if _vector3(neutral_proxy.get("a", []), "%s neutral proxy a" % profile_id) == null or _vector3(neutral_proxy.get("b", []), "%s neutral proxy b" % profile_id) == null or _vector3(posed_proxy.get("a", []), "%s posed proxy a" % profile_id) == null or _vector3(posed_proxy.get("b", []), "%s posed proxy b" % profile_id) == null:
			return {}
		neutral_by_bone[bone_id] = neutral_proxy
		posed_by_bone[bone_id] = posed_proxy
	if neutral_by_bone.size() != BONE_COUNT or posed_by_bone.size() != BONE_COUNT:
		_failure = "%s proxies do not cover every bone" % profile_id
		return {}
	var ordered_bones := _order_bones(neutral_bones, profile_id)
	if ordered_bones.is_empty():
		return {}
	for vertex_index in range(neutral.vertices.size()):
		var expected_point := Vector3.ZERO
		var expected_normal := Vector3.ZERO
		for influence in rows[vertex_index]:
			var bone_id := String(influence.bone_id)
			var weight := float(influence.weight)
			var point_value = _matrix_point(skin_matrices[bone_id], neutral.vertices[vertex_index], "%s vertex %d" % [profile_id, vertex_index])
			var normal_value = _matrix_direction(skin_matrices[bone_id], neutral.normals[vertex_index], "%s normal %d" % [profile_id, vertex_index])
			if point_value == null or normal_value == null:
				return {}
			expected_point += (point_value as Vector3) * weight
			expected_normal += (normal_value as Vector3) * weight
		if expected_point.distance_to(posed.vertices[vertex_index]) > TOLERANCE or expected_normal.length() <= 1.0e-12 or expected_normal.normalized().distance_to(posed.normals[vertex_index]) > TOLERANCE:
			_failure = "%s published posed mesh disagrees with its published skin matrices" % profile_id
			return {}
	for bone_id in neutral_by_bone:
		for endpoint in ["a", "b"]:
			var neutral_endpoint = _vector3(neutral_by_bone[bone_id][endpoint], "%s neutral proxy %s" % [profile_id, endpoint])
			var posed_endpoint = _vector3(posed_by_bone[bone_id][endpoint], "%s posed proxy %s" % [profile_id, endpoint])
			var expected_endpoint = _matrix_point(skin_matrices[bone_id], neutral_endpoint as Vector3, "%s proxy %s" % [profile_id, endpoint])
			if expected_endpoint == null or (expected_endpoint as Vector3).distance_to(posed_endpoint as Vector3) > TOLERANCE:
				_failure = "%s published posed proxy disagrees with its skin matrix" % profile_id
				return {}
	return {
		"ordered_bones": ordered_bones,
		"bind_world": bind_world_matrices,
		"local_bind": local_bind_matrices,
		"skin": skin_matrices,
		"posed_world": posed_world_matrices,
		"neutral_by_bone": neutral_by_bone,
		"posed_by_bone": posed_by_bone,
	}


func _order_bones(bones: Array, profile_id: String) -> Array:
	var pending: Array = bones.duplicate()
	var ordered: Array = []
	var present := {}
	for bone in bones:
		present[String(bone.get("id", ""))] = true
	while not pending.is_empty():
		var progress := false
		for bone in pending.duplicate():
			var parent = bone.get("parent", null)
			var parent_ready := parent == null
			if parent != null:
				for prior in ordered:
					if String(prior.id) == String(parent):
						parent_ready = true
						break
			if parent_ready:
				ordered.append(bone)
				pending.erase(bone)
				progress = true
		if not progress:
			_failure = "%s skeleton hierarchy is cyclic or cannot be topologically ordered" % profile_id
			return []
	if ordered.size() != present.size():
		_failure = "%s skeleton hierarchy contains duplicate or missing IDs" % profile_id
		return []
	return ordered


func _capture_neutral(profile: Dictionary) -> bool:
	var baked := _bake_mesh(profile.mesh_instance, "%s neutral" % profile.profile_id)
	if baked.is_empty():
		return false
	var comparison := _compare_mesh_arrays(baked.arrays, profile.neutral, "%s neutral" % profile.profile_id)
	if comparison.is_empty():
		return false
	profile["neutral_mesh_aabb"] = _aabb_json(baked.mesh.get_aabb())
	profile["neutral_mesh_compare"] = comparison
	return true


func _apply_shared_pose(profile: Dictionary, pose: Dictionary) -> bool:
	var pose_by_selector := {}
	for rule in pose.rules:
		pose_by_selector[rule.selector] = rule.rotation
	var applied := 0
	for bone in profile.ordered_bones:
		var bone_id: String = String(bone.id)
		var selector = _pose_selector_for_bone(bone, profile.profile_id)
		if selector == null:
			return false
		if not pose_by_selector.has(selector):
			_failure = "%s bone %s is not covered by the shared pose" % [profile.profile_id, bone_id]
			return false
		var bone_index: int = int(profile.bone_indices[bone_id])
		var local_pose: Transform3D = profile.skeleton.get_bone_rest(bone_index) * Transform3D(Basis(pose_by_selector[selector]), Vector3.ZERO)
		profile.skeleton.set_bone_pose(bone_index, local_pose)
		applied += 1
	if applied != BONE_COUNT:
		_failure = "%s did not apply exactly 18 shared pose rules" % profile.profile_id
		return false
	profile["pose_rotations"] = pose_by_selector
	return true


func _pose_selector_for_bone(bone: Dictionary, profile_id: String) -> Variant:
	if String(bone.get("kind", "")) == "synthetic-source-part-root":
		return _selector("synthetic-root", "", [])
	var joint = bone.get("joint", null)
	if typeof(joint) != TYPE_DICTIONARY:
		_failure = "%s bone %s has no pose selector" % [profile_id, String(bone.get("id", ""))]
		return null
	return _selector("joint", joint.get("role", ""), joint.get("anchors", []))


func _capture_posed(profile: Dictionary) -> bool:
	var matrices := {}
	var pose_rotations: Dictionary = profile.get("pose_rotations", {})
	var pose_rule_match_count := 0
	var pose_match_count := 0
	var skin_match_count := 0
	var max_skin_error := 0.0
	var max_pose_error := 0.0
	for bone in profile.ordered_bones:
		var bone_id: String = String(bone.id)
		var bone_index: int = int(profile.bone_indices[bone_id])
		var selector = _pose_selector_for_bone(bone, profile.profile_id)
		if selector == null or not pose_rotations.has(selector):
			return false
		var expected_local_pose: Transform3D = profile.skeleton.get_bone_rest(bone_index) * Transform3D(Basis(pose_rotations[selector]), Vector3.ZERO)
		var local_pose: Transform3D = profile.skeleton.get_bone_pose(bone_index)
		if _transform_error(local_pose, expected_local_pose) <= TOLERANCE:
			pose_rule_match_count += 1
		var global_pose: Transform3D = profile.skeleton.get_bone_global_pose(bone_index)
		var expected_pose: Array = profile.structural.posed_world[bone_id]
		var pose_error := _transform_matrix_error(global_pose, expected_pose)
		max_pose_error = max(max_pose_error, pose_error)
		if pose_error <= TOLERANCE:
			pose_match_count += 1
		var bind_index: int = int(profile.skin_bind_indices[bone_id])
		var bind_pose: Transform3D = profile.skin.get_bind_pose(bind_index)
		var skin_transform: Transform3D = global_pose * bind_pose
		matrices[bone_id] = skin_transform
		var expected_skin: Array = profile.structural.skin[bone_id]
		var skin_error := _transform_matrix_error(skin_transform, expected_skin)
		max_skin_error = max(max_skin_error, skin_error)
		if skin_error <= TOLERANCE:
			skin_match_count += 1
	if pose_rule_match_count != BONE_COUNT:
		_failure = "%s Skeleton3D local poses do not match the applied shared pose rules (matches=%d)" % [profile.profile_id, pose_rule_match_count]
		return false
	if pose_match_count != BONE_COUNT or skin_match_count != BONE_COUNT:
		_failure = "%s Skeleton3D pose or Skin matrices differ from published pose evidence (pose_matches=%d skin_matches=%d max_pose=%s max_skin=%s)" % [profile.profile_id, pose_match_count, skin_match_count, _report_float(max_pose_error), _report_float(max_skin_error)]
		return false
	var baked := _bake_mesh(profile.mesh_instance, "%s posed" % profile.profile_id)
	if baked.is_empty():
		return false
	var comparison := _compare_mesh_arrays(baked.arrays, profile.posed, "%s posed" % profile.profile_id)
	if comparison.is_empty():
		return false
	var proxy_result := _build_host_proxies(profile, matrices)
	if proxy_result.is_empty():
		return false
	profile["posed_mesh_aabb"] = _aabb_json(baked.mesh.get_aabb())
	profile["posed_proxy_aabb"] = _aabb_json(proxy_result.aabb)
	profile["posed_mesh_compare"] = comparison
	profile["proxy_nodes"] = proxy_result.nodes
	return true


func _bake_mesh(mesh_instance: MeshInstance3D, where: String) -> Dictionary:
	if mesh_instance.get_skeleton_path().is_empty() or mesh_instance.get_skin() == null:
		_failure = "%s mesh instance is not bound to a skeleton path and Skin" % where
		return {}
	var resolved_skeleton = mesh_instance.get_node_or_null(mesh_instance.get_skeleton_path())
	if not (resolved_skeleton is Skeleton3D):
		_failure = "%s mesh instance skeleton path does not resolve: %s" % [where, mesh_instance.get_skeleton_path()]
		return {}
	var skin_reference = mesh_instance.get_skin_reference()
	if skin_reference == null:
		_failure = "%s mesh instance SkinReference is null after skeleton/Skin binding: %s" % [where, mesh_instance.get_skeleton_path()]
		return {}
	if not skin_reference.get_skeleton().is_valid():
		_failure = "%s mesh instance SkinReference has an invalid skeleton RID: %s" % [where, mesh_instance.get_skeleton_path()]
		return {}
	var baked: ArrayMesh = mesh_instance.bake_mesh_from_current_skeleton_pose()
	if baked == null or baked.get_surface_count() != 1:
		_failure = "%s could not bake one current Skeleton3D pose surface" % where
		return {}
	var arrays := baked.surface_get_arrays(0)
	if arrays.size() <= Mesh.ARRAY_NORMAL or not (arrays[Mesh.ARRAY_VERTEX] is PackedVector3Array) or not (arrays[Mesh.ARRAY_NORMAL] is PackedVector3Array):
		_failure = "%s baked mesh arrays are incomplete" % where
		return {}
	return {"mesh": baked, "arrays": arrays}


func _compare_mesh_arrays(arrays: Array, expected: Dictionary, where: String) -> Dictionary:
	var vertices: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
	var normals: PackedVector3Array = arrays[Mesh.ARRAY_NORMAL]
	var indices: PackedInt32Array = arrays[Mesh.ARRAY_INDEX]
	if vertices.size() != expected.vertices.size() or normals.size() != expected.normals.size() or indices != expected.indices:
		_failure = "%s baked mesh counts or indices differ from published evidence" % where
		return {}
	var max_vertex_error := 0.0
	var max_normal_error := 0.0
	var max_normal_index := -1
	var max_actual_normal := Vector3.ZERO
	var max_expected_normal := Vector3.ZERO
	for index in range(vertices.size()):
		max_vertex_error = max(max_vertex_error, vertices[index].distance_to(expected.vertices[index]))
		var normal_error := normals[index].distance_to(expected.normals[index])
		if normal_error > max_normal_error:
			max_normal_error = normal_error
			max_normal_index = index
			max_actual_normal = normals[index]
			max_expected_normal = expected.normals[index]
	if max_vertex_error > TOLERANCE or max_normal_error > NORMAL_TOLERANCE:
		_failure = "%s host-baked mesh differs from published evidence beyond tolerance (vertex=%s normal=%s index=%d actual=%s expected=%s)" % [where, _report_float(max_vertex_error), _report_float(max_normal_error), max_normal_index, max_actual_normal, max_expected_normal]
		return {}
	return {
		"vertex_count": vertices.size(),
		"normal_count": normals.size(),
		"face_count": int(indices.size() / 3),
		"max_vertex_error": _report_float(max_vertex_error),
		"max_normal_error": _report_float(max_normal_error),
		"tolerance": TOLERANCE,
		"normal_tolerance": NORMAL_TOLERANCE,
		"matches_published": max_vertex_error <= TOLERANCE and max_normal_error <= NORMAL_TOLERANCE,
	}


func _build_host_proxies(profile: Dictionary, matrices: Dictionary) -> Dictionary:
	var body: StaticBody3D = profile.body
	var host_by_bone := {}
	var max_endpoint_error := 0.0
	var matching_node_count := 0
	var proxy_aabb := AABB()
	var has_aabb := false
	var neutral_by_bone: Dictionary = profile.structural.neutral_by_bone
	var posed_by_bone: Dictionary = profile.structural.posed_by_bone
	for bone_id in neutral_by_bone:
		var neutral_proxy = neutral_by_bone[bone_id]
		var posed_proxy = posed_by_bone[bone_id]
		var start: Vector3 = matrices[bone_id] * (_vector3(neutral_proxy.a, "%s proxy a" % profile.profile_id) as Vector3)
		var end: Vector3 = matrices[bone_id] * (_vector3(neutral_proxy.b, "%s proxy b" % profile.profile_id) as Vector3)
		var expected_start: Vector3 = _vector3(posed_proxy.a, "%s posed proxy a" % profile.profile_id)
		var expected_end: Vector3 = _vector3(posed_proxy.b, "%s posed proxy b" % profile.profile_id)
		var radius := float(neutral_proxy.radius)
		var segment := end - start
		var segment_length := segment.length()
		if not is_finite(segment_length) or segment_length <= 1.0e-12 or radius <= 0.0 or not is_finite(radius):
			_failure = "%s contains an invalid host proxy segment" % profile.profile_id
			return {}
		var shape := CapsuleShape3D.new()
		shape.radius = radius
		shape.height = segment_length + 2.0 * radius
		var collision := CollisionShape3D.new()
		collision.name = "Capsule_%s" % bone_id
		collision.shape = shape
		var orientation = _basis_for_y_axis(segment / segment_length, "%s proxy %s" % [profile.profile_id, bone_id])
		if orientation == null:
			return {}
		collision.transform = Transform3D(orientation, (start + end) * 0.5)
		body.add_child(collision)
		var observed := _read_proxy_geometry(collision, "%s proxy %s" % [profile.profile_id, bone_id])
		if observed.is_empty():
			return {}
		var observed_start: Vector3 = observed.start
		var observed_end: Vector3 = observed.end
		var observed_radius: float = observed.radius
		var endpoint_error: float = max(observed_start.distance_to(expected_start), observed_end.distance_to(expected_end))
		max_endpoint_error = max(max_endpoint_error, endpoint_error)
		if endpoint_error <= TOLERANCE and abs(observed_radius - radius) <= TOLERANCE:
			matching_node_count += 1
		var proxy_min := Vector3(min(observed_start.x, observed_end.x) - observed_radius, min(observed_start.y, observed_end.y) - observed_radius, min(observed_start.z, observed_end.z) - observed_radius)
		var proxy_max := Vector3(max(observed_start.x, observed_end.x) + observed_radius, max(observed_start.y, observed_end.y) + observed_radius, max(observed_start.z, observed_end.z) + observed_radius)
		var proxy_box := AABB(proxy_min, proxy_max - proxy_min)
		if not has_aabb:
			proxy_aabb = proxy_box
			has_aabb = true
		else:
			proxy_aabb = proxy_aabb.merge(proxy_box)
		host_by_bone[bone_id] = collision
	if body.get_child_count() != PROXY_COUNT or host_by_bone.size() != PROXY_COUNT or matching_node_count != PROXY_COUNT:
		_failure = "%s did not instantiate exactly 18 posed proxy shapes" % profile.profile_id
		return {}
	return {
		"aabb": proxy_aabb,
		"nodes": host_by_bone,
		"compare": {
			"endpoint_count": matching_node_count * 2,
			"max_endpoint_error": _report_float(max_endpoint_error),
			"tolerance": TOLERANCE,
			"matching_node_count": matching_node_count,
			"matches_published": matching_node_count == PROXY_COUNT and max_endpoint_error <= TOLERANCE,
		},
	}


func _read_proxy_geometry(collision: CollisionShape3D, where: String) -> Dictionary:
	if not is_instance_valid(collision) or not (collision.shape is CapsuleShape3D):
		_failure = "%s is not a valid host capsule node" % where
		return {}
	var shape: CapsuleShape3D = collision.shape
	var radius := shape.radius
	var segment_length := shape.height - 2.0 * radius
	if not is_finite(radius) or radius <= 0.0 or not is_finite(segment_length) or segment_length <= 1.0e-12:
		_failure = "%s has invalid read-back capsule dimensions" % where
		return {}
	var start := collision.transform * Vector3(0.0, -0.5 * segment_length, 0.0)
	var end := collision.transform * Vector3(0.0, 0.5 * segment_length, 0.0)
	if not is_finite(start.x) or not is_finite(start.y) or not is_finite(start.z) or not is_finite(end.x) or not is_finite(end.y) or not is_finite(end.z):
		_failure = "%s has non-finite read-back capsule endpoints" % where
		return {}
	return {"start": start, "end": end, "radius": radius}


func _readback_proxy_nodes(profile: Dictionary) -> Dictionary:
	var nodes = profile.get("proxy_nodes", {})
	if typeof(nodes) != TYPE_DICTIONARY or nodes.size() != PROXY_COUNT:
		_failure = "%s proxy node read-back is incomplete" % profile.profile_id
		return {}
	var neutral_by_bone: Dictionary = profile.structural.neutral_by_bone
	var posed_by_bone: Dictionary = profile.structural.posed_by_bone
	var matching_node_count := 0
	var max_endpoint_error := 0.0
	for bone in profile.ordered_bones:
		var bone_id: String = String(bone.id)
		if not nodes.has(bone_id) or not (nodes[bone_id] is CollisionShape3D):
			_failure = "%s proxy node read-back is missing bone %s" % [profile.profile_id, bone_id]
			return {}
		var collision: CollisionShape3D = nodes[bone_id]
		if collision.get_parent() != profile.body:
			_failure = "%s proxy node %s is not attached to its StaticBody3D" % [profile.profile_id, bone_id]
			return {}
		var observed := _read_proxy_geometry(collision, "%s proxy %s" % [profile.profile_id, bone_id])
		if observed.is_empty():
			return {}
		var expected_start: Vector3 = _vector3(posed_by_bone[bone_id].a, "%s posed proxy a" % profile.profile_id)
		var expected_end: Vector3 = _vector3(posed_by_bone[bone_id].b, "%s posed proxy b" % profile.profile_id)
		var observed_start: Vector3 = observed.start
		var observed_end: Vector3 = observed.end
		var endpoint_error: float = max(observed_start.distance_to(expected_start), observed_end.distance_to(expected_end))
		max_endpoint_error = max(max_endpoint_error, endpoint_error)
		var expected_radius := float(neutral_by_bone[bone_id].radius)
		if endpoint_error <= TOLERANCE and abs(float(observed.radius) - expected_radius) <= TOLERANCE:
			matching_node_count += 1
	return {
		"matching_node_count": matching_node_count,
		"max_endpoint_error": _report_float(max_endpoint_error),
	}


func _safe_avatar_root_name(index: int, instance_id: String) -> String:
	return "Avatar_%02d_%s" % [index, instance_id.replace("-", "_")]


func _readback_carrier_avatar_binding(profile: Dictionary, avatar_index: int, expected_record: Dictionary) -> Dictionary:
	var root = profile.get("root", null)
	if not (root is Node3D) or not is_instance_valid(root):
		_failure = "carrier avatar binding root is invalid"
		return {}
	var instance_id := String(expected_record.get("instance_id", ""))
	var expected_name := _safe_avatar_root_name(avatar_index, instance_id)
	if root.name != expected_name:
		_failure = "carrier avatar %s root name read-back is invalid" % instance_id
		return {}
	var metadata := {}
	for key in CARRIER_ROOT_METADATA_KEYS:
		if not root.has_meta(key):
			_failure = "carrier avatar %s root metadata is missing %s" % [instance_id, key]
			return {}
		metadata[key] = root.get_meta(key)
	var expected_metadata := {
		"ck_experiment_instance_id": expected_record.instance_id,
		"ck_profile_id": expected_record.profile_id,
		"ck_candidate_profile_sha256": expected_record.candidate_profile_sha256,
	}
	if metadata != expected_metadata:
		_failure = "carrier avatar %s root metadata does not match its validated record" % instance_id
		return {}
	return {
		"instance_id": metadata.ck_experiment_instance_id,
		"profile_id": metadata.ck_profile_id,
		"candidate_profile_sha256": metadata.ck_candidate_profile_sha256,
		"root_name": String(root.name),
		"root_metadata": metadata,
	}


func _readback_binding(profile: Dictionary) -> Dictionary:
	var skeleton: Skeleton3D = profile.skeleton
	var skin: Skin = profile.skin
	var mesh_instance: MeshInstance3D = profile.mesh_instance
	var skeleton_bone_count := skeleton.get_bone_count()
	var skin_bind_count := skin.get_bind_count()
	if skeleton_bone_count != BONE_COUNT or skin_bind_count != BONE_COUNT:
		_failure = "%s runtime Skeleton3D/Skin counts are not exactly 18" % profile.profile_id
		return {}

	var unique_bone_names := true
	var parent_links_match := true
	var neutral_rest_matches_published := true
	var skin_bind_poses_match_published := true
	var names := {}
	for bone_index in range(BONE_COUNT):
		var bone_name := String(skeleton.get_bone_name(bone_index))
		if bone_name.is_empty() or names.has(bone_name):
			unique_bone_names = false
		names[bone_name] = true
		var bone: Dictionary = profile.ordered_bones[bone_index]
		var expected_parent = bone.get("parent", null)
		var expected_parent_index := -1
		if expected_parent != null:
			if not profile.bone_indices.has(String(expected_parent)):
				_failure = "%s runtime parent lookup has an unknown expected parent" % profile.profile_id
				return {}
			expected_parent_index = int(profile.bone_indices[String(expected_parent)])
		if skeleton.get_bone_parent(bone_index) != expected_parent_index:
			parent_links_match = false
		var bone_id: String = String(bone.id)
		if _transform_matrix_error(skeleton.get_bone_rest(bone_index), profile.structural.local_bind[bone_id]) > TOLERANCE:
			neutral_rest_matches_published = false
		var bind_index := int(profile.skin_bind_indices[bone_id])
		if bind_index < 0 or bind_index >= skin_bind_count:
			skin_bind_poses_match_published = false
		else:
			var expected_bind_pose: Transform3D = _transform_from_matrix(profile.structural.bind_world[bone_id]).affine_inverse()
			if skin.get_bind_bone(bind_index) != bone_index or _transform_error(skin.get_bind_pose(bind_index), expected_bind_pose) > TOLERANCE:
				skin_bind_poses_match_published = false

	var skeleton_path := mesh_instance.get_skeleton_path()
	var resolved_skeleton = mesh_instance.get_node_or_null(skeleton_path)
	var mesh_skeleton_path_bound := not skeleton_path.is_empty() and resolved_skeleton == skeleton
	var mesh_skin_bound := mesh_instance.get_skin() == skin
	var skin_reference = mesh_instance.get_skin_reference()
	var skin_reference_valid := skin_reference != null and skin_reference.get_skeleton().is_valid()
	if not mesh_skeleton_path_bound or not mesh_skin_bound or not skin_reference_valid:
		_failure = "%s runtime MeshInstance3D/SkinReference binding is incomplete" % profile.profile_id
		return {}

	var pose_rotations: Dictionary = profile.get("pose_rotations", {})
	if pose_rotations.size() != BONE_COUNT:
		_failure = "%s runtime pose rotation read-back has incomplete selectors" % profile.profile_id
		return {}
	var pose_rule_match_count := 0
	var pose_global_match_count := 0
	var skin_match_count := 0
	for bone in profile.ordered_bones:
		var bone_id: String = String(bone.id)
		var bone_index: int = int(profile.bone_indices[bone_id])
		var selector = _pose_selector_for_bone(bone, profile.profile_id)
		if selector == null:
			return {}
		if not pose_rotations.has(selector):
			_failure = "%s runtime pose rotation read-back is missing selector %s" % [profile.profile_id, selector]
			return {}
		var expected_local_pose: Transform3D = skeleton.get_bone_rest(bone_index) * Transform3D(Basis(pose_rotations[selector]), Vector3.ZERO)
		if _transform_error(skeleton.get_bone_pose(bone_index), expected_local_pose) <= TOLERANCE:
			pose_rule_match_count += 1
		var global_pose: Transform3D = skeleton.get_bone_global_pose(bone_index)
		if _transform_matrix_error(global_pose, profile.structural.posed_world[bone_id]) <= TOLERANCE:
			pose_global_match_count += 1
		var bind_index: int = int(profile.skin_bind_indices[bone_id])
		var skin_transform: Transform3D = global_pose * skin.get_bind_pose(bind_index)
		if _transform_matrix_error(skin_transform, profile.structural.skin[bone_id]) <= TOLERANCE:
			skin_match_count += 1

	var neutral_compare: Dictionary = profile.get("neutral_mesh_compare", {})
	var posed_compare: Dictionary = profile.get("posed_mesh_compare", {})
	if neutral_compare.is_empty() or posed_compare.is_empty() or typeof(neutral_compare.get("matches_published", null)) != TYPE_BOOL or typeof(posed_compare.get("matches_published", null)) != TYPE_BOOL:
		_failure = "%s runtime baked mesh comparisons are incomplete" % profile.profile_id
		return {}
	var proxy_readback := _readback_proxy_nodes(profile)
	if proxy_readback.is_empty():
		return {}
	var binding := {
		"skeleton_bone_count": skeleton_bone_count,
		"skin_bind_count": skin_bind_count,
		"unique_bone_names": unique_bone_names,
		"parent_links_match": parent_links_match,
		"neutral_rest_matches_published": neutral_rest_matches_published,
		"skin_bind_poses_match_published": skin_bind_poses_match_published,
		"mesh_skeleton_path_bound": mesh_skeleton_path_bound,
		"mesh_skin_bound": mesh_skin_bound,
		"neutral_baked_mesh_matches": neutral_compare.matches_published,
		"posed_baked_mesh_matches": posed_compare.matches_published,
		"pose_rules_applied": pose_rule_match_count,
		"pose_global_matrices_match": pose_global_match_count,
		"skin_matrices_match": skin_match_count,
		"posed_proxy_nodes_match": proxy_readback.matching_node_count,
		"tolerance": TOLERANCE,
		"normal_tolerance": NORMAL_TOLERANCE,
		"max_neutral_vertex_error": neutral_compare.max_vertex_error,
		"max_neutral_normal_error": neutral_compare.max_normal_error,
		"max_posed_vertex_error": posed_compare.max_vertex_error,
		"max_posed_normal_error": posed_compare.max_normal_error,
		"max_posed_proxy_endpoint_error": proxy_readback.max_endpoint_error,
	}
	if not unique_bone_names or not parent_links_match or not neutral_rest_matches_published or not skin_bind_poses_match_published or pose_rule_match_count != BONE_COUNT or pose_global_match_count != BONE_COUNT or skin_match_count != BONE_COUNT or not neutral_compare.matches_published or not posed_compare.matches_published or proxy_readback.matching_node_count != PROXY_COUNT:
		_failure = "%s runtime binding read-back does not satisfy the expected host-local evidence" % profile.profile_id
		return {}
	return binding


func _readback_node_counts(profile: Dictionary) -> Dictionary:
	var root = profile.get("root", null)
	var body = profile.get("body", null)
	if not (root is Node3D) or not is_instance_valid(root) or not (body is StaticBody3D) or not is_instance_valid(body):
		_failure = "runtime profile root or StaticBody3D is invalid"
		return {}
	var root_node: Node3D = root
	var body_node: StaticBody3D = body
	var skeleton_count := 0
	var mesh_instance_count := 0
	var body_count := 0
	for child in root_node.get_children():
		if child is Skeleton3D:
			skeleton_count += 1
		elif child is MeshInstance3D:
			mesh_instance_count += 1
		elif child is StaticBody3D:
			body_count += 1
	var collision_count := 0
	for child in body_node.get_children():
		if child is CollisionShape3D:
			collision_count += 1
	var counts := {
		"profile_root": 1 if is_instance_valid(root_node) else 0,
		"skeleton_3d": skeleton_count,
		"mesh_instance_3d": mesh_instance_count,
		"static_body_3d": body_count,
		"collision_shape_3d": collision_count,
		"total_profile_nodes": _count_profile_nodes(root_node),
	}
	if root_node.get_child_count() != 3 or body_node.get_child_count() != PROXY_COUNT or collision_count != body_node.get_child_count() or counts.total_profile_nodes != 4 + PROXY_COUNT:
		_failure = "runtime profile node read-back does not match the constructed tree"
		return {}
	return counts


func _count_profile_nodes(node: Node) -> int:
	var total := 1
	for child in node.get_children():
		total += _count_profile_nodes(child)
	return total


func _check_neutral_separation(profiles: Array[Dictionary]) -> bool:
	var first: Dictionary = profiles[0]
	var second: Dictionary = profiles[1]
	var first_translation: Vector3 = first.root.position
	var second_translation: Vector3 = second.root.position
	var first_max := float(first.neutral.aabb.end.x) + first_translation.x
	var second_min := float(second.neutral.aabb.position.x) + second_translation.x
	return first_max < second_min


func _check_posed_separation(profiles: Array[Dictionary]) -> bool:
	var first: Dictionary = profiles[0]
	var second: Dictionary = profiles[1]
	var first_translation: Vector3 = first.root.position
	var second_translation: Vector3 = second.root.position
	var first_max := float(first.posed_proxy_aabb.max[0]) + first_translation.x
	var second_min := float(second.posed_proxy_aabb.min[0]) + second_translation.x
	if first_max >= second_min:
		_failure = "fixed host-only translations do not separate the posed proxy evidence"
		return false
	return true


func _build_report(options: Dictionary, validated: Dictionary, loaded_profiles: Array[Dictionary]) -> Dictionary:
	var candidate_hashes := {}
	var profiles: Array[Dictionary] = []
	var carrier_avatar_bindings: Array[Dictionary] = []
	var profile_translations: Array = []
	var pose_rule_count := -1
	var pose_rules_validated := true
	for index in range(loaded_profiles.size()):
		var profile: Dictionary = loaded_profiles[index]
		candidate_hashes[profile.profile_id] = profile.candidate_profile_sha256
		var metrics: Dictionary = profile.metrics
		var binding := _readback_binding(profile)
		if binding.is_empty():
			return {}
		var node_counts := _readback_node_counts(profile)
		if node_counts.is_empty():
			return {}
		var actual_translation: Vector3 = profile.root.position
		var expected_translation: Vector3 = profile.expected_translation
		if actual_translation.distance_to(expected_translation) > TOLERANCE:
			_failure = "%s runtime profile translation differs from the expected host-only placement" % profile.profile_id
			return {}
		if options.has("carrier_identity"):
			var carrier_binding := _readback_carrier_avatar_binding(profile, index, options.carrier_avatar_records[index])
			if carrier_binding.is_empty():
				return {}
			carrier_avatar_bindings.append(carrier_binding)
		profile_translations.append(_vector_json(actual_translation))
		var profile_pose_rule_count := int(binding.pose_rules_applied)
		if pose_rule_count < 0:
			pose_rule_count = profile_pose_rule_count
		elif profile_pose_rule_count != pose_rule_count:
			_failure = "runtime profiles disagree on the applied shared-pose rule count"
			return {}
		pose_rules_validated = pose_rules_validated and profile.pose_rules_validated
		profiles.append({
			"profile_id": profile.profile_id,
			"candidate_profile_sha256": profile.candidate_profile_sha256,
			"metrics": metrics,
			"profile_translation": _vector_json(actual_translation),
			"counts": {
				"neutral_vertex_count": profile.neutral.vertices.size(),
				"posed_vertex_count": profile.posed.vertices.size(),
				"face_count": int(profile.posed.indices.size() / 3),
				"bone_count": binding.skeleton_bone_count,
				"proxy_count": node_counts.collision_shape_3d,
				"weight_vertex_count": int(profile.weights.vertex_count),
				"influence_count": int(_influence_count(profile.weights.influences)),
			},
			"neutral_mesh_aabb": profile.neutral_mesh_aabb,
			"posed_mesh_aabb": profile.posed_mesh_aabb,
			"posed_proxy_aabb": profile.posed_proxy_aabb,
			"node_counts": node_counts,
			"binding": binding,
		})
	if pose_rule_count < 0 or not pose_rules_validated:
		_failure = "runtime shared-pose evidence is incomplete"
		return {}
	var report := {
		"schema": REPORT_SCHEMA,
		"status": "success",
		"boundary": REPORT_BOUNDARY,
		"claims": ["host-local Skeleton3D/Skin pose binding", "host-local consumption of the shared structural pose recipe"],
		"scope_flags": {
			"physics_stepping": false,
			"animation": false,
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
			"scope": REPORT_BOUNDARY,
			"profile_translations": profile_translations,
		},
		"pose_binding": {
			"pose_id": validated.pose_id,
			"pose_sha256": validated.pose_sha256,
			"path": POSE_FILE,
			"rule_count": pose_rule_count,
			"rules_validated": pose_rules_validated,
			"applied_to_skeleton3d": pose_rule_count == BONE_COUNT,
			"ik": false,
			"contact": false,
		},
		"profiles": profiles,
	}
	if options.has("carrier_identity"):
		report["validated_carrier"] = options.carrier_identity
		report["carrier_avatar_bindings"] = carrier_avatar_bindings
	return report


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
		_failure = "%s has an incomplete PLY record stream" % where
		return {}
	if lines[0] != "ply" or lines[1] != "format ascii 1.0" or lines[3] != "property float x" or lines[4] != "property float y" or lines[5] != "property float z" or lines[6] != "property float nx" or lines[7] != "property float ny" or lines[8] != "property float nz" or lines[10] != "property list uchar int vertex_indices" or lines[11] != "end_header":
		_failure = "%s has an unsupported PLY schema" % where
		return {}
	var vertex_count := _canonical_count(lines[2], "element vertex ", MAX_VERTICES, where + " vertex count")
	var face_count := _canonical_count(lines[9], "element face ", MAX_FACES, where + " face count")
	if vertex_count < 0 or face_count < 0 or lines.size() != 12 + vertex_count + face_count + 1:
		_failure = "%s has invalid PLY record counts" % where
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
		lower = Vector3(min(lower.x, point.x), min(lower.y, point.y), min(lower.z, point.z))
		upper = Vector3(max(upper.x, point.x), max(upper.y, point.y), max(upper.z, point.z))
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
		_failure = "%s cannot be opened" % where
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
		if typeof(item) == TYPE_BOOL or not is_finite(float(item)):
			_failure = "%s contains a non-finite vector item" % where
			return null
	return Vector3(float(value[0]), float(value[1]), float(value[2]))


func _basis_for_y_axis(direction: Vector3, where: String) -> Variant:
	if not is_finite(direction.x) or not is_finite(direction.y) or not is_finite(direction.z) or direction.length_squared() <= 1.0e-24:
		_failure = "%s has an invalid capsule direction" % where
		return null
	var y_axis := direction.normalized()
	var reference := Vector3.BACK
	if abs(y_axis.dot(reference)) > 0.9:
		reference = Vector3.RIGHT
	var x_axis := y_axis.cross(reference).normalized()
	var z_axis := x_axis.cross(y_axis).normalized()
	var result := Basis(x_axis, y_axis, z_axis)
	if abs(result.determinant() - 1.0) > TOLERANCE:
		_failure = "%s could not construct an orthonormal capsule basis" % where
		return null
	return result


func _matrix(value, where: String) -> Array:
	if typeof(value) != TYPE_ARRAY or value.size() != 16:
		_failure = "%s is not a 4x4 matrix" % where
		return []
	var result: Array = []
	for item in value:
		if typeof(item) == TYPE_BOOL or not is_finite(float(item)):
			_failure = "%s contains a non-finite matrix value" % where
			return []
		result.append(float(item))
	if abs(result[12]) > TOLERANCE or abs(result[13]) > TOLERANCE or abs(result[14]) > TOLERANCE or abs(result[15] - 1.0) > TOLERANCE:
		_failure = "%s is not an affine column-vector matrix" % where
		return []
	return result


func _matrix_transform(matrix: Array) -> Transform3D:
	return Transform3D(
		Basis(
			Vector3(matrix[0], matrix[4], matrix[8]),
			Vector3(matrix[1], matrix[5], matrix[9]),
			Vector3(matrix[2], matrix[6], matrix[10])
		),
		Vector3(matrix[3], matrix[7], matrix[11])
	)


func _transform_from_matrix(matrix: Array) -> Transform3D:
	return _matrix_transform(matrix)


func _transform_matrix_error(value: Transform3D, expected: Array) -> float:
	var actual := [
		value.basis.x.x, value.basis.y.x, value.basis.z.x, value.origin.x,
		value.basis.x.y, value.basis.y.y, value.basis.z.y, value.origin.y,
		value.basis.x.z, value.basis.y.z, value.basis.z.z, value.origin.z,
		0.0, 0.0, 0.0, 1.0,
	]
	var maximum := 0.0
	for index in range(16):
		maximum = max(maximum, abs(float(actual[index]) - float(expected[index])))
	return maximum


func _transform_error(left: Transform3D, right: Transform3D) -> float:
	var left_values := [
		left.basis.x.x, left.basis.y.x, left.basis.z.x, left.origin.x,
		left.basis.x.y, left.basis.y.y, left.basis.z.y, left.origin.y,
		left.basis.x.z, left.basis.y.z, left.basis.z.z, left.origin.z,
	]
	var right_values := [
		right.basis.x.x, right.basis.y.x, right.basis.z.x, right.origin.x,
		right.basis.x.y, right.basis.y.y, right.basis.z.y, right.origin.y,
		right.basis.x.z, right.basis.y.z, right.basis.z.z, right.origin.z,
	]
	var maximum := 0.0
	for index in range(left_values.size()):
		maximum = max(maximum, abs(float(left_values[index]) - float(right_values[index])))
	return maximum


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


func _bounds_match(value, aabb: AABB) -> bool:
	if typeof(value) != TYPE_DICTIONARY:
		return false
	var minimum = _vector3(value.get("min", []), "bounds min")
	var maximum = _vector3(value.get("max", []), "bounds max")
	if minimum == null or maximum == null:
		return false
	return (minimum as Vector3).distance_to(aabb.position) <= TOLERANCE and (maximum as Vector3).distance_to(aabb.end) <= TOLERANCE


func _aabb_json(aabb: AABB) -> Dictionary:
	return {"min": _vector_json(aabb.position), "max": _vector_json(aabb.end)}


func _vector_json(value: Vector3) -> Array[float]:
	return [value.x, value.y, value.z]


func _influence_count(rows) -> int:
	var total := 0
	for row in rows:
		total += row.size()
	return total


func _report_float(value: float) -> float:
	return round(value * 1.0e12) / 1.0e12


func _write_report(path: String, report: Dictionary) -> bool:
	if not _failure.is_empty():
		return false
	var file := FileAccess.open(path, FileAccess.WRITE)
	if file == null:
		_failure = "report cannot be opened for writing"
		return false
	file.store_string(JSON.stringify(report) + "\n")
	file.flush()
	var error := file.get_error()
	file.close()
	if error != OK:
		_failure = "report cannot be written"
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
	push_error("skeletal pose smoke failed: %s" % _failure)
	return 1
