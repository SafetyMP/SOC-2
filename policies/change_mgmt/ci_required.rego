package change_mgmt.ci_required

import rego.v1

__rego_metadata__ := {
	"controls": ["CTRL-CHG-008"],
	"severity": "high",
	"frameworks": {
		"soc2": ["CC8.1"],
		"iso27001": ["A.8.32", "A.8.19"],
	},
}

# Input (normalized) from the GitHub sensor:
#   { "repositories": [ {
#       "name":        string,
#       "environment": "prod"|"nonprod",   # default prod if omitted
#       "ci_workflow": boolean
#   } ] }

# CTRL-CHG-008 / SOC 2 CC8.1: a production repo is denied unless it has a
# version-controlled CI workflow. A missing ci_workflow flag is not evidence.
# A deploy pipeline that lives outside the repo does not satisfy this control.
deny contains msg if {
	some r in input.repositories
	is_prod(r)
	not r.ci_workflow
	msg := sprintf("CTRL-CHG-008: production repo %q has no version-controlled CI workflow", [r.name])
}

is_prod(r) if {
	object.get(r, "environment", "prod") == "prod"
}
