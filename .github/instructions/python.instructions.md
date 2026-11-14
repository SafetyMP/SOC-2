---
applyTo: "**/*.py"
---

# Python conventions

- Preserve the existing Python 3.11+ stack. Type-annotate public functions and APIs.
- Reuse the local component's style. Tests are executable `test_*.py` files using
  unittest or assertions; do not assume a separate `tests/` directory or pytest.
- Keep credentials out of arguments, logs, exceptions, reports, and fixtures.
  Provider errors need safe diagnostics rather than raw stderr or response bodies.
- New real evidence belongs in fresh private files outside Git checkouts. Never
  overwrite retained evidence as part of collection or tests.
- Provider requests must be explicit, bounded, and read-only for this assessment
  workflow. Keep the real collector separate from the fixture runner.
- Validate untrusted input before evaluation; unreadable or unsupported settings
  remain MISSING. Do not relax validation to manufacture passing results.
- Run the relevant script tests and `./scripts/verify.sh`; state any environment
  limitation instead of claiming checks that were not run.
