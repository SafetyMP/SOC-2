# Control catalog (L0)

The catalog is the **single source of truth** for every obligation. Frameworks
(SOC 2, ISO 27001) are _views_ over it, not separate rulebooks. Every Rego rule
(L1) and every sensor (L2) references these stable local IDs so attribution is
automatic.

## Schema

Each control is a YAML map:

| Field               | Type                                    | Meaning                                                                             |
| ------------------- | --------------------------------------- | ----------------------------------------------------------------------------------- |
| `id`                | string                                  | Stable local ID: `CTRL-<DOMAIN>-<NNN>`                                              |
| `title`             | string                                  | One-line statement of the control                                                   |
| `soc2`              | list                                    | SOC 2 TSC refs (CC*._, A1._, C1._, PI1._, P*.*)                                     |
| `iso27001`          | list                                    | ISO/IEC 27001:2022 Annex A refs (A._._)                                             |
| `criticality`       | int 1-3                                 | Weight used by the readiness scorer (L4)                                            |
| `assertion_type`    | `technical` \| `procedural` \| `policy` | Technical = sensor-evaluated; procedural = document + date; policy = governance doc |
| `evidence_validity` | ISO-8601 duration                       | `P30D` etc.; stale evidence → EXPIRED                                               |
| `sensors`           | list                                    | Which L2 adapters produce evidence                                                  |
| `rego_packages`     | list                                    | Which Rego packages evaluate this control (technical only)                          |
| `guidance`          | string                                  | Implementation / audit notes                                                        |

## Files

| File                      | Domain                                                             |
| ------------------------- | ------------------------------------------------------------------ |
| `access-control.yaml`     | Identity, MFA, least privilege, source-code access                 |
| `encryption.yaml`         | At-rest and in-transit cryptography                                |
| `logging.yaml`            | Audit logging, monitoring, clock sync                              |
| `network.yaml`            | Segmentation, public exposure, TLS                                 |
| `change-mgmt.yaml`        | Branch protection, reviews, change control                         |
| `vulnerability-mgmt.yaml` | Patching, SAST/SCA, secrets in code                                |
| `backup.yaml`             | Backups and restore testing                                        |
| `procedural.yaml`         | Governance, risk, IR, awareness, supplier (document+date evidence) |

## Framework coverage

This catalog targets **full-scope SOC 2** (CC1-CC9 + A1 Availability + C1
Confidentiality + PI1 Processing Integrity + P1-P8 Privacy) and **ISO/IEC
27001:2022 Annex A** (A.5 Organizational, A.6 People, A.7 Physical, A.8
Technological). Privacy (P*) and Processing Integrity (PI1) criteria are
primarily procedural/organizational and are represented in `procedural.yaml`
plus data-lifecycle entries in `encryption.yaml`.

## Versioning

The catalog is version-controlled; a control's `id` is immutable. Retire a
control with `status: retired` rather than reusing an ID.
