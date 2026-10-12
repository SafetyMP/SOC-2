package change_mgmt.ci_required

import rego.v1

# SOC 2 CC8.1: production deploys come from a version-controlled CI workflow.

test_pass_when_prod_has_ci_workflow if {
	count(deny) == 0 with input as {"repositories": [{
		"name": "core-service",
		"environment": "prod",
		"ci_workflow": true,
	}]}
}

test_fail_when_prod_ci_workflow_is_false if {
	some msg in deny with input as {"repositories": [{
		"name": "core-service",
		"environment": "prod",
		"ci_workflow": false,
	}]}
	contains(msg, "CTRL-CHG-008")
	contains(msg, "core-service")
}

test_fail_when_prod_omits_ci_workflow if {
	some msg in deny with input as {"repositories": [{
		"name": "core-service",
		"environment": "prod",
	}]}
	contains(msg, "CTRL-CHG-008")
	contains(msg, "core-service")
}

test_pass_when_nonprod_ci_workflow_is_false if {
	count(deny) == 0 with input as {"repositories": [{
		"name": "sandbox",
		"environment": "nonprod",
		"ci_workflow": false,
	}]}
}
