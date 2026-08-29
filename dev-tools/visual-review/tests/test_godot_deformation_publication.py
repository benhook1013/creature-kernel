from __future__ import annotations

import hashlib
import importlib.util
import json
import struct
import sys
import tempfile
import unittest
import zlib
from pathlib import Path


HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))


def load_module(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, HERE / filename)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


publisher = load_module("godot_deformation_publisher", "publish_godot_deformation.py")


class GodotDeformationPublicationTests(unittest.TestCase):
    def setUp(self) -> None:
        # The inherited publisher uses renameat2(RENAME_NOREPLACE), which is
        # not implemented by the Windows-mounted temporary directory exposed
        # through this environment. Keep the fixture inside this worktree.
        self.temp = tempfile.TemporaryDirectory(
            prefix="godot-deformation-publication-",
            dir=HERE,
        )
        self.directory = Path(self.temp.name)
        self.reviews = self.directory / "reviews"
        self.reviews.mkdir()
        self.report = self.directory / "report.json"
        self.captures = self.directory / "captures"
        self.captures.mkdir()
        self._write_fixture()

    def tearDown(self) -> None:
        self.temp.cleanup()

    @staticmethod
    def _chunk(kind: bytes, payload: bytes) -> bytes:
        return (
            struct.pack(">I", len(payload))
            + kind
            + payload
            + struct.pack(">I", zlib.crc32(kind + payload) & 0xFFFFFFFF)
        )

    @classmethod
    def _png(
        cls,
        colour: tuple[int, int, int],
        *,
        peak_colour: tuple[int, int, int] | None = None,
        peak_box: tuple[int, int, int, int] | None = None,
        uniform: bool = False,
    ) -> bytes:
        width, height = publisher.CAPTURE_WIDTH, publisher.CAPTURE_HEIGHT
        raw_rows = []
        for y in range(height):
            shade = 0 if uniform else y % publisher.CAPTURE_MIN_UNIQUE_RGBA_PIXELS
            row_colour = bytes(tuple(min(255, value + shade) for value in colour))
            row = bytearray(row_colour * width)
            if peak_colour is not None and peak_box is not None:
                left, top, right, bottom = peak_box
                if top <= y < bottom:
                    peak_row_colour = bytes(peak_colour)
                    if not uniform:
                        peak_row_colour = bytes(tuple(min(255, value + shade) for value in peak_colour))
                    row[left * 3 : right * 3] = peak_row_colour * (right - left)
            raw_rows.append(b"\x00" + bytes(row))
        raw = b"".join(raw_rows)
        return (
            b"\x89PNG\r\n\x1a\n"
            + cls._chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
            + cls._chunk(b"IDAT", zlib.compress(raw, 9))
            + cls._chunk(b"IEND", b"")
        )

    def _write_fixture(self) -> None:
        records = []
        for label, file_name, colour in zip(
            publisher.CAPTURE_LABELS,
            publisher.CAPTURE_NAMES,
            ((80, 90, 100), (80, 90, 100), (80, 90, 100)),
        ):
            data = self._png(
                colour,
                peak_colour=(220, 40, 30) if label == "peak" else None,
                peak_box=(128, 128, 256, 256) if label == "peak" else None,
            )
            (self.captures / file_name).write_bytes(data)
            records.append(
                {
                    "label": label,
                    "file_name": file_name,
                    "width": publisher.CAPTURE_WIDTH,
                    "height": publisher.CAPTURE_HEIGHT,
                    "sha256": hashlib.sha256(data).hexdigest(),
                    "byte_count_decimal": str(len(data)),
                }
            )
        report = {
            "schema": publisher.REPORT_SCHEMA,
            "status": "success",
            "boundary": publisher.REPORT_BOUNDARY,
            "claims": publisher.REPORT_BASE_CLAIMS,
            "scope_flags": publisher.REPORT_SCOPE_FLAGS,
            "semantic_deformation": {
                "boundary": publisher.REPORT_BOUNDARY,
                "surface": {"collision_mode": publisher.DEFORMATION_SURFACE_COLLISION_MODE},
                "drive": {"kind": publisher.DEFORMATION_DRIVE_KIND},
                "captures": records,
            },
        }
        self.report.write_text(json.dumps(report, sort_keys=True) + "\n", encoding="utf-8")

    def _replace_capture(self, file_name: str, data: bytes) -> None:
        (self.captures / file_name).write_bytes(data)
        report = json.loads(self.report.read_text(encoding="utf-8"))
        record = next(
            record
            for record in report["semantic_deformation"]["captures"]
            if record["file_name"] == file_name
        )
        record["sha256"] = hashlib.sha256(data).hexdigest()
        record["byte_count_decimal"] = str(len(data))
        self.report.write_text(json.dumps(report, sort_keys=True) + "\n", encoding="utf-8")

    def test_four_claim_report_publishes_one_stable_three_state_group(self) -> None:
        summary = publisher.publish_godot_deformation(self.reviews, self.report, self.captures)
        session = Path(summary["session"])
        review = json.loads((session / "review.json").read_text(encoding="utf-8"))
        self.assertEqual(summary["id"], publisher.DEFAULT_REVIEW_ID)
        self.assertEqual(review["kind"], "image")
        self.assertEqual(len(review["groups"]), 1)
        group = review["groups"][0]
        self.assertEqual(group["selection_mode"], "none")
        self.assertEqual([item["id"] for item in group["items"]], ["reference", "peak", "recovered"])
        self.assertEqual(
            {path.name for path in (session / "assets").iterdir()},
            {"reference.png", "peak.png", "recovered.png"},
        )
        self.assertIn("same fixed views", review["instructions"])
        self.assertIn("small smooth depression at the sleeve's open edge", review["instructions"])
        self.assertIn("hollow red ring", review["instructions"])
        self.assertIn("recovered should match reference", review["instructions"])
        self.assertIn("fixed falloff footprint", review["instructions"])
        self.assertIn("not a press into the middle of a closed fleshy surface", review["instructions"])
        self.assertIn("static replay captures", review["instructions"])
        self.assertIn("rather than revalidating the runtime experiment", review["instructions"])
        self.assertIn("Rigid collision remains undeformed", review["instructions"])
        self.assertIn("inconclusive", review["instructions"])

    def test_current_five_claim_report_publishes_without_coherence_attestation(self) -> None:
        report = json.loads(self.report.read_text(encoding="utf-8"))
        report["claims"] = [*publisher.REPORT_BASE_CLAIMS, publisher.REPORT_OPTIONAL_CLAIM]
        self.report.write_text(json.dumps(report, sort_keys=True) + "\n", encoding="utf-8")

        summary = publisher.publish_godot_deformation(
            self.reviews,
            self.report,
            self.captures,
            review_id="five-claim-report",
        )
        review = json.loads((Path(summary["session"]) / "review.json").read_text(encoding="utf-8"))
        published = json.dumps(review, sort_keys=True)
        self.assertNotIn("claims", review)
        self.assertNotIn(publisher.REPORT_OPTIONAL_CLAIM, published)

    def test_different_extra_claim_is_rejected(self) -> None:
        report = json.loads(self.report.read_text(encoding="utf-8"))
        report["claims"] = [*publisher.REPORT_BASE_CLAIMS, "unvalidated extra claim"]
        self.report.write_text(json.dumps(report, sort_keys=True) + "\n", encoding="utf-8")

        with self.assertRaisesRegex(publisher.GodotDeformationPublishError, "exact screened deformation scope"):
            publisher.publish_godot_deformation(
                self.reviews,
                self.report,
                self.captures,
                review_id="different-extra-claim",
            )
        self.assertFalse((self.reviews / "different-extra-claim").exists())

    def test_blank_capture_is_rejected(self) -> None:
        self._replace_capture(
            "reference.png",
            self._png((0, 0, 0), uniform=True),
        )
        with self.assertRaisesRegex(publisher.GodotDeformationPublishError, "blank or uniformly rendered"):
            publisher.publish_godot_deformation(self.reviews, self.report, self.captures, review_id="blank-capture")
        self.assertFalse((self.reviews / "blank-capture").exists())

    def test_identical_peak_and_reference_are_rejected(self) -> None:
        self._replace_capture("peak.png", (self.captures / "reference.png").read_bytes())
        with self.assertRaisesRegex(publisher.GodotDeformationPublishError, "reference and recovered pixels|peak-vs-reference"):
            publisher.publish_godot_deformation(self.reviews, self.report, self.captures, review_id="identical-captures")
        self.assertFalse((self.reviews / "identical-captures").exists())

    def test_trivial_peak_difference_is_rejected(self) -> None:
        self._replace_capture(
            "peak.png",
            self._png((80, 90, 100), peak_colour=(220, 40, 30), peak_box=(0, 0, 1, 1)),
        )
        with self.assertRaisesRegex(publisher.GodotDeformationPublishError, "below the meaningful minimum"):
            publisher.publish_godot_deformation(self.reviews, self.report, self.captures, review_id="trivial-difference")
        self.assertFalse((self.reviews / "trivial-difference").exists())

    def test_peak_difference_above_bound_is_rejected(self) -> None:
        self._replace_capture(
            "peak.png",
            self._png(
                (80, 90, 100),
                peak_colour=(220, 40, 30),
                peak_box=(0, 0, publisher.CAPTURE_WIDTH, publisher.CAPTURE_HEIGHT),
            ),
        )
        with self.assertRaisesRegex(publisher.GodotDeformationPublishError, "exceeds the bounded maximum"):
            publisher.publish_godot_deformation(self.reviews, self.report, self.captures, review_id="bounded-difference")
        self.assertFalse((self.reviews / "bounded-difference").exists())

    def test_drive_contract_is_required(self) -> None:
        report = json.loads(self.report.read_text(encoding="utf-8"))
        report["semantic_deformation"]["drive"]["kind"] = "actual-contact-driven-inward-falloff"
        self.report.write_text(json.dumps(report, sort_keys=True) + "\n", encoding="utf-8")
        with self.assertRaisesRegex(publisher.GodotDeformationPublishError, "fixed contact-driven deformation contract"):
            publisher.publish_godot_deformation(self.reviews, self.report, self.captures, review_id="wrong-drive-contract")
        self.assertFalse((self.reviews / "wrong-drive-contract").exists())

    def test_tamper_and_scope_changes_fail_closed_without_session(self) -> None:
        cases = (
            ("boundary", lambda report: report.update(boundary="wrong-boundary")),
            ("scope", lambda report: report["scope_flags"].update(deformation=False)),
            ("capture-order", lambda report: report["semantic_deformation"].update(captures=list(reversed(report["semantic_deformation"]["captures"]))),),
            ("capture-hash", lambda report: report["semantic_deformation"]["captures"][1].update(sha256="0" * 64)),
        )
        original = self.report.read_text(encoding="utf-8")
        for name, mutate in cases:
            with self.subTest(name=name):
                report = json.loads(original)
                mutate(report)
                self.report.write_text(json.dumps(report, sort_keys=True) + "\n", encoding="utf-8")
                with self.assertRaises(publisher.GodotDeformationPublishError):
                    publisher.publish_godot_deformation(self.reviews, self.report, self.captures, review_id=f"tampered-{name}")
                self.assertFalse((self.reviews / f"tampered-{name}").exists())
                self.report.write_text(original, encoding="utf-8")

    def test_capture_dimensions_and_bytes_are_checked_before_publish(self) -> None:
        peak = self.captures / "peak.png"
        data = bytearray(peak.read_bytes())
        data[16:20] = struct.pack(">I", publisher.CAPTURE_WIDTH - 1)
        peak.write_bytes(data)
        with self.assertRaisesRegex(
            publisher.GodotDeformationPublishError,
            r"Godot deformation capture peak\.png dimensions are 1535x512, expected 1536x512",
        ):
            publisher.publish_godot_deformation(self.reviews, self.report, self.captures, review_id="bad-dimensions")
        self.assertFalse((self.reviews / "bad-dimensions").exists())

        self._write_fixture()
        peak.write_bytes(peak.read_bytes() + b"tamper")
        with self.assertRaises(publisher.GodotDeformationPublishError):
            publisher.publish_godot_deformation(self.reviews, self.report, self.captures, review_id="bad-bytes")
        self.assertFalse((self.reviews / "bad-bytes").exists())

    def test_existing_stable_session_is_not_overwritten(self) -> None:
        publisher.publish_godot_deformation(self.reviews, self.report, self.captures)
        with self.assertRaises(publisher.GodotDeformationPublishError):
            publisher.publish_godot_deformation(self.reviews, self.report, self.captures)


if __name__ == "__main__":
    unittest.main()
