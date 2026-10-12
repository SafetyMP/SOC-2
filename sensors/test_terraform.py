import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sensors.terraform import normalize_plan


def _plan(resources):
    return {"planned_values": {"root_module": {"resources": resources}}}


def test_unencrypted_rds_is_flagged():
    plan = _plan([{"type": "aws_db_instance", "address": "aws_db_instance.db",
                   "values": {"storage_encrypted": False}}])
    out = normalize_plan(plan)
    assert out["data_resources"] == [{"id": "aws_db_instance.db", "type": "rds",
                                       "environment": "prod", "encrypted": False,
                                       "customer_managed_key": False}]


def test_encrypted_ebs_is_compliant():
    plan = _plan([{"type": "aws_ebs_volume", "address": "aws_ebs_volume.v",
                   "values": {"encrypted": True}}])
    assert normalize_plan(plan)["data_resources"][0]["encrypted"] is True


def test_missing_encrypted_defaults_false():
    plan = _plan([{"type": "aws_db_instance", "address": "aws_db_instance.x", "values": {}}])
    assert normalize_plan(plan)["data_resources"][0]["encrypted"] is False


def test_s3_encrypted_via_separate_sse_resource():
    plan = _plan([
        {"type": "aws_s3_bucket", "address": "aws_s3_bucket.logs", "values": {}},
        {"type": "aws_s3_bucket_server_side_encryption_configuration",
         "address": "aws_s3_bucket_server_side_encryption_configuration.logs",
         "values": {"bucket": "aws_s3_bucket.logs.id"}},
    ])
    dr = {d["id"]: d for d in normalize_plan(plan)["data_resources"]}
    assert dr["aws_s3_bucket.logs"]["encrypted"] is True


def test_rds_kms_key_is_customer_managed():
    plan = _plan([{"type": "aws_db_instance", "address": "aws_db_instance.db",
                   "values": {"storage_encrypted": True, "kms_key_id": "arn:aws:kms:us-east-1:1:key/abc"}}])
    row = normalize_plan(plan)["data_resources"][0]
    assert row["encrypted"] is True
    assert row["customer_managed_key"] is True


def test_s3_sse_with_master_key_is_customer_managed():
    plan = _plan([
        {"type": "aws_s3_bucket", "address": "aws_s3_bucket.logs", "values": {}},
        {"type": "aws_s3_bucket_server_side_encryption_configuration",
         "address": "aws_s3_bucket_server_side_encryption_configuration.logs",
         "values": {"bucket": "aws_s3_bucket.logs.id",
                    "rule": [{"apply_server_side_encryption_by_default": [
                        {"sse_algorithm": "aws:kms", "kms_master_key_id": "arn:aws:kms:us-east-1:1:key/abc"}]}]}},
    ])
    row = {d["id"]: d for d in normalize_plan(plan)["data_resources"]}["aws_s3_bucket.logs"]
    assert row["encrypted"] is True
    assert row["customer_managed_key"] is True


def test_s3_without_sse_is_unencrypted():
    plan = _plan([{"type": "aws_s3_bucket", "address": "aws_s3_bucket.public", "values": {}}])
    assert normalize_plan(plan)["data_resources"][0]["encrypted"] is False


def test_no_resource_changes_plan_is_non_mutating_unapproved_prod():
    plan = _plan([{"type": "aws_db_instance", "address": "aws_db_instance.db",
                   "values": {"storage_encrypted": False}}])
    out = normalize_plan(plan)
    assert out["data_resources"] == [{"id": "aws_db_instance.db", "type": "rds",
                                       "environment": "prod", "encrypted": False,
                                       "customer_managed_key": False}]
    assert out["plans"][0]["id"] == "terraform"
    assert out["plans"][0]["mutating"] is False
    assert out["plans"][0]["approved"] is False
    assert out["plans"][0]["environment"] == "prod"


def test_update_action_is_mutating():
    plan = {"resource_changes": [{"change": {"actions": ["update"]}}]}
    assert normalize_plan(plan)["plans"][0]["mutating"] is True


def test_noop_action_is_not_mutating():
    plan = {"resource_changes": [{"change": {"actions": ["no-op"]}}]}
    assert normalize_plan(plan)["plans"][0]["mutating"] is False


def test_change_approved_true():
    plan = {"variables": {"change_approved": {"value": True}}}
    assert normalize_plan(plan)["plans"][0]["approved"] is True


def test_environment_nonprod():
    plan = {"variables": {"environment": {"value": "nonprod"}}}
    assert normalize_plan(plan)["plans"][0]["environment"] == "nonprod"


def test_walks_child_modules():
    plan = {"planned_values": {"root_module": {"resources": [], "child_modules": [
        {"resources": [{"type": "aws_db_instance", "address": "m.db", "values": {"storage_encrypted": True}}]}
    ]}}}
    assert len(normalize_plan(plan)["data_resources"]) == 1


def main():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"PASS {t.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"FAIL {t.__name__}: {e}")
    print(f"\n{'PASS' if not failed else 'FAIL'}: {len(tests) - failed}/{len(tests)} terraform sensor tests")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
