import json
import os
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.iac_gate import decide

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _write(doc):
    fd, path = tempfile.mkstemp(suffix=".json")
    with os.fdopen(fd, "w") as fh:
        json.dump(doc, fh)
    return path


def test_empty_payload_is_missing_not_pass():
    """An empty normalized payload must not take the empty-deny PASS branch."""
    cases = ({}, [], {"data_resources": []})
    for doc in cases:
        path = _write(doc)
        try:
            for mode in ("warn", "enforce"):
                code, message = decide("encryption.at_rest_required", path, mode)
                assert code != 0, (doc, mode, code, message)
                assert message.startswith("MISSING"), (doc, mode, message)
                assert "PASS" not in message
        finally:
            os.remove(path)


def test_iac_gate_script_empty_payload_skips_terraform():
    path = _write({"data_resources": []})
    try:
        env = os.environ.copy()
        env["IAC_PAYLOAD"] = path
        proc = subprocess.run(
            ["bash", "scripts/iac_gate.sh", "warn"],
            cwd=_REPO_ROOT,
            env=env,
            capture_output=True,
            text=True,
        )
        assert proc.returncode != 0, (proc.returncode, proc.stdout, proc.stderr)
        assert "MISSING" in proc.stdout
        assert "PASS" not in proc.stdout
        assert "terraform not found" not in proc.stdout + proc.stderr
    finally:
        os.remove(path)


def main():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"PASS {t.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"FAIL {t.__name__}: {e}")
    print(f"\n{'PASS' if not failed else 'FAIL'}: {len(tests) - failed}/{len(tests)} iac gate tests")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
