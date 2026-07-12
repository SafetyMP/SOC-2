import glob
import os
from datetime import datetime, timezone

import yaml

from engine.scorer import FAIL, PASS, EXCEPTION, EXPIRED


def _parse(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def load_exceptions(exc_dir="exceptions"):
    out = []
    for path in sorted(glob.glob(os.path.join(exc_dir, "*.yaml"))):
        for doc in yaml.safe_load_all(open(path)):
            if doc is None:
                continue
            docs = doc if isinstance(doc, list) else [doc]
            for w in docs:
                if isinstance(w, dict):
                    out.append(w)
    return out


def _unexpired(w, now):
    expires = _parse(w.get("expires"))
    if expires is None:
        return True
    return expires > now


def apply_waivers(verdicts, waivers, now=None):
    now = now or datetime.now(timezone.utc)
    by_control = {}
    for w in waivers:
        by_control.setdefault(w.get("control_id"), []).append(w)
    applied = []
    for cid, v in verdicts.items():
        if v.get("status") != FAIL:
            continue
        for w in by_control.get(cid, []):
            if _unexpired(w, now):
                v["status"] = EXCEPTION
                v["waiver"] = {
                    "id": w.get("id"),
                    "reason": w.get("reason"),
                    "approver": w.get("approver"),
                    "expires": w.get("expires"),
                }
                applied.append(cid)
                break
    return applied


def apply_decay(verdicts, as_of=None):
    as_of = as_of or datetime.now(timezone.utc)
    decayed = []
    for cid, v in verdicts.items():
        if v.get("status") != PASS:
            continue
        valid_until = _parse(v.get("valid_until"))
        if valid_until is not None and valid_until < as_of:
            v["status"] = EXPIRED
            decayed.append(cid)
    return decayed
