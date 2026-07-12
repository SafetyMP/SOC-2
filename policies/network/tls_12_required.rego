package network.tls_12_required

import rego.v1

__rego_metadata__ := {
	"controls": ["CTRL-NET-008"],
	"severity": "medium",
	"frameworks": {
		"soc2": ["CC6.7", "C1.2"],
		"iso27001": ["A.8.24", "A.8.22"],
	},
}

# Input (normalized, provider-agnostic):
#   { "endpoints": [ { "id": string, "tls_min_version": "1.3"|"1.2"|"1.1"|"1.0"|string } ] }

acceptable_tls := {"1.2", "1.3"}

deny contains msg if {
	some e in input.endpoints
	not acceptable_tls[e.tls_min_version]
	msg := sprintf("CTRL-NET-008: endpoint %q does not enforce TLS 1.2+ (min=%q)", [e.id, e.tls_min_version])
}
