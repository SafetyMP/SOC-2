package access_control.iam_mfa_enforced

import rego.v1

# Metadata consumed by the catalog crosswalk (L0) and the auditor packaging (L5).
__rego_metadata__ := {
	"controls": ["CTRL-ACCESS-001"],
	"severity": "critical",
	"frameworks": {
		"soc2": ["CC6.1", "CC6.6"],
		"iso27001": ["A.8.2", "A.8.5", "A.5.17"],
	},
}

# Input (normalized, provider-agnostic) produced by the cloud + github sensors:
#   { "principals": [ {
#       "arn":         string,            # stable identity handle
#       "type":        "human"|"machine",
#       "privileged":  boolean,
#       "mfa_active":  boolean            # true if a strong MFA factor is enrolled
#   } ] }

# MFA is required for every human identity AND every privileged identity.
deny contains msg if {
	some p in input.principals
	is_mfa_required(p)
	not p.mfa_active
	msg := sprintf("CTRL-ACCESS-001: %s identity %q lacks MFA", [p.type, p.arn])
}

is_mfa_required(p) if {
	p.type == "human"
}

is_mfa_required(p) if {
	p.privileged == true
}
