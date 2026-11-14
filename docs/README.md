# SOC-2 documentation

SOC-2 is a local readiness workspace backed by Python sensors and OPA/Rego
checks. Start with the synthetic demo, or collect a bounded assessment of one
real GitHub repository while keeping credentials and evidence on your computer.
A score describes evaluated checks, not certification or an audit opinion.

## Choose a path

| I want to… | Start here |
| --- | --- |
| Understand the project and try the sample | [Project overview](../README.md) · [Public sample workspace](https://safetymp.github.io/SOC-2/) |
| Assess a real repository | [Local GitHub assessment](local-github-assessment.md) |
| Open a report or restore an exported review | [Workspace guide](../demo/README.md) |
| Understand the implemented components and data boundaries | [Current architecture](architecture.md) |
| Extend a check or sensor | [Control catalog](../catalog/README.md) · [Sensor contracts](../sensors/README.md) · [Engine](../engine/README.md) |
| Contribute code or documentation | [Contributing](../CONTRIBUTING.md) · [Agent instructions](../AGENTS.md) |
| Report a security problem | [Security policy](../SECURITY.md) |

## Current reference

- [Local GitHub assessment](local-github-assessment.md): setup, API permissions,
  private outputs, scope, missing evidence, and review restoration.
- [Architecture](architecture.md): implemented paths, report types, scoring,
  evidence boundaries, and components that remain examples or stubs.
- [Catalog](../catalog/README.md): stable control IDs and scope by workflow.
- [Sensors](../sensors/README.md): normalized inputs and collector limitations.
- [Engine](../engine/README.md): evaluation, records, scores, and the legacy fixture runner.
- [Procedural evidence](../procedural/README.md): sample file-presence and review-date checks.
- [Evidence utilities](../evidence/README.md): optional reference locker and packaging;
  these are separate from the private GitHub assessment workflow.
- [Exception examples](../exceptions/README.md): legacy waiver overlays and their limits;
  workspace review notes do not create waivers.

## Historical decisions and validation

These records preserve earlier reasoning and observations. They are not the
current command reference or a promise that planned integrations are implemented.

- [Initial workspace redesign](workspace-redesign.md): original fixture-only delivery.
- [First-use usability review](workspace-usability-review.md): observed interaction fixes,
  with the verification scope and counts at that point in time.
- [September positioning pivot](DESIGN-PIVOT.md): earlier sensor-pack positioning.
- [Original readiness-layer design](readiness-layer-design.md): broad architecture,
  proposed collection schedules, production storage, and other future capabilities.

The repository keeps canonical community files at its root:
[CONTRIBUTING.md](../CONTRIBUTING.md), [CODE_OF_CONDUCT.md](../CODE_OF_CONDUCT.md),
and [SECURITY.md](../SECURITY.md). Agent navigation starts at
[AGENTS.md](../AGENTS.md) and [llms.txt](../llms.txt).
