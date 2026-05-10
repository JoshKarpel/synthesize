# Synthesize

[![PyPI](https://img.shields.io/pypi/v/synthesize)](https://pypi.org/project/synthesize)
[![PyPI - License](https://img.shields.io/pypi/l/synthesize)](https://pypi.org/project/synthesize)
[![Docs](https://img.shields.io/badge/docs-exist-brightgreen)](https://www.synth.how)

[![pre-commit.ci status](https://results.pre-commit.ci/badge/github/JoshKarpel/synthesize/main.svg)](https://results.pre-commit.ci/latest/github/JoshKarpel/synthesize/main)
[![codecov](https://codecov.io/gh/JoshKarpel/synthesize/branch/main/graph/badge.svg?token=2sjP4V0AfY)](https://codecov.io/gh/JoshKarpel/synthesize)

[![GitHub issues](https://img.shields.io/github/issues/JoshKarpel/synthesize)](https://github.com/JoshKarpel/synthesize/issues)
[![GitHub pull requests](https://img.shields.io/github/issues-pr/JoshKarpel/synthesize)](https://github.com/JoshKarpel/synthesize/pulls)

Synthesize is a DAG-shaped workflow runner for local development.
Flows are graphs of nodes that run concurrently;
each node can re-run based on conditions like file changes, predecessor completion, or unexpected exits.

Install Synthesize as a [development dependency](https://docs.astral.sh/uv/concepts/projects/dependencies/#development-dependencies) in your project:

```bash
uv add --dev synthesize
```

Then use `uv run synth --help` to see what's available.

See [the documentation](https://www.synth.how) for more information.
