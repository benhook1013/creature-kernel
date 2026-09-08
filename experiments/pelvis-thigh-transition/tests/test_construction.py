"""Synthetic-only tests for the generic Catmull--Clark evaluator."""
from __future__ import annotations

from pathlib import Path
import sys
import unittest


PACKAGE_DIR = Path(__file__).resolve().parents[1]
if str(PACKAGE_DIR) not in sys.path:
    sys.path.insert(0, str(PACKAGE_DIR))

import construction  # noqa: E402


class SyntheticGridTests(unittest.TestCase):
    """Exercise subdivision without loading or constructing a real case."""

    def setUp(self) -> None:
        # A 3x3 x/z grid, with four consistently wound planar quads.
        vertices = tuple(
            (float(x), 0.0, float(z))
            for z in range(3)
            for x in range(3)
        )
        quads = (
            (0, 1, 4, 3),
            (1, 2, 5, 4),
            (3, 4, 7, 6),
            (4, 5, 8, 7),
        )
        base_owners = tuple("synthetic.grid" for _ in vertices)
        dummy_frame = {
            "H": (0.0, 0.0, 0.0),
            "knee": (0.0, -1.0, 0.0),
            "length": 1.0,
            "d": (0.0, -1.0, 0.0),
            "X": (1.0, 0.0, 0.0),
            "U": (0.0, 1.0, 0.0),
            "F": (0.0, 0.0, 1.0),
            "exit": (0.0, -0.45, 0.0),
        }
        self.mesh = {
            "vertices": vertices,
            "quads": quads,
            "face_owners": tuple("synthetic.grid" for _ in quads),
            "control_owners": base_owners,
            "loops": {
                "outer": (0, 1, 2, 5, 8, 7, 6, 3),
            },
            "base_stencils": tuple(((index, 1.0),) for index in range(9)),
            "frames": {
                "left": dict(dummy_frame),
                "right": dict(dummy_frame),
            },
            "metadata": {
                "level": 0,
                "admission_status": "accepted",
                "admission_failures": (),
                "base_control_owners": base_owners,
                "dominant_owner_label": (
                    "display representative only; authoritative ownership is "
                    "base_control_owners plus full base_stencils"
                ),
            },
        }

    def test_all_sixteen_child_quads_and_loop(self) -> None:
        evaluated = construction.evaluate(self.mesh, levels=1)
        level_one = evaluated[1]
        expected_quads = (
            (0, 9, 21, 10),
            (1, 12, 21, 9),
            (4, 14, 21, 12),
            (3, 10, 21, 14),
            (1, 11, 22, 12),
            (2, 13, 22, 11),
            (5, 16, 22, 13),
            (4, 12, 22, 16),
            (3, 14, 23, 15),
            (4, 17, 23, 14),
            (7, 19, 23, 17),
            (6, 15, 23, 19),
            (4, 16, 24, 17),
            (5, 18, 24, 16),
            (8, 20, 24, 18),
            (7, 17, 24, 20),
        )
        self.assertEqual(level_one["quads"], expected_quads)
        self.assertEqual(level_one["face_owners"], ("synthetic.grid",) * 16)
        self.assertEqual(level_one["loops"]["outer"],
                         (0, 9, 1, 11, 2, 13, 5, 18,
                          8, 20, 7, 19, 6, 15, 3, 10))

    def test_affine_reproduction_partition_and_planarity(self) -> None:
        evaluated = construction.evaluate(self.mesh, levels=2)
        base_vertices = self.mesh["vertices"]
        for mesh in evaluated:
            self.assertTrue(all(
                abs(sum(weight for _index, weight in stencil) - 1.0)
                <= 1.0e-12
                for stencil in mesh["base_stencils"]
            ))
            self.assertTrue(all(
                weight >= -1.0e-12
                for stencil in mesh["base_stencils"]
                for _index, weight in stencil
            ))
            for point, stencil in zip(mesh["vertices"],
                                      mesh["base_stencils"]):
                reproduced = tuple(
                    sum(base_vertices[index][axis] * weight
                        for index, weight in stencil)
                    for axis in range(3)
                )
                self.assertEqual(point[1], 0.0)
                for actual, expected in zip(point, reproduced):
                    self.assertAlmostEqual(actual, expected, places=12)

    def test_translation_reproduction_and_owner_metadata(self) -> None:
        translation = (2.5, -3.0, 4.0)
        translated = dict(self.mesh)
        translated["vertices"] = tuple(
            tuple(point[axis] + translation[axis] for axis in range(3))
            for point in self.mesh["vertices"]
        )
        original_levels = construction.evaluate(self.mesh, levels=2)
        translated_levels = construction.evaluate(translated, levels=2)
        for original, shifted in zip(original_levels, translated_levels):
            self.assertEqual(
                shifted["metadata"]["dominant_owner_label"],
                "display representative only; authoritative ownership is "
                "base_control_owners plus full base_stencils",
            )
            self.assertEqual(original["metadata"]["base_control_owners"],
                             shifted["metadata"]["base_control_owners"])
            for original_point, shifted_point in zip(
                original["vertices"], shifted["vertices"]
            ):
                for actual, expected in zip(
                    shifted_point,
                    (original_point[axis] + translation[axis]
                     for axis in range(3)),
                ):
                    self.assertAlmostEqual(actual, expected, places=12)

    def test_shared_edges_have_opposite_winding(self) -> None:
        level_one = construction.evaluate(self.mesh, levels=1)[1]
        directed = {}
        for face_index, face in enumerate(level_one["quads"]):
            for slot, left in enumerate(face):
                right = face[(slot + 1) % 4]
                edge = tuple(sorted((left, right)))
                directed.setdefault(edge, []).append((face_index, left, right))

        boundary = {edge for edge, rows in directed.items() if len(rows) == 1}
        self.assertEqual(boundary, {
            tuple(sorted((left, right)))
            for index, left in enumerate(level_one["loops"]["outer"])
            for right in (level_one["loops"]["outer"]
                          [(index + 1) % len(level_one["loops"]["outer"])],)
        })
        for rows in directed.values():
            self.assertIn(len(rows), (1, 2))
            if len(rows) == 2:
                self.assertEqual((rows[0][1], rows[0][2]),
                                 (rows[1][2], rows[1][1]))


if __name__ == "__main__":
    unittest.main()
