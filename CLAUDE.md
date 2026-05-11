# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build/Test Commands
- Run all tests: `uv run pytest`.
- Run a single test: `uv run pytest tests/test_file.py::test_function`
- Type checking: `uv run mypy`
- Linting and formatting: `git add -u && uv run pre-commit run`
- Build docs: `uv run mkdocs build`

## Code Style Guidelines
- Line length: 120
- Strict typing: All functions must be fully typed
- Formatting and linting: Run pre-commit to enforce
- Use pathlib instead of os.path
- Follow PEP 8 conventions for naming
- Use rich for terminal output
- Pydantic for data modeling
- Use pytest for testing
- No implicit optional types
- Don't write lots of comments; the code and test names should be self-explanatory.

## Architecture Notes
- All `SYNTH_*` environment variables are defined on the `Env` pydantic-settings model in `cli.py`. New env vars should be added there so they are automatically documented via the `@env` hook in `docs/environment.md`.
- `Config.resolve(setting_overrides)` returns a `ResolvedConfig` containing the resolved flows, the effective settings (after overrides), and the computed default flow name. CLI commands work from this object rather than the raw `Config`.
- The `force_rich_terminal` autouse fixture in `tests/conftest.py` sets `SYNTH_FORCE_TERMINAL=true`, so all CLI output in tests includes ANSI escape codes. Assert on the raw output (including ANSI) rather than stripping it; use the `strip_ansi` helper only when testing non-formatting behavior.
- Docs use `@schema(module, Model)` to auto-generate field documentation from Pydantic models, and `@env(module, EnvModel)` for pydantic-settings env var models. Both are MkDocs hooks in `docs/hooks/`.

## Instructions
- You can check types and run tests at the same time by running `uv run mypy && uv run pytest`.
- When you're done making a set of changes, run `git add -u && uv run pre-commit run` to stage changes and format and lint the code.
- Never commit; I'll do the commits.
