"""Focused tests for the initial connected coarse-arm candidate."""
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

import arm_construction  # noqa: E402
import checks  # noqa: E402
import collision_broadphase  # noqa: E402
import construction  # noqa: E402


INPUTS = json.loads((HERE / "inputs.json").read_text(encoding="utf-8"))
ARM_INPUTS = json.loads((HERE / "arm-inputs.json").read_text(encoding="utf-8"))
EXPECTED = ("calibrated_ordinary_human", "calibrated_upright_anthropomorphic")


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_reference(row, name):
    ref = row[name]
    path = Path(ref["path"])
    if _sha(path) != ref["sha256"]:
        raise AssertionError(f"immutable {name} identity drifted: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _cases():
    arm_rows = {row["case_id"]: row["sides"] for row in ARM_INPUTS["cases"]}
    result = []
    for row in INPUTS["cases"]:
        if row["id"] not in EXPECTED:
            continue
        root = _load_reference(row, "root_mesh")
        source = _load_reference(row, "original_case")
        base = construction.build(root, row["leg_inputs"])
        arms = arm_construction.build(base, source, arm_rows[row["id"]])
        levels = arm_construction.evaluate(arms, levels=2)
        result.append((row["id"], base, source, arm_rows[row["id"]], arms, levels))
    if tuple(row[0] for row in result) != EXPECTED:
        raise AssertionError("canonical arm cases were not loaded")
    return result


def _triangles(quads):
    return [triangle for face in quads
            for triangle in ((face[0], face[1], face[2]), (face[0], face[2], face[3]))]


class ArmConstructionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases = _cases()

    def test_actual_cases_evaluate_with_complete_stencils(self):
        self.assertEqual(len(self.cases), 2)
        for case_id, base, _source, _inputs, arms, levels in self.cases:
            with self.subTest(case=case_id):
                self.assertEqual(len(arms["vertices"]), len(base["vertices"]) + 178)
                self.assertEqual(len(arms["quads"]), len(base["quads"]) + 184)
                self.assertEqual([level["metadata"]["level"] for level in levels], [0, 1, 2])
                for level in levels:
                    self.assertEqual(len(level["base_stencils"]), len(level["vertices"]))
                    for stencil in level["base_stencils"]:
                        self.assertAlmostEqual(sum(float(term[1]) for term in stencil), 1.0, places=9)
                        self.assertTrue(all(term[1] > 0.0 for term in stencil))

    def test_prefix_closure_and_source_owned_port(self):
        for _case_id, base, source, _inputs, arms, _levels in self.cases:
            self.assertEqual(arms["vertices"][:len(base["vertices"])], base["vertices"])
            self.assertEqual(arms["quads"][:len(base["quads"])], base["quads"])
            self.assertNotIn("port.left_arm", arms["loops"])
            self.assertNotIn("port.right_arm", arms["loops"])
            for side in ("left", "right"):
                row = arms["metadata"]["arms"][side]
                components = source["components"]
                J = [components[f"shoulders.{side}.arm_origin.{axis}"] for axis in "xyz"]
                self.assertEqual(row["J"], J)
                self.assertEqual(row["J_source"], f"shoulders.{side}.arm_origin")
                self.assertTrue(row["collar"]["exact_port_translation"])
                self.assertEqual(len(row["source_port"]["section_frame_phase"]), 8)
                self.assertEqual(len(row["new_vertex_indices"]), 89)
                self.assertEqual(len(row["new_face_indices"]), 92)

    def test_stale_source_origin_rejects_instead_of_becoming_duplicate_J(self):
        _case_id, base, source, inputs, _arms, _levels = self.cases[0]
        changed = copy.deepcopy(source)
        changed["components"]["shoulders.left.arm_origin.x"] -= 0.001
        with self.assertRaisesRegex(arm_construction.ArmConstructionError, "does not own"):
            arm_construction.build(base, changed, inputs)
        self.assertNotIn("J", inputs["left"])

    def test_frames_are_right_handed_front_facing_and_mirrored(self):
        for tangent in ((-1.0, -1.0e-10, 1.0e-10),
                        (1.0, -1.0e-10, 1.0e-10)):
            frame = arm_construction._frame(tangent)
            t, u, f = frame["tangent"], frame["U"], frame["F"]
            cross = arm_construction._cross(t, u)
            self.assertGreater(sum(cross[i] * f[i] for i in range(3)), 1.0 - 1.0e-7)
            self.assertGreaterEqual(f[2], 0.0)
            self.assertAlmostEqual(sum(t[i] * u[i] for i in range(3)), 0.0, places=8)
        for _case_id, _base, _source, _inputs, arms, _levels in self.cases:
            left = arms["metadata"]["arms"]["left"]["sections"][0]["frame"]
            right = arms["metadata"]["arms"]["right"]["sections"][0]["frame"]
            self.assertLess(left["tangent"][0], 0.0)
            self.assertGreater(right["tangent"][0], 0.0)
            self.assertGreaterEqual(left["F"][2], 0.0)
            self.assertGreaterEqual(right["F"][2], 0.0)

    def test_collar_distance_and_upper_length_use_source_J(self):
        for _case_id, _base, _source, _inputs, arms, _levels in self.cases:
            for side in ("left", "right"):
                row = arms["metadata"]["arms"][side]
                J, P, E = row["J"], row["P"], row["E"]
                C = row["collar"]["centre"]
                distance = lambda a, b: math.sqrt(sum((a[i] - b[i]) ** 2 for i in range(3)))
                self.assertAlmostEqual(distance(C, P), 0.6 * distance(P, J), places=10)
                self.assertAlmostEqual(row["bone_lengths"]["upper_J_E"], distance(J, E), places=12)
                self.assertAlmostEqual(row["bone_lengths"]["visible_P_E"], distance(P, E), places=12)
                self.assertGreater(row["bone_lengths"]["upper_J_E"], row["bone_lengths"]["visible_P_E"])

    def test_E_W_radii_and_hand_length_have_independent_geometric_response(self):
        _case_id, base, source, inputs, baseline, _levels = self.cases[0]
        mutations = (("E", 1, -0.007, "elbow"), ("W", 2, 0.006, "wrist"))
        for field, axis, delta, section in mutations:
            changed = copy.deepcopy(inputs)
            changed["left"][field][axis] += delta
            output = arm_construction.build(base, source, changed)
            before = next(row for row in baseline["metadata"]["arms"]["left"]["sections"] if row["name"] == section)
            after = next(row for row in output["metadata"]["arms"]["left"]["sections"] if row["name"] == section)
            self.assertAlmostEqual(after["centre"][axis] - before["centre"][axis], delta, places=12)
        changed = copy.deepcopy(inputs)
        changed["left"]["radii"]["forearm"][0] += 0.004
        output = arm_construction.build(base, source, changed)
        before = next(row for row in baseline["metadata"]["arms"]["left"]["sections"] if row["name"] == "forearm_belly")
        after = next(row for row in output["metadata"]["arms"]["left"]["sections"] if row["name"] == "forearm_belly")
        self.assertAlmostEqual(after["radii_up_forward"][0] - before["radii_up_forward"][0], 0.004, places=12)
        changed = copy.deepcopy(inputs)
        changed["left"]["hand_length"] += 0.010
        output = arm_construction.build(base, source, changed)
        before = baseline["metadata"]["arms"]["left"]["cap"]["centre"]
        after = output["metadata"]["arms"]["left"]["cap"]["centre"]
        self.assertAlmostEqual(math.sqrt(sum((after[i] - before[i]) ** 2 for i in range(3))), 0.010, places=10)

    def test_actual_L2_has_no_quad_folds_or_intersections_by_existing_checkers(self):
        for case_id, _base, _source, _inputs, _arms, levels in self.cases:
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
