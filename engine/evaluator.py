import json
import os
import re
import subprocess

from engine.scorer import PASS, FAIL, MISSING

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CTRL_RE = re.compile(r"^(CTRL-[A-Z]+-\d+):")


def _rel(path):
    return os.path.relpath(os.path.abspath(path), _REPO_ROOT)


def evaluate(package, payload_path, policies_dir="policies"):
    query = f"data.{package}.deny"
    proc = subprocess.run(
        ["opa", "eval", "--format=json", "-d", _rel(policies_dir), "-i", _rel(payload_path), query],
        capture_output=True,
        text=True,
        cwd=_REPO_ROOT,
    )
    if proc.returncode != 0:
        return {"status": MISSING, "findings": [], "error": proc.stderr.strip()}

    try:
        doc = json.loads(proc.stdout)
    except json.JSONDecodeError as e:
        return {"status": MISSING, "findings": [], "error": f"opa output not JSON: {e}"}

    results = doc.get("result", [])
    if not results:
        return {"status": MISSING, "findings": [], "error": f"package '{package}' produced no result"}

    value = results[0]["expressions"][0].get("value", [])
    findings = list(value) if isinstance(value, list) else [str(value)]
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
