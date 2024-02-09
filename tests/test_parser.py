from io import StringIO
from typing import Any

import pytest

from pysonnet import ast
from pysonnet.lexer import Lexer
from pysonnet.parser import Parser


@pytest.mark.parametrize(
    "inputs,expected_expr",
    [
        (
            "{a: 123}",
            ast.Object([ast.ObjectField(ast.String("a"), ast.Number(123))]),
        ),
        (
            "{'a': 123}",
            ast.Object([ast.ObjectField(ast.String("a"), ast.Number(123))]),
        ),
        (
            """
            local x = 1, y = "2";
            {a: x, b: [y, 3]}
            """,
            ast.LocalExpression(
                [
                    ast.LocalExpression.Bind(ast.Identifier("x"), ast.Number(1)),
                    ast.LocalExpression.Bind(ast.Identifier("y"), ast.String("2")),
                ],
                ast.Object(
                    [
                        ast.ObjectField(ast.String("a"), ast.Identifier("x")),
                        ast.ObjectField(ast.String("b"), ast.Array([ast.Identifier("y"), ast.Number(3)])),
                    ]
                ),
            ),
        ),
        (
            """
            local xs = [1, 2, 3];
            [x for x in xs if !x]
            """,
            ast.LocalExpression(
                [
                    ast.LocalExpression.Bind(
                        ast.Identifier("xs"), ast.Array([ast.Number(1), ast.Number(2), ast.Number(3)])
                    )
                ],
                ast.ArrayComprehension(
                    ast.Identifier("x"),
                    ast.ForSpec(ast.Identifier("x"), ast.Identifier("xs")),
                    [ast.IfSpec(ast.Unary(ast.Unary.Operator.NOT, ast.Identifier("x")))],
                ),
            ),
        ),
        (
            """
            1 + 2 * 3 > 4
            """,
            ast.Binary(
                ast.Binary.Operator.GT,
                ast.Binary(
                    ast.Binary.Operator.ADD,
                    ast.Number(1),
                    ast.Binary(ast.Binary.Operator.MUL, ast.Number(2), ast.Number(3)),
                ),
                ast.Number(4),
            ),
        ),
        (
            """
            (1 + 2 / -a) * b
            """,
            ast.Binary(
                ast.Binary.Operator.MUL,
                ast.Binary(
                    ast.Binary.Operator.ADD,
                    ast.Number(1),
                    ast.Binary(
                        ast.Binary.Operator.DIV,
                        ast.Number(2),
                        ast.Unary(ast.Unary.Operator.MINUS, ast.Identifier("a")),
                    ),
                ),
                ast.Identifier("b"),
            ),
        ),
        (
            """
            local obj = { msg: 'Hi' };
            [ obj + { msg: super.msg + '!' } ]
            """,
            ast.LocalExpression(
                [
                    ast.LocalExpression.Bind(
                        ast.Identifier("obj"),
                        ast.Object([ast.ObjectField(ast.String("msg"), ast.String("Hi"))]),
                    )
                ],
                ast.Array(
                    [
                        ast.Binary[dict](
                            ast.Binary.Operator.ADD,
                            ast.Identifier("obj"),
                            ast.Object(
                                [
                                    ast.ObjectField(
                                        ast.String("msg"),
                                        ast.Binary(
                                            ast.Binary.Operator.ADD,
                                            ast.SuperIndex(ast.String("msg")),
                                            ast.String("!"),
                                        ),
                                    )
                                ]
                            ),
                        )
                    ]
                ),
            ),
        ),
        (
            """
            local x = {y: 123}.y, z = [1, 2, 3][0];
            {a: x, b: z}
            """,
            ast.LocalExpression(
                [
                    ast.LocalExpression.Bind(
                        ast.Identifier("x"),
                        ast.Binary(
                            ast.Binary.Operator.INDEX,
                            ast.Object([ast.ObjectField(ast.String("y"), ast.Number(123))]),
                            ast.String("y"),
                        ),
                    ),
                    ast.LocalExpression.Bind(
                        ast.Identifier("z"),
                        ast.Binary(
                            ast.Binary.Operator.INDEX,
                            ast.Array([ast.Number(1), ast.Number(2), ast.Number(3)]),
                            ast.Number(0),
                        ),
                    ),
                ],
                ast.Object(
                    [
                        ast.ObjectField(ast.String("a"), ast.Identifier("x")),
                        ast.ObjectField(ast.String("b"), ast.Identifier("z")),
                    ]
                ),
            ),
        ),
        (
            """
            {
              a: ['a'],
              b:: ['b'],
              c::: { c: 'c' },
              a2+: ['a2'],
              b2+:: ['b2'],
              c2+::: { a: 'a2', b: 'b2' },
            }
            """,
            ast.Object(
                [
                    ast.ObjectField(ast.String("a"), ast.Array([ast.String("a")])),
                    ast.ObjectField(
                        ast.String("b"), ast.Array([ast.String("b")]), visibility=ast.ObjectField.Visibility.HIDDEN
                    ),
                    ast.ObjectField(
                        ast.String("c"),
                        ast.Object([ast.ObjectField(ast.String("c"), ast.String("c"))]),
                        visibility=ast.ObjectField.Visibility.FORCE_VISIBLE,
                    ),
                    ast.ObjectField(
                        ast.String("a2"),
                        ast.Array([ast.String("a2")]),
                        inherit=True,
                    ),
                    ast.ObjectField(
                        ast.String("b2"),
                        ast.Array([ast.String("b2")]),
                        inherit=True,
                        visibility=ast.ObjectField.Visibility.HIDDEN,
                    ),
                    ast.ObjectField(
                        ast.String("c2"),
                        ast.Object(
                            [
                                ast.ObjectField(ast.String("a"), ast.String("a2")),
                                ast.ObjectField(ast.String("b"), ast.String("b2")),
                            ],
                        ),
                        inherit=True,
                        visibility=ast.ObjectField.Visibility.FORCE_VISIBLE,
                    ),
                ]
            ),
        ),
        (
            """
            local f = function(x) x + 1;
            { a: f(1), b(x): x * x }
            """,
            ast.LocalExpression(
                [
                    ast.LocalExpression.Bind(
                        ast.Identifier("f"),
                        ast.Function(
                            [ast.Param(ast.Identifier("x"))],
                            ast.Binary(ast.Binary.Operator.ADD, ast.Identifier("x"), ast.Number(1)),
                        ),
                    )
                ],
                ast.Object(
                    [
                        ast.ObjectField(
                            ast.String("a"),
                            ast.Apply(ast.Identifier("f"), [ast.Number(1)], {}),
                        ),
                        ast.ObjectField(
                            ast.String("b"),
                            ast.Function(
                                [ast.Param(ast.Identifier("x"))],
                                ast.Binary(ast.Binary.Operator.MUL, ast.Identifier("x"), ast.Identifier("x")),
                            ),
                        ),
                    ]
                ),
            ),
        ),
        (
            """
            error 'fail'
            """,
            ast.Error(ast.String("fail")),
        ),
        (
            """
            assert x % 2 == 0 : 'x must be even';
            {}
            """,
            ast.AssertExpression(
                ast.Assert(
                    ast.Binary(
                        ast.Binary.Operator.EQ,
                        ast.Binary(ast.Binary.Operator.MOD, ast.Identifier("x"), ast.Number(2)),
                        ast.Number(0),
                    ),
                    ast.String("x must be even"),
                ),
                ast.Object([]),
            ),
        ),
        (
            """
            {
                assert flag,
                x: 1,
            }
            """,
            ast.Object(
                [
                    ast.Assert(ast.Identifier("flag")),
                    ast.ObjectField(ast.String("x"), ast.Number(1)),
                ],
            ),
        ),
        (
            """
            {
                a: if x % 2 == 0 then 'even' else 'odd',
                [if flag then 'b']: 'optional',
            }
            """,
            ast.Object(
                [
                    ast.ObjectField(
                        ast.String("a"),
                        ast.IfExpression(
                            ast.Binary(
                                ast.Binary.Operator.EQ,
                                ast.Binary(ast.Binary.Operator.MOD, ast.Identifier("x"), ast.Number(2)),
                                ast.Number(0),
                            ),
                            ast.String("even"),
                            ast.String("odd"),
                        ),
                    ),
                    ast.ObjectField(
                        ast.IfExpression(
                            ast.Identifier("flag"),
                            ast.String("b"),
                        ),
                        ast.String("optional"),
                    ),
                ],
            ),
        ),
        (
            """
            {
              local p = 'v',
              ['k' + i]: p + (i + n),
              local n = 2
              for i in values
              if i % 2 == 0
            }
            """,
            ast.ObjectCompreshension(
                [
                    ast.ObjectLocal(ast.Identifier("p"), ast.String("v")),
                    ast.ObjectLocal(ast.Identifier("n"), ast.Number(2)),
                ],
                ast.Binary[str](ast.Binary.Operator.ADD, ast.String("k"), ast.Identifier("i")),
                ast.Binary[str](
                    ast.Binary.Operator.ADD,
                    ast.Identifier("p"),
                    ast.Binary(ast.Binary.Operator.ADD, ast.Identifier("i"), ast.Identifier("n")),
                ),
                ast.ForSpec(
                    ast.Identifier("i"),
                    ast.Identifier("values"),
                ),
                [
                    ast.IfSpec(
                        ast.Binary(
                            ast.Binary.Operator.EQ,
                            ast.Binary(ast.Binary.Operator.MOD, ast.Identifier("i"), ast.Number(2)),
                            ast.Number(0),
                        ),
                    ),
                ],
            ),
        ),
        (
            """
            local
                lib = import "lib.jsonnet"
                , text = importstr "body.txt"
                , bin = importbin "some.bin"
            ;
            {}
            """,
            ast.LocalExpression(
                [
                    ast.LocalExpression.Bind(ast.Identifier("lib"), ast.Import("lib.jsonnet")),
                    ast.LocalExpression.Bind(ast.Identifier("text"), ast.Importstr("body.txt")),
                    ast.LocalExpression.Bind(ast.Identifier("bin"), ast.Importbin("some.bin")),
                ],
                ast.Object([]),
            ),
        ),
    ],
)
def test_object_expression(inputs: str, expected_expr: Any) -> None:
    parser = Parser(Lexer(StringIO(inputs)))
    statement = parser.parse()
    print(parser._errors)
    assert statement == expected_expr
