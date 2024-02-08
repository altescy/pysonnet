import enum
from typing import Any, Callable, Dict, List, Optional, Union

from pysonnet import ast
from pysonnet.lexer import Lexer
from pysonnet.token import TokenType


class Precedence(enum.IntEnum):
    """
    ref: https://jsonnet.org/ref/spec.html#associativity_precedence
    """

    LOWEST = enum.auto()
    OR = enum.auto()
    AND = enum.auto()
    LOR = enum.auto()
    XOR = enum.auto()
    LAND = enum.auto()
    EQUALS = enum.auto()
    LESSGREATER = enum.auto()
    BITSHIFT = enum.auto()
    SUM = enum.auto()
    PRODUCT = enum.auto()
    UNARY = enum.auto()
    INDEX = enum.auto()


_BINARY_PRECEDENCE = {
    TokenType.OR: Precedence.OR,
    TokenType.AND: Precedence.AND,
    TokenType.LOR: Precedence.LOR,
    TokenType.XOR: Precedence.XOR,
    TokenType.LAND: Precedence.LAND,
    TokenType.EQEQ: Precedence.EQUALS,
    TokenType.NEQ: Precedence.EQUALS,
    TokenType.LT: Precedence.LESSGREATER,
    TokenType.GT: Precedence.LESSGREATER,
    TokenType.LE: Precedence.LESSGREATER,
    TokenType.GE: Precedence.LESSGREATER,
    TokenType.IN: Precedence.LESSGREATER,
    TokenType.LSHIFT: Precedence.BITSHIFT,
    TokenType.RSHIFT: Precedence.BITSHIFT,
    TokenType.PLUS: Precedence.SUM,
    TokenType.MINUS: Precedence.SUM,
    TokenType.STAR: Precedence.PRODUCT,
    TokenType.SLASH: Precedence.PRODUCT,
    TokenType.MOD: Precedence.PRODUCT,
    TokenType.LBRACKET: Precedence.INDEX,
    TokenType.LPAREN: Precedence.INDEX,
    TokenType.DOT: Precedence.INDEX,
}


class Parser:
    def __init__(self, lexer: Lexer) -> None:
        self._lexer = lexer
        self._cur_token = self._lexer.next_token()
        self._peek_token = self._lexer.next_token()

        self._errors: List[str] = []

        self._prefix_parsers: Dict[TokenType, Callable[[], Optional[ast.Expression]]] = {
            TokenType.NULL: self._parse_null,
            TokenType.TRUE: self._parse_boolean,
            TokenType.FALSE: self._parse_boolean,
            TokenType.NUMBER: self._parse_number,
            TokenType.STRING: self._parse_string,
            TokenType.IDENT: self._parse_identifier,
            TokenType.LPAREN: self._parse_grouped_expression,
            TokenType.LBRACE: self._parse_object,
            TokenType.LBRACKET: self._parse_array,
            TokenType.LOCAL: self._parse_local_expression,
            TokenType.PLUS: self._parse_unary_expression,
            TokenType.MINUS: self._parse_unary_expression,
            TokenType.BANG: self._parse_unary_expression,
            TokenType.TILDE: self._parse_unary_expression,
            TokenType.SUPER: self._parse_super,
            TokenType.FUNCTION: self._parse_function,
        }
        self._infix_parsers: Dict[TokenType, Callable[[ast.Expression], Optional[ast.Expression]]] = {
            TokenType.PLUS: self._parse_binary_expression,
            TokenType.MINUS: self._parse_binary_expression,
            TokenType.STAR: self._parse_binary_expression,
            TokenType.SLASH: self._parse_binary_expression,
            TokenType.MOD: self._parse_binary_expression,
            TokenType.LAND: self._parse_binary_expression,
            TokenType.LOR: self._parse_binary_expression,
            TokenType.XOR: self._parse_binary_expression,
            TokenType.LSHIFT: self._parse_binary_expression,
            TokenType.RSHIFT: self._parse_binary_expression,
            TokenType.AND: self._parse_binary_expression,
            TokenType.OR: self._parse_binary_expression,
            TokenType.EQEQ: self._parse_binary_expression,
            TokenType.NEQ: self._parse_binary_expression,
            TokenType.LT: self._parse_binary_expression,
            TokenType.GT: self._parse_binary_expression,
            TokenType.LE: self._parse_binary_expression,
            TokenType.GE: self._parse_binary_expression,
            TokenType.DOT: self._parse_binary_expression,
            TokenType.LPAREN: self._parse_call_expression,
            TokenType.LBRACKET: self._parse_binary_expression,
        }

    def _peek_error(self, token_type: TokenType) -> None:
        msg = f"expected next token to be {token_type}, got {self._peek_token.token_type} instead"
        self._errors.append(msg)

    def _current_token_type_is(self, token_type: TokenType) -> bool:
        return self._cur_token.token_type == token_type

    def _peek_token_type_is(self, token_type: TokenType) -> bool:
        return self._peek_token.token_type == token_type

    def _expect_peek_type(self, token_type: TokenType) -> bool:
        if self._peek_token_type_is(token_type):
            self.next_token()
            return True
        self._peek_error(token_type)
        return False

    def _current_binary_precedence(self) -> Precedence:
        return _BINARY_PRECEDENCE.get(self._cur_token.token_type, Precedence.LOWEST)

    def _peek_binary_precedence(self) -> Precedence:
        return _BINARY_PRECEDENCE.get(self._peek_token.token_type, Precedence.LOWEST)

    def _parse_null(self) -> ast.Null:
        return ast.Null()

    def _parse_boolean(self) -> ast.Boolean:
        return ast.Boolean(self._cur_token.token_type == TokenType.TRUE)

    def _parse_number(self) -> ast.Number:
        if "." in self._cur_token.literal or "e" in self._cur_token.literal.lower():
            value = float(self._cur_token.literal)
        else:
            value = int(self._cur_token.literal)
        return ast.Number(value=value)

    def _parse_string(self) -> ast.String:
        return ast.String(self._cur_token.literal)

    def _parse_identifier(self) -> ast.Identifier:
        return ast.Identifier(self._cur_token.literal)

    def _parse_grouped_expression(self) -> Optional[ast.Expression]:
        self.next_token()  # consume the '(' token
        expression = self._parse_expression(Precedence.LOWEST)
        if not self._expect_peek_type(TokenType.RPAREN):
            return None
        return expression

    def _parse_super(self) -> Optional[ast.Super]:
        self.next_token()  # consume the 'super' token
        key: ast.Expression[str]
        if self._current_token_type_is(TokenType.DOT):
            if not self._expect_peek_type(TokenType.IDENT):
                return None
            key = ast.String(self._cur_token.literal)
        elif self._current_token_type_is(TokenType.LBRACKET):
            self.next_token()  # consume the '[' token
            expression = self._parse_expression(Precedence.LOWEST)
            if expression is None:
                return None
            key = expression
            if not self._expect_peek_type(TokenType.RBRACKET):
                return None
        return ast.Super(key)

    def _parse_param_statement(self) -> Optional[ast.ParamStatement]:
        ident = self._parse_identifier()
        default: Optional[ast.Expression] = None
        if self._peek_token_type_is(TokenType.EQUAL):
            self.next_token()
            default = self._parse_expression(Precedence.LOWEST)
            if default is None:
                return None
        return ast.ParamStatement(ident, default)

    def _parse_params_statement(self) -> Optional[List[ast.ParamStatement]]:
        param = self._parse_param_statement()
        if param is None:
            return None
        params = [param]
        while self._peek_token_type_is(TokenType.COMMA):
            self.next_token()  # consume the ',' token
            if not self._peek_token_type_is(TokenType.IDENT):
                break
            self.next_token()
            param = self._parse_param_statement()
            if param is None:
                return None
            params.append(param)
        return params

    def _parse_function(self) -> Optional[ast.Function]:
        if not self._expect_peek_type(TokenType.LPAREN):
            return None
        self.next_token()
        params = self._parse_params_statement()
        if params is None:
            return None
        if not self._expect_peek_type(TokenType.RPAREN):
            return None
        self.next_token()
        expression = self._parse_expression(Precedence.LOWEST)
        if expression is None:
            return None
        return ast.Function(params, expression)

    def _parse_call_expression(self, function: ast.Expression) -> Optional[ast.Call]:
        args: List[ast.Expression] = []
        kwargs: Dict[ast.Identifier, ast.Expression] = {}
        print("parse call", self._peek_token)
        while not self._peek_token_type_is(TokenType.RPAREN):
            if kwargs:
                if not self._expect_peek_type(TokenType.IDENT):
                    return None
                ident = self._parse_identifier()
                if not self._expect_peek_type(TokenType.EQUAL):
                    return None
                self.next_token()
                expression = self._parse_expression(Precedence.LOWEST)
                if expression is None:
                    return None
                kwargs[ident] = expression
            else:
                self.next_token()
                print("parse args", self._cur_token)
                if self._current_token_type_is(TokenType.IDENT) and self._peek_token_type_is(TokenType.EQUAL):
                    ident = self._parse_identifier()
                    if not self._expect_peek_type(TokenType.EQUAL):
                        return None
                    self.next_token()
                    expression = self._parse_expression(Precedence.LOWEST)
                    if expression is None:
                        return None
                    kwargs[ident] = expression
                else:
                    expression = self._parse_expression(Precedence.LOWEST)
                    if expression is None:
                        return None
                    args.append(expression)
            if self._peek_token_type_is(TokenType.COMMA):
                self.next_token()
        if not self._expect_peek_type(TokenType.RPAREN):
            return None
        return ast.Call(function, args, kwargs)

    def _parse_unary_expression(self) -> Optional[ast.UnaryExpression]:
        operator: ast.UnaryExpression.Operator
        if self._current_token_type_is(TokenType.PLUS):
            operator = ast.UnaryExpression.Operator.PLUS
        elif self._current_token_type_is(TokenType.MINUS):
            operator = ast.UnaryExpression.Operator.MINUS
        elif self._current_token_type_is(TokenType.BANG):
            operator = ast.UnaryExpression.Operator.NOT
        elif self._current_token_type_is(TokenType.TILDE):
            operator = ast.UnaryExpression.Operator.BITWISE_NOT
        else:
            self._errors.append(f"unknown unary operator: {self._cur_token.literal}")
            return None
        self.next_token()
        expression = self._parse_expression(Precedence.UNARY)
        if not expression:
            return None
        return ast.UnaryExpression(operator, expression)

    def _parse_binary_expression(self, left: ast.Expression) -> Optional[ast.BinaryExpression]:
        operator: ast.BinaryExpression.Operator
        if self._current_token_type_is(TokenType.PLUS):
            operator = ast.BinaryExpression.Operator.ADD
        elif self._current_token_type_is(TokenType.MINUS):
            operator = ast.BinaryExpression.Operator.SUB
        elif self._current_token_type_is(TokenType.STAR):
            operator = ast.BinaryExpression.Operator.MUL
        elif self._current_token_type_is(TokenType.SLASH):
            operator = ast.BinaryExpression.Operator.DIV
        elif self._current_token_type_is(TokenType.MOD):
            operator = ast.BinaryExpression.Operator.MOD
        elif self._current_token_type_is(TokenType.LAND):
            operator = ast.BinaryExpression.Operator.BITWISE_AND
        elif self._current_token_type_is(TokenType.LOR):
            operator = ast.BinaryExpression.Operator.BITWISE_OR
        elif self._current_token_type_is(TokenType.XOR):
            operator = ast.BinaryExpression.Operator.BITWISE_XOR
        elif self._current_token_type_is(TokenType.LSHIFT):
            operator = ast.BinaryExpression.Operator.LSHIFT
        elif self._current_token_type_is(TokenType.RSHIFT):
            operator = ast.BinaryExpression.Operator.RSHIFT
        elif self._current_token_type_is(TokenType.AND):
            operator = ast.BinaryExpression.Operator.AND
        elif self._current_token_type_is(TokenType.OR):
            operator = ast.BinaryExpression.Operator.OR
        elif self._current_token_type_is(TokenType.EQEQ):
            operator = ast.BinaryExpression.Operator.EQ
        elif self._current_token_type_is(TokenType.NEQ):
            operator = ast.BinaryExpression.Operator.NE
        elif self._current_token_type_is(TokenType.LT):
            operator = ast.BinaryExpression.Operator.LT
        elif self._current_token_type_is(TokenType.GT):
            operator = ast.BinaryExpression.Operator.GT
        elif self._current_token_type_is(TokenType.LE):
            operator = ast.BinaryExpression.Operator.LE
        elif self._current_token_type_is(TokenType.GE):
            operator = ast.BinaryExpression.Operator.GE
        elif self._current_token_type_is(TokenType.DOT):
            if not self._expect_peek_type(TokenType.IDENT):
                return None
            return ast.BinaryExpression(
                ast.BinaryExpression.Operator.INDEX,
                left,
                ast.String(self._cur_token.literal),
            )
        elif self._current_token_type_is(TokenType.LBRACKET):
            self.next_token()
            index = self._parse_expression(Precedence.LOWEST)
            if index is None:
                return None
            if not self._expect_peek_type(TokenType.RBRACKET):
                return None
            return ast.BinaryExpression(
                ast.BinaryExpression.Operator.INDEX,
                left,
                index,
            )
        else:
            self._errors.append(f"unknown binary operator: {self._cur_token.literal}")
            return None
        precedence = self._current_binary_precedence()
        self.next_token()
        right = self._parse_expression(precedence)
        if not right:
            return None
        return ast.BinaryExpression(operator, left, right)

    def _parse_expression(self, precedence: Precedence) -> Optional[ast.Expression]:
        prefix = self._prefix_parsers.get(self._cur_token.token_type)
        if prefix is None:
            self._errors.append(f"no prefix parse function for {self._cur_token.token_type}")
            return None

        left = prefix()
        if left is None:
            return None

        while precedence < self._peek_binary_precedence():
            assert left is not None
            infix = self._infix_parsers.get(self._peek_token.token_type)
            if infix is None:
                return left
            self.next_token()
            left = infix(left)
            if left is None:
                return None

        return left

    def _parse_local_expression(self) -> Optional[ast.LocalExpression]:
        self.next_token()  # consume the 'local' token
        binds: List[ast.BindStatement] = []

        bind = self._parse_bind_statement()
        if bind is None:
            return None
        binds.append(bind)

        while self._peek_token_type_is(TokenType.COMMA):
            self.next_token()
            if not self._expect_peek_type(TokenType.IDENT):
                return None
            bind = self._parse_bind_statement()
            if bind is None:
                return None
            binds.append(bind)

        if not self._expect_peek_type(TokenType.SEMICOLON):
            return None

        self.next_token()

        expression = self._parse_expression(Precedence.LOWEST)
        if expression is None:
            return None

        return ast.LocalExpression(binds, expression)

    def _parse_bind_statement(self) -> Optional[ast.BindStatement]:
        name = ast.Identifier[Any](self._cur_token.literal)
        if self._peek_token_type_is(TokenType.LPAREN):
            raise NotImplementedError
        if not self._expect_peek_type(TokenType.EQUAL):
            self._errors.append("expected '=' after identifier")
            return None
        self.next_token()  # consume the '=' token
        expression = self._parse_expression(Precedence.LOWEST)
        if expression is None:
            return None
        return ast.BindStatement(name, expression)

    def _parse_objlocal_statement(self) -> Optional[ast.ObjlocalStatement]:
        if not self._expect_peek_type(TokenType.IDENT):
            return None
        bind = self._parse_bind_statement()
        if bind is None:
            return None
        if not self._expect_peek_type(TokenType.SEMICOLON):
            return None
        return ast.ObjlocalStatement(bind)

    def _parse_field_statement(self) -> Optional[ast.FieldStatement]:
        key: ast.Expression[str]
        if self._current_token_type_is(TokenType.IDENT):
            key = ast.String(self._cur_token.literal)
        elif self._current_token_type_is(TokenType.STRING):
            key = ast.String(self._cur_token.literal)
        elif self._current_token_type_is(TokenType.LBRACKET):
            self.next_token()  # consume the '[' token
            expression = self._parse_expression(Precedence.LOWEST)
            if expression is None:
                return None
            if not self._expect_peek_type(TokenType.RBRACKET):
                return None
            key = expression
        else:
            self._errors.append("invalid key")
            return None

        params: Optional[List[ast.ParamStatement]] = None
        if self._peek_token_type_is(TokenType.LPAREN):
            self.next_token()
            self.next_token()
            params = self._parse_params_statement()
            if params is None:
                return None
            if not self._expect_peek_type(TokenType.RPAREN):
                return None

        inherit = False
        if self._peek_token_type_is(TokenType.PLUS):
            inherit = True
            self.next_token()

        visibility: ast.FieldStatement.Visibility
        if self._peek_token_type_is(TokenType.COLON):
            visibility = ast.FieldStatement.Visibility.VISIBLE
        elif self._peek_token_type_is(TokenType.DCOLON):
            visibility = ast.FieldStatement.Visibility.HIDDEN
        elif self._peek_token_type_is(TokenType.TCOLON):
            visibility = ast.FieldStatement.Visibility.FORCE_VISIBLE
        else:
            self._errors.append("expected ':' or '::' or ':::', got {self._peek_token.token_type} instead")
            return None

        self.next_token()  # consume the separator token
        self.next_token()

        expression = self._parse_expression(Precedence.LOWEST)
        if expression is None:
            return None

        if params is not None:
            expression = ast.Function(params, expression)

        return ast.FieldStatement(key, expression, inherit, visibility)

    def _parse_member_statement(self) -> Optional[ast.MemberStatement]:
        member: Optional[ast.MemberStatement]
        if self._current_token_type_is(TokenType.LOCAL):
            member = self._parse_objlocal_statement()
        elif (
            self._current_token_type_is(TokenType.IDENT)
            or self._current_token_type_is(TokenType.STRING)
            or self._current_token_type_is(TokenType.LBRACKET)
        ):
            member = self._parse_field_statement()
        else:
            member = None
        if member is None:
            return None
        return member

    def _parse_for_statement(self) -> Optional[ast.ForStatement]:
        self.next_token()  # consume the 'for' token
        identifier = self._parse_identifier()
        if not self._expect_peek_type(TokenType.IN):
            return None
        self.next_token()  # consume the 'in' token
        expression = self._parse_expression(Precedence.LOWEST)
        if expression is None:
            return None
        return ast.ForStatement(identifier, expression)

    def _parse_if_statement(self) -> Optional[ast.IfStatement]:
        self.next_token()  # consume the 'if' token
        condition = self._parse_expression(Precedence.LOWEST)
        if condition is None:
            return None
        return ast.IfStatement(condition)

    def _parse_object(self) -> Optional[ast.Object]:
        members: List[ast.MemberStatement] = []
        while not self._peek_token_type_is(TokenType.RBRACE):
            self.next_token()
            member = self._parse_member_statement()
            if member is None:
                return None
            members.append(member)
            if self._peek_token_type_is(TokenType.COMMA):
                self.next_token()
        if not self._expect_peek_type(TokenType.RBRACE):
            return None
        return ast.Object(members)

    def _parse_array(self) -> Optional[Union[ast.Array, ast.ListComprehension]]:
        self.next_token()  # consume the '[' token

        first_expression = self._parse_expression(Precedence.LOWEST)
        if first_expression is None:
            return None

        # parse list comprehension
        if self._peek_token_type_is(TokenType.FOR):
            self.next_token()  # move to the 'for' token
            forspec = self._parse_for_statement()
            if forspec is None:
                return None
            compspec: List[Union[ast.ForStatement, ast.IfStatement]] = []
            while not self._peek_token_type_is(TokenType.RBRACKET):
                if self._peek_token_type_is(TokenType.FOR):
                    self.next_token()
                    forspec = self._parse_for_statement()
                    if forspec is None:
                        return None
                    compspec.append(forspec)
                elif self._peek_token_type_is(TokenType.IF):
                    self.next_token()
                    ifspec = self._parse_if_statement()
                    if ifspec is None:
                        return None
                    compspec.append(ifspec)
                else:
                    self._errors.append(f"expected 'for' or 'if', got {self._peek_token.token_type} instead")
                    return None
            if not self._expect_peek_type(TokenType.RBRACKET):
                return None
            return ast.ListComprehension(first_expression, forspec, compspec)

        # parse array
        elements: List[ast.Expression[Any]] = [first_expression]
        if self._peek_token_type_is(TokenType.COMMA):
            self.next_token()  # consume the ',' token
        while not self._peek_token_type_is(TokenType.RBRACKET):
            self.next_token()
            element = self._parse_expression(Precedence.LOWEST)
            if element is None:
                return None
            elements.append(element)
            if self._peek_token_type_is(TokenType.COMMA):
                self.next_token()
        if not self._expect_peek_type(TokenType.RBRACKET):
            return None
        return ast.Array(elements)

    def _parse_statement(self) -> Optional[ast.Statement]:
        if self._current_token_type_is(TokenType.LOCAL):
            return self._parse_objlocal_statement()
        return None

    def next_token(self) -> None:
        self._cur_token = self._peek_token
        self._peek_token = self._lexer.next_token()

    def parse(self) -> Optional[ast.Expression]:
        return self._parse_expression(Precedence.LOWEST)
