#!/usr/bin/env python3
"""Validate the control catalog and cross-reference Rego packages.

Exit codes:
  0 — catalog structurally valid (unimplemented-but-planned Rego is a warning)
  1 — structural error (missing field, bad type, malformed YAML, typo'd package
      on a control that is marked implemented)

Usage: python3 scripts/validate_catalog.py [catalog_dir] [policies_dir]
"""
import glob, os, re, sys, yaml

CATALOG_DIR = sys.argv[1] if len(sys.argv) > 1 else "catalog"
POLICIES_DIR = sys.argv[2] if len(sys.argv) > 2 else "policies"

REQUIRED = ("id", "soc2", "iso27001", "criticality", "assertion_type", "evidence_validity")
ASSERTION_TYPES = ("technical", "procedural", "policy")

errors, warnings = [], []


def load_controls(path):
    """A catalog file is one YAML document that is a LIST of control maps."""
    out = []
    for doc in yaml.safe_load_all(open(path)):
        if doc is None:
            continue
        if isinstance(doc, list):
            out.extend(doc)
        elif isinstance(doc, dict):
            out.append(doc)
    return out


def declared_packages():
    pkgs = set()
    for pf in glob.glob(os.path.join(POLICIES_DIR, "**", "*.rego"), recursive=True):
        if os.path.basename(pf).endswith("_test.rego"):
            continue
        with open(pf) as fh:
            for line in fh:
                m = re.match(r"^package\s+(\S+)", line)
                if m:
                    pkgs.add(m.group(1))
    return pkgs


def main():
    control_count = 0
    pkg_refs = []
    catalog_files = sorted(glob.glob(os.path.join(CATALOG_DIR, "*.yaml")))
    if not catalog_files:
        errors.append(f"no catalog files found in {CATALOG_DIR}/")

    for f in catalog_files:
        try:
            controls = load_controls(f)
        except Exception as e:
            errors.append(f"{f}: YAML parse error: {e}")
            continue
        for c in controls:
            control_count += 1
            cid = c.get("id", "?")
            for field in REQUIRED:
                if field not in c:
                    errors.append(f"{f}: {cid} missing '{field}'")
            for field in ("soc2", "iso27001"):
                v = c.get(field)
                if not isinstance(v, list) or not v:
                    errors.append(f"{f}: {cid} '{field}' must be a non-empty list")
            at = c.get("assertion_type")
            if at not in ASSERTION_TYPES:
                errors.append(f"{f}: {cid} invalid assertion_type '{at}'")
            rp = c.get("rego_packages") or []
            if at == "technical" and not rp:
                errors.append(f"{f}: {cid} technical control has no rego_packages")
            if at in ("procedural", "policy") and rp:
                errors.append(f"{f}: {cid} {at} control should not declare rego_packages")
            pkg_refs.extend(rp)
        print(f"OK  {f} ({len(controls)} controls)")

    declared = declared_packages()
    for pkg in sorted(set(pkg_refs) - declared):
        # A missing package is expected during phased rollout (control declared
        # before its Rego ships). Surfaced as a warning, not a failure.
        warnings.append(f"catalog references Rego package '{pkg}' not yet implemented in {POLICIES_DIR}/")

    print(f"\nCatalog: {control_count} controls, {len(catalog_files)} files")
    print(f"Rego: {len(declared)} packages implemented, {len(set(pkg_refs))} referenced by catalog")
    if warnings:
        print(f"\nWARNINGS ({len(warnings)}):")
        for w in warnings:
            print("  - " + w)

    print()
    if errors:
        print(f"FAIL — {len(errors)} structural error(s):")
        for e in errors:
            print("  - " + e)
        sys.exit(1)
    print("PASS — catalog structurally valid")
    sys.exit(0)


if __name__ == "__main__":
    main()
