# Procedural evidence (L2 — `procedural-evidence` sensor)

Procedural controls (governance, risk, incident response, awareness, suppliers,
privacy, continuity) can't be sensed from infrastructure. Their evidence is a
**signed manifest** carrying an approval date and a `next_review_due` — the
review cadence itself drives validity decay (design §15).

## How it's evaluated (`sensors/procedural.py`)

For each manifest, at scoring time:

- `next_review_due` in the future → **PASS** (review is current)
- `next_review_due` in the past → **EXPIRED** (review overdue; readiness drops)
- no manifest for a procedural control → **MISSING** (control not implemented)

The engine ingests these verdicts alongside the technical (Rego) verdicts, so
procedural and technical controls score through the same readiness model and
appear together in the auditor package.

## Schema

| Field             | Required | Meaning                                                                     |
| ----------------- | -------- | --------------------------------------------------------------------------- |
| `control_id`      | yes      | Catalog control this attests (must be `assertion_type: procedural\|policy`) |
| `document_ref`    | yes      | Where the artifact lives (path / git ref / locker URI)                      |
| `approved_at`     | yes      | When the activity was completed/approved (ISO-8601)                         |
| `approved_by`     | yes      | Who approved it (accountable)                                               |
| `next_review_due` | yes      | When the next review is due (ISO-8601); drives EXPIRED decay                |
| `notes`           | no       | Free-text context                                                           |

## Files

- `manifests.yaml` — **SAMPLE** attestations for the 9 procedural/policy
  controls. Replace with real, approver-signed records before relying on the
  score. One (CTRL-RISK-001) is intentionally overdue to demonstrate decay.

## Running

```bash
python3 -m sensors.procedural                      # print current procedural verdicts
python3 -m engine.run --live                       # ingest procedural + technical, score
python3 -m evidence.packaging                      # package reflects procedural coverage
```
