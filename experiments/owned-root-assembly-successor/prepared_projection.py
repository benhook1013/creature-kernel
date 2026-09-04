"""Closed section-2 source admission and standard-neutral projection."""
import json
import math
from functools import wraps
from pathlib import Path
from types import MappingProxyType

import artifact_serialization as artifacts


class PreparedProjectionError(ValueError):
    """A source, profile, or prepared-input boundary failed closed."""
ROOT = Path(__file__).resolve().parents[2]
CONTRACT_ROLE = "experiments/owned-root-assembly-successor/design-contract.md"
SOURCE_ROLE = "examples/body-documents/stylized-digitigrade-biped-authored-form.json"
PROFILE_ROLE = "experiments/current-form-surface-preview/structural_profile_candidates.json"
CONTRACT_PATH = ROOT / CONTRACT_ROLE
SIDECAR_PATH = ROOT / "experiments/owned-root-assembly-successor/design-contract.sha256"
SOURCE_PATH, PROFILE_TABLE_PATH = ROOT / SOURCE_ROLE, ROOT / PROFILE_ROLE
EXPECTED_CONTRACT_SHA256 = "3122f0db2235754ed782bd38a88c4d7ad7cc7edbf635d147194f1e93f8556490"
EXPECTED_SOURCE_SHA256 = "82269e843555ff1aad3c66399e3fcaeb11bbee81d72b69d15765ea9c4e7aff14"
EXPECTED_PROFILE_TABLE_SHA256 = "a5fba6643d0031bac83c08e9093e11fd7945806963509fa939865866112d9640"
EXPECTED_BINDING_COMPONENTS_SHA256 = "58c7ba6d4fd20135f9e93bc8b92690102287f11ae6092b9f3b82459e59375a5f"
EXPECTED_BINDINGS_SHA256 = "57ce3638fd31cca47294d8c9ddf142d783b527b18be431a5501fccda1085bc12"
EXPECTED_SOURCE_BYTES, EXPECTED_PROFILE_BYTES = 56984, 29970
# Definition-time immutable admission commitments. Public constants remain
# inspectable, but their ordinary reassignment cannot redirect admission.
_ADMISSION = ((CONTRACT_ROLE, SOURCE_ROLE, PROFILE_ROLE),
    (CONTRACT_PATH, SIDECAR_PATH, SOURCE_PATH, PROFILE_TABLE_PATH),
    (EXPECTED_CONTRACT_SHA256, EXPECTED_SOURCE_SHA256, EXPECTED_PROFILE_TABLE_SHA256),
    (173184, 127, EXPECTED_SOURCE_BYTES, EXPECTED_PROFILE_BYTES),
    (EXPECTED_BINDING_COMPONENTS_SHA256, EXPECTED_BINDINGS_SHA256))
_ROLES, _PATHS, _HASHES, _SIZES, _BINDING_HASHES = _ADMISSION
(_JSON_BYTES, _DECODE_JSON, _COERCE_BINARY64, _READ_FILE, _SHA256_BYTES) = (
    artifacts.canonical_json_bytes, artifacts.decode_canonical_json,
    artifacts.coerce_binary64, artifacts.read_regular_file, artifacts.sha256_bytes)
_SIDECAR_CONTENT = artifacts.contract_sidecar_bytes(_HASHES[0])
_PREPARED_SCHEMA = "owned-root-assembly-successor-prepared.v1"
_NEUTRAL_PROFILE = "standard_neutral_reference"
_ROTATION = (0.0, 0.0, 0.0, 1.0)
_AXES = ("x", "y", "z")
_BASIS_ITEMS = (("length_unit", "metre"), ("handedness", "right"), ("up", "+y"), ("forward", "+z"))
_SOURCE_DOCUMENT = "stylized_digitigrade_biped_authored_form"
_SOURCE_CONTRACT = (("family", "creature-kernel.body"), ("revision", 1))
_SOURCE_IDENTITY = (("document", _SOURCE_DOCUMENT), ("namespace", "main"))
PARTS = (("pelvis", None), ("torso", None), ("neck", None), ("upper_arm", "left"), ("upper_arm", "right"), ("thigh", "left"), ("thigh", "right"))
STATIONS = (("lower_pelvis", "pelvis", "form_torso_profile_lower_pelvis"), ("upper_pelvis", "pelvis", "form_torso_profile_upper_pelvis"),
    ("lower_abdomen", "torso", "form_torso_profile_lower_abdomen"), ("waist_abdomen", "torso", "form_torso_profile_waist_abdomen"),
    ("upper_abdomen", "torso", "form_torso_profile_upper_abdomen"), ("lower_ribcage", "torso", "form_torso_profile_lower_ribcage"),
    ("upper_ribcage_shoulder", "torso", "form_torso_profile_upper_ribcage_shoulder"), ("neck_collar", "neck", "form_head_neck_profile_neck_collar"),
    ("neck_upper", "neck", "form_head_neck_profile_neck_upper"))
SHOULDER_DIMS = (("start_lateral", "form_arm_profile_upper_arm_start_lateral_radius"), ("start_up", "form_arm_profile_upper_arm_start_up_radius"),
    ("start_forward", "form_arm_profile_upper_arm_start_forward_radius"), ("shoulder_depth", "form_shoulder_depth_radius"))
HIP_DIMS = (("r_x", "form_leg_profile_thigh_start_lateral_radius"), ("r_y", "form_leg_profile_thigh_start_up_radius"), ("r_z", "form_leg_profile_thigh_start_forward_radius"))
SHOULDER_SUMS = (("axilla", "form_axilla"), ("peak", "form_shoulder_peak"), ("arm_origin", None))
HIP_SUMS = (("P_s", "form_leg_profile_thigh_start"),)
SIDE_CONFIGS = (("shoulders", "upper_arm", (("axilla", "form_axilla", "form_shoulder_control"), ("peak", "form_shoulder_peak", "form_shoulder_control")), SHOULDER_DIMS),
    ("hips", "thigh", (("P_s", "form_leg_profile_thigh_start", "form_leg_profile_control"),), HIP_DIMS))
BODY_COUNTS = {"attachments": 1, "capabilities": 3, "dimensions": 153, "fields": 0, "frames": 16, "joints": 17, "landmarks": 43, "modules": 1, "parts": 18, "regions": 4, "sockets": 2}
SOURCE_ROW_FIELDS = {"dimensions": {"owner", "role", "value"}, "frames": {"owner", "role", "transform"}, "landmarks": {"frame", "owner", "position", "role"}}
PROFILE_IDS = ("standard_neutral_reference", "compact_broad_short_limb_large_head", "tall_narrow_long_legged", "slender_long_limb", "stocky_broad_chested")
PROFILE_DIMENSION_KEYS = frozenset("""arm_profile_forward arm_profile_lateral arm_profile_up arm_radius arm_shoulder body_extent_x body_extent_y body_extent_z body_profile_depth body_profile_lateral foot_extent_x foot_extent_y foot_extent_z foot_profile_forward foot_profile_lateral foot_profile_up hand_extent_x hand_extent_y hand_extent_z head_extent_x head_extent_y head_extent_z head_profile_forward head_profile_lateral head_profile_up leg_profile_forward leg_profile_lateral leg_profile_up leg_radius neck_profile_forward neck_profile_lateral neck_profile_up neck_radius tail_root_end tail_root_start tail_tip_end tail_tip_start""".split())  # noqa: SIM905
_ADDRESS, _B64, _PB64 = object(), ("binary64", False), ("binary64", True)
_IDENTITY_SPEC = {"path": str, "sha256": str}
_PART_SPEC = {"address": _ADDRESS, "placement": {
    "translation": ("vector", 3), "rotation_xyzw": ("vector", 4)}}
_STATION_SPEC = {"owner": _ADDRESS, "prefix": str, "C": ("vector", 3), "rL": _PB64, "rA": _PB64, "rP": _PB64}
_SHOULDER_SPEC = {field: _PB64 for field, _ in SHOULDER_DIMS}
_SHOULDER_SPEC.update({field: ("vector", 3) for field in ("axilla", "peak", "arm_origin")})
_HIP_SPEC = {"P_s": ("vector", 3), **{field: _PB64 for field, _ in HIP_DIMS}}
_PREPARED_SPEC = {
    "schema": str, "contract": _IDENTITY_SPEC, "source": _IDENTITY_SPEC,
    "profile_selection": {"profile_id": str, "profile_table_path": str, "profile_table_sha256": str,
                          "dimensions": {key: _B64 for key in PROFILE_DIMENSION_KEYS}},
    "basis": {key: str for key, _ in _BASIS_ITEMS},
    "parts": ("list", len(PARTS), _PART_SPEC),
    "stations": {name: _STATION_SPEC for name, _, _ in STATIONS},
    "shoulders": {side: _SHOULDER_SPEC for side in ("left", "right")},
    "hips": {side: _HIP_SPEC for side in ("left", "right")},
    "provenance": {"source_files": ("list", 2, {"path": str, "sha256": str, "bytes": int})},
}
def _freeze(value):
    if type(value) is dict: return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if type(value) is set: return frozenset(value)
    if type(value) is tuple: return tuple(_freeze(item) for item in value)
    return value
_COMMITMENTS = _freeze({
    "admission": {"roles": _ROLES, "paths": _PATHS, "hashes": _HASHES, "sizes": _SIZES, "binding_hashes": _BINDING_HASHES, "sidecar": _SIDECAR_CONTENT},
    "semantic": {"schema": _PREPARED_SCHEMA, "neutral_profile": _NEUTRAL_PROFILE, "rotation": _ROTATION, "axes": _AXES, "basis": _BASIS_ITEMS, "source_document": _SOURCE_DOCUMENT, "source_contract": _SOURCE_CONTRACT,
                 "source_identity": _SOURCE_IDENTITY, "parts": PARTS, "stations": STATIONS, "shoulder_dims": SHOULDER_DIMS, "hip_dims": HIP_DIMS, "shoulder_sums": SHOULDER_SUMS, "hip_sums": HIP_SUMS,
                 "side_configs": SIDE_CONFIGS, "body_counts": BODY_COUNTS, "source_row_fields": SOURCE_ROW_FIELDS, "profile_ids": PROFILE_IDS, "profile_dimension_keys": PROFILE_DIMENSION_KEYS, "address_marker": _ADDRESS},
    "prepared_spec": _PREPARED_SPEC,
    "operations": {"json_bytes": _JSON_BYTES, "decode_json": _DECODE_JSON, "coerce_binary64": _COERCE_BINARY64, "read_file": _READ_FILE, "sha256_bytes": _SHA256_BYTES, "serialization_error": artifacts.ArtifactSerializationError,
                   "loads": json.loads, "source_json_errors": (UnicodeDecodeError, json.JSONDecodeError, RecursionError, TypeError, ValueError), "isfinite": math.isfinite, "path_type": Path, "error": PreparedProjectionError},
})
def _public_admission(function, _error=_COMMITMENTS["operations"]["error"]):
    @wraps(function)
    def guarded(*args, **kwargs):
        try: return function(*args, **kwargs)
        except _error: raise
        except Exception as exc: raise _error(f"{function.__name__}: malformed admission") from exc
    return guarded
def _need(test, where, message, _error=_COMMITMENTS["operations"]["error"]):
    if not test: raise _error(f"{where}: {message}")
def _obj(value, where):
    _need(type(value) is dict, where, "expected object")
    return value
def _keys(value, expected, where):
    _obj(value, where)
    _need(all(type(key) is str for key in value) and set(value) == set(expected), where, "unknown, missing, or non-string field")
    return value
def _text(value, where, nonempty=True):
    _need(type(value) is str and (value or not nonempty), where, "expected string")
    return value
def _literal(value, expected, where): _need(type(value) is type(expected) and value == expected, where, "wrong value")
def _attempt(function, args, caught, where, message, kwargs=None, _error=_COMMITMENTS["operations"]["error"]):
    try: return function(*args, **(kwargs or {}))
    except caught as exc: raise _error(f"{where}: {message}") from exc
def _number(value, where, *, runtime=False, positive=False, wire=False, _c=_COMMITMENTS):
    operations = _c["operations"]
    if wire:
        result = _attempt(operations["coerce_binary64"], (value,), operations["serialization_error"],
                          where, "invalid canonical binary64", {"label": where})
    elif runtime:
        _need(type(value) is float, where, "expected runtime binary64 float")
        result = value
    else:
        _need(type(value) in (int, float), where, "expected finite number")
        result = _attempt(float, (value,), (OverflowError, ValueError), where, "expected finite number")
    label = "positive " if positive else ""
    _need(operations["isfinite"](result) and (not positive or result > 0.0), where, f"expected finite {label}number")
    return result
def _vector(value, where, length=3, *, runtime=False, wire=False):
    _need(type(value) is list and len(value) == length, where, f"expected {length}-vector")
    return [_number(item, f"{where}[{i}]", runtime=runtime, wire=wire) for i, item in enumerate(value)]
def _pairs(items):
    result = dict(items)
    if len(result) != len(items): raise ValueError("duplicate JSON key")
    return result
def _constant(token): raise ValueError(f"non-finite JSON constant {token}")
def _decode_source_json(raw, where, _c=_COMMITMENTS):
    _need(type(raw) is bytes, where, "expected raw bytes")
    operations, caught = _c["operations"], _c["operations"]["source_json_errors"]
    text = _attempt(raw.decode, ("utf-8",), caught, where, "source is not strict UTF-8 JSON")
    value = _attempt(operations["loads"], (text,), caught, where, "source is not strict UTF-8 JSON", {"object_pairs_hook": _pairs, "parse_constant": _constant})
    return _obj(value, where), operations["sha256_bytes"](raw)
def _read(path, where, _reader=_COMMITMENTS["operations"]["read_file"]): return _attempt(_reader, (path,), (OSError, TypeError, ValueError), where, "read failed")
def _fixed_path(path, expected, where, _path_type=_COMMITMENTS["operations"]["path_type"]):
    candidate = _attempt(_path_type, (path,), (TypeError, ValueError), where, "invalid path").absolute()
    _need(candidate == expected, where, "path is not the fixed canonical path")
    _need(not candidate.is_symlink() and candidate.is_file(), where, "expected regular file")
    return candidate
@_public_admission
def normalize_source_address(raw):
    value = _keys(raw, {"namespace", "anchors", "kind", "role"}, "source address")
    for key in ("namespace", "kind", "role"): _text(value[key], f"source address.{key}")
    anchors = value["anchors"]
    _need(type(anchors) is list and all(type(item) is str for item in anchors), "source anchors", "invalid array")
    return [value["namespace"], list(anchors), value["kind"], value["role"]]
def _address(raw, _normalize=normalize_source_address):
    value = _normalize(raw)
    return value[0], tuple(value[1]), value[2], value[3]
def _runtime_address(value, where):
    _need(type(value) is list and len(value) == 4, where, "expected normalized address")
    namespace, anchors, kind, role = value
    _text(namespace, f"{where}[0]")
    _need(type(anchors) is list and all(type(item) is str for item in anchors), f"{where}[1]", "invalid anchors")
    _text(kind, f"{where}[2]"); _text(role, f"{where}[3]")
    return namespace, tuple(anchors), kind, role
def _a(role, side=None): return "main", () if side is None else (side,), "part", role
def _address_json(value): return [value[0], list(value[1]), value[2], value[3]]
def _add(left, right): return [left[index] + right[index] for index in range(3)]
def _source_transform(raw, where, *, zero_translation=False, _rotation=_COMMITMENTS["semantic"]["rotation"]):
    transform = _keys(raw, {"translation", "rotation_xyzw"}, where)
    translation = _vector(transform["translation"], f"{where}.translation"); rotation = _vector(transform["rotation_xyzw"], f"{where}.rotation_xyzw", 4)
    _need(tuple(rotation) == _rotation, where, "rotation must be exact identity"); _need(not zero_translation or translation == [0.0, 0.0, 0.0], where, "frame translation must be zero")
    return translation
def _validate_selector_rows(rows, name, _fields=_COMMITMENTS["semantic"]["source_row_fields"]):
    selectors, frame_references = {}, set()
    for index, raw in enumerate(rows):
        where = f"body.{name}[{index}]"; row = _keys(raw, _fields[name], where)
        owner = _address(row["owner"]); role = _text(row["role"], f"{where}.role")
        _need((owner, role) not in selectors, where, "duplicate selector")
        selectors[owner, role] = row, index
        if name == "dimensions": _number(row["value"], f"{where}.value", positive=True)
        elif name == "frames": _source_transform(row["transform"], f"{where}.transform", zero_translation=True)
        else:
            frame = _keys(row["frame"], {"owner", "role"}, f"{where}.frame")
            frame_owner = _address(frame["owner"])
            frame_role = _text(frame["role"], f"{where}.frame.role"); _need(frame_owner == owner, f"{where}.frame", "wrong frame owner")
            frame_references.add((frame_owner, frame_role)); _vector(row["position"], f"{where}.position")
    return selectors, frame_references
def _fixed_scalars(value, items, where):
    record = _keys(value, {key for key, _ in items}, where)
    for key, expected in items:
        _literal(record[key], expected, f"{where}.{key}")
def _validate_source_document(source, _semantic=_COMMITMENTS["semantic"]):
    _keys(source, {"contract", "source", "basis", "profiles", "body", "extensions"}, "source")
    _fixed_scalars(source["contract"], _semantic["source_contract"], "source.contract")
    identity = _obj(source["source"], "source.source")
    _keys(identity, {"document", "namespace", "dependencies"}, "source.source")
    for key, expected in _semantic["source_identity"]:
        _literal(identity[key], expected, f"source.source.{key}")
    _need(type(identity["dependencies"]) is list and not identity["dependencies"], "source.dependencies", "not empty")
    _fixed_scalars(source["basis"], _semantic["basis"], "source.basis")
    _fixed_scalars(source["profiles"], (("semantic_numeric", "ck.numeric-frame.r1"),), "source.profiles")
    _need(type(source["extensions"]) is list and not source["extensions"], "source.extensions", "not empty")
    body = _obj(source["body"], "source.body")
    _keys(body, _semantic["body_counts"], "source.body")
    valid_counts = all(type(body[name]) is list and len(body[name]) == count for name, count in _semantic["body_counts"].items())
    _need(valid_counts, "source.body", "wrong required record counts")
    parts = {}
    for index, raw in enumerate(body["parts"]):
        where = f"body.parts[{index}]"; row = _keys(raw, {"address", "containment", "placement"}, where)
        address = _address(row["address"]); _need(address not in parts, where, "duplicate part address")
        _source_transform(row["placement"], f"{where}.placement")
        _obj(row["containment"], f"{where}.containment")
        parts[address] = row, index
    dimensions, _ = _validate_selector_rows(body["dimensions"], "dimensions"); frames, _ = _validate_selector_rows(body["frames"], "frames")
    landmarks, references = _validate_selector_rows(body["landmarks"], "landmarks")
    _need(references <= set(frames), "source.body.landmarks", "missing referenced frame")
    return parts, frames, landmarks, dimensions
def _admit_source_bytes(raw, _admission=_COMMITMENTS["admission"]):
    source, digest = _decode_source_json(raw, "source")
    _need(len(raw) == _admission["sizes"][2] and digest == _admission["hashes"][1], "source", "source identity mismatch")
    parts, frames, landmarks, dimensions = _validate_source_document(source)
    return {"parts": parts, "frames": frames, "landmarks": landmarks,
            "dimensions": dimensions, "bytes": raw, "sha256": digest}
def _validate_profile_table(table, _c=_COMMITMENTS):
    admission, semantic = _c["admission"], _c["semantic"]
    _keys(table, {"base_source", "canonicalization", "format", "profiles", "transform"}, "profile table")
    _literal(table["format"], "creature-kernel.disposable-structural-profile-candidates.v1", "profile table.format")
    _fixed_scalars(table["base_source"], (("document", semantic["source_document"]), ("namespace", "main"), ("path", admission["roles"][1]), ("sha256", admission["hashes"][1])), "profile table.base_source")
    profiles = table["profiles"]
    _need(type(profiles) is list and len(profiles) == len(semantic["profile_ids"]), "profile profiles", "wrong count")
    for index, raw in enumerate(profiles):
        where = f"profile table.profiles[{index}]"; row = _keys(raw, {"dimension_scales", "id", "label", "part_placements"}, where)
        _literal(row["id"], semantic["profile_ids"][index], f"{where}.id"); _text(row["label"], f"{where}.label")
        scales = _obj(row["dimension_scales"], f"{where}.dimension_scales"); _keys(scales, semantic["profile_dimension_keys"], f"{where}.dimension_scales")
        _need(all(type(number) is int and number > 0 for number in scales.values()), where, "invalid profile scale")
        _need(index != 0 or all(number == 1000 for number in scales.values()), where, "neutral scales differ")
        _obj(row["part_placements"], f"{where}.part_placements")
    return profiles[0]
def _admit_profile_bytes(raw, _admission=_COMMITMENTS["admission"]):
    table, digest = _decode_source_json(raw, "profile table")
    _need(len(raw) == _admission["sizes"][3] and digest == _admission["hashes"][2], "profile table", "profile identity mismatch")
    return _validate_profile_table(table), raw, digest
def _verify_contract(path=_PATHS[0], _c=_COMMITMENTS):
    _admission, operations = _c["admission"], _c["operations"]
    paths, hashes, sizes = _admission["paths"], _admission["hashes"], _admission["sizes"]
    contract = _fixed_path(path, paths[0], "contract path")
    sidecar = _fixed_path(paths[1], paths[1], "contract sidecar path")
    contract_raw, sidecar_raw = _read(contract, "contract"), _read(sidecar, "contract sidecar")
    _need(len(contract_raw) == sizes[0] and operations["sha256_bytes"](contract_raw) == hashes[0], "contract", "identity mismatch")
    _need(len(sidecar_raw) == sizes[1] and sidecar_raw == _admission["sidecar"], "contract sidecar", "identity mismatch")
def _fixed_inputs(source_path, contract_path, profile_path, _admission=_COMMITMENTS["admission"]):
    paths = _admission["paths"]
    _verify_contract(contract_path)
    source = _fixed_path(source_path, paths[2], "source path"); profile = _fixed_path(profile_path, paths[3], "profile table path")
    admission = _admit_source_bytes(_read(source, "source")); selected, raw, digest = _admit_profile_bytes(_read(profile, "profile table"))
    return admission, selected, raw, digest
def _select(rows, owner, role, name):
    match = rows.get((owner, role))
    _need(match is not None, f"body.{name}.{role}", "missing required record")
    return match
def _world(parts, chain):
    _need(chain and all(owner in parts for owner in chain), "world translation", "invalid chain")
    result = [0.0, 0.0, 0.0]
    for owner in chain:
        placement = parts[owner][0]["placement"]; result = _add(result, _vector(placement["translation"], "part placement.translation"))
    return result
def _select_position(admission, owner, role, frame_role, worlds):
    row, index = _select(admission["landmarks"], owner, role, "landmarks")
    frame = _keys(row["frame"], {"owner", "role"}, f"body.landmarks[{index}].frame")
    _need(_address(frame["owner"]) == owner and frame["role"] == frame_role, f"body.landmarks[{index}].frame", "wrong landmark frame")
    _select(admission["frames"], owner, frame_role, "frames")
    position = _vector(row["position"], f"body.landmarks[{index}].position"); return _add(worlds[owner], position)
def _dimension(admission, owner, role):
    row, index = _select(admission["dimensions"], owner, role, "dimensions")
    return _number(row["value"], f"body.dimensions[{index}].value", positive=True), index
def _source_files(source_digest, source_size, profile_digest, profile_size, _roles=_COMMITMENTS["admission"]["roles"]):
    records = ({"path": _roles[1], "sha256": source_digest, "bytes": source_size}, {"path": _roles[2], "sha256": profile_digest, "bytes": profile_size})
    return sorted(records, key=lambda record: record["path"].encode("utf-8"))
def _identity(path, digest): return {"path": path, "sha256": digest}
def _walk(value, spec, where, *, wire, _c=_COMMITMENTS):
    if spec is str: return _text(value, where, nonempty=False)
    if spec is int: _need(type(value) is int, where, "expected integer"); return value
    if spec is _c["semantic"]["address_marker"]: _runtime_address(value, where); return value
    if type(spec) is type(_c["prepared_spec"]):
        record = _keys(value, spec, where)
        for field, child_spec in spec.items():
            converted = _walk(record[field], child_spec, f"{where}.{field}", wire=wire)
            if wire: record[field] = converted
        return record
    kind, argument, *tail = spec
    if kind == "binary64": return _number(value, where, runtime=not wire, positive=argument and not wire, wire=wire)
    if kind == "vector": return _vector(value, where, argument, runtime=not wire, wire=wire)
    _need(kind == "list" and type(value) is list and len(value) == argument, where, "wrong list shape")
    for index, item in enumerate(value):
        converted = _walk(item, tail[0], f"{where}[{index}]", wire=wire)
        if wire: value[index] = converted
    return value
def _validate_prepared_structure(prepared, *, wire=False, _spec=_COMMITMENTS["prepared_spec"]): return _walk(prepared, _spec, "prepared", wire=wire)
def _validate_prepared_shape(prepared): return _validate_prepared_structure(prepared)
def _chains():
    pelvis, torso, neck = _a("pelvis"), _a("torso"), _a("neck")
    result = {pelvis: (pelvis,), torso: (pelvis, torso), neck: (pelvis, torso, neck)}
    for side in ("left", "right"):
        result[_a("upper_arm", side)] = (pelvis, torso, _a("upper_arm", side)); result[_a("thigh", side)] = (pelvis, _a("thigh", side))
    return result
def _part_output(parts, owner, _rotation=_COMMITMENTS["semantic"]["rotation"]):
    value = _vector(parts[owner][0]["placement"]["translation"], "part placement.translation")
    return {"address": _address_json(owner), "placement": {"translation": value, "rotation_xyzw": list(_rotation)}}
def _station_suffixes(role): return (("lateral_radius", "forward_radius", "forward_radius") if role == "neck" else ("lateral_radius", "anterior_radius", "posterior_radius"))
def _station_output(admission, worlds, role, prefix):
    owner = _a(role)
    frame = "form_head_neck_profile_control" if role == "neck" else "form_torso_profile_control"
    radii = [_dimension(admission, owner, f"{prefix}_{suffix}")[0] for suffix in _station_suffixes(role)]
    return {"owner": _address_json(owner), "prefix": prefix, "C": _select_position(admission, owner, prefix, frame, worlds), "rL": radii[0], "rA": radii[1], "rP": radii[2]}
def _side_output(admission, worlds, side, part_role, positions, dimensions):
    owner = _a(part_role, side)
    result = {field: _select_position(admission, owner, role, frame, worlds) for field, role, frame in positions}
    if part_role == "upper_arm": result["arm_origin"] = list(worlds[owner])
    for field, role in dimensions: result[field] = _dimension(admission, owner, role)[0]
    return result
def _build_prepared(admission, profile, profile_raw, profile_digest, _c=_COMMITMENTS):
    fixed, semantic = _c["admission"], _c["semantic"]
    parts, chains = admission["parts"], _chains()
    worlds = {owner: _world(parts, chain) for owner, chain in chains.items()}
    sides = {group: {side: _side_output(admission, worlds, side, role, positions, dimensions) for side in ("left", "right")} for group, role, positions, dimensions in semantic["side_configs"]}
    prepared = {
        "schema": semantic["schema"], "contract": _identity(fixed["roles"][0], fixed["hashes"][0]), "source": _identity(fixed["roles"][1], fixed["hashes"][1]),
        "profile_selection": {
            "profile_id": semantic["neutral_profile"], "profile_table_path": fixed["roles"][2],
            "profile_table_sha256": profile_digest, "dimensions": {key: float(number) for key, number in profile["dimension_scales"].items()},
        },
        "basis": dict(semantic["basis"]), "parts": [_part_output(parts, _a(role, side)) for role, side in semantic["parts"]],
        "stations": {n: _station_output(admission, worlds, r, p) for n, r, p in semantic["stations"]},
        "shoulders": sides["shoulders"], "hips": sides["hips"],
        "provenance": {"source_files": _source_files(admission["sha256"], len(admission["bytes"]), profile_digest, len(profile_raw))},
    }
    return _validate_prepared_shape(prepared)
def _prepared_apis(_c):
    fixed, operations = _c["admission"], _c["operations"]
    shape, structure, build, inputs, need, attempt = _validate_prepared_shape, _validate_prepared_structure, _build_prepared, _fixed_inputs, _need, _attempt
    @_public_admission
    def validate_prepared(prepared):
        """Admit only the projection freshly derived from the fixed files."""
        value = shape(prepared); expected = build(*inputs(fixed["paths"][2], fixed["paths"][0], fixed["paths"][3]))
        need(operations["json_bytes"](value) == operations["json_bytes"](expected), "prepared", "values do not match fixed projection")
        return value
    @_public_admission
    def admit_prepared_bytes(raw):
        """Decode and admit exact canonical prepared bytes with schema-aware floats."""
        need(type(raw) is bytes, "prepared bytes", "expected bytes")
        decoded = attempt(operations["decode_json"], (raw,), (operations["serialization_error"], RecursionError), "prepared bytes", "invalid canonical JSON")
        value = structure(decoded, wire=True); need(operations["json_bytes"](value) == raw, "prepared bytes", "coercion changed canonical bytes")
        return validate_prepared(value)
    @_public_admission
    def prepare_standard_neutral(source_path=fixed["paths"][2], *, contract_path=fixed["paths"][0], profile_table_path=fixed["paths"][3]):
        """Admit fixed inputs and return the exact standard-neutral object."""
        return build(*inputs(source_path, contract_path, profile_table_path))
    return validate_prepared, admit_prepared_bytes, prepare_standard_neutral
validate_prepared, admit_prepared_bytes, prepare_standard_neutral = _prepared_apis(_COMMITMENTS)
def _pointer(kind, index, axis=None):
    if kind in {"part", "landmark"}:
        _need(axis in range(3), "source pointer", "invalid axis")
        path = "parts" if kind == "part" else "landmarks"
        field = "placement/translation" if kind == "part" else "position"
        return f"/body/{path}/{index}/{field}/{axis}"
    _need(kind == "dimension" and axis is None, "source pointer", "invalid pointer kind")
    return f"/body/dimensions/{index}/value"
def _bind(component, derivation, addresses, pointers, _json_bytes=_COMMITMENTS["operations"]["json_bytes"]):
    addresses = sorted(set(addresses), key=lambda item: _json_bytes(_address_json(item)))
    pointers = sorted(set(pointers), key=str.encode)
    _need(addresses and pointers, "source binding", "empty binding")
    return {"prepared_component": component, "derivation_id": derivation,
            "source_addresses": [_address_json(item) for item in addresses],
            "source_pointers": pointers}
def _validate_binding_records(records, _c=_COMMITMENTS):
    _need(type(records) is list and len(records) == 92, "source bindings", "expected 92 records")
    components = []
    for index, raw in enumerate(records):
        where = f"source bindings[{index}]"
        row = _keys(raw, {"prepared_component", "derivation_id", "source_addresses", "source_pointers"}, where)
        components.append(_text(row["prepared_component"], f"{where}.prepared_component"))
        _text(row["derivation_id"], f"{where}.derivation_id")
        addresses, pointers = row["source_addresses"], row["source_pointers"]
        _need(type(addresses) is list and addresses, where, "expected source addresses")
        _need(type(pointers) is list and pointers, where, "expected source pointers")
        for address_index, address in enumerate(addresses):
            _runtime_address(address, f"{where}.source_addresses[{address_index}]")
        for pointer_index, pointer in enumerate(pointers):
            _text(pointer, f"{where}.source_pointers[{pointer_index}]")
    _need(len(set(components)) == 92 and components == sorted(components, key=str.encode),
          "source bindings", "wrong component order or uniqueness")
    hashes, operations = _c["admission"]["binding_hashes"], _c["operations"]
    _need(operations["sha256_bytes"](operations["json_bytes"](components)) == hashes[0], "source bindings", "component universe mismatch")
    _need(operations["sha256_bytes"](operations["json_bytes"](records)) == hashes[1], "source bindings", "mapping mismatch")
    return records
def _append_sum(bindings, admission, parts, chains, component, owner, landmark_role, _axes=_COMMITMENTS["semantic"]["axes"]):
    chain, landmark_index = chains[owner], None
    if landmark_role is not None:
        landmark_index = _select(admission["landmarks"], owner, landmark_role, "landmarks")[1]
    derivation = ("source.world-landmark-axis-sum.v1" if landmark_role
                  else "source.world-placement-axis-sum.v1")
    for axis, name in enumerate(_axes):
        pointers = [_pointer("part", parts[item][1], axis) for item in chain]
        if landmark_index is not None:
            pointers.append(_pointer("landmark", landmark_index, axis))
        bindings.append(_bind(f"{component}.{name}", derivation, chain, pointers))
def _append_group(bindings, admission, parts, chains, prefix, owner, sums, dimensions):
    for field, landmark in sums:
        _append_sum(bindings, admission, parts, chains, f"{prefix}.{field}", owner, landmark)
    for field, role in dimensions:
        _, index = _dimension(admission, owner, role)
        bindings.append(_bind(f"{prefix}.{field}", "source.dimension-value.v1",
                              (owner,), (_pointer("dimension", index),)))
def _binding_api(_c):
    fixed, semantic = _c["admission"], _c["semantic"]
    inputs, chains_for_parts, address, suffixes, append, validate = _fixed_inputs, _chains, _a, _station_suffixes, _append_group, _validate_binding_records
    @_public_admission
    def source_binding_records(source_path=fixed["paths"][2], *, contract_path=fixed["paths"][0], profile_table_path=fixed["paths"][3]):
        admission, _, _, _ = inputs(source_path, contract_path, profile_table_path)
        parts, bindings, chains = admission["parts"], [], chains_for_parts()
        for name, role, prefix in semantic["stations"]:
            owner = address(role)
            dimensions = tuple((field, f"{prefix}_{suffix}") for field, suffix in zip(("rL", "rA", "rP"), suffixes(role)))
            append(bindings, admission, parts, chains, f"stations.{name}", owner, (("C", prefix),), dimensions)
        for side in ("left", "right"):
            append(bindings, admission, parts, chains, f"shoulders.{side}", address("upper_arm", side), semantic["shoulder_sums"], semantic["shoulder_dims"])
            append(bindings, admission, parts, chains, f"hips.{side}", address("thigh", side), semantic["hip_sums"], semantic["hip_dims"])
        return validate(sorted(bindings, key=lambda item: item["prepared_component"].encode("utf-8")))
    return source_binding_records
source_binding_records = _binding_api(_COMMITMENTS)
build_source_binding_records = source_binding_records
canonical_json_bytes = _JSON_BYTES
def _sha_api(operations):
    def canonical_json_sha256(value): return operations["sha256_bytes"](operations["json_bytes"](value))
    return canonical_json_sha256
canonical_json_sha256 = _sha_api(_COMMITMENTS["operations"])
__all__ = [
    "EXPECTED_CONTRACT_SHA256", "EXPECTED_PROFILE_TABLE_SHA256",
    "EXPECTED_SOURCE_SHA256", "PreparedProjectionError",
    "admit_prepared_bytes", "build_source_binding_records", "canonical_json_bytes",
    "canonical_json_sha256", "normalize_source_address",
    "prepare_standard_neutral", "source_binding_records", "validate_prepared",
]
