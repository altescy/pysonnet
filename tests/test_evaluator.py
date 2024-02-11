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
        ("1 + 2", 3),
        ("true && false", False),
        ("false || true || false", True),
        ("[1, 2, 3]", [1, 2, 3]),
        ("[1, 2, 3][1]", 2),
        ("[1, 2, 3][1:]", [2, 3]),
        ("[1, 2, 3][::-1]", [3, 2, 1]),
        ("1 in [1, 2, 3]", True),
        ("5 in [1, 2, 3]", False),
        ("{a: 1, b: '2' + 3}", {"a": 1, "b": "23"}),
        ("'b' in {a: 1, b: '2' + 3}", True),
        ("'c' in {a: 1, b: '2' + 3}", False),
        ("std.length('hello')", 5),
        ("std.join('-', ['a', 'b', 'c'])", "a-b-c"),
        (
            """
            {
                local x = 1,
                a: x + 2,
            }
            """,
            {"a": 3},
        ),
        (
            """
            { x: 1, y: self.x + 2 }
            """,
            {"x": 1, "y": 3},
        ),
        (
            """
            { a: 1, b: { c: $.a + 1 } }
            """,
            {"a": 1, "b": {"c": 2}},
        ),
        (
            """
            [1, { a: 123, b: { c: $.a } }]
            """,
            [1, {"a": 123, "b": {"c": 123}}],
        ),
        (
            """
            { a: 1 } + { b: 2 }
            """,
            {"a": 1, "b": 2},
        ),
        (
            """
            { a: 1 } { b: 2 }
            """,
            {"a": 1, "b": 2},
        ),
        (
            """
            { a: 1 } + { b:: 2 }
            """,
            {"a": 1},
        ),
        (
            """
            { a: 1 } + { a+: 2 }
            """,
            {"a": 3},
        ),
        (
            """
            { a: 1, b:: 2 } + { b+::: 'b' }
            """,
            {"a": 1, "b": "2b"},
        ),
        (
            """
            local a = { x+: 1 } + { x+: 1 };
            { x: 2 } + a
            """,
            {"x": 4},
        ),
        (
            """
            local a = 1, b = a + 1;
            { a: a, b: b }
            """,
            {"a": 1, "b": 2},
        ),
        (
            """
            local a = 1;
            if a % 2 == 1 then { a: 1 } else { b: 2 }
            """,
            {"a": 1},
        ),
        (
            """
            local a = 0;
            if a % 2 == 1 then { a: 1 } else { b: 2 }
            """,
            {"b": 2},
        ),
        (
            """
            (if false then {}) == null
            """,
            True,
        ),
        (
            """
            local a = 1;
            {
              [if a % 2 == 0 then 'even']: true,
              [if a % 2 == 1 then 'odd']: true,
            }
            """,
            {"odd": True},
        ),
        (
            """
            local a = error 'error message';
            {}
            """,
            {},
        ),
        (
            """
            local isEven = function(x) x % 2 == 0;
            isEven(2)
            """,
            True,
        ),
        (
            """
            local isEven = function(x) x % 2 == 0;
            isEven(x=2)
            """,
            True,
        ),
        (
            """
            local increment(x, delta=1) = x + delta;
            increment(2)
            """,
            3,
        ),
        (
            """
            local increment(x, delta=1) = x + delta;
            increment(2, 2)
            """,
            4,
        ),
        (
            """
            local increment(x, delta=1) = x + delta;
            increment(x=2, delta=2)
            """,
            4,
        ),
        (
            """
            [x for x in [1, 2, 3, 4, 5] if x % 2 == 0]
            """,
            [2, 4],
        ),
        (
            """
            [i * j for i in [1, 2] for j in [3, 4]]
            """,
            [3, 4, 6, 8],
        ),
        (
            """
            [i * j for i in [1, 2, 3] if i < 3 for j in [1, 2, 3] if i != j]
            """,
            [2, 3, 2, 6],
        ),
        (
            """
            { ['key' + i]: i for i in [1, 2, 3, 4] }
            """,
            {"key1": 1, "key2": 2, "key3": 3, "key4": 4},
        ),
        (
            """
            { ['key' + i]: i for i in [1, 2, 3, 4] if i % 2 == 1 }
            """,
            {"key1": 1, "key3": 3},
        ),
        (
            """
            {['key' + i + j]: i * j for i in [1, 2, 3] if i < 3 for j in [1, 2, 3] if i != j}
            """,
            {"key12": 2, "key13": 3, "key21": 2, "key23": 6},
        ),
        (
            """
            {a: 1} + {b: super.a}
            """,
            {"a": 1, "b": 1},
        ),
    ],
)
def test_evaluate(inputs: str, expected: Any) -> None:
    parser = Parser(Lexer(StringIO(inputs)))
    evaluator = Evaluator()
    node = parser.parse()
    assert node is not None
    result = evaluator(node).to_json()
    assert result == expected


@pytest.mark.parametrize(
    "inputs, error_msg",
    [
        (
            """
            error "error message"
            """,
            "error message",
        ),
        (
            """
            local x = { a: a };
            local a = 1;
            x
            """,
            "Unknown variable: a",
        ),
    ],
)
def test_evaluate_error(inputs: str, error_msg: str) -> None:
    parser = Parser(Lexer(StringIO(inputs)))
    evaluator = Evaluator()
    node = parser.parse()
    assert node is not None
    with pytest.raises(PysonnetRuntimeError) as exc_info:
        evaluator(node)
    assert str(exc_info.value) == error_msg


def test_ext_vars() -> None:
    ext_vars = {"a": "1"}
    inputs = "{ a: std.extVar('a') }"
    parser = Parser(Lexer(StringIO(inputs)))
    evaluator = Evaluator(ext_vars)
    node = parser.parse()
    assert node is not None
    value = evaluator(node)
    assert value.to_json() == {"a": "1"}
