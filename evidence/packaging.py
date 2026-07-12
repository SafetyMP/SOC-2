import argparse
import glob
import json
import os
from collections import defaultdict
from datetime import datetime, timezone

from engine import waivers
from engine.catalog import Catalog
from engine.scorer import PASS, FAIL, EXCEPTION, EXPIRED, MISSING

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

_LABELS = {
    PASS: "Met", FAIL: "Not met", EXCEPTION: "Exception (waivered)",
    EXPIRED: "Expired", MISSING: "Not evaluated",
}

SOC2_FAMILIES = [
    ("CC1", "Control Environment"), ("CC2", "Communication & Information"),
    ("CC3", "Risk Assessment"), ("CC4", "Monitoring Activities"),
    ("CC5", "Control Activities"), ("CC6", "Logical & Physical Access"),
    ("CC7", "System Operations"), ("CC8", "Change Management"),
    ("CC9", "Risk Mitigation"), ("A1", "Availability"), ("C1", "Confidentiality"),
    ("PI1", "Processing Integrity"),
    ("P1", "Privacy — Notice"), ("P2", "Choice & Consent"), ("P3", "Collection"),
    ("P4", "Use, Retention & Disposal"), ("P5", "Access"), ("P6", "Disclosure"),
    ("P7", "Quality & Monitoring"), ("P8", "Enforcement"),
]
SOC2_FAMILY_ORDER = {f: i for i, (f, _) in enumerate(SOC2_FAMILIES)}
ISO_THEMES = [("A.5", "Organizational"), ("A.6", "People"), ("A.7", "Physical"), ("A.8", "Technological")]


def _path(p):
    return p if os.path.isabs(p) else os.path.join(_REPO_ROOT, p)


def load_latest_evidence(out_dir):
    latest = {}
    for path in glob.glob(os.path.join(out_dir, "*", "*.json")):
        rec = json.load(open(path))
        cid = rec.get("control_id")
        if not cid:
            continue
        if cid not in latest or rec.get("collected_at", "") > latest[cid].get("collected_at", ""):
            latest[cid] = rec
    return latest


def criterion_status(statuses):
    if not statuses:
        return "Not addressed"
    if FAIL in statuses:
        return "Partial" if PASS in statuses else "Not met"
    if all(s == PASS for s in statuses):
        return "Met"
    if PASS in statuses:
        return "Partial"
    if EXCEPTION in statuses:
        return "Exception (waivered)"
    return "Not evaluated"


def _soc2_family(ref):
    return ref.split(".")[0]


def _iso_theme(ref):
    parts = ref.split(".")
    return ".".join(parts[:2]) if len(parts) >= 2 else ref


def current_verdicts(catalog, latest, exc_dir, as_of=None):
    verdicts = {}
    for cid in catalog.controls:
        rec = latest.get(cid)
        if rec:
            verdicts[cid] = {
                "status": rec.get("status", MISSING),
                "findings": rec.get("verdict_detail", {}).get("findings", []),
                "valid_until": rec.get("valid_until"),
            }
    waivers.apply_decay(verdicts, as_of)
    waivers.apply_waivers(verdicts, waivers.load_exceptions(_path(exc_dir)), as_of or datetime.now(timezone.utc))
    return verdicts


def build(catalog, verdicts):
    soc2 = defaultdict(list)
    iso = defaultdict(list)
    for cid, ctrl in catalog.controls.items():
        status = verdicts.get(cid, {}).get("status", MISSING)
        for ref in ctrl.soc2:
            soc2[ref].append((cid, status))
        for ref in ctrl.iso27001:
            iso[ref].append((cid, status))
    return soc2, iso


def _summary(soc2, iso, catalog, verdicts):
    crit_status = {ref: criterion_status([s for _, s in ctrls]) for ref, ctrls in soc2.items()}
    iso_status = {ref: criterion_status([s for _, s in ctrls]) for ref, ctrls in iso.items()}
    evaluated = sum(1 for c in catalog.controls if c in verdicts)
    return {
        "controls_total": len(catalog.controls),
        "controls_evaluated": evaluated,
        "coverage_pct": round(100 * evaluated / max(len(catalog.controls), 1), 1),
        "soc2_criteria_addressed": len(soc2),
        "soc2_met": sum(1 for v in crit_status.values() if v == "Met"),
        "soc2_not_met": sum(1 for v in crit_status.values() if v == "Not met"),
        "soc2_partial": sum(1 for v in crit_status.values() if v == "Partial"),
        "iso_controls_addressed": len(iso),
        "iso_met": sum(1 for v in iso_status.values() if v == "Met"),
        "iso_not_met": sum(1 for v in iso_status.values() if v == "Not met"),
    }


def render_markdown(catalog, verdicts, latest, as_of_label):
    soc2, iso = build(catalog, verdicts)
    summary = _summary(soc2, iso, catalog, verdicts)
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    lines = [
        "# SOC 2 / ISO 27001 Readiness — Auditor Package",
        "",
        f"_Generated: {now}  ·  Source: evidence locker (local)  ·  {as_of_label}_",
        "",
        "## Summary",
        "",
        f"- Controls in catalog: **{summary['controls_total']}**  ·  evaluated: **{summary['controls_evaluated']}**  ·  coverage: **{summary['coverage_pct']}%**",
        f"- SOC 2 criteria addressed: **{summary['soc2_criteria_addressed']}** (Met {summary['soc2_met']} · Partial {summary['soc2_partial']} · Not met {summary['soc2_not_met']})",
        f"- ISO 27001:2022 controls addressed: **{summary['iso_controls_addressed']}** (Met {summary['iso_met']} · Not met {summary['iso_not_met']})",
        "",
        "## SOC 2 — Trust Services Criteria",
        "",
    ]

    grouped = defaultdict(list)
    for ref, ctrls in soc2.items():
        grouped[_soc2_family(ref)].append((ref, ctrls))
    for fam, _ in SOC2_FAMILIES:
        if fam not in grouped:
            continue
        title = dict(SOC2_FAMILIES)[fam]
        lines.append(f"### {fam} — {title}")
        lines.append("")
        lines.append("| Criterion | Control(s) | Status | Evidence |")
        lines.append("|---|---|---|---|")
        for ref, ctrls in sorted(grouped[fam]):
            cstat = criterion_status([s for _, s in ctrls])
            controls = ", ".join(c for c, _ in ctrls)
            ev = _evidence_cell(ctrls, latest)
            lines.append(f"| {ref} | {controls} | {cstat} | {ev} |")
        lines.append("")

    lines += ["## ISO/IEC 27001:2022 — Statement of Applicability", ""]
    igrouped = defaultdict(list)
    for ref, ctrls in iso.items():
        igrouped[_iso_theme(ref)].append((ref, ctrls))
    for theme, title in ISO_THEMES:
        if theme not in igrouped:
            continue
        lines.append(f"### {theme} — {title} controls")
        lines.append("")
        lines.append("| Annex control | Control(s) | Applicable | Status | Evidence |")
        lines.append("|---|---|---|---|---|")
        for ref, ctrls in sorted(igrouped[theme]):
            cstat = criterion_status([s for _, s in ctrls])
            controls = ", ".join(c for c, _ in ctrls)
            ev = _evidence_cell(ctrls, latest)
            lines.append(f"| {ref} | {controls} | Yes | {cstat} | {ev} |")
        lines.append("")

    lines.append("## Control evidence index")
    lines.append("")
    lines.append("| Control | Status | Collected | Valid until | Fingerprint |")
    lines.append("|---|---|---|---|---|")
    for cid in sorted(catalog.controls):
        rec = latest.get(cid)
        status = _LABELS.get(verdicts.get(cid, {}).get("status", MISSING), "Not evaluated")
        if rec:
            lines.append(f"| {cid} | {status} | {rec.get('collected_at','-')} | {rec.get('valid_until','-')} | `{(rec.get('fingerprint','-'))[:18]}` |")
        else:
            lines.append(f"| {cid} | {status} | — | — | — |")
    lines.append("")
    return "\n".join(lines)


def _evidence_cell(ctrls, latest):
    refs = []
    for cid, _ in ctrls:
        rec = latest.get(cid)
        if rec:
            refs.append(f"`{(rec.get('fingerprint',''))[:12]}`")
    return " ".join(refs) if refs else "—"


def render_manifest(catalog, verdicts, latest, as_of_label):
    soc2, iso = build(catalog, verdicts)
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    def view(refmap):
        return {ref: {"status": criterion_status([s for _, s in c]), "controls": [{"id": c, "status": s} for c, s in c]}
                for ref, c in refmap.items()}
    return {
        "generated_at": now,
        "source": "evidence locker (local)",
        "as_of": as_of_label,
        "summary": _summary(soc2, iso, catalog, verdicts),
        "soc2": view(soc2),
        "iso27001": view(iso),
        "evidence": {cid: {"evidence_id": r.get("evidence_id"), "status": r.get("status"),
                           "collected_at": r.get("collected_at"), "valid_until": r.get("valid_until"),
                           "fingerprint": r.get("fingerprint")}
                     for cid, r in latest.items()},
    }


def main():
    ap = argparse.ArgumentParser(description="Package evidence into SOC 2 + ISO 27001 auditor artifacts")
    ap.add_argument("--catalog", default="catalog")
    ap.add_argument("--evidence", default="evidence/out")
    ap.add_argument("--exceptions", default="exceptions")
    ap.add_argument("--write", default="evidence/packages")
    ap.add_argument("--as-of", default=None)
    args = ap.parse_args()

    catalog = Catalog.load(_path(args.catalog))
    latest = load_latest_evidence(_path(args.evidence))
    as_of = None
    label = "current"
    if args.as_of:
        as_of = datetime.fromisoformat(args.as_of.replace("Z", "+00:00"))
        if as_of.tzinfo is None:
            as_of = as_of.replace(tzinfo=timezone.utc)
        label = f"as-of {args.as_of}"

    verdicts = current_verdicts(catalog, latest, args.exceptions, as_of)
    md = render_markdown(catalog, verdicts, latest, label)
    manifest = render_manifest(catalog, verdicts, latest, label)

    out_dir = _path(args.write)
    os.makedirs(out_dir, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    md_path = os.path.join(out_dir, f"auditor-package-{stamp}.md")
    json_path = os.path.join(out_dir, f"auditor-package-{stamp}.json")
    with open(md_path, "w") as fh:
        fh.write(md)
    with open(json_path, "w") as fh:
        json.dump(manifest, fh, indent=2, sort_keys=True)
    print(md)
    print(f"\n_wrote {md_path} and {json_path}_")


if __name__ == "__main__":
    main()
