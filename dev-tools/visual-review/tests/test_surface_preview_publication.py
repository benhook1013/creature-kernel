from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import os
import struct
import sys
import tempfile
import textwrap
import unittest
import zlib
from pathlib import Path
from unittest.mock import patch


HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))


def load_module(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, HERE / filename)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


import common
publisher = load_module("surface_preview_publisher", "publish_surface_preview.py")


class SurfacePreviewPublicationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.directory = Path(self.temp.name)
        self.root = self.directory / "reviews"
        self.root.mkdir()
        self.input = self.directory / "body.json"
        self.input.write_text("{}", encoding="utf-8")

    def tearDown(self) -> None:
        self.temp.cleanup()

    @staticmethod
    def _chunk(kind: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(data, zlib.crc32(kind)) & 0xFFFFFFFF)

    @classmethod
    def _png(cls, *, include_idat: bool = True, invalid_idat: bool = False, unknown_chunk: bool = False) -> bytes:
        ihdr = cls._chunk(b"IHDR", struct.pack(">IIBBBBB", 32, 24, 8, 2, 0, 0, 0))
        raw = b"".join(b"\x00" + b"\x00" * (32 * 3) for _ in range(24))
        compressed = b"not-a-zlib-stream" if invalid_idat else zlib.compress(raw)
        idat = cls._chunk(b"IDAT", compressed) if include_idat else b""
        extra = cls._chunk(b"ABCD", b"unknown") if unknown_chunk else b""
        return b"\x89PNG\r\n\x1a\n" + ihdr + extra + idat + cls._chunk(b"IEND", b"")

    def _producer(self) -> Path:
        path = self.directory / "producer"
        path.write_text("#!/usr/bin/env python3\nprint('{}')\n", encoding="utf-8")
        path.chmod(0o755)
        return path

    def _generator(self, *, mode: str = "success") -> Path:
        path = self.directory / f"generator-{mode}.py"
        png_bytes = self._png()
        if mode == "png-truncated":
            png_bytes = png_bytes[:-1]
        elif mode == "png-crc":
            damaged = bytearray(png_bytes)
            damaged[-1] ^= 1
            png_bytes = bytes(damaged)
        elif mode == "png-no-idat":
            png_bytes = self._png(include_idat=False)
        elif mode == "png-invalid-idat":
            png_bytes = self._png(invalid_idat=True)
        elif mode == "png-unknown-critical":
            png_bytes = self._png(unknown_chunk=True)
        path.write_text(textwrap.dedent(f"""
            #!/usr/bin/env python3
            import hashlib, json, pathlib, struct, sys, time
            args = dict(zip(sys.argv[1::2], sys.argv[2::2]))
            out = pathlib.Path(args["--output"])
            source_hash = hashlib.sha256(pathlib.Path(args["--input"]).read_bytes()).hexdigest()
            if {mode!r} == "source-mismatch": source_hash = "0" * 64
            if out.exists(): raise RuntimeError("output must not already exist")
            if {mode!r} == "timeout":
                time.sleep(60)
            out.mkdir(parents=True, exist_ok=True)
            variants = []
            ids = {list(common.PROVISIONAL_FORM_VARIANT_IDS)!r}
            for variant_id in ids:
                directory = out / variant_id
                directory.mkdir()
                png = directory / "composite.png"
                png.write_bytes({png_bytes!r})
                files = [
                    ("ply", directory / "surface.ply", b"ply\\n"),
                    ("semantic-sidecar", directory / "semantic.json", b"{{}}"),
                    ("metrics", directory / "metrics.json", b"{{}}"),
                    ("neutral-composite-png", png, None),
                ]
                inventory = []
                for kind, file, value in files:
                    if value is not None: file.write_bytes(value)
                    data = file.read_bytes()
                    item = {{"kind": kind, "path": file.relative_to(out).as_posix(), "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}}
                    if {mode!r} == "hash" and kind == "metrics": item["sha256"] = "0" * 64
                    if kind == "neutral-composite-png": item.update({{"width": 32, "height": 24, "views": ["front", "side", "three-quarter"], "mode": "RGB"}})
                    inventory.append(item)
                variants.append({{"id": variant_id, "profile_id": ("wrong" if {mode!r} == "profile-mismatch" and not variants else variant_id), "inventory": inventory}})
            if {mode!r} == "bad-count": variants.pop()
            if {mode!r} == "unlisted": (out / "unlisted.bin").write_bytes(b"x")
            if {mode!r} == "symlink": (out / "escape").symlink_to(out / ids[0] / "surface.ply")
            (out / "surface-preview-manifest.json").write_text(json.dumps({{"format": {publisher.SURFACE_PREVIEW_FORMAT!r}, "status": "success", "source_format": {common.PROVISIONAL_FORM_FORMAT!r}, "source": {{"format": {common.PROVISIONAL_FORM_FORMAT!r}, "sha256": source_hash, "document": "fixture", "namespace": "main", "resource_profile_id": "ck.resource.body.r2", "reference_scale": {{}}}}, "generator": {{"samples_per_axis": 72, "padding": 0.75, "smooth_union": {{"operator": "polynomial_cubic_smooth_min", "k": 0.12, "fold_order": "full_address_key_ascending"}}, "field_primitives": ["ellipsoid", "capsule", "linear-radius-tapered-segment"], "boundary": "disposable exploratory visual proof; not production geometry, SDF, collision, rig, topology, or Readiness evidence"}}, "variants": variants}}))
        """), encoding="utf-8")
        path.chmod(0o755)
        return path

    def _payload(self) -> dict[str, object]:
        return {"format": common.PROVISIONAL_FORM_FORMAT}

    def test_success_stubs_both_executables_and_publishes_only_pngs(self) -> None:
        with patch.object(publisher, "_parse_inspection", return_value=self._payload()):
            result = publisher.publish_surface_preview(
                self.root,
                self.input,
                creature_kernel=self._producer(),
                generator=self._generator(),
                review_id="surface-test",
            )
        session = Path(result["session"])
        self.assertEqual(result["variants"], 4)
        self.assertEqual(sorted(p.name for p in (session / "assets").iterdir()), sorted(f"{v}.png" for v in common.PROVISIONAL_FORM_VARIANT_IDS))
        review = json.loads((session / "review.json").read_text(encoding="utf-8"))
        self.assertIn("subject_context", review)
        self.assertEqual(review["groups"][0]["selection_mode"], "none")

    def test_malformed_count_and_unlisted_output_publish_nothing(self) -> None:
        for index, mode in enumerate(("bad-count", "unlisted", "symlink", "hash", "source-mismatch", "profile-mismatch", "png-truncated", "png-crc", "png-no-idat", "png-invalid-idat", "png-unknown-critical")):
            with self.subTest(mode=mode):
                with patch.object(publisher, "_parse_inspection", return_value=self._payload()):
                    with self.assertRaises(publisher.SurfacePreviewPublishError):
                        publisher.publish_surface_preview(self.root, self.input, creature_kernel=self._producer(), generator=self._generator(mode=mode), review_id=f"bad-{index}")
                self.assertFalse((self.root / f"bad-{index}").exists())

    def test_generator_timeout_is_bounded(self) -> None:
        with patch.object(publisher, "_parse_inspection", return_value=self._payload()), patch.object(publisher, "GENERATOR_TIMEOUT_SECONDS", 0.05):
            with self.assertRaisesRegex(publisher.SurfacePreviewPublishError, "timed out"):
                publisher.publish_surface_preview(self.root, self.input, creature_kernel=self._producer(), generator=self._generator(mode="timeout"), review_id="timeout")
        self.assertEqual(list(self.root.iterdir()), [])

    def test_bundle_root_symlink_is_rejected_before_manifest_access(self) -> None:
        real_bundle = self.directory / "real-bundle"
        real_bundle.mkdir()
        link = self.directory / "bundle-link"
        link.symlink_to(real_bundle, target_is_directory=True)
        with self.assertRaisesRegex(publisher.SurfacePreviewPublishError, "real non-symlink directory"):
            publisher._validate_bundle(link, "0" * 64)


if __name__ == "__main__":
    unittest.main()
