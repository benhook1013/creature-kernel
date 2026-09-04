"""Private managed-test and seeded-bundle builder for the frozen successor."""
from __future__ import annotations
import datetime, importlib.metadata, importlib.util, io, locale, math, os, platform, re
import shutil, struct, sys, sysconfig, tempfile, time, unittest, zlib
from pathlib import Path; import artifact_serialization as artifacts
ROOT = Path(__file__).resolve().parents[2]
PACKAGE, TESTS = ROOT / "experiments/owned-root-assembly-successor", ROOT / "experiments/owned-root-assembly-successor/tests"
CONTRACT_ROLE, SIDECAR_ROLE, SOURCE_ROLE = ("experiments/owned-root-assembly-successor/design-contract.md", "experiments/owned-root-assembly-successor/design-contract.sha256", "examples/body-documents/stylized-digitigrade-biped-authored-form.json")
PROFILE_ROLE, LAUNCHER_ROLE, REQUIREMENTS_ROLE = ("experiments/current-form-surface-preview/structural_profile_candidates.json", "experiments/current-form-surface-preview/surface_preview_launcher.sh", "experiments/current-form-surface-preview/requirements.txt")
EXPECTED_CONTRACT_SHA256 = "3122f0db2235754ed782bd38a88c4d7ad7cc7edbf635d147194f1e93f8556490"
EXPECTED_SOURCE_SHA256 = "82269e843555ff1aad3c66399e3fcaeb11bbee81d72b69d15765ea9c4e7aff14"
EXPECTED_PROFILE_SHA256 = "a5fba6643d0031bac83c08e9093e11fd7945806963509fa939865866112d9640"
EXPECTED_SOURCE_BYTES, EXPECTED_PROFILE_BYTES = 56984, 29970
IMPLEMENTATION_ROLES = tuple("experiments/owned-root-assembly-successor/anatomy_gates.py experiments/owned-root-assembly-successor/artifact_serialization.py experiments/owned-root-assembly-successor/build_owned_root.py experiments/owned-root-assembly-successor/chart_lineage.py experiments/owned-root-assembly-successor/compare_two_seed_outputs.py experiments/owned-root-assembly-successor/mesh_correctness.py experiments/owned-root-assembly-successor/owned_root_launcher.sh experiments/owned-root-assembly-successor/owned_root_surface.py experiments/owned-root-assembly-successor/prepared_projection.py experiments/owned-root-assembly-successor/render_export.py experiments/owned-root-assembly-successor/tests/test_build_owned_root.py experiments/owned-root-assembly-successor/tests/test_mesh_correctness.py experiments/owned-root-assembly-successor/tests/test_owned_root_surface.py experiments/owned-root-assembly-successor/tests/test_prepared_projection.py experiments/owned-root-assembly-successor/tests/test_render_export.py".split())
FORMULA_IDS = tuple("formula.axial.j1.edge formula.axial.j1.interior formula.axial.station formula.neck.stem formula.shoulder.left formula.shoulder.right formula.hip.left formula.hip.right".split())
SPECIAL_CASE_IDS = tuple("formula.axial.j1.edge formula.axial.j1.interior formula.neck.stem formula.shoulder.left formula.shoulder.right formula.hip.left formula.hip.right topology.open-port-cap topology.shared-junction".split())
PARAMETER_IDS = tuple("left.r_y right.r_y lower_pelvis.L_y lower_pelvis.C_z left.r_x right.r_x lower_pelvis.R_x left.r_z right.r_z lower_pelvis.R_f lower_pelvis.R_b left.thigh_start_x left.thigh_start_y left.thigh_start_z right.thigh_start_x right.thigh_start_y right.thigh_start_z neck_collar.C_y neck_collar.rL neck_upper.C_y neck_upper.rL left.axilla_x left.axilla_y right.axilla_x right.axilla_y left.peak_y right.peak_y left.start_lateral right.start_lateral left.start_up right.start_up left.shoulder_depth right.shoulder_depth".split())
SURFACE_ROLES = ("surface-level-0.ply", "surface-level-1.ply", "surface-level-2.ply")
PERTURBATION_ROLES = tuple(f"perturb-{p.replace('.', '-')}.ply" for p in PARAMETER_IDS)
ARTIFACT_ROLES = (*SURFACE_ROLES, *PERTURBATION_ROLES, "direct.png", "lineage.png", "input-manifest.json", "coordinate-manifest.json", "gate-manifest.json", "causality-manifest.json", "render-manifest.json", "stable-manifest.json", "prepared-input.json", "report.json", "report.sha256")
RUN_REPORT_GATES = tuple(f"seed.{i}.{name}" for i, name in enumerate(("identity", "prepared-input", "catalogs", "geometry-gates", "causality", "serialization"), 1))
REQUIRED_TEST_IDS = ("test_mesh_correctness.ProductionIntersectionFixtureTests.test_contract_fixture_matrix", "test_owned_root_surface.ProductionAxillaryFixtureTests.test_contract_fixture_matrix")
LEVEL_COUNTS = ((120, 227, 104, 208, 38), (451, 870, 416, 832, 76), (1737, 3404, 1664, 3328, 152))
MANIFEST_SCHEMAS = {name + "-manifest.json": f"owned-root-assembly-successor-{name}-manifest.v1" for name in ("input", "coordinate", "gate", "causality", "render", "stable")}
RUN_PHASES = ("identity", "prepared-input", "catalogs", "geometry-gates", "causality", "serialization", "total-before-seal")
STABLE_ARTIFACT_ROLES = tuple(sorted((*SURFACE_ROLES, "direct.png", "lineage.png"), key=str.encode))
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_UTC = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{6}Z\Z")
_RUNTIME_DISTS = (("imageio", "2.37.4"), ("lazy-loader", "0.5"), ("networkx", "3.4.2"), ("numpy", "2.2.6"), ("packaging", "26.3"), ("pillow", "11.1.0"), ("scikit-image", "0.25.2"), ("scipy", "1.15.3"), ("tifffile", "2025.5.10"))
_DIRECT_DISTS = (("numpy", "2.2.6"), ("scikit-image", "0.25.2"), ("pillow", "11.1.0"))
class BuildError(ValueError): """A closed builder admission, evidence, or publication failure."""
def _fail(message): raise BuildError(message)
def _need(condition, message): return None if condition else _fail(message)
def _order(values): return tuple(sorted(values, key=lambda value: value.encode("utf-8")))
def _order_records(records, field): return sorted(records, key=lambda row: row[field].encode("utf-8"))
def _record(role):
    path = ROOT / role; _need(not path.is_symlink() and path.is_file(), f"missing or non-regular fixed file: {role}")
    try: return artifacts.regular_file_record(path, role, max_bytes=64 * 1024 if role == REQUIREMENTS_ROLE else 4 * 1024 * 1024)
    except Exception as exc: raise BuildError(f"cannot admit fixed file: {role}") from exc
def _implementation_files():
    found = []
    for directory, subdirectories, filenames in os.walk(PACKAGE, followlinks=False):
        subdirectories[:] = [n for n in subdirectories if not (Path(directory) / n).is_symlink()]; found.extend((Path(directory) / n).relative_to(ROOT).as_posix() for n in filenames if Path(n).suffix in (".py", ".sh"))
    expected, found = _order(IMPLEMENTATION_ROLES), _order(found); _need(found == expected, f"implementation allowlist mismatch; missing={sorted(set(expected) - set(found), key=str.encode)}; extra={sorted(set(found) - set(expected), key=str.encode)}"); return tuple(_record(role) for role in expected)
def _runtime_text(value, label, limit=128): return value if type(value) is str and len(value.encode("utf-8")) <= limit else _fail(f"{label} is not a bounded runtime string")
def _distribution(name, version):
    try: actual = importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError as exc: raise BuildError(f"missing required distribution: {name}=={version}") from exc
    _need(actual == version, f"wrong distribution version: {name}=={actual}, expected {version}"); return {"name": name.lower(), "version": _runtime_text(actual, f"{name}.version")}
def _builtin(name):
    module, spec = __import__(name), importlib.util.find_spec(name); _need(getattr(module, "__file__", None) is None and spec is not None and spec.origin == "built-in", f"{name} is not admitted as a built-in module"); versions = (None, None) if name == "math" else (_runtime_text(zlib.ZLIB_VERSION, "zlib compile version"), _runtime_text(zlib.ZLIB_RUNTIME_VERSION, "zlib runtime version")); return {"module_name": name, "__file__": None, "find_spec_origin": "built-in", "compile_version": versions[0], "runtime_version": versions[1]}
def _runtime(launcher, requirements):
    _need(platform.python_implementation() == "CPython" and platform.python_version() == "3.10.12" and getattr(sys.implementation, "cache_tag", None) == "cpython-310", "runtime requires CPython 3.10.12 with cache tag cpython-310"); soabi = sysconfig.get_config_var("SOABI"); _need(type(soabi) is str, "runtime SOABI is missing")
    python = {"implementation": "CPython", "version": "3.10.12", "build": _runtime_text(" ".join(platform.python_build()), "python.build"), "compiler": _runtime_text(platform.python_compiler(), "python.compiler"), "cache_tag": "cpython-310", "abiflags": _runtime_text(getattr(sys, "abiflags", ""), "python.abiflags"), "soabi": _runtime_text(soabi, "python.soabi")}
    libc_name, libc_version = platform.libc_ver(); platform_value = {"system": platform.system(), "release": platform.release(), "version": platform.version(), "machine": platform.machine(), "pointer_bits": 8 * struct.calcsize("P"), "byteorder": sys.byteorder, "libc_name": libc_name, "libc_version": libc_version}
    for key in ("system", "release", "version", "machine", "libc_name", "libc_version"): platform_value[key] = _runtime_text(platform_value[key], f"platform.{key}")
    _need(platform_value["system"] == "Linux" and platform_value["byteorder"] in ("little", "big") and type(platform_value["pointer_bits"]) is int and platform_value["pointer_bits"] > 0, "runtime platform is not admitted"); locale_value = {"active": _runtime_text(locale.setlocale(locale.LC_ALL, None), "locale.active", 512), "preferred_encoding": _runtime_text(locale.getpreferredencoding(False), "locale.preferred_encoding", 512)}; return {"schema": "owned-root-assembly-successor-runtime.v2", "python": python, "platform": platform_value, "locale": locale_value, "managed_launcher": launcher, "requirements": requirements, "direct_distributions": [_distribution(*d) for d in _DIRECT_DISTS], "resolved_distributions": [_distribution(*d) for d in _RUNTIME_DISTS], "builtin_modules": [_builtin("math"), _builtin("zlib")]}
def _static_admission():
    contract, sidecar = _record(CONTRACT_ROLE), _record(SIDECAR_ROLE); _need(contract["bytes"] == 173184 and contract["sha256"] == EXPECTED_CONTRACT_SHA256, "contract identity mismatch"); sidecar_bytes = f"{EXPECTED_CONTRACT_SHA256}  {CONTRACT_ROLE}\n".encode("ascii"); _need(sidecar["bytes"] == len(sidecar_bytes) and artifacts.read_regular_file(ROOT / SIDECAR_ROLE) == sidecar_bytes, "contract sidecar identity mismatch")
    source, profile = _record(SOURCE_ROLE), _record(PROFILE_ROLE); _need((source["bytes"], source["sha256"]) == (EXPECTED_SOURCE_BYTES, EXPECTED_SOURCE_SHA256) and (profile["bytes"], profile["sha256"]) == (EXPECTED_PROFILE_BYTES, EXPECTED_PROFILE_SHA256), "source or profile identity mismatch"); launcher, requirements = _record(LAUNCHER_ROLE), _record(REQUIREMENTS_ROLE); _need(artifacts.read_regular_file(ROOT / REQUIREMENTS_ROLE) == b"numpy==2.2.6\nscikit-image==0.25.2\nPillow==11.1.0\n", "requirements are not the exact pinned file")
    implementation = _implementation_files(); runtime = _runtime(launcher, requirements); runtime_bytes = artifacts.canonical_json_bytes(runtime); _need(len(runtime_bytes) <= 64 * 1024, "runtime fingerprint exceeds 64 KiB"); return {"contract": contract, "source": source, "profile_table": profile, "runtime": runtime, "runtime_bytes": runtime_bytes, "runtime_fingerprint_sha256": artifacts.sha256_bytes(runtime_bytes), "implementation_files": implementation}
def _recipe(admission):
    value = {"schema": "owned-root-assembly-successor-recipe.v1", "contract_role": CONTRACT_ROLE, "contract_sha256": EXPECTED_CONTRACT_SHA256, "sidecar_role": SIDECAR_ROLE, "source": admission["source"], "profile_table": admission["profile_table"], "profile_id": "standard_neutral_reference", "correction_round": 0, "topology_id": "owned-root-58-cell-120-control-104-quad.v1", "formula_ids": list(_order(FORMULA_IDS)), "subdivision_levels": 2, "special_case_ids": list(_order(SPECIAL_CASE_IDS)), "gate_set_id": "owned-root-neutral-gates.v1", "renderer_id": "owned-root-raster-pillow-11.1.0.v1", "artifact_roles": list(_order(ARTIFACT_ROLES)), "implementation_files": list(admission["implementation_files"]), "runtime_fingerprint_sha256": admission["runtime_fingerprint_sha256"]}; return value, artifacts.sha256_bytes(artifacts.canonical_json_bytes(value))
def _gate(gate_id, count, minimum, maximum, relation, lower, upper, unit):
    threshold = {"threshold_id": f"threshold.{gate_id}", "relation": relation, "lower": lower, "upper": upper, "unit": unit}; passed = minimum == lower and maximum == upper if relation == "eq" else minimum >= lower if relation == "ge" else maximum <= upper if relation == "le" else maximum < upper; return {"gate_id": gate_id, "outcome": "pass" if passed else "fail", "sample_count": count, "observed_min": minimum, "observed_max": maximum, "threshold_id": threshold["threshold_id"]}, threshold
def _bool(gate_id): return _gate(gate_id, 1, 1, 1, "eq", 1, 1, "boolean")
def _put(rows, thresholds, pair): rows.append(pair[0]); thresholds.append(pair[1])
def _directions(surface): return {name: {"+X": (1.0, 0.0, 0.0), "-X": (-1.0, 0.0, 0.0), "+Y": (0.0, 1.0, 0.0), "-Y": (0.0, -1.0, 0.0)}[info[1]] for name, info in surface.PORT_INFO.items()}
def _chart_owners(mesh, summary):
    if summary is None: return tuple(mesh.face_owners)
    rows = [row for row in summary["chart_records"] if row["level"] == mesh.level]; owners = {}
    for row in rows:
        if row["face_id"] in owners: _fail(f"duplicate chart face ownership at L{mesh.level}")
        owners[row["face_id"]] = row["construction_owner"]
    _need(len(rows) == len(mesh.face_ids) and set(owners) == set(mesh.face_ids), f"chart face incidence is incomplete at L{mesh.level}"); return tuple(owners[face_id] for face_id in mesh.face_ids)
def _junction_cycles(mesh, owners, domains):
    uses = {}
    for face_index, face in enumerate(mesh.quads):
        for slot, left in enumerate(face):
            right = face[(slot + 1) % 4]; uses.setdefault(tuple(sorted((left, right))), []).append((owners[face_index], left, right))
    result = []
    for domain in domains:
        following = {}
        for rows in uses.values():
            if len(rows) != 2 or frozenset(row[0] for row in rows) != frozenset(domains): continue
            selected = [row for row in rows if row[0] == domain]; _need(len(selected) == 1, "junction domain incidence is not independently unique")
            if selected[0][1] in following: _fail("junction domain incidence has duplicate trace starts")
            following[selected[0][1]] = selected[0][2]
        _need(following, f"no junction trace for {domain}"); start = current = min(following); cycle = []
        while current not in cycle:
            cycle.append(current); _need(current in following, "junction trace is not closed"); current = following[current]
        _need(current == start and len(cycle) == len(following), "junction trace is not one closed cycle"); result.append(tuple(cycle))
    return tuple(result)
def _half_tag(left, right):
    numerator = left[0] * right[1] + right[0] * left[1]; denominator = 2 * left[1] * right[1]; common = math.gcd(abs(numerator), denominator); return numerator // common, denominator // common
def _domain_tags(meshes, owners, domains, domain_index, axes, level, surface):
    axis_index = {"i": 0, "j": 1, "k": 2}; cycles = tuple(_junction_cycles(mesh, owner, domains)[domain_index] for mesh, owner in zip(meshes[:level + 1], owners[:level + 1])); tags = {vertex: tuple((surface.COORDINATE_BY_CONTROL[meshes[0].control_ids[vertex]][axis_index[axis]], 1) for axis in axes) for vertex in cycles[0]}
    for current in range(1, level + 1):
        points = dict(surface.subdivision_incidence(meshes[current - 1])["edge_point_indices"]); previous = cycles[current - 1]; out = {vertex: tags[vertex] for vertex in cycles[current] if vertex in tags}
        for slot, left in enumerate(previous):
            right = previous[(slot + 1) % len(previous)]; edge = tuple(sorted((left, right))); point = points.get(edge); _need(point is not None, "junction edge midpoint is absent"); out[point] = tuple(_half_tag(tags[left][axis], tags[right][axis]) for axis in range(2))
        _need(set(out) == set(cycles[current]), "junction tag incidence is incomplete"); tags = out
    return dict(sorted(tags.items()))
def _junction_inputs(surface, evaluation, level, chart_summary=None):
    meshes = (evaluation.cage, *evaluation.levels); _need(level in range(3), "junction level is outside the frozen three-level universe"); owners = tuple(_chart_owners(mesh, chart_summary) for mesh in meshes); result = {}
    for junction in surface.JUNCTIONS:
        domains, (_drop, axes) = surface.JUNCTION_INFO[junction]; maps = tuple(_domain_tags(meshes, owners, domains, index, axes, level, surface) for index in range(2)); reference_map = surface.propagate_junction_tags(evaluation, junction)[level]; reference = tuple(dict(reference_map) for _ in domains); result[junction] = {"incident_domains": domains, "domain_vertex_tags": maps, "expected_domain_vertex_tags": reference}
    return result
def _metric_values(mesh):
    edges = {tuple(sorted((left, face[(slot + 1) % 4]))) for face in mesh.quads for slot, left in enumerate(face)}
    sub = lambda a, b: tuple(a[i] - b[i] for i in range(3)); cross = lambda a, b: (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]); norm = lambda p: math.sqrt(sum(v * v for v in p))
    edge = tuple(norm(sub(mesh.vertices[b], mesh.vertices[a])) for a, b in sorted(edges)); triangles, quads = [], []
    for face in mesh.quads:
        a, b, c, d = (mesh.vertices[i] for i in face); areas = (0.5 * norm(cross(sub(b, a), sub(c, a))), 0.5 * norm(cross(sub(c, a), sub(d, a)))); triangles.extend(areas); quads.append(sum(areas))
    return edge, tuple(triangles), tuple(quads)
def _edge_uses(mesh):
    uses = {}
    for face_index, face in enumerate(mesh.quads):
        for slot, left in enumerate(face):
            right = face[(slot + 1) % 4]; uses.setdefault(tuple(sorted((left, right))), []).append(face_index)
    return uses
def _edge_candidates(uses, owners, boundary, junction_edges):
    result = []
    for edge, faces in uses.items():
        if len(faces) == 1 and edge in boundary: result.append((("edge", edge), "classification", True))
        if len(faces) == 2 and owners[faces[0]] == owners[faces[1]]: result.append((("edge", edge), "classification", True))
        if len(faces) == 2 and edge in junction_edges.get(frozenset(owners[index] for index in faces), ()): result.append((("edge", edge), "classification", True))
    return result
def _fold_samples(mesh, surface, junction, level, mesh_api):
    uses = {}
    for face_index, face in enumerate(mesh.quads):
        for slot, left in enumerate(face): uses.setdefault(tuple(sorted((left, face[(slot + 1) % 4]))), []).append(face_index)
    owners = frozenset(surface.JUNCTION_INFO[junction][0])
    values = tuple(mesh_api.fold_angle_degrees(mesh_api.quad_normal(mesh.vertices, mesh.quads[faces[0]]), mesh_api.quad_normal(mesh.vertices, mesh.quads[faces[1]])) for faces in uses.values() if len(faces) == 2 and frozenset(mesh.face_owners[i] for i in faces) == owners); _need(bool(values), f"no fold samples for {junction} at L{level}"); return values
def _ownership_counts(surface, evaluation, chart_api, mesh_api, geometry_input, formulas, summary, level):
    mesh = (evaluation.cage, *evaluation.levels)[level]; uses = _edge_uses(mesh); expected_counts = LEVEL_COUNTS[level]; _need((len(mesh.control_ids), len(mesh.quads), len(uses), len(surface.PORTS)) == (expected_counts[0], expected_counts[2], expected_counts[1], 5) and sum((expected_counts[0], expected_counts[2], expected_counts[1], 5)) == (456, 1742, 6810)[level], f"ownership element universe changed at L{level}")
    edges = tuple(uses); keys = tuple(("vertex", value) for value in mesh.control_ids) + tuple(("face", value) for value in mesh.face_ids) + tuple(("edge", value) for value in edges) + tuple(("boundary", value) for value in surface.PORTS); required = {key: ("construction", "lineage") if level == 0 and key[0] == "vertex" else ("lineage",) if key[0] == "vertex" else ("chart",) if key[0] == "face" else ("classification",) if key[0] == "edge" else ("boundary",) for key in keys}; expected = chart_api.build_chart_summary(evaluation, formulas); formula_by_id = {row["control_id"]: row for row in formulas}; expected_vertices = {(row["level"], row["vertex_id"]): row for row in expected["vertex_records"]}; expected_faces = {(row["level"], row["face_id"]): row for row in expected["chart_records"]}; records = [( ("vertex", row["control_id"]), "construction", row == formula_by_id.get(row["control_id"]) ) for row in evaluation.cage.formula_records] if level == 0 else []
    records.extend((("vertex", row["vertex_id"]), "lineage", row == expected_vertices.get((level, row["vertex_id"]))) for row in summary["vertex_records"] if row["level"] == level); records.extend((("face", row["face_id"]), "chart", row == expected_faces.get((level, row["face_id"]))) for row in summary["chart_records"] if row["level"] == level)
    owners = mesh.face_owners; junction_edges = {}
    for junction in surface.JUNCTIONS:
        domains = surface.JUNCTION_INFO[junction][0]; cycle = _junction_cycles(mesh, owners, domains)[0]; junction_edges[frozenset(domains)] = {tuple(sorted((left, cycle[(slot + 1) % len(cycle)]))) for slot, left in enumerate(cycle)}
    boundary = {edge for edge, faces in uses.items() if len(faces) == 1}; records.extend(_edge_candidates(uses, owners, boundary, junction_edges)); records.extend((("boundary", port), "boundary", all(edge in boundary for edge in {tuple(sorted((left, loop[(slot + 1) % len(loop)]))) for slot, left in enumerate(loop)}) and len(boundary) == sum(len({tuple(sorted((left, values[(slot + 1) % len(values)]))) for slot, left in enumerate(values)}) for _, values in mesh.boundary_loops)) for port, loop in mesh.boundary_loops)
    return mesh_api.classify_ownership_records(keys, required, tuple(records))
def _invalid_counts(mesh, report, edges, triangles, ownership, surface):
    return {"duplicate_vertex_ids": len(mesh.control_ids) - len(set(mesh.control_ids)), "duplicate_face_ids": len(mesh.face_ids) - len(set(mesh.face_ids)), "degenerate_faces": sum(triangles[2 * index] <= 0.0 or triangles[2 * index + 1] <= 0.0 for index in range(len(mesh.quads))), "zero_length_edges": sum(value == 0.0 for value in edges), "non_manifold_edges": report["topology"].non_manifold_edges, "orientation_conflicts": report["topology"].orientation_conflicts, "unowned_elements": ownership["unowned_elements"], "overowned_elements": ownership["overowned_elements"], "accidental_boundary_components": abs(report["topology"].boundary_components - len(surface.PORTS))}
def _catalog(surface):
    surface.validate_catalogs(); values = {"selected_cells": 58, "un_capped_faces": 122, "domains": 8, "junctions": 7, "ports": 5, "controls": 120, "base_quads": 104, "base_edges": 227, "base_boundary_edges": 38, "boundary_components": 5, "connected_components": 1, "euler_characteristic": -3, "extraordinary_controls": 20, "special_case_ids": 9, "topology_decision_sites": 3}; booleans = "all_domains_nonempty selected_cell_inventory_exact control_catalog_exact face_catalog_exact junction_catalog_exact port_catalog_exact special_case_catalog_exact base_face_controls_distinct base_edge_use_within_two construction_ownership_complete port_caps_exactly_removed axillary_fixture_suite_complete intersection_fixture_suite_complete".split(); gates, thresholds = [], []
    [_put(gates, thresholds, _gate(f"structural.catalog.{name}", 1, value, value, *("le", None, 3) if name == "topology_decision_sites" else ("eq", value, value), "dimensionless" if name == "euler_characteristic" else "count")) for name, value in values.items()]
    [_put(gates, thresholds, _bool(f"structural.catalog_boolean.{name}")) for name in booleans]; return gates, thresholds
def _sample_gate(rows, thresholds, gate_id, values, relation, lower, upper, unit):
    values = tuple(values); _need(bool(values) and all(math.isfinite(value) for value in values), f"{gate_id} has a non-finite or empty raw sample collection"); _put(rows, thresholds, _gate(gate_id, len(values), min(values), max(values), relation, lower, upper, unit))
def _continuity(surface, mesh_api, evaluation, reports, chart_summary=None):
    gates, thresholds, limits = [], [], (90.0, 60.0, 30.0); meshes = (evaluation.cage, *evaluation.levels)
    for level, mesh in enumerate(meshes):
        inputs = _junction_inputs(surface, evaluation, level, chart_summary)
        for junction in surface.JUNCTIONS:
            metrics = mesh_api.junction_continuity_metrics(mesh.vertices, mesh.quads, mesh.face_owners, **inputs[junction]); count = len(metrics["traces"][0]); residuals, folds = metrics["coordinate_residual_samples"], _fold_samples(mesh, surface, junction, level, mesh_api); _need(len(residuals) == 3 * count and len(folds) == count, f"continuity sample cardinality changed for {junction} at L{level}")
            values = (("tag_identity", (1,), "eq", 1, 1, "boolean"), ("opposite_trace_direction", (1,), "eq", 1, 1, "boolean"), ("coordinate_residual", residuals, "le", None, mesh_api.T, "m"), ("fold_angle", folds, "lt", None, limits[level], "degree")); [_sample_gate(gates, thresholds, f"continuity.{junction}.L{level}.{name}", samples, relation, lower, upper, unit) for name, samples, relation, lower, upper, unit in values]
        for port, metric in reports[level]["port_metrics"].items():
            count = len(dict(mesh.boundary_loops)[port]); _need(len(metric["planarity_samples"]) == count and len(metric["co_normal_samples"]) == count, f"port sample cardinality changed for {port} at L{level}"); values = (("orientation", (metric["orientation"],), "ge", .99, None, "dimensionless"), ("planarity", metric["planarity_samples"], "le", None, mesh_api.T, "m"), ("area_ratio", (metric["area_ratio"],), "ge", .0001, None, "dimensionless"), ("co_normal", metric["co_normal_samples"], "ge", .80, None, "dimensionless")); [_sample_gate(gates, thresholds, f"continuity.{port}.L{level}.{name}", samples, relation, lower, upper, unit) for name, samples, relation, lower, upper, unit in values]
    return gates, thresholds
def _geometry(surface, mesh_api, chart, anatomy, geometry_input):
    axillary = anatomy.run_production_axillary_fixtures(); _need(len(axillary) == 13 and tuple(row["fixture_id"] for row in axillary) == anatomy.AXILLARY_FIXTURE_IDS, "axillary production fixture suite did not execute its exact 13 IDs")
    runner = getattr(mesh_api, "run_production_intersection_fixtures", None); _need(runner is not None, "missing required public API: mesh_correctness.run_production_intersection_fixtures (105 cases)")
    fixtures = runner(); _need(len(fixtures) == 105 and tuple(row["fixture_id"] for row in fixtures) == mesh_api.INTERSECTION_FIXTURE_IDS, "intersection production fixture suite did not execute its exact 105 IDs")
    evaluation = surface.evaluate(geometry_input); meshes = (evaluation.cage, *evaluation.levels); formulas = tuple(surface.formula_candidate_records(geometry_input)); chart_summary = chart.build_chart_summary(evaluation, formulas); chart.validate_chart_summary(chart_summary, evaluation, formulas); anatomy.validate_evaluated_surface(evaluation, geometry_input, chart_summary); anatomy_rows = tuple(anatomy.anatomy_gate_records(evaluation, geometry_input, chart_summary))
    expected = tuple(tuple(int(control[1:]) for control in row[2]) for row in surface.FACE_RECORDS); derived = mesh_api.derive_expected_face_catalogs(expected); _need(tuple(len(rows) for rows in derived) == (104, 416, 1664), "independently derived expected topology differs")
    reports, intersection_reports = [], []
    for level, mesh in enumerate(meshes):
        inputs = _junction_inputs(surface, evaluation, level, chart_summary); reports.append(mesh_api.validate_geometry(mesh.vertices, mesh.quads, level, dict(mesh.boundary_loops), _directions(surface), expected, inputs, mesh.face_owners)); intersection_reports.append(mesh_api.intersection_diagnostics(mesh.vertices, mesh.triangles))
    structural, thresholds = [], []; invalid = "duplicate_vertex_ids duplicate_face_ids degenerate_faces zero_length_edges non_manifold_edges orientation_conflicts unowned_elements overowned_elements accidental_boundary_components".split(); chart_counts = {row["level"]: row for row in chart_summary["level_counts"]}
    for level, (mesh, report) in enumerate(zip(meshes, reports)):
        edge, triangles, quads = _metric_values(mesh); top = report["topology"]; [_put(structural, thresholds, _gate(f"structural.L{level}.count.{name}", 1, value, value, "eq", value, value, "count")) for name, value in zip(("vertices", "edges", "quads", "triangles", "boundary_edges"), (len(mesh.vertices), top.edge_count, len(mesh.quads), len(mesh.triangles), top.boundary_edge_count))]
        [_put(structural, thresholds, _bool(f"structural.L{level}.surface_boolean.{name}")) for name in "connected orientable outward_wound boundary_components_match_ports".split()]
        [(_put(structural, thresholds, _bool(f"structural.L{level}.finite.{name}")), structural[-1].__setitem__("sample_count", count)) for name, count in (("coordinates", 3 * len(mesh.vertices)), ("quad_normals", 3 * len(mesh.quads)), ("triangle_areas", len(triangles)), ("quad_areas", len(quads)))]
        [_put(structural, thresholds, _gate(f"structural.L{level}.floor.{name}", len(values), min(values), max(values), "ge", mesh_api.STRUCTURAL_FLOORS[level][name], None, "m" if name == "edge_length" else "m2")) for name, values in (("edge_length", edge), ("triangle_area", triangles), ("quad_area", quads))]
        invalid_values = _invalid_counts(mesh, report, edge, triangles, _ownership_counts(surface, evaluation, chart, mesh_api, geometry_input, formulas, chart_summary, level), surface); [_put(structural, thresholds, _gate(f"structural.L{level}.invalid_count.{name}", 1, invalid_values[name], invalid_values[name], "eq", 0, 0, "count")) for name in invalid]
        [_put(structural, thresholds, _gate(f"structural.L{level}.chart.{name}", 1, chart_counts[level][name], chart_counts[level][name], "eq", chart_counts[level][name], chart_counts[level][name], "count")) for name in ("charts", "interior_transitions", "maximum_samples_per_vertex")]
    for name, limit in (("base_control_contributors", 20), ("dependency_union_keys", 54), ("contributor_domains", 5)):
        rows = [row for row in chart_summary["vertex_records"] if row["level"] == 2]; field = {"base_control_contributors": "base_control_contributors", "dependency_union_keys": "geometry_dependency_union", "contributor_domains": "contributor_domains"}[name]; value = max(len(row[field]) for row in rows); row, threshold = _gate(f"structural.L2.lineage_cap.{name}", 1737, value, value, "le", None, limit, "count"); structural.append(row); thresholds.append(threshold)
    [_put(structural, thresholds, _bool(f"structural.subdivision.{name}")) for name in "recurrence_exact incidence_complete boundary_neighbors_exact face_emission_exact lineage_complete chart_complete transition_complete".split()]
    continuity, continuity_thresholds = _continuity(surface, mesh_api, evaluation, reports, chart_summary); thresholds.extend(continuity_thresholds); thresholds.extend(anatomy.anatomy_threshold_records()); intersection, intersection_thresholds = [], []
    for level, (mesh, report) in enumerate(zip(meshes, intersection_reports)):
        values = (("triangle_count", report["triangle_count"], "eq", len(mesh.triangles), len(mesh.triangles), "count"), ("broad_phase_candidate_count", report["broad_phase_candidate_count"], "le", None, mesh_api.MAX_CANDIDATES, "count"), ("intersection_hit_count", report["intersection_hit_count"], "eq", 0, 0, "count"), ("pair_policy_complete", int(report["pair_policy_complete"]), "eq", 1, 1, "boolean"))
        [_put(intersection, intersection_thresholds, _gate(f"intersection.L{level}.{name}", 1, value, value, relation, lower, upper, unit)) for name, value, relation, lower, upper, unit in values]
    thresholds.extend(intersection_thresholds); thresholds.append({"threshold_id": "gate.boolean-pass", "relation": "eq", "lower": 1, "upper": 1, "unit": "dimensionless"}); _need((len(structural), len(continuity), len(anatomy_rows), len(intersection), len(thresholds)) == (94, 144, 78, 12, 329), "geometry gate inventory is not closed"); return {"evaluation": evaluation, "formula_records": formulas, "chart_summary": chart_summary, "reports": reports, "structural": structural, "continuity": continuity, "anatomy": anatomy_rows, "intersection": intersection, "thresholds": thresholds}
def _support_hash(indices):
    values = tuple(indices)
    if tuple(sorted(set(values))) != values or any(type(index) is not int or not 0 <= index < 1737 for index in values): _fail("support indices are not ascending level-2 indices")
    payload = b"CKSUPPORTv1\0\2" + struct.pack("<I", len(values)) + b"".join(struct.pack("<I", index) for index in values)
    return artifacts.sha256_bytes(payload)
def _causality(surface, render, mesh_api, prepared_api, prepared, geometry):
    geometry_input = prepared_api.project_geometry(prepared)
    baseline = geometry["evaluation"].levels[1]; baseline_shape = (baseline.control_ids, baseline.quads, baseline.formula_ids, baseline.dependencies, baseline.boundary_loops, baseline.face_ids, baseline.face_owners, baseline.vertex_records, baseline.source_stencils); baseline_ply, perturbations, payloads = render.ply_bytes(baseline), [], {}; minimum = float.fromhex("0x1.d14e3bcd35a85p-11")
    if tuple(prepared_api.MUST_AFFECT_PARAMETER_IDS) != PARAMETER_IDS or type(prepared_api.PERTURBATION_DELTA_M) is not float or prepared_api.PERTURBATION_DELTA_M != 0.01: _fail("must-affect inventory or exact binary64 delta differs from the frozen contract")
    for parameter in PARAMETER_IDS:
        component = prepared_api.MUST_AFFECT_COMPONENTS.get(parameter)
        if component is None: _fail(f"missing prepared selector for {parameter}")
        derivative = surface.propagate_derivative(geometry["evaluation"].cage, surface.analytic_control_derivatives(geometry_input, component), level=2)
        predicted = tuple(index for index, point in enumerate(derivative) if any(value != 0.0 for value in point))
        observed_geometry = prepared_api.project_perturbed_geometry(prepared, parameter)
        observed = surface.evaluate(observed_geometry, levels=2).levels[1]
        observed_shape = (observed.control_ids, observed.quads, observed.formula_ids, observed.dependencies, observed.boundary_loops, observed.face_ids, observed.face_owners, observed.vertex_records, observed.source_stencils)
        if observed_shape != baseline_shape: _fail(f"topology or lineage changed for {parameter}")
        movement = tuple(math.sqrt(sum((observed.vertices[index][axis] - baseline.vertices[index][axis]) ** 2 for axis in range(3))) for index in range(1737))
        actual = tuple(index for index, value in enumerate(movement) if value > mesh_api.T); maximum = max(movement)
        if not predicted or actual != predicted or maximum < minimum or any(movement[index] > mesh_api.T for index in range(1737) if index not in predicted): _fail(f"support/movement gate failed for {parameter}")
        if parameter in ("left.thigh_start_x", "right.thigh_start_x") and len(predicted) != 436: _fail(f"hip support cardinality changed for {parameter}")
        role = f"perturb-{parameter.replace('.', '-')}.ply"
        payloads[role] = render.ply_bytes(observed)
        if payloads[role] == baseline_ply: _fail(f"serialized perturbation is unchanged for {parameter}")
        perturbations.append({"parameter_id": parameter, "prepared_component": component, "delta_m": float(prepared_api.PERTURBATION_DELTA_M), "support_level": 2, "predicted_support_count": len(predicted), "observed_support_count": len(actual), "predicted_support_sha256": _support_hash(predicted), "observed_support_sha256": _support_hash(actual), "maximum_movement_m": maximum, "artifact": None})
    return perturbations, payloads
def _manifest_ref(record, schema): return {"role_path": record["role_path"], "bytes": record["bytes"], "sha256": record["sha256"], "schema": schema}
def _write_json(path, value): artifacts.write_canonical_json_no_replace(path, value); return artifacts.regular_file_record(path, path.name)
def _write(path, value): artifacts.write_bytes_no_replace(path, value); return artifacts.regular_file_record(path, path.name)
def _limits(stage, admission):
    records = artifacts.closed_inventory(stage, ARTIFACT_ROLES, max_file_bytes=8 * 1024 * 1024)
    for record in records:
        limit = 8 * 1024 * 1024 if record["role_path"] == "causality-manifest.json" else 2 * 1024 * 1024
        if record["bytes"] > limit: _fail(f"artifact resource cap exceeded: {record['role_path']}")
    production = sum(artifacts.read_regular_file(ROOT / record["role_path"]).count(b"\n") for record in admission["implementation_files"] if "/tests/" not in record["role_path"])
    tests = sum(artifacts.read_regular_file(ROOT / record["role_path"]).count(b"\n") for record in admission["implementation_files"] if "/tests/" in record["role_path"])
    if production > 3400 or tests > 2600: _fail(f"implementation LOC cap exceeded: production={production}, tests={tests}")
    return records
def _now(): return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
def _keys(value, expected, label): return value if type(value) is dict and set(value) == set(expected) else _fail(f"{label} does not have the exact closed keys")
def _text(value, label): return value if type(value) is str and value else _fail(f"{label} must be a nonempty string")
def _integer(value, label, minimum=0): return value if type(value) is int and value >= minimum else _fail(f"{label} must be an integer >= {minimum}")
def _binary64(value, label): return artifacts.coerce_binary64(value, label=label)
def _hex(value, label): return value if type(value) is str and _SHA256.fullmatch(value) is not None else _fail(f"{label} must be lowercase SHA-256")
def _absolute(value, label): return Path(value) if type(value) is str and value and Path(value).is_absolute() and os.path.normpath(value) == value else _fail(f"{label} must be an absolute canonical path")
def _same_json(left, right, label): return None if artifacts.canonical_json_bytes(left) == artifacts.canonical_json_bytes(right) else _fail(f"{label} differs from the frozen value")
def _file_record(value, label, role=None):
    row = _keys(value, ("role_path", "bytes", "sha256"), label)
    try: artifacts.validate_role_path(row["role_path"])
    except Exception as exc: raise BuildError(f"{label}.role_path is invalid") from exc
    _need(role is None or row["role_path"] == role, f"{label}.role_path is not {role}"); _integer(row["bytes"], f"{label}.bytes"); _hex(row["sha256"], f"{label}.sha256"); return row
def _manifest_reference(value, label, role, record): _keys(value, ("role_path", "bytes", "sha256", "schema"), label); _need(value == _manifest_ref(record, MANIFEST_SCHEMAS[role]), f"{label} does not reference the exact admitted manifest"); return value
def _validate_identity(identity):
    row = _keys(identity, ("contract", "source", "profile_table", "runtime", "runtime_bytes", "runtime_fingerprint_sha256", "implementation_files"), "identity"); contract = _file_record(row["contract"], "identity.contract", CONTRACT_ROLE); source = _file_record(row["source"], "identity.source", SOURCE_ROLE); profile = _file_record(row["profile_table"], "identity.profile_table", PROFILE_ROLE)
    if (contract["bytes"], contract["sha256"]) != (173184, EXPECTED_CONTRACT_SHA256) or (source["bytes"], source["sha256"]) != (EXPECTED_SOURCE_BYTES, EXPECTED_SOURCE_SHA256) or (profile["bytes"], profile["sha256"]) != (EXPECTED_PROFILE_BYTES, EXPECTED_PROFILE_SHA256): _fail("identity fixed-file records differ")
    implementation = row["implementation_files"]; _need(type(implementation) in (list, tuple) and len(implementation) == 15, "identity implementation inventory is not exactly 15 files")
    for index, (record, role) in enumerate(zip(implementation, _order(IMPLEMENTATION_ROLES))): _file_record(record, f"identity.implementation_files[{index}]", role)
    runtime_bytes = row["runtime_bytes"]; _need(type(runtime_bytes) is bytes and len(runtime_bytes) <= 64 * 1024 and artifacts.canonical_json_bytes(row["runtime"]) == runtime_bytes and artifacts.sha256_bytes(runtime_bytes) == _hex(row["runtime_fingerprint_sha256"], "identity.runtime_fingerprint_sha256"), "identity runtime bytes or hash differ"); return row
def _canonical_value(raw, value, label):
    _need(type(raw) is bytes, f"{label} raw value must be bytes")
    try: decoded = artifacts.decode_canonical_json(raw)
    except Exception as exc: raise BuildError(f"{label} is not canonical JSON") from exc
    _need(decoded == value and artifacts.canonical_json_bytes(value) == raw, f"{label} value differs from its canonical bytes"); return value
def validate_managed_test_receipt(*, receipt, raw, identity):
    identity = _validate_identity(identity); value = _canonical_value(raw, receipt, "managed-test receipt"); _keys(value, ("schema", "outcome", "literal_invocation", "contract_sha256", "runtime_fingerprint_sha256", "implementation_files", "executed_test_ids", "required_test_ids", "results"), "managed-test receipt")
    _need(value["schema"] == "owned-root-assembly-successor-managed-test-receipt.v1" and value["outcome"] == "success" and value["contract_sha256"] == EXPECTED_CONTRACT_SHA256 and value["runtime_fingerprint_sha256"] == identity["runtime_fingerprint_sha256"] and value["implementation_files"] == list(identity["implementation_files"]), "managed-test receipt identity, schema, or outcome differs")
    invocation = _keys(value["literal_invocation"], ("environment", "argv"), "managed-test receipt invocation"); argv = invocation["argv"]; _need(invocation["environment"] == ["PYTHONHASHSEED=0"] and type(argv) is list and len(argv) == 4 and argv[:3] == ["experiments/owned-root-assembly-successor/build_owned_root.py", "--internal-managed-tests", "--receipt"] and _absolute(argv[3], "managed-test receipt path").name == "managed-test-receipt.json", "managed-test receipt invocation differs")
    executed, required = value["executed_test_ids"], value["required_test_ids"]; _need(type(executed) is list and bool(executed) and all(type(item) is str and item for item in executed) and executed == list(_order(executed)) and len(executed) == len(set(executed)) and required == list(REQUIRED_TEST_IDS) and all(executed.count(item) == 1 for item in REQUIRED_TEST_IDS), "managed-test executed or required IDs differ")
    result = _keys(value["results"], ("tests_run", "failures", "errors", "skipped", "expected_failures", "unexpected_successes"), "managed-test results"); expected = {"tests_run": len(executed), "failures": 0, "errors": 0, "skipped": 0, "expected_failures": 0, "unexpected_successes": 0}
    _need(result == expected and all(type(item) is int for item in result.values()), "managed-test result is not an exact all-pass result")
    return value
def validate_run_report(*, root, seed, report, identity):
    identity = _validate_identity(identity); _need(type(seed) is int and seed in (17, 29), "run report seed must be integer 17 or 29"); root = Path(root); _need(root.is_absolute() and os.path.normpath(str(root)) == str(root) and root.name == f"seed-{seed}" and not root.is_symlink() and root.is_dir(), "run report root is not the exact admitted seed directory")
    value = _keys(report, ("schema", "outcome", "seed", "literal_invocation", "output_path", "staging_path", "python_executable_path", "started_utc", "finished_utc", "timings", "runtime_fingerprint_sha256", "stable_manifest", "gates"), "run report")
    _need(value["schema"] == "owned-root-assembly-successor-run-report.v1" and value["outcome"] == "success" and value["seed"] == seed and type(value["seed"]) is int and value["runtime_fingerprint_sha256"] == identity["runtime_fingerprint_sha256"], "run report identity, schema, outcome, or seed differs")
    invocation = _keys(value["literal_invocation"], ("environment", "argv"), "run report invocation"); _need(invocation == {"environment": [f"PYTHONHASHSEED={seed}"], "argv": ["experiments/owned-root-assembly-successor/build_owned_root.py", "--output", str(root)]} and value["output_path"] == str(root), "run report invocation or output path differs")
    staging = _absolute(value["staging_path"], "run report staging path"); _absolute(value["python_executable_path"], "run report Python executable"); _need(staging.parent == root.parent and staging.name.startswith(f".{root.name}.stage-") and staging != root, "run report staging path is not the builder sibling staging path")
    started, finished = value["started_utc"], value["finished_utc"]; _need(type(started) is str and type(finished) is str and _UTC.fullmatch(started) is not None and _UTC.fullmatch(finished) is not None and finished >= started, "run report timestamps are not ordered fixed UTC timestamps")
    timings = value["timings"]; _need(type(timings) is list and [item.get("phase") if type(item) is dict else None for item in timings] == list(RUN_PHASES), "run report timings differ from the exact phase order")
    for index, item in enumerate(timings): _keys(item, ("phase", "seconds"), f"run report timings[{index}]"); _need(_binary64(item["seconds"], f"run report timings[{index}].seconds") >= 0.0, "run report timing is negative")
    stable = _keys(value["stable_manifest"], ("role_path", "bytes", "sha256", "schema"), "run report stable manifest"); _need(stable["role_path"] == "stable-manifest.json" and stable["schema"] == MANIFEST_SCHEMAS["stable-manifest.json"], "run report stable manifest reference differs"); _integer(stable["bytes"], "run report stable manifest bytes"); _hex(stable["sha256"], "run report stable manifest sha256")
    _need(value["gates"] == [{"gate_id": gate, "outcome": "pass", "sample_count": 1, "observed_min": 1, "observed_max": 1, "threshold_id": "gate.boolean-pass"} for gate in RUN_REPORT_GATES], "run report gate inventory is not the exact six all-pass gates"); return value
def _expected_gate_contract():
    import anatomy_gates as anatomy; import mesh_correctness as mesh_api; import owned_root_surface as surface
    catalog_gates, catalog_thresholds = _catalog(surface); groups = {"structural": [row["gate_id"] for row in catalog_gates], "continuity": [], "anatomy": [], "intersection": []}; thresholds = list(catalog_thresholds)
    def add(group, gate_id, relation, lower, upper, unit): groups[group].append(gate_id); thresholds.append({"threshold_id": f"threshold.{gate_id}", "relation": relation, "lower": lower, "upper": upper, "unit": unit})
    invalid = "duplicate_vertex_ids duplicate_face_ids degenerate_faces zero_length_edges non_manifold_edges orientation_conflicts unowned_elements overowned_elements accidental_boundary_components".split(); chart_counts = ((104, 189, 5), (416, 794, 5), (1664, 3252, 5))
    for level, counts in enumerate(LEVEL_COUNTS):
        for name, count in zip(("vertices", "edges", "quads", "triangles", "boundary_edges"), counts): add("structural", f"structural.L{level}.count.{name}", "eq", count, count, "count")
        for name in "connected orientable outward_wound boundary_components_match_ports".split(): add("structural", f"structural.L{level}.surface_boolean.{name}", "eq", 1, 1, "boolean")
        for name in "coordinates quad_normals triangle_areas quad_areas".split(): add("structural", f"structural.L{level}.finite.{name}", "eq", 1, 1, "boolean")
        for name in ("edge_length", "triangle_area", "quad_area"): add("structural", f"structural.L{level}.floor.{name}", "ge", mesh_api.STRUCTURAL_FLOORS[level][name], None, "m" if name == "edge_length" else "m2")
        for name in invalid: add("structural", f"structural.L{level}.invalid_count.{name}", "eq", 0, 0, "count")
        for name, count in zip(("charts", "interior_transitions", "maximum_samples_per_vertex"), chart_counts[level]): add("structural", f"structural.L{level}.chart.{name}", "eq", count, count, "count")
    for name, limit in (("base_control_contributors", 20), ("dependency_union_keys", 54), ("contributor_domains", 5)): add("structural", f"structural.L2.lineage_cap.{name}", "le", None, limit, "count")
    for name in "recurrence_exact incidence_complete boundary_neighbors_exact face_emission_exact lineage_complete chart_complete transition_complete".split(): add("structural", f"structural.subdivision.{name}", "eq", 1, 1, "boolean")
    for level, fold_limit in enumerate((90.0, 60.0, 30.0)):
        [add("continuity", f"continuity.{junction}.L{level}.{name}", relation, lower, upper, unit) for junction in surface.JUNCTIONS for name, relation, lower, upper, unit in (("tag_identity", "eq", 1, 1, "boolean"), ("opposite_trace_direction", "eq", 1, 1, "boolean"), ("coordinate_residual", "le", None, mesh_api.T, "m"), ("fold_angle", "lt", None, fold_limit, "degree"))]
        [add("continuity", f"continuity.{port}.L{level}.{name}", relation, lower, upper, unit) for port in surface.PORT_INFO for name, relation, lower, upper, unit in (("orientation", "ge", .99, None, "dimensionless"), ("planarity", "le", None, mesh_api.T, "m"), ("area_ratio", "ge", .0001, None, "dimensionless"), ("co_normal", "ge", .80, None, "dimensionless"))]
    [(thresholds.append(threshold), groups["anatomy"].append(threshold["threshold_id"].removeprefix("threshold."))) for threshold in anatomy.anatomy_threshold_records()]
    for level, triangle_count in enumerate((208, 832, 3328)):
        for name, relation, lower, upper, unit in (("triangle_count", "eq", triangle_count, triangle_count, "count"), ("broad_phase_candidate_count", "le", None, mesh_api.MAX_CANDIDATES, "count"), ("intersection_hit_count", "eq", 0, 0, "count"), ("pair_policy_complete", "eq", 1, 1, "boolean")): add("intersection", f"intersection.L{level}.{name}", relation, lower, upper, unit)
    thresholds.append({"threshold_id": "gate.boolean-pass", "relation": "eq", "lower": 1, "upper": 1, "unit": "dimensionless"}); groups = {group: list(_order(ids)) for group, ids in groups.items()}; thresholds = _order_records(thresholds, "threshold_id"); _need(tuple(len(groups[name]) for name in ("structural", "continuity", "anatomy", "intersection")) == (122, 144, 78, 12) and len(thresholds) == 357, "derived validator gate inventory differs from the frozen contract")
    return groups, thresholds
def _validate_gate(row, threshold, label):
    row = _keys(row, ("gate_id", "outcome", "sample_count", "observed_min", "observed_max", "threshold_id"), label)
    if threshold is None or row["outcome"] != "pass" or row["threshold_id"] != f"threshold.{row['gate_id']}": _fail(f"{label} is not linked all-pass evidence")
    _integer(row["sample_count"], f"{label}.sample_count", 1); integer = threshold["unit"] in ("boolean", "count") or threshold["unit"] == "dimensionless" and type(row["observed_min"]) is int and type(row["observed_max"]) is int; minimum = 0 if threshold["unit"] in ("boolean", "count") else -(1 << 63)
    low = _integer(row["observed_min"], f"{label}.observed_min", minimum) if integer else _binary64(row["observed_min"], f"{label}.observed_min"); high = _integer(row["observed_max"], f"{label}.observed_max", minimum) if integer else _binary64(row["observed_max"], f"{label}.observed_max")
    if low > high: _fail(f"{label} has reversed observations")
    relation, lower, upper = threshold["relation"], threshold["lower"], threshold["upper"]
    if not ((low == lower and high == upper) if relation == "eq" else low >= lower if relation == "ge" else high <= upper if relation == "le" else high < upper): _fail(f"{label} does not satisfy its threshold")
def _validate_gate_manifest(value):
    groups, expected = _expected_gate_contract(); thresholds = value["thresholds"]; _need(type(thresholds) is list, "gate thresholds must be a list")
    for index, row in enumerate(thresholds): row = _keys(row, ("threshold_id", "relation", "lower", "upper", "unit"), f"gate threshold[{index}]"); _need(bool(_text(row["threshold_id"], f"gate threshold[{index}].threshold_id")) and row["relation"] in ("eq", "ge", "le", "lt") and row["unit"] in ("boolean", "count", "degree", "dimensionless", "m", "m2"), "gate threshold relation or unit is not admitted")
    _same_json(thresholds, expected, "gate threshold inventory"); threshold_map = {row["threshold_id"]: row for row in thresholds}
    for group, ids in groups.items(): rows = value[group]; _need(type(rows) is list and [row.get("gate_id") if type(row) is dict else None for row in rows] == ids, f"{group} gate IDs are not the exact sorted inventory"); [_validate_gate(row, threshold_map.get(row.get("threshold_id")), f"{group} gate[{index}]") for index, row in enumerate(rows)]
def _bundle_blob(root, role, record_map):
    cap = 8 * 1024 * 1024 if role == "causality-manifest.json" else 2 * 1024 * 1024; raw = artifacts.read_regular_file(root / role, max_bytes=cap); expected = record_map[role]
    _need(expected == {"role_path": role, "bytes": len(raw), "sha256": artifacts.sha256_bytes(raw)}, f"bundle artifact changed while validating: {role}"); return raw
def _closed_inventory(root):
    try: return artifacts.closed_inventory(root, ARTIFACT_ROLES, max_file_bytes=8 * 1024 * 1024)
    except Exception as exc: raise BuildError("bundle closed-inventory admission failed") from exc
def _bundle_json(root, role, record_map):
    raw = _bundle_blob(root, role, record_map)
    try: value = artifacts.decode_canonical_json(raw)
    except Exception as exc: raise BuildError(f"bundle JSON is not canonical: {role}") from exc
    if type(value) is not dict: _fail(f"bundle JSON must be an object: {role}")
    return raw, value
def _parse_ply(raw, role, vertices_count, quads_count, render):
    try: lines = raw.decode("ascii").splitlines()
    except UnicodeDecodeError as exc: raise BuildError(f"PLY is not ASCII: {role}") from exc
    header = ["ply", "format ascii 1.0", f"element vertex {vertices_count}", "property double x", "property double y", "property double z", f"element face {quads_count}", "property list uchar int vertex_indices", "end_header"]
    if not raw.endswith(b"\n") or lines[:9] != header or len(lines) != 9 + vertices_count + quads_count: _fail(f"PLY header or row count differs: {role}")
    try: vertices = tuple(tuple(float(item) for item in line.split()) for line in lines[9:9 + vertices_count]); quads = tuple(tuple(int(item) for item in line.split()[1:]) for line in lines[9 + vertices_count:])
    except ValueError as exc: raise BuildError(f"PLY row is not numeric: {role}") from exc
    if any(len(row) != 3 for row in vertices) or any(len(row) != 4 or line.split()[0] != "4" for row, line in zip(quads, lines[9 + vertices_count:])): _fail(f"PLY row shape differs: {role}")
    try: canonical = render.ply_bytes(vertices, quads)
    except Exception as exc: raise BuildError(f"PLY geometry is invalid: {role}") from exc
    if canonical != raw: _fail(f"PLY bytes are not the exact canonical serialization: {role}")
    return vertices, quads
def _validate_png(raw, role):
    try:
        from PIL import Image
        image = Image.open(io.BytesIO(raw)); _need(image.format == "PNG" and image.mode == "RGB" and image.size == (512, 1536) and not image.info, f"PNG dimensions, mode, or metadata differ: {role}"); image.verify()
    except BuildError: raise
    except Exception as exc: raise BuildError(f"PNG failed exact decoding: {role}") from exc
def validate_seed_bundle(*, root, seed, identity):
    identity = _validate_identity(identity); _need(type(seed) is int and seed in (17, 29), "seed bundle seed must be integer 17 or 29"); root = Path(root); _need(root.is_absolute() and os.path.normpath(str(root)) == str(root) and root.name == f"seed-{seed}" and not root.is_symlink() and root.is_dir(), "seed bundle root is not the exact admitted seed directory")
    records = _closed_inventory(root); record_map = {record["role_path"]: record for record in records}; _limits(root, identity)
    import chart_lineage as chart; import owned_root_surface as surface; import prepared_projection as prepared_api; import render_export as render
    prepared_raw = _bundle_blob(root, "prepared-input.json", record_map)
    try: prepared = prepared_api.admit_prepared_bytes(prepared_raw); geometry_input = prepared_api.project_geometry(prepared)
    except Exception as exc: raise BuildError("prepared-input.json failed fixed projection admission") from exc
    bindings = list(prepared_api.source_binding_records()); manifests = {role: _bundle_json(root, role, record_map)[1] for role in MANIFEST_SCHEMAS}
    input_value = _keys(manifests["input-manifest.json"], ("schema", "contract_sha256", "source", "profile_table", "profile_id", "prepared_input", "source_bindings", "runtime", "implementation_files", "recipe_id"), "input manifest"); recipe_id = _recipe(identity)[1]
    _need(input_value["schema"] == MANIFEST_SCHEMAS["input-manifest.json"] and input_value["contract_sha256"] == EXPECTED_CONTRACT_SHA256 and input_value["source"] == identity["source"] and input_value["profile_table"] == identity["profile_table"] and input_value["profile_id"] == "standard_neutral_reference" and input_value["runtime"] == identity["runtime"] and input_value["implementation_files"] == list(identity["implementation_files"]) and input_value["recipe_id"] == recipe_id and _file_record(input_value["prepared_input"], "input manifest prepared input", "prepared-input.json") == record_map["prepared-input.json"], "input manifest fixed identity, recipe, or prepared record differs"); _same_json(input_value["source_bindings"], bindings, "input manifest source bindings")
    coordinate = _keys(manifests["coordinate-manifest.json"], ("schema", "contract_sha256", "input_manifest", "counts", "coordinate_hashes", "triangle_index_hashes", "surface_artifacts"), "coordinate manifest")
    expected_counts = [{"level": level, "vertices": values[0], "edges": values[1], "quads": values[2], "triangles": values[3], "boundary_edges": values[4]} for level, values in enumerate(LEVEL_COUNTS)]; _need(coordinate["schema"] == MANIFEST_SCHEMAS["coordinate-manifest.json"] and coordinate["contract_sha256"] == EXPECTED_CONTRACT_SHA256 and coordinate["counts"] == expected_counts, "coordinate manifest identity or counts differ"); _manifest_reference(coordinate["input_manifest"], "coordinate input reference", "input-manifest.json", record_map["input-manifest.json"])
    baseline, coordinate_hashes, triangle_hashes = {}, [], []
    for level, role in enumerate(SURFACE_ROLES):
        raw = _bundle_blob(root, role, record_map); vertices, quads = _parse_ply(raw, role, LEVEL_COUNTS[level][0], LEVEL_COUNTS[level][2], render); triangles = tuple(item for a, b, c, d in quads for item in ((a, b, c), (a, c, d))); coordinate_bytes = artifacts.coordinate_hash_bytes(vertices); triangle_bytes = artifacts.triangle_index_hash_bytes(triangles)
        coordinate_hashes.append({"level": level, "bytes": len(coordinate_bytes), "sha256": artifacts.sha256_bytes(coordinate_bytes)}); triangle_hashes.append({"level": level, "bytes": len(triangle_bytes), "sha256": artifacts.sha256_bytes(triangle_bytes)}); baseline[level] = (raw, vertices, quads)
    _need(coordinate["coordinate_hashes"] == coordinate_hashes and coordinate["triangle_index_hashes"] == triangle_hashes and coordinate["surface_artifacts"] == [record_map[role] for role in _order(SURFACE_ROLES)], "coordinate hashes or surface artifact records differ")
    gate = _keys(manifests["gate-manifest.json"], ("schema", "contract_sha256", "coordinate_manifest", "thresholds", "structural", "continuity", "anatomy", "intersection"), "gate manifest")
    _need(gate["schema"] == MANIFEST_SCHEMAS["gate-manifest.json"] and gate["contract_sha256"] == EXPECTED_CONTRACT_SHA256, "gate manifest identity differs"); _manifest_reference(gate["coordinate_manifest"], "gate coordinate reference", "coordinate-manifest.json", record_map["coordinate-manifest.json"]); _validate_gate_manifest(gate)
    causality = _keys(manifests["causality-manifest.json"], ("schema", "contract_sha256", "input_manifest", "formula_records", "source_bindings", "charts", "perturbations"), "causality manifest")
    _need(causality["schema"] == MANIFEST_SCHEMAS["causality-manifest.json"] and causality["contract_sha256"] == EXPECTED_CONTRACT_SHA256, "causality manifest identity differs"); _manifest_reference(causality["input_manifest"], "causality input reference", "input-manifest.json", record_map["input-manifest.json"])
    formulas = tuple(surface.formula_candidate_records(geometry_input)); _same_json(causality["formula_records"], formulas, "causality formula records"); _same_json(causality["source_bindings"], bindings, "causality source bindings")
    evaluation = surface.evaluate(geometry_input)
    try: chart.validate_chart_summary(causality["charts"], evaluation, formulas)
    except Exception as exc: raise BuildError("causality chart summary validation failed") from exc
    for level, mesh in enumerate((evaluation.cage, *evaluation.levels)):
        if render.ply_bytes(mesh) != baseline[level][0]: _fail(f"baseline PLY differs from evaluated level {level}")
    perturbations = causality["perturbations"]; expected_parameters = list(_order(PARAMETER_IDS)); _need(type(perturbations) is list and [item.get("parameter_id") if type(item) is dict else None for item in perturbations] == expected_parameters and tuple(prepared_api.MUST_AFFECT_PARAMETER_IDS) == PARAMETER_IDS and prepared_api.PERTURBATION_DELTA_M == 0.01, "runtime or manifest must-affect inventory differs")
    minimum = float.fromhex("0x1.d14e3bcd35a85p-11")
    for index, row in enumerate(perturbations):
        value = _keys(row, ("parameter_id", "prepared_component", "delta_m", "support_level", "predicted_support_count", "observed_support_count", "predicted_support_sha256", "observed_support_sha256", "maximum_movement_m", "artifact"), f"causality perturbation[{index}]"); parameter, role = value["parameter_id"], f"perturb-{value['parameter_id'].replace('.', '-')}.ply"
        _need(value["prepared_component"] == prepared_api.MUST_AFFECT_COMPONENTS.get(parameter) and _binary64(value["delta_m"], f"causality perturbation[{index}].delta_m") == 0.01 and value["support_level"] == 2 and type(value["support_level"]) is int, f"causality perturbation selector, delta, or level differs: {parameter}")
        predicted = _integer(value["predicted_support_count"], f"causality perturbation[{index}].predicted_support_count", 1); observed = _integer(value["observed_support_count"], f"causality perturbation[{index}].observed_support_count", 1)
        _need(predicted == observed and predicted <= 1737 and value["predicted_support_sha256"] == value["observed_support_sha256"], f"causality support differs between analytic and observed evidence: {parameter}")
        _hex(value["predicted_support_sha256"], f"causality perturbation[{index}].predicted_support_sha256"); _hex(value["observed_support_sha256"], f"causality perturbation[{index}].observed_support_sha256")
        _need(not (parameter in ("left.thigh_start_x", "right.thigh_start_x") and predicted != 436) and _binary64(value["maximum_movement_m"], f"causality perturbation[{index}].maximum_movement_m") >= minimum and _file_record(value["artifact"], f"causality perturbation[{index}].artifact", role) == record_map[role], f"causality support cardinality, movement, or artifact differs: {parameter}")
        perturb_raw = _bundle_blob(root, role, record_map); _, perturb_quads = _parse_ply(perturb_raw, role, LEVEL_COUNTS[2][0], LEVEL_COUNTS[2][2], render)
        if perturb_quads != baseline[2][2] or perturb_raw == baseline[2][0]: _fail(f"causality perturbation topology changed or bytes did not: {parameter}")
    render_value = _keys(manifests["render-manifest.json"], ("schema", "contract_sha256", "coordinate_manifest", "render_config", "visibility", "artifacts"), "render manifest")
    _need(render_value["schema"] == MANIFEST_SCHEMAS["render-manifest.json"] and render_value["contract_sha256"] == EXPECTED_CONTRACT_SHA256, "render manifest identity differs"); _manifest_reference(render_value["coordinate_manifest"], "render coordinate reference", "coordinate-manifest.json", record_map["coordinate-manifest.json"])
    try: render.validate_render_config(render_value["render_config"])
    except Exception as exc: raise BuildError("render configuration validation failed") from exc
    visibility = _keys(render_value["visibility"], ("level", "triangle_count", "triangle_index_sha256", "rule"), "render visibility")
    _need(visibility == {"level": 2, "triangle_count": 3328, "triangle_index_sha256": triangle_hashes[2]["sha256"], "rule": "larger-depth-then-lower-triangle-index"} and render_value["artifacts"] == [record_map[role] for role in _order(("direct.png", "lineage.png"))], "render visibility or artifact records differ")
    for role in ("direct.png", "lineage.png"): _validate_png(_bundle_blob(root, role, record_map), role)
    stable = _keys(manifests["stable-manifest.json"], ("schema", "contract_sha256", "recipe_id", "runtime", "implementation_files", "input_manifest", "coordinate_manifest", "gate_manifest", "causality_manifest", "render_manifest", "artifact_hashes"), "stable manifest")
    _need(stable["schema"] == MANIFEST_SCHEMAS["stable-manifest.json"] and stable["contract_sha256"] == EXPECTED_CONTRACT_SHA256 and stable["recipe_id"] == recipe_id and stable["runtime"] == identity["runtime"] and stable["implementation_files"] == list(identity["implementation_files"]), "stable manifest identity or recipe differs")
    for field, role in (("input_manifest", "input-manifest.json"), ("coordinate_manifest", "coordinate-manifest.json"), ("gate_manifest", "gate-manifest.json"), ("causality_manifest", "causality-manifest.json"), ("render_manifest", "render-manifest.json")):
        _manifest_reference(stable[field], f"stable {field}", role, record_map[role])
    _need(stable["artifact_hashes"] == [record_map[role] for role in STABLE_ARTIFACT_ROLES], "stable artifact hashes are not the exact five stable roles")
    report_raw, report = _bundle_json(root, "report.json", record_map); validate_run_report(root=root, seed=seed, report=report, identity=identity); _manifest_reference(report["stable_manifest"], "report stable manifest", "stable-manifest.json", record_map["stable-manifest.json"])
    _need(_bundle_blob(root, "report.sha256", record_map) == f"{artifacts.sha256_bytes(report_raw)}  report.json\n".encode("ascii"), "report sidecar is not the exact report hash line")
    return manifests
def run_managed_tests(receipt_path):
    _need(os.environ.get("PYTHONHASHSEED") == "0", "managed tests require literal PYTHONHASHSEED=0"); receipt = Path(receipt_path); _need(receipt.is_absolute() and receipt.name == "managed-test-receipt.json" and os.path.normpath(str(receipt)) == str(receipt) and not os.path.lexists(receipt) and not receipt.parent.is_symlink() and not (receipt.parent.exists() and not receipt.parent.is_dir()) and receipt.parent.parent.is_dir(), "managed receipt must be absolute, canonical, fresh, and staging-parented"); before = _static_admission()
    sys.path.insert(0, str(PACKAGE))
    try:
        suite = unittest.TestLoader().discover(str(TESTS), pattern="test_*.py")
        def flatten(value):
            for item in value:
                yield from flatten(item) if isinstance(item, unittest.TestSuite) else (item,)
        tests = tuple(flatten(suite)); ids = tuple(test.id() for test in tests); _need(bool(ids) and len(ids) == len(set(ids)) and all(ids.count(required) == 1 for required in REQUIRED_TEST_IDS), "managed discovery did not produce the exact required fixture IDs"); result = unittest.TestResult(); suite.run(result)
    finally:
        if sys.path and sys.path[0] == str(PACKAGE): sys.path.pop(0)
    after = _static_admission(); snapshot = ("contract", "source", "profile_table", "implementation_files", "runtime_bytes"); _need(all(before[key] == after[key] for key in snapshot), "identity changed during managed tests"); _need(result.testsRun == len(ids) and not (result.failures or result.errors or result.skipped or result.expectedFailures or result.unexpectedSuccesses), "managed tests were not an exact all-pass result")
    value = {"schema": "owned-root-assembly-successor-managed-test-receipt.v1", "outcome": "success", "literal_invocation": {"environment": ["PYTHONHASHSEED=0"], "argv": ["experiments/owned-root-assembly-successor/build_owned_root.py", "--internal-managed-tests", "--receipt", str(receipt)]}, "contract_sha256": EXPECTED_CONTRACT_SHA256, "runtime_fingerprint_sha256": after["runtime_fingerprint_sha256"], "implementation_files": list(after["implementation_files"]), "executed_test_ids": list(_order(ids)), "required_test_ids": list(REQUIRED_TEST_IDS), "results": {"tests_run": len(ids), "failures": 0, "errors": 0, "skipped": 0, "expected_failures": 0, "unexpected_successes": 0}}
    receipt.parent.mkdir(exist_ok=True); artifacts.write_canonical_json_no_replace(receipt, value); return value
def build_seed(output_path):
    _need(os.environ.get("PYTHONHASHSEED") in ("17", "29"), "seed builder requires literal PYTHONHASHSEED=17 or 29"); output = Path(output_path); _need(output.is_absolute() and os.path.normpath(str(output)) == str(output) and not os.path.lexists(output) and output.parent.is_dir(), "seed output must be an absolute canonical fresh path"); started, clock, stage, timings = _now(), time.perf_counter(), None, []
    try:
        mark = time.perf_counter(); admission = _static_admission(); recipe, recipe_id = _recipe(admission); timings.append({"phase": "identity", "seconds": float(time.perf_counter() - mark)})
        mark = time.perf_counter(); import prepared_projection as prepared_api; prepared = prepared_api.prepare_standard_neutral(); prepared_api.validate_prepared(prepared); prepared_bytes = prepared_api.canonical_json_bytes(prepared); prepared_api.admit_prepared_bytes(prepared_bytes); geometry_input = prepared_api.project_geometry(prepared); bindings = prepared_api.source_binding_records(); timings.append({"phase": "prepared-input", "seconds": float(time.perf_counter() - mark)})
        mark = time.perf_counter(); import anatomy_gates as anatomy; import chart_lineage as chart; import mesh_correctness as mesh_api; import owned_root_surface as surface; import render_export as render; catalog, catalog_thresholds = _catalog(surface); timings.append({"phase": "catalogs", "seconds": float(time.perf_counter() - mark)})
        mark = time.perf_counter(); geometry = _geometry(surface, mesh_api, chart, anatomy, geometry_input); geometry["structural"] = catalog + geometry["structural"]; geometry["thresholds"] = catalog_thresholds + geometry["thresholds"]
        _need(len(geometry["structural"]) == 122 and len(geometry["thresholds"]) == 357, "closed gate inventory count mismatch"); timings.append({"phase": "geometry-gates", "seconds": float(time.perf_counter() - mark)})
        mark = time.perf_counter(); perturbations, perturb_payloads = _causality(surface, render, mesh_api, prepared_api, prepared, geometry); timings.append({"phase": "causality", "seconds": float(time.perf_counter() - mark)})
        mark = time.perf_counter(); stage = Path(tempfile.mkdtemp(prefix=f".{output.name}.stage-", dir=output.parent)); prepared_record = _write(stage / "prepared-input.json", prepared_bytes); meshes = (geometry["evaluation"].cage, *geometry["evaluation"].levels); surface_records, coordinates, triangle_hashes = [], [], []
        for role, mesh in zip(SURFACE_ROLES, meshes): surface_records.append(_write(stage / role, render.ply_bytes(mesh))); coordinate_bytes = artifacts.coordinate_hash_bytes(mesh.vertices); index_bytes = artifacts.triangle_index_hash_bytes(mesh.triangles); coordinates.append({"level": mesh.level, "bytes": len(coordinate_bytes), "sha256": artifacts.sha256_bytes(coordinate_bytes)}); triangle_hashes.append({"level": mesh.level, "bytes": len(index_bytes), "sha256": artifacts.sha256_bytes(index_bytes)})
        for index, role in enumerate(PERTURBATION_ROLES): _write(stage / role, perturb_payloads[role]); perturbations[index]["artifact"] = artifacts.regular_file_record(stage / role, role)
        direct, lineage, visibility = render.render_pair_bytes(meshes[-1]); direct_record, lineage_record = _write(stage / "direct.png", direct), _write(stage / "lineage.png", lineage)
        input_manifest = {"schema": "owned-root-assembly-successor-input-manifest.v1", "contract_sha256": EXPECTED_CONTRACT_SHA256, "source": admission["source"], "profile_table": admission["profile_table"], "profile_id": "standard_neutral_reference", "prepared_input": prepared_record, "source_bindings": list(bindings), "runtime": admission["runtime"], "implementation_files": list(admission["implementation_files"]), "recipe_id": recipe_id}; input_record = _write_json(stage / "input-manifest.json", input_manifest)
        coordinate_manifest = {"schema": "owned-root-assembly-successor-coordinate-manifest.v1", "contract_sha256": EXPECTED_CONTRACT_SHA256, "input_manifest": _manifest_ref(input_record, input_manifest["schema"]), "counts": [{"level": level, "vertices": len(mesh.vertices), "edges": report["topology"].edge_count, "quads": len(mesh.quads), "triangles": len(mesh.triangles), "boundary_edges": report["topology"].boundary_edge_count} for level, (mesh, report) in enumerate(zip(meshes, geometry["reports"]))], "coordinate_hashes": coordinates, "triangle_index_hashes": triangle_hashes, "surface_artifacts": sorted(surface_records, key=lambda record: record["role_path"].encode("utf-8"))}; coordinate_record = _write_json(stage / "coordinate-manifest.json", coordinate_manifest)
        gate_manifest = {"schema": "owned-root-assembly-successor-gate-manifest.v1", "contract_sha256": EXPECTED_CONTRACT_SHA256, "coordinate_manifest": _manifest_ref(coordinate_record, coordinate_manifest["schema"]), "thresholds": _order_records(geometry["thresholds"], "threshold_id"), "structural": _order_records(geometry["structural"], "gate_id"), "continuity": _order_records(geometry["continuity"], "gate_id"), "anatomy": _order_records(geometry["anatomy"], "gate_id"), "intersection": _order_records(geometry["intersection"], "gate_id")}; _validate_gate_manifest(gate_manifest); gate_record = _write_json(stage / "gate-manifest.json", gate_manifest)
        causality_manifest = {"schema": "owned-root-assembly-successor-causality-manifest.v1", "contract_sha256": EXPECTED_CONTRACT_SHA256, "input_manifest": _manifest_ref(input_record, input_manifest["schema"]), "formula_records": list(geometry["formula_records"]), "source_bindings": list(bindings), "charts": geometry["chart_summary"], "perturbations": list(_order_records(perturbations, "parameter_id"))}; causality_record = _write_json(stage / "causality-manifest.json", causality_manifest)
        render_manifest = {"schema": "owned-root-assembly-successor-render-manifest.v1", "contract_sha256": EXPECTED_CONTRACT_SHA256, "coordinate_manifest": _manifest_ref(coordinate_record, coordinate_manifest["schema"]), "render_config": render.render_config_record(), "visibility": render.visibility_record(visibility), "artifacts": sorted((direct_record, lineage_record), key=lambda record: record["role_path"].encode("utf-8"))}; render_record = _write_json(stage / "render-manifest.json", render_manifest)
        stable_artifacts = sorted((*surface_records, direct_record, lineage_record), key=lambda record: record["role_path"].encode("utf-8")); stable_manifest = {"schema": "owned-root-assembly-successor-stable-manifest.v1", "contract_sha256": EXPECTED_CONTRACT_SHA256, "recipe_id": recipe_id, "runtime": admission["runtime"], "implementation_files": list(admission["implementation_files"]), "input_manifest": _manifest_ref(input_record, input_manifest["schema"]), "coordinate_manifest": _manifest_ref(coordinate_record, coordinate_manifest["schema"]), "gate_manifest": _manifest_ref(gate_record, gate_manifest["schema"]), "causality_manifest": _manifest_ref(causality_record, causality_manifest["schema"]), "render_manifest": _manifest_ref(render_record, render_manifest["schema"]), "artifact_hashes": stable_artifacts}; stable_record = _write_json(stage / "stable-manifest.json", stable_manifest); timings.append({"phase": "serialization", "seconds": float(time.perf_counter() - mark)})
        report = {"schema": "owned-root-assembly-successor-run-report.v1", "outcome": "success", "seed": int(os.environ["PYTHONHASHSEED"]), "literal_invocation": {"environment": [f"PYTHONHASHSEED={os.environ['PYTHONHASHSEED']}"], "argv": ["experiments/owned-root-assembly-successor/build_owned_root.py", "--output", str(output)]}, "output_path": str(output), "staging_path": str(stage), "python_executable_path": str(Path(sys.executable).absolute()), "started_utc": started, "finished_utc": _now(), "timings": timings + [{"phase": "total-before-seal", "seconds": float(time.perf_counter() - clock)}], "runtime_fingerprint_sha256": admission["runtime_fingerprint_sha256"], "stable_manifest": _manifest_ref(stable_record, stable_manifest["schema"]), "gates": [{"gate_id": gate, "outcome": "pass", "sample_count": 1, "observed_min": 1, "observed_max": 1, "threshold_id": "gate.boolean-pass"} for gate in RUN_REPORT_GATES]}
        report_bytes = artifacts.canonical_json_bytes(report); _write(stage / "report.json", report_bytes); _write(stage / "report.sha256", f"{artifacts.sha256_bytes(report_bytes)}  report.json\n".encode("ascii")); inventory = _limits(stage, admission); artifacts.publish_no_replace(stage, output, inventory, max_file_bytes=8 * 1024 * 1024); stage = None; return output
    except Exception:
        if stage is not None and stage.exists(): shutil.rmtree(stage)
        raise
def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    try:
        if argv[:1] == ["--internal-managed-tests"] and len(argv) == 3 and argv[1] == "--receipt": run_managed_tests(argv[2]); return 0
        if argv[:1] == ["--output"] and len(argv) == 2: build_seed(argv[1]); return 0
        _fail("private builder accepts only --internal-managed-tests --receipt ABS or --output ABS")
    except Exception as exc: print(f"build_owned_root: error: {exc}", file=sys.stderr); return 1
if __name__ == "__main__": raise SystemExit(main())
