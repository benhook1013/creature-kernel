from __future__ import annotations

import copy
import hashlib
import importlib.util
import io
import json
import os
import struct
import sys
import tempfile
import textwrap
import unittest
import zlib
from contextlib import redirect_stderr
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

    @staticmethod
    def _chunk(kind: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(data, zlib.crc32(kind)) & 0xFFFFFFFF)

    @classmethod
    def _png(cls, *, width: int = 1800, height: int = 570, include_idat: bool = True, invalid_idat: bool = False, unknown_chunk: bool = False) -> bytes:
        ihdr = cls._chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        raw = b"".join(b"\x00" + b"\x00" * (width * 3) for _ in range(height))
        compressed = b"not-a-zlib-stream" if invalid_idat else zlib.compress(raw)
        idat = cls._chunk(b"IDAT", compressed) if include_idat else b""
        extra = cls._chunk(b"ABCD", b"unknown") if unknown_chunk else b""
        return b"\x89PNG\r\n\x1a\n" + ihdr + extra + idat + cls._chunk(b"IEND", b"")

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
            import hashlib, json, pathlib, struct, sys, time
            args = dict(zip(sys.argv[1::2], sys.argv[2::2]))
            out = pathlib.Path(args["--output"])
            source_hash = hashlib.sha256(pathlib.Path(args["--input"]).read_bytes()).hexdigest()
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
            canvas = {{"width": 1800, "height": 570, "mode": "RGB"}}
            projections = [{{"name": "front", "basis": [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]], "base": "x-right/y-up/z-depth"}}, {{"name": "side", "basis": [[0.0, 0.0, -1.0], [0.0, 1.0, 0.0], [1.0, 0.0, 0.0]], "base": "-z-right/y-up/x-depth"}}, {{"name": "three-quarter", "basis": [[0.7071067811865475, 0.0, -0.7071067811865475], [0.0, 1.0, 0.0], [0.7071067811865475, 0.0, 0.7071067811865475]], "base": "front-right/y-up/depth"}}]
            layout = {{"panel_order": ["front-guide", "front-skin", "side-guide", "side-skin", "three-quarter-guide", "three-quarter-skin"], "panels": [{{"id": "front-guide", "projection": "front", "content": "guide", "box": [12, 72, 292, 548]}}, {{"id": "front-skin", "projection": "front", "content": "skin", "box": [310, 72, 590, 548]}}, {{"id": "side-guide", "projection": "side", "content": "guide", "box": [608, 72, 888, 548]}}, {{"id": "side-skin", "projection": "side", "content": "skin", "box": [906, 72, 1186, 548]}}, {{"id": "three-quarter-guide", "projection": "three-quarter", "content": "guide", "box": [1204, 72, 1484, 548]}}, {{"id": "three-quarter-skin", "projection": "three-quarter", "content": "skin", "box": [1502, 72, 1782, 548]}}], "pairing": "guide-left/skin-right per projection", "frame": "shared-world-bounds-and-projection-basis"}}
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
                head = {{"owners": [owners[3], owners[2]], "masses": [mass("cranium"), mass("muzzle"), mass("neck-collar")], "sections": [path("head-transition"), path("neck-transition")]}}
                limb_specs = [(owners[4], ("pre-joint", "joint"), ("root",), ("shoulder-girdle",), ("elbow",)), (owners[5], ("proximal", "distal"), (), (), ()), (owners[7], ("pre-joint", "joint"), ("root",), ("shoulder-girdle",), ("elbow",)), (owners[8], ("proximal", "distal"), (), (), ()), (owners[10], ("pre-joint", "joint"), ("root", "hip"), ("hip-girdle",), ("knee",)), (owners[11], ("pre-joint", "joint"), (), (), ("hock",)), (owners[13], ("pre-joint", "joint"), ("root", "hip"), ("hip-girdle",), ("knee",)), (owners[14], ("pre-joint", "joint"), (), (), ("hock",))]
                limbs = []
                for owner, section_names, bridge_names, mass_names, joint_names in limb_specs:
                    section_values = [path(control, "capsule") for control in section_names]
                    if len(section_values) == 2: section_values[1]["points"] = [list(section_values[0]["points"][1]), [1.0, 0.0, 0.0]]
                    anchors = []
                    if owner["role"] == "forearm":
                        anchors = [{{"name": "forearm-distal-boundary", "kind": "parent-surface-anchor", "point": [0.25, 0.0, 0.0], "boundary_point": [1.0, 0.0, 0.0]}}]
                    elif owner["role"] == "shin":
                        anchors = [{{"name": "hock-endpoint", "kind": "endpoint", "point": [1.0, 0.0, 0.0], "boundary_point": [1.0, 0.0, 0.0]}}]
                    limb = {{"owner": owner, "profile_controls": [0.2, 0.2, 0.2], "sections": section_values, "bridges": [path(control, "tapered-segment") for control in bridge_names], "masses": [mass(control) for control in mass_names], "joints": [{{"name": name, "owner": owner, "mass": {{**mass(name), "center": [1.0, 0.0, 0.0], "radii": [0.14, 0.14, 0.14]}}, "adjacent_profiles": [0.2, (0.5 if name == "hock" else 0.2)]}} for name in joint_names], "anchors": anchors}}
                    limbs.append(limb)
                paws = []
                for owner in [owners[6], owners[9], owners[12], owners[15]]:
                    if owner["role"] == "foot":
                        parent = next(candidate for candidate in owners if candidate["role"] == "shin" and candidate["anchors"] == owner["anchors"])
                        metatarsal = path("metatarsal", "tapered-segment"); metatarsal["points"] = [[1.0, 0.0, 0.0], [1.0, -0.2, 0.5]]; metatarsal["thickness"] = [0.5, 0.3]
                        pad = mass("paw-pad"); pad["center"] = [1.0, -0.2, 0.5]; pad["radii"] = [0.4, 0.2, 0.3]
                        toe = mass("toe-box"); toe["center"] = [1.0, -0.2, 1.0]; toe["radii"] = [0.35, 0.2, 0.25]
                        hock = mass("hock-anchor"); hock["center"] = [1.0, 0.0, 0.0]; hock["radii"] = [0.14, 0.14, 0.14]
                        hock_source = {{"owner": parent, "anchor": "hock-endpoint", "point": [1.0, 0.0, 0.0], "boundary_point": [1.0, 0.0, 0.0]}}
                        paws.append({{"owner": owner, "chain": {{"hock": hock, "metatarsal": metatarsal, "masses": [pad, toe], "contact_height": -0.4, "axes": {{"lateral": [1.0, 0.0, 0.0], "up": [0.0, 1.0, 0.0], "forward": [0.0, 0.0, 1.0]}}}}, "hock_source": hock_source}})
                    else:
                        paw = mass("paw")
                        attachment = path("attachment", "capsule"); attachment["points"] = [[0.25, 0.0, 0.0], paw["center"]]
                        parent = next(candidate for candidate in owners if candidate["role"] == "forearm" and candidate["anchors"] == owner["anchors"])
                        attachment_source = {{"owner": parent, "anchor": "forearm-distal-boundary", "point": list(attachment["points"][0]), "boundary_point": [1.0, 0.0, 0.0]}}
                        paws.append({{"owner": owner, "masses": [paw], "attachment": attachment, "attachment_source": attachment_source}})
                tails = [{{"owner": owners[16], "centerline": path("segment", "tapered-segment"), "sections": [path("root-attachment", "tapered-segment")], "masses": [mass("root-collar")]}}, {{"owner": owners[17], "centerline": path("segment", "tapered-segment"), "sections": [path("tip-extension", "tapered-segment")], "masses": [mass("tip-cap")]}}]
                cage_sections = [
                    {{"name": "lower-pelvis", "owner": owners[0], "center": [0.0, -1.0, 0.0], "lateral_radius": 0.5, "depth_radius": 0.5}},
                    {{"name": "upper-pelvis", "owner": owners[0], "center": [0.0, -0.5, 0.0], "lateral_radius": 0.5, "depth_radius": 0.5}},
                    {{"name": "lower-abdomen", "owner": owners[1], "center": [0.0, -0.25, 0.0], "lateral_radius": 0.5, "depth_radius": 0.5}},
                    {{"name": "waist-abdomen", "owner": owners[1], "center": [0.0, 0.0, 0.0], "lateral_radius": 0.5, "depth_radius": 0.5}},
                    {{"name": "upper-abdomen", "owner": owners[1], "center": [0.0, 0.25, 0.0], "lateral_radius": 0.5, "depth_radius": 0.5}},
                    {{"name": "lower-ribcage", "owner": owners[1], "center": [0.0, 0.5, 0.0], "lateral_radius": 0.5, "depth_radius": 0.5}},
                    {{"name": "upper-ribcage-shoulder", "owner": owners[1], "center": [0.0, 1.0, 0.0], "lateral_radius": 0.5, "depth_radius": 0.5}},
                ]
                torso_cage = {{"status": "skin-driving torso controls", "owners": [owners[0], owners[1]], "axes": {{"lateral": [1.0, 0.0, 0.0], "up": [0.0, 1.0, 0.0], "forward": [0.0, 0.0, 1.0]}}, "orientation": "elliptical cross-section rings lie in the lateral/forward plane and rise along the up axis", "sections": cage_sections, "connections": [{{"from": cage_sections[index]["name"], "to": cage_sections[index + 1]["name"]}} for index in range(6)]}}
                def shoulder_curve(name, owner, points, profile):
                    return {{"name": name, "owner": owner, "points": points, "profile": profile, "consumption": ("skin-driving" if name == "deltoid-sweep" else "guide-only")}}
                shoulder_sides = []
                for side_name, side_owner, sign in (("left", owners[4], -1.0), ("right", owners[7], 1.0)):
                    shoulder_sides.append({{"side": side_name, "owner": side_owner, "socket": {{"owner": side_owner, "point": [sign * 1.5, 0.9, 0.0]}}, "extremum": {{"owner": side_owner, "point": [sign * 1.0, 1.0, 0.0]}}, "span": 1.0, "slope": 0.0, "curves": [
                        shoulder_curve("anterior-support", owners[1], [[0.0, 1.0, 0.0], [sign * 0.5, 1.05, 0.25], [sign * 1.0, 1.0, 0.0], [sign * 1.5, 0.9, 0.0]], [0.2, 0.2, 0.2, 0.2]),
                        shoulder_curve("posterior-return", owners[1], [[0.0, 1.0, 0.0], [sign * 0.5, 1.05, -0.25], [sign * 1.0, 1.0, 0.0], [sign * 1.5, 0.9, 0.0]], [0.2, 0.2, 0.2, 0.2]),
                        shoulder_curve("deltoid-sweep", side_owner, [[sign * 1.0, 1.0, 0.0], [sign * 1.5, 0.9, 0.0], [-0.25, 0.0, 0.0]], [0.2, 0.2, 0.2]),
                    ]}})
                shoulder_frame = {{"status": "private shoulder frame; support curves guide-only; deltoid sweep skin-driving", "owners": {{"torso": owners[1], "neck": owners[2], "left_upper_arm": owners[4], "right_upper_arm": owners[7]}}, "central": {{"owner": owners[1], "anchor": [0.0, 1.0, 0.0], "profile": [0.2, 0.2]}}, "sides": shoulder_sides}}
                guide = {{"format": {publisher.REGIONAL_GUIDE_FORMAT!r}, "variant": variant_id, "owners": owners, "counts": {publisher.EXPECTED_GUIDE_COUNTS!r}, "projections": projections, "shared_render_bounds": bounds, "canvas": canvas, "layout": layout, "controls": {{"axes": {{"lateral": [1.0, 0.0, 0.0], "up": [0.0, 1.0, 0.0], "forward": [0.0, 0.0, 1.0]}}, "axial": axial, "torso_cage": torso_cage, "shoulder_frame": shoulder_frame, "head": head, "limbs": limbs, "paws": paws, "tails": tails}}, "boundary": "private disposable regional controls; source-owned AddressKeys only; not a semantic or runtime contract"}}
                if {mode!r} == "guide-obsolete-recipe-count":
                    guide["counts"] = dict(guide["counts"])
                    guide["counts"]["compiled_field_recipe_counts"] = dict(guide["counts"]["compiled_field_recipe_counts"])
                    guide["counts"]["compiled_fields"] = 54
                    guide["counts"]["compiled_field_recipe_counts"].update({{"hip-girdle": 2, "shoulder-mass": 2}})
                if {mode!r} == "guide-wrong-recipe-count":
                    guide["counts"] = dict(guide["counts"])
                    guide["counts"]["compiled_field_recipe_counts"] = dict(guide["counts"]["compiled_field_recipe_counts"])
                    guide["counts"]["compiled_field_recipe_counts"]["torso-cage"] = 2
                if {mode!r} == "guide-format": guide["format"] = "wrong"
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
                if {mode!r} == "guide-girdle-malformed": guide["controls"]["limbs"][2]["masses"][0]["control"] = "wrong"
                if {mode!r} == "guide-joint-endpoint": guide["controls"]["limbs"][2]["joints"][0]["mass"]["center"][0] = 0.0
                if {mode!r} == "guide-foot-legacy": guide["controls"]["paws"][2] = {{"owner": owners[12], "masses": [], "attachment": {{}}, "attachment_source": {{}}}}
                if {mode!r} == "guide-foot-order": guide["controls"]["paws"][2]["chain"]["masses"][1]["center"][2] = -1.0
                if {mode!r} == "guide-foot-hock-source": guide["controls"]["paws"][2]["hock_source"]["point"][0] = 0.5
                if {mode!r} == "guide-foot-hock-radii": guide["controls"]["paws"][2]["chain"]["hock"]["radii"][0] = 0.13
                if {mode!r} == "guide-foot-contact": guide["controls"]["paws"][2]["chain"]["masses"][0]["center"][1] = 0.0
                if {mode!r} == "guide-foot-taper": guide["controls"]["paws"][2]["chain"]["metatarsal"]["thickness"] = [0.3, 0.5]
                if {mode!r} == "guide-foot-axis": guide["controls"]["paws"][2]["chain"]["axes"]["forward"] = [0.0, 0.0, 2.0]
                if {mode!r} == "guide-foot-gap": guide["controls"]["paws"][2]["chain"]["masses"][1]["center"][2] = 4.8
                if {mode!r} == "guide-hand-attachment-start": guide["controls"]["paws"][0]["attachment"]["points"][0][2] = 0.75
                if {mode!r} == "guide-hand-anchor-point": guide["controls"]["limbs"][1]["anchors"][0]["point"][2] = 0.75
                if {mode!r} == "guide-section-gap": guide["controls"]["limbs"][2]["sections"][1]["points"][0][0] = 0.4
                if {mode!r} == "guide-profile-second-start": guide["controls"]["limbs"][2]["sections"][1]["thickness"][0] = 0.19
                if {mode!r} == "guide-adjacent-profile": guide["controls"]["limbs"][2]["joints"][0]["adjacent_profiles"][1] = 0.99
                guide_path = directory / "regional-guide.json"
                guide_path.write_text(json.dumps(guide), encoding="utf-8")
                if {mode!r} == "guide-omitted": guide_path.unlink()
                metrics_payload = {{"source_descriptor_count": 18, "generated_field_count": 52, "field_recipe_counts": {dict(publisher.EXPECTED_GUIDE_COUNTS["compiled_field_recipe_counts"])!r}}}
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
                    if kind == "guide-skin-composite-png": item.update({{"width": (1 if {mode!r} == "png-small" else 1800), "height": (1 if {mode!r} == "png-small" else 570), "views": ["front", "side", "three-quarter"], "panels_per_view": 2, "mode": "RGB"}})
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
            manifest = {{"format": {publisher.SURFACE_PREVIEW_FORMAT!r}, "status": "success", "source_format": {common.PROVISIONAL_FORM_FORMAT!r}, "source": {{"format": {common.PROVISIONAL_FORM_FORMAT!r}, "sha256": source_hash, "document": "fixture", "namespace": "main", "resource_profile_id": "ck.resource.body.r2", "reference_scale": {{"parent": {{**owners[2], "anchors": []}}, "child": {{**owners[3], "anchors": []}}, "axis_delta": [0, 1, 0], "squared_length": 1, "source": "exact-containment-edge"}}}}, "shared_render_bounds": bounds, "canvas": canvas, "layout": layout, "projections": projections, "generator": {{"bundle_version": 2, "samples_per_axis": 72, "padding": 0.75, "smooth_union": {{"operator": "polynomial_cubic_smooth_min", "k": 0.12, "fold_order": "source_address_then_recipe_order"}}, "field_primitives": ["ellipsoid", "capsule", "linear-radius-tapered-segment"], "field_recipes": generator_field_recipes, "ownership": generator_ownership, "boundary": "disposable exploratory visual proof; not production geometry, SDF, collision, rig, topology, or Readiness evidence"}}, "variants": variants}}
            (out / "surface-preview-manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        """), encoding="utf-8")
        path.chmod(0o755)
        return path

    def _payload(self) -> dict[str, object]:
        owner_specs = [("pelvis", []), ("torso", []), ("neck", []), ("head", []), ("upper_arm", ["left"]), ("forearm", ["left"]), ("hand", ["left"]), ("upper_arm", ["right"]), ("forearm", ["right"]), ("hand", ["right"]), ("thigh", ["left"]), ("shin", ["left"]), ("foot", ["left"]), ("thigh", ["right"]), ("shin", ["right"]), ("foot", ["right"]), ("tail_root", ["tail"]), ("tail_tip", ["tail"])]
        owners = [{"namespace": "main", "anchors": anchors, "kind": "part", "role": role} for role, anchors in owner_specs]
        source = {"document": "fixture", "namespace": "main", "resource_profile_id": common.PROVISIONAL_FORM_RESOURCE_PROFILE}
        reference_scale = {"parent": owners[2], "child": owners[3], "axis_delta": [0, 1, 0], "squared_length": 1, "source": "exact-containment-edge"}
        return {
            "format": common.PROVISIONAL_FORM_FORMAT,
            "source": source,
            "reference_scale": reference_scale,
            "variants": [{"id": variant_id, "profile_id": variant_id, "descriptors": [{"address": owner} for owner in owners]} for variant_id in common.PROVISIONAL_FORM_VARIANT_IDS],
        }

    def test_address_validation_accepts_empty_anchors_and_rejects_malformed_entries(self) -> None:
        valid = {"namespace": "main", "anchors": [], "kind": "part", "role": "neck"}
        self.assertEqual(publisher._validate_address(valid, "address"), valid)
        for anchors in (None, [""], [1], "neck"):
            with self.subTest(anchors=anchors):
                with self.assertRaises(publisher.SurfacePreviewPublishError):
                    publisher._validate_address({**valid, "anchors": anchors}, "address")

    def test_success_stubs_both_executables_and_publishes_only_pngs(self) -> None:
        self.assertEqual(publisher.EXPECTED_GUIDE_COUNTS["compiled_fields"], 52)
        self.assertEqual(publisher.EXPECTED_GUIDE_COUNTS["shoulder_frame_compiled_fields"], 2)
        self.assertNotIn("hip-girdle", publisher.EXPECTED_GUIDE_COUNTS["compiled_field_recipe_counts"])
        self.assertNotIn("shoulder-mass", publisher.EXPECTED_GUIDE_COUNTS["compiled_field_recipe_counts"])
        with patch.object(publisher, "_parse_inspection", return_value=self._payload()):
            result = publisher.publish_surface_preview(
                self.root,
                self.input,
                creature_kernel=self._producer(),
                generator=self._generator(),
                review_id="surface-test",
            )
        session = Path(result["session"])
        self.assertEqual(result["variants"], 4)
        self.assertEqual(sorted(p.name for p in (session / "assets").iterdir()), sorted(f"{v}.png" for v in common.PROVISIONAL_FORM_VARIANT_IDS))
        review = json.loads((session / "review.json").read_text(encoding="utf-8"))
        self.assertIn("subject_context", review)
        self.assertEqual(review["groups"][0]["selection_mode"], "none")

    def test_malformed_count_and_unlisted_output_publish_nothing(self) -> None:
        for index, mode in enumerate(("bad-count", "unlisted", "symlink", "extra-directory", "hash", "source-mismatch", "fabricated-provenance", "fabricated-descriptor", "profile-mismatch", "guide-format", "guide-provenance", "guide-controls", "guide-station-omitted", "guide-transition-omitted", "guide-cage-omitted", "guide-cage-malformed", "guide-cage-connection", "guide-shoulder-omitted", "guide-shoulder-stale-status", "guide-shoulder-consumption", "guide-shoulder-malformed", "guide-shoulder-owner", "guide-shoulder-order", "guide-shoulder-endpoint", "guide-shoulder-span", "guide-shoulder-degenerate", "guide-shoulder-points", "guide-shoulder-profile", "guide-shoulder-profile-continuity", "guide-shoulder-first-quarter", "guide-girdle-omitted", "guide-station-malformed", "guide-transition-malformed", "guide-girdle-malformed", "guide-joint-endpoint", "guide-foot-legacy", "guide-foot-order", "guide-foot-hock-source", "guide-foot-hock-radii", "guide-foot-contact", "guide-foot-taper", "guide-foot-axis", "guide-foot-gap", "guide-hand-attachment-start", "guide-hand-anchor-point", "guide-section-gap", "guide-profile-second-start", "guide-adjacent-profile", "guide-obsolete-recipe-count", "guide-wrong-recipe-count", "metrics-generated-count", "metrics-recipe-count", "manifest-metrics", "generator-recipes", "generator-ownership", "guide-omitted", "png-small", "png-truncated", "png-crc", "png-no-idat", "png-invalid-idat", "png-unknown-critical")):
            with self.subTest(mode=mode):
                with patch.object(publisher, "_parse_inspection", return_value=self._payload()):
                    with self.assertRaises(publisher.SurfacePreviewPublishError):
                        publisher.publish_surface_preview(self.root, self.input, creature_kernel=self._producer(), generator=self._generator(mode=mode), review_id=f"bad-{index}")
                self.assertFalse((self.root / f"bad-{index}").exists())

    def test_generator_timeout_is_bounded(self) -> None:
        with patch.object(publisher, "_parse_inspection", return_value=self._payload()), patch.object(publisher, "GENERATOR_TIMEOUT_SECONDS", 0.05):
            with self.assertRaisesRegex(publisher.SurfacePreviewPublishError, "timed out"):
                publisher.publish_surface_preview(self.root, self.input, creature_kernel=self._producer(), generator=self._generator(mode="timeout"), review_id="timeout")
        self.assertEqual(list(self.root.iterdir()), [])

    def test_bundle_root_symlink_is_rejected_before_manifest_access(self) -> None:
        real_bundle = self.directory / "real-bundle"
        real_bundle.mkdir()
        link = self.directory / "bundle-link"
        link.symlink_to(real_bundle, target_is_directory=True)
        with self.assertRaisesRegex(publisher.SurfacePreviewPublishError, "real non-symlink directory"):
            publisher._validate_bundle(link, "0" * 64)

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


if __name__ == "__main__":
    unittest.main()
