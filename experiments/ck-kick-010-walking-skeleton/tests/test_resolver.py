import copy
import json
import math
import unittest
from pathlib import Path

from ck_spike.diagnostics import Phase, Severity, ValidationError
from ck_spike.resolver import resolve_document, resolve_file


EXPERIMENT_ROOT = Path(__file__).resolve().parents[1]
VALID_FIXTURE = EXPERIMENT_ROOT / "fixtures" / "valid.json"
INVALID_FIXTURE = EXPERIMENT_ROOT / "fixtures" / "invalid-missing-right-shin.json"


class ResolverTests(unittest.TestCase):
    def test_valid_fixture_resolves_to_serializable_graph(self):
        result = resolve_file(VALID_FIXTURE)

        self.assertTrue(result.ok)
        self.assertEqual(result.diagnostics, ())
        graph_data = result.require_graph().to_dict()
        self.assertEqual(graph_data["fixture_id"], "ck-kick-010-valid-biped")
        self.assertEqual(len(graph_data["nodes"]), 15)
        json.dumps(graph_data, sort_keys=True)
        for node in graph_data["nodes"]:
            matrix = node["world_transform"]["matrix"]
            self.assertEqual(len(matrix), 4)
            self.assertTrue(all(len(row) == 4 for row in matrix))
            self.assertIn(node["primitive"]["kind"], {"capsule", "ellipsoid"})

    def test_invalid_fixture_only_removes_right_shin(self):
        valid = json.loads(VALID_FIXTURE.read_text(encoding="utf-8"))
        invalid = json.loads(INVALID_FIXTURE.read_text(encoding="utf-8"))

        valid["fixture_id"] = invalid["fixture_id"]
        valid["nodes"] = [
            node for node in valid["nodes"] if node["label"] != "right_shin"
        ]
        self.assertEqual(invalid, valid)

    def test_order_and_world_transforms_are_deterministic(self):
        first = resolve_file(VALID_FIXTURE).require_graph().to_dict()
        second = resolve_file(VALID_FIXTURE).require_graph().to_dict()

        self.assertEqual(first, second)
        labels = [node["label"] for node in first["nodes"]]
        self.assertEqual(labels, sorted(labels))
        right_foot = next(node for node in first["nodes"] if node["label"] == "right_foot_paw")
        translation = [row[3] for row in right_foot["world_transform"]["matrix"][:3]]
        for actual, expected in zip(translation, [-0.35, -1.42, 0.26]):
            self.assertAlmostEqual(actual, expected)

    def test_bilateral_landmarks_follow_creature_left_and_right_axes(self):
        graph = resolve_file(VALID_FIXTURE).require_graph().to_dict()
        nodes = {node["label"]: node for node in graph["nodes"]}

        def world_x(label):
            return nodes[label]["world_transform"]["matrix"][0][3]

        self.assertGreater(world_x("left_arm"), 0.0)
        self.assertLess(world_x("right_arm"), 0.0)
        self.assertGreater(world_x("left_thigh"), 0.0)
        self.assertLess(world_x("right_thigh"), 0.0)
        self.assertGreater(world_x("left_ear"), 0.0)

    def test_parent_socket_rotation_is_included_in_world_transform(self):
        document = json.loads(VALID_FIXTURE.read_text(encoding="utf-8"))
        half_turn = math.sqrt(0.5)
        torso = next(node for node in document["nodes"] if node["label"] == "torso")
        torso["transform"]["rotation"] = [0.0, 0.0, half_turn, half_turn]

        result = resolve_document(document)
        self.assertTrue(result.ok)
        head = next(node for node in result.require_graph().to_dict()["nodes"] if node["label"] == "head")
        translation = [row[3] for row in head["world_transform"]["matrix"][:3]]
        for actual, expected in zip(translation, [-0.97, 1.2, 0.08]):
            self.assertAlmostEqual(actual, expected)

    def test_duplicate_source_label_is_a_structured_validation_failure(self):
        document = json.loads(VALID_FIXTURE.read_text(encoding="utf-8"))
        document["nodes"].append(copy.deepcopy(document["nodes"][0]))

        result = resolve_document(document)
        self.assertFalse(result.ok)
        self.assertEqual(len(result.diagnostics), 1)
        diagnostic = result.diagnostics[0]
        self.assertEqual(diagnostic.code, "DUPLICATE_SOURCE_LABEL")
        self.assertEqual(diagnostic.phase, Phase.VALIDATION)
        self.assertEqual(diagnostic.severity, Severity.ERROR)
        self.assertEqual(diagnostic.related_source_labels, ("torso",))

    def test_invalid_fixture_stops_at_exact_missing_module_diagnostic(self):
        result = resolve_file(INVALID_FIXTURE)

        self.assertFalse(result.ok)
        self.assertIsNone(result.graph)
        self.assertEqual(len(result.diagnostics), 1)
        diagnostic = result.diagnostics[0]
        self.assertEqual(diagnostic.code, "MISSING_REQUIRED_MODULE")
        self.assertEqual(diagnostic.severity, Severity.ERROR)
        self.assertEqual(diagnostic.phase, Phase.VALIDATION)
        self.assertEqual(diagnostic.path, "/nodes/right_shin")
        self.assertEqual(diagnostic.related_source_labels, ("right_shin",))
        with self.assertRaises(ValidationError) as raised:
            result.require_graph()
        self.assertEqual(raised.exception.diagnostics, result.diagnostics)

    def test_coordinate_convention_must_match_current_spike_convention(self):
        document = json.loads(VALID_FIXTURE.read_text(encoding="utf-8"))
        document["coordinate_convention"]["units"] = "centimetres"

        result = resolve_document(document)
        self.assertFalse(result.ok)
        self.assertEqual(len(result.diagnostics), 1)
        diagnostic = result.diagnostics[0]
        self.assertEqual(diagnostic.code, "UNSUPPORTED_COORDINATE_CONVENTION")
        self.assertEqual(diagnostic.phase, Phase.VALIDATION)
        self.assertEqual(diagnostic.path, "/coordinate_convention")

    def test_only_current_spike_revision_is_supported(self):
        document = json.loads(VALID_FIXTURE.read_text(encoding="utf-8"))
        document["spike_revision"] = 2

        result = resolve_document(document)
        self.assertFalse(result.ok)
        self.assertEqual(len(result.diagnostics), 1)
        diagnostic = result.diagnostics[0]
        self.assertEqual(diagnostic.code, "UNSUPPORTED_SPIKE_REVISION")
        self.assertEqual(diagnostic.phase, Phase.VALIDATION)
        self.assertEqual(diagnostic.path, "/spike_revision")

    def test_non_unit_quaternion_is_rejected(self):
        document = json.loads(VALID_FIXTURE.read_text(encoding="utf-8"))
        torso = next(node for node in document["nodes"] if node["label"] == "torso")
        torso["transform"]["rotation"] = [0.0, 0.0, 0.0, 2.0]

        result = resolve_document(document)
        self.assertFalse(result.ok)
        self.assertEqual(len(result.diagnostics), 1)
        diagnostic = result.diagnostics[0]
        self.assertEqual(diagnostic.code, "INVALID_ROTATION")
        self.assertEqual(diagnostic.phase, Phase.VALIDATION)
        self.assertEqual(diagnostic.path, "/nodes/0/transform/rotation")


if __name__ == "__main__":
    unittest.main()
