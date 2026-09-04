"""Frozen topology, formula, subdivision, derivative, and incidence authority; chart and summary data belong to ``chart_lineage``."""
from __future__ import annotations

import copy
from collections import defaultdict, namedtuple
from collections.abc import Mapping
from dataclasses import dataclass
from fractions import Fraction
from functools import reduce
from hashlib import sha256
from math import gcd, isfinite, pow
from typing import Any

try:
    import prepared_projection
except ImportError:  # pragma: no cover
    from . import prepared_projection
try:
    import mesh_correctness as _generic
except ImportError:  # pragma: no cover
    from . import mesh_correctness as _generic

DOMAINS = tuple(f"domain.{name}" for name in "pelvis abdomen thorax neck left_shoulder right_shoulder left_hip right_hip".split())  # noqa: SIM905
JUNCTIONS = tuple(f"junction.{name}" for name in "pelvis__left_hip pelvis__abdomen abdomen__thorax thorax__left_shoulder thorax__neck pelvis__right_hip thorax__right_shoulder".split())  # noqa: SIM905
PORTS = tuple(f"port.{name}" for name in "neck left_arm right_arm left_thigh right_thigh".split())  # noqa: SIM905
FORMULAS = tuple("formula.axial.j1.edge formula.axial.j1.interior formula.axial.station formula.neck.stem formula.shoulder.left formula.shoulder.right formula.hip.left formula.hip.right".split())  # noqa: SIM905
SPECIAL_CASE_IDS = tuple("formula.axial.j1.edge formula.axial.j1.interior formula.neck.stem formula.shoulder.left formula.shoulder.right formula.hip.left formula.hip.right topology.open-port-cap topology.shared-junction".split())  # noqa: SIM905
_STATIONS = tuple((name, ("main", [], "part", role), prefix) for name, role, prefix in (row.split() for row in "lower_pelvis pelvis form_torso_profile_lower_pelvis;upper_pelvis pelvis form_torso_profile_upper_pelvis;lower_abdomen torso form_torso_profile_lower_abdomen;waist_abdomen torso form_torso_profile_waist_abdomen;upper_abdomen torso form_torso_profile_upper_abdomen;lower_ribcage torso form_torso_profile_lower_ribcage;upper_ribcage_shoulder torso form_torso_profile_upper_ribcage_shoulder;neck_collar neck form_head_neck_profile_neck_collar;neck_upper neck form_head_neck_profile_neck_upper".split(";")))  # noqa: SIM905
STATION_NAMES = tuple(row[0] for row in _STATIONS)
STATION_INFO = {name: (owner, prefix) for name, owner, prefix in _STATIONS}
JUNCTION_INFO = {junction: (tuple(domains.split(",")), (drop, tuple(axes.split(",")))) for junction, domains, drop, axes in (("junction.pelvis__left_hip", "domain.pelvis,domain.left_hip", "j", "i,k"), ("junction.pelvis__abdomen", "domain.pelvis,domain.abdomen", "j", "i,k"), ("junction.abdomen__thorax", "domain.abdomen,domain.thorax", "j", "i,k"), ("junction.thorax__left_shoulder", "domain.thorax,domain.left_shoulder", "i", "j,k"), ("junction.thorax__neck", "domain.thorax,domain.neck", "j", "i,k"), ("junction.pelvis__right_hip", "domain.pelvis,domain.right_hip", "j", "i,k"), ("junction.thorax__right_shoulder", "domain.thorax,domain.right_shoulder", "i", "j,k"))}
PORT_INFO = {port: (domain, direction, tuple(controls.split(","))) for port, domain, direction, controls in (("port.neck", "domain.neck", "+Y", "c057,c079,c080,c081,c059,c058"), ("port.left_arm", "domain.left_shoulder", "-X", "c009,c012,c014,c015,c016,c013,c011,c010"), ("port.right_arm", "domain.right_shoulder", "+X", "c112,c113,c114,c116,c119,c118,c117,c115"), ("port.left_thigh", "domain.left_hip", "-Y", "c000,c001,c002,c018,c040,c039,c038,c017"), ("port.right_thigh", "domain.right_hip", "-Y", "c060,c061,c062,c083,c105,c104,c103,c082"))}
JUNCTION_TRACES = {junction: tuple(controls.split(",")) for junction, controls in (("junction.pelvis__left_hip", "c003,c004,c005,c020,c043,c042,c041,c019"), ("junction.pelvis__abdomen", "c021,c022,c023,c045,c067,c088,c087,c086,c066,c044"), ("junction.abdomen__thorax", "c027,c028,c029,c049,c071,c094,c093,c092,c070,c048"), ("junction.thorax__left_shoulder", "c030,c031,c032,c034,c037,c036,c035,c033"), ("junction.thorax__neck", "c054,c055,c056,c078,c077,c076"), ("junction.pelvis__right_hip", "c063,c064,c065,c085,c108,c107,c106,c084"), ("junction.thorax__right_shoulder", "c095,c096,c097,c099,c102,c101,c100,c098"))}
_CONTROL_COORDINATES = """0 -1 0;0 -1 1;0 -1 2;0 0 0;0 0 1;0 0 2;0 1 0;0 1 1;0 1 2;0 4 0;0 4 1;0 4 2;0 5 0;0 5 2;0 6 0;0 6 1;0 6 2;1 -1 0;1 -1 2;1 0 0;1 0 2;1 1 0;1 1 1;1 1 2;1 2 0;1 2 1;1 2 2;1 3 0;1 3 1;1 3 2;1 4 0;1 4 1;1 4 2;1 5 0;1 5 2;1 6 0;1 6 1;1 6 2;2 -1 0;2 -1 1;2 -1 2;2 0 0;2 0 1;2 0 2;2 1 0;2 1 2;2 2 0;2 2 2;2 3 0;2 3 2;2 4 0;2 4 2;2 5 0;2 5 2;2 6 0;2 6 1;2 6 2;2 7 0;2 7 1;2 7 2;3 -1 0;3 -1 1;3 -1 2;3 0 0;3 0 1;3 0 2;3 1 0;3 1 2;3 2 0;3 2 2;3 3 0;3 3 2;3 4 0;3 4 2;3 5 0;3 5 2;3 6 0;3 6 1;3 6 2;3 7 0;3 7 1;3 7 2;4 -1 0;4 -1 2;4 0 0;4 0 2;4 1 0;4 1 1;4 1 2;4 2 0;4 2 1;4 2 2;4 3 0;4 3 1;4 3 2;4 4 0;4 4 1;4 4 2;4 5 0;4 5 2;4 6 0;4 6 1;4 6 2;5 -1 0;5 -1 1;5 -1 2;5 0 0;5 0 1;5 0 2;5 1 0;5 1 1;5 1 2;5 4 0;5 4 1;5 4 2;5 5 0;5 5 2;5 6 0;5 6 1;5 6 2"""
CONTROL_COORDINATES = tuple(tuple(map(int, row.split())) for row in _CONTROL_COORDINATES.split(";") if row.strip())
CONTROL_IDS = tuple(f"c{i:03d}" for i in range(120))
CONTROL_BY_COORDINATE = dict(zip(CONTROL_COORDINATES, CONTROL_IDS))
COORDINATE_BY_CONTROL = dict(zip(CONTROL_IDS, CONTROL_COORDINATES))
_FACE_TEXT = """domain.left_hip:0,1,4,3|domain.left_hip:0,3,19,17|domain.left_hip:1,2,5,4|domain.left_hip:2,18,20,5|domain.pelvis:3,4,7,6|domain.pelvis:3,6,21,19|domain.pelvis:4,5,8,7|domain.pelvis:5,20,23,8|domain.pelvis:6,7,22,21|domain.pelvis:7,8,23,22|domain.left_shoulder:9,12,33,30|domain.left_shoulder:9,30,31,10|domain.left_shoulder:10,31,32,11|domain.left_shoulder:11,32,34,13|domain.left_shoulder:12,14,35,33|domain.left_shoulder:13,34,37,16|domain.left_shoulder:14,15,36,35|domain.left_shoulder:15,16,37,36|domain.left_hip:17,19,41,38|domain.left_hip:18,40,43,20|domain.pelvis:19,21,44,41|domain.pelvis:20,43,45,23|domain.abdomen:21,22,25,24|domain.abdomen:21,24,46,44|domain.abdomen:22,23,26,25|domain.abdomen:23,45,47,26|domain.abdomen:24,25,28,27|domain.abdomen:24,27,48,46|domain.abdomen:25,26,29,28|domain.abdomen:26,47,49,29|domain.thorax:27,28,31,30|domain.thorax:27,30,50,48|domain.thorax:28,29,32,31|domain.thorax:29,49,51,32|domain.thorax:30,33,52,50|domain.thorax:32,51,53,34|domain.thorax:33,35,54,52|domain.thorax:34,53,56,37|domain.thorax:35,36,55,54|domain.thorax:36,37,56,55|domain.left_hip:38,41,42,39|domain.left_hip:39,42,43,40|domain.pelvis:41,44,66,63|domain.pelvis:41,63,64,42|domain.pelvis:42,64,65,43|domain.pelvis:43,65,67,45|domain.abdomen:44,46,68,66|domain.abdomen:45,67,69,47|domain.abdomen:46,48,70,68|domain.abdomen:47,69,71,49|domain.thorax:48,50,72,70|domain.thorax:49,71,73,51|domain.thorax:50,52,74,72|domain.thorax:51,73,75,53|domain.thorax:52,54,76,74|domain.thorax:53,75,78,56|domain.neck:54,55,58,57|domain.neck:54,57,79,76|domain.neck:55,56,59,58|domain.neck:56,78,81,59|domain.right_hip:60,61,64,63|domain.right_hip:60,63,84,82|domain.right_hip:61,62,65,64|domain.right_hip:62,83,85,65|domain.pelvis:63,66,86,84|domain.pelvis:65,85,88,67|domain.abdomen:66,68,89,86|domain.abdomen:67,88,91,69|domain.abdomen:68,70,92,89|domain.abdomen:69,91,94,71|domain.thorax:70,72,95,92|domain.thorax:71,94,97,73|domain.thorax:72,74,98,95|domain.thorax:73,97,99,75|domain.thorax:74,76,100,98|domain.thorax:75,99,102,78|domain.thorax:76,77,101,100|domain.neck:76,79,80,77|domain.thorax:77,78,102,101|domain.neck:77,80,81,78|domain.right_hip:82,84,106,103|domain.right_hip:83,105,108,85|domain.pelvis:84,86,109,106|domain.pelvis:85,108,111,88|domain.pelvis:86,87,110,109|domain.abdomen:86,89,90,87|domain.pelvis:87,88,111,110|domain.abdomen:87,90,91,88|domain.abdomen:89,92,93,90|domain.abdomen:90,93,94,91|domain.thorax:92,95,96,93|domain.thorax:93,96,97,94|domain.right_shoulder:95,98,115,112|domain.right_shoulder:95,112,113,96|domain.right_shoulder:96,113,114,97|domain.right_shoulder:97,114,116,99|domain.right_shoulder:98,100,117,115|domain.right_shoulder:99,116,119,102|domain.right_shoulder:100,101,118,117|domain.right_shoulder:101,102,119,118|domain.right_hip:103,106,107,104|domain.right_hip:104,107,108,105|domain.pelvis:106,109,110,107|domain.pelvis:107,110,111,108"""
FACE_CATALOG = tuple((f"q{i:03d}", *item.split(":", 1)[:1], tuple(map(int, item.split(":", 1)[1].split(",")))) for i, item in enumerate(x for x in _FACE_TEXT.replace("\n", "").split("|") if x))
def _rational(value): return value if isinstance(value, Fraction) else Fraction.from_float(value) if type(value) is float else Fraction(value)
def _add(a, b): return _rational(a) + _rational(b) if isinstance(a, Fraction) or isinstance(b, Fraction) else a + b
def _sub(a, b): return _rational(a) - _rational(b) if isinstance(a, Fraction) or isinstance(b, Fraction) else a - b
def _mul(a, b): return _rational(a) * _rational(b) if isinstance(a, Fraction) or isinstance(b, Fraction) else a * b
def _div(a, b): return _rational(a) / _rational(b) if isinstance(a, Fraction) or isinstance(b, Fraction) else a / b
def _ordered(values): return reduce(_add, values, 0.0)
def _sp(value, exponent):
    if isinstance(value, _Dual):
        magnitude = pow(abs(value.value), exponent); coefficient = 0.0 if value.value == 0.0 else exponent * pow(abs(value.value), exponent - 1.0) * (1.0 if value.value > 0 else -1.0)
        derivative = _rational(coefficient) * value.derivative; return _Dual(0.0 if magnitude == 0.0 else (-magnitude if value.value < 0 else magnitude), derivative)
    magnitude = pow(abs(value), exponent); return 0.0 if magnitude == 0.0 else (-magnitude if value < 0.0 else magnitude)
def _lerp(a, b, t): return _add(_mul(_sub(1.0, t), a), _mul(t, b))
def _vadd(a, b): return tuple(_add(x, y) for x, y in zip(a, b))
def _vlerp(a, b, t): return tuple(_lerp(x, y, t) for x, y in zip(a, b))
def _e(center, u, q, r_l, r_a, r_p, n):
    exponent = _div(2.0, n); return (_add(center[0], _mul(r_l, _sp(u, exponent))), center[1], _add(center[2], _mul(r_a if q >= 0.0 else r_p, _sp(q, exponent))))
def _cell_inventory():
    rows = {"domain.pelvis": [(i, 0) for i in range(5)], "domain.abdomen": [(i, j) for i in range(1, 4) for j in (1, 2)], "domain.thorax": [(i, j) for i in range(1, 4) for j in (3, 4, 5)], "domain.neck": [(2, 6)], "domain.left_shoulder": [(0, 4), (0, 5)], "domain.right_shoulder": [(4, 4), (4, 5)], "domain.left_hip": [(i, -1) for i in (0, 1)], "domain.right_hip": [(i, -1) for i in (3, 4)]}
    return tuple((domain, i, j, k) for domain in DOMAINS for i, j in rows[domain] for k in (0, 1))
CELL_CATALOG = _cell_inventory()
def _cube_faces(i, j, k):
    return ((-1, ((i, j, k), (i, j, k + 1), (i, j + 1, k + 1), (i, j + 1, k))), (1, ((i + 1, j, k), (i + 1, j + 1, k), (i + 1, j + 1, k + 1), (i + 1, j, k + 1))), (-2, ((i, j, k), (i + 1, j, k), (i + 1, j, k + 1), (i, j, k + 1))), (2, ((i, j + 1, k), (i, j + 1, k + 1), (i + 1, j + 1, k + 1), (i + 1, j + 1, k))), (-3, ((i, j, k), (i, j + 1, k), (i + 1, j + 1, k), (i + 1, j, k))), (3, ((i, j, k + 1), (i + 1, j, k + 1), (i + 1, j + 1, k + 1), (i, j + 1, k + 1))))
def _generated_faces():
    uses = defaultdict(list)
    for domain, i, j, k in CELL_CATALOG:
        for direction, cycle in _cube_faces(i, j, k): uses[tuple(sorted(cycle))].append((domain, direction, cycle))
    excluded = {("domain.neck", 2), ("domain.left_shoulder", -1), ("domain.right_shoulder", 1), ("domain.left_hip", -2), ("domain.right_hip", -2)}
    return {tuple(CONTROL_BY_COORDINATE[p] for p in rows[0][2]): rows[0][0] for rows in uses.values() if len(rows) == 1 and (rows[0][0], rows[0][1]) not in excluded}
def _catalog_faces():
    generated = _generated_faces()
    if len(generated) != 104: raise ValueError("selected-cell/port-cap face count mismatch")
    result = []
    for face_id, domain, cycle in FACE_CATALOG:
        ids = tuple(f"c{x:03d}" for x in cycle)
        if generated.get(ids) != domain: raise ValueError(f"face catalog mismatch at {face_id}")
        result.append((face_id, domain, ids))
    if set(generated) != {row[2] for row in result}: raise ValueError("face catalog is not a bijection")
    return tuple(result)
FACE_RECORDS = _catalog_faces()
def _edges(faces):
    result = defaultdict(list)
    for fi, (_, domain, face) in enumerate(faces):
        for slot, a in enumerate(face):
            b = face[(slot + 1) % 4]; key = tuple(sorted((a, b), key=lambda x: int(x[1:]))); result[key].append((fi, slot, a, b, domain))
    return dict(result)
def _control_sources():
    incident = {control: {domain for _, domain, face in FACE_RECORDS if control in face} for control in CONTROL_IDS}
    ordered = {control: tuple(domain for domain in DOMAINS if domain in incident[control]) for control in CONTROL_IDS}; by_pair = {frozenset(info[0]): jid for jid, info in JUNCTION_INFO.items()}; owners = {}
    for control, domains in ordered.items():
        if len(domains) == 1: owners[control] = domains[0]
        elif frozenset(domains) in by_pair: owners[control] = by_pair[frozenset(domains)]
        else: raise ValueError(f"invalid incident domains for {control}")
    return ordered, owners
CONTROL_DOMAIN_INCIDENTS, CONTROL_OWNERS = _control_sources()
CONTROL_JUNCTION_INCIDENTS = {c: CONTROL_OWNERS[c] for c in CONTROL_IDS if CONTROL_OWNERS[c].startswith("junction.")}
EDGE_RECORDS = _edges(FACE_RECORDS)
TopologyReport = namedtuple("TopologyReport", "vertex_count edge_count face_count boundary_edge_count boundary_components euler_characteristic extraordinary_controls")
def _numeric_id(value): return int(value[1:])
def _edge_key(left, right): return tuple(sorted((left, right), key=_numeric_id))
def _boundary_components(edges):
    adjacency = defaultdict(set)
    for left, right in edges: adjacency[left].add(right); adjacency[right].add(left)
    unseen = set(adjacency); count = 0
    while unseen:
        count += 1; todo = [unseen.pop()]
        while todo:
            vertex = todo.pop(); neighbours = adjacency[vertex] & unseen; unseen.difference_update(neighbours); todo.extend(neighbours)
    return count
def _domain_boundary_edges(domain):
    counts = defaultdict(int)
    for _, owner, face in FACE_RECORDS:
        if owner == domain:
            for left, right in zip(face, face[1:] + face[:1]): counts[_edge_key(left, right)] += 1
    return {edge for edge, count in counts.items() if count == 1}
def _directed_boundary_cycle(domain, shared):
    following = {}
    for _, owner, face in FACE_RECORDS:
        if owner != domain: continue
        for left, right in zip(face, face[1:] + face[:1]):
            if _edge_key(left, right) in shared:
                if left in following and following[left] != right: raise ValueError("ambiguous directed junction edge")
                following[left] = right
    vertices = {vertex for edge in shared for vertex in edge}
    if len(following) != len(shared) or set(following) != vertices: raise ValueError("junction boundary is not a directed cycle")
    return _closed_cycle(following, len(shared))
def _closed_cycle(following, size):
    start = min(following, key=_numeric_id); cycle = []; current = start
    for _ in range(size):
        cycle.append(current); current = following.get(current)
        if current is None: raise ValueError("junction boundary cycle is open")
    if current != start or len(set(cycle)) != size: raise ValueError("junction boundary cycle is not closed")
    return tuple(cycle)
def _canonical_cycle(edges):
    adjacency = defaultdict(set)
    for left, right in edges: adjacency[left].add(right); adjacency[right].add(left)
    if not adjacency or any(len(neighbours) != 2 for neighbours in adjacency.values()): raise ValueError("junction boundary is not one undirected cycle")
    following = {}; previous = None; current = min(adjacency, key=_numeric_id)
    while current not in following:
        candidates = sorted(adjacency[current] - ({previous} if previous is not None else set()), key=_numeric_id)
        if not candidates: raise ValueError("junction boundary cycle is open")
        following[current] = candidates[0]; previous, current = current, candidates[0]
    return _closed_cycle(following, len(edges))
def _junction_evidence():
    result = {}
    for junction in JUNCTIONS:
        domains = JUNCTION_INFO[junction][0]; boundaries = tuple(_domain_boundary_edges(domain) for domain in domains); shared = boundaries[0] & boundaries[1]
        first, second = (_directed_boundary_cycle(domain, shared) for domain in domains)
        if first != (second[0], *reversed(second[1:])): raise ValueError(f"junction directions are not opposite: {junction}")
        trace = _canonical_cycle(shared)
        if tuple(JUNCTION_TRACES[junction]) != trace: raise ValueError(f"junction trace disagrees with face incidence: {junction}")
        result[junction] = {"domains": domains, "trace": trace, "edges": shared}
    return result
def validate_catalogs():
    boundary = {e for e, uses in EDGE_RECORDS.items() if len(uses) == 1}; vertices = {control for _, _, face in FACE_RECORDS for control in face}
    if vertices != set(CONTROL_IDS) or (len(CELL_CATALOG), len(FACE_RECORDS), len(EDGE_RECORDS), len(boundary)) != (58, 104, 227, 38): raise ValueError("catalog count mismatch")
    if any(len(uses) not in (1, 2) for uses in EDGE_RECORDS.values()): raise ValueError("non-manifold base edge")
    directed = {(u[2], u[3]) for uses in EDGE_RECORDS.values() for u in uses}
    if any(len(uses) == 2 and (uses[0][2], uses[0][3]) == (uses[1][2], uses[1][3]) for uses in EDGE_RECORDS.values()): raise ValueError("base orientation conflict")
    declared = {tuple(sorted((loop[i], loop[(i + 1) % len(loop)]), key=lambda x: int(x[1:]))) for _, _, loop in PORT_INFO.values() for i in range(len(loop))}
    if declared != boundary or any((loop[i], loop[(i + 1) % len(loop)]) not in directed for _, _, loop in PORT_INFO.values() for i in range(len(loop))): raise ValueError("port loops do not cover base boundary")
    _junction_evidence(); boundary_vertices = {control for edge in boundary for control in edge}; incident_faces = {control: {index for index, (_, _, face) in enumerate(FACE_RECORDS) if control in face} for control in CONTROL_IDS}
    extraordinary = tuple(control for control in CONTROL_IDS if control not in boundary_vertices and len(incident_faces[control]) != 4)
    report = TopologyReport(len(vertices), len(EDGE_RECORDS), len(FACE_RECORDS), len(boundary), _boundary_components(boundary), len(vertices) - len(EDGE_RECORDS) + len(FACE_RECORDS), extraordinary)
    if (report.vertex_count, report.edge_count, report.face_count, report.boundary_edge_count, report.boundary_components, report.euler_characteristic, len(report.extraordinary_controls)) != (120, 227, 104, 38, 5, -3, 20): raise ValueError("derived catalog topology does not match the frozen counts")
    return report
CATALOG_REPORT = validate_catalogs()
def symbolic_topology(): return CONTROL_IDS, tuple(tuple(int(c[1:]) for c in f[2]) for f in FACE_RECORDS), tuple((name, tuple(int(c[1:]) for c in info[2])) for name, info in PORT_INFO.items())
@dataclass(frozen=True)
class Mesh:
    vertices: tuple[tuple[float, float, float], ...]; quads: tuple[tuple[int, int, int, int], ...]
    control_ids: tuple[str, ...]; formula_ids: tuple[str, ...]; dependencies: tuple[tuple[str, ...], ...]
    boundary_loops: tuple[tuple[str, tuple[int, ...]], ...]; triangles: tuple[tuple[int, int, int], ...] = ()
    level: int = 0; face_ids: tuple[str, ...] = (); face_owners: tuple[str, ...] = ()
    formula_records: tuple[Mapping[str, Any], ...] = (); vertex_records: tuple[Mapping[str, Any], ...] = (); source_stencils: tuple[tuple[int, ...], ...] = ()
@dataclass(frozen=True)
class SurfaceEvaluation: cage: Mesh; levels: tuple[Mesh, Mesh]
_FORMULA_RECORD_FIELDS = ("control_id", "lattice_key", "formula_id", "construction_owner", "index_parameters", "geometry_dependencies", "coordinate")
_FORMULA_LEDGER_SHA256 = "da8569de79e3c7479f94a94c5a2d45a9a131f623880c9301835a8e5f8e322bd5"
def _reference_e(center, u, q, lateral, anterior, posterior, exponent):
    def signed_power(value):
        magnitude = pow(abs(value), 2.0 / exponent)
        return 0.0 if magnitude == 0.0 else -magnitude if value < 0.0 else magnitude
    return (center[0] + lateral * signed_power(u), center[1], center[2] + (anterior if q >= 0.0 else posterior) * signed_power(q))
def _reference_control_coordinate(prepared, control):
    i, j, k = COORDINATE_BY_CONTROL[control]; q = float(k - 1)
    if j in (6, 7) and i in (2, 3):
        row = prepared["stations"]["neck_collar" if j == 6 else "neck_upper"]
        return _reference_e(row["C"], 2.0 * (float(i) - 2.5), q, row["rL"], row["rA"], row["rP"], 2.2)
    if j in (4, 5, 6) and i in (0, 1, 4, 5):
        side = "left" if i < 2 else "right"; sign = -1.0 if side == "left" else 1.0; a = 1 - i if side == "left" else i - 4; v = (float(j) - 4.0) / 2.0; row = prepared["shoulders"][side]
        inner = tuple((1.0 - v) * row["axilla"][axis] + v * row["peak"][axis] for axis in range(3)); outer = (row["arm_origin"][0] + sign * row["start_lateral"], row["arm_origin"][1] + (2.0 * v - 1.0) * row["start_up"] * .5, row["arm_origin"][2])
        center = tuple((1.0 - float(a)) * inner[axis] + float(a) * outer[axis] for axis in range(3)); inner_depth = .75 * row["start_forward"] if v == 0.0 else row["shoulder_depth"]; depth = (1.0 - float(a)) * inner_depth + float(a) * row["start_forward"]
        return _reference_e(center, 0.0, q, 0.0, depth, depth, 2.2)
    if j in (-1, 0):
        side = "left" if i <= 2 else "right"; row = prepared["hips"][side]; u = float(i) - (1.0 if side == "left" else 4.0); ps = row["P_s"]
        if j == -1: return (ps[0] + u * row["r_x"], ps[1], ps[2] + q * row["r_z"])
        low = prepared["stations"]["lower_pelvis"]; distance = low["C"][1] - ps[1]; maximum_x = low["rL"] - abs(ps[0] - low["C"][0]); hc = row["r_y"] + .25 * (distance - row["r_y"]); hs = .70 * hc
        jf = row["r_z"] + .20 * (low["rA"] - row["r_z"]); jb = row["r_z"] + .20 * (low["rP"] - row["r_z"])
        return (ps[0] + u * (row["r_x"] + (maximum_x - row["r_x"])), ps[1] + hs + (hc - hs) * (1.0 - u * u), ps[2] + .20 * (low["C"][2] - ps[2]) + (jf if q >= 0.0 else jb) * q)
    if j == 1:
        row = prepared["stations"]["upper_pelvis"] if i in (0, 5) else prepared["stations"]["lower_abdomen"]; u = (float(i) - 2.5) / 2.5
        center = row["C"] if i in (0, 5) else (row["C"][0], (prepared["stations"]["upper_pelvis"]["C"][1] + row["C"][1]) / 2.0, row["C"][2])
        return _reference_e(center, u, q, row["rL"], row["rA"], row["rP"], 2.6)
    u = (float(i) - 2.5) / 1.5
    if j == 5:
        low, high = (prepared["stations"][name] for name in ("lower_ribcage", "upper_ribcage_shoulder")); center = tuple((low["C"][axis] + high["C"][axis]) / 2.0 for axis in range(3)); radii = tuple((low[name] + high[name]) / 2.0 for name in ("rL", "rA", "rP"))
    else:
        row = prepared["stations"][("waist_abdomen", "upper_abdomen", "lower_ribcage")[j - 2]]; center, radii = row["C"], (row["rL"], row["rA"], row["rP"])
    return _reference_e(center, u, q, *radii, 2.6)
def _validate_cage_lineage(mesh, prepared):
    if type(mesh.formula_records) is not tuple: raise ValueError("L0 formula records are not a tuple")
    reference_vertices = tuple(tuple(float(x) for x in _reference_control_coordinate(prepared, control)) for control in CONTROL_IDS)
    if mesh.vertices != reference_vertices: raise ValueError("L0 vertices differ from independent prepared reference")
    ledger = []
    for index, (control, record) in enumerate(zip(CONTROL_IDS, mesh.formula_records)):
        if type(record) is not dict or set(record) != set(_FORMULA_RECORD_FIELDS): raise ValueError(f"L0 formula record schema mismatch at {index}")
        if type(record["coordinate"]) is not list or len(record["coordinate"]) != 3 or any(type(value) is not float or not isfinite(value) for value in record["coordinate"]) or record["coordinate"] != list(reference_vertices[index]): raise ValueError(f"L0 formula coordinate differs from independent prepared reference at {index}")
        ledger.append({field: record[field] for field in _FORMULA_RECORD_FIELDS[:-1]})
    if sha256(repr(tuple(ledger)).encode("ascii")).hexdigest() != _FORMULA_LEDGER_SHA256: raise ValueError("L0 formula ledger differs from the frozen contract")
    if mesh.formula_ids != tuple(record["formula_id"] for record in mesh.formula_records) or mesh.dependencies != tuple(tuple(record["geometry_dependencies"]) for record in mesh.formula_records): raise ValueError("L0 formula projections disagree with formula records")
    if mesh.source_stencils != tuple((index,) for index in range(120)): raise ValueError("L0 source stencils are not the identity")
    if mesh.vertex_records != tuple(_record(0, control, (control,), mesh.formula_records) for control in CONTROL_IDS): raise ValueError("L0 vertex records disagree with formula records")
def _check_faces(quads, vertex_count):
    if any(len(f) != 4 or len(set(f)) != 4 or any(type(x) is not int or not 0 <= x < vertex_count for x in f) for f in quads): raise ValueError("invalid quad catalog")
    uses = defaultdict(list)
    for fi, face in enumerate(quads):
        for slot, a in enumerate(face):
            b = face[(slot + 1) % 4]; uses[tuple(sorted((a, b)))].append((fi, a, b, slot))
    if any(len(v) not in (1, 2) for v in uses.values()): raise ValueError("non-manifold edge")
    if any(len(v) == 2 and v[0][1:3] == v[1][1:3] for v in uses.values()): raise ValueError("orientation conflict")
    return dict(uses)
def _validate_level_shape(mesh):
    if type(mesh) is not Mesh or type(mesh.level) is not int or mesh.level not in range(3): raise ValueError("invalid surface level")
    expected = ((120, 104, 227), (451, 416, 870), (1737, 1664, 3404))[mesh.level]; expected_ids = CONTROL_IDS if mesh.level == 0 else tuple(f"vertex.L{mesh.level}.v{i:04d}" for i in range(expected[0])); expected_faces = tuple(tuple(int(c[1:]) for c in row[2]) for row in FACE_RECORDS) if mesh.level == 0 else None
    expected_face_ids = tuple(row[0] for row in FACE_RECORDS) if mesh.level == 0 else tuple(f"face.L{mesh.level}.q{i:04d}" for i in range(expected[1])); expected_owners = tuple(row[1] for row in FACE_RECORDS) if mesh.level == 0 else tuple(FACE_RECORDS[i // (4 ** mesh.level)][1] for i in range(expected[1]))
    if (type(mesh.vertices) is not tuple or type(mesh.quads) is not tuple or mesh.control_ids != expected_ids or len(mesh.face_ids) != expected[1] or tuple(mesh.face_ids) != expected_face_ids or len(mesh.face_owners) != expected[1] or tuple(mesh.face_owners) != expected_owners or (expected_faces is not None and mesh.quads != expected_faces)): raise ValueError(f"L{mesh.level} identifier/catalog mismatch")
    if len(mesh.vertices) != expected[0] or any(type(point) is not tuple or len(point) != 3 or any(type(x) is not float or not isfinite(x) for x in point) for point in mesh.vertices): raise ValueError(f"L{mesh.level} coordinate shape mismatch")
    if any(type(face) is not tuple or len(face) != 4 for face in mesh.quads): raise ValueError(f"L{mesh.level} quad shape mismatch")
    if len(mesh.formula_ids) != expected[0] or len(mesh.dependencies) != expected[0] or len(mesh.vertex_records) != expected[0] or len(mesh.source_stencils) != expected[0] or len(mesh.formula_records) != 120: raise ValueError(f"L{mesh.level} lineage cardinality mismatch")
    if type(mesh.boundary_loops) is not tuple or tuple(name for name, _ in mesh.boundary_loops) != PORTS: raise ValueError(f"L{mesh.level} port loop catalog mismatch")
    loops = dict(mesh.boundary_loops); report = _generic.validate_topology(len(mesh.vertices), mesh.quads, loops, expected_faces)
    if (len(mesh.vertices), len(mesh.quads), report.edge_count) != expected: raise ValueError(f"L{mesh.level} topology counts mismatch")
    expected_triangles = tuple(t for face in mesh.quads for t in ((face[0], face[1], face[2]), (face[0], face[2], face[3])))
    if mesh.triangles != expected_triangles: raise ValueError(f"L{mesh.level} triangle catalog mismatch")
    return report
def _mesh_difference(actual, expected): return next((field for field in Mesh.__dataclass_fields__ if getattr(actual, field) != getattr(expected, field)), None)
def _reference_subdivision(parent, level):
    uses = _check_faces(parent.quads, len(parent.vertices)); edges = tuple(sorted(uses)); boundary, around, incident = defaultdict(set), defaultdict(list), defaultdict(list)
    for face_index, face in enumerate(parent.quads):
        for vertex in face: around[vertex].append(face_index)
    for edge, rows in uses.items():
        for vertex in edge: incident[vertex].append(edge)
        if len(rows) == 1: boundary[edge[0]].add(edge[1]); boundary[edge[1]].add(edge[0])
    face_points = [tuple(_div(_ordered(parent.vertices[v][axis] for v in face), 4.0) for axis in range(3)) for face in parent.quads]
    vertex_sources = tuple((i, *sorted(boundary[i])) if i in boundary else tuple(v for face_index in sorted(around[i]) for v in parent.quads[face_index]) for i in range(len(parent.vertices)))
    edge_sources = tuple(edge + tuple(v for face_index, *_ in sorted(uses[edge]) for v in parent.quads[face_index]) for edge in edges); sources = vertex_sources + edge_sources + tuple(parent.quads)
    vertices, formulas = [], []
    for i, point in enumerate(parent.vertices):
        if i in boundary:
            left, right = sorted(boundary[i]); value = tuple((6.0 * point[axis] + parent.vertices[left][axis] + parent.vertices[right][axis]) / 8.0 for axis in range(3)); formula = "subdivision.open-boundary-vertex"
        else:
            faces, local_edges = sorted(around[i]), sorted(incident[i]); count = len(faces); average_face = tuple(_ordered(face_points[f][axis] for f in faces) / float(count) for axis in range(3)); average_edge = tuple(_ordered((parent.vertices[a][axis] + parent.vertices[b][axis]) / 2.0 for a, b in local_edges) / float(len(local_edges)) for axis in range(3)); value = tuple((average_face[axis] + 2.0 * average_edge[axis] + float(count - 3) * point[axis]) / float(count) for axis in range(3)); formula = "subdivision.interior-vertex"
        vertices.append(value); formulas.append(formula)
    for edge in edges:
        a, b = edge
        if len(uses[edge]) == 1: value, formula = tuple((parent.vertices[a][axis] + parent.vertices[b][axis]) / 2.0 for axis in range(3)), "subdivision.boundary-edge"
        else:
            f0, f1 = sorted(row[0] for row in uses[edge]); value, formula = tuple((parent.vertices[a][axis] + parent.vertices[b][axis] + face_points[f0][axis] + face_points[f1][axis]) / 4.0 for axis in range(3)), "subdivision.interior-edge"
        vertices.append(value); formulas.append(formula)
    vertices.extend(face_points); formulas.extend("subdivision.face-point" for _ in parent.quads)
    edge_index = {edge: len(parent.vertices) + index for index, edge in enumerate(edges)}; face_start = len(parent.vertices) + len(edges)
    quads = tuple((vertex, edge_index[tuple(sorted((vertex, face[(corner + 1) % 4])))], face_start + face_index, edge_index[tuple(sorted((face[(corner - 1) % 4], vertex)))]) for face_index, face in enumerate(parent.quads) for corner, vertex in enumerate(face))
    loops = tuple((name, tuple(item for index, vertex in enumerate(loop) for item in (vertex, edge_index[tuple(sorted((vertex, loop[(index + 1) % len(loop)])))]))) for name, loop in parent.boundary_loops); ids = tuple(f"vertex.L{level}.v{i:04d}" for i in range(len(vertices)))
    def lineage(index, source):
        controls = tuple(sorted({control for parent_index in source for control in parent.vertex_records[parent_index]["base_control_contributors"]}, key=lambda value: int(value[1:]))); dependencies = tuple(sorted({item for control in controls for item in parent.formula_records[int(control[1:])]["geometry_dependencies"]})); contributing = {domain for control in controls for domain in (JUNCTION_INFO[CONTROL_OWNERS[control]][0] if CONTROL_OWNERS[control].startswith("junction.") else (CONTROL_OWNERS[control],))}
        return {"level": level, "vertex_id": ids[index], "base_control_contributors": controls, "geometry_dependency_union": dependencies, "contributor_domains": tuple(domain for domain in DOMAINS if domain in contributing)}
    records = tuple(lineage(index, source) for index, source in enumerate(sources)); dependencies = tuple(record["geometry_dependency_union"] for record in records); triangles = tuple(triangle for face in quads for triangle in ((face[0], face[1], face[2]), (face[0], face[2], face[3])))
    return Mesh(tuple(vertices), quads, ids, tuple(formulas), dependencies, loops, triangles, level, tuple(f"face.L{level}.q{i:04d}" for i in range(len(quads))), tuple(parent.face_owners[index // 4] for index in range(len(quads))), parent.formula_records, records, sources)
def _validate_derived_level(mesh, parent):
    report = _validate_level_shape(mesh)
    if type(parent) is not Mesh or parent.level != mesh.level - 1: raise ValueError(f"L{mesh.level} requires its immediately preceding parent")
    _validate_level_shape(parent); expected = _reference_subdivision(parent, mesh.level); difference = _mesh_difference(mesh, expected)
    if difference is not None: raise ValueError(f"L{mesh.level} differs from its parent-derived {difference}")
    return report
def _validate_level_structure_admitted(mesh, prepared, parent=None):
    report = _validate_level_shape(mesh)
    if mesh.level == 0:
        if parent is not None: raise ValueError("level 0 cannot have a parent")
        _validate_cage_lineage(mesh, prepared); return report
    if type(parent) is Mesh and parent.level == 0: _validate_cage_lineage(parent, prepared)
    return _validate_derived_level(mesh, parent)
def validate_level_structure(mesh, prepared=None, parent=None):
    cage = mesh if type(mesh) is Mesh and mesh.level == 0 else parent if type(parent) is Mesh and parent.level == 0 else None
    prepared = _infer_surface_prepared(cage) if prepared is None and cage is not None else prepared
    if prepared is None: raise ValueError("prepared input is required when no L0 cage is available")
    _admit_surface_prepared(prepared); return _validate_level_structure_admitted(mesh, prepared, parent)
def _evaluation_meshes(value):
    if type(value) is SurfaceEvaluation: cage, levels = value.cage, value.levels
    elif isinstance(value, Mapping) and set(value) == {"cage", "levels"}: cage, levels = value["cage"], value["levels"]
    elif type(value) in (tuple, list) and len(value) == 3: return tuple(value)
    else: raise ValueError("evaluation requires cage and levels 0 through 2")
    if type(levels) is not tuple or len(levels) != 2: raise ValueError("evaluation requires two derived levels")
    return (cage, *levels)
def validate_evaluation(value, prepared=None):
    meshes = _evaluation_meshes(value)
    prepared = _infer_surface_prepared(meshes[0]) if prepared is None else prepared; _admit_surface_prepared(prepared)
    _validate_level_structure_admitted(meshes[0], prepared); _validate_level_structure_admitted(meshes[1], prepared, meshes[0]); _validate_level_structure_admitted(meshes[2], prepared, meshes[1])
    return meshes
def topology_incidence(mesh):
    uses = _check_faces(mesh.quads, len(mesh.vertices)); return tuple({"edge": edge, "incident_faces": tuple(u[0] for u in uses[edge]), "slots": tuple(u[3] for u in uses[edge])} for edge in sorted(uses))
def level_topology(mesh):
    return {"level": mesh.level, "vertex_ids": mesh.control_ids, "face_ids": mesh.face_ids, "face_owners": mesh.face_owners, "faces": mesh.quads, "edges": topology_incidence(mesh), "boundary_loops": mesh.boundary_loops, "triangles": mesh.triangles}
def _component_dependencies(name, u, q):
    return {f"stations.{name}.C.{axis}" for axis in "xyz"} | ({f"stations.{name}.rL"} if u != 0.0 else set()) | ({f"stations.{name}.rA"} if q > 0.0 else set()) | ({f"stations.{name}.rP"} if q < 0.0 else set())
def _station(prepared, name):
    row = prepared["stations"][name]; return row["C"], row["rL"], row["rA"], row["rP"]
def _formula_for_control(prepared, control_id):
    i, j, k = COORDINATE_BY_CONTROL[control_id]; q = float(k - 1)
    if j in (6, 7) and i in (2, 3):
        name = "neck_collar" if j == 6 else "neck_upper"; C, rl, ra, rp = _station(prepared, name); u = _mul(2.0, _sub(float(i), 2.5)); point = _e(C, u, q, rl, ra, rp, 2.2)
        deps = _component_dependencies(name, u, q); formula = "formula.neck.stem"; params = {"i": i, "j": j, "k": k, "u": u, "q": q, "n": 2.2, "station_selector": name}
    elif j in (4, 5, 6) and i in (0, 1, 4, 5):
        side = "left" if i < 2 else "right"; sign = -1 if side == "left" else 1
        a = 1 - i if side == "left" else i - 4; v = _div(_sub(float(j), 4.0), 2.0); row = prepared["shoulders"][side]
        inner = _vlerp(row["axilla"], row["peak"], v); outer = _vadd(row["arm_origin"], (_mul(float(sign), row["start_lateral"]), _mul(_mul(_sub(_mul(2.0, v), 1.0), row["start_up"]), .5), 0.0)); inner_depth = _mul(.75, row["start_forward"]) if v == 0.0 else row["shoulder_depth"]
        depth = _add(_mul(float(1 - a), inner_depth), _mul(float(a), row["start_forward"])); point = _e(_vlerp(inner, outer, float(a)), 0.0, q, 0.0, depth, depth, 2.2); deps = set()
        if a == 0:
            if v < 1: deps.update(f"shoulders.{side}.axilla.{x}" for x in "xyz")
            if v > 0: deps.update(f"shoulders.{side}.peak.{x}" for x in "xyz")
            if q != 0 and v == 0: deps.add(f"shoulders.{side}.start_forward")
            if q != 0 and v > 0: deps.add(f"shoulders.{side}.shoulder_depth")
        else:
            deps.update(f"shoulders.{side}.arm_origin.{x}" for x in "xyz"); deps.add(f"shoulders.{side}.start_lateral");
            if v != .5: deps.add(f"shoulders.{side}.start_up")
            if q != 0: deps.add(f"shoulders.{side}.start_forward")
        formula = f"formula.shoulder.{side}"; params = {"i": i, "j": j, "k": k, "side": side, "a": float(a), "v": v, "q": q, "sign": sign}
    elif j in (-1, 0):
        side = "left" if i <= 2 else "right"; row = prepared["hips"][side]; u = _sub(float(i), 1.0 if side == "left" else 4.0)
        if j == -1:
            point = (_add(row["P_s"][0], _mul(u, row["r_x"])), row["P_s"][1], _add(row["P_s"][2], _mul(q, row["r_z"])))
            deps = {f"hips.{side}.P_s.{x}" for x in "xyz"} | ({f"hips.{side}.r_x"} if u != 0 else set()) | ({f"hips.{side}.r_z"} if q != 0 else set())
        else:
            low = prepared["stations"]["lower_pelvis"]; ps = row["P_s"]; D = _sub(low["C"][1], ps[1]); Mx = _sub(low["rL"], abs(_sub(ps[0], low["C"][0]))); Hc = _add(row["r_y"], _mul(.25, _sub(D, row["r_y"]))); Hs = _mul(.70, Hc); Jx = _add(row["r_x"], _sub(Mx, row["r_x"]))
            Jf = _add(row["r_z"], _mul(.20, _sub(low["rA"], row["r_z"]))); Jb = _add(row["r_z"], _mul(.20, _sub(low["rP"], row["r_z"]))); J0z = _lerp(ps[2], low["C"][2], .20); Qz = _mul(Jf if q >= 0 else Jb, q)
            point = (_add(ps[0], _mul(u, Jx)), _add(_add(ps[1], Hs), _mul(_sub(Hc, Hs), _sub(1., _mul(u, u)))), _add(J0z, Qz))
            deps = {f"hips.{side}.P_s.y", f"hips.{side}.P_s.z", f"hips.{side}.r_y", "stations.lower_pelvis.C.y", "stations.lower_pelvis.C.z"} | ({f"hips.{side}.P_s.x"} if not ((side == "left" and u == -1.) or (side == "right" and u == 1.)) else set()) | ({"stations.lower_pelvis.rL", "stations.lower_pelvis.C.x"} if u != 0 else set()) | ({f"hips.{side}.r_z", "stations.lower_pelvis.rA"} if q > 0 else {f"hips.{side}.r_z", "stations.lower_pelvis.rP"} if q < 0 else set())
        formula = f"formula.hip.{side}"; params = {"i": i, "j": j, "k": k, "side": side, "u": u, "q": q}
    else:
        if j == 1 and i in (0, 5):
            name, d = "upper_pelvis", 2.5; C, rl, ra, rp = _station(prepared, name); u = _div(_sub(float(i), 2.5), d); point = _e(C, u, q, rl, ra, rp, 2.6); deps = _component_dependencies(name, u, q); formula = "formula.axial.j1.edge"; selector = name
        elif j == 1:
            low, up = prepared["stations"]["lower_abdomen"], prepared["stations"]["upper_pelvis"]; d = 2.5; u = _div(_sub(float(i), 2.5), d); C = (low["C"][0], _div(_add(up["C"][1], low["C"][1]), 2.), low["C"][2]); point = _e(C, u, q, low["rL"], low["rA"], low["rP"], 2.6)
            deps = _component_dependencies("lower_abdomen", u, q) | {"stations.upper_pelvis.C.y"}; formula = "formula.axial.j1.interior"; selector = "virtual.upper_pelvis_y__lower_abdomen"
        else:
            d = 1.5; u = _div(_sub(float(i), 2.5), d)
            if j == 5:
                low, up = prepared["stations"]["lower_ribcage"], prepared["stations"]["upper_ribcage_shoulder"]; C = tuple(_div(_add(low["C"][x], up["C"][x]), 2.) for x in range(3)); radii = tuple(_div(_add(low[x], up[x]), 2.) for x in ("rL", "rA", "rP")); selector = "virtual.lower_ribcage__upper_ribcage_shoulder"
                point = _e(C, u, q, *radii, 2.6); deps = {f"stations.{name}.C.{x}" for name in ("lower_ribcage", "upper_ribcage_shoulder") for x in "xyz"}
                if u != 0: deps.update(f"stations.{name}.rL" for name in ("lower_ribcage", "upper_ribcage_shoulder"))
                if q > 0: deps.update(f"stations.{name}.rA" for name in ("lower_ribcage", "upper_ribcage_shoulder"))
                if q < 0: deps.update(f"stations.{name}.rP" for name in ("lower_ribcage", "upper_ribcage_shoulder"))
            else:
                selector = {2: "waist_abdomen", 3: "upper_abdomen", 4: "lower_ribcage"}[j]; C, rl, ra, rp = _station(prepared, selector); point = _e(C, u, q, rl, ra, rp, 2.6); deps = _component_dependencies(selector, u, q)
            formula = "formula.axial.station"
        params = {"i": i, "j": j, "k": k, "u": u, "q": q, "d": float(d), "n": 2.6, "station_selector": selector}
    return formula, tuple(sorted(deps)), tuple(point), params
def _formula_candidate_records_admitted(prepared):
    return tuple({"control_id": control, "lattice_key": list(COORDINATE_BY_CONTROL[control]), "formula_id": formula, "construction_owner": CONTROL_OWNERS[control], "index_parameters": params, "geometry_dependencies": list(deps), "coordinate": [float(x) for x in point]} for control in CONTROL_IDS for formula, deps, point, params in (_formula_for_control(prepared, control),))
def formula_candidate_records(prepared):
    prepared_projection.validate_prepared(prepared); return _formula_candidate_records_admitted(prepared)
def _record(level, vertex_id, contributors, formulas):
    controls = tuple(sorted(set(contributors), key=lambda x: int(x[1:]))); deps = tuple(sorted({d for c in controls for d in formulas[int(c[1:])]["geometry_dependencies"]}))
    contributing = {domain for c in controls for domain in (JUNCTION_INFO[CONTROL_OWNERS[c]][0] if CONTROL_OWNERS[c].startswith("junction.") else (CONTROL_OWNERS[c],))}; domains = tuple(domain for domain in DOMAINS if domain in contributing)
    return {"level": level, "vertex_id": vertex_id, "base_control_contributors": controls, "geometry_dependency_union": deps, "contributor_domains": domains}
def _contributors(mesh, indices): return [c for i in indices for c in mesh.vertex_records[i]["base_control_contributors"]]
def _incidence(mesh):
    uses = _check_faces(mesh.quads, len(mesh.vertices)); edges = tuple(sorted(uses)); boundary = defaultdict(set); faces = defaultdict(list); incident_edges = defaultdict(list)
    for fi, face in enumerate(mesh.quads):
        for v in face: faces[v].append(fi)
    for edge, rows in uses.items():
        for v in edge: incident_edges[v].append(edge)
        if len(rows) == 1: boundary[edge[0]].add(edge[1]); boundary[edge[1]].add(edge[0])
    return uses, edges, boundary, faces, incident_edges
def subdivision_incidence(mesh):
    uses, edges, boundary, faces, _incident_edges = _incidence(mesh); V, E, Q = len(mesh.vertices), len(edges), len(mesh.quads)
    stencils = tuple((i, *sorted(boundary[i])) if i in boundary else tuple(v for fi in sorted(faces[i]) for v in mesh.quads[fi]) for i in range(V))
    edge_stencils = tuple((edge, tuple(edge) + tuple(v for fi, *_ in sorted(uses[edge]) for v in mesh.quads[fi])) for edge in edges)
    face_stencils = tuple((fi, tuple(mesh.quads[fi])) for fi in range(Q))
    edge_indices = tuple((edge, V + i) for i, edge in enumerate(edges)); face_indices = tuple((fi, V + E + fi) for fi in range(Q))
    children = tuple((fi, corner, (face[corner], edge_indices[edges.index(tuple(sorted((face[corner], face[(corner + 1) % 4]))))][1], V + E + fi, edge_indices[edges.index(tuple(sorted((face[(corner - 1) % 4], face[corner]))))][1])) for fi, face in enumerate(mesh.quads) for corner in range(4))
    propagated = tuple((name, tuple(item for i, v in enumerate(loop) for item in (v, edge_indices[edges.index(tuple(sorted((v, loop[(i + 1) % len(loop)]))))][1])) ) for name, loop in mesh.boundary_loops)
    return {"source_level": mesh.level, "target_level": mesh.level + 1, "edges": tuple((e, tuple(u[0] for u in uses[e])) for e in edges), "boundary_edges": tuple(e for e in edges if len(uses[e]) == 1), "vertex_stencils": stencils, "edge_stencils": edge_stencils, "face_stencils": face_stencils, "edge_point_indices": edge_indices, "face_point_indices": face_indices, "child_emission": children, "propagated_port_loops": propagated}
def propagate_port_loops(mesh):
    return dict(subdivision_incidence(mesh)["propagated_port_loops"])
def junction_trace_inputs():
    evidence = _junction_evidence(); result = []
    for junction in JUNCTIONS:
        domains, (drop, tag_axes) = JUNCTION_INFO[junction]; trace = evidence[junction]["trace"]
        result.append({"junction_id": junction, "incident_domains": domains, "drop_axis": drop, "tag_axes": tag_axes, "base_control_ids": trace, "base_lattice_tags": tuple(tuple(COORDINATE_BY_CONTROL[c][{"i": 0, "j": 1}.get(axis, 2)] for axis in tag_axes) for c in trace)})
    return tuple(result)
def propagate_junction_tags(mesh, junction):
    if junction not in JUNCTIONS: raise ValueError("unknown junction")
    trace = _junction_evidence()[junction]["trace"]; meshes = (mesh.cage, *mesh.levels) if hasattr(mesh, "cage") else tuple(mesh) if isinstance(mesh, (list, tuple)) else (mesh,)
    if not meshes or len(meshes) > 3: raise ValueError("junction tag propagation requires levels 0 through 2")
    axes = JUNCTION_INFO[junction][1][1]; index = {c: i for i, c in enumerate(meshes[0].control_ids)}
    cycle = tuple(index[c] for c in trace); selected = {tuple(sorted((a, cycle[(i + 1) % len(cycle)]))) for i, a in enumerate(cycle)}
    tags = {i: tuple((COORDINATE_BY_CONTROL[meshes[0].control_ids[i]][{"i": 0, "j": 1, "k": 2}[axis]], 1) for axis in axes) for i in {v for edge in selected for v in edge}}
    result = (dict(sorted(tags.items())),)
    for level in range(1, len(meshes)):
        edge_points = dict(subdivision_incidence(meshes[level - 1])["edge_point_indices"]); out = dict(tags)
        for a, b in selected: out[edge_points[(a, b)]] = tuple(_half_tag(tags[a][axis], tags[b][axis]) for axis in range(2))
        selected = {tuple(sorted((a, edge_points[(a, b)]))) for a, b in selected} | {tuple(sorted((edge_points[(a, b)], b))) for a, b in selected}; tags = out; result += (dict(sorted(tags.items())),)
    return result
def _half_tag(left, right):
    numerator = left[0] * right[1] + right[0] * left[1]; denominator = 2 * left[1] * right[1]; common = gcd(abs(numerator), denominator)
    return numerator // common, denominator // common
def _build_cage_admitted(prepared):
    records = _formula_candidate_records_admitted(prepared); quads = tuple(tuple(int(c[1:]) for c in f[2]) for f in FACE_RECORDS)
    loops = tuple((name, tuple(int(c[1:]) for c in info[2])) for name, info in PORT_INFO.items())
    triangles = tuple(t for f in quads for t in ((f[0], f[1], f[2]), (f[0], f[2], f[3])))
    mesh = Mesh(tuple(tuple(r["coordinate"]) for r in records), quads, CONTROL_IDS, tuple(r["formula_id"] for r in records), tuple(tuple(r["geometry_dependencies"]) for r in records), loops, triangles, 0, tuple(f[0] for f in FACE_RECORDS), tuple(f[1] for f in FACE_RECORDS), records, tuple(_record(0, c, (c,), records) for c in CONTROL_IDS), tuple((i,) for i in range(120)))
    _validate_level_structure_admitted(mesh, prepared); return mesh
def build_cage(prepared):
    prepared_projection.validate_prepared(prepared); return _build_cage_admitted(prepared)
def _subdivide_once(mesh, level, points=None):
    if type(level) is not int or level not in (1, 2) or mesh.level != level - 1: raise ValueError("subdivision level must follow level 0,1 order")
    inc = subdivision_incidence(mesh); uses, edges, boundary, faces, incident_edges = _incidence(mesh); points = mesh.vertices if points is None else points
    face_points = [tuple(_div(_ordered(points[v][axis] for v in face), 4.) for axis in range(3)) for face in mesh.quads]
    vertices, stencils, formulas, deps = [], list(inc["vertex_stencils"]), [], []
    for i, point in enumerate(points):
        source = stencils[i]
        if i in boundary: n0, n1 = sorted(boundary[i]); value = tuple(_div(_add(_add(_mul(6., point[a]), points[n0][a]), points[n1][a]), 8.) for a in range(3)); formula = "subdivision.open-boundary-vertex"
        else:
            fs = sorted(faces[i]); es = sorted(incident_edges[i]); n = len(fs); F = tuple(_div(_ordered(face_points[f][a] for f in fs), float(n)) for a in range(3)); R = tuple(_div(_ordered(_div(_add(points[x][a], points[y][a]), 2.) for x, y in es), float(len(es))) for a in range(3))
            t0 = tuple(_mul(2., x) for x in R); t1 = tuple(_add(F[a], t0[a]) for a in range(3)); t2 = tuple(_mul(float(n - 3), point[a]) for a in range(3)); value = tuple(_div(_add(t1[a], t2[a]), float(n)) for a in range(3)); formula = "subdivision.interior-vertex"
        vertices.append(value); formulas.append(formula); base = _contributors(mesh, source); deps.append(tuple(sorted({d for c in base for d in mesh.formula_records[int(c[1:])]["geometry_dependencies"]})))
    for edge in edges:
        a, b = edge
        if len(uses[edge]) == 1: value = tuple(_div(_add(points[a][x], points[b][x]), 2.) for x in range(3)); formula = "subdivision.boundary-edge"
        else: f0, f1 = sorted(u[0] for u in uses[edge]); value = tuple(_div(_add(_add(_add(points[a][x], points[b][x]), face_points[f0][x]), face_points[f1][x]), 4.) for x in range(3)); formula = "subdivision.interior-edge"
        vertices.append(value); formulas.append(formula); base = _contributors(mesh, inc["edge_stencils"][edges.index(edge)][1]); deps.append(tuple(sorted({d for c in base for d in mesh.formula_records[int(c[1:])]["geometry_dependencies"]})))
    for fi, face in enumerate(mesh.quads):
        vertices.append(face_points[fi]); formulas.append("subdivision.face-point"); base = _contributors(mesh, face); deps.append(tuple(sorted({d for c in base for d in mesh.formula_records[int(c[1:])]["geometry_dependencies"]})))
    quads = tuple(child[2] for child in inc["child_emission"]); face_ids = tuple(f"face.L{level}.q{i:04d}" for i in range(len(quads))); owners = tuple(mesh.face_owners[fi] for fi, _, _ in inc["child_emission"]); loops = inc["propagated_port_loops"]; ids = tuple(f"vertex.L{level}.v{i:04d}" for i in range(len(vertices)))
    records = tuple(_record(level, ids[i], _contributors(mesh, source), mesh.formula_records) for i, source in enumerate(stencils))
    records += tuple(_record(level, ids[index], _contributors(mesh, source), mesh.formula_records) for (edge, source), (_, index) in zip(inc["edge_stencils"], inc["edge_point_indices"]))
    records += tuple(_record(level, ids[index], _contributors(mesh, face), mesh.formula_records) for (fi, face), (_, index) in zip(inc["face_stencils"], inc["face_point_indices"])); triangles = tuple(t for f in quads for t in ((f[0], f[1], f[2]), (f[0], f[2], f[3])))
    complete_stencils = tuple(stencils) + tuple(source for _, source in inc["edge_stencils"]) + tuple(face for _, face in inc["face_stencils"]); return Mesh(tuple(vertices), quads, ids, tuple(formulas), tuple(deps), loops, triangles, level, face_ids, owners, mesh.formula_records, records, complete_stencils)
def subdivide(mesh, level=1):
    if type(level) is not int or level not in (1, 2) or type(mesh) is not Mesh or mesh.level >= level: raise ValueError("the frozen surface has exactly two ordered subdivision levels")
    result = mesh
    for target in range(mesh.level + 1, level + 1):
        parent = result; result = _subdivide_once(parent, target); _validate_derived_level(result, parent)
    return result
def _evaluate_cage(cage, prepared):
    level1 = subdivide(cage, 1); level2 = subdivide(level1, 2); evaluation = SurfaceEvaluation(cage, (level1, level2)); validate_evaluation(evaluation, prepared); return evaluation
def evaluate(prepared, levels=2):
    if type(levels) is not int or levels != 2: raise ValueError("the frozen neutral surface evaluates exactly two levels")
    return _evaluate_cage(build_cage(prepared), prepared)
_MUST_AFFECT = (
    ("left.r_y", "hips.left.r_y"), ("right.r_y", "hips.right.r_y"), ("lower_pelvis.L_y", "stations.lower_pelvis.C.y"), ("lower_pelvis.C_z", "stations.lower_pelvis.C.z"), ("left.r_x", "hips.left.r_x"), ("right.r_x", "hips.right.r_x"),
    ("lower_pelvis.R_x", "stations.lower_pelvis.rL"), ("left.r_z", "hips.left.r_z"), ("right.r_z", "hips.right.r_z"), ("lower_pelvis.R_f", "stations.lower_pelvis.rA"), ("lower_pelvis.R_b", "stations.lower_pelvis.rP"),
    ("left.thigh_start_x", "hips.left.P_s.x"), ("left.thigh_start_y", "hips.left.P_s.y"), ("left.thigh_start_z", "hips.left.P_s.z"), ("right.thigh_start_x", "hips.right.P_s.x"), ("right.thigh_start_y", "hips.right.P_s.y"), ("right.thigh_start_z", "hips.right.P_s.z"),
    ("neck_collar.C_y", "stations.neck_collar.C.y"), ("neck_collar.rL", "stations.neck_collar.rL"), ("neck_upper.C_y", "stations.neck_upper.C.y"), ("neck_upper.rL", "stations.neck_upper.rL"),
    ("left.axilla_x", "shoulders.left.axilla.x"), ("left.axilla_y", "shoulders.left.axilla.y"), ("right.axilla_x", "shoulders.right.axilla.x"), ("right.axilla_y", "shoulders.right.axilla.y"), ("left.peak_y", "shoulders.left.peak.y"), ("right.peak_y", "shoulders.right.peak.y"),
    ("left.start_lateral", "shoulders.left.start_lateral"), ("right.start_lateral", "shoulders.right.start_lateral"), ("left.start_up", "shoulders.left.start_up"), ("right.start_up", "shoulders.right.start_up"),
    ("left.shoulder_depth", "shoulders.left.shoulder_depth"), ("right.shoulder_depth", "shoulders.right.shoulder_depth"))
MUST_AFFECT_PARAMETER_IDS = tuple(parameter for parameter, _ in _MUST_AFFECT)
MUST_AFFECT_COMPONENTS = dict(_MUST_AFFECT)
_MUST_AFFECT_PATHS = {parameter: tuple("xyz".index(axis) if len(axis) == 1 and axis in "xyz" else axis for axis in component.split(".")) for parameter, component in _MUST_AFFECT}
_PERTURBATION_DELTA = float.fromhex("0x1.47ae147ae147bp-7")
PERTURBATION_DELTA_M = _PERTURBATION_DELTA
def _path_get(value, path):
    for key in path: value = value[key]
    return value
def _path_set(value, path, replacement): _path_get(value, path[:-1])[path[-1]] = replacement
def _admit_surface_prepared(prepared):
    try:
        prepared_projection.validate_prepared(prepared); return prepared
    except prepared_projection.PreparedProjectionError:
        canonical = prepared_projection.prepare_standard_neutral(); canonical_bytes = prepared_projection.canonical_json_bytes(canonical); matches = 0
        for path in _MUST_AFFECT_PATHS.values():
            try:
                baseline, candidate = _path_get(canonical, path), _path_get(prepared, path)
                if type(candidate) is not float or candidate != float(baseline + _PERTURBATION_DELTA): continue
                restored = copy.deepcopy(prepared); _path_set(restored, path, baseline); matches += prepared_projection.canonical_json_bytes(restored) == canonical_bytes
            except (KeyError, IndexError, TypeError, ValueError, OverflowError): continue
        if matches != 1: raise
        return prepared
def _surface_prepared_candidates():
    canonical = prepared_projection.prepare_standard_neutral(); yield canonical
    for path in _MUST_AFFECT_PATHS.values():
        candidate = copy.deepcopy(canonical); baseline = _path_get(candidate, path); _path_set(candidate, path, float(baseline + _PERTURBATION_DELTA)); yield candidate
def _infer_surface_prepared(cage):
    if type(cage) is not Mesh: raise ValueError("prepared inference requires an L0 cage")
    matches = []
    for candidate in _surface_prepared_candidates():
        try: _validate_cage_lineage(cage, candidate)
        except (ValueError, TypeError, IndexError): continue
        matches.append(candidate)
    if len(matches) != 1: raise ValueError("L0 cage does not identify exactly one frozen prepared input")
    return matches[0]
def perturb_prepared(prepared, parameter_id):
    if type(parameter_id) is not str or parameter_id not in _MUST_AFFECT_PATHS: raise ValueError("parameter_id is not one of the 33 frozen must-affect parameters")
    prepared_projection.validate_prepared(prepared); path = _MUST_AFFECT_PATHS[parameter_id]; component = MUST_AFFECT_COMPONENTS[parameter_id]; baseline = _path_get(prepared, path)
    if type(baseline) is not float or not isfinite(baseline): raise ValueError(f"{component} is not binary64")
    candidate = copy.deepcopy(prepared); changed = float(baseline + _PERTURBATION_DELTA); _path_set(candidate, path, changed)
    if _path_get(candidate, path) != changed: raise ValueError("perturbation did not change its selected component")
    restored = copy.deepcopy(candidate); _path_set(restored, path, baseline)
    if prepared_projection.canonical_json_bytes(restored) != prepared_projection.canonical_json_bytes(prepared): raise ValueError("perturbation changed more than its selected component")
    return candidate
def build_perturbed_cage(prepared, parameter_id): return _build_cage_admitted(perturb_prepared(prepared, parameter_id))
def evaluate_perturbation(prepared, parameter_id, levels=2):
    if type(levels) is not int or levels != 2: raise ValueError("the frozen surface evaluates exactly two levels")
    candidate = perturb_prepared(prepared, parameter_id); return _evaluate_cage(_build_cage_admitted(candidate), candidate)
evaluate_perturbed = evaluate_perturbation
@dataclass(frozen=True)
class _Dual:
    value: float
    derivative: Fraction
    def __add__(self, other): return _Dual(self.value + _value(other), self.derivative + _derivative(other))
    def __radd__(self, other): return self + other
    def __sub__(self, other): return _Dual(self.value - _value(other), self.derivative - _derivative(other))
    def __rsub__(self, other): return _Dual(_value(other) - self.value, _derivative(other) - self.derivative)
    def __mul__(self, other): return _Dual(self.value * _value(other), self.derivative * _rational(_value(other)) + _rational(self.value) * _derivative(other))
    def __rmul__(self, other): return self * other
    def __truediv__(self, other): return _Dual(self.value / _value(other), (self.derivative * _rational(_value(other)) - _rational(self.value) * _derivative(other)) / (_rational(_value(other)) ** 2))
    def __rtruediv__(self, other): return _Dual(_value(other) / self.value, (_derivative(other) * _rational(self.value) - _rational(_value(other)) * self.derivative) / (_rational(self.value) ** 2))
    def __abs__(self): return _Dual(abs(self.value), self.derivative if self.value > 0 else -self.derivative if self.value < 0 else 0.0)
def _value(x): return x.value if isinstance(x, _Dual) else x
def _derivative(x): return x.derivative if isinstance(x, _Dual) else Fraction(0)
def _analytic_components(prepared):
    source = {record["prepared_component"] for record in prepared_projection.source_binding_records()}; formula = {dependency for control in CONTROL_IDS for dependency in _formula_for_control(prepared, control)[1]}
    if not formula <= source: raise ValueError("formula authority names a component outside frozen source bindings")
    return formula
def analytic_control_derivatives(prepared, component):
    _admit_surface_prepared(prepared)
    if component not in _analytic_components(prepared): raise ValueError(f"unknown prepared component: {component}")
    dual = copy.deepcopy(prepared); parts = component.split("/") if "/" in component else component.split("."); leaf = parts[-1]
    if leaf in "xyz" and len(parts) >= 2:
        target = dual
        for part in parts[:-2]: target = target[part]
        vector = list(target[parts[-2]]); vector["xyz".index(leaf)] = _Dual(vector["xyz".index(leaf)], Fraction(1)); target[parts[-2]] = tuple(vector)
    else:
        target = dual
        for part in parts[:-1]: target = target[part]
        target[leaf] = _Dual(target[leaf], Fraction(1))
    result = []
    for control in CONTROL_IDS:
        _, _, point, _ = _formula_for_control(dual, control); result.append(tuple(_derivative(x) for x in point))
    return tuple(result)
def _propagate_values(mesh, values, level): return _subdivide_once(mesh, level, values).vertices
def propagate_derivative(mesh, derivatives, level=2):
    if len(derivatives) != len(mesh.vertices): raise ValueError("derivative vector count mismatch")
    result, current = tuple(tuple(_rational(x) for x in p) for p in derivatives), mesh
    for target in range(mesh.level + 1, level + 1): result = _propagate_values(current, result, target); current = subdivide(current, target)
    return result
def predicted_support(prepared, component): cage = build_cage(prepared); derivative = analytic_control_derivatives(prepared, component); level2 = propagate_derivative(cage, derivative, 2); return tuple(i for i, point in enumerate(level2) if any(value != 0.0 for value in point))
analytic_derivative_support = predicted_support
causal_support = predicted_support
validate_topology, build_surface = validate_catalogs, build_cage
__all__ = ["CELL_CATALOG", "CONTROL_BY_COORDINATE", "CONTROL_DOMAIN_INCIDENTS", "CONTROL_IDS", "CONTROL_JUNCTION_INCIDENTS", "CONTROL_OWNERS", "COORDINATE_BY_CONTROL", "DOMAINS", "EDGE_RECORDS", "FACE_CATALOG", "FACE_RECORDS", "FORMULAS", "JUNCTIONS", "JUNCTION_INFO", "JUNCTION_TRACES", "MUST_AFFECT_COMPONENTS", "MUST_AFFECT_PARAMETER_IDS", "PERTURBATION_DELTA_M", "PORTS", "PORT_INFO", "SPECIAL_CASE_IDS", "Mesh", "SurfaceEvaluation", "analytic_control_derivatives", "analytic_derivative_support", "build_cage", "build_perturbed_cage", "causal_support", "evaluate", "evaluate_perturbation", "evaluate_perturbed", "formula_candidate_records", "junction_trace_inputs", "level_topology", "perturb_prepared", "predicted_support", "propagate_derivative", "propagate_junction_tags", "propagate_port_loops", "subdivide", "subdivision_incidence", "symbolic_topology", "topology_incidence", "validate_catalogs", "validate_evaluation", "validate_level_structure"]
