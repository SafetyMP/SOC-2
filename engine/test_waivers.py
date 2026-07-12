import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.waivers import apply_waivers, apply_decay
from engine.scorer import FAIL, PASS, EXCEPTION, EXPIRED

NOW = datetime(2026, 7, 12, tzinfo=timezone.utc)


def _w(cid, expires):
    return {"id": "w1", "control_id": cid, "reason": "r", "approver": "a",
            "approved_at": "2026-07-10T00:00:00Z", "expires": expires}


def test_unexpired_waiver_converts_fail_to_exception():
    v = {"C": {"status": FAIL, "findings": ["x"]}}
    applied = apply_waivers(v, [_w("C", "2026-12-31T00:00:00Z")], NOW)
    assert v["C"]["status"] == EXCEPTION and applied == ["C"]


def test_expired_waiver_does_not_apply():
    v = {"C": {"status": FAIL, "findings": ["x"]}}
    applied = apply_waivers(v, [_w("C", "2026-01-01T00:00:00Z")], NOW)
    assert v["C"]["status"] == FAIL and applied == []


def test_waiver_only_applies_to_fail():
    v = {"C": {"status": PASS, "findings": []}}
    apply_waivers(v, [_w("C", "2026-12-31T00:00:00Z")], NOW)
    assert v["C"]["status"] == PASS


def test_waiver_targets_specific_control():
    v = {"A": {"status": FAIL, "findings": []}, "B": {"status": FAIL, "findings": []}}
    apply_waivers(v, [_w("A", "2026-12-31T00:00:00Z")], NOW)
    assert v["A"]["status"] == EXCEPTION and v["B"]["status"] == FAIL


def test_decay_expires_stale_pass():
    v = {"C": {"status": PASS, "valid_until": "2026-06-01T00:00:00Z"}}
    decayed = apply_decay(v, NOW)
    assert v["C"]["status"] == EXPIRED and decayed == ["C"]


def test_decay_leaves_fresh_pass():
    v = {"C": {"status": PASS, "valid_until": "2026-12-01T00:00:00Z"}}
    apply_decay(v, NOW)
    assert v["C"]["status"] == PASS


def test_decay_ignores_fail():
    v = {"C": {"status": FAIL, "valid_until": "2020-01-01T00:00:00Z"}}
    apply_decay(v, NOW)
    assert v["C"]["status"] == FAIL


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
    print(f"\n{'PASS' if not failed else 'FAIL'}: {len(tests) - failed}/{len(tests)} waiver/decay tests")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
