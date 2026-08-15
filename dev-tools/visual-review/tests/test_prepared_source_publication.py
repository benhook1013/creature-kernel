from __future__ import annotations

import copy
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
    @staticmethod
    def address(kind: str, role: str, anchors: tuple[str, ...] = ()) -> dict[str, object]:
        return {
            "namespace": "main",
            "anchors": list(anchors),
            "kind": kind,
            "role": role,
        }

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
                "modules": [],
                "parts": [{
                    "address": self.address("part", "root"),
                    "containment": {"root": True},
                }],
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
            "preview": {
                "format": common.EXACT_PLACEMENT_PREVIEW_FORMAT,
                "status": "available",
                "basis": {
                    "length_unit": "metre",
                    "handedness": "right",
                    "up": "+y",
                    "forward": "+z",
                    "source_for_canonical": ["+x", "+y", "+z"],
                },
                "parts": [{
                    "address": self.address("part", "root"),
                    "position": [0, 0, 0],
                    "parent": None,
                    "placement_source": "authored-root",
                }],
                "containment_edges": [],
                "joint_edges": [],
                "attachments": [],
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

    def attached_preview_fixture(self) -> tuple[dict[str, object], dict[str, object]]:
        graph = copy.deepcopy(self.payload["graph"])
        root = self.address("part", "root")
        attached_root = self.address("part", "tail_root", ("tail",))
        host_socket = self.address("socket", "host")
        mating_socket = self.address("socket", "mating", ("tail",))
        attachment_address = self.address("attachment", "tail_attach", ("tail",))
        graph["parts"].append({"address": attached_root, "containment": {"parent": root}})
        graph["modules"] = [{
            "declaration": {
                "document": "tail_module",
                "namespace": "tail_module",
                "anchors": [],
                "role": "tail_decl",
            },
            "module": "tail_module",
            "root_role": "tail_root",
            "instance_anchor": "tail",
            "presence": "present",
            "optional": True,
            "attachment_required": True,
            "root": attached_root,
        }]
        graph["sockets"] = [
            {"address": host_socket, "owner": root},
            {"address": mating_socket, "owner": attached_root},
        ]
        graph["attachments"] = [{
            "address": attachment_address,
            "host": host_socket,
            "mating": mating_socket,
        }]
        preview = copy.deepcopy(self.payload["preview"])
        preview["parts"].append({
            "address": attached_root,
            "position": [0, 0, 0],
            "parent": root,
            "placement_source": "authored-attachment",
        })
        preview["containment_edges"] = [{"parent": root, "child": attached_root}]
        preview["attachments"] = [{
            "attachment": attachment_address,
            "root": attached_root,
            "host_socket": host_socket,
            "mating_socket": mating_socket,
            "offset": [0, 0, 0],
            "authored_root_local": [0, 0, 0],
            "derived_root_local": [0, 0, 0],
        }]
        return graph, preview

    def test_valid_envelope_uses_existing_structure_session_and_api(self) -> None:
        binary = self.fake_binary(
            "import json, sys\n"
            f"sys.stdout.write({json.dumps(json.dumps(self.payload))})\n"
        )
        session = self.publish_with(binary, review_id="prepared-review", title="Prepared")
        review = json.loads((session / "review.json").read_text(encoding="utf-8"))
        self.assertEqual(review["kind"], "structure")
        self.assertEqual(review["structure"], self.payload)

        self.payload["preview"]["parts"][0]["position"][0] = 99
        reread = json.loads((session / "review.json").read_text(encoding="utf-8"))
        self.assertEqual(reread["structure"]["preview"]["parts"][0]["position"], [0, 0, 0])

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

    def test_legacy_no_preview_is_accepted(self) -> None:
        payload = dict(self.payload)
        payload.pop("preview")
        common._validate_prepared_source_envelope(payload, "payload")

    def test_unavailable_preview_has_no_partial_spatial_fields(self) -> None:
        unavailable = dict(
            self.payload,
            preview={
                "format": common.EXACT_PLACEMENT_PREVIEW_FORMAT,
                "status": "unavailable",
                "diagnostic": {
                    "code": common.EXACT_PLACEMENT_PREVIEW_UNAVAILABLE_CODE,
                    "message": "exact placement could not be resolved",
                },
            },
        )
        common._validate_prepared_source_envelope(unavailable, "payload")
        for partial in (
            dict(unavailable["preview"], parts=[]),
            dict(unavailable["preview"], basis=self.payload["preview"]["basis"]),
        ):
            with self.assertRaises(common.ValidationError):
                common._validate_prepared_source_envelope(
                    dict(unavailable, preview=partial), "payload"
                )

    def test_preview_translation_boundaries_cover_position_and_attachment_fields(self) -> None:
        boundaries = (
            ((1 << 53) + 1, False),
            ((1 << 53) + 2, True),
            (common.SIGNED_I64_MIN, True),
            ((1 << 63), False),
        )
        for component, accepted in boundaries:
            with self.subTest(position=component):
                preview = copy.deepcopy(self.payload["preview"])
                preview["parts"][0]["position"] = [component, 0, 0]
                if accepted:
                    common._validate_exact_placement_preview(
                        preview, "preview", self.payload["graph"]
                    )
                else:
                    with self.assertRaises(common.ValidationError):
                        common._validate_exact_placement_preview(
                            preview, "preview", self.payload["graph"]
                        )

        graph, base_preview = self.attached_preview_fixture()
        for field in ("offset", "authored_root_local", "derived_root_local"):
            for component, accepted in boundaries:
                with self.subTest(attachment_field=field, component=component):
                    preview = copy.deepcopy(base_preview)
                    preview["attachments"][0][field] = [component, 0, 0]
                    if accepted:
                        common._validate_exact_placement_preview(preview, "preview", graph)
                    else:
                        with self.assertRaises(common.ValidationError):
                            common._validate_exact_placement_preview(preview, "preview", graph)

    def test_preview_relationships_address_shape_basis_and_surrogates_are_rejected(self) -> None:
        graph, valid = self.attached_preview_fixture()
        common._validate_exact_placement_preview(valid, "preview", graph)

        for mutation in (
            lambda preview: preview["parts"][1].update(parent=None),
            lambda preview: preview["containment_edges"].__setitem__(
                0, {"parent": preview["parts"][1]["address"], "child": preview["parts"][0]["address"]}
            ),
            lambda preview: preview["parts"][1].update(placement_source="authored-root"),
            lambda preview: preview["attachments"][0].update(root=preview["parts"][0]["address"]),
            lambda preview: preview["attachments"][0].update(
                host_socket=preview["attachments"][0]["mating_socket"]
            ),
            lambda preview: preview["parts"][0].update(
                address={"namespace": "main", "anchors": [], "kind": "part"}
            ),
            lambda preview: preview["parts"][0]["address"].update(extra="reject"),
        ):
            with self.subTest(mutation=mutation):
                candidate = copy.deepcopy(valid)
                mutation(candidate)
                with self.assertRaises(common.ValidationError):
                    common._validate_exact_placement_preview(candidate, "preview", graph)

        joint_graph = copy.deepcopy(graph)
        joint_graph["joints"] = [{
            "address": self.address("joint", "tail_joint", ("tail",)),
            "proximal": self.address("part", "root"),
            "distal": self.address("part", "tail_root", ("tail",)),
        }]
        joint_preview = copy.deepcopy(valid)
        joint_preview["joint_edges"] = [{
            "joint": joint_graph["joints"][0]["address"],
            "proximal": self.address("part", "root"),
            "distal": self.address("part", "tail_root", ("tail",)),
        }]
        common._validate_exact_placement_preview(joint_preview, "preview", joint_graph)
        joint_preview["joint_edges"][0]["proximal"] = self.address(
            "part", "tail_root", ("tail",)
        )
        with self.assertRaises(common.ValidationError):
            common._validate_exact_placement_preview(joint_preview, "preview", joint_graph)

        mismatched_basis = dict(valid["basis"], up="-y")
        with self.assertRaises(common.ValidationError):
            common._validate_exact_placement_preview(
                valid, "preview", graph, mismatched_basis
            )

        unavailable = {
            "format": common.EXACT_PLACEMENT_PREVIEW_FORMAT,
            "status": "unavailable",
            "diagnostic": {
                "code": common.EXACT_PLACEMENT_PREVIEW_UNAVAILABLE_CODE,
                "message": "\ud800",
            },
        }
        with self.assertRaises(common.ValidationError):
            common._validate_prepared_source_envelope(
                dict(self.payload, preview=unavailable), "payload"
            )

    def test_preview_shape_basis_counts_coordinates_refs_duplicates_and_unknowns_rejected(self) -> None:
        valid = self.payload["preview"]
        malformed = (
            dict(valid, format="wrong"),
            dict(valid, status="pending"),
            dict(valid, basis=dict(valid["basis"], up="+z")),
            dict(valid, parts=[]),
            dict(
                valid,
                parts=[dict(valid["parts"][0], position=[0, 0])],
            ),
            dict(
                valid,
                parts=[dict(valid["parts"][0], position=[0, False, 0])],
            ),
            dict(
                valid,
                parts=[dict(valid["parts"][0], parent=self.address("part", "missing"))],
            ),
            dict(
                valid,
                containment_edges=[
                    {"parent": self.address("part", "root"),
                     "child": self.address("part", "root")},
                ],
            ),
            dict(valid, unexpected=True),
            dict(
                valid,
                parts=[dict(valid["parts"][0], unexpected=True)],
            ),
        )
        for index, preview in enumerate(malformed):
            with self.subTest(index=index):
                with self.assertRaises(common.ValidationError):
                    common._validate_prepared_source_envelope(
                        dict(self.payload, preview=preview), "payload"
                    )

        unavailable = {
            "format": common.EXACT_PLACEMENT_PREVIEW_FORMAT,
            "status": "unavailable",
            "diagnostic": {
                "code": common.EXACT_PLACEMENT_PREVIEW_UNAVAILABLE_CODE,
                "message": "exact placement could not be resolved",
            },
        }
        for invalid in (
            dict(unavailable, status="available"),
            dict(unavailable, unexpected=True),
            dict(unavailable, diagnostic=dict(unavailable["diagnostic"], extra=True)),
            dict(unavailable, diagnostic={"code": "other", "message": "bad"}),
            dict(unavailable, diagnostic={"code": common.EXACT_PLACEMENT_PREVIEW_UNAVAILABLE_CODE}),
        ):
            with self.subTest(unavailable=invalid):
                with self.assertRaises(common.ValidationError):
                    common._validate_prepared_source_envelope(
                        dict(self.payload, preview=invalid), "payload"
                    )

        graph = copy.deepcopy(self.payload["graph"])
        preview = copy.deepcopy(valid)
        for role in ("child", "grandchild"):
            address = self.address("part", role)
            parent = self.address("part", "root" if role == "child" else "child")
            graph["parts"].append({"address": address, "containment": {"parent": parent}})
            preview["parts"].append({
                "address": address,
                "position": [0, 0, 0],
                "parent": parent,
                "placement_source": "authored-containment",
            })
        preview["containment_edges"] = [
            {"parent": valid["parts"][0]["address"], "child": preview["parts"][1]["address"]},
            {"parent": valid["parts"][0]["address"], "child": preview["parts"][1]["address"]},
        ]
        with self.assertRaises(common.ValidationError):
            common._validate_exact_placement_preview(preview, "preview", graph)

        preview["containment_edges"][1] = {
            "parent": preview["parts"][1]["address"],
            "child": preview["parts"][2]["address"],
        }
        preview["parts"][2]["address"] = preview["parts"][1]["address"]
        with self.assertRaises(common.ValidationError):
            common._validate_exact_placement_preview(preview, "preview", graph)

        joint_graph = copy.deepcopy(self.payload["graph"])
        joint_graph["joints"] = [
            {
                "address": self.address("joint", "first"),
                "proximal": self.address("part", "root"),
                "distal": self.address("part", "root"),
            },
            {
                "address": self.address("joint", "second"),
                "proximal": self.address("part", "root"),
                "distal": self.address("part", "root"),
            },
        ]
        joint_preview = copy.deepcopy(valid)
        joint_preview["joint_edges"] = [
            {
                "joint": joint_graph["joints"][0]["address"],
                "proximal": valid["parts"][0]["address"],
                "distal": valid["parts"][0]["address"],
            },
            {
                "joint": joint_graph["joints"][0]["address"],
                "proximal": valid["parts"][0]["address"],
                "distal": valid["parts"][0]["address"],
            },
        ]
        with self.assertRaises(common.ValidationError):
            common._validate_exact_placement_preview(joint_preview, "preview", joint_graph)

        attachment_graph = copy.deepcopy(self.payload["graph"])
        attachment_graph["sockets"] = [
            {"address": self.address("socket", "host"), "owner": self.address("part", "root")},
            {"address": self.address("socket", "mating"), "owner": self.address("part", "root")},
        ]
        attachment_graph["attachments"] = [
            {
                "address": self.address("attachment", "first"),
                "host": self.address("socket", "host"),
                "mating": self.address("socket", "mating"),
            },
            {
                "address": self.address("attachment", "second"),
                "host": self.address("socket", "host"),
                "mating": self.address("socket", "mating"),
            },
        ]
        attachment_preview = copy.deepcopy(valid)
        attachment = {
            "attachment": attachment_graph["attachments"][0]["address"],
            "root": valid["parts"][0]["address"],
            "host_socket": attachment_graph["sockets"][0]["address"],
            "mating_socket": attachment_graph["sockets"][1]["address"],
            "offset": [0, 0, 0],
            "authored_root_local": [0, 0, 0],
            "derived_root_local": [0, 0, 0],
        }
        attachment_preview["attachments"] = [attachment, copy.deepcopy(attachment)]
        with self.assertRaises(common.ValidationError):
            common._validate_exact_placement_preview(
                attachment_preview, "preview", attachment_graph
            )

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
        payload.pop("preview")
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
