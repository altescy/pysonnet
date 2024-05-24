import argparse
import json
import os
import sys
from io import StringIO
from pathlib import Path
from typing import Dict, List, Optional, TextIO

from pysonnet import __version__
from pysonnet.ast import asdict
from pysonnet.errors import PysonnetRuntimeError
from pysonnet.evaluator import Evaluator
from pysonnet.lexer import Lexer
from pysonnet.parser import Parser


def _parse_ext_vars(inputs: List[str]) -> Dict[str, str]:
    ext_vars: Dict[str, str] = {}
    for variable in inputs:
        if "=" not in variable:
            name = variable
            value = os.getenv(variable)
            if value is None:
                print(f"Environment variable {variable} was undefined.", file=sys.stderr)
                sys.exit(1)
        else:
            name, value = variable.split("=", 1)
        ext_vars[name] = value
    return ext_vars


def _show_errors(errors: List[str]) -> None:
    for error in errors:
        print(error, file=sys.stderr)


def main(prog: Optional[str] = None) -> None:
    parser = argparse.ArgumentParser(prog=prog)
    parser.add_argument("input", nargs="?", type=str, help="input file")
    parser.add_argument("-e", "--exec", action="store_true")
    parser.add_argument("-V", "--ext-str", type=str, action="append", default=[], help="external string variable")
    parser.add_argument("--ast", action="store_true", help="show the abstract syntax tree")
    parser.add_argument("--indent", type=int, default=None, help="indentation level for JSON output")
    parser.add_argument("--ensure-ascii", action="store_true", help="ensure ASCII output")
    parser.add_argument("-v", "--version", action="version", version=f"%(prog)s {__version__}")
    args = parser.parse_args()

    textio: TextIO
    filename: Optional[Path] = None
    if args.input is None:
        if not sys.stdin.isatty():
            textio = StringIO(sys.stdin.read())
        else:
            parser.error("the following arguments are required: input")
    else:
        if args.exec:
            textio = StringIO(args.input)
        else:
            textio = open(args.input)
            filename = Path(args.input)

    with textio:
        jp = Parser(Lexer(textio))
        ast = jp.parse()

    if not ast:
        _show_errors(jp.errors)
        sys.exit(1)

    if args.ast:
        print(json.dumps(asdict(ast), indent=args.indent, ensure_ascii=args.ensure_ascii))

    ext_vars = _parse_ext_vars(args.ext_str)

    try:
        evaluator = Evaluator(filename, ext_vars=ext_vars)
        value = evaluator(ast)
    except PysonnetRuntimeError as e:
        print("Runtime Error:", e.args[0], file=sys.stderr)
        sys.exit(1)

    print(json.dumps(value.to_json(), indent=args.indent, ensure_ascii=args.ensure_ascii))
