# Engine (L3 eval + L4 scorer + L6 waiver eval)

Consumes normalized sensor payloads, runs the Rego policy library, and emits
per-control verdicts that the readiness scorer rolls up.

## Components (to be implemented)

- **evaluator** — binds each sensor payload to the Rego packages named in the
  catalog (`rego_packages`), runs `opa eval`, and maps `deny` outputs to
  control verdicts (`PASS` / `FAIL`).
- **aggregator** — folds sensor verdicts + procedural evidence into one verdict
  per control, attaching exception (`EXCEPTION`) where a waiver applies.
- **scorer** — computes clean vs. effective readiness per domain/framework
  (see `docs/readiness-layer-design.md §7`). Applies validity decay: records
  past `valid_until` become `EXPIRED` (not-ready) in the nightly recompute.
- **waiver eval** — evaluates `exceptions/*.yaml` as Rego data at scoring time;
  expired waivers vanish and the control reverts to `FAIL`.

## Verdict state machine

```
sensor ──► PASS | FAIL
procedural ──► PASS | MISSING | EXPIRED
FAIL + unexpired waiver ──► EXCEPTION
age > valid_until ──► EXPIRED
no evidence ──► MISSING
```

`Ready(c) := status(c) ∈ {PASS, EXCEPTION(unexpired)}`.
