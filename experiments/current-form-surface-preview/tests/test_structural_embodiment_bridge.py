#!/usr/bin/env python3
"""Focused synthetic coverage for the disposable structural bridge."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch


HERE = Path(__file__).resolve()
EXPERIMENT = HERE.parents[1]
sys.path.insert(0, str(EXPERIMENT))
import structural_embodiment_bridge as bridge  # noqa: E402
import structural_atomic_publish  # noqa: E402


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def address(kind: str, role: str, anchors: list[str] | None = None) -> dict[str, object]:
    return {"namespace": "main", "anchors": anchors or [], "kind": kind, "role": role}


def source_part(role: str, parent: dict[str, object] | None, point: list[float]) -> dict[str, object]:
    return {"address": address("part", role), "containment": {"root": True} if parent is None else {"parent": parent}, "placement": {"translation": point, "rotation_xyzw": [0, 0, 0, 1]}}


def frame() -> dict[str, object]:
    return {"translation": [0, 0, 0], "rotation_xyzw": [0, 0, 0, 1]}


def make_structure() -> dict[str, object]:
    root = address("part", "root")
    child = address("part", "child")
    joint = {"address": address("joint", "hinge"), "proximal": root, "distal": child, "proximal_frame": frame(), "distal_frame": frame()}
    graph = {"projection": "source-preserving-provisional-structural-debug", "contract": {"family": "creature-kernel.body", "revision": 1}, "source": {"document": "synthetic", "namespace": "main", "dependencies": []}, "basis": {"length_unit": "metre", "handedness": "right", "up": "+y", "forward": "+z"}, "profiles": {"semantic_numeric": "ck.numeric-frame.r1"}, "extensions": [], "modules": [], "parts": [source_part("root", None, [0, 0, 0]), source_part("child", root, [0, 1, 0])], "joints": [joint], "sockets": [], "attachments": [], "landmarks": [], "dimensions": [], "frames": [], "regions": [], "capabilities": [], "fields": []}
    return {"format": bridge.STRUCTURE_FORMAT, "operation": "inspect-structure", "stage": "structural-validation", "status": "success", "processing_complete": True, "diagnostics_complete": True, "diagnostics": [], "summary": {"parts": 2, "joints": 1}, "graph": graph}


def descriptor(address_value: dict[str, object], point: list[float], profile: str) -> dict[str, object]:
    return {"descriptor_kind": "display-only-form-descriptor", "address": address_value, "parent": None, "placement_source": "authored-root", "reference_point": point, "dimension_roles": ["form_radius"], "profile_id": profile, "source": "profile-derived-display", "provenance": {"source": "profile-derived-display", "resource_profile_id": "ck.resource.body.r2", "shape_basis": "source-authored-dimensions-plus-fixed-display-factor"}, "shape": {"name": "capsule", "radius": 1.0, "endpoint": [0, 1, 0], "axis": [0, 1, 0]}}


def make_form(profile: str = "neutral-v0") -> dict[str, object]:
    root = address("part", "root")
    child = address("part", "child")
    descriptors = [descriptor(root, [0, 0, 0], profile), descriptor(child, [0, 1, 0], profile)]
    variant = {"id": profile, "profile_id": profile, "provenance": {"source": "profile-derived-display", "resource_profile_id": "ck.resource.body.r2", "shape_basis": "source-authored-dimensions-plus-fixed-display-factor"}, "descriptors": descriptors, "torso_profile": {}, "head_neck_profile": {}, "arm_profile": {}, "leg_profile": {}, "foot_profile": {}}
    empty_object = {}
    return {"format": bridge.SOURCE_FORMAT, "operation": "inspect-provisional-form", "status": "success", "stage": "provisional-form", "processing_complete": True, "diagnostics_complete": True, "diagnostics": [], "source": {"document": "synthetic", "namespace": "main", "resource_profile_id": "ck.resource.body.r2"}, "reference_scale": {"parent": root, "child": child, "axis_delta": [0, 1, 0], "squared_length": 1, "source": "exact-containment-edge"}, "authored_dimensions": [], "authored_landmarks": [], "authored_frames": [], "authored_torso_profile": empty_object, "authored_head_neck_profile": empty_object, "authored_arm_profile": empty_object, "authored_leg_profile": empty_object, "authored_foot_profile": empty_object, "variants": [variant], "limitations": "Exploratory Readiness geometry evidence only; not production."}


def tetra_ply() -> bytes:
    # Outward-oriented tetrahedron with one vertex above the base.
    lines = ["ply", "format ascii 1.0", "element vertex 4", "property float x", "property float y", "property float z", "property float nx", "property float ny", "property float nz", "element face 4", "property list uchar int vertex_indices", "end_header", "0 0 0 0 -1 -1", "1 0 0 1 -1 -1", "0 1 0 -1 1 -1", "0 0 1 -1 -1 1", "3 0 2 1", "3 0 1 3", "3 0 3 2", "3 1 2 3"]
    return ("\n".join(lines) + "\n").encode("ascii")


def make_bundle(root: Path, structure: dict[str, object], form: dict[str, object], *, profile: str = "neutral-v0", mode: str = "valid") -> Path:
    bundle = root / "surface-bundle"
    variant_dir = bundle / profile
    variant_dir.mkdir(parents=True)
    form_variant = form["variants"][0]
    ply = tetra_ply()
    (variant_dir / "surface.ply").write_bytes(ply)
    addresses = [item["address"] for item in form_variant["descriptors"]]
    semantic = {"format": bridge.SEMANTIC_FORMAT, "source_format": bridge.SOURCE_FORMAT, "variant_id": profile, "source_variant_sha256": hashlib.sha256(canonical(form_variant)).hexdigest(), "surface_sha256": hashlib.sha256(ply).hexdigest(), "vertex_count": 4, "source_node_labels": [addresses[0], addresses[0], addresses[0], addresses[1]], "attribution": "every recipe component resolves to its source descriptor owner; no synthetic node identity is emitted"}
    (variant_dir / "semantic.json").write_bytes(canonical(semantic))
    signed_volume = 1.0 / 6.0
    metrics = {"vertex_count": 4, "face_count": 4, "component_count": 1, "watertight": True, "finite_vertices": True, "finite_normals": True, "valid_indices": True, "signed_volume": signed_volume}
    if mode == "metrics":
        metrics["vertex_count"] = 3
    (variant_dir / "metrics.json").write_bytes(canonical(metrics))
    source_variant_hash = hashlib.sha256(canonical(form_variant)).hexdigest()
    successor = {"format": bridge.SUCCESSOR_FORMAT, "variant_id": profile, "profile_id": profile, "source_variant_sha256": source_variant_hash, "consumer_id": "successor-surface-v1"}
    (variant_dir / "successor.json").write_bytes(canonical(successor))
    (variant_dir / "guide-skin-composite.png").write_bytes(b"synthetic png placeholder")
    input_files = [("ply", variant_dir / "surface.ply"), ("semantic-sidecar", variant_dir / "semantic.json"), ("metrics", variant_dir / "metrics.json"), ("successor-consumer-sidecar", variant_dir / "successor.json"), ("guide-skin-composite-png", variant_dir / "guide-skin-composite.png")]
    inventory = []
    for kind, path in input_files:
        data = path.read_bytes()
        inventory.append({"kind": kind, "path": f"{profile}/{path.name}", "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data), **({"width": 1, "height": 1, "views": ["front", "side", "three-quarter"], "panels_per_view": 3, "mode": "RGB"} if kind.endswith("png") else {})})
    source_data = canonical(form)
    variant_record = {"id": profile, "profile_id": profile, "source_variant_sha256": source_variant_hash, "metrics": metrics, "inventory": inventory}
    manifest = {"format": bridge.SUCCESSOR_FORMAT, "status": "success", "consumer_id": "successor-surface-v1", "source_format": bridge.SOURCE_FORMAT, "source": {"format": bridge.SOURCE_FORMAT, "sha256": hashlib.sha256(source_data).hexdigest(), "document": "synthetic", "namespace": "main", "resource_profile_id": "ck.resource.body.r2"}, "shared_render_bounds": {"min": [-1, -1, -1], "max": [1, 1, 1]}, "canvas": {"width": 1, "height": 1, "mode": "RGB"}, "layout": {}, "projections": [], "generator": {}, "variants": [variant_record]}
    if mode == "lineage":
        manifest["source"]["document"] = "wrong"
    (bundle / "successor-surface-manifest.json").write_bytes(canonical(manifest))
    return bundle


def refresh_inventory(bundle: Path, name: str, data: bytes) -> None:
    manifest_path = bundle / "successor-surface-manifest.json"
    manifest = json.loads(manifest_path.read_text())
    entry = next(item for item in manifest["variants"][0]["inventory"] if item["path"].endswith("/" + name))
    entry["sha256"] = hashlib.sha256(data).hexdigest()
    entry["bytes"] = len(data)
    manifest_path.write_bytes(canonical(manifest))


class StructuralEmbodimentBridgeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.structure = make_structure()
        self.form = make_form()
        self.structure_path = self.root / "structure.json"
        self.form_path = self.root / "form.json"
        self.structure_path.write_bytes(canonical(self.structure))
        self.form_path.write_bytes(canonical(self.form))
        self.bundle = make_bundle(self.root, self.structure, self.form)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_success_hierarchy_mapping_weights_proxies_and_pose_boundary(self) -> None:
        result = bridge.build(self.structure_path, self.form_path, self.bundle, "synthetic_profile", "neutral-v0", self.root / "out")
        candidate = result["candidate"]
        bones = {bone["id"]: bone for bone in candidate["hierarchy"]["bones"]}
        self.assertEqual(len(candidate["hierarchy"]["bones"]), 2)
        self.assertTrue(candidate["checks"]["rooted_acyclic_hierarchy"])
        self.assertTrue(candidate["checks"]["spatially_continuous_hierarchy"])
        self.assertEqual(bones["bone-source-part-root"]["a"], [0.25, 0.25, 0.25])
        self.assertEqual(bones["bone-source-part-root"]["b"], [0.0, 0.0, 0.0])
        self.assertEqual(
            bones["bone-source-part-root"]["surface_anchor_rule"],
            "centroid of the complete neutral surface, with lexicographically stable farthest-vertex fallback",
        )
        self.assertEqual(bones["bone-joint-" + hashlib.sha256(canonical(address("joint", "hinge"))).hexdigest()[:16]]["a"], bones["bone-source-part-root"]["b"])
        self.assertEqual(len(candidate["hierarchy"]["joint_address_to_bone"]), 1)
        self.assertEqual(len(candidate["weights"]["influences"]), 4)
        self.assertTrue(all(len(row) <= 4 and abs(sum(item["weight"] for item in row) - 1.0) < 1e-12 for row in candidate["weights"]["influences"]))
        self.assertEqual(len(candidate["proxies"]), 2)
        self.assertEqual(candidate["pose"]["status"], "later-slice")
        self.assertTrue((self.root / "out" / bridge.BRIDGE_FILE).is_file())
        self.assertTrue((self.root / "out" / bridge.MANIFEST_FILE).is_file())

    def test_bone_parent_comes_from_graph_topology_not_joint_sort_order(self) -> None:
        structure = make_structure()
        root = address("part", "root")
        child = address("part", "child")
        grandchild = address("part", "grandchild")
        structure["graph"]["parts"].append(source_part("grandchild", child, [0, 1, 0]))
        structure["graph"]["joints"][0]["address"]["role"] = "z-parent"
        structure["graph"]["joints"].append({
            "address": address("joint", "a-child"),
            "proximal": child,
            "distal": grandchild,
            "proximal_frame": frame(),
            "distal_frame": frame(),
        })
        normalized = bridge._validate_structure(structure)
        descriptor_map = {
            bridge._address(root, "root", kind="part")[0]: {"reference_point": (0.0, 0.0, 0.0)},
            bridge._address(child, "child", kind="part")[0]: {"reference_point": (0.0, 1.0, 0.0)},
            bridge._address(grandchild, "grandchild", kind="part")[0]: {"reference_point": (0.0, 2.0, 0.0)},
        }
        points = [(0.0, 0.0, 0.0), (1.0, 0.0, 0.2), (0.0, 1.0, 0.5), (1.0, 1.0, 0.2), (1.0, 2.0, 0.3)]
        # The intermediate child intentionally wins no surface vertices.  Its
        # incident bones must still receive truthful adjacent-owner influence,
        # while the absence remains explicit evidence rather than a fake proxy
        # ownership requirement.
        labels = [root, root, root, grandchild, grandchild]
        candidate = bridge._build_candidate(
            normalized,
            {"source": {"document": "synthetic", "namespace": "main"}, "variants": {"neutral-v0": {"descriptors": descriptor_map}}},
            {"variant": {"ply": {"vertices": points}, "semantic": {"source_node_labels": labels}}},
            "neutral-v0",
            {},
        )
        bones = {bone.get("joint", {}).get("role"): bone for bone in candidate["hierarchy"]["bones"]}
        self.assertEqual(bones["a-child"]["parent"], bones["z-parent"]["id"])
        self.assertEqual(
            candidate["semantic_coverage"]["unobserved_source_parts"],
            [child],
        )
        self.assertTrue(candidate["checks"]["every_bone_has_positive_influence"])
        self.assertTrue(candidate["checks"]["complete_proxy_vertex_partition"])

    def test_spatial_discontinuity_mutation_fails_closed(self) -> None:
        result = bridge.build(self.structure_path, self.form_path, self.bundle, "synthetic_profile", "neutral-v0", self.root / "continuity")
        bones = deepcopy(result["candidate"]["hierarchy"]["bones"])
        child = next(bone for bone in bones if bone["parent"] == "bone-source-part-root")
        child["a"][0] += 0.25
        with self.assertRaisesRegex(bridge.BridgeError, "spatial discontinuity"):
            bridge._validate_bone_continuity(bones)

    def test_root_reference_outside_owned_surface_fails_closed(self) -> None:
        form = deepcopy(self.form)
        form["variants"][0]["descriptors"][0]["reference_point"] = [2, 2, 2]
        form_path = self.root / "outside-root-reference-form.json"
        form_path.write_bytes(canonical(form))
        bundle = make_bundle(self.root / "outside-root-reference", self.structure, form)
        with self.assertRaisesRegex(bridge.BridgeError, "outside its owned surface evidence"):
            bridge.build(self.structure_path, form_path, bundle, "synthetic_profile", "neutral-v0", self.root / "outside-root-reference-out")

    def test_root_surface_anchor_uses_all_vertices_and_deterministic_fallback(self) -> None:
        structure = make_structure()
        form = make_form()
        form["variants"][0]["descriptors"][0]["reference_point"] = [1 / 3, 1 / 3, 0.0]
        validated_structure = bridge._validate_structure(structure)
        validated_form = bridge._validate_form(
            form,
            "neutral-v0",
            structure=validated_structure,
            form_hash=hashlib.sha256(canonical(form)).hexdigest(),
        )
        candidate = bridge._build_candidate(
            validated_structure,
            validated_form,
            {
                "variant": {
                    "ply": {"vertices": [(0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (1 / 3, 1 / 3, 0.0)]},
                    "semantic": {"source_node_labels": [address("part", "root")] * 3 + [address("part", "child")]},
                },
            },
            "neutral-v0",
            {},
        )
        root = candidate["hierarchy"]["bones"][0]
        self.assertEqual(root["a"], [0.0, 1.0, 0.0])
        self.assertEqual(root["b"], [1 / 3, 1 / 3, 0.0])

    def test_separate_destinations_are_byte_identical_and_identity_has_no_paths(self) -> None:
        first = bridge.build(self.structure_path, self.form_path, self.bundle, "synthetic_profile", "neutral-v0", self.root / "first")
        second = bridge.build(self.structure_path, self.form_path, self.bundle, "synthetic_profile", "neutral-v0", self.root / "second")
        self.assertEqual(first["manifest"], second["manifest"])
        self.assertEqual((self.root / "first" / bridge.BRIDGE_FILE).read_bytes(), (self.root / "second" / bridge.BRIDGE_FILE).read_bytes())
        self.assertNotIn(str(self.root), (self.root / "first" / bridge.BRIDGE_FILE).read_text())

    def test_publication_stays_on_opened_parent_after_ancestor_swap(self) -> None:
        parent = self.root / "bridge-parent"
        parent.mkdir()
        output = parent / "bridge-output"
        moved_parent = self.root / "opened-bridge-parent"

        def swap_then_publish(parent_fd: int, stage_name: str, destination_name: str) -> None:
            parent.rename(moved_parent)
            parent.mkdir()
            structural_atomic_publish.publish_no_replace(parent_fd, stage_name, destination_name)

        with patch.object(bridge, "_atomic_publish_no_replace", side_effect=swap_then_publish):
            bridge.build(self.structure_path, self.form_path, self.bundle, "synthetic_profile", "neutral-v0", output)
        self.assertTrue((moved_parent / "bridge-output" / bridge.BRIDGE_FILE).is_file())
        self.assertFalse((parent / "bridge-output").exists())

    def test_regular_parent_replacement_before_open_is_rejected(self) -> None:
        parent = self.root / "validated-bridge-parent"
        parent.mkdir()
        output = parent / "bridge-output"
        moved_parent = self.root / "validated-bridge-parent-original"
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
            with self.assertRaisesRegex(bridge.BridgeError, "changed after validation"):
                bridge.build(
                    self.structure_path,
                    self.form_path,
                    self.bundle,
                    "synthetic_profile",
                    "neutral-v0",
                    output,
                )
        self.assertFalse((parent / "bridge-output").exists())
        self.assertFalse((moved_parent / "bridge-output").exists())

    def test_failures_leave_no_output(self) -> None:
        cases = [
            ("malformed", self.root / "malformed.json", b"{"),
            ("structure-lineage", self.root / "bad-structure.json", canonical({**self.structure, "status": "failure"})),
        ]
        for name, path, data in cases:
            with self.subTest(name=name):
                path.write_bytes(data)
                output = self.root / name
                with self.assertRaises(bridge.BridgeError):
                    bridge.build(path, self.form_path, self.bundle, "synthetic_profile", "neutral-v0", output)
                self.assertFalse(output.exists())

        deep = self.root / "deep.json"
        deep.write_text("{\"x\":" * 2000 + "0" + "}" * 2000, encoding="utf-8")
        with self.assertRaises(bridge.BridgeError):
            bridge._load_json(deep, "deep JSON")

        collision_output = self.root / "collision-out"
        with self.assertRaisesRegex(bridge.BridgeError, "must not collide"):
            bridge.build(
                self.structure_path,
                self.form_path,
                self.bundle,
                "neutral-v0",
                "neutral-v0",
                collision_output,
            )
        self.assertFalse(collision_output.exists())

    def test_inventory_lineage_metrics_labels_and_topology_fail_closed(self) -> None:
        for mode in ("lineage", "metrics"):
            with self.subTest(mode=mode):
                bundle = make_bundle(self.root / mode, self.structure, self.form, mode=mode)
                with self.assertRaises(bridge.BridgeError):
                    bridge.build(self.structure_path, self.form_path, bundle, "synthetic_profile", "neutral-v0", self.root / (mode + "-out"))
        bad_bundle = make_bundle(self.root / "labels", self.structure, self.form)
        semantic_path = bad_bundle / "neutral-v0" / "semantic.json"
        semantic = json.loads(semantic_path.read_text())
        semantic["source_node_labels"][0] = address("part", "unknown")
        semantic_path.write_bytes(canonical(semantic))
        manifest = json.loads((bad_bundle / "successor-surface-manifest.json").read_text())
        entry = manifest["variants"][0]["inventory"][1]
        data = semantic_path.read_bytes()
        entry["sha256"], entry["bytes"] = hashlib.sha256(data).hexdigest(), len(data)
        (bad_bundle / "successor-surface-manifest.json").write_bytes(canonical(manifest))
        with self.assertRaises(bridge.BridgeError):
            bridge.build(self.structure_path, self.form_path, bad_bundle, "synthetic_profile", "neutral-v0", self.root / "labels-out")

    def test_inventory_ply_and_topology_fail_closed_without_partial_output(self) -> None:
        inventory_bundle = make_bundle(self.root / "inventory", self.structure, self.form)
        manifest_path = inventory_bundle / "successor-surface-manifest.json"
        manifest = json.loads(manifest_path.read_text())
        manifest["variants"][0]["inventory"][0]["sha256"] = "0" * 64
        manifest_path.write_bytes(canonical(manifest))
        output = self.root / "inventory-out"
        with self.assertRaises(bridge.BridgeError):
            bridge.build(self.structure_path, self.form_path, inventory_bundle, "synthetic_profile", "neutral-v0", output)
        self.assertFalse(output.exists())

        ply_bundle = make_bundle(self.root / "ply", self.structure, self.form)
        ply_path = ply_bundle / "neutral-v0" / "surface.ply"
        bad_ply = ply_path.read_bytes().replace(b"3 0 2 1\n", b"3 0 2 9\n")
        ply_path.write_bytes(bad_ply)
        refresh_inventory(ply_bundle, "surface.ply", bad_ply)
        with self.assertRaises(bridge.BridgeError):
            bridge.build(self.structure_path, self.form_path, ply_bundle, "synthetic_profile", "neutral-v0", self.root / "ply-out")

        topology_bundle = make_bundle(self.root / "topology", self.structure, self.form)
        topology_path = topology_bundle / "neutral-v0" / "surface.ply"
        bad_topology = topology_path.read_bytes().replace(b"3 0 2 1\n", b"3 0 1 3\n")
        topology_path.write_bytes(bad_topology)
        refresh_inventory(topology_bundle, "surface.ply", bad_topology)
        with self.assertRaises(bridge.BridgeError):
            bridge.build(self.structure_path, self.form_path, topology_bundle, "synthetic_profile", "neutral-v0", self.root / "topology-out")

    def test_ply_rejects_closed_shells_joined_only_at_one_vertex(self) -> None:
        vertices = [
            "0 0 0 1 1 1",
            "1 0 0 1 1 1",
            "0 1 0 1 1 1",
            "0 0 1 1 1 1",
            "-1 0 0 -1 -1 -1",
            "0 -1 0 -1 -1 -1",
            "0 0 -1 -1 -1 -1",
        ]
        faces = [
            "3 0 2 1", "3 0 1 3", "3 0 3 2", "3 1 2 3",
            "3 0 4 5", "3 0 6 4", "3 0 5 6", "3 4 6 5",
        ]
        lines = [
            "ply", "format ascii 1.0", "element vertex 7",
            "property float x", "property float y", "property float z",
            "property float nx", "property float ny", "property float nz",
            "element face 8", "property list uchar int vertex_indices",
            "end_header", *vertices, *faces,
        ]
        data = ("\n".join(lines) + "\n").encode("ascii")
        path = self.root / "point-contact.ply"
        path.write_bytes(data)
        with self.assertRaisesRegex(bridge.BridgeError, "connected only at vertices"):
            bridge._parse_ply(
                path,
                expected_sha256=hashlib.sha256(data).hexdigest(),
            )

    def test_cycle_uncovered_and_zero_length_fail_closed(self) -> None:
        cyclic = deepcopy(self.structure)
        parts = cyclic["graph"]["parts"]
        parts[0]["containment"] = {"parent": address("part", "child")}
        cyclic_path = self.root / "cyclic.json"
        cyclic_path.write_bytes(canonical(cyclic))
        with self.assertRaises(bridge.BridgeError):
            bridge.build(cyclic_path, self.form_path, self.bundle, "synthetic_profile", "neutral-v0", self.root / "cyclic-out")

        uncovered = make_bundle(self.root / "uncovered", self.structure, self.form)
        semantic_path = uncovered / "neutral-v0" / "semantic.json"
        semantic = json.loads(semantic_path.read_text())
        semantic["source_node_labels"].pop()
        uncovered_semantic = canonical(semantic)
        semantic_path.write_bytes(uncovered_semantic)
        refresh_inventory(uncovered, "semantic.json", uncovered_semantic)
        with self.assertRaises(bridge.BridgeError):
            bridge.build(self.structure_path, self.form_path, uncovered, "synthetic_profile", "neutral-v0", self.root / "uncovered-out")

        zero_form = make_form()
        zero_form["variants"][0]["descriptors"][1]["reference_point"] = [0, 0, 0]
        zero_form_path = self.root / "zero-form.json"
        zero_form_path.write_bytes(canonical(zero_form))
        zero_bundle = make_bundle(self.root / "zero", self.structure, zero_form)
        with self.assertRaises(bridge.BridgeError):
            bridge.build(self.structure_path, zero_form_path, zero_bundle, "synthetic_profile", "neutral-v0", self.root / "zero-out")

    def test_cli_success_and_failure_are_json_envelopes(self) -> None:
        generator = EXPERIMENT / "generate_structural_embodiment_bridge.py"
        output = self.root / "cli-out"
        command = [sys.executable, str(generator), "--inspect-structure", str(self.structure_path), "--inspect-provisional-form", str(self.form_path), "--surface-bundle", str(self.bundle), "--candidate-profile-id", "synthetic_profile", "--surface-variant-id", "neutral-v0", "--output", str(output)]
        success = subprocess.run(command, text=True, capture_output=True, check=False)
        self.assertEqual(success.returncode, 0, success.stderr)
        self.assertEqual(json.loads(success.stdout)["status"], "success")
        failed = subprocess.run(command, text=True, capture_output=True, check=False)
        self.assertNotEqual(failed.returncode, 0)
        self.assertEqual(json.loads(failed.stderr)["status"], "failure")
        usage_failed = subprocess.run([sys.executable, str(generator)], text=True, capture_output=True, check=False)
        self.assertNotEqual(usage_failed.returncode, 0)
        self.assertEqual(json.loads(usage_failed.stderr)["status"], "failure")


if __name__ == "__main__":
    unittest.main()
