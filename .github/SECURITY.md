# Security Policy

## Status: reference implementation

This repository is an **evergreen open-source readiness-sensor pack** (OPA/Rego
catalog + GitHub/org sensors). It is **not** a certified audit product,
**not** a SOC 2 Type I/II report, and **not** a claim that SafetyMP or any user
of this repository is SOC 2 certified. Treat readiness scores and sample
evidence as fixtures unless you replace them with your own systems.

## Reporting a Vulnerability

**Do not open a public GitHub issue** for undisclosed security vulnerabilities.

Submit a private report via
**[GitHub Security Advisories](https://github.com/SafetyMP/SOC-2/security/advisories/new)**.

If that link returns 404, private vulnerability reporting is not enabled yet —
ask a repo admin to turn on **Settings → Code security → Privately report a
security vulnerability**, then retry the link above.

Include reproduction steps, impact, and affected components where safe. We aim
to acknowledge within **72 hours**.

## Demo credentials and fixtures

`docker-compose.yml` uses well-known local MinIO credentials (`minioadmin`) and
`terraform-examples/main.tf` uses fake AWS keys plus a labeled demo password.
Those exist so `terraform plan` and the locker can run without cloud accounts.
Do not reuse them outside localhost, and do not treat fixture emails such as
`alice@example.com` as real identities.

## Supply-chain notes

- GitHub Actions are pinned to full commit SHAs (immutable), not moving tags.
- CI installs a checksum-verified OPA `v1.20.2` binary rather than `latest`.
- Review Dependabot PRs before merge; keep Action pins as `owner/repo@<sha> # tag`.
