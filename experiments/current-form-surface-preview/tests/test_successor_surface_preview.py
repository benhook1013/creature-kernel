from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
FIXTURE_SPEC = importlib.util.spec_from_file_location("successor_fixture", Path(__file__).with_name("test_surface_preview.py"))
assert FIXTURE_SPEC and FIXTURE_SPEC.loader
fixture = importlib.util.module_from_spec(FIXTURE_SPEC)
FIXTURE_SPEC.loader.exec_module(fixture)
sys.path.insert(0, str(ROOT))
import surface_preview  # noqa: E402
import successor_surface_preview as successor  # noqa: E402


class SuccessorSurfacePreviewTests(unittest.TestCase):
    def setUp(self) -> None:
        self.form = surface_preview.validate_envelope(fixture.make_varied_payload())

    def test_successor_consumes_ordered_cage_and_real_shoulder_inputs(self) -> None:
        _, descriptors, _ = self.form.variants[0]
        guide = surface_preview._derive_hybrid_guides(self.form, descriptors)
        baseline_fields = surface_preview._compile_hybrid_guide(guide)
        region = successor.compile_successor_region(guide, baseline_fields)

        self.assertEqual(region.consumer_id, successor.CONSUMER_ID)
        self.assertEqual(region.region_id, successor.SUCCESSOR_REGION_ID)
        self.assertEqual(region.sections_consumed, 7)
        self.assertEqual(region.section_names, (
            "lower-pelvis", "upper-pelvis", "lower-abdomen", "waist-abdomen",
            "upper-abdomen", "lower-ribcage", "upper-ribcage-shoulder",
        ))
        self.assertEqual(region.shoulder_inputs_consumed, 16)
        self.assertEqual({span.curve_name for span in region.shoulder_spans}, {"anterior-support", "posterior-return", "deltoid-sweep"})
        self.assertEqual({span.side for span in region.shoulder_spans}, {"left", "right"})
        self.assertNotIn("torso-cage", {field.recipe for field in region.bridge_fields})
        self.assertNotIn("deltoid-sweep-1", {field.recipe for field in region.bridge_fields})
        self.assertEqual(len(region.bridge_fields), len(baseline_fields) - 3)

        # Changing an actual support profile changes the successor skin field;
        # the support is not merely emitted as an x-ray guide line.
        point = np.asarray(region.shoulder_spans[0].start, dtype=np.float64).reshape(1, 3)
        before = successor._successor_region_field(point, region, 0.10)
        changed = region.shoulder_spans[0].__class__(
            region.shoulder_spans[0].side,
            region.shoulder_spans[0].curve_name,
            region.shoulder_spans[0].span_index,
            region.shoulder_spans[0].owner,
            region.shoulder_spans[0].start,
            region.shoulder_spans[0].end,
            region.shoulder_spans[0].start_radius * 1.35,
            region.shoulder_spans[0].end_radius,
        )
        changed_region = region.__class__(
            region.consumer_id, region.region_id, region.loft,
            (changed,) + region.shoulder_spans[1:], region.bridge_fields,
            region.replaced_baseline_recipes, region.source_owners,
        )
        after = successor._successor_region_field(point, changed_region, 0.10)
        self.assertFalse(np.array_equal(before, after))

    def test_baseline_recipe_signature_is_unchanged_and_successor_is_distinct(self) -> None:
        _, descriptors, _ = self.form.variants[0]
        guide = surface_preview._derive_hybrid_guides(self.form, descriptors)
        before = tuple((field.owner.key, field.recipe) for field in surface_preview._compile_hybrid_guide(guide))
        mesh = successor.build_variant(self.form, descriptors, samples=48, padding=0.5)
        after = tuple((field.owner.key, field.recipe) for field in surface_preview._compile_hybrid_guide(guide))

        self.assertEqual(before, after)
        self.assertEqual(mesh.metrics["consumer_id"], successor.CONSUMER_ID)
        self.assertEqual(mesh.metrics["successor_region"]["torso_sections_consumed"], 7)
        self.assertTrue(mesh.metrics["temporary_bridge"]["enabled"])
        self.assertGreater(mesh.metrics["temporary_bridge"]["field_count"], 0)
        self.assertNotEqual(mesh.metrics["consumer_id"], "creature-kernel.disposable-surface-preview.v2")
        self.assertEqual(len(mesh.vertices.shape), 2)
        self.assertEqual(mesh.vertices.shape[1], 3)
        self.assertEqual(mesh.faces.shape[1], 3)
        self.assertTrue(np.all(np.isfinite(mesh.vertices)))
        self.assertTrue(np.all(np.isfinite(mesh.normals)))
        self.assertTrue(mesh.metrics["watertight"])
        self.assertEqual(mesh.metrics["component_count"], 1)
        self.assertGreater(mesh.metrics["signed_volume"], 0.0)

    def test_successor_preserves_section_source_ownership_in_attribution(self) -> None:
        _, descriptors, _ = self.form.variants[0]
        guide = surface_preview._derive_hybrid_guides(self.form, descriptors)
        region = successor.compile_successor_region(guide)
        points = np.asarray([region.loft.centers[0], region.loft.centers[1], region.loft.centers[2], region.loft.centers[-1]])
        owner_roles = tuple(owner[3] for owner in successor._loft_owner_keys(points, region.loft))
        self.assertEqual(owner_roles, ("pelvis", "pelvis", "torso", "torso"))

        mesh = successor.build_variant(self.form, descriptors, samples=48, padding=0.5)
        emitted = mesh.metrics["successor_region"]["torso_section_owner_keys"]
        self.assertEqual([item["role"] for item in emitted[:2]], ["pelvis", "pelvis"])
        self.assertEqual([item["role"] for item in emitted[2:]], ["torso"] * 5)
        winner_roles = {item["role"] for item in mesh.metrics["winner_addresses"]}
        self.assertIn("pelvis", winner_roles)
        self.assertIn("torso", winner_roles)

    def test_successor_rejects_missing_renamed_duplicate_or_wrong_owner_inventory(self) -> None:
        _, descriptors, _ = self.form.variants[0]
        guide = surface_preview._derive_hybrid_guides(self.form, descriptors)
        baseline = surface_preview._compile_hybrid_guide(guide)
        torso = guide.torso_cage.torso_owner
        left, right = guide.shoulder_frame.sides
        head = guide.head_guide.head_owner

        cases = {
            "missing-torso": tuple(field for field in baseline if field.recipe != "torso-cage"),
            "duplicate-torso": baseline + (next(field for field in baseline if field.recipe == "torso-cage"),),
            "wrong-torso-owner": tuple(
                replace(field, owner=head) if field.recipe == "torso-cage" else field for field in baseline
            ),
            "renamed-deltoid": tuple(
                replace(field, recipe="deltoid-sweep-2")
                if field.recipe == "deltoid-sweep-1" and field.owner is left.owner
                else field
                for field in baseline
            ),
            "duplicate-left-deltoid": tuple(
                field for field in baseline if not (field.recipe == "deltoid-sweep-1" and field.owner is right.owner)
            ) + (next(field for field in baseline if field.recipe == "deltoid-sweep-1" and field.owner is left.owner),),
            "wrong-deltoid-owner": tuple(
                replace(field, owner=torso)
                if field.recipe == "deltoid-sweep-1" and field.owner is left.owner
                else field
                for field in baseline
            ),
        }
        for name, mutated in cases.items():
            with self.subTest(name=name), self.assertRaises(successor.SuccessorPreviewError):
                successor.compile_successor_region(guide, mutated)

    def test_all_variants_are_deterministic_and_remain_distinct(self) -> None:
        signatures = []
        for variant_id, descriptors, _ in self.form.variants:
            first = successor.build_variant(self.form, descriptors, samples=48, padding=0.5)
            second = successor.build_variant(self.form, descriptors, samples=48, padding=0.5)
            np.testing.assert_array_equal(first.vertices, second.vertices)
            np.testing.assert_array_equal(first.faces, second.faces)
            np.testing.assert_array_equal(first.normals, second.normals)
            self.assertEqual(first.metrics, second.metrics)
            self.assertEqual(first.metrics["successor_region"]["torso_section_names"][-1], "upper-ribcage-shoulder")
            signatures.append((first.vertices.shape, first.metrics["signed_volume"], tuple(first.metrics["grid"]["bounds_max"])))
        self.assertEqual(len(signatures), 4)
        self.assertGreater(len(set(signatures)), 1)

    def test_generator_emits_explicit_successor_and_bridge_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "input.json"
            source.write_bytes(surface_preview._canonical(fixture.make_varied_payload()))
            existing = root / "existing"
            existing.mkdir()
            sentinel = existing / "sentinel"
            sentinel.write_text("keep", encoding="utf-8")
            with self.assertRaisesRegex(successor.SuccessorPreviewError, "refusing to overwrite"):
                successor.generate(source, existing, samples=48, padding=0.5)
            self.assertEqual(sentinel.read_text(encoding="utf-8"), "keep")
            first = root / "first"
            second = root / "second"
            first_manifest = successor.generate(source, first, samples=48, padding=0.5)
            second_manifest = successor.generate(source, second, samples=48, padding=0.5)
            self.assertEqual(first_manifest, second_manifest)
            self.assertEqual(first_manifest["format"], successor.FORMAT)
            self.assertEqual(first_manifest["consumer_id"], successor.CONSUMER_ID)
            self.assertEqual([item["id"] for item in first_manifest["variants"]], list(surface_preview.VARIANT_IDS))
            self.assertEqual(
                sorted(path.relative_to(first).as_posix() for path in first.rglob("*") if path.is_file()),
                sorted(path.relative_to(second).as_posix() for path in second.rglob("*") if path.is_file()),
            )
            for variant in first_manifest["variants"]:
                sidecar = json.loads((first / variant["id"] / "successor.json").read_text())
                self.assertEqual(sidecar["consumer_id"], successor.CONSUMER_ID)
                self.assertEqual(sidecar["torso"]["sections_consumed"], 7)
                self.assertEqual(sidecar["shoulders"]["inputs_consumed"], 16)
                self.assertTrue(sidecar["temporary_bridge"]["enabled"])

    def test_atomic_directory_collision_preserves_stage_and_target(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            stage = root / "stage"
            target = root / "target"
            stage.mkdir()
            target.mkdir()
            (stage / "staged.txt").write_text("stage", encoding="utf-8")
            (target / "existing.txt").write_text("target", encoding="utf-8")
            with self.assertRaises(FileExistsError):
                successor._atomic_rename_noreplace(stage, target)
            self.assertEqual((stage / "staged.txt").read_text(encoding="utf-8"), "stage")
            self.assertEqual((target / "existing.txt").read_text(encoding="utf-8"), "target")


if __name__ == "__main__":
    unittest.main()
