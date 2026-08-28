extends SceneTree

const MAX_ARTIFACT_BYTES := 32 * 1024 * 1024
const MAX_VERTICES := 100000
const MAX_FACES := 200000
const BONE_COUNT := 18
const PROXY_COUNT := 18
const MAX_WEIGHT_ROW := 4
const TOLERANCE := 2.0e-5
const NORMAL_TOLERANCE := 3.0e-4
# Source and command recipe validation remains stricter than runtime readback.
const POSE_QUATERNION_TOLERANCE := 1.0e-7
# Godot's Basis-to-Quaternion reconstruction can add a few float32 ULPs.
const RUNTIME_POSE_QUATERNION_TOLERANCE := 5.0e-7
const WEIGHT_TOLERANCE := 1.0e-6
const TRANSLATIONS := [Vector3(-8.0, 0.0, 0.0), Vector3(8.0, 0.0, 0.0)]
const EXPECTED_GODOT_VERSION := "4.7.2.stable.official.ed1daf0bf"
const GALLERY_FORMAT := "creature-kernel.disposable-structural-embodiment-gallery.v1"
const POSE_FORMAT := "creature-kernel.disposable-structural-embodiment-shared-pose.v1"
const POSE_FILE := "structural_embodiment_shared_pose.json"
const REPORT_SCHEMA := "creature-kernel.disposable-godot-skeletal-pose-smoke.v1"
const REPORT_BOUNDARY := "host_local_skeleton3d_skin_pose_binding"
const CONTACT_REPORT_BOUNDARY := "experiment_local_semantic_contact_and_physical_response"
const CARRIER_SCHEMA := "creature-kernel.disposable-engine-neutral-avatar-input.v1"
const CARRIER_BOUNDARY := "experiment_input_only_no_runtime_package_or_adapter_contract"
const CK_PROJECTION_SCHEMA := "creature-kernel.disposable-ck-rust-projection.v1"
const CK_PROJECTION_BOUNDARY := "experiment_local_ck_projection_evidence_only"
const CK_PROJECTION_IDENTITY_SCOPE := "canonical_transport_body_only_not_provenance"
const CK_PROJECTION_MAX_BYTES := 4 * 1024 * 1024
const CK_PROJECTION_MAX_CLI_BYTES := 128 * 1024 * 1024
const CK_PROJECTION_MAX_JSON_NODES := 200000
const CK_PROJECTION_MAX_JSON_DEPTH := 96
const CK_PROJECTION_MAX_STRING_LENGTH := 65536
const CK_PROJECTION_MAX_DEPENDENCIES := 4096
const CK_PROJECTION_MAX_SOURCE_BYTES := 16 * 1024 * 1024
const CK_PROJECTION_RUST_FORMAT := "creature-kernel.provisional-structural-inspection.v1"
const CK_PROJECTION_RUST_OPERATION := "inspect-structure"
const CK_PROJECTION_RUST_STAGE := "structural-validation"
const CK_PROJECTION_SOURCE_DIR := "sources"
const CARRIER_ROOT_METADATA_KEYS := [
	"ck_experiment_instance_id",
	"ck_profile_id",
	"ck_candidate_profile_sha256",
]
const SEMANTIC_POSE_COMMAND_SCHEMA := "creature-kernel.disposable-semantic-pose-command.v1"
const SEMANTIC_POSE_COMMAND_BOUNDARY := "experiment_local_command_evidence_only_no_adapter_or_runtime_conformance"
const SEMANTIC_POSE_COMMAND_ID := "inject-semantic-pose"
const SEMANTIC_POSE_COMMAND_VERSION := 1
const SEMANTIC_POSE_COMMAND_RULE_COUNT := 18
const SEMANTIC_CONTACT_COMMAND_SCHEMA := "creature-kernel.disposable-semantic-contact-command.v1"
const SEMANTIC_CONTACT_COMMAND_BOUNDARY := "experiment_local_contact_command_evidence_only_no_adapter_or_runtime_conformance"
const SEMANTIC_CONTACT_COMMAND_ID := "probe-single-semantic-contact"
const SEMANTIC_CONTACT_COMMAND_VERSION := 1
const SEMANTIC_CONTACT_MAPPING_REVISION := "joint-selector-to-posed-proxy-v1"
const CONTACT_PHASE_ORDER := ["approach", "contact", "release", "exit"]
const CONTACT_PARTICIPANTS := [
	# Godot's JSON parser materializes JSON numbers as floats.  Keep the
	# comparison constants in that representation; the command's canonical
	# bytes and identity still distinguish the authored integer spelling.
	{"role": "actuator", "target_index": 0.0, "selector": {"kind": "joint", "role": "wrist", "anchors": ["right"]}},
	{"role": "response", "target_index": 1.0, "selector": {"kind": "joint", "role": "wrist", "anchors": ["left"]}},
]
const CONTACT_INTERACTION := {"kind": "single-proxy-press-release", "phase_order": CONTACT_PHASE_ORDER}
const CONTACT_APPROACH_TICKS := 24
const CONTACT_HOLD_TICKS := 8
const CONTACT_RELEASE_TICKS := 24
const CONTACT_EXIT_TICKS := 8
const CONTACT_MAX_TICKS := 256
const CONTACT_COLLISION_LAYER := 2
const CONTACT_OVERDRIVE := 2.0e-2
const CONTACT_GEOMETRY_TOLERANCE := 1.0e-5
const CONTACT_MIN_IMPULSE := 1.0e-5
const CONTACT_MIN_NORMAL_VELOCITY := 1.0e-5
const CONTACT_MIN_NORMAL_DISPLACEMENT := 1.0e-5
const ARTIFACT_NAMES := [
	"neutral.ply",
	"posed.ply",
	"skeleton.json",
	"weights.json",
	"proxies-neutral.json",
	"proxies-posed.json",
]


class ContactCaptureBody extends RigidBody3D:
	var probe_tick: int = 0
	var probe_phase: String = "setup"
	var expected_collider_id: int = 0
	var tick_evidence: Array[Dictionary] = []
	var contact_samples: Array[Dictionary] = []

	func _integrate_forces(state: PhysicsDirectBodyState3D) -> void:
		var contact_count := state.get_contact_count()
		tick_evidence.append({"tick": probe_tick, "phase": probe_phase, "contact_count": contact_count})
		for contact_index in range(contact_count):
			var collider_object := state.get_contact_collider_object(contact_index)
			var collider_id: int = int(state.get_contact_collider_id(contact_index))
			var collider_shape: int = state.get_contact_collider_shape(contact_index)
			var local_shape: int = state.get_contact_local_shape(contact_index)
			var point: Vector3 = state.get_contact_local_position(contact_index)
			var normal: Vector3 = state.get_contact_local_normal(contact_index)
			var impulse: Vector3 = state.get_contact_impulse(contact_index)
			contact_samples.append({
				"contact_index": contact_index,
				"collider_id": collider_id,
				"collider_object_id": int(collider_object.get_instance_id()) if collider_object != null else 0,
				"collider_shape_index": collider_shape,
				"local_shape_index": local_shape,
				"point": [point.x, point.y, point.z],
				"normal": [normal.x, normal.y, normal.z],
				"impulse": [impulse.x, impulse.y, impulse.z],
				"tick": probe_tick,
				"phase": probe_phase,
			})
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
	var pose: Dictionary
	if options.semantic_pose_command_present:
		pose = _load_semantic_pose_command(options, validated)
	else:
		pose = _load_shared_pose(options.gallery_path, validated)
	if pose.is_empty():
		return _fail_exit()
	if options.semantic_contact_command_present:
		var contact_command := _load_semantic_contact_command(options)
		if contact_command.is_empty():
			return _fail_exit()
	if get_root().get_child_count() != 0:
		return _fail("the disposable scene root was not empty before instantiation")

	var loaded_profiles: Array[Dictionary] = []
	var carrier_avatar_records: Array = options.get("carrier_avatar_records", [])
	for index in range(2):
		var profile_id: String = options.profile_ids[index]
		var profile_payload: Dictionary = _profile_payload(validated, profile_id)
		if options.has("ck_projection_profile_payloads"):
			profile_payload = options.ck_projection_profile_payloads[profile_id]
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
	if options.has("semantic_contact_command"):
		var contact_probe: Dictionary = await _run_contact_probe(loaded_profiles, options)
		if contact_probe.is_empty():
			_release_profiles(loaded_profiles)
			return _fail_exit()
		options["semantic_contact_probe"] = contact_probe
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
		"semantic_pose_command_json": "",
		"semantic_pose_command_identity_json": "",
		"semantic_pose_payload_json": "",
		"semantic_pose_command_present": false,
		"semantic_pose_command_identity_present": false,
		"semantic_pose_payload_present": false,
		"semantic_contact_command_json": "",
		"semantic_contact_command_present": false,
		"semantic_contact_command_identity_json": "",
		"semantic_contact_command_identity_present": false,
		"ck_projection_json": "",
		"ck_projection_identity_json": "",
		"ck_projection_present": false,
		"ck_projection_identity_present": false,
	}
	var index := 0
	while index < arguments.size():
		var argument: String = arguments[index]
		if argument == "--gallery" or argument == "--report" or argument == "--validated-json" or argument == "--carrier-identity-json" or argument == "--carrier-avatar-records-json" or argument == "--semantic-pose-command-json" or argument == "--semantic-pose-command-identity-json" or argument == "--semantic-pose-payload-json" or argument == "--semantic-contact-command-json" or argument == "--semantic-contact-command-identity-json" or argument == "--ck-projection-json" or argument == "--ck-projection-identity-json" or argument == "--profile-id":
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
			elif argument == "--semantic-pose-command-json":
				result.semantic_pose_command_json = value
				result.semantic_pose_command_present = true
			elif argument == "--semantic-pose-command-identity-json":
				result.semantic_pose_command_identity_json = value
				result.semantic_pose_command_identity_present = true
			elif argument == "--semantic-pose-payload-json":
				result.semantic_pose_payload_json = value
				result.semantic_pose_payload_present = true
			elif argument == "--semantic-contact-command-json":
				result.semantic_contact_command_json = value
				result.semantic_contact_command_present = true
			elif argument == "--semantic-contact-command-identity-json":
				result.semantic_contact_command_identity_json = value
				result.semantic_contact_command_identity_present = true
			elif argument == "--ck-projection-json":
				result.ck_projection_json = value
				result.ck_projection_present = true
			elif argument == "--ck-projection-identity-json":
				result.ck_projection_identity_json = value
				result.ck_projection_identity_present = true
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
	var projection_presence_count := int(options.ck_projection_present) + int(options.ck_projection_identity_present)
	if projection_presence_count != 0 and projection_presence_count != 2:
		_failure = "CK projection and projection identity must be supplied together"
		return false
	if projection_presence_count == 2:
		if not _validate_ck_projection(options, validated):
			return false
	var command_values := [
		options.semantic_pose_command_present,
		options.semantic_pose_command_identity_present,
		options.semantic_pose_payload_present,
	]
	var command_value_count := 0
	for supplied in command_values:
		if supplied:
			command_value_count += 1
	if command_value_count != 0 and command_value_count != command_values.size():
		_failure = "semantic pose command, identity, and payload must be supplied together"
		return false
	if command_value_count == command_values.size() and not options.has("carrier_identity"):
		_failure = "semantic pose command requires a validated carrier"
		return false
	if options.semantic_contact_command_present:
		if not options.semantic_contact_command_identity_present:
			_failure = "semantic contact command and contact command identity must be supplied together"
			return false
		if command_value_count != command_values.size() or not options.has("carrier_identity"):
			_failure = "semantic contact command requires a validated semantic pose command and carrier"
			return false
		if projection_presence_count != 2 or not options.has("ck_projection"):
			_failure = "semantic contact command requires the validated CK projection and explicit CLI evidence"
			return false
	elif options.semantic_contact_command_identity_present:
		_failure = "semantic contact command identity was supplied without the contact command"
		return false
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
		var code: int = value.unicode_at(index)
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


func _validate_ck_projection(options: Dictionary, validated: Dictionary) -> bool:
	if not options.has("carrier_identity") or not options.has("carrier_avatar_records"):
		_failure = "CK projection requires separately validated carrier identity and avatar records"
		return false
	var projection_json: String = options.ck_projection_json
	var identity_json: String = options.ck_projection_identity_json
	if projection_json.is_empty() or projection_json.ends_with("\n") or identity_json.is_empty() or identity_json.ends_with("\n"):
		_failure = "CK projection inputs must be non-empty canonical JSON without a trailing newline"
		return false
	var projection_value = JSON.parse_string(projection_json)
	var identity_value = JSON.parse_string(identity_json)
	if typeof(projection_value) != TYPE_DICTIONARY or typeof(identity_value) != TYPE_DICTIONARY:
		_failure = "CK projection inputs must be JSON objects"
		return false
	var projection: Dictionary = projection_value
	var identity: Dictionary = identity_value
	if projection_json.to_utf8_buffer().size() + 1 > CK_PROJECTION_MAX_BYTES:
		_failure = "CK projection exceeds its bounded transport size"
		return false
	if not _validate_ck_projection_json(projection, options, validated):
		return false
	if not _validate_ck_projection_identity(identity, projection):
		return false
	var projection_records: Array[Dictionary] = []
	var projection_payloads := {}
	for avatar in projection.avatars:
		var carrier_record := {
			"instance_id": avatar.instance_id,
			"profile_id": avatar.profile_id,
			"candidate_profile_sha256": avatar.candidate_profile_sha256,
		}
		projection_records.append(carrier_record)
		var reconstructed := {
			"profile_id": avatar.profile_id,
			"label": avatar.label,
			"candidate_profile_sha256": avatar.candidate_profile_sha256,
			"artifacts": avatar.artifacts,
			"metrics": avatar.metrics,
		}
		projection_payloads[avatar.profile_id] = reconstructed
	options["carrier_avatar_records"] = projection_records
	options["ck_projection"] = projection
	options["ck_projection_identity"] = identity
	options["ck_projection_avatars"] = projection.avatars
	options["ck_projection_profile_payloads"] = projection_payloads
	return true


func _validate_ck_projection_json(projection: Dictionary, options: Dictionary, validated: Dictionary) -> bool:
	if not _exact_keys(projection, ["schema", "boundary", "projection_identity", "producer_identity", "carrier_identity", "gallery_identity", "shared_pose", "avatars"]):
		_failure = "CK projection has unexpected or missing top-level fields"
		return false
	if projection.schema != CK_PROJECTION_SCHEMA or projection.boundary != CK_PROJECTION_BOUNDARY:
		_failure = "CK projection schema or boundary is invalid"
		return false
	if not _validate_ck_projection_finite(projection):
		_failure = "CK projection contains unsupported, non-finite, or oversized JSON"
		return false
	if _projection_has_forbidden_field(projection):
		_failure = "CK projection contains a forbidden host, package, adapter, or readiness field"
		return false
	if not _validate_ck_projection_transport_identity_shape(projection.projection_identity):
		return false
	var producer = projection.producer_identity
	if typeof(producer) != TYPE_DICTIONARY or not _exact_keys(producer, ["sha256", "bytes", "operation", "format"]):
		_failure = "CK projection producer identity has unexpected or missing fields"
		return false
	if not _is_sha256(String(producer.sha256)) or not _is_bounded_ck_projection_integer(producer.bytes, CK_PROJECTION_MAX_CLI_BYTES, false) or producer.operation != CK_PROJECTION_RUST_OPERATION or producer.format != CK_PROJECTION_RUST_FORMAT:
		_failure = "CK projection producer identity is invalid"
		return false
	var carrier = projection.carrier_identity
	if typeof(carrier) != TYPE_DICTIONARY or not _exact_keys(carrier, ["schema", "boundary", "sha256", "bytes", "instance_ids"]):
		_failure = "CK projection carrier identity has unexpected or missing fields"
		return false
	var supplied_carrier: Dictionary = options.carrier_identity
	if carrier.schema != CARRIER_SCHEMA or carrier.boundary != CARRIER_BOUNDARY or carrier.sha256 != supplied_carrier.sha256:
		_failure = "CK projection carrier identity does not match the validated carrier"
		return false
	if not _is_bounded_ck_projection_integer(carrier.bytes, CK_PROJECTION_MAX_BYTES, false) or int(carrier.bytes) != int(supplied_carrier.byte_count_decimal):
		_failure = "CK projection carrier byte identity does not match the validated carrier"
		return false
	if carrier.instance_ids != supplied_carrier.experiment_instance_ids:
		_failure = "CK projection carrier instance identities do not match the validated carrier"
		return false
	var gallery = projection.gallery_identity
	if typeof(gallery) != TYPE_DICTIONARY or not _exact_keys(gallery, ["projection_contract", "manifest_sha256", "manifest_bytes", "boundary", "profile_ids"]):
		_failure = "CK projection gallery identity has unexpected or missing fields"
		return false
	var expected_gallery := {
		"projection_contract": validated.projection_contract,
		"manifest_sha256": validated.manifest_sha256,
		"manifest_bytes": validated.manifest_bytes,
		"boundary": validated.boundary,
		"profile_ids": validated.profile_ids,
	}
	if not _exact_json_value(gallery, expected_gallery):
		_failure = "CK projection gallery identity does not match the validated payload"
		return false
	var shared_pose = projection.shared_pose
	if typeof(shared_pose) != TYPE_DICTIONARY or not _exact_keys(shared_pose, ["path", "pose_id", "sha256", "bytes"]):
		_failure = "CK projection shared-pose identity has unexpected or missing fields"
		return false
	var pose_bytes := _read_bytes(options.gallery_path.path_join(POSE_FILE), "shared pose")
	if pose_bytes.is_empty() or shared_pose.path != POSE_FILE or shared_pose.pose_id != validated.pose_id or shared_pose.sha256 != validated.pose_sha256 or not _is_bounded_ck_projection_integer(shared_pose.bytes, CK_PROJECTION_MAX_SOURCE_BYTES, false) or int(shared_pose.bytes) != pose_bytes.size() or _sha256(pose_bytes) != shared_pose.sha256:
		_failure = "CK projection shared-pose identity does not match the validated gallery"
		return false
	var avatars = projection.avatars
	if typeof(avatars) != TYPE_ARRAY or avatars.size() != 2:
		_failure = "CK projection must contain exactly two ordered avatars"
		return false
	for index in range(2):
		var avatar = avatars[index]
		if not _validate_ck_projection_avatar(avatar, index, options, validated):
			return false
	return true


func _validate_ck_projection_avatar(avatar, index: int, options: Dictionary, validated: Dictionary) -> bool:
	if typeof(avatar) != TYPE_DICTIONARY or not _exact_keys(avatar, ["instance_id", "profile_id", "label", "candidate_profile_sha256", "source", "rust_inspection", "artifacts", "metrics"]):
		_failure = "CK projection avatar %d has unexpected or missing fields" % index
		return false
	if avatar.instance_id != String(options.carrier_identity.experiment_instance_ids[index]) or avatar.profile_id != String(options.profile_ids[index]):
		_failure = "CK projection avatar %d identity is reordered or mismatched" % index
		return false
	var carrier_record: Dictionary = options.carrier_avatar_records[index]
	if avatar.instance_id != carrier_record.instance_id or avatar.profile_id != carrier_record.profile_id or avatar.candidate_profile_sha256 != carrier_record.candidate_profile_sha256:
		_failure = "CK projection avatar %d does not match the separately supplied carrier record" % index
		return false
	var validated_profile := _profile_payload(validated, String(avatar.profile_id))
	if validated_profile.is_empty() or not _exact_keys(validated_profile, ["profile_id", "label", "candidate_profile_sha256", "artifacts", "metrics"]):
		_failure = "CK projection avatar %d has no exact validated profile counterpart" % index
		return false
	var reconstructed := {
		"profile_id": avatar.profile_id,
		"label": avatar.label,
		"candidate_profile_sha256": avatar.candidate_profile_sha256,
		"artifacts": avatar.artifacts,
		"metrics": avatar.metrics,
	}
	if not _exact_json_value(reconstructed, validated_profile):
		_failure = "CK projection avatar %d cannot reconstruct the validated profile exactly" % index
		return false
	if not _validate_ck_projection_source(avatar.source, avatar.rust_inspection, String(avatar.profile_id), options.gallery_path):
		return false
	if not _validate_ck_projection_artifacts(avatar.artifacts, validated_profile.artifacts, String(avatar.profile_id)):
		return false
	return true


func _validate_ck_projection_source(source, rust_inspection, profile_id: String, gallery_path: String) -> bool:
	if typeof(source) != TYPE_DICTIONARY or not _exact_keys(source, ["path", "sha256", "bytes", "document", "namespace"]):
		_failure = "%s CK projection source identity has unexpected or missing fields" % profile_id
		return false
	var expected_path := "%s/%s.json" % [CK_PROJECTION_SOURCE_DIR, profile_id]
	if source.path != expected_path or String(source.path).is_absolute_path():
		_failure = "%s CK projection source path is invalid" % profile_id
		return false
	if typeof(source.sha256) != TYPE_STRING or not _is_sha256(source.sha256) or not _is_bounded_ck_projection_integer(source.bytes, CK_PROJECTION_MAX_SOURCE_BYTES, false):
		_failure = "%s CK projection source identity is invalid" % profile_id
		return false
	var source_bytes := _read_bytes(gallery_path.path_join(String(source.path)), "%s source" % profile_id)
	if source_bytes.is_empty() or int(source.bytes) != source_bytes.size() or source.sha256 != _sha256(source_bytes):
		_failure = "%s CK projection source identity does not match the gallery" % profile_id
		return false
	if typeof(source.document) != TYPE_STRING or String(source.document).is_empty() or typeof(source.namespace) != TYPE_STRING or String(source.namespace).is_empty():
		_failure = "%s CK projection source document identity is invalid" % profile_id
		return false
	if typeof(rust_inspection) != TYPE_DICTIONARY or not _exact_keys(rust_inspection, ["format", "operation", "stage", "status", "processing_complete", "diagnostics_complete", "diagnostics", "summary", "source"]):
		_failure = "%s CK projection Rust evidence has unexpected or missing fields" % profile_id
		return false
	if typeof(rust_inspection.format) != TYPE_STRING or typeof(rust_inspection.operation) != TYPE_STRING or typeof(rust_inspection.stage) != TYPE_STRING or typeof(rust_inspection.status) != TYPE_STRING or typeof(rust_inspection.processing_complete) != TYPE_BOOL or typeof(rust_inspection.diagnostics_complete) != TYPE_BOOL or rust_inspection.format != CK_PROJECTION_RUST_FORMAT or rust_inspection.operation != CK_PROJECTION_RUST_OPERATION or rust_inspection.stage != CK_PROJECTION_RUST_STAGE or rust_inspection.status != "success" or rust_inspection.processing_complete != true or rust_inspection.diagnostics_complete != true or rust_inspection.diagnostics != [] or typeof(rust_inspection.summary) != TYPE_DICTIONARY:
		_failure = "%s CK projection Rust evidence is not a bounded successful inspection" % profile_id
		return false
	var evidence_source = rust_inspection.source
	if typeof(evidence_source) != TYPE_DICTIONARY or not _exact_keys(evidence_source, ["dependencies", "document", "namespace"]) or evidence_source.document != source.document or evidence_source.namespace != source.namespace or typeof(evidence_source.dependencies) != TYPE_ARRAY or evidence_source.dependencies.size() > CK_PROJECTION_MAX_DEPENDENCIES:
		_failure = "%s CK projection Rust source evidence is invalid" % profile_id
		return false
	for dependency in evidence_source.dependencies:
		if typeof(dependency) != TYPE_DICTIONARY or not _exact_keys(dependency, ["document", "namespace", "content_sha256"]) or typeof(dependency.document) != TYPE_STRING or String(dependency.document).is_empty() or typeof(dependency.namespace) != TYPE_STRING or String(dependency.namespace).is_empty() or typeof(dependency.content_sha256) != TYPE_STRING or not String(dependency.content_sha256).begins_with("sha256:") or not _is_sha256(String(dependency.content_sha256).substr(7)):
			_failure = "%s CK projection Rust dependency evidence is invalid" % profile_id
			return false
	return true


func _validate_ck_projection_artifacts(artifacts, expected_artifacts, profile_id: String) -> bool:
	if typeof(artifacts) != TYPE_ARRAY or artifacts.size() != ARTIFACT_NAMES.size() or not _exact_json_value(artifacts, expected_artifacts):
		_failure = "%s CK projection artifacts do not exactly match the validated profile" % profile_id
		return false
	for index in range(ARTIFACT_NAMES.size()):
		var artifact = artifacts[index]
		if not _exact_keys(artifact, ["path", "sha256", "bytes"]) or artifact.path != "%s/%s" % [profile_id, ARTIFACT_NAMES[index]] or not _is_sha256(String(artifact.sha256)) or not _is_bounded_ck_projection_integer(artifact.bytes, CK_PROJECTION_MAX_SOURCE_BYTES, false):
			_failure = "%s CK projection artifact %d is invalid" % [profile_id, index]
			return false
	return true


func _validate_ck_projection_identity(identity: Dictionary, projection: Dictionary) -> bool:
	if not _validate_ck_projection_transport_identity_shape(identity):
		return false
	if not _exact_json_value(identity, projection.projection_identity):
		_failure = "CK projection transport identity does not match the embedded body identity"
		return false
	return true


func _validate_ck_projection_transport_identity_shape(identity) -> bool:
	if typeof(identity) != TYPE_DICTIONARY or not _exact_keys(identity, ["scope", "sha256", "bytes"]):
		_failure = "CK projection transport identity has unexpected or missing fields"
		return false
	if identity.scope != CK_PROJECTION_IDENTITY_SCOPE or not _is_sha256(String(identity.sha256)) or not _is_bounded_ck_projection_integer(identity.bytes, CK_PROJECTION_MAX_BYTES, false):
		_failure = "CK projection transport identity is invalid"
		return false
	return true


func _is_sha256(value: String) -> bool:
	if value.length() != 64:
		return false
	for index in range(value.length()):
		var code: int = value.unicode_at(index)
		if not ((code >= 48 and code <= 57) or (code >= 97 and code <= 102)):
			return false
	return true


func _is_bounded_ck_projection_integer(value, maximum: int, allow_zero: bool) -> bool:
	if typeof(value) != TYPE_INT and typeof(value) != TYPE_FLOAT:
		return false
	var numeric := float(value)
	if not is_finite(numeric) or numeric != floor(numeric):
		return false
	var integer := int(numeric)
	return integer >= (0 if allow_zero else 1) and integer <= maximum


func _exact_json_value(left, right) -> bool:
	if typeof(left) != typeof(right):
		return false
	if typeof(left) == TYPE_DICTIONARY:
		if left.size() != right.size():
			return false
		for key in left:
			if not right.has(key) or not _exact_json_value(left[key], right[key]):
				return false
		return true
	if typeof(left) == TYPE_ARRAY:
		if left.size() != right.size():
			return false
		for index in range(left.size()):
			if not _exact_json_value(left[index], right[index]):
				return false
		return true
	return left == right


func _validate_ck_projection_finite(value, depth: int = 0, state = null) -> bool:
	if depth > CK_PROJECTION_MAX_JSON_DEPTH:
		return false
	if state == null:
		state = [0]
	state[0] += 1
	if state[0] > CK_PROJECTION_MAX_JSON_NODES:
		return false
	match typeof(value):
		TYPE_FLOAT:
			return is_finite(value)
		TYPE_STRING:
			return value.length() <= CK_PROJECTION_MAX_STRING_LENGTH
		TYPE_ARRAY:
			for item in value:
				if not _validate_ck_projection_finite(item, depth + 1, state):
					return false
			return true
		TYPE_DICTIONARY:
			if value.size() > 2048:
				return false
			for key in value:
				if typeof(key) != TYPE_STRING or key.length() > CK_PROJECTION_MAX_STRING_LENGTH or not _validate_ck_projection_finite(value[key], depth + 1, state):
					return false
			return true
		TYPE_INT, TYPE_BOOL, TYPE_NIL:
			return true
		_:
			return false


func _projection_has_forbidden_field(value) -> bool:
	if typeof(value) == TYPE_DICTIONARY:
		for key in value:
			var normalized := String(key).to_lower().replace("-", "_")
			for token in ["adapter", "godot", "host", "package", "readiness"]:
				if normalized == token or normalized.begins_with(token + "_"):
					return true
			if _projection_has_forbidden_field(value[key]):
				return true
	elif typeof(value) == TYPE_ARRAY:
		for item in value:
			if _projection_has_forbidden_field(item):
				return true
	return false


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


func _load_semantic_pose_command(options: Dictionary, validated: Dictionary) -> Dictionary:
	var command = _parse_json_text(options.semantic_pose_command_json, "semantic pose command")
	if command.is_empty():
		return {}
	var command_identity = _parse_json_text(options.semantic_pose_command_identity_json, "semantic pose command identity")
	if command_identity.is_empty():
		return {}
	var semantic_payload = _parse_json_text(options.semantic_pose_payload_json, "semantic pose payload")
	if semantic_payload.is_empty():
		return {}
	var validated_command := _validate_semantic_pose_command(command, command_identity, semantic_payload, options, validated)
	if validated_command.is_empty():
		return {}
	options["semantic_pose_command"] = command
	options["semantic_pose_command_identity"] = command_identity
	options["semantic_pose_frame"] = command.identity_frame
	options["semantic_pose_command_selectors"] = validated_command.selectors
	return {"rules": validated_command.rules}


func _load_semantic_contact_command(options: Dictionary) -> Dictionary:
	var command := _parse_json_text(options.semantic_contact_command_json, "semantic contact command")
	if command.is_empty():
		return {}
	var command_identity := _parse_json_text(options.semantic_contact_command_identity_json, "semantic contact command identity")
	if command_identity.is_empty():
		return {}
	if not _validate_semantic_contact_command(command, options):
		return {}
	if not _validate_semantic_contact_identity(command, command_identity, options.semantic_contact_command_json):
		return {}
	# JSON.parse_string represents JSON numbers as floats.  Identity validation
	# above is against the canonical bytes; normalize the authored integer fields
	# only for exact report read-back after that validation succeeds.
	var normalized_command: Dictionary = command.duplicate(true)
	normalized_command.command_version = int(normalized_command.command_version)
	normalized_command.source_pose_command.command_version = int(normalized_command.source_pose_command.command_version)
	for participant in normalized_command.participants:
		participant.target_index = int(participant.target_index)
	var normalized_identity: Dictionary = command_identity.duplicate(true)
	normalized_identity.command_version = int(normalized_identity.command_version)
	options["semantic_contact_command"] = normalized_command
	options["semantic_contact_command_identity"] = normalized_identity
	return {"participants": normalized_command.participants}


func _validate_semantic_contact_command(command: Dictionary, options: Dictionary) -> bool:
	if not _exact_keys(command, ["schema", "boundary", "command_id", "command_version", "mapping_revision", "targets", "source_pose_command", "participants", "interaction"]):
		_failure = "semantic contact command has unexpected or missing fields"
		return false
	if command.schema != SEMANTIC_CONTACT_COMMAND_SCHEMA or command.boundary != SEMANTIC_CONTACT_COMMAND_BOUNDARY or command.command_id != SEMANTIC_CONTACT_COMMAND_ID or command.command_version != SEMANTIC_CONTACT_COMMAND_VERSION or command.mapping_revision != SEMANTIC_CONTACT_MAPPING_REVISION:
		_failure = "semantic contact command schema, boundary, version, or mapping revision is invalid"
		return false
	if not options.has("carrier_avatar_records") or not options.has("semantic_pose_command_identity") or not options.has("ck_projection"):
		_failure = "semantic contact command is missing its validated carrier, CK projection, or pose command"
		return false
	if typeof(command.targets) != TYPE_ARRAY or command.targets.size() != 2 or not _exact_json_value(command.targets, options.carrier_avatar_records):
		_failure = "semantic contact command targets are not the exact ordered carrier records"
		return false
	if not _exact_json_value(command.source_pose_command, options.semantic_pose_command_identity):
		_failure = "semantic contact command source pose identity does not match the supplied pose command"
		return false
	if not _exact_json_value(command.participants, CONTACT_PARTICIPANTS):
		_failure = "semantic contact command participants do not match the exact actuator/response selectors"
		return false
	if not _exact_json_value(command.interaction, CONTACT_INTERACTION):
		_failure = "semantic contact command interaction is not the exact press-release sequence"
		return false
	return true


func _validate_semantic_contact_identity(command: Dictionary, identity: Dictionary, command_json: String) -> bool:
	if not _exact_keys(identity, ["sha256", "byte_count_decimal", "schema", "boundary", "command_id", "command_version"]):
		_failure = "semantic contact command identity has unexpected or missing fields"
		return false
	var command_bytes := command_json.to_utf8_buffer()
	command_bytes.append(10)
	if identity.sha256 != _sha256(command_bytes) or not _is_canonical_command_byte_count(identity.byte_count_decimal) or int(identity.byte_count_decimal) != command_bytes.size() or identity.schema != command.schema or identity.boundary != command.boundary or identity.command_id != command.command_id or identity.command_version != command.command_version:
		_failure = "semantic contact command identity does not match the injected command"
		return false
	return true


func _parse_json_text(text: String, where: String) -> Dictionary:
	if text.is_empty() or text.ends_with("\n"):
		_failure = "%s is not the canonical injected JSON text" % where
		return {}
	var value = JSON.parse_string(text)
	if typeof(value) != TYPE_DICTIONARY:
		_failure = "%s is not a JSON object" % where
		return {}
	return value


func _exact_keys(value: Dictionary, keys: Array) -> bool:
	if value.size() != keys.size():
		return false
	for key in keys:
		if not value.has(key):
			return false
	return true


func _validate_semantic_pose_command(command: Dictionary, command_identity: Dictionary, semantic_payload: Dictionary, options: Dictionary, validated: Dictionary) -> Dictionary:
	if not _exact_keys(command, ["schema", "boundary", "command_id", "command_version", "source_pose", "targets", "rules", "identity_frame"]):
		_failure = "semantic pose command has unexpected or missing fields"
		return {}
	if command.schema != SEMANTIC_POSE_COMMAND_SCHEMA or command.boundary != SEMANTIC_POSE_COMMAND_BOUNDARY or command.command_id != SEMANTIC_POSE_COMMAND_ID or command.command_version != SEMANTIC_POSE_COMMAND_VERSION:
		_failure = "semantic pose command schema, boundary, or identity is invalid"
		return {}
	var source_pose = command.source_pose
	if typeof(source_pose) != TYPE_DICTIONARY or not _exact_keys(source_pose, ["format", "pose_id", "sha256", "version"]):
		_failure = "semantic pose command source-pose identity is incomplete"
		return {}
	if source_pose.format != POSE_FORMAT or source_pose.pose_id != String(validated.pose_id) or source_pose.sha256 != String(validated.pose_sha256) or source_pose.version != 1:
		_failure = "semantic pose command source-pose identity does not match the validated gallery"
		return {}
	var targets = command.targets
	if typeof(targets) != TYPE_ARRAY or targets.size() != 2 or not options.has("carrier_avatar_records"):
		_failure = "semantic pose command must target exactly two carrier-bound avatars"
		return {}
	var seen_targets := {}
	for index in range(2):
		var target = targets[index]
		if typeof(target) != TYPE_DICTIONARY or not _exact_keys(target, ["instance_id", "profile_id", "candidate_profile_sha256"]):
			_failure = "semantic pose command target %d is incomplete" % index
			return {}
		var instance_id := String(target.instance_id)
		if not _is_safe_instance_id(instance_id) or seen_targets.has(instance_id):
			_failure = "semantic pose command target instance identities are not unique"
			return {}
		seen_targets[instance_id] = true
		if target != options.carrier_avatar_records[index]:
			_failure = "semantic pose command targets are missing, reordered, or mismatched"
			return {}
	var rules = command.rules
	if typeof(rules) != TYPE_ARRAY or rules.size() != SEMANTIC_POSE_COMMAND_RULE_COUNT:
		_failure = "semantic pose command must contain exactly 18 semantic rules"
		return {}
	var normalized: Array[Dictionary] = []
	var selectors: Array[String] = []
	var selector_set := {}
	for index in range(SEMANTIC_POSE_COMMAND_RULE_COUNT):
		var rule = rules[index]
		var expected: Dictionary = POSE_RECIPE[index]
		if typeof(rule) != TYPE_DICTIONARY or not _exact_keys(rule, ["kind", "role", "anchors", "rotation_xyzw"]):
			_failure = "semantic pose command rule %d has unexpected or missing fields" % index
			return {}
		if rule.kind != expected.kind or rule.role != expected.role or rule.anchors != expected.anchors:
			_failure = "semantic pose command rule %d selector is reordered or mismatched" % index
			return {}
		var selector := _selector(String(rule.kind), rule.role, rule.anchors)
		if selector_set.has(selector):
			_failure = "semantic pose command contains duplicate semantic selectors"
			return {}
		selector_set[selector] = true
		var quaternion = _quaternion_from_command_rule(rule, expected, index)
		if quaternion == null:
			return {}
		selectors.append(selector)
		normalized.append({"selector": selector, "rotation": quaternion})
	if selector_set.size() != SEMANTIC_POSE_COMMAND_RULE_COUNT:
		_failure = "semantic pose command does not cover exactly 18 semantic selectors"
		return {}
	var frame = command.identity_frame
	if not _validate_identity_frame(frame):
		return {}
	if semantic_payload != {"rules": command.rules, "identity_frame": command.identity_frame}:
		_failure = "semantic pose payload does not match the injected command"
		return {}
	if not _validate_semantic_pose_identity(command, command_identity, options.semantic_pose_command_json):
		return {}
	return {"rules": normalized, "selectors": selectors}


func _quaternion_from_command_rule(rule: Dictionary, expected: Dictionary, index: int) -> Variant:
	var raw = rule.rotation_xyzw
	if typeof(raw) != TYPE_ARRAY or raw.size() != 4:
		_failure = "semantic pose command rule %d rotation is not a four-vector" % index
		return null
	var values: Array[float] = []
	for item in raw:
		if typeof(item) == TYPE_BOOL or not is_finite(float(item)):
			_failure = "semantic pose command rule %d rotation contains a non-finite value" % index
			return null
		values.append(float(item))
	var quaternion := Quaternion(values[0], values[1], values[2], values[3])
	if abs(quaternion.length() - 1.0) > POSE_QUATERNION_TOLERANCE:
		_failure = "semantic pose command rule %d rotation is not normalized" % index
		return null
	var axis: String = String(expected.axis)
	var angle := deg_to_rad(float(expected.angle))
	var expected_quaternion := Quaternion.IDENTITY if axis == "identity" else Quaternion(Vector3.RIGHT if axis == "x" else Vector3(0.0, 0.0, 1.0), angle)
	if _quaternion_error(quaternion, expected_quaternion) > POSE_QUATERNION_TOLERANCE:
		_failure = "semantic pose command rule %d rotation is not bound to the shared-pose recipe" % index
		return null
	return quaternion


func _validate_identity_frame(frame) -> bool:
	if typeof(frame) != TYPE_DICTIONARY or not _exact_keys(frame, ["vectors", "rotation_storage", "C", "s", "evidence_only", "runtime_conformance"]):
		_failure = "semantic pose command identity frame is incomplete or has extra fields"
		return false
	if frame.vectors != "column" or frame.rotation_storage != "xyzw":
		_failure = "semantic pose command frame does not declare column vectors and xyzw rotations"
		return false
	var matrix = frame.C
	if typeof(matrix) != TYPE_ARRAY or matrix.size() != 3:
		_failure = "semantic pose command frame C is not a 3x3 identity matrix"
		return false
	var identity := [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]
	for row_index in range(3):
		if typeof(matrix[row_index]) != TYPE_ARRAY or matrix[row_index].size() != 3:
			_failure = "semantic pose command frame C is not a 3x3 identity matrix"
			return false
		for column_index in range(3):
			if typeof(matrix[row_index][column_index]) == TYPE_BOOL or not is_finite(float(matrix[row_index][column_index])):
				_failure = "semantic pose command frame C contains a non-finite value"
				return false
	if matrix != identity or frame.s != 1.0 or typeof(frame.evidence_only) != TYPE_BOOL or frame.evidence_only != true or typeof(frame.runtime_conformance) != TYPE_BOOL or frame.runtime_conformance != false:
		_failure = "semantic pose command frame is not explicit trial-local identity evidence"
		return false
	return true


func _validate_semantic_pose_identity(command: Dictionary, identity: Dictionary, command_json: String) -> bool:
	if not _exact_keys(identity, ["sha256", "byte_count_decimal", "schema", "boundary", "command_id", "command_version"]):
		_failure = "semantic pose command identity evidence has unexpected or missing fields"
		return false
	var command_bytes := command_json.to_utf8_buffer()
	command_bytes.append(10)
	if identity.sha256 != _sha256(command_bytes) or not _is_canonical_command_byte_count(identity.byte_count_decimal) or int(identity.byte_count_decimal) != command_bytes.size() or identity.schema != command.schema or identity.boundary != command.boundary or identity.command_id != command.command_id or identity.command_version != command.command_version:
		_failure = "semantic pose command identity evidence does not match the injected command"
		return false
	return true


func _is_canonical_command_byte_count(value) -> bool:
	if typeof(value) != TYPE_STRING or value.is_empty() or value.length() > 6 or value.begins_with("0"):
		return false
	for index in range(value.length()):
		var code: int = value.unicode_at(index)
		if code < 48 or code > 57:
			return false
	var byte_count: int = value.to_int()
	return byte_count > 0 and byte_count <= 262144 and str(byte_count) == value


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
	var direct: float = max(abs(left.x - right.x), abs(left.y - right.y), abs(left.z - right.z), abs(left.w - right.w))
	var antipodal: float = max(abs(left.x + right.x), abs(left.y + right.y), abs(left.z + right.z), abs(left.w + right.w))
	return min(direct, antipodal)


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
	var posed_proxy_index_by_bone := {}
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
		posed_proxy_index_by_bone[bone_id] = index
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
		"posed_proxy_index_by_bone": posed_proxy_index_by_bone,
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


func _readback_binding(profile: Dictionary, validate_command_rotation: bool) -> Dictionary:
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
	var max_command_rotation_error := 0.0
	var max_command_rotation_error_selector := ""
	var runtime_pose_rule_readback: Array[Dictionary] = []
	for bone in profile.ordered_bones:
		var bone_id: String = String(bone.id)
		var bone_index: int = int(profile.bone_indices[bone_id])
		if not skeleton.has_bone_meta(bone_index, "ck_bone_id") or String(skeleton.get_bone_meta(bone_index, "ck_bone_id")) != bone_id:
			_failure = "%s runtime pose read-back bone identity is missing or mismatched" % profile.profile_id
			return {}
		var selector = _pose_selector_for_bone(bone, profile.profile_id)
		if selector == null:
			return {}
		if not pose_rotations.has(selector):
			_failure = "%s runtime pose rotation read-back is missing selector %s" % [profile.profile_id, selector]
			return {}
		var rest: Transform3D = skeleton.get_bone_rest(bone_index)
		var actual_local_pose: Transform3D = skeleton.get_bone_pose(bone_index)
		var expected_rotation: Quaternion = pose_rotations[selector]
		var expected_local_pose: Transform3D = rest * Transform3D(Basis(expected_rotation), Vector3.ZERO)
		var observed_rotation: Quaternion = (rest.affine_inverse() * actual_local_pose).basis.get_rotation_quaternion()
		var command_rotation_error := _quaternion_error(observed_rotation, expected_rotation)
		if command_rotation_error > max_command_rotation_error:
			max_command_rotation_error = command_rotation_error
			max_command_rotation_error_selector = selector
		var command_rotation_matches: bool = not validate_command_rotation or command_rotation_error <= RUNTIME_POSE_QUATERNION_TOLERANCE
		if _transform_error(actual_local_pose, expected_local_pose) <= TOLERANCE and command_rotation_matches:
			pose_rule_match_count += 1
		runtime_pose_rule_readback.append({
			"selector": selector,
			"runtime_bone_id": String(skeleton.get_bone_meta(bone_index, "ck_bone_id")),
			"observed_rotation_xyzw": _quaternion_json(observed_rotation),
			"max_component_error_to_command": command_rotation_error,
		})
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
		_failure = "%s runtime binding read-back does not satisfy the expected host-local evidence: pose=%d global=%d skin=%d proxy=%d max_command_rotation_error=%.12f selector=%s neutral_mesh=%s posed_mesh=%s" % [profile.profile_id, pose_rule_match_count, pose_global_match_count, skin_match_count, proxy_readback.matching_node_count, max_command_rotation_error, max_command_rotation_error_selector, neutral_compare.matches_published, posed_compare.matches_published]
		return {}
	profile["runtime_pose_rule_readback"] = runtime_pose_rule_readback
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


func _resolve_contact_proxy(profile: Dictionary, selector: Dictionary, participant_role: String, target_index: int) -> Dictionary:
	if typeof(selector) != TYPE_DICTIONARY or not _exact_keys(selector, ["kind", "role", "anchors"]):
		_failure = "%s contact selector is incomplete" % participant_role
		return {}
	if selector.kind != "joint" or typeof(selector.role) != TYPE_STRING or String(selector.role).is_empty() or typeof(selector.anchors) != TYPE_ARRAY:
		_failure = "%s contact selector is not a joint selector" % participant_role
		return {}
	var matching_bones: Array = []
	for bone in profile.ordered_bones:
		var joint = bone.get("joint", null)
		if typeof(joint) == TYPE_DICTIONARY and joint.get("kind", "") == selector.kind and joint.get("role", "") == selector.role and joint.get("anchors", []) == selector.anchors:
			matching_bones.append(bone)
	if matching_bones.size() != 1:
		_failure = "%s contact selector resolved to %d source joint bones; expected exactly one" % [participant_role, matching_bones.size()]
		return {}
	var bone: Dictionary = matching_bones[0]
	var bone_id := String(bone.get("id", ""))
	var posed_by_bone: Dictionary = profile.structural.posed_by_bone
	var proxy = posed_by_bone.get(bone_id, null)
	if typeof(proxy) != TYPE_DICTIONARY or proxy.get("bone_id", "") != bone_id or proxy.get("kind", "") != "capsule":
		_failure = "%s contact selector has no unique posed capsule for source bone %s" % [participant_role, bone_id]
		return {}
	if typeof(proxy.get("owned_part", null)) != TYPE_DICTIONARY or String(proxy.owned_part.get("role", "")).is_empty() or typeof(proxy.get("partition_rule", null)) != TYPE_STRING or typeof(proxy.get("radius_rule", null)) != TYPE_STRING:
		_failure = "%s contact proxy %s is missing owned-part lineage" % [participant_role, bone_id]
		return {}
	var proxy_nodes: Dictionary = profile.get("proxy_nodes", {})
	if not proxy_nodes.has(bone_id) or not (proxy_nodes[bone_id] is CollisionShape3D):
		_failure = "%s contact selector has no runtime posed proxy node for source bone %s" % [participant_role, bone_id]
		return {}
	var source_collision: CollisionShape3D = proxy_nodes[bone_id]
	var local_geometry := _read_proxy_geometry(source_collision, "%s contact source proxy %s" % [participant_role, bone_id])
	if local_geometry.is_empty() or not (source_collision.shape is CapsuleShape3D):
		_failure = "%s contact source proxy %s is not one valid capsule" % [participant_role, bone_id]
		return {}
	var expected_start: Vector3 = _vector3(proxy.a, "%s contact posed proxy a" % participant_role)
	var expected_end: Vector3 = _vector3(proxy.b, "%s contact posed proxy b" % participant_role)
	if expected_start == null or expected_end == null or (local_geometry.start as Vector3).distance_to(expected_start) > TOLERANCE or (local_geometry.end as Vector3).distance_to(expected_end) > TOLERANCE or abs(float(local_geometry.radius) - float(proxy.radius)) > TOLERANCE:
		_failure = "%s contact runtime proxy does not match the selected posed proxy" % participant_role
		return {}
	var posed_proxy_index_by_bone: Dictionary = profile.structural.get("posed_proxy_index_by_bone", {})
	var source_proxy_index := int(posed_proxy_index_by_bone.get(bone_id, -1))
	if source_proxy_index < 0:
		_failure = "%s contact source proxy index is unresolved" % participant_role
		return {}
	var report_proxy: Dictionary = proxy.duplicate(true)
	report_proxy.partition_vertex_count = int(report_proxy.partition_vertex_count)
	var source_body = source_collision.get_parent()
	if not (source_body is Node3D):
		_failure = "%s contact source proxy has no spatial parent" % participant_role
		return {}
	# _read_proxy_geometry already applies the CollisionShape3D transform and
	# returns coordinates in the source body's frame.  Applying the collision
	# transform again would move and rotate the selected capsule twice.
	var world_start: Vector3 = (source_body as Node3D).global_transform * (local_geometry.start as Vector3)
	var world_end: Vector3 = (source_body as Node3D).global_transform * (local_geometry.end as Vector3)
	if not _finite_vector3(world_start) or not _finite_vector3(world_end):
		_failure = "%s contact source proxy has non-finite world endpoints" % participant_role
		return {}
	return {
		"participant_role": participant_role,
		"target_index": target_index,
		"selector": selector.duplicate(true),
		"source_joint": bone.joint.duplicate(true),
		"source_bone_id": bone_id,
		"source_proxy_index": source_proxy_index,
		"source_collision": source_collision,
		"posed_proxy": report_proxy,
		"world_start": world_start,
		"world_end": world_end,
		"radius": float(local_geometry.radius),
	}


func _duplicate_contact_shape(source_collision: CollisionShape3D, body: Node3D, where: String) -> Dictionary:
	if not is_instance_valid(source_collision) or not (source_collision.shape is CapsuleShape3D):
		_failure = "%s source shape is not a valid capsule" % where
		return {}
	var duplicate_resource = source_collision.shape.duplicate()
	if not (duplicate_resource is CapsuleShape3D):
		_failure = "%s could not duplicate one capsule shape" % where
		return {}
	var collision := CollisionShape3D.new()
	collision.name = "SelectedCapsule"
	collision.shape = duplicate_resource
	collision.transform = Transform3D(source_collision.global_transform.basis, Vector3.ZERO)
	body.add_child(collision)
	if body.get_child_count() != 1 or not (collision.shape is CapsuleShape3D):
		_failure = "%s did not create exactly one duplicated capsule shape" % where
		return {}
	return {"collision": collision, "shape": collision.shape}


func _closest_points_on_segments(first_start: Vector3, first_end: Vector3, second_start: Vector3, second_end: Vector3, where: String) -> Dictionary:
	var first_axis := first_end - first_start
	var second_axis := second_end - second_start
	var offset := first_start - second_start
	var first_length_squared := first_axis.length_squared()
	var second_length_squared := second_axis.length_squared()
	if not _finite_vector3(first_axis) or not _finite_vector3(second_axis) or first_length_squared <= 1.0e-24 or second_length_squared <= 1.0e-24:
		_failure = "%s contains a degenerate capsule segment" % where
		return {}
	var dot_axes := first_axis.dot(second_axis)
	var dot_first_offset := first_axis.dot(offset)
	var dot_second_offset := second_axis.dot(offset)
	var denominator := first_length_squared * second_length_squared - dot_axes * dot_axes
	var first_fraction := 0.0
	var second_fraction := 0.0
	if abs(denominator) > 1.0e-24:
		first_fraction = clamp((dot_axes * dot_second_offset - dot_first_offset * second_length_squared) / denominator, 0.0, 1.0)
	var second_numerator := dot_axes * first_fraction + dot_second_offset
	if second_numerator < 0.0:
		second_fraction = 0.0
		first_fraction = clamp(-dot_first_offset / first_length_squared, 0.0, 1.0)
	elif second_numerator > second_length_squared:
		second_fraction = 1.0
		first_fraction = clamp((dot_axes - dot_first_offset) / first_length_squared, 0.0, 1.0)
	else:
		second_fraction = second_numerator / second_length_squared
	var first_point := first_start + first_axis * first_fraction
	var second_point := second_start + second_axis * second_fraction
	var separation := second_point - first_point
	var distance := separation.length()
	if not _finite_vector3(first_point) or not _finite_vector3(second_point) or not is_finite(distance):
		_failure = "%s closest-point calculation is non-finite" % where
		return {}
	return {"first": first_point, "second": second_point, "distance": distance}


func _finite_vector3(value: Vector3) -> bool:
	return is_finite(value.x) and is_finite(value.y) and is_finite(value.z)


func _contact_snapshot(body: RigidBody3D, label: String, tick: int) -> Dictionary:
	var transform: Transform3D = body.global_transform
	var linear_velocity: Vector3 = body.linear_velocity
	var angular_velocity: Vector3 = body.angular_velocity
	if not _finite_transform(transform) or not _finite_vector3(linear_velocity) or not _finite_vector3(angular_velocity):
		_failure = "%s response-body snapshot is non-finite" % label
		return {}
	return {
		"label": label,
		"tick": tick,
		"transform": _transform_json(transform),
		"position": _vector_json(transform.origin),
		"linear_velocity": _vector_json(linear_velocity),
		"angular_velocity": _vector_json(angular_velocity),
	}


func _finite_transform(value: Transform3D) -> bool:
	return _finite_vector3(value.basis.x) and _finite_vector3(value.basis.y) and _finite_vector3(value.basis.z) and _finite_vector3(value.origin)


func _contact_probe_failure(container: Node3D, message: String) -> Dictionary:
	if is_instance_valid(container):
		container.free()
	_failure = message
	return {}


func _run_contact_probe(profiles: Array[Dictionary], options: Dictionary) -> Dictionary:
	var command: Dictionary = options.semantic_contact_command
	var physics_engine := String(ProjectSettings.get_setting("physics/3d/physics_engine", ""))
	if physics_engine != "Jolt Physics":
		_failure = "semantic contact probe requires the explicit disposable Jolt Physics backend"
		return {}
	var participants: Array = command.participants
	var actuator_mapping := _resolve_contact_proxy(profiles[int(participants[0].target_index)], participants[0].selector, "actuator", int(participants[0].target_index))
	var response_mapping := _resolve_contact_proxy(profiles[int(participants[1].target_index)], participants[1].selector, "response", int(participants[1].target_index))
	if actuator_mapping.is_empty() or response_mapping.is_empty():
		return {}
	var actuator_start: Vector3 = (actuator_mapping.world_start + actuator_mapping.world_end) * 0.5
	var response_start: Vector3 = (response_mapping.world_start + response_mapping.world_end) * 0.5
	var initial_closest := _closest_points_on_segments(actuator_mapping.world_start, actuator_mapping.world_end, response_mapping.world_start, response_mapping.world_end, "semantic contact initial proxy geometry")
	if initial_closest.is_empty():
		return {}
	var combined_radius := float(actuator_mapping.radius) + float(response_mapping.radius)
	if float(initial_closest.distance) <= combined_radius + CONTACT_GEOMETRY_TOLERANCE:
		_failure = "semantic contact probe starts with penetrating or touching selected capsules"
		return {}
	var closest_vector: Vector3 = (initial_closest.second as Vector3) - (initial_closest.first as Vector3)
	var approach_direction: Vector3 = closest_vector / float(initial_closest.distance)
	var projected_gap := float(initial_closest.distance) - combined_radius
	if not is_finite(projected_gap) or projected_gap <= CONTACT_GEOMETRY_TOLERANCE:
		_failure = "semantic contact closest proxy points and radii do not define a positive approach gap"
		return {}
	var precontact_distance := projected_gap - CONTACT_OVERDRIVE
	if not is_finite(precontact_distance) or precontact_distance <= CONTACT_GEOMETRY_TOLERANCE:
		_failure = "semantic contact proxy approach gap is too small for a separated pre-contact phase"
		return {}
	var approach_distance := projected_gap + CONTACT_OVERDRIVE
	var contact_center := actuator_start + approach_direction * approach_distance
	var contact_press_distance := approach_distance + CONTACT_OVERDRIVE
	if not _finite_vector3(contact_center):
		_failure = "semantic contact target position is non-finite"
		return {}
	var contact_translation := approach_direction * approach_distance
	var contact_closest := _closest_points_on_segments(actuator_mapping.world_start + contact_translation, actuator_mapping.world_end + contact_translation, response_mapping.world_start, response_mapping.world_end, "semantic contact target proxy geometry")
	if contact_closest.is_empty():
		return {}
	if float(contact_closest.distance) >= combined_radius - CONTACT_GEOMETRY_TOLERANCE:
		_failure = "semantic contact target does not create a verified capsule overlap"
		return {}

	var contact_root := Node3D.new()
	contact_root.name = "SemanticContactProbe"
	get_root().add_child(contact_root)
	var actuator_body := AnimatableBody3D.new()
	actuator_body.name = "ContactActuator"
	actuator_body.sync_to_physics = true
	actuator_body.collision_layer = CONTACT_COLLISION_LAYER
	actuator_body.collision_mask = CONTACT_COLLISION_LAYER
	contact_root.add_child(actuator_body)
	actuator_body.global_position = actuator_start
	var actuator_shape := _duplicate_contact_shape(actuator_mapping.source_collision, actuator_body, "semantic contact actuator")
	if actuator_shape.is_empty():
		return _contact_probe_failure(contact_root, _failure)

	var response_body := ContactCaptureBody.new()
	response_body.name = "ContactResponse"
	response_body.contact_monitor = true
	response_body.max_contacts_reported = 8
	response_body.mass = 1.0
	response_body.gravity_scale = 0.0
	response_body.can_sleep = false
	response_body.axis_lock_angular_x = true
	response_body.axis_lock_angular_y = true
	response_body.axis_lock_angular_z = true
	response_body.collision_layer = CONTACT_COLLISION_LAYER
	response_body.collision_mask = CONTACT_COLLISION_LAYER
	contact_root.add_child(response_body)
	if not actuator_body.sync_to_physics or not response_body.axis_lock_angular_x or not response_body.axis_lock_angular_y or not response_body.axis_lock_angular_z:
		return _contact_probe_failure(contact_root, "semantic contact bodies did not retain the required synchronization and angular locks")
	response_body.global_position = response_start
	var response_shape := _duplicate_contact_shape(response_mapping.source_collision, response_body, "semantic contact response")
	if response_shape.is_empty():
		return _contact_probe_failure(contact_root, _failure)
	response_body.expected_collider_id = int(actuator_body.get_instance_id())
	response_body.linear_velocity = Vector3.ZERO
	response_body.angular_velocity = Vector3.ZERO

	response_body.probe_phase = "setup"
	response_body.probe_tick = 0
	await physics_frame
	if response_body.tick_evidence.is_empty():
		await physics_frame
	if response_body.tick_evidence.is_empty() or int(response_body.tick_evidence[0].tick) != 0:
		return _contact_probe_failure(contact_root, "semantic contact setup tick did not reach the rigid-body direct-state callback")
	var initial_response := _contact_snapshot(response_body, "initial", 0)
	if initial_response.is_empty():
		return _contact_probe_failure(contact_root, _failure)
	var schedule := [
		{"phase": "approach", "ticks": CONTACT_APPROACH_TICKS, "start_tick": 1, "end_tick": CONTACT_APPROACH_TICKS},
		{"phase": "contact", "ticks": CONTACT_HOLD_TICKS, "start_tick": CONTACT_APPROACH_TICKS + 1, "end_tick": CONTACT_APPROACH_TICKS + CONTACT_HOLD_TICKS},
		{"phase": "release", "ticks": CONTACT_RELEASE_TICKS, "start_tick": CONTACT_APPROACH_TICKS + CONTACT_HOLD_TICKS + 1, "end_tick": CONTACT_APPROACH_TICKS + CONTACT_HOLD_TICKS + CONTACT_RELEASE_TICKS},
		{"phase": "exit", "ticks": CONTACT_EXIT_TICKS, "start_tick": CONTACT_APPROACH_TICKS + CONTACT_HOLD_TICKS + CONTACT_RELEASE_TICKS + 1, "end_tick": CONTACT_APPROACH_TICKS + CONTACT_HOLD_TICKS + CONTACT_RELEASE_TICKS + CONTACT_EXIT_TICKS},
	]
	var tick := 0
	var contact_response := {}
	var contact_snapshots_by_tick: Dictionary = {}
	for phase_record in schedule:
		var phase: String = phase_record.phase
		var phase_ticks: int = int(phase_record.ticks)
		for phase_tick in range(phase_ticks):
			tick += 1
			response_body.probe_phase = phase
			response_body.probe_tick = tick
			if phase == "approach":
				actuator_body.global_position = actuator_start + approach_direction * precontact_distance * (float(phase_tick + 1) / float(phase_ticks))
			elif phase == "contact":
				actuator_body.global_position = actuator_start + approach_direction * lerp(approach_distance, contact_press_distance, float(phase_tick + 1) / float(phase_ticks))
			elif phase == "release":
				actuator_body.global_position = actuator_start + approach_direction * contact_press_distance * (1.0 - float(phase_tick + 1) / float(phase_ticks))
			else:
				actuator_body.global_position = actuator_start
			await physics_frame
			if phase == "contact" and _contact_tick_has_contact(response_body, tick):
				var contact_snapshot := _contact_snapshot(response_body, "contact", tick)
				if contact_snapshot.is_empty():
					return _contact_probe_failure(contact_root, _failure)
				contact_snapshots_by_tick[tick] = contact_snapshot
				if contact_response.is_empty():
					contact_response = contact_snapshot
	var final_response := _contact_snapshot(response_body, "final", tick)
	if final_response.is_empty():
		return _contact_probe_failure(contact_root, _failure)
	if response_body.tick_evidence.size() != tick + 1:
		return _contact_probe_failure(contact_root, "semantic contact probe did not record exactly one logical direct-state sample per declared tick (expected=%d observed=%d)" % [tick + 1, response_body.tick_evidence.size()])
	for expected_tick in range(tick + 1):
		if int(response_body.tick_evidence[expected_tick].tick) != expected_tick:
			return _contact_probe_failure(contact_root, "semantic contact probe direct-state tick sequence is incomplete or reordered")

	var attribution_valid := true
	var max_impulse := 0.0
	var strongest_sample := {}
	for sample in response_body.contact_samples:
		if int(sample.collider_id) != response_body.expected_collider_id or int(sample.collider_object_id) != response_body.expected_collider_id or int(sample.collider_shape_index) != 0 or int(sample.local_shape_index) != 0:
			attribution_valid = false
		var point: Variant = _vector3(sample.point, "semantic contact sample point")
		var normal: Variant = _vector3(sample.normal, "semantic contact sample normal")
		var impulse: Variant = _vector3(sample.impulse, "semantic contact sample impulse")
		if point == null or normal == null or impulse == null or not _finite_vector3(point as Vector3) or not _finite_vector3(normal as Vector3) or not _finite_vector3(impulse as Vector3) or (normal as Vector3).length() <= 1.0e-9:
			attribution_valid = false
			continue
		var impulse_length := (impulse as Vector3).length()
		if String(sample.phase) == "contact" and impulse_length > max_impulse:
			max_impulse = impulse_length
			strongest_sample = sample
	if not attribution_valid:
		return _contact_probe_failure(contact_root, "semantic contact sample collider or shape attribution is invalid")
	var contact_seen := false
	var exit_empty_seen := false
	var final_exit_contact_count := -1
	for tick_record in response_body.tick_evidence:
		if String(tick_record.phase) == "contact" and int(tick_record.contact_count) > 0:
			contact_seen = true
		if String(tick_record.phase) == "exit":
			final_exit_contact_count = int(tick_record.contact_count)
			if final_exit_contact_count == 0:
				exit_empty_seen = true
	if not contact_seen or contact_response.is_empty() or response_body.contact_samples.is_empty():
		return _contact_probe_failure(contact_root, "semantic contact probe did not establish a clean contact phase")
	if not exit_empty_seen or final_exit_contact_count != 0:
		return _contact_probe_failure(contact_root, "semantic contact probe did not establish a clean exit phase")
	if not strongest_sample.is_empty() and String(strongest_sample.phase) != "contact":
		return _contact_probe_failure(contact_root, "semantic contact strongest solver sample was outside the contact phase")
	if max_impulse <= CONTACT_MIN_IMPULSE:
		return _contact_probe_failure(contact_root, "semantic contact phase has no solver impulse above the declared floor")
	var strongest_tick := int(strongest_sample.tick)
	if not contact_snapshots_by_tick.has(strongest_tick):
		return _contact_probe_failure(contact_root, "semantic contact strongest solver sample has no same-tick response snapshot")
	contact_response = contact_snapshots_by_tick[strongest_tick]

	var initial_position: Variant = _vector3(initial_response.position, "semantic contact initial response position")
	var final_position: Variant = _vector3(final_response.position, "semantic contact final response position")
	var initial_velocity: Variant = _vector3(initial_response.linear_velocity, "semantic contact initial response velocity")
	var contact_velocity: Variant = _vector3(contact_response.linear_velocity, "semantic contact contact response velocity")
	var strongest_normal: Variant = _vector3(strongest_sample.normal, "semantic contact strongest sample normal")
	if initial_position == null or final_position == null or initial_velocity == null or contact_velocity == null or strongest_normal == null:
		return _contact_probe_failure(contact_root, _failure)
	var normal_direction := (strongest_normal as Vector3).normalized()
	var displacement: Vector3 = (final_position as Vector3) - (initial_position as Vector3)
	var velocity_delta: Vector3 = (contact_velocity as Vector3) - (initial_velocity as Vector3)
	var normal_velocity_delta: float = abs(velocity_delta.dot(normal_direction))
	var normal_displacement: float = abs(displacement.dot(normal_direction))
	if not is_finite(normal_velocity_delta) or normal_velocity_delta <= CONTACT_MIN_NORMAL_VELOCITY:
		return _contact_probe_failure(contact_root, "semantic contact response normal velocity delta is absent or below its declared floor")
	if not is_finite(normal_displacement) or normal_displacement <= CONTACT_MIN_NORMAL_DISPLACEMENT:
		return _contact_probe_failure(contact_root, "semantic contact response normal displacement is absent or below its declared floor")

	var result := {
		"mapping_revision": SEMANTIC_CONTACT_MAPPING_REVISION,
		"participants": [
			{
				"role": "actuator",
				"target_index": 0,
				"target": options.carrier_avatar_records[0],
				"selector": actuator_mapping.selector,
				"source_joint": actuator_mapping.source_joint,
				"source_bone_id": actuator_mapping.source_bone_id,
				"source_proxy_index": actuator_mapping.source_proxy_index,
				"posed_proxy": actuator_mapping.posed_proxy,
				"runtime_shape_index": 0,
			},
			{
				"role": "response",
				"target_index": 1,
				"target": options.carrier_avatar_records[1],
				"selector": response_mapping.selector,
				"source_joint": response_mapping.source_joint,
				"source_bone_id": response_mapping.source_bone_id,
				"source_proxy_index": response_mapping.source_proxy_index,
				"posed_proxy": response_mapping.posed_proxy,
				"runtime_shape_index": 0,
			},
		],
		"phase_tick_schedule": schedule,
		"approach_geometry": {
			"actuator_start_center": _vector_json(actuator_start),
			"response_start_center": _vector_json(response_start),
			"approach_direction": _vector_json(approach_direction),
			"initial_segment_distance": initial_closest.distance,
			"combined_radius": combined_radius,
			"projected_gap": projected_gap,
			"precontact_distance": precontact_distance,
			"approach_distance": approach_distance,
			"contact_press_distance": contact_press_distance,
		},
		"physics_configuration": {
			"physics_engine": physics_engine,
			"actuator_body": "AnimatableBody3D",
			"actuator_sync_to_physics": actuator_body.sync_to_physics,
			"response_body": "RigidBody3D",
			"response_mass": response_body.mass,
			"response_gravity_scale": response_body.gravity_scale,
			"response_can_sleep": response_body.can_sleep,
			"response_rotation_locked": response_body.axis_lock_angular_x and response_body.axis_lock_angular_y and response_body.axis_lock_angular_z,
			"response_contact_monitor": response_body.contact_monitor,
			"response_max_contacts_reported": response_body.max_contacts_reported,
			"one_shape_per_contact_body": actuator_body.get_child_count() == 1 and response_body.get_child_count() == 1,
		},
		"contact_tick_evidence": response_body.tick_evidence,
		"contact_samples": response_body.contact_samples,
		"initial_response": initial_response,
		"contact_response": contact_response,
		"final_response": final_response,
		"response_displacement": _vector_json(displacement),
		"response_displacement_length": displacement.length(),
		"contact_normal": _vector_json(normal_direction),
		"solver_impulse_magnitude": max_impulse,
		"normal_velocity_delta": normal_velocity_delta,
		"normal_displacement": normal_displacement,
		"clean_contact": contact_seen,
		"clean_exit": exit_empty_seen and final_exit_contact_count == 0,
		"solver_response": max_impulse > CONTACT_MIN_IMPULSE and normal_velocity_delta > CONTACT_MIN_NORMAL_VELOCITY and normal_displacement > CONTACT_MIN_NORMAL_DISPLACEMENT,
	}
	contact_root.free()
	return result


func _contact_tick_has_contact(response_body: ContactCaptureBody, tick: int) -> bool:
	for tick_record in response_body.tick_evidence:
		if int(tick_record.tick) == tick and int(tick_record.contact_count) > 0:
			return true
	return false


func _readback_semantic_pose_injection(profile: Dictionary, index: int, binding: Dictionary, carrier_binding: Dictionary, options: Dictionary) -> Dictionary:
	var rule_readback = profile.get("runtime_pose_rule_readback", [])
	if typeof(rule_readback) != TYPE_ARRAY or rule_readback.size() != SEMANTIC_POSE_COMMAND_RULE_COUNT:
		_failure = "%s semantic pose runtime rule read-back is incomplete" % profile.profile_id
		return {}
	var readback_by_selector := {}
	for record in rule_readback:
		if typeof(record) != TYPE_DICTIONARY:
			_failure = "%s semantic pose runtime rule read-back is malformed" % profile.profile_id
			return {}
		var selector := String(record.get("selector", ""))
		if selector.is_empty() or readback_by_selector.has(selector):
			_failure = "%s semantic pose runtime rule read-back has a missing or duplicate selector" % profile.profile_id
			return {}
		readback_by_selector[selector] = record
	var ordered_readback: Array[Dictionary] = []
	for selector in options.semantic_pose_command_selectors:
		if not readback_by_selector.has(selector):
			_failure = "%s semantic pose selector read-back is incomplete" % profile.profile_id
			return {}
		ordered_readback.append(readback_by_selector[selector])
	var target := {
		"instance_id": carrier_binding.get("instance_id", ""),
		"profile_id": carrier_binding.get("profile_id", ""),
		"candidate_profile_sha256": carrier_binding.get("candidate_profile_sha256", ""),
	}
	var applied: bool = (
		target == options.semantic_pose_command.targets[index]
		and ordered_readback.size() == SEMANTIC_POSE_COMMAND_RULE_COUNT
		and int(binding.pose_rules_applied) == SEMANTIC_POSE_COMMAND_RULE_COUNT
		and int(binding.pose_global_matrices_match) == SEMANTIC_POSE_COMMAND_RULE_COUNT
		and int(binding.skin_matrices_match) == SEMANTIC_POSE_COMMAND_RULE_COUNT
	)
	if not applied:
		_failure = "%s semantic pose command did not produce complete runtime read-back" % profile.profile_id
		return {}
	return {
		"target": target,
		"rule_readback": ordered_readback,
		"rules_observed": ordered_readback.size(),
		"local_pose_matches_command": int(binding.pose_rules_applied),
		"global_pose_matches_published": int(binding.pose_global_matrices_match),
		"skin_matrices_match_published": int(binding.skin_matrices_match),
		"applied": applied,
	}


func _build_report(options: Dictionary, validated: Dictionary, loaded_profiles: Array[Dictionary]) -> Dictionary:
	var candidate_hashes := {}
	var profiles: Array[Dictionary] = []
	var carrier_avatar_bindings: Array[Dictionary] = []
	var profile_translations: Array = []
	var pose_rule_count := -1
	var pose_rules_validated := true
	var contact_mode: bool = options.has("semantic_contact_command")
	for index in range(loaded_profiles.size()):
		var profile: Dictionary = loaded_profiles[index]
		candidate_hashes[profile.profile_id] = profile.candidate_profile_sha256
		var metrics: Dictionary = profile.metrics
		var binding := _readback_binding(profile, options.has("semantic_pose_command"))
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
		var carrier_binding := {}
		if options.has("carrier_identity"):
			carrier_binding = _readback_carrier_avatar_binding(profile, index, options.carrier_avatar_records[index])
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
		var profile_report := {
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
		}
		if options.has("ck_projection"):
			var projection_avatar: Dictionary = options.ck_projection_avatars[index]
			profile_report["ck_projection_binding"] = {
				"instance_id": projection_avatar.instance_id,
				"profile_id": projection_avatar.profile_id,
				"candidate_profile_sha256": projection_avatar.candidate_profile_sha256,
				"source": projection_avatar.source,
				"artifacts": projection_avatar.artifacts,
			}
		if options.has("semantic_pose_command"):
			var injection := _readback_semantic_pose_injection(profile, index, binding, carrier_binding, options)
			if injection.is_empty():
				return {}
			profile_report["semantic_pose_injection"] = injection
		profiles.append(profile_report)
	if pose_rule_count < 0 or not pose_rules_validated:
		_failure = "runtime shared-pose evidence is incomplete"
		return {}
	var claims: Array[String] = ["host-local Skeleton3D/Skin pose binding", "host-local consumption of the shared structural pose recipe"]
	if contact_mode:
		claims.append("experiment-local semantic proxy contact and rigid-body response")
	var report_boundary := CONTACT_REPORT_BOUNDARY if contact_mode else REPORT_BOUNDARY
	var report := {
		"schema": REPORT_SCHEMA,
		"status": "success",
		"boundary": report_boundary,
		"claims": claims,
		"scope_flags": {
			"physics_stepping": contact_mode,
			"animation": false,
			"contact": contact_mode,
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
			"scope": report_boundary,
			"profile_translations": profile_translations,
		},
		"pose_binding": {
			"pose_id": validated.pose_id,
			"pose_sha256": validated.pose_sha256,
			"path": "injected-semantic-pose-command" if options.has("semantic_pose_command") else POSE_FILE,
			"rule_count": pose_rule_count,
			"rules_validated": pose_rules_validated,
			"applied_to_skeleton3d": pose_rule_count == BONE_COUNT,
			"ik": false,
			"contact": contact_mode,
		},
		"profiles": profiles,
	}
	if options.has("carrier_identity"):
		report["validated_carrier"] = options.carrier_identity
		report["carrier_avatar_bindings"] = carrier_avatar_bindings
	if options.has("ck_projection_identity"):
		report["validated_ck_projection"] = options.ck_projection_identity
	if options.has("semantic_pose_command"):
		report["semantic_pose_command_identity"] = options.semantic_pose_command_identity
		report["semantic_pose_targets"] = options.semantic_pose_command.targets
		report["semantic_pose_frame"] = options.semantic_pose_frame
	if contact_mode:
		var contact_probe: Dictionary = options.get("semantic_contact_probe", {})
		if contact_probe.is_empty():
			_failure = "semantic contact report evidence is missing"
			return {}
		var selector_mappings: Array[Dictionary] = []
		for participant in contact_probe.participants:
			selector_mappings.append({
				"role": participant.role,
				"target_index": participant.target_index,
				"selector": participant.selector,
				"bone_id": participant.source_bone_id,
				"proxy_id": participant.source_bone_id,
				"owned_part": participant.posed_proxy.owned_part,
				"shape_index": participant.source_proxy_index,
				"runtime_shape_index": participant.runtime_shape_index,
			})
		var solver_impulses := [{
			"runtime_derived": true,
			"target_indices": [0, 1],
			"shape_indices": [contact_probe.participants[0].source_proxy_index, contact_probe.participants[1].source_proxy_index],
			"impulse_magnitude": contact_probe.solver_impulse_magnitude,
			"contact_samples": contact_probe.contact_samples,
		}]
		var initial_response: Dictionary = contact_probe.initial_response
		var contact_response: Dictionary = contact_probe.contact_response
		var final_response: Dictionary = contact_probe.final_response
		report["semantic_contact"] = {
			"command_identity": options.semantic_contact_command_identity,
			"targets": options.semantic_contact_command.targets,
			"source_pose_command": options.semantic_contact_command.source_pose_command,
			"mapping_revision": contact_probe.mapping_revision,
			"participants": contact_probe.participants,
			"interaction": options.semantic_contact_command.interaction,
			"selector_mappings": selector_mappings,
			"phase_order": CONTACT_PHASE_ORDER,
			"phase_ticks": contact_probe.phase_tick_schedule,
			"max_ticks": CONTACT_MAX_TICKS,
			"contact_tick_evidence": contact_probe.contact_tick_evidence,
			"physics_configuration": contact_probe.physics_configuration,
			"solver_impulses": solver_impulses,
			"response": {
				"target_index": 1,
				"shape_index": contact_probe.participants[1].source_proxy_index,
				"normal": contact_probe.contact_normal,
				"snapshots": {
					"initial": initial_response,
					"contact": contact_response,
					"final": final_response,
				},
				"normal_velocity_delta": contact_probe.normal_velocity_delta,
				"normal_displacement": contact_probe.normal_displacement,
				"displacement": contact_probe.response_displacement_length,
			},
		}
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


func _transform_json(value: Transform3D) -> Array[float]:
	return [
		value.basis.x.x, value.basis.y.x, value.basis.z.x, value.origin.x,
		value.basis.x.y, value.basis.y.y, value.basis.z.y, value.origin.y,
		value.basis.x.z, value.basis.y.z, value.basis.z.z, value.origin.z,
		0.0, 0.0, 0.0, 1.0,
	]


func _quaternion_json(value: Quaternion) -> Array[float]:
	return [value.x, value.y, value.z, value.w]


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
