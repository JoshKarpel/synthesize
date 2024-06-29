import re
import subprocess

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
        if match := re.match(r"@mermaid\(([\w\.\/]+)\)", line):
            lines.append("```mermaid")
            cmd = subprocess.run(
                ("synth", "--mermaid", "--config", match.group(1)),
                capture_output=True,
                text=True,
                check=False,
            )

            if cmd.returncode != 0:
                raise Exception(f"Error: {cmd.stdout}\n{cmd.stderr}")
            else:
                lines.append(cmd.stdout)

            lines.append("```")
        else:
            lines.append(line)

    return "\n".join(lines)
