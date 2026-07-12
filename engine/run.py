import argparse
import os
from datetime import datetime, timezone

import yaml

from engine import waivers
from engine.catalog import Catalog
from engine.evaluator import evaluate
from engine.locker import LockerClient, build_record
from engine.scorer import score, PASS

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _path(p):
    return p if os.path.isabs(p) else os.path.join(_REPO_ROOT, p)


def load_jobs(jobs_path):
    with open(jobs_path) as fh:
        return yaml.safe_load(fh)["jobs"]


def run(catalog_dir, policies_dir, jobs_path, locker, exceptions_dir="exceptions", as_of=None):
    catalog = Catalog.load(_path(catalog_dir))
    implemented = catalog.implemented_packages(_path(policies_dir))
    jobs = load_jobs(_path(jobs_path))

    verdicts = {}
    evidence = []
    for job in jobs:
        pkg = job["package"]
        payload = _path(job["payload"])
        if pkg not in implemented:
            print(f"SKIP  {pkg} (not implemented)")
            continue
        with open(payload, "rb") as fh:
            payload_bytes = fh.read()
        result = evaluate(pkg, payload, _path(policies_dir))
        sensor = job.get("sensor", pkg.split(".")[0])
        for cid in catalog.pkg_to_controls.get(pkg, []):
            ctrl = catalog.controls[cid]
            record = build_record(ctrl, result, payload_bytes, sensor)
            verdicts[cid] = {"status": result["status"], "findings": result["findings"],
                             "valid_until": record["valid_until"]}
            stored = locker.put(record)
            evidence.append((cid, record["status"], stored))

    waiver_list = waivers.load_exceptions(_path(exceptions_dir))
    decayed = waivers.apply_decay(verdicts, as_of)
    eval_now = as_of or datetime.now(timezone.utc)
    applied = waivers.apply_waivers(verdicts, waiver_list, eval_now)
    report(verdicts, catalog, implemented, evidence, applied=applied, decayed=decayed, as_of=as_of)
    return verdicts


def report(verdicts, catalog, implemented, evidence, applied=None, decayed=None, as_of=None):
    applied = applied or []
    decayed = decayed or []
    scope = list(verdicts.keys())
    s = score(verdicts, catalog, scope=scope)
    all_pkgs = {p for c in catalog.controls.values() for p in c.rego_packages}

    print("\n=== SOC 2 / ISO 27001 Readiness ===")
    print(f"controls evaluated: {len(scope)} wired "
          f"({len(implemented)} Rego packages) of {len(catalog.controls)} catalog controls "
          f"({100 * len(implemented) / max(len(all_pkgs), 1):.0f}% package coverage)")
    if as_of:
        print(f"as-of: {as_of.isoformat()}  (validity-decay simulation)")
    print()

    print("per control:")
    for cid in sorted(scope):
        ctrl = catalog.controls[cid]
        v = verdicts[cid]
        status = v["status"]
        mark = "PASS" if status == PASS else status
        refs = f"[soc2: {','.join(ctrl.soc2)} | iso: {','.join(ctrl.iso27001)}]"
        print(f"  {mark:9} {cid:16} {ctrl.domain:24} crit={ctrl.criticality}  {refs}")
        if status == "EXCEPTION" and v.get("waiver"):
            w = v["waiver"]
            print(f"            -> waived by {w.get('approver')} (expires {w.get('expires')}): {w.get('reason','')[:90]}")
        else:
            for f in v["findings"][:1]:
                line = f if len(f) <= 110 else f[:107] + "..."
                print(f"            -> {line}")
            if len(v["findings"]) > 1:
                print(f"            -> ...and {len(v['findings']) - 1} more")

    print("\nper domain (clean / effective):")
    for domain in sorted(s["domains"]):
        d = s["domains"][domain]
        print(f"  {domain:24} {100 * d['clean_ratio']:6.1f}% / {100 * d['effective_ratio']:6.1f}%"
              f"   ({d['ready_weight']}/{d['total_weight']})")

    ov = s["overall"]
    gap = ov["effective_ratio"] - ov["clean_ratio"]
    print(f"\noverall (wired): clean {100 * ov['clean_ratio']:.1f}% / "
          f"effective {100 * ov['effective_ratio']:.1f}%  ({ov['ready_weight']}/{ov['total_weight']})")
    print(f"risk-acceptance gap (effective - clean): {100 * gap:.1f}%  "
          f"[waivers applied: {len(applied)}, decayed: {len(decayed)}]")

    push_count = sum(1 for _, _, st in evidence if st.get("version_id") and not str(st["version_id"]).startswith("<"))
    dest = f"evidence/out/ (+ {push_count} version-pinned to MinIO)" if push_count else "evidence/out/"
    print(f"evidence: {len(evidence)} records -> {dest}\n")


def _parse_as_of(value):
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise SystemExit(f"invalid --as-of date: {value}")
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def main():
    ap = argparse.ArgumentParser(description="Run the readiness evaluation loop")
    ap.add_argument("--catalog", default="catalog")
    ap.add_argument("--policies", default="policies")
    ap.add_argument("--jobs", default="engine/jobs.yaml")
    ap.add_argument("--exceptions", default="exceptions")
    ap.add_argument("--out", default="evidence/out")
    ap.add_argument("--as-of", default=None, help="simulate decay as of this ISO date (e.g. 2026-09-15)")
    ap.add_argument("--push", action="store_true", help="push evidence records to the MinIO locker")
    args = ap.parse_args()
    locker = LockerClient(out_dir=args.out, push=args.push)
    run(args.catalog, args.policies, args.jobs, locker,
        exceptions_dir=args.exceptions, as_of=_parse_as_of(args.as_of))


if __name__ == "__main__":
    main()
