import json
from dataclasses import replace
from pathlib import Path
import unittest

import numpy as np

from ck_spike.diagnostics import Phase, Severity
from ck_spike.geometry import (
    GeometryConfig,
    GeometryError,
    SMOOTH_MIN_FORMULA,
    attribute_winners,
    build_surface,
    capsule_raw_field,
    derive_grid_metadata,
    ellipsoid_raw_field,
    primitive_world_aabb,
)
from ck_spike.model import ResolvedGraph
from ck_spike.resolver import resolve_file


EXPERIMENT_ROOT = Path(__file__).resolve().parents[1]
VALID_FIXTURE = EXPERIMENT_ROOT / "fixtures" / "valid.json"


class GeometryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.graph = resolve_file(VALID_FIXTURE).require_graph()

    def test_capsule_signs_boundary_and_rigid_transform(self):
        endpoints = ((0.0, -1.0, 0.0), (0.0, 1.0, 0.0))
        points = np.asarray(((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (1.1, 0.0, 0.0)))
        values = capsule_raw_field(points, endpoints, 1.0)
        np.testing.assert_allclose(values, [-1.0, 0.0, 0.1])

        # A 90-degree Z rotation maps the local segment onto world X and the
        # translation moves its centre to (2, 3, 0).
        half = np.sqrt(0.5)
        matrix = (
            0.0,
            -1.0,
            0.0,
            2.0,
            1.0,
            0.0,
            0.0,
            3.0,
            0.0,
            0.0,
            1.0,
            0.0,
            0.0,
            0.0,
            0.0,
            1.0,
        )
        transformed = capsule_raw_field(
            ((2.0, 3.0, 0.0), (3.0, 3.0, 0.0)), endpoints, 1.0, matrix
        )
        np.testing.assert_allclose(transformed, [-1.0, -1.0])

    def test_ellipsoid_signs_boundary_and_rigid_transform(self):
        radii = (2.0, 3.0, 4.0)
        values = ellipsoid_raw_field(
            ((0.0, 0.0, 0.0), (2.0, 0.0, 0.0), (2.2, 0.0, 0.0)), radii
        )
        np.testing.assert_allclose(values, [-1.0, 0.0, 0.1])
        matrix = (
            0.0,
            -1.0,
            0.0,
            4.0,
            1.0,
            0.0,
            0.0,
            -2.0,
            0.0,
            0.0,
            1.0,
            0.0,
            0.0,
            0.0,
            0.0,
            1.0,
        )
        np.testing.assert_allclose(
            ellipsoid_raw_field(((4.0, -2.0, 0.0), (4.0, 0.0, 0.0)), radii, matrix),
            [-1.0, 0.0],
        )

    def test_config_and_grid_metadata_are_explicit(self):
        config = GeometryConfig(samples_per_axis=12)
        self.assertEqual(config.samples_per_axis, 12)
        self.assertEqual(config.padding, 0.10)
        self.assertEqual(config.isovalue, 0.0)
        self.assertEqual(config.to_dict()["smooth_min"]["formula"], SMOOTH_MIN_FORMULA)
        self.assertEqual(config.to_dict()["smooth_min"]["fold_order"], "sorted_source_label")
        json.dumps(config.to_dict(), sort_keys=True)

        grid = derive_grid_metadata(self.graph, config)
        self.assertEqual(grid.axis_order, ("x", "y", "z"))
        self.assertEqual(grid.origin, grid.bounds_min)
        self.assertTrue(all(value > 0.0 for value in grid.spacing))
        for node in self.graph.nodes:
            lower, upper = primitive_world_aabb(node)
            self.assertTrue(np.all(np.asarray(lower) >= np.asarray(grid.bounds_min)))
            self.assertTrue(np.all(np.asarray(upper) <= np.asarray(grid.bounds_max)))

    def test_winner_ties_use_sorted_source_label(self):
        first, second = self.graph.nodes[0], self.graph.nodes[1]
        # Reuse the exact same primitive and transform under labels that sort
        # in the opposite order of the graph tuple.
        a = replace(first, node=replace(first.node, label="zeta"))
        b = replace(
            second,
            node=replace(second.node, label="alpha", primitive=first.node.primitive),
            world_matrix=first.world_matrix,
        )
        graph = ResolvedGraph(
            fixture_id="tie",
            spike_revision=1,
            seed=0,
            coordinate_convention=self.graph.coordinate_convention,
            nodes=(a, b),
        )
        labels = attribute_winners(graph, ((0.0, 1.2, 0.0),))
        self.assertEqual(labels, ("alpha",))

    def test_reduced_surface_is_watertight_attributed_and_repeatable(self):
        config = GeometryConfig(samples_per_axis=16)
        first = build_surface(self.graph, config)
        second = build_surface(self.graph, config)
        self.assertEqual(first, second)
        self.assertTrue(first.vertices and first.faces and first.normals)
        self.assertEqual(len(first.vertices), len(first.source_labels))
        self.assertEqual(first.metrics.component_count, 1)
        self.assertTrue(first.metrics.watertight)
        self.assertEqual(first.metrics.degenerate_face_count, 0)
        self.assertGreater(first.metrics.domain_face_minimum, 0.0)
        self.assertLess(first.metrics.field_minimum, 0.0)
        self.assertGreater(first.metrics.field_maximum, 0.0)
        self.assertGreater(first.metrics.orientation_alignment, 0.0)
        json.dumps(first.to_dict(), sort_keys=True)

    def test_domain_face_failure_is_typed_and_deterministic(self):
        graph = ResolvedGraph(
            fixture_id="single-capsule",
            spike_revision=1,
            seed=0,
            coordinate_convention=self.graph.coordinate_convention,
            nodes=(self.graph.nodes[0],),
        )
        with self.assertRaises(GeometryError) as raised:
            build_surface(graph, GeometryConfig(samples_per_axis=11, padding=0.0))
        self.assertEqual(
            [(item.code, item.phase, item.severity) for item in raised.exception.diagnostics],
            [("FIELD_DOMAIN_FACE_NOT_POSITIVE", Phase.FIELD, Severity.ERROR)],
        )


if __name__ == "__main__":
    unittest.main()
