# SOC-2 readiness workspace

Cedarline Dispatch is preparing for Eastbank Food Co-op’s Friday rollout review. Start with the depot rollout and the purpose of SOC 2. See which settings the local collector can check for Priya, then open the June timeline and decide what the record supports. Switch records to compare the outcomes. The optional evidence-source controls also cover settings at collection and a quarter of changes. A second reviewer returns a finding for revision or releases a scoped reply and next owner. Revisit a missing file with a simulated owner follow-up.

The policy check and the human workpaper have different inputs. The bundled settings check under CTRL-CHG-002 maps to change management (CC8.1). Returned release and quarter packets are synthetic event evidence. A workpaper mark never changes the recorded policy verdict. Choose a three- or eight-repository pilot to compare team hours over three months.

The [technical trace](https://safetymp.github.io/SOC-2/#technical) opens with the case question and selected file. Try three branch configurations, trace the owner’s record, and inspect the customer reply after review. Comparing another file keeps the case finding intact. Bookmark the URL to resume.

[Public project overview](https://safetymp.github.io/SOC-2/about.html) ·
[Interactive sample](https://safetymp.github.io/SOC-2/)

The bundled report is generated from repository fixtures. It is not a live
assessment, an audit report, or evidence of SOC 2 certification. Catalog coverage
and weighted readiness are separate; unwired controls never count as passing.

## Preview locally

From the repository root:

```bash
python3 scripts/serve_workspace.py --port 4173
```

Open <http://127.0.0.1:4173/>. Use an HTTP server rather than opening
`index.html` directly because the browser loads modules and the sample JSON.
The interface uses plain HTML, CSS, and JavaScript. No npm install or build step
is required; the Python/Rego stack remains the source of evaluation semantics.

## Assess a real repository

Follow the [local GitHub assessment guide](../docs/local-github-assessment.md). The
local collector evaluates three GitHub checks with private evidence files. Start
the viewer with `--report /absolute/path/report.json` to open those results.
Use `--report /absolute/path/review.json` to open an exported review and restore
its notes at startup. Failed results stay failed; notes do not create waivers.
The selected file stays unchanged, and newer edits require a fresh export.
Real reports have a persistent repository/scope banner, never use sample evidence,
and keep review notes in tab memory only. The public demo rejects real reports.

## Generate and inspect a fixture report

With the repository's Python dependencies and OPA installed:

```bash
python3 scripts/export_workspace.py --output /tmp/soc2-workspace-report.json
```

Open the separate fixture viewer locally at `http://127.0.0.1:4173/?local=viewer` with the server above. Use **Open report** in that viewer to open that JSON locally. The exporter
evaluates repository fixtures only; it does not contact providers, run live
sensors, or push to an evidence locker. It writes the requested JSON output
without replacing the engine's existing evidence outputs.

To inspect a future validity date:

```bash
python3 scripts/export_workspace.py --as-of 2026-12-01 --output /tmp/soc2-future-report.json
```

An as-of report is a simulation. Actual collection timestamps remain intact.
Procedural manifests are checked for evidence availability and review dates;
the engine does not verify document content or approval signatures.

Imported reports stay in the browser. Review annotations are browser-local
planning notes and never change a control's policy result, evidence, or waiver.
Use **Export review** to save the report and action plans together. Reopen that JSON
through **Open report** to restore the plans after reviewing the replacement notice.
Raw fixture reports are also accepted. Imported reports stay in memory until reload;
export your latest review before closing or refreshing the page.
Do not publish sensitive reports in this public repository or its Pages demo.

## Verify

```bash
python3 scripts/test_export_workspace.py
python3 scripts/test_assess_github.py
python3 scripts/test_serve_workspace.py
node --test demo/*.test.mjs
node --check demo/app.js
./scripts/verify.sh
```

The existing repository verification also requires Terraform. The demo workflow
checks the adapter, browser model, and public fixture payload; it supplements the
existing policy/catalog workflows and does not replace the repository's full
Definition of Done.

## GitHub Pages

All application asset URLs are relative, so the same directory works at
`https://safetymp.github.io/SOC-2/` and on localhost. Hash-based navigation does
not require server rewrites.

.github/workflows/demo.yml verifies pull requests and deploys an explicit static
asset allowlist from `main`. GitHub Pages uses **GitHub Actions** as its source. The deploy
job has the required `pages: write` and `id-token: write` permissions; PR jobs
receive only read access. The workflow never refreshes the sample from real
provider data.

## Boundaries

- No browser account, telemetry, upload, or provider connection is included. The
  separate local collector uses authenticated read-only GitHub requests.
- Evidence fingerprints are source metadata, not independent signature checks.
- A valid exception may affect effective readiness but never clean readiness.
- Missing and expired evidence remain visible and cannot be completed by a
  review note or checklist.
- Readiness describes the evaluated slice, not the entire catalog or an
  auditor's opinion.

## First-use improvements

The action form follows each finding and recommended step; technical guidance
and evidence remain available in an expandable section. Closing a control with
unsaved edits offers Keep editing or Discard changes. Saved plans show their owner,
progress, and note in the queue, and can be filtered by progress without changing
policy results. Blank owners remain blank when reopened.

Mobile navigation exposes every destination, with larger task text and touch
targets. Readiness explanations are available beside the summary metrics. See
[the usability review](../docs/workspace-usability-review.md) for observed issues,
changes, and validation scope.

## Public discovery

`about.html` provides a project introduction, assessment limits, and setup links
without requiring JavaScript. `index.html` contains an initial semantic summary
and links before the interactive workspace loads. Both pages declare descriptive
titles, summaries, canonical URLs, and social-sharing text. The overview includes
SoftwareSourceCode structured data with the actual repository, stack, and license;
it makes no ratings or certification claims.

`sitemap.xml` lists only the two canonical public HTML URLs, never hash routes or
local evidence. `llms.txt` is a concise public source index for tools and readers;
it is not an authorization mechanism or a guarantee of agent retrieval.

GitHub Pages serves this project under `/SOC-2/`. A robots file at that subpath
would not control the host: robots.txt must live at `https://safetymp.github.io/robots.txt`.
This project does not modify that separate host-root site. Search Console sitemap
submission and indexing inspection require the host owner's verified access;
metadata and crawlable links do not guarantee indexing or ranking.

Primary guidance: [Google's JavaScript SEO basics](https://developers.google.com/search/docs/crawling-indexing/javascript/javascript-seo-basics),
[crawlable links](https://developers.google.com/search/docs/crawling-indexing/links-crawlable),
[sitemaps](https://developers.google.com/search/docs/crawling-indexing/sitemaps/build-sitemap),
and [robots.txt location](https://developers.google.com/crawling/docs/robots-txt/create-robots-txt).
