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
- Don't write lots of comments; the code should be self-explanatory.

## Instructions
- You can check types and run tests at the same time by running `uv run mypy && uv run pytest`.
- When you're done making a set of changes, run `git add . && uv run pre-commit run` to stage changes and format and lint the code.
- Never commit; I'll do the commits.
