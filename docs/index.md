# Synthesize

Synthesize is a tool for managing long-lived development workflows that involve multiple tools executing concurrently,
each of which might have bespoke conditions around when and how it needs to be run or re-run.

In Synthesize, a **flow** is a graph (potentially disjoint) of **nodes**,
each of which runs a **target** whenever one of that node's **triggers** activates.
Synthesize has a wide variety of triggers:

- Target `B` should run after target `A` runs.
- Target `W` should run every time file `F` changes.
- Target `R` should be restarted if it ever exits.
- Target `O` should run once when the flow starts.

These can all coexist as part of same flow, and can even be combined for a single target,
allowing for complex nodes like
["restart target `W` if it exits or if file `F` changes"](./triggers.md#example-restarting-on-completion-or-config-changes).

## Features

- Target and trigger definitions can be factored out and shared across multiple nodes and flows.
- Targets are just shell commands, so you can use any tools you'd like. Synthesize works with your existing tools, it doesn't replace them.
- Targets can be parameterized with arguments (each target is actually a [Jinja template](https://jinja.palletsprojects.com/)) and environment variables.
  Arguments and environment variables can also be provided at the flow and target levels (most specific wins).
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

Synthesize is [available on PyPI](https://pypi.org/project/synthesize/).

We recommend installing Synthesize via `pipx`:

```bash
pipx install synthesize
```

Then run
```
synth --help
```
to get started.

!!! warning "Synthesize does not work on Windows"

    We recommend using the [Windows Subsystem for Linux (WSL)](https://learn.microsoft.com/en-us/windows/wsl/install)
    to run Synthesize on Windows.



## Inspirations

- [`concurrently`](https://www.npmjs.com/package/concurrently)
- [`make`](https://www.gnu.org/software/make/)
- [`just`](https://github.com/casey/just)
