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
            ast.Object([ast.MemberStatement(ast.FieldStatement(ast.String("a"), ast.Number(123)))]),
        ),
        (
            "{'a': 123}",
            ast.Object([ast.MemberStatement(ast.FieldStatement(ast.String("a"), ast.Number(123)))]),
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
                        ast.MemberStatement(ast.FieldStatement(ast.String("a"), ast.Identifier("x"))),
                        ast.MemberStatement(
                            ast.FieldStatement(ast.String("b"), ast.Array([ast.Identifier("y"), ast.Number(3)]))
                        ),
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
    ],
)
def test_object_expression(inputs: str, expected_expr: Any) -> None:
    parser = Parser(Lexer(StringIO(inputs)))
    statement = parser.parse()
    assert statement == expected_expr
