from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch


HERE = Path(__file__).resolve().parents[1]
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


regional_item = _load_module(
    "publish_regional_surface_preview",
    HERE / "publish_regional_surface_preview.py",
)
gallery = _load_module(
    "visual_review_publish_regional_surface_gallery_tests",
    HERE / "publish_regional_surface_gallery.py",
)


def _record(profile_id: str, path: Path | None = None) -> SimpleNamespace:
    return SimpleNamespace(
        id=profile_id,
        path=path or Path("/tmp/unused-source.json"),
        bytes=1,
        sha256="1" * 64,
        document=f"document-{profile_id}",
        namespace="main",
    )


def _renderer_source_snapshot(
    source: bytes = b"renderer-source-snapshot",
) -> object:
    root = Path("/immutable")
    dependencies = tuple(
        regional_item.RendererDependencySourceSnapshot(
            root / filename,
            dependency_source,
            hashlib.sha256(dependency_source).hexdigest(),
        )
        for filename in regional_item.RENDERER_DEPENDENCY_FILENAMES
        for dependency_source in [
            f"# retained gallery source: {filename}\n".encode("utf-8")
        ]
    )
    return regional_item.RendererSourceSnapshot(
        root / regional_item.RENDERER_ENTRYPOINT_FILENAME,
        source,
        hashlib.sha256(source).hexdigest(),
        dependencies,
    )


def _renderer_source_identity() -> dict[str, object]:
    return _renderer_source_snapshot().identity


def _implementation(renderer_source: dict[str, object]) -> dict[str, dict[str, object]]:
    return {
        "gallery": {"id": gallery.GALLERY_IMPLEMENTATION_ID, "bytes": 1, "sha256": "2" * 64},
        "item_api": {"id": regional_item.PUBLISHER_IMPLEMENTATION_ID, "bytes": 1, "sha256": "3" * 64},
        "renderer": renderer_source,
        "source_validator": {
            "id": "structural_profile_source_manifest.validate_structural_profile_source_manifest",
            "bytes": 1,
            "sha256": "4" * 64,
        },
    }


def _rendered_profile(profile_id: str, source_identity: dict[str, object]):
    record = _record(profile_id)
    inspected = gallery._InspectedProfile(
        record=record,
        prepared={"source": {"document": record.document, "namespace": "main"}},
        prepared_input_sha256="5" * 64,
        raw_prepared_form_sha256="6" * 64,
    )
    png = b"test-png-payload"
    png_hash = hashlib.sha256(png).hexdigest()
    publication_identity = {
        "prepared_input_sha256": inspected.prepared_input_sha256,
        "raw_prepared_form_sha256": inspected.raw_prepared_form_sha256,
        "png_sha256": png_hash,
        "renderer_source": source_identity,
        "renderer_source_sha256": source_identity["sha256"],
        "publisher": _implementation(source_identity)["item_api"],
        "candidate": {"sha256": "8" * 64},
        "binding": {"sha256": "9" * 64},
        "complete_test_marker": {"retained": True},
    }
    return gallery._RenderedProfile(
        inspected=inspected,
        png_bytes=png,
        png_sha256=png_hash,
        renderer_metadata_sha256="7" * 64,
        renderer_source_identity=source_identity,
        publication_identity=publication_identity,
    )


def _item_result(rendered: gallery._RenderedProfile) -> dict[str, object]:
    return {
        "png_bytes": rendered.png_bytes,
        "png_sha256": rendered.png_sha256,
        "prepared_input_sha256": rendered.inspected.prepared_input_sha256,
        "raw_prepared_form_sha256": rendered.inspected.raw_prepared_form_sha256,
        "renderer_source": rendered.renderer_source_identity,
        "publication_identity": rendered.publication_identity,
        "publication": {
            "format": regional_item.PREVIEW_FORMAT,
            "external_id": rendered.inspected.record.id,
            "source_variant": gallery.SOURCE_VARIANT_ID,
            "renderer_metadata_sha256": rendered.renderer_metadata_sha256,
            "identity": rendered.publication_identity,
            "candidate_contract": {},
        },
        "item_metadata": {
            "external_id": rendered.inspected.record.id,
            "source_variant": gallery.SOURCE_VARIANT_ID,
            "prepared_input_sha256": rendered.inspected.prepared_input_sha256,
            "raw_prepared_form_sha256": rendered.inspected.raw_prepared_form_sha256,
            "png_sha256": rendered.png_sha256,
            "renderer_metadata_sha256": rendered.renderer_metadata_sha256,
            "renderer_source": rendered.renderer_source_identity,
            "renderer_source_sha256": rendered.renderer_source_identity["sha256"],
            "identity": rendered.publication_identity,
        },
        "source": {
            "document": rendered.inspected.record.document,
            "namespace": rendered.inspected.record.namespace,
            "sha256": rendered.inspected.prepared_input_sha256,
        },
    }


class RegionalSurfaceGalleryTests(unittest.TestCase):
    def test_checkpoint_identity_accepts_retained_and_generic_mesh_settings(self) -> None:
        retained = gallery._validate_checkpoint_identity(
            gallery.EXACT_FIVE_CHECKPOINT_ID,
            gallery.EXPECTED_SAMPLES,
            gallery.EXPECTED_PADDING,
        )
        self.assertEqual(
            retained,
            {
                "id": gallery.EXACT_FIVE_CHECKPOINT_ID,
                "mesh": {
                    "samples_per_axis": gallery.EXPECTED_SAMPLES,
                    "padding": gallery.EXPECTED_PADDING,
                },
            },
        )

        generic = gallery._validate_checkpoint_identity(
            "regional-surface-custom-review",
            32,
            0.5,
        )
        self.assertEqual(generic["mesh"], {"samples_per_axis": 32, "padding": 0.5})

    def test_exact_five_checkpoint_rejects_non_retained_mesh_settings(self) -> None:
        with patch.object(gallery, "_refuse_existing_destination"):
            with self.assertRaisesRegex(
                gallery.RegionalSurfaceGalleryError,
                "requires mesh_samples=56 and mesh_padding=0.2",
            ):
                gallery.publish_regional_surface_gallery(
                    Path("/unused/reviews"),
                    Path("/unused/manifest.json"),
                    Path("/unused/creature-kernel"),
                    review_id=gallery.EXACT_FIVE_CHECKPOINT_ID,
                    mesh_samples=55,
                    mesh_padding=gallery.EXPECTED_PADDING,
                )

    def test_implementation_identity_uses_all_retained_executed_sources(self) -> None:
        renderer_identity = _renderer_source_identity()
        gallery_source_bytes = (HERE / "publish_regional_surface_gallery.py").read_bytes()
        expected = {
            "item_api": regional_item._publisher_implementation_identity(),
            "source_validator": gallery.source_manifest_validator._implementation_source_identity(),
        }
        with tempfile.TemporaryDirectory() as directory:
            live_path = Path(directory) / "publish_regional_surface_gallery.py"
            live_path.write_bytes(gallery_source_bytes)
            snapshot_module = _load_module(
                "visual_review_regional_gallery_live_replacement_test",
                live_path,
            )
            live_path.write_bytes(b"raise RuntimeError('replacement must not be hashed')\n")
            implementation = snapshot_module._implementation_identity(renderer_identity)

        self.assertEqual(implementation["gallery"]["id"], gallery.GALLERY_IMPLEMENTATION_ID)
        self.assertEqual(implementation["gallery"]["bytes"], len(gallery_source_bytes))
        self.assertEqual(
            implementation["gallery"]["sha256"],
            hashlib.sha256(gallery_source_bytes).hexdigest(),
        )
        self.assertEqual(implementation["item_api"], expected["item_api"])
        self.assertEqual(implementation["source_validator"], expected["source_validator"])
        self.assertEqual(implementation["renderer"], renderer_identity)

    def test_child_stderr_is_not_included_in_nonzero_inspection_error(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.json"
            source.write_bytes(b"x")
            record = _record(gallery.PROFILE_IDS[0], source)
            record.bytes = 1
            record.sha256 = hashlib.sha256(b"x").hexdigest()
            executable = gallery._PinnedExecutable(Path("/bin/true"), "8" * 64, 1)
            with patch.object(
                gallery,
                "_run_inspection",
                return_value=(b"{}", b"secret child stderr and path", 23),
            ):
                with self.assertRaisesRegex(
                    gallery.RegionalSurfaceGalleryError,
                    "exited with status 23",
                ) as raised:
                    gallery._inspect_profile(record, executable, root)
            self.assertNotIn("secret child stderr", str(raised.exception))
            self.assertNotIn(str(source), str(raised.exception))

    def test_duplicate_members_in_inspection_output_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.json"
            source.write_bytes(b"x")
            record = _record(gallery.PROFILE_IDS[0], source)
            record.bytes = 1
            record.sha256 = hashlib.sha256(b"x").hexdigest()
            executable = gallery._PinnedExecutable(Path("/bin/true"), "8" * 64, 1)
            duplicate = b'{"format":"first","format":"second"}'
            with patch.object(
                gallery,
                "_run_inspection",
                return_value=(duplicate, b"secret stderr", 0),
            ):
                with self.assertRaisesRegex(
                    gallery.RegionalSurfaceGalleryError,
                    "duplicate JSON object members",
                ) as raised:
                    gallery._inspect_profile(record, executable, root)
            self.assertNotIn("secret stderr", str(raised.exception))

    def test_unexpected_inspection_callable_exception_is_sanitized_by_api(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.json"
            source.write_bytes(b"x")
            records = tuple(_record(profile_id, source) for profile_id in gallery.PROFILE_IDS)
            for record in records:
                record.bytes = 1
                record.sha256 = hashlib.sha256(b"x").hexdigest()
            validation = SimpleNamespace(sources=records)
            executable = gallery._PinnedExecutable(Path("/bin/true"), "8" * 64, 1)

            with patch.object(gallery, "_refuse_existing_destination"), patch.object(
                gallery,
                "_validate_sampling",
                return_value=(gallery.EXPECTED_SAMPLES, gallery.EXPECTED_PADDING),
            ), patch.object(
                gallery, "_validate_source_manifest", return_value=validation
            ), patch.object(
                gallery, "_validate_executable", return_value=SimpleNamespace()
            ), patch.object(
                gallery, "_pin_executable", return_value=executable
            ), patch.object(
                gallery,
                "_run_inspection",
                side_effect=RuntimeError("secret inspection callable internals"),
            ):
                with self.assertRaisesRegex(
                    gallery.RegionalSurfaceGalleryError,
                    "unexpected gallery failure",
                ) as raised:
                    gallery.publish_regional_surface_gallery(
                        Path("/unused/reviews"),
                        Path("/unused/manifest.json"),
                        Path("/unused/creature-kernel"),
                        review_id="gallery-inspection-error",
                        mesh_samples=gallery.EXPECTED_SAMPLES,
                        mesh_padding=gallery.EXPECTED_PADDING,
                    )
        self.assertNotIn("secret inspection callable internals", str(raised.exception))

    def test_item_and_group_lineage_retain_complete_direct_publication_identity(self) -> None:
        source_identity = _renderer_source_identity()
        rendered = tuple(
            _rendered_profile(profile_id, source_identity)
            for profile_id in gallery.PROFILE_IDS
        )
        validation = SimpleNamespace(
            manifest=SimpleNamespace(
                format=gallery.SOURCE_MANIFEST_FORMAT,
                sha256="a" * 64,
                bytes=1,
                candidate_sha256="b" * 64,
                base_source_sha256="c" * 64,
            ),
            generator=SimpleNamespace(sha256="d" * 64),
            profile_ids=gallery.PROFILE_IDS,
            sources=tuple(item.inspected.record for item in rendered),
        )
        implementation = _implementation(source_identity)
        checkpoint_identity = gallery._validate_checkpoint_identity(
            gallery.EXACT_FIVE_CHECKPOINT_ID,
            gallery.EXPECTED_SAMPLES,
            gallery.EXPECTED_PADDING,
        )
        descriptor = gallery._descriptor_snapshot(
            validation,
            SimpleNamespace(bytes=1, sha256="e" * 64),
            implementation,
            rendered,
            gallery.EXPECTED_SAMPLES,
            gallery.EXPECTED_PADDING,
            checkpoint_identity=checkpoint_identity,
        )
        self.assertEqual(descriptor["checkpoint_identity"], checkpoint_identity)
        self.assertEqual(descriptor["lineage"]["renderer_source"], source_identity)
        self.assertEqual(
            [item["renderer_source"] for item in descriptor["profiles"]],
            [source_identity] * len(gallery.PROFILE_IDS),
        )
        expected_publication_identities = [
            item.publication_identity for item in rendered
        ]
        self.assertEqual(
            [item["sha256"] for item in descriptor["lineage"]["publication_identity_inventory"]],
            [
                hashlib.sha256(
                    gallery._canonical_bytes(identity, "test publication identity")
                ).hexdigest()
                for identity in expected_publication_identities
            ],
        )

        with tempfile.TemporaryDirectory() as directory:
            manifest_path, _ = gallery._review_manifest(
                rendered,
                descriptor,
                Path(directory),
                review_id=gallery.EXACT_FIVE_CHECKPOINT_ID,
                mesh_samples=gallery.EXPECTED_SAMPLES,
                mesh_padding=gallery.EXPECTED_PADDING,
            )
            review = json.loads(manifest_path.read_text(encoding="utf-8"))
            normalized_review, _ = gallery.common.read_rich_manifest(manifest_path)
        group = review["groups"][0]
        self.assertEqual(
            review["subject_context"]["authored_summary"]["text"],
            "This gallery compares five simplified stylized biped profiles generated by the same regional-surface method, standard neutral first, to judge body-region transitions and coherent variation.",
        )
        self.assertIn(source_identity["sha256"], group["description"])
        self.assertIn(
            descriptor["lineage"]["publication_identities_sha256"],
            group["description"],
        )
        self.assertEqual(len(group["items"]), len(expected_publication_identities))
        for item, expected_identity in zip(
            group["items"], expected_publication_identities, strict=True
        ):
            self.assertEqual(item["metadata"]["renderer_source"], source_identity)
            self.assertEqual(
                item["metadata"]["hashes"]["renderer_source_sha256"],
                source_identity["sha256"],
            )
            self.assertEqual(item["metadata"]["publication_identity"], expected_identity)
            self.assertEqual(
                item["metadata"]["publication_identity_sha256"],
                hashlib.sha256(
                    gallery._canonical_bytes(expected_identity, "test publication identity")
                ).hexdigest(),
            )
        self.assertEqual(
            [
                item["metadata"]["publication_identity"]
                for item in normalized_review["groups"][0]["items"]
            ],
            expected_publication_identities,
        )

    def test_gallery_reuses_one_renderer_snapshot_for_every_profile(self) -> None:
        records = tuple(_record(profile_id) for profile_id in gallery.PROFILE_IDS)
        validation = SimpleNamespace(sources=records)
        snapshot = _renderer_source_snapshot(b"renderer-source")
        implementation = _implementation(snapshot.identity)
        inspected = {
            record.id: gallery._InspectedProfile(record, {}, "1" * 64, "2" * 64)
            for record in records
        }
        render_calls: list[dict[str, object]] = []

        def fake_render(prepared: dict[str, object], **kwargs: object) -> dict[str, object]:
            render_calls.append(kwargs)
            return {}

        def fake_rendered_item(
            item: gallery._InspectedProfile,
            rendered: object,
            *,
            expected_renderer_source: dict[str, object],
            expected_item_api: dict[str, object],
        ) -> gallery._RenderedProfile:
            self.assertEqual(expected_item_api, implementation["item_api"])
            return _rendered_profile(item.record.id, expected_renderer_source)

        with tempfile.TemporaryDirectory() as directory:
            with patch.object(gallery, "_refuse_existing_destination"), patch.object(
                gallery,
                "_validate_sampling",
                return_value=(gallery.EXPECTED_SAMPLES, gallery.EXPECTED_PADDING),
            ), patch.object(
                gallery, "_validate_source_manifest", return_value=validation
            ), patch.object(
                gallery, "_validate_executable", return_value=SimpleNamespace()
            ), patch.object(
                gallery, "_pin_executable", return_value=SimpleNamespace()
            ), patch.object(
                regional_item, "_snapshot_renderer_source", return_value=snapshot
            ) as snapshot_source, patch.object(
                gallery, "_implementation_identity", return_value=implementation
            ) as implementation_identity, patch.object(
                gallery, "_inspect_profile", side_effect=lambda record, executable, root: inspected[record.id]
            ), patch.object(
                gallery,
                "render_and_validate_regional_surface_item",
                side_effect=fake_render,
            ), patch.object(
                gallery, "_rendered_item", side_effect=fake_rendered_item
            ), patch.object(
                gallery,
                "_descriptor_snapshot",
                return_value={"implementation": implementation},
            ), patch.object(
                gallery,
                "_review_manifest",
                return_value=(Path(directory) / "manifest.json", {}),
            ), patch.object(
                gallery,
                "publish_session",
                return_value={"session": "unused"},
            ):
                summary = gallery.publish_regional_surface_gallery(
                    Path("/unused/reviews"),
                    Path("/unused/manifest.json"),
                    Path("/unused/creature-kernel"),
                    review_id="gallery-snapshot-reuse",
                    mesh_samples=gallery.EXPECTED_SAMPLES,
                    mesh_padding=gallery.EXPECTED_PADDING,
                )

        self.assertEqual(summary["items"], len(gallery.PROFILE_IDS))
        self.assertEqual(len(render_calls), len(gallery.PROFILE_IDS))
        self.assertTrue(
            all(call["renderer_source_snapshot"] is snapshot for call in render_calls)
        )
        snapshot_source.assert_called_once_with()
        implementation_identity.assert_called_once_with(snapshot.identity)

    def test_item_renderer_identity_mismatch_is_rejected(self) -> None:
        expected = _renderer_source_identity()
        rendered = _rendered_profile(gallery.PROFILE_IDS[0], {**expected, "sha256": "f" * 64})
        with self.assertRaisesRegex(
            gallery.RegionalSurfaceGalleryError,
            "renderer source identity",
        ):
            gallery._rendered_item(
                rendered.inspected,
                _item_result(rendered),
                expected_renderer_source=expected,
                expected_item_api=_implementation(expected)["item_api"],
            )

    def test_unexpected_renderer_exception_is_fixed_at_gallery_boundary(self) -> None:
        records = tuple(_record(profile_id) for profile_id in gallery.PROFILE_IDS)
        validation = SimpleNamespace(sources=records)
        snapshot = _renderer_source_snapshot(b"renderer")
        with patch.object(gallery, "_refuse_existing_destination"), patch.object(
            gallery, "_validate_sampling", return_value=(gallery.EXPECTED_SAMPLES, gallery.EXPECTED_PADDING)
        ), patch.object(gallery, "_validate_source_manifest", return_value=validation), patch.object(
            gallery, "_validate_executable", return_value=SimpleNamespace()
        ), patch.object(gallery, "_pin_executable", return_value=SimpleNamespace()), patch.object(
            regional_item, "_snapshot_renderer_source", return_value=snapshot
        ), patch.object(gallery, "_implementation_identity", return_value=_implementation(snapshot.identity)), patch.object(
            gallery, "_inspect_profile", side_effect=lambda record, executable, root: gallery._InspectedProfile(
                record, {}, "1" * 64, "2" * 64
            )
        ), patch.object(
            gallery,
            "render_and_validate_regional_surface_item",
            side_effect=RuntimeError("secret renderer implementation"),
        ):
            with self.assertRaisesRegex(
                gallery.RegionalSurfaceGalleryError,
                "unexpected renderer failure",
            ) as raised:
                gallery.publish_regional_surface_gallery(
                    Path("/unused/reviews"),
                    Path("/unused/manifest.json"),
                    Path("/unused/creature-kernel"),
                    review_id="gallery-render-error",
                    mesh_samples=gallery.EXPECTED_SAMPLES,
                    mesh_padding=gallery.EXPECTED_PADDING,
                )
        self.assertNotIn("secret renderer implementation", str(raised.exception))

    def test_unexpected_publisher_exception_is_fixed_at_gallery_boundary(self) -> None:
        records = tuple(_record(profile_id) for profile_id in gallery.PROFILE_IDS)
        validation = SimpleNamespace(sources=records)
        snapshot = _renderer_source_snapshot(b"renderer")
        rendered = _rendered_profile(gallery.PROFILE_IDS[0], snapshot.identity)
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(gallery, "_refuse_existing_destination"), patch.object(
                gallery, "_validate_sampling", return_value=(gallery.EXPECTED_SAMPLES, gallery.EXPECTED_PADDING)
            ), patch.object(gallery, "_validate_source_manifest", return_value=validation), patch.object(
                gallery, "_validate_executable", return_value=SimpleNamespace()
            ), patch.object(gallery, "_pin_executable", return_value=SimpleNamespace()), patch.object(
                regional_item, "_snapshot_renderer_source", return_value=snapshot
            ), patch.object(gallery, "_implementation_identity", return_value=_implementation(snapshot.identity)), patch.object(
                gallery, "_inspect_profile", side_effect=lambda record, executable, root: gallery._InspectedProfile(
                    record, {}, "1" * 64, "2" * 64
                )
            ), patch.object(
                gallery,
                "render_and_validate_regional_surface_item",
                return_value={},
            ), patch.object(
                gallery, "_rendered_item", return_value=rendered
            ), patch.object(
                gallery, "_descriptor_snapshot", return_value={"implementation": _implementation(snapshot.identity)}
            ), patch.object(
                gallery, "_review_manifest", return_value=(Path(directory) / "manifest.json", {})
            ), patch.object(
                gallery,
                "publish_session",
                side_effect=RuntimeError("secret publisher implementation"),
            ):
                with self.assertRaisesRegex(
                    gallery.RegionalSurfaceGalleryError,
                    "unexpected publication failure",
                ) as raised:
                    gallery.publish_regional_surface_gallery(
                        Path("/unused/reviews"),
                        Path("/unused/manifest.json"),
                        Path("/unused/creature-kernel"),
                        review_id="gallery-publish-error",
                        mesh_samples=gallery.EXPECTED_SAMPLES,
                        mesh_padding=gallery.EXPECTED_PADDING,
                    )
        self.assertNotIn("secret publisher implementation", str(raised.exception))


if __name__ == "__main__":
    unittest.main()
