"""Focused tests for the six-phase connected head candidate."""
from __future__ import annotations

import copy
import hashlib
import json
import math
from pathlib import Path
import sys
import unittest


HERE = Path(__file__).resolve().parents[1]
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import checks  # noqa: E402
import collision_broadphase  # noqa: E402
import construction  # noqa: E402
import head_construction  # noqa: E402


INPUTS = json.loads((HERE / "inputs.json").read_text(encoding="utf-8"))
HEAD_INPUTS = json.loads((HERE / "head-inputs.json").read_text(encoding="utf-8"))
HEAD_REFINEMENT = HERE / "head-refinement-inputs.json"
EXPECTED = ("calibrated_ordinary_human", "calibrated_upright_anthropomorphic")


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load(row, field):
    ref = row[field]
    path = Path(ref["path"])
    if _sha(path) != ref["sha256"]:
        raise AssertionError(f"immutable {field} identity drifted: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _cases():
    controls = {row["case_id"]: row["head"] for row in HEAD_INPUTS["cases"]}
    result = []
    for row in INPUTS["cases"]:
        if row["id"] not in EXPECTED:
            continue
        root, source = _load(row, "root_mesh"), _load(row, "original_case")
        base = construction.build(root, row["leg_inputs"])
        head = head_construction.build(base, source, controls[row["id"]])
        levels = head_construction.evaluate(head, levels=2)
        result.append((row["id"], base, source, controls[row["id"]], head, levels))
    if tuple(row[0] for row in result) != EXPECTED:
        raise AssertionError("canonical head cases were not loaded")
    return result


def _triangles(quads):
    return [triangle for face in quads for triangle in
            ((face[0], face[1], face[2]), (face[0], face[2], face[3]))]


def _fixed_l2_domain(mesh, support):
    support = set(support)
    return [index for index, stencil in enumerate(mesh["base_stencils"])
            if any(int(term[0]) in support for term in stencil)]


def _axis_extent(mesh, indices, axis, maximum_only=False):
    values = [mesh["vertices"][index][axis] for index in indices]
    return max(values) if maximum_only else max(values) - min(values)


class HeadConstructionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases = _cases()

    def test_actual_cases_evaluate_with_complete_stencils(self):
        for case_id, _base, _source, _controls, head, levels in self.cases:
            with self.subTest(case=case_id):
                self.assertEqual([level["metadata"]["level"] for level in levels], [0, 1, 2])
                for level in levels:
                    self.assertEqual(len(level["vertices"]), len(level["base_stencils"]))
                    for stencil in level["base_stencils"]:
                        self.assertAlmostEqual(sum(float(term[1]) for term in stencil), 1.0, places=9)
                        self.assertTrue(all(term[1] > 0.0 for term in stencil))
                self.assertNotIn("port.neck", head["loops"])

    def test_inherited_prefix_closure_and_source_owned_phase(self):
        expected_phase = {(-1.0, -1.0), (1.0, -1.0), (1.0, 0.0),
                          (1.0, 1.0), (-1.0, 1.0), (-1.0, 0.0)}
        for _case_id, base, source, _controls, head, _levels in self.cases:
            self.assertEqual(head["vertices"][:len(base["vertices"])], base["vertices"])
            self.assertEqual(head["quads"][:len(base["quads"])], base["quads"])
            meta = head["metadata"]["head"]
            self.assertEqual({tuple(pair) for pair in meta["neck_phase"]}, expected_phase)
            centre = [source["components"][f"stations.neck_upper.C.{axis}"] for axis in "xyz"]
            first = meta["stations"][0]["centre"]
            self.assertEqual(first[0], centre[0]); self.assertEqual(first[2], centre[2])

    def test_binding_handoff_is_source_owned_and_matches_exact_allocations(self):
        for _case_id, _base, source, _controls, head, _levels in self.cases:
            meta = head["metadata"]["head"]
            handoff = meta["binding_handoff"]
            expected_pivot = [
                source["components"][f"stations.neck_collar.C.{axis}"]
                for axis in "xyz"
            ]
            support = next(row for row in meta["stations"]
                           if row["name"] == "neck_support")
            self.assertEqual(handoff["joint"], "neck_head")
            self.assertEqual(handoff["pivot_source"], "stations.neck_collar.C")
            self.assertEqual(handoff["pivot"], expected_pivot)
            self.assertEqual(handoff["consumed_neck_port_indices"],
                             meta["neck_port_indices"])
            self.assertEqual(handoff["neck_support_ring_indices"], support["indices"])
            self.assertEqual(handoff["head_new_vertex_indices"],
                             meta["new_vertex_indices"])
            self.assertEqual(handoff["feature_new_vertex_indices"],
                             meta["feature_vertex_indices"])

    def test_stale_source_neck_rejects(self):
        _case_id, base, source, controls, _head, _levels = self.cases[0]
        changed = copy.deepcopy(source)
        changed["components"]["stations.neck_upper.rL"] += 0.001
        with self.assertRaisesRegex(head_construction.HeadConstructionError, "source neck radii"):
            head_construction.build(base, changed, controls)

    def test_optional_features_are_generic_and_connected(self):
        human, anthro = self.cases
        self.assertFalse(human[4]["metadata"]["head"]["features"]["muzzle"]["enabled"])
        self.assertFalse(human[4]["metadata"]["head"]["features"]["ears"]["enabled"])
        features = anthro[4]["metadata"]["head"]["features"]
        self.assertTrue(features["muzzle"]["enabled"])
        self.assertTrue(features["ears"]["enabled"])
        self.assertEqual(set(features["ears"]["sides"]), {"left", "right"})
        self.assertNotIn("case_id", anthro[3])

    def test_ear_sections_are_broad_X_thin_Z_right_handed_and_mirrored(self):
        features = self.cases[1][4]["metadata"]["head"]["features"]["ears"]["sides"]
        for side in ("left", "right"):
            row = features[side]
            axis, broad, depth = (row["frame"][name] for name in ("axis", "broad", "depth"))
            cross = head_construction._cross(tuple(axis), tuple(broad))
            self.assertGreater(sum(cross[i] * depth[i] for i in range(3)), 1.0 - 1.0e-7)
            self.assertGreater(abs(broad[0]), 0.95)
            self.assertGreater(abs(depth[2]), 0.95)
            self.assertEqual(len(set(tuple(pair) for pair in row["host_phase"])), 4)
            self.assertGreater(row["controls"]["base_halfwidth_x"], row["controls"]["base_halfdepth_z"])
        self.assertLess(features["left"]["frame"]["axis"][0], 0.0)
        self.assertGreater(features["right"]["frame"]["axis"][0], 0.0)

    def _assert_l0_to_l2_response(self, baseline_l0, baseline_l2, changed_l0,
                                  l0_support, measurement_support, axis,
                                  maximum_only=False):
        self.assertEqual(changed_l0["quads"], baseline_l0["quads"])
        changed_l2 = head_construction.evaluate(changed_l0, levels=2)[-1]
        self.assertEqual(changed_l2["quads"], baseline_l2["quads"])
        self.assertEqual(changed_l2["base_stencils"], baseline_l2["base_stencils"])

        support = set(l0_support)
        l0_delta = [[changed_l0["vertices"][index][component] -
                     baseline_l0["vertices"][index][component]
                     for component in range(3)]
                    for index in range(len(baseline_l0["vertices"]))]
        self.assertGreater(max(abs(value) for index in support for value in l0_delta[index]),
                           100.0 * math.ulp(1.0))
        self.assertEqual(
            max((abs(value) for index, row in enumerate(l0_delta)
                 if index not in support for value in row), default=0.0),
            0.0,
        )

        domain = _fixed_l2_domain(baseline_l2, support)
        self.assertTrue(domain)
        max_transfer_error = 0.0
        for vertex_index in domain:
            expected = [sum(float(coefficient) * l0_delta[int(base_index)][component]
                            for base_index, coefficient in
                            baseline_l2["base_stencils"][vertex_index])
                        for component in range(3)]
            actual = [changed_l2["vertices"][vertex_index][component] -
                      baseline_l2["vertices"][vertex_index][component]
                      for component in range(3)]
            max_transfer_error = max(
                max_transfer_error,
                max(abs(actual[component] - expected[component])
                    for component in range(3)),
            )
        self.assertLessEqual(max_transfer_error, 1.0e-12)

        measurement_domain = _fixed_l2_domain(baseline_l2, measurement_support)
        before = _axis_extent(baseline_l2, measurement_domain, axis, maximum_only)
        after = _axis_extent(changed_l2, measurement_domain, axis, maximum_only)
        self.assertGreater(after - before, 100.0 * math.ulp(max(abs(before), 1.0)))

    def test_declared_controls_reach_actual_l0_and_evaluated_l2_surface(self):
        for case_id, base, source, controls, baseline_l0, levels in self.cases:
            with self.subTest(case=case_id, control="stations.cheek.radii[0]"):
                baseline_l2 = levels[-1]
                cheek = next(row for row in baseline_l0["metadata"]["head"]["stations"]
                             if row["name"] == "cheek")["indices"]
                support = set(cheek)
                muzzle = baseline_l0["metadata"]["head"]["features"]["muzzle"]
                if muzzle["enabled"]:
                    support.update(muzzle["support_indices"])
                    support.update(muzzle["tip_indices"])
                changed = copy.deepcopy(controls)
                changed["stations"]["cheek"]["radii"][0] += 0.004
                changed_l0 = head_construction.build(base, source, changed)
                self._assert_l0_to_l2_response(
                    baseline_l0, baseline_l2, changed_l0, support, cheek, axis=0)

        _case_id, base, source, controls, baseline_l0, levels = self.cases[1]
        baseline_l2 = levels[-1]
        features = baseline_l0["metadata"]["head"]["features"]
        muzzle = features["muzzle"]
        muzzle_support = set(muzzle["support_indices"] + muzzle["tip_indices"])
        changed = copy.deepcopy(controls)
        changed["muzzle"]["length"] += 0.010
        self._assert_l0_to_l2_response(
            baseline_l0, baseline_l2,
            head_construction.build(base, source, changed),
            muzzle_support, muzzle_support, axis=2, maximum_only=True)

        ears = features["ears"]["sides"]
        ear_sections = {
            side: {index for ring in ears[side]["section_indices"] for index in ring}
            for side in ("left", "right")
        }
        all_sections = ear_sections["left"] | ear_sections["right"]
        all_ear_vertices = all_sections | {
            index for side in ("left", "right")
            for index in ears[side]["attachment_indices"]
        }
        for control, amount, support, axis in (
            ("base_halfwidth_x", 0.003, all_sections, 0),
            ("base_halfdepth_z", 0.002, all_sections, 2),
            ("tip_up", 0.010, all_ear_vertices, 1),
        ):
            with self.subTest(case=_case_id, control=f"ears.{control}"):
                changed = copy.deepcopy(controls)
                changed["ears"][control] += amount
                changed_l0 = head_construction.build(base, source, changed)
                self._assert_l0_to_l2_response(
                    baseline_l0, baseline_l2, changed_l0,
                    support, support, axis=axis)

    def test_refined_muzzle_support_dimensions_reach_actual_l2_semantic_support(self):
        # Capture-only geometry regression: this method is intentionally not
        # run before the new source/input snapshot is created.
        _case_id, base, source, _legacy_controls, _legacy_l0, _legacy_levels = self.cases[1]
        refined_controls = head_construction.head_inputs_for_refinement(
            HEAD_REFINEMENT, "calibrated_upright_anthropomorphic"
        )
        baseline_l0 = head_construction.build(base, source, refined_controls)
        baseline_l2 = head_construction.evaluate(baseline_l0, levels=2)[-1]
        muzzle = baseline_l0["metadata"]["head"]["features"]["muzzle"]
        support = set(muzzle["support_indices"])
        self.assertEqual(muzzle["support_source"], "explicit")
        for field, amount, axis in (
            ("support_halfwidth", 0.007, 0),
            ("support_halfheight", 0.006, 1),
        ):
            with self.subTest(control=f"muzzle.{field}"):
                changed = copy.deepcopy(refined_controls)
                changed["muzzle"][field] += amount
                self._assert_l0_to_l2_response(
                    baseline_l0,
                    baseline_l2,
                    head_construction.build(base, source, changed),
                    support,
                    support,
                    axis=axis,
                )

    def test_actual_L2_has_no_quad_folds_or_intersections_by_existing_checkers(self):
        for case_id, _base, _source, _controls, _head, levels in self.cases:
            mesh = levels[2]
            dots = []
            for face in mesh["quads"]:
                first = checks._triangle_normal(mesh["vertices"], (face[0], face[1], face[2]))
                second = checks._triangle_normal(mesh["vertices"], (face[0], face[2], face[3]))
                denominator = checks._norm(first) * checks._norm(second)
                dots.append(checks._dot(first, second) / denominator if denominator > 0.0 else -1.0)
            with self.subTest(case=case_id, check="fold"):
                self.assertGreater(min(dots), 0.0)
            collision = collision_broadphase.collision_report(mesh["vertices"], _triangles(mesh["quads"]))
            with self.subTest(case=case_id, check="collision"):
                self.assertTrue(collision["available"])
                self.assertTrue(collision["pair_partition_complete"])
                self.assertTrue(collision["final_classification_partition_complete"])
                self.assertEqual(collision["intersection_hit_count"], 0)


if __name__ == "__main__":
    unittest.main()
