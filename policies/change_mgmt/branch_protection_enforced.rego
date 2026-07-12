package change_mgmt.branch_protection_enforced

import rego.v1

__rego_metadata__ := {
	"controls": ["CTRL-CHG-001", "CTRL-CHG-002"],
	"severity": "high",
	"frameworks": {
		"soc2": ["CC8.1", "CC5.2"],
		"iso27001": ["A.8.32"],
	},
}

# Input (normalized) from the GitHub sensor:
#   { "repositories": [ {
#       "name":                 string,
#       "environment":          "prod"|"nonprod",   # default prod if omitted
#       "protected":            boolean,
#       "allow_force_pushes":   boolean,
#       "required_reviewers":   number,
#       "enforce_admins":       boolean,
#       "required_status_checks": boolean
#   } ] }

# CTRL-CHG-001: production branches are protected; no direct/force push.
deny contains msg if {
	some r in input.repositories
	not r.protected
	msg := sprintf("CTRL-CHG-001: repo %q default branch is not protected", [r.name])
}

deny contains msg if {
	some r in input.repositories
	r.allow_force_pushes == true
	msg := sprintf("CTRL-CHG-001: repo %q allows force-pushes", [r.name])
}

# CTRL-CHG-002: production changes require >= 2 reviewer approvals.
deny contains msg if {
	some r in input.repositories
	is_prod(r)
	r.required_reviewers < 2
	msg := sprintf("CTRL-CHG-002: production repo %q requires >= 2 reviewers (has %v)", [r.name, r.required_reviewers])
}

# Non-prod still requires at least one review (no unreviewed merges).
deny contains msg if {
	some r in input.repositories
	not is_prod(r)
	r.required_reviewers < 1
	msg := sprintf("CTRL-CHG-001: repo %q requires >= 1 reviewer (has %v)", [r.name, r.required_reviewers])
}

is_prod(r) if {
	object.get(r, "environment", "prod") == "prod"
}
