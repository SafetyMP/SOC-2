#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
errors=0
for f in .harness/profile.yaml .harness/VERSION AGENTS.md scripts/verify.sh .cursor/hooks.json; do
  [[ -f "$f" ]] || { echo "MISSING: $f" >&2; errors=$((errors+1)); }
done
python3 -c "import json; json.load(open('.cursor/hooks.json'))"
python3 -m py_compile .cursor/hooks/*.py
[[ "$errors" -eq 0 ]] || exit 1
echo "check-harness: ok"
