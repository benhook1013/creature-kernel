from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest

from PIL import Image

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
import render


def _occluding_quads():
    # The horizontal quad is behind the nearer quad in +Z.  The nearer quad is
    # deliberately tilted, so its directional-light colour differs.
    vertices = (
        (-0.8, -0.7, 0.0), (0.8, -0.7, 0.0), (0.8, 0.8, 0.0), (-0.8, 0.8, 0.0),
        (-0.8, -0.7, 0.7), (0.8, -0.7, 0.9), (0.8, 0.8, 0.8), (-0.8, 0.8, 0.6),
    )
    return vertices, ((0, 1, 2, 3), (4, 5, 6, 7))


class RenderTests(unittest.TestCase):
    def test_three_named_views_have_fixed_layout_and_pending_status(self):
        vertices, quads = _occluding_quads()
        with tempfile.TemporaryDirectory() as directory:
            metadata = render.render_views(vertices, quads, Path(directory) / "views.png",
                                          "Pelvis transition", "NOT APPRAISED")
            self.assertEqual((metadata["width"], metadata["height"]), (1600, 550))
            self.assertEqual(metadata["views"], ["front", "side", "rear-three-quarter"])
            self.assertEqual(metadata["visual_status"], "pending")
            with Image.open(metadata["output_path"]) as image:
                self.assertEqual((image.mode, image.size), ("RGB", (1600, 550)))

    def test_z_buffer_is_order_independent_for_overlapping_quads(self):
        vertices, quads = _occluding_quads()
        with tempfile.TemporaryDirectory() as directory:
            first = Path(directory) / "first.png"
            second = Path(directory) / "second.png"
            nearer = Path(directory) / "nearer.png"
            farther = Path(directory) / "farther.png"
            render.render_views(vertices, quads, first, "same", "PASS technical")
            render.render_views(vertices, tuple(reversed(quads)), second, "same", "PASS technical")
            render.render_views(vertices, (quads[1],), nearer, "same", "PASS technical")
            render.render_views(vertices, (quads[0],), farther, "same", "PASS technical")
            # Reversing the face order does not change the visible nearer surface.
            with Image.open(first) as first_image, Image.open(second) as second_image:
                self.assertEqual(first_image.tobytes(), second_image.tobytes())
            # The tilted nearer quad wins at an interior sample, and its colour
            # differs from the farther horizontal quad.
            with Image.open(first) as first_image, Image.open(nearer) as nearer_image, Image.open(farther) as farther_image:
                self.assertEqual(first_image.getpixel((267, 280)),
                                 nearer_image.getpixel((267, 280)))
                self.assertNotEqual(first_image.getpixel((267, 280)),
                                    farther_image.getpixel((267, 280)))

    def test_repeated_render_is_byte_deterministic_and_underside_is_separate(self):
        vertices, quads = _occluding_quads()
        with tempfile.TemporaryDirectory() as directory:
            first = Path(directory) / "first.png"
            second = Path(directory) / "second.png"
            first_meta = render.render_views(vertices, quads, first, "same", "REJECTED",
                                             underside=True)
            second_meta = render.render_views(vertices, quads, second, "same", "REJECTED",
                                              underside=True)
            self.assertEqual(first.read_bytes(), second.read_bytes())
            self.assertEqual(Path(first_meta["underside_path"]).read_bytes(),
                             Path(second_meta["underside_path"]).read_bytes())
            self.assertNotEqual(first_meta["output_path"], first_meta["underside_path"])
            self.assertEqual(first_meta["underside_visible_pixels"] > 0, True)

    def test_explicit_bounds_keep_comparison_frame_and_overlays_make_diagnostic(self):
        vertices, quads = _occluding_quads()
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "views.png"
            metadata = render.render_views(
                vertices, quads, output, "frame", "NOT APPRAISED",
                bounds=((-1.0, -1.0, -1.0), (1.0, 1.0, 1.0)),
                overlays=[{"start": [-1.0, 0.0, 0.0], "end": [1.0, 0.0, 0.0],
                           "color": [210, 40, 40], "label": "hip frame"}],
            )
            diagnostic = output.with_name("views-diagnostic.png")
            self.assertEqual(metadata["diagnostic_path"], str(diagnostic))
            self.assertTrue(diagnostic.exists())
            self.assertEqual(metadata["bounds"], [[-1.0, -1.0, -1.0], [1.0, 1.0, 1.0]])

    def test_crop_requires_explicit_opt_in_and_keeps_full_geometry_inputs(self):
        vertices = ((-2.0, -0.5, 0.0), (2.0, -0.5, 0.0),
                    (2.0, 0.5, 0.0), (-2.0, 0.5, 0.0))
        quads = ((0, 1, 2, 3),)
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "cropped.png"
            with self.assertRaises(render.RenderError):
                render.render_views(vertices, quads, output, "crop", "NOT APPRAISED",
                                    bounds=((-1.0, -1.0, -1.0), (1.0, 1.0, 1.0)))
            metadata = render.render_views(
                vertices, quads, output, "crop", "NOT APPRAISED",
                bounds=((-1.0, -1.0, -1.0), (1.0, 1.0, 1.0)), allow_crop=True)
            self.assertTrue(metadata["allow_crop"])
            self.assertEqual(metadata["triangle_count"], 2)

    def test_nonfinite_vertices_and_invalid_indices_are_rejected(self):
        vertices = ((-1.0, -1.0, 0.0), (1.0, -1.0, 0.0), (0.0, 1.0, 0.0),
                    (-1.0, -1.0, 1.0))
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "invalid.png"
            with self.assertRaises(render.RenderError):
                render.render_views(((float("nan"), 0.0, 0.0), *vertices[1:]),
                                    ((0, 1, 2, 3),), output, "bad", "REJECTED")
            with self.assertRaises(render.RenderError):
                render.render_views(vertices, ((0, 1, 2, 99),), output, "bad", "REJECTED")
            with self.assertRaises(render.RenderError):
                render.render_views(vertices, ((0, 1, True, 3),), output, "bad", "REJECTED")


if __name__ == "__main__":
    unittest.main()
