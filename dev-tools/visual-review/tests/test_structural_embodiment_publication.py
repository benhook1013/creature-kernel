from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import shutil
import struct
import sys
import tempfile
import unittest
import zlib
from pathlib import Path
from unittest.mock import patch


HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))


def load_module(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, HERE / filename)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


publisher = load_module("structural_embodiment_publisher", "publish_structural_embodiment.py")


def semantic_fixture_profile(profile_id: str, source_data: bytes, pose: dict[str, object]) -> dict[str, object]:
    gallery = publisher.gallery_generator
    source_root = json.loads(source_data)
    source = publisher._source_semantic_inputs(source_data, profile_id)
    root_part = source["root_part"]
    raw_parts = source_root["body"]["parts"]
    root_address = next(item["address"] for item in raw_parts if gallery._address_key(item["address"], "fixture root") == root_part)

    radius = 2.0
    offsets = [(0.0, radius, 0.0), (0.0, -radius, 0.0)]
    vertices = list(offsets)
    normals = [(0.0, 1.0, 0.0), (0.0, -1.0, 0.0)]
    for y in (radius * 0.5, -radius * 0.5):
        ring_radius = math.sqrt(radius * radius - y * y)
        for index in range(8):
            angle = math.tau * index / 8.0
            vertices.append((ring_radius * math.cos(angle), y, ring_radius * math.sin(angle)))
            normals.append((ring_radius * math.cos(angle) / radius, y / radius, ring_radius * math.sin(angle) / radius))
    faces: list[tuple[int, int, int]] = []
    for index in range(8):
        next_index = (index + 1) % 8
        faces.append((0, 2 + next_index, 2 + index))
    for index in range(8):
        next_index = (index + 1) % 8
        first, second, third, fourth = 2 + index, 2 + next_index, 10 + index, 10 + next_index
        faces.extend(((first, fourth, third), (first, second, fourth)))
    for index in range(8):
        next_index = (index + 1) % 8
        faces.append((1, 10 + index, 10 + next_index))
    neutral_data = gallery._ply_bytes(vertices, normals, faces)
    with tempfile.TemporaryDirectory(prefix="structural-publication-fixture-ply-") as temporary:
        neutral_path = Path(temporary) / "neutral.ply"
        neutral_path.write_bytes(neutral_data)
        neutral = gallery.bridge._parse_ply(neutral_path, expected_sha256=hashlib.sha256(neutral_data).hexdigest())
    vertices = [tuple(vertex) for vertex in neutral["vertices"]]
    normals = [tuple(normal) for normal in neutral["normals"]]

    joint_bone_ids = {key: f"bone-joint-{index:02d}" for index, key in enumerate(source["joints"])}
    joint_by_distal = {
        gallery._address_key(joint["distal"], "fixture distal"): joint_bone_ids[key]
        for key, joint in source["joints"].items()
    }
    bones: list[dict[str, object]] = [{
        "id": "bone-source-part-root",
        "kind": "synthetic-source-part-root",
        "parent": None,
        "a": list(sorted(vertices, key=lambda item: (-sum(value * value for value in item), item))[0]),
        "b": list(source["world_points"][root_part]),
        "source_part": root_address,
        "owned_part": root_address,
        "source_parts": [root_address],
        "surface_anchor_rule": "centroid of the complete neutral surface, with lexicographically stable farthest-vertex fallback",
    }]
    for joint_key, joint in source["joints"].items():
        proximal_key = gallery._address_key(joint["proximal"], "fixture proximal")
        distal_key = gallery._address_key(joint["distal"], "fixture distal")
        bones.append({
            "id": joint_bone_ids[joint_key],
            "kind": "derived-joint",
            "parent": "bone-source-part-root" if proximal_key == root_part else joint_by_distal[proximal_key],
            "a": list(source["world_points"][proximal_key]),
            "b": list(source["world_points"][distal_key]),
            "joint": joint["address"],
            "proximal": joint["proximal"],
            "distal": joint["distal"],
            "owned_part": joint["distal"],
            "source_parts": [joint["proximal"], joint["distal"]],
        })
    for bone in bones:
        bone["length"] = round(math.dist(bone["a"], bone["b"]), 12)

    remaining = set(range(len(vertices)))
    assignments: list[tuple[str, int]] = []
    for bone in sorted(bones, key=lambda item: item["id"]):
        vertex_index = max(
            remaining,
            key=lambda index: gallery.bridge._distance_to_segment(tuple(vertices[index]), tuple(bone["a"]), tuple(bone["b"])),
        )
        remaining.remove(vertex_index)
        assignments.append((bone["id"], vertex_index))
    influences: list[list[dict[str, object]]] = [[] for _ in vertices]
    proxies: list[dict[str, object]] = []
    by_bone = {bone["id"]: bone for bone in bones}
    for bone_id, vertex_index in assignments:
        influences[vertex_index] = [{"bone_id": bone_id, "weight": 1.0}]
        bone = by_bone[bone_id]
        proxies.append({
            "bone_id": bone_id,
            "a": bone["a"],
            "b": bone["b"],
            "radius": gallery.bridge._distance_to_segment(tuple(vertices[vertex_index]), tuple(bone["a"]), tuple(bone["b"])),
            "kind": "capsule",
            "owned_part": bone.get("owned_part", bone.get("source_part")),
            "partition_rule": "nearest eligible weighted bone, then ascending derived bone id",
            "partition_vertex_count": 1,
            "radius_rule": "maximum point-to-segment distance over the bone's complete primary-influence partition",
        })
    candidate = {
        "hierarchy": {
            "bones": bones,
            "joint_address_to_bone": [
                {"bone_id": joint_bone_ids[key], "joint": joint["address"]}
                for key, joint in source["joints"].items()
            ],
        },
        "weights": {"vertex_count": len(vertices), "influences": influences},
        "proxies": proxies,
    }
    gallery._validate_candidate_geometry(profile_id, candidate, neutral, source["parts"], source["joints"])
    prepared = gallery._prepare_profile({"id": profile_id, "candidate": candidate, "neutral": neutral}, pose)
    skeleton = {
        "convention": {"matrices": "row-major storage with column-vector multiplication", "vectors": "column"},
        "format": publisher.GALLERY_FORMAT,
        "profile_id": profile_id,
        "neutral": {
            "bones": prepared["neutral_skeleton"],
            "bind_world": {key: gallery._round_matrix(value) for key, value in sorted(prepared["world_bind"].items())},
            "bind_parent_local": {key: gallery._round_matrix(value) for key, value in sorted(prepared["local_bind"].items())},
        },
        "posed": {
            "bones": prepared["posed_skeleton"],
            "posed_world": {key: gallery._round_matrix(value) for key, value in sorted(prepared["posed_world"].items())},
            "skin": {key: gallery._round_matrix(value) for key, value in sorted(prepared["skin"].items())},
        },
    }
    weights = {
        "format": publisher.GALLERY_FORMAT,
        "profile_id": profile_id,
        "vertex_count": len(vertices),
        "influences": influences,
        "dominant": [{"bone_id": bone_id, "max_weight": weight} for bone_id, weight in prepared["dominant"]],
    }
    neutral_proxy_value = {"format": publisher.GALLERY_FORMAT, "profile_id": profile_id, "state": "neutral", "radius_transform": "unchanged", "proxies": prepared["neutral_proxies"]}
    posed_proxy_value = {"format": publisher.GALLERY_FORMAT, "profile_id": profile_id, "state": "posed", "radius_transform": "unchanged", "proxies": prepared["posed_proxies"]}
    metrics = {
        "format": publisher.GALLERY_FORMAT,
        "profile_id": profile_id,
        "neutral_vertex_count": len(neutral["vertices"]),
        "posed_vertex_count": len(prepared["posed_vertices"]),
        "face_count": len(neutral["faces"]),
        "bone_count": len(prepared["neutral_skeleton"]),
        "proxy_count": len(prepared["neutral_proxies"]),
        "neutral_bounds": {"min": list(gallery._bounds(neutral["vertices"])[0]), "max": list(gallery._bounds(neutral["vertices"])[1])},
        "posed_bounds": {"min": list(gallery._bounds(prepared["posed_vertices"])[0]), "max": list(gallery._bounds(prepared["posed_vertices"])[1])},
        "pose_rule_count": len(prepared["pose_rules"]),
        "source_joint_frame_policy": "identity-only-validated-from-hash-bound-structure",
        "gallery_global_world_bound": None,
    }
    artifacts = {
        "neutral.ply": neutral_data,
        "posed.ply": gallery._ply_bytes(prepared["posed_vertices"], prepared["posed_normals"], neutral["faces"]),
        "skeleton.json": publisher.canonical_json(skeleton).encode(),
        "weights.json": publisher.canonical_json(weights).encode(),
        "proxies-neutral.json": publisher.canonical_json(neutral_proxy_value).encode(),
        "proxies-posed.json": publisher.canonical_json(posed_proxy_value).encode(),
        "metrics.json": publisher.canonical_json(metrics).encode(),
    }
    return {"prepared": prepared, "artifacts": artifacts, "metrics": metrics}


def png_bytes(
    rgb: tuple[int, int, int],
    *,
    filter_byte: int = 0,
    idat_suffix: bytes = b"",
    extra_critical_chunk: tuple[bytes, bytes] | None = None,
) -> bytes:
    scanline = bytes([filter_byte]) + bytes(rgb) * 1800
    raw = scanline * 2500

    def chunk(kind: bytes, payload: bytes) -> bytes:
        return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", zlib.crc32(kind + payload) & 0xFFFFFFFF)

    chunks = [chunk(b"IHDR", struct.pack(">IIBBBBB", 1800, 2500, 8, 2, 0, 0, 0))]
    if extra_critical_chunk is not None:
        chunks.append(chunk(*extra_critical_chunk))
    chunks.extend((chunk(b"IDAT", zlib.compress(raw, 9) + idat_suffix), chunk(b"IEND", b"")))
    return b"\x89PNG\r\n\x1a\n" + b"".join(chunks)


def artifact(data: bytes) -> dict[str, object]:
    return {"sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}


class StructuralEmbodimentPublicationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temp = tempfile.TemporaryDirectory(prefix="structural-publication-tests-")
        cls.base = Path(cls.temp.name) / "gallery"
        cls.base.mkdir()
        cls._write_gallery(cls.base)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temp.cleanup()

    @classmethod
    def _write_gallery(cls, root: Path) -> None:
        inventory: list[dict[str, object]] = []
        profiles: list[dict[str, object]] = []
        candidate_path = HERE.parent.parent / "experiments" / "current-form-surface-preview" / publisher.CANDIDATE_FILE
        candidate_data = candidate_path.read_bytes()
        candidate_value = json.loads(candidate_data)
        expected_source_data = publisher._expected_source_documents(candidate_value, candidate_data)
        (root / publisher.CANDIDATE_FILE).write_bytes(candidate_data)
        inventory.append({"path": publisher.CANDIDATE_FILE, **artifact(candidate_data)})

        sources_dir = root / publisher.SOURCES_DIR
        sources_dir.mkdir()
        source_records: list[dict[str, object]] = []
        source_data_by_profile: dict[str, bytes] = {}
        for profile_id in publisher.PROFILE_IDS:
            source_data = expected_source_data[profile_id]
            source_value = json.loads(source_data)
            source_data_by_profile[profile_id] = source_data
            source_records.append({
                "bytes": len(source_data),
                "document": f"stylized_digitigrade_biped_authored_form__structural_profile__{profile_id}",
                "file": f"{profile_id}.json",
                "id": profile_id,
                "sha256": hashlib.sha256(source_data).hexdigest(),
                "tail_signature": list(publisher.profile_source_generator._tail_signature(source_value)),
            })
            (sources_dir / f"{profile_id}.json").write_bytes(source_data)
            inventory.append({"path": f"{publisher.SOURCES_DIR}/{profile_id}.json", **artifact(source_data)})
        source_manifest_value = {
            "candidate_format": "creature-kernel.disposable-structural-profile-candidates.v1",
            "format": publisher.SOURCE_MANIFEST_FORMAT,
            "profiles": source_records,
            "source": {
                "base_document": "stylized_digitigrade_biped_authored_form",
                "base_namespace": "main",
                "candidate_sha256": publisher.FROZEN_CANDIDATE_TABLE_SHA256,
                "source_sha256": publisher.FROZEN_BASE_SOURCE_SHA256,
            },
        }
        source_manifest_data = json.dumps(source_manifest_value, sort_keys=True, separators=(",", ":")).encode() + b"\n"
        (sources_dir / publisher.SOURCE_MANIFEST_FILE).write_bytes(source_manifest_data)
        inventory.append({"path": f"{publisher.SOURCES_DIR}/{publisher.SOURCE_MANIFEST_FILE}", **artifact(source_manifest_data)})
        pose_path = HERE.parent.parent / "experiments" / "current-form-surface-preview" / publisher.POSE_FILE
        pose_data = pose_path.read_bytes()
        pose, _ = publisher.gallery_generator._load_pose_with_bytes(pose_path)
        profile_values = {
            profile_id: semantic_fixture_profile(profile_id, expected_source_data[profile_id], pose)
            for profile_id in publisher.PROFILE_IDS
        }
        lower, upper = publisher.gallery_generator._bounds(
            publisher.gallery_generator._all_bound_points([profile["prepared"] for profile in profile_values.values()])
        )
        global_world_bound = {"min": list(lower), "max": list(upper)}
        for index, profile_id in enumerate(publisher.PROFILE_IDS):
            profile_dir = root / profile_id
            profile_dir.mkdir()
            per_profile: list[dict[str, object]] = []
            profile_value = profile_values[profile_id]
            metrics = dict(profile_value["metrics"])
            metrics["gallery_global_world_bound"] = global_world_bound
            profile_value["artifacts"]["metrics.json"] = publisher.canonical_json(metrics).encode()
            for name in publisher.PROFILE_ARTIFACT_NAMES:
                data = (
                    publisher.gallery_generator._render_gallery(
                        {**profile_value["prepared"], "label": publisher.PROFILE_LABELS[index]},
                        (lower, upper),
                    )
                    if name == publisher.GALLERY_FILE
                    else profile_value["artifacts"][name]
                )
                path = profile_dir / name
                path.write_bytes(data)
                entry = {"path": f"{profile_id}/{name}", **artifact(data)}
                per_profile.append(entry)
                inventory.append(entry)
            profiles.append({
                "id": profile_id,
                "label": publisher.PROFILE_LABELS[index],
                "bridge_manifest_sha256": "1" * 64,
                "bridge_json_sha256": "2" * 64,
                "neutral_source_sha256": "3" * 64,
                "neutral_source_bytes": 10,
                "structure_source_sha256": "4" * 64,
                "structure_source_bytes": 11,
                "generated_source_path": f"{publisher.SOURCES_DIR}/{profile_id}.json",
                "generated_source_sha256": hashlib.sha256(source_data_by_profile[profile_id]).hexdigest(),
                "generated_source_bytes": len(source_data_by_profile[profile_id]),
                "candidate_profile_sha256": publisher.PROFILE_SHA256[profile_id],
                "source": {"document": f"stylized_digitigrade_biped_authored_form__structural_profile__{profile_id}", "namespace": "main", "candidate_sha256": "5" * 64, "request_sha256": "6" * 64},
                "gallery": {"path": f"{profile_id}/{publisher.GALLERY_FILE}", "global_world_bound": global_world_bound},
                "artifacts": per_profile,
                "metrics": metrics,
            })
        (root / publisher.POSE_FILE).write_bytes(pose_data)
        inventory.append({"path": publisher.POSE_FILE, **artifact(pose_data)})
        inventory.sort(key=lambda item: item["path"])
        root_manifest = {
            "format": publisher.MANIFEST_FORMAT,
            "status": "success",
            "gallery_format": publisher.GALLERY_FORMAT,
            "pose_format": publisher.POSE_FORMAT,
            "pose_sha256": hashlib.sha256(pose_data).hexdigest(),
            "pose_id": publisher.POSE_ID,
            "candidate_table": {
                "kind": "candidate-table",
                "path": publisher.CANDIDATE_FILE,
                "sha256": publisher.FROZEN_CANDIDATE_TABLE_SHA256,
                "bytes": publisher.FROZEN_CANDIDATE_TABLE_BYTES,
                "profile_sha256": dict(publisher.PROFILE_SHA256),
            },
            "source_manifest": {
                "kind": "generated-source-manifest",
                "path": f"{publisher.SOURCES_DIR}/{publisher.SOURCE_MANIFEST_FILE}",
                "sha256": hashlib.sha256(source_manifest_data).hexdigest(),
                "bytes": len(source_manifest_data),
                "base_source_sha256": publisher.FROZEN_BASE_SOURCE_SHA256,
            },
            "profile_ids": list(publisher.PROFILE_IDS),
            "profiles": profiles,
            "global_world_bound": global_world_bound,
            "canvas": {"width": 1800, "height": 2500, "mode": "RGB", "columns": ["front", "side", "three-quarter"], "rows": ["neutral skin+skeleton", "posed skin+skeleton", "per-vertex dominant-bone hue/max-weight brightness", "neutral skin+proxies", "posed skin+proxies"]},
            "transform_convention": publisher.TRANSFORM_CONVENTION,
            "boundary": "candidate-scoped disposable structural evidence; no muscles, anatomy, IK, contacts, runtime, engine, or VR",
            "lineage": {"source": "frozen candidate table, generated source manifest/documents, hash-bound bridge manifests, bridge JSON, neutral PLYs, and per-profile identity-frame structures", "build": "shared deterministic structural embodiment gallery v1", "scenario": {"id": publisher.POSE_ID, "surface_variant_id": publisher.NEUTRAL_VARIANT_ID, "pose_id": publisher.POSE_ID}},
            "artifacts": inventory,
        }
        (root / publisher.MANIFEST_FILE).write_text(json.dumps(root_manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")

    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="structural-publication-case-")
        self.directory = Path(self.temp.name)
        self.gallery = self.directory / "gallery"
        shutil.copytree(self.base, self.gallery)
        self.reviews = self.directory / "reviews"
        self.reviews.mkdir()

    def tearDown(self) -> None:
        self.temp.cleanup()

    def publish(self, review_id: str = "structural-review") -> Path:
        result = publisher.publish_structural_embodiment(self.reviews, self.gallery, review_id=review_id)
        return Path(result["session"])

    def reset_case(self) -> None:
        self.tearDown()
        self.setUp()

    def manifest(self) -> dict[str, object]:
        path = self.gallery / publisher.MANIFEST_FILE
        return json.loads(path.read_text(encoding="utf-8"))

    def write_manifest(self, value: dict[str, object]) -> None:
        (self.gallery / publisher.MANIFEST_FILE).write_text(json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")

    def refresh_source_bindings(self) -> None:
        source_manifest_path = self.gallery / publisher.SOURCES_DIR / publisher.SOURCE_MANIFEST_FILE
        source_manifest = json.loads(source_manifest_path.read_text(encoding="utf-8"))
        for record in source_manifest["profiles"]:
            source_path = self.gallery / publisher.SOURCES_DIR / record["file"]
            record.update(artifact(source_path.read_bytes()))
        source_manifest_data = json.dumps(source_manifest, sort_keys=True, separators=(",", ":")).encode() + b"\n"
        source_manifest_path.write_bytes(source_manifest_data)

        value = self.manifest()
        value["source_manifest"].update(artifact(source_manifest_data))
        for entry in value["artifacts"]:
            if entry["path"] == f"{publisher.SOURCES_DIR}/{publisher.SOURCE_MANIFEST_FILE}":
                entry.update(artifact(source_manifest_data))
        for profile in value["profiles"]:
            source_path = self.gallery / profile["generated_source_path"]
            source_entry = artifact(source_path.read_bytes())
            profile["generated_source_sha256"] = source_entry["sha256"]
            profile["generated_source_bytes"] = source_entry["bytes"]
            for entry in value["artifacts"]:
                if entry["path"] == profile["generated_source_path"]:
                    entry.update(source_entry)
        self.write_manifest(value)

    def replace_png(self, profile_index: int, data: bytes) -> None:
        profile_id = publisher.PROFILE_IDS[profile_index]
        path = self.gallery / profile_id / publisher.GALLERY_FILE
        path.write_bytes(data)
        entry = artifact(data)
        value = self.manifest()
        for item in value["artifacts"]:
            if item["path"] == f"{profile_id}/{publisher.GALLERY_FILE}":
                item.update(entry)
        for item in value["profiles"][profile_index]["artifacts"]:
            if item["path"] == f"{profile_id}/{publisher.GALLERY_FILE}":
                item.update(entry)
        self.write_manifest(value)

    def replace_semantic_artifact(self, profile_index: int, name: str, data: bytes) -> None:
        value = self.manifest()
        if name == publisher.POSE_FILE:
            path = self.gallery / name
            path.write_bytes(data)
            value["pose_sha256"] = hashlib.sha256(data).hexdigest()
            for item in value["artifacts"]:
                if item["path"] == name:
                    item.update(artifact(data))
        else:
            profile_id = publisher.PROFILE_IDS[profile_index]
            path = self.gallery / profile_id / name
            path.write_bytes(data)
            relative = f"{profile_id}/{name}"
            for item in value["artifacts"]:
                if item["path"] == relative:
                    item.update(artifact(data))
            for item in value["profiles"][profile_index]["artifacts"]:
                if item["path"] == relative:
                    item.update(artifact(data))
            if name == "metrics.json":
                value["profiles"][profile_index]["metrics"] = json.loads(data)
        self.write_manifest(value)

    def test_success_publishes_one_group_and_only_four_pngs(self) -> None:
        session = self.publish()
        review = json.loads((session / "review.json").read_text(encoding="utf-8"))
        self.assertEqual(review["title"], publisher.TITLE)
        self.assertEqual(review["kind"], "image")
        self.assertEqual(len(review["groups"]), 1)
        self.assertEqual(len(list((session / "assets").iterdir())), 4)
        self.assertEqual({p.name for p in (session / "assets").iterdir()}, {f"{p}.png" for p in publisher.PROFILE_IDS})

    def test_order_and_labels_are_frozen(self) -> None:
        session = self.publish()
        review = json.loads((session / "review.json").read_text(encoding="utf-8"))
        items = review["groups"][0]["items"]
        self.assertEqual([item["id"] for item in items], list(publisher.PROFILE_IDS))
        self.assertEqual([item["title"] for item in items], list(publisher.PROFILE_LABELS))
        self.assertEqual(review["groups"][0]["selection_mode"], "none")

    def test_source_bound_inventory_tree_and_canvas_contract(self) -> None:
        value = self.manifest()
        self.assertEqual(len(value["artifacts"]), publisher.INVENTORY_ARTIFACT_COUNT)
        self.assertEqual({item["path"] for item in value["artifacts"]}, set(publisher.ROOT_ARTIFACTS))
        self.assertEqual(set(path.relative_to(self.gallery).as_posix() for path in self.gallery.rglob("*") if path.is_file()), publisher.EXPECTED_FILES)
        self.assertEqual(value["canvas"]["rows"][2], "per-vertex dominant-bone hue/max-weight brightness")

        candidate = value["candidate_table"]
        candidate_entry = next(item for item in value["artifacts"] if item["path"] == publisher.CANDIDATE_FILE)
        self.assertEqual(candidate_entry, {key: candidate[key] for key in ("path", "sha256", "bytes")})
        source_manifest = value["source_manifest"]
        source_manifest_entry = next(item for item in value["artifacts"] if item["path"] == source_manifest["path"])
        self.assertEqual(source_manifest["base_source_sha256"], publisher.FROZEN_BASE_SOURCE_SHA256)
        self.assertEqual(source_manifest_entry, {key: source_manifest[key] for key in ("path", "sha256", "bytes")})
        for profile in value["profiles"]:
            source_entry = next(item for item in value["artifacts"] if item["path"] == profile["generated_source_path"])
            self.assertEqual(profile["generated_source_path"], f"{publisher.SOURCES_DIR}/{profile['id']}.json")
            self.assertEqual(source_entry, {key: profile[f"generated_source_{key}"] for key in ("path", "sha256", "bytes")})

    def test_source_bound_metadata_and_inventory_mismatches_fail_closed(self) -> None:
        value = self.manifest()
        value["source_manifest"]["base_source_sha256"] = "0" * 64
        self.write_manifest(value)
        with self.assertRaises(publisher.StructuralEmbodimentPublishError):
            self.publish("wrong-base-source")

        self.reset_case()
        value = self.manifest()
        candidate_entry = next(item for item in value["artifacts"] if item["path"] == publisher.CANDIDATE_FILE)
        candidate_entry["bytes"] += 1
        self.write_manifest(value)
        with self.assertRaises(publisher.StructuralEmbodimentPublishError):
            self.publish("wrong-candidate-inventory")

        self.reset_case()
        value = self.manifest()
        value["profiles"][0]["generated_source_sha256"] = "0" * 64
        self.write_manifest(value)
        with self.assertRaises(publisher.StructuralEmbodimentPublishError):
            self.publish("wrong-generated-source")

    def test_semantically_forged_rehashed_artifacts_fail_closed(self) -> None:
        pose = json.loads((self.gallery / publisher.POSE_FILE).read_text(encoding="utf-8"))
        pose["rules"][0]["angle_degrees"] = 1.0
        self.replace_semantic_artifact(0, publisher.POSE_FILE, publisher.canonical_json(pose).encode())
        with self.assertRaises(publisher.StructuralEmbodimentPublishError):
            self.publish("forged-pose")

        self.reset_case()
        skeleton_path = self.gallery / publisher.PROFILE_IDS[0] / "skeleton.json"
        skeleton = json.loads(skeleton_path.read_text(encoding="utf-8"))
        skeleton["neutral"]["bones"][0]["b"][0] += 100.0
        self.replace_semantic_artifact(0, "skeleton.json", publisher.canonical_json(skeleton).encode())
        with self.assertRaises(publisher.StructuralEmbodimentPublishError):
            self.publish("forged-skeleton-root")

        self.reset_case()
        weights_path = self.gallery / publisher.PROFILE_IDS[0] / "weights.json"
        weights = json.loads(weights_path.read_text(encoding="utf-8"))
        weights["influences"][0][0]["weight"] = 0.5
        self.replace_semantic_artifact(0, "weights.json", publisher.canonical_json(weights).encode())
        with self.assertRaises(publisher.StructuralEmbodimentPublishError):
            self.publish("forged-weights")

        self.reset_case()
        posed_path = self.gallery / publisher.PROFILE_IDS[0] / "posed.ply"
        posed = publisher._parse_ply_bytes(posed_path.read_bytes(), "fixture posed PLY")
        translated = [tuple(vertex) for vertex in posed["vertices"]]
        translated[0] = (translated[0][0] + 0.25, translated[0][1], translated[0][2])
        forged_posed = publisher.gallery_generator._ply_bytes(translated, posed["normals"], posed["faces"])
        self.replace_semantic_artifact(0, "posed.ply", forged_posed)
        with self.assertRaises(publisher.StructuralEmbodimentPublishError):
            self.publish("forged-posed-surface")

        self.reset_case()
        proxy_path = self.gallery / publisher.PROFILE_IDS[0] / "proxies-neutral.json"
        proxies = json.loads(proxy_path.read_text(encoding="utf-8"))
        proxies["proxies"][0]["radius"] *= 2.0
        self.replace_semantic_artifact(0, "proxies-neutral.json", publisher.canonical_json(proxies).encode())
        with self.assertRaises(publisher.StructuralEmbodimentPublishError):
            self.publish("forged-proxy")

        self.reset_case()
        metrics_path = self.gallery / publisher.PROFILE_IDS[0] / "metrics.json"
        metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
        metrics["neutral_vertex_count"] += 1
        self.replace_semantic_artifact(0, "metrics.json", publisher.canonical_json(metrics).encode())
        with self.assertRaises(publisher.StructuralEmbodimentPublishError):
            self.publish("forged-metrics")

        self.reset_case()
        self.replace_png(0, png_bytes((220, 80, 80)))
        with self.assertRaises(publisher.StructuralEmbodimentPublishError):
            self.publish("forged-gallery-render")

    def test_semantically_forged_rehashed_sources_fail_closed(self) -> None:
        source_manifest_path = self.gallery / publisher.SOURCES_DIR / publisher.SOURCE_MANIFEST_FILE
        source_manifest = json.loads(source_manifest_path.read_text(encoding="utf-8"))
        source_manifest["source"]["candidate_sha256"] = "0" * 64
        source_manifest_path.write_text(json.dumps(source_manifest, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
        self.refresh_source_bindings()
        with self.assertRaises(publisher.StructuralEmbodimentPublishError):
            self.publish("forged-source-manifest")

        self.reset_case()
        profile_id = publisher.PROFILE_IDS[0]
        source_path = self.gallery / publisher.SOURCES_DIR / f"{profile_id}.json"
        source_document = json.loads(source_path.read_text(encoding="utf-8"))
        source_document["source"]["document"] = "forged_structural_profile_document"
        source_path.write_text(json.dumps(source_document, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
        source_manifest_path = self.gallery / publisher.SOURCES_DIR / publisher.SOURCE_MANIFEST_FILE
        source_manifest = json.loads(source_manifest_path.read_text(encoding="utf-8"))
        source_manifest["profiles"][0]["document"] = "forged_structural_profile_document"
        source_manifest_path.write_text(json.dumps(source_manifest, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
        self.refresh_source_bindings()
        with self.assertRaises(publisher.StructuralEmbodimentPublishError):
            self.publish("forged-source-document")

        self.reset_case()
        profile_id = publisher.PROFILE_IDS[0]
        source_path = self.gallery / publisher.SOURCES_DIR / f"{profile_id}.json"
        source_document = json.loads(source_path.read_text(encoding="utf-8"))
        source_document["body"]["dimensions"][0]["value"] += 1
        source_path.write_text(json.dumps(source_document, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
        self.refresh_source_bindings()
        with self.assertRaisesRegex(publisher.StructuralEmbodimentPublishError, "not the exact output"):
            self.publish("forged-source-dimension")

        self.reset_case()
        value = self.manifest()
        value["profiles"][0]["source"]["document"] = "forged_structural_profile_document"
        self.write_manifest(value)
        with self.assertRaises(publisher.StructuralEmbodimentPublishError):
            self.publish("forged-profile-source-document")

        self.reset_case()
        source_manifest_path = self.gallery / publisher.SOURCES_DIR / publisher.SOURCE_MANIFEST_FILE
        source_manifest = json.loads(source_manifest_path.read_text(encoding="utf-8"))
        source_manifest["profiles"][0]["tail_signature"] = [1, 2]
        source_manifest_path.write_text(json.dumps(source_manifest, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
        self.refresh_source_bindings()
        with self.assertRaises(publisher.StructuralEmbodimentPublishError):
            self.publish("invalid-tail-signature")

    def test_manifest_order_labels_and_path_traversal_are_rejected(self) -> None:
        value = self.manifest()
        value["profile_ids"] = list(reversed(value["profile_ids"]))
        self.write_manifest(value)
        with self.assertRaises(publisher.StructuralEmbodimentPublishError):
            self.publish("wrong-order")

        self.reset_case()
        value = self.manifest()
        value["profiles"][0]["label"] = "unfrozen label"
        self.write_manifest(value)
        with self.assertRaises(publisher.StructuralEmbodimentPublishError):
            self.publish("wrong-label")

        self.reset_case()
        value = self.manifest()
        value["artifacts"][0]["path"] = "../outside"
        self.write_manifest(value)
        with self.assertRaises(publisher.StructuralEmbodimentPublishError):
            self.publish("traversal")

    def test_lineage_is_carried_in_allowed_metadata(self) -> None:
        session = self.publish()
        review = json.loads((session / "review.json").read_text(encoding="utf-8"))
        context = review["subject_context"]
        self.assertEqual(context["provenance"]["scenario"]["id"], publisher.POSE_ID)
        self.assertEqual(context["descriptor_snapshot"]["profile_ids"], list(publisher.PROFILE_IDS))
        metadata = review["groups"][0]["items"][0]["metadata"]
        self.assertEqual(metadata["profile_label"], publisher.PROFILE_LABELS[0])
        self.assertEqual(
            metadata["generator_reported_upstream_lineage"]["source"]["request_sha256"],
            "6" * 64,
        )
        self.assertNotIn("source", metadata)

    def test_pngs_are_exact_canvas_and_distinct(self) -> None:
        session = self.publish()
        review = json.loads((session / "review.json").read_text(encoding="utf-8"))
        hashes = [item["metadata"]["artifact"]["sha256"] for item in review["groups"][0]["items"]]
        self.assertEqual(len(set(hashes)), 4)
        self.assertTrue(all(item["metadata"]["artifact"]["width"] == 1800 for item in review["groups"][0]["items"]))
        self.assertTrue(all(item["metadata"]["artifact"]["mode"] == "RGB" for item in review["groups"][0]["items"]))

    def test_tamper_missing_extra_and_symlink_fail_without_session(self) -> None:
        (self.gallery / publisher.PROFILE_IDS[0] / "weights.json").write_bytes(b"tampered")
        with self.assertRaises(publisher.StructuralEmbodimentPublishError):
            self.publish()
        self.assertEqual(list(self.reviews.iterdir()), [])

        self.reset_case()
        (self.gallery / publisher.POSE_FILE).unlink()
        with self.assertRaises(publisher.StructuralEmbodimentPublishError):
            self.publish("missing")
        self.assertFalse((self.reviews / "missing").exists())

        self.reset_case()
        (self.gallery / "extra.bin").write_bytes(b"extra")
        with self.assertRaises(publisher.StructuralEmbodimentPublishError):
            self.publish("extra")
        self.assertFalse((self.reviews / "extra").exists())

        self.reset_case()
        (self.gallery / "link.bin").symlink_to(self.gallery / publisher.POSE_FILE)
        with self.assertRaises(publisher.StructuralEmbodimentPublishError):
            self.publish("symlink")
        self.assertFalse((self.reviews / "symlink").exists())

    def test_duplicate_image_hash_is_rejected(self) -> None:
        source = self.gallery / publisher.PROFILE_IDS[0] / publisher.GALLERY_FILE
        target = self.gallery / publisher.PROFILE_IDS[1] / publisher.GALLERY_FILE
        target.write_bytes(source.read_bytes())
        value = self.manifest()
        for entry in value["artifacts"]:
            if entry["path"] == f"{publisher.PROFILE_IDS[1]}/{publisher.GALLERY_FILE}":
                entry.update(artifact(source.read_bytes()))
        for entry in value["profiles"][1]["artifacts"]:
            if entry["path"].endswith(publisher.GALLERY_FILE):
                entry.update(artifact(source.read_bytes()))
        self.write_manifest(value)
        with self.assertRaises(publisher.StructuralEmbodimentPublishError):
            self.publish()

    def test_temporary_provenance_and_invalid_png_are_rejected(self) -> None:
        value = self.manifest()
        value["lineage"]["source"] = "/tmp/structural-bridge"
        self.write_manifest(value)
        with self.assertRaises(publisher.StructuralEmbodimentPublishError):
            self.publish("temp-provenance")

        self.reset_case()
        path = self.gallery / publisher.PROFILE_IDS[0] / publisher.GALLERY_FILE
        path.write_bytes(b"not png")
        value = self.manifest()
        for entry in value["artifacts"]:
            if entry["path"] == f"{publisher.PROFILE_IDS[0]}/{publisher.GALLERY_FILE}":
                entry.update(artifact(path.read_bytes()))
        for entry in value["profiles"][0]["artifacts"]:
            if entry["path"].endswith(publisher.GALLERY_FILE):
                entry.update(artifact(path.read_bytes()))
        self.write_manifest(value)
        with self.assertRaises(publisher.StructuralEmbodimentPublishError):
            self.publish("invalid-png")

    def test_invalid_png_filter_byte_is_rejected(self) -> None:
        self.replace_png(0, png_bytes((220, 80, 80), filter_byte=5))
        with self.assertRaises(publisher.StructuralEmbodimentPublishError):
            self.publish("invalid-filter")
        self.assertEqual(list(self.reviews.iterdir()), [])

    def test_unknown_critical_png_chunk_is_rejected(self) -> None:
        self.replace_png(0, png_bytes((220, 80, 80), extra_critical_chunk=(b"ABCD", b"")))
        with self.assertRaises(publisher.StructuralEmbodimentPublishError):
            self.publish("unknown-critical")
        self.assertEqual(list(self.reviews.iterdir()), [])

    def test_trailing_zlib_data_is_rejected(self) -> None:
        self.replace_png(0, png_bytes((220, 80, 80), idat_suffix=b"trailing"))
        with self.assertRaises(publisher.StructuralEmbodimentPublishError):
            self.publish("trailing-zlib")
        self.assertEqual(list(self.reviews.iterdir()), [])

    def test_source_mutation_after_validation_is_rejected_without_session(self) -> None:
        source = self.gallery / publisher.PROFILE_IDS[0] / publisher.GALLERY_FILE
        original_publish_session = publisher.publish_session

        def mutate_before_copy(reviews_root: Path, manifest_path: Path, *, expected_sources: dict[str, dict[str, object]]):
            source.write_bytes(source.read_bytes() + b"mutation")
            return original_publish_session(
                reviews_root,
                manifest_path,
                expected_sources=expected_sources,
            )

        with patch.object(publisher, "publish_session", side_effect=mutate_before_copy):
            with self.assertRaises(publisher.StructuralEmbodimentPublishError):
                self.publish("mutated-source")
        self.assertFalse((self.reviews / "mutated-source").exists())
        self.assertEqual(list(self.reviews.iterdir()), [])

    def test_session_collision_is_atomic_and_leaves_existing_session(self) -> None:
        session = self.publish("collision")
        before = (session / "review.json").read_bytes()
        with self.assertRaises(publisher.StructuralEmbodimentPublishError):
            self.publish("collision")
        self.assertEqual((session / "review.json").read_bytes(), before)
        self.assertEqual(sorted(p.name for p in self.reviews.iterdir()), ["collision"])


if __name__ == "__main__":
    unittest.main()
