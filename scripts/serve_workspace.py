#!/usr/bin/env python3
"""Serve the readiness workspace on loopback without exposing local directories.

This viewer has no GitHub connection, credentials, upload endpoint, or telemetry.
An explicitly selected report is loaded once and served only as local-report.json.
"""

from __future__ import annotations

import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import stat
from typing import Any
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
MAX_REPORT_BYTES = 2_000_000
ASSETS = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/index.html": ("index.html", "text/html; charset=utf-8"),
    "/app.js": ("app.js", "text/javascript; charset=utf-8"),
    "/model.mjs": ("model.mjs", "text/javascript; charset=utf-8"),
    "/styles.css": ("styles.css", "text/css; charset=utf-8"),
    "/favicon.svg": ("favicon.svg", "image/svg+xml"),
    "/data/sample-report.json": ("data/sample-report.json", "application/json"),
}
CSP = (
    "default-src 'self'; connect-src 'self'; script-src 'self'; "
    "style-src 'self' 'unsafe-inline'; font-src 'self'; img-src 'self' data:; "
    "frame-ancestors 'none'; form-action 'none'; base-uri 'none'; object-src 'none'"
)


class WorkspaceError(ValueError):
    """A safe, non-sensitive explanation of a viewer setup error."""


def read_report(path: str | Path) -> bytes:
    """Read one bounded regular JSON file, refusing leaf symlinks and devices."""
    selected = Path(path)
    if selected.is_symlink():
        raise WorkspaceError("Choose a regular report file, not a symbolic link.")
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
    try:
        descriptor = os.open(selected, flags)
        with os.fdopen(descriptor, "rb") as stream:
            info = os.fstat(stream.fileno())
            if not stat.S_ISREG(info.st_mode):
                raise WorkspaceError("Choose a regular JSON report file.")
            if info.st_size > MAX_REPORT_BYTES:
                raise WorkspaceError("Choose a report smaller than 2 MB.")
            data = stream.read(MAX_REPORT_BYTES + 1)
    except WorkspaceError:
        raise
    except OSError:
        raise WorkspaceError("The selected report could not be read.") from None
    if len(data) > MAX_REPORT_BYTES:
        raise WorkspaceError("Choose a report smaller than 2 MB.")
    try:
        report = json.loads(data)
    except (ValueError, RecursionError):
        raise WorkspaceError("The selected report is not valid JSON.") from None
    if (not isinstance(report, dict) or type(report.get("schema_version")) is not int
            or report.get("schema_version") != 1
            or report.get("mode") not in ("fixture", "github")
            or not isinstance(report.get("controls"), list) or not report["controls"]):
        raise WorkspaceError("Choose a version 1 fixture or GitHub assessment report.")
    return data


class LocalWorkspaceServer(ThreadingHTTPServer):
    """A bounded loopback server whose handler never opens arbitrary paths."""

    daemon_threads = True
    block_on_close = False

    def get_request(self) -> tuple[Any, Any]:
        connection, address = super().get_request()
        connection.settimeout(10)
        return connection, address


def new_server(report_path: str | Path | None = None, port: int = 0) -> LocalWorkspaceServer:
    """Create a loopback-only viewer; call serve_forever() and server_close()."""
    if type(port) is not int or not 0 <= port <= 65535:
        raise WorkspaceError("Choose a port between 0 and 65535.")
    payloads: dict[str, tuple[bytes, str]] = {}
    try:
        for route, (name, mime) in ASSETS.items():
            payloads[route] = ((ROOT / "demo" / name).read_bytes(), mime)
    except OSError:
        raise WorkspaceError("The workspace assets are unavailable in this checkout.") from None
    if report_path is not None:
        payloads["/local-report.json"] = (read_report(report_path), "application/json")

    class Handler(BaseHTTPRequestHandler):
        server_version = "SOC2Workspace"
        sys_version = ""

        def log_message(self, format: str, *args: Any) -> None:
            # A request path or query can contain local evidence identifiers.
            return

        def _reply(self, status: int, data: bytes = b"", mime: str = "text/plain") -> None:
            self.send_response(status)
            self.send_header("Content-Type", mime)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Security-Policy", CSP)
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("Cross-Origin-Resource-Policy", "same-origin")
            self.send_header("X-Frame-Options", "DENY")
            self.send_header("Connection", "close")
            if status == 405:
                self.send_header("Allow", "GET")
            self.end_headers()
            self.close_connection = True
            if self.command != "HEAD" and data:
                try:
                    self.wfile.write(data)
                except (BrokenPipeError, ConnectionResetError):
                    pass

        def send_error(self, code: int, message: str | None = None,
                       explain: str | None = None) -> None:
            # Never reflect attacker-controlled request text in an HTML error.
            self._reply(code, b"Request rejected.\n")

        def _allowed_request(self) -> bool:
            actual_port = self.server.server_address[1]
            hosts = {f"127.0.0.1:{actual_port}", f"localhost:{actual_port}"}
            supplied_hosts = self.headers.get_all("Host", [])
            origins = self.headers.get_all("Origin", [])
            if len(supplied_hosts) != 1 or supplied_hosts[0] not in hosts:
                self._reply(403, b"Local origin required.\n")
                return False
            if origins and (len(origins) != 1 or origins[0] not in {f"http://{h}" for h in hosts}):
                self._reply(403, b"Local origin required.\n")
                return False
            if self.headers.get("Sec-Fetch-Site") not in {None, "none", "same-origin"}:
                self._reply(403, b"Local origin required.\n")
                return False
            if self.headers.get("Transfer-Encoding") or self.headers.get("Content-Length", "0") != "0":
                self._reply(400, b"Request bodies are not supported.\n")
                return False
            return True

        def do_GET(self) -> None:
            if not self._allowed_request():
                return
            try:
                parts = urlsplit(self.path)
            except ValueError:
                self._reply(400, b"Request rejected.\n")
                return
            if parts.scheme or parts.netloc or parts.fragment:
                self._reply(400, b"Request rejected.\n")
                return
            selected = payloads.get(parts.path)
            if selected is None:
                self._reply(404, b"Not found.\n")
                return
            self._reply(200, *selected)

        def _unsupported(self) -> None:
            if self._allowed_request():
                self._reply(405, b"Only GET is supported.\n")

        do_HEAD = _unsupported
        do_POST = _unsupported
        do_PUT = _unsupported
        do_PATCH = _unsupported
        do_DELETE = _unsupported
        do_OPTIONS = _unsupported
        do_TRACE = _unsupported
        do_CONNECT = _unsupported

    return LocalWorkspaceServer(("127.0.0.1", port), Handler)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--report", type=Path, help="One local report.json to open automatically")
    args = parser.parse_args()
    try:
        server = new_server(args.report, args.port)
    except WorkspaceError as error:
        raise SystemExit(str(error)) from None
    except OSError:
        raise SystemExit("Could not start the local viewer. Choose an unused local port.") from None
    port = server.server_address[1]
    suffix = "?local=1" if args.report else ""
    print(f"Local workspace: http://127.0.0.1:{port}/{suffix}", flush=True)
    print("Loopback only. No uploads or provider connection. Press Ctrl+C to stop.", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
