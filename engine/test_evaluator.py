import json
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.evaluator import attribute_findings, evaluate, payload_is_empty
from engine.scorer import FAIL, MISSING, PASS


def test_tagged_findings_attributed_to_their_control():
    findings = ["CTRL-CHG-002: needs 2 reviewers", "CTRL-ACCESS-001: no MFA"]
    per = attribute_findings(findings, ["CTRL-CHG-001", "CTRL-CHG-002", "CTRL-ACCESS-001"])
    assert per["CTRL-CHG-002"] == ["CTRL-CHG-002: needs 2 reviewers"]
    assert per["CTRL-ACCESS-001"] == ["CTRL-ACCESS-001: no MFA"]
    assert per["CTRL-CHG-001"] == []


def test_shared_package_splits_controls():
    findings = ["CTRL-CHG-002: needs 2 reviewers"]
    per = attribute_findings(findings, ["CTRL-CHG-001", "CTRL-CHG-002"])
    assert per["CTRL-CHG-001"] == []
    assert per["CTRL-CHG-002"] == ["CTRL-CHG-002: needs 2 reviewers"]


def test_untagged_finding_applies_to_all_controls():
    findings = ["something is wrong"]
    per = attribute_findings(findings, ["CTRL-A-001", "CTRL-A-002"])
    assert per["CTRL-A-001"] == ["something is wrong"]
    assert per["CTRL-A-002"] == ["something is wrong"]


def test_empty_findings():
    per = attribute_findings([], ["CTRL-A-001"])
    assert per["CTRL-A-001"] == []


def test_payload_is_empty_for_no_rows():
    assert payload_is_empty({}) is True
    assert payload_is_empty([]) is True
    assert payload_is_empty({"principals": []}) is True
    assert payload_is_empty({"repositories": []}) is True
    assert payload_is_empty({"repositories": [], "note": "none"}) is True
    assert payload_is_empty(None) is True
    assert payload_is_empty({"principals": [{"arn": "a"}]}) is False
    assert payload_is_empty([{"id": "x"}]) is False


def _eval_doc(package, doc):
    fd, path = tempfile.mkstemp(suffix=".json")
    try:
        with os.fdopen(fd, "w") as fh:
            json.dump(doc, fh)
        return evaluate(package, path)
    finally:
        os.remove(path)


def test_empty_payload_and_empty_list_score_missing():
    """Regression: deny-contains is vacuous on [] and used to return PASS."""
    opa = shutil.which("opa") is not None
    cases = [
        ("access_control.iam_mfa_enforced", {}),
        ("access_control.iam_mfa_enforced", []),
        ("access_control.iam_mfa_enforced", {"principals": []}),
        ("access_control.no_wildcard_policies", {"policies": []}),
        ("change_mgmt.branch_protection_enforced", {"repositories": []}),
        ("encryption.at_rest_required", {"data_resources": []}),
        ("network.tls_12_required", {"endpoints": []}),
        ("logging.audit_log_enabled", {"audit_logs": []}),
        ("backup.automated_backup_enabled", {"datastores": []}),
    ]
    for package, doc in cases:
        result = _eval_doc(package, doc)
        assert result["status"] == MISSING, (package, doc, result)
        assert result["status"] != PASS
        if opa:
            assert result.get("rego_empty") is True, (package, doc, result)


def test_nonempty_input_still_pass_and_fail():
    if shutil.which("opa") is None:
        print("SKIP nonempty pass/fail (opa not on PATH)")
        return
    passed = _eval_doc("access_control.iam_mfa_enforced", {
        "principals": [
            {"arn": "human-1", "type": "human", "privileged": False, "mfa_active": True},
        ],
    })
    assert passed["status"] == PASS, passed
    failed = _eval_doc("access_control.iam_mfa_enforced", {
        "principals": [
            {"arn": "human-2", "type": "human", "privileged": False, "mfa_active": False},
        ],
    })
    assert failed["status"] == FAIL, failed
    assert any("CTRL-ACCESS-001" in f and "human-2" in f for f in failed["findings"])


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
    print(f"\n{'PASS' if not failed else 'FAIL'}: {len(tests) - failed}/{len(tests)} evaluator tests")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
