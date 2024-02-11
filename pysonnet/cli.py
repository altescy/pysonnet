import argparse
import json
import sys
from io import StringIO
from typing import Dict, List, Optional

from pysonnet import __version__
from pysonnet.ast import asdict
from pysonnet.evaluator import Evaluator
from pysonnet.lexer import Lexer
from pysonnet.parser import Parser


def _parse_ext_vars(inputs: List[str]) -> Dict[str, str]:
    ext_vars: Dict[str, str] = {}
    for value in inputs:
        if "=" not in value:
            print(f"--ext-str argument must be in the form of NAME=VALUE: {value}", file=sys.stderr)
            sys.exit(1)
        name, value = value.split("=", 1)
        ext_vars[name] = value
    return ext_vars


def _show_errors(errors: List[str]) -> None:
    for error in errors:
        print(error, file=sys.stderr)


def main(prog: Optional[str] = None) -> None:
    parser = argparse.ArgumentParser(prog=prog)
    parser.add_argument("input", nargs="?", type=argparse.FileType("r"), help="input file")
    parser.add_argument("-V", "--ext-str", type=str, action="append", default=[], help="external string variable")
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
        print(json.dumps(asdict(ast), indent=args.indent, ensure_ascii=args.ensure_ascii))

    ext_vars = _parse_ext_vars(args.ext_str)

    evaluator = Evaluator(ext_vars)
    value = evaluator(ast)
    print(json.dumps(value.to_json(), indent=args.indent, ensure_ascii=args.ensure_ascii))
