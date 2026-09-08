"""Independent checks for the planned connected-leg staging experiment.

This module is deliberately a checker only.  It does not build geometry, call
the binding implementation, repair meshes, or select a morphology.  Missing
protocol information is reported as unavailable and never becomes a pass.
"""

from __future__ import annotations

from collections import defaultdict
import copy
import hashlib
import importlib.util
import math
from pathlib import Path
import sys
from typing import Any, Iterable, Mapping, Sequence


_JOINTS = ("pelvis", "left_hip", "left_knee", "right_hip", "right_knee")
_WEIGHT_COLUMNS = ("pelvis", "left_thigh", "left_shank", "right_thigh", "right_shank")
_ARM_JOINTS = (*_JOINTS, "left_shoulder", "left_elbow", "right_shoulder", "right_elbow")
_ARM_WEIGHT_COLUMNS = (*_WEIGHT_COLUMNS, "left_upper_arm", "left_forearm",
                       "right_upper_arm", "right_forearm")
_HEAD_JOINTS = (*_JOINTS, "neck")
_HEAD_WEIGHT_COLUMNS = (*_WEIGHT_COLUMNS, "neck")
_ARM_HEAD_JOINTS = (*_ARM_JOINTS, "neck")
_ARM_HEAD_WEIGHT_COLUMNS = (*_ARM_WEIGHT_COLUMNS, "neck")
_SIDES = ("left", "right")
_OLD_ROOT_VERTEX_COUNT = 152
_OLD_WEIGHT_COLUMNS = ("pelvis", "left_leg", "right_leg")
_FIXED_PRIOR_COLUMN_MAP = (0, 1, 3)
_STATION_NAMES = (
    "mid_thigh", "knee_pre_support", "knee", "knee_post_support",
    "calf", "ankle_approach", "ankle",
)
_STATION_SHANK_WEIGHTS = (0.0, 0.0, 0.5, 1.0, 1.0, 1.0, 1.0)
_ARM_SECTION_NAMES = (
    "upper_belly", "pre_elbow", "elbow", "post_elbow", "forearm_belly",
    "pre_wrist", "wrist", "palm", "knuckle", "terminal",
)
_ARM_FRAME_SOURCE = "source J->E and E->W bones; not construction P->E/E->W sections"
_HEAD_FRAME_SOURCE = "world-aligned at source stations.neck_collar.C"
_TAIL_SUPPORT_OWN = 0.55
_TAIL_SUPPORT_OTHER = 0.15
_MAX_COLLISION_BLOCK = 1800
_EXAMPLE_CAP = 8

_FROZEN_CORE = Path(
    "/home/ben/.cache/creature-kernel/pelvis-thigh-transition/"
    "attempt-2-snapshot/source/experiments/owned-root-assembly-successor/"
    "mesh_correctness.py"
)
_BROADPHASE: Any | None = None


def _report(schema: str) -> dict[str, Any]:
    return {
        "schema": schema,
        "pass": False,
        "available": True,
        "outcome": "fail",
        "checks": {},
        "metrics": {},
        "diagnostics": {},
        "uncertainties": [],
        "errors": [],
    }


def _error(report: dict[str, Any], code: str, detail: str, **data: Any) -> None:
    row: dict[str, Any] = {"code": code, "detail": detail}
    row.update(data)
    report["errors"].append(row)


def _unavailable(report: dict[str, Any], code: str, detail: str, **data: Any) -> None:
    report["available"] = False
    _error(report, code, detail, **data)


def _finish(report: dict[str, Any]) -> dict[str, Any]:
    values = list(report["checks"].values())
    report["pass"] = bool(report["available"] and not report["errors"] and values and all(values))
    report["outcome"] = "pass" if report["pass"] else "unavailable" if not report["available"] else "fail"
    return report


def _mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{label} must be a mapping")
    return value


def _sequence(value: Any, label: str) -> list[Any]:
    if isinstance(value, (str, bytes, bytearray)) or value is None:
        raise ValueError(f"{label} must be a sequence")
    try:
        result = list(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be a sequence") from exc
    return result


def _number(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{label} must be numeric")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{label} must be finite")
    return result


def _vector(value: Any, label: str) -> tuple[float, float, float]:
    values = _sequence(value, label)
    if len(values) != 3:
        raise ValueError(f"{label} must have three components")
    return tuple(_number(item, f"{label}[{index}]") for index, item in enumerate(values))  # type: ignore[return-value]


def _matrix(value: Any, label: str) -> list[list[float]]:
    raw = _sequence(value, label)
    if len(raw) == 16:
        raw = [raw[index:index + 4] for index in range(0, 16, 4)]
    if len(raw) != 4 or any(not isinstance(row, Sequence) or len(row) != 4 for row in raw):
        raise ValueError(f"{label} must be a 4x4 matrix")
    result = [[_number(item, f"{label}[{r}][{c}]") for c, item in enumerate(row)] for r, row in enumerate(raw)]
    return result


def _mesh(mesh: Any, label: str) -> dict[str, Any]:
    value = _mapping(mesh, label)
    raw_vertices = _sequence(value.get("vertices"), f"{label}.vertices")
    vertices = [_vector(point, f"{label}.vertices[{index}]") for index, point in enumerate(raw_vertices)]
    if not vertices:
        raise ValueError(f"{label}.vertices must not be empty")
    raw_quads = _sequence(value.get("quads"), f"{label}.quads")
    quads: list[tuple[int, int, int, int]] = []
    for face_index, raw_face in enumerate(raw_quads):
        face = _sequence(raw_face, f"{label}.quads[{face_index}]")
        if len(face) != 4 or any(isinstance(index, bool) or not isinstance(index, int) for index in face):
            raise ValueError(f"{label}.quads[{face_index}] must contain four integer indices")
        checked = tuple(int(index) for index in face)
        if len(set(checked)) != 4 or any(index < 0 or index >= len(vertices) for index in checked):
            raise ValueError(f"{label}.quads[{face_index}] contains an invalid index")
        quads.append(checked)  # type: ignore[arg-type]
    if not quads:
        raise ValueError(f"{label}.quads must not be empty")
    return {
        "value": value,
        "vertices": vertices,
        "quads": quads,
        "face_owners": value.get("face_owners"),
        "loops": value.get("loops", value.get("boundary_loops")),
        "stencils": value.get("base_stencils"),
        "metadata": value.get("metadata", {}),
    }


def _edge_incidence(quads: Sequence[Sequence[int]]) -> dict[tuple[int, int], list[tuple[int, int, int]]]:
    result: dict[tuple[int, int], list[tuple[int, int, int]]] = defaultdict(list)
    for face_index, face in enumerate(quads):
        for slot, start in enumerate(face):
            end = face[(slot + 1) % 4]
            result[(min(start, end), max(start, end))].append((face_index, start, end))
    return dict(result)


def _boundary_cycles(incidence: Mapping[tuple[int, int], Sequence[tuple[int, int, int]]]) -> list[list[int]]:
    outgoing: dict[int, list[int]] = defaultdict(list)
    for uses in incidence.values():
        if len(uses) == 1:
            _, start, end = uses[0]
            outgoing[start].append(end)
    if any(len(targets) != 1 for targets in outgoing.values()):
        raise ValueError("boundary edges do not form directed cycles")
    next_vertex = {start: targets[0] for start, targets in outgoing.items()}
    remaining = set(next_vertex)
    result: list[list[int]] = []
    while remaining:
        start = min(remaining)
        current = start
        cycle: list[int] = []
        while current in remaining:
            remaining.remove(current)
            cycle.append(current)
            current = next_vertex[current]
        if current != start or len(cycle) < 3:
            raise ValueError("boundary edge cycle is not closed")
        result.append(cycle)
    return result


def _cyclic_equal(actual: Sequence[int], expected: Sequence[int]) -> bool:
    left = tuple(actual)
    right = tuple(expected)
    return any(left == target[index:] + target[:index]
               for target in (right, tuple(reversed(right)))
               for index in range(len(right)))


def _connected_components(quads: Sequence[Sequence[int]], vertex_count: int) -> int:
    adjacency = [set() for _ in range(vertex_count)]
    for face in quads:
        for left, right in zip(face, face[1:] + face[:1]):
            adjacency[left].add(right)
            adjacency[right].add(left)
    unseen = set(range(vertex_count))
    count = 0
    while unseen:
        count += 1
        todo = [unseen.pop()]
        while todo:
            for neighbour in adjacency[todo.pop()].intersection(unseen):
                unseen.remove(neighbour)
                todo.append(neighbour)
    return count


def _cross(a: Sequence[float], b: Sequence[float]) -> tuple[float, float, float]:
    return (a[1] * b[2] - a[2] * b[1],
            a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0])


def _sub(a: Sequence[float], b: Sequence[float]) -> tuple[float, float, float]:
    return tuple(float(a[index]) - float(b[index]) for index in range(3))  # type: ignore[return-value]


def _add(a: Sequence[float], b: Sequence[float]) -> tuple[float, float, float]:
    return tuple(float(a[index]) + float(b[index]) for index in range(3))  # type: ignore[return-value]


def _scale(a: Sequence[float], factor: float) -> tuple[float, float, float]:
    return tuple(float(value) * factor for value in a)  # type: ignore[return-value]


def _dot(a: Sequence[float], b: Sequence[float]) -> float:
    return sum(float(a[index]) * float(b[index]) for index in range(3))


def _norm(a: Sequence[float]) -> float:
    return math.sqrt(_dot(a, a))


def _distance(a: Sequence[float], b: Sequence[float]) -> float:
    return _norm(_sub(a, b))


def _triangles(quads: Sequence[Sequence[int]]) -> list[tuple[int, int, int]]:
    return [triangle for face in quads for triangle in ((face[0], face[1], face[2]), (face[0], face[2], face[3]))]


def _triangle_normal(vertices: Sequence[Sequence[float]], triangle: Sequence[int]) -> tuple[float, float, float]:
    return _cross(_sub(vertices[triangle[1]], vertices[triangle[0]]),
                  _sub(vertices[triangle[2]], vertices[triangle[0]]))


def _triangle_area(vertices: Sequence[Sequence[float]], triangle: Sequence[int]) -> float:
    return 0.5 * _norm(_triangle_normal(vertices, triangle))


def _limit(protocol: Mapping[str, Any], names: Sequence[str]) -> float | tuple[float, float] | None:
    pending: list[Mapping[str, Any]] = [protocol]
    sources: list[Mapping[str, Any]] = []
    while pending:
        source = pending.pop(0)
        sources.append(source)
        pending.extend(value for value in source.values() if isinstance(value, Mapping))
    for source in sources:
        for name in names:
            if name in source:
                value = source[name]
                if isinstance(value, Sequence) and not isinstance(value, (str, bytes)) and len(value) == 2:
                    return (_number(value[0], name), _number(value[1], name))
                return _number(value, name)
    return None


def _require_limit(report: dict[str, Any], protocol: Mapping[str, Any], names: Sequence[str]) -> float | tuple[float, float]:
    value = _limit(protocol, names)
    if value is None:
        _unavailable(report, "missing_protocol_threshold", f"protocol threshold is required: {names[0]}")
        raise ValueError(f"missing protocol threshold {names[0]}")
    return value


def _owner_is_inherited_lower(owner: Any) -> bool:
    if not isinstance(owner, str):
        return False
    normal = owner.lower().replace("-", "_").replace(" ", "_")
    return any(word in normal for word in ("pelvis", "hip", "abdomen"))


def _prior_face_count(mesh: Mapping[str, Any], protocol: Mapping[str, Any]) -> int | None:
    metadata = mesh.get("metadata")
    for source in (protocol, protocol.get("checks"), metadata):
        if isinstance(source, Mapping):
            for key in ("prior_face_count", "new_face_start", "original_face_count"):
                if key in source:
                    value = source[key]
                    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                        return None
                    return value
    if isinstance(metadata, Mapping):
        root = metadata.get("root")
        if isinstance(root, Mapping):
            value = root.get("face_count")
            level = mesh.get("level", metadata.get("level", 0))
            if (isinstance(value, int) and not isinstance(value, bool) and value >= 0
                    and isinstance(level, int) and not isinstance(level, bool)
                    and level >= 0):
                return value * (4 ** level)
    return None


def _lower_faces(parsed: Mapping[str, Any], protocol: Mapping[str, Any]) -> tuple[set[int], set[int], int | None]:
    owners = parsed.get("face_owners")
    if not isinstance(owners, Sequence) or len(owners) != len(parsed["quads"]):
        raise ValueError("face_owners must cover every face for lower collision checks")
    start = _prior_face_count(parsed["value"], protocol)
    if start is None or start > len(owners):
        raise ValueError("prior_face_count/new_face_start is required and must fit the face array")
    lower = {index for index in range(start) if _owner_is_inherited_lower(owners[index])}
    lower.update(range(start, len(owners)))
    upper = set(range(start)).difference(lower)
    return lower, upper, start


def _load_intersection_core() -> Any:
    path = _FROZEN_CORE
    if not path.is_file() or path.is_symlink():
        return None
    spec = importlib.util.spec_from_file_location("connected_leg_generic_intersection", path)
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    function = getattr(module, "intersection_diagnostics", None)
    if callable(function):
        return function
    return None


def _load_broadphase() -> Any:
    """Load the captured broadphase wrapper beside this checker."""
    path = Path(__file__).resolve().with_name("collision_broadphase.py")
    if not path.is_file() or path.is_symlink():
        return None
    spec = importlib.util.spec_from_file_location(
        "connected_leg_collision_broadphase", path
    )
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        if sys.modules.get(spec.name) is module:
            sys.modules.pop(spec.name, None)
        return None
    if Path(str(module.__file__)).resolve() != path:
        return None
    return module


def _set_broadphase(module: Any) -> None:
    """Install the already-captured wrapper loaded by the runner."""
    global _BROADPHASE
    _BROADPHASE = module


def _frozen_core_sha256() -> str | None:
    try:
        if not _FROZEN_CORE.is_file() or _FROZEN_CORE.is_symlink():
            return None
        digest = hashlib.sha256()
        with _FROZEN_CORE.open("rb") as handle:
            for block in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(block)
        return digest.hexdigest()
    except OSError:
        return None


def _foot_collision_report(vertices: Sequence[Sequence[float]],
                           quads: Sequence[Sequence[int]],
                           owners: Sequence[str], lower_faces: set[int],
                           upper_faces: set[int]) -> dict[str, Any]:
    """Adapt the accepted broadphase report to the checker face inventory.

    The wrapper owns broadphase, frozen narrowphase, and complete pair
    accounting.  This adapter only maps triangle ids to quad faces and keeps
    the existing lower/upper ownership classification.
    """
    result: dict[str, Any] = {
        "available": False,
        "coverage_complete": False,
        "vertex_array_reused": True,
        "method": None,
        "narrowphase": None,
        "blocks": [],
        "calls": [],
        "hit_triangle_pairs": [],
        "hit_face_pairs": [],
        "lower_hit_pairs": [],
        "upper_only_hit_pairs": [],
        "errors": [],
        "intersection_core_path": str(_FROZEN_CORE),
        "intersection_core_sha256": _frozen_core_sha256(),
        "scope": {"triangle_count": 0, "pair_count": 0,
                  "complete_pair_accounting": False},
    }
    triangles = _triangles(quads)
    result["scope"]["triangle_count"] = len(triangles)
    if not triangles:
        result["errors"].append({
            "code": "empty_triangle_inventory",
            "detail": "collision inventory is empty",
        })
        return result
    broadphase = _BROADPHASE or _load_broadphase()
    collision_report = getattr(broadphase, "collision_report", None)
    declared_core = getattr(broadphase, "FROZEN_CORE_PATH", None)
    if (not callable(collision_report) or declared_core is None
            or Path(str(declared_core)).resolve() != _FROZEN_CORE.resolve()):
        result["errors"].append({
            "code": "broadphase_unavailable",
            "detail": "accepted collision broadphase wrapper or pinned core is unavailable",
            "wrapper_core_path": str(declared_core) if declared_core is not None else None,
        })
        return result
    result["method"] = getattr(broadphase, "METHOD", None)
    try:
        wrapped = collision_report(vertices, triangles, include_classifications=False)
        if not isinstance(wrapped, Mapping):
            raise ValueError("collision broadphase report must be an object")
        result["narrowphase"] = wrapped.get("narrowphase")
        result["blocks"] = wrapped.get("blocks", [])
        result["pair_partition_complete"] = bool(wrapped.get("pair_partition_complete"))
        result["final_classification_partition_complete"] = bool(
            wrapped.get("final_classification_partition_complete")
        )
        result["class_counts"] = wrapped.get("class_counts", {})
        result["survivor_pair_count"] = wrapped.get("survivor_pair_count")
        result["hit_pairs_truncated"] = bool(wrapped.get("hit_pairs_truncated"))
        result["scope"]["pair_count"] = wrapped.get("pair_count", 0)
        result["scope"]["complete_pair_accounting"] = bool(
            wrapped.get("pair_partition_complete")
            and wrapped.get("final_classification_partition_complete")
            and not wrapped.get("hit_pairs_truncated")
        )
        result["coverage_complete"] = result["scope"]["complete_pair_accounting"]
        result["errors"].extend(list(wrapped.get("errors", ())))
        result["candidate_pairs_truncated"] = bool(wrapped.get("candidate_pairs_truncated"))
        result["nontrivial_evidence_truncated"] = bool(wrapped.get("nontrivial_evidence_truncated"))
        result["expected_pair_count"] = wrapped.get("pair_count")
        result["covered_pair_count"] = (
            wrapped.get("pair_count") if result["coverage_complete"] else
            wrapped.get("survivor_pair_count")
        )
        result["hit_triangle_pairs"] = [
            list(pair) for pair in wrapped.get("hit_pairs", ())
        ]
        seen_faces: set[tuple[int, int]] = set()
        for raw_pair in result["hit_triangle_pairs"]:
            if len(raw_pair) != 2:
                result["errors"].append({
                    "code": "malformed_hit_pair",
                    "detail": "broadphase returned a non-pair hit record",
                })
                continue
            triangle_pair = tuple(sorted((int(raw_pair[0]), int(raw_pair[1]))))
            face_pair = tuple(sorted((triangle_pair[0] // 2, triangle_pair[1] // 2)))
            if face_pair[0] == face_pair[1] or face_pair in seen_faces:
                continue
            if any(index < 0 or index >= len(owners) for index in face_pair):
                result["errors"].append({
                    "code": "hit_face_out_of_range",
                    "detail": "broadphase hit pair mapped outside face ownership",
                    "triangles": list(triangle_pair),
                })
                continue
            seen_faces.add(face_pair)
            row = {"triangles": list(triangle_pair), "faces": list(face_pair),
                   "owners": [owners[face_pair[0]], owners[face_pair[1]]]}
            result["hit_face_pairs"].append(row)
            if face_pair[0] in lower_faces or face_pair[1] in lower_faces:
                result["lower_hit_pairs"].append(row)
            elif face_pair[0] in upper_faces and face_pair[1] in upper_faces:
                result["upper_only_hit_pairs"].append(row)
        result["global_face_pair_count"] = len(seen_faces)
        result["available"] = bool(wrapped.get("available") and
                                    result["coverage_complete"] and
                                    not result["errors"])
    except Exception as exc:
        result["errors"].append({"code": "broadphase_failure", "detail": str(exc)})
    result["hit_triangle_pairs"] = sorted(result["hit_triangle_pairs"])
    result["hit_face_pairs"] = sorted(result["hit_face_pairs"], key=lambda row: tuple(row["faces"]))
    result["lower_hit_pairs"] = sorted(result["lower_hit_pairs"], key=lambda row: tuple(row["faces"]))
    result["upper_only_hit_pairs"] = sorted(result["upper_only_hit_pairs"], key=lambda row: tuple(row["faces"]))
    result["pass"] = bool(result["available"] and not result["lower_hit_pairs"])
    return result


def _collision_report(vertices: Sequence[Sequence[float]], quads: Sequence[Sequence[int]],
                      owners: Sequence[str], lower_faces: set[int], upper_faces: set[int]) -> dict[str, Any]:
    result: dict[str, Any] = {
        "available": False,
        "coverage_complete": False,
        "vertex_array_reused": True,
        "block_size": _MAX_COLLISION_BLOCK,
        "blocks": [],
        "calls": [],
        "hit_triangle_pairs": [],
        "hit_face_pairs": [],
        "lower_hit_pairs": [],
        "upper_only_hit_pairs": [],
        "errors": [],
        "intersection_core_path": str(_FROZEN_CORE),
    }
    triangles = _triangles(quads)
    if not triangles:
        result["errors"].append({"code": "empty_triangle_inventory", "detail": "collision inventory is empty"})
        return result
    intersection_diagnostics = _load_intersection_core()
    if intersection_diagnostics is None:
        result["errors"].append({"code": "intersection_unavailable", "detail": "generic intersection diagnostic could not be loaded"})
        return result

    blocks = [list(range(start, min(start + _MAX_COLLISION_BLOCK, len(triangles))))
              for start in range(0, len(triangles), _MAX_COLLISION_BLOCK)]
    result["blocks"] = [{"block": index, "triangle_ids": ids, "triangle_count": len(ids)}
                         for index, ids in enumerate(blocks)]
    seen_triangle_pairs: set[tuple[int, int]] = set()
    seen_face_pairs: set[tuple[int, int]] = set()
    expected_pairs = len(triangles) * (len(triangles) - 1) // 2
    covered_pairs = 0

    for first_block in range(len(blocks)):
        for second_block in range(first_block, len(blocks)):
            local_ids = blocks[first_block] if first_block == second_block else blocks[first_block] + blocks[second_block]
            local_triangles = [triangles[index] for index in local_ids]
            call: dict[str, Any] = {
                "blocks": [first_block, second_block],
                "triangle_count": len(local_triangles),
                "pair_policy_complete": False,
                "hit_pairs": [],
            }
            try:
                diagnostic = intersection_diagnostics(vertices, local_triangles)
                call["pair_count"] = diagnostic.get("pair_count")
                call["processed_pair_count"] = diagnostic.get("pair_policy_evidence", {}).get("processed_pair_count")
                call["pair_policy_complete"] = bool(diagnostic.get("pair_policy_complete"))
                call["candidate_pairs_truncated"] = bool(diagnostic.get("candidate_pairs_truncated"))
                call["hit_pairs_truncated"] = bool(diagnostic.get("hit_pairs_truncated"))
                expected_local_pairs = len(local_triangles) * (len(local_triangles) - 1) // 2
                call["expected_pair_count"] = expected_local_pairs
                call["processed_pair_count_matches"] = (
                    call["pair_count"] == expected_local_pairs
                    and call["processed_pair_count"] == expected_local_pairs
                )
                if first_block == second_block:
                    covered_pairs += len(blocks[first_block]) * (len(blocks[first_block]) - 1) // 2
                else:
                    covered_pairs += len(blocks[first_block]) * len(blocks[second_block])
                if not call["pair_policy_complete"] or not call["processed_pair_count_matches"]:
                    result["errors"].append({"code": "incomplete_pair_policy", "detail": "generic core did not process every local pair", "blocks": call["blocks"]})
                if call["hit_pairs_truncated"]:
                    result["errors"].append({"code": "truncated_collision_inventory", "detail": "generic core truncated intersection-hit evidence", "blocks": call["blocks"]})
                for local_first, local_second in diagnostic.get("hit_pairs", ()):
                    first = local_ids[int(local_first)]
                    second = local_ids[int(local_second)]
                    triangle_pair = tuple(sorted((first, second)))
                    if triangle_pair in seen_triangle_pairs:
                        continue
                    seen_triangle_pairs.add(triangle_pair)
                    face_pair = tuple(sorted((triangle_pair[0] // 2, triangle_pair[1] // 2)))
                    if face_pair[0] == face_pair[1]:
                        continue
                    if face_pair in seen_face_pairs:
                        continue
                    seen_face_pairs.add(face_pair)
                    row = {
                        "triangles": list(triangle_pair),
                        "faces": list(face_pair),
                        "owners": [owners[face_pair[0]], owners[face_pair[1]]],
                    }
                    call["hit_pairs"].append(list(triangle_pair))
                    result["hit_triangle_pairs"].append(list(triangle_pair))
                    result["hit_face_pairs"].append(row)
                    if face_pair[0] in lower_faces or face_pair[1] in lower_faces:
                        result["lower_hit_pairs"].append(row)
                    elif face_pair[0] in upper_faces and face_pair[1] in upper_faces:
                        result["upper_only_hit_pairs"].append(row)
            except Exception as exc:
                result["errors"].append({"code": "intersection_failure", "detail": str(exc), "blocks": call["blocks"]})
            result["calls"].append(call)

    result["expected_pair_count"] = expected_pairs
    result["covered_pair_count"] = covered_pairs
    result["coverage_complete"] = (covered_pairs == expected_pairs
                                    and all(call["pair_policy_complete"] for call in result["calls"])
                                    and all(call.get("processed_pair_count_matches") for call in result["calls"])
                                    and not any(call.get("hit_pairs_truncated") for call in result["calls"]))
    result["candidate_detail_truncated_calls"] = [
        call["blocks"] for call in result["calls"] if call.get("candidate_pairs_truncated")
    ]
    if result["candidate_detail_truncated_calls"]:
        result["limitations"] = [
            "Broad-phase candidate detail is bounded, but the frozen core reports complete pair-policy processing and complete intersection-hit evidence."
        ]
    result["available"] = result["coverage_complete"] and not result["errors"]
    result["hit_triangle_pairs"] = sorted(result["hit_triangle_pairs"])
    result["hit_face_pairs"] = sorted(result["hit_face_pairs"], key=lambda row: tuple(row["faces"]))
    result["lower_hit_pairs"] = sorted(result["lower_hit_pairs"], key=lambda row: tuple(row["faces"]))
    result["upper_only_hit_pairs"] = sorted(result["upper_only_hit_pairs"], key=lambda row: tuple(row["faces"]))
    result["global_face_pair_count"] = len(seen_face_pairs)
    result["pass"] = bool(result["available"] and not result["lower_hit_pairs"])
    return result


def _declared_loop_names(protocol: Mapping[str, Any]) -> set[str]:
    for source in (protocol, protocol.get("checks")):
        if isinstance(source, Mapping) and "boundary_loop_names" in source:
            return {str(item) for item in _sequence(source["boundary_loop_names"], "boundary_loop_names")}
    return {"neck", "arm.left", "arm.right", "ankle.left", "ankle.right"}


def _loop_role(name: str) -> str | None:
    normal = name.lower().replace("_", ".").replace("-", ".").replace("port", "")
    normal = ".".join(part for part in normal.split(".") if part)
    aliases = {
        "neck": "neck", "neck.upper": "neck", "upper.neck": "neck",
        "arm.left": "arm.left", "left.arm": "arm.left", "left.arm.upper": "arm.left",
        "arm.right": "arm.right", "right.arm": "arm.right", "right.arm.upper": "arm.right",
        "ankle.left": "ankle.left", "left.ankle": "ankle.left", "left.thigh": "ankle.left",
        "ankle.right": "ankle.right", "right.ankle": "ankle.right", "right.thigh": "ankle.right",
    }
    return aliases.get(normal)


def _arm_metadata_contract(mesh: Mapping[str, Any], vertex_count: int,
                           occupied: set[int] | None = None) -> dict[str, Any]:
    """Validate the explicit connected-arm L0 allocation and J/E/W sources."""
    metadata = _mapping(mesh.get("metadata"), "mesh.metadata")
    raw_arms = metadata.get("arms")
    if raw_arms is None:
        return {"present": False, "indices": {side: [] for side in _SIDES},
                "all_indices": set()}
    arms = _mapping(raw_arms, "mesh.metadata.arms")
    if set(arms) != set(_SIDES):
        raise ValueError("mesh.metadata.arms must contain exactly left and right")
    root = _mapping(metadata.get("root"), "mesh.metadata.root")
    root_count = root.get("vertex_count")
    if (isinstance(root_count, bool) or not isinstance(root_count, int)
            or root_count != _OLD_ROOT_VERTEX_COUNT):
        raise ValueError("mesh.metadata.root.vertex_count must preserve the original 152-vertex root")
    base_count = metadata.get("base_vertex_count", vertex_count)
    if (isinstance(base_count, bool) or not isinstance(base_count, int)
            or not root_count < base_count <= vertex_count):
        raise ValueError("mesh.metadata.base_vertex_count must lie inside the mesh vertex count")

    result: dict[str, Any] = {"present": True, "indices": {},
                              "source_points": {}, "base_count": base_count,
                              "root_count": root_count}
    all_indices: set[int] = set()
    for side in _SIDES:
        row = _mapping(arms[side], f"mesh.metadata.arms.{side}")
        if row.get("J_source") != f"shoulders.{side}.arm_origin":
            raise ValueError(f"mesh.metadata.arms.{side}.J_source must identify the calibrated arm_origin")
        source_port = _mapping(row.get("source_port"),
                               f"mesh.metadata.arms.{side}.source_port")
        if source_port.get("name") != f"port.{side}_arm":
            raise ValueError(f"mesh.metadata.arms.{side}.source_port.name must identify the named arm port")
        port = _sequence(source_port.get("indices"),
                         f"mesh.metadata.arms.{side}.source_port.indices")
        if len(port) != 8 or len(set(port)) != 8:
            raise ValueError(f"mesh.metadata.arms.{side}.source_port.indices must contain eight unique vertices")
        if any(isinstance(index, bool) or not isinstance(index, int)
               for index in port):
            raise ValueError(f"mesh.metadata.arms.{side}.source_port.indices must contain integer vertices")
        if any(index < 0 or index >= root_count for index in port):
            raise ValueError(f"mesh.metadata.arms.{side}.source_port.indices must reference root vertices")
        port = [int(index) for index in port]

        collar = _mapping(row.get("collar"), f"mesh.metadata.arms.{side}.collar")
        collar_values = _sequence(collar.get("indices"),
                                  f"mesh.metadata.arms.{side}.collar.indices")
        if len(collar_values) != 8 or len(set(collar_values)) != 8:
            raise ValueError(f"mesh.metadata.arms.{side}.collar.indices must contain eight unique vertices")
        if any(isinstance(index, bool) or not isinstance(index, int)
               for index in collar_values):
            raise ValueError(f"mesh.metadata.arms.{side}.collar.indices must contain integer vertices")
        collar_indices = [int(index) for index in collar_values]

        section_values = _sequence(row.get("sections"),
                                   f"mesh.metadata.arms.{side}.sections")
        if len(section_values) != len(_ARM_SECTION_NAMES):
            raise ValueError(f"mesh.metadata.arms.{side}.sections must contain the complete named arm sections")
        sections: dict[str, list[int]] = {}
        for name, raw_section in zip(_ARM_SECTION_NAMES, section_values):
            section = _mapping(raw_section,
                               f"mesh.metadata.arms.{side}.sections.{name}")
            if section.get("name") != name:
                raise ValueError(f"mesh.metadata.arms.{side}.sections order/name mismatch")
            values = _sequence(section.get("indices"),
                               f"mesh.metadata.arms.{side}.sections.{name}.indices")
            if len(values) != 8 or len(set(values)) != 8:
                raise ValueError(f"mesh.metadata.arms.{side}.sections.{name}.indices must contain eight unique vertices")
            if any(isinstance(index, bool) or not isinstance(index, int)
                   for index in values):
                raise ValueError(f"mesh.metadata.arms.{side}.sections.{name}.indices must contain integer vertices")
            sections[name] = [int(index) for index in values]
        cap = _mapping(row.get("cap"), f"mesh.metadata.arms.{side}.cap")
        cap_value = cap.get("vertex")
        if isinstance(cap_value, bool) or not isinstance(cap_value, int):
            raise ValueError(f"mesh.metadata.arms.{side}.cap.vertex must be an integer vertex")
        cap_index = int(cap_value)
        new_indices = _sequence(row.get("new_vertex_indices"),
                                f"mesh.metadata.arms.{side}.new_vertex_indices")
        expected = collar_indices + [index for name in _ARM_SECTION_NAMES
                                     for index in sections[name]] + [cap_index]
        if any(isinstance(index, bool) or not isinstance(index, int)
               for index in new_indices):
            raise ValueError(f"mesh.metadata.arms.{side}.new_vertex_indices must contain integer vertices")
        checked_new = [int(index) for index in new_indices]
        if checked_new != expected:
            raise ValueError(f"mesh.metadata.arms.{side}.new_vertex_indices disagrees with semantic sections")
        if len(set(checked_new)) != len(checked_new):
            raise ValueError(f"mesh.metadata.arms.{side} contains overlapping vertex allocations")
        if any(index < root_count or index >= base_count for index in checked_new):
            raise ValueError(f"mesh.metadata.arms.{side} contains an invalid appended vertex")
        if all_indices.intersection(checked_new) or (occupied and occupied.intersection(checked_new)):
            raise ValueError(f"mesh.metadata.arms.{side} overwrites another L0 allocation")

        source_points = {
            name: _vector(row.get(name), f"mesh.metadata.arms.{side}.{name}")
            for name in ("J", "E", "W")
        }
        if (source_points["J"] == source_points["E"]
                or source_points["E"] == source_points["W"]):
            raise ValueError(f"mesh.metadata.arms.{side} J/E/W bones must be non-degenerate")
        result["indices"][side] = checked_new
        result["source_points"][side] = source_points
        all_indices.update(checked_new)
    result["all_indices"] = all_indices
    return result


def _head_metadata_contract(mesh: Mapping[str, Any], vertex_count: int,
                            occupied: set[int] | None = None) -> dict[str, Any]:
    """Validate the one-joint neck/head handoff without treating the upper port as pivot."""
    metadata = _mapping(mesh.get("metadata"), "mesh.metadata")
    raw_head = metadata.get("head")
    if raw_head is None:
        return {"present": False, "source_port": [], "support": [],
                "new_vertex_indices": [], "all_indices": set()}
    head = _mapping(raw_head, "mesh.metadata.head")
    handoff = _mapping(head.get("binding_handoff"), "mesh.metadata.head.binding_handoff")
    if handoff.get("joint") != "neck_head":
        raise ValueError("head.binding_handoff.joint must be neck_head")
    if handoff.get("pivot_source") != "stations.neck_collar.C":
        raise ValueError("head binding pivot must be stations.neck_collar.C")
    pivot = _vector(handoff.get("pivot"), "head.binding_handoff.pivot")
    if head.get("neck_source") != "stations.neck_upper":
        raise ValueError("head.neck_source must identify the upper port, not the pivot")
    port = [int(index) for index in _sequence(head.get("neck_port_indices"),
                                               "head.neck_port_indices")]
    consumed = [int(index) for index in _sequence(
        handoff.get("consumed_neck_port_indices"),
        "head.binding_handoff.consumed_neck_port_indices")]
    if len(port) != 6 or len(set(port)) != 6:
        raise ValueError("head.neck_port_indices must contain six unique vertices")
    if len(consumed) != 6 or len(set(consumed)) != 6 or consumed != port:
        raise ValueError("head consumed neck boundary must exactly equal the six-point upper port")
    if any(index < 0 or index >= _OLD_ROOT_VERTEX_COUNT for index in port):
        raise ValueError("head.neck_port_indices must reference the original root")

    stations = _sequence(head.get("stations"), "head.stations")
    support_rows = [
        _mapping(row, "head station") for row in stations
        if isinstance(row, Mapping) and row.get("name") == "neck_support"
    ]
    if len(support_rows) != 1:
        raise ValueError("head.stations must contain exactly one neck_support station")
    support = [int(index) for index in _sequence(
        support_rows[0].get("indices"), "head.stations.neck_support.indices")]
    handoff_support = [int(index) for index in _sequence(
        handoff.get("neck_support_ring_indices"),
        "head.binding_handoff.neck_support_ring_indices")]
    if len(support) != 6 or len(set(support)) != 6 or support != handoff_support:
        raise ValueError("head neck_support ring and binding handoff must contain the same six vertices")

    new_indices = [int(index) for index in _sequence(
        head.get("new_vertex_indices"), "head.new_vertex_indices")]
    handoff_new = [int(index) for index in _sequence(
        handoff.get("head_new_vertex_indices"),
        "head.binding_handoff.head_new_vertex_indices")]
    if new_indices != handoff_new or len(set(new_indices)) != len(new_indices):
        raise ValueError("head vertex allocation and binding handoff must agree exactly")
    if not new_indices or any(index < _OLD_ROOT_VERTEX_COUNT or index >= vertex_count
                              for index in new_indices):
        raise ValueError("head.new_vertex_indices must be unique appended L0 vertices")
    if any(index not in set(new_indices) for index in support):
        raise ValueError("head neck_support vertices must be part of the head allocation")
    feature = head.get("feature_new_vertex_indices", ())
    if feature is not None:
        feature_indices = [int(index) for index in _sequence(feature, "head.feature_new_vertex_indices")]
        if any(index not in set(new_indices) for index in feature_indices):
            raise ValueError("head feature allocation must be contained in head.new_vertex_indices")
    all_indices = set(new_indices)
    if occupied and all_indices.intersection(occupied):
        raise ValueError("head allocation overwrites another connected allocation")
    return {"present": True, "J": pivot, "pivot_source": handoff["pivot_source"],
            "source_port": port, "consumed_neck_port_indices": consumed,
            "support": support, "new_vertex_indices": new_indices,
            "all_indices": all_indices, "root_count": _OLD_ROOT_VERTEX_COUNT,
            "base_count": metadata.get("base_vertex_count", vertex_count)}


def _tail_metadata_contract(mesh: Mapping[str, Any], vertex_count: int) -> dict[str, Any]:
    """Validate the explicit pinned host-58 tail handoff without inferring anatomy."""
    raw_metadata = mesh.get("metadata", {})
    if raw_metadata is None:
        raw_metadata = {}
    if not isinstance(raw_metadata, Mapping):
        raise ValueError("mesh.metadata must be a mapping")
    metadata = raw_metadata
    raw_tail = metadata.get("tail")
    if raw_tail is None:
        return {"present": False, "new_vertex_indices": [], "all_indices": set()}
    tail = _mapping(raw_tail, "mesh.metadata.tail")
    if tail.get("enabled") is not True or tail.get("owner") != "domain.tail":
        raise ValueError("mesh.metadata.tail must be an enabled domain.tail allocation")
    root = _mapping(metadata.get("root"), "mesh.metadata.root")
    root_count = root.get("vertex_count")
    root_face_count = root.get("face_count")
    if root_count != _OLD_ROOT_VERTEX_COUNT or not isinstance(root_face_count, int) or root_face_count <= 0:
        raise ValueError("tail metadata must preserve the 152-vertex source root and a positive face count")
    base_count = metadata.get("base_vertex_count")
    if isinstance(base_count, bool) or not isinstance(base_count, int) or base_count > vertex_count:
        raise ValueError("tail metadata base_vertex_count must cover the declared L0")
    identity = _mapping(tail.get("source_host_identity"),
                        "mesh.metadata.tail.source_host_identity")
    host_face = identity.get("face_index")
    host_vertices = _sequence(identity.get("vertex_indices"),
                               "mesh.metadata.tail.source_host_identity.vertex_indices")
    if (identity.get("owner") != "domain.pelvis" or
            isinstance(host_face, bool) or not isinstance(host_face, int) or
            host_face < 0 or host_face >= root_face_count or len(host_vertices) != 4):
        raise ValueError("tail source host identity must pin one pelvis quadrilateral")
    host_vertices = [int(index) for index in host_vertices]
    if len(set(host_vertices)) != 4 or any(index < 0 or index >= root_count for index in host_vertices):
        raise ValueError("tail source host identity vertices must be four unique root vertices")

    replacement = _mapping(tail.get("face_replacement"),
                           "mesh.metadata.tail.face_replacement")
    if (replacement.get("original_face_index") != host_face or
            list(replacement.get("original_quad", ())) != host_vertices or
            replacement.get("original_host_retained") is not False):
        raise ValueError("tail face replacement must explicitly replace the pinned host face")
    replacement_faces = _sequence(replacement.get("replacement_face_indices"),
                                  "tail.face_replacement.replacement_face_indices")
    replacement_faces = [int(index) for index in replacement_faces]
    if (not replacement_faces or len(set(replacement_faces)) != len(replacement_faces) or
            host_face not in replacement_faces or
            replacement.get("one_to_many") != [[host_face, *replacement_faces]]):
        raise ValueError("tail face replacement one-to-many mapping is incomplete")
    quads = _sequence(mesh.get("quads"), "mesh.quads")
    if any(index < 0 or index >= len(quads) for index in replacement_faces):
        raise ValueError("tail replacement face index is outside mesh.quads")
    index_mapping = _mapping(metadata.get("index_mapping"), "mesh.metadata.index_mapping")
    kept = index_mapping.get("root_face_mappings_excluding_tail_host")
    expected_kept = [[index, index] for index in range(root_face_count) if index != host_face]
    if kept != expected_kept:
        raise ValueError("tail kept-face correspondence must exclude only the pinned host face")

    new_indices = _sequence(tail.get("new_vertex_indices"),
                            "mesh.metadata.tail.new_vertex_indices")
    if (not new_indices or any(isinstance(index, bool) or not isinstance(index, int)
                               for index in new_indices)):
        raise ValueError("tail.new_vertex_indices must be non-empty integer IDs")
    new_indices = [int(index) for index in new_indices]
    if (len(set(new_indices)) != len(new_indices) or
            any(index < root_count or index >= base_count for index in new_indices)):
        raise ValueError("tail.new_vertex_indices must be a unique appended L0 allocation")
    rings_raw = _sequence(tail.get("ring_indices"), "mesh.metadata.tail.ring_indices")
    rings: list[list[int]] = []
    for ring_index, raw_ring in enumerate(rings_raw):
        ring = _sequence(raw_ring, f"tail.ring_indices[{ring_index}]")
        if len(ring) != 4 or any(index not in new_indices for index in ring):
            raise ValueError("tail rings must preserve four-corner source phase order")
        rings.append([int(index) for index in ring])
    if [index for ring in rings for index in ring] != new_indices:
        raise ValueError("tail ring allocations must cover new_vertex_indices exactly once")
    corner_by_vertex = {
        vertex_index: corner
        for ring in rings
        for corner, vertex_index in enumerate(ring)
    }
    source_phase = _sequence(tail.get("source_phase"), "mesh.metadata.tail.source_phase")
    if len(source_phase) != 4 or len({tuple(phase) for phase in source_phase}) != 4:
        raise ValueError("tail source_phase must contain four distinct corners")
    if any(len(phase) != 2 or any(type(value) is not int or value not in (-1, 1)
                                   for value in phase) for phase in source_phase):
        raise ValueError("tail source_phase entries must be signed pairs")
    source_phase = [list(phase) for phase in source_phase]
    host_record = _mapping(tail.get("host"), "mesh.metadata.tail.host")
    if host_record.get("source_phase") != source_phase:
        raise ValueError("tail host/source phase declarations must agree")
    fractions = _sequence(tail.get("station_fractions"),
                          "mesh.metadata.tail.station_fractions")
    fractions = [_number(value, f"tail.station_fractions[{index}]")
                 for index, value in enumerate(fractions)]
    if (len(fractions) != len(rings) or not fractions or fractions != sorted(fractions) or
            fractions[0] != 0.0 or fractions[-1] != 1.0 or
            any(value < 0.0 or value > 1.0 for value in fractions)):
        raise ValueError("tail station fractions must be ordered from collar 0 to tip 1")

    transition = _mapping(tail.get("transition_weights"),
                          "mesh.metadata.tail.transition_weights")
    collar_blend = _number(transition.get("collar_blend_strength"),
                           "tail.transition_weights.collar_blend_strength")
    if not 0.0 <= collar_blend <= 1.0:
        raise ValueError("tail collar_blend_strength must lie in [0, 1]")
    supports = _mapping(transition.get("supports"),
                        "tail.transition_weights.supports")
    if set(supports) != {str(index) for index in new_indices}:
        raise ValueError("tail supports must cover every new vertex exactly once")
    checked_supports: dict[int, dict[str, Any]] = {}
    for index in new_indices:
        row = _mapping(supports[str(index)], f"tail.transition_weights.supports.{index}")
        corner = corner_by_vertex[index]
        if (row.get("target_joint") != "pelvis" or
                list(row.get("host_vertex_indices", ())) != host_vertices or
                row.get("host_corner") != corner or
                row.get("source_phase") != source_phase[corner]):
            raise ValueError(f"tail support {index} has an invalid host corner/phase contract")
        weights = [_number(value, f"tail support {index}.convex_weights[{slot}]")
                   for slot, value in enumerate(_sequence(row.get("convex_weights"),
                                                          f"tail support {index}.convex_weights"))]
        expected = [_TAIL_SUPPORT_OWN if slot == corner else _TAIL_SUPPORT_OTHER
                    for slot in range(4)]
        if len(weights) != 4 or any(abs(actual - wanted) > 1e-12
                                    for actual, wanted in zip(weights, expected)):
            raise ValueError(f"tail support {index} must match the declared .55/.15 corner rule")
        checked_supports[index] = {"host_vertex_indices": host_vertices[:],
                                   "host_corner": corner,
                                   "source_phase": source_phase[corner],
                                   "convex_weights": weights}
    return {
        "present": True, "owner": tail["owner"], "host_face": int(host_face),
        "host_vertices": host_vertices, "replacement_faces": replacement_faces,
        "kept_faces": expected_kept, "new_vertex_indices": new_indices,
        "rings": rings, "station_fractions": fractions,
        "source_phase": source_phase, "collar_blend_strength": collar_blend,
        "supports": checked_supports, "root_count": root_count,
        "root_face_count": root_face_count, "base_count": base_count,
        "all_indices": set(new_indices),
    }


def _foot_metadata_contract(mesh: Mapping[str, Any], vertex_count: int,
                            excluded_indices: set[int] | None = None) -> dict[str, Any]:
    """Validate the explicit L0 allocation used by a closed terminal foot.

    The indices are source metadata, not a mesh-size convention.  A returned
    allocation is subsequently used by the binding check to verify the
    shank-only five-column weights and their complete L2 transfer.
    """
    metadata = _mapping(mesh.get("metadata"), "mesh.metadata")
    tail_contract = _tail_metadata_contract(mesh, vertex_count)
    tail_indices = set(tail_contract.get("all_indices", ()))
    if "feet" not in metadata:
        if not tail_contract["present"]:
            # Preserve the historical no-feet path: the leg constructor owns
            # its station allocation contract in _constructor_station_rings.
            return {"present": False, "indices": {side: [] for side in _SIDES},
                    "excluded_indices": set(excluded_indices or ())}
        chains = _mapping(metadata.get("chains"), "mesh.metadata.chains")
        leg_indices: set[int] = set()
        for side in _SIDES:
            chain = _mapping(chains.get(side), f"mesh.metadata.chains.{side}")
            raw_chain = chain.get("new_vertex_indices", ())
            leg_indices.update(int(index) for index in _sequence(raw_chain, f"chains.{side}.new_vertex_indices"))
            for raw_section in _sequence(chain.get("sections", ()), f"chains.{side}.sections"):
                leg_indices.update(int(index) for index in _sequence(
                    _mapping(raw_section, "chain section").get("indices"), "chain section.indices"))
        root_count = int(_mapping(metadata.get("root"), "mesh.metadata.root")["vertex_count"])
        base_count = int(metadata.get("base_vertex_count", vertex_count))
        appended = set(range(root_count, base_count))
        excluded = set(excluded_indices or ()) | tail_indices
        if leg_indices | excluded != appended or leg_indices & excluded:
            raise ValueError("mesh leg and tail metadata must cover every appended L0 vertex exactly once")
        return {"present": False, "indices": {side: [] for side in _SIDES},
                "excluded_indices": excluded, "tail": tail_contract,
                "base_count": base_count, "root_count": root_count}

    owner_count = metadata.get("base_vertex_count")
    if isinstance(owner_count, bool) or not isinstance(owner_count, int) or owner_count <= 0:
        raise ValueError("mesh.metadata.base_vertex_count must be a positive integer")
    owners = metadata.get("base_control_owners")
    if not isinstance(owners, (list, tuple)) or len(owners) != owner_count:
        raise ValueError("mesh.metadata.base_control_owners must cover the declared L0")
    level = mesh.get("level", metadata.get("level", 0))
    if level == 0:
        l0_count = vertex_count
    else:
        l0_count = owner_count
        raw_stencils = mesh.get("base_stencils")
        if isinstance(raw_stencils, (list, tuple)):
            for raw_row in raw_stencils:
                if not isinstance(raw_row, (list, tuple)):
                    continue
                for raw_term in raw_row:
                    if (isinstance(raw_term, (list, tuple)) and len(raw_term) == 2
                            and isinstance(raw_term[0], int) and not isinstance(raw_term[0], bool)):
                        l0_count = max(l0_count, int(raw_term[0]) + 1)
    if l0_count > vertex_count:
        raise ValueError("declared L0 exceeds the mesh vertex count")
    root = _mapping(metadata.get("root"), "mesh.metadata.root")
    root_count = root.get("vertex_count")
    if isinstance(root_count, bool) or not isinstance(root_count, int) or not 0 < root_count < l0_count:
        raise ValueError("mesh.metadata.root.vertex_count must lie inside the declared L0")

    chains = _mapping(metadata.get("chains"), "mesh.metadata.chains")
    if set(chains) != set(_SIDES):
        raise ValueError("mesh.metadata.chains must contain exactly left and right")
    leg_indices: set[int] = set()
    for side in _SIDES:
        chain = _mapping(chains[side], f"mesh.metadata.chains.{side}")
        raw = chain.get("new_vertex_indices")
        values = _sequence(raw, f"mesh.metadata.chains.{side}.new_vertex_indices")
        if not values or any(isinstance(index, bool) or not isinstance(index, int) for index in values):
            raise ValueError(f"mesh.metadata.chains.{side}.new_vertex_indices must contain integers")
        checked = {int(index) for index in values}
        if len(checked) != len(values) or any(index < root_count or index >= l0_count for index in checked):
            raise ValueError(f"mesh.metadata.chains.{side}.new_vertex_indices is not a unique appended allocation")
        if leg_indices & checked:
            raise ValueError("mesh.metadata.chains allocations overlap")
        leg_indices.update(checked)

    feet = _mapping(metadata.get("feet"), "mesh.metadata.feet")
    if set(feet) != set(_SIDES):
        raise ValueError("mesh.metadata.feet must contain exactly left and right")
    foot_indices: dict[str, list[int]] = {}
    assigned: set[int] = set()
    for side in _SIDES:
        row = _mapping(feet[side], f"mesh.metadata.feet.{side}")
        values = _sequence(row.get("new_vertex_indices"),
                           f"mesh.metadata.feet.{side}.new_vertex_indices")
        if not values or any(isinstance(index, bool) or not isinstance(index, int) for index in values):
            raise ValueError(f"mesh.metadata.feet.{side}.new_vertex_indices must contain integers")
        checked = [int(index) for index in values]
        checked_set = set(checked)
        if len(checked_set) != len(checked):
            raise ValueError(f"mesh.metadata.feet.{side}.new_vertex_indices must be unique")
        if any(index < root_count or index >= l0_count for index in checked_set):
            raise ValueError(f"mesh.metadata.feet.{side}.new_vertex_indices is outside the declared L0")
        if checked_set & leg_indices:
            raise ValueError(f"mesh.metadata.feet.{side}.new_vertex_indices overlaps a leg allocation")
        if checked_set & assigned:
            raise ValueError("mesh.metadata.feet left and right allocations overlap")
        foot_indices[side] = checked
        assigned.update(checked_set)

    appended = set(range(root_count, l0_count))
    excluded = set(excluded_indices or ()) | tail_indices
    if leg_indices | assigned | excluded != appended:
        raise ValueError("mesh leg and foot metadata must cover every appended L0 vertex exactly once")
    if ((leg_indices & excluded) or (assigned & excluded) or
            (tail_indices & leg_indices) or (tail_indices & assigned)):
        raise ValueError("mesh leg, foot, arm, and tail allocations must be disjoint")
    return {"present": True, "indices": foot_indices,
            "base_count": l0_count, "root_count": root_count,
            "excluded_indices": excluded | assigned, "tail": tail_contract}


def _arm_graph_fields(base_mesh: Mapping[str, Any],
                      base_quads: Sequence[Sequence[int]],
                      arms: Mapping[str, Any], *,
                      root_quads: Sequence[Sequence[int]] | None = None) -> tuple[dict[str, dict[int, float]],
                                                                                 dict[str, dict[int, float]],
                                                                                 dict[str, Any]]:
    """Independently solve the declared D0/D1-to-collar arm field and elbow blend."""
    metadata = _mapping(base_mesh.get("metadata"), "base.metadata")
    root = _mapping(metadata.get("root"), "base.metadata.root")
    root_count = root.get("vertex_count")
    root_face_count = root.get("face_count")
    if (isinstance(root_count, bool) or not isinstance(root_count, int)
            or isinstance(root_face_count, bool) or not isinstance(root_face_count, int)):
        raise ValueError("arm harmonic field requires integer root vertex/face counts")
    if root_count != _OLD_ROOT_VERTEX_COUNT:
        raise ValueError("arm harmonic field must preserve the original 152-vertex root")
    root_quads = base_quads if root_quads is None else root_quads
    if root_face_count <= 0 or root_face_count > len(root_quads):
        raise ValueError("arm harmonic field root range is invalid")
    root_graph = [set() for _ in range(root_count)]
    graph = [set() for _ in range(max(root_count, 1 + max(max(face) for face in base_quads)))]
    for face_index, face in enumerate(base_quads):
        for slot, left in enumerate(face):
            right = face[(slot + 1) % 4]
            graph[left].add(right)
            graph[right].add(left)
    for face in root_quads[:root_face_count]:
        for slot, left in enumerate(face):
            right = face[(slot + 1) % 4]
            if left >= root_count or right >= root_count:
                raise ValueError("root face references a non-root vertex")
            root_graph[left].add(right)
            root_graph[right].add(left)

    def solve(matrix: list[list[float]], rhs: list[float], label: str) -> list[float]:
        size = len(rhs)
        augmented = [row[:] + [rhs[index]] for index, row in enumerate(matrix)]
        for column in range(size):
            pivot = max(range(column, size), key=lambda row: abs(augmented[row][column]))
            if abs(augmented[pivot][column]) <= 1.0e-14:
                raise ValueError(f"{label} harmonic system is singular")
            augmented[column], augmented[pivot] = augmented[pivot], augmented[column]
            divisor = augmented[column][column]
            augmented[column] = [value / divisor for value in augmented[column]]
            for row in range(size):
                if row == column:
                    continue
                factor = augmented[row][column]
                if factor:
                    augmented[row] = [left - factor * right
                                      for left, right in zip(augmented[row], augmented[column])]
        values = [augmented[index][-1] for index in range(size)]
        if any(not math.isfinite(value) for value in values):
            raise ValueError(f"{label} harmonic system produced non-finite values")
        return values

    fields: dict[str, dict[int, float]] = {}
    blends: dict[str, dict[int, float]] = {}
    regions: dict[str, tuple[set[int], set[int], set[int]]] = {}
    diagnostics: dict[str, Any] = {"per_side": {}}
    for side in _SIDES:
        row = _mapping(arms[side], f"base.metadata.arms.{side}")
        source = _mapping(row.get("source_port"), f"base.metadata.arms.{side}.source_port")
        d0 = set(_sequence(source.get("indices"),
                           f"base.metadata.arms.{side}.source_port.indices"))
        collar = set(_sequence(_mapping(row.get("collar"),
                                        f"base.metadata.arms.{side}.collar").get("indices"),
                               f"base.metadata.arms.{side}.collar.indices"))
        d1 = {neighbour for index in d0 for neighbour in root_graph[index]} - d0
        d2 = {neighbour for index in d1 for neighbour in root_graph[index]} - d0 - d1
        if not d0 or not d1 or not d2 or not collar:
            raise ValueError(f"base.metadata.arms.{side} requires non-empty D0, D1, D2, and collar")
        if (len(d0), len(d1), len(d2)) != (8, 8, 10):
            raise ValueError(
                f"base.metadata.arms.{side} requires D0/D1/D2 counts 8/8/10, "
                f"got {len(d0)}/{len(d1)}/{len(d2)}"
            )
        if set.intersection(*(set(values) for values in (d0, d1, d2))):
            raise ValueError(f"base.metadata.arms.{side} D0/D1/D2 regions overlap")
        regions[side] = (d0, d1, d2)
        free = sorted(d0 | d1)
        positions = {index: position for position, index in enumerate(free)}
        matrix = [[1.0 if row_index == column_index else 0.0
                   for column_index, _column in enumerate(free)]
                  for row_index in range(len(free))]
        rhs = [0.0 for _ in free]
        for index in free:
            neighbours = graph[index]
            if not neighbours:
                raise ValueError(f"base.metadata.arms.{side} has an isolated D0/D1 vertex")
            row_index = positions[index]
            for neighbour in neighbours:
                if neighbour in positions:
                    matrix[row_index][positions[neighbour]] -= 1.0 / len(neighbours)
                elif neighbour in collar:
                    rhs[row_index] += 1.0 / len(neighbours)
                elif neighbour in d2:
                    pass
                else:
                    raise ValueError(f"base.metadata.arms.{side} D0/D1 has an undeclared neighbour")
        values = solve(matrix, rhs, f"{side} shoulder")
        fields[side] = {index: value for index, value in zip(free, values)}

        sections = _mapping(row, f"base.metadata.arms.{side}").get("sections")
        section_rows = {str(_mapping(item, "arm section").get("name")): _mapping(item, "arm section")
                        for item in _sequence(sections, f"base.metadata.arms.{side}.sections")}
        zero = set(collar) | set(_sequence(section_rows["upper_belly"].get("indices"), "arm upper_belly")) | set(_sequence(section_rows["pre_elbow"].get("indices"), "arm pre_elbow"))
        free_elbow = set(_sequence(section_rows["elbow"].get("indices"), "arm elbow"))
        one = set()
        for name in ("post_elbow", "forearm_belly", "pre_wrist", "wrist", "palm", "knuckle", "terminal"):
            one.update(_sequence(section_rows[name].get("indices"), f"arm {name}"))
        one.add(int(_mapping(row.get("cap"), f"base.metadata.arms.{side}.cap").get("vertex")))
        if not zero or not free_elbow or not one or zero & free_elbow or zero & one or free_elbow & one:
            raise ValueError(f"base.metadata.arms.{side} elbow blend regions overlap or are empty")
        elbow_nodes = sorted(free_elbow)
        elbow_positions = {index: position for position, index in enumerate(elbow_nodes)}
        elbow_matrix = [[1.0 if row_index == column_index else 0.0
                         for column_index, _column in enumerate(elbow_nodes)]
                        for row_index in range(len(elbow_nodes))]
        elbow_rhs = [0.0 for _ in elbow_nodes]
        for index in elbow_nodes:
            neighbours = graph[index]
            if not neighbours or not (neighbours & (zero | one)):
                raise ValueError(f"base.metadata.arms.{side} elbow blend is not anchored")
            row_index = elbow_positions[index]
            for neighbour in neighbours:
                if neighbour in elbow_positions:
                    elbow_matrix[row_index][elbow_positions[neighbour]] -= 1.0 / len(neighbours)
                elif neighbour in one:
                    elbow_rhs[row_index] += 1.0 / len(neighbours)
                elif neighbour not in zero:
                    raise ValueError(f"base.metadata.arms.{side} elbow has an undeclared neighbour")
        elbow_values = solve(elbow_matrix, elbow_rhs, f"{side} elbow")
        blends[side] = {index: 0.0 for index in zero}
        blends[side].update({index: value for index, value in zip(elbow_nodes, elbow_values)})
        blends[side].update({index: 1.0 for index in one})
        diagnostics["per_side"][side] = {
            "D0": sorted(d0), "D1": sorted(d1), "D2": sorted(d2),
            "collar": sorted(collar), "elbow": sorted(free_elbow),
            "shoulder_values": {str(index): fields[side][index] for index in free},
        }
    if set(fields["left"]) & set(fields["right"]):
        raise ValueError("bilateral arm D0/D1 regions overlap")
    left_free = set(fields["left"])
    right_free = set(fields["right"])
    if (left_free & regions["right"][2]) or (right_free & regions["left"][2]):
        raise ValueError("arm free region overlaps the opposite arm D2 boundary")
    return fields, blends, diagnostics


def _head_graph_field(base_mesh: Mapping[str, Any],
                      base_quads: Sequence[Sequence[int]],
                      head: Mapping[str, Any], *,
                      root_quads: Sequence[Sequence[int]] | None = None) -> tuple[dict[int, float], dict[str, Any]]:
    """Solve the declared neck D0/D1 field with support=1 and D2=0."""
    metadata = _mapping(base_mesh.get("metadata"), "base.metadata")
    root = _mapping(metadata.get("root"), "base.metadata.root")
    root_count, root_faces = root.get("vertex_count"), root.get("face_count")
    if root_count != _OLD_ROOT_VERTEX_COUNT or not isinstance(root_faces, int):
        raise ValueError("head harmonic field requires the original root face/vertex declaration")
    root_quads = base_quads if root_quads is None else root_quads
    if root_faces <= 0 or root_faces > len(root_quads):
        raise ValueError("head harmonic field root range is invalid")
    graph = [set() for _ in range(root_count)]
    for face in root_quads[:root_faces]:
        if any(index >= root_count for index in face):
            raise ValueError("head harmonic field root faces must reference only root vertices")
        for left, right in zip(face, face[1:] + face[:1]):
            graph[left].add(right)
            graph[right].add(left)
    d0 = set(head["source_port"])
    support = set(head["support"])
    connections = []
    all_edges = {
        tuple(sorted((left, right)))
        for face in base_quads
        for left, right in zip(face, face[1:] + face[:1])
    }
    for port_index, support_index in zip(head["source_port"], head["support"]):
        edge = tuple(sorted((port_index, support_index)))
        if edge not in all_edges:
            raise ValueError("head port-to-support weld is missing from the base mesh")
        connections.append((port_index, support_index))
    d1 = {neighbour for index in d0 for neighbour in graph[index]} - d0
    d2 = {neighbour for index in d1 for neighbour in graph[index]} - d0 - d1
    if not d0 or not d1 or not d2 or not support:
        raise ValueError("head harmonic field requires non-empty D0, D1, D2, and support")
    free = sorted(d0 | d1)
    positions = {index: position for position, index in enumerate(free)}
    matrix = [[1.0 if row_index == column_index else 0.0
               for column_index, _column in enumerate(free)]
              for row_index in range(len(free))]
    rhs = [0.0 for _ in free]
    for index in free:
        neighbours = set(graph[index])
        for port_index, support_index in connections:
            if index == port_index:
                neighbours.add(support_index)
        if not neighbours:
            raise ValueError("head harmonic field has an isolated boundary vertex")
        row = positions[index]
        for neighbour in neighbours:
            if neighbour in positions:
                matrix[row][positions[neighbour]] -= 1.0 / len(neighbours)
            elif neighbour in support:
                rhs[row] += 1.0 / len(neighbours)
            elif neighbour in d2:
                pass
            else:
                raise ValueError("head D0/D1 has an undeclared root neighbour")
    augmented = [row[:] + [rhs[index]] for index, row in enumerate(matrix)]
    size = len(free)
    for column in range(size):
        pivot = max(range(column, size), key=lambda row: abs(augmented[row][column]))
        if abs(augmented[pivot][column]) <= 1.0e-14:
            raise ValueError("head harmonic system is singular")
        augmented[column], augmented[pivot] = augmented[pivot], augmented[column]
        divisor = augmented[column][column]
        augmented[column] = [value / divisor for value in augmented[column]]
        for row in range(size):
            if row != column:
                factor = augmented[row][column]
                if factor:
                    augmented[row] = [left - factor * right
                                      for left, right in zip(augmented[row], augmented[column])]
    values = {index: augmented[position][-1] for position, index in enumerate(free)}
    return values, {"D0": sorted(d0), "D1": sorted(d1), "D2": sorted(d2),
                    "support": sorted(support), "values": values}


def _tail_expected_base_rows(base_weights: Sequence[Sequence[float]],
                             tail_contract: Mapping[str, Any],
                             columns: Sequence[str]) -> dict[int, list[float]]:
    """Derive tail L0 rows while retaining non-tail host rows for L2 transfer."""
    pelvis_column = list(columns).index("pelvis") if "pelvis" in columns else -1
    expected_rows: dict[int, list[float]] = {}
    for ring, fraction in zip(tail_contract["rings"], tail_contract["station_fractions"]):
        pelvis_fraction = (float(tail_contract["collar_blend_strength"])
                           + (1.0 - float(tail_contract["collar_blend_strength"]))
                           * float(fraction))
        for vertex_index in ring:
            support = tail_contract["supports"][vertex_index]
            host_support = [0.0] * len(columns)
            for host_index, coefficient in zip(support["host_vertex_indices"],
                                               support["convex_weights"]):
                for column in range(len(columns)):
                    host_support[column] += float(coefficient) * base_weights[host_index][column]
            expected = [(1.0 - pelvis_fraction) * value for value in host_support]
            if pelvis_column >= 0:
                expected[pelvis_column] += pelvis_fraction
            expected_rows[int(vertex_index)] = expected
    return expected_rows


def _matrix_error(actual: Sequence[Sequence[float]], expected: Sequence[Sequence[float]]) -> float:
    return max((abs(float(actual[row][column]) - float(expected[row][column]))
                for row in range(4) for column in range(4)), default=math.inf)


def _stencil_rows(value: Any, vertex_count: int, base_count: int | None, label: str,
                  tolerance: float) -> list[list[tuple[int, float]]]:
    rows = _sequence(value, label)
    if len(rows) != vertex_count:
        raise ValueError(f"{label} must cover every evaluated vertex")
    result: list[list[tuple[int, float]]] = []
    for row_index, raw_row in enumerate(rows):
        terms = _sequence(raw_row, f"{label}[{row_index}]")
        if not terms:
            raise ValueError(f"{label}[{row_index}] must not be empty")
        checked: list[tuple[int, float]] = []
        previous = -1
        for term in terms:
            pair = _sequence(term, f"{label}[{row_index}] term")
            if len(pair) != 2 or isinstance(pair[0], bool) or not isinstance(pair[0], int):
                raise ValueError(f"{label}[{row_index}] has an invalid index/coefficient pair")
            index = int(pair[0])
            if index <= previous or index < 0 or (base_count is not None and index >= base_count):
                raise ValueError(f"{label}[{row_index}] indices must be sorted and in range")
            coefficient = _number(pair[1], f"{label}[{row_index}] coefficient")
            if coefficient <= 0.0:
                raise ValueError(f"{label}[{row_index}] coefficients must be positive")
            checked.append((index, coefficient))
            previous = index
        if abs(sum(coefficient for _, coefficient in checked) - 1.0) > tolerance:
            raise ValueError(f"{label}[{row_index}] must partition unity within {tolerance}")
        result.append(checked)
    return result


def check_mesh(mesh: Mapping[str, Any], protocol: Mapping[str, Any]) -> dict[str, Any]:
    """Check one staged mesh without imposing historical exact vertex counts."""
    report = _report("creature-kernel.connected-leg-assembly-mesh-checks.v1")
    try:
        parsed = _mesh(mesh, "mesh")
        vertices, quads = parsed["vertices"], parsed["quads"]
        incidence = _edge_incidence(quads)
        edge_use = all(len(uses) in (1, 2) for uses in incidence.values())
        orientation = all(len(uses) != 2 or (uses[0][1], uses[0][2]) == (uses[1][2], uses[1][1])
                          for uses in incidence.values())
        cycles: list[list[int]] = []
        boundary_valid = True
        try:
            cycles = _boundary_cycles(incidence)
        except Exception as exc:
            boundary_valid = False
            _error(report, "boundary_cycle", str(exc))

        loops = parsed["loops"]
        declared_match = False
        declared_roles: set[str | None] = set()
        declared: dict[str, list[Any]] = {}
        if isinstance(loops, Mapping):
            declared = {str(name): _sequence(value, f"loops.{name}") for name, value in loops.items()}
            declared_roles = {_loop_role(name) for name in declared}
            declared_match = (len(cycles) == 5 and len(declared) == 5
                              and all(any(_cyclic_equal(actual, expected) for expected in declared.values())
                                      for actual in cycles))
            declared_match = declared_match and declared_roles == _declared_loop_names(protocol)
        else:
            _error(report, "boundary_declaration", "mesh must declare named neck, arm, and ankle loops")

        metadata = parsed["metadata"] if isinstance(parsed["metadata"], Mapping) else {}
        arm_present = "arms" in metadata
        arm_contract: dict[str, Any] = {
            "present": False, "indices": {side: [] for side in _SIDES},
            "all_indices": set(),
        }
        arm_metadata_valid = not arm_present
        arm_indices: set[int] = set()
        chain_indices: set[int] = set()
        chains = metadata.get("chains")
        if isinstance(chains, Mapping):
            for side in _SIDES:
                chain = chains.get(side)
                if isinstance(chain, Mapping):
                    values = chain.get("new_vertex_indices", ())
                    if isinstance(values, (list, tuple)):
                        chain_indices.update(index for index in values
                                             if isinstance(index, int) and not isinstance(index, bool))
        if arm_present:
            try:
                occupied: set[int] = set()
                if isinstance(chains, Mapping):
                    for side in _SIDES:
                        chain = chains.get(side)
                        if isinstance(chain, Mapping):
                            values = chain.get("new_vertex_indices", ())
                            if isinstance(values, (list, tuple)):
                                occupied.update(index for index in values
                                                if isinstance(index, int) and not isinstance(index, bool))
                arm_contract = _arm_metadata_contract(parsed["value"], len(vertices), occupied)
                arm_indices = set(arm_contract["all_indices"])
                arm_metadata_valid = True
            except Exception as exc:
                _error(report, "arm_metadata", str(exc))

        head_present = "head" in metadata
        head_contract: dict[str, Any] = {
            "present": False, "source_port": [], "support": [],
            "new_vertex_indices": [], "all_indices": set(),
        }
        head_metadata_valid = not head_present
        if head_present:
            try:
                head_contract = _head_metadata_contract(
                    parsed["value"], len(vertices), arm_indices | chain_indices
                )
                head_metadata_valid = True
            except Exception as exc:
                _error(report, "head_metadata", str(exc))

        tail_present = "tail" in metadata
        tail_contract: dict[str, Any] = {
            "present": False, "new_vertex_indices": [], "all_indices": set(),
        }
        tail_metadata_valid = not tail_present
        if tail_present:
            try:
                tail_contract = _tail_metadata_contract(parsed["value"], len(vertices))
                tail_metadata_valid = True
            except Exception as exc:
                _error(report, "tail_metadata", str(exc))

        allocation_exclusions = (arm_indices |
                                 set(head_contract.get("all_indices", ())) |
                                 set(tail_contract.get("all_indices", ())))
        foot_present = "feet" in metadata
        foot_contract: dict[str, Any] = {"present": False, "indices": {side: [] for side in _SIDES}}
        foot_metadata_valid = not foot_present
        if foot_present:
            try:
                foot_contract = _foot_metadata_contract(parsed["value"], len(vertices), allocation_exclusions)
                foot_metadata_valid = True
            except Exception as exc:
                _error(report, "foot_metadata", str(exc))

        remaining_boundary_roles = {"neck", "arm.left", "arm.right",
                                    "ankle.left", "ankle.right"}
        if arm_present:
            remaining_boundary_roles -= {"arm.left", "arm.right"}
        if head_present:
            remaining_boundary_roles.discard("neck")
        if foot_present:
            remaining_boundary_roles -= {"ankle.left", "ankle.right"}
        declared_boundary_match = bool(
            isinstance(loops, Mapping)
            and len(cycles) == len(remaining_boundary_roles)
            and len(declared) == len(remaining_boundary_roles)
            and declared_roles == remaining_boundary_roles
            and all(any(_cyclic_equal(actual, expected) for expected in declared.values())
                    for actual in cycles)
        )
        foot_declared_match = declared_boundary_match if foot_present else False
        foot_boundary_contract = bool(foot_metadata_valid and boundary_valid and foot_declared_match)

        if not foot_present:
            foot_declared_match = False
            foot_boundary_contract = False

        if head_present:
            head_boundary_contract = bool(head_metadata_valid and boundary_valid and declared_boundary_match)
        else:
            head_boundary_contract = False

        if arm_present and isinstance(loops, Mapping):
            arm_declared_match = declared_boundary_match
        else:
            arm_declared_match = False
        arm_boundary_contract = bool(arm_metadata_valid and boundary_valid and arm_declared_match)

        triangle_rows = _triangles(quads)
        areas = [_triangle_area(vertices, triangle) for triangle in triangle_rows]
        edge_lengths = [_distance(vertices[left], vertices[right]) for left, right in incidence]
        quad_dots = []
        for face in quads:
            first = _triangle_normal(vertices, (face[0], face[1], face[2]))
            second = _triangle_normal(vertices, (face[0], face[2], face[3]))
            first_norm, second_norm = _norm(first), _norm(second)
            quad_dots.append(_dot(first, second) / (first_norm * second_norm)
                             if first_norm > 0.0 and second_norm > 0.0 else -1.0)
        minimum_edge = _require_limit(report, protocol, ("minimum_edge_over_scale",))
        minimum_area = _require_limit(report, protocol, ("minimum_triangle_area_over_scale_squared",))
        if isinstance(minimum_edge, tuple) or isinstance(minimum_area, tuple):
            raise ValueError("minimum edge and triangle area thresholds must be scalar")
        stencil_tolerance = _require_limit(report, protocol, (
            "weight_sum_max_abs_error", "weight_partition_tolerance",
        ))
        if isinstance(stencil_tolerance, tuple):
            raise ValueError("stencil partition tolerance must be scalar")

        stencils = parsed["stencils"]
        base_count = None
        for source in (metadata, protocol, protocol.get("checks")):
            if isinstance(source, Mapping) and isinstance(source.get("base_vertex_count"), int):
                base_count = source["base_vertex_count"]
                break
        if arm_present and arm_metadata_valid:
            base_count = arm_contract["base_count"]
        if head_present and head_metadata_valid:
            base_count = head_contract["base_count"]
        if foot_present:
            base_count = (foot_contract["base_count"] if foot_metadata_valid
                          else len(vertices) if parsed["value"].get("level", metadata.get("level", 0)) == 0
                          else base_count)
        stencil_valid = False
        if stencils is not None:
            _stencil_rows(stencils, len(vertices), base_count, "mesh.base_stencils",
                          stencil_tolerance)
            stencil_valid = True
        else:
            _error(report, "missing_base_stencils", "mesh.base_stencils is required")

        component_count = _connected_components(quads, len(vertices))
        report["metrics"].update({
            "vertex_count": len(vertices), "quad_count": len(quads),
            "triangle_count": len(triangle_rows), "connected_components": component_count,
            "boundary_count": len(cycles), "triangle_area_min": min(areas, default=None),
            "edge_length_min": min(edge_lengths, default=None),
            "quad_triangle_normal_dot_min": min(quad_dots, default=None),
        })
        report["diagnostics"]["quad_triangle_dihedral"] = {
            "gated": False,
            "minimum_normal_dot": min(quad_dots, default=None),
        }
        report["uncertainties"].append(
            "No quad-dihedral threshold is declared; the normal-dot value is diagnostic only."
        )
        report["checks"].update({
            "finite_vertices_and_quads": True,
            "one_connected_component": component_count == 1,
            "no_nonmanifold_edges": edge_use,
            "no_orientation_conflicts": orientation,
            "edge_minimum": bool(edge_lengths) and min(edge_lengths) >= minimum_edge,
            "triangle_minimum_area": bool(areas) and min(areas) >= minimum_area,
            "base_stencils_positive_partition_unity": stencil_valid,
        })
        if arm_present:
            report["checks"].update({
                "arm_metadata_contract": arm_metadata_valid,
                "arm_closed_boundary_contract": arm_boundary_contract,
                "no_hand_boundary": arm_boundary_contract,
            })
            if not arm_boundary_contract:
                _error(report, "arm_boundary_contract",
                       "closed arm ports require only the declared neck and optional ankle boundaries")
        if head_present:
            report["checks"].update({
                "head_metadata_contract": head_metadata_valid,
                "head_consumed_neck_boundary": head_boundary_contract,
                "no_head_upper_boundary": head_boundary_contract,
            })
            if not head_boundary_contract:
                _error(report, "head_boundary_contract",
                       "neck_head must consume the named neck boundary and leave only unconsumed ports")
        if foot_present:
            report["checks"].update({
                "foot_metadata_contract": foot_metadata_valid,
                "foot_closed_boundary_contract": foot_boundary_contract,
            })
            if not foot_boundary_contract:
                _error(report, "foot_boundary_contract",
                       "closed foot metadata requires exactly neck and two arm boundaries")
        if tail_present:
            report["checks"]["tail_metadata_contract"] = tail_metadata_valid
            if not tail_metadata_valid:
                _error(report, "tail_metadata_contract",
                       "tail metadata must declare the pinned host replacement and binding supports")
        elif not foot_present and not tail_present and not arm_present and not head_present:
            report["checks"].update({
                "exact_five_boundary_loops": boundary_valid and len(cycles) == 5,
                "declared_neck_two_arms_two_ankles": declared_match,
            })
        if component_count != 1:
            _error(report, "disconnected_surface", "mesh must have one connected component")
        if not edge_use:
            _error(report, "nonmanifold_edges", "every edge must have one or two incident faces")
        if not orientation:
            _error(report, "orientation_conflict", "shared edges must have opposite directions")
        if not edge_lengths or min(edge_lengths) < minimum_edge:
            _error(report, "short_edge", "an edge is below the declared protocol minimum")
        if not areas or min(areas) < minimum_area:
            _error(report, "small_triangle_area", "a triangle is below the declared protocol minimum")
        if not stencil_valid:
            _error(report, "invalid_base_stencils", "base stencils must be positive and partition unity")
    except Exception as exc:
        if not report["errors"] or report["errors"][-1].get("detail") != str(exc):
            _error(report, "input_or_check_failure", str(exc))
    return _finish(report)


def _identity_matrix() -> list[list[float]]:
    return [[1.0 if row == column else 0.0 for column in range(4)] for row in range(4)]


def _mm(a: Sequence[Sequence[float]], b: Sequence[Sequence[float]]) -> list[list[float]]:
    return [[sum(a[row][k] * b[k][column] for k in range(4)) for column in range(4)] for row in range(4)]


def _mp(matrix: Sequence[Sequence[float]], point: Sequence[float]) -> tuple[float, float, float]:
    values = [float(point[0]), float(point[1]), float(point[2]), 1.0]
    return tuple(sum(matrix[row][column] * values[column] for column in range(4)) for row in range(3))  # type: ignore[return-value]


def _inverse(matrix: Sequence[Sequence[float]]) -> list[list[float]]:
    augmented = [list(map(float, matrix[row])) + [1.0 if row == column else 0.0 for column in range(4)] for row in range(4)]
    for column in range(4):
        pivot = max(range(column, 4), key=lambda row: abs(augmented[row][column]))
        if abs(augmented[pivot][column]) == 0.0:
            raise ValueError("matrix is singular")
        augmented[column], augmented[pivot] = augmented[pivot], augmented[column]
        divisor = augmented[column][column]
        augmented[column] = [value / divisor for value in augmented[column]]
        for row in range(4):
            if row == column:
                continue
            factor = augmented[row][column]
            augmented[row] = [left - factor * right for left, right in zip(augmented[row], augmented[column])]
    return [row[4:] for row in augmented]


def _rotation_x(degrees: float, sign: float) -> list[list[float]]:
    angle = math.radians(sign * degrees)
    cosine, sine = math.cos(angle), math.sin(angle)
    return [[1.0, 0.0, 0.0, 0.0],
            [0.0, cosine, -sine, 0.0],
            [0.0, sine, cosine, 0.0],
            [0.0, 0.0, 0.0, 1.0]]


def _rotation_y(degrees: float) -> list[list[float]]:
    angle = math.radians(degrees)
    cosine, sine = math.cos(angle), math.sin(angle)
    return [[cosine, 0.0, sine, 0.0],
            [0.0, 1.0, 0.0, 0.0],
            [-sine, 0.0, cosine, 0.0],
            [0.0, 0.0, 0.0, 1.0]]


def _rotation_z(degrees: float) -> list[list[float]]:
    angle = math.radians(degrees)
    cosine, sine = math.cos(angle), math.sin(angle)
    return [[cosine, -sine, 0.0, 0.0],
            [sine, cosine, 0.0, 0.0],
            [0.0, 0.0, 1.0, 0.0],
            [0.0, 0.0, 0.0, 1.0]]


def _normalise_vector(value: Sequence[float], label: str) -> tuple[float, float, float]:
    length = _norm(value)
    if not math.isfinite(length) or length <= 0.0:
        raise ValueError(f"{label} must have positive finite length")
    return _scale(value, 1.0 / length)


def _source_frame(origin: Sequence[float], distal: Sequence[float], label: str) -> list[list[float]]:
    y_axis = _normalise_vector(_sub(origin, distal), f"{label} Y axis")
    world_x = (1.0, 0.0, 0.0)
    x_axis = _normalise_vector(
        _sub(world_x, _scale(y_axis, _dot(world_x, y_axis))),
        f"{label} projected +X",
    )
    z_axis = _normalise_vector(_cross(x_axis, y_axis), f"{label} Z axis")
    result = _identity_matrix()
    for row in range(3):
        result[row][0] = x_axis[row]
        result[row][1] = y_axis[row]
        result[row][2] = z_axis[row]
        result[row][3] = float(origin[row])
    return result


def _arm_source_frame(origin: Sequence[float], distal: Sequence[float],
                      label: str) -> list[list[float]]:
    """Build the settled arm frame from the source J->E or E->W bone."""
    y_axis = _normalise_vector(_sub(origin, distal), f"{label} Y axis")
    world_y = (0.0, 1.0, 0.0)
    x_axis = _normalise_vector(
        _sub(world_y, _scale(y_axis, _dot(world_y, y_axis))),
        f"{label} projected +Y",
    )
    z_axis = _normalise_vector(_cross(x_axis, y_axis), f"{label} Z axis")
    if _dot(z_axis, (0.0, 0.0, 1.0)) < 0.0:
        x_axis = _scale(x_axis, -1.0)
        z_axis = _scale(z_axis, -1.0)
    result = _identity_matrix()
    for row in range(3):
        result[row][0] = x_axis[row]
        result[row][1] = y_axis[row]
        result[row][2] = z_axis[row]
        result[row][3] = float(origin[row])
    return result


def _source_leg_points(leg_inputs: Mapping[str, Any]) -> dict[str, dict[str, tuple[float, float, float]]]:
    raw = _mapping(leg_inputs, "leg_inputs")
    if set(raw) != set(_SIDES):
        raise ValueError("leg_inputs must contain exactly left and right")
    return {
        side: {
            name: _vector(_mapping(raw[side], f"leg_inputs.{side}").get(name),
                          f"leg_inputs.{side}.{name}")
            for name in ("J", "T", "K", "A")
        }
        for side in _SIDES
    }


def _source_joint_rows(leg_inputs: Mapping[str, Any]) -> tuple[
    dict[str, dict[str, list[list[float]]]],
    dict[str, dict[str, tuple[float, float, float]]],
]:
    points = _source_leg_points(leg_inputs)
    identity = _identity_matrix()
    rows = {"pelvis": {"rest": identity, "inverse_bind": identity}}
    for side in _SIDES:
        thigh = _source_frame(points[side]["J"], points[side]["K"], f"{side} thigh")
        knee = _source_frame(points[side]["K"], points[side]["A"], f"{side} knee")
        rows[f"{side}_hip"] = {"rest": thigh, "inverse_bind": _inverse(thigh)}
        rows[f"{side}_knee"] = {"rest": knee, "inverse_bind": _inverse(knee)}
    return rows, points


def _matrix_max_error(left: Sequence[Sequence[float]], right: Sequence[Sequence[float]]) -> float:
    return max(abs(float(left[row][column]) - float(right[row][column]))
               for row in range(4) for column in range(4))


def _binding_source_error(binding: Mapping[str, Any], leg_inputs: Mapping[str, Any]) -> tuple[float, bool]:
    source_rows, source_points = _source_joint_rows(leg_inputs)
    order, binding_rows, parents = _joint_rows(binding)
    expected_parents = {"pelvis": None, "left_hip": "pelvis", "left_knee": "left_hip",
                        "right_hip": "pelvis", "right_knee": "right_hip"}
    if tuple(order) in (_ARM_JOINTS, _ARM_HEAD_JOINTS):
        expected_parents.update({"left_shoulder": "pelvis", "left_elbow": "left_shoulder",
                                 "right_shoulder": "pelvis", "right_elbow": "right_shoulder"})
    if tuple(order) in (_HEAD_JOINTS, _ARM_HEAD_JOINTS):
        expected_parents["neck"] = "pelvis"
    structure_ok = tuple(order) in (_JOINTS, _HEAD_JOINTS, _ARM_JOINTS, _ARM_HEAD_JOINTS) and parents == expected_parents
    errors = []
    for name in _JOINTS:
        errors.append(_matrix_max_error(binding_rows[name]["rest"], source_rows[name]["rest"]))
        errors.append(_matrix_max_error(binding_rows[name]["inverse_bind"], source_rows[name]["inverse_bind"]))
    frames = _mapping(binding.get("rest_frames"), "binding.rest_frames")
    expected_frame_keys = set(_SIDES)
    if tuple(order) in (_HEAD_JOINTS, _ARM_HEAD_JOINTS):
        expected_frame_keys.add("head")
    if set(frames) != expected_frame_keys:
        raise ValueError("binding.rest_frames must contain exactly the declared side and head frames")
    for side in _SIDES:
        frame = _mapping(frames[side], f"binding.rest_frames.{side}")
        for point_name in ("J", "T", "K", "A"):
            errors.append(_distance(_vector(frame.get(point_name),
                                            f"binding.rest_frames.{side}.{point_name}"),
                                    source_points[side][point_name]))
        thigh = _mapping(frame.get("thigh"), f"binding.rest_frames.{side}.thigh")
        knee = _mapping(frame.get("knee"), f"binding.rest_frames.{side}.knee")
        errors.append(_matrix_max_error(
            _matrix(thigh.get("rest_global", thigh.get("rest_matrix")),
                    f"binding.rest_frames.{side}.thigh.rest_global"),
            source_rows[f"{side}_hip"]["rest"],
        ))
        errors.append(_matrix_max_error(
            _matrix(knee.get("rest_global", knee.get("rest_matrix")),
                    f"binding.rest_frames.{side}.knee.rest_global"),
            source_rows[f"{side}_knee"]["rest"],
        ))
    if tuple(order) in (_HEAD_JOINTS, _ARM_HEAD_JOINTS):
        frames = _mapping(binding.get("rest_frames"), "binding.rest_frames")
        head_frame = _mapping(frames.get("head"), "binding.rest_frames.head")
        head_joint = binding_rows["neck"]
        head_j = _vector(head_frame.get("J"), "binding.rest_frames.head.J")
        expected = _identity_matrix()
        for row in range(3):
            expected[row][3] = head_j[row]
        errors.extend((_matrix_max_error(head_joint["rest"], expected),
                       _matrix_max_error(head_joint["inverse_bind"], _inverse(expected))))
    return max(errors, default=math.inf), structure_ok


def _joint_angles(angles: Mapping[str, Any], side: str) -> tuple[float, float]:
    row = angles.get(side)
    if isinstance(row, Mapping):
        hip = row.get("hip", row.get(f"{side}_hip", 0.0))
        knee = row.get("knee", row.get(f"{side}_knee", 0.0))
    elif row is not None:
        hip, knee = row, 0.0
    else:
        hip = angles.get(f"{side}_hip", 0.0)
        knee = angles.get(f"{side}_knee", 0.0)
    return _number(hip, f"angles.{side}.hip"), _number(knee, f"angles.{side}.knee")


def _joint_rows(binding: Mapping[str, Any]) -> tuple[list[str], dict[str, dict[str, Any]], dict[str, str | None]]:
    raw_order = binding.get("joint_order", _JOINTS)
    order = [str(item) for item in _sequence(raw_order, "binding.joint_order")]
    if tuple(order) not in (_JOINTS, _HEAD_JOINTS, _ARM_JOINTS, _ARM_HEAD_JOINTS) or len(set(order)) != len(order):
        raise ValueError("binding must expose the exact five-, six-, nine-, or ten-joint contract")
    raw_joints = binding.get("joints")
    if not isinstance(raw_joints, Mapping):
        raise ValueError("binding.joints is required for independent hierarchical reconstruction")
    rows: dict[str, dict[str, Any]] = {}
    for name in order:
        row = _mapping(raw_joints.get(name), f"binding.joints.{name}")
        rows[name] = {
            "rest": _matrix(row.get("rest_matrix"), f"binding.joints.{name}.rest_matrix"),
            "inverse_bind": _matrix(row.get("inverse_bind_matrix", row.get("inverse_bind")),
                                     f"binding.joints.{name}.inverse_bind_matrix"),
        }
    raw_parents = binding.get("parents", binding.get("hierarchy"))
    parents: dict[str, str | None] = {"pelvis": None, "left_hip": "pelvis", "left_knee": "left_hip",
                                      "right_hip": "pelvis", "right_knee": "right_hip"}
    if tuple(order) in (_ARM_JOINTS, _ARM_HEAD_JOINTS):
        parents.update({"left_shoulder": "pelvis", "left_elbow": "left_shoulder",
                        "right_shoulder": "pelvis", "right_elbow": "right_shoulder"})
    if tuple(order) in (_HEAD_JOINTS, _ARM_HEAD_JOINTS):
        parents["neck"] = "pelvis"
    if isinstance(raw_parents, Mapping):
        for name in order:
            if name in raw_parents:
                parent = raw_parents[name]
                parents[name] = None if parent is None else str(parent)
    for name, parent in parents.items():
        if name in rows and parent is not None and parent not in rows:
            raise ValueError(f"binding hierarchy parent {parent} is missing")
    return order, rows, parents


def _expected_joint_poses(leg_inputs: Mapping[str, Any], angles: Mapping[str, Any],
                          binding: Mapping[str, Any] | None = None) -> tuple[list[str], dict[str, list[list[float]]], dict[str, list[list[float]]]]:
    if binding is None:
        rows, _points = _source_joint_rows(leg_inputs)
        order = list(_JOINTS)
        parents = {"pelvis": None, "left_hip": "pelvis", "left_knee": "left_hip",
                   "right_hip": "pelvis", "right_knee": "right_hip"}
    else:
        order, parsed_rows, parents = _joint_rows(binding)
        rows = {name: {"rest": row["rest"], "inverse_bind": row["inverse_bind"]}
                for name, row in parsed_rows.items()}
    arm_angles = _arm_angles(angles) if tuple(order) in (_ARM_JOINTS, _ARM_HEAD_JOINTS) else None
    head_angles = _head_angles(angles) if tuple(order) in (_HEAD_JOINTS, _ARM_HEAD_JOINTS) else None
    local_rest: dict[str, list[list[float]]] = {}
    for name in order:
        parent = parents.get(name)
        local_rest[name] = rows[name]["rest"] if parent is None else _mm(_inverse(rows[parent]["rest"]), rows[name]["rest"])
    posed: dict[str, list[list[float]]] = {}
    for name in order:
        parent = parents.get(name)
        if name == "pelvis":
            joint_angle = 0.0
            local_rotation = _identity_matrix()
        elif name in {"left_hip", "left_knee", "right_hip", "right_knee"}:
            side = "left" if name.startswith("left_") else "right"
            hip_angle, knee_angle = _joint_angles(angles, side)
            joint_angle = hip_angle if name.endswith("hip") else knee_angle
            sign = -1.0 if name.endswith("hip") else 1.0
            local_rotation = _rotation_x(joint_angle, sign)
        elif name == "neck":
            if head_angles is None:
                raise ValueError("neck joint rows require head angles")
            local_rotation = _mm(_rotation_y(head_angles["yaw"]),
                                 _rotation_x(head_angles["nod"], 1.0))
        else:
            if arm_angles is None:
                raise ValueError("arm joint rows require arm angles")
            side = "left" if name.startswith("left_") else "right"
            if name.endswith("shoulder"):
                local_rotation = _mm(
                    _rotation_z((-1.0 if side == "left" else 1.0) *
                                arm_angles[side]["shoulder_raise"]),
                    _rotation_x(arm_angles[side]["shoulder_forward"], -1.0),
                )
            elif name.endswith("elbow"):
                local_rotation = _rotation_x(arm_angles[side]["elbow"], -1.0)
            else:
                raise ValueError(f"unsupported arm joint {name}")
        local_pose = _mm(local_rest[name], local_rotation)
        posed[name] = local_pose if parent is None else _mm(posed[parent], local_pose)
    skins = {name: _mm(posed[name], rows[name]["inverse_bind"]) for name in order}
    return order, posed, skins


def _weights(binding: Mapping[str, Any], count: int, order: Sequence[str]) -> list[list[float]]:
    raw = binding.get("evaluated_weights", binding.get("weights"))
    rows = _sequence(raw, "binding.evaluated_weights")
    if len(rows) != count:
        raise ValueError("binding.evaluated_weights must cover every rest vertex")
    result: list[list[float]] = []
    for index, raw_row in enumerate(rows):
        if isinstance(raw_row, Mapping):
            if set(raw_row).difference(order):
                raise ValueError(f"binding weight row {index} names an unknown joint")
            row = [_number(raw_row.get(name, 0.0), f"weight[{index}].{name}") for name in order]
        else:
            values = _sequence(raw_row, f"binding.evaluated_weights[{index}]")
            if len(values) != len(order):
                raise ValueError(f"binding weight row {index} must contain five columns")
            row = [_number(value, f"weight[{index}][{column}]") for column, value in enumerate(values)]
        result.append(row)
    return result


def _lbs(vertices: Sequence[Sequence[float]], weights: Sequence[Sequence[float]], skins: Mapping[str, Sequence[Sequence[float]]], order: Sequence[str]) -> list[tuple[float, float, float]]:
    result = []
    for point, row in zip(vertices, weights):
        contributions = [_scale(_mp(skins[name], point), row[index]) for index, name in enumerate(order)]
        value = (0.0, 0.0, 0.0)
        for contribution in contributions:
            value = _add(value, contribution)
        result.append(value)
    return result


def _mesh_topology_equal(rest: Mapping[str, Any], posed: Mapping[str, Any]) -> bool:
    return (rest.get("quads") == posed.get("quads")
            and rest.get("loops", rest.get("boundary_loops")) == posed.get("loops", posed.get("boundary_loops")))


def _arm_angles(angles: Mapping[str, Any]) -> dict[str, dict[str, float]]:
    result: dict[str, dict[str, float]] = {}
    for side in _SIDES:
        row = _mapping(angles.get(side), f"angles.{side}")
        allowed = {"hip", "knee", "ankle", "shoulder_raise",
                   "shoulder_forward", "elbow"}
        if set(row).difference(allowed):
            raise ValueError(f"angles.{side} contains an unsupported arm angle")
        result[side] = {
            name: _number(row.get(name, 0.0), f"angles.{side}.{name}")
            for name in ("shoulder_raise", "shoulder_forward", "elbow")
        }
    return result


def _head_angles(angles: Mapping[str, Any]) -> dict[str, float]:
    row = angles.get("head", {})
    row = _mapping(row, "angles.head")
    if set(row).difference({"yaw", "nod"}):
        raise ValueError("angles.head contains an unsupported neck/head angle")
    return {name: _number(row.get(name, 0.0), f"angles.head.{name}")
            for name in ("yaw", "nod")}


def _arm_endpoint_oracle(binding: Mapping[str, Any],
                         angles: Mapping[str, Any]) -> dict[str, Any]:
    """Independently derive arm endpoints from source bones and settled angles."""
    parsed_angles = _arm_angles(angles)
    frames = _mapping(binding.get("rest_frames"), "binding.rest_frames")
    result: dict[str, Any] = {}
    for side in _SIDES:
        frame = _mapping(frames.get(side), f"binding.rest_frames.{side}")
        source = _mapping(frame.get("arm_source_points"),
                          f"binding.rest_frames.{side}.arm_source_points")
        points = {name: _vector(source.get(name),
                                f"binding.rest_frames.{side}.arm_source_points.{name}")
                  for name in ("J", "E", "W")}
        shoulder_rest = _arm_source_frame(points["J"], points["E"],
                                           f"{side} shoulder")
        elbow_rest = _arm_source_frame(points["E"], points["W"],
                                       f"{side} elbow")
        shoulder_local = _mm(
            _rotation_z((-1.0 if side == "left" else 1.0) *
                        parsed_angles[side]["shoulder_raise"]),
            _rotation_x(parsed_angles[side]["shoulder_forward"], -1.0),
        )
        elbow_local = _rotation_x(parsed_angles[side]["elbow"], -1.0)
        shoulder_pose = _mm(shoulder_rest, shoulder_local)
        elbow_pose = _mm(
            _mm(_mm(shoulder_pose, _inverse(shoulder_rest)), elbow_rest),
            elbow_local,
        )
        shoulder_skin = _mm(shoulder_pose, _inverse(shoulder_rest))
        elbow_skin = _mm(elbow_pose, _inverse(elbow_rest))
        result[side] = {
            "rest": points,
            "posed": {
                "J": _mp(shoulder_skin, points["J"]),
                "E": _mp(shoulder_skin, points["E"]),
                "W": _mp(elbow_skin, points["W"]),
            },
            "shoulder_matrix": shoulder_pose,
            "elbow_matrix": elbow_pose,
        }
    return result


def _head_source_frame_error(report: dict[str, Any], binding: Mapping[str, Any],
                             head_contract: Mapping[str, Any], tolerance: float) -> float:
    """Compare the complete neck source frame and inverse bind to the handoff pivot."""
    frames = _mapping(binding.get("rest_frames"), "binding.rest_frames")
    frame = _mapping(frames.get("head"), "binding.rest_frames.head")
    joints = _mapping(binding.get("joints"), "binding.joints")
    joint = _mapping(joints.get("neck"), "binding.joints.neck")
    pivot = _vector(frame.get("J"), "binding.rest_frames.head.J")
    expected = _identity_matrix()
    for row in range(3):
        expected[row][3] = pivot[row]
    error = max(
        _distance(pivot, head_contract["J"]),
        _matrix_error(_matrix(frame.get("rest_global", frame.get("rest_matrix")),
                              "binding.rest_frames.head.rest_global"), expected),
        _matrix_error(_matrix(joint.get("rest_matrix"),
                              "binding.joints.neck.rest_matrix"), expected),
        _matrix_error(_matrix(joint.get("inverse_bind_matrix", joint.get("inverse_bind")),
                              "binding.joints.neck.inverse_bind_matrix"), _inverse(expected)),
    )
    report["metrics"]["head_source_frame_max_error"] = error
    declaration_ok = (frame.get("pivot_source") == "stations.neck_collar.C"
                      and frame.get("frame_source", _HEAD_FRAME_SOURCE) == _HEAD_FRAME_SOURCE)
    report["checks"]["head_source_pivot_declaration"] = declaration_ok
    report["checks"]["head_source_rest_inversebind_matrices"] = error <= tolerance
    if not declaration_ok:
        _error(report, "head_source_declaration",
               "neck_head must declare stations.neck_collar.C as its pivot source")
    if error > tolerance:
        _error(report, "head_source_matrices",
               "neck rest and inverse-bind matrices must be the complete source pivot frame")
    return error


def _head_endpoint_oracle(binding: Mapping[str, Any], angles: Mapping[str, Any]) -> dict[str, Any]:
    """Derive neck/head endpoint motion from the source pivot, independently of binder pose code."""
    frames = _mapping(binding.get("rest_frames"), "binding.rest_frames")
    frame = _mapping(frames.get("head"), "binding.rest_frames.head")
    pivot = _vector(frame.get("J"), "binding.rest_frames.head.J")
    parsed = _head_angles(angles)
    rest = _identity_matrix()
    for row in range(3):
        rest[row][3] = pivot[row]
    posed = _mm(rest, _mm(_rotation_y(parsed["yaw"]), _rotation_x(parsed["nod"], 1.0)))
    skin = _mm(posed, _inverse(rest))
    rest_forward = _add(pivot, (0.0, 0.0, 1.0))
    posed_pivot = _mp(skin, pivot)
    posed_forward = _mp(skin, rest_forward)
    return {"rest_global": rest, "posed_global": posed, "skin_matrix": skin,
            "rest_J": pivot, "posed_J": posed_pivot,
            "rest_forward_endpoint": rest_forward,
            "posed_forward_endpoint": posed_forward,
            "angle_degrees": parsed,
            "pose_rotation_order": "Ry(yaw) @ Rx(nod)"}


def _check_head_endpoint_oracle(report: dict[str, Any], binding: Mapping[str, Any],
                                angles: Mapping[str, Any], posed_joints: Mapping[str, Any],
                                tolerance: float) -> None:
    oracle = _head_endpoint_oracle(binding, angles)
    actual = posed_joints.get("neck")
    actual_error = (_matrix_error(actual, oracle["posed_global"])
                    if actual is not None else math.inf)
    direction = _sub(oracle["posed_forward_endpoint"], oracle["posed_J"])
    yaw_probe = dict(angles)
    yaw_probe["head"] = {"yaw": 10.0, "nod": 0.0}
    nod_probe = dict(angles)
    nod_probe["head"] = {"yaw": 0.0, "nod": 10.0}
    yaw = _head_endpoint_oracle(binding, yaw_probe)
    nod = _head_endpoint_oracle(binding, nod_probe)
    yaw_ok = yaw["posed_forward_endpoint"][0] > yaw["rest_forward_endpoint"][0]
    nod_ok = nod["posed_forward_endpoint"][1] < nod["rest_forward_endpoint"][1]
    report["checks"].update({
        "head_endpoint_source_oracle": actual_error <= tolerance,
        "head_positive_yaw_face_plus_x": yaw_ok,
        "head_positive_nod_face_down": nod_ok,
    })
    report["metrics"].update({
        "head_endpoint_oracle_max_error": actual_error,
        "head_rest_forward_direction": [0.0, 0.0, 1.0],
        "head_pose_forward_direction": list(direction),
        "head_yaw10_forward_endpoint": list(yaw["posed_forward_endpoint"]),
        "head_nod10_forward_endpoint": list(nod["posed_forward_endpoint"]),
    })
    if actual_error > tolerance:
        _error(report, "head_endpoint_oracle",
               "posed neck transform does not match the independent pivot endpoint oracle")
    if not yaw_ok:
        _error(report, "head_yaw_direction", "positive yaw 10 must move the face direction toward +X")
    if not nod_ok:
        _error(report, "head_nod_direction", "positive nod 10 must move the face direction downward")


def _check_arm_endpoint_oracle(report: dict[str, Any], binding: Mapping[str, Any],
                               angles: Mapping[str, Any],
                               posed_joints: Mapping[str, Sequence[Sequence[float]]],
                               tolerance: float) -> None:
    """Check parent endpoints and semantic positive-angle directions."""
    oracle = _arm_endpoint_oracle(binding, angles)
    endpoint_error = 0.0
    for side in _SIDES:
        for joint_name, point_name in ((f"{side}_shoulder", "J"),
                                       (f"{side}_elbow", "E")):
            matrix = _matrix(posed_joints[joint_name],
                             f"posed joint {joint_name}")
            expected = oracle[side]["posed"][point_name]
            endpoint_error = max(endpoint_error,
                                 max(abs(matrix[row][3] - expected[row])
                                     for row in range(3)))

    zero = {side: {"shoulder_raise": 0.0, "shoulder_forward": 0.0,
                   "elbow": 0.0} for side in _SIDES}
    direction_checks: dict[str, bool] = {}
    for side in _SIDES:
        for angle_name, point_name, component, label in (
            ("shoulder_raise", "E", 1, "raise_E_y_increases"),
            ("shoulder_forward", "E", 2, "forward_E_z_increases"),
            ("elbow", "W", 2, "elbow_W_z_increases"),
        ):
            probe_angles = copy.deepcopy(zero)
            probe_angles[side][angle_name] = 10.0
            probe = _arm_endpoint_oracle(binding, probe_angles)[side]
            direction_checks[f"{side}_{label}"] = (
                probe["posed"][point_name][component] >
                probe["rest"][point_name][component]
            )
    report["metrics"]["arm_endpoint_oracle"] = {
        side: {"rest": data["rest"], "posed": data["posed"]}
        for side, data in oracle.items()
    }
    report["metrics"]["arm_endpoint_max_error"] = endpoint_error
    report["checks"]["arm_endpoint_parent_oracle"] = endpoint_error <= tolerance
    report["checks"].update(direction_checks)
    if endpoint_error > tolerance:
        _error(report, "arm_endpoint_oracle",
               "arm shoulder/elbow parent endpoints do not match the independent source-bone oracle")
    for name, passed in direction_checks.items():
        if not passed:
            _error(report, name,
                   "positive arm angle has the wrong anatomical endpoint direction")


def check_pose(rest: Mapping[str, Any], posed: Mapping[str, Any], binding: Mapping[str, Any],
               angles: Mapping[str, Any], protocol: Mapping[str, Any],
               leg_inputs: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Independently verify a posed surface for the supported 5/6/9/10 layouts."""
    report = _report("creature-kernel.connected-leg-assembly-pose-checks.v1")
    try:
        rest_parsed = _mesh(rest, "rest")
        posed_parsed = _mesh(posed, "posed")
        if len(rest_parsed["vertices"]) != len(posed_parsed["vertices"]):
            raise ValueError("rest and posed vertex counts differ")
        topology = _mesh_topology_equal(rest, posed)
        report["checks"]["unchanged_topology"] = topology
        if not topology:
            _error(report, "topology_changed", "posed mesh must preserve vertex-indexed quads and declared loops")

        bound = _mapping(binding, "binding")
        binding_order = tuple(bound.get("joint_order", ()))
        arm_binding = binding_order in (_ARM_JOINTS, _ARM_HEAD_JOINTS)
        head_binding = binding_order in (_HEAD_JOINTS, _ARM_HEAD_JOINTS)
        if arm_binding:
            _arm_angles(_mapping(angles, "angles"))
            report["checks"]["arm_pose_angle_interface"] = True
        if head_binding:
            _head_angles(_mapping(angles, "angles"))
            report["checks"]["head_pose_angle_interface"] = True
        if leg_inputs is None:
            raise ValueError("independent check_pose requires immutable leg_inputs")
        source_inputs = _mapping(leg_inputs, "leg_inputs")
        binding_inputs = _mapping(bound.get("leg_inputs"), "binding.leg_inputs")
        input_copy_matches = binding_inputs == source_inputs
        source_error, hierarchy_matches = _binding_source_error(bound, source_inputs)
        source_limit = _require_limit(report, protocol, (
            "rest_transform_max_abs_error", "hierarchical_K_A_response_max_abs_error",
            "independent_lbs_tolerance",
        ))
        if isinstance(source_limit, tuple):
            raise ValueError("source-frame tolerance must be scalar")
        report["checks"].update({
            "binding_leg_inputs_match_immutable_inputs": input_copy_matches,
            "binding_rest_sources_match_J_K_A": hierarchy_matches and source_error <= source_limit,
        })
        report["metrics"]["binding_rest_source_max_error"] = source_error
        if not input_copy_matches:
            _error(report, "binding_leg_inputs", "binding leg_inputs do not match the immutable case inputs")
        if not hierarchy_matches or source_error > source_limit:
            _error(report, "binding_rest_sources", "binding rest frames or inverse binds do not match source-derived J/K/A frames")
        if arm_binding:
            try:
                rest_metadata = _mapping(rest.get("metadata", {}), "rest.metadata")
                if "arms" in rest_metadata:
                    arm_contract = _arm_metadata_contract(
                        rest, len(rest_parsed["vertices"])
                    )
                else:
                    frames = _mapping(bound.get("rest_frames"), "binding.rest_frames")
                    arm_contract = {"source_points": {}}
                    for side in _SIDES:
                        source = _mapping(
                            _mapping(frames[side], f"binding.rest_frames.{side}")
                            .get("arm_source_points"),
                            f"binding.rest_frames.{side}.arm_source_points",
                        )
                        arm_contract["source_points"][side] = {
                            name: _vector(source.get(name),
                                          f"binding.rest_frames.{side}.arm_source_points.{name}")
                            for name in ("J", "E", "W")
                        }
                _check_arm_source_frames(report, bound, arm_contract, source_limit)
            except Exception as exc:
                _error(report, "arm_source_frames", str(exc))
        if head_binding:
            try:
                head_contract = _head_metadata_contract(
                    rest, len(rest_parsed["vertices"])
                )
                if not head_contract["present"]:
                    raise ValueError("head pose requires rest.metadata.head binding_handoff")
                _head_source_frame_error(report, bound, head_contract, source_limit)
            except Exception as exc:
                _error(report, "head_source_frames", str(exc))
        order, posed_joints, skins = _expected_joint_poses(
            source_inputs, _mapping(angles, "angles"), bound if (arm_binding or head_binding) else None
        )
        if arm_binding:
            _check_arm_endpoint_oracle(
                report, bound, _mapping(angles, "angles"), posed_joints, source_limit
            )
        if head_binding:
            _check_head_endpoint_oracle(
                report, bound, _mapping(angles, "angles"), posed_joints, source_limit
            )
        weights = _weights(binding, len(rest_parsed["vertices"]), order)
        partition_limit = _require_limit(report, protocol, (
            "weight_sum_max_abs_error", "weight_partition_tolerance",
        ))
        if isinstance(partition_limit, tuple):
            raise ValueError("weight partition tolerance must be scalar")
        finite_weights = all(math.isfinite(value) for row in weights for value in row)
        nonnegative_weights = all(value >= -partition_limit for row in weights for value in row)
        partition_error = max((abs(sum(row) - 1.0) for row in weights), default=math.inf)
        report["checks"].update({
            "five_joint_transforms": tuple(order) in (_JOINTS, _HEAD_JOINTS,
                                                       _ARM_JOINTS, _ARM_HEAD_JOINTS),
            "five_weight_columns": tuple(bound.get("weight_columns", ())) in (
                _WEIGHT_COLUMNS, _HEAD_WEIGHT_COLUMNS, _ARM_WEIGHT_COLUMNS,
                _ARM_HEAD_WEIGHT_COLUMNS),
            "six_joint_transforms": ((not head_binding) or
                                      tuple(order) in (_HEAD_JOINTS, _ARM_HEAD_JOINTS)),
            "six_weight_columns": ((not head_binding) or
                                    tuple(bound.get("weight_columns", ())) in (
                                        _HEAD_WEIGHT_COLUMNS, _ARM_HEAD_WEIGHT_COLUMNS)),
            "nine_joint_transforms": ((not arm_binding) or
                                       tuple(order) in (_ARM_JOINTS, _ARM_HEAD_JOINTS)),
            "nine_weight_columns": ((not arm_binding) or
                                     tuple(bound.get("weight_columns", ())) in (
                                         _ARM_WEIGHT_COLUMNS, _ARM_HEAD_WEIGHT_COLUMNS)),
            "ten_joint_transforms": ((not (arm_binding and head_binding)) or
                                      tuple(order) == _ARM_HEAD_JOINTS),
            "ten_weight_columns": ((not (arm_binding and head_binding)) or
                                    tuple(bound.get("weight_columns", ())) == _ARM_HEAD_WEIGHT_COLUMNS),
            "finite_weights": finite_weights,
            "nonnegative_weights": nonnegative_weights,
            "weight_partition_unity": finite_weights and partition_error <= partition_limit,
        })
        if not finite_weights:
            _error(report, "nonfinite_weights", "all five binding weights must be finite")
        if not nonnegative_weights:
            _error(report, "negative_weights", "binding weights must be nonnegative")
        if partition_error > partition_limit:
            _error(report, "weight_partition", "five binding weights must partition unity")

        expected_vertices = _lbs(rest_parsed["vertices"], weights, skins, order)
        actual_vertices = posed_parsed["vertices"]
        lbs_limit = _require_limit(report, protocol, (
            "source_effect_response_max_abs_error", "hierarchical_K_A_response_max_abs_error",
            "independent_lbs_tolerance", "exported_lbs_tolerance", "pose_position_tolerance",
        ))
        if isinstance(lbs_limit, tuple):
            raise ValueError("independent LBS tolerance must be scalar")
        lbs_errors = [_distance(actual, expected) for actual, expected in zip(actual_vertices, expected_vertices)]
        report["checks"]["independent_hierarchical_lbs"] = bool(lbs_errors) and max(lbs_errors) <= lbs_limit
        report["metrics"].update({"weight_partition_error": partition_error,
                                  "independent_lbs_max_error": max(lbs_errors, default=math.inf),
                                  "independent_lbs_worst_vertices": sorted(range(len(lbs_errors)), key=lbs_errors.__getitem__, reverse=True)[:_EXAMPLE_CAP],
                                  "joint_order": list(order),
                                  "posed_joint_matrices": posed_joints})
        if not report["checks"]["independent_hierarchical_lbs"]:
            _error(report, "independent_lbs", "posed vertices do not match independently reconstructed five-joint LBS")

        zero_pose = all(_joint_angles(angles, side) == (0.0, 0.0)
                        for side in ("left", "right"))
        if arm_binding:
            zero_pose = zero_pose and all(
                value == 0.0
                for row in _arm_angles(_mapping(angles, "angles")).values()
                for value in row.values()
            )
        if head_binding:
            zero_pose = zero_pose and all(
                value == 0.0 for value in
                _head_angles(_mapping(angles, "angles")).values()
            )
        identity_limit = _require_limit(report, protocol, (
            "rest_identity_max_abs_error", "identity_position_tolerance", "identity_rest_tolerance",
        ))
        if isinstance(identity_limit, tuple):
            raise ValueError("identity position tolerance must be scalar")
        identity_errors = [_distance(actual, expected) for actual, expected in zip(actual_vertices, rest_parsed["vertices"])]
        report["checks"]["identity_at_zero_angles"] = (not zero_pose) or (bool(identity_errors) and max(identity_errors) <= identity_limit)
        report["metrics"]["identity_checked"] = zero_pose
        report["metrics"]["identity_max_error"] = max(identity_errors, default=math.inf)

        lower_faces, upper_faces, face_start = _lower_faces(rest_parsed, protocol)
        report["metrics"].update({"prior_face_count": face_start, "lower_face_count": len(lower_faces), "inherited_upper_face_count": len(upper_faces)})
        report["checks"]["lower_face_inventory"] = bool(lower_faces)
        if not lower_faces:
            _error(report, "empty_lower_inventory", "lower checks require inherited pelvis/hip/abdomen or appended faces")

        area_range = _require_limit(report, protocol, (
            "triangle_area_ratio_report_range", "lower_triangle_area_ratio", "triangle_area_ratio",
        ))
        edge_range = _require_limit(report, protocol, (
            "edge_ratio_report_range", "lower_edge_strain_ratio", "edge_strain_ratio",
        ))
        if not isinstance(area_range, tuple) or not isinstance(edge_range, tuple):
            raise ValueError("pose diagnostic ranges have the wrong shape")
        rest_triangles, posed_triangles = _triangles(rest_parsed["quads"]), _triangles(posed_parsed["quads"])
        lower_triangle_ids = [index for index in range(len(rest_triangles)) if index // 2 in lower_faces]
        rest_areas = [_triangle_area(rest_parsed["vertices"], rest_triangles[index]) for index in lower_triangle_ids]
        posed_areas = [_triangle_area(actual_vertices, posed_triangles[index]) for index in lower_triangle_ids]
        area_ratios = [posed_area / rest_area if rest_area > 0.0 else math.inf for rest_area, posed_area in zip(rest_areas, posed_areas)]
        edges = sorted({tuple(sorted((face[slot], face[(slot + 1) % 4])))
                        for face_index, face in enumerate(rest_parsed["quads"]) if face_index in lower_faces
                        for slot in range(4)})
        edge_ratios = [_distance(actual_vertices[left], actual_vertices[right]) / _distance(rest_parsed["vertices"][left], rest_parsed["vertices"][right])
                       if _distance(rest_parsed["vertices"][left], rest_parsed["vertices"][right]) > 0.0 else math.inf
                       for left, right in edges]
        normal_dots = []
        for index in lower_triangle_ids:
            rest_normal = _triangle_normal(rest_parsed["vertices"], rest_triangles[index])
            posed_normal = _triangle_normal(actual_vertices, posed_triangles[index])
            denominator = _norm(rest_normal) * _norm(posed_normal)
            normal_dots.append(_dot(rest_normal, posed_normal) / denominator if denominator > 0.0 else -1.0)
        report["diagnostics"].update({
            "lower_edge_strain": {
                "range": list(edge_range),
                "outside_range": (not edge_ratios or min(edge_ratios) < edge_range[0]
                                  or max(edge_ratios) > edge_range[1]),
            },
            "lower_triangle_area_ratio": {
                "range": list(area_range),
                "outside_range": (not area_ratios or min(area_ratios) < area_range[0]
                                  or max(area_ratios) > area_range[1]),
            },
            "lower_normal_dot": {
                "gross_collapse": not normal_dots or min(normal_dots) <= 0.0,
                "gated": False,
            },
        })
        report["metrics"].update({
            "edge_strain_min": min(edge_ratios, default=math.inf), "edge_strain_max": max(edge_ratios, default=-math.inf),
            "triangle_area_ratio_min": min(area_ratios, default=math.inf), "triangle_area_ratio_max": max(area_ratios, default=-math.inf),
            "normal_dot_min": min(normal_dots, default=-1.0), "normal_dot_max": max(normal_dots, default=-1.0),
        })
        report["uncertainties"].append(
            "Strain, area-ratio, and corresponding-normal values are diagnostics; the protocol declares no anatomy acceptance gate."
        )

        owners = rest_parsed["face_owners"]
        if not isinstance(owners, Sequence) or len(owners) != len(rest_parsed["quads"]):
            raise ValueError("face_owners must cover every pose face")
        # Terminal-foot surfaces use the accepted broadphase wrapper.  The
        # historical five-port leg surface keeps the original checker route.
        arm_pose = ("arms" in _mapping(rest.get("metadata", {}), "rest.metadata")
                    or "arms" in _mapping(posed.get("metadata", {}), "posed.metadata"))
        foot_pose = ("feet" in _mapping(rest.get("metadata", {}), "rest.metadata")
                     or "feet" in _mapping(posed.get("metadata", {}), "posed.metadata"))
        head_pose = ("head" in _mapping(rest.get("metadata", {}), "rest.metadata")
                     or "head" in _mapping(posed.get("metadata", {}), "posed.metadata"))
        collision = (_foot_collision_report(actual_vertices, posed_parsed["quads"], owners,
                                            lower_faces, upper_faces)
                     if foot_pose or arm_pose or head_pose else
                     _collision_report(actual_vertices, posed_parsed["quads"], owners,
                                       lower_faces, upper_faces))
        report["checks"]["lower_collision_inventory"] = bool(collision["available"] and collision["coverage_complete"] and not collision["lower_hit_pairs"])
        report["checks"]["collision_coverage_complete"] = bool(collision["available"] and collision["coverage_complete"])
        report["metrics"]["collision"] = collision
        if not collision["available"]:
            _unavailable(report, "collision_unavailable", "collision coverage or generic intersection evidence is unavailable")
        elif collision["lower_hit_pairs"]:
            _error(report, "lower_collision", "relevant lower faces contain non-adjacent intersections", pairs=collision["lower_hit_pairs"][:_EXAMPLE_CAP])
    except Exception as exc:
        if not report["errors"] or report["errors"][-1].get("detail") != str(exc):
            _error(report, "input_or_check_failure", str(exc))
    return _finish(report)


def _source_station_values(binding: Mapping[str, Any], leg_inputs: Mapping[str, Any]) -> Any:
    sources = [binding, binding.get("metadata"), leg_inputs, leg_inputs.get("metadata") if isinstance(leg_inputs, Mapping) else None]
    for source in sources:
        if isinstance(source, Mapping):
            for key in ("source_station_knee", "source_station_knee_values", "base_source_station_knee"):
                if key in source:
                    return source[key]
            stations = source.get("source_stations")
            if isinstance(stations, Mapping) and "knee" in stations:
                return stations["knee"]
    return None


def _mapped_prior_weights(prior_binding: Mapping[str, Any], count: int) -> list[list[float]]:
    raw = prior_binding.get("base_weights", prior_binding.get("weights"))
    rows = _sequence(raw, "prior_hip_binding.base_weights")
    if len(rows) != count:
        raise ValueError("prior hip binding must cover the original 152 root vertices")
    result = []
    for index, row in enumerate(rows):
        values = _sequence(row, f"prior_hip_binding.base_weights[{index}]")
        if len(values) != 3:
            raise ValueError("prior hip binding must expose three weight columns")
        result.append([_number(value, f"prior weight[{index}][{column}]") for column, value in enumerate(values)])
    return result


def _constructor_station_rings(base: Mapping[str, Any], base_count: int,
                               expected_indices: set[int] | None = None) -> dict[str, list[list[int]]]:
    metadata = _mapping(base.get("metadata"), "base.metadata")
    chains = _mapping(metadata.get("chains"), "base.metadata.chains")
    if set(chains) != set(_SIDES):
        raise ValueError("base.metadata.chains must contain exactly left and right")
    result: dict[str, list[list[int]]] = {}
    all_indices: list[int] = []
    for side in _SIDES:
        chain = _mapping(chains[side], f"base.metadata.chains.{side}")
        sections = _sequence(chain.get("sections"), f"base.metadata.chains.{side}.sections")
        if len(sections) != len(_STATION_NAMES):
            raise ValueError(f"base.metadata.chains.{side}.sections must contain seven stations")
        side_rings = []
        for station_index, station_name in enumerate(_STATION_NAMES):
            section = _mapping(sections[station_index],
                               f"base.metadata.chains.{side}.sections[{station_index}]")
            if section.get("name") != station_name or section.get("order") != station_index:
                raise ValueError(f"constructor station order mismatch for {side}.{station_name}")
            ring = _sequence(section.get("indices"), f"constructor ring {side}.{station_name}")
            if (len(ring) != 8 or any(isinstance(index, bool) or not isinstance(index, int)
                                      for index in ring) or len(set(ring)) != 8):
                raise ValueError(f"constructor ring {side}.{station_name} must contain eight unique indices")
            checked = [int(index) for index in ring]
            if any(index < _OLD_ROOT_VERTEX_COUNT or index >= base_count for index in checked):
                raise ValueError(f"constructor ring {side}.{station_name} must reference appended vertices")
            side_rings.append(checked)
            all_indices.extend(checked)
        result[side] = side_rings
    expected = (set(range(_OLD_ROOT_VERTEX_COUNT, base_count))
                if expected_indices is None else expected_indices)
    if len(set(all_indices)) != len(all_indices) or set(all_indices) != expected:
        raise ValueError("constructor station rings must cover every appended vertex exactly once")
    return result


def _check_arm_source_frames(report: dict[str, Any], binding: Mapping[str, Any],
                             arm_contract: Mapping[str, Any],
                             tolerance: float) -> float:
    frames = _mapping(binding.get("rest_frames"), "binding.rest_frames")
    joints = _mapping(binding.get("joints"), "binding.joints")
    expected_parents = {
        "pelvis": None, "left_hip": "pelvis", "left_knee": "left_hip",
        "right_hip": "pelvis", "right_knee": "right_hip",
        "left_shoulder": "pelvis", "left_elbow": "left_shoulder",
        "right_shoulder": "pelvis", "right_elbow": "right_shoulder",
    }
    parents = binding.get("parents", binding.get("hierarchy"))
    if not isinstance(parents, Mapping) or {
        name: (None if parents.get(name) is None else str(parents.get(name)))
        for name in _ARM_JOINTS
    } != expected_parents:
        _error(report, "arm_parent_hierarchy",
               "9-column binding must declare the exact pelvis/shoulder/elbow parent hierarchy")
    source_error = 0.0
    for side in _SIDES:
        frame = _mapping(frames.get(side), f"binding.rest_frames.{side}")
        source = _mapping(frame.get("arm_source_points"),
                          f"binding.rest_frames.{side}.arm_source_points")
        expected = arm_contract["source_points"][side]
        for name in ("J", "E", "W"):
            actual = _vector(source.get(name),
                             f"binding.rest_frames.{side}.arm_source_points.{name}")
            source_error = max(source_error, _distance(actual, expected[name]))
        frame_source_ok = source.get("frame_source") == _ARM_FRAME_SOURCE
        report["checks"][f"{side}_arm_source_frame_declaration"] = frame_source_ok
        if not frame_source_ok:
            _error(report, "arm_source_frame_declaration",
                   "arm pivot frames must declare source J->E and E->W bones, excluding construction P frames",
                   side=side)
        shoulder = _mapping(frame.get("shoulder"),
                            f"binding.rest_frames.{side}.shoulder")
        elbow = _mapping(frame.get("elbow"),
                         f"binding.rest_frames.{side}.elbow")
        shoulder_matrix = _matrix(shoulder.get("rest_global", shoulder.get("rest_matrix")),
                                  f"binding.rest_frames.{side}.shoulder.rest_global")
        elbow_matrix = _matrix(elbow.get("rest_global", elbow.get("rest_matrix")),
                               f"binding.rest_frames.{side}.elbow.rest_global")
        expected_shoulder = _arm_source_frame(expected["J"], expected["E"],
                                               f"{side} shoulder")
        expected_elbow = _arm_source_frame(expected["E"], expected["W"],
                                            f"{side} elbow")
        expected_elbow_local = _mm(_inverse(expected_shoulder), expected_elbow)
        actual_elbow_local = _matrix(
            elbow.get("rest_local"),
            f"binding.rest_frames.{side}.elbow.rest_local",
        )
        source_error = max(source_error,
                           _matrix_error(shoulder_matrix, expected_shoulder),
                           _matrix_error(elbow_matrix, expected_elbow),
                           _matrix_error(actual_elbow_local, expected_elbow_local))
        for joint_name, expected_point, matrix in (
            (f"{side}_shoulder", expected["J"], shoulder_matrix),
            (f"{side}_elbow", expected["E"], elbow_matrix),
        ):
            joint = _mapping(joints.get(joint_name), f"binding.joints.{joint_name}")
            joint_matrix = _matrix(joint.get("rest_matrix"),
                                   f"binding.joints.{joint_name}.rest_matrix")
            source_error = max(source_error,
                               _matrix_error(
                                   joint_matrix,
                                   expected_shoulder if joint_name.endswith("shoulder")
                                   else expected_elbow,
                               ),
                               _matrix_error(
                                   _matrix(joint.get("inverse_bind_matrix", joint.get("inverse_bind")),
                                           f"binding.joints.{joint_name}.inverse_bind_matrix"),
                                   _inverse(expected_shoulder if joint_name.endswith("shoulder")
                                            else expected_elbow),
                               ),
                               max(abs(joint_matrix[row][3] - expected_point[row])
                                   for row in range(3)))
    report["metrics"]["arm_source_frame_max_error"] = source_error
    report["checks"]["arm_source_J_E_W_frames"] = source_error <= tolerance
    if source_error > tolerance:
        _error(report, "arm_source_frames",
               "arm rest frames and joint origins must be derived from source J/E/W")
    return source_error


def _check_arm_binding(report: dict[str, Any], base_parsed: Mapping[str, Any],
                       rest_parsed: Mapping[str, Any], binding: Mapping[str, Any],
                       prior_root_parsed: Mapping[str, Any],
                       prior_hip_binding: Mapping[str, Any],
                       leg_inputs: Mapping[str, Any],
                       protocol: Mapping[str, Any]) -> dict[str, Any]:
    base_value = base_parsed["value"]
    metadata = _mapping(base_value.get("metadata"), "base.metadata")
    occupied = set()
    chains = _mapping(metadata.get("chains"), "base.metadata.chains")
    for side in _SIDES:
        occupied.update(_sequence(_mapping(chains[side], f"base.metadata.chains.{side}")
                                  .get("new_vertex_indices"),
                                  f"base.metadata.chains.{side}.new_vertex_indices"))
    arm_contract = _arm_metadata_contract(base_value, len(base_parsed["vertices"]), occupied)
    arm_indices = set(arm_contract["all_indices"])
    head_present = "head" in metadata
    head_contract = (_head_metadata_contract(base_value, len(base_parsed["vertices"]), arm_indices)
                     if head_present else {"present": False, "all_indices": set()})
    head_indices = set(head_contract.get("all_indices", ()))
    weight_columns = _ARM_HEAD_WEIGHT_COLUMNS if head_present else _ARM_WEIGHT_COLUMNS
    foot_contract = _foot_metadata_contract(base_value, len(base_parsed["vertices"]),
                                            arm_indices | head_indices)
    foot_indices = foot_contract["indices"]
    expected_station_indices = (set(range(_OLD_ROOT_VERTEX_COUNT, len(base_parsed["vertices"])))
                                - arm_indices
                                - head_indices
                                - set(foot_contract.get("excluded_indices", ())))
    rings = _constructor_station_rings(base_value, len(base_parsed["vertices"]),
                                       expected_station_indices)
    prior_weights = _mapped_prior_weights(_mapping(prior_hip_binding, "prior_hip_binding"),
                                          _OLD_ROOT_VERTEX_COUNT)
    raw_base = binding.get("base_weights", binding.get("weights"))
    base_rows = _sequence(raw_base, "binding.base_weights")
    if len(base_rows) != len(base_parsed["vertices"]):
        raise ValueError("binding.base_weights must cover every L0 vertex")
    base_weights = []
    for index, row in enumerate(base_rows):
        values = _sequence(row, f"binding.base_weights[{index}]")
        if len(values) != len(weight_columns):
            raise ValueError("binding.base_weights has the wrong arm/head column count")
        base_weights.append([_number(value, f"base weight[{index}][{column}]")
                             for column, value in enumerate(values)])
    tolerance = _require_limit(report, protocol, (
        "weight_sum_max_abs_error", "weight_partition_tolerance", "binding_transfer_tolerance",
    ))
    if isinstance(tolerance, tuple):
        raise ValueError("binding tolerance must be scalar")
    for index, row in enumerate(base_weights):
        if any(value < -tolerance or value > 1.0 + tolerance for value in row):
            _error(report, "arm_weight_bounds", "arm/head base weights must remain in the declared numeric bounds", vertex=index)
        if abs(sum(row) - 1.0) > tolerance:
            _error(report, "arm_weight_partition", "9-column base weights must partition unity", vertex=index)

    bound = _mapping(binding, "binding")
    immutable_inputs = _mapping(leg_inputs, "leg_inputs")
    binding_inputs = _mapping(bound.get("leg_inputs"), "binding.leg_inputs")
    input_copy_matches = binding_inputs == immutable_inputs
    source_error, hierarchy_matches = _binding_source_error(bound, immutable_inputs)
    source_limit = _require_limit(report, protocol, (
        "rest_transform_max_abs_error", "binding_transfer_tolerance", "weight_partition_tolerance",
    ))
    if isinstance(source_limit, tuple):
        raise ValueError("binding source tolerance must be scalar")
    mapped = [int(value) for value in _sequence(bound.get("prior_column_map"), "prior_column_map")]
    root_vertex_prefix = (base_parsed["vertices"][:_OLD_ROOT_VERTEX_COUNT]
                          == prior_root_parsed["vertices"])
    fixed_column_map = tuple(mapped) == _FIXED_PRIOR_COLUMN_MAP
    arm_order_ok = tuple(bound.get("joint_order", ())) == (_ARM_HEAD_JOINTS if head_present else _ARM_JOINTS)
    arm_columns_ok = tuple(bound.get("weight_columns", ())) == weight_columns
    fields, blends, field_diagnostics = _arm_graph_fields(
        base_value, base_parsed["quads"], metadata["arms"],
        root_quads=prior_root_parsed["quads"]
    )
    expected_base = [[0.0] * len(weight_columns) for _ in base_weights]
    for index, old_row in enumerate(prior_weights):
        expected_base[index][0] = old_row[0]
        expected_base[index][1] = old_row[1]
        expected_base[index][3] = old_row[2]
    for side, upper_column in (("left", 5), ("right", 7)):
        for index, influence in fields[side].items():
            expected_base[index][:5] = [value * (1.0 - influence)
                                        for value in expected_base[index][:5]]
            expected_base[index][upper_column] = influence
    for side, upper_column, fore_column in (("left", 5, 6), ("right", 7, 8)):
        for index, blend in blends[side].items():
            expected_base[index][upper_column] = 1.0 - blend
            expected_base[index][fore_column] = blend
    for side, thigh_column, shank_column in (("left", 1, 2), ("right", 3, 4)):
        for station_index, ring in enumerate(rings[side]):
            shank = _STATION_SHANK_WEIGHTS[station_index]
            for index in ring:
                expected_base[index][thigh_column] = 1.0 - shank
                expected_base[index][shank_column] = shank
    for side, shank_column in (("left", 2), ("right", 4)):
        for index in foot_indices[side]:
            expected_base[index][shank_column] = 1.0
    head_field: dict[int, float] = {}
    head_diagnostics: dict[str, Any] = {}
    if head_present:
        head_field, head_diagnostics = _head_graph_field(
            base_value, base_parsed["quads"], head_contract,
            root_quads=prior_root_parsed["quads"]
        )
        for index, influence in head_field.items():
            expected_base[index][:9] = [value * (1.0 - influence)
                                         for value in expected_base[index][:9]]
            expected_base[index][9] = influence
        for index in head_indices:
            expected_base[index] = [0.0] * 9 + [1.0]
    tail_contract = _tail_metadata_contract(base_value, len(base_weights))
    if tail_contract["present"]:
        expected_base_rows = _tail_expected_base_rows(
            expected_base, tail_contract, weight_columns
        )
        for index, row in expected_base_rows.items():
            expected_base[index] = row
    base_error = max((abs(base_weights[index][column] - expected_base[index][column])
                      for index in range(len(base_weights))
                      for column in range(len(weight_columns))), default=math.inf)
    arm_field_error = max(
        (abs(base_weights[index][upper_column] - influence)
         for side, upper_column in (("left", 5), ("right", 7))
         for index, influence in fields[side].items()),
        default=math.inf,
    )
    modified = set(fields["left"]) | set(fields["right"])
    if head_present and (set(head_field) & modified):
        raise ValueError("head D0/D1 field overlaps an arm-modified root region")
    if head_present:
        modified.update(head_field)
    prior_ratio_error = max(
        (abs(base_weights[index][new_column] -
             prior_weights[index][old_column] * (1.0 - fields[side][index]))
         for side, upper_column in (("left", 5), ("right", 7))
         for index in fields[side]
         for old_column, new_column in zip(range(3), _FIXED_PRIOR_COLUMN_MAP)),
        default=math.inf,
    )
    far_error = max((abs(base_weights[index][column] - expected_base[index][column])
                     for index in range(_OLD_ROOT_VERTEX_COUNT) if index not in modified
                     for column in range(5)), default=0.0)
    arm_source_error = _check_arm_source_frames(report, bound, arm_contract, source_limit)
    head_source_error = (_head_source_frame_error(report, bound, head_contract, source_limit)
                         if head_present else 0.0)
    stencils = _stencil_rows(rest_parsed["stencils"], len(rest_parsed["vertices"]),
                             len(base_weights), "rest.base_stencils", tolerance)
    evaluated = _sequence(bound.get("evaluated_weights", bound.get("weights")),
                          "binding.evaluated_weights")
    if len(evaluated) != len(rest_parsed["vertices"]):
        raise ValueError("binding.evaluated_weights must cover every L2 vertex")
    transfer_error = 0.0
    for vertex_index, row in enumerate(evaluated):
        actual = [_number(value, f"evaluated weight[{vertex_index}][{column}]")
                  for column, value in enumerate(_sequence(row, f"evaluated weight[{vertex_index}]"))]
        if len(actual) != len(weight_columns):
            raise ValueError("binding.evaluated_weights has the wrong arm/head column count")
        expected = [sum(coefficient * expected_base[base_index][column]
                        for base_index, coefficient in stencils[vertex_index])
                    for column in range(len(weight_columns))]
        transfer_error = max(transfer_error,
                             max(abs(actual[column] - expected[column])
                                 for column in range(len(weight_columns)))
                             )
    endpoint_error = max((abs(base_weights[index][column] - expected_base[index][column])
                          for side in _SIDES for index, _blend in blends[side].items()
                          for column in range(len(weight_columns))), default=math.inf)
    arm_checks = {
        "declared_nine_weight_columns": arm_columns_ok,
        "declared_nine_joint_hierarchy": arm_order_ok and hierarchy_matches,
        "declared_ten_weight_columns": (not head_present) or arm_columns_ok,
        "declared_ten_joint_hierarchy": (not head_present) or (arm_order_ok and hierarchy_matches),
        "arm_source_J_E_W_frames": arm_source_error <= source_limit,
        "arm_D0_D1_harmonic_shoulder": arm_field_error <= tolerance,
        "arm_station_and_elbow_endpoint_weights": endpoint_error <= tolerance,
        "arm_prior_ratios_and_far_rows": max(prior_ratio_error, far_error) <= tolerance,
        "actual_l2_full_stencil_transfer": transfer_error <= tolerance,
        "terminal_foot_full_l2_stencil_transfer": (not foot_contract["present"] or transfer_error <= tolerance),
        "binding_leg_inputs_match_immutable_inputs": input_copy_matches,
        "binding_rest_sources_match_J_K_A": hierarchy_matches and source_error <= source_limit,
    }
    if head_present:
        arm_checks.update({
            "head_source_pivot_frame": head_source_error <= source_limit,
            "head_D0_D1_harmonic_transition": max(
                (abs(base_weights[index][9] - value) for index, value in head_field.items()),
                default=math.inf,
            ) <= tolerance,
            "head_new_vertices_neck_onehot": all(
                abs(base_weights[index][9] - 1.0) <= tolerance
                and max(abs(value) for value in base_weights[index][:9]) <= tolerance
                for index in head_indices
            ),
            "head_prior_ratios_and_far_rows": max(
                (abs(base_weights[index][column]
                    - prior_weights[index][old_column] * (1.0 - head_field[index]))
                 for index in head_field
                 for old_column, column in zip(range(3), _FIXED_PRIOR_COLUMN_MAP)),
                default=math.inf,
            ) <= tolerance and far_error <= tolerance,
        })
    report["checks"].update(arm_checks)
    report["metrics"].update({
        "arm_graph": field_diagnostics,
        "head_graph": head_diagnostics,
        "arm_base_weight_max_error": base_error,
        "arm_harmonic_field_max_error": arm_field_error,
        "arm_far_root_weight_max_error": far_error,
        "arm_modified_prior_ratio_max_error": prior_ratio_error,
        "arm_endpoint_weight_max_error": endpoint_error,
        "l2_full_stencil_max_error": transfer_error,
        "prior_column_map": mapped,
    })
    failures = {
        "declared_nine_weight_columns": "binding weight columns do not match the exact nine-column arm contract",
        "declared_nine_joint_hierarchy": "binding joint order or parent hierarchy does not match the exact nine-joint contract",
        "arm_D0_D1_harmonic_shoulder": "arm root D0/D1 weights do not match the independent collar=1/D2=0 harmonic field",
        "arm_station_and_elbow_endpoint_weights": "arm station or elbow endpoint weights do not match the declared section anchors",
        "arm_prior_ratios_and_far_rows": "prior root weight ratios or far unchanged rows drifted",
        "actual_l2_full_stencil_transfer": "evaluated 9-column weights do not equal complete rest stencil transfer",
    }
    if head_present:
        failures.update({
            "declared_ten_weight_columns": "binding weight columns do not match the exact ten-column arm/head contract",
            "declared_ten_joint_hierarchy": "binding joint order or parent hierarchy does not match the exact ten-joint contract",
            "head_source_pivot_frame": "neck rest and inverse-bind matrices do not match the source pivot handoff",
            "head_D0_D1_harmonic_transition": "neck root D0/D1 weights do not match the independent harmonic transition",
            "head_new_vertices_neck_onehot": "head allocation must be one-hot to the neck joint",
            "head_prior_ratios_and_far_rows": "neck transition changed prior root ratios or far rows unexpectedly",
        })
    for name, detail in failures.items():
        if not arm_checks[name]:
            _error(report, name, detail)
    if not input_copy_matches:
        _error(report, "binding_leg_inputs", "binding leg_inputs do not match immutable case inputs")
    if not hierarchy_matches or source_error > source_limit:
        _error(report, "binding_rest_sources", "binding leg rest frames do not match immutable J/K/A inputs")
    return report


def _check_head_binding(report: dict[str, Any], base_parsed: Mapping[str, Any],
                        rest_parsed: Mapping[str, Any], binding: Mapping[str, Any],
                        prior_root_parsed: Mapping[str, Any],
                        prior_hip_binding: Mapping[str, Any],
                        leg_inputs: Mapping[str, Any],
                        protocol: Mapping[str, Any]) -> dict[str, Any]:
    """Check the six-column neck/head transition independently of binder pose code."""
    base_value = base_parsed["value"]
    metadata = _mapping(base_value.get("metadata"), "base.metadata")
    chains = _mapping(metadata.get("chains"), "base.metadata.chains")
    occupied: set[int] = set()
    for side in _SIDES:
        occupied.update(_sequence(_mapping(chains[side], f"base.metadata.chains.{side}")
                                  .get("new_vertex_indices"),
                                  f"base.metadata.chains.{side}.new_vertex_indices"))
    head_contract = _head_metadata_contract(base_value, len(base_parsed["vertices"]), occupied)
    if not head_contract["present"]:
        raise ValueError("six-column binding requires base.metadata.head.binding_handoff")
    head_indices = set(head_contract["all_indices"])
    foot_contract = _foot_metadata_contract(base_value, len(base_parsed["vertices"]), head_indices)
    foot_indices = foot_contract["indices"]
    expected_station_indices = (set(range(_OLD_ROOT_VERTEX_COUNT, len(base_parsed["vertices"])))
                                - head_indices
                                - set(foot_contract.get("excluded_indices", ())))
    rings = _constructor_station_rings(base_value, len(base_parsed["vertices"]),
                                       expected_station_indices)
    prior_weights = _mapped_prior_weights(_mapping(prior_hip_binding, "prior_hip_binding"),
                                          _OLD_ROOT_VERTEX_COUNT)
    raw_base = binding.get("base_weights", binding.get("weights"))
    base_rows = _sequence(raw_base, "binding.base_weights")
    if len(base_rows) != len(base_parsed["vertices"]):
        raise ValueError("binding.base_weights must cover every L0 vertex")
    base_weights: list[list[float]] = []
    for index, row in enumerate(base_rows):
        values = _sequence(row, f"binding.base_weights[{index}]")
        if len(values) != len(_HEAD_WEIGHT_COLUMNS):
            raise ValueError("6-column binding.base_weights must have pelvis/thigh/shank/neck columns")
        base_weights.append([_number(value, f"base weight[{index}][{column}]")
                             for column, value in enumerate(values)])
    tolerance = _require_limit(report, protocol, (
        "weight_sum_max_abs_error", "weight_partition_tolerance", "binding_transfer_tolerance",
    ))
    if isinstance(tolerance, tuple):
        raise ValueError("binding tolerance must be scalar")
    bound = _mapping(binding, "binding")
    immutable_inputs = _mapping(leg_inputs, "leg_inputs")
    input_copy_matches = _mapping(bound.get("leg_inputs"), "binding.leg_inputs") == immutable_inputs
    source_error, hierarchy_matches = _binding_source_error(bound, immutable_inputs)
    source_limit = _require_limit(report, protocol, (
        "rest_transform_max_abs_error", "binding_transfer_tolerance",
        "weight_partition_tolerance",
    ))
    if isinstance(source_limit, tuple):
        raise ValueError("binding source tolerance must be scalar")
    mapped = [int(value) for value in _sequence(bound.get("prior_column_map"), "prior_column_map")]
    root_vertex_prefix = (base_parsed["vertices"][:_OLD_ROOT_VERTEX_COUNT]
                          == prior_root_parsed["vertices"])
    fixed_column_map = tuple(mapped) == _FIXED_PRIOR_COLUMN_MAP
    station_values = _source_station_values(bound, immutable_inputs)
    station_declaration_ok = (station_values is not None and
                              [float(value) for value in _sequence(
                                  station_values, "source station knee values")]
                              == list(_STATION_SHANK_WEIGHTS))
    order_ok = tuple(bound.get("joint_order", ())) == _HEAD_JOINTS
    columns_ok = tuple(bound.get("weight_columns", ())) == _HEAD_WEIGHT_COLUMNS
    head_field, head_diagnostics = _head_graph_field(
        base_value, base_parsed["quads"], head_contract,
        root_quads=prior_root_parsed["quads"]
    )
    expected_base = [[0.0] * len(_HEAD_WEIGHT_COLUMNS) for _ in base_weights]
    for index, old_row in enumerate(prior_weights):
        expected_base[index][0] = old_row[0]
        expected_base[index][1] = old_row[1]
        expected_base[index][3] = old_row[2]
    for side, thigh_column, shank_column in (("left", 1, 2), ("right", 3, 4)):
        for station_index, ring in enumerate(rings[side]):
            shank = _STATION_SHANK_WEIGHTS[station_index]
            for index in ring:
                expected_base[index][thigh_column] = 1.0 - shank
                expected_base[index][shank_column] = shank
    for side, shank_column in (("left", 2), ("right", 4)):
        for index in foot_indices[side]:
            expected_base[index][shank_column] = 1.0
    for index, influence in head_field.items():
        expected_base[index][:5] = [value * (1.0 - influence)
                                    for value in expected_base[index][:5]]
        expected_base[index][5] = influence
    for index in head_indices:
        expected_base[index] = [0.0] * 5 + [1.0]
    tail_contract = _tail_metadata_contract(base_value, len(base_weights))
    if tail_contract["present"]:
        expected_base_rows = _tail_expected_base_rows(
            expected_base, tail_contract, _HEAD_WEIGHT_COLUMNS
        )
        for index, row in expected_base_rows.items():
            expected_base[index] = row
    base_error = max((abs(base_weights[index][column] - expected_base[index][column])
                      for index in range(len(base_weights))
                      for column in range(len(_HEAD_WEIGHT_COLUMNS))), default=math.inf)
    field_error = max((abs(base_weights[index][5] - influence)
                       for index, influence in head_field.items()), default=math.inf)
    modified = set(head_field)
    prior_ratio_error = max((abs(base_weights[index][column]
                                 - prior_weights[index][old_column] * (1.0 - head_field[index]))
                             for index in head_field
                             for old_column, column in zip(range(3), _FIXED_PRIOR_COLUMN_MAP)),
                            default=math.inf)
    far_error = max((abs(base_weights[index][column] - expected_base[index][column])
                     for index in range(_OLD_ROOT_VERTEX_COUNT) if index not in modified
                     for column in range(5)), default=0.0)
    source_frame_error = _head_source_frame_error(report, bound, head_contract, source_limit)
    stencils = _stencil_rows(rest_parsed["stencils"], len(rest_parsed["vertices"]),
                             len(base_weights), "rest.base_stencils", tolerance)
    evaluated = _sequence(bound.get("evaluated_weights", bound.get("weights")),
                           "binding.evaluated_weights")
    if len(evaluated) != len(rest_parsed["vertices"]):
        raise ValueError("binding.evaluated_weights must cover every L2 vertex")
    transfer_error = 0.0
    for vertex_index, row in enumerate(evaluated):
        actual = [_number(value, f"evaluated weight[{vertex_index}][{column}]")
                  for column, value in enumerate(_sequence(row, f"binding.evaluated_weights[{vertex_index}]"))]
        if len(actual) != len(_HEAD_WEIGHT_COLUMNS):
            raise ValueError("binding.evaluated_weights must have six columns")
        expected = [sum(coefficient * expected_base[base_index][column]
                        for base_index, coefficient in stencils[vertex_index])
                    for column in range(len(_HEAD_WEIGHT_COLUMNS))]
        transfer_error = max(transfer_error,
                             max(abs(actual[column] - expected[column])
                                 for column in range(len(_HEAD_WEIGHT_COLUMNS))))
    report["checks"].update({
        "declared_six_weight_columns": columns_ok,
        "declared_six_joint_hierarchy": order_ok and hierarchy_matches,
        "declared_source_station_knee": station_declaration_ok,
        "head_source_pivot_frame": source_frame_error <= source_limit,
        "head_D0_D1_harmonic_transition": field_error <= tolerance,
        "head_new_vertices_neck_onehot": all(
            abs(base_weights[index][5] - 1.0) <= tolerance and
            max(abs(value) for value in base_weights[index][:5]) <= tolerance
            for index in head_indices
        ),
        "head_prior_ratios_and_far_rows": max(prior_ratio_error, far_error) <= tolerance,
        "original_root_152x3_mapped_to_six_columns": root_vertex_prefix and fixed_column_map,
        "actual_l2_full_stencil_transfer": transfer_error <= tolerance,
        "binding_leg_inputs_match_immutable_inputs": input_copy_matches,
        "binding_rest_sources_match_J_K_A": hierarchy_matches and source_error <= source_limit,
    })
    report["metrics"].update({
        "head_graph": head_diagnostics,
        "head_base_weight_max_error": base_error,
        "head_harmonic_field_max_error": field_error,
        "head_modified_prior_ratio_max_error": prior_ratio_error,
        "head_far_root_weight_max_error": far_error,
        "head_l2_full_stencil_max_error": transfer_error,
        "prior_column_map": mapped,
        "original_root_vertex_prefix": root_vertex_prefix,
        "source_station_knee": station_values,
    })
    failures = {
        "declared_six_weight_columns": "binding weight columns do not match the exact six-column neck/head contract",
        "declared_six_joint_hierarchy": "binding joint order or parent hierarchy does not match the exact six-joint contract",
        "declared_source_station_knee": "declared base source-station knee values must equal [0,0,.5,1,1,1,1]",
        "head_D0_D1_harmonic_transition": "neck root D0/D1 weights do not match the independent support=1/D2=0 harmonic field",
        "head_new_vertices_neck_onehot": "head allocation must be one-hot to the neck joint",
        "head_prior_ratios_and_far_rows": "head transition changed prior root ratios or far rows unexpectedly",
        "original_root_152x3_mapped_to_six_columns": "the expanded L0 does not preserve the prior 152x3 root mapping",
        "actual_l2_full_stencil_transfer": "evaluated six-column weights do not equal complete rest stencil transfer",
    }
    for name, detail in failures.items():
        if not report["checks"][name]:
            _error(report, name, detail)
    if not input_copy_matches:
        _error(report, "binding_leg_inputs", "binding leg_inputs do not match immutable case inputs")
    if not hierarchy_matches or source_error > source_limit:
        _error(report, "binding_rest_sources", "binding leg rest frames or inverse binds do not match immutable J/K/A inputs")
    return report


def _check_tail_binding(report: dict[str, Any], base_parsed: Mapping[str, Any],
                        rest_parsed: Mapping[str, Any], binding: Mapping[str, Any],
                        prior_root_parsed: Mapping[str, Any],
                        tail_contract: Mapping[str, Any], protocol: Mapping[str, Any]) -> None:
    """Check the local host replacement and pelvis-only tail weight handoff."""
    try:
        base_value = base_parsed["value"]
        bound = _mapping(binding, "binding")
        prior_quads = prior_root_parsed["quads"]
        base_quads = base_parsed["quads"]
        host_face = int(tail_contract["host_face"])
        host_vertices = list(tail_contract["host_vertices"])
        kept_exact = all(
            0 <= old_index < len(prior_quads) and 0 <= new_index < len(base_quads)
            and base_quads[new_index] == prior_quads[old_index]
            for old_index, new_index in tail_contract["kept_faces"]
        )
        replacement_faces = list(tail_contract["replacement_faces"])
        replacement_slots_valid = all(0 <= index < len(base_quads)
                                      for index in replacement_faces)
        host_identity = (0 <= host_face < len(prior_quads)
                         and list(prior_quads[host_face]) == host_vertices)
        host_replaced = (host_identity and 0 <= host_face < len(base_quads)
                         and list(base_quads[host_face]) != host_vertices)

        raw_columns = _sequence(bound.get("weight_columns"), "binding.weight_columns")
        columns = [str(column) for column in raw_columns]
        pelvis_column = columns.index("pelvis") if "pelvis" in columns else -1
        raw_base = binding.get("base_weights", binding.get("weights"))
        base_rows = _sequence(raw_base, "binding.base_weights")
        if len(base_rows) != len(base_parsed["vertices"]):
            raise ValueError("binding.base_weights must cover every tail L0 vertex")
        base_weights = []
        for index, row in enumerate(base_rows):
            values = _sequence(row, f"binding.base_weights[{index}]")
            if len(values) != len(columns):
                raise ValueError("tail binding base weights disagree with weight_columns")
            base_weights.append([_number(value, f"tail base weight[{index}][{column}]")
                                 for column, value in enumerate(values)])
        tolerance = _require_limit(report, protocol, (
            "weight_sum_max_abs_error", "weight_partition_tolerance", "binding_transfer_tolerance",
        ))
        if isinstance(tolerance, tuple):
            raise ValueError("tail binding tolerance must be scalar")

        fractions = {
            vertex_index: float(fraction)
            for ring, fraction in zip(tail_contract["rings"], tail_contract["station_fractions"])
            for vertex_index in ring
        }
        l0_error = 0.0
        l0_partition = True
        expected_rows = _tail_expected_base_rows(base_weights, tail_contract, columns)
        for vertex_index in tail_contract["new_vertex_indices"]:
            expected = expected_rows[vertex_index]
            l0_error = max(l0_error,
                           max((abs(base_weights[vertex_index][column] - expected[column])
                                for column in range(len(columns))), default=math.inf))
            l0_partition = l0_partition and abs(sum(base_weights[vertex_index]) - 1.0) <= tolerance

        weighting = bound.get("tail_weighting")
        weighting_contract = _mapping(_mapping(bound.get("metadata", {}), "binding.metadata")
                                      .get("tail_weighting_contract", {}),
                                      "binding.metadata.tail_weighting_contract")
        declared_control = (
            weighting_contract.get("host_face") == host_face
            and weighting_contract.get("host_vertex_indices") == host_vertices
            and weighting_contract.get("kept_root_face_correspondence") == tail_contract["kept_faces"]
            and weighting_contract.get("replacement_face_indices") == replacement_faces
            and weighting_contract.get("collar_blend_strength") == tail_contract["collar_blend_strength"]
            and weighting_contract.get("distal_target_joint") == "pelvis"
            and weighting_contract.get("tail_joint") == "not_present"
        )
        weighting_vertices = _mapping(weighting, "binding.tail_weighting").get("vertices", {})
        supports_match = True
        for vertex_index in tail_contract["new_vertex_indices"]:
            row = weighting_vertices.get(str(vertex_index))
            support = tail_contract["supports"][vertex_index]
            supports_match = supports_match and isinstance(row, Mapping) and (
                row.get("host_vertex_indices") == support["host_vertex_indices"]
                and row.get("convex_weights") == support["convex_weights"]
                and row.get("ring_fraction") == fractions[vertex_index]
            )

        stencils = _stencil_rows(rest_parsed["stencils"], len(rest_parsed["vertices"]),
                                 len(base_weights), "rest.base_stencils", tolerance)
        evaluated = _sequence(bound.get("evaluated_weights", bound.get("weights")),
                              "binding.evaluated_weights")
        if len(evaluated) != len(rest_parsed["vertices"]):
            raise ValueError("binding.evaluated_weights must cover every tail L2 vertex")
        tail_l2_rows = [index for index, row in enumerate(stencils)
                        if any(base_index in fractions for base_index, _coefficient in row)]
        l2_error = 0.0
        for vertex_index in tail_l2_rows:
            actual = [_number(value, f"tail evaluated weight[{vertex_index}][{column}]")
                      for column, value in enumerate(_sequence(
                          evaluated[vertex_index], f"binding.evaluated_weights[{vertex_index}]"))]
            if len(actual) != len(columns):
                raise ValueError("tail evaluated weights disagree with weight_columns")
            expected = [sum(coefficient * expected_rows[base_index][column]
                            if base_index in expected_rows else
                            coefficient * base_weights[base_index][column]
                            for base_index, coefficient in stencils[vertex_index])
                        for column in range(len(columns))]
            l2_error = max(l2_error,
                           max((abs(actual[column] - expected[column])
                                for column in range(len(columns))), default=math.inf))

        checks = {
            "tail_host_face_identity": host_identity,
            "tail_kept_root_faces_exact": kept_exact,
            "tail_host_face_replaced": host_replaced and replacement_slots_valid,
            "tail_binding_control_explicit": declared_control,
            "tail_corner_supports": supports_match,
            "tail_l0_weight_formula": pelvis_column >= 0 and l0_error <= tolerance,
            "tail_weight_partition": l0_partition,
            "tail_l2_full_stencil_transfer": bool(tail_l2_rows) and l2_error <= tolerance,
        }
        report["checks"].update(checks)
        report["metrics"].update({
            "tail_host_face": host_face,
            "tail_host_vertices": host_vertices,
            "tail_replacement_faces": replacement_faces,
            "tail_new_vertex_count": len(tail_contract["new_vertex_indices"]),
            "tail_l0_weight_max_error": l0_error,
            "tail_l2_row_count": len(tail_l2_rows),
            "tail_l2_weight_max_error": l2_error,
            "tail_collar_blend_strength": tail_contract["collar_blend_strength"],
            "tail_support_rule": ".55 own retained corner/.15 other retained corners",
        })
        failures = {
            "tail_host_face_identity": "tail host identity does not match the supplied original root",
            "tail_kept_root_faces_exact": "a non-host root face changed despite the explicit kept-face mapping",
            "tail_host_face_replaced": "tail host slot is not the declared one-to-many replacement",
            "tail_binding_control_explicit": "binding metadata does not repeat the explicit pelvis-only tail control",
            "tail_corner_supports": "tail binding did not retain the declared .55/.15 corner supports",
            "tail_l0_weight_formula": "tail L0 weights do not match collar blend plus pelvis transition",
            "tail_weight_partition": "tail L0 weights do not partition unity",
            "tail_l2_full_stencil_transfer": "tail L2 rows do not equal complete rest-stencil weight transfer",
        }
        for name, detail in failures.items():
            if not checks[name]:
                _error(report, name, detail)
    except Exception as exc:
        _error(report, "tail_binding_check_failure", str(exc))


def check_binding(base: Mapping[str, Any], rest: Mapping[str, Any], binding: Mapping[str, Any],
                  prior_root: Mapping[str, Any], prior_hip_binding: Mapping[str, Any],
                  leg_inputs: Mapping[str, Any], protocol: Mapping[str, Any]) -> dict[str, Any]:
    """Check the supported 5/6/9/10-column mapping and full L2 transfer independently."""
    report = _report("creature-kernel.connected-leg-assembly-binding-checks.v1")
    try:
        base_parsed = _mesh(base, "base")
        rest_parsed = _mesh(rest, "rest")
        prior_root_parsed = _mesh(prior_root, "prior_root")
        if len(prior_root_parsed["vertices"]) != _OLD_ROOT_VERTEX_COUNT:
            raise ValueError("prior root must preserve exactly 152 vertices")
        tail_contract = _tail_metadata_contract(base_parsed["value"],
                                                len(base_parsed["vertices"]))
        base_metadata = base_parsed["value"].get("metadata", {})
        if isinstance(base_metadata, Mapping) and "arms" in base_metadata:
            _check_arm_binding(
                report, base_parsed, rest_parsed, binding,
                prior_root_parsed, prior_hip_binding, leg_inputs, protocol
            )
            if tail_contract["present"]:
                _check_tail_binding(report, base_parsed, rest_parsed, binding,
                                    prior_root_parsed, tail_contract, protocol)
            return _finish(report)
        if isinstance(base_metadata, Mapping) and "head" in base_metadata:
            _check_head_binding(
                report, base_parsed, rest_parsed, binding,
                prior_root_parsed, prior_hip_binding, leg_inputs, protocol
            )
            if tail_contract["present"]:
                _check_tail_binding(report, base_parsed, rest_parsed, binding,
                                    prior_root_parsed, tail_contract, protocol)
            return _finish(report)
        root_vertex_prefix = base_parsed["vertices"][:_OLD_ROOT_VERTEX_COUNT] == prior_root_parsed["vertices"]
        if len(base_parsed["vertices"]) < _OLD_ROOT_VERTEX_COUNT:
            root_vertex_prefix = False
        prior_weights = _mapped_prior_weights(_mapping(prior_hip_binding, "prior_hip_binding"), _OLD_ROOT_VERTEX_COUNT)
        raw_base = binding.get("base_weights", binding.get("weights"))
        base_rows = _sequence(raw_base, "binding.base_weights")
        if len(base_rows) != len(base_parsed["vertices"]):
            raise ValueError("binding.base_weights must cover every L0 vertex")
        base_weights = []
        for index, row in enumerate(base_rows):
            values = _sequence(row, f"binding.base_weights[{index}]")
            if len(values) != 5:
                raise ValueError("binding.base_weights must have five columns")
            base_weights.append([_number(value, f"base weight[{index}][{column}]") for column, value in enumerate(values)])
        tolerance = _require_limit(report, protocol, (
            "weight_sum_max_abs_error", "weight_partition_tolerance", "binding_transfer_tolerance",
        ))
        if isinstance(tolerance, tuple):
            raise ValueError("binding tolerance must be scalar")

        bound = _mapping(binding, "binding")
        immutable_inputs = _mapping(leg_inputs, "leg_inputs")
        binding_inputs = _mapping(bound.get("leg_inputs"), "binding.leg_inputs")
        input_copy_matches = binding_inputs == immutable_inputs
        source_error, hierarchy_matches = _binding_source_error(bound, immutable_inputs)
        source_limit = _require_limit(report, protocol, (
            "rest_transform_max_abs_error", "binding_transfer_tolerance",
            "weight_partition_tolerance",
        ))
        if isinstance(source_limit, tuple):
            raise ValueError("binding source tolerance must be scalar")

        station_values = _source_station_values(bound, immutable_inputs)
        station_declaration_ok = (station_values is not None and
                                  [float(value) for value in _sequence(
                                      station_values, "source station knee values")]
                                  == list(_STATION_SHANK_WEIGHTS))
        mapped = [int(value) for value in _sequence(
            bound.get("prior_column_map"), "prior_column_map")]
        fixed_column_map = tuple(mapped) == _FIXED_PRIOR_COLUMN_MAP
        fixed_weight_columns = tuple(bound.get("weight_columns", ())) == _WEIGHT_COLUMNS
        foot_contract = _foot_metadata_contract(base_parsed["value"], len(base_weights))
        foot_present = bool(foot_contract["present"])
        foot_indices = foot_contract["indices"]
        expected_station_indices = set(range(_OLD_ROOT_VERTEX_COUNT, len(base_weights)))
        expected_station_indices -= set(foot_contract.get("excluded_indices", ()))
        rings = _constructor_station_rings(base_parsed["value"], len(base_weights),
                                           expected_station_indices)
        foot_declaration_ok = True
        if foot_present:
            expected_foot_declaration = {
                side: list(foot_indices[side]) for side in _SIDES
            }
            binding_metadata = _mapping(bound.get("metadata", {}), "binding.metadata")
            foot_declaration_ok = (
                bound.get("foot_vertex_indices") == expected_foot_declaration
                and binding_metadata.get("foot_vertex_indices") == expected_foot_declaration
            )
        expected_base = [[0.0] * 5 for _ in base_weights]
        for index, old_row in enumerate(prior_weights):
            for old_index, new_index in enumerate(_FIXED_PRIOR_COLUMN_MAP):
                expected_base[index][new_index] = old_row[old_index]
        for side, thigh_column, shank_column in (
            ("left", 1, 2), ("right", 3, 4),
        ):
            for station_index, ring in enumerate(rings[side]):
                shank = _STATION_SHANK_WEIGHTS[station_index]
                for vertex_index in ring:
                    expected_base[vertex_index][thigh_column] = 1.0 - shank
                    expected_base[vertex_index][shank_column] = shank
        for side, shank_column in (("left", 2), ("right", 4)):
            for vertex_index in foot_indices[side]:
                expected_base[vertex_index][shank_column] = 1.0
        if tail_contract["present"]:
            for ring, fraction in zip(tail_contract["rings"], tail_contract["station_fractions"]):
                pelvis_fraction = (tail_contract["collar_blend_strength"]
                                   + (1.0 - tail_contract["collar_blend_strength"]) * fraction)
                for vertex_index in ring:
                    support = tail_contract["supports"][vertex_index]
                    host_support = [0.0] * 5
                    for host_index, coefficient in zip(support["host_vertex_indices"],
                                                       support["convex_weights"]):
                        for column in range(5):
                            host_support[column] += coefficient * expected_base[host_index][column]
                    expected_base[vertex_index] = [
                        (1.0 - pelvis_fraction) * value for value in host_support
                    ]
                    expected_base[vertex_index][0] += pelvis_fraction
        base_error = max(
            (abs(base_weights[index][column] - expected_base[index][column])
             for index in range(len(base_weights)) for column in range(5)),
            default=math.inf,
        )
        prior_mapping_ok = root_vertex_prefix and fixed_column_map and base_error <= tolerance
        station_weight_error = max(
            (abs(base_weights[index][column] - expected_base[index][column])
             for side in _SIDES for ring in rings[side] for index in ring
             for column in range(5)),
            default=math.inf,
        )
        station_weights_ok = station_declaration_ok and station_weight_error <= tolerance
        foot_weight_error = max(
            (abs(base_weights[index][column] - expected_base[index][column])
             for side in _SIDES for index in foot_indices[side]
             for column in range(5)),
            default=0.0,
        )
        foot_weights_ok = (not foot_present or
                           foot_declaration_ok and foot_weight_error <= tolerance)

        stencils = _stencil_rows(rest_parsed["stencils"], len(rest_parsed["vertices"]),
                                 len(base_weights), "rest.base_stencils", tolerance)
        evaluated = _sequence(binding.get("evaluated_weights", binding.get("weights")), "binding.evaluated_weights")
        if len(evaluated) != len(rest_parsed["vertices"]):
            raise ValueError("binding.evaluated_weights must cover every L2 vertex")
        transfer_error = 0.0
        transfer_ok = True
        for vertex_index, row in enumerate(evaluated):
            actual = [_number(value, f"evaluated weight[{vertex_index}][{column}]") for column, value in enumerate(_sequence(row, f"binding.evaluated_weights[{vertex_index}]"))]
            if len(actual) != 5:
                raise ValueError("binding.evaluated_weights must have five columns")
            expected = [sum(coefficient * expected_base[base_index][column] for base_index, coefficient in stencils[vertex_index])
                        for column in range(5)]
            transfer_error = max(transfer_error, max(abs(actual[column] - expected[column]) for column in range(5)))
        transfer_ok = transfer_error <= tolerance
        report["checks"].update({
            "declared_source_station_knee": station_declaration_ok,
            "declared_five_weight_columns": fixed_weight_columns,
            "original_root_vertices_preserved": root_vertex_prefix,
            "original_root_152x3_mapped_to_five_columns": prior_mapping_ok,
            "constructor_station_base_weights": station_weights_ok,
            "actual_l2_full_stencil_transfer": transfer_ok,
            "terminal_foot_metadata_and_shank_weights": foot_weights_ok,
            "terminal_foot_full_l2_stencil_transfer": (not foot_present or transfer_ok),
            "binding_leg_inputs_match_immutable_inputs": input_copy_matches,
            "binding_rest_sources_match_J_K_A": hierarchy_matches and source_error <= source_limit,
        })
        report["metrics"].update({"source_station_knee": station_values,
                                  "base_weight_max_error": base_error,
                                  "station_base_weight_max_error": station_weight_error,
                                  "terminal_foot_base_weight_max_error": foot_weight_error,
                                  "original_root_vertex_prefix": root_vertex_prefix,
                                  "l2_full_stencil_max_error": transfer_error,
                                  "prior_column_map": mapped,
                                  "binding_rest_source_max_error": source_error})
        if not station_declaration_ok:
            _error(report, "source_station_knee_values", "declared base source-station knee values must equal [0,0,.5,1,1,1,1]")
        if not fixed_weight_columns:
            _error(report, "weight_columns", "binding weight columns do not match pelvis/thigh/shank positional semantics")
        if not root_vertex_prefix:
            _error(report, "root_vertex_prefix", "the expanded L0 must preserve the original 152 root vertices")
        if not prior_mapping_ok:
            _error(report, "prior_root_mapping", "the preserved 152x3 prior binding does not map exactly into the five-column base field")
        if not station_weights_ok:
            _error(report, "station_base_weights", "constructor station rings do not carry the independently expected five-column base weights")
        if not transfer_ok:
            _error(report, "l2_stencil_transfer", "evaluated weights do not equal the full rest stencil transfer")
        if not foot_weights_ok:
            _error(report, "terminal_foot_weights",
                   "terminal foot L0 allocations must be declared in binding metadata and be shank one-hot")
        if foot_present and not transfer_ok:
            _error(report, "terminal_foot_l2_stencil_transfer",
                   "terminal foot evaluated weights do not equal the complete rest stencil transfer")
        if not input_copy_matches:
            _error(report, "binding_leg_inputs", "binding leg_inputs do not match the immutable case inputs")
        if not hierarchy_matches or source_error > source_limit:
            _error(report, "binding_rest_sources", "binding rest frames or inverse binds do not match source-derived J/K/A frames")
        if tail_contract["present"]:
            _check_tail_binding(report, base_parsed, rest_parsed, binding,
                                prior_root_parsed, tail_contract, protocol)
    except Exception as exc:
        if not report["errors"] or report["errors"][-1].get("detail") != str(exc):
            _error(report, "input_or_check_failure", str(exc))
    return _finish(report)


def _stencil_signature(row: Any) -> tuple[tuple[int, float], ...]:
    return tuple((int(pair[0]), float(pair[1])) for pair in _sequence(row, "stencil") )


def _positions(mesh: Mapping[str, Any], count: int) -> list[Any] | None:
    for source in (mesh, mesh.get("metadata")):
        if isinstance(source, Mapping):
            for key in ("parametric_positions", "patch_positions", "positions"):
                if key in source:
                    values = _sequence(source[key], key)
                    if len(values) == count:
                        return values
    return None


def _exit_vertices(mesh: Mapping[str, Any]) -> set[int]:
    value = mesh.get("metadata")
    if isinstance(value, Mapping):
        for key in ("old_exit_vertices", "exit_vertices"):
            if key in value:
                return {int(index) for index in _sequence(value[key], key)}
    loops = mesh.get("loops", mesh.get("boundary_loops"))
    if isinstance(loops, Mapping):
        result: set[int] = set()
        for name, values in loops.items():
            normal = str(name).lower()
            if any(word in normal for word in ("exit", "ankle", "thigh")):
                result.update(int(index) for index in _sequence(values, f"loops.{name}"))
        return result
    return set()


def _declared_leg_root_ports(prior_root: Mapping[str, Any],
                             metadata: Mapping[str, Any]) -> dict[str, set[int]]:
    """Validate the two leg seam declarations against the prior root topology."""
    raw_chains = metadata.get("chains")
    if raw_chains is None:
        return {}
    chains = _mapping(raw_chains, "expanded_L0.metadata.chains")
    loops = prior_root.get("loops")
    if not isinstance(loops, Mapping):
        raise ValueError("leg root ports require prior_L0 source loops")
    boundary_cycles = _boundary_cycles(_edge_incidence(prior_root["quads"]))
    closed = _mapping(_mapping(metadata.get("root"),
                               "expanded_L0.metadata.root").get("old_thigh_ports_closed"),
                      "expanded_L0.metadata.root.old_thigh_ports_closed") \
        if metadata.get("root", {}).get("old_thigh_ports_closed") is not None else None
    result: dict[str, set[int]] = {}
    occupied: set[int] = set()
    for side in _SIDES:
        chain = _mapping(chains.get(side), f"expanded_L0.metadata.chains.{side}")
        declared = [int(index) for index in _sequence(
            chain.get("root_exit"), f"expanded_L0.metadata.chains.{side}.root_exit")]
        if len(declared) < 3 or len(set(declared)) != len(declared):
            raise ValueError(f"expanded_L0.metadata.chains.{side}.root_exit must be a unique loop")
        source_loop = loops.get(f"port.{side}_thigh")
        if source_loop is None:
            raise ValueError(f"prior_L0 is missing port.{side}_thigh")
        source_loop = [int(index) for index in _sequence(
            source_loop, f"prior_L0.loops.port.{side}_thigh")]
        if (not _cyclic_equal(declared, source_loop) or
                not any(_cyclic_equal(declared, boundary) for boundary in boundary_cycles)):
            raise ValueError(
                f"expanded_L0.metadata.chains.{side}.root_exit is not the declared prior-root boundary port")
        if closed is not None:
            closed_loop = [int(index) for index in _sequence(
                closed.get(side), f"expanded_L0.metadata.root.old_thigh_ports_closed.{side}")]
            if not _cyclic_equal(declared, closed_loop):
                raise ValueError(
                    f"expanded_L0.metadata.root.old_thigh_ports_closed.{side} disagrees with chains.{side}.root_exit")
        if occupied & set(declared):
            raise ValueError("left and right leg root ports overlap")
        occupied.update(declared)
        result[f"leg_{side}"] = set(declared)
    return result


def _declared_attachment_vertices(mesh: Mapping[str, Any],
                                  tail: Mapping[str, Any],
                                  prior_root: Mapping[str, Any]) -> dict[str, set[int]]:
    """Return old-L0 source vertices whose appended seams may affect L2 stencils.

    A combined appendage mesh can change Catmull--Clark rows at several declared
    ports.  Those local rows are expected to lose exact full-stencil identity;
    all other rows must still retain it.  This is accounting for explicit
    source metadata, not a distance-based exemption.
    """
    metadata = _mapping(mesh.get("metadata"), "expanded_L0.metadata")
    attachments: dict[str, set[int]] = {"tail": set(tail["host_vertices"])}
    attachments.update(_declared_leg_root_ports(prior_root, metadata))

    arms = metadata.get("arms")
    if isinstance(arms, Mapping):
        values: set[int] = set()
        for side in _SIDES:
            row = _mapping(arms.get(side), f"expanded_L0.metadata.arms.{side}")
            source = _mapping(row.get("source_port"),
                              f"expanded_L0.metadata.arms.{side}.source_port")
            values.update(int(index) for index in _sequence(
                source.get("indices"),
                f"expanded_L0.metadata.arms.{side}.source_port.indices"))
        attachments["arms"] = values

    head = metadata.get("head")
    if isinstance(head, Mapping):
        handoff = head.get("binding_handoff")
        source = handoff.get("consumed_neck_port_indices") if isinstance(handoff, Mapping) else None
        if source is None:
            source = head.get("neck_port_indices")
        if source is not None:
            attachments["head"] = {int(index) for index in _sequence(
                source, "expanded_L0.metadata.head neck port indices")}

    feet = metadata.get("feet")
    if isinstance(feet, Mapping):
        values = set()
        for side in _SIDES:
            row = _mapping(feet.get(side), f"expanded_L0.metadata.feet.{side}")
            source = row.get("ankle_source_loop")
            if source is None:
                attachment_loop = row.get("attachment_loop")
                source = (attachment_loop.get("ankle")
                          if isinstance(attachment_loop, Mapping) else None)
            if source is not None:
                values.update(int(index) for index in _sequence(
                    source, f"expanded_L0.metadata.feet.{side}.ankle_source_loop"))
        if values:
            attachments["feet"] = values

    return attachments


def compare_root(prior_L0: Mapping[str, Any], expanded_L0: Mapping[str, Any],
                 prior_L2: Mapping[str, Any], expanded_L2: Mapping[str, Any]) -> dict[str, Any]:
    """Compare unchanged root data, with an explicit tail host exception."""
    report = _report("creature-kernel.connected-leg-assembly-root-comparison.v1")
    try:
        old_l0, new_l0 = _mesh(prior_L0, "prior_L0"), _mesh(expanded_L0, "expanded_L0")
        old_l2, new_l2 = _mesh(prior_L2, "prior_L2"), _mesh(expanded_L2, "expanded_L2")
        l0_vertex_prefix = new_l0["vertices"][:len(old_l0["vertices"])] == old_l0["vertices"]
        tail = _tail_metadata_contract(new_l0["value"], len(new_l0["vertices"]))
        tail_mode = bool(tail["present"])
        if len(new_l0["vertices"]) < len(old_l0["vertices"]):
            l0_vertex_prefix = False
        if not old_l0["quads"] or not old_l2["quads"]:
            raise ValueError("root comparison requires non-empty L0 and L2 face arrays")
        if tail_mode:
            host_face = int(tail["host_face"])
            host_identity = (host_face < len(old_l0["quads"])
                             and list(old_l0["quads"][host_face]) == list(tail["host_vertices"]))
            kept_exact = all(
                0 <= old_index < len(old_l0["quads"])
                and 0 <= new_index < len(new_l0["quads"])
                and new_l0["quads"][new_index] == old_l0["quads"][old_index]
                for old_index, new_index in tail["kept_faces"]
            )
            replacement_valid = (
                host_identity and host_face < len(new_l0["quads"])
                and list(new_l0["quads"][host_face]) != list(tail["host_vertices"])
                and all(0 <= index < len(new_l0["quads"]) for index in tail["replacement_faces"])
            )
            l0_face_prefix = kept_exact and replacement_valid
        else:
            l0_face_prefix = new_l0["quads"][:len(old_l0["quads"])] == old_l0["quads"]
            host_identity = kept_exact = replacement_valid = True
        if len(new_l0["quads"]) < len(old_l0["quads"]):
            l0_face_prefix = False
        relation_numerator, relation_denominator = len(new_l0["quads"]), len(old_l0["quads"])
        expected_l2 = len(old_l2["quads"]) * relation_numerator
        l2_count_relation = len(new_l2["quads"]) * relation_denominator == expected_l2

        old_stencils, new_stencils = old_l2["stencils"], new_l2["stencils"]
        mapping_old_to_new: dict[int, int] = {}
        mapping_consistent = True
        stencil_invariance = True
        changed_rows: list[dict[str, Any]] = []
        unexpected_far_rows: list[int] = []
        if old_stencils is None or new_stencils is None:
            _unavailable(report, "missing_l2_stencils", "both L2 meshes must expose full base stencils")
            stencil_invariance = False
        else:
            old_rows = _sequence(old_stencils, "prior_L2.base_stencils")
            new_rows = _sequence(new_stencils, "expanded_L2.base_stencils")
            if len(old_rows) != len(old_l2["vertices"]) or len(new_rows) != len(new_l2["vertices"]):
                raise ValueError("L2 stencil arrays must cover their vertices")
            old_exit = _exit_vertices(old_l2["value"])
            old_positions = _positions(old_l2["value"], len(old_l2["vertices"]))
            new_positions = _positions(new_l2["value"], len(new_l2["vertices"]))
            if tail_mode:
                attachment_vertices = _declared_attachment_vertices(new_l0["value"], tail, old_l0["value"])
                all_attachment_vertices = set().union(*attachment_vertices.values())
                candidates: dict[tuple[tuple[tuple[int, float], ...], tuple[float, float, float]], list[int]] = defaultdict(list)
                by_stencil: dict[tuple[tuple[int, float], ...], list[int]] = defaultdict(list)
                for new_index, row in enumerate(new_rows):
                    signature = _stencil_signature(row)
                    by_stencil[signature].append(new_index)
                    candidates[(signature, new_l2["vertices"][new_index])].append(new_index)
                used: set[int] = set()
                for old_index, row in enumerate(old_rows):
                    signature = _stencil_signature(row)
                    exact = [index for index in candidates.get(
                        (signature, old_l2["vertices"][old_index]), []) if index not in used]
                    fallback = [index for index in by_stencil.get(signature, []) if index not in used]
                    new_index = (exact or fallback or [None])[0]
                    support_vertices = {int(pair[0]) for pair in _sequence(
                        row, "old attachment stencil")}
                    attachment_sources = sorted(
                        name for name, vertices in attachment_vertices.items()
                        if support_vertices & vertices
                    )
                    near = bool(support_vertices & all_attachment_vertices)
                    if new_index is None:
                        mapping_consistent = False if not near else mapping_consistent
                        row_data: dict[str, Any] = {
                            "old_vertex": old_index, "new_vertex": None,
                            "expected_near_attachment": near,
                            "attachment_sources": attachment_sources,
                            "reason": "changed_full_stencil",
                        }
                        if near:
                            changed_rows.append(row_data)
                        else:
                            unexpected_far_rows.append(old_index)
                            changed_rows.append(row_data)
                        continue
                    used.add(new_index)
                    mapping_old_to_new[old_index] = new_index
                    displacement = _distance(old_l2["vertices"][old_index], new_l2["vertices"][new_index])
                    if displacement > 0.0:
                        row_data = {"old_vertex": old_index, "new_vertex": new_index,
                                    "surface_displacement": displacement,
                                    "expected_near_attachment": near,
                                    "attachment_sources": attachment_sources,
                                    "reason": "same_full_stencil_displacement"}
                        if old_positions is not None and new_positions is not None:
                            row_data["parametric_position_displacement"] = _distance(
                                _vector(old_positions[old_index], "old parametric position"),
                                _vector(new_positions[new_index], "new parametric position"))
                        if old_exit:
                            row_data["distance_to_old_exit"] = min(
                                _distance(old_l2["vertices"][old_index], old_l2["vertices"][exit_index])
                                for exit_index in old_exit if 0 <= exit_index < len(old_l2["vertices"])
                            )
                        changed_rows.append(row_data)
                        if not near:
                            unexpected_far_rows.append(old_index)
                mapping_consistent = mapping_consistent and not unexpected_far_rows
                stencil_invariance = not unexpected_far_rows
            else:
                mapping_new_to_old: dict[int, int] = {}
                for old_face, new_face in zip(old_l2["quads"], new_l2["quads"][:len(old_l2["quads"])]):
                    for old_index, new_index in zip(old_face, new_face):
                        if (old_index in mapping_old_to_new and mapping_old_to_new[old_index] != new_index or
                                new_index in mapping_new_to_old and mapping_new_to_old[new_index] != old_index):
                            mapping_consistent = False
                        mapping_old_to_new[old_index] = new_index
                        mapping_new_to_old[new_index] = old_index
                mapping_consistent = mapping_consistent and len(new_l2["quads"]) >= len(old_l2["quads"])
                for old_index, new_index in mapping_old_to_new.items():
                    same = _stencil_signature(old_rows[old_index]) == _stencil_signature(new_rows[new_index])
                    displacement = _distance(old_l2["vertices"][old_index], new_l2["vertices"][new_index])
                    if same and displacement > 0.0:
                        stencil_invariance = False
                    if not same:
                        row_data = {"old_vertex": old_index, "new_vertex": new_index,
                                    "surface_displacement": displacement}
                        if old_positions is not None and new_positions is not None:
                            row_data["parametric_position_displacement"] = _distance(
                                _vector(old_positions[old_index], "old parametric position"),
                                _vector(new_positions[new_index], "new parametric position"))
                        if old_exit:
                            row_data["distance_to_old_exit"] = min(
                                _distance(old_l2["vertices"][old_index], old_l2["vertices"][exit_index])
                                for exit_index in old_exit if 0 <= exit_index < len(old_l2["vertices"])
                            )
                        changed_rows.append(row_data)

        report["checks"].update({
            "original_l0_vertex_prefix": l0_vertex_prefix,
            "original_l0_face_prefix": l0_face_prefix,
            "l2_face_count_relation": l2_count_relation,
            "l2_face_prefix_mapping_consistent": mapping_consistent,
            "same_full_stencil_unchanged_invariance": stencil_invariance,
        })
        if tail_mode:
            report["checks"].update({
                "tail_explicit_host_identity": host_identity,
                "tail_kept_root_faces_exact": kept_exact,
                "tail_host_replacement_declared": replacement_valid,
                "tail_far_support_invariance": not unexpected_far_rows,
                "tail_near_attachment_changes_labelled": all(
                    row.get("expected_near_attachment") for row in changed_rows
                    if row.get("new_vertex") is None or row.get("surface_displacement", 0.0) > 0.0
                ),
            })
        parametric_displacements = [row["parametric_position_displacement"] for row in changed_rows
                                    if "parametric_position_displacement" in row]
        location_rows = [row for row in changed_rows if "distance_to_old_exit" in row]
        report["metrics"].update({
            "l0_relation": {"numerator": relation_numerator, "denominator": relation_denominator},
            "old_to_new_l2_vertex_map": {str(key): value for key, value in sorted(mapping_old_to_new.items())},
            "changed_stencil_count": len(changed_rows),
            "changed_stencil_displacements": changed_rows,
            "unexpected_far_support_rows": unexpected_far_rows,
            "tail_mode": tail_mode,
            "parametric_patch_position_displacement_max": max(parametric_displacements, default=None),
            "changed_stencil_location_worst": max(location_rows, key=lambda row: row["distance_to_old_exit"], default=None),
            "changed_stencil_location_available": bool(location_rows),
            "declared_attachment_vertices": {
                name: sorted(vertices) for name, vertices in attachment_vertices.items()
            } if tail_mode and old_stencils is not None and new_stencils is not None else {},
        })
        if not l0_vertex_prefix:
            _error(report, "l0_vertex_prefix", "expanded L0 must preserve original vertices as a prefix")
        if not l0_face_prefix:
            _error(report, "tail_root_face_mapping" if tail_mode else "l0_face_prefix",
                   "expanded L0 must preserve every non-host face and explicitly replace only the declared host"
                   if tail_mode else "expanded L0 must append faces after the original face prefix")
        if not l2_count_relation:
            _error(report, "l2_face_count_relation", "expanded L2 face count does not equal original L2 count times the L0 relation")
        if not mapping_consistent:
            _error(report, "l2_face_mapping", "L2 correspondence is inconsistent outside the declared tail attachment")
        if not stencil_invariance:
            _error(report, "stencil_invariance", "far-support vertices with identical full stencils were displaced or lost")
        if tail_mode and not report["checks"]["tail_near_attachment_changes_labelled"]:
            _error(report, "tail_near_attachment_label", "tail attachment changes must be explicitly labelled as near-host changes")
    except Exception as exc:
        if not report["errors"] or report["errors"][-1].get("detail") != str(exc):
            _error(report, "input_or_check_failure", str(exc))
    return _finish(report)


__all__ = ["check_mesh", "check_pose", "check_binding", "compare_root"]
