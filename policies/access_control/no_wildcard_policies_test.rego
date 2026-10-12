package access_control.no_wildcard_policies

import rego.v1

# Verifies CTRL-ACCESS-003: an action containing "*" is denied. A resource ARN with "/*" is not.

test_fail_when_action_is_bare_star if {
	some msg in deny with input as {
		"policies": [{
			"name": "Admin",
			"actions": ["*"],
			"resources": ["arn:aws:s3:::data"],
		}],
	}
	contains(msg, "Admin")
}

test_fail_when_action_is_s3_wildcard if {
	some msg in deny with input as {
		"policies": [{
			"name": "S3Admin",
			"actions": ["s3:*"],
			"resources": ["arn:aws:s3:::data"],
		}],
	}
	contains(msg, "S3Admin")
}

test_fail_when_action_is_prefix_wildcard if {
	some msg in deny with input as {
		"policies": [{
			"name": "GetStar",
			"actions": ["s3:Get*"],
			"resources": ["arn:aws:s3:::data"],
		}],
	}
	contains(msg, "GetStar")
}

test_fail_when_action_is_iam_wildcard if {
	some msg in deny with input as {
		"policies": [{
			"name": "IAMAdmin",
			"actions": ["iam:*"],
			"resources": ["arn:aws:iam::111:role/Deploy"],
		}],
	}
	contains(msg, "IAMAdmin")
}

test_fail_when_one_action_in_the_list_is_star if {
	count(deny) > 0 with input as {
		"policies": [{
			"name": "Mixed",
			"actions": ["s3:GetObject", "*"],
			"resources": ["arn:aws:s3:::data"],
		}],
	}
}

test_fail_when_resource_is_bare_star if {
	some msg in deny with input as {
		"policies": [{
			"name": "AllResources",
			"actions": ["s3:GetObject"],
			"resources": ["*"],
		}],
	}
	contains(msg, "AllResources")
}

test_pass_when_actions_and_resources_are_specific if {
	count(deny) == 0 with input as {
		"policies": [{
			"name": "ReadDataBuckets",
			"actions": ["s3:GetObject", "s3:ListBucket"],
			"resources": ["arn:aws:s3:::data/*"],
		}],
	}
}
