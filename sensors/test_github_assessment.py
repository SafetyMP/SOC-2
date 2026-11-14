"""Hermetic tests: no authentication, credentials, or live repository required."""

import json
import os
import subprocess
import sys
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sensors.github_assessment import CollectionError, collect_repository, validate_repository

REPO = "acme/example"
SECRET = "synthetic-private-response-do-not-export"


def _responses(branch="main", protected=True):
    encoded = branch.replace("/", "%2F").replace("#", "%23")
    return {
        f"repos/{REPO}": {"full_name": REPO, "default_branch": branch, "visibility": "private"},
        f"repos/{REPO}/branches/{encoded}": {
            "name": branch, "protected": protected, "commit": {"sha": "a" * 40}},
        f"repos/{REPO}/branches/{encoded}/protection": {
            "allow_force_pushes": {"enabled": False}, "enforce_admins": {"enabled": True},
            "required_pull_request_reviews": {"required_approving_review_count": 2},
            "required_status_checks": {"contexts": ["build"], "checks": []}},
        f"repos/{REPO}/rules/branches/{encoded}?per_page=100&page=1": [],
        f"repos/{REPO}/actions/workflows?per_page=100&page=1": {
            "total_count": 1, "workflows": [
                {"path": ".github/workflows/test.yml", "state": "active"}]},
    }


def _collect(responses):
    calls = []

    def run(args, **kwargs):
        calls.append(args)
        assert args[:7] == ["gh", "api", "--hostname", "github.com", "--method", "GET", "--include"]
        assert kwargs["timeout"] == 20
        assert kwargs["capture_output"] and kwargs["text"]
        assert "GH_DEBUG" not in kwargs["env"]
        assert SECRET not in " ".join(args)
        value = responses[args[-1]]
        if isinstance(value, Exception):
            raise value
        status, body = value if isinstance(value, tuple) else (200, value)
        return SimpleNamespace(returncode=0 if status == 200 else 1,
            stdout=f"HTTP/2.0 {status} status\r\nAuthorization: {SECRET}\r\n\r\n{json.dumps(body)}",
            stderr=SECRET)

    with patch("sensors.github_assessment.subprocess.run", run), patch.dict(os.environ, {"GH_DEBUG": "api"}):
        result = collect_repository(REPO)
    assert SECRET not in json.dumps(result)
    return result, calls


def _branch(result):
    return result["payloads"]["branch_protection"]["repositories"][0]


def test_valid_classic_and_ci() -> None:
    result, calls = _collect(_responses())
    assert len(calls) == 5
    assert result["target"]["commit"] == "a" * 40
    assert _branch(result)["required_reviewers"] == 2
    assert _branch(result)["required_status_checks"] is True
    assert result["errors"] == {"branch_protection": None, "ci": None}
    assert result["payloads"]["ci"]["repositories"][0]["ci_workflow"] is True


def test_invalid_repository_never_calls_gh() -> None:
    with patch("sensors.github_assessment.subprocess.run") as run:
        for repo in ["https://github.com/a/b", "--hostname", "a/b/c", "a/..", "a/b?x=y",
                     "a/b\n", "a/b#fragment", "/a", "a/", "a b/c", None]:
            try:
                validate_repository(repo)
            except CollectionError:
                pass
            else:
                raise AssertionError("invalid repository accepted")
        run.assert_not_called()


def test_authentication_and_api_failures_are_missing_and_safe() -> None:
    for status in (401, 403, 404, 429, 500):
        responses = _responses()
        responses[f"repos/{REPO}"] = (status, {"message": SECRET})
        result, calls = _collect(responses)
        assert len(calls) == 1
        assert result["payloads"] == {"branch_protection": None, "ci": None}
        assert result["target"]["branch"] is None
        assert str(status) in result["errors"]["ci"]


def test_ambiguous_protection_404_is_missing():
    responses = _responses()
    responses[f"repos/{REPO}/branches/main/protection"] = (404, {"message": SECRET})
    result, _ = _collect(responses)
    assert result["payloads"]["branch_protection"] is None
    assert result["payloads"]["ci"] is not None


def test_confirmed_absent_protection_is_negative_evidence() -> None:
    responses = _responses(protected=False)
    responses[f"repos/{REPO}/branches/main/protection"] = (404, {})
    result, _ = _collect(responses)
    assert _branch(result)["protected"] is False
    assert _branch(result)["required_reviewers"] == 0
    assert _branch(result)["allow_force_pushes"] is True


def test_omitted_optional_classic_settings_are_negative_evidence() -> None:
    for omitted in ("required_status_checks", "required_pull_request_reviews"):
        responses = _responses()
        del responses[f"repos/{REPO}/branches/main/protection"][omitted]
        result, _ = _collect(responses)
        branch = _branch(result)
        assert branch["protected"] is True
        if omitted == "required_status_checks":
            assert branch["required_status_checks"] is False
        else:
            assert branch["required_reviewers"] == 0
        assert result["errors"]["branch_protection"] is None


def test_classic_forbidden_never_defaults_to_unprotected() -> None:
    responses = _responses(protected=False)
    responses[f"repos/{REPO}/branches/main/protection"] = (403, {"message": SECRET})
    result, _ = _collect(responses)
    assert result["payloads"]["branch_protection"] is None
    assert "403" in result["errors"]["branch_protection"]


def _rules_responses():
    responses = _responses()
    responses[f"repos/{REPO}/branches/main/protection"] = (404, {})
    responses[f"repos/{REPO}/rules/branches/main?per_page=100&page=1"] = [
        {"type": "non_fast_forward", "ruleset_id": 42},
        {"type": "pull_request", "ruleset_id": 42,
         "parameters": {"required_approving_review_count": 2}},
        {"type": "required_status_checks", "ruleset_id": 42,
         "parameters": {"required_status_checks": [{"context": "build"}]}},
    ]
    responses[f"repos/{REPO}/rulesets/42?includes_parents=true"] = {
        "id": 42, "target": "branch", "enforcement": "active", "bypass_actors": []}
    return responses


def test_rulesets_normalize_only_when_bypass_settings_are_known() -> None:
    result, _ = _collect(_rules_responses())
    branch = _branch(result)
    assert branch["protected"] is True and branch["allow_force_pushes"] is False
    assert branch["required_reviewers"] == 2 and branch["required_status_checks"] is True
    for bypass in (None, [{"actor_id": 5}], {}):
        responses = _rules_responses()
        detail = responses[f"repos/{REPO}/rulesets/42?includes_parents=true"]
        if bypass is None:
            del detail["bypass_actors"]
        else:
            detail["bypass_actors"] = bypass
        result, _ = _collect(responses)
        assert result["payloads"]["branch_protection"] is None


def test_effective_rules_are_fully_paginated() -> None:
    responses = _rules_responses()
    first = responses[f"repos/{REPO}/rules/branches/main?per_page=100&page=1"]
    responses[f"repos/{REPO}/rules/branches/main?per_page=100&page=1"] = [first[0]] * 100
    responses[f"repos/{REPO}/rules/branches/main?per_page=100&page=2"] = first[1:]
    result, calls = _collect(responses)
    assert _branch(result)["required_reviewers"] == 2
    assert any("page=2" in command[-1] for command in calls)


def test_unsupported_rules_and_classic_bypass_are_missing() -> None:
    responses = _rules_responses()
    responses[f"repos/{REPO}/rules/branches/main?per_page=100&page=1"][0]["type"] = "unknown_new_rule"
    result, _ = _collect(responses)
    assert result["payloads"]["branch_protection"] is None
    responses = _responses()
    reviews = responses[f"repos/{REPO}/branches/main/protection"]["required_pull_request_reviews"]
    reviews["bypass_pull_request_allowances"] = {"users": [{"login": SECRET}]}
    result, _ = _collect(responses)
    assert result["payloads"]["branch_protection"] is None


def test_unreadable_branch_does_not_prevent_independent_ci_observation() -> None:
    responses = _responses()
    responses[f"repos/{REPO}/branches/main"] = (403, {"message": SECRET})
    result, _ = _collect(responses)
    assert result["target"]["commit"] is None
    assert result["payloads"]["branch_protection"] is None
    assert result["payloads"]["ci"] is not None


def test_active_version_controlled_workflows_only() -> None:
    for workflow in [
        {"path": ".github/workflows/test.yml", "state": "disabled_manually"},
        {"path": "dynamic/pages/pages-build-deployment", "state": "active"},
        {"path": ".github/workflows/test.yml", "state": "deleted"},
        {"path": ".github/workflows/../secret.yml", "state": "active"},
    ]:
        responses = _responses()
        responses[f"repos/{REPO}/actions/workflows?per_page=100&page=1"]["workflows"] = [workflow]
        result, _ = _collect(responses)
        assert result["payloads"]["ci"]["repositories"][0]["ci_workflow"] is False


def test_workflows_paginate_and_api_denial_is_missing() -> None:
    responses = _responses()
    disabled = {"path": ".github/workflows/test.yml", "state": "disabled_manually"}
    responses[f"repos/{REPO}/actions/workflows?per_page=100&page=1"] = {
        "total_count": 101, "workflows": [disabled] * 100}
    responses[f"repos/{REPO}/actions/workflows?per_page=100&page=2"] = {
        "total_count": 101, "workflows": [{"path": ".github/workflows/ci.yaml", "state": "active"}]}
    result, _ = _collect(responses)
    assert result["payloads"]["ci"]["repositories"][0]["ci_workflow"] is True
    responses[f"repos/{REPO}/actions/workflows?per_page=100&page=2"] = (403, {"message": SECRET})
    result, _ = _collect(responses)
    assert result["payloads"]["ci"] is None


def test_malformed_payloads_are_missing() -> None:
    mutations = [
        (f"repos/{REPO}", {"full_name": REPO, "visibility": [], "default_branch": "main"}, "ci"),
        (f"repos/{REPO}", {"full_name": REPO, "visibility": "public"}, "ci"),
        (f"repos/{REPO}/branches/main/protection", {}, "branch_protection"),
        (f"repos/{REPO}/branches/main/protection", {"required_status_checks": SECRET}, "branch_protection"),
        (f"repos/{REPO}/rules/branches/main?per_page=100&page=1", {}, "branch_protection"),
        (f"repos/{REPO}/actions/workflows?per_page=100&page=1", {"total_count": 1, "workflows": []}, "ci"),
        (f"repos/{REPO}/actions/workflows?per_page=100&page=1", {"total_count": True, "workflows": []}, "ci"),
        (f"repos/{REPO}/actions/workflows?per_page=100&page=1", {"total_count": 1, "workflows": [{"path": "x", "state": []}]}, "ci"),
    ]
    for endpoint, payload, sensor in mutations:
        responses = _responses()
        responses[endpoint] = payload
        result, _ = _collect(responses)
        assert result["payloads"][sensor] is None
        assert result["errors"][sensor]


def test_timeout_and_cli_errors_do_not_export_sensitive_details() -> None:
    for error in [subprocess.TimeoutExpired("gh " + SECRET, 20, output=SECRET, stderr=SECRET),
                  OSError(SECRET)]:
        responses = _responses()
        responses[f"repos/{REPO}"] = error
        result, _ = _collect(responses)
        assert result["payloads"]["ci"] is None


def test_branch_names_are_url_encoded() -> None:
    result, calls = _collect(_responses("release/v2#test"))
    assert result["target"]["branch"] == "release/v2#test"
    assert any("release%2Fv2%23test" in command[-1] for command in calls)


def test_raw_json_and_error_output_never_escape() -> None:
    for output in ("not-json " + SECRET, "HTTP/2.0 200 OK\n\n" + SECRET):
        proc = SimpleNamespace(returncode=0, stdout=output, stderr=SECRET)
        with patch("sensors.github_assessment.subprocess.run", return_value=proc):
            result = collect_repository(REPO)
        assert SECRET not in json.dumps(result)
        assert result["payloads"]["ci"] is None


def test_raw_extra_metadata_is_discarded() -> None:
    responses = _responses()
    for value in responses.values():
        if isinstance(value, dict):
            value["private_extra"] = {"token": SECRET}
    result, _ = _collect(responses)
    assert result["payloads"]["ci"] is not None


def test_inconsistent_protection_is_missing() -> None:
    responses = _responses(protected=False)
    result, _ = _collect(responses)
    assert result["payloads"]["branch_protection"] is None


def main() -> None:
    tests = [value for name, value in sorted(globals().items()) if name.startswith("test_")]
    for test in tests:
        test()
        print(f"PASS {test.__name__}")
    print(f"PASS: {len(tests)} local GitHub collector tests")


if __name__ == "__main__":
    main()
