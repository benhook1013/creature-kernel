"""Static and captured real-build JUNCTION-001 contract tests.

Raman owns execution of geometry-building tests.  The synthetic tests exercise
the declared local graph and accounting rules.  The real-build smoke is
intended for the captured run only: it uses both immutable connected-leg cases
and genuine FOOT-004 inputs, without L2 evaluation or the collision core.
"""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import sys
import unittest


EXPERIMENT_DIR = Path(__file__).resolve().parents[1]
if str(EXPERIMENT_DIR) not in sys.path:
    sys.path.insert(0, str(EXPERIMENT_DIR))

import foot_construction  # noqa: E402
import foot_form_construction  # noqa: E402
import foot_junction_construction as junction  # noqa: E402
import construction  # noqa: E402


INPUTS_PATH = EXPERIMENT_DIR / "inputs.json"
FORM_INPUTS_PATH = EXPERIMENT_DIR / "foot-form-inputs.json"
POLICY_PATH = EXPERIMENT_DIR / "foot-junction-policy.json"
EXPECTED_CASES = (
    "calibrated_ordinary_human",
    "calibrated_upright_anthropomorphic",
)


def _policy() -> dict:
    return json.loads(POLICY_PATH.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _captured_real_cases() -> list[dict]:
    document = json.loads(INPUTS_PATH.read_text(encoding="utf-8"))
    form_document = json.loads(FORM_INPUTS_PATH.read_text(encoding="utf-8"))
    forms = {row["case_id"]: row for row in form_document["cases"]}
    result = []
    for case in document["cases"]:
        if case["id"] not in EXPECTED_CASES:
            continue
        root_ref = case["root_mesh"]
        root_path = Path(root_ref["path"])
        if _sha256(root_path) != root_ref["sha256"]:
            raise AssertionError(f"immutable root identity drifted: {root_path}")
        result.append({
            "id": case["id"],
            "root": json.loads(root_path.read_text(encoding="utf-8")),
            "leg_inputs": copy.deepcopy(case["leg_inputs"]),
            "form_inputs": forms[case["id"]],
        })
    if tuple(row["id"] for row in result) != EXPECTED_CASES:
        raise AssertionError("the two canonical connected-leg cases were not loaded")
    return result


def _source_grid(base: dict, row: dict, side: str) -> tuple[dict, dict]:
    base_vertices = [tuple(point) for point in base["vertices"]]
    ankle_loop, ankle_centre, attachment_frame = foot_construction._ankle_chain(
        base, side, row["leg_inputs"][side], base_vertices, base["loops"]
    )
    source_frame = foot_form_construction._source_frame(
        base, side, attachment_frame
    )
    controls = row["form_inputs"]["sides"][side]
    grid = foot_form_construction._grid_points(
        ankle_centre, source_frame,
        {name: controls[name] for name in foot_form_construction._ANCHORS},
        row["form_inputs"]["construction"], side,
    )
    return source_frame, grid


def _grid() -> dict:
    top = [[(float(column), float(row), 1.0) for column in range(5)]
           for row in range(8)]
    bottom = [[(float(column), float(row), -1.0) for column in range(5)]
              for row in range(8)]
    return {"top": top, "bottom": bottom}


def _synthetic_junction_faces():
    local = junction._local_grid(_grid())
    by_name = junction._body_faces(local)
    body_faces = [face for name in ("dorsal_grid", "plantar_grid", "outer_perimeter")
                  for face in by_name[name]]
    holes = [local["top"][row][column]
             for row, column in junction._HOLE_POSITIONS]
    holes = [int(index) for index in holes]
    local_to_output = {}
    output_points = []
    for index, point in enumerate(local["points"]):
        if index in holes:
            continue
        local_to_output[index] = len(output_points)
        output_points.append(point)
    actual_start = len(output_points)
    actual_loop = list(range(actual_start, actual_start + 8))
    hole_to_actual = dict(zip(holes, actual_loop))
    actual_points = [
        tuple(local["points"][index][axis] + (0.0 if axis != 2 else 0.25)
              for axis in range(3))
        for index in holes
    ]
    output_points.extend(actual_points)
    support_start = len(output_points)
    for index in range(8):
        output_points.extend(((0.0, 0.0, 0.0), (0.0, 1.0, 0.0)))
    base_faces = []
    for index in range(8):
        left = actual_loop[index]
        right = actual_loop[(index + 1) % 8]
        support = support_start + 2 * index
        base_faces.append((left, right, support, support + 1))
    output_faces = list(base_faces)
    new_faces = []
    for face in body_faces:
        mapped = junction._map_local_face(
            face, local_to_output, hole_to_actual, "synthetic junction face"
        )
        output_faces.append(mapped)
        new_faces.append(len(output_faces) - 1)
    return local, by_name, output_points, output_faces, new_faces, actual_loop


class JunctionPolicyTests(unittest.TestCase):
    def test_policy_seals_frontier_and_forbids_old_builders(self):
        policy = _policy()
        parsed = junction._policy(policy)
        self.assertEqual(parsed["graph"]["frontier_row"], 5)
        self.assertEqual(parsed["graph"]["frontier_source"], "M")
        self.assertEqual(parsed["output"]["connector_rings"], False)
        self.assertEqual(
            parsed["source"]["forbidden_builders"],
            ["foot_form_construction.build", "foot_attachment_construction.build"],
        )

    def test_graph_is_79_vertices_and_74_quads(self):
        local = junction._local_grid(_grid())
        faces = junction._body_faces(local)
        self.assertEqual(len(local["points"]), 79)
        self.assertEqual(sum(len(value) for value in faces.values()), 74)
        self.assertEqual(len(local["top"]), 8)
        self.assertEqual(local["top"][2][2], None)


class HarmonicDisplacementTests(unittest.TestCase):
    def setUp(self):
        self.policy = _policy()
        self.local = junction._local_grid(_grid())
        by_name = junction._body_faces(self.local)
        self.faces = [face for name in ("dorsal_grid", "plantar_grid", "outer_perimeter")
                      for face in by_name[name]]
        self.frame = {"X": (1.0, 0.0, 0.0), "U": (0.0, 1.0, 0.0),
                      "F": (0.0, 0.0, 1.0)}
        self.holes = [self.local["top"][row][column]
                      for row, column in junction._HOLE_POSITIONS]
        self.holes = [int(index) for index in self.holes]

    def _solve(self, forward=0.02):
        deltas = [(0.01 * index, 0.0, forward) for index in range(8)]
        return junction._displacements(
            self.local, self.faces, self.frame, self.holes, deltas,
            self.policy, "synthetic",
        )

    def test_fixed_frontier_and_plantar_u_are_exact_constraints(self):
        displacements, record = self._solve()
        for index, row in enumerate(self.local["rows"]):
            if row in (0, 5, 6, 7):
                self.assertEqual(displacements[index], (0.0, 0.0, 0.0))
            if self.local["regions"][index] == "plantar" and row in (1, 2, 3, 4):
                self.assertEqual(displacements[index][1], 0.0)
        self.assertEqual(record["basis_order"], ["X", "U", "F"])
        self.assertLessEqual(record["max_residual"], 1.0e-10)

    def test_source_change_reaches_a_free_cage_vertex(self):
        first, _ = self._solve(forward=0.01)
        second, _ = self._solve(forward=0.03)
        free_index = self.local["top"][2][0]
        self.assertNotEqual(first[free_index], second[free_index])
        self.assertEqual(first[self.local["top"][5][2]], (0.0, 0.0, 0.0))

    def test_disconnected_free_component_fails_without_fallback(self):
        adjacency = [{1}, {0}, set()]
        with self.assertRaises(junction.FootJunctionConstructionError):
            junction._harmonic_values(adjacency, {0: 0.0}, 1.0e-10, "hostile")

    def test_mirrored_frames_preserve_local_solution_and_mirror_world_x(self):
        left = junction._world_from_components(
            {"X": (1.0, 0.0, 0.0), "U": (0.0, 1.0, 0.0), "F": (0.0, 0.0, 1.0)},
            (0.03, 0.01, 0.02),
        )
        right = junction._world_from_components(
            {"X": (-1.0, 0.0, 0.0), "U": (0.0, 1.0, 0.0), "F": (0.0, 0.0, -1.0)},
            (0.03, 0.01, 0.02),
        )
        self.assertEqual(junction._cross((1.0, 0.0, 0.0), (0.0, 1.0, 0.0)),
                         (0.0, 0.0, 1.0))
        self.assertEqual(junction._cross((-1.0, 0.0, 0.0), (0.0, 1.0, 0.0)),
                         (0.0, 0.0, -1.0))
        self.assertEqual(left[0], -right[0])
        self.assertEqual(left[1], right[1])
        self.assertEqual(left[2], -right[2])


class CapturedRealBuildSmokeTests(unittest.TestCase):
    """Run only from Raman's capture; this is not a live pre-capture test."""

    @classmethod
    def setUpClass(cls):
        cls.rows = _captured_real_cases()
        cls.outputs = []
        for row in cls.rows:
            base = construction.build(row["root"], row["leg_inputs"])
            output = junction.build(
                base, row["leg_inputs"], row["form_inputs"], _policy()
            )
            cls.outputs.append((row, base, output))

    def _assert_inherited_prefix(self, base, output):
        base_count = len(base["vertices"])
        face_count = len(base["quads"])
        # Keep these exact comparisons independent of any vertex-ID mapping
        # used by the local junction grid.
        self.assertEqual(output["vertices"][:base_count], base["vertices"])
        self.assertEqual(output["quads"][:face_count], base["quads"])

    def _assert_fixed_rows(self, row, base, output):
        for side in ("left", "right"):
            source_frame, grid = _source_grid(base, row, side)
            foot = output["metadata"]["feet"][side]
            for grid_name, source_name in (("dorsal", "top"), ("plantar", "bottom")):
                output_rows = foot["output_grid_indices"][grid_name]
                source_rows = grid[source_name]
                for row_index in (5, 6, 7):
                    for column, output_index in enumerate(output_rows[row_index]):
                        expected = tuple(source_rows[row_index][column])
                        actual = tuple(output["vertices"][output_index])
                        self.assertEqual(actual, expected)

            for row_index in (1, 2, 3, 4):
                for column, output_index in enumerate(foot["output_grid_indices"]["plantar"][row_index]):
                    expected = tuple(grid["bottom"][row_index][column])
                    actual = tuple(output["vertices"][output_index])
                    displacement = junction._sub(actual, expected)
                    # The policy fixes the local U component exactly; X/F
                    # remain harmonic unknowns and are intentionally not
                    # compared to the source point here.
                    self.assertLess(abs(junction._dot(displacement, source_frame["U"])),
                                    1.0e-12)

    def test_captured_real_foot004_build_preserves_prefix_fixed_frontier_and_plantar_u(self):
        self.assertEqual([row["id"] for row in self.rows], list(EXPECTED_CASES))
        for row, base, output in self.outputs:
            with self.subTest(case=row["id"]):
                self._assert_inherited_prefix(base, output)
                self._assert_fixed_rows(row, base, output)

    def test_captured_a_perturbation_reaches_free_proximal_output(self):
        row = copy.deepcopy(self.rows[0])
        _baseline_row, baseline_base, baseline_output = self.outputs[0]
        row["leg_inputs"]["left"]["A"][2] += 0.01
        changed_base = construction.build(row["root"], row["leg_inputs"])
        changed_output = junction.build(
            changed_base, row["leg_inputs"], row["form_inputs"], _policy()
        )

        self._assert_inherited_prefix(changed_base, changed_output)
        self._assert_fixed_rows(row, changed_base, changed_output)
        baseline_foot = baseline_output["metadata"]["feet"]["left"]
        changed_foot = changed_output["metadata"]["feet"]["left"]
        baseline_index = baseline_foot["output_grid_indices"]["dorsal"][2][0]
        changed_index = changed_foot["output_grid_indices"]["dorsal"][2][0]
        self.assertNotEqual(
            tuple(baseline_output["vertices"][baseline_index]),
            tuple(changed_output["vertices"][changed_index]),
        )
        self.assertEqual(
            baseline_output["vertices"][:len(baseline_base["vertices"])],
            baseline_base["vertices"],
        )


class MouthAndAccountingTests(unittest.TestCase):
    def test_direct_mouth_weld_and_no_duplicate_mouth_vertices(self):
        _local, _by_name, vertices, quads, new_faces, actual_loop = _synthetic_junction_faces()
        junction._validate_side_output(
            vertices, quads, new_faces, actual_loop, "synthetic"
        )
        self.assertEqual(len(set(actual_loop)), 8)
        self.assertEqual(len(new_faces), 74)
        uses = foot_construction._edge_uses([tuple(face) for face in quads])
        for index, left in enumerate(actual_loop):
            edge = tuple(sorted((left, actual_loop[(index + 1) % 8])))
            self.assertEqual(len(uses[edge]), 2)

    def test_fixed_rows_keep_exact_source_points_in_moved_grid(self):
        local = junction._local_grid(_grid())
        frame = {"X": (1.0, 0.0, 0.0), "U": (0.0, 1.0, 0.0),
                 "F": (0.0, 0.0, 1.0)}
        faces_by_name = junction._body_faces(local)
        faces = [face for name in ("dorsal_grid", "plantar_grid", "outer_perimeter")
                 for face in faces_by_name[name]]
        holes = [int(local["top"][row][column])
                 for row, column in junction._HOLE_POSITIONS]
        displacements, _ = junction._displacements(
            local, faces, frame, holes, [(0.0, 0.0, 0.0)] * 8,
            _policy(), "synthetic",
        )
        moved = [junction._add(point, junction._world_from_components(frame, displacement))
                 for point, displacement in zip(local["points"], displacements)]
        for index, row in enumerate(local["rows"]):
            if row in (0, 5, 6, 7):
                self.assertEqual(moved[index], local["points"][index])


if __name__ == "__main__":
    unittest.main()
