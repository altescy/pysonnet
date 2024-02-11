from io import StringIO
from typing import Any

import pytest

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
    ],
)
def test_evaluate(inputs: str, expected: Any) -> None:
    parser = Parser(Lexer(StringIO(inputs)))
    evaluator = Evaluator()
    ast = parser.parse()
    assert ast is not None
    result = evaluator(ast).to_json()
    assert result == expected
