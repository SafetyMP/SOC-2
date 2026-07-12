# SOC 2 / ISO 27001 Readiness Layer over Policy-as-Code

**Status:** Design (no code yet) · **Engine:** OPA / Rego · **Audience:** Security engineering, GRC, audit
**Scope:** IaC (Terraform), Kubernetes, Cloud accounts (AWS/Azure/GCP), CI/CD & GitHub, Code (SAST/SCA/secrets)

---

## 1. Problem & goals

SOC 2 and ISO 27001 both demand evidence that security controls are **designed** and **operating effectively**. Today that evidence is produced by hand — Word policies, screenshots, spreadsheets — collected into a point-in-time snapshot that is stale the day after the audit closes.

A **readiness layer over policy-as-code** turns controls into version-controlled, executable, continuously-evaluated rules so that:

1. **Readiness is a live number**, not a quarterly scramble. You always know your audit posture.
2. **One rule satisfies many frameworks.** A single Rego check contributes evidence to both SOC 2 and ISO 27001, eliminating duplicate work.
3. **Evidence is collected continuously and is audit-ready on demand**, with tamper-evident provenance.
4. **Gaps and drift are detected immediately** — a misconfigured resource or a missing control surfaces as a failing readiness score, not a surprise finding in eleven months.

**Non-goals (this design does not):**

- Replace the written ISMS / security policy (procedural controls still need human narrative — but they become _traceable_ to a `policy` assertion and an owner).
- Act as the SIEM. It consumes findings/posture; it is not the intrusion-detection system.
- Provide legal attestation. It produces the _artifact_ an auditor/CPA reviews; the auditor still opines.

---

## 2. Design principles

| Principle                                             | What it forces                                                                                                                             |
| ----------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------ |
| **Policy is the single source of truth**              | Frameworks are _views_ over one policy library, not separate rulebooks.                                                                    |
| **Evidence over assertion**                           | A control is "ready" only if fresh, verifiable evidence exists — never because someone checked a box.                                      |
| **Truthful provenance**                               | Every evidence record carries a real `collected_at`, a source sensor, and a content fingerprint. No backdating; stale evidence decays.     |
| **Enforce or monitor, choose per control**            | Same policy can block a `terraform apply` (enforce) or just lower a readiness score (monitor).                                             |
| **Common-control deduplication**                      | One technical check maps to N criteria across frameworks; we score once, attribute many.                                                   |
| **Fail open for the business, never for the auditor** | Enforcement gates can be bypassed via a time-boxed, approved exception — but the exception is itself recorded evidence, not a silent hole. |

---

## 3. Engine choice: OPA / Rego (and why not the alternatives)

**Recommendation: Open Policy Agent (Rego).** Rationale:

| Need                                                | OPA/Rego                 | AWS Cedar     | Cloud-native (Config/Azure Policy/Org Pol.) |
| --------------------------------------------------- | ------------------------ | ------------- | ------------------------------------------- |
| Evaluate **Terraform plans pre-apply**              | ✅ conftest / Regula     | ❌ authz-only | ⚠️ partial (limited)                        |
| **Kubernetes** admission + audit                    | ✅ Gatekeeper / Kyverno  | ❌            | ⚠️ per-cloud only                           |
| **Multi-cloud** runtime posture from exported state | ✅ (stateless JSON eval) | ❌            | ❌ one cloud each                           |
| **CI/CD & GitHub** config as data                   | ✅                       | ❌            | ❌                                          |
| **Code** SAST/SCA findings normalized               | ✅                       | ❌            | ❌                                          |
| One language, many surfaces                         | ✅                       | ⚠️ narrow     | ❌                                          |
| Mature ecosystem for compliance mapping             | ✅                       | 🟡 young      | ⚠️ vendor lock-in                           |

- **Why not Cedar?** Cedar is excellent for fine-grained _authorization_ ("can user U do action A on resource R"), but it is not a configuration-evaluation language. It cannot naturally express "this S3 bucket must be encrypted" against a Terraform plan.
- **Why not pure cloud-native?** AWS Config Rules, Azure Policy, and GCP Org Policies lock policy logic to one cloud, cannot evaluate IaC _before_ deploy, and cannot read CI/GitHub config. They are excellent **sensors** (Layer 2 below) but poor as the single policy language.

**The one gap in Rego:** it cannot _itself_ scan a live cloud account. The design closes this by pairing Rego with **state-collectors** (Steampipe / Prowler / native security hubs) that export resource state to JSON, which Rego then evaluates. Policy logic stays in one language; data acquisition is pluggable.

---

## 4. Architecture — seven layers

```
            ┌─────────────────────────────────────────────────────────────┐
   L7  CI gates        │  pre-apply (conftest) · PR (relevant policies)    │
            ├─────────────────────────────────────────────────────────────┤
   L6  Exceptions      │  time-boxed waivers (policy-as-data) + risk log   │
            ├─────────────────────────────────────────────────────────────┤
   L5  Evidence locker │  immutable · hash-attested · auditor packaging    │
            ├─────────────────────────────────────────────────────────────┤
   L4  Readiness scorer│  per-control / per-domain / per-framework %       │
            ├─────────────────────────────────────────────────────────────┤
   L3  Eval & aggregate│  run policies over sensor outputs → verdicts      │
            ├─────────────────────────────────────────────────────────────┤
   L2  Sensors (xN)    │  Terraform · K8s · Cloud · CI/CD · SAST/SCA → JSON│
            ├─────────────────────────────────────────────────────────────┤
   L1  Policy library  │  Rego rules, each tagged with control IDs         │
            ├─────────────────────────────────────────────────────────────┤
   L0  Control catalog │  canonical IDs ↔ SOC 2 TSC ↔ ISO 27001:2022 ↔ Rego│
            └─────────────────────────────────────────────────────────────┘
```

### L0 — Control catalog (source of truth)

A versioned YAML catalog that gives every obligation a **stable local ID** and binds it to both frameworks and to Rego package(s). Frameworks become projections over this catalog. Every Rego rule and every sensor references these IDs, so attribution is automatic.

```yaml
# catalog/access-control.yaml
- id: CTRL-ACCESS-001
  title: Enforce MFA on all human privileged identities
  soc2: [CC6.1, CC6.6]
  iso27001: [A.8.2, A.8.5]
  criticality: 3 # weight used by the scorer
  assertion_type: technical # technical | procedural | policy
  evidence_validity: P30D # ISO-8601 duration; stale → EXPIRED
  sensors: [cloud-steampipe, github-api]
  rego_packages:
    - access_control.iam_mfa_enforced
  guidance: |
    Every IAM principal with admin/privileged policy must have MFA enabled
    (hardware or TOTP). Programmatic (access-key) principals are out of scope
    here (see CTRL-ACCESS-007 — no static keys for humans).
```

The catalog also carries **procedural** controls (e.g. `CTRL-GOV-001` "Security policy approved annually" → CC1.x / A.5.1) whose `assertion_type: procedural` means evidence is a signed document + a review date, scored against the review cadence rather than a live sensor.

### L1 — Policy library (Rego)

Rules grouped by domain (`access_control`, `encryption`, `logging`, `vulnerability_mgmt`, `change_mgmt`, `backup`, `network`, `incident_response`, `supply_chain`). Each rule embeds metadata that ties it back to L0 so a single rule can satisfy many controls:

```rego
package access_control.iam_mfa_enforced

__rego_metadata__ := {
  "controls": ["CTRL-ACCESS-001"],
  "severity": "critical",
  "frameworks": {"soc2": ["CC6.1"], "iso27001": ["A.8.5"]},
}

# PASS when no privileged principal lacks MFA
deny[msg] {
  principal := input.privileged_principals[_]
  not principal.mfa_active
  msg := sprintf("privileged principal %q lacks MFA", [principal.arn])
}
```

Rule classes:

- **deny** — hard violation (control not met).
- **warn** — soft (weakens posture, not a fail).
- **require** — demands a positive evidence artifact exists (e.g. "a backup-restore test log exists within 180d").
- **positive assertions** are first-class ("encryption IS on"), not just negations.

### L2 — Sensors (evidence collectors)

Adapters that turn each target surface into normalized JSON (or run a native check) and emit **Evidence Records**. Sensors are the only place cloud-specific know-how lives; the policy language stays portable.

| Surface                 | Sensor                                                                                           | Output → Rego             | Trigger             |
| ----------------------- | ------------------------------------------------------------------------------------------------ | ------------------------- | ------------------- |
| Terraform               | conftest / Regula on `plan` JSON                                                                 | resource graph            | pre-apply gate, PR  |
| Kubernetes              | Gatekeeper **audit** dump + admission violations                                                 | k8s objects + constraints | nightly, on-change  |
| Cloud (AWS/Azure/GCP)   | Steampipe / Prowler / Security Hub export                                                        | resource state JSON       | scheduled (e.g. 4h) |
| CI/CD & GitHub          | GitHub API client → branch protection, required reviews, secret scanning, signing, SBOM presence | repo config JSON          | on PR, nightly      |
| Code (SAST/SCA/secrets) | Semgrep + OSV/Dependabot/Snyk + gitleaks/trufflehog                                              | normalized findings JSON  | on PR, nightly      |

### L3 — Evaluation & aggregation engine

Runs L1 policies over L2 outputs (scheduled + on-change) and emits a per-control **verdict** that the scorer (L4) consumes. Verdict states:

| State       | Meaning                                       | Counts as ready? |
| ----------- | --------------------------------------------- | ---------------- |
| `PASS`      | Policy satisfied, fresh evidence              | ✅               |
| `FAIL`      | Policy violated                               | ❌               |
| `MISSING`   | No evidence collected                         | ❌               |
| `EXPIRED`   | Evidence older than `evidence_validity`       | ❌               |
| `EXCEPTION` | FAIL but an approved, unexpired waiver exists | ⚠️ flagged       |

### L4 — Readiness scorer

Produces the live number, rolled up three ways (control → domain → framework). Distinguishes **clean readiness** (no exceptions) from **effective readiness** (exceptions accepted) so risk acceptance is visible, not hidden inside a green score.

### L5 — Evidence locker & auditor packaging

Immutable, hash-attested store (object-lock S3 + append-only transparency log, or a git ref). On demand it generates **framework-specific packages**: a SOC 2 criteria checklist and an ISO 27001:2022 Statement of Applicability (SoA), each cross-referenced to the underlying evidence artifacts.

### L6 — Exceptions / waivers

A waiver is **policy-as-data**: a signed, time-boxed record linking a failing control to a compensating control and an approver. It is evaluated _by Rego_ at scoring time (so accepted exceptions stop counting as raw FAIL but are surfaced in the risk register). No silent holes.

### L7 — CI integration & gates

Pre-deploy enforcement (Terraform plan must pass conftest), PR gates (run only policies relevant to changed files), and scheduled full-posture runs. Gate results feed back into the readiness layer as evidence.

---

## 5. Control mapping matrix (representative slice)

The matrix below shows how **one Rego rule + one sensor** satisfies criteria across both frameworks. The full catalog covers all SOC 2 common criteria (CC1–CC9) plus the selected categories (A1/C1/PI1/P*) and the relevant ISO 27001:2022 Annex A controls; this slice illustrates the pattern.

| Domain                   | Rego rule (L1)                                 | Sensor (L2)                         | SOC 2 TSC    | ISO 27001:2022         | Notes                         |
| ------------------------ | ---------------------------------------------- | ----------------------------------- | ------------ | ---------------------- | ----------------------------- |
| Access — MFA             | `access_control.iam_mfa_enforced`              | cloud-steampipe, github-api         | CC6.1, CC6.6 | A.8.2, A.8.5           | humans + privileged           |
| Access — least privilege | `access_control.no_wildcard_policies`          | cloud-steampipe                     | CC6.3        | A.8.2, A.8.3           | deny `Action:*`/`Resource:*`  |
| Access — no static keys  | `access_control.no_human_access_keys`          | cloud-steampipe                     | CC6.1        | A.8.2, A.8.4           | SSO+federation only           |
| Access — source code     | `change_mgmt.branch_protection_enforced`       | github-api                          | CC8.1, CC6.1 | A.8.4                  | protected main, ≥1 review     |
| Encryption — at rest     | `encryption.kms_at_rest_required`              | terraform-conftest, cloud-steampipe | CC6.1, C1.1  | A.8.24                 | KMS/customer-managed keys     |
| Encryption — in transit  | `network.tls_12_plus_required`                 | terraform-conftest, cloud-steampipe | CC6.7, C1.2  | A.8.24, A.8.22         | deny TLS<1.2                  |
| Network — segmentation   | `network.no_public_subnets_for_data`           | terraform-conftest, cloud-steampipe | CC6.6        | A.8.20, A.8.22         | data tier private             |
| Logging                  | `logging.audit_log_enabled_in_all_regions`     | cloud-steampipe                     | CC7.2, CC7.3 | A.8.15, A.8.16         | CloudTrail/Activity Log on    |
| Monitoring — alerting    | `logging.metric_alarm_on_root_use`             | cloud-steampipe                     | CC7.2        | A.8.16                 | alarm on root API use         |
| Clock sync               | `logging.clock_synchronisation`                | cloud-steampipe, k8s-gatekeeper     | CC7.2        | A.8.17                 | NTP/chrony enforced           |
| Vulnerability mgmt       | `vulnerability_mgmt.no_critical_unpatched`     | osv/dependabot + cloud-prowler      | CC7.1, CC7.4 | A.8.8                  | SLA-gated by severity         |
| Patch SLA                | `vulnerability_mgmt.patch_within_sla`          | osv/dependabot                      | CC7.1        | A.8.8, A.8.19          | crit ≤7d, high ≤30d           |
| Secrets in code          | `code.no_unredacted_secrets`                   | gitleaks/trufflehog                 | CC6.1, C1.1  | A.8.24, A.8.12         | block merge on hit            |
| Dependency vulns         | `code.sca_no_critical_in_build`                | osv/snyk                            | CC7.1        | A.8.8, A.8.29          | break the build               |
| Secure coding            | `code.sast_no_high_findings`                   | semgrep                             | CC8.1        | A.8.25, A.8.28         | on PR                         |
| Change mgmt              | `change_mgmt.require_pr_review`                | github-api                          | CC8.1        | A.8.32                 | ≥1 approval, no direct push   |
| Change mgmt — approvals  | `change_mgmt.min_two_reviewers_prod`           | github-api                          | CC8.1, CC5.2 | A.8.32                 | prod-only rule                |
| Backup                   | `backup.automated_backup_enabled`              | terraform-conftest, cloud-steampipe | A1.2         | A.8.13                 | PITR for datastores           |
| Backup — restore tested  | `backup.restore_test_within_window`            | scheduled-runner                    | A1.2, A1.3   | A.8.13, A.5.30         | `require`-class evidence      |
| Capacity / availability  | `availability.redundancy_required`             | terraform-conftest, cloud-steampipe | A1.1         | A.8.14, A.8.6          | multi-AZ/region for prod      |
| Malware protection       | `endpoint.antimalware_on_compute`              | cloud-steampipe                     | CC7.1        | A.8.7                  | GuardDuty/Defender on         |
| Incident response        | `incident_response.runbook_exists_and_drilled` | procedural-evidence                 | CC7.3, CC7.4 | A.5.24, A.5.25, A.5.26 | annual tabletop evidence      |
| Supplier / 3rd party     | `supply_chain.sbom_present_per_release`        | github-api, ci-runner               | CC9.2        | A.5.19, A.5.20         | SBOM artifact per release     |
| Data deletion/retention  | `data.lifecycle_enforced`                      | terraform-conftest, cloud-steampipe | C1.1, P5.x   | A.8.10                 | lifecycle policies on buckets |
| Risk assessment          | `risk.register_reviewed_quarterly`             | procedural-evidence                 | CC3.1–CC3.3  | A.5.1, A.5.7           | review-date evidence          |
| Governance / policy      | `governance.policy_approved_annually`          | procedural-evidence                 | CC1.1, CC1.3 | A.5.1, A.5.2           | signed doc + date             |

**Common-control payoff (illustrative):** `encryption.kms_at_rest_required` alone satisfies CC6.1 + C1.1 (SOC 2) and A.8.24 (ISO 27001) from a single evaluation. The catalog attributes that one verdict to four criteria automatically.

---

## 6. Evidence record schema

Every sensor emission is normalized to this shape. It is the unit the scorer consumes and the auditor package links to.

```yaml
evidence_id: ev_01HXYZ... # UUIDv7 (time-sortable)
control_id: CTRL-ACCESS-001 # ← L0 catalog ID
framework_refs: # denormalized for fast packaging
  soc2: [CC6.1, CC6.6]
  iso27001: [A.8.2, A.8.5]
status: pass # pass | fail | missing | expired | exception
source:
  sensor: cloud-steampipe # which L2 adapter
  query: aws_iam_user # reproducible query/command
  artifact_ref: s3://locker/ev_01HXYZ.json.gz
collected_at: 2026-07-11T18:30:00Z # truthful, never backdated
valid_until: 2026-08-10T18:30:00Z # collected_at + catalog.evidence_validity
fingerprint: sha256:9f2a... # hash of the raw artifact
verdict_detail:
  failing_resources: [] # empty for pass
exception: # present only when status == exception
  id: waiver_2026_07_05_a
  reason: "Legacy service account; migration in flight (TICKET-421)"
  approver: sec-lead@company
  approved_at: 2026-07-05T09:00:00Z
  expires: 2026-10-05T00:00:00Z
  compensating_controls: [CTRL-MONITOR-003]
```

Integrity guarantees: stored in an object-lock bucket, each batch appended to a transparency log keyed by `fingerprint`; the log root hash is published so any later tampering is detectable.

---

## 7. Readiness scoring model

**Per control:** a control is _Ready_ iff `status ∈ {PASS, EXCEPTION(unexpired)}`. `EXPIRED` and `MISSING` are treated as not-ready even if the control was implemented once — evidence must be live.

**Per domain / per framework:** criticality-weighted average.

```
effective_readiness(domain) = Σ_c ( criticality_c · isReady_c ) / Σ_c criticality_c
```

where `isReady_c = 1` if PASS or accepted EXCEPTION, else `0`.

**Two scores, reported together:**

- **Clean readiness** — EXCEPTION counted as _not_ ready. What the auditor sees as "controls operating, no waivers."
- **Effective readiness** — EXCEPTION counted as ready. Operational posture assuming waivers hold.
  The gap between the two is the **risk-acceptance surface area** — a number that should trend to zero.

**Validity decay:** a scheduled job re-evaluates every record at `valid_until`; once exceeded, PASS silently becomes EXPIRED and readiness drops — preventing a "green" dashboard built on three-month-old screenshots.

**Example:**

```
Access domain (3 controls, criticality 3/3/2):
  CTRL-ACCESS-001 MFA         PASS   → 3 ready
  CTRL-ACCESS-003 least-priv  EXCEPTION(approved) → effective 3, clean 0
  CTRL-ACCESS-007 no static   PASS   → 2 ready
  Clean readiness    = 5 / 8 = 62.5%
  Effective readiness= 8 / 8 = 100%
  → signal: one accepted waiver carrying the domain's risk
```

---

## 8. Per-surface integration design

### 8.1 Terraform (IaC)

- **Enforce (gate):** `terraform plan -out tfplan` → `terraform show -json tfplan` → `conftest test tfplan.json -p policies/`. CI fails the PR on `deny`. Maps mostly to CC8.1 / A.8.32 (change mgmt) and CC6.x / C1.1 (access, encryption).
- **Monitor:** same Rego run in a nightly "plan against prod" job; verdicts feed L4.

### 8.2 Kubernetes

- **Enforce:** Gatekeeper/Kyverno ConstraintTemplates in `audit=enforce` for prod, `audit` mode elsewhere. Constraint labels carry control IDs.
- **Monitor:** `gatekeeper audit` dump exported on a schedule → Rego over the violations list → L3. Covers A.8.5 (auth), A.8.24 (crypto), A.8.32 (change).

### 8.3 Cloud accounts — AWS + Azure + GCP (full big-3)

**Decision: all three providers, every account/subscription/project in org scope.** The catalog's cloud controls are written provider-agnostic in Rego; per-provider **collectors** export a normalized resource-state JSON so one policy evaluates all three.

- **AWS:** Steampipe (`aws_*` tables) across all accounts via org-wide audit role; Prowler + Security Hub as cross-check for A.8.8 (vulns) / A.8.16 (detection). Key controls: IAM MFA (CC6.1/A.8.5), no wildcard/overly-permissive policies (A.8.2/A.8.3), CloudTrail all-region + immutable (A.8.15), S3/KMS at-rest encryption (C1.1/A.8.24), public-exposure = 0 (A.8.20/A.8.22).
- **Azure:** Steampipe (`azure_*`) / Azure Policy guest config + Defender for Cloud. Controls mirror AWS: MFA on all human + privileged (A.8.5), least privilege via RBAC (A.8.2), Activity Log + diagnostic settings on (A.8.15), storage/Key Vault encryption (A.8.24), no public endpoints on data services (A.8.22).
- **GCP:** Steampipe (`gcp_*`) / Security Command Center. MFA + context-aware access (A.8.5), least-priv IAM (A.8.2), Cloud Audit Logs (A.8.15), CMEK on storage (A.8.24), VPC-SC perimeter enforcement (A.8.20/A.8.22).
- **Collect:** each provider's collector exports normalized JSON per account/subscription/project on the cadence in §8.6. Org-wide audit/readonly roles assumed per-provider; no write credentials ever held by sensors.
- **Evaluate:** provider-agnostic Rego over the normalized state.
- **Read-only by design:** sensors never mutate cloud state; cloud enforcement is via the Terraform gate (pre-apply) and native preventive controls (SCPs, Azure Policy deny, Org Policies), not via this layer.

### 8.4 CI/CD & GitHub

- A lightweight GitHub-API client reads repo/org configuration: branch protection, required reviewer counts, required status checks, secret-scanning/push-protection on, signed commits, deploy-environment approvals. Mapped to CC8.1 / A.8.32 and CC6.1 / A.8.4 (source-code access).
- Release-time checks: presence of a signed release artifact and an SBOM (CC9.2 / A.5.19 supply chain).

### 8.5 Code (SAST / SCA / secrets)

- **SAST:** Semgrep on PRs; high/critical findings block merge (CC8.1 / A.8.25, A.8.28).
- **SCA:** OSV/Dependabot/Snyk; break-the-build on criticals, SLA-gate highs (CC7.1 / A.8.8).
- **Secrets:** gitleaks/trufflehog pre-receive/PR; any hit blocks (CC6.1 / A.8.24).
- All findings normalized to the L2 finding JSON and scored against patch-SLA rules.

### 8.6 Cadence (recommended)

| Trigger                             | What runs                                                                                                    | Mode                                                                               |
| ----------------------------------- | ------------------------------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------- |
| **PR opened / synced**              | Only policies relevant to changed files (Terraform→conftest, code→SAST/SCA/secrets, `.github/*`→repo-config) | blocking in enforce (warn in burn-in)                                              |
| **Terraform pre-apply**             | conftest over `plan` JSON                                                                                    | blocking in enforce (warn in burn-in)                                              |
| **Cloud config-change event**       | EventBridge / Event Grid / Eventarc → immediate sensor run for the affected account                          | event-driven, near-real-time for high-signal rules (public exposure, MFA disabled) |
| **Scheduled — cloud posture**       | Steampipe/Prowler full export, all 3 providers, all accounts                                                 | every **4h**; critical-severity rules every **1h**                                 |
| **Scheduled — Kubernetes**          | Gatekeeper audit dump → Rego                                                                                 | every **1h**                                                                       |
| **Scheduled — readiness recompute** | Re-evaluate every record's `valid_until`; decay expired → EXPIRED; recompute scores                          | **nightly**                                                                        |

Rationale: 4h balances API cost vs. freshness across 3 providers × many accounts; critical-exposure rules need sub-hour detection; the **nightly decay** pass is what keeps the readiness number honest (no green dashboard on stale evidence). Event-driven runs close the gap between "something changed" and "we noticed" for the controls that matter most.

---

## 9. Exception / waiver model

Waivers are first-class, _not_ escape hatches:

- Stored as YAML in `exceptions/` (policy-as-data), reviewed via PR so approval is itself an auditable event.
- Each carries: control ID, reason, **approver**, **expiry**, and one or more **compensating controls**.
- A Rego data rule (`data.exceptions[_]`) is evaluated at scoring time; an unexpired, approver-signed waiver converts FAIL → EXCEPTION. Expired waivers vanish automatically and the control reverts to FAIL (readiness drops) — no manual cleanup.
- Exceptions never raise clean readiness; they only raise _effective_ readiness. The delta is the risk register.

---

## 10. Evidence locker & auditor packaging

- **Storage — self-hosted, same code two targets (recommendation):**
  - **Local/dev (Docker):** `docker compose` runs **MinIO in object-lock mode** (S3 API) + a lightweight **append-only Merkle-log service** that writes each evidence batch to MinIO and publishes its head hash to a local file. Engineers run the full collect→evaluate→package loop offline against a local locker.
  - **Prod:** cloud **object-lock** bucket on the primary provider (S3 Object Lock `COMPLIANCE` / Azure immutable blob / GCS retention lock), **cross-cloud replicated** to a second provider for durability; the Merkle service's head hash is published to the (public) repo so locker tampering is externally detectable.
  - **Why self-host over managed:** big-3 portability, no vendor lock, full control of the transparency log. A managed compliance-evidence product is the fallback if ops burden proves too high. The Merkle log can start thin and graduate to Trillian/Rekor later without changing the locker interface.
- **Packaging (on demand):**
  - **SOC 2:** criteria checklist (CC1–CC9, +A1/C1/PI1/P as applicable) with each criterion linked to its controls and the latest PASS evidence record + fingerprint.
  - **ISO 27001:2022:** Statement of Applicability (SoA) listing applicable Annex A controls (A.5–A.8), implementation status, and evidence reference; plus the risk-register cross-reference.
- Output rendered to a signed bundle (PDF/HTML + JSON manifest) the auditor/CPA can replay against the locker.

---

## 11. Proposed repository layout

```
.
├── catalog/                 # L0 control catalog (YAML), source of truth
│   ├── access-control.yaml
│   ├── encryption.yaml
│   └── ...
├── policies/                # L1 Rego policy library
│   ├── access_control/
│   ├── encryption/
│   └── ...
├── sensors/                 # L2 adapters (collectors + normalizers)
│   ├── terraform/
│   ├── kubernetes/
│   ├── cloud/
│   ├── github/
│   └── code/
├── engine/                  # L3 eval + L4 scorer + L6 waiver eval
├── evidence/                # L5 locker client + packaging
├── exceptions/              # L6 waivers (policy-as-data)
├── docs/                    # this design + control narratives
│   └── readiness-layer-design.md
└── .github/workflows/       # L7 gates + scheduled posture runs
```

---

## 12. Phased rollout

| Phase                          | Scope                                                              | Outcome                                                               |
| ------------------------------ | ------------------------------------------------------------------ | --------------------------------------------------------------------- |
| **0 — Foundation**             | L0 catalog + crosswalk (SOC 2 ↔ ISO 27001); pick pilot scope       | Every obligation has a stable ID and framework refs                   |
| **1 — IaC**                    | Terraform sensor + access/encryption/change Rego + conftest gate   | Fastest wins; CC8.1, CC6.1, C1.1 covered; first live readiness number |
| **2 — Cloud + K8s**            | Steampipe/Prowler + Gatekeeper audit; logging/backup/network rules | Operating-effectiveness evidence for CC6/CC7/A.8.x                    |
| **3 — CI/CD + Code**           | GitHub API + Semgrep/OSV/gitleaks; patch-SLA scoring               | Change-mgmt + vuln-mgmt + secrets coverage                            |
| **4 — Evidence + packaging**   | Locker, transparency log, SOC 2 checklist + ISO SoA generator      | Audit-ready artifacts on demand                                       |
| **5 — Exceptions + dashboard** | Waiver eval, clean-vs-effective scoring, trend UI                  | Continuous, honest readiness; risk surface visible                    |

**Enforcement posture — flag/warn → default-deny (decision):** prod gates do **not** block on day one.

1. **Burn-in (warn):** Phases 1–3 ship gates in **warn/monitor** mode — they run, report verdicts, and feed the readiness score, but a `deny` does not fail the build/PR/apply. Every fail is triaged: real violation → fix; noise → tune the Rego; legitimate gap → file a waiver.
2. **Flip to default-deny (enforce):** once a gate shows a sustained clean signal — e.g. **2–4 weeks with zero unexplained fails and every fail closed (fixed or waivered)** — that gate is promoted to **enforce** for prod. Dev/staging can be promoted earlier as a canary.
3. **After enforce:** a `deny` is hard; the **only** sanctioned bypass is a time-boxed, approved waiver (§9), which is recorded as EXCEPTION evidence. Promotion is per-gate, per-environment, reversible — no big-bang flip.

This sequence avoids breaking the business on immature rules while guaranteeing that once a gate is enforcing, the control is genuinely operating.

---

## 13. Risks & tradeoffs

| Risk                                                     | Mitigation                                                                                                                                                                                                                  |
| -------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Evidence-fabrication pressure** (e.g. "backdate this") | Architecture makes backdating impossible to hide: every record carries truthful `collected_at` + fingerprint + transparency-log entry; stale evidence auto-decays. Truthful provenance is a design invariant, not a nicety. |
| Rego cannot scan live cloud                              | Pair with state-collectors (Steampipe/Prowler); keep policy portable, data pluggable.                                                                                                                                       |
| Sensor drift / false negatives                           | Each control names ≥1 sensor; MISSING is a not-ready state, so a broken sensor surfaces as falling readiness rather than silent green.                                                                                      |
| Over-blocking dev with prod-grade gates                  | Per-environment enforcement classes; dev = monitor, prod = enforce, via the same policies.                                                                                                                                  |
| Transcript/secret exposure in tooling                    | Session/tooling logs that may contain prompts are routed to a **private** evidence repo, never the public code repo.                                                                                                        |
| Compliance theater                                       | Clean-vs-effective readiness split forces accepted risk into the open; can't hide waivers inside a green number.                                                                                                            |

---

## 14. Decisions (resolved)

| #   | Question                      | Decision                                                                                                                                                                                   |
| --- | ----------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 1   | SOC 2 scope                   | **Full scope** — Common Criteria (CC1–CC9) **plus all categories**: A1 Availability, C1 Confidentiality, PI1 Processing Integrity, P1–P8 Privacy. Catalog must cover the complete TSC set. |
| 2   | Cloud scope                   | **Big-3 (AWS + Azure + GCP), every account/sub/project in org scope.** Provider-agnostic Rego + per-provider normalized collectors (§8.3).                                                 |
| 3   | Procedural evidence ownership | **Recommendation adopted** — see §15.                                                                                                                                                      |
| 4   | Enforcement posture           | **Warn/flag → default-deny** after a clean-signal burn-in. Per-gate, per-env, reversible (§12).                                                                                            |
| 5   | Locker hosting                | **Recommendation adopted** — self-hosted MinIO object-lock + Merkle log, Docker-local for dev, cloud object-lock + cross-cloud replica for prod (§10).                                     |
| 6   | Cadence                       | **Recommendation adopted** — event-driven + 4h cloud (1h criticals) + 1h k8s + nightly decay recompute (§8.6).                                                                             |

---

## 15. Procedural evidence ownership (recommendation)

Procedural controls (CC1.1 policy approval, CC3.x risk review, CC7.4 IR drills, A.6.3 awareness, CC9.2 supplier review) cannot be sensed from infrastructure — they are documents + dates. They still must be policy-as-code traceable and must decay when overdue.

- **Accountability = one owner per procedural control (RACI "A").** The **Security/GRC lead** owns the _cadence tracker_ — a `procedural-evidence` sensor that reads a signed manifest and checks due dates. **Domain owners produce the artifact**: infra lead → backup restore-test log; IR lead → tabletop drill record; people ops → awareness-training completion; procurement → supplier security review.
- **Evidence shape** — a signed manifest per record:
  ```yaml
  control_id: CTRL-GOV-001
  document_ref: s3://locker/policies/infosec-policy.pdf # or a git ref
  approved_at: 2026-01-15T00:00:00Z
  approved_by: ciso@company
  next_review_due: 2027-01-15T00:00:00Z # drives decay
  fingerprint: sha256:...
  ```
  `next_review_due` is `collected_at + cadence`; once exceeded the scorer flips the record to EXPIRED and readiness drops automatically — same decay model as technical evidence.
- **Recommended cadences** (catalog `evidence_validity`):
  - Information security policy approval — **annual** (CC1.1 / A.5.1)
  - Risk register review — **quarterly** (CC3.1–CC3.4 / A.5.7)
  - Incident-response tabletop / drill — **semi-annual** (CC7.4 / A.5.24–A.5.26)
  - Security awareness training — **annual + on-join/move** (A.6.3)
  - Supplier / third-party security review — **annual** (CC9.2 / A.5.19–A.5.20)
  - Backup restore test — **semi-annual** (A1.2 / A.8.13)
- **Why this works:** ownership is named (no "who does the policy?" ambiguity), cadence is machine-enforced (overdue = falling readiness, not a forgotten spreadsheet), and the evidence locker treats procedural and technical records identically — one packaging path for the auditor.

---

## Appendix A — Framework reference (why these mappings)

- **SOC 2 Trust Services Criteria (TSC 2017, rev. 2022):** Common Criteria CC1 (Control Environment) … CC9 (Risk Mitigation) are mandatory for any engagement; A1 (Availability), C1 (Confidentiality), PI1 (Processing Integrity), and P1–P8 (Privacy) are optional categories included by scope. This layer treats them as labels on catalog controls.
- **ISO/IEC 27001:2022 Annex A:** 93 controls grouped into themes — A.5 Organizational (37), A.6 People (8), A.7 Physical (14), A.8 Technological (34). The catalog's `iso27001` field uses these IDs; the SoA generator projects the applicable subset.

## Appendix B — What "ready" will mean operationally

A control is audit-ready when, for the lookback period the auditor requests, the locker can produce a chain of PASS/EXCEPTION evidence records with non-expired `valid_until`, reproducible source queries, and matching fingerprints — with no gaps. The readiness score is the live projection of that same condition across all in-scope controls.
