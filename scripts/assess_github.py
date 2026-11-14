#!/usr/bin/env python3
"""Assess one real GitHub repository, keeping reports and credentials local.

Authentication is provided by the local GitHub CLI. This command does not accept
credentials, upload evidence, modify repositories, or load demonstration inputs.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import shlex
import sys
import tempfile
from typing import Any
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from engine.catalog import Catalog
from engine.evaluator import attribute_findings, evaluate
from engine.locker import build_record, parse_validity
from export_workspace import build_report, catalog_metadata, iso_time

JOBS = {
    "branch_protection": ("change_mgmt.branch_protection_enforced", ("CTRL-CHG-001", "CTRL-CHG-002")),
    "ci": ("change_mgmt.ci_required", ("CTRL-CHG-008",)),
}
CONTROL_IDS = ["CTRL-CHG-001", "CTRL-CHG-002", "CTRL-CHG-008"]
CHECK_SCOPE = {
    "CTRL-CHG-001": "Default branch protection and force-push settings only; does not prove every change used a pull request or that privileged bypass is impossible.",
    "CTRL-CHG-002": "Configured approving-review count and required status checks only; does not prove reviewers approved each change or that checks succeeded.",
    "CTRL-CHG-008": "Presence of an active version-controlled GitHub Actions workflow only; does not prove deployment reproducibility, successful runs, or absence of manual deployments.",
}
LIMITATIONS = [
    "This is a real, point-in-time GitHub configuration assessment, not a sample or audit opinion.",
    "Only three GitHub-backed controls are in scope; every other catalog control is not evaluated.",
    "No fixture payloads, procedural manifests, or sample waivers are used.",
    "Configuration checks do not establish operating effectiveness or full SOC 2 compliance.",
    "Unreadable or unsupported settings are MISSING, not evidence that a control passed or failed.",
]
REPOSITORY_PATTERN = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})/[A-Za-z0-9_.-]{1,100}\Z")


class LocalInputError(ValueError):
    """A fixed, safe diagnostic for local inputs before any GitHub collection."""


def validate_repository(repo: str) -> str:
    """Accept a literal GitHub.com repository identifier, never a URL or option."""
    if not isinstance(repo, str) or not REPOSITORY_PATTERN.fullmatch(repo):
        raise LocalInputError("Use one GitHub repository in OWNER/REPO form.")
    if repo.split("/", 1)[1] in {".", ".."}:
        raise LocalInputError("Use one GitHub repository in OWNER/REPO form.")
    return repo


def collect_repository(repo: str) -> dict[str, Any]:
    """Load the dedicated real-data collector without involving the fixture runner."""
    from sensors.github_assessment import collect_repository as collect
    return collect(repo)


def default_output_directory(repo: str) -> Path:
    """Choose a fresh directory outside the source checkout."""
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return Path.home() / ".local/share/soc2-workspace/assessments" / f"{stamp}-{repo.replace('/', '-')}-{uuid.uuid4().hex[:8]}"


def prepare_output_directory(path: Path) -> Path:
    """Create a private fresh directory, refusing source trees and symlinks."""
    path = path.expanduser()
    if not path.is_absolute():
        raise LocalInputError("The output directory must be an absolute path outside a Git checkout.")
    if path.exists() or path.is_symlink():
        raise LocalInputError("The output directory already exists; choose a new directory.")
    for parent in [path, *path.parents]:
        if parent.is_symlink():
            raise LocalInputError("The output path must not contain symlinks.")
        if (parent / ".git").exists():
            raise LocalInputError("Keep real evidence outside Git checkouts and public demo directories.")
    try:
        path.resolve().relative_to(ROOT.resolve())
    except ValueError:
        pass
    else:
        raise LocalInputError("Keep real evidence outside this source checkout.")
    old_umask = os.umask(0o077)
    try:
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        path.mkdir(mode=0o700)
    finally:
        os.umask(old_umask)
    return path


def _write_private_json(path: Path, value: Any) -> None:
    data = json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True) + "\n"
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        handle.write(data)


def _collection_time(value: Any) -> datetime:
    if not isinstance(value, str):
        raise ValueError("Collector did not provide a collection timestamp.")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("Collector timestamp must include a timezone.")
    return parsed.astimezone(timezone.utc).replace(microsecond=0)


def _safe_evaluation(package: str, payload_path: Path) -> dict[str, Any]:
    """Convert runtime failures to a fixed message; never retain subprocess output."""
    try:
        result = evaluate(package, str(payload_path), str(ROOT / "policies"))
    except (OSError, ValueError, KeyError, TypeError, IndexError):
        result = {"status": "MISSING"}
    if not isinstance(result, dict):
        result = {}
    status = result.get("status")
    findings = result.get("findings")
    if (status not in {"PASS", "FAIL"} or not isinstance(findings, list)
            or not all(isinstance(f, str) for f in findings)
            or (status == "FAIL" and not findings) or (status == "PASS" and findings)):
        return {"status": "MISSING", "findings": ["Local policy evaluation was unavailable or returned invalid output. Check the local OPA installation and rerun."]}
    return {"status": status, "findings": findings}


def assess_repository(repo: str, output_dir: Path | None = None) -> tuple[dict[str, Any], Path, bool]:
    """Collect one repository and save private evidence, returning incomplete status."""
    repo = validate_repository(repo)
    destination = prepare_output_directory(output_dir or default_output_directory(repo))
    collection = collect_repository(repo)
    collected_at = _collection_time(collection["collected_at"])
    target = {key: collection["target"].get(key)
              for key in ("host", "repository", "branch", "commit", "visibility")}
    if target.get("host") != "github.com" or target.get("repository", "").lower() != repo.lower():
        raise ValueError("Collector target did not match the requested repository.")
    catalog = Catalog.load(str(ROOT / "catalog"))
    metadata = catalog_metadata(ROOT)
    verdicts: dict[str, dict[str, Any]] = {}
    records: list[dict[str, Any]] = []
    payloads: dict[str, Any] = {}
    incomplete = False
    with tempfile.TemporaryDirectory(prefix="soc2-github-evaluation-") as temporary:
        for key, (package, ids) in JOBS.items():
            payload = collection["payloads"].get(key)
            payloads[key] = payload
            payload_bytes = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
            if payload is None or collection.get("errors", {}).get(key):
                result = {"status": "MISSING", "findings": [f"GitHub {key.replace('_', ' ')} settings could not be read reliably. Review local collection diagnostics and permissions, then rerun."]}
            else:
                payload_path = Path(temporary) / f"{key}.json"
                _write_private_json(payload_path, payload)
                result = _safe_evaluation(package, payload_path)
            incomplete = incomplete or result["status"] == "MISSING"
            attributed = attribute_findings(result["findings"], ids)
            for cid in ids:
                findings = attributed[cid]
                status = "MISSING" if result["status"] == "MISSING" else ("FAIL" if findings else "PASS")
                verdict = {"status": status, "findings": findings}
                record = build_record(catalog.controls[cid], verdict, payload_bytes, "github-api")
                record["collected_at"] = iso_time(collected_at)
                record["valid_until"] = iso_time(collected_at + parse_validity(catalog.controls[cid].evidence_validity))
                record["source"]["payload"] = "evidence.json"
                record["source"]["query"] = f"opa eval data.{package}.deny"
                verdicts[cid] = {**verdict, "valid_until": record["valid_until"]}
                records.append(record)
    report = build_report(catalog, verdicts, records, metadata,
                          {cid: "evidence.json" for cid in CONTROL_IDS},
                          generated_at=collected_at, as_of=collected_at, source_commit=None)
    limitations = LIMITATIONS + list(collection.get("limitations", []))
    report.update({"mode": "github", "title": repo, "target": target,
                   "assessment": {"kind": "github-repository", "control_ids": CONTROL_IDS,
                                  "limitations": limitations, "incomplete": incomplete},
                   "caveats": limitations, "source_state": "local-github-collection"})
    for control in report["controls"]:
        if control["id"] in CHECK_SCOPE:
            control["check_scope"] = CHECK_SCOPE[control["id"]]
        else:
            control["scope_reason"] = "Outside this GitHub repository assessment. No source was collected for this control."
    evidence = {"schema_version": 1, "mode": "github", "target": target,
                "collected_at": iso_time(collected_at), "normalized_payloads": payloads,
                "observations": collection.get("observations", []),
                "collection_errors": collection.get("errors", {}), "records": records,
                "limitations": limitations}
    _write_private_json(destination / "evidence.json", evidence)
    _write_private_json(destination / "report.json", report)
    return report, destination, incomplete


def main(argv: list[str] | None = None) -> int:
    """Write a real assessment; exit 2 when its evidence is incomplete."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True, help="Explicit GitHub.com OWNER/REPO; no organization-wide collection")
    parser.add_argument("--output-dir", type=Path, help="New absolute directory outside source checkouts (default: ~/.local/share/soc2-workspace/assessments/…)")
    args = parser.parse_args(argv)
    try:
        report, destination, incomplete = assess_repository(args.repo, args.output_dir)
    except LocalInputError as error:
        print(f"Assessment could not start. {error}", file=sys.stderr)
        return 1
    except (OSError, ValueError, KeyError, TypeError, RuntimeError):
        # Do not expose GitHub response bodies, subprocess stderr, or environment.
        print("Assessment could not complete. Check OWNER/REPO, local gh authentication, OPA, and a new writable output directory outside Git checkouts.", file=sys.stderr)
        return 1
    print(f"Saved real GitHub assessment ({report['summary']['wired_count']} scoped controls) locally: {destination / 'report.json'}")
    print("Evidence and credentials were not uploaded to the workspace or demo.")
    print("Open this report in the local workspace (run from the project directory):")
    print(f"python3 scripts/serve_workspace.py --report {shlex.quote(str(destination / 'report.json'))}")
    if incomplete:
        print("Assessment is incomplete: unreadable settings or unavailable policy evaluation are marked MISSING. See local evidence.json diagnostics.")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
