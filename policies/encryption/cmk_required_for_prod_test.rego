package encryption.cmk_required_for_prod

import rego.v1

test_pass_when_prod_uses_a_customer_managed_key if {
	count(deny) == 0 with input as {"data_resources": [{
		"id": "prod-db",
		"type": "rds",
		"environment": "prod",
		"encrypted": true,
		"customer_managed_key": true,
	}]}
}

test_fail_when_prod_uses_a_provider_key if {
	some msg in deny with input as {"data_resources": [{
		"id": "prod-db",
		"type": "rds",
		"environment": "prod",
		"encrypted": true,
		"customer_managed_key": false,
	}]}
	contains(msg, "CTRL-ENC-003")
	contains(msg, "prod-db")
}

test_fail_when_prod_omits_the_key_flag if {
	some msg in deny with input as {"data_resources": [{
		"id": "prod-data-bucket",
		"type": "s3_bucket",
		"environment": "prod",
		"encrypted": true,
	}]}
	contains(msg, "no customer-managed key")
}

test_pass_when_nonprod_uses_a_provider_key if {
	count(deny) == 0 with input as {"data_resources": [{
		"id": "dev-db",
		"type": "rds",
		"environment": "nonprod",
		"encrypted": true,
		"customer_managed_key": false,
	}]}
}
