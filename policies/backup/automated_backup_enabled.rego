package backup.automated_backup_enabled

import rego.v1

__rego_metadata__ := {
	"controls": ["CTRL-BKP-001"],
	"severity": "high",
	"frameworks": {
		"soc2": ["A1.2"],
		"iso27001": ["A.8.13"],
	},
}

# Input (normalized, provider-agnostic):
#   { "datastores": [ {
#       "id":              string,
#       "kind":            "rds"|"aurora"|"vm"|"bucket"|"volume",
#       "environment":     "prod"|"nonprod",
#       "backup_enabled":  boolean,
#       "pitr":            boolean    # point-in-time-recovery available
#   } ] }

deny contains msg if {
	some d in input.datastores
	is_prod(d)
	not d.backup_enabled
	msg := sprintf("CTRL-BKP-001: production datastore %q (%s) has no automated backup", [d.id, d.kind])
}

is_prod(d) if {
	object.get(d, "environment", "prod") == "prod"
}
