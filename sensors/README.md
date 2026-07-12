# Sensors (L2)

Sensors turn each target surface into **normalized JSON** that the provider-agnostic
Rego policies evaluate. This file is the **output contract** — a sensor is conforming
iff its emission matches the schema its policy expects.

Each sensor emission is wrapped in the evidence-record envelope from
`docs/readiness-layer-design.md §6`, with the surface-specific payload in a
`raw` field. The payloads below are what Rego `input` is bound to.

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

## Sensor status

| Sensor                          | Status          | Notes                                                                                         |
| ------------------------------- | --------------- | --------------------------------------------------------------------------------------------- |
| `github-api`                    | **implemented** | `sensors/github.py` reads live branch protection via `gh api`; `python3 -m engine.run --live` |
| `terraform-conftest`            | designed        | conftest over `terraform show -json plan`; gate workflow Phase 1                              |
| `cloud-steampipe`               | stub            | Steampipe queries per provider -> payloads above (Phase 2)                                    |
| `code-*` (semgrep/osv/gitleaks) | stub            | findings -> normalized finding JSON (Phase 3)                                                 |
| `k8s-gatekeeper`                | stub            | Gatekeeper audit dump (Phase 2)                                                               |
| `procedural-evidence`           | stub            | signed-manifest reader for procedural controls (§15)                                          |

A sensor that produces no payload for a control it owns causes the control to be
scored `MISSING` (not-ready) — a broken sensor surfaces as falling readiness,
never as silent green.

### Running the live github sensor

```bash
python3 -m sensors.github                       # collect origin repo -> sensors/out/github.json
python3 -m sensors.github --repo OWNER/REPO     # collect a specific repo
python3 -m engine.run --live                    # refresh sensor(s) then evaluate live data
```

Live evidence is tagged `_source.live: true`; `--live` swaps in the sensor
output for any job declaring `sensor: github` in `engine/jobs.yaml`.
