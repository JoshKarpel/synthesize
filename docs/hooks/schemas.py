import importlib
import logging
import re
from collections.abc import Iterator

from mkdocs.config.defaults import MkDocsConfig
from mkdocs.structure.files import Files
from mkdocs.structure.pages import Page
from openapi_pydantic import DataType, Schema

logger = logging.getLogger("mkdocs")


def on_page_markdown(
    markdown: str,
    page: Page,
    config: MkDocsConfig,
    files: Files,
) -> str:
    lines = []
    for line in markdown.splitlines():
        if match := re.match(r"@schema\(([\w\.]+)\s*\,\s*(\w*)\)", line):
            mod = importlib.import_module(match.group(1))
            importlib.reload(mod)
            model = getattr(mod, match.group(2))
            # lines.append(f"```json\n{json.dumps(model.model_json_schema(), indent=2)}\n```")
            schema = Schema.model_validate(model.model_json_schema())
            lines.append("")
            lines.extend(schema_lines(schema))
            lines.append("")
        else:
            lines.append(line)

    return "\n".join(lines)


def schema_lines(schema: Schema) -> Iterator[str]:
    i = " " * 4
    if schema.type in {DataType.STRING, DataType.NUMBER, DataType.BOOLEAN}:
        d = f'`"{schema.const}"`' if schema.const else schema.description
        t = f"`{schema.title.lower()}`" if schema.title else ""
        default = f" (Default: `{schema.default!r}`) " if not schema.required else " "
        yield f"- {t} *{schema.type}*{default}{d}"
    elif schema.type is DataType.ARRAY:
        t = f"`{schema.title.lower()}`" if schema.title else ""
        yield f"- {t} *{schema.type}[{schema.items.type}]* {schema.description}"
    elif schema.type is DataType.OBJECT:
        default = f" (Default: `{schema.default!r}`) " if not schema.required else " "
        yield f"- {schema.title.title()} *{schema.type}*{default}{schema.description or ''}"
        if not schema.properties:
            return
        for name, prop in schema.properties.items():
            yield from (i + l for l in schema_lines(prop))
    else:
        raise NotImplementedError(f"Type {schema.type} not implemented.")
