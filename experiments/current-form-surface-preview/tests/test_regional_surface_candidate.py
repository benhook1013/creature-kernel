from __future__ import annotations

import copy
from dataclasses import replace
import importlib.util
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

import numpy as np


REPO_ROOT = Path(__file__).resolve().parents[3]
EXPERIMENT_ROOT = REPO_ROOT / "experiments/current-form-surface-preview"
SOURCE_FORM = REPO_ROOT / "examples/body-documents/stylized-digitigrade-biped-authored-form.json"
CLI = REPO_ROOT / "target/debug/creature-kernel"
CANDIDATE_SPEC = importlib.util.spec_from_file_location(
    "regional_surface_candidate",
    EXPERIMENT_ROOT / "regional_surface_candidate.py",
)
assert CANDIDATE_SPEC and CANDIDATE_SPEC.loader
candidate_module = importlib.util.module_from_spec(CANDIDATE_SPEC)
sys.modules[CANDIDATE_SPEC.name] = candidate_module
CANDIDATE_SPEC.loader.exec_module(candidate_module)
sys.path.insert(0, str(EXPERIMENT_ROOT))
import generate_structural_profile_sources as profile_generator  # noqa: E402
sys.path.pop(0)


def inspection_command_prefix(cargo_path: str | None, cli_path: Path = CLI) -> list[str]:
    if cargo_path:
        return [cargo_path, "run", "-q", "-p", "creature-kernel-cli", "--"]
    if cli_path.is_file() and os.access(cli_path, os.X_OK):
        return [str(cli_path)]
    raise AssertionError(
        "neither cargo on PATH nor an executable fresh creature-kernel fallback is available: "
        f"{cli_path}"
    )


def _prepared_radii(section, axes=("lateral", "up", "forward")) -> np.ndarray:
    return np.asarray(
        [float(getattr(section, f"{axis}_radius_permille")) / 1000.0 for axis in axes],
        dtype=np.float64,
    )


def _prepared_station_center(form, by_key, authored, projected) -> np.ndarray:
    owner = by_key[authored.owner]
    source = candidate_module._descriptor_source(
        candidate_module._load_surface_preview(), owner, form.reference_scale,
    )
    return candidate_module._source_section_center(
        owner,
        source,
        authored.owner[3],
        projected.position,
        form.reference_scale,
        f"test.{authored.name}",
    )


_RETAINED_LOWER_PELVIS_FACTORS = np.asarray((0.82, 0.78, 0.82), dtype=np.float64)
_RETAINED_UPPER_PELVIS_FACTORS = np.asarray((0.98, 0.90, 0.92), dtype=np.float64)


def _retained_baseline_torso_radii(form, profile_id: str) -> tuple[np.ndarray, ...]:
    """Reconstruct the retained pre-correction torso formula independently."""

    variant_index, _, _ = candidate_module._variant(form, profile_id)
    projected = tuple(form.variant_torso_profiles[variant_index].sections)
    source = tuple(_prepared_radii(section, ("lateral", "anterior", "posterior")) for section in projected)
    return (
        source[0] * _RETAINED_LOWER_PELVIS_FACTORS,
        source[1] * _RETAINED_UPPER_PELVIS_FACTORS,
        source[2],
        np.maximum(source[3], 0.88 * np.minimum(source[2], source[4])),
        source[4],
        source[5],
        np.minimum(source[6], source[5] * np.asarray((0.86, 0.82, 0.82), dtype=np.float64)),
    )


def _retained_baseline_hip_cup_records(candidate, form, profile_id: str):
    """Reconstruct cup stations/certificates against the retained torso formula."""

    hybrid = candidate_module._load_hybrid()
    baseline_stations = tuple(
        hybrid.AxialStation(
            station.name,
            station.position,
            station.center,
            tuple(float(value) for value in radii),
            station.semantic_key,
        )
        for station, radii in zip(candidate.stations, _retained_baseline_torso_radii(form, profile_id))
    )
    baseline_chain = hybrid.AxialMassChain(
        baseline_stations,
        candidate.chain.regions,
        start_cap_radius=candidate.chain.start_cap_radius,
        end_cap_radius=candidate.chain.end_cap_radius,
    )
    namespace = form.source["namespace"]
    pelvis_key = (namespace, (), "part", "pelvis")
    records = []
    for side_index, side in enumerate(("left", "right")):
        route = candidate.routes[3 + side_index]
        thigh_key = (namespace, (side,), "part", "thigh")
        cups, evidence, context = candidate_module._derive_pelvis_hip_cup_chain(
            hybrid,
            baseline_chain,
            baseline_chain.stations[0],
            baseline_chain.regions[0],
            baseline_chain.regions[0].first_basis,
            route.sections[3],
            pelvis_key,
            thigh_key,
            route.route_name,
        )
        baseline_route = replace(route, sections=(*cups, *route.sections[3:]))
        baseline_context = dict(context)
        baseline_context["evidence"] = [dict(item) for item in evidence]
        candidate_module._certify_pelvis_leg_overlap(
            hybrid,
            baseline_chain,
            baseline_route,
            baseline_context,
        )
        records.append((cups, baseline_context["evidence"][0]["finite_open_overlap_certificate"]))
    return tuple(records)


def _final_skin_ray_extent(candidate, center, direction, maximum: float) -> float:
    """Find the outermost final-skin crossing on one local cross-section ray."""

    samples = np.linspace(0.0, maximum, 2049, dtype=np.float64)
    points = np.asarray(center, dtype=np.float64) + samples[:, None] * np.asarray(direction, dtype=np.float64)
    values = np.asarray(candidate.evaluate(points), dtype=np.float64)
    if not np.isfinite(values).all() or values[0] >= 0.0:
        raise AssertionError("cross-section ray must begin inside the final skin")
    crossings = np.flatnonzero(values[:-1] * values[1:] <= 0.0)
    if len(crossings) == 0:
        raise AssertionError("cross-section ray has no final-skin crossing")
    index = int(crossings[-1])
    denominator = values[index] - values[index + 1]
    fraction = 0.5 if denominator == 0.0 else float(np.clip(values[index] / denominator, 0.0, 1.0))
    return float(samples[index] + fraction * (samples[index + 1] - samples[index]))


def _candidate_without_neck_collar_lift(candidate):
    """Rebuild the same live graph with only the retained lift reversed."""

    hybrid = candidate_module._load_hybrid()
    routes = list(candidate.routes)
    route = routes[0]
    station = route.sections[0]
    center = np.asarray(station.center, dtype=np.float64).copy()
    center[1] -= candidate_module.NECK_COLLAR_LIFT_UP_RADIUS_FRACTION * float(station.radii[1])
    sections = list(route.sections)
    sections[0] = hybrid.SectionStation(
        station.name,
        station.position,
        tuple(center),
        station.radii,
        station.semantic_key,
        station.source_key,
        station.source_index,
    )
    closures = {item.name: item for item in route.endpoint_closures}
    old = closures["neck-collar-closure"]
    closures[old.name] = hybrid.EndpointClosure(
        old.name,
        sections[0].center,
        sections[0].radii,
        old.semantic_key,
        old.source_key,
    )
    routes[0] = hybrid.AnisotropicSectionSweep(
        tuple(sections),
        route.connections,
        tuple(closures[item.name] for item in route.endpoint_closures),
        route.route_name,
    )
    attachments = tuple(
        hybrid.SectionAttachment(item.route_name, item, None, None, f"route:{item.route_name}")
        for item in routes
    )
    interfaces, _ = candidate_module._make_interface_patches(
        hybrid,
        candidate.chain,
        tuple(routes),
        candidate.controls,
        candidate.source["namespace"],
    )
    field = hybrid.FullSectionComposite(candidate.chain, attachments, interfaces=interfaces)
    return replace(candidate, routes=tuple(routes), field=field, mesh=None)


def _candidate_without_wrist_transition(candidate, side: str):
    """Reconstruct the exact old arm span for a final-skin counterfactual."""

    hybrid = candidate_module._load_hybrid()
    route = next(item for item in candidate.routes if item.route_name == f"{side}-arm")
    if route.sections[5].name != "wrist-transition":
        raise AssertionError(f"{route.route_name} does not contain the derived wrist transition")
    sections = route.sections[:5] + route.sections[6:]
    connections = tuple(
        hybrid.SectionConnection(
            f"{route.route_name}:{sections[index].name}-to-{sections[index + 1].name}",
            index,
            index + 1,
            "upper-arm-forearm",
        )
        for index in range(len(sections) - 1)
    )
    old_route = hybrid.AnisotropicSectionSweep(
        sections,
        connections,
        route.endpoint_closures,
        route.route_name,
    )
    attachments = tuple(
        replace(item, field=old_route) if item.name == route.route_name else item
        for item in candidate.field.attachments
    )
    interfaces = tuple(
        replace(item, child=old_route) if item.child is route else item
        for item in candidate.field.interfaces
    )
    field = hybrid.FullSectionComposite(candidate.chain, attachments, interfaces=interfaces)
    return replace(
        candidate,
        routes=tuple(old_route if item is route else item for item in candidate.routes),
        field=field,
        mesh=None,
    )


def _candidate_without_femoral_neck_axis_decomposition(candidate, side: str):
    """Reconstruct the diagonal femoral-neck route for a final-skin counterfactual."""

    hybrid = candidate_module._load_hybrid()
    route = next(item for item in candidate.routes if item.route_name == f"{side}-leg")
    rim = route.sections[1]
    neck = route.sections[2]
    thigh = route.sections[3]
    diagonal_center = np.asarray(rim.center, dtype=np.float64) + candidate_module.FEMORAL_NECK_CENTER_FACTOR * (
        np.asarray(thigh.center, dtype=np.float64) - np.asarray(rim.center, dtype=np.float64)
    )
    diagonal_neck = hybrid.SectionStation(
        neck.name,
        neck.position,
        tuple(diagonal_center),
        neck.radii,
        neck.semantic_key,
        neck.source_key,
        neck.source_index,
    )
    old_route = hybrid.AnisotropicSectionSweep(
        route.sections[:2] + (diagonal_neck,) + route.sections[3:],
        route.connections,
        route.endpoint_closures,
        route.route_name,
    )
    attachments = tuple(
        replace(item, field=old_route) if item.field is route else item
        for item in candidate.field.attachments
    )
    interfaces = []
    for patch in candidate.field.interfaces:
        kwargs = {}
        if patch.parent is route:
            kwargs["parent"] = old_route
        if patch.child is route:
            kwargs["child"] = old_route
        interfaces.append(replace(patch, **kwargs) if kwargs else patch)
    field = hybrid.FullSectionComposite(candidate.chain, attachments, interfaces=interfaces)
    return replace(
        candidate,
        routes=tuple(old_route if item is route else item for item in candidate.routes),
        field=field,
        mesh=None,
    )


def _independent_wrist_geometric_oracle(midpoint, distal, hand_closure, wrist):
    """Check the returned slice against the hand ellipsoid and old span geometry."""

    M = np.asarray(midpoint.center, dtype=np.float64)
    D = np.asarray(distal.center, dtype=np.float64)
    H = np.asarray(hand_closure.center, dtype=np.float64)
    W = np.asarray(wrist.center, dtype=np.float64)
    Rm = np.asarray(midpoint.radii, dtype=np.float64)
    Rd = np.asarray(distal.radii, dtype=np.float64)
    Rh = np.asarray(hand_closure.radii, dtype=np.float64)
    forearm_delta = D - M
    forearm_length = float(np.linalg.norm(forearm_delta))
    axis = forearm_delta / forearm_length
    wrist_fraction = float(np.dot(W - M, axis) / forearm_length)
    hand_axial_coordinate = float(np.dot(W - H, axis))
    hand_axial_normalized = hand_axial_coordinate / Rh[0]
    if abs(hand_axial_normalized) >= 1.0:
        raise AssertionError("wrist must lie within the hand ellipsoid axial extent")
    hand_cross_section_radii = Rh[1:] * math.sqrt(1.0 - hand_axial_normalized**2)
    old_forearm_radii_at_wrist = Rm + wrist_fraction * (Rd - Rm)
    return hand_cross_section_radii, Rd[1:], old_forearm_radii_at_wrist


def _ray_root(field, y: float, axis: int) -> float | None:
    radii = np.linspace(0.0, 1.8, 721, dtype=np.float64)
    points = np.zeros((len(radii), 3), dtype=np.float64)
    points[:, 1] = y
    points[:, axis] = radii
    values = np.asarray(field.evaluate(points), dtype=np.float64)
    inside = values <= 0.0
    crossings = np.flatnonzero(inside[:-1] & ~inside[1:])
    if len(crossings) == 0:
        return None
    index = int(crossings[-1])
    first_radius, second_radius = radii[index:index + 2]
    first_value, second_value = values[index:index + 2]
    if second_value == first_value:
        return float(first_radius)
    return float(first_radius - first_value * (second_radius - first_radius) / (second_value - first_value))


def _ray_root_band_delta(baseline, candidate, lower: float, upper: float) -> dict[str, float]:
    ys = np.linspace(1.95, 3.05, 45, dtype=np.float64)
    selected = (ys >= lower) & (ys <= upper)
    result = {}
    for label, axis in (("lateral", 0), ("forward", 2)):
        baseline_roots = np.asarray(
            [_ray_root(baseline.field, float(y), axis) for y in ys],
            dtype=np.float64,
        )
        candidate_roots = np.asarray(
            [_ray_root(candidate.field, float(y), axis) for y in ys],
            dtype=np.float64,
        )
        delta = (candidate_roots - baseline_roots)[selected]
        finite = delta[np.isfinite(delta)]
        if len(finite) == 0:
            raise AssertionError(f"no finite {label} roots in y={lower}:{upper}")
        result[f"{label}_max_abs"] = float(np.max(np.abs(finite)))
        result[f"{label}_mean_signed"] = float(np.mean(finite))
    return result


def _independent_endpoint_oracle(chain, lower: bool, toward, mu: float):
    """Closed-form oracle independent of candidate/hybrid ray helpers."""

    station = chain.stations[0 if lower else -1]
    region = chain.regions[0 if lower else -1]
    basis = region.first_basis if lower else region.last_basis
    cap_radius = chain.start_cap_radius if lower else chain.end_cap_radius
    origin = np.asarray(station.center, dtype=np.float64)
    delta = np.asarray(toward, dtype=np.float64) - origin
    lateral = float(np.dot(delta, np.asarray(basis.lateral_axis)))
    forward = float(np.dot(delta, np.asarray(basis.forward_axis)))
    axial = float(np.dot(delta, np.asarray(basis.axial_axis)))
    lateral_radius, anterior_radius, posterior_radius = station.radii
    width = min(anterior_radius, posterior_radius)
    transverse_squared = (lateral / lateral_radius) ** 2 + (axial / cap_radius) ** 2

    def forward_radius(ray_fraction: float) -> float:
        normalized = max(-1.0, min(1.0, forward * ray_fraction / width))
        blend = 0.5 + 0.75 * normalized - 0.25 * normalized**3
        return posterior_radius + blend * (anterior_radius - posterior_radius)

    def solve(normalized_level: float) -> float:
        candidates = []
        if abs(forward) <= 1.0e-12:
            candidates.append(normalized_level / math.sqrt(transverse_squared))
        else:
            slope = forward / width
            difference = anterior_radius - posterior_radius
            radius_polynomial = np.asarray((
                posterior_radius + 0.5 * difference,
                0.75 * difference * slope,
                0.0,
                -0.25 * difference * slope**3,
            ))
            radius_squared = np.polynomial.polynomial.polymul(radius_polynomial, radius_polynomial)
            equation = np.polynomial.polynomial.polymul(
                np.asarray((-normalized_level**2, 0.0, transverse_squared)),
                radius_squared,
            )
            equation[2] += forward**2
            saturation = width / abs(forward)
            candidates.extend(
                float(root.real)
                for root in np.polynomial.polynomial.polyroots(equation)
                if abs(float(root.imag)) <= 1.0e-9 and 0.0 < float(root.real) <= saturation + 1.0e-8
            )
            saturated_radius = anterior_radius if forward > 0.0 else posterior_radius
            saturated_fraction = normalized_level / math.sqrt(
                transverse_squared + (forward / saturated_radius) ** 2,
            )
            if saturated_fraction >= saturation - 1.0e-8:
                candidates.append(saturated_fraction)
        exact = []
        for candidate in sorted(candidates):
            normalized = math.sqrt(
                (lateral * candidate / lateral_radius) ** 2
                + (forward * candidate / forward_radius(candidate)) ** 2
                + (axial * candidate / cap_radius) ** 2
            )
            if abs(normalized - normalized_level) <= 2.0e-7 and (
                not exact or abs(candidate - exact[-1]) > 2.0e-7
            ):
                exact.append(candidate)
        if len(exact) != 1:
            raise AssertionError(f"oracle expected one exact root, got {exact!r}")
        return exact[0]

    scale = min(*station.radii, cap_radius)
    boundary_fraction = solve(1.0)
    interior_fraction = solve(1.0 - mu / scale)
    return (
        origin + boundary_fraction * delta,
        origin + interior_fraction * delta,
        interior_fraction / boundary_fraction,
    )


def _expected_variant_geometry(form, profile_id: str) -> dict[str, object]:
    variant_index, descriptors, _ = candidate_module._variant(form, profile_id)
    by_key = candidate_module._descriptor_map(descriptors, form.source["namespace"])

    authored_torso = tuple(form.authored_torso_profile.sections)
    projected_torso = tuple(form.variant_torso_profiles[variant_index].sections)
    torso_centers = tuple(
        candidate_module._owner_point(
            by_key[authored.owner], form.reference_scale, projected.position,
            f"test.torso.{authored.name}",
        )
        for authored, projected in zip(authored_torso, projected_torso)
    )
    torso_source_radii = tuple(
        _prepared_radii(projected, ("lateral", "anterior", "posterior"))
        for projected in projected_torso
    )
    torso_radii = []
    for index, authored in enumerate(authored_torso):
        source = torso_source_radii[index]
        if authored.name == "waist-abdomen":
            expected = np.maximum(
                source,
                0.88 * np.minimum(torso_source_radii[2], torso_source_radii[4]),
            )
        elif authored.name == "upper-pelvis":
            expected = np.minimum(
                source * np.asarray(candidate_module.TORSO_RADIUS_FACTORS[authored.name]),
                torso_source_radii[0]
                * np.asarray(candidate_module.TORSO_RADIUS_FACTORS["lower-pelvis"]),
            )
        elif authored.name == "upper-ribcage-shoulder":
            expected = np.minimum(
                source,
                torso_source_radii[5]
                * np.asarray(candidate_module.TORSO_RADIUS_FACTORS[authored.name]),
            )
        else:
            expected = source * np.asarray(candidate_module.TORSO_RADIUS_FACTORS[authored.name])
        torso_radii.append(expected)

    authored_head = tuple(form.authored_head_neck_profile.sections)
    projected_head = tuple(form.variant_head_neck_profiles[variant_index].sections)
    head_source_centers = tuple(
        _prepared_station_center(form, by_key, authored, projected)
        for authored, projected in zip(authored_head, projected_head)
    )
    head_source_radii = tuple(_prepared_radii(projected) for projected in projected_head)
    muzzle_root = head_source_centers[5]
    head = []
    for authored, source_center, source_radii in zip(authored_head, head_source_centers, head_source_radii):
        center = source_center
        radii = source_radii
        if authored.name == "neck-collar":
            center = source_center.copy()
            center[1] += candidate_module.NECK_COLLAR_LIFT_UP_RADIUS_FRACTION * source_radii[1]
        if authored.name in candidate_module.HEAD_RADIUS_FACTORS:
            radii = source_radii * np.asarray(candidate_module.HEAD_RADIUS_FACTORS[authored.name])
        if authored.name in candidate_module.MUZZLE_CENTER_FACTORS:
            factor = candidate_module.MUZZLE_CENTER_FACTORS[authored.name]
            center = muzzle_root + factor * (source_center - muzzle_root)
        head.append({"center": center, "radii": radii, "source_radii": source_radii})

    authored_feet = tuple(form.authored_foot_profile.sides)
    projected_feet = tuple(form.variant_foot_profiles[variant_index].sides)
    feet: dict[str, tuple[dict[str, np.ndarray], ...]] = {}
    for authored_side, projected_side in zip(authored_feet, projected_feet):
        feet[authored_side.side] = tuple(
            {
                "center": _prepared_station_center(form, by_key, authored, projected),
                "radii": _prepared_radii(projected),
            }
            for authored, projected in zip(authored_side.sections, projected_side.sections)
        )

    arms: dict[str, tuple[dict[str, np.ndarray], ...]] = {}
    authored_arms = tuple(form.authored_arm_profile.sides)
    projected_arms = tuple(form.variant_arm_profiles[variant_index].sides)
    for authored_side, projected_side in zip(authored_arms, projected_arms):
        source_centers = tuple(
            _prepared_station_center(form, by_key, authored, projected)
            for authored, projected in zip(authored_side.sections, projected_side.sections)
        )
        source_radii = tuple(_prepared_radii(projected) for projected in projected_side.sections)
        expected_radii = [item.copy() for item in source_radii]
        expected_radii[1] = source_radii[1] * candidate_module.MIDPOINT_BELLY_FACTORS["upper-arm-midpoint"]
        expected_radii[2] = np.minimum(
            source_radii[2],
            candidate_module.JOINT_RADIUS_FACTOR * np.minimum(source_radii[1], source_radii[3]),
        )
        expected_radii[3] = source_radii[3] * candidate_module.MIDPOINT_BELLY_FACTORS["forearm-midpoint"]
        arms[authored_side.side] = tuple(
            {"center": center, "radii": radii, "source_radii": source}
            for center, radii, source in zip(source_centers, expected_radii, source_radii)
        )

    legs: dict[str, dict[str, object]] = {}
    authored_legs = tuple(form.authored_leg_profile.sides)
    projected_legs = tuple(form.variant_leg_profiles[variant_index].sides)
    pelvis_key = (form.source["namespace"], (), "part", "pelvis")
    pelvis_source = candidate_module._descriptor_source(
        candidate_module._load_surface_preview(), by_key[pelvis_key], form.reference_scale,
    )
    pelvis_center = np.asarray(pelvis_source["center"], dtype=np.float64)
    caps = (
        candidate_module.TORSO_LOWER_CAP_FACTOR
        * float(np.mean([_prepared_radii(side.sections[0])[1] for side in projected_legs])),
        candidate_module.TORSO_UPPER_CAP_FACTOR * head_source_radii[0][1],
    )
    hybrid = candidate_module._load_hybrid()
    expected_chain = hybrid.AxialMassChain(
        tuple(
            hybrid.AxialStation(authored.name, float(center[1]), tuple(center), tuple(radii))
            for authored, center, radii in zip(authored_torso, torso_centers, torso_radii)
        ),
        candidate_module._make_regions(hybrid),
        start_cap_radius=caps[0],
        end_cap_radius=caps[1],
    )
    for authored_side, projected_side in zip(authored_legs, projected_legs):
        source_centers = tuple(
            _prepared_station_center(form, by_key, authored, projected)
            for authored, projected in zip(authored_side.sections, projected_side.sections)
        )
        source_radii = tuple(_prepared_radii(projected) for projected in projected_side.sections)
        expected_radii = [item.copy() for item in source_radii]
        expected_radii[1] = source_radii[1] * candidate_module.MIDPOINT_BELLY_FACTORS["thigh-midpoint"]
        expected_radii[2] = np.minimum(
            source_radii[2],
            candidate_module.JOINT_RADIUS_FACTOR * np.minimum(source_radii[1], source_radii[3]),
        )
        expected_radii[3] = source_radii[3] * candidate_module.MIDPOINT_BELLY_FACTORS["shin-midpoint"]
        expected_radii[4] = np.minimum(
            source_radii[4],
            candidate_module.JOINT_RADIUS_FACTOR
            * np.minimum(source_radii[3], feet[authored_side.side][0]["radii"]),
        )
        source_sections = tuple(
            {"center": center, "radii": radii, "source_radii": source}
            for center, radii, source in zip(source_centers, expected_radii, source_radii)
        )
        cup_radii = np.minimum(expected_chain.stations[0].radii, expected_radii[0])
        mu = candidate_module.HIP_CUP_SEAT_DEPTH_FRACTION * float(np.min(cup_radii))
        rim_center, seat_center, _ = _independent_endpoint_oracle(
            expected_chain, True, source_centers[0], mu,
        )
        up_axis = np.asarray(expected_chain.regions[0].first_basis.axial_axis, dtype=np.float64)
        neck_toward_thigh = candidate_module.FEMORAL_NECK_CENTER_FACTOR * (
            source_centers[0] - rim_center
        )
        neck_center = rim_center + up_axis * float(np.dot(neck_toward_thigh, up_axis))
        legs[authored_side.side] = {
            "sections": source_sections,
            "cup": (
                {"center": seat_center, "radii": cup_radii},
                {"center": rim_center, "radii": cup_radii * candidate_module.HIP_CUP_RIM_RADIUS_FACTOR},
                {"center": neck_center, "radii": cup_radii * candidate_module.FEMORAL_NECK_RADIUS_FACTOR},
            ),
        }
    return {
        "torso": tuple(
            {"center": center, "radii": radii, "source_radii": source}
            for center, radii, source in zip(torso_centers, torso_radii, torso_source_radii)
        ),
        "head": tuple(head),
        "arms": arms,
        "legs": legs,
        "feet": feet,
        "caps": caps,
        "torso_chain": expected_chain,
    }


def _expected_interface_specs(geometry: dict[str, object]):
    specs = [
        (
            ("torso", "head-neck"),
            (geometry["torso"][-1]["center"], geometry["head"][0]["center"]),
            (geometry["torso"][-1]["radii"], geometry["head"][0]["radii"]),
            candidate_module.INTERFACE_PAD,
        ),
    ]
    for side in ("left", "right"):
        parent = geometry["torso"][-1]
        child = geometry["arms"][side][0]
        chain = geometry["torso_chain"]
        shared_radii = np.minimum(parent["radii"], child["radii"])
        parent_point, _, _ = _independent_endpoint_oracle(
            chain,
            False,
            child["center"],
            candidate_module.ENDPOINT_CONNECTOR_DEPTH_FRACTION * float(np.min(shared_radii)),
        )
        specs.append(
            (
                ("torso", f"{side}-arm"),
                (parent_point, child["center"]),
                (shared_radii, shared_radii),
                candidate_module.INTERFACE_PAD,
            )
        )
    for side in ("left", "right"):
        specs.append(
            (
                ("torso", f"{side}-leg"),
                tuple(item["center"] for item in geometry["legs"][side]["cup"]),
                tuple(item["radii"] for item in geometry["legs"][side]["cup"]),
                candidate_module.INTERFACE_PAD,
            )
        )
    for side in ("left", "right"):
        specs.append(
            (
                (f"{side}-leg", f"{side}-foot"),
                (geometry["legs"][side]["sections"][-1]["center"],),
                (geometry["legs"][side]["sections"][-1]["radii"],),
                candidate_module.HOCK_INTERFACE_PAD,
            )
        )
    return tuple(specs)


class RegionalSurfaceCandidateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        command_prefix = inspection_command_prefix(shutil.which("cargo"))
        result = subprocess.run(
            [*command_prefix, "inspect-provisional-form", "--input", str(SOURCE_FORM)],
            cwd=REPO_ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        cls.prepared = json.loads(result.stdout)
        cls.candidate = candidate_module.build_regional_surface_candidate(cls.prepared, mesh_samples=None)
        cls.structural_temp = tempfile.TemporaryDirectory(
            prefix="ck-regional-arm-connectors-", dir="/tmp",
        )
        structural_root = Path(cls.structural_temp.name)
        candidate_table = json.loads(
            (EXPERIMENT_ROOT / "structural_profile_candidates.json").read_text(encoding="utf-8"),
        )
        base_source = json.loads(SOURCE_FORM.read_text(encoding="utf-8"))
        generated_sources = profile_generator.generate_sources(candidate_table, base_source)
        cls.structural_prepared = {}
        for profile_id, source in zip(profile_generator.ACTIVE_PROFILE_IDS, generated_sources):
            source_path = structural_root / f"{profile_id}.json"
            source_path.write_text(json.dumps(source), encoding="utf-8")
            prepared = subprocess.run(
                [*command_prefix, "inspect-provisional-form", "--input", str(source_path)],
                cwd=REPO_ROOT,
                check=True,
                capture_output=True,
                text=True,
            )
            cls.structural_prepared[profile_id] = json.loads(prepared.stdout)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.structural_temp.cleanup()

    def test_retains_seven_station_three_region_torso(self) -> None:
        candidate = self.candidate
        self.assertEqual(candidate.profile_id, "neutral-v0")
        self.assertEqual(candidate.metadata["format"], "creature-kernel.disposable-regional-surface-candidate.v3")
        self.assertEqual(
            tuple(station.name for station in candidate.stations),
            (
                "lower-pelvis", "upper-pelvis", "lower-abdomen", "waist-abdomen",
                "upper-abdomen", "lower-ribcage", "upper-ribcage-shoulder",
            ),
        )
        self.assertEqual(
            tuple((region.name, region.start_index, region.end_index) for region in candidate.regions),
            (("pelvis", 0, 2), ("abdominal-bridge", 2, 4), ("ribcage", 4, 6)),
        )
        self.assertIs(candidate.regions[0].end_basis, candidate.regions[1].start_basis)
        self.assertIs(candidate.regions[1].end_basis, candidate.regions[2].start_basis)
        self.assertTrue(candidate.metadata["proof"]["seven_ordered_torso_stations"])
        self.assertTrue(candidate.metadata["proof"]["three_explicit_regions"])
        source_radii = [np.asarray(item["source_radii"], dtype=np.float64) for item in candidate.metadata["torso"]["stations"]]
        expected = [
            source_radii[0] * np.asarray(candidate_module.TORSO_RADIUS_FACTORS["lower-pelvis"]),
            np.minimum(
                source_radii[1] * np.asarray(candidate_module.TORSO_RADIUS_FACTORS["upper-pelvis"]),
                source_radii[0] * np.asarray(candidate_module.TORSO_RADIUS_FACTORS["lower-pelvis"]),
            ),
            source_radii[2],
            np.maximum(source_radii[3], 0.88 * np.minimum(source_radii[2], source_radii[4])),
            source_radii[4],
            source_radii[5],
            np.minimum(source_radii[6], source_radii[5] * np.asarray((0.86, 0.82, 0.82))),
        ]
        self.assertTrue(np.allclose(np.asarray([station.radii for station in candidate.stations]), np.asarray(expected), rtol=0.0, atol=1.0e-15))

    def test_consumes_exact_full_section_route_inventory_once(self) -> None:
        candidate = self.candidate
        self.assertEqual(
            set(candidate.metadata),
            {
                "format", "source", "profile_id", "variant_source", "torso", "routes",
                "interfaces", "shoulder_controls", "proof",
            },
        )
        hybrid = candidate_module._load_hybrid()
        self.assertIsInstance(candidate.field, hybrid.FullSectionComposite)
        self.assertFalse(hasattr(hybrid, "_solve_ray_field_level"))
        for retired_name in (
            "CompositeHybridField", "BilateralPelvicSaddle", "PelvicSaddle", "PelvicCup",
            "CupCarve", "RootAttachment", "RootSweep", "RootKnot", "NamedRoot",
        ):
            self.assertFalse(hasattr(hybrid, retired_name), retired_name)
        self.assertEqual(
            tuple(route.route_name for route in candidate.routes),
            ("head-neck", "left-arm", "right-arm", "left-leg", "right-leg", "left-foot", "right-foot"),
        )
        head = candidate.routes[0]
        self.assertEqual(tuple(section.name for section in head.sections), (
            "neck-collar", "neck-upper", "head-base", "cranium-mid", "cranium-crown",
            "muzzle-root", "muzzle-mid", "muzzle-tip",
        ))
        self.assertEqual(
            tuple((item.name, item.from_section_index, item.to_section_index, item.route) for item in head.connections),
            (
                ("neck-collar-to-neck-upper", 0, 1, "vertical-neck-cranium"),
                ("neck-upper-to-head-base", 1, 2, "vertical-neck-cranium"),
                ("head-base-to-cranium-mid", 2, 3, "vertical-neck-cranium"),
                ("cranium-mid-to-cranium-crown", 3, 4, "vertical-neck-cranium"),
                ("cranium-mid-to-muzzle-root", 3, 5, "forward-muzzle"),
                ("muzzle-root-to-muzzle-mid", 5, 6, "forward-muzzle"),
                ("muzzle-mid-to-muzzle-tip", 6, 7, "forward-muzzle"),
            ),
        )
        self.assertEqual([len(route.sections) for route in candidate.routes[1:3]], [7, 7])
        self.assertEqual([len(route.connections) for route in candidate.routes[1:3]], [6, 6])
        for route in candidate.routes[1:3]:
            self.assertEqual(route.sections[0].name, "torso-arm-interface")
            self.assertEqual(route.sections[1].name, "upper-arm-start")
            self.assertEqual(route.connections[0].from_section_index, 0)
            self.assertEqual(route.connections[0].to_section_index, 1)
            self.assertEqual(route.connections[2].to_section_index, 3)
            self.assertEqual(route.connections[3].from_section_index, 3)
            self.assertEqual(route.sections[5].name, "wrist-transition")
            self.assertEqual(route.sections[6].name, "forearm-distal")
            self.assertEqual((route.connections[4].from_section_index, route.connections[4].to_section_index), (4, 5))
            self.assertEqual((route.connections[5].from_section_index, route.connections[5].to_section_index), (5, 6))
        for route in candidate.routes[3:5]:
            self.assertEqual(len(route.sections), 8)
            self.assertEqual(len(route.connections), 7)
            self.assertEqual(
                tuple(section.name for section in route.sections),
                ("pelvis-seat", "hip-cup-rim", "femoral-neck", "thigh-start", "thigh-midpoint", "knee", "shin-midpoint", "hock-endpoint"),
            )
            self.assertEqual(route.connections[0].to_section_index, 1)
            self.assertEqual((route.connections[2].from_section_index, route.connections[2].to_section_index), (2, 3))
            self.assertEqual(route.sections[5].name, "knee")
            self.assertEqual(route.sections[7].name, "hock-endpoint")
            self.assertEqual(route.endpoint_closures[0].name, f"{route.route_name}:hip-cup-rim-closure")
            self.assertEqual(route.endpoint_closures[0].center, route.sections[1].center)
            self.assertFalse(any(closure.center == route.sections[0].center for closure in route.endpoint_closures))
        self.assertEqual([len(route.sections) for route in candidate.routes[5:]], [3, 3])
        self.assertEqual([len(route.connections) for route in candidate.routes[5:]], [2, 2])
        self.assertIs(candidate.routes[3].sections[-1], candidate.routes[5].sections[0])
        self.assertIs(candidate.routes[4].sections[-1], candidate.routes[6].sections[0])
        self.assertTrue(candidate.metadata["routes"]["required_head_neck_sections"])
        self.assertTrue(candidate.metadata["routes"]["required_head_neck_connections"])
        self.assertTrue(candidate.metadata["routes"]["shared_interfaces"]["feet_use_leg_hock_identity"])
        self.assertEqual(candidate.metadata["routes"]["bilateral_arm_authored_sections"], [5, 5])
        self.assertEqual(candidate.metadata["routes"]["bilateral_arm_total_sections"], [7, 7])
        self.assertEqual(candidate.metadata["routes"]["bilateral_arm_transition_sections"], [["wrist-transition"], ["wrist-transition"]])
        self.assertEqual(candidate.metadata["routes"]["bilateral_leg_authored_sections"], [5, 5])
        self.assertEqual(candidate.metadata["routes"]["bilateral_leg_sections"], [8, 8])
        self.assertEqual(candidate.metadata["routes"]["binding_evidence_count"], 42)
        self.assertEqual(candidate.metadata["routes"]["arm_connector_method"], "analytic live terminal-constituent ellipsoid ray level")
        self.assertEqual(candidate.metadata["routes"]["hip_cup_chain_method"], "shared analytic live initial-constituent ray boundary/interior with profile-independent factors")
        self.assertEqual(candidate.metadata["routes"]["shared_interfaces"]["hip_cup_sections"], ["pelvis-seat", "hip-cup-rim", "femoral-neck"])
        self.assertEqual(
            candidate.metadata["interfaces"]["authority_source"],
            "interface samples plus side-matched authority-only shoulder controls",
        )
        metadata_text = json.dumps(candidate.metadata, sort_keys=True)
        self.assertNotIn("first crossing", metadata_text)
        self.assertNotIn("first-crossing", metadata_text)
        self.assertNotIn("full-chain", metadata_text)

    def test_source_bound_centers_radii_and_provenance_are_explicit(self) -> None:
        candidate = self.candidate
        expected_head_centers = (
            (0.0, 2.15 + candidate_module.NECK_COLLAR_LIFT_UP_RADIUS_FRACTION * candidate.routes[0].sections[0].radii[1], 0.0),
            (0.0, 2.55, 0.0), (0.0, 2.65, 0.0), (0.0, 3.05, 0.0),
            (0.0, 3.4, 0.0), (0.0, 2.9, 0.25), (0.0, 2.877, 0.595), (0.0, 2.875, 0.9375),
        )
        self.assertTrue(np.allclose([item.center for item in candidate.routes[0].sections], expected_head_centers, rtol=0.0, atol=1.0e-12))
        self.assertTrue(np.allclose(candidate.routes[0].sections[3].radii, (0.702, 0.6048, 0.5904), rtol=0.0, atol=1.0e-15))
        self.assertEqual(candidate.routes[1].sections[3].center, (-2.0, 2.0, 0.0))
        self.assertEqual(candidate.routes[3].sections[5].center, (-1.0, -2.0, 0.0))
        self.assertEqual(candidate.routes[3].sections[7].center, (-1.0, -3.0, 1.0))
        self.assertTrue(np.allclose(candidate.routes[5].sections[1].center, (-1.0, -3.2, 1.36), rtol=0.0, atol=1.0e-12))
        for route in candidate.routes:
            for section in route.sections:
                self.assertTrue(section.semantic_key.startswith("section:"))
                if section.source_index is None:
                    self.assertIn(section.name, {"torso-arm-interface", "wrist-transition", "pelvis-seat", "hip-cup-rim", "femoral-neck"})
                    self.assertTrue(section.source_key.startswith("derived-"))
                else:
                    self.assertTrue(section.source_key.startswith("source-route:"))
            for closure in route.endpoint_closures:
                self.assertTrue(closure.source_key)
                self.assertTrue(np.all(np.isfinite(closure.center)))
                self.assertTrue(np.all(np.asarray(closure.radii) > 0.0))
        self.assertTrue(candidate.metadata["proof"]["explicit_source_derived_endpoint_closures"])
        self.assertTrue(candidate.metadata["proof"]["finite_interface_authorities"])
        form = candidate_module._as_form(self.prepared)
        authored_thigh = form.authored_leg_profile.sides[0].sections[0]
        thigh_start = candidate.routes[3].sections[3]
        self.assertEqual(thigh_start.source_index, authored_thigh.section_index)
        self.assertEqual(thigh_start.source_key, candidate_module._source_route_key(authored_thigh.owner, "left-leg:thigh-start"))
        self.assertEqual(thigh_start.semantic_key, f"section:left-leg:thigh-start:{candidate_module._key_text(authored_thigh.owner)}")

    def test_prepared_parser_rejects_nonidentity_frames_and_nonaxial_limb_landmarks(self) -> None:
        parser = candidate_module._load_surface_preview()

        def change_frame(raw):
            frame = next(
                item for item in raw["authored_frames"]
                if item["role"] == parser.ARM_PROFILE_CONTROL_FRAME_ROLE
            )
            frame["transform"]["translation"][0] = 0.125

        def change_rotation(raw):
            frame = next(
                item for item in raw["authored_frames"]
                if item["role"] == parser.LEG_PROFILE_CONTROL_FRAME_ROLE
            )
            frame["transform"]["rotation_xyzw"] = [0.0, 0.0, 0.125, 1.0]

        def change_arm_x(raw):
            landmark = next(
                item for item in raw["authored_landmarks"]
                if item["role"].startswith(parser.ARM_PROFILE_LANDMARK_PREFIX)
            )
            landmark["position"][0] = 0.125

        def change_leg_z(raw):
            landmark = next(
                item for item in raw["authored_landmarks"]
                if item["role"].startswith(parser.LEG_PROFILE_LANDMARK_PREFIX)
            )
            landmark["position"][2] = 0.125

        for label, mutation, message in (
            ("frame-translation", change_frame, "must be an identity control frame"),
            ("frame-rotation", change_rotation, "must be an identity control frame"),
            ("arm-x", change_arm_x, "arm profile landmark must be source-local on its arm axis"),
            ("leg-z", change_leg_z, "leg profile landmark must be source-local on its leg axis"),
        ):
            with self.subTest(label=label):
                malformed = copy.deepcopy(self.prepared)
                mutation(malformed)
                with self.assertRaisesRegex(parser.PreviewError, message):
                    parser.validate_envelope(malformed)

    def test_section_station_rejects_equal_but_wrong_authored_and_projected_indices(self) -> None:
        form = candidate_module._as_form(self.prepared)
        variant_index, descriptors, _ = candidate_module._variant(form, "neutral-v0")
        authored = form.authored_head_neck_profile.sections[0]
        projected = form.variant_head_neck_profiles[variant_index].sections[0]
        malformed_authored = replace(authored, section_index=1)
        malformed_projected = replace(projected, source_section_index=1)
        by_key = candidate_module._descriptor_map(descriptors, form.source["namespace"])
        frame_by_key = {(frame.owner, frame.role): frame for frame in form.authored_frames}
        module = candidate_module._load_surface_preview()
        with self.assertRaisesRegex(candidate_module.RegionalSurfaceCandidateError, "lost source section order"):
            candidate_module._section_station(
                form,
                by_key,
                frame_by_key,
                malformed_authored,
                malformed_projected,
                "head-neck",
                0,
                "neck",
                module.HEAD_NECK_PROFILE_FRAME_ROLE,
                module,
                candidate_module._load_hybrid(),
            )

    def test_arm_connector_derivation_rejects_wrong_live_operands_and_identity_clones(self) -> None:
        hybrid = candidate_module._load_hybrid()
        candidate = self.candidate
        form = candidate_module._as_form(self.prepared)
        chain = candidate.chain
        parent = chain.stations[-1]
        region = chain.regions[-1]
        child = candidate.routes[1].sections[1]
        torso_key = form.authored_torso_profile.sections[-1].owner
        left_arm_key = form.authored_arm_profile.sides[0].sections[0].owner
        right_arm_key = form.authored_arm_profile.sides[1].sections[0].owner

        def derive(
            parent_operand=parent,
            region_operand=region,
            basis_operand=region.last_basis,
            child_operand=child,
            torso_owner=torso_key,
            arm_owner=left_arm_key,
            route_name="left-arm",
            chain_operand=chain,
        ):
            return candidate_module._derive_torso_arm_connector(
                hybrid,
                chain_operand,
                parent_operand,
                region_operand,
                basis_operand,
                child_operand,
                torso_owner,
                arm_owner,
                route_name,
            )

        connector, evidence, context = derive()
        self.assertTrue(np.array_equal(np.asarray(connector.center), np.asarray(candidate.routes[1].sections[0].center)))
        self.assertIn("finite_open_overlap_certificate", candidate.metadata["routes"]["routes"][1]["sections"][0])
        self.assertNotIn("finite_open_overlap_certificate", evidence)

        cases = (
            ("nonterminal-station", {"parent_operand": chain.stations[-2]}, "requires terminal torso"),
            ("equal-station-clone", {"parent_operand": replace(parent)}, "exact live terminal station"),
            ("wrong-radii-station-clone", {"parent_operand": replace(parent, radii=tuple(value * 0.9 for value in parent.radii))}, "exact live terminal station"),
            ("nonterminal-region", {"region_operand": chain.regions[-2], "basis_operand": chain.regions[-2].last_basis}, "exact live terminal region"),
            ("equal-region-clone", {"region_operand": replace(region), "basis_operand": replace(region).last_basis}, "exact live terminal region"),
            ("equal-basis-clone", {"basis_operand": replace(region.last_basis)}, "exact live terminal region basis"),
            ("wrong-torso-owner", {"torso_owner": form.authored_torso_profile.sections[0].owner}, "wrong terminal torso owner"),
            ("wrong-arm-owner", {"arm_owner": right_arm_key}, "wrong upper-arm source binding"),
            ("wrong-side-route", {"route_name": "right-arm"}, "wrong upper-arm source binding"),
            ("aggregate-parent", {"chain_operand": candidate.field}, "live axial mass chain"),
            ("other-chain", {"chain_operand": candidate_module.build_regional_surface_candidate(self.prepared, mesh_samples=None).chain}, "exact live terminal station"),
        )
        for label, kwargs, message in cases:
            with self.subTest(label=label), self.assertRaisesRegex(
                (candidate_module.RegionalSurfaceCandidateError, hybrid.RegionalHybridSurfaceError),
                message,
            ):
                derive(**kwargs)

        wrong_child_source = replace(child, source_key="source-route:wrong-owner")
        with self.assertRaisesRegex(candidate_module.RegionalSurfaceCandidateError, "wrong upper-arm source binding"):
            derive(child_operand=wrong_child_source)

        with mock.patch.object(
            hybrid.AxialMassChain,
            "operation_trace",
            return_value=hybrid._leaf_trace(-0.1, "wrong-trace"),
        ):
            with self.assertRaisesRegex(candidate_module.RegionalSurfaceCandidateError, "not consumed by the live endpoint constituent"):
                derive()

        route = candidate.routes[1]
        live_context = {
            "constituent": chain._terminal_constituent(parent, region, region.last_basis),
            "connector": route.sections[0],
            "child": route.sections[1],
            "evidence": {},
        }
        candidate_module._certify_torso_arm_overlap(hybrid, chain, route, live_context)
        self.assertEqual(live_context["evidence"]["finite_open_overlap_certificate"]["kind"], "finite-open-overlap")
        for label, key, replacement in (
            ("wrong-connector-radii", "connector", replace(route.sections[0], radii=tuple(value * 0.9 for value in route.sections[0].radii))),
            ("wrong-child-radii", "child", replace(route.sections[1], radii=tuple(value * 0.9 for value in route.sections[1].radii))),
        ):
            wrong_context = dict(live_context)
            wrong_context[key] = replacement
            wrong_context["evidence"] = {}
            with self.subTest(label=label), self.assertRaisesRegex(candidate_module.RegionalSurfaceCandidateError, "wrong connector or child object identity"):
                candidate_module._certify_torso_arm_overlap(hybrid, chain, route, wrong_context)

    def test_pelvis_hip_cup_derivation_rejects_wrong_live_operands_and_identity_clones(self) -> None:
        hybrid = candidate_module._load_hybrid()
        form = candidate_module._as_form(self.prepared)
        candidate = self.candidate
        chain = candidate.chain
        route = candidate.routes[3]
        parent = chain.stations[0]
        region = chain.regions[0]
        thigh = route.sections[3]
        pelvis_key = form.authored_torso_profile.sections[0].owner
        thigh_key = form.authored_leg_profile.sides[0].sections[0].owner
        right_thigh_key = form.authored_leg_profile.sides[1].sections[0].owner

        def derive(
            parent_operand=parent,
            region_operand=region,
            basis_operand=region.first_basis,
            thigh_operand=thigh,
            pelvis_owner=pelvis_key,
            thigh_owner=thigh_key,
            route_name="left-leg",
            chain_operand=chain,
        ):
            return candidate_module._derive_pelvis_hip_cup_chain(
                hybrid, chain_operand, parent_operand, region_operand, basis_operand,
                thigh_operand, pelvis_owner, thigh_owner, route_name,
            )

        sections, evidence, context = derive()
        self.assertEqual(tuple(item.name for item in sections), ("pelvis-seat", "hip-cup-rim", "femoral-neck"))
        self.assertTrue(all(item.source_index is None and item.source_key.startswith("derived-") for item in sections))
        self.assertLess(chain.evaluate(sections[0].center), 0.0)
        self.assertAlmostEqual(float(context["constituent"].evaluate(sections[1].center)), 0.0, places=12)
        self.assertTrue(np.all(np.asarray(sections[2].radii) < np.asarray(sections[1].radii)))
        self.assertEqual(tuple(item["provenance"]["kind"] for item in evidence), ("pelvis+thigh",) * 3)
        live_context = {
            **context,
            "seat": route.sections[0],
            "rim": route.sections[1],
            "neck": route.sections[2],
            "thigh": route.sections[3],
            "evidence": [{}, {}, {}],
        }
        candidate_module._certify_pelvis_leg_overlap(hybrid, chain, route, live_context)
        certificate = live_context["evidence"][0]["finite_open_overlap_certificate"]
        self.assertEqual(certificate["kind"], "finite-open-overlap-through-named-hip-cup-chain")
        self.assertEqual(len(certificate["adjacent_cup_spans"]), 3)
        self.assertTrue(all(item["max_value"] < 0.0 for item in certificate["adjacent_cup_spans"]))

        cases = (
            ("noninitial-station", {"parent_operand": chain.stations[1]}, "requires lower-pelvis"),
            ("equal-station-clone", {"parent_operand": replace(parent)}, "exact live initial station"),
            ("noninitial-region", {"region_operand": chain.regions[1], "basis_operand": chain.regions[1].first_basis}, "exact live initial region"),
            ("equal-region-clone", {"region_operand": replace(region), "basis_operand": replace(region).first_basis}, "exact live initial region"),
            ("equal-basis-clone", {"basis_operand": replace(region.first_basis)}, "exact live initial region basis"),
            ("wrong-pelvis-owner", {"pelvis_owner": form.authored_torso_profile.sections[2].owner}, "wrong lower-pelvis owner"),
            ("wrong-thigh-owner", {"thigh_owner": right_thigh_key}, "wrong thigh-start source binding"),
            ("wrong-side-route", {"route_name": "right-leg"}, "wrong thigh-start source binding"),
            ("aggregate-parent", {"chain_operand": candidate.field}, "live axial mass chain"),
        )
        for label, kwargs, message in cases:
            with self.subTest(label=label), self.assertRaisesRegex(
                (candidate_module.RegionalSurfaceCandidateError, hybrid.RegionalHybridSurfaceError), message,
            ):
                derive(**kwargs)
        with self.assertRaisesRegex(candidate_module.RegionalSurfaceCandidateError, "wrong thigh-start source binding"):
            derive(thigh_operand=replace(thigh, source_key="source-route:wrong"))

    @unittest.skip("legacy two-section pelvis interface test retained outside the bounded hip-cup slice")
    def test_pelvis_leg_connector_rejects_wrong_live_operands_and_identity_clones(self) -> None:
        hybrid = candidate_module._load_hybrid()
        candidate = self.candidate
        form = candidate_module._as_form(self.prepared)
        chain = candidate.chain
        route = candidate.routes[3]
        parent = chain.stations[0]
        region = chain.regions[0]
        hip = route.sections[1]
        thigh = route.sections[2]
        pelvis_key = form.authored_torso_profile.sections[0].owner
        thigh_key = form.authored_leg_profile.sides[0].sections[0].owner
        right_thigh_key = form.authored_leg_profile.sides[1].sections[0].owner

        def derive(
            parent_operand=parent,
            region_operand=region,
            basis_operand=region.first_basis,
            hip_operand=hip,
            thigh_operand=thigh,
            pelvis_owner=pelvis_key,
            thigh_owner=thigh_key,
            route_name="left-leg",
            chain_operand=chain,
        ):
            return candidate_module._derive_pelvis_leg_connector(
                hybrid,
                chain_operand,
                parent_operand,
                region_operand,
                basis_operand,
                hip_operand,
                thigh_operand,
                pelvis_owner,
                thigh_owner,
                route_name,
            )

        connector, evidence, _ = derive()
        self.assertTrue(np.array_equal(np.asarray(connector.center), np.asarray(route.sections[0].center)))
        self.assertNotIn("finite_open_overlap_certificate", evidence)
        cases = (
            ("noninitial-station", {"parent_operand": chain.stations[1]}, "requires lower-pelvis"),
            ("equal-station-clone", {"parent_operand": replace(parent)}, "exact live initial station"),
            ("wrong-radii-station-clone", {"parent_operand": replace(parent, radii=tuple(value * 0.9 for value in parent.radii))}, "exact live initial station"),
            ("noninitial-region", {"region_operand": chain.regions[1], "basis_operand": chain.regions[1].first_basis}, "exact live initial region"),
            ("equal-region-clone", {"region_operand": replace(region), "basis_operand": replace(region).first_basis}, "exact live initial region"),
            ("equal-basis-clone", {"basis_operand": replace(region.first_basis)}, "exact live initial region basis"),
            ("wrong-pelvis-owner", {"pelvis_owner": form.authored_torso_profile.sections[2].owner}, "wrong lower-pelvis owner"),
            ("wrong-thigh-owner", {"thigh_owner": right_thigh_key}, "wrong derived hip binding"),
            ("wrong-side-route", {"route_name": "right-leg"}, "wrong derived hip binding"),
            ("aggregate-parent", {"chain_operand": candidate.field}, "live axial mass chain"),
        )
        for label, kwargs, message in cases:
            with self.subTest(label=label), self.assertRaisesRegex(
                (candidate_module.RegionalSurfaceCandidateError, hybrid.RegionalHybridSurfaceError),
                message,
            ):
                derive(**kwargs)
        with self.assertRaisesRegex(candidate_module.RegionalSurfaceCandidateError, "wrong derived hip binding"):
            derive(hip_operand=replace(hip, source_key="derived-hip-interface:wrong"))
        with self.assertRaisesRegex(candidate_module.RegionalSurfaceCandidateError, "wrong thigh-start source binding"):
            derive(thigh_operand=replace(thigh, source_key="source-route:wrong"))
        with mock.patch.object(
            hybrid.AxialMassChain,
            "operation_trace",
            return_value=hybrid._leaf_trace(-0.1, "wrong-trace"),
        ):
            with self.assertRaisesRegex(candidate_module.RegionalSurfaceCandidateError, "not consumed by the live endpoint constituent"):
                derive()

        live_context = {
            "constituent": chain._initial_constituent(parent, region, region.first_basis),
            "connector": route.sections[0],
            "hip": route.sections[1],
            "thigh": route.sections[2],
            "evidence": {},
        }
        candidate_module._certify_pelvis_leg_overlap(hybrid, chain, route, live_context)
        self.assertEqual(
            live_context["evidence"]["finite_open_overlap_certificate"]["kind"],
            "finite-open-overlap-through-thigh-start",
        )
        for label, key, replacement in (
            ("wrong-connector-radii", "connector", replace(route.sections[0], radii=tuple(value * 0.9 for value in route.sections[0].radii))),
            ("wrong-hip-radii", "hip", replace(route.sections[1], radii=tuple(value * 0.9 for value in route.sections[1].radii))),
            ("wrong-thigh-radii", "thigh", replace(route.sections[2], radii=tuple(value * 0.9 for value in route.sections[2].radii))),
        ):
            wrong_context = dict(live_context)
            wrong_context[key] = replacement
            wrong_context["evidence"] = {}
            with self.subTest(label=label), self.assertRaisesRegex(candidate_module.RegionalSurfaceCandidateError, "wrong connector, hip or thigh object identity"):
                candidate_module._certify_pelvis_leg_overlap(hybrid, chain, route, wrong_context)

    def test_candidate_derivations_reconstruct_source_values_for_every_variant(self) -> None:
        form = candidate_module._as_form(self.prepared)
        for profile_id, _, _ in form.variants:
            candidate = candidate_module.build_regional_surface_candidate(form, profile_id, mesh_samples=None)
            expected = _expected_variant_geometry(form, profile_id)
            for station, source in zip(candidate.stations, expected["torso"]):
                self.assertTrue(np.array_equal(np.asarray(station.center), source["center"]), station.name)
                self.assertTrue(np.array_equal(np.asarray(station.radii), source["radii"]), station.name)
            for station, source in zip(candidate.routes[0].sections, expected["head"]):
                self.assertTrue(np.array_equal(np.asarray(station.center), source["center"]), station.name)
                self.assertTrue(np.array_equal(np.asarray(station.radii), source["radii"]), station.name)
            self.assertEqual(len(candidate.routes[1:3]), 2)
            authored_arm_by_side = {item.side: item for item in form.authored_arm_profile.sides}
            for side_index, side in enumerate(("left", "right")):
                route = candidate.routes[1 + side_index]
                self.assertEqual(route.route_name, f"{side}-arm")
                self.assertEqual(len(route.sections), 7)
                self.assertEqual(len(route.connections), 6)
                connector = route.sections[0]
                child = route.sections[1]
                expected_connector_radii = np.minimum(
                    expected["torso"][-1]["radii"], expected["arms"][side][0]["radii"],
                )
                expected_chain = expected["torso_chain"]
                mu = candidate_module.ENDPOINT_CONNECTOR_DEPTH_FRACTION * float(np.min(expected_connector_radii))
                expected_boundary, expected_center, expected_rho = _independent_endpoint_oracle(
                    expected_chain,
                    False,
                    expected["arms"][side][0]["center"],
                    mu,
                )
                self.assertIsNone(connector.source_index)
                self.assertTrue(np.array_equal(np.asarray(connector.radii), expected_connector_radii))
                self.assertTrue(np.array_equal(np.asarray(connector.center), expected_center))
                self.assertAlmostEqual(float(candidate.chain.evaluate(connector.center)), -mu, places=12)
                self.assertEqual(child.name, "upper-arm-start")
                authored_sections = tuple(authored_arm_by_side[side].sections)
                self.assertEqual(len(authored_sections), 5)
                self.assertEqual(len(expected["arms"][side]), 5)
                authored_route_indices = (1, 2, 3, 4, 6)
                for source_index, route_index in enumerate(authored_route_indices):
                    station = route.sections[route_index]
                    source = expected["arms"][side][source_index]
                    authored = authored_sections[source_index]
                    self.assertEqual(station.source_index, source_index)
                    self.assertTrue(np.array_equal(np.asarray(station.center), source["center"]), f"{route.route_name}:{station.name}")
                    self.assertTrue(np.array_equal(np.asarray(station.radii), source["radii"]), f"{route.route_name}:{station.name}")
                    self.assertEqual(station.source_key, candidate_module._source_route_key(authored.owner, f"{route.route_name}:{authored.name}"))
                    self.assertEqual(station.semantic_key, f"section:{route.route_name}:{authored.name}:{candidate_module._key_text(authored.owner)}")
                wrist = route.sections[5]
                hand_closure = route.endpoint_closures[-1]
                M = np.asarray(route.sections[4].center, dtype=np.float64)
                D = np.asarray(route.sections[6].center, dtype=np.float64)
                Rd = np.asarray(route.sections[6].radii, dtype=np.float64)
                H = np.asarray(hand_closure.center, dtype=np.float64)
                Rh = np.asarray(hand_closure.radii, dtype=np.float64)
                u = (D - M) / np.linalg.norm(D - M)
                q = max(Rd[1] / Rh[1], Rd[2] / Rh[2])
                s = math.sqrt(1.0 - q * q)
                W = H - u * Rh[0] * s
                Rw = np.minimum(Rd, Rh)
                lambda_value = float(np.dot(W - M, u) / np.linalg.norm(D - M))
                self.assertTrue(np.array_equal(H, D))
                self.assertTrue(np.allclose(wrist.center, W, rtol=0.0, atol=1.0e-15))
                self.assertTrue(np.allclose(wrist.radii, Rw, rtol=0.0, atol=1.0e-15))
                self.assertAlmostEqual(wrist.position, 3.0 + lambda_value, places=15)
                self.assertIsNone(wrist.source_index)
                self.assertTrue(wrist.source_key.startswith("derived-wrist-transition:forearm="))
                wrist_evidence = next(
                    item for item in candidate.binding_evidence if item["semantic_key"] == wrist.semantic_key
                )
                self.assertEqual(wrist_evidence["provenance"]["kind"], "forearm+hand")
                self.assertEqual(wrist_evidence["provenance"]["forearm"], candidate_module._key_json(authored_sections[4].owner))
                self.assertEqual(wrist_evidence["provenance"]["hand"], candidate_module._key_json((form.source["namespace"], (side,), "part", "hand")))
                record = next(item for item in candidate.metadata["routes"]["routes"] if item["name"] == route.route_name)["sections"][0]
                self.assertTrue(np.array_equal(np.asarray(record["constituent_boundary_center"]), expected_boundary))
                self.assertEqual(record["mu"], mu)
                self.assertEqual(record["rho"], expected_rho)
                self.assertEqual(record["constituent_field_scale"], min(*expected_chain.stations[-1].radii, expected_chain.end_cap_radius))
            for side_index, side in enumerate(("left", "right")):
                route = candidate.routes[3 + side_index]
                self.assertEqual(route.route_name, f"{side}-leg")
                self.assertEqual(len(route.sections), 8)
                self.assertEqual(len(route.connections), 7)
                leg_expected = expected["legs"][side]
                for section, expected_section in zip(route.sections[:3], leg_expected["cup"]):
                    self.assertIsNone(section.source_index)
                    self.assertTrue(np.array_equal(np.asarray(section.center), expected_section["center"]))
                    self.assertTrue(np.array_equal(np.asarray(section.radii), expected_section["radii"]))
                self.assertEqual((route.sections[3].name, route.sections[3].source_index), ("thigh-start", 0))
                self.assertEqual(len(leg_expected["sections"]), 5)
                for source_index in range(5):
                    station = route.sections[source_index + 3]
                    source = leg_expected["sections"][source_index]
                    self.assertEqual(station.source_index, source_index)
                    self.assertTrue(np.array_equal(np.asarray(station.center), source["center"]), f"{route.route_name}:{station.name}")
                    self.assertTrue(np.array_equal(np.asarray(station.radii), source["radii"]), f"{route.route_name}:{station.name}")
                record = next(item for item in candidate.metadata["routes"]["routes"] if item["name"] == route.route_name)["sections"][1]
                self.assertTrue(np.array_equal(np.asarray(record["constituent_boundary_center"]), leg_expected["cup"][1]["center"]))
                self.assertEqual(record["mu"], candidate_module.HIP_CUP_SEAT_DEPTH_FRACTION * float(np.min(leg_expected["cup"][0]["radii"])))
                self.assertGreater(record["rho"], 0.0)
                self.assertEqual(record["constituent_field_scale"], min(*expected["torso_chain"].stations[0].radii, expected["torso_chain"].start_cap_radius))
            for route in candidate.routes[5:]:
                side = route.route_name.split("-", 1)[0]
                for source_index, (station, source) in enumerate(zip(route.sections[1:], expected["feet"][side])):
                    self.assertEqual(station.source_index, source_index)
                    self.assertTrue(np.array_equal(np.asarray(station.center), source["center"]), f"{route.route_name}:{station.name}")
                    self.assertTrue(np.array_equal(np.asarray(station.radii), source["radii"]), f"{route.route_name}:{station.name}")
                self.assertIs(route.sections[0], candidate.routes[3 if side == "left" else 4].sections[-1])
            self.assertTrue(np.array_equal(np.asarray(candidate.routes[1].sections[2].radii), np.asarray(candidate.routes[2].sections[2].radii)))
            for cup_index in range(3):
                self.assertTrue(np.array_equal(np.asarray(candidate.routes[3].sections[cup_index].radii), np.asarray(candidate.routes[4].sections[cup_index].radii)))
            self.assertEqual((candidate.chain.start_cap_radius, candidate.chain.end_cap_radius), expected["caps"])
            self.assertEqual(len(candidate.binding_evidence), 53)
            binding_keys = tuple(record["semantic_key"] for record in candidate.binding_evidence)
            self.assertEqual(len(set(binding_keys)), 53)
            expected_keys = [station.semantic_key for station in candidate.stations]
            seen_route_objects = set()
            for route in candidate.routes:
                for station in route.sections:
                    if id(station) not in seen_route_objects:
                        seen_route_objects.add(id(station))
                        expected_keys.append(station.semantic_key)
            expected_keys.extend(control.semantic_key for control in candidate.controls)
            self.assertEqual(len(expected_keys), 53)
            self.assertEqual(set(binding_keys), set(expected_keys))

    def test_interface_authorities_include_exact_side_controls_without_changing_k(self) -> None:
        expected_relations = (
            ("torso", "head-neck"), ("torso", "left-arm"), ("torso", "right-arm"),
            ("torso", "left-leg"), ("torso", "right-leg"),
            ("left-leg", "left-foot"), ("right-leg", "right-foot"),
        )
        form = candidate_module._as_form(self.prepared)
        for profile_id, _, _ in form.variants:
            candidate = candidate_module.build_regional_surface_candidate(form, profile_id, mesh_samples=None)
            geometry = _expected_variant_geometry(form, profile_id)
            expected_specs = _expected_interface_specs(geometry)
            patches = {(patch.parent_name, patch.child_name): patch for patch in candidate.interfaces}
            records = {
                (record["parent"], record["child"]): record
                for record in candidate.metadata["interfaces"]["patches"]
            }
            self.assertEqual(tuple(patches), tuple(sorted(expected_relations, key=lambda item: f"interface:{item[0]}->{item[1]}")))
            for relation, raw_points, raw_radii, pad in expected_specs:
                patch = patches[relation]
                points = np.asarray(raw_points, dtype=np.float64)
                point_radii = np.asarray(raw_radii, dtype=np.float64)
                padding = pad * np.max(point_radii, axis=0)
                lower = np.min(points, axis=0) - padding
                upper = np.max(points, axis=0) + padding
                expected_controls = ()
                if relation[0] == "torso" and relation[1].endswith("-arm"):
                    side = relation[1].split("-", 1)[0]
                    expected_controls = candidate_module._side_matched_shoulder_controls(candidate.controls, side)
                    for control in expected_controls:
                        lower = np.minimum(lower, np.asarray(control.center) - np.asarray(control.radii))
                        upper = np.maximum(upper, np.asarray(control.center) + np.asarray(control.radii))
                self.assertTrue(np.array_equal(np.asarray(patch.authority.center), (lower + upper) * 0.5), f"{profile_id}:{relation}")
                self.assertTrue(np.array_equal(np.asarray(patch.authority.radii), (upper - lower) * 0.5), f"{profile_id}:{relation}")
                self.assertEqual(patch.blend_radius, candidate_module.INTERFACE_BLEND_FRACTION * np.min(point_radii))
                self.assertTrue(all(patch.authority.contains(point) for point in points), f"{profile_id}:{relation}")
                self.assertTrue(all(patch.authority.contains(control.center) for control in expected_controls))
                record = records[relation]["authority"]
                self.assertTrue(np.array_equal(np.asarray(record["points"]), points))
                self.assertTrue(np.array_equal(np.asarray(record["interface_radii"]), point_radii))
                self.assertEqual(record["pad"], pad)
                self.assertTrue(record["contains_all_points"])
                expected_authority_controls = []
                for control in expected_controls:
                    side = control.name.split("-", 1)[0]
                    role = "form_shoulder_peak" if control.name.endswith("shoulder-peak") else "form_axilla"
                    owner = candidate_module._key_json((form.source["namespace"], (side,), "part", "upper_arm"))
                    expected_authority_controls.append({
                        "name": control.name,
                        "center": list(control.center),
                        "radii": list(control.radii),
                        "semantic_key": control.semantic_key,
                        "source_key": control.source_key,
                        "canonical_source_key": control.source_key,
                        "namespace": form.source["namespace"],
                        "side": side,
                        "owner": owner,
                        "role": role,
                        "frame": {"owner": owner, "role": "form_shoulder_control"},
                    })
                self.assertEqual(record["authority_controls"], expected_authority_controls)

        candidate = self.candidate
        patches = {(patch.parent_name, patch.child_name): patch for patch in candidate.interfaces}
        head_patch = patches[("torso", "head-neck")]
        self.assertFalse(head_patch.authority.contains(candidate.routes[0].sections[4].center))
        self.assertFalse(head_patch.authority.contains(candidate.routes[0].sections[7].center))
        for side in ("left", "right"):
            shoulder_patch = patches[("torso", f"{side}-arm")]
            arm = next(route for route in candidate.routes if route.route_name == f"{side}-arm")
            self.assertTrue(shoulder_patch.authority.contains(arm.sections[1].center))
            self.assertFalse(shoulder_patch.authority.contains(arm.sections[3].center))
            self.assertFalse(shoulder_patch.authority.contains(arm.endpoint_closures[-1].center))
            hip_patch = patches[("torso", f"{side}-leg")]
            leg = next(route for route in candidate.routes if route.route_name == f"{side}-leg")
            self.assertTrue(hip_patch.authority.contains(leg.sections[0].center))
            self.assertTrue(hip_patch.authority.contains(leg.sections[1].center))
            self.assertTrue(hip_patch.authority.contains(leg.sections[2].center))
            self.assertFalse(hip_patch.authority.contains(leg.sections[5].center))
            self.assertFalse(hip_patch.authority.contains(leg.sections[7].center))
            hock_patch = patches[(f"{side}-leg", f"{side}-foot")]
            self.assertTrue(hock_patch.authority.contains(leg.sections[7].center))
            foot = next(route for route in candidate.routes if route.route_name == f"{side}-foot")
            self.assertFalse(hock_patch.authority.contains(foot.sections[-1].center))
            self.assertTrue(hock_patch.validate_outside_hard_min())
        self.assertFalse(any(isinstance(item.field, type(candidate.controls[0])) for item in candidate.field.attachments))
        self.assertFalse(any(component in candidate.controls for component in candidate.field.components))
        self.assertFalse(any(patch.parent in candidate.controls or patch.child in candidate.controls for patch in candidate.interfaces))

    def test_wrong_side_and_cloned_shoulder_authority_bindings_fail_closed(self) -> None:
        controls = self.candidate.controls
        hybrid = candidate_module._load_hybrid()
        with self.assertRaisesRegex(candidate_module.RegionalSurfaceCandidateError, "order or identity"):
            candidate_module._side_matched_shoulder_controls(
                (controls[2], controls[1], controls[0], controls[3]), "left",
            )

        cloned_right_peak = hybrid.SectionControl(
            "right-shoulder-peak",
            controls[0].center,
            controls[0].radii,
            "control:right-shoulder-peak",
            controls[0].source_key,
        )
        with self.assertRaisesRegex(candidate_module.RegionalSurfaceCandidateError, "cloned bindings|wrong side"):
            candidate_module._side_matched_shoulder_controls(
                (controls[0], controls[1], cloned_right_peak, controls[3]), "right",
            )

        def forged_control(source_key: str):
            return hybrid.SectionControl(
                controls[0].name,
                controls[0].center,
                controls[0].radii,
                controls[0].semantic_key,
                source_key,
            )

        canonical_prefix = candidate_module._SHOULDER_CONTROL_SOURCE_PREFIX
        original_payload = json.loads(controls[0].source_key.removeprefix(canonical_prefix))
        malformed_payload = copy.deepcopy(original_payload)
        malformed_payload["owner"]["role"] = "forearm"
        wrong_owner_key = canonical_prefix + json.dumps(malformed_payload, sort_keys=True, separators=(",", ":"))
        malformed_payload = copy.deepcopy(original_payload)
        malformed_payload["frame"]["role"] = "form_arm_profile_control"
        wrong_frame_key = canonical_prefix + json.dumps(malformed_payload, sort_keys=True, separators=(",", ":"))
        forged_bindings = (
            ("wrong-role", candidate_module._canonical_shoulder_control_source_key("main", "left", "form_axilla")),
            ("wrong-namespace", candidate_module._canonical_shoulder_control_source_key("forged", "left", "form_shoulder_peak")),
            ("wrong-side", candidate_module._canonical_shoulder_control_source_key("main", "right", "form_shoulder_peak")),
            ("wrong-owner", wrong_owner_key),
            ("wrong-frame", wrong_frame_key),
        )
        for label, source_key in forged_bindings:
            with self.subTest(binding=label), self.assertRaises(candidate_module.RegionalSurfaceCandidateError):
                candidate_module._side_matched_shoulder_controls(
                    (forged_control(source_key), controls[1], controls[2], controls[3]), "left",
                )

        for side in ("left", "right"):
            matched = candidate_module._side_matched_shoulder_controls(controls, side)
            patch = next(
                item for item in self.candidate.interfaces
                if (item.parent_name, item.child_name) == ("torso", f"{side}-arm")
            )
            arm = next(route for route in self.candidate.routes if route.route_name == f"{side}-arm")
            points, radii = candidate_module._torso_arm_interface_samples(
                hybrid, self.candidate.chain, arm,
            )
            _, original_k, _ = candidate_module._interface_authority(
                hybrid, f"torso->{side}-arm", points, radii, candidate_module.INTERFACE_PAD,
            )
            self.assertEqual(patch.blend_radius, original_k)
            self.assertEqual(tuple(control.name for control in matched), (f"{side}-shoulder-peak", f"{side}-axilla"))

    def test_interface_composition_registration_is_canonical_and_traces_reconstruct(self) -> None:
        candidate = self.candidate
        attachments = tuple(candidate.field.attachments)
        patches = tuple(candidate.field.interfaces)
        points = np.asarray((
            candidate.stations[3].center,
            candidate.routes[0].sections[6].center,
            candidate.routes[1].sections[0].center,
            candidate.routes[3].sections[0].center,
            candidate.routes[5].sections[1].center,
        ))
        baseline = candidate.field.evaluate(points)
        baseline_trace = candidate.field.operation_trace(points[1])
        for attachment_order, patch_order in (
            (tuple(reversed(attachments)), tuple(reversed(patches))),
            (attachments[2:] + attachments[:2], patches[3:] + patches[:3]),
        ):
            field = candidate_module._load_hybrid().FullSectionComposite(
                candidate.chain, attachment_order, interfaces=patch_order,
            )
            self.assertTrue(np.array_equal(field.evaluate(points), baseline))
            trace = field.operation_trace(points[1])
            self.assertEqual(trace.as_dict(), baseline_trace.as_dict())
            self.assertAlmostEqual(trace.reconstruct(), float(field.evaluate(points[1])), places=12)
            permuted_candidate = candidate_module.RegionalSurfaceCandidate(
                candidate.profile_id,
                candidate.source,
                candidate.chain,
                candidate.regions,
                candidate.stations,
                candidate.routes,
                candidate.controls,
                field,
                candidate.metadata,
                candidate.binding_evidence,
            )
            expected_mesh = candidate.mesh_candidate(samples=20, padding=0.20)
            actual_mesh = permuted_candidate.mesh_candidate(samples=20, padding=0.20)
            self.assertTrue(np.array_equal(actual_mesh.vertices, expected_mesh.vertices))
            self.assertTrue(np.array_equal(actual_mesh.faces, expected_mesh.faces))
            self.assertTrue(np.array_equal(actual_mesh.normals, expected_mesh.normals))

        def patch_nodes(trace):
            found = []
            if trace.operator == "parent-targeted-interface-patch":
                found.append(trace)
            for child in trace.children:
                found.extend(patch_nodes(child))
            return found

        nodes = patch_nodes(baseline_trace)
        self.assertEqual(len(nodes), 7)
        for node in nodes:
            self.assertTrue(node.parent_id)
            self.assertTrue(node.child_id)
            self.assertTrue(node.authority_id)
            self.assertEqual(len(node.children), 2)
            self.assertAlmostEqual(node.reconstruct(), node.value, places=12)
        self.assertEqual(baseline_trace.operator, "full-section-interface-composite")
        self.assertAlmostEqual(baseline_trace.reconstruct(), float(candidate.evaluate(points[1])), places=12)

    def test_exact_five_shoulder_controls_retain_source_namespace_owner_role_frame_and_keys(self) -> None:
        for profile_id, prepared in self.structural_prepared.items():
            with self.subTest(profile_id=profile_id):
                form = candidate_module._as_form(prepared)
                variant_index, descriptors, _ = candidate_module._variant(form, "neutral-v0")
                candidate = candidate_module.build_regional_surface_candidate(
                    form, "neutral-v0", mesh_samples=None,
                )
                for index, control in enumerate(candidate.controls):
                    side = "left" if index < 2 else "right"
                    role = "form_shoulder_peak" if index % 2 == 0 else "form_axilla"
                    binding = candidate_module._shoulder_control_binding(form, descriptors, side, role)
                    identity = candidate_module._validate_shoulder_control_identity(
                        control,
                        namespace=form.source["namespace"],
                        side=side,
                        role=role,
                    )
                    self.assertEqual(identity["namespace"], form.source["namespace"])
                    self.assertEqual(identity["side"], side)
                    self.assertEqual(identity["owner"], (form.source["namespace"], (side,), "part", "upper_arm"))
                    self.assertEqual(identity["role"], role)
                    self.assertEqual(identity["frame"], (identity["owner"], "form_shoulder_control"))
                    self.assertEqual(identity["semantic_key"], binding["semantic_key"])
                    self.assertEqual(identity["source_key"], binding["source_key"])
                    self.assertEqual(
                        candidate.metadata["shoulder_controls"]["controls"][index]["canonical_source_key"],
                        binding["source_key"],
                    )

    def test_final_field_is_exact_hard_min_of_envelope_and_every_patch_outside_authorities(self) -> None:
        candidate = self.candidate
        component_fields = (candidate.chain,) + tuple(route for route in candidate.routes)
        for patch in candidate.interfaces:
            points = patch.authority.sampled_boundary_points()
            component_values = np.stack([np.asarray(field.evaluate(points)) for field in component_fields], axis=0)
            envelope = np.min(component_values, axis=0)
            patch_values = np.stack([np.asarray(other.evaluate(points)) for other in candidate.interfaces], axis=0)
            expected = np.min(np.vstack((envelope.reshape(1, -1), patch_values)), axis=0)
            self.assertTrue(np.allclose(np.asarray(candidate.evaluate(points)), expected, rtol=0.0, atol=1.0e-12))
            self.assertTrue(patch.validate_outside_hard_min(points))
            lower, upper = patch.authority.bounds
            axes = tuple(np.linspace(lower[axis], upper[axis], 7) for axis in range(3))
            interior = np.stack(np.meshgrid(*axes, indexing="ij"), axis=-1).reshape(-1, 3)
            parent = np.asarray(patch.parent.evaluate(interior))
            child = np.asarray(patch.child.evaluate(interior))
            hard = np.minimum(parent, child)
            displacement = hard - np.asarray(patch.evaluate(interior))
            self.assertGreaterEqual(float(np.min(displacement)), -1.0e-12)
            self.assertLessEqual(
                float(np.max(displacement)),
                patch.blend_radius * math.log(2.0) + 1.0e-12,
            )

    def test_source_identity_inventory_has_only_bilateral_endpoint_connectors_and_named_hip_cup_sections(self) -> None:
        candidate = self.candidate
        all_records = [section for route in candidate.metadata["routes"]["routes"] for section in route["sections"]]
        derived = [section for section in all_records if section.get("derived")]
        self.assertEqual(len(derived), 10)
        arm_connectors = [section for section in derived if section["name"] == "torso-arm-interface"]
        cup_sections = [section for section in derived if section["name"] in {"pelvis-seat", "hip-cup-rim", "femoral-neck"}]
        wrist_sections = [section for section in derived if section["name"] == "wrist-transition"]
        self.assertEqual(len(arm_connectors), 2)
        self.assertEqual(len(cup_sections), 6)
        self.assertEqual(len(wrist_sections), 2)
        self.assertTrue(all(section["source_index"] is None for section in derived))
        self.assertTrue(all(section["provenance"]["kind"] == "torso+upper-arm" for section in arm_connectors))
        self.assertTrue(all(section["provenance"]["kind"] == "pelvis+thigh" for section in cup_sections))
        self.assertTrue(all(set(section["provenance"]) >= {"torso", "upper_arm"} for section in arm_connectors))
        self.assertTrue(all(set(section["provenance"]) >= {"pelvis", "thigh"} for section in cup_sections))
        self.assertTrue(all(section["provenance"]["kind"] == "forearm+hand" for section in wrist_sections))
        self.assertTrue(all(set(section["provenance"]) >= {"forearm", "hand"} for section in wrist_sections))
        self.assertEqual(
            tuple(section["name"] for section in cup_sections),
            ("pelvis-seat", "hip-cup-rim", "femoral-neck") * 2,
        )
        self.assertEqual(
            tuple(section["route_index"] for section in cup_sections),
            (0, 1, 2) * 2,
        )
        self.assertEqual(tuple(section["route_index"] for section in wrist_sections), (5, 5))
        source_records = [section for section in all_records if not section.get("derived")]
        self.assertTrue(all(section["source_index"] is not None for section in source_records))
        self.assertTrue(all(section.get("source_frame") and section.get("source_landmark") for section in source_records if "source_frame" in section))
        self.assertTrue(all(section["source_key"].startswith("source-route:") for section in source_records))

    def test_wrist_transition_is_strictly_local_and_causal_for_every_exact_five_profile(self) -> None:
        for profile_id, prepared in self.structural_prepared.items():
            with self.subTest(profile_id=profile_id):
                candidate = candidate_module.build_regional_surface_candidate(
                    prepared, "neutral-v0", mesh_samples=None,
                )
                for side in ("left", "right"):
                    with self.subTest(side=side):
                        route = next(item for item in candidate.routes if item.route_name == f"{side}-arm")
                        wrist = route.sections[5]
                        hand_closure = route.endpoint_closures[-1]
                        hand_cross_section, distal_cross_section, old_forearm_radii = _independent_wrist_geometric_oracle(
                            route.sections[4], route.sections[6], hand_closure, wrist,
                        )
                        self.assertTrue(
                            np.all(hand_cross_section >= distal_cross_section - 1.0e-12),
                            f"{profile_id}:{side}:hand cross-section does not contain distal forearm",
                        )
                        self.assertTrue(
                            np.any(np.isclose(hand_cross_section, distal_cross_section, rtol=0.0, atol=1.0e-12)),
                            f"{profile_id}:{side}:hand cross-section has no tangent equality",
                        )
                        self.assertTrue(
                            np.all(np.asarray(wrist.radii) <= old_forearm_radii + 1.0e-12),
                            f"{profile_id}:{side}:wrist transition widens the old forearm interpolation",
                        )
                        counterfactual = _candidate_without_wrist_transition(candidate, side)
                        for axis, direction in (
                            ("up+", (0.0, 1.0, 0.0)),
                            ("up-", (0.0, -1.0, 0.0)),
                            ("forward+", (0.0, 0.0, 1.0)),
                            ("forward-", (0.0, 0.0, -1.0)),
                        ):
                            old_extent = _final_skin_ray_extent(
                                counterfactual, wrist.center, direction, maximum=1.2,
                            )
                            new_extent = _final_skin_ray_extent(
                                candidate, wrist.center, direction, maximum=1.2,
                            )
                            self.assertGreater(
                                old_extent - new_extent,
                                1.0e-9,
                                f"{profile_id}:{side}:{axis} did not narrow",
                            )
                            probe_extent = 0.5 * (old_extent + new_extent)
                            probe = np.asarray(wrist.center) + probe_extent * np.asarray(direction)
                            self.assertLess(float(counterfactual.evaluate(probe)), 0.0)
                            self.assertGreater(float(candidate.evaluate(probe)), 0.0)
                            influence = candidate.contribution_report(probe)["geometric_influence"]["components"].get(route.route_name, 0.0)
                            self.assertGreater(influence, 1.0e-12)

    def test_wrist_transition_fails_closed_for_hand_equality_axis_and_slice_domain(self) -> None:
        candidate = self.candidate
        route = candidate.routes[2]
        old_sections = route.sections[:5] + route.sections[6:]
        hand_closure = route.endpoint_closures[-1]
        form = candidate_module._as_form(self.prepared)
        variant_index, descriptors, _ = candidate_module._variant(form, "neutral-v0")
        by_key = candidate_module._descriptor_map(descriptors, form.source["namespace"])
        forearm_key = form.authored_arm_profile.sides[1].sections[4].owner
        hand_key = (form.source["namespace"], ("right",), "part", "hand")
        left_forearm_key = form.authored_arm_profile.sides[0].sections[4].owner
        left_hand_key = (form.source["namespace"], ("left",), "part", "hand")
        hand_source = candidate_module._descriptor_source(
            candidate_module._load_surface_preview(), by_key[hand_key], form.reference_scale,
        )
        hybrid = candidate_module._load_hybrid()

        with self.assertRaisesRegex(candidate_module.RegionalSurfaceCandidateError, "H==forearm-distal"):
            candidate_module._derive_wrist_transition(
                hybrid,
                "right-arm",
                old_sections,
                replace(hand_closure, center=(hand_closure.center[0], hand_closure.center[1] + 0.01, hand_closure.center[2])),
                hand_source,
                forearm_key,
                hand_key,
            )

        shifted_midpoint = replace(
            old_sections[4],
            center=(old_sections[4].center[0], old_sections[4].center[1] + 0.01, old_sections[4].center[2]),
        )
        shifted_sections = old_sections[:4] + (shifted_midpoint, old_sections[5])
        with self.assertRaisesRegex(candidate_module.RegionalSurfaceCandidateError, "fixed arm axis relationship"):
            candidate_module._derive_wrist_transition(
                hybrid, "right-arm", shifted_sections, hand_closure, hand_source, forearm_key, hand_key,
            )

        invalid_slice_closure = replace(
            hand_closure,
            radii=(hand_closure.radii[0], old_sections[5].radii[1] * 0.5, hand_closure.radii[2]),
        )
        invalid_slice_hand_source = {
            **hand_source,
            "radii": invalid_slice_closure.radii,
        }
        with self.assertRaisesRegex(candidate_module.RegionalSurfaceCandidateError, "0 < q < 1"):
            candidate_module._derive_wrist_transition(
                hybrid, "right-arm", old_sections, invalid_slice_closure,
                invalid_slice_hand_source, forearm_key, hand_key,
            )

        cases = (
            (
                "wrong-forearm-key",
                {"forearm_key": left_forearm_key},
                "wrong live forearm source binding",
            ),
            (
                "opposite-side-hand-key",
                {"hand_key": left_hand_key},
                "wrong expected route-side hand binding",
            ),
            (
                "wrong-route-side",
                {"route_name": "left-arm"},
                "wrong live forearm source binding",
            ),
            (
                "forged-hand-closure-source-key",
                {"hand_closure": replace(hand_closure, source_key="source-route:forged-hand")},
                "wrong hand closure source identity",
            ),
            (
                "forged-hand-closure-semantic-key",
                {"hand_closure": replace(hand_closure, semantic_key="closure:right-arm:forged")},
                "wrong hand closure semantic identity",
            ),
            (
                "forged-live-forearm-station-source-key",
                {"sections": old_sections[:4] + (replace(old_sections[4], source_key="source-route:forged-forearm"), old_sections[5])},
                "forearm station outside the live source binding",
            ),
            (
                "non-ellipsoid-hand-source",
                {"hand_source": {**hand_source, "name": "capsule"}},
                "requires an ellipsoid hand source",
            ),
        )
        for label, kwargs, message in cases:
            with self.subTest(label=label), self.assertRaisesRegex(
                candidate_module.RegionalSurfaceCandidateError, message,
            ):
                candidate_module._derive_wrist_transition(
                    hybrid,
                    kwargs.pop("route_name", "right-arm"),
                    kwargs.pop("sections", old_sections),
                    kwargs.pop("hand_closure", hand_closure),
                    kwargs.pop("hand_source", hand_source),
                    kwargs.pop("forearm_key", forearm_key),
                    kwargs.pop("hand_key", hand_key),
                )
                self.assertFalse(kwargs, f"unused wrist negative-test arguments: {kwargs}")

    def test_foot_metadata_marks_shared_hock_as_borrowed_leg_authored_identity(self) -> None:
        candidate = self.candidate
        records = {record["name"]: record for record in candidate.metadata["routes"]["routes"]}
        namespace = candidate.source["namespace"]
        for side_index, side in enumerate(("left", "right")):
            leg = candidate.routes[3 + side_index]
            foot = candidate.routes[5 + side_index]
            borrowed = records[f"{side}-foot"]["sections"][0]
            self.assertIs(foot.sections[0], leg.sections[-1])
            self.assertEqual(borrowed["route_index"], 0)
            self.assertEqual(borrowed["binding_kind"], "borrowed-shared-leg-station")
            self.assertFalse(borrowed["authored_in_foot_route"])
            self.assertEqual(borrowed["source_route"], f"{side}-leg")
            self.assertEqual(borrowed["source_index"], 4)
            self.assertEqual(borrowed["owner"], candidate_module._key_json((namespace, (side,), "part", "shin")))
            self.assertEqual(borrowed["source_key"], leg.sections[-1].source_key)
            self.assertEqual(borrowed["semantic_key"], leg.sections[-1].semantic_key)
            self.assertEqual(borrowed["leg_authored_identity"], {
                "route": f"{side}-leg",
                "name": "hock-endpoint",
                "source_index": 4,
                "owner": candidate_module._key_json((namespace, (side,), "part", "shin")),
                "source_key": leg.sections[-1].source_key,
                "semantic_key": leg.sections[-1].semantic_key,
            })

    def test_exact_five_upper_pelvis_is_bounded_without_changing_retained_lower_hip_cup_baseline(self) -> None:
        for structural_profile_id, prepared in self.structural_prepared.items():
            with self.subTest(structural_profile_id=structural_profile_id):
                form = candidate_module._as_form(prepared)
                candidate = candidate_module.build_regional_surface_candidate(form, "neutral-v0", mesh_samples=None)
                baseline_torso = _retained_baseline_torso_radii(form, "neutral-v0")
                lower = np.asarray(candidate.stations[0].radii, dtype=np.float64)
                upper = np.asarray(candidate.stations[1].radii, dtype=np.float64)
                self.assertTrue(np.all(upper <= lower))
                self.assertTrue(np.array_equal(lower, baseline_torso[0]))

                baseline_cups = _retained_baseline_hip_cup_records(candidate, form, "neutral-v0")
                route_records = {record["name"]: record for record in candidate.metadata["routes"]["routes"]}
                for side_index, side in enumerate(("left", "right")):
                    route = candidate.routes[3 + side_index]
                    cups, baseline_certificate = baseline_cups[side_index]
                    for actual, expected in zip(route.sections[:3], cups):
                        self.assertEqual(actual.center, expected.center, f"{side}:{actual.name} center")
                        self.assertEqual(actual.radii, expected.radii, f"{side}:{actual.name} radii")
                    actual_certificate = route_records[route.route_name]["sections"][0]["finite_open_overlap_certificate"]
                    self.assertEqual(actual_certificate, baseline_certificate)
                    self.assertEqual(
                        json.dumps(actual_certificate, sort_keys=True, separators=(",", ":")).encode("utf-8"),
                        json.dumps(baseline_certificate, sort_keys=True, separators=(",", ":")).encode("utf-8"),
                    )

    def test_final_skin_pelvis_cross_sections_have_no_local_upper_bulge(self) -> None:
        for structural_profile_id, prepared in self.structural_prepared.items():
            with self.subTest(structural_profile_id=structural_profile_id):
                candidate = candidate_module.build_regional_surface_candidate(prepared, "neutral-v0", mesh_samples=None)
                lower_station, upper_station = candidate.stations[:2]
                basis = candidate.regions[0].basis
                directions = (
                    basis.lateral_axis,
                    tuple(-value for value in basis.lateral_axis),
                    basis.forward_axis,
                    tuple(-value for value in basis.forward_axis),
                )
                maximum = 1.25 * float(np.linalg.norm(np.asarray(candidate.bounds[1]) - np.asarray(candidate.bounds[0])))
                lower_extents = tuple(
                    _final_skin_ray_extent(candidate, lower_station.center, direction, maximum)
                    for direction in directions
                )
                upper_extents = tuple(
                    _final_skin_ray_extent(candidate, upper_station.center, direction, maximum)
                    for direction in directions
                )
                self.assertTrue(
                    np.all(np.asarray(upper_extents) <= np.asarray(lower_extents) + 0.01),
                    f"upper={upper_extents!r} lower={lower_extents!r}",
                )

    def test_exact_five_retained_neck_collar_lift_is_causal_and_local(self) -> None:
        expected_profiles = (
            "standard_neutral_reference",
            "compact_broad_short_limb_large_head",
            "tall_narrow_long_legged",
            "slender_long_limb",
            "stocky_broad_chested",
        )
        self.assertEqual(tuple(self.structural_prepared), expected_profiles)
        for structural_profile_id, prepared in self.structural_prepared.items():
            with self.subTest(structural_profile_id=structural_profile_id):
                candidate = candidate_module.build_regional_surface_candidate(
                    prepared, "neutral-v0", mesh_samples=None,
                )
                baseline = _candidate_without_neck_collar_lift(candidate)
                lift = (
                    np.asarray(candidate.routes[0].sections[0].center, dtype=np.float64)
                    - np.asarray(baseline.routes[0].sections[0].center, dtype=np.float64)
                )
                collar_up_radius = float(candidate.routes[0].sections[0].radii[1])
                np.testing.assert_allclose(
                    lift,
                    (0.0, candidate_module.NECK_COLLAR_LIFT_UP_RADIUS_FRACTION * collar_up_radius, 0.0),
                    rtol=0.0,
                    atol=1.0e-12,
                )
                self.assertEqual(
                    candidate.metadata["routes"]["neck_collar_lift"],
                    {
                        "axis": "+Y",
                        "fraction_of_up_radius": 0.25,
                        "formula": "neck-collar.center.y += 0.25*neck-collar.up-radius",
                        "endpoint_closure": "reuses the translated neck-collar station center and radii",
                    },
                )

                self.assertEqual(
                    tuple(item.route_name for item in candidate.routes),
                    tuple(item.route_name for item in baseline.routes),
                )
                self.assertEqual(
                    tuple(item.name for item in candidate.routes[0].connections),
                    tuple(item.name for item in baseline.routes[0].connections),
                )
                for lifted, unchanged in zip(
                    candidate.routes[0].sections[1:], baseline.routes[0].sections[1:], strict=True
                ):
                    self.assertEqual(lifted.name, unchanged.name)
                    self.assertEqual(lifted.source_key, unchanged.source_key)
                    np.testing.assert_array_equal(lifted.center, unchanged.center)
                    np.testing.assert_array_equal(lifted.radii, unchanged.radii)
                for lifted, unchanged in zip(
                    candidate.routes[0].endpoint_closures[1:],
                    baseline.routes[0].endpoint_closures[1:],
                    strict=True,
                ):
                    self.assertEqual(lifted.name, unchanged.name)
                    self.assertEqual(lifted.semantic_key, unchanged.semantic_key)
                    self.assertEqual(lifted.source_key, unchanged.source_key)
                    np.testing.assert_array_equal(lifted.center, unchanged.center)
                    self.assertEqual(lifted.radii, unchanged.radii)
                self.assertEqual(
                    candidate.routes[0].endpoint_closures[0].center,
                    candidate.routes[0].sections[0].center,
                )

                lower_delta = _ray_root_band_delta(baseline, candidate, 1.95, 2.50)
                upper_delta = _ray_root_band_delta(baseline, candidate, 2.50, 3.05)
                self.assertGreater(lower_delta["lateral_mean_signed"], 0.0)
                self.assertGreater(lower_delta["forward_mean_signed"], 0.0)
                self.assertLessEqual(upper_delta["lateral_max_abs"], 1.0e-3)
                self.assertLessEqual(upper_delta["forward_max_abs"], 1.0e-3)

    def test_all_five_profiles_have_named_hip_cup_overlap_certificates_and_shared_factors(self) -> None:
        factors = None
        for structural_profile_id, prepared in self.structural_prepared.items():
            form = candidate_module._as_form(prepared)
            candidate = candidate_module.build_regional_surface_candidate(form, "neutral-v0", mesh_samples=None)
            route_records = {record["name"]: record for record in candidate.metadata["routes"]["routes"]}
            profile_factors = candidate.metadata["routes"]["hip_cup_factors"]
            if factors is None:
                factors = profile_factors
            self.assertEqual(profile_factors, factors)
            for side_index, side in enumerate(("left", "right")):
                route = candidate.routes[3 + side_index]
                self.assertEqual(
                    tuple(section.name for section in route.sections[:4]),
                    ("pelvis-seat", "hip-cup-rim", "femoral-neck", "thigh-start"),
                )
                self.assertTrue(all(section.source_index is None for section in route.sections[:3]))
                self.assertEqual(route.sections[3].source_index, 0)
                record = route_records[route.route_name]["sections"][0]
                certificate = record["finite_open_overlap_certificate"]
                self.assertEqual(
                    tuple(item["name"] for item in certificate["adjacent_cup_spans"]),
                    tuple(item.name for item in route.connections[:3]),
                )
                self.assertTrue(all(item["max_value"] < 0.0 for item in certificate["adjacent_cup_spans"]))
                constituent = candidate.chain._initial_constituent(
                    candidate.stations[0], candidate.chain.regions[0], candidate.chain.regions[0].first_basis,
                )
                self.assertLess(float(constituent.evaluate(route.sections[0].center)), 0.0)
                self.assertAlmostEqual(float(constituent.evaluate(route.sections[1].center)), 0.0, places=12)
                self.assertTrue(np.all(np.asarray(route.sections[2].radii) < np.asarray(route.sections[1].radii)))
                for section in route.sections[:3]:
                    self.assertIn(section.semantic_key, {item["semantic_key"] for item in candidate.binding_evidence})

    def test_femoral_neck_axis_decomposition_is_shared_bilateral_and_local_for_all_profiles(self) -> None:
        expected_profiles = (
            "standard_neutral_reference",
            "compact_broad_short_limb_large_head",
            "tall_narrow_long_legged",
            "slender_long_limb",
            "stocky_broad_chested",
        )
        self.assertEqual(tuple(self.structural_prepared), expected_profiles)
        candidate_source = Path(candidate_module.__file__).read_text(encoding="utf-8")
        for profile_id in expected_profiles:
            self.assertNotIn(profile_id, candidate_source)

        formula_signatures = set()
        for structural_profile_id, prepared in self.structural_prepared.items():
            with self.subTest(profile_id=structural_profile_id):
                form = candidate_module._as_form(prepared)
                candidate = candidate_module.build_regional_surface_candidate(
                    form, "neutral-v0", mesh_samples=None,
                )
                route_records = {
                    record["name"]: record for record in candidate.metadata["routes"]["routes"]
                }
                formula_signatures.add(
                    (
                        candidate.metadata["routes"]["hip_cup_chain_method"],
                        tuple(
                            route_records[f"{side}-leg"]["sections"][2]["derivation"]
                            for side in ("left", "right")
                        ),
                        tuple(sorted(candidate.metadata["routes"]["hip_cup_factors"].items())),
                    )
                )

                basis = candidate.chain.regions[0].first_basis
                up_axis = np.asarray(basis.axial_axis, dtype=np.float64)
                lateral_axis = np.asarray(basis.lateral_axis, dtype=np.float64)
                forward_axis = np.asarray(basis.forward_axis, dtype=np.float64)
                for side_index, side in enumerate(("left", "right")):
                    route = candidate.routes[3 + side_index]
                    rim = route.sections[1]
                    neck = route.sections[2]
                    thigh = route.sections[3]
                    rim_center = np.asarray(rim.center, dtype=np.float64)
                    thigh_center = np.asarray(thigh.center, dtype=np.float64)
                    expected_center = rim_center + up_axis * float(
                        np.dot(
                            candidate_module.FEMORAL_NECK_CENTER_FACTOR * (thigh_center - rim_center),
                            up_axis,
                        )
                    )
                    np.testing.assert_allclose(neck.center, expected_center, rtol=0.0, atol=1.0e-12)
                    self.assertAlmostEqual(
                        float(np.dot(np.asarray(neck.center) - rim_center, lateral_axis)),
                        0.0,
                        places=12,
                    )
                    self.assertAlmostEqual(
                        float(np.dot(np.asarray(neck.center) - rim_center, forward_axis)),
                        0.0,
                        places=12,
                    )
                    rim_up = float(np.dot(rim_center, up_axis))
                    neck_up = float(np.dot(np.asarray(neck.center), up_axis))
                    thigh_up = float(np.dot(thigh_center, up_axis))
                    self.assertLess(min(rim_up, thigh_up), neck_up)
                    self.assertLess(neck_up, max(rim_up, thigh_up))

                    expected_thigh = _expected_variant_geometry(form, "neutral-v0")["legs"][side]["sections"][0]
                    np.testing.assert_array_equal(thigh.center, expected_thigh["center"])
                    np.testing.assert_array_equal(thigh.radii, expected_thigh["radii"])
                    self.assertEqual(thigh.source_index, 0)
                    self.assertEqual(
                        thigh.source_key,
                        candidate_module._source_route_key(
                            (form.source["namespace"], (side,), "part", "thigh"),
                            f"{side}-leg:thigh-start",
                        ),
                    )

                    counterfactual = _candidate_without_femoral_neck_axis_decomposition(candidate, side)
                    old_route = next(
                        item for item in counterfactual.routes if item.route_name == f"{side}-leg"
                    )
                    self.assertIs(counterfactual.chain, candidate.chain)
                    self.assertIs(counterfactual.stations, candidate.stations)
                    self.assertIs(counterfactual.regions, candidate.regions)
                    self.assertIs(counterfactual.controls, candidate.controls)
                    self.assertEqual(len(old_route.sections), len(route.sections))
                    self.assertEqual(len(old_route.connections), len(route.connections))
                    for index, (actual, old) in enumerate(zip(route.sections, old_route.sections, strict=True)):
                        self.assertEqual((actual.name, actual.position, actual.radii), (old.name, old.position, old.radii))
                        self.assertEqual((actual.semantic_key, actual.source_key, actual.source_index), (old.semantic_key, old.source_key, old.source_index))
                        if index != 2:
                            np.testing.assert_array_equal(actual.center, old.center)
                    self.assertNotEqual(route.sections[2].center, old_route.sections[2].center)
                    for actual, old in zip(route.endpoint_closures, old_route.endpoint_closures, strict=True):
                        self.assertEqual(actual, old)
                    self.assertEqual(thigh.center, old_route.sections[3].center)
                    self.assertEqual(thigh.radii, old_route.sections[3].radii)

                    for actual_route, old_route_value in zip(
                        candidate.routes, counterfactual.routes, strict=True
                    ):
                        if actual_route is not route:
                            self.assertIs(actual_route, old_route_value)
                    for actual_patch, old_patch in zip(
                        candidate.interfaces, counterfactual.interfaces, strict=True
                    ):
                        self.assertEqual(actual_patch.identifier, old_patch.identifier)
                        self.assertIs(actual_patch.authority, old_patch.authority)
                        self.assertEqual(actual_patch.blend_radius, old_patch.blend_radius)
                        self.assertEqual(actual_patch.semantic_key, old_patch.semantic_key)

                left_route = candidate.routes[3]
                right_route = candidate.routes[4]
                for left_section, right_section in zip(left_route.sections, right_route.sections, strict=True):
                    self.assertEqual(left_section.name, right_section.name)
                    np.testing.assert_allclose(
                        right_section.center,
                        candidate_module._reflect_x(left_section.center, "test.left-leg.center"),
                        rtol=0.0,
                        atol=1.0e-12,
                    )
                    np.testing.assert_array_equal(left_section.radii, right_section.radii)

        self.assertEqual(len(formula_signatures), 1)

    @unittest.skip("legacy two-section pelvis overlap test retained outside the bounded hip-cup slice")
    def test_all_structural_profiles_have_exact_finite_open_endpoint_overlaps(self) -> None:
        self.assertEqual(len(self.structural_prepared), 5)
        certified_arm_relations = []
        certified_pelvis_leg_relations = []
        for structural_profile_id, prepared in self.structural_prepared.items():
            form = candidate_module._as_form(prepared)
            candidate = candidate_module.build_regional_surface_candidate(form, "neutral-v0", mesh_samples=None)
            expected = _expected_variant_geometry(form, "neutral-v0")
            self.assertEqual(candidate.metadata["format"], "creature-kernel.disposable-regional-surface-candidate.v3")
            self.assertEqual(1 + len(candidate.routes), 8)
            self.assertEqual(len(candidate.field.attachments), 7)
            self.assertEqual(len(candidate.interfaces), 7)
            self.assertEqual(len(candidate.controls), 4)
            self.assertEqual(len(candidate.binding_evidence), 49)
            self.assertEqual(len({record["semantic_key"] for record in candidate.binding_evidence}), 49)
            route_records = {record["name"]: record for record in candidate.metadata["routes"]["routes"]}
            authored_arm_by_side = {item.side: item for item in form.authored_arm_profile.sides}
            authored_leg_by_side = {item.side: item for item in form.authored_leg_profile.sides}
            self.assertEqual(set(authored_arm_by_side), {"left", "right"})
            self.assertEqual(set(authored_leg_by_side), {"left", "right"})

            for side_index, side in enumerate(("left", "right")):
                route = candidate.routes[1 + side_index]
                connector, child = route.sections[:2]
                parent = candidate.stations[-1]
                expected_radii = np.minimum(np.asarray(parent.radii), expected["arms"][side][0]["radii"])
                mu = candidate_module.ENDPOINT_CONNECTOR_DEPTH_FRACTION * float(np.min(expected_radii))
                boundary, expected_center, rho = _independent_endpoint_oracle(candidate.chain, False, child.center, mu)
                constituent = candidate.chain._terminal_constituent(parent, candidate.chain.regions[-1], candidate.chain.regions[-1].last_basis)
                self.assertEqual((len(route.sections), len(route.connections)), (6, 5))
                self.assertEqual(connector.name, "torso-arm-interface")
                self.assertIsNone(connector.source_index)
                self.assertTrue(np.array_equal(np.asarray(connector.center), expected_center))
                self.assertTrue(np.array_equal(np.asarray(connector.radii), expected_radii))
                self.assertAlmostEqual(float(constituent.evaluate(boundary)), 0.0, places=12)
                self.assertAlmostEqual(float(constituent.evaluate(connector.center)), -mu, places=12)
                self.assertLessEqual(float(candidate.chain.evaluate(connector.center)), float(constituent.evaluate(connector.center)))
                self.assertEqual(candidate.chain.operation_trace(connector.center).children[0].dominance, "end-cap")
                authored_sections = tuple(authored_arm_by_side[side].sections)
                self.assertEqual(len(authored_sections), 5)
                for source_index in range(5):
                    station = route.sections[source_index + 1]
                    authored = authored_sections[source_index]
                    self.assertEqual(station.source_index, source_index)
                    self.assertEqual(station.source_key, candidate_module._source_route_key(authored.owner, f"{route.route_name}:{authored.name}"))
                record = route_records[route.route_name]["sections"][0]
                self.assertEqual(record["rho"], rho)
                self.assertEqual(record["parent_depth_fraction"], candidate_module.ENDPOINT_CONNECTOR_DEPTH_FRACTION)
                certificate = record["finite_open_overlap_certificate"]
                self.assertEqual(certificate["parent_operand"], "live-terminal-constituent-ellipsoid")
                self.assertLess(certificate["constituent_at_interior"], 0.0)
                self.assertLessEqual(certificate["parent_at_interior"], certificate["constituent_at_interior"])
                self.assertLess(certificate["connector_at_interior"], 0.0)
                self.assertTrue(certificate["positive_connector_radii_along_centerline"])
                self.assertLess(certificate["connector_at_upper_arm_start"], 0.0)
                self.assertLess(certificate["authored_arm_at_upper_arm_start"], 0.0)
                parent_path = np.linspace(np.asarray(parent.center), np.asarray(connector.center), 129)
                connector_path = np.linspace(np.asarray(connector.center), np.asarray(child.center), 129)
                self.assertLess(float(np.max(candidate.chain.evaluate(parent_path))), 0.0)
                self.assertLess(float(np.max(route._connection_value(connector_path, route.connections[0]))), 0.0)
                hard_path = np.vstack((parent_path, connector_path[1:]))
                hard_envelope = np.min(np.stack(
                    [np.asarray(candidate.chain.evaluate(hard_path))]
                    + [np.asarray(component.evaluate(hard_path)) for component in candidate.routes],
                    axis=0,
                ), axis=0)
                self.assertLess(float(np.max(hard_envelope)), 0.0)
                certified_arm_relations.append((structural_profile_id, side))

            for side_index, side in enumerate(("left", "right")):
                route = candidate.routes[3 + side_index]
                connector, hip, thigh = route.sections[:3]
                parent = candidate.stations[0]
                expected_leg = expected["legs"][side]
                expected_radii = np.minimum.reduce((
                    np.asarray(parent.radii),
                    expected_leg["hip"]["radii"],
                    expected_leg["sections"][0]["radii"],
                ))
                mu = candidate_module.ENDPOINT_CONNECTOR_DEPTH_FRACTION * float(np.min(expected_radii))
                boundary, expected_center, rho = _independent_endpoint_oracle(candidate.chain, True, hip.center, mu)
                initial_region = candidate.chain.regions[0]
                constituent = candidate.chain._initial_constituent(parent, initial_region, initial_region.first_basis)
                self.assertEqual((len(route.sections), len(route.connections)), (7, 6))
                self.assertEqual(tuple(section.name for section in route.sections[:3]), ("pelvis-leg-interface", "hip-interface", "thigh-start"))
                self.assertIsNone(connector.source_index)
                self.assertTrue(np.array_equal(np.asarray(connector.center), expected_center))
                self.assertTrue(np.array_equal(np.asarray(connector.radii), expected_radii))
                self.assertTrue(np.array_equal(np.asarray(hip.center), expected_leg["hip"]["center"]))
                self.assertTrue(np.array_equal(np.asarray(hip.radii), expected_leg["hip"]["radii"]))
                self.assertAlmostEqual(float(constituent.evaluate(boundary)), 0.0, places=12)
                self.assertAlmostEqual(float(constituent.evaluate(connector.center)), -mu, places=12)
                self.assertLessEqual(float(candidate.chain.evaluate(connector.center)), float(constituent.evaluate(connector.center)))
                self.assertEqual(candidate.chain.operation_trace(connector.center).children[0].dominance, "start-cap")
                self.assertEqual(tuple((item.from_section_index, item.to_section_index) for item in route.connections[:3]), ((0, 1), (1, 2), (2, 3)))
                self.assertEqual(route.endpoint_closures[0].center, hip.center)
                self.assertFalse(any(closure.center == connector.center for closure in route.endpoint_closures))
                authored_sections = tuple(authored_leg_by_side[side].sections)
                self.assertEqual(len(authored_sections), 5)
                for source_index in range(5):
                    station = route.sections[source_index + 2]
                    authored = authored_sections[source_index]
                    self.assertEqual(station.source_index, source_index)
                    self.assertEqual(station.source_key, candidate_module._source_route_key(authored.owner, f"{route.route_name}:{authored.name}"))
                record = route_records[route.route_name]["sections"][0]
                self.assertEqual(record["provenance"]["kind"], "pelvis+thigh")
                self.assertEqual(record["rho"], rho)
                self.assertEqual(record["parent_depth_fraction"], candidate_module.ENDPOINT_CONNECTOR_DEPTH_FRACTION)
                certificate = record["finite_open_overlap_certificate"]
                self.assertEqual(certificate["kind"], "finite-open-overlap-through-thigh-start")
                self.assertEqual(certificate["parent_operand"], "live-initial-constituent-ellipsoid")
                self.assertEqual(certificate["connector_operand"], route.connections[0].name)
                self.assertEqual(certificate["hip_thigh_operand"], route.connections[1].name)
                self.assertEqual(certificate["authored_thigh_operand"], route.connections[2].name)
                self.assertLess(certificate["constituent_at_interior"], 0.0)
                self.assertLessEqual(certificate["parent_at_interior"], certificate["constituent_at_interior"])
                self.assertLess(certificate["connector_at_interior"], 0.0)
                self.assertLess(certificate["connector_at_hip_interface"], 0.0)
                self.assertLess(certificate["hip_thigh_at_hip_interface"], 0.0)
                self.assertLess(certificate["hip_thigh_at_thigh_start"], 0.0)
                self.assertLess(certificate["authored_thigh_at_thigh_start"], 0.0)
                self.assertTrue(certificate["positive_radii_along_both_centerlines"])

                parent_path = np.linspace(np.asarray(parent.center), np.asarray(connector.center), 129)
                connector_path = np.linspace(np.asarray(connector.center), np.asarray(hip.center), 129)
                hip_thigh_path = np.linspace(np.asarray(hip.center), np.asarray(thigh.center), 129)
                self.assertLess(float(np.max(candidate.chain.evaluate(parent_path))), 0.0)
                self.assertLess(float(np.max(route._connection_value(connector_path, route.connections[0]))), 0.0)
                self.assertLess(float(np.max(route._connection_value(hip_thigh_path, route.connections[1]))), 0.0)
                hard_path = np.vstack((parent_path, connector_path[1:], hip_thigh_path[1:]))
                hard_envelope = np.min(np.stack(
                    [np.asarray(candidate.chain.evaluate(hard_path))]
                    + [np.asarray(component.evaluate(hard_path)) for component in candidate.routes],
                    axis=0,
                ), axis=0)
                self.assertTrue(np.all(np.isfinite(hard_envelope)))
                self.assertLess(float(np.max(hard_envelope)), 0.0)
                certified_pelvis_leg_relations.append((structural_profile_id, side))

        self.assertEqual(len(certified_arm_relations), 10)
        self.assertEqual(len(certified_pelvis_leg_relations), 10)
        self.assertIn(("standard_neutral_reference", "left"), certified_pelvis_leg_relations)
        self.assertIn(("standard_neutral_reference", "right"), certified_pelvis_leg_relations)

    def test_shoulder_controls_are_bilateral_authority_only_inputs_without_skin_consumers(self) -> None:
        candidate = self.candidate
        self.assertEqual(
            tuple(item.name for item in candidate.controls),
            ("left-shoulder-peak", "left-axilla", "right-shoulder-peak", "right-axilla"),
        )
        self.assertEqual(candidate.metadata["shoulder_controls"]["count"], 4)
        self.assertTrue(candidate.metadata["shoulder_controls"]["authority_only"])
        self.assertFalse(candidate.metadata["shoulder_controls"]["skin_consumer"])
        self.assertEqual(candidate.metadata["shoulder_controls"]["counterfactual_authority_bound_influence"], "proven")
        self.assertFalse(candidate.metadata["shoulder_controls"]["control_local_final_skin_influence"])
        self.assertEqual(candidate.metadata["shoulder_controls"]["control_local_final_skin_influence_status"], "unverified")
        self.assertEqual(candidate.metadata["shoulder_controls"]["shoulder_visual_floor_satisfaction"], "unverified")
        self.assertEqual(candidate.metadata["shoulder_controls"]["axilla_visual_floor_satisfaction"], "unverified")
        self.assertEqual(len(candidate.field.attachments), 7)
        self.assertTrue(all(item.authority is None for item in candidate.field.attachments))
        for item in candidate.metadata["shoulder_controls"]["controls"]:
            self.assertTrue(item["authority_only"])
            self.assertFalse(item["skin_consumer"])
            self.assertEqual(item["counterfactual_authority_bound_influence"], "proven")
            self.assertFalse(item["control_local_final_skin_influence"])
            self.assertEqual(item["control_local_final_skin_influence_status"], "unverified")
            self.assertEqual(item["visual_floor_satisfaction"], "unverified")
            self.assertEqual(item["source_key"], item["canonical_source_key"])
            self.assertEqual(item["interface_id"], f"interface:torso->{item['name'].split('-', 1)[0]}-arm")
        self.assertEqual(candidate.metadata["interfaces"]["count"], 7)
        self.assertTrue(candidate.metadata["proof"]["route_authorities_absent"])
        source = (EXPERIMENT_ROOT / "regional_surface_candidate.py").read_text()
        self.assertNotIn("successor_surface_preview", source)
        self.assertNotIn("_derive_hybrid_guides", source)
        self.assertNotIn("_compile_hybrid_guide", source)

    def test_neck_thigh_and_every_limb_station_have_crossings_of_the_expected_route_operand(self) -> None:
        candidate = self.candidate
        directions = np.asarray(((1.0, 0.0, 0.0), (-1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, -1.0, 0.0), (0.0, 0.0, 1.0), (0.0, 0.0, -1.0)))
        for route in candidate.routes:
            if route.route_name in {"left-foot", "right-foot"}:
                continue
            for station in route.sections:
                if station.name in {"torso-arm-interface"}:
                    continue
                center = np.asarray(station.center)
                radius = min(station.radii)
                found = False
                for direction in directions:
                    # The authored distal hand endpoint is a source-shape
                    # closure, so its larger source extent places the final
                    # crossing just beyond two profile radii.
                    fractions = np.linspace(0.05, 3.0, 96)
                    probes = center + fractions[:, None] * radius * direction
                    final_values = np.asarray(candidate.evaluate(probes))
                    route_values = np.asarray(route.evaluate(probes))
                    final_crossings = set(np.flatnonzero(final_values[:-1] * final_values[1:] <= 0.0).tolist())
                    route_crossings = set(np.flatnonzero(route_values[:-1] * route_values[1:] <= 0.0).tolist())
                    shared_crossings = sorted(final_crossings & route_crossings)
                    if shared_crossings:
                        crossing_index = shared_crossings[0]
                        probe = probes[crossing_index + 1]
                        trace = route.operation_trace(probe)
                        self.assertEqual(trace.operator, "section-sweep-hard-min")
                        self.assertAlmostEqual(trace.reconstruct(), float(route.evaluate(probe)), places=12)
                        self.assertIn(station.semantic_key, trace.semantic_keys)
                        influence = candidate.contribution_report(probe)["geometric_influence"]["components"].get(route.route_name, 0.0)
                        self.assertGreater(influence, 1.0e-12)
                        found = True
                        break
                self.assertTrue(found, f"no shared final/route crossing for {route.route_name}:{station.name}")
        for route in candidate.routes[3:5]:
            self.assertEqual(tuple(section.name for section in route.sections[:4]), ("pelvis-seat", "hip-cup-rim", "femoral-neck", "thigh-start"))
            self.assertEqual(route.endpoint_closures[0].name, f"{route.route_name}:hip-cup-rim-closure")
            self.assertEqual(route.sections[5].name, "knee")

        neck_upper = candidate.routes[0].sections[1]
        neck_crossing = False
        for direction in directions:
            fractions = np.linspace(0.05, 2.0, 24)
            values = np.asarray(candidate.evaluate(np.asarray(neck_upper.center) + fractions[:, None] * min(neck_upper.radii) * direction))
            crossing = np.flatnonzero(values[:-1] * values[1:] <= 0.0)
            if len(crossing):
                probe = np.asarray(neck_upper.center) + fractions[int(crossing[0]) + 1] * min(neck_upper.radii) * direction
                if candidate.contribution_report(probe)["geometric_influence"]["components"].get("head-neck", 0.0) > 1.0e-12:
                    neck_crossing = True
                    break
        self.assertTrue(neck_crossing, "neck-upper remains swallowed instead of reaching the final surface")

    def test_traces_metadata_and_evaluation_are_deterministic(self) -> None:
        candidate = self.candidate
        repeated = candidate_module.build_regional_surface_candidate(self.prepared, mesh_samples=None)
        self.assertEqual(repeated.metadata, candidate.metadata)
        self.assertEqual(repeated.binding_evidence, candidate.binding_evidence)
        points = np.asarray((candidate.stations[3].center, candidate.routes[0].sections[3].center, candidate.routes[3].sections[0].center, candidate.routes[5].sections[1].center))
        self.assertTrue(np.array_equal(candidate.evaluate(points), repeated.evaluate(points)))
        for point in points:
            first = candidate.operation_trace(point)
            second = repeated.operation_trace(point)
            self.assertEqual(first.as_dict(), second.as_dict())
            self.assertAlmostEqual(first.reconstruct(), float(candidate.evaluate(point)), places=10)
            self.assertTrue(first.semantic_keys)

    def test_marching_cubes_proves_lower_resolution_robustness(self) -> None:
        mesh = self.candidate.mesh_candidate(samples=20, padding=0.20)
        self.assertTrue(mesh.closed_triangle_2_manifold)
        self.assertEqual(mesh.connected_components, 1)
        self.assertEqual(mesh.boundary_edge_count, 0)
        self.assertEqual(mesh.nonmanifold_edge_count, 0)
        self.assertEqual(mesh.nonmanifold_vertex_count, 0)

    def test_marching_cubes_proves_standard_neutral_at_56_and_80_samples(self) -> None:
        for samples in (56, 80):
            mesh = self.candidate.mesh_candidate(samples=samples, padding=0.20)
            self.assertTrue(mesh.connected)
            self.assertTrue(mesh.watertight)
            self.assertTrue(mesh.closed_triangle_2_manifold)
            self.assertTrue(mesh.topology_proven)
            self.assertEqual(mesh.connected_components, 1)
            self.assertEqual(mesh.boundary_edge_count, 0)
            self.assertEqual(mesh.nonmanifold_edge_count, 0)
            self.assertEqual(mesh.nonmanifold_vertex_count, 0)
            self.assertEqual(mesh.faces.shape[1], 3)

    def test_all_structural_profiles_are_closed_connected_manifolds_at_56_and_80(self) -> None:
        certificates = []
        for structural_profile_id, prepared in self.structural_prepared.items():
            candidate = candidate_module.build_regional_surface_candidate(prepared, "neutral-v0")
            for samples in (56, 80):
                with self.subTest(structural_profile_id=structural_profile_id, samples=samples):
                    mesh = candidate.mesh if samples == 56 else candidate.mesh_candidate(samples=samples, padding=0.20)
                    self.assertEqual(mesh.samples, samples)
                    self.assertTrue(mesh.connected, f"{structural_profile_id}:{samples}")
                    self.assertTrue(mesh.watertight, f"{structural_profile_id}:{samples}")
                    self.assertTrue(mesh.closed_triangle_2_manifold, f"{structural_profile_id}:{samples}")
                    self.assertEqual(mesh.connected_components, 1, f"{structural_profile_id}:{samples}")
                    self.assertEqual(mesh.boundary_edge_count, 0, f"{structural_profile_id}:{samples}")
                    self.assertEqual(mesh.nonmanifold_edge_count, 0, f"{structural_profile_id}:{samples}")
                    self.assertEqual(mesh.nonmanifold_vertex_count, 0, f"{structural_profile_id}:{samples}")
                    certificates.append((structural_profile_id, samples))
        self.assertEqual(len(certificates), 10)

    def test_exact_five_bilateral_connectors_interfaces_controls_authorities_and_values(self) -> None:
        for structural_profile_id, prepared in self.structural_prepared.items():
            with self.subTest(profile_id=structural_profile_id):
                form = candidate_module._as_form(prepared)
                variant_index, descriptors, _ = candidate_module._variant(form, "neutral-v0")
                candidate_module._validate_exact_bilateral_source_profile(form, descriptors, variant_index)
                candidate = candidate_module.build_regional_surface_candidate(
                    form, "neutral-v0", mesh_samples=None,
                )
                routes = {route.route_name: route for route in candidate.routes}
                for left_name, right_name in (
                    ("left-arm", "right-arm"),
                    ("left-leg", "right-leg"),
                    ("left-foot", "right-foot"),
                ):
                    for index, (left, right) in enumerate(zip(routes[left_name].sections, routes[right_name].sections)):
                        reflected = np.asarray(left.center, dtype=np.float64).copy()
                        reflected[0] *= -1.0
                        self.assertLessEqual(float(np.max(np.abs(reflected - np.asarray(right.center)))), 1.0e-8, f"{left_name}:{index}:center")
                        self.assertLessEqual(float(np.max(np.abs(np.asarray(left.radii) - np.asarray(right.radii)))), 1.0e-12, f"{left_name}:{index}:radii")

                controls = {control.name: control for control in candidate.controls}
                for suffix in ("shoulder-peak", "axilla"):
                    left = controls[f"left-{suffix}"]
                    right = controls[f"right-{suffix}"]
                    reflected = np.asarray(left.center, dtype=np.float64).copy()
                    reflected[0] *= -1.0
                    self.assertLessEqual(float(np.max(np.abs(reflected - np.asarray(right.center)))), 1.0e-8, f"{suffix}:center")
                    self.assertLessEqual(float(np.max(np.abs(np.asarray(left.radii) - np.asarray(right.radii)))), 1.0e-12, f"{suffix}:radii")

                patches = {patch.identifier: patch for patch in candidate.interfaces}
                records = {record["identifier"]: record["authority"] for record in candidate.metadata["interfaces"]["patches"]}
                sample_offsets = np.asarray(
                    ((0.0, 0.0, 0.0), (0.37, 0.0, 0.0), (-0.37, 0.0, 0.0), (0.0, 0.37, 0.0), (0.0, -0.37, 0.0), (0.0, 0.0, 0.37), (0.0, 0.0, -0.37)),
                    dtype=np.float64,
                )
                for left_id, right_id in (
                    ("interface:torso->left-arm", "interface:torso->right-arm"),
                    ("interface:torso->left-leg", "interface:torso->right-leg"),
                    ("interface:left-leg->left-foot", "interface:right-leg->right-foot"),
                ):
                    left_record = records[left_id]
                    right_record = records[right_id]
                    left_points = np.asarray(left_record["points"], dtype=np.float64)
                    reflected_points = left_points.copy()
                    reflected_points[:, 0] *= -1.0
                    np.testing.assert_allclose(reflected_points, np.asarray(right_record["points"]), rtol=0.0, atol=1.0e-8)
                    np.testing.assert_allclose(left_record["interface_radii"], right_record["interface_radii"], rtol=0.0, atol=1.0e-12)
                    np.testing.assert_allclose(left_record["radii"], right_record["radii"], rtol=0.0, atol=1.0e-12)
                    self.assertLessEqual(abs(float(left_record["k"]) - float(right_record["k"])), 1.0e-12)
                    if left_record["authority_controls"]:
                        left_controls = {item["role"]: item for item in left_record["authority_controls"]}
                        right_controls = {item["role"]: item for item in right_record["authority_controls"]}
                        for role in left_controls:
                            center = np.asarray(left_controls[role]["center"], dtype=np.float64).copy()
                            center[0] *= -1.0
                            np.testing.assert_allclose(center, right_controls[role]["center"], rtol=0.0, atol=1.0e-8)
                            np.testing.assert_allclose(left_controls[role]["radii"], right_controls[role]["radii"], rtol=0.0, atol=1.0e-12)
                    left_patch = patches[left_id]
                    right_patch = patches[right_id]
                    samples = np.asarray(left_patch.authority.center) + sample_offsets * np.asarray(left_patch.authority.radii)
                    reflected_samples = samples.copy()
                    reflected_samples[:, 0] *= -1.0
                    np.testing.assert_allclose(
                        left_patch.authority.gate(samples),
                        right_patch.authority.gate(reflected_samples),
                        rtol=0.0,
                        atol=1.0e-12,
                    )
                    np.testing.assert_allclose(
                        left_patch.evaluate(samples),
                        right_patch.evaluate(reflected_samples),
                        rtol=0.0,
                        atol=1.0e-12,
                    )

    def test_mesh_connectivity_uses_shared_edges_and_rejects_vertex_links(self) -> None:
        faces = np.asarray(
            ((0, 1, 2), (0, 3, 1), (1, 3, 2), (2, 3, 0), (0, 4, 5), (0, 6, 4), (4, 6, 5), (5, 6, 0)),
            dtype=np.int64,
        )
        self.assertEqual(candidate_module._face_component_count(faces), 2)
        self.assertEqual(candidate_module._nonmanifold_vertex_count(faces), 1)


if __name__ == "__main__":
    unittest.main()
