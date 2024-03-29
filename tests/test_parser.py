from io import StringIO
from typing import Any

import pytest

from pysonnet import ast
from pysonnet.lexer import Lexer
from pysonnet.parser import Parser


@pytest.mark.parametrize(
    "inputs,expected_expr",
    [
        ("null", ast.Null(value=None)),
        ("true", ast.Boolean(value=True)),
        ("false", ast.Boolean(value=False)),
        ("42", ast.Number(value=42)),
        ("3.14", ast.Number(value=3.14)),
        ('"hello"', ast.String(value="hello")),
        ("{}", ast.Object([])),
        ("[]", ast.Array[None]([])),
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
                    ast.Bind(ast.Identifier("x"), ast.Number(1)),
                    ast.Bind(ast.Identifier("y"), ast.String("2")),
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
                [ast.Bind(ast.Identifier("xs"), ast.Array([ast.Number(1), ast.Number(2), ast.Number(3)]))],
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
                    ast.Bind(
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
                                            ast.Binary(ast.Binary.Operator.INDEX, ast.Super(), ast.String("msg")),
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
                    ast.Bind(
                        ast.Identifier("x"),
                        ast.Binary(
                            ast.Binary.Operator.INDEX,
                            ast.Object([ast.ObjectField(ast.String("y"), ast.Number(123))]),
                            ast.String("y"),
                        ),
                    ),
                    ast.Bind(
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
                    ast.Bind(
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
                            ast.Apply(ast.Identifier("f"), [ast.Arg(ast.Number(1))]),
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
            ast.ObjectComprehension(
                [
                    ast.ObjectLocal(ast.Bind(ast.Identifier("p"), ast.String("v"))),
                    ast.ObjectLocal(ast.Bind(ast.Identifier("n"), ast.Number(2))),
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
                    ast.Bind(ast.Identifier("lib"), ast.Import("lib.jsonnet")),
                    ast.Bind(ast.Identifier("text"), ast.Importstr("body.txt")),
                    ast.Bind(ast.Identifier("bin"), ast.Importbin("some.bin")),
                ],
                ast.Object([]),
            ),
        ),
        (
            """
            { a: 1, b: 2 } { b: 3, c: 4 }
            """,
            ast.ApplyBrace(
                ast.Object(
                    [ast.ObjectField(ast.String("a"), ast.Number(1)), ast.ObjectField(ast.String("b"), ast.Number(2))]
                ),
                ast.Object(
                    [ast.ObjectField(ast.String("b"), ast.Number(3)), ast.ObjectField(ast.String("c"), ast.Number(4))]
                ),
            ),
        ),
        (
            """
            local secret = utils.store('team', 'name');
            {
                scheduler: util.scheduler('batch') {},
            }
            """,
            ast.LocalExpression(
                [
                    ast.Bind(
                        ast.Identifier("secret"),
                        ast.Apply(
                            ast.Binary(ast.Binary.Operator.INDEX, ast.Identifier("utils"), ast.String("store")),
                            [ast.Arg(ast.String("team")), ast.Arg(ast.String("name"))],
                        ),
                    )
                ],
                ast.Object(
                    [
                        ast.ObjectField(
                            ast.String("scheduler"),
                            ast.ApplyBrace(
                                ast.Apply(
                                    ast.Binary(
                                        ast.Binary.Operator.INDEX, ast.Identifier("util"), ast.String("scheduler")
                                    ),
                                    [ast.Arg(ast.String("batch"))],
                                ),
                                ast.Object([]),
                            ),
                        ),
                    ]
                ),
            ),
        ),
        (
            """
            local f(x) = { a: x + 1 };
            { a: f(1) { x: 2 } }
            """,
            ast.LocalExpression(
                [
                    ast.Bind(
                        ast.Identifier("f"),
                        ast.Function(
                            [ast.Param(ast.Identifier("x"))],
                            ast.Object(
                                [
                                    ast.ObjectField(
                                        ast.String("a"),
                                        ast.Binary(ast.Binary.Operator.ADD, ast.Identifier("x"), ast.Number(1)),
                                    )
                                ]
                            ),
                        ),
                    ),
                ],
                ast.Object(
                    [
                        ast.ObjectField(
                            ast.String("a"),
                            ast.ApplyBrace(
                                ast.Apply(ast.Identifier("f"), [ast.Arg(ast.Number(1))]),
                                ast.Object([ast.ObjectField(ast.String("x"), ast.Number(2))]),
                            ),
                        ),
                    ]
                ),
            ),
        ),
        (
            """
            {
                a: 1,
                b: self.a,
                c: { d: $.a }
            }
            """,
            ast.Object(
                [
                    ast.ObjectField(ast.String("a"), ast.Number(1)),
                    ast.ObjectField(
                        ast.String("b"), ast.Binary(ast.Binary.Operator.INDEX, ast.Self(), ast.String("a"))
                    ),
                    ast.ObjectField(
                        ast.String("c"),
                        ast.Object(
                            [
                                ast.ObjectField(
                                    ast.String("d"),
                                    ast.Binary(ast.Binary.Operator.INDEX, ast.Dollar(), ast.String("a")),
                                )
                            ]
                        ),
                    ),
                ],
            ),
        ),
        (
            """
            {
                x: 'foo' in { foo: 1, bar: 2 },
            }
            """,
            ast.Object(
                [
                    ast.ObjectField(
                        ast.String("x"),
                        ast.Binary(
                            ast.Binary.Operator.IN,
                            ast.String("foo"),
                            ast.Object(
                                [
                                    ast.ObjectField(ast.String("foo"), ast.Number(1)),
                                    ast.ObjectField(ast.String("bar"), ast.Number(2)),
                                ]
                            ),
                        ),
                    ),
                ],
            ),
        ),
        (
            """
            { a: 1 }  { b: 'a' in super }
            """,
            ast.ApplyBrace(
                ast.Object([ast.ObjectField(ast.String("a"), ast.Number(1))]),
                ast.Object(
                    [
                        ast.ObjectField(
                            ast.String("b"), ast.Binary(ast.Binary.Operator.IN, ast.String("a"), ast.Super())
                        )
                    ],
                ),
            ),
        ),
        (
            """
            {
                foo(a, b=1):: a + b,
            }
            """,
            ast.Object(
                [
                    ast.ObjectField(
                        ast.String("foo"),
                        ast.Function(
                            [ast.Param(ast.Identifier("a")), ast.Param(ast.Identifier("b"), ast.Number(1))],
                            ast.Binary(ast.Binary.Operator.ADD, ast.Identifier("a"), ast.Identifier("b")),
                        ),
                        visibility=ast.ObjectField.Visibility.HIDDEN,
                    ),
                ],
            ),
        ),
        (
            """
            a["x"]
            """,
            ast.Binary(ast.Binary.Operator.INDEX, ast.Identifier("a"), ast.String("x")),
        ),
        (
            """
            a.x
            """,
            ast.Binary(ast.Binary.Operator.INDEX, ast.Identifier("a"), ast.String("x")),
        ),
        (
            """
            a[::]
            """,
            ast.Identifier("a"),
        ),
        (
            """
            a[:2]
            """,
            ast.Apply(
                ast.Binary(ast.Binary.Operator.INDEX, ast.Identifier("std"), ast.String("slice")),
                [
                    ast.Arg(ast.Identifier("a")),
                    ast.Arg(ast.Null()),
                    ast.Arg(ast.Number(2)),
                    ast.Arg(ast.Null()),
                ],
            ),
        ),
        (
            """
            a[:2:]
            """,
            ast.Apply(
                ast.Binary(ast.Binary.Operator.INDEX, ast.Identifier("std"), ast.String("slice")),
                [
                    ast.Arg(ast.Identifier("a")),
                    ast.Arg(ast.Null()),
                    ast.Arg(ast.Number(2)),
                    ast.Arg(ast.Null()),
                ],
            ),
        ),
        (
            """
            a[::2]
            """,
            ast.Apply(
                ast.Binary(ast.Binary.Operator.INDEX, ast.Identifier("std"), ast.String("slice")),
                [
                    ast.Arg(ast.Identifier("a")),
                    ast.Arg(ast.Null()),
                    ast.Arg(ast.Null()),
                    ast.Arg(ast.Number(2)),
                ],
            ),
        ),
        (
            """
            a[1:10:2]
            """,
            ast.Apply(
                ast.Binary(ast.Binary.Operator.INDEX, ast.Identifier("std"), ast.String("slice")),
                [
                    ast.Arg(ast.Identifier("a")),
                    ast.Arg(ast.Number(1)),
                    ast.Arg(ast.Number(10)),
                    ast.Arg(ast.Number(2)),
                ],
            ),
        ),
        (
            """
            {
              local a() =
                local x = 1;
                { y: x },
              z: a(),
            }
            """,
            ast.Object(
                [
                    ast.ObjectLocal(
                        ast.Bind(
                            ast.Identifier("a"),
                            ast.Function(
                                [],
                                ast.LocalExpression(
                                    [ast.Bind(ast.Identifier("x"), ast.Number(1))],
                                    ast.Object([ast.ObjectField(ast.String("y"), ast.Identifier("x"))]),
                                ),
                            ),
                        ),
                    ),
                    ast.ObjectField(
                        ast.String("z"),
                        ast.Apply(ast.Identifier("a"), []),
                    ),
                ],
            ),
        ),
        (
            """
            [
              arr[i],
              for i in std.range(0, std.length(arr) - 1)
              if i != at
            ]
            """,
            ast.ArrayComprehension(
                ast.Binary(ast.Binary.Operator.INDEX, ast.Identifier("arr"), ast.Identifier("i")),
                ast.ForSpec(
                    ast.Identifier("i"),
                    ast.Apply(
                        ast.Binary(ast.Binary.Operator.INDEX, ast.Identifier("std"), ast.String("range")),
                        [
                            ast.Arg(ast.Number(0)),
                            ast.Arg(
                                ast.Binary(
                                    ast.Binary.Operator.SUB,
                                    ast.Apply(
                                        ast.Binary(
                                            ast.Binary.Operator.INDEX, ast.Identifier("std"), ast.String("length")
                                        ),
                                        [ast.Arg(ast.Identifier("arr"))],
                                    ),
                                    ast.Number(1),
                                )
                            ),
                        ],
                    ),
                ),
                [
                    ast.IfSpec(
                        ast.Binary(ast.Binary.Operator.NE, ast.Identifier("i"), ast.Identifier("at")),
                    )
                ],
            ),
        ),
        (
            """
            local foo(x) = 42; foo(error "xxx") tailstrict
            """,
            ast.LocalExpression(
                [ast.Bind(ast.Identifier("foo"), ast.Function([ast.Param(ast.Identifier("x"))], ast.Number(42)))],
                ast.Apply(
                    ast.Identifier("foo"),
                    [ast.Arg(ast.Error(ast.String("xxx")))],
                    tailstrict=True,
                ),
            ),
        ),
        (
            """
            [i * j for i in [1, 2] for j in [3, 4]]
            """,
            ast.ArrayComprehension(
                ast.Binary(ast.Binary.Operator.MUL, ast.Identifier("i"), ast.Identifier("j")),
                ast.ForSpec(ast.Identifier("i"), ast.Array([ast.Number(1), ast.Number(2)])),
                [ast.ForSpec(ast.Identifier("j"), ast.Array([ast.Number(3), ast.Number(4)]))],
            ),
        ),
        (
            """
            {[a + b]: a + b for a in ["a", "b"] for b in [1, 2]}
            """,
            ast.ObjectComprehension(
                [],
                ast.Binary[str](ast.Binary.Operator.ADD, ast.Identifier("a"), ast.Identifier("b")),
                ast.Binary[str](ast.Binary.Operator.ADD, ast.Identifier("a"), ast.Identifier("b")),
                ast.ForSpec(ast.Identifier("a"), ast.Array([ast.String("a"), ast.String("b")])),
                [ast.ForSpec(ast.Identifier("b"), ast.Array([ast.Number(1), ast.Number(2)]))],
            ),
        ),
        (
            """
            {
                [a + b]: a + b
                local n = 1
                for a in ["a", "b"]
                for b in [n, 2]
            }
            """,
            ast.ObjectComprehension(
                [ast.ObjectLocal(ast.Bind(ast.Identifier("n"), ast.Number(1)))],
                ast.Binary[str](ast.Binary.Operator.ADD, ast.Identifier("a"), ast.Identifier("b")),
                ast.Binary[str](ast.Binary.Operator.ADD, ast.Identifier("a"), ast.Identifier("b")),
                ast.ForSpec(ast.Identifier("a"), ast.Array([ast.String("a"), ast.String("b")])),
                [ast.ForSpec(ast.Identifier("b"), ast.Array([ast.Identifier("n"), ast.Number(2)]))],
            ),
        ),
    ],
)
def test_object_expression(inputs: str, expected_expr: Any) -> None:
    parser = Parser(Lexer(StringIO(inputs)))
    statement = parser.parse()
    print(parser.errors)
    assert statement == expected_expr
