import argparse
import json
import os


def _walk(module):
    for r in module.get("resources", []):
        yield r
    for child in module.get("child_modules", []):
        yield from _walk(child)


def _has_cmk(value):
    """A non-empty kms_key_id or kms_master_key_id is a customer-managed key."""
    if isinstance(value, dict):
        for field in ("kms_key_id", "kms_master_key_id"):
            key = value.get(field)
            if isinstance(key, str) and key.strip():
                return True
        return any(_has_cmk(child) for child in value.values())
    if isinstance(value, list):
        return any(_has_cmk(child) for child in value)
    return False


_READ_ONLY_ACTIONS = frozenset({"no-op", "read"})


def _variable_value(plan, name):
    variables = plan.get("variables")
    if not isinstance(variables, dict):
        return None
    spec = variables.get(name)
    if not isinstance(spec, dict):
        return None
    return spec.get("value")


def _plan_mutates(plan):
    """True when any resource change is outside no-op and read."""
    changes = plan.get("resource_changes")
    if not isinstance(changes, list):
        return False
    for item in changes:
        change = item.get("change") if isinstance(item, dict) else None
        actions = change.get("actions") if isinstance(change, dict) else None
        if isinstance(actions, list) and not set(actions).issubset(_READ_ONLY_ACTIONS):
            return True
    return False


def _change_plan(plan):
    environment = "nonprod" if _variable_value(plan, "environment") == "nonprod" else "prod"
    return {
        "id": "terraform",
        "environment": environment,
        "mutating": _plan_mutates(plan),
        "approved": _variable_value(plan, "change_approved") is True,
    }


def normalize_plan(plan):
    data_resources = []
    root = (plan.get("planned_values") or {}).get("root_module") or {}
    resources = list(_walk(root))

    sse_refs = {}
    for r in resources:
        if r.get("type") == "aws_s3_bucket_server_side_encryption_configuration":
            values = r.get("values") or {}
            ref = str(values.get("bucket", ""))
            sse_refs[ref] = _has_cmk(values)

    for r in resources:
        t = r.get("type")
        v = r.get("values") or {}
        addr = r.get("address", "")
        if t == "aws_db_instance":
            data_resources.append({"id": addr, "type": "rds", "environment": "prod",
                                   "encrypted": bool(v.get("storage_encrypted", False)),
                                   "customer_managed_key": _has_cmk(v)})
        elif t in ("aws_ebs_volume", "google_compute_disk", "azurerm_managed_disk"):
            data_resources.append({"id": addr, "type": "ebs_volume", "environment": "prod",
                                   "encrypted": bool(v.get("encrypted", False)),
                                   "customer_managed_key": _has_cmk(v)})
        elif t == "aws_s3_bucket":
            inline = bool(v.get("server_side_encryption_configuration"))
            linked_cmk = False
            linked = False
            for ref, cmk in sse_refs.items():
                if addr in ref or ref.endswith(addr + ".id"):
                    linked = True
                    linked_cmk = linked_cmk or cmk
            data_resources.append({"id": addr, "type": "s3_bucket", "environment": "prod",
                                   "encrypted": inline or linked,
                                   "customer_managed_key": _has_cmk(v) or linked_cmk})
    return {"data_resources": data_resources, "plans": [_change_plan(plan)]}


def from_plan_file(path):
    with open(path) as fh:
        return normalize_plan(json.load(fh))


def main():
    ap = argparse.ArgumentParser(description="Terraform-plan sensor -> normalized data_resources payload")
    ap.add_argument("--plan", required=True, help="path to `terraform show -json <plan>` output")
    ap.add_argument("--out", default=None, help="write payload here (default: stdout)")
    args = ap.parse_args()
    payload = from_plan_file(args.plan)
    if args.out:
        os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
        with open(args.out, "w") as fh:
            json.dump(payload, fh, indent=2)
        print(f"# wrote {len(payload['data_resources'])} data_resources -> {args.out}")
    else:
        print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
