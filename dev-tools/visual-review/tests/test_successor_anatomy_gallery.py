#!/usr/bin/env python3
"""Focused tests for the disposable successor anatomy-gallery adapter."""

from __future__ import annotations

import copy
import hashlib
import io
import json
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


HERE = Path(__file__).resolve()
REPOSITORY_ROOT = HERE.parents[3]
VISUAL_REVIEW_ROOT = HERE.parents[1]
EXPERIMENT_ROOT = REPOSITORY_ROOT / "experiments" / "current-form-surface-preview"
sys.path.insert(0, str(VISUAL_REVIEW_ROOT))
sys.path.insert(0, str(EXPERIMENT_ROOT))

import generate_structural_profile_sources as profile_generator  # noqa: E402
import publish_successor_anatomy_gallery as adapter  # noqa: E402


PROFILE_IDS = list(adapter.PROFILE_IDS)


class SuccessorAnatomyGalleryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="ck-successor-anatomy-tests-")
        self.root = Path(self.temp.name)
        self.creature_kernel = REPOSITORY_ROOT / "target" / "debug" / "creature-kernel"
        self.source_dir = self.root / "sources"
        self.expected_sources: dict[str, dict[str, int | str]] = {}
        profile_generator.write_sources(
            profile_generator.DEFAULT_CANDIDATE,
            profile_generator.DEFAULT_SOURCE,
            self.source_dir,
        )
        self.source_manifest = self.source_dir / "manifest.json"

    def tearDown(self) -> None:
        self.temp.cleanup()

    def require_creature_kernel(self, path: Path | None = None) -> Path:
        executable = path or self.creature_kernel
        if not executable.is_file():
            self.skipTest(f"requires built inspection CLI at {executable}")
        return executable

    def _run_gallery(
        self,
        review_id: str,
        *,
        samples: int = adapter.MIN_GALLERY_SAMPLES,
        creature_kernel: Path | None = None,
    ) -> dict[str, object]:
        creature_kernel = self.require_creature_kernel(creature_kernel)
        published: dict[str, object] = {}
        events: list[tuple[str, str]] = []
        (self.root / "reviews").mkdir(exist_ok=True)

        def fake_publish(_reviews_root: Path, manifest_path: Path, *, expected_sources=None):
            published["manifest"] = json.loads(manifest_path.read_text(encoding="utf-8"))
            normalized, _sources = adapter.common.read_rich_manifest(manifest_path)
            self.assertEqual(
                [item["id"] for item in normalized["groups"][0]["items"]],
                PROFILE_IDS,
            )
            self.assertEqual(
                [item["metadata"] for item in normalized["groups"][0]["items"]],
                [item["metadata"] for item in published["manifest"]["groups"][0]["items"]],
            )
            published["expected_sources"] = expected_sources
            self.expected_sources = expected_sources
            return {"schema_version": 1, "id": review_id, "session": "test", "review": "test/review.json", "assets": 5}

        def fake_build(form, descriptors, **_configuration):
            neutral_descriptors = next(
                item[1] for item in form.variants if item[0] == adapter.NEUTRAL_VARIANT_ID
            )
            self.assertEqual(descriptors, neutral_descriptors)
            events.append(("build", form.source["document"]))
            return SimpleNamespace(
                vertices=object(),
                faces=object(),
                render_components=(
                    SimpleNamespace(
                        bounds=((-100.0, -100.0, -100.0), (100.0, 100.0, 100.0))
                    ),
                ),
            )

        def fake_render(path: Path, _vertices, _faces, variant_id: str, **_kwargs) -> None:
            events.append(("render", variant_id))
            colour = {
                PROFILE_IDS[0]: (80, 90, 100),
                PROFILE_IDS[1]: (100, 90, 80),
                PROFILE_IDS[2]: (80, 110, 90),
                PROFILE_IDS[3]: (110, 80, 100),
                PROFILE_IDS[4]: (90, 110, 80),
            }[variant_id]
            adapter.successor._baseline.Image.new(
                "RGB",
                (adapter.EXPECTED_CANVAS["width"], adapter.EXPECTED_CANVAS["height"]),
                colour,
            ).save(path, format="PNG")

        with patch.object(
            adapter.successor,
            "build_neutral_alternative_variant",
            side_effect=fake_build,
        ) as alternative_builder, patch.object(
            adapter.successor,
            "build_variant",
            side_effect=AssertionError("the rejected v9 builder must not be used"),
        ) as v9_builder, patch.object(
            adapter.successor._baseline, "_render", side_effect=fake_render
        ), patch.object(adapter, "publish_session", side_effect=fake_publish), patch.object(
            adapter, "_run_inspection", wraps=adapter._run_inspection
        ) as run_inspection:
            result = adapter.publish_successor_anatomy_gallery(
                self.root / "reviews",
                self.source_manifest,
                creature_kernel=creature_kernel,
                samples=samples,
                review_id=review_id,
            )
        review = published["manifest"]
        self.assertEqual(result["images"], 5)
        self.assertEqual(alternative_builder.call_count, 5)
        self.assertEqual(v9_builder.call_count, 0)
        self.assertEqual(run_inspection.call_count, 5)
        self.assertEqual([event[0] for event in events], ["build"] * 5 + ["render"] * 5)
        commands = [call.args[0] for call in run_inspection.call_args_list]
        self.assertEqual(
            [command[1:3] for command in commands],
            [["inspect-provisional-form", "--input"]] * 5,
        )
        self.assertEqual(len({command[0] for command in commands}), 1)
        self.assertTrue(all(command[0] != str(creature_kernel) for command in commands))
        self.assertEqual(len({command[-1] for command in commands}), 5)
        self.assertEqual(
            [form.source["document"] for form, _ in (call.args for call in alternative_builder.call_args_list)],
            [
                f"{json.loads(self.source_manifest.read_text(encoding='utf-8'))['source']['base_document']}"
                f"__{profile_generator.SOURCE_DOCUMENT_SUFFIX}__{profile_id}"
                for profile_id in PROFILE_IDS
            ],
        )
        return review  # type: ignore[return-value]

    def test_missing_reviews_root_fails_before_source_or_render_work(self) -> None:
        missing = self.root / "missing-reviews-root"
        with patch.object(adapter, "_validate_source_manifest") as validate_manifest:
            with self.assertRaisesRegex(
                adapter.SuccessorAnatomyGalleryError,
                "reviews root must already exist",
            ):
                adapter.publish_successor_anatomy_gallery(
                    missing,
                    self.source_manifest,
                    creature_kernel=self.creature_kernel,
                )
        validate_manifest.assert_not_called()

    def test_existing_destination_fails_before_work_and_is_preserved(self) -> None:
        reviews_root = self.root / "reviews"
        reviews_root.mkdir()
        cases = ("directory", "symlink")
        for kind in cases:
            with self.subTest(kind=kind):
                destination = reviews_root / f"existing-{kind}"
                preserved = self.root / f"preserved-{kind}"
                preserved.write_bytes(f"preserved {kind}".encode())
                if kind == "directory":
                    destination.mkdir()
                    (destination / "keep").write_bytes(b"keep")
                    expected_error = "refusing to overwrite existing destination"
                else:
                    destination.symlink_to(preserved)
                    expected_error = "refusing existing destination symlink"

                with patch.object(adapter, "_validate_source_manifest") as validate_manifest, patch.object(
                    adapter, "_validate_executable"
                ) as validate_executable, patch.object(adapter, "_inspect_profile") as inspect_profile, patch.object(
                    adapter, "_run_inspection"
                ) as run_inspection, patch.object(
                    adapter.successor, "build_neutral_alternative_variant"
                ) as build, patch.object(adapter.successor._baseline, "_render") as render, patch.object(
                    adapter, "publish_session"
                ) as publish:
                    with self.assertRaisesRegex(adapter.SuccessorAnatomyGalleryError, expected_error):
                        adapter.publish_successor_anatomy_gallery(
                            reviews_root,
                            self.source_manifest,
                            creature_kernel=self.creature_kernel,
                            review_id=destination.name,
                        )

                validate_manifest.assert_not_called()
                validate_executable.assert_not_called()
                inspect_profile.assert_not_called()
                run_inspection.assert_not_called()
                build.assert_not_called()
                render.assert_not_called()
                publish.assert_not_called()
                self.assertEqual(preserved.read_bytes(), f"preserved {kind}".encode())
                if kind == "directory":
                    self.assertEqual((destination / "keep").read_bytes(), b"keep")
                else:
                    self.assertTrue(destination.is_symlink())

    def test_later_profile_alternative_builder_failure_fails_closed_before_render_or_install(self) -> None:
        creature_kernel = self.require_creature_kernel()
        reviews_root = self.root / "reviews"
        reviews_root.mkdir()
        expected_profile_order = [
            "standard_neutral_reference",
            "compact_broad_short_limb_large_head",
            "tall_narrow_long_legged",
            "slender_long_limb",
            "stocky_broad_chested",
        ]
        self.assertEqual(PROFILE_IDS, expected_profile_order)
        base_document = json.loads(self.source_manifest.read_text(encoding="utf-8"))["source"]["base_document"]
        expected_documents = [
            f"{base_document}__{profile_generator.SOURCE_DOCUMENT_SUFFIX}__{profile_id}"
            for profile_id in expected_profile_order
        ]
        attempted_documents: list[str] = []

        def build_until_later_failure(form, descriptors, **_configuration):
            document = form.source["document"]
            attempted_documents.append(document)
            if document == expected_documents[2]:
                raise adapter.successor.SuccessorPreviewError("intentional later-profile alternative builder failure")
            neutral_descriptors = next(
                item[1] for item in form.variants if item[0] == adapter.NEUTRAL_VARIANT_ID
            )
            self.assertEqual(descriptors, neutral_descriptors)
            return SimpleNamespace(
                vertices=object(),
                faces=object(),
                render_components=(
                    SimpleNamespace(
                        bounds=((-100.0, -100.0, -100.0), (100.0, 100.0, 100.0))
                    ),
                ),
            )

        with patch.object(
            adapter.successor,
            "build_neutral_alternative_variant",
            side_effect=build_until_later_failure,
        ) as build, patch.object(adapter.successor._baseline, "_render") as render, patch.object(
            adapter, "publish_session"
        ) as publish:
            with self.assertRaisesRegex(
                adapter.SuccessorAnatomyGalleryError,
                "tall_narrow_long_legged successor surface build failed: intentional later-profile alternative builder failure",
            ):
                adapter.publish_successor_anatomy_gallery(
                    reviews_root,
                    self.source_manifest,
                    creature_kernel=creature_kernel,
                    review_id="later-profile-builder-failure",
                )

        self.assertEqual(attempted_documents, expected_documents[:3])
        self.assertEqual(build.call_count, 3)
        render.assert_not_called()
        publish.assert_not_called()
        self.assertFalse((reviews_root / "later-profile-builder-failure").exists())
        self.assertEqual(tuple(reviews_root.iterdir()), ())

    def test_active_profile_contract_is_generator_owned_and_neutral_first(self) -> None:
        generation_mode, profile_ids = adapter._active_profile_contract()
        self.assertEqual(profile_ids, tuple(profile_generator.ACTIVE_PROFILE_IDS))
        self.assertEqual(generation_mode, profile_generator.DEFAULT_GENERATION_MODE)
        self.assertEqual(profile_ids[0], profile_generator.STANDARD_NEUTRAL_PROFILE_ID)
        self.assertEqual(len(profile_ids), 5)

    def test_malformed_active_generation_mode_returns_fail_closed_exit_status(self) -> None:
        malformed_mode = "malformed-generation-mode"
        generator = SimpleNamespace(
            ACTIVE_PROFILE_IDS=tuple(profile_generator.ACTIVE_PROFILE_IDS),
            DEFAULT_GENERATION_MODE=malformed_mode,
            HISTORICAL_GENERATION_MODE=profile_generator.HISTORICAL_GENERATION_MODE,
            STANDARD_NEUTRAL_PROFILE_ID=profile_generator.STANDARD_NEUTRAL_PROFILE_ID,
            ProfileGenerationError=profile_generator.ProfileGenerationError,
            _profile_contract=profile_generator._profile_contract,
        )
        with patch.dict(
            adapter._PROFILE_SOURCE_CONSTANTS,
            {"DEFAULT_GENERATION_MODE": malformed_mode},
        ), patch.object(adapter.profile_source_generator, "_module", generator), patch(
            "sys.stderr", new_callable=io.StringIO
        ) as stderr:
            status = adapter.main(
                [
                    "--root",
                    str(self.root),
                    "--source-manifest",
                    str(self.source_manifest),
                ]
            )
        self.assertEqual(status, 2)
        self.assertIn(
            "active profile generation mode is invalid: unsupported structural profile generation mode",
            stderr.getvalue(),
        )
        self.assertNotIn("Traceback", stderr.getvalue())

    def test_unexpected_profile_contract_error_is_not_masked(self) -> None:
        def raise_unexpected(_mode: str) -> tuple[int, tuple[str, ...] | None]:
            raise RuntimeError("unexpected profile-contract implementation failure")

        generator = SimpleNamespace(
            ACTIVE_PROFILE_IDS=tuple(profile_generator.ACTIVE_PROFILE_IDS),
            DEFAULT_GENERATION_MODE=profile_generator.DEFAULT_GENERATION_MODE,
            HISTORICAL_GENERATION_MODE=profile_generator.HISTORICAL_GENERATION_MODE,
            STANDARD_NEUTRAL_PROFILE_ID=profile_generator.STANDARD_NEUTRAL_PROFILE_ID,
            ProfileGenerationError=profile_generator.ProfileGenerationError,
            _profile_contract=raise_unexpected,
        )
        with patch.object(adapter.profile_source_generator, "_module", generator):
            with self.assertRaisesRegex(RuntimeError, "unexpected profile-contract implementation failure"):
                adapter._active_profile_contract()

    def test_internal_profile_contract_attribute_error_is_not_masked(self) -> None:
        def raise_internal(_mode: str) -> tuple[int, tuple[str, ...] | None]:
            raise AttributeError("internal profile-contract implementation failure")

        with patch.object(profile_generator, "_profile_contract", side_effect=raise_internal):
            with self.assertRaises(AttributeError) as raised:
                adapter._active_profile_contract()

        self.assertIs(type(raised.exception), AttributeError)
        self.assertEqual(str(raised.exception), "internal profile-contract implementation failure")

    def test_missing_profile_contract_fails_closed_before_publication(self) -> None:
        generator_values = vars(profile_generator).copy()
        generator_values.pop("_profile_contract")
        generator = SimpleNamespace(**generator_values)
        reviews_root = self.root / "reviews"
        reviews_root.mkdir()

        with patch.object(adapter.profile_source_generator, "_module", generator), patch.object(
            adapter, "publish_session"
        ) as publish_session:
            with self.assertRaisesRegex(
                adapter.SuccessorAnatomyGalleryError,
                "missing _profile_contract",
            ):
                adapter.publish_successor_anatomy_gallery(
                    reviews_root,
                    self.source_manifest,
                    creature_kernel=self.creature_kernel,
                )

        publish_session.assert_not_called()
        self.assertEqual(tuple(reviews_root.iterdir()), ())

    def test_missing_tail_signature_fails_closed_before_publication(self) -> None:
        generator_values = vars(profile_generator).copy()
        generator_values.pop("_tail_signature")
        generator = SimpleNamespace(**generator_values)
        reviews_root = self.root / "reviews"
        reviews_root.mkdir()

        with patch.object(adapter.profile_source_generator, "_module", generator), patch.object(
            adapter, "publish_session"
        ) as publish_session:
            with self.assertRaisesRegex(
                adapter.SuccessorAnatomyGalleryError,
                "missing _tail_signature",
            ):
                adapter.publish_successor_anatomy_gallery(
                    reviews_root,
                    self.source_manifest,
                    creature_kernel=self.creature_kernel,
                )

        publish_session.assert_not_called()
        self.assertEqual(tuple(reviews_root.iterdir()), ())

    def test_internal_tail_signature_attribute_error_is_not_masked(self) -> None:
        def raise_internal(_source_object: dict[str, object]) -> list[int]:
            raise AttributeError("internal tail-signature implementation failure")

        with patch.object(profile_generator, "_tail_signature", side_effect=raise_internal):
            with self.assertRaises(AttributeError) as raised:
                adapter._validate_source_manifest(self.source_manifest)

        self.assertIs(type(raised.exception), AttributeError)
        self.assertEqual(str(raised.exception), "internal tail-signature implementation failure")

    def test_generator_profile_order_drift_is_rejected(self) -> None:
        with patch.object(
            adapter.profile_source_generator,
            "ACTIVE_PROFILE_IDS",
            tuple(reversed(profile_generator.ACTIVE_PROFILE_IDS)),
        ):
            with self.assertRaisesRegex(
                adapter.SuccessorAnatomyGalleryError,
                "loaded generator active profile IDs drifted",
            ):
                adapter._validate_source_manifest(self.source_manifest)

    def test_loaded_profile_ids_list_drift_is_rejected(self) -> None:
        with patch.object(
            adapter.profile_source_generator,
            "ACTIVE_PROFILE_IDS",
            list(profile_generator.ACTIVE_PROFILE_IDS),
        ):
            with self.assertRaisesRegex(
                adapter.SuccessorAnatomyGalleryError,
                "loaded generator active profile IDs drifted",
            ):
                adapter._validate_source_manifest(self.source_manifest)

    def test_loaded_generation_constant_type_drift_is_rejected(self) -> None:
        with patch.object(
            adapter.profile_source_generator,
            "DEFAULT_GENERATION_MODE",
            [profile_generator.DEFAULT_GENERATION_MODE],
        ):
            with self.assertRaisesRegex(
                adapter.SuccessorAnatomyGalleryError,
                "loaded generator DEFAULT_GENERATION_MODE must be a non-empty string",
            ):
                adapter._validate_source_manifest(self.source_manifest)

    def test_historical_generation_mode_is_rejected(self) -> None:
        with patch.object(
            adapter.profile_source_generator,
            "DEFAULT_GENERATION_MODE",
            profile_generator.HISTORICAL_GENERATION_MODE,
        ):
            with self.assertRaisesRegex(
                adapter.SuccessorAnatomyGalleryError,
                "loaded generator DEFAULT_GENERATION_MODE drifted",
            ):
                adapter._validate_source_manifest(self.source_manifest)

    def test_active_generation_mode_is_forwarded_explicitly(self) -> None:
        with patch.object(
            adapter.profile_source_generator,
            "generate_sources",
            wraps=profile_generator.generate_sources,
        ) as generate_sources:
            adapter._validate_source_manifest(self.source_manifest)
        self.assertEqual(
            generate_sources.call_args.kwargs["mode"],
            profile_generator.DEFAULT_GENERATION_MODE,
        )

    def test_active_generated_manifest_with_decimal_metre_signatures_validates(self) -> None:
        manifest, _manifest_bytes, records = adapter._validate_source_manifest(self.source_manifest)
        signatures = [profile["tail_signature"] for profile in manifest["profiles"]]
        self.assertTrue(any(type(number) is float for signature in signatures for number in signature))
        self.assertEqual(len(records), 5)

    def test_malformed_tail_signatures_are_rejected_fail_closed(self) -> None:
        manifest = json.loads(self.source_manifest.read_text(encoding="utf-8"))
        original_signature = manifest["profiles"][0]["tail_signature"]
        malformed_signatures = (
            ("bool", [True, *original_signature[1:]], "tail_signature is invalid", False),
            ("zero", [0, *original_signature[1:]], "tail_signature is invalid", False),
            ("negative", [-0.1, *original_signature[1:]], "tail_signature is invalid", False),
            ("wrong-length", original_signature[:-1], "tail_signature is invalid", False),
            ("mismatch", [original_signature[0] + 1, *original_signature[1:]], "does not match", False),
            ("nan", [float("nan"), *original_signature[1:]], "not finite UTF-8 JSON", True),
            ("infinity", [float("inf"), *original_signature[1:]], "not finite UTF-8 JSON", True),
        )
        for name, signature, expected_error, noncanonical in malformed_signatures:
            with self.subTest(name=name):
                malformed = copy.deepcopy(manifest)
                malformed["profiles"][0]["tail_signature"] = signature
                if noncanonical:
                    self.source_manifest.write_text(
                        json.dumps(malformed, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=True) + "\n",
                        encoding="utf-8",
                    )
                else:
                    self.source_manifest.write_bytes(profile_generator.canonical_bytes(malformed))
                with self.assertRaisesRegex(adapter.SuccessorAnatomyGalleryError, expected_error):
                    adapter._validate_source_manifest(self.source_manifest)

    def test_profile_source_constant_reader_does_not_execute_source(self) -> None:
        marker = self.root / "executed"
        source_path = self.root / "generator.py"
        source_path.write_text(
            "ACTIVE_PROFILE_IDS = (\"standard_neutral_reference\",)\n"
            f"open({str(marker)!r}, \"w\").write(\"executed\")\n",
            encoding="utf-8",
        )
        with patch.object(adapter, "_profile_source_path", return_value=source_path):
            values = adapter._read_profile_source_constants()
        self.assertEqual(values["ACTIVE_PROFILE_IDS"], ("standard_neutral_reference",))
        self.assertFalse(marker.exists())

    def test_profile_source_constant_reader_bounds_oversized_stream(self) -> None:
        class OversizedStream:
            def __init__(self) -> None:
                self.read_sizes: list[int] = []

            def __enter__(self) -> "OversizedStream":
                return self

            def __exit__(self, *_args: object) -> None:
                return None

            def read(self, size: int = -1) -> bytes:
                self.read_sizes.append(size)
                return b"x" * (adapter._PROFILE_SOURCE_MAX_BYTES + 1)

        stream = OversizedStream()

        class SourcePath:
            def open(self, mode: str) -> OversizedStream:
                self.mode = mode
                return stream

        source_path = SourcePath()
        with patch.object(adapter, "_profile_source_path", return_value=source_path):
            with self.assertRaisesRegex(
                adapter.SuccessorAnatomyGalleryError,
                "exceeds the bounded source size",
            ):
                adapter._read_profile_source_constants()
        self.assertEqual(stream.read_sizes, [adapter._PROFILE_SOURCE_MAX_BYTES + 1])
        self.assertEqual(source_path.mode, "rb")

    def test_gallery_is_one_ordered_group_with_neutral_only_shared_bound_and_distinct_lineage(self) -> None:
        review = self._run_gallery("successor-anatomy-test")
        self.assertEqual(review["title"], adapter.TITLE)
        self.assertIn("not structural, pose, or skeleton evidence", review["description"])
        self.assertIn("acceptance evidence", review["instructions"])
        self.assertEqual(len(review["groups"]), 1)
        group = review["groups"][0]
        self.assertEqual(group["selection_mode"], "none")
        items = group["items"]
        self.assertEqual([item["id"] for item in items], PROFILE_IDS)
        self.assertEqual(
            [item["metadata"]["producer"]["variant_id"] for item in items],
            [adapter.successor.ALTERNATIVE_NEUTRAL_PROFILE_ID] * 5,
        )
        self.assertEqual(
            [item["metadata"]["producer"]["profile_id"] for item in items],
            [adapter.successor.ALTERNATIVE_NEUTRAL_PROFILE_ID] * 5,
        )
        self.assertEqual(
            [item["metadata"]["successor"] for item in items],
            [{
                "format": adapter.successor.ALTERNATIVE_FORMAT,
                "consumer_id": adapter.successor.ALTERNATIVE_CONSUMER_ID,
                "region_id": adapter.successor.ALTERNATIVE_REGION_ID,
                "config": items[0]["metadata"]["successor"]["config"],
                "implementation_sha256": items[0]["metadata"]["successor"]["implementation_sha256"],
            }] * 5,
        )
        self.assertEqual(
            review["subject_context"]["descriptor_snapshot"]["successor"]["format"],
            adapter.successor.ALTERNATIVE_FORMAT,
        )
        self.assertEqual(
            review["subject_context"]["descriptor_snapshot"]["successor"]["consumer_id"],
            adapter.successor.ALTERNATIVE_CONSUMER_ID,
        )
        self.assertEqual(
            review["subject_context"]["descriptor_snapshot"]["successor"]["region_id"],
            adapter.successor.ALTERNATIVE_REGION_ID,
        )

        bounds = [item["metadata"]["capture"]["global_capture_bound"] for item in items]
        self.assertEqual(bounds, [bounds[0]] * 5)
        self.assertEqual(items[0]["metadata"]["capture"]["canvas"], adapter.EXPECTED_CANVAS)
        self.assertEqual(items[0]["metadata"]["capture"]["views"], list(adapter.EXPECTED_VIEWS))
        self.assertEqual(
            [item["metadata"]["source_hashes"]["source_document_sha256"] for item in items],
            list(dict.fromkeys(item["metadata"]["source_hashes"]["source_document_sha256"] for item in items)),
        )
        self.assertEqual(
            [item["metadata"]["producer"]["envelope_sha256"] for item in items],
            list(dict.fromkeys(item["metadata"]["producer"]["envelope_sha256"] for item in items)),
        )
        self.assertEqual(
            [item["metadata"]["producer"]["variant_sha256"] for item in items],
            list(dict.fromkeys(item["metadata"]["producer"]["variant_sha256"] for item in items)),
        )
        self.assertEqual(
            [item["metadata"]["output_identity"]["sha256"] for item in items],
            list(dict.fromkeys(item["metadata"]["output_identity"]["sha256"] for item in items)),
        )
        self.assertEqual(
            [item["metadata"]["source_manifest_sha256"] for item in items],
            [hashlib.sha256(self.source_manifest.read_bytes()).hexdigest()] * 5,
        )
        self.assertEqual(
            review["subject_context"]["descriptor_snapshot"]["source_manifest"]["profile_ids"],
            PROFILE_IDS,
        )
        self.assertEqual(
            len(review["subject_context"]["descriptor_snapshot"]["producer"]["envelope_sha256_by_profile"]),
            5,
        )
        implementation = review["subject_context"]["descriptor_snapshot"]["implementation"]
        self.assertRegex(implementation["identity_sha256"], r"^[0-9a-f]{64}$")
        self.assertEqual(
            set(implementation["files"]),
            {"adapter", "successor", "renderer", "producer_executable"},
        )
        self.assertEqual(
            {item["metadata"]["successor"]["implementation_sha256"] for item in items},
            {implementation["identity_sha256"]},
        )
        self.assertEqual(
            {item["metadata"]["output_identity"]["identity_sha256"] for item in items},
            set(review["subject_context"]["descriptor_snapshot"]["output_identity_sha256_by_profile"]),
        )
        self.assertEqual(
            [item["metadata"]["producer"]["source_binding"]["profile_id"] for item in items],
            PROFILE_IDS,
        )
        self.assertTrue(
            all(
                item["metadata"]["producer"]["source_binding"]["mode"] == "identifier-only"
                for item in items
            )
        )
        self.assertNotIn("source_sha256", items[0]["metadata"]["producer"])
        for name, file_identity in implementation["files"].items():
            self.assertGreater(file_identity["bytes"], 0)
            self.assertRegex(file_identity["sha256"], r"^[0-9a-f]{64}$", name)
            if name != "producer_executable":
                self.assertFalse(Path(file_identity["repository_path"]).is_absolute())
        self.assertEqual(
            list(self.expected_sources),
            PROFILE_IDS,
        )
        self.assertEqual(
            {
                item["id"]: {
                    "bytes": item["metadata"]["output_identity"]["bytes"],
                    "sha256": item["metadata"]["output_identity"]["sha256"],
                }
                for item in items
            },
            self.expected_sources,
        )

    def test_metadata_is_deterministic_for_same_inputs(self) -> None:
        first = self._run_gallery("successor-anatomy-test-a")
        second = self._run_gallery("successor-anatomy-test-b")
        self.assertEqual(first["description"], second["description"])
        self.assertEqual(first["instructions"], second["instructions"])
        self.assertEqual(first["subject_context"], second["subject_context"])
        self.assertEqual(
            [item["metadata"] for item in first["groups"][0]["items"]],
            [item["metadata"] for item in second["groups"][0]["items"]],
        )

    def test_sampling_below_the_known_five_profile_floor_is_rejected(self) -> None:
        with self.assertRaisesRegex(adapter.SuccessorAnatomyGalleryError, "between 56 and 96"):
            self._run_gallery("successor-anatomy-low-resolution", samples=20)

    def test_file_identity_rejects_growth_after_initial_size_check(self) -> None:
        identity_path = self.root / "identity-source"
        identity_path.write_bytes(b"")

        class GrowingStream(io.BytesIO):
            def __init__(self, data: bytes, descriptor: int) -> None:
                super().__init__(data)
                self._descriptor = descriptor

            def fileno(self) -> int:
                return self._descriptor

        with identity_path.open("rb") as initial, GrowingStream(b"12345", initial.fileno()) as growing, patch.object(
            adapter.common,
            "open_source_reference",
            return_value=growing,
        ):
            with self.assertRaisesRegex(adapter.SuccessorAnatomyGalleryError, "exceeds the bounded size"):
                adapter._file_identity(
                    identity_path,
                    4,
                    "growing identity source",
                    repository_path=False,
                )

    def test_failed_inspection_reports_exit_status_before_parsing_stdout(self) -> None:
        manifest, _manifest_bytes, records = adapter._validate_source_manifest(self.source_manifest)
        profile, source_ref, _source_value, source_bytes = records[0]
        inspection_root = self.root / "failed-inspection"
        inspection_root.mkdir()
        with patch.object(
            adapter,
            "_run_inspection",
            return_value=(b"not-json", b"boom", 7),
        ), patch.object(adapter, "_parse_inspection") as parse:
            with self.assertRaisesRegex(
                adapter.SuccessorAnatomyGalleryError,
                "exited with status 7: boom",
            ):
                adapter._inspect_profile(
                    profile,
                    source_ref,
                    source_bytes,
                    self.creature_kernel,
                    inspection_root,
                    manifest["source"]["base_namespace"],
                )
        parse.assert_not_called()

    def test_pinning_survives_original_path_replacement_and_propagates_digest(self) -> None:
        try:
            result = subprocess.run(
                ["cargo", "build", "-q", "-p", "creature-kernel-cli"],
                cwd=REPOSITORY_ROOT,
                text=True,
                capture_output=True,
                check=False,
                timeout=180,
            )
        except FileNotFoundError:
            self.skipTest("requires cargo to build the inspection CLI")
        if result.returncode != 0:
            raise AssertionError(f"could not build the inspection CLI: {result.stderr[-2000:]}")
        if not self.creature_kernel.is_file():
            raise AssertionError(f"inspection CLI is missing: {self.creature_kernel}")
        original_path = self.root / "creature-kernel"
        original_bytes = self.creature_kernel.read_bytes()
        original_path.write_bytes(original_bytes)
        original_path.chmod(0o700)
        expected_digest = hashlib.sha256(original_bytes).hexdigest()

        reference = adapter._resolve_file(original_path, "test executable")
        private_root = self.root / "private"
        private_root.mkdir()
        pinned = adapter._pin_executable(reference, private_root)
        self.assertEqual(stat.S_IMODE(pinned.stat().st_mode), 0o700)

        replacement = b"replacement after the adapter pinned the executable"
        original_path.write_bytes(replacement)
        original_path.chmod(0o700)
        self.assertNotEqual(hashlib.sha256(original_path.read_bytes()).hexdigest(), expected_digest)
        self.assertEqual(hashlib.sha256(pinned.read_bytes()).hexdigest(), expected_digest)

        stdout, _stderr, returncode = adapter._run_inspection(
            [str(pinned), "inspect-provisional-form", "--input", str(self.source_dir / f"{PROFILE_IDS[0]}.json")]
        )
        self.assertEqual(returncode, 0)
        self.assertEqual(adapter._parse_inspection(stdout)["format"], adapter.common.PROVISIONAL_FORM_V11_FORMAT)

        implementation = adapter._implementation_identity(pinned)
        self.assertEqual(implementation["files"]["producer_executable"]["sha256"], expected_digest)
        self.assertEqual(implementation["files"]["producer_executable"]["bytes"], len(original_bytes))

    def test_component_bounds_expand_the_shared_frame_for_a_tall_cranium(self) -> None:
        profile = SimpleNamespace(profile_id=PROFILE_IDS[0])
        mesh = SimpleNamespace(
            render_components=(
                SimpleNamespace(bounds=((-2.0, -8.0, -3.0), (2.0, 8.0, 3.0))),
            )
        )
        lower, upper = adapter._capture_bound_with_components(
            ((-1.0, -1.0, -1.0), (1.0, 1.0, 1.0)),
            [(profile, None, mesh)],
        )
        self.assertEqual(lower.tolist(), [-2.0, -8.0, -3.0])
        self.assertEqual(upper.tolist(), [2.0, 8.0, 3.0])

    def test_malformed_or_missing_component_bounds_fail_before_render(self) -> None:
        profiles = [
            adapter._ProfileInput(
                profile_id=profile_id,
                source_document=f"doc-{profile_id}",
                source_namespace="fixture.namespace",
                source_sha256="a" * 64,
                form=object(),
                descriptors=(),
                producer_envelope_sha256="b" * 64,
                producer_variant_sha256="c" * 64,
            )
            for profile_id in PROFILE_IDS
        ]
        prepared = tuple((profile, None, ()) for profile in profiles)
        source_manifest = {
            "format": adapter.SOURCE_MANIFEST_FORMAT,
            "source": {"candidate_sha256": "d" * 64, "source_sha256": "e" * 64},
        }
        implementation = {"identity_sha256": "f" * 64, "files": {}}
        malformed_meshes = (
            (
                SimpleNamespace(render_components=(SimpleNamespace(bounds=None),)),
                "standard_neutral_reference render component 0 bounds is not a valid three-dimensional bound:",
                False,
            ),
            (
                SimpleNamespace(
                    render_components=(
                        SimpleNamespace(bounds=((0.0, 0.0, 0.0), (float("nan"), 1.0, 1.0))),
                    )
                ),
                "standard_neutral_reference render component 0 bounds is not finite and ordered",
                True,
            ),
            (
                SimpleNamespace(render_components=(SimpleNamespace(),)),
                "standard_neutral_reference render component 0 is missing bounds",
                True,
            ),
        )
        for mesh, expected_error, exact in malformed_meshes:
            with self.subTest(mesh=mesh), patch.object(
                adapter,
                "_shared_capture_bound",
                return_value=(((0.0, 0.0, 0.0), (1.0, 1.0, 1.0)), prepared),
            ), patch.object(adapter.successor, "build_neutral_alternative_variant", return_value=mesh), patch.object(
                adapter.successor._baseline, "_render"
            ) as render:
                with self.assertRaises(adapter.SuccessorAnatomyGalleryError) as raised:
                    adapter._build_review_manifest(
                        profiles,
                        source_manifest,
                        "1" * 64,
                        implementation,
                        self.root,
                        samples=adapter.MIN_GALLERY_SAMPLES,
                        padding=adapter.successor.DEFAULT_PADDING,
                        smooth_k=adapter.successor.DEFAULT_SMOOTH_K,
                        review_id="successor-anatomy-components",
                        title=adapter.TITLE,
                    )
                if exact:
                    self.assertEqual(str(raised.exception), expected_error)
                else:
                    self.assertTrue(str(raised.exception).startswith(expected_error))
                render.assert_not_called()

    def test_manifest_order_path_profile_and_symlink_rejections(self) -> None:
        manifest = json.loads(self.source_manifest.read_text(encoding="utf-8"))

        reordered = copy.deepcopy(manifest)
        reordered["profiles"][0], reordered["profiles"][1] = reordered["profiles"][1], reordered["profiles"][0]
        self.source_manifest.write_bytes(profile_generator.canonical_bytes(reordered))
        with self.assertRaisesRegex(adapter.SuccessorAnatomyGalleryError, "exact required order"):
            adapter._validate_source_manifest(self.source_manifest)

        path_manifest = copy.deepcopy(manifest)
        path_manifest["profiles"][0]["file"] = "../escape.json"
        self.source_manifest.write_bytes(profile_generator.canonical_bytes(path_manifest))
        with self.assertRaisesRegex(adapter.SuccessorAnatomyGalleryError, "canonical profile path"):
            adapter._validate_source_manifest(self.source_manifest)

        profile_manifest = copy.deepcopy(manifest)
        profile_manifest["profiles"][0]["document"] = "wrong-profile-document"
        self.source_manifest.write_bytes(profile_generator.canonical_bytes(profile_manifest))
        with self.assertRaisesRegex(adapter.SuccessorAnatomyGalleryError, "does not bind its profile id"):
            adapter._validate_source_manifest(self.source_manifest)

        self.source_manifest.write_bytes(profile_generator.canonical_bytes(manifest))
        linked_manifest = self.root / "manifest-link.json"
        linked_manifest.symlink_to(self.source_manifest)
        with self.assertRaisesRegex(
            adapter.SuccessorAnatomyGalleryError,
            "source manifest may not use symlinks",
        ):
            adapter._validate_source_manifest(linked_manifest)

    def test_source_tamper_is_rejected_before_inspection(self) -> None:
        source = self.source_dir / f"{PROFILE_IDS[0]}.json"
        with source.open("ab") as stream:
            stream.write(b"tampered")
        with self.assertRaises(adapter.SuccessorAnatomyGalleryError) as raised:
            adapter._validate_source_manifest(self.source_manifest)
        self.assertTrue(
            str(raised.exception).startswith(
                "source manifest.profiles[0].file is not finite UTF-8 JSON:"
            )
        )

    def test_profile_mutation_is_rejected_with_self_consistent_manifest_integrity(self) -> None:
        manifest = json.loads(self.source_manifest.read_text(encoding="utf-8"))
        profile = manifest["profiles"][0]
        source_path = self.source_dir / profile["file"]
        source = json.loads(source_path.read_text(encoding="utf-8"))
        source["body"]["dimensions"][0]["value"] += 1
        source_bytes = profile_generator.canonical_source_bytes(source)
        source_path.write_bytes(source_bytes)
        profile["bytes"] = len(source_bytes)
        profile["sha256"] = hashlib.sha256(source_bytes).hexdigest()
        profile["tail_signature"] = list(profile_generator.tail_signature(source))
        self.source_manifest.write_bytes(profile_generator.canonical_bytes(manifest))

        with self.assertRaisesRegex(
            adapter.SuccessorAnatomyGalleryError,
            "canonical checked-in candidate/base generator output",
        ):
            adapter._validate_source_manifest(self.source_manifest)

    def test_candidate_internal_base_source_hash_must_match_checked_in_base(self) -> None:
        candidate = json.loads(profile_generator.DEFAULT_CANDIDATE.read_text(encoding="utf-8"))
        candidate["base_source"]["sha256"] = "0" * 64
        candidate_path = self.root / "candidate-with-wrong-base-hash.json"
        candidate_bytes = profile_generator.canonical_bytes(candidate)
        candidate_path.write_bytes(candidate_bytes)
        manifest = json.loads(self.source_manifest.read_text(encoding="utf-8"))
        manifest["source"]["candidate_sha256"] = hashlib.sha256(candidate_bytes).hexdigest()
        self.source_manifest.write_bytes(profile_generator.canonical_bytes(manifest))

        with patch.object(adapter.profile_source_generator, "DEFAULT_CANDIDATE", candidate_path):
            with self.assertRaisesRegex(
                adapter.SuccessorAnatomyGalleryError,
                "candidate base-source hash does not match",
            ):
                adapter._validate_source_manifest(self.source_manifest)

    def test_image_identity_rejects_jpeg_bytes_named_png(self) -> None:
        image_path = self.root / "jpeg-disguised-as-png.png"
        adapter.successor._baseline.Image.new(
            "RGB",
            (adapter.EXPECTED_CANVAS["width"], adapter.EXPECTED_CANVAS["height"]),
            (80, 90, 100),
        ).save(image_path, format="JPEG")
        profile = adapter._ProfileInput(
            profile_id=PROFILE_IDS[0],
            source_document="source-document",
            source_namespace="source-namespace",
            source_sha256="a" * 64,
            form=object(),
            descriptors=(),
            producer_envelope_sha256="b" * 64,
            producer_variant_sha256="c" * 64,
        )

        with self.assertRaisesRegex(adapter.SuccessorAnatomyGalleryError, "actual PNG image"):
            adapter._image_identity(
                image_path,
                profile,
                {},
                {"identity_sha256": "d" * 64},
            )


if __name__ == "__main__":
    unittest.main()
