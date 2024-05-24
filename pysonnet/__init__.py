import json
from importlib.metadata import version
from io import StringIO
from os import PathLike
from typing import Callable, Mapping, Optional, Union

from pysonnet.errors import PysonnetSyntaxError
from pysonnet.evaluator import Evaluator
from pysonnet.lexer import Lexer
from pysonnet.parser import Parser
from pysonnet.types import JsonPrimitive

__version__ = version("pysonnet")
__all__ = ["Evaluator", "Lexer", "Parser", "evaluate_file", "load", "loads"]


def load(
    filename: Union[str, PathLike],
    *,
    ext_vars: Optional[Mapping[str, str]] = None,
    native_callbacks: Optional[Mapping[str, Callable[..., JsonPrimitive]]] = None,
    encoding: Optional[str] = None,
) -> JsonPrimitive:
    with open(filename, "r", encoding=encoding) as jsonnetfile:
        lexer = Lexer(jsonnetfile)
        parser = Parser(lexer)
        node = parser.parse()
        if node is None:
            raise PysonnetSyntaxError(*parser.errors)
        evaluator = Evaluator(
            filename,
            ext_vars=ext_vars,
            native_callbacks=native_callbacks,
        )
        value = evaluator(node)
    return value.to_json()


def loads(
    s: str,
    *,
    ext_vars: Optional[Mapping[str, str]] = None,
    native_callbacks: Optional[Mapping[str, Callable[..., JsonPrimitive]]] = None,
) -> JsonPrimitive:
    lexer = Lexer(StringIO(s))
    parser = Parser(lexer)
    node = parser.parse()
    if node is None:
        raise PysonnetSyntaxError(*parser.errors)
    evaluator = Evaluator(
        ext_vars=ext_vars,
        native_callbacks=native_callbacks,
    )
    value = evaluator(node)
    return value.to_json()


def evaluate_file(
    filename: Union[str, PathLike],
    *,
    ext_vars: Optional[Mapping[str, str]] = None,
    native_callbacks: Optional[Mapping[str, Callable[..., JsonPrimitive]]] = None,
    encoding: Optional[str] = None,
    indent: Optional[int] = None,
    ensure_ascii: bool = True,
) -> str:
    return json.dumps(
        load(
            filename,
            ext_vars=ext_vars,
            native_callbacks=native_callbacks,
            encoding=encoding,
        ),
        indent=indent,
        ensure_ascii=ensure_ascii,
    )
