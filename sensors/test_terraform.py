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
                                       "environment": "prod", "encrypted": False}]


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


def test_s3_without_sse_is_unencrypted():
    plan = _plan([{"type": "aws_s3_bucket", "address": "aws_s3_bucket.public", "values": {}}])
    assert normalize_plan(plan)["data_resources"][0]["encrypted"] is False


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
