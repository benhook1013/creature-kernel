from __future__ import annotations

import importlib.util
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen


HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))


def load_module(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, HERE / filename)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


import common
publish = load_module("visual_review_publish", "publish.py")
serve = load_module("visual_review_serve", "serve.py")
publish_structure = load_module("visual_review_publish_structure", "publish_structure.py")


def run_app_in_node(
    *,
    entrypoint_replacement: str,
    context_setup: str,
    after_run: str = "",
    input_text: str | None = None,
) -> subprocess.CompletedProcess[str]:
    script = (
        r'''const fs = require("fs");
const vm = require("vm");
const appPath = process.argv[1];
let source = fs.readFileSync(appPath, "utf8");
const entrypoint = "  load();\n}());";
if (source.split(entrypoint).length !== 2) {
  throw new Error("unexpected browser app entrypoint");
}
source = source.replace(entrypoint, '''
        + json.dumps(entrypoint_replacement)
        + r''');
'''
        + context_setup
        + r'''
vm.runInNewContext(source, context, { filename: appPath });
'''
        + after_run
    )
    return subprocess.run(
        ["node", "-e", script, str(HERE / "static" / "app.js")],
        input=input_text,
        capture_output=True,
        text=True,
        check=True,
    )


class ReviewFixture(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / "reviews"
        self.root.mkdir()
        self.source = Path(self.temp.name) / "candidate.png"
        self.source.write_bytes(b"fake png bytes")
        self.manifest_path = Path(self.temp.name) / "manifest.json"
        self.manifest_path.write_text(json.dumps({
            "schema_version": 1,
            "id": "demo-review",
            "title": "Demo review",
            "description": "A safe description.",
            "instructions": "Choose one.",
            "groups": [{
                "id": "coat",
                "title": "Coat",
                "selection_mode": "single",
                "items": [{
                    "id": "warm",
                    "title": "Warm",
                    "source": str(self.source),
                    "description": "A candidate.",
                    "metadata": {"seed": 3},
                }],
            }],
        }), encoding="utf-8")

    def tearDown(self) -> None:
        self.temp.cleanup()

    def publish(self) -> Path:
        publish.publish_session(self.root, self.manifest_path)
        return self.root / "demo-review"

    def start_server(self):
        self.publish()
        server = serve.create_server(self.root, 0)
        thread = threading.Thread(target=server.serve_forever)
        thread.start()
        self.addCleanup(lambda: (server.shutdown(), thread.join(), server.server_close()))
        return server, f"http://127.0.0.1:{server.server_port}"

    @staticmethod
    def get(url: str):
        with urlopen(url, timeout=3) as response:
            return response.status, response.headers, response.read()

    def post(self, base: str, body: dict, **headers):
        default_headers = {
            "Content-Type": "application/json",
            "Origin": base,
            "X-Visual-Review-Token": self.server.write_token,
        }
        default_headers.update(headers)
        request = Request(
            base + "/api/reviews/demo-review/response",
            data=json.dumps(body).encode("utf-8"),
            headers=default_headers,
            method="POST",
        )
        return urlopen(request, timeout=3)

    def response_body(self) -> dict:
        return {
            "schema_version": 1,
            "review_id": "demo-review",
            "selections": {"coat": ["warm"]},
            "group_notes": {"coat": "looks good"},
            "overall_note": "keep warm",
        }


class ManifestAndPublishTests(ReviewFixture):
    def test_session_index_is_newest_first_with_publication_timestamps(self):
        older = self.publish()
        manifest = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        manifest["id"] = "newer-review"
        manifest["title"] = "Newer review"
        self.manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        publish.publish_session(self.root, self.manifest_path)
        newer = self.root / "newer-review"
        os.utime(older / "review.json", ns=(1_700_000_000_000_000_000,) * 2)
        os.utime(newer / "review.json", ns=(1_700_000_100_000_000_000,) * 2)

        sessions, errors = common.iter_sessions(self.root)

        self.assertEqual(errors, [])
        self.assertEqual([session["id"] for session in sessions], ["newer-review", "demo-review"])
        self.assertEqual(sessions[0]["published_at"], "2023-11-14T22:15:00.000000Z")
        self.assertEqual(sessions[1]["published_at"], "2023-11-14T22:13:20.000000Z")

    def test_session_index_reports_unrepresentable_publication_timestamp(self):
        self.publish()
        with patch.object(common, "datetime") as timestamp:
            timestamp.fromtimestamp.side_effect = OverflowError("timestamp out of range")
            sessions, errors = common.iter_sessions(self.root)

        self.assertEqual(sessions, [])
        self.assertEqual(errors, [{
            "id": "demo-review",
            "error": "invalid review.json publication timestamp: timestamp out of range",
        }])

    def test_normalization_and_exact_inventory(self):
        session = self.publish()
        normalized = json.loads((session / "review.json").read_text(encoding="utf-8"))
        self.assertEqual(normalized["kind"], "image")
        item = normalized["groups"][0]["items"][0]
        self.assertEqual(item["image"], "assets/warm.png")
        self.assertNotIn("source", item)
        self.assertEqual(sorted(path.name for path in (session / "assets").iterdir()), ["warm.png"])
        self.assertEqual((session / "assets" / "warm.png").read_bytes(), self.source.read_bytes())

    def test_existing_session_and_missing_root_refuse(self):
        self.publish()
        with self.assertRaises(publish.PublishError):
            publish.publish_session(self.root, self.manifest_path)
        with self.assertRaises(common.ValidationError):
            publish.publish_session(self.root / "missing", self.manifest_path)

    def test_expected_source_integrity_mismatch_fails_before_installation(self):
        expected = {
            "warm": {
                "bytes": len(self.source.read_bytes()),
                "sha256": hashlib.sha256(b"different source").hexdigest(),
            }
        }
        with self.assertRaisesRegex(publish.PublishError, "source integrity mismatch"):
            publish.publish_session(self.root, self.manifest_path, expected)
        self.assertFalse((self.root / "demo-review").exists())

    def test_review_root_rejects_symlink_path_components(self):
        real_parent = Path(self.temp.name) / "real-parent"
        real_parent.mkdir()
        linked_parent = Path(self.temp.name) / "linked-parent"
        linked_parent.symlink_to(real_parent, target_is_directory=True)
        root = linked_parent / "reviews"
        root.mkdir()
        with self.assertRaisesRegex(common.ValidationError, "symlinks"):
            publish.publish_session(root, self.manifest_path)

    def test_review_root_rejects_regular_replacement_between_validation_and_open(self):
        root = Path(self.temp.name) / "validated-reviews"
        root.mkdir()
        moved_root = Path(self.temp.name) / "validated-reviews-real"
        replacement_marker = root / "replacement-marker.txt"
        original_open_directory = publish._open_directory

        def swap_before_root_open(parent_fd, path_or_name, where):
            if where == "reviews root":
                root.rename(moved_root)
                root.mkdir()
                replacement_marker.write_text("different regular directory", encoding="utf-8")
            return original_open_directory(parent_fd, path_or_name, where)

        try:
            with patch.object(publish, "_open_directory", side_effect=swap_before_root_open):
                with self.assertRaisesRegex(publish.ValidationError, "changed while being opened"):
                    publish.publish_session(root, self.manifest_path)
            self.assertEqual(replacement_marker.read_text(encoding="utf-8"), "different regular directory")
        finally:
            if root.exists():
                replacement_marker.unlink(missing_ok=True)
                root.rmdir()
            if moved_root.exists():
                moved_root.rename(root)

    def test_publish_staging_stays_on_open_root_after_ancestor_swap(self):
        parent = Path(self.temp.name) / "publish-parent"
        parent.mkdir()
        root = parent / "reviews"
        root.mkdir()
        attacker_parent = Path(self.temp.name) / "attacker-parent"
        attacker_parent.mkdir()
        attacker_root = attacker_parent / "reviews"
        attacker_root.mkdir()
        sentinel = attacker_root / "keep.txt"
        sentinel.write_text("attacker destination", encoding="utf-8")
        moved_parent = Path(self.temp.name) / "publish-parent-real"
        original_open_directory = publish._open_directory
        original_mkdir = publish.os.mkdir
        staging_mkdirs = []

        def swap_after_root_open(parent_fd, path_or_name, where):
            fd = original_open_directory(parent_fd, path_or_name, where)
            if where == "reviews root":
                parent.rename(moved_parent)
                parent.symlink_to(attacker_parent, target_is_directory=True)
            return fd

        def record_staging_mkdir(path, mode=0o777, *, dir_fd=None):
            if Path(path).name.startswith(".demo-review.publish-"):
                staging_mkdirs.append((path, dir_fd, os.fstat(dir_fd) if dir_fd is not None else None))
            return original_mkdir(path, mode, dir_fd=dir_fd)

        try:
            with patch.object(publish, "_open_directory", side_effect=swap_after_root_open):
                with patch.object(publish.os, "mkdir", side_effect=record_staging_mkdir):
                    publish.publish_session(root, self.manifest_path)
        finally:
            if parent.is_symlink():
                parent.unlink()
            if moved_parent.exists():
                moved_parent.rename(parent)

        self.assertEqual(len(staging_mkdirs), 1)
        _, staging_parent_fd, staging_parent_info = staging_mkdirs[0]
        self.assertIsNotNone(staging_parent_fd)
        self.assertEqual(
            (staging_parent_info.st_dev, staging_parent_info.st_ino),
            (root.stat().st_dev, root.stat().st_ino),
        )
        self.assertTrue((root / "demo-review" / "review.json").is_file())
        self.assertEqual(sentinel.read_text(encoding="utf-8"), "attacker destination")
        self.assertEqual(sorted(path.name for path in attacker_root.iterdir()), ["keep.txt"])

    def test_symlink_unsupported_traversal_duplicate_and_no_unrelated_deletion(self):
        unrelated = self.root / "unrelated.txt"
        unrelated.write_text("keep", encoding="utf-8")
        link = Path(self.temp.name) / "link.png"
        link.symlink_to(self.source)
        for source in (str(link), str(Path(self.temp.name) / "bad.svg"), "../candidate.png"):
            if source.endswith("bad.svg"):
                Path(source).write_bytes(b"svg")
            manifest = json.loads(self.manifest_path.read_text(encoding="utf-8"))
            manifest["groups"][0]["items"][0]["source"] = source
            self.manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaises(common.ValidationError):
                publish.publish_session(self.root, self.manifest_path)
        manifest = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        # Reach duplicate-ID validation with an otherwise valid source.  The
        # preceding invalid-source cases must not mask this assertion.
        manifest["groups"][0]["items"][0]["source"] = str(self.source)
        manifest["groups"][0]["items"].append(dict(manifest["groups"][0]["items"][0], id="warm"))
        self.manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        with self.assertRaisesRegex(common.ValidationError, "duplicate id"):
            publish.publish_session(self.root, self.manifest_path)
        self.assertEqual(unrelated.read_text(encoding="utf-8"), "keep")
        self.assertEqual(list(self.root.iterdir()), [unrelated])

    def test_source_replacement_after_validation_is_rejected(self):
        alternate = Path(self.temp.name) / "alternate.png"
        alternate.write_bytes(b"alternate source")
        original_reader = publish.read_rich_manifest

        def read_then_replace(path):
            review, sources = original_reader(path)
            alternate.replace(self.source)
            return review, sources

        with patch.object(publish, "read_rich_manifest", side_effect=read_then_replace):
            with self.assertRaisesRegex(common.ValidationError, "changed while publishing"):
                publish.publish_session(self.root, self.manifest_path)
        self.assertFalse((self.root / "demo-review").exists())
        staging = list(self.root.glob(".demo-review.publish-*"))
        self.assertEqual(len(staging), 1)
        self.assertEqual(list(staging[0].iterdir()), [])

    def test_post_open_fstat_failures_close_descriptors(self):
        _, sources = common.read_rich_manifest(self.manifest_path)
        destination = Path(self.temp.name) / "descriptor-failures"
        destination.mkdir()
        destination_fd = os.open(destination, os.O_RDONLY | os.O_DIRECTORY)
        try:
            before = len(os.listdir("/proc/self/fd"))
            with patch.object(publish.os, "fstat", side_effect=OSError("injected copy fstat failure")):
                with self.assertRaisesRegex(OSError, "injected copy fstat failure"):
                    publish._copy_source(sources["warm"], destination_fd, "copy.png", "copy")
            self.assertEqual(len(os.listdir("/proc/self/fd")), before)

            before = len(os.listdir("/proc/self/fd"))
            with patch.object(publish.os, "fstat", side_effect=OSError("injected write fstat failure")):
                with self.assertRaisesRegex(OSError, "injected write fstat failure"):
                    publish._write_owned(destination_fd, "review.json", "{}\n")
            self.assertEqual(len(os.listdir("/proc/self/fd")), before)
        finally:
            os.close(destination_fd)

        original_open_directory = publish._open_directory
        original_fstat = publish.os.fstat
        target_fd = {"value": None}

        def track_root_fd(parent_fd, path_or_name, where):
            fd = original_open_directory(parent_fd, path_or_name, where)
            if where == "reviews root":
                target_fd["value"] = fd
            return fd

        def fail_opened_root(fd):
            if fd == target_fd["value"]:
                raise OSError("injected root fstat failure")
            return original_fstat(fd)

        before = len(os.listdir("/proc/self/fd"))
        with patch.object(publish, "_open_directory", side_effect=track_root_fd):
            with patch.object(publish.os, "fstat", side_effect=fail_opened_root):
                with self.assertRaisesRegex(OSError, "injected root fstat failure"):
                    publish.publish_session(self.root, self.manifest_path)
        self.assertEqual(len(os.listdir("/proc/self/fd")), before)

    def test_install_failure_cleans_owned_staging_but_not_concurrent_file(self):
        def fail_install(root_fd, source_name, destination_fd, destination_name):
            raise OSError("injected review install failure")

        with patch.object(publish, "_rename_noreplace", side_effect=fail_install):
            with self.assertRaises(OSError):
                publish.publish_session(self.root, self.manifest_path)
        self.assertFalse((self.root / "demo-review").exists())
        staging = list(self.root.glob(".demo-review.publish-*"))
        self.assertEqual(len(staging), 1)
        self.assertEqual(list(staging[0].iterdir()), [])

        def fail_with_concurrent_file(root_fd, source_name, destination_fd, destination_name):
            stage = self.root / source_name
            stage.joinpath("concurrent.txt").write_text("keep", encoding="utf-8")
            raise OSError("injected review install failure")

        with patch.object(publish, "_rename_noreplace", side_effect=fail_with_concurrent_file):
            with self.assertRaises(OSError):
                publish.publish_session(self.root, self.manifest_path)
        staging = sorted(self.root.glob(".demo-review.publish-*"))
        self.assertEqual(len(staging), 2)
        concurrent = [path for path in staging if (path / "concurrent.txt").exists()]
        self.assertEqual(len(concurrent), 1)
        self.assertEqual((concurrent[0] / "concurrent.txt").read_text(encoding="utf-8"), "keep")
        self.assertEqual(list(concurrent[0].iterdir()), [concurrent[0] / "concurrent.txt"])

    def test_no_visible_partial_final_session(self):
        original_install = publish._rename_noreplace
        observed = {}

        def inspect_before_install(root_fd, source_name, destination_fd, destination_name):
            stage = self.root / source_name
            observed["final_exists"] = (self.root / "demo-review").exists()
            observed["stage_entries"] = sorted(path.name for path in stage.iterdir())
            return original_install(root_fd, source_name, destination_fd, destination_name)

        with patch.object(publish, "_rename_noreplace", side_effect=inspect_before_install):
            publish.publish_session(self.root, self.manifest_path)
        self.assertFalse(observed["final_exists"])
        self.assertEqual(observed["stage_entries"], ["assets", "review.json"])
        session = self.root / "demo-review"
        self.assertEqual(sorted(path.name for path in session.iterdir()), ["assets", "review.json"])

    def test_failed_staging_cleanup_preserves_replacement_at_old_post_check_boundary(self):
        def replace_staging_before_cleanup(root_fd, source_name, destination_fd, destination_name):
            staging = self.root / source_name
            moved = self.root / f"{source_name}.owned"
            staging.rename(moved)
            staging.mkdir(mode=0o700)
            (staging / "replacement.txt").write_text("keep", encoding="utf-8")
            raise OSError("injected install failure")

        with patch.object(publish, "_rename_noreplace", side_effect=replace_staging_before_cleanup):
            with self.assertRaisesRegex(OSError, "injected install failure"):
                publish.publish_session(self.root, self.manifest_path)
        replacement = next(
            path
            for path in self.root.iterdir()
            if path.name.startswith(".demo-review.publish-") and not path.name.endswith(".owned")
        )
        self.assertEqual((replacement / "replacement.txt").read_text(encoding="utf-8"), "keep")
        owned = list(self.root.glob(".demo-review.publish-*.owned"))
        self.assertEqual(len(owned), 1)
        self.assertEqual(list(owned[0].iterdir()), [])

    def test_session_collision_during_atomic_install_preserves_existing_session(self):
        original_install = publish._rename_noreplace

        def collide(root_fd, source_name, destination_fd, destination_name):
            session = self.root / destination_name
            session.mkdir()
            (session / "sentinel.txt").write_text("keep", encoding="utf-8")
            return original_install(root_fd, source_name, destination_fd, destination_name)

        with patch.object(publish, "_rename_noreplace", side_effect=collide):
            with self.assertRaisesRegex(publish.PublishError, "session appeared during publish"):
                publish.publish_session(self.root, self.manifest_path)
        self.assertEqual(
            (self.root / "demo-review" / "sentinel.txt").read_text(encoding="utf-8"),
            "keep",
        )
        staging = list(self.root.glob(".demo-review.publish-*"))
        self.assertEqual(len(staging), 1)
        self.assertEqual(list(staging[0].iterdir()), [])

    def test_subject_context_normalization_and_rejection(self):
        manifest = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        manifest["subject_context"] = {
            "authored_summary": {"text": "Supplied interpretation", "unknowns": ["lighting"]},
            "descriptor_snapshot": {"height": 1.8},
            "provenance": {"build": "debug-1"},
        }
        self.manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        session = self.publish()
        review = json.loads((session / "review.json").read_text(encoding="utf-8"))
        self.assertEqual(review["subject_context"], manifest["subject_context"])

        for invalid in (
            {},
            {"unknown": {}},
            {"authored_summary": {"unknowns": []}},
            {"authored_summary": {"text": "x", "extra": "reject"}},
            {"descriptor_snapshot": []},
            {"provenance": "not an object"},
        ):
            manifest["id"] = "invalid-context"
            manifest["subject_context"] = invalid
            self.manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaises(common.ValidationError):
                publish.publish_session(self.root, self.manifest_path)


class StructureReviewFixture(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / "reviews"
        self.root.mkdir()
        self.structure_source = Path(self.temp.name) / "inspection.json"
        self.payload = {
            "format": "creature-kernel.provisional-structural-inspection.v1",
            "operation": "inspect-structure",
            "stage": "structural-validation",
            "status": "success",
            "processing_complete": True,
            "diagnostics_complete": True,
            "diagnostics": [],
            "summary": {"parts": 1},
            "graph": {"parts": [{"address": {"kind": "part", "role": "root"}}]},
        }
        self.structure_source.write_text(json.dumps(self.payload), encoding="utf-8")
        self.manifest_path = Path(self.temp.name) / "manifest.json"
        self.write_manifest()

    def tearDown(self) -> None:
        self.temp.cleanup()

    def write_manifest(self, **overrides: object) -> None:
        manifest: dict[str, object] = {
            "schema_version": 1,
            "id": "structure-review",
            "title": "Structure review",
            "kind": "structure",
            "structure_source": str(self.structure_source),
        }
        manifest.update(overrides)
        self.manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    def publish(self) -> Path:
        publish.publish_session(self.root, self.manifest_path)
        return self.root / "structure-review"


class StructureReviewPublishTests(StructureReviewFixture):
    def test_successful_no_image_structure_publication_and_immutable_copy(self):
        session = self.publish()
        normalized = json.loads((session / "review.json").read_text(encoding="utf-8"))
        self.assertEqual(normalized["kind"], "structure")
        self.assertEqual(normalized["groups"], [])
        self.assertEqual(normalized["structure"], self.payload)
        self.assertNotIn("structure_source", normalized)
        self.assertEqual(list((session / "assets").iterdir()), [])

        replacement = dict(self.payload, status="invalid-source", diagnostics=[{"code": "changed"}])
        self.structure_source.write_text(json.dumps(replacement), encoding="utf-8")
        reread = json.loads((session / "review.json").read_text(encoding="utf-8"))
        self.assertEqual(reread["structure"], self.payload)

    def test_structure_payload_is_exposed_by_existing_review_api(self):
        self.publish()
        server = serve.create_server(self.root, 0)
        thread = threading.Thread(target=server.serve_forever)
        thread.start()
        try:
            with urlopen(
                f"http://127.0.0.1:{server.server_port}/api/reviews/structure-review",
                timeout=3,
            ) as response:
                body = json.loads(response.read())
            self.assertEqual(body["review"]["kind"], "structure")
            self.assertEqual(body["review"]["structure"], self.payload)
            self.assertIsNone(body["response"])
        finally:
            server.shutdown()
            thread.join()
            server.server_close()

    def test_invalid_status_with_diagnostics_is_supported(self):
        self.payload["status"] = "invalid-source"
        self.payload["diagnostics"] = [{"code": "ck.test.invalid", "message": "bad source"}]
        self.payload.pop("graph")
        self.structure_source.write_text(json.dumps(self.payload), encoding="utf-8")
        session = self.publish()
        normalized = json.loads((session / "review.json").read_text(encoding="utf-8"))
        self.assertEqual(normalized["structure"]["status"], "invalid-source")
        self.assertEqual(normalized["structure"]["diagnostics"][0]["code"], "ck.test.invalid")

    def test_structure_envelope_rejects_unknown_revision_status_and_contradictions(self):
        invalid_payloads = (
            dict(self.payload, format="creature-kernel.provisional-structural-inspection.v999"),
            dict(self.payload, status="unknown-status"),
            dict(self.payload, processing_complete=False),
            dict(self.payload, diagnostics_complete=False),
            dict(self.payload, status="invalid-source", graph={}),
            dict(self.payload, status="resource-limit", processing_complete=False, diagnostics_complete=False),
        )
        for index, payload in enumerate(invalid_payloads):
            self.structure_source.write_text(json.dumps(payload), encoding="utf-8")
            self.write_manifest(id=f"invalid-envelope-{index}")
            with self.assertRaises(common.ValidationError):
                publish.publish_session(self.root, self.manifest_path)

        # A bounded diagnostic accumulator may report incomplete diagnostics
        # while processing still completed; retain that emitted non-success
        # combination rather than imposing a resolver-specific status policy.
        supported = dict(
            self.payload,
            status="invalid-source",
            diagnostics_complete=False,
            diagnostics=[{"code": "many-diagnostics"}],
        )
        supported.pop("graph")
        self.structure_source.write_text(json.dumps(supported), encoding="utf-8")
        self.write_manifest(id="incomplete-diagnostics")
        session = publish.publish_session(self.root, self.manifest_path)
        self.assertEqual(session["id"], "incomplete-diagnostics")

    def test_missing_malformed_non_object_oversized_and_out_of_bound_sources_fail(self):
        cases: list[tuple[str, object]] = [
            ("missing", {"kind": "structure"}),
            ("malformed", {"source_bytes": b"{"}),
            ("non-object", {"source_value": []}),
            (
                "oversized",
                {"source_bytes": b"{" + b'"x":"' + b"x" * common.MAX_STRUCTURE_JSON_BYTES + b'"}'},
            ),
            ("out-of-bound", {"structure_source": "../inspection.json"}),
        ]
        for label, change in cases:
            self.manifest_path.write_text(
                json.dumps({
                    "schema_version": 1,
                    "id": f"structure-{label}",
                    "title": "Structure review",
                    "kind": "structure",
                    "structure_source": str(self.structure_source),
                    **(change if isinstance(change, dict) and "structure_source" in change else {}),
                }),
                encoding="utf-8",
            )
            if "source_bytes" in change:
                self.structure_source.write_bytes(change["source_bytes"])
            elif "source_value" in change:
                self.structure_source.write_text(json.dumps(change["source_value"]), encoding="utf-8")
            elif label == "missing":
                self.manifest_path.write_text(
                    json.dumps({
                        "schema_version": 1,
                        "id": "structure-missing",
                        "title": "Structure review",
                        "kind": "structure",
                    }),
                    encoding="utf-8",
                )
            else:
                self.structure_source.write_text(json.dumps(self.payload), encoding="utf-8")
            with self.assertRaisesRegex(common.ValidationError, "structure"):
                publish.publish_session(self.root, self.manifest_path)

    def test_symlink_and_invalid_envelope_fail(self):
        link = Path(self.temp.name) / "inspection-link.json"
        link.symlink_to(self.structure_source)
        self.write_manifest(structure_source=str(link), id="structure-symlink")
        with self.assertRaises(common.ValidationError):
            publish.publish_session(self.root, self.manifest_path)

        for invalid in (
            {"status": "success"},
            dict(self.payload, format="unrelated.json", graph={}),
            dict(self.payload, operation="other", graph={}),
            dict(self.payload, status="invalid-source", diagnostics=[]),
            dict(self.payload, status="success", graph=[]),
        ):
            self.structure_source.write_text(json.dumps(invalid), encoding="utf-8")
            self.write_manifest(id="structure-invalid-envelope")
            with self.assertRaises(common.ValidationError):
                publish.publish_session(self.root, self.manifest_path)

    def test_image_kind_rejects_structure_source_and_structure_requires_source(self):
        self.write_manifest(kind="image", id="image-misuse")
        with self.assertRaisesRegex(common.ValidationError, "only valid for structure"):
            publish.publish_session(self.root, self.manifest_path)

        self.write_manifest(id="missing-source")
        manifest = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        del manifest["structure_source"]
        self.manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        with self.assertRaisesRegex(common.ValidationError, "structure_source is required"):
            publish.publish_session(self.root, self.manifest_path)


class StructurePublisherCLITests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.directory = Path(self.temp.name)
        self.root = self.directory / "reviews"
        self.root.mkdir()
        self.input = self.directory / "body.json"
        self.input.write_text("{}", encoding="utf-8")
        self.payload = {
            "format": "creature-kernel.provisional-structural-inspection.v1",
            "operation": "inspect-structure",
            "stage": "structural-validation",
            "status": "success",
            "processing_complete": True,
            "diagnostics_complete": True,
            "diagnostics": [],
            "graph": {"parts": []},
        }

    def tearDown(self) -> None:
        self.temp.cleanup()

    def fake_binary(self, body: str, *, name: str = "fake-kernel") -> Path:
        path = self.directory / name
        path.write_text("#!/usr/bin/env python3\n" + body, encoding="utf-8")
        path.chmod(0o755)
        return path

    def publish_with(self, binary: Path, **kwargs: object) -> Path:
        summary = publish_structure.publish_structure(
            self.root,
            self.input,
            creature_kernel=binary,
            **kwargs,
        )
        return Path(summary["session"])

    def test_success_publishes_real_cli_envelope_and_stable_metadata(self):
        binary = self.fake_binary(
            "import json, sys\n"
            f"sys.stdout.write({json.dumps(json.dumps(self.payload))})\n"
        )
        session = self.publish_with(binary, review_id="body-structure", title="Body structure")
        review = json.loads((session / "review.json").read_text(encoding="utf-8"))
        self.assertEqual(review["id"], "body-structure")
        self.assertEqual(review["title"], "Body structure")
        self.assertEqual(review["kind"], "structure")
        self.assertEqual(review["structure"], self.payload)

    def test_invalid_source_result_is_published_even_with_nonzero_cli_status(self):
        payload = dict(self.payload, status="invalid-source", diagnostics=[{"code": "bad"}])
        payload.pop("graph")
        binary = self.fake_binary(
            "import json, sys\n"
            f"sys.stdout.write({json.dumps(json.dumps(payload))})\n"
            "sys.exit(1)\n"
        )
        session = self.publish_with(binary, review_id="invalid-body")
        review = json.loads((session / "review.json").read_text(encoding="utf-8"))
        self.assertEqual(review["structure"]["status"], "invalid-source")

    def test_zero_exit_with_invalid_source_is_rejected(self):
        payload = dict(self.payload, status="invalid-source", diagnostics=[{"code": "bad"}])
        payload.pop("graph")
        binary = self.fake_binary(
            "import json, sys\n"
            f"sys.stdout.write({json.dumps(json.dumps(payload))})\n",
            name="inconsistent-kernel",
        )
        with self.assertRaisesRegex(publish_structure.StructurePublishError, "status 0 but reported invalid-source"):
            self.publish_with(binary, review_id="inconsistent-status")
        self.assertFalse((self.root / "inconsistent-status").exists())

    def test_missing_binary_and_process_failure_are_clear(self):
        with self.assertRaisesRegex(publish_structure.StructurePublishError, "cannot execute"):
            self.publish_with(self.directory / "missing-kernel")
        binary = self.fake_binary("import sys\nsys.stderr.write('boom')\nsys.exit(7)\n", name="failed-kernel")
        with self.assertRaisesRegex(publish_structure.StructurePublishError, "no JSON"):
            self.publish_with(binary)

    def test_malformed_multiple_and_oversized_output_fail_before_publication(self):
        cases = [
            ("malformed", "sys.stdout.write('{')\n"),
            ("multiple", "sys.stdout.write('{} {}')\n"),
            (
                "oversized",
                f"sys.stdout.write('x' * {publish_structure.MAX_STDOUT_BYTES + 1})\n",
            ),
        ]
        for name, body in cases:
            binary = self.fake_binary("import sys\n" + body, name=f"{name}-kernel")
            with self.assertRaises(publish_structure.StructurePublishError):
                self.publish_with(binary, review_id=f"bad-{name}")
            self.assertFalse((self.root / f"bad-{name}").exists())

    def test_timeout_is_bounded_and_does_not_publish(self):
        binary = self.fake_binary("import time\ntime.sleep(30)\n", name="slow-kernel")
        with patch.object(publish_structure, "INSPECTION_TIMEOUT_SECONDS", 0.05):
            with self.assertRaisesRegex(publish_structure.StructurePublishError, "timed out"):
                self.publish_with(binary, review_id="timed-out")
        self.assertFalse((self.root / "timed-out").exists())

    def test_no_overwrite_preserves_existing_session(self):
        binary = self.fake_binary(
            "import json, sys\n"
            f"sys.stdout.write({json.dumps(json.dumps(self.payload))})\n"
        )
        session = self.publish_with(binary, review_id="same-id", title="First")
        before = (session / "review.json").read_bytes()
        with self.assertRaisesRegex(publish_structure.StructurePublishError, "already exists"):
            self.publish_with(binary, review_id="same-id", title="Second")
        self.assertEqual((session / "review.json").read_bytes(), before)


class HTTPTests(ReviewFixture):
    def setUp(self) -> None:
        super().setUp()
        self.server, self.base = self.start_server()

    def test_index_review_asset_and_response_happy_paths(self):
        status, headers, body = self.get(self.base + "/")
        self.assertEqual(status, 200)
        self.assertIn(b"visual reviews", body)
        self.assertEqual(headers["X-Content-Type-Options"], "nosniff")
        status, _, body = self.get(self.base + "/api/sessions")
        self.assertEqual(status, 200)
        index = json.loads(body)
        self.assertEqual(index["sessions"][0]["id"], "demo-review")
        self.assertRegex(index["sessions"][0]["published_at"], r"Z$")
        status, headers, body = self.get(self.base + "/static/style.css")
        self.assertEqual(status, 200)
        self.assertEqual(headers["Content-Type"].split(";")[0], "text/css")
        self.assertIn(b".option-grid", body)
        status, headers, body = self.get(self.base + "/static/app.js")
        self.assertEqual(status, 200)
        self.assertEqual(headers["Content-Type"].split(";")[0], "text/javascript")
        self.assertIn(b"What you're looking at", body)
        status, _, body = self.get(self.base + "/review/demo-review")
        self.assertEqual(status, 200)
        self.assertIn(b"visual-review-write-token", body)
        status, headers, body = self.get(self.base + "/api/reviews/demo-review/assets/warm.png")
        self.assertEqual((status, headers["Content-Type"].split(";")[0], body), (200, "image/png", b"fake png bytes"))
        head = Request(self.base + "/api/reviews/demo-review/assets/warm.png", method="HEAD")
        with urlopen(head, timeout=3) as response:
            self.assertEqual(response.status, 200)
            self.assertEqual(response.headers["Content-Length"], str(len(b"fake png bytes")))
            self.assertEqual(response.read(), b"")
        with self.post(self.base, self.response_body()) as response:
            saved = json.loads(response.read())
        self.assertEqual(saved["review_id"], "demo-review")
        self.assertRegex(saved["saved_at"], r"Z$")
        _, _, api_body = self.get(self.base + "/api/reviews/demo-review")
        self.assertEqual(json.loads(api_body)["response"]["selections"], {"coat": ["warm"]})

    def test_default_server_binds_loopback(self):
        self.assertEqual(self.server.server_address[0], "127.0.0.1")

    def test_lan_read_only_server_allows_gets_but_rejects_remote_write(self):
        self.server.shutdown()
        self.server.server_close()
        # Use a separate listener so this test does not depend on an external
        # interface; 127.0.0.1 reaches the wildcard socket locally.
        lan_server = serve.create_server(self.root, 0, lan_read_only=True)
        lan_thread = threading.Thread(target=lan_server.serve_forever)
        lan_thread.start()
        self.addCleanup(lambda: (lan_server.shutdown(), lan_thread.join(), lan_server.server_close()))
        self.assertEqual(lan_server.server_address[0], "0.0.0.0")
        lan_base = f"http://127.0.0.1:{lan_server.server_port}"

        status, _, body = self.get(lan_base + "/")
        self.assertEqual(status, 200)
        self.assertIn(b"visual reviews", body)
        status, _, body = self.get(lan_base + "/api/reviews/demo-review")
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)["review"]["id"], "demo-review")

        response_path = self.root / "demo-review" / "response.json"
        self.assertFalse(response_path.exists())
        request_headers = {
            "Content-Type": "application/json",
            "X-Visual-Review-Token": lan_server.write_token,
        }

        request_headers.update({
            "Host": f"192.0.2.10:{lan_server.server_port}",
            "Origin": f"http://192.0.2.10:{lan_server.server_port}",
        })
        request = Request(
            lan_base + "/api/reviews/demo-review/response",
            data=json.dumps(self.response_body()).encode("utf-8"),
            headers=request_headers,
            method="POST",
        )
        with self.assertRaises(HTTPError) as caught:
            urlopen(request, timeout=3)
        self.assertEqual(caught.exception.code, 403)
        self.assertFalse(response_path.exists())

        sentinel = b'{"unchanged":true}\n'
        response_path.write_bytes(sentinel)
        request_headers.update({
            "Host": f"localhost:{lan_server.server_port}",
            "Origin": f"http://localhost:{lan_server.server_port}",
        })
        request = Request(
            lan_base + "/api/reviews/demo-review/response",
            data=json.dumps(self.response_body()).encode("utf-8"),
            headers=request_headers,
            method="POST",
        )
        with self.assertRaises(HTTPError) as caught:
            urlopen(request, timeout=3)
        self.assertEqual(caught.exception.code, 403)
        self.assertEqual(response_path.read_bytes(), sentinel)

    def test_rejection_paths(self):
        body = self.response_body()
        for path in (
            "/api/reviews/demo-review/assets/..%2Freview.json",
            "/api/reviews/demo-review/assets/%2e%2e%2freview.json",
        ):
            with self.assertRaises(HTTPError) as caught:
                self.get(self.base + path)
            self.assertIn(caught.exception.code, (400, 404))
        bad = dict(body, selections={"coat": ["unknown"]})
        with self.assertRaises(HTTPError) as caught:
            self.post(self.base, bad)
        self.assertEqual(caught.exception.code, 400)
        with self.assertRaises(HTTPError) as caught:
            self.post(self.base, body, **{"X-Visual-Review-Token": "wrong"})
        self.assertEqual(caught.exception.code, 403)
        with self.assertRaises(HTTPError) as caught:
            self.post(self.base, body, **{"X-Visual-Review-Token": ""})
        self.assertEqual(caught.exception.code, 403)
        with self.assertRaises(HTTPError) as caught:
            self.post(self.base, body, Origin="https://example.invalid")
        self.assertEqual(caught.exception.code, 403)
        oversized = json.dumps(dict(body, overall_note="x" * (64 * 1024))).encode()
        request = Request(self.base + "/api/reviews/demo-review/response", data=oversized, headers={
            "Content-Type": "application/json",
            "Origin": self.base,
            "X-Visual-Review-Token": self.server.write_token,
        }, method="POST")
        with self.assertRaises(HTTPError) as caught:
            urlopen(request, timeout=3)
        self.assertEqual(caught.exception.code, 413)

    def test_asset_extension_file_not_in_allow_list_is_not_served(self):
        stray = self.root / "demo-review" / "assets" / "stray.png"
        stray.write_bytes(b"not in manifest")
        with self.assertRaises(HTTPError) as caught:
            self.get(self.base + "/api/reviews/demo-review/assets/stray.png")
        self.assertEqual(caught.exception.code, 404)

    def test_assets_parent_swap_after_validation_stays_on_open_directory(self):
        session = self.root / "demo-review"
        assets = session / "assets"
        moved_assets = session / "assets-real"
        outside = Path(self.temp.name) / "outside-assets"
        outside.mkdir()
        (outside / "warm.png").write_bytes(b"outside asset")
        original_open_regular = serve._open_regular
        calls = {"asset": 0}

        def swap_on_route(parent_fd, name, where):
            if where == "review asset":
                calls["asset"] += 1
                assets.rename(moved_assets)
                assets.symlink_to(outside)
            return original_open_regular(parent_fd, name, where)

        try:
            with patch.object(serve, "_open_regular", side_effect=swap_on_route):
                status, _, body = self.get(self.base + "/api/reviews/demo-review/assets/warm.png")
            self.assertEqual((status, body), (200, b"fake png bytes"))
            self.assertEqual(calls["asset"], 1)
            self.assertEqual((outside / "warm.png").read_bytes(), b"outside asset")
        finally:
            if assets.is_symlink():
                assets.unlink()
            if moved_assets.exists():
                moved_assets.rename(assets)

    def test_response_parent_swap_after_validation_stays_on_open_session(self):
        session = self.root / "demo-review"
        moved_session = self.root / "demo-review-real"
        outside = Path(self.temp.name) / "outside-session"
        outside.mkdir()
        (outside / "response.json").write_text("outside", encoding="utf-8")
        original_atomic = serve.VisualReviewHandler._atomic_response

        def swap_then_save(handler, session_fd, value):
            session.rename(moved_session)
            session.symlink_to(outside, target_is_directory=True)
            try:
                return original_atomic(handler, session_fd, value)
            finally:
                session.unlink()
                moved_session.rename(session)

        with patch.object(serve.VisualReviewHandler, "_atomic_response", new=swap_then_save):
            with self.post(self.base, self.response_body()) as response:
                self.assertEqual(response.status, 200)
        self.assertEqual((outside / "response.json").read_text(encoding="utf-8"), "outside")
        self.assertEqual(json.loads((session / "response.json").read_text(encoding="utf-8"))["review_id"], "demo-review")

    def test_atomic_repeat_save_only_changes_response(self):
        session = self.root / "demo-review"
        review_before = (session / "review.json").read_bytes()
        with self.post(self.base, self.response_body()) as response:
            first = json.loads(response.read())
        with self.post(self.base, dict(self.response_body(), overall_note="second")) as response:
            second = json.loads(response.read())
        self.assertNotEqual(first["saved_at"], "")
        self.assertEqual(second["overall_note"], "second")
        self.assertEqual((session / "review.json").read_bytes(), review_before)
        self.assertEqual(sorted(path.name for path in session.iterdir()), ["assets", "response.json", "review.json"])


class SubjectContextHTTPTests(ReviewFixture):
    def setUp(self) -> None:
        super().setUp()
        manifest = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        manifest["subject_context"] = {
            "authored_summary": {"text": "Context text", "unknowns": ["unknown detail"]},
            "descriptor_snapshot": {"shape": "compact"},
            "provenance": {"render": "test"},
        }
        self.manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        self.server, self.base = self.start_server()

    def test_context_is_preserved_by_review_get(self):
        _, _, body = self.get(self.base + "/api/reviews/demo-review")
        review = json.loads(body)["review"]
        self.assertEqual(review["subject_context"]["authored_summary"]["unknowns"], ["unknown detail"])
        self.assertEqual(review["subject_context"]["descriptor_snapshot"], {"shape": "compact"})


class StaticAssetTests(unittest.TestCase):
    def test_regional_exact_five_markup_is_compact_and_json_is_collapsed(self):
        context_setup = r'''
function element(tagName) {
  return {
    tagName: tagName,
    children: [],
    attributes: {},
    className: "",
    dataset: {},
    style: {},
    open: false,
    textContent: "",
    appendChild: function (child) { this.children.push(child); return child; },
    removeChild: function (child) {
      const index = this.children.indexOf(child);
      if (index >= 0) { this.children.splice(index, 1); }
      return child;
    },
    get firstChild() { return this.children[0] || null; },
    setAttribute: function (name, value) { this.attributes[name] = String(value); },
    addEventListener: function () {},
    cloneNode: function () {
      const copy = element(this.tagName);
      copy.className = this.className;
      copy.textContent = this.textContent;
      copy.attributes = Object.assign({}, this.attributes);
      return copy;
    },
  };
}

const app = element("main");
const context = {
  document: {
    title: "",
    body: element("body"),
    documentElement: element("html"),
    getElementById: function () { return app; },
    createElement: element,
  },
  window: {},
};
'''
        after_run = r'''

function reviewCase(groupId, itemCount) {
  const items = Array.from({length: itemCount}, function (_, index) {
    return {
      id: "item-" + index,
      title: "Item " + index,
      image: "assets/item-" + index + ".png",
      metadata: {index: index},
    };
  });
  context.__renderReview({
    review: {
      id: "review-" + groupId + "-" + itemCount,
      title: "Review",
      description: "Review purpose",
      subject_context: {
        descriptor_snapshot: {shape: "compact"},
        provenance: {render: "test"},
      },
      groups: [{
        id: groupId,
        title: "Gallery",
        selection_mode: "none",
        items: items,
      }],
    },
    response: {selections: {}, group_notes: {}, overall_note: ""},
  });
  const form = app.children.find(function (child) { return child.tagName === "form"; });
  const section = form.children.find(function (child) { return child.tagName === "section" && child.dataset.groupId === groupId; });
  const card = section.children[1].children[0];
  const body = card.children[1];
  const metadata = body.children.find(function (child) { return child.tagName === "details" || child.tagName === "pre"; });
  const contextPanel = app.children.find(function (child) { return child.className === "subject-context"; });
  const contextDetails = contextPanel.children.filter(function (child) { return child.tagName === "details"; });
  return {
    sectionClass: section.className,
    metadataTag: metadata.tagName,
    metadataOpen: metadata.open,
    purpose: contextPanel.children[1].textContent,
    contextDetailsOpen: contextDetails.map(function (details) { return details.open; }),
  };
}

process.stdout.write(JSON.stringify({
  exactFive: reviewCase("regional-surface-gallery", 5),
  regionalFour: reviewCase("regional-surface-gallery", 4),
  nonRegionalFive: reviewCase("other-gallery", 5),
}));
'''
        completed = run_app_in_node(
            entrypoint_replacement="  globalThis.__renderReview = renderReview;\n}());",
            context_setup=context_setup,
            after_run=after_run,
        )
        self.assertEqual(
            json.loads(completed.stdout),
            {
                "exactFive": {
                    "sectionClass": "review-group regional-exact-five-gallery",
                    "metadataTag": "details",
                    "metadataOpen": False,
                    "purpose": "Review purpose",
                    "contextDetailsOpen": [False, False],
                },
                "regionalFour": {
                    "sectionClass": "review-group",
                    "metadataTag": "pre",
                    "metadataOpen": False,
                    "purpose": "Review purpose",
                    "contextDetailsOpen": [False, False],
                },
                "nonRegionalFive": {
                    "sectionClass": "review-group",
                    "metadataTag": "pre",
                    "metadataOpen": False,
                    "purpose": "Review purpose",
                    "contextDetailsOpen": [False, False],
                },
            },
        )

    def test_subject_context_leads_with_purpose_and_collapses_json_by_default(self):
        context_setup = r'''
function element(tagName) {
  return {
    tagName: tagName,
    children: [],
    attributes: {},
    className: "",
    open: false,
    textContent: "",
    appendChild: function (child) { this.children.push(child); return child; },
    setAttribute: function (name, value) { this.attributes[name] = String(value); },
  };
}
const context = {
  document: {
    getElementById: function () { return null; },
    createElement: element,
  },
  window: {},
};
'''
        after_run = r'''
function detailsSummary(details) {
  return {
    tagName: details.tagName,
    className: details.className,
    open: details.open,
    summary: details.children[0].textContent,
    pre: details.children[1].textContent,
    ariaLabel: details.attributes["aria-label"] || null,
  };
}
const metadata = context.__metadataBlock({id: "profile-a", metadata: {seed: 3}}, true);
const panel = context.__subjectContextBlock({
  authored_summary: {text: "The resolved artifact purpose.", unknowns: ["lighting"]},
  descriptor_snapshot: {shape: "compact"},
  provenance: {render: "test"},
}, {description: "Legacy review purpose."});
const fallbackPanel = context.__subjectContextBlock({
  descriptor_snapshot: {shape: "legacy"},
}, {description: "Legacy review purpose."});
const descriptionOnlyPanel = context.__subjectContextBlock(null, {description: "Description-only review purpose."});
process.stdout.write(JSON.stringify({
  metadata: detailsSummary(metadata),
  purpose: panel.children[1].textContent,
  unknownHeading: panel.children[2].textContent,
  descriptor: detailsSummary(panel.children[4]),
  provenance: detailsSummary(panel.children[5]),
  fallbackPurpose: fallbackPanel.children[1].textContent,
  descriptionOnlyPurpose: descriptionOnlyPanel.children[1].textContent,
}));
'''
        completed = run_app_in_node(
            entrypoint_replacement=(
                "  globalThis.__metadataBlock = metadataBlock;\n"
                "  globalThis.__subjectContextBlock = subjectContextBlock;\n"
                "}());"
            ),
            context_setup=context_setup,
            after_run=after_run,
        )
        rendered = json.loads(completed.stdout)
        self.assertEqual(
            rendered["metadata"],
            {
                "tagName": "details",
                "className": "json-disclosure metadata-disclosure",
                "open": False,
                "summary": "Technical metadata for profile-a",
                "pre": '{\n  "seed": 3\n}',
                "ariaLabel": "Technical metadata for profile-a",
            },
        )
        self.assertFalse(rendered["descriptor"]["open"])
        self.assertEqual(rendered["descriptor"]["summary"], "Generated descriptor snapshot")
        self.assertEqual(rendered["purpose"], "The resolved artifact purpose.")
        self.assertEqual(rendered["unknownHeading"], "Unknowns")
        self.assertFalse(rendered["provenance"]["open"])
        self.assertEqual(rendered["fallbackPurpose"], "Legacy review purpose.")
        self.assertEqual(rendered["descriptionOnlyPurpose"], "Description-only review purpose.")

    def test_image_accessible_labels_include_description_without_html_interpolation(self):
        js = (HERE / "static" / "app.js").read_text(encoding="utf-8")
        context_setup = r'''
const context = {
  document: { getElementById: function () { return null; } },
  window: {}
};
'''
        after_run = r'''
const items = JSON.parse(fs.readFileSync(0, "utf8"));
process.stdout.write(JSON.stringify(items.map(context.__imageAccessibleLabel)));
'''
        completed = run_app_in_node(
            entrypoint_replacement="  globalThis.__imageAccessibleLabel = imageAccessibleLabel;\n}());",
            context_setup=context_setup,
            after_run=after_run,
            input_text=json.dumps([
                {"title": "Front", "description": "Control guide <not geometry>"},
                {"title": "Side"},
            ]),
        )
        self.assertEqual(
            json.loads(completed.stdout),
            ["Front — Control guide <not geometry>", "Side"],
        )
        self.assertIn("function imageDescription(item)", js)
        self.assertIn("function imageAccessibleLabel(item)", js)
        self.assertIn('return description ? title + " — " + description : title;', js)
        self.assertIn('imageButton.setAttribute("aria-label", "Expand " + imageLabel);', js)
        self.assertIn("image.alt = imageLabel;", js)
        self.assertIn("nextImage.alt = imageLabel;", js)
        self.assertIn(
            'nextImage.setAttribute("aria-label", imageDescription(item) ? "Show next comparison image: " + imageLabel : "Show next comparison image");',
            js,
        )

    def test_image_comparator_exposes_group_navigation_and_stale_load_guard(self):
        js = (HERE / "static" / "app.js").read_text(encoding="utf-8")
        css = (HERE / "static" / "style.css").read_text(encoding="utf-8")
        for contract in (
            "function openImage(items, selectedIndex)",
            "var imageItems = group.items.map",
            "openImage(imageItems, itemIndex);",
            'event.key === "ArrowLeft"',
            'event.key === "ArrowRight"',
            "function showItem(index, focusImage)",
            "function restoreViewport(viewportState)",
            "function captureViewport()",
            "showItem(requestedIndex - 1, image !== null && document.activeElement === image);",
            "showItem(requestedIndex + 1, image !== null && document.activeElement === image);",
            "showItem(requestedIndex + 1, true);",
            "showItem(requestedIndex - 1, false);",
            "showItem(requestedIndex + 1, false);",
            "showItem(requestedIndex, false);",
            "viewport.scrollLeft = viewportState.scrollLeft;",
            "viewport.scrollTop = viewportState.scrollTop;",
            "if (viewportState) {",
            "restoreViewport(viewportState);",
            "if (focusImage)",
            "focusPreservingViewport(image);",
            'node("button", "Previous"',
            'node("button", "Next"',
            "positionLabel.textContent = displayedPositionText()",
            'Use Previous/Next, the Left/Right arrow keys',
            'nextImage.addEventListener("click"',
            'nextImage.addEventListener("load"',
            'nextImage.addEventListener("error"',
            'loadToken !== imageLoadToken || requestedIndex !== targetIndex',
            'nextImage.alt = imageLabel',
            'nextImage.title = item.title',
            'nextImage.setAttribute("role", "button")',
            'nextImage.setAttribute("aria-label", imageDescription(item) ? "Show next comparison image: " + imageLabel : "Show next comparison image")',
            'nextImage.addEventListener("keydown", showNextImage)',
            "var returnFocus = document.activeElement",
            "document.documentElement.contains(returnFocus)",
            "function closeImageDialog()",
            'close.addEventListener("click", closeImageDialog)',
            "closeImageDialog();",
        ):
            self.assertIn(contract, js)
        for selector in (".image-navigation-control", ".image-position", ".image-dialog-instructions", ".image-dialog img:focus-visible"):
            self.assertIn(selector, css)

    def test_image_comparator_keeps_desktop_header_height_stable(self):
        css = (HERE / "static" / "style.css").read_text(encoding="utf-8")
        self.assertIn("flex-wrap: nowrap", css)
        self.assertIn("flex: 1 1 auto", css)
        self.assertIn("text-overflow: ellipsis", css)
        self.assertIn("white-space: nowrap", css)
        self.assertIn("@media (max-width: 52rem)", css)
        self.assertIn("flex-wrap: wrap", css)

    def test_image_comparator_names_requested_item_during_initial_load(self):
        js = (HERE / "static" / "app.js").read_text(encoding="utf-8")
        self.assertIn(
            'var heading = node("h2", items.length ? items[initialIndex].title : "Image comparison", "image-dialog-title");',
            js,
        )
        self.assertIn(
            'var headingIndex = displayedIndex >= 0 ? displayedIndex : requestedIndex;',
            js,
        )
        self.assertIn(
            'heading.textContent = headingIndex >= 0 && headingIndex < items.length ? items[headingIndex].title : "Image comparison";',
            js,
        )

    def test_image_viewer_preloads_and_captures_latest_viewport_on_winning_load(self):
        js = (HERE / "static" / "app.js").read_text(encoding="utf-8")
        self.assertIn("var image = null;", js)
        self.assertNotIn("canvas.appendChild(image);", js)
        self.assertNotIn("preserveViewport", js)
        self.assertNotIn("image.src = item.source;", js)
        self.assertIn("nextImage.src = item.source;", js)
        self.assertIn("var viewportState = image ? captureViewport() : null;", js)
        self.assertIn("canvas.replaceChild(nextImage, image);", js)
        self.assertIn("canvas.appendChild(nextImage);", js)
        self.assertIn("if (viewportState) {\n          restoreViewport(viewportState);\n        } else {\n          fitToViewport();", js)
        load_handler = js.index('nextImage.addEventListener("load"')
        latest_capture = js.index("var viewportState = image ? captureViewport() : null;", load_handler)
        error_handler = js.index('nextImage.addEventListener("error"', load_handler)
        source_assignment = js.index("nextImage.src = item.source;", error_handler)
        self.assertLess(load_handler, latest_capture)
        self.assertLess(latest_capture, error_handler)
        self.assertLess(error_handler, source_assignment)
        self.assertEqual(js.count("captureViewport()"), 3)
        self.assertEqual(js.count("restoreViewport(viewportState);"), 1)

    def test_image_viewer_stale_load_and_error_paths_keep_displayed_state_honest(self):
        js = (HERE / "static" / "app.js").read_text(encoding="utf-8")
        stale_guard = "cleaned || loadToken !== imageLoadToken || requestedIndex !== targetIndex"
        self.assertEqual(js.count(stale_guard), 2)
        self.assertIn("var requestedIndex = initialIndex;", js)
        self.assertIn("var displayedIndex = -1;", js)
        self.assertIn("displayedIndex = targetIndex;\n        requestedIndex = targetIndex;", js)
        self.assertIn("if (displayedIndex >= 0) {\n          requestedIndex = displayedIndex;\n        }", js)
        self.assertIn('return "No image displayed";', js)
        self.assertIn('updateDisplayedState("Loading item " + (targetIndex + 1) + ": " + item.title);', js)
        self.assertIn('updateDisplayedState("Could not load item " + (targetIndex + 1) + ": " + item.title);', js)
        self.assertIn('var headingIndex = displayedIndex >= 0 ? displayedIndex : requestedIndex;', js)
        self.assertIn("positionLabel.textContent = displayedPositionText()", js)
        self.assertIn("var disabled = image === null;", js)
        error_handler = js.index('nextImage.addEventListener("error"')
        source_assignment = js.index("nextImage.src = item.source;", error_handler)
        error_contract = js[error_handler:source_assignment]
        self.assertNotIn("canvas.replaceChild", error_contract)
        self.assertNotIn("canvas.appendChild", error_contract)
        self.assertNotIn("displayedIndex = targetIndex", error_contract)

    def test_image_viewer_preservation_is_scoped_to_one_open_item_set(self):
        js = (HERE / "static" / "app.js").read_text(encoding="utf-8")
        self.assertIn("var scale = 1;", js)
        self.assertIn("var initialIndex = Math.max(0, Math.min(items.length - 1, selectedIndex || 0));", js)
        self.assertIn("var requestedIndex = initialIndex;", js)
        self.assertIn("var displayedIndex = -1;", js)
        self.assertIn("showItem(requestedIndex, false);", js)
        self.assertEqual(js.count("showItem(requestedIndex, false);"), 1)

    def test_image_switch_focus_preserves_scroll_with_fallback(self):
        js = (HERE / "static" / "app.js").read_text(encoding="utf-8")
        self.assertIn("function focusPreservingViewport(element)", js)
        self.assertIn("var scrollLeft = viewport.scrollLeft;", js)
        self.assertIn("var scrollTop = viewport.scrollTop;", js)
        self.assertIn("element.focus({ preventScroll: true });", js)
        self.assertIn("catch (error) {\n        element.focus();\n      }", js)
        self.assertIn("viewport.scrollLeft = scrollLeft;", js)
        self.assertIn("viewport.scrollTop = scrollTop;", js)
        self.assertEqual(js.count("focusPreservingViewport(image);"), 2)
        self.assertNotIn("image.focus();", js)

    def test_image_switch_focus_reapplies_scroll_after_deferred_browser_adjustment(self):
        js = (HERE / "static" / "app.js").read_text(encoding="utf-8")
        self.assertIn("var focusRestoreFrame = null;", js)
        self.assertIn("var focusedImage = element;", js)
        self.assertIn("var focusedLoadToken = imageLoadToken;", js)
        self.assertIn("window.cancelAnimationFrame(focusRestoreFrame);", js)
        self.assertIn("focusRestoreFrame = window.requestAnimationFrame(function () {", js)
        self.assertIn(
            "if (cleaned || !dialog.open || image !== focusedImage || imageLoadToken !== focusedLoadToken)",
            js,
        )
        self.assertGreaterEqual(js.count("viewport.scrollLeft = scrollLeft;"), 2)
        self.assertGreaterEqual(js.count("viewport.scrollTop = scrollTop;"), 2)
        cleanup = js.index("function cleanup()")
        release_lock = js.index("releaseScrollLock();", cleanup)
        cancel_frame = js.index("window.cancelAnimationFrame(focusRestoreFrame);", cleanup)
        self.assertLess(cancel_frame, release_lock)

    def test_async_image_load_captures_pan_before_focus_restoration(self):
        js = (HERE / "static" / "app.js").read_text(encoding="utf-8")
        load_handler = js.index('nextImage.addEventListener("load"')
        capture = js.index("var viewportState = image ? captureViewport() : null;", load_handler)
        restore = js.index("restoreViewport(viewportState);", capture)
        focus = js.index("focusPreservingViewport(image);", restore)
        self.assertLess(capture, restore)
        self.assertLess(restore, focus)

    def test_image_viewer_pointer_drag_preserves_click_navigation_contract(self):
        js = (HERE / "static" / "app.js").read_text(encoding="utf-8")
        css = (HERE / "static" / "style.css").read_text(encoding="utf-8")
        for contract in (
            "var suppressNextImageClick = false;",
            "nextImage.draggable = false;",
            'nextImage.addEventListener("dragstart", function (event) { event.preventDefault(); });',
            "var pointerGesture = null;",
            "var pendingClickViewportState = null;",
            'nextImage.addEventListener("pointerdown", onPointerDown);',
            'nextImage.addEventListener("pointermove", onPointerMove);',
            'nextImage.addEventListener("pointerup", function (event) { onPointerEnd(event, false); });',
            'nextImage.addEventListener("pointercancel", function (event) { onPointerEnd(event, true); });',
            'nextImage.addEventListener("lostpointercapture", function (event) { onPointerEnd(event, true); });',
            "if (nextImage.setPointerCapture) {",
            "nextImage.setPointerCapture(event.pointerId);",
            "nextImage.releasePointerCapture(event.pointerId);",
            "deltaX * deltaX + deltaY * deltaY >= 36",
            "pointerGesture.dragging = true;",
            "viewportState: captureViewport(),",
            "var completedGesture = pointerGesture;",
            "pointerGesture = null;",
            "pendingClickViewportState = !cancelled && !completedGesture.dragging ? completedGesture.viewportState : null;",
            "viewport.scrollLeft = pointerGesture.startScrollLeft - deltaX;",
            "viewport.scrollTop = pointerGesture.startScrollTop - deltaY;",
            'nextImage.classList.add("is-dragging");',
            'nextImage.classList.remove("is-dragging");',
            'if (event.type === "click" && suppressNextImageClick) {',
            "event.stopPropagation();",
        ):
            self.assertIn(contract, js)
        self.assertIn("cursor: grab", css)
        self.assertIn("cursor: grabbing", css)
        self.assertIn("touch-action: none", css)
        self.assertIn("-webkit-user-drag: none", css)
        self.assertIn("click the displayed image, or drag it", js)

    def test_image_click_restores_pointerdown_viewport_before_switch(self):
        js = (HERE / "static" / "app.js").read_text(encoding="utf-8")
        click_handler = js.index("function showNextImage(event)")
        click_restore = js.index('if (event.type === "click" && pendingClickViewportState)', click_handler)
        restore = js.index("restoreViewport(pendingClickViewportState);", click_restore)
        discard = js.index("pendingClickViewportState = null;", restore)
        switch = js.index("showItem(requestedIndex + 1, true);", discard)
        self.assertLess(click_restore, restore)
        self.assertLess(restore, discard)
        self.assertLess(discard, switch)
        self.assertIn(
            "pendingClickViewportState = !cancelled && !completedGesture.dragging ? completedGesture.viewportState : null;",
            js,
        )
        self.assertIn(
            'if (event.type === "keydown") {\n          event.preventDefault();\n          pendingClickViewportState = null;',
            js,
        )

    def test_image_viewer_is_viewport_sized_and_image_scoped(self):
        js = (HERE / "static" / "app.js").read_text(encoding="utf-8")
        css = (HERE / "static" / "style.css").read_text(encoding="utf-8")
        self.assertIn("width: 96vw", css)
        self.assertIn("height: 94vh", css)
        self.assertNotIn("min(95vw, 1100px)", css)
        for selector in (".image-viewport", ".image-canvas", ".image-dialog img"):
            self.assertIn(selector, css)
        for behavior in (
            'document.body.style.overflow = "hidden"',
            "image.style.transform = \"scale(\" + scale",
            'viewport.addEventListener("wheel", onWheel, { passive: false })',
            "event.preventDefault();",
            'window.removeEventListener("resize", onResize)',
            'dialog.addEventListener("close", cleanup)',
            'node("button", "Zoom in"',
            'node("button", "Zoom out"',
            'node("button", "Fit / reset"',
            'scaleLabel.textContent = "Scale: "',
        ):
            self.assertIn(behavior, js)

    def test_image_viewer_scroll_lock_survives_rapid_reopen(self):
        js = (HERE / "static" / "app.js").read_text(encoding="utf-8")
        self.assertIn("var imageDialogLockCount = 0", js)
        self.assertIn("function acquireImageDialogLock()", js)
        self.assertIn("var releaseScrollLock = acquireImageDialogLock()", js)
        self.assertIn("var released = false", js)
        self.assertIn("if (imageDialogLockCount === 0)", js)
        self.assertIn("releaseScrollLock();", js)
        self.assertIn("imageDialogPreviousOverflow = null", js)
        self.assertNotIn("document.body.style.overflow = previousBodyOverflow", js)

    def test_assets_have_no_external_fetches_or_html_interpolation(self):
        js = (HERE / "static" / "app.js").read_text(encoding="utf-8")
        css = (HERE / "static" / "style.css").read_text(encoding="utf-8")
        self.assertNotIn("innerHTML", js)
        assets = (js + css).replace("http://www.w3.org/2000/svg", "")
        self.assertNotRegex(assets, r"https?://")
        for label in (
            "Latest published",
            "Earlier publication",
            "not approved or the project's next active checkpoint",
            "What you're looking at",
            "subject-context-purpose",
            "Generated descriptor snapshot",
            "Build/render provenance",
        ):
            self.assertIn(label, js)


if __name__ == "__main__":
    unittest.main()
