from __future__ import annotations

from contextlib import redirect_stdout
from copy import deepcopy
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch


HERE = Path(__file__).resolve()
EXPERIMENT = HERE.parent
PROFILE_IDS = ("compact_broad_short_limb_large_head", "tall_narrow_long_legged")
ALTERNATE_IDS = ("slender_long_limb", "stocky_broad_chested")
INSTANCE_IDS = ("avatar-left", "avatar-right")
POSE_BYTES = b'{"pose_id":"shared-test-pose","rules":[]}\n'
REAL_GALLERY = Path(os.environ.get("CK_GODOT_STRUCTURAL_GALLERY", "/tmp/ck-godot-structural-inputs/gallery"))
REAL_CLI = HERE.parents[2] / "target" / "debug" / "creature-kernel"
sys.dont_write_bytecode = True


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


smoke = load_module("run_structural_gallery_smoke_for_projection_tests", EXPERIMENT / "run_structural_gallery_smoke.py")
sys.modules["run_structural_gallery_smoke"] = smoke
carrier = load_module("disposable_avatar_carrier_for_projection_tests", EXPERIMENT / "disposable_avatar_carrier.py")
sys.modules["disposable_avatar_carrier"] = carrier
projection = load_module("disposable_ck_projection_under_test", EXPERIMENT / "disposable_ck_projection.py")


def artifact_bytes(profile_id: str, name: str) -> bytes:
    return f"{profile_id}/{name}".encode("ascii")


def artifact_records(profile_id: str) -> list[dict[str, object]]:
    records = []
    for name in smoke.EXPECTED_ARTIFACT_NAMES:
        path = f"{profile_id}/{name}"
        data = artifact_bytes(profile_id, name)
        records.append({"path": path, "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)})
    return records


def metrics(profile_id: str) -> dict[str, object]:
    return {
        "format": "creature-kernel.disposable-structural-embodiment-metrics.v1",
        "profile_id": profile_id,
        "vertex_count": 3,
    }


def payload(pose_sha256: str) -> dict[str, object]:
    profiles = []
    for profile_id in PROFILE_IDS:
        profiles.append(
            {
                "profile_id": profile_id,
                "label": f"Fixture {profile_id}",
                "candidate_profile_sha256": hashlib.sha256(profile_id.encode("ascii")).hexdigest(),
                "artifacts": artifact_records(profile_id),
                "metrics": metrics(profile_id),
            }
        )
    return {
        "projection_contract": "creature-kernel.disposable-structural-embodiment-gallery.v1",
        "manifest_sha256": "a" * 64,
        "manifest_bytes": 321,
        "godot_version": carrier.EXPECTED_GODOT_VERSION,
        "profile_ids": list(PROFILE_IDS),
        "pose_id": "shared-test-pose",
        "pose_sha256": pose_sha256,
        "boundary": "host_only_smoke",
        "profiles": profiles,
    }


def rust_inspection(profile_id: str) -> dict[str, object]:
    graph = {
        "projection": "source-preserving-provisional-structural-debug",
        "contract": {"family": "creature-kernel.body", "revision": 1},
        "source": {"dependencies": [], "document": f"fixture.{profile_id}", "namespace": "fixture"},
        "basis": {"length_unit": "metre", "handedness": "right", "up": "+y", "forward": "+z"},
        "profiles": {"semantic_numeric": "ck.numeric-frame.r1"},
        "extensions": [],
        "modules": [],
        "parts": [],
        "joints": [],
        "sockets": [],
        "attachments": [],
        "landmarks": [],
        "dimensions": [],
        "frames": [],
        "regions": [],
        "capabilities": [],
        "fields": [],
    }
    return {
        "format": projection.RUST_FORMAT,
        "operation": projection.RUST_OPERATION,
        "stage": "structural-validation",
        "status": "success",
        "processing_complete": True,
        "diagnostics_complete": True,
        "diagnostics": [],
        "summary": {name: 0 for name in projection.SUMMARY_KEYS},
        "graph": graph,
    }


class DisposableCKProjectionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="ck-disposable-projection-test-")
        self.root = Path(self.temp.name)
        self.gallery = self.root / "gallery"
        (self.gallery / projection.SOURCE_DIR).mkdir(parents=True)
        (self.gallery / projection.POSE_FILE).write_bytes(POSE_BYTES)
        for profile_id in PROFILE_IDS:
            source = {"source": {"dependencies": [], "document": f"fixture.{profile_id}", "namespace": "fixture"}}
            (self.gallery / projection.SOURCE_DIR / f"{profile_id}.json").write_text(
                json.dumps(source) + "\n",
                encoding="utf-8",
            )
            profile_directory = self.gallery / profile_id
            profile_directory.mkdir()
            for name in smoke.EXPECTED_ARTIFACT_NAMES:
                (profile_directory / name).write_bytes(artifact_bytes(profile_id, name))
        self.pose_sha256 = hashlib.sha256(POSE_BYTES).hexdigest()
        self.payload = payload(self.pose_sha256)
        self.carrier_value = {
            "schema": carrier.SCHEMA,
            "boundary": carrier.BOUNDARY,
            "source_gallery": {
                "projection_contract": self.payload["projection_contract"],
                "manifest_sha256": self.payload["manifest_sha256"],
                "manifest_bytes": self.payload["manifest_bytes"],
                "boundary": self.payload["boundary"],
            },
            "shared_pose": {
                "path": projection.POSE_FILE,
                "pose_id": "shared-test-pose",
                "sha256": self.pose_sha256,
                "bytes": len(POSE_BYTES),
            },
            "instances": [
                {
                    "instance_id": instance_id,
                    "profile_id": profile_id,
                    "label": f"Fixture {profile_id}",
                    "candidate_profile_sha256": hashlib.sha256(profile_id.encode("ascii")).hexdigest(),
                    "artifacts": artifact_records(profile_id),
                    "metrics": metrics(profile_id),
                }
                for instance_id, profile_id in zip(INSTANCE_IDS, PROFILE_IDS)
            ],
        }
        self.carrier_path = self.root / "carrier.json"
        carrier.write_carrier(self.carrier_path, self.carrier_value)
        self.cli_path = self._write_executable("creature-kernel", "raise SystemExit(0)\n")

    def tearDown(self) -> None:
        self.temp.cleanup()

    def _write_executable(self, name: str, body: str) -> Path:
        path = self.root / name
        path.write_text(f"#!{sys.executable}\n{body}", encoding="utf-8")
        path.chmod(0o700)
        return path

    def static_validator(self, value, gallery):
        return deepcopy(self.payload), PROFILE_IDS, INSTANCE_IDS

    def valid_runner(self, command):
        profile_id = Path(command[-1]).stem
        return 0, (json.dumps(rust_inspection(profile_id)) + "\n").encode("utf-8"), b""

    def build(self, *, runner=None, validator=None) -> dict[str, object]:
        with (
            patch.object(projection, "_load_carrier_module", return_value=carrier),
            patch.object(carrier, "validate_carrier", side_effect=validator or self.static_validator),
            patch.object(projection, "_bounded_subprocess", side_effect=runner or self.valid_runner),
        ):
            return projection.build_projection(self.gallery, self.carrier_path, cli_path=self.cli_path)

    def validate(self, output: Path, *, runner=None, validator=None):
        with (
            patch.object(projection, "_load_carrier_module", return_value=carrier),
            patch.object(carrier, "validate_carrier", side_effect=validator or self.static_validator),
            patch.object(projection, "_bounded_subprocess", side_effect=runner or self.valid_runner),
        ):
            return projection.validate_projection(output, self.gallery, self.carrier_path, cli_path=self.cli_path)

    def test_build_binds_two_avatars_exact_producer_and_transport_identity(self) -> None:
        calls = []

        def runner(command):
            calls.append(command)
            return self.valid_runner(command)

        value = self.build(runner=runner)
        self.assertEqual(tuple(value), projection.PROJECTION_KEYS)
        self.assertEqual([item["profile_id"] for item in value["avatars"]], list(PROFILE_IDS))
        self.assertEqual([item["instance_id"] for item in value["avatars"]], list(INSTANCE_IDS))
        self.assertEqual(len(calls), 2)
        cli_bytes = self.cli_path.read_bytes()
        self.assertEqual(
            value["producer_identity"],
            {
                "sha256": hashlib.sha256(cli_bytes).hexdigest(),
                "bytes": len(cli_bytes),
                "operation": projection.RUST_OPERATION,
                "format": projection.RUST_FORMAT,
            },
        )
        for profile_id, avatar in zip(PROFILE_IDS, value["avatars"]):
            self.assertEqual(avatar["source"]["path"], f"sources/{profile_id}.json")
            self.assertEqual(
                [item["path"] for item in avatar["artifacts"]],
                [f"{profile_id}/{name}" for name in smoke.EXPECTED_ARTIFACT_NAMES],
            )
            self.assertEqual(avatar["rust_inspection"]["operation"], projection.RUST_OPERATION)
        identity = projection.projection_identity(value)
        self.assertEqual(identity["scope"], projection.PROJECTION_IDENTITY_SCOPE)
        body = {key: value[key] for key in projection.PROJECTION_BODY_KEYS}
        self.assertEqual(identity, projection._transport_identity(body))

    def test_explicit_absolute_regular_non_symlink_executable_is_required(self) -> None:
        with self.assertRaises(projection.ProjectionError):
            projection.build_projection(self.gallery, self.carrier_path)
        with self.assertRaises(projection.ProjectionError):
            projection.build_projection(self.gallery, self.carrier_path, cli_path=Path("relative-cli"))
        non_executable = self.root / "non-executable"
        non_executable.write_bytes(b"not executable")
        with self.assertRaises(projection.ProjectionError):
            projection.build_projection(self.gallery, self.carrier_path, cli_path=non_executable)
        symlink = self.root / "cli-link"
        symlink.symlink_to(self.cli_path)
        with self.assertRaises(projection.ProjectionError):
            projection.build_projection(self.gallery, self.carrier_path, cli_path=symlink)
        with self.assertRaises(SystemExit):
            projection._parser().parse_args(
                [
                    "build",
                    "--gallery",
                    str(self.gallery),
                    "--carrier",
                    str(self.carrier_path),
                    "--output",
                    str(self.root / "out.json"),
                ]
            )

    def test_changed_executable_is_rejected_during_build_and_fresh_validation(self) -> None:
        calls = 0

        def changing_runner(command):
            nonlocal calls
            calls += 1
            result = self.valid_runner(command)
            if calls == 1:
                self.cli_path.write_bytes(self.cli_path.read_bytes() + b"# changed\n")
                self.cli_path.chmod(0o700)
            return result

        with self.assertRaises(projection.ProjectionError):
            self.build(runner=changing_runner)

        self.cli_path = self._write_executable("creature-kernel", "raise SystemExit(0)\n")
        value = self.build()
        output = self.root / "projection.json"
        with patch.object(projection, "_load_carrier_module", return_value=carrier):
            projection.write_projection(output, value)
        self.cli_path.write_bytes(self.cli_path.read_bytes() + b"# replacement\n")
        self.cli_path.chmod(0o700)
        with self.assertRaises(projection.ProjectionError):
            self.validate(output)

    def test_bounded_subprocess_rejects_stdout_and_stderr_over_limits(self) -> None:
        stdout_writer = self._write_executable(
            "stdout-writer",
            f"import os\nos.write(1, b'x' * {projection.MAX_RUST_STDOUT_BYTES + 1})\n",
        )
        stderr_writer = self._write_executable(
            "stderr-writer",
            f"import os\nos.write(2, b'x' * {projection.MAX_RUST_STDERR_BYTES + 1})\n",
        )
        with self.assertRaisesRegex(projection.ProjectionError, "stdout exceeds"):
            projection._bounded_subprocess([str(stdout_writer)])
        with self.assertRaisesRegex(projection.ProjectionError, "stderr exceeds"):
            projection._bounded_subprocess([str(stderr_writer)])

    def test_subprocess_return_code_malformed_output_and_source_mutation_fail_closed(self) -> None:
        with self.assertRaisesRegex(projection.ProjectionError, "exited 7"):
            self.build(runner=lambda command: (7, b"", b"broken"))
        with self.assertRaisesRegex(projection.ProjectionError, "valid JSON"):
            self.build(runner=lambda command: (0, b"not-json\n", b""))

        def mutating_runner(command):
            profile_id = Path(command[-1]).stem
            source_path = self.gallery / projection.SOURCE_DIR / f"{profile_id}.json"
            source_path.write_text('{"mutated":true}\n', encoding="utf-8")
            return self.valid_runner(command)

        with self.assertRaises(projection.ProjectionError):
            self.build(runner=mutating_runner)

    def test_rust_semantics_reject_forged_summary_wrong_collection_and_count_mismatch(self) -> None:
        valid = rust_inspection(PROFILE_IDS[0])
        self.assertEqual(projection._validate_rust_inspection(valid)["summary"], valid["summary"])

        forged_summary = deepcopy(valid)
        forged_summary["summary"]["parts"] = -1
        wrong_collection = deepcopy(valid)
        wrong_collection["graph"]["parts"] = {}
        count_mismatch = deepcopy(valid)
        count_mismatch["graph"]["parts"] = [{"fixture": True}]
        extra_summary = deepcopy(valid)
        extra_summary["summary"]["unexpected"] = 0
        wrong_contract = deepcopy(valid)
        wrong_contract["graph"]["contract"]["revision"] = True
        for case in (forged_summary, wrong_collection, count_mismatch, extra_summary, wrong_contract):
            with self.subTest(case=case):
                with self.assertRaises(projection.ProjectionError):
                    projection._validate_rust_inspection(case)

    def test_post_inspection_revalidation_rejects_pose_and_artifact_mutation(self) -> None:
        artifact_path = self.gallery / PROFILE_IDS[0] / smoke.EXPECTED_ARTIFACT_NAMES[0]

        def mutation_sensitive_validator(value, gallery):
            if (self.gallery / projection.POSE_FILE).read_bytes() != POSE_BYTES:
                raise carrier.CarrierError("pose changed")
            for profile_id in PROFILE_IDS:
                for name in smoke.EXPECTED_ARTIFACT_NAMES:
                    if (self.gallery / profile_id / name).read_bytes() != artifact_bytes(profile_id, name):
                        raise carrier.CarrierError("artifact changed")
            return deepcopy(self.payload), PROFILE_IDS, INSTANCE_IDS

        for label in ("pose", "artifact"):
            with self.subTest(label=label):
                (self.gallery / projection.POSE_FILE).write_bytes(POSE_BYTES)
                artifact_path.write_bytes(artifact_bytes(PROFILE_IDS[0], smoke.EXPECTED_ARTIFACT_NAMES[0]))
                calls = 0

                def runner(command):
                    nonlocal calls
                    calls += 1
                    result = self.valid_runner(command)
                    if calls == 1:
                        if label == "pose":
                            (self.gallery / projection.POSE_FILE).write_bytes(b"mutated pose\n")
                        else:
                            artifact_path.write_bytes(b"mutated artifact\n")
                    return result

                with self.assertRaises(projection.ProjectionError):
                    self.build(runner=runner, validator=mutation_sensitive_validator)

    def test_transport_reidentification_is_mechanical_but_fresh_validation_rejects_mutations(self) -> None:
        original = self.build()
        mutations = (
            ("pose", lambda value: value["shared_pose"].__setitem__("sha256", "b" * 64)),
            ("artifact", lambda value: value["avatars"][0]["artifacts"][0].__setitem__("sha256", "c" * 64)),
            ("manifest", lambda value: value["gallery_identity"].__setitem__("manifest_sha256", "d" * 64)),
        )
        for label, mutate in mutations:
            with self.subTest(label=label):
                changed = deepcopy(original)
                mutate(changed)
                changed = projection.identify_projection(changed, carrier_module=carrier)
                output = self.root / f"{label}-projection.json"
                with patch.object(projection, "_load_carrier_module", return_value=carrier):
                    projection.write_projection(output, changed)
                    self.assertEqual(projection.load_projection(output), changed)
                with self.assertRaises(projection.ProjectionError):
                    self.validate(output)

    def test_transport_identity_atomic_publication_and_bounds_fail_closed(self) -> None:
        value = self.build()
        output = self.root / "projection.json"
        with patch.object(projection, "_load_carrier_module", return_value=carrier):
            projection.write_projection(output, value)
            self.assertEqual(projection.load_projection(output), value)
            original_bytes = output.read_bytes()
            with self.assertRaises(projection.ProjectionError):
                projection.write_projection(output, value)
            self.assertEqual(output.read_bytes(), original_bytes)

        tampered = deepcopy(value)
        tampered["shared_pose"]["sha256"] = "e" * 64
        with self.assertRaises(projection.ProjectionError):
            projection._validate_projection_shape(tampered, carrier)
        oversized = deepcopy(value)
        oversized["avatars"][0]["metrics"]["padding"] = ["x" * 4000] * 1100
        with self.assertRaises(projection.ProjectionError):
            projection.identify_projection(oversized, carrier_module=carrier)

    def test_shape_rejects_duplicate_unsafe_or_reordered_identities(self) -> None:
        original = self.build()
        cases = []
        duplicate_instances = deepcopy(original)
        duplicate_instances["carrier_identity"]["instance_ids"][1] = duplicate_instances["carrier_identity"]["instance_ids"][0]
        cases.append(duplicate_instances)
        duplicate_profiles = deepcopy(original)
        duplicate_profiles["gallery_identity"]["profile_ids"][1] = duplicate_profiles["gallery_identity"]["profile_ids"][0]
        cases.append(duplicate_profiles)
        unsafe_instance = deepcopy(original)
        unsafe_instance["carrier_identity"]["instance_ids"][0] = "Avatar One"
        cases.append(unsafe_instance)
        wrong_carrier = deepcopy(original)
        wrong_carrier["carrier_identity"]["schema"] = "other.schema.v1"
        cases.append(wrong_carrier)
        reordered = deepcopy(original)
        reordered["avatars"] = list(reversed(reordered["avatars"]))
        cases.append(reordered)
        for case in cases:
            with self.subTest(case=case):
                with self.assertRaises(projection.ProjectionError):
                    projection.identify_projection(case, carrier_module=carrier)

    def test_build_is_deterministic_and_does_not_mutate_gallery(self) -> None:
        before = {path.relative_to(self.gallery): path.read_bytes() for path in self.gallery.rglob("*") if path.is_file()}
        first = self.build()
        second = self.build()
        after = {path.relative_to(self.gallery): path.read_bytes() for path in self.gallery.rglob("*") if path.is_file()}
        self.assertEqual(first, second)
        self.assertEqual(before, after)

    @unittest.skipUnless(REAL_GALLERY.is_dir() and REAL_CLI.is_file(), "cached real gallery or native Rust CLI is unavailable")
    def test_real_native_build_validate_default_and_alternate_pairs(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ck-real-projection-regression-") as temporary:
            root = Path(temporary)
            for label, profile_ids in (("default", PROFILE_IDS), ("alternate", ALTERNATE_IDS)):
                carrier_path = root / f"{label}-carrier.json"
                projection_path = root / f"{label}-projection.json"
                carrier.write_carrier(carrier_path, carrier.build_carrier(REAL_GALLERY, profile_ids, INSTANCE_IDS))
                with redirect_stdout(io.StringIO()):
                    self.assertEqual(
                        projection.main(
                            [
                                "build",
                                "--gallery",
                                str(REAL_GALLERY),
                                "--carrier",
                                str(carrier_path),
                                "--output",
                                str(projection_path),
                                "--cli",
                                str(REAL_CLI),
                            ]
                        ),
                        0,
                    )
                    self.assertEqual(
                        projection.main(
                            [
                                "validate",
                                "--gallery",
                                str(REAL_GALLERY),
                                "--carrier",
                                str(carrier_path),
                                "--projection",
                                str(projection_path),
                                "--cli",
                                str(REAL_CLI),
                            ]
                        ),
                        0,
                    )
                value = projection.load_projection(projection_path)
                self.assertEqual([avatar["profile_id"] for avatar in value["avatars"]], list(profile_ids))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
