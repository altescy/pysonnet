from io import StringIO
from typing import List

import pytest

from pysonnet.lexer import Lexer
from pysonnet.token import Token, TokenType

_EXAPLES = [
    (
        "[0, 123, 4.56, -7.8, 9e1, 2.3e-4, 0.5e+6]",
        [
            Token(TokenType.LBRACKET, "["),
            Token(TokenType.NUMBER, "0"),
            Token(TokenType.COMMA, ","),
            Token(TokenType.NUMBER, "123"),
            Token(TokenType.COMMA, ","),
            Token(TokenType.NUMBER, "4.56"),
            Token(TokenType.COMMA, ","),
            Token(TokenType.NUMBER, "-7.8"),
            Token(TokenType.COMMA, ","),
            Token(TokenType.NUMBER, "9e1"),
            Token(TokenType.COMMA, ","),
            Token(TokenType.NUMBER, "2.3e-4"),
            Token(TokenType.COMMA, ","),
            Token(TokenType.NUMBER, "0.5e+6"),
            Token(TokenType.RBRACKET, "]"),
            Token(TokenType.EOF, ""),
        ],
    ),
    (
        r"""
        {
          dq: "double quoted",
          sq: 'single quoted',
          dqb: @"c:\path\to\u0066.txt",
          sqb: @'c:\path\to\u0066.txt',
          escape: "\" \' \\ \b \f \n \r \t \u1234",
          block: |||
            this is a text block
            \ \n \t \u0066
          |||,
        }
        """,
        [
            Token(TokenType.LBRACE, "{"),
            Token(TokenType.IDENT, "dq"),
            Token(TokenType.COLON, ":"),
            Token(TokenType.STRING, "double quoted"),
            Token(TokenType.COMMA, ","),
            Token(TokenType.IDENT, "sq"),
            Token(TokenType.COLON, ":"),
            Token(TokenType.STRING, "single quoted"),
            Token(TokenType.COMMA, ","),
            Token(TokenType.IDENT, "dqb"),
            Token(TokenType.COLON, ":"),
            Token(TokenType.STRING, r"c:\path\to\u0066.txt"),
            Token(TokenType.COMMA, ","),
            Token(TokenType.IDENT, "sqb"),
            Token(TokenType.COLON, ":"),
            Token(TokenType.STRING, r"c:\path\to\u0066.txt"),
            Token(TokenType.COMMA, ","),
            Token(TokenType.IDENT, "escape"),
            Token(TokenType.COLON, ":"),
            Token(TokenType.STRING, r"\" \' \\ \b \f \n \r \t \u1234"),
            Token(TokenType.COMMA, ","),
            Token(TokenType.IDENT, "block"),
            Token(TokenType.COLON, ":"),
            Token(TokenType.STRING, "this is a text block\n\\ \\n \\t \\u0066\n"),
            Token(TokenType.COMMA, ","),
            Token(TokenType.RBRACE, "}"),
        ],
    ),
    (
        """
        // let's do some math

        local foo = 5.2;
        local bar = 10;

        # this is another comment

        {
            a: foo + bar,
            b:: foo - bar,
            "c"::: foo * bar,
        }

        /*
        this is a block comment
        */
        """,
        [
            Token(TokenType.LOCAL, "local"),
            Token(TokenType.IDENT, "foo"),
            Token(TokenType.EQUAL, "="),
            Token(TokenType.NUMBER, "5.2"),
            Token(TokenType.SEMICOLON, ";"),
            Token(TokenType.LOCAL, "local"),
            Token(TokenType.IDENT, "bar"),
            Token(TokenType.EQUAL, "="),
            Token(TokenType.NUMBER, "10"),
            Token(TokenType.SEMICOLON, ";"),
            Token(TokenType.LBRACE, "{"),
            Token(TokenType.IDENT, "a"),
            Token(TokenType.COLON, ":"),
            Token(TokenType.IDENT, "foo"),
            Token(TokenType.PLUS, "+"),
            Token(TokenType.IDENT, "bar"),
            Token(TokenType.COMMA, ","),
            Token(TokenType.IDENT, "b"),
            Token(TokenType.DCOLON, "::"),
            Token(TokenType.IDENT, "foo"),
            Token(TokenType.MINUS, "-"),
            Token(TokenType.IDENT, "bar"),
            Token(TokenType.COMMA, ","),
            Token(TokenType.STRING, "c"),
            Token(TokenType.TCOLON, ":::"),
            Token(TokenType.IDENT, "foo"),
            Token(TokenType.STAR, "*"),
            Token(TokenType.IDENT, "bar"),
            Token(TokenType.COMMA, ","),
            Token(TokenType.RBRACE, "}"),
            Token(TokenType.EOF, ""),
        ],
    ),
    (
        """
        local map(func, arr) =
            if std.length(arr) == 0 then
                []
            else
                [func(arr[0])] + map(func, arr[1:])
            ;
        map(function(i) i * 2, [1, 2, 3])
        """,
        [
            Token(TokenType.LOCAL, "local"),
            Token(TokenType.IDENT, "map"),
            Token(TokenType.LPAREN, "("),
            Token(TokenType.IDENT, "func"),
            Token(TokenType.COMMA, ","),
            Token(TokenType.IDENT, "arr"),
            Token(TokenType.RPAREN, ")"),
            Token(TokenType.EQUAL, "="),
            Token(TokenType.IF, "if"),
            Token(TokenType.IDENT, "std"),
            Token(TokenType.DOT, "."),
            Token(TokenType.IDENT, "length"),
            Token(TokenType.LPAREN, "("),
            Token(TokenType.IDENT, "arr"),
            Token(TokenType.RPAREN, ")"),
            Token(TokenType.EQEQ, "=="),
            Token(TokenType.NUMBER, "0"),
            Token(TokenType.THEN, "then"),
            Token(TokenType.LBRACKET, "["),
            Token(TokenType.RBRACKET, "]"),
            Token(TokenType.ELSE, "else"),
            Token(TokenType.LBRACKET, "["),
            Token(TokenType.IDENT, "func"),
            Token(TokenType.LPAREN, "("),
            Token(TokenType.IDENT, "arr"),
            Token(TokenType.LBRACKET, "["),
            Token(TokenType.NUMBER, "0"),
            Token(TokenType.RBRACKET, "]"),
            Token(TokenType.RPAREN, ")"),
            Token(TokenType.RBRACKET, "]"),
            Token(TokenType.PLUS, "+"),
            Token(TokenType.IDENT, "map"),
            Token(TokenType.LPAREN, "("),
            Token(TokenType.IDENT, "func"),
            Token(TokenType.COMMA, ","),
            Token(TokenType.IDENT, "arr"),
            Token(TokenType.LBRACKET, "["),
            Token(TokenType.NUMBER, "1"),
            Token(TokenType.COLON, ":"),
            Token(TokenType.RBRACKET, "]"),
            Token(TokenType.RPAREN, ")"),
            Token(TokenType.SEMICOLON, ";"),
            Token(TokenType.IDENT, "map"),
            Token(TokenType.LPAREN, "("),
            Token(TokenType.FUNCTION, "function"),
            Token(TokenType.LPAREN, "("),
            Token(TokenType.IDENT, "i"),
            Token(TokenType.RPAREN, ")"),
            Token(TokenType.IDENT, "i"),
            Token(TokenType.STAR, "*"),
            Token(TokenType.NUMBER, "2"),
            Token(TokenType.COMMA, ","),
            Token(TokenType.LBRACKET, "["),
            Token(TokenType.NUMBER, "1"),
            Token(TokenType.COMMA, ","),
            Token(TokenType.NUMBER, "2"),
            Token(TokenType.COMMA, ","),
            Token(TokenType.NUMBER, "3"),
            Token(TokenType.RBRACKET, "]"),
            Token(TokenType.RPAREN, ")"),
        ],
    ),
]


@pytest.mark.parametrize("inputs,expected_tokens", _EXAPLES)
def test_next_token(inputs: str, expected_tokens: List[Token]) -> None:
    lexer = Lexer(StringIO(inputs))
    for expected_token in expected_tokens:
        token = lexer.next_token()
        assert token == expected_token
