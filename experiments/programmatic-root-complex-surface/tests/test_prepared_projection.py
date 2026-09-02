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
    PreparedProjectionError, canonical_json_bytes, canonical_json_sha256,
    prepare_standard_neutral,
)


class PreparedProjectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.prepared = prepare_standard_neutral(SOURCE)

    def test_exact_surface_mapping_and_evaluation_compatibility(self):
        self.assertEqual(set(self.prepared), {"source", "basis", "frames", "landmarks", "stations", "scalars"})
        self.assertEqual(set(self.prepared["frames"]), {"body"})
        self.assertEqual(set(self.prepared["landmarks"]), {f"{kind}_{side}" for side in ("left", "right") for kind in ("shoulder_peak", "axilla", "thigh_start", "thigh_mid")})
        self.assertEqual(len(self.prepared["stations"]), 7)
        self.assertNotIn("iliac_overlap", self.prepared["stations"])
        self.assertEqual(set(self.prepared["scalars"]), {"arm_root_depth", "arm_root_outward", "thigh_lateral_radius", "thigh_depth"})
        result = surface.evaluate(self.prepared, levels=2)
        self.assertEqual(len(result.levels), 2)
        self.assertTrue(all(isinstance(value, (int, float)) for value in self.prepared["stations"]["lower_pelvis"]["center"]))

    def test_source_identity_provenance_and_expected_controls(self):
        self.assertEqual(self.prepared["source"]["sha256"], hashlib.sha256(SOURCE.read_bytes()).hexdigest())
        self.assertEqual(self.prepared["basis"], {"length_unit": "metre", "handedness": "right", "up": "+y", "forward": "+z"})
        paths = re.compile(r"(?:body\.(?:parts|landmarks|dimensions)\[\d+\]|source\.basis)")
        records = list(self.prepared["landmarks"].values()) + list(self.prepared["stations"].values()) + list(self.prepared["scalars"].values())
        self.assertTrue(all(isinstance(record["provenance"], str) and paths.search(record["provenance"]) for record in records))
        self.assertEqual(self.prepared["stations"]["lower_pelvis"]["center"], (0, -0.45, 0))
        self.assertEqual(self.prepared["stations"]["lower_pelvis"]["lateral_radius"], 1.5)
        self.assertEqual(self.prepared["stations"]["lower_pelvis"]["front_extent"], 0.85)
        self.assertEqual(self.prepared["landmarks"]["shoulder_peak_left"]["point"], (-1.1, 2.15, 0))
        self.assertEqual(self.prepared["landmarks"]["axilla_left"]["point"], (-1.1, 1.7, 0))
        self.assertEqual(self.prepared["landmarks"]["thigh_mid_right"]["point"], (1, -1.5, 0))
        self.assertLess(self.prepared["landmarks"]["shoulder_peak_left"]["point"][0], 0)
        self.assertGreater(self.prepared["landmarks"]["shoulder_peak_right"]["point"][0], 0)
        self.assertEqual(self.prepared["scalars"]["arm_root_depth"]["value"], 0.32)
        self.assertEqual(self.prepared["scalars"]["thigh_lateral_radius"]["value"], 0.32)
        dimension_records = list(self.prepared["stations"].values()) + list(self.prepared["scalars"].values())
        self.assertTrue(all("source_dimension_canonical_metre_value_v1" in record["provenance"] for record in dimension_records))

    @staticmethod
    def set_dimension_value(source, role, value):
        matches = [row for row in source["body"]["dimensions"] if row.get("role") == role]
        if not matches:
            raise AssertionError(f"dimension role not found: {role}")
        for row in matches:
            row["value"] = value

    def prepared_from_mutated_source(self, mutate):
        source = json.loads(SOURCE.read_text(encoding="utf-8"))
        mutate(source)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "source.json"; path.write_text(json.dumps(source), encoding="utf-8")
            return prepare_standard_neutral(path)

    def test_canonical_metre_dimensions_are_admitted_without_rescaling(self):
        prepared = self.prepared_from_mutated_source(lambda source: (self.set_dimension_value(source, "form_torso_profile_lower_pelvis_lateral_radius", 1.5), self.set_dimension_value(source, "form_arm_profile_upper_arm_start_forward_radius", 0.32)))
        self.assertEqual(prepared["stations"]["lower_pelvis"]["lateral_radius"], 1.5)
        self.assertEqual(prepared["scalars"]["arm_root_depth"]["value"], 0.32)

    def test_non_dimension_routes_remain_unchanged_when_dimensions_change(self):
        prepared = self.prepared_from_mutated_source(lambda source: (self.set_dimension_value(source, "form_torso_profile_lower_pelvis_lateral_radius", 1.25), self.set_dimension_value(source, "form_arm_profile_upper_arm_start_forward_radius", 0.28)))
        self.assertEqual(prepared["basis"], self.prepared["basis"])
        self.assertEqual(prepared["frames"], self.prepared["frames"])
        self.assertEqual(prepared["landmarks"], self.prepared["landmarks"])
        self.assertEqual({name: station["center"] for name, station in prepared["stations"].items()}, {name: station["center"] for name, station in self.prepared["stations"].items()})

    def test_canonical_bytes_and_forbidden_payloads(self):
        again = prepare_standard_neutral(SOURCE)
        encoded = canonical_json_bytes(self.prepared)
        self.assertEqual(encoded, canonical_json_bytes(again))
        self.assertEqual(canonical_json_sha256(self.prepared), hashlib.sha256(encoded).hexdigest())
        forbidden = ("vertices", "faces", "connectivity", "perimeter", "silhouette", "mask", "resolved", "graph", "profile_id")
        self.assertFalse(any(re.search(rf"(?<![a-z]){token}(?![a-z])", encoded.decode().lower()) for token in forbidden))

    def assert_rejected(self, mutate):
        source = json.loads(SOURCE.read_text(encoding="utf-8")); mutate(source)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "source.json"; path.write_text(json.dumps(source), encoding="utf-8")
            with self.assertRaises(PreparedProjectionError): prepare_standard_neutral(path)

    def test_dimension_values_fail_closed_for_booleans_nonfinite_and_nonpositive_values(self):
        for value in (True, False, float("nan"), float("inf"), 0, -0.01):
            with self.subTest(value=value):
                self.assert_rejected(lambda source, value=value: self.set_dimension_value(source, "form_torso_profile_lower_pelvis_lateral_radius", value))

    def test_unused_dimension_value_fails_closed(self):
        self.assert_rejected(lambda source: source["body"]["dimensions"][0].__setitem__("value", 0))

    def test_required_source_shape_and_routes_fail_closed(self):
        self.assert_rejected(lambda source: source["basis"].__setitem__("forward", "-z"))
        self.assert_rejected(lambda source: source["source"].__setitem__("document", "other"))
        self.assert_rejected(lambda source: source["body"]["landmarks"][15].__setitem__("position", [0, 0, 0]))
        self.assert_rejected(lambda source: source["body"]["landmarks"].__setitem__(42, copy.deepcopy(source["body"]["landmarks"][24])))
        self.assert_rejected(lambda source: source["body"]["landmarks"].__setitem__(0, {}))
        self.assert_rejected(lambda source: source["body"].__setitem__("unknown", []))

        def duplicate_pelvis_frame(source):
            frames = source["body"]["frames"]
            frames[1] = copy.deepcopy(frames[0])
            self.assertEqual((frames[1]["owner"], frames[1]["role"]), (frames[0]["owner"], frames[0]["role"]))

        self.assert_rejected(duplicate_pelvis_frame)
