package encryption.at_rest_required

import rego.v1

# Verifies CTRL-ENC-001: data stores must be encrypted at rest.

test_pass_when_all_encrypted if {
	count(deny) == 0 with input as {
		"data_resources": [
			{"id": "b1", "type": "s3_bucket", "encrypted": true},
			{"id": "v1", "type": "ebs_volume", "encrypted": true},
		],
	}
}

test_fail_when_bucket_unencrypted if {
	some msg in deny with input as {
		"data_resources": [
			{"id": "b2", "type": "s3_bucket", "encrypted": false},
		],
	}
	contains(msg, "b2")
}

test_fail_reports_each_unencrypted_resource if {
	count(deny) == 2 with input as {
		"data_resources": [
			{"id": "x1", "type": "rds", "encrypted": false},
			{"id": "x2", "type": "gcs_bucket", "encrypted": false},
			{"id": "x3", "type": "s3_bucket", "encrypted": true},
		],
	}
}
