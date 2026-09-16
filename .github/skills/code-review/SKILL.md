---
name: code-review
description: "Review SOC-2 sensor-pack PRs for honesty (no certification claims) and unchanged verify semantics. Use on pull requests that touch engine/, catalog, Rego, or sensors. Flag CPA-opinion language and new harness programs."
---

# Copilot code review — SOC-2

Use this skill when reviewing a pull request in this repository.

This is an **OPA readiness-sensor example pack**, not a GRC product.

- Reject SOC 2 certification or CPA-opinion claims.
- Reject treating fixture scores as production evidence.
- Reject new corporate-site-harness programs in this repo (CEO workflow).
- Verify with `./scripts/verify.sh`.


## Always flag

- Secrets, `.env` values, private keys, or real personal data in the diff
- Weakened or skipped verify / lint / typecheck / adversarial gates
- Invented success (prose claiming a gate passed with no command output)
- Fail-open authorization, skipped human approval, or agents recording `--actor user`

## Never request

- Drive-by major upgrades, formatter churn, or unrelated refactors
- Softening honesty disclaimers or certification claims
