import copy
import importlib.util
import math
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("pelvis_hip_checks", ROOT / "checks.py")
CHECKS = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = CHECKS
SPEC.loader.exec_module(CHECKS)


def mm(a, b):
    return [[sum(a[r][k] * b[k][c] for k in range(4)) for c in range(4)] for r in range(4)]


def mp(m, p):
    q = [*p, 1.0]
    return [sum(m[r][c] * q[c] for c in range(4)) for r in range(3)]


def rigid(origin):
    x, y, z = origin
    rest = [[1., 0., 0., x], [0., 1., 0., y], [0., 0., 1., z], [0., 0., 0., 1.]]
    inv = [[1., 0., 0., -x], [0., 1., 0., -y], [0., 0., 1., -z], [0., 0., 0., 1.]]
    return rest, inv


def fixture(left=15.0, right=0.0, left_joint_y=0.0):
    vertices = [
        [-.5, .8, 0.], [.5, .8, 0.], [.5, 1.2, 0.], [-.5, 1.2, 0.],
        [-1.2, -.4, 0.], [-.8, -.4, 0.], [-.8, -.9, 0.], [-1.2, -.9, 0.],
        [.8, -.4, 0.], [1.2, -.4, 0.], [1.2, -.9, 0.], [.8, -.9, 0.],
    ]
    quads = [[0, 1, 2, 3], [4, 5, 6, 7], [8, 9, 10, 11]]
    loops = {"port.left_thigh": [4, 5, 6, 7], "port.right_thigh": [8, 9, 10, 11]}
    rest = {"vertices": vertices, "quads": quads, "loops": loops,
            "face_owners": ["domain.pelvis", "domain.left_hip", "domain.right_hip"]}
    ident, ident_inv = rigid((0., 0., 0.))
    left_rest, left_inv = rigid((-1., left_joint_y, 0.))
    right_rest, right_inv = rigid((1., 0., 0.))
    joints = {"pelvis": {"rest_matrix": ident, "inverse_bind_matrix": ident_inv},
              "left_hip": {"rest_matrix": left_rest, "inverse_bind_matrix": left_inv},
              "right_hip": {"rest_matrix": right_rest, "inverse_bind_matrix": right_inv}}
    weights = [[1., 0., 0.]] * 4 + [[0., 1., 0.]] * 4 + [[0., 0., 1.]] * 4
    binding = {"joint_order": ["pelvis", "left_hip", "right_hip"], "evaluated_weights": weights,
               "rest_frames": {
                   "left": {"rest_matrix": left_rest, "J": [-1., left_joint_y, 0.], "T": [-1., -.5, 0.], "K": [-1., -1., 0.],
                            "T_local": [0., -.5-left_joint_y, 0.], "K_local": [0., -1.-left_joint_y, 0.]},
                   "right": {"rest_matrix": right_rest, "J": [1., 0., 0.], "T": [1., -.5, 0.], "K": [1., -1., 0.],
                             "T_local": [0., -.5, 0.], "K_local": [0., -1., 0.]},
               }}
    poses = {"pelvis": ident}
    for side, angle, rest_matrix in (("left", left, left_rest), ("right", right, right_rest)):
        a = math.radians(-angle); c, s = math.cos(a), math.sin(a)
        poses[f"{side}_hip"] = mm(rest_matrix, [[1.,0.,0.,0.], [0.,c,-s,0.], [0.,s,c,0.], [0.,0.,0.,1.]])
    skins = {name: mm(poses[name], joints[name]["inverse_bind_matrix"]) for name in poses}
    posed_vertices = []
    for p, row in zip(vertices, weights):
        posed_vertices.append([sum(row[j] * mp(skins[name], p)[a] for j, name in enumerate(("pelvis", "left_hip", "right_hip"))) for a in range(3)])
    posed = {**copy.deepcopy(rest), "vertices": posed_vertices,
             "provenance": {"vertices": "POSED_BY_REST_L2_3JOINT_LBS", "base_stencils": "REST"},
             "metadata": {"posed_cage_evaluation": False, "pose_angles_degrees": {"left": left, "right": right}}}
    refs = {"joint_left": [-1., left_joint_y, 0.], "joint_right": [1., 0., 0.],
            "crest_left": [-1., .5, 0.], "crest_right": [1., .5, 0.]}
    case = {"diagnostic_scale": 1., "attachments": {
        "left": {"centre": [-1., -.5, 0.], "knee": [-1., -1., 0.]},
        "right": {"centre": [1., -.5, 0.], "knee": [1., -1., 0.]}}}
    protocol = {"checks": {
        "identity_error_over_L_max": 1e-12, "weight_partition_tolerance": 1e-12,
        "frame_and_transform_tolerance": 1e-10, "exported_LBS_error_over_L_max": 1e-10,
        "rigid_port_error_over_L_max": 1e-9, "pelvis_only_weighted_error_over_L_max": 1e-10,
        "above_crest_skin_displacement_over_L_max": .01, "lower_triangle_area_ratio": [.5, 2.],
        "lower_edge_length_ratio": [.65, 1.5], "lower_rest_posed_triangle_normal_dot_min": 0.,
        "lower_nonadjacent_intersections_max": 0}}
    return rest, posed, binding, {"left": left, "right": right}, case, refs, protocol


def binding_fixture():
    vertices = [[float(x), float(y), 0.] for y in range(3) for x in range(4)]
    quads = [[y*4+x, y*4+x+1, (y+1)*4+x+1, (y+1)*4+x] for y in range(2) for x in range(3)]
    transitions = {"left": {"socket": [4], "ringA": [5], "ringB": [0], "exit": [1]},
                   "right": {"socket": [6], "ringA": [7], "ringB": [2], "exit": [3]}}
    base = {"vertices": vertices, "quads": quads, "metadata": {"transition_indices": transitions}}
    graph = [set() for _ in vertices]
    for quad in quads:
        for i, vertex in enumerate(quad): graph[vertex].add(quad[(i+1) % 4]); graph[quad[(i+1) % 4]].add(vertex)
    unknown = [4, 5, 6, 7]; position = {vertex: i for i, vertex in enumerate(unknown)}
    matrix = [[0.]*4 for _ in range(4)]; fixed = [[0., 0., 0.] for _ in vertices]
    for i in (0, 1): fixed[i] = [0., 1., 0.]
    for i in (2, 3): fixed[i] = [0., 0., 1.]
    for i in range(8, 12): fixed[i] = [1., 0., 0.]
    rhs = [[0.]*3 for _ in range(4)]
    for vertex, row in position.items():
        matrix[row][row] = len(graph[vertex])
        for neighbour in graph[vertex]:
            if neighbour in position: matrix[row][position[neighbour]] -= 1.
            else:
                for column in range(3): rhs[row][column] += fixed[neighbour][column]
    augmented = [matrix[i] + rhs[i] for i in range(4)]
    for column in range(4):
        pivot = max(range(column, 4), key=lambda row: abs(augmented[row][column]))
        augmented[column], augmented[pivot] = augmented[pivot], augmented[column]
        divisor = augmented[column][column]; augmented[column] = [x/divisor for x in augmented[column]]
        for row in range(4):
            if row != column:
                factor = augmented[row][column]
                augmented[row] = [a-factor*b for a, b in zip(augmented[row], augmented[column])]
    for row, vertex in enumerate(unknown): fixed[vertex] = augmented[row][4:]
    rest = {"vertices": copy.deepcopy(vertices), "base_stencils": [[[i, 1.]] for i in range(len(vertices))]}
    binding = {"base_weights": copy.deepcopy(fixed), "evaluated_weights": copy.deepcopy(fixed)}
    protocol = fixture()[-1]
    return base, rest, binding, protocol


class CheckPoseTests(unittest.TestCase):
    def check(self, values):
        return CHECKS.check_pose(*values)

    def test_import_smoke_and_independent_matrix_response(self):
        values = fixture()
        self.assertGreater(values[1]["vertices"][6][2], 0.1)
        report = self.check(values)
        self.assertTrue(report["pass"], report)
        self.assertLessEqual(report["metrics"]["posed_lbs_max_error"], 1e-10)
        self.assertIn("frozen_pelvis_transition_checks", sys.modules)
        self.assertTrue(report["checks"]["lower_nonadjacent_self_intersection"])
        self.assertEqual(report["metrics"]["lower_intersection_count"], 0)

    def test_wrong_pivot_is_caught(self):
        values = list(fixture())
        values[2] = copy.deepcopy(values[2])
        values[2]["rest_frames"]["left"]["rest_matrix"][1][3] = .1
        report = self.check(values)
        self.assertFalse(report["pass"])
        self.assertFalse(report["checks"]["frames"])

    def test_left_joint_up_counterfactual_changes_pose_without_retuning(self):
        nominal = fixture(left_joint_y=0.0)
        shifted = fixture(left_joint_y=.01)
        report = self.check(shifted)
        response = max(math.dist(a, b) for a, b in zip(nominal[1]["vertices"], shifted[1]["vertices"]))
        self.assertTrue(report["pass"], report)
        self.assertGreater(response, 1e-4)
        self.assertEqual(nominal[2]["evaluated_weights"], shifted[2]["evaluated_weights"])

    def test_static_export_is_caught(self):
        values = list(fixture())
        values[1] = copy.deepcopy(values[1]); values[1]["vertices"] = copy.deepcopy(values[0]["vertices"])
        report = self.check(values)
        self.assertFalse(report["pass"])
        self.assertFalse(report["checks"]["independent_lbs"])

    def test_malformed_weights_are_caught(self):
        values = list(fixture())
        values[2] = copy.deepcopy(values[2]); values[2]["evaluated_weights"][4] = [1.2, -.2, 0.]
        report = self.check(values)
        self.assertFalse(report["pass"])
        self.assertFalse(report["checks"]["weight_bounds"])

    def test_declared_weight_roundoff_tolerance_is_accepted(self):
        values = list(fixture())
        values[2] = copy.deepcopy(values[2])
        values[2]["evaluated_weights"][4] = [-5e-13, 1.0+5e-13, 0.]
        report = self.check(values)
        self.assertTrue(report["checks"]["weight_bounds"], report)
        self.assertTrue(report["checks"]["partition_unity"], report)

    def test_crest_ceiling_uses_higher_declared_crest(self):
        values = fixture()
        refs = copy.deepcopy(values[5]); refs["crest_left"][1] = .4; refs["crest_right"][1] = .6
        normalized = CHECKS._references(values[4], refs)
        self.assertEqual(normalized["crest_y"], .6)

    def test_modified_quad_is_caught(self):
        values = list(fixture())
        values[1] = copy.deepcopy(values[1]); values[1]["quads"][1] = [4, 5, 7, 6]
        report = self.check(values)
        self.assertFalse(report["pass"])
        self.assertFalse(report["checks"]["exact_topology"])

    def test_gross_collapse_is_caught(self):
        values = list(fixture())
        values[1] = copy.deepcopy(values[1])
        for i in (4, 5, 6, 7): values[1]["vertices"][i] = copy.deepcopy(values[1]["vertices"][4])
        report = self.check(values)
        self.assertFalse(report["pass"])
        self.assertFalse(report["checks"]["triangle_area_ratios"])

    def test_binding_method_and_wrong_in_range_field(self):
        values = binding_fixture()
        self.assertTrue(CHECKS.check_binding(*values)["pass"])
        wrong = list(values); wrong[2] = copy.deepcopy(values[2])
        wrong[2]["base_weights"][4][0] += .01
        wrong[2]["base_weights"][4][1] -= .01
        wrong[2]["evaluated_weights"] = copy.deepcopy(wrong[2]["base_weights"])
        report = CHECKS.check_binding(*wrong)
        self.assertFalse(report["pass"])
        self.assertFalse(report["checks"]["harmonic_residual"])
        self.assertTrue(report["checks"]["stencil_transfer"])


if __name__ == "__main__":
    unittest.main()
