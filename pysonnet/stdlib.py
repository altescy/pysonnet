from typing import Final, TypeVar, Union

from pysonnet.errors import PysonnetRuntimeError
from pysonnet.objects import Array, Boolean, Function, Null, Number, Object, Primitive, String

_T = TypeVar("_T", bound=Primitive)
_T_co = TypeVar("_T_co", covariant=True, bound=Primitive)
_T_contra = TypeVar("_T_contra", contravariant=True, bound=Primitive)


def _type(value: Primitive) -> String:
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


def _length(value: Primitive) -> Number[int]:
    if isinstance(value, String):
        return Number(len(value))
    if isinstance(value, Array):
        return Number(len(value))
    if isinstance(value, Object):
        return Number(len(value))
    raise PysonnetRuntimeError(f"Cannot get length of {_type(value)}")


def _slice(
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


def _filter(func: Function, value: Array[_T]) -> Array[_T]:
    return Array([item for item in value if func(item)])


def _map(func: Function, value: Primitive) -> Primitive:
    if isinstance(value, Array):
        return Array(map(func, value))
    raise PysonnetRuntimeError(f"Cannot map over {_type(value)}")


def _make_array(size: int, func: Function[_T]) -> Array[_T]:
    return Array([func(Number(i)) for i in range(size)])


def _join(delimiter: String, value: Array[String]) -> String:
    return String(delimiter.join(value))


def _codepoint(value: String) -> Number[int]:
    return Number(ord(value))


def _abs(value: Number) -> Number:
    return abs(Number(value))  # type: ignore[type-var]


def _max(a: Number, b: Number) -> Number:
    return Number(max(a, b))


def _min(a: Number, b: Number) -> Number:
    return Number(min(a, b))


def _clamp(a: Number, minVal: Number, maxVal: Number) -> Number:
    return Number(max(min(a, maxVal), minVal))


STDLIB: Final = Object(
    Object.Field(String("type"), Function(_type)),
    Object.Field(String("length"), Function(_length)),
    Object.Field(String("slice"), Function(_slice)),
    Object.Field(String("map"), Function(_map)),
    Object.Field(String("makeArray"), Function(_make_array)),
    Object.Field(String("join"), Function(_join)),
    Object.Field(String("codepoint"), Function(_codepoint)),
    Object.Field(String("abs"), Function(_abs)),
    Object.Field(String("max"), Function(_max)),
    Object.Field(String("min"), Function(_min)),
    Object.Field(String("clamp"), Function(_clamp)),
)
