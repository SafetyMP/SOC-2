package change_mgmt.iac_policy_gate

import rego.v1

__rego_metadata__ := {
	"controls": ["CTRL-CHG-005"],
	"severity": "high",
	"frameworks": {
		"soc2": ["CC8.1"],
		"iso27001": ["A.8.32"],
	},
}

# Input (normalized) from the Terraform sensor:
#   { "plans": [ {
#       "id":          string,
#       "environment": "prod"|"nonprod",   # default prod if omitted
#       "mutating":    boolean,
#       "approved":    boolean
#   } ] }

# CTRL-CHG-005 / SOC 2 CC8.1: a production infrastructure change is denied
# unless it was approved before apply. A missing approved flag is not approval.
deny contains msg if {
	some plan in input.plans
	is_prod(plan)
	plan.mutating == true
	not plan.approved
	msg := sprintf("CTRL-CHG-005: production plan %q changes infrastructure without approval", [plan.id])
}

is_prod(plan) if {
	object.get(plan, "environment", "prod") == "prod"
}
