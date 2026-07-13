#!/usr/bin/env bash
# Hermetic Definition of Done — catalog validation + IaC gate (warn mode).
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

echo "== verify: iac gate (warn) =="
bash scripts/iac_gate.sh warn

echo "verify: ok"
