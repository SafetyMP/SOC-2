# Evidence locker (L5)

Immutable, tamper-evident store for evidence records. One interface, two targets
(see `docs/readiness-layer-design.md §10`):

| Target               | Store                                          | Status              |
| -------------------- | ---------------------------------------------- | ------------------- |
| **Local/dev**        | MinIO (object-lock) via `docker-compose.yml`   | **wired (Phase 0)** |
| **Prod**             | cloud object-lock bucket + cross-cloud replica | stub (Phase 4)      |
| **Transparency log** | Merkle append-log, head hash published         | stub (Phase 4)      |

## Local usage

```bash
docker compose up -d                       # starts MinIO + creates object-locked `evidence` bucket
# endpoint: http://localhost:9000  ak/sk: minioadmin/minioadmin
# bucket:   evidence               object-lock: governance 365d
```

## Interface (target contract)

The locker client exposes three operations (to be implemented in Phase 4):

- `put(record)` — write one evidence record; returns `fingerprint` (sha256) + log entry index. Object-lock (GOVERNANCE) prevents the version from being **purged or overwritten** within retention — it does _not_ prevent a delete marker (see "Smoke-test findings").
- `get(evidence_id)` — fetch a record + verify its fingerprint.
- `package(framework)` — emit a signed bundle: SOC 2 criteria checklist or ISO 27001:2022 SoA, each criterion linked to its latest PASS/EXCEPTION records.

## Integrity invariant

Every record carries a truthful `collected_at`, a content `fingerprint`, and a
transparency-log entry. The Merkle head hash is published so any post-hoc
tampering is externally detectable. **Records are never backdated** — stale
evidence decays to EXPIRED via the nightly recompute (§8.6), it is not
re-stamped.

## Smoke-test findings (verified locally)

Verified against the MinIO locker on 2026-07-11:

| Check                                                        | Result                                               |
| ------------------------------------------------------------ | ---------------------------------------------------- |
| Bucket created with object-lock GOVERNANCE 365d + versioning | ✅                                                   |
| Retained version cannot be permanently purged without bypass | ✅ — `"is WORM protected and cannot be overwritten"` |
| Retained version data remains readable by versionId          | ✅                                                   |
| Delete marker can be added (obscures the "current" view)     | ⚠️ confirmed                                         |

**Caveat surfaced:** because versioning is on, `DeleteObject` (no versionId) adds a
delete marker rather than purging data. The retained version survives and is
retrievable by versionId, but the default ("current") view reports it absent.
This does not violate immutability of the record itself, but it can hide it.

**Hardening required (Phase 4 locker client):**

1. **Bucket policy** denying `s3:DeleteObject` for the evidence-writer credential,
   so only put/get are allowed — delete markers cannot be added in the first place.
2. **Read by versionId** — the `get` path pins the exact retained version (never the
   moveable "current" pointer), so even a stray delete marker cannot hide evidence.
3. **Write path records the versionId** returned by each put, so every evidence
   reference is version-pinned from the moment it is created.
