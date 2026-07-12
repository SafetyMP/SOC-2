# Sample Terraform for the IaC enforcement gate demo.
# Intentionally contains a violation: the RDS instance is unencrypted
# (storage_encrypted = false), which must trip CTRL-ENC-001 at `terraform plan`.
#
# skip_* flags let `terraform plan` run locally without real AWS credentials
# (these resources have no data sources, so no AWS API calls are needed).

provider "aws" {
  region                      = "us-east-1"
  access_key                  = "fake"
  secret_key                  = "fake"
  skip_credentials_validation = true
  skip_requesting_account_id  = true
  skip_metadata_api_check     = true
}

resource "aws_db_instance" "unencrypted_db" {
  engine            = "postgres"
  engine_version    = "15"
  instance_class    = "db.t3.micro"
  db_name           = "app"
  username          = "postgres"
  password          = "not-a-real-secret-this-is-a-demo-only"
  storage_encrypted = false # VIOLATION: CTRL-ENC-001
}

resource "aws_ebs_volume" "encrypted_vol" {
  availability_zone = "us-east-1a"
  size              = 10
  encrypted         = true # compliant
}
