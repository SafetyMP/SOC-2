import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.catalog import Control
from engine.locker import build_record


def _control():
    return Control(
        {
            "id": "CTRL-ACCESS-003",
            "criticality": 3,
            "evidence_validity": "P30D",
            "rego_packages": ["access_control.no_wildcard_policies"],
        },
        "access-control",
    )


def test_same_payload_different_status_hashes_differently():
    payload = b'{"policies":[{"name":"Read","actions":["s3:GetObject"],"resources":["arn"]}]}'
    passed = build_record(_control(), {"status": "PASS", "findings": []}, payload, "access")
    failed = build_record(_control(), {"status": "FAIL", "findings": ["CTRL-ACCESS-003: wildcard"]}, payload, "access")
    missing = build_record(_control(), {"status": "MISSING", "findings": []}, payload, "access")
    assert passed["fingerprint"] != failed["fingerprint"]
    assert passed["fingerprint"] != missing["fingerprint"]
    assert passed["fingerprint"].startswith("sha256:")
    again = build_record(_control(), {"status": "PASS", "findings": []}, payload, "access")
    assert passed["fingerprint"] == again["fingerprint"]


def test_findings_change_the_fingerprint():
    payload = b'{"policies":[]}'
    one = build_record(_control(), {"status": "FAIL", "findings": ["a"]}, payload, "access")
    two = build_record(_control(), {"status": "FAIL", "findings": ["b"]}, payload, "access")
    assert one["fingerprint"] != two["fingerprint"]
    assert one["verdict_detail"]["findings"] == ["a"]


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
        except Exception as e:
            failed += 1
            print(f"FAIL {t.__name__}: {type(e).__name__}: {e}")
    print(f"\n{'PASS' if not failed else 'FAIL'}: {len(tests) - failed}/{len(tests)} locker tests")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
