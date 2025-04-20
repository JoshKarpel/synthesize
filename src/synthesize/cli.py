from __future__ import annotations

import asyncio
from pathlib import Path
from time import monotonic
from typing import Optional

import typer.rich_utils as ru
from click.exceptions import Exit
from pydantic import ValidationError
from rich.console import Console
from rich.json import JSON
from rich.panel import Panel
from rich.style import Style
from rich.text import Text
from typer import Argument, Option, Typer

from synthesize.config import Config
from synthesize.orchestrator import Orchestrator
from synthesize.state import CyclicFlowDetected

ru.STYLE_HELPTEXT = ""

cli = Typer(pretty_exceptions_enable=False)


@cli.command()
def run(
    flow: str = Argument(
        default="default",
        help="The flow to execute.",
    ),
    once: bool = Option(
        default=False,
        help="If passed, any trigger that could cause a node to run more than once will be replaced by a `once` trigger.",
    ),
    config: Optional[Path] = Option(
        default=None,
        exists=True,
        readable=True,
        show_default=True,
        envvar="SYNTHFILE",
        help="The path to the configuration file to execute.",
    ),
    mermaid: bool = Option(
        default=False,
        help="If enabled, output a description of the flow as a Mermaid diagram, and don't run the flow.",
    ),
    dry: bool = Option(
        default=False,
        help="If enabled, do not run actually run the flow.",
    ),
) -> None:
    start_time = monotonic()

    console = Console()

    config = config or find_config_file(console)

    try:
        parsed_config = Config.from_file(config)
    except ValidationError as e:
        for err in e.errors():
            loc = ".".join(map(str, err["loc"]))
            msg = err["msg"]
            console.print(f"[red]ERROR[/red] {loc} -> {msg}")
        raise Exit(code=1)

    if dry:
        console.print(
            Panel(
                JSON(parsed_config.model_dump_json(exclude_unset=True)),
                title="Configuration",
                title_align="left",
            )
        )

    resolved = parsed_config.resolve()

    try:
        selected_flow = resolved[flow]
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

    if once:
        selected_flow = selected_flow.once()

    if mermaid:
        print(selected_flow.mermaid())
        return

    if dry:
        return

    try:
        controller = Orchestrator(flow=selected_flow, console=console)
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
