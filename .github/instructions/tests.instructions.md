---
applyTo: "**/*test*.py,**/tests/**/*.py"
---

# Test standards (September 2026)

- pytest is the runner. Add tests next to the existing `tests/` layout.
- Do not skip or weaken verify, ruff, or adversarial gates.
- Do not invent a passing gate from prose.
- Fixtures are synthetic. Never commit secrets or live tenant data.

## This repository

- Definition of Done: `./scripts/verify.sh`.
- `python3 -m engine.run` and `./scripts/iac_gate.sh warn` are optional, not the stop-hook oracle.
