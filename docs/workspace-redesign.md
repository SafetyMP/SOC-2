# Readiness workspace redesign

## Problem and design hypothesis

The repository had a policy/sensor engine and a terminal report, but no browser
experience. Contradictory coverage counts and outdated procedural-evidence docs
made it harder to understand what was evaluated and what to do next. This is a
source-based diagnosis; no user analytics or customer interviews were available.

The redesign tests a practical hypothesis: an explicit journey from summary to
finding, source evidence, and next action is easier to use than reading the
terminal report and reconciling multiple technical documents.

The workspace remains a reference interface for the policy/sensor pack. It does
not expand the project into an audit service or certify a control environment.

## Scope and stack

The Python/Rego engine remains authoritative. A fixture exporter creates JSON
using its actual evaluator and scorer. A narrow optional output path lets the
exporter avoid writing retained evidence files. No policy semantics change.

The browser uses HTML, CSS, and JavaScript modules without a framework, package
installation, or build step. This fits static GitHub Pages hosting and keeps the
existing Python stack intact. Node's built-in test runner verifies pure browser
logic; Node is not needed to serve the demo. Visual direction uses a quiet green
palette, clear type hierarchy, compact tables, and progressive detail panels.

## Interaction contract

- Display all 37 catalog controls; score only the 20 evaluated controls.
- Separate 11 technical and 9 procedural controls in coverage.
- Keep missing evidence, expiry, exceptions, and unevaluated controls distinct.
- Prioritize the two actual critical access failures in the bundled sample.
- Show findings, guidance, framework references, dates, and fingerprints together.
- Store review notes locally, bound to the exact report contents. Notes never
  mutate verdicts. Export the report and notes in a portable JSON review.
- Import fixture reports locally, reject invalid schema/status/date metadata,
  and escape untrusted text. Recompute displayed scores from control verdicts.
- Support responsive layouts, keyboard navigation, native modal focus behavior,
  reduced motion, labeled fields, empty states, and recoverable filters.

## Evidence and limitations

The sample snapshot was generated on November 14, 2026 from repository fixtures:
9 passing, 2 failing, and 9 missing-evidence controls; 17 unevaluated. Clean and
effective readiness both equal 46% by catalog criticality weights. The wildcard
waiver had expired, so it contributes no effective pass. All sample procedural
document references were absent. These facts are not a live company assessment.

Local verification includes the required `./scripts/verify.sh`, real Terraform
planning in warn mode, OPA format/check/tests, exporter tests, and browser model
tests. Terraform was temporarily checksum-verified outside the repository; no
infrastructure was applied. Independent review identified and led to fixes for
incompatible queue filters, malformed import dates, Git-free reports, dirty
source provenance, and focus restoration. Browser QA covers desktop/mobile
layout, findings, local persistence, filters, export, and route behavior.

Deployment of the static demo is separate from merging the source redesign.
The initial demo is published from `gh-pages`; a source PR preserves review of
the engine adapter and documentation. The included Actions workflow supports
deployment from main after the Pages source is explicitly switched to Actions.

This delivery does not establish improved customer engagement. A follow-up user
study should measure whether participants can identify the first failure, trace
its source, and record a concrete next action without help. Compare task success,
completion time, and misunderstandings against the original terminal/docs flow.
