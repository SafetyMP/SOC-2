package encryption.at_rest_required

import rego.v1

__rego_metadata__ := {
	"controls": ["CTRL-ENC-001"],
	"severity": "critical",
	"frameworks": {
		"soc2": ["CC6.1", "C1.1"],
		"iso27001": ["A.8.24"],
	},
}

# Input (normalized, provider-agnostic):
#   { "data_resources": [ {
#       "id":          string,
#       "type":        "s3_bucket"|"azure_storage"|"gcs_bucket"|"rds"|"ebs_volume",
#       "encrypted":   boolean,
#       "environment": "prod"|"nonprod"
#   } ] }

deny contains msg if {
	some r in input.data_resources
	not r.encrypted
	msg := sprintf("CTRL-ENC-001: %s %q is not encrypted at rest", [r.type, r.id])
}
