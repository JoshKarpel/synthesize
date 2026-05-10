# Using Synthesize with Other Tools

## Continuous Integration

CI systems like GitHub Actions have their own workflow syntax,
but you can avoid duplicating your command definitions by calling Synthesize from your CI workflows.

The `--once` flag replaces all triggers with `Once` triggers, so the flow runs each node once and exits.

### Example: GitHub Actions

```yaml
flows:
  check:
    nodes:
      lint:
        recipe: lint
      tests:
        recipe: tests
        triggers:
          - after: [lint]
      types:
        recipe: types
        triggers:
          - after: [lint]

recipes:
  lint:  { commands: "ruff check ." }
  tests: { commands: "pytest -vv" }
  types: { commands: "mypy" }
```

```yaml
jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
      - run: uv run synth run check --once
```

!!! tip

    Synthesize does not support CI-specific features like caching, artifacts, secrets, or matrix builds.
    Use your CI system's native mechanisms for those.

## AI Coding Agents

AI coding agents need to discover a project's commands before they can help.
A `synth.yaml` is a readable index of the recipes and flows available in a project.

Agents can use `synth list` to discover available flows, then invoke them with `--once` to run a flow to completion:

```bash
synth list              # list available flows
synth list --details    # list flows with their nodes and commands
synth run --once        # run the default flow
synth run check --once  # run a specific flow
```

Moreover, since recipes are just shell commands intended to run on your local system,
agents can also learn the project's conventions from `synth.yaml` but run individual commands directly,
without going through Synthesize at all.

!!! warning

    `--once` prevents nodes from re-running, but does not stop a recipe whose command blocks forever (e.g. `mkdocs serve`).
    Flows intended for agent or CI use should contain only recipes that exit naturally;
    keep long-running processes in a separate flow.
