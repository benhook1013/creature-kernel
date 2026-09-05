#!/usr/bin/env python3
"""Publish the already-sealed exact-five PNGs as a disposable review gallery."""

from __future__ import annotations

import argparse
import hashlib
import math
import struct
import tempfile
import zlib
from pathlib import Path
import sys
from typing import Any, NoReturn


VISUAL_REVIEW_ROOT = Path(__file__).resolve().parent
REPOSITORY_ROOT = VISUAL_REVIEW_ROOT.parents[1]
EXACT_FIVE_ROOT = REPOSITORY_ROOT / "experiments" / "owned-root-assembly-successor-exact-five"
NEUTRAL_ROOT = REPOSITORY_ROOT / "experiments" / "owned-root-assembly-successor"
if str(VISUAL_REVIEW_ROOT) not in sys.path:
    sys.path.insert(0, str(VISUAL_REVIEW_ROOT))
if str(EXACT_FIVE_ROOT) not in sys.path:
    sys.path.insert(0, str(EXACT_FIVE_ROOT))
if str(NEUTRAL_ROOT) not in sys.path:
    sys.path.insert(0, str(NEUTRAL_ROOT))

import common  # noqa: E402
from common import ValidationError, canonical_json  # noqa: E402
from publish import PublishError, publish_session  # noqa: E402
import artifact_serialization as artifacts  # noqa: E402
import exact_five_publisher as exact_five  # noqa: E402


class ExactFiveGalleryError(RuntimeError):
    """A bounded, fail-closed exact-five gallery error."""


REVIEW_ID = "owned-root-assembly-successor-exact-five-gallery"
TITLE = "Exact-five owned-root assembly visual review"
DESCRIPTION = (
    "Disposable visual review of the frozen exact-five surface render pairs. "
    "Publishing this gallery records no decision; Ben's appraisal of this exact "
    "candidate remains the merge checkpoint."
)
INSTRUCTIONS = (
    "For each ordered profile, compare the direct render with its lineage render. "
    "The standard neutral reference is first. Appraise the visible form and "
    "whether the two render paths agree. The gallery itself does not imply "
    "acceptance; Ben's approval or qualified feedback is required before merge."
)
PNG_WIDTH = 512
PNG_HEIGHT = 1536
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
MAX_PNG_BYTES = 2 * 1024 * 1024
MAX_JSON_BYTES = 16 * 1024 * 1024


def _fail(message: str) -> NoReturn:
    raise ExactFiveGalleryError(message)


def _keys(value: Any, required: set[str], where: str) -> dict[str, Any]:
    if not isinstance(value, dict) or not required <= set(value):
        missing = sorted(required - set(value)) if isinstance(value, dict) else sorted(required)
        _fail(f"{where} is missing required field(s): {', '.join(missing)}")
    return value


def _closed_keys(value: Any, expected: set[str], where: str) -> dict[str, Any]:
    result = _keys(value, expected, where)
    if set(result) != expected:
        _fail(f"{where} has unexpected field(s): {', '.join(sorted(set(result) - expected))}")
    return result


def _sha256(value: Any, where: str) -> str:
    if not isinstance(value, str) or len(value) != 64 or any(char not in "0123456789abcdef" for char in value):
        _fail(f"{where} is not lowercase SHA-256")
    return value


def _record(value: Any, where: str) -> dict[str, Any]:
    result = _closed_keys(value, {"role_path", "bytes", "sha256"}, where)
    try:
        artifacts.validate_role_path(result["role_path"])
    except Exception as exc:
        raise ExactFiveGalleryError(f"{where}.role_path is invalid") from exc
    if type(result["bytes"]) is not int or result["bytes"] < 0:
        _fail(f"{where}.bytes is invalid")
    _sha256(result["sha256"], f"{where}.sha256")
    return result


def _publisher_check(callback: Any, *args: Any) -> Any:
    try:
        return callback(*args)
    except Exception as exc:
        raise ExactFiveGalleryError(f"exact-five semantic admission failed: {exc}") from exc


def _local_record(record: dict[str, Any], role: str, where: str) -> dict[str, Any]:
    result = _record(record, where)
    if result["role_path"] != role:
        _fail(f"{where} has the wrong role")
    return result


def _same_file_identity(left: dict[str, Any], right: dict[str, Any]) -> bool:
    return left["bytes"] == right["bytes"] and left["sha256"] == right["sha256"]


PROFILE_EVIDENCE_KEYS = {
    "schema", "outcome", "activation_contract", "design_contract", "source", "profile_table",
    "existing_dependencies", "additive_implementation_files", "runtime",
    "runtime_fingerprint_sha256", "profile_id", "profile_index", "selection",
    "projected_values", "projected_carrier", "projection_bindings", "levels", "thresholds",
    "gates", "causality", "renders", "payloads", "invariants",
}
INVARIANTS = {
    "topology_equal_to_neutral": True,
    "formulas_equal_to_neutral": True,
    "tunables_equal_to_neutral": True,
    "thresholds_equal_to_neutral": True,
    "gate_inventory_equal_to_neutral": True,
    "subdivision_equal_to_neutral": True,
    "ownership_equal_to_neutral": True,
    "causality_rules_equal_to_neutral": True,
    "renderer_equal_to_neutral": True,
}
GATE_CARDINALITIES = {"structural": 122, "continuity": 144, "anatomy": 78, "intersection": 12}


def _validate_managed_tests(value: Any, identity: dict[str, Any]) -> None:
    managed = _closed_keys(value, {"receipt_sha256", "receipt"}, "managed tests")
    receipt = managed["receipt"]
    receipt_raw = artifacts.canonical_json_bytes(receipt)
    if managed["receipt_sha256"] != artifacts.sha256_bytes(receipt_raw):
        _fail("managed-test receipt hash differs")
    _publisher_check(
        exact_five._new_receipt,
        receipt,
        receipt_raw,
        Path("managed-test-receipt.json"),
        identity,
    )


def _validate_profile_evidence(
    root: Path,
    profile: dict[str, Any],
    index: int,
    identity: dict[str, Any],
    table: list[dict[str, Any]],
    public_records: dict[str, dict[str, Any]],
    frozen_thresholds: list[dict[str, Any]] | None,
    frozen_gate_ids: dict[str, list[str]] | None,
) -> tuple[list[dict[str, Any]], dict[str, list[str]], dict[str, dict[str, Any]], bytes]:
    profile_id = exact_five.PROFILES[index]
    _closed_keys(
        profile,
        {"profile_id", "profile_index", "evidence", "stable_cross_seed_comparisons", "neutral_payload_comparisons"},
        f"profile {profile_id}",
    )
    if profile["profile_id"] != profile_id or profile["profile_index"] != index:
        _fail(f"profile {profile_id} identity/order differs")
    nested = _closed_keys(profile["evidence"], PROFILE_EVIDENCE_KEYS, f"profile {profile_id} evidence")
    if not (
        nested["schema"] == "owned-root-assembly-successor-profile-seed-evidence.v1"
        and nested["outcome"] == "success"
        and nested["profile_id"] == profile_id
        and nested["profile_index"] == index
        and nested["activation_contract"] == identity["activation"]
        and nested["design_contract"] == identity["design"]
        and nested["source"] == identity["source"]
        and nested["profile_table"] == identity["profile"]
        and nested["existing_dependencies"] == identity["dependencies"]
        and nested["additive_implementation_files"] == identity["additive_files"]
        and nested["runtime"] == identity["runtime"]
        and nested["runtime_fingerprint_sha256"] == identity["runtime_sha"]
    ):
        _fail(f"profile {profile_id} frozen provenance differs")

    row = table[index]
    selection = _closed_keys(
        nested["selection"],
        {"profile_pointer", "profile_row_sha256", "dimension_scales_sha256", "part_placements_sha256"},
        f"profile {profile_id} selection",
    )
    expected_selection = {
        "profile_pointer": f"/profiles/{index}",
        "profile_row_sha256": artifacts.sha256_bytes(artifacts.canonical_json_bytes(row)),
        "dimension_scales_sha256": artifacts.sha256_bytes(artifacts.canonical_json_bytes(row["dimension_scales"])),
        "part_placements_sha256": artifacts.sha256_bytes(artifacts.canonical_json_bytes(row["part_placements"])),
    }
    if selection != expected_selection:
        _fail(f"profile {profile_id} selection does not bind the frozen profile row")

    values, bindings = nested["projected_values"], nested["projection_bindings"]
    if not (
        isinstance(values, list) and isinstance(bindings, list)
        and [item.get("prepared_component") for item in values if isinstance(item, dict)] == list(exact_five.COMPONENT_IDS)
        and [item.get("prepared_component") for item in bindings if isinstance(item, dict)] == list(exact_five.COMPONENT_IDS)
    ):
        _fail(f"profile {profile_id} projection inventory differs")
    for position, (value, binding) in enumerate(zip(values, bindings)):
        _closed_keys(value, {"prepared_component", "value", "source_pointers", "profile_pointers"}, f"profile {profile_id} projected value {position}")
        _closed_keys(binding, {"prepared_component", "derivation_id", "source_addresses", "source_pointers", "profile_pointers"}, f"profile {profile_id} projection binding {position}")
        try:
            binary_value = artifacts.coerce_binary64(value["value"], label="projected value")
        except Exception as exc:
            raise ExactFiveGalleryError(f"profile {profile_id} projected value {position} is invalid") from exc
        if not (
            value["prepared_component"] == binding["prepared_component"]
            and binary_value == value["value"]
            and value["source_pointers"] == binding["source_pointers"]
            and value["profile_pointers"] == binding["profile_pointers"]
            and binding["derivation_id"] in (
                "profile.dimension-permille-half-even-mm.v1",
                "profile.world-placement-axis-sum.v1",
                "profile.world-landmark-axis-sum.v1",
            )
        ):
            _fail(f"profile {profile_id} projection binding {position} differs")
        _publisher_check(exact_five._pointers, value["source_pointers"], "source pointers")
        _publisher_check(exact_five._pointers, value["profile_pointers"], "profile pointers")
        _publisher_check(exact_five._addresses, binding["source_addresses"], "source addresses")
        if not all(pointer.startswith(f"/profiles/{index}/") for pointer in value["profile_pointers"]):
            _fail(f"profile {profile_id} projection selects another profile")
    carrier_raw = artifacts.canonical_json_bytes([item["value"] for item in values])
    if nested["projected_carrier"] != {"bytes": len(carrier_raw), "sha256": artifacts.sha256_bytes(carrier_raw)}:
        _fail(f"profile {profile_id} projected carrier differs")

    nested_payloads = nested["payloads"]
    if not isinstance(nested_payloads, list) or [item.get("role_path") if isinstance(item, dict) else None for item in nested_payloads] != list(exact_five.PAYLOAD_ROLES):
        _fail(f"profile {profile_id} payload inventory differs")
    payload_map = {item["role_path"]: _record(item, f"profile {profile_id} payload") for item in nested_payloads}

    levels = nested["levels"]
    if not isinstance(levels, list) or [item.get("level") if isinstance(item, dict) else None for item in levels] != [0, 1, 2]:
        _fail(f"profile {profile_id} level inventory differs")
    for level, level_row in enumerate(levels):
        _closed_keys(level_row, {"level", "counts", "coordinate_bytes", "coordinate_sha256", "triangle_index_bytes", "triangle_index_sha256", "ply"}, f"profile {profile_id} level {level}")
        counts = exact_five.neutral.LEVEL_COUNTS[level]
        expected_counts = {"level": level, "vertices": counts[0], "edges": counts[1], "quads": counts[2], "triangles": counts[3], "boundary_edges": counts[4]}
        local_role = f"surface-level-{level}.ply"
        if level_row["counts"] != expected_counts or level_row["ply"] != payload_map[local_role]:
            _fail(f"profile {profile_id} level {level} identity differs")
        if type(level_row["coordinate_bytes"]) is not int or level_row["coordinate_bytes"] <= 0 or type(level_row["triangle_index_bytes"]) is not int or level_row["triangle_index_bytes"] <= 0:
            _fail(f"profile {profile_id} level {level} digest sizes differ")
        _sha256(level_row["coordinate_sha256"], "coordinate hash")
        _sha256(level_row["triangle_index_sha256"], "triangle hash")
        if level == 2:
            public = public_records[f"{profile_id}/{local_role}"]
            if not _same_file_identity(level_row["ply"], public):
                _fail(f"profile {profile_id} public PLY is not bound to level 2")
            _, _, coordinates, triangles = _publisher_check(
                exact_five._ply_digest, root / profile_id / local_role, f"{profile_id}/{local_role}", 2
            )
            if coordinates != {"bytes": level_row["coordinate_bytes"], "sha256": level_row["coordinate_sha256"]} or triangles != {"bytes": level_row["triangle_index_bytes"], "sha256": level_row["triangle_index_sha256"]}:
                _fail(f"profile {profile_id} public PLY geometry digest differs")

    thresholds = nested["thresholds"]
    if frozen_thresholds is None:
        _publisher_check(exact_five._threshold_shape, thresholds, "profile thresholds")
        frozen_thresholds = thresholds
    else:
        _publisher_check(exact_five._thresholds, thresholds, frozen_thresholds, "profile thresholds")
    gates = _closed_keys(nested["gates"], set(GATE_CARDINALITIES), f"profile {profile_id} gates")
    gate_ids = {group: [item.get("gate_id") if isinstance(item, dict) else None for item in gates[group]] for group in GATE_CARDINALITIES}
    if any(len(gates[group]) != count for group, count in GATE_CARDINALITIES.items()):
        _fail(f"profile {profile_id} gate cardinality differs")
    if frozen_gate_ids is not None and gate_ids != frozen_gate_ids:
        _fail(f"profile {profile_id} gate inventory differs from neutral")
    for group in GATE_CARDINALITIES:
        _publisher_check(exact_five._gate_rows, gates[group], gate_ids[group], thresholds, f"profile {profile_id} {group}")

    causality = nested["causality"]
    expected_parameters = sorted(exact_five.CAUSAL_COMPONENTS, key=str.encode)
    if not isinstance(causality, list) or [item.get("parameter_id") if isinstance(item, dict) else None for item in causality] != expected_parameters:
        _fail(f"profile {profile_id} causality inventory differs")
    for position, item in enumerate(causality):
        _closed_keys(item, {"parameter_id", "prepared_component", "delta_m", "support_level", "predicted_support_count", "observed_support_count", "predicted_support_sha256", "observed_support_sha256", "maximum_movement_m", "artifact"}, f"profile {profile_id} causality {position}")
        parameter = item["parameter_id"]
        artifact_role = f"perturb-{parameter.replace('.', '-')}.ply"
        movement = item["maximum_movement_m"]
        if not (
            item["prepared_component"] == exact_five.CAUSAL_COMPONENTS[parameter]
            and item["delta_m"] == 0.01 and item["support_level"] == 2
            and type(item["predicted_support_count"]) is int
            and 0 < item["predicted_support_count"] <= 1737
            and item["predicted_support_count"] == item["observed_support_count"]
            and item["predicted_support_sha256"] == item["observed_support_sha256"]
            and type(movement) is float and math.isfinite(movement)
            and movement >= float.fromhex("0x1.d14e3bcd35a85p-11")
            and item["artifact"] == payload_map[artifact_role]
        ):
            _fail(f"profile {profile_id} causality {position} differs")
        _sha256(item["predicted_support_sha256"], "causality support hash")

    renders = _closed_keys(nested["renders"], {"renderer_id", "render_config", "render_config_sha256", "visibility", "visibility_sha256", "direct", "lineage", "same_surface_positions_sha256", "same_surface_triangles_sha256"}, f"profile {profile_id} renders")
    _publisher_check(exact_five.render.validate_render_config, renders["render_config"])
    visibility = _closed_keys(renders["visibility"], {"level", "triangle_count", "triangle_index_sha256", "rule"}, f"profile {profile_id} visibility")
    if not (
        renders["renderer_id"] == "owned-root-raster-pillow-11.1.0.v1"
        and renders["render_config_sha256"] == artifacts.sha256_bytes(artifacts.canonical_json_bytes(renders["render_config"]))
        and renders["visibility_sha256"] == artifacts.sha256_bytes(artifacts.canonical_json_bytes(visibility))
        and visibility == {"level": 2, "triangle_count": 3328, "triangle_index_sha256": levels[2]["triangle_index_sha256"], "rule": "larger-depth-then-lower-triangle-index"}
        and renders["same_surface_positions_sha256"] == levels[2]["coordinate_sha256"]
        and renders["same_surface_triangles_sha256"] == levels[2]["triangle_index_sha256"]
        and renders["direct"] == payload_map["direct.png"]
        and renders["lineage"] == payload_map["lineage.png"]
    ):
        _fail(f"profile {profile_id} render/surface identity differs")
    if nested["invariants"] != INVARIANTS:
        _fail(f"profile {profile_id} invariant evidence differs")

    for render_kind in ("direct", "lineage"):
        local = renders[render_kind]
        public_role = f"{profile_id}/{render_kind}.png"
        public = public_records[public_role]
        if not _same_file_identity(local, public):
            _fail(f"profile {profile_id} {render_kind} render is not bound to the public PNG")
        data = _validate_png(root / public_role, public_role)
        if len(data) != public["bytes"] or hashlib.sha256(data).hexdigest() != public["sha256"]:
            _fail(f"profile {profile_id} {render_kind} PNG changed after evidence admission")

    nested_raw = artifacts.canonical_json_bytes(nested)
    nested_record = {"role_path": "profile-seed-evidence.json", "bytes": len(nested_raw), "sha256": artifacts.sha256_bytes(nested_raw)}
    nested_sidecar = f"{nested_record['sha256']}  profile-seed-evidence.json\n".encode("ascii")
    expected_stable = dict(payload_map)
    expected_stable["profile-seed-evidence.json"] = nested_record
    expected_stable["profile-seed-evidence.sha256"] = {"role_path": "profile-seed-evidence.sha256", "bytes": len(nested_sidecar), "sha256": artifacts.sha256_bytes(nested_sidecar)}
    stable = profile["stable_cross_seed_comparisons"]
    if not isinstance(stable, list) or [item.get("role_path") if isinstance(item, dict) else None for item in stable] != list(exact_five.BUNDLE_STABLE_ROLES):
        _fail(f"profile {profile_id} stable comparison inventory differs")
    if stable != [expected_stable[role] for role in exact_five.BUNDLE_STABLE_ROLES]:
        _fail(f"profile {profile_id} stable comparisons are not bound to seed evidence")
    return frozen_thresholds, gate_ids, payload_map, nested_raw


def _read_json(path: Path, where: str, *, max_bytes: int = MAX_JSON_BYTES) -> tuple[dict[str, Any], bytes]:
    try:
        raw = artifacts.read_regular_file(path, max_bytes=max_bytes)
        value = artifacts.decode_canonical_json(raw)
    except Exception as exc:
        raise ExactFiveGalleryError(f"{where} is not canonical JSON") from exc
    if not isinstance(value, dict):
        _fail(f"{where} is not an object")
    return value, raw


def _validate_png(path: Path, role: str) -> bytes:
    try:
        data = artifacts.read_regular_file(path, max_bytes=MAX_PNG_BYTES)
    except Exception as exc:
        raise ExactFiveGalleryError(f"{role} cannot be read") from exc
    if not data.startswith(PNG_SIGNATURE):
        _fail(f"{role} is not a PNG")
    offset = len(PNG_SIGNATURE)
    chunk_names: list[bytes] = []
    idat = bytearray()
    while offset < len(data):
        if len(data) - offset < 12:
            _fail(f"{role} has a truncated PNG chunk")
        length = struct.unpack(">I", data[offset : offset + 4])[0]
        chunk_type = data[offset + 4 : offset + 8]
        end = offset + 12 + length
        if end > len(data):
            _fail(f"{role} has a truncated PNG payload")
        payload = data[offset + 8 : offset + 8 + length]
        expected_crc = struct.unpack(">I", data[offset + 8 + length : end])[0]
        if zlib.crc32(chunk_type + payload) & 0xFFFFFFFF != expected_crc:
            _fail(f"{role} has an invalid PNG CRC")
        chunk_names.append(chunk_type)
        if chunk_type == b"IHDR":
            if len(payload) != 13:
                _fail(f"{role} has an invalid IHDR")
            width, height, depth, colour, compression, filtering, interlace = struct.unpack(
                ">IIBBBBB", payload
            )
            if (width, height, depth, colour, compression, filtering, interlace) != (
                PNG_WIDTH,
                PNG_HEIGHT,
                8,
                2,
                0,
                0,
                0,
            ):
                _fail(f"{role} PNG dimensions or colour format differ")
        elif chunk_type == b"IDAT":
            idat.extend(payload)
        elif chunk_type == b"IEND":
            if length != 0 or end != len(data):
                _fail(f"{role} has trailing or malformed IEND data")
        else:
            _fail(f"{role} contains unexpected PNG chunk {chunk_type!r}")
        offset = end
        if chunk_type == b"IEND":
            break
    if chunk_names != [b"IHDR", b"IDAT", b"IEND"] or not idat:
        _fail(f"{role} has an incomplete PNG structure")
    try:
        decompressor = zlib.decompressobj()
        decoded = decompressor.decompress(bytes(idat), PNG_HEIGHT * (1 + PNG_WIDTH * 3) + 1)
    except zlib.error as exc:
        raise ExactFiveGalleryError(f"{role} contains invalid image data") from exc
    expected_raw_bytes = PNG_HEIGHT * (1 + PNG_WIDTH * 3)
    if (
        len(decoded) != expected_raw_bytes
        or decompressor.unconsumed_tail
        or decompressor.unused_data
        or not decompressor.eof
        or any(decoded[index] > 4 for index in range(0, len(decoded), PNG_WIDTH * 3 + 1))
    ):
        _fail(f"{role} contains invalid RGB scanline data")
    return data


def _refuse_existing_destination(reviews_root: Path, review_id: str) -> None:
    if reviews_root.is_symlink() or not reviews_root.is_dir():
        _fail("reviews root must already exist as a regular directory")
    destination = reviews_root / review_id
    if destination.is_symlink():
        _fail("refusing existing destination symlink")
    if destination.exists():
        _fail("refusing to overwrite existing destination")


def validate_exact_five_root(root: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, dict[str, Any]], bytes, bytes]:
    """Re-admit the sealed public root without invoking any generator."""

    root = root.absolute()
    identity = _publisher_check(exact_five._static)
    table = _publisher_check(exact_five._table, identity)
    try:
        inventory = artifacts.closed_inventory(root, exact_five.PUBLIC_ROLES, max_file_bytes=MAX_JSON_BYTES)
    except Exception as exc:
        raise ExactFiveGalleryError(f"exact-five root is not the closed public layout: {exc}") from exc
    by_role = {item["role_path"]: item for item in inventory}
    evidence, evidence_raw = _read_json(root / "exact-five-evidence.json", "exact-five evidence")
    sidecar = artifacts.read_regular_file(root / "exact-five-evidence.sha256", max_bytes=256)
    expected_sidecar = f"{artifacts.sha256_bytes(evidence_raw)}  exact-five-evidence.json\n".encode("ascii")
    if sidecar != expected_sidecar:
        _fail("exact-five evidence sidecar does not bind the evidence bytes")
    report, report_raw = _read_json(root / "run-report.json", "exact-five run report", max_bytes=2 * 1024 * 1024)
    report_sidecar = artifacts.read_regular_file(root / "run-report.sha256", max_bytes=256)
    if report_sidecar != f"{artifacts.sha256_bytes(report_raw)}  run-report.json\n".encode("ascii"):
        _fail("exact-five run-report sidecar does not bind the report bytes")

    _closed_keys(evidence, {
        "schema", "outcome", "activation_contract", "design_contract", "source", "profile_table",
        "existing_dependencies", "additive_implementation_files", "managed_tests", "neutral_baseline",
        "runtime", "runtime_fingerprint_sha256", "profile_order", "profiles", "payloads",
    }, "exact-five evidence")
    if not (
        evidence["schema"] == "owned-root-assembly-successor-exact-five-evidence.v1"
        and evidence["outcome"] == "success"
        and evidence["activation_contract"] == identity["activation"]
        and evidence["design_contract"] == identity["design"]
        and evidence["source"] == identity["source"]
        and evidence["profile_table"] == identity["profile"]
        and evidence["existing_dependencies"] == identity["dependencies"]
        and evidence["additive_implementation_files"] == identity["additive_files"]
        and evidence["runtime"] == identity["runtime"]
        and evidence["runtime_fingerprint_sha256"] == identity["runtime_sha"]
    ):
        _fail("exact-five evidence is not a successful exact-five publication")
    if evidence["profile_order"] != list(exact_five.PROFILES):
        _fail("exact-five evidence profile order is not neutral-first")
    _validate_managed_tests(evidence["managed_tests"], identity)

    neutral = _closed_keys(
        evidence["neutral_baseline"],
        {"comparison_report", "stable_manifest_sha256", "runtime_fingerprint_sha256", "payload_comparisons"},
        "neutral baseline",
    )
    comparison = _local_record(neutral["comparison_report"], "comparison-report.json", "neutral comparison report")
    if not (
        comparison["sha256"] == exact_five.BASELINE_REPORT_SHA
        and neutral["stable_manifest_sha256"] == exact_five.BASELINE_STABLE_SHA
        and neutral["runtime_fingerprint_sha256"] == identity["runtime_sha"]
    ):
        _fail("neutral baseline frozen identity differs")
    neutral_comparisons = neutral["payload_comparisons"]
    if not isinstance(neutral_comparisons, list) or [item.get("role_path") if isinstance(item, dict) else None for item in neutral_comparisons] != list(exact_five.PAYLOAD_ROLES):
        _fail("neutral baseline payload comparison inventory differs")
    for position, item in enumerate(neutral_comparisons):
        _record(item, f"neutral payload comparison {position}")

    _closed_keys(report, {
        "schema", "outcome", "literal_invocation", "output_path", "staging_path", "python_executable_path",
        "neutral_baseline_path", "started_utc", "finished_utc", "timings", "activation_contract_sha256",
        "design_contract_sha256", "runtime_fingerprint_sha256", "evidence", "evidence_sidecar", "payloads",
        "profile_seed_runs", "gates",
    }, "exact-five run report")
    if not (
        report["schema"] == "owned-root-assembly-successor-exact-five-run-report.v1"
        and report["outcome"] == "success"
        and report["activation_contract_sha256"] == exact_five.ACTIVATION_SHA
        and report["design_contract_sha256"] == exact_five.DESIGN_SHA
        and report["runtime_fingerprint_sha256"] == identity["runtime_sha"]
    ):
        _fail("exact-five run report is not successful")
    evidence_record = by_role["exact-five-evidence.json"]
    evidence_ref = {**evidence_record, "schema": evidence["schema"]}
    if (
        report["evidence"] != evidence_ref
        or report["evidence_sidecar"] != by_role["exact-five-evidence.sha256"]
        or report["payloads"] != evidence["payloads"]
    ):
        _fail("exact-five run report does not bind the evidence inventory")

    payloads = evidence["payloads"]
    if not isinstance(payloads, list) or [item.get("role_path") if isinstance(item, dict) else None for item in payloads] != list(exact_five.PUBLIC_PAYLOAD_ROLES):
        _fail("exact-five evidence payload inventory is not the frozen public order")
    for index, item in enumerate(payloads):
        item_record = _record(item, f"exact-five evidence.payloads[{index}]")
        if by_role.get(item_record["role_path"]) != item_record:
            _fail(f"exact-five evidence payload is not bound to the root: {item_record['role_path']}")

    profiles = evidence["profiles"]
    if not isinstance(profiles, list) or len(profiles) != len(exact_five.PROFILES):
        _fail("exact-five evidence does not contain five profiles")
    png_records: dict[str, dict[str, Any]] = {}
    frozen_thresholds: list[dict[str, Any]] | None = None
    frozen_gate_ids: dict[str, list[str]] | None = None
    nested_raw_by_profile: dict[str, bytes] = {}
    for index, profile in enumerate(profiles):
        profile_id = exact_five.PROFILES[index]
        frozen_thresholds, admitted_gate_ids, payload_map, nested_raw = _validate_profile_evidence(
            root, profile, index, identity, table, by_role, frozen_thresholds, frozen_gate_ids
        )
        if frozen_gate_ids is None:
            frozen_gate_ids = admitted_gate_ids
        nested_raw_by_profile[profile_id] = nested_raw
        neutral_rows = profile["neutral_payload_comparisons"]
        if index == 0:
            if neutral_rows != neutral_comparisons or neutral_rows != [payload_map[role] for role in exact_five.PAYLOAD_ROLES]:
                _fail("standard-neutral payload comparisons do not bind the neutral profile")
        elif neutral_rows != []:
            _fail(f"profile {profile_id} unexpectedly carries neutral payload comparisons")
        for render_kind in ("direct", "lineage"):
            role = f"{profile_id}/{render_kind}.png"
            png_records[role] = by_role[role]
    expected_seed_runs = [
        {
            "profile_id": profile["profile_id"],
            "seed": seed,
            "outcome": "success",
            "evidence_sha256": artifacts.sha256_bytes(
                nested_raw_by_profile[profile["profile_id"]]
            ),
        }
        for profile in profiles
        for seed in exact_five.SEEDS
    ]
    if report["profile_seed_runs"] != expected_seed_runs:
        _fail("exact-five run report profile/seed inventory is not bound to evidence")
    final_gate_ids = tuple(getattr(exact_five, "FINAL_GATE_IDS", ()))
    expected_final_gates = [
        {"gate_id": gate, "outcome": "pass", "sample_count": 1, "observed_min": 1, "observed_max": 1, "threshold_id": "gate.boolean-pass"}
        for gate in final_gate_ids
    ]
    if not final_gate_ids:
        final_gate_ids = tuple(
            ["exact-five.run.01.identity", "exact-five.run.02.managed-tests", "exact-five.run.03.publisher-baseline-admission"]
            + [f"exact-five.run.{4 + index * 2 + offset:02d}.profile.{profile}.seed-{seed}" for index, profile in enumerate(exact_five.PROFILES) for offset, seed in enumerate(exact_five.SEEDS)]
            + [f"exact-five.run.{14 + index:02d}.profile.{profile}.cross-seed" for index, profile in enumerate(exact_five.PROFILES)]
            + ["exact-five.run.19.standard-neutral-payload-equality", "exact-five.run.20.evidence-graph", "exact-five.run.21.pre-report-closure"]
        )
        expected_final_gates = [
            {"gate_id": gate, "outcome": "pass", "sample_count": 1, "observed_min": 1, "observed_max": 1, "threshold_id": "gate.boolean-pass"}
            for gate in final_gate_ids
        ]
    if report["gates"] != expected_final_gates:
        _fail("exact-five final gate inventory is not the frozen all-pass set")
    return evidence, report, png_records, evidence_raw, report_raw


def _profile_title(profile_id: str) -> str:
    return profile_id.replace("_", " ").title()


def _build_review_manifest(
    exact_root: Path,
    review_id: str,
    evidence: dict[str, Any],
    report: dict[str, Any],
    png_records: dict[str, dict[str, Any]],
    evidence_raw: bytes,
    report_raw: bytes,
) -> tuple[dict[str, Any], dict[str, dict[str, int | str]]]:
    groups: list[dict[str, Any]] = []
    expected_sources: dict[str, dict[str, int | str]] = {}
    for profile_id in exact_five.PROFILES:
        items: list[dict[str, Any]] = []
        for render_kind in ("direct", "lineage"):
            item_id = f"{profile_id}__{render_kind}"
            role = f"{profile_id}/{render_kind}.png"
            artifact = png_records[role]
            item = {
                "id": item_id,
                "title": render_kind.title(),
                "source": str((exact_root / role).absolute()),
                "description": f"{render_kind.title()} exact-five render for the {_profile_title(profile_id)} profile.",
                "metadata": {
                    "profile_id": profile_id,
                    "render_kind": render_kind,
                    "artifact": {**artifact, "width": PNG_WIDTH, "height": PNG_HEIGHT, "mode": "RGB"},
                    "exact_five_evidence_sha256": artifacts.sha256_bytes(evidence_raw),
                    "exact_five_run_report_sha256": artifacts.sha256_bytes(report_raw),
                },
            }
            items.append(item)
            expected_sources[item_id] = {"bytes": artifact["bytes"], "sha256": artifact["sha256"]}
        groups.append({
            "id": profile_id,
            "title": _profile_title(profile_id),
            "description": "Compare the direct and lineage renders for this exact-five profile.",
            "selection_mode": "none",
            "items": items,
        })
    review = {
        "schema_version": 1,
        "id": review_id,
        "title": TITLE,
        "description": DESCRIPTION,
        "instructions": INSTRUCTIONS,
        "kind": "image",
        "subject_context": {
            "authored_summary": {
                "text": "Five ordered exact-five profiles, each shown as direct and lineage renders of the already-published surface."
            },
            "descriptor_snapshot": {
                "format": evidence["schema"],
                "profile_order": list(exact_five.PROFILES),
                "render_order": ["direct", "lineage"],
                "image_count": 10,
                "canvas": {"width": PNG_WIDTH, "height": PNG_HEIGHT, "mode": "RGB"},
                "exact_five_evidence_sha256": artifacts.sha256_bytes(evidence_raw),
                "exact_five_run_report_sha256": artifacts.sha256_bytes(report_raw),
                "activation_contract_sha256": (
                    evidence.get("activation_contract", {}).get("sha256")
                    if isinstance(evidence.get("activation_contract"), dict)
                    else None
                ),
            },
            "provenance": {
                "source": "already-published exact-five public root",
                "evidence_sha256": artifacts.sha256_bytes(evidence_raw),
                "run_report_sha256": artifacts.sha256_bytes(report_raw),
            },
        },
        "groups": groups,
    }
    return review, expected_sources


def publish_exact_five_gallery(
    reviews_root: Path,
    exact_root: Path,
    *,
    review_id: str = REVIEW_ID,
) -> dict[str, Any]:
    try:
        review_id = common.validate_id(review_id, "review id")
    except ValidationError as exc:
        _fail(str(exc))
    _refuse_existing_destination(reviews_root, review_id)
    exact_root = exact_root.absolute()
    evidence, report, png_records, evidence_raw, report_raw = validate_exact_five_root(exact_root)
    review, expected_sources = _build_review_manifest(
        exact_root, review_id, evidence, report, png_records, evidence_raw, report_raw
    )
    try:
        with tempfile.TemporaryDirectory(prefix="ck-exact-five-gallery-") as temporary:
            manifest_path = Path(temporary) / "review-manifest.json"
            manifest_path.write_text(canonical_json(review), encoding="utf-8", newline="\n")
            summary = publish_session(
                reviews_root,
                manifest_path,
                expected_sources=expected_sources,
            )
    except (ValidationError, PublishError, OSError) as exc:
        raise ExactFiveGalleryError(f"could not publish exact-five gallery: {exc}") from exc
    return {**summary, "kind": "exact-five-gallery", "profiles": len(exact_five.PROFILES), "images": 2 * len(exact_five.PROFILES)}


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, type=Path, help="existing visual-review root")
    parser.add_argument("--exact-five-root", required=True, type=Path, help="already-published exact-five public root")
    parser.add_argument("--id", dest="review_id", default=REVIEW_ID)
    return parser


def main(argv: list[str] | None = None) -> int:
    try:
        args = _parser().parse_args(argv)
        summary = publish_exact_five_gallery(args.root, args.exact_five_root, review_id=args.review_id)
    except (ExactFiveGalleryError, ValidationError, PublishError, OSError) as exc:
        print(f"publish-exact-five-gallery failed: {exc}", file=sys.stderr)
        return 2
    print(canonical_json(summary), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
