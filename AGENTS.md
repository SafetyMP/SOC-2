# AGENTS.md — SOC-2 readiness-sensor pack

Harness profile: **solo** — hermetic verify only (no Docker in stop hook).

This repo is an OSS **policy + sensor pack** (OPA/Rego catalog, GitHub/org
sensors, evidence records). It does **not** certify SOC 2 compliance and is
not a standalone GRC product. See [docs/DESIGN-PIVOT.md](docs/DESIGN-PIVOT.md).

## Commands

| Command | Purpose |
|---------|---------|
| `./scripts/verify.sh` | Definition of Done (canary + harness + catalog + unit tests + IaC warn gate) |
| `python3 -m engine.run` | Fixture readiness assessment (sensors → score). Optional: `--live` / `--org` |
| `./scripts/iac_gate.sh` | Rego policy over terraform plan (`warn` or `enforce`) |

## Definition of Done

```bash
./scripts/verify.sh
```

Live GitHub collection (`python3 -m engine.run --live`) is manual — not wired to verify-on-stop.

Do not implement a new corporate-site-harness program in this repository without
the corporate CEO workflow.
