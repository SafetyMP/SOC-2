#!/usr/bin/env bash
# Local verification: repository, policies, Python/browser tests, and IaC warn gate.
# No live collection, cloud apply, evidence upload, or Docker startup.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ -x ./scripts/check-stub-canary.sh ]]; then
  ./scripts/check-stub-canary.sh
fi

if [[ -x ./scripts/check-harness.sh ]]; then
  ./scripts/check-harness.sh
fi

echo "== verify: catalog =="
python3 scripts/validate_catalog.py

echo "== verify: repository and discovery =="
python3 scripts/check_repository.py
python3 scripts/test_check_repository.py

echo "== verify: Rego =="
opa fmt --fail policies/
opa check policies/
opa test policies/

echo "== verify: unit tests =="
for t in engine/test_*.py evidence/test_*.py sensors/test_*.py; do
  python3 "$t"
done

echo "== verify: workspace =="
python3 scripts/test_export_workspace.py
python3 scripts/test_assess_github.py
python3 scripts/test_serve_workspace.py
node --check demo/app.js
node --test demo/*.test.mjs

echo "== verify: iac gate (warn) =="
bash scripts/iac_gate.sh warn

echo "verify: ok"
