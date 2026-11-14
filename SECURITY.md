# Security policy

SOC-2 is an open-source readiness workspace with a local GitHub configuration
collector and a Python/Rego policy library. It is not a SOC 2 Type I/II report,
CPA opinion, certification, or proof that a control operated effectively over time.
The public demo uses synthetic data; real assessments run separately on your
computer. See [the local data boundary](docs/local-github-assessment.md#local-data-boundary).

## Report a vulnerability privately

Do not disclose an unpatched vulnerability in a public issue or pull request.
Use [GitHub's private vulnerability reporting form](https://github.com/SafetyMP/SOC-2/security/advisories/new).
If the form is unavailable, ask the maintainer to enable a private reporting
channel without posting exploit details, credentials, or sensitive evidence.

Include the affected commit, component, impact, and minimal reproduction with
synthetic data. Do not send access tokens, private keys, real repository reports,
or customer evidence. Share only the information needed to reproduce the issue.
Ordinary bugs and feature requests belong in the public issue templates after
removing sensitive information.

## Credentials and real evidence

- The real collector uses the locally authenticated GitHub CLI and read-only API
  requests for one explicitly named repository. Credentials stay with that CLI;
  they are not passed to the browser or written into report/evidence JSON.
- The collector saves allowlisted facts and safe diagnostics, not raw API response
  bodies, headers, or subprocess errors. It uses fresh private directories outside
  Git checkouts (`0700`) and private files (`0600`).
- The local viewer binds to `127.0.0.1` and serves an exact static asset allowlist
  plus the explicitly selected report or review. It has no upload endpoint,
  credential form, provider connection, or directory browsing.
- Real reports and notes stay in browser memory. Opening an exported review with
  `--report` restores its saved notes, but does not write changes back. Exporting
  creates a local download containing repository information; browser downloads
  follow normal download-folder permissions, not the collector's `0600` setting.
- Treat reports and review exports as sensitive even when they contain no tokens.
  Keep them out of public repositories, Pages deployments, issue attachments,
  hosted paste services, and public screenshots. The public demo rejects real-mode
  reports; this is a product boundary, not authentication or provenance verification.
- Other local processes can reach the viewer while it runs. Use a trusted computer
  and browser and stop the server when finished. The viewer does not verify report
  signatures or defend against a compromised local environment.

Missing permissions or unsupported API responses produce missing evidence. A note
or a solo-maintainer decision must not hide a failed check or silently create a
waiver. The legacy `engine.run --live` path can combine live inputs with other
configured data; use `scripts/assess_github.py` for the isolated real-only workflow.

## Development fixtures and optional locker

`docker-compose.yml` provides an optional development locker with known demo
credentials, bound to loopback ports. It is not part of the local GitHub assessment
workflow and is not a production evidence-storage guarantee. Do not reuse its
credentials or expose it publicly. Docker is not required to run the workspace.

Terraform examples contain labeled fake credentials and demonstration settings so
local validation can run without cloud accounts. Fixture identities such as
`alice@example.com` are synthetic. Preserve that distinction in documentation and
tests; do not substitute real secrets or tenant records into committed examples.

## Supply chain and changes

GitHub Actions are pinned to full commit SHAs. CI installs a checksum-verified
OPA binary; Python dependencies are pinned in the existing manifests. Dependabot
checks Actions and Python dependencies weekly. Updates still require review and
passing checks. Do not weaken local evidence protections to make a test or demo
pass, and report the scope of verification honestly.
