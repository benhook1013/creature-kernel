from __future__ import annotations

import hashlib
import importlib.util
import io
import json
import os
import subprocess
import threading
from concurrent.futures import ThreadPoolExecutor
from contextlib import redirect_stderr
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch


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


import common  # noqa: E402
import publish as shared_publish  # noqa: E402

publisher = _load_module(
    "visual_review_publish_regional_surface_preview_tests",
    HERE / "publish_regional_surface_preview.py",
)


def _prepared(document: str = publisher.EXPECTED_SOURCE_DOCUMENT) -> dict[str, object]:
    return {
        "format": common.PROVISIONAL_FORM_FORMAT,
        "source": {
            "document": document,
            "namespace": "main",
            "resource_profile_id": common.PROVISIONAL_FORM_RESOURCE_PROFILE,
        },
        "reference_scale": {"squared_length": 1},
        "variants": [],
    }


def _renderer_source(marker: str) -> bytes:
    return (
        "class RegionalSurfacePreviewError(ValueError):\n"
        "    pass\n"
        "PreviewError = RegionalSurfacePreviewError\n"
        f"def render_regional_surface_preview(*args, **kwargs):\n"
        f"    return {marker!r}\n"
    ).encode("utf-8")


class RegionalSurfacePublicationTests(unittest.TestCase):
    def test_publisher_identity_uses_retained_executed_source_after_live_path_replacement(self) -> None:
        source_bytes = (HERE / "publish_regional_surface_preview.py").read_bytes()
        with tempfile.TemporaryDirectory() as directory:
            live_path = Path(directory) / "publish_regional_surface_preview.py"
            live_path.write_bytes(source_bytes)
            snapshot_module = _load_module(
                "visual_review_regional_preview_live_replacement_test",
                live_path,
            )
            live_path.write_bytes(b"raise RuntimeError('replacement must not be hashed')\n")
            identity = snapshot_module._publisher_implementation_identity()

        self.assertEqual(identity["id"], publisher.PUBLISHER_IMPLEMENTATION_ID)
        self.assertEqual(identity["bytes"], len(source_bytes))
        self.assertEqual(identity["sha256"], hashlib.sha256(source_bytes).hexdigest())

    def test_prepared_form_duplicate_members_are_rejected_before_validation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "prepared.json"
            document = publisher.EXPECTED_SOURCE_DOCUMENT
            raw = (
                '{"format":"'
                + common.PROVISIONAL_FORM_FORMAT
                + '","source":{"document":"'
                + document
                + '","namespace":"main","resource_profile_id":"'
                + common.PROVISIONAL_FORM_RESOURCE_PROFILE
                + '","resource_profile_id":"'
                + common.PROVISIONAL_FORM_RESOURCE_PROFILE
                + '"}}'
            ).encode("utf-8")
            path.write_bytes(raw)
            with self.assertRaisesRegex(
                publisher.RegionalSurfacePublicationError,
                "duplicate JSON object member",
            ):
                publisher._read_prepared_input(
                    path,
                    expected_source_document=publisher.EXPECTED_SOURCE_DOCUMENT,
                )

    def test_renderer_replacement_after_snapshot_executes_snapshot_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "regional_surface_preview.py"
            source_a = _renderer_source("snapshot-a")
            source_b = _renderer_source("replacement-b")
            path.write_bytes(source_a)
            snapshot = publisher._snapshot_renderer_source(path)
            path.write_bytes(source_b)

            renderer, error_type = publisher._load_renderer(snapshot)

            self.assertEqual(renderer(), "snapshot-a")
            self.assertEqual(error_type.__name__, "RegionalSurfacePreviewError")
            self.assertEqual(
                snapshot.identity,
                {
                    "id": publisher.RENDERER_SOURCE_ID,
                    "bytes": len(source_a),
                    "sha256": hashlib.sha256(source_a).hexdigest(),
                },
            )

    def test_renderer_snapshot_rejects_a_mismatched_recorded_digest(self) -> None:
        source_bytes = _renderer_source("snapshot-integrity")
        snapshot = publisher.RendererSourceSnapshot(
            Path("/immutable/regional_surface_preview.py"),
            source_bytes,
            "f" * 64,
        )
        with self.assertRaisesRegex(
            publisher.RegionalSurfacePublicationError,
            "snapshot hash does not match its bytes",
        ):
            publisher._load_renderer(snapshot)

    def test_direct_item_carries_exact_renderer_identity_into_publication(self) -> None:
        prepared = _prepared()
        source_bytes = _renderer_source("identity")
        snapshot = publisher.RendererSourceSnapshot(
            Path("/immutable/regional_surface_preview.py"),
            source_bytes,
            hashlib.sha256(source_bytes).hexdigest(),
        )
        canonical_hash = publisher._sha256_value(
            prepared,
            "test prepared form",
            maximum=publisher.MAX_PREPARED_INPUT_BYTES,
        )
        renderer = Mock(return_value=object())
        renderer_validation_error = type("RendererValidationError", (Exception,), {})
        captured: dict[str, object] = {}

        def validate_metadata(*args: object, **kwargs: object):
            captured.update(kwargs)
            identity = kwargs["renderer_source_identity"]
            return (
                {
                    "renderer_metadata_sha256": "a" * 64,
                    "identity": {"renderer_source": identity},
                },
                {"sha256": canonical_hash},
            )

        with patch.object(
            publisher.common,
            "_validate_provisional_form_envelope",
            side_effect=lambda value, where: value,
        ), patch.object(
            publisher,
            "_load_renderer",
            return_value=(renderer, renderer_validation_error),
        ) as load_renderer, patch.object(
            publisher,
            "_result_parts",
            return_value=(b"opaque-test-payload", {}),
        ), patch.object(
            publisher,
            "_validate_png",
            return_value=(1800, 1500, "RGB"),
        ), patch.object(
            publisher,
            "_validate_renderer_metadata",
            side_effect=validate_metadata,
        ), patch.object(
            publisher,
            "_retained_renderer_metadata",
            return_value={},
        ):
            item = publisher.render_and_validate_regional_surface_item(
                prepared,
                prepared_input_sha256=canonical_hash,
                raw_prepared_form_sha256="b" * 64,
                external_profile_id=publisher.EXTERNAL_ID,
                expected_source_document=publisher.EXPECTED_SOURCE_DOCUMENT,
                mesh_samples=publisher.MIN_MESH_SAMPLES,
                mesh_padding=0.20,
                renderer_source_snapshot=snapshot,
            )

        renderer.assert_called_once_with(
            prepared,
            external_profile_id=publisher.EXTERNAL_ID,
            mesh_samples=publisher.MIN_MESH_SAMPLES,
            mesh_padding=0.20,
        )
        load_renderer.assert_called_once_with(snapshot)
        self.assertEqual(captured["renderer_source_identity"], snapshot.identity)
        self.assertEqual(item["renderer_source"], snapshot.identity)
        self.assertEqual(
            item["publication_identity"]["renderer_source"],
            snapshot.identity,
        )
        self.assertEqual(
            item["item_metadata"]["renderer_source"],
            snapshot.identity,
        )

    def test_prepared_input_mutation_during_renderer_call_fails_before_retention(self) -> None:
        prepared = _prepared()
        canonical_hash = publisher._sha256_value(
            prepared,
            "test prepared form",
            maximum=publisher.MAX_PREPARED_INPUT_BYTES,
        )
        source_bytes = _renderer_source("mutation")
        snapshot = publisher.RendererSourceSnapshot(
            Path("/immutable/regional_surface_preview.py"),
            source_bytes,
            hashlib.sha256(source_bytes).hexdigest(),
        )

        def mutate(value: dict[str, object], **kwargs: object) -> object:
            value["reference_scale"] = {"squared_length": 2}
            return object()

        with patch.object(
            publisher.common,
            "_validate_provisional_form_envelope",
            side_effect=lambda value, where: value,
        ), patch.object(
            publisher,
            "_load_renderer",
            return_value=(mutate, ValueError),
        ), patch.object(
            publisher,
            "_result_parts",
        ) as result_parts:
            with self.assertRaisesRegex(
                publisher.RegionalSurfacePublicationError,
                "prepared input changed during rendering",
            ):
                publisher.render_and_validate_regional_surface_item(
                    prepared,
                    prepared_input_sha256=canonical_hash,
                    raw_prepared_form_sha256="b" * 64,
                    external_profile_id=publisher.EXTERNAL_ID,
                    expected_source_document=publisher.EXPECTED_SOURCE_DOCUMENT,
                    mesh_samples=publisher.MIN_MESH_SAMPLES,
                    mesh_padding=0.20,
                    renderer_source_snapshot=snapshot,
                )
        result_parts.assert_not_called()

    def test_publish_session_no_overwrite_race_installs_exactly_one_session(self) -> None:
        synthetic_asset = b"synthetic-not-rendered-image-bytes"
        asset_sha256 = hashlib.sha256(synthetic_asset).hexdigest()
        barrier = threading.Barrier(2)
        original_rename = shared_publish._rename_noreplace

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "reviews"
            root.mkdir()
            manifests: list[Path] = []
            for index in range(2):
                staging = Path(directory) / f"source-{index}"
                staging.mkdir()
                asset = staging / "race-item.png"
                asset.write_bytes(synthetic_asset)
                manifest = staging / "manifest.json"
                manifest.write_text(
                    json.dumps(
                        {
                            "schema_version": 1,
                            "id": "publication-race",
                            "title": "Publication race",
                            "description": "Synthetic no-overwrite race fixture.",
                            "instructions": "No visual appraisal.",
                            "subject_context": {"descriptor_snapshot": {"synthetic": True}},
                            "kind": "image",
                            "groups": [
                                {
                                    "id": "race-group",
                                    "title": "Race",
                                    "selection_mode": "none",
                                    "items": [
                                        {
                                            "id": "race-item",
                                            "title": "Synthetic race item",
                                            "source": str(asset),
                                        }
                                    ],
                                }
                            ],
                        }
                    ),
                    encoding="utf-8",
                )
                manifests.append(manifest)

            def synchronized_rename(*args: object, **kwargs: object) -> object:
                barrier.wait(timeout=5)
                return original_rename(*args, **kwargs)

            def publish(manifest: Path) -> object:
                try:
                    return shared_publish.publish_session(
                        root,
                        manifest,
                        expected_sources={
                            "race-item": {
                                "bytes": len(synthetic_asset),
                                "sha256": asset_sha256,
                            }
                        },
                    )
                except Exception as exc:  # returned for exact two-way race assertions
                    return exc

            with patch.object(
                shared_publish,
                "_rename_noreplace",
                side_effect=synchronized_rename,
            ), ThreadPoolExecutor(max_workers=2) as executor:
                outcomes = list(executor.map(publish, manifests))

            successes = [outcome for outcome in outcomes if isinstance(outcome, dict)]
            failures = [outcome for outcome in outcomes if isinstance(outcome, Exception)]
            self.assertEqual(len(successes), 1)
            self.assertEqual(len(failures), 1)
            self.assertIsInstance(failures[0], shared_publish.PublishError)
            self.assertIn("session appeared during publish", str(failures[0]))
            self.assertTrue((root / "publication-race" / "review.json").is_file())
            entries = list(root.iterdir())
            self.assertEqual(
                [path.name for path in entries if not path.name.startswith(".")],
                ["publication-race"],
            )
            retained_staging = [path for path in entries if path.name.startswith(".")]
            self.assertEqual(len(retained_staging), 1)
            self.assertEqual(list(retained_staging[0].iterdir()), [])

    def test_unexpected_direct_failure_has_generic_publication_classification(self) -> None:
        prepared = _prepared()
        with tempfile.TemporaryDirectory() as directory:
            input_path = Path(directory) / "prepared.json"
            input_path.write_text(json.dumps(prepared), encoding="utf-8")
            source_bytes = _renderer_source("unused")
            snapshot = publisher.RendererSourceSnapshot(
                Path("/immutable/regional_surface_preview.py"),
                source_bytes,
                hashlib.sha256(source_bytes).hexdigest(),
            )
            renderer = Mock(side_effect=RuntimeError("secret renderer internals"))
            stderr = io.StringIO()
            with patch.object(
                publisher.common,
                "_validate_provisional_form_envelope",
                side_effect=lambda value, where: value,
            ), patch.object(
                publisher,
                "_snapshot_renderer_source",
                return_value=snapshot,
            ), patch.object(
                publisher,
                "_load_renderer",
                return_value=(renderer, ValueError),
            ), redirect_stderr(stderr):
                status = publisher.main(
                    [
                        "--root",
                        str(input_path.parent),
                        "--prepared-form",
                        str(input_path),
                        "--id",
                        "direct-publication-error",
                        "--mesh-samples",
                        str(publisher.MIN_MESH_SAMPLES),
                        "--mesh-padding",
                        "0.20",
                    ]
                )

        output = stderr.getvalue()
        self.assertEqual(status, 2)
        self.assertIn("unexpected publication failure", output)
        self.assertNotIn("unexpected renderer failure", output)
        self.assertNotIn("secret renderer internals", output)
        self.assertNotIn("Traceback", output)

    def test_v3_candidate_uses_current_route_and_truthful_operand_split(self) -> None:
        for side in ("left", "right"):
            with self.subTest(side=side):
                route_name = f"{side}-arm"
                sections = publisher._expected_arm_route_sections(route_name)
                self.assertEqual(
                    [item["name"] for item in sections],
                    [
                        "torso-arm-interface",
                        "upper-arm-start",
                        "upper-arm-midpoint",
                        "elbow",
                        "forearm-midpoint",
                        "forearm-distal",
                    ],
                )
                self.assertEqual(
                    [item["index"] for item in sections],
                    [0, 1, 2, 3, 4, 5],
                )
                self.assertEqual(
                    [item["source_index"] for item in sections],
                    [None, 0, 1, 2, 3, 4],
                )
                self.assertTrue(sections[0]["derived"])
                self.assertIn("torso=", sections[0]["source_key"])
                self.assertIn("upper-arm=", sections[0]["source_key"])
                self.assertEqual(sections[3]["name"], "elbow")
                self.assertEqual(sections[3]["source_index"], 2)
                self.assertEqual(
                    sections[publisher.EXPECTED_ARM_SHOULDER_CLOSURE_ROUTE_INDEX]["name"],
                    "upper-arm-start",
                )

        self.assertEqual(publisher.CANDIDATE_FORMAT.rsplit(".", 1)[-1], "v3")
        self.assertEqual(len(publisher.EXPECTED_TORSO_STATION_NAMES), 7)
        self.assertEqual(len(publisher.EXPECTED_ROUTE_NAMES), 7)
        self.assertEqual(len(publisher.EXPECTED_CONTROL_NAMES), 4)
        self.assertEqual(len(publisher.EXPECTED_SKIN_SOURCE_IDENTITIES), 8)
        self.assertEqual(len(publisher.EXPECTED_PATCH_IDENTITIES), 7)
        self.assertEqual(len(publisher.EXPECTED_AUTHORITY_CONTROL_IDENTITIES), 4)
        self.assertEqual(len(publisher.EXPECTED_OPERANDS), 15)
        self.assertEqual(
            len(publisher.EXPECTED_SKIN_SOURCE_IDENTITIES)
            + len(publisher.EXPECTED_PATCH_IDENTITIES),
            15,
        )
        self.assertEqual(publisher.EXPECTED_WITNESS_COUNT, 21)
        self.assertEqual(len(publisher.EXPECTED_INTERFACE_RELATIONS), 7)

    def test_final_control_schema_is_exact_and_rejects_legacy_final_skin_influence(self) -> None:
        name = "left-shoulder-peak"
        compact = publisher._expected_control_binding(name)
        self.assertEqual(
            set(compact),
            {
                "name", "namespace", "side", "owner", "role", "frame", "frame_role",
                "semantic_key", "source_key", "canonical_source_key", "authority_only",
                "skin_consumer", "counterfactual_authority_bound_influence",
                "control_local_final_skin_influence", "control_local_final_skin_influence_status",
                "visual_floor_satisfaction", "interface_id",
            },
        )
        self.assertEqual(compact["counterfactual_authority_bound_influence"], "proven")
        self.assertIs(compact["control_local_final_skin_influence"], False)
        self.assertEqual(compact["control_local_final_skin_influence_status"], "unverified")
        self.assertEqual(compact["visual_floor_satisfaction"], "unverified")
        self.assertEqual(compact["source_key"], compact["canonical_source_key"])
        self.assertEqual(
            publisher._validate_candidate_control_record(compact, name, "test compact control"),
            compact,
        )

        legacy_compact = {**compact, "final_skin_influence": True}
        with self.assertRaisesRegex(
            publisher.RegionalSurfacePublicationError,
            "unexpected final_skin_influence",
        ):
            publisher._validate_candidate_control_record(
                legacy_compact,
                name,
                "test legacy compact control",
            )

        identity = publisher.EXPECTED_AUTHORITY_CONTROL_IDENTITIES[0]
        diagnostic = {
            "identifier": identity[0],
            "kind": identity[1],
            "semantic_identity": identity[2],
            **{
                key: compact[key]
                for key in (
                    "source_key", "canonical_source_key", "namespace", "side", "owner", "role",
                    "frame", "interface_id", "authority_only", "skin_consumer",
                    "counterfactual_authority_bound_influence", "control_local_final_skin_influence",
                    "control_local_final_skin_influence_status", "visual_floor_satisfaction",
                )
            },
        }
        self.assertEqual(
            publisher._validate_authority_control_record(
                diagnostic,
                identity,
                "test diagnostic control",
            ),
            diagnostic,
        )
        with self.assertRaisesRegex(
            publisher.RegionalSurfacePublicationError,
            "unexpected final_skin_influence",
        ):
            publisher._validate_authority_control_record(
                {**diagnostic, "final_skin_influence": True},
                identity,
                "test legacy diagnostic control",
            )

    def test_v3_leg_route_reconstructs_three_derived_hip_sections_and_five_authored_sections(self) -> None:
        for side in ("left", "right"):
            with self.subTest(side=side):
                route_name = f"{side}-leg"
                sections = publisher._expected_leg_route_sections(route_name)
                self.assertEqual(
                    [item["name"] for item in sections],
                    [
                        "pelvis-seat",
                        "hip-cup-rim",
                        "femoral-neck",
                        "thigh-start",
                        "thigh-midpoint",
                        "knee",
                        "shin-midpoint",
                        "hock-endpoint",
                    ],
                )
                self.assertEqual([item["index"] for item in sections], list(range(8)))
                self.assertEqual(
                    [item["source_index"] for item in sections],
                    [None, None, None, 0, 1, 2, 3, 4],
                )
                self.assertEqual(
                    [item["derived"] for item in sections],
                    [True, True, True, False, False, False, False, False],
                )
                pelvis = publisher._source_address([], "pelvis")
                thigh = publisher._source_address([side], "thigh")
                shin = publisher._source_address([side], "shin")
                self.assertEqual(
                    sections[0]["source_key"],
                    f"derived-pelvis-seat:pelvis={pelvis}:thigh={thigh}",
                )
                self.assertEqual(
                    sections[1]["source_key"],
                    f"derived-hip-cup-rim:pelvis={pelvis}:thigh={thigh}",
                )
                self.assertEqual(
                    sections[2]["source_key"],
                    f"derived-femoral-neck:pelvis={pelvis}:thigh={thigh}",
                )
                for route_index in (3, 4, publisher.EXPECTED_LEG_KNEE_ROUTE_INDEX):
                    self.assertTrue(sections[route_index]["source_key"].endswith(thigh))
                for route_index in (6, publisher.EXPECTED_LEG_HOCK_ROUTE_INDEX):
                    self.assertTrue(sections[route_index]["source_key"].endswith(shin))
                self.assertEqual(sections[publisher.EXPECTED_LEG_KNEE_ROUTE_INDEX]["name"], "knee")
                self.assertEqual(sections[publisher.EXPECTED_LEG_KNEE_ROUTE_INDEX]["source_index"], 2)
                self.assertEqual(sections[publisher.EXPECTED_LEG_HOCK_ROUTE_INDEX]["name"], "hock-endpoint")
                self.assertEqual(sections[publisher.EXPECTED_LEG_HOCK_ROUTE_INDEX]["source_index"], 4)
                closures = publisher._expected_leg_endpoint_closures(route_name, sections)
                self.assertEqual(
                    closures[0],
                    {
                        "name": f"{route_name}:hip-cup-rim-closure",
                        "source_key": sections[publisher.EXPECTED_LEG_HIP_CUP_RIM_ROUTE_INDEX]["source_key"],
                    },
                )
                self.assertNotEqual(closures[0]["source_key"], sections[0]["source_key"])
                self.assertEqual(closures[1]["source_key"], sections[7]["source_key"])

        self.assertEqual(publisher.EXPECTED_LEG_AUTHORED_SECTION_COUNT, 5)
        self.assertEqual(publisher.EXPECTED_LEG_TOTAL_SECTION_COUNT, 8)
        self.assertEqual(publisher.EXPECTED_LEG_CONNECTION_COUNT, 7)
        self.assertIn("bilateral_leg_authored_sections", publisher.EXPECTED_ROUTE_METADATA_FIELDS)
        self.assertIn("bilateral_leg_total_sections", publisher.EXPECTED_ROUTE_METADATA_FIELDS)
        self.assertNotIn("bilateral_leg_sections", publisher.EXPECTED_ROUTE_METADATA_FIELDS)
        self.assertEqual(
            publisher._expected_shared_interface_metadata(),
            {
                "cranium_mid": {"head_section_index": 3, "connection_indices": [2, 3, 4]},
                "elbows": [3, 3],
                "knees": [5, 5],
                "hocks": [7, 7],
                "hip_cup_sections": ["pelvis-seat", "hip-cup-rim", "femoral-neck"],
                "feet_use_leg_hock_identity": True,
            },
        )

    def test_v3_foot_route_requires_explicit_borrowed_leg_authored_hock_identity(self) -> None:
        for side in ("left", "right"):
            with self.subTest(side=side):
                leg_name = f"{side}-leg"
                foot_name = f"{side}-foot"
                leg_sections = publisher._expected_leg_route_sections(leg_name)
                foot_sections = publisher._expected_foot_route_sections(
                    foot_name,
                    leg_sections[publisher.EXPECTED_LEG_HOCK_ROUTE_INDEX],
                )
                borrowed = foot_sections[0]
                owner = publisher._source_identity([side], "shin")
                self.assertEqual([item["name"] for item in foot_sections], ["hock-endpoint", "pad", "toe"])
                self.assertEqual(
                    set(borrowed),
                    {
                        "index",
                        "route_index",
                        "name",
                        "binding_kind",
                        "authored_in_foot_route",
                        "shared_with",
                        "source_route",
                        "owner",
                        "source_index",
                        "source_key",
                        "semantic_key",
                        "derived",
                        "leg_authored_identity",
                    },
                )
                self.assertEqual(borrowed["index"], 0)
                self.assertEqual(borrowed["route_index"], 0)
                self.assertEqual(borrowed["binding_kind"], "borrowed-shared-leg-station")
                self.assertIs(borrowed["authored_in_foot_route"], False)
                self.assertEqual(borrowed["shared_with"], leg_name)
                self.assertEqual(borrowed["source_route"], leg_name)
                self.assertEqual(borrowed["source_index"], 4)
                self.assertEqual(borrowed["owner"], owner)
                self.assertEqual(
                    borrowed["leg_authored_identity"],
                    {
                        "route": leg_name,
                        "name": "hock-endpoint",
                        "source_index": 4,
                        "owner": owner,
                        "source_key": leg_sections[7]["source_key"],
                        "semantic_key": leg_sections[7]["semantic_key"],
                    },
                )
                self.assertEqual(borrowed["source_key"], leg_sections[7]["source_key"])
                self.assertEqual(borrowed["semantic_key"], leg_sections[7]["semantic_key"])
                self.assertEqual(
                    [item["source_index"] for item in foot_sections],
                    [4, 0, 1],
                )

    def test_current_renderer_metadata_passes_publication_validator_for_standard_and_compact_profiles(self) -> None:
        """Exercise the validator against two profiles from the canonical live path."""

        repo_root = HERE.parents[1]
        launcher = repo_root / "experiments/current-form-surface-preview/surface_preview_launcher.sh"
        generator = repo_root / "experiments/current-form-surface-preview/generate_structural_profile_sources.py"
        cli = repo_root / "target/debug/creature-kernel"
        profile_documents = (
            (
                publisher.EXTERNAL_ID,
                publisher.EXPECTED_SOURCE_DOCUMENT,
            ),
            (
                "compact_broad_short_limb_large_head",
                "stylized_digitigrade_biped_authored_form__structural_profile__"
                "compact_broad_short_limb_large_head",
            ),
        )
        self.assertTrue(launcher.is_file())
        self.assertTrue(generator.is_file())
        self.assertTrue(cli.is_file() and os.access(cli, os.X_OK))
        with tempfile.TemporaryDirectory(prefix="ck-regional-publication-e2e-", dir="/tmp") as directory:
            root = Path(directory)
            source_dir = root / "sources"
            environment = os.environ.copy()
            environment.update({"TMPDIR": "/tmp", "TEMP": "/tmp", "TMP": "/tmp"})
            subprocess.run(
                [str(launcher), str(generator), "--output-dir", str(source_dir)],
                cwd=repo_root,
                env=environment,
                check=True,
                capture_output=True,
                timeout=60,
            )
            validation_script = """
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd() / "dev-tools/visual-review"))
import publish_regional_surface_preview as publisher

prepared_path = Path(sys.argv[1])
external_profile_id = sys.argv[2]
expected_source_document = sys.argv[3]
raw = prepared_path.read_bytes()
prepared = json.loads(raw)
validated = publisher.common._validate_provisional_form_envelope(prepared, "e2e prepared form")
canonical_sha256 = publisher._sha256_value(
    validated,
    "e2e prepared validated-envelope identity",
    maximum=publisher.MAX_PREPARED_INPUT_BYTES,
)
item = publisher.render_and_validate_regional_surface_item(
    validated,
    prepared_input_sha256=canonical_sha256,
    raw_prepared_form_sha256=hashlib.sha256(raw).hexdigest(),
    external_profile_id=external_profile_id,
    expected_source_document=expected_source_document,
    mesh_samples=56,
    mesh_padding=0.20,
)
print(json.dumps({
    "profile_id": external_profile_id,
    "candidate": item["publication"]["identity"]["candidate"],
    "candidate_contract": item["publication"]["candidate_contract"],
    "diagnostic_inventory": item["retained_renderer_metadata"]["diagnostic_inventory"],
    "diagnostics": item["retained_renderer_metadata"]["diagnostics"],
}, sort_keys=True))
"""
            payloads: dict[str, dict[str, object]] = {}
            for profile_id, source_document in profile_documents:
                inspection = subprocess.run(
                    [
                        str(cli),
                        "inspect-provisional-form",
                        "--input",
                        str(source_dir / f"{profile_id}.json"),
                    ],
                    cwd=repo_root,
                    env=environment,
                    check=True,
                    capture_output=True,
                    timeout=30,
                )
                prepared_path = root / f"{profile_id}.prepared.json"
                prepared_path.write_bytes(inspection.stdout)
                result = subprocess.run(
                    [
                        str(launcher),
                        "-c",
                        validation_script,
                        str(prepared_path),
                        profile_id,
                        source_document,
                    ],
                    cwd=repo_root,
                    env=environment,
                    check=True,
                    capture_output=True,
                    text=True,
                    timeout=120,
                )
                payloads[profile_id] = json.loads(result.stdout)

        self.assertEqual(set(payloads), {profile_id for profile_id, _ in profile_documents})
        for profile_id, _ in profile_documents:
            with self.subTest(profile_id=profile_id):
                payload = payloads[profile_id]
                self.assertEqual(payload["profile_id"], profile_id)
                candidate = payload["candidate"]
                self.assertEqual(candidate["format"], publisher.CANDIDATE_FORMAT)
                self.assertEqual(candidate["skin_source_count"], 8)
                self.assertEqual(candidate["derived_patch_count"], 7)
                self.assertEqual(candidate["authority_control_count"], 4)
                self.assertEqual(len(payload["candidate_contract"]["routes"]["section_counts"]), 7)
                self.assertEqual(payload["candidate_contract"]["routes"]["section_counts"], [8, 6, 6, 8, 8, 3, 3])
                self.assertEqual(payload["candidate_contract"]["routes"]["connection_counts"], [7, 5, 5, 7, 7, 2, 2])
                self.assertEqual(payload["diagnostics"]["skin_source_count"], 8)
                self.assertEqual(payload["diagnostics"]["derived_patch_count"], 7)
                self.assertEqual(payload["diagnostics"]["authority_control_count"], 4)
                self.assertEqual(payload["diagnostics"]["final_field_graph"]["final_term_count"], 15)
                self.assertEqual(len(payload["diagnostic_inventory"]["skin_sources"]), 8)
                self.assertEqual(len(payload["diagnostic_inventory"]["derived_patches"]), 7)
                self.assertEqual(len(payload["diagnostic_inventory"]["authority_controls"]), 4)
                authority_contract = payload["candidate_contract"]["authority_controls"]
                self.assertEqual(authority_contract["counterfactual_authority_bound_influence"], "proven")
                self.assertIs(authority_contract["control_local_final_skin_influence"], False)
                self.assertEqual(authority_contract["control_local_final_skin_influence_status"], "unverified")
                self.assertEqual(authority_contract["shoulder_visual_floor_satisfaction"], "unverified")
                self.assertEqual(authority_contract["axilla_visual_floor_satisfaction"], "unverified")
                self.assertNotIn("final_skin_influence", payload["diagnostic_inventory"]["authority_controls"][0])
                self.assertNotIn("final_skin_influence", authority_contract)


if __name__ == "__main__":
    unittest.main()
