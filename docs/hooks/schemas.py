import importlib
import logging
import re
from collections.abc import Iterator, Mapping

from mkdocs.config.defaults import MkDocsConfig
from mkdocs.structure.files import Files
from mkdocs.structure.pages import Page
from openapi_pydantic import DataType, Reference, Schema

logger = logging.getLogger("mkdocs")

INDENT = " " * 4


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
            schema_raw = model.model_json_schema()
            schema = Schema.model_validate(schema_raw)
            defs = {k: Schema.model_validate(v) for k, v in schema_raw.get("$defs", {}).items()}
            lines.append("")
            lines.extend(schema_lines(schema, None, defs))
            lines.append("")
        else:
            lines.append(line)

    return "\n".join(lines)


def indent(lines: Iterator[str]) -> Iterator[str]:
    return (INDENT + l for l in lines)


def schema_lines(
    schema_or_ref: Schema | Reference, key: str | None, defs: Mapping[str, Schema]
) -> Iterator[str]:
    schema = ref_to_schema(schema_or_ref, defs)

    dt = italic(display_type(schema, defs))

    st = schema.title
    assert st is not None

    if schema.type in {DataType.STRING, DataType.NUMBER, DataType.BOOLEAN}:
        t = mono(st.lower()) if st else ""
        default = f" (Default: {mono(repr(schema.default))}) " if not schema.required else " "
        yield f"- {t} {dt} {default} {schema.description}"
    elif schema.type is DataType.ARRAY:
        t = mono(st.lower()) if st else ""
        yield f"- {t} {dt} {schema.description}"
    elif schema.type is DataType.OBJECT:
        default = (
            f" (Default: {mono(repr(schema.default))}) " if key and not schema.required else " "
        )
        yield f"- {key or st.title()} {dt} {default} {schema.description or ''}"
        if not schema.properties:
            return
        for k, prop in schema.properties.items():
            yield from indent(schema_lines(prop, mono(k), defs))
    elif schema.type is None:
        if schema.anyOf:
            yield f"- {mono(st.lower())} {dt} {schema.description}"
        else:
            raise NotImplementedError(
                f"Type {schema.type} not implemented. Appeared in the schema for {st}: {schema!r}."
            )
    else:
        raise NotImplementedError(
            f"Type {schema.type} not implemented. Appeared in the schema for {st}: {schema!r}."
        )


def ref_to_schema(schema_or_ref: Schema | Reference, defs: Mapping[str, Schema]) -> Schema:
    if isinstance(schema_or_ref, Reference):
        try:
            return defs[schema_or_ref.ref.removeprefix("#/$defs/")]
        except KeyError:
            logger.error(f"Could not find reference {schema_or_ref.ref!r} in {defs.keys()!r}")
            raise
    else:
        return schema_or_ref


def display_type(schema: Schema | Reference, defs: Mapping[str, Schema]) -> str:
    schema = ref_to_schema(schema, defs)

    st = schema.type

    if isinstance(st, DataType) and st in {
        DataType.STRING,
        DataType.NUMBER,
        DataType.BOOLEAN,
        DataType.OBJECT,
    }:
        return str(st.value)
    elif st is DataType.ARRAY:
        assert schema.items is not None
        return f"array[{display_type(schema.items, defs)}]"
    elif st is None and (options := schema.anyOf) is not None:
        schemas = [ref_to_schema(s, defs) for s in options]
        return " | ".join(s.title or str(s.type.value) for s in schemas)  # type: ignore[union-attr]
    else:
        raise NotImplementedError(f"Type {st} not implemented. Schema: {schema!r}.")


def italic(s: str) -> str:
    return f"*{s}*"


def bold(s: str) -> str:
    return f"**{s}**"


def mono(s: str) -> str:
    return f"`{s}`"
