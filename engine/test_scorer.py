import sys

from engine.catalog import Catalog, Control
from engine.scorer import score, PASS, FAIL, EXCEPTION, MISSING


def _ctrl(cid, crit, domain, soc2=None, iso=None):
    return Control(
        {"id": cid, "criticality": crit, "soc2": soc2 or [], "iso27001": iso or []},
        domain,
    )


def _v(status):
    return {"status": status, "findings": []}


def test_all_pass():
    cat = Catalog([_ctrl("A", 3, "d"), _ctrl("B", 3, "d")])
    r = score({"A": _v(PASS), "B": _v(PASS)}, cat)
    assert r["overall"]["clean_ratio"] == 1.0
    assert r["overall"]["effective_ratio"] == 1.0


def test_fail_lowers_clean():
    cat = Catalog([_ctrl("A", 3, "d"), _ctrl("B", 3, "d")])
    r = score({"A": _v(PASS), "B": _v(FAIL)}, cat)
    assert r["overall"]["clean_ratio"] == 0.5
    assert r["overall"]["effective_ratio"] == 0.5


def test_exception_splits_clean_vs_effective():
    cat = Catalog([_ctrl("A", 3, "d"), _ctrl("B", 3, "d")])
    r = score({"A": _v(PASS), "B": _v(EXCEPTION)}, cat)
    assert r["overall"]["clean_ratio"] == 0.5
    assert r["overall"]["effective_ratio"] == 1.0


def test_missing_is_not_ready():
    cat = Catalog([_ctrl("A", 3, "d"), _ctrl("B", 2, "d")])
    r = score({"A": _v(PASS), "B": _v(MISSING)}, cat)
    assert r["overall"]["clean_ratio"] == 0.6


def test_missing_verdict_defaults_to_missing():
    cat = Catalog([_ctrl("A", 3, "d")])
    r = score({}, cat)
    assert r["overall"]["clean_ratio"] == 0.0


def test_domain_isolation():
    cat = Catalog([_ctrl("A", 3, "x"), _ctrl("B", 1, "y")])
    r = score({"A": _v(FAIL), "B": _v(PASS)}, cat)
    assert r["domains"]["x"]["clean_ratio"] == 0.0
    assert r["domains"]["y"]["clean_ratio"] == 1.0


def test_framework_rollup():
    cat = Catalog([_ctrl("A", 3, "d", soc2=["CC6.1", "CC6.6"], iso=["A.8.5"])])
    r = score({"A": _v(PASS)}, cat)
    assert r["frameworks"]["soc2"]["CC6.1"]["ready"] == 1
    assert r["frameworks"]["soc2"]["CC6.6"]["ready"] == 1
    assert r["frameworks"]["iso27001"]["A.8.5"]["ready"] == 1


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
    print(f"\n{'PASS' if not failed else 'FAIL'}: {len(tests) - failed}/{len(tests)} scorer tests")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    main()
