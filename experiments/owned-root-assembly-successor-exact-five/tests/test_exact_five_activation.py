"""Managed tests for the frozen exact-five activation boundary.

The test module is intentionally a consumer of the public neutral package and
the public validation surfaces of the exact-five runner/publisher.  It does
not import implementation helpers from either package.  The runner is
expected to expose the small admission/projection/build validators named
below; those names are the integration seam for the additive package.
"""

from __future__ import annotations

import copy
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import contextmanager
from decimal import Decimal
from pathlib import Path


HERE = Path(__file__).resolve()
EXACT_PACKAGE = HERE.parents[1]
REPOSITORY = HERE.parents[3]
NEUTRAL_PACKAGE = REPOSITORY / "experiments/owned-root-assembly-successor"
PROFILE_PACKAGE = REPOSITORY / "experiments/current-form-surface-preview"

sys.path.insert(0, str(EXACT_PACKAGE))
sys.path.insert(0, str(NEUTRAL_PACKAGE))
sys.path.insert(0, str(PROFILE_PACKAGE))

import artifact_serialization as artifacts  # noqa: E402
import exact_five_publisher as publisher  # noqa: E402
import exact_five_runner as runner  # noqa: E402
import generate_structural_profile_sources as profile_sources  # noqa: E402
import build_owned_root as neutral_builder  # noqa: E402
import compare_two_seed_outputs as neutral_comparator  # noqa: E402
import owned_root_surface as surface  # noqa: E402
import prepared_projection as neutral_projection  # noqa: E402
import render_export as render  # noqa: E402
from unittest.mock import patch  # noqa: E402


ACTIVATION_CONTRACT = NEUTRAL_PACKAGE / "exact-five-activation-contract.md"
ACTIVATION_SIDECAR = NEUTRAL_PACKAGE / "exact-five-activation-contract.sha256"
DESIGN_CONTRACT = NEUTRAL_PACKAGE / "design-contract.md"
SOURCE = REPOSITORY / "examples/body-documents/stylized-digitigrade-biped-authored-form.json"
PROFILE_TABLE = PROFILE_PACKAGE / "structural_profile_candidates.json"
PINNED_LAUNCHER = PROFILE_PACKAGE / "surface_preview_launcher.sh"
RUNNER_SCRIPT = EXACT_PACKAGE / "exact_five_runner.py"

ACTIVATION_ROLE = "experiments/owned-root-assembly-successor/exact-five-activation-contract.md"
DESIGN_ROLE = "experiments/owned-root-assembly-successor/design-contract.md"
SOURCE_ROLE = "examples/body-documents/stylized-digitigrade-biped-authored-form.json"
PROFILE_ROLE = "experiments/current-form-surface-preview/structural_profile_candidates.json"

ACTIVATION_SHA256 = "a5c38645c810efb24e79297fb7c8049f0f59529f37a67c18a5a728a7119f0d49"
DESIGN_SHA256 = "3122f0db2235754ed782bd38a88c4d7ad7cc7edbf635d147194f1e93f8556490"
SOURCE_SHA256 = "82269e843555ff1aad3c66399e3fcaeb11bbee81d72b69d15765ea9c4e7aff14"
PROFILE_SHA256 = "a5fba6643d0031bac83c08e9093e11fd7945806963509fa939865866112d9640"
BASELINE_REPORT_SHA256 = "fe450e9047275c517de297f50b9ed7881c969fd2c315e9714334dcb8d9e68f2a"
BASELINE_MANIFEST_SHA256 = "1b4aaed96671a55ae65dc163fd80db45288daf1b9dc9c91745bf19e414fa7ffa"

PROFILE_IDS = (
    "standard_neutral_reference",
    "compact_broad_short_limb_large_head",
    "tall_narrow_long_legged",
    "slender_long_limb",
    "stocky_broad_chested",
)
SEEDS = (17, 29)

SELECTORS = (
    ("left.r_y", "hips.left.r_y"),
    ("right.r_y", "hips.right.r_y"),
    ("lower_pelvis.L_y", "stations.lower_pelvis.C.y"),
    ("lower_pelvis.C_z", "stations.lower_pelvis.C.z"),
    ("left.r_x", "hips.left.r_x"),
    ("right.r_x", "hips.right.r_x"),
    ("lower_pelvis.R_x", "stations.lower_pelvis.rL"),
    ("left.r_z", "hips.left.r_z"),
    ("right.r_z", "hips.right.r_z"),
    ("lower_pelvis.R_f", "stations.lower_pelvis.rA"),
    ("lower_pelvis.R_b", "stations.lower_pelvis.rP"),
    ("left.thigh_start_x", "hips.left.P_s.x"),
    ("left.thigh_start_y", "hips.left.P_s.y"),
    ("left.thigh_start_z", "hips.left.P_s.z"),
    ("right.thigh_start_x", "hips.right.P_s.x"),
    ("right.thigh_start_y", "hips.right.P_s.y"),
    ("right.thigh_start_z", "hips.right.P_s.z"),
    ("neck_collar.C_y", "stations.neck_collar.C.y"),
    ("neck_collar.rL", "stations.neck_collar.rL"),
    ("neck_upper.C_y", "stations.neck_upper.C.y"),
    ("neck_upper.rL", "stations.neck_upper.rL"),
    ("left.axilla_x", "shoulders.left.axilla.x"),
    ("left.axilla_y", "shoulders.left.axilla.y"),
    ("right.axilla_x", "shoulders.right.axilla.x"),
    ("right.axilla_y", "shoulders.right.axilla.y"),
    ("left.peak_y", "shoulders.left.peak.y"),
    ("right.peak_y", "shoulders.right.peak.y"),
    ("left.start_lateral", "shoulders.left.start_lateral"),
    ("right.start_lateral", "shoulders.right.start_lateral"),
    ("left.start_up", "shoulders.left.start_up"),
    ("right.start_up", "shoulders.right.start_up"),
    ("left.shoulder_depth", "shoulders.left.shoulder_depth"),
    ("right.shoulder_depth", "shoulders.right.shoulder_depth"),
)

SURFACE_ROLES = ("surface-level-0.ply", "surface-level-1.ply", "surface-level-2.ply")
PERTURBATION_ROLES = tuple(f"perturb-{parameter.replace('.', '-')}.ply" for parameter, _ in SELECTORS)
PAYLOAD_ROLES = tuple(sorted((*SURFACE_ROLES, *PERTURBATION_ROLES, "direct.png", "lineage.png"), key=lambda value: value.encode("utf-8")))
BUNDLE_ROLES = tuple(sorted((*PAYLOAD_ROLES, "profile-seed-evidence.json", "profile-seed-evidence.sha256", "run-report.json", "run-report.sha256"), key=lambda value: value.encode("utf-8")))
PUBLIC_ROLES = tuple(
    f"{profile}/{role}"
    for profile in PROFILE_IDS
    for role in ("surface-level-2.ply", "direct.png", "lineage.png")
) + ("exact-five-evidence.json", "exact-five-evidence.sha256", "run-report.json", "run-report.sha256")
PUBLIC_ROLES = tuple(sorted(PUBLIC_ROLES, key=lambda value: value.encode("utf-8")))

REQUIRED_TEST_IDS = tuple(sorted(
    (
        f"test_exact_five_activation.ExactFiveActivationTests.{name}"
        for name in (
        "test_all_33_selectors_copy_one_component",
        "test_atomic_failure_has_no_partial_publication",
        "test_decimal_half_even_boundaries",
        "test_final_evidence_schema_and_19_file_closure",
        "test_geometry_receives_only_components",
        "test_neutral_projection_preserves_38_payloads",
        "test_profile_seed_bundle_schema_and_closure",
        "test_profile_table_closed_and_exact_order",
        "test_profile_table_rejects_duplicate_keys_and_signatures",
        "test_projection_has_exact_92_bindings",
        "test_seed_dispatch_is_exact",
        "test_static_identity_and_allowlist",
        )
    ),
    key=lambda value: value.encode("utf-8"),
))

FINAL_GATE_IDS = (
    "exact-five.run.01.identity",
    "exact-five.run.02.managed-tests",
    "exact-five.run.03.publisher-baseline-admission",
    "exact-five.run.04.profile.standard_neutral_reference.seed-17",
    "exact-five.run.05.profile.standard_neutral_reference.seed-29",
    "exact-five.run.06.profile.compact_broad_short_limb_large_head.seed-17",
    "exact-five.run.07.profile.compact_broad_short_limb_large_head.seed-29",
    "exact-five.run.08.profile.tall_narrow_long_legged.seed-17",
    "exact-five.run.09.profile.tall_narrow_long_legged.seed-29",
    "exact-five.run.10.profile.slender_long_limb.seed-17",
    "exact-five.run.11.profile.slender_long_limb.seed-29",
    "exact-five.run.12.profile.stocky_broad_chested.seed-17",
    "exact-five.run.13.profile.stocky_broad_chested.seed-29",
    "exact-five.run.14.profile.standard_neutral_reference.cross-seed",
    "exact-five.run.15.profile.compact_broad_short_limb_large_head.cross-seed",
    "exact-five.run.16.profile.tall_narrow_long_legged.cross-seed",
    "exact-five.run.17.profile.slender_long_limb.cross-seed",
    "exact-five.run.18.profile.stocky_broad_chested.cross-seed",
    "exact-five.run.19.standard-neutral-payload-equality",
    "exact-five.run.20.evidence-graph",
    "exact-five.run.21.pre-report-closure",
)

EXPECTED_DEPENDENCY_ROLES = tuple(sorted((
    "experiments/owned-root-assembly-successor/anatomy_gates.py",
    "experiments/owned-root-assembly-successor/artifact_serialization.py",
    "experiments/owned-root-assembly-successor/build_owned_root.py",
    "experiments/owned-root-assembly-successor/chart_lineage.py",
    "experiments/owned-root-assembly-successor/mesh_correctness.py",
    "experiments/owned-root-assembly-successor/owned_root_surface.py",
    "experiments/owned-root-assembly-successor/prepared_projection.py",
    "experiments/owned-root-assembly-successor/render_export.py",
    "experiments/current-form-surface-preview/generate_structural_profile_sources.py",
    "experiments/current-form-surface-preview/structural_atomic_publish.py",
    "experiments/current-form-surface-preview/surface_preview_launcher.sh",
    "experiments/current-form-surface-preview/requirements.txt",
), key=lambda value: value.encode("utf-8")))


def _record(path: Path, role: str, *, max_bytes: int | None = None) -> dict[str, object]:
    return artifacts.regular_file_record(path, role, max_bytes=max_bytes)


def _json(path: Path, *, max_bytes: int | None = None) -> tuple[dict[str, object], bytes]:
    raw = artifacts.read_regular_file(path, max_bytes=max_bytes)
    value = artifacts.decode_canonical_json(raw)
    if not isinstance(value, dict):
        raise AssertionError(f"{path} is not a JSON object")
    if raw[:3] == b"\xef\xbb\xbf" or raw[-1:] == b"\n" or raw != artifacts.canonical_json_bytes(value):
        raise AssertionError(f"{path} is not canonical JSON")
    return value, raw


def _sidecar(payload: bytes, sidecar: bytes, role: str) -> None:
    expected = f"{hashlib.sha256(payload).hexdigest()}  {role}\n".encode("ascii")
    if sidecar != expected:
        raise AssertionError(f"{role} sidecar is not its exact hash line")


class ExactFiveActivationTests(unittest.TestCase):
    """The exact managed-test inventory named by section 7.0."""

    @classmethod
    def _run_pinned(cls, arguments: list[str], seed: int) -> subprocess.CompletedProcess[str]:
        environment = os.environ.copy()
        environment["PYTHONHASHSEED"] = str(seed)
        return subprocess.run(
            [str(PINNED_LAUNCHER), *arguments],
            cwd=REPOSITORY,
            env=environment,
            text=True,
            capture_output=True,
            check=False,
            timeout=300,
        )

    @classmethod
    def _baseline(cls) -> Path:
        cached = getattr(cls, "_baseline_path", None)
        if cached is not None:
            return cached
        configured = os.environ.get("CK_EXACT_FIVE_BASELINE_ROOT")
        if not configured:
            raise AssertionError("set CK_EXACT_FIVE_BASELINE_ROOT to the admitted retained baseline root")
        output = Path(configured)
        if not output.is_absolute() or os.path.normpath(str(output)) != str(output) or output.is_symlink() or not output.is_dir() or output.resolve() != output:
            raise AssertionError("CK_EXACT_FIVE_BASELINE_ROOT must be a canonical, regular absolute directory")
        report = output / "comparison" / "comparison-report.json"
        if hashlib.sha256(report.read_bytes()).hexdigest() != BASELINE_REPORT_SHA256:
            raise AssertionError("configured baseline is not the admitted post-seam report")
        manifest = output / "seed-17" / "stable-manifest.json"
        if hashlib.sha256(manifest.read_bytes()).hexdigest() != BASELINE_MANIFEST_SHA256:
            raise AssertionError("configured baseline is not the admitted stable manifest")
        cls._baseline_path = output
        return output

    @classmethod
    def _bundle(cls, profile_id: str = PROFILE_IDS[0], seed: int = SEEDS[0]) -> Path:
        cached = getattr(cls, "_bundles", None)
        if cached is not None:
            return cached[(profile_id, seed)]
        holder = tempfile.TemporaryDirectory(prefix="ck-exact-five-bundle-", dir="/tmp")
        cls.addClassCleanup(holder.cleanup)
        bundles = {}
        for profile in PROFILE_IDS:
            profile_root = Path(holder.name) / profile
            profile_root.mkdir()
            for requested_seed in SEEDS:
                output = profile_root / f"seed-{requested_seed}"
                result = cls._run_pinned([str(RUNNER_SCRIPT), "--profile", profile, "--output", str(output)], requested_seed)
                if result.returncode != 0:
                    raise AssertionError(f"exact-five profile build failed: {result.stderr[-4000:]}")
                bundles[(profile, requested_seed)] = output
        cls._bundles = bundles
        return bundles[(profile_id, seed)]

    @classmethod
    def _all_bundles(cls) -> tuple[Path, ...]:
        cls._bundle()
        return tuple(cls._bundles[(profile, seed)] for profile in PROFILE_IDS for seed in SEEDS)

    @classmethod
    def _receipt(cls, path: Path) -> Path:
        identity = runner.static_admission()
        value = {
            "schema": "owned-root-assembly-successor-exact-five-managed-test-receipt.v1",
            "outcome": "success",
            "invocation": {
                "environment": ["PYTHONHASHSEED=0"],
                "implementation_role": "experiments/owned-root-assembly-successor-exact-five/exact_five_runner.py",
                "mode": "managed-tests",
            },
            "activation_contract": identity["activation_contract"],
            "design_contract": identity["design_contract"],
            "existing_dependencies": list(identity["existing_dependencies"]),
            "additive_implementation_files": list(identity["additive_implementation_files"]),
            "runtime": identity["runtime"],
            "runtime_fingerprint_sha256": identity["runtime_fingerprint_sha256"],
            "executed_test_ids": list(REQUIRED_TEST_IDS),
            "required_test_ids": list(REQUIRED_TEST_IDS),
            "results": {
                "tests_run": len(REQUIRED_TEST_IDS), "failures": 0, "errors": 0,
                "skipped": 0, "expected_failures": 0, "unexpected_successes": 0,
            },
        }
        artifacts.write_canonical_json_no_replace(path, value)
        return path

    @classmethod
    def _context(cls, path: Path, baseline: Path, output: Path) -> Path:
        value = {
            "schema": "owned-root-assembly-successor-exact-five-launcher-context.v1",
            "literal_invocation": {
                "environment": ["PYTHONHASHSEED=0"],
                "argv": [
                    "experiments/owned-root-assembly-successor-exact-five/exact_five_launcher.sh",
                    "--baseline-root", str(baseline), "--output", str(output),
                ],
            },
            "output_path": str(output),
            "neutral_baseline_path": str(baseline),
            "timings": [{"phase": phase, "seconds": 0.125} for phase in (
                "identity", "managed-tests", "launcher-baseline-admission", "profile-seed-builds"
            )],
        }
        artifacts.write_canonical_json_no_replace(path, value)
        return path

    @classmethod
    def _publication(cls, baseline: Path | None = None) -> tuple[Path, Path]:
        cached = getattr(cls, "_publication_fixture", None)
        if cached is not None and baseline is None:
            return cached
        holder = tempfile.TemporaryDirectory(prefix="ck-exact-five-publication-", dir="/tmp")
        cls.addClassCleanup(holder.cleanup)
        baseline = baseline or cls._baseline()
        root = Path(holder.name)
        output = root / "final-output"
        receipt = cls._receipt(root / "managed-test-receipt.json")
        context = cls._context(root / "launcher-context.json", baseline, output)
        staging = root / "publication-staging"
        result = publisher.publish(baseline, cls._all_bundles(), receipt, context, staging)
        if Path(result) != staging:
            raise AssertionError("publisher did not return its sealed staging root")
        if baseline == cls._baseline():
            cls._publication_fixture = (staging, root)
        return staging, root

    @staticmethod
    def _admit_table(raw: bytes) -> dict[str, object]:
        value = runner.admit_profile_table(raw)
        if not isinstance(value, dict):
            raise AssertionError("profile admission did not return a table object")
        return value

    @staticmethod
    def _projection(profile_id: str) -> dict[str, object]:
        source, _ = profile_sources.load_json_with_bytes(SOURCE, "authored source")
        table, _ = profile_sources.load_json_with_bytes(PROFILE_TABLE, "profile table")
        value = runner.project_profile(profile_id, source, table)
        if not isinstance(value, dict):
            raise AssertionError("profile projection did not return an evidence object")
        return value

    @staticmethod
    @contextmanager
    def _patched_path_bound_baseline_apis():
        with patch.object(
            neutral_builder,
            "validate_seed_bundle",
            side_effect=AssertionError("relocated admission used the path-bound neutral validator"),
        ), patch.object(
            neutral_comparator,
            "outer_publication_inventory",
            side_effect=AssertionError("relocated admission used the path-bound neutral comparator"),
        ):
            yield

    def test_all_33_selectors_copy_one_component(self):
        self.assertEqual(len(SELECTORS), 33)
        self.assertEqual(tuple(runner.PARAMETER_IDS), tuple(parameter for parameter, _ in SELECTORS))
        self.assertEqual(dict(neutral_projection.MUST_AFFECT_COMPONENTS), dict(SELECTORS))
        self.assertEqual(tuple(neutral_projection.MUST_AFFECT_PARAMETER_IDS), tuple(parameter for parameter, _ in SELECTORS))
        prepared = neutral_projection.prepare_standard_neutral(SOURCE)
        baseline = neutral_projection.project_geometry(prepared)
        self.assertEqual(len(baseline.values), 92)
        delta = float.fromhex("0x1.47ae147ae147bp-7")
        for parameter, component in SELECTORS:
            with self.subTest(parameter=parameter):
                perturbed = neutral_projection.project_perturbed_geometry(prepared, parameter)
                changed = [index for index, (left, right) in enumerate(zip(baseline.values, perturbed.values)) if left != right]
                self.assertEqual(len(changed), 1)
                self.assertEqual(surface.GEOMETRY_COMPONENT_IDS[changed[0]], component)
                self.assertEqual(perturbed.values[changed[0]], baseline.values[changed[0]] + delta)
        self.assertEqual(tuple(runner.PERTURBATION_ROLES), PERTURBATION_ROLES)
        self.assertEqual(len(runner.PERTURBATION_ROLES), 33)
        self.assertEqual(5 * 2 * len(runner.PERTURBATION_ROLES), 330)

    def test_atomic_failure_has_no_partial_publication(self):
        with tempfile.TemporaryDirectory(prefix="ck-exact-five-failure-", dir="/tmp") as directory:
            root = Path(directory)
            output = root / "absent-output"
            wrong_seed = self._run_pinned([str(RUNNER_SCRIPT), "--profile", PROFILE_IDS[0], "--output", str(output)], 19)
            self.assertNotEqual(wrong_seed.returncode, 0)
            self.assertFalse(output.exists() or output.is_symlink())

            stage = root / "stage"
            stage.mkdir()
            payload = stage / "payload.bin"
            payload.write_bytes(b"admitted")
            inventory = artifacts.closed_inventory(stage, ("payload.bin",), max_file_bytes=64)
            payload.write_bytes(b"drifted")
            with self.assertRaises(artifacts.ArtifactSerializationError):
                artifacts.publish_no_replace(stage, output, inventory, max_file_bytes=64)
            self.assertFalse(output.exists() or output.is_symlink())

            invalid_baseline = root / "missing-baseline"
            public_output = root / "public-output"
            environment = os.environ.copy()
            environment["PYTHONHASHSEED"] = "0"
            result = subprocess.run(
                [str(EXACT_PACKAGE / "exact_five_launcher.sh"), "--baseline-root", str(invalid_baseline), "--output", str(public_output)],
                cwd=REPOSITORY, env=environment, text=True, capture_output=True, check=False, timeout=300,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(public_output.exists() or public_output.is_symlink())

    def test_decimal_half_even_boundaries(self):
        source_bytes = SOURCE.read_bytes()
        marker = b'"role": "form_head_neck_profile_cranium_crown_forward_radius", "value": 0.65'
        self.assertEqual(source_bytes.count(marker), 1)
        expected = {"below": 812, "tie": 812, "above": 813}
        for label, token in (("below", "0.6499999999999999999"), ("tie", "0.65"), ("above", "0.6500000000000000001")):
            with self.subTest(label=label):
                projected, number = runner.project_decimal_metres(Decimal(token), 1250)
                self.assertEqual(projected, Decimal(expected[label]) / 1000)
                self.assertEqual(Decimal(str(number)), projected)

    def test_final_evidence_schema_and_19_file_closure(self):
        self.assertEqual(tuple(runner.PROFILE_IDS), PROFILE_IDS)
        self.assertEqual(tuple(publisher.SEEDS), SEEDS)
        self.assertEqual(tuple(publisher.PUBLIC_ROLES), PUBLIC_ROLES)
        self.assertEqual(len(PUBLIC_ROLES), 19)

        baseline = self._baseline()
        with tempfile.TemporaryDirectory(prefix="ck-exact-five-relocated-", dir="/tmp") as directory:
            relocated = Path(directory) / "relocated-baseline"
            shutil.copytree(baseline, relocated)
            self.assertTrue(relocated.is_absolute())
            self.assertNotEqual(relocated, baseline)
            self.assertNotEqual(relocated.resolve(), baseline.resolve())
            with self._patched_path_bound_baseline_apis():
                staging, publication_root = self._publication(relocated)
            records = artifacts.closed_inventory(staging, PUBLIC_ROLES, max_file_bytes=16 * 1024 * 1024)
            self.assertEqual(len(records), 19)
            by_role = {record["role_path"]: record for record in records}
            evidence, evidence_raw = _json(staging / "exact-five-evidence.json", max_bytes=16 * 1024 * 1024)
            report, report_raw = _json(staging / "run-report.json", max_bytes=2 * 1024 * 1024)
            self.assertEqual(set(evidence), {
                "schema", "outcome", "activation_contract", "design_contract", "source", "profile_table",
                "existing_dependencies", "additive_implementation_files", "managed_tests", "neutral_baseline",
                "runtime", "runtime_fingerprint_sha256", "profile_order", "profiles", "payloads",
            })
            self.assertEqual((evidence["schema"], evidence["outcome"], evidence["profile_order"]), (
                "owned-root-assembly-successor-exact-five-evidence.v1", "success", list(PROFILE_IDS)
            ))
            self.assertEqual(len(evidence["payloads"]), 15)
            self.assertEqual(evidence["payloads"], [by_role[role] for role in PUBLIC_ROLES if "/" in role])
            receipt, receipt_raw = _json(publication_root / "managed-test-receipt.json", max_bytes=16 * 1024 * 1024)
            self.assertEqual(evidence["managed_tests"], {
                "receipt_sha256": artifacts.sha256_bytes(receipt_raw), "receipt": receipt,
            })
            neutral = evidence["neutral_baseline"]
            self.assertEqual(len(neutral["payload_comparisons"]), 38)
            self.assertEqual(
                neutral["payload_comparisons"],
                [{"role_path": role, **{key: value for key, value in artifacts.regular_file_record(baseline / f"seed-17/{role}", role).items() if key != "role_path"}} for role in PAYLOAD_ROLES],
            )
            self.assertEqual(len(evidence["profiles"]), 5)
            for index, (profile_id, profile) in enumerate(zip(PROFILE_IDS, evidence["profiles"])):
                with self.subTest(profile=profile_id):
                    self.assertEqual(set(profile), {"profile_id", "profile_index", "evidence", "stable_cross_seed_comparisons", "neutral_payload_comparisons"})
                    self.assertEqual((profile["profile_id"], profile["profile_index"]), (profile_id, index))
                    self.assertEqual(len(profile["stable_cross_seed_comparisons"]), 40)
                    self.assertEqual([row["role_path"] for row in profile["stable_cross_seed_comparisons"]], list(BUNDLE_ROLES[:-2]))
                    self.assertEqual(len(profile["neutral_payload_comparisons"]), 38 if index == 0 else 0)
                    self.assertNotIn(b"run-report.json", artifacts.canonical_json_bytes(profile["evidence"]))
            self.assertEqual(set(report), {
                "schema", "outcome", "literal_invocation", "output_path", "staging_path", "python_executable_path",
                "neutral_baseline_path", "started_utc", "finished_utc", "timings", "activation_contract_sha256",
                "design_contract_sha256", "runtime_fingerprint_sha256", "evidence", "evidence_sidecar", "payloads",
                "profile_seed_runs", "gates",
            })
            self.assertEqual(report["schema"], "owned-root-assembly-successor-exact-five-run-report.v1")
            self.assertEqual(report["neutral_baseline_path"], str(relocated))
            self.assertEqual([row["phase"] for row in report["timings"]], [
                "identity", "managed-tests", "launcher-baseline-admission", "profile-seed-builds",
                "publisher-baseline-admission", "comparison", "pre-report-closure", "total-before-seal",
            ])
            self.assertEqual(report["payloads"], [by_role[role] for role in PUBLIC_ROLES if "/" in role])
            self.assertEqual([(row["profile_id"], row["seed"]) for row in report["profile_seed_runs"]], [
                (profile, seed) for profile in PROFILE_IDS for seed in SEEDS
            ])
            self.assertEqual([row["gate_id"] for row in report["gates"]], list(FINAL_GATE_IDS))
            self.assertTrue(all(row == {"gate_id": row["gate_id"], "outcome": "pass", "sample_count": 1, "observed_min": 1, "observed_max": 1, "threshold_id": "gate.boolean-pass"} for row in report["gates"]))
            self.assertEqual(report["evidence"], {
                "role_path": "exact-five-evidence.json", "bytes": len(evidence_raw),
                "sha256": artifacts.sha256_bytes(evidence_raw), "schema": evidence["schema"],
            })
            self.assertEqual(report["evidence_sidecar"], by_role["exact-five-evidence.sha256"])
            _sidecar(evidence_raw, (staging / "exact-five-evidence.sha256").read_bytes(), "exact-five-evidence.json")
            _sidecar(report_raw, (staging / "run-report.sha256").read_bytes(), "run-report.json")

            malformed_missing = Path(directory) / "malformed-missing"
            shutil.copytree(staging, malformed_missing)
            (malformed_missing / "run-report.sha256").unlink()
            with self.assertRaises(artifacts.ArtifactSerializationError):
                artifacts.closed_inventory(malformed_missing, PUBLIC_ROLES, max_file_bytes=16 * 1024 * 1024)
            malformed_extra = Path(directory) / "malformed-extra"
            shutil.copytree(staging, malformed_extra)
            (malformed_extra / "unexpected").write_bytes(b"x")
            with self.assertRaises(artifacts.ArtifactSerializationError):
                artifacts.closed_inventory(malformed_extra, PUBLIC_ROLES, max_file_bytes=16 * 1024 * 1024)

            drifted_payload = relocated / "seed-17" / "surface-level-2.ply"
            original_payload = drifted_payload.read_bytes()
            drifted_payload.write_bytes(original_payload + b"\n")
            self.assertEqual(drifted_payload.read_bytes(), original_payload + b"\n")
            output = Path(directory) / "drift-output"
            receipt = self._receipt(Path(directory) / "drift-receipt.json")
            context = self._context(Path(directory) / "drift-context.json", relocated, output)
            drift_stage = Path(directory) / "drift-stage"
            with self._patched_path_bound_baseline_apis(), self.assertRaises(ValueError):
                publisher.publish(relocated, self._all_bundles(), receipt, context, drift_stage)
            self.assertFalse(output.exists() or output.is_symlink() or drift_stage.exists() or drift_stage.is_symlink())

    def test_geometry_receives_only_components(self):
        prepared = neutral_projection.prepare_standard_neutral(SOURCE)
        geometry = neutral_projection.project_geometry(prepared)
        self.assertIs(type(geometry), surface.GeometryComponents)
        self.assertEqual(tuple(surface.GeometryComponents.__slots__), ("values",))
        self.assertEqual(len(geometry.values), 92)
        self.assertTrue(all(type(value) is float for value in geometry.values))
        self.assertFalse(hasattr(geometry, "profile_id"))
        self.assertFalse(hasattr(geometry, "source"))
        self.assertFalse(hasattr(geometry, "provenance"))
        surface.validate_geometry_components(geometry)
        for forbidden in (prepared, {"profile_id": PROFILE_IDS[1]}, PROFILE_IDS[1], geometry.values):
            with self.subTest(forbidden=type(forbidden).__name__), self.assertRaises(ValueError):
                surface.evaluate(forbidden)
            with self.subTest(runner_input=type(forbidden).__name__), self.assertRaises(ValueError):
                runner.run_geometry(forbidden)
        with self.assertRaises(ValueError):
            surface.validate_geometry_components({"values": geometry.values})

    def test_neutral_projection_preserves_38_payloads(self):
        baseline_root = self._baseline()
        prepared = neutral_projection.prepare_standard_neutral(SOURCE)
        geometry = neutral_projection.project_geometry(prepared)
        evaluation = surface.evaluate(geometry)
        actual: dict[str, bytes] = {}
        for mesh in (evaluation.cage, *evaluation.levels):
            actual[f"surface-level-{mesh.level}.ply"] = render.ply_bytes(mesh)
        for parameter, _ in SELECTORS:
            mesh = surface.evaluate(neutral_projection.project_perturbed_geometry(prepared, parameter)).levels[1]
            actual[f"perturb-{parameter.replace('.', '-')}.ply"] = render.ply_bytes(mesh)
        direct, lineage, visibility = render.render_pair_bytes(evaluation.levels[1])
        actual["direct.png"], actual["lineage.png"] = direct, lineage
        self.assertEqual(len(actual), 38)
        for seed in SEEDS:
            seed_root = baseline_root / f"seed-{seed}"
            with self.subTest(seed=seed):
                for role, payload in actual.items():
                    self.assertEqual(payload, (seed_root / role).read_bytes(), role)
        self.assertEqual(
            artifacts.sha256_bytes(artifacts.canonical_json_bytes(list(geometry.values))),
            self._projection(PROFILE_IDS[0])["projected_carrier"]["sha256"],
        )
        self.assertEqual(visibility.triangle_index_sha256, artifacts.sha256_bytes(artifacts.triangle_index_hash_bytes(evaluation.levels[1].triangles)))

    def test_profile_seed_bundle_schema_and_closure(self):
        bundle = self._bundle()
        records = artifacts.closed_inventory(bundle, BUNDLE_ROLES, max_file_bytes=2 * 1024 * 1024)
        self.assertEqual(len(records), 42)
        self.assertEqual(tuple(record["role_path"] for record in records), tuple(sorted(BUNDLE_ROLES)))
        evidence, evidence_raw = _json(bundle / "profile-seed-evidence.json", max_bytes=16 * 1024 * 1024)
        report, report_raw = _json(bundle / "run-report.json", max_bytes=2 * 1024 * 1024)
        self.assertEqual(set(evidence), {
            "schema", "outcome", "activation_contract", "design_contract", "source", "profile_table",
            "existing_dependencies", "additive_implementation_files", "runtime", "runtime_fingerprint_sha256",
            "profile_id", "profile_index", "selection", "projected_values", "projected_carrier",
            "projection_bindings", "levels", "thresholds", "gates", "causality", "renders", "payloads", "invariants",
        })
        self.assertEqual(evidence["schema"], "owned-root-assembly-successor-profile-seed-evidence.v1")
        self.assertEqual(evidence["outcome"], "success")
        self.assertEqual((evidence["profile_id"], evidence["profile_index"]), (PROFILE_IDS[0], 0))
        self.assertEqual(len(evidence["projected_values"]), 92)
        self.assertEqual(len(evidence["projection_bindings"]), 92)
        self.assertEqual([row["prepared_component"] for row in evidence["projected_values"]], sorted(row["prepared_component"] for row in evidence["projected_values"]))
        self.assertEqual([row["prepared_component"] for row in evidence["projection_bindings"]], sorted(row["prepared_component"] for row in evidence["projection_bindings"]))
        self.assertEqual(len(evidence["levels"]), 3)
        self.assertEqual([row["level"] for row in evidence["levels"]], [0, 1, 2])
        self.assertEqual(len(evidence["thresholds"]), 357)
        self.assertEqual(tuple(len(evidence["gates"][name]) for name in ("structural", "continuity", "anatomy", "intersection")), (122, 144, 78, 12))
        self.assertEqual(len(evidence["causality"]), 33)
        self.assertEqual([row["parameter_id"] for row in evidence["causality"]], sorted((parameter for parameter, _ in SELECTORS), key=lambda value: value.encode("utf-8")))
        self.assertEqual({row["parameter_id"]: row["prepared_component"] for row in evidence["causality"]}, dict(SELECTORS))
        self.assertTrue(all(row["delta_m"] == 0.01 and row["support_level"] == 2 and row["predicted_support_count"] == row["observed_support_count"] and row["predicted_support_sha256"] == row["observed_support_sha256"] for row in evidence["causality"]))
        self.assertEqual(len(evidence["payloads"]), 38)
        self.assertEqual(set(evidence["invariants"]), {
            "topology_equal_to_neutral", "formulas_equal_to_neutral", "tunables_equal_to_neutral",
            "thresholds_equal_to_neutral", "gate_inventory_equal_to_neutral", "subdivision_equal_to_neutral",
            "ownership_equal_to_neutral", "causality_rules_equal_to_neutral", "renderer_equal_to_neutral",
        })
        self.assertNotIn("run-report.json", evidence_raw.decode("utf-8"))
        self.assertEqual(set(report), {
            "schema", "outcome", "profile_id", "profile_index", "seed", "literal_invocation", "output_path",
            "staging_path", "python_executable_path", "started_utc", "finished_utc", "timings",
            "runtime_fingerprint_sha256", "manifest_ref", "gates",
        })
        self.assertEqual(report["schema"], "owned-root-assembly-successor-profile-seed-run-report.v1")
        self.assertEqual(report["seed"], SEEDS[0])
        self.assertEqual([row["phase"] for row in report["timings"]], ["identity", "selection-projection", "catalogs", "geometry-gates", "causality", "serialization", "total-before-seal"])
        self.assertEqual([row["gate_id"] for row in report["gates"]], list(runner.RUN_GATES))
        self.assertTrue(all(row == {"gate_id": row["gate_id"], "outcome": "pass", "sample_count": 1, "observed_min": 1, "observed_max": 1, "threshold_id": "gate.boolean-pass"} for row in report["gates"]))
        self.assertEqual(report["manifest_ref"], {
            "role_path": "profile-seed-evidence.json", "bytes": len(evidence_raw),
            "sha256": artifacts.sha256_bytes(evidence_raw), "schema": evidence["schema"],
        })
        self.assertEqual(report_raw[-1:], b"}")
        _sidecar(evidence_raw, (bundle / "profile-seed-evidence.sha256").read_bytes(), "profile-seed-evidence.json")
        _sidecar(report_raw, (bundle / "run-report.sha256").read_bytes(), "run-report.json")
        self.assertEqual(tuple(runner.BUNDLE_ROLES), BUNDLE_ROLES)
        self.assertEqual(tuple(runner.STABLE_ROLES), tuple(sorted((*PAYLOAD_ROLES, "profile-seed-evidence.json", "profile-seed-evidence.sha256"))))
        for profile_id in PROFILE_IDS:
            for seed in SEEDS:
                with self.subTest(profile=profile_id, seed=seed):
                    validated = runner.validate_profile_seed_bundle(self._bundle(profile_id, seed), profile_id, seed)
                    self.assertEqual(validated["profile_id"], profile_id)

    def test_profile_table_closed_and_exact_order(self):
        table = self._admit_table(PROFILE_TABLE.read_bytes())
        source, _ = profile_sources.load_json_with_bytes(SOURCE, "authored source")
        self.assertEqual(set(table), {"base_source", "canonicalization", "format", "profiles", "transform"})
        rows = table["profiles"]
        self.assertEqual([row["id"] for row in rows], list(PROFILE_IDS))
        self.assertEqual(len({row["id"] for row in rows}), 5)
        self.assertEqual(len({row["label"] for row in rows}), 5)
        self.assertTrue(all(set(row) == {"dimension_scales", "id", "label", "part_placements"} for row in rows))
        self.assertTrue(all(len(row["dimension_scales"]) == 37 for row in rows))
        self.assertTrue(all(len(row["part_placements"]) == 18 for row in rows))
        self.assertEqual(tuple(profile_sources.ACTIVE_PROFILE_IDS), PROFILE_IDS)
        self.assertEqual(tuple(runner.PROFILE_IDS), PROFILE_IDS)
        for bad in ("unknown", 2, PROFILE_IDS[0] + "\x00"):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                runner.project_profile(bad, source, table)
        projected = runner.project_profile(PROFILE_IDS[2], source, table)
        self.assertEqual(projected["profile_id"], PROFILE_IDS[2])
        self.assertEqual(projected["profile_index"], 2)

    def test_profile_table_rejects_duplicate_keys_and_signatures(self):
        raw = PROFILE_TABLE.read_bytes()
        duplicate = raw[:-1] + b',"profiles":[]}'
        with self.assertRaises(ValueError):
            self._admit_table(duplicate)

        table = self._admit_table(raw)
        forged = copy.deepcopy(table)
        forged["profiles"][1]["dimension_scales"] = copy.deepcopy(forged["profiles"][0]["dimension_scales"])
        forged["profiles"][1]["part_placements"] = copy.deepcopy(forged["profiles"][0]["part_placements"])
        source, _ = profile_sources.load_json_with_bytes(SOURCE, "authored source")
        with self.assertRaises(ValueError):
            runner.project_profile(PROFILE_IDS[0], source, forged)

        extra = copy.deepcopy(table)
        extra["profiles"][0]["forged"] = 1
        with self.assertRaises(ValueError):
            runner.project_profile(PROFILE_IDS[0], source, extra)
        reordered = copy.deepcopy(table)
        reordered["profiles"][0], reordered["profiles"][1] = reordered["profiles"][1], reordered["profiles"][0]
        with self.assertRaises(ValueError):
            runner.project_profile(PROFILE_IDS[0], source, reordered)

    def test_projection_has_exact_92_bindings(self):
        table = self._admit_table(PROFILE_TABLE.read_bytes())
        projection = self._projection(PROFILE_IDS[1])
        values = projection["projected_values"]
        bindings = projection["projection_bindings"]
        components = tuple(surface.GEOMETRY_COMPONENT_IDS)
        self.assertEqual(len(components), 92)
        self.assertEqual(components, tuple(sorted(components, key=lambda value: value.encode("utf-8"))))
        self.assertEqual(len(values), len(bindings), 92)
        self.assertEqual(tuple(row["prepared_component"] for row in values), components)
        self.assertEqual(tuple(row["prepared_component"] for row in bindings), components)
        selected = table["profiles"][1]
        selection = projection["selection"]
        self.assertEqual(selection["profile_pointer"], "/profiles/1")
        self.assertEqual(selection["profile_row_sha256"], artifacts.sha256_bytes(artifacts.canonical_json_bytes(selected)))
        self.assertEqual(selection["dimension_scales_sha256"], artifacts.sha256_bytes(artifacts.canonical_json_bytes(selected["dimension_scales"])))
        self.assertEqual(selection["part_placements_sha256"], artifacts.sha256_bytes(artifacts.canonical_json_bytes(selected["part_placements"])))
        self.assertEqual(projection["projected_carrier"]["bytes"], len(artifacts.canonical_json_bytes([row["value"] for row in values])))
        self.assertEqual(projection["projected_carrier"]["sha256"], artifacts.sha256_bytes(artifacts.canonical_json_bytes([row["value"] for row in values])))
        neutral_bindings = {
            row["prepared_component"]: row for row in neutral_projection.source_binding_records(SOURCE)
        }
        for value, binding in zip(values, bindings):
            self.assertEqual(set(value), {"prepared_component", "value", "source_pointers", "profile_pointers"})
            self.assertEqual(set(binding), {"prepared_component", "derivation_id", "source_addresses", "source_pointers", "profile_pointers"})
            self.assertEqual(value["prepared_component"], binding["prepared_component"])
            self.assertEqual(value["source_pointers"], binding["source_pointers"])
            self.assertEqual(value["profile_pointers"], binding["profile_pointers"])
            self.assertEqual(value["source_pointers"], neutral_bindings[value["prepared_component"]]["source_pointers"])
            if binding["derivation_id"] == "profile.dimension-permille-half-even-mm.v1":
                self.assertEqual(len(value["profile_pointers"]), 1)
                self.assertIn("/dimension_scales/", value["profile_pointers"][0])
            else:
                self.assertTrue(value["profile_pointers"])
                self.assertTrue(all("/part_placements/" in pointer for pointer in value["profile_pointers"]))
            self.assertEqual(value["source_pointers"], sorted(set(value["source_pointers"])))
            self.assertEqual(value["profile_pointers"], sorted(set(value["profile_pointers"])))
            self.assertTrue(all(pointer.startswith("/body/") for pointer in value["source_pointers"]))
            self.assertTrue(all(pointer.startswith("/profiles/1/") for pointer in value["profile_pointers"]))
            self.assertTrue(all("//" not in pointer and not any(part.startswith("0") and part != "0" for part in pointer.split("/") if part.isdigit()) for pointer in value["profile_pointers"]))
        self.assertTrue(all(row["derivation_id"] in {
            "profile.dimension-permille-half-even-mm.v1", "profile.world-placement-axis-sum.v1", "profile.world-landmark-axis-sum.v1"
        } for row in bindings))

    def test_seed_dispatch_is_exact(self):
        self.assertEqual(tuple(runner.PROFILE_IDS), PROFILE_IDS)
        self.assertEqual(tuple(publisher.SEEDS), SEEDS)
        self.assertEqual(tuple(runner.PARAMETER_IDS), tuple(parameter for parameter, _ in SELECTORS))
        self.assertEqual(tuple(runner.PERTURBATION_ROLES), PERTURBATION_ROLES)
        with tempfile.TemporaryDirectory(prefix="ck-exact-five-seed-dispatch-", dir="/tmp") as directory:
            for seed in (0, 16, 18, 30, 31):
                output = Path(directory) / f"{PROFILE_IDS[0]}-{seed}"
                result = self._run_pinned([str(RUNNER_SCRIPT), "--profile", PROFILE_IDS[0], "--output", str(output)], seed)
                with self.subTest(profile=PROFILE_IDS[0], seed=seed):
                    self.assertNotEqual(result.returncode, 0)
                    self.assertFalse(output.exists() or output.is_symlink())

    def test_static_identity_and_allowlist(self):
        self.assertEqual(hashlib.sha256(ACTIVATION_CONTRACT.read_bytes()).hexdigest(), ACTIVATION_SHA256)
        self.assertEqual(ACTIVATION_SIDECAR.read_bytes(), f"{ACTIVATION_SHA256}  {ACTIVATION_ROLE}\n".encode("ascii"))
        self.assertEqual(_record(DESIGN_CONTRACT, DESIGN_ROLE)["sha256"], DESIGN_SHA256)
        self.assertEqual(_record(SOURCE, SOURCE_ROLE)["sha256"], SOURCE_SHA256)
        self.assertEqual(_record(PROFILE_TABLE, PROFILE_ROLE)["sha256"], PROFILE_SHA256)
        self.assertEqual(runner.EXPECTED_ACTIVATION_SHA256, ACTIVATION_SHA256)
        self.assertEqual(runner.EXPECTED_DESIGN_SHA256, DESIGN_SHA256)
        self.assertEqual(runner.EXPECTED_SOURCE_SHA256, SOURCE_SHA256)
        self.assertEqual(runner.EXPECTED_PROFILE_SHA256, PROFILE_SHA256)
        self.assertEqual(len(REQUIRED_TEST_IDS), 12)
        self.assertEqual(tuple(runner.REQUIRED_TEST_IDS), REQUIRED_TEST_IDS)
        self.assertEqual(tuple(row[0] for row in runner.DEPENDENCIES), EXPECTED_DEPENDENCY_ROLES)
        expected_files = {
            "experiments/owned-root-assembly-successor-exact-five/exact_five_launcher.sh",
            "experiments/owned-root-assembly-successor-exact-five/exact_five_runner.py",
            "experiments/owned-root-assembly-successor-exact-five/exact_five_publisher.py",
            "experiments/owned-root-assembly-successor-exact-five/tests/test_exact_five_activation.py",
        }
        found = set()
        for directory, subdirectories, filenames in os.walk(EXACT_PACKAGE, followlinks=False):
            subdirectories[:] = [name for name in subdirectories if not (Path(directory) / name).is_symlink()]
            for filename in filenames:
                path = Path(directory) / filename
                if path.suffix in (".py", ".sh"):
                    self.assertFalse(path.is_symlink(), path)
                    found.add(path.relative_to(REPOSITORY).as_posix())
        self.assertEqual(found, expected_files)
        self.assertEqual(tuple(runner.ADDITIVE_ROLES), tuple(sorted(expected_files, key=lambda value: value.encode("utf-8"))))
        self.assertEqual(tuple(sorted(runner.PAYLOAD_ROLES, key=lambda value: value.encode("utf-8"))), PAYLOAD_ROLES)
        self.assertEqual(tuple(sorted(runner.BUNDLE_ROLES, key=lambda value: value.encode("utf-8"))), BUNDLE_ROLES)
        self.assertEqual(tuple(publisher.PUBLIC_ROLES), PUBLIC_ROLES)
        self.assertEqual(tuple(runner.PROFILE_PACKAGE.parts[-2:]), ("experiments", "current-form-surface-preview"))


if __name__ == "__main__":
    unittest.main()
