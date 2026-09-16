---
applyTo: "**/*.rego"
---

# Rego coding standards (September 2026)

- Fail closed. Do not add a default allow to unblock an agent or a test.
- Keep package names and `data.*` paths consistent with existing tests.
- Do not encode identity or jurisdiction in query parameters.
- Pair policy edits with tests unless this repository is a documented mirror that forbids local `*_test.rego`.

## This repository

- Catalog and IaC gates live with the sensor pack. Do not change catalog/Rego semantics in a docs-only PR.
