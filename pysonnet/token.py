import dataclasses
from enum import Enum


class TokenType(Enum):
    ILLEGAL = "ILLEGAL"
    EOF = "EOF"

    # Identifiers + literals
    IDENT = "IDENT"
    STRING = "STRING"
    NUMBER = "NUMBER"

    # Operators
    EQUAL = "="
    PLUS = "+"
    MINUS = "-"
    STAR = "*"
    SLASH = "/"
    MOD = "%"
    LT = "<"
    GT = ">"
    EQEQ = "=="
    NEQ = "!="
    LE = "<="
    GE = ">="
    AND = "&&"
    OR = "||"
    NOT = "!"
    LAND = "&"
    LOR = "|"
    XOR = "^"
    LSHIFT = "<<"
    RSHIFT = ">>"
    BANG = "!"
    TILDE = "~"

    # Delimiters
    DOT = "."
    COMMA = ","
    COLON = ":"
    DCOLON = "::"
    TCOLON = ":::"
    SEMICOLON = ";"
    LPAREN = "("
    RPAREN = ")"
    LBRACE = "{"
    RBRACE = "}"
    LBRACKET = "["
    RBRACKET = "]"

    # Keywords
    LOCAL = "LOCAL"
    NULL = "NULL"
    TRUE = "TRUE"
    FALSE = "FALSE"
    FUNCTION = "FUNCTION"
    SELF = "SELF"
    SUPER = "SUPER"
    IF = "IF"
    THEN = "THEN"
    ELSE = "ELSE"
    FOR = "FOR"
    IN = "IN"
    ASSERT = "ASSERT"
    ERROR = "ERROR"
    IMPORT = "IMPORT"
    IMPORTSTR = "IMPORTSTR"
    IMPORTBIN = "IMPORTBIN"
    DOLLAR = "DOLLAR"
    TAILSTRICT = "TAILSTRICT"


_KEYWORDS = {
    "local": TokenType.LOCAL,
    "null": TokenType.NULL,
    "true": TokenType.TRUE,
    "false": TokenType.FALSE,
    "function": TokenType.FUNCTION,
    "self": TokenType.SELF,
    "super": TokenType.SUPER,
    "if": TokenType.IF,
    "then": TokenType.THEN,
    "else": TokenType.ELSE,
    "for": TokenType.FOR,
    "in": TokenType.IN,
    "assert": TokenType.ASSERT,
    "error": TokenType.ERROR,
    "import": TokenType.IMPORT,
    "importstr": TokenType.IMPORTSTR,
    "importbin": TokenType.IMPORTBIN,
    "tailstrict": TokenType.TAILSTRICT,
}

_HIDDEN = {
    ":": TokenType.COLON,
    "::": TokenType.DCOLON,
    ":::": TokenType.TCOLON,
}


def lookup_ident(ident: str) -> TokenType:
    return _KEYWORDS.get(ident, TokenType.IDENT)


def lookup_hidden(hidden: str) -> TokenType:
    return _HIDDEN.get(hidden, TokenType.ILLEGAL)


@dataclasses.dataclass(frozen=True)
class Token:
    token_type: TokenType
    literal: str
