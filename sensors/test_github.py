import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sensors.github import normalize, filter_repos

REPO = "SafetyMP/SOC-2"
BRANCH = "main"


def test_unprotected_branch():
    e = normalize(None, REPO, BRANCH)
    assert e["protected"] is False
    assert e["required_reviewers"] == 0
    assert e["allow_force_pushes"] is False
    assert e["enforce_admins"] is False
    assert e["_source"]["live"] is True


def test_fully_protected_branch():
    prot = {
        "allow_force_pushes": {"enabled": False},
        "required_pull_request_reviews": {"required_approving_review_count": 2},
        "enforce_admins": {"enabled": True},
        "required_status_checks": {"strict": True, "contexts": ["ci/build"]},
    }
    e = normalize(prot, REPO, BRANCH)
    assert e["protected"] is True
    assert e["required_reviewers"] == 2
    assert e["enforce_admins"] is True
    assert e["required_status_checks"] is True
    assert e["allow_force_pushes"] is False


def test_force_pushes_flagged():
    prot = {"allow_force_pushes": {"enabled": True},
            "required_pull_request_reviews": {"required_approving_review_count": 1}}
    e = normalize(prot, REPO, BRANCH)
    assert e["protected"] is True
    assert e["allow_force_pushes"] is True
    assert e["required_reviewers"] == 1
    assert e["required_status_checks"] is False


def test_missing_review_count_defaults_zero():
    prot = {"enforce_admins": {"enabled": True}}
    e = normalize(prot, REPO, BRANCH, environment="nonprod")
    assert e["required_reviewers"] == 0
    assert e["environment"] == "nonprod"


def test_filter_repos_public_only_excludes_forks_archived_private():
    repos = [
        {"nameWithOwner": "A/pub", "isFork": False, "isArchived": False, "visibility": "PUBLIC"},
        {"nameWithOwner": "B/fork", "isFork": True, "isArchived": False, "visibility": "PUBLIC"},
        {"nameWithOwner": "C/old", "isFork": False, "isArchived": True, "visibility": "PUBLIC"},
        {"nameWithOwner": "D/priv", "isFork": False, "isArchived": False, "visibility": "PRIVATE"},
    ]
    assert filter_repos(repos, "public") == ["A/pub"]


def test_filter_repos_private_only():
    repos = [
        {"nameWithOwner": "A/pub", "isFork": False, "isArchived": False, "visibility": "PUBLIC"},
        {"nameWithOwner": "D/priv", "isFork": False, "isArchived": False, "visibility": "PRIVATE"},
    ]
    assert filter_repos(repos, "private") == ["D/priv"]


def test_filter_repos_all_still_excludes_forks_archived():
    repos = [
        {"nameWithOwner": "A/pub", "isFork": False, "isArchived": False, "visibility": "PUBLIC"},
        {"nameWithOwner": "B/fork", "isFork": True, "isArchived": False, "visibility": "PUBLIC"},
        {"nameWithOwner": "D/priv", "isFork": False, "isArchived": False, "visibility": "PRIVATE"},
    ]
    assert filter_repos(repos, "all") == ["A/pub", "D/priv"]


def main():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"PASS {t.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"FAIL {t.__name__}: {e}")
    print(f"\n{'PASS' if not failed else 'FAIL'}: {len(tests) - failed}/{len(tests)} github sensor tests")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
