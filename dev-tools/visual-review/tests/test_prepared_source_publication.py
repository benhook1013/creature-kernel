from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import threading
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
serve = load_module("prepared_source_serve", "serve.py")
publish_prepared_source = load_module(
    "visual_review_publish_prepared_source", "publish_prepared_source.py"
)


class PreparedSourcePublicationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.directory = Path(self.temp.name)
        self.root = self.directory / "reviews"
        self.root.mkdir()
        self.input = self.directory / "body.json"
        self.input.write_text("{}", encoding="utf-8")
        self.payload = {
            "format": common.PREPARED_SOURCE_FORMAT,
            "operation": "inspect-prepared-source",
            "stage": "source-preparation",
            "status": "success",
            "processing_complete": True,
            "diagnostics_complete": True,
            "diagnostics": [],
            "graph": {
                "parts": [{"address": {"kind": "part", "role": "root"}}],
                "joints": [],
                "sockets": [],
                "attachments": [],
                "landmarks": [],
                "dimensions": [],
                "frames": [],
            },
            "prepared": {
                "basis": {
                    "length_unit": "metre",
                    "handedness": "right",
                    "up": "+y",
                    "forward": "+z",
                    "source_for_canonical": ["+x", "+y", "+z"],
                },
                "counts": {
                    "parts": 1,
                    "joints": 0,
                    "sockets": 0,
                    "attachments": 0,
                    "landmarks": 0,
                    "dimensions": 0,
                    "frames": 0,
                },
                "numeric_values": [
                    {
                        "group": "parts",
                        "semantic_key": "part:root",
                        "field": "placement",
                        "component": component,
                        "display_value": "0",
                        "binary64_bits": "0000000000000000",
                    }
                    for component in (
                        "translation.x", "translation.y", "translation.z",
                        "rotation.x", "rotation.y", "rotation.z", "rotation.w",
                    )
                ],
            },
        }

    def tearDown(self) -> None:
        self.temp.cleanup()

    def fake_binary(self, body: str, name: str = "fake-kernel") -> Path:
        binary = self.directory / name
        binary.write_text("#!/usr/bin/env python3\n" + body, encoding="utf-8")
        binary.chmod(0o755)
        return binary

    def publish_with(self, binary: Path, **kwargs: object) -> Path:
        result = publish_prepared_source.publish_prepared_source(
            self.root, self.input, creature_kernel=binary, **kwargs
        )
        return Path(result["session"])

    def test_valid_envelope_uses_existing_structure_session_and_api(self) -> None:
        binary = self.fake_binary(
            "import json, sys\n"
            f"sys.stdout.write({json.dumps(json.dumps(self.payload))})\n"
        )
        session = self.publish_with(binary, review_id="prepared-review", title="Prepared")
        review = json.loads((session / "review.json").read_text(encoding="utf-8"))
        self.assertEqual(review["kind"], "structure")
        self.assertEqual(review["structure"], self.payload)

        server = serve.create_server(self.root, 0)
        thread = threading.Thread(target=server.serve_forever)
        thread.start()
        try:
            with urlopen(
                f"http://127.0.0.1:{server.server_port}/api/reviews/prepared-review",
                timeout=3,
            ) as response:
                body = json.loads(response.read())
            self.assertEqual(body["review"]["structure"]["prepared"], self.payload["prepared"])
            self.assertIsNone(body["response"])
        finally:
            server.shutdown()
            thread.join()
            server.server_close()

    def test_invalid_envelope_fields_are_rejected(self) -> None:
        invalid = (
            {"format": "wrong"},
            dict(self.payload, operation="inspect-structure"),
            dict(self.payload, stage="structural-validation"),
            dict(self.payload, prepared={}),
            dict(self.payload, prepared=dict(self.payload["prepared"], basis=[])),
            dict(
                self.payload,
                prepared=dict(
                    self.payload["prepared"],
                    basis=dict(self.payload["prepared"]["basis"], source_for_canonical=["+x"]),
                ),
            ),
            dict(
                self.payload,
                prepared=dict(self.payload["prepared"], counts={"parts": -1}),
            ),
            dict(
                self.payload,
                prepared=dict(
                    self.payload["prepared"],
                    counts={"parts": 1, "joints": 0, "sockets": 0, "attachments": 0},
                ),
            ),
            dict(
                self.payload,
                prepared=dict(self.payload["prepared"], numeric_values=[1]),
            ),
            dict(
                self.payload,
                prepared=dict(
                    self.payload["prepared"],
                    numeric_values=[
                        dict(self.payload["prepared"]["numeric_values"][0], binary64_bits="0x0000000000000000")
                    ],
                ),
            ),
        )
        for index, payload in enumerate(invalid):
            with self.subTest(index=index):
                with self.assertRaises(common.ValidationError):
                    common._validate_prepared_source_envelope(payload, "payload")

    def test_status_stage_diagnostics_and_cardinality_mismatches_are_rejected(self) -> None:
        diagnostic = {"code": "ck.source.invalid"}
        stage_mismatch = dict(
            self.payload,
            status="input-failure",
            stage="source-preparation",
            processing_complete=False,
            diagnostics=[diagnostic],
            primary_diagnostic=diagnostic,
        )
        missing_primary = dict(
            self.payload,
            status="invalid-source",
            diagnostics=[diagnostic],
            processing_complete=True,
        )
        missing_primary.pop("graph")
        missing_primary.pop("prepared")
        wrong_primary = dict(missing_primary, primary_diagnostic={"code": "other"})
        count_mismatch = dict(
            self.payload,
            prepared=dict(
                self.payload["prepared"],
                counts=dict(self.payload["prepared"]["counts"], parts=0),
            ),
        )
        truncated_rows = dict(
            self.payload,
            prepared=dict(
                self.payload["prepared"],
                numeric_values=self.payload["prepared"]["numeric_values"][:-1],
            ),
        )
        bad_graph = dict(
            self.payload,
            graph=dict(self.payload["graph"], joints={}),
        )
        for index, payload in enumerate(
            (stage_mismatch, missing_primary, wrong_primary, count_mismatch, truncated_rows, bad_graph)
        ):
            with self.subTest(index=index):
                with self.assertRaises(common.ValidationError):
                    common._validate_prepared_source_envelope(payload, "payload")

    def test_command_failure_timeout_and_output_bound_do_not_publish(self) -> None:
        failed = self.fake_binary("import sys\nsys.exit(7)\n", "failed-kernel")
        with self.assertRaisesRegex(
            publish_prepared_source.PreparedSourcePublishError, "no JSON"
        ):
            self.publish_with(failed, review_id="failed")

        slow = self.fake_binary("import time\ntime.sleep(30)\n", "slow-kernel")
        with patch.object(publish_prepared_source, "INSPECTION_TIMEOUT_SECONDS", 0.05):
            with self.assertRaisesRegex(
                publish_prepared_source.PreparedSourcePublishError, "timed out"
            ):
                self.publish_with(slow, review_id="timed-out")

        noisy = self.fake_binary(
            f"import sys\nsys.stdout.write('x' * {publish_prepared_source.MAX_STDOUT_BYTES + 1})\n",
            "noisy-kernel",
        )
        with self.assertRaises(publish_prepared_source.PreparedSourcePublishError):
            self.publish_with(noisy, review_id="oversized")
        self.assertFalse((self.root / "failed").exists())
        self.assertFalse((self.root / "timed-out").exists())
        self.assertFalse((self.root / "oversized").exists())

    def test_admission_failure_stage_is_publishable(self) -> None:
        payload = dict(
            self.payload,
            stage="admission",
            status="invalid-source",
            processing_complete=False,
            diagnostics=[{"code": "ck.source.invalid"}],
            primary_diagnostic={"code": "ck.source.invalid"},
        )
        payload.pop("graph")
        payload.pop("prepared")
        binary = self.fake_binary(
            "import json, sys\n"
            f"sys.stdout.write({json.dumps(json.dumps(payload))})\n"
            "sys.exit(1)\n",
            "admission-failure-kernel",
        )
        session = self.publish_with(binary, review_id="admission-failure")
        review = json.loads((session / "review.json").read_text(encoding="utf-8"))
        self.assertEqual(review["structure"]["stage"], "admission")
        self.assertEqual(review["structure"]["status"], "invalid-source")


if __name__ == "__main__":
    unittest.main()
