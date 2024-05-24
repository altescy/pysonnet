import dataclasses
from os import PathLike
from pathlib import Path
from typing import Callable, Dict, List, Mapping, Optional, Union, cast

from pysonnet import ast
from pysonnet.errors import PysonnetRuntimeError
from pysonnet.lexer import Lexer
from pysonnet.objects import FALSE, NULL, TRUE, Array, Boolean, Function, Lazy, Null, Number, Object, Primitive, String
from pysonnet.parser import Parser
from pysonnet.stdlib import StdLib
from pysonnet.types import JsonPrimitive


def _make_lazy(evaluator: "Evaluator", node: ast.AST, context: "Context") -> Lazy:
    # specify default args to capture the values
    return Lazy(lambda evalualtor=evaluator, node=node, context=context: evaluator(node, context))  # type: ignore[misc]


@dataclasses.dataclass
class Context:
    bindings: Dict[str, Union[Lazy, Primitive]] = dataclasses.field(default_factory=dict)
    dollar: Optional[Object] = None
    super_: Optional[Object] = None
    this: Optional[Object] = None

    def clone(self) -> "Context":
        return Context(
            {k: v.clone() for k, v in self.bindings.items()},
            self.dollar,
            self.super_.clone() if self.super_ is not None else None,
            self.this,
        )


class Evaluator:
    def __init__(
        self,
        filename: Optional[Union[str, PathLike]] = None,
        *,
        ext_vars: Optional[Mapping[str, str]] = None,
        native_callbacks: Optional[Mapping[str, Union[Callable[..., JsonPrimitive], Function]]] = None,
    ) -> None:
        ext_vars = ext_vars or {}
        filename = Path(filename) if filename else None
        callbacks = {
            name: callback if isinstance(callback, Function) else Function.from_native_function(callback)
            for name, callback in (native_callbacks or {}).items()
        }
        self._filename = filename
        self._ext_vars = ext_vars
        self._native_callbacks = callbacks
        self._stdlib = StdLib(ext_vars, callbacks)
        self._stdobj = self._stdlib.as_object()
        self._rootdir = self._filename.parent if self._filename else Path("")
        self._stdobj.add_field(Object.Field(String("thisFile"), String(self._filename or "")))

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
                value = value()
            return value
        if node.name == "std":
            return self._stdobj
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
                    raise PysonnetRuntimeError(f"Field name must be a string, not {self._stdlib._type(key)}")
                if key in objfields:
                    raise PysonnetRuntimeError(f"Duplicate field: {key}")
                objfields[key] = member
            elif isinstance(member, ast.ObjectLocal):
                bindings[member.bind.ident.name] = _make_lazy(self, member.bind.expr, context)
            elif isinstance(member, ast.Assert):
                condition = self(member.condition, context)
                if not isinstance(condition, Boolean):
                    raise PysonnetRuntimeError(f"Unpexpected type {self._stdlib._type(condition)}, expected boolean")
                if not condition:
                    message: Primitive
                    if member.message is not None:
                        message = self(member.message, context)
                    else:
                        message = String("Object assertion failed")
                    raise PysonnetRuntimeError(str(message))
                continue
            else:
                raise PysonnetRuntimeError(f"Unsupported object member: {type(member)}")
        obj = Object()
        context = context.clone()
        context.bindings.update(bindings)
        context.this = obj
        if context.dollar is None:
            context.dollar = obj
        for key, field in objfields.items():
            _context = context.clone()
            if isinstance(field.expr, ast.Object) and _context.super_:
                super_ = _context.super_.get(key)
                if super_ and isinstance(super_, Lazy):
                    super_ = super_()
                if super_ is None or isinstance(super_, Object):
                    _context.super_ = super_
            value = _make_lazy(self, field.expr, _context)
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
        if isinstance(left, Lazy):
            left = left()
        if isinstance(left, Object):
            context = context.clone()
            context.super_ = left
        right = self(node.right, context)
        if isinstance(right, Lazy):
            right = right()
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
            raise PysonnetRuntimeError(
                f"Unsupported operand types for +: {self._stdlib._type(left)} and {self._stdlib._type(right)}"
            )
        if operator == ast.Binary.Operator.SUB:
            if isinstance(left, Number) and isinstance(right, Number):
                return left - right
            raise PysonnetRuntimeError(
                f"Unsupported operand types for -: {self._stdlib._type(left)} and {self._stdlib._type(right)}"
            )
        if operator == ast.Binary.Operator.MUL:
            if isinstance(left, Number) and isinstance(right, Number):
                return left * right
            raise PysonnetRuntimeError(
                f"Unsupported operand types for *: {self._stdlib._type(left)} and {self._stdlib._type(right)}"
            )
        if operator == ast.Binary.Operator.DIV:
            if isinstance(left, Number) and isinstance(right, Number):
                try:
                    return left / right
                except ZeroDivisionError:
                    raise PysonnetRuntimeError("Division by zero")
            raise PysonnetRuntimeError(
                f"Unsupported operand types for /: {self._stdlib._type(left)} and {self._stdlib._type(right)}"
            )
        if operator == ast.Binary.Operator.MOD:
            if isinstance(left, Number) and isinstance(right, Number):
                return left % right
            if isinstance(left, String) and isinstance(right, (Number, String, Array, Object)):
                try:
                    return left % right
                except TypeError as e:
                    raise PysonnetRuntimeError(e.args[0])
            raise PysonnetRuntimeError(
                f"Unsupported operand types for %: {self._stdlib._type(left)} and {self._stdlib._type(right)}"
            )
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
            raise PysonnetRuntimeError(
                f"Unsupported operand types for <: {self._stdlib._type(left)} and {self._stdlib._type(right)}"
            )
        if operator == ast.Binary.Operator.LE:
            if isinstance(left, Number) and isinstance(right, Number):
                return Boolean(left <= right)
            if isinstance(left, String) and isinstance(right, String):
                return Boolean(left <= right)
            if isinstance(left, Array) and isinstance(right, Array):
                return Boolean(left <= right)
            raise PysonnetRuntimeError(
                f"Unsupported operand types for <=: {self._stdlib._type(left)} and {self._stdlib._type(right)}"
            )
        if operator == ast.Binary.Operator.GT:
            if isinstance(left, Number) and isinstance(right, Number):
                return Boolean(left > right)
            if isinstance(left, String) and isinstance(right, String):
                return Boolean(left > right)
            if isinstance(left, Array) and isinstance(right, Array):
                return Boolean(left > right)
            raise PysonnetRuntimeError(
                f"Unsupported operand types for >: {self._stdlib._type(left)} and {self._stdlib._type(right)}"
            )
        if operator == ast.Binary.Operator.GE:
            if isinstance(left, Number) and isinstance(right, Number):
                return Boolean(left >= right)
            if isinstance(left, String) and isinstance(right, String):
                return Boolean(left >= right)
            if isinstance(left, Array) and isinstance(right, Array):
                return Boolean(left >= right)
            raise PysonnetRuntimeError(
                f"Unsupported operand types for >=: {self._stdlib._type(left)} and {self._stdlib._type(right)}"
            )
        if operator == ast.Binary.Operator.AND:
            return left and right
        if operator == ast.Binary.Operator.OR:
            return left or right
        if operator == ast.Binary.Operator.IN:
            if isinstance(right, Array):
                return Boolean(left in right)
            if isinstance(right, dict):
                return Boolean(left in right)
            raise PysonnetRuntimeError(
                f"Unsupported operand types for in: {self._stdlib._type(left)} and {self._stdlib._type(right)}"
            )
        if operator == ast.Binary.Operator.INDEX:
            value: Primitive
            if isinstance(left, Array) and isinstance(right, Number):
                try:
                    value = cast(Primitive, left[right.value])
                except IndexError:
                    raise PysonnetRuntimeError(f"Index out of range, not within [0, {len(left)})")
            elif isinstance(left, Object):
                if not isinstance(right, String):
                    raise PysonnetRuntimeError(f"Unsupported type for index: {type(right)}, expected string")
                try:
                    value = left[right]
                except KeyError:
                    raise PysonnetRuntimeError(f"Field does not exist: {right}")
            else:
                raise PysonnetRuntimeError(f"Unsupported operand types for index: {type(left)} and {type(right)}")
            return value
        raise PysonnetRuntimeError(f"Unsupported binary operator: {operator}")

    def _evaluate_apply(self, node: ast.Apply, context: Context) -> Primitive:
        callee = self(node.callee, context)
        if isinstance(callee, Lazy):
            callee = callee()
        if not isinstance(callee, Function):
            raise PysonnetRuntimeError(f"Cannot call {self._stdlib._type(callee)}")
        args = [
            self(arg.expr, context) if node.tailstrict else _make_lazy(self, arg.expr, context)
            for arg in node.args
            if arg.ident is None
        ]
        kwargs = {
            arg.ident.name: self(arg.expr) if node.tailstrict else _make_lazy(self, arg.expr, context)
            for arg in node.args
            if arg.ident is not None
        }
        return cast(Primitive, callee(*args, **kwargs))

    def _evaluate_apply_brace(self, node: ast.ApplyBrace, context: Context) -> Primitive:
        return self._evaluate_binary(ast.Binary(ast.Binary.Operator.ADD, node.left, node.right), context)

    def _evaluate_local(self, node: ast.LocalExpression, context: Context) -> Primitive:
        context = context.clone()
        for bind in node.binds:
            context.bindings[bind.ident.name] = _make_lazy(self, bind.expr, context)
        return self(node.expr, context)

    def _evaluate_if(self, node: ast.IfExpression, context: Context) -> Primitive:
        condition = self(node.condition, context)
        if isinstance(condition, Lazy):
            condition = condition()
        if not isinstance(condition, Boolean):
            raise PysonnetRuntimeError(f"Condition must be a boolean, not {self._stdlib._type(condition)}")
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
            default_kwargs = {
                name: _make_lazy(self, default_kwparam_nodes[name], context) for name in missing_kwparam_names
            }
            # update context
            context.bindings.update(kwargs)
            context.bindings.update(default_kwargs)
            return self(expr, context)

        return Function(_execute_function)

    def _evaluate_array_comprehension(self, node: ast.ArrayComprehension, context: Context) -> Array:
        iterable = self(node.forspec.expr, context)
        if isinstance(iterable, Lazy):
            iterable = iterable()
        if not isinstance(iterable, Array):
            raise PysonnetRuntimeError(f"Unexpected type {self._stdlib._type(iterable)}, expected array")
        context = context.clone()
        compspecs = [compspec for compspec in node.compspecs]
        while compspecs and isinstance(compspecs[0], ast.IfSpec):
            ifspec = cast(ast.IfSpec, compspecs.pop(0))
            for index, value in enumerate(iterable):
                context.bindings[node.forspec.ident.name] = value
                condition = self(ifspec.condition, context)
                if isinstance(condition, Lazy):
                    condition = condition()
                if not isinstance(condition, Boolean):
                    raise PysonnetRuntimeError(f"Unpexpected type {self._stdlib._type(condition)}, expected boolean")
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
        if isinstance(iterable, Lazy):
            iterable = iterable()
        if not isinstance(iterable, Array):
            raise PysonnetRuntimeError(f"Unexpected type {self._stdlib._type(iterable)}, expected array")
        context = context.clone()
        for local in node.locals_:
            context.bindings[local.bind.ident.name] = _make_lazy(self, local.bind.expr, context)
        compspecs = [compspec for compspec in node.compspecs]
        while compspecs and isinstance(compspecs[0], ast.IfSpec):
            ifspec = cast(ast.IfSpec, compspecs.pop(0))
            for index, value in enumerate(iterable):
                context.bindings[node.forspec.ident.name] = value
                condition = self(ifspec.condition, context)
                if isinstance(condition, Lazy):
                    condition = condition()
                if not isinstance(condition, Boolean):
                    raise PysonnetRuntimeError(f"Unpexpected type {self._stdlib._type(condition)}, expected boolean")
                if not condition:
                    iterable.pop(index)
        obj = Object()
        context.this = obj
        if context.dollar is None:
            context.dollar = obj
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
                if isinstance(key_, Lazy):
                    key_ = key_()
                if isinstance(key_, Null):
                    continue
                if not isinstance(key_, String):
                    raise PysonnetRuntimeError(f"Field name must be a string, not {self._stdlib._type(key)}")
                key = key_
                if key in obj:
                    raise PysonnetRuntimeError(f"Duplicate field name: {key}")
                value = self(node.value, context)
                obj.add_field(Object.Field(key, value))
        return obj

    def _evaluate_self(self, node: ast.Self, context: Context) -> Primitive:
        if context.this is None:
            raise PysonnetRuntimeError("Can't use self outside of an object.")
        return context.this

    def _evaluate_dollar(self, node: ast.Dollar, context: Context) -> Primitive:
        if context.dollar is None:
            raise PysonnetRuntimeError("No top-level object found.")
        return context.dollar

    def _evaluate_super(self, node: ast.Super, context: Context) -> Primitive:
        if context.super_ is None:
            raise PysonnetRuntimeError("Attempt to use super when there is no super class.")
        return context.super_

    def _evaluate_error(self, node: ast.Error, context: Context) -> Primitive:
        message = self(node.expr, context)
        raise PysonnetRuntimeError(str(message))

    def _evaluate_assert(self, node: ast.AssertExpression, context: Context) -> Primitive:
        condition = self(node.assert_.condition, context)
        if isinstance(condition, Lazy):
            condition = condition()
        if not isinstance(condition, Boolean):
            raise PysonnetRuntimeError(f"Unpexpected type {self._stdlib._type(condition)}, expected boolean")
        if not condition:
            message: Primitive
            if node.assert_.message is None:
                message = String("Assertion failed")
            else:
                message = self(node.assert_.message, context)
            raise PysonnetRuntimeError(str(message))
        return self(node.expr, context)

    def _evaluate_import(self, node: ast.Import, context: Context) -> Primitive:
        del context
        filename = self._rootdir / Path(node.filename)
        if not filename.exists():
            raise PysonnetRuntimeError(f"File not found: {filename}")
        if not filename.is_file():
            raise PysonnetRuntimeError(f"Not a file: {filename}")
        with filename.open() as f:
            jp = Parser(Lexer(f))
            ast = jp.parse()
        if not ast:
            raise PysonnetRuntimeError(f"Failed to parse {filename}")
        evaluator = Evaluator(
            filename,
            ext_vars=self._ext_vars,
            native_callbacks=self._native_callbacks,
        )
        return evaluator(ast)

    def _evaluate_importstr(self, node: ast.Importstr, context: Context) -> String:
        del context
        filename = self._rootdir / Path(node.filename)
        if not filename.exists():
            raise PysonnetRuntimeError(f"File not found: {filename}")
        if not filename.is_file():
            raise PysonnetRuntimeError(f"Not a file: {filename}")
        return String(filename.read_text())

    def _evaluate_importbin(self, node: ast.Importbin, context: Context) -> Array[Number[int]]:
        del context
        filename = self._rootdir / Path(node.filename)
        if not filename.exists():
            raise PysonnetRuntimeError(f"File not found: {filename}")
        if not filename.is_file():
            raise PysonnetRuntimeError(f"Not a file: {filename}")
        return Array([Number(b) for b in filename.read_bytes()])

    def __call__(self, node: ast.AST, context: Optional[Context] = None) -> Primitive:
        if context is None:
            context = Context()

        if isinstance(node, ast.LiteralAST):
            return self._evaluate_literal(node, context)

        if isinstance(node, ast.Self):
            return self._evaluate_self(node, context)

        if isinstance(node, ast.Dollar):
            return self._evaluate_dollar(node, context)

        if isinstance(node, ast.Super):
            return self._evaluate_super(node, context)

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

        if isinstance(node, ast.AssertExpression):
            return self._evaluate_assert(node, context)

        if isinstance(node, ast.Import):
            return self._evaluate_import(node, context)

        if isinstance(node, ast.Importbin):
            return self._evaluate_importbin(node, context)

        if isinstance(node, ast.Importstr):
            return self._evaluate_importstr(node, context)

        raise PysonnetRuntimeError(f"Unsupported type: {type(node)}")
