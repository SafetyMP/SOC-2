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
	contains_wildcard_action(pol.actions)
	msg := sprintf("CTRL-ACCESS-003: policy %q grants wildcard actions (Action: *)", [pol.name])
}

deny contains msg if {
	some pol in input.policies
	contains_wildcard(pol.resources)
	msg := sprintf("CTRL-ACCESS-003: policy %q grants wildcard resources (Resource: *)", [pol.name])
}

# AWS IAM treats "*" anywhere in an action as a wildcard: "*", "s3:*", "s3:Get*".
# Resource ARNs such as arn:aws:s3:::data/* stay allowed. Only a resource of exactly "*" is denied.
contains_wildcard_action(arr) if {
	some entry in arr
	wildcard_action(entry)
}

wildcard_action(entry) if {
	is_string(entry)
	contains(entry, "*")
}

contains_wildcard(arr) if {
	some entry in arr
	entry == "*"
}
