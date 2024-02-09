import argparse
import dataclasses
import json
import sys
from io import StringIO
from typing import List, Optional

from pysonnet import __version__
from pysonnet.lexer import Lexer
from pysonnet.parser import Parser


def _show_errors(errors: List[str]) -> None:
    for error in errors:
        print(error, file=sys.stderr)


def main(prog: Optional[str] = None) -> None:
    parser = argparse.ArgumentParser(prog=prog)
    parser.add_argument("input", nargs="?", type=argparse.FileType("r"), help="input file")
    parser.add_argument("--ast", action="store_true", help="show the abstract syntax tree")
    parser.add_argument("--indent", type=int, default=None, help="indentation level for JSON output")
    parser.add_argument("--ensure-ascii", action="store_true", help="ensure ASCII output")
    parser.add_argument("-v", "--version", action="version", version=f"%(prog)s {__version__}")
    args = parser.parse_args()

    if args.input is None:
        if not sys.stdin.isatty():
            args.input = StringIO(sys.stdin.read())
        else:
            parser.error("the following arguments are required: input")

    jp = Parser(Lexer(args.input))
    ast = jp.parse()
    if not ast:
        _show_errors(jp.errors)
        sys.exit(1)

    if args.ast:
        print(json.dumps(dataclasses.asdict(ast), indent=args.indent, ensure_ascii=args.ensure_ascii))
