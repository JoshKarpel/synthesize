from __future__ import annotations

import asyncio
from collections.abc import Mapping
from enum import Enum
from pathlib import Path
from time import monotonic
from typing import Annotated, Optional, assert_never

import typer.rich_utils as ru
from click.exceptions import Exit
from dotenv import load_dotenv
from more_itertools import mark_ends
from pydantic import ValidationError
from rich.console import Console
from rich.json import JSON
from rich.panel import Panel
from rich.style import Style
from rich.text import Text
from typer import Argument, Option, Typer

from synthesize.config import Config, ResolvedFlow, Settings
from synthesize.orchestrator import Orchestrator
from synthesize.state import CyclicFlowDetected

ru.STYLE_HELPTEXT = ""

cli = Typer(pretty_exceptions_enable=False)


ConfigOption = Annotated[
    Optional[Path],
    Option(
        exists=True,
        readable=True,
        show_default=True,
        envvar="SYNTHFILE",
        help="The path to the configuration file.",
    ),
]

OnceOption = Annotated[
    bool,
    Option(
        help="If passed, any trigger that could cause a node to run more than once will be replaced by a `once` trigger.",
    ),
]


@cli.command()
def run(
    flow: Annotated[str, Argument(help="The flow to execute.")] = "default",
    once: OnceOption = False,
    setting: Annotated[
        list[str],
        Option(
            "-s",
            "--set",
            "--setting",
            help="Override a setting from the config file using a dotted path, e.g. `-s timestamps.sub_second_digits=3`.",
        ),
    ] = [],
    config: ConfigOption = None,
    dry: Annotated[
        bool,
        Option(help="If enabled, print the parsed config and exit without running the flow."),
    ] = False,
) -> None:
    """Run a flow."""
    start_time = monotonic()

    console = Console()

    config_path, parsed_config = _load_config(config, console)

    effective_settings = _apply_settings(parsed_config, setting, console)

    if effective_settings.dot_env.load:
        load_dotenv(config_path.parent / effective_settings.dot_env.file)

    if dry:
        console.print(
            Panel(
                JSON(
                    parsed_config.model_copy(update={"settings": effective_settings}).model_dump_json(
                        exclude_unset=True
                    )
                ),
                title="Configuration",
                title_align="left",
            )
        )

    resolved = parsed_config.resolve()

    selected_flow = _select_flow(resolved, flow, console)

    if once:
        selected_flow = selected_flow.once()

    if dry:
        return

    try:
        controller = Orchestrator(flow=selected_flow, console=console, settings=effective_settings)
    except CyclicFlowDetected as e:
        console.print(
            Text(
                f"Error: cyclic flow detected: {e.cycle_path()}. Cyclic flows are not allowed.",
                style=Style(color="red"),
            )
        )
        raise Exit(code=1)

    try:
        exit_code = asyncio.run(controller.run())
        raise Exit(code=exit_code)
    except KeyboardInterrupt:
        raise Exit(code=0)
    finally:
        end_time = monotonic()

        console.print(Text(f"Finished in {end_time - start_time:.3f} seconds. Final state:"))
        console.print(controller.renderer.state_summary())


@cli.command("list")
def list_flows(
    config: ConfigOption = None,
    details: Annotated[
        bool,
        Option(help="If enabled, show each flow's nodes with their triggers and commands."),
    ] = False,
) -> None:
    """List the flows defined in the config file."""
    console = Console()

    _, parsed_config = _load_config(config, console)

    resolved = parsed_config.resolve()

    for is_first, is_last, (name, flow) in mark_ends(parsed_config.flows.items()):
        if details and not is_first:
            console.print()

        if flow.description:
            console.print(f"{name}  [dim]{flow.description}[/dim]")
        else:
            console.print(name)

        if details:
            for node in resolved[name].nodes.values():
                triggers_str = ", ".join(type(t).__name__.lower() for t in node.triggers)
                lines = node.recipe.commands.strip().splitlines()
                console.print(f"  [dim]{node.id}  ({triggers_str})[/dim]")
                for line in lines:
                    console.print(f"    {line}")


class DiagramFormat(str, Enum):
    mermaid = "mermaid"


@cli.command()
def diagram(
    flow: Annotated[str, Argument(help="The flow to diagram.")] = "default",
    once: OnceOption = False,
    format: Annotated[
        DiagramFormat,
        Option(help="The output format for the diagram."),
    ] = DiagramFormat.mermaid,
    config: ConfigOption = None,
) -> None:
    """Output a diagram describing a flow."""
    console = Console()

    _, parsed_config = _load_config(config, console)

    resolved = parsed_config.resolve()

    selected_flow = _select_flow(resolved, flow, console)

    if once:
        selected_flow = selected_flow.once()

    match format:
        case DiagramFormat.mermaid:
            print(selected_flow.mermaid())  # bare print keeps output clean for piping (e.g. the MkDocs hook)
        case _:
            assert_never(format)


def _apply_settings(parsed_config: Config, setting: list[str], console: Console) -> Settings:
    try:
        return parsed_config.settings.with_overrides(setting)
    except ValueError as e:
        console.print(f"[red]ERROR[/red] {e}")
        raise Exit(code=1)
    except ValidationError as e:
        for err in e.errors():
            loc = ".".join(map(str, err["loc"]))
            msg = err["msg"]
            console.print(f"[red]ERROR[/red] setting {loc} -> {msg}")
        raise Exit(code=1)


def _select_flow(
    resolved: Mapping[str, ResolvedFlow],
    flow: str,
    console: Console,
) -> ResolvedFlow:
    try:
        return resolved[flow]
    except KeyError:
        sep = "\n  "
        available_flows = sep + sep.join(resolved.keys())
        console.print(
            Text(
                f"Error: no flow named '{flow}'. Available flows:{available_flows}",
                style=Style(color="red"),
            )
        )
        raise Exit(code=1)


def _load_config(config: Optional[Path], console: Console) -> tuple[Path, Config]:
    resolved = config or find_config_file(console)
    try:
        return resolved, Config.from_file(resolved)
    except ValidationError as e:
        for err in e.errors():
            loc = ".".join(map(str, err["loc"]))
            msg = err["msg"]
            console.print(f"[red]ERROR[/red] {loc} -> {msg}")
        raise Exit(code=1)


def find_config_file(console: Console) -> Path:
    cwd = Path.cwd()
    for dir in (cwd, *cwd.parents):
        contents = set(dir.iterdir())
        for name in ("synth.yaml",):
            if (path := dir / name) in contents:
                return path

        if dir / ".git" in contents:
            break

    console.print(Text("Error: failed to find a Synthesize config file", style=Style(color="red")))
    raise Exit(code=1)
