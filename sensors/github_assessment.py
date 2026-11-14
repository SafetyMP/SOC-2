"""Read-only, allowlisted GitHub observations for local repository assessments.

Credentials stay in the local gh authentication store/environment. API bodies and
stderr are never evidence. Unknown or ambiguous protection is missing evidence.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
from datetime import datetime, timezone
from typing import Any
from urllib.parse import quote

TIMEOUT_SECONDS = 20
MAX_PAGES = 10
MAX_RESPONSE_BYTES = 4 * 1024 * 1024
_OWNER = r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?"
_REPOSITORY = re.compile(rf"{_OWNER}/[A-Za-z0-9_.-]{{1,100}}\Z")


class CollectionError(ValueError):
    """An intentionally safe message, never an upstream exception or response."""


def validate_repository(repository: str) -> str:
    """Accept only a github.com owner/repository slug, never a URL or option."""
    if (not isinstance(repository, str) or not _REPOSITORY.fullmatch(repository)
            or repository.split("/")[-1] in {".", ".."}):
        raise CollectionError("Use a GitHub repository in owner/repository form.")
    return repository


def _require(condition: bool) -> None:
    if not condition:
        raise CollectionError("GitHub returned incomplete or unsupported data.")


class _Client:
    def __init__(self) -> None:
        self.observations: list[dict[str, Any]] = []

    def get(self, endpoint: str) -> tuple[int | None, Any, str | None]:
        # GH_DEBUG can cause sensitive HTTP diagnostics; never propagate them.
        env = {key: value for key, value in os.environ.items() if key != "GH_DEBUG"}
        env.update({"GH_HOST": "github.com", "GH_PROMPT_DISABLED": "1"})
        observation: dict[str, Any] = {"endpoint": endpoint, "status": None}
        self.observations.append(observation)
        try:
            proc = subprocess.run(
                ["gh", "api", "--hostname", "github.com", "--method", "GET",
                 "--include", "-H", "Accept: application/vnd.github+json",
                 "-H", "X-GitHub-Api-Version: 2026-03-10", endpoint],
                capture_output=True, text=True, timeout=TIMEOUT_SECONDS, env=env,
            )
        except subprocess.TimeoutExpired:
            error = "GitHub request timed out."
        except (OSError, UnicodeError):
            error = "GitHub CLI is unavailable or its response could not be read."
        else:
            output = proc.stdout or ""
            match = re.match(r"HTTP/\S+ (\d{3})[^\r\n]*\r?\n", output)
            status = int(match[1]) if match else None
            observation["status"] = status
            if status != 200 or proc.returncode != 0:
                error = (f"GitHub request failed (HTTP {status})." if status
                         else "GitHub request failed. Check local gh authentication.")
            elif len(output.encode("utf-8")) > MAX_RESPONSE_BYTES:
                error = "GitHub response exceeded the local collection limit."
            else:
                parts = re.split(r"\r?\n\r?\n", output, maxsplit=1)
                try:
                    body = json.loads(parts[1])
                except (IndexError, ValueError, RecursionError):
                    error = "GitHub returned malformed JSON."
                else:
                    observation["outcome"] = "read"
                    return status, body, None
        observation["outcome"] = "unavailable"
        return observation["status"], None, error

    def read(self, endpoint: str) -> Any:
        _, body, error = self.get(endpoint)
        if error:
            raise CollectionError(error)
        return body

    def rules(self, endpoint: str) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        for page in range(1, MAX_PAGES + 1):
            body = self.read(f"{endpoint}?per_page=100&page={page}")
            _require(isinstance(body, list) and len(body) <= 100
                     and all(isinstance(item, dict) for item in body))
            result.extend(body)
            if len(body) < 100:
                return result
        raise CollectionError("GitHub rules exceeded the local pagination limit.")


def _review_count(value: Any) -> int:
    _require(type(value) is int and 0 <= value <= 6)
    return value


def _classic(body: Any) -> dict[str, Any]:
    _require(isinstance(body, dict))
    force = body.get("allow_force_pushes")
    admins = body.get("enforce_admins")
    _require(isinstance(force, dict) and type(force.get("enabled")) is bool)
    _require(isinstance(admins, dict) and type(admins.get("enabled")) is bool)
    # GitHub omits disabled optional protections from an otherwise successful
    # protection response. Its branch-protection OpenAPI schema marks these
    # properties optional; absence is not an unreadable endpoint.
    reviews = body.get("required_pull_request_reviews")
    reviewers = 0
    if reviews is not None:
        _require(isinstance(reviews, dict))
        reviewers = _review_count(reviews.get("required_approving_review_count"))
        bypass = reviews.get("bypass_pull_request_allowances", {})
        _require(isinstance(bypass, dict))
        for kind in ("users", "teams", "apps"):
            _require(isinstance(bypass.get(kind, []), list))
            if bypass.get(kind):
                raise CollectionError("Pull request bypass allowances need manual review.")
    checks = body.get("required_status_checks")
    has_checks = False
    if checks is not None:
        _require(isinstance(checks, dict))
        _require("contexts" in checks or "checks" in checks)
        contexts, entries = checks.get("contexts", []), checks.get("checks", [])
        _require(isinstance(contexts, list) and all(isinstance(x, str) and x for x in contexts))
        _require(isinstance(entries, list) and all(
            isinstance(x, dict) and isinstance(x.get("context"), str) and x["context"]
            for x in entries))
        has_checks = bool(contexts or entries)
    return {"protected": True, "allow_force_pushes": force["enabled"],
            "required_reviewers": reviewers, "enforce_admins": admins["enabled"],
            "required_status_checks": has_checks}


def _protection(client: _Client, repo: str, branch: str, protected: bool) -> dict[str, Any]:
    encoded = quote(branch, safe="")
    status, classic, error = client.get(f"repos/{repo}/branches/{encoded}/protection")
    if error and status != 404:
        raise CollectionError(error)
    rules = client.rules(f"repos/{repo}/rules/branches/{encoded}")
    if status == 404 and protected and not rules:
        raise CollectionError("Protection is reported but its configuration is unavailable.")
    if not protected and (status == 200 or rules):
        raise CollectionError("GitHub protection observations disagree; collect again.")
    result = (_classic(classic) if status == 200 else {
        "protected": bool(rules), "allow_force_pushes": True, "required_reviewers": 0,
        "enforce_admins": False, "required_status_checks": False,
    })
    verified: set[int] = set()
    for rule in rules:
        rule_id = rule.get("ruleset_id")
        _require(type(rule_id) is int and rule_id > 0)
        if rule_id not in verified:
            detail = client.read(f"repos/{repo}/rulesets/{rule_id}?includes_parents=true")
            _require(isinstance(detail, dict) and detail.get("id") == rule_id
                     and detail.get("target") == "branch" and detail.get("enforcement") == "active")
            # GitHub omits bypass_actors when the caller cannot inspect them.
            if detail.get("bypass_actors") != []:
                raise CollectionError("Ruleset bypass settings are unavailable or need manual review.")
            verified.add(rule_id)
        kind, parameters = rule.get("type"), rule.get("parameters", {})
        _require(isinstance(kind, str) and isinstance(parameters, dict))
        if kind == "non_fast_forward":
            result["allow_force_pushes"] = False
        elif kind == "pull_request":
            result["required_reviewers"] = max(result["required_reviewers"],
                _review_count(parameters.get("required_approving_review_count")))
        elif kind == "required_status_checks":
            checks = parameters.get("required_status_checks")
            _require(isinstance(checks, list) and all(
                isinstance(x, dict) and isinstance(x.get("context"), str) and x["context"]
                for x in checks))
            result["required_status_checks"] |= bool(checks)
        elif kind not in {"creation", "update", "deletion", "required_linear_history",
                          "required_deployments", "required_signatures", "merge_queue",
                          "commit_message_pattern", "commit_author_email_pattern",
                          "committer_email_pattern", "branch_name_pattern", "workflows",
                          "code_scanning", "max_file_path_length", "file_path_restriction",
                          "file_extension_restriction", "max_file_size"}:
            raise CollectionError("An unsupported GitHub branch rule needs manual review.")
    return result


def _ci(client: _Client, repo: str) -> bool:
    seen = 0
    total: int | None = None
    active = False
    for page in range(1, MAX_PAGES + 1):
        body = client.read(f"repos/{repo}/actions/workflows?per_page=100&page={page}")
        _require(isinstance(body, dict))
        count, workflows = body.get("total_count"), body.get("workflows")
        _require(type(count) is int and count >= 0 and isinstance(workflows, list)
                 and len(workflows) <= 100)
        if total is None:
            total = count
        _require(total == count)
        for workflow in workflows:
            _require(isinstance(workflow, dict))
            path, state = workflow.get("path"), workflow.get("state")
            _require(isinstance(path, str) and isinstance(state, str) and state in {
                "active", "deleted", "disabled_fork", "disabled_inactivity", "disabled_manually"})
            # Dynamic workflows and disabled historical workflows are not CI evidence.
            if (state == "active" and re.fullmatch(r"\.github/workflows/[^/]+\.(?:yml|yaml)", path)
                    and not any(ord(character) < 32 for character in path)):
                active = True
        seen += len(workflows)
        _require(seen <= total)
        if seen == total:
            return active
        _require(bool(workflows))
    raise CollectionError("GitHub workflows exceeded the local pagination limit.")


def collect_repository(repository: str) -> dict[str, Any]:
    """Collect safe facts for exactly one repository, without changing GitHub."""
    repo = validate_repository(repository)
    client = _Client()
    result: dict[str, Any] = {
        "target": {"host": "github.com", "repository": repo, "branch": None,
                   "commit": None, "visibility": None},
        "collected_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "payloads": {"branch_protection": None, "ci": None},
        "errors": {"branch_protection": None, "ci": None},
        "observations": client.observations,
        "limitations": [
            "Only the repository default branch and active GitHub Actions workflow settings are observed.",
            "Production is the policy context; this does not verify the repository deploys to production.",
            "An active version-controlled workflow does not prove successful builds, tests, or deployments.",
            "Protection checks do not establish universal enforcement, administrator behavior, or SOC 2 compliance.",
            "Collection is a point-in-time series of API reads, not an atomic GitHub snapshot.",
        ],
    }
    try:
        info = client.read(f"repos/{repo}")
        _require(isinstance(info, dict) and isinstance(info.get("full_name"), str)
                 and info["full_name"].lower() == repo.lower())
        visibility = info.get("visibility")
        _require(isinstance(visibility, str) and visibility in {"public", "private", "internal"})
        result["target"]["visibility"] = visibility
        branch = info.get("default_branch")
        _require(isinstance(branch, str) and 0 < len(branch) <= 255
                 and not any(ord(character) < 32 or ord(character) == 127 for character in branch))
        result["target"]["branch"] = branch
    except CollectionError as exc:
        result["errors"] = {"branch_protection": str(exc), "ci": str(exc)}
        return result
    try:
        branch_info = client.read(f"repos/{repo}/branches/{quote(branch, safe='')}")
        _require(isinstance(branch_info, dict) and branch_info.get("name") == branch
                 and type(branch_info.get("protected")) is bool)
        commit = branch_info.get("commit")
        _require(isinstance(commit, dict) and isinstance(commit.get("sha"), str)
                 and bool(re.fullmatch(r"[a-fA-F0-9]{40}", commit["sha"])))
        result["target"]["commit"] = commit["sha"]
        normalized = _protection(client, repo, branch, branch_info["protected"])
        normalized.update({"name": repo, "environment": "prod",
                           "_source": {"branch": branch, "live": True}})
        result["payloads"]["branch_protection"] = {"repositories": [normalized]}
    except CollectionError as exc:
        result["errors"]["branch_protection"] = str(exc)
    try:
        present = _ci(client, repo)
        result["payloads"]["ci"] = {"repositories": [{
            "name": repo, "environment": "prod", "ci_workflow": present,
            "_source": {"branch": branch, "live": True},
        }]}
    except CollectionError as exc:
        result["errors"]["ci"] = str(exc)
    return result
