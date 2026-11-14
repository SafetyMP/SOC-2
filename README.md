# SOC-2 — local readiness workspace

Assess GitHub repository settings, understand policy findings, and plan the next
fix without sending your evidence to a hosted workspace. SOC-2 combines a local
Python collector, OPA/Rego policy checks, and a browser interface for evidence
review. A synthetic demo lets you explore the workflow before connecting anything.

**[Try the sample workspace](https://safetymp.github.io/SOC-2/)** ·
[Project overview](https://safetymp.github.io/SOC-2/about.html) ·
[Local assessment guide](docs/local-github-assessment.md) ·
[Documentation](docs/README.md)

[![Workspace checks](https://github.com/SafetyMP/SOC-2/actions/workflows/demo.yml/badge.svg?branch=main)](https://github.com/SafetyMP/SOC-2/actions/workflows/demo.yml)
[![Policy checks](https://github.com/SafetyMP/SOC-2/actions/workflows/policy-ci.yml/badge.svg?branch=main)](https://github.com/SafetyMP/SOC-2/actions/workflows/policy-ci.yml)

## Choose your workflow

| | Real GitHub assessment | Sample workspace |
| --- | --- | --- |
| Purpose | Inspect one repository's observed settings and plan fixes | Learn how findings, evidence, and review notes work |
| Input | Read-only GitHub API collection using your local `gh` authentication | Bundled synthetic fixtures and procedural manifests |
| Scope | **3 GitHub checks**, 34 catalog controls outside scope | **20 checks**: 11 technical and 9 procedural; 17 outside scope |
| Where it runs | Local CLI and loopback browser viewer | [GitHub Pages demo](https://safetymp.github.io/SOC-2/) or local viewer |
| Evidence and notes | Private files outside Git checkouts; notes in tab memory until exported | Synthetic report; sample notes stored in your browser |

A pass describes the supplied evidence for a specific check. It is **not a SOC 2
report, CPA opinion, certification, or proof of complete framework coverage**.
Missing evidence and controls outside scope never become passes.

## Assess a repository

Prerequisites: Python 3.11+, [OPA](https://www.openpolicyagent.org/docs/latest/#running-opa),
and the [GitHub CLI](https://cli.github.com/). CI verifies policies with OPA 1.20.2.
Run from a checkout; no npm installation, hosted workspace account, or Docker service is
needed for this workflow.

```bash
git clone https://github.com/SafetyMP/SOC-2.git
cd SOC-2
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
# Use your existing GitHub CLI login, or sign in from your own terminal:
gh auth login --hostname github.com
python3 scripts/assess_github.py --repo OWNER/REPO
```

The collector prints a private report path and the command to open it:

```bash
python3 scripts/serve_workspace.py --report /absolute/path/report.json
```

Open the localhost URL printed in your terminal. The three observed checks cover
**default-branch protection and force-push settings**, **required reviews and
status checks**, and **active GitHub Actions workflow presence**. They do not
prove that every change received review or every deployment was reproducible.
Unreadable or unsupported settings become **MISSING**. See the
[permissions, exit codes, and privacy guide](docs/local-github-assessment.md).

## Review, export, and resume

Open a finding to inspect its measurement scope, source, and recommended next
step. Capture an owner, progress, and a review note. Export the report and plans
with **Export review**, then reopen that local file directly:

```bash
python3 scripts/serve_workspace.py --report /absolute/path/review.json
```

Saved notes restore at startup. A note never changes a policy verdict or creates
a waiver: a solo-maintainer decision can be recorded while the two-reviewer
check remains **FAIL**. Fix the source and rerun the assessment to measure a change.
Export newer edits before closing or reloading; the viewer never writes back to
the selected file.

## Explore without connecting GitHub

The [public demo](https://safetymp.github.io/SOC-2/) contains sample data only and
rejects real repository reports. Preview it locally with:

```bash
python3 scripts/serve_workspace.py
```

Generate a fresh **fixture-only** report from this checkout with:

```bash
python3 scripts/export_workspace.py --output /absolute/path/sample-report.json
```

The legacy `python3 -m engine.run --live` path combines GitHub observations with
other configured inputs. Use `scripts/assess_github.py` for the dedicated real-only
workflow. [Workspace usage](demo/README.md) explains both report formats.

## Privacy and scope

- Credentials stay with your local GitHub CLI; the collector sends authenticated
  read requests to GitHub. Tokens are not stored in reports or given to the browser.
- Real reports and sanitized evidence are written to fresh private directories
  outside Git checkouts. The viewer binds to `127.0.0.1`, has no upload endpoint,
  and loads no external fonts, analytics, or scripts.
- Review exports contain repository information. Keep them local and private;
  never attach real evidence or credentials to public issues or pull requests.
- Fingerprints identify collected records. The workspace does not authenticate
  report provenance, verify approval signatures, or operate a production evidence vault.
- The optional development locker, sample exceptions, and historical architecture
  plans are reference components. They are not required for local assessment.

Read [SECURITY.md](SECURITY.md) for the security boundary and private reporting.

## Develop and contribute

The stack is Python, OPA/Rego, and buildless HTML/CSS/JavaScript. Full verification
requires Node.js 22 and Terraform in addition to the assessment prerequisites:

```bash
./scripts/verify.sh
```

Verification does not collect live GitHub evidence or start the locker. Initial
installation of tools and Terraform providers can require network access.
See [CONTRIBUTING.md](CONTRIBUTING.md) for focused checks and pull-request guidance.

| Start here | What you will find |
| --- | --- |
| [Architecture](docs/architecture.md) | Current data flow and implementation boundaries |
| [Documentation map](docs/README.md) | User, contributor, and historical references |
| [Catalog](catalog/README.md) / [policies](policies/) | Control metadata and executable Rego checks |
| [Sensors](sensors/README.md) / [engine](engine/README.md) | Collection, evaluation, and scoring |
| [Agent instructions](AGENTS.md) | Repository conventions, safe commands, and verification |
| [Agent reading index](llms.txt) | A short, optional navigation aid for automated readers |

Maintained in [SafetyMP/SOC-2](https://github.com/SafetyMP/SOC-2). Use
[issues](https://github.com/SafetyMP/SOC-2/issues) for sanitized bug reports and
feature proposals; follow the [Code of Conduct](CODE_OF_CONDUCT.md).
Licensed under [Apache-2.0](LICENSE).
