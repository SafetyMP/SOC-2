# Engine (L3 eval + L4 scorer + L6 waivers)

Closes the loop: normalized sensor payload → Rego evaluation → control verdict →
evidence record (version-pinned into the locker) → readiness score, with waivers
and validity decay so the clean-vs-effective gap reflects accepted risk honestly.

## Run

```bash
python3 -m engine.run                       # evaluate fixtures, apply waivers+decay, print report
python3 -m engine.run --push                # also version-pin evidence records into the MinIO locker
python3 -m engine.run --as-of 2026-12-01    # simulate decay (evidence + waiver expiry aged forward)
python3 -m engine.test_scorer               # scorer unit tests (pure)
python3 -m engine.test_waivers              # waiver + decay unit tests (pure)
```

Inputs: `catalog/` (controls), `policies/` (Rego), `engine/jobs.yaml`
(payload→package routing), `fixtures/` (sample normalized sensor payloads),
`procedural/` (document paths and review-date manifests), and `exceptions/`
(waivers — policy-as-data).

## Modules

| Module         | Role                                                                                                                        | Status      |
| -------------- | --------------------------------------------------------------------------------------------------------------------------- | ----------- |
| `catalog.py`   | Load + index controls; map `rego_package → control_id`; infer domain                                                        | implemented |
| `evaluator.py` | Run `opa eval` (subprocess, paths relativized to repo root) → `PASS`/`FAIL`/`MISSING` + findings                            | implemented |
| `scorer.py`    | Clean vs. effective readiness, weighted by `criticality`, rolled up per domain/framework (pure)                             | implemented |
| `locker.py`    | Build the §6 evidence record; `put()` → local JSON + optional version-pinned MinIO push                                     | implemented |
| `waivers.py`   | Load `exceptions/*.yaml`; `apply_decay` (PASS→EXPIRED past `valid_until`); `apply_waivers` (FAIL→EXCEPTION, unexpired only) | implemented |
| `run.py`       | Orchestrate the loop + print the readiness report                                                                           | implemented |

## Verdict state machine

```
sensor ──► PASS | FAIL              (evaluator, only when the payload has rows)
empty payload / empty list ──► MISSING
no result / evaluator error ──► MISSING
package not implemented ──► excluded from evaluated scope
PASS with valid_until < as_of ──► EXPIRED   (decay at scoring time / --as-of)
FAIL + unexpired waiver ──► EXCEPTION       (waiver eval)
```

`Ready(c) := status(c) ∈ {PASS, EXCEPTION(unexpired)}`.

Procedural controls use a separate evidence-presence and date check. The
`document_ref` must resolve to a nonempty file inside the repository, and
`next_review_due` must be parseable. Missing evidence or a missing/unparseable
date produces **MISSING**. With the file present, a future due date produces
**PASS**; a due date equal to or earlier than the assessment time produces
**EXPIRED**. The sensor does not inspect document content or verify signatures.

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

For technical records, `build_record()` derives `valid_until` from the actual
collection time plus the catalog's `evidence_validity` duration. The parser uses
365 days per year and 30 days per month, and falls back to 30 days for an
unrecognized duration. For procedural records, `run()` replaces that value with
the manifest sensor's `valid_until`, derived from `next_review_due` when the
referenced file is present. The scorer applies expiry to these timestamps, not
directly to the catalog duration. Stored records contain the original evaluation
status; later decay and waiver overlays affect the reported verdicts.

## Coverage model

The default repository inputs evaluate **20 wired controls out of 37 catalog
controls**: **11 technical** controls routed through 10 implemented Rego packages
in `engine/jobs.yaml`, plus **9 procedural** controls with manifests. Readiness
is weighted by criticality over this evaluated slice. Missing evidence for a
wired control stays in the denominator; it does not count as passing.

The other **17 catalog controls** are unwired and excluded from readiness. The
CLI also reports package coverage (implemented packages ÷ referenced packages),
which is separate from both control coverage and the readiness score. A larger
score does not establish coverage of the entire catalog or an audit opinion.
