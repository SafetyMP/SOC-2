# Control catalog (L0)

This directory is the input list for the local scorer. The scorer evaluates
the wired controls below and nothing else. It is not the source of truth for
a full-scope SOC 2 exam or for ISO/IEC 27001:2022 Annex A. `soc2` and
`iso27001` fields are reference labels stored on a control. They are not a
certification mapping.

An empty payload or an empty list on a technical control scores **MISSING**.

## Wired controls

### Technical (OPA/Rego)

`engine/jobs.yaml` routes these packages. Each one needs a non-empty array in
the named field.

| ID | Rego package | Payload field |
| --- | --- | --- |
| CTRL-ACCESS-001 | `access_control.iam_mfa_enforced` | `principals` |
| CTRL-ACCESS-003 | `access_control.no_wildcard_policies` | `policies` |
| CTRL-CHG-001 | `change_mgmt.branch_protection_enforced` | `repositories` |
| CTRL-CHG-002 | `change_mgmt.branch_protection_enforced` | `repositories` |
| CTRL-ENC-001 | `encryption.at_rest_required` | `data_resources` |
| CTRL-NET-008 | `network.tls_12_required` | `endpoints` |
| CTRL-LOG-001 | `logging.audit_log_enabled` | `audit_logs` |
| CTRL-BKP-001 | `backup.automated_backup_enabled` | `datastores` |

### Procedural (date manifests)

`sensors/procedural.py` reads `procedural/manifests.yaml`. PASS means
`next_review_due` is still in the future. The scorer does not open or verify
`document_ref`.

- CTRL-GOV-001, CTRL-GOV-002
- CTRL-RISK-001
- CTRL-IR-001
- CTRL-PEOPLE-001
- CTRL-SUPP-001
- CTRL-PRIV-001
- CTRL-PI-001
- CTRL-CONT-001

## Not scored

The YAML files also name controls this job does not run. Those IDs do not
affect the score. Examples that have no Rego package in this tree:
`change_mgmt.iac_policy_gate`, `change_mgmt.ci_required`,
`encryption.cmk_required_for_prod`, `encryption.no_hardcoded_secrets`, and
`data.lifecycle_enforced`.

## Schema

Each control is a YAML map:

| Field               | Type                                    | Meaning                                                                             |
| ------------------- | --------------------------------------- | ----------------------------------------------------------------------------------- |
| `id`                | string                                  | Stable local ID: `CTRL-<DOMAIN>-<NNN>`                                              |
| `title`             | string                                  | One-line statement of the control                                                   |
| `soc2`              | list                                    | Reference labels only. Not a SOC 2 exam scope.                                      |
| `iso27001`          | list                                    | Reference labels only. Not an ISO/IEC 27001 certification scope.                   |
| `criticality`       | int 1-3                                 | Weight used by the readiness scorer (L4)                                            |
| `assertion_type`    | `technical` \| `procedural` \| `policy` | Technical = sensor-evaluated; procedural = document + date; policy = governance doc |
| `evidence_validity` | ISO-8601 duration                       | `P30D` etc.; stale evidence → EXPIRED                                               |
| `sensors`           | list                                    | Which L2 adapters produce evidence                                                  |
| `rego_packages`     | list                                    | Which Rego packages evaluate this control (technical only)                          |
| `guidance`          | string                                  | Implementation notes. Not an audit opinion.                                         |

## Files

| File                      | Wired IDs in this scorer                                      |
| ------------------------- | ------------------------------------------------------------- |
| `access-control.yaml`     | CTRL-ACCESS-001, CTRL-ACCESS-003                              |
| `encryption.yaml`         | CTRL-ENC-001                                                  |
| `logging.yaml`            | CTRL-LOG-001                                                  |
| `network.yaml`            | CTRL-NET-008                                                  |
| `change-mgmt.yaml`        | CTRL-CHG-001, CTRL-CHG-002                                    |
| `backup.yaml`             | CTRL-BKP-001                                                  |
| `procedural.yaml`         | The nine manifest controls listed above                       |
| `vulnerability-mgmt.yaml` | None. Entries in this file are not scored.                    |

## Versioning

The catalog is version-controlled; a control's `id` is immutable. Retire a
control with `status: retired` rather than reusing an ID.
