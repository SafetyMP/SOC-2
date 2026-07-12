import argparse
import json
import os

import yaml

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


def run(catalog_dir, policies_dir, jobs_path, locker):
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
            verdicts[cid] = {"status": result["status"], "findings": result["findings"]}
            record = build_record(ctrl, result, payload_bytes, sensor)
            stored = locker.put(record)
            evidence.append((cid, record["status"], stored))

    report(verdicts, catalog, implemented, evidence)
    return verdicts


def report(verdicts, catalog, implemented, evidence):
    scope = list(verdicts.keys())
    s = score(verdicts, catalog, scope=scope)
    all_pkgs = {p for c in catalog.controls.values() for p in c.rego_packages}

    print("\n=== SOC 2 / ISO 27001 Readiness ===")
    print(f"controls evaluated: {len(scope)} wired "
          f"({len(implemented)} Rego packages) of {len(catalog.controls)} catalog controls "
          f"({100 * len(implemented) / max(len(all_pkgs), 1):.0f}% package coverage)\n")

    print("per control:")
    for cid in sorted(scope):
        ctrl = catalog.controls[cid]
        v = verdicts[cid]
        status = v["status"]
        mark = "PASS" if status == PASS else status
        refs = f"[soc2: {','.join(ctrl.soc2)} | iso: {','.join(ctrl.iso27001)}]"
        print(f"  {mark:9} {cid:16} {ctrl.domain:24} crit={ctrl.criticality}  {refs}")
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
    print(f"\noverall (wired): clean {100 * ov['clean_ratio']:.1f}% / "
          f"effective {100 * ov['effective_ratio']:.1f}%  ({ov['ready_weight']}/{ov['total_weight']})")

    push_count = sum(1 for _, _, st in evidence if st.get("version_id") and not str(st["version_id"]).startswith("<"))
    dest = f"evidence/out/ (+ {push_count} version-pinned to MinIO)" if push_count else "evidence/out/"
    print(f"evidence: {len(evidence)} records -> {dest}\n")


def main():
    ap = argparse.ArgumentParser(description="Run the readiness evaluation loop")
    ap.add_argument("--catalog", default="catalog")
    ap.add_argument("--policies", default="policies")
    ap.add_argument("--jobs", default="engine/jobs.yaml")
    ap.add_argument("--out", default="evidence/out")
    ap.add_argument("--push", action="store_true", help="push evidence records to the MinIO locker")
    args = ap.parse_args()
    locker = LockerClient(out_dir=args.out, push=args.push)
    run(args.catalog, args.policies, args.jobs, locker)


if __name__ == "__main__":
    main()
