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

The locker client exposes three operations:

- `put(record)` — write one evidence record; returns `fingerprint` (sha256) + log entry index. Object-lock (GOVERNANCE) prevents the version from being **purged or overwritten** within retention — it does _not_ prevent a delete marker (see "Smoke-test findings").
- `get(evidence_id)` — fetch a record + verify its fingerprint.
- `package(framework)` — emit a signed bundle: SOC 2 criteria checklist or ISO 27001:2022 SoA, each criterion linked to its latest PASS/EXCEPTION records. **Implemented** — `python3 -m evidence.packaging`.

## Integrity invariant

Every record carries a truthful `collected_at`, a content `fingerprint`, and a
transparency-log entry. The Merkle head hash is published so any post-hoc
tampering is externally detectable. **Records are never backdated** — stale
evidence decays to EXPIRED via the nightly recompute (§8.6), it is not
re-stamped.

## Integrity hardening (implemented)

The original smoke test (2026-07-11) found a gap: with versioning on,
`DeleteObject` (no versionId) adds a **delete marker** that obscures the
"current" view without purging the retained version. Three controls now close
it — prevent, detect, retrieve:

| Control                                  | Implementation                                                                                                       | Verified                                                                                          |
| ---------------------------------------- | -------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------- |
| Object-lock GOVERNANCE 365d + versioning | bucket created with WORM                                                                                             | retained version can't be purged without bypass (`"is WORM protected and cannot be overwritten"`) |
| **deny-DeleteObject** _(prevent)_        | `evidence-writer` IAM user in `docker-compose` init: PutObject/GetObject only, Deny DeleteObject                     | writer PUT succeeds; delete-marker attempt → **DENIED** ("Access Denied")                         |
| **Merkle append log** _(detect)_         | `evidence/log.py`; `run.py` appends each record fingerprint and publishes the head to `evidence/out/merkle_head.txt` | tampering with any record's content/order changes every subsequent head; 8 unit tests             |
| **Version-pinned get** _(retrieve)_      | `locker.get(control_id, evidence_id)` reads by pin, never the moveable current pointer                               | a stray delete marker cannot hide a record                                                        |

The published Merkle head makes post-hoc tampering externally detectable — any
divergence between a record's committed fingerprint and the chain breaks
verification. Records are never backdated; stale evidence decays to EXPIRED via
the nightly recompute (§8.6), it is not re-stamped.
