"""Path-neutral publisher for the frozen exact-five activation."""
from __future__ import annotations

import importlib.metadata
import importlib.util
import io
import json
import locale
import math
import os
import platform
import re
import struct
import sys
import sysconfig
import time
import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
NEUTRAL = ROOT / "experiments/owned-root-assembly-successor"
PACKAGE = ROOT / "experiments/owned-root-assembly-successor-exact-five"
sys.path.insert(0, str(NEUTRAL))
import artifact_serialization as artifacts  # noqa: E402
import build_owned_root as neutral  # noqa: E402
import render_export as render  # noqa: E402

ACTIVATION_ROLE = "experiments/owned-root-assembly-successor/exact-five-activation-contract.md"
ACTIVATION_SHA = "a5c38645c810efb24e79297fb7c8049f0f59529f37a67c18a5a728a7119f0d49"
DESIGN_ROLE = "experiments/owned-root-assembly-successor/design-contract.md"
DESIGN_SHA = "3122f0db2235754ed782bd38a88c4d7ad7cc7edbf635d147194f1e93f8556490"
SOURCE_ROLE = "examples/body-documents/stylized-digitigrade-biped-authored-form.json"
SOURCE_SHA = "82269e843555ff1aad3c66399e3fcaeb11bbee81d72b69d15765ea9c4e7aff14"
PROFILE_ROLE = "experiments/current-form-surface-preview/structural_profile_candidates.json"
PROFILE_SHA = "a5fba6643d0031bac83c08e9093e11fd7945806963509fa939865866112d9640"
RUNTIME_SHA = "c19ca9c0b8268504f93513d55f90a0eb63777e566aba06e376b503c5e648f085"
BASELINE_REPORT_SHA = "fe450e9047275c517de297f50b9ed7881c969fd2c315e9714334dcb8d9e68f2a"
BASELINE_REPORT_SIDE_SHA = "27d4941acc57c9a800c2ee76205dd349f401f900d6ed0ee01b3d07925df85dac"
BASELINE_STABLE_SHA = "1b4aaed96671a55ae65dc163fd80db45288daf1b9dc9c91745bf19e414fa7ffa"
BUILDER_ROLE = "experiments/owned-root-assembly-successor/build_owned_root.py"
COMPARATOR_ROLE = "experiments/owned-root-assembly-successor/compare_two_seed_outputs.py"
LAUNCHER_ROLE = "experiments/owned-root-assembly-successor-exact-five/exact_five_launcher.sh"
RUNNER_ROLE = "experiments/owned-root-assembly-successor-exact-five/exact_five_runner.py"
PUBLISHER_ROLE = "experiments/owned-root-assembly-successor-exact-five/exact_five_publisher.py"
ADDITIVE_ROLES = tuple(sorted((LAUNCHER_ROLE, RUNNER_ROLE, PUBLISHER_ROLE,
                               "experiments/owned-root-assembly-successor-exact-five/tests/test_exact_five_activation.py"), key=str.encode))
PROFILES = ("standard_neutral_reference", "compact_broad_short_limb_large_head", "tall_narrow_long_legged", "slender_long_limb", "stocky_broad_chested")
SEEDS = (17, 29)
PAYLOAD_ROLES = tuple(sorted(set(neutral.ARTIFACT_ROLES) - {"input-manifest.json", "coordinate-manifest.json", "gate-manifest.json", "causality-manifest.json", "render-manifest.json", "stable-manifest.json", "prepared-input.json", "report.json", "report.sha256"}, key=str.encode))
BASELINE_STABLE_ROLES = tuple(sorted(set(neutral.ARTIFACT_ROLES) - {"report.json", "report.sha256"}, key=str.encode))
BUNDLE_ROLES = tuple(sorted((*PAYLOAD_ROLES, "profile-seed-evidence.json", "profile-seed-evidence.sha256", "run-report.json", "run-report.sha256"), key=str.encode))
BUNDLE_STABLE_ROLES = tuple(sorted((*PAYLOAD_ROLES, "profile-seed-evidence.json", "profile-seed-evidence.sha256"), key=str.encode))
PUBLIC_PAYLOAD_ROLES = tuple(sorted(tuple(f"{profile}/surface-level-2.ply" for profile in PROFILES) + tuple(f"{profile}/{role}" for profile in PROFILES for role in ("direct.png", "lineage.png")), key=str.encode))
PUBLIC_ROLES = tuple(sorted((*PUBLIC_PAYLOAD_ROLES, "exact-five-evidence.json", "exact-five-evidence.sha256", "run-report.json", "run-report.sha256"), key=str.encode))
PRE_REPORT_ROLES = tuple(sorted((*PUBLIC_PAYLOAD_ROLES, "exact-five-evidence.json", "exact-five-evidence.sha256"), key=str.encode))
BASELINE_ROLES = tuple(sorted((*[f"seed-{seed}/{role}" for seed in SEEDS for role in neutral.ARTIFACT_ROLES], "comparison/comparison-report.json", "comparison/comparison-report.sha256"), key=str.encode))
COMPONENT_IDS = tuple(sorted(tuple(f"stations.{station}.{field}" for station in ("lower_pelvis", "upper_pelvis", "lower_abdomen", "waist_abdomen", "upper_abdomen", "lower_ribcage", "upper_ribcage_shoulder", "neck_collar", "neck_upper") for field in ("C.x", "C.y", "C.z", "rL", "rA", "rP")) + tuple(f"shoulders.{side}.{field}" for side in ("left", "right") for field in ("axilla.x", "axilla.y", "axilla.z", "peak.x", "peak.y", "peak.z", "arm_origin.x", "arm_origin.y", "arm_origin.z", "start_lateral", "start_up", "start_forward", "shoulder_depth")) + tuple(f"hips.{side}.{field}" for side in ("left", "right") for field in ("P_s.x", "P_s.y", "P_s.z", "r_x", "r_y", "r_z")), key=str.encode))
CAUSAL_COMPONENTS = {"left.r_y": "hips.left.r_y", "right.r_y": "hips.right.r_y", "lower_pelvis.L_y": "stations.lower_pelvis.C.y", "lower_pelvis.C_z": "stations.lower_pelvis.C.z", "left.r_x": "hips.left.r_x", "right.r_x": "hips.right.r_x", "lower_pelvis.R_x": "stations.lower_pelvis.rL", "left.r_z": "hips.left.r_z", "right.r_z": "hips.right.r_z", "lower_pelvis.R_f": "stations.lower_pelvis.rA", "lower_pelvis.R_b": "stations.lower_pelvis.rP", "left.thigh_start_x": "hips.left.P_s.x", "left.thigh_start_y": "hips.left.P_s.y", "left.thigh_start_z": "hips.left.P_s.z", "right.thigh_start_x": "hips.right.P_s.x", "right.thigh_start_y": "hips.right.P_s.y", "right.thigh_start_z": "hips.right.P_s.z", "neck_collar.C_y": "stations.neck_collar.C.y", "neck_collar.rL": "stations.neck_collar.rL", "neck_upper.C_y": "stations.neck_upper.C.y", "neck_upper.rL": "stations.neck_upper.rL", "left.axilla_x": "shoulders.left.axilla.x", "left.axilla_y": "shoulders.left.axilla.y", "right.axilla_x": "shoulders.right.axilla.x", "right.axilla_y": "shoulders.right.axilla.y", "left.peak_y": "shoulders.left.peak.y", "right.peak_y": "shoulders.right.peak.y", "left.start_lateral": "shoulders.left.start_lateral", "right.start_lateral": "shoulders.right.start_lateral", "left.start_up": "shoulders.left.start_up", "right.start_up": "shoulders.right.start_up", "left.shoulder_depth": "shoulders.left.shoulder_depth", "right.shoulder_depth": "shoulders.right.shoulder_depth"}
EXPECTED_DEPS = {"experiments/owned-root-assembly-successor/anatomy_gates.py": (25674, "0c4b5f7812141a4cd7c7107655e578044355dfef5dbda6574bbb63bc359a2ff4"), "experiments/owned-root-assembly-successor/artifact_serialization.py": (27977, "3837928e4b987c65fd773e540f7db502f5d9a0b4c5940b95c923953754fdf7d4"), "experiments/owned-root-assembly-successor/build_owned_root.py": (78268, "713cbf967bf2e0e233bae0c3506199fdc9a6ed71418edbd8dbf9b75beeee4045"), "experiments/owned-root-assembly-successor/chart_lineage.py": (18263, "01fdd09e8e0bb6d31851f0c7af711d90b313e36a012dbe3d71415a0468c31efc"), "experiments/owned-root-assembly-successor/mesh_correctness.py": (51035, "4104b70e70e958a469125d1fff544e20fee44b784bf7915d8e724e63d4f39db1"), "experiments/owned-root-assembly-successor/owned_root_surface.py": (58732, "c982d889fee30e2efea881b5725170740bc8afa2a883aa3dc4623941cd3e2a22"), "experiments/owned-root-assembly-successor/prepared_projection.py": (39646, "58637097a350332db40368a027347ec395192880aa6ba4782c7d523e5b288190"), "experiments/owned-root-assembly-successor/render_export.py": (15933, "bc251ea3f3f3cb1aa5ea66bfc4f79a82f86191e76bacb9a3c4f58e64883c4780"), "experiments/current-form-surface-preview/generate_structural_profile_sources.py": (54437, "009be817cd2ec2db663b668fb5c9bdfa7296936283322e59d7a145e3d3cfec62"), "experiments/current-form-surface-preview/structural_atomic_publish.py": (10489, "5e648b3a1a3519afdf0fc1f2f1ecfe6fe7f1c58130f71fd2c8ee4317e2f282b5"), "experiments/current-form-surface-preview/surface_preview_launcher.sh": (6582, "3e18da2d361029a16558757d9727150d54c4d691b35c6a2a21b5b51cb7785190"), "experiments/current-form-surface-preview/requirements.txt": (49, "69a3ce10b1f993d7913f02ca187eabb8d367abf214662ffa2132feacbdeedbec")}
OLD_REQUIRED = ("test_mesh_correctness.ProductionIntersectionFixtureTests.test_contract_fixture_matrix", "test_owned_root_surface.ProductionAxillaryFixtureTests.test_contract_fixture_matrix")
NEW_REQUIRED = ("test_exact_five_activation.ExactFiveActivationTests.test_all_33_selectors_copy_one_component", "test_exact_five_activation.ExactFiveActivationTests.test_atomic_failure_has_no_partial_publication", "test_exact_five_activation.ExactFiveActivationTests.test_decimal_half_even_boundaries", "test_exact_five_activation.ExactFiveActivationTests.test_final_evidence_schema_and_19_file_closure", "test_exact_five_activation.ExactFiveActivationTests.test_geometry_receives_only_components", "test_exact_five_activation.ExactFiveActivationTests.test_neutral_projection_preserves_38_payloads", "test_exact_five_activation.ExactFiveActivationTests.test_profile_seed_bundle_schema_and_closure", "test_exact_five_activation.ExactFiveActivationTests.test_profile_table_closed_and_exact_order", "test_exact_five_activation.ExactFiveActivationTests.test_profile_table_rejects_duplicate_keys_and_signatures", "test_exact_five_activation.ExactFiveActivationTests.test_projection_has_exact_92_bindings", "test_exact_five_activation.ExactFiveActivationTests.test_seed_dispatch_is_exact", "test_exact_five_activation.ExactFiveActivationTests.test_static_identity_and_allowlist")
SHA = re.compile(r"[0-9a-f]{64}\Z")
UTC = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{6}Z\Z")


class PublisherError(ValueError):
    pass


def _need(condition, message):
    if not condition:
        raise PublisherError(message)


def _keys(value, expected, label):
    _need(type(value) is dict and set(value) == set(expected), f"{label} has non-closed keys")
    return value


def _hex(value, label):
    _need(type(value) is str and SHA.fullmatch(value) is not None, f"{label} is not lowercase SHA-256")
    return value


def _abs(value, label):
    _need(type(value) is str and value and Path(value).is_absolute() and os.path.normpath(value) == value and "//" not in value, f"{label} is not canonical absolute")
    return Path(value)


def _fr(value, label, role=None):
    _keys(value, ("role_path", "bytes", "sha256"), label)
    try:
        artifacts.validate_role_path(value["role_path"])
    except Exception as exc:
        raise PublisherError(f"{label} has an invalid role") from exc
    _need(role is None or value["role_path"] == role, f"{label} has the wrong role")
    _need(type(value["bytes"]) is int and value["bytes"] >= 0, f"{label} has an invalid byte count")
    _hex(value["sha256"], f"{label}.sha256")
    return value


def _record(path, role, cap=4 * 1024 * 1024):
    return artifacts.regular_file_record(path, role, max_bytes=cap)


def _json(path, cap=16 * 1024 * 1024):
    raw = artifacts.read_regular_file(path, max_bytes=cap)
    try:
        value = artifacts.decode_canonical_json(raw)
    except Exception as exc:
        raise PublisherError(f"{path} is not canonical JSON") from exc
    _need(type(value) is dict, f"{path} is not an object")
    return value, raw


def _same_record(path, role, expected, cap=16 * 1024 * 1024):
    actual = _record(path, role, cap)
    _need(actual == expected, f"{role} changed after inventory")
    return actual


def _sidecar(raw, payload, name):
    _need(raw == f"{artifacts.sha256_bytes(payload)}  {name}\n".encode("ascii"), f"{name} sidecar is invalid")


def _now():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _bounded(value, label, limit=128):
    _need(type(value) is str and len(value.encode("utf-8")) <= limit, f"{label} is not bounded")
    return value


def _pointers(value, label):
    _need(type(value) is list and value and value == sorted(set(value), key=str.encode), f"{label} is not sorted and unique")
    for pointer in value:
        _need(type(pointer) is str and pointer.startswith("/") and "//" not in pointer and not re.search(r"~(?![01])", pointer), f"{label} contains an invalid RFC-6901 pointer")


def _addresses(value, label):
    encoded = [artifacts.canonical_json_bytes(item) for item in value] if type(value) is list else []
    _need(type(value) is list and value and len(encoded) == len(set(encoded)) and encoded == sorted(encoded), f"{label} is not sorted and unique")
    for address in value:
        _need(type(address) is list and len(address) == 4 and type(address[0]) is str and address[0] and type(address[1]) is list and all(type(anchor) is str and anchor for anchor in address[1]) and type(address[2]) is str and address[2] and type(address[3]) is str and address[3], f"{label} contains an invalid address tuple")


def _artifact_caps(records, evidence_role=None, large_role=None, total_limit=None):
    for row in records:
        role = row["role_path"].split("/", 1)[-1]
        cap = 16 * 1024 * 1024 if role == evidence_role else 8 * 1024 * 1024 if large_role and role == large_role else 2 * 1024 * 1024
        if role.endswith(".sha256"):
            cap = 256
        _need(row["bytes"] <= cap, f"artifact exceeds its cap: {row['role_path']}")
    if total_limit is not None:
        _need(sum(row["bytes"] for row in records) <= total_limit, "artifact root exceeds its cap")


def _png(path, role):
    raw = artifacts.read_regular_file(path, max_bytes=2 * 1024 * 1024)
    try:
        from PIL import Image
        image = Image.open(io.BytesIO(raw))
        _need(image.format == "PNG" and image.mode == "RGB" and image.size == (512, 1536) and not image.info, f"{role} PNG metadata differs")
        image.verify()
    except PublisherError:
        raise
    except Exception as exc:
        raise PublisherError(f"{role} PNG is invalid") from exc


def _ply_digest(path, role, level):
    raw = artifacts.read_regular_file(path, max_bytes=2 * 1024 * 1024)
    vertices_count, _, quads_count, _, _ = neutral.LEVEL_COUNTS[level]
    try:
        lines = raw.decode("ascii").splitlines()
    except UnicodeDecodeError as exc:
        raise PublisherError(f"{role} is not ASCII PLY") from exc
    header = ["ply", "format ascii 1.0", f"element vertex {vertices_count}", "property double x", "property double y", "property double z", f"element face {quads_count}", "property list uchar int vertex_indices", "end_header"]
    _need(b"\r" not in raw and raw.endswith(b"\n") and lines[:9] == header and len(lines) == 9 + vertices_count + quads_count, f"{role} PLY framing differs")
    try:
        vertices = tuple(tuple(float(item) for item in lines[9 + i].split()) for i in range(vertices_count))
        quads = tuple(tuple(int(item) for item in lines[9 + vertices_count + i].split()[1:]) for i in range(quads_count))
    except (IndexError, ValueError) as exc:
        raise PublisherError(f"{role} PLY rows are invalid") from exc
    _need(all(len(row) == 3 and all(math.isfinite(item) for item in row) for row in vertices) and all(len(row) == 4 and 0 <= min(row) and max(row) < vertices_count and len(set(row)) == 4 and lines[9 + vertices_count + i].split()[:1] == ["4"] for i, row in enumerate(quads)), f"{role} PLY geometry rows differ")
    triangles = tuple(item for a, b, c, d in quads for item in ((a, b, c), (a, c, d)))
    coordinates, indices = artifacts.coordinate_hash_bytes(vertices), artifacts.triangle_index_hash_bytes(triangles)
    return raw, quads, {"bytes": len(coordinates), "sha256": artifacts.sha256_bytes(coordinates)}, {"bytes": len(indices), "sha256": artifacts.sha256_bytes(indices)}


def _runtime(launcher, requirements):
    _need((platform.python_implementation(), platform.python_version(), platform.system(), getattr(sys.implementation, "cache_tag", None)) == ("CPython", "3.10.12", "Linux", "cpython-310"), "runtime is not the pinned CPython/Linux runtime")
    direct = (("numpy", "2.2.6"), ("scikit-image", "0.25.2"), ("pillow", "11.1.0"))
    resolved = (("imageio", "2.37.4"), ("lazy-loader", "0.5"), ("networkx", "3.4.2"), ("numpy", "2.2.6"), ("packaging", "26.3"), ("pillow", "11.1.0"), ("scikit-image", "0.25.2"), ("scipy", "1.15.3"), ("tifffile", "2025.5.10"))
    for name, version in (*direct, *resolved):
        try:
            observed = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError as exc:
            raise PublisherError(f"missing runtime distribution: {name}") from exc
        _need(observed == version, f"runtime distribution drift: {name}")
    builtins = []
    for name in ("math", "zlib"):
        module, spec = __import__(name), importlib.util.find_spec(name)
        _need(getattr(module, "__file__", None) is None and spec is not None and spec.origin == "built-in", f"{name} is not a built-in")
        versions = (None, None) if name == "math" else (_bounded(module.ZLIB_VERSION, "zlib compile"), _bounded(module.ZLIB_RUNTIME_VERSION, "zlib runtime"))
        builtins.append({"module_name": name, "__file__": None, "find_spec_origin": "built-in", "compile_version": versions[0], "runtime_version": versions[1]})
    python = {"implementation": "CPython", "version": "3.10.12", "build": _bounded(" ".join(platform.python_build()), "python build"), "compiler": _bounded(platform.python_compiler(), "python compiler"), "cache_tag": "cpython-310", "abiflags": _bounded(sys.abiflags, "python abiflags"), "soabi": _bounded(sysconfig.get_config_var("SOABI"), "python soabi")}
    libc_name, libc_version = platform.libc_ver()
    platform_value = {"system": platform.system(), "release": platform.release(), "version": platform.version(), "machine": platform.machine(), "pointer_bits": 8 * struct.calcsize("P"), "byteorder": sys.byteorder, "libc_name": libc_name, "libc_version": libc_version}
    for key in ("system", "release", "version", "machine", "libc_name", "libc_version"):
        platform_value[key] = _bounded(platform_value[key], f"platform.{key}")
    _need(platform_value["byteorder"] in ("little", "big") and platform_value["pointer_bits"] > 0, "platform is not admitted")
    locale_value = {"active": _bounded(locale.setlocale(locale.LC_ALL, None), "locale.active", 512), "preferred_encoding": _bounded(locale.getpreferredencoding(False), "locale.preferred_encoding", 512)}
    value = {"schema": "owned-root-assembly-successor-runtime.v2", "python": python, "platform": platform_value, "locale": locale_value, "managed_launcher": launcher, "requirements": requirements, "direct_distributions": [{"name": n, "version": v} for n, v in direct], "resolved_distributions": [{"name": n, "version": v} for n, v in resolved], "builtin_modules": builtins}
    raw = artifacts.canonical_json_bytes(value)
    _need(len(raw) <= 64 * 1024, "runtime JSON exceeds its cap")
    return value, raw, artifacts.sha256_bytes(raw)


def _source_records(package, expected):
    found = []
    for directory, dirs, files in os.walk(package, followlinks=False):
        _need(not any((Path(directory) / name).is_symlink() for name in dirs), "implementation package contains a symlink directory")
        found.extend((Path(directory) / name).relative_to(ROOT).as_posix() for name in files if name.endswith((".py", ".sh")))
    found = tuple(sorted(found, key=str.encode))
    expected = tuple(sorted(expected, key=str.encode))
    _need(found == expected, f"implementation source allowlist differs: {found}")
    return [_record(ROOT / role, role) for role in expected]


def _static():
    _need(os.environ.get("PYTHONHASHSEED") == "0", "publisher requires literal PYTHONHASHSEED=0")
    activation = _record(ROOT / ACTIVATION_ROLE, ACTIVATION_ROLE)
    _need(activation["sha256"] == ACTIVATION_SHA, "activation contract identity differs")
    sidecar = _record(ROOT / "experiments/owned-root-assembly-successor/exact-five-activation-contract.sha256", "experiments/owned-root-assembly-successor/exact-five-activation-contract.sha256", 256)
    _need(artifacts.read_regular_file(ROOT / sidecar["role_path"], max_bytes=256) == f"{ACTIVATION_SHA}  experiments/owned-root-assembly-successor/exact-five-activation-contract.md\n".encode("ascii"), "activation sidecar differs")
    design, source, profile = (_record(ROOT / role, role) for role in (DESIGN_ROLE, SOURCE_ROLE, PROFILE_ROLE))
    _need(artifacts.read_regular_file(ROOT / "experiments/owned-root-assembly-successor/design-contract.sha256", max_bytes=256) == f"{DESIGN_SHA}  {DESIGN_ROLE}\n".encode("ascii"), "design sidecar differs")
    _need((design["bytes"], design["sha256"]) == (173184, DESIGN_SHA) and (source["bytes"], source["sha256"]) == (56984, SOURCE_SHA) and (profile["bytes"], profile["sha256"]) == (29970, PROFILE_SHA), "fixed source identity differs")
    deps = []
    for role, fixed in sorted(EXPECTED_DEPS.items(), key=lambda pair: pair[0].encode()):
        actual = _record(ROOT / role, role, 4 * 1024 * 1024 if not role.endswith("requirements.txt") else 64 * 1024)
        _need((actual["bytes"], actual["sha256"]) == fixed, f"fixed dependency drift: {role}")
        deps.append(actual)
    neutral_files = _source_records(NEUTRAL, neutral.IMPLEMENTATION_ROLES)
    additive_files = _source_records(PACKAGE, ADDITIVE_ROLES)
    launcher = next(row for row in deps if row["role_path"] == "experiments/current-form-surface-preview/surface_preview_launcher.sh")
    requirements = next(row for row in deps if row["role_path"] == "experiments/current-form-surface-preview/requirements.txt")
    _need(artifacts.read_regular_file(ROOT / requirements["role_path"], max_bytes=64 * 1024) == b"numpy==2.2.6\nscikit-image==0.25.2\nPillow==11.1.0\n", "requirements are not pinned")
    runtime, runtime_raw, runtime_sha = _runtime(launcher, requirements)
    _need(runtime_sha == RUNTIME_SHA, "runtime fingerprint differs")
    return {"activation": activation, "design": design, "source": source, "profile": profile, "dependencies": deps, "neutral_files": neutral_files, "additive_files": additive_files, "runtime": runtime, "runtime_raw": runtime_raw, "runtime_sha": runtime_sha, "comparator": next(row for row in neutral_files if row["role_path"] == COMPARATOR_ROLE)}


def _table(identity):
    raw = artifacts.read_regular_file(ROOT / PROFILE_ROLE, max_bytes=4 * 1024 * 1024)
    try:
        table = json.loads(raw.decode("utf-8"), object_pairs_hook=lambda pairs: _unique_pairs(pairs))
    except Exception as exc:
        raise PublisherError("profile table is not valid JSON") from exc
    _need(type(table) is dict and type(table.get("profiles")) is list and [row.get("id") for row in table["profiles"]] == list(PROFILES), "profile table order differs")
    for index, row in enumerate(table["profiles"]):
        _keys(row, ("dimension_scales", "id", "label", "part_placements"), f"profile[{index}]")
        _need(type(row["label"]) is str and row["label"] and type(row["dimension_scales"]) is dict and len(row["dimension_scales"]) == 37 and type(row["part_placements"]) is dict and len(row["part_placements"]) == 18, f"profile[{index}] shape differs")
        _need(all(type(v) is int and 1 <= v <= 10000 for v in row["dimension_scales"].values()), f"profile[{index}] scale differs")
        _need(all(type(v) is list and len(v) == 3 and all(type(n) is int and -1000000000 <= n <= 1000000000 for n in v) for v in row["part_placements"].values()), f"profile[{index}] placement differs")
    _need(identity["profile"]["sha256"] == PROFILE_SHA, "profile table identity differs")
    return table["profiles"]


def _unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate key: {key}")
        result[key] = value
    return result


def _manifest_ref(value, label, role, record, schema=None):
    _keys(value, ("role_path", "bytes", "sha256", "schema"), label)
    artifacts.validate_role_path(value["role_path"])
    _need(type(value["bytes"]) is int and value["bytes"] >= 0, f"{label} has an invalid byte count")
    _hex(value["sha256"], f"{label}.sha256")
    _need(value["role_path"] == role and value["bytes"] == record["bytes"] and value["sha256"] == record["sha256"] and (schema is None or value["schema"] == schema), f"{label} does not reference the admitted record")


def _thresholds(value, expected, label):
    _need(type(value) is list and [row.get("threshold_id") if type(row) is dict else None for row in value] == [row["threshold_id"] for row in expected], f"{label} threshold order differs")
    for index, row in enumerate(value):
        _keys(row, ("threshold_id", "relation", "lower", "upper", "unit"), f"{label}[{index}]")
    _need(value == expected, f"{label} differs from the frozen neutral inventory")


def _threshold_shape(value, label):
    _need(type(value) is list and len(value) == 357, f"{label} threshold cardinality differs")
    ids = []
    for index, row in enumerate(value):
        _keys(row, ("threshold_id", "relation", "lower", "upper", "unit"), f"{label}[{index}]")
        _need(type(row["threshold_id"]) is str and row["threshold_id"], f"{label}[{index}] threshold ID differs")
        _need(row["relation"] in ("eq", "ge", "gt", "le", "lt", "range") and type(row["unit"]) is str and row["unit"], f"{label}[{index}] threshold type differs")
        for bound in (row["lower"], row["upper"]):
            _need(bound is None or (type(bound) in (int, float) and math.isfinite(float(bound))), f"{label}[{index}] threshold bound differs")
        relation, lower, upper = row["relation"], row["lower"], row["upper"]
        _need((relation == "eq" and lower is not None and upper is not None and lower == upper) or (relation in ("ge", "gt") and lower is not None and upper is None) or (relation in ("le", "lt") and lower is None and upper is not None) or (relation == "range" and lower is not None and upper is not None and lower <= upper), f"{label}[{index}] threshold bounds do not match relation")
        ids.append(row["threshold_id"])
    _need(ids == sorted(set(ids), key=str.encode), f"{label} thresholds are not sorted and unique")


def _gate_rows(rows, expected_ids, thresholds, label):
    _need(type(rows) is list and [row.get("gate_id") if type(row) is dict else None for row in rows] == expected_ids, f"{label} gate inventory differs")
    threshold_map = {row["threshold_id"]: row for row in thresholds}
    for index, row in enumerate(rows):
        _keys(row, ("gate_id", "outcome", "sample_count", "observed_min", "observed_max", "threshold_id"), f"{label}[{index}]")
        threshold = threshold_map.get(row["threshold_id"])
        _need(row["outcome"] == "pass" and row["threshold_id"] == f"threshold.{row['gate_id']}" and threshold is not None and type(row["sample_count"]) is int and row["sample_count"] >= 1, f"{label}[{index}] is not all-pass evidence")
        low, high = row["observed_min"], row["observed_max"]
        _need(type(low) in (int, float) and type(high) in (int, float) and math.isfinite(float(low)) and math.isfinite(float(high)) and low <= high, f"{label}[{index}] observations are invalid")
        relation, lower, upper = threshold["relation"], threshold["lower"], threshold["upper"]
        passes = (low == lower and high == upper) if relation == "eq" else low >= lower if relation == "ge" else low > lower if relation == "gt" else high <= upper if relation == "le" else high < upper if relation == "lt" else low >= lower and high <= upper
        _need(passes, f"{label}[{index}] fails its threshold")


def _manifest_graph(root, records, identity, stable):
    def get(role):
        value, raw = _json(root / role)
        _need(_same_record(root / role, role, records[role]) == records[role], f"{role} changed")
        return value, raw
    input_value, _ = get("input-manifest.json")
    _keys(input_value, ("schema", "contract_sha256", "source", "profile_table", "profile_id", "prepared_input", "source_bindings", "runtime", "implementation_files", "recipe_id"), "input manifest")
    _need(input_value["schema"] == "owned-root-assembly-successor-input-manifest.v1" and input_value["contract_sha256"] == DESIGN_SHA and input_value["source"] == identity["source"] and input_value["profile_table"] == identity["profile"] and input_value["profile_id"] == "standard_neutral_reference" and input_value["runtime"] == identity["runtime"] and input_value["implementation_files"] == identity["neutral_files"] and type(input_value["source_bindings"]) is list and len(input_value["source_bindings"]) == 92 and type(input_value["recipe_id"]) is str and SHA.fullmatch(input_value["recipe_id"]) and input_value["recipe_id"] == stable["recipe_id"], "input manifest identity differs")
    _fr(input_value["prepared_input"], "input prepared", "prepared-input.json")
    coordinate, _ = get("coordinate-manifest.json")
    _keys(coordinate, ("schema", "contract_sha256", "input_manifest", "counts", "coordinate_hashes", "triangle_index_hashes", "surface_artifacts"), "coordinate manifest")
    counts = [{"level": i, "vertices": n[0], "edges": n[1], "quads": n[2], "triangles": n[3], "boundary_edges": n[4]} for i, n in enumerate(neutral.LEVEL_COUNTS)]
    _need(coordinate["schema"] == "owned-root-assembly-successor-coordinate-manifest.v1" and coordinate["contract_sha256"] == DESIGN_SHA and coordinate["counts"] == counts and len(coordinate["coordinate_hashes"]) == 3 and len(coordinate["triangle_index_hashes"]) == 3 and coordinate["surface_artifacts"] == [records[r] for r in sorted(neutral.SURFACE_ROLES, key=str.encode)], "coordinate manifest differs")
    _manifest_ref(coordinate["input_manifest"], "coordinate input", "input-manifest.json", records["input-manifest.json"], "owned-root-assembly-successor-input-manifest.v1")
    gate, _ = get("gate-manifest.json")
    _keys(gate, ("schema", "contract_sha256", "coordinate_manifest", "thresholds", "structural", "continuity", "anatomy", "intersection"), "gate manifest")
    _need(gate["schema"] == "owned-root-assembly-successor-gate-manifest.v1" and gate["contract_sha256"] == DESIGN_SHA, "gate manifest identity differs")
    _manifest_ref(gate["coordinate_manifest"], "gate coordinate", "coordinate-manifest.json", records["coordinate-manifest.json"], coordinate["schema"])
    _need(len(gate["structural"]) == 122 and len(gate["continuity"]) == 144 and len(gate["anatomy"]) == 78 and len(gate["intersection"]) == 12 and len(gate["thresholds"]) == 357, "gate cardinality differs")
    thresholds = gate["thresholds"]
    _threshold_shape(thresholds, "gate")
    ids = {group: [row["gate_id"] for row in gate[group]] for group in ("structural", "continuity", "anatomy", "intersection")}
    for group in ids:
        _gate_rows(gate[group], ids[group], thresholds, group)
    causality, _ = get("causality-manifest.json")
    _keys(causality, ("schema", "contract_sha256", "input_manifest", "formula_records", "source_bindings", "charts", "perturbations"), "causality manifest")
    _need(causality["schema"] == "owned-root-assembly-successor-causality-manifest.v1" and causality["contract_sha256"] == DESIGN_SHA and len(causality["formula_records"]) == 120 and len(causality["source_bindings"]) == 92 and type(causality["charts"]) is dict and len(causality["perturbations"]) == 33, "causality manifest differs")
    _manifest_ref(causality["input_manifest"], "causality input", "input-manifest.json", records["input-manifest.json"], input_value["schema"])
    render_value, _ = get("render-manifest.json")
    _keys(render_value, ("schema", "contract_sha256", "coordinate_manifest", "render_config", "visibility", "artifacts"), "render manifest")
    _need(render_value["schema"] == "owned-root-assembly-successor-render-manifest.v1" and render_value["contract_sha256"] == DESIGN_SHA and render_value["artifacts"] == [records[r] for r in sorted(("direct.png", "lineage.png"), key=str.encode)], "render manifest differs")
    _manifest_ref(render_value["coordinate_manifest"], "render coordinate", "coordinate-manifest.json", records["coordinate-manifest.json"], coordinate["schema"])
    render.validate_render_config(render_value["render_config"])
    _keys(render_value["visibility"], ("level", "triangle_count", "triangle_index_sha256", "rule"), "render visibility")
    _need(render_value["visibility"]["level"] == 2 and render_value["visibility"]["triangle_count"] == 3328 and render_value["visibility"]["rule"] == "larger-depth-then-lower-triangle-index", "render visibility differs")
    return thresholds, ids


def _old_receipt(receipt, identity):
    _keys(receipt, ("schema", "outcome", "literal_invocation", "contract_sha256", "runtime_fingerprint_sha256", "implementation_files", "executed_test_ids", "required_test_ids", "results"), "neutral receipt")
    _need(receipt["schema"] == "owned-root-assembly-successor-managed-test-receipt.v1" and receipt["outcome"] == "success" and receipt["contract_sha256"] == DESIGN_SHA and receipt["runtime_fingerprint_sha256"] == identity["runtime_sha"] and receipt["implementation_files"] == identity["neutral_files"], "neutral receipt identity differs")
    invocation = _keys(receipt["literal_invocation"], ("environment", "argv"), "neutral receipt invocation")
    argv = invocation["argv"]
    _need(invocation["environment"] == ["PYTHONHASHSEED=0"] and type(argv) is list and len(argv) == 4 and argv[:3] == [BUILDER_ROLE, "--internal-managed-tests", "--receipt"] and _abs(argv[3], "neutral receipt path").name == "managed-test-receipt.json", "neutral receipt invocation differs")
    executed = receipt["executed_test_ids"]
    _need(type(executed) is list and len(executed) == 134 and executed == sorted(set(executed), key=str.encode) and all(type(v) is str and v for v in executed) and receipt["required_test_ids"] == list(OLD_REQUIRED) and all(executed.count(v) == 1 for v in OLD_REQUIRED), "neutral receipt tests differ")
    _need(receipt["results"] == {"tests_run": 134, "failures": 0, "errors": 0, "skipped": 0, "expected_failures": 0, "unexpected_successes": 0}, "neutral receipt result differs")


def _baseline(path, identity):
    root = _abs(str(path), "baseline root")
    rows = artifacts.closed_inventory(root, BASELINE_ROLES, max_file_bytes=8 * 1024 * 1024)
    records = {row["role_path"]: row for row in rows}
    _artifact_caps(rows, large_role="causality-manifest.json", total_limit=32 * 1024 * 1024)
    _need(records["comparison/comparison-report.json"]["sha256"] == BASELINE_REPORT_SHA and records["comparison/comparison-report.sha256"]["sha256"] == BASELINE_REPORT_SIDE_SHA and records["comparison/comparison-report.sha256"]["bytes"] == 89, "baseline comparison identity differs")
    report, raw = _json(root / "comparison/comparison-report.json")
    _same_record(root / "comparison/comparison-report.json", "comparison/comparison-report.json", records["comparison/comparison-report.json"])
    _sidecar(artifacts.read_regular_file(root / "comparison/comparison-report.sha256", max_bytes=256), raw, "comparison-report.json")
    _keys(report, ("schema", "outcome", "comparator", "runtime_fingerprint_sha256", "managed_test_receipt", "seed_bundles", "stable_comparisons", "excluded_run_local_roles"), "comparison report")
    _need(report["schema"] == "owned-root-assembly-successor-comparison-report.v1" and report["outcome"] == "success" and report["comparator"] == identity["comparator"] and report["runtime_fingerprint_sha256"] == identity["runtime_sha"] and report["excluded_run_local_roles"] == ["report.json", "report.sha256"], "comparison report identity differs")
    _old_receipt(report["managed_test_receipt"], identity)
    _need(type(report["stable_comparisons"]) is list and [row.get("role_path") for row in report["stable_comparisons"]] == list(BASELINE_STABLE_ROLES), "baseline stable comparison inventory differs")
    for row, role in zip(report["stable_comparisons"], BASELINE_STABLE_ROLES):
        _fr(row, f"baseline comparison {role}")
        _need(row == records[f"seed-17/{role}"] | {"role_path": role} and row == records[f"seed-29/{role}"] | {"role_path": role}, f"baseline comparison differs: {role}")
    thresholds = ids = None
    bundles = report["seed_bundles"]
    _need(type(bundles) is list and len(bundles) == 2, "baseline bundle inventory differs")
    for index, seed in enumerate(SEEDS):
        prefix = f"seed-{seed}"
        stable, _ = _json(root / prefix / "stable-manifest.json")
        _need(records[f"{prefix}/stable-manifest.json"]["sha256"] == BASELINE_STABLE_SHA, f"{prefix} stable manifest identity differs")
        _keys(stable, ("schema", "contract_sha256", "recipe_id", "runtime", "implementation_files", "input_manifest", "coordinate_manifest", "gate_manifest", "causality_manifest", "render_manifest", "artifact_hashes"), f"{prefix} stable manifest")
        _need(stable["schema"] == "owned-root-assembly-successor-stable-manifest.v1" and stable["contract_sha256"] == DESIGN_SHA and stable["runtime"] == identity["runtime"] and stable["implementation_files"] == identity["neutral_files"] and type(stable["recipe_id"]) is str and SHA.fullmatch(stable["recipe_id"]), f"{prefix} stable identity differs")
        thresholds, ids = _manifest_graph(root / prefix, {role: records[f"{prefix}/{role}"] for role in neutral.ARTIFACT_ROLES}, identity, stable)
        for field, role in (("input_manifest", "input-manifest.json"), ("coordinate_manifest", "coordinate-manifest.json"), ("gate_manifest", "gate-manifest.json"), ("causality_manifest", "causality-manifest.json"), ("render_manifest", "render-manifest.json")):
            _manifest_ref(stable[field], f"{prefix} {field}", role, records[f"{prefix}/{role}"], f"owned-root-assembly-successor-{role.removesuffix('.json').replace('-manifest', '')}-manifest.v1")
        _need(stable["artifact_hashes"] == [{**records[f"{prefix}/{role}"], "role_path": role} for role in sorted(neutral.STABLE_ARTIFACT_ROLES, key=str.encode)], f"{prefix} stable artifacts differ")
        expected_bundle = {"seed": seed, "role_path": prefix, "stable_manifest": {"role_path": f"{prefix}/stable-manifest.json", "bytes": records[f"{prefix}/stable-manifest.json"]["bytes"], "sha256": records[f"{prefix}/stable-manifest.json"]["sha256"], "schema": stable["schema"]}, "report": {**records[f"{prefix}/report.json"], "role_path": f"{prefix}/report.json"}, "report_sidecar": {**records[f"{prefix}/report.sha256"], "role_path": f"{prefix}/report.sha256"}}
        _need(bundles[index] == expected_bundle, f"{prefix} comparison bundle differs")
        run_report, report_raw = _json(root / prefix / "report.json")
        _keys(run_report, ("schema", "outcome", "seed", "literal_invocation", "output_path", "staging_path", "python_executable_path", "started_utc", "finished_utc", "timings", "runtime_fingerprint_sha256", "stable_manifest", "gates"), f"{prefix} report")
        _need(run_report["schema"] == "owned-root-assembly-successor-run-report.v1" and run_report["outcome"] == "success" and run_report["seed"] == seed and run_report["runtime_fingerprint_sha256"] == identity["runtime_sha"], f"{prefix} report identity differs")
        output_path = _abs(run_report["output_path"], f"{prefix} output")
        staging_path = _abs(run_report["staging_path"], f"{prefix} staging")
        _need(run_report["stable_manifest"] == expected_bundle["stable_manifest"] and run_report["literal_invocation"] == {"environment": [f"PYTHONHASHSEED={seed}"], "argv": [BUILDER_ROLE, "--output", run_report["output_path"]]} and output_path.name == prefix and staging_path.parent == output_path.parent and staging_path.name.startswith(f".{output_path.name}.stage-"), f"{prefix} report paths differ")
        _abs(run_report["python_executable_path"], f"{prefix} Python")
        _need(UTC.fullmatch(run_report["started_utc"]) and UTC.fullmatch(run_report["finished_utc"]) and run_report["finished_utc"] >= run_report["started_utc"] and [row.get("phase") for row in run_report["timings"]] == list(neutral.RUN_PHASES) and all(_keys(row, ("phase", "seconds"), f"{prefix} timing") and type(row["seconds"]) is float and math.isfinite(row["seconds"]) and row["seconds"] >= 0.0 for row in run_report["timings"]) and run_report["gates"] == [{"gate_id": gate, "outcome": "pass", "sample_count": 1, "observed_min": 1, "observed_max": 1, "threshold_id": "gate.boolean-pass"} for gate in neutral.RUN_REPORT_GATES], f"{prefix} report stages differ")
        _sidecar(artifacts.read_regular_file(root / prefix / "report.sha256", max_bytes=256), report_raw, "report.json")
    return {"root": root, "records": records, "report": report, "thresholds": thresholds, "gate_ids": ids, "comparison_record": {"role_path": "comparison-report.json", "bytes": records["comparison/comparison-report.json"]["bytes"], "sha256": records["comparison/comparison-report.json"]["sha256"]}}


def _bundle(path, profile, seed, identity, thresholds, gate_ids, table):
    root = _abs(str(path), f"{profile}/{seed} bundle")
    _need(root.name == f"seed-{seed}" and root.is_dir(), "bundle path is not a seed directory")
    rows = artifacts.closed_inventory(root, BUNDLE_ROLES, max_file_bytes=8 * 1024 * 1024)
    records = {row["role_path"]: row for row in rows}
    _artifact_caps(rows, evidence_role="profile-seed-evidence.json")
    _png(root / "direct.png", "direct.png")
    _png(root / "lineage.png", "lineage.png")
    evidence, evidence_raw = _json(root / "profile-seed-evidence.json")
    _sidecar(artifacts.read_regular_file(root / "profile-seed-evidence.sha256", max_bytes=256), evidence_raw, "profile-seed-evidence.json")
    _keys(evidence, ("schema", "outcome", "activation_contract", "design_contract", "source", "profile_table", "existing_dependencies", "additive_implementation_files", "runtime", "runtime_fingerprint_sha256", "profile_id", "profile_index", "selection", "projected_values", "projected_carrier", "projection_bindings", "levels", "thresholds", "gates", "causality", "renders", "payloads", "invariants"), "profile evidence")
    _need(evidence["schema"] == "owned-root-assembly-successor-profile-seed-evidence.v1" and evidence["outcome"] == "success" and evidence["profile_id"] == profile and evidence["profile_index"] == PROFILES.index(profile) and evidence["activation_contract"] == identity["activation"] and evidence["design_contract"] == identity["design"] and evidence["source"] == identity["source"] and evidence["profile_table"] == identity["profile"] and evidence["existing_dependencies"] == identity["dependencies"] and evidence["additive_implementation_files"] == identity["additive_files"] and evidence["runtime"] == identity["runtime"] and evidence["runtime_fingerprint_sha256"] == identity["runtime_sha"], f"{profile}/{seed} evidence identity differs")
    row = table[evidence["profile_index"]]
    selection = _keys(evidence["selection"], ("profile_pointer", "profile_row_sha256", "dimension_scales_sha256", "part_placements_sha256"), "selection")
    _need(selection["profile_pointer"] == f"/profiles/{evidence['profile_index']}" and selection["profile_row_sha256"] == artifacts.sha256_bytes(artifacts.canonical_json_bytes(row)) and selection["dimension_scales_sha256"] == artifacts.sha256_bytes(artifacts.canonical_json_bytes(row["dimension_scales"])) and selection["part_placements_sha256"] == artifacts.sha256_bytes(artifacts.canonical_json_bytes(row["part_placements"])), "selection hashes differ")
    _need(evidence["projected_values"] and [item.get("prepared_component") for item in evidence["projected_values"]] == list(COMPONENT_IDS) and len(evidence["projected_values"]) == 92, "projected values differ")
    bindings = evidence["projection_bindings"]
    _need(type(bindings) is list and [item.get("prepared_component") for item in bindings] == list(COMPONENT_IDS) and len(bindings) == 92, "projection bindings differ")
    for index, (value, binding) in enumerate(zip(evidence["projected_values"], bindings)):
        _keys(value, ("prepared_component", "value", "source_pointers", "profile_pointers"), f"projected value {index}")
        _keys(binding, ("prepared_component", "derivation_id", "source_addresses", "source_pointers", "profile_pointers"), f"binding {index}")
        _need(value["prepared_component"] == binding["prepared_component"] and artifacts.coerce_binary64(value["value"], label="projected value") == value["value"] and value["source_pointers"] == binding["source_pointers"] and value["profile_pointers"] == binding["profile_pointers"] and binding["derivation_id"] in ("profile.dimension-permille-half-even-mm.v1", "profile.world-placement-axis-sum.v1", "profile.world-landmark-axis-sum.v1"), f"binding {index} differs")
        _pointers(value["source_pointers"], f"binding {index} source pointers")
        _pointers(value["profile_pointers"], f"binding {index} profile pointers")
        _addresses(binding["source_addresses"], f"binding {index} source addresses")
        _need(all(pointer.startswith(f"/profiles/{evidence['profile_index']}/") for pointer in value["profile_pointers"]), f"binding {index} selects another profile")
    carrier = _keys(evidence["projected_carrier"], ("bytes", "sha256"), "projected carrier")
    carrier_raw = artifacts.canonical_json_bytes([row["value"] for row in evidence["projected_values"]])
    _need(carrier == {"bytes": len(carrier_raw), "sha256": artifacts.sha256_bytes(carrier_raw)}, "projected carrier differs")
    levels = evidence["levels"]
    _need(type(levels) is list and [item.get("level") for item in levels] == [0, 1, 2], "level inventory differs")
    level_digests = {}
    for level, item in enumerate(levels):
        _keys(item, ("level", "counts", "coordinate_bytes", "coordinate_sha256", "triangle_index_bytes", "triangle_index_sha256", "ply"), f"level {level}")
        expected = neutral.LEVEL_COUNTS[level]
        _need(item["counts"] == {"level": level, "vertices": expected[0], "edges": expected[1], "quads": expected[2], "triangles": expected[3], "boundary_edges": expected[4]} and item["ply"] == records[f"surface-level-{level}.ply"], f"level {level} differs")
        _need(type(item["coordinate_bytes"]) is int and item["coordinate_bytes"] > 0 and type(item["triangle_index_bytes"]) is int and item["triangle_index_bytes"] > 0, f"level {level} hashes differ")
        _hex(item["coordinate_sha256"], f"level {level} coordinate hash")
        _hex(item["triangle_index_sha256"], f"level {level} triangle hash")
        level_digests[level] = _ply_digest(root / f"surface-level-{level}.ply", f"surface-level-{level}.ply", level)
        _need(item["coordinate_bytes"] == level_digests[level][2]["bytes"] and item["coordinate_sha256"] == level_digests[level][2]["sha256"] and item["triangle_index_bytes"] == level_digests[level][3]["bytes"] and item["triangle_index_sha256"] == level_digests[level][3]["sha256"], f"level {level} coordinate identity differs")
    _thresholds(evidence["thresholds"], thresholds, "profile thresholds")
    gates = _keys(evidence["gates"], ("structural", "continuity", "anatomy", "intersection"), "profile gates")
    for group in gates:
        _gate_rows(gates[group], gate_ids[group], thresholds, f"profile {group}")
    causality = evidence["causality"]
    _need(type(causality) is list and [item.get("parameter_id") for item in causality] == sorted(CAUSAL_COMPONENTS, key=str.encode) and len(causality) == 33, "causality inventory differs")
    for index, item in enumerate(causality):
        _keys(item, ("parameter_id", "prepared_component", "delta_m", "support_level", "predicted_support_count", "observed_support_count", "predicted_support_sha256", "observed_support_sha256", "maximum_movement_m", "artifact"), f"causality {index}")
        parameter = item["parameter_id"]
        _need(item["prepared_component"] == CAUSAL_COMPONENTS[parameter] and item["delta_m"] == 0.01 and item["support_level"] == 2 and type(item["predicted_support_count"]) is int and item["predicted_support_count"] == item["observed_support_count"] and item["predicted_support_count"] > 0 and item["predicted_support_count"] <= 1737 and item["predicted_support_sha256"] == item["observed_support_sha256"] and _hex(item["predicted_support_sha256"], "support hash") and type(item["maximum_movement_m"]) is float and math.isfinite(item["maximum_movement_m"]) and item["maximum_movement_m"] >= float.fromhex("0x1.d14e3bcd35a85p-11") and item["artifact"] == records[f"perturb-{parameter.replace('.', '-')}.ply"], f"causality {index} differs")
        perturb_raw, perturb_quads, _, _ = _ply_digest(root / f"perturb-{parameter.replace('.', '-')}.ply", f"perturb-{parameter.replace('.', '-')}.ply", 2)
        _need(perturb_quads == level_digests[2][1] and perturb_raw != level_digests[2][0], f"causality {index} topology or byte movement differs")
    renders = _keys(evidence["renders"], ("renderer_id", "render_config", "render_config_sha256", "visibility", "visibility_sha256", "direct", "lineage", "same_surface_positions_sha256", "same_surface_triangles_sha256"), "profile renders")
    _need(renders["renderer_id"] == "owned-root-raster-pillow-11.1.0.v1" and renders["render_config_sha256"] == artifacts.sha256_bytes(artifacts.canonical_json_bytes(renders["render_config"])) and renders["direct"] == records["direct.png"] and renders["lineage"] == records["lineage.png"], "profile render identity differs")
    render.validate_render_config(renders["render_config"])
    _keys(renders["visibility"], ("level", "triangle_count", "triangle_index_sha256", "rule"), "profile visibility")
    _need(renders["visibility"]["level"] == 2 and renders["visibility"]["triangle_count"] == 3328 and renders["visibility"]["rule"] == "larger-depth-then-lower-triangle-index" and renders["visibility_sha256"] == artifacts.sha256_bytes(artifacts.canonical_json_bytes(renders["visibility"])) and renders["same_surface_positions_sha256"] == levels[2]["coordinate_sha256"] and renders["same_surface_triangles_sha256"] == levels[2]["triangle_index_sha256"] == renders["visibility"]["triangle_index_sha256"], "profile surface binding differs")
    _need(evidence["payloads"] == [records[role] for role in PAYLOAD_ROLES] and evidence["invariants"] == {"topology_equal_to_neutral": True, "formulas_equal_to_neutral": True, "tunables_equal_to_neutral": True, "thresholds_equal_to_neutral": True, "gate_inventory_equal_to_neutral": True, "subdivision_equal_to_neutral": True, "ownership_equal_to_neutral": True, "causality_rules_equal_to_neutral": True, "renderer_equal_to_neutral": True}, "profile payload or invariant identity differs")
    run_report, run_raw = _json(root / "run-report.json")
    _keys(run_report, ("schema", "outcome", "profile_id", "profile_index", "seed", "literal_invocation", "output_path", "staging_path", "python_executable_path", "started_utc", "finished_utc", "timings", "runtime_fingerprint_sha256", "manifest_ref", "gates"), "profile run report")
    _need(run_report["schema"] == "owned-root-assembly-successor-profile-seed-run-report.v1" and run_report["outcome"] == "success" and run_report["profile_id"] == profile and run_report["profile_index"] == PROFILES.index(profile) and run_report["seed"] == seed and run_report["runtime_fingerprint_sha256"] == identity["runtime_sha"] and run_report["output_path"] == str(root) and run_report["literal_invocation"] == {"environment": [f"PYTHONHASHSEED={seed}"], "argv": [RUNNER_ROLE, "--profile", profile, "--output", str(root)]}, "profile report identity differs")
    profile_staging = _abs(run_report["staging_path"], "profile staging")
    _abs(run_report["python_executable_path"], "profile Python")
    _need(profile_staging.parent == root.parent and profile_staging.name.startswith(f".{root.name}.stage-") and UTC.fullmatch(run_report["started_utc"]) and UTC.fullmatch(run_report["finished_utc"]) and run_report["finished_utc"] >= run_report["started_utc"] and [item.get("phase") for item in run_report["timings"]] == ["identity", "selection-projection", "catalogs", "geometry-gates", "causality", "serialization", "total-before-seal"] and all(_keys(item, ("phase", "seconds"), "profile timing") and type(item["seconds"]) is float and math.isfinite(item["seconds"]) and item["seconds"] >= 0.0 for item in run_report["timings"]), "profile report timings differ")
    _need(run_report["gates"] == [{"gate_id": gate, "outcome": "pass", "sample_count": 1, "observed_min": 1, "observed_max": 1, "threshold_id": "gate.boolean-pass"} for gate in neutral.RUN_REPORT_GATES], "profile report gates differ")
    _manifest_ref(run_report["manifest_ref"], "profile evidence reference", "profile-seed-evidence.json", records["profile-seed-evidence.json"], evidence["schema"])
    _sidecar(artifacts.read_regular_file(root / "run-report.sha256", max_bytes=256), run_raw, "run-report.json")
    return {"root": root, "records": records, "evidence": evidence}


def _compare(left, right, roles):
    result = []
    for role in roles:
        lraw = artifacts.read_regular_file(left["root"] / role, max_bytes=8 * 1024 * 1024)
        rraw = artifacts.read_regular_file(right["root"] / role, max_bytes=8 * 1024 * 1024)
        _need(left["records"][role] == {"role_path": role, "bytes": len(lraw), "sha256": artifacts.sha256_bytes(lraw)} and right["records"][role] == {"role_path": role, "bytes": len(rraw), "sha256": artifacts.sha256_bytes(rraw)} and lraw == rraw, f"cross-seed role differs: {role}")
        result.append({"role_path": role, "bytes": len(lraw), "sha256": artifacts.sha256_bytes(lraw)})
    return result


def _context(path, baseline):
    value, raw = _json(path, 64 * 1024)
    _keys(value, ("schema", "literal_invocation", "output_path", "neutral_baseline_path", "timings"), "launcher context")
    output = _abs(value["output_path"], "output path")
    _need(value["schema"] == "owned-root-assembly-successor-exact-five-launcher-context.v1" and value["output_path"] == str(output) and value["neutral_baseline_path"] == str(baseline) and value["literal_invocation"] == {"environment": ["PYTHONHASHSEED=0"], "argv": [LAUNCHER_ROLE, "--baseline-root", str(baseline), "--output", str(output)]}, "launcher context identity differs")
    _need([item.get("phase") for item in value["timings"]] == ["identity", "managed-tests", "launcher-baseline-admission", "profile-seed-builds"] and all(_keys(item, ("phase", "seconds"), "launcher timing") and type(item["seconds"]) is float and math.isfinite(item["seconds"]) and item["seconds"] >= 0.0 for item in value["timings"]), "launcher context timings differ")
    _need(raw == artifacts.canonical_json_bytes(value), "launcher context is not canonical")
    return value


def _new_receipt(value, raw, path, identity):
    _need(raw == artifacts.canonical_json_bytes(value), "managed-test receipt is not canonical")
    _keys(value, ("schema", "outcome", "invocation", "activation_contract", "design_contract", "existing_dependencies", "additive_implementation_files", "runtime", "runtime_fingerprint_sha256", "executed_test_ids", "required_test_ids", "results"), "activation receipt")
    _need(value["schema"] == "owned-root-assembly-successor-exact-five-managed-test-receipt.v1" and value["outcome"] == "success" and value["activation_contract"] == identity["activation"] and value["design_contract"] == identity["design"] and value["existing_dependencies"] == identity["dependencies"] and value["additive_implementation_files"] == identity["additive_files"] and value["runtime"] == identity["runtime"] and value["runtime_fingerprint_sha256"] == identity["runtime_sha"], "activation receipt identity differs")
    invocation = _keys(value["invocation"], ("environment", "implementation_role", "mode"), "activation invocation")
    _need(invocation == {"environment": ["PYTHONHASHSEED=0"], "implementation_role": RUNNER_ROLE, "mode": "managed-tests"}, "activation invocation differs")
    executed = value["executed_test_ids"]
    _need(type(executed) is list and executed and executed == sorted(set(executed), key=str.encode) and all(type(item) is str and item for item in executed) and value["required_test_ids"] == list(NEW_REQUIRED) and all(executed.count(item) == 1 for item in NEW_REQUIRED), "activation test inventory differs")
    results = _keys(value["results"], ("tests_run", "failures", "errors", "skipped", "expected_failures", "unexpected_successes"), "activation test results")
    _need(all(type(count) is int for count in results.values()) and results == {"tests_run": len(executed), "failures": 0, "errors": 0, "skipped": 0, "expected_failures": 0, "unexpected_successes": 0}, "activation test result differs")
    _need(path.name == "managed-test-receipt.json", "receipt path role differs")
    return value


def publish(baseline_root, bundle_paths, receipt_path, context_path, staging_path):
    identity = _static()
    baseline = _abs(str(baseline_root), "baseline root")
    stage = _abs(str(staging_path), "publication staging")
    context = _context(_abs(str(context_path), "launcher context"), baseline)
    output = _abs(context["output_path"], "output path")
    _need(not os.path.lexists(stage) and not os.path.lexists(output), "publication or final output already exists")
    _need(stage != baseline and not (stage in baseline.parents or baseline in stage.parents), "staging overlaps baseline")
    _need(len(bundle_paths) == 10, "publisher requires exactly ten bundle paths")
    all_inputs = [_abs(str(path), "bundle path") for path in (*bundle_paths, receipt_path, context_path)]
    _need(len(set(all_inputs)) == len(all_inputs), "publisher inputs are not unique")
    for path in all_inputs:
        _need(path != baseline and not (path in baseline.parents or baseline in path.parents) and path != stage and not (path in stage.parents or stage in path.parents) and path != output and not (path in output.parents or output in path.parents), "publisher paths are not disjoint")
    _need(output != baseline and not (output in baseline.parents or baseline in output.parents) and output != stage and not (output in stage.parents or stage in output.parents), "publisher paths are not disjoint")
    start = time.perf_counter()
    baseline_a = _baseline(baseline, identity)
    baseline_seconds = float(time.perf_counter() - start)
    receipt_value, receipt_raw = _json(receipt_path, 16 * 1024 * 1024)
    receipt = _new_receipt(receipt_value, receipt_raw, _abs(str(receipt_path), "receipt"), identity)
    table = _table(identity)
    bundle_values = []
    comparison_values = []
    compare_start = time.perf_counter()
    for index, profile in enumerate(PROFILES):
        for seed in SEEDS:
            bundle_values.append(_bundle(bundle_paths[index * 2 + (seed == 29)], profile, seed, identity, baseline_a["thresholds"], baseline_a["gate_ids"], table))
        comparison_values.append(_compare(bundle_values[-2], bundle_values[-1], BUNDLE_STABLE_ROLES))
    neutral_comparisons = [row for row in baseline_a["report"]["stable_comparisons"] if row["role_path"] in PAYLOAD_ROLES]
    _need([row["role_path"] for row in neutral_comparisons] == list(PAYLOAD_ROLES), "standard-neutral comparison inventory differs")
    for role, expected in zip(PAYLOAD_ROLES, neutral_comparisons):
        left = bundle_values[0]["records"][role]
        _need(left == expected, f"standard-neutral payload differs: {role}")
    os.mkdir(stage)
    public_payloads = []
    for profile, bundle in zip(PROFILES, bundle_values[::2]):
        os.mkdir(stage / profile)
        for role in ("surface-level-2.ply", "direct.png", "lineage.png"):
            data = artifacts.read_regular_file(bundle["root"] / role, max_bytes=2 * 1024 * 1024)
            artifacts.write_bytes_no_replace(stage / profile / role, data)
            public_payloads.append(_record(stage / profile / role, f"{profile}/{role}", 2 * 1024 * 1024))
    baseline_b = _baseline(baseline, identity)
    _need(baseline_a["records"] == baseline_b["records"], "baseline changed during publication")
    post_neutral_comparisons = [row for row in baseline_b["report"]["stable_comparisons"] if row["role_path"] in PAYLOAD_ROLES]
    _need(post_neutral_comparisons == neutral_comparisons, "post-seam neutral comparison differs")
    neutral_comparisons = post_neutral_comparisons
    comparison_seconds = float(time.perf_counter() - compare_start)
    managed_tests = {"receipt_sha256": artifacts.sha256_bytes(receipt_raw), "receipt": receipt}
    profiles = [{"profile_id": profile, "profile_index": index, "evidence": bundle_values[index * 2]["evidence"], "stable_cross_seed_comparisons": comparison_values[index], "neutral_payload_comparisons": neutral_comparisons if index == 0 else []} for index, profile in enumerate(PROFILES)]
    evidence = {"schema": "owned-root-assembly-successor-exact-five-evidence.v1", "outcome": "success", "activation_contract": identity["activation"], "design_contract": identity["design"], "source": identity["source"], "profile_table": identity["profile"], "existing_dependencies": identity["dependencies"], "additive_implementation_files": identity["additive_files"], "managed_tests": managed_tests, "neutral_baseline": {"comparison_report": baseline_b["comparison_record"], "stable_manifest_sha256": BASELINE_STABLE_SHA, "runtime_fingerprint_sha256": identity["runtime_sha"], "payload_comparisons": neutral_comparisons}, "runtime": identity["runtime"], "runtime_fingerprint_sha256": identity["runtime_sha"], "profile_order": list(PROFILES), "profiles": profiles, "payloads": sorted(public_payloads, key=lambda row: row["role_path"].encode())}
    evidence_raw = artifacts.canonical_json_bytes(evidence)
    artifacts.write_bytes_no_replace(stage / "exact-five-evidence.json", evidence_raw)
    evidence_record = _record(stage / "exact-five-evidence.json", "exact-five-evidence.json", 16 * 1024 * 1024)
    evidence_sidecar = f"{artifacts.sha256_bytes(evidence_raw)}  exact-five-evidence.json\n".encode("ascii")
    artifacts.write_bytes_no_replace(stage / "exact-five-evidence.sha256", evidence_sidecar)
    _sidecar(artifacts.read_regular_file(stage / "exact-five-evidence.sha256", max_bytes=256), evidence_raw, "exact-five-evidence.json")
    pre_start = time.perf_counter()
    pre_records = artifacts.closed_inventory(stage, PRE_REPORT_ROLES, max_file_bytes=16 * 1024 * 1024)
    _artifact_caps(pre_records, evidence_role="exact-five-evidence.json")
    _need(len(pre_records) == 17, "pre-report closure is not exactly 17 files")
    pre_seconds = float(time.perf_counter() - pre_start)
    timings = [*context["timings"], {"phase": "publisher-baseline-admission", "seconds": baseline_seconds}, {"phase": "comparison", "seconds": comparison_seconds}, {"phase": "pre-report-closure", "seconds": pre_seconds}]
    timings.append({"phase": "total-before-seal", "seconds": float(sum(item["seconds"] for item in timings))})
    gate_ids = ("exact-five.run.01.identity", "exact-five.run.02.managed-tests", "exact-five.run.03.publisher-baseline-admission", *tuple(f"exact-five.run.{4 + index * 2 + offset:02d}.profile.{profile}.seed-{seed}" for index, profile in enumerate(PROFILES) for offset, seed in enumerate(SEEDS)), *tuple(f"exact-five.run.{14 + index:02d}.profile.{profile}.cross-seed" for index, profile in enumerate(PROFILES)), "exact-five.run.19.standard-neutral-payload-equality", "exact-five.run.20.evidence-graph", "exact-five.run.21.pre-report-closure")
    gates = [{"gate_id": gate, "outcome": "pass", "sample_count": 1, "observed_min": 1, "observed_max": 1, "threshold_id": "gate.boolean-pass"} for gate in gate_ids]
    started_utc, finished_utc = _now(), _now()
    report = {"schema": "owned-root-assembly-successor-exact-five-run-report.v1", "outcome": "success", "literal_invocation": context["literal_invocation"], "output_path": context["output_path"], "staging_path": str(stage), "python_executable_path": os.path.abspath(sys.executable), "neutral_baseline_path": str(baseline), "started_utc": started_utc, "finished_utc": finished_utc, "timings": timings, "activation_contract_sha256": ACTIVATION_SHA, "design_contract_sha256": DESIGN_SHA, "runtime_fingerprint_sha256": identity["runtime_sha"], "evidence": {"role_path": "exact-five-evidence.json", "bytes": evidence_record["bytes"], "sha256": evidence_record["sha256"], "schema": "owned-root-assembly-successor-exact-five-evidence.v1"}, "evidence_sidecar": {"role_path": "exact-five-evidence.sha256", "bytes": len(evidence_sidecar), "sha256": artifacts.sha256_bytes(evidence_sidecar)}, "payloads": sorted(public_payloads, key=lambda row: row["role_path"].encode()), "profile_seed_runs": [{"profile_id": profile, "seed": seed, "outcome": "success", "evidence_sha256": bundle_values[index * 2 + (seed == 29)]["records"]["profile-seed-evidence.json"]["sha256"]} for index, profile in enumerate(PROFILES) for seed in SEEDS], "gates": gates}
    report_raw = artifacts.canonical_json_bytes(report)
    artifacts.write_bytes_no_replace(stage / "run-report.json", report_raw)
    report_sidecar = f"{artifacts.sha256_bytes(report_raw)}  run-report.json\n".encode("ascii")
    artifacts.write_bytes_no_replace(stage / "run-report.sha256", report_sidecar)
    _sidecar(artifacts.read_regular_file(stage / "run-report.sha256", max_bytes=256), report_raw, "run-report.json")
    final_records = artifacts.closed_inventory(stage, PUBLIC_ROLES, max_file_bytes=16 * 1024 * 1024)
    _artifact_caps(final_records, evidence_role="exact-five-evidence.json", total_limit=32 * 1024 * 1024)
    _need(len(final_records) == 19, "final staging closure is not exactly 19 files")
    return stage


def main(argv=None):
    values = sys.argv[1:] if argv is None else argv
    try:
        _need(len(values) == 14, "publisher requires baseline, ten bundles, receipt, context, and staging paths")
        paths = [_abs(value, "publisher path") for value in values]
        _need(paths[0].is_dir() and paths[11].name == "managed-test-receipt.json" and paths[12].name == "launcher-context.json", "publisher input roles differ")
        _need([paths[1 + index].name for index in range(10)] == ["seed-17", "seed-29"] * 5, "publisher bundle order differs")
        _need(not os.path.lexists(paths[13]), "publication staging path is not absent")
        publish(paths[0], paths[1:11], paths[11], paths[12], paths[13])
    except Exception as exc:
        print(f"exact-five publisher: error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
