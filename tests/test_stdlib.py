import math
from io import StringIO
from typing import Any

import pytest

from pysonnet.errors import PysonnetRuntimeError
from pysonnet.evaluator import Evaluator
from pysonnet.lexer import Lexer
from pysonnet.parser import Parser


@pytest.mark.parametrize(
    "inputs, expected",
    [
        ("std.prune({'a': {b: [[]]}})", {}),
        ("std.prune({'a': {b: [], c: 1, d: null}})", {"a": {"c": 1}}),
        ("std.codepoint('a')", 97),
        ("std.char(97)", "a"),
        ("std.substr('hello', 1, 2)", "el"),
        ("std.findSubstr('bb', 'abbbc')", [1, 2]),
        ("std.startsWith('hello', 'he')", True),
        ("std.endsWith('hello', 'lo')", True),
        ("std.stripChars(' test  ', ' ')", "test"),
        ("std.lstripChars(' test  ', ' ')", "test  "),
        ("std.rstripChars(' test  ', ' ')", " test"),
        ("std.split('a,b,c', ',')", ["a", "b", "c"]),
        ("std.splitLimit('a,b,c', ',', 1)", ["a", "b,c"]),
        ("std.splitLimitR('a,b,c', ',', 1)", ["a,b", "c"]),
        ("std.strReplace('I like to skate with my skateboard', 'skate', 'surf')", "I like to surf with my surfboard"),
        ("std.isEmpty('')", True),
        ("std.isEmpty('x')", False),
        ("std.trim(' hello  ')", "hello"),
        ("std.equalsIgnoreCase('aBc', 'AbC')", True),
        ("std.asciiUpper('100 Cats!')", "100 CATS!"),
        ("std.asciiLower('100 Cats!')", "100 cats!"),
        ("std.stringChars('foo')", ["f", "o", "o"]),
        ("std.escapeStringBash(\"echo 'foo'\")", "'echo '\"'\"'foo'\"'\"''"),
        ("std.escapeStringDollars('hello $name')", "hello $$name"),
        ("std.escapeStringJson('Multiline\\nc:\\\\path')", '"Multiline\\nc:\\\\path"'),
        ("std.escapeStringPython('Multiline\\nc:\\\\path')", '"Multiline\\nc:\\\\path"'),
        ("std.escapeStringXml('<test>')", "&lt;test&gt;"),
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
    assert result == expected


def test_assert_equal() -> None:
    evaluator = Evaluator()

    parser = Parser(Lexer(StringIO("std.assertEqual(1, 1)")))
    node = parser.parse()
    assert node is not None
    result = evaluator(node).to_json()
    assert result

    parser = Parser(Lexer(StringIO("std.assertEqual(1, 2)")))
    node = parser.parse()
    assert node is not None
    with pytest.raises(PysonnetRuntimeError):
        evaluator(node)
