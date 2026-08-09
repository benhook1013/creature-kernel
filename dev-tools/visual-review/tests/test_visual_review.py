from __future__ import annotations

import importlib.util
import json
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
    def test_normalization_and_exact_inventory(self):
        session = self.publish()
        normalized = json.loads((session / "review.json").read_text(encoding="utf-8"))
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
        self.assertEqual(list(self.root.iterdir()), [])

    def test_install_failure_cleans_owned_files_but_not_concurrent_file(self):
        original_rename = publish.os.rename

        def fail_review_install(source, destination, *args, **kwargs):
            if Path(source).name == "review.json" and ".publish-" in str(source):
                raise OSError("injected review install failure")
            return original_rename(source, destination, *args, **kwargs)

        with patch.object(publish.os, "rename", side_effect=fail_review_install):
            with self.assertRaises(OSError):
                publish.publish_session(self.root, self.manifest_path)
        self.assertFalse((self.root / "demo-review").exists())

        session = self.root / "demo-review"

        def fail_with_concurrent_file(source, destination, *args, **kwargs):
            if Path(source).name == "review.json" and ".publish-" in str(source):
                session.joinpath("concurrent.txt").write_text("keep", encoding="utf-8")
                raise OSError("injected review install failure")
            return original_rename(source, destination, *args, **kwargs)

        with patch.object(publish.os, "rename", side_effect=fail_with_concurrent_file):
            with self.assertRaises(OSError):
                publish.publish_session(self.root, self.manifest_path)
        self.assertEqual((session / "concurrent.txt").read_text(encoding="utf-8"), "keep")
        self.assertFalse((session / "review.json").exists())
        self.assertFalse((session / "assets").exists())

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


class HTTPTests(ReviewFixture):
    def setUp(self) -> None:
        super().setUp()
        self.server, self.base = self.start_server()

    def test_index_review_asset_and_response_happy_paths(self):
        status, headers, body = self.get(self.base + "/")
        self.assertEqual(status, 200)
        self.assertIn(b"visual reviews", body)
        self.assertEqual(headers["X-Content-Type-Options"], "nosniff")
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
    def test_assets_have_no_external_fetches_or_html_interpolation(self):
        js = (HERE / "static" / "app.js").read_text(encoding="utf-8")
        css = (HERE / "static" / "style.css").read_text(encoding="utf-8")
        self.assertNotIn("innerHTML", js)
        self.assertNotRegex(js + css, r"https?://")
        for label in (
            "What you're looking at",
            "Authored summary",
            "Generated descriptor snapshot",
            "Build/render provenance",
        ):
            self.assertIn(label, js)


if __name__ == "__main__":
    unittest.main()
