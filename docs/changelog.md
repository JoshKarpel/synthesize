# Changelog

## `0.0.6`

## Added

- [#126](https://github.com/JoshKarpel/synthesize/pull/126)
  If no more work can be done in a flow, `synth` will exit.
  If all targets ran and succeeded, the exit code will be `0`.
  Otherwise, the exit code will be `1`.
- [#126](https://github.com/JoshKarpel/synthesize/pull/126)
  Added the `--once` option, which replaces all "repeating" triggers (like `watch` or `restart`) with `once`.
  This allows an existing flow to be run as a "single shot",
  and when combined with the exit behavior change described above
  potentially useful for using Snyth workflows in CI or other automation.

## Changed

- [#128](https://github.com/JoshKarpel/synthesize/pull/128)
  The separator rule is now red when any node has failed,
  and a status summary is printed when exiting.

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
  and environment variables into target commands.
  Arguments and environment variables can be specified at either
  the flow, node, or target level, with the most specific taking precedence.
- [#43](https://github.com/JoshKarpel/synthesize/pull/43)
  Mermaid diagrams can be generated for a flow using the `--mermaid` option.

### Changed

- [#30](https://github.com/JoshKarpel/synthesize/pull/30)
  Reorganized configuration to separate targets,
  triggers (formerly "lifecycles"),
  and flows (graphs of targets and triggers)."
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

- [#1](https://github.com/JoshKarpel/synthesize/pull/1) Core graph-of-targets data model and executor, with support for `once`, `restart`, and `watch` lifecycles.
- [#1](https://github.com/JoshKarpel/synthesize/pull/1) Support for YAML configuration files.
