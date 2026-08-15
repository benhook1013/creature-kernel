from __future__ import annotations

import copy
import importlib.util
import json
import os
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.request import urlopen


HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))


def load_module(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, HERE / filename)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


import common
serve = load_module("provisional_form_serve", "serve.py")
publisher = load_module("provisional_form_publisher", "publish_provisional_form.py")


class ProvisionalFormPublicationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.directory = Path(self.temp.name)
        self.root = self.directory / "reviews"
        self.root.mkdir()
        self.input = self.directory / "body.json"
        self.input.write_text("{}", encoding="utf-8")
        address = {"namespace": "main", "anchors": [], "kind": "part", "role": "pelvis"}
        self.payload = {
            "format": common.PROVISIONAL_FORM_FORMAT,
            "operation": common.PROVISIONAL_FORM_OPERATION,
            "status": "success",
            "stage": common.PROVISIONAL_FORM_STAGE,
            "processing_complete": True,
            "diagnostics_complete": True,
            "diagnostics": [],
            "source": {"document": "fixture", "namespace": "main", "resource_profile_id": common.PROVISIONAL_FORM_RESOURCE_PROFILE},
            "reference_scale": {"parent": {**address, "role": "pelvis"}, "child": {**address, "role": "torso"}, "axis_delta": [0, 1, 0], "squared_length": 1, "source": "exact-containment-edge"},
            "variants": [],
            "limitations": "Provisional display-only geometry descriptors; no production geometry or Readiness 3.",
        }
        for variant_id in common.PROVISIONAL_FORM_VARIANT_IDS:
            descriptor = {
                "descriptor_kind": "display-only-form-descriptor",
                "address": address,
                "parent": None,
                "placement_source": "authored-root",
                "reference_point": [0, 0, 0],
                "profile_id": variant_id,
                "source": common.PROVISIONAL_FORM_PROVENANCE,
                "provenance": {"source": common.PROVISIONAL_FORM_PROVENANCE, "resource_profile_id": common.PROVISIONAL_FORM_RESOURCE_PROFILE},
                "shape": {"name": "ellipsoid", "center": [0, 0, 0], "axis_extents_permille": [1000, 900, 800]},
            }
            torso = copy.deepcopy(descriptor)
            torso["address"] = {**address, "role": "torso"}
            torso["parent"] = {**address, "role": "pelvis"}
            torso["placement_source"] = "authored-containment"
            torso["reference_point"] = [0, 1, 0]
            torso["shape"]["center"] = [0, 1, 0]
            self.payload["variants"].append({"id": variant_id, "profile_id": variant_id, "provenance": {"source": common.PROVISIONAL_FORM_PROVENANCE, "resource_profile_id": common.PROVISIONAL_FORM_RESOURCE_PROFILE}, "descriptors": [descriptor, torso]})

    def tearDown(self) -> None:
        self.temp.cleanup()

    def fake_binary(self, body: str, name: str = "fake-kernel") -> Path:
        binary = self.directory / name
        binary.write_text("#!/usr/bin/env python3\n" + body, encoding="utf-8")
        binary.chmod(0o755)
        return binary

    def publish_with(self, binary: Path, **kwargs: object) -> Path:
        summary = publisher.publish_provisional_form(self.root, self.input, creature_kernel=binary, **kwargs)
        return Path(summary["session"])

    def test_success_publishes_distinct_immutable_form_session_and_route(self) -> None:
        binary = self.fake_binary("import json, sys\nsys.stdout.write(" + repr(json.dumps(self.payload)) + ")\n")
        session = self.publish_with(binary, review_id="form-review", title="Filled form")
        review = json.loads((session / "review.json").read_text(encoding="utf-8"))
        self.assertEqual(review["kind"], "provisional-form")
        self.assertEqual(review["provisional_form"], self.payload)
        self.assertEqual(list((session / "assets").iterdir()), [])
        self.payload["variants"][0]["descriptors"][0]["shape"]["center"][0] = 9
        self.assertEqual(json.loads((session / "review.json").read_text())["provisional_form"]["variants"][0]["descriptors"][0]["shape"]["center"], [0, 0, 0])
        server = serve.create_server(self.root, 0)
        thread = threading.Thread(target=server.serve_forever)
        thread.start()
        try:
            with urlopen(f"http://127.0.0.1:{server.server_port}/api/reviews/form-review") as response:
                body = json.load(response)
            self.assertEqual(body["review"]["kind"], "provisional-form")
            self.assertEqual(len(body["review"]["provisional_form"]["variants"]), 4)
        finally:
            server.shutdown(); thread.join(); server.server_close()

    def test_unknown_and_malformed_payloads_fail_closed(self) -> None:
        cases = [
            {"unknown": True},
            {"variants": list(reversed(self.payload["variants"]))},
            {"shape": {"name": "mesh"}},
            {"reference_scale": {"axis_delta": [0, 1, 0], "squared_length": 2}},
            {"point": [1.5, 0, 0]},
            {"permille": 0},
        ]
        for index, change in enumerate(cases):
            payload = copy.deepcopy(self.payload)
            if "unknown" in change:
                payload["unexpected"] = True
            elif "variants" in change:
                payload["variants"] = change["variants"]
            elif "shape" in change:
                payload["variants"][0]["descriptors"][0]["shape"] = {"name": "mesh"}
            elif "reference_scale" in change:
                payload["reference_scale"]["squared_length"] = 2
            elif "point" in change:
                payload["variants"][0]["descriptors"][0]["reference_point"] = [1.5, 0, 0]
            else:
                payload["variants"][0]["descriptors"][0]["shape"]["axis_extents_permille"][0] = 0
            binary = self.fake_binary("import json, sys\nsys.stdout.write(" + repr(json.dumps(payload)) + ")\n", f"bad-{index}")
            with self.assertRaises(publisher.ProvisionalFormPublishError):
                self.publish_with(binary, review_id=f"bad-form-{index}")
            self.assertFalse((self.root / f"bad-form-{index}").exists())

    def test_nonzero_output_bound_timeout_and_collision_are_bounded(self) -> None:
        noisy = self.fake_binary(f"import sys\nsys.stdout.write('x' * {publisher.MAX_STDOUT_BYTES + 1})\n", "noisy")
        with self.assertRaises(publisher.ProvisionalFormPublishError):
            self.publish_with(noisy, review_id="noisy")
        slow = self.fake_binary("import time\ntime.sleep(30)\n", "slow")
        with patch.object(publisher, "INSPECTION_TIMEOUT_SECONDS", 0.05):
            with self.assertRaisesRegex(publisher.ProvisionalFormPublishError, "timed out"):
                self.publish_with(slow, review_id="slow")
        failed = self.fake_binary("import sys\nsys.stderr.write('failed')\nsys.exit(9)\n", "failed")
        with self.assertRaises(publisher.ProvisionalFormPublishError):
            self.publish_with(failed, review_id="failed")
        valid = self.fake_binary("import json, sys\nsys.stdout.write(" + repr(json.dumps(self.payload)) + ")\n", "valid")
        self.publish_with(valid, review_id="collision")
        with self.assertRaisesRegex(publisher.ProvisionalFormPublishError, "already exists"):
            self.publish_with(valid, review_id="collision")

    def test_payload_rejects_root_role_shape_scale_and_exact_integer_violations(self) -> None:
        cases = []
        root_violation = copy.deepcopy(self.payload)
        root_violation["variants"][0]["descriptors"][1]["placement_source"] = "authored-root"
        root_violation["variants"][0]["descriptors"][1]["parent"] = None
        cases.append(root_violation)
        unknown_role = copy.deepcopy(self.payload)
        unknown_role["variants"][0]["descriptors"][0]["address"]["role"] = "mystery"
        cases.append(unknown_role)
        role_shape = copy.deepcopy(self.payload)
        role_shape["variants"][0]["descriptors"][0]["shape"]["name"] = "capsule"
        cases.append(role_shape)
        drift = copy.deepcopy(self.payload)
        drift["variants"][1]["descriptors"][0]["shape"]["name"] = "capsule"
        cases.append(drift)
        binary64 = copy.deepcopy(self.payload)
        binary64["variants"][0]["descriptors"][0]["reference_point"][0] = (1 << 53) + 1
        cases.append(binary64)
        non_edge = copy.deepcopy(self.payload)
        head = copy.deepcopy(non_edge["variants"][0]["descriptors"][1])
        head["address"] = {**head["address"], "role": "head"}
        head["parent"] = {**head["parent"], "role": "torso"}
        head["reference_point"] = [0, 2, 0]
        head["shape"]["center"] = [0, 2, 0]
        for variant in non_edge["variants"]:
            variant_head = copy.deepcopy(head)
            variant_head["profile_id"] = variant["id"]
            variant_head["provenance"] = copy.deepcopy(variant["provenance"])
            variant["descriptors"] = [variant_head, variant["descriptors"][0], variant["descriptors"][1]]
        non_edge["reference_scale"] = {
            "parent": {"namespace": "main", "anchors": [], "kind": "part", "role": "pelvis"},
            "child": {"namespace": "main", "anchors": [], "kind": "part", "role": "head"},
            "axis_delta": [0, 2, 0],
            "squared_length": 4,
            "source": "exact-containment-edge",
        }
        cases.append(non_edge)
        for index, payload in enumerate(cases):
            binary = self.fake_binary("import json, sys\nsys.stdout.write(" + repr(json.dumps(payload)) + ")\n", f"semantic-{index}")
            with self.assertRaises(publisher.ProvisionalFormPublishError):
                self.publish_with(binary, review_id=f"semantic-{index}")

    def test_input_is_copied_from_validated_identity_before_cli(self) -> None:
        capture = self.directory / "captured-input.bin"
        binary = self.fake_binary(
            "import json, pathlib, sys\n"
            f"pathlib.Path({str(capture)!r}).write_bytes(pathlib.Path(sys.argv[-1]).read_bytes())\n"
            "sys.stdout.write(" + repr(json.dumps(self.payload)) + ")\n",
            "identity-kernel",
        )
        self.input.write_bytes(b'{"identity":"original"}')
        self.publish_with(binary, review_id="identity-copy")
        self.assertEqual(capture.read_bytes(), self.input.read_bytes())
        self.assertNotEqual(capture.read_bytes(), b"{}")

    def test_forked_descendant_is_killed_on_timeout(self) -> None:
        pid_path = self.directory / "descendant.pid"
        binary = self.fake_binary(
            "import pathlib, subprocess, sys, time\n"
            f"child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)'])\n"
            f"pathlib.Path({str(pid_path)!r}).write_text(str(child.pid))\n"
            "time.sleep(30)\n",
            "fork-kernel",
        )
        with patch.object(publisher, "INSPECTION_TIMEOUT_SECONDS", 0.05):
            with self.assertRaises(publisher.ProvisionalFormPublishError):
                self.publish_with(binary, review_id="forked-timeout")
        child_pid = int(pid_path.read_text())
        deadline = time.monotonic() + 2
        while time.monotonic() < deadline:
            try:
                os.kill(child_pid, 0)
            except ProcessLookupError:
                break
            time.sleep(0.02)
        else:
            self.fail("forked descendant survived bounded process-group cleanup")

    def test_output_caps_are_exactly_bounded_before_buffering(self) -> None:
        self.assertEqual(publisher.MAX_STDOUT_BYTES, 256 * 1024)
        self.assertEqual(publisher.MAX_STDERR_BYTES, 64 * 1024)
        for label, limit in (("stdout", publisher.MAX_STDOUT_BYTES), ("stderr", publisher.MAX_STDERR_BYTES)):
            binary = self.fake_binary(
                "import sys\n"
                + (f"sys.stdout.write('x' * {limit + 1})\n" if label == "stdout" else f"sys.stderr.write('x' * {limit + 1})\n"),
                f"bound-{label}",
            )
            with self.assertRaisesRegex(publisher.ProvisionalFormPublishError, label):
                self.publish_with(binary, review_id=f"bound-{label}")

    def test_checked_in_browser_dispatch_is_anchor_aware_and_shared_scale(self) -> None:
        app = (HERE / "static" / "app.js").read_text(encoding="utf-8")
        self.assertIn("function renderProvisionalForm", app)
        self.assertIn("provisionalFormPreviewSection(payload)", app)
        self.assertIn("payload.variants.forEach", app)
        self.assertIn("formBounds(payload)", app)
        self.assertIn("function formDescriptorQualifier", app)
        self.assertIn('anchors.indexOf("left")', app)
        self.assertIn('anchors.indexOf("right")', app)
        self.assertIn('return "#a78bfa"', app)
        self.assertIn('return "#f4a261"', app)
        self.assertIn('"Front · x / y"', app)
        self.assertIn('"Side · z / y"', app)
        self.assertIn('"Top · x / z"', app)


if __name__ == "__main__":
    unittest.main()
