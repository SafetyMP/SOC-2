# Evaluation engine

The workspace uses the existing Python and OPA/Rego engine to turn normalized
inputs into scoped verdicts. Read the [current architecture](../docs/architecture.md)
for the difference between a real repository assessment and the fixture runner.

## Recommended workspace commands

```bash
# One real repository; private evidence outside the checkout
python3 scripts/assess_github.py --repo OWNER/REPO
python3 scripts/serve_workspace.py --report /absolute/path/report.json

# Synthetic fixtures only; no provider connection
python3 scripts/export_workspace.py --output workspace-report.json
```

The real command evaluates exactly three GitHub controls, leaves the other 34
catalog controls outside scope, and applies no sample waivers. Unreadable settings
or unavailable evaluation become MISSING. See the
[setup and privacy guide](../docs/local-github-assessment.md).

## Reference runner

Run from the repository root:

```bash
python3 -m engine.run                    # configured fixtures and procedural manifests
python3 -m engine.run --as-of 2026-12-01 # simulate validity/waiver expiry
python3 -m engine.test_scorer
python3 -m engine.test_waivers
```

`python3 -m engine.run` and the installed `soc2-score` command use `catalog/`,
`policies/`, `engine/jobs.yaml`, fixtures, procedural manifests, and `exceptions/`.
They write reference records under `evidence/out/` and a local hash-chain head.
The workspace fixture exporter avoids replacing these retained outputs.

The legacy `--live` option refreshes GitHub inputs only; all other configured
inputs and waiver overlays remain. `--org` broadens that legacy collection.
Neither is the private real-only workspace workflow. Do not use a combined run
as evidence that all displayed controls were collected from live systems.

`--push` additionally attempts a write to the optional local demo locker. It is
not needed for the browser workspace. Read the [locker limits](../evidence/README.md)
before using it; no production custody guarantee follows from this option.

## Modules

| Module | Responsibility |
| --- | --- |
| `catalog.py` | Load controls and package-to-control mappings |
| `evaluator.py` | Invoke OPA and attribute findings to control IDs |
| `scorer.py` | Compute weighted clean/effective readiness over an explicit scope |
| `locker.py` | Construct fingerprinted records and optionally write reference outputs |
| `waivers.py` | Apply legacy validity and exception overlays; no signature verification |
| `run.py` | Run configured technical/procedural jobs and print their reference report |

## Verdicts and limits

- A nonempty technical input can evaluate to PASS or FAIL.
- Empty input or unavailable evaluation becomes MISSING, not a vacuous pass.
- A control without an evaluation is outside the scored scope; the workspace labels
  it UNWIRED / not evaluated rather than passing it.
- In the reference runner, PASS evidence can become EXPIRED at assessment time;
  a legacy waiver can convert FAIL to EXCEPTION. See [exception limits](../exceptions/README.md).
- Workspace planning notes are independent of all these states. They cannot
  convert FAIL to PASS or EXCEPTION.

The default reference inputs evaluate 20 of 37 controls: 11 technical through ten
Rego packages and nine procedural. The other 17 are outside that run's scope.
Procedural evaluation checks a nonempty repository-contained evidence file and
its review date, not its content or signature. The bundled procedural references
are absent, so they produce MISSING evidence.

## Evidence records

`build_record()` records the control, source query, collection time, status,
findings, and a fingerprint over normalized payload bytes plus the verdict.
Technical validity uses the catalog duration (365-day years, 30-day months;
unrecognized durations fall back to 30 days). Procedural records use the manifest
review date when available. Reference decay/waiver overlays change reported
verdicts, not the original stored collection record.

A fingerprint is not a digital signature or proof of provider authenticity. The
local workspace does not independently verify custody. Scores describe evaluated
checks, not a SOC 2 examination, certification, or operating effectiveness.
