"""Independent chart, transition, and propagated-lineage validation."""
from collections import defaultdict
from fractions import Fraction
from hashlib import sha256
from math import isfinite

import owned_root_surface as surface


class ChartLineageError(ValueError): pass
COUNTS = ((120, 227, 104, 38, 189), (451, 870, 416, 76, 794), (1737, 3404, 1664, 152, 3252))
TOPOLOGY_HASH = "230cad4872ddafafd28110e6baf45510c1a11fb6b39e12ffc0ef787d9c89bdb9"
JUNCTION_HASH = "1637c96b888e47c7714fbf4dc68521f86bf9e14d113ca14a55d4a430fb68f5b3"
FORMULA_HASH = "da8569de79e3c7479f94a94c5a2d45a9a131f623880c9301835a8e5f8e322bd5"
NEUTRAL_HASH = "caa90159002661fb7e36063e1f2cbab2c26d1bcbb8e35227cd2d34eddbc400e0"
FORMULA_FIELDS = ("control_id", "lattice_key", "formula_id", "construction_owner", "index_parameters",
                  "geometry_dependencies", "coordinate")
def _fail(message):
    raise ChartLineageError(message)
def _hash(value):
    return sha256(repr(value).encode("ascii")).hexdigest()
def _strict(actual, expected, where):
    if type(actual) is not type(expected): _fail(f"{where} has an invalid type")
    if type(expected) is dict:
        if set(actual) != set(expected): _fail(f"{where} has an open schema")
        [_strict(actual[key], expected[key], f"{where}.{key}") for key in expected]
    elif type(expected) in (list, tuple):
        if len(actual) != len(expected): _fail(f"{where} has an invalid length")
        [_strict(actual[index], value, f"{where}[{index}]") for index, value in enumerate(expected)]
    elif type(expected) is float and (not isfinite(actual) or actual != expected): _fail(f"{where} is non-finite or incorrect")
    elif actual != expected: _fail(f"{where} does not match the frozen contract")
def _incidence(faces, vertex_count):
    uses, around, boundary = defaultdict(list), defaultdict(list), defaultdict(set)
    for face_index, face in enumerate(faces):
        if type(face) is not tuple or len(face) != 4 or len(set(face)) != 4: _fail("a face is not a four-vertex cycle")
        if any(type(v) is not int or not 0 <= v < vertex_count for v in face): _fail("a face has an invalid vertex")
        for slot, left in enumerate(face):
            around[left].append(face_index)
            uses[tuple(sorted((left, face[(slot + 1) % 4])))].append((face_index, slot, left, face[(slot + 1) % 4]))
    for edge, rows in uses.items():
        if len(rows) not in (1, 2) or (len(rows) == 2 and rows[0][2:] == rows[1][2:]):
            _fail("edge incidence is non-manifold or inconsistently oriented")
        if len(rows) == 1:
            boundary[edge[0]].add(edge[1])
            boundary[edge[1]].add(edge[0])
    return dict(uses), around, boundary
def _subdivide(faces, loops, vertex_count):
    uses, around, boundary = _incidence(faces, vertex_count)
    edges = tuple(sorted(uses))
    points = tuple((edge, vertex_count + i) for i, edge in enumerate(edges))
    point_by_edge, face_start = dict(points), vertex_count + len(edges)
    vertices = tuple((v, *sorted(boundary[v])) if v in boundary else tuple(x for fi in sorted(around[v]) for x in faces[fi]) for v in range(vertex_count))
    if any(v in boundary and len(boundary[v]) != 2 for v in range(vertex_count)): _fail("invalid boundary valence")
    edge_stencils = tuple((edge, edge + tuple(v for fi, *_ in uses[edge] for v in faces[fi])) for edge in edges)
    children = tuple((fi, corner, (v, point_by_edge[tuple(sorted((v, face[(corner + 1) % 4])))], face_start + fi, point_by_edge[tuple(sorted((face[(corner - 1) % 4], v)))])) for fi, face in enumerate(faces) for corner, v in enumerate(face))
    propagated = tuple((name, tuple(x for i, v in enumerate(loop) for x in (v, point_by_edge[tuple(sorted((v, loop[(i + 1) % len(loop)])))]))) for name, loop in loops)
    local = {"vertex_stencils": vertices, "edge_stencils": edge_stencils, "face_stencils": tuple(enumerate(faces)), "edge_point_indices": points, "child_emission": children, "propagated_port_loops": propagated}
    stencils = vertices + tuple(row[1] for row in edge_stencils) + tuple(faces)
    return local, stencils
def _topology(evaluation):
    meshes, symbolic = (evaluation.cage, *evaluation.levels), surface.symbolic_topology()
    if len(meshes) != 3 or _hash(symbolic) != TOPOLOGY_HASH: _fail("symbolic topology is not frozen")
    controls, next_faces, next_loops = symbolic
    levels, incidences, subdivisions, next_stencils, base_owners = [], [], [], None, None
    for level, mesh in enumerate(meshes):
        vertices, edges, faces, boundary, _ = COUNTS[level]
        report, incidence = surface.level_topology(mesh), surface.topology_incidence(mesh)
        if level == 0: base_owners = report["face_owners"]
        owners = tuple(base_owners[i // (4 ** level)] for i in range(faces))
        vertex_ids = controls if level == 0 else tuple(f"vertex.L{level}.v{i:04d}" for i in range(vertices))
        face_ids = tuple(f"q{i:03d}" for i in range(faces)) if level == 0 else tuple(f"face.L{level}.q{i:04d}" for i in range(faces))
        _strict((report["vertex_ids"], report["face_ids"], report["face_owners"], report["faces"], report["boundary_loops"]), (vertex_ids, face_ids, owners, next_faces, next_loops), f"L{level} order")
        uses, _, _ = _incidence(next_faces, vertices)
        expected_incidence = tuple({"edge": edge, "incident_faces": tuple(r[0] for r in uses[edge]), "slots": tuple(r[1] for r in uses[edge])} for edge in sorted(uses))
        _strict(incidence, expected_incidence, f"topology_incidence[{level}]")
        boundary_edges = {edge for edge, rows in uses.items() if len(rows) == 1}
        loop_edges = {tuple(sorted((loop[i], loop[(i + 1) % len(loop)]))) for _, loop in next_loops for i in range(len(loop))}
        if (len(uses), len(boundary_edges)) != (edges, boundary) or boundary_edges != loop_edges: _fail("bad edge/port inventory")
        if len(mesh.vertices) != vertices or any(type(p) is not tuple or len(p) != 3 or any(type(x) is not float or not isfinite(x) for x in p) for p in mesh.vertices):
            _fail("surface coordinates are not finite binary64 vector3 values")
        _strict(mesh.source_stencils, tuple((i,) for i in range(120)) if level == 0 else next_stencils, f"source_stencils[{level}]")
        levels.append(report)
        incidences.append(incidence)
        if level < 2:
            candidate = surface.subdivision_incidence(mesh)
            local, next_stencils = _subdivide(next_faces, next_loops, vertices)
            [_strict(candidate[key], expected, f"subdivision_incidence[{level}].{key}") for key, expected in local.items()]
            _strict(surface.propagate_port_loops(mesh), dict(local["propagated_port_loops"]), "propagated ports")
            subdivisions.append((candidate, next_stencils))
            next_faces, next_loops = tuple(row[2] for row in local["child_emission"]), local["propagated_port_loops"]
    neutral = tuple(levels), tuple(incidences), tuple(candidate for candidate, _ in subdivisions)
    if _hash(neutral) != NEUTRAL_HASH: _fail("neutral topology commitment changed")
    return meshes, controls, levels, subdivisions
def _formulas(records, controls, vertices, control_domains, junctions):
    if type(records) is not tuple or len(records) != 120: _fail("formula inventory is not exactly 120 records")
    ledger, dependencies, lattice = [], {}, []
    for index, (record, control) in enumerate(zip(records, controls)):
        if type(record) is not dict or set(record) != set(FORMULA_FIELDS): _fail(f"formula_records[{index}] has an open schema")
        domains = control_domains[index]
        owner = domains[0] if len(domains) == 1 else junctions.get(frozenset(domains))
        deps, key = record["geometry_dependencies"], record["lattice_key"]
        invalid = record["control_id"] != control or record["construction_owner"] != owner or type(key) is not list or len(key) != 3 or any(type(x) is not int for x in key) or type(deps) is not list or deps != sorted(set(deps)) or len(deps) > 12
        if owner is None or invalid: _fail(f"formula_records[{index}] has invalid IDs, ownership, lattice, or dependencies")
        _strict(record["coordinate"], list(vertices[index]), f"formula_records[{index}].coordinate")
        ledger.append({field: record[field] for field in FORMULA_FIELDS[:-1]})
        dependencies[control], lattice = deps, lattice + [key]
    if _hash(tuple(ledger)) != FORMULA_HASH: _fail("formula shape/dependency ledger is not frozen")
    if len({item for values in dependencies.values() for item in values}) != 92: _fail("dependency universe is not 92")
    return dependencies, lattice
def _domain_boundary(topology, domain):
    uses = defaultdict(list)
    for face, owner in zip(topology["faces"], topology["face_owners"]):
        if owner == domain:
            for i, left in enumerate(face):
                edge = tuple(sorted((left, face[(i + 1) % 4])))
                uses[edge].append((left, face[(i + 1) % 4]))
    return {edge: rows[0] for edge, rows in uses.items() if len(rows) == 1}
def _domain_cycle(boundary, shared):
    following = {boundary[e][0]: boundary[e][1] for e in shared}
    if len(following) != len(shared): _fail("a junction is not a domain boundary cycle")
    cycle = [min(following)]
    while following.get(cycle[-1]) != cycle[0] and len(cycle) <= len(shared):
        cycle.append(following[cycle[-1]])
    if len(cycle) != len(shared) or following.get(cycle[-1]) != cycle[0]: _fail("a junction is not one closed trace")
    return tuple(cycle)
def _traces(levels, subdivisions, rows, lattice, evaluation):
    axes, result, meshes = {"i": 0, "j": 1, "k": 2}, [{} for _ in levels], (evaluation.cage, *evaluation.levels)
    for row in rows:
        jid, domains, tags, expected_tags = row["junction_id"], row["incident_domains"], None, []
        for level, topology in enumerate(levels):
            boundaries = tuple(_domain_boundary(topology, domain) for domain in domains)
            shared = set(boundaries[0]) & set(boundaries[1])
            first, second = (_domain_cycle(boundary, shared) for boundary in boundaries)
            paired = (second[0], *reversed(second[1:]))
            residuals = (abs(meshes[level].vertices[a][axis] - meshes[level].vertices[b][axis]) for a, b in zip(first, paired) for axis in range(3))
            if first != paired or any(value > float.fromhex("0x1.c666666666666p-45") for value in residuals):
                _fail("junction traces disagree")
            result[level][jid] = shared
            if level == 0:
                indices = tuple(int(control[1:]) for control in row["base_control_ids"])
                if set(first) != set(indices): _fail("junction controls do not match independent incidence")
                base_tags = tuple(tuple(lattice[v][axes[a]] for a in row["tag_axes"]) for v in indices)
                if base_tags != row["base_lattice_tags"]: _fail("junction lattice tags are incorrect")
                tags = {v: tuple((lattice[v][axes[a]], 1) for a in row["tag_axes"]) for v in first}
            if set(tags) != set(first): _fail("junction tag membership is incomplete")
            expected_tags.append(dict(sorted(tags.items())))
            if level < 2:
                points = dict(subdivisions[level][0]["edge_point_indices"])
                tags = tags | {points[e]: tuple(((Fraction(*tags[e[0]][a]) + Fraction(*tags[e[1]][a])) / 2).as_integer_ratio() for a in range(2)) for e in shared}
        _strict(surface.propagate_junction_tags(evaluation, jid), tuple(expected_tags), f"junction_tags.{jid}")
    return result
def _uv(path):
    corners = ((Fraction(0), Fraction(0)), (Fraction(1), Fraction(0)), (Fraction(1), Fraction(1)), (Fraction(0), Fraction(1)))
    for child in path:
        mids = tuple(tuple((a + b) / 2 for a, b in zip(corners[i], corners[(i + 1) % 4])) for i in range(4))
        center = tuple(sum(point[a] for point in corners) / 4 for a in range(2))
        corners = ((corners[0], mids[0], center, mids[3]), (corners[1], mids[1], center, mids[0]), (corners[2], mids[2], center, mids[1]), (corners[3], mids[3], center, mids[2]))[child]
    return corners
def _charts(topology, level):
    records, samples = [], [[] for _ in topology["vertex_ids"]]
    for index, face in enumerate(topology["faces"]):
        base = index // (4 ** level)
        path = () if level == 0 else ((index % 4,) if level == 1 else ((index % 16) // 4, index % 4))
        chart_id = f"chart.q{base:03d}" if level == 0 else f"chart.q{base:03d}/L{level}.s{'.s'.join(map(str, path))}"
        corners = []
        for vertex, uv in zip(face, _uv(path)):
            sample = {"chart_id": chart_id, "u": {"numerator": uv[0].numerator, "denominator": uv[0].denominator}, "v": {"numerator": uv[1].numerator, "denominator": uv[1].denominator}}
            samples[vertex].append(sample)
            corners.append({"vertex_id": topology["vertex_ids"][vertex], "u": sample["u"], "v": sample["v"]})
        records.append({"chart_id": chart_id, "level": level, "face_id": topology["face_ids"][index], "base_face_id": f"q{base:03d}", "construction_owner": topology["face_owners"][index], "corners": corners})
    return records, samples
def _transitions(topology, charts, level, traces, junctions, domain_order):
    uses, _, _ = _incidence(topology["faces"], len(topology["vertex_ids"]))
    records, observed = [], defaultdict(set)
    for edge, rows in sorted(uses.items()):
        if len(rows) == 1: continue
        source, destination = sorted((rows[0][0], rows[1][0]))
        source_row, destination_row = (next(row for row in rows if row[0] == face) for face in (source, destination))
        owners = topology["face_owners"][source], topology["face_owners"][destination]
        junction = None if owners[0] == owners[1] else junctions.get(frozenset(owners))
        if owners[0] != owners[1] and (junction is None or edge not in traces[junction]): _fail("bad cross-domain transition")
        if junction: observed[junction].add(edge)
        endpoints = [topology["vertex_ids"][v] for v in edge]
        records.append({"transition_id": f"transition/L{level}/e{endpoints[0]}-{endpoints[1]}", "level": level, "source_chart": charts[source]["chart_id"], "destination_chart": charts[destination]["chart_id"], "source_edge_slot": source_row[1], "destination_edge_slot": destination_row[1], "endpoint_ids": endpoints, "t_destination_rule": "1-t_source", "junction_id": junction, "incident_domains": [owners[0]] if junction is None else [d for d in domain_order if d in owners]})
    if any(observed[jid] != edges for jid, edges in traces.items()): _fail("junction transition membership is incomplete")
    return records
def _derive(evaluation, formula_records):
    meshes, controls, levels, subdivisions = _topology(evaluation)
    junction_rows = surface.junction_trace_inputs()
    if _hash(junction_rows) != JUNCTION_HASH: _fail("the seven junction declarations are not frozen")
    junctions = {frozenset(row["incident_domains"]): row["junction_id"] for row in junction_rows}
    port_domains = tuple(next(owner for face, owner in zip(levels[0]["faces"], levels[0]["face_owners"]) if loop[0] in face and loop[1] in face) for _, loop in levels[0]["boundary_loops"])
    domain_order = tuple(junction_rows[i]["incident_domains"][j] for i, j in ((0, 0), (1, 1), (2, 1))) + port_domains
    if len(set(domain_order)) != 8: _fail("domain order is incomplete")
    control_domains = [tuple(domain for domain in domain_order if any(owner == domain and index in face for face, owner in zip(levels[0]["faces"], levels[0]["face_owners"]))) for index in range(120)]
    dependencies, lattice = _formulas(formula_records, controls, meshes[0].vertices, control_domains, junctions)
    traces = _traces(levels, subdivisions, junction_rows, lattice, evaluation)
    contributors = [[{i} for i in range(120)]]
    for _, stencils in subdivisions:
        previous = contributors[-1]
        contributors.append([{base for source in stencil for base in previous[source]} for stencil in stencils])
    chart_levels, transition_levels, vertices = [], [], []
    for level, topology in enumerate(levels):
        charts, samples = _charts(topology, level)
        transitions = _transitions(topology, charts, level, traces[level], junctions, domain_order)
        if (len(charts), len(transitions), max(map(len, samples))) != (COUNTS[level][2], COUNTS[level][4], 5):
            _fail("bad chart, transition, or sample count")
        if any(not values or len(values) > 5 for values in samples): _fail("vertex chart samples are empty or over cap")
        for index, base in enumerate(contributors[level]):
            base_ids = [f"c{i:03d}" for i in sorted(base)]
            union = sorted({item for control in base_ids for item in dependencies[control]})
            domains = [domain for domain in domain_order if any(domain in control_domains[i] for i in base)]
            if len(base_ids) > 20 or len(union) > 54 or len(domains) > 5: _fail("propagated lineage exceeds a frozen cap")
            key = lambda row: (row["chart_id"], Fraction(row["u"]["numerator"], row["u"]["denominator"]), Fraction(row["v"]["numerator"], row["v"]["denominator"]))
            vertices.append({"level": level, "vertex_id": topology["vertex_ids"][index], "samples": sorted(samples[index], key=key), "base_control_contributors": base_ids, "geometry_dependency_union": union, "contributor_domains": domains})
        chart_levels.append(charts)
        transition_levels.append(transitions)
    return {"level_counts": [{"level": level, "charts": COUNTS[level][2], "interior_transitions": COUNTS[level][4], "maximum_samples_per_vertex": 5} for level in range(3)], "chart_records": sorted((r for rows in chart_levels for r in rows), key=lambda r: r["chart_id"]), "transition_records": sorted((r for rows in transition_levels for r in rows), key=lambda r: r["transition_id"]), "vertex_records": vertices}
def build_chart_summary(evaluation, formula_records): return _derive(evaluation, formula_records)
def validate_chart_summary(summary, evaluation, formula_records): _strict(summary, _derive(evaluation, formula_records), "chart_summary")
