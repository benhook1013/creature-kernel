#!/usr/bin/env python3
"""Focused tests for the sealed exact-five visual-review gallery adapter."""

from __future__ import annotations

import hashlib
import json
import shutil
import struct
import sys
import tempfile
import unittest
import zlib
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve()
REPOSITORY_ROOT = HERE.parents[3]
VISUAL_REVIEW_ROOT = HERE.parents[1]
EXACT_FIVE_ROOT = REPOSITORY_ROOT / "experiments" / "owned-root-assembly-successor-exact-five"
NEUTRAL_ROOT = REPOSITORY_ROOT / "experiments" / "owned-root-assembly-successor"
sys.path.insert(0, str(VISUAL_REVIEW_ROOT))
sys.path.insert(0, str(EXACT_FIVE_ROOT))
sys.path.insert(0, str(NEUTRAL_ROOT))

import artifact_serialization as artifacts  # noqa: E402
import exact_five_publisher as exact_five  # noqa: E402
import publish_exact_five_gallery as adapter  # noqa: E402


def _chunk(kind: bytes, payload: bytes) -> bytes:
    return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", zlib.crc32(kind + payload) & 0xFFFFFFFF)


def _png(colour: tuple[int, int, int]) -> bytes:
    raw = b"".join(b"\x00" + bytes(colour) * adapter.PNG_WIDTH for _ in range(adapter.PNG_HEIGHT))
    header = struct.pack(">IIBBBBB", adapter.PNG_WIDTH, adapter.PNG_HEIGHT, 8, 2, 0, 0, 0)
    return adapter.PNG_SIGNATURE + _chunk(b"IHDR", header) + _chunk(b"IDAT", zlib.compress(raw, 9)) + _chunk(b"IEND", b"")


def _ply() -> bytes:
    vertex_count, _, quad_count, _, _ = exact_five.neutral.LEVEL_COUNTS[2]
    lines = ["ply", "format ascii 1.0", f"element vertex {vertex_count}", "property double x", "property double y", "property double z", f"element face {quad_count}", "property list uchar int vertex_indices", "end_header"]
    lines.extend(f"{index}.0 0.0 0.0" for index in range(vertex_count))
    lines.extend(f"4 {index % (vertex_count - 3)} {index % (vertex_count - 3) + 1} {index % (vertex_count - 3) + 2} {index % (vertex_count - 3) + 3}" for index in range(quad_count))
    return ("\n".join(lines) + "\n").encode("ascii")


class ExactFiveGalleryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="ck-exact-five-gallery-tests-")
        self.root = Path(self.temp.name)
        self.exact_root = self.root / "exact-five"
        self.reviews_root = self.root / "reviews"
        self.exact_root.mkdir()
        self.reviews_root.mkdir()
        self.identity = self._identity()
        self.table = [{"id": profile, "label": profile, "dimension_scales": {"scale": 1000 + index}, "part_placements": {"part": [index, 0, 0]}} for index, profile in enumerate(exact_five.PROFILES)]
        self._write_exact_root()

    def tearDown(self) -> None:
        self.temp.cleanup()

    @staticmethod
    def _record(role: str, data: bytes) -> dict[str, object]:
        return {"role_path": role, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}

    @staticmethod
    def _fixed_record(role: str, sha256: str) -> dict[str, object]:
        return {"role_path": role, "bytes": 1, "sha256": sha256}

    def _identity(self) -> dict[str, object]:
        runtime = {"implementation": "CPython", "version": "3.10.12", "platform": "Linux", "packages": {"Pillow": "11.1.0", "numpy": "2.2.6", "scikit-image": "0.25.2"}}
        comparator = self._fixed_record(exact_five.COMPARATOR_ROLE, "2" * 64)
        return {
            "activation": self._fixed_record(exact_five.ACTIVATION_ROLE, exact_five.ACTIVATION_SHA),
            "design": self._fixed_record(exact_five.DESIGN_ROLE, exact_five.DESIGN_SHA),
            "source": self._fixed_record(exact_five.SOURCE_ROLE, exact_five.SOURCE_SHA),
            "profile": self._fixed_record(exact_five.PROFILE_ROLE, exact_five.PROFILE_SHA),
            "dependencies": [self._fixed_record("dependency.py", "1" * 64)],
            "neutral_files": [comparator], "additive_files": [self._fixed_record(exact_five.PUBLISHER_ROLE, "3" * 64)],
            "runtime": runtime, "runtime_raw": artifacts.canonical_json_bytes(runtime),
            "runtime_sha": exact_five.RUNTIME_SHA, "comparator": comparator,
        }

    def _projection(self, profile_index: int) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
        values, bindings = [], []
        for component in exact_five.COMPONENT_IDS:
            source_pointers = [f"/source/{component.replace('.', '/')}"]
            profile_pointers = [f"/profiles/{profile_index}/dimension_scales/scale"]
            values.append({"prepared_component": component, "value": 1.0, "source_pointers": source_pointers, "profile_pointers": profile_pointers})
            bindings.append({"prepared_component": component, "derivation_id": "profile.dimension-permille-half-even-mm.v1", "source_addresses": [["document", ["body"], component, "value"]], "source_pointers": source_pointers, "profile_pointers": profile_pointers})
        return values, bindings

    @staticmethod
    def _thresholds_and_gates() -> tuple[list[dict[str, object]], dict[str, list[dict[str, object]]]]:
        gates: dict[str, list[dict[str, object]]] = {}
        prefixes = {"structural": "a", "continuity": "b", "anatomy": "c", "intersection": "d"}
        thresholds: list[dict[str, object]] = []
        for group, count in adapter.GATE_CARDINALITIES.items():
            rows = []
            for index in range(count):
                gate_id = f"{prefixes[group]}.{index:03d}"
                threshold_id = f"threshold.{gate_id}"
                thresholds.append({"threshold_id": threshold_id, "relation": "ge", "lower": 0, "upper": None, "unit": "score"})
                rows.append({"gate_id": gate_id, "outcome": "pass", "sample_count": 1, "observed_min": 1, "observed_max": 1, "threshold_id": threshold_id})
            gates[group] = rows
        thresholds.append({"threshold_id": "threshold.z.extra", "relation": "eq", "lower": 1, "upper": 1, "unit": "flag"})
        return sorted(thresholds, key=lambda row: str(row["threshold_id"]).encode()), gates

    def _managed_tests(self) -> dict[str, object]:
        executed = sorted(exact_five.NEW_REQUIRED, key=str.encode)
        receipt = {
            "schema": "owned-root-assembly-successor-exact-five-managed-test-receipt.v1", "outcome": "success",
            "invocation": {"environment": ["PYTHONHASHSEED=0"], "implementation_role": exact_five.RUNNER_ROLE, "mode": "managed-tests"},
            "activation_contract": self.identity["activation"], "design_contract": self.identity["design"],
            "existing_dependencies": self.identity["dependencies"], "additive_implementation_files": self.identity["additive_files"],
            "runtime": self.identity["runtime"], "runtime_fingerprint_sha256": self.identity["runtime_sha"],
            "executed_test_ids": executed, "required_test_ids": list(exact_five.NEW_REQUIRED),
            "results": {"tests_run": len(executed), "failures": 0, "errors": 0, "skipped": 0, "expected_failures": 0, "unexpected_successes": 0},
        }
        raw = artifacts.canonical_json_bytes(receipt)
        return {"receipt_sha256": artifacts.sha256_bytes(raw), "receipt": receipt}

    def _write_exact_root(self, *, invalid_ply: bool = False) -> None:
        thresholds, gates = self._thresholds_and_gates()
        public_records: dict[str, dict[str, object]] = {}
        nested_profiles: list[dict[str, object]] = []
        base_ply = _ply()
        if invalid_ply:
            base_ply = base_ply.replace(b"format ascii 1.0", b"format ascii 1.1", 1)
        neutral_payloads: list[dict[str, object]] | None = None
        for index, profile_id in enumerate(exact_five.PROFILES):
            profile_root = self.exact_root / profile_id
            profile_root.mkdir()
            (profile_root / "surface-level-2.ply").write_bytes(base_ply)
            direct, lineage = _png((30 + index, 60, 90)), _png((90, 60 + index, 30))
            (profile_root / "direct.png").write_bytes(direct)
            (profile_root / "lineage.png").write_bytes(lineage)
            for role, data in (("surface-level-2.ply", base_ply), ("direct.png", direct), ("lineage.png", lineage)):
                public_records[f"{profile_id}/{role}"] = self._record(f"{profile_id}/{role}", data)
            local: dict[str, dict[str, object]] = {}
            for role in exact_five.PAYLOAD_ROLES:
                data = direct if role == "direct.png" else lineage if role == "lineage.png" else base_ply if role == "surface-level-2.ply" else f"{profile_id}:{role}".encode()
                local[role] = self._record(role, data)
            if neutral_payloads is None:
                neutral_payloads = [local[role] for role in exact_five.PAYLOAD_ROLES]
            if invalid_ply:
                coordinate, triangles = {"bytes": 1, "sha256": "4" * 64}, {"bytes": 1, "sha256": "5" * 64}
            else:
                _, _, coordinate, triangles = exact_five._ply_digest(profile_root / "surface-level-2.ply", "surface-level-2.ply", 2)
            levels = []
            for level in range(3):
                counts = exact_five.neutral.LEVEL_COUNTS[level]
                coordinates = coordinate if level == 2 else {"bytes": 1, "sha256": str(6 + level) * 64}
                indices = triangles if level == 2 else {"bytes": 1, "sha256": str(8 + level) * 64}
                levels.append({"level": level, "counts": {"level": level, "vertices": counts[0], "edges": counts[1], "quads": counts[2], "triangles": counts[3], "boundary_edges": counts[4]}, "coordinate_bytes": coordinates["bytes"], "coordinate_sha256": coordinates["sha256"], "triangle_index_bytes": indices["bytes"], "triangle_index_sha256": indices["sha256"], "ply": local[f"surface-level-{level}.ply"]})
            values, bindings = self._projection(index)
            carrier_raw = artifacts.canonical_json_bytes([row["value"] for row in values])
            row = self.table[index]
            selection = {"profile_pointer": f"/profiles/{index}", "profile_row_sha256": artifacts.sha256_bytes(artifacts.canonical_json_bytes(row)), "dimension_scales_sha256": artifacts.sha256_bytes(artifacts.canonical_json_bytes(row["dimension_scales"])), "part_placements_sha256": artifacts.sha256_bytes(artifacts.canonical_json_bytes(row["part_placements"]))}
            causality = []
            for parameter in sorted(exact_five.CAUSAL_COMPONENTS, key=str.encode):
                role = f"perturb-{parameter.replace('.', '-')}.ply"
                causality.append({"parameter_id": parameter, "prepared_component": exact_five.CAUSAL_COMPONENTS[parameter], "delta_m": 0.01, "support_level": 2, "predicted_support_count": 1, "observed_support_count": 1, "predicted_support_sha256": "a" * 64, "observed_support_sha256": "a" * 64, "maximum_movement_m": 0.001, "artifact": local[role]})
            config = exact_five.render.render_config_record()
            visibility = {"level": 2, "triangle_count": 3328, "triangle_index_sha256": levels[2]["triangle_index_sha256"], "rule": "larger-depth-then-lower-triangle-index"}
            nested = {
                "schema": "owned-root-assembly-successor-profile-seed-evidence.v1", "outcome": "success",
                "activation_contract": self.identity["activation"], "design_contract": self.identity["design"], "source": self.identity["source"], "profile_table": self.identity["profile"],
                "existing_dependencies": self.identity["dependencies"], "additive_implementation_files": self.identity["additive_files"], "runtime": self.identity["runtime"], "runtime_fingerprint_sha256": self.identity["runtime_sha"],
                "profile_id": profile_id, "profile_index": index, "selection": selection, "projected_values": values,
                "projected_carrier": {"bytes": len(carrier_raw), "sha256": artifacts.sha256_bytes(carrier_raw)}, "projection_bindings": bindings,
                "levels": levels, "thresholds": thresholds, "gates": gates, "causality": causality,
                "renders": {"renderer_id": "owned-root-raster-pillow-11.1.0.v1", "render_config": config, "render_config_sha256": artifacts.sha256_bytes(artifacts.canonical_json_bytes(config)), "visibility": visibility, "visibility_sha256": artifacts.sha256_bytes(artifacts.canonical_json_bytes(visibility)), "direct": local["direct.png"], "lineage": local["lineage.png"], "same_surface_positions_sha256": levels[2]["coordinate_sha256"], "same_surface_triangles_sha256": levels[2]["triangle_index_sha256"]},
                "payloads": [local[role] for role in exact_five.PAYLOAD_ROLES], "invariants": dict(adapter.INVARIANTS),
            }
            nested_raw = artifacts.canonical_json_bytes(nested)
            evidence_record = self._record("profile-seed-evidence.json", nested_raw)
            sidecar_raw = f"{evidence_record['sha256']}  profile-seed-evidence.json\n".encode()
            stable_map = dict(local)
            stable_map["profile-seed-evidence.json"] = evidence_record
            stable_map["profile-seed-evidence.sha256"] = self._record("profile-seed-evidence.sha256", sidecar_raw)
            nested_profiles.append({"profile_id": profile_id, "profile_index": index, "evidence": nested, "stable_cross_seed_comparisons": [stable_map[role] for role in exact_five.BUNDLE_STABLE_ROLES], "neutral_payload_comparisons": neutral_payloads if index == 0 else []})
        assert neutral_payloads is not None
        payloads = [public_records[role] for role in exact_five.PUBLIC_PAYLOAD_ROLES]
        evidence = {
            "schema": "owned-root-assembly-successor-exact-five-evidence.v1", "outcome": "success",
            "activation_contract": self.identity["activation"], "design_contract": self.identity["design"], "source": self.identity["source"], "profile_table": self.identity["profile"],
            "existing_dependencies": self.identity["dependencies"], "additive_implementation_files": self.identity["additive_files"], "managed_tests": self._managed_tests(),
            "neutral_baseline": {"comparison_report": self._fixed_record("comparison-report.json", exact_five.BASELINE_REPORT_SHA), "stable_manifest_sha256": exact_five.BASELINE_STABLE_SHA, "runtime_fingerprint_sha256": self.identity["runtime_sha"], "payload_comparisons": neutral_payloads},
            "runtime": self.identity["runtime"], "runtime_fingerprint_sha256": self.identity["runtime_sha"], "profile_order": list(exact_five.PROFILES), "profiles": nested_profiles, "payloads": payloads,
        }
        evidence_raw = artifacts.canonical_json_bytes(evidence)
        (self.exact_root / "exact-five-evidence.json").write_bytes(evidence_raw)
        evidence_sidecar = f"{hashlib.sha256(evidence_raw).hexdigest()}  exact-five-evidence.json\n".encode()
        (self.exact_root / "exact-five-evidence.sha256").write_bytes(evidence_sidecar)
        final_gate_ids = (["exact-five.run.01.identity", "exact-five.run.02.managed-tests", "exact-five.run.03.publisher-baseline-admission"] + [f"exact-five.run.{4 + index * 2 + offset:02d}.profile.{profile}.seed-{seed}" for index, profile in enumerate(exact_five.PROFILES) for offset, seed in enumerate(exact_five.SEEDS)] + [f"exact-five.run.{14 + index:02d}.profile.{profile}.cross-seed" for index, profile in enumerate(exact_five.PROFILES)] + ["exact-five.run.19.standard-neutral-payload-equality", "exact-five.run.20.evidence-graph", "exact-five.run.21.pre-report-closure"])
        report = {
            "schema": "owned-root-assembly-successor-exact-five-run-report.v1", "outcome": "success", "literal_invocation": {"environment": ["PYTHONHASHSEED=0"], "argv": [exact_five.LAUNCHER_ROLE]},
            "output_path": str(self.exact_root), "staging_path": str(self.exact_root.parent / ".stage"), "python_executable_path": sys.executable, "neutral_baseline_path": str(self.root / "baseline"),
            "started_utc": "2026-01-01T00:00:00.000000Z", "finished_utc": "2026-01-01T00:00:01.000000Z", "timings": [],
            "activation_contract_sha256": exact_five.ACTIVATION_SHA, "design_contract_sha256": exact_five.DESIGN_SHA, "runtime_fingerprint_sha256": self.identity["runtime_sha"],
            "evidence": {**self._record("exact-five-evidence.json", evidence_raw), "schema": evidence["schema"]}, "evidence_sidecar": self._record("exact-five-evidence.sha256", evidence_sidecar), "payloads": payloads,
            "profile_seed_runs": [{"profile_id": profile["profile_id"], "seed": seed, "outcome": "success", "evidence_sha256": artifacts.sha256_bytes(artifacts.canonical_json_bytes(profile["evidence"]))} for profile in nested_profiles for seed in exact_five.SEEDS],
            "gates": [{"gate_id": gate, "outcome": "pass", "sample_count": 1, "observed_min": 1, "observed_max": 1, "threshold_id": "gate.boolean-pass"} for gate in final_gate_ids],
        }
        report_raw = artifacts.canonical_json_bytes(report)
        (self.exact_root / "run-report.json").write_bytes(report_raw)
        (self.exact_root / "run-report.sha256").write_bytes(f"{hashlib.sha256(report_raw).hexdigest()}  run-report.json\n".encode())

    def _publish(self, review_id: str) -> dict[str, object]:
        with mock.patch.object(adapter.exact_five, "_static", return_value=self.identity), mock.patch.object(adapter.exact_five, "_table", return_value=self.table):
            return adapter.publish_exact_five_gallery(self.reviews_root, self.exact_root, review_id=review_id)

    def _reseal_evidence(self, evidence: dict[str, object]) -> None:
        evidence_raw = artifacts.canonical_json_bytes(evidence)
        (self.exact_root / "exact-five-evidence.json").write_bytes(evidence_raw)
        sidecar = f"{hashlib.sha256(evidence_raw).hexdigest()}  exact-five-evidence.json\n".encode()
        (self.exact_root / "exact-five-evidence.sha256").write_bytes(sidecar)
        report = json.loads((self.exact_root / "run-report.json").read_text())
        report["evidence"] = {**self._record("exact-five-evidence.json", evidence_raw), "schema": evidence["schema"]}
        report["evidence_sidecar"] = self._record("exact-five-evidence.sha256", sidecar)
        report_raw = artifacts.canonical_json_bytes(report)
        (self.exact_root / "run-report.json").write_bytes(report_raw)
        (self.exact_root / "run-report.sha256").write_bytes(f"{hashlib.sha256(report_raw).hexdigest()}  run-report.json\n".encode())

    def test_publishes_real_report_manifest_ref_and_five_ordered_pairs(self) -> None:
        result = self._publish("exact-five-gallery-test")
        self.assertEqual(result["images"], 10)
        review = json.loads((self.reviews_root / "exact-five-gallery-test" / "review.json").read_text())
        self.assertEqual([group["id"] for group in review["groups"]], list(exact_five.PROFILES))
        self.assertIn("merge checkpoint", review["description"])
        for profile_id, group in zip(exact_five.PROFILES, review["groups"]):
            self.assertEqual([item["id"] for item in group["items"]], [f"{profile_id}__direct", f"{profile_id}__lineage"])

    def test_rejects_self_consistently_resealed_tampered_provenance(self) -> None:
        evidence = json.loads((self.exact_root / "exact-five-evidence.json").read_text())
        evidence["design_contract"]["sha256"] = "f" * 64
        self._reseal_evidence(evidence)
        with self.assertRaisesRegex(adapter.ExactFiveGalleryError, "publication|provenance"):
            self._publish("tampered-provenance")
        self.assertFalse((self.reviews_root / "tampered-provenance").exists())

    def test_rejects_self_consistently_recorded_invalid_ply(self) -> None:
        shutil.rmtree(self.exact_root)
        self.exact_root.mkdir()
        self._write_exact_root(invalid_ply=True)
        with self.assertRaisesRegex(adapter.ExactFiveGalleryError, "PLY|semantic admission"):
            self._publish("invalid-ply")
        self.assertFalse((self.reviews_root / "invalid-ply").exists())

    def test_rejects_png_tampering_against_exact_five_evidence(self) -> None:
        path = self.exact_root / exact_five.PROFILES[0] / "direct.png"
        data = bytearray(path.read_bytes())
        data[-20] ^= 1
        path.write_bytes(data)
        with self.assertRaises(adapter.ExactFiveGalleryError):
            self._publish("tampered")

    def test_rejects_extra_root_file_before_publishing(self) -> None:
        (self.exact_root / "unexpected.bin").write_bytes(b"extra")
        with self.assertRaises(adapter.ExactFiveGalleryError):
            self._publish("extra-file")


if __name__ == "__main__":
    raise SystemExit(unittest.main())
