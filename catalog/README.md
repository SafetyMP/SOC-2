# Control catalog (L0)

This directory defines the 37 controls visible in the readiness workspace.
Each assessment explicitly selects a smaller evaluated scope; catalog presence
alone does not mean a control was checked. It is not the source of truth for
a full-scope SOC 2 exam or for ISO/IEC 27001:2022 Annex A. `soc2` and
`iso27001` fields are reference labels stored on a control. They are not a
certification mapping.

An empty payload or an empty list on a technical control scores **MISSING**.

## Scope depends on the workflow

| Workflow | Evaluated controls | Outside scope |
| --- | --- | --- |
| Real GitHub assessment (`scripts/assess_github.py`) | CTRL-CHG-001, CTRL-CHG-002, CTRL-CHG-008 | 34 |
| Synthetic sample / default reference engine | 11 technical + 9 procedural | 17 |

The real checks observe default-branch protection/force-push settings, configured
review count and required status checks, and active GitHub Actions workflow
presence. The broader catalog titles are aspirations for controls; passing these
narrow configuration checks does not prove all changes were reviewed, status
checks succeeded, or deployments were reproducible. The workspace displays the
specific measurement limits alongside the catalog guidance.

Use the [local GitHub guide](../docs/local-github-assessment.md) for real results.
The table below documents the larger **reference fixture** scope.

## Wired reference controls

The default inputs evaluate **20 of 37 catalog controls**: **11 technical**
controls through 10 Rego packages, plus **9 procedural** controls. The other
17 catalog controls are excluded from the readiness score.

### Technical (OPA/Rego)

`engine/jobs.yaml` routes these packages. Each one needs a non-empty array in
the named field.

| ID | Rego package | Payload field |
| --- | --- | --- |
| CTRL-ACCESS-001 | `access_control.iam_mfa_enforced` | `principals` |
| CTRL-ACCESS-003 | `access_control.no_wildcard_policies` | `policies` |
| CTRL-CHG-001 | `change_mgmt.branch_protection_enforced` | `repositories` |
| CTRL-CHG-002 | `change_mgmt.branch_protection_enforced` | `repositories` |
| CTRL-CHG-005 | `change_mgmt.iac_policy_gate` | `plans` |
| CTRL-CHG-008 | `change_mgmt.ci_required` | `repositories` |
| CTRL-ENC-001 | `encryption.at_rest_required` | `data_resources` |
| CTRL-ENC-003 | `encryption.cmk_required_for_prod` | `data_resources` |
| CTRL-NET-008 | `network.tls_12_required` | `endpoints` |
| CTRL-LOG-001 | `logging.audit_log_enabled` | `audit_logs` |
| CTRL-BKP-001 | `backup.automated_backup_enabled` | `datastores` |

### Procedural (date manifests)

`sensors/procedural.py` reads `procedural/manifests.yaml`. PASS requires a
`document_ref` that resolves to a nonempty file inside the repository and a
parseable `next_review_due` strictly in the future. Missing evidence or a
missing/unparseable date scores MISSING. With the file present, a due date equal
to or earlier than the assessment time scores EXPIRED. The sensor checks file
presence and size; it does not inspect document content or verify signatures.

The supplied manifests reference files that are absent from this repository, so
all nine sample procedural controls score MISSING regardless of their dates.

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
`access_control.no_human_access_keys`, `access_control.service_account_key_age`,
`encryption.no_hardcoded_secrets`, and `data.lifecycle_enforced`.

## Schema

Each control is a YAML map:

| Field               | Type                                    | Meaning                                                                             |
| ------------------- | --------------------------------------- | ----------------------------------------------------------------------------------- |
| `id`                | string                                  | Stable local ID: `CTRL-<DOMAIN>-<NNN>`                                              |
| `title`             | string                                  | One-line statement of the control                                                   |
| `soc2`              | list                                    | Reference labels only. Not a SOC 2 exam scope.                                      |
| `iso27001`          | list                                    | Reference labels only. Not an ISO/IEC 27001 certification scope.                   |
| `criticality`       | int 1-3                                 | Weight used by the readiness scorer (L4)                                            |
| `assertion_type`    | `technical` \| `procedural` \| `policy` | Stored and validated. Procedural evaluation checks evidence file presence and review date, not document content or approval signatures. |
| `evidence_validity` | ISO-8601 duration                       | Used by the record builder to derive technical `valid_until` from collection time. Procedural records instead use the manifest review date. The scorer applies expiry to `valid_until`. |
| `sensors`           | list                                    | Which L2 adapters produce evidence                                                  |
| `rego_packages`     | list                                    | Which Rego packages evaluate this control (technical only)                          |
| `guidance`          | string                                  | Implementation notes. Not an audit opinion.                                         |

## Files

| File                      | Wired IDs in this scorer                                      |
| ------------------------- | ------------------------------------------------------------- |
| `access-control.yaml`     | CTRL-ACCESS-001, CTRL-ACCESS-003                              |
| `encryption.yaml`         | CTRL-ENC-001, CTRL-ENC-003                                    |
| `logging.yaml`            | CTRL-LOG-001                                                  |
| `network.yaml`            | CTRL-NET-008                                                  |
| `change-mgmt.yaml`        | CTRL-CHG-001, CTRL-CHG-002, CTRL-CHG-005, CTRL-CHG-008        |
| `backup.yaml`             | CTRL-BKP-001                                                  |
| `procedural.yaml`         | The nine manifest controls listed above                       |
| `vulnerability-mgmt.yaml` | None. Entries in this file are not scored.                    |

## Versioning

The catalog is version-controlled; do not reuse a control's stable `id` for a
different assertion. A retirement field alone does not remove an evaluation:
update and validate the routing and scope explicitly when retiring a control.
