import copy
import dataclasses
from typing import Dict, Optional, cast

from pysonnet import ast
from pysonnet.errors import PysonnetRuntimeError
from pysonnet.objects import FALSE, NULL, TRUE, Array, Boolean, Function, Number, Object, Primitive, String
from pysonnet.stdlib import STDLIB

stdtype = cast(Function[String], STDLIB[String("type")])


@dataclasses.dataclass
class Context:
    bindings: Dict[str, Primitive] = dataclasses.field(default_factory=dict)
    dollar: Optional[Object] = None
    super_: Optional[Object] = None
    this: Optional[Object] = None

    def clone(self) -> "Context":
        return copy.deepcopy(self)


class Evaluator:
    def _evaluate_literal(self, node: ast.LiteralAST, context: Context) -> Primitive:
        del context
        if isinstance(node, ast.Null):
            return NULL
        if isinstance(node, ast.Boolean):
            return TRUE if node.value else FALSE
        if isinstance(node, ast.Number):
            return Number(node.value)
        if isinstance(node, ast.String):
            return String(node.value)
        raise PysonnetRuntimeError(f"Unsupported literal type: {type(node)}")

    def _evaluate_identifier(self, node: ast.Identifier, context: Context) -> Primitive:
        if node.name in context.bindings:
            return context.bindings[node.name]
        if node.name == "std":
            return STDLIB
        raise PysonnetRuntimeError(f"Undefined identifier: {node.name}")

    def _evaluate_object(self, node: ast.Object, context: Context) -> Object:
        bindings = {}
        objfields: Dict[String, ast.ObjectField] = {}
        for member in node.members:
            if isinstance(member, ast.ObjectField):
                key = self(member.key, context)
                if not isinstance(key, String):
                    raise PysonnetRuntimeError(f"Field name must be a string, not {stdtype(key)}")
                if key in objfields:
                    raise PysonnetRuntimeError(f"Duplicate field: {key}")
                objfields[key] = member
            elif isinstance(member, ast.ObjectLocal):
                bindings[member.bind.ident.name] = self(member.bind.expr, context)
            else:
                raise PysonnetRuntimeError(f"Unsupported object member: {type(member)}")
        obj = Object()
        context = context.clone()
        context.bindings.update(bindings)
        context.this = obj
        if context.dollar is None:
            context.dollar = obj
        for key, field in objfields.items():
            value = self(field.expr, context)
            inherit = field.inherit
            visibility = Object.Visibility.VISIBLE
            if field.visibility == ast.ObjectField.Visibility.HIDDEN:
                visibility = Object.Visibility.HIDDEN
            elif field.visibility == ast.ObjectField.Visibility.FORCE_VISIBLE:
                visibility = Object.Visibility.FORCE_VISIBLE
            obj.add(Object.Field(key, value, inherit, visibility))
        return obj

    def _evaluate_array(self, node: ast.Array, context: Context) -> Array:
        return Array([self(expr, context) for expr in node.elements])

    def _evaluate_binary(self, node: ast.Binary, context: Context) -> Primitive:
        operator = node.operator
        left = self(node.left, context)
        right = self(node.right, context)
        if operator == ast.Binary.Operator.ADD:
            if isinstance(left, Number) and isinstance(right, Number):
                return left + right
            if isinstance(left, Array) and isinstance(right, Array):
                return left + right
            if isinstance(left, Object) and isinstance(right, Object):
                return left + right
            if isinstance(left, String) and isinstance(right, (Number, String, Array, Object)):
                return left + right
            if isinstance(left, (Number, String, Array, Object)) and isinstance(right, String):
                return left + right  # type: ignore[operator]
            raise PysonnetRuntimeError(f"Unsupported operand types for +: {stdtype(left)} and {stdtype(right)}")
        if operator == ast.Binary.Operator.SUB:
            if isinstance(left, Number) and isinstance(right, Number):
                return left - right
            raise PysonnetRuntimeError(f"Unsupported operand types for -: {stdtype(left)} and {stdtype(right)}")
        if operator == ast.Binary.Operator.MUL:
            if isinstance(left, Number) and isinstance(right, Number):
                return left * right
            raise PysonnetRuntimeError(f"Unsupported operand types for *: {stdtype(left)} and {stdtype(right)}")
        if operator == ast.Binary.Operator.DIV:
            if isinstance(left, Number) and isinstance(right, Number):
                try:
                    return left / right
                except ZeroDivisionError:
                    raise PysonnetRuntimeError("Division by zero")
            raise PysonnetRuntimeError(f"Unsupported operand types for /: {stdtype(left)} and {stdtype(right)}")
        if operator == ast.Binary.Operator.MOD:
            if isinstance(left, Number) and isinstance(right, Number):
                return left % right
            if isinstance(left, String) and isinstance(right, (Number, String, Array, Object)):
                try:
                    return left % right
                except TypeError as e:
                    raise PysonnetRuntimeError(e.args[0])
            raise PysonnetRuntimeError(f"Unsupported operand types for %: {stdtype(left)} and {stdtype(right)}")
        if operator == ast.Binary.Operator.EQ:
            return Boolean(left == right)
        if operator == ast.Binary.Operator.NE:
            return Boolean(left != right)
        if operator == ast.Binary.Operator.LT:
            if isinstance(left, Number) and isinstance(right, Number):
                return Boolean(left < right)
            if isinstance(left, String) and isinstance(right, String):
                return Boolean(left < right)
            if isinstance(left, Array) and isinstance(right, Array):
                return Boolean(left < right)
            raise PysonnetRuntimeError(f"Unsupported operand types for <: {stdtype(left)} and {stdtype(right)}")
        if operator == ast.Binary.Operator.LE:
            if isinstance(left, Number) and isinstance(right, Number):
                return Boolean(left <= right)
            if isinstance(left, String) and isinstance(right, String):
                return Boolean(left <= right)
            if isinstance(left, Array) and isinstance(right, Array):
                return Boolean(left <= right)
            raise PysonnetRuntimeError(f"Unsupported operand types for <=: {stdtype(left)} and {stdtype(right)}")
        if operator == ast.Binary.Operator.GT:
            if isinstance(left, Number) and isinstance(right, Number):
                return Boolean(left > right)
            if isinstance(left, String) and isinstance(right, String):
                return Boolean(left > right)
            if isinstance(left, Array) and isinstance(right, Array):
                return Boolean(left > right)
            raise PysonnetRuntimeError(f"Unsupported operand types for >: {stdtype(left)} and {stdtype(right)}")
        if operator == ast.Binary.Operator.GE:
            if isinstance(left, Number) and isinstance(right, Number):
                return Boolean(left >= right)
            if isinstance(left, String) and isinstance(right, String):
                return Boolean(left >= right)
            if isinstance(left, Array) and isinstance(right, Array):
                return Boolean(left >= right)
            raise PysonnetRuntimeError(f"Unsupported operand types for >=: {stdtype(left)} and {stdtype(right)}")
        if operator == ast.Binary.Operator.AND:
            return left and right
        if operator == ast.Binary.Operator.OR:
            return left or right
        if operator == ast.Binary.Operator.IN:
            if isinstance(right, Array):
                return Boolean(left in right)
            if isinstance(right, dict):
                return Boolean(left in right)
            raise PysonnetRuntimeError(f"Unsupported operand types for in: {stdtype(left)} and {stdtype(right)}")
        if operator == ast.Binary.Operator.INDEX:
            if isinstance(left, Array) and isinstance(right, Number):
                try:
                    return cast(Primitive, left[right.value])
                except IndexError:
                    raise PysonnetRuntimeError(f"Index out of range, not within [0, {len(left)})")
            if isinstance(left, Object):
                if not isinstance(right, String):
                    raise PysonnetRuntimeError(f"Unsupported type for index: {type(right)}, expected string")
                try:
                    return left[right]
                except KeyError:
                    raise PysonnetRuntimeError(f"Field does not exist: {right}")
            raise PysonnetRuntimeError(f"Unsupported operand types for index: {type(left)} and {type(right)}")
        raise PysonnetRuntimeError(f"Unsupported binary operator: {operator}")

    def _evaluate_apply(self, node: ast.Apply, context: Context) -> Primitive:
        callee = self(node.callee)
        if not isinstance(callee, Function):
            raise PysonnetRuntimeError(f"Cannot call {stdtype(callee)}")
        args = [self(arg.expr, context) for arg in node.args if arg.ident is None]
        kwargs = {arg.ident.name: self(arg.expr) for arg in node.args if arg.ident is not None}
        return cast(Primitive, callee(*args, **kwargs))

    def _evaluate_self(self, node: ast.Self, context: Context) -> Primitive:
        if context.this is None:
            raise PysonnetRuntimeError("No object in context")
        return context.this

    def _evaluate_dollar(self, node: ast.Dollar, context: Context) -> Primitive:
        if context.dollar is None:
            raise PysonnetRuntimeError("No object in context")
        return context.dollar

    def __call__(self, node: ast.AST, context: Optional[Context] = None) -> Primitive:
        if context is None:
            context = Context()

        if isinstance(node, ast.LiteralAST):
            return self._evaluate_literal(node, context)

        if isinstance(node, ast.Self):
            return self._evaluate_self(node, context)

        if isinstance(node, ast.Dollar):
            return self._evaluate_dollar(node, context)

        if isinstance(node, ast.Object):
            return self._evaluate_object(node, context)

        if isinstance(node, ast.Array):
            return self._evaluate_array(node, context)

        if isinstance(node, ast.Identifier):
            return self._evaluate_identifier(node, context)

        if isinstance(node, ast.Binary):
            return self._evaluate_binary(node, context)

        if isinstance(node, ast.Apply):
            return self._evaluate_apply(node, context)

        raise PysonnetRuntimeError(f"Unsupported type: {type(node)}")
