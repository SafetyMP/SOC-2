# Design pivot — readiness-sensor example pack

**Status:** Positioning document (September 2026). Does not change catalog, Rego,
or sensor semantics. **Does not claim SOC 2 certification.**

This repository is not a standalone GRC or audit product. It is the
**readiness-sensor example pack** for
[SafetyMP](https://github.com/SafetyMP) /
[corporate-site-harness](https://github.com/SafetyMP/corporate-site-harness):
an OPA/Rego control catalog plus GitHub and org sensors that **emit evidence**.
An auditor or CPA still opines. Nothing in this pack is a Type I/II report,
attestation, or certification.

## Why pivot

The GRC / compliance-as-code space is crowded. Shipping another “audit platform”
README invites the wrong comparison: commercial GRC suites, CPA firms, and
tools that sell a readiness score as if it were an opinion.

What this repo already does well is narrower and more useful to the factory:

| Keep | Stop selling as |
|------|-----------------|
| Version-controlled catalog (`catalog/`) mapped to TSC / ISO views | A complete ISMS or GRC system of record |
| OPA/Rego library (`policies/`) evaluated against fixtures and sensors | A certified control environment |
| GitHub / org / Terraform / procedural sensors (`sensors/`) | Live multi-cloud posture management |
| Evidence records and a local locker demo | Tamper-proof production object-lock for auditors |
| Hermetic `./scripts/verify.sh` | A substitute for a CPA engagement |

Evidence is a sensor output. Certification is a human opinion. Do not collapse
the two.

## What this pack is

1. **Catalog** — stable control IDs (`CTRL-*`) with SOC 2 TSC and ISO/IEC
   27001:2022 Annex A views. Frameworks are projections, not separate products.
2. **Rego** — provider-agnostic checks. Coverage is reported separately from
   readiness so unimplemented packages do not score green.
3. **Sensors** — adapters that normalize GitHub/org config, Terraform plans,
   and dated procedural manifests into JSON the policies evaluate.
4. **Reference loop** — evaluator, scorer, time-boxed waivers, and a demo
   locker so the pack is runnable. Those pieces stay reference, not a SaaS
   audit console.

## What this pack is not

- A SOC 2 **certification**, Type I/II report, or CPA opinion
- A claim that SafetyMP, this repository, or any consumer is SOC 2 certified
- A replacement for an ISMS, SIEM, or production evidence locker
- A second corporate-site-harness or a new factory program in this repo

See the README [What this is not](../README.md#what-this-is-not) section and
[SECURITY.md](../SECURITY.md).

## Next slice (not this change)

Wire `catalog/` and `sensors/` as an **example factory program** consumed by
corporate-site-harness. Keep **this** repository as the policy + sensor pack.

Do **not** implement that program here. A new harness program follows the
corporate CEO workflow (`program.json`, digest-bound gates, human approval).
This document only records the intended hand-off.

## Honesty rules

- Never write “SOC 2 certified”, “we are compliant”, or equivalent in README,
  badges, topics, or marketing copy.
- Scores, fixtures, and sample locker objects are **demo evidence**, not
  production attestation.
- If a change would require an auditor to accept this pack as an opinion,
  reject the change.
