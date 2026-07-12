import argparse
import json
import os


def _walk(module):
    for r in module.get("resources", []):
        yield r
    for child in module.get("child_modules", []):
        yield from _walk(child)


def normalize_plan(plan):
    data_resources = []
    root = (plan.get("planned_values") or {}).get("root_module") or {}
    resources = list(_walk(root))

    sse_refs = set()
    for r in resources:
        if r.get("type") == "aws_s3_bucket_server_side_encryption_configuration":
            ref = str((r.get("values") or {}).get("bucket", ""))
            sse_refs.add(ref)

    for r in resources:
        t = r.get("type")
        v = r.get("values") or {}
        addr = r.get("address", "")
        if t == "aws_db_instance":
            data_resources.append({"id": addr, "type": "rds", "environment": "prod",
                                   "encrypted": bool(v.get("storage_encrypted", False))})
        elif t in ("aws_ebs_volume", "google_compute_disk", "azurerm_managed_disk"):
            data_resources.append({"id": addr, "type": "ebs_volume", "environment": "prod",
                                   "encrypted": bool(v.get("encrypted", False))})
        elif t == "aws_s3_bucket":
            inline = bool(v.get("server_side_encryption_configuration"))
            linked = any(addr in ref or ref.endswith(addr + ".id") for ref in sse_refs)
            data_resources.append({"id": addr, "type": "s3_bucket", "environment": "prod",
                                   "encrypted": inline or linked})
    return {"data_resources": data_resources}


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
