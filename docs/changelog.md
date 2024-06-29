# Changelog

## `0.0.3`

*Unreleased*

### Added

- [#3](https://github.com/JoshKarpel/synthesize/pull/3) Added PyPI classifiers and other metadata.
- [#33](https://github.com/JoshKarpel/synthesize/pull/33)
  [#40](https://github.com/JoshKarpel/synthesize/pull/40)
  Allow injecting arguments
  (via [Jinja2 templates](https://jinja.palletsprojects.com/))
  and environment variables into target commands.
  Arguments and environment variables can be specified at either
  the flow, node, or target level, with the most specific taking precedence.

### Changed

- [#30](https://github.com/JoshKarpel/synthesize/pull/30)
  Reorganized configuration to separate targets,
  triggers (formerly "lifecycles"),
  and flows (graphs of targets and triggers)."
- [#41](https://github.com/JoshKarpel/synthesize/pull/41)
  Execution duration is printed in the completion message.

## `0.0.2`

Released `2023-02-12`

### Added

- [#1](https://github.com/JoshKarpel/synthesize/pull/1) Core graph-of-targets data model and executor, with support for `once`, `restart`, and `watch` lifecycles.
- [#1](https://github.com/JoshKarpel/synthesize/pull/1) Support for YAML configuration files.
