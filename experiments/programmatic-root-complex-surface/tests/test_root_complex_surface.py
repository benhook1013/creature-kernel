from __future__ import annotations

from copy import deepcopy
from dataclasses import FrozenInstanceError
from pathlib import Path
import sys
import unittest

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import root_complex_surface as surface  # noqa: E402
import mesh_correctness  # noqa: E402


def synthetic_prepared():
    def station(center, radius, front, back, name):
        return {
            "center": center,
            "lateral_radius": radius,
            "front_extent": front,
            "back_extent": back,
            "provenance": f"synthetic.station.{name}",
        }

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
        landmarks[f"shoulder_peak_{side}"] = landmark(
            (sign * 1.38, 2.55, 0.0), f"shoulder_peak_{side}")
        landmarks[f"axilla_{side}"] = landmark(
            (sign * 1.25, 1.76, 0.0), f"axilla_{side}")
        landmarks[f"thigh_start_{side}"] = landmark(
            (sign * 0.78, -0.70, 0.0), f"thigh_start_{side}")
        landmarks[f"thigh_mid_{side}"] = landmark(
            (sign * 0.82, -1.85, 0.03), f"thigh_mid_{side}")
    return {
        "source": {"document": "synthetic_root_complex", "namespace": "synthetic", "sha256": "synthetic-source", "provenance": "synthetic.source"},
        "basis": {"length_unit": "metre", "handedness": "right", "up": "+y", "forward": "+z"},
        "stations": stations,
        "landmarks": landmarks,
        "frames": {"body": {
            "lateral_axis": (1.0, 0.0, 0.0),
            "up_axis": (0.0, 1.0, 0.0),
            "forward_axis": (0.0, 0.0, 1.0),
            "provenance": "synthetic.frame.body",
        }},
        "scalars": {
            "arm_root_depth": scalar(0.34, "arm_root_depth"),
            "arm_root_outward": scalar(0.22, "arm_root_outward"),
            "thigh_lateral_radius": scalar(0.70, "thigh_lateral_radius"),
            "thigh_depth": scalar(0.42, "thigh_depth"),
        },
    }


def independent_subdivision_stencils(quads, loops, vertex_count):
    uses = {}
    for face_index, face in enumerate(quads):
        for a, b in zip(face, face[1:] + face[:1]):
            uses.setdefault(tuple(sorted((a, b))), []).append(face_index)
    boundary, incident = {}, {}
    for edge, face_indices in uses.items():
        for vertex in edge:
            incident.setdefault(vertex, []).extend(face_indices)
        if len(face_indices) == 1:
            boundary.setdefault(edge[0], []).append(edge[1])
            boundary.setdefault(edge[1], []).append(edge[0])
    sources = []
    for vertex in range(vertex_count):
        sources.append({vertex, *boundary[vertex]} if vertex in boundary else
                       {v for fi in incident[vertex] for v in quads[fi]})
    edges = tuple(sorted(uses))
    for edge in edges:
        source = set(edge) | ({v for fi in uses[edge] for v in quads[fi]}
                               if len(uses[edge]) == 2 else set())
        sources.append(source)
    sources.extend(set(face) for face in quads)
    edge_index = {edge: vertex_count + i for i, edge in enumerate(edges)}
    face_index = {fi: vertex_count + len(edges) + fi for fi in range(len(quads))}
    next_quads = tuple((vertex, edge_index[tuple(sorted((vertex, face[(i + 1) % 4])))], face_index[fi], edge_index[tuple(sorted((face[i - 1], vertex)))]) for fi, face in enumerate(quads) for i, vertex in enumerate(face))
    next_loops = tuple((name, tuple(value for i, vertex in enumerate(loop) for value in (vertex, edge_index[tuple(sorted((vertex, loop[(i + 1) % len(loop)]))) ]))) for name, loop in loops)
    return tuple(sources), next_quads, next_loops


class SymbolicTopologyTests(unittest.TestCase):
    def test_exact_counts_loops_euler_orientation_and_valences(self):
        ids, quads, loops = surface.symbolic_topology()
        report = surface.validate_topology(len(ids), quads, loops, surface.EXPECTED_VALENCES)
        self.assertEqual(surface.RING_NAMES, (
            "neck_collar", "upper_ribcage_shoulder", "axilla_transition",
            "lower_ribcage", "waist_abdomen", "iliac_overlap", "lower_pelvis"))
        self.assertEqual((report.vertex_count, report.edge_count, report.face_count), (72, 138, 63))
        self.assertEqual(report.boundary_edge_count, 24)
        self.assertEqual(report.boundary_lengths, (8, 4, 4, 4, 4))
        self.assertEqual(report.euler, -3)
        self.assertEqual(report.valence_inventory, ((3, 22), (4, 40), (5, 10)))
        self.assertEqual(loops, (("neck", (0, 1, 2, 3, 4, 5, 6, 7)),
                                 ("left_arm", (56, 59, 58, 57)),
                                 ("right_arm", (60, 63, 62, 61)),
                                 ("left_thigh", (64, 67, 66, 65)),
                                 ("right_thigh", (68, 69, 70, 71))))
        self.assertEqual(ids[16:24], tuple(f"ring.axilla_transition.{i}" for i in range(8)))
        self.assertEqual(ids[56:64], tuple(
            f"shoulder.{side}.{i}" for side in ("left", "right") for i in range(4)))
        self.assertEqual(ids[64:72], tuple(
            f"thigh.{side}.{i}" for side in ("left", "right") for i in range(4)))
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
        reversed_loop = list(loops)
        reversed_loop[1] = ("left_arm", tuple(reversed(loops[1][1])))
        with self.assertRaisesRegex(ValueError, "directed winding"):
            surface.validate_topology(len(ids), quads, tuple(reversed_loop))


class FormulaAndInputTests(unittest.TestCase):
    def test_plain_mapping_build_has_complete_immutable_records(self):
        cage = surface.build_cage(synthetic_prepared())
        self.assertEqual((len(cage.vertices), len(cage.quads)), (72, 63))
        self.assertEqual(len(set(cage.control_ids)), 72)
        self.assertEqual(len(cage.formula_ids), 72)
        self.assertTrue(all(item for item in cage.dependencies))
        self.assertTrue(all(item for item in cage.provenance_ids))
        self.assertEqual(set(cage.formula_ids), {
            "station.asymmetric_superellipse", "iliac.blend.superellipse",
            "shoulder.axilla_transition", "shoulder.peak_axilla_collar",
            "shoulder.superior_axial_saddle", "station.axial_envelope.min_clamp",
            "thigh.seat_gap_loop",
        })
        with self.assertRaises(FrozenInstanceError):
            cage.vertices = ()

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
        self.assertEqual({frozenset(face) for face in faces[-9:]},
                         {frozenset(face) for face in expected})

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
        prepared = synthetic_prepared(); cage = surface.build_cage(prepared)
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
                        (max(abs(seat[0]) for seat in seats) + 0.70, 0.42, 0.42)))

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
        station_fields = lambda name: {f"stations.{name}.{key}" for key in ("center", *keys)}
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
                    self.assertNotEqual(sign * (other[0] - point[0]), 0.0)
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
        socket_indices = set()
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
                    socket_indices.add(actual_index)
                    expected = (float(np.dot(anchor, lateral)) * lateral +
                                float(np.dot(center, up)) * up +
                                (float(np.dot(center, forward)) + depth_sign * arm["arm_root_depth"]["value"]) * forward)
                    np.testing.assert_allclose(vertices[actual_index], expected)
                    self.assertEqual(cage.formula_ids[actual_index], "shoulder.peak_axilla_collar")
                    station_fields = lambda name: {f"stations.{name}.{key}" for key in
                                                   ("center", "lateral_radius", "front_extent", "back_extent")}
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

        for index in socket_indices:
            self.assertIn("stations.", " ".join(cage.dependencies[index]))
        collar_indices = set(range(56, 64))
        edges = set()
        for face in cage.quads:
            for a, b in zip(face, face[1:] + face[:1]):
                if {a, b} <= socket_indices | collar_indices and ({a, b} & socket_indices) and ({a, b} & collar_indices):
                    edges.add(tuple(sorted((a, b))))
        self.assertEqual(len(edges), 8)
        directions = {"left": [], "right": []}
        for socket, collar in edges:
            delta = vertices[collar] - vertices[socket]
            np.testing.assert_allclose(np.dot(delta, up), 0.0, atol=1e-12)
            np.testing.assert_allclose(np.dot(delta, forward), 0.0, atol=1e-12)
            side = "left" if socket in {11, 12, 19, 20} else "right"
            sign = -1 if side == "left" else 1
            directions[side].append(sign * float(np.dot(delta, lateral)))
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
        self.assertNotIn("profile", surface.build_cage.__code__.co_varnames)

    def test_shared_formula_constants_have_local_expected_effects(self):
        baseline = surface.build_cage(synthetic_prepared())
        changed = synthetic_prepared(); changed["scalars"]["n"] = {"value": 3.1, "provenance": "synthetic.constant.n"}
        powered = surface.build_cage(changed)
        self.assertNotEqual(baseline.vertices[1], powered.vertices[1])
        self.assertEqual((baseline.vertices[0], baseline.vertices[56:]),
                         (powered.vertices[0], powered.vertices[56:]))

        changed = synthetic_prepared(); changed["scalars"]["lambda"] = {"value": 0.5, "provenance": "synthetic.constant.lambda"}
        blended = surface.build_cage(changed)
        self.assertNotEqual(baseline.vertices[40:48], blended.vertices[40:48])
        self.assertEqual((baseline.vertices[:40], baseline.vertices[48:]),
                         (blended.vertices[:40], blended.vertices[48:]))

        changed = synthetic_prepared(); changed["scalars"]["eta"] = {"value": 0.5, "provenance": "synthetic.constant.eta"}
        seated = surface.build_cage(changed)
        self.assertEqual((baseline.vertices[:48], baseline.vertices[56:64]),
                         (seated.vertices[:48], seated.vertices[56:64]))
        self.assertNotEqual((baseline.vertices[48:56], baseline.vertices[64:]),
                            (seated.vertices[48:56], seated.vertices[64:]))
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
        self.assertEqual((baseline.vertices[:8], baseline.vertices[56:]),
                         (sourced.vertices[:8], sourced.vertices[56:]))
        self.assertNotEqual((baseline.vertices[42], baseline.vertices[50]), (sourced.vertices[42], sourced.vertices[50]))

        for key, changed_slice, stable_slice in (
                ("shoulder", slice(56, 58), slice(58, 60)),
                ("axilla", slice(58, 60), slice(56, 58))):
            changed = synthetic_prepared()
            changed["scalars"][key] = {"value": surface.RANGES[key][1],
                                       "provenance": f"synthetic.constant.{key}"}
            collar = surface.build_cage(changed)
            self.assertNotEqual(baseline.vertices[changed_slice], collar.vertices[changed_slice])
            self.assertEqual(baseline.vertices[stable_slice], collar.vertices[stable_slice])

        axilla_u = synthetic_prepared()
        for side in ("left", "right"):
            point = list(axilla_u["landmarks"][f"axilla_{side}"]["point"]); point[1] += 0.12; axilla_u["landmarks"][f"axilla_{side}"]["point"] = tuple(point)
        moved = surface.build_cage(axilla_u); self.assertTrue(all(baseline.vertices[a:b] != moved.vertices[a:b] for a, b in ((16, 24), (58, 60), (62, 64))))
        self.assertEqual((baseline.vertices[24:32], tuple(baseline.vertices[i] for i in (10, 13, 14, 15))), (moved.vertices[24:32], tuple(moved.vertices[i] for i in (10, 13, 14, 15))))

        for key, value, expected_indices in (
                ("shoulder", 0.81, {8, 9, 11, 12, 56, 57, 60, 61}),
                ("saddle", 0.60, {10, 13, 14, 15})):
            changed = synthetic_prepared(); changed["scalars"][key] = {"value": value, "provenance": f"synthetic.constant.{key}"}
            candidate = surface.build_cage(changed)
            changed_indices = {i for i, (before, after) in enumerate(zip(baseline.vertices, candidate.vertices)) if before != after}
            self.assertEqual(changed_indices, expected_indices)
            self.assertEqual((baseline.quads, baseline.control_ids), (candidate.quads, candidate.control_ids))
            base_eval = surface.evaluate(synthetic_prepared(), levels=2); changed_eval = surface.evaluate(changed, levels=2)
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
        self.assertNotEqual((baseline.vertices[64], baseline.vertices[68]),
                            (gapped.vertices[64], gapped.vertices[68]))
        self.assertEqual((baseline.vertices[65:68], baseline.vertices[69:72]),
                         (gapped.vertices[65:68], gapped.vertices[69:72]))

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

    def test_invalid_inputs_fail_closed(self):
        mutations = (lambda p: p["stations"].pop("neck_collar"), lambda p: p["stations"]["waist_abdomen"].update(center=(0, np.nan, 0)), lambda p: p["frames"]["body"].update(forward_axis=(0, 0, -1)), lambda p: p["landmarks"]["thigh_mid_left"].update(point=p["landmarks"]["thigh_start_left"]["point"]), lambda p: p["landmarks"]["thigh_start_left"].update(point=(0.2, -0.7, 0)), lambda p: [p["landmarks"][f"axilla_{side}"].update(point=(0, 1.55, 0)) for side in ("left", "right")], lambda p: p["stations"]["neck_collar"].update(center=(0, 2.40, 0)))
        for index, mutate in enumerate(mutations):
            with self.subTest(case=index):
                prepared = synthetic_prepared(); mutate(prepared)
                with self.assertRaises(ValueError): surface.build_cage(prepared)


class SubdivisionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.prepared = synthetic_prepared()
        cls.result = surface.evaluate(cls.prepared, levels=2)

    def test_open_boundaries_subdivide_and_euler_is_preserved(self):
        first, second = self.result.levels
        self.assertEqual((len(first.vertices), len(first.quads)), (273, 252))
        self.assertEqual((len(second.vertices), len(second.quads)), (1053, 1008))
        for level, multiplier in ((first, 2), (second, 4)):
            report = surface.validate_topology(len(level.vertices), level.quads, level.boundary_loops)
            self.assertEqual(report.euler, -3)
            self.assertEqual(report.boundary_lengths, tuple(multiplier * n for n in (8, 4, 4, 4, 4)))
            self.assertEqual(len(level.triangles), 2 * len(level.quads))
            surface.validate_geometry(level, evaluated=True)
        self.assertEqual(self.result.intersection_counts, (0, 0))
        self.assertEqual(tuple(name for name, _ in self.result.clearance_ratios),
                         ("neck", "axilla_left", "axilla_right", "groin", "medial_thigh"))
        self.assertTrue(all(value > threshold for (_, value), threshold in zip(
            self.result.clearance_ratios, (0.030, 0.025, 0.025, 0.020, 0.025))))

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


class MeshCorrectnessTests(unittest.TestCase):
    def assert_pairs(self, vertices, triangles, expected):
        self.assertEqual(mesh_correctness.intersecting_triangle_pairs(vertices, triangles, 1.0), expected)

    def test_real_intersection_cases_and_adjacency_policy(self):
        crossing = np.asarray((
            (0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0),
            (0.25, -0.25, -1.0), (0.25, 0.75, 1.0), (0.25, 0.75, -1.0)),
            dtype=float)
        triangles = np.asarray(((0, 1, 2), (3, 4, 5)), dtype=np.int64)
        self.assert_pairs(crossing, triangles, ((0, 1),))
        with self.assertRaisesRegex(ValueError, "first pair \(0, 1\)"):
            mesh_correctness.validate_triangle_intersections(crossing, triangles, 1.0)

        coplanar_overlap = np.vstack((
            crossing[:3], ((0.25, 0.25, 0.0), (0.9, 0.1, 0.0), (0.1, 0.9, 0.0))))
        self.assert_pairs(coplanar_overlap, triangles, ((0, 1),))
        coplanar_disjoint = np.vstack((
            crossing[:3], ((2.0, 0.0, 0.0), (3.0, 0.0, 0.0), (2.0, 1.0, 0.0))))
        self.assert_pairs(coplanar_disjoint, triangles, ())
        separated = coplanar_overlap.copy(); separated[3:, 2] = 2.0
        self.assert_pairs(separated, triangles, ())
        near = coplanar_overlap.copy(); near[3:, 2] = mesh_correctness.INTERSECTION_TOLERANCE / 2
        self.assert_pairs(near, triangles, ((0, 1),))

        shared = np.asarray(((0.0, 0.0, 0.0), (1.0, 0.0, 0.0),
                             (0.0, 1.0, 0.0), (0.0, -1.0, 0.0),
                             (-1.0, 0.0, 0.0)), dtype=float)
        self.assert_pairs(shared, np.asarray(((0, 1, 2), (0, 3, 4)), dtype=np.int64), ())
        coincident = np.vstack((crossing[:3], crossing[:3]))
        self.assert_pairs(coincident, triangles, ((0, 1),))

    def test_intersection_resource_caps_fail_closed(self):
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

    def test_each_named_clearance_gate_rejects_independent_collapse(self):
        result = surface.evaluate(synthetic_prepared(), levels=2)
        mesh = result.levels[-1]
        vertices = np.asarray(mesh.vertices, dtype=float)
        loops = dict(mesh.boundary_loops)
        axes = {"L": (1.0, 0.0, 0.0), "U": (0.0, 1.0, 0.0), "F": (0.0, 0.0, 1.0)}
        scale = surface.validate_geometry(mesh, evaluated=True)
        for name in ("neck", "axilla_left", "axilla_right", "groin", "medial_thigh"):
            collapsed = vertices.copy()
            if name in ("neck", "axilla_left", "axilla_right"):
                loop_name = {"neck": "neck", "axilla_left": "left_arm", "axilla_right": "right_arm"}[name]
                indices = loops[loop_name]
                collapsed[list(indices)] = collapsed[indices[0]]
            elif name == "groin":
                collapsed[loops["right_thigh"][0], 0] = collapsed[loops["left_thigh"][0], 0]
            else:
                left, right = loops["left_thigh"], loops["right_thigh"]
                collapsed[right[1], 0] = collapsed[left[1], 0] + 0.001
            with self.subTest(gate=name):
                with self.assertRaisesRegex(ValueError, name):
                    mesh_correctness.validate_boundary_clearances(
                        collapsed, loops, axes, scale)


if __name__ == "__main__":
    unittest.main()
