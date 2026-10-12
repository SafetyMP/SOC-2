import argparse
import json
import os
import re
import subprocess


class SensorError(RuntimeError):
    """The GitHub sensor could not read a repository list from gh."""


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


def normalize(prot, repo, branch, environment="prod", ci_workflow=False):
    if not prot:
        return {
            "name": repo, "environment": environment, "protected": False,
            "allow_force_pushes": False, "required_reviewers": 0,
            "enforce_admins": False, "required_status_checks": False,
            "ci_workflow": ci_workflow,
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
        "ci_workflow": ci_workflow,
        "_source": {"branch": branch, "live": True},
    }


def ci_workflow_present(body):
    """True when the Actions API reports a version-controlled workflow."""
    if not isinstance(body, dict):
        return False
    total = body.get("total_count")
    if type(total) is int and total > 0:
        return True
    workflows = body.get("workflows")
    return isinstance(workflows, list) and len(workflows) > 0


def fetch_ci_workflow(repo):
    proc = subprocess.run(
        ["gh", "api", f"repos/{repo}/actions/workflows"],
        capture_output=True, text=True,
    )
    if proc.returncode != 0:
        detail = (proc.stderr or "").strip() or "gh actions workflows failed"
        raise SensorError(detail)
    try:
        parsed = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        detail = (proc.stderr or "").strip() or "gh actions workflows failed"
        raise SensorError(detail) from exc
    return ci_workflow_present(parsed)


def collect(repo, environment="prod"):
    info = _gh(f"repos/{repo}") or {}
    branch = info.get("default_branch", "main")
    prot = _gh(f"repos/{repo}/branches/{branch}/protection")
    return normalize(prot, repo, branch, environment, fetch_ci_workflow(repo))


def filter_repos(repos, visibility="public"):
    want = (visibility or "public").lower()
    out = []
    for r in repos:
        if r.get("isFork") or r.get("isArchived"):
            continue
        vis = (r.get("visibility") or "").lower()
        if want == "all" or vis == want:
            out.append(r["nameWithOwner"])
    return out


def list_repos(owner, visibility="public"):
    proc = subprocess.run(
        ["gh", "repo", "list", owner, "--limit", "200",
         "--json", "nameWithOwner,isFork,isArchived,visibility"],
        capture_output=True, text=True,
    )
    if proc.returncode != 0:
        detail = (proc.stderr or "").strip() or "gh repo list failed"
        raise SensorError(detail)
    try:
        repos = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise SensorError(f"gh repo list returned invalid JSON: {exc}") from exc
    return filter_repos(repos, visibility)


def collect_org(owner, visibility="public", environment="prod"):
    payload = {"repositories": []}
    for repo in list_repos(owner, visibility):
        payload["repositories"].append(collect(repo, environment))
    return payload


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
    ap.add_argument("--owner", default=None, help="org-wide: collect all repos of this owner")
    ap.add_argument("--visibility", default="public", choices=["public", "private", "all"],
                    help="repo visibility filter for --owner (default: public)")
    ap.add_argument("--out", default="sensors/out/github.json")
    args = ap.parse_args()
    if args.owner:
        try:
            repos = list_repos(args.owner, args.visibility)
        except SensorError as e:
            raise SystemExit(f"github sensor failed: {e}")
        if not repos:
            raise SystemExit(f"no {args.visibility} repos found for {args.owner}")
        payload = collect_org(args.owner, args.visibility)
        out_path = args.out if os.path.isabs(args.out) else os.path.join(os.getcwd(), args.out)
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        with open(out_path, "w") as fh:
            json.dump(payload, fh, indent=2)
        print(f"# collected {len(repos)} {args.visibility} repos for {args.owner}")
        print(json.dumps(payload, indent=2))
        return
    repos = args.repo or [origin_repo()]
    if not repos or not repos[0]:
        raise SystemExit("no repo given and origin remote not found")
    path = write_payload(repos, args.out)
    with open(path) as fh:
        print(fh.read())


if __name__ == "__main__":
    main()
