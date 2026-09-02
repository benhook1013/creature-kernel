from __future__ import annotations

import ast
import copy
import dataclasses
from dataclasses import FrozenInstanceError
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np
from PIL import Image


REPO_ROOT = Path(__file__).resolve().parents[3]
EXPERIMENT_ROOT = REPO_ROOT / "experiments/current-form-surface-preview"
SOURCE_FORM = REPO_ROOT / "examples/body-documents/stylized-digitigrade-biped-authored-form.json"
CLI = REPO_ROOT / "target/debug/creature-kernel"
sys.path.insert(0, str(EXPERIMENT_ROOT))
import generate_structural_profile_sources as profile_generator  # noqa: E402

RENDERER_PATH = EXPERIMENT_ROOT / "regional_surface_preview.py"
RENDER_MESH_SAMPLES = 56
RENDERER_SPEC = importlib.util.spec_from_file_location("regional_surface_preview", RENDERER_PATH)
assert RENDERER_SPEC and RENDERER_SPEC.loader
renderer = importlib.util.module_from_spec(RENDERER_SPEC)
sys.modules[RENDERER_SPEC.name] = renderer
RENDERER_SPEC.loader.exec_module(renderer)


def inspection_command_prefix(cargo_path: str | None, cli_path: Path = CLI) -> list[str]:
    if cargo_path:
        return [cargo_path, "run", "-q", "-p", "creature-kernel-cli", "--"]
    if cli_path.is_file() and os.access(cli_path, os.X_OK):
        return [str(cli_path)]
    raise FileNotFoundError("neither cargo on PATH nor the bounded existing creature-kernel binary is available")


def valid_tetrahedron_proof(**overrides: object) -> SimpleNamespace:
    vertices = np.asarray(
        ((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)),
        dtype=np.float64,
    )
    faces = np.asarray(((0, 2, 1), (0, 1, 3), (0, 3, 2), (1, 2, 3)), dtype=np.int64)
    values: dict[str, object] = {
        "vertices": vertices,
        "faces": faces,
        "normals": np.zeros_like(vertices),
        "lower": (-0.1, -0.1, -0.1),
        "upper": (1.1, 1.1, 1.1),
        "samples": 20,
        "connected_components": 1,
        "boundary_edge_count": 0,
        "nonmanifold_edge_count": 0,
        "nonmanifold_vertex_count": 0,
        "watertight": True,
        "connected": True,
        "closed_triangle_2_manifold": True,
        "topology_proven": True,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


class InspectionCommandSelectionTests(unittest.TestCase):
    def test_inspection_command_prefers_discovered_cargo_then_bounded_binary_fallback(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ck-regional-command-selection-") as temporary:
            fallback = Path(temporary) / "creature-kernel"
            fallback.write_bytes(b"fixture")
            fallback.chmod(0o755)
            self.assertEqual(
                inspection_command_prefix("/resolved/toolchain/cargo", fallback),
                ["/resolved/toolchain/cargo", "run", "-q", "-p", "creature-kernel-cli", "--"],
            )
            self.assertEqual(inspection_command_prefix(None, fallback), [str(fallback)])
            with self.assertRaises(FileNotFoundError):
                inspection_command_prefix(None, Path(temporary) / "missing")


class RegionalSurfacePreviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._generated_sources = tempfile.TemporaryDirectory(prefix="ck-regional-surface-preview-sources-")
        generated_dir = Path(cls._generated_sources.name) / "sources"
        profile_generator.write_sources(
            EXPERIMENT_ROOT / "structural_profile_candidates.json",
            SOURCE_FORM,
            generated_dir,
        )

        command_prefix = inspection_command_prefix(shutil.which("cargo"))

        def inspect(path: Path) -> dict[str, object]:
            result = subprocess.run(
                [*command_prefix, "inspect-provisional-form", "--input", str(path)],
                cwd=REPO_ROOT,
                check=True,
                capture_output=True,
                text=True,
            )
            return json.loads(result.stdout)

        cls.profile_ids = tuple(renderer.EXTERNAL_PROFILE_IDS)
        cls.prepared_by_profile_id = {
            profile_id: inspect(generated_dir / f"{profile_id}.json")
            for profile_id in cls.profile_ids
        }
        cls.prepared = cls.prepared_by_profile_id[renderer.EXTERNAL_PROFILE_ID]
        cls.base_prepared = inspect(SOURCE_FORM)
        cls.results_by_profile_id = {}
        cls.render_failures_by_profile_id = {}
        for profile_id, prepared in cls.prepared_by_profile_id.items():
            try:
                cls.results_by_profile_id[profile_id] = renderer.render_regional_surface_preview(
                    prepared,
                    external_profile_id=profile_id,
                    mesh_padding=0.20,
                )
            except renderer.RegionalSurfacePreviewError as exc:
                cls.render_failures_by_profile_id[profile_id] = str(exc)
        cls.result = cls.results_by_profile_id[renderer.EXTERNAL_PROFILE_ID]

    @classmethod
    def tearDownClass(cls) -> None:
        cls._generated_sources.cleanup()

    @classmethod
    def candidate_for(cls, profile_id: str, mesh_samples: int | None = None):
        return renderer.regional_surface_candidate.build_regional_surface_candidate(
            renderer._prepared_form(cls.prepared_by_profile_id[profile_id], profile_id), profile_id="neutral-v0", mesh_samples=mesh_samples,
            mesh_padding=0.20,
        )

    @classmethod
    def candidate(cls, mesh_samples: int | None = None):
        return cls.candidate_for(renderer.EXTERNAL_PROFILE_ID, mesh_samples)

    @staticmethod
    def forge_field(candidate, interfaces=None, attachments=None):
        """Forge a copy only for validator-negative tests; never touch the live graph."""

        field = dataclasses.replace(candidate.field)
        if interfaces is not None:
            object.__setattr__(field, "interfaces", tuple(interfaces))
            object.__setattr__(field, "_junctions", tuple(interfaces))
        if attachments is not None:
            object.__setattr__(field, "attachments", tuple(attachments))
        return dataclasses.replace(candidate, field=field)

    def test_result_envelope_aliases_png_and_metadata_are_deterministic(self) -> None:
        self.assertIsInstance(self.result, renderer.RegionalSurfacePreviewResult)
        self.assertIs(self.result.image_bytes, self.result.png_bytes)
        self.assertEqual(self.result.png_bytes[:8], b"\x89PNG\r\n\x1a\n")
        with self.assertRaises(FrozenInstanceError):
            self.result.png_bytes = b"mutated"  # type: ignore[misc]
        json.dumps(self.result.metadata, sort_keys=True, allow_nan=False)

        repeated = renderer.render(self.prepared, mesh_padding=0.20)
        self.assertEqual(repeated.png_bytes, self.result.png_bytes)
        self.assertEqual(repeated.metadata, self.result.metadata)

        explicit_default = renderer.render(
            self.prepared,
            external_profile_id=renderer.EXTERNAL_PROFILE_ID,
            mesh_samples=RENDER_MESH_SAMPLES,
            mesh_padding=0.20,
        )
        self.assertEqual(explicit_default.png_bytes, self.result.png_bytes)
        self.assertEqual(explicit_default.metadata, self.result.metadata)

    def test_standard_neutral_binding_fixed_camera_and_actual_skin_arrays(self) -> None:
        metadata = self.result.metadata
        self.assertEqual(self.prepared["source"]["document"], renderer.EXPECTED_SOURCE_DOCUMENT)
        self.assertEqual(metadata["format"], "creature-kernel.disposable-regional-surface-preview.v2")
        self.assertEqual(
            metadata["candidate_binding"]["candidate_format"],
            "creature-kernel.disposable-regional-surface-candidate.v3",
        )
        self.assertEqual(metadata["profile_id"], renderer.EXTERNAL_PROFILE_ID)
        self.assertEqual(metadata["source_variant_id"], renderer.SOURCE_VARIANT_ID)
        self.assertEqual(metadata["camera"]["views"], ["front", "side", "three-quarter"])
        self.assertEqual(metadata["camera"]["canvas"], {"width": 1800, "height": 1500, "mode": "RGB"})
        self.assertEqual(
            metadata["layout"]["panel_order"],
            [
                "front-skin", "side-skin", "three-quarter-skin",
                "front-field-contributors", "side-field-contributors", "three-quarter-field-contributors",
                "front-source-diagnostics", "side-source-diagnostics", "three-quarter-source-diagnostics",
            ],
        )
        mesh = metadata["mesh"]
        self.assertEqual(mesh["samples_per_axis"], RENDER_MESH_SAMPLES)
        self.assertEqual(mesh["padding"], 0.20)
        self.assertTrue(mesh["topology_proof"]["proven"])
        self.assertEqual(metadata["png"]["sha256"], hashlib.sha256(self.result.png_bytes).hexdigest())
        self.assertEqual(metadata["png"]["bytes"], len(self.result.png_bytes))

        with Image.open(__import__("io").BytesIO(self.result.png_bytes)) as image:
            self.assertEqual((image.format, image.mode, image.size), ("PNG", "RGB", (1800, 1500)))
            image.load()

    def test_mapping_and_form_identity_hash_kinds_are_honest(self) -> None:
        form = renderer._prepared_form(self.prepared)
        mapping_identity = renderer._prepared_identity(self.prepared, form)
        expected_hash = hashlib.sha256(renderer._canonical(renderer._jsonable(form.raw))).hexdigest()
        self.assertEqual(mapping_identity["hash_kind"], "canonical-prepared-envelope")
        self.assertEqual(mapping_identity["sha256"], expected_hash)
        form_identity = renderer._prepared_identity(form, form)
        self.assertEqual(form_identity["hash_kind"], renderer.FORM_REDUCED_INVENTORY_HASH_KIND)
        self.assertNotEqual(form_identity["sha256"], mapping_identity["sha256"])

    def test_wrong_source_bindings_are_rejected_before_candidate_build(self) -> None:
        with patch.object(renderer.regional_surface_candidate, "build_regional_surface_candidate") as builder:
            with self.assertRaises(renderer.RegionalSurfacePreviewError):
                renderer.render_regional_surface_preview(self.base_prepared, mesh_samples=20, mesh_padding=0.20)
            builder.assert_not_called()

        wrong_namespace = copy.deepcopy(self.prepared)
        wrong_namespace["source"]["namespace"] = "foreign"
        with patch.object(renderer.regional_surface_candidate, "build_regional_surface_candidate") as builder:
            with self.assertRaises(renderer.RegionalSurfacePreviewError):
                renderer.render_regional_surface_preview(wrong_namespace, mesh_samples=20, mesh_padding=0.20)
            builder.assert_not_called()

        mismatched_profile = renderer.EXTERNAL_PROFILE_IDS[1]
        with patch.object(renderer.regional_surface_candidate, "build_regional_surface_candidate") as builder:
            with self.assertRaises(renderer.RegionalSurfacePreviewError):
                renderer.render_regional_surface_preview(
                    self.prepared,
                    external_profile_id=mismatched_profile,
                    mesh_samples=20,
                    mesh_padding=0.20,
                )
            builder.assert_not_called()

        wrong_resource = copy.deepcopy(self.prepared)
        wrong_resource["source"]["resource_profile_id"] = "ck.resource.body.other"
        with patch.object(renderer.regional_surface_candidate, "build_regional_surface_candidate") as builder:
            with self.assertRaises(renderer.RegionalSurfacePreviewError):
                renderer.render_regional_surface_preview(wrong_resource, mesh_samples=20, mesh_padding=0.20)
            builder.assert_not_called()

    def test_exact_five_generated_profiles_keep_external_source_and_neutral_candidate_bindings(self) -> None:
        self.assertEqual(
            self.profile_ids,
            (
                "standard_neutral_reference",
                "compact_broad_short_limb_large_head",
                "tall_narrow_long_legged",
                "slender_long_limb",
                "stocky_broad_chested",
            ),
        )
        self.assertEqual(self.profile_ids, tuple(profile_generator.ACTIVE_PROFILE_IDS))

        geometry_selection = "fixed neutral-v0; external profile identity does not branch geometry"
        prepared_hashes = set()
        source_hashes = set()
        png_hashes = []
        common_candidate_shape = None
        rendered_count = 0
        for profile_id in self.profile_ids:
            with self.subTest(profile_id=profile_id):
                expected_document = (
                    "stylized_digitigrade_biped_authored_form__structural_profile__"
                    f"{profile_id}"
                )
                prepared = self.prepared_by_profile_id[profile_id]
                self.assertEqual(prepared["source"]["document"], expected_document)
                self.assertEqual(prepared["source"]["namespace"], "main")
                self.assertEqual(prepared["source"]["resource_profile_id"], "ck.resource.body.r2")
                form = renderer._prepared_form(prepared, profile_id)
                prepared_identity = renderer._prepared_identity(prepared, form)
                self.assertEqual(prepared_identity["document"], expected_document)
                prepared_hashes.add(prepared_identity["sha256"])
                source_hashes.add(prepared_identity["sha256"])

                candidate = self.candidate_for(profile_id)
                field, chain, routes, interfaces, controls = renderer._validate_candidate_contract(candidate, form)
                self.assertEqual(candidate.source["document"], expected_document)
                self.assertEqual(candidate.profile_id, renderer.SOURCE_VARIANT_ID)
                self.assertEqual(candidate.metadata["profile_id"], renderer.SOURCE_VARIANT_ID)
                self.assertEqual(candidate.metadata["variant_source"]["id"], renderer.SOURCE_VARIANT_ID)
                operands = renderer._candidate_operands(candidate)
                candidate_shape = {
                    "graph": {
                        "field_type": f"{type(field).__module__}.{type(field).__qualname__}",
                        "base_type": f"{type(chain).__module__}.{type(chain).__qualname__}",
                        "routes": tuple(
                            (route.route_name, tuple(section.name for section in route.sections), len(route.connections))
                            for route in routes
                        ),
                        "controls": tuple(control.name for control in controls),
                        "interfaces": tuple(
                            (item.identifier, item.parent_name, item.child_name)
                            for item in interfaces
                        ),
                    },
                    "layout": renderer._layout_metadata(),
                    "inventory": tuple(
                        (item.identifier, item.kind, item.semantic_identity, type(item.evaluator).__qualname__)
                        for item in operands
                    ),
                }
                if common_candidate_shape is None:
                    common_candidate_shape = candidate_shape
                else:
                    self.assertEqual(candidate_shape, common_candidate_shape)

                result = self.results_by_profile_id.get(profile_id)
                if result is None:
                    self.fail(
                        f"{profile_id} did not produce a proven in-memory render: "
                        f"{self.render_failures_by_profile_id[profile_id]}"
                    )

                rendered_count += 1
                metadata = result.metadata
                source = metadata["source"]
                self.assertEqual(metadata["profile_id"], profile_id)
                self.assertEqual(metadata["source_variant_id"], renderer.SOURCE_VARIANT_ID)
                self.assertEqual(source["document"], expected_document)
                self.assertEqual(source["namespace"], "main")
                self.assertEqual(source["resource_profile_id"], "ck.resource.body.r2")
                self.assertEqual(source["variant_id"], renderer.SOURCE_VARIANT_ID)
                self.assertEqual(metadata["prepared_input"]["document"], expected_document)
                self.assertEqual(metadata["prepared_input"]["namespace"], "main")
                self.assertEqual(metadata["prepared_input"]["resource_profile_id"], "ck.resource.body.r2")
                self.assertEqual(metadata["prepared_input"]["sha256"], prepared_identity["sha256"])

                expected_binding = {
                    "external_profile_id": profile_id,
                    "source_variant_id": renderer.SOURCE_VARIANT_ID,
                    "geometry_selection": geometry_selection,
                }
                self.assertEqual(metadata["identity"]["binding"], expected_binding)
                self.assertEqual(metadata["candidate_binding"]["external_profile_id"], profile_id)
                self.assertEqual(metadata["candidate_binding"]["source_variant_id"], renderer.SOURCE_VARIANT_ID)
                self.assertEqual(metadata["candidate_binding"]["geometry_selection"], geometry_selection)
                self.assertEqual(metadata["identity"]["candidate"]["profile_id"], renderer.SOURCE_VARIANT_ID)
                self.assertEqual(metadata["identity"]["candidate"]["source_variant_id"], renderer.SOURCE_VARIANT_ID)
                self.assertEqual(metadata["candidate_metadata"]["source"]["document"], expected_document)
                self.assertEqual(metadata["candidate_metadata"]["profile_id"], renderer.SOURCE_VARIANT_ID)
                self.assertEqual(metadata["candidate_metadata"]["variant_source"]["id"], renderer.SOURCE_VARIANT_ID)

                topology = metadata["mesh"]["topology_proof"]
                self.assertTrue(topology["connected"])
                self.assertTrue(topology["watertight"])
                self.assertTrue(topology["closed_triangle_2_manifold"])
                self.assertEqual(topology["connected_components"], 1)
                self.assertEqual(topology["boundary_edge_count"], 0)
                self.assertEqual(topology["nonmanifold_edge_count"], 0)
                self.assertEqual(topology["nonmanifold_vertex_count"], 0)

                png_hashes.append(metadata["png"]["sha256"])

        self.assertEqual(len(prepared_hashes), len(self.profile_ids))
        self.assertEqual(len(source_hashes), len(self.profile_ids))
        self.assertEqual(rendered_count, len(self.profile_ids))
        self.assertEqual(self.render_failures_by_profile_id, {})
        self.assertEqual(
            set(self.results_by_profile_id) | set(self.render_failures_by_profile_id),
            set(self.profile_ids),
        )
        distinct_png_count = len(set(png_hashes))
        print(
            f"exact-five renderer real renders={rendered_count}/{len(self.profile_ids)}; "
            f"PNG hashes distinct={distinct_png_count}/{len(png_hashes)}; "
            f"topology-unavailable={sorted(self.render_failures_by_profile_id)}"
        )

    def test_unsupported_and_unsafe_external_profile_ids_are_rejected(self) -> None:
        invalid_ids = (
            "unknown_profile",
            "../standard_neutral_reference",
            "standard_neutral_reference/other",
            "standard-neutral-reference",
            "",
            None,
        )
        for external_profile_id in invalid_ids:
            with self.subTest(external_profile_id=external_profile_id):
                with patch.object(renderer.regional_surface_candidate, "build_regional_surface_candidate") as builder:
                    with self.assertRaises(renderer.RegionalSurfacePreviewError):
                        renderer.render_regional_surface_preview(
                            self.prepared,
                            external_profile_id=external_profile_id,
                            mesh_samples=20,
                            mesh_padding=0.20,
                        )
                    builder.assert_not_called()

    def test_exact_public_graph_has_eight_sources_seven_patches_and_four_authority_controls(self) -> None:
        candidate = self.candidate()
        field, chain, routes, interfaces, controls = renderer._validate_candidate_graph(candidate)
        self.assertFalse(hasattr(candidate, "roots"))
        self.assertNotIn("roots", candidate.metadata)
        self.assertIs(candidate.interfaces, field.interfaces)
        self.assertIs(field.base, chain)
        self.assertEqual(tuple(route.route_name for route in routes), renderer.EXPECTED_ROUTE_NAMES)
        self.assertEqual(tuple(control.name for control in controls), renderer.EXPECTED_CONTROL_NAMES)
        self.assertEqual(len(field.attachments), 7)
        self.assertEqual(len(field.interfaces), 7)
        self.assertEqual(
            tuple((patch.parent_name, patch.child_name) for patch in interfaces),
            tuple(sorted(renderer.EXPECTED_INTERFACE_RELATIONS)),
        )
        self.assertEqual([len(route.sections) for route in routes], [8, 6, 6, 8, 8, 3, 3])
        for route in routes[1:3]:
            with self.subTest(route=route.route_name):
                self.assertEqual(tuple(section.name for section in route.sections), renderer.EXPECTED_ROUTE_SECTIONS[route.route_name])
                self.assertEqual(
                    tuple((connection.from_section_index, connection.to_section_index) for connection in route.connections),
                    ((0, 1), (1, 2), (2, 3), (3, 4), (4, 5)),
                )
                self.assertIsNone(route.sections[0].source_index)
                self.assertEqual(tuple(section.source_index for section in route.sections[1:]), (0, 1, 2, 3, 4))
                self.assertEqual((route.sections[3].name, route.sections[3].source_index), ("elbow", 2))
                shoulder_closure = route.endpoint_closures[0]
                self.assertEqual(shoulder_closure.name, f"{route.route_name}:shoulder-closure")
                self.assertEqual(shoulder_closure.center, route.sections[1].center)
                self.assertEqual(shoulder_closure.radii, route.sections[1].radii)
                self.assertEqual(shoulder_closure.source_key, route.sections[1].source_key)
        for route in routes[3:5]:
            with self.subTest(route=route.route_name):
                self.assertEqual(tuple(section.name for section in route.sections), renderer.EXPECTED_ROUTE_SECTIONS[route.route_name])
                self.assertEqual(
                    tuple((connection.from_section_index, connection.to_section_index) for connection in route.connections),
                    ((0, 1), (1, 2), (2, 3), (3, 4), (4, 5), (5, 6), (6, 7)),
                )
                self.assertEqual([section.source_index for section in route.sections[:3]], [None, None, None])
                self.assertEqual(tuple(section.source_index for section in route.sections[3:]), (0, 1, 2, 3, 4))
                self.assertEqual((route.sections[5].name, route.sections[5].source_index), ("knee", 2))
                self.assertEqual((route.sections[7].name, route.sections[7].source_index), ("hock-endpoint", 4))
                hip_closure = route.endpoint_closures[0]
                self.assertEqual(hip_closure.name, f"{route.route_name}:hip-cup-rim-closure")
                self.assertEqual(hip_closure.center, route.sections[1].center)
                self.assertEqual(hip_closure.radii, route.sections[1].radii)
                self.assertEqual(hip_closure.source_key, route.sections[1].source_key)
                self.assertNotEqual(hip_closure.source_key, route.sections[0].source_key)
        self.assertIs(routes[3].sections[-1], routes[5].sections[0])
        self.assertIs(routes[4].sections[-1], routes[6].sections[0])
        self.assertTrue(all(attachment.authority is None and attachment.blend_radius is None for attachment in field.attachments))
        self.assertTrue(
            all(
                patch.parent is chain if patch.parent_name == "torso" else any(item is patch.parent for item in routes)
                for patch in interfaces
            )
        )
        self.assertTrue(all(any(item is patch.child for item in routes) for patch in interfaces))
        self.assertFalse(hasattr(candidate, "saddle"))

        operands = renderer._candidate_operands(candidate)
        self.assertEqual(len(operands), 15)
        self.assertEqual([item.kind for item in operands].count("skin-source"), 8)
        self.assertEqual([item.kind for item in operands].count("derived-interface-patch"), 7)
        self.assertIs(operands[0].evaluator, chain)
        self.assertTrue(all(item.evaluator not in controls for item in operands))
        self.assertTrue(all(control not in field.components for control in controls))
        self.assertTrue(all(
            patch.parent not in controls and patch.child not in controls
            for patch in interfaces
        ))

        legacy_metadata = dict(candidate.metadata)
        legacy_metadata["roots"] = {"status": "legacy"}
        validated = renderer._validate_candidate_contract(dataclasses.replace(candidate, metadata=legacy_metadata))
        self.assertIs(validated[0], candidate.field)

    def test_render_metadata_splits_truthful_inventories_and_omits_legacy_graph_projection(self) -> None:
        metadata = self.result.metadata
        inventory = metadata["diagnostic_inventory"]
        self.assertEqual(set(inventory), {"skin_sources", "derived_patches", "authority_controls"})
        self.assertEqual(len(inventory["skin_sources"]), 8)
        self.assertEqual(len(inventory["derived_patches"]), 7)
        self.assertEqual(len(inventory["authority_controls"]), 4)
        self.assertEqual(
            {item["kind"] for group in inventory.values() for item in group},
            {"skin-source", "derived-interface-patch", "authority-only-control"},
        )
        graph = metadata["candidate_graph"]
        self.assertEqual(graph["skin_source_count"], 8)
        self.assertEqual(graph["derived_patch_count"], 7)
        self.assertTrue(graph["final_field_type"].endswith("FullSectionComposite"))
        self.assertEqual(graph["interfaces"], sorted(graph["interfaces"]))
        self.assertNotIn("controls", graph)
        self.assertNotIn("junction_count", graph)
        self.assertNotIn("roots", metadata["candidate_metadata"])
        self.assertNotIn("pelvic_saddle", metadata["candidate_metadata"])

        diagnostics = metadata["diagnostics"]
        self.assertEqual(diagnostics["skin_source_count"], 8)
        self.assertEqual(diagnostics["derived_patch_count"], 7)
        self.assertEqual(diagnostics["authority_control_count"], 4)
        self.assertEqual(len(diagnostics["operands"]), 15)
        self.assertEqual(diagnostics["final_field_graph"]["final_term_count"], 15)
        self.assertEqual(len(diagnostics["skin_sources"]), 8)
        self.assertEqual(len(diagnostics["derived_patches"]), 7)
        self.assertEqual(len(diagnostics["authority_controls"]), 4)
        self.assertTrue(all(item["surface"]["vertex_count"] > 0 for item in diagnostics["operands"]))

    def test_candidate_metadata_is_a_compact_live_summary(self) -> None:
        candidate_metadata = self.result.metadata["candidate_metadata"]
        self.assertEqual(
            set(candidate_metadata),
            {"format", "source", "profile_id", "variant_source", "torso", "routes", "interfaces", "shoulder_controls", "proof"},
        )
        self.assertEqual(
            set(candidate_metadata["torso"]),
            {"stations", "regions", "station_count", "region_count", "region_intervals"},
        )
        self.assertEqual(
            set(candidate_metadata["torso"]["stations"][0]),
            {"index", "name", "semantic_key"},
        )
        self.assertEqual(
            set(candidate_metadata["routes"]["routes"][0]),
            {"name", "kind", "side", "section_count", "sections", "connection_count", "connections", "shared_station_indices", "hip_cup_sections", "endpoint_closures", "attachment"},
        )
        self.assertEqual(
            set(candidate_metadata["routes"]["routes"][0]["sections"][0]),
            {"index", "name", "source_key", "semantic_key", "source_index", "derived"},
        )
        self.assertEqual(
            set(candidate_metadata["routes"]["routes"][0]["endpoint_closures"][0]),
            {"name", "source_key"},
        )
        self.assertEqual(
            set(candidate_metadata["interfaces"]["patches"][0]),
            {"identifier", "parent", "child", "semantic_key", "authority"},
        )
        self.assertEqual(
            candidate_metadata["interfaces"]["parent_relations"],
            [list(item) for item in renderer.EXPECTED_INTERFACE_RELATIONS],
        )
        route_metadata = candidate_metadata["routes"]
        self.assertEqual(route_metadata["bilateral_arm_authored_sections"], [5, 5])
        self.assertEqual(route_metadata["bilateral_arm_total_sections"], [6, 6])
        self.assertNotIn("bilateral_arm_sections", route_metadata)
        self.assertEqual(route_metadata["shared_interfaces"]["elbows"], [3, 3])
        for arm in route_metadata["routes"][1:3]:
            with self.subTest(route=arm["name"]):
                self.assertEqual(arm["section_count"], 6)
                self.assertEqual(arm["connection_count"], 5)
                self.assertEqual(arm["shared_station_indices"], [3])
                self.assertTrue(arm["sections"][0]["derived"])
                self.assertIsNone(arm["sections"][0]["source_index"])
                self.assertEqual([section["source_index"] for section in arm["sections"][1:]], [0, 1, 2, 3, 4])
                self.assertEqual((arm["sections"][3]["name"], arm["sections"][3]["source_index"]), ("elbow", 2))
                self.assertEqual(arm["endpoint_closures"][0]["source_key"], arm["sections"][1]["source_key"])
        self.assertEqual(route_metadata["bilateral_leg_authored_sections"], [5, 5])
        self.assertEqual(route_metadata["bilateral_leg_total_sections"], [8, 8])
        self.assertNotIn("bilateral_leg_sections", route_metadata)
        self.assertEqual(route_metadata["shared_interfaces"]["knees"], [5, 5])
        self.assertEqual(route_metadata["shared_interfaces"]["hocks"], [7, 7])
        for leg in route_metadata["routes"][3:5]:
            with self.subTest(route=leg["name"]):
                self.assertEqual(leg["section_count"], 8)
                self.assertEqual(leg["connection_count"], 7)
                self.assertEqual(leg["shared_station_indices"], [5, 7])
                self.assertEqual([section["source_index"] for section in leg["sections"][:3]], [None, None, None])
                self.assertEqual([section["source_index"] for section in leg["sections"][3:]], [0, 1, 2, 3, 4])
                self.assertEqual((leg["sections"][5]["name"], leg["sections"][5]["source_index"]), ("knee", 2))
                self.assertEqual((leg["sections"][7]["name"], leg["sections"][7]["source_index"]), ("hock-endpoint", 4))
                self.assertEqual(leg["endpoint_closures"][0]["source_key"], leg["sections"][1]["source_key"])
        for side_index, foot in enumerate(route_metadata["routes"][5:]):
            side = ("left", "right")[side_index]
            leg = route_metadata["routes"][3 + side_index]
            borrowed = foot["sections"][0]
            owner = {"namespace": "main", "anchors": [side], "kind": "part", "role": "shin"}
            self.assertEqual(borrowed["binding_kind"], "borrowed-shared-leg-station")
            self.assertFalse(borrowed["authored_in_foot_route"])
            self.assertEqual(borrowed["route_index"], 0)
            self.assertEqual(borrowed["source_route"], f"{side}-leg")
            self.assertEqual(borrowed["shared_with"], f"{side}-leg")
            self.assertEqual(borrowed["owner"], owner)
            self.assertEqual(borrowed["source_index"], 4)
            self.assertEqual(borrowed["source_key"], leg["sections"][7]["source_key"])
            self.assertEqual(borrowed["semantic_key"], leg["sections"][7]["semantic_key"])
            self.assertEqual(
                borrowed["leg_authored_identity"],
                {
                    "route": f"{side}-leg",
                    "name": "hock-endpoint",
                    "source_index": 4,
                    "owner": owner,
                "source_key": leg["sections"][7]["source_key"],
                "semantic_key": leg["sections"][7]["semantic_key"],
                },
            )
        self.assertEqual(
            set(candidate_metadata["shoulder_controls"]["controls"][0]),
            {
                "name", "namespace", "side", "owner", "role", "frame", "frame_role",
                "semantic_key", "source_key", "canonical_source_key", "authority_only", "skin_consumer",
                "counterfactual_authority_bound_influence", "control_local_final_skin_influence",
                "control_local_final_skin_influence_status", "visual_floor_satisfaction", "interface_id",
            },
        )
        self.assertNotIn("axial_caps", candidate_metadata["torso"])
        self.assertNotIn("pelvic_saddle", candidate_metadata)
        self.assertNotIn("center", candidate_metadata["torso"]["stations"][0])
        self.assertNotIn("radii", candidate_metadata["routes"]["routes"][0]["sections"][0])
        self.assertNotIn("points", candidate_metadata["interfaces"]["patches"][0])
        self.assertNotIn("k", candidate_metadata["interfaces"]["patches"][0])

    def test_forged_rich_candidate_metadata_cannot_leak_into_successful_output(self) -> None:
        mutations = {
            "torso center": lambda metadata: metadata["torso"]["stations"][0].update(center=[901.0, 902.0, 903.0]),
            "route radius": lambda metadata: metadata["routes"]["routes"][0]["sections"][0].update(radii=[904.0, 905.0, 906.0]),
            "interface point": lambda metadata: metadata["interfaces"]["patches"][0]["authority"].update(points=[[907.0, 908.0, 909.0]]),
            "interface k": lambda metadata: metadata["interfaces"]["patches"][0]["authority"].update(k=910.0),
            "stale pelvic saddle": lambda metadata: metadata.update({"pelvic_saddle": {"status": "stale-forged", "cup_count": 99}}),
            "sidecar cleared": lambda metadata: metadata.clear(),
        }
        candidate = self.candidate(mesh_samples=RENDER_MESH_SAMPLES)
        for label, mutate in mutations.items():
            with self.subTest(label=label):
                forged_metadata = copy.deepcopy(candidate.metadata)
                mutate(forged_metadata)
                forged_candidate = dataclasses.replace(candidate, metadata=forged_metadata)
                with patch.object(
                    renderer.regional_surface_candidate,
                    "build_regional_surface_candidate",
                    return_value=forged_candidate,
                ):
                    rendered = renderer.render_regional_surface_preview(
                        self.prepared,
                        mesh_samples=RENDER_MESH_SAMPLES,
                        mesh_padding=0.20,
                    )
                self.assertEqual(rendered.metadata["candidate_metadata"], self.result.metadata["candidate_metadata"])
                self.assertNotIn("pelvic_saddle", rendered.metadata["candidate_metadata"])
                self.assertNotIn("center", rendered.metadata["candidate_metadata"]["torso"]["stations"][0])
                self.assertNotIn("radii", rendered.metadata["candidate_metadata"]["routes"]["routes"][0]["sections"][0])
                self.assertNotIn("points", rendered.metadata["candidate_metadata"]["interfaces"]["patches"][0])
                self.assertNotIn("k", rendered.metadata["candidate_metadata"]["interfaces"]["patches"][0])

    def test_path_witnesses_reconstruct_and_all_exact_five_controls_change_skin_through_authority(self) -> None:
        witnesses = self.result.metadata["diagnostics"]["witnesses"]
        self.assertEqual(len(witnesses), 21)
        self.assertEqual([item["identifier"] for item in witnesses[:3]], ["region:pelvis", "region:abdominal-bridge", "region:ribcage"])
        self.assertEqual([item["identifier"] for item in witnesses[3:10]], [f"route:{name}" for name in renderer.EXPECTED_ROUTE_NAMES])
        self.assertEqual(
            [item["identifier"] for item in witnesses[10:17]],
            [f"patch:{parent}->{child}" for parent, child in renderer.EXPECTED_INTERFACE_RELATIONS],
        )
        self.assertEqual([item["identifier"] for item in witnesses[17:]], [f"control:{name}" for name in renderer.EXPECTED_CONTROL_NAMES])

        for witness in witnesses[:17]:
            self.assertLessEqual(witness["reconstruction_error"], renderer.TRACE_TOLERANCE)
            self.assertTrue(witness["nonzero_geometric_influence"])
            self.assertGreater(witness["expected_component_influence"], renderer.INFLUENCE_TOLERANCE)
            self.assertEqual(witness["operation_trace"]["value"], witness["reconstructed_value"])
            self.assertTrue(witness["source_semantic_keys"])
        for witness in witnesses[10:17]:
            self.assertEqual(witness["final_term_kind"], "derived-interface-patch")
            self.assertEqual(set(witness["interface"]), {"identifier", "semantic_identity", "parent", "child", "authority"})
            self.assertEqual(witness["interface"]["semantic_identity"], witness["expected_semantic_identity"])
            pending = [witness["operation_trace"]]
            matching_patch_nodes = []
            while pending:
                node = pending.pop()
                if (
                    node["operator"] == "parent-targeted-interface-patch"
                    and node["authority_id"] == witness["interface"]["authority"]
                    and node["parent_id"] == witness["interface"]["parent"]
                    and node["child_id"] == witness["interface"]["child"]
                ):
                    matching_patch_nodes.append(node)
                pending.extend(node["children"])
            self.assertEqual(len(matching_patch_nodes), 1)
            self.assertEqual(len(matching_patch_nodes[0]["children"]), 2)
            self.assertEqual(len(matching_patch_nodes[0]["sensitivity"]), 2)
        for witness in witnesses[17:]:
            self.assertEqual(witness["final_term_kind"], "authority-only-control")
            self.assertEqual(witness["counterfactual_authority_bound_influence"], "proven")
            self.assertFalse(witness["control_local_final_skin_influence"])
            self.assertEqual(witness["control_local_final_skin_influence_status"], "unverified")
            self.assertEqual(witness["visual_floor_satisfaction"], "unverified")
            self.assertTrue(witness["near_zero"])
            self.assertGreater(witness["counterfactual_delta"], renderer.INFLUENCE_TOLERANCE)
            self.assertGreater(witness["authority_bound_influence_weight"], renderer.INFLUENCE_TOLERANCE)
            self.assertNotEqual(witness["full_authority_gate"], witness["omitted_input_gate"])
            self.assertLessEqual(
                witness["counterfactual_delta"],
                witness["maximum_displacement"] + renderer.TRACE_TOLERANCE,
            )
            self.assertEqual(witness["interface"]["identifier"], witness["expected_path"].removeprefix("authority:"))
            self.assertTrue(witness["source_trace_semantic_keys"])
            self.assertNotIn(witness["expected_semantic_identity"], witness["trace_semantic_keys"])

        for profile_id, result in self.results_by_profile_id.items():
            with self.subTest(profile_id=profile_id):
                control_witnesses = result.metadata["diagnostics"]["witnesses"][17:]
                self.assertEqual(len(control_witnesses), 4)
                self.assertTrue(all(item["near_zero"] for item in control_witnesses))
                self.assertTrue(all(item["counterfactual_delta"] > renderer.INFLUENCE_TOLERANCE for item in control_witnesses))
                self.assertTrue(all(item["expected_component_influence"] > renderer.INFLUENCE_TOLERANCE for item in control_witnesses))
                self.assertTrue(all(item["counterfactual_authority_bound_influence"] == "proven" for item in control_witnesses))
                self.assertTrue(all(item["control_local_final_skin_influence"] is False for item in control_witnesses))
                self.assertTrue(all(item["control_local_final_skin_influence_status"] == "unverified" for item in control_witnesses))

    def test_missing_extra_and_undeclared_patches_fail_closed(self) -> None:
        candidate = self.candidate()
        with self.assertRaises(renderer.RegionalSurfacePreviewError):
            renderer._validate_candidate_graph(self.forge_field(candidate, interfaces=candidate.interfaces[:-1]))

        with self.assertRaises(renderer.RegionalSurfacePreviewError):
            renderer._validate_candidate_graph(self.forge_field(candidate, interfaces=(*candidate.interfaces, candidate.interfaces[0])))

        hybrid = renderer.regional_surface_candidate._load_hybrid()
        extra = hybrid.ParentTargetedInterfacePatch(
            "interface:torso->left-foot", "torso", "left-foot", candidate.chain, candidate.routes[5],
            hybrid.AuthorityVolume("authority:torso->left-foot", candidate.routes[5].sections[0].center, (0.3, 0.3, 0.3)),
            0.04, "interface:torso->left-foot",
        )
        with self.assertRaises(renderer.RegionalSurfacePreviewError):
            renderer._validate_candidate_graph(self.forge_field(candidate, interfaces=(extra, *candidate.interfaces[1:])))

    def test_wrong_parent_aggregate_parent_and_control_as_skin_fail_closed(self) -> None:
        candidate = self.candidate()
        hybrid = renderer.regional_surface_candidate._load_hybrid()

        wrong_parent = dataclasses.replace(candidate.interfaces[0], parent=candidate.routes[0])
        bad_field = dataclasses.replace(candidate.field)
        bad_interfaces = (wrong_parent, *candidate.interfaces[1:])
        object.__setattr__(bad_field, "interfaces", bad_interfaces)
        object.__setattr__(bad_field, "_junctions", bad_interfaces)
        with self.assertRaises(renderer.RegionalSurfacePreviewError):
            renderer._validate_candidate_graph(dataclasses.replace(candidate, field=bad_field))

        aggregate_parent = dataclasses.replace(candidate.interfaces[0], parent=candidate.field)
        aggregate_field = dataclasses.replace(candidate.field)
        aggregate_interfaces = (aggregate_parent, *candidate.interfaces[1:])
        object.__setattr__(aggregate_field, "interfaces", aggregate_interfaces)
        object.__setattr__(aggregate_field, "_junctions", aggregate_interfaces)
        with self.assertRaises(renderer.RegionalSurfacePreviewError):
            renderer._validate_candidate_graph(dataclasses.replace(candidate, field=aggregate_field))

        control_attachment = hybrid.SectionAttachment("left-arm", candidate.controls[0], None, None, "route:left-arm")
        with self.assertRaises(renderer.RegionalSurfacePreviewError):
            renderer._validate_candidate_graph(
                self.forge_field(candidate, attachments=(control_attachment, *candidate.field.attachments[1:]))
            )

    def test_missing_final_influence_and_trace_report_disagreement_fail_closed(self) -> None:
        candidate = self.candidate()
        route = candidate.routes[0]
        point = renderer._active_component_witness_point(candidate, route, "route:head-neck", "head-neck")
        original_report = candidate.contribution_report

        def report_with_zero(point_value):
            report = copy.deepcopy(original_report(point_value))
            report["geometric_influence"]["components"]["head-neck"] = 0.0
            return report

        zero_candidate = SimpleNamespace(
            evaluate=candidate.evaluate, operation_trace=candidate.operation_trace, contribution_report=report_with_zero,
        )
        with self.assertRaises(renderer.RegionalSurfacePreviewError):
            renderer._capture_witness(zero_candidate, "route:head-neck", point, "route:head-neck", "head-neck")

        def report_with_disagreement(point_value):
            report = copy.deepcopy(original_report(point_value))
            report["geometric_influence"]["components"]["head-neck"] += 0.25
            return report

        disagreeing_candidate = SimpleNamespace(
            evaluate=candidate.evaluate, operation_trace=candidate.operation_trace, contribution_report=report_with_disagreement,
        )
        with self.assertRaises(renderer.RegionalSurfacePreviewError):
            renderer._capture_witness(disagreeing_candidate, "route:head-neck", point, "route:head-neck", "head-neck")

    def test_malformed_mesh_proofs_are_rejected_independently(self) -> None:
        empty = valid_tetrahedron_proof(
            vertices=np.empty((0, 3), dtype=np.float64), faces=np.empty((0, 3), dtype=np.int64), normals=np.empty((0, 3), dtype=np.float64),
        )
        with self.assertRaises(renderer.RegionalSurfacePreviewError):
            renderer._mesh_metadata(empty, 0.20)

        degenerate = valid_tetrahedron_proof(
            faces=np.asarray(((0, 0, 1), (0, 1, 3), (0, 3, 2), (1, 2, 3)), dtype=np.int64)
        )
        with self.assertRaises(renderer.RegionalSurfacePreviewError):
            renderer._mesh_metadata(degenerate, 0.20)

        boundary = valid_tetrahedron_proof(
            faces=np.asarray(((0, 2, 1), (0, 1, 3), (0, 3, 2)), dtype=np.int64)
        )
        with self.assertRaises(renderer.RegionalSurfacePreviewError):
            renderer._mesh_metadata(boundary, 0.20)

    def test_renderer_has_no_forbidden_successor_import(self) -> None:
        source = RENDERER_PATH.read_text(encoding="utf-8")
        forbidden = "successor_" + "surface_preview"
        self.assertNotIn(forbidden, source)
        tree = ast.parse(source)
        imported = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.append(node.module)
        self.assertFalse(any(forbidden in name for name in imported))


if __name__ == "__main__":
    unittest.main()
