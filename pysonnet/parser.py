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
    TokenType.LBRACE: Precedence.SUM,
}


class Parser:
    def __init__(self, lexer: Lexer) -> None:
        self._lexer = lexer
        self._cur_token = self._lexer.next_token()
        self._peek_token = self._lexer.next_token()

        self._errors: List[str] = []

        self._prefix_parsers: Dict[TokenType, Callable[[], Optional[ast.AST]]] = {
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
            TokenType.PLUS: self._parse_unary,
            TokenType.MINUS: self._parse_unary,
            TokenType.BANG: self._parse_unary,
            TokenType.TILDE: self._parse_unary,
            TokenType.SELF: self._parse_self,
            TokenType.DOLLAR: self._parse_dollar,
            TokenType.SUPER: self._parse_super,
            TokenType.FUNCTION: self._parse_function,
            TokenType.ERROR: self._parse_error,
            TokenType.ASSERT: self._parse_assert_expression,
            TokenType.IF: self._parse_if_expression,
            TokenType.IMPORT: self._parse_import,
            TokenType.IMPORTSTR: self._parse_importstr,
            TokenType.IMPORTBIN: self._parse_importbin,
        }
        self._infix_parsers: Dict[TokenType, Callable[[ast.AST], Optional[ast.AST]]] = {
            TokenType.PLUS: self._parse_binary,
            TokenType.MINUS: self._parse_binary,
            TokenType.STAR: self._parse_binary,
            TokenType.SLASH: self._parse_binary,
            TokenType.MOD: self._parse_binary,
            TokenType.LAND: self._parse_binary,
            TokenType.LOR: self._parse_binary,
            TokenType.XOR: self._parse_binary,
            TokenType.LSHIFT: self._parse_binary,
            TokenType.RSHIFT: self._parse_binary,
            TokenType.AND: self._parse_binary,
            TokenType.OR: self._parse_binary,
            TokenType.EQEQ: self._parse_binary,
            TokenType.NEQ: self._parse_binary,
            TokenType.LT: self._parse_binary,
            TokenType.GT: self._parse_binary,
            TokenType.LE: self._parse_binary,
            TokenType.GE: self._parse_binary,
            TokenType.IN: self._parse_binary,
            TokenType.DOT: self._parse_binary,
            TokenType.LBRACKET: self._parse_binary,
            TokenType.LPAREN: self._parse_apply,
            TokenType.LBRACE: self._parse_apply_brace,
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

    def _parse_grouped_expression(self) -> Optional[ast.AST]:
        self.next_token()  # consume the '(' token
        expression = self._parse_expression(Precedence.LOWEST)
        if not self._expect_peek_type(TokenType.RPAREN):
            return None
        return expression

    def _parse_self(self) -> Optional[ast.Self]:
        return ast.Self()

    def _parse_dollar(self) -> Optional[ast.Dollar]:
        return ast.Dollar()

    def _parse_super(self) -> Optional[ast.Super]:
        return ast.Super()

    def _parse_error(self) -> Optional[ast.Error]:
        self.next_token()  # consume the 'error' token
        expression = self._parse_expression(Precedence.LOWEST)
        if expression is None:
            return None
        return ast.Error(expression)

    def _parse_assert(self) -> Optional[ast.Assert]:
        self.next_token()  # consume the 'assert' token
        condition = self._parse_expression(Precedence.LOWEST)
        if condition is None:
            return None
        message: Optional[ast.AST] = None
        if self._peek_token_type_is(TokenType.COLON):
            self.next_token()  # consume the ':' token
            self.next_token()  # move to the message
            message = self._parse_expression(Precedence.LOWEST)
            if message is None:
                return None
        return ast.Assert(condition, message)

    def _parse_assert_expression(self) -> Optional[ast.AssertExpression]:
        assert_ = self._parse_assert()
        if not assert_:
            return None
        if not self._expect_peek_type(TokenType.SEMICOLON):
            return None
        self.next_token()
        expression = self._parse_expression(Precedence.LOWEST)
        if expression is None:
            return None
        return ast.AssertExpression(assert_, expression)

    def _parse_if_expression(self) -> Optional[ast.IfExpression]:
        self.next_token()  # consume the 'if' token
        condition = self._parse_expression(Precedence.LOWEST)
        if not condition:
            return None
        if not self._expect_peek_type(TokenType.THEN):
            return None

        self.next_token()  # consume the 'then' token

        then_expr = self._parse_expression(Precedence.LOWEST)
        if not then_expr:
            return None

        else_expr: Optional[ast.AST] = None
        if self._peek_token_type_is(TokenType.ELSE):
            self.next_token()  # move to the 'else' token
            self.next_token()  # consume the 'else' token
            else_expr = self._parse_expression(Precedence.LOWEST)
            if not else_expr:
                return None

        return ast.IfExpression(condition, then_expr, else_expr)

    def _parse_param(self) -> Optional[ast.Param]:
        ident = self._parse_identifier()
        default: Optional[ast.AST] = None
        if self._peek_token_type_is(TokenType.EQUAL):
            self.next_token()  # move to the '=' token
            self.next_token()  # consume the '=' token
            default = self._parse_expression(Precedence.LOWEST)
            if default is None:
                return None
        return ast.Param(ident, default)

    def _parse_params(self) -> Optional[List[ast.Param]]:
        param = self._parse_param()
        if param is None:
            return None
        params = [param]
        while self._peek_token_type_is(TokenType.COMMA):
            self.next_token()  # consume the ',' token
            if not self._peek_token_type_is(TokenType.IDENT):
                break
            self.next_token()
            param = self._parse_param()
            if param is None:
                return None
            params.append(param)
        return params

    def _parse_function(self) -> Optional[ast.Function]:
        if not self._expect_peek_type(TokenType.LPAREN):
            return None
        self.next_token()
        params = self._parse_params()
        if params is None:
            return None
        if not self._expect_peek_type(TokenType.RPAREN):
            return None
        self.next_token()
        expression = self._parse_expression(Precedence.LOWEST)
        if expression is None:
            return None
        return ast.Function(params, expression)

    def _parse_apply(self, function: ast.AST) -> Optional[ast.Apply]:
        args: List[ast.Arg] = []
        read_kwargs = False
        while not self._peek_token_type_is(TokenType.RPAREN):
            if read_kwargs:
                if not self._expect_peek_type(TokenType.IDENT):
                    return None
                ident = self._parse_identifier()
                if not self._expect_peek_type(TokenType.EQUAL):
                    return None
                self.next_token()
                expression = self._parse_expression(Precedence.LOWEST)
                if expression is None:
                    return None
                args.append(ast.Arg(expression, ident))
            else:
                self.next_token()
                if self._current_token_type_is(TokenType.IDENT) and self._peek_token_type_is(TokenType.EQUAL):
                    ident = self._parse_identifier()
                    if not self._expect_peek_type(TokenType.EQUAL):
                        return None
                    self.next_token()
                    expression = self._parse_expression(Precedence.LOWEST)
                    if expression is None:
                        return None
                    args.append(ast.Arg(expression, ident))
                else:
                    expression = self._parse_expression(Precedence.LOWEST)
                    if expression is None:
                        return None
                    args.append(ast.Arg(expression))
            if self._peek_token_type_is(TokenType.COMMA):
                self.next_token()
        if not self._expect_peek_type(TokenType.RPAREN):
            return None
        tailstrict = False
        if self._peek_token_type_is(TokenType.TAILSTRICT):
            self.next_token()
            tailstrict = True
        return ast.Apply(function, args, tailstrict)

    def _parse_apply_brace(self, left: ast.AST) -> Optional[ast.ApplyBrace]:
        right = self._parse_object()
        if right is None:
            return None
        return ast.ApplyBrace(left, right)

    def _parse_unary(self) -> Optional[ast.Unary]:
        operator: ast.Unary.Operator
        if self._current_token_type_is(TokenType.PLUS):
            operator = ast.Unary.Operator.PLUS
        elif self._current_token_type_is(TokenType.MINUS):
            operator = ast.Unary.Operator.MINUS
        elif self._current_token_type_is(TokenType.BANG):
            operator = ast.Unary.Operator.NOT
        elif self._current_token_type_is(TokenType.TILDE):
            operator = ast.Unary.Operator.BITWISE_NOT
        else:
            self._errors.append(f"unknown unary operator: {self._cur_token.literal}")
            return None
        self.next_token()
        expression = self._parse_expression(Precedence.UNARY)
        if not expression:
            return None
        return ast.Unary(operator, expression)

    def _parse_binary(self, left: ast.AST) -> Optional[ast.AST]:
        operator: ast.Binary.Operator
        if self._current_token_type_is(TokenType.PLUS):
            operator = ast.Binary.Operator.ADD
        elif self._current_token_type_is(TokenType.MINUS):
            operator = ast.Binary.Operator.SUB
        elif self._current_token_type_is(TokenType.STAR):
            operator = ast.Binary.Operator.MUL
        elif self._current_token_type_is(TokenType.SLASH):
            operator = ast.Binary.Operator.DIV
        elif self._current_token_type_is(TokenType.MOD):
            operator = ast.Binary.Operator.MOD
        elif self._current_token_type_is(TokenType.LAND):
            operator = ast.Binary.Operator.BITWISE_AND
        elif self._current_token_type_is(TokenType.LOR):
            operator = ast.Binary.Operator.BITWISE_OR
        elif self._current_token_type_is(TokenType.XOR):
            operator = ast.Binary.Operator.BITWISE_XOR
        elif self._current_token_type_is(TokenType.LSHIFT):
            operator = ast.Binary.Operator.LSHIFT
        elif self._current_token_type_is(TokenType.RSHIFT):
            operator = ast.Binary.Operator.RSHIFT
        elif self._current_token_type_is(TokenType.AND):
            operator = ast.Binary.Operator.AND
        elif self._current_token_type_is(TokenType.OR):
            operator = ast.Binary.Operator.OR
        elif self._current_token_type_is(TokenType.EQEQ):
            operator = ast.Binary.Operator.EQ
        elif self._current_token_type_is(TokenType.NEQ):
            operator = ast.Binary.Operator.NE
        elif self._current_token_type_is(TokenType.LT):
            operator = ast.Binary.Operator.LT
        elif self._current_token_type_is(TokenType.GT):
            operator = ast.Binary.Operator.GT
        elif self._current_token_type_is(TokenType.LE):
            operator = ast.Binary.Operator.LE
        elif self._current_token_type_is(TokenType.GE):
            operator = ast.Binary.Operator.GE
        elif self._current_token_type_is(TokenType.IN):
            operator = ast.Binary.Operator.IN
        elif self._current_token_type_is(TokenType.DOT):
            if not self._expect_peek_type(TokenType.IDENT):
                return None
            return ast.Binary(
                ast.Binary.Operator.INDEX,
                left,
                ast.String(self._cur_token.literal),
            )
        elif self._current_token_type_is(TokenType.LBRACKET):
            expr = self._parse_index(left)
            if expr is None:
                return None
            return expr
        else:
            self._errors.append(f"unknown binary operator: {self._cur_token.literal}")
            return None
        precedence = self._current_binary_precedence()
        self.next_token()
        right = self._parse_expression(precedence)
        if not right:
            return None
        return ast.Binary(operator, left, right)

    def _parse_index(self, indexable: ast.AST) -> Optional[ast.AST]:
        if self._peek_token_type_is(TokenType.RBRACKET):
            self._errors.append("index expression is empty")
            return None
        start: Optional[ast.AST] = None
        end: Optional[ast.AST] = None
        step: Optional[ast.AST] = None
        num_colons = 0
        if self._peek_token_type_is(TokenType.COLON):
            num_colons += 1
            self.next_token()
        elif self._peek_token_type_is(TokenType.DCOLON):
            num_colons += 2
        else:
            self.next_token()
            start = self._parse_expression(Precedence.LOWEST)
            if start is None:
                return None
            if self._peek_token_type_is(TokenType.COLON):
                num_colons += 1
                self.next_token()
        if self._peek_token_type_is(TokenType.DCOLON):
            num_colons += 2
            self.next_token()
        elif self._peek_token_type_is(TokenType.RBRACKET):
            pass
        else:
            self.next_token()
            end = self._parse_expression(Precedence.LOWEST)
            if not end:
                return None
            if self._peek_token_type_is(TokenType.COLON):
                num_colons += 1
                self.next_token()
        if not self._peek_token_type_is(TokenType.RBRACKET):
            self.next_token()
            step = self._parse_expression(Precedence.LOWEST)
            if not step:
                return None
        if not self._expect_peek_type(TokenType.RBRACKET):
            return None
        if num_colons == 0:
            if start is None:
                return indexable
            return ast.Binary(ast.Binary.Operator.INDEX, indexable, start)
        if not start and not end and not step:
            return indexable
        return ast.Apply(
            ast.Binary(
                ast.Binary.Operator.INDEX,
                ast.Identifier("std"),
                ast.String("slice"),
            ),
            [
                ast.Arg(indexable),
                ast.Arg(start or ast.Null()),
                ast.Arg(end or ast.Null()),
                ast.Arg(step or ast.Null()),
            ],
        )

    def _parse_expression(self, precedence: Precedence) -> Optional[ast.AST]:
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
        binds: List[ast.Bind] = []

        bind = self._parse_bind()
        if bind is None:
            return None
        binds.append(bind)

        while self._peek_token_type_is(TokenType.COMMA):
            self.next_token()
            if not self._expect_peek_type(TokenType.IDENT):
                return None
            bind = self._parse_bind()
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

    def _parse_bind(self) -> Optional[ast.Bind]:
        name = ast.Identifier[Any](self._cur_token.literal)
        params: Optional[List[ast.Param]] = None
        if self._peek_token_type_is(TokenType.LPAREN):
            self.next_token()  # move to the '(' token
            if self._peek_token_type_is(TokenType.RPAREN):
                params = []
            else:
                self.next_token()  # consume the '(' token
                params = self._parse_params()
                if not params:
                    return None
            if not self._expect_peek_type(TokenType.RPAREN):
                return None
        if not self._expect_peek_type(TokenType.EQUAL):
            return None
        self.next_token()  # consume the '=' token
        expression = self._parse_expression(Precedence.LOWEST)
        if expression is None:
            return None
        if params is not None:
            expression = ast.Function(params, expression)
        return ast.Bind(name, expression)

    def _parse_object_local(self) -> Optional[ast.ObjectLocal]:
        self.next_token()  # consume the 'local' token
        bind = self._parse_bind()
        if not bind:
            return None
        return ast.ObjectLocal(bind)

    def _parse_object_field(self) -> Optional[ast.ObjectField]:
        key: ast.AST[str]
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

        params: Optional[List[ast.Param]] = None
        if self._peek_token_type_is(TokenType.LPAREN):
            self.next_token()
            self.next_token()
            params = self._parse_params()
            if params is None:
                return None
            if not self._expect_peek_type(TokenType.RPAREN):
                return None

        inherit = False
        if self._peek_token_type_is(TokenType.PLUS):
            inherit = True
            self.next_token()

        visibility: ast.ObjectField.Visibility
        if self._peek_token_type_is(TokenType.COLON):
            visibility = ast.ObjectField.Visibility.VISIBLE
        elif self._peek_token_type_is(TokenType.DCOLON):
            visibility = ast.ObjectField.Visibility.HIDDEN
        elif self._peek_token_type_is(TokenType.TCOLON):
            visibility = ast.ObjectField.Visibility.FORCE_VISIBLE
        else:
            self._errors.append(f"expected ':' or '::' or ':::', got {self._peek_token.token_type} instead")
            return None

        self.next_token()  # consume the separator token
        self.next_token()

        expression = self._parse_expression(Precedence.LOWEST)
        if expression is None:
            return None

        if params is not None:
            expression = ast.Function(params, expression)

        return ast.ObjectField(key, expression, inherit, visibility)

    def _parse_object_member(self) -> Optional[ast.ObjectMember]:
        member: Optional[ast.ObjectMember] = None
        if self._current_token_type_is(TokenType.LOCAL):
            member = self._parse_object_local()
        elif self._current_token_type_is(TokenType.ASSERT):
            member = self._parse_assert()
        elif (
            self._current_token_type_is(TokenType.IDENT)
            or self._current_token_type_is(TokenType.STRING)
            or self._current_token_type_is(TokenType.LBRACKET)
        ):
            member = self._parse_object_field()
        else:
            self._errors.append(f"unexpected token {self._cur_token.token_type}")
        if member is None:
            return None
        return member

    def _parse_for_spec(self) -> Optional[ast.ForSpec]:
        self.next_token()  # consume the 'for' token
        identifier = self._parse_identifier()
        if not self._expect_peek_type(TokenType.IN):
            return None
        self.next_token()  # consume the 'in' token
        expression = self._parse_expression(Precedence.LOWEST)
        if expression is None:
            return None
        return ast.ForSpec(identifier, expression)

    def _parse_if_spec(self) -> Optional[ast.IfSpec]:
        self.next_token()  # consume the 'if' token
        condition = self._parse_expression(Precedence.LOWEST)
        if condition is None:
            return None
        return ast.IfSpec(condition)

    def _parse_object(self) -> Optional[Union[ast.Object, ast.ObjectComprehension]]:
        fields: List[ast.ObjectField] = []
        efields: List[ast.ObjectField] = []
        asserts: List[ast.Assert] = []
        locals_: List[ast.ObjectLocal] = []
        members: List[ast.ObjectMember] = []
        while not (self._peek_token_type_is(TokenType.RBRACE) or self._peek_token_type_is(TokenType.FOR)):
            container: List
            if self._peek_token_type_is(TokenType.LOCAL):
                container = locals_
            elif self._peek_token_type_is(TokenType.ASSERT):
                container = asserts
            elif self._peek_token_type_is(TokenType.LBRACKET):
                container = efields
            else:
                container = fields
            self.next_token()
            member = self._parse_object_member()
            if member is None:
                return None
            container.append(member)
            members.append(member)
            if self._peek_token_type_is(TokenType.COMMA):
                self.next_token()
        if self._peek_token_type_is(TokenType.FOR):
            if fields or len(efields) != 1:
                self._errors.append("object comprehensions can only have a single [e] field")
                return None
            key = efields[0].key
            value = efields[0].expr
            self.next_token()  # move to the 'for' token
            forspec = self._parse_for_spec()
            if forspec is None:
                return None
            compspecs: List[ast.ComprehensionSpec] = []
            while not self._peek_token_type_is(TokenType.RBRACE):
                if self._peek_token_type_is(TokenType.FOR):
                    self.next_token()
                    nested_forspec = self._parse_for_spec()
                    if nested_forspec is None:
                        return None
                    compspecs.append(nested_forspec)
                elif self._peek_token_type_is(TokenType.IF):
                    self.next_token()
                    nested_ifspec = self._parse_if_spec()
                    if nested_ifspec is None:
                        return None
                    compspecs.append(nested_ifspec)
                else:
                    self._errors.append(f"expected 'for' or 'if', got {self._peek_token.token_type} instead")
                    return None
            if not self._expect_peek_type(TokenType.RBRACE):
                return None
            return ast.ObjectComprehension(locals_, key, value, forspec, compspecs)
        if not self._expect_peek_type(TokenType.RBRACE):
            return None
        return ast.Object(members)

    def _parse_array(self) -> Optional[Union[ast.Array, ast.ArrayComprehension]]:
        if self._peek_token_type_is(TokenType.RBRACKET):
            self.next_token()
            return ast.Array([])

        self.next_token()  # consume the '[' token
        first_expression = self._parse_expression(Precedence.LOWEST)
        if first_expression is None:
            return None

        if self._peek_token_type_is(TokenType.COMMA):
            self.next_token()

        # parse array comprehension
        if self._peek_token_type_is(TokenType.FOR):
            self.next_token()  # move to the 'for' token
            forspec = self._parse_for_spec()
            if forspec is None:
                return None
            compspec: List[ast.ComprehensionSpec] = []
            while not self._peek_token_type_is(TokenType.RBRACKET):
                if self._peek_token_type_is(TokenType.FOR):
                    self.next_token()
                    nested_forspec = self._parse_for_spec()
                    if nested_forspec is None:
                        return None
                    compspec.append(nested_forspec)
                elif self._peek_token_type_is(TokenType.IF):
                    self.next_token()
                    nested_ifspec = self._parse_if_spec()
                    if nested_ifspec is None:
                        return None
                    compspec.append(nested_ifspec)
                else:
                    self._errors.append(f"expected 'for' or 'if', got {self._peek_token.token_type} instead")
                    return None
            if not self._expect_peek_type(TokenType.RBRACKET):
                return None
            return ast.ArrayComprehension(first_expression, forspec, compspec)

        # parse array
        elements: List[ast.AST[Any]] = [first_expression]
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

    def _parse_import(self) -> Optional[ast.Import]:
        if not self._expect_peek_type(TokenType.STRING):
            return None
        filename = self._cur_token.literal
        return ast.Import(filename)

    def _parse_importstr(self) -> Optional[ast.Importstr]:
        if not self._expect_peek_type(TokenType.STRING):
            return None
        filename = self._cur_token.literal
        return ast.Importstr(filename)

    def _parse_importbin(self) -> Optional[ast.Importbin]:
        if not self._expect_peek_type(TokenType.STRING):
            return None
        filename = self._cur_token.literal
        return ast.Importbin(filename)

    @property
    def errors(self) -> List[str]:
        return self._errors

    def next_token(self) -> None:
        self._cur_token = self._peek_token
        self._peek_token = self._lexer.next_token()

    def parse(self) -> Optional[ast.AST]:
        return self._parse_expression(Precedence.LOWEST)
