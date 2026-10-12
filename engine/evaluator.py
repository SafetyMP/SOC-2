import json
import os
import re
import subprocess

from engine.scorer import PASS, FAIL, MISSING

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CTRL_RE = re.compile(r"^(CTRL-[A-Z]+-\d+):")

def _rel(path):
    return os.path.relpath(os.path.abspath(path), _REPO_ROOT)


def payload_is_empty(doc):
    """True when a deny-contains rule would see no rows.

    Matches policies/lib/payload.rego. An empty object, an empty list, or an
    object whose array fields are all empty is not evidence.
    """
    if isinstance(doc, list):
        return len(doc) == 0
    if isinstance(doc, dict):
        arrays = [v for v in doc.values() if isinstance(v, list)]
        if not arrays:
            return True
        return all(len(v) == 0 for v in arrays)
    return True


def _load_payload(payload_path):
    try:
        with open(payload_path) as fh:
            return json.load(fh), None
    except (OSError, json.JSONDecodeError) as e:
        return None, str(e)


def _missing(error, rego_empty=None):
    out = {"status": MISSING, "findings": [], "error": error}
    if rego_empty is not None:
        out["rego_empty"] = rego_empty
    return out


def evaluate(package, payload_path, policies_dir="policies"):
    loaded, load_err = _load_payload(payload_path)
    if load_err:
        return _missing(load_err)

    py_empty = payload_is_empty(loaded)
    query = f'{{"deny": data.{package}.deny, "empty": data.lib.payload.empty}}'
    try:
        proc = subprocess.run(
            ["opa", "eval", "--format=json", "-d", _rel(policies_dir), "-i", _rel(payload_path), query],
            capture_output=True,
            text=True,
            cwd=_REPO_ROOT,
        )
    except FileNotFoundError:
        if py_empty:
            return _missing("empty input")
        return _missing("opa not on PATH")

    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "").strip()
        if py_empty:
            return _missing("empty input")
        return _missing(detail or "opa eval failed")

    try:
        doc = json.loads(proc.stdout)
    except json.JSONDecodeError as e:
        if py_empty:
            return _missing("empty input")
        return _missing(f"opa output not JSON: {e}")

    results = doc.get("result", [])
    if not results:
        if py_empty:
            return _missing("empty input")
        return _missing(f"package '{package}' produced no result")

    value = results[0]["expressions"][0].get("value", {})
    if not isinstance(value, dict):
        if py_empty:
            return _missing("empty input")
        return _missing(f"package '{package}' produced no result")

    raw = value.get("deny", [])
    findings = list(raw) if isinstance(raw, list) else [str(raw)]
    rego_empty = value.get("empty") is True
    if py_empty or rego_empty:
        return _missing("empty input", rego_empty=rego_empty)
    status = PASS if not findings else FAIL
    return {"status": status, "findings": findings}


def attribute_findings(findings, control_ids):
    per = {cid: [] for cid in control_ids}
    for f in findings:
        m = CTRL_RE.match(f)
        tag = m.group(1) if m else None
        for cid in control_ids:
            if tag is None or tag == cid:
                per[cid].append(f)
    return per
