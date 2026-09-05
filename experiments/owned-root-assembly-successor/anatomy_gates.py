"""Independent anatomy selectors, gates, thresholds, and production fixtures; owns no surface, chart, transition, sample, or summary construction."""
from __future__ import annotations

from collections import defaultdict, namedtuple
from collections.abc import Mapping
from fractions import Fraction
from math import isfinite, sqrt

try:
    import owned_root_surface as surface
except ImportError:  # pragma: no cover
    from . import owned_root_surface as surface
LEVEL_COUNTS = ((120, 104, 227), (451, 416, 870), (1737, 1664, 3404)); DOMAINS, PORTS, JUNCTIONS = surface.DOMAINS, surface.PORTS, surface.JUNCTIONS
PAIRS = {j: tuple(surface.JUNCTION_INFO[j][0]) for j in JUNCTIONS}; DROPS = {j: surface.JUNCTION_INFO[j][1] for j in JUNCTIONS}
ANATOMY_METRICS = ("shoulder_surface_descent", "arm_port_descent", "axillary_turn_depth", "axillary_path_stretch", "axillary_inboard_recess", "axillary_downward_recess", "pelvic_vertical_wrap", "pelvic_lateral_ratio", "front_depth_wrap", "back_depth_wrap")
CLEARANCES = ("neck", "left_axilla", "right_axilla", "groin", "medial_thigh")
THRESHOLD = 0.05
class AnatomyGateError(ValueError):
    def __init__(self, message, diagnostics=()):
        self.diagnostics = tuple(sorted(map(str, diagnostics))); super().__init__(message + (": " + ", ".join(self.diagnostics) if self.diagnostics else ""))
def _fail(message, *diagnostics): raise AnatomyGateError(message, diagnostics)
def _get(value, name): return value[name] if isinstance(value, Mapping) else getattr(value, name)
def _edges(mesh):
    result = defaultdict(list)
    for fi, face in enumerate(_get(mesh, "quads")):
        for slot, a in enumerate(face): result[tuple(sorted((a, face[(slot + 1) % 4])))].append((fi, slot))
    return result
def _chart_path(level, index): return () if level == 0 else (index % 4,) if level == 1 else ((index % 16) // 4, index % 4)
def _chart_id(level, index): base = index // (4 ** level); path = _chart_path(level, index); return f"chart.q{base:03d}" if not path else f"chart.q{base:03d}/L{level}.s{'.s'.join(map(str, path))}"
def _chart_uv(path):
    corners = ((Fraction(0), Fraction(0)), (Fraction(1), Fraction(0)), (Fraction(1), Fraction(1)), (Fraction(0), Fraction(1)))
    for child in path:
        mids = tuple(tuple((left + right) / 2 for left, right in zip(corners[i], corners[(i + 1) % 4])) for i in range(4)); center = tuple(sum((point[axis] for point in corners), Fraction(0)) / 4 for axis in range(2)); corners = ((corners[0], mids[0], center, mids[3]), (corners[1], mids[1], center, mids[0]), (corners[2], mids[2], center, mids[1]), (corners[3], mids[3], center, mids[2]))[child]
    return corners
def _dyadic(value, expected, where):
    if not isinstance(value, Mapping) or set(value) != {"numerator", "denominator"}: _fail("chart dyadic schema mismatch", where)
    numerator, denominator = value["numerator"], value["denominator"]
    if type(numerator) is not int or type(denominator) is not int or denominator <= 0 or denominator & (denominator - 1): _fail("chart dyadic grammar mismatch", where)
    reduced = Fraction(numerator, denominator); invalid = reduced.numerator != numerator or reduced.denominator != denominator or reduced != expected
    if invalid: _fail("chart dyadic value or reduction mismatch", where)
def _chart_levels(charts, levels):
    if isinstance(charts, Mapping) and "chart_records" not in charts: _fail("chart ancestry is required")
    if isinstance(charts, Mapping): charts = charts["chart_records"]
    if not isinstance(charts, (list, tuple)): _fail("chart ancestry is required")
    if len(charts) == 3 and all(isinstance(item, (list, tuple)) for item in charts): by_level = tuple(tuple(item) for item in charts)
    else:
        if any(not isinstance(item, Mapping) or "level" not in item for item in charts): _fail("chart ancestry record is malformed")
        if any(not isinstance(item.get("chart_id"), str) for item in charts): _fail("chart ID is malformed")
        if any(type(item["level"]) is not int or item["level"] not in range(3) for item in charts): _fail("chart level is malformed or out of range")
        if tuple(item["chart_id"] for item in charts) != tuple(sorted((item["chart_id"] for item in charts), key=str.encode)): _fail("chart records are not sorted by chart ID")
        by_level = tuple(tuple(item for item in charts if item["level"] == level) for level in range(3))
    seen = set(); result = []
    for level, (mesh, records) in enumerate(zip(levels, by_level)):
        if len(records) != len(_get(mesh, "quads")): _fail("chart ancestry cardinality mismatch", f"L{level}")
        checked = []
        for index, chart in enumerate(records):
            where = f"L{level}[{index}]"
            if not isinstance(chart, Mapping) or set(chart) != {"chart_id", "level", "face_id", "base_face_id", "construction_owner", "corners"}: _fail("chart ancestry schema mismatch", where)
            if type(chart["level"]) is not int or chart["level"] != level: _fail("chart level is malformed or misplaced", where)
            expected_id = _chart_id(level, index); base = surface.FACE_RECORDS[index // (4 ** level)][0]
            face_id, owner = _get(mesh, "face_ids")[index], _get(mesh, "face_owners")[index]
            if (chart["chart_id"], chart["level"], chart["face_id"], chart["base_face_id"], chart["construction_owner"]) != (expected_id, level, face_id, base, owner): _fail("chart ancestry disagrees with public face authority", where)
            if chart["chart_id"] in seen: _fail("chart ancestry has duplicate IDs", where)
            seen.add(chart["chart_id"]); corners = chart["corners"]; face = _get(mesh, "quads")[index]
            if not isinstance(corners, (list, tuple)) or len(corners) != 4: _fail("chart corner incidence is incomplete", where)
            for corner, (entry, vertex) in enumerate(zip(corners, face)):
                corner_where = f"{where}c{corner}"
                if not isinstance(entry, Mapping) or set(entry) != {"vertex_id", "u", "v"} or entry["vertex_id"] != _get(mesh, "control_ids")[vertex]: _fail("chart corner incidence disagrees with public topology", corner_where)
                expected_u, expected_v = _chart_uv(_chart_path(level, index))[corner]
                _dyadic(entry["u"], expected_u, corner_where + ".u"); _dyadic(entry["v"], expected_v, corner_where + ".v")
            checked.append(chart)
        result.append(tuple(checked))
    if len(result) != 3 or len(seen) != sum(len(row) for row in result): _fail("chart ancestry is not a three-level sequence")
    return tuple(result)
def validate_evaluated_surface(value, geometry, chart_summary=None):
    try: levels = surface.validate_evaluation(value, geometry)
    except (ValueError, IndexError, TypeError) as exc: _fail("evaluated surface admission is invalid", str(exc))
    for level, mesh in enumerate(levels):
        if (len(mesh.vertices), len(mesh.quads), len(surface.topology_incidence(mesh))) != LEVEL_COUNTS[level]: _fail("evaluated surface count mismatch", f"L{level}")
    if chart_summary is not None: _chart_levels(chart_summary, levels)
    return levels
def _context(value, geometry, chart_summary):
    if chart_summary is None: _fail("chart ancestry is required for anatomy selectors")
    levels = validate_evaluated_surface(value, geometry); return levels, _chart_levels(chart_summary, levels)
def _actual_feature_edges(mesh, charts, feature, expected=None):
    edges = _edges(mesh)
    if feature in PORTS:
        boundary = {edge for edge, uses in edges.items() if len(uses) == 1}; groups = []; unseen = set(boundary)
        while unseen:
            group, todo = set(), [unseen.pop()]
            while todo:
                edge = todo.pop(); group.add(edge); neighbours = {other for other in unseen if set(edge) & set(other)}
                unseen.difference_update(neighbours); todo.extend(neighbours)
            groups.append(group)
        expected = _base_feature_edges(feature, mesh) if expected is None else expected
        if len(groups) == len(PORTS) and sum(group == expected for group in groups) == 1: return expected
        return boundary
    owners = tuple(c["construction_owner"] for c in charts); result = set(); matches = PAIRS[feature]
    for edge, uses in edges.items():
        if len(uses) == 2 and frozenset((owners[uses[0][0]], owners[uses[1][0]])) == frozenset(matches): result.add(edge)
    return result
def _base_feature_edges(feature, mesh):
    ids = surface.PORT_INFO[feature][2] if feature in PORTS else surface.JUNCTION_TRACES[feature]; indexes = {name: i for i, name in enumerate(mesh.control_ids)}; cycle = tuple(indexes[name] for name in ids); return {tuple(sorted((a, cycle[(i + 1) % len(cycle)]))) for i, a in enumerate(cycle)}
def _new_selector_cache(): return {"incidence": {}, "feature_edges": {}}
def _cached_incidence(levels, level, cache): return cache["incidence"][level] if level in cache["incidence"] else cache["incidence"].setdefault(level, surface.subdivision_incidence(levels[level]))
def _feature_edge_levels(levels, charts, feature, target, cache=None):
    cache = _new_selector_cache() if cache is None else cache; cached = cache["feature_edges"].setdefault(feature, [])
    if not cached: selected = _base_feature_edges(feature, levels[0]); actual = _actual_feature_edges(levels[0], charts[0], feature, selected); _fail("incidence selector disagrees with catalog", f"{feature}:L0") if selected != actual else cached.append(frozenset(selected))
    for level in range(len(cached), target + 1):
        incidence = _cached_incidence(levels, level - 1, cache); edge_point = dict(incidence["edge_point_indices"]); expected = set()
        for a, b in cached[-1]: mid = edge_point[(a, b)]; expected.update((tuple(sorted((a, mid))), tuple(sorted((mid, b)))))
        actual = _actual_feature_edges(levels[level], charts[level], feature, expected)
        _fail("propagated incidence selector disagrees with catalog", f"{feature}:L{level}") if expected != actual else cached.append(frozenset(expected))
    return tuple(set(edges) for edges in cached[:target + 1])
def _feature_edges(levels, charts, feature, target, cache=None): return _feature_edge_levels(levels, charts, feature, target, cache)[target]
def _tag(control, feature):
    coords = surface.COORDINATE_BY_CONTROL[control]; axes = (0, 2) if feature in PORTS and feature in ("port.neck", "port.left_thigh", "port.right_thigh") else (1, 2) if feature in PORTS else tuple(0 if x == "i" else 1 if x == "j" else 2 for x in DROPS[feature][1]); return tuple(Fraction(coords[a]) for a in axes)
def _feature_tags(levels, charts, feature, target, cache=None):
    cache = _new_selector_cache() if cache is None else cache; edge_levels = _feature_edge_levels(levels, charts, feature, target, cache)
    base = {c: _tag(levels[0].control_ids[c], feature) for edge in edge_levels[0] for c in edge}; tags = base
    for level in range(1, target + 1):
        edge_points = dict(_cached_incidence(levels, level - 1, cache)["edge_point_indices"]); out = {i: tag for i, tag in tags.items()}
        for edge in edge_levels[level - 1]: out[edge_points[edge]] = tuple((tags[edge[0]][a] + tags[edge[1]][a]) / 2 for a in range(2))
        expected = {v for edge in edge_levels[level] for v in edge}
        if set(out) != expected: _fail("feature tag propagation mismatch", f"{feature}:L{level}")
        tags = out
    return tags
def _trace(levels, charts, feature, level, cache=None):
    if feature not in PORTS + JUNCTIONS or level not in range(3): _fail("unknown anatomy selector", feature)
    tags = _feature_tags(levels, charts, feature, level, cache); result = {tag: tuple(levels[level].vertices[index]) for index, tag in tags.items()}
    if len(result) != len(tags): _fail("ambiguous anatomy selector", feature)
    return dict(sorted(result.items()))
def select_trace(value, geometry, feature, level=2, chart_summary=None):
    levels, charts = _context(value, geometry, chart_summary); return _trace(levels, charts, feature, level, _new_selector_cache())
def _vec(value, name):
    if not isinstance(value, (tuple, list)) or len(value) != 3 or any(type(x) is not float or not isfinite(x) for x in value): raise ValueError(f"{name} must be a finite binary64 vector3")
    return tuple(value)
def _sub(a, b): return tuple(float(a[i] - b[i]) for i in range(3))
def _xy(v): return sqrt(float(v[0] * v[0] + v[1] * v[1]))
def _div(a, b): return float(a / b)
AxillaryPredicateResult = namedtuple("AxillaryPredicateResult", "passed stage turn_depth path_stretch lr ls lc", defaults=(None, None, None))
class AxillaryPredicateError(ValueError):
    def __init__(self, stage, lr=None, ls=None, lc=None):
        self.stage, self.lr, self.ls, self.lc = stage, lr, ls, lc; super().__init__(f"axillary predicate failed at step {stage}")
_TURN = float.fromhex("0x1.999999999999ap-5"); _STRETCH = float.fromhex("0x1.4000000000000p+1")
def evaluate_axillary_predicate(side, U, A, O, _turn=_TURN, _stretch=_STRETCH):
    if side not in ("left", "right"): raise ValueError("axillary side must be left or right")
    U, A, O = _vec(U, "U"), _vec(A, "A"), _vec(O, "O"); r, s, c = _sub(A, U), _sub(O, A), _sub(O, U)
    lr, ls, lc = _xy(r), _xy(s), _xy(c)
    for step, value, name in ((3, lr, "lr"), (4, ls, "ls"), (5, lc, "lc")):
        if not isfinite(value) or value <= 0: raise AxillaryPredicateError(step, lr, ls, lc)
    path = float(lr + ls)
    if not isfinite(path) or path <= 0: raise ValueError("axillary predicate failed at step 6: path")
    cross = float(c[0] * r[1] - c[1] * r[0]); oriented = cross if side == "left" else float(-cross)
    turn, stretch = _div(oriented, path), _div(path, lc)
    if not all(isfinite(x) for x in (turn, stretch)): raise ValueError("axillary predicate failed at step 7: non-finite measure")
    if turn < _turn: return AxillaryPredicateResult(False, 8, turn, stretch, lr, ls, lc)
    if stretch > _stretch: return AxillaryPredicateResult(False, 9, turn, stretch, lr, ls, lc)
    return AxillaryPredicateResult(True, None, turn, stretch, lr, ls, lc)
def axillary_predicate(side, U, A, O): return evaluate_axillary_predicate(side, U, A, O).passed
def evaluate_axillary_scalars(turn_depth, path_stretch, _turn=_TURN, _stretch=_STRETCH):
    if type(turn_depth) is not float or type(path_stretch) is not float or not all(isfinite(x) for x in (turn_depth, path_stretch)): raise ValueError("axillary scalar fixture values must be finite binary64")
    if turn_depth < _turn: return AxillaryPredicateResult(False, 8, turn_depth, path_stretch)
    if path_stretch > _stretch: return AxillaryPredicateResult(False, 9, turn_depth, path_stretch)
    return AxillaryPredicateResult(True, None, turn_depth, path_stretch)
_U0 = (-float.fromhex("0x1.0866666666667p+0"), float.fromhex("0x1.1333333333333p+1"), -float.fromhex("0x1.699999999999ap-4"))
_A0 = (-float.fromhex("0x1.289999999999ap+0"), float.fromhex("0x1.9533333333334p+0"), -float.fromhex("0x1.2f28f5c28f5c4p-4"))
_O0 = (-float.fromhex("0x1.599999999999ap+0"), float.fromhex("0x1.d99999999999ap+0"), -float.fromhex("0x1.47ae147ae147bp-4"))
AXILLARY_FIXTURE_IDS = ("axillary.principal-left-pass", "axillary.principal-right-mirror-pass", "axillary.wrong-sign-left", "axillary.U-equals-A", "axillary.A-equals-O", "axillary.U-equals-O", "axillary.long-sag-left", "axillary.scalar.turn-depth-predecessor", "axillary.scalar.turn-depth-boundary", "axillary.scalar.turn-depth-successor", "axillary.scalar.path-stretch-predecessor", "axillary.scalar.path-stretch-boundary", "axillary.scalar.path-stretch-successor")
def run_axillary_fixture_matrix(_turn=_TURN, _stretch=_STRETCH):
    mirror = lambda p: tuple(-x if i == 0 else x for i, x in enumerate(p))
    calls = (("left", _U0, _A0, _O0), ("right", mirror(_U0), mirror(_A0), mirror(_O0)), ("left", _O0, _A0, _U0), ("left", _U0, _U0, _O0), ("left", _U0, _O0, _O0), ("left", _U0, _A0, _U0), ("left", (0., 1., 0.), (0., -10., 0.), (-1., 0., 0.)))
    expected = ((True, None, float.fromhex("0x1.4016a28cc89afp-3"), float.fromhex("0x1.0ab0f3d101d06p+1")), (True, None, float.fromhex("0x1.4016a28cc89afp-3"), float.fromhex("0x1.0ab0f3d101d06p+1")), (False, 8, -float.fromhex("0x1.4016a28cc89afp-3"), float.fromhex("0x1.0ab0f3d101d06p+1")), ("hard-failure", 3, None, None), ("hard-failure", 4, None, None), ("hard-failure", 5, None, None), (False, 9, float.fromhex("0x1.0b8e161fdc225p-1"), float.fromhex("0x1.dc4de77c38e3cp+3")))
    hard_values = ((0.0, None, None), (float.fromhex("0x1.bf1092ac1a7f1p-2"), 0.0, None), (float.fromhex("0x1.29747f9d3ab49p-1"), float.fromhex("0x1.29747f9d3ab49p-1"), 0.0))
    result = []
    for fixture, call, wanted in zip(AXILLARY_FIXTURE_IDS[:7], calls, expected):
        try:
            row = evaluate_axillary_predicate(*call)
            if wanted[0] == "hard-failure" or (row.passed, row.stage, row.turn_depth, row.path_stretch) != wanted: raise AssertionError(f"{fixture} expected {wanted!r}")
            result.append({"fixture_id": fixture, "outcome": "pass" if row.passed else "fail", "stage": row.stage, "turn_depth": row.turn_depth, "path_stretch": row.path_stretch, "lr": row.lr, "ls": row.ls, "lc": row.lc})
        except AxillaryPredicateError as exc:
            if wanted[0] != "hard-failure": raise AssertionError(f"{fixture} unexpectedly failed at step {exc.stage}") from exc
            values = hard_values[wanted[1] - 3]; actual_values = (exc.lr, exc.ls, exc.lc)
            if exc.stage != wanted[1] or any(want is not None and actual != want for actual, want in zip(actual_values, values)): raise AssertionError(f"{fixture} hard failure changed: {(exc.stage, exc.lr, exc.ls, exc.lc)!r}")
            result.append({"fixture_id": fixture, "outcome": "hard-failure", "stage": exc.stage, "turn_depth": None, "path_stretch": None, "lr": exc.lr, "ls": exc.ls, "lc": exc.lc})
        except ValueError as exc: raise AssertionError(f"{fixture} raised an unclassified failure") from exc
    scalar = ((float.fromhex("0x1.9999999999999p-5"), 1.), (_turn, 1.), (float.fromhex("0x1.999999999999bp-5"), 1.), (1., float.fromhex("0x1.3ffffffffffffp+1")), (1., _stretch), (1., float.fromhex("0x1.4000000000001p+1")))
    wanted = ((False, 8), (True, None), (True, None), (True, None), (True, None), (False, 9))
    for fixture, values, (okay, stage) in zip(AXILLARY_FIXTURE_IDS[7:], scalar, wanted):
        row = evaluate_axillary_scalars(*values)
        if (row.passed, row.stage, row.turn_depth, row.path_stretch) != (okay, stage, *values): raise AssertionError(f"{fixture} changed: {(row.passed, row.stage, row.turn_depth, row.path_stretch)!r}")
        result.append({"fixture_id": fixture, "outcome": "pass" if okay else "fail", "stage": row.stage, "turn_depth": row.turn_depth, "path_stretch": row.path_stretch})
    return tuple(result)
def _put(out, key, values, relation="ge", unit="m", omitted=0):
    values = tuple(float(x) for x in values)
    if not values or any(not isfinite(x) for x in values): _fail("anatomy measure is empty or non-finite", key)
    out[key] = {"values": values, "minimum": min(values), "maximum": max(values), "sample_count": len(values), "relation": relation, "unit": unit, "omitted_count": omitted}
def _span(points, axis): return max(p[axis] for p in points) - min(p[axis] for p in points)
def _pair(a, b, name):
    if not a or set(a) != set(b): _fail("anatomy traces are missing or unequal", name)
    return [(tag, a[tag], b[tag]) for tag in sorted(a)]
def _side(out, levels, charts, level, side, neck_y, geometry, cache=None):
    shoulder = _trace(levels, charts, f"junction.thorax__{side}_shoulder", level, cache); arm = _trace(levels, charts, f"port.{side}_arm", level, cache); prefix = "anatomy."
    _put(out, prefix + f"arm_port_descent.{side}.L{level}", [neck_y - p[1] for p in arm.values()])
    owners = tuple(c["construction_owner"] for c in charts[level]); points = {i for fi, face in enumerate(levels[level].quads) if owners[fi] == f"domain.{side}_shoulder" for i in face}
    _put(out, prefix + f"shoulder_surface_descent.{side}.L{level}", [neck_y - levels[level].vertices[i][1] for i in sorted(points)])
    upper = {tag[1]: p for tag, p in shoulder.items() if tag[0] == 6}; axilla = {tag[1]: p for tag, p in shoulder.items() if tag[0] == 4}; inferior = {tag[1]: p for tag, p in arm.items() if tag[0] == 4}; axillary = []
    if set(upper) != set(axilla) or set(axilla) != set(inferior): _fail("axillary traces are missing or unequal", side)
    for tag in sorted(upper):
        try: row = evaluate_axillary_predicate(side, upper[tag], axilla[tag], inferior[tag])
        except ValueError as exc: _fail("axillary predicate rejected selected trace", side, str(exc))
        axillary.append(row)
    _put(out, prefix + f"axillary_turn_depth.{side}.L{level}", [x.turn_depth for x in axillary]); _put(out, prefix + f"axillary_path_stretch.{side}.L{level}", [x.path_stretch for x in axillary], "le", "dimensionless")
    paired = _pair({t: p for t, p in shoulder.items() if 4 <= t[0] <= 5}, {t: p for t, p in arm.items() if 4 <= t[0] <= 5}, "axillary recess"); sign = 1 if side == "right" else -1
    _put(out, prefix + f"axillary_inboard_recess.{side}.L{level}", [sign * (o[0] - j[0]) for _, j, o in paired]); _put(out, prefix + f"axillary_downward_recess.{side}.L{level}", [o[1] - j[1] for _, j, o in paired])
    hip = _trace(levels, charts, f"junction.pelvis__{side}_hip", level, cache); thigh = _trace(levels, charts, f"port.{side}_thigh", level, cache); paired = _pair(hip, thigh, "pelvic wrap");
    _put(out, prefix + f"pelvic_vertical_wrap.{side}.L{level}", [j[1] - p[1] for _, j, p in paired])
    ps_x = surface.geometry_component(geometry, f"hips.{side}.P_s.x"); ratios = [abs(j[0] - ps_x) / abs(p[0] - ps_x) for _, j, p in paired if p[0] - ps_x != 0.0]; omitted = len(paired) - len(ratios)
    if not ratios: _fail("pelvic lateral ratio has no nonzero denominators", side)
    _put(out, prefix + f"pelvic_lateral_ratio.{side}.L{level}", ratios, "ge", "dimensionless", omitted)
    _put(out, prefix + f"front_depth_wrap.{side}.L{level}", [j[2] - p[2] for tag, j, p in paired if tag[1] > 1], "ge", "m"); _put(out, prefix + f"back_depth_wrap.{side}.L{level}", [p[2] - j[2] for tag, j, p in paired if tag[1] < 1], "ge", "m")
    _put(out, prefix + f"clearance.{side}_axilla.L{level}", [min(_span(tuple(arm.values()), 1), _span(tuple(arm.values()), 2))])
def measure_anatomy(value, geometry, chart_summary=None):
    levels, charts = _context(value, geometry, chart_summary); out = {}; cache = _new_selector_cache()
    for level in range(3):
        neck = _trace(levels, charts, "port.neck", level, cache); neck_junction = _trace(levels, charts, "junction.thorax__neck", level, cache); paired = _pair(neck, neck_junction, "neck exposure")
        _put(out, f"anatomy.neck_exposure.L{level}", [port[1] - junction[1] for _, port, junction in paired]); neck_y = min(p[1] for p in neck.values())
        for side in ("left", "right"): _side(out, levels, charts, level, side, neck_y, geometry, cache)
        left_hip, right_hip = _trace(levels, charts, "junction.pelvis__left_hip", level, cache), _trace(levels, charts, "junction.pelvis__right_hip", level, cache); left_thigh, right_thigh = _trace(levels, charts, "port.left_thigh", level, cache), _trace(levels, charts, "port.right_thigh", level, cache)
        _put(out, f"anatomy.clearance.neck.L{level}", [min(_span(tuple(neck.values()), 0), _span(tuple(neck.values()), 2))]); _put(out, f"anatomy.clearance.groin.L{level}", [min(p[0] for p in right_hip.values()) - max(p[0] for p in left_hip.values())]); _put(out, f"anatomy.clearance.medial_thigh.L{level}", [min(p[0] for p in right_thigh.values()) - max(p[0] for p in left_thigh.values())])
    if len(out) != 78: _fail("anatomy inventory is not exactly 78 measures", len(out))
    return out
def _spec(key, _threshold=THRESHOLD):
    return ("le", 2.5, "dimensionless") if "path_stretch" in key else ("ge", 1.05, "dimensionless") if "lateral_ratio" in key else ("ge", .005, "m") if "depth_wrap" in key else ("ge", _threshold, "m")
def anatomy_threshold_records():
    ids = [f"anatomy.neck_exposure.L{l}" for l in range(3)] + [f"anatomy.{m}.{s}.L{l}" for m in ANATOMY_METRICS for s in ("left", "right") for l in range(3)] + [f"anatomy.clearance.{c}.L{l}" for c in CLEARANCES for l in range(3)]; result = []
    for key in sorted(ids): relation, bound, unit = _spec(key); result.append({"threshold_id": f"threshold.{key}", "relation": relation, "lower": bound if relation == "ge" else None, "upper": bound if relation == "le" else None, "unit": unit})
    return result
def anatomy_gate_records(value, geometry, chart_summary=None):
    measures = measure_anatomy(value, geometry, chart_summary); failures = []
    for key, item in measures.items():
        relation, bound, _ = _spec(key); valid = item["maximum"] <= bound if relation == "le" else item["minimum"] >= bound
        failures.extend((key,) if not valid else ())
    if failures: _fail("anatomy gates failed", *failures)
    return [{"gate_id": key, "outcome": "pass", "sample_count": item["sample_count"], "observed_min": item["minimum"], "observed_max": item["maximum"], "threshold_id": f"threshold.{key}"} for key, item in sorted(measures.items())]
run_production_axillary_fixtures = run_axillary_fixture_matrix
__all__ = ["ANATOMY_METRICS", "AXILLARY_FIXTURE_IDS", "CLEARANCES", "AnatomyGateError", "AxillaryPredicateError", "anatomy_gate_records", "anatomy_threshold_records", "axillary_predicate", "evaluate_axillary_predicate", "evaluate_axillary_scalars", "measure_anatomy", "run_axillary_fixture_matrix", "run_production_axillary_fixtures", "select_trace", "validate_evaluated_surface"]
