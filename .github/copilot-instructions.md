# SOC-2 repository instructions

This is a readiness workspace: local GitHub configuration assessment, browser
finding review, and a Python/Rego policy and sensor library. Start with
[AGENTS.md](../AGENTS.md) for the current code map and commands, and
[CONTRIBUTING.md](../CONTRIBUTING.md) for contribution expectations.

## Product and evidence boundaries

- `scripts/assess_github.py` collects one explicitly named repository with local
  GitHub CLI authentication. It evaluates three GitHub checks without fixtures or
  sample waivers. Keep real reports and evidence outside the checkout.
- `scripts/export_workspace.py` creates synthetic fixture reports. The public
  Pages demo accepts fixture data; real results open only in the local workspace.
- `scripts/serve_workspace.py --report PATH` opens either a report or exported
  review. Saved notes restore separately from verdicts; a failed result stays
  failed, and a review note is not a waiver.
- Empty, inaccessible, and unsupported evidence must not become PASS. Controls
  outside scope remain unevaluated and excluded from the score.
- Credentials must not enter browser code, reports, logs, screenshots, or commits.
  Preserve the viewer's loopback bind, asset allowlist, origin checks, and CSP.
- Do not describe results as certification, an audit opinion, complete SOC 2
  coverage, or proof of operating effectiveness. Use the check's measured scope.

## Implementation and verification

Preserve the Python, OPA/Rego, and buildless browser stack. Use the adjacent test
style rather than introducing a new framework. Run `./scripts/verify.sh` and
appropriate focused tests; report actual results and any unrun checks. Live
provider collection is not part of the test suite. Do not run it for unrelated
work or publish its outputs.

Keep source changes focused and preserve user edits. Do not alter evaluation
semantics as a side effect of documentation or visual work. Use
[path-specific instructions](instructions/) for Python, Rego, workspace, and tests.
[Review guidance](skills/code-review/SKILL.md) covers the shared evidence boundaries.
Historical plans are context, not evidence that a feature is implemented.
