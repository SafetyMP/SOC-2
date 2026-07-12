import argparse
import glob
import json
import os
from datetime import datetime, timezone

import yaml

from engine.scorer import PASS, EXPIRED, MISSING


def _parse(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def load_manifests(manifest_dir):
    out = []
    for path in sorted(glob.glob(os.path.join(manifest_dir, "*.yaml"))):
        for doc in yaml.safe_load_all(open(path)):
            if doc is None:
                continue
            docs = doc if isinstance(doc, list) else [doc]
            for m in docs:
                if isinstance(m, dict):
                    out.append(m)
    return out


def evaluate(manifest, now):
    raw_due = manifest.get("next_review_due")
    due = _parse(raw_due)
    if due is None:
        return {"status": MISSING,
                "findings": ["manifest missing or unparseable next_review_due"],
                "valid_until": str(raw_due) if raw_due is not None else None}
    valid_until = due.isoformat().replace("+00:00", "Z")
    if due > now:
        return {"status": PASS, "findings": [], "valid_until": valid_until}
    return {"status": EXPIRED,
            "findings": [f"review overdue (due {valid_until})"],
            "valid_until": valid_until}


def collect(manifest_dir, now=None):
    now = now or datetime.now(timezone.utc)
    out = {}
    for m in load_manifests(manifest_dir):
        cid = m.get("control_id")
        if not cid:
            continue
        ev = evaluate(m, now)
        ev["_manifest"] = m
        out[cid] = ev
    return out


def main():
    ap = argparse.ArgumentParser(description="Procedural-evidence sensor")
    ap.add_argument("--dir", default="procedural")
    ap.add_argument("--as-of", default=None)
    args = ap.parse_args()
    now = None
    if args.as_of:
        now = _parse(args.as_of) or datetime.now(timezone.utc)
    verdicts = collect(args.dir, now)
    print(json.dumps({cid: {"status": v["status"], "findings": v["findings"],
                            "valid_until": v["valid_until"]}
                      for cid, v in verdicts.items()}, indent=2))


if __name__ == "__main__":
    main()
