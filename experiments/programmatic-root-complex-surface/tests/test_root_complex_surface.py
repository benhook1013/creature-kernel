from __future__ import annotations

from copy import deepcopy
from dataclasses import FrozenInstanceError
from pathlib import Path
import sys
import unittest

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import root_complex_surface as surface  # noqa: E402


def synthetic_prepared():
    def station(center, radius, front, back, name):
        return {
            "center": center,
            "lateral_radius": radius,
            "front_extent": front,
            "back_extent": back,
            "provenance": f"synthetic.station.{name}",
        }

    def landmark(point, name):
        return {"point": point, "provenance": f"synthetic.landmark.{name}"}

    def scalar(value, name):
        return {"value": value, "provenance": f"synthetic.scalar.{name}"}

    stations = {
        "neck_collar": station((0.0, 3.1, 0.0), 0.55, 0.42, 0.36, "neck"),
        "upper_ribcage_shoulder": station((0.0, 2.45, 0.0), 1.45, 0.82, 0.67, "upper_rib"),
        "lower_ribcage": station((0.0, 1.55, 0.0), 1.28, 0.73, 0.65, "lower_rib"),
        "waist_abdomen": station((0.0, 0.72, 0.0), 0.94, 0.58, 0.55, "waist"),
        "lower_abdomen": station((0.0, 0.28, 0.0), 1.03, 0.62, 0.58, "abdomen"),
        "upper_pelvis": station((0.0, 0.02, 0.0), 1.37, 0.72, 0.66, "upper_pelvis"),
        "lower_pelvis": station((0.0, -0.68, 0.0), 1.20, 0.66, 0.61, "lower_pelvis"),
    }
    landmarks = {}
    for side, sign in (("left", -1.0), ("right", 1.0)):
        landmarks[f"shoulder_peak_{side}"] = landmark(
            (sign * 1.38, 2.55, 0.0), f"shoulder_peak_{side}")
        landmarks[f"axilla_{side}"] = landmark(
            (sign * 1.25, 1.76, 0.0), f"axilla_{side}")
        landmarks[f"thigh_start_{side}"] = landmark(
            (sign * 0.78, -0.70, 0.0), f"thigh_start_{side}")
        landmarks[f"thigh_mid_{side}"] = landmark(
            (sign * 0.82, -1.85, 0.03), f"thigh_mid_{side}")
    return {
        "stations": stations,
        "landmarks": landmarks,
        "frames": {"body": {
            "lateral_axis": (1.0, 0.0, 0.0),
            "up_axis": (0.0, 1.0, 0.0),
            "forward_axis": (0.0, 0.0, 1.0),
            "provenance": "synthetic.frame.body",
        }},
        "scalars": {
            "arm_root_depth": scalar(0.34, "arm_root_depth"),
            "arm_root_outward": scalar(0.22, "arm_root_outward"),
            "thigh_lateral_radius": scalar(0.70, "thigh_lateral_radius"),
            "thigh_depth": scalar(0.42, "thigh_depth"),
        },
        "provenance": "synthetic.prepared.root",
    }


class SymbolicTopologyTests(unittest.TestCase):
    def test_exact_counts_loops_euler_orientation_and_valences(self):
        ids, quads, loops = surface.symbolic_topology()
        report = surface.validate_topology(len(ids), quads, loops, surface.EXPECTED_VALENCES)
        self.assertEqual((report.vertex_count, report.edge_count, report.face_count), (64, 122, 55))
        self.assertEqual(report.boundary_edge_count, 24)
        self.assertEqual(report.boundary_lengths, (8, 4, 4, 4, 4))
        self.assertEqual(report.euler, -3)
        self.assertEqual(report.valence_inventory, ((3, 22), (4, 32), (5, 10)))
        self.assertEqual(loops, (("neck", (0, 1, 2, 3, 4, 5, 6, 7)),
                                 ("left_arm", (48, 51, 50, 49)),
                                 ("right_arm", (52, 55, 54, 53)),
                                 ("left_thigh", (56, 59, 58, 57)),
                                 ("right_thigh", (60, 61, 62, 63))))
        uses = {}
        for face in quads:
            for a, b in zip(face, face[1:] + face[:1]):
                uses.setdefault(tuple(sorted((a, b))), []).append((a, b))
        self.assertTrue(all(len(value) in (1, 2) for value in uses.values()))
        self.assertTrue(all(value[0] == tuple(reversed(value[1]))
                            for value in uses.values() if len(value) == 2))

    def test_validator_rejects_bad_quad_and_boundary_declaration(self):
        ids, quads, loops = surface.symbolic_topology()
        with self.assertRaisesRegex(ValueError, "quad index"):
            surface.validate_topology(len(ids), quads[:-1] + ((0, 1, 2, 99),), loops)
        with self.assertRaisesRegex(ValueError, "declared boundary"):
            surface.validate_topology(len(ids), quads, loops[:-1])
        reversed_loop = list(loops)
        reversed_loop[1] = ("left_arm", tuple(reversed(loops[1][1])))
        with self.assertRaisesRegex(ValueError, "directed winding"):
            surface.validate_topology(len(ids), quads, tuple(reversed_loop))


class FormulaAndInputTests(unittest.TestCase):
    def test_plain_mapping_build_has_complete_immutable_records(self):
        cage = surface.build_cage(synthetic_prepared())
        self.assertEqual((len(cage.vertices), len(cage.quads)), (64, 55))
        self.assertEqual(len(set(cage.control_ids)), 64)
        self.assertEqual(len(cage.formula_ids), 64)
        self.assertTrue(all(item for item in cage.dependencies))
        self.assertTrue(all(item for item in cage.provenance_ids))
        self.assertEqual(set(cage.formula_ids), {
            "station.asymmetric_superellipse", "iliac.blend.superellipse",
            "shoulder.peak_axilla_collar", "thigh.seat_gap_loop",
        })
        with self.assertRaises(FrozenInstanceError):
            cage.vertices = ()

    def test_named_boundaries_and_shoulder_offsets_use_canonical_sides(self):
        prepared = synthetic_prepared()
        cage = surface.build_cage(prepared)
        lateral = np.array((1.0, 0.0, 0.0))
        forward = np.array((0.0, 0.0, 1.0))
        for side, sign, arm, thigh in (("left", -1, 48, 56), ("right", 1, 52, 60)):
            arm_centroid = np.mean(cage.vertices[arm:arm + 4], axis=0)
            thigh_centroid = np.mean(cage.vertices[thigh:thigh + 4], axis=0)
            self.assertGreater(sign * float(np.dot(arm_centroid, lateral)), 0.0)
            self.assertGreater(sign * float(np.dot(thigh_centroid, lateral)), 0.0)
            peak = np.asarray(prepared["landmarks"][f"shoulder_peak_{side}"]["point"])
            upper = np.mean(cage.vertices[arm:arm + 2], axis=0)
            self.assertGreater(sign * float(np.dot(upper - peak, lateral)), 0.0)
            cuff = np.asarray(cage.vertices[arm:arm + 4])
            local = np.column_stack((cuff @ lateral, cuff @ forward))
            area = 0.5 * sum(local[i, 0] * local[(i + 1) % 4, 1]
                             - local[(i + 1) % 4, 0] * local[i, 1]
                             for i in range(4))
            self.assertGreater(abs(area), 1e-12)

    def test_symmetric_pair_of_pants_routes_are_exact(self):
        _, faces, _ = surface.symbolic_topology()
        expected = []
        for path, cuff in (((42, 43, 44, 45, 46), (56, 57, 58, 59, 56)),
                           ((42, 41, 40, 47, 46), (60, 61, 62, 63, 60))):
            expected.extend((path[i], path[i + 1], cuff[i + 1], cuff[i])
                            for i in range(4))
        expected.append((42, 56, 46, 60))
        self.assertEqual({frozenset(face) for face in faces[-9:]},
                         {frozenset(face) for face in expected})

    def test_pelvic_routes_have_no_proper_front_projection_crossings(self):
        cage = surface.build_cage(synthetic_prepared())
        routes = ((42, 43), (43, 44), (44, 45), (45, 46),
                  (42, 41), (41, 40), (40, 47), (47, 46), (42, 46))
        projected = np.asarray(cage.vertices)[:, (0, 1)]

        def orientation(a, b, c):
            return ((b[0] - a[0]) * (c[1] - a[1])
                    - (b[1] - a[1]) * (c[0] - a[0]))

        def proper_crossing(a, b, c, d):
            ab = orientation(a, b, c) * orientation(a, b, d)
            cd = orientation(c, d, a) * orientation(c, d, b)
            return ab < 0 and cd < 0

        for index, (a, b) in enumerate(routes):
            for c, d in routes[index + 1:]:
                if {a, b} & {c, d}:
                    continue
                self.assertFalse(proper_crossing(projected[a], projected[b],
                                                 projected[c], projected[d]))

    def test_symmetric_fixture_is_mirror_equivalent_at_all_levels(self):
        result = surface.evaluate(synthetic_prepared(), levels=2)

        def assert_mirror(vertices):
            values = np.asarray(vertices, dtype=float)
            reflected = values.copy(); reflected[:, 0] *= -1
            remaining = list(reflected)
            for point in values:
                distances = np.max(np.abs(np.asarray(remaining) - point), axis=1)
                index = int(np.argmin(distances))
                self.assertLessEqual(distances[index], 1e-8)
                remaining.pop(index)

        for mesh in (result.cage, *result.levels):
            assert_mirror(mesh.vertices)

    def test_profile_identity_is_not_an_input_path(self):
        prepared = synthetic_prepared()
        prepared["profile_id"] = "forbidden"
        with self.assertRaisesRegex(ValueError, "profile identity"):
            surface.build_cage(prepared)
        prepared = synthetic_prepared()
        prepared["stations"]["neck_collar"]["profile-id"] = "also-forbidden"
        with self.assertRaisesRegex(ValueError, "profile identity"):
            surface.build_cage(prepared)
        self.assertNotIn("profile", surface.build_cage.__code__.co_varnames)

    def test_shared_formula_constants_have_local_expected_effects(self):
        baseline = surface.build_cage(synthetic_prepared())
        changed = synthetic_prepared()
        changed["scalars"]["n"] = {"value": 3.1, "provenance": "synthetic.constant.n"}
        powered = surface.build_cage(changed)
        self.assertEqual(baseline.vertices[0], powered.vertices[0])
        self.assertNotEqual(baseline.vertices[1], powered.vertices[1])
        self.assertEqual(baseline.vertices[48:], powered.vertices[48:])

        changed = synthetic_prepared()
        changed["scalars"]["lambda"] = {"value": 0.5, "provenance": "synthetic.constant.lambda"}
        blended = surface.build_cage(changed)
        self.assertEqual(baseline.vertices[:32], blended.vertices[:32])
        self.assertNotEqual(baseline.vertices[32:40], blended.vertices[32:40])
        self.assertEqual(baseline.vertices[40:], blended.vertices[40:])

        changed = synthetic_prepared()
        changed["scalars"]["eta"] = {"value": 0.5, "provenance": "synthetic.constant.eta"}
        seated = surface.build_cage(changed)
        self.assertEqual(baseline.vertices[:56], seated.vertices[:56])
        self.assertNotEqual(baseline.vertices[56:], seated.vertices[56:])
        for side, offset in (("left", 56), ("right", 60)):
            start = np.asarray(changed["landmarks"][f"thigh_start_{side}"]["point"], dtype=float)
            mid = np.asarray(changed["landmarks"][f"thigh_mid_{side}"]["point"], dtype=float)
            route = mid - start
            centroid = np.mean(np.asarray(seated.vertices[offset:offset + 4]), axis=0)
            expected = start + changed["scalars"]["eta"]["value"] * route
            np.testing.assert_allclose(centroid, expected)
            projection = float(np.dot(centroid - start, route))
            self.assertGreater(projection, 0.0)
            self.assertAlmostEqual(projection / float(np.dot(route, route)),
                                   changed["scalars"]["eta"]["value"])

        for key, changed_slice, stable_slice in (
                ("shoulder", slice(48, 50), slice(50, 52)),
                ("axilla", slice(50, 52), slice(48, 50))):
            changed = synthetic_prepared()
            changed["scalars"][key] = {"value": surface.RANGES[key][1],
                                       "provenance": f"synthetic.constant.{key}"}
            collar = surface.build_cage(changed)
            self.assertNotEqual(baseline.vertices[changed_slice], collar.vertices[changed_slice])
            self.assertEqual(baseline.vertices[stable_slice], collar.vertices[stable_slice])

        changed = synthetic_prepared()
        changed["scalars"]["gamma"] = {"value": 0.12, "provenance": "synthetic.constant.gamma"}
        gapped = surface.build_cage(changed)
        self.assertNotEqual(baseline.vertices[56], gapped.vertices[56])
        self.assertNotEqual(baseline.vertices[60], gapped.vertices[60])
        self.assertEqual(baseline.vertices[57:60], gapped.vertices[57:60])
        self.assertEqual(baseline.vertices[61:64], gapped.vertices[61:64])

    def test_invalid_inputs_fail_closed(self):
        cases = []
        missing = synthetic_prepared(); del missing["stations"]["neck_collar"]; cases.append(missing)
        nonfinite = synthetic_prepared(); nonfinite["stations"]["waist_abdomen"]["center"] = (0, np.nan, 0); cases.append(nonfinite)
        left_handed = synthetic_prepared(); left_handed["frames"]["body"]["forward_axis"] = (0, 0, -1); cases.append(left_handed)
        no_route = synthetic_prepared(); no_route["landmarks"]["thigh_mid_left"]["point"] = no_route["landmarks"]["thigh_start_left"]["point"]; cases.append(no_route)
        no_gap = synthetic_prepared(); no_gap["landmarks"]["thigh_start_left"]["point"] = (0.2, -0.7, 0); cases.append(no_gap)
        for prepared in cases:
            with self.subTest(case=cases.index(prepared)):
                with self.assertRaises(ValueError):
                    surface.build_cage(prepared)


class SubdivisionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.prepared = synthetic_prepared()
        cls.result = surface.evaluate(cls.prepared, levels=2)

    def test_open_boundaries_subdivide_and_euler_is_preserved(self):
        first, second = self.result.levels
        self.assertEqual((len(first.vertices), len(first.quads)), (241, 220))
        self.assertEqual((len(second.vertices), len(second.quads)), (925, 880))
        for level, multiplier in ((first, 2), (second, 4)):
            report = surface.validate_topology(len(level.vertices), level.quads, level.boundary_loops)
            self.assertEqual(report.euler, -3)
            self.assertEqual(report.boundary_lengths, tuple(multiplier * n for n in (8, 4, 4, 4, 4)))
            self.assertEqual(len(level.triangles), 2 * len(level.quads))
            surface.validate_geometry(level, evaluated=True)

    def test_correspondence_order_and_results_are_deterministic(self):
        repeated = surface.evaluate(synthetic_prepared(), levels=2)
        self.assertEqual(self.result, repeated)
        first = self.result.levels[0]
        self.assertTrue(all(name.startswith("L1.v.") for name in first.control_ids[:64]))
        self.assertTrue(all(name.startswith("L1.e.") for name in first.control_ids[64:186]))
        self.assertTrue(all(name.startswith("L1.f.") for name in first.control_ids[186:]))
        self.assertIn("catmull_clark.open_boundary_vertex", first.formula_ids)
        self.assertIn("catmull_clark.open_boundary_edge", first.formula_ids)
        self.assertTrue(all(dependency for dependency in first.dependencies))

    def test_invalid_level_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "one or two"):
            surface.subdivide(self.result.cage, 0)
        with self.assertRaisesRegex(ValueError, "one or two"):
            surface.evaluate(self.prepared, levels=3)


if __name__ == "__main__":
    unittest.main()
