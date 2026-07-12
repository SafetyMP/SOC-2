import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.evaluator import attribute_findings


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
