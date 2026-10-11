package lib.payload

import rego.v1

test_empty_object if {
	empty with input as {}
}

test_empty_list if {
	empty with input as []
}

test_empty_array_field if {
	empty with input as {"principals": []}
}

test_empty_when_every_array_is_empty if {
	empty with input as {"repositories": [], "note": "none"}
}

test_empty_null if {
	empty with input as null
}

test_not_empty_when_a_row_exists if {
	not empty with input as {"principals": [{"arn": "a"}]}
}

test_not_empty_for_nonempty_root_list if {
	not empty with input as [{"id": "x"}]
}
