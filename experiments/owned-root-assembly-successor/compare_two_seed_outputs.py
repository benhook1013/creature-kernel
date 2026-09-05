"""Private, fail-closed comparator for two sealed successor seed bundles."""
from __future__ import annotations
import importlib, importlib.metadata, importlib.util, locale, os, platform, shutil, stat, struct, sys, sysconfig, tempfile
from pathlib import Path
PACKAGE = Path(__file__).resolve().parent; REPO = PACKAGE.parents[1]
sys.path.insert(0, str(PACKAGE))
import artifact_serialization as artifacts  # noqa: E402
EXPECTED_CONTRACT_SHA256, EXPECTED_SOURCE_SHA256, EXPECTED_PROFILE_SHA256 = "3122f0db2235754ed782bd38a88c4d7ad7cc7edbf635d147194f1e93f8556490", "82269e843555ff1aad3c66399e3fcaeb11bbee81d72b69d15765ea9c4e7aff14", "a5fba6643d0031bac83c08e9093e11fd7945806963509fa939865866112d9640"
CONTRACT_ROLE, SIDECAR_ROLE, SOURCE_ROLE = "experiments/owned-root-assembly-successor/design-contract.md", "experiments/owned-root-assembly-successor/design-contract.sha256", "examples/body-documents/stylized-digitigrade-biped-authored-form.json"
PROFILE_ROLE, CURRENT_LAUNCHER_ROLE, REQUIREMENTS_ROLE = "experiments/current-form-surface-preview/structural_profile_candidates.json", "experiments/current-form-surface-preview/surface_preview_launcher.sh", "experiments/current-form-surface-preview/requirements.txt"
BUILDER_ROLE, COMPARATOR_ROLE = "experiments/owned-root-assembly-successor/build_owned_root.py", "experiments/owned-root-assembly-successor/compare_two_seed_outputs.py"
IMPLEMENTATION_ROLES = tuple(sorted(("experiments/owned-root-assembly-successor/" + role for role in "build_owned_root.py prepared_projection.py owned_root_surface.py mesh_correctness.py render_export.py owned_root_launcher.sh compare_two_seed_outputs.py artifact_serialization.py anatomy_gates.py chart_lineage.py tests/test_build_owned_root.py tests/test_prepared_projection.py tests/test_owned_root_surface.py tests/test_mesh_correctness.py tests/test_render_export.py".split()), key=lambda value: value.encode("utf-8")))
ROLES = tuple("surface-level-0.ply surface-level-1.ply surface-level-2.ply perturb-left-r_y.ply perturb-right-r_y.ply perturb-lower_pelvis-L_y.ply perturb-left-r_x.ply perturb-lower_pelvis-C_z.ply perturb-right-r_x.ply perturb-lower_pelvis-R_x.ply perturb-left-r_z.ply perturb-right-r_z.ply perturb-lower_pelvis-R_f.ply perturb-lower_pelvis-R_b.ply perturb-left-thigh_start_x.ply perturb-left-thigh_start_y.ply perturb-left-thigh_start_z.ply perturb-right-thigh_start_x.ply perturb-right-thigh_start_y.ply perturb-right-thigh_start_z.ply perturb-neck_collar-C_y.ply perturb-neck_collar-rL.ply perturb-neck_upper-C_y.ply perturb-neck_upper-rL.ply perturb-left-axilla_x.ply perturb-left-axilla_y.ply perturb-right-axilla_x.ply perturb-right-axilla_y.ply perturb-left-peak_y.ply perturb-right-peak_y.ply perturb-left-start_lateral.ply perturb-right-start_lateral.ply perturb-left-start_up.ply perturb-right-start_up.ply perturb-left-shoulder_depth.ply perturb-right-shoulder_depth.ply direct.png lineage.png input-manifest.json coordinate-manifest.json gate-manifest.json causality-manifest.json render-manifest.json stable-manifest.json prepared-input.json report.json report.sha256".split())
STABLE_ROLES = tuple(sorted(set(ROLES) - {"report.json", "report.sha256"}, key=lambda value: value.encode("utf-8")))
READ_FLAGS = os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW | os.O_CLOEXEC
class ComparatorError(ValueError): pass
def _need(condition: bool, message: str) -> None:
    if not condition: raise ComparatorError(message)
def _bounded(value: object, label: str, limit: int = 128) -> str:
    _need(type(value) is str and len(value.encode("utf-8")) <= limit, f"{label} is not a bounded runtime string"); return value
def _json(path: Path) -> tuple[dict, bytes]:
    raw = artifacts.read_regular_file(path, max_bytes=2 * 1024 * 1024); value = artifacts.decode_canonical_json(raw); _need(isinstance(value, dict), f"{path} is not a JSON object"); return value, raw
def _record(path: Path, role: str, cap: int = 4 * 1024 * 1024) -> dict: return artifacts.regular_file_record(path, role, max_bytes=cap)
def _implementation_nodes() -> list[tuple[str, os.stat_result]]:
    result, flags = [], os.O_RDONLY | os.O_DIRECTORY | os.O_NONBLOCK | os.O_NOFOLLOW | os.O_CLOEXEC
    def visit(directory: int, prefix: str) -> None:
        with os.scandir(directory) as entries:
            for entry in entries:
                info = entry.stat(follow_symlinks=False); role = f"{prefix}/{entry.name}"
                if entry.name.endswith((".py", ".sh")): result.append((role, info))
                if stat.S_ISDIR(info.st_mode):
                    child = os.open(entry.name, flags, dir_fd=directory)
                    try: artifacts._require_same_stat(info, os.fstat(child), "implementation directory changed during admission"); visit(child, role)
                    finally: os.close(child)
    root = artifacts._open_directory(PACKAGE)
    try: visit(root, PACKAGE.relative_to(REPO).as_posix())
    finally: os.close(root)
    return sorted(result, key=lambda item: item[0].encode("utf-8"))
def _implementation_record(role: str, admitted: os.stat_result) -> dict:
    parts = Path(role).relative_to(PACKAGE.relative_to(REPO)).parts; parent = artifacts._open_directory(PACKAGE.joinpath(*parts[:-1]))
    try:
        descriptor = os.open(parts[-1], READ_FLAGS, dir_fd=parent)
        try:
            opened = os.fstat(descriptor); artifacts._require_regular(opened, role); artifacts._require_same_stat(admitted, opened, f"{role} changed after allowlist scan")
            readings = [artifacts._read_stable_once(descriptor, opened, 4 * 1024 * 1024) for _ in range(2)]
            artifacts._require_same_stat(opened, os.stat(parts[-1], dir_fd=parent, follow_symlinks=False), f"{role} changed while reading")
            if readings[0] != readings[1] or len(readings[1]) != opened.st_size: raise ComparatorError(f"{role} changed while reading")
        finally: os.close(descriptor)
    finally: os.close(parent)
    return {"role_path": role, "bytes": len(readings[1]), "sha256": artifacts.sha256_bytes(readings[1])}
def _implementation_files() -> list[dict]:
    before = _implementation_nodes(); found = tuple(role for role, _ in before)
    _need(not any(not stat.S_ISREG(info.st_mode) for _, info in before), "package implementation allowlist contains a non-regular .py/.sh node"); _need(found == IMPLEMENTATION_ROLES, "package implementation source does not match the exact 15-file allowlist")
    records = [_implementation_record(role, info) for role, info in before]; after = _implementation_nodes()
    _need(len(after) == len(before) and not any(left[0] != right[0] or not artifacts._same_stat(left[1], right[1]) for left, right in zip(before, after)), "package implementation allowlist changed while reading"); return records
def _unchanged(path: Path, role: str, expected: dict, cap: int = 4 * 1024 * 1024) -> None:
    _need(_record(path, role, cap) == expected, f"{role} changed after inventory")
def _bundle(root: Path) -> dict:
    rows = artifacts.closed_inventory(root, ROLES, max_file_bytes=8 * 1024 * 1024)
    _need(not any(row["bytes"] > (8 if row["role_path"] == "causality-manifest.json" else 2) * 1024 * 1024 for row in rows), "seed bundle exceeds its exact artifact size caps"); return {row["role_path"]: row for row in rows}
def _api(module: object, name: str):
    function = getattr(module, name, None); _need(callable(function), f"missing future builder API: build_owned_root.{name}()"); return function
def _runtime(launcher: dict, requirements: dict) -> tuple[dict, bytes, str]:
    _need((platform.python_implementation(), platform.python_version(), platform.system(), getattr(sys.implementation, "cache_tag", None)) == ("CPython", "3.10.12", "Linux", "cpython-310"), "runtime must be CPython 3.10.12 on Linux with cache tag cpython-310")
    direct = (("numpy", "2.2.6"), ("scikit-image", "0.25.2"), ("pillow", "11.1.0"))
    resolved = (("imageio", "2.37.4"), ("lazy-loader", "0.5"), ("networkx", "3.4.2"), ("numpy", "2.2.6"), ("packaging", "26.3"), ("pillow", "11.1.0"), ("scikit-image", "0.25.2"), ("scipy", "1.15.3"), ("tifffile", "2025.5.10"))
    for name, expected in (*direct, *resolved):
        try: observed = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError as exc: raise ComparatorError(f"runtime distribution is missing: {name}") from exc
        _need(observed == expected, f"runtime distribution drift: {name}=={observed}")
    builtins = []
    for name in ("math", "zlib"):
        module, spec = importlib.import_module(name), importlib.util.find_spec(name)
        _need(getattr(module, "__file__", None) is None and spec is not None and spec.origin == "built-in", f"{name} is not the required built-in module")
        versions = (None, None) if name == "math" else (_bounded(module.ZLIB_VERSION, "zlib compile version"), _bounded(module.ZLIB_RUNTIME_VERSION, "zlib runtime version"))
        builtins.append({"module_name": name, "__file__": None, "find_spec_origin": "built-in", "compile_version": versions[0], "runtime_version": versions[1]})
    build, compiler = _bounded(" ".join(platform.python_build()), "python.build"), _bounded(platform.python_compiler(), "python.compiler")
    python = {"implementation": "CPython", "version": "3.10.12", "build": build, "compiler": compiler, "cache_tag": "cpython-310", "abiflags": _bounded(sys.abiflags, "python.abiflags"), "soabi": _bounded(sysconfig.get_config_var("SOABI"), "python.soabi")}
    libc_name, libc_version = platform.libc_ver()
    platform_value = {"system": platform.system(), "release": platform.release(), "version": platform.version(), "machine": platform.machine(), "pointer_bits": 8 * struct.calcsize("P"), "byteorder": sys.byteorder, "libc_name": libc_name, "libc_version": libc_version}
    for key in ("system", "release", "version", "machine", "libc_name", "libc_version"): platform_value[key] = _bounded(platform_value[key], f"platform.{key}")
    _need(platform_value["system"] == "Linux" and platform_value["byteorder"] in ("little", "big") and platform_value["pointer_bits"] > 0, "runtime platform is not admitted")
    locale_value = {"active": _bounded(locale.setlocale(locale.LC_ALL, None), "locale.active", 512), "preferred_encoding": _bounded(locale.getpreferredencoding(False), "locale.preferred_encoding", 512)}
    value = {"schema": "owned-root-assembly-successor-runtime.v2", "python": python, "platform": platform_value, "locale": locale_value, "managed_launcher": launcher, "requirements": requirements, "direct_distributions": [{"name": n, "version": v} for n, v in direct], "resolved_distributions": [{"name": n, "version": v} for n, v in resolved], "builtin_modules": builtins}
    raw = artifacts.canonical_json_bytes(value)
    _need(len(raw) <= 64 * 1024, "runtime fingerprint exceeds its 64 KiB cap"); return value, raw, artifacts.sha256_bytes(raw)
def _static() -> dict:
    _need(os.environ.get("PYTHONHASHSEED") == "0", "comparator requires literal PYTHONHASHSEED=0")
    contract = _record(REPO / CONTRACT_ROLE, CONTRACT_ROLE)
    _need(contract["sha256"] == EXPECTED_CONTRACT_SHA256, "design-contract SHA-256 does not match the independent literal")
    artifacts.validate_contract_sidecar(artifacts.read_regular_file(REPO / SIDECAR_ROLE), EXPECTED_CONTRACT_SHA256)
    source, profile = _record(REPO / SOURCE_ROLE, SOURCE_ROLE), _record(REPO / PROFILE_ROLE, PROFILE_ROLE)
    _need((source["sha256"], profile["sha256"]) == (EXPECTED_SOURCE_SHA256, EXPECTED_PROFILE_SHA256), "fixed source or profile identity drifted")
    launcher, requirements = _record(REPO / CURRENT_LAUNCHER_ROLE, CURRENT_LAUNCHER_ROLE), _record(REPO / REQUIREMENTS_ROLE, REQUIREMENTS_ROLE)
    shell_literal = f'EXPECTED_CONTRACT_SHA256="{EXPECTED_CONTRACT_SHA256}"'.encode("ascii"); python_literal = f'EXPECTED_CONTRACT_SHA256 = "{EXPECTED_CONTRACT_SHA256}"'.encode("ascii")
    _need(artifacts.read_regular_file(PACKAGE / "owned_root_launcher.sh").count(shell_literal) == 1 and artifacts.read_regular_file(PACKAGE / "build_owned_root.py").count(python_literal) == 1, "the two required code literals do not match the contract identity"); _need(artifacts.read_regular_file(REPO / REQUIREMENTS_ROLE) == b"numpy==2.2.6\nscikit-image==0.25.2\nPillow==11.1.0\n", "requirements are not the exact pinned file")
    implementation = _implementation_files(); runtime, runtime_bytes, runtime_sha = _runtime(launcher, requirements)
    return {"contract": contract, "source": source, "profile_table": profile, "runtime": runtime, "runtime_bytes": runtime_bytes, "runtime_fingerprint_sha256": runtime_sha, "implementation_files": implementation}
def _args() -> tuple[Path, Path, Path, Path]:
    _need(len(sys.argv) == 7 and sys.argv[3] == "--test-receipt" and sys.argv[5] == "--output", "usage: compare_two_seed_outputs.py SEED17 SEED29 --test-receipt RECEIPT --output COMPARISON")
    raw_values = (sys.argv[1], sys.argv[2], sys.argv[4], sys.argv[6])
    _need(not any(not raw.startswith("/") or any(part in ("", ".", "..") for part in raw.split("/")[1:]) for raw in raw_values), "all comparator paths must be canonical absolute paths without empty or dot components")
    values = tuple(Path(raw) for raw in raw_values); seed17, seed29, receipt, output = values
    _need((seed17.name, seed29.name, receipt.name, output.name) == ("seed-17", "seed-29", "managed-test-receipt.json", "comparison"), "comparator paths do not use the fixed role names"); _need(seed17.parent == seed29.parent == receipt.parent == output.parent, "seed bundles, receipt, and comparison must be invocation-owned siblings"); _need(not any(not os.path.lexists(path) for path in (seed17, seed29, receipt)) and not os.path.lexists(output), "seed bundles and receipt must exist, while comparison must be absent")
    return values
def _admit_receipt(path: Path) -> tuple:
    parent = artifacts._open_directory(path.parent)
    try:
        parent_state = os.fstat(parent); descriptor = os.open(path.name, READ_FLAGS, dir_fd=parent)
        try:
            raw, receipt_state = artifacts._read_stable_fd(descriptor, 2 * 1024 * 1024); artifacts._require_same_stat(receipt_state, os.stat(path.name, dir_fd=parent, follow_symlinks=False), "managed-test receipt changed during admission")
            value = artifacts.decode_canonical_json(raw); _need(isinstance(value, dict), "managed-test receipt is not an object"); return value, raw, parent, descriptor, parent_state, receipt_state
        except Exception: os.close(descriptor); raise
    except Exception: os.close(parent); raise
def _remove_receipt(path: Path, raw: bytes, parent: int, descriptor: int, parent_state: os.stat_result, receipt_state: os.stat_result, stage: Path) -> None:
    current_parent = artifacts._open_directory(path.parent)
    try:
        current_parent_state = os.fstat(current_parent); _need(os.path.samestat(parent_state, current_parent_state) and all(getattr(parent_state, field) == getattr(current_parent_state, field) for field in ("st_mode", "st_uid", "st_gid", "st_rdev")), "managed-test receipt parent identity changed before removal")
    finally: os.close(current_parent)
    observed, observed_state = artifacts._read_stable_fd(descriptor, 2 * 1024 * 1024); _need(observed == raw, "managed-test receipt bytes changed before removal"); artifacts._require_same_stat(receipt_state, observed_state, "managed-test receipt identity changed before removal"); artifacts._require_same_stat(receipt_state, os.stat(path.name, dir_fd=parent, follow_symlinks=False), "managed-test receipt pathname was substituted")
    stage_fd, tomb = artifacts._open_directory(stage), ".managed-test-receipt.remove"
    try:
        os.rename(path.name, tomb, src_dir_fd=parent, dst_dir_fd=stage_fd)
        try: os.stat(path.name, dir_fd=parent, follow_symlinks=False); raise ComparatorError("managed-test receipt pathname remained after removal move")
        except FileNotFoundError: pass
        _need(artifacts._same_published_state(receipt_state, os.stat(tomb, dir_fd=stage_fd, follow_symlinks=False)), "managed-test receipt pathname was substituted during removal"); final, final_state = artifacts._read_stable_fd(descriptor, 2 * 1024 * 1024); _need(final == raw and artifacts._same_published_state(receipt_state, final_state), "managed-test receipt bytes or identity changed during removal"); os.unlink(tomb, dir_fd=stage_fd)
        try: os.stat(tomb, dir_fd=stage_fd, follow_symlinks=False); raise ComparatorError("managed-test receipt tomb remained after removal")
        except FileNotFoundError: pass
    finally: os.close(stage_fd)
def _receipt(value: dict, raw: bytes, path: Path, identity: dict, builder: object) -> dict:
    keys = {"schema", "outcome", "literal_invocation", "contract_sha256", "runtime_fingerprint_sha256", "implementation_files", "executed_test_ids", "required_test_ids", "results"}; required = ["test_mesh_correctness.ProductionIntersectionFixtureTests.test_contract_fixture_matrix", "test_owned_root_surface.ProductionAxillaryFixtureTests.test_contract_fixture_matrix"]; executed, results = value.get("executed_test_ids"), value.get("results")
    _need(set(value) == keys and value.get("schema") == "owned-root-assembly-successor-managed-test-receipt.v1" and value.get("outcome") == "success" and value.get("contract_sha256") == EXPECTED_CONTRACT_SHA256 and value.get("runtime_fingerprint_sha256") == identity["runtime_fingerprint_sha256"] and value.get("implementation_files") == identity["implementation_files"] and isinstance(executed, list) and bool(executed) and all(type(item) is str for item in executed) and executed == sorted(set(executed), key=lambda item: item.encode("utf-8")) and value.get("required_test_ids") == required and all(executed.count(item) == 1 for item in required), "managed-test receipt identity or test inventory is invalid")
    expected_invocation = {"environment": ["PYTHONHASHSEED=0"], "argv": [BUILDER_ROLE, "--internal-managed-tests", "--receipt", str(path)]}
    _need(value.get("literal_invocation") == expected_invocation, "managed-test receipt invocation is not exact")
    expected_results = {"tests_run": len(executed), "failures": 0, "errors": 0, "skipped": 0, "expected_failures": 0, "unexpected_successes": 0}
    _need(isinstance(results, dict) and set(results) == set(expected_results) and all(type(results[name]) is int for name in results) and results == expected_results, "managed-test receipt result counts are not exact"); _api(builder, "validate_managed_test_receipt")(receipt=value, raw=raw, identity=identity); return value
def _sidecar(raw: bytes, payload: bytes, name: str) -> None:
    _need(raw == f"{artifacts.sha256_bytes(payload)}  {name}\n".encode("ascii"), f"{name} sidecar is not the exact LF-terminated hash line")
def _admit_report_sidecar(root: Path, records: dict) -> None:
    path = root / "report.sha256"; raw = artifacts.read_regular_file(path, max_bytes=128)
    _need(len(raw) == 78 and raw[64:] == b"  report.json\n" and not any(byte not in b"0123456789abcdef" for byte in raw[:64]), f"{path} does not have the required lexical grammar"); _unchanged(path, "report.sha256", records["report.sha256"])
def _stable(root: Path, records: dict, identity: dict) -> dict:
    path = root / "stable-manifest.json"; value, _ = _json(path); _unchanged(path, "stable-manifest.json", records["stable-manifest.json"])
    keys = {"schema", "contract_sha256", "recipe_id", "runtime", "implementation_files", "input_manifest", "coordinate_manifest", "gate_manifest", "causality_manifest", "render_manifest", "artifact_hashes"}
    _need(set(value) == keys and value.get("schema") == "owned-root-assembly-successor-stable-manifest.v1" and value.get("contract_sha256") == EXPECTED_CONTRACT_SHA256 and value.get("implementation_files") == identity["implementation_files"] and artifacts.canonical_json_bytes(value.get("runtime")) == identity["runtime_bytes"], "stable manifest has a mismatched identity"); return value
def _report(root: Path, seed: int, records: dict, identity: dict, builder: object, stable: dict) -> None:
    report_path, sidecar_path = root / "report.json", root / "report.sha256"; payload = artifacts.read_regular_file(report_path, max_bytes=2 * 1024 * 1024); value = artifacts.decode_canonical_json(payload)
    keys = {"schema", "outcome", "seed", "literal_invocation", "output_path", "staging_path", "python_executable_path", "started_utc", "finished_utc", "timings", "runtime_fingerprint_sha256", "stable_manifest", "gates"}
    _need(isinstance(value, dict) and set(value) == keys and value.get("schema") == "owned-root-assembly-successor-run-report.v1" and value.get("outcome") == "success" and value.get("seed") == seed and value.get("runtime_fingerprint_sha256") == identity["runtime_fingerprint_sha256"], f"seed-{seed} run report identity is invalid")
    _unchanged(report_path, "report.json", records["report.json"], 2 * 1024 * 1024)
    reference = {"role_path": "stable-manifest.json", "bytes": records["stable-manifest.json"]["bytes"], "sha256": records["stable-manifest.json"]["sha256"], "schema": stable["schema"]}
    _need(value.get("stable_manifest") == reference, f"seed-{seed} run report stable-manifest reference is invalid"); _api(builder, "validate_run_report")(root=root, seed=seed, report=value, identity=identity); _unchanged(sidecar_path, "report.sha256", records["report.sha256"]); _sidecar(artifacts.read_regular_file(sidecar_path, max_bytes=128), payload, "report.json")
def _outer_nodes(root: Path) -> None:
    if not root.is_absolute() or os.path.normpath(str(root)) != str(root): raise ComparatorError("outer staging root is not canonical and absolute")
    descriptor = artifacts._open_directory(root)
    try:
        with os.scandir(descriptor) as entries: rows = sorted((entry.name, entry.stat(follow_symlinks=False)) for entry in entries)
    finally: os.close(descriptor)
    if [name for name, _ in rows] != ["comparison", "seed-17", "seed-29"] or any(not stat.S_ISDIR(info.st_mode) for _, info in rows): raise ComparatorError("staging root is not the exact closed outer inventory")
def outer_publication_inventory(root: Path) -> list[dict]:
    """Semantically re-admit a completed pair and return its exact closed inventory."""
    root = Path(root); _outer_nodes(root); identity = _static(); builder = importlib.import_module("build_owned_root")
    comparison_root = root / "comparison"; comparison_rows = artifacts.closed_inventory(comparison_root, ("comparison-report.json", "comparison-report.sha256"), max_file_bytes=2 * 1024 * 1024); comparison_records = {row["role_path"]: row for row in comparison_rows}
    value, raw = _json(comparison_root / "comparison-report.json"); _unchanged(comparison_root / "comparison-report.json", "comparison-report.json", comparison_records["comparison-report.json"], 2 * 1024 * 1024)
    _sidecar(artifacts.read_regular_file(comparison_root / "comparison-report.sha256", max_bytes=128), raw, "comparison-report.json"); _unchanged(comparison_root / "comparison-report.sha256", "comparison-report.sha256", comparison_records["comparison-report.sha256"])
    keys = {"schema", "outcome", "comparator", "runtime_fingerprint_sha256", "managed_test_receipt", "seed_bundles", "stable_comparisons", "excluded_run_local_roles"}; comparator = next(row for row in identity["implementation_files"] if row["role_path"] == COMPARATOR_ROLE)
    if (set(value) != keys or value.get("schema") != "owned-root-assembly-successor-comparison-report.v1" or value.get("outcome") != "success" or value.get("comparator") != comparator or value.get("runtime_fingerprint_sha256") != identity["runtime_fingerprint_sha256"] or value.get("excluded_run_local_roles") != ["report.json", "report.sha256"]): raise ComparatorError("comparison report identity or closed schema is invalid")
    receipt = value.get("managed_test_receipt"); receipt_path = root / "managed-test-receipt.json"
    if not isinstance(receipt, dict): raise ComparatorError("comparison report managed receipt is invalid")
    _receipt(receipt, artifacts.canonical_json_bytes(receipt), receipt_path, identity, builder)
    comparisons, bundles = value.get("stable_comparisons"), value.get("seed_bundles")
    if not isinstance(comparisons, list) or [row.get("role_path") if isinstance(row, dict) else None for row in comparisons] != list(STABLE_ROLES) or not isinstance(bundles, list) or len(bundles) != 2: raise ComparatorError("comparison report inventories are not exact")
    groups = []
    for index, seed in enumerate((17, 29)):
        seed_root = root / f"seed-{seed}"; records = _bundle(seed_root); stable = _stable(seed_root, records, identity); _api(builder, "validate_seed_bundle")(root=seed_root, seed=seed, identity=identity); _report(seed_root, seed, records, identity, builder, stable)
        expected_bundle = {"seed": seed, "role_path": f"seed-{seed}", "stable_manifest": {"role_path": f"seed-{seed}/stable-manifest.json", "bytes": records["stable-manifest.json"]["bytes"], "sha256": records["stable-manifest.json"]["sha256"], "schema": stable["schema"]}, "report": {**records["report.json"], "role_path": f"seed-{seed}/report.json"}, "report_sidecar": {**records["report.sha256"], "role_path": f"seed-{seed}/report.sha256"}}
        if bundles[index] != expected_bundle or any(records[role] != comparisons[position] for position, role in enumerate(STABLE_ROLES)): raise ComparatorError(f"seed-{seed} bytes are not bound by the comparison report")
        groups.append((f"seed-{seed}", records.values()))
    if artifacts.closed_inventory(comparison_root, ("comparison-report.json", "comparison-report.sha256"), max_file_bytes=2 * 1024 * 1024) != comparison_rows: raise ComparatorError("comparison result changed during outer admission")
    groups.append(("comparison", comparison_rows)); inventory = sorted(({**record, "role_path": f"{prefix}/{record['role_path']}"} for prefix, records in groups for record in records), key=lambda record: record["role_path"].encode("utf-8"))
    if len(inventory) != 96: raise ComparatorError("outer publication inventory is not exactly 47+47+2 roles")
    return inventory
def _compare_admitted(seed17: Path, seed29: Path, receipt_path: Path, output: Path, records17: dict, records29: dict, admission: tuple) -> Path:
    receipt, receipt_raw, receipt_parent, receipt_fd, receipt_parent_state, receipt_state = admission
    # Stage 2: all fixed, runtime, seed, recipe, and receipt identities.
    identity = _static()
    builder = importlib.import_module("build_owned_root")
    receipt = _receipt(receipt, receipt_raw, receipt_path, identity, builder)
    stables = [_stable(root, records, identity) for root, records in ((seed17, records17), (seed29, records29))]
    recipe_api = getattr(builder, "_recipe", None)
    if not callable(recipe_api) or any(stable["recipe_id"] != recipe_api(identity)[1] for stable in stables):
        raise ComparatorError("seed recipe identities differ")
    # Stage 3: each stable DAG and its gates, in seed order.
    for seed, root in ((17, seed17), (29, seed29)):
        _api(builder, "validate_seed_bundle")(root=root, seed=seed, identity=identity)
    # Stage 4: exactly 45 stable roles in canonical role order.
    comparisons = []
    for role in STABLE_ROLES:
        left, right = (artifacts.read_regular_file(root / role, max_bytes=8 * 1024 * 1024) for root in (seed17, seed29))
        for data, record in ((left, records17[role]), (right, records29[role])):
            if len(data) != record["bytes"] or artifacts.sha256_bytes(data) != record["sha256"]:
                raise ComparatorError(f"stable role changed after inventory: {role}")
        if left != right:
            raise ComparatorError(f"stable role differs across seeds: {role}")
        comparisons.append({"role_path": role, "bytes": len(left), "sha256": artifacts.sha256_bytes(left)})
    # Stage 5: each complete report followed by its sidecar, in seed order.
    for seed, root, records, stable in ((17, seed17, records17, stables[0]), (29, seed29, records29, stables[1])):
        _report(root, seed, records, identity, builder, stable)
    # Stage 6: private construction, receipt removal, then atomic publication.
    bundles = [{"seed": seed, "role_path": f"seed-{seed}", "stable_manifest": {"role_path": f"seed-{seed}/stable-manifest.json", "bytes": records["stable-manifest.json"]["bytes"], "sha256": records["stable-manifest.json"]["sha256"], "schema": stable["schema"]}, "report": {**records["report.json"], "role_path": f"seed-{seed}/report.json"}, "report_sidecar": {**records["report.sha256"], "role_path": f"seed-{seed}/report.sha256"}} for seed, records, stable in ((17, records17, stables[0]), (29, records29, stables[1]))]
    report = {"schema": "owned-root-assembly-successor-comparison-report.v1", "outcome": "success", "comparator": next(row for row in identity["implementation_files"] if row["role_path"] == COMPARATOR_ROLE), "runtime_fingerprint_sha256": identity["runtime_fingerprint_sha256"], "managed_test_receipt": receipt, "seed_bundles": bundles, "stable_comparisons": comparisons, "excluded_run_local_roles": ["report.json", "report.sha256"]}
    stage = Path(tempfile.mkdtemp(prefix=f".{output.name}.stage-", dir=output.parent))
    try:
        payload = artifacts.canonical_json_bytes(report)
        artifacts.write_bytes_no_replace(stage / "comparison-report.json", payload)
        artifacts.write_bytes_no_replace(stage / "comparison-report.sha256", f"{artifacts.sha256_bytes(payload)}  comparison-report.json\n".encode("ascii"))
        _sidecar(artifacts.read_regular_file(stage / "comparison-report.sha256"), payload, "comparison-report.json"); comparison_inventory = artifacts.closed_inventory(stage, ("comparison-report.json", "comparison-report.sha256"), max_file_bytes=2 * 1024 * 1024)
        _remove_receipt(receipt_path, receipt_raw, receipt_parent, receipt_fd, receipt_parent_state, receipt_state, stage)
        artifacts.publish_no_replace(stage, output, comparison_inventory, max_file_bytes=2 * 1024 * 1024)
        stage = None
        return output
    finally:
        if stage is not None and stage.exists() and not stage.is_symlink():
            shutil.rmtree(stage)
def compare(seed17: Path, seed29: Path, receipt_path: Path, output: Path) -> Path:
    # Stage 1: closed structure, lexical report sidecars, and canonical receipt.
    records17, records29 = _bundle(seed17), _bundle(seed29); _admit_report_sidecar(seed17, records17); _admit_report_sidecar(seed29, records29)
    admission = _admit_receipt(receipt_path)
    try: return _compare_admitted(seed17, seed29, receipt_path, output, records17, records29, admission)
    finally: os.close(admission[3]); os.close(admission[2])
def main() -> int:
    try: compare(*_args())
    except Exception as exc: print(f"owned-root comparator: error: {exc}", file=sys.stderr); return 1
    return 0
if __name__ == "__main__":
    raise SystemExit(main())
