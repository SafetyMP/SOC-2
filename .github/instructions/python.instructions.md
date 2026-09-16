---
applyTo: "**/*.py"
---

# Python coding standards (September 2026)

- Type-annotate public functions and module-level APIs.
- Follow the existing Ruff / pyproject configuration. Do not disable rules repository-wide to land a change.
- Tests use pytest and the existing `tests/` layout.
- Never print, log, or commit secrets, `.env` values, or private keys.
- Do not claim a gate passed from prose. Run the documented verify command and keep the output.

## This repository

- Readiness-sensor pack: OPA catalog + GitHub/org sensors that emit evidence.
- Do not claim SOC 2 certification, attestation, or a CPA opinion.
- Do not treat fixture scores or the demo locker as production evidence.
- Do not add a new corporate-site-harness program here without the CEO workflow.
