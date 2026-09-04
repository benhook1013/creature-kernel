from __future__ import annotations

import math
import sys
import unittest
from importlib import import_module
from pathlib import Path
from unittest.mock import patch

PACKAGE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE))
mesh = import_module("mesh_correctness")


P0 = float.fromhex("0x0.0p+0")
ONE = float.fromhex("0x1.0000000000000p+0")
D50 = float.fromhex("0x1.0000000000000p-50")
MIN_SUBNORMAL = float.fromhex("0x0.0000000000001p-1022")
D = float.fromhex("0x1.0000000000000p-46")
I0 = float.fromhex("0x1.b7cdfd9d7bdbbp-34")

def _shared_base(b0=(ONE, P0, P0), b1=(P0, ONE, P0)):
    shared = (P0, P0, P0)
    a0 = (ONE, P0, P0)
    a1 = (P0, ONE, P0)
    return [shared, a0, a1], [shared, b0, b1]


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
    )


class _SubtractionRecorder:
    def __init__(self, calls):
        self.calls = calls

    def __rsub__(self, value):
        self.calls.append(value)
        return 0.0


class OwnershipRecordTests(unittest.TestCase):
    def test_exact_universes_classify_omission_and_duplicate_records(self):
        for total in (456, 1742, 6810):
            with self.subTest(total=total):
                keys = tuple(("element", index) for index in range(total))
                obligations = {key: ("ownership",) for key in keys}
                records = tuple((key, "ownership", True) for key in keys)
                self.assertEqual(len(keys), total)
                self.assertEqual(mesh.classify_ownership_records(
                    keys, obligations, records)["unowned_elements"], 0)
                omitted = mesh.classify_ownership_records(
                    keys, obligations, records[:-1])
                self.assertEqual((omitted["unowned_elements"],
                                  omitted["overowned_elements"]), (1, 0))
                duplicated = mesh.classify_ownership_records(
                    keys, obligations, records + ((keys[-1], "ownership", False),))
                self.assertEqual((duplicated["unowned_elements"],
                                  duplicated["overowned_elements"]), (0, 1))


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
    seam_index = metadata.index(((1, 1, 0), (0, 0, -1)))
    owners[seam_index] = "flat-seam"
    tags = {vertex: f"sample.{slot}" for slot, vertex in enumerate(faces[seam_index])}
    junctions = {
        f"junction.{index}": {
            "incident_domains": ("flat-seam", "surface"),
            "domain_vertex_tags": (dict(tags), dict(tags)),
        }
        for index in range(7)
    }
    inputs = {
        "vertices": tuple(coordinates),
        "quads": tuple(faces),
        "level": 0,
        "boundary_loops": loops,
        "port_directions": directions,
        "expected_base_faces": tuple(faces),
        "junction_inputs": junctions,
        "face_owners": tuple(owners),
    }
    return inputs, tuple(metadata), vertex_ids


class PrimitiveTests(unittest.TestCase):
    def test_full_quad_normal_uses_both_split_triangles(self):
        vertices = ((0.0, 0.0, 0.0), (2.0, 0.0, 0.0),
                    (2.0, 1.0, 0.0), (0.0, 0.0, 2.0))
        actual = mesh.quad_normal(vertices, (0, 1, 2, 3))
        scale = math.sqrt(24.0)
        expected = (2.0 / scale, -4.0 / scale, 2.0 / scale)
        for component, value in zip(actual, expected):
            self.assertAlmostEqual(component, value)
        self.assertNotEqual(actual, (0.0, 0.0, 1.0))

    def test_port_metrics_publish_raw_samples_and_true_extrema(self):
        points = ((0.0, 0.0, 0.0), (2.0, 0.0, 0.0),
                  (2.0, 1.0, 1.0), (1.0, 2.0, 3.0), (0.0, 0.0, 2.0))
        metrics = mesh.port_loop_metrics(
            points, (0, 1, 2, 3, 4), (0.0, 0.0, 1.0),
            ((0.0, 1.0, 0.0),) * 5)
        self.assertEqual(metrics["planarity"], max(metrics["planarity_samples"]))
        self.assertEqual(metrics["co_normal"], min(metrics["co_normal_samples"]))
        self.assertEqual((len(metrics["planarity_samples"]),
                          len(metrics["co_normal_samples"])), (5, 5))
        self.assertNotEqual(min(metrics["planarity_samples"]),
                            max(metrics["planarity_samples"]))

    def test_interval_disjoint_uses_both_subtractions_and_one_tolerance(self):
        just_abutting = math.nextafter(I0, math.inf)
        self.assertFalse(mesh.interval_disjoint(P0, P0, I0, I0))
        self.assertTrue(mesh.interval_disjoint(P0, P0, just_abutting, just_abutting))
        self.assertFalse(mesh.interval_disjoint(P0, P0, I0, math.nextafter(I0, math.inf)))

    def test_interval_disjoint_materializes_cut_b_then_cut_a_before_disjunction(self):
        calls = []
        with patch.object(mesh, "_FIXED_I0", _SubtractionRecorder(calls)):
            self.assertTrue(mesh.interval_disjoint(2.0, -1.0, 1.0, 0.0))
        self.assertEqual(calls, [1.0, 2.0])

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
        with self.assertRaisesRegex(mesh.MeshCorrectnessError, "malformed public input"):
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
        owners = ("domain.a",) + ("domain.b",) * (len(self.faces) - 1)
        tags = {vertex: f"tag.{slot}" for slot, vertex in enumerate(self.faces[0])}
        continuity = mesh.junction_continuity_metrics(
            self.points, self.faces, owners, ("domain.a", "domain.b"),
            (dict(tags), dict(tags)),
        )
        self.assertTrue(continuity["tag_identity"])
        self.assertTrue(continuity["vertex_id_identity"])
        self.assertTrue(continuity["opposite_trace_direction"])
        self.assertTrue(all(len(record) == 3 for trace in continuity["traces"]
                            for record in trace))
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
        old_trace = ((0, (0.0, 0.0, 0.0)), (1, (1.0, 0.0, 0.0)),
                     (2, (2.0, 0.0, 0.0)))
        with self.assertRaisesRegex(mesh.MeshCorrectnessError, "malformed public input"):
            mesh.junction_continuity_metrics(old_trace, tuple(reversed(old_trace)))

        owners = ("domain.a",) + ("domain.b",) * (len(self.faces) - 1)
        tags = {vertex: f"tag.{slot}" for slot, vertex in enumerate(self.faces[0])}
        forged = dict(tags)
        tag = forged.pop(self.faces[0][0])
        forged[4] = tag
        with self.assertRaisesRegex(mesh.MeshCorrectnessError, "vertex IDs"):
            mesh.junction_continuity_metrics(
                self.points, self.faces, owners, ("domain.a", "domain.b"),
                (dict(tags), forged),
            )
        with self.assertRaisesRegex(mesh.MeshCorrectnessError, "independent reference"):
            mesh.junction_continuity_metrics(
                self.points, self.faces, owners, ("domain.a", "domain.b"),
                (dict(forged), dict(forged)), (dict(tags), dict(tags)),
            )

    def test_contract_threshold_and_normalization_knobs_are_not_public(self):
        loop_points = ((0.0, 0.0, 0.0), (1.0, 0.0, 0.0),
                       (1.0, 0.0, 1.0), (0.0, 0.0, 1.0))
        with self.assertRaisesRegex(mesh.MeshCorrectnessError, "malformed public input"):
            mesh.validate_port_loop(loop_points, (0, 1, 2, 3),
                                    (0.0, 1.0, 0.0))
        with self.assertRaisesRegex(ValueError, "exact list or tuple"):
            mesh.port_loop_metrics(loop_points, (0, 1, 2, 3),
                                   (0.0, 1.0, 0.0), None)
        self.assertFalse(hasattr(mesh, "validate_junction_continuity"))
        triangles = ((0, 1, 2),)
        points = ((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0))
        with self.assertRaisesRegex(mesh.MeshCorrectnessError, "malformed public input"):
            mesh.intersection_diagnostics(points, triangles, scale=1.0)
        with self.assertRaisesRegex(mesh.MeshCorrectnessError, "malformed public input"):
            mesh.enumerate_broad_phase_candidates(points, triangles, cap=3)
        with self.assertRaisesRegex(ValueError, "below"):
            mesh.validate_fold((1.0, 0.0, 0.0), (1.0, 1.0, 0.0), 2)

    def test_production_geometry_requires_all_selectors_and_gate_data(self):
        with self.assertRaisesRegex(mesh.MeshCorrectnessError, "malformed public input"):
            mesh.validate_geometry(self.points, self.faces)
        with self.assertRaisesRegex(ValueError, "required"):
            mesh.validate_geometry(self.points, self.faces, 0, None, None, None, None, None)

    def test_frozen_child_face_catalogs_reject_mutated_level_faces(self):
        expected_l1 = (
            (0, 4, 8, 5), (1, 6, 8, 4), (2, 7, 8, 6), (3, 5, 8, 7),
        )
        expected_l2 = (
            (0, 9, 21, 10), (4, 17, 21, 9), (8, 18, 21, 17), (5, 10, 21, 18),
            (1, 12, 22, 11), (6, 19, 22, 12), (8, 17, 22, 19), (4, 11, 22, 17),
            (2, 14, 23, 13), (7, 20, 23, 14), (8, 19, 23, 20), (6, 13, 23, 19),
            (3, 15, 24, 16), (5, 18, 24, 15), (8, 20, 24, 18), (7, 16, 24, 20),
        )
        self.assertEqual(
            mesh.derive_expected_face_catalogs(((0, 1, 2, 3),)),
            (((0, 1, 2, 3),), expected_l1, expected_l2),
        )
        catalogs = mesh.derive_expected_face_catalogs(self.faces)
        for level in (1, 2):
            with self.subTest(level=level):
                actual = list(catalogs[level])
                actual[0] = tuple(reversed(actual[0]))
                vertex_count = max(index for face in catalogs[level] for index in face) + 1
                points = tuple((float(index), 0.0, 0.0) for index in range(vertex_count))
                loops = {f"port.{slot}": tuple(range(3 * slot, 3 * slot + 3))
                         for slot in range(5)}
                with self.assertRaisesRegex(mesh.MeshCorrectnessError,
                                            "face winding/catalog"):
                    mesh.validate_geometry(
                        points, tuple(actual), level, loops, {}, self.faces, {},
                        ("owner",) * len(actual),
                    )
                with self.assertRaisesRegex(mesh.MeshCorrectnessError,
                                            "expected_faces index out of range"):
                    mesh.validate_geometry(
                        points, catalogs[level], level, loops, {}, catalogs[level], {},
                        ("owner",) * len(catalogs[level]),
                    )


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
        with self.assertRaisesRegex(ValueError, "face winding/catalog"):
            self._validate(quads=tuple(faces))

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

    def test_each_of_seven_junctions_rejects_forged_vertex_ids(self):
        for name in sorted(self.inputs["junction_inputs"]):
            with self.subTest(name=name):
                junctions = {key: dict(value)
                             for key, value in self.inputs["junction_inputs"].items()}
                first, second = junctions[name]["domain_vertex_tags"]
                forged = dict(second)
                vertex, tag = next(iter(forged.items()))
                del forged[vertex]
                forged[next(candidate for candidate in range(len(self.inputs["vertices"]))
                            if candidate not in second)] = tag
                junctions[name]["domain_vertex_tags"] = (dict(first), forged)
                with self.assertRaisesRegex(ValueError, "vertex IDs"):
                    self._validate(junction_inputs=junctions)


class ProductionIntersectionFixtureTests(unittest.TestCase):
    def test_contract_fixture_matrix(self):
        shared_names = (
            "shared1.offset-d50-point-only", "shared1.coplanar-duplicate-hit",
            "shared1.offset-positive-minsub-point-only", "shared1.offset-negative-minsub-point-only",
            "shared1.coplanar-disjoint-fans", "shared1.ray-cone-hit",
            "shared1.near-coplanar-full-rank-hit", "shared1.transformed-point-only",
            "shared1.transformed-hit", "shared1.negative-zero-hit", "shared1.level2-ply-point-only",
        )
        suffixes = ("p000", "p001", "p010", "p011", "p100", "p101", "p110", "p111")
        general = (
            "shared0.clear-hit-origin", "shared0.clear-hit-translated",
            "shared0.sub-I0-contact-origin", "shared0.sub-I0-contact-translated",
            "shared0.aabb-disjoint", "shared0.sat-disjoint", "shared0.extreme-small-hit",
            "shared0.extreme-large-hit", "normal.boundary-D-reject", "normal.successor-D-accept",
            "shared2.opposite-edge-valid", "shared2.same-direction-reject",
            "shared3.duplicate-triangle-reject", "triangle-cap.boundary-4096",
            "triangle-cap.successor-4097", "candidate-cap.boundary-injected-3",
            "candidate-cap.successor-injected-3",
        )
        expected_ids = tuple(f"{name}.{suffix}" for name in shared_names
                             for suffix in suffixes) + general
        shared_outcomes = tuple(
            outcome
            for outcome in (
                "point-only", "hit", "point-only", "point-only", "point-only",
                "hit", "hit", "point-only", "hit", "hit", "point-only",
            )
            for _ in suffixes
        )
        general_outcomes = (
            "hit", "hit", "hit", "hit", "aabb-disjoint", "sat-disjoint",
            "hit", "hit", "hard-failure", "pass", "excluded-adjacent",
            "hard-failure", "hard-failure", "pass", "hard-failure", "hit",
            "hard-failure",
        )
        artifact_failure = AssertionError("fixture runner emitted an artifact")
        with (
            patch("builtins.open", side_effect=artifact_failure),
            patch.object(Path, "open", side_effect=artifact_failure),
            patch.object(Path, "mkdir", side_effect=artifact_failure),
            patch.object(Path, "touch", side_effect=artifact_failure),
            patch.object(Path, "write_bytes", side_effect=artifact_failure),
            patch.object(Path, "write_text", side_effect=artifact_failure),
        ):
            records = mesh.run_production_intersection_fixtures()

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
        self.assertEqual(len(records), 105)
        self.assertEqual(mesh.INTERSECTION_FIXTURE_IDS, expected_ids)
        self.assertEqual(tuple(record["fixture_id"] for record in records), expected_ids)
        self.assertTrue(all(tuple(record) == ("fixture_id", "outcome")
                            for record in records))
        self.assertEqual(tuple(record["outcome"] for record in records),
                         shared_outcomes + general_outcomes)

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
        evidence = report["pair_policy_evidence"]
        self.assertEqual(
            (evidence["expected_pair_count"], evidence["processed_pair_count"],
             evidence["first_pair"], evidence["last_pair"]),
            (pair_count, pair_count, (0, 1), (98, 99)),
        )
        self.assertEqual(evidence["class_counts"], (
            ("aabb-disjoint", 0), ("sat-disjoint", 0), ("hit", pair_count),
            ("point-only", 0), ("excluded-adjacent", 0),
        ))
        self.assertEqual(evidence["nontrivial_pair_count"], pair_count)
        self.assertEqual(len(evidence["nontrivial_classifications"]), 64)
        self.assertEqual(evidence["nontrivial_classifications"][0], ((0, 1), "hit"))
        self.assertTrue(evidence["nontrivial_evidence_truncated"])
        self.assertNotIn("classifications", report)
        with self.assertRaisesRegex(ValueError, "classification detail cap"):
            mesh.intersection_diagnostics(
                points, triangles, include_classifications=True)

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
