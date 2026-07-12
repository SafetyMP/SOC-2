# Exceptions / waivers (L6)

A waiver is **policy-as-data**: a signed, time-boxed record that accepts a
failing control's risk until a fix lands. It is the _only_ sanctioned bypass for
an enforcing gate, and it is itself recorded evidence.

## How waivers are evaluated

At scoring time (`engine/waivers.py`):

1. `apply_decay` runs first — a `PASS` whose evidence is past `valid_until`
   becomes `EXPIRED` (not-ready).
2. `apply_waivers` runs next — a `FAIL` with an **unexpired**, approver-signed
   waiver becomes `EXCEPTION`.

`Ready_clean = status == PASS` · `Ready_effective = status in {PASS, EXCEPTION}`.
So a waiver raises **effective** readiness but never **clean** readiness — the
delta between the two is the risk-acceptance surface area, surfaced in every
report. An expired waiver vanishes automatically and the control reverts to
`FAIL`; no manual cleanup.

## Schema

Each `*.yaml` here is a list of waiver maps:

| Field                   | Required | Meaning                                                     |
| ----------------------- | -------- | ----------------------------------------------------------- |
| `id`                    | yes      | Stable waiver ID                                            |
| `control_id`            | yes      | Catalog control this waives                                 |
| `reason`                | yes      | Why the risk is accepted + remediation plan                 |
| `approver`              | yes      | Who accepted the risk (accountable)                         |
| `approved_at`           | yes      | When it was approved (ISO-8601)                             |
| `expires`               | yes      | When the waiver lapses (ISO-8601); after this, FAIL returns |
| `compensating_controls` | no       | Control IDs that mitigate while the waiver holds            |

## Files

- `CTRL-ACCESS-003.yaml` — sample waiver for the break-glass wildcard role
  (demonstrates the clean-vs-effective gap on `CTRL-ACCESS-003`).
