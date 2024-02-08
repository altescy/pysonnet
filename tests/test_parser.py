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
            ast.Object([ast.FieldStatement(ast.String("a"), ast.Number(123))]),
        ),
        (
            "{'a': 123}",
            ast.Object([ast.FieldStatement(ast.String("a"), ast.Number(123))]),
        ),
        (
            """
            local x = 1, y = "2";
            {a: x, b: [y, 3]}
            """,
            ast.LocalExpression(
                [
                    ast.BindStatement(ast.Identifier("x"), ast.Number(1)),
                    ast.BindStatement(ast.Identifier("y"), ast.String("2")),
                ],
                ast.Object(
                    [
                        ast.FieldStatement(ast.String("a"), ast.Identifier("x")),
                        ast.FieldStatement(ast.String("b"), ast.Array([ast.Identifier("y"), ast.Number(3)])),
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
                [ast.BindStatement(ast.Identifier("xs"), ast.Array([ast.Number(1), ast.Number(2), ast.Number(3)]))],
                ast.ListComprehension(
                    ast.Identifier("x"),
                    ast.ForStatement(ast.Identifier("x"), ast.Identifier("xs")),
                    [ast.IfStatement(ast.UnaryExpression(ast.UnaryExpression.Operator.NOT, ast.Identifier("x")))],
                ),
            ),
        ),
        (
            """
            1 + 2 * 3 > 4
            """,
            ast.BinaryExpression(
                ast.BinaryExpression.Operator.GT,
                ast.BinaryExpression(
                    ast.BinaryExpression.Operator.ADD,
                    ast.Number(1),
                    ast.BinaryExpression(ast.BinaryExpression.Operator.MUL, ast.Number(2), ast.Number(3)),
                ),
                ast.Number(4),
            ),
        ),
        (
            """
            (1 + 2 / -a) * b
            """,
            ast.BinaryExpression(
                ast.BinaryExpression.Operator.MUL,
                ast.BinaryExpression(
                    ast.BinaryExpression.Operator.ADD,
                    ast.Number(1),
                    ast.BinaryExpression(
                        ast.BinaryExpression.Operator.DIV,
                        ast.Number(2),
                        ast.UnaryExpression(ast.UnaryExpression.Operator.MINUS, ast.Identifier("a")),
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
                    ast.BindStatement(
                        ast.Identifier("obj"),
                        ast.Object([ast.FieldStatement(ast.String("msg"), ast.String("Hi"))]),
                    )
                ],
                ast.Array(
                    [
                        ast.BinaryExpression(
                            ast.BinaryExpression.Operator.ADD,
                            ast.Identifier("obj"),
                            ast.Object(
                                [
                                    ast.FieldStatement(
                                        ast.String("msg"),
                                        ast.BinaryExpression(
                                            ast.BinaryExpression.Operator.ADD,
                                            ast.Super(ast.String("msg")),
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
                    ast.BindStatement(
                        ast.Identifier("x"),
                        ast.BinaryExpression(
                            ast.BinaryExpression.Operator.INDEX,
                            ast.Object([ast.FieldStatement(ast.String("y"), ast.Number(123))]),
                            ast.String("y"),
                        ),
                    ),
                    ast.BindStatement(
                        ast.Identifier("z"),
                        ast.BinaryExpression(
                            ast.BinaryExpression.Operator.INDEX,
                            ast.Array([ast.Number(1), ast.Number(2), ast.Number(3)]),
                            ast.Number(0),
                        ),
                    ),
                ],
                ast.Object(
                    [
                        ast.FieldStatement(ast.String("a"), ast.Identifier("x")),
                        ast.FieldStatement(ast.String("b"), ast.Identifier("z")),
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
                    ast.FieldStatement(ast.String("a"), ast.Array([ast.String("a")])),
                    ast.FieldStatement(
                        ast.String("b"), ast.Array([ast.String("b")]), visibility=ast.FieldStatement.Visibility.HIDDEN
                    ),
                    ast.FieldStatement(
                        ast.String("c"),
                        ast.Object([ast.FieldStatement(ast.String("c"), ast.String("c"))]),
                        visibility=ast.FieldStatement.Visibility.FORCE_VISIBLE,
                    ),
                    ast.FieldStatement(
                        ast.String("a2"),
                        ast.Array([ast.String("a2")]),
                        inherit=True,
                    ),
                    ast.FieldStatement(
                        ast.String("b2"),
                        ast.Array([ast.String("b2")]),
                        inherit=True,
                        visibility=ast.FieldStatement.Visibility.HIDDEN,
                    ),
                    ast.FieldStatement(
                        ast.String("c2"),
                        ast.Object(
                            [
                                ast.FieldStatement(ast.String("a"), ast.String("a2")),
                                ast.FieldStatement(ast.String("b"), ast.String("b2")),
                            ],
                        ),
                        inherit=True,
                        visibility=ast.FieldStatement.Visibility.FORCE_VISIBLE,
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
                    ast.BindStatement(
                        ast.Identifier("f"),
                        ast.Function(
                            [ast.ParamStatement(ast.Identifier("x"))],
                            ast.BinaryExpression(ast.BinaryExpression.Operator.ADD, ast.Identifier("x"), ast.Number(1)),
                        ),
                    )
                ],
                ast.Object(
                    [
                        ast.FieldStatement(
                            ast.String("a"),
                            ast.Call(ast.Identifier("f"), [ast.Number(1)], {}),
                        ),
                        ast.FieldStatement(
                            ast.String("b"),
                            ast.Function(
                                [ast.ParamStatement(ast.Identifier("x"))],
                                ast.BinaryExpression(
                                    ast.BinaryExpression.Operator.MUL, ast.Identifier("x"), ast.Identifier("x")
                                ),
                            ),
                        ),
                    ]
                ),
            ),
        ),
    ],
)
def test_object_expression(inputs: str, expected_expr: Any) -> None:
    parser = Parser(Lexer(StringIO(inputs)))
    statement = parser.parse()
    print(parser._errors)
    assert statement == expected_expr
