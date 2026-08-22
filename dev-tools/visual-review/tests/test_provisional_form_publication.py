from __future__ import annotations

import copy
import importlib.util
import json
import os
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.request import urlopen


HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))


def load_module(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, HERE / filename)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


import common
serve = load_module("provisional_form_serve", "serve.py")
publisher = load_module("provisional_form_publisher", "publish_provisional_form.py")


def fixed_display_factors(profile_id: str, role: str, shape_name: str) -> tuple[int, ...]:
    if shape_name == "ellipsoid":
        if profile_id == "neutral-v0":
            return (1_000, 1_000, 1_000)
        if profile_id == "broad-soft-v0":
            if role in {"pelvis", "torso", "head"}:
                return (1_200, 1_000, 1_150)
            if role in {"hand", "foot"}:
                return (1_150, 1_000, 1_150)
            return (1_000, 1_000, 1_000)
        if profile_id == "lean-readable-v0":
            return (800, 1_000, 800)
        if profile_id == "depth-forward-v0":
            if role in {"torso", "head", "foot"}:
                return (1_000, 1_000, 1_300)
            return (1_000, 1_000, 1_000)
    if shape_name == "capsule":
        return ((1_150 if profile_id == "broad-soft-v0" else 800 if profile_id == "lean-readable-v0" else 1_000),)
    if shape_name == "tapered-segment":
        factor = 1_150 if profile_id == "broad-soft-v0" else 800 if profile_id == "lean-readable-v0" else 1_000
        return (factor, factor)
    raise AssertionError(f"unsupported fixture shape {shape_name!r}")


def apply_fixed_display_factors(item: dict[str, object], profile_id: str) -> None:
    shape = item["shape"]
    role = item["address"]["role"]
    factors = fixed_display_factors(profile_id, role, shape["name"])
    if shape["name"] == "ellipsoid":
        shape["axis_extents_permille"] = [
            value * factor // 1_000
            for value, factor in zip(shape["axis_extents_permille"], factors)
        ]
    elif shape["name"] == "capsule":
        shape["radius_permille"] = shape["radius_permille"] * factors[0] // 1_000
    else:
        shape["start_radius_permille"] = shape["start_radius_permille"] * factors[0] // 1_000
        shape["end_radius_permille"] = shape["end_radius_permille"] * factors[1] // 1_000


class ProvisionalFormPublicationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.directory = Path(self.temp.name)
        self.root = self.directory / "reviews"
        self.root.mkdir()
        self.input = self.directory / "body.json"
        self.input.write_text("{}", encoding="utf-8")
        address = {"namespace": "main", "anchors": [], "kind": "part", "role": "pelvis"}
        self.payload = {
            "format": common.PROVISIONAL_FORM_FORMAT,
            "operation": common.PROVISIONAL_FORM_OPERATION,
            "status": "success",
            "stage": common.PROVISIONAL_FORM_STAGE,
            "processing_complete": True,
            "diagnostics_complete": True,
            "diagnostics": [],
            "source": {"document": "fixture", "namespace": "main", "resource_profile_id": common.PROVISIONAL_FORM_RESOURCE_PROFILE},
            "reference_scale": {"parent": {**address, "role": "pelvis"}, "child": {**address, "role": "torso"}, "axis_delta": [0, 1, 0], "squared_length": 1, "source": "exact-containment-edge"},
            "authored_dimensions": [
                {"owner": {**address, "role": "pelvis"}, "role": "form_extent_x", "value_permille": 1000, "provenance": {"source": common.PROVISIONAL_FORM_AUTHORED_DIMENSION_PROVENANCE, "document": "fixture", "namespace": "main"}},
                {"owner": {**address, "role": "pelvis"}, "role": "form_extent_y", "value_permille": 900, "provenance": {"source": common.PROVISIONAL_FORM_AUTHORED_DIMENSION_PROVENANCE, "document": "fixture", "namespace": "main"}},
                {"owner": {**address, "role": "pelvis"}, "role": "form_extent_z", "value_permille": 800, "provenance": {"source": common.PROVISIONAL_FORM_AUTHORED_DIMENSION_PROVENANCE, "document": "fixture", "namespace": "main"}},
                {"owner": {**address, "role": "torso"}, "role": "form_extent_x", "value_permille": 1000, "provenance": {"source": common.PROVISIONAL_FORM_AUTHORED_DIMENSION_PROVENANCE, "document": "fixture", "namespace": "main"}},
                {"owner": {**address, "role": "torso"}, "role": "form_extent_y", "value_permille": 1000, "provenance": {"source": common.PROVISIONAL_FORM_AUTHORED_DIMENSION_PROVENANCE, "document": "fixture", "namespace": "main"}},
                {"owner": {**address, "role": "torso"}, "role": "form_extent_z", "value_permille": 900, "provenance": {"source": common.PROVISIONAL_FORM_AUTHORED_DIMENSION_PROVENANCE, "document": "fixture", "namespace": "main"}},
            ],
            "variants": [],
            "limitations": "Provisional display-only geometry descriptors; no production geometry or Readiness 3.",
        }
        for variant_id in common.PROVISIONAL_FORM_VARIANT_IDS:
            descriptor = {
                "descriptor_kind": "display-only-form-descriptor",
                "address": address,
                "parent": None,
                "placement_source": "authored-root",
                "reference_point": [0, 0, 0],
                "dimension_roles": ["form_extent_x", "form_extent_y", "form_extent_z"],
                "profile_id": variant_id,
                "source": common.PROVISIONAL_FORM_PROVENANCE,
                "provenance": {"source": common.PROVISIONAL_FORM_PROVENANCE, "resource_profile_id": common.PROVISIONAL_FORM_RESOURCE_PROFILE, "shape_basis": common.PROVISIONAL_FORM_SHAPE_BASIS},
                "shape": {"name": "ellipsoid", "center": [0, 0, 0], "axis_extents_permille": [1000, 900, 800]},
            }
            torso = copy.deepcopy(descriptor)
            torso["address"] = {**address, "role": "torso"}
            torso["parent"] = {**address, "role": "pelvis"}
            torso["placement_source"] = "authored-containment"
            torso["reference_point"] = [0, 1, 0]
            torso["shape"]["center"] = [0, 1, 0]
            torso["shape"]["axis_extents_permille"] = [1000, 1000, 900]
            apply_fixed_display_factors(descriptor, variant_id)
            apply_fixed_display_factors(torso, variant_id)
            self.payload["variants"].append({"id": variant_id, "profile_id": variant_id, "provenance": {"source": common.PROVISIONAL_FORM_PROVENANCE, "resource_profile_id": common.PROVISIONAL_FORM_RESOURCE_PROFILE, "shape_basis": common.PROVISIONAL_FORM_SHAPE_BASIS}, "descriptors": [descriptor, torso]})

    def tearDown(self) -> None:
        self.temp.cleanup()

    def fake_binary(self, body: str, name: str = "fake-kernel") -> Path:
        binary = self.directory / name
        binary.write_text("#!/usr/bin/env python3\n" + body, encoding="utf-8")
        binary.chmod(0o755)
        return binary

    def publish_with(self, binary: Path, **kwargs: object) -> Path:
        summary = publisher.publish_provisional_form(self.root, self.input, creature_kernel=binary, **kwargs)
        return Path(summary["session"])

    def capsule_payload(
        self, *, format_name: str = common.PROVISIONAL_FORM_FORMAT
    ) -> dict[str, object]:
        """Build a small body chain under either versioned capsule contract."""

        def address(role: str, anchors: list[str] | None = None) -> dict[str, object]:
            return {"namespace": "main", "anchors": anchors or [], "kind": "part", "role": role}

        def descriptor(
            role: str,
            point: list[int],
            parent: dict[str, object] | None,
            shape: dict[str, object],
        ) -> dict[str, object]:
            dimension_roles = {
                "ellipsoid": ["form_extent_x", "form_extent_y", "form_extent_z"],
                "capsule": ["form_radius"],
                "tapered-segment": ["form_start_radius", "form_end_radius"],
            }[shape["name"]]
            return {
                "descriptor_kind": "display-only-form-descriptor",
                "address": address(role),
                "parent": parent,
                "placement_source": "authored-root" if parent is None else "authored-containment",
                "reference_point": point,
                "dimension_roles": dimension_roles,
                "profile_id": "neutral-v0",
                "source": common.PROVISIONAL_FORM_PROVENANCE,
                "provenance": {
                    "source": common.PROVISIONAL_FORM_PROVENANCE,
                    "resource_profile_id": common.PROVISIONAL_FORM_RESOURCE_PROFILE,
                    "shape_basis": common.PROVISIONAL_FORM_SHAPE_BASIS,
                },
                "shape": shape,
            }

        pelvis = address("pelvis")
        torso = address("torso")
        neck = address("neck")
        head = address("head")
        upper_arm = address("upper_arm")
        forearm = address("forearm")
        hand = address("hand")
        neck_shape = (
            {"name": "capsule", "from": [0, 2, 0], "to": [0, 3, 0], "radius_permille": 500}
            if format_name in {
                common.PROVISIONAL_FORM_HISTORICAL_V4_FORMAT,
                common.PROVISIONAL_FORM_FORMAT,
            }
            else {"name": "ellipsoid", "center": [0, 2, 0], "axis_extents_permille": [650, 600, 600]}
        )
        descriptors = [
            descriptor("pelvis", [0, 0, 0], None, {"name": "ellipsoid", "center": [0, 0, 0], "axis_extents_permille": [1000, 900, 800]}),
            descriptor("torso", [0, 1, 0], pelvis, {"name": "ellipsoid", "center": [0, 1, 0], "axis_extents_permille": [1000, 1000, 900]}),
            descriptor("neck", [0, 2, 0], torso, neck_shape),
            descriptor("head", [0, 3, 0], neck, {"name": "ellipsoid", "center": [0, 3, 0], "axis_extents_permille": [1000, 1000, 900]}),
            descriptor("upper_arm", [-1, 2, 0], torso, {"name": "capsule", "from": [-1, 2, 0], "to": [-2, 2, 0], "radius_permille": 200}),
            descriptor("forearm", [-2, 2, 0], upper_arm, {"name": "capsule", "from": [-2, 2, 0], "to": [-3, 2, 0], "radius_permille": 180}),
            descriptor("hand", [-3, 2, 0], forearm, {"name": "ellipsoid", "center": [-3, 2, 0], "axis_extents_permille": [450, 400, 350]}),
        ]
        descriptors.sort(key=lambda item: (
            item["address"]["namespace"], tuple(item["address"]["anchors"]),
            item["address"]["kind"], item["address"]["role"],
        ))
        payload = copy.deepcopy(self.payload)
        payload["format"] = format_name
        payload["authored_dimensions"] = []
        for item in descriptors:
            shape = item["shape"]
            if shape["name"] == "ellipsoid":
                values = shape["axis_extents_permille"]
            elif shape["name"] == "capsule":
                values = [shape["radius_permille"]]
            else:
                values = [shape["start_radius_permille"], shape["end_radius_permille"]]
            for role, value in zip(item["dimension_roles"], values):
                payload["authored_dimensions"].append({
                    "owner": copy.deepcopy(item["address"]),
                    "role": role,
                    "value_permille": value,
                    "provenance": {
                        "source": common.PROVISIONAL_FORM_AUTHORED_DIMENSION_PROVENANCE,
                        "document": "fixture",
                        "namespace": "main",
                    },
                })
        if format_name == common.PROVISIONAL_FORM_LEGACY_FORMAT:
            points = {
                item["address"]["role"]: item["reference_point"]
                for item in descriptors
            }
            parent_roles = {"upper_arm": "torso", "forearm": "upper_arm"}
            for item in descriptors:
                role = item["address"]["role"]
                if role in parent_roles:
                    item["shape"]["from"] = points[parent_roles[role]]
                    item["shape"]["to"] = item["reference_point"]
        payload["reference_scale"] = {
            "parent": upper_arm,
            "child": forearm,
            "axis_delta": [-1, 0, 0],
            "squared_length": 1,
            "source": "exact-containment-edge",
        }
        payload["variants"] = []
        for variant_id in common.PROVISIONAL_FORM_VARIANT_IDS:
            variant_descriptors = copy.deepcopy(descriptors)
            for item in variant_descriptors:
                item["profile_id"] = variant_id
                if format_name == common.PROVISIONAL_FORM_FORMAT:
                    apply_fixed_display_factors(item, variant_id)
            payload["variants"].append({
                "id": variant_id,
                "profile_id": variant_id,
                "provenance": {
                    "source": common.PROVISIONAL_FORM_PROVENANCE,
                    "resource_profile_id": common.PROVISIONAL_FORM_RESOURCE_PROFILE,
                    "shape_basis": common.PROVISIONAL_FORM_SHAPE_BASIS,
                },
                "descriptors": variant_descriptors,
            })
        if format_name != common.PROVISIONAL_FORM_FORMAT:
            payload.pop("authored_dimensions")
            for variant in payload["variants"]:
                variant["provenance"].pop("shape_basis")
                for item in variant["descriptors"]:
                    item.pop("dimension_roles")
                    item["provenance"].pop("shape_basis")
        return payload

    def test_success_publishes_distinct_immutable_form_session_and_route(self) -> None:
        self.assertEqual(self.payload["format"], common.PROVISIONAL_FORM_FORMAT)
        binary = self.fake_binary("import json, sys\nsys.stdout.write(" + repr(json.dumps(self.payload)) + ")\n")
        session = self.publish_with(binary, review_id="form-review", title="Filled form")
        review = json.loads((session / "review.json").read_text(encoding="utf-8"))
        self.assertEqual(review["kind"], "provisional-form")
        self.assertEqual(review["provisional_form"], self.payload)
        self.assertEqual(list((session / "assets").iterdir()), [])
        self.payload["variants"][0]["descriptors"][0]["shape"]["center"][0] = 9
        self.assertEqual(json.loads((session / "review.json").read_text())["provisional_form"]["variants"][0]["descriptors"][0]["shape"]["center"], [0, 0, 0])
        server = serve.create_server(self.root, 0)
        thread = threading.Thread(target=server.serve_forever)
        thread.start()
        try:
            with urlopen(f"http://127.0.0.1:{server.server_port}/api/reviews/form-review") as response:
                body = json.load(response)
            self.assertEqual(body["review"]["kind"], "provisional-form")
            self.assertEqual(len(body["review"]["provisional_form"]["variants"]), 4)
        finally:
            server.shutdown(); thread.join(); server.server_close()

    def test_v5_rejects_tampered_authored_dimension_with_unchanged_descriptors(self) -> None:
        payload = copy.deepcopy(self.payload)
        payload["authored_dimensions"][0]["value_permille"] += 1
        with self.assertRaisesRegex(
            common.ValidationError,
            "shape numeric controls do not match source-authored dimensions",
        ):
            common._validate_provisional_form_envelope(
                payload, "tampered authored dimension fixture"
            )

    def test_v5_rejects_tampered_non_neutral_variant_shape_control(self) -> None:
        payload = copy.deepcopy(self.payload)
        payload["variants"][1]["descriptors"][1]["shape"]["axis_extents_permille"][0] += 1
        with self.assertRaisesRegex(
            common.ValidationError,
            "shape numeric controls do not match source-authored dimensions",
        ):
            common._validate_provisional_form_envelope(
                payload, "tampered non-neutral variant fixture"
            )

    def test_v5_rejects_unconsumed_authored_dimension(self) -> None:
        payload = copy.deepcopy(self.payload)
        payload["authored_dimensions"].append({
            "owner": copy.deepcopy(payload["authored_dimensions"][0]["owner"]),
            "role": "form_unconsumed",
            "value_permille": 100,
            "provenance": {
                "source": common.PROVISIONAL_FORM_AUTHORED_DIMENSION_PROVENANCE,
                "document": "fixture",
                "namespace": "main",
            },
        })
        payload["authored_dimensions"].sort(key=lambda item: (
            item["owner"]["namespace"], tuple(item["owner"]["anchors"]),
            item["owner"]["kind"], item["owner"]["role"], item["role"],
        ))
        with self.assertRaisesRegex(
            common.ValidationError,
            "authored_dimensions must equal the complete descriptor-consumed control set",
        ):
            common._validate_provisional_form_envelope(payload, "extra v5 dimension fixture")

    def test_unknown_and_malformed_payloads_fail_closed(self) -> None:
        cases = [
            {"unknown": True},
            {"variants": list(reversed(self.payload["variants"]))},
            {"shape": {"name": "mesh"}},
            {"reference_scale": {"axis_delta": [0, 1, 0], "squared_length": 2}},
            {"point": [1.5, 0, 0]},
            {"permille": 0},
        ]
        for index, change in enumerate(cases):
            payload = copy.deepcopy(self.payload)
            if "unknown" in change:
                payload["unexpected"] = True
            elif "variants" in change:
                payload["variants"] = change["variants"]
            elif "shape" in change:
                payload["variants"][0]["descriptors"][0]["shape"] = {"name": "mesh"}
            elif "reference_scale" in change:
                payload["reference_scale"]["squared_length"] = 2
            elif "point" in change:
                payload["variants"][0]["descriptors"][0]["reference_point"] = [1.5, 0, 0]
            else:
                payload["variants"][0]["descriptors"][0]["shape"]["axis_extents_permille"][0] = 0
            binary = self.fake_binary("import json, sys\nsys.stdout.write(" + repr(json.dumps(payload)) + ")\n", f"bad-{index}")
            with self.assertRaises(publisher.ProvisionalFormPublishError):
                self.publish_with(binary, review_id=f"bad-form-{index}")
            self.assertFalse((self.root / f"bad-form-{index}").exists())

    def test_v2_through_v5_limb_capsules_use_their_direct_distal_child_anchor(self) -> None:
        for format_name in (
            common.PROVISIONAL_FORM_V2_FORMAT,
            common.PROVISIONAL_FORM_V3_FORMAT,
            common.PROVISIONAL_FORM_HISTORICAL_V4_FORMAT,
            common.PROVISIONAL_FORM_FORMAT,
        ):
            with self.subTest(format_name=format_name):
                payload = self.capsule_payload(format_name=format_name)
                validated = common._validate_provisional_form_envelope(
                    payload, "capsule fixture"
                )
                self.assertEqual(validated["format"], format_name)

                old_parent_center = copy.deepcopy(payload)
                for descriptor in old_parent_center["variants"][0]["descriptors"]:
                    if descriptor["address"]["role"] == "upper_arm":
                        descriptor["shape"]["from"] = [0, 1, 0]
                        break
                with self.assertRaisesRegex(
                    common.ValidationError,
                    "start does not match its reference point",
                ):
                    common._validate_provisional_form_envelope(
                        old_parent_center, "old capsule fixture"
                    )

        payload = self.capsule_payload()

        missing_distal = copy.deepcopy(payload)
        for variant in missing_distal["variants"]:
            variant["descriptors"] = [
                descriptor
                for descriptor in variant["descriptors"]
                if descriptor["address"]["role"] != "forearm"
            ]
        with self.assertRaisesRegex(common.ValidationError, "missing its direct forearm child"):
            common._validate_provisional_form_envelope(missing_distal, "missing capsule fixture")

        ambiguous = self.capsule_payload()
        for variant in ambiguous["variants"]:
            descriptors = variant["descriptors"]
            forearm = next(item for item in descriptors if item["address"]["role"] == "forearm")
            duplicate_forearm = copy.deepcopy(forearm)
            duplicate_forearm["address"]["anchors"] = ["branch"]
            duplicate_forearm["reference_point"] = [-2, 3, 0]
            duplicate_forearm["shape"]["from"] = [-2, 3, 0]
            duplicate_forearm["shape"]["to"] = [-3, 3, 0]
            duplicate_hand = next(item for item in descriptors if item["address"]["role"] == "hand")
            duplicate_hand = copy.deepcopy(duplicate_hand)
            duplicate_hand["address"]["anchors"] = ["branch"]
            duplicate_hand["parent"] = duplicate_forearm["address"]
            duplicate_hand["reference_point"] = [-3, 3, 0]
            duplicate_hand["shape"]["center"] = [-3, 3, 0]
            descriptors.extend([duplicate_forearm, duplicate_hand])
            descriptors.sort(key=lambda item: (
                item["address"]["namespace"], tuple(item["address"]["anchors"]),
                item["address"]["kind"], item["address"]["role"],
            ))
        ambiguous["authored_dimensions"].extend([
            {
                "owner": {"namespace": "main", "anchors": ["branch"], "kind": "part", "role": "forearm"},
                "role": "form_radius",
                "value_permille": 180,
                "provenance": {"source": common.PROVISIONAL_FORM_AUTHORED_DIMENSION_PROVENANCE, "document": "fixture", "namespace": "main"},
            },
            *[
                {
                    "owner": {"namespace": "main", "anchors": ["branch"], "kind": "part", "role": "hand"},
                    "role": role,
                    "value_permille": value,
                    "provenance": {"source": common.PROVISIONAL_FORM_AUTHORED_DIMENSION_PROVENANCE, "document": "fixture", "namespace": "main"},
                }
                for role, value in (
                    ("form_extent_x", 450),
                    ("form_extent_y", 400),
                    ("form_extent_z", 350),
                )
            ],
        ])
        ambiguous["authored_dimensions"].sort(key=lambda item: (
            item["owner"]["namespace"], tuple(item["owner"]["anchors"]),
            item["owner"]["kind"], item["owner"]["role"], item["role"],
        ))
        with self.assertRaisesRegex(common.ValidationError, "ambiguous direct forearm children"):
            common._validate_provisional_form_envelope(ambiguous, "ambiguous capsule fixture")

    def test_v5_neck_capsule_requires_exactly_one_direct_head_endpoint(self) -> None:
        payload = self.capsule_payload()
        validated = common._validate_provisional_form_envelope(payload, "v5 neck fixture")
        self.assertEqual(validated["format"], common.PROVISIONAL_FORM_FORMAT)

        neck_ellipsoid = copy.deepcopy(payload)
        for descriptor in neck_ellipsoid["variants"][0]["descriptors"]:
            if descriptor["address"]["role"] == "neck":
                descriptor["shape"] = {
                    "name": "ellipsoid",
                    "center": descriptor["reference_point"],
                    "axis_extents_permille": [650, 600, 600],
                }
                break
        with self.assertRaisesRegex(
            common.ValidationError, "must be capsule for role neck"
        ):
            common._validate_provisional_form_envelope(
                neck_ellipsoid, "v5 ellipsoid neck fixture"
            )

        wrong_endpoint = copy.deepcopy(payload)
        for descriptor in wrong_endpoint["variants"][0]["descriptors"]:
            if descriptor["address"]["role"] == "neck":
                descriptor["shape"]["to"] = [0, 4, 0]
                break
        with self.assertRaisesRegex(
            common.ValidationError, "end does not match its direct head child point"
        ):
            common._validate_provisional_form_envelope(
                wrong_endpoint, "v5 wrong neck endpoint fixture"
            )

        missing_head = copy.deepcopy(payload)
        for variant in missing_head["variants"]:
            variant["descriptors"] = [
                descriptor
                for descriptor in variant["descriptors"]
                if descriptor["address"]["role"] != "head"
            ]
        with self.assertRaisesRegex(
            common.ValidationError, "missing its direct head child"
        ):
            common._validate_provisional_form_envelope(
                missing_head, "v5 missing head fixture"
            )

        ambiguous_head = copy.deepcopy(payload)
        for variant in ambiguous_head["variants"]:
            descriptors = variant["descriptors"]
            head = next(
                item for item in descriptors if item["address"]["role"] == "head"
            )
            extra_head = copy.deepcopy(head)
            extra_head["address"]["anchors"] = ["branch"]
            extra_head["reference_point"] = [0, 4, 0]
            extra_head["shape"]["center"] = [0, 4, 0]
            descriptors.append(extra_head)
            descriptors.sort(key=lambda item: (
                item["address"]["namespace"], tuple(item["address"]["anchors"]),
                item["address"]["kind"], item["address"]["role"],
            ))
        ambiguous_head["authored_dimensions"].extend([
            {
                "owner": {"namespace": "main", "anchors": ["branch"], "kind": "part", "role": "head"},
                "role": role,
                "value_permille": value,
                "provenance": {"source": common.PROVISIONAL_FORM_AUTHORED_DIMENSION_PROVENANCE, "document": "fixture", "namespace": "main"},
            }
            for role, value in (
                ("form_extent_x", 1000),
                ("form_extent_y", 1000),
                ("form_extent_z", 900),
            )
        ])
        ambiguous_head["authored_dimensions"].sort(key=lambda item: (
            item["owner"]["namespace"], tuple(item["owner"]["anchors"]),
            item["owner"]["kind"], item["owner"]["role"], item["role"],
        ))
        with self.assertRaisesRegex(
            common.ValidationError, "ambiguous direct head children"
        ):
            common._validate_provisional_form_envelope(
                ambiguous_head, "v5 ambiguous head fixture"
            )

        for prior_format in (
            common.PROVISIONAL_FORM_LEGACY_FORMAT,
            common.PROVISIONAL_FORM_V2_FORMAT,
            common.PROVISIONAL_FORM_V3_FORMAT,
            common.PROVISIONAL_FORM_HISTORICAL_V4_FORMAT,
        ):
            prior = self.capsule_payload(format_name=prior_format)
            prior["format"] = common.PROVISIONAL_FORM_FORMAT
            with self.subTest(prior_format=prior_format), self.assertRaisesRegex(
                common.ValidationError, "authored_dimensions is required for v5"
            ):
                common._validate_provisional_form_envelope(
                    prior, "prior payload mislabeled v5"
                )

    def test_v1_capsules_retain_legacy_parent_to_current_contract(self) -> None:
        legacy = self.capsule_payload(
            format_name=common.PROVISIONAL_FORM_LEGACY_FORMAT
        )
        common._validate_provisional_form_envelope(legacy, "legacy capsule fixture")

        normalized = common.validate_normalized_review(
            {
                "schema_version": 1,
                "id": "legacy-form",
                "title": "Legacy form",
                "kind": "provisional-form",
                "groups": [],
                "provisional_form": legacy,
            },
            self.directory,
            check_assets=False,
        )
        self.assertEqual(
            normalized["provisional_form"]["format"],
            common.PROVISIONAL_FORM_LEGACY_FORMAT,
        )

        corrected_mislabeled_v1 = self.capsule_payload(
            format_name=common.PROVISIONAL_FORM_V2_FORMAT
        )
        corrected_mislabeled_v1["format"] = common.PROVISIONAL_FORM_LEGACY_FORMAT
        with self.assertRaisesRegex(common.ValidationError, "capsule endpoints are invalid"):
            common._validate_provisional_form_envelope(
                corrected_mislabeled_v1, "corrected payload mislabeled v1"
            )

        for corrected_format in (
            common.PROVISIONAL_FORM_V2_FORMAT,
            common.PROVISIONAL_FORM_V3_FORMAT,
        ):
            legacy_mislabeled_corrected = copy.deepcopy(legacy)
            legacy_mislabeled_corrected["format"] = corrected_format
            with self.subTest(corrected_format=corrected_format), self.assertRaisesRegex(
                common.ValidationError, "start does not match its reference point"
            ):
                common._validate_provisional_form_envelope(
                    legacy_mislabeled_corrected,
                    "legacy payload mislabeled corrected",
                )

    def test_nonzero_output_bound_timeout_and_collision_are_bounded(self) -> None:
        noisy = self.fake_binary(f"import sys\nsys.stdout.write('x' * {publisher.MAX_STDOUT_BYTES + 1})\n", "noisy")
        with self.assertRaises(publisher.ProvisionalFormPublishError):
            self.publish_with(noisy, review_id="noisy")
        slow = self.fake_binary("import time\ntime.sleep(30)\n", "slow")
        with patch.object(publisher, "INSPECTION_TIMEOUT_SECONDS", 0.05):
            with self.assertRaisesRegex(publisher.ProvisionalFormPublishError, "timed out"):
                self.publish_with(slow, review_id="slow")
        failed = self.fake_binary("import sys\nsys.stderr.write('failed')\nsys.exit(9)\n", "failed")
        with self.assertRaises(publisher.ProvisionalFormPublishError):
            self.publish_with(failed, review_id="failed")
        valid = self.fake_binary("import json, sys\nsys.stdout.write(" + repr(json.dumps(self.payload)) + ")\n", "valid")
        self.publish_with(valid, review_id="collision")
        with self.assertRaisesRegex(publisher.ProvisionalFormPublishError, "already exists"):
            self.publish_with(valid, review_id="collision")

    def test_payload_rejects_root_role_shape_scale_and_exact_integer_violations(self) -> None:
        cases = []
        root_violation = copy.deepcopy(self.payload)
        root_violation["variants"][0]["descriptors"][1]["placement_source"] = "authored-root"
        root_violation["variants"][0]["descriptors"][1]["parent"] = None
        cases.append(root_violation)
        unknown_role = copy.deepcopy(self.payload)
        unknown_role["variants"][0]["descriptors"][0]["address"]["role"] = "mystery"
        cases.append(unknown_role)
        role_shape = copy.deepcopy(self.payload)
        role_shape["variants"][0]["descriptors"][0]["shape"]["name"] = "capsule"
        cases.append(role_shape)
        drift = copy.deepcopy(self.payload)
        drift["variants"][1]["descriptors"][0]["shape"]["name"] = "capsule"
        cases.append(drift)
        binary64 = copy.deepcopy(self.payload)
        binary64["variants"][0]["descriptors"][0]["reference_point"][0] = (1 << 53) + 1
        cases.append(binary64)
        non_edge = copy.deepcopy(self.payload)
        head = copy.deepcopy(non_edge["variants"][0]["descriptors"][1])
        head["address"] = {**head["address"], "role": "head"}
        head["parent"] = {**head["parent"], "role": "torso"}
        head["reference_point"] = [0, 2, 0]
        head["shape"]["center"] = [0, 2, 0]
        for variant in non_edge["variants"]:
            variant_head = copy.deepcopy(head)
            variant_head["profile_id"] = variant["id"]
            variant_head["provenance"] = copy.deepcopy(variant["provenance"])
            variant["descriptors"] = [variant_head, variant["descriptors"][0], variant["descriptors"][1]]
        non_edge["reference_scale"] = {
            "parent": {"namespace": "main", "anchors": [], "kind": "part", "role": "pelvis"},
            "child": {"namespace": "main", "anchors": [], "kind": "part", "role": "head"},
            "axis_delta": [0, 2, 0],
            "squared_length": 4,
            "source": "exact-containment-edge",
        }
        cases.append(non_edge)
        for index, payload in enumerate(cases):
            binary = self.fake_binary("import json, sys\nsys.stdout.write(" + repr(json.dumps(payload)) + ")\n", f"semantic-{index}")
            with self.assertRaises(publisher.ProvisionalFormPublishError):
                self.publish_with(binary, review_id=f"semantic-{index}")

    def test_input_is_copied_from_validated_identity_before_cli(self) -> None:
        capture = self.directory / "captured-input.bin"
        binary = self.fake_binary(
            "import json, pathlib, sys\n"
            f"pathlib.Path({str(capture)!r}).write_bytes(pathlib.Path(sys.argv[-1]).read_bytes())\n"
            "sys.stdout.write(" + repr(json.dumps(self.payload)) + ")\n",
            "identity-kernel",
        )
        self.input.write_bytes(b'{"identity":"original"}')
        self.publish_with(binary, review_id="identity-copy")
        self.assertEqual(capture.read_bytes(), self.input.read_bytes())
        self.assertNotEqual(capture.read_bytes(), b"{}")

    def test_forked_descendant_is_killed_on_timeout(self) -> None:
        pid_path = self.directory / "descendant.pid"
        binary = self.fake_binary(
            "import pathlib, subprocess, sys, time\n"
            f"child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)'])\n"
            f"pathlib.Path({str(pid_path)!r}).write_text(str(child.pid))\n"
            "time.sleep(30)\n",
            "fork-kernel",
        )
        # Leave enough startup time for the helper to fork and persist its PID;
        # the timeout still interrupts the deliberately long-running process.
        with patch.object(publisher, "INSPECTION_TIMEOUT_SECONDS", 1.0):
            with self.assertRaises(publisher.ProvisionalFormPublishError):
                self.publish_with(binary, review_id="forked-timeout")
        child_pid = int(pid_path.read_text())
        deadline = time.monotonic() + 2
        while time.monotonic() < deadline:
            try:
                os.kill(child_pid, 0)
            except ProcessLookupError:
                break
            time.sleep(0.02)
        else:
            self.fail("forked descendant survived bounded process-group cleanup")

    def test_output_caps_are_exactly_bounded_before_buffering(self) -> None:
        self.assertEqual(publisher.MAX_STDOUT_BYTES, 256 * 1024)
        self.assertEqual(publisher.MAX_STDERR_BYTES, 64 * 1024)
        for label, limit in (("stdout", publisher.MAX_STDOUT_BYTES), ("stderr", publisher.MAX_STDERR_BYTES)):
            binary = self.fake_binary(
                "import sys\n"
                + (f"sys.stdout.write('x' * {limit + 1})\n" if label == "stdout" else f"sys.stderr.write('x' * {limit + 1})\n"),
                f"bound-{label}",
            )
            with self.assertRaisesRegex(publisher.ProvisionalFormPublishError, label):
                self.publish_with(binary, review_id=f"bound-{label}")

    def test_checked_in_browser_dispatch_is_anchor_aware_and_shared_scale(self) -> None:
        app = (HERE / "static" / "app.js").read_text(encoding="utf-8")
        self.assertIn("function renderProvisionalForm", app)
        self.assertIn("provisionalFormPreviewSection(payload)", app)
        self.assertIn("payload.variants.forEach", app)
        self.assertIn("formBounds(payload)", app)
        self.assertIn("function formDescriptorQualifier", app)
        self.assertIn('anchors.indexOf("left")', app)
        self.assertIn('anchors.indexOf("right")', app)
        self.assertIn('return "#a78bfa"', app)
        self.assertIn('return "#f4a261"', app)
        self.assertIn('"Front · x / y"', app)
        self.assertIn('"Side · z / y"', app)
        self.assertIn('"Top · x / z"', app)


if __name__ == "__main__":
    unittest.main()
