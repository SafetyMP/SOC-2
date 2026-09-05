# Copilot / community agents

This repository is a **readiness-sensor example pack**: OPA/Rego catalog plus
GitHub/org sensors that emit evidence. It is not a GRC product and does not
certify SOC 2.

## Verify

```bash
./scripts/verify.sh
```

Optional (not the Definition of Done):

```bash
python3 -m engine.run
./scripts/iac_gate.sh warn
```

## Never

- Never claim SOC 2 certification, attestation, or a CPA opinion.
- Never treat fixture scores or the demo locker as production evidence.
- Never change catalog, Rego, or sensor **semantics** in a docs-only PR.
- Never add a new corporate-site-harness program here (CEO workflow; see
  [docs/DESIGN-PIVOT.md](../docs/DESIGN-PIVOT.md)).

Community contract: [AGENTS.md](../AGENTS.md).
Positioning: [docs/DESIGN-PIVOT.md](../docs/DESIGN-PIVOT.md).
