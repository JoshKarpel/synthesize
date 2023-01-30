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
from synth.controller import Controller

ru.STYLE_HELPTEXT = ""

cli = Typer()


@cli.command()
def run(
    config_path: Path = Argument(
        default="synth.yaml",
        metavar="config",
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

    config = Config.parse_yaml(config_path.read_text())

    if dry:
        console.print(
            Panel(
                JSON.from_data(config.dict()),
                title="Configuration",
                title_align="left",
            )
        )
        return

    controller = Controller(config=config, console=console)
    try:
        asyncio.run(controller.start())
    except KeyboardInterrupt:
        raise Exit(code=0)
    finally:
        end_time = monotonic()

        console.print(Text(f"Finished in {end_time - start_time:.6f} seconds."))
