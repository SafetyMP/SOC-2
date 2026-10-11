"""Decision for scripts/iac_gate.sh after a plan has been normalized.

Empty input uses the same rule as engine.evaluator: MISSING, never PASS.
"""
import argparse
import sys

from engine.evaluator import evaluate
from engine.scorer import MISSING, PASS


def decide(package, payload_path, mode):
    """Return (exit_code, message) for one normalized payload.

    warn and enforce both exit non-zero on MISSING. warn still exits 0 when
    the payload has rows and the only outcome is findings.
    """
    result = evaluate(package, payload_path)
    status = result["status"]
    if status == MISSING:
        detail = result.get("error") or "empty input"
        return 1, f"MISSING: {detail}"
    if status == PASS:
        return 0, "PASS: no policy violations"
    lines = ["FINDINGS:"]
    lines.extend(str(item) for item in result.get("findings") or [])
    if mode == "enforce":
        lines.append("BLOCK: enforce mode - plan rejected")
        return 1, "\n".join(lines)
    lines.append("(warn mode - not blocking)")
    return 0, "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Score one normalized IaC payload")
    ap.add_argument("--mode", choices=("warn", "enforce"), default="warn")
    ap.add_argument("--package", default="encryption.at_rest_required")
    ap.add_argument("--payload", required=True)
    args = ap.parse_args(argv)
    code, message = decide(args.package, args.payload, args.mode)
    print(message)
    return code


if __name__ == "__main__":
    sys.exit(main())
