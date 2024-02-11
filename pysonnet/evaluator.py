import dataclasses
from typing import Dict, List, Optional, Union, cast

from pysonnet import ast
from pysonnet.errors import PysonnetRuntimeError
from pysonnet.objects import FALSE, NULL, TRUE, Array, Boolean, Function, Null, Number, Object, Primitive, String
from pysonnet.stdlib import STDLIB

stdtype = cast(Function[String], STDLIB[String("type")])


@dataclasses.dataclass
class Lazy:
    node: ast.AST
    context: "Context"

    def clone(self) -> "Lazy":
        return Lazy(self.node, self.context)


@dataclasses.dataclass
class Context:
    bindings: Dict[str, Union[Lazy, Primitive]] = dataclasses.field(default_factory=dict)
    dollar: Optional[Object] = None
    super_: Optional[Object] = None
    this: Optional[Object] = None

    def clone(self) -> "Context":
        return Context(
            {k: v.clone() for k, v in self.bindings.items()},
            self.dollar.clone() if self.dollar is not None else None,
            self.super_.clone() if self.super_ is not None else None,
            self.this.clone() if self.this is not None else None,
        )


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
            value = context.bindings[node.name]
            if isinstance(value, Lazy):
                return self(value.node, value.context)
            return value
        if node.name == "std":
            return STDLIB
        raise PysonnetRuntimeError(f"Unknown variable: {node.name}")

    def _evaluate_object(self, node: ast.Object, context: Context) -> Object:
        bindings = {}
        objfields: Dict[String, ast.ObjectField] = {}
        for member in node.members:
            if isinstance(member, ast.ObjectField):
                key = self(member.key, context)
                if isinstance(key, Null):
                    continue
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
            obj.add_field(Object.Field(key, value, inherit, visibility))
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
            if isinstance(left, String) and isinstance(right, (Number, String, Array, Object)):
                return left + right
            if isinstance(left, (Number, String, Array, Object)) and isinstance(right, String):
                return left + right
            if isinstance(left, Object) and isinstance(right, Object):
                # TODO: handle errors
                return left + right
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
        # TODO: handle tailstrict
        callee = self(node.callee, context)
        if not isinstance(callee, Function):
            raise PysonnetRuntimeError(f"Cannot call {stdtype(callee)}")
        args = [self(arg.expr, context) for arg in node.args if arg.ident is None]
        kwargs = {arg.ident.name: self(arg.expr) for arg in node.args if arg.ident is not None}
        return cast(Primitive, callee(*args, **kwargs))

    def _evaluate_apply_brace(self, node: ast.ApplyBrace, context: Context) -> Primitive:
        left = self(node.left, context)
        right = self(node.right, context)
        assert isinstance(left, Object) and isinstance(right, Object)
        return left + right

    def _evaluate_local(self, node: ast.LocalExpression, context: Context) -> Primitive:
        context = context.clone()
        for bind in node.binds:
            context.bindings[bind.ident.name] = Lazy(bind.expr, context)
        return self(node.expr, context)

    def _evaluate_if(self, node: ast.IfExpression, context: Context) -> Primitive:
        condition = self(node.condition, context)
        if not isinstance(condition, Boolean):
            raise PysonnetRuntimeError(f"Condition must be a boolean, not {stdtype(condition)}")
        if condition:
            return self(node.then_expr, context)
        if node.else_expr is not None:
            return self(node.else_expr, context)
        return NULL

    def _evaluate_function(self, node: ast.Function, context: Context) -> Function:
        expr = node.expr
        context = context.clone()

        def _execute_function(*args: Primitive, **kwargs: Primitive) -> Primitive:
            # check parameter names
            unknown_param_names = set(kwargs) - set(param.ident.name for param in node.params)
            if unknown_param_names:
                raise PysonnetRuntimeError(f"Unknown parameters: {', '.join(unknown_param_names)}")
            # check parameter count
            if len(args) + len(kwargs) > len(node.params):
                raise PysonnetRuntimeError(f"Too many parameters, expected {len(node.params)}")
            # check parameter duplication
            args_ = dict(zip((param.ident.name for param in node.params), args))
            duplicate_param_names = set(args_) & set(kwargs)
            if duplicate_param_names:
                raise PysonnetRuntimeError(f"Duplicate parameters: {', '.join(duplicate_param_names)}")
            # merge args into kwargs
            kwargs.update(args_)
            del args
            # fill missing kwargs with default values
            expected_param_names = set(param.ident.name for param in node.params)
            missing_kwparam_names = expected_param_names - set(kwargs)
            default_kwparam_nodes = {
                param.ident.name: param.default for param in node.params if param.default is not None
            }
            if set(missing_kwparam_names) - set(default_kwparam_nodes):
                raise PysonnetRuntimeError(f"Missing parameters: {', '.join(missing_kwparam_names)}")
            default_kwargs = {name: Lazy(default_kwparam_nodes[name], context) for name in missing_kwparam_names}
            # update context
            context.bindings.update(kwargs)
            context.bindings.update(default_kwargs)
            return self(expr, context)

        return Function(_execute_function)

    def _evaluate_array_comprehension(self, node: ast.ArrayComprehension, context: Context) -> Array:
        iterable = self(node.forspec.expr, context)
        if not isinstance(iterable, Array):
            raise PysonnetRuntimeError(f"Unexpected type {stdtype(iterable)}, expected array")
        context = context.clone()
        compspecs = [compspec for compspec in node.compspecs]
        while compspecs and isinstance(compspecs[0], ast.IfSpec):
            ifspec = cast(ast.IfSpec, compspecs.pop(0))
            for index, value in enumerate(iterable):
                context.bindings[node.forspec.ident.name] = value
                condition = self(ifspec.condition, context)
                if not isinstance(condition, Boolean):
                    raise PysonnetRuntimeError(f"Unpexpected type {stdtype(condition)}, expected boolean")
                if not condition:
                    iterable.pop(index)
        values: List[Primitive] = []
        for value in iterable:
            context.bindings[node.forspec.ident.name] = value
            if compspecs:
                nested_forspec = compspecs[0]
                assert isinstance(nested_forspec, ast.ForSpec)
                nested_comprehension = ast.ArrayComprehension(node.expression, nested_forspec, compspecs[1:])
                nested_values = self._evaluate_array_comprehension(nested_comprehension, context.clone())
                values.extend(nested_values)
            else:
                values.append(self(node.expression, context))
        return Array(values)

    def _evaluate_object_comprehension(self, node: ast.ObjectComprehension, context: Context) -> Object:
        iterable = self(node.forspec.expr, context)
        if not isinstance(iterable, Array):
            raise PysonnetRuntimeError(f"Unexpected type {stdtype(iterable)}, expected array")
        context = context.clone()
        for local in node.locals_:
            context.bindings[local.bind.ident.name] = Lazy(local.bind.expr, context)
        compspecs = [compspec for compspec in node.compspecs]
        while compspecs and isinstance(compspecs[0], ast.IfSpec):
            ifspec = cast(ast.IfSpec, compspecs.pop(0))
            for index, value in enumerate(iterable):
                context.bindings[node.forspec.ident.name] = value
                condition = self(ifspec.condition, context)
                if not isinstance(condition, Boolean):
                    raise PysonnetRuntimeError(f"Unpexpected type {stdtype(condition)}, expected boolean")
                if not condition:
                    iterable.pop(index)
        obj = Object()
        for value in iterable:
            context.bindings[node.forspec.ident.name] = value

            if compspecs:
                nested_forspec = compspecs[0]
                assert isinstance(nested_forspec, ast.ForSpec)
                nested_comprehension = ast.ObjectComprehension([], node.key, node.value, nested_forspec, compspecs[1:])
                values = self._evaluate_object_comprehension(nested_comprehension, context.clone())
                for key, value in values.items():
                    if key in obj:
                        raise PysonnetRuntimeError(f"Duplicate field name: {key}")
                    obj.add_field(Object.Field(key, value))
            else:
                key_ = self(node.key, context)
                if isinstance(key_, Null):
                    continue
                if not isinstance(key_, String):
                    raise PysonnetRuntimeError(f"Field name must be a string, not {stdtype(key)}")
                key = key_
                if key in obj:
                    raise PysonnetRuntimeError(f"Duplicate field name: {key}")
                value = self(node.value, context)
                obj.add_field(Object.Field(key, value))
        return obj

    def _evaluate_self(self, node: ast.Self, context: Context) -> Primitive:
        if context.this is None:
            raise PysonnetRuntimeError("No object in context")
        return context.this

    def _evaluate_dollar(self, node: ast.Dollar, context: Context) -> Primitive:
        if context.dollar is None:
            raise PysonnetRuntimeError("No object in context")
        return context.dollar

    def _evaluate_error(self, node: ast.Error, context: Context) -> Primitive:
        message = self(node.expr, context)
        raise PysonnetRuntimeError(str(message))

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

        if isinstance(node, ast.ApplyBrace):
            return self._evaluate_apply_brace(node, context)

        if isinstance(node, ast.LocalExpression):
            return self._evaluate_local(node, context)

        if isinstance(node, ast.IfExpression):
            return self._evaluate_if(node, context)

        if isinstance(node, ast.Function):
            return self._evaluate_function(node, context)

        if isinstance(node, ast.ArrayComprehension):
            return self._evaluate_array_comprehension(node, context)

        if isinstance(node, ast.ObjectComprehension):
            return self._evaluate_object_comprehension(node, context)

        if isinstance(node, ast.Error):
            return self._evaluate_error(node, context)

        raise PysonnetRuntimeError(f"Unsupported type: {type(node)}")
