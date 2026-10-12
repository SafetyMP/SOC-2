import os
import sys
import tempfile
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sensors.procedural import evaluate
from engine.scorer import PASS, EXPIRED, MISSING

NOW = datetime(2026, 7, 12, tzinfo=timezone.utc)


def _with_doc(due, name="policy.md"):
    root = tempfile.mkdtemp()
    path = os.path.join(root, name)
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "w") as handle:
        handle.write("approved policy text\n")
    manifest = {"control_id": "C", "document_ref": name, "approved_at": "2026-01-01T00:00:00Z",
                "approved_by": "a", "next_review_due": due}
    return root, manifest


def test_future_due_is_pass():
    root, manifest = _with_doc("2027-01-01T00:00:00Z")
    assert evaluate(manifest, NOW, root)["status"] == PASS


def test_future_due_without_file_is_missing():
    root = tempfile.mkdtemp()
    manifest = {"control_id": "C", "document_ref": "missing.md",
                "approved_at": "2026-01-01T00:00:00Z", "approved_by": "a",
                "next_review_due": "2027-01-01T00:00:00Z"}
    result = evaluate(manifest, NOW, root)
    assert result["status"] == MISSING
    assert "document_ref" in result["findings"][0]


def test_path_escape_is_missing():
    root, _manifest = _with_doc("2027-01-01T00:00:00Z")
    escaped = {"control_id": "C", "document_ref": "../policy.md",
               "next_review_due": "2027-01-01T00:00:00Z"}
    assert evaluate(escaped, NOW, root)["status"] == MISSING


def test_past_due_is_expired():
    root, manifest = _with_doc("2026-01-01T00:00:00Z")
    r = evaluate(manifest, NOW, root)
    assert r["status"] == EXPIRED
    assert r["findings"] and "overdue" in r["findings"][0]


def test_missing_due_is_missing():
    root, manifest = _with_doc("2027-01-01T00:00:00Z")
    del manifest["next_review_due"]
    r = evaluate(manifest, NOW, root)
    assert r["status"] == MISSING


def test_valid_until_propagates():
    root, manifest = _with_doc("2027-01-01T00:00:00Z")
    r = evaluate(manifest, NOW, root)
    assert r["valid_until"] == "2027-01-01T00:00:00Z"


def test_boundary_due_equals_now_is_expired():
    root, manifest = _with_doc("2026-07-12T00:00:00Z")
    assert evaluate(manifest, NOW, root)["status"] == EXPIRED


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
