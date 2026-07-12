import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sensors.procedural import evaluate
from engine.scorer import PASS, EXPIRED, MISSING

NOW = datetime(2026, 7, 12, tzinfo=timezone.utc)


def _m(due):
    return {"control_id": "C", "document_ref": "d", "approved_at": "2026-01-01T00:00:00Z",
            "approved_by": "a", "next_review_due": due}


def test_future_due_is_pass():
    assert _m("2027-01-01T00:00:00Z") and evaluate(_m("2027-01-01T00:00:00Z"), NOW)["status"] == PASS


def test_past_due_is_expired():
    r = evaluate(_m("2026-01-01T00:00:00Z"), NOW)
    assert r["status"] == EXPIRED
    assert r["findings"] and "overdue" in r["findings"][0]


def test_missing_due_is_missing():
    r = evaluate({"control_id": "C", "approved_at": "2026-01-01T00:00:00Z"}, NOW)
    assert r["status"] == MISSING


def test_valid_until_propagates():
    r = evaluate(_m("2027-01-01T00:00:00Z"), NOW)
    assert r["valid_until"] == "2027-01-01T00:00:00Z"


def test_boundary_due_equals_now_is_expired():
    assert evaluate(_m("2026-07-12T00:00:00Z"), NOW)["status"] == EXPIRED


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
    print(f"\n{'PASS' if not failed else 'FAIL'}: {len(tests) - failed}/{len(tests)} procedural sensor tests")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
