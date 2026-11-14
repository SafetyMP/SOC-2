# First-use review and fixes

**Historical usability record — first-use fixes, November 2026.** These are the
observations and checks from that delivery, not current test totals or customer
engagement measurements. The current workspace also has a private real-repository
flow and can restore an exported review directly with `--report`. Real notes stay
in tab memory; sample notes may use browser-local storage. See the
[current architecture](architecture.md) and [workspace guide](../demo/README.md).

---

Reviewed the live demo on November 14, 2026 by walking through the sample as a
new visitor. This is a task-based usability inspection, not a customer study or
proof of improved engagement. An independent read-only source review supplemented
the browser observations.

## Observed friction and resulting changes

| Observation | Change |
| --- | --- |
| Mobile navigation clipped Evidence and How it works without an obvious cue | All five destinations remain visible in a wrapping navigation layout |
| Task text, result badges, and controls were small on mobile | Larger task text, 16px touch inputs, and larger navigation/close/action targets |
| Users had to scroll past policy guidance and provenance to record an action | Finding, recommended step, and action form now precede expandable evidence |
| Exported reviews could not be reopened through the import control | Open report explains and accepts both fixture snapshots and saved reviews; restored plans are validated before replacement |
| Saving only an owner or note was visible only in a temporary toast | Queue rows show saved-plan progress, owner, and note excerpts; a progress filter supports follow-up |
| Escape or closing a control silently discarded unfinished edits | Dirty forms offer Keep editing or Discard changes; unchanged forms close directly |
| Clean and effective readiness terminology needed explanation away from the metrics | Plain descriptions and explanation buttons sit beside the values; as-of simulations are labeled |

## Acceptance and evidence

- Browser walkthrough: save an action plan, export, reset, reopen the saved JSON,
  and restore the same plan without changing the FAIL result or 46% score.
- The shared model tests validate review envelopes, note limits, unknown control
  IDs, prototype-shaped data, progress filtering, and unchanged verdicts.
- Independent review identified fixes for clearing owners, resetting one report
  without deleting another report's plans, focus after filtered saves, and the
  skip link preserving the current route.
- Responsive browser checks cover 320px, 390px, and desktop layouts. Navigation
  remains discoverable and page-level horizontal overflow is checked.
- The existing verification contract remains intact: 76 Python tests and the
  Terraform warn gate; 14 exporter tests and 37 Rego tests also pass.

Notes remain local to the browser. Imported reports remain in memory until
reload, with that limit explained in the opening flow and overview. Export a
review to retain its report and action plans together. Restoring a saved review
explicitly replaces saved plans for the same report. The source snapshot,
assessment semantics, and Python/Rego engine are unchanged in this pass.
