import argparse
import json
import os
import re
import subprocess


def _gh(path):
    proc = subprocess.run(["gh", "api", path], capture_output=True, text=True)
    if proc.returncode != 0:
        return None
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        return None


def origin_repo():
    proc = subprocess.run(["git", "remote", "get-url", "origin"], capture_output=True, text=True)
    url = proc.stdout.strip()
    m = re.search(r"github\.com[:/]([^/]+/[^/.\s]+)", url)
    return m.group(1) if m else None


def normalize(prot, repo, branch, environment="prod"):
    if not prot:
        return {
            "name": repo, "environment": environment, "protected": False,
            "allow_force_pushes": False, "required_reviewers": 0,
            "enforce_admins": False, "required_status_checks": False,
            "_source": {"branch": branch, "live": True},
        }
    rpr = prot.get("required_pull_request_reviews") or {}
    rsc = prot.get("required_status_checks") or {}
    return {
        "name": repo,
        "environment": environment,
        "protected": True,
        "allow_force_pushes": bool((prot.get("allow_force_pushes") or {}).get("enabled", False)),
        "required_reviewers": int(rpr.get("required_approving_review_count", 0) or 0),
        "enforce_admins": bool((prot.get("enforce_admins") or {}).get("enabled", False)),
        "required_status_checks": bool(rsc.get("contexts") or rsc.get("checks")),
        "_source": {"branch": branch, "live": True},
    }


def collect(repo, environment="prod"):
    info = _gh(f"repos/{repo}") or {}
    branch = info.get("default_branch", "main")
    prot = _gh(f"repos/{repo}/branches/{branch}/protection")
    return normalize(prot, repo, branch, environment)


def write_payload(repos, out_path):
    payload = {"repositories": []}
    for r in repos:
        payload["repositories"].append(collect(r))
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w") as fh:
        json.dump(payload, fh, indent=2)
    return out_path


def main():
    ap = argparse.ArgumentParser(description="GitHub branch-protection sensor")
    ap.add_argument("--repo", action="append", default=None, help="OWNER/REPO (repeatable; default: origin)")
    ap.add_argument("--out", default="sensors/out/github.json")
    args = ap.parse_args()
    repos = args.repo or [origin_repo()]
    if not repos or not repos[0]:
        raise SystemExit("no repo given and origin remote not found")
    path = write_payload(repos, args.out)
    with open(path) as fh:
        print(fh.read())


if __name__ == "__main__":
    main()
