package logging.audit_log_enabled

import rego.v1

__rego_metadata__ := {
	"controls": ["CTRL-LOG-001"],
	"severity": "critical",
	"frameworks": {
		"soc2": ["CC7.2", "CC7.3"],
		"iso27001": ["A.8.15"],
	},
}

# Input (normalized, provider-agnostic), one entry per cloud provider in scope:
#   { "audit_logs": [ {
#       "cloud":             "aws"|"azure"|"gcp",
#       "enabled":           boolean,
#       "all_regions":       boolean,   # global/all-region, not single-region
#       "management_events": boolean    # captures control-plane (mgmt) events
#   } ] }

deny contains msg if {
	some lg in input.audit_logs
	not lg.enabled
	msg := sprintf("CTRL-LOG-001: %s management-plane audit logging is not enabled", [lg.cloud])
}

deny contains msg if {
	some lg in input.audit_logs
	lg.enabled
	not lg.all_regions
	msg := sprintf("CTRL-LOG-001: %s audit logging is not enabled in all regions", [lg.cloud])
}

deny contains msg if {
	some lg in input.audit_logs
	lg.enabled
	not lg.management_events
	msg := sprintf("CTRL-LOG-001: %s audit logging does not capture management events", [lg.cloud])
}
