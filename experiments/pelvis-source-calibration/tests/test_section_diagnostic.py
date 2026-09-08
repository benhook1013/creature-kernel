from __future__ import annotations

import json
import math
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import section_diagnostic  # noqa: E402


def _side_surface(center_x: float, radius_x: float, radius_z: float, sides: int = 8, y0: float = 0.0, y1: float = 2.0) -> tuple[list[tuple[float, float, float]], list[tuple[int, int, int, int]]]:
    vertices = []
    for y in (y0, y1):
        for index in range(sides):
            angle = 2.0 * math.pi * index / sides
            vertices.append((center_x + radius_x * math.cos(angle), y, radius_z * math.sin(angle)))
    quads = [(index, (index + 1) % sides, sides + (index + 1) % sides, sides + index) for index in range(sides)]
    return vertices, quads


def _box(remove_side: int | None = None):
    vertices, quads = _side_surface(0.0, 1.0, 1.0, 4)
    if remove_side is not None:
        quads.pop(remove_side)
    return vertices, quads


def _combine(*meshes):
    vertices = []
    quads = []
    for mesh_vertices, mesh_quads in meshes:
        offset = len(vertices)
        vertices.extend(mesh_vertices)
        quads.extend(tuple(index + offset for index in quad) for quad in mesh_quads)
    return vertices, quads


def _annulus():
    return _combine(_side_surface(0.0, 3.0, 3.0), _side_surface(0.0, 1.0, 1.0))


def _bowtie_surface():
    ring = [(-1.0, -1.0), (1.0, 1.0), (-1.0, 1.0), (1.0, -1.0)]
    vertices = [(x, y, z) for y in (0.0, 2.0) for x, z in ring]
    quads = [(index, (index + 1) % 4, 4 + (index + 1) % 4, 4 + index) for index in range(4)]
    return vertices, quads


class SectionDiagnosticTests(unittest.TestCase):
    def assert_json_safe(self, value):
        json.dumps(value, allow_nan=False)

    def test_open_box_midpoint_inside_external_and_boundary(self):
        vertices, quads = _box()
        for point, expected in [((0.0, 1.0, 0.0), "inside"), ((2.0, 1.0, 0.0), "outside"), ((1.0, 1.0, 0.0), "on_surface")]:
            with self.subTest(point=point):
                result = section_diagnostic.evaluate_point(vertices, quads, point, 2.0)
                self.assertEqual(result["classification"], expected, result)
                self.assertEqual(result["section"]["closed_count"], 1)
                self.assert_json_safe(result)

    def test_point_beyond_open_end_is_out_of_range(self):
        vertices, quads = _side_surface(0.0, 1.0, 1.0)
        result = section_diagnostic.evaluate_point(vertices, quads, (0.0, 3.0, 0.0), 2.0)
        self.assertEqual(result["classification"], "out_of_range", result)
        self.assertEqual(result["reason"], "out_of_represented_range")
        self.assertEqual(result["section"]["classification"], "out_of_range")
        self.assert_json_safe(result)

    def test_empty_section_within_mesh_height_is_outside(self):
        vertices, quads = _combine(_side_surface(-2.0, 1.0, 1.0, y1=0.75), _side_surface(2.0, 1.0, 1.0, y0=1.25))
        result = section_diagnostic.evaluate_point(vertices, quads, (0.0, 1.0, 0.0), 2.0)
        self.assertEqual(result["classification"], "outside", result)
        self.assertEqual(result["reason"], "empty_section_within_represented_range")
        self.assert_json_safe(result)

    def test_removed_side_is_indeterminate_open_section(self):
        vertices, quads = _box(remove_side=0)
        result = section_diagnostic.evaluate_point(vertices, quads, (0.0, 1.0, 0.0), 2.0)
        self.assertEqual(result["classification"], "INDETERMINATE_OPEN_SECTION", result)
        self.assertGreater(result["section"]["diagnostics"]["open_node_count"], 0)
        self.assert_json_safe(result)

    def test_two_disjoint_tubes_have_inside_gap_outside(self):
        vertices, quads = _combine(_side_surface(-2.0, 1.0, 1.0), _side_surface(2.0, 1.0, 1.0))
        for point, expected in [((-2.0, 1.0, 0.0), "inside"), ((2.0, 1.0, 0.0), "inside"), ((0.0, 1.0, 0.0), "outside")]:
            with self.subTest(point=point):
                result = section_diagnostic.evaluate_point(vertices, quads, point, 2.0)
                self.assertEqual(result["classification"], expected, result)
                self.assertEqual(result["section"]["closed_count"], 2)
                self.assert_json_safe(result)

    def test_annular_hole_uses_even_parity(self):
        vertices, quads = _annulus()
        hole = section_diagnostic.evaluate_point(vertices, quads, (0.0, 1.0, 0.0), 2.0)
        shell = section_diagnostic.evaluate_point(vertices, quads, (2.0, 1.0, 0.0), 2.0)
        self.assertEqual(hole["classification"], "outside", hole)
        self.assertEqual(hole["parity"], 0)
        self.assertEqual(hole["inside_contour_count"], 2)
        self.assertEqual(shell["classification"], "inside", shell)
        self.assertEqual(shell["parity"], 1)
        self.assert_json_safe(hole)
        self.assert_json_safe(shell)

    def test_reversed_winding_keeps_membership(self):
        vertices, quads = _box()
        reversed_quads = [(a, d, c, b) for a, b, c, d in quads]
        forward = section_diagnostic.evaluate_point(vertices, quads, (0.0, 1.0, 0.0), 2.0)
        reversed_result = section_diagnostic.evaluate_point(vertices, reversed_quads, (0.0, 1.0, 0.0), 2.0)
        self.assertEqual(forward["classification"], "inside")
        self.assertEqual(reversed_result["classification"], "inside")
        self.assertEqual(forward["parity"], reversed_result["parity"])
        self.assert_json_safe(reversed_result)

    def test_self_intersecting_section_does_not_claim_inside(self):
        vertices, quads = _bowtie_surface()
        result = section_diagnostic.evaluate_point(vertices, quads, (0.0, 1.0, 0.0), 2.0)
        self.assertIn(result["classification"], {"INDETERMINATE_OPEN_SECTION", "INDETERMINATE_SELF_INTERSECTION"}, result)
        self.assert_json_safe(result)

    def test_segment_intersection_uses_linear_scaled_tolerance(self):
        first, second = (0.0, 0.0), (0.001, 0.001)
        third, fourth = (0.0005, 0.0005001), (0.0006, 0.0007)
        crossing_first, crossing_second = (0.0, 0.001), (0.001, 0.0)
        for factor in (0.16, 1.0, 1000.0):
            with self.subTest(scale_factor=factor):
                scale_point = lambda point: tuple(factor * value for value in point)
                tolerance = factor * 1.0e-9
                self.assertFalse(section_diagnostic._intersects(scale_point(first), scale_point(second), scale_point(third), scale_point(fourth), tolerance))
                self.assertTrue(section_diagnostic._intersects(scale_point(first), scale_point(second), scale_point(crossing_first), scale_point(crossing_second), tolerance))

    def test_coincident_vertex_level_is_reported_ambiguous(self):
        vertices, quads = _box()
        section = section_diagnostic.inspect_section(vertices, quads, 0.0, 2.0)
        result = section_diagnostic.evaluate_point(vertices, quads, (0.0, 0.0, 0.0), 2.0)
        self.assertTrue(section["diagnostics"]["exact_coplanarity"], section)
        self.assertTrue(section["ambiguous"], section)
        self.assertTrue(result["classification"].startswith("INDETERMINATE_"), result)
        self.assert_json_safe(section)
        self.assert_json_safe(result)


if __name__ == "__main__":
    unittest.main()
