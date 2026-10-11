package lib.payload

import rego.v1

# Deny-contains rules are vacuous when they have no rows to inspect.
# Callers must score that MISSING, never PASS.
default empty := false

empty if {
	not is_object(input)
	not is_array(input)
}

empty if {
	is_array(input)
	count(input) == 0
}

empty if {
	is_object(input)
	not has_row
}

has_row if {
	some key
	value := input[key]
	is_array(value)
	count(value) > 0
}
