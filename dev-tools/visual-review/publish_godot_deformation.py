#!/usr/bin/env python3
"""Publish three screened static-replay Godot deformation captures."""

from __future__ import annotations

import argparse
import hashlib
from io import BytesIO
import json
import sys
import tempfile
from pathlib import Path
from typing import Any

from PIL import Image, ImageChops, ImageStat

# This file is also used as a directly executed script.  Make sibling imports
# deliberate for both that path and importlib-based tests.
VISUAL_REVIEW_ROOT = Path(__file__).resolve().parent
if str(VISUAL_REVIEW_ROOT) not in sys.path:
    sys.path.insert(0, str(VISUAL_REVIEW_ROOT))

import common
from common import ValidationError, canonical_json, validate_id
from publish import PublishError, publish_session


class GodotDeformationPublishError(RuntimeError):
    """A bounded, fail-closed deformation publication failure."""


REPORT_SCHEMA = "creature-kernel.disposable-godot-skeletal-pose-smoke.v1"
REPORT_BOUNDARY = "experiment_local_contact_driven_smooth_forearm_surface_deformation"
# These are the only claims this capture-only publisher screens.  Runtime
# render/collision coherence is not validated by this publisher.
REPORT_BASE_CLAIMS = [
    "host-local Skeleton3D/Skin pose binding",
    "host-local consumption of the shared structural pose recipe",
    "experiment-local semantic proxy contact and rigid-body response",
    "experiment-local contact-driven smooth forearm surface deformation, exact recovery, and static replay "
    "captures of runtime read-back states",
]
# The current experiment report may append this one claim.  It remains
# report-declared metadata only: this publisher neither requires nor validates
# coherence evidence, and never republishes the claim.
REPORT_OPTIONAL_CLAIM = "experiment-local paired runtime render-surface and rigid-collision read-back coherence"
# Keep the historical constant name as the four-claim screened base contract.
REPORT_CLAIMS = REPORT_BASE_CLAIMS
REPORT_SCOPE_FLAGS = {
    "physics_stepping": True,
    "animation": False,
    "contact": True,
    "deformation": True,
    "render_output": True,
    "adapter": False,
}
DEFORMATION_SURFACE_COLLISION_MODE = "rigid-selected-capsule-not-deformed"
DEFORMATION_DRIVE_KIND = "actual-contact-triggered-fixed-depth-contact-normal-projected-sleeve-falloff"
CAPTURE_NAMES = ("reference.png", "peak.png", "recovered.png")
CAPTURE_LABELS = ("reference", "peak", "recovered")
CAPTURE_WIDTH = 1536
CAPTURE_HEIGHT = 512
CAPTURE_MAX_BYTES = 8 * 1024 * 1024
# These are integrity floors/caps shared with the runner, not subjective
# visibility criteria. Ben's appraisal remains the visibility decision.
CAPTURE_MIN_UNIQUE_RGBA_PIXELS = 16
CAPTURE_MIN_NON_DOMINANT_PIXELS = 1024
CAPTURE_MIN_CHANGED_PIXELS = 256
CAPTURE_MIN_TOTAL_ABS_CHANNEL_DELTA = 4096
CAPTURE_MAX_CHANGED_PIXEL_FRACTION = 0.25
DEFAULT_REVIEW_ID = "godot-semantic-deformation-reference-peak-recovered-v4"
TITLE = "Godot edge-contact deformation - reference, peak, recovered"
DESCRIPTION = (
    "Capture-only visual comparison of report-declared runtime read-back states replayed in a separate static "
    "scene; the rigid collision proxy remains separate."
)
INSTRUCTIONS = (
    "Compare reference, peak, and recovered using the same fixed views and framing. "
    "At peak, look inside the hollow red ring for a small smooth depression at the sleeve's open edge; "
    "recovered should match reference. The ring marks the fixed falloff footprint, not live contact or "
    "deformation strength. This run exercises capsule end/edge contact, not a press into the middle of a closed "
    "fleshy surface. These are static replay captures of stored runtime mesh read-back states, not live contact "
    "rendering, and this standalone publisher screens capture integrity rather than revalidating the runtime "
    "experiment. Rigid collision remains undeformed. If the edge change is not readable, the result is inconclusive."
)
DEFORMATION_REPORT_ALIAS_KEYS = {
    "semantic_deformation_evidence",
    "deformation_evidence",
    "deformation_captures",
}
# Keep the contract names visible to callers that consume the smoke-runner
# vocabulary directly.
DEFORMATION_REPORT_CLAIMS = REPORT_CLAIMS
DEFORMATION_REPORT_FLAGS = REPORT_SCOPE_FLAGS
DEFORMATION_CAPTURE_NAMES = CAPTURE_NAMES
DEFORMATION_CAPTURE_LABELS = CAPTURE_LABELS
DEFORMATION_CAPTURE_WIDTH = CAPTURE_WIDTH
DEFORMATION_CAPTURE_HEIGHT = CAPTURE_HEIGHT
DEFORMATION_CAPTURE_MAX_BYTES = CAPTURE_MAX_BYTES


def _exact_equal(left: Any, right: Any) -> bool:
    """Compare JSON-shaped values without Python's bool/int equivalence."""
    if type(left) is not type(right):
        return False
    if isinstance(left, dict):
        return set(left) == set(right) and all(_exact_equal(left[key], right[key]) for key in left)
    if isinstance(left, list):
        return len(left) == len(right) and all(_exact_equal(a, b) for a, b in zip(left, right))
    return left == right


def _read_report(report_path: Path) -> tuple[dict[str, Any], bytes]:
    if report_path.is_symlink() or not report_path.is_file():
        raise GodotDeformationPublishError("Godot deformation report is missing or unsafe")
    try:
        if report_path.stat().st_size > common.MAX_JSON_BYTES:
            raise GodotDeformationPublishError("Godot deformation report exceeds the bounded JSON limit")
        report_bytes = report_path.read_bytes()
    except OSError as exc:
        raise GodotDeformationPublishError(f"Godot deformation report cannot be read: {exc}") from exc
    if len(report_bytes) > common.MAX_JSON_BYTES:
        raise GodotDeformationPublishError("Godot deformation report exceeds the bounded JSON limit")
    try:
        report = json.loads(
            report_bytes.decode("utf-8"),
            parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)),
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError, RecursionError) as exc:
        raise GodotDeformationPublishError(f"Godot deformation report is invalid JSON: {exc}") from exc
    if not isinstance(report, dict):
        raise GodotDeformationPublishError("Godot deformation report must be a JSON object")
    return report, report_bytes


def _validate_report(report: dict[str, Any]) -> list[dict[str, Any]]:
    if report.get("schema") != REPORT_SCHEMA or report.get("status") != "success":
        raise GodotDeformationPublishError("Godot deformation report schema or status is invalid")
    if report.get("boundary") != REPORT_BOUNDARY:
        raise GodotDeformationPublishError("Godot deformation report boundary is invalid")
    claims = report.get("claims")
    if not (
        _exact_equal(claims, REPORT_BASE_CLAIMS)
        or _exact_equal(claims, [*REPORT_BASE_CLAIMS, REPORT_OPTIONAL_CLAIM])
    ):
        raise GodotDeformationPublishError("Godot deformation report claims are not the exact screened deformation scope")
    scope_flags = report.get("scope_flags")
    if not _exact_equal(scope_flags, REPORT_SCOPE_FLAGS):
        raise GodotDeformationPublishError("Godot deformation report scope flags are not the exact deformation scope")
    if DEFORMATION_REPORT_ALIAS_KEYS.intersection(report):
        raise GodotDeformationPublishError("Godot deformation report contains unsupported deformation aliases")

    evidence = report.get("semantic_deformation")
    if not isinstance(evidence, dict) or evidence.get("boundary") != REPORT_BOUNDARY:
        raise GodotDeformationPublishError("Godot semantic deformation evidence boundary is invalid")
    surface = evidence.get("surface")
    if not isinstance(surface, dict) or surface.get("collision_mode") != DEFORMATION_SURFACE_COLLISION_MODE:
        raise GodotDeformationPublishError("Godot deformation report does not disclose the rigid collision boundary")
    drive = evidence.get("drive")
    if not isinstance(drive, dict) or drive.get("kind") != DEFORMATION_DRIVE_KIND:
        raise GodotDeformationPublishError("Godot deformation report does not use the fixed contact-driven deformation contract")
    captures = evidence.get("captures")
    if not isinstance(captures, list) or len(captures) != len(CAPTURE_NAMES):
        raise GodotDeformationPublishError("Godot deformation capture records are incomplete or reordered")
    capture_keys = {"label", "file_name", "width", "height", "sha256", "byte_count_decimal"}
    for index, (record, label, file_name) in enumerate(zip(captures, CAPTURE_LABELS, CAPTURE_NAMES)):
        if not isinstance(record, dict) or set(record) != capture_keys:
            raise GodotDeformationPublishError(f"Godot deformation capture record {index} is incomplete")
        if (
            record["label"] != label
            or record["file_name"] != file_name
            or type(record["width"]) is not int
            or record["width"] != CAPTURE_WIDTH
            or type(record["height"]) is not int
            or record["height"] != CAPTURE_HEIGHT
        ):
            raise GodotDeformationPublishError(f"Godot deformation capture record {index} identity or dimensions are invalid")
        if (
            not isinstance(record["sha256"], str)
            or len(record["sha256"]) != 64
            or any(character not in "0123456789abcdef" for character in record["sha256"])
            or not isinstance(record["byte_count_decimal"], str)
            or not record["byte_count_decimal"].isascii()
            or not record["byte_count_decimal"].isdigit()
            or record["byte_count_decimal"].startswith("0")
        ):
            raise GodotDeformationPublishError(f"Godot deformation capture record {index} integrity metadata is invalid")
    return captures


def _validate_png_dimensions(data: bytes, file_name: str) -> None:
    if len(data) > CAPTURE_MAX_BYTES:
        raise GodotDeformationPublishError(f"Godot deformation capture {file_name} exceeds the bounded byte limit")
    if len(data) < 33 or data[:8] != b"\x89PNG\r\n\x1a\n":
        raise GodotDeformationPublishError(f"Godot deformation capture {file_name} is not a PNG")
    if int.from_bytes(data[8:12], "big") != 13 or data[12:16] != b"IHDR":
        raise GodotDeformationPublishError(f"Godot deformation capture {file_name} does not begin with an IHDR chunk")
    width = int.from_bytes(data[16:20], "big")
    height = int.from_bytes(data[20:24], "big")
    if (width, height) != (CAPTURE_WIDTH, CAPTURE_HEIGHT):
        raise GodotDeformationPublishError(
            f"Godot deformation capture {file_name} dimensions are {width}x{height}, "
            f"expected {CAPTURE_WIDTH}x{CAPTURE_HEIGHT}"
        )


def _read_captures(capture_directory: Path) -> dict[str, bytes]:
    if capture_directory.is_symlink() or not capture_directory.is_dir():
        raise GodotDeformationPublishError("Godot deformation capture directory is missing or unsafe")
    try:
        entries = list(capture_directory.iterdir())
    except OSError as exc:
        raise GodotDeformationPublishError(f"Godot deformation captures cannot be enumerated: {exc}") from exc
    if {entry.name for entry in entries} != set(CAPTURE_NAMES):
        raise GodotDeformationPublishError("Godot deformation capture directory does not contain exactly the three required PNGs")
    captures: dict[str, bytes] = {}
    for file_name in CAPTURE_NAMES:
        path = capture_directory / file_name
        if path.is_symlink() or not path.is_file():
            raise GodotDeformationPublishError(f"Godot deformation capture {file_name} is not a regular file")
        try:
            if path.stat().st_size > CAPTURE_MAX_BYTES:
                raise GodotDeformationPublishError(
                    f"Godot deformation capture {file_name} exceeds the bounded byte limit"
                )
            data = path.read_bytes()
        except GodotDeformationPublishError:
            raise
        except OSError as exc:
            raise GodotDeformationPublishError(f"Godot deformation capture {file_name} cannot be read: {exc}") from exc
        _validate_png_dimensions(data, file_name)
        captures[file_name] = data
    return captures


def _decode_and_validate_capture_content(captures: dict[str, bytes]) -> None:
    """Decode all captures independently and validate their rendered pixels."""
    decoded: dict[str, bytes] = {}
    total_pixels = CAPTURE_WIDTH * CAPTURE_HEIGHT
    for file_name in CAPTURE_NAMES:
        data = captures[file_name]
        try:
            with Image.open(BytesIO(data)) as image:
                if image.format != "PNG" or image.size != (CAPTURE_WIDTH, CAPTURE_HEIGHT):
                    raise GodotDeformationPublishError(
                        f"Godot deformation capture {file_name} Pillow decode does not match the PNG contract"
                    )
                image.load()
                rgba = image.convert("RGBA")
                rgba.load()
                extrema = rgba.getextrema()
                if all(low == high for low, high in extrema) or extrema[3] == (0, 0):
                    raise GodotDeformationPublishError(
                        f"Godot deformation capture {file_name} is blank or uniformly rendered"
                    )
                pixels = rgba.tobytes()
                frequencies = rgba.getcolors(total_pixels)
                if frequencies is None:
                    raise GodotDeformationPublishError(
                        f"Godot deformation capture {file_name} has too many distinct RGBA colors"
                    )
                non_dominant_pixels = total_pixels - max(
                    (count for count, _ in frequencies), default=0
                )
                if (
                    len(frequencies) < CAPTURE_MIN_UNIQUE_RGBA_PIXELS
                    or non_dominant_pixels < CAPTURE_MIN_NON_DOMINANT_PIXELS
                ):
                    raise GodotDeformationPublishError(
                        f"Godot deformation capture {file_name} lacks bounded rendered content "
                        f"(unique_rgba={len(frequencies)}, non_dominant_pixels={non_dominant_pixels})"
                    )
                decoded[file_name] = pixels
        except GodotDeformationPublishError:
            raise
        except (OSError, ValueError, SyntaxError) as exc:
            raise GodotDeformationPublishError(
                f"Godot deformation capture {file_name} cannot be decoded by Pillow: {exc}"
            ) from exc

    reference = decoded[CAPTURE_NAMES[0]]
    recovered = decoded[CAPTURE_NAMES[2]]
    if reference != recovered:
        raise GodotDeformationPublishError("Godot deformation reference and recovered pixels are not exactly equal")

    peak = decoded[CAPTURE_NAMES[1]]
    difference = ImageChops.difference(
        Image.frombytes("RGBA", (CAPTURE_WIDTH, CAPTURE_HEIGHT), peak),
        Image.frombytes("RGBA", (CAPTURE_WIDTH, CAPTURE_HEIGHT), reference),
    )
    difference_frequencies = difference.getcolors(total_pixels)
    if difference_frequencies is None:
        raise GodotDeformationPublishError("Godot deformation capture difference has too many distinct RGBA colors")
    unchanged_pixels = next(
        (count for count, colour in difference_frequencies if colour == (0, 0, 0, 0)),
        0,
    )
    changed_pixels = total_pixels - unchanged_pixels
    # Pillow exposes ImageStat sums as floats, but the bounded 8-bit channel
    # total is exactly integral at this image size.
    total_abs_channel_delta = int(sum(ImageStat.Stat(difference).sum))
    difference_fraction = changed_pixels / total_pixels
    if (
        changed_pixels < CAPTURE_MIN_CHANGED_PIXELS
        or total_abs_channel_delta < CAPTURE_MIN_TOTAL_ABS_CHANNEL_DELTA
    ):
        raise GodotDeformationPublishError(
            "Godot deformation peak-vs-reference pixel difference is below the meaningful minimum "
            f"(changed_pixels={changed_pixels}, total_abs_channel_delta={total_abs_channel_delta})"
        )
    if difference_fraction > CAPTURE_MAX_CHANGED_PIXEL_FRACTION:
        raise GodotDeformationPublishError(
            "Godot deformation peak-vs-reference pixel difference exceeds the bounded maximum "
            f"({difference_fraction:.6f} > {CAPTURE_MAX_CHANGED_PIXEL_FRACTION:.6f})"
        )


def _build_manifest(
    report: dict[str, Any],
    report_bytes: bytes,
    capture_directory: Path,
    capture_records: list[dict[str, Any]],
) -> dict[str, Any]:
    # Do not copy report claims into the manifest.  This publisher screens the
    # four capture claims only and must not attest to unvalidated coherence.
    report_sha256 = hashlib.sha256(report_bytes).hexdigest()
    items: list[dict[str, Any]] = []
    for label, file_name, record in zip(CAPTURE_LABELS, CAPTURE_NAMES, capture_records):
        item_id = label
        items.append(
            {
                "id": item_id,
                "title": label.capitalize(),
                "source": str((capture_directory / file_name).absolute()),
                "description": {
                    "reference": "Undeformed reference state.",
                    "peak": "Contact-driven peak state; inspect the small edge depression inside the red ring.",
                    "recovered": "Released state; inspect full recovery against reference.",
                }[label],
                "metadata": {
                    "state": label,
                    "file_name": file_name,
                    "width": record["width"],
                    "height": record["height"],
                    "byte_count_decimal": record["byte_count_decimal"],
                    "sha256": record["sha256"],
                    "report_sha256": report_sha256,
                    "report_boundary": report["boundary"],
                    "collision_mode": DEFORMATION_SURFACE_COLLISION_MODE,
                },
            }
        )
    return {
        "schema_version": 1,
        "title": TITLE,
        "description": DESCRIPTION,
        "instructions": INSTRUCTIONS,
        "kind": "image",
        "subject_context": {
            "authored_summary": {
                "text": "Three fixed-view static replays supplied from one report-declared forearm deformation run."
            },
            "descriptor_snapshot": {
                "report_sha256": report_sha256,
                "report_boundary": report["boundary"],
                "scope_flags": report["scope_flags"],
                "capture_names": list(CAPTURE_NAMES),
                "capture_width": CAPTURE_WIDTH,
                "capture_height": CAPTURE_HEIGHT,
            },
            "provenance": {"source": "screened report metadata and static replay capture directory"},
        },
        "groups": [
            {
                "id": "deformation_states",
                "title": "Reference, peak, and recovered states",
                "selection_mode": "none",
                "items": items,
            }
        ],
    }


def publish_godot_deformation(
    reviews_root: Path,
    report_path: Path,
    capture_directory: Path,
    *,
    review_id: str | None = None,
) -> dict[str, Any]:
    """Validate one report/capture pair and publish its three image states."""
    try:
        stable_id = validate_id(review_id or DEFAULT_REVIEW_ID, "review id")
        report, report_bytes = _read_report(Path(report_path).absolute())
        capture_records = _validate_report(report)
        capture_directory = Path(capture_directory).absolute()
        captures = _read_captures(capture_directory)
        for record, file_name in zip(capture_records, CAPTURE_NAMES):
            data = captures[file_name]
            if record["byte_count_decimal"] != str(len(data)) or record["sha256"] != hashlib.sha256(data).hexdigest():
                raise GodotDeformationPublishError(
                    f"Godot deformation capture {file_name} does not match report byte count or sha256"
                )
        _decode_and_validate_capture_content(captures)
        review = _build_manifest(report, report_bytes, capture_directory, capture_records)
        review["id"] = stable_id
        expected_sources = {
            item["id"]: {
                "bytes": int(item["metadata"]["byte_count_decimal"]),
                "sha256": item["metadata"]["sha256"],
            }
            for group in review["groups"]
            for item in group["items"]
        }
        with tempfile.TemporaryDirectory(prefix="ck-godot-deformation-review-") as temporary:
            manifest_path = Path(temporary) / "manifest.json"
            manifest_path.write_text(canonical_json(review), encoding="utf-8")
            try:
                summary = publish_session(
                    Path(reviews_root),
                    manifest_path,
                    expected_sources=expected_sources,
                )
            except (ValidationError, PublishError, OSError) as exc:
                raise GodotDeformationPublishError(f"could not publish Godot deformation review: {exc}") from exc
        return {**summary, "kind": "image"}
    except GodotDeformationPublishError:
        raise
    except (OSError, ValueError, TypeError) as exc:
        raise GodotDeformationPublishError(str(exc)) from exc


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, type=Path, help="existing reviews root")
    parser.add_argument("--report", required=True, type=Path, help="Godot deformation report JSON")
    parser.add_argument(
        "--captures",
        "--capture-directory",
        dest="capture_directory",
        required=True,
        type=Path,
        help="directory containing the three captures",
    )
    parser.add_argument("--id", dest="review_id", help="stable review/session ID")
    return parser


def main(argv: list[str] | None = None) -> int:
    try:
        args = _parser().parse_args(argv)
        summary = publish_godot_deformation(
            args.root,
            args.report,
            args.capture_directory,
            review_id=args.review_id,
        )
    except GodotDeformationPublishError as exc:
        print(f"publish failed: {exc}", file=sys.stderr)
        return 2
    print(canonical_json(summary), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
