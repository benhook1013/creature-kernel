import importlib.util
import json
import math
from pathlib import Path
import sys
import time
import unittest


EXPERIMENT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "connected_leg_collision_broadphase", EXPERIMENT / "collision_broadphase.py"
)
COLLISION = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = COLLISION
SPEC.loader.exec_module(COLLISION)
CORE = COLLISION._load_core()


def _frozen_pair_input(pair):
    return pair[0] + pair[1][1:], ((0, 1, 2), (0, 3, 4))


def _frozen_zero_input(pair):
    return pair[0] + pair[1], ((0, 1, 2), (3, 4, 5))


def _class_counts(report):
    return tuple((stage, report["class_counts"][stage])
                 for stage in ("aabb-disjoint", "sat-disjoint", "hit",
                               "point-only", "excluded-adjacent"))


class BroadphaseEquivalenceTests(unittest.TestCase):
    def assert_equivalent_to_frozen(self, vertices, triangles, *, block_size=3):
        frozen = CORE.intersection_diagnostics(
            vertices, triangles, include_classifications=True
        )
        actual = COLLISION.collision_report(
            vertices, triangles, include_classifications=True,
            block_size=block_size,
        )
        self.assertEqual(actual["method"], COLLISION.METHOD)
        self.assertEqual(actual["pair_count"], frozen["pair_count"])
        self.assertEqual(actual["normalization_scale"], frozen["normalization_scale"])
        self.assertEqual(actual["candidate_pairs"], [list(pair) for pair in frozen["candidate_pairs"]])
        self.assertEqual(actual["hit_pairs"], [list(pair) for pair in frozen["hit_pairs"]])
        self.assertEqual(
            actual["classifications"],
            [[list(pair), stage] for pair, stage in frozen["classifications"]],
        )
        frozen_counts = dict(frozen["pair_policy_evidence"]["class_counts"])
        self.assertEqual(_class_counts(actual), tuple(frozen_counts.items()))
        self.assertTrue(actual["pair_partition_complete"], actual)
        self.assertTrue(actual["final_classification_partition_complete"], actual)
        self.assertEqual(actual["proven_aabb_reject_count"] +
                         actual["survivor_pair_count"], actual["pair_count"])
        return actual

    def test_frozen_shared_one_and_shared_zero_fixtures_match_exactly(self):
        for _fixture_id, pair, _expected in CORE._SHARED_ONE_FIXTURES:
            with self.subTest(fixture=_fixture_id):
                self.assert_equivalent_to_frozen(*_frozen_pair_input(pair))
        for fixture_id, pair, _expected in CORE._SHARED_ZERO_FIXTURES:
            with self.subTest(fixture=fixture_id):
                self.assert_equivalent_to_frozen(*_frozen_zero_input(pair))

    def test_frozen_boundary_duplicate_and_edge_failures_remain_frozen(self):
        p0 = CORE._P0
        one = CORE._ONE
        fixed_d = CORE._FIXED_D
        normal_points = ((p0, p0, p0), (one, p0, p0), (p0, fixed_d, p0))
        with self.assertRaisesRegex(CORE.MeshCorrectnessError,
                                    "normalized triangle normal"):
            COLLISION.collision_report(normal_points, ((0, 1, 2),))

        successor = ((p0, p0, p0), (one, p0, p0),
                     (p0, float.fromhex("0x1.0000000000000p-45"), p0))
        self.assert_equivalent_to_frozen(successor, ((0, 1, 2),))

        shared_two = ((p0, p0, p0), (one, p0, p0), (p0, one, p0),
                      (p0, -one, p0))
        self.assert_equivalent_to_frozen(shared_two, ((0, 1, 2), (1, 0, 3)))
        with self.assertRaisesRegex(CORE.MeshCorrectnessError, "shared-two"):
            COLLISION.collision_report(shared_two, ((0, 1, 2), (0, 1, 3)))
        with self.assertRaisesRegex(CORE.MeshCorrectnessError, "duplicate triangle"):
            COLLISION.collision_report(
                normal_points[:2] + ((p0, one, p0),),
                ((0, 1, 2), (0, 1, 2)),
            )

    def test_translated_scaled_fixture_and_cross_block_order_are_exact(self):
        fixture = CORE._SHARED_ONE_FIXTURES[7]
        vertices, triangles = _frozen_pair_input(fixture[1])
        self.assert_equivalent_to_frozen(vertices, triangles, block_size=1)
        many_vertices = []
        many_triangles = []
        for row in range(11):
            offset = len(many_vertices)
            x = float(4 * row)
            many_vertices.extend(((x, 0.0, 0.0), (x + 1.0, 0.0, 0.0),
                                  (x, 1.0, 0.0)))
            many_triangles.append((offset, offset + 1, offset + 2))
        self.assert_equivalent_to_frozen(many_vertices, many_triangles,
                                         block_size=2)


class BroadphaseScaleTests(unittest.TestCase):
    def test_known_collision_supports_more_than_frozen_triangle_limit(self):
        clear_pair = CORE._CLEAR_PAIR
        vertices = list(clear_pair[0] + clear_pair[1])
        triangles = [(0, 1, 2), (3, 4, 5)]
        for row in range(4095):
            offset = len(vertices)
            x = 10.0 + 4.0 * row
            vertices.extend(((x, 0.0, 0.0), (x + 1.0, 0.0, 0.0),
                             (x, 1.0, 0.0)))
            triangles.append((offset, offset + 1, offset + 2))
        started = time.perf_counter()
        report = COLLISION.collision_report(vertices, triangles, block_size=1024)
        elapsed = time.perf_counter() - started
        print(json.dumps({"known_collision_over_4096_seconds": elapsed,
                          "triangle_count": report["triangle_count"],
                          "hit_pairs": report["hit_pairs"]}, sort_keys=True))
        self.assertEqual(report["triangle_count"], 4097)
        self.assertTrue(report["local_triangle_limit_exceeded"])
        self.assertEqual(report["hit_pairs"], [[0, 1]])
        self.assertEqual(report["intersection_hit_count"], 1)
        self.assertTrue(report["pair_partition_complete"], report)
        self.assertTrue(report["final_classification_partition_complete"], report)
        self.assertEqual(report["proven_aabb_reject_count"] +
                         report["survivor_pair_count"], report["pair_count"])

    def test_actual_004_rest_matches_preserved_fullcoverage_collision_report(self):
        run_root = Path(
            "/home/ben/.cache/creature-kernel/connected-leg-assembly-004-checked-run"
        )
        if not run_root.is_dir():
            self.skipTest("preserved 004 run is unavailable")
        run_report = json.loads((run_root / "run-report.json").read_text())
        case_dir = run_root / "cases/case-00-calibrated_ordinary_human"
        rest = json.loads((case_dir / "rest.json").read_text())
        preserved = run_report["cases"][0]["poses"][0]["checks"]["metrics"]["collision"]
        triangles = [triangle for face in rest["quads"]
                     for triangle in ((face[0], face[1], face[2]),
                                      (face[0], face[2], face[3]))]
        started = time.perf_counter()
        actual = COLLISION.collision_report(rest["vertices"], triangles)
        elapsed = time.perf_counter() - started
        print(json.dumps({"actual_004_rest_seconds": elapsed,
                          "actual_004_rest_triangles": actual["triangle_count"],
                          "actual_004_rest_survivors": actual["survivor_pair_count"]},
                         sort_keys=True))
        self.assertEqual(actual["pair_count"], preserved["expected_pair_count"])
        self.assertEqual(actual["hit_pairs"], preserved["hit_triangle_pairs"])
        self.assertEqual(actual["intersection_hit_count"],
                         len(preserved["hit_triangle_pairs"]))
        self.assertEqual(preserved["covered_pair_count"],
                         preserved["expected_pair_count"])
        self.assertTrue(all(call["pair_policy_complete"]
                            for call in preserved["calls"]))
        self.assertTrue(actual["pair_partition_complete"], actual)
        self.assertTrue(actual["final_classification_partition_complete"], actual)
        self.assertFalse(actual["hit_pairs_truncated"], actual)
        self.assertEqual(actual["triangle_count"], 7936)


if __name__ == "__main__":
    unittest.main()
