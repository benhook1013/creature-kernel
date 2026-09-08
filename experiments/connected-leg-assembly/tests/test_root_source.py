import copy
import json
import sys
import unittest
from collections.abc import Mapping
from pathlib import Path
from unittest import mock


EXPERIMENT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(EXPERIMENT))
import root_source  # noqa: E402


def _json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _difference_paths(expected, actual, path="$", limit=12):
    if limit <= 0:
        return [path]
    if type(expected) is not type(actual):
        return [f"{path} (types {type(expected).__name__}/{type(actual).__name__})"]
    if isinstance(expected, Mapping):
        differences = []
        for key in sorted(set(expected) | set(actual), key=str):
            child = f"{path}.{key}"
            if key not in expected or key not in actual:
                differences.append(child)
            else:
                differences.extend(
                    _difference_paths(expected[key], actual[key], child,
                                      limit - len(differences))
                )
            if len(differences) >= limit:
                return differences[:limit]
        return differences
    if isinstance(expected, list):
        differences = []
        if len(expected) != len(actual):
            differences.append(f"{path} (length {len(expected)}/{len(actual)})")
        for index, (left, right) in enumerate(zip(expected, actual)):
            differences.extend(
                _difference_paths(left, right, f"{path}[{index}]",
                                  limit - len(differences))
            )
            if len(differences) >= limit:
                return differences[:limit]
        return differences
    return [] if expected == actual else [path]


class RootSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.document = _json(EXPERIMENT / "inputs.json")

    def test_both_recorded_source_cases_rebuild_saved_L0_and_L2_exactly(self):
        for case in self.document["cases"]:
            source_case = _json(case["original_case"]["path"])
            rebuilt = root_source.reconstruct_source_case(source_case)
            cls = case["id"]
            self.assertEqual(rebuilt["source_case_id"], cls)
            self.assertTrue(
                rebuilt["provenance"]["frozen_construction"]["sha256"]
            )
            for level, reference_key in (("L0", "root_mesh"),
                                          ("L2", "prior_rest_mesh")):
                expected = _json(case[reference_key]["path"])
                actual = rebuilt["levels"][level]
                differences = _difference_paths(expected, actual)
                self.assertFalse(
                    differences,
                    f"{cls} {level} differs at: {', '.join(differences)}",
                )

    def test_provenance_selects_immutable_captured_runner_not_live_sibling(self):
        case = self.document["cases"][0]
        source_case = _json(case["original_case"]["path"])
        rebuilt = root_source.reconstruct_source_case(source_case)
        runner_path = Path(rebuilt["provenance"]["calibration_runner"]["path"])
        live_sibling = EXPERIMENT.parent / "pelvis-source-calibration" / "runner.py"
        self.assertEqual(runner_path, root_source.CALIBRATION_RUNNER_PATH)
        self.assertNotEqual(runner_path.resolve(), live_sibling.resolve())
        self.assertTrue(str(runner_path).startswith(
            "/home/ben/.cache/creature-kernel/pelvis-source-calibration-set-1/"
        ))
        self.assertEqual(
            rebuilt["provenance"]["calibration_runner"]["manifest_path"],
            str(root_source.CALIBRATION_SOURCE_MANIFEST_PATH),
        )
        self.assertEqual(
            rebuilt["provenance"]["frozen_construction"]["dependency_root"],
            "/home/ben/.cache/creature-kernel/pelvis-thigh-transition/attempt-2-snapshot",
        )

    def test_recorded_source_component_reaches_frozen_consumer(self):
        case = self.document["cases"][0]
        source_case = _json(case["original_case"]["path"])
        changed = copy.deepcopy(source_case)
        key = "stations.lower_pelvis.C.y"
        changed["components"][key] = float(changed["components"][key]) + 0.001

        baseline = root_source.reconstruct_source_case(source_case)
        perturbed = root_source.reconstruct_source_case(changed)
        baseline_l0 = baseline["levels"]["L0"]
        perturbed_l0 = perturbed["levels"]["L0"]
        self.assertNotEqual(baseline_l0["vertices"], perturbed_l0["vertices"])
        self.assertEqual(baseline_l0["quads"], perturbed_l0["quads"])
        self.assertEqual(baseline_l0["loops"], perturbed_l0["loops"])

    def test_optional_constructor_transform_installs_locally_before_build(self):
        construction = mock.Mock()
        calibration_runner = mock.Mock()
        verified_provenance = {
            "calibration_runner": {"path": "runner.py"},
            "frozen_construction": {"sha256": "frozen"},
            "calibration_runner_module": calibration_runner,
        }
        events = []

        def build(components, attachments, diagnostic):
            self.assertEqual(events, ["transform"])
            self.assertEqual(components, {"component": 1})
            self.assertEqual(attachments, {"attachment": 2})
            self.assertTrue(diagnostic)
            self.assertEqual(construction.source_provider, {"name": "torso"})
            events.append("build")
            return {"mesh": "built"}

        def evaluate(built, levels):
            self.assertEqual(events, ["transform", "build"])
            self.assertEqual(built, {"mesh": "built"})
            self.assertEqual(levels, 2)
            events.append("evaluate")
            return [{"level": 0}, {"level": 1}, {"level": 2}]

        construction.build.side_effect = build
        construction.evaluate.side_effect = evaluate
        calibration_runner._bounded.side_effect = lambda value: value

        def transform(private_constructor, complete_provenance):
            self.assertIs(private_constructor, construction)
            self.assertIs(complete_provenance, verified_provenance)
            construction.source_provider = {"name": "torso"}
            events.append("transform")
            return {"provider": "torso", "config_sha256": "config"}

        source_case = {
            "id": "mock-case",
            "components": {"component": 1},
            "attachments": {"attachment": 2},
        }
        with mock.patch.object(
                root_source, "_load_frozen_construction",
                return_value=(construction, verified_provenance)):
            rebuilt = root_source.reconstruct_source_case(
                source_case, constructor_transform=transform)

        self.assertEqual(events, ["transform", "build", "evaluate"])
        self.assertEqual(
            rebuilt["provenance"]["source_refinement"],
            {"provider": "torso", "config_sha256": "config"},
        )
        self.assertNotIn("calibration_runner_module", rebuilt["provenance"])
        self.assertIs(
            verified_provenance["calibration_runner_module"], calibration_runner
        )


if __name__ == "__main__":
    unittest.main()
