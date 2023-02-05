from lark import Lark
from rich.console import Console

# tree_grammar = r"""
# ?start: (_NL* target _NL*)*
#
# target: NAME ":" _NL [_INDENT COMMAND+ _DEDENT]
#
# %import common.WS_INLINE
# %declare _INDENT _DEDENT
# %ignore WS_INLINE
#
# _NL: /(\r?\n[\t ]*)+/
# COMMAND: /[\w \n]+/
# NAME: /[\w\-]/+
# """
#
# class TreeIndenter(Indenter):
#     NL_type = '_NL'
#     OPEN_PAREN_types = []
#     CLOSE_PAREN_types = []
#     INDENT_type = '_INDENT'
#     DEDENT_type = '_DEDENT'
#     tab_len = 4
#
# parser = Lark(tree_grammar, parser='lalr', postlex=TreeIndenter())

tree_grammar = r"""
?start: (NL* target)*

target: NAME ":" NL meta_line* command_line+
NAME: /[\w\-]/+

meta_line: META_WS "@" META_ATTR (META_WS META_ARG)* NL

META_WS: /[ \t]+/
META_ATTR: /\w+/
META_ARG: /\w+/

command_line: COMMAND_LINE | BLANK_LINE
COMMAND_LINE: /[ \t]+[\w ]*\r?\n/
BLANK_LINE: /\r?\n/

NL: /\r?\n/
"""


parser = Lark(tree_grammar, parser="lalr")


def parse(text: str):
    print(repr(text))
    parsed = parser.parse(text)

    print(parsed)

    console = Console()
    console.print(parsed)
