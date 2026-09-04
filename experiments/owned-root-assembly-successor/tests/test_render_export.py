from __future__ import annotations

import hashlib
import struct
import sys
import unittest
from copy import deepcopy
from dataclasses import replace
from functools import lru_cache
from io import BytesIO
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
import artifact_serialization as artifacts
import owned_root_surface as surface
import prepared_projection
import render_export as render


def _prepared():
    return prepared_projection.prepare_standard_neutral(
        REPO / "examples/body-documents/stylized-digitigrade-biped-authored-form.json"
    )


@lru_cache(maxsize=1)
def _evaluation():
    return surface.evaluate(_prepared())


def _level2():
    return _evaluation().levels[1]


@lru_cache(maxsize=1)
def _visibility():
    return render.build_visibility(_level2())


class PLYTests(unittest.TestCase):
    def test_exact_quad_header_rows_and_terminal_lf(self):
        data = render.ply_bytes(
            ((0.0, -0.0, 1e-5), (1.0, 2.0, -1e20), (3.0, 4.0, 5.0), (6.0, 7.0, 8.0)),
            ((0, 1, 2, 3),),
        )
        expected = (
            b"ply\nformat ascii 1.0\n"
            b"element vertex 4\nproperty double x\nproperty double y\nproperty double z\n"
            b"element face 1\nproperty list uchar int vertex_indices\nend_header\n"
            b"0 0 1.0000000000000001e-5\n1 2 -1e+20\n3 4 5\n6 7 8\n4 0 1 2 3\n"
        )
        self.assertEqual(data, expected)
        self.assertEqual(data[-1:], b"\n")
        self.assertNotIn(b"\r", data)

    def test_mesh_export_preserves_quad_order_and_rejects_mutations(self):
        mesh = _level2()
        data = render.ply_bytes(mesh)
        self.assertIn(b"element vertex 1737\n", data)
        self.assertIn(b"element face 1664\n", data)
        first_face = b"4 " + b" ".join(str(item).encode("ascii") for item in mesh.quads[0])
        self.assertIn(b"\n" + first_face + b"\n", data)
        with self.assertRaises(render.RenderExportError):
            render.ply_bytes([(0, 0, 0)], [(0, 0, 0, 0)])
        with self.assertRaises(render.RenderExportError):
            render.ply_bytes(((0.0, 0.0, 0.0),), ((0, 1, 2, 3),))

    def test_ply_rejects_non_binary64_and_non_quad_inputs(self):
        points = ((0.0, 0.0, 0.0), (1.0, 0.0, 0.0),
                  (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))
        invalid = (
            ((0, 0.0, 0.0), points[1], points[2], points[3]),
            ((float("nan"), 0.0, 0.0), points[1], points[2], points[3]),
        )
        for rows in invalid:
            with self.subTest(row=rows[0]), self.assertRaises(render.RenderExportError):
                render.ply_bytes(rows, ((0, 1, 2, 3),))
        for face in (((0, 1, 2),), ((0, 1, 2, 4),), ((0, 1, True, 3),)):
            with self.subTest(face=face), self.assertRaises(render.RenderExportError):
                render.ply_bytes(points, face)

class ConfigTests(unittest.TestCase):
    def test_config_is_closed_and_has_exact_literals(self):
        config = render.render_config_record()
        render.validate_render_config(config)
        self.assertEqual(tuple(config), render.CONFIG_KEYS)
        self.assertEqual(config["panel_order"], ["front", "side", "45deg"])
        self.assertEqual(config["padding"], 24)
        self.assertEqual(config["png_metadata"], {})
        self.assertEqual(config["cameras"][2]["right"][0], 0.7071067811865476)
        self.assertEqual(config["cameras"][2]["right"][2], -0.7071067811865475)
        self.assertEqual(config["quad_split"], [[0, 1, 2], [0, 2, 3]])
        self.assertEqual(config["png_compress_level"], 9)
        self.assertFalse(any(config[key] for key in
                             ("shading", "lighting", "labels", "outlines", "anti_aliasing", "alpha", "culling")))

    def test_config_mutation_is_rejected(self):
        config = render.render_config_record()
        for key, value in (("padding", 25), ("labels", True), ("png_metadata", {"x": 1})):
            candidate = deepcopy(config)
            candidate[key] = value
            with self.subTest(key=key), self.assertRaises(render.RenderExportError):
                render.validate_render_config(candidate)
        candidate = deepcopy(config)
        candidate["extra"] = False
        with self.assertRaises(render.RenderExportError):
            render.validate_render_config(candidate)

    def test_equal_valued_scalar_type_substitutions_are_rejected_recursively(self):
        config = render.render_config_record()
        cases = (
            ("padding", ("padding",), 24.0),
            ("compress", ("png_compress_level",), 9.0),
            ("boolean", ("shading",), 0),
            ("camera", ("cameras", 0, "right", 0), 1),
            ("palette", ("domain_palette", "domain.pelvis", 0), 214.0),
        )
        for label, path, replacement in cases:
            candidate, target = deepcopy(config), None
            target = candidate
            for key in path[:-1]:
                target = target[key]
            target[path[-1]] = replacement
            with self.subTest(label=label), self.assertRaises(render.RenderExportError):
                render.validate_render_config(candidate)

    def test_canonical_wire_config_admits_only_zero_float_normalization(self):
        config = artifacts.decode_canonical_json(
            artifacts.canonical_json_bytes(render.render_config_record())
        )
        self.assertIs(type(config["cameras"][0]["right"][1]), int)
        render.validate_render_config(config)
        for label, path, replacement in (
                ("type", ("cameras", 0, "right", 0), 1),
                ("value", ("padding",), 25)):
            candidate, target = deepcopy(config), None
            target = candidate
            for key in path[:-1]:
                target = target[key]
            target[path[-1]] = replacement
            with self.subTest(label=label), self.assertRaises(render.RenderExportError):
                render.validate_render_config(candidate)
        candidate = deepcopy(config)
        candidate["extra"] = False
        with self.assertRaises(render.RenderExportError):
            render.validate_render_config(candidate)

    def test_config_factory_returns_independent_closed_values(self):
        first = render.render_config_record()
        first["cameras"][0]["right"][0] = 99.0
        first["domain_palette"]["domain.pelvis"][0] = 0
        second = render.render_config_record()
        render.validate_render_config(second)
        self.assertEqual(second["cameras"][0]["right"][0], 1.0)
        self.assertEqual(second["domain_palette"]["domain.pelvis"], [214, 83, 83])


class RendererTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mesh = _level2()

    def test_visibility_is_level2_closed_and_shared(self):
        visibility = _visibility()
        self.assertEqual(len(visibility.owners), 3 * 512 * 512)
        self.assertEqual(len(visibility.depths), len(visibility.owners))
        self.assertEqual(len(visibility.triangle_owners), 3328)
        self.assertEqual(visibility.triangle_index_sha256, hashlib.sha256(
            b"".join(struct.pack("<qqq", *triangle) for face in self.mesh.quads
                      for triangle in ((face[0], face[1], face[2]), (face[0], face[2], face[3])))
        ).hexdigest())
        self.assertEqual(visibility.triangle_index_sha256,
                         "31a4bfb22d2551d3682d264da94d918c34e65c938720da2661321d21e077d335")
        evidence = render.visibility_record(visibility)
        self.assertEqual(set(evidence), {"level", "triangle_count", "triangle_index_sha256", "rule"})
        self.assertEqual(evidence["triangle_count"], 3328)
        self.assertEqual(evidence["level"], 2)
        self.assertEqual(evidence["rule"], "larger-depth-then-lower-triangle-index")
        expected = tuple(record[1] for record in surface.FACE_RECORDS for _ in range(32))
        self.assertEqual(visibility.triangle_owners, expected)
        self.assertGreater(sum(owner is not None for owner in visibility.owners), 0)
        for panel in range(3):
            panel_owners = visibility.owners[panel * 512 * 512:(panel + 1) * 512 * 512]
            self.assertGreater(sum(owner is not None for owner in panel_owners), 0)

    def test_direct_and_lineage_share_visibility_and_only_colour_changes(self):
        direct, lineage, visibility = render.render_pair_bytes(self.mesh)
        self.assertEqual(direct, render.render_png_bytes(visibility))
        self.assertEqual(lineage, render.render_png_bytes(visibility, lineage=True))
        self.assertNotEqual(direct, lineage)
        self.assertTrue(direct.startswith(b"\x89PNG\r\n\x1a\n"))
        self.assertTrue(lineage.startswith(b"\x89PNG\r\n\x1a\n"))
        from PIL import Image
        with Image.open(BytesIO(direct)) as first, Image.open(BytesIO(lineage)) as second:
            self.assertEqual((first.mode, first.size), ("RGB", (512, 1536)))
            self.assertEqual((second.mode, second.size), ("RGB", (512, 1536)))
            first_pixels, second_pixels = list(first.getdata()), list(second.getdata())
        for owner, left, right in zip(visibility.owners, first_pixels, second_pixels):
            if owner is None:
                self.assertEqual((left, right), (render.BACKGROUND_RGB, render.BACKGROUND_RGB))
            else:
                self.assertEqual(left, render.DIRECT_RGB)
                self.assertEqual(right, render.PALETTE[visibility.triangle_owners[owner]])

    def test_render_is_deterministic_and_rejects_wrong_meshes(self):
        first = render.render_pair_bytes(self.mesh)
        second = render.render_pair_bytes(self.mesh)
        self.assertEqual(first[0], second[0])
        self.assertEqual(first[1], second[1])
        with self.assertRaises(render.RenderExportError):
            render.build_visibility(replace(self.mesh, level=1))
        owners = list(self.mesh.face_owners)
        owners[1] = "domain.pelvis"
        broken = replace(self.mesh, face_owners=tuple(owners))
        with self.assertRaises(render.RenderExportError):
            render.build_visibility(broken)
        broken_faces = replace(self.mesh, face_ids=tuple("wrong" for _ in self.mesh.face_ids))
        with self.assertRaises(render.RenderExportError):
            render.build_visibility(broken_faces)
        broken_triangles = replace(self.mesh, triangles=self.mesh.triangles[:-1])
        with self.assertRaises(render.RenderExportError):
            render.build_visibility(broken_triangles)
        broken_points = replace(self.mesh, vertices=((float("inf"), 0.0, 0.0),) + self.mesh.vertices[1:])
        with self.assertRaises(render.RenderExportError):
            render.build_visibility(broken_points)

    def test_cosmetic_owner_relabels_and_reordered_topology_are_rejected(self):
        owner_cases = (
            ("domain.pelvis",) * len(self.mesh.face_owners),
            ("domain.pelvis",) * 16 + self.mesh.face_owners[16:],
        )
        for owners in owner_cases:
            with self.subTest(owners=owners[:17]), self.assertRaises(render.RenderExportError):
                render.build_visibility(replace(self.mesh, face_owners=owners))
        quads = list(self.mesh.quads)
        quads[0], quads[1] = quads[1], quads[0]
        quads = tuple(quads)
        triangles = tuple(item for face in quads for item in
                          ((face[0], face[1], face[2]), (face[0], face[2], face[3])))
        with self.assertRaises(render.RenderExportError):
            render.build_visibility(replace(self.mesh, quads=quads, triangles=triangles))

    def test_visibility_record_rejects_mutated_buffer_shape(self):
        visibility = _visibility()
        with self.assertRaises(render.RenderExportError):
            render.visibility_record(replace(visibility, owners=visibility.owners[:-1]))
        with self.assertRaises(render.RenderExportError):
            render.render_png_bytes(visibility, lineage=1)
        with self.assertRaises(render.RenderExportError):
            render.visibility_record(replace(visibility, triangle_index_sha256="x" * 64))
        with self.assertRaises(render.RenderExportError):
            render.render_png_bytes(replace(visibility, triangle_owners=("bad",) * 3328))
        with self.assertRaises(render.RenderExportError):
            render.visibility_record(replace(visibility, depths=(float("nan"),) + visibility.depths[1:]))
        with self.assertRaises(render.RenderExportError):
            render.visibility_record(replace(visibility, owners=(3328,) + visibility.owners[1:]))
        with self.assertRaises(render.RenderExportError):
            render.visibility_record(replace(visibility, degenerate_triangles=True))

    def test_depth_ties_retain_the_lower_triangle_index(self):
        owners = [None]
        depths = [None]
        render._accept_sample(owners, depths, 0, 8, 1.0)
        render._accept_sample(owners, depths, 0, 9, 1.0)
        self.assertEqual((owners[0], depths[0]), (8, 1.0))
        render._accept_sample(owners, depths, 0, 3, 1.0)
        self.assertEqual((owners[0], depths[0]), (3, 1.0))
        render._accept_sample(owners, depths, 0, 7, 2.0)
        self.assertEqual((owners[0], depths[0]), (7, 2.0))

    def test_png_is_rgb_metadata_free_and_fixed_size(self):
        data = render.render_png_bytes(_visibility())
        from PIL import Image
        with Image.open(BytesIO(data)) as image:
            self.assertEqual(image.info, {})
            self.assertEqual((image.mode, image.size, image.format), ("RGB", (512, 1536), "PNG"))
            self.assertEqual(image.getbbox(), (0, 0, 512, 1536))
    def test_row_candidates_are_bounded_and_triangle_ordered(self):
        screen = ((0.0, 0.0, 0.0), (4.0, 0.0, 1.0), (0.0, 4.0, 2.0), (4.0, 4.0, 3.0))
        records, rows, degenerate = render._panel_candidates(screen, ((0, 1, 2), (0, 2, 3)))
        self.assertEqual((len(records), degenerate), (2, 0))
        for row in rows:
            candidates = [item[0] for item in row]
            self.assertEqual(candidates, sorted(candidates))

    def test_png_has_only_frozen_chunks_and_lineage_domain_colours(self):
        direct, lineage, visibility = render.render_pair_bytes(self.mesh)
        def chunks(data):
            offset, result = 8, []
            while offset < len(data):
                size = int.from_bytes(data[offset:offset + 4], "big")
                result.append(data[offset + 4:offset + 8])
                offset += 12 + size
            return result
        self.assertEqual(chunks(direct), [b"IHDR", b"IDAT", b"IEND"])
        self.assertEqual(chunks(lineage), [b"IHDR", b"IDAT", b"IEND"])
        self.assertEqual(hashlib.sha256(direct).hexdigest(),
                         "b98d9cf219cad3c60ce43921fc86be7817529fd93448386860738b60110075ed")
        self.assertEqual(hashlib.sha256(lineage).hexdigest(),
                         "19a006f8f237857d94821894016364dcc446caece3358e9c6da0794a75bf74d2")
        self.assertEqual(set(render.PALETTE.values()), {
            render.PALETTE[owner] for owner in visibility.triangle_owners
        })


if __name__ == "__main__":
    unittest.main()
