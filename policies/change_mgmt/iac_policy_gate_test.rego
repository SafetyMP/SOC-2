package change_mgmt.iac_policy_gate

import rego.v1

# SOC 2 CC8.1: a production infrastructure change is denied unless approved before apply.

test_pass_when_prod_mutation_is_approved if {
	count(deny) == 0 with input as {"plans": [{
		"id": "terraform",
		"environment": "prod",
		"mutating": true,
		"approved": true,
	}]}
}

test_fail_when_prod_mutation_is_unapproved if {
	some msg in deny with input as {"plans": [{
		"id": "vpc-main",
		"environment": "prod",
		"mutating": true,
		"approved": false,
	}]}
	contains(msg, "CTRL-CHG-005")
	contains(msg, "vpc-main")
}

test_fail_when_prod_mutation_omits_approved if {
	some msg in deny with input as {"plans": [{
		"id": "db-main",
		"environment": "prod",
		"mutating": true,
	}]}
	contains(msg, "CTRL-CHG-005")
	contains(msg, "db-main")
}

test_pass_when_nonprod_mutation_is_unapproved if {
	count(deny) == 0 with input as {"plans": [{
		"id": "sandbox",
		"environment": "nonprod",
		"mutating": true,
		"approved": false,
	}]}
}

test_pass_when_prod_plan_is_not_mutating if {
	count(deny) == 0 with input as {"plans": [{
		"id": "read-only",
		"environment": "prod",
		"mutating": false,
		"approved": false,
	}]}
}
