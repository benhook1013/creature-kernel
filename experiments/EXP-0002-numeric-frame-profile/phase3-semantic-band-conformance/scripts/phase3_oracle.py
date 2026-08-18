"""Independent exact semantic oracle for synthetic Phase 3 cases.

The oracle consumes only serialized source text and a metric name.  It does
not import the materializer, read a corpus, or use construction metadata.  All
source numeric tokens are retained as :class:`~decimal.Decimal` values and
converted to :class:`~fractions.Fraction` before basis conversion or rigid
transform algebra.
"""

from __future__ import annotations

import json
import math
from fractions import Fraction
from typing import Any, Mapping, Sequence

from phase3_common import (
    MAX_SOURCE_BYTES,
    INTERVAL_DECIMAL_PLACES,
    SQRT_PRECISION_BITS,
    Phase3Error,
    RationalInterval,
    as_fraction,
    decimal_outward,
    directed_sqrt_bounds,
    fraction_text,
    fraction_to_binary64_bits,
    parse_json,
)


DOMAIN_LIMIT = Fraction(16)
CONTRIBUTION_SUM_LIMIT = Fraction(64)
PATH_EDGE_LIMIT = 4
KAPPA_LIMIT = Fraction(1_000_000)
UNIT_METRES = {"metre": Fraction(1), "centimetre": Fraction(1, 100), "millimetre": Fraction(1, 1000)}


class OracleError(Phase3Error):
    pass


class OracleIntegrityError(OracleError):
    """The source itself cannot be evaluated by the closed oracle."""


Vec3 = tuple[Fraction, Fraction, Fraction]
Quat = tuple[Fraction, Fraction, Fraction, Fraction]
Transform = tuple[Vec3, Quat]


IDENTITY: Transform = ((Fraction(0), Fraction(0), Fraction(0)), (Fraction(0), Fraction(0), Fraction(0), Fraction(1)))


def _fail(code: str, detail: str) -> None:
    raise OracleError(code, detail)


def _obj(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        _fail("wrong-type", f"{label} must be an object")
    return value


def _arr(value: Any, label: str, length: int | None = None) -> list[Any]:
    if not isinstance(value, list):
        _fail("wrong-type", f"{label} must be an array")
    if length is not None and len(value) != length:
        _fail("length", f"{label} must contain {length} entries")
    return value


def _str(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value:
        _fail("wrong-type", f"{label} must be a non-empty string")
    return value


def _fraction(value: Any, label: str) -> Fraction:
    try:
        return as_fraction(value, label)
    except Phase3Error as error:
        raise OracleError(error.code, error.detail) from error


def _address(value: Any, label: str) -> dict[str, Any]:
    result = _obj(value, label)
    for field in ("namespace", "anchors", "kind", "role"):
        if field not in result:
            _fail("address", f"{label}.{field} is missing")
    _str(result["namespace"], f"{label}.namespace")
    anchors = _arr(result["anchors"], f"{label}.anchors")
    if any(not isinstance(anchor, str) for anchor in anchors):
        _fail("address", f"{label}.anchors must contain strings")
    _str(result["kind"], f"{label}.kind")
    _str(result["role"], f"{label}.role")
    return {"namespace": result["namespace"], "anchors": list(anchors), "kind": result["kind"], "role": result["role"]}


def _key(address: Mapping[str, Any]) -> tuple[Any, ...]:
    return (address.get("namespace"), tuple(address.get("anchors", [])), address.get("kind"), address.get("role"))


def _signed_axis(value: Any, label: str) -> tuple[int, int]:
    text = _str(value, label)
    if len(text) != 2 or text[0] not in "+-" or text[1] not in "xyz":
        _fail("basis", f"{label} is not a signed axis")
    return "xyz".index(text[1]), 1 if text[0] == "+" else -1


def basis_map(source: Mapping[str, Any]) -> tuple[tuple[int, int], ...]:
    basis = _obj(source.get("basis"), "basis")
    up_index, up_sign = _signed_axis(basis.get("up"), "basis.up")
    forward_index, forward_sign = _signed_axis(basis.get("forward"), "basis.forward")
    if up_index == forward_index:
        _fail("basis", "basis up and forward are collinear")
    cross = {
        (0, 1): (2, up_sign * forward_sign),
        (1, 2): (0, up_sign * forward_sign),
        (2, 0): (1, up_sign * forward_sign),
        (1, 0): (2, -up_sign * forward_sign),
        (2, 1): (0, -up_sign * forward_sign),
        (0, 2): (1, -up_sign * forward_sign),
    }[(up_index, forward_index)]
    handedness = _str(basis.get("handedness"), "basis.handedness")
    if handedness not in {"right", "left"}:
        _fail("basis", "basis.handedness is unsupported")
    right = (cross[0], cross[1] if handedness == "right" else -cross[1])
    return (right, (up_index, up_sign), (forward_index, forward_sign))


def _map_vec(values: Any, mapping: tuple[tuple[int, int], ...], unit: Fraction, label: str) -> Vec3:
    raw = [_fraction(item, f"{label}[{index}]") for index, item in enumerate(_arr(values, label, 3))]
    return tuple(raw[index] * sign * unit for index, sign in mapping)  # type: ignore[return-value]


def _map_quat(values: Any, mapping: tuple[tuple[int, int], ...], label: str) -> Quat:
    raw = [_fraction(item, f"{label}[{index}]") for index, item in enumerate(_arr(values, label, 4))]
    permutation = [item[0] for item in mapping]
    inversions = sum(permutation[i] > permutation[j] for i in range(3) for j in range(i + 1, 3))
    determinant = (-1 if inversions % 2 else 1) * math.prod(item[1] for item in mapping)
    vector = [raw[index] * sign for index, sign in mapping]
    vector = [item * determinant for item in vector]
    return _canonical_q(tuple(vector + [raw[3]]))


def _canonical_q(value: Sequence[Fraction]) -> Quat:
    result = tuple(value)
    sign = next((result[index] for index in (3, 0, 1, 2) if result[index] != 0), None)
    if sign is not None and sign < 0:
        result = tuple(-item for item in result)
    return result  # type: ignore[return-value]


def _qmul(left: Sequence[Fraction], right: Sequence[Fraction]) -> Quat:
    x1, y1, z1, w1 = left
    x2, y2, z2, w2 = right
    return (
        w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2,
        w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2,
        w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2,
        w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2,
    )


def _qinv(value: Sequence[Fraction]) -> Quat:
    return (-value[0], -value[1], -value[2], value[3])  # type: ignore[return-value]


def _qrot(q: Sequence[Fraction], value: Sequence[Fraction]) -> Vec3:
    norm_squared = sum(component * component for component in q)
    if norm_squared == 0:
        _fail("quaternion", "cannot rotate with a zero quaternion")
    result = _qmul(_qmul(q, (value[0], value[1], value[2], Fraction(0))), _qinv(q))
    return tuple(component / norm_squared for component in result[:3])  # type: ignore[return-value]


def _compose(left: Transform, right: Transform) -> Transform:
    translation = tuple(left[0][index] + _qrot(left[1], right[0])[index] for index in range(3))
    return translation, _canonical_q(_qmul(left[1], right[1]))  # type: ignore[return-value]


def _inverse(value: Transform) -> Transform:
    q = _canonical_q(_qinv(value[1]))
    return tuple(-component for component in _qrot(q, value[0])), q  # type: ignore[return-value]


def _transform(value: Any, mapping: tuple[tuple[int, int], ...], unit: Fraction, label: str) -> Transform:
    item = _obj(value, label)
    return (_map_vec(item.get("translation"), mapping, unit, f"{label}.translation"), _map_quat(item.get("rotation_xyzw"), mapping, f"{label}.rotation_xyzw"))


def _find(records: list[Any], role: str, anchors: list[str], label: str) -> dict[str, Any]:
    matches = []
    for item in records:
        if isinstance(item, dict) and isinstance(item.get("address"), dict) and item["address"].get("role") == role and item["address"].get("anchors") == anchors:
            matches.append(item)
    if len(matches) != 1:
        _fail("source-shape", f"expected one {label} {role}/{anchors}")
    return _obj(matches[0], label)


def _find_address(records: list[Any], address: Mapping[str, Any], label: str) -> dict[str, Any]:
    wanted = _key(address)
    for item in records:
        if isinstance(item, dict) and _key(item.get("address", {})) == wanted:
            return item
    _fail("source-shape", f"{label} address is absent")
    raise AssertionError


def _source_member(source: Mapping[str, Any]) -> dict[str, str]:
    identity = _obj(source.get("source"), "source.source")
    return {"document": _str(identity.get("document"), "source.source.document"), "namespace": _str(identity.get("namespace"), "source.source.namespace")}


def _location(source: Mapping[str, Any], slot_kind: str, address: Mapping[str, Any], component: str) -> dict[str, Any]:
    return {"member": _source_member(source), "role": "root", "slot": {"kind": slot_kind, "address": _address(address, "location.address"), "component": component}}


def _value_transform(value: Transform) -> dict[str, Any]:
    norm_squared = sum(component * component for component in value[1])
    return {
        "translation_exact": [fraction_text(component) for component in value[0]],
        "translation_binary64": [fraction_to_binary64_bits(component, "translation") for component in value[0]],
        "rotation_raw_exact": [fraction_text(component) for component in value[1]],
        "rotation_norm_squared_exact": fraction_text(norm_squared),
        "rotation_representation": "exact-rational-projective-quaternion",
    }


def _kappa(items: list[Vec3]) -> Fraction | None:
    norms = [max(abs(component) for component in item) for item in items]
    total = tuple(sum(item[index] for item in items) for index in range(3))
    s = sum(norms)
    d = max(abs(component) for component in total)
    if s == d == 0:
        return Fraction(1)
    if d == 0:
        return None
    return s / d


def _rotation_interval(authored: Quat, derived: Quat) -> tuple[RationalInterval, dict[str, Any]]:
    authored_norm_sq = sum(component * component for component in authored)
    derived_norm_sq = sum(component * component for component in derived)
    if authored_norm_sq <= 0 or derived_norm_sq <= 0:
        _fail("quaternion", "rotation interval requires non-zero quaternions")
    product = authored_norm_sq * derived_norm_sq
    product_lower, product_upper = directed_sqrt_bounds(product)
    absolute_dot = abs(sum(left * right for left, right in zip(authored, derived)))
    ratio_lower = Fraction(0) if absolute_dot == 0 else absolute_dot / product_upper
    ratio_upper = Fraction(0) if absolute_dot == 0 else absolute_dot / product_lower
    square_lower = max(Fraction(0), Fraction(2) - 2 * ratio_upper)
    square_upper = max(Fraction(0), Fraction(2) - 2 * ratio_lower)
    lower = directed_sqrt_bounds(square_lower)[0]
    upper = directed_sqrt_bounds(square_upper)[1]
    interval = RationalInterval(lower, upper)
    if interval.width > Fraction(1, 10**10):
        _fail("interval-cap", "rotation truth interval exceeds 1e-10")
    witness = {
        "norm_product_exact": fraction_text(product),
        "norm_product_sqrt_lower_exact": fraction_text(product_lower),
        "norm_product_sqrt_upper_exact": fraction_text(product_upper),
        "absolute_dot_exact": fraction_text(absolute_dot),
        "full_chord_square_lower_exact": fraction_text(square_lower),
        "full_chord_square_upper_exact": fraction_text(square_upper),
        "final_lower_exact": fraction_text(lower),
        "final_upper_exact": fraction_text(upper),
        "method": "integer-isqrt-rational-directed-v1",
        "certified": True,
        "sqrt_precision_bits": SQRT_PRECISION_BITS,
        "decimal_endpoint_places": INTERVAL_DECIMAL_PLACES,
        "quantity": "normalized-q-neg-q-full-chord",
        "propagation": "exact-dot-norm-squared;abs-dot-over-sqrt-product;full-chord-square;directed-final-sqrt",
    }
    return interval, witness


def _domain(source: Mapping[str, Any], mapping: tuple[tuple[int, int], ...], unit: Fraction, parts: list[Any], sockets: list[Any], joints: list[Any], attachments: list[Any], frames: list[Any], landmarks: list[Any], path_nodes: list[dict[str, Any]], authored: Transform, derived: Transform, host: Transform, offset: Transform, mating: Transform) -> dict[str, Any]:
    translations: list[tuple[dict[str, Any], Vec3]] = []
    quaternions: list[tuple[dict[str, Any], Quat]] = []

    def add(frame: Mapping[str, Any], address: Mapping[str, Any], kind: str) -> None:
        location = _location(source, kind, address, "translation")
        transform = _transform(frame, mapping, unit, f"{kind}.frame")
        translations.append((location, transform[0]))
        qloc = json.loads(json.dumps(location))
        qloc["slot"]["component"] = "rotation"
        quaternions.append((qloc, transform[1]))

    for item in parts:
        add(_obj(item, "part").get("placement"), item["address"], "part-placement")
    for item in joints:
        add(_obj(item, "joint").get("proximal_frame"), item["address"], "joint-proximal")
        add(_obj(item, "joint").get("distal_frame"), item["address"], "joint-distal")
    for item in sockets:
        add(_obj(item, "socket").get("interface_frame"), item["address"], "socket-interface")
    for item in attachments:
        add(_obj(item, "attachment").get("offset"), item["address"], "attachment-offset")
    for item in frames:
        add(_obj(item, "frame").get("transform"), item["address"], "named-frame")
    for item in landmarks:
        loc = _location(source, "landmark", _obj(item, "landmark")["address"], "translation")
        translations.append((loc, _map_vec(item["position"], mapping, unit, "landmark.position")))

    authored_contributions = [authored[0]]
    path = IDENTITY
    expanded: list[Vec3] = []
    for item in path_nodes:
        local = _transform(item.get("placement"), mapping, unit, "path.placement")
        expanded.append(_qrot(path[1], local[0]))
        path = _compose(path, local)
    root_to_mating = _compose(path, mating)
    final_rotation = _qmul(_qmul(host[1], offset[1]), _qinv(root_to_mating[1]))
    derived_contributions = [host[0], _qrot(host[1], offset[0])]
    derived_contributions.extend(tuple(-component for component in _qrot(final_rotation, item)) for item in [*expanded, _qrot(path[1], mating[0])])
    all_translations = [value for _, value in translations] + [authored[0], derived[0]]
    canonical_max = max((max(abs(value) for value in item) for item in all_translations), default=Fraction(0))
    authored_max = max((max(abs(value) for value in item) for item in authored_contributions), default=Fraction(0))
    derived_max = max((max(abs(value) for value in item) for item in derived_contributions), default=Fraction(0))
    authored_sum = sum(max(abs(value) for value in item) for item in authored_contributions)
    derived_sum = sum(max(abs(value) for value in item) for item in derived_contributions)
    authored_kappa = _kappa(authored_contributions)
    derived_kappa = _kappa(derived_contributions)
    pair_kappa = None if authored_kappa is None or derived_kappa is None else max(authored_kappa, derived_kappa)
    component_max = max((max(abs(value) for value in q) for _, q in quaternions), default=Fraction(0))
    zero_locations = [location for location, q in quaternions if sum(value * value for value in q) == 0]
    norm_rows = []
    norm_gate = True
    kappa_q_upper: Fraction | None = Fraction(0)
    for location, q in quaternions:
        norm_sq = sum(value * value for value in q)
        if norm_sq == 0:
            norm_gate = False
            kappa_q_upper = None
            norm_rows.append({"location": location, "norm_squared_exact": "0/1", "status": "typed-zero-quaternion"})
            continue
        lower, upper = directed_sqrt_bounds(norm_sq)
        if norm_sq < Fraction(1, 4) or norm_sq > Fraction(4):
            norm_gate = False
        if kappa_q_upper is not None:
            kappa_q_upper = max(kappa_q_upper, Fraction(1) / lower)
        norm_rows.append({"location": location, "norm_squared_exact": fraction_text(norm_sq), "lower": decimal_outward(lower, "lower"), "upper": decimal_outward(upper, "upper")})
    gates = {
        "canonical_translation_components": canonical_max <= DOMAIN_LIMIT,
        "contribution_components": max(authored_max, derived_max) <= DOMAIN_LIMIT,
        "contribution_inf_norm_sum": max(authored_sum, derived_sum) <= CONTRIBUTION_SUM_LIMIT,
        "quaternion_components": component_max <= Fraction(1),
        "source_quaternion_norm": norm_gate,
        "path_edges": len(path_nodes) <= PATH_EDGE_LIMIT,
        "translation_kappa_pair": pair_kappa is not None and pair_kappa <= KAPPA_LIMIT,
        "kappa_q": kappa_q_upper is not None and kappa_q_upper <= Fraction(2),
    }
    ordinary = [name for name, passed in gates.items() if not passed and name not in {"source_quaternion_norm", "kappa_q"}]
    if ordinary:
        status, reason = "out-of-domain", ordinary[0]
    elif zero_locations:
        status, reason = "typed-control", "zero-quaternion"
    elif not all(gates.values()):
        status, reason = "out-of-domain", next(name for name, passed in gates.items() if not passed)
    else:
        status, reason = "admitted", None
    return {
        "status": status,
        "reason": reason,
        "gates": gates,
        "canonical_translation_max_abs_exact": fraction_text(canonical_max),
        "authored_contribution_max_abs_exact": fraction_text(authored_max),
        "derived_contribution_max_abs_exact": fraction_text(derived_max),
        "authored_contribution_inf_norm_sum_exact": fraction_text(authored_sum),
        "derived_contribution_inf_norm_sum_exact": fraction_text(derived_sum),
        "path_edges": len(path_nodes),
        "authored_kappa_exact": None if authored_kappa is None else fraction_text(authored_kappa),
        "derived_kappa_exact": None if derived_kappa is None else fraction_text(derived_kappa),
        "kappa_pair_exact": None if pair_kappa is None else fraction_text(pair_kappa),
        "quaternion_component_max_abs_exact": fraction_text(component_max),
        "source_quaternion_norms": norm_rows,
        "zero_quaternion_locations": zero_locations,
        "kappa_q": {"kind": "not-applicable-typed-control"} if zero_locations else {"kind": "certified-upper", "upper": decimal_outward(kappa_q_upper or Fraction(0), "upper"), "precision_bits": SQRT_PRECISION_BITS},
    }


def _zero_quaternion_locations(source: Mapping[str, Any], mapping: tuple[tuple[int, int], ...], parts: list[Any], sockets: list[Any], joints: list[Any], attachments: list[Any], frames: list[Any]) -> list[dict[str, Any]]:
    locations: list[dict[str, Any]] = []

    def check(frame: Any, address: Any, kind: str) -> None:
        value = _obj(frame, f"{kind}.frame")
        q = _map_quat(value.get("rotation_xyzw"), mapping, f"{kind}.rotation_xyzw")
        if sum(component * component for component in q) == 0:
            locations.append(_location(source, kind, _obj(address, f"{kind}.address"), "rotation"))

    for item in parts:
        check(_obj(item, "part").get("placement"), item["address"], "part-placement")
    for item in joints:
        check(_obj(item, "joint").get("proximal_frame"), item["address"], "joint-proximal")
        check(_obj(item, "joint").get("distal_frame"), item["address"], "joint-distal")
    for item in sockets:
        check(_obj(item, "socket").get("interface_frame"), item["address"], "socket-interface")
    for item in attachments:
        check(_obj(item, "attachment").get("offset"), item["address"], "attachment-offset")
    for item in frames:
        check(_obj(item, "frame").get("transform"), item["address"], "named-frame")
    return locations


def evaluate_source(source_text: str | bytes, metric: str = "translation") -> dict[str, Any]:
    """Evaluate one serialized standalone transform and return source truth."""
    if metric not in {"translation", "rotation"}:
        raise OracleError("metric", "metric must be translation or rotation")
    source_size = len(source_text.encode("utf-8")) if isinstance(source_text, str) else len(source_text)
    if source_size > MAX_SOURCE_BYTES:
        raise OracleError("source-too-large", "source exceeds the 24 KiB Phase 2 limit")
    try:
        source = parse_json(source_text, label="source")
        source = _obj(source, "source")
        mapping = basis_map(source)
        basis = _obj(source.get("basis"), "basis")
        unit_name = _str(basis.get("length_unit"), "basis.length_unit")
        if unit_name not in UNIT_METRES:
            _fail("unit", f"unsupported length unit {unit_name}")
        unit = UNIT_METRES[unit_name]
        body = _obj(source.get("body"), "body")
        parts = _arr(body.get("parts"), "body.parts")
        sockets = _arr(body.get("sockets"), "body.sockets")
        joints = _arr(body.get("joints"), "body.joints")
        attachments = _arr(body.get("attachments"), "body.attachments")
        frames = _arr(body.get("frames", []), "body.frames")
        landmarks = _arr(body.get("landmarks", []), "body.landmarks")
        root = _find(parts, "tail_root", ["tail"], "root part")
        host = _find(sockets, "tail_mount", [], "host socket")
        mating = _find(sockets, "tail_mount", ["tail"], "mating socket")
        attachment = _find(attachments, "tail_mount", ["tail"], "attachment")
        authored = _transform(root.get("placement"), mapping, unit, "root.placement")
        host_transform = _transform(host.get("interface_frame"), mapping, unit, "host.interface_frame")
        offset_transform = _transform(attachment.get("offset"), mapping, unit, "attachment.offset")
        mating_transform = _transform(mating.get("interface_frame"), mapping, unit, "mating.interface_frame")
        target_provenance = {
            "attachment": _address(attachment.get("address"), "attachment.address"),
            "root": _address(root.get("address"), "root.address"),
            "host_socket": _address(host.get("address"), "host.address"),
            "mating_socket": _address(mating.get("address"), "mating.address"),
            "host_owner": _address(host.get("owner"), "host.owner"),
            "mating_owner": _address(mating.get("owner"), "mating.owner"),
            "offset": _value_transform(offset_transform),
        }
        zero_locations = _zero_quaternion_locations(source, mapping, parts, sockets, joints, attachments, frames)
        if zero_locations:
            return {
                "status": "typed-control",
                "metric": metric,
                "source_identity": _source_member(source),
                "I_truth": None,
                "authored_root_local": _value_transform(authored),
                "derived_root_local": None,
                "provenance": target_provenance,
                "equation": None,
                "domain": {"status": "typed-control", "reason": "zero-quaternion", "zero_quaternion_locations": zero_locations},
            }
        part_map = {_key(_obj(item, "part").get("address")): item for item in parts}
        cursor = _obj(mating.get("owner"), "mating.owner")
        path_nodes: list[dict[str, Any]] = []
        while _key(cursor) != _key(root.get("address")):
            node = part_map.get(_key(cursor))
            if node is None:
                _fail("source-shape", "containment path references missing part")
            path_nodes.append(node)
            parent = _obj(node.get("containment"), "part.containment").get("parent")
            cursor = _obj(parent, "containment.parent")
            if len(path_nodes) > len(parts):
                _fail("source-shape", "containment path did not reach root")
        path_nodes.reverse()
        path = IDENTITY
        for item in path_nodes:
            path = _compose(path, _transform(item.get("placement"), mapping, unit, "path.placement"))
        root_to_mating = _compose(path, mating_transform)
        derived = _compose(_compose(host_transform, offset_transform), _inverse(root_to_mating))
        domain = _domain(source, mapping, unit, parts, sockets, joints, attachments, frames, landmarks, path_nodes, authored, derived, host_transform, offset_transform, mating_transform)
        if domain["status"] != "admitted":
            truth: RationalInterval | None = None
            interval_witness: dict[str, Any] = {"kind": "not-scored-domain"}
        elif metric == "translation":
            discrepancy = max(abs(authored[0][i] - derived[0][i]) for i in range(3))
            truth = RationalInterval(discrepancy, discrepancy)
            interval_witness = {"kind": "exact", "metric": "translation-linf-metres"}
        else:
            truth, interval_witness = _rotation_interval(authored[1], derived[1])
        provenance = {
            **target_provenance,
            "root_to_mating_owner_path": [_address(item.get("address"), "path.address") for item in path_nodes],
        }
        equation = {
            "host_socket_local": _value_transform(host_transform),
            "mating_socket_local": _value_transform(mating_transform),
            "root_to_mating_owner_part_locals": [{"address": _address(item.get("address"), "path.address"), "local": _value_transform(_transform(item.get("placement"), mapping, unit, "path.placement"))} for item in path_nodes],
            "equation_steps": [
                {"operation": "attachment-containment", "output": _value_transform(path)},
                {"operation": "attachment-mating-socket", "output": _value_transform(root_to_mating)},
                {"operation": "attachment-host-offset", "output": _value_transform(_compose(host_transform, offset_transform))},
                {"operation": "attachment-inverse", "output": _value_transform(_inverse(root_to_mating))},
                {"operation": "attachment-equation", "output": _value_transform(derived)},
            ],
        }
        return {
            "status": domain["status"],
            "metric": metric,
            "source_identity": _source_member(source),
            "I_truth": None if truth is None else {**truth.as_dict(quantity="translation-linf-metres" if metric == "translation" else "normalized-q-neg-q-full-chord", method="exact-rational" if metric == "translation" else interval_witness["method"]), **interval_witness},
            "authored_root_local": _value_transform(authored),
            "derived_root_local": _value_transform(derived),
            "provenance": provenance,
            "equation": equation,
            "domain": domain,
        }
    except OracleError:
        raise
    except (Phase3Error, KeyError, TypeError, ValueError) as error:
        raise OracleIntegrityError(getattr(error, "code", "source-integrity"), str(error)) from error


def verify_sqrt_vectors(vectors: Sequence[Mapping[str, Any]] | Mapping[str, Any]) -> dict[str, Any]:
    """Verify a small in-memory sqrt fixture without reading its file."""
    if isinstance(vectors, Mapping):
        vectors = vectors.get("vectors")
    if not isinstance(vectors, Sequence) or isinstance(vectors, (str, bytes)):
        raise OracleError("sqrt-vectors", "vectors must be a sequence")
    checked = 0
    for index, vector in enumerate(vectors):
        if not isinstance(vector, Mapping):
            _fail("sqrt-vectors", f"vector {index} is not an object")
        raw_expected = vector.get("expected", vector.get("sqrt"))
        if isinstance(raw_expected, Mapping) and raw_expected.get("operation") == "root-scale":
            base = _fraction(vector.get("base_radicand"), f"vectors[{index}].base_radicand")
            scale = _fraction(vector.get("scale"), f"vectors[{index}].scale")
            scaled = _fraction(vector.get("scaled_radicand"), f"vectors[{index}].scaled_radicand")
            if scale < 0 or scaled != base * scale * scale:
                _fail("sqrt-vectors", f"vector {index} scale relation is invalid")
            checked += 1
            continue
        radicand = _fraction(vector.get("radicand"), f"vectors[{index}].radicand")
        lower, upper = directed_sqrt_bounds(radicand)
        expected = vector.get("expected", vector.get("sqrt"))
        if "exact_root" in vector:
            expected = {"lower": vector["exact_root"], "upper": vector["exact_root"]}
        elif "lower" in vector or "upper" in vector:
            expected = {"lower": vector.get("lower"), "upper": vector.get("upper")}
        if isinstance(expected, Mapping):
            # Metamorphic records carry an operation rather than a direct
            # bracket; their relation is checked below.
            expected_lower = _fraction(expected.get("lower"), f"vectors[{index}].expected.lower")
            expected_upper = _fraction(expected.get("upper"), f"vectors[{index}].expected.upper")
            if lower < expected_lower or upper > expected_upper:
                _fail("sqrt-vectors", f"vector {index} expected bracket does not contain implementation bound")
        checked += 1
    return {"checked": checked, "certified": True, "precision_bits": SQRT_PRECISION_BITS}


evaluate = evaluate_source
