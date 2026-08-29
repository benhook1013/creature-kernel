from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
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
from unittest.mock import Mock, patch


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


def runtime_input_instance(profile_id: str, instance_id: str) -> dict[str, object]:
    return {
        "instance_id": instance_id,
        "source": {"document": f"fixture.{profile_id}", "namespace": "fixture"},
        "prepared": {
            "basis": deepcopy(projection.EXPECTED_PREPARED_BASIS),
            "counts": {name: 0 for name in projection.PREPARED_COUNT_KEYS},
        },
        "structural": {
            "counts": {name: 0 for name in projection.STRUCTURAL_COUNT_KEYS},
        },
    }


def runtime_input_result(instance_sources: list[tuple[str, Path]]) -> dict[str, object]:
    return {
        "format": projection.RUST_FORMAT,
        "operation": projection.RUST_OPERATION,
        "stage": "runtime-input",
        "status": "success",
        "processing_complete": True,
        "diagnostics_complete": True,
        "diagnostics": [],
        "instances": [
            runtime_input_instance(Path(source_path).stem, instance_id)
            for instance_id, source_path in instance_sources
        ],
    }


def valid_cli_body() -> str:
    instances = {
        instance_id: runtime_input_instance(profile_id, instance_id)
        for instance_id, profile_id in zip(INSTANCE_IDS, PROFILE_IDS)
    }
    return (
        "import json\n"
        "import sys\n"
        f"instances = {instances!r}\n"
        "arguments = sys.argv[1:]\n"
        "if arguments != [\"inspect-runtime-input\", \"--instance\", arguments[2], \"--source\", arguments[4], \"--instance\", arguments[6], \"--source\", arguments[8]]:\n"
        "    raise SystemExit('unexpected inspect-runtime-input arguments')\n"
        "instance_ids = (arguments[2], arguments[6])\n"
        "print(json.dumps({\"format\": "
        f"{projection.RUST_FORMAT!r}, "
        "\"operation\": \"inspect-runtime-input\", \"stage\": \"runtime-input\", \"status\": \"success\", "
        "\"processing_complete\": True, \"diagnostics_complete\": True, \"diagnostics\": [], "
        "\"instances\": [instances[instance_ids[0]], instances[instance_ids[1]]]}))\n"
    )


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
        self.cli_path = self._write_executable("creature-kernel", valid_cli_body())

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
        instance_sources = [
            (command[3], Path(command[5])),
            (command[7], Path(command[9])),
        ]
        return 0, (json.dumps(runtime_input_result(instance_sources)) + "\n").encode("utf-8"), b""

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
        source_snapshot_bytes = {}

        def runner(command):
            calls.append(command)
            source_snapshot_bytes[command[3]] = Path(command[5]).read_bytes()
            source_snapshot_bytes[command[7]] = Path(command[9]).read_bytes()
            return self.valid_runner(command)

        value = self.build(runner=runner)
        self.assertEqual(tuple(value), projection.PROJECTION_KEYS)
        self.assertEqual([item["profile_id"] for item in value["avatars"]], list(PROFILE_IDS))
        self.assertEqual([item["instance_id"] for item in value["avatars"]], list(INSTANCE_IDS))
        self.assertEqual(len(calls), 1)
        self.assertEqual(
            calls[0][1:],
            [
                projection.RUST_OPERATION,
                "--instance",
                INSTANCE_IDS[0],
                "--source",
                calls[0][5],
                "--instance",
                INSTANCE_IDS[1],
                "--source",
                calls[0][9],
            ],
        )
        self.assertEqual(
            source_snapshot_bytes[calls[0][3]],
            (self.gallery / projection.SOURCE_DIR / f"{PROFILE_IDS[0]}.json").read_bytes(),
        )
        self.assertEqual(
            source_snapshot_bytes[calls[0][7]],
            (self.gallery / projection.SOURCE_DIR / f"{PROFILE_IDS[1]}.json").read_bytes(),
        )
        self.assertNotEqual(Path(calls[0][5]).resolve(), (self.gallery / projection.SOURCE_DIR / f"{PROFILE_IDS[0]}.json").resolve())
        self.assertNotEqual(Path(calls[0][9]).resolve(), (self.gallery / projection.SOURCE_DIR / f"{PROFILE_IDS[1]}.json").resolve())
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
            self.assertEqual(avatar["runtime_input_inspection"]["operation"], projection.RUST_OPERATION)
        identity = projection.projection_identity(value)
        self.assertEqual(identity["scope"], projection.PROJECTION_IDENTITY_SCOPE)
        body = {key: value[key] for key in projection.PROJECTION_BODY_KEYS}
        self.assertEqual(identity, projection._transport_identity(body))

    def test_cli_identity_uses_bounded_streaming_without_retaining_executable_bytes(self) -> None:
        large_cli = self.root / "large-cli"
        large_cli.write_bytes(b"x" * (projection.CLI_HASH_CHUNK_BYTES * 2 + 1))
        large_cli.chmod(0o700)
        read_sizes = []
        original_read = projection.os.read

        def read(fd, size):
            read_sizes.append(size)
            return original_read(fd, size)

        with (
            patch.object(projection, "_read_regular_file", side_effect=AssertionError("full executable read")),
            patch.object(projection.os, "read", side_effect=read),
        ):
            with tempfile.TemporaryDirectory(prefix="ck-projection-cli-snapshot-") as staging:
                path, identity = projection._validated_cli_producer(
                    carrier,
                    large_cli,
                    staging_directory=Path(staging),
                )
                self.assertNotEqual(path, large_cli)
                self.assertEqual(path.read_bytes(), large_cli.read_bytes())
                self.assertTrue(os.access(path, os.X_OK))
                self.assertFalse(os.access(path, os.W_OK))

        self.assertEqual(identity["sha256"], hashlib.sha256(large_cli.read_bytes()).hexdigest())
        self.assertEqual(identity["bytes"], large_cli.stat().st_size)
        self.assertTrue(read_sizes)
        self.assertLessEqual(max(read_sizes), projection.CLI_HASH_CHUNK_BYTES)

    def test_cli_identity_stream_preserves_size_bound(self) -> None:
        bounded_cli = self.root / "bounded-cli"
        bounded_cli.write_bytes(b"x" * 9)
        bounded_cli.chmod(0o700)
        with patch.object(projection, "MAX_CLI_BYTES", 8), self.assertRaisesRegex(
            projection.ProjectionError, "Rust CLI path exceeds the bounded size of 8 bytes"
        ):
            projection._validated_cli_producer(carrier, bounded_cli)

    def test_runtime_input_uses_one_private_cli_snapshot(self) -> None:
        marker_path = self.root / "inspection-count"
        replacement_cli_path = self.root / "replacement-cli"
        cli_paths_path = self.root / "cli-paths"
        result = runtime_input_result(
            [
                (INSTANCE_IDS[0], Path(f"{PROFILE_IDS[0]}.json")),
                (INSTANCE_IDS[1], Path(f"{PROFILE_IDS[1]}.json")),
            ]
        )
        cli_body = (
            "import json\n"
            "import os\n"
            "import sys\n"
            "from pathlib import Path\n"
            f"result = {result!r}\n"
            f"marker = Path({str(marker_path)!r})\n"
            f"replacement_cli = Path({str(replacement_cli_path)!r})\n"
            f"cli_paths = Path({str(cli_paths_path)!r})\n"
            "with cli_paths.open('a', encoding='utf-8') as handle:\n"
            "    handle.write(f'{sys.argv[0]}\\n')\n"
            "if sys.argv[1] != 'inspect-runtime-input' or len(sys.argv) != 10:\n"
            "    raise SystemExit('unexpected inspect-runtime-input arguments')\n"
            "count = int(marker.read_text(encoding='utf-8')) if marker.exists() else 0\n"
            "if count == 0:\n"
            "    replacement_cli.write_text('#!/bin/sh\\nexit 97\\n', encoding='utf-8')\n"
            "    replacement_cli.chmod(0o700)\n"
            "    os.replace(replacement_cli, Path(sys.argv[0]))\n"
            "marker.write_text(str(count + 1), encoding='utf-8')\n"
            "print(json.dumps(result))\n"
        )
        self.cli_path = self._write_executable("attacking-cli", cli_body)

        with (
            patch.object(projection, "_load_carrier_module", return_value=carrier),
            patch.object(carrier, "validate_carrier", side_effect=self.static_validator),
        ):
            value = projection.build_projection(self.gallery, self.carrier_path, cli_path=self.cli_path)

        cli_bytes = f"#!{sys.executable}\n{cli_body}".encode()
        self.assertEqual(marker_path.read_text(encoding="utf-8"), "1")
        staged_cli_paths = cli_paths_path.read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(staged_cli_paths), 1)
        self.assertEqual(len(set(staged_cli_paths)), 1)
        self.assertTrue(all(not Path(path).exists() for path in staged_cli_paths))
        self.assertEqual(value["producer_identity"]["sha256"], hashlib.sha256(cli_bytes).hexdigest())
        self.assertEqual(value["producer_identity"]["bytes"], len(cli_bytes))

    def test_cli_basename_sources_does_not_collide_with_private_source_staging(self) -> None:
        self.cli_path = self._write_executable("sources", valid_cli_body())

        value = self.build()

        self.assertEqual(value["producer_identity"]["operation"], projection.RUST_OPERATION)
        self.assertEqual([avatar["profile_id"] for avatar in value["avatars"]], list(PROFILE_IDS))

    def test_private_snapshots_bind_cli_and_source_during_path_replacement(self) -> None:
        original_source_paths = {
            profile_id: self.gallery / projection.SOURCE_DIR / f"{profile_id}.json"
            for profile_id in PROFILE_IDS
        }
        expected_sources = {profile_id: path.read_bytes() for profile_id, path in original_source_paths.items()}
        result = runtime_input_result(
            [
                (INSTANCE_IDS[0], Path(f"{PROFILE_IDS[0]}.json")),
                (INSTANCE_IDS[1], Path(f"{PROFILE_IDS[1]}.json")),
            ]
        )
        original_cli_path = self.root / "attacking-cli"
        replacement_cli_path = self.root / "replacement-cli"
        replacement_source_path = self.root / "replacement-source.json"
        marker_path = self.root / "inspection-count"
        staged_paths = self.root / "staged-paths"
        original_source = original_source_paths[PROFILE_IDS[0]]
        cli_body = (
            "import json\n"
            "import os\n"
            "import sys\n"
            "from pathlib import Path\n"
            f"result = {result!r}\n"
            f"expected_sources = {expected_sources!r}\n"
            f"original_cli = Path({str(original_cli_path)!r})\n"
            f"original_source = Path({str(original_source)!r})\n"
            f"replacement_cli = Path({str(replacement_cli_path)!r})\n"
            f"replacement_source = Path({str(replacement_source_path)!r})\n"
            f"marker = Path({str(marker_path)!r})\n"
            f"staged_paths = Path({str(staged_paths)!r})\n"
            "if Path(sys.argv[0]).resolve() == original_cli.resolve():\n"
            "    raise SystemExit('original CLI path was executed')\n"
            "if sys.argv[1] != 'inspect-runtime-input' or len(sys.argv) != 10:\n"
            "    raise SystemExit('unexpected inspect-runtime-input arguments')\n"
            "source_paths = (Path(sys.argv[5]), Path(sys.argv[9]))\n"
            "for source_path in source_paths:\n"
            "    if source_path.resolve() == original_source.resolve():\n"
            "        raise SystemExit('original source path was inspected')\n"
            "    profile_id = source_path.stem\n"
            "    if source_path.read_bytes() != expected_sources[profile_id]:\n"
            "        raise SystemExit('private source snapshot bytes changed')\n"
            "staged_paths.write_text(f'{sys.argv[0]}\\n{source_paths[0]}\\n{source_paths[1]}\\n', encoding='utf-8')\n"
            "count = int(marker.read_text(encoding='utf-8')) if marker.exists() else 0\n"
            "if count == 0:\n"
            "    replacement_source.write_text('{\"source\":{\"dependencies\":[],\"document\":\"attacker\",\"namespace\":\"fixture\"}}\\n', encoding='utf-8')\n"
            "    os.replace(replacement_source, original_source)\n"
            "    replacement_cli.write_text('#!/bin/sh\\nexit 97\\n', encoding='utf-8')\n"
            "    replacement_cli.chmod(0o700)\n"
            "    os.replace(replacement_cli, original_cli)\n"
            "marker.write_text(str(count + 1), encoding='utf-8')\n"
            "print(json.dumps(result))\n"
        )
        self.cli_path = self._write_executable(original_cli_path.name, cli_body)

        with (
            patch.object(projection, "_load_carrier_module", return_value=carrier),
            patch.object(carrier, "validate_carrier", side_effect=self.static_validator),
            self.assertRaisesRegex(
                projection.ProjectionError,
                f"source {PROFILE_IDS[0]} changed before post-inspection validation completed",
            ),
        ):
            projection.build_projection(self.gallery, self.carrier_path, cli_path=self.cli_path)

        self.assertEqual(marker_path.read_text(encoding="utf-8"), "1")
        self.assertEqual(
            original_source.read_bytes(),
            b'{"source":{"dependencies":[],"document":"attacker","namespace":"fixture"}}\n',
        )
        self.assertEqual(self.cli_path.read_text(encoding="utf-8"), "#!/bin/sh\nexit 97\n")
        staged_cli, staged_source0, staged_source1 = staged_paths.read_text(encoding="utf-8").splitlines()
        self.assertFalse(Path(staged_cli).exists())
        self.assertFalse(Path(staged_source0).exists())
        self.assertFalse(Path(staged_source1).exists())

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

    def test_main_projection_error_returns_bounded_exit_without_output(self) -> None:
        output = self.root / "projection.json"
        stdout = io.StringIO()
        stderr = io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            result = projection.main(
                [
                    "build",
                    "--gallery",
                    str(self.gallery),
                    "--carrier",
                    str(self.carrier_path),
                    "--output",
                    str(output),
                    "--cli",
                    str(self.root / "missing-cli"),
                ]
            )

        self.assertEqual(result, 2)
        self.assertEqual(stdout.getvalue(), "")
        self.assertRegex(
            stderr.getvalue(),
            r"\Aprojection-error: Rust CLI path is not a regular non-symlink file: "
            r"CarrierError: Rust CLI path is unavailable: .*/missing-cli\n\Z",
        )
        self.assertFalse(output.exists())

    def test_short_instance_list_is_rejected_before_indexing(self) -> None:
        short_carrier = deepcopy(self.carrier_value)
        short_carrier["instances"] = short_carrier["instances"][:1]
        short_carrier_path = self.root / "short-carrier.json"
        carrier.write_carrier(short_carrier_path, short_carrier)
        with (
            patch.object(projection, "_load_carrier_module", return_value=carrier),
            patch.object(carrier, "validate_carrier", side_effect=self.static_validator),
            patch.object(projection, "_bounded_subprocess", side_effect=self.valid_runner),
        ):
            with self.assertRaisesRegex(projection.ProjectionError, "exactly two instances"):
                projection.build_projection(self.gallery, short_carrier_path, cli_path=self.cli_path)

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

        self.cli_path = self._write_executable("creature-kernel", valid_cli_body())
        value = self.build(runner=projection._bounded_subprocess)
        output = self.root / "projection.json"
        with patch.object(projection, "_load_carrier_module", return_value=carrier):
            projection.write_projection(output, value)
        self.cli_path.write_bytes(self.cli_path.read_bytes() + b"# replacement\n")
        self.cli_path.chmod(0o700)
        with self.assertRaisesRegex(
            projection.ProjectionError,
            "projection does not exactly match fresh carrier/gallery/runtime-input evidence",
        ):
            self.validate(output, runner=projection._bounded_subprocess)

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

    def test_stop_process_only_kills_group_while_direct_child_is_live(self) -> None:
        exited = Mock(pid=101)
        exited.poll.return_value = 0
        live = Mock(pid=202)
        live.poll.return_value = None

        with patch.object(projection.os, "killpg") as killpg:
            projection._stop_process(exited)
            projection._stop_process(live)

        killpg.assert_called_once_with(live.pid, projection.signal.SIGKILL)
        exited.wait.assert_called_once_with(timeout=5)
        live.wait.assert_called_once_with(timeout=5)

    def test_bounded_subprocess_timeout_kills_and_waits_for_child(self) -> None:
        pid_path = self.root / "timeout-descendant.pid"
        descendant_body = (
            "from pathlib import Path\n"
            "import os\n"
            "import time\n"
            f"Path({str(pid_path)!r}).write_text(str(os.getpid()))\n"
            "time.sleep(30)\n"
        )
        sleeper = self._write_executable(
            "timeout-sleeper",
            "import os\n"
            "import subprocess\n"
            "import sys\n"
            "import time\n"
            f"subprocess.Popen([sys.executable, '-c', {descendant_body!r}])\n"
            "time.sleep(30)\n",
        )
        with patch.object(projection, "RUST_TIMEOUT_SECONDS", 2.0), self.assertRaisesRegex(
            projection.ProjectionError, "timed out after 2.0 seconds"
        ):
            projection._bounded_subprocess([str(sleeper)])
        self.assertTrue(pid_path.is_file(), "descendant did not start")
        descendant_pid = int(pid_path.read_text())
        deadline = projection.time.monotonic() + 2.0
        while projection.time.monotonic() < deadline:
            try:
                os.kill(descendant_pid, 0)
            except ProcessLookupError:
                break
            projection.time.sleep(0.01)
        else:
            self.fail("descendant survived process-group cleanup")

    def test_subprocess_return_code_malformed_output_and_source_mutation_fail_closed(self) -> None:
        with self.assertRaisesRegex(projection.ProjectionError, "exited 7"):
            self.build(runner=lambda command: (7, b"", b"broken"))
        with self.assertRaisesRegex(projection.ProjectionError, "valid JSON"):
            self.build(runner=lambda command: (0, b"not-json\n", b""))

        def mutating_runner(command):
            profile_id = Path(command[5]).stem
            source_path = self.gallery / projection.SOURCE_DIR / f"{profile_id}.json"
            source_path.write_text('{"mutated":true}\n', encoding="utf-8")
            return self.valid_runner(command)

        with self.assertRaises(projection.ProjectionError):
            self.build(runner=mutating_runner)

    def test_private_source_snapshot_replacement_is_rejected_before_publication(self) -> None:
        output = self.root / "replacement-projection.json"
        replacement_source = self.root / "replacement-source.json"
        result = runtime_input_result(
            [
                (INSTANCE_IDS[0], Path(f"{PROFILE_IDS[0]}.json")),
                (INSTANCE_IDS[1], Path(f"{PROFILE_IDS[1]}.json")),
            ]
        )
        replacement_bytes = (
            json.dumps(
                {
                    "source": {
                        "dependencies": [
                            {
                                "document": "attacker.dependency",
                                "namespace": "attacker",
                                "content_sha256": "sha256:" + "c" * 64,
                            }
                        ],
                        "document": f"fixture.{PROFILE_IDS[0]}",
                        "namespace": "fixture",
                    }
                },
                separators=(",", ":"),
            )
            + "\n"
        ).encode()
        cli_body = (
            "import json\n"
            "import os\n"
            "import sys\n"
            "from pathlib import Path\n"
            f"result = {result!r}\n"
            f"replacement_source = Path({str(replacement_source)!r})\n"
            f"replacement_bytes = {replacement_bytes!r}\n"
            "if sys.argv[1] != 'inspect-runtime-input' or len(sys.argv) != 10:\n"
            "    raise SystemExit('unexpected inspect-runtime-input arguments')\n"
            "source_path = Path(sys.argv[5])\n"
            "replacement_source.write_bytes(replacement_bytes)\n"
            "os.replace(replacement_source, source_path)\n"
            "print(json.dumps(result))\n"
        )
        self.cli_path = self._write_executable("snapshot-replacing-cli", cli_body)

        stdout = io.StringIO()
        stderr = io.StringIO()
        with (
            patch.object(projection, "_load_carrier_module", return_value=carrier),
            patch.object(carrier, "validate_carrier", side_effect=self.static_validator),
            redirect_stdout(stdout),
            redirect_stderr(stderr),
        ):
            result_code = projection.main(
                [
                    "build",
                    "--gallery",
                    str(self.gallery),
                    "--carrier",
                    str(self.carrier_path),
                    "--output",
                    str(output),
                    "--cli",
                    str(self.cli_path),
                ]
            )

        self.assertEqual(result_code, 2)
        self.assertEqual(stdout.getvalue(), "")
        self.assertRegex(stderr.getvalue(), "private source snapshot 0 changed during runtime-input inspection")
        self.assertFalse(output.exists())
        self.assertEqual(
            (self.gallery / projection.SOURCE_DIR / f"{PROFILE_IDS[0]}.json").read_bytes(),
            json.dumps(
                {"source": {"dependencies": [], "document": f"fixture.{PROFILE_IDS[0]}", "namespace": "fixture"}}
            ).encode()
            + b"\n",
        )

    def test_declared_dependencies_are_validated_in_python_but_not_replaced_by_compact_evidence(self) -> None:
        source_path = self.gallery / projection.SOURCE_DIR / f"{PROFILE_IDS[0]}.json"
        source_path.write_text(
            json.dumps(
                {
                    "source": {
                        "dependencies": [
                            {
                                "document": "fixture.dependency",
                                "namespace": "fixture",
                                "content_sha256": "sha256:" + "b" * 64,
                            }
                        ],
                        "document": f"fixture.{PROFILE_IDS[0]}",
                        "namespace": "fixture",
                    }
                }
            )
            + "\n",
            encoding="utf-8",
        )
        value = self.build()
        self.assertNotIn("dependencies", value["avatars"][0]["source"])

        source_path.write_text(
            json.dumps(
                {
                    "source": {
                        "dependencies": [{"document": "fixture.dependency", "namespace": "fixture", "content_sha256": "bad"}],
                        "document": f"fixture.{PROFILE_IDS[0]}",
                        "namespace": "fixture",
                    }
                }
            )
            + "\n",
            encoding="utf-8",
        )
        with self.assertRaisesRegex(projection.ProjectionError, "content_sha256"):
            self.build()

    def test_runtime_input_evidence_rejects_partial_reordered_and_malformed_results(self) -> None:
        valid = runtime_input_result(
            [
                (INSTANCE_IDS[0], Path(f"{PROFILE_IDS[0]}.json")),
                (INSTANCE_IDS[1], Path(f"{PROFILE_IDS[1]}.json")),
            ]
        )
        evidence = projection._validate_runtime_input_result(valid, INSTANCE_IDS)
        self.assertEqual(evidence[0]["prepared_basis"], projection.EXPECTED_PREPARED_BASIS)

        partial = deepcopy(valid)
        partial["instances"] = partial["instances"][:1]
        reordered = deepcopy(valid)
        reordered["instances"] = list(reversed(reordered["instances"]))
        wrong_basis = deepcopy(valid)
        wrong_basis["instances"][0]["prepared"]["basis"]["up"] = "+z"
        wrong_count = deepcopy(valid)
        wrong_count["instances"][0]["prepared"]["counts"]["parts"] = -1
        extra_instance_field = deepcopy(valid)
        extra_instance_field["instances"][0]["unexpected"] = True
        extra_result_field = deepcopy(valid)
        extra_result_field["unexpected"] = True
        for case in (partial, reordered, wrong_basis, wrong_count, extra_instance_field, extra_result_field):
            with self.subTest(case=case):
                with self.assertRaises(projection.ProjectionError):
                    projection._validate_runtime_input_result(case, INSTANCE_IDS)

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
        legacy_schema = deepcopy(original)
        legacy_schema["schema"] = "creature-kernel.disposable-ck-rust-projection.v1"
        cases.append(legacy_schema)
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
                native_runner = projection._bounded_subprocess
                build_calls = []

                def recording_build_runner(command):
                    build_calls.append(command)
                    return native_runner(command)

                with redirect_stdout(io.StringIO()):
                    with patch.object(projection, "_bounded_subprocess", side_effect=recording_build_runner):
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
                self.assertEqual(len(build_calls), 1)
                self.assertEqual(
                    build_calls[0][1:],
                    [
                        projection.RUST_OPERATION,
                        "--instance",
                        INSTANCE_IDS[0],
                        "--source",
                        build_calls[0][5],
                        "--instance",
                        INSTANCE_IDS[1],
                        "--source",
                        build_calls[0][9],
                    ],
                )

                validate_calls = []

                def recording_validate_runner(command):
                    validate_calls.append(command)
                    return native_runner(command)

                with redirect_stdout(io.StringIO()):
                    with patch.object(projection, "_bounded_subprocess", side_effect=recording_validate_runner):
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
                self.assertEqual(len(validate_calls), 1)
                self.assertEqual(
                    validate_calls[0][1:],
                    [
                        projection.RUST_OPERATION,
                        "--instance",
                        INSTANCE_IDS[0],
                        "--source",
                        validate_calls[0][5],
                        "--instance",
                        INSTANCE_IDS[1],
                        "--source",
                        validate_calls[0][9],
                    ],
                )
                value = projection.load_projection(projection_path)
                self.assertEqual([avatar["profile_id"] for avatar in value["avatars"]], list(profile_ids))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
