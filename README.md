# SOC-2 — local scorer for wired controls

This repository scores only the controls that are actually wired: **8
technical** OPA/Rego checks and **9 procedural** date manifests. Other IDs in
`catalog/` are not part of the score. See [catalog/README.md](catalog/README.md).

[![policy-ci](https://github.com/SafetyMP/SOC-2/actions/workflows/policy-ci.yml/badge.svg?branch=main)](https://github.com/SafetyMP/SOC-2/actions/workflows/policy-ci.yml)
[![License: Apache-2.0](https://img.shields.io/github/license/SafetyMP/SOC-2)](LICENSE)

A score is evidence about those wired checks. It is **not** a CPA opinion,
**not** a SOC 2 Type I/II report, and **not** an ISO/IEC 27001 certification.
An auditor still opines. See [SECURITY.md](SECURITY.md).

An empty payload or an empty list scores **MISSING**. A deny rule that sees
no rows is not a pass.

## What it scores

| Layer | In this repo | What the scorer uses |
|-------|--------------|----------------------|
| L0 Catalog | `catalog/` | Wired IDs only. The YAML still lists controls this job does not run |
| L1 Policy | `policies/` | The 7 Rego packages in `engine/jobs.yaml`, plus `lib.payload` (empty input is not a pass) |
| L2 Sensors | `sensors/` | GitHub, Terraform, and procedural manifests. Cloud, Kubernetes, and SAST adapters are stubs and are not scored |
| L3–L4 Engine | `engine/` | Evaluator + clean/effective scorer |
| L5 Locker | `evidence/` + local MinIO | Dev locker + Merkle log; prod replica stubbed |
| L6 Waivers | `exceptions/` | Time-boxed policy-as-data. Waivers do not count as clean |
| L7 IaC gate | `scripts/iac_gate.sh` | Warn-mode sample Terraform for encryption at rest only |

Unimplemented Rego is reported separately from the score so a missing package
does not count as green.

## What this is not

- A SOC 2 **certification**, attestation, or CPA opinion
- An ISO/IEC 27001 certification
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
| [catalog/](catalog/README.md) | Wired control IDs this scorer runs |
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


## Documentation map

[docs/README.md](docs/README.md) lists the repository layout. Community policy files are the root `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, and `SECURITY.md`.
