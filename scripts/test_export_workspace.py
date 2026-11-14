"""Contract and integration checks for browser report export."""

from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from export_workspace import ROOT, build_report, export_report, source_provenance
from engine.catalog import Catalog, Control


class ExportContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.now = datetime(2026, 11, 14, tzinfo=timezone.utc)
        self.catalog = Catalog([
            Control({"id": "CTRL-A-001", "criticality": 3}, "access"),
            Control({"id": "CTRL-B-001", "criticality": 2}, "access"),
            Control({"id": "CTRL-C-001", "criticality": 1}, "access"),
        ])

    def report(self, verdicts: dict, records: list | None = None) -> dict:
        return build_report(self.catalog, verdicts, records or [], {}, {},
                            generated_at=self.now, as_of=self.now, source_commit=None)

    def test_exceptions_are_effective_only_and_unwired_excluded(self) -> None:
        report = self.report({"CTRL-A-001": {"status": "PASS"},
                              "CTRL-B-001": {"status": "EXCEPTION"}})
        summary = report["summary"]
        self.assertEqual(summary["clean_ratio"], 3 / 5)
        self.assertEqual(summary["effective_ratio"], 1)
        self.assertEqual(summary["effective_weight"], 5)
        self.assertEqual(summary["unwired_count"], 1)
        self.assertEqual(report["controls"][2]["status"], "UNWIRED")

    def test_missing_and_expired_are_never_ready(self) -> None:
        report = self.report({"CTRL-A-001": {"status": "MISSING"},
                              "CTRL-B-001": {"status": "EXPIRED"}})
        self.assertEqual(report["summary"]["clean_ratio"], 0)
        self.assertEqual(report["summary"]["effective_ratio"], 0)
        self.assertEqual(report["summary"]["total_weight"], 5)

    def test_empty_evaluation_does_not_score_entire_catalog(self) -> None:
        report = self.report({})
        self.assertEqual(report["summary"]["total_weight"], 0)
        self.assertEqual(report["summary"]["wired_count"], 0)
        self.assertEqual(report["summary"]["unwired_count"], 3)

    def test_unknown_verdict_rejected(self) -> None:
        with self.assertRaises(ValueError):
            self.report({"CTRL-A-001": {"status": "LOOKS_GOOD"}})
        with self.assertRaises(ValueError):
            self.report({"CTRL-NOT-IN-CATALOG": {"status": "PASS"}})

    def test_original_evidence_separate_from_waiver_overlay(self) -> None:
        report = self.report(
            {"CTRL-A-001": {"status": "EXCEPTION", "waiver": {"reason": "Review pending"}}},
            [{"control_id": "CTRL-A-001", "status": "FAIL", "fingerprint": "sha256:original"}],
        )
        control = report["controls"][0]
        self.assertEqual(control["status"], "EXCEPTION")
        self.assertEqual(control["evidence_status"], "FAIL")
        self.assertEqual(control["fingerprint"], "sha256:original")

    def test_missing_evaluator_failures_are_strings_in_browser_contract(self) -> None:
        report = self.report({"CTRL-A-001": {"status": "MISSING",
                                            "findings": [{"note": "opa unavailable"}]}})
        self.assertIsInstance(report["controls"][0]["findings"][0], str)


class ExportIntegrationTests(unittest.TestCase):
    def test_missing_evaluator_and_documents_fail_closed_without_retained_writes(self) -> None:
        evidence_dir = ROOT / "evidence/out"
        before = {str(path): path.read_bytes() for path in evidence_dir.rglob("*") if path.is_file()}
        with patch("engine.run.evaluate", return_value={"status": "MISSING", "error": "test outage"}):
            report = export_report(datetime(2026, 11, 14, tzinfo=timezone.utc))
        after = {str(path): path.read_bytes() for path in evidence_dir.rglob("*") if path.is_file()}
        self.assertEqual(before, after)
        self.assertEqual(report["summary"]["wired_count"], 20)
        self.assertEqual(report["summary"]["catalog_count"], 37)
        self.assertEqual(report["summary"]["counts"], {"MISSING": 20, "UNWIRED": 17})
        self.assertEqual(report["summary"]["clean_ratio"], 0)
        self.assertEqual(report["mode"], "fixture")
        self.assertEqual(report["as_of"], "2026-11-14T00:00:00Z")
        self.assertTrue(all(c["collected_at"] for c in report["controls"] if c["status"] != "UNWIRED"))
        json.dumps(report)

    def test_committed_sample_scores_and_scope_are_internally_consistent(self) -> None:
        sample = json.loads((ROOT / "demo/data/sample-report.json").read_text())
        wired = [c for c in sample["controls"] if c["status"] != "UNWIRED"]
        summary = sample["summary"]
        total = sum(c["criticality"] for c in wired)
        clean = sum(c["criticality"] for c in wired if c["status"] == "PASS")
        effective = sum(c["criticality"] for c in wired if c["status"] in {"PASS", "EXCEPTION"})
        self.assertEqual(summary["wired_count"], len(wired))
        self.assertEqual(summary["catalog_count"], len(sample["controls"]))
        self.assertEqual(summary["clean_ratio"], clean / total)
        self.assertEqual(summary["effective_ratio"], effective / total)
        self.assertTrue(all(c["fingerprint"].startswith("sha256:") for c in wired))
        self.assertEqual(sample["mode"], "fixture")


class SourceProvenanceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="soc2-provenance-test-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        (self.root / "fixtures").mkdir()
        (self.root / "fixtures/input.json").write_text('{"sample": true}\n')
        (self.root / "procedural").mkdir()
        (self.root / "procedural/manifests.yaml").write_text(
            "- control_id: CTRL-GOV-001\n  document_ref: governance/policy.md\n")
        (self.root / ".gitignore").write_text("private/\n")
        self.git("init", "--quiet")
        self.git("add", ".")
        self.git("-c", "user.name=Test", "-c", "user.email=test@example.invalid",
                 "commit", "--quiet", "-m", "Fixture baseline")

    def git(self, *arguments: str) -> str:
        return subprocess.run(["git", *arguments], cwd=self.root, capture_output=True,
                              text=True, check=True).stdout.strip()

    def test_clean_inputs_pin_head_and_unrelated_ui_changes_do_not_disable_it(self) -> None:
        (self.root / "demo").mkdir()
        (self.root / "demo/index.html").write_text("Unrelated interface")
        result = source_provenance(self.root)
        self.assertEqual(result["source_commit"], self.git("rev-parse", "HEAD"))
        self.assertEqual(result["source_state"], "clean")

    def test_changed_fixture_retains_baseline_without_claiming_exact_source(self) -> None:
        (self.root / "fixtures/input.json").write_text('{"sample": false}\n')
        result = source_provenance(self.root)
        self.assertIsNone(result["source_commit"])
        self.assertEqual(result["source_baseline_commit"], self.git("rev-parse", "HEAD"))
        self.assertEqual(result["source_state"], "modified")

    def test_untracked_referenced_document_disables_commit_links(self) -> None:
        (self.root / "governance").mkdir()
        (self.root / "governance/policy.md").write_text("New sample document")
        self.assertIsNone(source_provenance(self.root)["source_commit"])

    def test_ignored_referenced_document_disables_commit_links(self) -> None:
        manifest = self.root / "procedural/manifests.yaml"
        manifest.write_text("- control_id: CTRL-GOV-001\n  document_ref: private/policy.md\n")
        self.git("add", ".")
        self.git("-c", "user.name=Test", "-c", "user.email=test@example.invalid",
                 "commit", "--quiet", "-m", "Reference ignored document")
        (self.root / "private").mkdir()
        (self.root / "private/policy.md").write_text("New ignored sample document")
        self.assertEqual(source_provenance(self.root)["source_state"], "modified")

    def test_missing_git_is_a_valid_unpinned_source(self) -> None:
        with patch("export_workspace.subprocess.run", side_effect=FileNotFoundError):
            result = source_provenance(self.root)
        self.assertIsNone(result["source_commit"])
        self.assertEqual(result["source_state"], "unavailable")

    def test_nested_zip_directory_does_not_claim_parent_repository_head(self) -> None:
        nested = self.root / "downloaded-project"
        nested.mkdir()
        self.assertEqual(source_provenance(nested)["source_state"], "unavailable")


if __name__ == "__main__":
    unittest.main()
