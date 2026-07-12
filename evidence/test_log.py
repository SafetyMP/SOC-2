import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from evidence.log import MerkleLog, leaf_hash, next_head, GENESIS


def test_empty_log_head_is_genesis():
    log = MerkleLog()
    assert log.head == GENESIS
    assert log.verify() is True


def test_append_advances_head():
    log = MerkleLog()
    e0 = log.append("leaf0")
    assert e0["index"] == 0
    assert log.head == next_head(GENESIS, "leaf0")
    assert log.verify() is True


def test_chain_is_sequential():
    log = MerkleLog()
    log.append("a")
    log.append("b")
    log.append("c")
    heads = [e["head"] for e in log.entries]
    assert len(set(heads)) == 3
    assert log.verify() is True


def test_roundtrip_through_entries():
    log = MerkleLog()
    for x in ("a", "b", "c"):
        log.append(x)
    rebuilt = MerkleLog(log.entries)
    assert rebuilt.head == log.head
    assert rebuilt.verify() is True


def test_tampered_leaf_breaks_verification():
    log = MerkleLog()
    log.append("a")
    log.append("b")
    log.entries[0]["leaf"] = "tampered"
    assert log.verify() is False


def test_tampered_head_detected_on_rebuild():
    log = MerkleLog()
    log.append("a")
    log.append("b")
    bad = [dict(e) for e in log.entries]
    bad[1]["head"] = "f" * 64
    try:
        MerkleLog(bad)
        raised = False
    except ValueError:
        raised = True
    assert raised


def test_out_of_order_detected():
    log = MerkleLog()
    log.append("a")
    log.append("b")
    swapped = [log.entries[1], log.entries[0]]
    try:
        MerkleLog(swapped)
        raised = False
    except ValueError:
        raised = True
    assert raised


def test_leaf_hash_of_bytes_and_str_match():
    assert leaf_hash("x") == leaf_hash(b"x")


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
    print(f"\n{'PASS' if not failed else 'FAIL'}: {len(tests) - failed}/{len(tests)} merkle log tests")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
