import hashlib

GENESIS = "0" * 64


def leaf_hash(content):
    if isinstance(content, str):
        content = content.encode()
    return hashlib.sha256(content).hexdigest()


def next_head(prev_head, leaf):
    return hashlib.sha256(f"{prev_head}{leaf}".encode()).hexdigest()


class MerkleLog:
    """Append-only hash-chain log. Each entry commits to (previous head, leaf).

    head_n = sha256(head_{n-1} || leaf_n). Publishing head_n makes any later
    tampering with entries 0..n-1 (content or order) detectable, since it would
    change every subsequent head. A linear hash-chain is the degenerate Merkle
    case (sufficient for tamper-evidence; full binary trees add batch proofs).
    """

    def __init__(self, entries=None):
        self.entries = []
        self.head = GENESIS
        if entries:
            for e in entries:
                self._verify_and_append(e)

    def append(self, leaf):
        entry = {"index": len(self.entries), "leaf": leaf, "prev_head": self.head,
                 "head": next_head(self.head, leaf)}
        self.entries.append(entry)
        self.head = entry["head"]
        return entry

    def _verify_and_append(self, entry):
        expected = next_head(entry["prev_head"], entry["leaf"])
        if expected != entry["head"]:
            raise ValueError(f"broken chain at index {entry.get('index')}: head mismatch")
        if entry["index"] != len(self.entries):
            raise ValueError(f"out-of-order entry: got {entry.get('index')}, expected {len(self.entries)}")
        self.entries.append(entry)
        self.head = entry["head"]

    def verify(self):
        head = GENESIS
        for i, e in enumerate(self.entries):
            if e["index"] != i or e["prev_head"] != head:
                return False
            if next_head(head, e["leaf"]) != e["head"]:
                return False
            head = e["head"]
        return head == self.head

    def to_json(self):
        return {"head": self.head, "entries": self.entries}
