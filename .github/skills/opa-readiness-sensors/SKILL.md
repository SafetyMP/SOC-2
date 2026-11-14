---
name: opa-readiness-sensors
description: Change SOC-2 Python/Rego control evaluation or sensors while preserving scoped results, local evidence, and the distinction between real assessments and synthetic fixtures.
---

# Policy and sensor work

The policy library powers a readiness workspace. Start with the
[architecture and documentation map](../../../docs/README.md),
[agent instructions](../../../AGENTS.md), and the affected component's README.

- Keep catalog IDs, Rego packages, normalized payloads, and attributed findings
  consistent. Describe policy changes explicitly and add relevant regression cases.
- The isolated real workflow is `scripts/assess_github.py`; it currently evaluates
  three GitHub configuration checks. Do not quietly fill missing inputs with sample
  fixtures or apply example waivers.
- Empty, unavailable, or unsupported evidence is MISSING, not PASS. Controls
  without an evaluation stay outside the score. Keep scope separate from readiness.
- Local review notes do not change policy results. Preserve a failed independent-
  review policy even when zero required approvals is an intentional operating choice.
- Use synthetic test data and bounded read-only provider collection when explicitly
  required. Never commit raw provider responses, secrets, or real assessment output.
- Run policy/component tests and `./scripts/verify.sh` before claiming success.
  Keep source, test, and live-verification evidence distinct.

A configuration check is not an audit opinion, SOC 2 certification, or proof of
operating effectiveness. The optional demo locker is not a production custody
system, and historical architecture plans are not implemented capabilities.
