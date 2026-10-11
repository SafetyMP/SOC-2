#!/usr/bin/env bash
# IaC enforcement gate (L7) — runs the Rego policy library over a terraform plan.
# Usage: scripts/iac_gate.sh [warn|enforce]   (default: warn, per design §12 burn-in)
#   warn    — report violations and exit 0; an empty payload prints MISSING and exits 1
#   enforce — exit 1 on any violation or on an empty payload
#
# IAC_PAYLOAD, when set, scores that already-normalized JSON and skips terraform.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

MODE="${1:-warn}"
DIR="${IAC_DIR:-terraform-examples}"
PKG="${IAC_PKG:-encryption.at_rest_required}"

run_gate() {
  python3 -m engine.iac_gate --mode "$MODE" --package "$PKG" --payload "$1"
}

if [[ -n "${IAC_PAYLOAD:-}" ]]; then
  run_gate "$IAC_PAYLOAD" || exit $?
  exit 0
fi

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
run_gate "$PAYLOAD" || exit $?
exit 0
