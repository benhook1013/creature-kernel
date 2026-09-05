"""Private managed-test and profile/seed runner for the frozen exact-five gate."""
from __future__ import annotations

import datetime
import importlib.metadata
import importlib.util
import json
import locale
import math
import os
import platform
import re
import shutil
import struct
import sys
import sysconfig
import tempfile
import time
import unittest
import zlib
from decimal import Decimal, ROUND_HALF_EVEN, localcontext
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
NEUTRAL = ROOT / "experiments/owned-root-assembly-successor"
PROFILE_PACKAGE = ROOT / "experiments/current-form-surface-preview"
TESTS = ROOT / "experiments/owned-root-assembly-successor-exact-five/tests"
for _module_path in (str(NEUTRAL), str(PROFILE_PACKAGE)):
    if _module_path not in sys.path:
        sys.path.insert(0, _module_path)

import anatomy_gates as anatomy
import artifact_serialization as artifacts
import chart_lineage as chart
import generate_structural_profile_sources as profiles
import mesh_correctness as mesh_api
import owned_root_surface as surface
import prepared_projection as neutral_projection
import render_export as render

ACTIVATION_ROLE = "experiments/owned-root-assembly-successor/exact-five-activation-contract.md"
ACTIVATION_SIDECAR_ROLE = "experiments/owned-root-assembly-successor/exact-five-activation-contract.sha256"
DESIGN_ROLE = "experiments/owned-root-assembly-successor/design-contract.md"
SOURCE_ROLE = "examples/body-documents/stylized-digitigrade-biped-authored-form.json"
PROFILE_ROLE = "experiments/current-form-surface-preview/structural_profile_candidates.json"
RUNNER_ROLE = "experiments/owned-root-assembly-successor-exact-five/exact_five_runner.py"
EXPECTED_ACTIVATION_SHA256 = "a5c38645c810efb24e79297fb7c8049f0f59529f37a67c18a5a728a7119f0d49"
EXPECTED_DESIGN_SHA256 = "3122f0db2235754ed782bd38a88c4d7ad7cc7edbf635d147194f1e93f8556490"
EXPECTED_SOURCE_SHA256 = "82269e843555ff1aad3c66399e3fcaeb11bbee81d72b69d15765ea9c4e7aff14"
EXPECTED_PROFILE_SHA256 = "a5fba6643d0031bac83c08e9093e11fd7945806963509fa939865866112d9640"
RUNTIME_SHA256 = "c19ca9c0b8268504f93513d55f90a0eb63777e566aba06e376b503c5e648f085"
PROFILE_IDS = (
    "standard_neutral_reference", "compact_broad_short_limb_large_head",
    "tall_narrow_long_legged", "slender_long_limb", "stocky_broad_chested",
)
PARAMETER_IDS = tuple(neutral_projection.MUST_AFFECT_PARAMETER_IDS)
PROFILE_SEEDS = (17, 29)
MUST_AFFECT_PARAMETER_IDS = PARAMETER_IDS
MUST_AFFECT_COMPONENTS = neutral_projection.MUST_AFFECT_COMPONENTS
SURFACE_ROLES = tuple(f"surface-level-{level}.ply" for level in range(3))
PERTURBATION_ROLES = tuple(f"perturb-{name.replace('.', '-')}.ply" for name in PARAMETER_IDS)
PAYLOAD_ROLES = (*SURFACE_ROLES, *PERTURBATION_ROLES, "direct.png", "lineage.png")
BUNDLE_ROLES = (*PAYLOAD_ROLES, "profile-seed-evidence.json", "profile-seed-evidence.sha256", "run-report.json", "run-report.sha256")
STABLE_ROLES = tuple(sorted((*PAYLOAD_ROLES, "profile-seed-evidence.json", "profile-seed-evidence.sha256")))
PUBLIC_ROLES = tuple(f"{profile}/{role}" for profile in PROFILE_IDS for role in ("surface-level-2.ply", "direct.png", "lineage.png")) + ("exact-five-evidence.json", "exact-five-evidence.sha256", "run-report.json", "run-report.sha256")
PINNED_LAUNCHER_ROLE = "experiments/current-form-surface-preview/surface_preview_launcher.sh"
FINAL_GATE_IDS = tuple("""exact-five.run.01.identity
exact-five.run.02.managed-tests
exact-five.run.03.publisher-baseline-admission
exact-five.run.04.profile.standard_neutral_reference.seed-17
exact-five.run.05.profile.standard_neutral_reference.seed-29
exact-five.run.06.profile.compact_broad_short_limb_large_head.seed-17
exact-five.run.07.profile.compact_broad_short_limb_large_head.seed-29
exact-five.run.08.profile.tall_narrow_long_legged.seed-17
exact-five.run.09.profile.tall_narrow_long_legged.seed-29
exact-five.run.10.profile.slender_long_limb.seed-17
exact-five.run.11.profile.slender_long_limb.seed-29
exact-five.run.12.profile.stocky_broad_chested.seed-17
exact-five.run.13.profile.stocky_broad_chested.seed-29
exact-five.run.14.profile.standard_neutral_reference.cross-seed
exact-five.run.15.profile.compact_broad_short_limb_large_head.cross-seed
exact-five.run.16.profile.tall_narrow_long_legged.cross-seed
exact-five.run.17.profile.slender_long_limb.cross-seed
exact-five.run.18.profile.stocky_broad_chested.cross-seed
exact-five.run.19.standard-neutral-payload-equality
exact-five.run.20.evidence-graph
exact-five.run.21.pre-report-closure""".splitlines())
LEVEL_COUNTS = ((120, 227, 104, 208, 38), (451, 870, 416, 832, 76), (1737, 3404, 1664, 3328, 152))
PHASES = ("identity", "selection-projection", "catalogs", "geometry-gates", "causality", "serialization", "total-before-seal")
RUN_GATES = tuple(f"seed.{index}.{name}" for index, name in enumerate(("identity", "prepared-input", "catalogs", "geometry-gates", "causality", "serialization"), 1))
ADDITIVE_ROLES = tuple(sorted((
    "experiments/owned-root-assembly-successor-exact-five/exact_five_launcher.sh",
    RUNNER_ROLE,
    "experiments/owned-root-assembly-successor-exact-five/exact_five_publisher.py",
    "experiments/owned-root-assembly-successor-exact-five/tests/test_exact_five_activation.py",
), key=str.encode))
DEPENDENCIES = tuple(sorted((
    ("experiments/owned-root-assembly-successor/anatomy_gates.py", 25674, "0c4b5f7812141a4cd7c7107655e578044355dfef5dbda6574bbb63bc359a2ff4"),
    ("experiments/owned-root-assembly-successor/artifact_serialization.py", 27977, "3837928e4b987c65fd773e540f7db502f5d9a0b4c5940b95c923953754fdf7d4"),
    ("experiments/owned-root-assembly-successor/build_owned_root.py", 78268, "713cbf967bf2e0e233bae0c3506199fdc9a6ed71418edbd8dbf9b75beeee4045"),
    ("experiments/owned-root-assembly-successor/chart_lineage.py", 18263, "01fdd09e8e0bb6d31851f0c7af711d90b313e36a012dbe3d71415a0468c31efc"),
    ("experiments/owned-root-assembly-successor/mesh_correctness.py", 51035, "4104b70e70e958a469125d1fff544e20fee44b784bf7915d8e724e63d4f39db1"),
    ("experiments/owned-root-assembly-successor/owned_root_surface.py", 58732, "c982d889fee30e2efea881b5725170740bc8afa2a883aa3dc4623941cd3e2a22"),
    ("experiments/owned-root-assembly-successor/prepared_projection.py", 39646, "58637097a350332db40368a027347ec395192880aa6ba4782c7d523e5b288190"),
    ("experiments/owned-root-assembly-successor/render_export.py", 15933, "bc251ea3f3f3cb1aa5ea66bfc4f79a82f86191e76bacb9a3c4f58e64883c4780"),
    ("experiments/current-form-surface-preview/generate_structural_profile_sources.py", 54437, "009be817cd2ec2db663b668fb5c9bdfa7296936283322e59d7a145e3d3cfec62"),
    ("experiments/current-form-surface-preview/structural_atomic_publish.py", 10489, "5e648b3a1a3519afdf0fc1f2f1ecfe6fe7f1c58130f71fd2c8ee4317e2f282b5"),
    ("experiments/current-form-surface-preview/surface_preview_launcher.sh", 6582, "3e18da2d361029a16558757d9727150d54c4d691b35c6a2a21b5b51cb7785190"),
    ("experiments/current-form-surface-preview/requirements.txt", 49, "69a3ce10b1f993d7913f02ca187eabb8d367abf214662ffa2132feacbdeedbec"),
), key=lambda row: row[0].encode()))
EXPECTED_DEPENDENCY_ROLES = tuple(row[0] for row in DEPENDENCIES)
ADDITIVE_IMPLEMENTATION_ROLES = ADDITIVE_ROLES
REQUIRED_TEST_IDS = tuple(sorted("""test_exact_five_activation.ExactFiveActivationTests.test_all_33_selectors_copy_one_component
test_exact_five_activation.ExactFiveActivationTests.test_atomic_failure_has_no_partial_publication
test_exact_five_activation.ExactFiveActivationTests.test_decimal_half_even_boundaries
test_exact_five_activation.ExactFiveActivationTests.test_final_evidence_schema_and_19_file_closure
test_exact_five_activation.ExactFiveActivationTests.test_geometry_receives_only_components
test_exact_five_activation.ExactFiveActivationTests.test_neutral_projection_preserves_38_payloads
test_exact_five_activation.ExactFiveActivationTests.test_profile_seed_bundle_schema_and_closure
test_exact_five_activation.ExactFiveActivationTests.test_profile_table_closed_and_exact_order
test_exact_five_activation.ExactFiveActivationTests.test_profile_table_rejects_duplicate_keys_and_signatures
test_exact_five_activation.ExactFiveActivationTests.test_projection_has_exact_92_bindings
test_exact_five_activation.ExactFiveActivationTests.test_seed_dispatch_is_exact
test_exact_five_activation.ExactFiveActivationTests.test_static_identity_and_allowlist""".splitlines(), key=str.encode))
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_RUNTIME_DISTS = (("imageio", "2.37.4"), ("lazy-loader", "0.5"), ("networkx", "3.4.2"), ("numpy", "2.2.6"), ("packaging", "26.3"), ("pillow", "11.1.0"), ("scikit-image", "0.25.2"), ("scipy", "1.15.3"), ("tifffile", "2025.5.10"))


class ExactFiveError(ValueError):
    """A frozen exact-five admission, build, gate, or sealing failure."""


def _need(condition: bool, message: str) -> None:
    if not condition:
        raise ExactFiveError(message)


def _ordered(values):
    return sorted(values, key=lambda value: value.encode("utf-8"))


def _record(role: str, expected_bytes: int | None = None, expected_hash: str | None = None) -> dict[str, Any]:
    path = ROOT / role
    _need(not path.is_symlink() and path.is_file(), f"missing or non-regular fixed file: {role}")
    record = artifacts.regular_file_record(path, role, max_bytes=4 * 1024 * 1024)
    _need(expected_bytes is None or record["bytes"] == expected_bytes, f"byte count mismatch: {role}")
    _need(expected_hash is None or record["sha256"] == expected_hash, f"SHA-256 mismatch: {role}")
    return record


def _runtime(launcher: dict[str, Any], requirements: dict[str, Any]) -> dict[str, Any]:
    _need((platform.python_implementation(), platform.python_version(), getattr(sys.implementation, "cache_tag", None)) == ("CPython", "3.10.12", "cpython-310"), "runtime is not pinned CPython 3.10.12")
    distributions = []
    for name, expected in _RUNTIME_DISTS:
        try:
            actual = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError as exc:
            raise ExactFiveError(f"missing distribution: {name}=={expected}") from exc
        _need(actual == expected, f"distribution drift: {name}=={actual}")
        distributions.append({"name": name, "version": actual})
    builtins = []
    for name in ("math", "zlib"):
        module, spec = __import__(name), importlib.util.find_spec(name)
        _need(getattr(module, "__file__", None) is None and spec is not None and spec.origin == "built-in", f"{name} is not built-in")
        compile_version, runtime_version = (None, None) if name == "math" else (zlib.ZLIB_VERSION, zlib.ZLIB_RUNTIME_VERSION)
        builtins.append({"module_name": name, "__file__": None, "find_spec_origin": "built-in", "compile_version": compile_version, "runtime_version": runtime_version})
    libc_name, libc_version = platform.libc_ver()
    runtime = {
        "schema": "owned-root-assembly-successor-runtime.v2",
        "python": {"implementation": "CPython", "version": "3.10.12", "build": " ".join(platform.python_build()), "compiler": platform.python_compiler(), "cache_tag": "cpython-310", "abiflags": getattr(sys, "abiflags", ""), "soabi": sysconfig.get_config_var("SOABI")},
        "platform": {"system": platform.system(), "release": platform.release(), "version": platform.version(), "machine": platform.machine(), "pointer_bits": 8 * struct.calcsize("P"), "byteorder": sys.byteorder, "libc_name": libc_name, "libc_version": libc_version},
        "locale": {"active": locale.setlocale(locale.LC_ALL, None), "preferred_encoding": locale.getpreferredencoding(False)},
        "managed_launcher": launcher, "requirements": requirements,
        "direct_distributions": [next(row for row in distributions if row["name"] == name) for name in ("numpy", "scikit-image", "pillow")],
        "resolved_distributions": distributions, "builtin_modules": builtins,
    }
    _need(runtime["platform"]["system"] == "Linux" and type(runtime["python"]["soabi"]) is str, "runtime platform is not admitted")
    raw = artifacts.canonical_json_bytes(runtime)
    _need(len(raw) <= 64 * 1024 and artifacts.sha256_bytes(raw) == RUNTIME_SHA256, "runtime fingerprint mismatch")
    return runtime


def static_admission() -> dict[str, Any]:
    """Bind every frozen input, dependency, additive source, and runtime."""
    activation = _record(ACTIVATION_ROLE, 53777, EXPECTED_ACTIVATION_SHA256)
    expected_sidecar = f"{EXPECTED_ACTIVATION_SHA256}  {ACTIVATION_ROLE}\n".encode("ascii")
    _need(artifacts.read_regular_file(ROOT / ACTIVATION_SIDECAR_ROLE, max_bytes=256) == expected_sidecar, "activation sidecar mismatch")
    design = _record(DESIGN_ROLE, 173184, EXPECTED_DESIGN_SHA256)
    source = _record(SOURCE_ROLE, 56984, EXPECTED_SOURCE_SHA256)
    table = _record(PROFILE_ROLE, 29970, EXPECTED_PROFILE_SHA256)
    dependencies = tuple(_record(*row) for row in DEPENDENCIES)
    package = ROOT / "experiments/owned-root-assembly-successor-exact-five"
    found = []
    for directory, subdirectories, filenames in os.walk(package, followlinks=False):
        _need(not Path(directory).is_symlink(), "additive package contains a symlink directory")
        for name in filenames:
            path = Path(directory) / name
            if path.suffix in (".py", ".sh"):
                _need(not path.is_symlink(), "additive package contains a symlink source")
                found.append(path.relative_to(ROOT).as_posix())
        subdirectories[:] = [name for name in subdirectories if not (Path(directory) / name).is_symlink()]
    _need(tuple(_ordered(found)) == ADDITIVE_ROLES, "additive implementation allowlist mismatch")
    additive = tuple(_record(role) for role in ADDITIVE_ROLES)
    production_loc = sum(artifacts.read_regular_file(ROOT / row["role_path"]).count(b"\n") for row in additive if "/tests/" not in row["role_path"])
    test_loc = sum(artifacts.read_regular_file(ROOT / row["role_path"]).count(b"\n") for row in additive if "/tests/" in row["role_path"])
    _need(production_loc <= 1600 and test_loc <= 1200, f"additive LOC cap exceeded: production={production_loc}, tests={test_loc}")
    launcher = next(row for row in dependencies if row["role_path"].endswith("surface_preview_launcher.sh"))
    requirements = next(row for row in dependencies if row["role_path"].endswith("requirements.txt"))
    _need(artifacts.read_regular_file(ROOT / requirements["role_path"]) == b"numpy==2.2.6\nscikit-image==0.25.2\nPillow==11.1.0\n", "requirements drift")
    runtime = _runtime(launcher, requirements)
    return {"activation_contract": activation, "design_contract": design, "source": source, "profile_table": table, "existing_dependencies": dependencies, "additive_implementation_files": additive, "runtime": runtime, "runtime_fingerprint_sha256": RUNTIME_SHA256}


def run_managed_tests(receipt_path: str | os.PathLike[str]) -> dict[str, Any]:
    _need(os.environ.get("PYTHONHASHSEED") == "0", "managed tests require literal PYTHONHASHSEED=0")
    receipt = Path(receipt_path)
    _need(receipt.is_absolute() and os.path.normpath(str(receipt)) == str(receipt) and not os.path.lexists(receipt), "receipt must be canonical, absolute, and absent")
    _need(not receipt.parent.is_symlink() and receipt.parent.parent.is_dir() and (not receipt.parent.exists() or receipt.parent.is_dir()), "receipt parent is not staging-safe")
    before = static_admission()
    sys.path.insert(0, str(TESTS))
    try:
        suite = unittest.TestLoader().discover(str(TESTS), pattern="test_*.py")
        def flatten(node):
            for item in node:
                yield from flatten(item) if isinstance(item, unittest.TestSuite) else (item,)
        tests = tuple(flatten(suite)); ids = tuple(test.id() for test in tests)
        _need(ids and len(ids) == len(set(ids)) and all(ids.count(required) == 1 for required in REQUIRED_TEST_IDS), "managed discovery missed a required exact-five test")
        result = unittest.TestResult(); suite.run(result)
    finally:
        if sys.path and sys.path[0] == str(TESTS):
            sys.path.pop(0)
    after = static_admission()
    _need(artifacts.canonical_json_bytes(before) == artifacts.canonical_json_bytes(after), "identity changed during managed tests")
    _need(result.testsRun == len(ids) and not (result.failures or result.errors or result.skipped or result.expectedFailures or result.unexpectedSuccesses), "managed tests did not all pass")
    value = {"schema": "owned-root-assembly-successor-exact-five-managed-test-receipt.v1", "outcome": "success", "invocation": {"environment": ["PYTHONHASHSEED=0"], "implementation_role": RUNNER_ROLE, "mode": "managed-tests"}, "activation_contract": after["activation_contract"], "design_contract": after["design_contract"], "existing_dependencies": list(after["existing_dependencies"]), "additive_implementation_files": list(after["additive_implementation_files"]), "runtime": after["runtime"], "runtime_fingerprint_sha256": RUNTIME_SHA256, "executed_test_ids": _ordered(ids), "required_test_ids": list(REQUIRED_TEST_IDS), "results": {"tests_run": len(ids), "failures": 0, "errors": 0, "skipped": 0, "expected_failures": 0, "unexpected_successes": 0}}
    raw = artifacts.canonical_json_bytes(value); _need(len(raw) <= 16 * 1024 * 1024, "managed-test receipt exceeds 16 MiB")
    receipt.parent.mkdir(exist_ok=True); artifacts.write_bytes_no_replace(receipt, raw)
    return value


def project_decimal_metres(token: int | Decimal, scale: int) -> tuple[Decimal, float]:
    """Apply the exact permille, half-even millimetre projection rule."""
    _need(type(scale) is int and 1 <= scale <= 10000 and not isinstance(token, bool) and isinstance(token, (int, Decimal)), "invalid decimal projection input")
    value = Decimal(token)
    _need(value.is_finite() and value > 0, "source dimension is not finite and positive")
    with localcontext() as context:
        context.prec = max(context.prec, len(value.as_tuple().digits) + len(str(scale)) + 2)
        q = (value * Decimal(scale)).to_integral_value(rounding=ROUND_HALF_EVEN)
        projected = q / Decimal(1000)
    _need(projected > 0 and projected.is_finite(), "dimension quantized to zero or non-finite")
    number = float(projected)
    _need(math.isfinite(number) and Decimal(str(number)) == projected, "projected decimal cannot round-trip through binary64")
    return projected, number


def _pointer_get(root: Any, pointer: str) -> Any:
    _need(pointer.startswith("/") and pointer != "/", "invalid canonical pointer")
    value = root
    for token in pointer[1:].split("/"):
        token = token.replace("~1", "/").replace("~0", "~")
        value = value[int(token)] if type(value) is list and token.isdigit() and (token == "0" or not token.startswith("0")) else value[token]
    return value


def _escape_pointer(value: str) -> str:
    return value.replace("~", "~0").replace("/", "~1")


def _dimension_group(component: str) -> str:
    if component.startswith("stations."):
        neck = component.split(".")[1] in ("neck_collar", "neck_upper")
        return ("neck_profile_lateral" if component.endswith(".rL") else "neck_profile_forward") if neck else ("body_profile_lateral" if component.endswith(".rL") else "body_profile_depth")
    if component.startswith("shoulders."):
        return {"start_lateral": "arm_profile_lateral", "start_up": "arm_profile_up", "start_forward": "arm_profile_forward", "shoulder_depth": "arm_shoulder"}[component.rsplit(".", 1)[1]]
    return {"r_x": "leg_profile_lateral", "r_y": "leg_profile_up", "r_z": "leg_profile_forward"}[component.rsplit(".", 1)[1]]


def validate_profile_table(table: dict[str, Any]) -> dict[str, Any]:
    """Validate the complete closed active-five table against the fixed source."""
    source, raw = profiles.load_json_with_bytes(ROOT / SOURCE_ROLE, "authored source")
    _need(artifacts.sha256_bytes(raw) == EXPECTED_SOURCE_SHA256, "fixed source identity mismatch")
    profiles.generate_sources(table, source, mode=profiles.DEFAULT_GENERATION_MODE)
    return table


def admit_profile_table(raw: bytes) -> dict[str, Any]:
    """Admit only the exact fixed canonical profile-table bytes."""
    _need(type(raw) is bytes and len(raw) == 29970 and artifacts.sha256_bytes(raw) == EXPECTED_PROFILE_SHA256, "profile table identity mismatch")
    def pairs(items):
        value = dict(items); _need(len(value) == len(items), "profile table contains a duplicate key"); return value
    try:
        table = json.loads(raw.decode("utf-8"), object_pairs_hook=pairs, parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)))
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError, TypeError, ValueError) as exc:
        raise ExactFiveError("profile table is not strict finite UTF-8 JSON") from exc
    _need(type(table) is dict, "profile table is not an object")
    return validate_profile_table(table)


def select_profile(table: dict[str, Any], profile_id: str) -> dict[str, Any]:
    """Select one exact ID only after complete-table validation."""
    validate_profile_table(table); _need(type(profile_id) is str and profile_id in PROFILE_IDS, "unknown exact profile ID")
    matches = [(index, row) for index, row in enumerate(table["profiles"]) if row["id"] == profile_id]
    _need(len(matches) == 1, "profile selection is not unique")
    return {"id": profile_id, "index": matches[0][0], "row": matches[0][1]}


def project_profile(profile_id: str, source: dict[str, Any] | None = None, table: dict[str, Any] | None = None) -> dict[str, Any]:
    """Validate all five transforms, select one exact row, and form 92 numbers."""
    _need(type(profile_id) is str and profile_id in PROFILE_IDS, "unknown exact profile ID")
    if source is None:
        source, source_raw = profiles.load_json_with_bytes(ROOT / SOURCE_ROLE, "authored source")
        _need(artifacts.sha256_bytes(source_raw) == EXPECTED_SOURCE_SHA256, "fixed source identity mismatch")
    if table is None:
        table, table_raw = profiles.load_json_with_bytes(ROOT / PROFILE_ROLE, "profile table")
        _need(artifacts.sha256_bytes(table_raw) == EXPECTED_PROFILE_SHA256, "fixed profile table identity mismatch")
    generated = profiles.generate_sources(table, source, mode=profiles.DEFAULT_GENERATION_MODE)
    rows = table.get("profiles") if type(table) is dict else None
    _need(type(rows) is list and len(rows) == 5 and tuple(row.get("id") for row in rows if type(row) is dict) == PROFILE_IDS, "profile order is not exact")
    matches = [(index, row) for index, row in enumerate(rows) if row["id"] == profile_id]
    _need(len(matches) == 1, "profile selection is not unique")
    profile_index, row = matches[0]; transformed = generated[profile_index]
    bindings, projected_values, values = [], [], []
    source_bindings = neutral_projection.source_binding_records()
    _need(tuple(item["prepared_component"] for item in source_bindings) == tuple(surface.GEOMETRY_COMPONENT_IDS), "neutral binding component universe drift")
    for original in source_bindings:
        component, source_pointers = original["prepared_component"], list(original["source_pointers"])
        if original["derivation_id"] == "source.dimension-value.v1":
            group = _dimension_group(component); scale = row["dimension_scales"][group]
            projected, number = project_decimal_metres(_pointer_get(source, source_pointers[0]), scale)
            _need(Decimal(str(_pointer_get(transformed, source_pointers[0]))) == projected, f"profile generator disagrees for {component}")
            profile_pointers = [f"/profiles/{profile_index}/dimension_scales/{_escape_pointer(group)}"]
            derivation = "profile.dimension-permille-half-even-mm.v1"
        else:
            part_pointers = sorted((pointer for pointer in source_pointers if pointer.startswith("/body/parts/")), key=lambda pointer: int(pointer.split("/")[3]))
            landmark_pointers = [pointer for pointer in source_pointers if pointer.startswith("/body/landmarks/")]
            _need(len(landmark_pointers) == (1 if "landmark" in original["derivation_id"] else 0), f"sum pointer inventory differs for {component}")
            number = 0.0
            for pointer in part_pointers:
                value = _pointer_get(transformed, pointer); _need(type(value) is int and abs(value) <= 1_000_000_000, "placement is not a bounded exact integer")
                number = number + float(value)
            for pointer in landmark_pointers:
                number = number + float(_pointer_get(transformed, pointer))
            _need(math.isfinite(number), f"world sum is non-finite for {component}")
            profile_pointers = []
            for pointer in part_pointers:
                pieces = pointer.split("/"); part_index, axis = int(pieces[3]), int(pieces[-1])
                key = profiles.address_key(source["body"]["parts"][part_index]["address"])
                profile_pointers.append(f"/profiles/{profile_index}/part_placements/{_escape_pointer(key)}/{axis}")
            derivation = "profile.world-landmark-axis-sum.v1" if landmark_pointers else "profile.world-placement-axis-sum.v1"
        profile_pointers = _ordered(profile_pointers)
        binding = {"prepared_component": component, "derivation_id": derivation, "source_addresses": original["source_addresses"], "source_pointers": source_pointers, "profile_pointers": profile_pointers}
        record = {"prepared_component": component, "value": number, "source_pointers": source_pointers, "profile_pointers": profile_pointers}
        bindings.append(binding); projected_values.append(record); values.append(number)
    _need(len(bindings) == 92 and len({row["prepared_component"] for row in bindings}) == 92, "projection is not exactly 92 unique bindings")
    carrier = surface.GeometryComponents(tuple(values)); surface.validate_geometry_components(carrier)
    carrier_raw = artifacts.canonical_json_bytes(list(carrier.values))
    selection = {"profile_pointer": f"/profiles/{profile_index}", "profile_row_sha256": artifacts.sha256_bytes(artifacts.canonical_json_bytes(row)), "dimension_scales_sha256": artifacts.sha256_bytes(artifacts.canonical_json_bytes(row["dimension_scales"])), "part_placements_sha256": artifacts.sha256_bytes(artifacts.canonical_json_bytes(row["part_placements"]))}
    return {"profile_id": profile_id, "profile_index": profile_index, "selection": selection, "carrier": carrier, "projected_values": projected_values, "projected_carrier": {"bytes": len(carrier_raw), "sha256": artifacts.sha256_bytes(carrier_raw)}, "projection_bindings": bindings}


def _gate(gate_id, count, minimum, maximum, relation, lower, upper, unit):
    threshold = {"threshold_id": f"threshold.{gate_id}", "relation": relation, "lower": lower, "upper": upper, "unit": unit}
    passed = minimum == lower and maximum == upper if relation == "eq" else minimum >= lower if relation == "ge" else maximum <= upper if relation == "le" else maximum < upper
    return {"gate_id": gate_id, "outcome": "pass" if passed else "fail", "sample_count": count, "observed_min": minimum, "observed_max": maximum, "threshold_id": threshold["threshold_id"]}, threshold


def _put(rows, thresholds, pair):
    rows.append(pair[0]); thresholds.append(pair[1])


def _bool(gate_id):
    return _gate(gate_id, 1, 1, 1, "eq", 1, 1, "boolean")


def _directions():
    vectors = {"+X": (1.0, 0.0, 0.0), "-X": (-1.0, 0.0, 0.0), "+Y": (0.0, 1.0, 0.0), "-Y": (0.0, -1.0, 0.0)}
    return {name: vectors[info[1]] for name, info in surface.PORT_INFO.items()}


def _chart_owners(mesh, summary):
    rows = [row for row in summary["chart_records"] if row["level"] == mesh.level]; owners = {}
    for row in rows:
        _need(row["face_id"] not in owners, "duplicate chart face ownership"); owners[row["face_id"]] = row["construction_owner"]
    _need(len(rows) == len(mesh.face_ids) and set(owners) == set(mesh.face_ids), "chart face incidence is incomplete")
    return tuple(owners[face_id] for face_id in mesh.face_ids)


def _junction_cycles(mesh, owners, domains):
    uses = {}
    for face_index, face in enumerate(mesh.quads):
        for slot, left in enumerate(face):
            right = face[(slot + 1) % 4]; uses.setdefault(tuple(sorted((left, right))), []).append((owners[face_index], left, right))
    result = []
    for domain in domains:
        following = {}
        for rows in uses.values():
            if len(rows) == 2 and frozenset(row[0] for row in rows) == frozenset(domains):
                selected = [row for row in rows if row[0] == domain]; _need(len(selected) == 1 and selected[0][1] not in following, "junction trace is not unique"); following[selected[0][1]] = selected[0][2]
        _need(following, "junction trace is empty"); start = current = min(following); cycle = []
        while current not in cycle:
            cycle.append(current); _need(current in following, "junction trace is open"); current = following[current]
        _need(current == start and len(cycle) == len(following), "junction trace is not one cycle"); result.append(tuple(cycle))
    return tuple(result)


def _half_tag(left, right):
    numerator = left[0] * right[1] + right[0] * left[1]; denominator = 2 * left[1] * right[1]; common = math.gcd(abs(numerator), denominator)
    return numerator // common, denominator // common


def _domain_tags(meshes, owners, domains, domain_index, axes, level):
    axis_index = {"i": 0, "j": 1, "k": 2}; cycles = tuple(_junction_cycles(mesh, owner, domains)[domain_index] for mesh, owner in zip(meshes[:level + 1], owners[:level + 1]))
    tags = {vertex: tuple((surface.COORDINATE_BY_CONTROL[meshes[0].control_ids[vertex]][axis_index[axis]], 1) for axis in axes) for vertex in cycles[0]}
    for current in range(1, level + 1):
        points = dict(surface.subdivision_incidence(meshes[current - 1])["edge_point_indices"]); previous = cycles[current - 1]; out = {vertex: tags[vertex] for vertex in cycles[current] if vertex in tags}
        for slot, left in enumerate(previous):
            right = previous[(slot + 1) % len(previous)]; point = points.get(tuple(sorted((left, right)))); _need(point is not None, "junction midpoint absent"); out[point] = tuple(_half_tag(tags[left][axis], tags[right][axis]) for axis in range(2))
        _need(set(out) == set(cycles[current]), "junction tag incidence incomplete"); tags = out
    return dict(sorted(tags.items()))


def _junction_inputs(evaluation, level, summary):
    meshes = (evaluation.cage, *evaluation.levels); owners = tuple(_chart_owners(mesh, summary) for mesh in meshes); result = {}
    for junction in surface.JUNCTIONS:
        domains, (_drop, axes) = surface.JUNCTION_INFO[junction]
        maps = tuple(_domain_tags(meshes, owners, domains, index, axes, level) for index in range(2)); reference = tuple(dict(surface.propagate_junction_tags(evaluation, junction)[level]) for _ in domains)
        result[junction] = {"incident_domains": domains, "domain_vertex_tags": maps, "expected_domain_vertex_tags": reference}
    return result


def _metrics(mesh):
    edges = {tuple(sorted((left, face[(slot + 1) % 4]))) for face in mesh.quads for slot, left in enumerate(face)}
    sub = lambda a, b: tuple(a[i] - b[i] for i in range(3)); cross = lambda a, b: (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]); norm = lambda value: math.sqrt(sum(item * item for item in value))
    edge_values = tuple(norm(sub(mesh.vertices[right], mesh.vertices[left])) for left, right in sorted(edges)); triangles, quads = [], []
    for face in mesh.quads:
        a, b, c, d = (mesh.vertices[index] for index in face); areas = (0.5 * norm(cross(sub(b, a), sub(c, a))), 0.5 * norm(cross(sub(c, a), sub(d, a)))); triangles.extend(areas); quads.append(sum(areas))
    return edge_values, tuple(triangles), tuple(quads)


def _edge_uses(mesh):
    uses = {}
    for face_index, face in enumerate(mesh.quads):
        for slot, left in enumerate(face):
            uses.setdefault(tuple(sorted((left, face[(slot + 1) % 4]))), []).append(face_index)
    return uses


def _ownership_counts(evaluation, formulas, summary, components, level):
    mesh = (evaluation.cage, *evaluation.levels)[level]; uses = _edge_uses(mesh); expected = LEVEL_COUNTS[level]
    _need((len(mesh.control_ids), len(mesh.quads), len(uses), len(surface.PORTS)) == (expected[0], expected[2], expected[1], 5), "ownership universe changed")
    edges = tuple(uses); keys = tuple(("vertex", value) for value in mesh.control_ids) + tuple(("face", value) for value in mesh.face_ids) + tuple(("edge", value) for value in edges) + tuple(("boundary", value) for value in surface.PORTS)
    required = {key: ("construction", "lineage") if level == 0 and key[0] == "vertex" else ("lineage",) if key[0] == "vertex" else ("chart",) if key[0] == "face" else ("classification",) if key[0] == "edge" else ("boundary",) for key in keys}
    expected_summary = chart.build_chart_summary(evaluation, formulas); formula_by_id = {row["control_id"]: row for row in formulas}; expected_vertices = {(row["level"], row["vertex_id"]): row for row in expected_summary["vertex_records"]}; expected_faces = {(row["level"], row["face_id"]): row for row in expected_summary["chart_records"]}
    records = [(("vertex", row["control_id"]), "construction", row == formula_by_id.get(row["control_id"])) for row in evaluation.cage.formula_records] if level == 0 else []
    records.extend((("vertex", row["vertex_id"]), "lineage", row == expected_vertices.get((level, row["vertex_id"]))) for row in summary["vertex_records"] if row["level"] == level)
    records.extend((("face", row["face_id"]), "chart", row == expected_faces.get((level, row["face_id"]))) for row in summary["chart_records"] if row["level"] == level)
    owners, junction_edges = mesh.face_owners, {}
    for junction in surface.JUNCTIONS:
        domains = surface.JUNCTION_INFO[junction][0]; cycle = _junction_cycles(mesh, owners, domains)[0]
        junction_edges[frozenset(domains)] = {tuple(sorted((left, cycle[(slot + 1) % len(cycle)]))) for slot, left in enumerate(cycle)}
    boundary = {edge for edge, faces in uses.items() if len(faces) == 1}
    for edge, faces in uses.items():
        if len(faces) == 1 and edge in boundary or len(faces) == 2 and owners[faces[0]] == owners[faces[1]] or len(faces) == 2 and edge in junction_edges.get(frozenset(owners[index] for index in faces), ()):
            records.append((("edge", edge), "classification", True))
    records.extend((("boundary", port), "boundary", all(tuple(sorted((left, loop[(slot + 1) % len(loop)]))) in boundary for slot, left in enumerate(loop)) and len(boundary) == sum(len(values) for _, values in mesh.boundary_loops)) for port, loop in mesh.boundary_loops)
    return mesh_api.classify_ownership_records(keys, required, tuple(records))


def _fold_samples(mesh, junction):
    uses = _edge_uses(mesh); domains = frozenset(surface.JUNCTION_INFO[junction][0])
    values = tuple(mesh_api.fold_angle_degrees(mesh_api.quad_normal(mesh.vertices, mesh.quads[faces[0]]), mesh_api.quad_normal(mesh.vertices, mesh.quads[faces[1]])) for faces in uses.values() if len(faces) == 2 and frozenset(mesh.face_owners[index] for index in faces) == domains)
    _need(values, f"no fold samples for {junction}"); return values


def _sample(rows, thresholds, gate_id, values, relation, lower, upper, unit):
    values = tuple(values); _need(values and all(math.isfinite(value) for value in values), f"empty/non-finite gate samples: {gate_id}")
    _put(rows, thresholds, _gate(gate_id, len(values), min(values), max(values), relation, lower, upper, unit))


def _catalog_gates():
    surface.validate_catalogs(); values = {"selected_cells": 58, "un_capped_faces": 122, "domains": 8, "junctions": 7, "ports": 5, "controls": 120, "base_quads": 104, "base_edges": 227, "base_boundary_edges": 38, "boundary_components": 5, "connected_components": 1, "euler_characteristic": -3, "extraordinary_controls": 20, "special_case_ids": 9, "topology_decision_sites": 3}
    booleans = "all_domains_nonempty selected_cell_inventory_exact control_catalog_exact face_catalog_exact junction_catalog_exact port_catalog_exact special_case_catalog_exact base_face_controls_distinct base_edge_use_within_two construction_ownership_complete port_caps_exactly_removed axillary_fixture_suite_complete intersection_fixture_suite_complete".split(); gates, thresholds = [], []
    for name, value in values.items():
        relation, lower, upper = ("le", None, 3) if name == "topology_decision_sites" else ("eq", value, value); _put(gates, thresholds, _gate(f"structural.catalog.{name}", 1, value, value, relation, lower, upper, "dimensionless" if name == "euler_characteristic" else "count"))
    for name in booleans:
        _put(gates, thresholds, _bool(f"structural.catalog_boolean.{name}"))
    return gates, thresholds


def run_geometry(components: surface.GeometryComponents) -> dict[str, Any]:
    """Run unchanged neutral geometry and gates from only the numeric carrier."""
    _need(type(components) is surface.GeometryComponents, "geometry accepts only GeometryComponents")
    surface.validate_geometry_components(components)
    axillary, intersections = anatomy.run_production_axillary_fixtures(), mesh_api.run_production_intersection_fixtures()
    _need(len(axillary) == 13 and tuple(row["fixture_id"] for row in axillary) == anatomy.AXILLARY_FIXTURE_IDS, "axillary fixtures drift")
    _need(len(intersections) == 105 and tuple(row["fixture_id"] for row in intersections) == mesh_api.INTERSECTION_FIXTURE_IDS, "intersection fixtures drift")
    evaluation = surface.evaluate(components); meshes = (evaluation.cage, *evaluation.levels); formulas = tuple(surface.formula_candidate_records(components)); summary = chart.build_chart_summary(evaluation, formulas)
    chart.validate_chart_summary(summary, evaluation, formulas); anatomy.validate_evaluated_surface(evaluation, components, summary); anatomy_rows = tuple(anatomy.anatomy_gate_records(evaluation, components, summary))
    expected_faces = tuple(tuple(int(control[1:]) for control in row[2]) for row in surface.FACE_RECORDS)
    _need(tuple(len(rows) for rows in mesh_api.derive_expected_face_catalogs(expected_faces)) == (104, 416, 1664), "topology derivation drift")
    reports = [mesh_api.validate_geometry(mesh.vertices, mesh.quads, level, dict(mesh.boundary_loops), _directions(), expected_faces, _junction_inputs(evaluation, level, summary), mesh.face_owners) for level, mesh in enumerate(meshes)]
    structural, thresholds = _catalog_gates(); chart_counts = {row["level"]: row for row in summary["level_counts"]}
    invalid_names = "duplicate_vertex_ids duplicate_face_ids degenerate_faces zero_length_edges non_manifold_edges orientation_conflicts unowned_elements overowned_elements accidental_boundary_components".split()
    for level, (mesh, report) in enumerate(zip(meshes, reports)):
        edges, triangles, quads = _metrics(mesh); topology = report["topology"]
        for name, value in zip(("vertices", "edges", "quads", "triangles", "boundary_edges"), (len(mesh.vertices), topology.edge_count, len(mesh.quads), len(mesh.triangles), topology.boundary_edge_count)):
            _put(structural, thresholds, _gate(f"structural.L{level}.count.{name}", 1, value, value, "eq", value, value, "count"))
        for name in "connected orientable outward_wound boundary_components_match_ports".split():
            _put(structural, thresholds, _bool(f"structural.L{level}.surface_boolean.{name}"))
        for name, count in (("coordinates", 3 * len(mesh.vertices)), ("quad_normals", 3 * len(mesh.quads)), ("triangle_areas", len(triangles)), ("quad_areas", len(quads))):
            _put(structural, thresholds, _bool(f"structural.L{level}.finite.{name}")); structural[-1]["sample_count"] = count
        for name, samples in (("edge_length", edges), ("triangle_area", triangles), ("quad_area", quads)):
            _put(structural, thresholds, _gate(f"structural.L{level}.floor.{name}", len(samples), min(samples), max(samples), "ge", mesh_api.STRUCTURAL_FLOORS[level][name], None, "m" if name == "edge_length" else "m2"))
        ownership = _ownership_counts(evaluation, formulas, summary, components, level)
        invalid = {"duplicate_vertex_ids": len(mesh.control_ids) - len(set(mesh.control_ids)), "duplicate_face_ids": len(mesh.face_ids) - len(set(mesh.face_ids)), "degenerate_faces": sum(triangles[2 * index] <= 0.0 or triangles[2 * index + 1] <= 0.0 for index in range(len(mesh.quads))), "zero_length_edges": sum(value == 0.0 for value in edges), "non_manifold_edges": topology.non_manifold_edges, "orientation_conflicts": topology.orientation_conflicts, "unowned_elements": ownership["unowned_elements"], "overowned_elements": ownership["overowned_elements"], "accidental_boundary_components": abs(topology.boundary_components - len(surface.PORTS))}
        for name in invalid_names:
            _put(structural, thresholds, _gate(f"structural.L{level}.invalid_count.{name}", 1, invalid[name], invalid[name], "eq", 0, 0, "count"))
        for name in ("charts", "interior_transitions", "maximum_samples_per_vertex"):
            value = chart_counts[level][name]; _put(structural, thresholds, _gate(f"structural.L{level}.chart.{name}", 1, value, value, "eq", value, value, "count"))
    rows = [row for row in summary["vertex_records"] if row["level"] == 2]
    for name, field, limit in (("base_control_contributors", "base_control_contributors", 20), ("dependency_union_keys", "geometry_dependency_union", 54), ("contributor_domains", "contributor_domains", 5)):
        value = max(len(row[field]) for row in rows); _put(structural, thresholds, _gate(f"structural.L2.lineage_cap.{name}", 1737, value, value, "le", None, limit, "count"))
    for name in "recurrence_exact incidence_complete boundary_neighbors_exact face_emission_exact lineage_complete chart_complete transition_complete".split():
        _put(structural, thresholds, _bool(f"structural.subdivision.{name}"))
    continuity, continuity_thresholds = [], []
    for level, (mesh, report) in enumerate(zip(meshes, reports)):
        inputs = _junction_inputs(evaluation, level, summary)
        for junction in surface.JUNCTIONS:
            metrics = mesh_api.junction_continuity_metrics(mesh.vertices, mesh.quads, mesh.face_owners, **inputs[junction]); count = len(metrics["traces"][0]); residuals, folds = metrics["coordinate_residual_samples"], _fold_samples(mesh, junction)
            _need(len(residuals) == 3 * count and len(folds) == count, "continuity cardinality drift")
            for name, samples, relation, lower, upper, unit in (("tag_identity", (1,), "eq", 1, 1, "boolean"), ("opposite_trace_direction", (1,), "eq", 1, 1, "boolean"), ("coordinate_residual", residuals, "le", None, mesh_api.T, "m"), ("fold_angle", folds, "lt", None, (90.0, 60.0, 30.0)[level], "degree")):
                _sample(continuity, continuity_thresholds, f"continuity.{junction}.L{level}.{name}", samples, relation, lower, upper, unit)
        for port, metric in report["port_metrics"].items():
            count = len(dict(mesh.boundary_loops)[port]); _need(len(metric["planarity_samples"]) == count and len(metric["co_normal_samples"]) == count, "port sample cardinality drift")
            for name, samples, relation, lower, upper, unit in (("orientation", (metric["orientation"],), "ge", .99, None, "dimensionless"), ("planarity", metric["planarity_samples"], "le", None, mesh_api.T, "m"), ("area_ratio", (metric["area_ratio"],), "ge", .0001, None, "dimensionless"), ("co_normal", metric["co_normal_samples"], "ge", .80, None, "dimensionless")):
                _sample(continuity, continuity_thresholds, f"continuity.{port}.L{level}.{name}", samples, relation, lower, upper, unit)
    thresholds.extend(continuity_thresholds); thresholds.extend(anatomy.anatomy_threshold_records()); intersection, intersection_thresholds = [], []
    for level, (mesh, report) in enumerate(zip(meshes, (row["intersection_report"] for row in reports))):
        for name, value, relation, lower, upper, unit in (("triangle_count", report["triangle_count"], "eq", len(mesh.triangles), len(mesh.triangles), "count"), ("broad_phase_candidate_count", report["broad_phase_candidate_count"], "le", None, mesh_api.MAX_CANDIDATES, "count"), ("intersection_hit_count", report["intersection_hit_count"], "eq", 0, 0, "count"), ("pair_policy_complete", int(report["pair_policy_complete"]), "eq", 1, 1, "boolean")):
            _put(intersection, intersection_thresholds, _gate(f"intersection.L{level}.{name}", 1, value, value, relation, lower, upper, unit))
    thresholds.extend(intersection_thresholds); thresholds.append({"threshold_id": "gate.boolean-pass", "relation": "eq", "lower": 1, "upper": 1, "unit": "dimensionless"})
    _need((len(structural), len(continuity), len(anatomy_rows), len(intersection), len(thresholds)) == (122, 144, 78, 12, 357), "gate inventory is not exact")
    all_gates = (*structural, *continuity, *anatomy_rows, *intersection); _need(all(row["outcome"] == "pass" for row in all_gates), "a geometry gate failed")
    return {"evaluation": evaluation, "reports": reports, "structural": structural, "continuity": continuity, "anatomy": anatomy_rows, "intersection": intersection, "thresholds": thresholds}


def _support_hash(indices) -> str:
    values = tuple(indices); _need(values == tuple(sorted(set(values))) and all(type(index) is int and 0 <= index < 1737 for index in values), "invalid support indices")
    return artifacts.sha256_bytes(b"CKSUPPORTv1\0\2" + struct.pack("<I", len(values)) + b"".join(struct.pack("<I", index) for index in values))


def run_causality(components: surface.GeometryComponents, geometry: dict[str, Any]):
    """Execute the exact 33 copied-component perturbations."""
    _need(type(components) is surface.GeometryComponents and tuple(PARAMETER_IDS) == tuple(neutral_projection.MUST_AFFECT_PARAMETER_IDS), "causality accepts only the frozen carrier/selectors")
    baseline = geometry["evaluation"].levels[1]; baseline_ply = render.ply_bytes(baseline)
    baseline_shape = (baseline.control_ids, baseline.quads, baseline.formula_ids, baseline.dependencies, baseline.boundary_loops, baseline.face_ids, baseline.face_owners, baseline.vertex_records, baseline.source_stencils)
    records, payloads, delta = [], {}, float.fromhex("0x1.47ae147ae147bp-7")
    _need(delta == neutral_projection.PERTURBATION_DELTA_M, "perturbation delta drift")
    for parameter in PARAMETER_IDS:
        component = neutral_projection.MUST_AFFECT_COMPONENTS.get(parameter); _need(component in surface.GEOMETRY_COMPONENT_IDS, f"unknown selector: {parameter}")
        index = surface.GEOMETRY_COMPONENT_IDS.index(component); copied = list(components.values); original = copied[index]; copied[index] = original + delta
        changed = tuple(copied); restored = list(changed); restored[index] = original
        _need(tuple(restored) == components.values and sum(left != right for left, right in zip(changed, components.values)) == 1, "perturbation changed other components")
        perturbed = surface.GeometryComponents(changed); surface.validate_geometry_components(perturbed)
        derivative = surface.propagate_derivative(geometry["evaluation"].cage, surface.analytic_control_derivatives(components, component), level=2)
        predicted = tuple(index for index, point in enumerate(derivative) if any(value != 0.0 for value in point)); observed = surface.evaluate(perturbed, levels=2).levels[1]
        observed_shape = (observed.control_ids, observed.quads, observed.formula_ids, observed.dependencies, observed.boundary_loops, observed.face_ids, observed.face_owners, observed.vertex_records, observed.source_stencils)
        _need(observed_shape == baseline_shape, f"topology/lineage changed for {parameter}")
        movement = tuple(math.sqrt(sum((observed.vertices[vertex][axis] - baseline.vertices[vertex][axis]) ** 2 for axis in range(3))) for vertex in range(1737)); actual = tuple(vertex for vertex, value in enumerate(movement) if value > mesh_api.T); maximum = max(movement)
        _need(predicted and actual == predicted and maximum >= float.fromhex("0x1.d14e3bcd35a85p-11") and all(movement[vertex] <= mesh_api.T for vertex in range(1737) if vertex not in predicted), f"support/movement gate failed for {parameter}")
        _need(parameter not in ("left.thigh_start_x", "right.thigh_start_x") or len(predicted) == 436, "thigh-x support cardinality drift")
        role = f"perturb-{parameter.replace('.', '-')}.ply"; payload = render.ply_bytes(observed); _need(payload != baseline_ply and len(payload) <= 2 * 1024 * 1024, "perturbation PLY gate failed"); payloads[role] = payload
        records.append({"parameter_id": parameter, "prepared_component": component, "delta_m": delta, "support_level": 2, "predicted_support_count": len(predicted), "observed_support_count": len(actual), "predicted_support_sha256": _support_hash(predicted), "observed_support_sha256": _support_hash(actual), "maximum_movement_m": maximum, "artifact": None})
    _need(len(records) == 33 and set(payloads) == set(PERTURBATION_ROLES), "causality inventory is not exact")
    return records, payloads


def _write(path: Path, data: bytes) -> dict[str, Any]:
    artifacts.write_bytes_no_replace(path, data)
    return artifacts.regular_file_record(path, path.name, max_bytes=16 * 1024 * 1024)


def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _same_admission(left, right) -> bool:
    return artifacts.canonical_json_bytes(left) == artifacts.canonical_json_bytes(right)


def build_profile_seed(profile_id: str, output_path: str | os.PathLike[str]) -> Path:
    """Build and atomically seal one exact 42-file profile/seed bundle."""
    seed = os.environ.get("PYTHONHASHSEED"); _need(seed in ("17", "29"), "profile build requires literal PYTHONHASHSEED=17 or 29")
    output = Path(output_path); _need(output.is_absolute() and os.path.normpath(str(output)) == str(output) and not os.path.lexists(output) and output.parent.is_dir(), "output must be canonical, absolute, absent, and parented")
    started, clock, stage, timings = _now(), time.perf_counter(), None, []
    try:
        mark = time.perf_counter(); admission = static_admission(); timings.append({"phase": "identity", "seconds": float(time.perf_counter() - mark)})
        mark = time.perf_counter(); source, source_raw = profiles.load_json_with_bytes(ROOT / SOURCE_ROLE, "authored source"); table, table_raw = profiles.load_json_with_bytes(ROOT / PROFILE_ROLE, "profile table")
        _need(artifacts.sha256_bytes(source_raw) == EXPECTED_SOURCE_SHA256 and artifacts.sha256_bytes(table_raw) == EXPECTED_PROFILE_SHA256, "source read drift")
        projection = project_profile(profile_id, source, table); components = projection["carrier"]; timings.append({"phase": "selection-projection", "seconds": float(time.perf_counter() - mark)})
        mark = time.perf_counter(); surface.validate_catalogs(); timings.append({"phase": "catalogs", "seconds": float(time.perf_counter() - mark)})
        mark = time.perf_counter(); geometry = run_geometry(components); timings.append({"phase": "geometry-gates", "seconds": float(time.perf_counter() - mark)})
        mark = time.perf_counter(); causality, perturbations = run_causality(components, geometry); timings.append({"phase": "causality", "seconds": float(time.perf_counter() - mark)})
        mark = time.perf_counter(); stage = Path(tempfile.mkdtemp(prefix=f".{output.name}.stage-", dir=output.parent)); meshes = (geometry["evaluation"].cage, *geometry["evaluation"].levels); payload_records, level_records = [], []
        for role, mesh, counts in zip(SURFACE_ROLES, meshes, LEVEL_COUNTS):
            ply = _write(stage / role, render.ply_bytes(mesh)); payload_records.append(ply); coordinate_raw = artifacts.coordinate_hash_bytes(mesh.vertices); triangle_raw = artifacts.triangle_index_hash_bytes(mesh.triangles)
            level_records.append({"level": mesh.level, "counts": {"level": mesh.level, "vertices": counts[0], "edges": counts[1], "quads": counts[2], "triangles": counts[3], "boundary_edges": counts[4]}, "coordinate_bytes": len(coordinate_raw), "coordinate_sha256": artifacts.sha256_bytes(coordinate_raw), "triangle_index_bytes": len(triangle_raw), "triangle_index_sha256": artifacts.sha256_bytes(triangle_raw), "ply": ply})
        for index, role in enumerate(PERTURBATION_ROLES):
            record = _write(stage / role, perturbations[role]); payload_records.append(record); causality[index]["artifact"] = record
        direct, lineage, visibility = render.render_pair_bytes(meshes[-1]); direct_record, lineage_record = _write(stage / "direct.png", direct), _write(stage / "lineage.png", lineage); payload_records.extend((direct_record, lineage_record))
        payload_records = sorted(payload_records, key=lambda row: row["role_path"].encode()); _need(tuple(row["role_path"] for row in payload_records) == tuple(_ordered(PAYLOAD_ROLES)), "payload inventory drift")
        config, visible = render.render_config_record(), render.visibility_record(visibility); render.validate_render_config(config)
        evidence = {"schema": "owned-root-assembly-successor-profile-seed-evidence.v1", "outcome": "success", "activation_contract": admission["activation_contract"], "design_contract": admission["design_contract"], "source": admission["source"], "profile_table": admission["profile_table"], "existing_dependencies": list(admission["existing_dependencies"]), "additive_implementation_files": list(admission["additive_implementation_files"]), "runtime": admission["runtime"], "runtime_fingerprint_sha256": RUNTIME_SHA256, "profile_id": profile_id, "profile_index": projection["profile_index"], "selection": projection["selection"], "projected_values": projection["projected_values"], "projected_carrier": projection["projected_carrier"], "projection_bindings": projection["projection_bindings"], "levels": level_records, "thresholds": sorted(geometry["thresholds"], key=lambda row: row["threshold_id"].encode()), "gates": {name: sorted(geometry[name], key=lambda row: row["gate_id"].encode()) for name in ("structural", "continuity", "anatomy", "intersection")}, "causality": sorted(causality, key=lambda row: row["parameter_id"].encode()), "renders": {"renderer_id": "owned-root-raster-pillow-11.1.0.v1", "render_config": config, "render_config_sha256": artifacts.sha256_bytes(artifacts.canonical_json_bytes(config)), "visibility": visible, "visibility_sha256": artifacts.sha256_bytes(artifacts.canonical_json_bytes(visible)), "direct": direct_record, "lineage": lineage_record, "same_surface_positions_sha256": level_records[2]["coordinate_sha256"], "same_surface_triangles_sha256": level_records[2]["triangle_index_sha256"]}, "payloads": payload_records, "invariants": {name: True for name in ("topology_equal_to_neutral", "formulas_equal_to_neutral", "tunables_equal_to_neutral", "thresholds_equal_to_neutral", "gate_inventory_equal_to_neutral", "subdivision_equal_to_neutral", "ownership_equal_to_neutral", "causality_rules_equal_to_neutral", "renderer_equal_to_neutral")}}
        _need(visible["triangle_index_sha256"] == level_records[2]["triangle_index_sha256"], "render does not bind the level-2 triangles")
        evidence_raw = artifacts.canonical_json_bytes(evidence); _need(len(evidence_raw) <= 16 * 1024 * 1024, "profile evidence exceeds 16 MiB"); _write(stage / "profile-seed-evidence.json", evidence_raw); _write(stage / "profile-seed-evidence.sha256", f"{artifacts.sha256_bytes(evidence_raw)}  profile-seed-evidence.json\n".encode("ascii")); timings.append({"phase": "serialization", "seconds": float(time.perf_counter() - mark)})
        _need(_same_admission(admission, static_admission()), "fixed identity changed during profile build")
        timings.append({"phase": "total-before-seal", "seconds": float(time.perf_counter() - clock)}); _need(tuple(row["phase"] for row in timings) == PHASES, "timing phase order drift")
        report = {"schema": "owned-root-assembly-successor-profile-seed-run-report.v1", "outcome": "success", "profile_id": profile_id, "profile_index": projection["profile_index"], "seed": int(seed), "literal_invocation": {"environment": [f"PYTHONHASHSEED={seed}"], "argv": [RUNNER_ROLE, "--profile", profile_id, "--output", str(output)]}, "output_path": str(output), "staging_path": str(stage), "python_executable_path": os.path.abspath(sys.executable), "started_utc": started, "finished_utc": _now(), "timings": timings, "runtime_fingerprint_sha256": RUNTIME_SHA256, "manifest_ref": {"role_path": "profile-seed-evidence.json", "bytes": len(evidence_raw), "sha256": artifacts.sha256_bytes(evidence_raw), "schema": evidence["schema"]}, "gates": [{"gate_id": gate, "outcome": "pass", "sample_count": 1, "observed_min": 1, "observed_max": 1, "threshold_id": "gate.boolean-pass"} for gate in RUN_GATES]}
        report_raw = artifacts.canonical_json_bytes(report); _need(len(report_raw) <= 2 * 1024 * 1024, "run report exceeds 2 MiB"); _write(stage / "run-report.json", report_raw); _write(stage / "run-report.sha256", f"{artifacts.sha256_bytes(report_raw)}  run-report.json\n".encode("ascii"))
        inventory = artifacts.closed_inventory(stage, BUNDLE_ROLES, max_file_bytes=16 * 1024 * 1024); _need(len(inventory) == 42 and sum(row["bytes"] for row in inventory) <= 512 * 1024 * 1024, "bundle closure/resource cap failed")
        for row in inventory:
            limit = 16 * 1024 * 1024 if row["role_path"] == "profile-seed-evidence.json" else 256 if row["role_path"].endswith(".sha256") else 2 * 1024 * 1024
            _need(row["bytes"] <= limit, f"bundle role exceeds cap: {row['role_path']}")
        artifacts.publish_no_replace(stage, output, inventory, max_file_bytes=16 * 1024 * 1024); stage = None
        return output
    except Exception:
        if stage is not None and stage.exists() and not stage.is_symlink():
            shutil.rmtree(stage)
        raise


def validate_profile_seed_bundle(root_path: str | os.PathLike[str], profile_id: str, seed: int) -> dict[str, Any]:
    """Re-admit one sealed 42-file bundle without rebuilding geometry."""
    _need(profile_id in PROFILE_IDS and seed in PROFILE_SEEDS, "invalid profile/seed admission")
    root = Path(root_path); records = artifacts.closed_inventory(root, BUNDLE_ROLES, max_file_bytes=16 * 1024 * 1024)
    _need(len(records) == 42, "bundle does not contain exactly 42 files"); by_role = {row["role_path"]: row for row in records}
    def read_json(role, cap):
        raw = artifacts.read_regular_file(root / role, max_bytes=cap); value = artifacts.decode_canonical_json(raw)
        _need(type(value) is dict and artifacts.canonical_json_bytes(value) == raw, f"{role} is not canonical closed JSON")
        return value, raw
    evidence, evidence_raw = read_json("profile-seed-evidence.json", 16 * 1024 * 1024); report, report_raw = read_json("run-report.json", 2 * 1024 * 1024)
    evidence_keys = {"schema", "outcome", "activation_contract", "design_contract", "source", "profile_table", "existing_dependencies", "additive_implementation_files", "runtime", "runtime_fingerprint_sha256", "profile_id", "profile_index", "selection", "projected_values", "projected_carrier", "projection_bindings", "levels", "thresholds", "gates", "causality", "renders", "payloads", "invariants"}
    _need(set(evidence) == evidence_keys and evidence["schema"] == "owned-root-assembly-successor-profile-seed-evidence.v1" and evidence["outcome"] == "success", "profile evidence schema mismatch")
    index = PROFILE_IDS.index(profile_id); _need((evidence["profile_id"], evidence["profile_index"]) == (profile_id, index), "profile evidence selection mismatch")
    identity = static_admission()
    for field in ("activation_contract", "design_contract", "source", "profile_table", "runtime_fingerprint_sha256"):
        _need(evidence[field] == identity[field], f"profile evidence {field} mismatch")
    _need(evidence["existing_dependencies"] == list(identity["existing_dependencies"]) and evidence["additive_implementation_files"] == list(identity["additive_implementation_files"]) and evidence["runtime"] == identity["runtime"], "profile evidence implementation/runtime mismatch")
    components = tuple(surface.GEOMETRY_COMPONENT_IDS); values, bindings = evidence["projected_values"], evidence["projection_bindings"]
    _need(type(values) is list and type(bindings) is list and len(values) == len(bindings) == 92 and tuple(row.get("prepared_component") for row in values) == components and tuple(row.get("prepared_component") for row in bindings) == components, "projected value/binding closure mismatch")
    carrier_raw = artifacts.canonical_json_bytes([row["value"] for row in values]); _need(evidence["projected_carrier"] == {"bytes": len(carrier_raw), "sha256": artifacts.sha256_bytes(carrier_raw)}, "projected carrier hash mismatch")
    selected = project_profile(profile_id); _need(evidence["selection"] == selected["selection"], "selection hash mismatch")
    _need(type(evidence["levels"]) is list and [row.get("level") for row in evidence["levels"]] == [0, 1, 2], "level evidence mismatch")
    for level, row in enumerate(evidence["levels"]):
        _need(row.get("counts") == {"level": level, "vertices": LEVEL_COUNTS[level][0], "edges": LEVEL_COUNTS[level][1], "quads": LEVEL_COUNTS[level][2], "triangles": LEVEL_COUNTS[level][3], "boundary_edges": LEVEL_COUNTS[level][4]} and row.get("ply") == by_role[SURFACE_ROLES[level]], "level record mismatch")
    _need(type(evidence["thresholds"]) is list and len(evidence["thresholds"]) == 357 and evidence["thresholds"] == sorted(evidence["thresholds"], key=lambda row: row["threshold_id"].encode()), "threshold closure mismatch")
    _need(set(evidence["gates"]) == {"structural", "continuity", "anatomy", "intersection"} and tuple(len(evidence["gates"][name]) for name in ("structural", "continuity", "anatomy", "intersection")) == (122, 144, 78, 12), "gate closure mismatch")
    _need(all(row["outcome"] == "pass" for rows in evidence["gates"].values() for row in rows), "sealed evidence contains a failed gate")
    _need(type(evidence["causality"]) is list and len(evidence["causality"]) == 33 and [row["parameter_id"] for row in evidence["causality"]] == _ordered(PARAMETER_IDS), "causality closure mismatch")
    for row in evidence["causality"]:
        _need(row["artifact"] == by_role[f"perturb-{row['parameter_id'].replace('.', '-')}.ply"], "causality artifact mismatch")
    expected_payloads = [by_role[role] for role in _ordered(PAYLOAD_ROLES)]; _need(evidence["payloads"] == expected_payloads, "payload record closure mismatch")
    renders = evidence["renders"]; config, visible = renders["render_config"], renders["visibility"]; render.validate_render_config(config)
    _need(renders["render_config_sha256"] == artifacts.sha256_bytes(artifacts.canonical_json_bytes(config)) and renders["visibility_sha256"] == artifacts.sha256_bytes(artifacts.canonical_json_bytes(visible)) and renders["direct"] == by_role["direct.png"] and renders["lineage"] == by_role["lineage.png"], "render evidence mismatch")
    _need(artifacts.read_regular_file(root / "profile-seed-evidence.sha256", max_bytes=256) == f"{artifacts.sha256_bytes(evidence_raw)}  profile-seed-evidence.json\n".encode("ascii"), "evidence sidecar mismatch")
    report_keys = {"schema", "outcome", "profile_id", "profile_index", "seed", "literal_invocation", "output_path", "staging_path", "python_executable_path", "started_utc", "finished_utc", "timings", "runtime_fingerprint_sha256", "manifest_ref", "gates"}
    _need(set(report) == report_keys and report["schema"] == "owned-root-assembly-successor-profile-seed-run-report.v1" and report["outcome"] == "success" and (report["profile_id"], report["profile_index"], report["seed"]) == (profile_id, index, seed), "run report schema/selection mismatch")
    _need([row["phase"] for row in report["timings"]] == list(PHASES) and [row["gate_id"] for row in report["gates"]] == list(RUN_GATES) and all(row["outcome"] == "pass" for row in report["gates"]), "run report timing/gate mismatch")
    expected_ref = {"role_path": "profile-seed-evidence.json", "bytes": len(evidence_raw), "sha256": artifacts.sha256_bytes(evidence_raw), "schema": evidence["schema"]}; _need(report["manifest_ref"] == expected_ref, "run report evidence reference mismatch")
    _need(artifacts.read_regular_file(root / "run-report.sha256", max_bytes=256) == f"{artifacts.sha256_bytes(report_raw)}  run-report.json\n".encode("ascii"), "run report sidecar mismatch")
    return evidence


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    try:
        if argv[:1] == ["--internal-managed-tests"] and len(argv) == 3 and argv[1] == "--receipt":
            run_managed_tests(argv[2]); return 0
        if argv[:1] == ["--profile"] and len(argv) == 4 and argv[2] == "--output" and argv[1] in PROFILE_IDS:
            build_profile_seed(argv[1], argv[3]); return 0
        raise ExactFiveError("private runner accepts only --internal-managed-tests --receipt ABS or --profile EXACT_ID --output ABS")
    except Exception as exc:
        print(f"exact_five_runner: error: {exc}", file=sys.stderr); return 1


if __name__ == "__main__":
    raise SystemExit(main())
