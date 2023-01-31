from __future__ import annotations

import asyncio
from pathlib import Path
from time import monotonic

import typer.rich_utils as ru
from click.exceptions import Exit
from rich.console import Console
from rich.json import JSON
from rich.panel import Panel
from rich.text import Text
from typer import Argument, Option, Typer

from synth.config import Config
from synth.controller import Controller, State

ru.STYLE_HELPTEXT = ""

cli = Typer()


@cli.command()
def run(
    target: list[str] = Argument(None),
    config: Path = Option(
        default="synth.yaml",
        exists=True,
        readable=True,
        show_default=True,
        envvar="SYNTHFILE",
        help="The path to the configuration file to execute.",
    ),
    dry: bool = Option(
        False,
        help="If enabled, do not run actually run any commands.",
    ),
) -> None:
    start_time = monotonic()

    console = Console()

    parsed_config = Config.parse_yaml(config.read_text())

    if dry:
        console.print(
            Panel(
                JSON.from_data(parsed_config.dict()),
                title="Configuration",
                title_align="left",
            )
        )
        return

    state = State.from_targets(
        config=parsed_config, target_ids=set(target or {t.id for t in parsed_config.targets})
    )
    controller = Controller(config=parsed_config, state=state, console=console)
    try:
        asyncio.run(controller.start())
    except KeyboardInterrupt:
        raise Exit(code=0)
    finally:
        end_time = monotonic()

        console.print(Text(f"Finished in {end_time - start_time:.6f} seconds."))
