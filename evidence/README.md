# Evidence files and reference locker

The current [real GitHub assessment](../docs/local-github-assessment.md) writes
private `report.json` and sanitized `evidence.json` files outside Git checkouts.
It does not use Docker, the legacy locker, sample waivers, or framework packaging.
The local workspace reads only an explicitly selected report or exported review;
review notes never change measured results.

This directory contains optional reference evidence utilities retained from the
original sensor pack. They are not a production evidence-custody system.

## Reference components

| Component | Actual behavior | Limit |
| --- | --- | --- |
| [`engine/locker.py`](../engine/locker.py) | Builds fingerprinted records and writes JSON by control/evidence ID; optional demo MinIO push | `get()` reads a local JSON file; it does not fetch a remote object version or verify a fingerprint |
| [`log.py`](log.py) | Builds and verifies an in-memory append-only hash chain | The reference runner writes the batch head to a local file; no external transparency service publishes or witnesses it |
| [`packaging.py`](packaging.py) | Renders framework-oriented Markdown and JSON from latest local reference records | Outputs are unsigned; labels such as “Auditor Package” or “Statement of Applicability” are reference views, not an auditor opinion or a complete ISMS |
| [`docker-compose.yml`](../docker-compose.yml) | Configures a development S3-compatible locker with versioning and GOVERNANCE retention | Demo credentials and local configuration do not establish production immutability, replication, or custody |

## Optional development locker

The workspace does not require this service. For an isolated local experiment,
inspect the Compose file and its network bindings before starting it:

```bash
docker compose up -d
python3 -m engine.run --push
```

The Compose configuration creates the `evidence` bucket with a 365-day governance
retention default and a limited `evidence-writer` account. The current Python push
adapter nevertheless uses the demo root account, not that limited writer. Root
credentials are well-known development values and must not be used for real evidence
or a shared deployment. Production storage and cross-cloud replication remain
unimplemented design work.

## Local packaging

```bash
python3 -m evidence.packaging
```

By default this reads records from `evidence/out/`, applies reference expiry and
waiver overlays, and writes Markdown/JSON under `evidence/packages/`. It is a
separate data format from workspace review exports and does not accept the private
GitHub workflow's `evidence.json` as a drop-in locker directory. Keep real evidence
out of the public repository and Pages payload.

## Integrity boundaries

Record fingerprints commit to payload bytes and the recorded status/findings.
An independently retained hash can help detect later changes, but the local
reference hash head alone is not external authentication or immutable custody.
`LockerClient.get()` does not recompute it, and the browser does not verify it.
There is no scheduled collection or nightly recomputation service in this workspace;
expiry overlays are applied when the reference commands run.

Historical July 2026 smoke tests explored GOVERNANCE retention, delete-marker
behavior, and a delete-denying writer policy. Those observations motivated the
reference configuration; they are not fresh verification of any current deployment.
The earlier [readiness-layer design](../docs/readiness-layer-design.md) also describes
signed bundles and published transparency logs as planned capabilities. Consult the
[current architecture](../docs/architecture.md) for what is implemented today.
