from __future__ import annotations

import copy
import hashlib
import inspect
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock


PACKAGE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE))
import build_owned_root as builder  # noqa: E402


def identity_fixture():
    runtime = {"schema": "owned-root-assembly-successor-runtime.v2", "fixture": "focused"}
    runtime_bytes = builder.artifacts.canonical_json_bytes(runtime)
    records = [
        {"role_path": role, "bytes": index + 1, "sha256": f"{index + 1:064x}"}
        for index, role in enumerate(builder._order(builder.IMPLEMENTATION_ROLES))
    ]
    return {
        "contract": {"role_path": builder.CONTRACT_ROLE, "bytes": 173184,
                     "sha256": builder.EXPECTED_CONTRACT_SHA256},
        "source": {"role_path": builder.SOURCE_ROLE, "bytes": builder.EXPECTED_SOURCE_BYTES,
                   "sha256": builder.EXPECTED_SOURCE_SHA256},
        "profile_table": {"role_path": builder.PROFILE_ROLE,
                          "bytes": builder.EXPECTED_PROFILE_BYTES,
                          "sha256": builder.EXPECTED_PROFILE_SHA256},
        "runtime": runtime,
        "runtime_bytes": runtime_bytes,
        "runtime_fingerprint_sha256": builder.artifacts.sha256_bytes(runtime_bytes),
        "implementation_files": records,
    }


class FrozenInventoryTests(unittest.TestCase):
    def test_contract_identity_and_private_roles_are_closed(self):
        self.assertEqual(len(builder.PARAMETER_IDS), 33)
        self.assertEqual(len(builder.SURFACE_ROLES), 3)
        self.assertEqual(len(builder.PERTURBATION_ROLES), 33)
        self.assertEqual(len(builder.ARTIFACT_ROLES), 47)
        self.assertEqual(len(builder.IMPLEMENTATION_ROLES), 15)
        self.assertEqual(len(set(builder.ARTIFACT_ROLES)), 47)
        self.assertEqual(builder.RUN_REPORT_GATES[0], "seed.1.identity")
        self.assertEqual(builder.RUN_REPORT_GATES[-1], "seed.6.serialization")

    def test_parameter_to_ply_mapping_is_literal_and_reversible(self):
        expected = (
            "perturb-left-r_y.ply", "perturb-right-r_y.ply",
            "perturb-lower_pelvis-L_y.ply", "perturb-lower_pelvis-C_z.ply",
            "perturb-left-r_x.ply", "perturb-right-r_x.ply",
            "perturb-lower_pelvis-R_x.ply", "perturb-left-r_z.ply",
            "perturb-right-r_z.ply", "perturb-lower_pelvis-R_f.ply",
            "perturb-lower_pelvis-R_b.ply", "perturb-left-thigh_start_x.ply",
            "perturb-left-thigh_start_y.ply", "perturb-left-thigh_start_z.ply",
            "perturb-right-thigh_start_x.ply", "perturb-right-thigh_start_y.ply",
            "perturb-right-thigh_start_z.ply", "perturb-neck_collar-C_y.ply",
            "perturb-neck_collar-rL.ply", "perturb-neck_upper-C_y.ply",
            "perturb-neck_upper-rL.ply", "perturb-left-axilla_x.ply",
            "perturb-left-axilla_y.ply", "perturb-right-axilla_x.ply",
            "perturb-right-axilla_y.ply", "perturb-left-peak_y.ply",
            "perturb-right-peak_y.ply", "perturb-left-start_lateral.ply",
            "perturb-right-start_lateral.ply", "perturb-left-start_up.ply",
            "perturb-right-start_up.ply", "perturb-left-shoulder_depth.ply",
            "perturb-right-shoulder_depth.ply",
        )
        self.assertEqual(builder.PERTURBATION_ROLES, expected)

    def test_roles_are_sorted_only_at_schema_boundaries(self):
        self.assertNotEqual(builder.ARTIFACT_ROLES, tuple(sorted(builder.ARTIFACT_ROLES)))
        self.assertEqual(builder._order(builder.ARTIFACT_ROLES), tuple(sorted(builder.ARTIFACT_ROLES)))
        self.assertEqual(builder._order(builder.IMPLEMENTATION_ROLES), tuple(sorted(builder.IMPLEMENTATION_ROLES)))


class SupportAndGateTests(unittest.TestCase):
    def test_support_hash_uses_the_frozen_header_and_u32_indices(self):
        indices = (0, 4, 1736)
        payload = b"CKSUPPORTv1\0\2" + (3).to_bytes(4, "little") + b"".join(
            index.to_bytes(4, "little") for index in indices
        )
        self.assertEqual(builder._support_hash(indices), hashlib.sha256(payload).hexdigest())
        for bad in ((1, 1), (-1,), (1737,), (1, 0)):
            with self.subTest(bad=bad), self.assertRaises(builder.BuildError):
                builder._support_hash(bad)

    def test_gate_records_have_the_closed_contract_shape(self):
        result, threshold = builder._gate(
            "structural.example", 3, 0.5, 1.0, "ge", 0.25, None, "m"
        )
        self.assertEqual(set(result), {"gate_id", "outcome", "sample_count",
                                       "observed_min", "observed_max", "threshold_id"})
        self.assertEqual(set(threshold), {"threshold_id", "relation", "lower", "upper", "unit"})
        self.assertEqual(result["threshold_id"], threshold["threshold_id"])
        self.assertEqual(builder._bool("structural.boolean")[0]["outcome"], "pass")
        failed, zero = builder._gate("structural.L0.invalid_count.unowned_elements",
                                     1, 1, 1, "eq", 0, 0, "count")
        self.assertEqual(failed["outcome"], "fail")
        with self.assertRaises(builder.BuildError): builder._validate_gate(failed, zero, "hostile")

    def _synthetic_continuity(self, residual_samples, fold_samples):
        counts = (2, 4, 8)
        meshes = tuple(mock.Mock(vertices=(), quads=(), face_owners=(),
                                 boundary_loops=()) for _ in counts)
        evaluation = mock.Mock(cage=meshes[0], levels=meshes[1:])
        surface = mock.Mock(JUNCTIONS=("junction.synthetic",))
        mesh_api = mock.Mock(T=1.0)
        mesh_api.junction_continuity_metrics.side_effect = [
            {"traces": (tuple(range(count)), ()),
             "coordinate_residual_samples": residual_samples(count)} for count in counts
        ]
        reports = tuple({"port_metrics": {}} for _ in counts)
        with mock.patch.object(builder, "_junction_inputs",
                               return_value={"junction.synthetic": {}}), mock.patch.object(
                                   builder, "_fold_samples",
                                   side_effect=[fold_samples(count) for count in counts]):
            return builder._continuity(surface, mesh_api, evaluation, reports)[0]

    def test_nonuniform_residual_samples_publish_exact_truthful_extrema(self):
        gates = self._synthetic_continuity(
            lambda count: tuple(index / 100.0 for index in range(3 * count)),
            lambda count: (1.0,) * count)
        rows = {row["gate_id"]: row for row in gates}
        for level, count in enumerate((2, 4, 8)):
            row = rows[f"continuity.junction.synthetic.L{level}.coordinate_residual"]
            self.assertEqual((row["sample_count"], row["observed_min"],
                              row["observed_max"]),
                             (3 * count, 0.0, (3 * count - 1) / 100.0))
            self.assertNotEqual(row["observed_min"], row["observed_max"])

    def test_nonuniform_fold_samples_publish_exact_truthful_extrema(self):
        gates = self._synthetic_continuity(
            lambda count: (0.0,) * (3 * count),
            lambda count: tuple(1.0 + index / 2.0 for index in range(count)))
        rows = {row["gate_id"]: row for row in gates}
        for level, count in enumerate((2, 4, 8)):
            row = rows[f"continuity.junction.synthetic.L{level}.fold_angle"]
            self.assertEqual((row["sample_count"], row["observed_min"],
                              row["observed_max"]),
                             (count, 1.0, 1.0 + (count - 1) / 2.0))
            self.assertNotEqual(row["observed_min"], row["observed_max"])

    def test_manifest_reference_does_not_copy_extra_file_fields(self):
        record = {"role_path": "input.json", "bytes": 12, "sha256": "a" * 64,
                  "unexpected": "not a manifest field"}
        self.assertEqual(builder._manifest_ref(record, "schema.v1"), {
            "role_path": "input.json", "bytes": 12, "sha256": "a" * 64,
            "schema": "schema.v1",
        })

    def test_mesh_adapters_use_independent_topology_and_incident_domain_traces(self):
        import mesh_correctness as mesh_api
        import owned_root_surface as surface
        import prepared_projection as prepared_api
        import chart_lineage as chart_api
        prepared = prepared_api.prepare_standard_neutral()
        evaluation = surface.evaluate(prepared)
        formulas = tuple(surface.formula_candidate_records(prepared))
        chart_summary = chart_api.build_chart_summary(evaluation, formulas)
        base_faces = tuple(tuple(int(control[1:]) for control in row[2])
                           for row in surface.FACE_RECORDS)
        expected = mesh_api.derive_expected_face_catalogs(base_faces)
        fixtures = mesh_api.run_production_intersection_fixtures()
        self.assertEqual(tuple(row["fixture_id"] for row in fixtures), mesh_api.INTERSECTION_FIXTURE_IDS)
        reports = []
        for level, mesh in enumerate((evaluation.cage, *evaluation.levels)):
            self.assertEqual(mesh.quads, expected[level])
            inputs = builder._junction_inputs(surface, evaluation, level, chart_summary)
            self.assertEqual(set(inputs), set(surface.JUNCTIONS))
            for junction, row in inputs.items():
                reference = surface.propagate_junction_tags(evaluation, junction)[level]
                self.assertEqual(row["expected_domain_vertex_tags"], (reference, reference))
            ownership = builder._ownership_counts(surface, evaluation, chart_api, mesh_api,
                                                  prepared, formulas, chart_summary, level)
            self.assertEqual((ownership["unowned_elements"],
                              ownership["overowned_elements"]), (0, 0))
            for junction in surface.JUNCTIONS:
                result = mesh_api.junction_continuity_metrics(
                    mesh.vertices, mesh.quads, mesh.face_owners, **inputs[junction]
                )
                self.assertEqual(result["coordinate_residual"], 0.0)
                self.assertEqual(len(result["traces"]), 2)
            reports.append(mesh_api.validate_geometry(
                mesh.vertices, mesh.quads, level, dict(mesh.boundary_loops),
                builder._directions(surface), base_faces, inputs, mesh.face_owners))
        continuity, thresholds = builder._continuity(
            surface, mesh_api, evaluation, reports, chart_summary)
        self.assertEqual((len(continuity), len(thresholds)), (144, 144))

    def test_junction_metrics_reject_builder_observation_mismatch(self):
        import mesh_correctness as mesh_api
        import owned_root_surface as surface
        import prepared_projection as prepared_api
        import chart_lineage as chart_api
        prepared = prepared_api.prepare_standard_neutral()
        evaluation = surface.evaluate(prepared)
        formulas = tuple(surface.formula_candidate_records(prepared))
        chart_summary = chart_api.build_chart_summary(evaluation, formulas)
        level, junction = 1, surface.JUNCTIONS[0]
        domains = surface.JUNCTION_INFO[junction][0]
        reference = surface.propagate_junction_tags(evaluation, junction)[level]
        original_domain_tags = builder._domain_tags
        forged_vertex = None
        forged_tag = None

        def forge_domain_tags(*args):
            nonlocal forged_tag, forged_vertex
            meshes, owners, candidate_domains, domain_index, axes, candidate_level, candidate_surface = args
            original = original_domain_tags(
                meshes, owners, candidate_domains, domain_index, axes,
                candidate_level, candidate_surface)
            forged = dict(original)
            if candidate_domains == domains:
                if forged_vertex is None:
                    forged_vertex = min(original)
                    base = original[forged_vertex]
                    delta = 1
                    while True:
                        candidate = ((base[0][0] + delta, base[0][1]), base[1])
                        if candidate not in reference.values() and candidate not in original.values():
                            forged_tag = candidate
                            break
                        delta += 1
                self.assertIn(forged_vertex, original)
                self.assertNotIn(forged_tag, original.values())
                forged[forged_vertex] = forged_tag
            return forged

        with mock.patch.object(builder, "_domain_tags", side_effect=forge_domain_tags):
            inputs = builder._junction_inputs(surface, evaluation, level, chart_summary)
        observed_maps = inputs[junction]["domain_vertex_tags"]
        self.assertEqual(set(observed_maps[0]), set(observed_maps[1]))
        self.assertEqual(observed_maps[0][forged_vertex], observed_maps[1][forged_vertex])
        self.assertNotIn(forged_tag, reference.values())
        mesh = evaluation.levels[level - 1]
        with self.assertRaisesRegex(mesh_api.MeshCorrectnessError, "independent reference"):
            mesh_api.junction_continuity_metrics(
                mesh.vertices, mesh.quads, mesh.face_owners, **inputs[junction]
            )


class StaticAdmissionTests(unittest.TestCase):
    def test_package_implementation_fits_frozen_physical_loc_caps(self):
        counts = {"production": 0, "tests": 0}
        for role in builder.IMPLEMENTATION_ROLES:
            group = "tests" if "/tests/" in role else "production"
            counts[group] += builder.artifacts.read_regular_file(builder.ROOT / role).count(b"\n")
        self.assertLessEqual(counts["production"], 3400)
        self.assertLessEqual(counts["tests"], 2600)

    def test_implementation_scan_never_reports_non_source_files(self):
        found = []
        for directory, _, filenames in os.walk(builder.PACKAGE):
            found.extend((Path(directory) / name).relative_to(builder.ROOT).as_posix()
                         for name in filenames if Path(name).suffix in (".py", ".sh"))
        found = tuple(sorted(found, key=lambda value: value.encode("utf-8")))
        self.assertTrue(set(found) <= set(builder.IMPLEMENTATION_ROLES))

    def test_runtime_string_rejects_non_strings_and_oversized_values(self):
        self.assertEqual(builder._runtime_text("ok", "value"), "ok")
        with self.assertRaises(builder.BuildError):
            builder._runtime_text("x" * 129, "value")
        with self.assertRaises(builder.BuildError):
            builder._runtime_text(1, "value")

    def test_wrong_hash_seed_is_rejected_before_output_creation(self):
        with tempfile.TemporaryDirectory() as directory, mock.patch.dict(
                os.environ, {"PYTHONHASHSEED": "0"}, clear=False):
            output = Path(directory) / "seed"
            with self.assertRaisesRegex(builder.BuildError, "PYTHONHASHSEED"):
                builder.build_seed(output)
            self.assertFalse(output.exists())

    def test_builder_binds_publication_inventory_and_never_self_feeds_mesh(self):
        publication = inspect.getsource(builder.build_seed)
        geometry = inspect.getsource(builder._geometry)
        junctions = inspect.getsource(builder._junction_inputs)
        self.assertIn("publish_no_replace(stage, output, inventory, max_file_bytes=", publication)
        self.assertNotIn("publish_no_replace(stage, output)", publication)
        self.assertLess(publication.index("_validate_gate_manifest(gate_manifest)"),
                        publication.index('_write_json(stage / "gate-manifest.json"'))
        self.assertLess(publication.index("_validate_gate_manifest(gate_manifest)"),
                        publication.index("publish_no_replace"))
        self.assertNotIn("else mesh.quads", geometry)
        self.assertIn("derive_expected_face_catalogs(expected)", geometry)
        self.assertNotIn("reversed", junctions)
        self.assertIn("propagate_junction_tags", junctions)


class ManagedDispatchTests(unittest.TestCase):
    def test_invalid_command_does_not_enter_admission(self):
        with mock.patch.object(builder, "_static_admission") as admission:
            self.assertEqual(builder.main(["--output"]), 1)
            admission.assert_not_called()

    def test_internal_mode_dispatches_exactly_after_static_admission(self):
        with mock.patch.object(builder, "run_managed_tests", return_value={}) as managed:
            self.assertEqual(builder.main(["--internal-managed-tests", "--receipt", "/tmp/receipt"]), 0)
            managed.assert_called_once_with("/tmp/receipt")

    def test_unittest_discovery_keeps_the_experiment_non_package(self):
        loader = unittest.TestLoader()
        suite = loader.discover(str(builder.TESTS), pattern="test_*.py")
        tests = []

        def flatten(value):
            for item in value:
                if isinstance(item, unittest.TestSuite):
                    yield from flatten(item)
                else:
                    yield item

        tests.extend(flatten(suite))
        ids = {test.id() for test in tests}
        self.assertIn(
            "test_mesh_correctness.ProductionIntersectionFixtureTests.test_contract_fixture_matrix", ids
        )
        self.assertIn(
            "test_owned_root_surface.ProductionAxillaryFixtureTests.test_contract_fixture_matrix", ids
        )
        self.assertEqual(len(ids), len(tests))


class PublicValidatorTests(unittest.TestCase):
    def receipt(self, path):
        identity = identity_fixture()
        executed = list(builder.REQUIRED_TEST_IDS)
        value = {
            "schema": "owned-root-assembly-successor-managed-test-receipt.v1",
            "outcome": "success",
            "literal_invocation": {
                "environment": ["PYTHONHASHSEED=0"],
                "argv": ["experiments/owned-root-assembly-successor/build_owned_root.py",
                         "--internal-managed-tests", "--receipt", str(path)],
            },
            "contract_sha256": builder.EXPECTED_CONTRACT_SHA256,
            "runtime_fingerprint_sha256": identity["runtime_fingerprint_sha256"],
            "implementation_files": identity["implementation_files"],
            "executed_test_ids": executed,
            "required_test_ids": list(builder.REQUIRED_TEST_IDS),
            "results": {"tests_run": len(executed), "failures": 0, "errors": 0,
                        "skipped": 0, "expected_failures": 0,
                        "unexpected_successes": 0},
        }
        return identity, value

    def report(self, root, seed=17):
        identity = identity_fixture()
        stable = {"role_path": "stable-manifest.json", "bytes": 123,
                  "sha256": "a" * 64,
                  "schema": builder.MANIFEST_SCHEMAS["stable-manifest.json"]}
        value = {
            "schema": "owned-root-assembly-successor-run-report.v1",
            "outcome": "success",
            "seed": seed,
            "literal_invocation": {
                "environment": [f"PYTHONHASHSEED={seed}"],
                "argv": ["experiments/owned-root-assembly-successor/build_owned_root.py",
                         "--output", str(root)],
            },
            "output_path": str(root),
            "staging_path": str(root.parent / f".{root.name}.stage-focused"),
            "python_executable_path": "/pinned/python",
            "started_utc": "2026-09-05T01:02:03.000004Z",
            "finished_utc": "2026-09-05T01:02:04.000005Z",
            "timings": [{"phase": phase, "seconds": 0.125}
                        for phase in builder.RUN_PHASES],
            "runtime_fingerprint_sha256": identity["runtime_fingerprint_sha256"],
            "stable_manifest": stable,
            "gates": [{"gate_id": gate, "outcome": "pass", "sample_count": 1,
                       "observed_min": 1, "observed_max": 1,
                       "threshold_id": "gate.boolean-pass"}
                      for gate in builder.RUN_REPORT_GATES],
        }
        return identity, value

    def test_three_required_validator_exports_are_callable(self):
        self.assertTrue(callable(builder.validate_managed_test_receipt))
        self.assertTrue(callable(builder.validate_seed_bundle))
        self.assertTrue(callable(builder.validate_run_report))

    def test_managed_receipt_accepts_exact_canonical_all_pass_evidence(self):
        path = Path(tempfile.gettempdir()) / "managed-stage" / "managed-test-receipt.json"
        identity, value = self.receipt(path)
        raw = builder.artifacts.canonical_json_bytes(value)
        self.assertIs(builder.validate_managed_test_receipt(
            receipt=value, raw=raw, identity=identity), value)

    def test_managed_receipt_rejects_forged_or_noncanonical_evidence(self):
        path = Path(tempfile.gettempdir()) / "managed-stage" / "managed-test-receipt.json"
        identity, value = self.receipt(path)
        forged = copy.deepcopy(value)
        forged["results"]["tests_run"] += 1
        with self.assertRaises(builder.BuildError):
            builder.validate_managed_test_receipt(
                receipt=forged, raw=builder.artifacts.canonical_json_bytes(forged),
                identity=identity)
        with self.assertRaises(builder.BuildError):
            builder.validate_managed_test_receipt(
                receipt=value, raw=builder.artifacts.canonical_json_bytes(value) + b"\n",
                identity=identity)

    def test_run_report_accepts_exact_ordered_internal_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "seed-17"
            root.mkdir()
            identity, value = self.report(root)
            self.assertIs(builder.validate_run_report(
                root=root, seed=17, report=value, identity=identity), value)

    def test_run_report_rejects_wrong_phase_order_and_staging_scope(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "seed-17"
            root.mkdir()
            identity, value = self.report(root)
            value["timings"][0], value["timings"][1] = value["timings"][1], value["timings"][0]
            with self.assertRaises(builder.BuildError):
                builder.validate_run_report(root=root, seed=17, report=value,
                                            identity=identity)
            _, value = self.report(root)
            value["staging_path"] = str(root / ".seed-17.stage-wrong-parent")
            with self.assertRaises(builder.BuildError):
                builder.validate_run_report(root=root, seed=17, report=value,
                                            identity=identity)

    def test_gate_validator_uses_exact_356_gate_and_357_threshold_contract(self):
        groups, thresholds = builder._expected_gate_contract()
        threshold_map = {item["threshold_id"]: item for item in thresholds}
        manifest = {"thresholds": thresholds}
        for group, gate_ids in groups.items():
            rows = []
            for gate_id in gate_ids:
                threshold = threshold_map[f"threshold.{gate_id}"]
                relation = threshold["relation"]
                if relation == "eq":
                    low = high = threshold["lower"]
                elif relation == "ge":
                    low = high = threshold["lower"]
                elif relation == "le":
                    low = high = threshold["upper"]
                else:
                    low = high = 0.0
                rows.append({"gate_id": gate_id, "outcome": "pass", "sample_count": 1,
                             "observed_min": low, "observed_max": high,
                             "threshold_id": f"threshold.{gate_id}"})
            manifest[group] = rows
        builder._validate_gate_manifest(manifest)
        self.assertEqual(sum(len(manifest[name]) for name in groups), 356)
        self.assertEqual(len(thresholds), 357)
        invalid_ids = [gate_id for gate_id in groups["structural"]
                       if ".invalid_count." in gate_id]
        self.assertEqual(len(invalid_ids), 27)
        self.assertTrue(all((threshold_map[f"threshold.{gate_id}"]["relation"],
                            threshold_map[f"threshold.{gate_id}"]["lower"],
                            threshold_map[f"threshold.{gate_id}"]["upper"])
                           == ("eq", 0, 0) for gate_id in invalid_ids))
        for metric in ("unowned_elements", "overowned_elements"):
            hostile = copy.deepcopy(manifest)
            for row in hostile["structural"]:
                if row["gate_id"].endswith(f"invalid_count.{metric}"):
                    row["observed_min"] = row["observed_max"] = 1
            with self.subTest(metric=metric), self.assertRaises(builder.BuildError):
                builder._validate_gate_manifest(hostile)
        manifest["thresholds"][0] = dict(manifest["thresholds"][0], relation="ge")
        with self.assertRaises(builder.BuildError):
            builder._validate_gate_manifest(manifest)

    def test_ply_validator_accepts_only_canonical_quad_serialization(self):
        import render_export as render
        vertices = ((0.0, 0.0, 0.0), (1.0, 0.0, 0.0),
                    (1.0, 1.0, 0.0), (0.0, 1.0, 0.0))
        quads = ((0, 1, 2, 3),)
        raw = render.ply_bytes(vertices, quads)
        self.assertEqual(builder._parse_ply(raw, "fixture.ply", 4, 1, render),
                         (vertices, quads))
        with self.assertRaises(builder.BuildError):
            builder._parse_ply(raw.replace(b"0 0 0\n", b"0.0 0 0\n", 1),
                               "fixture.ply", 4, 1, render)

    def test_seed_validator_fails_closed_before_mutating_incomplete_bundle(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "seed-17"
            root.mkdir()
            before = tuple(root.iterdir())
            with self.assertRaises(builder.BuildError):
                builder.validate_seed_bundle(root=root, seed=17,
                                             identity=identity_fixture())
            self.assertEqual(tuple(root.iterdir()), before)

    def test_seed_validator_admits_complete_serialized_bundle(self):
        requested_seed = os.environ.get("PYTHONHASHSEED")
        self.assertIn(requested_seed, ("0", "17", "29"),
                      "test requires literal PYTHONHASHSEED=0, 17, or 29")
        if requested_seed == "0":
            return
        seed = int(requested_seed)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / f"seed-{seed}"
            identity = builder._static_admission()
            builder.build_seed(root)
            self.assertIsInstance(
                builder.validate_seed_bundle(root=root, seed=seed, identity=identity), dict
            )


if __name__ == "__main__":
    unittest.main()
