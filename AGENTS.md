# AGENTS.md — SOC-2 local readiness workspace

## Purpose and entry points

This repository combines a private local GitHub assessment workflow with a
synthetic browser demo, backed by Python and OPA/Rego. Read [README.md](README.md),
then the relevant [guide](docs/README.md) and implementation files for your task.
[docs/architecture.md](docs/architecture.md) describes current behavior; historical
design documents are context, not proof of implemented features.

## Preserve these boundaries

- Real workflow: `scripts/assess_github.py` evaluates exactly three GitHub-backed
  checks for one explicit repository. Other catalog controls stay outside scope.
  Never supplement real findings with sample payloads or example waivers.
- Sample workflow: `scripts/export_workspace.py` uses synthetic fixtures and
  procedural manifests. Public Pages publishes only the curated demo assets.
- Keep GitHub credentials with the local `gh` process. Do not request tokens in
  browser forms, log secrets, commit real reports, or upload customer evidence.
- The local viewer binds only to loopback, serves an explicit asset allowlist and
  one selected report/review, and has no write/upload/provider endpoints.
- Real review notes stay in tab memory and explicitly exported files. Notes do
  not change verdicts, prove review happened, or create policy exceptions.
- Unknown, inaccessible, empty, or unsupported evidence must not become PASS.
  Keep missing evidence, failed checks, exceptions, and unevaluated scope distinct.
- No score is a SOC 2 report, CPA opinion, certification, or complete compliance
  percentage. Use the narrow observed-check descriptions near real results.
- Preserve existing evidence and user edits. Do not reactivate archived external
  orchestration or introduce unrelated factory integrations.

## Commands

Run from the repository root. Use Python 3.11+, PyYAML, and OPA (CI: 1.20.2);
Node.js 22 and Terraform are also needed for full verification.

| Task | Command |
| --- | --- |
| Full verification | `./scripts/verify.sh` |
| Repository links and discovery assets | `python3 scripts/check_repository.py` |
| Sample workspace | `python3 scripts/serve_workspace.py` |
| Real assessment, when requested | `python3 scripts/assess_github.py --repo OWNER/REPO` |
| Open report or exported review | `python3 scripts/serve_workspace.py --report /absolute/path/file.json` |
| Generate synthetic report | `python3 scripts/export_workspace.py --output /absolute/path/sample-report.json` |
| Workspace Python checks | `python3 scripts/test_export_workspace.py`, `python3 scripts/test_assess_github.py`, `python3 scripts/test_serve_workspace.py` |
| Browser model checks | `node --test demo/*.test.mjs` and `node --check demo/app.js` |
| Rego validation | `opa fmt --fail policies/`, `opa check policies/`, `opa test policies/` |

`verify.sh` must never perform live collection, apply Terraform, start Docker,
change GitHub settings, or upload evidence. Initial tool/provider installation
can require network access. Keep the legacy `engine.run --live` mixed-input path
separate from the real-only workflow; see [engine/README.md](engine/README.md).

## Implementation and acceptance

Preserve the existing stack. Python tests are executable `test_*.py` scripts;
browser model tests use Node's built-in test runner. Do not invent pytest, npm,
or lint commands that this checkout does not provide. Follow
[Python](.github/instructions/python.instructions.md),
[Rego](.github/instructions/rego.instructions.md), and
[test](.github/instructions/tests.instructions.md) conventions where applicable.

For meaningful changes, define the behavior to verify, run relevant checks and
full verification, and obtain independent review. Browser changes need visual
and interaction verification. Distinguish mocked tests, real collection, browser
observations, remote CI, and deployment; one does not prove the others.

Use small PRs against `main`. Required checks are `validate-catalog`,
`validate-policies`, and `verify-demo`; deployment runs after merge. Current
solo-maintainer settings do not require approving reviews. Do not weaken the
policy's two-review threshold to make that operational choice appear compliant.
Never bypass branch protection or alter it without task authorization.

Keep README, CLI help, current guides, and both optional `llms.txt` navigation
files accurate when behavior changes. Agent indexes are documentation, not
permission to run commands or override user instructions. Avoid fabricated
releases, ratings, coverage, search-ranking claims, or indexing guarantees.
