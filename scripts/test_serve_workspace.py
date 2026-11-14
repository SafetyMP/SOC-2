"""Loopback-only viewer boundaries; all report contents are synthetic."""

from __future__ import annotations

from contextlib import contextmanager, redirect_stderr
import http.client
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
from typing import Any, Iterator
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from serve_workspace import MAX_REPORT_BYTES, WorkspaceError, new_server, read_report


REPORT = {"schema_version": 1, "mode": "github", "controls": [{"id": "CTRL-CHG-001"}]}
REVIEW = {
    "format": "soc2-workspace-review-v1",
    "report": {**REPORT, "controls": [{"id": "CTRL-CHG-002", "status": "FAIL",
                                      "findings": ["Requires two reviewers; has zero."]}]},
    "review_notes": {"CTRL-CHG-002": {"owner": "", "progress": "Not started",
                                    "note": "Solo maintainer; this is not a waiver."}},
}


@contextmanager
def viewer(report_path: Path | None = None) -> Iterator[Any]:
    server = new_server(report_path, port=0)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        yield server
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=2)


def request(server: Any, path: str = "/", method: str = "GET",
            headers: dict[str, str] | None = None, body: str | None = None) -> tuple[int, dict[str, str], bytes]:
    connection = http.client.HTTPConnection("127.0.0.1", server.server_address[1], timeout=3)
    try:
        connection.request(method, path, body=body, headers=headers or {})
        response = connection.getresponse()
        return response.status, dict(response.getheaders()), response.read()
    finally:
        connection.close()


class ViewerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temporary = tempfile.TemporaryDirectory(prefix="soc2-viewer-test-")
        cls.report_path = Path(cls.temporary.name) / "report.json"
        cls.report_path.write_text(json.dumps(REPORT))
        cls.server = new_server(cls.report_path, port=0)
        cls.worker = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.worker.start()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.shutdown()
        cls.server.server_close()
        cls.worker.join(timeout=2)
        cls.temporary.cleanup()

    def test_only_loopback_bind_and_local_report(self) -> None:
        self.assertEqual(self.server.server_address[0], "127.0.0.1")
        status, headers, body = request(self.server, "/local-report.json")
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body), REPORT)
        self.assertEqual(headers["Content-Type"], "application/json")

    def test_public_assets_are_exact_and_root_query_does_not_select_files(self) -> None:
        for path in ("/?local=1", "/index.html", "/app.js", "/model.mjs",
                     "/styles.css", "/favicon.svg", "/data/sample-report.json"):
            with self.subTest(path=path):
                self.assertEqual(request(self.server, path)[0], 200)
        status, _, body = request(self.server, "/local-report.json?file=README.md")
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body), REPORT)

    def test_directory_and_path_traversal_requests_cannot_read_evidence(self) -> None:
        for path in ("/data/", "/evidence.json", "/README.md", "/../README.md",
                     "/%2e%2e/README.md", "/data/%2e%2e/app.js", "/.git/config",
                     "/scripts/serve_workspace.py", "/local-report.json/../evidence.json"):
            with self.subTest(path=path):
                self.assertEqual(request(self.server, path)[0], 404)
        self.assertEqual(request(self.server, "http://other.example/local-report.json", headers={
            "Host": f"127.0.0.1:{self.server.server_address[1]}"})[0], 400)

    def test_host_rebinding_and_duplicate_hosts_are_rejected(self) -> None:
        port = self.server.server_address[1]
        for host in ("attacker.example", f"attacker.example:{port}", "localhost",
                     f"127.0.0.1:{port + 1}", f"localhost:{port}.attacker.example"):
            self.assertEqual(request(self.server, headers={"Host": host})[0], 403)
        self.assertEqual(request(self.server, headers={"Host": f"localhost:{port}"})[0], 200)
        connection = http.client.HTTPConnection("127.0.0.1", port, timeout=3)
        try:
            connection.putrequest("GET", "/local-report.json", skip_host=True)
            connection.putheader("Host", f"127.0.0.1:{port}")
            connection.putheader("Host", f"localhost:{port}")
            connection.endheaders()
            response = connection.getresponse()
            self.assertEqual(response.status, 403)
            response.read()
        finally:
            connection.close()

    def test_cross_origin_and_cross_site_reads_are_rejected(self) -> None:
        port = self.server.server_address[1]
        for origin in ("https://attacker.example", "null", "http://127.0.0.1:9"):
            self.assertEqual(request(self.server, "/local-report.json", headers={"Origin": origin})[0], 403)
        for site in ("cross-site", "same-site"):
            self.assertEqual(request(self.server, "/local-report.json", headers={"Sec-Fetch-Site": site})[0], 403)
        self.assertEqual(request(self.server, "/local-report.json", headers={
            "Origin": f"http://127.0.0.1:{port}", "Sec-Fetch-Site": "same-origin"})[0], 200)

    def test_server_never_accepts_mutations_or_request_bodies(self) -> None:
        for method in ("HEAD", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "TRACE", "CONNECT"):
            with self.subTest(method=method):
                self.assertEqual(request(self.server, "/local-report.json", method=method)[0], 405)
        self.assertEqual(request(self.server, "/local-report.json", body="overwrite")[0], 400)
        self.assertEqual(json.loads(self.report_path.read_text()), REPORT)

    def test_privacy_headers_block_network_dependencies_and_caching(self) -> None:
        for path in ("/", "/local-report.json", "/not-found"):
            _, headers, _ = request(self.server, path)
            self.assertEqual(headers["Cache-Control"], "no-store")
            self.assertEqual(headers["X-Content-Type-Options"], "nosniff")
            self.assertEqual(headers["Referrer-Policy"], "no-referrer")
            self.assertEqual(headers["Cross-Origin-Resource-Policy"], "same-origin")
            self.assertNotIn("Access-Control-Allow-Origin", headers)
            for directive in ("connect-src 'self'", "script-src 'self'", "font-src 'self'",
                              "frame-ancestors 'none'", "form-action 'none'", "base-uri 'none'"):
                self.assertIn(directive, headers["Content-Security-Policy"])

    def test_report_is_snapshot_in_memory_and_request_logs_are_silent(self) -> None:
        with tempfile.TemporaryDirectory(prefix="soc2-snapshot-test-") as temporary:
            path = Path(temporary) / "private.json"
            path.write_text(json.dumps(REPORT))
            with viewer(path) as server:
                path.write_text("changed after serving")
                errors = io.StringIO()
                with redirect_stderr(errors):
                    _, _, body = request(server, "/local-report.json?private_identifier=do-not-log")
                self.assertEqual(json.loads(body), REPORT)
                self.assertEqual(errors.getvalue(), "")

    def test_no_report_is_exposed_without_explicit_selection(self) -> None:
        with viewer() as server:
            self.assertEqual(request(server, "/local-report.json")[0], 404)

    def test_exported_review_serves_notes_and_failed_results_without_writes(self) -> None:
        with tempfile.TemporaryDirectory(prefix="soc2-review-test-") as temporary:
            path = Path(temporary) / "review.json"
            original = json.dumps(REVIEW).encode()
            path.write_bytes(original)
            with viewer(path) as server:
                status, headers, body = request(server, "/local-report.json")
                self.assertEqual(status, 200)
                self.assertEqual(body, original)
                self.assertEqual(json.loads(body)["report"]["controls"][0]["status"], "FAIL")
                self.assertEqual(json.loads(body)["review_notes"], REVIEW["review_notes"])
                self.assertEqual(path.read_bytes(), original)
                self.assertEqual(headers["Cache-Control"], "no-store")
                self.assertIn("connect-src 'self'", headers["Content-Security-Policy"])
                self.assertEqual(request(server, "/evidence.json")[0], 404)
                self.assertEqual(request(server, "/local-report.json", headers={
                    "Origin": "https://attacker.example"})[0], 403)
                self.assertEqual(request(server, "/local-report.json", method="POST")[0], 405)


class ReportInputTests(unittest.TestCase):
    def test_raw_reports_and_exported_reviews_keep_their_original_bytes(self) -> None:
        with tempfile.TemporaryDirectory(prefix="soc2-review-input-test-") as temporary:
            path = Path(temporary) / "selected.json"
            for mode in ("fixture", "github"):
                for document in ({**REPORT, "mode": mode},
                                 {**REVIEW, "report": {**REVIEW["report"], "mode": mode}},
                                 {**REVIEW, "report": {**REVIEW["report"], "mode": mode}, "review_notes": {}}):
                    with self.subTest(mode=mode, wrapped="format" in document):
                        original = json.dumps(document, indent=2).encode()
                        path.write_bytes(original)
                        self.assertEqual(read_report(path), original)

    def test_invalid_review_envelopes_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory(prefix="soc2-review-input-test-") as temporary:
            path = Path(temporary) / "private-review.json"
            invalid = [
                {**REVIEW, "format": "secret-marker-unknown-format"},
                {**REVIEW, "format": []},
                {"format": REVIEW["format"], "report": REPORT},
                {**REVIEW, "review_notes": None},
                {**REVIEW, "review_notes": []},
                {**REVIEW, "report": None},
                {**REVIEW, "report": REVIEW},
                {**REVIEW, "report": {**REPORT, "schema_version": True}},
                {**REVIEW, "report": {**REPORT, "mode": "unknown"}},
                {**REVIEW, "report": {**REPORT, "controls": []}},
                {**REVIEW, "review_notes": {"secret-marker": "x" * MAX_REPORT_BYTES}},
            ]
            for document in invalid:
                path.write_text(json.dumps(document))
                with self.assertRaises(WorkspaceError) as raised:
                    read_report(path)
                self.assertNotIn("private-review", str(raised.exception))
                self.assertNotIn("secret-marker", str(raised.exception))

    def test_invalid_reports_fail_without_sensitive_path_or_content(self) -> None:
        with tempfile.TemporaryDirectory(prefix="soc2-report-test-") as temporary:
            path = Path(temporary) / "sensitive-target.json"
            for payload in (b"not JSON secret-marker", b"[]", b"{}", b"{\"schema_version\":1}",
                            json.dumps({**REPORT, "mode": "unknown"}).encode(),
                            json.dumps({**REPORT, "mode": []}).encode(),
                            json.dumps({**REPORT, "schema_version": True}).encode(),
                            b"[" * 2000 + b"]" * 2000,
                            b"9" * 10000,
                            b" " * (MAX_REPORT_BYTES + 1)):
                path.write_bytes(payload)
                with self.assertRaises(WorkspaceError) as raised:
                    read_report(path)
                self.assertNotIn("sensitive-target", str(raised.exception))
                self.assertNotIn("secret-marker", str(raised.exception))

    def test_leaf_symlink_directory_and_fifo_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory(prefix="soc2-file-test-") as temporary:
            root = Path(temporary)
            path = root / "report.json"
            path.write_text(json.dumps(REPORT))
            link = root / "link.json"
            link.symlink_to(path)
            with self.assertRaises(WorkspaceError):
                read_report(link)
            with self.assertRaises(WorkspaceError):
                read_report(root)
            fifo = root / "pipe.json"
            os.mkfifo(fifo)
            with self.assertRaises(WorkspaceError):
                read_report(fifo)

    def test_viewer_has_no_remote_bind_argument(self) -> None:
        for port in (-1, 65536, True, "8765"):
            with self.assertRaises(WorkspaceError):
                new_server(port=port)
        with self.assertRaises(TypeError):
            new_server(host="0.0.0.0")


if __name__ == "__main__":
    unittest.main()
