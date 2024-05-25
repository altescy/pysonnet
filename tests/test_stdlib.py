import math
from io import StringIO
from typing import Any

import pytest

from pysonnet.evaluator import Evaluator
from pysonnet.lexer import Lexer
from pysonnet.parser import Parser


@pytest.mark.parametrize(
    "inputs, expected",
    [
        ("std.prune({'a': {b: [[]]}})", {}),
        ("std.prune({'a': {b: [], c: 1, d: null}})", {"a": {"c": 1}}),
        # Mathematical functions
        ("std.mod(5, 2)", 1),
        ("std.abs(1)", 1),
        ("std.abs(-1)", 1),
        ("std.sign(10)", 1),
        ("std.sign(-5)", -1),
        ("std.sign(0)", 0),
        ("std.max(1, 2)", 2),
        ("std.min(1, 2)", 1),
        ("std.pow(2, 3)", 8),
        ("std.exp(1)", math.exp(1)),
        ("std.log(10)", math.log(10)),
        ("std.exponent(5)", 3),
        ("std.mantissa(5)", 0.625),
        ("std.floor(1.5)", 1),
        ("std.ceil(1.5)", 2),
        ("std.sqrt(4)", 2),
        ("std.sin(0)", 0),
        ("std.cos(0)", 1),
        ("std.tan(0)", 0),
        ("std.asin(0)", 0),
        ("std.acos(1)", 0),
        ("std.atan(0)", 0),
        ("std.round(1.5)", 2),
        ("std.isEven(2)", True),
        ("std.isEven(3)", False),
        ("std.isOdd(2)", False),
        ("std.isOdd(3)", True),
        ("std.isInteger(2)", True),
        ("std.isInteger(2.5)", False),
        ("std.isDecimal(2)", False),
        ("std.isDecimal(2.5)", True),
    ],
)
def test_evaluate(inputs: str, expected: Any) -> None:
    parser = Parser(Lexer(StringIO(inputs)))
    evaluator = Evaluator()
    node = parser.parse()
    assert node is not None
    result = evaluator(node).to_json()
    print("result", result, type(result))
    assert result == expected
