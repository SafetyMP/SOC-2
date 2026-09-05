#!/usr/bin/env bash
# Hermetic Definition of Done — canary, harness, catalog, unit tests, IaC warn gate.
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

echo "== verify: unit tests =="
for t in engine/test_*.py evidence/test_*.py sensors/test_*.py; do
  python3 "$t"
done

echo "== verify: iac gate (warn) =="
bash scripts/iac_gate.sh warn

echo "verify: ok"
