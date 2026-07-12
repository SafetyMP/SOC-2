package access_control.iam_mfa_enforced

import rego.v1

# Verifies CTRL-ACCESS-001: human OR privileged identities must have MFA.

test_pass_when_everyone_has_mfa if {
	count(deny) == 0 with input as {
		"principals": [
			{"arn": "human-1", "type": "human", "privileged": false, "mfa_active": true},
			{"arn": "role-1", "type": "machine", "privileged": true, "mfa_active": true},
		],
	}
}

test_fail_when_human_lacks_mfa if {
	some msg in deny with input as {
		"principals": [
			{"arn": "human-2", "type": "human", "privileged": false, "mfa_active": false},
		],
	}
	contains(msg, "human-2")
}

test_fail_when_privileged_machine_lacks_mfa if {
	some msg in deny with input as {
		"principals": [
			{"arn": "role-2", "type": "machine", "privileged": true, "mfa_active": false},
		],
	}
	contains(msg, "role-2")
}

# A non-privileged machine identity is not required to have MFA.
test_pass_machine_unprivileged_no_mfa if {
	count(deny) == 0 with input as {
		"principals": [
			{"arn": "role-3", "type": "machine", "privileged": false, "mfa_active": false},
		],
	}
}
