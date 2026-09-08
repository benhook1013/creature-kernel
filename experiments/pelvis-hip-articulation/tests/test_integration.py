from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path


EXPERIMENT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(EXPERIMENT_DIR))
import binding  # noqa: E402
import checks  # noqa: E402


def _fixture() -> tuple[dict, dict, dict, dict, dict]:
    # Two four-vertex distal port loops attach through one ringB, socket and
    # ringA chain per side to a small shared pelvis.  The faces are nonzero
    # area and the boundary-edge graph is connected.
    vertices = [
        [-1.5, 0.0, -0.4], [-0.9, 0.0, -0.4], [-0.9, 0.6, -0.4], [-1.5, 0.6, -0.4],
        [0.9, 0.0, -0.4], [1.5, 0.0, -0.4], [1.5, 0.6, -0.4], [0.9, 0.6, -0.4],
        [-1.2, 0.15, 0.0], [-1.55, 0.15, 0.0], [-1.35, 0.8, 0.0],
        [1.2, 0.15, 0.0], [1.55, 0.15, 0.0], [1.35, 0.8, 0.0],
        [0.0, 1.0, 0.0], [-0.6, 1.2, 0.0], [0.6, 1.2, 0.0], [0.0, 1.6, 0.0],
    ]
    quads = [
        [0, 1, 2, 3], [1, 0, 9, 8], [8, 9, 10, 14],
        [4, 5, 6, 7], [5, 4, 12, 11], [11, 12, 13, 14],
        [14, 15, 16, 17],
    ]
    transitions = {
        "left": {"socket": [9], "ringA": [10], "ringB": [8], "exit": [0, 1, 2, 3]},
        "right": {"socket": [12], "ringA": [13], "ringB": [11], "exit": [4, 5, 6, 7]},
    }
    stencils = [[[index, 1.0]] for index in range(len(vertices))]
    owners = ["synthetic_pelvis"] * len(quads)
    base = {
        "schema": "synthetic-l0",
        "level": 0,
        "vertices": copy.deepcopy(vertices),
        "quads": copy.deepcopy(quads),
        "base_stencils": copy.deepcopy(stencils),
        "metadata": {"transition_indices": copy.deepcopy(transitions)},
    }
    rest = {
        "schema": "synthetic-l2",
        "level": 2,
        "vertices": copy.deepcopy(vertices),
        "quads": copy.deepcopy(quads),
        "base_stencils": stencils,
        "loops": {"port.left_thigh": [0, 1, 2, 3],
                  "port.right_thigh": [4, 5, 6, 7]},
        "control_owners": [f"control-{index}" for index in range(len(vertices))],
        "face_owners": owners,
        "metadata": {"transition_indices": copy.deepcopy(transitions)},
    }
    case = {
        "id": "synthetic-integration",
        "components": {f"component_{index:02d}": float(index) for index in range(92)},
        "attachments": {
            "left": {"centre": [-1.2, 0.3, -0.4], "knee": [-1.2, -0.8, 0.0]},
            "right": {"centre": [1.2, 0.3, -0.4], "knee": [1.2, -0.8, 0.0]},
        },
    }
    references = {
        "joint_left": [-1.2, 0.3, 0.0], "joint_right": [1.2, 0.3, 0.0],
        "crest_left": [-0.3, 1.5, 0.0], "crest_right": [0.3, 1.5, 0.0],
    }
    protocol = json.loads((EXPERIMENT_DIR / "protocol.json").read_text(encoding="utf-8"))
    return base, rest, case, references, protocol


def _json_roundtrip(value: object) -> object:
    return json.loads(json.dumps(value))


class BindingIntegrationTests(unittest.TestCase):
    def test_binding_pose_json_roundtrip_consumes_checks_at_identity_and_modest_pose(self) -> None:
        base, rest, case, references, protocol = _fixture()
        bound = _json_roundtrip(binding.bind(base, rest, case, references))
        protocol = _json_roundtrip(protocol)
        self.assertIsInstance(bound, dict)
        for angles in ({"left": 0.0, "right": 0.0},
                       {"left": 15.0, "right": 0.0}):
            posed = _json_roundtrip(binding.pose(rest, bound, angles))
            report = checks.check_pose(rest, posed, bound, angles, case, references, protocol)
            self.assertTrue(report["pass"], report)
            self.assertFalse(report["errors"], report)
        self.assertEqual(rest["vertices"], base["vertices"])
        self.assertEqual(rest["quads"], base["quads"])


if __name__ == "__main__":
    unittest.main()
