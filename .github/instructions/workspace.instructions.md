---
applyTo: "demo/**,scripts/serve_workspace.py,scripts/export_workspace.py,scripts/assess_github.py"
---

# Workspace conventions

- Keep the interface buildless HTML/CSS/JavaScript. No npm installation or framework
  migration is needed for routine workspace changes.
- Make the user's next action and evidence scope clear. Preserve semantic HTML,
  keyboard focus, dialog close behavior, readable text, and responsive navigation.
- Keep real repository labels, fixture labels, and controls outside scope visible.
  Real check names and descriptions must match the limited facts actually observed.
- Keep credentials and provider calls out of the browser. Real notes use tab memory;
  preserve report identity and restore notes only with their own report.
- Treat imported JSON as untrusted data. Use the shared report/note validator and
  escape rendered text. A note, label, or progress selection cannot change a verdict.
- Preserve the local server's exact asset allowlist and request/privacy headers.
  Public Pages artifacts must contain only public assets and synthetic sample data.
- Public content must be meaningful without running the workspace. Use truthful
  metadata and crawlable links; do not promise search ranking or agent retrieval.
- Run the focused model/exporter/server tests, syntax checks, and repository
  verification. Verify changed interactions in a browser when available.
