"""Future-only NumPy AABB partition around the frozen collision narrowphase.

This module is intentionally not wired into the connected-leg checker.  It
keeps the frozen point, normalization, triangle, interval, shared-vertex,
shared-edge, duplicate, and SAT semantics, while replacing only exhaustive
Python pair enumeration with a bounded NumPy AABB partition.  Every pair is
still accounted for in deterministic global ``i < j`` order.
"""
from __future__ import annotations

import importlib.util
import math
from pathlib import Path
import sys
from typing import Any

import numpy as np


FROZEN_CORE_PATH = Path(
    "/home/ben/.cache/creature-kernel/pelvis-thigh-transition/"
    "attempt-2-snapshot/source/experiments/owned-root-assembly-successor/"
    "mesh_correctness.py"
)
METHOD = "numpy-conservative-aabb-partition-frozen-narrowphase.v1"
DEFAULT_BLOCK_SIZE = 1024
MAX_BLOCK_SIZE = 2048
_STAGES = (
    "aabb-disjoint", "sat-disjoint", "hit", "point-only", "excluded-adjacent"
)
_CORE: Any | None = None


def _load_core() -> Any:
    global _CORE
    if _CORE is not None:
        return _CORE
    if not FROZEN_CORE_PATH.is_file() or FROZEN_CORE_PATH.is_symlink():
        raise RuntimeError(f"frozen collision core is unavailable: {FROZEN_CORE_PATH}")
    spec = importlib.util.spec_from_file_location(
        "connected_leg_future_frozen_collision_core", FROZEN_CORE_PATH
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load frozen collision core: {FROZEN_CORE_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    if Path(module.__file__).resolve() != FROZEN_CORE_PATH.resolve():
        raise RuntimeError("frozen collision core resolved away from its recorded path")
    _CORE = module
    return module


def _checked_block_size(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("block_size must be an integer")
    if value <= 0 or value > MAX_BLOCK_SIZE:
        raise ValueError(f"block_size must be in 1..{MAX_BLOCK_SIZE}")
    return value


def _intersection_inputs_without_count_cap(core: Any, vertices: Any,
                                           triangles: Any) -> tuple[Any, ...]:
    """Use the frozen validation/normalization path without its 4096 wrapper."""
    points = core._points(vertices)
    faces = core._indexed_rows(
        triangles, 3, len(points), "triangles", cap=None
    )
    normalized, scale = core._normalize_points(points)
    for index, face in enumerate(faces):
        length = core._norm_vec(core._triangle_normal(face, normalized))
        if not math.isfinite(length) or length <= core._FIXED_D:
            core._fail(f"normalized triangle normal degeneracy at {index}")
    bounds = tuple(core._aabb(normalized, face) for face in faces)
    face_sets = tuple(frozenset(face) for face in faces)
    return faces, normalized, scale, bounds, face_sets


def _aabb_disjoint_row(core: Any, lower: np.ndarray, upper: np.ndarray,
                       first: int, second_start: int,
                       second_end: int) -> np.ndarray:
    """Return conservative frozen-interval AABB rejects for one first row."""
    second_lower = lower[second_start:second_end]
    second_upper = upper[second_start:second_end]
    first_lower = lower[first]
    first_upper = upper[first]
    # Moving the rejection cut toward -infinity can only turn a frozen reject
    # into a survivor.  It cannot reject a pair that the frozen interval rule
    # would retain.
    cut_for_second = np.nextafter(
        second_lower - core.I0, -np.inf
    )
    cut_for_first = np.nextafter(
        first_lower - core.I0, -np.inf
    )
    return np.any(
        (first_upper < cut_for_second) |
        (second_upper < cut_for_first), axis=1
    )


def _bounded_append(target: list[Any], value: Any, cap: int) -> None:
    if len(target) < cap:
        target.append(value)


def _pair_ordinal(triangle_count: int, first: int, second: int) -> int:
    return first * (2 * triangle_count - first - 1) // 2 + second - first - 1


def collision_report(vertices: Any, triangles: Any, *,
                     include_classifications: bool = False,
                     block_size: int = DEFAULT_BLOCK_SIZE) -> dict[str, Any]:
    """Return future-checker collision evidence with frozen classifications.

    The local parser intentionally accepts more than the frozen core's
    production 4096-triangle wrapper, but retains every frozen per-point,
    normalization, triangle-degeneracy, pair-status, shared-one rational, and
    SAT operation.  ``block_size`` is a bounded memory/performance parameter,
    not a numerical or geometric gate.
    """
    if not isinstance(include_classifications, bool):
        raise ValueError("include_classifications must be a boolean")
    block_size = _checked_block_size(block_size)
    core = _load_core()
    (faces, normalized, scale, bounds, face_sets) = \
        _intersection_inputs_without_count_cap(core, vertices, triangles)
    triangle_count = len(faces)
    expected_pairs = triangle_count * (triangle_count - 1) // 2
    if include_classifications and expected_pairs > core._MAX_CLASSIFICATION_DETAILS:
        core._fail(
            f"classification detail cap exceeded: {expected_pairs} > "
            f"{core._MAX_CLASSIFICATION_DETAILS}"
        )
    bounds_array = np.asarray(bounds, dtype=np.float64)
    lower = bounds_array[:, :3]
    upper = bounds_array[:, 3:]
    class_counts = {stage: 0 for stage in _STAGES}
    candidate_pairs: list[list[int]] = []
    hit_pairs: list[list[int]] = []
    nontrivial_classifications: list[list[Any]] = []
    classifications: list[list[Any]] | None = [] if include_classifications else None
    candidate_count = 0
    hit_count = 0
    first_hit_pair: list[int] | None = None
    proven_aabb_reject_count = 0
    survivor_count = 0

    for first in range(max(0, triangle_count - 1)):
        for second_start in range(first + 1, triangle_count, block_size):
            second_end = min(second_start + block_size, triangle_count)
            disjoint = _aabb_disjoint_row(
                core, lower, upper, first, second_start, second_end
            )
            reject_count = int(np.count_nonzero(disjoint))
            proven_aabb_reject_count += reject_count
            if include_classifications:
                second_offsets = range(second_end - second_start)
            else:
                second_offsets = np.flatnonzero(~disjoint).tolist()
                survivor_count += len(second_offsets)

            for offset in second_offsets:
                second = second_start + int(offset)
                ordinal = _pair_ordinal(triangle_count, first, second)
                if bool(disjoint[int(offset)]):
                    stage = "aabb-disjoint"
                    if include_classifications:
                        class_counts[stage] += 1
                        assert classifications is not None
                        classifications.append([[first, second], stage])
                    continue

                if include_classifications:
                    survivor_count += 1
                stage = core._pair_status(
                    first, second, faces, normalized, bounds, face_sets
                )
                pair = (first, second)
                if stage == "candidate":
                    candidate_count += 1
                    if candidate_count > core._MAX_CANDIDATES:
                        core._fail(
                            f"AABB candidate cap exceeded: >{core._MAX_CANDIDATES}"
                        )
                    _bounded_append(candidate_pairs, [first, second],
                                    core._MAX_DIAGNOSTIC_EVIDENCE)
                    first_points = tuple(normalized[index] for index in faces[first])
                    second_points = tuple(normalized[index] for index in faces[second])
                    stage = "sat-disjoint" if core._sat_disjoint(
                        first_points, second_points
                    ) else "hit"
                core._record_pair_policy(
                    triangle_count, first, second, ordinal, stage, class_counts
                )
                if stage == "hit":
                    hit_count += 1
                    if first_hit_pair is None:
                        first_hit_pair = [first, second]
                    _bounded_append(hit_pairs, [first, second],
                                    core._MAX_DIAGNOSTIC_EVIDENCE)
                if stage != "aabb-disjoint":
                    _bounded_append(
                        nontrivial_classifications,
                        [[first, second], stage],
                        core._MAX_DIAGNOSTIC_EVIDENCE,
                    )
                if classifications is not None:
                    classifications.append([[first, second], stage])

    if not include_classifications:
        class_counts["aabb-disjoint"] += proven_aabb_reject_count
    classification_count = sum(class_counts.values())
    partition_complete = (
        proven_aabb_reject_count + survivor_count == expected_pairs
    )
    classification_partition_complete = classification_count == expected_pairs
    hit_pairs_truncated = hit_count > len(hit_pairs)
    candidate_pairs_truncated = candidate_count > len(candidate_pairs)
    nontrivial_pair_count = expected_pairs - class_counts["aabb-disjoint"]
    nontrivial_evidence_truncated = (
        nontrivial_pair_count > len(nontrivial_classifications)
    )
    errors: list[dict[str, Any]] = []
    if hit_pairs_truncated:
        errors.append({
            "code": "truncated_collision_hit_inventory",
            "detail": "frozen hit inventory evidence cap was exceeded",
        })
    available = bool(
        partition_complete and classification_partition_complete and not errors
    )
    report: dict[str, Any] = {
        "schema": "creature-kernel.connected-leg-future-collision.v1",
        "method": METHOD,
        "narrowphase": "frozen _pair_status followed by frozen _sat_disjoint",
        "intersection_core_path": str(FROZEN_CORE_PATH),
        "triangle_count": triangle_count,
        "local_triangle_limit_exceeded": triangle_count > core._MAX_TRIANGLES,
        "normalization_scale": scale,
        "block_size": block_size,
        "blocks": [
            {"block": index, "start": start,
             "end": min(start + block_size, triangle_count),
             "triangle_count": min(start + block_size, triangle_count) - start}
            for index, start in enumerate(range(0, triangle_count, block_size))
        ],
        "pair_count": expected_pairs,
        "proven_aabb_reject_count": proven_aabb_reject_count,
        "survivor_pair_count": survivor_count,
        "pair_partition_complete": partition_complete,
        "final_classification_count": classification_count,
        "final_classification_partition_complete": classification_partition_complete,
        "class_counts": {stage: class_counts[stage] for stage in _STAGES},
        "candidate_count": candidate_count,
        "broad_phase_candidate_count": candidate_count,
        "intersection_hit_count": hit_count,
        "candidate_pairs": candidate_pairs,
        "hit_pairs": hit_pairs,
        "first_hit_pair": first_hit_pair,
        "candidate_pairs_truncated": candidate_pairs_truncated,
        "hit_pairs_truncated": hit_pairs_truncated,
        "nontrivial_pair_count": nontrivial_pair_count,
        "nontrivial_classifications": nontrivial_classifications,
        "nontrivial_evidence_truncated": nontrivial_evidence_truncated,
        "errors": errors,
        "available": available,
        "pass": bool(available and hit_count == 0),
    }
    if classifications is not None:
        report["classifications"] = classifications
    return report


__all__ = ["FROZEN_CORE_PATH", "METHOD", "collision_report"]
