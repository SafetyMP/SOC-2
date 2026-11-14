---
applyTo: "**/*.rego"
---

# Rego conventions

- Preserve package names and `data.*` query paths used by the catalog and evaluator.
- Pair policy changes with `*_test.rego` cases for the changed behavior, including
  missing input and relevant negative cases. Never add a default pass to unblock CI.
- Keep findings attributable to their control IDs. Do not let one control's failure
  mark unrelated controls as failed or passing.
- Explain what a check actually observes. A configured setting does not prove
  operating effectiveness, certification, or universal enforcement.
- Keep catalog wiring, sensor payload shape, and policy semantics aligned. A
  documentation-only change must not alter them.
- Run `opa fmt --fail policies/`, `opa check policies/`, `opa test policies/`, and
  the repository verification command for relevant changes.
