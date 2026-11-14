# SOC-2 evidence workspace

A static browser interface for the existing readiness-sensor pack. Start with
the findings that need attention, inspect the source and control guidance, and
keep a local review plan without changing the underlying verdicts.

The bundled report is generated from repository fixtures. It is not a live
assessment, an audit report, or evidence of SOC 2 certification. Catalog coverage
and weighted readiness are separate; unwired controls never count as passing.

## Preview locally

From the repository root:

```bash
python3 -m http.server 4173 --directory demo --bind 127.0.0.1
```

Open <http://127.0.0.1:4173/>. Use an HTTP server rather than opening
`index.html` directly because the browser loads modules and the sample JSON.
The interface uses plain HTML, CSS, and JavaScript. No npm install or build step
is required; the Python/Rego stack remains the source of evaluation semantics.

## Generate and inspect a report

With the repository's Python dependencies and OPA installed:

```bash
python3 scripts/export_workspace.py --output /tmp/soc2-workspace-report.json
```

Use **Import report** in the workspace to open that JSON locally. The exporter
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
Export a report to retain the review context before clearing browser data.
Do not publish sensitive reports in this public repository or its Pages demo.

## Verify

```bash
python3 scripts/test_export_workspace.py
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

An initial publication may put only the contents of `demo/` on the `gh-pages`
branch and configure Pages to serve that branch's root. This keeps the original
`main` branch available for source review. Copy the static payload, not the
repository's private or locally generated evidence directories.

Once the redesign is merged, `.github/workflows/demo.yml` verifies pull requests
and deploys `demo/` on `main` pushes or manual runs on `main`. Set the repository's
Pages publishing source to **GitHub Actions** to use this workflow. The deploy
job has the required `pages: write` and `id-token: write` permissions; PR jobs
receive only read access. The workflow never refreshes the sample from real
provider data.

## Boundaries

- No account, backend, telemetry, or live provider connection is included.
- Evidence fingerprints are source metadata, not independent signature checks.
- A valid exception may affect effective readiness but never clean readiness.
- Missing and expired evidence remain visible and cannot be completed by a
  review note or checklist.
- Readiness describes the evaluated slice, not the entire catalog or an
  auditor's opinion.
