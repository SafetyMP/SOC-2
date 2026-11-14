---
name: code-review
description: Review SOC-2 workspace, assessment, policy, and documentation changes for evidence integrity, privacy, truthful scope, and meaningful verification.
---

# Review the SOC-2 readiness workspace

Read the changed files and relevant callers, then give concrete findings tied to
observable behavior. Use [AGENTS.md](../../../AGENTS.md) and
[CONTRIBUTING.md](../../../CONTRIBUTING.md) for the current stack and commands.

## Check the result users will see

- Real GitHub assessments use only the explicitly selected repository and scoped
  inputs. The public demo stays synthetic, and unevaluated controls never count
  as passing. Do not treat the legacy mixed-input `--live` runner as real-only.
- Failed, missing, or unsupported evidence stays visible. Review notes and progress
  cannot change verdicts or create accepted exceptions.
- Real reports and credentials remain local. Check credential redaction, private
  output paths, loopback-only serving, origin/Host checks, and the asset allowlist.
- Imports and startup-restored reviews use shared validation before application.
  Untrusted report text must not become HTML, executable code, or network requests.
- Check descriptions match measured facts. Flag certification, CPA-opinion,
  operating-effectiveness, or complete-coverage claims unsupported by the code.
- Browser changes preserve useful empty/error states, keyboard behavior, and
  readability on small screens. Public metadata describes actual capabilities.

## Assess validation proportionately

`./scripts/verify.sh` is the repository verification command. Look for focused
regression coverage where behavior changed and distinguish local tests, mocked
collection, and real external validation. Flag fabricated success, omitted
material failures, weakened tests, and secrets or real evidence in a diff.

Prefer actionable correctness and security findings over unrelated upgrades,
formatter churn, or hypothetical refactors. Do not invent a two-approval merge
requirement: the repository currently uses a solo-maintainer workflow, while its
assessment policy can still report the resulting independent-review gap.
