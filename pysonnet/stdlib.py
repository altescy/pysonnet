from typing import Mapping, TypeVar, Union

from pysonnet.errors import PysonnetRuntimeError
from pysonnet.objects import NULL, Array, Boolean, Function, Null, Number, Object, Primitive, String

_T = TypeVar("_T", bound=Primitive)
_T_co = TypeVar("_T_co", covariant=True, bound=Primitive)
_T_contra = TypeVar("_T_contra", contravariant=True, bound=Primitive)


class StdLib:
    def __init__(self, ext_vars: Mapping[str, str] = {}) -> None:
        self._ext_vars = ext_vars

    def _ext_var(self, name: String) -> String:
        if name not in self._ext_vars:
            raise PysonnetRuntimeError(f"Undefined external variable: {name}")
        return String(self._ext_vars[name])

    def _type(self, value: Primitive) -> String:
        if isinstance(value, Null):
            return String("null")
        if isinstance(value, Boolean):
            return String("boolean")
        if isinstance(value, Number):
            return String("number")
        if isinstance(value, String):
            return String("string")
        if isinstance(value, Array):
            return String("array")
        if isinstance(value, Object):
            return String("object")
        if isinstance(value, Function):
            return String("function")
        raise TypeError(type(value))

    def _length(self, value: Primitive) -> Number[int]:
        if isinstance(value, String):
            return Number(len(value))
        if isinstance(value, Array):
            return Number(len(value))
        if isinstance(value, Object):
            return Number(len(value))
        raise PysonnetRuntimeError(f"Cannot get length of {self._type(value)}")

    def _slice(
        self,
        iterable: Array[_T],
        start: Union[Number[int], Null],
        end: Union[Number[int], Null],
        step: Union[Number[int], Null],
    ) -> Array[_T]:
        s = slice(
            start.value if isinstance(start, Number) else None,
            end.value if isinstance(end, Number) else None,
            step.value if isinstance(step, Number) else None,
        )
        return Array(iterable[s])

    def _range(
        self,
        start: Number[int],
        end: Number[int],
        step: Union[Number[int], Null] = NULL,
    ) -> Array[Number[int]]:
        return Array(
            [
                Number(i)
                for i in range(
                    start.value,
                    end.value + 1,
                    step.value if isinstance(step, Number) else 1,
                )
            ]
        )

    def _filter(self, func: Function, value: Array[_T]) -> Array[_T]:
        return Array([item for item in value if func(item)])

    def _map(self, func: Function, value: Primitive) -> Primitive:
        if isinstance(value, Array):
            return Array(map(func, value))
        raise PysonnetRuntimeError(f"Cannot map over {self._type(value)}")

    def _make_array(self, size: int, func: Function[_T]) -> Array[_T]:
        return Array([func(Number(i)) for i in range(size)])

    def _join(self, delimiter: String, value: Array[String]) -> String:
        return String(delimiter.join(value))

    def _codepoint(self, value: String) -> Number[int]:
        return Number(ord(value))

    def _abs(self, value: Number) -> Number:
        return abs(Number(value))  # type: ignore[type-var]

    def _max(self, a: Number, b: Number) -> Number:
        return Number(max(a, b))

    def _min(self, a: Number, b: Number) -> Number:
        return Number(min(a, b))

    def _clamp(self, a: Number, minVal: Number, maxVal: Number) -> Number:
        return Number(max(min(a, maxVal), minVal))

    def as_object(self) -> Object:
        return Object(
            Object.Field(String("extVar"), Function(self._ext_var)),
            Object.Field(String("type"), Function(self._type)),
            Object.Field(String("length"), Function(self._length)),
            Object.Field(String("slice"), Function(self._slice)),
            Object.Field(String("range"), Function(self._range)),
            Object.Field(String("map"), Function(self._map)),
            Object.Field(String("makeArray"), Function(self._make_array)),
            Object.Field(String("join"), Function(self._join)),
            Object.Field(String("codepoint"), Function(self._codepoint)),
            Object.Field(String("abs"), Function(self._abs)),
            Object.Field(String("max"), Function(self._max)),
            Object.Field(String("min"), Function(self._min)),
            Object.Field(String("clamp"), Function(self._clamp)),
        )
