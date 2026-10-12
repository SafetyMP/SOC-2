package encryption.cmk_required_for_prod

import rego.v1

__rego_metadata__ := {
	"controls": ["CTRL-ENC-003"],
	"severity": "high",
	"frameworks": {
		"soc2": ["CC6.1", "C1.1"],
		"iso27001": ["A.8.24"],
	},
}

# SOC 2 CC6.1 / ISO 27001 A.8.24: production encryption must use a
# customer-managed key. Provider-default encryption is not that key.
# A missing flag is not evidence of a customer-managed key.

deny contains msg if {
	some r in input.data_resources
	object.get(r, "environment", "prod") == "prod"
	object.get(r, "customer_managed_key", false) != true
	msg := sprintf("CTRL-ENC-003: production %s %q has no customer-managed key", [r.type, r.id])
}
