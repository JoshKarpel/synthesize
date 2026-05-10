# Changelog

## Unreleased

### Added

- [#253](https://github.com/JoshKarpel/synthesize/pull/253)
  The `synth list` subcommand lists the flows defined in the config file.
  The `--details` flag additionally shows each flow's nodes with their triggers and commands.

- [#253](https://github.com/JoshKarpel/synthesize/pull/253)
  The `synth diagram` subcommand outputs a Mermaid diagram describing a flow,
  replacing the `--mermaid` flag that was previously on `synth run`.
  A `--format` flag controls the output format (currently only `mermaid`).

- [#253](https://github.com/JoshKarpel/synthesize/pull/253)
  Flows now support an optional `description` field, displayed by `synth list`.

- [#253](https://github.com/JoshKarpel/synthesize/pull/253)
  Added a [Using Synthesize with Other Tools](./other-tools.md) documentation page
  covering integration with CI systems and AI coding agents.

### Changed

- [#253](https://github.com/JoshKarpel/synthesize/pull/253)
  `synth` is now a multi-command app.
  Running a flow now requires the explicit `synth run [FLOW]` form;
  `synth [FLOW]` no longer works.

- [#253](https://github.com/JoshKarpel/synthesize/pull/253)
  The recommended installation method is now `uv add --dev synthesize`,
  adding Synthesize as a development dependency to your project.

- [#233](https://github.com/JoshKarpel/synthesize/issues/233)
  Added support for loading `.env` files via [python-dotenv](https://pypi.org/project/python-dotenv/).
  A new `settings.dot_env` sub-section controls the behavior:
  `dot_env.load` (default `true`) enables loading, and `dot_env.file` (default `.env`) sets the filename,
  resolved relative to the config file.
  Both can be overridden at run time with `-s dot_env.load=false` or `-s dot_env.file=.custom-env`.

- [#247](https://github.com/JoshKarpel/synthesize/pull/247)
  Added a `settings` section to the configuration file with a `timestamps` sub-section.
  `timestamps.sub_second_digits` (0-6, default 0) controls how many sub-second digits appear in timestamps,
  and `timestamps.include_date` (default false) prepends the date to timestamps.
  Settings can also be overridden on the command line via `-s`/`--setting` using dotted paths
  (e.g. `-s timestamps.sub_second_digits=3`).

### Changed

- [#244](https://github.com/JoshKarpel/synthesize/pull/244)
  Updated the recommended installation method from `pipx` to `uv tool install`,
  with alternatives for `uvx` and `uv add --dev`.

- [#246](https://github.com/JoshKarpel/synthesize/pull/246)
  Renamed `target`/`targets` to `recipe`/`recipes` in the configuration schema,
  matching the terminology used by [`just`](https://github.com/casey/just).

## `0.0.6`

### Added

- [#126](https://github.com/JoshKarpel/synthesize/pull/126)
  If no more work can be done in a flow, `synth` will exit.
  If all recipes ran and succeeded, the exit code will be `0`.
  Otherwise, the exit code will be `1`.
- [#126](https://github.com/JoshKarpel/synthesize/pull/126)
  Added the `--once` option, which replaces all "repeating" triggers (like `watch` or `restart`) with `once`.
  This allows an existing flow to be run as a "single shot",
  and when combined with the exit behavior change described above
  potentially useful for using Snyth workflows in CI or other automation.

### Changed

- [#128](https://github.com/JoshKarpel/synthesize/pull/128)
  The separator rule is now red when any node has failed,
  and a status summary is printed when exiting.
- [#131](https://github.com/JoshKarpel/synthesize/pull/131)
  Flows can no longer have cycles in them (via the `after` trigger).

### Fixed

- [#129](https://github.com/JoshKarpel/synthesize/pull/129)
  Ensured that the async tasks that trigger restarts don't get garbage-collected.

## `0.0.5`

Released `2025-02-12`

### Fixed

- [#112](https://github.com/JoshKarpel/synthesize/pull/112)
  Fix a crash that could happen when a process outputs too much data without a newline.

## `0.0.4`

Released `2024-10-24`

### Fixed

- [#79](https://github.com/JoshKarpel/synthesize/pull/79)
  Fix a crash that could happen when a process exits while we are trying to terminate it.

## `0.0.3`

Released `2024-07-07`

### Added

- [#3](https://github.com/JoshKarpel/synthesize/pull/3) Added PyPI classifiers and other metadata.
- [#33](https://github.com/JoshKarpel/synthesize/pull/33)
  [#40](https://github.com/JoshKarpel/synthesize/pull/40)
  Allow injecting arguments
  (via [Jinja2 templates](https://jinja.palletsprojects.com/))
  and environment variables into recipe commands.
  Arguments and environment variables can be specified at either
  the flow, node, or recipe level, with the most specific taking precedence.
- [#43](https://github.com/JoshKarpel/synthesize/pull/43)
  Mermaid diagrams can be generated for a flow using the `--mermaid` option.

### Changed

- [#30](https://github.com/JoshKarpel/synthesize/pull/30)
  Reorganized configuration to separate recipes,
  triggers (formerly "lifecycles"),
  and flows (graphs of recipes and triggers).
- [#41](https://github.com/JoshKarpel/synthesize/pull/41)
  Execution duration is printed in the completion message.
- [#49](https://github.com/JoshKarpel/synthesize/pull/49)
  Flow nodes can now have multiple triggers.

### Fixed

- [#45](https://github.com/JoshKarpel/synthesize/pull/45)
  `Restart` triggers now allow for the node's children to run again after the node completes.

## `0.0.2`

Released `2023-02-12`

### Added

- [#1](https://github.com/JoshKarpel/synthesize/pull/1) Core graph-of-recipes data model and executor, with support for `once`, `restart`, and `watch` lifecycles.
- [#1](https://github.com/JoshKarpel/synthesize/pull/1) Support for YAML configuration files.
