"""Independent, fail-closed checks for exported hip-articulation poses."""

from __future__ import annotations

import importlib.util
import math
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence


_OLD_CHECKS = Path("/home/ben/.cache/creature-kernel/pelvis-thigh-transition/attempt-2-snapshot/source/experiments/pelvis-thigh-transition/checks.py")
_JOINTS = ("pelvis", "left_hip", "right_hip")
_EXAMPLE_CAP = 8


def _vsub(a, b): return tuple(float(a[i]) - float(b[i]) for i in range(3))
def _vadd(a, b): return tuple(float(a[i]) + float(b[i]) for i in range(3))
def _vmul(a, s): return tuple(float(x) * float(s) for x in a)
def _dot(a, b): return sum(float(a[i]) * float(b[i]) for i in range(3))
def _cross(a, b): return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])
def _norm(a): return math.sqrt(_dot(a, a))
def _distance(a, b): return _norm(_vsub(a, b))


def _mat(value: Any, label: str) -> list[list[float]]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise ValueError(f"{label} must be a 4x4 matrix")
    if len(value) == 16:
        rows = [value[i:i + 4] for i in range(0, 16, 4)]
    else:
        rows = value
    if len(rows) != 4 or any(not isinstance(r, Sequence) or len(r) != 4 for r in rows):
        raise ValueError(f"{label} must be a 4x4 matrix")
    out = [[float(x) for x in row] for row in rows]
    if not all(math.isfinite(x) for row in out for x in row):
        raise ValueError(f"{label} is not finite")
    return out


def _mm(a, b): return [[sum(a[r][k]*b[k][c] for k in range(4)) for c in range(4)] for r in range(4)]
def _mp(m, p):
    q = [float(p[0]), float(p[1]), float(p[2]), 1.0]
    return tuple(sum(m[r][c]*q[c] for c in range(4)) for r in range(3))
def _identity_error(m): return max(abs(m[r][c] - (1.0 if r == c else 0.0)) for r in range(4) for c in range(4))


def _rigid_inverse(m):
    out = [[m[c][r] if r < 3 and c < 3 else 0.0 for c in range(4)] for r in range(4)]
    out[3][3] = 1.0
    for r in range(3): out[r][3] = -sum(out[r][c]*m[c][3] for c in range(3))
    return out


def _landmark(data: Mapping[str, Any], side: str, name: str) -> tuple[float, float, float]:
    value = None
    if isinstance(data.get(side), Mapping): value = data[side].get(name)
    if value is None and isinstance(data.get(name), Mapping): value = data[name].get(side)
    if value is None: value = data.get(f"{side}_{name}")
    if not isinstance(value, Sequence) or len(value) != 3:
        raise ValueError(f"missing reference landmark {side}.{name}")
    point = tuple(float(x) for x in value)
    if not all(math.isfinite(x) for x in point): raise ValueError(f"non-finite reference landmark {side}.{name}")
    return point


def _references(case, refs):
    if isinstance(refs.get("left"), Mapping): return dict(refs)
    attachments = case.get("attachments", {}) if isinstance(case, Mapping) else {}
    result = {}
    for side in ("left", "right"):
        row = attachments.get(side, {}) if isinstance(attachments, Mapping) else {}
        result[side] = {"J": refs.get(f"joint_{side}"), "T": row.get("centre"), "K": row.get("knee")}
    crests = [refs.get("crest_left"), refs.get("crest_right")]
    if all(isinstance(p, Sequence) and len(p) == 3 for p in crests): result["crest_y"] = max(float(p[1]) for p in crests)
    return result


def _frame(j, k):
    y0 = _vsub(j, k); yn = _norm(y0)
    if yn == 0.0: raise ValueError("J and K coincide")
    y = _vmul(y0, 1.0/yn)
    xp = _vsub((1.0, 0.0, 0.0), _vmul(y, y[0])); xn = _norm(xp)
    if xn == 0.0: raise ValueError("J-K is parallel to global +X")
    x = _vmul(xp, 1.0/xn); z = _cross(x, y)
    return [[x[0], y[0], z[0], j[0]], [x[1], y[1], z[1], j[1]], [x[2], y[2], z[2], j[2]], [0.0, 0.0, 0.0, 1.0]]


def _expected_matrices(angles, refs):
    result = {"pelvis": [[1.,0.,0.,0.], [0.,1.,0.,0.], [0.,0.,1.,0.], [0.,0.,0.,1.]]}
    for side in ("left", "right"):
        rest = _frame(_landmark(refs, side, "J"), _landmark(refs, side, "K"))
        a = math.radians(-float(angles.get(side, 0.0))); c, s = math.cos(a), math.sin(a)
        rx = [[1.,0.,0.,0.], [0.,c,-s,0.], [0.,s,c,0.], [0.,0.,0.,1.]]
        result[f"{side}_hip"] = (rest, _mm(rest, rx))
    return result


def _joint_rows(binding: Mapping[str, Any]):
    joints = binding.get("joints")
    if not isinstance(joints, Mapping):
        frames = binding.get("rest_frames")
        if not isinstance(frames, Mapping): raise ValueError("binding.rest_frames must be a mapping")
        identity = [[1.,0.,0.,0.], [0.,1.,0.,0.], [0.,0.,1.,0.], [0.,0.,0.,1.]]
        rows = {"pelvis": (identity, identity)}
        for side in ("left", "right"):
            row = frames.get(side)
            if not isinstance(row, Mapping): raise ValueError(f"missing binding rest frame {side}")
            rest = _mat(row.get("rest_matrix"), f"{side}.rest_matrix")
            rows[f"{side}_hip"] = (rest, _rigid_inverse(rest))
        return rows
    rows = {}
    for name in _JOINTS:
        row = joints.get(name)
        if not isinstance(row, Mapping): raise ValueError(f"missing binding joint {name}")
        rest = _mat(row.get("rest_matrix"), f"{name}.rest_matrix")
        inv = _mat(row.get("inverse_bind_matrix", row.get("inverse_bind")), f"{name}.inverse_bind_matrix")
        rows[name] = (rest, inv)
    return rows


def _weights(binding, count):
    raw = binding.get("evaluated_weights", binding.get("weights"))
    order = binding.get("joint_order", list(_JOINTS))
    if not isinstance(raw, Sequence) or len(raw) != count: raise ValueError("binding.weights must cover every vertex")
    out = []
    for i, row in enumerate(raw):
        if isinstance(row, Mapping): vals = [float(row.get(name, 0.0)) for name in _JOINTS]
        elif isinstance(row, Sequence) and len(row) == len(order):
            keyed = dict(zip(order, row)); vals = [float(keyed.get(name, 0.0)) for name in _JOINTS]
        else: raise ValueError(f"malformed weight row {i}")
        out.append(vals)
    return out


def _pose_payload(posed):
    joints = posed.get("joints")
    if joints is None and isinstance(posed.get("metadata"), Mapping): joints = posed["metadata"].get("joints")
    if not isinstance(joints, Mapping): return None
    result = {}
    for name in _JOINTS:
        row = joints.get(name)
        if not isinstance(row, Mapping): raise ValueError(f"posed export is missing joint {name}")
        result[name] = _mat(row.get("pose_matrix", row.get("matrix")), f"posed {name}.pose_matrix")
    return result


def _lbs(vertices, weights, skins):
    result = []
    for p, row in zip(vertices, weights):
        result.append(tuple(sum(row[j] * _mp(skins[name], p)[axis] for j, name in enumerate(_JOINTS)) for axis in range(3)))
    return result


def _triangles(quads): return [t for q in quads for t in ((q[0], q[1], q[2]), (q[0], q[2], q[3]))]
def _tri_area(v, t): return 0.5*_norm(_cross(_vsub(v[t[1]], v[t[0]]), _vsub(v[t[2]], v[t[0]])))
def _face_normal(v, q): return _vadd(_cross(_vsub(v[q[1]], v[q[0]]), _vsub(v[q[2]], v[q[0]])), _cross(_vsub(v[q[2]], v[q[0]]), _vsub(v[q[3]], v[q[0]])))


def _frozen_helpers():
    spec = importlib.util.spec_from_file_location("frozen_pelvis_transition_checks", _OLD_CHECKS)
    if spec is None or spec.loader is None: raise RuntimeError("frozen intersection helper unavailable")
    module = importlib.util.module_from_spec(spec); sys.modules[spec.name] = module; spec.loader.exec_module(module)
    return module


def _crest_y(case, refs, protocol):
    for source in (protocol, case, refs):
        if isinstance(source, Mapping):
            for key in ("crest_y", "pelvic_crest_y"):
                if key in source: return float(source[key])
    raise ValueError("crest_y is required")


def _scale(case, refs, vertices):
    lengths = [_distance(_landmark(refs, s, "J"), _landmark(refs, s, "K")) for s in ("left", "right")]
    return sum(lengths)/len(lengths) if max(lengths) > 0.0 else max(_distance(vertices[0], p) for p in vertices)


def check_binding(base_mesh: Mapping[str, Any], rest_mesh: Mapping[str, Any], binding: Mapping[str, Any],
                  protocol: Mapping[str, Any]) -> dict[str, Any]:
    """Verify the exported weights satisfy the declared harmonic/stencil method."""
    report = {"schema": "pelvis-hip-articulation-binding-checks-v1", "pass": False, "checks": {}, "metrics": {}, "errors": []}
    try:
        tolerance = float(protocol["checks"]["weight_partition_tolerance"])
        base_vertices, quads = base_mesh["vertices"], base_mesh["quads"]
        count = len(base_vertices); graph = [set() for _ in range(count)]
        for qi, quad in enumerate(quads):
            if not isinstance(quad, Sequence) or len(quad) != 4: raise ValueError(f"malformed base quad {qi}")
            for i, vertex in enumerate(quad):
                neighbour = quad[(i+1) % 4]
                if not isinstance(vertex, int) or not isinstance(neighbour, int) or min(vertex, neighbour) < 0 or max(vertex, neighbour) >= count:
                    raise ValueError(f"out-of-range base quad {qi}")
                graph[vertex].add(neighbour); graph[neighbour].add(vertex)
        seen, pending = ({0}, [0]) if count else (set(), [])
        while pending:
            vertex = pending.pop()
            for neighbour in graph[vertex] - seen: seen.add(neighbour); pending.append(neighbour)
        connected = len(seen) == count and count > 0
        transitions = base_mesh["metadata"]["transition_indices"]
        groups = {(side, group): set(transitions[side][group]) for side in ("left", "right")
                  for group in ("socket", "ringA", "ringB", "exit")}
        if any(not values or any(i < 0 or i >= count for i in values) for values in groups.values()): raise ValueError("invalid base transition indices")
        unknown = groups["left", "socket"] | groups["left", "ringA"] | groups["right", "socket"] | groups["right", "ringA"]
        left = groups["left", "ringB"] | groups["left", "exit"]
        right = groups["right", "ringB"] | groups["right", "exit"]
        if (unknown & left) or (unknown & right) or (left & right): raise ValueError("overlapping Dirichlet groups")
        base_weights = binding.get("base_weights"); evaluated = binding.get("evaluated_weights")
        if not isinstance(base_weights, Sequence) or len(base_weights) != count: raise ValueError("base_weights dimensions do not match L0")
        if not isinstance(evaluated, Sequence) or len(evaluated) != len(rest_mesh["vertices"]): raise ValueError("evaluated_weights dimensions do not match L2")
        rows = [[float(x) for x in row] for row in base_weights]
        eval_rows = [[float(x) for x in row] for row in evaluated]
        finite_dims = all(len(row) == 3 and all(math.isfinite(x) for x in row) for row in rows + eval_rows)
        if not finite_dims: raise ValueError("weights must be finite three-column rows")
        anchor_error = 0.0
        for i in set(range(count)) - unknown:
            expected = (0., 1., 0.) if i in left else (0., 0., 1.) if i in right else (1., 0., 0.)
            anchor_error = max(anchor_error, max(abs(rows[i][c]-expected[c]) for c in range(3)))
        residual = max((abs(len(graph[i])*rows[i][c] - sum(rows[j][c] for j in graph[i]))
                        for i in unknown for c in range(3)), default=math.inf)
        stencils = rest_mesh.get("base_stencils")
        if not isinstance(stencils, Sequence) or len(stencils) != len(eval_rows): raise ValueError("base_stencils dimensions do not match L2")
        stencil_error = 0.0
        for i, stencil in enumerate(stencils):
            if not isinstance(stencil, Sequence) or not stencil: raise ValueError(f"malformed base stencil {i}")
            for c in range(3):
                expected = sum(float(coefficient)*rows[int(index)][c] for index, coefficient in stencil)
                stencil_error = max(stencil_error, abs(eval_rows[i][c]-expected))
        report["checks"] = {"connected_base_graph": connected, "finite_dimensions": finite_dims,
                            "dirichlet_anchors": anchor_error <= tolerance,
                            "harmonic_residual": residual <= tolerance,
                            "stencil_transfer": stencil_error <= tolerance}
        report["metrics"] = {"anchor_max_error": anchor_error, "laplacian_residual_max": residual,
                             "stencil_max_error": stencil_error}
    except Exception as exc:
        report["errors"].append({"code": "binding_check_failure", "detail": str(exc)})
    report["pass"] = not report["errors"] and bool(report["checks"]) and all(report["checks"].values())
    return report


def check_pose(rest_mesh: Mapping[str, Any], posed_mesh: Mapping[str, Any], binding: Mapping[str, Any],
               angles: Mapping[str, float], case: Mapping[str, Any], reference_landmarks: Mapping[str, Any],
               protocol: Mapping[str, Any]) -> dict[str, Any]:
    """Return a small JSON-safe report; exported inputs are never repaired."""
    report: dict[str, Any] = {"schema": "pelvis-hip-articulation-checks-v1", "pass": False, "checks": {}, "metrics": {}, "errors": []}
    fail = lambda code, detail: report["errors"].append({"code": code, "detail": str(detail)})
    try:
        reference_landmarks = _references(case, reference_landmarks)
        limits = protocol.get("checks")
        if not isinstance(limits, Mapping): raise ValueError("protocol.checks must be a mapping")
        weight_tolerance = float(limits["weight_partition_tolerance"])
        frame_tolerance = float(limits["frame_and_transform_tolerance"])
        identity_tolerance = float(limits["identity_error_over_L_max"])
        lbs_tolerance = float(limits["exported_LBS_error_over_L_max"])
        port_tolerance = float(limits["rigid_port_error_over_L_max"])
        pelvis_tolerance = float(limits["pelvis_only_weighted_error_over_L_max"])
        crest_tolerance = float(limits["above_crest_skin_displacement_over_L_max"])
        area_min, area_max = (float(x) for x in limits["lower_triangle_area_ratio"])
        edge_min, edge_max = (float(x) for x in limits["lower_edge_length_ratio"])
        normal_min = float(limits["lower_rest_posed_triangle_normal_dot_min"])
        intersection_max = int(limits["lower_nonadjacent_intersections_max"])
        rv, pv = rest_mesh["vertices"], posed_mesh["vertices"]
        rq, pq = rest_mesh["quads"], posed_mesh["quads"]
        if not isinstance(rv, Sequence) or not isinstance(pv, Sequence) or len(rv) != len(pv): raise ValueError("vertex arrays differ in length")
        finite = all(isinstance(p, Sequence) and len(p) == 3 and all(math.isfinite(float(x)) for x in p) for p in list(rv)+list(pv))
        topology = rq == pq and rest_mesh.get("loops") == posed_mesh.get("loops")
        report["checks"].update(finite_vertices=finite, exact_topology=topology)
        if not finite: raise ValueError("non-finite or malformed vertices")
        if not topology: fail("topology", "quads or welded-index loops changed")
        L = _scale(case, reference_landmarks, rv)
        joints = _joint_rows(binding); weights = _weights(binding, len(rv)); exported_pose = _pose_payload(posed_mesh)
        finite_weights = all(math.isfinite(w) for row in weights for w in row)
        bounds = finite_weights and all(-weight_tolerance <= w <= 1.0+weight_tolerance for row in weights for w in row)
        partition_error = max(abs(sum(row)-1.0) for row in weights)
        report["checks"].update(finite_weights=finite_weights, weight_bounds=bounds,
                                partition_unity=finite_weights and partition_error <= weight_tolerance)
        if not finite_weights: raise ValueError("binding weights are non-finite")
        expected = _expected_matrices(angles, reference_landmarks)
        frame_errors, det_errors, inverse_errors, pose_export_errors = [], [], [], []
        expected_pose = {"pelvis": expected["pelvis"]}
        for name in _JOINTS:
            rest, inv = joints[name]
            basis = [[rest[r][c] for c in range(3)] for r in range(3)]
            frame_errors.append(max(abs(sum(basis[k][r]*basis[k][c] for k in range(3))-(r == c)) for r in range(3) for c in range(3)))
            det = _dot(tuple(basis[r][0] for r in range(3)), _cross(tuple(basis[r][1] for r in range(3)), tuple(basis[r][2] for r in range(3))))
            det_errors.append(abs(det-1.0)); inverse_errors.append(_identity_error(_mm(rest, inv)))
            if name != "pelvis":
                exp_rest, exp_pose = expected[name]; frame_errors.append(max(abs(rest[r][c]-exp_rest[r][c]) for r in range(4) for c in range(4))); expected_pose[name] = exp_pose
            if exported_pose is not None:
                pose_export_errors.append(max(abs(exported_pose[name][r][c]-expected_pose[name][r][c]) for r in range(4) for c in range(4)))
        metadata = posed_mesh.get("metadata", {})
        exported_angles = metadata.get("pose_angles_degrees", {}) if isinstance(metadata, Mapping) else {}
        if not isinstance(exported_angles, Mapping) or any(side not in exported_angles for side in ("left", "right")):
            raise ValueError("posed metadata must export both pose angles")
        angle_error = max(abs(float(exported_angles.get(side, math.inf))-float(angles.get(side, 0.0))) for side in ("left", "right"))
        local_errors = []
        frames = binding.get("rest_frames", {})
        for side in ("left", "right"):
            if isinstance(frames, Mapping) and isinstance(frames.get(side), Mapping):
                inv = joints[f"{side}_hip"][1]
                for mark, key in (("T", "T_local"), ("K", "K_local")):
                    declared = frames[side].get(key, binding.get(key.lower(), {}).get(side) if isinstance(binding.get(key.lower()), Mapping) else None)
                    if not isinstance(declared, Sequence) or len(declared) != 3: raise ValueError(f"missing {side} {key}")
                    local_errors.append(_distance(declared, _mp(inv, _landmark(reference_landmarks, side, mark))))
                for mark in ("J", "T", "K"):
                    declared = frames[side].get(mark)
                    if declared is not None: local_errors.append(_distance(declared, _landmark(reference_landmarks, side, mark)))
        skins_rest = {n: _mm(joints[n][0], joints[n][1]) for n in _JOINTS}
        skins_pose = {n: _mm(expected_pose[n], joints[n][1]) for n in _JOINTS}
        identity_error = max(_distance(a, b) for a, b in zip(rv, _lbs(rv, weights, skins_rest)))
        posed_errors = [_distance(a, b) for a, b in zip(pv, _lbs(rv, weights, skins_pose))]
        report["checks"].update(frames=max(frame_errors) <= frame_tolerance and max(det_errors) <= frame_tolerance,
                                inverse_bind=max(inverse_errors) <= frame_tolerance,
                                exported_pose=angle_error <= frame_tolerance and (not pose_export_errors or max(pose_export_errors) <= frame_tolerance),
                                landmark_rest_locals=(not local_errors or max(local_errors) <= frame_tolerance*L),
                                identity_rest=identity_error <= identity_tolerance*L,
                                independent_lbs=max(posed_errors) <= lbs_tolerance*L)
        report["metrics"].update(scale=L, partition_error=partition_error, frame_error=max(frame_errors), determinant_error=max(det_errors),
                                 inverse_bind_error=max(inverse_errors), pose_export_error=max(pose_export_errors, default=angle_error),
                                 landmark_rest_local_error=max(local_errors, default=0.0), identity_rest_max_error=identity_error,
                                 posed_lbs_max_error=max(posed_errors), posed_lbs_worst_vertices=sorted(range(len(posed_errors)), key=posed_errors.__getitem__, reverse=True)[:_EXAMPLE_CAP])

        tris = _triangles(rq); rest_areas = [_tri_area(rv, t) for t in tris]; posed_areas = [_tri_area(pv, t) for t in tris]
        owners = rest_mesh.get("face_owners", [])
        if len(owners) != len(rq): raise ValueError("face_owners must cover quads")
        frozen = _frozen_helpers()
        lower_faces = {i for i, owner in enumerate(owners) if frozen._owner_is_lower(owner)}
        lower_triangle_ids = [i for i in range(len(tris)) if i//2 in lower_faces]
        area_ratios = [posed_areas[i]/rest_areas[i] if rest_areas[i] > 0 else math.inf for i in lower_triangle_ids]
        edges = {tuple(sorted((q[i], q[(i+1)%4]))) for f, q in enumerate(rq) if f in lower_faces for i in range(4)}
        edge_ratios = [_distance(pv[a], pv[b])/_distance(rv[a], rv[b]) for a, b in edges if _distance(rv[a], rv[b]) > 0]
        normals, normal_face_ids = [], []
        for i in lower_triangle_ids:
            triangle = tris[i]
            a = _cross(_vsub(rv[triangle[1]], rv[triangle[0]]), _vsub(rv[triangle[2]], rv[triangle[0]]))
            b = _cross(_vsub(pv[triangle[1]], pv[triangle[0]]), _vsub(pv[triangle[2]], pv[triangle[0]]))
            normals.append(_dot(a, b)/(_norm(a)*_norm(b)) if _norm(a)*_norm(b) > 0 else -1.0); normal_face_ids.append(i//2)
        tri_ids = [i//2 for i in range(len(tris))]
        intersections = frozen._intersection_report(pv, tris, tri_ids, owners)
        lower_intersection_count = len(intersections.get("lower_hit_pairs", []))
        report["checks"].update(triangle_area_ratios=bool(area_ratios) and min(area_ratios) >= area_min and max(area_ratios) <= area_max,
                                lower_edge_ratios=bool(edge_ratios) and min(edge_ratios) >= edge_min and max(edge_ratios) <= edge_max,
                                lower_nonadjacent_self_intersection=bool(intersections.get("available"))
                                    and bool(intersections.get("pair_policy_complete"))
                                    and bool(intersections.get("collision_inventory_complete"))
                                    and lower_intersection_count <= intersection_max,
                                gross_normal_flip=(max(abs(float(angles.get(s, 0.0))) for s in ("left", "right")) > 30.0 or min(normals) > normal_min))
        report["metrics"].update(area_ratio_min=min(area_ratios), area_ratio_max=max(area_ratios), lower_edge_ratio_min=min(edge_ratios),
                                 lower_edge_ratio_max=max(edge_ratios), normal_dot_min=min(normals), normal_dot_max=max(normals),
                                 worst_normal_faces=[normal_face_ids[i] for i in sorted(range(len(normals)), key=normals.__getitem__)[:_EXAMPLE_CAP]],
                                 lower_intersection_count=lower_intersection_count,
                                 lower_intersection_examples=intersections.get("lower_hit_pairs", [])[:_EXAMPLE_CAP])

        crest = _crest_y(case, reference_landmarks, protocol)
        crest_ids = [i for i, p in enumerate(rv) if float(p[1]) >= crest]
        crest_error = max((_distance(rv[i], pv[i]) for i in crest_ids), default=math.inf)
        pelvis_ids = [i for i, row in enumerate(weights) if row[0] == 1.0 and row[1] == 0.0 and row[2] == 0.0]
        pelvis_error = max((_distance(rv[i], pv[i]) for i in pelvis_ids), default=math.inf)
        report["checks"].update(crest_ceiling=bool(crest_ids) and crest_error <= crest_tolerance*L,
                                strict_pelvis_stationary=bool(pelvis_ids) and pelvis_error <= pelvis_tolerance*L)
        report["metrics"].update(crest_vertex_count=len(crest_ids), crest_max_displacement=crest_error,
                                 strict_pelvis_vertex_count=len(pelvis_ids), strict_pelvis_max_displacement=pelvis_error)

        port_rows = {}
        loops = rest_mesh.get("loops", {})
        for side in ("left", "right"):
            ids = loops.get(f"port.{side}_thigh", [])
            target = [_mp(skins_pose[f"{side}_hip"], rv[i]) for i in ids]
            errors = [_distance(pv[i], q) for i, q in zip(ids, target)]
            rc = tuple(sum(rv[i][a] for i in ids)/len(ids) for a in range(3)); pc = tuple(sum(pv[i][a] for i in ids)/len(ids) for a in range(3))
            ec = _mp(skins_pose[f"{side}_hip"], rc)
            extent_error = max((abs(_distance(pc, pv[i])-_distance(ec, q)) for i, q in zip(ids, target)), default=math.inf)
            def area_vector(points):
                return _vmul(tuple(sum(_cross(points[i], points[(i+1) % len(points)])[a] for i in range(len(points))) for a in range(3)), .5)
            actual_area, target_area = area_vector([pv[i] for i in ids]), area_vector(target)
            area_vector_error = _distance(actual_area, target_area)
            port_rows[side] = {"count": len(ids), "max_vertex_error": max(errors, default=math.inf), "centroid_error": _distance(pc, ec) if ids else math.inf,
                               "extent_error": extent_error, "area_vector_error": area_vector_error}
        report["checks"]["distal_ports_rigid"] = all(r["count"] and max(r["max_vertex_error"], r["centroid_error"], r["extent_error"]) <= port_tolerance*L
                                                              and r["area_vector_error"] <= port_tolerance*L*L for r in port_rows.values())
        report["metrics"]["ports"] = port_rows

        landmark_errors = []
        for side in ("left", "right"):
            pose_matrix = exported_pose[f"{side}_hip"] if exported_pose is not None else expected_pose[f"{side}_hip"]
            skin = _mm(pose_matrix, joints[f"{side}_hip"][1])
            for name in ("J", "T", "K"):
                p = _landmark(reference_landmarks, side, name)
                expected_p = _mp(skins_pose[f"{side}_hip"], p)
                landmark_errors.append(_distance(_mp(skin, p), expected_p))
            landmark_errors.append(_distance(_mp(skin, _landmark(reference_landmarks, side, "J")), _landmark(reference_landmarks, side, "J")))
        report["checks"]["exported_landmark_motion"] = max(landmark_errors) <= frame_tolerance*L
        report["metrics"]["exported_landmark_max_error"] = max(landmark_errors)
        provenance = posed_mesh.get("provenance", {})
        report["checks"]["rest_provenance_preserved"] = (isinstance(provenance, Mapping) and provenance.get("base_stencils") == "REST"
                                                           and not bool(metadata.get("posed_cage_evaluation", True)))
    except Exception as exc:
        fail("input_or_check_failure", exc)
    report["pass"] = not report["errors"] and bool(report["checks"]) and all(report["checks"].values())
    return report
