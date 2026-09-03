"""Minimal standard-neutral projection for the root-complex experiment."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path


class PreparedProjectionError(ValueError): pass


class _DuplicateJSONKeyError(ValueError): pass


class _NonFiniteJSONConstantError(ValueError): pass


class _NonFiniteJSONNumberError(ValueError): pass


class _JSONRootTypeError(TypeError): pass

_TOP = {"basis", "body", "contract", "extensions", "profiles", "source"}
_BODY = {"attachments", "capabilities", "dimensions", "fields", "frames", "joints", "landmarks", "modules", "parts", "regions", "sockets"}
_COUNT = {"parts": 18, "frames": 16, "landmarks": 43, "dimensions": 153}
_I = (0, 0, 0, 1)
_D = "derivation=source_dimension_integer_as_thousandths_of_canonical_metre_v1"
_P = "derivation=parent_local_part_translation_plus_landmark_position_v1"
_BILATERAL_SCALARS = {"arm_root_depth": ("upper_arm", "form_arm_profile_upper_arm_start_forward_radius"), "arm_root_outward": ("upper_arm", "form_arm_profile_upper_arm_start_lateral_radius"), "thigh_lateral_radius": ("thigh", "form_leg_profile_thigh_start_lateral_radius"), "thigh_depth": ("thigh", "form_leg_profile_thigh_start_forward_radius")}

def _bad(where, message): raise PreparedProjectionError(f"{where}: {message}")
def _ok(condition, where, message):
    if not condition: _bad(where, message)
def _dict(value, where): _ok(isinstance(value, dict), where, "expected object"); return value
def _finite(value):
    try: return math.isfinite(value)
    except OverflowError: return False
def _num(value, where, positive=False):
    _ok(not isinstance(value, bool) and isinstance(value, (int, float)) and _finite(value), where, "expected finite number"); _ok(not positive or value > 0, where, "expected positive number"); return 0 if value == 0 else value
def _vec(value, where, size=3):
    _ok(isinstance(value, list) and len(value) == size, where, f"expected {size}-vector"); return tuple(_num(x, f"{where}[{i}]") for i, x in enumerate(value))
def _pairs(items):
    result = {}
    for key, value in items:
        if key in result: raise _DuplicateJSONKeyError(f"duplicate JSON key {key!r}")
        result[key] = value
    return result
def _reject_constant(value): raise _NonFiniteJSONConstantError(value)
def _parse_float(value):
    number = float(value)
    if not math.isfinite(number): raise _NonFiniteJSONNumberError(value)
    return number
def _require_object(value):
    if not isinstance(value, dict): raise _JSONRootTypeError
    return value
def _reject_excessive_json_nesting(text):
    depth = 0; in_string = escaped = False
    for char in text:
        if in_string: escaped, in_string = (False, True) if escaped else (char == "\\", char != '"')
        else: in_string = char == '"'; depth += char in "[{"; depth -= char in "]}"
        if depth > 1000: raise RecursionError("JSON nesting exceeds the supported limit")
def _load(path):
    try:
        raw = Path(path).read_bytes()
    except OSError as exc:
        raise PreparedProjectionError("source file could not be read") from exc
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise PreparedProjectionError("source is not valid UTF-8") from exc
    try:
        _reject_excessive_json_nesting(text)
        data = _require_object(json.loads(text, object_pairs_hook=_pairs, parse_constant=_reject_constant, parse_float=_parse_float))
    except _DuplicateJSONKeyError as exc:
        raise PreparedProjectionError("source contains duplicate JSON keys") from exc
    except _NonFiniteJSONConstantError as exc:
        raise PreparedProjectionError("source contains non-finite JSON constants") from exc
    except _NonFiniteJSONNumberError as exc:
        raise PreparedProjectionError("source contains non-finite JSON numbers") from exc
    except json.JSONDecodeError as exc:
        raise PreparedProjectionError("source has invalid JSON syntax") from exc
    except _JSONRootTypeError as exc:
        raise PreparedProjectionError("source JSON root must be an object") from exc
    except RecursionError as exc:
        raise PreparedProjectionError("source JSON is too deeply nested") from exc
    except TypeError as exc:
        raise PreparedProjectionError("source has an invalid JSON type") from exc
    except ValueError as exc:
        raise PreparedProjectionError("source contains an invalid JSON value") from exc
    return data, hashlib.sha256(raw).hexdigest()
def _addr(value, where):
    value = _dict(value, where); _ok(set(value) == {"namespace", "anchors", "kind", "role"}, where, "invalid address")
    anchors = value["anchors"]; _ok(isinstance(anchors, list) and all(isinstance(x, str) and x for x in anchors) and len(set(anchors)) == len(anchors), where, "invalid anchors"); _ok(value["kind"] == "part" and isinstance(value["namespace"], str) and isinstance(value["role"], str), where, "invalid part address"); return value["namespace"], tuple(anchors), "part", value["role"]
def _pick(rows, owner, role, fields, name):
    hits = []
    for i, raw in enumerate(rows):
        where, row = f"body.{name}[{i}]", _dict(raw, f"body.{name}[{i}]"); key = "owner" if "owner" in row else "address"; _ok(key in row, where, "missing record selector")
        if _addr(row[key], f"{where}.{key}") == owner and row.get("role", owner[3]) == role: hits.append((row, where))
    _ok(len(hits) == 1, f"body.{name}.{role}", "missing or duplicate required record"); row, where = hits[0]
    _ok(set(row) == fields, where, "unknown or missing required field"); return row, where
def _part(rows, owner, parent):
    row, where = _pick(rows, owner, owner[3], {"address", "containment", "placement"}, "parts"); place = _dict(row["placement"], where)
    _ok(set(place) == {"translation", "rotation_xyzw"}, where, "unknown placement field"); translation = _vec(place["translation"], f"{where}.placement.translation"); _ok(_vec(place["rotation_xyzw"], f"{where}.placement.rotation_xyzw", 4) == _I, where, "non-identity part rotation"); containment = _dict(row["containment"], where)
    _ok(containment == {"root": True} if parent is None else set(containment) == {"parent"} and _addr(containment["parent"], where) == parent, where, "invalid containment")
    return translation, where
def _add(a, b): result = tuple(x + y for x, y in zip(a, b)); _ok(all(_finite(value) for value in result), "derived point", "expected finite number"); return result
def _dimension(rows, owner, role):
    row, where = _pick(rows, owner, role, {"owner", "role", "value"}, "dimensions"); _ok(not isinstance(row["value"], bool) and isinstance(row["value"], int), f"{where}.value", "expected integer dimension"); value = _num(row["value"], f"{where}.value", True) / 1000.0
    return value, f"{where}.value; {_D}"
def _landmark(rows, owner, role, frame):
    row, where = _pick(rows, owner, role, {"owner", "role", "frame", "position"}, "landmarks"); ref = _dict(row["frame"], f"{where}.frame"); _ok(set(ref) == {"owner", "role"} and (_addr(ref["owner"], where), ref["role"]) == frame, where, "invalid landmark frame"); return _vec(row["position"], f"{where}.position"), where
def _point(pair, owner, part_data, world):
    local, where = pair; point = _add(world[owner], local); return point, f"{where}.position; {part_data[owner][1]}.placement.translation; {_P}"
def _frame(rows, owner, role):
    row, where = _pick(rows, owner, role, {"owner", "role", "transform"}, "frames"); transform = _dict(row["transform"], where); _ok(set(transform) == {"translation", "rotation_xyzw"} and _vec(transform["translation"], where) == (0, 0, 0) and _vec(transform["rotation_xyzw"], where, 4) == _I, where, "non-identity named frame")
def _bilateral_scalar(rows, owners, role, name):
    left, right = (_dimension(rows, owner, role) for owner in owners)
    _ok(left[0] == right[0], f"scalars.{name}", "left and right dimensions must match")
    return {"value": left[0], "provenance": "; ".join((left[1], right[1], "derivation=validated_bilateral_scalar_v1"))}


def prepare_standard_neutral(path):
    source, digest = _load(path); _ok(set(source) == _TOP, "source", "unknown or missing top-level field")
    _ok(source["contract"] == {"family": "creature-kernel.body", "revision": 1}, "source.contract", "wrong contract")
    _ok(source["source"] == {"document": "stylized_digitigrade_biped_authored_form", "namespace": "main", "dependencies": []}, "source.source", "wrong source identity")
    _ok(source["basis"] == {"length_unit": "metre", "handedness": "right", "up": "+y", "forward": "+z"}, "source.basis", "wrong basis")
    _ok(source["profiles"] == {"semantic_numeric": "ck.numeric-frame.r1"} and source["extensions"] == [], "source", "unsupported profile or extension")
    body = _dict(source["body"], "source.body"); _ok(set(body) == _BODY, "source.body", "unknown or missing collection")
    _ok(body["fields"] == [], "body.fields", "forbidden geometry-input collection")
    for name, count in _COUNT.items(): _ok(isinstance(body[name], list) and len(body[name]) == count, f"body.{name}", f"expected {count} records")
    ns = source["source"]["namespace"]
    def part(role, side=None): return ns, () if side is None else (side,), "part", role
    p = {part("pelvis"): _part(body["parts"], part("pelvis"), None), part("torso"): _part(body["parts"], part("torso"), part("pelvis")), part("neck"): _part(body["parts"], part("neck"), part("torso"))}
    for side in ("left", "right"):
        p[part("upper_arm", side)] = _part(body["parts"], part("upper_arm", side), part("torso")); p[part("thigh", side)] = _part(body["parts"], part("thigh", side), part("pelvis"))
    world = {part("pelvis"): p[part("pelvis")][0], part("torso"): _add(p[part("pelvis")][0], p[part("torso")][0])}
    world[part("neck")] = _add(world[part("torso")], p[part("neck")][0])
    for side in ("left", "right"):
        world[part("upper_arm", side)] = _add(world[part("torso")], p[part("upper_arm", side)][0]); world[part("thigh", side)] = _add(world[part("pelvis")], p[part("thigh", side)][0])
    for owner, role in ((part("pelvis"), "form_torso_profile_control"), (part("torso"), "form_torso_profile_control"), (part("neck"), "form_head_neck_profile_control")):
        _frame(body["frames"], owner, role)
    for side in ("left", "right"):
        _frame(body["frames"], part("upper_arm", side), "form_shoulder_control"); _frame(body["frames"], part("thigh", side), "form_leg_profile_control")
    frame_body = {"lateral_axis": (1, 0, 0), "up_axis": (0, 1, 0), "forward_axis": (0, 0, 1), "provenance": "source.basis; derivation=right_handed_lateral_axis_from_up_forward_v1"}
    landmarks = {}
    for side in ("left", "right"):
        upper, thigh = part("upper_arm", side), part("thigh", side); shoulder_frame, leg_frame = (upper, "form_shoulder_control"), (thigh, "form_leg_profile_control")
        for name, owner, role, frame in ((f"shoulder_peak_{side}", upper, "form_shoulder_peak", shoulder_frame), (f"axilla_{side}", upper, "form_axilla", shoulder_frame), (f"thigh_start_{side}", thigh, "form_leg_profile_thigh_start", leg_frame), (f"thigh_mid_{side}", thigh, "form_leg_profile_thigh_midpoint", leg_frame)):
            local, where = _landmark(body["landmarks"], owner, role, frame); landmarks[name] = dict(zip(("point", "provenance"), _point((local, where), owner, p, world)))
        _ok(landmarks[f"shoulder_peak_{side}"]["point"] != landmarks[f"axilla_{side}"]["point"] and landmarks[f"thigh_start_{side}"]["point"] != landmarks[f"thigh_mid_{side}"]["point"], f"{side} controls", "degenerate required route")
    specs = (("lower_pelvis", "pelvis", "form_torso_profile_lower_pelvis"), ("upper_pelvis", "pelvis", "form_torso_profile_upper_pelvis"), ("lower_abdomen", "torso", "form_torso_profile_lower_abdomen"), ("waist_abdomen", "torso", "form_torso_profile_waist_abdomen"), ("lower_ribcage", "torso", "form_torso_profile_lower_ribcage"), ("upper_ribcage_shoulder", "torso", "form_torso_profile_upper_ribcage_shoulder"), ("neck_collar", "neck", "form_head_neck_profile_neck_collar"))
    stations = {}
    for name, role, station_role in specs:
        owner = part(role); local, where = _landmark(body["landmarks"], owner, station_role, (owner, "form_torso_profile_control" if role != "neck" else "form_head_neck_profile_control")); center, center_provenance = _point((local, where), owner, p, world); prefix = station_role + "_"
        lateral, lp = _dimension(body["dimensions"], owner, prefix + "lateral_radius"); forward = name == "neck_collar"; front, fp = _dimension(body["dimensions"], owner, prefix + ("forward_radius" if forward else "anterior_radius")); back, bp = _dimension(body["dimensions"], owner, prefix + ("forward_radius" if forward else "posterior_radius")); bp += "; derivation=symmetric_neck_depth_from_forward_radius_v1" if forward else ""
        stations[name] = {"center": center, "lateral_radius": lateral, "front_extent": front, "back_extent": back, "provenance": "; ".join((center_provenance, lp, fp, bp))}
    owners = {role: tuple(part(role, side) for side in ("left", "right")) for role in ("upper_arm", "thigh")}
    scalars = {name: _bilateral_scalar(body["dimensions"], owners[role], dimension_role, name)
               for name, (role, dimension_role) in _BILATERAL_SCALARS.items()}
    return {"source": {"document": source["source"]["document"], "namespace": ns, "sha256": digest, "provenance": "raw_source_utf8_bytes_sha256_v1"}, "basis": dict(source["basis"]), "frames": {"body": frame_body}, "landmarks": landmarks, "stations": stations, "scalars": scalars}


def canonical_json_bytes(value): return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
def canonical_json_sha256(value): return hashlib.sha256(canonical_json_bytes(value)).hexdigest()
__all__ = ["PreparedProjectionError", "canonical_json_bytes", "canonical_json_sha256", "prepare_standard_neutral"]
