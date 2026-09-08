"""Small prepare/run/verify harness for the connected-leg staging experiment.

The harness owns evidence plumbing only.  Construction, binding, checking and
rendering remain experiment-local collaborators and may be absent while their
interfaces are being prepared.  In particular, importing this module never
executes a candidate body.
"""

from __future__ import annotations

import argparse
import ast
import copy
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import platform
import sys
from types import ModuleType
from typing import Any, Iterable, Mapping

sys.dont_write_bytecode = True
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

HERE = Path(__file__).resolve().parent
SNAPSHOT_SOURCE = Path("source/experiments/connected-leg-assembly")
CAPTURE_DEPENDENCIES = {
    "pelvis-source-calibration/section_diagnostic.py": (
        HERE.parent / "pelvis-source-calibration/section_diagnostic.py"
    ),
}
FROZEN_DEPENDENCY_ROOT = Path(
    "/home/ben/.cache/creature-kernel/pelvis-thigh-transition/attempt-2-snapshot"
)
FROZEN_HIP_CAPTURE = Path(
    "/home/ben/.cache/creature-kernel/pelvis-hip-articulation-harmonic-lbs-001-snapshot"
    "/source/experiments/pelvis-hip-articulation/capture.py"
)
FROZEN_RENDERER_RELATIVE = Path("source/experiments/pelvis-thigh-transition/render.py")
FROZEN_COLLISION_CORE = Path(
    "/home/ben/.cache/creature-kernel/pelvis-thigh-transition/attempt-2-snapshot"
    "/source/experiments/owned-root-assembly-successor/mesh_correctness.py"
)

# This is a closed local allowlist, not a recursive copy of the repository.
# Missing entries are allowed during the staged interface phase; prepare will
# capture the ones that exist and run reports absent execution collaborators.
CAPTURE_FILES = (
    "runner.py", "construction.py", "binding.py", "checks.py", "render.py",
    "perturbations.py",
    "root_source.py", "hip_source.py", "foot_construction.py", "foot_trial.py",
    "arm_construction.py", "head_construction.py", "body_assembly.py",
    "pelvis_foundation.py", "pelvis_foundation_preflight.py",
    "abdomen_foundation.py", "abdomen_foundation_provider.py",
    "abdomen_foundation_preflight.py", "abdomen_foundation_body_evidence.py",
    "tail_construction.py",
    "foot_form_construction.py", "foot_attachment_construction.py",
    "foot_junction_construction.py",
    "torso_refinement.py",
    "thorax_foundation.py",
    "thorax_foundation_diagnostic.py",
    "thorax_foundation_body_evidence.py",
    "thorax_foundation_checks.py",
    "chest_envelope_evidence.py",
    "chest_envelope_diagnostics.py",
    "collision_broadphase.py",
    "foot-inputs.json", "foot-form-inputs.json", "tail-inputs.json",
    "torso-refinement-inputs.json", "torso-silhouette-inputs.json",
    "torso-silhouette-correction-inputs.json",
    "torso-chest-depth-ablation-inputs.json",
    "torso-chest-envelope-inputs.json",
    "thorax-foundation-baseline-inputs.json",
    "thorax-foundation-width-inputs.json",
    "thorax-foundation-fullness-inputs.json",
    "abdomen-foundation-baseline-inputs.json",
    "abdomen-foundation-bow-inputs.json",
    "abdomen-foundation-fullness-inputs.json",
    "head-refinement-inputs.json", "arm-refinement-inputs.json",
    "foot-attachment-inputs.json", "foot-junction-policy.json",
    "body-config.json", "body-refinement-internal-config.json",
    "body-torso-correction-config.json",
    "body-junction-integration-config.json",
    "body-chest-depth-ablation-config.json",
    "body-chest-envelope-config.json",
    "body-silhouette-refinement-config.json", "tail-stage.md",
    "body-thorax-foundation-baseline-config.json",
    "body-thorax-foundation-width-config.json",
    "body-thorax-foundation-fullness-config.json",
    "body-pelvis-foundation-baseline-config.json",
    "body-pelvis-foundation-iliac-config.json",
    "body-pelvis-foundation-gluteal-config.json",
    "body-abdomen-foundation-baseline-config.json",
    "body-abdomen-foundation-bow-config.json",
    "body-abdomen-foundation-fullness-config.json",
    "abdomen-foundation-proposal.md",
    "pelvis-foundation-recipe.md", "pelvis-foundation-proposal.md",
    "pelvis-foundation-baseline-inputs.json",
    "pelvis-foundation-iliac-inputs.json",
    "pelvis-foundation-gluteal-inputs.json",
    "captured_tests.py",
    "arm-inputs.json", "head-inputs.json",
    "protocol.json", "inputs.json", "README.md", "example-brief.md",
    "tests/test_runner.py", "tests/test_construction.py", "tests/test_binding.py",
    "tests/test_checks.py", "tests/test_perturbations.py", "tests/test_integration.py",
    "tests/test_root_source.py", "tests/test_hip_source.py",
    "tests/test_foot_construction.py",
    "tests/test_arm_construction.py", "tests/test_arm_refinement.py",
    "tests/test_head_construction.py", "tests/test_head_refinement.py",
    "tests/test_body_assembly.py",
    "tests/test_foot_form_construction.py", "tests/test_foot_attachment_construction.py",
    "tests/test_foot_junction_construction.py",
    "tests/test_torso_refinement.py",
    "tests/test_thorax_foundation_diagnostic.py",
    "tests/test_thorax_foundation_body_evidence.py",
    "tests/test_thorax_foundation_checks.py",
    "tests/test_thorax_foundation.py",
    "tests/test_chest_envelope_evidence.py",
    "tests/test_tail_construction.py",
    "tests/test_collision_broadphase.py",
    "tests/test_pelvis_foundation.py",
    "tests/test_pelvis_foundation_provider.py",
    "tests/test_pelvis_foundation_selection.py",
    "foot-junction-stage.md",
)
MAPPED_INPUT_FIELDS = ("root_mesh", "prior_rest_mesh", "prior_hip_binding")
OPTIONAL_MAPPED_INPUT_FIELDS = ("original_case", "original_ref")
CANONICAL_LEG_INPUT_FIELDS = (
    "left.J", "left.T", "left.K", "left.A", "left.radii",
    "left.mid_thigh_factor", "left.support_fraction", "left.role_metadata",
    "right.J", "right.T", "right.K", "right.A", "right.radii",
    "right.mid_thigh_factor", "right.support_fraction", "right.role_metadata",
)
REQUIRED_CHECK_SIGNATURES = {
    "checks.check_mesh": "check_mesh(mesh, protocol)",
    "checks.check_binding": "check_binding(base, rest, binding, root, prior_binding, leg_inputs, protocol)",
    "checks.check_pose": "check_pose(rest, posed, binding, angles, protocol, leg_inputs)",
    "checks.compare_root": "compare_root(prior_L0, expanded_L0, prior_L2, expanded_L2)",
}
PERTURBATION_SIGNATURE = (
    "run_case(root, prior_rest, prior_binding, leg_inputs, baseline_L0, baseline_L2, "
    "baseline_binding, protocol, construction_module, binding_module)"
)

# Internal body evidence only.  This is separate from the frozen leg protocol
# and reuses its checker thresholds; it is not the named whole-character
# checkpoint.  The explicit fields must survive transport into binding.pose.
BODY_PROVISIONAL_POSES = (
    {
        "id": "body_neutral",
        "left": {"hip": 0, "knee": 0, "ankle": 0,
                 "shoulder_raise": 0, "shoulder_forward": 0, "elbow": 0},
        "right": {"hip": 0, "knee": 0, "ankle": 0,
                  "shoulder_raise": 0, "shoulder_forward": 0, "elbow": 0},
        "head": {"yaw": 0, "nod": 0},
    },
    {
        "id": "body_combined_modest",
        "left": {"hip": 10, "knee": 10, "ankle": 0,
                 "shoulder_raise": 8, "shoulder_forward": 6, "elbow": 10},
        "right": {"hip": -8, "knee": 8, "ankle": 0,
                  "shoulder_raise": -7, "shoulder_forward": 5, "elbow": 9},
        "head": {"yaw": 6, "nod": 4},
    },
)


class RunnerError(ValueError):
    """Raised when evidence cannot be admitted by the local runner contract."""


def _fail(message: str) -> None:
    raise RunnerError(message)


def _mapping(value: Any, where: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        _fail(f"{where} must be an object")
    return value


def _canonical(value: str | os.PathLike[str], label: str) -> Path:
    path = Path(value)
    if not path.is_absolute() or os.path.normpath(str(path)) != str(path):
        _fail(f"{label} must be an absolute canonical path")
    return path


def _regular(path: Path, label: str) -> None:
    try:
        info = path.lstat()
    except OSError as exc:
        raise RunnerError(f"{label} is unavailable: {path}") from exc
    if path.is_symlink() or not path.is_file() or not info:
        _fail(f"{label} must be a regular non-symlink file: {path}")


def _directory(path: Path, label: str) -> None:
    if path.is_symlink() or not path.is_dir():
        _fail(f"{label} must be a regular directory: {path}")


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256(path: Path) -> str:
    _regular(path, "hashed file")
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _identity(path: Path) -> dict[str, Any]:
    return {"bytes": path.stat().st_size, "sha256": _sha256(path)}


def _json_bytes(value: Any) -> bytes:
    try:
        return (json.dumps(value, sort_keys=True, indent=2, ensure_ascii=True,
                           allow_nan=False) + "\n").encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise RunnerError(f"value is not finite JSON: {exc}") from exc


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(_json_bytes(value))


def _read_json(path: Path) -> tuple[Any, bytes]:
    _regular(path, "JSON file")
    raw = path.read_bytes()
    try:
        value = json.loads(raw.decode("utf-8"),
                          parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)))
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise RunnerError(f"invalid finite UTF-8 JSON: {path}") from exc
    return value, raw


def _load_module(name: str, path: Path) -> ModuleType:
    """Load a module from an admitted path, registering it before execution."""
    _regular(path, "dynamic module")
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        _fail(f"unable to load dynamic module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        if sys.modules.get(name) is module:
            sys.modules.pop(name, None)
        raise
    if Path(str(module.__file__)).resolve() != path.resolve():
        _fail(f"module resolved away from its frozen path: {name}")
    return module


def _frozen_dependency_identity() -> dict[str, Any]:
    """Obtain the existing transition identity through the pinned hip helper."""
    helper_before = _identity(FROZEN_HIP_CAPTURE)
    helper = _load_module("ck_connected_leg_pinned_hip_capture", FROZEN_HIP_CAPTURE)
    getter = getattr(helper, "_load_frozen_dependency_identity", None)
    if not callable(getter):
        _fail("pinned hip capture has no frozen dependency identity helper")
    identity = getter()
    if not isinstance(identity, Mapping):
        _fail("frozen dependency identity is not an object")
    identity = dict(identity)
    helper_after = _identity(FROZEN_HIP_CAPTURE)
    if helper_before != helper_after:
        _fail("pinned hip capture helper changed while reading dependency identity")
    root = Path(str(identity.get("root", FROZEN_DEPENDENCY_ROOT)))
    renderer = root / FROZEN_RENDERER_RELATIVE
    _regular(renderer, "frozen renderer")
    collision_core = _collision_core_identity()
    return {
        "identity": identity,
        "hip_capture_helper": {"path": str(FROZEN_HIP_CAPTURE),
                                "before": helper_before, "after": helper_after},
        "renderer": {"path": str(renderer), **_identity(renderer)},
        "collision_core": collision_core,
    }


def _collision_core_identity() -> dict[str, Any]:
    """Record Sol's checks-declared external core from its frozen location."""
    before = _identity(FROZEN_COLLISION_CORE)
    after = _identity(FROZEN_COLLISION_CORE)
    if before != after:
        _fail("frozen collision core changed while reading its identity")
    return {"path": str(FROZEN_COLLISION_CORE), "before": before, "after": after}


def _dependency_identity() -> dict[str, Any]:
    """Public seam for tests and for before/after dependency verification."""
    return _frozen_dependency_identity()


def _adapter_dependency_identity(source_root: Path) -> dict[str, Any]:
    """Record source-adapter dependencies without constructing a candidate."""
    root_path = source_root / "root_source.py"
    hip_path = source_root / "hip_source.py"
    present = [path for path in (root_path, hip_path) if path.is_file()]
    if not present:
        return {}
    if len(present) != 2:
        _fail("root_source.py and hip_source.py must be captured together")
    try:
        root_adapter = _load_module("ck_connected_leg_capture_root_source", root_path)
        root_loader = getattr(root_adapter, "_load_frozen_construction", None)
        if not callable(root_loader):
            _fail("root_source.py has no frozen dependency loader")
        _unused_root_construction, root_provenance = root_loader()
        root_provenance = dict(root_provenance)
        root_provenance.pop("calibration_runner_module", None)

        hip_adapter = _load_module("ck_connected_leg_capture_hip_source", hip_path)
        hip_loader = getattr(hip_adapter, "_load_frozen_binding", None)
        if not callable(hip_loader):
            _fail("hip_source.py has no frozen dependency loader")
        _unused_hip_binding, hip_provenance = hip_loader()
        return _jsonable({"root_source": root_provenance,
                          "hip_source": hip_provenance})
    except RunnerError:
        raise
    except Exception as exc:
        _fail(f"source-adapter dependency identity is unavailable: {exc}")


def _source_path(name: str) -> Path:
    relative = Path(name)
    if relative.is_absolute() or ".." in relative.parts:
        _fail(f"source filename escapes the experiment: {name}")
    path = HERE / relative
    _regular(path, "experiment source")
    return path


def _selected_source_names(file_names: Iterable[str] | None) -> list[str]:
    names = list(CAPTURE_FILES if file_names is None else file_names)
    if not names or len(set(names)) != len(names):
        _fail("source file selection must be non-empty and unique")
    selected = [Path(name).as_posix() for name in names
                if (HERE / Path(name)).exists()]
    for name in selected:
        _source_path(name)
    if "runner.py" not in selected:
        _fail("capture must include runner.py")
    return selected


def _local_imports(path: Path) -> set[str]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (OSError, SyntaxError) as exc:
        raise RunnerError(f"cannot inspect imports in {path}") from exc
    result: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            result.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            result.add(node.module.split(".", 1)[0])
    return result


def _expand_imported_sources(names: list[str]) -> list[str]:
    allowed = set(CAPTURE_FILES)
    selected = set(names)
    changed = True
    while changed:
        changed = False
        for name in tuple(sorted(selected)):
            if not name.endswith(".py"):
                continue
            for module_name in _local_imports(HERE / name):
                candidate = f"{module_name}.py"
                if candidate in allowed and (HERE / candidate).is_file() and candidate not in selected:
                    selected.add(candidate)
                    changed = True
    return sorted(selected, key=lambda item: item.encode("utf-8"))


def _copy_file(source: Path, target: Path, label: str) -> dict[str, Any]:
    _regular(source, label)
    before = _identity(source)
    if target.exists() or target.is_symlink():
        _fail(f"capture target must be absent: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(source.read_bytes())
    after = _identity(source)
    copied = _identity(target)
    if before != after or before != copied:
        _fail(f"{label} changed while being captured: {source}")
    return {"origin_path": str(source), "snapshot_path": str(target), **before}


def _input_reference(value: Any) -> tuple[str, str] | None:
    if (isinstance(value, Mapping) and isinstance(value.get("path"), str)
            and isinstance(value.get("sha256"), str)):
        return str(value["path"]), str(value["sha256"])
    return None


def _input_refs(document: Mapping[str, Any], inputs_path: Path) -> list[dict[str, Any]]:
    cases = document.get("cases")
    if not isinstance(cases, list):
        _fail("inputs.json must contain a cases list")
    refs: list[dict[str, Any]] = []
    for index, case in enumerate(cases):
        if not isinstance(case, Mapping):
            _fail(f"case {index} is not an object")
        case_id = str(case.get("id", f"case-{index:02d}"))
        for field in (*MAPPED_INPUT_FIELDS, *OPTIONAL_MAPPED_INPUT_FIELDS):
            reference = _input_reference(case.get(field))
            if reference is None:
                if field in OPTIONAL_MAPPED_INPUT_FIELDS:
                    continue
                _fail(f"case {case_id} lacks mapped input field {field}")
            reference_path, declared_sha256 = reference
            origin = Path(reference_path)
            if not origin.is_absolute():
                origin = inputs_path.parent / origin
            _regular(origin, f"mapped input {case_id}.{field}")
            if _sha256(origin) != declared_sha256:
                _fail(f"mapped input {case_id}.{field} does not match its declared SHA-256")
            refs.append({"case_id": case_id, "field": field, "origin": origin,
                         "declared_sha256": declared_sha256})
    explicit = document.get("input_files", [])
    if explicit:
        if not isinstance(explicit, list):
            _fail("inputs.json input_files must be a list")
        for row in explicit:
            if (not isinstance(row, Mapping) or not isinstance(row.get("name"), str)
                    or not isinstance(row.get("path"), str)
                    or not isinstance(row.get("sha256"), str)):
                _fail("input_files rows require name, path, and sha256")
            origin = Path(str(row["path"]))
            if not origin.is_absolute():
                origin = inputs_path.parent / origin
            _regular(origin, f"explicit mapped input {row['name']}")
            if _sha256(origin) != row["sha256"]:
                _fail(f"explicit mapped input {row['name']} does not match its declared SHA-256")
            refs.append({"name": str(row["name"]), "field": "explicit", "origin": origin,
                         "declared_sha256": str(row["sha256"])})
    return refs


def _host_record(dependency: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "python": sys.version,
        "python_executable": sys.executable,
        "platform": platform.platform(),
        "machine": platform.machine(),
        "dependency_runtime": dependency.get("identity", {}).get("runtime", {}),
        "limitations": [
            "This records the host and library identity but does not claim hermetic OS, loader, or kernel isolation.",
            "The transition source/runtime are referenced and digest-verified; the 292 MB runtime is not cloned.",
        ],
    }


def prepare(snapshot: str | os.PathLike[str], file_names: Iterable[str] | None = None,
            rest_only: bool = False) -> dict[str, Any]:
    """Capture new source and concrete inputs into an absent snapshot."""
    target = _canonical(snapshot, "snapshot")
    if target.exists() or target.is_symlink():
        _fail(f"snapshot must be absent: {target}")
    if not target.parent.is_dir() or target.parent.is_symlink():
        _fail("snapshot parent must be an existing regular directory")
    selected = _selected_source_names(file_names)
    if rest_only and file_names is None:
        selected = [name for name in selected if name != "checks.py"]
    names = _expand_imported_sources(selected)
    dependency_names = (
        dict(CAPTURE_DEPENDENCIES)
        if "thorax_foundation_body_evidence.py" in names else {}
    )
    inputs_source = HERE / "inputs.json"
    if inputs_source.is_file():
        document, input_raw = _read_json(inputs_source)
        if not isinstance(document, Mapping):
            _fail("inputs.json must be an object")
        refs = _input_refs(document, inputs_source)
    else:
        document, input_raw, refs = None, None, []
    dependency_before = _dependency_identity()
    adapter_dependency_before = _adapter_dependency_identity(HERE)
    target.mkdir()
    source_rows: list[dict[str, Any]] = []
    try:
        for name in names:
            destination = target / SNAPSHOT_SOURCE / name
            row = _copy_file(HERE / name, destination, "source file")
            row["path"] = name
            source_rows.append(row)
        captured_dependency_rows: list[dict[str, Any]] = []
        for logical_name, origin in dependency_names.items():
            destination = target / "dependencies" / logical_name
            row = _copy_file(origin, destination, "captured source dependency")
            row.update({"path": logical_name,
                        "snapshot_path": destination.relative_to(target).as_posix(),
                        "origin_path": str(origin)})
            captured_dependency_rows.append(row)
        input_rows: list[dict[str, Any]] = []
        by_origin: dict[Path, Path] = {}
        for index, ref in enumerate(refs):
            origin = ref["origin"]
            destination = by_origin.get(origin)
            if destination is None:
                stem = origin.name or f"input-{index}"
                destination = Path("inputs") / f"{index:03d}-{stem}"
                by_origin[origin] = destination
                row = _copy_file(origin, target / destination, "concrete input")
                row.update({"path": destination.as_posix()})
                input_rows.append(row)
            ref_row = {key: value for key, value in ref.items() if key != "origin"}
            ref_row.update({"origin_path": str(origin), "snapshot_path": destination.as_posix()})
            input_rows.append(ref_row)
        if input_raw is not None:
            # The input document is a source artifact and is kept byte-for-byte;
            # path rewrites belong to this manifest's path map.
            _ = input_raw
        dependency_after = _dependency_identity()
        adapter_dependency_after = _adapter_dependency_identity(HERE)
        if dependency_before != dependency_after:
            _fail("frozen transition dependency changed while preparing capture")
        if adapter_dependency_before != adapter_dependency_after:
            _fail("source-adapter dependency changed while preparing capture")
        source_manifest = {
            "schema": "creature-kernel.connected-leg-assembly-source.v1",
            "files": [{key: row[key] for key in ("path", "bytes", "sha256")} for row in source_rows],
        }
        _write_json(target / "source" / "manifest.json", source_manifest)
        source_inventory = [{"path": row["path"], "bytes": row["bytes"],
                            "sha256": row["sha256"]} for row in source_rows]
        dependency_inventory = [{"path": row["path"], "bytes": row["bytes"],
                                "sha256": row["sha256"]}
                               for row in captured_dependency_rows]
        input_copies = [row for row in input_rows if "path" in row and "bytes" in row]
        input_inventory = [{"path": row["path"], "bytes": row["bytes"],
                            "sha256": row["sha256"]} for row in input_copies]
        manifest = {
            "schema": "creature-kernel.connected-leg-assembly-capture.v1",
            "status": "prepared",
            "body_execution": False,
            "captured_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "source": {"root": str(target / SNAPSHOT_SOURCE), "files": source_rows,
                       "before": source_inventory, "after": source_inventory},
            "captured_dependencies": {
                "files": captured_dependency_rows,
                "before": dependency_inventory,
                "after": dependency_inventory,
            },
            "code_manifest": {"sha256": _sha256_bytes(_json_bytes(source_manifest)), "files": source_rows},
            "input_manifest": {
                "source_path": str(inputs_source) if inputs_source.is_file() else None,
                "source_sha256": _sha256(inputs_source) if inputs_source.is_file() else None,
                "copies": input_copies,
                "before": input_inventory, "after": input_inventory,
                "path_map": [row for row in input_rows if "case_id" in row or "name" in row],
            },
            "dependency": {"root": str(dependency_before["identity"].get("root", FROZEN_DEPENDENCY_ROOT)),
                           "before": dependency_before, "after": dependency_after,
                           "reused_without_copy": True},
            "adapter_dependency": {
                "before": adapter_dependency_before,
                "after": adapter_dependency_after,
                "reused_without_copy": True,
            },
            "runtime": {"python": dependency_before["identity"].get("runtime", {}),
                        "executable": dependency_before["identity"].get("runtime", {}).get("executable")},
            "host": _host_record(dependency_before),
            "limitations": [
                "Preparation is stdlib-only and does not execute construction, binding, checks, or candidate bodies.",
                "Run must load the captured new source and the recorded frozen dependency locations, never the live worktree.",
                "The host OS and dynamic-loader environment are not hermetic.",
            ],
        }
        _write_json(target / "manifest.json", manifest)
        return manifest
    except Exception:
        # Retain a partial capture for diagnosis; callers can choose a new
        # absent path for a later repair/replay.
        raise


def _manifest(snapshot: Path) -> dict[str, Any]:
    value, _ = _read_json(snapshot / "manifest.json")
    if not isinstance(value, Mapping) or value.get("schema") != "creature-kernel.connected-leg-assembly-capture.v1":
        _fail("capture manifest schema is not admitted")
    return dict(value)


def verify(snapshot: str | os.PathLike[str]) -> dict[str, Any]:
    """Verify captured source/input bytes and the unchanged frozen dependency."""
    root = _canonical(snapshot, "snapshot")
    _directory(root, "snapshot")
    manifest = _manifest(root)
    if manifest.get("body_execution") is not False:
        _fail("capture manifest claims body execution")
    source_group = manifest.get("source", {})
    if source_group.get("before") != source_group.get("after"):
        _fail("captured source inventory drifted")
    input_group = manifest.get("input_manifest", {})
    if input_group.get("before") != input_group.get("after"):
        _fail("captured input inventory drifted")
    dependency_group = manifest.get("captured_dependencies", {})
    if dependency_group.get("before", []) != dependency_group.get("after", []):
        _fail("captured source dependency inventory drifted")
    expected: set[str] = {"manifest.json", "source/manifest.json"}
    source_rows = source_group.get("files", [])
    for row in source_rows:
        if not isinstance(row, Mapping):
            _fail("source manifest row is malformed")
        path = root / str(row["snapshot_path"])
        _regular(path, "captured source")
        expected.add(path.relative_to(root).as_posix())
        if _identity(path) != {"bytes": row["bytes"], "sha256": row["sha256"]}:
            _fail(f"captured source drifted: {path}")
    for row in dependency_group.get("files", []):
        if not isinstance(row, Mapping):
            _fail("captured source dependency row is malformed")
        path = root / str(row["snapshot_path"])
        _regular(path, "captured source dependency")
        expected.add(path.relative_to(root).as_posix())
        if _identity(path) != {"bytes": row["bytes"], "sha256": row["sha256"]}:
            _fail(f"captured source dependency drifted: {path}")
    expected_source_manifest = {"schema": "creature-kernel.connected-leg-assembly-source.v1",
                                "files": [{key: row[key] for key in ("path", "bytes", "sha256")}
                                          for row in source_rows]}
    source_manifest, _ = _read_json(root / "source/manifest.json")
    if source_manifest != expected_source_manifest:
        _fail("captured source manifest drifted")
    for row in input_group.get("copies", []):
        path = root / str(row["snapshot_path"])
        _regular(path, "captured concrete input")
        expected.add(path.relative_to(root).as_posix())
        if _identity(path) != {"bytes": row["bytes"], "sha256": row["sha256"]}:
            _fail(f"captured input drifted: {path}")
    actual = {path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file()}
    if actual != expected:
        _fail("snapshot contains missing or unexpected files")
    dependency = _dependency_identity()
    recorded = manifest.get("dependency", {})
    if dependency != recorded.get("before") or dependency != recorded.get("after"):
        _fail("frozen dependency identity drifted")
    recorded_adapters = manifest.get("adapter_dependency")
    if recorded_adapters is not None:
        adapter_dependency = _adapter_dependency_identity(root / SNAPSHOT_SOURCE)
        if (adapter_dependency != recorded_adapters.get("before") or
                adapter_dependency != recorded_adapters.get("after")):
            _fail("source-adapter dependency identity drifted")
    return manifest


def _snapshot_path(snapshot: Path, relative: str) -> Path:
    path = snapshot / relative
    try:
        path.relative_to(snapshot)
    except ValueError:
        _fail(f"snapshot path escapes capture: {relative}")
    _regular(path, "captured path")
    return path


def _path_map(manifest: Mapping[str, Any]) -> dict[tuple[str, str], Path]:
    rows = manifest.get("input_manifest", {}).get("path_map", [])
    result: dict[tuple[str, str], Path] = {}
    for row in rows:
        if isinstance(row, Mapping) and isinstance(row.get("case_id"), str) and isinstance(row.get("field"), str):
            result[(row["case_id"], row["field"])] = Path(str(row["snapshot_path"]))
    return result


def _jsonable(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if type(value) in (str, int, float, bool) or value is None:
        if isinstance(value, float) and not math.isfinite(value):
            _fail("mesh contains a non-finite number")
        return value
    _fail(f"value is not JSON-serializable: {type(value).__name__}")


def _load_case_inputs(snapshot: Path, manifest: Mapping[str, Any], document: Mapping[str, Any]) -> list[dict[str, Any]]:
    cases = document.get("cases")
    if not isinstance(cases, list) or not cases:
        _fail("captured inputs must contain a non-empty cases list")
    mappings = _path_map(manifest)
    loaded: list[dict[str, Any]] = []
    for index, raw_case in enumerate(cases):
        if not isinstance(raw_case, Mapping):
            _fail(f"case {index} is not an object")
        case = dict(raw_case)
        case_id = str(case.get("id", f"case-{index:02d}"))
        values: dict[str, Any] = {}
        for field in MAPPED_INPUT_FIELDS:
            relative = mappings.get((case_id, field))
            if relative is None:
                _fail(f"captured path map lacks {case_id}.{field}")
            value, _ = _read_json(_snapshot_path(snapshot, str(relative)))
            values[field] = value
        for field in OPTIONAL_MAPPED_INPUT_FIELDS:
            relative = mappings.get((case_id, field))
            if relative is not None:
                values[field], _ = _read_json(_snapshot_path(snapshot, str(relative)))
        values["leg_inputs"] = case.get("leg_inputs", {})
        loaded.append({"id": case_id, "case": case, "values": values})
    return loaded


def _load_body_config(snapshot: Path, manifest: Mapping[str, Any],
                      logical_path: str) -> Mapping[str, Any]:
    relative = Path(logical_path)
    if relative.is_absolute() or ".." in relative.parts or relative.suffix != ".json":
        _fail("--body-config must name a relative captured JSON file")
    rows = manifest.get("source", {}).get("files", [])
    match = next((row for row in rows
                  if isinstance(row, Mapping) and row.get("path") == relative.as_posix()), None)
    if not isinstance(match, Mapping) or not isinstance(match.get("snapshot_path"), str):
        _fail(f"--body-config file is not captured: {logical_path}")
    value, _ = _read_json(_snapshot_path(snapshot, str(match["snapshot_path"])))
    return _mapping(value, "body-config")


def _module_package(source_root: Path) -> str:
    package_name = "ck_connected_leg_snapshot"
    package = ModuleType(package_name)
    package.__path__ = [str(source_root)]  # type: ignore[attr-defined]
    package.__package__ = package_name
    sys.modules[package_name] = package
    return package_name


def _load_collaborators(snapshot: Path, manifest: Mapping[str, Any],
                        rest_only: bool = False) -> dict[str, Any]:
    source_root = snapshot / SNAPSHOT_SOURCE
    package = _module_package(source_root)
    paths = {row.get("path"): source_root / str(row.get("path"))
             for row in manifest.get("source", {}).get("files", []) if isinstance(row, Mapping)}
    result: dict[str, Any] = {}
    dependency_root = Path(str(manifest["dependency"]["root"]))
    generic_transition = dependency_root / "source/experiments/pelvis-thigh-transition/construction.py"
    if generic_transition.is_file():
        result["generic_transition"] = _load_module(
            "_ck_connected_leg_generic_transition", generic_transition)
    broadphase_path = paths.get("collision_broadphase.py")
    if broadphase_path is not None:
        broadphase = _load_module(f"{package}.collision_broadphase", broadphase_path)
        recorded_core = manifest.get("dependency", {}).get("before", {}).get("collision_core", {})
        recorded_core_path = recorded_core.get("path") if isinstance(recorded_core, Mapping) else None
        declared_core_path = getattr(broadphase, "FROZEN_CORE_PATH", None)
        if (recorded_core_path is None or declared_core_path is None
                or Path(str(declared_core_path)).resolve() != Path(str(recorded_core_path)).resolve()):
            _fail("captured collision broadphase does not declare the pinned collision core")
        core_before = recorded_core.get("before")
        core_after = recorded_core.get("after")
        current_core = _identity(Path(str(declared_core_path)))
        if current_core != core_before or current_core != core_after:
            _fail("pinned collision core identity drifted")
        result["collision_broadphase"] = broadphase
    names = ("construction", "root_source", "hip_source")
    if not rest_only:
        names += ("binding", "checks", "perturbations",
                  "foot_construction", "foot_form_construction",
                  "foot_junction_construction",
                  "arm_construction", "head_construction",
        "tail_construction",
                  "torso_refinement", "thorax_foundation",
                  "thorax_foundation_checks")
    for name in names:
        path = paths.get(f"{name}.py")
        if path is not None:
            result[name] = _load_module(f"{package}.{name}", path)
            if name == "construction":
                # Captured body_assembly imports these historical top-level
                # names. Bind them before loading it, never to live modules.
                sys.modules["construction"] = result[name]
            elif name in {"root_source", "hip_source", "binding",
                          "foot_construction", "foot_junction_construction",
                          "arm_construction", "head_construction",
                          "foot_form_construction", "tail_construction",
                          "torso_refinement", "thorax_foundation"}:
                sys.modules[name] = result[name]
    if not rest_only:
        pelvis_calculator_path = paths.get("pelvis_foundation.py")
        if pelvis_calculator_path is not None:
            result["pelvis_foundation"] = _load_module(
                f"{package}.pelvis_foundation", pelvis_calculator_path
            )
            # The captured abdomen provider has a package-relative import and
            # a top-level fallback; bind both identities before it loads.
            sys.modules["pelvis_foundation"] = result["pelvis_foundation"]
        abdomen_calculator_path = paths.get("abdomen_foundation.py")
        if abdomen_calculator_path is not None:
            result["abdomen_foundation_calculator"] = _load_module(
                f"{package}.abdomen_foundation", abdomen_calculator_path
            )
            sys.modules["abdomen_foundation"] = result["abdomen_foundation_calculator"]
        abdomen_provider_path = paths.get("abdomen_foundation_provider.py")
        if abdomen_provider_path is not None:
            result["abdomen_foundation_provider"] = _load_module(
                f"{package}.abdomen_foundation_provider", abdomen_provider_path
            )
            sys.modules["abdomen_foundation_provider"] = result["abdomen_foundation_provider"]
            # The body seam calls this selected provider ``abdomen_foundation``;
            # retain the filename-qualified key for provenance and diagnostics.
            result["abdomen_foundation"] = result["abdomen_foundation_provider"]
    checks = result.get("checks")
    if checks is not None and result.get("collision_broadphase") is not None:
        setter = getattr(checks, "_set_broadphase", None)
        if callable(setter):
            setter(result["collision_broadphase"])
    foot_path = paths.get("foot_construction.py")
    foot_input_path = paths.get("foot-inputs.json")
    if foot_path is not None or foot_input_path is not None:
        if foot_path is None or foot_input_path is None:
            _fail("foot_construction.py and foot-inputs.json must be captured together")
        if result.get("foot_construction") is None:
            result["foot_construction"] = _load_module(
                f"{package}.foot_construction", foot_path)
        sys.modules["foot_construction"] = result["foot_construction"]
        result["foot_inputs"], _ = _read_json(foot_input_path)
    if not rest_only:
        input_files = {
            "arm_inputs": "arm-inputs.json",
            "arm_refinement_inputs": "arm-refinement-inputs.json",
            "head_inputs": "head-inputs.json",
            "head_refinement_inputs": "head-refinement-inputs.json",
            "foot_form_inputs": "foot-form-inputs.json",
            "foot_junction_policy": "foot-junction-policy.json",
            "torso_refinement_inputs": "torso-refinement-inputs.json",
            "torso_silhouette_inputs": "torso-silhouette-inputs.json",
            "torso_silhouette_correction_inputs": "torso-silhouette-correction-inputs.json",
            "torso_chest_depth_ablation_inputs": "torso-chest-depth-ablation-inputs.json",
            "torso_chest_envelope_inputs": "torso-chest-envelope-inputs.json",
            "thorax_foundation_baseline_inputs": "thorax-foundation-baseline-inputs.json",
            "thorax_foundation_width_inputs": "thorax-foundation-width-inputs.json",
            "thorax_foundation_fullness_inputs": "thorax-foundation-fullness-inputs.json",
            "abdomen_foundation_baseline_inputs": "abdomen-foundation-baseline-inputs.json",
            "abdomen_foundation_bow_inputs": "abdomen-foundation-bow-inputs.json",
            "abdomen_foundation_fullness_inputs": "abdomen-foundation-fullness-inputs.json",
            "tail_inputs": "tail-inputs.json",
        }
        for name, filename in input_files.items():
            input_path = paths.get(filename)
            if input_path is not None:
                result[name], _ = _read_json(input_path)
        body_path = paths.get("body_assembly.py")
        if body_path is not None:
            result["body_assembly"] = _load_module(f"{package}.body_assembly", body_path)
    renderer_path = Path(str(manifest["dependency"]["before"]["renderer"]["path"]))
    result["render"] = _load_module("ck_connected_leg_frozen_renderer", renderer_path)
    return result


def _protocol_poses(protocol: Mapping[str, Any]) -> list[dict[str, Any]]:
    poses = protocol.get("poses", protocol.get("baseline_poses"))
    if not isinstance(poses, list) or not poses:
        _fail("protocol must declare a non-empty poses list")
    result = []
    for index, row in enumerate(poses):
        if not isinstance(row, Mapping) or not isinstance(row.get("id"), str):
            _fail(f"protocol pose {index} is malformed")
        angles = row.get("angles")
        if not isinstance(angles, Mapping):
            # The protocol stores pose metadata (for example ``label`` and
            # ``meaning``) beside the two executable side-angle records.
            # Pass only the declared binding input shape to binding.pose;
            # metadata is retained in the captured protocol itself.
            if all(side in row and isinstance(row[side], Mapping) for side in ("left", "right")):
                angles = {side: row[side] for side in ("left", "right")}
                if isinstance(row.get("head"), Mapping):
                    angles["head"] = row["head"]
            else:
                angles = {key: value for key, value in row.items() if key != "id"}
        result.append({"id": row["id"], "angles": dict(angles)})
    return result


def _vertices(mesh: Any) -> list[list[float]]:
    if not isinstance(mesh, Mapping) or not isinstance(mesh.get("vertices"), (list, tuple)):
        _fail("mesh must expose a vertices list")
    points = []
    for point in mesh["vertices"]:
        if not isinstance(point, (list, tuple)) or len(point) != 3:
            _fail("mesh vertex must be a three-component point")
        values = [float(item) for item in point]
        if not all(math.isfinite(item) for item in values):
            _fail("mesh vertex is not finite")
        points.append(values)
    if not points:
        _fail("mesh has no vertices")
    return points


def _bounds(meshes: Iterable[Any]) -> list[list[float]]:
    points = [point for mesh in meshes for point in _vertices(mesh)]
    low = [min(point[axis] for point in points) for axis in range(3)]
    high = [max(point[axis] for point in points) for axis in range(3)]
    span = max(high[axis] - low[axis] for axis in range(3))
    margin = max(span * 0.05, 1e-6)
    return [[value - margin for value in low], [value + margin for value in high]]


def _render_bounds_inputs(results: Iterable[Mapping[str, Any]]) -> list[Any]:
    """Build one shared bounds inventory for ordinary and perturbation surfaces."""
    meshes: list[Any] = []
    for result in results:
        meshes.extend(mesh for mesh in result.get("bounds_inputs", []) if isinstance(mesh, Mapping))
        meshes.extend(item["mesh"] for item in result.get("perturbation_meshes", [])
                      if isinstance(item, Mapping) and isinstance(item.get("mesh"), Mapping))
    return meshes


def _overlays(points: Any) -> list[dict[str, Any]]:
    if not isinstance(points, Mapping):
        return []
    result = []
    for side, value in points.items():
        if not isinstance(value, Mapping):
            continue
        for start_name, end_name in (("J", "T"), ("J", "K"), ("J", "A")):
            if start_name in value and end_name in value:
                result.append({"start": _jsonable(value[start_name]), "end": _jsonable(value[end_name]),
                               "color": [211, 77, 77] if str(side).lower().startswith("l") else [55, 112, 213],
                               "label": f"diagnostic {side} {start_name}-{end_name}"})
    return result


def _report_pass(report: Any) -> bool:
    if not isinstance(report, Mapping):
        _fail("checker report must be an object")
    if type(report.get("pass")) is bool:
        return bool(report["pass"])
    if report.get("outcome") in ("pass", "support", "reject", "failed"):
        return report["outcome"] in ("pass", "support")
    nested = report.get("technical")
    if isinstance(nested, Mapping) and type(nested.get("pass")) is bool:
        return bool(nested["pass"])
    _fail("checker report lacks an explicit pass/reject result")


def _safe_token(value: Any) -> str:
    text = str(value)
    if not text or any(character not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-"
                       for character in text):
        _fail(f"evidence name is not a safe filename token: {text!r}")
    return text


def _mesh_mapping(value: Any) -> bool:
    return (isinstance(value, Mapping) and isinstance(value.get("vertices"), (list, tuple))
            and isinstance(value.get("quads", value.get("faces")), (list, tuple)))


def _save_perturbation_evidence(case_dir: Path, evidence: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Persist every returned diagnostic value and identify mesh values for render."""
    render_inputs: list[dict[str, Any]] = []
    records = evidence.get("perturbations")
    if not isinstance(records, list):
        return render_inputs
    for record in records:
        if not isinstance(record, Mapping):
            continue
        perturbation_id = _safe_token(record.get("id", "unknown"))
        diagnostic_meshes = record.get("diagnostic_meshes", {})
        if not isinstance(diagnostic_meshes, Mapping):
            continue
        diagnostic_dir = case_dir / "perturbations" / perturbation_id
        for name, value in diagnostic_meshes.items():
            filename = _safe_token(name) + ".json"
            target = diagnostic_dir / filename
            _write_json(target, _jsonable(value))
            if _mesh_mapping(value):
                render_inputs.append({
                    "perturbation_id": perturbation_id,
                    "name": _safe_token(name),
                    "path": target.relative_to(case_dir).as_posix(),
                    "mesh": _jsonable(value),
                })
    return render_inputs


def _perturbation_result_ready(result: Any, expected_ids: list[str]) -> bool:
    if not isinstance(result, Mapping) or result.get("status") != "pass":
        return False
    records = result.get("perturbations")
    if not isinstance(records, list) or [row.get("id") for row in records if isinstance(row, Mapping)] != expected_ids:
        return False
    return len(records) == len(expected_ids) and all(
        isinstance(row, Mapping) and row.get("status") == "pass" for row in records
    )


def _aggregate_perturbations(protocol: Mapping[str, Any], results: Iterable[Mapping[str, Any]],
                             perturbation_api_available: bool = False) -> dict[str, Any]:
    """Summarize per-case perturbation evidence without turning omissions into pass."""
    declared = _perturbation_status(protocol)
    if declared["status"] == "not-declared":
        return declared
    case_rows = list(results)
    case_results = [row.get("perturbations") for row in case_rows]
    if perturbation_api_available:
        blockers = []
        for row in case_rows:
            perturbation = row.get("perturbations")
            if isinstance(perturbation, Mapping) and perturbation.get("status") == "blocked-by-earlier-error":
                blockers.append(perturbation.get("blocker", {"case": row.get("id")}))
            elif row.get("status") == "exception" and perturbation is None:
                blockers.append({"case": row.get("id"), "stage": "unknown",
                                 "detail": "case exception occurred before perturbation dispatch"})
        if blockers:
            return {**declared, "status": "blocked-by-earlier-error", "execution": "not-run",
                    "blocker": blockers}
    if case_results and all(isinstance(row, Mapping) and row.get("status") == "pass"
                            and _perturbation_result_ready(row, declared.get("declared_ids", []))
                            for row in case_results):
        return {**declared, "status": "pass", "execution": "captured"}
    if case_results and all(isinstance(row, Mapping) and row.get("status") == "leg-only"
                            for row in case_results):
        return {**declared, "status": "leg-only", "execution": "captured",
                "coverage": "leg-baseline-only", "foot_coverage": "not-run"}
    if any(isinstance(row, Mapping) and row.get("status") == "failed" for row in case_results):
        return {**declared, "status": "failed", "execution": "captured"}
    if any(isinstance(row, Mapping) and row.get("status") == "unavailable" for row in case_results):
        return {**declared, "status": "unavailable", "execution": "captured"}
    return declared


def _perturbation_status(protocol: Mapping[str, Any]) -> dict[str, Any]:
    declared = protocol.get("input_perturbations", [])
    if not isinstance(declared, list):
        return {"status": "invalid", "declared_count": 0,
                "reason": "protocol input_perturbations is not a list"}
    return {
        "status": "not-implemented" if declared else "not-declared",
        "execution": "not-run",
        "declared_count": len(declared),
        "declared_ids": [row.get("id") for row in declared if isinstance(row, Mapping)],
        "reason": "declared perturbations require the captured run_case hook",
    }


def _readiness(modules: Mapping[str, Any], protocol: Mapping[str, Any]) -> dict[str, Any]:
    checks = modules.get("checks")
    available = {
        name: bool(checks is not None and callable(getattr(checks, name, None)))
        for name in ("check_mesh", "check_binding", "check_pose", "compare_root")
    }
    perturbation_api_available = bool(
        modules.get("perturbations") is not None
        and callable(getattr(modules["perturbations"], "run_case", None))
    )
    perturbation_protocol = _perturbation_status(protocol)
    if perturbation_protocol["status"] == "not-implemented" and perturbation_api_available:
        perturbation_protocol = {
            **perturbation_protocol,
            "implementation": "captured",
            "reason": "captured run_case hook is available; execution is recorded per case",
        }
    else:
        perturbation_protocol = {**perturbation_protocol, "implementation": "pending"}
    return {
        "status": "ready" if all(available.values()) else "pending",
        "required_checks": {
            key: {"signature": signature, "available": available[key.split(".")[-1]]}
            for key, signature in REQUIRED_CHECK_SIGNATURES.items()
        },
        "new_source_leg_inputs": list(CANONICAL_LEG_INPUT_FIELDS),
        "protocol_pose_field": "baseline_poses",
        "protocol_perturbations": perturbation_protocol,
        "perturbation_api": {
            "signature": PERTURBATION_SIGNATURE,
            "available": perturbation_api_available,
        },
    }


def _render_one(render: Any, mesh: Mapping[str, Any], path: Path, title: str,
                status: str, bounds: list[list[float]], overlays: list[dict[str, Any]]) -> dict[str, Any]:
    try:
        surface = render.render_views(mesh["vertices"], mesh.get("quads", mesh.get("faces")), path,
                                      title, status, bounds=bounds, overlays=None,
                                      underside=True, allow_crop=False)
        diagnostic = None
        if overlays:
            diagnostic = render.render_views(mesh["vertices"], mesh.get("quads", mesh.get("faces")),
                                             path.with_name(path.stem + "-diagnostic.png"), title,
                                             status, bounds=bounds, overlays=overlays,
                                             underside=False, allow_crop=False)
        return {"surface": _jsonable(surface), "diagnostic": _jsonable(diagnostic), "status": status}
    except Exception as exc:
        return {"status": "exception", "exception": {"type": type(exc).__name__, "message": str(exc)}}


def _visual_status(result: Mapping[str, Any], rest_only: bool, perturbation: bool = False) -> str:
    if result.get("status") == "rejected":
        return "REJECTED"
    if result.get("status") == "exception":
        return "EXECUTION ERROR - UNCLASSIFIED"
    if rest_only:
        return "INTERNAL DIAGNOSTIC - NO FULL PASS"
    if result.get("status") == "pending" or perturbation:
        return "CHECKS PENDING - VISUAL PENDING"
    return "TECHNICAL PASS - VISUAL PENDING"


def _evaluate(module: Any, mesh: Mapping[str, Any]) -> list[Any]:
    """Use the existing two-level evaluator, retaining tiny test doubles."""
    function = getattr(module, "evaluate", None)
    if not callable(function):
        _fail("construction collaborator has no evaluate function")
    try:
        value = function(mesh, levels=2)
    except TypeError as exc:
        # Existing synthetic runner tests predate the explicit levels keyword.
        # Only retry that narrow compatibility shape; do not mask other errors.
        if "unexpected keyword argument 'levels'" not in str(exc):
            raise
        value = function(mesh)
    if not isinstance(value, (list, tuple)) or not value:
        _fail("construction.evaluate must return a non-empty sequence")
    return list(value)


def _source_mode(values: Mapping[str, Any], modules: Mapping[str, Any]) -> bool:
    root_source = modules.get("root_source")
    hip_source = modules.get("hip_source")
    source_present = root_source is not None or hip_source is not None
    if not source_present:
        return False
    if root_source is None or hip_source is None:
        _fail("root_source.py and hip_source.py are required together")
    if not callable(getattr(root_source, "reconstruct_source_case", None)):
        _fail("root_source.reconstruct_source_case is not captured")
    if not callable(getattr(hip_source, "bind_source_case", None)):
        _fail("hip_source.bind_source_case is not captured")
    if values.get("original_case") is None:
        _fail("source rebuild requires the captured original_case input")
    return True


def _foot_case_inputs(foot_inputs: Any, case_id: str) -> Mapping[str, Any]:
    if not isinstance(foot_inputs, Mapping):
        _fail("captured foot-inputs.json must be an object")
    rows = [row for row in foot_inputs.get("cases", [])
            if isinstance(row, Mapping) and row.get("case_id") == case_id]
    if len(rows) != 1:
        _fail(f"captured foot-inputs.json lacks unique case {case_id}")
    sides = rows[0].get("sides")
    if not isinstance(sides, Mapping):
        _fail(f"captured foot-inputs.json case {case_id} lacks sides")
    return sides


def _case_row(document: Any, case_id: str, label: str) -> Mapping[str, Any]:
    if not isinstance(document, Mapping):
        _fail(f"captured {label} must be an object")
    rows = [row for row in document.get("cases", [])
            if isinstance(row, Mapping) and row.get("case_id") == case_id]
    if len(rows) != 1:
        _fail(f"captured {label} lacks unique case {case_id}")
    return rows[0]


def _component_case_inputs(document: Any, case_id: str, key: str,
                           label: str) -> Mapping[str, Any]:
    if not isinstance(document, Mapping):
        _fail(f"captured {label} must be an object")
    rows = [row for row in document.get("cases", [])
            if isinstance(row, Mapping) and row.get("case_id") == case_id]
    if len(rows) != 1:
        _fail(f"captured {label} lacks unique case {case_id}")
    value = rows[0].get(key)
    if not isinstance(value, Mapping):
        _fail(f"captured {label} case {case_id} lacks {key}")
    return value


def _body_dependencies(modules: Mapping[str, Any],
                        optional: Mapping[str, Any] | None = None) -> Any:
    body = modules.get("body_assembly")
    dependencies = getattr(body, "AssemblyDependencies", None)
    if not callable(dependencies):
        _fail("body_assembly.AssemblyDependencies is not captured")
    selected = optional or {}
    dependency_kwargs = dict(
        root_source=modules.get("root_source"),
        hip_source=modules.get("hip_source"),
        leg_builder=modules.get("construction"),
        binding=modules.get("binding"),
        foot_builder=selected.get("foot_builder", modules.get("foot_construction")),
        foot_builder_name=selected.get("foot_builder_name", "foot_construction.build"),
        arm_builder=modules.get("arm_construction"),
        head_builder=modules.get("head_construction"),
        tail_builder=selected.get("tail_builder"),
        tail_builder_name=selected.get("tail_builder_name"),
        torso_refinement=modules.get("torso_refinement"),
    )
    # Preserve the legacy dependency call unless a body config explicitly
    # selects an optional foundation provider.
    thorax_foundation = selected.get("thorax_foundation")
    if thorax_foundation is not None:
        dependency_kwargs["thorax_foundation"] = thorax_foundation
    abdomen_foundation = selected.get("abdomen_foundation")
    if abdomen_foundation is not None:
        dependency_kwargs["abdomen_foundation"] = abdomen_foundation
    return dependencies(**dependency_kwargs)


def _assemble_selected_body(modules: Mapping[str, Any],
                            source_case: Mapping[str, Any],
                            leg_inputs: Mapping[str, Any],
                            optional: Mapping[str, Any]) -> Mapping[str, Any]:
    """Assemble one explicitly selected source-driven body.

    This is the single body-assembly seam used by the normal runner and by
    bounded body evidence probes.  The kwargs are intentionally the existing
    runner kwargs; the helper does not introduce a second construction lane.
    """
    body = modules.get("body_assembly")
    if body is None or not callable(getattr(body, "assemble", None)):
        _fail("body_assembly.assemble is not captured")
    body_kwargs = {
        "foot_inputs": optional["foot_inputs"],
        "arm_inputs": optional["arm_inputs"],
        "head_inputs": optional["head_inputs"],
        "dependencies": _body_dependencies(modules, optional),
    }
    if optional["foot_form_inputs"] is not None:
        body_kwargs["foot_form_inputs"] = optional["foot_form_inputs"]
    if optional["foot_policy"] is not None:
        body_kwargs["foot_policy"] = optional["foot_policy"]
    if optional["tail_inputs"] is not None:
        body_kwargs["tail_inputs"] = optional["tail_inputs"]
    if optional["source_refinement_inputs"] is not None:
        body_kwargs["source_refinement_inputs"] = optional["source_refinement_inputs"]
    if optional["thorax_foundation_inputs"] is not None:
        body_kwargs["thorax_foundation_inputs"] = optional["thorax_foundation_inputs"]
    if optional["abdomen_foundation_inputs"] is not None:
        body_kwargs["abdomen_foundation_inputs"] = optional["abdomen_foundation_inputs"]
    if optional.get("pelvis_foundation_inputs") is not None:
        body_kwargs["pelvis_foundation_inputs"] = optional["pelvis_foundation_inputs"]
    result = body.assemble(source_case, leg_inputs, **body_kwargs)
    if not isinstance(result, Mapping):
        _fail("body_assembly.assemble must return a mapping")
    return result


def _body_provisional_protocol(protocol: Mapping[str, Any], *,
                               has_arms: bool, has_head: bool) -> dict[str, Any]:
    """Overlay two internal body poses while retaining captured thresholds."""
    result = dict(protocol)
    result.pop("poses", None)
    poses = copy.deepcopy(BODY_PROVISIONAL_POSES)
    if not has_arms:
        for row in poses:
            for side in ("left", "right"):
                for name in ("shoulder_raise", "shoulder_forward", "elbow"):
                    row[side][name] = 0
    if not has_head:
        for row in poses:
            row["head"] = {"yaw": 0, "nod": 0}
    result["baseline_poses"] = list(poses)
    result["body_provisional_evidence"] = {
        "status": "internal-only",
        "pose_count_per_case": 2,
        "threshold_source": "captured connected-leg protocol",
        "whole_character_checkpoint": False,
        "arms_enabled": has_arms,
        "head_enabled": has_head,
    }
    return result


def _body_config_section(body_config: Any, key: str) -> Mapping[str, Any] | None:
    if body_config is None:
        return None
    document = _mapping(body_config, "body-config")
    value = document.get(key)
    if value is None:
        return None
    return _mapping(value, f"body-config.{key}")


def _body_optional_inputs(modules: Mapping[str, Any], case_id: str,
                          body_config: Mapping[str, Any] | None = None) -> dict[str, Any]:
    values: dict[str, Any] = {
        "source_refinement_inputs": None,
        "thorax_foundation_inputs": None,
        "thorax_foundation": None,
        "thorax_foundation_input_name": None,
        "abdomen_foundation_inputs": None,
        "abdomen_foundation": None,
        "abdomen_foundation_input_name": None,
        "pelvis_foundation_inputs": None,
        "pelvis_foundation": modules.get("pelvis_foundation"),
        "pelvis_foundation_input_name": None,
        "foot_inputs": None,
        "foot_builder": modules.get("foot_construction"),
        "foot_builder_name": "foot_construction.build",
        "foot_form_inputs": None,
        "foot_policy": None,
        "arm_inputs": None,
        "head_inputs": None,
        "tail_inputs": None,
        "tail_builder": None,
        "tail_builder_name": None,
    }

    torso_section = _body_config_section(body_config, "torso_refinement")
    foundation_section = _body_config_section(body_config, "thorax_foundation")
    abdomen_section = _body_config_section(body_config, "abdomen_foundation")
    pelvis_section = _body_config_section(body_config, "pelvis_foundation")
    if torso_section is not None and (foundation_section is not None
                                      or abdomen_section is not None
                                      or pelvis_section is not None):
        _fail("body-config.torso_refinement and foundation sections are mutually exclusive")
    if abdomen_section is not None and foundation_section is None:
        _fail("body-config.abdomen_foundation requires thorax_foundation")
    if pelvis_section is not None:
        unknown_pelvis = set(pelvis_section) - {"inputs", "authority"}
        if unknown_pelvis:
            _fail(f"body-config.pelvis_foundation has unsupported fields: {sorted(unknown_pelvis)!r}")
        if foundation_section is None or abdomen_section is None:
            _fail("body-config.pelvis_foundation requires thorax_foundation and abdomen_foundation")
        if foundation_section.get("inputs") != "thorax-foundation-baseline-inputs.json":
            _fail("body-config.pelvis_foundation requires thorax-foundation-baseline-inputs.json")
        if abdomen_section.get("inputs") != "abdomen-foundation-baseline-inputs.json":
            _fail("body-config.pelvis_foundation requires abdomen-foundation-baseline-inputs.json")

    if torso_section is not None:
        selected_file = torso_section.get("inputs")
        torso_input_keys = {
            "torso-refinement-inputs.json": "torso_refinement_inputs",
            "torso-silhouette-inputs.json": "torso_silhouette_inputs",
            "torso-silhouette-correction-inputs.json": "torso_silhouette_correction_inputs",
            "torso-chest-depth-ablation-inputs.json": "torso_chest_depth_ablation_inputs",
            "torso-chest-envelope-inputs.json": "torso_chest_envelope_inputs",
        }
        selected_input_key = torso_input_keys.get(selected_file)
        if selected_input_key is None:
            _fail("body-config.torso_refinement.inputs selects an unsupported captured input")
        if modules.get("torso_refinement") is None:
            _fail("body-config torso refinement requires torso_refinement.py")
        values["source_refinement_inputs"] = modules.get(selected_input_key)
        if values["source_refinement_inputs"] is None:
            _fail(f"body-config torso refinement requires {selected_file}")

    if foundation_section is not None:
        selected_file = foundation_section.get("inputs")
        foundation_input_keys = {
            "thorax-foundation-baseline-inputs.json": "thorax_foundation_baseline_inputs",
            "thorax-foundation-width-inputs.json": "thorax_foundation_width_inputs",
            "thorax-foundation-fullness-inputs.json": "thorax_foundation_fullness_inputs",
        }
        selected_input_key = foundation_input_keys.get(selected_file)
        if selected_input_key is None:
            _fail("body-config.thorax_foundation.inputs selects an unsupported captured input")
        if modules.get("thorax_foundation") is None:
            _fail("body-config thorax foundation requires thorax_foundation.py")
        selected_inputs = modules.get(selected_input_key)
        if selected_inputs is None:
            _fail(f"body-config thorax foundation requires {selected_file}")
        values["thorax_foundation_inputs"] = selected_inputs
        values["thorax_foundation"] = modules["thorax_foundation"]
        values["thorax_foundation_input_name"] = selected_file

    if abdomen_section is not None:
        selected_file = abdomen_section.get("inputs")
        abdomen_input_keys = {
            "abdomen-foundation-baseline-inputs.json": "abdomen_foundation_baseline_inputs",
            "abdomen-foundation-bow-inputs.json": "abdomen_foundation_bow_inputs",
            "abdomen-foundation-fullness-inputs.json": "abdomen_foundation_fullness_inputs",
        }
        selected_input_key = abdomen_input_keys.get(selected_file)
        if selected_input_key is None:
            _fail("body-config.abdomen_foundation.inputs selects an unsupported captured input")
        if modules.get("abdomen_foundation") is None:
            _fail("body-config abdomen foundation requires abdomen_foundation_provider.py")
        selected_inputs = modules.get(selected_input_key)
        if selected_inputs is None:
            _fail(f"body-config abdomen foundation requires {selected_file}")
        values["abdomen_foundation_inputs"] = selected_inputs
        values["abdomen_foundation"] = modules["abdomen_foundation"]
        values["abdomen_foundation_input_name"] = selected_file

    if pelvis_section is not None:
        selected_file = pelvis_section.get("inputs")
        pelvis_input_keys = {
            "pelvis-foundation-baseline-inputs.json": "pelvis_foundation_baseline_inputs",
            "pelvis-foundation-iliac-inputs.json": "pelvis_foundation_iliac_inputs",
            "pelvis-foundation-gluteal-inputs.json": "pelvis_foundation_gluteal_inputs",
        }
        selected_input_key = pelvis_input_keys.get(selected_file)
        if selected_input_key is None:
            _fail("body-config.pelvis_foundation.inputs selects an unsupported captured input")
        if modules.get("pelvis_foundation") is None:
            _fail("body-config pelvis foundation requires pelvis_foundation.py")
        selected_inputs = modules.get(selected_input_key)
        if selected_inputs is None:
            _fail(f"body-config pelvis foundation requires {selected_file}")
        abdomen_inputs = values.get("abdomen_foundation_inputs")
        if (not isinstance(abdomen_inputs, Mapping)
                or abdomen_inputs.get("bow") != 0.0
                or abdomen_inputs.get("fullness") != 1.0):
            _fail("body-config.pelvis_foundation requires direct abdomen baseline values")
        values["pelvis_foundation_inputs"] = selected_inputs
        values["pelvis_foundation_input_name"] = selected_file

    feet_section = _body_config_section(body_config, "feet")
    if feet_section is not None:
        builder = feet_section.get("builder")
        if builder == "foot_form_construction.py":
            if modules.get("foot_form_construction") is None:
                _fail("body-config FOOT004 requires foot_form_construction.py")
            values["foot_inputs"] = _case_row(
                modules.get("foot_form_inputs"), case_id, "foot-form-inputs.json"
            )
            values["foot_builder"] = modules["foot_form_construction"]
            values["foot_builder_name"] = "foot_form_construction.build"
        elif builder == "foot_junction_construction.py":
            if feet_section.get("inputs") != "foot-form-inputs.json":
                _fail("JUNCTION-001 feet.inputs must select foot-form-inputs.json")
            if feet_section.get("policy") != "foot-junction-policy.json":
                _fail("JUNCTION-001 feet.policy must select foot-junction-policy.json")
            if modules.get("foot_junction_construction") is None:
                _fail("body-config JUNCTION-001 requires foot_junction_construction.py")
            if modules.get("foot_form_inputs") is None:
                _fail("body-config JUNCTION-001 requires foot-form-inputs.json")
            policy = modules.get("foot_junction_policy")
            if not isinstance(policy, Mapping):
                _fail("body-config JUNCTION-001 requires foot-junction-policy.json")
            if policy.get("schema") != "creature-kernel.connected-leg-assembly-foot-junction-policy.v1":
                _fail("foot-junction-policy.json has an unsupported schema")
            if policy.get("candidate") != "JUNCTION-001":
                _fail("foot-junction-policy.json must select JUNCTION-001")
            values["foot_form_inputs"] = _case_row(
                modules.get("foot_form_inputs"), case_id, "foot-form-inputs.json"
            )
            values["foot_policy"] = policy
            values["foot_builder"] = modules["foot_junction_construction"]
            values["foot_builder_name"] = "foot_junction_construction.build"
        elif builder == "foot_construction.py":
            if modules.get("foot_construction") is None:
                _fail("body-config diagnostic feet requires foot_construction.py")
            values["foot_inputs"] = _foot_case_inputs(
                modules.get("foot_inputs"), case_id
            )
        else:
            _fail("body-config.feet.builder must select a captured foot builder")
    else:
        legacy_document = modules.get("foot_inputs") if body_config is None else None
        if legacy_document is not None:
            if modules.get("foot_construction") is None:
                _fail("captured foot-inputs.json requires foot_construction.py")
            values["foot_inputs"] = _foot_case_inputs(legacy_document, case_id)

    pairs = (
        ("arms", "arm_construction", "arm_inputs", "arm-inputs.json", "sides"),
        ("head", "head_construction", "head_inputs", "head-inputs.json", "head"),
    )
    for section_key, module_key, input_key, default_file, row_key in pairs:
        selected_file = default_file
        section = _body_config_section(body_config, section_key)
        if section is not None:
            selected_file = section.get("inputs")
            if section_key == "arms":
                allowed_files = {"arm-inputs.json", "arm-refinement-inputs.json"}
                selected_input_key = (
                    "arm_refinement_inputs"
                    if selected_file == "arm-refinement-inputs.json"
                    else "arm_inputs"
                )
            else:
                allowed_files = {"head-inputs.json", "head-refinement-inputs.json"}
                selected_input_key = (
                    "head_refinement_inputs"
                    if selected_file == "head-refinement-inputs.json"
                    else "head_inputs"
                )
            if selected_file not in allowed_files:
                _fail(f"body-config.{section_key}.inputs selects an unsupported captured input")
            input_key = selected_input_key
        document = modules.get(input_key)
        module = modules.get(module_key)
        if document is None:
            if section is not None:
                _fail(f"body-config.{section_key} requires {selected_file}")
            continue
        if module is None:
            _fail(f"captured {input_key}.json requires its construction module")
        values["head_inputs" if section_key == "head" else "arm_inputs"] = (
            _component_case_inputs(document, case_id, row_key, selected_file)
        )

    tail_section = _body_config_section(body_config, "tail")
    if tail_section is not None:
        if tail_section.get("builder") != "tail_construction.py":
            _fail("body-config.tail.builder must select tail_construction.py")
        if modules.get("tail_construction") is None:
            _fail("body-config tail requires tail_construction.py")
        values["tail_inputs"] = _case_row(
            modules.get("tail_inputs"), case_id, "tail-inputs.json"
        )
        values["tail_builder"] = modules["tail_construction"]
        values["tail_builder_name"] = "tail_construction.build"
    return values


def _source_cache_comparison(source_root: Mapping[str, Any],
                             source_rest: Mapping[str, Any],
                             source_binding: Mapping[str, Any],
                             cached_root: Any, cached_rest: Any,
                             cached_binding: Any) -> dict[str, Any]:
    binding_keys = ("base_weights", "evaluated_weights", "rest_frames")
    cached_binding_map = cached_binding if isinstance(cached_binding, Mapping) else {}
    return {
        "cache_role": "comparison-only; never a construction or binding input",
        "root_L0_exact": source_root == cached_root,
        "root_L2_exact": source_rest == cached_rest,
        "root_binding_exact": {
            key: source_binding.get(key) == cached_binding_map.get(key)
            for key in binding_keys
        },
    }


def _case_run(case_data: Mapping[str, Any], protocol: Mapping[str, Any], modules: Mapping[str, Any],
              case_dir: Path, rest_only: bool,
              body_config: Mapping[str, Any] | None = None) -> dict[str, Any]:
    case = case_data["case"]
    values = case_data["values"]
    case_id = str(case_data["id"])
    construction = modules.get("construction")
    if construction is None or not callable(getattr(construction, "build", None)) or not callable(getattr(construction, "evaluate", None)):
        return {"id": case_id, "status": "pending", "reason": "construction API is not captured", "exceptions": []}
    case_dir.mkdir(parents=True, exist_ok=True)
    result: dict[str, Any] = {"id": case_id, "status": "pending", "exceptions": [], "poses": []}
    if body_config is not None:
        result["body_evidence"] = {
            "label": body_config.get("evidence_label"),
            "acceptance": body_config.get("acceptance"),
            "status": body_config.get("status"),
        }
    stage = "construction"
    try:
        cached_root = values["root_mesh"]
        cached_rest = values["prior_rest_mesh"]
        cached_binding = values["prior_hip_binding"]
        leg_inputs = values["leg_inputs"]
        source_comparison: dict[str, Any] | None = None
        body_mode = False
        body_binding: Mapping[str, Any] | None = None
        foot_enabled = False
        tail_enabled = False
        if _source_mode(values, modules):
            stage = "source-reconstruction"
            source_case = values["original_case"]
            body = modules.get("body_assembly")
            if body is not None:
                body_mode = True
                optional = _body_optional_inputs(modules, case_id, body_config)
                stage = "body-assembly"
                body_result = _assemble_selected_body(
                    modules, source_case, leg_inputs, optional
                )
                root = body_result.get("rebuilt_root_l0")
                prior_rest = body_result.get("rebuilt_root_l2")
                prior_binding = body_result.get("rebuilt_root_binding")
                built = body_result.get("final_l0")
                baseline_l0 = built
                baseline_l2 = body_result.get("final_l2")
                body_binding = body_result.get("binding")
                if not all(isinstance(value, Mapping) for value in
                           (root, prior_rest, prior_binding, built,
                            baseline_l2, body_binding)):
                    _fail("body_assembly result lacks rebuilt roots, final L0/L2, or binding")
                source_comparison = _source_cache_comparison(
                    root, prior_rest, prior_binding, cached_root,
                    cached_rest, cached_binding)
                if optional["thorax_foundation_inputs"] is not None:
                    source_comparison = {
                        **source_comparison,
                        "comparison_role": "diagnostic-only",
                        "required_for_full_pass": False,
                        "reason": (
                            "thorax foundation intentionally rebuilds J/skin from "
                            "source; cached root remains comparison-only"
                        ),
                    }
                source_provenance = {
                    "root_source": body_result.get("source_provenance", {}).get("root", {}),
                    "hip_source": body_result.get("source_provenance", {}).get("hip", {}),
                    "refinement": body_result.get("refinement_provenance"),
                    "effective_source_case": body_result.get("effective_source_case"),
                    "cache_comparison": source_comparison,
                    "component_manifest": body_result.get("component_manifest", {}),
                    "foundation_input_selection": {
                        "thorax": optional.get("thorax_foundation_input_name"),
                        "abdomen": optional.get("abdomen_foundation_input_name"),
                        "pelvis": optional.get("pelvis_foundation_input_name"),
                    },
                }
                foundation_records = body_result.get("foundation_records")
                if foundation_records is not None:
                    foundation_records = _mapping(
                        foundation_records, "body_result.foundation_records"
                    )
                    if "abdomen_foundation" in foundation_records:
                        combined_name = "combined-foundation-source-evidence.json"
                        _write_json(
                            case_dir / combined_name,
                            _jsonable(foundation_records),
                        )
                        source_provenance["combined_foundation_source_evidence"] = combined_name
                        result["combined_foundation_source_evidence"] = combined_name
                        evidence_name = "abdomen-foundation-source-evidence.json"
                        _write_json(
                            case_dir / evidence_name,
                            _jsonable(foundation_records["abdomen_foundation"]),
                        )
                        source_provenance["abdomen_foundation_source_evidence"] = evidence_name
                        result["abdomen_foundation_source_evidence"] = evidence_name
                    if "pelvis_foundation" in foundation_records:
                        evidence_name = "pelvis-foundation-source-evidence.json"
                        _write_json(
                            case_dir / evidence_name,
                            _jsonable(foundation_records["pelvis_foundation"]),
                        )
                        source_provenance["pelvis_foundation_source_evidence"] = evidence_name
                        result["pelvis_foundation_source_evidence"] = evidence_name
                    if "thorax_foundation" in foundation_records:
                        evidence_name = "thorax-foundation-source-evidence.json"
                        _write_json(
                            case_dir / evidence_name,
                            _jsonable(foundation_records["thorax_foundation"]),
                        )
                        source_provenance["thorax_foundation_source_evidence"] = evidence_name
                        result["thorax_foundation_source_evidence"] = evidence_name
                    elif (optional["thorax_foundation_inputs"] is not None
                          and optional["abdomen_foundation_inputs"] is None):
                        evidence_name = "thorax-foundation-source-evidence.json"
                        _write_json(case_dir / evidence_name, _jsonable(foundation_records))
                        source_provenance["thorax_foundation_source_evidence"] = evidence_name
                        result["thorax_foundation_source_evidence"] = evidence_name
                _write_json(case_dir / "source-provenance.json", _jsonable(source_provenance))
                # Keep existing perturbation evidence on the leg-only baseline.
                leg_built = construction.build(root, leg_inputs)
                leg_levels = _evaluate(construction, leg_built)
                foot_enabled = (
                    optional["foot_inputs"] is not None or
                    optional["foot_form_inputs"] is not None
                )
                tail_enabled = optional["tail_inputs"] is not None
            else:
                source_module = modules["root_source"]
                source_result = source_module.reconstruct_source_case(source_case)
                source_levels = source_result.get("levels") if isinstance(source_result, Mapping) else None
                if not isinstance(source_levels, Mapping) or "L0" not in source_levels or "L2" not in source_levels:
                    _fail("root_source reconstruction must return L0 and L2 levels")
                root = source_levels["L0"]
                prior_rest = source_levels["L2"]
                hip_result = modules["hip_source"].bind_source_case(
                    root, prior_rest, source_case, leg_inputs=leg_inputs)
                if not isinstance(hip_result, Mapping) or not isinstance(hip_result.get("binding"), Mapping):
                    _fail("hip_source binding must return a binding mapping")
                prior_binding = hip_result["binding"]
                source_comparison = _source_cache_comparison(
                    root, prior_rest, prior_binding, cached_root, cached_rest, cached_binding)
                _write_json(case_dir / "source-provenance.json", _jsonable({
                    "root_source": source_result.get("provenance", {}),
                    "hip_source": hip_result.get("provenance", {}),
                    "cache_comparison": source_comparison,
                }))
        else:
            # Older leg-only captures predate the source adapters.  Preserve
            # that mode, but keep the cached values in this explicitly named
            # compatibility path rather than silently mixing modes.
            root = cached_root
            prior_rest = cached_rest
            prior_binding = cached_binding

        if not body_mode:
            leg_built = construction.build(root, leg_inputs)
            leg_levels = _evaluate(construction, leg_built)
            built = leg_built
            levels = leg_levels
            foot = modules.get("foot_construction")
            foot_inputs = modules.get("foot_inputs")
            if foot is not None or foot_inputs is not None:
                if foot is None or foot_inputs is None:
                    _fail("foot_construction.py and foot-inputs.json are required together")
                stage = "foot-construction"
                foot_row = _foot_case_inputs(foot_inputs, case_id)
                built = foot.build(leg_built, leg_inputs, foot_row)
                levels = _evaluate(foot, built)
                foot_enabled = True
            baseline_l0 = levels[0]
            baseline_l2 = levels[-1]
        _write_json(case_dir / "prior-root.json", _jsonable(cached_root))
        _write_json(case_dir / "prior-rest.json", _jsonable(cached_rest))
        _write_json(case_dir / "prior-hip-binding.json", _jsonable(cached_binding))
        if source_comparison is not None:
            _write_json(case_dir / "rebuilt-root-L0.json", _jsonable(root))
            _write_json(case_dir / "rebuilt-root-L2.json", _jsonable(prior_rest))
            _write_json(case_dir / "rebuilt-root-binding.json", _jsonable(prior_binding))
            result["rebuilt_root_artifacts"] = {
                "L0": "rebuilt-root-L0.json",
                "L2": "rebuilt-root-L2.json",
                "binding": "rebuilt-root-binding.json",
            }
        _write_json(case_dir / "leg-baseline-L0.json", _jsonable(leg_levels[0]))
        _write_json(case_dir / "leg-baseline-L2.json", _jsonable(leg_levels[-1]))
        _write_json(case_dir / "base.json", _jsonable(built))
        _write_json(case_dir / "baseline-L0.json", _jsonable(baseline_l0))
        _write_json(case_dir / "baseline-L2.json", _jsonable(baseline_l2))
        _write_json(case_dir / "rest.json", _jsonable(baseline_l2))
        base_reloaded, _ = _read_json(case_dir / "base.json")
        baseline_l0_reloaded, _ = _read_json(case_dir / "baseline-L0.json")
        baseline_l2_reloaded, _ = _read_json(case_dir / "baseline-L2.json")
        rest_reloaded, _ = _read_json(case_dir / "rest.json")
        result.update({"rest": rest_reloaded, "base": base_reloaded,
                       "baseline_L0": baseline_l0_reloaded,
                       "baseline_L2": baseline_l2_reloaded,
                       "bounds_inputs": [rest_reloaded],
                       "materialization": "source-rebuilt" if source_comparison is not None else "legacy-cached-root",
                       "body_materialized": body_mode,
                       "foot_materialized": foot_enabled,
                       "tail_materialized": tail_enabled,
                       "source_rebuild": source_comparison})
        checks = modules.get("checks")
        checks_ready = checks is not None and callable(getattr(checks, "check_mesh", None))
        if checks is None:
            result["checks"] = {"status": "pending", "reason": "checks module is not captured"}
        elif checks_ready:
            report = checks.check_mesh(rest_reloaded, protocol)
            _write_json(case_dir / "mesh-checks.json", _jsonable(report))
            result["checks"] = {"mesh": _jsonable(report), "mesh_pass": _report_pass(report)}
        else:
            result["checks"] = {"status": "pending", "reason": "checks.check_mesh is not ready"}
        if rest_only:
            result.update({"status": "internal-diagnostic", "full_pass": False,
                           "reason": "--rest-only stops before binding and is not a full pass"})
            return result
        binding_module = modules.get("binding")
        if binding_module is None:
            result.update({"status": "pending", "reason": "binding API is not captured", "full_pass": False})
            return result
        stage = "binding"
        binding = body_binding if body_mode else binding_module.bind(
            base_reloaded, rest_reloaded, root, prior_binding, leg_inputs)
        _write_json(case_dir / "binding.json", _jsonable(binding))
        binding_reloaded, _ = _read_json(case_dir / "binding.json")
        binding_check_ready = checks is not None and callable(getattr(checks, "check_binding", None))
        if binding_check_ready:
            report = checks.check_binding(base_reloaded, rest_reloaded, binding_reloaded,
                                          root, prior_binding, leg_inputs, protocol)
            _write_json(case_dir / "binding-checks.json", _jsonable(report))
            result["checks"]["binding"] = _jsonable(report)
            result["checks"]["binding_pass"] = _report_pass(report)
        else:
            result["checks"]["binding"] = {"status": "pending", "reason": "checks.check_binding is not ready"}
        poses = _protocol_poses(protocol)
        pose_points = []
        source_comparison_pass = True
        if source_comparison is not None:
            if source_comparison.get("required_for_full_pass") is False:
                source_comparison_pass = True
            else:
                source_comparison_pass = bool(
                    source_comparison.get("root_L0_exact") and
                    source_comparison.get("root_L2_exact") and
                    all(source_comparison.get("root_binding_exact", {}).values())
                )
        all_pass = (result.get("checks", {}).get("mesh_pass", False) is True and
                    result.get("checks", {}).get("binding_pass", False) is True and
                    source_comparison_pass)
        checks_complete = checks_ready and binding_check_ready
        for pose in poses:
            stage = f"pose:{pose['id']}"
            pose_dir = case_dir / "poses" / str(pose["id"])
            pose_dir.mkdir(parents=True, exist_ok=True)
            posed = binding_module.pose(rest_reloaded, binding_reloaded, pose["angles"])
            points = binding_module.joint_points(binding_reloaded, pose["angles"])
            _write_json(pose_dir / "mesh.json", _jsonable(posed))
            _write_json(pose_dir / "joints.json", _jsonable(points))
            posed_reloaded, _ = _read_json(pose_dir / "mesh.json")
            pose_reloaded, _ = _read_json(pose_dir / "joints.json")
            pose_record: dict[str, Any] = {"id": pose["id"], "angles": pose["angles"], "mesh": posed_reloaded,
                                           "joints": pose_reloaded}
            if checks is not None and callable(getattr(checks, "check_pose", None)):
                report = checks.check_pose(rest_reloaded, posed_reloaded, binding_reloaded,
                                           pose["angles"], protocol, leg_inputs)
                _write_json(pose_dir / "checks.json", _jsonable(report))
                pose_record["checks"] = _jsonable(report)
                pose_pass = _report_pass(report)
                all_pass = all_pass and pose_pass
            else:
                pose_record["checks"] = {"status": "pending", "reason": "checks.check_pose is not ready"}
                all_pass = False
                checks_complete = False
            result["poses"].append(pose_record)
            # Add each successfully materialized pose immediately so a later
            # case/pose exception cannot shrink the shared render bounds.
            result["bounds_inputs"].append(posed_reloaded)
            pose_points.append(pose_reloaded)
        if checks is not None and callable(getattr(checks, "compare_root", None)):
            stage = "root-comparison"
            report = checks.compare_root(root, baseline_l0_reloaded, prior_rest, baseline_l2_reloaded)
            _write_json(case_dir / "root-comparison.json", _jsonable(report))
            result["root_comparison"] = _jsonable(report)
            all_pass = all_pass and _report_pass(report)
        else:
            result["root_comparison"] = {"status": "pending", "reason": "checks.compare_root is not ready"}
            all_pass = False
            checks_complete = False
        stage = "perturbations"
        perturbation_status = _perturbation_status(protocol)
        perturbation_module = modules.get("perturbations")
        perturbation_result: dict[str, Any] | None = None
        if perturbation_status["status"] == "not-declared":
            result["perturbations"] = perturbation_status
            perturbation_pass = True
        elif perturbation_module is None or not callable(getattr(perturbation_module, "run_case", None)):
            result["perturbations"] = {
                **perturbation_status,
                "reason": "perturbations.run_case is not captured",
            }
            perturbation_pass = False
            checks_complete = False
        else:
            perturbation_baseline_binding = binding_reloaded
            leg_only_perturbations = body_mode or foot_enabled
            if leg_only_perturbations:
                # The existing perturbation hook is explicitly leg-only.  Run
                # it against the saved intermediate leg baseline only, and
                # keep it out of body/foot acceptance accounting.
                perturbation_baseline_binding = binding_module.bind(
                    leg_levels[0], leg_levels[-1], root, prior_binding, leg_inputs)
            perturbation_result = perturbation_module.run_case(
                root, prior_rest, prior_binding, leg_inputs,
                leg_levels[0] if leg_only_perturbations else baseline_l0_reloaded,
                leg_levels[-1] if leg_only_perturbations else baseline_l2_reloaded,
                perturbation_baseline_binding,
                protocol, construction, binding_module)
            perturbation_result = _jsonable(perturbation_result)
            if leg_only_perturbations:
                perturbation_result = {
                    **perturbation_result,
                    "status": "leg-only",
                    "coverage": "leg-baseline-only",
                    "foot_coverage": "not-run",
                    "leg_baseline_result": perturbation_result,
                }
            _write_json(case_dir / "perturbations.json", perturbation_result)
            result["perturbations"] = perturbation_result
            result["perturbation_meshes"] = _save_perturbation_evidence(case_dir, perturbation_result)
            expected_ids = perturbation_status.get("declared_ids", [])
            perturbation_pass = (not foot_enabled and
                                 _perturbation_result_ready(perturbation_result, expected_ids))
        complete = all_pass and checks_complete and perturbation_pass
        perturbation_rejected = (isinstance(perturbation_result, Mapping)
                                and perturbation_result.get("status") == "failed")
        result["status"] = ("technical-pass" if complete else
                             "pending" if not checks_complete or
                             (not perturbation_pass and not perturbation_rejected) else
                             "rejected")
        result["full_pass"] = complete
        result["overlay_points"] = pose_points
        return result
    except Exception as exc:
        result["status"] = "exception"
        result["full_pass"] = False
        blocker = {"case": case_id, "stage": stage, "type": type(exc).__name__, "message": str(exc)}
        result["exceptions"].append({"type": type(exc).__name__, "message": str(exc), "stage": stage})
        if (stage != "perturbations" and _perturbation_status(protocol)["status"] not in ("not-declared", "invalid")
                and "perturbations" not in result
                and modules.get("perturbations") is not None
                and callable(getattr(modules["perturbations"], "run_case", None))):
            result["perturbations"] = {
                "status": "blocked-by-earlier-error", "execution": "not-run", "blocker": blocker,
            }
        return result


def run(snapshot: str | os.PathLike[str], output: str | os.PathLike[str],
        rest_only: bool = False, body_config: str | None = None) -> dict[str, Any]:
    """Execute captured collaborators once into an absent output directory."""
    snapshot_path = _canonical(snapshot, "snapshot")
    manifest = verify(snapshot_path)
    captured_runner = snapshot_path / SNAPSHOT_SOURCE / "runner.py"
    if Path(__file__).resolve() != captured_runner.resolve():
        _fail("run must execute from the captured new-source runner")
    output_path = _canonical(output, "output")
    if output_path.exists() or output_path.is_symlink():
        _fail(f"output must be absent: {output_path}")
    if not output_path.parent.is_dir() or output_path.parent.is_symlink():
        _fail("output parent must be an existing regular directory")
    protocol, protocol_raw = _read_json(_snapshot_path(snapshot_path, str(SNAPSHOT_SOURCE / "protocol.json")))
    inputs, inputs_raw = _read_json(_snapshot_path(snapshot_path, str(SNAPSHOT_SOURCE / "inputs.json")))
    if not isinstance(protocol, Mapping) or not isinstance(inputs, Mapping):
        _fail("captured protocol and inputs must be objects")
    cases = _load_case_inputs(snapshot_path, manifest, inputs)
    modules = _load_collaborators(snapshot_path, manifest, rest_only)
    body_source_mode = bool(
        not rest_only and modules.get("body_assembly") is not None
        and any(isinstance(item.get("values", {}).get("original_case"), Mapping)
                for item in cases)
    )
    if body_config is not None and not body_source_mode:
        _fail("--body-config requires source-driven body mode and is incompatible with --rest-only")
    selected_body_config = (_load_body_config(snapshot_path, manifest, body_config)
                            if body_config is not None else None)
    case_protocol = (_body_provisional_protocol(
        protocol,
        has_arms=modules.get("arm_inputs") is not None,
        has_head=(modules.get("head_inputs") is not None or
                  modules.get("head_refinement_inputs") is not None),
    ) if body_source_mode else protocol)
    output_path.mkdir()
    _write_json(output_path / "protocol.json", protocol)
    if body_source_mode:
        _write_json(output_path / "effective-body-protocol.json", _jsonable(case_protocol))
    (output_path / "inputs.json").write_bytes(inputs_raw)
    (output_path / "runner-source.py").write_bytes((snapshot_path / SNAPSHOT_SOURCE / "runner.py").read_bytes())
    results = []
    for index, case in enumerate(cases):
        results.append(_case_run(case, case_protocol, modules,
                                 output_path / "cases" / f"case-{index:02d}-{case['id']}",
                                 rest_only, selected_body_config))
    all_meshes = _render_bounds_inputs(results)
    bounds = _bounds(all_meshes) if all_meshes else None
    render = modules.get("render")
    render_errors = []
    if render is not None and bounds is not None:
        for case_index, result in enumerate(results):
            case_dir = output_path / "cases" / f"case-{case_index:02d}-{result['id']}"
            meshes = [result.get("rest")] + [row.get("mesh") for row in result.get("poses", [])]
            meshes = [mesh for mesh in meshes if isinstance(mesh, Mapping)]
            result["renders"] = []
            for mesh_index, mesh in enumerate(meshes):
                status = _visual_status(result, rest_only)
                overlays = []
                if mesh_index > 0 and mesh_index - 1 < len(result.get("overlay_points", [])):
                    overlays = _overlays(result["overlay_points"][mesh_index - 1])
                filename = "rest.png" if mesh_index == 0 else f"pose-{mesh_index:02d}.png"
                record = _render_one(render, mesh, case_dir / filename,
                                     str(result["id"]), status, bounds, overlays)
                result["renders"].append(record)
                if record.get("status") == "exception":
                    render_errors.append({"case": result["id"], "error": record["exception"]})
            for perturbation_mesh in result.get("perturbation_meshes", []):
                if not isinstance(perturbation_mesh, Mapping) or not isinstance(perturbation_mesh.get("mesh"), Mapping):
                    continue
                perturbation_id = _safe_token(perturbation_mesh.get("perturbation_id", "unknown"))
                name = _safe_token(perturbation_mesh.get("name", "mesh"))
                perturbation_path = case_dir / "perturbations" / perturbation_id / f"{name}.png"
                record = _render_one(render, perturbation_mesh["mesh"], perturbation_path,
                                     f"{result['id']} perturbation {perturbation_id} {name}",
                                     _visual_status(result, rest_only, perturbation=True), bounds, [])
                result.setdefault("perturbation_renders", []).append({
                    "perturbation_id": perturbation_id, "name": name, "record": record,
                })
                if record.get("status") == "exception":
                    render_errors.append({"case": result["id"],
                                          "perturbation": perturbation_id,
                                          "error": record["exception"]})
    post_run_verification: dict[str, Any] = {
        "status": "verified",
        "scope": "captured source/input, frozen transition/renderer/collision-core, and source adapters",
    }
    try:
        verify(snapshot_path)
    except Exception as exc:
        post_run_verification = {
            "status": "failed",
            "scope": "captured source/input, frozen transition/renderer/collision-core, and source adapters",
            "type": type(exc).__name__,
            "message": str(exc),
        }
    perturbation_api_available = bool(
        modules.get("perturbations") is not None
        and callable(getattr(modules["perturbations"], "run_case", None))
    )
    perturbations = _aggregate_perturbations(protocol, results, perturbation_api_available)
    overall_status = ("error" if any(item.get("status") == "exception" for item in results) or render_errors
                      or post_run_verification["status"] == "failed" else
                       "internal-diagnostic" if rest_only else
                       "rejected" if any(item.get("status") == "rejected" for item in results) else
                       "pending" if any(item.get("status") == "pending" for item in results) else
                       "pending" if perturbations["status"] in ("not-implemented", "unavailable",
                                                                  "blocked-by-earlier-error") else
                       "rejected" if perturbations["status"] == "failed" else
                       "complete")
    readiness = _readiness(modules, protocol)
    report = {
        "schema": "creature-kernel.connected-leg-assembly-run.v1",
        "status": overall_status,
        "full_pass": (post_run_verification["status"] == "verified" and
                      not rest_only and perturbations["status"] in ("not-declared", "pass") and
                      all(item.get("status") == "technical-pass" for item in results)),
        "rest_only": rest_only,
        "body_config": body_config,
        "body_evidence": (
            {
                "label": selected_body_config.get("evidence_label"),
                "acceptance": selected_body_config.get("acceptance"),
                "status": selected_body_config.get("status"),
            }
            if selected_body_config is not None else None
        ),
        "case_count": len(results), "cases": results, "shared_bounds": bounds,
        "render_errors": render_errors,
        "post_run_verification": post_run_verification,
        "perturbations": perturbations,
        "readiness": readiness,
        "body_provisional_protocol": (
            _jsonable(case_protocol.get("body_provisional_evidence"))
            if body_source_mode else None
        ),
        "effective_body_protocol_artifact": (
            "effective-body-protocol.json" if body_source_mode else None
        ),
        "numerical_checks": "pending" if rest_only or modules.get("checks") is None else "captured",
        "pose_checks": "pending" if rest_only or modules.get("checks") is None else "captured",
        "inputs_sha256": _sha256_bytes(inputs_raw), "protocol_sha256": _sha256_bytes(protocol_raw),
        "limitations": ["Visual acceptance remains pending and is parent-owned.", "No publication, browser, or window launch is performed."],
    }
    _write_json(output_path / "run-report.json", _jsonable(report))
    files = []
    for path in sorted(output_path.rglob("*"), key=lambda item: item.relative_to(output_path).as_posix().encode("utf-8")):
        if path.is_file() and path.name != "artifact-manifest.json":
            files.append({"path": path.relative_to(output_path).as_posix(), **_identity(path)})
    _write_json(output_path / "artifact-manifest.json", {"schema": "creature-kernel.connected-leg-assembly-artifacts.v1", "files": files})
    return report


def _main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Connected-leg evidence runner")
    subparsers = parser.add_subparsers(dest="command", required=True)
    prepare_parser = subparsers.add_parser("prepare")
    prepare_parser.add_argument("--snapshot", required=True)
    prepare_parser.add_argument("--files", nargs="*")
    prepare_parser.add_argument("--rest-only", action="store_true")
    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("--snapshot", required=True)
    run_parser.add_argument("--output", required=True)
    run_parser.add_argument("--rest-only", action="store_true")
    run_parser.add_argument("--body-config")
    verify_parser = subparsers.add_parser("verify")
    verify_parser.add_argument("--snapshot", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "prepare":
            prepare(args.snapshot, args.files, args.rest_only)
        elif args.command == "verify":
            verify(args.snapshot)
        else:
            report = run(args.snapshot, args.output, args.rest_only, args.body_config)
            if report.get("status") in ("error", "rejected"):
                return 1
    except Exception as exc:
        print(f"runner.py: error: {exc}", file=sys.stderr, flush=True)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
