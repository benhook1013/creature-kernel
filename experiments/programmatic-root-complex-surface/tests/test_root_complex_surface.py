from __future__ import annotations

from copy import deepcopy
from dataclasses import FrozenInstanceError
import json
import math
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import root_complex_surface as surface  # noqa: E402
import mesh_correctness  # noqa: E402
import build_root_complex  # noqa: E402

def synthetic_prepared():
    def station(center, radius, front, back, name):
        return dict(center=center, lateral_radius=radius, front_extent=front,
                    back_extent=back, provenance=f"synthetic.station.{name}")

    def landmark(point, name):
        return {"point": point, "provenance": f"synthetic.landmark.{name}"}

    def scalar(value, name):
        return {"value": value, "provenance": f"synthetic.scalar.{name}"}

    stations = {
        "neck_collar": station((0.0, 3.1, 0.0), 0.55, 0.42, 0.36, "neck"),
        "upper_ribcage_shoulder": station((0.0, 2.45, 0.0), 1.45, 0.82, 0.67, "upper_rib"),
        "lower_ribcage": station((0.0, 1.55, 0.0), 1.28, 0.73, 0.65, "lower_rib"),
        "waist_abdomen": station((0.0, 0.72, 0.0), 0.94, 0.58, 0.55, "waist"),
        "lower_abdomen": station((0.0, 0.28, 0.0), 1.03, 0.62, 0.58, "abdomen"),
        "upper_pelvis": station((0.0, 0.02, 0.0), 1.37, 0.72, 0.66, "upper_pelvis"),
        "lower_pelvis": station((0.0, -0.68, 0.0), 1.20, 0.66, 0.61, "lower_pelvis"),
    }
    landmarks = {}
    for side, sign in (("left", -1.0), ("right", 1.0)):
        for kind, x, y, z in (("shoulder_peak", 1.38, 2.55, 0.0),
                              ("axilla", 1.25, 1.76, 0.0),
                              ("thigh_start", 0.78, -0.70, 0.0),
                              ("thigh_mid", 0.82, -1.85, 0.03)):
            name = f"{kind}_{side}"; landmarks[name] = landmark((sign * x, y, z), name)
    frame = dict(zip(("lateral_axis", "up_axis", "forward_axis"),
                     ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))))
    frame["provenance"] = "synthetic.frame.body"
    scalars = {name: scalar(value, name) for name, value in (
        ("arm_root_depth", 0.34), ("arm_root_outward", 0.22),
        ("thigh_lateral_radius", 0.70), ("thigh_depth", 0.42))}
    return {"source": {"document": "synthetic_root_complex", "namespace": "synthetic", "sha256": "synthetic-source", "provenance": "synthetic.source"},
            "basis": {"length_unit": "metre", "handedness": "right", "up": "+y", "forward": "+z"},
            "stations": stations, "landmarks": landmarks, "frames": {"body": frame}, "scalars": scalars}
def independent_subdivision_stencils(quads, loops, vertex_count):
    uses = {}
    for face_index, face in enumerate(quads):
        for a, b in zip(face, face[1:] + face[:1]): uses.setdefault(tuple(sorted((a, b))), []).append(face_index)
    boundary, incident = {}, {}
    for edge, face_indices in uses.items():
        for vertex in edge: incident.setdefault(vertex, []).extend(face_indices)
        if len(face_indices) == 1:
            boundary.setdefault(edge[0], []).append(edge[1]); boundary.setdefault(edge[1], []).append(edge[0])
    sources = []
    for vertex in range(vertex_count): sources.append({vertex, *boundary[vertex]} if vertex in boundary else {v for fi in incident[vertex] for v in quads[fi]})
    edges = tuple(sorted(uses))
    for edge in edges: sources.append(set(edge) | ({v for fi in uses[edge] for v in quads[fi]} if len(uses[edge]) == 2 else set()))
    sources.extend(set(face) for face in quads)
    edge_index = {edge: vertex_count + i for i, edge in enumerate(edges)}
    face_index = {fi: vertex_count + len(edges) + fi for fi in range(len(quads))}
    next_quads = tuple((vertex, edge_index[tuple(sorted((vertex, face[(i + 1) % 4])))], face_index[fi], edge_index[tuple(sorted((face[i - 1], vertex)))]) for fi, face in enumerate(quads) for i, vertex in enumerate(face))
    next_loops = tuple((name, tuple(value for i, vertex in enumerate(loop) for value in (vertex, edge_index[tuple(sorted((vertex, loop[(i + 1) % len(loop)]))) ]))) for name, loop in loops)
    return tuple(sources), next_quads, next_loops
def station_fields(name):
    return {f"stations.{name}.{key}" for key in ("center", "lateral_radius", "front_extent", "back_extent")}
class SymbolicTopologyTests(unittest.TestCase):
    def test_exact_counts_loops_euler_orientation_and_valences(self):
        ids, quads, loops = surface.symbolic_topology()
        report = surface.validate_topology(len(ids), quads, loops, surface.EXPECTED_VALENCES)
        self.assertEqual(surface.RING_NAMES, ("neck_collar", "upper_ribcage_shoulder", "axilla_transition", "lower_ribcage", "waist_abdomen", "iliac_overlap", "lower_pelvis"))
        self.assertEqual((report.vertex_count, report.edge_count, report.face_count), (72, 138, 63))
        self.assertEqual((report.boundary_edge_count, report.euler, report.boundary_lengths,
                          report.valence_inventory), (24, -3, (8, 4, 4, 4, 4), ((3, 22), (4, 40), (5, 10))))
        self.assertEqual(loops, (("neck", (0, 1, 2, 3, 4, 5, 6, 7)), ("left_arm", (56, 59, 58, 57)),
                                 ("right_arm", (60, 63, 62, 61)), ("left_thigh", (64, 67, 66, 65)),
                                 ("right_thigh", (68, 69, 70, 71))))
        self.assertEqual((ids[16:24], ids[56:64], ids[64:72]),
                         (tuple(f"ring.axilla_transition.{i}" for i in range(8)),
                          tuple(f"shoulder.{side}.{i}" for side in ("left", "right") for i in range(4)),
                          tuple(f"thigh.{side}.{i}" for side in ("left", "right") for i in range(4))))
        uses = {}
        for face in quads:
            for a, b in zip(face, face[1:] + face[:1]):
                uses.setdefault(tuple(sorted((a, b))), []).append((a, b))
        self.assertTrue(all(len(value) in (1, 2) for value in uses.values()))
        self.assertTrue(all(value[0] == tuple(reversed(value[1]))
                            for value in uses.values() if len(value) == 2))
    def test_validator_rejects_bad_quad_and_boundary_declaration(self):
        ids, quads, loops = surface.symbolic_topology()
        with self.assertRaisesRegex(ValueError, "quad index"):
            surface.validate_topology(len(ids), quads[:-1] + ((0, 1, 2, 99),), loops)
        with self.assertRaisesRegex(ValueError, "declared boundary"):
            surface.validate_topology(len(ids), quads, loops[:-1])
        reversed_loop = list(loops); reversed_loop[1] = ("left_arm", tuple(reversed(loops[1][1])))
        with self.assertRaisesRegex(ValueError, "directed winding"): surface.validate_topology(len(ids), quads, tuple(reversed_loop))
        same_direction = list(quads); same_direction[8] = tuple(reversed(same_direction[8]))
        with self.assertRaisesRegex(ValueError, "same direction"): surface.validate_topology(len(ids), tuple(same_direction), loops)
        reversed_faces = tuple(tuple(reversed(face)) for face in quads); reversed_loops = tuple((name, tuple(reversed(loop))) for name, loop in loops); self.assertEqual(surface.validate_topology(len(ids), reversed_faces, reversed_loops), surface.validate_topology(len(ids), quads, loops))
class FormulaAndInputTests(unittest.TestCase):
    def test_plain_mapping_build_has_complete_immutable_records(self):
        cage = surface.build_cage(synthetic_prepared())
        self.assertEqual((len(cage.vertices), len(cage.quads), len(set(cage.control_ids)),
                          len(cage.formula_ids)), (72, 63, 72, 72))
        self.assertTrue(all(item for item in cage.dependencies) and all(item for item in cage.provenance_ids))
        self.assertEqual(set(cage.formula_ids), {
            "station.asymmetric_superellipse", "iliac.blend.superellipse",
            "shoulder.axilla_transition", "shoulder.peak_axilla_collar",
            "shoulder.superior_axial_saddle", "station.axial_envelope.min_clamp",
            "thigh.seat_gap_loop",
        })
        with self.assertRaises(FrozenInstanceError):
            cage.vertices = ()
    def test_number_admission_handles_huge_integer_with_stable_error(self):
        prepared = synthetic_prepared(); prepared["scalars"]["n"] = {"value": 10 ** 309, "provenance": "huge.integer"}
        with self.assertRaises(ValueError) as raised: surface.build_cage(prepared)
        self.assertEqual(str(raised.exception), "scalars.n.value must be finite"); self.assertIsInstance(raised.exception.__cause__, OverflowError); self.assertEqual(surface._number(2, "ordinary"), 2.0)
        baseline = surface.build_cage(synthetic_prepared()); ordinary = synthetic_prepared(); ordinary["scalars"]["n"] = {"value": 2.6, "provenance": "ordinary.float"}
        self.assertEqual(baseline.vertices, surface.build_cage(ordinary).vertices)
    def test_unknown_names_fields_and_provenance_are_rejected(self):
        mutations = (("empty station provenance", lambda p: p["stations"]["neck_collar"].update(provenance="")), ("blank landmark provenance", lambda p: p["landmarks"]["axilla_left"].update(provenance=" \t\n")), ("empty frame provenance", lambda p: p["frames"]["body"].update(provenance="")), ("blank scalar provenance", lambda p: p["scalars"]["thigh_depth"].update(provenance=" \t\n")), ("top-level collection", lambda p: p.update(extra={})), ("frame name", lambda p: p["frames"].update(extra={})), ("landmark name", lambda p: p["landmarks"].update(extra={})), ("station name", lambda p: p["stations"].update(extra={})), ("scalar name", lambda p: p["scalars"].update(extra={})), ("source field", lambda p: p["source"].update(extra="rejected")), ("basis field", lambda p: p["basis"].update(extra="rejected")), ("frame field", lambda p: p["frames"]["body"].update(extra="rejected")), ("landmark field", lambda p: p["landmarks"]["axilla_left"].update(extra="rejected")), ("station field", lambda p: p["stations"]["neck_collar"].update(extra="rejected")), ("scalar field", lambda p: p["scalars"]["thigh_depth"].update(extra="rejected")))
        for kind, mutate in mutations:
            with self.subTest(kind=kind):
                prepared = synthetic_prepared(); mutate(prepared)
                with self.assertRaisesRegex(ValueError, "unknown or missing|requires provenance"): surface.build_cage(prepared)
    def test_named_boundaries_and_shoulder_offsets_use_canonical_sides(self):
        prepared = synthetic_prepared(); cage = surface.build_cage(prepared)
        lateral = np.array((1.0, 0.0, 0.0))
        forward = np.array((0.0, 0.0, 1.0))
        for side, sign, arm, thigh in (("left", -1, 56, 64), ("right", 1, 60, 68)):
            arm_centroid = np.mean(cage.vertices[arm:arm + 4], axis=0)
            thigh_centroid = np.mean(cage.vertices[thigh:thigh + 4], axis=0)
            self.assertGreater(sign * float(np.dot(arm_centroid, lateral)), 0.0)
            self.assertGreater(sign * float(np.dot(thigh_centroid, lateral)), 0.0)
            peak = np.asarray(prepared["landmarks"][f"shoulder_peak_{side}"]["point"])
            upper = np.mean(cage.vertices[arm:arm + 2], axis=0)
            self.assertGreater(sign * float(np.dot(upper - peak, lateral)), 0.0)
            cuff = np.asarray(cage.vertices[arm:arm + 4])
            local = np.column_stack((cuff @ lateral, cuff @ forward))
            area = 0.5 * sum(local[i, 0] * local[(i + 1) % 4, 1]
                             - local[(i + 1) % 4, 0] * local[i, 1]
                             for i in range(4))
            self.assertGreater(abs(area), 1e-12)
    def test_symmetric_pair_of_pants_routes_are_exact(self):
        _, faces, _ = surface.symbolic_topology()
        expected = []
        for path, cuff in (((50, 51, 52, 53, 54), (64, 65, 66, 67, 64)),
                           ((50, 49, 48, 55, 54), (68, 69, 70, 71, 68))):
            expected.extend((path[i], path[i + 1], cuff[i + 1], cuff[i])
                            for i in range(4))
        expected.append((50, 64, 54, 68))
        self.assertEqual(faces[-9:], tuple(expected[:4]) + tuple(tuple(reversed(face)) for face in expected[4:8]) + (expected[8],))
    def test_pelvic_routes_have_no_proper_front_projection_crossings(self):
        cage = surface.build_cage(synthetic_prepared())
        routes = ((50, 51), (51, 52), (52, 53), (53, 54),
                  (50, 49), (49, 48), (48, 55), (55, 54), (50, 54))
        projected = np.asarray(cage.vertices)[:, (0, 1)]
        def orientation(a, b, c):
            return ((b[0] - a[0]) * (c[1] - a[1])
                    - (b[1] - a[1]) * (c[0] - a[0]))

        def proper_crossing(a, b, c, d):
            ab = orientation(a, b, c) * orientation(a, b, d)
            cd = orientation(c, d, a) * orientation(c, d, b)
            return ab < 0 and cd < 0

        for index, (a, b) in enumerate(routes):
            for c, d in routes[index + 1:]:
                if {a, b} & {c, d}:
                    continue
                self.assertFalse(proper_crossing(projected[a], projected[b],
                                                 projected[c], projected[d]))

    def test_symmetric_fixture_is_mirror_equivalent_at_all_levels(self):
        prepared = synthetic_prepared(); prepared["scalars"]["saddle"] = {"value": 0.60, "provenance": "override.saddle"}
        result = surface.evaluate(prepared, levels=2)

        def assert_mirror(vertices):
            values = np.asarray(vertices, dtype=float)
            reflected = values.copy(); reflected[:, 0] *= -1
            remaining = list(reflected)
            for point in values:
                distances = np.max(np.abs(np.asarray(remaining) - point), axis=1)
                index = int(np.argmin(distances))
                self.assertLessEqual(distances[index], 1e-8)
                remaining.pop(index)

        for mesh in (result.cage, *result.levels):
            assert_mirror(mesh.vertices)

    def test_axial_envelope_and_axilla_transition_use_exact_interpolation(self):
        prepared = synthetic_prepared(); prepared["scalars"]["thigh_lateral_radius"]["value"] = 0.73; prepared["scalars"]["thigh_depth"]["value"] = 0.47; cage = surface.build_cage(prepared)
        keys = ("lateral_radius", "front_extent", "back_extent")
        anchors = [(prepared["stations"][name]["center"][1], tuple(
            prepared["stations"][name][key] for key in keys)) for name in
            ("upper_ribcage_shoulder", "waist_abdomen", "upper_pelvis")]
        seats = [np.asarray(prepared["landmarks"][f"thigh_start_{side}"]["point"]) +
                 surface.CONSTANTS["eta"] * (np.asarray(
                     prepared["landmarks"][f"thigh_mid_{side}"]["point"]) - np.asarray(
                         prepared["landmarks"][f"thigh_start_{side}"]["point"]))
                 for side in ("left", "right")]
        anchors.append((np.mean([seat[1] for seat in seats]),
                        (max(abs(seat[0]) for seat in seats) + prepared["scalars"]["thigh_lateral_radius"]["value"],
                         prepared["scalars"]["thigh_depth"]["value"], prepared["scalars"]["thigh_depth"]["value"])))

        def limited(name):
            station = prepared["stations"][name]; position = station["center"][1]
            high, low = next(pair for pair in zip(anchors, anchors[1:]) if pair[1][0] <= position <= pair[0][0])
            fraction = (position - low[0]) / (high[0] - low[0])
            bound = tuple(lo + fraction * (hi - lo) for hi, lo in zip(high[1], low[1]))
            return np.asarray(station["center"]), tuple(min(station[key], value) for key, value in zip(keys, bound))

        def cardinal(center, extents):
            radius, front, back = extents; middle = center + (0, 0, (front - back) / 2)
            return (middle + (radius, 0, 0), center + (0, 0, front),
                    middle - (radius, 0, 0), center - (0, 0, back))

        for name, start in (("lower_ribcage", 24), ("lower_pelvis", 48)):
            expected = cardinal(*limited(name))
            for index, point in zip((0, 2, 4, 6), expected):
                np.testing.assert_allclose(cage.vertices[start + index], point)
                self.assertEqual(cage.formula_ids[start + index], "station.axial_envelope.min_clamp")
        self.assertEqual(cage.formula_ids[10], "shoulder.superior_axial_saddle")
        self.assertEqual(set(cage.dependencies[10]), station_fields("upper_ribcage_shoulder") | {
            "stations.neck_collar.center", "frames.body", "scalars.n", "scalars.saddle"})
        upper = prepared["stations"]["upper_ribcage_shoulder"]; neck = prepared["stations"]["neck_collar"]
        expected = cardinal(np.asarray(upper["center"]), tuple(upper[key] for key in keys))[1]
        expected += surface.CONSTANTS["saddle"] * (neck["center"][1] - upper["center"][1]) * np.asarray((0.0, 1.0, 0.0))
        np.testing.assert_allclose(cage.vertices[10], expected)
        self.assertEqual(cage.provenance_ids[10], ("synthetic.station.upper_rib", "synthetic.station.neck",
                                                   "synthetic.frame.body", "formula_constant.n.v1", "formula_constant.saddle.v1"))
        self.assertEqual(cage.formula_ids[34], "station.asymmetric_superellipse")
        self.assertEqual(set(cage.dependencies[34]), station_fields("waist_abdomen") | {"frames.body", "scalars.n"})
        lower_center, lower_extents = limited("lower_abdomen"); upper = prepared["stations"]["upper_pelvis"]
        fraction = surface.CONSTANTS["lambda"]
        iliac = ((1 - fraction) * lower_center + fraction * np.asarray(upper["center"]), tuple(
            (1 - fraction) * lo + fraction * upper[key] for lo, key in zip(lower_extents, keys)))
        for index, point in zip((0, 2, 4, 6), cardinal(*iliac)):
            np.testing.assert_allclose(cage.vertices[40 + index], point)
        lower_center, lower_extents = limited("lower_ribcage"); upper_center, upper_extents = limited("upper_ribcage_shoulder")
        target = np.mean([prepared["landmarks"][f"axilla_{side}"]["point"][1] for side in ("left", "right")])
        fraction = (target - lower_center[1]) / (upper_center[1] - lower_center[1])
        transition = ((1 - fraction) * lower_center + fraction * upper_center, tuple(
            (1 - fraction) * lo + fraction * hi for lo, hi in zip(lower_extents, upper_extents)))
        for index, point in zip((2, 6), cardinal(*transition)[1::2]):
            np.testing.assert_allclose(cage.vertices[16 + index], point)
        exact = station_fields("lower_pelvis") | station_fields("upper_pelvis") | {
            f"landmarks.thigh_{point}_{side}" for side in ("left", "right") for point in ("start", "mid")}
        exact |= {"scalars.thigh_lateral_radius", "scalars.thigh_depth", "scalars.eta", "frames.body", "scalars.n"}
        self.assertEqual(set(cage.dependencies[50]), exact)
        provenance = "|".join(cage.provenance_ids[50]); self.assertTrue(all(item in provenance for item in (
            "synthetic.station.lower_pelvis",
            "synthetic.station.upper_pelvis", "synthetic.landmark.thigh_start_left",
            "synthetic.landmark.thigh_mid_right", "synthetic.scalar.thigh_lateral_radius",
            "synthetic.scalar.thigh_depth", "formula_constant.eta.v1", "synthetic.frame.body")))

        boundary = synthetic_prepared(); boundary["stations"]["lower_abdomen"]["center"] = boundary["stations"]["waist_abdomen"]["center"]
        boundary_cage = surface.build_cage(boundary); boundary_deps = "|".join(boundary_cage.dependencies[42])
        boundary_prov = "|".join(boundary_cage.provenance_ids[42]); self.assertEqual(("stations.waist_abdomen" in boundary_deps,
                          "stations.upper_ribcage_shoulder" in boundary_deps, "synthetic.station.upper_rib" in boundary_prov),
                         (True, False, False))
        authored = synthetic_prepared(); authored["stations"]["lower_ribcage"].update(dict(zip(keys, (1.0, 0.6, 0.5)))); authored_cage = surface.build_cage(authored)
        self.assertEqual((authored_cage.formula_ids[26], set(authored_cage.dependencies[26])),
                         ("station.asymmetric_superellipse", station_fields("lower_ribcage") | {"frames.body", "scalars.n"}))

        exact_anchor = synthetic_prepared(); exact_anchor["stations"]["lower_ribcage"].update(center=(0.11, 0.72, 0.07), lateral_radius=1.0, front_extent=0.60, back_extent=0.56); exact_dependencies = set(surface.build_cage(exact_anchor).dependencies[26]); self.assertIn("stations.waist_abdomen.lateral_radius", exact_dependencies); self.assertNotIn("stations.upper_ribcage_shoulder.lateral_radius", exact_dependencies)

    def test_shoulder_bridges_are_outward_and_each_quad_is_unfolded(self):
        cage = surface.build_cage(synthetic_prepared()); _, faces, _ = surface.symbolic_topology()
        vertices = np.asarray(cage.vertices)
        for side, sign, ring_segment, collar_start in (
                ("left", -1, 3, 56), ("right", 1, 0, 60)):
            ring = (8 + ring_segment, 8 + (ring_segment + 1) % 8,
                    16 + (ring_segment + 1) % 8, 16 + ring_segment)
            collar = set(range(collar_start, collar_start + 4))
            bridges = [face for face in faces if len(collar.intersection(face)) == 2
                       and len(set(face).intersection(ring)) == 2]
            self.assertEqual(len(bridges), 4)
            for face in bridges:
                cross_edges = [(face[i], face[(i + 1) % 4]) for i in range(4)
                               if (face[i] in collar) != (face[(i + 1) % 4] in collar)]
                self.assertEqual(len(cross_edges), 2)
                for a, b in cross_edges:
                    point = vertices[a] if a in collar else vertices[b]
                    other = vertices[b] if a in collar else vertices[a]
                    self.assertGreater(sign * (point[0] - other[0]), 0.0)
                def orientation(a, b, c):
                    return ((b[0] - a[0]) * (c[1] - a[1])
                            - (b[1] - a[1]) * (c[0] - a[0]))

                def proper_crossing(a, b, c, d):
                    return (orientation(a, b, c) * orientation(a, b, d) < 0
                            and orientation(c, d, a) * orientation(c, d, b) < 0)

                projections = [vertices[list(face)][:, axes]
                               for axes in ((0, 1), (0, 2), (1, 2))]
                def signed_area(projection):
                    return 0.5 * sum(projection[i, 0] * projection[(i + 1) % 4, 1]
                                     - projection[(i + 1) % 4, 0] * projection[i, 1]
                                     for i in range(4))
                projection = max(projections, key=lambda item: abs(signed_area(item)))
                area = signed_area(projection)
                self.assertGreater(abs(area), 1e-10)
                self.assertFalse(proper_crossing(projection[0], projection[1],
                                                 projection[2], projection[3]))
                self.assertFalse(proper_crossing(projection[1], projection[2],
                                                 projection[3], projection[0]))

    def test_shoulder_socket_coordinates_dependencies_and_lateral_bridges(self):
        prepared = synthetic_prepared(); cage = surface.build_cage(prepared)
        vertices = np.asarray(cage.vertices)
        lateral = np.asarray((1.0, 0.0, 0.0))
        up = np.asarray((0.0, 1.0, 0.0))
        forward = np.asarray((0.0, 0.0, 1.0))
        socket_sides = {}
        for side, sign, ring_segment, front_index, back_index in (
                ("left", -1, 3, 3, 4), ("right", 1, 0, 1, 0)):
            arm = prepared["scalars"]
            peak = np.asarray(prepared["landmarks"][f"shoulder_peak_{side}"]["point"])
            axilla = np.asarray(prepared["landmarks"][f"axilla_{side}"]["point"])
            sigma = surface.CONSTANTS["shoulder"]
            upper_center = axilla + sigma * (peak - axilla) + sign * sigma * arm["arm_root_outward"]["value"] * lateral
            lower_center = axilla + sign * surface.CONSTANTS["axilla"] * arm["arm_root_outward"]["value"] * lateral
            for ring_name, center, ring_start in (
                    ("upper_ribcage_shoulder", upper_center, 8),
                    ("axilla_transition", lower_center, 16)):
                if ring_name == "axilla_transition":
                    lower, upper = (prepared["stations"][name] for name in
                                    ("lower_ribcage", "upper_ribcage_shoulder"))
                    waist = prepared["stations"]["waist_abdomen"]
                    envelope_fraction = ((lower["center"][1] - waist["center"][1]) /
                                         (upper["center"][1] - waist["center"][1]))
                    limited = {key: min(lower[key], waist[key] + envelope_fraction *
                                   (upper[key] - waist[key])) for key in (
                                       "lateral_radius", "front_extent", "back_extent")}
                    t = (np.mean([prepared["landmarks"][f"axilla_{item}"]["point"][1]
                                  for item in ("left", "right")]) - lower["center"][1]) / (upper["center"][1] - lower["center"][1])
                    station = {"center": tuple((1 - t) * a + t * b for a, b in
                                                zip(lower["center"], upper["center"])),
                               **{key: (1 - t) * limited[key] + t * upper[key] for key in limited}}
                else:
                    station = prepared["stations"][ring_name]
                station_center = np.asarray(station["center"])
                anchor = station_center + ((station["front_extent"] - station["back_extent"]) / 2) * forward + sign * station["lateral_radius"] * lateral
                for index, depth_sign in ((front_index, 1), (back_index, -1)):
                    actual_index = ring_start + index
                    socket_sides[actual_index] = side
                    expected = (float(np.dot(anchor, lateral)) * lateral +
                                float(np.dot(center, up)) * up +
                                (float(np.dot(center, forward)) + depth_sign * arm["arm_root_depth"]["value"]) * forward)
                    np.testing.assert_allclose(vertices[actual_index], expected)
                    self.assertEqual(cage.formula_ids[actual_index], "shoulder.peak_axilla_collar")
                    if ring_name == "upper_ribcage_shoulder":
                        expected_dependencies = station_fields(ring_name) | {
                            f"landmarks.shoulder_peak_{side}", f"landmarks.axilla_{side}",
                            "scalars.arm_root_depth", "scalars.arm_root_outward",
                            "scalars.shoulder", "frames.body"}
                    else:
                        expected_dependencies = (station_fields("upper_ribcage_shoulder") |
                                                 station_fields("lower_ribcage") | station_fields("waist_abdomen"))
                        expected_dependencies.update(("landmarks.axilla_left", "landmarks.axilla_right",
                                                      "frames.body", f"landmarks.axilla_{side}",
                                                      "scalars.arm_root_depth", "scalars.arm_root_outward",
                                                      "scalars.axilla"))
                    self.assertEqual(set(cage.dependencies[actual_index]), expected_dependencies)
                    self.assertTrue(all(value for value in cage.provenance_ids[actual_index]))

        for index in socket_sides:
            self.assertIn("stations.", " ".join(cage.dependencies[index]))
        collar_indices = set(range(56, 64))
        edges = set()
        for face in cage.quads:
            for a, b in zip(face, face[1:] + face[:1]):
                if {a, b} <= socket_sides.keys() | collar_indices and ({a, b} & socket_sides.keys()) and ({a, b} & collar_indices):
                    edges.add(tuple(sorted((a, b))))
        self.assertEqual(len(edges), 8)
        directions = {"left": [], "right": []}
        for socket, collar in edges:
            delta = vertices[collar] - vertices[socket]
            np.testing.assert_allclose(np.dot(delta, up), 0.0, atol=1e-12)
            np.testing.assert_allclose(np.dot(delta, forward), 0.0, atol=1e-12)
            side = socket_sides[socket]
            sign = -1 if side == "left" else 1
            directions[side].append(sign * float(np.dot(delta, lateral)))
        self.assertEqual((len(directions["left"]), len(directions["right"])), (4, 4))
        for values in directions.values():
            self.assertTrue(all(value * values[0] > 0.0 for value in values))

    def test_profile_identity_is_not_an_input_path(self):
        for path, value in ((("profile_id",), "forbidden"),
                            (("stations", "neck_collar", "profile-id"), "also-forbidden")):
            prepared = synthetic_prepared(); target = prepared
            for key in path[:-1]:
                target = target[key]
            target[path[-1]] = value
            with self.assertRaisesRegex(ValueError, "profile identity"):
                surface.build_cage(prepared)
        self.assertRaisesRegex(ValueError, "profile identity", surface.evaluate, {**synthetic_prepared(), "profile_id": "forbidden"})

    def test_shared_formula_constants_have_local_expected_effects(self):
        baseline = surface.build_cage(synthetic_prepared())
        base_eval = surface.evaluate(synthetic_prepared(), levels=2)
        changed = synthetic_prepared(); changed["scalars"]["n"] = {"value": 3.1, "provenance": "synthetic.constant.n"}
        powered = surface.build_cage(changed)
        self.assertNotEqual(baseline.vertices[1], powered.vertices[1])
        self.assertEqual((baseline.vertices[0], baseline.vertices[56:]), (powered.vertices[0], powered.vertices[56:]))
        changed = synthetic_prepared(); changed["scalars"]["lambda"] = {"value": 0.5, "provenance": "synthetic.constant.lambda"}
        blended = surface.build_cage(changed)
        self.assertTrue(all(baseline.vertices[index] != blended.vertices[index] for index in range(40, 48)))
        self.assertEqual((baseline.vertices[:40], baseline.vertices[48:]), (blended.vertices[:40], blended.vertices[48:]))
        changed = synthetic_prepared(); changed["scalars"]["eta"] = {"value": 0.5, "provenance": "synthetic.constant.eta"}
        seated = surface.build_cage(changed)
        self.assertEqual((baseline.vertices[:48], baseline.vertices[56:64]), (seated.vertices[:48], seated.vertices[56:64]))
        for region in (slice(48, 56), slice(64, 68), slice(68, 72)): self.assertTrue(all(baseline.vertices[index] != seated.vertices[index] for index in range(region.start, region.stop)))
        for side, offset in (("left", 64), ("right", 68)):
            start = np.asarray(changed["landmarks"][f"thigh_start_{side}"]["point"], dtype=float)
            mid = np.asarray(changed["landmarks"][f"thigh_mid_{side}"]["point"], dtype=float)
            route = mid - start
            centroid = np.mean(np.asarray(seated.vertices[offset:offset + 4]), axis=0)
            expected = start + changed["scalars"]["eta"]["value"] * route
            np.testing.assert_allclose(centroid, expected)
            projection = float(np.dot(centroid - start, route)); self.assertGreater(projection, 0.0)
            self.assertAlmostEqual(projection / float(np.dot(route, route)), changed["scalars"]["eta"]["value"])
        changed = synthetic_prepared(); changed["stations"]["upper_pelvis"]["front_extent"] = 0.5; sourced = surface.build_cage(changed)
        self.assertEqual((baseline.vertices[:8], baseline.vertices[56:]), (sourced.vertices[:8], sourced.vertices[56:]))
        self.assertTrue(all(baseline.vertices[index] != sourced.vertices[index] for index in (42, 50)))
        for key, changed_slice, stable_slice in (
                ("shoulder", slice(56, 58), slice(58, 60)),
                ("axilla", slice(58, 60), slice(56, 58))):
            changed = synthetic_prepared()
            changed["scalars"][key] = {"value": surface.RANGES[key][1],
                                       "provenance": f"synthetic.constant.{key}"}
            collar = surface.build_cage(changed)
            self.assertTrue(all(baseline.vertices[index] != collar.vertices[index] for index in range(changed_slice.start, changed_slice.stop)))
            self.assertEqual(baseline.vertices[stable_slice], collar.vertices[stable_slice])

        axilla_u = synthetic_prepared()
        for side in ("left", "right"):
            point = list(axilla_u["landmarks"][f"axilla_{side}"]["point"]); point[1] += 0.12; axilla_u["landmarks"][f"axilla_{side}"]["point"] = tuple(point)
        moved = surface.build_cage(axilla_u); self.assertTrue(all(baseline.vertices[index] != moved.vertices[index] for a, b in ((16, 24), (58, 60), (62, 64)) for index in range(a, b)))
        self.assertEqual((baseline.vertices[24:32], tuple(baseline.vertices[i] for i in (10, 13, 14, 15))), (moved.vertices[24:32], tuple(moved.vertices[i] for i in (10, 13, 14, 15))))

        for key, value, expected_indices in (
                ("shoulder", 0.81, {8, 9, 11, 12, 56, 57, 60, 61}),
                ("saddle", 0.60, {10, 13, 14, 15})):
            changed = synthetic_prepared(); changed["scalars"][key] = {"value": value, "provenance": f"synthetic.constant.{key}"}
            candidate = surface.build_cage(changed)
            changed_indices = {i for i, (before, after) in enumerate(zip(baseline.vertices, candidate.vertices)) if before != after}
            self.assertEqual(changed_indices, expected_indices)
            self.assertEqual((baseline.quads, baseline.control_ids), (candidate.quads, candidate.control_ids))
            changed_eval = surface.evaluate(changed, levels=2)
            l1_inputs, l1_quads, l1_loops = independent_subdivision_stencils(baseline.quads, baseline.boundary_loops, len(baseline.vertices))
            l1_changed = {i for i, inputs in enumerate(l1_inputs) if inputs & changed_indices}
            l2_inputs, _, _ = independent_subdivision_stencils(l1_quads, l1_loops, len(base_eval.levels[0].vertices))
            expected = (l1_changed, {i for i, inputs in enumerate(l2_inputs) if inputs & l1_changed})
            for base, trial in zip(base_eval.levels, changed_eval.levels):
                self.assertEqual((base.quads, base.control_ids, base.formula_ids), (trial.quads, trial.control_ids, trial.formula_ids))
            for base, trial, affected in zip(base_eval.levels, changed_eval.levels, expected):
                actual = {i for i, (before, after) in enumerate(zip(base.vertices, trial.vertices)) if before != after}
                self.assertEqual(actual, affected); self.assertTrue(affected and set(range(len(base.vertices))) - affected)

        changed = synthetic_prepared(); changed["scalars"]["gamma"] = {"value": 0.12, "provenance": "synthetic.constant.gamma"}
        gapped = surface.build_cage(changed)
        self.assertTrue(all(baseline.vertices[index] != gapped.vertices[index] for index in (64, 68)))
        self.assertEqual((baseline.vertices[65:68], baseline.vertices[69:72]), (gapped.vertices[65:68], gapped.vertices[69:72]))

        overrides = synthetic_prepared()
        for key, value in (("n", 2.7), ("lambda", 0.3), ("shoulder", 0.81),
                           ("axilla", 0.56), ("eta", 0.3), ("gamma", 0.09), ("saddle", 0.50)):
            overrides["scalars"][key] = {"value": value, "provenance": f"override.{key}"}
        emitted = surface.build_cage(overrides)
        for index, key in ((0, "n"), (40, "lambda"), (64, "eta"), (64, "gamma"), (10, "saddle")):
            self.assertTrue(any(f"override.{key}" in item for item in emitted.provenance_ids[index]))
        self.assertIn("formula_constant.n.v1", baseline.provenance_ids[0])
        self.assertEqual(tuple(any(key in item for item in emitted.provenance_ids[index])
                               for index, key in ((8, "override.shoulder"), (8, "override.axilla"),
                                                  (16, "override.axilla"), (16, "override.shoulder"))),
                         (True, False, True, False))

    def test_forbidden_geometry_payload_keys_are_rejected_recursively(self):
        keys = ("vertices", "faces", "edges", "rings", "connectivity",
                "ordered perimeter samples", "point clouds", "fields", "masks",
                "silhouettes", "corrective offsets", "serialized old output")
        for key in keys:
            prepared = synthetic_prepared(); prepared["stations"]["waist_abdomen"][key] = None
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, "forbidden prepared geometry"):
                surface.build_cage(prepared)
        prepared = synthetic_prepared(); shared = []; shared.append(shared)
        prepared["source"]["document"] = shared; prepared["source"]["namespace"] = shared
        self.assertEqual(len(surface.build_cage(prepared).vertices), 72)
        prepared = synthetic_prepared(); shared = [{"vertices": None}]; shared.append(shared)
        prepared["source"]["document"] = shared; prepared["source"]["namespace"] = shared
        with self.assertRaisesRegex(ValueError, "forbidden prepared geometry"):
            surface.build_cage(prepared)

    def test_invalid_inputs_fail_closed(self):
        cases = ((lambda p: p["stations"].pop("neck_collar"), r"prepared\.stations has unknown or missing fields"), (lambda p: p["stations"]["waist_abdomen"].update(center=(0, np.nan, 0)), r"stations\.waist_abdomen\.center must be a finite 3-vector"), (lambda p: p["frames"]["body"].update(lateral_axis=(0, 0, 0)), "body frame axes must have finite positive norms"), (lambda p: p["frames"]["body"].update(lateral_axis=(np.finfo(float).max,) * 3), "body frame axes must have finite positive norms"), (lambda p: p["frames"]["body"].update(forward_axis=(0, 0, -1)), "body frame must be orthonormal and right-handed"), (lambda p: p["landmarks"]["thigh_mid_left"].update(point=p["landmarks"]["thigh_start_left"]["point"]), "thigh route left must have positive length"), (lambda p: p["landmarks"]["thigh_start_left"].update(point=(0.2, -0.7, 0)), "thigh medial radius left is non-positive"), (lambda p: [p["landmarks"][f"axilla_{side}"].update(point=(0, 1.55, 0)) for side in ("left", "right")], "axilla transition interpolation must have 0 < t < 1"), (lambda p: p["stations"]["neck_collar"].update(center=(0, 2.40, 0)), "neck must be above upper ribcage"))
        for index, (mutate, message) in enumerate(cases):
            with self.subTest(case=index):
                prepared = synthetic_prepared(); mutate(prepared)
                self.assertRaisesRegex(ValueError, message, surface.build_cage, prepared)
class SubdivisionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.prepared = synthetic_prepared(); cls.result = surface.evaluate(cls.prepared, levels=2)
    def test_open_boundaries_subdivide_and_euler_is_preserved(self):
        first, second = self.result.levels
        self.assertEqual((len(first.vertices), len(first.quads)), (273, 252))
        self.assertEqual((len(second.vertices), len(second.quads)), (1053, 1008))
        for level, multiplier in ((first, 2), (second, 4)):
            report = surface.validate_topology(len(level.vertices), level.quads, level.boundary_loops)
            self.assertEqual((report.euler, report.boundary_lengths, len(level.triangles)),
                             (-3, tuple(multiplier * n for n in (8, 4, 4, 4, 4)), 2 * len(level.quads)))
            surface.validate_geometry(level, evaluated=True)
        self.assertEqual(self.result.intersection_counts, (0, 0))
        self.assertEqual(tuple(name for name, _ in self.result.clearance_ratios),
                         ("neck", "axilla_left", "axilla_right", "groin", "medial_thigh"))
        self.assertTrue(all(value > mesh_correctness.CLEARANCE_THRESHOLDS[name]
                            for name, value in self.result.clearance_ratios))
    def test_final_level_clearance_gate_runs_at_requested_level(self):
        self.assertEqual(tuple(name for name, _ in surface.evaluate(self.prepared, levels=1).clearance_ratios), ("neck", "axilla_left", "axilla_right", "groin", "medial_thigh"))
    def test_evaluate_validates_each_produced_level_once(self):
        original = surface.validate_geometry; evaluated_meshes = []

        def counted(mesh, evaluated=False):
            if evaluated:
                evaluated_meshes.append(mesh)
            return original(mesh, evaluated=evaluated)

        with patch.object(surface, "validate_geometry", counted):
            result = surface.evaluate(self.prepared, levels=2)
        self.assertEqual(evaluated_meshes, list(result.levels))

    def test_correspondence_order_and_results_are_deterministic(self):
        repeated = surface.evaluate(synthetic_prepared(), levels=2)
        self.assertEqual(self.result, repeated)
        first = self.result.levels[0]
        self.assertTrue(all(name.startswith("L1.v.") for name in first.control_ids[:72]))
        self.assertTrue(all(name.startswith("L1.e.") for name in first.control_ids[72:210]))
        self.assertTrue(all(name.startswith("L1.f.") for name in first.control_ids[210:]))
        self.assertIn("catmull_clark.open_boundary_vertex", first.formula_ids)
        self.assertIn("catmull_clark.open_boundary_edge", first.formula_ids)
        self.assertTrue(all(dependency for dependency in first.dependencies))

    def test_invalid_level_is_rejected(self):
        for operation in (lambda: surface.subdivide(self.result.cage, 0),
                          lambda: surface.evaluate(self.prepared, levels=3)):
            with self.assertRaisesRegex(ValueError, "one or two"):
                operation()

    def test_normal_angle_fold_diagnostics_are_deterministic_and_explicit(self):
        diagnostics = build_root_complex.normal_angle_fold_diagnostics(self.result.levels)
        self.assertEqual(diagnostics, build_root_complex.normal_angle_fold_diagnostics(self.result.levels))
        self.assertEqual(diagnostics["schema"], "programmatic-root-complex.normal-angle-fold.v1")
        self.assertEqual(tuple(report["level"] for report in diagnostics["levels"]), (1, 2))
        for report in diagnostics["levels"]:
            self.assertGreater(report["interior_edge_count"], 0)
            self.assertLessEqual(report["interior_edge_count"], build_root_complex.MAX_NORMAL_ANGLE_DIAGNOSTIC_INTERIOR_EDGES)
            self.assertGreaterEqual(report["normal_angle_min_radians"], 0.0)
            self.assertLessEqual(report["normal_angle_max_radians"], math.pi)
            self.assertLessEqual(report["normal_angle_min_radians"], report["normal_angle_mean_radians"])
            self.assertLessEqual(report["normal_angle_mean_radians"], report["normal_angle_max_radians"])
            self.assertGreaterEqual(report["folded_edge_count"], 0)
            self.assertGreaterEqual(report["folded_edge_fraction"], 0.0)
            self.assertLessEqual(report["folded_edge_fraction"], 1.0)

    def test_normal_angle_fold_diagnostic_defines_fold_count(self):
        mesh = type("DiagnosticMesh", (), {
            "vertices": ((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (1.0, 1.0, 0.0),
                         (0.0, 1.0, 0.0), (0.0, 0.0, 1.0), (0.0, 1.0, 1.0)),
            "quads": ((0, 1, 2, 3), (2, 1, 4, 5)),
        })()
        report = build_root_complex.normal_angle_fold_diagnostics((mesh,))["levels"][0]
        self.assertEqual(report["interior_edge_count"], 1)
        self.assertAlmostEqual(report["normal_angle_min_radians"], 3.0 * math.pi / 4.0)
        self.assertEqual(report["folded_edge_count"], 1)
        self.assertEqual(report["folded_edge_fraction"], 1.0)

    def test_normal_angle_fold_diagnostics_are_invariant_to_cyclic_quad_rotation(self):
        vertices = ((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (1.0, 1.0, 0.0),
                    (0.0, 1.0, 0.0), (0.0, 0.0, 1.0), (0.0, 1.0, 1.0))
        faces = ((0, 1, 2, 3), (2, 1, 4, 5))
        def mesh(quads):
            return type("DiagnosticMesh", (), {"vertices": vertices, "quads": quads})()
        reference = build_root_complex.normal_angle_fold_diagnostics(
            (mesh(faces),))
        for face_index in range(2):
            for rotation in range(4):
                rotated = list(faces)
                face = rotated[face_index]
                rotated[face_index] = face[rotation:] + face[:rotation]
                candidate = mesh(tuple(rotated))
                self.assertEqual(
                    reference,
                    build_root_complex.normal_angle_fold_diagnostics((candidate,)),
                )
class BuildMetricsTests(unittest.TestCase):
    def test_published_metrics_include_evaluated_normal_angle_fold_diagnostics(self):
        source = ROOT.parents[1] / "examples/body-documents/stylized-digitigrade-biped-authored-form.json"
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "published"
            build_root_complex.build(source, output)
            metrics = json.loads((output / "metrics.json").read_text(encoding="utf-8"))
        diagnostics = metrics["normal_angle_fold_diagnostics"]
        self.assertEqual(diagnostics["schema"], "programmatic-root-complex.normal-angle-fold.v1")
        self.assertEqual([report["level"] for report in diagnostics["levels"]], [1, 2])
        self.assertTrue(all("folded_edge_count" in report for report in diagnostics["levels"]))
class MeshCorrectnessTests(unittest.TestCase):
    def assert_pairs(self, vertices, triangles, expected, scale=1.0):
        self.assertEqual(mesh_correctness.intersecting_triangle_pairs(vertices, triangles, scale), expected)
    def test_real_intersection_cases_and_adjacency_policy(self):
        base = ((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0))
        fan = ((0.0, 0.0, 0.0), (1.0, 1.0, 0.0), (1.0, -1.0, 0.0))
        delta = mesh_correctness.INTERSECTION_TOLERANCE / 2
        separate = ((0, 1, 2), (3, 4, 5))
        shared = ((0, 1, 2), (0, 3, 4))
        cases = (
            ("crossing", base, ((0.25, -0.25, -1.0), (0.25, 0.75, 1.0), (0.25, 0.75, -1.0)), separate, ((0, 1),)),
            ("coplanar overlap", base, ((0.25, 0.25, 0.0), (0.9, 0.1, 0.0), (0.1, 0.9, 0.0)), separate, ((0, 1),)),
            ("coplanar disjoint", base, ((2.0, 0.0, 0.0), (3.0, 0.0, 0.0), (2.0, 1.0, 0.0)), separate, ()),
            ("parallel separated", base, ((0.25, 0.25, 2.0), (0.9, 0.1, 2.0), (0.1, 0.9, 2.0)), separate, ()),
            ("near contact", base, ((0.25, 0.25, delta), (0.9, 0.1, delta), (0.1, 0.9, delta)), separate, ((0, 1),)),
            ("coincident", base, base, separate, ((0, 1),)),
            ("coplanar point fan", base, ((0.0, -1.0, 0.0), (-1.0, 0.0, 0.0)), shared, ()),
            ("shared edge", base, ((0.0, -1.0, 0.0),), ((0, 1, 2), (1, 0, 3)), ()),
            ("noncoplanar point fan", fan, ((-1.0, 0.0, 1.0), (-1.0, 0.0, -1.0)), shared, ()),
            ("sub-tolerance coplanar overlap", fan, ((delta, 0.0, 0.0), (-1.0, 0.25, 0.0)), shared, ((0, 1),)),
            ("sub-tolerance noncoplanar overlap", fan, ((delta, 0.0, -1.0), (-delta / 2, 0.0, 1.0)), shared, ((0, 1),)),
            ("near-degenerate axis", fan, ((-1.0, -1.0 + 1e-12, 1e-12), (-1.0, 1.0, 1e-12)), shared, ()),
        )
        for name, first, extra, faces, expected in cases:
            for scale, translation in ((1.0, (0.0, 0.0, 0.0)),
                                       (0.25, (17.25, -3.5, 41.0)),
                                       (2.5, (-12.5, 0.125, 8.75)),
                                       (1e-200, (1e5, -2e5, 3e5)),
                                       (1e200, (1e5, -2e5, 3e5))):
                with self.subTest(case=name, scale=scale, translation=translation):
                    points = np.asarray(first + extra, dtype=float) * scale
                    points += np.asarray(translation, dtype=float) * scale
                    self.assert_pairs(points, np.asarray(faces, dtype=np.int64), expected, scale)
        crossing = np.asarray(base + cases[0][2], dtype=float)
        with self.assertRaisesRegex(ValueError, r"first pair \(0, 1\)"):
            mesh_correctness.validate_triangle_intersections(crossing, np.asarray(separate, dtype=np.int64), 1.0)
        collinear = np.asarray(((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (2.0, 0.0, 0.0)))
        with self.assertRaisesRegex(ValueError, "triangle normal must be nonzero"):
            mesh_correctness.intersecting_triangle_pairs(collinear, np.asarray(((0, 1, 2),), dtype=np.int64), 1.0)
        tiny_normal = np.asarray(((0.0, 0.0, 0.0), (5e-324, 0.0, 0.0), (0.0, 1.0, 0.0)))
        with self.assertRaisesRegex(ValueError, "triangle normal must be nonzero"):
            mesh_correctness.intersecting_triangle_pairs(tiny_normal, np.asarray(((0, 1, 2),), dtype=np.int64), 1.0)
        separated = np.asarray((*collinear, (10.0, 0.0, 0.0), (10.0, 1.0, 0.0), (10.0, 0.0, 1.0)))
        with self.assertRaisesRegex(ValueError, "triangle normal must be nonzero"):
            mesh_correctness.validate_triangle_intersections(separated, np.asarray(((0, 1, 2), (3, 4, 5)), dtype=np.int64), 1.0)
        tiny = 2e-6 * np.asarray(
            base + ((1.5, 1.5, 0.0), (2.5, 1.5, 0.0), (1.5, 2.5, 0.0)))
        self.assert_pairs(tiny, np.asarray(separate, dtype=np.int64), ())
        noncoplanar = 2e-6 * np.asarray(
            ((1.0, 1.0, 1.0), (2.0, -2.0, -2.0), (-2.0, -2.0, -2.0),
             (-1.0, 0.0, 0.0), (1.0, 2.0, 2.0), (2.0, 2.0, 2.0)))
        self.assert_pairs(noncoplanar, np.asarray(separate, dtype=np.int64), ())
    def test_intersection_resource_caps_fail_closed(self):
        self.assertEqual((mesh_correctness.MAX_TRIANGLES, len(mesh_correctness._triangles(np.tile((0, 1, 2), (mesh_correctness.MAX_TRIANGLES, 1)), 3))), (3072, 3072))
        with self.assertRaisesRegex(ValueError, "triangle cap"):
            mesh_correctness.intersecting_triangle_pairs(
                np.zeros((3, 3)),
                np.zeros((mesh_correctness.MAX_TRIANGLES + 1, 3), dtype=np.int64), 1.0)
        old_cap = mesh_correctness.MAX_CANDIDATES
        try:
            mesh_correctness.MAX_CANDIDATES = 0
            crossing = np.asarray((
                (0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0),
                (0.25, -0.25, -1.0), (0.25, 0.75, 1.0), (0.25, 0.75, -1.0)),
                dtype=float)
            with self.assertRaisesRegex(ValueError, "candidate cap"):
                mesh_correctness.intersecting_triangle_pairs(
                    crossing, np.asarray(((0, 1, 2), (3, 4, 5)), dtype=np.int64), 1.0)
        finally:
            mesh_correctness.MAX_CANDIDATES = old_cap
    def test_boundary_clearances_are_rotation_invariant_and_reject_each_collapse(self):
        result = surface.evaluate(synthetic_prepared(), levels=2); mesh = result.levels[-1]
        vertices = np.asarray(mesh.vertices, dtype=float); loops = dict(mesh.boundary_loops)
        axes = {"L": (1.0, 0.0, 0.0), "U": (0.0, 1.0, 0.0), "F": (0.0, 0.0, 1.0)}; scale = surface.validate_geometry(mesh, evaluated=True)
        baseline = mesh_correctness.boundary_clearance_ratios(vertices, loops, axes, scale)
        left, right = loops["left_thigh"], loops["right_thigh"]
        lateral = np.asarray(axes["L"]); points = vertices / scale; left_lateral = points[list(left)] @ lateral; right_lateral = points[list(right)] @ lateral; medial_gap = float(right_lateral.min() - left_lateral.max()); groin_right = right[int(np.argmin(right_lateral))]; groin_left = left[int(np.argmax(left_lateral))]
        self.assertGreater(medial_gap, 0.0); self.assertAlmostEqual(baseline["groin"], medial_gap, delta=1e-12)
        for left_shift, right_shift in ((i, j) for i in range(len(left)) for j in range(len(right))):
            rotated = dict(loops); rotated["left_thigh"] = left[left_shift:] + left[:left_shift]; rotated["right_thigh"] = right[right_shift:] + right[:right_shift]
            self.assertEqual(mesh_correctness.boundary_clearance_ratios(vertices, rotated, axes, scale), baseline)
        for name in ("neck", "axilla_left", "axilla_right", "groin", "medial_thigh"):
            collapsed = vertices.copy()
            if name in ("neck", "axilla_left", "axilla_right"):
                loop_name = {"neck": "neck", "axilla_left": "left_arm", "axilla_right": "right_arm"}[name]; indices = loops[loop_name]; collapsed[list(indices)] = collapsed[indices[0]]
            elif name == "groin":
                collapsed[groin_right, 0] = collapsed[groin_left, 0]
            else:
                collapsed[groin_right, 0] = collapsed[groin_left, 0] + 0.022 * scale
            with self.subTest(gate=name), self.assertRaisesRegex(ValueError, name):
                mesh_correctness.validate_boundary_clearances(collapsed, loops, axes, scale)
        with patch.object(mesh_correctness, "MAX_BOUNDARY_CLEARANCE_PAIRS", 9):
            minimal = dict(loops); minimal["left_thigh"] = left[:3]; minimal["right_thigh"] = right[:3]; exact = mesh_correctness.boundary_clearance_ratios(vertices, minimal, axes, scale)
            expected = min(float((points[r] - points[l]) @ lateral) for l in minimal["left_thigh"] for r in minimal["right_thigh"]); self.assertEqual(exact["medial_thigh"], expected); over = dict(minimal); over["right_thigh"] = right[:4]
            with self.assertRaisesRegex(ValueError, r"boundary clearance pair cap exceeded: 12 > 9"): mesh_correctness.boundary_clearance_ratios(vertices, over, axes, scale)
    def test_subdivide_rejects_malformed_mesh_before_boundary_indexing(self):
        mesh = surface.Mesh(tuple((float(i), 0.0, 0.0) for i in range(8)),
                            ((0, 1, 2, 3), (0, 1, 4, 3), (0, 1, 6, 7)),
                            tuple(f"c{i}" for i in range(8)), ("f",) * 8,
                            (("d",),) * 8, (("p",),) * 8, ())
        valid = surface.subdivide(surface.build_cage(synthetic_prepared()))
        self.assertEqual((len(valid.vertices), len(valid.quads)), (273, 252))
        with self.assertRaisesRegex(ValueError, "non-manifold edge"):
            surface.subdivide(mesh)
        with patch.object(surface, "validate_topology", return_value=None):
            with self.assertRaisesRegex(ValueError, "exactly two boundary neighbors"):
                surface.subdivide(mesh)
class ComplexityBoundaryTests(unittest.TestCase):
    def test_exact_python_inventory_and_physical_line_caps(self):
        production_names = ("build_root_complex.py", "mesh_correctness.py", "prepared_projection.py",
                            "render_export.py", "root_complex_surface.py")
        test_names = ("test_prepared_projection.py", "test_render_export.py", "test_root_complex_surface.py")
        expected_paths = tuple(sorted(production_names + tuple(f"tests/{name}" for name in test_names)))
        actual_paths = tuple(sorted(path.relative_to(ROOT).as_posix() for path in ROOT.rglob("*.py") if path.is_file()))
        self.assertEqual(actual_paths, expected_paths, "unexpected, missing, or additional Python files")
        self.assertEqual(len(actual_paths), 8)
        def physical_lines(paths):
            total = 0
            for path in paths:
                with path.open(encoding="utf-8") as handle:
                    total += sum(1 for _ in handle)
            return total
        production = tuple(ROOT / name for name in production_names)
        tests = tuple(ROOT / "tests" / name for name in test_names)
        self.assertLessEqual(physical_lines(production), 1250)
        self.assertLessEqual(physical_lines(tests), 1050)
        self.assertLessEqual(physical_lines((ROOT / "mesh_correctness.py",)), 220)
if __name__ == "__main__":
    unittest.main()
