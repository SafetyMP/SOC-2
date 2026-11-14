# Reference exception overlays

This directory contains example waiver data for the legacy fixture/reference
engine. It is not part of the real GitHub assessment workflow. That workflow
reports only PASS, FAIL, and MISSING for its three scoped checks and never loads
these examples.

A workspace review note records an owner, progress, or rationale. It is **not a
waiver** and never changes a policy result. For example, a solo-maintainer decision
can remain visible beside a FAIL for a two-reviewer policy.

## Current reference behavior

[`engine/waivers.py`](../engine/waivers.py) applies validity decay first and exception
overlays second. A matching waiver considered unexpired can convert a FAIL to
EXCEPTION. Exceptions contribute to effective readiness, not clean readiness.
An expired waiver is ignored on the next assessment; the original failure remains.

This is a reference overlay, not an approval system: the implementation does not
verify signatures, approver identity, authorization, or compensating controls.
It also treats an absent or unparseable `expires` value as unexpired. Do not rely
on it as a production time-boxed enforcement boundary. Use explicit, valid expiry
values in examples, and keep these limitations distinct from future design goals.

## Example fields

| Field | Meaning |
| --- | --- |
| `id` | Example waiver identifier |
| `control_id` | Control whose FAIL may receive the overlay |
| `reason` | Rationale and intended remediation |
| `approver` | Descriptive approver label; not authenticated by this code |
| `approved_at` | Descriptive date; not verified as approval evidence |
| `expires` | Intended expiry; must be a valid timestamp for reliable time-boxing |
| `compensating_controls` | Contextual references; not evaluated by this overlay |

[`CTRL-ACCESS-003.yaml`](CTRL-ACCESS-003.yaml) is a sample break-glass wildcard-role
waiver. Its dates are fixed example data, not renewed authorization or a current
risk-acceptance decision for this repository or any user.

See [current architecture](../docs/architecture.md) for scope and
[local review restoration](../docs/local-github-assessment.md) for preserving notes
without changing findings.
