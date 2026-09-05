#!/usr/bin/env bash
set -euo pipefail

ACTIVATION_SHA256="a5c38645c810efb24e79297fb7c8049f0f59529f37a67c18a5a728a7119f0d49"
DESIGN_SHA256="3122f0db2235754ed782bd38a88c4d7ad7cc7edbf635d147194f1e93f8556490"
SOURCE_SHA256="82269e843555ff1aad3c66399e3fcaeb11bbee81d72b69d15765ea9c4e7aff14"
PROFILE_SHA256="a5fba6643d0031bac83c08e9093e11fd7945806963509fa939865866112d9640"
BASELINE_REPORT_SHA256="fe450e9047275c517de297f50b9ed7881c969fd2c315e9714334dcb8d9e68f2a"
BASELINE_REPORT_SIDECAR_SHA256="27d4941acc57c9a800c2ee76205dd349f401f900d6ed0ee01b3d07925df85dac"
BASELINE_MANIFEST_SHA256="1b4aaed96671a55ae65dc163fd80db45288daf1b9dc9c91745bf19e414fa7ffa"
RUNTIME_SHA256="c19ca9c0b8268504f93513d55f90a0eb63777e566aba06e376b503c5e648f085"
SCRIPT_DIR="$(CDPATH='' cd -P -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(CDPATH='' cd -P -- "$SCRIPT_DIR/../.." && pwd)"
CURRENT_LAUNCHER="$REPO_ROOT/experiments/current-form-surface-preview/surface_preview_launcher.sh"
RUNNER_ROLE="experiments/owned-root-assembly-successor-exact-five/exact_five_runner.py"
PUBLISHER_ROLE="experiments/owned-root-assembly-successor-exact-five/exact_five_publisher.py"
EXACT_PACKAGE="$REPO_ROOT/experiments/owned-root-assembly-successor-exact-five"
error() { printf 'exact-five-launcher: error: %s\n' "$*" >&2; exit 1; }
now_ns() { date +%s%N; }
disjoint() { [[ "$1" != "$2" && "$1" != "$2"/* && "$2" != "$1"/* ]]; }
remove_owned() { local p ok=0; for p in "$@"; do if [[ -L "$p" ]]; then ok=1; elif [[ -d "$p" ]]; then rm -rf -- "$p" || ok=1; elif [[ -e "$p" ]]; then rm -f -- "$p" || ok=1; fi; done; return "$ok"; }
cleanup() { local status=$?; trap - EXIT; if (( status != 0 )); then remove_owned "${BUNDLES[@]}" "${PROFILE_DIRS[@]}" "$RECEIPT" "$CONTEXT" "$PUBLIC_STAGE" || status=1; [[ -z "$INVOCATION_ROOT" || ! -d "$INVOCATION_ROOT" || -L "$INVOCATION_ROOT" ]] || rmdir -- "$INVOCATION_ROOT" 2>/dev/null || status=1; fi; exit "$status"; }
BUNDLES=(); PROFILE_DIRS=(); RECEIPT=""; CONTEXT=""; INVOCATION_ROOT=""; PUBLIC_STAGE=""
trap cleanup EXIT; trap 'exit 1' HUP INT TERM
[[ "${PYTHONHASHSEED-}" == 0 ]] || error 'public invocation requires literal PYTHONHASHSEED=0'
[[ $# == 4 && $1 == --baseline-root && $3 == --output ]] || error 'usage: PYTHONHASHSEED=0 exact_five_launcher.sh --baseline-root BASELINE_ROOT --output ABSENT_PATH'
BASELINE_ROOT="$2"; OUTPUT="$4"
[[ "$BASELINE_ROOT" == /* && "$BASELINE_ROOT" != / && -d "$BASELINE_ROOT" && ! -L "$BASELINE_ROOT" && "$(realpath -e -- "$BASELINE_ROOT")" == "$BASELINE_ROOT" ]] || error 'BASELINE_ROOT must be an existing canonical absolute directory'
[[ "$OUTPUT" == /* && "$(realpath -m -- "$OUTPUT")" == "$OUTPUT" && ! -e "$OUTPUT" && ! -L "$OUTPUT" ]] || error 'ABSENT_PATH must be a canonical absolute absent path'
OUTPUT_PARENT="$(dirname -- "$OUTPUT")"; [[ -d "$OUTPUT_PARENT" && ! -L "$OUTPUT_PARENT" && "$(realpath -e -- "$OUTPUT_PARENT")" == "$OUTPUT_PARENT" && -w "$OUTPUT_PARENT" ]] || error 'output parent must be an existing canonical writable directory'
FS_TYPE="$(df -P -T -- "$OUTPUT_PARENT" | awk 'NR == 2 {print $2}')"; case "$FS_TYPE" in ''|9p|drvfs|fuseblk|cifs|smb|smb2|smb3|ntfs|ntfs3|vfat|exfat|fat|fat32) error 'output parent must be native Linux storage';; esac
disjoint "$BASELINE_ROOT" "$OUTPUT_PARENT" || error 'BASELINE_ROOT must be disjoint from output and staging paths'
FIXED=(
  "experiments/owned-root-assembly-successor/exact-five-activation-contract.md|-|$ACTIVATION_SHA256"
  "experiments/owned-root-assembly-successor/design-contract.md|173184|$DESIGN_SHA256"
  "examples/body-documents/stylized-digitigrade-biped-authored-form.json|56984|$SOURCE_SHA256"
  "experiments/current-form-surface-preview/structural_profile_candidates.json|29970|$PROFILE_SHA256"
  "experiments/owned-root-assembly-successor/anatomy_gates.py|25674|0c4b5f7812141a4cd7c7107655e578044355dfef5dbda6574bbb63bc359a2ff4"
  "experiments/owned-root-assembly-successor/artifact_serialization.py|27977|3837928e4b987c65fd773e540f7db502f5d9a0b4c5940b95c923953754fdf7d4"
  "experiments/owned-root-assembly-successor/build_owned_root.py|78268|713cbf967bf2e0e233bae0c3506199fdc9a6ed71418edbd8dbf9b75beeee4045"
  "experiments/owned-root-assembly-successor/chart_lineage.py|18263|01fdd09e8e0bb6d31851f0c7af711d90b313e36a012dbe3d71415a0468c31efc"
  "experiments/owned-root-assembly-successor/mesh_correctness.py|51035|4104b70e70e958a469125d1fff544e20fee44b784bf7915d8e724e63d4f39db1"
  "experiments/owned-root-assembly-successor/owned_root_surface.py|58732|c982d889fee30e2efea881b5725170740bc8afa2a883aa3dc4623941cd3e2a22"
  "experiments/owned-root-assembly-successor/prepared_projection.py|39646|58637097a350332db40368a027347ec395192880aa6ba4782c7d523e5b288190"
  "experiments/owned-root-assembly-successor/render_export.py|15933|bc251ea3f3f3cb1aa5ea66bfc4f79a82f86191e76bacb9a3c4f58e64883c4780"
  "experiments/current-form-surface-preview/generate_structural_profile_sources.py|54437|009be817cd2ec2db663b668fb5c9bdfa7296936283322e59d7a145e3d3cfec62"
  "experiments/current-form-surface-preview/structural_atomic_publish.py|10489|5e648b3a1a3519afdf0fc1f2f1ecfe6fe7f1c58130f71fd2c8ee4317e2f282b5"
  "experiments/current-form-surface-preview/surface_preview_launcher.sh|6582|3e18da2d361029a16558757d9727150d54c4d691b35c6a2a21b5b51cb7785190"
  "experiments/current-form-surface-preview/requirements.txt|49|69a3ce10b1f993d7913f02ca187eabb8d367abf214662ffa2132feacbdeedbec"
)
for spec in "${FIXED[@]}"; do IFS='|' read -r role bytes digest <<< "$spec"; path="$REPO_ROOT/$role"; [[ -f "$path" && ! -L "$path" ]] || error "fixed file is not regular: $role"; [[ "$bytes" == - || "$(stat -c %s -- "$path")" == "$bytes" ]] || error "fixed byte count drift: $role"; [[ "$(sha256sum -- "$path" | awk '{print $1}')" == "$digest" ]] || error "fixed SHA-256 drift: $role"; done
for sidecar in "$REPO_ROOT/experiments/owned-root-assembly-successor/design-contract.sha256" "$REPO_ROOT/experiments/owned-root-assembly-successor/exact-five-activation-contract.sha256"; do [[ -f "$sidecar" && ! -L "$sidecar" ]] || error 'contract sidecar is not regular'; done
cmp -s <(printf '%s  experiments/owned-root-assembly-successor/design-contract.md\n' "$DESIGN_SHA256") "$REPO_ROOT/experiments/owned-root-assembly-successor/design-contract.sha256" || error 'design-contract sidecar drift'
cmp -s <(printf '%s  experiments/owned-root-assembly-successor/exact-five-activation-contract.md\n' "$ACTIVATION_SHA256") "$REPO_ROOT/experiments/owned-root-assembly-successor/exact-five-activation-contract.sha256" || error 'activation-contract sidecar drift'
[[ -d "$EXACT_PACKAGE" && ! -L "$EXACT_PACKAGE" && -d "$EXACT_PACKAGE/tests" && ! -L "$EXACT_PACKAGE/tests" ]] || error 'exact-five package is incomplete'
EXPECTED_FILES="$(printf '%s\n' 'f exact_five_launcher.sh' 'f exact_five_publisher.py' 'f exact_five_runner.py' 'f tests/test_exact_five_activation.py' | LC_ALL=C sort)"; ACTUAL_FILES="$(LC_ALL=C find -P "$EXACT_PACKAGE" \( -type f -o -type l \) \( -name '*.py' -o -name '*.sh' \) -printf '%y %P\n' | LC_ALL=C sort)"; [[ "$ACTUAL_FILES" == "$EXPECTED_FILES" ]] || error 'exact-five source inventory drift'
for role in exact_five_launcher.sh exact_five_runner.py exact_five_publisher.py tests/test_exact_five_activation.py; do path="$EXACT_PACKAGE/$role"; [[ -f "$path" && ! -L "$path" && $(stat -c %s -- "$path") -le 4000000 ]] || error "additive file is invalid: $role"; done
NON_TEST_LOC=$(( $(wc -l < "$EXACT_PACKAGE/exact_five_launcher.sh") + $(wc -l < "$EXACT_PACKAGE/exact_five_runner.py") + $(wc -l < "$EXACT_PACKAGE/exact_five_publisher.py") )); TEST_LOC=$(wc -l < "$EXACT_PACKAGE/tests/test_exact_five_activation.py"); [[ $NON_TEST_LOC -le 1600 && $TEST_LOC -le 1200 ]] || error 'additive physical LOC cap exceeded'

pinned() { local seed="$1"; shift; PYTHONHASHSEED="$seed" "$CURRENT_LAUNCHER" - "$@" <<'PY'
import importlib, importlib.metadata, importlib.util, math, os, re, stat, sys
from pathlib import Path
mode, repo = sys.argv[1], Path(sys.argv[2])
def bad(message): raise SystemExit("exact-five launcher: " + message)
def canon(value): return type(value) is str and value.startswith("/") and os.path.normpath(value) == value and "//" not in value
def keys(value, names): return isinstance(value, dict) and set(value) == set(names)
def record(path, role, cap=4 * 1024 * 1024):
    import artifact_serialization as a
    return a.regular_file_record(path, role, max_bytes=cap)
def sidecar(raw, payload, name):
    import artifact_serialization as a
    if raw != f"{a.sha256_bytes(payload)}  {name}\n".encode("ascii"): bad(name + " sidecar drift")
if mode == "runtime":
    if (sys.implementation.name, sys.version_info[:3], sys.platform, getattr(sys.implementation, "cache_tag", None)) != ("cpython", (3, 10, 12), "linux", "cpython-310"): bad("runtime is not pinned CPython 3.10.12 Linux")
    for name, version in (("imageio", "2.37.4"), ("lazy-loader", "0.5"), ("networkx", "3.4.2"), ("numpy", "2.2.6"), ("packaging", "26.3"), ("pillow", "11.1.0"), ("scikit-image", "0.25.2"), ("scipy", "1.15.3"), ("tifffile", "2025.5.10")):
        if importlib.metadata.version(name) != version: bad("runtime distribution drift: " + name)
    for name in ("math", "zlib"):
        module, spec = importlib.import_module(name), importlib.util.find_spec(name)
        if getattr(module, "__file__", None) is not None or spec is None or spec.origin != "built-in": bad("built-in module admission failed: " + name)
    raise SystemExit(0)
sys.path.insert(0, str(repo / "experiments/owned-root-assembly-successor"))
import artifact_serialization as a
def json_file(path, cap=2 * 1024 * 1024): return a.decode_canonical_json(a.read_regular_file(path, max_bytes=cap))
def baseline(root):
    import build_owned_root as b
    roles, stable_roles = tuple(b.ARTIFACT_ROLES), tuple(sorted(set(b.ARTIFACT_ROLES) - {"report.json", "report.sha256"}, key=lambda x: x.encode()))
    entries = list(os.scandir(root)); names = sorted(x.name for x in entries); expected = ["comparison", "seed-17", "seed-29"]
    if names != expected or any(not (root / n).is_dir() or (root / n).is_symlink() for n in expected): bad("baseline outer inventory drift")
    maps = {}
    for seed in (17, 29):
        rows = list(a.closed_inventory(root / f"seed-{seed}", roles, max_file_bytes=8 * 1024 * 1024)); maps[seed] = {x["role_path"]: x for x in rows}
        if len(rows) != 47 or any(x["bytes"] > (8 if x["role_path"] == "causality-manifest.json" else 2) * 1024 * 1024 for x in rows): bad("baseline seed size or inventory drift")
    comp = root / "comparison"; crows = list(a.closed_inventory(comp, ("comparison-report.json", "comparison-report.sha256"), max_file_bytes=2 * 1024 * 1024)); raw = a.read_regular_file(comp / "comparison-report.json", max_bytes=2 * 1024 * 1024); sc = a.read_regular_file(comp / "comparison-report.sha256", max_bytes=128)
    expected_report, expected_sidecar, expected_manifest, expected_runtime = sys.argv[4:8]
    if len(raw) != 24640 or a.sha256_bytes(raw) != expected_report or len(sc) != 89 or a.sha256_bytes(sc) != expected_sidecar or sc != f"{expected_report}  comparison-report.json\n".encode(): bad("baseline comparison identity drift")
    report = a.decode_canonical_json(raw); comp_record = record(repo / "experiments/owned-root-assembly-successor/compare_two_seed_outputs.py", "experiments/owned-root-assembly-successor/compare_two_seed_outputs.py")
    if not keys(report, ("schema", "outcome", "comparator", "runtime_fingerprint_sha256", "managed_test_receipt", "seed_bundles", "stable_comparisons", "excluded_run_local_roles")) or report["schema"] != "owned-root-assembly-successor-comparison-report.v1" or report["outcome"] != "success" or report["comparator"] != comp_record or report["runtime_fingerprint_sha256"] != expected_runtime or report["excluded_run_local_roles"] != ["report.json", "report.sha256"]: bad("baseline comparison schema or identity drift")
    receipt = report["managed_test_receipt"]; impl = [record(repo / role, role) for role in sorted(b.IMPLEMENTATION_ROLES, key=lambda x: x.encode())]; results = receipt.get("results", {}); invocation = receipt.get("literal_invocation", {}); argv = invocation.get("argv", [])
    if not keys(receipt, ("schema", "outcome", "literal_invocation", "contract_sha256", "runtime_fingerprint_sha256", "implementation_files", "executed_test_ids", "required_test_ids", "results")) or receipt["schema"] != "owned-root-assembly-successor-managed-test-receipt.v1" or receipt["outcome"] != "success" or receipt["contract_sha256"] != "3122f0db2235754ed782bd38a88c4d7ad7cc7edbf635d147194f1e93f8556490" or receipt["runtime_fingerprint_sha256"] != "c19ca9c0b8268504f93513d55f90a0eb63777e566aba06e376b503c5e648f085" or receipt["implementation_files"] != impl or receipt["required_test_ids"] != list(b.REQUIRED_TEST_IDS) or not keys(invocation, ("environment", "argv")) or receipt["executed_test_ids"] != sorted(set(receipt["executed_test_ids"]), key=lambda x: x.encode()) or len(receipt["executed_test_ids"]) != 134 or not all(receipt["executed_test_ids"].count(x) == 1 for x in b.REQUIRED_TEST_IDS) or not (invocation.get("environment") == ["PYTHONHASHSEED=0"] and len(argv) == 4 and argv[:3] == ["experiments/owned-root-assembly-successor/build_owned_root.py", "--internal-managed-tests", "--receipt"] and canon(argv[3]) and Path(argv[3]).name == "managed-test-receipt.json") or not (keys(results, ("tests_run", "failures", "errors", "skipped", "expected_failures", "unexpected_successes")) and results == {"tests_run": 134, "failures": 0, "errors": 0, "skipped": 0, "expected_failures": 0, "unexpected_successes": 0}): bad("baseline managed receipt drift")
    comparisons = report["stable_comparisons"]
    if [x.get("role_path") for x in comparisons] != list(stable_roles) or len(report["seed_bundles"]) != 2: bad("baseline stable comparison inventory drift")
    for index, seed in enumerate((17, 29)):
        sm = root / f"seed-{seed}" / "stable-manifest.json"; stable = json_file(sm); mr = maps[seed]; recipe = stable.get("recipe_id"); expected_refs = {field: (role, "owned-root-assembly-successor-" + field.removesuffix("_manifest") + "-manifest.v1") for field, role in (("input_manifest", "input-manifest.json"), ("coordinate_manifest", "coordinate-manifest.json"), ("gate_manifest", "gate-manifest.json"), ("causality_manifest", "causality-manifest.json"), ("render_manifest", "render-manifest.json"))}
        if len(mr) != 47 or mr["stable-manifest.json"]["sha256"] != expected_manifest or not keys(stable, ("schema", "contract_sha256", "recipe_id", "runtime", "implementation_files", "input_manifest", "coordinate_manifest", "gate_manifest", "causality_manifest", "render_manifest", "artifact_hashes")) or stable["schema"] != "owned-root-assembly-successor-stable-manifest.v1" or stable["contract_sha256"] != "3122f0db2235754ed782bd38a88c4d7ad7cc7edbf635d147194f1e93f8556490" or not isinstance(recipe, str) or len(recipe) != 64 or stable["implementation_files"] != impl or a.sha256_bytes(a.canonical_json_bytes(stable["runtime"])) != expected_runtime or stable["artifact_hashes"] != [mr[x] for x in sorted(b.STABLE_ARTIFACT_ROLES, key=lambda x: x.encode())] or any(stable[field] != {"role_path": role, "bytes": mr[role]["bytes"], "sha256": mr[role]["sha256"], "schema": schema} for field, (role, schema) in expected_refs.items()): bad("baseline stable manifest drift")
        rp = root / f"seed-{seed}" / "report.json"; rv = json_file(rp); rr = maps[seed]; inv = rv.get("literal_invocation", {}); args = inv.get("argv", []); out, stage, exe = (Path(rv.get(x, "")) for x in ("output_path", "staging_path", "python_executable_path")); timings = rv.get("timings", []); gates = rv.get("gates", [])
        if not keys(rv, ("schema", "outcome", "seed", "literal_invocation", "output_path", "staging_path", "python_executable_path", "started_utc", "finished_utc", "timings", "runtime_fingerprint_sha256", "stable_manifest", "gates")) or rv["schema"] != "owned-root-assembly-successor-run-report.v1" or rv["outcome"] != "success" or type(rv["seed"]) is not int or rv["seed"] != seed or rv["runtime_fingerprint_sha256"] != "c19ca9c0b8268504f93513d55f90a0eb63777e566aba06e376b503c5e648f085" or not (keys(inv, ("environment", "argv")) and all(canon(str(x)) for x in (out, stage, exe)) and out.name == f"seed-{seed}" and stage.parent == out.parent and stage.name.startswith(f".{out.name}.stage-") and inv.get("environment") == [f"PYTHONHASHSEED={seed}"] and args == ["experiments/owned-root-assembly-successor/build_owned_root.py", "--output", str(out)] and re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{6}Z", rv["started_utc"]) and re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{6}Z", rv["finished_utc"]) and rv["finished_utc"] >= rv["started_utc"]) or not (isinstance(timings, list) and all(keys(x, ("phase", "seconds")) and type(x["seconds"]) is float and math.isfinite(x["seconds"]) and x["seconds"] >= 0 for x in timings)) or [x.get("phase") for x in timings] != list(b.RUN_PHASES) or rv["stable_manifest"] != {"role_path": "stable-manifest.json", "bytes": rr["stable-manifest.json"]["bytes"], "sha256": rr["stable-manifest.json"]["sha256"], "schema": "owned-root-assembly-successor-stable-manifest.v1"} or rv["gates"] != [{"gate_id": gate, "outcome": "pass", "sample_count": 1, "observed_min": 1, "observed_max": 1, "threshold_id": "gate.boolean-pass"} for gate in b.RUN_REPORT_GATES]: bad("baseline run report drift")
        sidecar(a.read_regular_file(root / f"seed-{seed}" / "report.sha256", max_bytes=128), a.read_regular_file(rp, max_bytes=2 * 1024 * 1024), "report.json")
        expected_bundle = {"seed": seed, "role_path": f"seed-{seed}", "stable_manifest": {"role_path": f"seed-{seed}/stable-manifest.json", "bytes": rr["stable-manifest.json"]["bytes"], "sha256": rr["stable-manifest.json"]["sha256"], "schema": "owned-root-assembly-successor-stable-manifest.v1"}, "report": {**rr["report.json"], "role_path": f"seed-{seed}/report.json"}, "report_sidecar": {**rr["report.sha256"], "role_path": f"seed-{seed}/report.sha256"}}
        if report["seed_bundles"][index] != expected_bundle or any(mr[x] != y for x, y in zip(stable_roles, comparisons)): bad("baseline comparison record drift")
    if len(crows) + sum(len(m) for m in maps.values()) != 96 or any(list(a.closed_inventory(root / f"seed-{seed}", roles, max_file_bytes=8 * 1024 * 1024)) != list(maps[seed].values()) for seed in (17, 29)) or list(a.closed_inventory(comp, ("comparison-report.json", "comparison-report.sha256"), max_file_bytes=2 * 1024 * 1024)) != crows: bad("baseline closed inventory changed during admission")
baseline(Path(sys.argv[3])) if mode == "baseline" else None
if mode == "context":
    path, base, output = map(Path, sys.argv[3:6]); ns = [int(x) for x in sys.argv[6:14]]; pairs = zip(ns[::2], ns[1::2]); value = {"schema": "owned-root-assembly-successor-exact-five-launcher-context.v1", "literal_invocation": {"environment": ["PYTHONHASHSEED=0"], "argv": ["experiments/owned-root-assembly-successor-exact-five/exact_five_launcher.sh", "--baseline-root", str(base), "--output", str(output)]}, "output_path": str(output), "neutral_baseline_path": str(base), "timings": [{"phase": phase, "seconds": float(end - start) / 1e9} for phase, (start, end) in zip(("identity", "managed-tests", "launcher-baseline-admission", "profile-seed-builds"), pairs)]}; raw = a.canonical_json_bytes(value); len(raw) <= 64 * 1024 or bad("launcher context exceeds size cap"); a.write_bytes_no_replace(path, raw)
def final_tree(stage, destination, expected_digest, publish, baseline_root):
    profiles = ["standard_neutral_reference", "compact_broad_short_limb_large_head", "tall_narrow_long_legged", "slender_long_limb", "stocky_broad_chested"]; roles = [f"{p}/{name}" for p in profiles for name in ("surface-level-2.ply", "direct.png", "lineage.png")] + ["exact-five-evidence.json", "exact-five-evidence.sha256", "run-report.json", "run-report.sha256"]; rows = list(a.closed_inventory(stage, roles, max_file_bytes=16 * 1024 * 1024)); rm = {x["role_path"]: x for x in rows}; total = sum(x["bytes"] for x in rows)
    if len(rows) != 19 or total > 32 * 1024 * 1024 or any(x["bytes"] > (16 if x["role_path"] == "exact-five-evidence.json" else 2) * 1024 * 1024 for x in rows): bad("sealed publication inventory or size drift")
    eraw = a.read_regular_file(stage / "exact-five-evidence.json", max_bytes=16 * 1024 * 1024); rraw = a.read_regular_file(stage / "run-report.json", max_bytes=2 * 1024 * 1024); evidence = a.decode_canonical_json(eraw); report = a.decode_canonical_json(rraw); payloads = sorted((rm[x] for x in roles if "/" in x), key=lambda x: x["role_path"].encode())
    if not keys(evidence, ("schema", "outcome", "activation_contract", "design_contract", "source", "profile_table", "existing_dependencies", "additive_implementation_files", "managed_tests", "neutral_baseline", "runtime", "runtime_fingerprint_sha256", "profile_order", "profiles", "payloads")) or evidence["schema"] != "owned-root-assembly-successor-exact-five-evidence.v1" or evidence["outcome"] != "success" or evidence["profile_order"] != profiles or evidence["payloads"] != payloads or not keys(report, ("schema", "outcome", "literal_invocation", "output_path", "staging_path", "python_executable_path", "neutral_baseline_path", "started_utc", "finished_utc", "timings", "activation_contract_sha256", "design_contract_sha256", "runtime_fingerprint_sha256", "evidence", "evidence_sidecar", "payloads", "profile_seed_runs", "gates")) or report["schema"] != "owned-root-assembly-successor-exact-five-run-report.v1" or report["outcome"] != "success" or report["activation_contract_sha256"] != "a5c38645c810efb24e79297fb7c8049f0f59529f37a67c18a5a728a7119f0d49" or report["design_contract_sha256"] != "3122f0db2235754ed782bd38a88c4d7ad7cc7edbf635d147194f1e93f8556490" or report["runtime_fingerprint_sha256"] != "c19ca9c0b8268504f93513d55f90a0eb63777e566aba06e376b503c5e648f085" or report["neutral_baseline_path"] != str(baseline_root) or report["payloads"] != payloads or report["evidence"] != {"role_path": "exact-five-evidence.json", "bytes": rm["exact-five-evidence.json"]["bytes"], "sha256": rm["exact-five-evidence.json"]["sha256"], "schema": evidence["schema"]} or report["evidence_sidecar"] != rm["exact-five-evidence.sha256"] or len(report["profile_seed_runs"]) != 10 or len(report["gates"]) != 21: bad("final evidence graph drift")
    sidecar(a.read_regular_file(stage / "exact-five-evidence.sha256", max_bytes=256), eraw, "exact-five-evidence.json"); sidecar(a.read_regular_file(stage / "run-report.sha256", max_bytes=256), rraw, "run-report.json"); digest = a.sha256_bytes(a.canonical_json_bytes(rows));
    if publish:
        if digest != expected_digest: bad("sealed tree changed during exact cleanup")
        a.publish_no_replace(stage, destination, rows, max_file_bytes=16 * 1024 * 1024)
    else: print(digest)
if mode == "final-check": final_tree(Path(sys.argv[3]), Path(sys.argv[4]), "", False, Path(sys.argv[5]))
if mode == "final-publish": final_tree(Path(sys.argv[3]), Path(sys.argv[4]), sys.argv[5], True, Path(sys.argv[6]))
PY
}

cd -- "$REPO_ROOT"; IDENTITY_START="$(now_ns)"; pinned 0 runtime "$REPO_ROOT"; IDENTITY_END="$(now_ns)"
TOKEN="$(tr -d '-' < /proc/sys/kernel/random/uuid 2>/dev/null || true)"; [[ -n "$TOKEN" ]] || TOKEN="$RANDOM$RANDOM"; INVOCATION_ROOT="$OUTPUT_PARENT/.exact-five-$TOKEN"; PUBLIC_STAGE="$OUTPUT_PARENT/.exact-five-public-$TOKEN"; RECEIPT="$INVOCATION_ROOT/managed-test-receipt.json"; CONTEXT="$INVOCATION_ROOT/launcher-context.json"; [[ ! -e "$INVOCATION_ROOT" && ! -L "$INVOCATION_ROOT" && ! -e "$PUBLIC_STAGE" && ! -L "$PUBLIC_STAGE" ]] || error 'selected staging path is occupied'; BUNDLES=()
MANAGED_START="$(now_ns)"; CK_EXACT_FIVE_BASELINE_ROOT="$BASELINE_ROOT" PYTHONHASHSEED=0 "$CURRENT_LAUNCHER" "$REPO_ROOT/$RUNNER_ROLE" --internal-managed-tests --receipt "$RECEIPT"; MANAGED_END="$(now_ns)"; [[ -f "$RECEIPT" && ! -L "$RECEIPT" && -d "$INVOCATION_ROOT" ]] || error 'managed tests did not seal their receipt'
BASELINE_START="$(now_ns)"; pinned 0 baseline "$REPO_ROOT" "$BASELINE_ROOT" "$BASELINE_REPORT_SHA256" "$BASELINE_REPORT_SIDECAR_SHA256" "$BASELINE_MANIFEST_SHA256" "$RUNTIME_SHA256"; BASELINE_END="$(now_ns)"
PROFILES=(standard_neutral_reference compact_broad_short_limb_large_head tall_narrow_long_legged slender_long_limb stocky_broad_chested); PROFILE_START="$(now_ns)"
for profile_index in 0 1 2 3 4; do profile="${PROFILES[$profile_index]}"; profile_dir="$INVOCATION_ROOT/profile-$profile_index"; mkdir -m 700 -- "$profile_dir"; PROFILE_DIRS+=("$profile_dir"); for seed in 17 29; do bundle="$profile_dir/seed-$seed"; BUNDLES+=("$bundle"); [[ ! -e "$bundle" && ! -L "$bundle" ]] || error 'profile bundle path is occupied'; PYTHONHASHSEED="$seed" "$CURRENT_LAUNCHER" "$REPO_ROOT/$RUNNER_ROLE" --profile "$profile" --output "$bundle"; done; done
PROFILE_END="$(now_ns)"; pinned 0 context "$REPO_ROOT" "$CONTEXT" "$BASELINE_ROOT" "$OUTPUT" "$IDENTITY_START" "$IDENTITY_END" "$MANAGED_START" "$MANAGED_END" "$BASELINE_START" "$BASELINE_END" "$PROFILE_START" "$PROFILE_END"
PYTHONHASHSEED=0 "$CURRENT_LAUNCHER" "$REPO_ROOT/$PUBLISHER_ROLE" "$BASELINE_ROOT" "${BUNDLES[@]}" "$RECEIPT" "$CONTEXT" "$PUBLIC_STAGE"
[[ -d "$PUBLIC_STAGE" && ! -L "$PUBLIC_STAGE" ]] || error 'publisher did not seal the public staging tree'; SEALED_DIGEST="$(pinned 0 final-check "$REPO_ROOT" "$PUBLIC_STAGE" "$OUTPUT" "$BASELINE_ROOT" | tail -n 1)"
remove_owned "${BUNDLES[@]}" "${PROFILE_DIRS[@]}" "$RECEIPT" "$CONTEXT" || error 'exact ephemeral cleanup failed'; [[ ! -e "$INVOCATION_ROOT" || -L "$INVOCATION_ROOT" ]] || rmdir -- "$INVOCATION_ROOT" || error 'invocation staging root remained after exact cleanup'
pinned 0 final-publish "$REPO_ROOT" "$PUBLIC_STAGE" "$OUTPUT" "$SEALED_DIGEST" "$BASELINE_ROOT"
