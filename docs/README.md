# Documentation map

The scorer covers the wired controls only. Start at the root [README](../README.md) and [catalog/README.md](../catalog/README.md).

- [DESIGN-PIVOT.md](./DESIGN-PIVOT.md)
- [readiness-layer-design.md](./readiness-layer-design.md)

## Repository layout

| Path | What it is |
| --- | --- |
| `catalog/` | Control catalog. Not every ID is scored |
| `policies/` | Rego packages the scorer runs |
| `sensors/` | GitHub, Terraform, and procedural sensors. Cloud, Kubernetes, and SAST adapters are stubs |
| `engine/` | Evaluator. An empty payload scores MISSING |
| `procedural/` | Date manifests |
| `scripts/` | Verify and the sample IaC gate |
| `evidence/`, `exceptions/`, `fixtures/` | Local locker and sample inputs |

Community files: root [CONTRIBUTING.md](../CONTRIBUTING.md), [CODE_OF_CONDUCT.md](../CODE_OF_CONDUCT.md), [SECURITY.md](../SECURITY.md).


## Canonical community files

`CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, and `SECURITY.md` are at the repository root. This repository does not keep a second copy under `.github/`, because GitHub would show that copy instead of the root file.
