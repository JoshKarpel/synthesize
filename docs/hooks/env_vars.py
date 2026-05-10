import importlib
import re
from collections.abc import Iterator

from mkdocs.config.defaults import MkDocsConfig
from mkdocs.structure.files import Files
from mkdocs.structure.pages import Page
from pydantic_settings import BaseSettings


def on_page_markdown(markdown: str, page: Page, config: MkDocsConfig, files: Files) -> str:
    lines = []
    for line in markdown.splitlines():
        if match := re.match(r"@env\(([\w\.]+)\s*,\s*(\w+)\)", line):
            mod = importlib.import_module(match.group(1))
            importlib.reload(mod)
            model_class = getattr(mod, match.group(2))
            lines.append("")
            lines.extend(_env_var_lines(model_class))
            lines.append("")
        else:
            lines.append(line)
    return "\n".join(lines)


def _env_var_lines(model_class: type[BaseSettings]) -> Iterator[str]:
    prefix = (model_class.model_config.get("env_prefix") or "").upper()
    for field_name, field_info in model_class.model_fields.items():
        env_var = f"{prefix}{field_name.upper()}"
        yield f"### `{env_var}`"
        yield ""
        if field_info.description:
            yield field_info.description
        yield ""
