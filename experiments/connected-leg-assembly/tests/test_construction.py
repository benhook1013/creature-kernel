"""Synthetic unit tests for the bounded connected-leg construction."""
from __future__ import annotations

import json
import hashlib
import importlib.util
import math
from pathlib import Path
import sys
import unittest


HERE = Path(__file__).resolve().parents[1]
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import construction  # noqa: E402


def _ring(center: tuple[float, float, float], radius_x: float = 0.2,
          radius_z: float = 0.15) -> list[list[float]]:
    return [
        [center[0] + radius_x * math.cos(2.0 * math.pi * index / 8.0),
         center[1],
         center[2] + radius_z * math.sin(2.0 * math.pi * index / 8.0)]
        for index in range(8)
    ]


def _root_mesh() -> tuple[dict, dict]:
    left_T = (-0.75, 0.0, 0.0)
    right_T = (0.75, 1.0, 0.0)
    left_K = (-0.75, -1.0, 0.0)
    right_K = (0.75, 0.0, 0.0)
    left_A = (-0.55, -1.6, 0.18)
    right_A = (0.55, -0.6, 0.18)
    left_exit = tuple(left_T[axis] + 0.45 * (left_K[axis] - left_T[axis])
                      for axis in range(3))
    right_exit = tuple(right_T[axis] + 0.45 * (right_K[axis] - right_T[axis])
                       for axis in range(3))
    left_ring = _ring(left_exit)
    right_ring = _ring(right_exit)
    vertices = left_ring + right_ring
    quads = [
        [index, (index + 1) % 8, 8 + (index + 1) % 8, 8 + index]
        for index in range(8)
    ]
    owners = ["domain.root"] * len(quads)
    root_frames = {}
    transitions = {}
    for side, T, K in (("left", left_T, left_K), ("right", right_T, right_K)):
        direction = (0.0, -1.0, 0.0)
        exit_point = [T[axis] + 0.45 * (K[axis] - T[axis]) for axis in range(3)]
        root_frames[side] = {
            "H": list(T), "knee": list(K), "length": 1.0,
            "d": list(direction), "X": [1.0, 0.0, 0.0],
            "U": [0.0, 1.0, 0.0], "F": [0.0, 0.0, 1.0],
            "exit": exit_point,
        }
        loop = list(range(8)) if side == "left" else [8, 15, 14, 13, 12, 11, 10, 9]
        transitions[side] = {"exit": loop}
    root = {
        "schema": "synthetic.connected-root.v1",
        "level": 0,
        "vertices": vertices,
        "quads": quads,
        "face_owners": owners,
        "control_owners": ["domain.root"] * len(vertices),
        "loops": {
            "port.left_thigh": list(range(8)),
            "port.right_thigh": [8, 15, 14, 13, 12, 11, 10, 9],
        },
        "base_stencils": [[[index, 1.0]] for index in range(len(vertices))],
        "frames": root_frames,
        "metadata": {
            "level": 0,
            "admission_status": "accepted",
            "admission_failures": [],
            "base_control_owners": ["domain.root"] * len(vertices),
            "dominant_owner_label": "synthetic root label",
            "transition_indices": transitions,
        },
    }
    inputs = {
        "left": {
            "J": [-0.8, 0.1, 0.0], "T": list(left_T), "K": list(left_K),
            "A": list(left_A),
            "radii": {"knee": [0.15, 0.12, 0.13],
                       "calf": [0.13, 0.11, 0.18],
                       "ankle": [0.10, 0.09, 0.12]},
            "mid_thigh_factor": 0.85, "support_fraction": 0.10,
            "J_role": "synthetic pose-only joint",
            "TK_source_role": "synthetic source points",
            "distal_design_status": "synthetic context",
        },
        "right": {
            "J": [0.8, 1.1, 0.0], "T": list(right_T), "K": list(right_K),
            "A": list(right_A),
            "radii": {"knee": [0.15, 0.12, 0.13],
                       "calf": [0.13, 0.11, 0.18],
                       "ankle": [0.10, 0.09, 0.12]},
            "mid_thigh_factor": 0.85, "support_fraction": 0.10,
            "J_role": "synthetic pose-only joint",
            "TK_source_role": "synthetic source points",
            "distal_design_status": "synthetic context",
        },
    }
    return root, inputs


def _closed_cube() -> dict:
    vertices = [
        [-1.0, -1.0, -1.0], [1.0, -1.0, -1.0],
        [1.0, 1.0, -1.0], [-1.0, 1.0, -1.0],
        [-1.0, -1.0, 1.0], [1.0, -1.0, 1.0],
        [1.0, 1.0, 1.0], [-1.0, 1.0, 1.0],
    ]
    return {
        "schema": "synthetic.closed-cube.v1",
        "level": 0,
        "vertices": vertices,
        "quads": [
            [0, 3, 2, 1], [4, 5, 6, 7], [0, 1, 5, 4],
            [3, 7, 6, 2], [0, 4, 7, 3], [1, 2, 6, 5],
        ],
        "face_owners": ["domain.cube"] * 6,
        "control_owners": ["domain.cube"] * 8,
        "loops": {},
        "base_stencils": [[[index, 1.0]] for index in range(8)],
        "frames": {
            side: {
                "H": [0.0, 0.0, 0.0], "d": [0.0, -1.0, 0.0],
                "X": [1.0, 0.0, 0.0], "U": [0.0, 1.0, 0.0],
                "F": [0.0, 0.0, 1.0], "exit": [0.0, -1.0, 0.0],
                "length": 1.0,
            }
            for side in ("left", "right")
        },
        "metadata": {
            "level": 0,
            "admission_status": "accepted",
            "admission_failures": [],
            "base_control_owners": ["domain.cube"] * 8,
            "base_vertex_count": 8,
            "dominant_owner_label": "synthetic cube",
        },
    }


class ConstructionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root, cls.inputs = _root_mesh()
        cls.mesh = construction.build(cls.root, cls.inputs)

    def test_checked_in_inputs_parse_authoritative_shape_without_build(self):
        with (HERE / "inputs.json").open(encoding="utf-8") as handle:
            document = json.load(handle)
        for case in document["cases"]:
            raw = case["leg_inputs"]
            self.assertEqual(set(raw), {"left", "right"})
            parsed = construction._parse_leg_inputs(raw)
            for side in ("left", "right"):
                self.assertEqual(parsed[side]["J"], tuple(raw[side]["J"]))
                self.assertEqual(parsed[side]["T"], tuple(raw[side]["T"]))
                self.assertEqual(parsed[side]["K"], tuple(raw[side]["K"]))
                self.assertEqual(parsed[side]["A"], tuple(raw[side]["A"]))
                self.assertEqual(
                    parsed[side]["mid_thigh_factor"],
                    raw[side]["mid_thigh_factor"],
                )
                self.assertEqual(
                    parsed[side]["support_fraction"],
                    raw[side]["support_fraction"],
                )
                self.assertEqual(
                    parsed[side]["role_metadata"],
                    {key: raw[side][key]
                     for key in ("J_role", "TK_source_role", "distal_design_status")},
                )

    def test_build_preserves_root_and_welds_both_exit_loops(self):
        root_count = len(self.root["vertices"])
        root_face_count = len(self.root["quads"])
        self.assertEqual(self.mesh["vertices"][:root_count], self.root["vertices"])
        self.assertEqual(self.mesh["quads"][:root_face_count], self.root["quads"])
        self.assertEqual(self.mesh["face_owners"][:root_face_count],
                         self.root["face_owners"])
        self.assertNotIn("port.left_thigh", self.mesh["loops"])
        self.assertNotIn("port.right_thigh", self.mesh["loops"])
        self.assertEqual(len(self.mesh["loops"]["port.left_ankle"]), 8)
        self.assertEqual(len(self.mesh["loops"]["port.right_ankle"]), 8)
        self.assertEqual(len(self.mesh["vertices"]), root_count + 2 * 7 * 8)
        self.assertEqual(len(self.mesh["quads"]), root_face_count + 2 * 7 * 8)
        self.assertEqual(self.mesh["metadata"]["index_mapping"]["root_vertex_old_to_new"][-1],
                         [root_count - 1, root_count - 1])

    def test_metadata_records_exact_sections_frames_and_posterior_calf(self):
        for side in ("left", "right"):
            chain = self.mesh["metadata"]["chains"][side]
            self.assertEqual([row["name"] for row in chain["sections"]], [
                "mid_thigh", "knee_pre_support", "knee", "knee_post_support",
                "calf", "ankle_approach", "ankle",
            ])
            self.assertAlmostEqual(chain["sections"][1]["fraction"], 0.90)
            self.assertAlmostEqual(chain["sections"][3]["fraction"], 0.12)
            self.assertEqual(chain["sections"][-1]["indices"], chain["ankle_port"])
            self.assertAlmostEqual(chain["sections"][4]["radii"][2], 0.18)
            for row in chain["sections"]:
                self.assertEqual(set(row["frame"]), {"tangent", "X", "U", "F"})
                self.assertTrue(all(math.isfinite(value)
                                    for values in row["frame"].values()
                                    for value in values))

    def test_support_fraction_moves_named_support_rings(self):
        inputs = json.loads(json.dumps(self.inputs))
        inputs["left"]["support_fraction"] = 0.20
        mesh = construction.build(self.root, inputs)
        for side in ("left", "right"):
            sections = mesh["metadata"]["chains"][side]["sections"]
            pre_fraction = 0.80 if side == "left" else 0.90
            post_fraction = 0.24 if side == "left" else 0.12
            self.assertAlmostEqual(sections[1]["fraction"], pre_fraction)
            self.assertAlmostEqual(sections[3]["fraction"], post_fraction)
            T = inputs[side]["T"]
            K = inputs[side]["K"]
            A = inputs[side]["A"]
            expected_pre = [
                T[index] + pre_fraction * (K[index] - T[index])
                for index in range(3)
            ]
            expected_post = [
                K[index] + post_fraction * (A[index] - K[index])
                for index in range(3)
            ]
            for actual, expected in zip(sections[1]["centre"], expected_pre):
                self.assertAlmostEqual(actual, expected)
            for actual, expected in zip(sections[3]["centre"], expected_post):
                self.assertAlmostEqual(actual, expected)
            self.assertEqual(
                sections[2]["frame"],
                self.mesh["metadata"]["chains"][side]["sections"][2]["frame"],
            )

    def test_one_side_factor_change_is_consumed_only_by_that_side(self):
        inputs = json.loads(json.dumps(self.inputs))
        inputs["right"]["mid_thigh_factor"] = 0.70
        mesh = construction.build(self.root, inputs)
        left_chain = mesh["metadata"]["chains"]["left"]
        right_chain = mesh["metadata"]["chains"]["right"]
        self.assertEqual(left_chain["mid_thigh_factor"], 0.85)
        self.assertEqual(right_chain["mid_thigh_factor"], 0.70)
        self.assertEqual(
            left_chain["sections"][0]["radii"],
            self.mesh["metadata"]["chains"]["left"]["sections"][0]["radii"],
        )
        self.assertNotEqual(
            right_chain["sections"][0]["radii"],
            self.mesh["metadata"]["chains"]["right"]["sections"][0]["radii"],
        )

    def test_unknown_numeric_control_is_rejected(self):
        inputs = json.loads(json.dumps(self.inputs))
        inputs["left"]["unadmitted_numeric_control"] = 1.0
        with self.assertRaises(construction.ConstructionError):
            construction._parse_leg_inputs(inputs)

    def test_reverse_root_winding_keeps_every_band_non_crossed(self):
        root = json.loads(json.dumps(self.root))
        root["quads"] = [list(reversed(face)) for face in root["quads"]]
        mesh = construction.build(root, self.inputs)
        for side in ("left", "right"):
            chain = mesh["metadata"]["chains"][side]
            self.assertEqual(chain["root_edge_winding"], -1)
            rings = [chain["root_exit"]] + [
                section["indices"] for section in chain["sections"]
            ]
            face_index = chain["new_face_indices"][0]
            for source, target in zip(rings, rings[1:]):
                for corner in range(8):
                    expected = [
                        source[corner],
                        source[(corner + 1) % 8],
                        target[(corner + 1) % 8],
                        target[corner],
                    ]
                    self.assertEqual(mesh["quads"][face_index], expected)
                    face_index += 1

    def test_output_is_json_compatible_and_l0_stencils_are_identity(self):
        encoded = json.dumps(self.mesh, allow_nan=False, sort_keys=True)
        self.assertTrue(encoded)
        for index, stencil in enumerate(self.mesh["base_stencils"]):
            self.assertEqual(stencil, [[index, 1.0]])

    def test_evaluate_propagates_generic_lineage_and_new_boundary_loops(self):
        levels = construction.evaluate(self.mesh, levels=2)
        self.assertEqual(len(levels), 3)
        self.assertEqual([level["metadata"]["level"] for level in levels], [0, 1, 2])
        self.assertEqual(len(levels[1]["loops"]["port.left_ankle"]), 16)
        self.assertEqual(len(levels[2]["loops"]["port.right_ankle"]), 32)
        l0_count = len(self.mesh["vertices"])
        for level in levels[1:]:
            self.assertEqual(len(level["base_stencils"]), len(level["vertices"]))
            for stencil in level["base_stencils"]:
                self.assertAlmostEqual(sum(term[1] for term in stencil), 1.0)
                self.assertTrue(all(0 <= term[0] < l0_count and term[1] >= 0.0
                                    for term in stencil))
        self.assertNotIn("port.left_thigh", levels[2]["loops"])
        self.assertNotIn("port.right_thigh", levels[2]["loops"])
        self.assertEqual(json.dumps(levels, allow_nan=False)[:1], "[")

    def test_closed_cube_uses_same_cc_counts_and_valid_stencils(self):
        levels = construction.evaluate(_closed_cube(), levels=2)
        self.assertEqual([len(level["vertices"]) for level in levels], [8, 26, 98])
        self.assertEqual([len(level["quads"]) for level in levels], [6, 24, 96])
        for level_index, level in enumerate(levels):
            self.assertEqual(level["loops"], {})
            self.assertEqual(level["metadata"]["level"], level_index)
            for stencil in level["base_stencils"]:
                self.assertAlmostEqual(sum(term[1] for term in stencil), 1.0)
                self.assertTrue(all(0 <= term[0] < 8 and term[1] >= 0.0
                                    for term in stencil))

    def test_open_output_matches_frozen_generic_numeric_hash(self):
        actual = construction.evaluate(self.mesh, levels=2)
        generic = construction._load_generic_transition()
        expected = generic.evaluate(self.mesh, levels=2)
        actual_bytes = json.dumps(actual, sort_keys=True, allow_nan=False).encode()
        expected_bytes = json.dumps(expected, sort_keys=True, allow_nan=False).encode()
        self.assertEqual(hashlib.sha256(actual_bytes).hexdigest(),
                         hashlib.sha256(expected_bytes).hexdigest())

    def test_closed_mesh_missing_declared_loop_is_rejected(self):
        hostile = _closed_cube()
        hostile["quads"] = hostile["quads"][:-1]
        hostile["face_owners"] = hostile["face_owners"][:-1]
        with self.assertRaisesRegex(construction.ConstructionError,
                                    "declared loops do not cover"):
            construction.evaluate(hostile, levels=2)

    def test_frame_admission_rejects_missing_malformed_and_nonfinite_metadata(self):
        missing = _closed_cube()
        del missing["frames"]["right"]
        with self.assertRaisesRegex(construction.ConstructionError,
                                    "frames must contain exactly"):
            construction.evaluate(missing, levels=0)

        malformed = _closed_cube()
        malformed["frames"]["left"] = []
        with self.assertRaisesRegex(construction.ConstructionError,
                                    "frames.left must be a mapping"):
            construction.evaluate(malformed, levels=0)

        nonfinite = _closed_cube()
        nonfinite["frames"]["right"]["H"][0] = float("nan")
        with self.assertRaisesRegex(construction.ConstructionError,
                                    "frames.right.H\[0\]"):
            construction.evaluate(nonfinite, levels=0)

    def test_closed_evaluator_cache_isolated_between_loaded_constructions(self):
        names = ("_ck_construction_cache_isolation_one",
                 "_ck_construction_cache_isolation_two")
        loaded = []
        evaluators = []
        try:
            for name in names:
                sys.modules.pop(name, None)
                spec = importlib.util.spec_from_file_location(
                    name, HERE / "construction.py")
                self.assertIsNotNone(spec)
                self.assertIsNotNone(spec.loader)
                module = importlib.util.module_from_spec(spec)
                sys.modules[name] = module
                spec.loader.exec_module(module)
                loaded.append(module)
                evaluators.append(module._load_closed_generic_transition())

            self.assertIsNot(evaluators[0], evaluators[1])
            self.assertNotEqual(evaluators[0].__name__, evaluators[1].__name__)
            self.assertIs(evaluators[0]._validate_mesh,
                          loaded[0]._closed_generic_validation)
            self.assertIs(evaluators[1]._validate_mesh,
                          loaded[1]._closed_generic_validation)
        finally:
            for module in evaluators + loaded:
                sys.modules.pop(module.__name__, None)

    def test_incompatible_root_or_zero_leg_segment_fails_closed(self):
        bad_inputs = json.loads(json.dumps(self.inputs))
        bad_inputs["left"]["T"][1] = 0.1
        with self.assertRaises(construction.ConstructionError):
            construction.build(self.root, bad_inputs)
        bad_inputs = json.loads(json.dumps(self.inputs))
        bad_inputs["right"]["A"] = bad_inputs["right"]["K"]
        with self.assertRaises(construction.ConstructionError):
            construction.build(self.root, bad_inputs)


if __name__ == "__main__":
    unittest.main()
