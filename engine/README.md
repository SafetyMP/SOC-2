# Engine (L3 eval + L4 scorer)

Closes the loop: normalized sensor payload → Rego evaluation → control verdict →
evidence record (version-pinned into the locker) → readiness score.

## Run

```bash
python3 -m engine.run                 # evaluate fixtures, emit evidence to evidence/out/, print report
python3 -m engine.run --push          # also version-pin evidence records into the MinIO locker
python3 -m engine.test_scorer         # unit tests for the scorer (pure)
```

Inputs: `catalog/` (controls), `policies/` (Rego), `engine/jobs.yaml`
(payload→package routing), `fixtures/` (sample normalized sensor payloads).

## Modules

| Module         | Role                                                                                             | Status         |
| -------------- | ------------------------------------------------------------------------------------------------ | -------------- |
| `catalog.py`   | Load + index controls; map `rego_package → control_id`; infer domain                             | implemented    |
| `evaluator.py` | Run `opa eval` (subprocess, paths relativized to repo root) → `PASS`/`FAIL`/`MISSING` + findings | implemented    |
| `scorer.py`    | Clean vs. effective readiness, weighted by `criticality`, rolled up per domain/framework (pure)  | implemented    |
| `locker.py`    | Build the §6 evidence record; `put()` → local JSON + optional version-pinned MinIO push          | implemented    |
| `run.py`       | Orchestrate the loop + print the readiness report                                                | implemented    |
| waiver eval    | Apply `exceptions/*.yaml` (FAIL → EXCEPTION); validity decay to EXPIRED                          | stub (Phase 5) |

## Verdict state machine

```
sensor ──► PASS | FAIL              (evaluator)
no result / error ──► MISSING       (sensor broken or pkg not implemented)
FAIL + unexpired waiver ──► EXCEPTION   (Phase 5)
age > valid_until ──► EXPIRED        (nightly recompute, Phase 5)
```

`Ready(c) := status(c) ∈ {PASS, EXCEPTION(unexpired)}`.

## Evidence record (§6 schema)

Every evaluation emits one record per evaluated control, e.g.:

```json
{
  "evidence_id": "ev_1183ebc5901b4baeac624d95",
  "control_id": "CTRL-ENC-001",
  "framework_refs": { "soc2": ["CC6.1", "C1.1"], "iso27001": ["A.8.24"] },
  "status": "PASS",
  "source": {
    "sensor": "encryption",
    "query": "opa eval data.encryption.at_rest_required.deny"
  },
  "collected_at": "2026-07-12T13:12:56Z",
  "valid_until": "2026-08-11T13:12:56Z",
  "fingerprint": "sha256:7d2b90ec...",
  "verdict_detail": { "findings": [] }
}
```

With `--push`, each record is written to the MinIO `evidence` bucket under
`GOVERNANCE` object-lock (365d) — the version is WORM-protected and cannot be
purged without bypass (verified). `collected_at` is always truthful; records are
never backdated.

## Coverage model

Readiness is computed over **wired** controls (those with an implemented Rego
package and a sensor payload). Catalog controls whose Rego is not yet
implemented are reported as a separate **coverage** metric (implemented packages
÷ referenced packages), not counted against readiness — honest for the phased
rollout. Current Phase-1 slice: 8 wired controls / 37 catalog controls.
