#!/usr/bin/env python3
"""Focused checks for the disposable structural source-profile slice."""

from __future__ import annotations

import copy
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


HERE = Path(__file__).resolve()
EXPERIMENT = HERE.parents[1]
REPO_ROOT = HERE.parents[3]
sys.path.insert(0, str(EXPERIMENT))
import generate_structural_profile_sources as generator  # noqa: E402
import structural_atomic_publish  # noqa: E402


PROFILE_IDS = [
    "standard_neutral_reference",
    "compact_broad_short_limb_large_head",
    "tall_narrow_long_legged",
    "slender_long_limb",
    "stocky_broad_chested",
]


def address(role: str, anchors: list[str] | None = None, kind: str = "part") -> dict[str, object]:
    return {"namespace": "main", "anchors": anchors or [], "kind": kind, "role": role}


class StructuralProfileSourcesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        result = subprocess.run(
            ["cargo", "build", "-q", "-p", "creature-kernel-cli"],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
            timeout=180,
        )
        if result.returncode != 0:
            raise AssertionError(f"could not build the inspection CLI: {result.stderr[-2000:]}")
        cls.cli = REPO_ROOT / "target" / "debug" / "creature-kernel"
        if not cls.cli.is_file():
            raise AssertionError(f"built inspection CLI is missing: {cls.cli}")

    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="ck-structural-profile-tests-", dir="/tmp")
        self.root = Path(self.temp.name)
        self.candidate_path = EXPERIMENT / "structural_profile_candidates.json"
        self.source_path = REPO_ROOT / "examples/body-documents/stylized-digitigrade-biped-authored-form.json"
        self.candidate = json.loads(self.candidate_path.read_text(encoding="utf-8"))
        self.base = json.loads(self.source_path.read_text(encoding="utf-8"))
        self.output_dir = self.root / "sources"
        generator.write_sources(self.candidate_path, self.source_path, self.output_dir)
        self.sources = {
            path.stem: json.loads(path.read_text(encoding="utf-8"))
            for path in self.output_dir.glob("*.json")
            if path.name != "manifest.json"
        }

    def tearDown(self) -> None:
        self.temp.cleanup()

    def run_cli(self, operation: str, source_path: Path) -> dict[str, object]:
        result = subprocess.run(
            [str(self.cli), operation, "--input", str(source_path)],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
            timeout=120,
        )
        self.assertEqual(result.returncode, 0, msg=f"{operation} failed for {source_path.name}: {result.stderr}")
        try:
            payload = json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            self.fail(f"{operation} did not return JSON for {source_path.name}: {exc}")
        self.assertEqual(payload["status"], "success", msg=result.stdout[:1000])
        self.assertEqual(payload["diagnostics"], [], msg=result.stdout[:1000])
        return payload

    @staticmethod
    def part(document: dict[str, object], role: str, anchors: list[str] | None = None) -> dict[str, object]:
        wanted = address(role, anchors)
        for part in document["body"]["parts"]:  # type: ignore[index]
            if part["address"] == wanted:  # type: ignore[index]
                return part
        raise AssertionError(f"missing Part {wanted}")

    @classmethod
    def dimension(cls, document: dict[str, object], owner_role: str, dimension_role: str, anchors: list[str] | None = None) -> int:
        wanted = address(owner_role, anchors)
        for dimension in document["body"]["dimensions"]:  # type: ignore[index]
            if dimension["owner"] == wanted and dimension["role"] == dimension_role:  # type: ignore[index]
                return dimension["value"]  # type: ignore[index,return-value]
        raise AssertionError(f"missing dimension {wanted} {dimension_role}")

    def test_freezes_exactly_five_canonical_sources_with_lineage(self) -> None:
        self.assertEqual([profile["id"] for profile in self.candidate["profiles"]], PROFILE_IDS)
        self.assertEqual(self.candidate_path.read_bytes(), generator.canonical_bytes(self.candidate))
        self.assertEqual(set(self.sources), set(PROFILE_IDS))
        manifest = json.loads((self.output_dir / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(
            manifest["source"]["source_sha256"],
            hashlib.sha256(self.source_path.read_bytes()).hexdigest(),
        )
        self.assertEqual(
            manifest["source"]["candidate_sha256"],
            hashlib.sha256(self.candidate_path.read_bytes()).hexdigest(),
        )
        for profile_id, document in self.sources.items():
            self.assertEqual(len(document["body"]["parts"]), 18)  # type: ignore[index]
            self.assertEqual(len(document["body"]["dimensions"]), 153)  # type: ignore[index]
            expected_document = f"stylized_digitigrade_biped_authored_form__structural_profile__{profile_id}"
            self.assertEqual(document["source"]["document"], expected_document)  # type: ignore[index]
            self.assertTrue(all(module["declaration"]["document"] == expected_document for module in document["body"]["modules"]))  # type: ignore[index]
            serialized = (self.output_dir / f"{profile_id}.json").read_bytes()
            self.assertEqual(serialized, generator.canonical_source_bytes(document))
            self.assertLessEqual(len(serialized), generator.MAX_OUTPUT_JSON_BYTES)
            self.assertTrue(all(isinstance(item["value"], int) and item["value"] > 0 for item in document["body"]["dimensions"]))  # type: ignore[index]
        self.assertLessEqual((self.output_dir / "manifest.json").stat().st_size, generator.MAX_OUTPUT_JSON_BYTES)

    def test_actual_structure_and_provisional_form_cli_succeed_for_all_profiles(self) -> None:
        for profile_id in PROFILE_IDS:
            with self.subTest(profile=profile_id):
                source_path = self.output_dir / f"{profile_id}.json"
                structure = self.run_cli("inspect-structure", source_path)
                self.assertEqual(structure["summary"]["parts"], 18)  # type: ignore[index]
                self.assertEqual(structure["summary"]["joints"], 17)  # type: ignore[index]
                self.assertEqual(structure["summary"]["attachments"], 1)  # type: ignore[index]
                form = self.run_cli("inspect-provisional-form", source_path)
                self.assertEqual(form["reference_scale"]["axis_delta"], [0, 1, 0])  # type: ignore[index]
                self.assertEqual(form["reference_scale"]["squared_length"], 1)  # type: ignore[index]
                self.assertEqual(form["reference_scale"]["source"], "exact-containment-edge")  # type: ignore[index]

    def test_exact_containment_attachment_reference_and_preservation_invariants(self) -> None:
        base_rotations = generator._rotation_paths(self.base)
        for profile_id, document in self.sources.items():
            with self.subTest(profile=profile_id):
                world = generator._world_part_translations(document)
                for part in document["body"]["parts"]:  # type: ignore[index]
                    key = generator.address_key(part["address"])  # type: ignore[index]
                    containment = part["containment"]  # type: ignore[index]
                    if "parent" in containment:  # type: ignore[operator]
                        parent_key = generator.address_key(containment["parent"])  # type: ignore[index]
                        local = part["placement"]["translation"]  # type: ignore[index]
                        expected = tuple(world[parent_key][axis] + local[axis] for axis in range(3))
                        self.assertEqual(world[key], expected)
                sockets = {}
                for socket in document["body"]["sockets"]:  # type: ignore[index]
                    owner_world = world[generator.address_key(socket["owner"])]  # type: ignore[index]
                    translation = socket["interface_frame"]["translation"]  # type: ignore[index]
                    sockets[generator.address_key(socket["address"])] = tuple(owner_world[axis] + translation[axis] for axis in range(3))  # type: ignore[index]
                for attachment in document["body"]["attachments"]:  # type: ignore[index]
                    host = sockets[generator.address_key(attachment["host"])]  # type: ignore[index]
                    mating = sockets[generator.address_key(attachment["mating"])]  # type: ignore[index]
                    offset = attachment["offset"]["translation"]  # type: ignore[index]
                    self.assertEqual(tuple(host[axis] + offset[axis] for axis in range(3)), mating)
                head = self.part(document, "head")
                self.assertEqual(head["placement"]["translation"], [0, 1, 0])  # type: ignore[index]
                neck_world = world[generator.address_key(address("neck"))]
                for side in ("left", "right"):
                    upper_arm_world = world[generator.address_key(address("upper_arm", [side]))]
                    self.assertEqual(upper_arm_world[1], neck_world[1])
                self.assertEqual(base_rotations, generator._rotation_paths(document))
                self.assertEqual(document["body"]["landmarks"], self.base["body"]["landmarks"])  # type: ignore[index]
                self.assertEqual(document["body"]["frames"], self.base["body"]["frames"])  # type: ignore[index]
                for module in document["body"]["modules"]:  # type: ignore[index]
                    if module["module"] == "tail":
                        self.assertEqual(module["presence"], "present")

    def test_neutral_reference_retains_base_placements_and_1000_scales(self) -> None:
        neutral = self.candidate["profiles"][0]
        self.assertEqual(neutral["id"], "standard_neutral_reference")
        self.assertTrue(all(scale == 1000 for scale in neutral["dimension_scales"].values()))
        source_placements = {
            generator.address_key(part["address"]): part["placement"]["translation"]
            for part in self.base["body"]["parts"]  # type: ignore[index]
        }
        self.assertEqual(neutral["part_placements"], source_placements)

    def test_thigh_roots_are_symmetric_and_inside_scaled_lower_pelvis(self) -> None:
        for profile_id, document in self.sources.items():
            with self.subTest(profile=profile_id):
                left = self.part(document, "thigh", ["left"])["placement"]["translation"]  # type: ignore[index]
                right = self.part(document, "thigh", ["right"])["placement"]["translation"]  # type: ignore[index]
                self.assertEqual(right, [-left[0], left[1], left[2]])
                lower_pelvis_radius = self.dimension(
                    document,
                    "pelvis",
                    "form_torso_profile_lower_pelvis_lateral_radius",
                )
                self.assertLess(abs(left[0]) * 1000, lower_pelvis_radius)
                expected_thigh_y = {
                    "standard_neutral_reference": -1,
                    "compact_broad_short_limb_large_head": -1,
                    "tall_narrow_long_legged": -2,
                    "slender_long_limb": -2,
                    "stocky_broad_chested": -1,
                }[profile_id]
                self.assertEqual(left[1:], [expected_thigh_y, 0])
                expected_shin_y = -2 if profile_id in {
                    "tall_narrow_long_legged",
                    "slender_long_limb",
                } else -1
                self.assertEqual(
                    self.part(document, "shin", ["left"])["placement"]["translation"],  # type: ignore[index]
                    [0, expected_shin_y, 0],
                )
                self.assertEqual(
                    self.part(document, "foot", ["left"])["placement"]["translation"],  # type: ignore[index]
                    [0, -1, 1],
                )

    def test_shared_torso_profile_keeps_endpoints_and_moves_fullness_lower(self) -> None:
        neutral = self.sources["standard_neutral_reference"]
        positions = {
            item["role"]: item["position"]
            for item in neutral["body"]["landmarks"]  # type: ignore[index]
            if item["role"].startswith("form_torso_profile_")  # type: ignore[index]
        }
        self.assertEqual(positions["form_torso_profile_lower_pelvis"], [0, -0.45, 0])
        self.assertEqual(positions["form_torso_profile_upper_pelvis"], [0, -0.2, 0])
        self.assertEqual(positions["form_torso_profile_lower_abdomen"], [0, -0.75, 0])
        self.assertEqual(positions["form_torso_profile_waist_abdomen"], [0, -0.5, 0])
        self.assertEqual(positions["form_torso_profile_upper_abdomen"], [0, -0.2, 0])
        self.assertEqual(positions["form_torso_profile_lower_ribcage"], [0, 0.05, 0])
        self.assertEqual(
            positions["form_torso_profile_upper_ribcage_shoulder"],
            [0, 0.95, 0],
        )
        expected_radii = {
            "form_torso_profile_lower_abdomen": (1125, 680, 540),
            "form_torso_profile_waist_abdomen": (875, 500, 400),
            "form_torso_profile_upper_abdomen": (1225, 725, 560),
            "form_torso_profile_lower_ribcage": (1450, 875, 675),
            "form_torso_profile_upper_ribcage_shoulder": (1500, 900, 700),
        }
        for role, (lateral, anterior, posterior) in expected_radii.items():
            with self.subTest(role=role):
                self.assertEqual(self.dimension(neutral, "torso" if "pelvis" not in role else "pelvis", f"{role}_lateral_radius"), lateral)
                self.assertEqual(self.dimension(neutral, "torso" if "pelvis" not in role else "pelvis", f"{role}_anterior_radius"), anterior)
                self.assertEqual(self.dimension(neutral, "torso" if "pelvis" not in role else "pelvis", f"{role}_posterior_radius"), posterior)
        self.assertEqual(self.dimension(neutral, "torso", "form_extent_y"), 1200)

    def test_profile_inequalities_and_tail_style_contrast_are_real_source_differences(self) -> None:
        neutral = self.sources[PROFILE_IDS[0]]
        compact = self.sources[PROFILE_IDS[1]]
        tall = self.sources[PROFILE_IDS[2]]
        slender = self.sources[PROFILE_IDS[3]]
        stocky = self.sources[PROFILE_IDS[4]]
        expected_document = (
            "stylized_digitigrade_biped_authored_form__structural_profile__"
            "standard_neutral_reference"
        )
        expected_neutral = copy.deepcopy(self.base)
        expected_neutral["source"]["document"] = expected_document  # type: ignore[index]
        for module in expected_neutral["body"]["modules"]:  # type: ignore[index]
            module["declaration"]["document"] = expected_document  # type: ignore[index]
        self.assertEqual(
            generator.canonical_source_bytes(neutral),
            generator.canonical_source_bytes(expected_neutral),
        )
        self.assertGreater(self.dimension(compact, "head", "form_extent_x"), self.dimension(tall, "head", "form_extent_x"))
        self.assertGreater(self.dimension(compact, "head", "form_extent_x"), self.dimension(slender, "head", "form_extent_x"))
        self.assertGreater(self.dimension(compact, "head", "form_extent_x"), self.dimension(stocky, "head", "form_extent_x"))
        self.assertGreater(self.dimension(compact, "torso", "form_extent_x"), self.dimension(tall, "torso", "form_extent_x"))
        self.assertGreater(self.dimension(compact, "torso", "form_extent_x"), self.dimension(slender, "torso", "form_extent_x"))
        self.assertLess(abs(self.part(compact, "forearm", ["left"])["placement"]["translation"][0]), abs(self.part(slender, "forearm", ["left"])["placement"]["translation"][0]))  # type: ignore[index]
        self.assertLess(abs(self.part(compact, "shin", ["left"])["placement"]["translation"][1]), abs(self.part(tall, "shin", ["left"])["placement"]["translation"][1]))  # type: ignore[index]
        self.assertEqual(self.part(tall, "torso")["placement"]["translation"][1], 1)  # type: ignore[index]
        self.assertGreater(self.dimension(tall, "torso", "form_extent_y"), self.dimension(compact, "torso", "form_extent_y"))
        self.assertLess(self.dimension(tall, "torso", "form_extent_x"), self.dimension(stocky, "torso", "form_extent_x"))
        self.assertGreater(self.dimension(stocky, "torso", "form_extent_x"), self.dimension(tall, "torso", "form_extent_x"))
        self.assertGreater(self.dimension(stocky, "torso", "form_extent_x"), self.dimension(slender, "torso", "form_extent_x"))
        self.assertGreater(
            self.dimension(stocky, "torso", "form_torso_profile_upper_ribcage_shoulder_lateral_radius"),
            self.dimension(compact, "torso", "form_torso_profile_upper_ribcage_shoulder_lateral_radius"),
        )
        self.assertGreater(abs(self.part(tall, "thigh", ["left"])["placement"]["translation"][1]), abs(self.part(compact, "thigh", ["left"])["placement"]["translation"][1]))  # type: ignore[index]
        self.assertGreater(abs(self.part(slender, "forearm", ["left"])["placement"]["translation"][0]), abs(self.part(tall, "forearm", ["left"])["placement"]["translation"][0]))  # type: ignore[index]
        self.assertEqual(self.part(tall, "torso")["placement"]["translation"][1], self.part(slender, "torso")["placement"]["translation"][1])  # type: ignore[index]
        self.assertGreater(abs(self.part(slender, "shin", ["left"])["placement"]["translation"][1]), abs(self.part(stocky, "shin", ["left"])["placement"]["translation"][1]))  # type: ignore[index]
        self.assertLess(self.dimension(slender, "upper_arm", "form_radius", ["left"]), self.dimension(tall, "upper_arm", "form_radius", ["left"]))
        self.assertLess(self.dimension(slender, "thigh", "form_radius", ["left"]), self.dimension(stocky, "thigh", "form_radius", ["left"]))
        placement_signatures = {
            json.dumps([part["placement"]["translation"] for part in document["body"]["parts"]])  # type: ignore[index]
            for document in self.sources.values()
        }
        self.assertEqual(len(placement_signatures), 4)
        self.assertEqual(len({generator.canonical_source_bytes(document) for document in self.sources.values()}), 5)
        signatures = {generator._tail_signature(document) for document in self.sources.values()}
        self.assertGreaterEqual(len(signatures), 3)
        self.assertEqual(generator._tail_signature(tall)[0], 1)
        self.assertEqual(generator._tail_signature(compact)[0], 1)
        self.assertNotEqual(generator._tail_signature(compact)[3] * generator._tail_signature(tall)[4], generator._tail_signature(tall)[3] * generator._tail_signature(compact)[4])

    def test_rerun_is_byte_identical_and_invalid_targets_fail_closed(self) -> None:
        first = self.root / "first"
        second = self.root / "second"
        generator.write_sources(self.candidate_path, self.source_path, first)
        generator.write_sources(self.candidate_path, self.source_path, second)
        first_files = sorted(path.name for path in first.iterdir())
        self.assertEqual(first_files, sorted(path.name for path in second.iterdir()))
        for name in first_files:
            self.assertEqual((first / name).read_bytes(), (second / name).read_bytes(), name)

        with self.assertRaisesRegex(generator.ProfileGenerationError, "already exists"):
            generator.write_sources(self.candidate_path, self.source_path, self.output_dir)

        def rejected(candidate: dict[str, object], label: str) -> None:
            with self.subTest(rejected=label):
                with self.assertRaises(generator.ProfileGenerationError):
                    generator.generate_sources(candidate, copy.deepcopy(self.base))

        unknown_target = copy.deepcopy(self.candidate)
        unknown_target["transform"]["placement_targets"].append("main|part||unknown")  # type: ignore[index]
        rejected(unknown_target, "unknown placement target")

        missing_target = copy.deepcopy(self.candidate)
        del missing_target["profiles"][0]["part_placements"]["main|part||head"]  # type: ignore[index]
        rejected(missing_target, "missing placement target")

        unsafe_scale = copy.deepcopy(self.candidate)
        unsafe_scale["profiles"][0]["dimension_scales"]["head_extent_x"] = 0  # type: ignore[index]
        rejected(unsafe_scale, "zero scale")

        unknown_group = copy.deepcopy(self.candidate)
        unknown_group["transform"]["dimension_groups"]["head_extent_x"]["owner_patterns"][0]["role"] = "missing_part"  # type: ignore[index]
        rejected(unknown_group, "missing dimension target")

        unsafe_source = copy.deepcopy(self.base)
        unsafe_source["body"]["dimensions"][0]["value"] = float("nan")  # type: ignore[index]
        with self.assertRaises(generator.ProfileGenerationError):
            generator.generate_sources(copy.deepcopy(self.candidate), unsafe_source)

        missing_candidate_key = copy.deepcopy(self.candidate)
        del missing_candidate_key["transform"]["dimension_groups"]  # type: ignore[index]
        with self.assertRaises(generator.ProfileGenerationError):
            generator.generate_sources(missing_candidate_key, copy.deepcopy(self.base))

        missing_source_key = copy.deepcopy(self.base)
        del missing_source_key["body"]["parts"]  # type: ignore[index]
        with self.assertRaises(generator.ProfileGenerationError):
            generator.generate_sources(copy.deepcopy(self.candidate), missing_source_key)

        duplicate_transform = copy.deepcopy(self.candidate)
        duplicate_transform["profiles"][1]["part_placements"] = copy.deepcopy(duplicate_transform["profiles"][0]["part_placements"])  # type: ignore[index]
        duplicate_transform["profiles"][1]["dimension_scales"] = copy.deepcopy(duplicate_transform["profiles"][0]["dimension_scales"])  # type: ignore[index]
        with self.assertRaisesRegex(generator.ProfileGenerationError, "pairwise semantically distinct"):
            generator.generate_sources(duplicate_transform, copy.deepcopy(self.base))

        duplicate_label = copy.deepcopy(self.candidate)
        duplicate_label["profiles"][1]["label"] = duplicate_label["profiles"][0]["label"]  # type: ignore[index]
        with self.assertRaisesRegex(generator.ProfileGenerationError, "label is not unique"):
            generator.generate_sources(duplicate_label, copy.deepcopy(self.base))

        empty_label = copy.deepcopy(self.candidate)
        empty_label["profiles"][0]["label"] = ""  # type: ignore[index]
        with self.assertRaises(generator.ProfileGenerationError):
            generator.generate_sources(empty_label, copy.deepcopy(self.base))

        malformed_candidate_path = copy.deepcopy(self.candidate)
        malformed_candidate_path["transform"]["dimension_groups"] = []  # type: ignore[index]
        with self.assertRaises(generator.ProfileGenerationError):
            generator.generate_sources(malformed_candidate_path, copy.deepcopy(self.base))

        malformed_source_path = copy.deepcopy(self.base)
        malformed_source_path["body"]["parts"] = {}  # type: ignore[index]
        with self.assertRaises(generator.ProfileGenerationError):
            generator.generate_sources(copy.deepcopy(self.candidate), malformed_source_path)

        reusable_candidate = copy.deepcopy(self.candidate)
        reusable_source = copy.deepcopy(self.base)
        first_in_memory = generator.generate_sources(reusable_candidate, reusable_source)
        second_in_memory = generator.generate_sources(reusable_candidate, reusable_source)
        self.assertEqual(first_in_memory, second_in_memory)
        self.assertEqual(reusable_candidate, self.candidate)
        self.assertEqual(reusable_source, self.base)
        rejected_output = self.root / "rejected-output"
        invalid_candidate_path = self.root / "invalid-candidate.json"
        invalid_candidate = copy.deepcopy(self.candidate)
        invalid_candidate["profiles"][0]["dimension_scales"]["head_extent_x"] = 0  # type: ignore[index]
        invalid_candidate_path.write_bytes(generator.canonical_bytes(invalid_candidate))
        with self.assertRaises(generator.ProfileGenerationError):
            generator.write_sources(invalid_candidate_path, self.source_path, rejected_output)
        self.assertFalse(rejected_output.exists())

        bounded_output = self.root / "bounded-output"
        with patch.object(generator, "MAX_OUTPUT_JSON_BYTES", 1):
            with self.assertRaisesRegex(generator.ProfileGenerationError, "bounded JSON size"):
                generator.write_sources(self.candidate_path, self.source_path, bounded_output)
        self.assertFalse(bounded_output.exists())
        bounded_stages = list(self.root.glob(".bounded-output.*"))
        self.assertEqual(len(bounded_stages), 1)
        self.assertEqual(list(bounded_stages[0].iterdir()), [])

        same_identity_source = copy.deepcopy(self.base)
        same_identity_source["extensions"] = ["lineage-mismatch"]
        same_identity_path = self.root / "same-identity-different-source.json"
        same_identity_path.write_bytes(generator.canonical_source_bytes(same_identity_source))
        with self.assertRaisesRegex(generator.ProfileGenerationError, "source bytes"):
            generator.write_sources(
                self.candidate_path,
                same_identity_path,
                self.root / "same-identity-output",
            )

        traversal_candidate = copy.deepcopy(self.candidate)
        traversal_candidate["base_source"]["path"] = "../outside.json"  # type: ignore[index]
        traversal_path = self.root / "traversal-candidate.json"
        traversal_path.write_bytes(generator.canonical_bytes(traversal_candidate))
        with self.assertRaises(generator.ProfileGenerationError):
            generator._default_source(traversal_path)

        output_target = self.root / "real-output-parent"
        output_target.mkdir()
        output_link = self.root / "output-parent-link"
        output_link.symlink_to(output_target, target_is_directory=True)
        with self.assertRaisesRegex(generator.ProfileGenerationError, "symlinked path component"):
            generator.write_sources(self.candidate_path, self.source_path, output_link / "sources")
        self.assertFalse((output_target / "sources").exists())

        missing_parent = self.root / "missing-output-parent" / "sources"
        with self.assertRaisesRegex(generator.ProfileGenerationError, "output parent must already exist"):
            generator.write_sources(self.candidate_path, self.source_path, missing_parent)
        self.assertFalse(missing_parent.parent.exists())

        source_target = self.root / "real-source-parent"
        source_target.mkdir()
        source_link = self.root / "source-parent-link"
        source_link.symlink_to(self.source_path.parent, target_is_directory=True)
        with self.assertRaisesRegex(generator.ProfileGenerationError, "symlinked path component"):
            generator.write_sources(self.candidate_path, source_link / self.source_path.name, self.root / "source-link-output")

        source_file_link = self.root / "source-file-link.json"
        source_file_link.symlink_to(self.source_path)
        with self.assertRaisesRegex(generator.ProfileGenerationError, "symlinked path component"):
            generator.write_sources(self.candidate_path, source_file_link, self.root / "source-file-link-output")

        candidate_file_link = self.root / "candidate-file-link.json"
        candidate_file_link.symlink_to(self.candidate_path)
        with self.assertRaisesRegex(generator.ProfileGenerationError, "symlinked path component"):
            generator.write_sources(candidate_file_link, self.source_path, self.root / "candidate-file-link-output")

        symlink_with_parent_traversal = self.root / "symlink-with-parent-traversal"
        symlink_with_parent_traversal.symlink_to(self.source_path.parent, target_is_directory=True)
        with self.assertRaisesRegex(generator.ProfileGenerationError, "symlinked path component"):
            generator.write_sources(
                self.candidate_path,
                symlink_with_parent_traversal / ".." / symlink_with_parent_traversal.name / self.source_path.name,
                self.root / "symlink-traversal-output",
            )

        default_link = self.root / "default-source-link"
        default_link.symlink_to(self.source_path.parent, target_is_directory=True)
        default_candidate = copy.deepcopy(self.candidate)
        default_candidate["base_source"]["path"] = "default-source-link/" + self.source_path.name  # type: ignore[index]
        default_candidate_path = self.root / "default-candidate.json"
        default_candidate_path.write_bytes(generator.canonical_bytes(default_candidate))
        with patch.object(generator, "REPO_ROOT", self.root):
            with self.assertRaisesRegex(generator.ProfileGenerationError, "symlinked path component"):
                generator._default_source(default_candidate_path)

        write_failure_output = self.root / "write-failure"
        with patch.object(Path, "write_bytes", side_effect=generator.ProfileGenerationError("synthetic write failure")):
            with self.assertRaisesRegex(generator.ProfileGenerationError, "synthetic write failure"):
                generator.write_sources(self.candidate_path, self.source_path, write_failure_output)
        self.assertFalse(write_failure_output.exists())
        write_failure_stages = list(self.root.glob(".write-failure.*"))
        self.assertEqual(len(write_failure_stages), 1)
        self.assertEqual(list(write_failure_stages[0].iterdir()), [])

        publication_output = self.root / "publication-failure"
        with patch.object(
            generator,
            "_atomic_publish_no_replace",
            side_effect=generator.ProfileGenerationError("synthetic atomic failure"),
        ):
            with self.assertRaises(generator.ProfileGenerationError):
                generator.write_sources(
                    self.candidate_path,
                    self.source_path,
                    publication_output,
                )
        self.assertFalse(publication_output.exists())
        publication_stages = list(self.root.glob(".publication-failure.*"))
        self.assertEqual(len(publication_stages), 1)
        self.assertEqual(list(publication_stages[0].iterdir()), [])

    def test_cleanup_stage_stays_on_opened_parent_after_ancestor_swap(self) -> None:
        parent = self.root / "publication-parent"
        parent.mkdir()
        parent_fd = structural_atomic_publish.open_directory_no_symlinks(parent)
        stage_name = None
        try:
            stage_name, stage = structural_atomic_publish.create_stage(parent_fd, "sources")
            (stage / "payload.json").write_bytes(b"owned")
            moved_parent = self.root / "opened-parent"
            parent.rename(moved_parent)
            parent.mkdir()
            attacker_marker = parent / "attacker-marker"
            attacker_marker.write_bytes(b"must remain")
            self.assertTrue(structural_atomic_publish.cleanup_stage(parent_fd, stage_name))
            self.assertTrue((moved_parent / stage_name).is_dir())
            self.assertEqual(list((moved_parent / stage_name).iterdir()), [])
            self.assertEqual(attacker_marker.read_bytes(), b"must remain")
        finally:
            os.close(parent_fd)

    def test_documented_check_mode_runs_without_retaining_output(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                str(EXPERIMENT / "generate_structural_profile_sources.py"),
                "--candidate",
                str(self.candidate_path),
                "--source",
                str(self.source_path),
                "--check",
            ],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("generated 5 structural profile sources", result.stdout)

    def test_regular_parent_replacement_before_open_is_rejected(self) -> None:
        parent = self.root / "validated-source-parent"
        parent.mkdir()
        output = parent / "sources"
        moved_parent = self.root / "validated-source-parent-original"
        original_open = structural_atomic_publish.open_directory_no_symlinks

        def replace_then_open(path: Path, expected_identity=None):
            parent.rename(moved_parent)
            parent.mkdir()
            return original_open(path, expected_identity)

        with patch.object(
            structural_atomic_publish,
            "open_directory_no_symlinks",
            side_effect=replace_then_open,
        ):
            with self.assertRaisesRegex(generator.ProfileGenerationError, "changed after validation"):
                generator.write_sources(self.candidate_path, self.source_path, output)
        self.assertFalse((parent / "sources").exists())
        self.assertFalse((moved_parent / "sources").exists())

    def test_replaced_stage_identity_is_never_published(self) -> None:
        parent = self.root / "stage-replacement-parent"
        parent.mkdir()
        parent_fd = structural_atomic_publish.open_directory_no_symlinks(parent)
        stage_name = None
        try:
            stage_name, stage = structural_atomic_publish.create_stage(parent_fd, "sources")
            (stage / "owned.txt").write_text("owned", encoding="utf-8")
            original_stage = parent / "original-stage"
            (parent / stage_name).rename(original_stage)
            (parent / stage_name).mkdir()
            (parent / stage_name / "attacker.txt").write_text("attacker", encoding="utf-8")
            (stage / "after-replacement.txt").write_text("owned through fd", encoding="utf-8")
            self.assertEqual((original_stage / "after-replacement.txt").read_text(encoding="utf-8"), "owned through fd")
            self.assertFalse((parent / stage_name / "after-replacement.txt").exists())
            with self.assertRaisesRegex(
                structural_atomic_publish.AtomicPublishError,
                "staging directory changed",
            ):
                structural_atomic_publish.publish_no_replace(parent_fd, stage_name, "sources")
            self.assertFalse((parent / "sources").exists())
            self.assertEqual((parent / stage_name / "attacker.txt").read_text(encoding="utf-8"), "attacker")
            self.assertTrue(structural_atomic_publish.cleanup_stage(parent_fd, stage_name))
            self.assertEqual(list(original_stage.iterdir()), [])
            self.assertEqual((parent / stage_name / "attacker.txt").read_text(encoding="utf-8"), "attacker")
        finally:
            structural_atomic_publish.close_stage(stage_name)
            os.close(parent_fd)

    def test_cleanup_stage_preserves_replacement_before_top_level_cleanup(self) -> None:
        parent = self.root / "cleanup-replacement-parent"
        parent.mkdir()
        parent_fd = structural_atomic_publish.open_directory_no_symlinks(parent)
        stage_name = None
        try:
            stage_name, stage = structural_atomic_publish.create_stage(parent_fd, "sources")
            (stage / "owned.txt").write_bytes(b"owned")
            original_stage = parent / "original-stage"
            attacker_stage = parent / str(stage_name)
            original_remove = structural_atomic_publish._remove_tree_contents

            def clean_then_replace(directory_fd: int) -> bool:
                result = original_remove(directory_fd)
                attacker_stage.rename(original_stage)
                attacker_stage.mkdir()
                (attacker_stage / "attacker.txt").write_bytes(b"attacker")
                return result

            with patch.object(structural_atomic_publish, "_remove_tree_contents", side_effect=clean_then_replace):
                self.assertTrue(structural_atomic_publish.cleanup_stage(parent_fd, stage_name))
            self.assertEqual((attacker_stage / "attacker.txt").read_bytes(), b"attacker")
            self.assertTrue(original_stage.is_dir())
            self.assertEqual(list(original_stage.iterdir()), [])
        finally:
            structural_atomic_publish.close_stage(stage_name)
            os.close(parent_fd)

    def test_publication_stays_on_opened_parent_after_ancestor_swap(self) -> None:
        parent = self.root / "source-parent"
        parent.mkdir()
        output = parent / "sources"
        moved_parent = self.root / "opened-source-parent"

        def swap_then_publish(parent_fd: int, stage_name: str, destination_name: str) -> None:
            parent.rename(moved_parent)
            parent.mkdir()
            structural_atomic_publish.publish_no_replace(parent_fd, stage_name, destination_name)

        with patch.object(generator, "_atomic_publish_no_replace", side_effect=swap_then_publish):
            generator.write_sources(self.candidate_path, self.source_path, output)
        self.assertTrue((moved_parent / "sources" / "manifest.json").is_file())
        self.assertFalse((parent / "sources").exists())


if __name__ == "__main__":
    unittest.main()
