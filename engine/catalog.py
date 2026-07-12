import glob
import os
import re

import yaml

DOMAIN_FROM_FILE = {
    "access-control": "access-control",
    "encryption": "encryption",
    "logging": "logging",
    "network": "network",
    "change-mgmt": "change-management",
    "vulnerability-mgmt": "vulnerability-management",
    "backup": "backup-availability",
    "procedural": "procedural",
}


def _load_controls(path):
    out = []
    for doc in yaml.safe_load_all(open(path)):
        if doc is None:
            continue
        if isinstance(doc, list):
            out.extend(doc)
        elif isinstance(doc, dict):
            out.append(doc)
    return out


class Control:
    def __init__(self, raw, domain):
        self.id = raw["id"]
        self.title = raw.get("title", "")
        self.soc2 = list(raw.get("soc2", []))
        self.iso27001 = list(raw.get("iso27001", []))
        self.criticality = int(raw.get("criticality", 1))
        self.assertion_type = raw.get("assertion_type", "technical")
        self.evidence_validity = raw.get("evidence_validity", "P30D")
        self.sensors = list(raw.get("sensors", []))
        self.rego_packages = list(raw.get("rego_packages", []))
        self.domain = domain

    def framework_refs(self):
        return {"soc2": self.soc2, "iso27001": self.iso27001}


class Catalog:
    def __init__(self, controls):
        self.controls = {c.id: c for c in controls}
        self.pkg_to_controls = {}
        for c in controls:
            for pkg in c.rego_packages:
                self.pkg_to_controls.setdefault(pkg, []).append(c.id)

    @classmethod
    def load(cls, catalog_dir="catalog"):
        controls = []
        for path in sorted(glob.glob(os.path.join(catalog_dir, "*.yaml"))):
            stem = os.path.splitext(os.path.basename(path))[0]
            domain = DOMAIN_FROM_FILE.get(stem, stem)
            for raw in _load_controls(path):
                controls.append(Control(raw, domain))
        return cls(controls)

    def domains(self):
        seen = []
        for c in self.controls.values():
            if c.domain not in seen:
                seen.append(c.domain)
        return seen

    def implemented_packages(self, policies_dir="policies"):
        declared = set()
        for path in glob.glob(os.path.join(policies_dir, "**", "*.rego"), recursive=True):
            if os.path.basename(path).endswith("_test.rego"):
                continue
            with open(path) as fh:
                for line in fh:
                    m = re.match(r"^package\s+(\S+)", line)
                    if m:
                        declared.add(m.group(1))
        return declared
