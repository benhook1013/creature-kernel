from __future__ import annotations

import copy
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("surface_preview", ROOT / "surface_preview.py")
assert SPEC and SPEC.loader
surface_preview = importlib.util.module_from_spec(SPEC)
sys.modules["surface_preview"] = surface_preview
SPEC.loader.exec_module(surface_preview)


def address(role: str, anchors: list[str] | None = None) -> dict[str, object]:
    return {"namespace": "main", "anchors": anchors or [], "kind": "part", "role": role}


def make_payload() -> dict[str, object]:
    def descriptor(role: str, point: list[int], parent: dict[str, object] | None, shape: dict[str, object], anchors: list[str] | None = None) -> dict[str, object]:
        return {"descriptor_kind": "display-only-form-descriptor", "address": address(role, anchors), "parent": parent, "placement_source": "authored-root" if parent is None else "authored-containment", "reference_point": point, "profile_id": "neutral-v0", "source": "profile-derived-display", "provenance": {"source": "profile-derived-display", "resource_profile_id": "ck.resource.body.r2"}, "shape": shape}
    pelvis = address("pelvis")
    descriptors = [
        descriptor("pelvis", [0, 0, 0], None, {"name": "ellipsoid", "center": [0, 0, 0], "axis_extents_permille": [1700, 1200, 900]}),
        descriptor("torso", [0, 1, 0], pelvis, {"name": "ellipsoid", "center": [0, 1, 0], "axis_extents_permille": [1650, 1200, 900]}),
        # Keep the synthetic body connected: the torso top is y=2.2 and this
        # head bottom is y=2.1, leaving a small analytic overlap.
        descriptor("head", [0, 3, 0], address("torso"), {"name": "ellipsoid", "center": [0, 3, 0], "axis_extents_permille": [1000, 900, 900]}),
        descriptor("upper_arm", [-1, 2, 0], address("torso"), {"name": "capsule", "from": [-1, 2, 0], "to": [-2, 2, 0], "radius_permille": 220}, ["left"]),
        descriptor("forearm", [-2, 2, 0], address("upper_arm", ["left"]), {"name": "capsule", "from": [-2, 2, 0], "to": [-3, 2, 0], "radius_permille": 190}, ["left"]),
        descriptor("hand", [-3, 2, 0], address("forearm", ["left"]), {"name": "ellipsoid", "center": [-3, 2, 0], "axis_extents_permille": [450, 400, 350]}, ["left"]),
    ]
    descriptors.sort(key=lambda item: (item["address"]["namespace"], tuple(item["address"]["anchors"]), item["address"]["kind"], item["address"]["role"]))
    variants = []
    for variant_id in surface_preview.VARIANT_IDS:
        current = copy.deepcopy(descriptors)
        for item in current:
            item["profile_id"] = variant_id
            item["provenance"]["resource_profile_id"] = "ck.resource.body.r2"
        variants.append({"id": variant_id, "profile_id": variant_id, "provenance": {"source": "profile-derived-display", "resource_profile_id": "ck.resource.body.r2"}, "descriptors": current})
    payload = {"format": surface_preview.SOURCE_FORMAT, "operation": "inspect-provisional-form", "status": "success", "stage": "provisional-form", "processing_complete": True, "diagnostics_complete": True, "diagnostics": [], "source": {"document": "test", "namespace": "main", "resource_profile_id": "ck.resource.body.r2"}, "reference_scale": {"parent": pelvis, "child": address("torso"), "axis_delta": [0, 1, 0], "squared_length": 1, "source": "exact-containment-edge"}, "variants": variants, "limitations": "Provisional display-only geometry descriptors; no production geometry or Readiness 3."}
    return payload


class SurfacePreviewTests(unittest.TestCase):
    def test_validation_preserves_four_variants_and_full_keys(self) -> None:
        form = surface_preview.validate_envelope(make_payload())
        self.assertEqual([x[0] for x in form.variants], list(surface_preview.VARIANT_IDS))
        self.assertIn(("main", ("left",), "part", "hand"), {x.key for x in form.variants[0][1]})

    def test_rejects_wrong_order_and_unknown_envelope_fields(self) -> None:
        payload = make_payload(); payload["variants"] = list(reversed(payload["variants"]))
        with self.assertRaises(surface_preview.PreviewError): surface_preview.validate_envelope(payload)
        payload = make_payload(); payload["extra"] = True
        with self.assertRaises(surface_preview.PreviewError): surface_preview.validate_envelope(payload)

    def test_output_is_deterministic_and_has_exact_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); input_path = root / "input.json"; input_path.write_bytes(surface_preview._canonical(make_payload()))
            first = root / "first"; second = root / "second"
            surface_preview.generate(input_path, first, samples=24, padding=0.5)
            surface_preview.generate(input_path, second, samples=24, padding=0.5)
            first_files = sorted(x.relative_to(first).as_posix() for x in first.rglob("*") if x.is_file())
            self.assertEqual(len(first_files), 17)
            self.assertEqual(first_files, sorted(x.relative_to(second).as_posix() for x in second.rglob("*") if x.is_file()))
            for name in first_files:
                self.assertEqual((first / name).read_bytes(), (second / name).read_bytes(), name)
            manifest = json.loads((first / "surface-preview-manifest.json").read_text())
            self.assertEqual(manifest["status"], "success")
            self.assertEqual(manifest["source_format"], surface_preview.SOURCE_FORMAT)
            self.assertEqual([x["id"] for x in manifest["variants"]], list(surface_preview.VARIANT_IDS))
            self.assertTrue(all(len(x["inventory"]) == 4 for x in manifest["variants"]))


if __name__ == "__main__":
    unittest.main()
