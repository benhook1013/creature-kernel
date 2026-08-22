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
            if {mode!r} == "failure":
                print("fixture generator failed", file=sys.stderr)
                raise SystemExit(3)
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

    def _successor_generator(self, *, mode: str = "success") -> Path:
        """Write a small valid successor-v2 fixture, with bounded mutations."""

        path = self.directory / f"successor-generator-{mode}.py"
        script = textwrap.dedent("""
            #!/usr/bin/env python3
            import hashlib, json, pathlib, sys, time

            MODE = __MODE__
            PNG = __PNG__
            CANVAS = __CANVAS__
            PROJECTIONS = __PROJECTIONS__
            LAYOUT = __LAYOUT__
            BOUNDS = __BOUNDS__
            SUCCESSOR_FORMAT = __SUCCESSOR_FORMAT__
            CONSUMER_ID = __CONSUMER_ID__
            REGION_ID = __REGION_ID__
            EXTREMITY_ORDER = __EXTREMITY_ORDER__
            EXTREMITY_KINDS = __EXTREMITY_KINDS__
            TAIL_ORDER = __TAIL_ORDER__
            TAIL_KINDS = __TAIL_KINDS__
            REPLACED = __REPLACED__
            MESH_PADDING = __MESH_PADDING__
            CAPTURE_PADDING = __CAPTURE_PADDING__

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
            source = {"format": payload["format"], "sha256": hashlib.sha256(source_path.read_bytes()).hexdigest(), **payload["source"], "reference_scale": payload["reference_scale"]}
            if MODE == "source-mismatch":
                source["sha256"] = "0" * 64
            frame = {"canvas": CANVAS, "projections": PROJECTIONS, "layout": LAYOUT, "shared_render_bounds": BOUNDS}
            if MODE == "frame-mismatch":
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
                (variant_dir / "surface.ply").write_bytes(b"ply\\n")
                bridge = {"enabled": True, "consumer": "baseline-analytic-fields", "regions": ["limb-root-connectors", "hip-transitions"], "field_count": 6, "retained_recipes": ["hip-transition", "root-bridge"]}
                replaced = list(REPLACED)
                sidecar = {
                    "format": SUCCESSOR_FORMAT,
                    "variant_id": variant_id,
                    "profile_id": variant_id,
                    "source_variant_sha256": source_variant_sha256,
                    "consumer_id": CONSUMER_ID,
                    "successor_region_id": REGION_ID,
                    "capture": frame,
                    "torso": {"representation": "frame-aware-ordered-profile-sweep", "sections_consumed": 7, "section_names": ["a", "b", "c", "d", "e", "f", "g"]},
                    "shoulders": {"representation": "distal-deltoid-swept-curve-spans", "spans_consumed": 2, "curve": "deltoid-sweep", "span_index": 1},
                    "head_neck": {"representation": "shared-guide-derived-profile-sweeps", "sweeps_consumed": 5, "sweep_order": ["a", "b", "c", "d", "e"], "section_counts": [1, 1, 1, 1, 1], "owner_keys": ["a", "b", "c", "d", "e"]},
                    "limbs": {"representation": "shared-guide-derived-ordered-profile-sweeps", "sweeps_consumed": 4, "sweep_order": ["a", "b", "c", "d"], "station_counts": [1, 1, 1, 1], "station_names": [["a"], ["b"], ["c"], ["d"]], "section_owner_keys": [["a"], ["b"], ["c"], ["d"]], "endpoint_cap_counts": [1, 1, 1, 1]},
                    "extremities": {"representation": "shared-guide-derived-hand-and-digitigrade-foot-profile-sweeps", "sweeps_consumed": 6, "sweep_order": EXTREMITY_ORDER, "sweep_kinds": EXTREMITY_KINDS, "station_counts": [1] * 6, "station_names": [["a"]] * 6, "section_owner_keys": [["a"]] * 6, "endpoint_cap_counts": [1] * 6, "internal_transition_counts": [0] * 6},
                    "tail": {"representation": "shared-guide-derived-profile-sweep-elements", "elements_consumed": 6, "element_order": TAIL_ORDER, "element_kinds": TAIL_KINDS, "section_counts": [1] * 6, "section_names": [["a"]] * 6, "owner_keys": ["a"] * 6, "endpoint_cap_counts": [1] * 6, "internal_transition_counts": [0] * 6, "controls": [], "tip_shared_endpoint": {}},
                    "temporary_bridge": bridge,
                    "replaced_baseline_recipes": replaced,
                }
                metrics = {"consumer_id": CONSUMER_ID, "successor_region_id": REGION_ID, "successor_region": {"shoulder_representation": "distal-deltoid-swept-curve-spans", "shoulder_spans_consumed": 2, "shoulder_curve": "deltoid-sweep", "shoulder_span_index": 1, "extremity_sweeps_consumed": 6, "tail_elements_consumed": 6, "replaced_baseline_recipes": replaced}, "temporary_bridge": bridge}
                if MODE == "sidecar-identity":
                    sidecar["consumer_id"] = "wrong-consumer"
                elif MODE == "sidecar-bridge":
                    sidecar["temporary_bridge"] = {**bridge, "field_count": 7}
                elif MODE == "sidecar-extremity":
                    sidecar["extremities"] = {**sidecar["extremities"], "sweeps_consumed": 5}
                elif MODE == "sidecar-extremity-order":
                    sidecar["extremities"] = {**sidecar["extremities"], "sweep_order": list(reversed(sidecar["extremities"]["sweep_order"]))}
                elif MODE == "sidecar-extremity-kind":
                    sidecar["extremities"] = {**sidecar["extremities"], "sweep_kinds": ["wrong", *sidecar["extremities"]["sweep_kinds"][1:]]}
                elif MODE == "sidecar-tail":
                    sidecar["tail"] = {**sidecar["tail"], "elements_consumed": 5}
                elif MODE == "sidecar-shoulder-span-type":
                    sidecar["shoulders"] = {**sidecar["shoulders"], "span_index": True}
                elif MODE == "sidecar-missing-deltoid-replacement":
                    sidecar["replaced_baseline_recipes"] = [recipe for recipe in replaced if recipe != "deltoid-sweep-1"]
                (variant_dir / "successor.json").write_text(json.dumps(sidecar, sort_keys=True), encoding="utf-8")
                metrics_file = dict(metrics)
                if MODE == "metrics-disagreement":
                    metrics_file["successor_region"] = {**metrics["successor_region"], "tail_elements_consumed": 5}
                elif MODE == "metrics-shoulder-span-type":
                    metrics_file["successor_region"] = {**metrics["successor_region"], "shoulder_span_index": 1.0}
                metrics_record = metrics_file if MODE == "metrics-shoulder-span-type" else metrics
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
                    entry("metrics", variant_dir / "metrics.json"),
                    entry("successor-consumer-sidecar", variant_dir / "successor.json"),
                    entry("guide-skin-composite-png", png, {"width": 1800, "height": 570, "views": ["front", "side", "three-quarter"], "panels_per_view": 2, "mode": "RGB"}),
                ]
                if MODE == "inventory":
                    inventory[0] = {**inventory[0], "path": variant_id + "/wrong.ply"}
                if MODE == "hash":
                    inventory[0] = {**inventory[0], "sha256": "0" * 64}
                if MODE == "invalid-png":
                    png.write_bytes(PNG[:-1])
                    inventory[-1] = entry("guide-skin-composite-png", png, {"width": 1800, "height": 570, "views": ["front", "side", "three-quarter"], "panels_per_view": 2, "mode": "RGB"})
                records.append({"id": variant_id, "profile_id": ("wrong" if MODE == "variant-profile" and not records else variant_id), "source_variant_sha256": source_variant_sha256, "metrics": metrics_record, "inventory": inventory})
            if MODE == "variant":
                records.pop()
            if MODE == "extra-path":
                (out / "extra.bin").write_bytes(b"unlisted")
            manifest = {"format": SUCCESSOR_FORMAT, "status": "success", "consumer_id": CONSUMER_ID, "source_format": payload["format"], "source": source, "shared_render_bounds": frame["shared_render_bounds"], "canvas": frame["canvas"], "layout": frame["layout"], "projections": frame["projections"], "generator": {"samples_per_axis": 56, "padding": MESH_PADDING, "capture_padding": CAPTURE_PADDING, "smooth_k": 0.12, "consumer_boundary": "successor torso/shoulder/head/neck, four limb chains, bilateral hands, digitigrade feet, and tail; baseline temporary bridge for root/hip connectors", "production_status": "disposable exploratory proof"}, "variants": records}
            (out / "successor-surface-manifest.json").write_text(json.dumps(manifest, sort_keys=True), encoding="utf-8")
        """)
        replacements = {
            "__MODE__": repr(mode),
            "__PNG__": repr(self._png()),
            "__CANVAS__": repr(publisher.EXPECTED_CANVAS),
            "__PROJECTIONS__": repr(publisher.EXPECTED_PROJECTIONS),
            "__LAYOUT__": repr(publisher.EXPECTED_LAYOUT),
            "__BOUNDS__": repr({"min": [-5.0, -5.0, -5.0], "max": [5.0, 5.0, 5.0]}),
            "__SUCCESSOR_FORMAT__": repr(publisher.SUCCESSOR_PREVIEW_FORMAT),
            "__CONSUMER_ID__": repr(publisher.SUCCESSOR_CONSUMER_ID),
            "__REGION_ID__": repr(publisher.SUCCESSOR_REGION_ID),
            "__EXTREMITY_ORDER__": repr(list(publisher.SUCCESSOR_EXTREMITY_ORDER)),
            "__EXTREMITY_KINDS__": repr(list(publisher.SUCCESSOR_EXTREMITY_KINDS)),
            "__TAIL_ORDER__": repr(list(publisher.SUCCESSOR_TAIL_ORDER)),
            "__TAIL_KINDS__": repr(list(publisher.SUCCESSOR_TAIL_KINDS)),
            "__REPLACED__": repr(sorted(publisher.SUCCESSOR_REQUIRED_REPLACED_RECIPES)),
            "__MESH_PADDING__": repr(0.5),
            "__CAPTURE_PADDING__": repr(0.5 if mode == "capture-padding-mismatch" else 0.75),
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

    def test_success_publishes_four_ordered_baseline_successor_pairs(self) -> None:
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
            self.assertEqual(baseline["metadata"]["views"], ["front", "side", "three-quarter"])
            self.assertEqual(successor["metadata"]["views"], baseline["metadata"]["views"])
            self.assertEqual(baseline["metadata"]["panels_per_view"], successor["metadata"]["panels_per_view"])
            self.assertEqual(successor["metadata"]["generator"]["padding"], 0.5)
            self.assertEqual(successor["metadata"]["generator"]["capture_padding"], 0.75)
            self.assertNotEqual(successor["metadata"]["generator"]["padding"], successor["metadata"]["generator"]["capture_padding"])
            self.assertEqual(set(successor["metadata"]["generator"]), {"samples_per_axis", "padding", "capture_padding", "smooth_k", "consumer_boundary", "production_status"})
            self.assertIn("shared capture frame", baseline["description"])
            self.assertIn("same shared capture frame", successor["description"])
        self.assertEqual(review["subject_context"]["descriptor_snapshot"]["images"], 8)
        self.assertEqual(review["subject_context"]["descriptor_snapshot"]["source_sha256"], review["groups"][0]["items"][0]["metadata"]["source_sha256"])
        self.assertIn("same source and shared front/side/three-quarter framing", review["subject_context"]["authored_summary"]["text"])
        self.assertIn("compare baseline first and successor second", review["instructions"])
        self.assertIn("overall creature coherence", review["instructions"])
        self.assertIn("same source and framing", review["subject_context"]["provenance"]["capture"])
        self.assertEqual(review["subject_context"]["provenance"]["baseline_generator_script"], "generator-success.py")
        self.assertEqual(review["subject_context"]["provenance"]["successor_generator_script"], "successor-generator-success.py")
        self.assertEqual(review["subject_context"]["provenance"]["successor_generator"]["padding"], 0.5)
        self.assertEqual(review["subject_context"]["provenance"]["successor_generator"]["capture_padding"], 0.75)
        self.assertIn("Disposable, non-production", review["subject_context"]["provenance"]["limitations"])

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

    def test_malformed_count_and_unlisted_output_publish_nothing(self) -> None:
        for index, mode in enumerate(("bad-count", "unlisted", "symlink", "extra-directory", "hash", "source-mismatch", "fabricated-provenance", "fabricated-descriptor", "profile-mismatch", "guide-format", "guide-provenance", "guide-controls", "guide-station-omitted", "guide-transition-omitted", "guide-cage-omitted", "guide-cage-malformed", "guide-cage-connection", "guide-shoulder-omitted", "guide-shoulder-stale-status", "guide-shoulder-consumption", "guide-shoulder-malformed", "guide-shoulder-owner", "guide-shoulder-order", "guide-shoulder-endpoint", "guide-shoulder-span", "guide-shoulder-degenerate", "guide-shoulder-points", "guide-shoulder-profile", "guide-shoulder-profile-continuity", "guide-shoulder-first-quarter", "guide-girdle-omitted", "guide-station-malformed", "guide-transition-malformed", "guide-girdle-malformed", "guide-joint-endpoint", "guide-foot-legacy", "guide-foot-order", "guide-foot-hock-source", "guide-foot-hock-radii", "guide-foot-contact", "guide-foot-taper", "guide-foot-axis", "guide-foot-gap", "guide-hand-attachment-start", "guide-hand-anchor-point", "guide-section-gap", "guide-profile-second-start", "guide-adjacent-profile", "guide-obsolete-recipe-count", "guide-wrong-recipe-count", "metrics-generated-count", "metrics-recipe-count", "manifest-metrics", "generator-recipes", "generator-ownership", "guide-omitted", "png-small", "png-truncated", "png-crc", "png-no-idat", "png-invalid-idat", "png-unknown-critical")):
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
            "frame-mismatch",
            "capture-padding-mismatch",
            "cross-variant-digest",
            "variant",
            "variant-profile",
            "inventory",
            "hash",
            "extra-path",
            "invalid-png",
            "sidecar-identity",
            "sidecar-bridge",
            "sidecar-extremity",
            "sidecar-extremity-order",
            "sidecar-extremity-kind",
            "sidecar-tail",
            "sidecar-shoulder-span-type",
            "sidecar-missing-deltoid-replacement",
            "metrics-disagreement",
            "metrics-shoulder-span-type",
        )
        for index, mode in enumerate(modes):
            review_id = f"successor-bad-{index}"
            with self.subTest(mode=mode):
                with patch.object(publisher, "_parse_inspection", return_value=self._payload()):
                    expected_error = {
                        "capture-padding-mismatch": "successor capture_padding does not match validated baseline generator padding",
                        "cross-variant-digest": "source_variant_sha256 does not match producer output",
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


if __name__ == "__main__":
    unittest.main()
