#!/usr/bin/env python3
"""Focused tests for the one-purpose neutral alternative rerender route."""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import stat
import sys
import tempfile
import unittest
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import patch


HERE = Path(__file__).resolve()
REPOSITORY_ROOT = HERE.parents[3]
VISUAL_REVIEW_ROOT = HERE.parents[1]
EXPERIMENT_ROOT = REPOSITORY_ROOT / "experiments" / "current-form-surface-preview"
sys.path.insert(0, str(VISUAL_REVIEW_ROOT))
sys.path.insert(0, str(EXPERIMENT_ROOT))

import generate_structural_profile_sources as profile_generator  # noqa: E402
import rerender_neutral_alternative as rerender  # noqa: E402


class NeutralAlternativeRerenderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="ck-neutral-rerender-tests-")
        self.root = Path(self.temp.name)
        self.output_parent = self.root / "outputs"
        self.output_parent.mkdir()
        self.source_dir = self.root / "sources"
        profile_generator.write_sources(
            profile_generator.DEFAULT_CANDIDATE,
            profile_generator.DEFAULT_SOURCE,
            self.source_dir,
        )
        self.source_manifest = self.source_dir / "manifest.json"
        self.creature_kernel = self.root / "creature-kernel"
        self.creature_kernel.write_bytes(b"test creature-kernel executable")
        self.creature_kernel.chmod(0o700)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def _profile(self, manifest: dict[str, object]) -> SimpleNamespace:
        first = manifest["profiles"][0]  # type: ignore[index]
        assert isinstance(first, dict)
        return SimpleNamespace(
            profile_id=rerender.STANDARD_NEUTRAL_PROFILE_ID,
            source_document=first["document"],
            source_namespace=manifest["source"]["base_namespace"],  # type: ignore[index]
            source_sha256=first["sha256"],
            form=object(),
            descriptors=(object(),),
            producer_envelope_sha256="b" * 64,
            producer_variant_sha256="c" * 64,
        )

    def _mesh(self) -> SimpleNamespace:
        return SimpleNamespace(
            vertices=((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)),
            faces=((0, 1, 2),),
            normals=((0.0, 0.0, 1.0),) * 3,
            metrics={"vertex_count": 3, "face_count": 1, "watertight": True},
            render_components=(
                SimpleNamespace(bounds=((-1.0, -1.0, -1.0), (1.0, 1.0, 1.0))),
            ),
        )

    def _run_mocked(self, output_id: str = "neutral-rerender") -> tuple[dict[str, object], dict[str, object], object, object]:
        manifest = json.loads(self.source_manifest.read_text(encoding="utf-8"))
        inspected = self._profile(manifest)
        mesh = self._mesh()
        inspected_calls: list[str] = []
        inspect_context: dict[str, object] = {}

        def fake_inspect(profile, source_ref, source_bytes, executable, temporary_root, expected_namespace):
            inspected_calls.append(profile["id"])
            inspect_context.update(
                {
                    "profile": profile,
                    "source_ref": source_ref,
                    "source_bytes": source_bytes,
                    "executable": executable,
                    "executable_bytes": executable.read_bytes(),
                    "temporary_root": temporary_root,
                    "expected_namespace": expected_namespace,
                }
            )
            return inspected

        prepared = (inspected, "guide", ())
        baseline_bound = ((0.0, 0.0, 0.0), (1.0, 1.0, 1.0))
        capture_bound = ((-1.0, -1.0, -1.0), (2.0, 2.0, 2.0))

        def fake_write_ply(path: Path, rendered_mesh) -> None:
            self.assertIs(rendered_mesh, mesh)
            path.write_bytes(b"ply test output\n")

        def fake_render(path: Path, vertices, faces, variant_id, *, guide, bounds, render_components) -> None:
            self.assertIs(vertices, mesh.vertices)
            self.assertIs(faces, mesh.faces)
            self.assertEqual(variant_id, rerender.STANDARD_NEUTRAL_PROFILE_ID)
            self.assertEqual(guide, "guide")
            self.assertEqual(bounds, capture_bound)
            self.assertIs(render_components, mesh.render_components)
            rerender.successor._baseline.Image.new(
                "RGB",
                (1800, 1500),
                (22, 33, 44),
            ).save(path, format="PNG")

        published = patch.object(rerender.exact_five_publisher, "publish_session")
        with patch.object(rerender, "_inspect_profile", side_effect=fake_inspect) as inspect, patch.object(
            rerender.exact_five_publisher,
            "_shared_capture_bound",
            return_value=(baseline_bound, (prepared,)),
        ) as shared_capture_bound, patch.object(
            rerender.exact_five_publisher,
            "_capture_bound_with_components",
            return_value=capture_bound,
        ) as capture_bound_with_components, patch.object(
            rerender.exact_five_publisher.successor._baseline,
            "_validate_hybrid_guide",
        ) as validate_hybrid_guide, patch.object(
            rerender.successor,
            "build_neutral_alternative_variant",
            return_value=mesh,
        ) as build, patch.object(
            rerender.successor,
            "_write_ply",
            side_effect=fake_write_ply,
        ) as write_ply, patch.object(
            rerender.successor._baseline,
            "_render",
            side_effect=fake_render,
        ) as render, published as publish_session:
            result = rerender.rerender_neutral_alternative(
                self.output_parent,
                output_id,
                self.source_manifest,
                creature_kernel=self.creature_kernel,
                samples=rerender.successor.ALTERNATIVE_MIN_SAMPLES,
            )
        output = self.output_parent / output_id
        return result, {
            "inspect": inspect,
            "calls": inspected_calls,
            "inspect_context": inspect_context,
            "shared_capture_bound": shared_capture_bound,
            "capture_bound_with_components": capture_bound_with_components,
            "validate_hybrid_guide": validate_hybrid_guide,
            "build": build,
            "write_ply": write_ply,
            "render": render,
            "publish": publish_session,
        }, output, inspected

    def test_inspects_first_profile_builds_once_and_installs_exact_inventory(self) -> None:
        result, calls, output, _inspected = self._run_mocked()
        manifest = json.loads(self.source_manifest.read_text(encoding="utf-8"))
        first_profile = manifest["profiles"][0]
        self.assertEqual(calls["calls"], [rerender.STANDARD_NEUTRAL_PROFILE_ID])
        inspect_args, inspect_kwargs = calls["inspect"].call_args
        self.assertEqual(inspect_kwargs, {})
        self.assertEqual(inspect_args[0], first_profile)
        self.assertEqual(inspect_args[1].path, self.source_dir / first_profile["file"])
        self.assertEqual(inspect_args[2], inspect_args[1].path.read_bytes())
        self.assertEqual(inspect_args[5], manifest["source"]["base_namespace"])
        self.assertEqual(inspect_args[4], calls["inspect_context"]["temporary_root"])
        self.assertEqual(inspect_args[3], calls["inspect_context"]["executable"])
        self.assertEqual(calls["inspect_context"]["executable_bytes"], self.creature_kernel.read_bytes())
        self.assertEqual(inspect_args[3].parent, inspect_args[4])
        calls["inspect"].assert_called_once()
        calls["shared_capture_bound"].assert_called_once_with([_inspected])
        calls["capture_bound_with_components"].assert_called_once_with(
            ((0.0, 0.0, 0.0), (1.0, 1.0, 1.0)),
            [(_inspected, "guide", calls["build"].return_value)],
        )
        calls["validate_hybrid_guide"].assert_called_once_with(
            "guide",
            ((-1.0, -1.0, -1.0), (2.0, 2.0, 2.0)),
        )
        calls["build"].assert_called_once_with(
            _inspected.form,
            _inspected.descriptors,
            samples=rerender.successor.ALTERNATIVE_MIN_SAMPLES,
            padding=rerender.successor.DEFAULT_PADDING,
            smooth_k=rerender.successor.DEFAULT_SMOOTH_K,
        )
        expected_surface = calls["inspect_context"]["temporary_root"] / rerender.OUTPUT_PLY_NAME
        calls["write_ply"].assert_called_once_with(expected_surface, calls["build"].return_value)
        expected_png = calls["inspect_context"]["temporary_root"] / rerender.OUTPUT_PNG_NAME
        calls["render"].assert_called_once_with(
            expected_png,
            calls["build"].return_value.vertices,
            calls["build"].return_value.faces,
            rerender.STANDARD_NEUTRAL_PROFILE_ID,
            guide="guide",
            bounds=((-1.0, -1.0, -1.0), (2.0, 2.0, 2.0)),
            render_components=calls["build"].return_value.render_components,
        )
        calls["build"].assert_called_once()
        calls["render"].assert_called_once()
        calls["publish"].assert_not_called()
        self.assertEqual(result["status"], "success")
        self.assertEqual({entry.name for entry in output.iterdir()}, set(rerender.EXPECTED_OUTPUTS))
        self.assertTrue(all(entry.is_file() and not entry.is_symlink() for entry in output.iterdir()))

    def test_identity_is_self_consistent_and_binds_lineage_metrics_outputs_and_implementation(self) -> None:
        _result, calls, output, inspected = self._run_mocked("neutral-rerender-identity")
        identity = json.loads((output / rerender.OUTPUT_IDENTITY_NAME).read_text(encoding="utf-8"))
        digest_input = dict(identity)
        digest_input.pop("identity_sha256")
        self.assertEqual(
            identity["identity_sha256"],
            hashlib.sha256(rerender.successor._canonical(digest_input)).hexdigest(),
        )
        self.assertEqual(identity["profile_id"], rerender.STANDARD_NEUTRAL_PROFILE_ID)
        self.assertEqual(identity["neutral_variant_id"], "neutral-v0")
        self.assertEqual(identity["source_document_sha256"], inspected.source_sha256)
        self.assertEqual(identity["producer_envelope_sha256"], inspected.producer_envelope_sha256)
        self.assertEqual(identity["neutral_variant_sha256"], inspected.producer_variant_sha256)
        self.assertEqual(identity["samples_per_axis"], rerender.successor.ALTERNATIVE_MIN_SAMPLES)
        self.assertEqual(identity["metrics"], {"face_count": 1, "vertex_count": 3, "watertight": True})
        expected_output_hashes = {
            rerender.OUTPUT_PLY_NAME: (identity["surface_bytes"], identity["surface_sha256"]),
            rerender.OUTPUT_PNG_NAME: (identity["png_bytes"], identity["png_sha256"]),
        }
        self.assertEqual(set(identity["outputs"]), set(expected_output_hashes))
        for name, expected in identity["outputs"].items():
            path = output / name
            self.assertEqual(expected["bytes"], path.stat().st_size)
            self.assertEqual(expected["sha256"], hashlib.sha256(path.read_bytes()).hexdigest())
            self.assertEqual(
                (expected["bytes"], expected["sha256"]),
                expected_output_hashes[name],
            )
        implementation = identity["implementation"]
        self.assertEqual(
            implementation["identity_sha256"],
            hashlib.sha256(
                rerender.successor._canonical(
                    {"files": implementation["files"], "runtime": implementation["runtime"]}
                )
            ).hexdigest(),
        )
        self.assertEqual(
            identity["successor"]["implementation_sha256"],
            implementation["identity_sha256"],
        )
        expected_file_names = {
            "rerender_helper",
            "exact_five_publisher",
            "successor",
            "renderer",
            "profile_source_generator",
            "common_safety_helper",
            "publication_helper",
            "inspection_helper",
            "launcher",
            "requirements",
            "pinned_executable",
        }
        self.assertEqual(set(identity["implementation"]["files"]), expected_file_names)
        for file_identity in identity["implementation"]["files"].values():
            self.assertGreater(file_identity["bytes"], 0)
            self.assertRegex(file_identity["sha256"], r"^[0-9a-f]{64}$")
        self.assertEqual(identity["implementation"]["files"]["pinned_executable"]["bytes"], self.creature_kernel.stat().st_size)
        runtime = implementation["runtime"]
        self.assertEqual(runtime["python"]["executable"], sys.executable)
        self.assertEqual(runtime["python"]["version"], sys.version)
        self.assertIn("does not capture all ambient", runtime["fingerprint_scope"])
        self.assertEqual(
            runtime["requirements_sha256"],
            implementation["files"]["requirements"]["sha256"],
        )
        self.assertEqual(
            {item["distribution"] for item in runtime["requirements"]},
            {"numpy", "scikit-image", "Pillow"},
        )
        self.assertTrue(runtime["module_files"])
        for module_file in runtime["module_files"]:
            self.assertGreaterEqual(module_file["bytes"], 0)
            self.assertRegex(module_file["sha256"], r"^[0-9a-f]{64}$")
        self.assertEqual(calls["publish"].call_count, 0)

    def test_runtime_identity_snapshots_modules_before_reading_module_files(self) -> None:
        requirements = self.root / "requirements.txt"
        requirements.write_text(
            f"numpy=={importlib.metadata.version('numpy')}\n",
            encoding="utf-8",
        )
        mutating_name = "numpy._runtime_identity_mutating_module"
        added_name = "numpy._runtime_identity_added_module"
        sentinel = object()
        previous_modules = {
            name: sys.modules.get(name, sentinel)
            for name in (mutating_name, added_name)
        }
        lookup_names: list[str] = []
        mutating_module = ModuleType(mutating_name)

        def module_getattr(name: str) -> None:
            lookup_names.append(name)
            sys.modules[added_name] = ModuleType(added_name)
            return None

        mutating_module.__getattr__ = module_getattr  # type: ignore[attr-defined]
        sys.modules[mutating_name] = mutating_module
        try:
            with patch.object(
                rerender,
                "_file_identity",
                return_value={"bytes": 0, "sha256": "0" * 64},
            ):
                runtime = rerender._runtime_identity(requirements)
        finally:
            for name, previous in previous_modules.items():
                if previous is sentinel:
                    sys.modules.pop(name, None)
                else:
                    sys.modules[name] = previous

        self.assertEqual(lookup_names, ["__file__"])
        self.assertEqual(runtime["requirements"][0]["import"], "numpy")
        self.assertIsInstance(runtime["module_files"], list)

    def test_runtime_import_name_normalizes_distribution_variants(self) -> None:
        variants = {
            "numpy": "numpy",
            "NUMPY": "numpy",
            "scikit-image": "skimage",
            "scikit_image": "skimage",
            "SCIKIT.IMAGE": "skimage",
            "Pillow": "PIL",
            "pillow": "PIL",
            "PILLOW": "PIL",
        }
        for distribution, expected_import in variants.items():
            with self.subTest(distribution=distribution):
                self.assertEqual(rerender._runtime_import_name(distribution), expected_import)

    def test_pin_successor_error_is_translated(self) -> None:
        with patch.object(
            rerender.exact_five_publisher,
            "_pin_executable",
            side_effect=rerender.exact_five_publisher.SuccessorAnatomyGalleryError("pin failed"),
        ):
            with self.assertRaisesRegex(rerender.NeutralAlternativeRerenderError, "pin failed"):
                rerender.rerender_neutral_alternative(
                    self.output_parent,
                    "pin-error",
                    self.source_manifest,
                    creature_kernel=self.creature_kernel,
                )

    def test_publication_create_error_is_translated(self) -> None:
        with patch.object(
            rerender.publication_helpers,
            "_create_staging",
            side_effect=rerender.publication_helpers.PublishError("create failed"),
        ):
            with self.assertRaisesRegex(rerender.NeutralAlternativeRerenderError, "create failed"):
                self._run_mocked("create-error")

    def test_publication_install_error_is_translated(self) -> None:
        with patch.object(
            rerender.publication_helpers,
            "_rename_noreplace",
            side_effect=rerender.publication_helpers.PublishError("install failed"),
        ):
            with self.assertRaisesRegex(rerender.NeutralAlternativeRerenderError, "install failed"):
                self._run_mocked("install-error")
        self.assertEqual(list(self.output_parent.iterdir()), [])

    def test_existing_destination_and_symlink_are_refused_before_expensive_work(self) -> None:
        existing = self.output_parent / "already-there"
        existing.mkdir()
        marker = existing / "keep"
        marker.write_bytes(b"keep")
        with patch.object(rerender, "_inspect_profile") as inspect, patch.object(
            rerender.successor,
            "build_neutral_alternative_variant",
        ) as build, patch.object(rerender.successor._baseline, "_render") as render:
            with self.assertRaisesRegex(rerender.NeutralAlternativeRerenderError, "refusing to overwrite"):
                rerender.rerender_neutral_alternative(
                    self.output_parent,
                    existing.name,
                    self.source_manifest,
                    creature_kernel=self.creature_kernel,
                )
        inspect.assert_not_called()
        build.assert_not_called()
        render.assert_not_called()
        self.assertEqual(marker.read_bytes(), b"keep")

        symlink_target = self.root / "symlink-target"
        symlink_target.mkdir()
        linked = self.output_parent / "linked-destination"
        linked.symlink_to(symlink_target, target_is_directory=True)
        with self.assertRaisesRegex(rerender.NeutralAlternativeRerenderError, "destination symlink"):
            rerender.rerender_neutral_alternative(
                self.output_parent,
                linked.name,
                self.source_manifest,
                creature_kernel=self.creature_kernel,
            )

    def test_sampling_floor_uses_successor_alternative_minimum(self) -> None:
        with self.assertRaisesRegex(rerender.NeutralAlternativeRerenderError, "between 56 and"):
            rerender.rerender_neutral_alternative(
                self.output_parent,
                "below-floor",
                self.source_manifest,
                creature_kernel=self.creature_kernel,
                samples=rerender.successor.ALTERNATIVE_MIN_SAMPLES - 1,
            )


if __name__ == "__main__":
    unittest.main()
