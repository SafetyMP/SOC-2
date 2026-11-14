# Contributing to the SOC-2 readiness workspace

SOC-2 combines a local GitHub assessment workflow, a browser workspace for
reviewing findings, and a Python/Rego policy and sensor library. Contributions
should help users understand the evidence, see what remains outside scope, and
plan a verifiable next action. Start with the [project overview](README.md),
[documentation map](docs/README.md), and [Code of Conduct](CODE_OF_CONDUCT.md).

## Choose the right workflow

- Explore the [public sample](https://safetymp.github.io/SOC-2/) without accounts or
  credentials. Its source data is synthetic.
- Follow the [local assessment guide](docs/local-github-assessment.md) for one real
  GitHub repository. That workflow assesses three configuration checks, leaves
  other controls outside scope, and keeps evidence outside the checkout.
- Use the [workspace guide](demo/README.md) for browser development, fixture
  exports, and reopening saved reviews.
- See [AGENTS.md](AGENTS.md) for the code map and commands used by coding agents.

## Develop and verify

Keep the existing Python, OPA/Rego, and buildless HTML/CSS/JavaScript stack.
Python dependencies are installed with `python3 -m pip install -r requirements.txt`.
Full verification also requires OPA, Terraform, and Node.js on `PATH`; CI provides
the pinned runtime versions used by its jobs.

Run the repository verification from the checkout root:

```bash
./scripts/verify.sh
```

For focused iteration on the workspace and local assessment:

```bash
python3 scripts/test_export_workspace.py
python3 scripts/test_assess_github.py
python3 scripts/test_serve_workspace.py
node --check demo/app.js
node --test demo/*.test.mjs
python3 scripts/check_repository.py
```

Keep tests next to the component they cover. Existing Python tests are executable
`test_*.py` scripts using unittest or assertions; browser-model tests use Node's
built-in test runner. Policy tests are `*_test.rego` files. No npm build is required.
When changing an interaction, check it in the browser as well as testing its data
model. Cover empty/error states, keyboard use, and narrow screens where relevant.

Tests must use synthetic data and must not contact real providers. Run a real
collection only for an explicitly selected repository when the task calls for it;
keep its report and evidence local. Report the commands actually run, their results,
and any environment limitation rather than claiming an unrun check passed.

## Preserve the evidence boundary

- Never commit credentials, tokens, private repository details, or real assessment
  reports, evidence, or review exports. Use minimal synthetic reproductions in
  issues, tests, screenshots, and pull requests.
- Keep sample and real results distinct. Empty, inaccessible, or unsupported inputs
  must not become passes. Unevaluated controls remain outside the score.
- Review notes are planning data. They never change measured results or create an
  accepted exception. A deliberately unmet review policy must remain visible.
- The browser must not receive GitHub credentials or upload evidence. Preserve the
  loopback viewer's file allowlist, request checks, and restrictive response headers.
- Do not change policy semantics, runtime behavior, or dependency versions as an
  incidental documentation edit. Describe intentional changes and test them.
- Do not describe a score as SOC 2 certification, a CPA opinion, or complete
  framework coverage. Explain exactly what each check observes.

## Propose and review changes

Use an [issue template](https://github.com/SafetyMP/SOC-2/issues/new/choose) for a bug
or proposed improvement. State the user's problem and expected behavior. For
security vulnerabilities, use the private route in [SECURITY.md](SECURITY.md).

Open a focused pull request against `main` and fill in the PR template. Required
checks are `validate-catalog`, `validate-policies`, and `verify-demo`; branches must
be up to date before merging. The repository uses a solo-maintainer merge policy,
so an independent approval count is not currently required. This operational
choice does not satisfy the assessment policy's two-reviewer threshold.
Independent review is still useful for changes to evidence handling, policy
semantics, or privacy boundaries.

Keep GitHub Actions pinned to full commit SHAs with a version comment. Review
Dependabot updates before merging. Documentation and public metadata should
reflect implemented behavior; mark historical designs and future work clearly.

## License

By contributing, you agree that your contributions are licensed under the
[Apache License 2.0](LICENSE).
