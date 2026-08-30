from __future__ import annotations

import base64
import copy
import hashlib
import importlib.util
import io
import json
import lzma
import os
import shutil
import struct
import subprocess
import sys
import tempfile
import textwrap
import unittest
import zlib
from contextlib import redirect_stderr, redirect_stdout
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


import common
publisher = load_module("surface_preview_publisher", "publish_surface_preview.py")


# Keep the normal synthetic successor fixture's identity and topology
# expectations independent from the publisher contract projection. If the
# publisher and source owner drift together, this fixture must still expose it.
INDEPENDENT_SUCCESSOR_FIXTURE = {
    "format": "creature-kernel.disposable-successor-surface-preview.v9",
    "consumer_id": "successor-surface-v1",
    "region_id": "successor-torso-shoulder-head-neck-arm-leg-foot-profile-limb-extremity-tail-hip-root-sweeps-v16",
    "operations": {
        "torso": "rounded-superellipse-axial-profile-sweep-v1",
        "head_neck": "authored-head-neck-branched-route-profile-v1",
        "arm": "authored-arm-profile-route-v1",
        "leg": "authored-leg-profile-route-v1",
        "foot": "authored-foot-profile-route-v1",
        "hand_paw": "symmetric-ellipse",
        "forward_muzzle": "successor-local-forward-muzzle-envelope-v1",
        "hip_root": "derived-pelvis-thigh-socket-profile-v2",
    },
    "hip_root_controls": {
        "boundary_samples": 64,
        "boundary_iterations": 64,
        "boundary_max_parameter": 4.0,
        "socket_fraction": 0.62,
        "cup_remaining_fraction": 0.55,
        "pelvis_support_cap": 1.20,
        "socket_thigh_weight": 0.68,
        "socket_pelvis_weight": 0.32,
        "cup_thigh_weight": 0.82,
        "cup_pelvis_weight": 0.18,
        "tangent_blend_fraction": 0.50,
    },
    "forward_muzzle_geometric_indices": (3, 5, 7),
    "forward_muzzle_radius_donor_indices": (5, 6, 7),
    "head_neck_order": ("vertical-neck-cranium", "forward-muzzle"),
    "head_neck_section_counts": (5, 4),
    "limb_order": (
        "left-upper-arm-route", "left-forearm-route",
        "right-upper-arm-route", "right-forearm-route",
        "left-leg", "right-leg",
    ),
    "limb_station_names": (
        ("upper-arm-start", "upper-arm-midpoint", "elbow"),
        ("elbow", "forearm-midpoint", "forearm-distal"),
        ("upper-arm-start", "upper-arm-midpoint", "elbow"),
        ("elbow", "forearm-midpoint", "forearm-distal"),
        ("thigh-start", "thigh-midpoint", "knee", "shin-midpoint", "hock-endpoint"),
        ("thigh-start", "thigh-midpoint", "knee", "shin-midpoint", "hock-endpoint"),
    ),
    "extremity_order": (
        "left-hand-attachment", "left-hand-paw", "left-foot",
        "right-hand-attachment", "right-hand-paw", "right-foot",
    ),
    "extremity_kinds": (
        "hand-attachment", "hand-paw", "foot-chain",
        "hand-attachment", "hand-paw", "foot-chain",
    ),
    "hand_paw_profile": (
        (-0.55, 0.62, 0.66),
        (-0.15, 1.00, 1.00),
        (0.35, 0.92, 1.05),
        (0.78, 0.55, 0.60),
    ),
    "hand_paw_section_names": (
        "hand-paw-base", "hand-paw-palm", "hand-paw-knuckle", "hand-paw-tip",
    ),
    "foot_section_names": (
        "hock", "metatarsal-midpoint", "pad", "pad-toe-midpoint", "toe",
    ),
    "foot_owner_roles": ("shin", "foot", "foot", "foot", "foot"),
    "tail_order": (
        "tail-root-source", "tail-root-attachment", "tail-root-collar",
        "tail-tip-source", "tail-tip-extension", "tail-tip-cap",
    ),
    "tail_kinds": (
        "source-centerline", "root-attachment", "root-collar-mass",
        "source-centerline", "tip-extension", "tip-cap-mass",
    ),
    "tail_section_names": (
        ("tail-root-source-start", "tail-root-source-end"),
        ("tail-root-attachment-start", "tail-root-attachment-end"),
        ("tail-root-collar-section-0", "tail-root-collar-section-1", "tail-root-collar-section-2"),
        ("tail-tip-source-start", "tail-tip-source-end"),
        ("tail-tip-extension-start", "tail-tip-extension-end"),
        ("tail-tip-cap-section-0", "tail-tip-cap-section-1", "tail-tip-cap-section-2"),
    ),
    "replaced": (
        "torso-cage", "cranium", "muzzle", "head-base-bridge", "tapered-neck", "neck-collar",
        "deltoid-sweep-1", "root-bridge", "hip-transition",
        "upper_arm-pre-joint", "upper_arm-joint", "forearm-proximal", "forearm-distal",
        "thigh-pre-joint", "thigh-joint", "shin-pre-joint", "shin-joint", "elbow", "knee", "hock",
        "paw", "extremity-bridge", "metatarsal", "paw-pad", "toe-box",
        "tail-segment", "tail-root-bridge", "tail-root-collar", "tail-tip-extension", "tail-tip-cap",
    ),
}
INDEPENDENT_SUCCESSOR_FIXTURE["extremity_station_names"] = (
    ("hand-attachment-start", "hand-attachment-end"),
    INDEPENDENT_SUCCESSOR_FIXTURE["hand_paw_section_names"],
    INDEPENDENT_SUCCESSOR_FIXTURE["foot_section_names"],
    ("hand-attachment-start", "hand-attachment-end"),
    INDEPENDENT_SUCCESSOR_FIXTURE["hand_paw_section_names"],
    INDEPENDENT_SUCCESSOR_FIXTURE["foot_section_names"],
)

class SurfacePreviewPublicationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.directory = Path(self.temp.name)
        self.root = self.directory / "reviews"
        self.root.mkdir()
        self.input = self.directory / "body.json"
        self.input.write_text("{}", encoding="utf-8")

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_successor_semantic_sidecar_scales_with_validated_vertex_count(self) -> None:
        address = {
            "namespace": "fixture",
            "anchors": ["root"],
            "kind": "Part",
            "role": "body",
        }
        vertex_count = 10_001
        path = self.directory / "semantic.json"
        path.write_text(
            json.dumps(
                {
                    "format": publisher.SEMANTIC_SIDECAR_FORMAT,
                    "source_format": common.PROVISIONAL_FORM_FORMAT,
                    "variant_id": "neutral-v0",
                    "source_variant_sha256": "1" * 64,
                    "surface_sha256": "2" * 64,
                    "vertex_count": vertex_count,
                    "source_node_labels": [address] * vertex_count,
                    "attribution": "every recipe component resolves to its source descriptor owner; no synthetic node identity is emitted",
                }
            ),
            encoding="utf-8",
        )
        self.assertGreater(path.stat().st_size, publisher.MAX_METRICS_BYTES)
        payload = publisher._validate_successor_semantic_sidecar(
            path,
            variant_id="neutral-v0",
            source_format=common.PROVISIONAL_FORM_FORMAT,
            source_variant_sha256="1" * 64,
            surface_sha256="2" * 64,
            ply_metrics={"vertex_count": vertex_count},
            descriptor_owners=[address],
        )
        self.assertEqual(payload["vertex_count"], vertex_count)

        path.write_text("[]", encoding="utf-8")
        with self.assertRaisesRegex(
            publisher.SurfacePreviewPublishError,
            "must be a JSON object",
        ):
            publisher._validate_successor_semantic_sidecar(
                path,
                variant_id="neutral-v0",
                source_format=common.PROVISIONAL_FORM_FORMAT,
                source_variant_sha256="1" * 64,
                surface_sha256="2" * 64,
                ply_metrics={"vertex_count": vertex_count},
                descriptor_owners=[address],
            )

    @staticmethod
    def _chunk(kind: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(data, zlib.crc32(kind)) & 0xFFFFFFFF)

    @classmethod
    def _png(cls, *, width: int = 1800, height: int = 1500, include_idat: bool = True, invalid_idat: bool = False, unknown_chunk: bool = False) -> bytes:
        ihdr = cls._chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        raw = b"".join(b"\x00" + b"\x00" * (width * 3) for _ in range(height))
        compressed = b"not-a-zlib-stream" if invalid_idat else zlib.compress(raw)
        idat = cls._chunk(b"IDAT", compressed) if include_idat else b""
        extra = cls._chunk(b"ABCD", b"unknown") if unknown_chunk else b""
        return b"\x89PNG\r\n\x1a\n" + ihdr + extra + idat + cls._chunk(b"IEND", b"")

    @staticmethod
    def _tetra_ply(
        *,
        copies: int = 1,
        missing_last_face: bool = False,
        duplicate_face: bool = False,
        inconsistent_orientation: bool = False,
        global_reversal: bool = False,
        zero_normals: bool = False,
        flattened_height: float | None = None,
    ) -> bytes:
        base_vertices = (
            (0.0, 0.0, 0.0, -0.577350269, -0.577350269, -0.577350269),
            (1.0, 0.0, 0.0, 0.707106781, 0.0, 0.707106781),
            (0.0, 1.0, 0.0, 0.0, 1.0, 0.0),
            (0.0, 0.0, 1.0, 0.0, 0.0, 1.0),
        )
        if flattened_height is not None:
            base_vertices = (
                base_vertices[0],
                base_vertices[1],
                base_vertices[2],
                (1.0, 1.0, flattened_height, 0.0, 0.0, 1.0),
            )
        if zero_normals:
            base_vertices = tuple((*vertex[:3], 0.0, 0.0, 0.0) for vertex in base_vertices)
        base_faces = ((0, 2, 1), (0, 1, 3), (0, 3, 2), (1, 2, 3))
        if global_reversal:
            base_faces = tuple(tuple(reversed(face)) for face in base_faces)
        vertices = []
        faces = []
        for copy_index in range(copies):
            offset = 4 * copy_index
            vertices.extend(
                (x + 3.0 * copy_index, y, z, nx, ny, nz)
                for x, y, z, nx, ny, nz in base_vertices
            )
            faces.extend((first + offset, second + offset, third + offset) for first, second, third in base_faces)
        if missing_last_face:
            faces.pop()
        if duplicate_face:
            faces[-1] = tuple(reversed(faces[0]))
        if inconsistent_orientation:
            faces[0] = tuple(reversed(faces[0]))
        lines = [
            "ply",
            "format ascii 1.0",
            f"element vertex {len(vertices)}",
            "property float x",
            "property float y",
            "property float z",
            "property float nx",
            "property float ny",
            "property float nz",
            f"element face {len(faces)}",
            "property list uchar int vertex_indices",
            "end_header",
        ]
        number_format = ".12g" if flattened_height is not None else ".9f"
        lines.extend(" ".join(format(value, number_format) for value in vertex) for vertex in vertices)
        lines.extend(f"3 {first} {second} {third}" for first, second, third in faces)
        return ("\n".join(lines) + "\n").encode("ascii")

    def _producer(self) -> Path:
        path = self.directory / "producer"
        path.write_text("#!/usr/bin/env python3\nprint('{}')\n", encoding="utf-8")
        path.chmod(0o755)
        return path

    def _generator(self, *, mode: str = "success") -> Path:
        path = self.directory / f"generator-{mode}.py"
        png_bytes = self._png()
        if mode == "png-truncated":
            png_bytes = png_bytes[:-1]
        elif mode == "png-crc":
            damaged = bytearray(png_bytes)
            damaged[-1] ^= 1
            png_bytes = bytes(damaged)
        elif mode == "png-no-idat":
            png_bytes = self._png(include_idat=False)
        elif mode == "png-invalid-idat":
            png_bytes = self._png(invalid_idat=True)
        elif mode == "png-unknown-critical":
            png_bytes = self._png(unknown_chunk=True)
        elif mode == "png-small":
            png_bytes = self._png(width=1, height=1)
        path.write_text(textwrap.dedent(f"""
            #!/usr/bin/env python3
            import hashlib, json, math, pathlib, struct, sys, time
            COMPONENT_VISUALIZATION_METRICS = {publisher.EXPECTED_COMPONENT_VISUALIZATION_METRICS!r}
            args = dict(zip(sys.argv[1::2], sys.argv[2::2]))
            out = pathlib.Path(args["--output"])
            if {mode!r} == "failure":
                print("fixture generator failed", file=sys.stderr)
                raise SystemExit(3)
            source_hash = hashlib.sha256(pathlib.Path(args["--input"]).read_bytes()).hexdigest()
            payload = json.loads(pathlib.Path(args["--input"]).read_text(encoding="utf-8"))
            if {mode!r} == "source-mismatch": source_hash = "0" * 64
            if out.exists(): raise RuntimeError("output must not already exist")
            if {mode!r} == "timeout":
                time.sleep(60)
            out.mkdir(parents=True, exist_ok=True)
            variants = []
            ids = {list(common.PROVISIONAL_FORM_VARIANT_IDS)!r}
            owner_specs = [("pelvis", []), ("torso", []), ("neck", []), ("head", []), ("upper_arm", ["left"]), ("forearm", ["left"]), ("hand", ["left"]), ("upper_arm", ["right"]), ("forearm", ["right"]), ("hand", ["right"]), ("thigh", ["left"]), ("shin", ["left"]), ("foot", ["left"]), ("thigh", ["right"]), ("shin", ["right"]), ("foot", ["right"]), ("tail_root", ["tail"]), ("tail_tip", ["tail"])]
            owners = [{{"namespace": "main", "anchors": anchors, "kind": "part", "role": role}} for role, anchors in owner_specs]
            source = {{"document": "fixture", "namespace": "main", "resource_profile_id": "ck.resource.body.r2"}}
            if {mode!r} == "fabricated-provenance": source["document"] = "fabricated"
            bounds = {{"min": [-5.0, -5.0, -5.0], "max": [5.0, 5.0, 5.0]}}
            canvas = {{"width": 1800, "height": 1500, "mode": "RGB"}}
            projections = [{{"name": "front", "basis": [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]], "base": "x-right/y-up/z-depth"}}, {{"name": "side", "basis": [[0.0, 0.0, -1.0], [0.0, 1.0, 0.0], [1.0, 0.0, 0.0]], "base": "-z-right/y-up/x-depth"}}, {{"name": "three-quarter", "basis": [[0.7071067811865475, 0.0, -0.7071067811865475], [0.0, 1.0, 0.0], [0.7071067811865475, 0.0, 0.7071067811865475]], "base": "front-right/y-up/depth"}}]
            layout = {{"panel_order": ["front-control-guide", "side-control-guide", "three-quarter-control-guide", "front-field-components", "side-field-components", "three-quarter-field-components", "front-skin", "side-skin", "three-quarter-skin"], "panels": [{{"id": "front-control-guide", "projection": "front", "content": "control-guide", "box": [12, 72, 592, 532]}}, {{"id": "side-control-guide", "projection": "side", "content": "control-guide", "box": [610, 72, 1190, 532]}}, {{"id": "three-quarter-control-guide", "projection": "three-quarter", "content": "control-guide", "box": [1208, 72, 1788, 532]}}, {{"id": "front-field-components", "projection": "front", "content": "field-components", "box": [12, 546, 592, 1006]}}, {{"id": "side-field-components", "projection": "side", "content": "field-components", "box": [610, 546, 1190, 1006]}}, {{"id": "three-quarter-field-components", "projection": "three-quarter", "content": "field-components", "box": [1208, 546, 1788, 1006]}}, {{"id": "front-skin", "projection": "front", "content": "skin", "box": [12, 1020, 592, 1480]}}, {{"id": "side-skin", "projection": "side", "content": "skin", "box": [610, 1020, 1190, 1480]}}, {{"id": "three-quarter-skin", "projection": "three-quarter", "content": "skin", "box": [1208, 1020, 1788, 1480]}}], "pairing": "control-guide/field-components/skin per projection", "frame": "shared-world-bounds-and-projection-basis"}}
            for variant_id in ids:
                directory = out / variant_id
                directory.mkdir()
                png = directory / "guide-skin-composite.png"
                png.write_bytes({png_bytes!r})
                def mass(control):
                    centers = {{"pelvic-girdle": [0.0, -1.0, 0.0], "waist": [0.0, 0.0, 0.0], "chest-girdle": [0.0, 1.0, 0.0]}}
                    return {{"control": control, "center": centers.get(control, [0.0, 0.0, 0.0]), "radii": [0.5, 0.5, 0.5]}}
                def path(control, kind=None):
                    value = {{"control": control, "points": [[-0.5, 0.0, 0.0], [0.5, 0.0, 0.0]], "thickness": [0.2, 0.2]}}
                    if kind is not None: value["path_kind"] = kind
                    return value
                axial = {{"status": "compatibility-diagnostic-not-rendered", "core": {{"owner": owners[0], "recipe": "pelvic-core", "mass": mass("pelvic-core")}}, "stations": [
                    {{"name": "pelvic-girdle", "owner": owners[0], "recipe": "hips", "mass": mass("pelvic-girdle")}},
                    {{"name": "waist", "owner": owners[1], "recipe": "waist", "mass": mass("waist")}},
                    {{"name": "chest-girdle", "owner": owners[1], "recipe": "chest", "mass": mass("chest-girdle")}},
                ], "transitions": [
                    {{"name": "pelvis-waist", "owner": owners[1], "recipe": "pelvis-waist-bridge", "path": path("pelvis-waist", "tapered-segment")}},
                    {{"name": "waist-chest", "owner": owners[1], "recipe": "waist-chest-bridge", "path": path("waist-chest", "tapered-segment")}},
                ]}}
                producer_variant = next(item for item in payload["variants"] if item["id"] == variant_id)
                source_head = payload["authored_head_neck_profile"]
                projected_head = producer_variant["head_neck_profile"]
                scale = math.sqrt(float(payload["reference_scale"]["squared_length"]))
                head_sections = []
                for source_section, projected_section in zip(source_head["sections"], projected_head["sections"]):
                    landmark = payload["authored_landmarks"][source_section["landmark_index"]]
                    owner = landmark["owner"]
                    descriptor = next(item for item in producer_variant["descriptors"] if item["address"] == owner)
                    center = [(float(descriptor["reference_point"][axis]) + float(landmark["position"][axis])) / scale for axis in range(3)]
                    radii = {{axis: projected_section[f"{{axis}}_radius_permille"] / 1000.0 for axis in ("lateral", "up", "forward")}}
                    lineage = {{}}
                    for axis, dimension_index in source_section["dimension_indices"].items():
                        dimension = payload["authored_dimensions"][dimension_index]
                        factor = projected_section["scaling"][f"{{axis}}_factor_permille"]
                        lineage[axis] = {{"base": dimension["value_permille"], "factor": factor, "scaled": projected_section[f"{{axis}}_radius_permille"], "reference": {{"owner": owner, "role": dimension["role"], "index": dimension_index}}, "provenance": dimension["provenance"], "consumed_section": source_section["name"]}}
                    head_sections.append({{"name": source_section["name"], "section_index": source_section["section_index"], "source_section_index": projected_section["source_section_index"], "frame_index": source_section["frame_index"], "landmark_index": source_section["landmark_index"], "owner": owner, "frame": {{"owner": owner, "role": "form_head_neck_profile_control"}}, "landmark": landmark, "center": center, "radii": radii, "lateral_radius": radii["lateral"], "up_radius": radii["up"], "forward_radius": radii["forward"], "lineage": lineage}})
                head_connections = []
                for connection_spec in source_head["connections"]:
                    from_section = head_sections[connection_spec["from_section_index"]]
                    to_section = head_sections[connection_spec["to_section_index"]]
                    thickness = [min(from_section["radii"].values()), min(to_section["radii"].values())]
                    head_connections.append({{"name": connection_spec["name"], "from_section_index": connection_spec["from_section_index"], "to_section_index": connection_spec["to_section_index"], "route": connection_spec["route"], "from": {{"name": from_section["name"], "owner": from_section["owner"]}}, "to": {{"name": to_section["name"], "owner": to_section["owner"]}}, "path": {{"control": connection_spec["name"], "points": [from_section["center"], to_section["center"]], "thickness": thickness, "path_kind": "tapered-segment"}}}})
                section_by_name = {{section["name"]: section for section in head_sections}}
                head = {{"owners": [owners[3], owners[2]], "profile_format": "creature-kernel.provisional-form-head-neck-profile.v1", "provenance": source_head["provenance"], "sections": head_sections, "connections": head_connections, "masses": [{{"control": "cranium", "center": section_by_name["cranium-mid"]["center"], "radii": list(section_by_name["cranium-mid"]["radii"].values())}}, {{"control": "muzzle", "center": section_by_name["muzzle-mid"]["center"], "radii": list(section_by_name["muzzle-mid"]["radii"].values())}}, {{"control": "neck-collar", "center": section_by_name["neck-collar"]["center"], "radii": list(section_by_name["neck-collar"]["radii"].values())}}], "paths": [{{"control": "head-transition", "points": [section_by_name["neck-upper"]["center"], section_by_name["head-base"]["center"]], "thickness": [min(section_by_name["neck-upper"]["radii"].values()), min(section_by_name["head-base"]["radii"].values())]}}, {{"control": "neck-transition", "points": [section_by_name["neck-collar"]["center"], section_by_name["neck-upper"]["center"]], "thickness": [min(section_by_name["neck-collar"]["radii"].values()), min(section_by_name["neck-upper"]["radii"].values())]}}]}}
                limb_specs = [(owners[4], ("pre-joint", "joint"), ("root",), ("shoulder-girdle",), ("elbow",)), (owners[5], ("proximal", "distal"), (), (), ()), (owners[7], ("pre-joint", "joint"), ("root",), ("shoulder-girdle",), ("elbow",)), (owners[8], ("proximal", "distal"), (), (), ()), (owners[10], ("pre-joint", "joint"), ("root", "hip"), ("hip-girdle",), ("knee",)), (owners[11], ("pre-joint", "joint"), (), (), ("hock",)), (owners[13], ("pre-joint", "joint"), ("root", "hip"), ("hip-girdle",), ("knee",)), (owners[14], ("pre-joint", "joint"), (), (), ("hock",))]
                limbs = []
                for owner, section_names, bridge_names, mass_names, joint_names in limb_specs:
                    section_values = [path(control, "capsule") for control in section_names]
                    side_sign = -1.0 if owner["anchors"] == ["left"] else 1.0
                    joint_center = [1.0, 0.0, 0.0]
                    if owner["role"] == "upper_arm":
                        section_values[0]["points"] = [[side_sign * 1.5, 0.9, 0.0], [side_sign * 1.25, 0.45, 0.0]]
                        section_values[1]["points"] = [[side_sign * 1.25, 0.45, 0.0], [side_sign * 1.0, 0.0, 0.0]]
                        joint_center = [side_sign * 1.0, 0.0, 0.0]
                    elif owner["role"] == "forearm":
                        section_values[0]["points"] = [[side_sign * 1.0, 0.0, 0.0], [side_sign * 1.1, -0.35, 0.0]]
                        section_values[1]["points"] = [[side_sign * 1.1, -0.35, 0.0], [side_sign * 1.2, -0.7, 0.0]]
                    elif owner["role"] == "thigh":
                        section_values[0]["points"] = [[side_sign * 1.0, -1.0, 0.0], [side_sign * 1.0, -1.5, 0.0]]
                        section_values[1]["points"] = [[side_sign * 1.0, -1.5, 0.0], [side_sign * 1.0, -2.0, 0.0]]
                        joint_center = [side_sign * 1.0, -2.0, 0.0]
                    elif owner["role"] == "shin":
                        section_values[0]["points"] = [[side_sign * 1.0, -2.0, 0.0], [side_sign * 1.0, -2.5, 0.5]]
                        section_values[1]["points"] = [[side_sign * 1.0, -2.5, 0.5], [side_sign * 1.0, -3.0, 1.0]]
                        joint_center = [side_sign * 1.0, -3.0, 1.0]
                    anchors = []
                    if owner["role"] == "forearm":
                        anchors = [{{"name": "forearm-distal-boundary", "kind": "parent-surface-anchor", "point": list(section_values[-1]["points"][1]), "boundary_point": list(section_values[-1]["points"][1])}}]
                    elif owner["role"] == "shin":
                        anchors = [{{"name": "hock-endpoint", "kind": "endpoint", "point": list(section_values[-1]["points"][1]), "boundary_point": list(section_values[-1]["points"][1])}}]
                    limb = {{"owner": owner, "profile_controls": [0.2, 0.2, 0.2], "sections": section_values, "bridges": [path(control, "tapered-segment") for control in bridge_names], "masses": [mass(control) for control in mass_names], "joints": [{{"name": name, "owner": owner, "mass": {{**mass(name), "center": joint_center, "radii": [0.14, 0.14, 0.14]}}, "adjacent_profiles": [0.2, (0.5 if name == "hock" else 0.2)]}} for name in joint_names], "anchors": anchors}}
                    limbs.append(limb)
                paws = []
                for owner in [owners[6], owners[9], owners[12], owners[15]]:
                    side_sign = -1.0 if owner["anchors"] == ["left"] else 1.0
                    if owner["role"] == "foot":
                        parent = next(candidate for candidate in owners if candidate["role"] == "shin" and candidate["anchors"] == owner["anchors"])
                        hock_center = [side_sign * 1.0, -3.0, 1.0]
                        pad_center = [side_sign * 1.0, -3.6, 1.5]
                        metatarsal = path("metatarsal", "tapered-segment"); metatarsal["points"] = [hock_center, pad_center]; metatarsal["thickness"] = [0.5, 0.3]
                        pad = mass("paw-pad"); pad["center"] = pad_center; pad["radii"] = [0.4, 0.2, 0.3]
                        toe = mass("toe-box"); toe["center"] = [side_sign * 1.0, -3.6, 1.72]; toe["radii"] = [0.35, 0.2, 0.25]
                        hock = mass("hock-anchor"); hock["center"] = hock_center; hock["radii"] = [0.14, 0.14, 0.14]
                        hock_source = {{"owner": parent, "anchor": "hock-endpoint", "point": hock_center, "boundary_point": hock_center}}
                        paws.append({{"owner": owner, "chain": {{"hock": hock, "metatarsal": metatarsal, "masses": [pad, toe], "contact_height": -3.8, "axes": {{"lateral": [1.0, 0.0, 0.0], "up": [0.0, 1.0, 0.0], "forward": [0.0, 0.0, 1.0]}}, "midpoints": {{"metatarsal": {{"center": [side_sign * 1.0, -3.3, 1.25], "radii": [0.5 * (0.185 + 0.4), 0.5 * (0.165 + 0.2), 0.5 * (0.175 + 0.3)]}}, "pad_toe": {{"center": [side_sign * 1.0, -3.6, 0.5 * (1.5 + 1.72)], "radii": [0.5 * (0.4 + 0.35), 0.5 * (0.2 + 0.2), 0.5 * (0.3 + 0.25)]}}}}}}, "hock_source": hock_source}})
                    else:
                        paw = mass("paw")
                        paw["center"] = [side_sign * 1.3, -0.9, 0.0]
                        attachment = path("attachment", "capsule"); attachment["points"] = [[side_sign * 1.2, -0.7, 0.0], paw["center"]]
                        parent = next(candidate for candidate in owners if candidate["role"] == "forearm" and candidate["anchors"] == owner["anchors"])
                        attachment_source = {{"owner": parent, "anchor": "forearm-distal-boundary", "point": list(attachment["points"][0]), "boundary_point": list(attachment["points"][0])}}
                        paws.append({{"owner": owner, "masses": [paw], "attachment": attachment, "attachment_source": attachment_source}})
                tail_root_centerline = path("segment", "tapered-segment")
                tail_root_attachment = path("root-attachment", "tapered-segment")
                tail_tip_centerline = path("segment", "tapered-segment")
                tail_tip_extension = path("tip-extension", "tapered-segment")
                tail_tip_extension["points"] = [list(tail_tip_centerline["points"][-1]), [1.0, 0.0, 0.0]]
                tail_tip_cap = mass("tip-cap")
                tail_tip_cap["center"] = list(tail_tip_extension["points"][-1])
                tails = [{{"owner": owners[16], "centerline": tail_root_centerline, "sections": [tail_root_attachment], "masses": [mass("root-collar")]}}, {{"owner": owners[17], "centerline": tail_tip_centerline, "sections": [tail_tip_extension], "masses": [tail_tip_cap]}}]
                producer_variant = next(item for item in payload["variants"] if item["id"] == variant_id)
                variant_sections = producer_variant["torso_profile"]["sections"]
                indexed_profile = payload["authored_torso_profile"]["sections"]
                scale = math.sqrt(float(payload["reference_scale"]["squared_length"]))
                cage_sections = []
                for profile_section, index_section in zip(variant_sections, indexed_profile):
                    landmark = payload["authored_landmarks"][index_section["landmark_index"]]
                    owner = landmark["owner"]
                    descriptor = next(item for item in producer_variant["descriptors"] if item["address"] == owner)
                    center = [(float(descriptor["reference_point"][axis]) + float(landmark["position"][axis])) / scale for axis in range(3)]
                    radii = [profile_section[f"{{axis}}_radius_permille"] / 1000.0 for axis in ("lateral", "anterior", "posterior")]
                    lineage = {{}}
                    for axis, dimension_index in index_section["dimension_indices"].items():
                        dimension = payload["authored_dimensions"][dimension_index]
                        factor = profile_section["scaling"][f"{{axis}}_factor_permille"]
                        lineage[axis] = {{"base": dimension["value_permille"], "factor": factor, "scaled": profile_section[f"{{axis}}_radius_permille"], "reference": {{"owner": owner, "role": dimension["role"], "index": dimension_index}}, "provenance": dimension["provenance"], "consumed_section": profile_section["name"]}}
                    cage_sections.append({{"name": profile_section["name"], "section_index": index_section["section_index"], "frame_index": index_section["frame_index"], "landmark_index": index_section["landmark_index"], "owner": owner, "frame": {{"owner": owner, "role": "form_torso_profile_control"}}, "landmark": landmark, "center": center, "lateral_radius": radii[0], "anterior_radius": radii[1], "posterior_radius": radii[2], "depth_radius": 0.5 * (radii[1] + radii[2]), "lateral": lineage["lateral"], "anterior": lineage["anterior"], "posterior": lineage["posterior"], "lineage": lineage}})
                torso_cage = {{"status": "skin-driving torso controls", "profile_format": {publisher.AUTHORED_TORSO_PROFILE_FORMAT!r}, "owners": [owners[0], owners[1]], "axes": {{"lateral": [1.0, 0.0, 0.0], "up": [0.0, 1.0, 0.0], "forward": [0.0, 0.0, 1.0]}}, "orientation": "elliptical cross-section rings lie in the lateral/forward plane and rise along the up axis", "sections": cage_sections, "connections": [{{"from": cage_sections[index]["name"], "to": cage_sections[index + 1]["name"]}} for index in range(6)]}}
                def shoulder_curve(name, owner, points, profile):
                    return {{"name": name, "owner": owner, "points": points, "profile": profile, "consumption": ("skin-driving" if name == "deltoid-sweep" else "guide-only")}}
                shoulder_control_provenance = {{"source": "source-authored", "document": "fixture", "namespace": "main"}}
                shoulder_sides = []
                source_controls = []
                shoulder_factors = {{"neutral-v0": 1000, "broad-soft-v0": 1150, "lean-readable-v0": 800, "depth-forward-v0": 1000}}
                depth_factor = shoulder_factors[variant_id]
                for side_name, side_owner, sign in (("left", owners[4], -1.0), ("right", owners[7], 1.0)):
                    shoulder_frame = {{"owner": side_owner, "role": "form_shoulder_control", "transform": {{"translation": [0.0, 0.0, 0.0], "rotation_xyzw": [0.0, 0.0, 0.0, 1.0]}}, "provenance": shoulder_control_provenance}}
                    axilla = {{"owner": side_owner, "role": "form_axilla", "frame": {{"owner": side_owner, "role": "form_shoulder_control"}}, "position": [sign * 0.1, -0.3, 0.0], "provenance": shoulder_control_provenance}}
                    peak = {{"owner": side_owner, "role": "form_shoulder_peak", "frame": {{"owner": side_owner, "role": "form_shoulder_control"}}, "position": [sign * 0.1, 0.15, 0.0], "provenance": shoulder_control_provenance}}
                    source_controls.append({{"side": side_name, "owner": side_owner, "frame": shoulder_frame, "landmarks": [axilla, peak], "depth_control": {{"owner": side_owner, "role": "form_shoulder_depth_radius", "value_permille": 100, "scaled_value_permille": 100 * depth_factor // 1000, "profile_factor": depth_factor, "provenance": {{"source": "source-authored", "document": "fixture", "namespace": "main"}}, "consumption": "guide-derived shoulder wrap depth; baseline field remains guide-only"}}}})
                    peak_anchor = [sign * 1.1, 1.15, 0.0]
                    axilla_anchor = [sign * 1.1, 0.7, 0.0]
                    vertical_midpoint = 0.5 * (peak_anchor[1] + axilla_anchor[1])
                    depth_radius = 0.1 * depth_factor / 1000.0
                    wrap_anchor = [peak_anchor[0], vertical_midpoint, 0.0]
                    socket = [sign * 1.5, 0.9, 0.0]
                    upper_arm = next(item for item in limbs if item["owner"]["role"] == "upper_arm" and item["owner"]["anchors"] == [side_name])
                    upper_arm_first_end = list(next(item for item in upper_arm["sections"] if item["control"] == "pre-joint")["points"][1])
                    first_quarter = [socket[axis] + 0.25 * (upper_arm_first_end[axis] - socket[axis]) for axis in range(3)]
                    shoulder_sides.append({{"side": side_name, "owner": side_owner, "socket": {{"owner": side_owner, "point": socket}}, "extremum": {{"owner": side_owner, "point": peak_anchor}}, "authored_controls": {{"peak": peak, "axilla": axilla, "frame": shoulder_frame}}, "peak_anchor": peak_anchor, "axilla_anchor": axilla_anchor, "vertical_midpoint": vertical_midpoint, "vertical_radius": 0.5 * (peak_anchor[1] - axilla_anchor[1]), "depth_radius": depth_radius, "depth_control": source_controls[-1]["depth_control"], "span": 1.1, "slope": (peak_anchor[1] - 1.0) / 1.1, "curves": [
                        shoulder_curve("anterior-support", owners[1], [[0.0, 1.0, 0.0], [wrap_anchor[0], wrap_anchor[1], wrap_anchor[2] + depth_radius], peak_anchor, socket], [0.2, 0.2, 0.2, 0.2]),
                        shoulder_curve("posterior-return", owners[1], [[0.0, 1.0, 0.0], [wrap_anchor[0], wrap_anchor[1], wrap_anchor[2] - depth_radius], peak_anchor, socket], [0.2, 0.2, 0.2, 0.2]),
                        shoulder_curve("deltoid-sweep", side_owner, [peak_anchor, socket, first_quarter], [0.2, 0.2, 0.2]),
                    ]}})
                shoulder_frame_controls = {{"status": "private shoulder frame; support curves guide-only; deltoid sweep skin-driving", "owners": {{"torso": owners[1], "neck": owners[2], "left_upper_arm": owners[4], "right_upper_arm": owners[7]}}, "central": {{"owner": owners[1], "anchor": [0.0, 1.0, 0.0], "profile": [0.2, 0.2]}}, "source_controls": source_controls, "sides": shoulder_sides}}
                # Keep the fixture source controls exactly in the producer's canonical order.
                source_controls = sorted(source_controls, key=lambda item: (item["side"] != "left", item["side"]))
                shoulder_frame_controls["source_controls"] = source_controls
                arm_profile_sides = []
                for side_name in ("left", "right"):
                    source_side = next(item for item in payload["authored_arm_profile"]["sides"] if item["side"] == side_name)
                    projected_side = next(item for item in producer_variant["arm_profile"]["sides"] if item["side"] == side_name)
                    arm_sections_json = []
                    for source_section, projected_section in zip(source_side["sections"], projected_side["sections"]):
                        landmark = payload["authored_landmarks"][source_section["landmark_index"]]
                        owner = landmark["owner"]
                        limb = next(item for item in limbs if item["owner"] == owner)
                        path_start = limb["sections"][0]["points"][0]
                        path_end = limb["sections"][-1]["points"][1]
                        local_y = float(landmark["position"][1])
                        center = [float(path_start[axis]) - local_y * (float(path_end[axis]) - float(path_start[axis])) for axis in range(3)]
                        radii = {{axis: projected_section[f"{{axis}}_radius_permille"] / 1000.0 for axis in ("lateral", "up", "forward")}}
                        lineage = {{}}
                        for axis, dimension_index in source_section["dimension_indices"].items():
                            dimension = payload["authored_dimensions"][dimension_index]
                            factor = projected_section["scaling"][f"{{axis}}_factor_permille"]
                            lineage[axis] = {{"base": dimension["value_permille"], "factor": factor, "scaled": projected_section[f"{{axis}}_radius_permille"], "reference": {{"owner": owner, "role": dimension["role"], "index": dimension_index}}, "provenance": dimension["provenance"], "consumed_section": source_section["name"]}}
                        arm_sections_json.append({{"name": source_section["name"], "section_index": source_section["section_index"], "source_section_index": projected_section["source_section_index"], "frame_index": source_section["frame_index"], "landmark_index": source_section["landmark_index"], "owner": owner, "frame": {{"owner": owner, "role": {common.PROVISIONAL_FORM_ARM_PROFILE_FRAME_ROLE!r}}}, "landmark": landmark, "center": center, "radii": radii, "lateral_radius": radii["lateral"], "up_radius": radii["up"], "forward_radius": radii["forward"], "lineage": lineage, "consumption": ("skin-driving; elbow seam owned by upper_arm station" if source_section["name"] == "elbow" else "skin-driving")}})
                    arm_profile_sides.append({{"side": side_name, "sections": arm_sections_json}})
                arm_profile_controls = {{"format": {publisher.AUTHORED_ARM_PROFILE_FORMAT!r}, "status": "skin-driving arm profile; legacy shoulder supports remain guide-only", "provenance": payload["authored_arm_profile"]["provenance"], "axes": {{"lateral": [1.0, 0.0, 0.0], "up": [0.0, 1.0, 0.0], "forward": [0.0, 0.0, 1.0]}}, "sides": arm_profile_sides}}
                for arm_side in arm_profile_sides:
                    elbow = arm_side["sections"][2]
                    upper_arm = next(item for item in limbs if item["owner"] == elbow["owner"])
                    upper_arm["joints"][0]["mass"]["center"] = list(elbow["center"])
                    upper_arm["joints"][0]["mass"]["radii"] = [elbow["radii"][axis] for axis in ("lateral", "up", "forward")]
                leg_profile_sides = []
                for side_name in ("left", "right"):
                    source_side = next(item for item in payload["authored_leg_profile"]["sides"] if item["side"] == side_name)
                    projected_side = next(item for item in producer_variant["leg_profile"]["sides"] if item["side"] == side_name)
                    leg_sections_json = []
                    for source_section, projected_section in zip(source_side["sections"], projected_side["sections"]):
                        landmark = payload["authored_landmarks"][source_section["landmark_index"]]
                        owner = landmark["owner"]
                        limb = next(item for item in limbs if item["owner"] == owner)
                        path_start = limb["sections"][0]["points"][0]
                        path_end = limb["sections"][-1]["points"][1]
                        local_y = float(landmark["position"][1])
                        center = [float(path_start[axis]) - local_y * (float(path_end[axis]) - float(path_start[axis])) for axis in range(3)]
                        radii = dict((axis, projected_section["{{}}_radius_permille".format(axis)] / 1000.0) for axis in ("lateral", "up", "forward"))
                        lineage = dict()
                        for axis, dimension_index in source_section["dimension_indices"].items():
                            dimension = payload["authored_dimensions"][dimension_index]
                            factor = projected_section["scaling"]["{{}}_factor_permille".format(axis)]
                            lineage[axis] = dict(base=dimension["value_permille"], factor=factor, scaled=projected_section["{{}}_radius_permille".format(axis)], reference=dict(owner=owner, role=dimension["role"], index=dimension_index), provenance=dimension["provenance"], consumed_section=source_section["name"])
                        leg_sections_json.append(dict(name=source_section["name"], section_index=source_section["section_index"], source_section_index=projected_section["source_section_index"], frame_index=source_section["frame_index"], landmark_index=source_section["landmark_index"], owner=owner, frame=dict(owner=owner, role="form_leg_profile_control"), landmark=landmark, center=center, radii=radii, lateral_radius=radii["lateral"], up_radius=radii["up"], forward_radius=radii["forward"], profile_provenance=payload["authored_leg_profile"]["provenance"], variant_provenance=payload["authored_leg_profile"]["provenance"], lineage=lineage, consumption=("skin-driving; knee seam owned by thigh station" if source_section["name"] == "knee" else "skin-driving")))
                    leg_profile_sides.append(dict(side=side_name, sections=leg_sections_json))
                leg_profile_controls = dict(format="creature-kernel.provisional-form-leg-profile.v1", status="skin-driving leg profile; knee seam owned by thigh; hock owned by shin", provenance=payload["authored_leg_profile"]["provenance"], variant_provenance=payload["authored_leg_profile"]["provenance"], axes=dict(lateral=[1.0, 0.0, 0.0], up=[0.0, 1.0, 0.0], forward=[0.0, 0.0, 1.0]), route_topology=dict(section_names=["thigh-start", "thigh-midpoint", "knee", "shin-midpoint", "hock-endpoint"], owner_roles=["thigh", "thigh", "thigh", "shin", "shin"], seam=dict(name="knee", index=2, owner_role="thigh"), endpoint=dict(name="hock-endpoint", index=4, owner_role="shin")), sides=leg_profile_sides)
                for leg_side in leg_profile_sides:
                    knee = leg_side["sections"][2]
                    hock = leg_side["sections"][4]
                    thigh = next(item for item in limbs if item["owner"] == knee["owner"])
                    shin = next(item for item in limbs if item["owner"] == hock["owner"])
                    thigh["joints"][0]["mass"]["center"] = list(knee["center"])
                    thigh["joints"][0]["mass"]["radii"] = [knee["radii"][axis] for axis in ("lateral", "up", "forward")]
                    shin["joints"][0]["mass"]["center"] = list(hock["center"])
                    shin["joints"][0]["mass"]["radii"] = [hock["radii"][axis] for axis in ("lateral", "up", "forward")]
                    foot = next(item for item in paws if item["owner"]["role"] == "foot" and item["owner"]["anchors"] == [leg_side["side"]])
                    foot["chain"]["hock"]["radii"] = list(shin["joints"][0]["mass"]["radii"])
                    chain = foot["chain"]
                    pad = next(mass for mass in chain["masses"] if mass["control"] == "paw-pad")
                    toe = next(mass for mass in chain["masses"] if mass["control"] == "toe-box")
                    chain["midpoints"] = {{
                        "metatarsal": {{
                            "center": [0.5 * (chain["hock"]["center"][axis] + pad["center"][axis]) for axis in range(3)],
                            "radii": [0.5 * (chain["hock"]["radii"][axis] + pad["radii"][axis]) for axis in range(3)],
                        }},
                        "pad_toe": {{
                            "center": [0.5 * (pad["center"][axis] + toe["center"][axis]) for axis in range(3)],
                            "radii": [0.5 * (pad["radii"][axis] + toe["radii"][axis]) for axis in range(3)],
                        }},
                    }}
                foot_profile_sides = []
                for side_name in ("left", "right"):
                    source_side = next(item for item in payload["authored_foot_profile"]["sides"] if item["side"] == side_name)
                    projected_side = next(item for item in producer_variant["foot_profile"]["sides"] if item["side"] == side_name)
                    foot_sections_json = []
                    for source_section, projected_section in zip(source_side["sections"], projected_side["sections"]):
                        landmark = payload["authored_landmarks"][source_section["landmark_index"]]
                        owner = landmark["owner"]
                        descriptor = next(item for item in producer_variant["descriptors"] if item["address"] == owner)
                        center = [(float(descriptor["reference_point"][axis]) + float(landmark["position"][axis])) / scale for axis in range(3)]
                        radii = {{axis: projected_section[f"{{axis}}_radius_permille"] / 1000.0 for axis in ("lateral", "up", "forward")}}
                        lineage = {{}}
                        for axis, dimension_index in source_section["dimension_indices"].items():
                            dimension = payload["authored_dimensions"][dimension_index]
                            factor = projected_section["scaling"][f"{{axis}}_factor_permille"]
                            lineage[axis] = {{"base": dimension["value_permille"], "factor": factor, "scaled": projected_section[f"{{axis}}_radius_permille"], "reference": {{"owner": owner, "role": dimension["role"], "index": dimension_index}}, "provenance": dimension["provenance"], "consumed_section": source_section["name"]}}
                        foot_sections_json.append({{"name": source_section["name"], "section_index": source_section["section_index"], "source_section_index": projected_section["source_section_index"], "frame_index": source_section["frame_index"], "landmark_index": source_section["landmark_index"], "owner": owner, "frame": {{"owner": owner, "role": "form_foot_profile_control"}}, "landmark": landmark, "center": center, "radii": radii, "lateral_radius": radii["lateral"], "up_radius": radii["up"], "forward_radius": radii["forward"], "profile_provenance": payload["authored_foot_profile"]["provenance"], "variant_provenance": payload["authored_foot_profile"]["provenance"], "lineage": lineage, "consumption": "skin-driving; pad/toe stations are exact authored foot controls"}})
                    foot_side_json = {{"side": side_name, "hock_binding": source_side["hock_binding"], "sections": foot_sections_json}}
                    foot_profile_sides.append(foot_side_json)
                    foot_paw = next(item for item in paws if item["owner"]["role"] == "foot" and item["owner"]["anchors"] == [side_name])
                    for mass, projected_section in zip(foot_paw["chain"]["masses"], projected_side["sections"]):
                        mass["radii"] = [projected_section[f"{{axis}}_radius_permille"] / 1000.0 for axis in ("lateral", "up", "forward")]
                    foot_paw["chain"]["midpoints"] = {{
                        "metatarsal": {{
                            "center": [0.5 * (foot_paw["chain"]["hock"]["center"][axis] + foot_paw["chain"]["masses"][0]["center"][axis]) for axis in range(3)],
                            "radii": [0.5 * (foot_paw["chain"]["hock"]["radii"][axis] + foot_paw["chain"]["masses"][0]["radii"][axis]) for axis in range(3)],
                        }},
                        "pad_toe": {{
                            "center": [0.5 * (foot_paw["chain"]["masses"][0]["center"][axis] + foot_paw["chain"]["masses"][1]["center"][axis]) for axis in range(3)],
                            "radii": [0.5 * (foot_paw["chain"]["masses"][0]["radii"][axis] + foot_paw["chain"]["masses"][1]["radii"][axis]) for axis in range(3)],
                        }},
                    }}
                    foot_paw["chain"]["authored_profile"] = foot_side_json
                foot_profile_controls = {{"format": "creature-kernel.provisional-form-foot-profile.v1", "status": "skin-driving authored foot profile; hock inherited from shin-owned authored leg endpoint", "provenance": payload["authored_foot_profile"]["provenance"], "variant_provenance": payload["authored_foot_profile"]["provenance"], "axes": {{"lateral": [1.0, 0.0, 0.0], "up": [0.0, 1.0, 0.0], "forward": [0.0, 0.0, 1.0]}}, "route_topology": {{"side_names": ["left", "right"], "section_names": ["pad", "toe"], "hock_binding": {{"source_profile": "authored_leg_profile", "section_index": 4, "owner_role": "shin"}}}}, "sides": foot_profile_sides}}
                guide = {{"format": {publisher.REGIONAL_GUIDE_FORMAT!r}, "variant": variant_id, "owners": owners, "counts": {publisher.EXPECTED_GUIDE_COUNTS!r}, "projections": projections, "shared_render_bounds": bounds, "canvas": canvas, "layout": layout, "controls": {{"axes": {{"lateral": [1.0, 0.0, 0.0], "up": [0.0, 1.0, 0.0], "forward": [0.0, 0.0, 1.0]}}, "axial": axial, "torso_cage": torso_cage, "shoulder_frame": shoulder_frame_controls, "arm_profile": arm_profile_controls, "leg_profile": leg_profile_controls, "foot_profile": foot_profile_controls, "head": head, "limbs": limbs, "paws": paws, "tails": tails}}, "boundary": "private disposable regional controls; source-owned AddressKeys only; not a semantic or runtime contract"}}
                if {mode!r} == "guide-obsolete-recipe-count":
                    guide["counts"] = dict(guide["counts"])
                    guide["counts"]["compiled_field_recipe_counts"] = dict(guide["counts"]["compiled_field_recipe_counts"])
                    guide["counts"]["compiled_fields"] = 54
                    guide["counts"]["compiled_field_recipe_counts"].update({{"hip-girdle": 2, "shoulder-mass": 2}})
                if {mode!r} == "guide-wrong-recipe-count":
                    guide["counts"] = dict(guide["counts"])
                    guide["counts"]["compiled_field_recipe_counts"] = dict(guide["counts"]["compiled_field_recipe_counts"])
                    guide["counts"]["compiled_field_recipe_counts"]["torso-cage"] = 2
                if {mode!r} == "guide-format": guide["format"] = "creature-kernel.disposable-surface-preview-regional-guide.v10"
                if {mode!r} == "guide-provenance": guide["controls"]["head"]["owners"][0]["provenance"] = {{"source": "unexpected"}}
                if {mode!r} == "guide-controls": guide["controls"]["axes"]["forward"] = [0.0, 0.0, 2.0]
                if {mode!r} == "guide-station-omitted": guide["controls"]["axial"]["stations"].pop()
                if {mode!r} == "guide-transition-omitted": guide["controls"]["axial"]["transitions"].pop()
                if {mode!r} == "guide-girdle-omitted": guide["controls"]["limbs"][2]["masses"].pop()
                if {mode!r} == "guide-station-malformed": guide["controls"]["axial"]["stations"][1]["mass"]["radii"][0] = 0.0
                if {mode!r} == "guide-transition-malformed": guide["controls"]["axial"]["transitions"][0]["path"]["path_kind"] = "capsule"
                if {mode!r} == "guide-cage-omitted": guide["controls"].pop("torso_cage")
                if {mode!r} == "guide-cage-malformed": guide["controls"]["torso_cage"]["sections"][2]["lateral_radius"] = 0.0
                if {mode!r} == "guide-cage-connection": guide["controls"]["torso_cage"]["connections"][1]["to"] = "wrong"
                if {mode!r} == "guide-shoulder-omitted": guide["controls"].pop("shoulder_frame")
                if {mode!r} == "guide-shoulder-stale-status": guide["controls"]["shoulder_frame"]["status"] = "skin-driving private shoulder frame"
                if {mode!r} == "guide-shoulder-consumption": guide["controls"]["shoulder_frame"]["sides"][0]["curves"][0]["consumption"] = "skin-driving"
                if {mode!r} == "guide-shoulder-malformed": guide["controls"]["shoulder_frame"]["central"]["profile"][0] = 0.0
                if {mode!r} == "guide-shoulder-owner": guide["controls"]["shoulder_frame"]["sides"][0]["curves"][2]["owner"] = owners[1]
                if {mode!r} == "guide-shoulder-order": guide["controls"]["shoulder_frame"]["sides"].reverse()
                if {mode!r} == "guide-shoulder-endpoint": guide["controls"]["shoulder_frame"]["sides"][0]["curves"][0]["points"][0][0] = 0.25
                if {mode!r} == "guide-shoulder-span": guide["controls"]["shoulder_frame"]["sides"][0]["span"] = 2.0
                if {mode!r} == "guide-shoulder-degenerate": guide["controls"]["shoulder_frame"]["sides"][0]["curves"][0]["points"][1] = list(guide["controls"]["shoulder_frame"]["sides"][0]["curves"][0]["points"][0])
                if {mode!r} == "guide-shoulder-points": guide["controls"]["shoulder_frame"]["sides"][0]["curves"][0]["points"].pop()
                if {mode!r} == "guide-shoulder-profile": guide["controls"]["shoulder_frame"]["sides"][0]["curves"][1]["profile"][0] = 0.0
                if {mode!r} == "guide-shoulder-profile-continuity": guide["controls"]["shoulder_frame"]["sides"][0]["curves"][0]["profile"][1] = 0.3
                if {mode!r} == "guide-shoulder-first-quarter": guide["controls"]["shoulder_frame"]["sides"][0]["curves"][2]["points"][2][0] = -0.5
                if {mode!r} == "guide-source-landmark": guide["controls"]["shoulder_frame"]["source_controls"][0]["landmarks"][0]["position"][0] = 0.0
                if {mode!r} == "guide-source-frame": guide["controls"]["shoulder_frame"]["source_controls"][0]["frame"]["role"] = "wrong-frame"
                if {mode!r} == "guide-depth-factor": guide["controls"]["shoulder_frame"]["source_controls"][0]["depth_control"]["profile_factor"] = 999
                if {mode!r} == "guide-depth-scaled": guide["controls"]["shoulder_frame"]["source_controls"][0]["depth_control"]["scaled_value_permille"] += 1
                if {mode!r} == "guide-derived-anchor": guide["controls"]["shoulder_frame"]["sides"][0]["peak_anchor"][1] += 0.01
                if {mode!r} == "guide-derived-wrap": guide["controls"]["shoulder_frame"]["sides"][0]["curves"][0]["points"][1][2] += 0.01
                if {mode!r} == "guide-shoulder-socket":
                    shoulder_side = guide["controls"]["shoulder_frame"]["sides"][0]
                    shoulder_side["socket"]["point"][0] += 0.01
                    changed_socket = list(shoulder_side["socket"]["point"])
                    shoulder_side["curves"][0]["points"][3] = changed_socket
                    shoulder_side["curves"][1]["points"][3] = changed_socket
                    shoulder_side["curves"][2]["points"][1] = changed_socket
                if {mode!r} == "guide-arm-omitted": guide["controls"].pop("arm_profile")
                if {mode!r} == "guide-arm-side-order": guide["controls"]["arm_profile"]["sides"].reverse()
                if {mode!r} == "guide-arm-source-index": guide["controls"]["arm_profile"]["sides"][0]["sections"][1]["source_section_index"] = 4
                if {mode!r} == "guide-arm-owner": guide["controls"]["arm_profile"]["sides"][0]["sections"][0]["owner"] = owners[7]
                if {mode!r} == "guide-arm-lineage": guide["controls"]["arm_profile"]["sides"][0]["sections"][2]["lineage"]["lateral"]["scaled"] += 1
                if {mode!r} == "guide-arm-attachment": guide["controls"]["arm_profile"]["sides"][0]["sections"][0]["center"][0] += 0.01
                if {mode!r} == "guide-arm-elbow": guide["controls"]["arm_profile"]["sides"][0]["sections"][2]["center"][0] += 0.01
                if {mode!r} == "guide-arm-midpoint": guide["controls"]["arm_profile"]["sides"][0]["sections"][3]["center"][1] += 0.01
                if {mode!r} == "guide-arm-joint-radii": guide["controls"]["limbs"][0]["joints"][0]["mass"]["radii"][0] += 0.01
                if {mode!r} == "guide-leg-omitted": guide["controls"].pop("leg_profile")
                if {mode!r} == "guide-leg-side-order": guide["controls"]["leg_profile"]["sides"].reverse()
                if {mode!r} == "guide-leg-owner": guide["controls"]["leg_profile"]["sides"][0]["sections"][3]["owner"] = owners[10]
                if {mode!r} == "guide-leg-lineage": guide["controls"]["leg_profile"]["sides"][0]["sections"][2]["lineage"]["lateral"]["scaled"] += 1
                if {mode!r} == "guide-leg-knee": guide["controls"]["leg_profile"]["sides"][0]["sections"][2]["center"][1] += 0.01
                if {mode!r} == "guide-leg-hock": guide["controls"]["paws"][2]["hock_source"]["point"][2] += 0.01
                if {mode!r} == "guide-head-section-omitted":
                    guide["controls"]["head"]["sections"].pop()
                if {mode!r} == "guide-head-section-malformed":
                    guide["controls"]["head"]["sections"][3]["owner"] = owners[2]
                if {mode!r} == "guide-head-connection":
                    guide["controls"]["head"]["connections"][4]["route"] = "vertical-neck-cranium"
                if {mode!r} == "guide-head-lineage":
                    guide["controls"]["head"]["sections"][0]["lineage"]["lateral"]["scaled"] += 1
                if {mode!r} == "guide-head-compatibility":
                    guide["controls"]["head"]["masses"][0]["center"][0] += 0.01
                if {mode!r} == "guide-girdle-malformed": guide["controls"]["limbs"][2]["masses"][0]["control"] = "wrong"
                if {mode!r} == "guide-joint-endpoint": guide["controls"]["limbs"][2]["joints"][0]["mass"]["center"][0] = 0.0
                if {mode!r} == "guide-knee-anisotropic": guide["controls"]["limbs"][4]["joints"][0]["mass"]["radii"][1] = 0.13
                if {mode!r} == "guide-foot-legacy": guide["controls"]["paws"][2] = {{"owner": owners[12], "masses": [], "attachment": {{}}, "attachment_source": {{}}}}
                if {mode!r} == "guide-foot-order": guide["controls"]["paws"][2]["chain"]["masses"][1]["center"][2] = -1.0
                if {mode!r} == "guide-foot-hock-source": guide["controls"]["paws"][2]["hock_source"]["point"][0] = 0.5
                if {mode!r} == "guide-foot-hock-radii": guide["controls"]["paws"][2]["chain"]["hock"]["radii"][0] = 0.13
                if {mode!r} == "guide-foot-contact": guide["controls"]["paws"][2]["chain"]["masses"][0]["center"][1] = 0.0
                if {mode!r} == "guide-foot-taper": guide["controls"]["paws"][2]["chain"]["metatarsal"]["thickness"] = [0.3, 0.5]
                if {mode!r} == "guide-foot-axis": guide["controls"]["paws"][2]["chain"]["axes"]["forward"] = [0.0, 0.0, 2.0]
                if {mode!r} == "guide-foot-gap": guide["controls"]["paws"][2]["chain"]["masses"][1]["center"][2] = 4.8
                if {mode!r} == "guide-foot-profile-order": guide["controls"]["foot_profile"]["sides"][0]["sections"].reverse()
                if {mode!r} == "guide-foot-profile-hock": guide["controls"]["foot_profile"]["sides"][0]["hock_binding"]["side_index"] = 1
                if {mode!r} == "guide-foot-profile-lineage": guide["controls"]["foot_profile"]["sides"][0]["sections"][0]["lineage"]["lateral"]["scaled"] += 1
                if {mode!r} == "guide-foot-profile-center": guide["controls"]["foot_profile"]["sides"][0]["sections"][0]["center"][0] += 0.01
                if {mode!r} == "guide-hand-attachment-start": guide["controls"]["paws"][0]["attachment"]["points"][0][2] = 0.75
                if {mode!r} == "guide-hand-anchor-point": guide["controls"]["limbs"][1]["anchors"][0]["point"][2] = 0.75
                if {mode!r} == "guide-section-gap": guide["controls"]["limbs"][2]["sections"][1]["points"][0][0] = 0.4
                if {mode!r} == "guide-profile-second-start": guide["controls"]["limbs"][2]["sections"][1]["thickness"][0] = 0.19
                if {mode!r} == "guide-adjacent-profile": guide["controls"]["limbs"][2]["joints"][0]["adjacent_profiles"][1] = 0.99
                guide_path = directory / "regional-guide.json"
                guide_path.write_text(json.dumps(guide), encoding="utf-8")
                if {mode!r} == "guide-omitted": guide_path.unlink()
                component_recipes = []
                for recipe, count in {dict(publisher.EXPECTED_GUIDE_COUNTS["compiled_field_recipe_counts"])!r}.items():
                    component_recipes.extend([recipe] * count)
                component_visualization = {{
                    **COMPONENT_VISUALIZATION_METRICS,
                    "component_count": 52,
                    "components": [{{"source_owner": owners[index % len(owners)], "recipe": recipe, "bounds": {{"min": [-1.0, -1.0, -1.0], "max": [1.0, 1.0, 1.0]}}}} for index, recipe in enumerate(component_recipes)],
                }}
                if {mode!r}.startswith("component-"):
                    components = [dict(item) for item in component_visualization["components"]]
                    if {mode!r} == "component-missing": components.pop()
                    elif {mode!r} == "component-extra": components.append(dict(components[-1]))
                    elif {mode!r} == "component-unknown-owner": components[0]["source_owner"] = {{**owners[0], "role": "unknown"}}
                    elif {mode!r} == "component-wrong-recipe": components[0]["recipe"] = "wrong-recipe"
                    elif {mode!r} == "component-wrong-histogram": components[-1]["recipe"] = components[-3]["recipe"]
                    elif {mode!r} == "component-malformed-bounds": components[0]["bounds"] = {{"min": [-1.0, -1.0], "max": [1.0, 1.0, 1.0]}}
                    elif {mode!r} == "component-out-of-range-bounds": components[0]["bounds"] = {{"min": [-101.0, -1.0, -1.0], "max": [1.0, 1.0, 1.0]}}
                    elif {mode!r} == "component-reversed-bounds": components[0]["bounds"] = {{"min": [1.0, 1.0, 1.0], "max": [-1.0, -1.0, -1.0]}}
                    component_visualization["components"] = components
                metrics_payload = {{"source_descriptor_count": 18, "generated_field_count": 52, "field_recipe_counts": {dict(publisher.EXPECTED_GUIDE_COUNTS["compiled_field_recipe_counts"])!r}, "component_visualization": component_visualization}}
                if {mode!r} == "metrics-generated-count": metrics_payload["generated_field_count"] = 59
                if {mode!r} == "metrics-recipe-count": metrics_payload["field_recipe_counts"] = {{**metrics_payload["field_recipe_counts"], "paw-pad": 1}}
                files = [
                    ("ply", directory / "surface.ply", b"ply\\n"),
                    ("semantic-sidecar", directory / "semantic.json", b"{{}}"),
                    ("metrics", directory / "metrics.json", json.dumps(metrics_payload).encode()),
                    ("guide-skin-composite-png", png, None),
                    ("regional-guide-json", guide_path, None),
                ]
                inventory = []
                for kind, file, value in files:
                    if value is not None: file.write_bytes(value)
                    data = file.read_bytes()
                    item = {{"kind": kind, "path": file.relative_to(out).as_posix(), "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}}
                    if {mode!r} == "hash" and kind == "metrics": item["sha256"] = "0" * 64
                    if kind == "guide-skin-composite-png": item.update({{"width": (1 if {mode!r} == "png-small" else 1800), "height": (1 if {mode!r} == "png-small" else 1500), "views": ["front", "side", "three-quarter"], "panels_per_view": (2 if {mode!r} == "stale-panels" else 3), "mode": "RGB"}})
                    if kind == "regional-guide-json": item.update({{"format": {publisher.REGIONAL_GUIDE_FORMAT!r}, "variant": variant_id}})
                    inventory.append(item)
                descriptor_addresses = owners
                if {mode!r} == "fabricated-descriptor" and not variants: descriptor_addresses = [{{**owners[0], "role": "fabricated"}}] + owners[1:]
                variants.append({{"id": variant_id, "profile_id": ("wrong" if {mode!r} == "profile-mismatch" and not variants else variant_id), "source": source, "descriptor_address_keys": descriptor_addresses, "grid": {{"samples_per_axis": 72, "axis_order": ["x", "y", "z"], "bounds_min": [-4.0, -4.0, -4.0], "bounds_max": [4.0, 4.0, 4.0], "spacing": [0.1, 0.1, 0.1]}}, "metrics": metrics_payload, "inventory": inventory}})
            if {mode!r} == "bad-count": variants.pop()
            if {mode!r} == "unlisted": (out / "unlisted.bin").write_bytes(b"x")
            if {mode!r} == "symlink": (out / "escape").symlink_to(out / ids[0] / "surface.ply")
            if {mode!r} == "extra-directory": (out / "extra-empty").mkdir()
            if {mode!r} == "manifest-metrics" and variants: variants[0]["metrics"] = {{**variants[0]["metrics"], "generated_field_count": 59}}
            generator_field_recipes = {list(publisher.EXPECTED_FIELD_RECIPES)!r}
            if {mode!r} == "generator-recipes": generator_field_recipes = ["hips"]
            generator_ownership = {publisher.EXPECTED_GENERATOR_OWNERSHIP!r}
            if {mode!r} == "generator-ownership": generator_ownership = "recipe fields are source-owned; shoulder support curves are skin-driving"
            component_visualization = {publisher.EXPECTED_COMPONENT_VISUALIZATION!r}
            manifest_canvas = canvas
            manifest_layout = layout
            manifest_format = {publisher.SURFACE_PREVIEW_FORMAT!r}
            if {mode!r} == "stale-canvas": manifest_canvas = {{"width": 1800, "height": 570, "mode": "RGB"}}
            if {mode!r} == "stale-layout": manifest_layout = {{"panel_order": ["front-guide", "front-skin", "side-guide", "side-skin", "three-quarter-guide", "three-quarter-skin"], "panels": [{{"id": "front-guide", "projection": "front", "content": "guide", "box": [12, 72, 292, 548]}}, {{"id": "front-skin", "projection": "front", "content": "skin", "box": [310, 72, 590, 548]}}, {{"id": "side-guide", "projection": "side", "content": "guide", "box": [608, 72, 888, 548]}}, {{"id": "side-skin", "projection": "side", "content": "skin", "box": [906, 72, 1186, 548]}}, {{"id": "three-quarter-guide", "projection": "three-quarter", "content": "guide", "box": [1204, 72, 1484, 548]}}, {{"id": "three-quarter-skin", "projection": "three-quarter", "content": "skin", "box": [1502, 72, 1782, 548]}}], "pairing": "guide-left/skin-right per projection", "frame": "shared-world-bounds-and-projection-basis"}}
            if {mode!r} == "stale-format": manifest_format = "creature-kernel.disposable-surface-preview.v2"
            manifest = {{"format": manifest_format, "status": "success", "source_format": {common.PROVISIONAL_FORM_FORMAT!r}, "source": {{"format": {common.PROVISIONAL_FORM_FORMAT!r}, "sha256": source_hash, "document": "fixture", "namespace": "main", "resource_profile_id": "ck.resource.body.r2", "reference_scale": {{"parent": {{**owners[2], "anchors": []}}, "child": {{**owners[3], "anchors": []}}, "axis_delta": [0, 1, 0], "squared_length": 1, "source": "exact-containment-edge"}}}}, "shared_render_bounds": bounds, "canvas": manifest_canvas, "layout": manifest_layout, "projections": projections, "generator": {{"bundle_version": (2 if {mode!r} == "stale-bundle-version" else 3), "samples_per_axis": 72, "padding": 0.75, "smooth_union": {{"operator": "polynomial_cubic_smooth_min", "k": 0.12, "fold_order": "source_address_then_recipe_order"}}, "field_primitives": ["ellipsoid", "capsule", "linear-radius-tapered-segment"], "field_recipes": generator_field_recipes, "ownership": generator_ownership, "boundary": "disposable exploratory visual proof; not production geometry, SDF, collision, rig, topology, or Readiness evidence", "component_visualization": component_visualization}}, "variants": variants}}
            (out / "surface-preview-manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        """), encoding="utf-8")
        path.chmod(0o755)
        return path

    def _successor_generator(self, *, mode: str = "success") -> Path:
        """Write a small valid successor-v9/v16-region fixture, with bounded mutations."""

        path = self.directory / f"successor-generator-{mode}.py"
        script = textwrap.dedent("""
            #!/usr/bin/env python3
            import copy, hashlib, json, math, pathlib, sys, time

            MODE = __MODE__
            PNG = __PNG__
            CANVAS = __CANVAS__
            PROJECTIONS = __PROJECTIONS__
            LAYOUT = __LAYOUT__
            BOUNDS = __BOUNDS__
            EXPANDED_BOUNDS = __EXPANDED_BOUNDS__
            SUCCESSOR_FORMAT = __SUCCESSOR_FORMAT__
            CONSUMER_ID = __CONSUMER_ID__
            REGION_ID = __REGION_ID__
            EXTREMITY_ORDER = __EXTREMITY_ORDER__
            EXTREMITY_KINDS = __EXTREMITY_KINDS__
            HEAD_NECK_ORDER = __HEAD_NECK_ORDER__
            HEAD_NECK_SECTION_COUNTS = __HEAD_NECK_SECTION_COUNTS__
            LIMB_ORDER = __LIMB_ORDER__
            LIMB_STATION_NAMES = __LIMB_STATION_NAMES__
            EXTREMITY_STATION_NAMES = __EXTREMITY_STATION_NAMES__
            HAND_PAW_PROFILE = __HAND_PAW_PROFILE__
            HAND_PAW_SECTION_NAMES = __HAND_PAW_SECTION_NAMES__
            FOOT_PROFILE_SECTION_NAMES = __FOOT_PROFILE_SECTION_NAMES__
            FOOT_PROFILE_OWNER_ROLES = __FOOT_PROFILE_OWNER_ROLES__
            HAND_PAW_OPERATION = __HAND_PAW_OPERATION__
            TORSO_PROFILE_OPERATION = __TORSO_PROFILE_OPERATION__
            HEAD_NECK_PROFILE_OPERATION = __HEAD_NECK_PROFILE_OPERATION__
            ARM_PROFILE_OPERATION = __ARM_PROFILE_OPERATION__
            LEG_PROFILE_OPERATION = __LEG_PROFILE_OPERATION__
            FOOT_PROFILE_OPERATION = __FOOT_PROFILE_OPERATION__
            FORWARD_MUZZLE_COMPOSITION_OPERATION = __FORWARD_MUZZLE_COMPOSITION_OPERATION__
            FORWARD_MUZZLE_GEOMETRIC_INPUT_SECTION_INDICES = __FORWARD_MUZZLE_GEOMETRIC_INPUT_SECTION_INDICES__
            FORWARD_MUZZLE_RADIUS_DONOR_SECTION_INDICES = __FORWARD_MUZZLE_RADIUS_DONOR_SECTION_INDICES__
            TORSO_SUPERELLIPSE_EXPONENT = __TORSO_SUPERELLIPSE_EXPONENT__
            HIP_ROOT_OPERATION = __HIP_ROOT_OPERATION__
            HIP_ROOT_CONTROLS = __HIP_ROOT_CONTROLS__
            TAIL_ORDER = __TAIL_ORDER__
            TAIL_KINDS = __TAIL_KINDS__
            TAIL_SECTION_NAMES = __TAIL_SECTION_NAMES__
            REPLACED = __REPLACED__
            MESH_PADDING = __MESH_PADDING__
            CAPTURE_PADDING = __CAPTURE_PADDING__
            COMPONENT_VISUALIZATION = __COMPONENT_VISUALIZATION__
            COMPONENT_VISUALIZATION_METRICS = __COMPONENT_VISUALIZATION_METRICS__
            VALID_PLY = __VALID_PLY__
            DISCONNECTED_PLY = __DISCONNECTED_PLY__
            NONWATERTIGHT_PLY = __NONWATERTIGHT_PLY__
            DUPLICATE_FACE_PLY = __DUPLICATE_FACE_PLY__
            INCONSISTENT_ORIENTATION_PLY = __INCONSISTENT_ORIENTATION_PLY__
            ZERO_VOLUME_PLY = __ZERO_VOLUME_PLY__
            FLATTENED_PLY = __FLATTENED_PLY__

            args = dict(zip(sys.argv[1::2], sys.argv[2::2]))
            source_path = pathlib.Path(args["--input"])
            out = pathlib.Path(args["--output"])
            if MODE == "failure":
                print("successor fixture generator failed", file=sys.stderr)
                raise SystemExit(7)
            if MODE == "timeout":
                time.sleep(60)
            if out.exists():
                raise RuntimeError("output must not already exist")
            payload = json.loads(source_path.read_text(encoding="utf-8"))
            def variant_digest(raw_variant):
                encoded = json.dumps(raw_variant, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
                return hashlib.sha256(encoded).hexdigest()
            def source_owner(descriptors, role, anchors):
                return next(item["address"] for item in descriptors if item["address"]["role"] == role and item["address"]["anchors"] == anchors)
            def bend_count(points):
                count = 0
                for index in range(1, len(points) - 1):
                    incoming = [float(points[index][axis]) - float(points[index - 1][axis]) for axis in range(3)]
                    outgoing = [float(points[index + 1][axis]) - float(points[index][axis]) for axis in range(3)]
                    incoming_length = math.sqrt(sum(value * value for value in incoming))
                    outgoing_length = math.sqrt(sum(value * value for value in outgoing))
                    alignment = sum(incoming[axis] * outgoing[axis] for axis in range(3)) / (incoming_length * outgoing_length)
                    if alignment < 1.0 - 1.0e-8:
                        count += 1
                return count
            def generated_section(name, center, radii, path_length):
                return {"name": name, "center": list(center), "tangent": [0.0, 1.0, 0.0], "transverse_axes": [[1.0, 0.0, 0.0], [0.0, 0.0, 1.0]], "transverse_radii": list(radii), "path_length": float(path_length)}
            def generated_cap(side, center, radii):
                return {"side": side, "center": list(center), "outward_tangent": ([0.0, -1.0, 0.0] if side == "start" else [0.0, 1.0, 0.0]), "transverse_axes": [[1.0, 0.0, 0.0], [0.0, 0.0, 1.0]], "transverse_radii": list(radii), "axial_radius": float(min(radii))}
            def generated_tail_controls(root_owner, tip_owner):
                source_points = [[-0.5, 0.0, 0.0], [0.5, 0.0, 0.0]]
                source_radii = [[0.2, 0.2], [0.2, 0.2]]
                extension_points = [list(source_points[-1]), [1.0, 0.0, 0.0]]
                extension_radii = [[0.2, 0.2], [0.2, 0.2]]
                collar_center = [0.0, 0.0, 0.0]
                collar_radii = [0.5, 0.5]
                tip_cap_center = list(extension_points[-1])
                specs = [
                    (TAIL_SECTION_NAMES[0], root_owner, source_points, source_radii),
                    (TAIL_SECTION_NAMES[1], root_owner, source_points, source_radii),
                    (TAIL_SECTION_NAMES[2], root_owner, [collar_center] * 3, [collar_radii] * 3),
                    (TAIL_SECTION_NAMES[3], tip_owner, source_points, source_radii),
                    (TAIL_SECTION_NAMES[4], tip_owner, extension_points, extension_radii),
                    (TAIL_SECTION_NAMES[5], tip_owner, [tip_cap_center] * 3, [collar_radii] * 3),
                ]
                controls = []
                for names, owner, centers, radii in specs:
                    sections = [generated_section(name, center, profile, section_index) for section_index, (name, center, profile) in enumerate(zip(names, centers, radii))]
                    controls.append({"name": TAIL_ORDER[len(controls)], "kind": TAIL_KINDS[len(controls)], "owner": owner, "sections": sections, "endpoint_caps": [generated_cap("start", sections[0]["center"], sections[0]["transverse_radii"]), generated_cap("end", sections[-1]["center"], sections[-1]["transverse_radii"])]})
                endpoint = {"point": list(source_points[-1]), "source_end_profile": list(source_radii[-1]), "extension_start_profile": list(extension_radii[0])}
                return controls, endpoint
            source = {"format": payload["format"], "sha256": hashlib.sha256(source_path.read_bytes()).hexdigest(), **payload["source"], "reference_scale": payload["reference_scale"]}
            if MODE == "source-mismatch":
                source["sha256"] = "0" * 64
            elif MODE == "source-cross-variant":
                source["document"] = "other-fixture"
            elif MODE == "scale-mismatch":
                source["reference_scale"] = {**payload["reference_scale"], "squared_length": 4, "axis_delta": [0, 2, 0]}
            frame_bounds = BOUNDS
            if MODE == "expanded-bounds":
                frame_bounds = EXPANDED_BOUNDS
            frame = {"canvas": CANVAS, "projections": PROJECTIONS, "layout": LAYOUT, "shared_render_bounds": frame_bounds}
            if MODE in {"frame-mismatch", "non-containing-bounds"}:
                frame["shared_render_bounds"] = {"min": [-4.0, -5.0, -5.0], "max": [5.0, 5.0, 5.0]}
            out.mkdir(parents=True)
            records = []
            raw_variants = payload["variants"]
            for variant_index, raw_variant in enumerate(raw_variants):
                variant_id = raw_variant["id"]
                source_variant_sha256 = variant_digest(raw_variant)
                if MODE == "cross-variant-digest" and variant_index == 0:
                    source_variant_sha256 = variant_digest(raw_variants[1])
                variant_dir = out / variant_id
                variant_dir.mkdir()
                surface_ply = VALID_PLY
                if MODE == "ply-disconnected": surface_ply = DISCONNECTED_PLY
                elif MODE == "ply-nonwatertight": surface_ply = NONWATERTIGHT_PLY
                elif MODE == "ply-duplicate-face": surface_ply = DUPLICATE_FACE_PLY
                elif MODE == "ply-inconsistent-orientation": surface_ply = INCONSISTENT_ORIENTATION_PLY
                elif MODE == "ply-zero-volume": surface_ply = ZERO_VOLUME_PLY
                elif MODE == "ply-flattened": surface_ply = FLATTENED_PLY
                (variant_dir / "surface.ply").write_bytes(surface_ply)
                bridge = {"enabled": False, "consumer": "none", "regions": [], "field_count": 0, "retained_recipes": []}
                replaced = list(REPLACED)
                producer_variant = raw_variants[variant_index]
                descriptors = producer_variant["descriptors"]
                semantic = {
                    "format": "creature-kernel.disposable-surface-preview-semantic-winners.v1",
                    "source_format": payload["format"],
                    "variant_id": variant_id,
                    "source_variant_sha256": source_variant_sha256,
                    "surface_sha256": hashlib.sha256(surface_ply).hexdigest(),
                    "vertex_count": 4,
                    "source_node_labels": [descriptors[0]["address"]] * 4,
                    "attribution": "every recipe component resolves to its source descriptor owner; no synthetic node identity is emitted",
                }
                if MODE == "semantic-format":
                    semantic["format"] = "creature-kernel.disposable-surface-preview-semantic-winners.v0"
                elif MODE == "semantic-count":
                    semantic["vertex_count"] = 3
                elif MODE == "semantic-owner":
                    semantic["source_node_labels"] = [{**descriptors[0]["address"], "role": "synthetic-bone"}] * 4
                elif MODE == "semantic-variant-hash":
                    semantic["source_variant_sha256"] = "0" * 64
                elif MODE == "semantic-surface-hash":
                    semantic["surface_sha256"] = "0" * 64
                (variant_dir / "semantic.json").write_text(json.dumps(semantic, sort_keys=True), encoding="utf-8")
                torso_owner = next(item["address"] for item in descriptors if item["address"]["role"] == "torso" and item["address"]["anchors"] == [])
                reference_scale = math.sqrt(float(payload["reference_scale"]["squared_length"]))
                depth_factor = {"neutral-v0": 1_000, "broad-soft-v0": 1_150, "lean-readable-v0": 800, "depth-forward-v0": 1_000}[variant_id]
                shoulder_controls = []
                shoulder_owner_keys = []
                for side in ("left", "right"):
                    upper_owner = next(item["address"] for item in descriptors if item["address"]["role"] == "upper_arm" and item["address"]["anchors"] == [side])
                    reference_point = next(item["reference_point"] for item in descriptors if item["address"] == upper_owner)
                    landmarks = {item["role"]: item for item in payload["authored_landmarks"] if item["owner"] == upper_owner}
                    peak = [(float(reference_point[axis]) + float(landmarks["form_shoulder_peak"]["position"][axis])) / reference_scale for axis in range(3)]
                    axilla = [(float(reference_point[axis]) + float(landmarks["form_axilla"]["position"][axis])) / reference_scale for axis in range(3)]
                    depth_value = next(item["value_permille"] for item in payload["authored_dimensions"] if item["owner"] == upper_owner and item["role"] == "form_shoulder_depth_radius")
                    shoulder_controls.append({"side": side, "authored_center": [0.5 * (peak[axis] + axilla[axis]) for axis in range(3)], "vertical_radius": 0.5 * (peak[1] - axilla[1]), "depth_radius": (depth_value * depth_factor // 1_000) / 1_000.0})
                    shoulder_owner_keys.append([torso_owner, torso_owner, upper_owner, upper_owner, upper_owner])
                torso_controls = []
                for profile_section in producer_variant["torso_profile"]["sections"]:
                    index_section = payload["authored_torso_profile"]["sections"][profile_section["source_section_index"]]
                    landmark = payload["authored_landmarks"][index_section["landmark_index"]]
                    owner = landmark["owner"]
                    descriptor = next(item for item in descriptors if item["address"] == owner)
                    center = [(float(descriptor["reference_point"][axis]) + float(landmark["position"][axis])) / reference_scale for axis in range(3)]
                    torso_controls.append({"name": profile_section["name"], "owner": owner, "center": center, "axial_position": center[1], "lateral_radius": profile_section["lateral_radius_permille"] / 1000.0, "anterior_radius": profile_section["anterior_radius_permille"] / 1000.0, "posterior_radius": profile_section["posterior_radius_permille"] / 1000.0})
                shoulder_section_names = ["torso-interior", "torso-boundary", "authored-shoulder", "upper-arm-socket", "upper-arm-midpoint"]
                head_owner = source_owner(descriptors, "head", [])
                neck_owner = source_owner(descriptors, "neck", [])
                source_head = payload["authored_head_neck_profile"]
                projected_head = producer_variant["head_neck_profile"]
                head_sections = []
                for source_section, projected_section in zip(source_head["sections"], projected_head["sections"]):
                    landmark = payload["authored_landmarks"][source_section["landmark_index"]]
                    owner = landmark["owner"]
                    descriptor = next(item for item in descriptors if item["address"] == owner)
                    center = [(float(descriptor["reference_point"][axis]) + float(landmark["position"][axis])) / reference_scale for axis in range(3)]
                    radii = {axis: projected_section[f"{axis}_radius_permille"] / 1000.0 for axis in ("lateral", "up", "forward")}
                    lineage = {}
                    for axis, dimension_index in source_section["dimension_indices"].items():
                        dimension = payload["authored_dimensions"][dimension_index]
                        lineage[axis] = {"base": dimension["value_permille"], "factor": projected_section["scaling"][f"{axis}_factor_permille"], "scaled": projected_section[f"{axis}_radius_permille"], "reference": {"owner": owner, "role": dimension["role"], "index": dimension_index}, "provenance": dimension["provenance"], "consumed_section": source_section["name"]}
                    head_sections.append({"name": source_section["name"], "section_index": source_section["section_index"], "source_section_index": projected_section["source_section_index"], "frame_index": source_section["frame_index"], "landmark_index": source_section["landmark_index"], "owner": owner, "center": center, "radii": radii, "lineage": lineage})
                head_connections = []
                for connection_spec in source_head["connections"]:
                    from_section = head_sections[connection_spec["from_section_index"]]
                    to_section = head_sections[connection_spec["to_section_index"]]
                    head_connections.append({"name": connection_spec["name"], "from_section_index": connection_spec["from_section_index"], "to_section_index": connection_spec["to_section_index"], "route": connection_spec["route"], "centerline": [from_section["center"], to_section["center"]], "thickness": [min(from_section["radii"].values()), min(to_section["radii"].values())]})
                cranium_index, muzzle_root_index, muzzle_tip_index = FORWARD_MUZZLE_GEOMETRIC_INPUT_SECTION_INDICES
                muzzle_root_radius_index, muzzle_mid_radius_index, muzzle_tip_radius_index = FORWARD_MUZZLE_RADIUS_DONOR_SECTION_INDICES
                composition_root = [0.5 * (head_sections[cranium_index]["center"][axis] + head_sections[cranium_index]["radii"]["forward"] * (1.0 if axis == 2 else 0.0) + head_sections[muzzle_root_index]["center"][axis]) for axis in range(3)]
                composition_mid = [0.5 * (composition_root[axis] + head_sections[muzzle_tip_index]["center"][axis]) for axis in range(3)]
                muzzle_composition = {"operation": FORWARD_MUZZLE_COMPOSITION_OPERATION, "section_names": ["muzzle-composition-root", "muzzle-composition-mid", "muzzle-composition-tip"], "geometric_input_section_indices": list(FORWARD_MUZZLE_GEOMETRIC_INPUT_SECTION_INDICES), "radius_donor_section_indices": list(FORWARD_MUZZLE_RADIUS_DONOR_SECTION_INDICES), "center_derivation": ["midpoint(cranium-mid forward surface, muzzle-root center)", "midpoint(derived root, muzzle-tip center)", "muzzle-tip center"], "centers": [composition_root, composition_mid, head_sections[muzzle_tip_index]["center"]], "station_radii": [head_sections[index]["radii"] for index in FORWARD_MUZZLE_RADIUS_DONOR_SECTION_INDICES]}
                head_neck = {
                    "profile_format": "creature-kernel.provisional-form-head-neck-profile.v1",
                    "operation": HEAD_NECK_PROFILE_OPERATION,
                    "regional_guide_format": "creature-kernel.disposable-surface-preview-regional-guide.v11",
                    "provenance": source_head["provenance"],
                    "sections_consumed": 8,
                    "connections_consumed": 7,
                    "sections": head_sections,
                    "connections": head_connections,
                    "route_topology": [
                        {"name": "vertical-neck-cranium", "operation": HEAD_NECK_PROFILE_OPERATION, "section_indices": [0, 1, 2, 3, 4], "section_names": [head_sections[index]["name"] for index in (0, 1, 2, 3, 4)], "connection_names": [head_connections[index]["name"] for index in (0, 1, 2, 3)], "tangent_axis": "up", "transverse_axes": ["lateral", "forward"], "owner_keys": [head_sections[index]["owner"] for index in (0, 1, 2, 3, 4)], "station_radii": [head_sections[index]["radii"] for index in (0, 1, 2, 3, 4)], "endpoint_cap_count": 2, "internal_transition_count": 0, "derived_compositions": []},
                        {"name": "forward-muzzle", "operation": HEAD_NECK_PROFILE_OPERATION, "section_indices": [3, 5, 6, 7], "section_names": [head_sections[index]["name"] for index in (3, 5, 6, 7)], "connection_names": [head_connections[index]["name"] for index in (4, 5, 6)], "tangent_axis": "forward", "transverse_axes": ["lateral", "up"], "owner_keys": [head_sections[index]["owner"] for index in (3, 5, 6, 7)], "station_radii": [head_sections[index]["radii"] for index in (3, 5, 6, 7)], "endpoint_cap_count": 2, "internal_transition_count": 0, "derived_compositions": [muzzle_composition]},
                    ],
                }
                limb_owners = {(side, role): source_owner(descriptors, role, [side]) for side in ("left", "right") for role in ("upper_arm", "forearm", "thigh", "shin")}
                arm_station_sides = []
                arm_routes = []
                for side_name in ("left", "right"):
                    source_side = next(item for item in payload["authored_arm_profile"]["sides"] if item["side"] == side_name)
                    projected_side = next(item for item in producer_variant["arm_profile"]["sides"] if item["side"] == side_name)
                    stations = []
                    for source_section, projected_section in zip(source_side["sections"], projected_side["sections"]):
                        landmark = payload["authored_landmarks"][source_section["landmark_index"]]
                        owner = landmark["owner"]
                        side_sign = -1.0 if side_name == "left" else 1.0
                        path_start = [side_sign * (1.5 if owner["role"] == "upper_arm" else 1.0), 0.9 if owner["role"] == "upper_arm" else 0.0, 0.0]
                        path_end = [side_sign * (1.0 if owner["role"] == "upper_arm" else 1.2), 0.0 if owner["role"] == "upper_arm" else -0.7, 0.0]
                        local_y = float(landmark["position"][1])
                        center = [float(path_start[axis]) - local_y * (float(path_end[axis]) - float(path_start[axis])) for axis in range(3)]
                        radii = {axis: projected_section[f"{axis}_radius_permille"] / 1000.0 for axis in ("lateral", "up", "forward")}
                        lineage = {}
                        for axis, dimension_index in source_section["dimension_indices"].items():
                            dimension = payload["authored_dimensions"][dimension_index]
                            lineage[axis] = {"base": dimension["value_permille"], "factor": projected_section["scaling"][f"{axis}_factor_permille"], "scaled": projected_section[f"{axis}_radius_permille"], "reference": {"owner": owner, "role": dimension["role"], "index": dimension_index}, "provenance": dimension["provenance"], "consumed_section": source_section["name"]}
                        stations.append({"name": source_section["name"], "section_index": source_section["section_index"], "source_section_index": projected_section["source_section_index"], "owner": owner, "center": center, "radii": radii, "lineage": lineage, "consumption": ("skin-driving; elbow seam owned by upper_arm station" if source_section["name"] == "elbow" else "skin-driving")})
                    arm_station_sides.append({"side": side_name, "sections": stations})
                    for route_name, route_kind, route_sections in ((f"{side_name}-upper-arm-route", "upper-arm", stations[:3]), (f"{side_name}-forearm-route", "forearm", stations[2:])):
                        arm_routes.append({"name": route_name, "side": side_name, "route": route_kind, "station_names": [item["name"] for item in route_sections], "source_section_indices": [int(item["source_section_index"]) for item in route_sections], "owner_keys": [item["owner"] for item in route_sections], "station_count": len(route_sections)})
                arm_profile = {"format": "creature-kernel.provisional-form-arm-profile.v1", "source": "authored_arm_profile", "regional_guide_format": "creature-kernel.disposable-surface-preview-regional-guide.v11", "operation": ARM_PROFILE_OPERATION, "topology": "two-routes-per-side-shared-upper-arm-elbow-seam", "route_order": [item["name"] for item in arm_routes], "routes": arm_routes, "stations": arm_station_sides, "elbow_ownership": "upper_arm"}
                leg_station_sides = []
                for side_name in ("left", "right"):
                    source_side = next(item for item in payload["authored_leg_profile"]["sides"] if item["side"] == side_name)
                    projected_side = next(item for item in producer_variant["leg_profile"]["sides"] if item["side"] == side_name)
                    side_sign = -1.0 if side_name == "left" else 1.0
                    path_start = [side_sign * 1.0, -1.0, 0.0]
                    path_end = [side_sign * 1.0, -2.0, 0.0]
                    shin_start = [side_sign * 1.0, -2.0, 0.0]
                    shin_end = [side_sign * 1.0, -3.0, 1.0]
                    stations = []
                    for source_section, projected_section in zip(source_side["sections"], projected_side["sections"]):
                        landmark = payload["authored_landmarks"][source_section["landmark_index"]]
                        owner = landmark["owner"]
                        start, end = (path_start, path_end) if owner["role"] == "thigh" else (shin_start, shin_end)
                        local_y = float(landmark["position"][1])
                        center = [float(start[axis]) - local_y * (float(end[axis]) - float(start[axis])) for axis in range(3)]
                        radii = {axis: projected_section[f"{axis}_radius_permille"] / 1000.0 for axis in ("lateral", "up", "forward")}
                        lineage = {}
                        for axis, dimension_index in source_section["dimension_indices"].items():
                            dimension = payload["authored_dimensions"][dimension_index]
                            lineage[axis] = {"base": dimension["value_permille"], "factor": projected_section["scaling"][f"{axis}_factor_permille"], "scaled": projected_section[f"{axis}_radius_permille"], "reference": {"owner": owner, "role": dimension["role"], "index": dimension_index}, "provenance": dimension["provenance"], "consumed_section": source_section["name"]}
                        stations.append({"name": source_section["name"], "section_index": source_section["section_index"], "source_section_index": projected_section["source_section_index"], "owner": owner, "center": center, "frame_index": source_section["frame_index"], "landmark_index": source_section["landmark_index"], "radii": radii, "lineage": lineage, "consumption": ("skin-driving; knee seam owned by thigh station" if source_section["name"] == "knee" else "skin-driving; hock endpoint owned by shin station" if source_section["name"] == "hock-endpoint" else "skin-driving"), "profile_provenance": payload["authored_leg_profile"]["provenance"], "variant_provenance": payload["authored_leg_profile"]["provenance"]})
                    leg_station_sides.append({"side": side_name, "route": f"{side_name}-leg", "route_kind": "leg-profile", "source_section_indices": [item["source_section_index"] for item in stations], "station_count": 5, "owner_keys": [item["owner"] for item in stations], "stations": stations})
                leg_profile = {"format": "creature-kernel.provisional-form-leg-profile.v1", "source": "authored_leg_profile", "source_format": payload["format"], "regional_guide_format": "creature-kernel.disposable-surface-preview-regional-guide.v11", "operation": LEG_PROFILE_OPERATION, "topology": "one-five-station-route-per-side-thigh-knee-shin-hock", "route_order": [item["route"] for item in leg_station_sides], "route_kinds": [item["route_kind"] for item in leg_station_sides], "section_names": list(payload["authored_leg_profile"]["sides"][0]["sections"][index]["name"] for index in range(5)), "owner_roles": ["thigh", "thigh", "thigh", "shin", "shin"], "station_count": 10, "radius_count": 30, "provenance": payload["authored_leg_profile"]["provenance"], "variant_provenance": payload["authored_leg_profile"]["provenance"], "knee_seam": {"name": "knee", "index": 2, "owner_role": "thigh"}, "hock_endpoint": {"name": "hock-endpoint", "index": 4, "owner_role": "shin"}, "sides": leg_station_sides}
                foot_profile_sides = []
                for side_name in ("left", "right"):
                    source_side = next(item for item in payload["authored_foot_profile"]["sides"] if item["side"] == side_name)
                    projected_side = next(item for item in producer_variant["foot_profile"]["sides"] if item["side"] == side_name)
                    leg_side = next(item for item in leg_station_sides if item["side"] == side_name)
                    hock = leg_side["stations"][4]
                    hock_radii = [hock["radii"][axis] for axis in ("lateral", "up", "forward")]
                    guide_sections = []
                    for source_section, projected_section in zip(source_side["sections"], projected_side["sections"]):
                        landmark = payload["authored_landmarks"][source_section["landmark_index"]]
                        owner = landmark["owner"]
                        descriptor = next(item for item in descriptors if item["address"] == owner)
                        center = [(float(descriptor["reference_point"][axis]) + float(landmark["position"][axis])) / reference_scale for axis in range(3)]
                        radii = {axis: projected_section[f"{axis}_radius_permille"] / 1000.0 for axis in ("lateral", "up", "forward")}
                        lineage = {}
                        for axis, dimension_index in source_section["dimension_indices"].items():
                            dimension = payload["authored_dimensions"][dimension_index]
                            lineage[axis] = {"base": dimension["value_permille"], "factor": projected_section["scaling"][f"{axis}_factor_permille"], "scaled": projected_section[f"{axis}_radius_permille"], "reference": {"owner": owner, "role": dimension["role"], "index": dimension_index}, "provenance": dimension["provenance"], "consumed_section": source_section["name"]}
                        guide_sections.append({"name": source_section["name"], "owner": owner, "center": center, "radii": [radii[axis] for axis in ("lateral", "up", "forward")], "lineage": lineage, "profile_provenance": payload["authored_foot_profile"]["provenance"], "variant_provenance": payload["authored_foot_profile"]["provenance"]})
                    pad = guide_sections[0]
                    toe = guide_sections[1]
                    station_sources = [
                        (FOOT_PROFILE_SECTION_NAMES[0], hock["owner"], hock["center"], hock_radii, {"kind": "authored-leg-hock", "profile": payload["authored_leg_profile"]["format"], "source": "authored_leg_profile", "radii": hock["lineage"], "profile_provenance": hock["profile_provenance"], "variant_provenance": hock["variant_provenance"]}),
                        (FOOT_PROFILE_SECTION_NAMES[1], pad["owner"], [0.5 * (hock["center"][axis] + pad["center"][axis]) for axis in range(3)], [0.5 * (hock_radii[axis] + pad["radii"][axis]) for axis in range(3)], {"kind": "derived-guide-midpoint", "inputs": [FOOT_PROFILE_SECTION_NAMES[0], FOOT_PROFILE_SECTION_NAMES[2]], "profile_provenance": pad["profile_provenance"], "variant_provenance": pad["variant_provenance"]}),
                        (FOOT_PROFILE_SECTION_NAMES[2], pad["owner"], pad["center"], pad["radii"], {"kind": "authored-foot-profile", "profile": payload["authored_foot_profile"]["format"], "source": "authored_foot_profile", "radii": pad["lineage"], "profile_provenance": pad["profile_provenance"], "variant_provenance": pad["variant_provenance"]}),
                        (FOOT_PROFILE_SECTION_NAMES[3], pad["owner"], [0.5 * (pad["center"][axis] + toe["center"][axis]) for axis in range(3)], [0.5 * (pad["radii"][axis] + toe["radii"][axis]) for axis in range(3)], {"kind": "derived-guide-midpoint", "inputs": [FOOT_PROFILE_SECTION_NAMES[2], FOOT_PROFILE_SECTION_NAMES[4]], "profile_provenance": pad["profile_provenance"], "variant_provenance": pad["variant_provenance"]}),
                        (FOOT_PROFILE_SECTION_NAMES[4], toe["owner"], toe["center"], toe["radii"], {"kind": "authored-foot-profile", "profile": payload["authored_foot_profile"]["format"], "source": "authored_foot_profile", "radii": toe["lineage"], "profile_provenance": toe["profile_provenance"], "variant_provenance": toe["variant_provenance"]}),
                    ]
                    stations = [{"name": name, "section_index": index, "source_section_index": [4, 0, 0, 1, 1][index], "owner": owner, "center": center, "volume_radii": radii, "lineage": lineage} for index, (name, owner, center, radii, lineage) in enumerate(station_sources)]
                    foot_profile_sides.append({"side": side_name, "route": f"{side_name}-foot", "route_kind": "foot-profile", "station_count": 5, "source_section_indices": [item["source_section_index"] for item in stations], "owner_roles": list(FOOT_PROFILE_OWNER_ROLES), "stations": stations})
                foot_profile = {"format": "creature-kernel.provisional-form-foot-profile.v1", "source": "authored_foot_profile", "source_format": payload["format"], "regional_guide_format": "creature-kernel.disposable-surface-preview-regional-guide.v11", "operation": FOOT_PROFILE_OPERATION, "topology": "one-five-station-hock-to-toe-route-per-side", "route_order": [item["route"] for item in foot_profile_sides], "route_kinds": ["foot-profile", "foot-profile"], "section_names": list(FOOT_PROFILE_SECTION_NAMES), "owner_roles": list(FOOT_PROFILE_OWNER_ROLES), "route_station_count": 10, "authored_station_count": 4, "route_volume_radius_count": 30, "authored_radius_count": 12, "provenance": payload["authored_foot_profile"]["provenance"], "variant_provenance": payload["authored_foot_profile"]["provenance"], "sides": foot_profile_sides}
                limb_owner_keys = [
                    [limb_owners[("left", "upper_arm")]] * 3,
                    [limb_owners[("left", "upper_arm")], limb_owners[("left", "forearm")], limb_owners[("left", "forearm")]],
                    [limb_owners[("right", "upper_arm")]] * 3,
                    [limb_owners[("right", "upper_arm")], limb_owners[("right", "forearm")], limb_owners[("right", "forearm")]],
                    [limb_owners[("left", "thigh")]] * 3 + [limb_owners[("left", "shin")]] * 2,
                    [limb_owners[("right", "thigh")]] * 3 + [limb_owners[("right", "shin")]] * 2,
                ]
                limb_centerlines = []
                for side, proximal_role in (("left", "thigh"), ("right", "thigh")):
                    side_sign = -1.0 if side == "left" else 1.0
                    if proximal_role == "upper_arm":
                        limb_centerlines.append([[side_sign * 1.5, 0.9, 0.0], [side_sign * 1.25, 0.45, 0.0], [side_sign * 1.0, 0.0, 0.0], [side_sign * 1.1, -0.35, 0.0], [side_sign * 1.2, -0.7, 0.0]])
                    else:
                        limb_centerlines.append([[side_sign * 1.0, -1.0, 0.0], [side_sign * 1.0, -1.5, 0.0], [side_sign * 1.0, -2.0, 0.0], [side_sign * 1.0, -2.5, 0.5], [side_sign * 1.0, -3.0, 1.0]])
                limb_internal_transition_counts = [0, 0, 0, 0, *[bend_count(points) for points in limb_centerlines]]
                pelvis_owner = torso_controls[0]["owner"]
                hip_root_section_names = ["hip-socket", "hip-cup", "thigh-tangent-blend", "thigh-root"]
                hip_root_section_owner_keys = []
                hip_root_source_owner_keys = []
                hip_root_boundary_parameters = []
                hip_root_socket_parameters = []
                hip_root_tangent_blend_distances = []
                hip_root_derived_from = []
                hip_root_volume_radii = []
                for leg_side in leg_profile["sides"]:
                    thigh_start = leg_side["stations"][0]
                    thigh_owner = thigh_start["owner"]
                    thigh_volume = [thigh_start["radii"][axis] for axis in ("lateral", "up", "forward")]
                    pelvis_support = [1.1 * radius for radius in thigh_volume]
                    socket_volume = [HIP_ROOT_CONTROLS["socket_thigh_weight"] * thigh + HIP_ROOT_CONTROLS["socket_pelvis_weight"] * support for thigh, support in zip(thigh_volume, pelvis_support)]
                    cup_volume = [HIP_ROOT_CONTROLS["cup_thigh_weight"] * thigh + HIP_ROOT_CONTROLS["cup_pelvis_weight"] * support for thigh, support in zip(thigh_volume, pelvis_support)]
                    tangent_blend_volume = [0.5 * (cup + thigh) for cup, thigh in zip(cup_volume, thigh_volume)]
                    boundary_parameter = 0.5
                    socket_parameter = HIP_ROOT_CONTROLS["socket_fraction"] * boundary_parameter
                    tangent_blend_distance = 0.25
                    hip_root_section_owner_keys.append([pelvis_owner, thigh_owner, thigh_owner, thigh_owner])
                    hip_root_source_owner_keys.append([pelvis_owner, thigh_owner])
                    hip_root_boundary_parameters.append(boundary_parameter)
                    hip_root_socket_parameters.append(socket_parameter)
                    hip_root_tangent_blend_distances.append(tangent_blend_distance)
                    hip_root_derived_from.append({
                        "lower_pelvis": {"section_name": "lower-pelvis", "source_section_index": 0},
                        "authored_thigh_start": {"station_name": "thigh-start", "source_station_index": 0},
                        "tangent_blend": {"station_name": "thigh-tangent-blend", "construction": "authored-thigh-start-center-minus-distance-times-authored-thigh-tangent", "distance": tangent_blend_distance},
                    })
                    hip_root_volume_radii.append({"socket": socket_volume, "cup": cup_volume, "tangent_blend": tangent_blend_volume, "authored_thigh_start": thigh_volume})
                hip_root = {
                    "operation": HIP_ROOT_OPERATION,
                    "topology": "one-derived-four-station-pelvis-socket-cup-tangent-blend-to-authored-thigh-root-per-side",
                    "route_order": ["left-hip-root-transition", "right-hip-root-transition"],
                    "route_kinds": ["derived-pelvis-thigh-transition", "derived-pelvis-thigh-transition"],
                    "section_names": [hip_root_section_names, hip_root_section_names],
                    "section_counts": [4, 4],
                    "section_owner_keys": hip_root_section_owner_keys,
                    "source_owner_keys": hip_root_source_owner_keys,
                    "pelvis_section_names": ["lower-pelvis", "lower-pelvis"],
                    "authored_station_names": ["thigh-start", "thigh-start"],
                    "boundary_parameters": hip_root_boundary_parameters,
                    "socket_parameters": hip_root_socket_parameters,
                    "tangent_blend_distances": hip_root_tangent_blend_distances,
                    "derived_from": hip_root_derived_from,
                    "controls": dict(HIP_ROOT_CONTROLS),
                    "volume_radii": hip_root_volume_radii,
                }
                limbs = {"representation": "shared-guide-derived-authored-arm-and-leg-profile-routes", "sweeps_consumed": len(LIMB_ORDER), "sweep_order": list(LIMB_ORDER), "route_kinds": ["arm-profile", "arm-profile", "arm-profile", "arm-profile", "leg-profile", "leg-profile"], "station_counts": [len(names) for names in LIMB_STATION_NAMES], "station_names": [list(names) for names in LIMB_STATION_NAMES], "section_owner_keys": limb_owner_keys, "station_owner_keys": limb_owner_keys, "endpoint_cap_counts": [2] * len(LIMB_ORDER), "arm_profile": arm_profile, "leg_profile": leg_profile, "hip_root": hip_root, "foot_profile": foot_profile}
                paw_owners = {(side, role): source_owner(descriptors, role, [side]) for side in ("left", "right") for role in ("hand", "foot")}
                hand_paw_sides = []
                for side in ("left", "right"):
                    side_sign = -1.0 if side == "left" else 1.0
                    hand_owner = paw_owners[(side, "hand")]
                    stations = []
                    for index, (offset, up_scale, forward_scale) in enumerate(HAND_PAW_PROFILE):
                        stations.append({
                            "name": HAND_PAW_SECTION_NAMES[index],
                            "section_index": index,
                            "owner": hand_owner,
                            "center": [side_sign * 1.3 + offset * 0.5 * side_sign, -0.9, 0.0],
                            "volume_axes": [[side_sign, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]],
                            "volume_radii": [0.5, 0.5 * up_scale, 0.5 * forward_scale],
                        })
                    hand_paw_sides.append({
                        "side": side,
                        "route": f"{side}-hand-paw",
                        "route_kind": "hand-paw",
                        "station_count": len(stations),
                        "owner_roles": ["hand"] * len(stations),
                        "stations": stations,
                    })
                hand_paw = {
                    "representation": "four-station-full-volume-hand-paw-sweeps",
                    "operation": HAND_PAW_OPERATION,
                    "route_order": [item["route"] for item in hand_paw_sides],
                    "route_kinds": [item["route_kind"] for item in hand_paw_sides],
                    "section_names": list(HAND_PAW_SECTION_NAMES),
                    "owner_roles": ["hand"] * len(HAND_PAW_SECTION_NAMES),
                    "route_station_count": sum(item["station_count"] for item in hand_paw_sides),
                    "route_volume_axis_count": sum(len(station["volume_axes"]) for item in hand_paw_sides for station in item["stations"]),
                    "route_volume_radius_count": sum(len(station["volume_radii"]) for item in hand_paw_sides for station in item["stations"]),
                    "sides": hand_paw_sides,
                }
                extremity_owner_keys = []
                extremity_internal_transition_counts = []
                for side in ("left", "right"):
                    side_sign = -1.0 if side == "left" else 1.0
                    hand_centers = [[side_sign * 1.3 + offset * 0.5 * side_sign, -0.9, 0.0] for offset, _up_scale, _forward_scale in HAND_PAW_PROFILE]
                    hock_center = [side_sign * 1.0, -3.0, 1.0]
                    pad_center = [side_sign * 1.0, -3.6, 1.5]
                    toe_center = [side_sign * 1.0, -3.6, 1.72]
                    foot_centers = next(item["stations"] for item in foot_profile_sides if item["side"] == side)
                    foot_centers = [item["center"] for item in foot_centers]
                    extremity_owner_keys.extend([
                        [paw_owners[(side, "hand")]] * 2,
                        [paw_owners[(side, "hand")]] * 4,
                        [limb_owners[(side, "shin")]] + [paw_owners[(side, "foot")]] * 4,
                    ])
                    extremity_internal_transition_counts.extend([0, bend_count(hand_centers), bend_count(foot_centers)])
                extremities = {"representation": "shared-guide-derived-hand-and-digitigrade-foot-profile-sweeps", "sweeps_consumed": len(EXTREMITY_ORDER), "sweep_order": list(EXTREMITY_ORDER), "sweep_kinds": list(EXTREMITY_KINDS), "station_counts": [len(names) for names in EXTREMITY_STATION_NAMES], "station_names": [list(names) for names in EXTREMITY_STATION_NAMES], "section_owner_keys": extremity_owner_keys, "endpoint_cap_counts": [2] * len(EXTREMITY_ORDER), "internal_transition_counts": extremity_internal_transition_counts, "hand_paw": hand_paw}
                limb_source_owner_keys = []
                for section_owners in limbs["section_owner_keys"]:
                    sweep_sources = []
                    for section_owner in section_owners:
                        if section_owner not in sweep_sources:
                            sweep_sources.append(section_owner)
                    limb_source_owner_keys.extend(sweep_sources)
                tail_root_owner = source_owner(descriptors, "tail_root", ["tail"])
                tail_tip_owner = source_owner(descriptors, "tail_tip", ["tail"])
                tail_controls, tip_shared_endpoint = generated_tail_controls(tail_root_owner, tail_tip_owner)
                tail = {"representation": "shared-guide-derived-profile-sweep-elements", "elements_consumed": len(TAIL_ORDER), "element_order": list(TAIL_ORDER), "element_kinds": list(TAIL_KINDS), "section_counts": [len(names) for names in TAIL_SECTION_NAMES], "section_names": [list(names) for names in TAIL_SECTION_NAMES], "owner_keys": [tail_root_owner] * 3 + [tail_tip_owner] * 3, "endpoint_cap_counts": [2] * len(TAIL_ORDER), "internal_transition_counts": [0] * len(TAIL_ORDER), "controls": tail_controls, "tip_shared_endpoint": tip_shared_endpoint}
                metrics_region = {
                    "regional_guide_format": "creature-kernel.disposable-surface-preview-regional-guide.v11",
                    "torso_representation": TORSO_PROFILE_OPERATION,
                    "torso_profile_exponent": TORSO_SUPERELLIPSE_EXPONENT,
                    "torso_sections_consumed": len(torso_controls),
                    "torso_section_names": [item["name"] for item in torso_controls],
                    "torso_section_owner_keys": [item["owner"] for item in torso_controls],
                    "torso_section_controls": torso_controls,
                    "shoulder_representation": "authored-five-section-frame-aware-profile-sweeps",
                    "shoulder_sweeps_consumed": 2,
                    "shoulder_sweep_order": ["left-shoulder-envelope", "right-shoulder-envelope"],
                    "shoulder_sweep_section_counts": [5, 5],
                    "shoulder_sweep_section_names": [shoulder_section_names, shoulder_section_names],
                    "shoulder_sweep_section_owner_keys": shoulder_owner_keys,
                    "shoulder_sweep_controls": shoulder_controls,
                    "head_neck": head_neck,
                    "arm_profile": arm_profile,
                    "leg_profile": leg_profile,
                    "hip_root": hip_root,
                    "foot_profile": foot_profile,
                    "hand_paw": hand_paw,
                    "limb_representation": limbs["representation"],
                    "limb_sweeps_consumed": limbs["sweeps_consumed"],
                    "limb_sweep_order": limbs["sweep_order"],
                    "limb_sweep_route_kinds": limbs["route_kinds"],
                    "limb_sweep_station_counts": limbs["station_counts"],
                    "limb_sweep_station_names": limbs["station_names"],
                    "limb_sweep_section_owner_keys": limbs["section_owner_keys"],
                    "limb_sweep_station_owner_keys": limbs["station_owner_keys"],
                    "limb_sweep_endpoint_cap_counts": limbs["endpoint_cap_counts"],
                    "limb_sweep_internal_transition_counts": limb_internal_transition_counts,
                    "limb_source_owner_keys": limb_source_owner_keys,
                    "extremity_representation": extremities["representation"],
                    "extremity_sweeps_consumed": extremities["sweeps_consumed"],
                    "extremity_sweep_order": extremities["sweep_order"],
                    "extremity_sweep_kinds": extremities["sweep_kinds"],
                    "extremity_sweep_station_counts": extremities["station_counts"],
                    "extremity_sweep_station_names": extremities["station_names"],
                    "extremity_sweep_section_owner_keys": extremities["section_owner_keys"],
                    "extremity_sweep_endpoint_cap_counts": extremities["endpoint_cap_counts"],
                    "extremity_sweep_internal_transition_counts": extremity_internal_transition_counts,
                    "extremity_source_owner_keys": [paw_owners[("left", "hand")], paw_owners[("left", "hand")], limb_owners[("left", "shin")], paw_owners[("left", "foot")], paw_owners[("right", "hand")], paw_owners[("right", "hand")], limb_owners[("right", "shin")], paw_owners[("right", "foot")]],
                    "tail_representation": tail["representation"],
                    "tail_elements_consumed": tail["elements_consumed"],
                    "tail_element_order": tail["element_order"],
                    "tail_element_kinds": tail["element_kinds"],
                    "tail_element_section_counts": tail["section_counts"],
                    "tail_element_section_names": tail["section_names"],
                    "tail_element_owner_keys": tail["owner_keys"],
                    "tail_element_endpoint_cap_counts": tail["endpoint_cap_counts"],
                    "tail_element_internal_transition_counts": tail["internal_transition_counts"],
                    "tail_source_owner_keys": [tail_root_owner, tail_tip_owner],
                    "tail_element_controls": tail_controls,
                    "tail_tip_shared_endpoint": tip_shared_endpoint,
                    "replaced_baseline_field_count": 52,
                    "replaced_baseline_recipes": list(REPLACED),
                }
                sidecar = {
                    "format": SUCCESSOR_FORMAT,
                    "variant_id": variant_id,
                    "profile_id": variant_id,
                    "source_variant_sha256": source_variant_sha256,
                    "consumer_id": CONSUMER_ID,
                    "successor_region_id": REGION_ID,
                    "capture": frame,
                    "torso": {"representation": TORSO_PROFILE_OPERATION, "regional_guide_format": "creature-kernel.disposable-surface-preview-regional-guide.v11", "superellipse_exponent": TORSO_SUPERELLIPSE_EXPONENT, "sections_consumed": 7, "section_names": [item["name"] for item in torso_controls], "section_controls": torso_controls},
                    "shoulders": {"representation": "authored-five-section-frame-aware-profile-sweeps", "sweeps_consumed": 2, "sweep_order": ["left-shoulder-envelope", "right-shoulder-envelope"], "section_counts": [5, 5], "section_names": [shoulder_section_names, shoulder_section_names]},
                    "head_neck": head_neck,
                    "limbs": limbs,
                    "extremities": extremities,
                    "tail": tail,
                    "temporary_bridge": bridge,
                    "replaced_baseline_recipes": replaced,
                }
                metrics = {"consumer_id": CONSUMER_ID, "successor_region_id": REGION_ID, "successor_region": metrics_region, "temporary_bridge": bridge, "vertex_count": 4, "face_count": 4, "component_count": 1, "watertight": True, "finite_vertices": True, "finite_normals": True, "valid_indices": True}
                component_recipes = [
                    "successor-torso-loft", "successor-vertical-neck-cranium", "successor-forward-muzzle",
                    "successor-left-upper-arm-route", "successor-left-forearm-route", "successor-right-upper-arm-route", "successor-right-forearm-route",
                    "successor-left-leg", "successor-right-leg", "successor-left-hand-attachment", "successor-left-hand-paw", "successor-left-foot",
                    "successor-right-hand-attachment", "successor-right-hand-paw", "successor-right-foot", "successor-tail-root-source",
                    "successor-tail-root-attachment", "successor-tail-root-collar", "successor-tail-tip-source", "successor-tail-tip-extension",
                    "successor-tail-tip-cap", "successor-left-shoulder-envelope", "successor-right-shoulder-envelope",
                    "successor-left-hip-root-transition", "successor-right-hip-root-transition",
                ]
                component_visualization = {
                    **COMPONENT_VISUALIZATION_METRICS,
                    "component_count": 25,
                    "components": [{"source_owner": descriptors[index % len(descriptors)]["address"], "recipe": recipe, "bounds": {"min": [-1.0, -1.0, -1.0], "max": [1.0, 1.0, 1.0]}} for index, recipe in enumerate(component_recipes)],
                }
                if MODE == "metrics-wrong-topology":
                    metrics.update({"vertex_count": 8, "face_count": 8, "component_count": 1, "watertight": True, "finite_vertices": True, "finite_normals": True, "valid_indices": True})
                if MODE == "sidecar-identity":
                    sidecar["consumer_id"] = "wrong-consumer"
                elif MODE == "sidecar-bridge":
                    sidecar["temporary_bridge"] = {**bridge, "field_count": 7}
                elif MODE == "sidecar-stale-v15-bridge":
                    sidecar["temporary_bridge"] = {"enabled": True, "consumer": "baseline-analytic-fields", "regions": ["thigh-root-connectors", "hip-transitions"], "field_count": 4, "retained_recipes": ["hip-transition", "root-bridge"]}
                elif MODE == "sidecar-stale-v2":
                    sidecar["format"] = "creature-kernel.disposable-successor-surface-preview.v2"
                elif MODE == "sidecar-old-shoulder":
                    sidecar["shoulders"] = {"representation": "distal-deltoid-swept-curve-spans", "spans_consumed": 2, "curve": "deltoid-sweep", "span_index": 1}
                elif MODE == "sidecar-stale-region-id":
                    sidecar["successor_region_id"] = "successor-torso-shoulder-head-neck-limb-extremity-tail-profile-sweeps-v6"
                elif MODE == "sidecar-extremity":
                    sidecar["extremities"] = {**sidecar["extremities"], "sweeps_consumed": 5}
                elif MODE == "sidecar-extremity-order":
                    sidecar["extremities"] = {**sidecar["extremities"], "sweep_order": list(reversed(sidecar["extremities"]["sweep_order"]))}
                elif MODE == "sidecar-extremity-kind":
                    sidecar["extremities"] = {**sidecar["extremities"], "sweep_kinds": ["wrong", *sidecar["extremities"]["sweep_kinds"][1:]]}
                elif MODE == "sidecar-tail":
                    sidecar["tail"] = {**sidecar["tail"], "elements_consumed": 5}
                elif MODE == "sidecar-tail-shared-endpoint":
                    sidecar["tail"] = {**sidecar["tail"], "tip_shared_endpoint": {**sidecar["tail"]["tip_shared_endpoint"], "point": [0.6, 0.0, 0.0]}}
                elif MODE == "sidecar-shoulder-span-type":
                    sidecar["shoulders"] = {**sidecar["shoulders"], "span_index": True}
                elif MODE == "sidecar-missing-deltoid-replacement":
                    sidecar["replaced_baseline_recipes"] = [recipe for recipe in replaced if recipe != "deltoid-sweep-1"]
                elif MODE == "sidecar-missing-hip-replacement":
                    sidecar["replaced_baseline_recipes"] = [recipe for recipe in replaced if recipe != "hip-transition"]
                elif MODE == "sidecar-hip-root":
                    sidecar["limbs"] = {**sidecar["limbs"], "hip_root": {**sidecar["limbs"]["hip_root"], "operation": "stale-hip-root-operation"}}
                elif MODE == "sidecar-torso-owner":
                    pelvis_owner = next(item["address"] for item in descriptors if item["address"]["role"] == "pelvis" and item["address"]["anchors"] == [])
                    sidecar["torso"] = {**sidecar["torso"], "section_controls": [*sidecar["torso"]["section_controls"][:2], {**sidecar["torso"]["section_controls"][2], "owner": pelvis_owner}, *sidecar["torso"]["section_controls"][3:]]}
                elif MODE == "sidecar-torso-radius":
                    sidecar["torso"] = {**sidecar["torso"], "section_controls": [*sidecar["torso"]["section_controls"][:2], {**sidecar["torso"]["section_controls"][2], "lateral_radius": sidecar["torso"]["section_controls"][2]["lateral_radius"] + 0.01}, *sidecar["torso"]["section_controls"][3:]]}
                elif MODE == "sidecar-torso-exponent":
                    sidecar["torso"] = {**sidecar["torso"], "superellipse_exponent": 4.0}
                elif MODE == "sidecar-head-section":
                    sections = list(sidecar["head_neck"]["sections"])
                    sections[0] = {**sections[0], "owner": head_owner}
                    sidecar["head_neck"] = {**sidecar["head_neck"], "sections": sections}
                elif MODE == "sidecar-head-connection":
                    connections = list(sidecar["head_neck"]["connections"])
                    connections[4] = {**connections[4], "route": "vertical-neck-cranium"}
                    sidecar["head_neck"] = {**sidecar["head_neck"], "connections": connections}
                elif MODE == "sidecar-head-route-topology":
                    routes = list(sidecar["head_neck"]["route_topology"])
                    routes[0] = {**routes[0], "section_indices": [0, 1, 2, 4, 3]}
                    sidecar["head_neck"] = {**sidecar["head_neck"], "route_topology": routes}
                elif MODE == "sidecar-head-derived-composition":
                    routes = copy.deepcopy(sidecar["head_neck"]["route_topology"])
                    routes[1]["derived_compositions"][0]["centers"][0][0] += 0.1
                    sidecar["head_neck"] = {**sidecar["head_neck"], "route_topology": routes}
                elif MODE == "sidecar-arm-route-order":
                    sidecar["limbs"] = {**sidecar["limbs"], "sweep_order": list(reversed(sidecar["limbs"]["sweep_order"]))}
                elif MODE == "sidecar-arm-route-owner":
                    routes = list(sidecar["limbs"]["arm_profile"]["routes"])
                    routes[0] = {**routes[0], "owner_keys": [limb_owners[("left", "forearm")]] * 3}
                    sidecar["limbs"] = {**sidecar["limbs"], "arm_profile": {**sidecar["limbs"]["arm_profile"], "routes": routes}}
                elif MODE == "sidecar-arm-elbow-ownership":
                    sidecar["limbs"] = {**sidecar["limbs"], "arm_profile": {**sidecar["limbs"]["arm_profile"], "elbow_ownership": "forearm"}}
                elif MODE == "sidecar-arm-lineage":
                    profile = sidecar["limbs"]["arm_profile"]
                    stations = list(profile["stations"])
                    sections = list(stations[0]["sections"])
                    sections[2] = {**sections[2], "lineage": {**sections[2]["lineage"], "lateral": {**sections[2]["lineage"]["lateral"], "scaled": sections[2]["lineage"]["lateral"]["scaled"] + 1}}}
                    stations[0] = {**stations[0], "sections": sections}
                    sidecar["limbs"] = {**sidecar["limbs"], "arm_profile": {**profile, "stations": stations}}
                elif MODE == "sidecar-leg-route-order":
                    profile = sidecar["limbs"]["leg_profile"]
                    sidecar["limbs"] = {**sidecar["limbs"], "leg_profile": {**profile, "route_order": list(reversed(profile["route_order"]))}}
                elif MODE == "sidecar-leg-owner":
                    profile = sidecar["limbs"]["leg_profile"]
                    sides = list(profile["sides"])
                    stations = list(sides[0]["stations"])
                    stations[3] = {**stations[3], "owner": limb_owners[("left", "thigh")]}
                    sides[0] = {**sides[0], "stations": stations}
                    sidecar["limbs"] = {**sidecar["limbs"], "leg_profile": {**profile, "sides": sides}}
                elif MODE == "sidecar-leg-lineage":
                    profile = sidecar["limbs"]["leg_profile"]
                    sides = list(profile["sides"])
                    stations = list(sides[0]["stations"])
                    station = stations[2]
                    stations[2] = {**station, "lineage": {**station["lineage"], "lateral": {**station["lineage"]["lateral"], "scaled": station["lineage"]["lateral"]["scaled"] + 1}}}
                    sides[0] = {**sides[0], "stations": stations}
                    sidecar["limbs"] = {**sidecar["limbs"], "leg_profile": {**profile, "sides": sides}}
                elif MODE == "sidecar-foot-order":
                    profile = sidecar["limbs"]["foot_profile"]
                    sides = list(profile["sides"])
                    stations = list(sides[0]["stations"])
                    stations[1], stations[2] = stations[2], stations[1]
                    sides[0] = {**sides[0], "stations": stations}
                    sidecar["limbs"] = {**sidecar["limbs"], "foot_profile": {**profile, "sides": sides}}
                elif MODE == "sidecar-foot-lineage":
                    profile = sidecar["limbs"]["foot_profile"]
                    sides = list(profile["sides"])
                    stations = list(sides[0]["stations"])
                    station = stations[2]
                    lineage = dict(station["lineage"])
                    radii = dict(lineage["radii"])
                    radii["lateral"] = {**radii["lateral"], "scaled": radii["lateral"]["scaled"] + 1}
                    lineage["radii"] = radii
                    stations[2] = {**station, "lineage": lineage}
                    sides[0] = {**sides[0], "stations": stations}
                    sidecar["limbs"] = {**sidecar["limbs"], "foot_profile": {**profile, "sides": sides}}
                elif MODE == "sidecar-hand-paw":
                    hand_paw = {**sidecar["extremities"]["hand_paw"], "route_station_count": 7}
                    sidecar["extremities"] = {**sidecar["extremities"], "hand_paw": hand_paw}
                elif MODE.startswith("sidecar-hand-paw-"):
                    hand_paw = copy.deepcopy(sidecar["extremities"]["hand_paw"])
                    station = hand_paw["sides"][0]["stations"][0]
                    if MODE == "sidecar-hand-paw-axis":
                        station["volume_axes"][0][0] = -station["volume_axes"][0][0]
                    elif MODE == "sidecar-hand-paw-center":
                        station["center"][1] += 0.1
                    elif MODE == "sidecar-hand-paw-radius":
                        station["volume_radii"][2] += 0.1
                    elif MODE == "sidecar-hand-paw-owner":
                        station["owner"] = hand_paw["sides"][1]["stations"][0]["owner"]
                    sidecar["extremities"] = {**sidecar["extremities"], "hand_paw": hand_paw}
                (variant_dir / "successor.json").write_text(json.dumps(sidecar, sort_keys=True), encoding="utf-8")
                metrics_file = dict(metrics)
                if MODE == "metrics-disagreement":
                    metrics_file["successor_region"] = {**metrics["successor_region"], "tail_elements_consumed": 5}
                elif MODE == "metrics-shoulder-span-type":
                    metrics_file["successor_region"] = {**metrics["successor_region"], "shoulder_sweep_section_counts": [5, 5, 5]}
                elif MODE == "metrics-shoulder-center":
                    controls = list(metrics["successor_region"]["shoulder_sweep_controls"])
                    controls[0] = {**controls[0], "authored_center": [0.0, 0.0, 0.0]}
                    metrics_file["successor_region"] = {**metrics["successor_region"], "shoulder_sweep_controls": controls}
                elif MODE == "metrics-shoulder-depth":
                    controls = list(metrics["successor_region"]["shoulder_sweep_controls"])
                    controls[0] = {**controls[0], "depth_radius": controls[0]["depth_radius"] + 0.001}
                    metrics_file["successor_region"] = {**metrics["successor_region"], "shoulder_sweep_controls": controls}
                elif MODE == "metrics-shoulder-owner":
                    owner_keys = list(metrics["successor_region"]["shoulder_sweep_section_owner_keys"])
                    owner_keys[0] = [owner_keys[0][0], owner_keys[0][1], owner_keys[0][1], owner_keys[0][3], owner_keys[0][4]]
                    metrics_file["successor_region"] = {**metrics["successor_region"], "shoulder_sweep_section_owner_keys": owner_keys}
                elif MODE == "metrics-torso-sidecar-disagreement":
                    controls = list(metrics["successor_region"]["torso_section_controls"])
                    controls[0] = {**controls[0], "posterior_radius": controls[0]["posterior_radius"] + 0.01}
                    metrics_file["successor_region"] = {**metrics["successor_region"], "torso_section_controls": controls}
                elif MODE == "metrics-torso-exponent":
                    metrics_file["successor_region"] = {**metrics["successor_region"], "torso_profile_exponent": 4.0}
                elif MODE == "metrics-torso-owner":
                    owners = list(metrics["successor_region"]["torso_section_owner_keys"])
                    owners[2] = owners[0]
                    metrics_file["successor_region"] = {**metrics["successor_region"], "torso_section_owner_keys": owners}
                elif MODE == "metrics-head-cross-binding":
                    head_metadata = dict(metrics["successor_region"]["head_neck"])
                    head_metadata["provenance"] = {"source": "cross-boundary", "document": "fixture", "namespace": "main"}
                    metrics_file["successor_region"] = {**metrics["successor_region"], "head_neck": head_metadata}
                elif MODE == "metrics-limb-source-owner":
                    owners = list(metrics["successor_region"]["limb_source_owner_keys"])
                    owners[1] = limb_owners[("left", "forearm")]
                    metrics_file["successor_region"] = {**metrics["successor_region"], "limb_source_owner_keys": owners}
                elif MODE == "metrics-leg-cross-binding":
                    owners = list(metrics["successor_region"]["limb_sweep_station_owner_keys"])
                    owners[4] = [limb_owners[("left", "thigh")]] * 5
                    metrics_file["successor_region"] = {**metrics["successor_region"], "limb_sweep_station_owner_keys": owners}
                elif MODE == "metrics-hip-root":
                    hip_metadata = {**metrics["successor_region"]["hip_root"], "route_order": ["right-hip-root-transition", "left-hip-root-transition"]}
                    metrics_file["successor_region"] = {**metrics["successor_region"], "hip_root": hip_metadata}
                elif MODE == "metrics-replaced-count":
                    metrics_file["successor_region"] = {**metrics["successor_region"], "replaced_baseline_field_count": 48}
                elif MODE == "metrics-foot-profile":
                    foot_profile_metadata = dict(metrics["successor_region"]["foot_profile"])
                    foot_profile_metadata["route_order"] = list(reversed(foot_profile_metadata["route_order"]))
                    metrics_file["successor_region"] = {**metrics["successor_region"], "foot_profile": foot_profile_metadata}
                elif MODE == "metrics-hand-paw":
                    hand_paw = {**metrics["successor_region"]["hand_paw"], "route_station_count": 7}
                    metrics_file["successor_region"] = {**metrics["successor_region"], "hand_paw": hand_paw}
                if MODE.startswith("component-"):
                    components = [dict(item) for item in component_visualization["components"]]
                    if MODE == "component-missing": components.pop()
                    elif MODE == "component-extra": components.append(dict(components[-1]))
                    elif MODE == "component-unknown-owner": components[0]["source_owner"] = {**descriptors[0]["address"], "role": "unknown"}
                    elif MODE == "component-wrong-recipe": components[0]["recipe"] = "wrong-recipe"
                    elif MODE == "component-wrong-histogram": components[-1]["recipe"] = components[-3]["recipe"]
                    elif MODE == "component-malformed-bounds": components[0]["bounds"] = {"min": [-1.0, -1.0], "max": [1.0, 1.0, 1.0]}
                    elif MODE == "component-out-of-range-bounds": components[0]["bounds"] = {"min": [-101.0, -1.0, -1.0], "max": [1.0, 1.0, 1.0]}
                    elif MODE == "component-reversed-bounds": components[0]["bounds"] = {"min": [1.0, 1.0, 1.0], "max": [-1.0, -1.0, -1.0]}
                    component_visualization["components"] = components
                metrics_file["component_visualization"] = component_visualization
                metrics_record = metrics_file
                (variant_dir / "metrics.json").write_text(json.dumps(metrics_file, sort_keys=True), encoding="utf-8")
                png = variant_dir / "guide-skin-composite.png"
                png.write_bytes(PNG)
                def entry(kind, artifact, extra=None):
                    data = artifact.read_bytes()
                    result = {"kind": kind, "path": artifact.relative_to(out).as_posix(), "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}
                    if extra:
                        result.update(extra)
                    return result
                inventory = [
                    entry("ply", variant_dir / "surface.ply"),
                    entry("semantic-sidecar", variant_dir / "semantic.json"),
                    entry("metrics", variant_dir / "metrics.json"),
                    entry("successor-consumer-sidecar", variant_dir / "successor.json"),
                    entry("guide-skin-composite-png", png, {"width": 1800, "height": 1500, "views": ["front", "side", "three-quarter"], "panels_per_view": (2 if MODE == "stale-panels" else 3), "mode": "RGB"}),
                ]
                if MODE == "inventory":
                    inventory[0] = {**inventory[0], "path": variant_id + "/wrong.ply"}
                if MODE == "hash":
                    inventory[0] = {**inventory[0], "sha256": "0" * 64}
                if MODE == "invalid-png":
                    png.write_bytes(PNG[:-1])
                    inventory[-1] = entry("guide-skin-composite-png", png, {"width": 1800, "height": 1500, "views": ["front", "side", "three-quarter"], "panels_per_view": (2 if MODE == "stale-panels" else 3), "mode": "RGB"})
                records.append({"id": variant_id, "profile_id": ("wrong" if MODE == "variant-profile" and not records else variant_id), "source_variant_sha256": source_variant_sha256, "metrics": metrics_record, "inventory": inventory})
            if MODE == "variant":
                records.pop()
            if MODE == "extra-path":
                (out / "extra.bin").write_bytes(b"unlisted")
            manifest_canvas = frame["canvas"]
            manifest_layout = frame["layout"]
            manifest_format = SUCCESSOR_FORMAT
            if MODE == "stale-canvas": manifest_canvas = {"width": 1800, "height": 570, "mode": "RGB"}
            if MODE == "stale-layout": manifest_layout = {"panel_order": ["front-guide", "front-skin", "side-guide", "side-skin", "three-quarter-guide", "three-quarter-skin"], "panels": [{"id": "front-guide", "projection": "front", "content": "guide", "box": [12, 72, 292, 548]}, {"id": "front-skin", "projection": "front", "content": "skin", "box": [310, 72, 590, 548]}, {"id": "side-guide", "projection": "side", "content": "guide", "box": [608, 72, 888, 548]}, {"id": "side-skin", "projection": "side", "content": "skin", "box": [906, 72, 1186, 548]}, {"id": "three-quarter-guide", "projection": "three-quarter", "content": "guide", "box": [1204, 72, 1484, 548]}, {"id": "three-quarter-skin", "projection": "three-quarter", "content": "skin", "box": [1502, 72, 1782, 548]}], "pairing": "guide-left/skin-right per projection", "frame": "shared-world-bounds-and-projection-basis"}
            if MODE == "stale-format": manifest_format = "creature-kernel.disposable-successor-surface-preview.v8"
            generator = {"samples_per_axis": 56, "padding": MESH_PADDING, "capture_padding": CAPTURE_PADDING, "smooth_k": 0.12, "consumer_boundary": "successor torso/shoulder/head/neck, authored arm and leg profile routes, bilateral pelvis-to-thigh socket/cup transitions, bilateral hands, digitigrade feet, and tail", "production_status": "disposable exploratory proof", "component_visualization": COMPONENT_VISUALIZATION}
            if MODE == "component-visualization-omitted": generator.pop("component_visualization")
            if MODE == "component-visualization-tampered": generator["component_visualization"] = {**COMPONENT_VISUALIZATION, "samples_per_axis": 31}
            manifest = {"format": manifest_format, "status": "success", "consumer_id": CONSUMER_ID, "source_format": payload["format"], "source": source, "shared_render_bounds": frame["shared_render_bounds"], "canvas": manifest_canvas, "layout": manifest_layout, "projections": frame["projections"], "generator": generator, "variants": records}
            (out / "successor-surface-manifest.json").write_text(json.dumps(manifest, sort_keys=True, separators=(",", ":")), encoding="utf-8")
        """)
        replacements = {
            "__MODE__": repr(mode),
            "__PNG__": repr(self._png()),
            "__CANVAS__": repr(publisher.EXPECTED_CANVAS),
            "__PROJECTIONS__": repr(publisher.EXPECTED_PROJECTIONS),
            "__LAYOUT__": repr(publisher.EXPECTED_LAYOUT),
            "__BOUNDS__": repr({"min": [-5.0, -5.0, -5.0], "max": [5.0, 5.0, 5.0]}),
            "__EXPANDED_BOUNDS__": repr({"min": [-6.0, -6.0, -6.0], "max": [6.0, 6.0, 6.0]}),
            "__SUCCESSOR_FORMAT__": repr(INDEPENDENT_SUCCESSOR_FIXTURE["format"]),
            "__CONSUMER_ID__": repr(INDEPENDENT_SUCCESSOR_FIXTURE["consumer_id"]),
            "__REGION_ID__": repr(INDEPENDENT_SUCCESSOR_FIXTURE["region_id"]),
            "__EXTREMITY_ORDER__": repr(list(INDEPENDENT_SUCCESSOR_FIXTURE["extremity_order"])),
            "__EXTREMITY_KINDS__": repr(list(INDEPENDENT_SUCCESSOR_FIXTURE["extremity_kinds"])),
            "__HEAD_NECK_ORDER__": repr(list(INDEPENDENT_SUCCESSOR_FIXTURE["head_neck_order"])),
            "__HEAD_NECK_SECTION_COUNTS__": repr(list(INDEPENDENT_SUCCESSOR_FIXTURE["head_neck_section_counts"])),
            "__LIMB_ORDER__": repr(list(INDEPENDENT_SUCCESSOR_FIXTURE["limb_order"])),
            "__LIMB_STATION_NAMES__": repr([list(names) for names in INDEPENDENT_SUCCESSOR_FIXTURE["limb_station_names"]]),
            "__EXTREMITY_STATION_NAMES__": repr([list(names) for names in INDEPENDENT_SUCCESSOR_FIXTURE["extremity_station_names"]]),
            "__HAND_PAW_PROFILE__": repr(list(INDEPENDENT_SUCCESSOR_FIXTURE["hand_paw_profile"])),
            "__HAND_PAW_SECTION_NAMES__": repr(list(INDEPENDENT_SUCCESSOR_FIXTURE["hand_paw_section_names"])),
            "__FOOT_PROFILE_SECTION_NAMES__": repr(list(INDEPENDENT_SUCCESSOR_FIXTURE["foot_section_names"])),
            "__FOOT_PROFILE_OWNER_ROLES__": repr(list(INDEPENDENT_SUCCESSOR_FIXTURE["foot_owner_roles"])),
            "__HAND_PAW_OPERATION__": repr(INDEPENDENT_SUCCESSOR_FIXTURE["operations"]["hand_paw"]),
            "__TORSO_PROFILE_OPERATION__": repr(INDEPENDENT_SUCCESSOR_FIXTURE["operations"]["torso"]),
            "__HEAD_NECK_PROFILE_OPERATION__": repr(INDEPENDENT_SUCCESSOR_FIXTURE["operations"]["head_neck"]),
            "__ARM_PROFILE_OPERATION__": repr(INDEPENDENT_SUCCESSOR_FIXTURE["operations"]["arm"]),
            "__LEG_PROFILE_OPERATION__": repr(INDEPENDENT_SUCCESSOR_FIXTURE["operations"]["leg"]),
            "__FOOT_PROFILE_OPERATION__": repr(INDEPENDENT_SUCCESSOR_FIXTURE["operations"]["foot"]),
            "__FORWARD_MUZZLE_COMPOSITION_OPERATION__": repr(INDEPENDENT_SUCCESSOR_FIXTURE["operations"]["forward_muzzle"]),
            "__FORWARD_MUZZLE_GEOMETRIC_INPUT_SECTION_INDICES__": repr(list(INDEPENDENT_SUCCESSOR_FIXTURE["forward_muzzle_geometric_indices"])),
            "__FORWARD_MUZZLE_RADIUS_DONOR_SECTION_INDICES__": repr(list(INDEPENDENT_SUCCESSOR_FIXTURE["forward_muzzle_radius_donor_indices"])),
            "__TORSO_SUPERELLIPSE_EXPONENT__": repr(3.0),
            "__HIP_ROOT_OPERATION__": repr(INDEPENDENT_SUCCESSOR_FIXTURE["operations"]["hip_root"]),
            "__HIP_ROOT_CONTROLS__": repr(INDEPENDENT_SUCCESSOR_FIXTURE["hip_root_controls"]),
            "__TAIL_ORDER__": repr(list(INDEPENDENT_SUCCESSOR_FIXTURE["tail_order"])),
            "__TAIL_KINDS__": repr(list(INDEPENDENT_SUCCESSOR_FIXTURE["tail_kinds"])),
            "__TAIL_SECTION_NAMES__": repr([list(names) for names in INDEPENDENT_SUCCESSOR_FIXTURE["tail_section_names"]]),
            "__REPLACED__": repr(list(INDEPENDENT_SUCCESSOR_FIXTURE["replaced"])),
            "__MESH_PADDING__": repr(0.5),
            "__CAPTURE_PADDING__": repr(0.5 if mode == "capture-padding-mismatch" else 0.75),
            "__COMPONENT_VISUALIZATION__": repr(publisher.EXPECTED_COMPONENT_VISUALIZATION),
            "__COMPONENT_VISUALIZATION_METRICS__": repr(publisher.EXPECTED_COMPONENT_VISUALIZATION_METRICS),
            "__VALID_PLY__": repr(self._tetra_ply()),
            "__DISCONNECTED_PLY__": repr(self._tetra_ply(copies=2)),
            "__NONWATERTIGHT_PLY__": repr(self._tetra_ply(missing_last_face=True)),
            "__DUPLICATE_FACE_PLY__": repr(self._tetra_ply(duplicate_face=True)),
            "__INCONSISTENT_ORIENTATION_PLY__": repr(self._tetra_ply(inconsistent_orientation=True)),
            "__ZERO_VOLUME_PLY__": repr(self._tetra_ply(flattened_height=0.0)),
            "__FLATTENED_PLY__": repr(self._tetra_ply(flattened_height=1.0e-13)),
        }
        for placeholder, value in replacements.items():
            script = script.replace(placeholder, value)
        path.write_text(script, encoding="utf-8")
        path.chmod(0o755)
        return path

    def _payload(self) -> dict[str, object]:
        owner_specs = [("pelvis", []), ("torso", []), ("neck", []), ("head", []), ("upper_arm", ["left"]), ("forearm", ["left"]), ("hand", ["left"]), ("upper_arm", ["right"]), ("forearm", ["right"]), ("hand", ["right"]), ("thigh", ["left"]), ("shin", ["left"]), ("foot", ["left"]), ("thigh", ["right"]), ("shin", ["right"]), ("foot", ["right"]), ("tail_root", ["tail"]), ("tail_tip", ["tail"])]
        owners = [{"namespace": "main", "anchors": anchors, "kind": "part", "role": role} for role, anchors in owner_specs]
        source = {"document": "fixture", "namespace": "main", "resource_profile_id": common.PROVISIONAL_FORM_RESOURCE_PROFILE}
        reference_scale = {"parent": owners[2], "child": owners[3], "axis_delta": [0, 1, 0], "squared_length": 1, "source": "exact-containment-edge"}
        dimension_roles = {
            "pelvis": ["form_extent_x", "form_extent_y", "form_extent_z"],
            "torso": ["form_extent_x", "form_extent_y", "form_extent_z"],
            "neck": ["form_radius"],
            "head": ["form_extent_x", "form_extent_y", "form_extent_z"],
            "upper_arm": ["form_radius", "form_shoulder_depth_radius"],
            "forearm": ["form_radius"],
            "hand": ["form_extent_x", "form_extent_y", "form_extent_z"],
            "thigh": ["form_radius"],
            "shin": ["form_radius"],
            "foot": ["form_extent_x", "form_extent_y", "form_extent_z"],
            "tail_root": ["form_start_radius", "form_end_radius"],
            "tail_tip": ["form_start_radius", "form_end_radius"],
        }
        dimensions = []
        for owner in owners:
            for role in dimension_roles[owner["role"]]:
                dimensions.append({
                    "owner": owner,
                    "role": role,
                    "value_permille": 100,
                    "provenance": {
                        "source": common.PROVISIONAL_FORM_AUTHORED_DIMENSION_PROVENANCE,
                        "document": source["document"],
                        "namespace": source["namespace"],
                    },
                })
        dimensions.sort(key=lambda item: (
            item["owner"]["namespace"], tuple(item["owner"]["anchors"]),
            item["owner"]["kind"], item["owner"]["role"], item["role"],
        ))
        torso_values = {
            "lower-pelvis": ("pelvis", -0.8, (600, 500, 450)),
            "upper-pelvis": ("pelvis", -0.45, (550, 460, 420)),
            "lower-abdomen": ("torso", -0.35, (420, 380, 350)),
            "waist-abdomen": ("torso", -0.1, (360, 330, 300)),
            "upper-abdomen": ("torso", 0.15, (420, 380, 350)),
            "lower-ribcage": ("torso", 0.4, (500, 450, 420)),
            "upper-ribcage-shoulder": ("torso", 0.7, (580, 520, 490)),
        }
        torso_sections = []
        for name, (owner_role, y, radii) in torso_values.items():
            owner = next(item for item in owners if item["role"] == owner_role and item["anchors"] == [])
            section_key = name.replace("-", "_")
            for suffix, value in zip(("lateral_radius", "anterior_radius", "posterior_radius"), radii):
                dimensions.append({"owner": owner, "role": f"form_torso_profile_{section_key}_{suffix}", "value_permille": value, "provenance": {"source": common.PROVISIONAL_FORM_AUTHORED_DIMENSION_PROVENANCE, "document": source["document"], "namespace": source["namespace"]}})
            torso_sections.append((name, owner, y, radii))
        head_values = (
            ("neck-collar", "neck", 0.15, 0.00, (120, 110, 100)),
            ("neck-upper", "neck", 0.55, 0.00, (115, 105, 95)),
            ("head-base", "head", -0.35, 0.00, (180, 160, 150)),
            ("cranium-mid", "head", 0.05, 0.00, (220, 190, 180)),
            ("cranium-crown", "head", 0.40, 0.00, (200, 175, 165)),
            ("muzzle-root", "head", -0.10, 0.25, (150, 130, 120)),
            ("muzzle-mid", "head", -0.12, 0.55, (135, 115, 105)),
            ("muzzle-tip", "head", -0.12, 0.80, (100, 90, 80)),
        )
        head_sections = []
        for name, owner_role, y, z, radii in head_values:
            owner = next(item for item in owners if item["role"] == owner_role and item["anchors"] == [])
            section_key = name.replace("-", "_")
            for suffix, value in zip(("lateral_radius", "up_radius", "forward_radius"), radii):
                dimensions.append({"owner": owner, "role": f"form_head_neck_profile_{section_key}_{suffix}", "value_permille": value, "provenance": {"source": common.PROVISIONAL_FORM_AUTHORED_DIMENSION_PROVENANCE, "document": source["document"], "namespace": source["namespace"]}})
            head_sections.append((name, owner, [0.0, y, z], radii))
        arm_sections = {}
        for side in ("left", "right"):
            for index, (name, owner_role, y, radii) in enumerate(zip(
                common.PROVISIONAL_FORM_ARM_PROFILE_SECTION_NAMES,
                common.PROVISIONAL_FORM_ARM_PROFILE_OWNER_ROLES,
                (0.0, -0.5, -1.0, -0.5, -1.0),
                ((240, 220, 200), (220, 205, 185), (200, 190, 170), (190, 180, 160), (175, 165, 150)),
            )):
                owner = next(item for item in owners if item["role"] == owner_role and item["anchors"] == [side])
                section_key = name.replace("-", "_")
                for suffix, value in zip(("lateral_radius", "up_radius", "forward_radius"), radii):
                    dimensions.append({"owner": owner, "role": f"form_arm_profile_{section_key}_{suffix}", "value_permille": value, "provenance": {"source": common.PROVISIONAL_FORM_AUTHORED_DIMENSION_PROVENANCE, "document": source["document"], "namespace": source["namespace"]}})
                arm_sections[(side, index)] = (name, owner, y, radii)
        leg_sections = {}
        for side in ("left", "right"):
            for index, (name, owner_role, y, z, radii) in enumerate(zip(
                common.PROVISIONAL_FORM_LEG_PROFILE_SECTION_NAMES,
                common.PROVISIONAL_FORM_LEG_PROFILE_OWNER_ROLES,
                (0.0, -0.5, -1.0, -0.5, -1.0),
                (0.0, 0.0, 0.0, 0.0, 0.0),
                ((320, 280, 300), (300, 260, 280), (240, 210, 225), (225, 195, 210), (185, 165, 175)),
            )):
                owner = next(item for item in owners if item["role"] == owner_role and item["anchors"] == [side])
                section_key = name.replace("-", "_")
                for suffix, value in zip(("lateral_radius", "up_radius", "forward_radius"), radii):
                    dimensions.append({"owner": owner, "role": f"form_leg_profile_{section_key}_{suffix}", "value_permille": value, "provenance": {"source": common.PROVISIONAL_FORM_AUTHORED_DIMENSION_PROVENANCE, "document": source["document"], "namespace": source["namespace"]}})
                leg_sections[(side, index)] = (name, owner, [0.0, y, z], radii)
        foot_sections = {}
        for side in ("left", "right"):
            owner = next(item for item in owners if item["role"] == "foot" and item["anchors"] == [side])
            for index, (name, position, radii) in enumerate(zip(
                common.PROVISIONAL_FORM_FOOT_PROFILE_SECTION_NAMES,
                ([0.0, -0.6, 0.5], [0.0, -0.6, 0.72]),
                ((400, 200, 300), (350, 200, 250)),
            )):
                for suffix, value in zip(("lateral_radius", "up_radius", "forward_radius"), radii):
                    dimensions.append({"owner": owner, "role": f"form_foot_profile_{name}_{suffix}", "value_permille": value, "provenance": {"source": common.PROVISIONAL_FORM_AUTHORED_DIMENSION_PROVENANCE, "document": source["document"], "namespace": source["namespace"]}})
                foot_sections[(side, index)] = (name, owner, position, radii)
        dimensions.sort(key=lambda item: (
            item["owner"]["namespace"], tuple(item["owner"]["anchors"]),
            item["owner"]["kind"], item["owner"]["role"], item["role"],
        ))
        shoulder_controls = []
        for side, x in (("left", -0.1), ("right", 0.1)):
            owner = {"namespace": "main", "anchors": [side], "kind": "part", "role": "upper_arm"}
            provenance = {"source": common.PROVISIONAL_FORM_AUTHORED_CONTROL_PROVENANCE, "document": "fixture", "namespace": "main"}
            for role, y in (("form_axilla", -0.3), ("form_shoulder_peak", 0.15)):
                shoulder_controls.append({
                    "owner": owner,
                    "role": role,
                    "frame": {"owner": owner, "role": common.PROVISIONAL_FORM_SHOULDER_CONTROL_FRAME_ROLE},
                    "position": [x, y, 0.0],
                    "provenance": provenance,
                })
        frames = [
            {
                "owner": {"namespace": "main", "anchors": [side], "kind": "part", "role": "upper_arm"},
                "role": common.PROVISIONAL_FORM_SHOULDER_CONTROL_FRAME_ROLE,
                "transform": {"translation": [0.0, 0.0, 0.0], "rotation_xyzw": [0.0, 0.0, 0.0, 1.0]},
                "provenance": {"source": common.PROVISIONAL_FORM_AUTHORED_CONTROL_PROVENANCE, "document": "fixture", "namespace": "main"},
            }
            for side in ("left", "right")
        ] + [
            {
                "owner": next(item for item in owners if item["role"] == owner_role and item["anchors"] == []),
                "role": common.PROVISIONAL_FORM_TORSO_PROFILE_FRAME_ROLE,
                "transform": {"translation": [0.0, 0.0, 0.0], "rotation_xyzw": [0.0, 0.0, 0.0, 1.0]},
                "provenance": {"source": common.PROVISIONAL_FORM_AUTHORED_CONTROL_PROVENANCE, "document": source["document"], "namespace": source["namespace"]},
            }
            for owner_role in ("pelvis", "torso")
        ]
        frames.sort(key=lambda item: (
            item["owner"]["namespace"], tuple(item["owner"]["anchors"]),
            item["owner"]["kind"], item["owner"]["role"], item["role"],
        ))
        frames.extend([
            {
                "owner": next(item for item in owners if item["role"] == owner_role and item["anchors"] == []),
                "role": common.PROVISIONAL_FORM_HEAD_NECK_PROFILE_FRAME_ROLE,
                "transform": {"translation": [0.0, 0.0, 0.0], "rotation_xyzw": [0.0, 0.0, 0.0, 1.0]},
                "provenance": {"source": common.PROVISIONAL_FORM_AUTHORED_CONTROL_PROVENANCE, "document": source["document"], "namespace": source["namespace"]},
            }
            for owner_role in ("head", "neck")
        ])
        frames.extend([
            {
                "owner": next(item for item in owners if item["role"] == owner_role and item["anchors"] == [side]),
                "role": common.PROVISIONAL_FORM_ARM_PROFILE_FRAME_ROLE,
                "transform": {"translation": [0.0, 0.0, 0.0], "rotation_xyzw": [0.0, 0.0, 0.0, 1.0]},
                "provenance": {"source": common.PROVISIONAL_FORM_AUTHORED_CONTROL_PROVENANCE, "document": source["document"], "namespace": source["namespace"]},
            }
            for side in ("left", "right")
            for owner_role in ("upper_arm", "forearm")
        ])
        frames.extend([
            {
                "owner": next(item for item in owners if item["role"] == owner_role and item["anchors"] == [side]),
                "role": common.PROVISIONAL_FORM_LEG_PROFILE_FRAME_ROLE,
                "transform": {"translation": [0.0, 0.0, 0.0], "rotation_xyzw": [0.0, 0.0, 0.0, 1.0]},
                "provenance": {"source": common.PROVISIONAL_FORM_AUTHORED_CONTROL_PROVENANCE, "document": source["document"], "namespace": source["namespace"]},
            }
            for side in ("left", "right")
            for owner_role in ("thigh", "shin")
        ])
        frames.extend([
            {
                "owner": next(item for item in owners if item["role"] == "foot" and item["anchors"] == [side]),
                "role": common.PROVISIONAL_FORM_FOOT_PROFILE_FRAME_ROLE,
                "transform": {"translation": [0.0, 0.0, 0.0], "rotation_xyzw": [0.0, 0.0, 0.0, 1.0]},
                "provenance": {"source": common.PROVISIONAL_FORM_AUTHORED_CONTROL_PROVENANCE, "document": source["document"], "namespace": source["namespace"]},
            }
            for side in ("left", "right")
        ])
        frames.sort(key=lambda item: (
            item["owner"]["namespace"], tuple(item["owner"]["anchors"]),
            item["owner"]["kind"], item["owner"]["role"], item["role"],
        ))
        reference_points = {
            ("pelvis", ()): [0, 0, 0],
            ("torso", ()): [0, 1, 0],
            ("neck", ()): [0, 2, 0],
            ("head", ()): [0, 3, 0],
            ("upper_arm", ("left",)): [-1, 1, 0],
            ("forearm", ("left",)): [-2, 1, 0],
            ("hand", ("left",)): [-3, 1, 0],
            ("upper_arm", ("right",)): [1, 1, 0],
            ("forearm", ("right",)): [2, 1, 0],
            ("hand", ("right",)): [3, 1, 0],
            ("thigh", ("left",)): [-1, -1, 0],
            ("shin", ("left",)): [-1, -2, 0],
            ("foot", ("left",)): [-1, -3, 1],
            ("thigh", ("right",)): [1, -1, 0],
            ("shin", ("right",)): [1, -2, 0],
            ("foot", ("right",)): [1, -3, 1],
            ("tail_root", ("tail",)): [0, 0, -1],
            ("tail_tip", ("tail",)): [0, 0, -2],
        }
        descriptors = [{"address": owner, "reference_point": reference_points[(owner["role"], tuple(owner["anchors"]))], "dimension_roles": dimension_roles[owner["role"]]} for owner in owners]
        authored_provenance = {"source": common.PROVISIONAL_FORM_AUTHORED_CONTROL_PROVENANCE, "document": source["document"], "namespace": source["namespace"]}
        torso_landmarks = [
            {"owner": owner, "role": f"form_torso_profile_{name.replace('-', '_')}", "frame": {"owner": owner, "role": common.PROVISIONAL_FORM_TORSO_PROFILE_FRAME_ROLE}, "position": [0.0, y, 0.0], "provenance": authored_provenance}
            for name, owner, y, _radii in torso_sections
        ]
        head_landmarks = [
            {"owner": owner, "role": f"form_head_neck_profile_{name.replace('-', '_')}", "frame": {"owner": owner, "role": common.PROVISIONAL_FORM_HEAD_NECK_PROFILE_FRAME_ROLE}, "position": position, "provenance": authored_provenance}
            for name, owner, position, _radii in head_sections
        ]
        arm_landmarks = [
            {
                "owner": owner,
                "role": f"form_arm_profile_{name.replace('-', '_')}",
                "frame": {"owner": owner, "role": common.PROVISIONAL_FORM_ARM_PROFILE_FRAME_ROLE},
                "position": [0.0, y, 0.0],
                "provenance": authored_provenance,
            }
            for (side, _index), (name, owner, y, _radii) in arm_sections.items()
        ]
        leg_landmarks = [
            {
                "owner": owner,
                "role": f"form_leg_profile_{name.replace('-', '_')}",
                "frame": {"owner": owner, "role": common.PROVISIONAL_FORM_LEG_PROFILE_FRAME_ROLE},
                "position": position,
                "provenance": authored_provenance,
            }
            for (side, _index), (name, owner, position, _radii) in leg_sections.items()
        ]
        foot_landmarks = [
            {
                "owner": owner,
                "role": f"form_foot_profile_{name}",
                "frame": {"owner": owner, "role": common.PROVISIONAL_FORM_FOOT_PROFILE_FRAME_ROLE},
                "position": list(position),
                "provenance": authored_provenance,
            }
            for (_side, _index), (name, owner, position, _radii) in foot_sections.items()
        ]
        landmarks = sorted(shoulder_controls + torso_landmarks + head_landmarks + arm_landmarks + leg_landmarks + foot_landmarks, key=lambda item: (
            item["owner"]["namespace"], tuple(item["owner"]["anchors"]), item["owner"]["kind"], item["owner"]["role"], item["role"]
        ))
        authored_profile = {
            "format": publisher.AUTHORED_TORSO_PROFILE_FORMAT,
            "provenance": authored_provenance,
            "sections": [
                {
                    "name": name,
                    "frame_index": next(index for index, frame in enumerate(frames) if frame["owner"] == owner and frame["role"] == common.PROVISIONAL_FORM_TORSO_PROFILE_FRAME_ROLE),
                    "landmark_index": next(index for index, landmark in enumerate(landmarks) if landmark["owner"] == owner and landmark["role"] == f"form_torso_profile_{name.replace('-', '_')}"),
                    "dimension_indices": {
                        axis: next(index for index, dimension in enumerate(dimensions) if dimension["owner"] == owner and dimension["role"] == f"form_torso_profile_{name.replace('-', '_')}_{suffix}")
                        for axis, suffix in zip(("lateral", "anterior", "posterior"), ("lateral_radius", "anterior_radius", "posterior_radius"))
                    },
                    "provenance": authored_provenance,
                    "section_index": index,
                }
                for index, (name, owner, _y, _radii) in enumerate(torso_sections)
            ],
        }
        authored_head_profile = {
            "format": publisher.AUTHORED_HEAD_NECK_PROFILE_FORMAT,
            "provenance": authored_provenance,
            "sections": [
                {
                    "name": name,
                    "frame_index": next(index for index, frame in enumerate(frames) if frame["owner"] == owner and frame["role"] == common.PROVISIONAL_FORM_HEAD_NECK_PROFILE_FRAME_ROLE),
                    "landmark_index": next(index for index, landmark in enumerate(landmarks) if landmark["owner"] == owner and landmark["role"] == f"form_head_neck_profile_{name.replace('-', '_')}"),
                    "dimension_indices": {
                        axis: next(index for index, dimension in enumerate(dimensions) if dimension["owner"] == owner and dimension["role"] == f"form_head_neck_profile_{name.replace('-', '_')}_{suffix}")
                        for axis, suffix in zip(("lateral", "up", "forward"), ("lateral_radius", "up_radius", "forward_radius"))
                    },
                    "provenance": authored_provenance,
                    "section_index": index,
                }
                for index, (name, owner, _position, _radii) in enumerate(head_sections)
            ],
            "connections": [
                {"name": name, "from_section_index": from_index, "to_section_index": to_index, "route": route}
                for name, from_index, to_index, route in common.PROVISIONAL_FORM_HEAD_NECK_PROFILE_CONNECTIONS
            ],
        }
        authored_arm_profile = {
            "format": publisher.AUTHORED_ARM_PROFILE_FORMAT,
            "provenance": authored_provenance,
            "sides": [
                {
                    "side": side,
                    "sections": [
                        {
                            "name": name,
                            "frame_index": next(index for index, frame in enumerate(frames) if frame["owner"] == owner and frame["role"] == common.PROVISIONAL_FORM_ARM_PROFILE_FRAME_ROLE),
                            "landmark_index": next(index for index, landmark in enumerate(landmarks) if landmark["owner"] == owner and landmark["role"] == f"form_arm_profile_{name.replace('-', '_')}"),
                            "dimension_indices": {
                                axis: next(index for index, dimension in enumerate(dimensions) if dimension["owner"] == owner and dimension["role"] == f"form_arm_profile_{name.replace('-', '_')}_{suffix}")
                                for axis, suffix in zip(("lateral", "up", "forward"), ("lateral_radius", "up_radius", "forward_radius"))
                            },
                            "provenance": authored_provenance,
                            "section_index": index,
                        }
                        for index in range(5)
                        for name, owner, _y, _radii in [arm_sections[(side, index)]]
                    ],
                }
                for side in ("left", "right")
            ],
        }
        authored_leg_profile = {
            "format": publisher.AUTHORED_LEG_PROFILE_FORMAT,
            "provenance": authored_provenance,
            "sides": [
                {
                    "side": side,
                    "sections": [
                        {
                            "name": name,
                            "frame_index": next(index for index, frame in enumerate(frames) if frame["owner"] == owner and frame["role"] == common.PROVISIONAL_FORM_LEG_PROFILE_FRAME_ROLE),
                            "landmark_index": next(index for index, landmark in enumerate(landmarks) if landmark["owner"] == owner and landmark["role"] == f"form_leg_profile_{name.replace('-', '_')}"),
                            "dimension_indices": {
                                axis: next(index for index, dimension in enumerate(dimensions) if dimension["owner"] == owner and dimension["role"] == f"form_leg_profile_{name.replace('-', '_')}_{suffix}")
                                for axis, suffix in zip(("lateral", "up", "forward"), ("lateral_radius", "up_radius", "forward_radius"))
                            },
                            "provenance": authored_provenance,
                            "section_index": index,
                        }
                        for index in range(5)
                        for name, owner, _position, _radii in [leg_sections[(side, index)]]
                    ],
                }
                for side in ("left", "right")
            ],
        }
        authored_foot_profile = {
            "format": publisher.AUTHORED_FOOT_PROFILE_FORMAT,
            "provenance": authored_provenance,
            "sides": [
                {
                    "side": side,
                    "hock_binding": {"source_profile": "authored_leg_profile", "side_index": side_index, "section_index": common.PROVISIONAL_FORM_FOOT_PROFILE_HOCK_SECTION_INDEX},
                    "sections": [
                        {
                            "name": name,
                            "frame_index": next(index for index, frame in enumerate(frames) if frame["owner"] == owner and frame["role"] == common.PROVISIONAL_FORM_FOOT_PROFILE_FRAME_ROLE),
                            "landmark_index": next(index for index, landmark in enumerate(landmarks) if landmark["owner"] == owner and landmark["role"] == f"form_foot_profile_{name}"),
                            "dimension_indices": {
                                axis: next(index for index, dimension in enumerate(dimensions) if dimension["owner"] == owner and dimension["role"] == f"form_foot_profile_{name}_{suffix}")
                                for axis, suffix in zip(("lateral", "up", "forward"), ("lateral_radius", "up_radius", "forward_radius"))
                            },
                            "provenance": authored_provenance,
                            "section_index": index,
                        }
                        for index in range(2)
                        for name, owner, _position, _radii in [foot_sections[(side, index)]]
                    ],
                }
                for side_index, side in enumerate(("left", "right"))
            ],
        }
        variant_profiles = {}
        variant_arm_profiles = {}
        variant_leg_profiles = {}
        variant_foot_profiles = {}
        for variant_id in common.PROVISIONAL_FORM_VARIANT_IDS:
            variant_sections = []
            for index, (name, owner, y, radii) in enumerate(torso_sections):
                factors = publisher._torso_profile_factors(variant_id, owner["role"])
                scaled = [value * factor // 1000 for value, factor in zip(radii, factors)]
                variant_sections.append({
                    "source_section_index": index,
                    "name": name,
                    "position": [0.0, y, 0.0],
                    "lateral_radius_permille": scaled[0],
                    "anterior_radius_permille": scaled[1],
                    "posterior_radius_permille": scaled[2],
                    "scaling": {"lateral_factor_permille": factors[0], "anterior_factor_permille": factors[1], "posterior_factor_permille": factors[2]},
                    "provenance": authored_provenance,
                })
            variant_profiles[variant_id] = {"format": publisher.AUTHORED_TORSO_PROFILE_FORMAT, "source": "authored_torso_profile", "provenance": authored_provenance, "sections": variant_sections}
            variant_arm_profiles[variant_id] = {
                "format": publisher.AUTHORED_ARM_PROFILE_FORMAT,
                "source": "authored_arm_profile",
                "provenance": authored_provenance,
                "sides": [
                    {
                        "side": side,
                        "sections": [
                            {
                                "source_section_index": index,
                                "name": name,
                                "position": [0.0, y, 0.0],
                                "lateral_radius_permille": scaled[0],
                                "up_radius_permille": scaled[1],
                                "forward_radius_permille": scaled[2],
                                "scaling": {"lateral_factor_permille": factors[0], "up_factor_permille": factors[1], "forward_factor_permille": factors[2]},
                                "provenance": authored_provenance,
                            }
                            for index in range(5)
                            for name, owner, y, radii in [arm_sections[(side, index)]]
                            for factors in [common._provisional_form_arm_profile_factors(variant_id)]
                            for scaled in [[value * factor // 1000 for value, factor in zip(radii, factors)]]
                        ],
                    }
                    for side in ("left", "right")
                ],
            }
            variant_leg_profiles[variant_id] = {
                "format": publisher.AUTHORED_LEG_PROFILE_FORMAT,
                "source": "authored_leg_profile",
                "provenance": authored_provenance,
                "sides": [
                    {
                        "side": side,
                        "sections": [
                            {
                                "source_section_index": index,
                                "name": name,
                                "position": list(position),
                                "lateral_radius_permille": scaled[0],
                                "up_radius_permille": scaled[1],
                                "forward_radius_permille": scaled[2],
                                "scaling": {"lateral_factor_permille": factors[0], "up_factor_permille": factors[1], "forward_factor_permille": factors[2]},
                                "provenance": authored_provenance,
                            }
                            for index in range(5)
                            for name, owner, position, radii in [leg_sections[(side, index)]]
                            for factors in [common._provisional_form_leg_profile_factors(variant_id)]
                            for scaled in [[value * factor // 1000 for value, factor in zip(radii, factors)]]
                        ],
                    }
                    for side in ("left", "right")
                ],
            }
            foot_factors = common._provisional_form_foot_profile_factors(variant_id)
            variant_foot_profiles[variant_id] = {
                "format": publisher.AUTHORED_FOOT_PROFILE_FORMAT,
                "source": "authored_foot_profile",
                "provenance": authored_provenance,
                "sides": [
                    {
                        "side": side,
                        "hock_binding": {"source_profile": "authored_leg_profile", "side_index": side_index, "section_index": common.PROVISIONAL_FORM_FOOT_PROFILE_HOCK_SECTION_INDEX},
                        "sections": [
                            {
                                "source_section_index": index,
                                "name": name,
                                "position": list(position),
                                "lateral_radius_permille": scaled[0],
                                "up_radius_permille": scaled[1],
                                "forward_radius_permille": scaled[2],
                                "scaling": {"lateral_factor_permille": foot_factors[0], "up_factor_permille": foot_factors[1], "forward_factor_permille": foot_factors[2]},
                                "provenance": authored_provenance,
                            }
                            for index in range(2)
                            for name, owner, position, radii in [foot_sections[(side, index)]]
                            for scaled in [[value * factor // 1000 for value, factor in zip(radii, foot_factors)]]
                        ],
                    }
                    for side in ("left", "right")
                    for side_index in [0 if side == "left" else 1]
                ],
            }
        return {
            "format": common.PROVISIONAL_FORM_FORMAT,
            "operation": common.PROVISIONAL_FORM_OPERATION,
            "status": "success",
            "stage": common.PROVISIONAL_FORM_STAGE,
            "processing_complete": True,
            "diagnostics_complete": True,
            "diagnostics": [],
            "source": source,
            "reference_scale": reference_scale,
            "authored_dimensions": dimensions,
            "authored_landmarks": landmarks,
            "authored_frames": frames,
            "authored_torso_profile": authored_profile,
            "authored_head_neck_profile": authored_head_profile,
            "authored_arm_profile": authored_arm_profile,
            "authored_leg_profile": authored_leg_profile,
            "authored_foot_profile": authored_foot_profile,
            "variants": [{"id": variant_id, "profile_id": variant_id, "provenance": {"source": common.PROVISIONAL_FORM_PROVENANCE, "resource_profile_id": common.PROVISIONAL_FORM_RESOURCE_PROFILE, "shape_basis": common.PROVISIONAL_FORM_SHAPE_BASIS}, "descriptors": descriptors, "torso_profile": variant_profiles[variant_id], "head_neck_profile": {
                "format": publisher.AUTHORED_HEAD_NECK_PROFILE_FORMAT,
                "source": "authored_head_neck_profile",
                "provenance": authored_provenance,
                "sections": [
                    {
                        "source_section_index": index,
                        "name": name,
                        "position": position,
                        "lateral_radius_permille": scaled[0],
                        "up_radius_permille": scaled[1],
                        "forward_radius_permille": scaled[2],
                        "scaling": {"lateral_factor_permille": factors[0], "up_factor_permille": factors[1], "forward_factor_permille": factors[2]},
                        "provenance": authored_provenance,
                    }
                    for index, (name, owner, position, radii) in enumerate(head_sections)
                    for factors in [common._provisional_form_head_neck_profile_factors(variant_id, owner["role"])]
                    for scaled in [[value * factor // 1000 for value, factor in zip(radii, factors)]]
                ],
                "connections": authored_head_profile["connections"],
            }, "arm_profile": variant_arm_profiles[variant_id], "leg_profile": variant_leg_profiles[variant_id], "foot_profile": variant_foot_profiles[variant_id]
            } for variant_id in common.PROVISIONAL_FORM_VARIANT_IDS],
            "limitations": "Provisional display-only geometry descriptors; no production geometry or Readiness 3.",
        }

    def test_successor_ply_parser_rejects_malformed_schema_values_and_indices(self) -> None:
        valid = self._tetra_ply()
        point_contact_lines = [
            "ply", "format ascii 1.0", "element vertex 7",
            "property float x", "property float y", "property float z",
            "property float nx", "property float ny", "property float nz",
            "element face 8", "property list uchar int vertex_indices", "end_header",
            "0 0 0 1 1 1", "1 0 0 1 1 1", "0 1 0 1 1 1", "0 0 1 1 1 1",
            "-1 0 0 -1 -1 -1", "0 -1 0 -1 -1 -1", "0 0 -1 -1 -1 -1",
            "3 0 2 1", "3 0 1 3", "3 0 3 2", "3 1 2 3",
            "3 0 4 5", "3 0 6 4", "3 0 5 6", "3 4 6 5",
        ]
        cases = {
            "schema": valid.replace(b"property float nx", b"property double nx", 1),
            "nonfinite": valid.replace(
                b"0.000000000 0.000000000 0.000000000",
                b"nan 0.000000000 0.000000000",
                1,
            ),
            "index": valid.replace(b"3 1 2 3\n", b"3 1 2 9\n", 1),
            "duplicate-face": self._tetra_ply(duplicate_face=True),
            "inconsistent-orientation": self._tetra_ply(inconsistent_orientation=True),
            "global-reversal": self._tetra_ply(global_reversal=True),
            "zero-normals": self._tetra_ply(zero_normals=True),
            "zero-volume": self._tetra_ply(flattened_height=0.0),
            "flattened": self._tetra_ply(flattened_height=1.0e-13),
            "point-contact": ("\n".join(point_contact_lines) + "\n").encode("ascii"),
        }
        expected = {
            "schema": "property schema",
            "nonfinite": "non-finite value",
            "index": "out-of-range index",
            "duplicate-face": "duplicate face independent of winding",
            "inconsistent-orientation": "inconsistent face orientation",
            "global-reversal": "canonical outward orientation",
            "zero-normals": "zero or unusable normal",
            "zero-volume": "positive enclosed volume",
            "flattened": "positive enclosed volume",
            "point-contact": "connected only at vertices",
        }
        for name, payload in cases.items():
            with self.subTest(name=name):
                path = self.directory / f"malformed-{name}.ply"
                path.write_bytes(payload)
                with self.assertRaisesRegex(
                    publisher.SurfacePreviewPublishError,
                    expected[name],
                ):
                    publisher._validate_successor_ply(path, path.name)

    def test_address_validation_accepts_empty_anchors_and_rejects_malformed_entries(self) -> None:
        valid = {"namespace": "main", "anchors": [], "kind": "part", "role": "neck"}
        self.assertEqual(publisher._validate_address(valid, "address"), valid)
        for anchors in (None, [""], [1], "neck"):
            with self.subTest(anchors=anchors):
                with self.assertRaises(publisher.SurfacePreviewPublishError):
                    publisher._validate_address({**valid, "anchors": anchors}, "address")

    def test_success_publishes_four_ordered_baseline_successor_pairs(self) -> None:
        self.assertEqual(publisher.EXPECTED_GUIDE_COUNTS["compiled_fields"], 52)
        self.assertEqual(publisher.EXPECTED_GUIDE_COUNTS["shoulder_frame_compiled_fields"], 2)
        self.assertEqual(publisher.EXPECTED_LAYOUT["pairing"], "control-guide/field-components/skin per projection")
        self.assertNotIn("hip-girdle", publisher.EXPECTED_GUIDE_COUNTS["compiled_field_recipe_counts"])
        self.assertNotIn("shoulder-mass", publisher.EXPECTED_GUIDE_COUNTS["compiled_field_recipe_counts"])
        with patch.object(publisher, "_parse_inspection", return_value=self._payload()):
            result = publisher.publish_surface_preview(
                self.root,
                self.input,
                creature_kernel=self._producer(),
                generator=self._generator(),
                successor_generator=self._successor_generator(),
                review_id="surface-test",
            )
        session = Path(result["session"])
        self.assertEqual(result["variants"], 4)
        self.assertEqual(result["images"], 8)
        self.assertEqual(result["assets"], 8)
        self.assertEqual(
            sorted(p.name for p in (session / "assets").iterdir()),
            sorted(f"{v}-{role}.png" for v in common.PROVISIONAL_FORM_VARIANT_IDS for role in ("baseline", "successor")),
        )
        review = json.loads((session / "review.json").read_text(encoding="utf-8"))
        descriptor_snapshot = review["subject_context"]["descriptor_snapshot"]
        input_bytes = self.input.read_bytes()
        self.assertEqual(descriptor_snapshot["input_body_document_encoding"], "utf-8")
        self.assertEqual(descriptor_snapshot["input_body_document_bytes"], len(input_bytes))
        self.assertEqual(
            descriptor_snapshot["input_body_document_sha256"],
            hashlib.sha256(input_bytes).hexdigest(),
        )
        producer_bytes = publisher._decode_producer_evidence(descriptor_snapshot)
        self.assertEqual(
            hashlib.sha256(producer_bytes).hexdigest(),
            descriptor_snapshot["producer_envelope_sha256"],
        )
        self.assertEqual(
            set(descriptor_snapshot),
            publisher.INPUT_EVIDENCE_FIELDS
            | publisher._evidence_fields(publisher.PRODUCER_EVIDENCE_PREFIX),
        )
        self.assertEqual(json.loads(producer_bytes), self._payload())
        tampered_producer = dict(descriptor_snapshot)
        tampered_producer["producer_envelope_sha256"] = "0" * 64
        with self.assertRaisesRegex(publisher.SurfacePreviewPublishError, "exact source bytes"):
            publisher._validate_producer_evidence(tampered_producer)
        self.assertEqual(len(review["groups"]), 4)
        self.assertEqual([item["metadata"]["source_role"] for item in review["groups"][0]["items"]], ["baseline", "successor"])
        self.assertEqual([item["title"] for item in review["groups"][0]["items"]], ["Neutral — baseline", "Neutral — successor"])
        self.assertEqual(review["groups"][0]["selection_mode"], "none")
        expected_prefixes = ["Neutral", "Broad soft", "Lean readable", "Depth forward"]
        for group, variant_id, title_prefix in zip(review["groups"], common.PROVISIONAL_FORM_VARIANT_IDS, expected_prefixes):
            self.assertEqual(group["id"], variant_id)
            self.assertEqual(group["title"], f"{title_prefix} ({variant_id})")
            baseline, successor = group["items"]
            self.assertEqual([item["metadata"]["source_role"] for item in group["items"]], ["baseline", "successor"])
            self.assertEqual(baseline["metadata"]["source_sha256"], successor["metadata"]["source_sha256"])
            self.assertEqual(baseline["metadata"]["variant_binding_sha256"], successor["metadata"]["variant_binding_sha256"])
            self.assertEqual(baseline["metadata"]["views"], ["front", "side", "three-quarter"])
            self.assertEqual(successor["metadata"]["views"], baseline["metadata"]["views"])
            self.assertEqual(baseline["metadata"]["panels_per_view"], successor["metadata"]["panels_per_view"])
            self.assertEqual(baseline["metadata"]["panels_per_view"], 3)
            self.assertEqual(baseline["metadata"]["generator"]["bundle_version"], 3)
            self.assertEqual(baseline["metadata"]["generator"]["component_visualization"], publisher.EXPECTED_COMPONENT_VISUALIZATION)
            self.assertEqual(baseline["metadata"]["generator"]["component_visualization"]["samples_per_axis"], 32)
            self.assertEqual(successor["metadata"]["generator"]["padding"], 0.5)
            self.assertEqual(successor["metadata"]["generator"]["capture_padding"], 0.75)
            self.assertNotEqual(successor["metadata"]["generator"]["padding"], successor["metadata"]["generator"]["capture_padding"])
            self.assertEqual(successor["metadata"]["generator"]["component_visualization"], publisher.EXPECTED_COMPONENT_VISUALIZATION)
            self.assertEqual(set(successor["metadata"]["generator"]), {"samples_per_axis", "padding", "capture_padding", "smooth_k", "consumer_boundary", "production_status", "component_visualization"})
            for item in (baseline, successor):
                self.assertIn("columns front/side/three-quarter", item["description"])
                self.assertIn("rows control guide (not geometry), consumed fields (exact pre-union components), and final skin (smooth union)", item["description"])
        self.assertEqual(review["subject_context"]["descriptor_snapshot"]["producer_envelope_sha256"], review["groups"][0]["items"][0]["metadata"]["source_sha256"])
        self.assertIn("compare baseline first and successor second", review["instructions"])
        self.assertIn("overall creature coherence", review["instructions"])
        self.assertEqual(
            set(review["subject_context"]),
            {"descriptor_snapshot"},
        )

        # The ordinary image publisher is immutable: a duplicate review ID is
        # rejected and does not replace the first published session.
        with patch.object(publisher, "_parse_inspection", return_value=self._payload()):
            with self.assertRaisesRegex(publisher.SurfacePreviewPublishError, "session already exists"):
                publisher.publish_surface_preview(
                    self.root,
                    self.input,
                    creature_kernel=self._producer(),
                    generator=self._generator(),
                    successor_generator=self._successor_generator(),
                    review_id="surface-test",
                )
        self.assertEqual(sorted(path.name for path in self.root.iterdir()), ["surface-test"])

    def test_publisher_hip_root_controls_match_independent_fixture(self) -> None:
        self.assertEqual(
            publisher.SUCCESSOR_HIP_ROOT_CONTROLS,
            INDEPENDENT_SUCCESSOR_FIXTURE["hip_root_controls"],
        )

    def test_synthetic_successor_fixture_rejects_publisher_identity_drift(self) -> None:
        with patch.object(publisher, "SUCCESSOR_REGION_ID", "publisher-only-region-drift"):
            with patch.object(publisher, "_parse_inspection", return_value=self._payload()):
                with self.assertRaises(publisher.SurfacePreviewPublishError):
                    publisher.publish_surface_preview(
                        self.root,
                        self.input,
                        creature_kernel=self._producer(),
                        generator=self._generator(),
                        successor_generator=self._successor_generator(),
                        review_id="independent-fixture-drift",
                    )
        self.assertFalse((self.root / "independent-fixture-drift").exists())

    def test_successor_bounds_contain_baseline_and_sidecar_uses_successor_frame(self) -> None:
        captured: dict[str, list[dict[str, object]]] = {}
        validate_bundle = publisher._validate_bundle
        validate_successor_bundle = publisher._validate_successor_bundle

        def capture_bundle(*args: object, **kwargs: object):
            published, metadata = validate_bundle(*args, **kwargs)
            captured["baseline"] = published
            return published, metadata

        def capture_successor_bundle(*args: object, **kwargs: object):
            published, metadata = validate_successor_bundle(*args, **kwargs)
            captured["successor"] = published
            return published, metadata

        with patch.object(publisher, "_parse_inspection", return_value=self._payload()):
            with patch.object(publisher, "_validate_bundle", side_effect=capture_bundle):
                with patch.object(
                    publisher,
                    "_validate_successor_bundle",
                    side_effect=capture_successor_bundle,
                ):
                    result = publisher.publish_surface_preview(
                        self.root,
                        self.input,
                        creature_kernel=self._producer(),
                        generator=self._generator(),
                        successor_generator=self._successor_generator(mode="expanded-bounds"),
                        review_id="expanded-successor-frame",
                    )
        self.assertEqual(result["variants"], 4)
        self.assertEqual(result["images"], 8)
        baseline_by_id = {item["id"]: item for item in captured["baseline"]}
        successor_by_id = {item["id"]: item for item in captured["successor"]}
        baseline_bounds = {"min": [-5.0, -5.0, -5.0], "max": [5.0, 5.0, 5.0]}
        successor_bounds = {"min": [-6.0, -6.0, -6.0], "max": [6.0, 6.0, 6.0]}
        review = json.loads(
            (Path(result["session"]) / "review.json").read_text(encoding="utf-8")
        )
        for group in review["groups"]:
            variant_id = group["id"]
            baseline_binding = baseline_by_id[variant_id]["binding"]
            successor_binding = successor_by_id[variant_id]["binding"]
            self.assertEqual(baseline_binding["capture"]["shared_render_bounds"], baseline_bounds)
            self.assertEqual(successor_binding["capture"]["shared_render_bounds"], successor_bounds)
            baseline_item, successor_item = group["items"]
            self.assertEqual(
                baseline_item["metadata"]["variant_binding_sha256"],
                hashlib.sha256(
                    publisher.canonical_json(baseline_binding).encode("utf-8")
                ).hexdigest(),
            )
            self.assertEqual(
                successor_item["metadata"]["variant_binding_sha256"],
                hashlib.sha256(
                    publisher.canonical_json(successor_binding).encode("utf-8")
                ).hexdigest(),
            )

    def test_successor_bounds_reject_non_containment(self) -> None:
        with patch.object(publisher, "_parse_inspection", return_value=self._payload()):
            with self.assertRaisesRegex(
                publisher.SurfacePreviewPublishError,
                "successor shared_render_bounds must contain baseline bounds",
            ):
                publisher.publish_surface_preview(
                    self.root,
                    self.input,
                    creature_kernel=self._producer(),
                    generator=self._generator(),
                    successor_generator=self._successor_generator(mode="non-containing-bounds"),
                    review_id="non-containing-successor-frame",
                )
        self.assertFalse((self.root / "non-containing-successor-frame").exists())

    def test_canonical_stylized_digitigrade_torso_profile_accepts_owner_local_landmarks(self) -> None:
        repository_root = HERE.parents[1]
        input_path = repository_root / "examples/body-documents/stylized-digitigrade-biped-authored-form.json"
        completed = subprocess.run(
            [
                "cargo", "run", "--quiet", "--package", "creature-kernel-cli",
                "--bin", "creature-kernel", "--", "inspect-provisional-form",
                "--input", str(input_path),
            ],
            cwd=repository_root,
            capture_output=True,
            text=True,
            check=True,
        )
        payload = json.loads(completed.stdout)
        profile_context = publisher._validate_authored_torso_profile(payload)
        self.assertEqual(
            [section["owner"]["role"] for section in profile_context["base_torso_lineage"]],
            ["pelvis", "pelvis", "torso", "torso", "torso", "torso", "torso"],
        )
        for first, second in ((0, 1), (2, 3), (3, 4), (4, 5), (5, 6)):
            self.assertLess(
                profile_context["base_torso_lineage"][first]["landmark"]["position"][1],
                profile_context["base_torso_lineage"][second]["landmark"]["position"][1],
            )

    def test_torso_profile_rejects_inverted_composed_body_space_order(self) -> None:
        payload = copy.deepcopy(self._payload())
        for variant in payload["variants"]:
            torso_descriptor = next(
                descriptor
                for descriptor in variant["descriptors"]
                if descriptor["address"]["role"] == "torso"
                and descriptor["address"]["anchors"] == []
            )
            torso_descriptor["reference_point"][1] = -2
        with self.assertRaisesRegex(
            publisher.SurfacePreviewPublishError,
            "composed body-space y",
        ):
            publisher._validate_authored_torso_profile(payload)

    def test_actual_generators_publish_hand_paw_metadata(self) -> None:
        if os.environ.get("CK_RUN_SURFACE_PREVIEW_INTEGRATION") != "1":
            self.skipTest(
                "set CK_RUN_SURFACE_PREVIEW_INTEGRATION=1 after building target/debug/creature-kernel"
            )
        repository_root = HERE.parents[1]
        creature_kernel = repository_root / "target/debug/creature-kernel"
        if not creature_kernel.is_file() or not os.access(creature_kernel, os.X_OK):
            self.skipTest("requires an executable target/debug/creature-kernel")
        input_path = repository_root / "examples/body-documents/stylized-digitigrade-biped-authored-form.json"
        captured: dict[str, object] = {}
        validate_successor_bundle = publisher._validate_successor_bundle

        def capture_successor_bundle(*args: object, **kwargs: object):
            published, metadata = validate_successor_bundle(*args, **kwargs)
            bundle = Path(args[0])
            captured["published"] = published
            captured["manifest_size"] = (bundle / publisher.SUCCESSOR_MANIFEST_NAME).stat().st_size
            return published, metadata

        with patch.object(publisher, "GENERATOR_TIMEOUT_SECONDS", 600.0), patch.object(
            publisher,
            "_validate_successor_bundle",
            side_effect=capture_successor_bundle,
        ):
            result = publisher.publish_surface_preview(
                self.root,
                input_path,
                creature_kernel=creature_kernel,
                generator=repository_root / "experiments/current-form-surface-preview/generate_surface_preview.py",
                successor_generator=repository_root / "experiments/current-form-surface-preview/successor_surface_preview.py",
                review_id="actual-hand-paw-metadata",
            )

        self.assertEqual(result["variants"], 4)
        self.assertEqual(result["images"], 8)
        review = json.loads((Path(result["session"]) / "review.json").read_text(encoding="utf-8"))
        self.assertEqual(len(review["groups"]), len(common.PROVISIONAL_FORM_VARIANT_IDS))
        self.assertTrue(all(len(group["items"]) == 2 for group in review["groups"]))
        published = captured["published"]
        self.assertIsInstance(published, list)
        self.assertEqual(len(published), len(common.PROVISIONAL_FORM_VARIANT_IDS))
        for item in published:
            sidecar_hand_paw = item["sidecar"]["extremities"]["hand_paw"]
            metrics_hand_paw = item["metrics"]["successor_region"]["hand_paw"]
            self.assertEqual(sidecar_hand_paw, metrics_hand_paw)
            self.assertEqual(sidecar_hand_paw["route_order"], ["left-hand-paw", "right-hand-paw"])
            self.assertEqual(sidecar_hand_paw["section_names"], list(publisher.SUCCESSOR_HAND_PAW_SECTION_NAMES))
            self.assertEqual(sidecar_hand_paw["route_station_count"], 8)
            self.assertEqual(sidecar_hand_paw["route_volume_axis_count"], 24)
            self.assertEqual(sidecar_hand_paw["route_volume_radius_count"], 24)
        manifest_size = captured["manifest_size"]
        self.assertIsInstance(manifest_size, int)
        self.assertEqual(manifest_size, 408_678)
        self.assertGreaterEqual(
            publisher.MAX_MANIFEST_BYTES - manifest_size,
            publisher.MIN_MANIFEST_HEADROOM_BYTES,
        )

    def test_manifest_cap_is_finite_and_rejects_bytes_over_the_bound(self) -> None:
        self.assertEqual(publisher.MIN_MANIFEST_HEADROOM_BYTES, 8 * 1024)
        self.assertEqual(publisher.MAX_MANIFEST_BYTES, 420 * 1024)
        path = self.directory / "over-cap-manifest.json"
        path.write_bytes(b"x" * (publisher.MAX_MANIFEST_BYTES + 1))
        with self.assertRaisesRegex(
            publisher.SurfacePreviewPublishError,
            f"manifest exceeds {publisher.MAX_MANIFEST_BYTES} bytes",
        ):
            publisher._read_json(path, publisher.MAX_MANIFEST_BYTES, "manifest")

    def test_v7_authored_torso_profile_tampering_rejects_without_review_directory(self) -> None:
        cases = ("omission", "reorder", "owner", "provenance", "name", "radius", "stale-version", "descriptor-owner")
        for index, case in enumerate(cases):
            review_id = f"profile-tamper-{index}"
            payload = copy.deepcopy(self._payload())
            sections = payload["authored_torso_profile"]["sections"]
            if case == "omission":
                sections.pop()
            elif case == "reorder":
                sections[1], sections[2] = sections[2], sections[1]
            elif case == "owner":
                sections[0]["frame_index"] = sections[2]["frame_index"]
            elif case == "provenance":
                sections[0]["provenance"] = {"source": "fabricated", "document": "fixture", "namespace": "main"}
            elif case == "name":
                sections[0]["name"] = "renamed-pelvis"
            elif case == "radius":
                payload["authored_dimensions"][sections[0]["dimension_indices"]["lateral"]]["value_permille"] += 1
            elif case == "stale-version":
                payload["authored_torso_profile"]["format"] = "creature-kernel.provisional-form-torso-profile.v0"
            elif case == "descriptor-owner":
                payload["variants"][0]["descriptors"][0]["address"] = payload["variants"][0]["descriptors"][1]["address"]
            with self.subTest(case=case):
                with patch.object(publisher, "_parse_inspection", return_value=payload):
                    with self.assertRaises(publisher.SurfacePreviewPublishError):
                        publisher.publish_surface_preview(
                            self.root,
                            self.input,
                            creature_kernel=self._producer(),
                            generator=self._generator(),
                            successor_generator=self._successor_generator(),
                            review_id=review_id,
                        )
                self.assertFalse((self.root / review_id).exists())

    def test_v7_authored_torso_profile_enforces_source_radius_bounds(self) -> None:
        for value, expected in ((0, "source torso radius"), (5_001, "source torso radius")):
            payload = copy.deepcopy(self._payload())
            role = "form_torso_profile_lower_pelvis_lateral_radius"
            dimension = next(item for item in payload["authored_dimensions"] if item["role"] == role)
            dimension["value_permille"] = value
            with self.subTest(value=value):
                with self.assertRaisesRegex(publisher.SurfacePreviewPublishError, expected):
                    publisher._validate_authored_torso_profile(payload)

    def test_v7_authored_torso_profile_enforces_projected_radius_bounds(self) -> None:
        cases = (
            ("below", "neutral-v0", 0, "lateral", 0),
            ("above", "neutral-v0", 6, "anterior", 5_001),
        )
        for name, variant_id, section_index, axis, value in cases:
            payload = copy.deepcopy(self._payload())
            variant = next(item for item in payload["variants"] if item["id"] == variant_id)
            variant["torso_profile"]["sections"][section_index][f"{axis}_radius_permille"] = value
            with self.subTest(name=name):
                with self.assertRaisesRegex(publisher.SurfacePreviewPublishError, "projected torso radius"):
                    publisher._validate_authored_torso_profile(payload)

    def test_v8_authored_head_neck_profile_rejects_representative_cross_bindings(self) -> None:
        cases = (
            "section-omitted",
            "section-malformed",
            "connection-mismatch",
            "lineage-mismatch",
            "variant-position-mismatch",
            "variant-connection-mismatch",
            "neck-route-order",
            "cranium-route-order",
            "muzzle-route-order",
        )
        for case in cases:
            payload = copy.deepcopy(self._payload())
            if case == "section-omitted":
                payload["authored_head_neck_profile"]["sections"].pop()
            elif case == "section-malformed":
                payload["authored_head_neck_profile"]["sections"][3]["dimension_indices"]["up"] = 0
            elif case == "connection-mismatch":
                payload["authored_head_neck_profile"]["connections"][4]["route"] = "vertical-neck-cranium"
            elif case == "lineage-mismatch":
                payload["variants"][0]["head_neck_profile"]["sections"][0]["lateral_radius_permille"] += 1
            elif case == "variant-position-mismatch":
                position = list(payload["variants"][0]["head_neck_profile"]["sections"][0]["position"])
                position[1] += 0.01
                payload["variants"][0]["head_neck_profile"]["sections"][0]["position"] = position
            elif case == "variant-connection-mismatch":
                payload["variants"][0]["head_neck_profile"]["connections"][0]["route"] = "forward-muzzle"
            elif case in {"neck-route-order", "cranium-route-order", "muzzle-route-order"}:
                route_indices, axis = {
                    "neck-route-order": ((0, 1), 1),
                    "cranium-route-order": ((3, 4), 1),
                    "muzzle-route-order": ((3, 5), 2),
                }[case]
                sections = payload["authored_head_neck_profile"]["sections"]
                landmarks = payload["authored_landmarks"]
                first, second = route_indices
                landmarks[sections[second]["landmark_index"]]["position"][axis] = (
                    landmarks[sections[first]["landmark_index"]]["position"][axis]
                )
            with self.subTest(case=case):
                with self.assertRaises(publisher.SurfacePreviewPublishError):
                    publisher._validate_authored_torso_profile(payload)

    def test_v8_authored_head_neck_profile_accepts_owner_local_source_routes(self) -> None:
        payload = self._payload()
        profile = payload["authored_head_neck_profile"]
        positions = [
            payload["authored_landmarks"][section["landmark_index"]]["position"]
            for section in profile["sections"]
        ]
        self.assertEqual(
            [position[1] for position in positions[:5]],
            [0.15, 0.55, -0.35, 0.05, 0.40],
        )
        self.assertEqual(
            [positions[index][2] for index in (3, 5, 6, 7)],
            [0.0, 0.25, 0.55, 0.80],
        )
        context = publisher._validate_authored_torso_profile(payload)
        self.assertEqual(
            [item["name"] for item in context["base_head_neck_lineage"]],
            list(publisher.AUTHORED_HEAD_NECK_PROFILE_SECTION_NAMES),
        )

    def test_v9_authored_arm_profile_validates_bilateral_lineage_and_rejects_cross_bindings(self) -> None:
        payload = self._payload()
        context = publisher._validate_authored_torso_profile(payload)
        self.assertEqual(
            [side["side"] for side in context["base_arm_lineage"]],
            ["left", "right"],
        )
        self.assertEqual(
            [section["name"] for section in context["base_arm_lineage"][0]["sections"]],
            list(publisher.AUTHORED_ARM_PROFILE_SECTION_NAMES),
        )
        self.assertEqual(
            context["variants"]["depth-forward-v0"]["arm_lineage"][0]["sections"][4]["scaling"]["forward"],
            1_300,
        )
        cases = {
            "side-order": lambda value: value["authored_arm_profile"]["sides"].reverse(),
            "source-index": lambda value: value["authored_arm_profile"]["sides"][0]["sections"][1].__setitem__("section_index", 4),
            "frame-index": lambda value: value["authored_arm_profile"]["sides"][0]["sections"][0].__setitem__("frame_index", value["authored_arm_profile"]["sides"][0]["sections"][3]["frame_index"]),
            "landmark-index": lambda value: value["authored_arm_profile"]["sides"][0]["sections"][0].__setitem__("landmark_index", value["authored_arm_profile"]["sides"][0]["sections"][1]["landmark_index"]),
            "dimension-index": lambda value: value["authored_arm_profile"]["sides"][0]["sections"][0]["dimension_indices"].__setitem__("lateral", value["authored_arm_profile"]["sides"][0]["sections"][1]["dimension_indices"]["lateral"]),
            "variant-radius": lambda value: value["variants"][0]["arm_profile"]["sides"][0]["sections"][0].__setitem__("forward_radius_permille", value["variants"][0]["arm_profile"]["sides"][0]["sections"][0]["forward_radius_permille"] + 1),
        }
        for name, mutate in cases.items():
            malformed = copy.deepcopy(payload)
            mutate(malformed)
            with self.subTest(name=name):
                with self.assertRaises(publisher.SurfacePreviewPublishError):
                    publisher._validate_authored_torso_profile(malformed)

    def test_v10_authored_leg_profile_validates_bilateral_five_station_lineage_and_rejects_cross_bindings(self) -> None:
        payload = self._payload()
        context = publisher._validate_authored_torso_profile(payload)
        self.assertEqual([side["side"] for side in context["base_leg_lineage"]], ["left", "right"])
        self.assertEqual(
            [section["name"] for section in context["base_leg_lineage"][0]["sections"]],
            list(common.PROVISIONAL_FORM_LEG_PROFILE_SECTION_NAMES),
        )
        self.assertEqual(
            context["variants"]["depth-forward-v0"]["leg_lineage"][0]["sections"][4]["scaled_values_permille"]["forward"],
            227,
        )
        cases = {
            "side-order": lambda value: value["authored_leg_profile"]["sides"].reverse(),
            "source-index": lambda value: value["authored_leg_profile"]["sides"][0]["sections"][1].__setitem__("section_index", 4),
            "owner-cross-binding": lambda value: value["authored_landmarks"][value["authored_leg_profile"]["sides"][0]["sections"][3]["landmark_index"]].__setitem__("owner", next(item for item in value["authored_landmarks"] if item["role"] == "form_leg_profile_thigh_start")["owner"]),
            "dimension-index": lambda value: value["authored_leg_profile"]["sides"][0]["sections"][0]["dimension_indices"].__setitem__("lateral", value["authored_leg_profile"]["sides"][0]["sections"][1]["dimension_indices"]["lateral"]),
            "variant-radius": lambda value: value["variants"][0]["leg_profile"]["sides"][0]["sections"][0].__setitem__("forward_radius_permille", value["variants"][0]["leg_profile"]["sides"][0]["sections"][0]["forward_radius_permille"] + 1),
            "variant-position": lambda value: value["variants"][0]["leg_profile"]["sides"][0]["sections"][3]["position"].__setitem__(1, value["variants"][0]["leg_profile"]["sides"][0]["sections"][3]["position"][1] + 0.01),
        }
        def positive_but_descending(value: dict[str, object]) -> None:
            for section_index, y in enumerate((0.75, 0.25, -0.25)):
                landmark_index = value["authored_leg_profile"]["sides"][0]["sections"][section_index]["landmark_index"]
                value["authored_landmarks"][landmark_index]["position"][1] = y

        cases["positive-but-descending-source-stations"] = positive_but_descending
        for name, mutate in cases.items():
            malformed = copy.deepcopy(payload)
            mutate(malformed)
            with self.subTest(name=name):
                with self.assertRaises(publisher.SurfacePreviewPublishError):
                    publisher._validate_authored_torso_profile(malformed)

    def test_v11_authored_foot_profile_validates_hock_station_lineage_and_scaled_radii(self) -> None:
        payload = self._payload()
        context = publisher._validate_authored_torso_profile(payload)
        self.assertEqual([side["side"] for side in context["base_foot_lineage"]], ["left", "right"])
        self.assertEqual(
            [section["name"] for section in context["base_foot_lineage"][0]["sections"]],
            ["pad", "toe"],
        )
        self.assertEqual(
            context["variants"]["depth-forward-v0"]["foot_lineage"][0]["sections"][0]["scaled_values_permille"]["forward"],
            390,
        )
        cases = {
            "side-order": lambda value: value["authored_foot_profile"]["sides"].reverse(),
            "hock-side-binding": lambda value: value["authored_foot_profile"]["sides"][0]["hock_binding"].__setitem__("side_index", 1),
            "station-order": lambda value: value["authored_foot_profile"]["sides"][0]["sections"].reverse(),
            "frame-index": lambda value: value["authored_foot_profile"]["sides"][0]["sections"][0].__setitem__("frame_index", 0),
            "landmark-index": lambda value: value["authored_foot_profile"]["sides"][0]["sections"][0].__setitem__("landmark_index", value["authored_foot_profile"]["sides"][0]["sections"][1]["landmark_index"]),
            "dimension-index": lambda value: value["authored_foot_profile"]["sides"][0]["sections"][0]["dimension_indices"].__setitem__("lateral", value["authored_foot_profile"]["sides"][0]["sections"][1]["dimension_indices"]["lateral"]),
            "variant-radius": lambda value: value["variants"][0]["foot_profile"]["sides"][0]["sections"][0].__setitem__("forward_radius_permille", value["variants"][0]["foot_profile"]["sides"][0]["sections"][0]["forward_radius_permille"] + 1),
            "variant-position": lambda value: value["variants"][0]["foot_profile"]["sides"][0]["sections"][1]["position"].__setitem__(2, 0.71),
        }
        for name, mutate in cases.items():
            malformed = copy.deepcopy(payload)
            mutate(malformed)
            with self.subTest(name=name):
                with self.assertRaises(publisher.SurfacePreviewPublishError):
                    publisher._validate_authored_torso_profile(malformed)

    def test_v10_guide_foot_profile_rejects_cross_bindings_in_controls_and_paws(self) -> None:
        modes = (
            "guide-foot-profile-order",
            "guide-foot-profile-hock",
            "guide-foot-profile-lineage",
            "guide-foot-profile-center",
        )
        for index, mode in enumerate(modes):
            review_id = f"foot-guide-tamper-{index}"
            with self.subTest(mode=mode):
                with patch.object(publisher, "_parse_inspection", return_value=self._payload()):
                    with self.assertRaises(publisher.SurfacePreviewPublishError):
                        publisher.publish_surface_preview(
                            self.root,
                            self.input,
                            creature_kernel=self._producer(),
                            generator=self._generator(mode=mode),
                            successor_generator=self._successor_generator(),
                            review_id=review_id,
                        )
                self.assertFalse((self.root / review_id).exists())

    def test_v8_guide_arm_controls_reject_malformed_routes_and_preserve_valid_publication(self) -> None:
        with patch.object(publisher, "_parse_inspection", return_value=self._payload()):
            result = publisher.publish_surface_preview(
                self.root,
                self.input,
                creature_kernel=self._producer(),
                generator=self._generator(),
                successor_generator=self._successor_generator(),
                review_id="valid-arm-publication",
            )
        self.assertEqual(result["variants"], 4)
        for index, mode in enumerate((
            "guide-arm-omitted", "guide-arm-side-order", "guide-arm-source-index",
            "guide-arm-owner", "guide-arm-lineage", "guide-arm-attachment",
            "guide-arm-elbow", "guide-arm-midpoint", "guide-arm-joint-radii",
        )):
            review_id = f"arm-guide-tamper-{index}"
            with self.subTest(mode=mode):
                with patch.object(publisher, "_parse_inspection", return_value=self._payload()):
                    with self.assertRaises(publisher.SurfacePreviewPublishError):
                        publisher.publish_surface_preview(
                            self.root,
                            self.input,
                            creature_kernel=self._producer(),
                            generator=self._generator(mode=mode),
                            successor_generator=self._successor_generator(),
                            review_id=review_id,
                        )
                self.assertFalse((self.root / review_id).exists())

    def test_successor_arm_sidecar_metadata_rejects_stale_routes_and_lineage(self) -> None:
        modes = (
            "sidecar-arm-route-order",
            "sidecar-arm-route-owner",
            "sidecar-arm-elbow-ownership",
            "sidecar-arm-lineage",
        )
        for index, mode in enumerate(modes):
            review_id = f"successor-arm-tamper-{index}"
            with self.subTest(mode=mode):
                with patch.object(publisher, "_parse_inspection", return_value=self._payload()):
                    with self.assertRaises(publisher.SurfacePreviewPublishError):
                        publisher.publish_surface_preview(
                            self.root,
                            self.input,
                            creature_kernel=self._producer(),
                            generator=self._generator(),
                            successor_generator=self._successor_generator(mode=mode),
                            review_id=review_id,
                        )
                self.assertFalse((self.root / review_id).exists())

    def test_successor_v9_foot_metadata_rejects_station_and_lineage_cross_bindings(self) -> None:
        modes = ("sidecar-foot-order", "sidecar-foot-lineage", "metrics-foot-profile")
        for index, mode in enumerate(modes):
            review_id = f"successor-foot-tamper-{index}"
            with self.subTest(mode=mode):
                with patch.object(publisher, "_parse_inspection", return_value=self._payload()):
                    with self.assertRaises(publisher.SurfacePreviewPublishError):
                        publisher.publish_surface_preview(
                            self.root,
                            self.input,
                            creature_kernel=self._producer(),
                            generator=self._generator(),
                            successor_generator=self._successor_generator(mode=mode),
                            review_id=review_id,
                        )
                self.assertFalse((self.root / review_id).exists())

    def test_successor_hand_paw_metadata_rejects_metrics_and_sidecar_drift(self) -> None:
        modes = (
            "sidecar-hand-paw",
            "sidecar-hand-paw-axis",
            "sidecar-hand-paw-center",
            "sidecar-hand-paw-radius",
            "sidecar-hand-paw-owner",
            "metrics-hand-paw",
        )
        for index, mode in enumerate(modes):
            review_id = f"successor-hand-paw-tamper-{index}"
            with self.subTest(mode=mode):
                with patch.object(publisher, "_parse_inspection", return_value=self._payload()):
                    with self.assertRaisesRegex(
                        publisher.SurfacePreviewPublishError,
                        "does not match the validated guide",
                    ):
                        publisher.publish_surface_preview(
                            self.root,
                            self.input,
                            creature_kernel=self._producer(),
                            generator=self._generator(),
                            successor_generator=self._successor_generator(mode=mode),
                            review_id=review_id,
                        )
                self.assertFalse((self.root / review_id).exists())

    def test_successor_torso_lineage_and_identity_tampering_reject_without_review_directory(self) -> None:
        modes = (
            "source-cross-variant",
            "scale-mismatch",
            "sidecar-torso-owner",
            "sidecar-torso-radius",
            "sidecar-torso-exponent",
            "sidecar-head-section",
            "sidecar-head-connection",
            "sidecar-head-route-topology",
            "sidecar-head-derived-composition",
            "metrics-torso-sidecar-disagreement",
            "metrics-torso-exponent",
            "metrics-torso-owner",
            "metrics-head-cross-binding",
        )
        for index, mode in enumerate(modes):
            review_id = f"successor-torso-tamper-{index}"
            with self.subTest(mode=mode):
                with patch.object(publisher, "_parse_inspection", return_value=self._payload()):
                    with self.assertRaises(publisher.SurfacePreviewPublishError):
                        publisher.publish_surface_preview(
                            self.root,
                            self.input,
                            creature_kernel=self._producer(),
                            generator=self._generator(),
                            successor_generator=self._successor_generator(mode=mode),
                            review_id=review_id,
                        )
                self.assertFalse((self.root / review_id).exists())

    def test_publication_ignores_unusable_process_temp_default(self) -> None:
        unusable_temp = self.directory / "missing-process-temp"
        with patch.object(tempfile, "tempdir", str(unusable_temp)), patch.object(
            publisher, "_parse_inspection", return_value=self._payload()
        ):
            result = publisher.publish_surface_preview(
                self.root,
                self.input,
                creature_kernel=self._producer(),
                generator=self._generator(),
                successor_generator=self._successor_generator(),
                review_id="root-filesystem-temp",
            )

        self.assertEqual(result["assets"], 8)
        self.assertTrue((self.root / "root-filesystem-temp" / "review.json").is_file())
        self.assertFalse(unusable_temp.exists())

    def test_baseline_publication_rejects_tampered_v6_shoulder_lineage_and_derivations(self) -> None:
        cases = (
            ("guide-source-landmark", "landmarks do not match"),
            ("guide-source-frame", "frame does not match"),
            ("guide-depth-factor", "depth_control does not match"),
            ("guide-depth-scaled", "depth_control does not match"),
            ("guide-derived-anchor", "peak_anchor does not bind its expected point"),
            ("guide-derived-wrap", "authored-depth-wrap does not bind its expected point"),
            ("guide-shoulder-socket", "socket-to-upper-arm-root does not bind"),
        )
        for index, (mode, expected_error) in enumerate(cases):
            review_id = f"tampered-shoulder-{index}"
            with self.subTest(mode=mode):
                with patch.object(publisher, "_parse_inspection", return_value=self._payload()):
                    with self.assertRaisesRegex(publisher.SurfacePreviewPublishError, expected_error):
                        publisher.publish_surface_preview(
                            self.root,
                            self.input,
                            creature_kernel=self._producer(),
                            generator=self._generator(mode=mode),
                            successor_generator=self._successor_generator(),
                            review_id=review_id,
                        )
                self.assertFalse((self.root / review_id).exists())

    def test_missing_reviews_root_is_created_before_any_subprocess(self) -> None:
        missing_root = self.directory / "missing-reviews"
        calls: list[str] = []
        original_runner = publisher._run_bounded

        def observe_runner(command, *, timeout, label):
            self.assertTrue(missing_root.is_dir())
            calls.append(label)
            return original_runner(command, timeout=timeout, label=label)

        with patch.object(publisher, "_parse_inspection", return_value=self._payload()), patch.object(
            publisher, "_run_bounded", side_effect=observe_runner
        ):
            result = publisher.publish_surface_preview(
                missing_root,
                self.input,
                creature_kernel=self._producer(),
                generator=self._generator(),
                successor_generator=self._successor_generator(),
                review_id="created-root",
            )

        self.assertEqual(calls, ["creature-kernel inspection", "baseline surface generator", "successor surface generator"])
        self.assertTrue(missing_root.is_dir())
        self.assertTrue((missing_root / "created-root" / "review.json").is_file())
        self.assertEqual(result["assets"], 8)

    def test_unusable_reviews_root_fails_before_any_subprocess(self) -> None:
        unusable_root = self.directory / "reviews-file"
        unusable_root.write_text("not a directory", encoding="utf-8")
        with patch.object(publisher, "_run_bounded") as runner:
            with self.assertRaisesRegex(publisher.SurfacePreviewPublishError, "reviews root is not usable"):
                publisher.publish_surface_preview(
                    unusable_root,
                    self.input,
                    creature_kernel=self._producer(),
                    generator=self._generator(),
                    successor_generator=self._successor_generator(),
                    review_id="unusable-root",
                )
        runner.assert_not_called()

    def test_existing_and_dangling_reviews_root_symlinks_fail_before_any_subprocess(self) -> None:
        target = self.directory / "symlink-target"
        target.mkdir()
        cases = (
            (self.directory / "existing-directory-link", target),
            (self.directory / "dangling-directory-link", self.directory / "missing-target"),
        )
        for link, destination in cases:
            with self.subTest(link=link.name):
                link.symlink_to(destination, target_is_directory=True)
                with patch.object(publisher, "_run_bounded") as runner:
                    with self.assertRaisesRegex(publisher.SurfacePreviewPublishError, "reviews root is not usable"):
                        publisher.publish_surface_preview(
                            link,
                            self.input,
                            creature_kernel=self._producer(),
                            generator=self._generator(),
                            successor_generator=self._successor_generator(),
                            review_id=f"{link.stem}-root",
                        )
                runner.assert_not_called()

    def test_reviews_root_preflight_probe_is_cleaned_when_subprocess_fails(self) -> None:
        with patch.object(publisher, "_parse_inspection", return_value=self._payload()), patch.object(
            publisher, "_run_bounded", side_effect=publisher.SurfacePreviewPublishError("forced runner failure")
        ):
            with self.assertRaisesRegex(publisher.SurfacePreviewPublishError, "forced runner failure"):
                publisher.publish_surface_preview(
                    self.root,
                    self.input,
                    creature_kernel=self._producer(),
                    generator=self._generator(),
                    successor_generator=self._successor_generator(),
                    review_id="probe-cleanup",
                )
        self.assertEqual(list(self.root.iterdir()), [])

    def test_source_evidence_is_deterministic_and_context_remains_fail_closed(self) -> None:
        first = publisher._read_input_evidence(self.input)
        second = publisher._read_input_evidence(self.input)
        self.assertEqual(first, second)
        for malformed in (
            {**first, "input_body_document_encoding": "utf-16"},
            {**first, "input_body_document_bytes": True},
            {**first, "input_body_document_sha256": "not-a-hash"},
        ):
            with self.subTest(malformed=malformed):
                with self.assertRaises(publisher.SurfacePreviewPublishError):
                    publisher._validate_input_evidence(malformed)
        with self.assertRaises(common.ValidationError):
            common._subject_context({"descriptor_snapshot": "not-an-object"}, "context")

    def test_subject_context_only_uses_the_larger_exact_carrier_cap(self) -> None:
        ordinary_exact = {"value": "x" * 8_179}
        ordinary_exact_json = json.dumps(ordinary_exact, ensure_ascii=False)
        self.assertEqual(len(ordinary_exact_json.encode("utf-8")), common.MAX_STRING)
        self.assertEqual(common._metadata(ordinary_exact, "ordinary.metadata"), ordinary_exact)
        ordinary_over = {"value": "x" * 8_180}
        ordinary_over_json = json.dumps(ordinary_over, ensure_ascii=False)
        self.assertEqual(len(ordinary_over_json.encode("utf-8")), common.MAX_STRING + 1)
        with self.assertRaises(common.ValidationError):
            common._metadata(ordinary_over, "ordinary.metadata")
        self.assertEqual(common._string("x" * common.MAX_STRING, "ordinary.string"), "x" * common.MAX_STRING)
        with self.assertRaises(common.ValidationError):
            common._string("x" * (common.MAX_STRING + 1), "ordinary.string")

        accepted = {"descriptor_snapshot": {"value": "x" * 9_000}}
        accepted_json = json.dumps(accepted, ensure_ascii=False)
        accepted_size = len(accepted_json.encode("utf-8"))
        self.assertGreater(accepted_size, common.MAX_STRING)
        self.assertLessEqual(accepted_size, common.MAX_CONTEXT_JSON)
        self.assertEqual(common._subject_context(accepted, "context"), accepted)

        rejected = {"descriptor_snapshot": {"value": "x" * 12_500}}
        rejected_json = json.dumps(rejected, ensure_ascii=False)
        rejected_size = len(rejected_json.encode("utf-8"))
        self.assertGreater(rejected_size, common.MAX_CONTEXT_JSON)
        with self.assertRaises(common.ValidationError):
            common._subject_context(rejected, "context")

        multibyte_rejected = {"descriptor_snapshot": {"value": "é" * 6_200}}
        multibyte_json = json.dumps(multibyte_rejected, ensure_ascii=False)
        self.assertLess(len(multibyte_json), common.MAX_CONTEXT_JSON)
        self.assertGreater(len(multibyte_json.encode("utf-8")), common.MAX_CONTEXT_JSON)
        with self.assertRaises(common.ValidationError):
            common._subject_context(multibyte_rejected, "context")

    def test_checked_in_authored_source_identity_fits_inside_context_bound(self) -> None:
        source = (
            HERE.parents[1]
            / "examples/body-documents/stylized-digitigrade-biped-authored-form.json"
        )
        raw = source.read_bytes()
        self.assertEqual(len(raw), 56_863)
        self.assertEqual(
            hashlib.sha256(raw).hexdigest(),
            "d4f0dad6f936d62f9ee8c0fa24701898ee4ae6e48bcdeaf44641bd4dc3b549de",
        )
        evidence = publisher._validate_input_evidence(
            publisher._read_input_evidence(source), "checked-in source"
        )
        self.assertEqual(evidence["input_body_document_bytes"], len(raw))
        self.assertEqual(
            evidence["input_body_document_sha256"], hashlib.sha256(raw).hexdigest()
        )
        self.assertLess(
            len(json.dumps(evidence, ensure_ascii=False)), common.MAX_CONTEXT_JSON
        )

    def test_current_sized_producer_evidence_fits_derived_carrier_bound(self) -> None:
        target_bytes = 198_777
        chunks = []
        byte_count = 0
        index = 0
        while byte_count < target_bytes:
            chunk = hashlib.sha256(str(index).encode("ascii")).hexdigest().encode("ascii")
            chunks.append(chunk)
            byte_count += len(chunk)
            index += 1
        raw = b"".join(chunks)[:target_bytes]
        producer = self.directory / "current-sized-producer.json"
        producer.write_bytes(raw)

        evidence = publisher._read_producer_evidence(producer)
        carrier_size = len(
            json.dumps(evidence, allow_nan=False, ensure_ascii=False)
        )
        self.assertEqual(len(raw), target_bytes)
        self.assertGreater(carrier_size, common.MAX_CONTEXT_JSON)
        self.assertLessEqual(
            carrier_size,
            publisher._exact_evidence_metadata_limit(
                prefix=publisher.PRODUCER_EVIDENCE_PREFIX,
                max_bytes=publisher.MAX_STDOUT_BYTES,
            ),
        )
        self.assertEqual(
            publisher._validate_producer_evidence(evidence, "current producer"),
            evidence,
        )
        self.assertEqual(publisher._decode_producer_evidence(evidence), raw)

    def test_current_shape_compact_producer_fits_final_descriptor_context(self) -> None:
        repository = HERE.parents[1]
        source = repository / "examples/body-documents/stylized-digitigrade-biped-authored-form.json"
        completed = subprocess.run(
            [
                "cargo", "run", "--quiet", "--package", "creature-kernel-cli",
                "--bin", "creature-kernel", "--", "inspect-provisional-form",
                "--input", str(source),
            ],
            cwd=repository,
            capture_output=True,
            text=True,
            check=True,
        )
        payload = json.loads(completed.stdout)
        compact = publisher._compact_canonical_json(payload).encode("utf-8")
        self.assertEqual(payload["format"], common.PROVISIONAL_FORM_V11_FORMAT)
        self.assertTrue(compact.endswith(b"\n"))
        self.assertEqual(json.loads(compact), payload)

        compact_path = self.directory / "compact-producer.json"
        compact_path.write_bytes(compact)
        descriptor = {
            **publisher._read_input_evidence(source),
            **publisher._read_producer_evidence(compact_path),
        }
        descriptor = publisher._validate_input_evidence(
            descriptor,
            "review.subject_context.descriptor_snapshot",
            max_len=common.MAX_CONTEXT_JSON,
        )
        publisher._validate_producer_evidence(
            descriptor, "review.subject_context.descriptor_snapshot"
        )
        self.assertEqual(len(compact), 190_465)
        self.assertEqual(
            hashlib.sha256(compact).hexdigest(),
            "22f59bd768f27da8130d213f13f277c500315d3e570e62ccbdc86758a322b0d5",
        )
        self.assertEqual(descriptor["producer_envelope_bytes"], 190_465)
        self.assertEqual(
            descriptor["producer_envelope_sha256"],
            "22f59bd768f27da8130d213f13f277c500315d3e570e62ccbdc86758a322b0d5",
        )
        compressed = base64.b64decode(descriptor["producer_envelope_xz_base64"])
        self.assertEqual(len(compressed), 6_272)
        self.assertEqual(len(descriptor["producer_envelope_xz_base64"]), 8_364)
        self.assertEqual(
            hashlib.sha256(compressed).hexdigest(),
            "b5ceac6a879620e45b43e0509da8555e9208f51b9c22203b6cd40ddae25ec98c",
        )
        self.assertEqual(
            publisher._decode_producer_evidence(descriptor), compact
        )
        self.assertEqual(
            descriptor["producer_envelope_sha256"], hashlib.sha256(compact).hexdigest()
        )
        self.assertEqual(descriptor["producer_envelope_compression"], "xz")
        subject_context = {
            "descriptor_snapshot": descriptor,
        }
        subject_context_json = json.dumps(subject_context, allow_nan=False, ensure_ascii=False)
        subject_context_size = len(subject_context_json.encode("utf-8"))
        self.assertEqual(subject_context_size, 8_848)
        self.assertEqual(
            hashlib.sha256(subject_context_json.encode("utf-8")).hexdigest(),
            "aa31709ee1f71ca9899ecd7fadf0a0476722b12e9c305d37e3303919b133f4d7",
        )
        self.assertLessEqual(subject_context_size, common.MAX_CONTEXT_JSON)
        self.assertEqual(
            common._subject_context(subject_context, "manifest.subject_context"),
            subject_context,
        )

    def test_xz_producer_evidence_rejects_invalid_or_trailing_streams(self) -> None:
        producer = self.directory / "producer.json"
        producer.write_text("{}\n", encoding="utf-8")
        evidence = publisher._read_producer_evidence(producer)
        payload_field = "producer_envelope_xz_base64"
        compressed = base64.b64decode(evidence[payload_field])
        self.assertEqual(publisher._decode_producer_evidence(evidence), b"{}\n")

        # Start with a tiny valid one-filter XZ stream, then change only its
        # LZMA2 dictionary property and block-header CRC.  This keeps the test
        # fixture tiny without making the test encoder allocate that dictionary.
        excessive_dictionary = bytearray(
            lzma.compress(
                b"{}\n",
                format=lzma.FORMAT_XZ,
                check=lzma.CHECK_CRC64,
                filters=[{"id": lzma.FILTER_LZMA2, "dict_size": 1 << 20}],
            )
        )
        excessive_dictionary[16] = 0x20  # LZMA2 property for a 256 MiB dictionary.
        excessive_dictionary[20:24] = struct.pack(
            "<I", zlib.crc32(excessive_dictionary[12:20]) & 0xFFFFFFFF
        )
        malformed = (
            {**evidence, payload_field: "*"},
            {**evidence, payload_field: base64.b64encode(compressed[:-1]).decode("ascii")},
            {**evidence, payload_field: base64.b64encode(compressed + b"x").decode("ascii")},
            {
                **evidence,
                payload_field: base64.b64encode(
                    lzma.compress(b"{}\n", format=lzma.FORMAT_ALONE)
                ).decode("ascii"),
            },
            {
                **evidence,
                payload_field: base64.b64encode(excessive_dictionary).decode("ascii"),
            },
        )
        for case in malformed:
            with self.subTest(case=case[payload_field][:12]):
                with self.assertRaises(publisher.SurfacePreviewPublishError):
                    publisher._decode_producer_evidence(case)
        with self.assertRaisesRegex(
            publisher.SurfacePreviewPublishError, "invalid encoding declaration"
        ):
            publisher._validate_producer_evidence({
                **evidence,
                "producer_envelope_compression": "zlib",
            })

    def test_producer_evidence_over_derived_carrier_bound_fails_closed(self) -> None:
        producer = self.directory / "producer.json"
        producer.write_text("{}", encoding="utf-8")
        evidence = publisher._read_producer_evidence(producer)
        limit = publisher._exact_evidence_metadata_limit(
            prefix=publisher.PRODUCER_EVIDENCE_PREFIX,
            max_bytes=publisher.MAX_STDOUT_BYTES,
        )
        evidence["adversarial_padding"] = "x" * limit
        with self.assertRaisesRegex(publisher.SurfacePreviewPublishError, "too large"):
            publisher._validate_producer_evidence(evidence, "oversized producer")

    def test_malformed_count_and_unlisted_output_publish_nothing(self) -> None:
        for index, mode in enumerate(("bad-count", "unlisted", "symlink", "extra-directory", "hash", "source-mismatch", "fabricated-provenance", "fabricated-descriptor", "profile-mismatch", "component-missing", "component-extra", "component-unknown-owner", "component-wrong-recipe", "component-wrong-histogram", "component-malformed-bounds", "component-out-of-range-bounds", "component-reversed-bounds", "stale-canvas", "stale-layout", "stale-panels", "stale-format", "stale-bundle-version", "guide-format", "guide-provenance", "guide-controls", "guide-station-omitted", "guide-transition-omitted", "guide-cage-omitted", "guide-cage-malformed", "guide-cage-connection", "guide-head-section-omitted", "guide-head-section-malformed", "guide-head-connection", "guide-head-lineage", "guide-head-compatibility", "guide-shoulder-omitted", "guide-shoulder-stale-status", "guide-shoulder-consumption", "guide-shoulder-malformed", "guide-shoulder-owner", "guide-shoulder-order", "guide-shoulder-endpoint", "guide-shoulder-span", "guide-shoulder-degenerate", "guide-shoulder-points", "guide-shoulder-profile", "guide-shoulder-profile-continuity", "guide-shoulder-first-quarter", "guide-girdle-omitted", "guide-station-malformed", "guide-transition-malformed", "guide-girdle-malformed", "guide-joint-endpoint", "guide-knee-anisotropic", "guide-leg-omitted", "guide-leg-side-order", "guide-leg-owner", "guide-leg-lineage", "guide-leg-knee", "guide-leg-hock", "guide-foot-legacy", "guide-foot-order", "guide-foot-hock-source", "guide-foot-hock-radii", "guide-foot-contact", "guide-foot-taper", "guide-foot-axis", "guide-foot-gap", "guide-hand-attachment-start", "guide-hand-anchor-point", "guide-section-gap", "guide-profile-second-start", "guide-adjacent-profile", "guide-obsolete-recipe-count", "guide-wrong-recipe-count", "metrics-generated-count", "metrics-recipe-count", "manifest-metrics", "generator-recipes", "generator-ownership", "guide-omitted", "png-small", "png-truncated", "png-crc", "png-no-idat", "png-invalid-idat", "png-unknown-critical")):
            with self.subTest(mode=mode):
                with patch.object(publisher, "_parse_inspection", return_value=self._payload()):
                    with self.assertRaises(publisher.SurfacePreviewPublishError):
                        publisher.publish_surface_preview(self.root, self.input, creature_kernel=self._producer(), generator=self._generator(mode=mode), successor_generator=self._successor_generator(), review_id=f"bad-{index}")
                self.assertFalse((self.root / f"bad-{index}").exists())

    def test_generator_timeout_is_bounded(self) -> None:
        with patch.object(publisher, "_parse_inspection", return_value=self._payload()), patch.object(publisher, "GENERATOR_TIMEOUT_SECONDS", 0.05):
            with self.assertRaisesRegex(publisher.SurfacePreviewPublishError, "timed out"):
                publisher.publish_surface_preview(self.root, self.input, creature_kernel=self._producer(), generator=self._generator(mode="timeout"), successor_generator=self._successor_generator(), review_id="timeout")
        self.assertEqual(list(self.root.iterdir()), [])

    def test_baseline_and_successor_process_failures_are_bounded_and_atomic(self) -> None:
        for label, baseline_mode, successor_mode in (
            ("baseline-failure", "failure", "success"),
            ("successor-failure", "success", "failure"),
        ):
            with self.subTest(label=label):
                with patch.object(publisher, "_parse_inspection", return_value=self._payload()):
                    with self.assertRaisesRegex(publisher.SurfacePreviewPublishError, "generator failed"):
                        publisher.publish_surface_preview(
                            self.root,
                            self.input,
                            creature_kernel=self._producer(),
                            generator=self._generator(mode=baseline_mode),
                            successor_generator=self._successor_generator(mode=successor_mode),
                            review_id=label,
                        )
                self.assertEqual(list(self.root.iterdir()), [])

        for label, baseline_mode, successor_mode in (
            ("baseline-timeout", "timeout", "success"),
            ("successor-timeout", "success", "timeout"),
        ):
            with self.subTest(label=label):
                with patch.object(publisher, "_parse_inspection", return_value=self._payload()), patch.object(publisher, "GENERATOR_TIMEOUT_SECONDS", 0.05):
                    with self.assertRaisesRegex(publisher.SurfacePreviewPublishError, "timed out"):
                        publisher.publish_surface_preview(
                            self.root,
                            self.input,
                            creature_kernel=self._producer(),
                            generator=self._generator(mode=baseline_mode),
                            successor_generator=self._successor_generator(mode=successor_mode),
                            review_id=label,
                        )
                self.assertEqual(list(self.root.iterdir()), [])

    def test_successor_cli_route_accepts_both_generator_paths(self) -> None:
        output = io.StringIO()
        with patch.object(publisher, "_parse_inspection", return_value=self._payload()), redirect_stdout(output):
            result = publisher.main([
                "--root", str(self.root),
                "--input", str(self.input),
                "--creature-kernel", str(self._producer()),
                "--generator", str(self._generator()),
                "--successor-generator", str(self._successor_generator()),
                "--id", "cli-surface-test",
            ])
        self.assertEqual(result, 0)
        self.assertEqual(json.loads(output.getvalue())["assets"], 8)
        review = json.loads((self.root / "cli-surface-test" / "review.json").read_text(encoding="utf-8"))
        self.assertEqual([len(group["items"]) for group in review["groups"]], [2, 2, 2, 2])

    def test_successor_validation_fails_closed_for_representative_boundary_errors(self) -> None:
        modes = (
            "source-mismatch",
            "component-missing",
            "component-extra",
            "component-unknown-owner",
            "component-wrong-recipe",
            "component-wrong-histogram",
            "component-malformed-bounds",
            "component-out-of-range-bounds",
            "component-reversed-bounds",
            "stale-canvas",
            "stale-layout",
            "stale-panels",
            "stale-format",
            "component-visualization-omitted",
            "component-visualization-tampered",
            "frame-mismatch",
            "capture-padding-mismatch",
            "cross-variant-digest",
            "variant",
            "variant-profile",
            "inventory",
            "hash",
            "semantic-format",
            "semantic-count",
            "semantic-owner",
            "semantic-variant-hash",
            "semantic-surface-hash",
            "ply-disconnected",
            "ply-nonwatertight",
            "ply-duplicate-face",
            "ply-inconsistent-orientation",
            "ply-zero-volume",
            "ply-flattened",
            "metrics-wrong-topology",
            "extra-path",
            "invalid-png",
            "sidecar-identity",
            "sidecar-bridge",
            "sidecar-extremity",
            "sidecar-extremity-order",
            "sidecar-extremity-kind",
            "sidecar-tail",
            "sidecar-tail-shared-endpoint",
            "sidecar-shoulder-span-type",
            "sidecar-hip-root",
            "sidecar-leg-route-order",
            "sidecar-leg-owner",
            "sidecar-leg-lineage",
            "sidecar-missing-deltoid-replacement",
            "sidecar-missing-hip-replacement",
            "sidecar-stale-v2",
            "sidecar-old-shoulder",
            "sidecar-stale-v15-bridge",
            "sidecar-stale-region-id",
            "metrics-disagreement",
            "metrics-shoulder-span-type",
            "metrics-shoulder-center",
            "metrics-shoulder-depth",
            "metrics-shoulder-owner",
            "metrics-limb-source-owner",
            "metrics-leg-cross-binding",
            "metrics-hip-root",
            "metrics-replaced-count",
        )
        for index, mode in enumerate(modes):
            review_id = f"successor-bad-{index}"
            with self.subTest(mode=mode):
                with patch.object(publisher, "_parse_inspection", return_value=self._payload()):
                    expected_error = {
                        "capture-padding-mismatch": "successor capture_padding does not match validated baseline generator padding",
                        "component-missing": "component visualization",
                        "component-extra": "component visualization",
                        "component-unknown-owner": "component visualization",
                        "component-wrong-recipe": "component visualization",
                        "component-wrong-histogram": "component visualization",
                        "component-malformed-bounds": "component visualization",
                        "component-out-of-range-bounds": "component visualization",
                        "component-reversed-bounds": "component visualization",
                        "component-visualization-omitted": "unknown or missing fields",
                        "component-visualization-tampered": "component_visualization is not the exact consumed-component visualization",
                        "cross-variant-digest": "source_variant_sha256 does not match producer output",
                        "ply-disconnected": "exactly one connected component",
                        "ply-nonwatertight": "not watertight",
                        "ply-duplicate-face": "duplicate face independent of winding",
                        "ply-inconsistent-orientation": "inconsistent face orientation",
                        "ply-zero-volume": "positive enclosed volume",
                        "ply-flattened": "positive enclosed volume",
                        "metrics-wrong-topology": "metrics topology does not match",
                    }.get(mode)
                    error_context = self.assertRaisesRegex(publisher.SurfacePreviewPublishError, expected_error) if expected_error else self.assertRaises(publisher.SurfacePreviewPublishError)
                    with error_context:
                        publisher.publish_surface_preview(
                            self.root,
                            self.input,
                            creature_kernel=self._producer(),
                            generator=self._generator(),
                            successor_generator=self._successor_generator(mode=mode),
                            review_id=review_id,
                        )
                self.assertFalse((self.root / review_id).exists())
        self.assertEqual(list(self.root.iterdir()), [])

    @unittest.skipUnless(os.name == "posix", "private process groups are POSIX-specific")
    def test_run_bounded_cleans_a_child_after_successful_parent_exit(self) -> None:
        child = self.directory / "marker-child.py"
        child.write_text(textwrap.dedent("""
            import pathlib, sys, time
            time.sleep(0.25)
            pathlib.Path(sys.argv[1]).write_text("child-survived", encoding="utf-8")
        """), encoding="utf-8")
        parent = self.directory / "spawning-parent.py"
        parent.write_text(textwrap.dedent("""
            import subprocess, sys
            subprocess.Popen([sys.executable, sys.argv[1], sys.argv[2]], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print("parent-exited")
        """), encoding="utf-8")
        marker = self.directory / "child-marker.txt"
        stdout, stderr, returncode = publisher._run_bounded(
            [sys.executable, str(parent), str(child), str(marker)],
            timeout=1.0,
            label="successful parent fixture",
        )
        self.assertEqual(returncode, 0)
        self.assertEqual(stdout, b"parent-exited\n")
        self.assertEqual(stderr, b"")
        # Give a surviving child enough time to perform its write.  A private
        # process-group cleanup should have terminated it before this point.
        import time
        time.sleep(0.35)
        self.assertFalse(marker.exists())

    def test_bundle_root_symlink_is_rejected_before_manifest_access(self) -> None:
        real_bundle = self.directory / "real-bundle"
        real_bundle.mkdir()
        link = self.directory / "bundle-link"
        link.symlink_to(real_bundle, target_is_directory=True)
        with self.assertRaisesRegex(publisher.SurfacePreviewPublishError, "real non-symlink directory"):
            publisher._validate_bundle(link, "0" * 64)

    def test_regular_artifacts_scans_valid_fixture_and_enforces_entry_depth_bounds(self) -> None:
        valid = self.directory / "regular-valid"
        (valid / "neutral-v0").mkdir(parents=True)
        (valid / "neutral-v0" / "surface.ply").write_bytes(b"ply\n")
        paths, directories = publisher._regular_artifacts(valid)
        self.assertEqual(paths, {"neutral-v0/surface.ply"})
        self.assertEqual(directories, {"neutral-v0"})

        overfull = self.directory / "regular-overfull"
        overfull.mkdir()
        (overfull / "one").write_bytes(b"1")
        (overfull / "two").write_bytes(b"2")
        with patch.object(publisher, "MAX_BUNDLE_SCAN_ENTRIES", 1):
            with self.assertRaisesRegex(publisher.SurfacePreviewPublishError, "too many entries"):
                publisher._regular_artifacts(overfull)

        deep = self.directory / "regular-deep" / "a" / "b"
        deep.mkdir(parents=True)
        (deep / "surface.ply").write_bytes(b"ply\n")
        with patch.object(publisher, "MAX_BUNDLE_SCAN_DEPTH", 2):
            with self.assertRaisesRegex(publisher.SurfacePreviewPublishError, "excessive directory depth"):
                publisher._regular_artifacts(self.directory / "regular-deep")

    def test_deeply_nested_bundle_json_is_rejected_without_recursion_traceback(self) -> None:
        path = self.directory / "nested.json"
        path.write_text("{\"x\":" * 2000 + "0" + "}" * 2000, encoding="utf-8")
        with self.assertRaises(publisher.SurfacePreviewPublishError):
            publisher._read_json(path, publisher.MAX_GUIDE_BYTES, "nested guide")

    def test_missing_input_cli_error_is_concise_and_returns_two(self) -> None:
        missing = self.directory / "does-not-exist.json"
        output = io.StringIO()
        with redirect_stderr(output):
            result = publisher.main(["--root", str(self.root), "--input", str(missing)])
        self.assertEqual(result, 2)
        self.assertIn("publish-surface-preview failed:", output.getvalue())
        self.assertNotIn("Traceback", output.getvalue())

    def _stage_publisher_contract_source(self, mode: str) -> tuple[Path, Path]:
        staged_repository = self.directory / f"staged-contract-{mode}"
        staged_visual_review = staged_repository / "dev-tools" / "visual-review"
        shutil.copytree(HERE, staged_visual_review)
        source_path = HERE.parents[1] / "experiments" / "current-form-surface-preview" / "successor_surface_preview.py"
        staged_source_path = staged_repository / "experiments" / "current-form-surface-preview" / "successor_surface_preview.py"
        staged_source_path.parent.mkdir(parents=True)
        source = source_path.read_text(encoding="utf-8")
        required_name = {
            "missing-foot-section-names": "_FOOT_PROFILE_SECTION_NAMES",
            "missing-foot-owner-roles": "_FOOT_PROFILE_OWNER_ROLES",
        }.get(mode, "_FORWARD_MUZZLE_RADIUS_DONOR_SECTION_INDICES")

        def has_assignment(text: str, name: str) -> bool:
            return any(
                line.startswith(f"{name} =") or line.startswith(f"{name}:")
                for line in text.splitlines()
            )

        if mode == "missing-source":
            staged_source_path.write_text(source, encoding="utf-8")
            staged_source_path.unlink()
        elif mode == "syntax-invalid":
            staged_source_path.write_text("def (", encoding="utf-8")
        elif mode == "oversized-source":
            (staged_visual_review / "sitecustomize.py").write_text(
                "import ast\n"
                "\n"
                "def _parse_tripwire(*args, **kwargs):\n"
                "    raise RuntimeError('AST PARSE STARTED')\n"
                "\n"
                "ast.parse = _parse_tripwire\n",
                encoding="utf-8",
            )
            staged_source_path.write_bytes(
                b"# oversized successor source\n"
                + b"#" * publisher.MAX_SUCCESSOR_SOURCE_BYTES
            )
        else:
            if mode in {"missing-required", "missing-foot-section-names", "missing-foot-owner-roles"}:
                lines: list[str] = []
                skipping = False
                closing_delimiter: str | None = None
                for line in source.splitlines():
                    if not skipping and (
                        line.startswith(f"{required_name} =")
                        or line.startswith(f"{required_name}:")
                    ):
                        skipping = True
                        assignment_rhs = line.split("=", 1)[1].strip() if "=" in line else ""
                        closing_delimiter = {
                            "(": ")",
                            "[": "]",
                            "{": "}",
                        }.get(assignment_rhs)
                        continue
                    if skipping:
                        if closing_delimiter is not None and line.strip() == closing_delimiter:
                            skipping = False
                            closing_delimiter = None
                            continue
                        if not line.strip() or not line[0].isspace():
                            skipping = False
                            closing_delimiter = None
                        else:
                            continue
                    lines.append(line)
                source = "\n".join(lines) + "\n"
            elif mode == "non-literal-required":
                source += f"\n{required_name} = str(())\n"
            elif mode == "wrong-type-required":
                source += f"\n{required_name} = 7\n"
            elif mode == "wrong-shape-required":
                source += f"\n{required_name} = ((5.0, 6.0),)\n"
            elif mode == "duplicate-hand-name":
                source += "\n_HAND_PAW_SECTION_NAMES = ('hand-paw-base', 'hand-paw-base', 'hand-paw-knuckle', 'hand-paw-tip')\n"
            elif mode == "non-monotonic-hand-profile":
                source += "\n_HAND_PAW_PROFILE = ((-0.15, 0.62, 0.66), (-0.55, 1.00, 1.00), (0.35, 0.92, 1.05), (0.78, 0.55, 0.60))\n"
            elif mode == "zero-socket-pelvis-weight":
                source += "\n_HIP_ROOT_SOCKET_PELVIS_WEIGHT = 0.0\n"
            elif mode == "duplicate-foot-name":
                source += "\n_FOOT_PROFILE_SECTION_NAMES = ('hock', 'metatarsal-midpoint', 'pad', 'pad', 'toe')\n"
            elif mode == "wrong-foot-owner-roles":
                source += "\n_FOOT_PROFILE_OWNER_ROLES = ('shin', 7, 'foot', 'foot', 'foot')\n"
            elif mode == "foot-parity":
                source += "\n_FOOT_PROFILE_SECTION_NAMES = ('hock-renamed', 'metatarsal-renamed', 'pad-renamed', 'pad-toe-renamed', 'toe-renamed')\n_FOOT_PROFILE_OWNER_ROLES = ('shin-owned', 'foot-owned', 'foot-owned', 'foot-owned', 'foot-owned')\n"
            elif mode == "annotated-literal":
                if not has_assignment(source, required_name):
                    source += f"\n{required_name} = (5, 6, 7)\n"
                source = source.replace(
                    "_HAND_PAW_SECTION_NAMES = (",
                    "_HAND_PAW_SECTION_NAMES: tuple[str, ...] = (",
                    1,
                )
            else:
                self.fail(f"unknown staged contract mode: {mode}")
            staged_source_path.write_text(source, encoding="utf-8")
        return staged_repository, staged_visual_review / "publish_surface_preview.py"

    def test_successor_contract_bootstrap_failures_are_concise_in_fresh_staged_process(self) -> None:
        for mode in (
            "missing-source",
            "syntax-invalid",
            "missing-required",
            "missing-foot-section-names",
            "missing-foot-owner-roles",
            "non-literal-required",
            "wrong-type-required",
            "wrong-shape-required",
            "duplicate-hand-name",
            "non-monotonic-hand-profile",
            "zero-socket-pelvis-weight",
            "duplicate-foot-name",
            "wrong-foot-owner-roles",
        ):
            with self.subTest(mode=mode):
                _staged_repository, staged_publisher = self._stage_publisher_contract_source(mode)
                completed = subprocess.run(
                    [
                        sys.executable,
                        str(staged_publisher),
                        "--root",
                        str(self.root),
                        "--input",
                        str(self.input),
                    ],
                    cwd=_staged_repository,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertEqual(completed.returncode, 2, completed.stderr)
                self.assertEqual(completed.stdout, "")
                self.assertIn("publish-surface-preview failed:", completed.stderr)
                self.assertIn("successor contract bootstrap failed:", completed.stderr)
                expected_missing_constant = {
                    "missing-foot-section-names": "_FOOT_PROFILE_SECTION_NAMES",
                    "missing-foot-owner-roles": "_FOOT_PROFILE_OWNER_ROLES",
                }.get(mode)
                if expected_missing_constant is not None:
                    self.assertIn(
                        f"successor contract owner does not define {expected_missing_constant}",
                        completed.stderr,
                    )
                if mode == "zero-socket-pelvis-weight":
                    self.assertIn(
                        "invalid _HIP_ROOT_SOCKET_PELVIS_WEIGHT: expected a bounded finite number",
                        completed.stderr,
                    )
                self.assertNotIn("Traceback", completed.stderr)

    def test_oversized_successor_source_rejects_before_parse_or_publication(self) -> None:
        staged_repository, staged_publisher = self._stage_publisher_contract_source(
            "oversized-source"
        )
        publication_root = self.directory / "oversized-source-reviews"
        valid_input = HERE.parents[1] / "examples" / "body-documents" / "stylized-digitigrade-biped-authored-form.json"
        environment = os.environ.copy()
        environment["PYTHONPATH"] = str(staged_repository / "dev-tools" / "visual-review")
        completed = subprocess.run(
            [
                sys.executable,
                str(staged_publisher),
                "--root",
                str(publication_root),
                "--input",
                str(valid_input),
            ],
            cwd=staged_repository,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 2, completed.stderr)
        self.assertEqual(completed.stdout, "")
        self.assertIn(
            f"successor contract bootstrap failed: successor contract owner source exceeds {publisher.MAX_SUCCESSOR_SOURCE_BYTES} bytes",
            completed.stderr,
        )
        self.assertNotIn("AST PARSE STARTED", completed.stderr)
        self.assertNotIn("Traceback", completed.stderr)
        self.assertFalse(publication_root.exists())

    def test_successor_literal_fails_closed_after_captured_bootstrap_error(self) -> None:
        staged_repository, _staged_publisher = self._stage_publisher_contract_source(
            "missing-required"
        )
        probe = textwrap.dedent(
            """
            import publish_surface_preview as publisher

            assert publisher._SUCCESSOR_CONTRACT_BOOTSTRAP_ERROR is not None
            try:
                publisher._successor_literal("SUCCESSOR_REGION_ID")
            except publisher.SurfacePreviewPublishError as exc:
                assert str(exc) == publisher._SUCCESSOR_CONTRACT_BOOTSTRAP_ERROR
            else:
                raise AssertionError("bootstrap failure was not enforced")
            print("ok")
            """
        )
        environment = os.environ.copy()
        environment["PYTHONPATH"] = str(staged_repository / "dev-tools" / "visual-review")
        completed = subprocess.run(
            [sys.executable, "-c", probe],
            cwd=staged_repository,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(completed.stdout.strip(), "ok")
        self.assertEqual(completed.stderr, "")

    def test_successor_contract_projects_foot_names_and_owner_roles_in_fresh_staged_process(self) -> None:
        staged_repository, _staged_publisher = self._stage_publisher_contract_source("foot-parity")
        probe = (
            "import publish_surface_preview as publisher; "
            "assert publisher._SUCCESSOR_CONTRACT_BOOTSTRAP_ERROR is None; "
            "assert publisher.SUCCESSOR_FOOT_PROFILE_SECTION_NAMES == "
            "('hock-renamed', 'metatarsal-renamed', 'pad-renamed', 'pad-toe-renamed', 'toe-renamed'); "
            "assert publisher.SUCCESSOR_FOOT_PROFILE_OWNER_ROLES == "
            "('shin-owned', 'foot-owned', 'foot-owned', 'foot-owned', 'foot-owned'); "
            "assert publisher.SUCCESSOR_EXTREMITY_STATION_NAMES[2] == "
            "publisher.SUCCESSOR_FOOT_PROFILE_SECTION_NAMES; "
            "print('ok')"
        )
        environment = os.environ.copy()
        environment["PYTHONPATH"] = str(staged_repository / "dev-tools" / "visual-review")
        completed = subprocess.run(
            [sys.executable, "-c", probe],
            cwd=staged_repository,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(completed.stdout.strip(), "ok")
        self.assertEqual(completed.stderr, "")

    def test_successor_contract_accepts_annotated_literal_in_fresh_staged_process(self) -> None:
        staged_repository, _staged_publisher = self._stage_publisher_contract_source("annotated-literal")
        probe = (
            "import publish_surface_preview as publisher; "
            "assert publisher._SUCCESSOR_CONTRACT_BOOTSTRAP_ERROR is None; "
            "assert publisher.SUCCESSOR_HAND_PAW_SECTION_NAMES == "
            "('hand-paw-base', 'hand-paw-palm', 'hand-paw-knuckle', 'hand-paw-tip'); "
            "print('ok')"
        )
        environment = os.environ.copy()
        environment["PYTHONPATH"] = str(staged_repository / "dev-tools" / "visual-review")
        completed = subprocess.run(
            [sys.executable, "-c", probe],
            cwd=staged_repository,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(completed.stdout.strip(), "ok")
        self.assertEqual(completed.stderr, "")


if __name__ == "__main__":
    unittest.main()
