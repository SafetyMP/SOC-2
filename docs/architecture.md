# Current architecture and data boundaries

SOC-2 combines an inspectable policy engine with a browser workspace for moving
from findings to a recorded next action. The existing Python/Rego stack remains
the source of measured verdicts; the browser presents results and planning notes.
No result is a SOC 2 report, CPA opinion, or certification.

## Three distinct paths

| Path | Entry point | Inputs and scope | Output |
| --- | --- | --- | --- |
| Public sample | [GitHub Pages workspace](https://safetymp.github.io/SOC-2/) | Bundled synthetic snapshot: 20 evaluated controls of 37; 11 technical and 9 procedural | Interactive sample and optional browser-local review export |
| Real repository assessment | `python3 scripts/assess_github.py --repo OWNER/REPO` | Read-only GitHub API observations for one repository; exactly CTRL-CHG-001, CTRL-CHG-002, and CTRL-CHG-008 | Private `report.json` and sanitized `evidence.json` outside Git checkouts; 34 controls remain outside scope |
| Reference engine | `python3 -m engine.run` or `soc2-score` | Jobs, fixtures, procedural manifests, and example waivers configured in the checkout | Terminal score and reference records under `evidence/out/`; optional demo-locker push |

The legacy reference runner's `--live` option replaces only GitHub job inputs.
Other configured inputs and waiver overlays remain in that run. It is not a
real-only assessment and must not be presented as one. Use the dedicated
[local GitHub workflow](local-github-assessment.md) for real repository findings.

## Real assessment flow

```text
Explicit OWNER/REPO
  → local GitHub CLI authentication
  → read-only GitHub API collector
  → allowlisted normalized configuration facts
  → two existing Rego packages / three scoped controls
  → private report.json + evidence.json
  → loopback viewer → findings + separate review notes → optional local export
```

[`sensors/github_assessment.py`](../sensors/github_assessment.py) collects default
branch protection, review/status-check configuration, and active Actions workflow
presence. It handles classic protection and effective rules conservatively.
Unreadable, ambiguous, unsupported, or incomplete settings produce MISSING evidence.
A successful observation of an absent required setting can produce FAIL.

[`scripts/assess_github.py`](../scripts/assess_github.py) evaluates only the scoped
GitHub inputs. It does not load fixture payloads, procedural manifests, or example
waivers. Observed settings are evaluated using the policies' production thresholds;
this does not prove the repository deploys to production. PASS describes those
settings, not actual review performance or successful/reproducible deployments.

## Workspace and report formats

[`demo/model.mjs`](../demo/model.mjs) validates version 1 reports and recomputes
scores from their control verdicts. `mode: fixture` identifies synthetic inputs;
`mode: github` carries the repository target, explicit scope, and measurement limits.
Mixed fixture/real results are rejected by the real-report validator.

An exported review uses `format: soc2-workspace-review-v1` and contains the report
plus a `review_notes` map keyed by control ID. Notes contain an owner, review
progress, and next-action text. They never change a result or create a waiver.
A solo-maintainer decision can therefore be recorded while a two-reviewer policy
continues to fail visibly.

```bash
python3 scripts/serve_workspace.py --report /absolute/path/report.json
python3 scripts/serve_workspace.py --report /absolute/path/review.json
```

The local viewer accepts both formats. Opening an exported review restores its
notes at startup; reloading restores the selected file's snapshot. New edits need
a new export. The selected source file is not rewritten.

## Privacy and publication boundary

- The collector uses local `gh` authentication; it sends authenticated read requests
  to GitHub but does not copy credentials to reports, browser code, or telemetry.
- Real output directories are fresh and private (`0700`); report/evidence files use
  `0600`. Output paths inside Git checkouts or through symlinks are refused.
- The viewer binds to `127.0.0.1`, serves only explicit application assets and the
  selected report/review, and exposes no upload or evidence-directory endpoint.
  Response headers disable caching and restrict page network access to itself.
- Real notes remain in tab memory. Sample notes may use browser-local storage under
  a separate report identity. Explicit downloads contain repository information and
  should be kept private; browser download permissions are browser-managed.
- Public Pages ships an explicit asset allowlist and a synthetic sample. It rejects
  real-mode imports. It never runs the collector or receives GitHub credentials.
- Fingerprints identify source records. The browser does not independently verify
  report authorship, signatures, or custody; API observations are not atomic snapshots.

## Score and scope

Clean readiness counts passing control weight. Effective readiness can also count
exception weight in the reference fixture path. Controls outside the evaluated
scope are shown separately and excluded from both denominators. MISSING and FAIL
are never passing results. Coverage must be read alongside any score.

The real workflow has no exception overlay. Changing a review note, progress label,
or rationale does not change its measured verdict. To verify a configuration fix,
collect a fresh report and inspect the new findings.

## Implemented versus reference or planned

| Capability | Current status |
| --- | --- |
| Synthetic browser workspace and fixture exporter | Implemented |
| Private single-repository GitHub assessment and review restoration | Implemented |
| Terraform plan normalization and warn/enforce sample policy gate | Implemented reference tooling |
| Procedural file-presence and review-date checks | Implemented reference tooling; no content/signature verification |
| Locker, local hash chain, framework-oriented Markdown/JSON packaging | Reference utilities; not production custody or signed audit deliverables |
| Cloud, Kubernetes, and code-scanning collectors | Stubs; not part of the current real assessment |
| Scheduled collection, external transparency publication, production replication | Historical design proposals; not current workspace features |
| SaaS accounts, shared evidence storage, reviewer identity verification | Not implemented |

The [historical design](readiness-layer-design.md) explains earlier ideas. It must
not be used to infer current capabilities, permissions, or collection schedules.
