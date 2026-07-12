package access_control.no_wildcard_policies

import rego.v1

__rego_metadata__ := {
	"controls": ["CTRL-ACCESS-003"],
	"severity": "high",
	"frameworks": {
		"soc2": ["CC6.3"],
		"iso27001": ["A.8.2", "A.8.3"],
	},
}

# Input (normalized, provider-agnostic):
#   { "policies": [ { "name": string, "actions": [string], "resources": [string] } ] }

deny contains msg if {
	some pol in input.policies
	contains_wildcard(pol.actions)
	msg := sprintf("CTRL-ACCESS-003: policy %q grants wildcard actions (Action: *)", [pol.name])
}

deny contains msg if {
	some pol in input.policies
	contains_wildcard(pol.resources)
	msg := sprintf("CTRL-ACCESS-003: policy %q grants wildcard resources (Resource: *)", [pol.name])
}

# A statement grants "*" if any entry is exactly the wildcard token.
contains_wildcard(arr) if {
	some entry in arr
	entry == "*"
}
