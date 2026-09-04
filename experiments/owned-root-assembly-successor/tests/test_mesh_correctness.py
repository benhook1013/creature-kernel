from __future__ import annotations

import math
import sys
import unittest
from importlib import import_module
from pathlib import Path

PACKAGE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE))
mesh = import_module("mesh_correctness")


P0 = float.fromhex("0x0.0p+0")
N0 = -P0
ONE = float.fromhex("0x1.0000000000000p+0")
HALF = float.fromhex("0x1.0000000000000p-1")
D50 = float.fromhex("0x1.0000000000000p-50")
MIN_SUBNORMAL = float.fromhex("0x0.0000000000001p-1022")
D = float.fromhex("0x1.0000000000000p-46")
I0 = float.fromhex("0x1.b7cdfd9d7bdbbp-34")


def _pair(a_points, b_points):
    points = tuple(a_points) + tuple(b_points)
    return points, ((0, 1, 2), (3, 4, 5))


def _shared_base(b0=(ONE, P0, P0), b1=(P0, ONE, P0)):
    shared = (P0, P0, P0)
    a0 = (ONE, P0, P0)
    a1 = (P0, ONE, P0)
    return [shared, a0, a1], [shared, b0, b1]


def _transform(point, scale, translation):
    return tuple(float(float(scale * value) + offset) for value, offset in zip(point, translation))


def _negative_zero(point):
    return tuple(math.copysign(0.0, -1.0) if value == 0.0 else value for value in point)


def _count_fixture(quad_count, control_count=128):
    points = tuple((float(index), 0.0, 0.0) for index in range(control_count))
    faces = []
    for first in range(1, control_count):
        for second in range(first + 1, control_count):
            for third in range(second + 1, control_count):
                faces.append((0, first, second, third))
                if len(faces) == quad_count:
                    return points, tuple(faces)
    raise AssertionError("fixture does not have enough unique quads")


def _assert_reaches_boundary_gate(test_case, level, points, faces):
    with test_case.assertRaisesRegex(ValueError, "exactly 5 boundary loops"):
        mesh.validate_geometry(
            points, faces, level, {"only": (0, 1, 2)}, {}, faces, {},
            ("owner",) * len(faces),
        )


class _CoercibleFloat:
    def __float__(self):
        return 1.0


class _ListSubclass(list):
    pass


def _fixture_shared_one():
    return (
        ("shared1.offset-d50-point-only", (ONE, P0, D50), (P0, ONE, D50), "point-only"),
        ("shared1.coplanar-duplicate-hit", (ONE, P0, P0), (P0, ONE, P0), "hit"),
        ("shared1.offset-positive-minsub-point-only", (ONE, P0, MIN_SUBNORMAL), (P0, ONE, MIN_SUBNORMAL), "point-only"),
        ("shared1.offset-negative-minsub-point-only", (ONE, P0, -MIN_SUBNORMAL), (P0, ONE, -MIN_SUBNORMAL), "point-only"),
        ("shared1.coplanar-disjoint-fans", (-ONE, P0, P0), (P0, -ONE, P0), "point-only"),
        ("shared1.ray-cone-hit", (ONE, ONE, P0), (P0, P0, ONE), "hit"),
        ("shared1.near-coplanar-full-rank-hit", (ONE, P0, D50), (P0, ONE, -D50), "hit"),
        ("shared1.transformed-point-only", (ONE, P0, D50), (P0, ONE, D50), "point-only"),
        ("shared1.transformed-hit", (ONE, P0, D50), (P0, ONE, -D50), "hit"),
        ("shared1.negative-zero-hit", (ONE, P0, P0), (P0, ONE, P0), "hit"),
        ("shared1.level2-ply-point-only",
         (float.fromhex("0x1.37918e2798bb6p-8"), float.fromhex("0x1.61bcdab8dcc06p-4"), float.fromhex("0x1.43c9e5ce2aeb6p-4")),
         (float.fromhex("0x1.7bc42ac7f04b0p-7"), float.fromhex("0x1.6cae8c4686bb2p-4"), float.fromhex("0x1.0be935f6a339ep-4")),
         "point-only"),
    )


_CUBE_DIRECTIONS = (
    (1, 0, 0), (-1, 0, 0), (0, 1, 0),
    (0, -1, 0), (0, 0, 1), (0, 0, -1),
)


def _face_corners(cube, direction):
    x, y, z = cube
    if direction == (1, 0, 0):
        return ((x + 1, y, z), (x + 1, y + 1, z),
                (x + 1, y + 1, z + 1), (x + 1, y, z + 1))
    if direction == (-1, 0, 0):
        return ((x, y, z), (x, y, z + 1),
                (x, y + 1, z + 1), (x, y + 1, z))
    if direction == (0, 1, 0):
        return ((x, y + 1, z), (x, y + 1, z + 1),
                (x + 1, y + 1, z + 1), (x + 1, y + 1, z))
    if direction == (0, -1, 0):
        return ((x, y, z), (x + 1, y, z),
                (x + 1, y, z + 1), (x, y, z + 1))
    if direction == (0, 0, 1):
        return ((x, y, z + 1), (x + 1, y, z + 1),
                (x + 1, y + 1, z + 1), (x, y + 1, z + 1))
    return ((x, y, z), (x, y + 1, z),
            (x + 1, y + 1, z), (x + 1, y, z))


def _integrated_fixture():
    occupied = {(x, y, z) for x in range(3) for y in range(3) for z in range(3)}
    arms = {
        "port.0": (((3, 1, 1), (4, 1, 1)), (1, 0, 0)),
        "port.1": (((-1, 1, 1), (-2, 1, 1)), (-1, 0, 0)),
        "port.2": (((1, 3, 1), (1, 4, 1)), (0, 1, 0)),
        "port.3": (((1, -1, 1), (1, -2, 1)), (0, -1, 0)),
        "port.4": (((1, 1, 3), (1, 1, 4)), (0, 0, 1)),
    }
    omitted = {}
    for name, (cubes, direction) in arms.items():
        occupied.update(cubes)
        omitted[(cubes[-1], direction)] = name

    coordinates = []
    vertex_ids = {}
    faces = []
    metadata = []
    port_corners = {}

    def vertex_id(corner):
        if corner not in vertex_ids:
            vertex_ids[corner] = len(coordinates)
            coordinates.append(tuple(float(value) for value in corner))
        return vertex_ids[corner]

    for cube in sorted(occupied):
        for direction in _CUBE_DIRECTIONS:
            neighbour = tuple(cube[axis] + direction[axis] for axis in range(3))
            if neighbour in occupied:
                continue
            corners = _face_corners(cube, direction)
            port_name = omitted.get((cube, direction))
            if port_name is not None:
                port_corners[port_name] = corners
                continue
            faces.append(tuple(vertex_id(corner) for corner in corners))
            metadata.append((cube, direction))

    loops = {
        name: tuple(vertex_ids[corner] for corner in reversed(port_corners[name]))
        for name in sorted(port_corners)
    }
    directions = {
        name: tuple(float(value) for value in arms[name][1])
        for name in sorted(arms)
    }
    owners = ["surface"] * len(faces)
    owners[metadata.index(((1, 1, 0), (0, 0, -1)))] = "flat-seam"
    trace = (
        ("sample.0", (0.0, 0.0, 0.0)),
        ("sample.1", (1.0, 0.0, 0.0)),
        ("sample.2", (1.0, 1.0, 0.0)),
    )
    traces = {
        f"junction.{index}": (trace, tuple(reversed(trace)))
        for index in range(7)
    }
    inputs = {
        "vertices": tuple(coordinates),
        "quads": tuple(faces),
        "level": 0,
        "boundary_loops": loops,
        "port_directions": directions,
        "expected_faces": tuple(faces),
        "junction_traces": traces,
        "face_owners": tuple(owners),
    }
    return inputs, tuple(metadata), vertex_ids


class PrimitiveTests(unittest.TestCase):
    def test_interval_disjoint_uses_both_subtractions_and_one_tolerance(self):
        just_abutting = math.nextafter(I0, math.inf)
        self.assertFalse(mesh.interval_disjoint(P0, P0, I0, I0))
        self.assertTrue(mesh.interval_disjoint(P0, P0, just_abutting, just_abutting))
        self.assertFalse(mesh.interval_disjoint(P0, P0, I0, math.nextafter(I0, math.inf)))

    def test_shared_one_classifier_is_exact_and_swap_invariant(self):
        for name, b0, b1, expected in _fixture_shared_one()[:7]:
            with self.subTest(name=name):
                first, second = _shared_base(b0, b1)
                shared, a0, a1 = first
                _, bb0, bb1 = second
                self.assertEqual(mesh.classify_shared_one(shared, a0, a1, bb0, bb1), expected)
                self.assertEqual(mesh.classify_shared_one(shared, a1, a0, bb0, bb1), expected)
                self.assertEqual(mesh.classify_shared_one(shared, a0, a1, bb1, bb0), expected)
                self.assertEqual(mesh.classify_shared_one(shared, bb0, bb1, a0, a1), expected)

    def test_shared_one_rejects_zero_ray(self):
        with self.assertRaisesRegex(ValueError, "zero ray"):
            mesh.shared_one_intersects((0.0, 0.0, 0.0), (0.0, 0.0, 0.0),
                                       (1.0, 0.0, 0.0), (0.0, 1.0, 0.0),
                                       (0.0, 0.0, 1.0))

    def test_coordinate_and_scalar_admission_is_exact_python_float(self):
        for value in (1, "1", True, _CoercibleFloat()):
            with self.subTest(value=type(value).__name__), self.assertRaisesRegex(
                    ValueError, "finite binary64"):
                mesh.interval_disjoint(value, 0.0, 2.0, 3.0)
        for value in (1, "1", True, _CoercibleFloat()):
            with self.subTest(vector_value=type(value).__name__), self.assertRaisesRegex(
                    ValueError, "finite binary64"):
                mesh.norm((value, 0.0, 0.0))

    def test_rows_require_exact_bounded_sequences_before_traversal(self):
        points = ((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0))

        def exploding_generator():
            raise AssertionError("generator was traversed")
            yield (0, 1, 2)

        for rows in ({0: (0, 1, 2)}, {(0, 1, 2)}, range(1),
                     _ListSubclass([(0, 1, 2)]), exploding_generator()):
            with self.subTest(rows=type(rows).__name__), self.assertRaisesRegex(
                    ValueError, "exact list or tuple"):
                mesh.intersection_diagnostics(points, rows)
        for row in ({0: 0, 1: 1, 2: 2}, {0, 1, 2}, range(3),
                    exploding_generator()):
            with self.subTest(row=type(row).__name__), self.assertRaisesRegex(
                    ValueError, "exact list or tuple"):
                mesh.intersection_diagnostics(points, (row,))
        with self.assertRaisesRegex(ValueError, "triangle cap"):
            mesh.intersection_diagnostics(points, [object()] * 4097)
        with self.assertRaisesRegex(ValueError, "quad cap"):
            mesh.validate_topology(4, [object()] * 2049)


class TopologyGeometryTests(unittest.TestCase):
    def setUp(self):
        self.points = (
            (0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (1.0, 1.0, 0.0), (0.0, 1.0, 0.0),
            (0.0, 0.0, 1.0), (1.0, 0.0, 1.0), (1.0, 1.0, 1.0), (0.0, 1.0, 1.0),
        )
        self.faces = (
            (0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4),
            (1, 2, 6, 5), (3, 7, 6, 2), (0, 4, 7, 3),
        )

    def test_closed_box_has_valid_topology_and_geometry(self):
        report = mesh.validate_topology(len(self.points), self.faces)
        self.assertEqual((report.edge_count, report.boundary_edge_count, report.euler), (12, 0, 2))
        with self.assertRaises(TypeError):
            mesh.validate_geometry(self.points, self.faces)

    def test_topology_rejects_same_direction_edge_and_unused_control(self):
        bad = list(self.faces)
        bad[1] = tuple(reversed(bad[1]))
        with self.assertRaisesRegex(ValueError, "orientation conflict"):
            mesh.validate_topology(8, bad)
        with self.assertRaisesRegex(ValueError, "unused vertex"):
            mesh.validate_topology(9, self.faces)

    def test_topology_rejects_duplicate_and_reversed_duplicate_quads(self):
        duplicates = (self.faces[0], tuple(reversed(self.faces[0])),
                      self.faces[0][1:] + self.faces[0][:1])
        for duplicate in duplicates:
            with self.subTest(duplicate=duplicate), self.assertRaisesRegex(
                    ValueError, "duplicate quad"):
                mesh.validate_topology(8, self.faces + (duplicate,))

    def test_clearance_semantics_are_owned_by_anatomy(self):
        self.assertFalse(hasattr(mesh, "boundary_clearance_ratios"))
        self.assertFalse(hasattr(mesh, "validate_boundary_clearances"))
        self.assertNotIn("boundary_clearance_ratios", mesh.__all__)

    def test_port_continuity_and_fold_are_independent(self):
        loop_points = ((0.0, 0.0, 0.0), (1.0, 0.0, 0.0),
                       (1.0, 0.0, 1.0), (0.0, 0.0, 1.0))
        adjacent = ((0.0, 0.0, -1.0), (1.0, 0.0, 0.0),
                    (0.0, 0.0, 1.0), (-1.0, 0.0, 0.0))
        metrics = mesh.validate_port_loop(loop_points, (0, 1, 2, 3),
                                          (0.0, 1.0, 0.0), adjacent)
        self.assertEqual(metrics["orientation"], 1.0)
        self.assertEqual(metrics["co_normal"], 1.0)
        traces = ((0, (0.0, 0.0, 0.0)), (1, (1.0, 0.0, 0.0)), (2, (2.0, 0.0, 0.0)))
        reverse = tuple(reversed(traces))
        self.assertTrue(mesh.junction_continuity_metrics(traces, reverse)["opposite_trace_direction"])
        self.assertLess(mesh.validate_fold((1.0, 0.0, 0.0), (1.0, 1.0, 0.0), 0), 90.0)
        with self.assertRaisesRegex(ValueError, "co-normal"):
            mesh.validate_port_loop(loop_points, (0, 1, 2, 3),
                                    (0.0, 1.0, 0.0),
                                    tuple((0.0, 0.0, 1.0) for _ in range(4)))

    def test_port_winding_and_continuity_fail_closed(self):
        with self.assertRaisesRegex(ValueError, "orientation"):
            mesh.validate_port_loop(((0.0, 0.0, 0.0), (1.0, 0.0, 0.0),
                                    (1.0, 0.0, 1.0), (0.0, 0.0, 1.0)),
                                   (0, 3, 2, 1), (0.0, 1.0, 0.0),
                                   ((1.0, 0.0, 0.0), (0.0, 0.0, -1.0),
                                    (-1.0, 0.0, 0.0), (0.0, 0.0, 1.0)))
        with self.assertRaisesRegex(ValueError, "directions"):
            mesh.junction_continuity_metrics(
                ((0, (0.0, 0.0, 0.0)), (1, (1.0, 0.0, 0.0)), (2, (2.0, 0.0, 0.0))),
                ((0, (0.0, 0.0, 0.0)), (1, (1.0, 0.0, 0.0)), (2, (2.0, 0.0, 0.0))),
            )

    def test_contract_threshold_and_normalization_knobs_are_not_public(self):
        loop_points = ((0.0, 0.0, 0.0), (1.0, 0.0, 0.0),
                       (1.0, 0.0, 1.0), (0.0, 0.0, 1.0))
        with self.assertRaises(TypeError):
            mesh.validate_port_loop(loop_points, (0, 1, 2, 3),
                                    (0.0, 1.0, 0.0))
        with self.assertRaisesRegex(ValueError, "exact list or tuple"):
            mesh.port_loop_metrics(loop_points, (0, 1, 2, 3),
                                   (0.0, 1.0, 0.0), None)
        self.assertFalse(hasattr(mesh, "validate_junction_continuity"))
        triangles = ((0, 1, 2),)
        points = ((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0))
        with self.assertRaises(TypeError):
            mesh.intersection_diagnostics(points, triangles, scale=1.0)
        with self.assertRaises(TypeError):
            mesh.enumerate_broad_phase_candidates(points, triangles, cap=3)
        with self.assertRaisesRegex(ValueError, "below"):
            mesh.validate_fold((1.0, 0.0, 0.0), (1.0, 1.0, 0.0), 2)

    def test_production_geometry_requires_all_selectors_and_gate_data(self):
        with self.assertRaises(TypeError):
            mesh.validate_geometry(self.points, self.faces)
        with self.assertRaisesRegex(ValueError, "required"):
            mesh.validate_geometry(self.points, self.faces, 0, None, None, None, None, None)


class GeometryCountTests(unittest.TestCase):
    def test_level_zero_count_boundaries_reach_the_next_gate(self):
        points, faces = _count_fixture(120, 128)
        _assert_reaches_boundary_gate(self, 0, points, faces)

    def test_level_zero_count_overruns_fail_closed(self):
        points, faces = _count_fixture(1, 129)
        with self.assertRaisesRegex(ValueError, "base control cap"):
            mesh.validate_geometry(
                points, faces, 0, {"only": (0, 1, 2)}, {}, faces, {},
                ("owner",),
            )
        points, faces = _count_fixture(121, 128)
        with self.assertRaisesRegex(ValueError, "base quad cap"):
            mesh.validate_geometry(
                points, faces, 0, {"only": (0, 1, 2)}, {}, faces, {},
                ("owner",) * len(faces),
            )

    def test_subdivision_quad_counts_are_not_subject_to_base_cap(self):
        for level, quad_count in ((1, 416), (2, 1664)):
            with self.subTest(level=level):
                points, faces = _count_fixture(quad_count)
                _assert_reaches_boundary_gate(self, level, points, faces)


class IntegratedGeometryTests(unittest.TestCase):
    def setUp(self):
        self.inputs, self.metadata, self.vertex_ids = _integrated_fixture()

    def _validate(self, **changes):
        return mesh.validate_geometry(**{**self.inputs, **changes})

    def test_success_runs_every_mandatory_production_gate(self):
        report = self._validate()
        floor = mesh.STRUCTURAL_FLOORS[0]
        self.assertEqual(report["topology"].boundary_components, 5)
        self.assertEqual(report["intersection_hit_count"], 0)
        self.assertEqual(report["port_count"], 5)
        self.assertEqual(set(report["port_metrics"]), set(self.inputs["boundary_loops"]))
        self.assertTrue(all(metrics["co_normal"] >= 0.80
                            for metrics in report["port_metrics"].values()))
        self.assertEqual(report["fold_count"], 4)
        self.assertEqual(report["junction_count"], 7)
        self.assertEqual(report["junction_residuals"], tuple(
            (f"junction.{index}", 0.0) for index in range(7)))
        self.assertGreaterEqual(report["edge_length_min"], floor["edge_length"])
        self.assertGreaterEqual(report["triangle_area_min"], floor["triangle_area"])
        self.assertGreaterEqual(report["quad_area_min"], floor["quad_area"])

    def test_topology_and_exact_five_port_gates_fail_in_production(self):
        faces = list(self.inputs["quads"])
        faces[0] = tuple(reversed(faces[0]))
        with self.assertRaisesRegex(ValueError, "orientation conflict"):
            self._validate(quads=tuple(faces), expected_faces=tuple(faces))

        loops = dict(self.inputs["boundary_loops"])
        loops.pop("port.4")
        directions = dict(self.inputs["port_directions"])
        directions.pop("port.4")
        with self.assertRaisesRegex(ValueError, "exactly 5 boundary loops"):
            self._validate(boundary_loops=loops, port_directions=directions)

    def test_structural_intersection_conormal_and_fold_gates_fail_in_production(self):
        scaled = tuple(tuple(0.01 * value for value in point)
                       for point in self.inputs["vertices"])
        with self.assertRaisesRegex(ValueError, "structural floor"):
            self._validate(vertices=scaled)

        crossed = list(self.inputs["vertices"])
        crossed[self.vertex_ids[(5, 1, 1)]] = (-3.0, 1.0, 1.0)
        with self.assertRaisesRegex(ValueError, "triangle intersections"):
            self._validate(vertices=tuple(crossed))

        flared = list(self.inputs["vertices"])
        replacements = {
            (4, 1, 1): (4.0, 0.0, 0.0),
            (4, 2, 1): (4.0, 3.0, 0.0),
            (4, 2, 2): (4.0, 3.0, 3.0),
            (4, 1, 2): (4.0, 0.0, 3.0),
        }
        for corner, point in replacements.items():
            flared[self.vertex_ids[corner]] = point
        with self.assertRaisesRegex(ValueError, "co-normal"):
            self._validate(vertices=tuple(flared))

        owners = list(self.inputs["face_owners"])
        owners[self.metadata.index(((0, 0, 0), (0, 0, -1)))] = "sharp-seam"
        with self.assertRaisesRegex(ValueError, "fold angle"):
            self._validate(face_owners=tuple(owners))

    def test_each_of_seven_junction_residuals_fails_in_production(self):
        for name in sorted(self.inputs["junction_traces"]):
            with self.subTest(name=name):
                traces = dict(self.inputs["junction_traces"])
                first, second = traces[name]
                bad_second = list(second)
                tag, _ = bad_second[0]
                bad_second[0] = (tag, (2.0, 2.0, 2.0))
                traces[name] = (first, tuple(bad_second))
                with self.assertRaisesRegex(ValueError, "coordinate residual"):
                    self._validate(junction_traces=traces)


class ProductionIntersectionFixtureTests(unittest.TestCase):
    def _assert_pair(self, name, points_a, points_b, expected, stage):
        points, triangles = _pair(points_a, points_b)
        report = mesh.intersection_diagnostics(
            points, triangles, include_classifications=True)
        self.assertTrue(report["pair_policy_complete"], name)
        self.assertEqual(report["classifications"], (((0, 1), stage),), name)
        actual = "hit" if report["intersection_hit_count"] else "point-only"
        self.assertEqual(actual, expected, name)

    def test_contract_fixture_matrix(self):
        executions = 0
        self.assertEqual(mesh.MAX_CANDIDATES, 1_000_000)
        self.assertEqual(
            mesh.intersection_candidate_threshold_records(),
            tuple(
                {
                    "threshold_id": f"threshold.intersection.L{level}.broad_phase_candidate_count",
                    "relation": "le",
                    "lower": None,
                    "upper": 1_000_000,
                    "unit": "count",
                }
                for level in range(3)
            ),
        )
        for name, b0, b1, expected in _fixture_shared_one():
            if name == "shared1.level2-ply-point-only":
                shared = (float.fromhex("0x1.8b59f7e4bf4dfp-7"), float.fromhex("0x1.0a35e0636f7c1p-4"), float.fromhex("0x1.264d28c7c3da4p-4"))
                first = [shared, b0, b1]
                second = [shared,
                          (float.fromhex("0x1.7888e87a16156p-6"), float.fromhex("0x1.7eec0987f75cdp-4"), float.fromhex("0x1.d5d88ce274e30p-5")),
                          (float.fromhex("0x1.8b59f7e4bf4dfp-6"), float.fromhex("0x1.18982604f83a1p-4"), float.fromhex("0x1.07df2315527a3p-4"))]
            else:
                first, second = _shared_base(b0, b1)
            if name == "shared1.transformed-point-only" or name == "shared1.transformed-hit":
                translation = (4.0, -2.0, 1.0)
                first = [_transform(point, 8.0, translation) for point in first]
                second = [_transform(point, 8.0, translation) for point in second]
            if name == "shared1.negative-zero-hit":
                first = [_negative_zero(point) for point in first]
                second = [_negative_zero(point) for point in second]
            base_points = tuple(first) + tuple(second[1:])
            base_triangles = ((0, 1, 2), (0, 3, 4))
            for suffix in ("p000", "p001", "p010", "p011", "p100", "p101", "p110", "p111"):
                a = list(base_triangles[0])
                b = list(base_triangles[1])
                if suffix[1] == "1":
                    a, b = b, a
                if suffix[2] == "1":
                    a[1], a[2] = a[2], a[1]
                if suffix[3] == "1":
                    b[1], b[2] = b[2], b[1]
                report = mesh.intersection_diagnostics(
                    base_points, (tuple(a), tuple(b)), include_classifications=True)
                self.assertTrue(report["pair_policy_complete"], f"{name}.{suffix}")
                self.assertEqual(report["classifications"], (((0, 1), expected),), f"{name}.{suffix}")
                actual = "hit" if report["intersection_hit_count"] else "point-only"
                self.assertEqual(actual, expected, f"{name}.{suffix}")
                executions += 1

        general = (
            ("shared0.clear-hit-origin", ((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)),
             ((0.0, -1.0, 0.0), (HALF, HALF, 0.0), (-HALF, HALF, 0.0)), "hit"),
            ("shared0.clear-hit-translated", ((4.0, -2.0, 1.0), (5.0, -2.0, 1.0), (4.0, -1.0, 1.0)),
             ((4.0, -3.0, 1.0), (4.5, -1.5, 1.0), (3.5, -1.5, 1.0)), "hit"),
            ("shared0.sub-I0-contact-origin", ((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)),
             ((0.0, 0.0, float.fromhex("0x1.0000000000000p-34")), (1.0, 0.0, float.fromhex("0x1.0000000000000p-34")), (0.0, 1.0, float.fromhex("0x1.0000000000000p-34"))), "hit"),
            ("shared0.sub-I0-contact-translated", ((4.0, -2.0, 1.0), (5.0, -2.0, 1.0), (4.0, -1.0, 1.0)),
             ((4.0, -2.0, 1.0 + float.fromhex("0x1.0000000000000p-34")), (5.0, -2.0, 1.0 + float.fromhex("0x1.0000000000000p-34")), (4.0, -1.0, 1.0 + float.fromhex("0x1.0000000000000p-34"))), "hit"),
            ("shared0.aabb-disjoint", ((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)), ((0.0, 0.0, 1.0), (1.0, 0.0, 1.0), (0.0, 1.0, 1.0)), "point-only"),
            ("shared0.sat-disjoint", ((0.0, 0.0, 0.0), (2.0, 0.0, 0.0), (0.0, 2.0, 0.0)), ((2.0, 2.0, 0.0), (2.0, 1.5, 0.0), (1.5, 2.0, 0.0)), "point-only"),
            ("shared0.extreme-small-hit", tuple(tuple(float(2.0 ** -500 * x) for x in point) for point in ((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0))),
             tuple(tuple(float(2.0 ** -500 * x) for x in point) for point in ((0.0, -1.0, 0.0), (0.5, 0.5, 0.0), (-0.5, 0.5, 0.0))), "hit"),
            ("shared0.extreme-large-hit", tuple(tuple(float(2.0 ** 500 * x) for x in point) for point in ((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0))),
             tuple(tuple(float(2.0 ** 500 * x) for x in point) for point in ((0.0, -1.0, 0.0), (0.5, 0.5, 0.0), (-0.5, 0.5, 0.0))), "hit"),
        )
        stages = {
            "shared0.clear-hit-origin": "hit",
            "shared0.clear-hit-translated": "hit",
            "shared0.sub-I0-contact-origin": "hit",
            "shared0.sub-I0-contact-translated": "hit",
            "shared0.aabb-disjoint": "aabb-disjoint",
            "shared0.sat-disjoint": "sat-disjoint",
            "shared0.extreme-small-hit": "hit",
            "shared0.extreme-large-hit": "hit",
        }
        for name, first, second, expected in general:
            self._assert_pair(name, first, second, expected, stages[name])
            executions += 1

        with self.assertRaisesRegex(ValueError, "normalized triangle normal"):
            mesh.intersection_diagnostics(((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, D, 0.0)), ((0, 1, 2),))
        self.assertEqual(mesh.intersection_diagnostics(
            ((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, float.fromhex("0x1.0000000000000p-45"), 0.0)), ((0, 1, 2),)
        )["intersection_hit_count"], 0)
        executions += 2

        valid_shared2 = ((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, -1.0, 0.0))
        self.assertEqual(
            mesh.intersection_diagnostics(
                valid_shared2, ((0, 1, 2), (1, 0, 3)),
                include_classifications=True,
            )["classifications"],
            (((0, 1), "excluded-adjacent"),),
        )
        executions += 1
        with self.assertRaisesRegex(ValueError, "shared-two"):
            mesh.intersection_diagnostics(valid_shared2, ((0, 1, 2), (0, 1, 3)))
        executions += 1
        with self.assertRaisesRegex(ValueError, "duplicate triangle"):
            mesh.intersection_diagnostics(((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)), ((0, 1, 2), (0, 1, 2)))
        executions += 1

        cap_points = []
        cap_triangles = []
        for row in range(4096):
            offset = 3 * row
            x = float(4 * row)
            cap_points.extend(((x, 0.0, 0.0), (float(x + 1.0), 0.0, 0.0), (x, 1.0, 0.0)))
            cap_triangles.append((offset, offset + 1, offset + 2))
        cap_report = mesh.intersection_diagnostics(tuple(cap_points), tuple(cap_triangles))
        self.assertEqual((cap_report["triangle_count"], cap_report["broad_phase_candidate_count"]), (4096, 0))
        pair_count = 4096 * 4095 // 2
        evidence = cap_report["pair_policy_evidence"]
        self.assertEqual(cap_report["pair_count"], pair_count)
        self.assertEqual(
            (evidence["expected_pair_count"], evidence["processed_pair_count"]),
            (pair_count, pair_count),
        )
        self.assertEqual(
            (evidence["first_pair"], evidence["last_pair"]),
            ((0, 1), (4094, 4095)),
        )
        self.assertEqual(
            evidence["class_counts"],
            (("aabb-disjoint", pair_count), ("sat-disjoint", 0),
             ("hit", 0), ("point-only", 0), ("excluded-adjacent", 0)),
        )
        self.assertEqual(evidence["nontrivial_pair_count"], 0)
        self.assertEqual(evidence["nontrivial_classifications"], ())
        self.assertFalse(evidence["nontrivial_evidence_truncated"])
        self.assertEqual(cap_report["candidate_pairs"], ())
        self.assertEqual(cap_report["hit_pairs"], ())
        self.assertFalse(cap_report["candidate_pairs_truncated"])
        self.assertFalse(cap_report["hit_pairs_truncated"])
        self.assertIsNone(cap_report["first_hit_pair"])
        self.assertNotIn("classifications", cap_report)
        self.assertTrue(cap_report["pair_policy_complete"])
        with self.assertRaisesRegex(ValueError, "classification detail cap"):
            mesh.intersection_diagnostics(
                tuple(cap_points), tuple(cap_triangles), include_classifications=True)
        executions += 1
        with self.assertRaisesRegex(ValueError, "triangle cap"):
            mesh.intersection_diagnostics(tuple(cap_points) + ((0.0, 0.0, 0.0),
                                          (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)),
                                          tuple(cap_triangles) + ((12288, 12289, 12290),))
        executions += 1

        candidate_points = tuple(point for _ in range(3) for point in ((0.0, 0.0, 0.0),
                                                                        (1.0, 0.0, 0.0),
                                                                        (0.0, 1.0, 0.0)))
        candidate_triangles = tuple((3 * row, 3 * row + 1, 3 * row + 2) for row in range(3))
        boundary_report = mesh.intersection_diagnostics(
            candidate_points, candidate_triangles, include_classifications=True)
        self.assertEqual(boundary_report["candidate_pairs"], ((0, 1), (0, 2), (1, 2)))
        self.assertEqual(boundary_report["intersection_hit_count"], 3)
        self.assertEqual(boundary_report["hit_pairs"], ((0, 1), (0, 2), (1, 2)))
        self.assertEqual(boundary_report["first_hit_pair"], (0, 1))
        self.assertFalse(boundary_report["candidate_pairs_truncated"])
        self.assertFalse(boundary_report["hit_pairs_truncated"])
        self.assertEqual(
            boundary_report["classifications"],
            (((0, 1), "hit"), ((0, 2), "hit"), ((1, 2), "hit")),
        )
        self.assertEqual(mesh._enumerate_fixture_candidates(candidate_points, candidate_triangles, 3),
                         ((0, 1), (0, 2), (1, 2)))
        executions += 1
        with self.assertRaisesRegex(ValueError, "candidate cap"):
            mesh._enumerate_fixture_candidates(
                candidate_points + ((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)),
                candidate_triangles + ((9, 10, 11),), 3)
        executions += 1
        self.assertEqual(executions, 105)

    def test_all_hit_diagnostics_keep_exact_counts_and_bounded_pair_evidence(self):
        triangle = ((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0))
        points = tuple(point for _ in range(100) for point in triangle)
        triangles = tuple((3 * row, 3 * row + 1, 3 * row + 2) for row in range(100))
        report = mesh.intersection_diagnostics(points, triangles)
        pair_count = 100 * 99 // 2

        self.assertEqual(report["pair_count"], pair_count)
        self.assertEqual(report["broad_phase_candidate_count"], pair_count)
        self.assertEqual(report["intersection_hit_count"], pair_count)
        self.assertEqual(report["first_hit_pair"], (0, 1))
        self.assertEqual(len(report["candidate_pairs"]), 64)
        self.assertEqual(len(report["hit_pairs"]), 64)
        self.assertTrue(report["candidate_pairs_truncated"])
        self.assertTrue(report["hit_pairs_truncated"])
        self.assertEqual(report["candidate_pairs"], report["hit_pairs"])
        self.assertTrue(report["pair_policy_complete"])
        self.assertNotIn("classifications", report)

    def test_candidate_cap_fixture_helper_is_local_and_deterministic(self):
        points = ((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0),
                  (0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0),
                  (0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0))
        triangles = ((0, 1, 2), (3, 4, 5), (6, 7, 8))
        self.assertEqual(mesh._enumerate_fixture_candidates(points, triangles, 3), ((0, 1), (0, 2), (1, 2)))
        points = points + ((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0))
        triangles = triangles + ((9, 10, 11),)
        with self.assertRaisesRegex(ValueError, "candidate cap"):
            mesh._enumerate_fixture_candidates(points, triangles, 3)


if __name__ == "__main__":
    unittest.main()
