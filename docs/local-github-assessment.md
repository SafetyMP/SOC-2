# Assess a real GitHub repository locally

The repository workflow collects read-only GitHub settings for **one explicitly
named repository** and evaluates three checks. It does not use the bundled sample,
procedural fixtures, or example waivers. Every other catalog control stays outside
scope. GitHub Pages remains a synthetic demo.

## Collect and open

From a local checkout of this project, install Python dependencies with
`python3 -m pip install -r requirements.txt`. Install [OPA](https://www.openpolicyagent.org/docs/latest/#running-opa)
and the [GitHub CLI](https://cli.github.com/), then use your existing local GitHub
CLI authentication. If needed, sign in from your own terminal:

```bash
gh auth login --hostname github.com
```

Do not paste credentials into the workspace or a command argument. The collector
uses `gh api` with explicit `github.com` GET requests. Existing `GH_TOKEN` or
`GITHUB_TOKEN` environment authentication also works; use your normal local secret
management, never a checked-in file.

```bash
python3 scripts/assess_github.py --repo OWNER/REPO
```

The command writes a new private directory under
`~/.local/share/soc2-workspace/assessments/` and prints the report path and viewer
command. Open that report using the printed command, for example:

```bash
python3 scripts/serve_workspace.py --report /absolute/path/report.json
```

Open the `http://127.0.0.1:8765/?local=1` URL printed in your terminal. If the port
is occupied, add `--port 8766`. Stop the viewer with Ctrl+C. A different/new report
requires restarting the viewer or using **Open report** in the local workspace.
To reopen an exported review with its notes, start the viewer and use **Open report**.

Optional output: `--output-dir /absolute/new/private/directory`. The directory must
not exist and must be outside every Git checkout. Symlink paths are refused.
Directories are created with mode `0700`; report and evidence files use `0600`.
Each run writes a fresh snapshot and does not overwrite earlier evidence.

## What the results mean

| Control | Observed check | What a pass does not prove |
| --- | --- | --- |
| CTRL-CHG-001 | Default branch protection and force-push settings | Every change used a pull request; privileged bypass is impossible |
| CTRL-CHG-002 | Configured approving-review count and required status checks | Reviews actually happened; checks succeeded |
| CTRL-CHG-008 | Presence of an active GitHub Actions workflow under `.github/workflows/` | Deployments are reproducible, successful, or exclusively automated |

The existing policies apply their production thresholds, including two approving
reviews. This does not establish that the repository deploys to production. The
workspace shows these narrower check names and their measurement limits alongside
the original catalog guidance. The other **34 controls** remain unevaluated and
never count as passing. The score describes this three-check slice only.

The collector inspects classic branch protection and effective active branch rules,
including inherited rulesets. Unsupported or unreadable settings, ambiguous 404s,
bypass settings requiring manual review, incomplete pagination, and API failures
produce **MISSING** evidence. A successful API read showing an absent required
setting can produce **FAIL**. No inaccessible setting is silently treated as safe.

Exit codes: `0` means collection and evaluation completed (findings may still fail);
`2` means a report was saved with missing evidence; `1` means setup or execution
could not complete. Open an incomplete report to see which checks need follow-up.
Local `evidence.json` contains safe endpoint/status diagnostics and normalized facts.

## Permissions and troubleshooting

Use the smallest existing access that can read your chosen repository. For a
fine-grained credential, the relevant repository permissions are Metadata: read,
Contents: read (branch metadata), Administration: read (classic branch protection),
and Actions: read (workflows). Some public endpoints work without these permissions;
organization policies and repository visibility can further restrict access.

GitHub only includes ruleset `bypass_actors` for callers with write access to that
ruleset. When that field is unavailable, this workflow leaves the protection checks
MISSING instead of assuming no bypass. You can inspect the settings manually; the
workflow does not request write access or modify protection to obtain a passing score.

For missing evidence, check the local diagnostics, repository spelling, your `gh`
account's access, token permissions, rate limits, and installed OPA. Refresh the
relevant input or permission and rerun. GitHub can return 404 for an inaccessible
resource, so a 404 alone is not proof that protection is absent.

API references: [branch protection](https://docs.github.com/en/rest/branches/branch-protection),
[branch metadata](https://docs.github.com/en/rest/branches/branches#get-a-branch),
[repository rules](https://docs.github.com/en/rest/repos/rules),
[workflows](https://docs.github.com/en/rest/actions/workflows#list-repository-workflows),
and [authentication-related 404s](https://docs.github.com/en/rest/using-the-rest-api/troubleshooting-the-rest-api#404-not-found-for-an-existing-resource).

## Local data boundary

- Authentication stays with the local GitHub CLI. Tokens and raw API responses are
  not written into evidence or passed to the browser. GitHub receives authenticated
  read requests during collection; this is not an offline collection process.
- `report.json` holds the scoped findings and target metadata. `evidence.json` holds
  sanitized observations and normalized policy inputs. These files are sensitive
  repository information even though they contain no credentials.
- The viewer binds only to `127.0.0.1`, serves an exact static asset allowlist plus
  your explicitly selected report, and has no upload or provider endpoint. It does
  not expose the evidence directory. It disables caching and external asset/network
  requests; fonts are local system fonts. Other local processes can read the viewer
  while it runs, so stop it when finished and use a trusted computer/browser.
- Real reports and review notes stay in tab memory. Reloading loses unsaved notes.
  **Export review** intentionally saves a local JSON download containing both the
  report and notes. Keep exports private; downloads follow your browser's usual
  folder permissions and are not covered by the CLI's `0600` file setting.
- Sample notes use browser-local storage under a separate report identity. Switching
  to the sample never changes or adds to a real assessment's results. The public
  Pages application rejects reports labeled as real; this is a product boundary,
  not authentication or a guarantee that manually edited files are genuine.
- Fingerprints identify records. The viewer does not independently authenticate
  report provenance or verify signatures. API reads are sequential observations,
  not an atomic snapshot; rerun after settings or branch changes.

Use `scripts/assess_github.py` for this workflow. The legacy
`python3 -m engine.run --live` path combines live GitHub inputs with the engine's
other configured inputs and is not this real-only assessment.

These results are configuration evidence, not a SOC 2 report, audit opinion,
certification, or proof of operating effectiveness.
