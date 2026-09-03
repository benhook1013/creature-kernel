from __future__ import annotations

import copy
import hashlib
import json
import re
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = ROOT.parents[1]
SOURCE = REPOSITORY / "examples/body-documents/stylized-digitigrade-biped-authored-form.json"
sys.path.insert(0, str(ROOT))
import root_complex_surface as surface  # noqa: E402
from prepared_projection import (  # noqa: E402
    PreparedProjectionError, _load, canonical_json_bytes, canonical_json_sha256,
    prepare_standard_neutral,
)

BILATERAL_SCALARS = (
    ("arm_root_depth", "upper_arm", "form_arm_profile_upper_arm_start_forward_radius"),
    ("arm_root_outward", "upper_arm", "form_arm_profile_upper_arm_start_lateral_radius"),
    ("thigh_lateral_radius", "thigh", "form_leg_profile_thigh_start_lateral_radius"),
    ("thigh_depth", "thigh", "form_leg_profile_thigh_start_forward_radius"),
)


class PreparedProjectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = json.loads(SOURCE.read_text(encoding="utf-8")); cls.prepared = prepare_standard_neutral(SOURCE)

    def test_exact_surface_mapping_and_evaluation_compatibility(self):
        self.assertEqual(set(self.prepared), {"source", "basis", "frames", "landmarks", "stations", "scalars"})
        for name, expected in (("frames", {"body"}), ("landmarks", {f"{kind}_{side}" for side in ("left", "right") for kind in ("shoulder_peak", "axilla", "thigh_start", "thigh_mid")}), ("scalars", {"arm_root_depth", "arm_root_outward", "thigh_lateral_radius", "thigh_depth"})):
            self.assertEqual(set(self.prepared[name]), expected)
        self.assertEqual(len(self.prepared["stations"]), 7)
        self.assertNotIn("iliac_overlap", self.prepared["stations"])
        result = surface.evaluate(self.prepared, levels=2)
        self.assertEqual(len(result.levels), 2)
        self.assertTrue(all(isinstance(value, (int, float)) for value in self.prepared["stations"]["lower_pelvis"]["center"]))

    def test_source_identity_provenance_and_expected_controls(self):
        self.assertEqual(self.prepared["basis"], {"length_unit": "metre", "handedness": "right", "up": "+y", "forward": "+z"})
        paths = re.compile(r"(?:body\.(?:parts|landmarks|dimensions)\[\d+\]|source\.basis)")
        records = list(self.prepared["landmarks"].values()) + list(self.prepared["stations"].values()) + list(self.prepared["scalars"].values())
        self.assertTrue(all(isinstance(record["provenance"], str) and paths.search(record["provenance"]) for record in records))
        self.assertEqual(self.prepared["source"]["sha256"], hashlib.sha256(SOURCE.read_bytes()).hexdigest())
        for path, expected in (("stations.lower_pelvis.center", (0, -0.45, 0)), ("stations.lower_pelvis.lateral_radius", 1.5), ("stations.lower_pelvis.front_extent", 0.85), ("landmarks.shoulder_peak_left.point", (-1.1, 2.15, 0)), ("landmarks.axilla_left.point", (-1.1, 1.7, 0)), ("landmarks.thigh_mid_right.point", (1, -1.5, 0))):
            value = self.prepared
            for key in path.split("."): value = value[key]
            self.assertEqual(value, expected)
        self.assertLess(self.prepared["landmarks"]["shoulder_peak_left"]["point"][0], 0)
        self.assertGreater(self.prepared["landmarks"]["shoulder_peak_right"]["point"][0], 0)
        self.assertEqual(self.prepared["scalars"]["arm_root_depth"]["value"], self.prepared["scalars"]["thigh_lateral_radius"]["value"])

    def test_canonical_bytes_and_forbidden_payloads(self):
        again = prepare_standard_neutral(SOURCE)
        encoded = canonical_json_bytes(self.prepared)
        self.assertEqual(encoded, canonical_json_bytes(again))
        self.assertEqual(canonical_json_sha256(self.prepared), hashlib.sha256(encoded).hexdigest())
        forbidden = ("vertices", "faces", "connectivity", "perimeter", "silhouette", "mask", "resolved", "graph", "profile_id")
        self.assertFalse(any(re.search(rf"(?<![a-z]){token}(?![a-z])", encoded.decode().lower()) for token in forbidden))

    def assert_rejected(self, pattern, mutate):
        source = copy.deepcopy(self.source); mutate(source)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "source.json"; path.write_text(json.dumps(source), encoding="utf-8")
            with self.assertRaisesRegex(PreparedProjectionError, pattern): prepare_standard_neutral(path)

    @staticmethod
    def record_index(source, collection, owner, role):
        return next(index for index, record in enumerate(source["body"][collection]) if record.get("owner") == owner and record.get("role") == role)

    @staticmethod
    def owner(role, anchors=()):
        return {"namespace": "main", "anchors": list(anchors), "kind": "part", "role": role}

    def duplicate_record(self, source, collection, target, replacement):
        records = source["body"][collection]; records[self.record_index(source, collection, *target)] = copy.deepcopy(records[self.record_index(source, collection, *replacement)])

    def blank_record(self, source, collection, selector):
        source["body"][collection][self.record_index(source, collection, *selector)] = {}

    def bump_right_dimension(self, source, role, dimension_role):
        source["body"]["dimensions"][self.record_index(source, "dimensions", self.owner(role, ("right",)), dimension_role)]["value"] += 1

    def test_bilateral_scalars_read_and_retain_both_source_routes(self):
        source = self.source
        for name, role, dimension_role in BILATERAL_SCALARS:
            with self.subTest(scalar=name):
                indexes = [self.record_index(source, "dimensions", self.owner(role, (side,)), dimension_role) for side in ("left", "right")]
                provenance = self.prepared["scalars"][name]["provenance"]
                self.assertTrue(all(f"body.dimensions[{index}].value" in provenance for index in indexes) and "validated_bilateral_scalar_v1" in provenance)

    def test_bilateral_scalar_asymmetry_is_rejected_for_each_shared_scalar(self):
        for name, role, dimension_role in BILATERAL_SCALARS:
            with self.subTest(owner=role, dimension=dimension_role):
                self.assert_rejected(rf"scalars\.{name}: left and right dimensions must match", lambda source, role=role, dimension_role=dimension_role: self.bump_right_dimension(source, role, dimension_role))

    def assert_load_error(self, raw, message, cause_type):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "raw.json"; path.write_bytes(raw)
            with self.assertRaises(PreparedProjectionError) as context:
                _load(path)
        self.assertEqual(str(context.exception), message)
        self.assertIsInstance(context.exception.__cause__, cause_type)

    def test_load_reports_stable_cause_specific_errors(self):
        cases = (
            (b'{"duplicate": 1, "duplicate": 2}', "source contains duplicate JSON keys", ValueError),
            (b'{"value": NaN}', "source contains non-finite JSON constants", ValueError),
            (b'{"value": Infinity}', "source contains non-finite JSON constants", ValueError),
            (b'{"value": -Infinity}', "source contains non-finite JSON constants", ValueError),
            (b'{"value": 1e9999}', "source contains non-finite JSON numbers", ValueError),
            (b"{", "source has invalid JSON syntax", json.JSONDecodeError),
            (b"[]", "source JSON root must be an object", TypeError),
            (b"[" * 2000 + b"0" + b"]" * 2000, "source JSON is too deeply nested", RecursionError),
            (b"1" * 5000, "source contains an invalid JSON value", ValueError),
            (b"\xff", "source is not valid UTF-8", UnicodeDecodeError),
        )
        for raw, message, cause_type in cases:
            with self.subTest(message=message):
                self.assert_load_error(raw, message, cause_type)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "missing.json"
            with self.assertRaises(PreparedProjectionError) as context:
                _load(path)
        self.assertEqual(str(context.exception), "source file could not be read")
        self.assertIsInstance(context.exception.__cause__, OSError)

    def test_full_source_rejects_overflowed_number_in_unconsumed_record(self):
        raw = SOURCE.read_bytes().replace(
            b'"fields": []', b'"fields": [{"overflow": 1e9999}]', 1
        )
        self.assertIn(b'1e9999', raw)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "source.json"; path.write_bytes(raw)
            with self.assertRaises(PreparedProjectionError) as context:
                prepare_standard_neutral(path)
        self.assertEqual(str(context.exception), "source contains non-finite JSON numbers")
        self.assertIsInstance(context.exception.__cause__, ValueError)

    def test_required_source_shape_and_routes_fail_closed(self):
        self.assert_rejected(r"source\.basis: wrong basis", lambda source: source["basis"].__setitem__("forward", "-z"))
        self.assert_rejected(r"source\.source: wrong source identity", lambda source: source["source"].__setitem__("document", "other"))
        pelvis = self.owner("pelvis")
        thigh_left = self.owner("thigh", ("left",))
        self.assert_rejected(r"body\.dimensions\[\d+\]\.value: expected positive number", lambda source: source["body"]["dimensions"][self.record_index(source, "dimensions", pelvis, "form_torso_profile_lower_pelvis_lateral_radius")].__setitem__("value", 0))
        self.assert_rejected(r"left controls: degenerate required route", lambda source: source["body"]["landmarks"][self.record_index(source, "landmarks", thigh_left, "form_leg_profile_thigh_midpoint")].__setitem__("position", [0, 0, 0]))
        self.assert_rejected(r"body\.landmarks\.form_torso_profile_lower_pelvis: missing or duplicate required record", lambda source: self.duplicate_record(source, "landmarks", (pelvis, "form_torso_profile_lower_pelvis"), (pelvis, "form_torso_profile_upper_pelvis")))
        self.assert_rejected(r"body\.landmarks\[\d+\]: missing record selector", lambda source: self.blank_record(source, "landmarks", (self.owner("upper_arm", ("left",)), "form_shoulder_peak")))
        self.assert_rejected(r"source\.body: unknown or missing collection", lambda source: source["body"].__setitem__("unknown", []))
        self.assert_rejected(r"body\.frames\.form_torso_profile_control: missing or duplicate required record", lambda source: self.duplicate_record(source, "frames", (self.owner("torso"), "form_torso_profile_control"), (pelvis, "form_torso_profile_control")))
