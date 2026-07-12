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

- `put(record)` — write one evidence record; returns `fingerprint` (sha256) + log entry index. Object-lock prevents deletion/overwrite within retention.
- `get(evidence_id)` — fetch a record + verify its fingerprint.
- `package(framework)` — emit a signed bundle: SOC 2 criteria checklist or ISO 27001:2022 SoA, each criterion linked to its latest PASS/EXCEPTION records.

## Integrity invariant

Every record carries a truthful `collected_at`, a content `fingerprint`, and a
transparency-log entry. The Merkle head hash is published so any post-hoc
tampering is externally detectable. **Records are never backdated** — stale
evidence decays to EXPIRED via the nightly recompute (§8.6), it is not
re-stamped.
