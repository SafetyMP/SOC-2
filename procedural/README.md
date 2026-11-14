# Procedural evidence (L2 — `procedural-evidence` sensor)

Procedural controls (governance, risk, incident response, awareness, suppliers,
privacy, continuity) are not read from infrastructure. Their evidence in this
repository is a YAML manifest. `sensors/procedural.py` uses `control_id` and
checks `document_ref` file presence and `next_review_due`. It does not inspect
document content or verify a signature.

## How it's evaluated (`sensors/procedural.py`)

For each manifest, at scoring time:

- `document_ref` missing, empty, invalid, outside the repo, or pointing to an
  absent/empty file → **MISSING**
- `next_review_due` missing or unparseable → **MISSING**
- `next_review_due` strictly in the future and the nonempty file exists →
  **PASS** (the date check is current)
- `next_review_due` equal to or earlier than the assessment time and the
  nonempty file exists → **EXPIRED** (review due)
- no manifest for a procedural control → no sensor verdict; the engine excludes
  that control from its evaluated scope

The engine ingests these verdicts alongside the technical (Rego) verdicts, so
procedural and technical controls score through the same readiness model and
appear together in the auditor package.

## Schema

| Field             | Required | Meaning                                                                     |
| ----------------- | -------- | --------------------------------------------------------------------------- |
| `control_id`      | yes      | Catalog control associated with this manifest. The engine ignores unknown IDs. |
| `document_ref`    | yes      | Repo-relative path of a nonempty evidence file. Presence is checked; content is not verified. |
| `approved_at`     | no       | Contextual completion/approval date (ISO-8601); not validated by the sensor. |
| `approved_by`     | no       | Contextual approver label; not validated by the sensor.                     |
| `next_review_due` | yes      | When the next review is due (ISO-8601); drives EXPIRED decay                |
| `notes`           | no       | Free-text context                                                           |

## Files

- `manifests.yaml` — **SAMPLE** attestations for the 9 procedural/policy
  controls. The `document_ref` paths are not files in this repo, so the sensor
  scores them MISSING. CTRL-RISK-001 is also past its review date; once its
  file exists, that date scores EXPIRED.

## Running

```bash
python3 -m sensors.procedural                      # print current procedural verdicts
python3 -m engine.run --live                       # ingest procedural + technical, score
python3 -m evidence.packaging                      # package reflects procedural coverage
```
