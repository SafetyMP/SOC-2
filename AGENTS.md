# AGENTS.md — SOC-2 readiness platform

Harness profile: **solo** — hermetic verify only (no Docker in stop hook).

## Commands

| Command | Purpose |
|---------|---------|
| `./scripts/verify.sh` | Definition of Done (catalog + IaC warn gate + stub canary) |
| `./scripts/assess.sh` | Live readiness assessment (sensors → score → auditor package) |
| `./scripts/iac_gate.sh` | Rego policy over terraform plan (`warn` or `enforce`) |

## Definition of Done

```bash
./scripts/verify.sh
```

Integration assessment (`assess.sh --live`) is CI/nightly and manual — not wired to verify-on-stop.
