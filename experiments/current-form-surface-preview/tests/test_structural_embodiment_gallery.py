#!/usr/bin/env python3
"""Focused fail-closed coverage for the shared-pose structural gallery."""

from __future__ import annotations

import hashlib
import io
import json
import math
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

from PIL import Image, ImageDraw


HERE = Path(__file__).resolve()
EXPERIMENT = HERE.parents[1]
sys.path.insert(0, str(EXPERIMENT))
import structural_embodiment_bridge as bridge  # noqa: E402
import structural_embodiment_gallery as gallery  # noqa: E402


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def address(kind: str, role: str, anchors: list[str] | None = None) -> dict[str, object]:
    return {"namespace": "main", "anchors": anchors or [], "kind": kind, "role": role}


def frame(translation: list[float] | None = None) -> dict[str, object]:
    return {"translation": translation or [0, 0, 0], "rotation_xyzw": [0, 0, 0, 1]}


SELECTORS = [
    ("spine", []),
    ("neck_base", []),
    ("head_base", []),
    ("shoulder", ["left"]),
    ("elbow", ["left"]),
    ("wrist", ["left"]),
    ("shoulder", ["right"]),
    ("elbow", ["right"]),
    ("wrist", ["right"]),
    ("hip", ["left"]),
    ("knee", ["left"]),
    ("ankle", ["left"]),
    ("hip", ["right"]),
    ("knee", ["right"]),
    ("ankle", ["right"]),
    ("base", ["tail"]),
    ("segment", ["tail"]),
]
PART_ROLES = [
    ("pelvis", []), ("torso", []), ("neck", []), ("head", []),
    ("upper_arm", ["left"]), ("forearm", ["left"]), ("hand", ["left"]),
    ("upper_arm", ["right"]), ("forearm", ["right"]), ("hand", ["right"]),
    ("thigh", ["left"]), ("shin", ["left"]), ("foot", ["left"]),
    ("thigh", ["right"]), ("shin", ["right"]), ("foot", ["right"]),
    ("tail_root", ["tail"]), ("tail_tip", ["tail"]),
]


def source_document(profile_id: str) -> str:
    return f"stylized_digitigrade_biped_authored_form__structural_profile__{profile_id}"


def make_structure(profile_id: str, *, nonidentity: bool = False) -> dict[str, object]:
    parts: list[dict[str, object]] = []
    part_addresses: list[dict[str, object]] = []
    for index, (role, anchors) in enumerate(PART_ROLES):
        part = address("part", role, anchors)
        part_addresses.append(part)
        parts.append({
            "address": part,
            "containment": {"root": True} if index == 0 else {"parent": part_addresses[index - 1]},
            "placement": {"translation": [0, 0 if index == 0 else 1, 0], "rotation_xyzw": [0, 0, 0, 1]},
        })
    joints: list[dict[str, object]] = []
    for index, (role, anchors) in enumerate(SELECTORS):
        joints.append({
            "address": address("joint", role, anchors),
            "proximal": part_addresses[index],
            "distal": part_addresses[index + 1],
            "proximal_frame": frame([0.125, 0, 0] if nonidentity and index == 0 else None),
            "distal_frame": frame(),
        })
    graph = {
        "projection": "source-preserving-provisional-structural-debug",
        "contract": {"family": "creature-kernel.body", "revision": 1},
        "source": {"document": source_document(profile_id), "namespace": "main", "dependencies": []},
        "basis": {"length_unit": "metre", "handedness": "right", "up": "+y", "forward": "+z"},
        "profiles": {"semantic_numeric": "ck.numeric-frame.r1"},
        "extensions": [],
        "modules": [],
        "parts": parts,
        "joints": joints,
        "sockets": [],
        "attachments": [],
        "landmarks": [],
        "dimensions": [],
        "frames": [],
        "regions": [],
        "capabilities": [],
        "fields": [],
    }
    return {
        "format": bridge.STRUCTURE_FORMAT,
        "operation": "inspect-structure",
        "stage": "structural-validation",
        "status": "success",
        "processing_complete": True,
        "diagnostics_complete": True,
        "diagnostics": [],
        "summary": {"parts": len(parts), "joints": len(joints)},
        "graph": graph,
    }


def cylinder_ply(scale: float = 1.0) -> bytes:
    rows: list[tuple[float, float, float, float, float, float]] = []
    sides = 6
    for y in (0.0, 1.0, 2.0):
        for index in range(sides):
            angle = math.tau * index / sides
            x, z = scale * math.cos(angle), scale * math.sin(angle)
            rows.append((x, y * scale, z, math.cos(angle), 0.0, math.sin(angle)))
    top_center = len(rows)
    rows.append((0.0, 2.0 * scale, 0.0, 0.0, 1.0, 0.0))
    bottom_center = len(rows)
    rows.append((0.0, 0.0, 0.0, 0.0, -1.0, 0.0))
    faces: list[tuple[int, int, int]] = []
    for band in range(2):
        lower = band * sides
        upper = (band + 1) * sides
        for index in range(sides):
            following = (index + 1) % sides
            faces.append((lower + index, upper + following, lower + following))
            faces.append((lower + index, upper + index, upper + following))
    for index in range(sides):
        following = (index + 1) % sides
        faces.append((bottom_center, index, following))
        faces.append((top_center, 2 * sides + following, 2 * sides + index))
    lines = [
        "ply", "format ascii 1.0", f"element vertex {len(rows)}",
        "property float x", "property float y", "property float z",
        "property float nx", "property float ny", "property float nz",
        f"element face {len(faces)}", "property list uchar int vertex_indices", "end_header",
    ]
    lines.extend(" ".join(f"{value:.12f}" for value in row) for row in rows)
    lines.extend(f"3 {a} {b} {c}" for a, b, c in faces)
    return ("\n".join(lines) + "\n").encode("ascii")


def make_candidate(profile_id: str, vertices: list[tuple[float, float, float]] | None = None) -> dict[str, object]:
    root_part = address("part", "pelvis")
    root_endpoint = (0.0, 0.0, 0.0)
    root_start = (0.0, 1.0, 0.0)
    if vertices is not None:
        root_start = tuple(
            math.fsum(vertex[axis] for vertex in vertices) / len(vertices)
            for axis in range(3)
        )
        if math.dist(root_start, root_endpoint) <= bridge.MIN_SEGMENT_LENGTH:
            root_start = sorted(
                vertices,
                key=lambda vertex: (
                    -sum((vertex[axis] - root_endpoint[axis]) ** 2 for axis in range(3)),
                    vertex,
                ),
            )[0]
    root_bone = {
        "id": "bone-source-part-root", "kind": "synthetic-source-part-root", "parent": None,
        "source_part": root_part, "a": list(root_start), "b": list(root_endpoint),
        "length": math.dist(root_start, root_endpoint), "owned_part": root_part, "source_parts": [root_part],
        "surface_anchor_rule": "centroid of the complete neutral surface, with lexicographically stable farthest-vertex fallback",
    }
    bones = [root_bone]
    mapping = []
    previous = root_bone["id"]
    part_addresses = [address("part", role, anchors) for role, anchors in PART_ROLES]
    for index, (role, anchors) in enumerate(SELECTORS):
        bone_id = f"bone-{index:02d}"
        joint = address("joint", role, anchors)
        bones.append({
            "id": bone_id, "kind": "derived-joint", "parent": previous, "joint": joint,
            "proximal": part_addresses[index], "distal": part_addresses[index + 1],
            "a": [0, index, 0], "b": [0, index + 1, 0], "length": 1.0,
            "owned_part": part_addresses[index + 1],
            "source_parts": [part_addresses[index], part_addresses[index + 1]],
        })
        mapping.append({"joint": joint, "bone_id": bone_id})
        previous = bone_id
    bone_ids = [bone["id"] for bone in bones]
    influences = []
    for index in range(20):
        bone_id = bone_ids[index] if index < len(bone_ids) else bone_ids[index - len(bone_ids)]
        influences.append([{"bone_id": bone_id, "weight": 1.0}])
    primary_counts = {bone_id: 0 for bone_id in bone_ids}
    for row in influences:
        primary_counts[row[0]["bone_id"]] += 1
    proxies = []
    for bone in bones:
        indices = [index for index, row in enumerate(influences) if row[0]["bone_id"] == bone["id"]]
        radius = 0.25
        if vertices is not None:
            radius = max(
                bridge._distance_to_segment(vertices[index], tuple(bone["a"]), tuple(bone["b"]))
                for index in indices
            )
        proxies.append({
            "bone_id": bone["id"],
            "kind": "capsule",
            "a": bone["a"],
            "b": bone["b"],
            "radius": radius,
            "owned_part": bone["owned_part"],
            "partition_vertex_count": primary_counts[bone["id"]],
            "partition_rule": "nearest eligible weighted bone, then ascending derived bone id",
            "radius_rule": "maximum point-to-segment distance over the bone's complete primary-influence partition",
        })
    return {
        "format": bridge.BRIDGE_FORMAT,
        "status": "success",
        "boundary": "candidate-scoped disposable structural evidence",
        "identity": {"basis": {}, "candidate_sha256": "a" * 64, "request_sha256": "b" * 64},
        "source": {
            "document": source_document(profile_id), "namespace": "main", "format": bridge.SOURCE_FORMAT,
            "candidate_profile_id": profile_id, "surface_variant_id": gallery.NEUTRAL_VARIANT_ID,
        },
        "hierarchy": {"bone_count": 18, "synthetic_root_bone_id": root_bone["id"], "bones": bones, "joint_address_to_bone": mapping},
        "weights": {"vertex_count": 20, "max_influences": 4, "influences": influences},
        "proxies": proxies,
        "checks": {
            "rooted_acyclic_hierarchy": True,
            "spatially_continuous_hierarchy": True,
            "complete_joint_to_bone_mapping": True,
            "finite_nonnegative_normalized_weights": True,
            "full_vertex_coverage": True,
            "max_four_influences": True,
            "every_bone_has_positive_influence": True,
            "complete_proxy_vertex_partition": True,
            "finite_non_degenerate_capsules": True,
        },
    }


def write_bridge_fixture(root: Path, profile_id: str, structure_path: Path, ply_path: Path) -> Path:
    bridge_dir = root / "bridges" / profile_id
    bridge_dir.mkdir(parents=True)
    ply_sha256 = hashlib.sha256(ply_path.read_bytes()).hexdigest()
    neutral = bridge._parse_ply(ply_path, expected_sha256=ply_sha256)
    candidate = make_candidate(profile_id, neutral["vertices"])
    input_files = [
        {"kind": "inspect-structure", "path": "inspect-structure.json", "sha256": hashlib.sha256(structure_path.read_bytes()).hexdigest(), "bytes": structure_path.stat().st_size},
        {"kind": "successor-ply", "path": "neutral-v0/surface.ply", "sha256": ply_sha256, "bytes": ply_path.stat().st_size},
        {"kind": "successor-ply", "path": "broad-soft-v0/surface.ply", "sha256": "c" * 64, "bytes": 1},
    ]
    identity_basis = {
        "algorithm_revision": bridge.ALGORITHM_REVISION,
        "configuration_revision": bridge.CONFIGURATION_REVISION,
        "candidate_profile_id": profile_id,
        "surface_variant_id": gallery.NEUTRAL_VARIANT_ID,
        "provenance_semantics": "exact bounded input bytes; logically equivalent re-encodings intentionally have distinct identity",
        "input_files": input_files,
    }
    candidate["identity"] = {
        "basis": identity_basis,
        "candidate_sha256": bridge._digest(bridge.IDENTITY_DOMAIN + ":candidate", identity_basis),
        "request_sha256": bridge._digest(bridge.IDENTITY_DOMAIN + ":request", identity_basis),
    }
    candidate_bytes = canonical(candidate) + b"\n"
    bridge_path = bridge_dir / bridge.BRIDGE_FILE
    bridge_path.write_bytes(candidate_bytes)
    manifest = {
        "format": bridge.MANIFEST_FORMAT,
        "status": "success",
        "bridge_format": bridge.BRIDGE_FORMAT,
        "algorithm_revision": bridge.ALGORITHM_REVISION,
        "configuration_revision": bridge.CONFIGURATION_REVISION,
        "candidate_profile_id": profile_id,
        "surface_variant_id": gallery.NEUTRAL_VARIANT_ID,
        "candidate_sha256": candidate["identity"]["candidate_sha256"],
        "request_sha256": candidate["identity"]["request_sha256"],
        "input_files": input_files,
        "inventory": [{"kind": "bridge-json", "path": bridge.BRIDGE_FILE, "sha256": hashlib.sha256(candidate_bytes).hexdigest(), "bytes": len(candidate_bytes)}],
    }
    (bridge_dir / bridge.MANIFEST_FILE).write_bytes(canonical(manifest) + b"\n")
    return bridge_dir


def rewrite_bridge_candidate(bridge_dir: Path, candidate: dict[str, object]) -> None:
    candidate_bytes = canonical(candidate) + b"\n"
    (bridge_dir / bridge.BRIDGE_FILE).write_bytes(candidate_bytes)
    manifest_path = bridge_dir / bridge.MANIFEST_FILE
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["inventory"][0]["sha256"] = hashlib.sha256(candidate_bytes).hexdigest()
    manifest["inventory"][0]["bytes"] = len(candidate_bytes)
    (manifest_path).write_bytes(canonical(manifest) + b"\n")


class StructuralEmbodimentGalleryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.structures: dict[str, Path] = {}
        self.plys: dict[str, Path] = {}
        self.inputs: dict[str, gallery.ProfileInput] = {}
        candidate_path = EXPERIMENT / gallery.CANDIDATE_FILE
        candidate_data = candidate_path.read_bytes()
        candidate = json.loads(candidate_data)
        base_source = candidate["base_source"]
        source_root = self.root / gallery.SOURCES_DIR
        source_root.mkdir()
        source_records = []
        self.expected_source_data: dict[str, bytes] = {}
        for index, profile_id in enumerate(gallery.FROZEN_PROFILE_IDS):
            structure = make_structure(profile_id)
            structure_path = self.root / f"{profile_id}.json"
            structure_path.write_bytes(canonical(structure))
            source_document_value = {
                "source": {
                    "document": source_document(profile_id),
                    "namespace": base_source["namespace"],
                },
                "body": {
                    key: structure["graph"][key]
                    for key in (
                        "modules", "parts", "joints", "sockets", "attachments",
                        "landmarks", "dimensions", "frames", "regions",
                        "capabilities", "fields",
                    )
                },
            }
            source_data = canonical(source_document_value) + b"\n"
            self.expected_source_data[profile_id] = source_data
            source_path = source_root / f"{profile_id}.json"
            source_path.write_bytes(source_data)
            source_records.append({
                "bytes": len(source_data),
                "document": source_document(profile_id),
                "file": source_path.name,
                "id": profile_id,
                "sha256": hashlib.sha256(source_data).hexdigest(),
                "tail_signature": [],
            })
            ply_path = self.root / f"{profile_id}.ply"
            ply_path.write_bytes(cylinder_ply(1.0 + index * 0.25))
            bridge_dir = write_bridge_fixture(self.root, profile_id, structure_path, ply_path)
            self.structures[profile_id] = structure_path
            self.plys[profile_id] = ply_path
            self.inputs[profile_id] = gallery.ProfileInput(bridge_dir, ply_path, structure_path)
        source_manifest = {
            "candidate_format": candidate["format"],
            "format": gallery.SOURCE_MANIFEST_FORMAT,
            "profiles": source_records,
            "source": {
                "base_document": base_source["document"],
                "base_namespace": base_source["namespace"],
                "candidate_sha256": hashlib.sha256(candidate_data).hexdigest(),
                "source_sha256": base_source["sha256"],
            },
        }
        self.source_manifest = source_root / gallery.SOURCE_MANIFEST_FILE
        self.source_manifest.write_bytes(canonical(source_manifest) + b"\n")
        self.expected_source_patch = patch.object(
            gallery,
            "_expected_source_documents",
            return_value=dict(self.expected_source_data),
        )
        self.expected_source_patch.start()
        self.addCleanup(self.expected_source_patch.stop)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def build(self, name: str, *, candidate_path: Path | None = None) -> Path:
        output = self.root / name
        gallery.build(
            self.inputs,
            output,
            source_manifest_path=self.source_manifest,
            candidate_path=candidate_path,
        )
        return output

    def test_success_inventory_global_bound_png_and_transformed_evidence(self) -> None:
        output = self.build("gallery")
        manifest = json.loads((output / gallery.MANIFEST_FILE).read_text(encoding="utf-8"))
        self.assertEqual(manifest["profile_ids"], list(gallery.FROZEN_PROFILE_IDS))
        self.assertEqual(len(manifest["profiles"]), 4)
        self.assertEqual(len(manifest["artifacts"]), 39)
        self.assertEqual({item["path"] for item in manifest["artifacts"]}, {
            f"{profile_id}/{name}"
            for profile_id in gallery.FROZEN_PROFILE_IDS
            for name in (gallery.NEUTRAL_FILE, gallery.POSED_FILE, gallery.SKELETON_FILE, gallery.WEIGHTS_FILE, gallery.NEUTRAL_PROXIES_FILE, gallery.POSED_PROXIES_FILE, gallery.METRICS_FILE, gallery.GALLERY_FILE)
        } | {
            gallery.CANDIDATE_FILE,
            gallery.POSE_FILE,
            f"{gallery.SOURCES_DIR}/{gallery.SOURCE_MANIFEST_FILE}",
            *(f"{gallery.SOURCES_DIR}/{profile_id}.json" for profile_id in gallery.FROZEN_PROFILE_IDS),
        })
        root_inventory = {item["path"]: item for item in manifest["artifacts"]}
        self.assertEqual(
            (output / gallery.CANDIDATE_FILE).read_bytes(),
            (EXPERIMENT / gallery.CANDIDATE_FILE).read_bytes(),
        )
        self.assertEqual(
            (output / gallery.SOURCES_DIR / gallery.SOURCE_MANIFEST_FILE).read_bytes(),
            self.source_manifest.read_bytes(),
        )
        self.assertEqual(
            manifest["source_manifest"]["sha256"],
            root_inventory[f"{gallery.SOURCES_DIR}/{gallery.SOURCE_MANIFEST_FILE}"]["sha256"],
        )
        profile_pngs = []
        for profile in manifest["profiles"]:
            profile_id = profile["id"]
            image_path = f"{profile_id}/{gallery.GALLERY_FILE}"
            profile_pngs.append(root_inventory[image_path])
            self.assertEqual(profile["gallery"]["path"], image_path)
            generated_source_path = f"{gallery.SOURCES_DIR}/{profile_id}.json"
            self.assertEqual(profile["generated_source_path"], generated_source_path)
            self.assertEqual(profile["generated_source_sha256"], root_inventory[generated_source_path]["sha256"])
            self.assertEqual(profile["generated_source_bytes"], root_inventory[generated_source_path]["bytes"])
            self.assertEqual(
                gallery._gallery_row_header({"id": profile_id, "label": profile["label"]}, 0, "NEUTRAL SKIN + SKELETON"),
                f"PROFILE: {profile_id} | {profile['label']} | NEUTRAL SKIN + SKELETON",
            )
            self.assertEqual(profile["gallery"]["global_world_bound"], manifest["global_world_bound"])
            self.assertEqual(profile["metrics"]["gallery_global_world_bound"], manifest["global_world_bound"])
            profile_inventory = {item["path"]: item for item in profile["artifacts"]}
            self.assertEqual(profile_inventory[image_path], root_inventory[image_path])
            image = Image.open(output / image_path)
            self.assertEqual((image.width, image.height, image.mode), (1800, 2500, "RGB"))
            image.close()
        self.assertEqual(len(profile_pngs), 4)
        self.assertEqual(len({item["path"] for item in profile_pngs}), 4)
        self.assertEqual(len({item["sha256"] for item in profile_pngs}), 4)
        self.assertFalse((output / gallery.GALLERY_FILE).exists())
        first = gallery.FROZEN_PROFILE_IDS[0]
        profile = next(item for item in manifest["profiles"] if item["id"] == first)
        self.assertEqual((output / first / gallery.NEUTRAL_FILE).read_bytes(), self.plys[first].read_bytes())
        posed = bridge._parse_ply(output / first / gallery.POSED_FILE, expected_sha256=next(item["sha256"] for item in profile["artifacts"] if item["path"].endswith("/" + gallery.POSED_FILE)))
        neutral = bridge._parse_ply(self.plys[first], expected_sha256=hashlib.sha256(self.plys[first].read_bytes()).hexdigest())
        self.assertTrue(any(left != right for left, right in zip(neutral["normals"], posed["normals"])))
        self.assertTrue(all(abs(sum(component * component for component in normal) - 1.0) < 1.0e-9 for normal in posed["normals"]))
        neutral_proxies = json.loads((output / first / gallery.NEUTRAL_PROXIES_FILE).read_text(encoding="utf-8"))["proxies"]
        posed_proxies = json.loads((output / first / gallery.POSED_PROXIES_FILE).read_text(encoding="utf-8"))["proxies"]
        self.assertTrue(any(item["a"] != other["a"] or item["b"] != other["b"] for item, other in zip(neutral_proxies, posed_proxies)))
        lineage_fields = {"owned_part", "partition_rule", "partition_vertex_count", "radius_rule"}
        for neutral_proxy, posed_proxy in zip(neutral_proxies, posed_proxies):
            self.assertTrue(lineage_fields.issubset(neutral_proxy))
            self.assertEqual({key: neutral_proxy[key] for key in lineage_fields}, {key: posed_proxy[key] for key in lineage_fields})
            self.assertEqual(neutral_proxy["radius"], posed_proxy["radius"])
        self.assertEqual(manifest["canvas"]["columns"], ["front", "side", "three-quarter"])
        self.assertEqual(len(manifest["canvas"]["rows"]), 5)
        self.assertEqual(gallery.VIEW_HEADERS["side"], "side (exact orthographic)")
        self.assertIn(
            "X-RAY OVERLAY",
            gallery._gallery_row_header(
                {"id": "ignored", "label": "ignored"},
                1,
                "POSED SKIN + SKELETON (X-RAY OVERLAY)",
            ),
        )

    def test_separate_outputs_are_byte_identical_and_existing_output_is_not_replaced(self) -> None:
        first = self.build("first")
        second = self.build("second")
        first_files = sorted(path.relative_to(first) for path in first.rglob("*") if path.is_file())
        second_files = sorted(path.relative_to(second) for path in second.rglob("*") if path.is_file())
        self.assertEqual(first_files, second_files)
        for relative in first_files:
            self.assertEqual((first / relative).read_bytes(), (second / relative).read_bytes(), str(relative))
        with self.assertRaisesRegex(gallery.GalleryError, "refusing to overwrite"):
            gallery.build(self.inputs, first, source_manifest_path=self.source_manifest)

    def test_each_bridge_requires_its_own_structure_hash(self) -> None:
        swapped = dict(self.inputs)
        profile_id = gallery.FROZEN_PROFILE_IDS[1]
        swapped[profile_id] = gallery.ProfileInput(swapped[profile_id].bridge_dir, swapped[profile_id].neutral_ply, self.structures[gallery.FROZEN_PROFILE_IDS[0]])
        with self.assertRaisesRegex(gallery.GalleryError, "does not match bridge inventory"):
            gallery.build(swapped, self.root / "cross-profile-structure", source_manifest_path=self.source_manifest)

    def test_depth_order_is_back_to_front_with_stable_face_index_ties(self) -> None:
        vertices = [
            (1.0, 0.0, 1.0), (2.0, 1.0, 1.0), (3.0, 0.0, 1.0),
            (-2.0, 0.0, -1.0), (-1.0, 1.0, -1.0), (0.0, 0.0, -1.0),
            (1.0, 0.0, 1.0), (2.0, 1.0, 1.0), (3.0, 0.0, 1.0),
        ]
        faces = [(0, 1, 2), (3, 4, 5), (6, 7, 8)]
        for view in ("front", "side", "three-quarter"):
            with self.subTest(view=view):
                self.assertEqual(gallery._ordered_face_indices(vertices, faces, view), [1, 0, 2])

    def test_projection_uses_one_scale_across_views_axes_and_proxy_radius(self) -> None:
        lower = (-2.0, -3.0, -4.0)
        upper = (6.0, 7.0, 8.0)
        box = (10, 20, 600, 500)
        pixels_per_unit = gallery._pixels_per_world_unit(lower, upper, box)
        self.assertAlmostEqual(pixels_per_unit, 600.0 * gallery.THREE_QUARTER_BASIS_NORM / 15.8)

        center = (2.0, 2.0, 2.0)
        for view in ("front", "side", "three-quarter"):
            with self.subTest(view=view):
                self.assertEqual(gallery._project(center, view, lower, upper, box), (310.0, 270.0))
        self.assertEqual(
            gallery._project((3.0, 2.0, 2.0), "side", lower, upper, box),
            gallery._project(center, "side", lower, upper, box),
        )
        self.assertAlmostEqual(
            gallery._project((3.0, 2.0, 2.0), "front", lower, upper, box)[0]
            - gallery._project(center, "front", lower, upper, box)[0],
            pixels_per_unit,
        )
        self.assertAlmostEqual(
            gallery._project((2.0, 3.0, 2.0), "front", lower, upper, box)[1]
            - gallery._project(center, "front", lower, upper, box)[1],
            -pixels_per_unit,
        )
        self.assertAlmostEqual(
            gallery._project((2.0, 2.0, 3.0), "side", lower, upper, box)[0]
            - gallery._project(center, "side", lower, upper, box)[0],
            pixels_per_unit,
        )
        self.assertAlmostEqual(
            gallery._project(
                (
                    2.0 + 1.0 / gallery.THREE_QUARTER_BASIS_NORM,
                    2.0,
                    2.0 - gallery.THREE_QUARTER_DEPTH_FACTOR / gallery.THREE_QUARTER_BASIS_NORM,
                ),
                "three-quarter",
                lower,
                upper,
                box,
            )[0] - gallery._project(center, "three-quarter", lower, upper, box)[0],
            pixels_per_unit,
        )
        self.assertAlmostEqual(gallery._proxy_radius_pixels(1.25, lower, upper, box), 56.61484386966723)

    def test_influence_markers_use_each_vertex_dominant_bone_and_max_weight(self) -> None:
        image = Image.new("RGB", (140, 120), (20, 23, 29))
        vertices = [(-0.75, -0.65, 0.0), (0.0, 0.75, 0.0), (0.75, -0.65, 0.0)]
        dominant = [("bone-a", 1.0), ("bone-b", 0.5), ("bone-c", 0.75)]
        lower, upper, box = (-1.0, -1.0, -1.0), (1.0, 1.0, 1.0), (0, 0, 140, 120)
        gallery._draw_influence_vertices(ImageDraw.Draw(image), vertices, dominant, "front", lower, upper, box)
        for vertex, influence in zip(vertices, dominant):
            x, y = gallery._project(vertex, "front", lower, upper, box)
            self.assertEqual(image.getpixel((round(x), round(y))), gallery._dominant_vertex_color(influence))
        self.assertNotEqual(gallery._dominant_vertex_color(dominant[0]), gallery._dominant_vertex_color(dominant[1]))
        self.assertNotEqual(gallery._dominant_vertex_color(dominant[1]), gallery._dominant_vertex_color(dominant[2]))

    def test_palette_legend_uses_readable_joint_selectors_not_hashed_bone_ids(self) -> None:
        image = Image.new("RGB", (600, 180), (20, 23, 29))
        draw = ImageDraw.Draw(image)
        records = make_candidate(gallery.FROZEN_PROFILE_IDS[0])["hierarchy"]["bones"]
        gallery._draw_palette_legend(draw, records, (0, 0, 600, 180))
        self.assertEqual(gallery._bone_label(records[0]), "root")
        self.assertEqual(gallery._bone_label(records[4]), "left shoulder")

    def test_projected_capsule_outline_is_one_stadium_or_one_collapsed_circle(self) -> None:
        stadium = gallery._projected_capsule_outline((10.0, 20.0), (30.0, 20.0), 5.0, arc_steps=8)
        self.assertEqual(len(stadium), 2 * (8 + 1))
        self.assertEqual((min(point[0] for point in stadium), max(point[0] for point in stadium)), (5.0, 35.0))
        self.assertEqual((min(point[1] for point in stadium), max(point[1] for point in stadium)), (15.0, 25.0))
        self.assertNotIn((10.0, 20.0), stadium)
        self.assertNotIn((30.0, 20.0), stadium)

        collapsed = gallery._projected_capsule_outline((20.0, 20.0), (20.0, 20.0), 5.0, arc_steps=8)
        self.assertEqual(len(collapsed), 8)
        self.assertTrue(all(math.isclose(math.dist(point, (20.0, 20.0)), 5.0) for point in collapsed))

    def test_projected_capsule_boundaries_are_parallel_and_zero_length_is_safe(self) -> None:
        boundaries = gallery._projected_capsule_side_boundaries((10.0, 20.0), (30.0, 20.0), 5.0)
        self.assertEqual(
            boundaries,
            (
                ((10.0, 25.0), (30.0, 25.0)),
                ((10.0, 15.0), (30.0, 15.0)),
            ),
        )
        self.assertEqual(gallery._projected_capsule_side_boundaries((10.0, 20.0), (10.0, 20.0), 5.0), ())

    def test_proxy_rendering_uses_filled_stadium_and_collapsed_circle(self) -> None:
        background = (20, 23, 29, 255)
        image = Image.new("RGBA", (100, 100), background)
        draw = gallery.ImageDraw.Draw(image)
        gallery._draw_proxies(
            draw,
            [{"bone_id": "bone-a", "a": [-0.5, 0.0, 0.0], "b": [0.5, 0.0, 0.0], "radius": 0.1}],
            "front",
            (-1.0, -1.0, -1.0),
            (1.0, 1.0, 1.0),
            (0, 0, 100, 100),
        )
        self.assertNotEqual(image.getpixel((50, 52)), background)
        self.assertNotEqual(image.getpixel((50, 50)), background)
        self.assertNotEqual(image.getpixel((50, 50)), (*gallery._bone_color("bone-a"), 255))

        zero_length = Image.new("RGBA", (100, 100), background)
        gallery._draw_proxies(
            gallery.ImageDraw.Draw(zero_length),
            [{"bone_id": "bone-b", "a": [0.0, 0.0, -1.0], "b": [0.0, 0.0, 1.0], "radius": 0.25}],
            "front",
            (-1.0, -1.0, -1.0),
            (1.0, 1.0, 1.0),
            (0, 0, 100, 100),
        )
        self.assertNotEqual(zero_length.getpixel((59, 50)), background)

    def test_shared_pose_has_the_exact_selector_axis_and_angle_recipe(self) -> None:
        pose = gallery.load_pose(EXPERIMENT / gallery.POSE_FILE)
        actual = {
            (rule["kind"], rule["role"] or "", rule["anchors"]): (rule["axis"], rule["angle_degrees"])
            for rule in pose["rules"]
        }
        expected = {
            ("synthetic-root", "", ()): ("identity", 0.0),
            ("joint", "spine", ()): ("identity", 0.0),
            ("joint", "neck_base", ()): ("x", 2.0),
            ("joint", "head_base", ()): ("x", 2.0),
            ("joint", "shoulder", ("left",)): ("z", 6.0),
            ("joint", "shoulder", ("right",)): ("z", -6.0),
            ("joint", "elbow", ("left",)): ("z", -8.0),
            ("joint", "elbow", ("right",)): ("z", 8.0),
            ("joint", "wrist", ("left",)): ("identity", 0.0),
            ("joint", "wrist", ("right",)): ("identity", 0.0),
            ("joint", "hip", ("left",)): ("z", 5.0),
            ("joint", "hip", ("right",)): ("z", -5.0),
            ("joint", "knee", ("left",)): ("z", -6.0),
            ("joint", "knee", ("right",)): ("z", 6.0),
            ("joint", "ankle", ("left",)): ("identity", 0.0),
            ("joint", "ankle", ("right",)): ("identity", 0.0),
            ("joint", "base", ("tail",)): ("x", 4.0),
            ("joint", "segment", ("tail",)): ("x", 4.0),
        }
        self.assertEqual(actual, expected)

        tampered = json.loads((EXPERIMENT / gallery.POSE_FILE).read_text(encoding="utf-8"))
        left_elbow = next(rule for rule in tampered["rules"] if rule["role"] == "elbow" and rule["anchors"] == ["left"])
        left_elbow["angle_degrees"] = 8.0
        left_elbow["rotation_xyzw"] = [0.0, 0.0, 0.069756473744125, 0.997564050259824]
        tampered_path = self.root / "self-consistent-wrong-pose.json"
        tampered_path.write_bytes(canonical(tampered))
        with self.assertRaisesRegex(gallery.GalleryError, "exact shared recipe"):
            gallery.load_pose(tampered_path)

    def test_pose_replacement_after_validation_cannot_publish_replacement_bytes(self) -> None:
        pose_path = self.root / "pose.json"
        validated_bytes = (EXPERIMENT / gallery.POSE_FILE).read_bytes()
        replacement_bytes = b'{"format":"invalid-replacement"}\n'
        pose_path.write_bytes(validated_bytes)
        original_prepare = gallery._prepare_profile
        replaced = False

        def replace_after_validation(profile: dict[str, object], pose: dict[str, object]) -> dict[str, object]:
            nonlocal replaced
            result = original_prepare(profile, pose)
            if not replaced:
                pose_path.write_bytes(replacement_bytes)
                replaced = True
            return result

        with patch.object(gallery, "_prepare_profile", side_effect=replace_after_validation):
            output = self.root / "pose-replacement"
            gallery.build(
                self.inputs,
                output,
                source_manifest_path=self.source_manifest,
                pose_path=pose_path,
            )

        manifest = json.loads((output / gallery.MANIFEST_FILE).read_text(encoding="utf-8"))
        self.assertEqual((output / gallery.POSE_FILE).read_bytes(), validated_bytes)
        self.assertEqual(manifest["pose_sha256"], hashlib.sha256(validated_bytes).hexdigest())
        self.assertEqual(pose_path.read_bytes(), replacement_bytes)

    def test_forged_weight_and_proxy_partition_claims_fail_closed(self) -> None:
        profile_id = gallery.FROZEN_PROFILE_IDS[0]
        bridge_dir = self.inputs[profile_id].bridge_dir
        original_candidate = json.loads((bridge_dir / bridge.BRIDGE_FILE).read_text(encoding="utf-8"))
        forged_weights = json.loads(json.dumps(original_candidate))
        for row in forged_weights["weights"]["influences"]:
            row[0]["bone_id"] = "bone-source-part-root"
        rewrite_bridge_candidate(bridge_dir, forged_weights)
        with self.assertRaisesRegex(gallery.GalleryError, "every bone positive influence"):
            gallery.build(self.inputs, self.root / "forged-positive-coverage", source_manifest_path=self.source_manifest)

        forged_proxy = json.loads(json.dumps(original_candidate))
        forged_proxy["proxies"][0]["partition_vertex_count"] += 1
        rewrite_bridge_candidate(bridge_dir, forged_proxy)
        with self.assertRaisesRegex(gallery.GalleryError, "partition count"):
            gallery.build(self.inputs, self.root / "forged-proxy-partition", source_manifest_path=self.source_manifest)

    def test_nonidentity_joint_frame_fails_after_matching_inventory_update(self) -> None:
        profile_id = gallery.FROZEN_PROFILE_IDS[0]
        bad_structure = self.root / "bad-identity.json"
        bad_structure.write_bytes(canonical(make_structure(profile_id, nonidentity=True)))
        bridge_dir = self.inputs[profile_id].bridge_dir
        manifest_path = bridge_dir / bridge.MANIFEST_FILE
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        entry = next(item for item in manifest["input_files"] if item["kind"] == "inspect-structure")
        data = bad_structure.read_bytes()
        entry["sha256"], entry["bytes"] = hashlib.sha256(data).hexdigest(), len(data)
        candidate_path = bridge_dir / bridge.BRIDGE_FILE
        candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
        basis = candidate["identity"]["basis"]
        basis["input_files"] = manifest["input_files"]
        candidate["identity"]["candidate_sha256"] = bridge._digest(bridge.IDENTITY_DOMAIN + ":candidate", basis)
        candidate["identity"]["request_sha256"] = bridge._digest(bridge.IDENTITY_DOMAIN + ":request", basis)
        candidate_data = canonical(candidate) + b"\n"
        candidate_path.write_bytes(candidate_data)
        manifest["candidate_sha256"] = candidate["identity"]["candidate_sha256"]
        manifest["request_sha256"] = candidate["identity"]["request_sha256"]
        manifest["inventory"][0]["sha256"] = hashlib.sha256(candidate_data).hexdigest()
        manifest["inventory"][0]["bytes"] = len(candidate_data)
        manifest_path.write_bytes(canonical(manifest) + b"\n")
        changed = dict(self.inputs)
        changed[profile_id] = gallery.ProfileInput(bridge_dir, self.plys[profile_id], bad_structure)
        with self.assertRaisesRegex(gallery.GalleryError, "non-identity|structure Joints do not match"):
            gallery.build(changed, self.root / "nonidentity", source_manifest_path=self.source_manifest)

    def test_candidate_table_is_exactly_bound_and_changed_bytes_fail_closed(self) -> None:
        original = self.build("candidate-original")
        candidate = json.loads((EXPERIMENT / "structural_profile_candidates.json").read_text(encoding="utf-8"))
        candidate["profiles"][0]["label"] += " changed"
        changed_path = self.root / "changed-candidates.json"
        changed_path.write_bytes(json.dumps(candidate, ensure_ascii=False, sort_keys=True, indent=2).encode("utf-8") + b"\n")
        original_manifest = json.loads((original / gallery.MANIFEST_FILE).read_text(encoding="utf-8"))
        self.assertEqual(original_manifest["candidate_table"]["sha256"], gallery.FROZEN_CANDIDATE_TABLE_SHA256)
        self.assertEqual(original_manifest["candidate_table"]["kind"], "candidate-table")
        self.assertEqual(original_manifest["candidate_table"]["bytes"], len((EXPERIMENT / "structural_profile_candidates.json").read_bytes()))
        with self.assertRaisesRegex(gallery.GalleryError, "exact frozen structural candidate table"):
            self.build("candidate-changed", candidate_path=changed_path)
        stale = json.loads((EXPERIMENT / "structural_profile_candidates.json").read_text(encoding="utf-8"))
        slender = next(item for item in stale["profiles"] if item["id"] == "slender_long_limb")
        slender["part_placements"]["main|part|tail|tail_tip"] = [0, 0, -2]
        stale_path = self.root / "stale-candidates.json"
        stale_path.write_bytes(json.dumps(stale, ensure_ascii=False, sort_keys=True, indent=2).encode("utf-8") + b"\n")
        with self.assertRaisesRegex(gallery.GalleryError, "exact frozen structural candidate table"):
            self.build("candidate-stale", candidate_path=stale_path)
        broken = dict(candidate)
        broken["profiles"][0]["id"] = "changed_profile_id"
        broken_path = self.root / "broken-candidates.json"
        broken_path.write_bytes(json.dumps(broken, ensure_ascii=False, sort_keys=True, indent=2).encode("utf-8") + b"\n")
        with self.assertRaisesRegex(gallery.GalleryError, "exact frozen four-profile set"):
            self.build("candidate-broken", candidate_path=broken_path)

    def test_generated_source_bytes_are_hash_bound(self) -> None:
        profile_id = gallery.FROZEN_PROFILE_IDS[0]
        source_path = self.source_manifest.parent / f"{profile_id}.json"
        source_path.write_bytes(source_path.read_bytes() + b" ")
        with self.assertRaisesRegex(gallery.GalleryError, "does not match its manifest"):
            self.build("tampered-generated-source")

    def test_self_consistently_rehashed_generated_source_still_fails_closed(self) -> None:
        profile_id = gallery.FROZEN_PROFILE_IDS[0]
        source_path = self.source_manifest.parent / f"{profile_id}.json"
        source = json.loads(source_path.read_text(encoding="utf-8"))
        source["body"]["joints"][0]["proximal"] = address("part", "head")
        source_data = canonical(source) + b"\n"
        source_path.write_bytes(source_data)
        manifest = json.loads(self.source_manifest.read_text(encoding="utf-8"))
        record = next(item for item in manifest["profiles"] if item["id"] == profile_id)
        record["sha256"] = hashlib.sha256(source_data).hexdigest()
        record["bytes"] = len(source_data)
        self.source_manifest.write_bytes(canonical(manifest) + b"\n")
        with self.assertRaisesRegex(gallery.GalleryError, "not the exact output of the frozen candidate table"):
            self.build("source-structure-mismatch")

    def test_mapped_bone_endpoints_must_match_the_source_joint(self) -> None:
        profile_id = gallery.FROZEN_PROFILE_IDS[0]
        bridge_dir = self.inputs[profile_id].bridge_dir
        candidate = json.loads((bridge_dir / bridge.BRIDGE_FILE).read_text(encoding="utf-8"))
        candidate["hierarchy"]["bones"][1]["proximal"] = address("part", "head")
        rewrite_bridge_candidate(bridge_dir, candidate)
        with self.assertRaisesRegex(gallery.GalleryError, "mapped bone endpoints do not match"):
            self.build("mapped-endpoint-mismatch")

    def test_self_consistently_translated_hierarchy_fails_source_geometry_binding(self) -> None:
        profile_id = gallery.FROZEN_PROFILE_IDS[0]
        bridge_dir = self.inputs[profile_id].bridge_dir
        candidate = json.loads((bridge_dir / bridge.BRIDGE_FILE).read_text(encoding="utf-8"))
        for bone in candidate["hierarchy"]["bones"]:
            bone["a"][0] += 100
            bone["b"][0] += 100
        for proxy in candidate["proxies"]:
            proxy["a"][0] += 100
            proxy["b"][0] += 100
        rewrite_bridge_candidate(bridge_dir, candidate)
        with self.assertRaisesRegex(gallery.GalleryError, "not bound to the source root Part|not derived from source Part placements"):
            self.build("translated-hierarchy")

    def test_synthetic_root_surface_anchor_is_recomputed_from_neutral_geometry(self) -> None:
        profile_id = gallery.FROZEN_PROFILE_IDS[0]
        bridge_dir = self.inputs[profile_id].bridge_dir
        candidate = json.loads((bridge_dir / bridge.BRIDGE_FILE).read_text(encoding="utf-8"))
        candidate["hierarchy"]["bones"][0]["a"][0] += 0.125
        candidate["hierarchy"]["bones"][0]["length"] = math.dist(
            candidate["hierarchy"]["bones"][0]["a"],
            candidate["hierarchy"]["bones"][0]["b"],
        )
        candidate["proxies"][0]["a"] = candidate["hierarchy"]["bones"][0]["a"]
        rewrite_bridge_candidate(bridge_dir, candidate)
        with self.assertRaisesRegex(gallery.GalleryError, "surface anchor is not exactly derived"):
            self.build("root-anchor-mismatch")

    def test_proxy_endpoints_and_radius_are_recomputed_from_bones_and_partition(self) -> None:
        profile_id = gallery.FROZEN_PROFILE_IDS[0]
        bridge_dir = self.inputs[profile_id].bridge_dir
        original = json.loads((bridge_dir / bridge.BRIDGE_FILE).read_text(encoding="utf-8"))
        changed_endpoint = json.loads(json.dumps(original))
        changed_endpoint["proxies"][0]["a"][0] += 0.125
        rewrite_bridge_candidate(bridge_dir, changed_endpoint)
        with self.assertRaisesRegex(gallery.GalleryError, "proxy endpoints or ownership do not match"):
            self.build("proxy-endpoint-mismatch")

        changed_radius = json.loads(json.dumps(original))
        changed_radius["proxies"][0]["radius"] += 0.125
        rewrite_bridge_candidate(bridge_dir, changed_radius)
        with self.assertRaisesRegex(gallery.GalleryError, "proxy radius does not match"):
            self.build("proxy-radius-mismatch")

    def test_cli_requires_three_paths_per_profile_and_succeeds(self) -> None:
        generator = EXPERIMENT / "generate_structural_embodiment_gallery.py"
        command = [
            "--source-manifest",
            str(self.source_manifest),
            "--output",
            str(self.root / "cli-out"),
        ]
        for profile_id in gallery.FROZEN_PROFILE_IDS:
            command.extend(["--profile", f"{profile_id}={self.inputs[profile_id].bridge_dir},{self.plys[profile_id]},{self.structures[profile_id]}"])
        stdout, stderr = io.StringIO(), io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            returncode = gallery.main(command)
        self.assertEqual(returncode, 0, stderr.getvalue())
        self.assertEqual(json.loads(stdout.getvalue())["status"], "success")
        missing_structure = subprocess.run(
            [sys.executable, str(generator), "--source-manifest", str(self.source_manifest), "--output", str(self.root / "cli-missing"), "--profile", f"{gallery.FROZEN_PROFILE_IDS[0]}={self.inputs[gallery.FROZEN_PROFILE_IDS[0]].bridge_dir},{self.plys[gallery.FROZEN_PROFILE_IDS[0]]}"],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertNotEqual(missing_structure.returncode, 0)
        self.assertEqual(json.loads(missing_structure.stderr)["status"], "failure")

        missing_source_manifest = subprocess.run(
            [sys.executable, str(generator), "--output", str(self.root / "cli-no-source-manifest")],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertNotEqual(missing_source_manifest.returncode, 0)

    def test_publication_stays_on_open_parent_after_ancestor_swap(self) -> None:
        parent = self.root / "publication-parent"
        parent.mkdir()
        moved_parent = self.root / "publication-parent-opened"
        attacker_parent = self.root / "attacker-parent"
        attacker_parent.mkdir()
        attacker_output = attacker_parent / "gallery"
        attacker_output.mkdir()
        sentinel = attacker_output / "keep.txt"
        sentinel.write_text("attacker destination", encoding="utf-8")
        original_create_stage = gallery.structural_atomic_publish.create_stage

        def swap_after_stage(parent_fd: int, destination_name: str):
            stage = original_create_stage(parent_fd, destination_name)
            parent.rename(moved_parent)
            parent.symlink_to(attacker_parent, target_is_directory=True)
            return stage

        try:
            with patch.object(
                gallery.structural_atomic_publish,
                "create_stage",
                side_effect=swap_after_stage,
            ):
                gallery.build(
                    self.inputs,
                    parent / "gallery",
                    source_manifest_path=self.source_manifest,
                )
        finally:
            if parent.is_symlink():
                parent.unlink()
            if moved_parent.exists():
                moved_parent.rename(parent)

        self.assertTrue((parent / "gallery" / gallery.MANIFEST_FILE).is_file())
        self.assertEqual(sentinel.read_text(encoding="utf-8"), "attacker destination")
        self.assertEqual(sorted(path.name for path in attacker_parent.iterdir()), ["gallery"])
        self.assertEqual(sorted(path.name for path in attacker_output.iterdir()), ["keep.txt"])

    def test_cleanup_stage_preserves_replacement_before_top_level_cleanup(self) -> None:
        parent = self.root / "gallery-cleanup-parent"
        parent.mkdir()
        parent_fd = gallery.structural_atomic_publish.open_directory_no_symlinks(parent)
        stage_name = None
        try:
            stage_name, stage = gallery.structural_atomic_publish.create_stage(parent_fd, "gallery")
            (stage / "owned.txt").write_bytes(b"owned")
            attacker_stage = parent / str(stage_name)
            original_stage = parent / "original-stage"
            original_remove = gallery.structural_atomic_publish._remove_tree_contents

            def clean_then_replace(directory_fd: int) -> bool:
                result = original_remove(directory_fd)
                attacker_stage.rename(original_stage)
                attacker_stage.mkdir()
                (attacker_stage / "attacker.txt").write_bytes(b"attacker")
                return result

            with patch.object(gallery.structural_atomic_publish, "_remove_tree_contents", side_effect=clean_then_replace):
                self.assertTrue(gallery.structural_atomic_publish.cleanup_stage(parent_fd, stage_name))
            self.assertEqual((attacker_stage / "attacker.txt").read_bytes(), b"attacker")
            self.assertTrue(original_stage.is_dir())
            self.assertEqual(list(original_stage.iterdir()), [])
        finally:
            gallery.structural_atomic_publish.close_stage(stage_name)
            os.close(parent_fd)

    def test_different_regular_parent_before_open_is_rejected(self) -> None:
        parent = self.root / "pre-open-parent"
        parent.mkdir()
        displaced_parent = self.root / "pre-open-parent-displaced"
        original_open = gallery.structural_atomic_publish.open_directory_no_symlinks

        def replace_before_open(path: Path) -> int:
            parent.rename(displaced_parent)
            parent.mkdir()
            return original_open(path)

        with patch.object(
            gallery.structural_atomic_publish,
            "open_directory_no_symlinks",
            side_effect=replace_before_open,
        ):
            with self.assertRaisesRegex(gallery.GalleryError, "changed between validation and open"):
                gallery.build(
                    self.inputs,
                    parent / "gallery",
                    source_manifest_path=self.source_manifest,
                )

        self.assertFalse((parent / "gallery").exists())
        self.assertFalse((displaced_parent / "gallery").exists())

    def test_symlinked_parent_is_rejected_for_every_admitted_path_kind(self) -> None:
        profile_id = gallery.FROZEN_PROFILE_IDS[0]
        alias = self.root / "alias"
        alias.symlink_to(self.root, target_is_directory=True)

        path_cases = {
            "bridge": gallery.ProfileInput(alias / "bridges" / profile_id, self.plys[profile_id], self.structures[profile_id]),
            "ply": gallery.ProfileInput(self.inputs[profile_id].bridge_dir, alias / self.plys[profile_id].name, self.structures[profile_id]),
            "structure": gallery.ProfileInput(self.inputs[profile_id].bridge_dir, self.plys[profile_id], alias / self.structures[profile_id].name),
        }
        for name, record in path_cases.items():
            with self.subTest(path=name):
                changed = dict(self.inputs)
                changed[profile_id] = record
                with self.assertRaisesRegex(gallery.GalleryError, "symlinked path component"):
                    gallery.build(changed, self.root / f"symlink-{name}", source_manifest_path=self.source_manifest)

        candidate_copy = self.root / "candidate.json"
        candidate_copy.write_bytes((EXPERIMENT / "structural_profile_candidates.json").read_bytes())
        with self.assertRaisesRegex(gallery.GalleryError, "symlinked path component"):
            gallery.build(self.inputs, self.root / "symlink-candidate", source_manifest_path=self.source_manifest, candidate_path=alias / candidate_copy.name)

        pose_copy = self.root / "pose.json"
        pose_copy.write_bytes((EXPERIMENT / gallery.POSE_FILE).read_bytes())
        with self.assertRaisesRegex(gallery.GalleryError, "symlinked path component"):
            gallery.build(self.inputs, self.root / "symlink-pose", source_manifest_path=self.source_manifest, pose_path=alias / pose_copy.name)

        with self.assertRaisesRegex(gallery.GalleryError, "symlinked path component"):
            gallery.build(self.inputs, self.root / "symlink-source-manifest", source_manifest_path=alias / gallery.SOURCES_DIR / gallery.SOURCE_MANIFEST_FILE)

        real_output_parent = self.root / "real-output"
        real_output_parent.mkdir()
        linked_output_parent = self.root / "linked-output"
        linked_output_parent.symlink_to(real_output_parent, target_is_directory=True)
        with self.assertRaisesRegex(gallery.GalleryError, "symlinked path component"):
            gallery.build(self.inputs, linked_output_parent / "gallery", source_manifest_path=self.source_manifest)


if __name__ == "__main__":
    unittest.main()
