---
applyTo: "**/test_*.py,**/*_test.rego,demo/*.test.mjs"
---

# Test conventions

- Follow the component's runner: Python test scripts use unittest or assertions,
  Rego uses `opa test`, and browser models use `node --test`.
- Use synthetic inputs. Mock provider responses; never commit real repository
  evidence, credentials, or customer data. Routine tests must not call GitHub.
- Cover meaningful behavior and boundary failures rather than mirroring code.
  For real assessments, verify scope isolation, failed/missing results, safe
  diagnostics, and no fixture or waiver mixing.
- For workspace imports and exports, verify notes cannot change verdicts or create
  waivers, real reports are rejected on hosted origins, and startup restoration
  preserves the selected snapshot.
- Keep loopback server tests local. Preserve traversal, cross-origin, mutation,
  size-limit, and no-cache/CSP checks when changing file handling.
- Run `./scripts/verify.sh` plus any focused check needed for the change. Do not
  skip or weaken existing gates, invent unconfigured gates, or report unrun tests
  as passing.
