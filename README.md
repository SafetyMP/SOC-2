# SOC-2 — OPA/Rego readiness sensors

**Readiness-sensor example pack** for [SafetyMP](https://github.com/SafetyMP)
and
[corporate-site-harness](https://github.com/SafetyMP/corporate-site-harness):
a version-controlled control catalog, OPA/Rego checks, and GitHub/org sensors
that emit **evidence**, not a CPA opinion.

[![policy-ci](https://github.com/SafetyMP/SOC-2/actions/workflows/policy-ci.yml/badge.svg?branch=main)](https://github.com/SafetyMP/SOC-2/actions/workflows/policy-ci.yml)
[![License: Apache-2.0](https://img.shields.io/github/license/SafetyMP/SOC-2)](LICENSE)

Positioning: [docs/DESIGN-PIVOT.md](docs/DESIGN-PIVOT.md).

> **Permit rule:** A readiness score is not a CPA opinion. Sensors emit evidence; an auditor still opines. Same instinct: [SafetyMP](https://github.com/SafetyMP/SafetyMP).

> **Scope:** Runnable policy + sensor pack — **not** a certified audit product,
> **not** a SOC 2 Type I/II report, and **not** a claim that SafetyMP or any
> user of this repository is SOC 2 certified. An auditor still opines. See
> [SECURITY.md](SECURITY.md).

## What this is

OPA/Rego readiness sensors over one catalog. Frameworks (SOC 2 Trust Services
Criteria, ISO/IEC 27001:2022 Annex A) are **views**, not separate products.
Fixtures and optional live GitHub sensors produce failing or expired controls
instead of a stale spreadsheet.

| Layer | In this repo | Status |
|-------|--------------|--------|
| L0 Catalog | `catalog/` | Implemented (37 controls) |
| L1 Policy | `policies/` (Rego) | Phase 1 slice wired |
| L2 Sensors | `sensors/` | GitHub + Terraform + procedural implemented; cloud/k8s/SAST stubbed |
| L3–L4 Engine | `engine/` | Evaluator + clean/effective scorer |
| L5 Locker | `evidence/` + local MinIO | Dev locker + Merkle log; prod replica stubbed |
| L6 Waivers | `exceptions/` | Time-boxed policy-as-data |
| L7 IaC gate | `scripts/iac_gate.sh` | Warn-mode burn-in on sample Terraform |

Current wired slice: **8 technical + 9 procedural** controls of 37 catalog
entries. Coverage is reported separately from readiness so unimplemented Rego
does not silently score green.

## What this is not

- A SOC 2 **certification**, attestation, or CPA opinion
- A standalone GRC / audit product or a replacement for an ISMS, SIEM, or
  production object-lock locker
- Evidence you can show an auditor without replacing sample manifests, fixtures,
  and demo locker credentials with your own systems
- A new corporate-site-harness program (that wiring is a later factory slice;
  see [DESIGN-PIVOT.md](docs/DESIGN-PIVOT.md))

## Quick start

Definition of Done (hermetic):

```bash
./scripts/verify.sh
```

Requires `python3`, [PyYAML](https://pypi.org/project/PyYAML/),
[OPA](https://www.openpolicyagent.org/docs/latest/#running-opa), and
[Terraform](https://developer.hashicorp.com/terraform/install) on `PATH`.

Fixture assessment (not wired to the stop-hook):

```bash
python3 -m engine.run
```

IaC gate over `terraform-examples/` (intentional unencrypted RDS should appear
as a finding; `warn` exits 0, `enforce` exits 1):

```bash
./scripts/iac_gate.sh warn
```

Optional local evidence locker (demo credentials only — localhost):

```bash
docker compose up -d
```

## Layout

| Path | Role |
|------|------|
| [catalog/](catalog/README.md) | Canonical control IDs ↔ SOC 2 TSC ↔ ISO 27001 |
| [policies/](policies/) | Rego library + `opa test` |
| [sensors/](sensors/README.md) | Normalized JSON adapters (GitHub/org, Terraform, procedural) |
| [engine/](engine/README.md) | Eval, score, waivers |
| [evidence/](evidence/README.md) | Locker client, Merkle log, auditor packaging |
| [docs/DESIGN-PIVOT.md](docs/DESIGN-PIVOT.md) | Sensor-pack positioning (not a GRC product) |
| [docs/readiness-layer-design.md](docs/readiness-layer-design.md) | Architecture (design + implemented Phase 1) |
| [AGENTS.md](AGENTS.md) | Agent verify contract |
| [CONTRIBUTING.md](CONTRIBUTING.md) | How to propose changes |

## License

[Apache License 2.0](LICENSE).
