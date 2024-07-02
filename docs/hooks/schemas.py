import importlib
import re

from mkdocs.config.defaults import MkDocsConfig
from mkdocs.structure.files import Files
from mkdocs.structure.pages import Page


def on_page_markdown(
    markdown: str,
    page: Page,
    config: MkDocsConfig,
    files: Files,
) -> str:
    lines = []
    for line in markdown.splitlines():
        if match := re.match(r"@schema\(([\w\.]+)\s*\,\s*(\w*)\)", line):
            model = getattr(importlib.import_module(match.group(1)), match.group(2))
            lines.append(f"hi {model.__name__}")

        else:
            lines.append(line)
    return "\n".join(lines)
