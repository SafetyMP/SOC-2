import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from evidence.packaging import criterion_status, _soc2_family, _iso_theme
from engine.scorer import PASS, FAIL, EXCEPTION, EXPIRED, MISSING


def test_empty_is_not_addressed():
    assert criterion_status([]) == "Not addressed"


def test_all_pass_is_met():
    assert criterion_status([PASS, PASS]) == "Met"


def test_fail_only_is_not_met():
    assert criterion_status([FAIL, FAIL]) == "Not met"


def test_pass_and_fail_is_partial():
    assert criterion_status([PASS, FAIL]) == "Partial"


def test_none_evaluated():
    assert criterion_status([MISSING, MISSING]) == "Not evaluated"


def test_pass_plus_missing_is_partial():
    assert criterion_status([PASS, MISSING]) == "Partial"


def test_exception_only():
    assert criterion_status([EXCEPTION]) == "Exception (waivered)"


def test_soc2_family():
    assert _soc2_family("CC6.1") == "CC6"
    assert _soc2_family("A1.2") == "A1"
    assert _soc2_family("P5.1") == "P5"


def test_iso_theme():
    assert _iso_theme("A.8.5") == "A.8"
    assert _iso_theme("A.5.15") == "A.5"


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
    print(f"\n{'PASS' if not failed else 'FAIL'}: {len(tests) - failed}/{len(tests)} packaging tests")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
