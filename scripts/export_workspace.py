#!/usr/bin/env python3
"""Export the existing fixture evaluator to the static readiness workspace.

This command never connects providers, pushes evidence, or changes source inputs.
Collection timestamps are real; --as-of changes evaluation time, not collection.
"""

from __future__ import annotations

import argparse
from collections import Counter
from contextlib import redirect_stdout
from datetime import datetime, timezone
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from engine.catalog import Catalog
from engine.run import run
from engine.scorer import score

STATUSES = frozenset({"PASS", "FAIL", "MISSING", "EXPIRED", "EXCEPTION"})


class MemoryLocker:
    """The engine's local sink contract, without filesystem or network writes."""

    def __init__(self) -> None:
        self.records: list[dict[str, Any]] = []

    def put(self, record: dict[str, Any]) -> dict[str, None]:
        self.records.append(record)
        return {"local_path": None, "version_id": None}


def iso_time(value: datetime) -> str:
    """Format an aware timestamp for JSON."""
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def parse_as_of(value: str) -> datetime:
    """Accept ISO timestamps and dates, treating a bare date as UTC."""
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise argparse.ArgumentTypeError("Expected an ISO date or timestamp") from error
    return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed


def catalog_metadata(root: Path) -> dict[str, dict[str, Any]]:
    """Retain guidance and ownership that the scorer does not need."""
    metadata: dict[str, dict[str, Any]] = {}
    for path in sorted((root / "catalog").glob("*.yaml")):
        for document in yaml.safe_load_all(path.read_text()):
            rows = document if isinstance(document, list) else [document]
            for row in rows:
                if isinstance(row, dict) and "id" in row:
                    metadata[row["id"]] = row
    return metadata


def source_provenance(root: Path) -> dict[str, str | None]:
    """Pin source links only when evaluation inputs match this checkout's HEAD.

    Referenced procedural documents may live outside the usual source folders.
    Include them explicitly, including ignored/untracked files, because adding a
    document changes a MISSING verdict even when its manifest is unchanged.
    """
    baseline = None

    def git(*arguments: str) -> str:
        return subprocess.run(["git", "--no-optional-locks", *arguments], cwd=root,
                              capture_output=True, text=True, check=True).stdout.strip()

    try:
        if Path(git("rev-parse", "--show-toplevel")).resolve() != root.resolve():
            raise ValueError("The checkout belongs to a different repository")
        baseline = git("rev-parse", "HEAD")
        paths = ["catalog", "policies", "fixtures", "procedural", "exceptions",
                 "engine", "sensors", "evidence", "scripts/export_workspace.py"]
        # Relevant ignored source files must not disappear from provenance checks.
        ignored_patterns = [
            ":(glob)catalog/*.yaml", ":(glob)policies/**/*.rego",
            ":(glob)fixtures/**/*.json", ":(glob)procedural/*.yaml",
            ":(glob)exceptions/*.yaml", ":(glob)engine/*.py",
            ":(glob)engine/*.yaml", ":(glob)sensors/*.py", ":(glob)evidence/*.py",
            ":(literal)scripts/export_workspace.py",
        ]
        for manifest in sorted((root / "procedural").glob("*.yaml")):
            for document in yaml.safe_load_all(manifest.read_text()):
                rows = document if isinstance(document, list) else [document]
                for row in rows:
                    reference = row.get("document_ref") if isinstance(row, dict) else None
                    if not isinstance(reference, str) or not reference:
                        continue
                    candidate = root / reference
                    try:
                        candidate.resolve().relative_to(root.resolve())
                    except ValueError:
                        continue
                    literal = ":(literal)" + reference
                    paths.append(literal)
                    ignored_patterns.append(literal)
        dirty = bool(git("status", "--porcelain=v1", "--untracked-files=all", "--", *paths))
        dirty = dirty or bool(git("ls-files", "--others", "--ignored", "--exclude-standard",
                                 "--", *ignored_patterns))
        return {"source_commit": None if dirty else baseline,
                "source_baseline_commit": baseline,
                "source_state": "modified" if dirty else "clean"}
    except (OSError, subprocess.CalledProcessError, ValueError):
        return {"source_commit": None, "source_baseline_commit": baseline,
                "source_state": "unavailable"}


def build_report(
    catalog: Catalog,
    verdicts: dict[str, dict[str, Any]],
    records: list[dict[str, Any]],
    metadata: dict[str, dict[str, Any]],
    payloads: dict[str, str],
    *,
    generated_at: datetime,
    as_of: datetime,
    source_commit: str | None,
) -> dict[str, Any]:
    """Create a browser snapshot; unwired controls never enter the score."""
    for cid, verdict in verdicts.items():
        if cid not in catalog.controls:
            raise ValueError(f"Unknown evaluated control: {cid}")
        if verdict.get("status") not in STATUSES:
            raise ValueError(f"Unknown verdict for {cid}: {verdict.get('status')}")

    by_control = {record["control_id"]: record for record in records}
    controls = []
    for cid, control in sorted(catalog.controls.items()):
        raw = metadata.get(cid, {})
        verdict = verdicts.get(cid, {})
        record = by_control.get(cid, {})
        source = dict(record.get("source", {}))
        source["payload"] = payloads.get(cid)
        findings = [finding if isinstance(finding, str) else json.dumps(finding, sort_keys=True)
                    for finding in verdict.get("findings", [])]
        controls.append({
            "id": cid,
            "title": control.title,
            "domain": control.domain,
            "status": verdict.get("status", "UNWIRED"),
            "criticality": control.criticality,
            "kind": control.assertion_type,
            "soc2": control.soc2,
            "iso27001": control.iso27001,
            "guidance": raw.get("guidance", "").strip(),
            "owner": raw.get("owner"),
            "source": source,
            "findings": findings,
            "valid_until": verdict.get("valid_until"),
            "collected_at": record.get("collected_at"),
            "fingerprint": record.get("fingerprint"),
            "evidence_id": record.get("evidence_id"),
            "evidence_status": record.get("status"),
            "waiver": verdict.get("waiver"),
        })

    # score() treats an empty scope as the full catalog; make that case explicit.
    scored = score(verdicts, catalog, scope=list(verdicts)) if verdicts else {
        "overall": {"clean_ratio": 0, "effective_ratio": 0,
                    "ready_weight": 0, "total_weight": 0},
        "domains": {},
    }
    overall = scored["overall"]
    effective_weight = sum(catalog.controls[cid].criticality for cid, verdict in verdicts.items()
                           if verdict["status"] in {"PASS", "EXCEPTION"})
    return {
        "schema_version": 1,
        "mode": "fixture",
        "title": "Reference environment",
        "generated_at": iso_time(generated_at),
        "as_of": iso_time(as_of),
        "source_commit": source_commit,
        "summary": {
            "catalog_count": len(controls),
            "wired_count": len(verdicts),
            "unwired_count": len(controls) - len(verdicts),
            "counts": dict(Counter(c["status"] for c in controls)),
            "clean_ratio": overall["clean_ratio"],
            "effective_ratio": overall["effective_ratio"],
            "ready_weight": overall["ready_weight"],
            "clean_weight": overall["ready_weight"],
            "effective_weight": effective_weight,
            "total_weight": overall["total_weight"],
        },
        "domains": scored["domains"],
        "controls": controls,
        "caveats": [
            "Synthetic repository fixtures, not a live assessment or an auditor opinion.",
            "Clean and effective ratios use criticality weights over evaluated controls only.",
            "Exceptions count toward effective readiness, never clean readiness.",
            "Unwired catalog controls are excluded from readiness, not treated as passing.",
            "Procedural checks require a nonempty referenced file and a future review date; they do not verify signatures or document quality.",
            "Fingerprints describe the collected verdict before expiry or waiver overlays; evidence_status preserves that original verdict.",
        ],
    }


def export_report(as_of: datetime | None = None) -> dict[str, Any]:
    """Evaluate repository fixtures without touching the retained evidence folder."""
    generated_at = datetime.now(timezone.utc).replace(microsecond=0)
    evaluated_at = as_of or generated_at
    catalog = Catalog.load(str(ROOT / "catalog"))
    metadata = catalog_metadata(ROOT)
    jobs = yaml.safe_load((ROOT / "engine/jobs.yaml").read_text())["jobs"]
    payloads = {cid: job["payload"] for job in jobs
                for cid in catalog.pkg_to_controls.get(job["package"], [])}
    for cid, raw in metadata.items():
        if "procedural-evidence" in raw.get("sensors", []):
            payloads[cid] = "procedural/manifests.yaml"
    locker = MemoryLocker()
    with tempfile.TemporaryDirectory(prefix="soc2-workspace-") as temporary:
        with redirect_stdout(io.StringIO()):
            verdicts = run(str(ROOT / "catalog"), str(ROOT / "policies"),
                           str(ROOT / "engine/jobs.yaml"), locker,
                           exceptions_dir=str(ROOT / "exceptions"),
                           procedural_dir=str(ROOT / "procedural"),
                           as_of=evaluated_at,
                           merkle_head_path=str(Path(temporary) / "merkle_head.txt"))
    provenance = source_provenance(ROOT)
    report = build_report(catalog, verdicts, locker.records, metadata, payloads,
                          generated_at=generated_at, as_of=evaluated_at,
                          source_commit=provenance["source_commit"])
    report.update(provenance)
    if provenance["source_state"] != "clean":
        report["caveats"].append(
            "Evaluation inputs are modified or Git provenance is unavailable. "
            "Source links are disabled; source_baseline_commit is context, not a claim that inputs match it."
        )
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("workspace-report.json"))
    parser.add_argument("--as-of", type=parse_as_of,
                        help="Simulate validity at this ISO date; collection dates stay truthful")
    args = parser.parse_args()
    report = export_report(args.as_of)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, default=str) + "\n")
    print(f"Exported {report['summary']['wired_count']} evaluated fixture controls to {args.output}")


if __name__ == "__main__":
    main()
