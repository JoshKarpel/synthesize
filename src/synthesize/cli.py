from __future__ import annotations

import asyncio
from enum import Enum
from pathlib import Path
from time import monotonic
from typing import Annotated, Optional

import typer.rich_utils as ru
from click.exceptions import Exit
from dotenv import load_dotenv
from more_itertools import mark_ends
from pydantic import Field, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict
from rich.console import Console
from rich.json import JSON
from rich.markup import escape
from rich.panel import Panel
from rich.style import Style
from rich.text import Text
from typer import Argument, Option, Typer
from typing_extensions import assert_never

from synthesize.config import Config, ResolvedConfig, ResolvedFlow
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
        envvar="SYNTH_FILE",
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
    flow: Annotated[Optional[str], Argument(help="The flow to execute.")] = None,
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

    console = _make_console(Env())

    config_path, parsed_config = _load_config(config, console)

    resolved = _resolve(parsed_config, setting, console)

    if resolved.settings.dot_env.load:
        load_dotenv(config_path.parent / resolved.settings.dot_env.file)

    if dry:
        console.print(
            Panel(
                JSON(
                    parsed_config.model_copy(update={"settings": resolved.settings}).model_dump_json(exclude_unset=True)
                ),
                title="Configuration",
                title_align="left",
            )
        )

    selected_flow = _select_flow(resolved, flow, console)

    if once:
        selected_flow = selected_flow.once()

    if dry:
        return

    try:
        controller = Orchestrator(flow=selected_flow, console=console, settings=resolved.settings)
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
    """List the flows defined in the config file. The default flow is marked with [default]."""
    console = _make_console(Env())

    _, parsed_config = _load_config(config, console)

    resolved = _resolve(parsed_config, [], console)

    for is_first, is_last, (name, flow) in mark_ends(parsed_config.flows.items()):
        if details and not is_first:
            console.print()

        marker = f" [dim]{escape('[default]')}[/dim]" if name == resolved.default_flow_name else ""
        if flow.description:
            console.print(f"{name}{marker}  [dim]{flow.description}[/dim]")
        else:
            console.print(f"{name}{marker}")

        if details:
            for node in resolved.flows[name].nodes.values():
                triggers_str = ", ".join(type(t).__name__.lower() for t in node.triggers)
                lines = node.recipe.commands.strip().splitlines()
                console.print(f"  [dim]{node.id}  ({triggers_str})[/dim]")
                for line in lines:
                    console.print(f"    {line}")


class DiagramFormat(str, Enum):
    mermaid = "mermaid"


@cli.command()
def diagram(
    flow: Annotated[Optional[str], Argument(help="The flow to diagram.")] = None,
    once: OnceOption = False,
    format: Annotated[
        DiagramFormat,
        Option(help="The output format for the diagram."),
    ] = DiagramFormat.mermaid,
    config: ConfigOption = None,
) -> None:
    """Output a diagram describing a flow."""
    console = _make_console(Env())

    _, parsed_config = _load_config(config, console)

    resolved = _resolve(parsed_config, [], console)

    selected_flow = _select_flow(resolved, flow, console)

    if once:
        selected_flow = selected_flow.once()

    match format:
        case DiagramFormat.mermaid:
            print(selected_flow.mermaid())  # bare print keeps output clean for piping (e.g. the MkDocs hook)
        case _:
            assert_never(format)


class Env(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SYNTH_")

    force_terminal: Optional[bool] = Field(
        None,
        description="Force terminal formatting on (`true`) or off (`false`). Defaults to auto-detection.",
    )


def _make_console(env: Env) -> Console:
    return Console(force_terminal=env.force_terminal)


def _resolve(parsed_config: Config, setting_overrides: list[str], console: Console) -> ResolvedConfig:
    try:
        return parsed_config.resolve(setting_overrides)
    except ValueError as e:
        console.print(f"[red]ERROR[/red] {e}")
        raise Exit(code=1)
    except ValidationError as e:
        for err in e.errors():
            loc = ".".join(map(str, err["loc"]))
            msg = err["msg"]
            console.print(f"[red]ERROR[/red] setting {loc} -> {msg}")
        raise Exit(code=1)


def _select_flow(resolved: ResolvedConfig, flow: Optional[str], console: Console) -> ResolvedFlow:
    sep = "\n  "
    available_flows = sep + sep.join(resolved.flows.keys())

    if flow is None:
        flow = resolved.default_flow_name

    try:
        return resolved.flows[flow]
    except KeyError:
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
