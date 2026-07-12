#!/usr/bin/env bash
# IaC enforcement gate (L7) — runs the Rego policy library over a terraform plan.
# Usage: scripts/iac_gate.sh [warn|enforce]   (default: warn, per design §12 burn-in)
#   warn    — report violations, exit 0
#   enforce — exit 1 on any violation (blocks terraform apply / the PR)
set -euo pipefail

MODE="${1:-warn}"
DIR="${IAC_DIR:-terraform-examples}"
PKG="${IAC_PKG:-encryption.at_rest_required}"

command -v terraform >/dev/null || { echo "terraform not found"; exit 2; }
command -v opa >/dev/null        || { echo "opa not found";        exit 2; }

PLAN=$(mktemp -t tfplan.XXXXXX)
PLANJSON=$(mktemp -t tfplan.json.XXXXXX)
PAYLOAD=$(mktemp -t payload.json.XXXXXX)
trap 'rm -f "$PLAN" "$PLANJSON" "$PAYLOAD"' EXIT

echo ">> terraform plan ($DIR)"
terraform -chdir="$DIR" init -input=false -lock=false >/dev/null 2>&1 || true
terraform -chdir="$DIR" plan -input=false -out="$PLAN" >/dev/null
terraform -chdir="$DIR" show -json "$PLAN" > "$PLANJSON"

echo ">> normalize plan -> data_resources"
python3 -m sensors.terraform --plan "$PLANJSON" --out "$PAYLOAD" >/dev/null

echo ">> policy gate: $PKG ($MODE mode)"
DENY=$(opa eval -f json -d policies -i "$PAYLOAD" "data.$PKG.deny" \
  | python3 -c "import sys,json
d=json.load(sys.stdin)
r=d.get('result',[])
v=r[0]['expressions'][0]['value'] if r else []
print('\n'.join(v) if isinstance(v,list) else str(v))")

if [ -z "$DENY" ]; then
  echo "PASS: no policy violations"
  exit 0
fi
echo "FINDINGS:"
echo "$DENY"
if [ "$MODE" = "enforce" ]; then
  echo "BLOCK: enforce mode - plan rejected"
  exit 1
fi
echo "(warn mode - not blocking)"
exit 0
