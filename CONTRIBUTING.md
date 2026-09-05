# Contributing to SOC-2

Thanks for improving this **readiness-sensor example pack** (OPA/Rego catalog,
GitHub/org sensors, evidence records). It is not a GRC product and does **not**
certify SOC 2 compliance. Read [docs/DESIGN-PIVOT.md](docs/DESIGN-PIVOT.md) and
the [Code of Conduct](CODE_OF_CONDUCT.md) first.

## Verify

A contribution is not finished until this is green locally:

```bash
./scripts/verify.sh
```

Requires `python3`, PyYAML, [OPA](https://www.openpolicyagent.org/), and
Terraform on `PATH`. Optional fixture assessment:
`python3 -m engine.run`.

## Scope

- Do not soften the “not a certification / not a CPA opinion” language in
  README, [SECURITY.md](SECURITY.md), or DESIGN-PIVOT.
- Do not implement a new corporate-site-harness program in this repo (CEO
  workflow). Keep this pack as catalog + policies + sensors.
- Prefer tests over prose when changing engine, sensors, or catalog validation.
- Never commit secrets, live credentials, or real customer evidence.

## Pull requests

- Small, reviewable diffs; fill in the PR template.
- Open against `main`; CI (`policy-ci`) must pass.
- Security issues: follow [SECURITY.md](SECURITY.md) — do not file a public issue.

## License

By contributing, you agree that your contributions are licensed under the
[Apache License 2.0](LICENSE).
