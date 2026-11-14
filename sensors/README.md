# Sensors and normalized inputs

Sensors turn source observations into JSON consumed by OPA/Rego. The real
repository workflow uses a dedicated conservative collector; the broader examples
below describe policy input shapes, not implemented live collection for every
surface. See [current architecture](../docs/architecture.md).

## Real GitHub repository assessment

```bash
python3 scripts/assess_github.py --repo OWNER/REPO
```

[`github_assessment.py`](github_assessment.py) uses the local GitHub CLI for
read-only API requests to one explicitly named repository. It inspects the default
branch, classic protection and effective rules, and active Actions workflows.
It retains allowlisted normalized facts and safe endpoint/status diagnostics;
credentials, raw response bodies, headers, and subprocess error output do not enter
the exported evidence. API collection is a series of observations, not an atomic
snapshot.

The real CLI evaluates exactly three checks:

| Control | Normalized facts | Measurement limit |
| --- | --- | --- |
| CTRL-CHG-001 | `protected`, `allow_force_pushes` | Default-branch configuration; not proof every change followed a pull request |
| CTRL-CHG-002 | `required_reviewers`, `required_status_checks` | Configured reviewer count and check presence; not proof of completed reviews or successful runs |
| CTRL-CHG-008 | `ci_workflow` | Active workflow presence under `.github/workflows/`; not deployment reproducibility |

Unreadable or unsupported settings, ambiguous protection responses, incomplete
pagination, and unavailable bypass information become MISSING. Known absent
settings can produce FAIL. The collector does not change repository settings.
The policy uses its production threshold without asserting that this repository
is a production deployment. Read the [setup and permission guide](../docs/local-github-assessment.md)
for details and local evidence handling.

The collector returns `target`, `collected_at`, `payloads`, `errors`,
`observations`, and `limitations`. Payloads contain one repository row for each
supported policy input. The CLI builds separate report/evidence files; there is
no universal sensor `raw` envelope or automatic remote locker upload.

## Collector and adapter status

| Implementation | Status and use |
| --- | --- |
| [`github_assessment.py`](github_assessment.py) | Current private single-repository workflow; conservative real-data normalization |
| [`github.py`](github.py) | Legacy GitHub/reference adapter used by `engine.run --live`; not the isolated real assessment |
| [`terraform.py`](terraform.py) | Implemented plan JSON normalization for the reference IaC gate |
| [`procedural.py`](procedural.py) | Implemented repository-contained nonempty-file and review-date checks; no signature/content verification |
| Cloud / Kubernetes / code-scanning adapters | Stubs or design examples; not current live workspace collectors |

## Normalized payloads (per surface)

### cloud (IAM / access)

```json
{
  "principals": [
    {
      "arn": "arn:aws:iam::111:role/Deploy",
      "type": "machine",
      "privileged": true,
      "mfa_active": true
    },
    {
      "arn": "alice@example.com",
      "type": "human",
      "privileged": false,
      "mfa_active": false
    }
  ]
}
```

Policies: `access_control.iam_mfa_enforced` (CTRL-ACCESS-001)

### cloud (authorization / least-privilege)

```json
{
  "policies": [
    { "name": "AdminPolicy", "actions": ["*"], "resources": ["*"] },
    {
      "name": "ReadBuckets",
      "actions": ["s3:Get*"],
      "resources": ["arn:...:bucket/data"]
    }
  ]
}
```

Policies: `access_control.no_wildcard_policies` (CTRL-ACCESS-003)

### cloud + terraform (encryption)

```json
{
  "data_resources": [
    { "id": "prod-db", "type": "rds", "encrypted": true, "environment": "prod" }
  ]
}
```

Policies: `encryption.at_rest_required` (CTRL-ENC-001)

### cloud + terraform (network / TLS)

```json
{ "endpoints": [{ "id": "prod-lb", "tls_min_version": "1.2" }] }
```

Policies: `network.tls_12_required` (CTRL-NET-008)

### cloud (logging)

```json
{
  "audit_logs": [
    {
      "cloud": "aws",
      "enabled": true,
      "all_regions": true,
      "management_events": true
    }
  ]
}
```

Policies: `logging.audit_log_enabled` (CTRL-LOG-001)

### github (change management)

```json
{
  "repositories": [
    {
      "name": "soc2",
      "environment": "prod",
      "protected": true,
      "allow_force_pushes": false,
      "required_reviewers": 2,
      "enforce_admins": true,
      "required_status_checks": true
    }
  ]
}
```

Policies: `change_mgmt.branch_protection_enforced` (CTRL-CHG-001, CTRL-CHG-002)

### cloud + terraform (backup)

```json
{
  "datastores": [
    {
      "id": "prod-db",
      "kind": "rds",
      "environment": "prod",
      "backup_enabled": true,
      "pitr": true
    }
  ]
}
```

Policies: `backup.automated_backup_enabled` (CTRL-BKP-001)

## Legacy GitHub adapter

The older `python3 -m sensors.github` commands write to `sensors/out/` and support
repository or owner-level collection. The reference runner's `--live` option
substitutes those outputs only for jobs marked `sensor: github` in
[`engine/jobs.yaml`](../engine/jobs.yaml). Other fixture jobs, procedural inputs,
and waiver overlays remain configured. `--org` broadens the GitHub portion to the
origin owner's public repositories; it is not an implicit scope of a workspace
assessment.

Use `scripts/assess_github.py --repo OWNER/REPO` for the new real workflow, which
keeps evidence outside Git checkouts and does not mix sample inputs. A `_source.live`
flag is metadata, not independent proof of source authenticity.

## Adding a collector

Keep collection separate from evaluation, state the target and scope explicitly,
and normalize only facts supported by the source. Empty or unavailable evidence
must not silently become a passing check. Add tests for permission failures,
missing fields, malformed inputs, pagination, and secret/error redaction. Keep
example fixtures synthetic and document the actual measurement limits.
