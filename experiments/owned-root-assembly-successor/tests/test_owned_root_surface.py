from __future__ import annotations

import sys
import unittest
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

HERE = Path(__file__).resolve().parents[1]
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
import anatomy_gates as anatomy
import chart_lineage as chart
import owned_root_surface as surface
import prepared_projection

def prepared():
    return prepared_projection.prepare_standard_neutral(
        REPO / "examples/body-documents/stylized-digitigrade-biped-authored-form.json"
    )


def independent_charts(evaluation):
    """Build valid chart ancestry while anatomy remains the unit under test."""
    return chart.build_chart_summary(evaluation, evaluation.cage.formula_records)


class CatalogTests(unittest.TestCase):
    def test_independent_catalog_counts_and_boundary_inventory(self):
        report = surface.validate_catalogs()
        self.assertEqual((len(surface.CELL_CATALOG), len(surface.DOMAINS)), (58, 8))
        self.assertEqual((report.vertex_count, report.edge_count, report.face_count), (120, 227, 104))
        self.assertEqual((report.boundary_edge_count, report.boundary_components), (38, 5))
        self.assertEqual(report.euler_characteristic, -3)
        self.assertEqual(len(report.extraordinary_controls), 20)
        self.assertEqual(len(surface.JUNCTION_INFO), 7)
        self.assertEqual(len(surface.PORT_INFO), 5)

        expected_ports = {
            "port.neck": ("c057", "c079", "c080", "c081", "c059", "c058"),
            "port.left_arm": ("c009", "c012", "c014", "c015", "c016", "c013", "c011", "c010"),
            "port.right_arm": ("c112", "c113", "c114", "c116", "c119", "c118", "c117", "c115"),
            "port.left_thigh": ("c000", "c001", "c002", "c018", "c040", "c039", "c038", "c017"),
            "port.right_thigh": ("c060", "c061", "c062", "c083", "c105", "c104", "c103", "c082"),
        }
        self.assertEqual({key: value[2] for key, value in surface.PORT_INFO.items()}, expected_ports)

    def test_public_surface_boundary_has_no_chart_or_sample_outputs(self):
        ids, faces, ports = surface.symbolic_topology()
        self.assertEqual((len(ids), len(faces), len(ports)), (120, 104, 5))
        self.assertEqual(tuple(name for name, _ in ports), surface.PORTS)
        self.assertEqual(surface.FACE_RECORDS[0], ("q000", "domain.left_hip", ("c000", "c001", "c004", "c003")))
        self.assertNotIn("_make_chart_records", surface.__dict__)
        self.assertNotIn("_attach_samples", surface.__dict__)


class SurfaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.prepared = prepared()
        cls.evaluation = surface.evaluate(cls.prepared)

    def test_formula_candidates_use_prepared_boundary_and_exact_dispatch(self):
        with patch.object(surface.prepared_projection, "validate_prepared",
                          wraps=surface.prepared_projection.validate_prepared) as admitted:
            cage = surface.build_cage(self.prepared)
        admitted.assert_called_once_with(self.prepared)
        self.assertEqual((len(cage.vertices), len(cage.quads), len(cage.formula_records)), (120, 104, 120))
        records = {r["control_id"]: r for r in cage.formula_records}
        self.assertEqual(records["c023"]["formula_id"], "formula.axial.j1.interior")
        self.assertIn("stations.lower_abdomen.rA", records["c023"]["geometry_dependencies"])
        self.assertNotIn("stations.lower_abdomen.rP", records["c023"]["geometry_dependencies"])
        self.assertNotIn("stations.upper_pelvis.rL", records["c023"]["geometry_dependencies"])
        self.assertEqual(records["c031"]["formula_id"], "formula.shoulder.left")
        self.assertNotIn("shoulders.left.start_up", records["c031"]["geometry_dependencies"])
        self.assertNotIn("hips.left.P_s.x", records["c003"]["geometry_dependencies"])
        self.assertIn("hips.left.P_s.x", records["c020"]["geometry_dependencies"])
        self.assertEqual(set(cage.formula_ids), set(surface.FORMULAS))

    def test_prepared_admission_rejects_malformed_binary64_and_rotation(self):
        bad = deepcopy(self.prepared)
        bad["stations"]["lower_pelvis"]["C"] = (0, -0.45, 0.0)
        with self.assertRaises(prepared_projection.PreparedProjectionError): surface.build_cage(bad)
        bad = deepcopy(self.prepared)
        bad["parts"][0]["placement"]["rotation_xyzw"][3] = 0.5
        with self.assertRaises(prepared_projection.PreparedProjectionError): surface.build_cage(bad)

    def test_subdivision_has_exact_numeric_topology_incidence_and_lineage(self):
        cage, level1, level2 = self.evaluation.cage, *self.evaluation.levels
        self.assertEqual([(len(m.vertices), len(m.quads), len(m.triangles)) for m in (cage, level1, level2)],
                         [(120, 104, 208), (451, 416, 832), (1737, 1664, 3328)])
        self.assertEqual((level1.control_ids[0], level2.control_ids[-1], level2.face_ids[-1]),
                         ("vertex.L1.v0000", "vertex.L2.v1736", "face.L2.q1663"))
        for mesh in (cage, level1, level2):
            self.assertFalse(hasattr(mesh, "chart_records"))
            self.assertFalse(hasattr(mesh, "transition_records"))
            self.assertTrue(all("samples" not in row for row in mesh.vertex_records))
        incidence = surface.subdivision_incidence(cage)
        self.assertEqual((len(incidence["edges"]), len(incidence["child_emission"])), (227, 416))
        self.assertEqual(incidence["child_emission"][0], (0, 0, (0, 120, 347, 121)))
        self.assertEqual(len(surface.propagate_port_loops(level1)["port.neck"]), 24)
        self.assertLessEqual(max(len(r["base_control_contributors"]) for r in level2.vertex_records), 20)
        self.assertLessEqual(max(len(r["geometry_dependency_union"]) for r in level2.vertex_records), 54)
        self.assertLessEqual(max(len(r["contributor_domains"]) for r in level2.vertex_records), 5)

    def test_contributor_domains_follow_catalog_order_and_forged_topology_fails(self):
        cage = self.evaluation.cage
        junction = cage.vertex_records[cage.control_ids.index("c021")]
        self.assertEqual(junction["contributor_domains"], ("domain.pelvis", "domain.abdomen"))
        self.assertEqual(surface.CONTROL_DOMAIN_INCIDENTS["c021"], ("domain.pelvis", "domain.abdomen"))
        bad = list(cage.quads); bad[0] = (bad[0][1], bad[0][0], bad[0][2], bad[0][3])
        with self.assertRaises(ValueError): surface.validate_level_structure(replace(cage, quads=tuple(bad)), self.prepared)

    def test_anatomy_rejects_forged_level_zero_triangles(self):
        bad = replace(self.evaluation.cage, triangles=self.evaluation.cage.triangles[:-1] + ((0, 1, 2, 3),))
        forged = surface.SurfaceEvaluation(bad, self.evaluation.levels)
        with self.assertRaises(anatomy.AnatomyGateError): anatomy.validate_evaluated_surface(forged, prepared=self.prepared)

    def test_analytic_derivatives_propagate_and_support_is_exact(self):
        derivative = surface.analytic_control_derivatives(self.prepared, "hips.left.P_s.x")
        self.assertEqual(derivative[self.evaluation.cage.control_ids.index("c003")], (0.0, 0.0, 0.0))
        self.assertEqual(len(surface.predicted_support(self.prepared, "hips.left.P_s.x")), 436)
        self.assertEqual(len(surface.predicted_support(self.prepared, "hips.right.P_s.x")), 436)
        with self.assertRaises(ValueError): surface.predicted_support(self.prepared, "outside.component")

    def test_analytic_support_ignores_formula_record_dependency_metadata(self):
        component = "hips.left.P_s.x"
        derivative = surface.analytic_control_derivatives(self.prepared, component)
        support = surface.predicted_support(self.prepared, component)
        for name, dependencies in (("stripped", []), ("corrupt", ["outside.component"])):
            records = deepcopy(surface.formula_candidate_records(self.prepared))
            for record in records: record["geometry_dependencies"] = dependencies
            with self.subTest(metadata=name), patch.object(surface, "formula_candidate_records", return_value=records):
                self.assertEqual(surface.analytic_control_derivatives(self.prepared, component), derivative)
                self.assertEqual(surface.predicted_support(self.prepared, component), support)
                with self.assertRaises(ValueError): surface.analytic_control_derivatives(self.prepared, "outside.component")

    def test_all_33_public_perturbations_match_exact_analytic_support(self):
        baseline = self.evaluation.levels[1]
        original = prepared_projection.canonical_json_bytes(self.prepared)
        tolerance = float.fromhex("0x1.c666666666666p-45")
        self.assertEqual((len(surface.MUST_AFFECT_PARAMETER_IDS), surface.PERTURBATION_DELTA_M), (33, 0.01))
        for parameter in surface.MUST_AFFECT_PARAMETER_IDS:
            with self.subTest(parameter=parameter):
                component = surface.MUST_AFFECT_COMPONENTS[parameter]; path = component.split(".")
                if path[-1] in "xyz": path[-1] = "xyz".index(path[-1])
                expected = deepcopy(self.prepared); target = expected
                for part in path[:-1]: target = target[part]
                target[path[-1]] = float(target[path[-1]] + surface.PERTURBATION_DELTA_M)
                self.assertEqual(surface.perturb_prepared(self.prepared, parameter), expected)
                cage = surface.build_perturbed_cage(self.prepared, parameter)
                evaluation = surface.evaluate_perturbation(self.prepared, parameter)
                self.assertEqual(cage, evaluation.cage); surface.validate_evaluation(evaluation, expected)
                predicted = surface.predicted_support(self.prepared, component)
                movement = tuple(sum((evaluation.levels[1].vertices[i][axis] - baseline.vertices[i][axis]) ** 2 for axis in range(3)) ** .5 for i in range(1737))
                observed = tuple(i for i, value in enumerate(movement) if value > tolerance)
                self.assertTrue(predicted); self.assertEqual(predicted, observed)
                self.assertLessEqual(max((movement[i] for i in range(1737) if i not in predicted), default=0.0), tolerance)
        self.assertEqual(prepared_projection.canonical_json_bytes(self.prepared), original)

    def test_l0_lineage_fields_are_independently_admitted(self):
        cage = self.evaluation.cage
        formula_records = list(deepcopy(cage.formula_records)); formula_records[0]["formula_id"] = "forged"
        vertex_records = list(deepcopy(cage.vertex_records)); vertex_records[0]["contributor_domains"] = ()
        probes = {
            "formula_ids": replace(cage, formula_ids=("forged", *cage.formula_ids[1:])),
            "dependencies": replace(cage, dependencies=(("forged",), *cage.dependencies[1:])),
            "source_stencils": replace(cage, source_stencils=(cage.source_stencils[1], *cage.source_stencils[1:])),
            "formula_records": replace(cage, formula_records=tuple(formula_records)),
            "vertex_records": replace(cage, vertex_records=tuple(vertex_records)),
        }
        for name, forged in probes.items():
            with self.subTest(field=name), self.assertRaises(ValueError): surface.validate_level_structure(forged, self.prepared)
            with self.subTest(evaluation_field=name), self.assertRaises(ValueError): surface.validate_evaluation(surface.SurfaceEvaluation(forged, self.evaluation.levels), self.prepared)

    def test_l0_coordinates_are_independently_recomputed_from_prepared(self):
        cage = self.evaluation.cage; vertices = list(cage.vertices); records = deepcopy(cage.formula_records)
        vertices[0] = (float(vertices[0][0] + .01), *vertices[0][1:]); records[0]["coordinate"][0] = vertices[0][0]
        forged = replace(cage, vertices=tuple(vertices), formula_records=tuple(records))
        level1 = surface.subdivide(forged, 1); level2 = surface.subdivide(level1, 2)
        evaluation = surface.SurfaceEvaluation(forged, (level1, level2))
        with self.assertRaises(ValueError): surface.validate_level_structure(forged, self.prepared)
        with self.assertRaises(ValueError): surface.validate_evaluation(evaluation, self.prepared)

    def test_l1_l2_fields_are_exactly_parent_derived(self):
        meshes = [self.evaluation.cage, *self.evaluation.levels]
        for level in (1, 2):
            mesh = meshes[level]; quads = (mesh.quads[0][1:] + mesh.quads[0][:1], *mesh.quads[1:])
            triangles = tuple(item for face in quads for item in ((face[0], face[1], face[2]), (face[0], face[2], face[3])))
            loops = list(mesh.boundary_loops); name, loop = loops[0]; loops[0] = (name, loop[1:] + loop[:1])
            formula_records = list(deepcopy(mesh.formula_records)); formula_records[0]["formula_id"] = "forged"
            vertex_records = list(deepcopy(mesh.vertex_records)); vertex_records[0]["vertex_id"] = "forged"
            probes = {
                "cycles": replace(mesh, quads=quads, triangles=triangles),
                "coordinates": replace(mesh, vertices=((mesh.vertices[0][0] + .01, *mesh.vertices[0][1:]), *mesh.vertices[1:])),
                "loops": replace(mesh, boundary_loops=tuple(loops)),
                "formula_ids": replace(mesh, formula_ids=("forged", *mesh.formula_ids[1:])),
                "dependencies": replace(mesh, dependencies=(mesh.dependencies[0] + ("forged",), *mesh.dependencies[1:])),
                "formula_records": replace(mesh, formula_records=tuple(formula_records)),
                "vertex_records": replace(mesh, vertex_records=tuple(vertex_records)),
                "stencils": replace(mesh, source_stencils=(mesh.source_stencils[0] + (mesh.source_stencils[0][0],), *mesh.source_stencils[1:])),
                "triangles": replace(mesh, triangles=(mesh.triangles[1], mesh.triangles[0], *mesh.triangles[2:])),
            }
            for field, child in probes.items():
                with self.subTest(level=level, field=field), self.assertRaises(ValueError): surface.validate_level_structure(child, self.prepared, meshes[level - 1])
                forged = list(meshes); forged[level] = child
                with self.subTest(evaluation_level=level, evaluation_field=field), self.assertRaises(ValueError): surface.validate_evaluation(surface.SurfaceEvaluation(forged[0], tuple(forged[1:])), self.prepared)

    def test_independent_references_reject_coordinated_producer_defects(self):
        def bad_formula(prepared, control, producer=surface._formula_for_control): formula, dependencies, point, parameters = producer(prepared, control); return formula, dependencies, (float(point[0] + .01), point[1], point[2]), parameters
        with patch.object(surface, "_formula_for_control", side_effect=bad_formula), self.assertRaisesRegex(ValueError, "independent prepared reference"): surface.build_cage(self.prepared)
        def bad_subdivision(parent, level, points=None, producer=surface._subdivide_once): child = producer(parent, level, points); vertices = list(child.vertices); vertices[0] = (float(vertices[0][0] + .01), *vertices[0][1:]); return replace(child, vertices=tuple(vertices))
        with patch.object(surface, "_subdivide_once", side_effect=bad_subdivision), self.assertRaisesRegex(ValueError, "parent-derived vertices"): surface.subdivide(self.evaluation.cage, 1)
        def bad_record(level, vertex_id, contributors, formulas, producer=surface._record): return producer(level, vertex_id, contributors, formulas) | {"contributor_domains": ()}
        with patch.object(surface, "_record", side_effect=bad_record), self.assertRaisesRegex(ValueError, "parent-derived vertex_records"): surface.subdivide(self.evaluation.cage, 1)
class ChartLineageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.prepared = prepared()
        cls.evaluation = surface.evaluate(cls.prepared)
        cls.formulas = surface.formula_candidate_records(cls.prepared)
        cls.summary = chart.build_chart_summary(cls.evaluation, cls.formulas)

    def test_exact_closed_inventory_ids_and_source_boundary(self):
        summary = self.summary
        self.assertEqual([row["charts"] for row in summary["level_counts"]], [104, 416, 1664])
        self.assertEqual([row["interior_transitions"] for row in summary["level_counts"]], [189, 794, 3252])
        self.assertEqual((len(summary["chart_records"]), len(summary["transition_records"]),
                          len(summary["vertex_records"])), (2184, 4235, 2308))
        self.assertEqual([sum(row["level"] == level for row in summary["vertex_records"])
                          for level in range(3)], [120, 451, 1737])
        self.assertEqual([row["maximum_samples_per_vertex"] for row in summary["level_counts"]], [5, 5, 5])
        level2 = [row["chart_id"] for row in summary["chart_records"] if row["level"] == 2]
        self.assertEqual((level2[0], level2[-1]),
                         ("chart.q000/L2.s0.s0", "chart.q103/L2.s3.s3"))
        self.assertEqual(len({item for row in self.formulas
                              for item in row["geometry_dependencies"]}), 92)
        self.assertEqual(len(self.formulas), 120)
        self.assertLessEqual(max(len(row["geometry_dependencies"]) for row in self.formulas), 12)
        lines = (HERE / "chart_lineage.py").read_text(encoding="utf-8").count("\n")
        self.assertIn(lines, range(190, 269))
        self.assertLessEqual(Path(__file__).read_text(encoding="utf-8").count("\n"), 400)

    def test_domain_cycle_rejects_disconnected_open_shared_boundary(self):
        self.assertRaisesRegex(chart.ChartLineageError, "a junction is not one closed trace", chart._domain_cycle, {(0, 1): (0, 1), (2, 3): (2, 3)}, {(0, 1), (2, 3)})

    def test_summary_rejects_closed_schema_duplicate_and_lineage_forgeries(self):
        def extra(value):
            value["unexpected"] = None
        def open_chart(value):
            value["chart_records"][0]["unexpected"] = None
        def open_transition(value):
            value["transition_records"][0]["unexpected"] = None
        def open_vertex(value):
            value["vertex_records"][0]["unexpected"] = None
        def duplicate_chart(value):
            value["chart_records"][0] = value["chart_records"][1]
        def rotate_cycle(value):
            corners = value["chart_records"][1]["corners"]
            value["chart_records"][1]["corners"] = corners[1:] + corners[:1]
        def forge_l2_id(value):
            value["chart_records"][5]["chart_id"] = "chart.q000/L1.s0/L2.s0"
        def forge_uv(value):
            value["chart_records"][5]["corners"][0]["u"]["denominator"] = 3
        def duplicate_transition(value):
            value["transition_records"][0] = value["transition_records"][1]
        def duplicate_vertex(value):
            value["vertex_records"][0] = value["vertex_records"][1]
        def empty_samples(value):
            value["vertex_records"][0]["samples"] = []
        def forge_contributor(value):
            value["vertex_records"][-1]["base_control_contributors"] = ["c000"]
        probes = (extra, open_chart, open_transition, open_vertex, duplicate_chart,
                  rotate_cycle, forge_l2_id, forge_uv, duplicate_transition,
                  duplicate_vertex, empty_samples, forge_contributor)
        for mutate in probes:
            forged = deepcopy(self.summary)
            mutate(forged)
            with self.subTest(probe=mutate.__name__), self.assertRaises(chart.ChartLineageError):
                chart.validate_chart_summary(forged, self.evaluation, self.formulas)

    def test_formula_inventory_schema_owner_dependency_and_coordinate_forgeries(self):
        def extra(value):
            value[0]["unexpected"] = None
        def duplicate(value):
            value[1] = deepcopy(value[0])
        def owner(value):
            value[0]["construction_owner"] = "domain.thorax"
        def dependencies(value):
            value[0]["geometry_dependencies"] = [f"forged.{i}" for i in range(13)]
        def dependency_universe(value):
            deps = set(value[0]["geometry_dependencies"])
            deps.remove(min(deps))
            deps.add("stations.forged.C.x")
            value[0]["geometry_dependencies"] = sorted(deps)
        def coordinate(value):
            value[0]["coordinate"][0] = float("nan")
        for mutate in (extra, duplicate, owner, dependencies, dependency_universe, coordinate):
            forged = list(deepcopy(self.formulas))
            mutate(forged)
            with self.subTest(probe=mutate.__name__), self.assertRaises(chart.ChartLineageError):
                chart.build_chart_summary(self.evaluation, tuple(forged))
        with self.assertRaises(chart.ChartLineageError):
            chart.build_chart_summary(self.evaluation, self.formulas[:-1])

    def test_neutral_topology_and_junction_candidates_are_independently_checked(self):
        level1 = self.evaluation.levels[0]
        faces = list(level1.quads)
        faces[0] = faces[0][1:] + faces[0][:1]
        forged = surface.SurfaceEvaluation(self.evaluation.cage,
                                            (replace(level1, quads=tuple(faces)), self.evaluation.levels[1]))
        with self.assertRaises(chart.ChartLineageError):
            chart.build_chart_summary(forged, self.formulas)
        traces = list(deepcopy(surface.junction_trace_inputs()))
        traces[0]["base_control_ids"] = traces[0]["base_control_ids"][1:]
        with patch.object(surface, "junction_trace_inputs", return_value=tuple(traces)), self.assertRaises(chart.ChartLineageError):
            chart.build_chart_summary(self.evaluation, self.formulas)
        junction = surface.junction_trace_inputs()[0]["junction_id"]
        tags = list(surface.propagate_junction_tags(self.evaluation, junction))
        tags[0] = dict(tags[0])
        tags[0].pop(next(iter(tags[0])))
        with patch.object(surface, "propagate_junction_tags", return_value=tuple(tags)), self.assertRaises(chart.ChartLineageError):
            chart.build_chart_summary(self.evaluation, self.formulas)

    def test_chart_uses_public_neutral_inputs_not_private_surface_oracles(self):
        with patch.object(surface, "_formula_for_control", side_effect=AssertionError("private oracle")):
            rebuilt = chart.build_chart_summary(self.evaluation, self.formulas)
        self.assertEqual(rebuilt, self.summary)
        source = (HERE / "chart_lineage.py").read_text(encoding="utf-8")
        self.assertNotIn("surface._", source)
        chart.validate_chart_summary(rebuilt, self.evaluation, self.formulas)


class AnatomyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.prepared = prepared()
        cls.evaluation = surface.evaluate(cls.prepared)
        cls.charts = independent_charts(cls.evaluation)

    def test_independent_selectors_and_exact_anatomy_inventory(self):
        levels = anatomy.validate_evaluated_surface(self.evaluation, self.charts, prepared=self.prepared)
        self.assertEqual(len(levels), 3)
        self.assertEqual(anatomy.validate_evaluated_surface(self.evaluation, self.charts), levels)
        self.assertEqual(len(anatomy.select_trace(self.evaluation, "port.neck", 2, self.charts, prepared=self.prepared)), 24)
        measures = anatomy.measure_anatomy(self.evaluation, self.prepared, self.charts)
        self.assertEqual(len(measures), 78)
        self.assertEqual(len(anatomy.anatomy_threshold_records()), 78)
        self.assertEqual(len(anatomy.anatomy_gate_records(self.evaluation, self.prepared, self.charts)), 78)
        self.assertGreater(measures["anatomy.pelvic_lateral_ratio.left.L2"]["omitted_count"], 0)

    def test_forged_chart_ancestry_and_corner_incidence_fail_closed(self):
        mutations = []
        records = lambda value, level: [row for row in value["chart_records"] if row["level"] == level]
        bad = deepcopy(self.charts); records(bad, 0)[0]["construction_owner"] = "domain.thorax"; mutations.append(bad)
        bad = deepcopy(self.charts); records(bad, 2)[0]["base_face_id"] = "q001"; mutations.append(bad)
        bad = deepcopy(self.charts); records(bad, 1)[0]["corners"][0]["vertex_id"] = "vertex.L1.v0001"; mutations.append(bad)
        bad = deepcopy(self.charts); bad["chart_records"].pop(); mutations.append(bad)
        for forged in mutations:
            with self.assertRaises(anatomy.AnatomyGateError): anatomy.measure_anatomy(self.evaluation, self.prepared, forged)

    def test_chart_levels_require_exact_bounded_integers(self):
        boolean = deepcopy(self.charts); boolean["chart_records"][0]["level"] = False
        surplus = deepcopy(self.charts); extra = deepcopy(surplus["chart_records"][-1])
        extra["chart_id"], extra["level"] = "chart.q999/L3.s0.s0.s0", 3; surplus["chart_records"].append(extra)
        for name, forged in (("boolean", boolean), ("surplus", surplus)):
            with self.subTest(probe=name), self.assertRaises(anatomy.AnatomyGateError): anatomy.validate_evaluated_surface(self.evaluation, forged, prepared=self.prepared)

    def test_shoulder_selection_uses_face_ancestry_not_vertex_records(self):
        altered = []
        for mesh in (self.evaluation.cage, *self.evaluation.levels):
            altered.append(replace(mesh, vertex_records=tuple({"base_control_contributors": (), "geometry_dependency_union": (), "contributor_domains": ()} for _ in mesh.vertex_records)))
        forged = surface.SurfaceEvaluation(altered[0], tuple(altered[1:]))
        original = anatomy.measure_anatomy(self.evaluation, self.prepared, self.charts)
        with patch.object(surface, "validate_evaluation", return_value=tuple(altered)):
            self.assertEqual(anatomy.measure_anatomy(forged, self.prepared, self.charts), original)

    def test_frozen_thresholds_resist_hostile_runtime_reassignment(self):
        expected = anatomy.anatomy_threshold_records(), anatomy.anatomy_gate_records(self.evaluation, self.prepared, self.charts), anatomy.run_production_axillary_fixtures()
        with patch.object(anatomy, "THRESHOLD", -1e9), patch.object(anatomy, "_TURN", -1e9), patch.object(anatomy, "_STRETCH", 1e9):
            self.assertEqual((anatomy.anatomy_threshold_records(), anatomy.anatomy_gate_records(self.evaluation, self.prepared, self.charts), anatomy.run_production_axillary_fixtures()), expected)
            self.assertEqual((anatomy.evaluate_axillary_scalars(float.fromhex("0x1.9999999999999p-5"), 1.0).passed, anatomy.evaluate_axillary_scalars(1.0, float.fromhex("0x1.4000000000001p+1")).passed), (False, False))


class ProductionAxillaryFixtureTests(unittest.TestCase):
    def test_contract_fixture_matrix(self):
        rows = anatomy.run_production_axillary_fixtures()
        self.assertEqual(len(rows), 13); self.assertEqual(tuple(row["fixture_id"] for row in rows), anatomy.AXILLARY_FIXTURE_IDS)
        self.assertEqual([row["outcome"] for row in rows[:3]], ["pass", "pass", "fail"]); self.assertEqual([row["outcome"] for row in rows[3:6]], ["hard-failure"] * 3)
        self.assertEqual(rows[6]["stage"], 9); self.assertEqual([row["outcome"] for row in rows[7:]], ["fail", "pass", "pass", "pass", "pass", "fail"])

    def test_failure_order_and_exact_boundary_comparators(self):
        with self.assertRaisesRegex(ValueError, "step 3"):
            anatomy.evaluate_axillary_predicate("left", (0.0, 0.0, 0.0), (0.0, 0.0, 0.0), (1.0, 0.0, 0.0))
        self.assertEqual((anatomy.evaluate_axillary_scalars(float.fromhex("0x1.9999999999999p-5"), 1.0).passed, anatomy.evaluate_axillary_scalars(float.fromhex("0x1.999999999999ap-5"), 1.0).passed, anatomy.evaluate_axillary_scalars(1.0, float.fromhex("0x1.4000000000001p+1")).passed), (False, True, False))
if __name__ == "__main__":
    unittest.main()
