package change_mgmt.branch_protection_enforced

import rego.v1

# SOC 2 CC8.1: production changes are reviewed and pass required status checks.

test_pass_when_prod_has_two_reviewers_and_status_checks if {
	count(deny) == 0 with input as {"repositories": [{
		"name": "core-service",
		"environment": "prod",
		"protected": true,
		"allow_force_pushes": false,
		"required_reviewers": 2,
		"required_status_checks": true,
	}]}
}

test_fail_when_prod_has_no_required_status_checks if {
	some msg in deny with input as {"repositories": [{
		"name": "core-service",
		"environment": "prod",
		"protected": true,
		"allow_force_pushes": false,
		"required_reviewers": 2,
		"required_status_checks": false,
	}]}
	contains(msg, "CTRL-CHG-002")
	contains(msg, "core-service")
}

test_fail_when_prod_omits_status_checks if {
	some msg in deny with input as {"repositories": [{
		"name": "core-service",
		"environment": "prod",
		"protected": true,
		"allow_force_pushes": false,
		"required_reviewers": 2,
	}]}
	contains(msg, "no required status checks")
}
