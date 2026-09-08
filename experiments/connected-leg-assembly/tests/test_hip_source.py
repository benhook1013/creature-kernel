from __future__ import annotations

import copy
import json
from collections.abc import Mapping
from pathlib import Path
import sys
from typing import Any
import unittest


EXPERIMENT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(EXPERIMENT))
import hip_source  # noqa: E402
import root_source  # noqa: E402


def _json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _difference_paths(expected: Any, actual: Any, path: str = "$", limit: int = 12) -> list[str]:
    if limit <= 0:
        return [path]
    if type(expected) is not type(actual):
        return [f"{path} (types {type(expected).__name__}/{type(actual).__name__})"]
    if isinstance(expected, Mapping):
        differences: list[str] = []
        for key in sorted(set(expected) | set(actual), key=str):
            child = f"{path}.{key}"
            if key not in expected or key not in actual:
                differences.append(child)
            else:
                differences.extend(_difference_paths(expected[key], actual[key], child,
                                                      limit - len(differences)))
            if len(differences) >= limit:
                return differences[:limit]
        return differences
    if isinstance(expected, list):
        differences = []
        if len(expected) != len(actual):
            differences.append(f"{path} (length {len(expected)}/{len(actual)})")
        for index, (left, right) in enumerate(zip(expected, actual)):
            differences.extend(_difference_paths(left, right, f"{path}[{index}]",
                                                  limit - len(differences)))
            if len(differences) >= limit:
                return differences[:limit]
        return differences
    return [] if expected == actual else [path]


class HipSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.document = _json(EXPERIMENT / "inputs.json")

    def _case(self, index: int) -> tuple[dict, dict, dict, dict]:
        row = self.document["cases"][index]
        source_case = _json(row["original_case"]["path"])
        rebuilt = root_source.reconstruct_source_case(source_case)
        prior = _json(row["prior_hip_binding"]["path"])
        return row, source_case, rebuilt, prior

    def test_both_recorded_cases_regenerate_saved_weights_and_frames(self) -> None:
        for index in range(2):
            row, source_case, rebuilt, prior = self._case(index)
            result = hip_source.bind_source_case(
                rebuilt["levels"]["L0"], rebuilt["levels"]["L2"], source_case,
                leg_inputs=row["leg_inputs"])
            actual = result["binding"]
            for key in ("base_weights", "evaluated_weights", "rest_frames"):
                differences = _difference_paths(prior[key], actual[key], f"$.{key}")
                self.assertFalse(
                    differences,
                    f"{row['id']} {key} metadata differs at: {', '.join(differences)}",
                )

            identity = result["provenance"]["frozen_helper_identity"]
            self.assertEqual(identity["before"], identity["after"])
            self.assertEqual(identity["manifest_path"], str(hip_source.FROZEN_HIP_MANIFEST))
            self.assertEqual(identity["path"], str(hip_source.FROZEN_HIP_BINDING))
            self.assertNotEqual(identity["path"], str(EXPERIMENT / "binding.py"))

    def test_j_only_change_preserves_weights_and_rest_geometry_but_changes_frame(self) -> None:
        row, source_case, rebuilt, _prior = self._case(0)
        rest_before = copy.deepcopy(rebuilt["levels"]["L2"])
        baseline_inputs = copy.deepcopy(row["leg_inputs"])
        changed_inputs = copy.deepcopy(baseline_inputs)
        changed_inputs["left"]["J"][1] += 0.01
        baseline = hip_source.bind_source_case(
            rebuilt["levels"]["L0"], rebuilt["levels"]["L2"], source_case,
            leg_inputs=baseline_inputs)["binding"]
        changed = hip_source.bind_source_case(
            rebuilt["levels"]["L0"], rebuilt["levels"]["L2"], source_case,
            leg_inputs=changed_inputs)["binding"]
        self.assertEqual(baseline["base_weights"], changed["base_weights"])
        self.assertEqual(baseline["evaluated_weights"], changed["evaluated_weights"])
        self.assertEqual(baseline["rest_frames"]["right"], changed["rest_frames"]["right"])
        self.assertNotEqual(baseline["rest_frames"]["left"], changed["rest_frames"]["left"])
        self.assertEqual(rest_before, rebuilt["levels"]["L2"])

    def test_leg_t_or_k_conflict_is_rejected(self) -> None:
        row, source_case, rebuilt, _prior = self._case(0)
        for field in ("T", "K"):
            changed = copy.deepcopy(row["leg_inputs"])
            changed["left"][field][0] += 0.001
            with self.subTest(field=field):
                with self.assertRaisesRegex(hip_source.HipSourceError, rf"left\.{field} conflicts"):
                    hip_source.bind_source_case(
                        rebuilt["levels"]["L0"], rebuilt["levels"]["L2"], source_case,
                        leg_inputs=changed)


if __name__ == "__main__":
    unittest.main()
