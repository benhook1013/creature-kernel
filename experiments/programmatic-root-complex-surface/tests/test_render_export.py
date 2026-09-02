from __future__ import annotations

import json, os, struct, subprocess, sys, tempfile, unittest
from pathlib import Path

import numpy as np
from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = ROOT.parents[1]
SOURCE = REPOSITORY / "examples/body-documents/stylized-digitigrade-biped-authored-form.json"
LAUNCHER = ROOT / "root_complex_launcher.sh"
BUILD_SCRIPT = ROOT / "build_root_complex.py"
ARTIFACTS = ("prepared.json", "skin.ply", "skin.png", "cage.png", "metrics.json", "manifest.json")
sys.path.insert(0, str(ROOT))
import build_root_complex as builder  # noqa: E402
import render_export  # noqa: E402


VERTICES = np.asarray(
    ((-1.0, -1.0, -1.0), (1.0, -1.0, -1.0), (1.0, 1.0, -1.0), (-1.0, 1.0, -1.0),
     (-1.0, -1.0, 1.0), (1.0, -1.0, 1.0), (1.0, 1.0, 1.0), (-1.0, 1.0, 1.0)), dtype=np.float64)
QUADS = np.asarray(((0, 1, 2, 3), (4, 7, 6, 5), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (4, 0, 3, 7)), dtype=np.int64)
DEPTH_VERTICES = np.asarray(((-1.0, -1.0, 0.0), (1.0, -1.0, 0.0), (1.0, 1.0, 3.0), (-1.0, 1.0, 3.0), (-1.0, -1.0, 1.6), (1.0, -1.0, 1.6), (1.0, 1.0, 1.6), (-1.0, 1.0, 1.6)), dtype=np.float64)
DEPTH_QUADS = np.asarray(((0, 1, 2, 3), (4, 5, 6, 7)), dtype=np.int64)


def png_chunk_types(data: bytes) -> list[bytes]:
    offset, result = 8, []
    while offset < len(data):
        length = struct.unpack(">I", data[offset : offset + 4])[0]; result.append(data[offset + 4 : offset + 8]); offset += 12 + length
    return result


class RenderExportTests(unittest.TestCase):
    def test_ply_has_counts_and_stable_quad_triangle_order(self) -> None:
        with tempfile.TemporaryDirectory(prefix="root-complex-render-", dir="/tmp") as d:
            path = Path(d) / "skin.ply"; render_export.write_skin_ply(path, VERTICES, QUADS); lines = path.read_text(encoding="ascii").splitlines()
        self.assertTrue({"element vertex 8", "element face 12", "property double x"} <= set(lines)); end = lines.index("end_header")
        faces = lines[end + 1 + len(VERTICES) :]; self.assertEqual(faces[:4], ["3 0 1 2", "3 0 2 3", "3 4 7 6", "3 4 6 5"]); self.assertEqual(len(faces), 12)

    def test_skin_ply_and_png_are_byte_repeatable(self) -> None:
        with tempfile.TemporaryDirectory(prefix="root-complex-render-", dir="/tmp") as d:
            root = Path(d)
            for suffix, writer in (("ply", render_export.write_skin_ply), ("png", render_export.render_skin_png)):
                writer(root / f"a.{suffix}", VERTICES, QUADS); writer(root / f"b.{suffix}", VERTICES, QUADS); self.assertEqual((root / f"a.{suffix}").read_bytes(), (root / f"b.{suffix}").read_bytes())

    def test_skin_z_buffer_chooses_local_near_depth_independent_of_triangle_order(self) -> None:
        with tempfile.TemporaryDirectory(prefix="root-complex-render-", dir="/tmp") as d:
            root = Path(d); render_export.render_skin_png(root / "forward.png", DEPTH_VERTICES, DEPTH_QUADS); render_export.render_skin_png(root / "reverse.png", DEPTH_VERTICES, DEPTH_QUADS[::-1])
            self.assertEqual((root / "forward.png").read_bytes(), (root / "reverse.png").read_bytes())
            with Image.open(root / "forward.png") as image: pixel = image.getpixel((300, 246))
        normal = np.cross(DEPTH_VERTICES[1] - DEPTH_VERTICES[0], DEPTH_VERTICES[2] - DEPTH_VERTICES[0]); brightness = 0.38 + 0.62 * max(0.0, float(np.dot(normal / np.linalg.norm(normal), render_export._LIGHT)))
        self.assertEqual(pixel, tuple(int(round(channel * brightness)) for channel in render_export._BASE_COLOUR))

    def test_png_is_rgb_fixed_size_and_has_no_metadata_chunks(self) -> None:
        with tempfile.TemporaryDirectory(prefix="root-complex-render-", dir="/tmp") as d:
            path = Path(d) / "skin.png"; render_export.render_skin_png(path, VERTICES, QUADS); data = path.read_bytes()
            with Image.open(path) as image: self.assertEqual((image.mode, image.size, image.info), ("RGB", render_export.CANVAS_SIZE, {}))
        self.assertEqual(png_chunk_types(data), [b"IHDR", b"IDAT", b"IEND"])

    def test_cage_diagnostic_is_rgb_and_has_visible_edges(self) -> None:
        with tempfile.TemporaryDirectory(prefix="root-complex-render-", dir="/tmp") as d:
            path = Path(d) / "cage.png"; render_export.render_cage_png(path, VERTICES, QUADS); data = path.read_bytes()
            with Image.open(path) as image: self.assertEqual((image.mode, image.size), ("RGB", render_export.CANVAS_SIZE)); self.assertIn((237, 188, 86), set(image.getdata()))
        self.assertTrue(data.startswith(b"\x89PNG\r\n\x1a\n"))

    def test_existing_outputs_are_not_replaced(self) -> None:
        with tempfile.TemporaryDirectory(prefix="root-complex-render-", dir="/tmp") as d:
            root = Path(d)
            for name, writer in (("skin.ply", render_export.write_skin_ply), ("skin.png", render_export.render_skin_png), ("cage.png", render_export.render_cage_png)):
                path = root / name; path.write_bytes(b"keep me")
                with self.assertRaises(FileExistsError): writer(path, VERTICES, QUADS)
                self.assertEqual(path.read_bytes(), b"keep me")

    def test_changing_a_supplied_vertex_changes_ply_and_skin_png(self) -> None:
        changed = VERTICES.copy(); changed[6, 0] += 0.35
        with tempfile.TemporaryDirectory(prefix="root-complex-render-", dir="/tmp") as d:
            root = Path(d)
            for suffix, writer in (("ply", render_export.write_skin_ply), ("png", render_export.render_skin_png)):
                writer(root / f"original.{suffix}", VERTICES, QUADS); writer(root / f"changed.{suffix}", changed, QUADS); self.assertNotEqual((root / f"original.{suffix}").read_bytes(), (root / f"changed.{suffix}").read_bytes())

    def test_nonfinite_and_invalid_indices_are_rejected(self) -> None:
        bad_vertices = VERTICES.copy(); bad_vertices[0, 0] = np.nan
        with self.assertRaises(ValueError): render_export.triangulate_quads(bad_vertices, QUADS)
        for value in (np.inf, 0.5, len(VERTICES)):
            bad_indices = QUADS.astype(np.float64); bad_indices[0, 0] = value
            with self.assertRaises(ValueError): render_export.triangulate_quads(VERTICES, bad_indices)

    def test_builder_publishes_complete_metrics_and_manifest(self) -> None:
        with tempfile.TemporaryDirectory(prefix="root-complex-build-", dir="/tmp") as d:
            target = Path(d) / "standard-neutral"; self.assertEqual(builder.build(SOURCE, target), target); self.assertEqual({p.name for p in target.iterdir()}, set(ARTIFACTS))
            metrics = json.loads((target / "metrics.json").read_text(encoding="utf-8")); manifest = json.loads((target / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(metrics["intersection_status"], "zero"); self.assertEqual(metrics["intersection_counts_by_level"], [0, 0]); self.assertEqual(set(manifest["files"]), set(ARTIFACTS[:-1])); self.assertEqual(manifest["files"]["metrics.json"], builder._sha256(target / "metrics.json"))

    def test_atomic_publication_refuses_existing_target_without_overwrite(self) -> None:
        with tempfile.TemporaryDirectory(prefix="root-complex-publish-", dir="/tmp") as d:
            root = Path(d); stage, target = root / "stage", root / "target"; stage.mkdir(); (stage / "payload").write_bytes(b"new"); target.mkdir(); (target / "payload").write_bytes(b"keep")
            with self.assertRaises(FileExistsError): builder._publish_no_replace(stage, target)
            self.assertEqual((stage / "payload").read_bytes(), b"new"); self.assertEqual((target / "payload").read_bytes(), b"keep")

    def test_builder_cleans_staging_after_generation_failure(self) -> None:
        with tempfile.TemporaryDirectory(prefix="root-complex-failure-", dir="/tmp") as d:
            root = Path(d); target = root / "standard-neutral"
            with self.assertRaises(ValueError): builder.build(root / "missing-source.json", target)
            self.assertFalse(target.exists()); self.assertEqual(list(root.glob(f".{target.name}.staging-*")), [])

    def test_launcher_fresh_processes_are_byte_identical(self) -> None:
        with tempfile.TemporaryDirectory(prefix="root-complex-determinism-", dir="/tmp") as d:
            root = Path(d); targets = (root / "seed-one", root / "seed-two")
            for seed, target in zip((41, 42), targets):
                environment = os.environ.copy(); environment["PYTHONHASHSEED"] = str(seed)
                subprocess.run((str(LAUNCHER), str(BUILD_SCRIPT), str(SOURCE), str(target)), cwd=REPOSITORY, env=environment, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            for name in ARTIFACTS: self.assertEqual((targets[0] / name).read_bytes(), (targets[1] / name).read_bytes(), name)


if __name__ == "__main__":
    unittest.main()
