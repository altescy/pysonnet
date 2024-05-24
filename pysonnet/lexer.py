from typing import TextIO

from .token import Token, TokenType, lookup_hidden, lookup_ident

_IDENT_START = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_"
_IDENT_CONT = _IDENT_START + "0123456789"
_HEXDIGITS = "0123456789abcdefABCDEF"
_HORIZ_WS = " \t\r"
_INDENT_WS = " \t"
_ESCAPED_CHARS = {
    '"': '"',
    "'": "'",
    "\\": "\\",
    "/": "/",
    "b": "\b",
    "f": "\f",
    "n": "\n",
    "r": "\r",
    "t": "\t",
}


class Lexer:
    def __init__(self, textio: TextIO) -> None:
        self._textio = textio
        self._ch = self._read_char()

    def _peek(self, n: int = 1) -> str:
        assert n > 0
        position = self._textio.tell()
        for _ in range(n):
            ch = self._textio.read(1)
        self._textio.seek(position)
        return ch

    def _read_char(self, n: int = 1) -> str:
        for _ in range(n):
            self._ch = self._textio.read(1)
        return self._ch

    def _read_identifier(self) -> str:
        literal = self._ch
        self._read_char()
        while True:
            if self._ch == "":
                break
            if self._ch in _IDENT_CONT:
                literal += self._ch
                self._read_char()
            else:
                break
        return literal

    def _read_number(self) -> str:
        """
        ref: https://www.json.org/json-en.html
        """

        literal = ""
        if self._ch == "-":
            literal += self._ch
            self._read_char()
        if self._ch == "0":
            literal += self._ch
            self._read_char()
        else:
            if self._ch not in "123456789":
                return literal
            literal += self._ch
            self._read_char()
            while self._ch.isdigit():
                literal += self._ch
                self._read_char()
        if self._ch == ".":
            literal += self._ch
            self._read_char()
            if not self._ch.isdigit():
                return literal
            literal += self._ch
            self._read_char()
            while self._ch.isdigit():
                literal += self._ch
                self._read_char()
        if self._ch in ("e", "E"):
            next_ch = self._peek()
            if next_ch in ("+", "-"):
                next_next_ch = self._peek(2)
                if not next_next_ch.isdigit():
                    return literal
                literal += self._ch + next_ch
                self._read_char(2)
            elif next_ch.isdigit():
                literal += self._ch
                self._read_char()
            else:
                return literal
            while self._ch.isdigit():
                literal += self._ch
                self._read_char()
        return literal

    def _read_string(self, verbatim: bool = False) -> str:
        """
        ref: https://www.json.org/json-en.html
        """

        if self._ch not in ('"', "'"):
            raise ValueError(f"unexpected character: {self._ch}")

        quote = self._ch
        self._read_char()

        literal = ""
        while True:
            if self._ch == "":
                raise ValueError("unexpected end of file")
            if self._ch == quote:
                self._read_char()
                break
            elif not verbatim and self._ch == "\\":
                next_ch = self._peek()
                if next_ch in ('"', "'", "\\", "/", "b", "f", "n", "r", "t"):
                    literal += _ESCAPED_CHARS[next_ch]
                    self._read_char(2)
                elif next_ch == "u":
                    if all(self._peek(i + 2) in _HEXDIGITS for i in range(4)):
                        self._read_char(2)  # skip "\u"
                        codepoint = ""
                        for ch in range(4):
                            codepoint += self._ch
                            self._read_char()
                        literal += chr(int(codepoint, 16))
                    else:
                        raise ValueError(f"unexpected character: {self._ch}")
            else:
                literal += self._ch
                self._read_char()

        return literal

    def _read_text_block(self) -> str:
        if not (self._ch == self._peek(1) == self._peek(2) == "|"):
            raise ValueError(f"unexpected character: {self._ch}")

        # skip the "|||"
        self._read_char(3)

        # chomp whitespace at end of line
        while self._ch in _HORIZ_WS:
            self._read_char()

        if self._ch != "\n":
            raise ValueError("text block syntax requires new line after |||.")

        # skip the new line
        self._read_char()

        literal = ""

        # skip any blank lines at the beginnig of the block
        while self._ch == "\n":
            self._read_char()
            literal += "\n"

        # read the first line and determine the indentation
        indent = ""
        while self._ch in _INDENT_WS:
            indent += self._ch
            self._read_char()
        if not indent:
            raise ValueError("text block's first line must start with whitespace.")
        while self._ch != "\n":
            literal += self._ch
            self._read_char()

        literal += "\n"
        self._read_char()

        while True:
            if self._ch == "":
                raise ValueError("unexpected end of file")
            # check & consume indentation
            for ws in indent:
                if self._ch != ws:
                    if self._ch == self._peek(1) == self._peek(2) == "|":
                        self._read_char(3)
                        break
                    raise ValueError("text block not terminated with |||")
                self._read_char()
            else:
                # read the line
                while self._ch != "\n":
                    if self._ch == "":
                        raise ValueError("unexpected end of file")
                    literal += self._ch
                    self._read_char()
                literal += "\n"
                self._read_char()
                continue
            break

        return literal

    def _read_hidden(self) -> str:
        literal = ""
        for _ in range(3):
            if self._ch == ":":
                literal += self._ch
                self._read_char()
            else:
                break
        return literal

    def _skip_whitespace(self) -> None:
        while self._ch.isspace():
            self._read_char()

    def _skip_single_line_comment(self) -> None:
        while self._ch != "\n" and self._ch != "":
            self._read_char()
        self._skip_whitespace()

    def _skip_block_comment(self) -> None:
        end_found = False
        while not end_found:
            if self._ch == "":
                end_found = True
            elif self._ch == "*" and self._peek() == "/":
                end_found = True
                self._read_char()

            self._read_char()
        self._skip_whitespace()

    def next_token(self) -> Token:
        self._skip_whitespace()

        token: Token

        if self._ch == "=":
            if self._peek() == "=":
                ch = self._ch
                self._read_char()
                literal = ch + self._ch
                token = Token(TokenType.EQEQ, literal)
            else:
                token = Token(TokenType.EQUAL, self._ch)
        elif self._ch == "+":
            token = Token(TokenType.PLUS, self._ch)
        elif self._ch == "-":
            if self._peek().isdigit():
                literal = self._read_number()
                return Token(TokenType.NUMBER, literal)
            token = Token(TokenType.MINUS, self._ch)
        elif self._ch == "*":
            token = Token(TokenType.STAR, self._ch)
        elif self._ch == "/":
            if self._peek() == "/":
                self._skip_single_line_comment()
                return self.next_token()
            elif self._peek() == "*":
                self._skip_block_comment()
                return self.next_token()
            token = Token(TokenType.SLASH, self._ch)
        elif self._ch == "%":
            token = Token(TokenType.MOD, self._ch)
        elif self._ch == "<":
            if self._peek() == "=":
                ch = self._ch
                self._read_char()
                literal = ch + self._ch
                token = Token(TokenType.LE, literal)
            elif self._peek() == "<":
                ch = self._ch
                self._read_char()
                literal = ch + self._ch
                token = Token(TokenType.LSHIFT, literal)
            else:
                token = Token(TokenType.LT, self._ch)
        elif self._ch == ">":
            if self._peek() == "=":
                ch = self._ch
                self._read_char()
                literal = ch + self._ch
                token = Token(TokenType.GE, literal)
            elif self._peek() == ">":
                ch = self._ch
                self._read_char()
                literal = ch + self._ch
                token = Token(TokenType.RSHIFT, literal)
            else:
                token = Token(TokenType.GT, self._ch)
        elif self._ch == "&":
            if self._peek() == "&":
                ch = self._ch
                self._read_char()
                literal = ch + self._ch
                token = Token(TokenType.AND, literal)
            else:
                token = Token(TokenType.LAND, self._ch)
        elif self._ch == "|":
            if self._peek() == "|":
                if self._peek(2) == "|":
                    litera = self._read_text_block()
                    return Token(TokenType.STRING, litera)
                else:
                    ch = self._ch
                    self._read_char()
                    literal = ch + self._ch
                    token = Token(TokenType.OR, literal)
            else:
                token = Token(TokenType.LOR, self._ch)
        elif self._ch == "!":
            if self._peek() == "=":
                ch = self._ch
                self._read_char()
                literal = ch + self._ch
                token = Token(TokenType.NEQ, literal)
            else:
                token = Token(TokenType.NOT, self._ch)
        elif self._ch == "^":
            token = Token(TokenType.XOR, self._ch)
        elif self._ch == ".":
            token = Token(TokenType.DOT, self._ch)
        elif self._ch == ",":
            token = Token(TokenType.COMMA, self._ch)
        elif self._ch == ":":
            literal = self._read_hidden()
            token_type = lookup_hidden(literal)
            return Token(token_type, literal)
        elif self._ch == ";":
            token = Token(TokenType.SEMICOLON, self._ch)
        elif self._ch == "(":
            token = Token(TokenType.LPAREN, self._ch)
        elif self._ch == ")":
            token = Token(TokenType.RPAREN, self._ch)
        elif self._ch == "{":
            token = Token(TokenType.LBRACE, self._ch)
        elif self._ch == "}":
            token = Token(TokenType.RBRACE, self._ch)
        elif self._ch == "[":
            token = Token(TokenType.LBRACKET, self._ch)
        elif self._ch == "]":
            token = Token(TokenType.RBRACKET, self._ch)
        elif self._ch in ('"', "'"):
            literal = self._read_string()
            return Token(TokenType.STRING, literal)
        elif self._ch == "$":
            token = Token(TokenType.DOLLAR, self._ch)
        elif self._ch == "@" and self._peek() in ("'", '"'):
            self._read_char()
            literal = self._read_string(verbatim=True)
            return Token(TokenType.STRING, literal)
        elif self._ch == "#":
            self._skip_single_line_comment()
            return self.next_token()
        elif self._ch == "":
            token = Token(TokenType.EOF, "")
        elif self._ch in _IDENT_START:
            literal = self._read_identifier()
            token_type = lookup_ident(literal)
            return Token(token_type, literal)
        elif self._ch.isdigit():
            return Token(TokenType.NUMBER, self._read_number())
        else:
            token = Token(TokenType.ILLEGAL, self._ch)

        self._read_char()
        return token
