# Synthesize

Synthesize is a DAG-shaped workflow runner for local development.

In Synthesize, a **flow** is a graph (potentially disjoint) of **nodes**,
each of which runs a **recipe** whenever one of that node's **triggers** activates.
Synthesize has a wide variety of triggers:

- Recipe `B` should run after recipe `A` runs.
- Recipe `W` should run every time file `F` changes.
- Recipe `R` should be restarted if it ever exits.
- Recipe `O` should run once when the flow starts.

These can all coexist as part of same flow, and can even be combined for a single recipe,
allowing for complex nodes like
["restart recipe `W` if it exits or if file `F` changes"](./triggers.md#example-restarting-on-completion-or-config-changes).

## Features

- Nodes naturally run concurrently based on their triggers.
- Recipe and trigger definitions can be factored out and shared across multiple nodes and flows.
- Recipes are just shell commands, so you can use any tools you'd like. Synthesize works with your existing tools, it doesn't replace them.
- Recipes can be parameterized with arguments (each recipe is actually a [Jinja template](https://jinja.palletsprojects.com/)) and environment variables.
  Arguments and environment variables can also be provided at the flow and recipe levels (most specific wins).
- Nodes can have multiple triggers, allowing you to express complex triggering conditions.
- All command output is combined in a single output stream, with each node's output prefixed with a timestamp and its name.
- The current time and the status of each node is displayed at the bottom of your terminal.
- You can generate [Mermaid](https://mermaid.js.org/) diagrams of your flows for debugging and documentation.

## Examples

As an example, here is Synthesize's own `synth.yaml` configuration file:

```yaml
--8<-- "synth.yaml"
```

@mermaid(synth.yaml)

## Installation

Add Synthesize as a [development dependency](https://docs.astral.sh/uv/concepts/projects/dependencies/#development-dependencies) in your project:

```bash
uv add --dev synthesize
```

Then use `uv run synth --help` to see what's available.

!!! warning "Synthesize does not work on Windows"

    We recommend using the [Windows Subsystem for Linux (WSL)](https://learn.microsoft.com/en-us/windows/wsl/install)
    to run Synthesize on Windows.

## Inspirations

- [`concurrently`](https://www.npmjs.com/package/concurrently)
- [`make`](https://www.gnu.org/software/make/)
- [`just`](https://github.com/casey/just)
