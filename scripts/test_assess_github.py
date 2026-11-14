"""Offline contracts for private, strictly scoped real repository assessments."""
from __future__ import annotations

import copy
import io
import json
import shlex
from pathlib import Path
import stat
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import assess_github as assessor


class GitHubAssessmentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="soc2-real-assessment-test-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.destination = self.root / "assessment"
        self.collection = {
            "target": {"host": "github.com", "repository": "example/real-repo",
                       "branch": "main", "commit": "a" * 40, "visibility": "private"},
            "collected_at": "2026-11-14T12:30:00Z",
            "payloads": {
                "branch_protection": {"repositories": [{"name": "example/real-repo", "environment": "prod",
                    "protected": True, "allow_force_pushes": False, "enforce_admins": True,
                    "required_reviewers": 2, "required_status_checks": True}]},
                "ci": {"repositories": [{"name": "example/real-repo", "environment": "prod", "ci_workflow": True}]},
            },
            "errors": {"branch_protection": None, "ci": None},
            "observations": [{"endpoint": "repository", "status": "read"}],
            "limitations": ["Configuration does not establish operating effectiveness."],
        }

    def run_assessment(self, results: list | None = None, collection: dict | None = None):
        answers = results or [{"status": "PASS", "findings": []}] * 2
        with patch.object(assessor, "collect_repository", return_value=collection or self.collection) as collect, \
             patch.object(assessor, "evaluate", side_effect=answers) as evaluate, \
             patch("export_workspace.run", side_effect=AssertionError("fixture runner must not execute")):
            result = assessor.assess_repository("example/real-repo", self.destination)
        return result, collect, evaluate

    def test_real_report_has_only_three_scoped_controls_without_demo_overlays(self) -> None:
        (report, destination, incomplete), collect, evaluate = self.run_assessment()
        self.assertFalse(incomplete)
        collect.assert_called_once_with("example/real-repo")
        self.assertEqual(evaluate.call_count, 2)
        self.assertEqual(report["mode"], "github")
        self.assertIsNone(report["source_commit"])
        self.assertEqual(report["target"], self.collection["target"])
        self.assertEqual(report["assessment"]["control_ids"], assessor.CONTROL_IDS)
        self.assertEqual(report["as_of"], self.collection["collected_at"])
        self.assertEqual(report["generated_at"], self.collection["collected_at"])
        self.assertEqual(report["summary"]["wired_count"], 3)
        self.assertEqual(report["summary"]["unwired_count"], 34)
        for control in report["controls"]:
            self.assertIsNone(control["waiver"])
            if control["id"] in assessor.CONTROL_IDS:
                self.assertEqual(control["status"], "PASS")
                self.assertEqual(control["source"]["sensor"], "github-api")
                self.assertEqual(control["source"]["payload"], "evidence.json")
                self.assertTrue(control["check_scope"])
                self.assertEqual(control["collected_at"], self.collection["collected_at"])
            else:
                self.assertEqual(control["status"], "UNWIRED")
                self.assertIn("Outside this GitHub repository assessment", control["scope_reason"])
        self.assertEqual(json.loads((destination / "report.json").read_text()), report)
        evidence = json.loads((destination / "evidence.json").read_text())
        self.assertEqual(evidence["normalized_payloads"], self.collection["payloads"])
        self.assertEqual(len(evidence["records"]), 3)
        self.assertEqual(set(p.name for p in destination.iterdir()), {"report.json", "evidence.json"})

    def test_shared_package_findings_are_attributed_to_the_right_control(self) -> None:
        (report, _, incomplete), _, _ = self.run_assessment([
            {"status": "FAIL", "findings": ["CTRL-CHG-002: expected two reviews"]},
            {"status": "FAIL", "findings": ["CTRL-CHG-008: no active workflow"]},
        ])
        results = {c["id"]: c for c in report["controls"]}
        self.assertEqual(results["CTRL-CHG-001"]["status"], "PASS")
        self.assertEqual(results["CTRL-CHG-002"]["status"], "FAIL")
        self.assertEqual(results["CTRL-CHG-008"]["status"], "FAIL")
        self.assertFalse(incomplete)

    def test_unreadable_package_is_missing_without_erasing_independent_result(self) -> None:
        collection = copy.deepcopy(self.collection)
        collection["payloads"]["branch_protection"] = None
        collection["errors"]["branch_protection"] = "GitHub settings unavailable."
        (report, _, incomplete), _, evaluate = self.run_assessment(collection=collection)
        self.assertTrue(incomplete)
        evaluate.assert_called_once()
        statuses = {c["id"]: c["status"] for c in report["controls"]}
        self.assertEqual(statuses["CTRL-CHG-001"], "MISSING")
        self.assertEqual(statuses["CTRL-CHG-002"], "MISSING")
        self.assertEqual(statuses["CTRL-CHG-008"], "PASS")

    def test_evaluator_error_is_missing_and_raw_stderr_is_not_saved(self) -> None:
        secret = "TOKEN=never-publish-this"
        (report, destination, incomplete), _, _ = self.run_assessment([
            {"status": "MISSING", "error": secret}, {"status": "PASS", "findings": []}])
        self.assertTrue(incomplete)
        self.assertEqual(report["summary"]["counts"]["MISSING"], 2)
        for path in destination.iterdir():
            self.assertNotIn(secret, path.read_text())

    def test_output_and_temporary_payloads_are_private_and_temporary_files_removed(self) -> None:
        paths = []
        def evaluate(package, payload_path, policies_dir):
            path = Path(payload_path)
            paths.append(path)
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
            self.assertEqual(stat.S_IMODE(path.parent.stat().st_mode), 0o700)
            self.assertIn("repositories", json.loads(path.read_text()))
            return {"status": "PASS", "findings": []}
        with patch.object(assessor, "collect_repository", return_value=self.collection), \
             patch.object(assessor, "evaluate", side_effect=evaluate):
            assessor.assess_repository("example/real-repo", self.destination)
        self.assertEqual(stat.S_IMODE(self.destination.stat().st_mode), 0o700)
        for path in self.destination.iterdir():
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
        self.assertTrue(all(not path.exists() for path in paths))

    def test_existing_output_is_refused_before_collection_and_preserved(self) -> None:
        self.destination.mkdir()
        retained = self.destination / "retained-evidence.json"
        retained.write_text("original evidence")
        with patch.object(assessor, "collect_repository") as collect:
            with self.assertRaises(ValueError):
                assessor.assess_repository("example/real-repo", self.destination)
        collect.assert_not_called()
        self.assertEqual(retained.read_text(), "original evidence")

    def test_symlink_or_git_checkout_destinations_are_refused_before_collection(self) -> None:
        checkout = self.root / "checkout"
        checkout.mkdir()
        (checkout / ".git").write_text("gitdir: elsewhere")
        link = self.root / "link"
        link.symlink_to(checkout, target_is_directory=True)
        paths = [checkout / "results", link / "results", link,
                 assessor.ROOT / "demo/real-private-results", Path("relative-output")]
        with patch.object(assessor, "collect_repository") as collect:
            for path in paths:
                with self.subTest(path=path), self.assertRaises(ValueError):
                    assessor.assess_repository("example/real-repo", path)
        collect.assert_not_called()

    def test_invalid_repository_never_creates_output_or_contacts_github(self) -> None:
        with patch.object(assessor, "collect_repository") as collect:
            for value in ["https://github.com/example/repo", "--help", "example/../repo", "example/..", "example/repo?token=secret"]:
                with self.subTest(value=value), self.assertRaises(ValueError):
                    assessor.assess_repository(value, self.destination)
        collect.assert_not_called()
        self.assertFalse(self.destination.exists())

    def test_unrelated_retained_repository_evidence_is_untouched(self) -> None:
        retained = assessor.ROOT / "evidence/out"
        before = {str(p): p.read_bytes() for p in retained.rglob("*") if p.is_file()}
        self.run_assessment()
        after = {str(p): p.read_bytes() for p in retained.rglob("*") if p.is_file()}
        self.assertEqual(before, after)

    def test_collector_target_mismatch_does_not_save_a_report(self) -> None:
        collection = copy.deepcopy(self.collection)
        collection["target"]["repository"] = "someone/else"
        with patch.object(assessor, "collect_repository", return_value=collection), \
             patch.object(assessor, "evaluate") as evaluate:
            with self.assertRaises(ValueError):
                assessor.assess_repository("example/real-repo", self.destination)
        evaluate.assert_not_called()
        self.assertFalse((self.destination / "report.json").exists())

    def test_command_exit_codes_distinguish_findings_from_incomplete_data(self) -> None:
        for index, (status, expected) in enumerate([("PASS", 0), ("FAIL", 0), ("MISSING", 2)]):
            findings = [] if status == "PASS" else ["check did not pass"]
            with self.subTest(status=status), \
                 patch.object(assessor, "collect_repository", return_value=self.collection), \
                 patch.object(assessor, "evaluate", return_value={"status": status, "findings": findings}), \
                 patch("sys.stdout", new_callable=io.StringIO):
                code = assessor.main(["--repo", "example/real-repo", "--output-dir", str(self.root / f"exit-{index}")])
            self.assertEqual(code, expected)

    def test_viewer_command_quotes_paths_for_complete_and_incomplete_reports(self) -> None:
        for index, (status, expected) in enumerate([("PASS", 0), ("MISSING", 2)]):
            destination = self.root / f"Bob's assessment $(); {index}"
            with self.subTest(status=status), \
                 patch.object(assessor, "collect_repository", return_value=self.collection), \
                 patch.object(assessor, "evaluate", return_value={"status": status, "findings": []}), \
                 patch("sys.stdout", new_callable=io.StringIO) as stdout:
                code = assessor.main(["--repo", "example/real-repo", "--output-dir", str(destination)])
            self.assertEqual(code, expected)
            command = next(line for line in stdout.getvalue().splitlines() if line.startswith("python3 "))
            self.assertEqual(shlex.split(command), ["python3", "scripts/serve_workspace.py", "--report",
                                                   str(destination / "report.json")])

    def test_preflight_errors_explain_safe_input_problem_without_collection(self) -> None:
        self.destination.mkdir()
        cases = [(["--repo", "not-a-repository"], "OWNER/REPO"),
                 (["--repo", "example/real-repo", "--output-dir", str(self.destination)],
                  "output directory already exists")]
        with patch.object(assessor, "collect_repository") as collect:
            for arguments, expected in cases:
                with self.subTest(arguments=arguments), \
                     patch("sys.stdout", new_callable=io.StringIO) as stdout, \
                     patch("sys.stderr", new_callable=io.StringIO) as stderr:
                    code = assessor.main(arguments)
                self.assertEqual(code, 1)
                self.assertEqual(stdout.getvalue(), "")
                self.assertIn(expected, stderr.getvalue())
        collect.assert_not_called()

    def test_fatal_error_prints_no_credentials_or_success_claim(self) -> None:
        with patch.object(assessor, "collect_repository", side_effect=RuntimeError("secret-token")), \
             patch("sys.stdout", new_callable=io.StringIO) as stdout, \
             patch("sys.stderr", new_callable=io.StringIO) as stderr:
            code = assessor.main(["--repo", "example/real-repo", "--output-dir", str(self.destination)])
        self.assertEqual(code, 1)
        self.assertEqual(stdout.getvalue(), "")
        self.assertNotIn("secret-token", stderr.getvalue())
        self.assertFalse((self.destination / "report.json").exists())

    def test_malformed_evaluator_results_fail_closed(self) -> None:
        for value in [None, {"status": "FAIL", "findings": []}, {"status": "PASS", "findings": ["unexpected"]}, {"status": "PASS", "findings": [123]}]:
            with self.subTest(value=value), patch.object(assessor, "evaluate", return_value=value):
                result = assessor._safe_evaluation("package", self.root / "input.json")
            self.assertEqual(result["status"], "MISSING")


if __name__ == "__main__":
    unittest.main()
