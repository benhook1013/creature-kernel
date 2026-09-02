from __future__ import annotations

import struct
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import render_export  # noqa: E402


VERTICES = np.asarray(
    (
        (-1.0, -1.0, -1.0),
        (1.0, -1.0, -1.0),
        (1.0, 1.0, -1.0),
        (-1.0, 1.0, -1.0),
        (-1.0, -1.0, 1.0),
        (1.0, -1.0, 1.0),
        (1.0, 1.0, 1.0),
        (-1.0, 1.0, 1.0),
    ),
    dtype=np.float64,
)
QUADS = np.asarray(
    (
        (0, 1, 2, 3),
        (4, 7, 6, 5),
        (0, 4, 5, 1),
        (1, 5, 6, 2),
        (2, 6, 7, 3),
        (4, 0, 3, 7),
    ),
    dtype=np.int64,
)
DEPTH_VERTICES = np.asarray(
    ((-1.0, -1.0, 0.0), (1.0, -1.0, 0.0), (1.0, 1.0, 3.0), (-1.0, 1.0, 3.0),
     (-1.0, -1.0, 1.6), (1.0, -1.0, 1.6), (1.0, 1.0, 1.6), (-1.0, 1.0, 1.6)),
    dtype=np.float64,
)
DEPTH_QUADS = np.asarray(((0, 1, 2, 3), (4, 5, 6, 7)), dtype=np.int64)


def png_chunk_types(data: bytes) -> list[bytes]:
    offset = 8
    result = []
    while offset < len(data):
        length = struct.unpack(">I", data[offset : offset + 4])[0]
        result.append(data[offset + 4 : offset + 8])
        offset += 12 + length
    return result


class RenderExportTests(unittest.TestCase):
    def test_ply_has_counts_and_stable_quad_triangle_order(self) -> None:
        with tempfile.TemporaryDirectory(prefix="root-complex-render-", dir="/tmp") as directory:
            path = Path(directory) / "skin.ply"
            render_export.write_skin_ply(path, VERTICES, QUADS)
            lines = path.read_text(encoding="ascii").splitlines()
        self.assertIn("element vertex 8", lines)
        self.assertIn("element face 12", lines)
        self.assertIn("property double x", lines)
        end = lines.index("end_header")
        face_lines = lines[end + 1 + len(VERTICES) :]
        self.assertEqual(face_lines[:4], ["3 0 1 2", "3 0 2 3", "3 4 7 6", "3 4 6 5"])
        self.assertEqual(len(face_lines), 12)

    def test_skin_ply_and_png_are_byte_repeatable(self) -> None:
        with tempfile.TemporaryDirectory(prefix="root-complex-render-", dir="/tmp") as directory:
            root = Path(directory)
            render_export.write_skin_ply(root / "a.ply", VERTICES, QUADS)
            render_export.write_skin_ply(root / "b.ply", VERTICES, QUADS)
            render_export.render_skin_png(root / "a.png", VERTICES, QUADS)
            render_export.render_skin_png(root / "b.png", VERTICES, QUADS)
            self.assertEqual((root / "a.ply").read_bytes(), (root / "b.ply").read_bytes())
            self.assertEqual((root / "a.png").read_bytes(), (root / "b.png").read_bytes())

    def test_skin_z_buffer_chooses_local_near_depth_independent_of_triangle_order(self) -> None:
        reversed_quads = DEPTH_QUADS[::-1]
        with tempfile.TemporaryDirectory(prefix="root-complex-render-", dir="/tmp") as directory:
            root = Path(directory)
            render_export.render_skin_png(root / "forward.png", DEPTH_VERTICES, DEPTH_QUADS)
            render_export.render_skin_png(root / "reverse.png", DEPTH_VERTICES, reversed_quads)
            self.assertEqual((root / "forward.png").read_bytes(), (root / "reverse.png").read_bytes())
            with Image.open(root / "forward.png") as image:
                pixel = image.getpixel((300, 246))
            normal = np.cross(DEPTH_VERTICES[1] - DEPTH_VERTICES[0], DEPTH_VERTICES[2] - DEPTH_VERTICES[0])
            brightness = 0.38 + 0.62 * max(0.0, float(np.dot(normal / np.linalg.norm(normal), render_export._LIGHT)))
            near_colour = tuple(int(round(channel * brightness)) for channel in render_export._BASE_COLOUR)
            self.assertEqual(pixel, near_colour)

    def test_png_is_rgb_fixed_size_and_has_no_metadata_chunks(self) -> None:
        with tempfile.TemporaryDirectory(prefix="root-complex-render-", dir="/tmp") as directory:
            path = Path(directory) / "skin.png"
            render_export.render_skin_png(path, VERTICES, QUADS)
            data = path.read_bytes()
            with Image.open(path) as image:
                self.assertEqual(image.mode, "RGB")
                self.assertEqual(image.size, render_export.CANVAS_SIZE)
                self.assertEqual(image.info, {})
            self.assertEqual(png_chunk_types(data), [b"IHDR", b"IDAT", b"IEND"])

    def test_cage_diagnostic_is_rgb_and_has_visible_edges(self) -> None:
        with tempfile.TemporaryDirectory(prefix="root-complex-render-", dir="/tmp") as directory:
            path = Path(directory) / "cage.png"
            render_export.render_cage_png(path, VERTICES, QUADS)
            data = path.read_bytes()
            with Image.open(path) as image:
                self.assertEqual(image.mode, "RGB")
                self.assertEqual(image.size, render_export.CANVAS_SIZE)
                self.assertIn((237, 188, 86), set(image.getdata()))
            self.assertTrue(data.startswith(b"\x89PNG\r\n\x1a\n"))

    def test_existing_outputs_are_not_replaced(self) -> None:
        with tempfile.TemporaryDirectory(prefix="root-complex-render-", dir="/tmp") as directory:
            root = Path(directory)
            for name, writer in (
                ("skin.ply", render_export.write_skin_ply),
                ("skin.png", render_export.render_skin_png),
                ("cage.png", render_export.render_cage_png),
            ):
                path = root / name
                path.write_bytes(b"keep me")
                with self.assertRaises(FileExistsError):
                    writer(path, VERTICES, QUADS)
                self.assertEqual(path.read_bytes(), b"keep me")

    def test_changing_a_supplied_vertex_changes_ply_and_skin_png(self) -> None:
        changed = VERTICES.copy()
        changed[6, 0] += 0.35
        with tempfile.TemporaryDirectory(prefix="root-complex-render-", dir="/tmp") as directory:
            root = Path(directory)
            render_export.write_skin_ply(root / "original.ply", VERTICES, QUADS)
            render_export.write_skin_ply(root / "changed.ply", changed, QUADS)
            render_export.render_skin_png(root / "original.png", VERTICES, QUADS)
            render_export.render_skin_png(root / "changed.png", changed, QUADS)
            self.assertNotEqual((root / "original.ply").read_bytes(), (root / "changed.ply").read_bytes())
            self.assertNotEqual((root / "original.png").read_bytes(), (root / "changed.png").read_bytes())

    def test_nonfinite_and_invalid_indices_are_rejected(self) -> None:
        bad_vertices = VERTICES.copy()
        bad_vertices[0, 0] = np.nan
        with self.assertRaises(ValueError):
            render_export.triangulate_quads(bad_vertices, QUADS)
        bad_indices = QUADS.astype(np.float64)
        bad_indices[0, 0] = np.inf
        with self.assertRaises(ValueError):
            render_export.triangulate_quads(VERTICES, bad_indices)
        bad_indices[0, 0] = 0.5
        with self.assertRaises(ValueError):
            render_export.triangulate_quads(VERTICES, bad_indices)
        bad_indices[0, 0] = len(VERTICES)
        with self.assertRaises(ValueError):
            render_export.triangulate_quads(VERTICES, bad_indices)

    def test_missing_parent_is_not_created(self) -> None:
        with tempfile.TemporaryDirectory(prefix="root-complex-render-", dir="/tmp") as directory:
            path = Path(directory) / "missing" / "skin.ply"
            with self.assertRaises(FileNotFoundError):
                render_export.write_skin_ply(path, VERTICES, QUADS)
            self.assertFalse(path.parent.exists())


if __name__ == "__main__":
    unittest.main()
