#!/usr/bin/env python3
"""Serve local visual-review sessions over loopback or explicit LAN read-only HTTP."""

from __future__ import annotations

import argparse
import html
import json
import os
import secrets
import stat
import sys
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlsplit

from common import (
    CONTENT_TYPES,
    MAX_JSON_BYTES,
    SCHEMA_VERSION,
    ValidationError,
    canonical_json,
    ensure_root,
    iter_sessions,
    require_secure_fs_support,
    utc_timestamp,
    validate_id,
    validate_normalized_review,
    validate_response_payload,
)


MAX_REQUEST_BODY = 64 * 1024
FILE_COPY_CHUNK = 64 * 1024
STATIC_ROOT = Path(__file__).with_name("static")
LOCAL_HOSTS = {"localhost", "127.0.0.1"}


def _decode_path(raw_path: str) -> str:
    if "\x00" in raw_path:
        raise ValidationError("invalid URL path")
    try:
        decoded = unquote(raw_path, errors="strict")
    except UnicodeDecodeError as exc:
        raise ValidationError("invalid URL encoding") from exc
    if "\x00" in decoded or "\\" in decoded:
        raise ValidationError("invalid URL path")
    return decoded


def _route_segments(path: str) -> list[str]:
    decoded = _decode_path(path)
    segments = decoded.split("/")
    if any(part in {".", ".."} for part in segments):
        raise ValidationError("path traversal is not allowed")
    return [part for part in segments if part]


def _asset_allowlist(review: dict[str, Any]) -> set[str]:
    return {
        item["image"]
        for group in review["groups"]
        for item in group["items"]
    }


def _open_directory(parent_fd: int | None, name: str | Path, where: str) -> int:
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    fd = None
    try:
        if parent_fd is None:
            fd = os.open(name, flags)
        else:
            fd = os.open(name, flags, dir_fd=parent_fd)
        info = os.fstat(fd)
        if not stat.S_ISDIR(info.st_mode):
            os.close(fd)
            fd = None
            raise ValidationError(f"{where} is not a regular directory")
        return fd
    except ValidationError:
        if fd is not None:
            os.close(fd)
        raise
    except OSError as exc:
        if fd is not None:
            os.close(fd)
        raise ValidationError(f"{where} is unavailable or changed") from exc


def _open_regular(parent_fd: int, name: str, where: str) -> int:
    flags = os.O_RDONLY | os.O_NOFOLLOW
    fd = None
    try:
        fd = os.open(name, flags, dir_fd=parent_fd)
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode):
            os.close(fd)
            fd = None
            raise ValidationError(f"{where} is not a regular file")
        return fd
    except ValidationError:
        if fd is not None:
            os.close(fd)
        raise
    except OSError as exc:
        if fd is not None:
            os.close(fd)
        raise ValidationError(f"{where} is unavailable or changed") from exc


def _read_json_descriptor(parent_fd: int, name: str, where: str) -> Any:
    fd = _open_regular(parent_fd, name, where)
    try:
        with os.fdopen(fd, "rb") as stream:
            if os.fstat(stream.fileno()).st_size > MAX_JSON_BYTES:
                raise ValidationError(f"{where} is too large")
            raw = stream.read(MAX_JSON_BYTES + 1)
    except ValidationError:
        raise
    except (OSError, UnicodeDecodeError) as exc:
        raise ValidationError(f"cannot read {where}: {exc}") from exc
    if len(raw) > MAX_JSON_BYTES:
        raise ValidationError(f"{where} is too large")
    try:
        return json.loads(raw.decode("utf-8"), parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise ValidationError(f"invalid JSON in {where}: {exc}") from exc


def _read_response_descriptor(session_fd: int, review: dict[str, Any]) -> tuple[dict[str, Any] | None, str | None]:
    try:
        value = _read_json_descriptor(session_fd, "response.json", "response.json")
    except ValidationError as exc:
        if "unavailable or changed" in str(exc):
            return None, None
        return None, str(exc)
    if not isinstance(value, dict):
        return None, "response must be an object"
    saved_at = value.get("saved_at")
    if not isinstance(saved_at, str):
        return None, "response.saved_at is missing"
    try:
        normalized = validate_response_payload(
            {key: value[key] for key in value if key != "saved_at"}, review
        )
    except ValidationError as exc:
        return None, str(exc)
    return {**normalized, "saved_at": saved_at}, None


class VisualReviewHTTPServer(ThreadingHTTPServer):
    """HTTP server carrying its root and one process-wide write token."""

    allow_reuse_address = True
    daemon_threads = True

    def __init__(self, address: tuple[str, int], reviews_root: Path, *, read_only: bool = False):
        self.reviews_root = ensure_root(reviews_root)
        require_secure_fs_support()
        self.root_fd = _open_directory(None, self.reviews_root, "reviews root")
        self.write_token = secrets.token_urlsafe(32)
        self.read_only = read_only
        try:
            super().__init__(address, VisualReviewHandler)
        except Exception:
            os.close(self.root_fd)
            raise

    def server_close(self) -> None:
        try:
            super().server_close()
        finally:
            try:
                os.close(self.root_fd)
            except OSError:
                pass


class VisualReviewHandler(BaseHTTPRequestHandler):
    server: VisualReviewHTTPServer
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt: str, *args: Any) -> None:
        # Keep the CLI's one clear URL readable while retaining useful request
        # diagnostics on stderr.
        sys.stderr.write(f"visual-review: {self.address_string()} - {fmt % args}\n")

    def _headers(self, content_type: str, length: int) -> None:
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(length))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'")
        self.send_header("Referrer-Policy", "no-referrer")

    def _send_bytes(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self._headers(content_type, len(body))
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _send_file(self, status: int, path: Path, content_type: str) -> None:
        """Stream one fixed-owned regular file without unbounded buffering."""

        fd = None
        try:
            initial = os.lstat(path)
            if not stat.S_ISREG(initial.st_mode):
                raise ValidationError("owned file is not a regular file")
            flags = os.O_RDONLY
            if hasattr(os, "O_NOFOLLOW"):
                flags |= os.O_NOFOLLOW
            fd = os.open(path, flags)
            opened = os.fstat(fd)
            if not stat.S_ISREG(opened.st_mode) or (opened.st_dev, opened.st_ino) != (initial.st_dev, initial.st_ino):
                raise ValidationError("owned file changed while opening")
        except ValidationError:
            if fd is not None:
                os.close(fd)
            raise
        except OSError as exc:
            if fd is not None:
                os.close(fd)
            raise ValidationError("owned file is unavailable") from exc

        owned_fd = fd
        fd = None
        self._send_open_file(status, owned_fd, content_type, opened.st_size)

    def _send_open_file(self, status: int, fd: int, content_type: str, length: int | None = None) -> None:
        """Send an already-open regular descriptor in bounded chunks."""

        stream = None
        try:
            stream = os.fdopen(fd, "rb")
            info = os.fstat(stream.fileno())
            if not stat.S_ISREG(info.st_mode):
                raise ValidationError("owned file is not a regular file")
            if length is None:
                length = info.st_size
            self.send_response(status)
            self._headers(content_type, length)
            self.end_headers()
            if self.command != "HEAD":
                while True:
                    chunk = stream.read(FILE_COPY_CHUNK)
                    if not chunk:
                        break
                    self.wfile.write(chunk)
        finally:
            if stream is not None:
                stream.close()
            else:
                try:
                    os.close(fd)
                except OSError:
                    pass

    def _send_json(self, status: int, value: Any) -> None:
        self._send_bytes(status, canonical_json(value).encode("utf-8"), "application/json; charset=utf-8")

    def _error(self, status: int, message: str) -> None:
        self._send_json(status, {"error": message})

    def _page(self, *, review: bool = False) -> None:
        if review:
            token = html.escape(self.server.write_token, quote=True)
            body = (
                "<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">"
                "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
                f"<meta name=\"visual-review-write-token\" content=\"{token}\">"
                "<title>Creature Kernel visual review</title><link rel=\"stylesheet\" href=\"/static/style.css\"></head>"
                "<body><main id=\"app\"><p>Loading visual review…</p></main>"
                "<script src=\"/static/app.js\" defer></script></body></html>"
            )
        else:
            body = (
                "<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">"
                "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
                "<title>Creature Kernel visual reviews</title><link rel=\"stylesheet\" href=\"/static/style.css\"></head>"
                "<body><main id=\"app\"><p>Loading visual reviews…</p></main>"
                "<script src=\"/static/app.js\" defer></script></body></html>"
            )
        self._send_bytes(HTTPStatus.OK, body.encode("utf-8"), "text/html; charset=utf-8")

    def _load_review(self, review_id: str) -> tuple[Path, dict[str, Any], int, int] | None:
        session_fd = None
        assets_fd = None
        try:
            validate_id(review_id, "review id")
            session_fd = _open_directory(self.server.root_fd, review_id, "review session")
            raw_review = _read_json_descriptor(session_fd, "review.json", "review.json")
            review = validate_normalized_review(
                raw_review,
                self.server.reviews_root / review_id,
                check_assets=False,
            )
            if review["id"] != review_id:
                raise ValidationError("session directory and review id differ")
            assets_fd = _open_directory(session_fd, "assets", "session assets")
            for group in review["groups"]:
                for item in group["items"]:
                    asset_fd = _open_regular(
                        assets_fd,
                        Path(item["image"]).name,
                        f"asset {item['id']}",
                    )
                    os.close(asset_fd)
            return self.server.reviews_root / review_id, review, session_fd, assets_fd
        except ValidationError as exc:
            if assets_fd is not None:
                os.close(assets_fd)
            if session_fd is not None:
                os.close(session_fd)
            self._error(HTTPStatus.NOT_FOUND, str(exc))
            return None

    def _request_path(self) -> tuple[str, list[str]]:
        parsed = urlsplit(self.path)
        return parsed.path, _route_segments(parsed.path)

    def do_HEAD(self) -> None:
        self.do_GET()

    def do_GET(self) -> None:
        try:
            path, segments = self._request_path()
            if path == "/":
                self._page()
                return
            if segments == ["static", "style.css"]:
                self._serve_static("style.css", "text/css; charset=utf-8")
                return
            if segments == ["static", "app.js"]:
                self._serve_static("app.js", "text/javascript; charset=utf-8")
                return
            if segments == ["api", "sessions"]:
                valid, errors = iter_sessions(self.server.reviews_root)
                self._send_json(HTTPStatus.OK, {"schema_version": SCHEMA_VERSION, "sessions": valid, "errors": errors})
                return
            # API review data and response reads.
            if len(segments) == 3 and segments[:2] == ["api", "reviews"]:
                loaded = self._load_review(segments[2])
                if loaded is None:
                    return
                session, review, session_fd, assets_fd = loaded
                try:
                    response, response_error = _read_response_descriptor(session_fd, review)
                    self._send_json(HTTPStatus.OK, {
                        "schema_version": SCHEMA_VERSION,
                        "review": review,
                        "response": response,
                        **({"response_error": response_error} if response_error else {}),
                    })
                finally:
                    os.close(assets_fd)
                    os.close(session_fd)
                return
            if len(segments) == 4 and segments[:3] == ["api", "reviews", segments[2]] and segments[3] == "response":
                loaded = self._load_review(segments[2])
                if loaded is None:
                    return
                _, review, session_fd, assets_fd = loaded
                try:
                    response, response_error = _read_response_descriptor(session_fd, review)
                    self._send_json(HTTPStatus.OK, {"schema_version": SCHEMA_VERSION, "review_id": review["id"], "response": response, **({"error": response_error} if response_error else {})})
                finally:
                    os.close(assets_fd)
                    os.close(session_fd)
                return
            # The asset route has an explicit API prefix.  A short /asset alias
            # is retained for convenient manual inspection.
            asset_start = None
            if len(segments) >= 5 and segments[:3] == ["api", "reviews", segments[2]] and segments[3] == "assets":
                asset_start = 4
                review_id = segments[2]
            elif len(segments) >= 3 and segments[0] == "asset":
                asset_start = 2
                review_id = segments[1]
            if asset_start is not None:
                loaded = self._load_review(review_id)
                if loaded is None:
                    return
                _, review, session_fd, assets_fd = loaded
                relative = "assets/" + "/".join(segments[asset_start:])
                try:
                    if relative not in _asset_allowlist(review):
                        raise ValidationError("asset is not part of this review")
                    parts = Path(relative).parts
                    if len(parts) != 2 or parts[0] != "assets":
                        raise ValidationError("asset path is outside the session")
                    asset_fd = _open_regular(assets_fd, parts[1], "review asset")
                    self._send_open_file(HTTPStatus.OK, asset_fd, CONTENT_TYPES[Path(relative).suffix.lower()])
                except ValidationError as exc:
                    self._error(HTTPStatus.NOT_FOUND, str(exc))
                finally:
                    os.close(assets_fd)
                    os.close(session_fd)
                return
            if len(segments) == 2 and segments[0] == "review":
                # Verify first so a typo does not produce a page that then
                # fails asynchronously in the browser.
                loaded = self._load_review(segments[1])
                if loaded is None:
                    return
                _, _, session_fd, assets_fd = loaded
                try:
                    self._page(review=True)
                finally:
                    os.close(assets_fd)
                    os.close(session_fd)
                return
            self._error(HTTPStatus.NOT_FOUND, "not found")
        except ValidationError as exc:
            self._error(HTTPStatus.BAD_REQUEST, str(exc))
        except (OSError, ValueError) as exc:
            self._error(HTTPStatus.INTERNAL_SERVER_ERROR, f"server error: {exc}")

    def _serve_static(self, name: str, content_type: str) -> None:
        path = STATIC_ROOT / name
        if path.is_symlink() or not path.is_file():
            self._error(HTTPStatus.INTERNAL_SERVER_ERROR, "owned static asset is unavailable")
            return
        try:
            self._send_file(HTTPStatus.OK, path, content_type)
        except ValidationError as exc:
            self._error(HTTPStatus.INTERNAL_SERVER_ERROR, str(exc))

    def _local_write_request(self) -> bool:
        host = self.headers.get("Host", "")
        try:
            host_url = urlsplit("//" + host)
            host_name = host_url.hostname
            host_port = host_url.port
        except ValueError:
            return False
        if host_name not in LOCAL_HOSTS or host_port not in {None, self.server.server_port}:
            return False
        origin = self.headers.get("Origin")
        if not origin:
            return False
        try:
            origin_url = urlsplit(origin)
            origin_name = origin_url.hostname
            origin_port = origin_url.port
        except ValueError:
            return False
        if origin_url.scheme != "http" or origin_name not in LOCAL_HOSTS:
            return False
        return origin_port in {None, self.server.server_port}

    def _read_body(self) -> bytes:
        raw_length = self.headers.get("Content-Length")
        if raw_length is None:
            raise ValidationError("Content-Length is required")
        try:
            length = int(raw_length)
        except ValueError as exc:
            raise ValidationError("invalid Content-Length") from exc
        if length < 0:
            raise ValidationError("invalid Content-Length")
        if length > MAX_REQUEST_BODY:
            raise OverflowError("request body exceeds 64 KiB")
        body = self.rfile.read(length)
        if len(body) != length:
            raise ValidationError("incomplete request body")
        return body

    def _atomic_response(self, session_fd: int, value: dict[str, Any]) -> None:
        """Atomically update response.json relative to an opened session dir."""

        temporary_name = f".response-{secrets.token_hex(16)}.tmp"
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW
        fd = os.open(temporary_name, flags, 0o600, dir_fd=session_fd)
        try:
            with open(fd, "w", encoding="utf-8", newline="\n") as stream:
                stream.write(canonical_json(value))
                stream.flush()
                os.fsync(stream.fileno())
            os.rename(
                temporary_name,
                "response.json",
                src_dir_fd=session_fd,
                dst_dir_fd=session_fd,
            )
        finally:
            try:
                os.unlink(temporary_name, dir_fd=session_fd)
            except FileNotFoundError:
                pass

    def do_POST(self) -> None:
        try:
            if self.server.read_only:
                self._error(HTTPStatus.FORBIDDEN, "response writes are disabled in LAN read-only mode")
                return
            _, segments = self._request_path()
            if not (len(segments) == 4 and segments[:2] == ["api", "reviews"] and segments[3] == "response"):
                self._error(HTTPStatus.NOT_FOUND, "not found")
                return
            if not self._local_write_request():
                self._error(HTTPStatus.FORBIDDEN, "writes require a localhost same-origin request")
                return
            if self.headers.get("X-Visual-Review-Token") != self.server.write_token:
                self._error(HTTPStatus.FORBIDDEN, "missing or incorrect write token")
                return
            content_type = self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
            if content_type != "application/json":
                self._error(HTTPStatus.UNSUPPORTED_MEDIA_TYPE, "Content-Type must be application/json")
                return
            loaded = self._load_review(segments[2])
            if loaded is None:
                return
            _, review, session_fd, assets_fd = loaded
            try:
                try:
                    body = self._read_body()
                except OverflowError as exc:
                    self._error(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, str(exc))
                    return
                try:
                    value = json.loads(body.decode("utf-8"), parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))
                except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
                    self._error(HTTPStatus.BAD_REQUEST, f"invalid JSON body: {exc}")
                    return
                normalized = validate_response_payload(value, review)
                response = {**normalized, "saved_at": utc_timestamp()}
                self._atomic_response(session_fd, response)
                self._send_json(HTTPStatus.OK, response)
            finally:
                os.close(assets_fd)
                os.close(session_fd)
        except ValidationError as exc:
            self._error(HTTPStatus.BAD_REQUEST, str(exc))
        except (OSError, ValueError) as exc:
            self._error(HTTPStatus.INTERNAL_SERVER_ERROR, f"server error: {exc}")


def create_server(
    reviews_root: Path,
    port: int = 0,
    *,
    lan_read_only: bool = False,
) -> VisualReviewHTTPServer:
    if not isinstance(port, int) or isinstance(port, bool) or not 0 <= port <= 65535:
        raise ValidationError("port must be between 0 and 65535")
    bind_host = "0.0.0.0" if lan_read_only else "127.0.0.1"
    return VisualReviewHTTPServer((bind_host, port), reviews_root, read_only=lan_read_only)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, type=Path, help="existing reviews root")
    parser.add_argument("--port", type=int, default=8000, help="TCP port (0 chooses one)")
    parser.add_argument(
        "--lan-read-only",
        action="store_true",
        help="bind to all interfaces for LAN GET/read access; disable all response writes",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        server = create_server(args.root, args.port, lan_read_only=args.lan_read_only)
    except (ValidationError, OSError, ValueError) as exc:
        print(f"serve failed: {exc}", file=sys.stderr)
        return 2
    if args.lan_read_only:
        print(
            "WARNING: --lan-read-only makes review contents readable to devices "
            "that can reach this port; response writes are disabled entirely in LAN mode.",
            flush=True,
        )
        print(f"Visual review gallery (LAN read-only): http://0.0.0.0:{server.server_port}/", flush=True)
        print("For another device, replace 0.0.0.0 with this host's LAN IP.", flush=True)
    else:
        print(f"Visual review gallery: http://127.0.0.1:{server.server_port}/", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
