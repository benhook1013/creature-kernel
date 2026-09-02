from __future__ import annotations

from dataclasses import replace
import importlib.util
import itertools
import math
from pathlib import Path
import sys
import unittest

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("regional_hybrid_surface", ROOT / "regional_hybrid_surface.py")
assert SPEC and SPEC.loader
regional = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = regional
SPEC.loader.exec_module(regional)


def basis(angle: float = 0.0) -> regional.RegionBasis:
    cosine = math.cos(angle)
    sine = math.sin(angle)
    return regional.RegionBasis(
        axial_axis=(0.0, 1.0, 0.0),
        lateral_axis=(cosine, 0.0, sine),
        forward_axis=(-sine, 0.0, cosine),
    )


def make_chain() -> regional.AxialMassChain:
    stations = tuple(
        regional.AxialStation(name, float(index), (0.0, float(index), 0.0), (1.0 + 0.1 * index, 0.7 + 0.05 * index, 0.5 + 0.05 * index))
        for index, name in enumerate(("pelvis-base", "pelvis-top", "waist", "rib-low", "rib-high"))
    )
    shared = basis()
    pelvis = regional.AxialRegion("pelvis", 0, 2, basis=shared, start_basis=shared, end_basis=shared)
    abdomen = regional.AxialRegion("abdomen", 2, 3, basis=basis(0.28), start_basis=shared, end_basis=shared)
    ribcage = regional.AxialRegion("ribcage", 3, 4, basis=basis(-0.22), start_basis=shared, end_basis=shared)
    return regional.AxialMassChain(stations, (pelvis, abdomen, ribcage))


def independent_endpoint_oracle(chain, lower: bool, toward, mu: float):
    """Closed-form test oracle independent of the production ray helper."""

    station = chain.stations[0 if lower else -1]
    region = chain.regions[0 if lower else -1]
    basis_value = region.first_basis if lower else region.last_basis
    cap_radius = chain.start_cap_radius if lower else chain.end_cap_radius
    origin = np.asarray(station.center, dtype=np.float64)
    delta = np.asarray(toward, dtype=np.float64) - origin
    lateral = float(np.dot(delta, np.asarray(basis_value.lateral_axis)))
    forward = float(np.dot(delta, np.asarray(basis_value.forward_axis)))
    axial = float(np.dot(delta, np.asarray(basis_value.axial_axis)))
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

    field_scale = min(*station.radii, cap_radius)
    boundary_fraction = solve(1.0)
    interior_fraction = solve(1.0 - mu / field_scale)
    return (
        origin + boundary_fraction * delta,
        origin + interior_fraction * delta,
        interior_fraction / boundary_fraction,
    )


class AxialRegionalCoreTests(unittest.TestCase):
    def test_regions_are_distinct_and_seams_are_C1_relevant(self) -> None:
        chain = make_chain()
        self.assertEqual(tuple(region.name for region in chain.regions), ("pelvis", "abdomen", "ribcage"))
        self.assertNotEqual(chain.regions[0].basis.lateral_axis, chain.regions[1].basis.lateral_axis)
        self.assertNotEqual(chain.regions[1].basis.lateral_axis, chain.regions[2].basis.lateral_axis)
        for boundary in (2.0, 3.0):
            epsilon = 1.0e-5
            point = np.asarray((0.35, boundary, 0.0))
            left = float(chain.evaluate(point - np.asarray((0.0, epsilon, 0.0))))
            center = float(chain.evaluate(point))
            right = float(chain.evaluate(point + np.asarray((0.0, epsilon, 0.0))))
            left_derivative = (center - left) / epsilon
            right_derivative = (right - center) / epsilon
            self.assertLess(abs(left_derivative - right_derivative), 2.0e-3)
            self.assertTrue(np.all(np.isfinite(chain.gradient(point))))

    def test_uneven_seven_station_regions_share_global_C1_source_derivatives(self) -> None:
        positions = np.asarray((0.0, 0.45, 1.35, 2.10, 3.55, 4.20, 6.10))
        lateral = np.asarray((0.82, 1.08, 0.91, 1.27, 1.04, 1.48, 1.22))
        anterior = np.asarray((0.58, 0.76, 0.63, 0.89, 0.70, 0.96, 0.78))
        posterior = np.asarray((0.44, 0.57, 0.49, 0.66, 0.53, 0.72, 0.60))
        stations = tuple(
            regional.AxialStation(
                f"seven-{index}",
                float(position),
                (0.0, float(position), 0.0),
                (float(lateral[index]), float(anterior[index]), float(posterior[index])),
                f"semantic:seven:{index}",
            )
            for index, position in enumerate(positions)
        )
        shared = basis()
        regions = (
            regional.AxialRegion("seven-pelvis", 0, 2, basis(0.18), shared, shared),
            regional.AxialRegion("seven-abdomen", 2, 4, basis(-0.24), shared, shared),
            regional.AxialRegion("seven-ribcage", 4, 6, basis(0.31), shared, shared),
        )
        radius_values = np.stack((lateral, anterior, posterior), axis=-1)
        independent_left = regional._pchip_slopes(positions[0:3], radius_values[0:3], "test independent left")[-1]
        independent_middle = regional._pchip_slopes(positions[2:5], radius_values[2:5], "test independent middle")[0]
        self.assertFalse(np.allclose(independent_left, independent_middle, rtol=0.0, atol=1.0e-8))

        chain = regional.AxialMassChain(stations, regions)
        center_values = np.asarray([station.center for station in stations])
        global_center_slopes = regional._pchip_slopes(positions, center_values, "test global centers")
        global_slopes = regional._pchip_slopes(positions, radius_values, "test global radii")
        self.assertTrue(np.array_equal(chain._runtimes[0]["center_slopes"][-1], global_center_slopes[2]))
        self.assertTrue(np.array_equal(chain._runtimes[1]["center_slopes"][0], global_center_slopes[2]))
        self.assertTrue(np.array_equal(chain._runtimes[1]["center_slopes"][-1], global_center_slopes[4]))
        self.assertTrue(np.array_equal(chain._runtimes[2]["center_slopes"][0], global_center_slopes[4]))
        self.assertTrue(np.array_equal(chain._runtimes[0]["radius_slopes"][-1], global_slopes[2]))
        self.assertTrue(np.array_equal(chain._runtimes[1]["radius_slopes"][0], global_slopes[2]))
        self.assertTrue(np.array_equal(chain._runtimes[1]["radius_slopes"][-1], global_slopes[4]))
        self.assertTrue(np.array_equal(chain._runtimes[2]["radius_slopes"][0], global_slopes[4]))
        for station_index in (2, 4):
            boundary = positions[station_index]
            epsilon = 1.0e-5
            point = np.asarray((0.31, boundary, 0.0))
            left_value = float(chain.evaluate(point - np.asarray((0.0, epsilon, 0.0))))
            center_value = float(chain.evaluate(point))
            right_value = float(chain.evaluate(point + np.asarray((0.0, epsilon, 0.0))))
            self.assertLess(abs((center_value - left_value) / epsilon - (right_value - center_value) / epsilon), 3.0e-3)
            trace = chain.operation_trace(point)
            regional_trace = trace.children[0]
            self.assertEqual(regional_trace.operator, "axial-regional-hard-min")
            self.assertEqual(regional_trace.tie_state, "tie")
            self.assertTrue(all(child.operator == "regional-span-leaf" for child in regional_trace.children))
            self.assertAlmostEqual(trace.reconstruct(), float(chain.evaluate(point)), places=12)

    def test_hard_min_sensitivity_does_not_promote_near_unequal_values_to_a_tie(self) -> None:
        minimum, active, sensitivity = regional._exact_hard_min_selection(
            (-1.0, -1.0 + 0.5 * regional._TIE_TOLERANCE),
            "test hard-min",
        )
        self.assertEqual(minimum, -1.0)
        self.assertEqual(active, (0,))
        self.assertEqual(sensitivity, (1.0, 0.0))
        self.assertEqual(
            regional._exact_hard_min_selection((-1.0, -1.0), "test exact tie")[1:],
            ((0, 1), (0.5, 0.5)),
        )

    def test_asymmetric_profile_interpolates_boundaries_and_labels_source_provenance(self) -> None:
        chain = make_chain()
        point = np.asarray((0.4, 1.5, 0.0))
        report = chain.contribution_report(point)
        self.assertEqual(report["diagnostic_kind"], "source-provenance")
        self.assertIs(report["geometric_influence"], False)
        self.assertEqual(report["selected_leaves"], ("pelvis:pelvis-top->waist",))
        self.assertIn("station:pelvis-top", report["source_semantic_keys"])
        self.assertIn("station:waist", report["source_semantic_keys"])
        self.assertNotIn("weights", report)
        self.assertEqual(report, chain.contribution_report(point.copy()))
        # The positive and negative forward radii are different at the same
        # station, so the two cardinal boundaries are both zero but distinct.
        centre = np.asarray((0.0, 1.0, 0.0))
        front = np.asarray((0.0, 1.0, 0.75))
        back = np.asarray((0.0, 1.0, -0.55))
        self.assertAlmostEqual(float(chain.evaluate(front)), 0.0, places=10)
        self.assertAlmostEqual(float(chain.evaluate(back)), 0.0, places=10)
        self.assertTrue(np.all(np.isfinite((front, back))))

    def test_bounds_enclose_station_profiles_and_finite_caps(self) -> None:
        chain = make_chain()
        lower, upper = chain.bounds
        self.assertTrue(np.all(np.isfinite(np.concatenate((lower, upper)))))
        self.assertTrue(np.all(upper > lower))
        for station in chain.stations:
            for axis, radius in zip((basis().lateral_axis, basis().axial_axis, basis().forward_axis), station.radii):
                point = np.asarray(station.center) + radius * np.asarray(axis)
                self.assertTrue(np.all(lower <= point + 1.0e-12))
                self.assertTrue(np.all(upper >= point - 1.0e-12))
        for point, dominance in ((np.asarray((0.0, -0.25, 0.0)), "start-cap"), (np.asarray((0.0, 4.25, 0.0)), "end-cap")):
            trace = chain.operation_trace(point)
            self.assertEqual(trace.children[0].operator, "axial-cap-leaf")
            self.assertEqual(trace.children[0].dominance, dominance)
            self.assertAlmostEqual(trace.reconstruct(), float(chain.evaluate(point)), places=12)

    def test_axial_validation_fails_closed(self) -> None:
        stations = (
            regional.AxialStation("a", 0.0, (0.0, 0.0, 0.0), (1.0, 1.0, 1.0)),
            regional.AxialStation("b", 1.0, (0.0, 1.0, 0.0), (1.0, 1.0, 1.0)),
        )
        with self.assertRaisesRegex(regional.RegionalHybridSurfaceError, "explicit AxialRegion"):
            regional.AxialMassChain(stations, ())
        with self.assertRaisesRegex(regional.RegionalHybridSurfaceError, "strictly increasing"):
            regional.AxialMassChain(
                (stations[0], regional.AxialStation("b", 0.0, stations[1].center, stations[1].radii)),
                (regional.AxialRegion("body", 0, 1),),
            )


class JunctionAndCompositeTests(unittest.TestCase):
    def _make_parent_targeted_composite(self):
        base = regional.SectionControl("base-field", (0.0, 0.0, 0.0), (0.20, 0.20, 0.20), "semantic:torso")
        alpha = regional.SectionControl("alpha-field", (0.0, 0.0, 0.0), (0.24, 0.22, 0.20), "semantic:alpha")
        beta = regional.SectionControl("beta-field", (0.0, 0.0, 0.0), (0.28, 0.26, 0.24), "semantic:beta")
        gamma = regional.SectionControl("gamma-field", (0.0, 0.0, 0.0), (0.32, 0.30, 0.28), "semantic:gamma")
        attachments = (
            regional.SectionAttachment("alpha", alpha, None, None, "route:alpha"),
            regional.SectionAttachment("beta", beta, None, None, "route:beta"),
            regional.SectionAttachment("gamma", gamma, None, None, "route:gamma"),
        )
        authority = lambda name: regional.AuthorityVolume(f"authority:{name}", (0.0, 0.0, 0.0), (1.0, 1.0, 1.0), 0.22)
        patches = (
            regional.ParentTargetedInterfacePatch("interface:torso->alpha", "torso", "alpha", base, alpha, authority("alpha"), 0.05, "interface:torso->alpha"),
            regional.ParentTargetedInterfacePatch("interface:torso->beta", "torso", "beta", base, beta, authority("beta"), 0.05, "interface:torso->beta"),
            regional.ParentTargetedInterfacePatch("interface:alpha->gamma", "alpha", "gamma", alpha, gamma, authority("gamma"), 0.05, "interface:alpha->gamma"),
        )
        return base, attachments, patches

    def test_terminal_constituent_analytic_ray_uses_exact_live_cap_implementation(self) -> None:
        chain = make_chain()
        station = chain.stations[-1]
        region = chain.regions[-1]
        self.assertIs(chain._runtimes[-1]["region"], region)
        self.assertIs(chain._runtimes[-1]["station_objects"][-1], station)
        constituent = chain._terminal_constituent(station, region, region.last_basis)
        self.assertIs(constituent.basis, region.last_basis)
        mu = 0.125
        toward = (1.25, 5.1, 0.8)
        boundary, interior, rho = constituent.analytic_ray_boundary_and_interior(
            toward,
            mu,
        )
        oracle_boundary, oracle_interior, oracle_rho = independent_endpoint_oracle(chain, False, toward, mu)
        self.assertTrue(np.allclose(boundary, oracle_boundary, rtol=0.0, atol=1.0e-12))
        self.assertTrue(np.allclose(interior, oracle_interior, rtol=0.0, atol=1.0e-12))
        self.assertAlmostEqual(rho, oracle_rho, places=12)
        self.assertGreater(rho, 0.0)
        self.assertLess(rho, 1.0)
        self.assertTrue(np.allclose(
            interior,
            np.asarray(station.center) + rho * (boundary - np.asarray(station.center)),
            rtol=0.0,
            atol=1.0e-12,
        ))
        self.assertAlmostEqual(float(constituent.evaluate(boundary)), 0.0, places=12)
        self.assertAlmostEqual(float(constituent.evaluate(interior)), -mu, places=12)
        self.assertEqual(float(chain.evaluate(interior)), float(constituent.evaluate(interior)))
        trace = chain.operation_trace(interior)
        self.assertEqual(trace.operator, "regional-axial-chain")
        self.assertEqual(trace.children[0].operator, "axial-cap-leaf")
        self.assertEqual(trace.children[0].dominance, "end-cap")
        self.assertEqual(trace.children[0].semantic_keys, ("station:rib-high", "region:ribcage"))
        self.assertEqual(constituent.operation_trace(interior), trace.children[0])

    def test_initial_constituent_analytic_ray_uses_exact_live_cap_and_independent_oracle(self) -> None:
        chain = make_chain()
        station = chain.stations[0]
        region = chain.regions[0]
        self.assertIs(chain._runtimes[0]["region"], region)
        self.assertIs(chain._runtimes[0]["station_objects"][0], station)
        constituent = chain._initial_constituent(station, region, region.first_basis)
        self.assertIs(constituent.basis, region.first_basis)
        self.assertTrue(constituent.lower)
        toward = (-0.9, -1.3, 0.65)
        mu = 0.10
        boundary, interior, rho = constituent.analytic_ray_boundary_and_interior(toward, mu)
        oracle_boundary, oracle_interior, oracle_rho = independent_endpoint_oracle(chain, True, toward, mu)
        self.assertTrue(np.allclose(boundary, oracle_boundary, rtol=0.0, atol=1.0e-12))
        self.assertTrue(np.allclose(interior, oracle_interior, rtol=0.0, atol=1.0e-12))
        self.assertAlmostEqual(rho, oracle_rho, places=12)
        self.assertAlmostEqual(float(constituent.evaluate(boundary)), 0.0, places=12)
        self.assertAlmostEqual(float(constituent.evaluate(interior)), -mu, places=12)
        self.assertEqual(float(chain.evaluate(interior)), float(constituent.evaluate(interior)))
        trace = chain.operation_trace(interior)
        self.assertEqual(trace.children[0].operator, "axial-cap-leaf")
        self.assertEqual(trace.children[0].dominance, "start-cap")
        self.assertEqual(constituent.operation_trace(interior), trace.children[0])
        with self.assertRaisesRegex(regional.RegionalHybridSurfaceError, "exact live initial station"):
            chain._initial_constituent(replace(station), region, region.first_basis)
        with self.assertRaisesRegex(regional.RegionalHybridSurfaceError, "enter the live initial cap domain"):
            constituent.analytic_ray_boundary((1.0, station.center[1], 0.0))

    def test_terminal_constituent_rejects_wrong_or_equal_valued_nonlive_operands(self) -> None:
        chain = make_chain()
        station = chain.stations[-1]
        region = chain.regions[-1]
        station_clone = replace(station)
        region_clone = replace(region)
        basis_clone = replace(region.last_basis)
        wrong_radii_clone = replace(station, radii=tuple(value * 0.9 for value in station.radii))
        other_chain = make_chain()
        for label, operands, message in (
            ("nonterminal", (chain.stations[-2], region, region.last_basis), "exact live terminal station"),
            ("equal-station-clone", (station_clone, region, region.last_basis), "exact live terminal station"),
            ("wrong-radii-clone", (wrong_radii_clone, region, region.last_basis), "exact live terminal station"),
            ("other-chain-station", (other_chain.stations[-1], region, region.last_basis), "exact live terminal station"),
            ("nonterminal-region", (station, chain.regions[-2], chain.regions[-2].last_basis), "exact live terminal region"),
            ("equal-region-clone", (station, region_clone, region_clone.last_basis), "exact live terminal region"),
            ("equal-basis-clone", (station, region, basis_clone), "exact live terminal region basis"),
        ):
            with self.subTest(label=label), self.assertRaisesRegex(regional.RegionalHybridSurfaceError, message):
                chain._terminal_constituent(*operands)
        constituent = chain._terminal_constituent(station, region, region.last_basis)
        with self.assertRaisesRegex(regional.RegionalHybridSurfaceError, "enter the live terminal cap domain"):
            constituent.analytic_ray_boundary((1.0, station.center[1], 0.0))
        with self.assertRaisesRegex(regional.RegionalHybridSurfaceError, "normalized level must be finite"):
            constituent.analytic_ray_boundary_and_interior((1.0, station.center[1] + 1.0, 0.0), constituent.field_scale)

    def test_retired_fixed_sampling_first_crossing_can_miss_a_real_narrow_excursion(self) -> None:
        sample_count = 256
        distances = np.linspace(0.0, 1.0, sample_count + 1)
        center = 100.5 / sample_count
        half_width = 0.20 / sample_count

        def narrow_excursion(values):
            return half_width**2 - (np.asarray(values) - center) ** 2

        sampled = narrow_excursion(distances)
        retired_crossings = np.flatnonzero((sampled[:-1] <= 0.0) & (sampled[1:] >= 0.0))
        self.assertEqual(len(retired_crossings), 0)
        self.assertGreater(float(narrow_excursion(center)), 0.0)
        self.assertAlmostEqual(float(narrow_excursion(center - half_width)), 0.0, places=18)
        self.assertAlmostEqual(float(narrow_excursion(center + half_width)), 0.0, places=18)

    def test_parent_targeted_composite_is_identical_for_all_small_registration_permutations(self) -> None:
        base, attachments, patches = self._make_parent_targeted_composite()
        points = np.asarray(((0.0, 0.0, 0.0), (0.3, 0.1, -0.1), (1.4, 0.0, 0.0)), dtype=np.float64)
        expected_field = regional.FullSectionComposite(base, attachments, interfaces=patches)
        expected_values = expected_field.evaluate(points)
        expected_trace = expected_field.operation_trace(points[1]).as_dict()
        for attachment_order in itertools.permutations(attachments):
            for patch_order in itertools.permutations(patches):
                field = regional.FullSectionComposite(base, attachment_order, interfaces=patch_order)
                self.assertTrue(np.array_equal(field.evaluate(points), expected_values))
                self.assertEqual(field.operation_trace(points[1]).as_dict(), expected_trace)
                self.assertEqual(tuple(item.identifier for item in field.interfaces), tuple(sorted(item.identifier for item in patches)))

    def test_parent_targeted_patch_uses_exact_formula_and_unrelated_route_can_dominate(self) -> None:
        base = regional.SectionControl("base-field", (0.0, 0.0, 0.0), (0.20, 0.20, 0.20), "semantic:torso")
        child = regional.SectionControl("child-field", (0.0, 0.0, 0.0), (0.24, 0.22, 0.20), "semantic:child")
        unrelated = regional.SectionControl("unrelated-field", (0.0, 0.0, 0.0), (2.0, 2.0, 2.0), "semantic:unrelated")
        authority = regional.AuthorityVolume("authority:interface", (0.0, 0.0, 0.0), (1.0, 1.0, 1.0), 0.22)
        patch = regional.ParentTargetedInterfacePatch("interface:torso->child", "torso", "child", base, child, authority, 0.10, "semantic:interface")
        point = np.asarray((0.0, 0.0, 0.0))
        parent_value = float(base.evaluate(point))
        child_value = float(child.evaluate(point))
        hard = min(parent_value, child_value)
        soft = regional._stable_soft_min(np.asarray((parent_value,)), np.asarray((child_value,)), 0.10)[0][0]
        expected_patch = hard + (soft - hard)
        self.assertEqual(float(patch.evaluate(point)), float(expected_patch))
        self.assertTrue(patch.validate_outside_hard_min())
        outside = np.asarray((2.0, 0.0, 0.0))
        self.assertEqual(float(patch.evaluate(outside)), min(float(base.evaluate(outside)), float(child.evaluate(outside))))
        composite = regional.FullSectionComposite(
            base,
            (
                regional.SectionAttachment("child", child),
                regional.SectionAttachment("unrelated", unrelated),
            ),
            interfaces=(patch,),
        )
        self.assertEqual(float(composite.evaluate(point)), float(unrelated.evaluate(point)))
        report = composite.contribution_report(point)
        self.assertGreater(report["geometric_influence"]["components"]["unrelated"], 0.0)

    def test_interface_trace_records_parent_child_authority_and_reconstructs_final(self) -> None:
        base, attachments, patches = self._make_parent_targeted_composite()
        field = regional.FullSectionComposite(base, attachments, interfaces=patches)
        trace = field.operation_trace(np.asarray((0.0, 0.0, 0.0)))
        self.assertEqual(trace.operator, "full-section-interface-composite")
        patch_nodes = []

        def visit(node):
            if node.operator == "parent-targeted-interface-patch":
                patch_nodes.append(node)
            for child in node.children:
                visit(child)

        visit(trace)
        self.assertEqual(len(patch_nodes), 3)
        self.assertEqual({(node.parent_id, node.child_id) for node in patch_nodes}, {
            ("torso", "alpha"), ("torso", "beta"), ("alpha", "gamma"),
        })
        self.assertTrue(all(node.authority_id and node.reconstruct() == node.value for node in patch_nodes))
        self.assertEqual(trace.reconstruct(), float(field.evaluate(np.asarray((0.0, 0.0, 0.0)))))

    def test_anisotropic_section_sweep_consumes_ordered_branch_and_reconstructs_exact_trace(self) -> None:
        sections = (
            regional.SectionStation("neck-collar", 0.0, (0.0, 0.0, 0.0), (0.40, 0.30, 0.20), "section:neck-collar", "source:neck-collar", 0),
            regional.SectionStation("cranium-mid", 1.0, (0.0, 1.0, 0.0), (0.35, 0.28, 0.18), "section:cranium-mid", "source:cranium-mid", 1),
            regional.SectionStation("cranium-crown", 2.0, (0.0, 2.0, 0.0), (0.30, 0.25, 0.16), "section:cranium-crown", "source:cranium-crown", 2),
            regional.SectionStation("muzzle-root", 3.0, (0.8, 1.5, 0.0), (0.24, 0.20, 0.14), "section:muzzle-root", "source:muzzle-root", 3),
        )
        connections = (
            regional.SectionConnection("neck-collar-to-cranium-mid", 0, 1, "vertical-neck-cranium"),
            regional.SectionConnection("cranium-mid-to-cranium-crown", 1, 2, "vertical-neck-cranium"),
            regional.SectionConnection("cranium-mid-to-muzzle-root", 1, 3, "forward-muzzle"),
        )
        closures = (
            regional.EndpointClosure("neck-collar-closure", sections[0].center, sections[0].radii, "closure:neck-collar", "source:neck-collar"),
            regional.EndpointClosure("cranium-crown-closure", sections[2].center, sections[2].radii, "closure:cranium-crown", "source:cranium-crown"),
            regional.EndpointClosure("muzzle-tip-closure", sections[3].center, sections[3].radii, "closure:muzzle-tip", "source:muzzle-root"),
        )
        sweep = regional.AnisotropicSectionSweep(sections, connections, closures, "head-neck")

        self.assertEqual(tuple(item.name for item in sweep.sections), tuple(item.name for item in sections))
        self.assertEqual(tuple(item.name for item in sweep.connections), tuple(item.name for item in connections))
        self.assertTrue(np.all(np.isfinite(np.concatenate(sweep.bounds))))
        point = np.asarray((0.0, 1.0, 0.15))
        value = float(sweep.evaluate(point))
        trace = sweep.operation_trace(point)
        self.assertEqual(trace.operator, "section-sweep-hard-min")
        self.assertEqual(len(trace.children), 6)
        self.assertEqual(trace.children[0].operator, "section-span-leaf")
        self.assertEqual(trace.children[-1].operator, "section-closure-leaf")
        self.assertAlmostEqual(trace.reconstruct(), value, places=12)
        provenance = sweep.source_provenance(point)
        self.assertEqual(provenance, sweep.source_provenance(point.copy()))
        self.assertEqual(provenance["route"], "head-neck")
        self.assertIn("section:cranium-mid", provenance["source_semantic_keys"])
        self.assertTrue(np.array_equal(sweep.evaluate(np.asarray((point, point))), np.asarray((value, value))))

    def test_anisotropic_section_sweep_rejects_missing_connectivity_and_closures(self) -> None:
        sections = (
            regional.SectionStation("a", 0.0, (0.0, 0.0, 0.0), (0.2, 0.2, 0.2)),
            regional.SectionStation("b", 1.0, (0.0, 1.0, 0.0), (0.2, 0.2, 0.2)),
            regional.SectionStation("c", 2.0, (0.0, 2.0, 0.0), (0.2, 0.2, 0.2)),
        )
        with self.assertRaisesRegex(regional.RegionalHybridSurfaceError, "explicit endpoint closures"):
            regional.AnisotropicSectionSweep(
                sections,
                (regional.SectionConnection("a-to-b", 0, 1, "route"),),
                (),
            )
        with self.assertRaisesRegex(regional.RegionalHybridSurfaceError, "unconnected station"):
            regional.AnisotropicSectionSweep(
                sections,
                (regional.SectionConnection("a-to-b", 0, 1, "route"),),
                (regional.EndpointClosure("a", sections[0].center, sections[0].radii),),
            )

        disconnected_sections = sections + (
            regional.SectionStation("d", 3.0, (0.0, 3.0, 0.0), (0.2, 0.2, 0.2)),
        )
        with self.assertRaisesRegex(regional.RegionalHybridSurfaceError, "connection graph must be connected"):
            regional.AnisotropicSectionSweep(
                disconnected_sections,
                (
                    regional.SectionConnection("a-to-b", 0, 1, "route"),
                    regional.SectionConnection("c-to-d", 2, 3, "route"),
                ),
                (regional.EndpointClosure("a", disconnected_sections[0].center, disconnected_sections[0].radii),),
            )


class PublicSurfaceTests(unittest.TestCase):
    def test_public_surface_excludes_retired_prior_path_names(self) -> None:
        expected = (
            "RegionalHybridSurfaceError",
            "RegionBasis",
            "AxialStation",
            "AxialRegion",
            "OperationTrace",
            "AxialMassChain",
            "SectionStation",
            "SectionConnection",
            "EndpointClosure",
            "SectionControl",
            "AnisotropicSectionSweep",
            "AuthorityVolume",
            "SectionAttachment",
            "ParentTargetedInterfacePatch",
            "FullSectionComposite",
        )
        self.assertEqual(regional.__all__, expected)
        retired = (
            "HybridSurfaceError",
            "ValidationError",
            "PelvicCup",
            "BilateralPelvicSaddle",
            "PelvicSaddle",
            "CupCarve",
            "RootKnot",
            "RootSweep",
            "RootAttachment",
            "NamedRoot",
            "RootAttachmentSpec",
            "CompositeHybridField",
            "CompositeField",
            "SmoothMinJunction",
            "LocalizedSmoothUnion",
            "LocalizedSmoothMin",
            "LocalizedSmoothUnionJunction",
            "SweepSection",
            "FullSection",
            "AnisotropicSection",
            "RouteConnection",
            "SectionEndpointClosure",
            "SourceEndpointClosure",
            "ControlMass",
            "FullSectionSweep",
            "SectionSweep",
            "AnisotropicSweep",
            "InterfacePatch",
            "ParentInterfacePatch",
            "SectionComposite",
            "CompositeSectionField",
            "RegionalSectionComposite",
            "AxialRegionBase",
            "RegionInterval",
            "JunctionAuthority",
            "make_axial_mass_chain",
            "make_root_sweep",
            "compose_hybrid_field",
            "validate_sampled_boundary_value_gradient_dominance",
            "validate_boundary_dominance",
            "smooth_min",
        )
        for name in retired:
            with self.subTest(name=name):
                self.assertNotIn(name, vars(regional))
                self.assertNotIn(name, regional.__all__)


if __name__ == "__main__":
    unittest.main()
