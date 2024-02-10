from __future__ import annotations

import enum
import json
from typing import Callable, Dict, Generic, List, NamedTuple, Optional, TypeVar, Union, overload

from pysonnet.types import JsonPrimitive

_Real_co = TypeVar("_Real_co", bound=Union[bool, int, float], covariant=True)
_Real_contra = TypeVar("_Real_contra", bound=Union[bool, int, float], contravariant=True)
_PrimitiveType = TypeVar("_PrimitiveType", bound="Primitive")


class Primitive:
    def to_json(self) -> JsonPrimitive:
        raise NotImplementedError


class Null(Primitive):
    def __str__(self) -> str:
        return "null"

    def to_json(self) -> None:
        return None


class Number(Generic[_Real_co], Primitive):
    def __init__(self, value: _Real_co) -> None:
        self.value: _Real_co = value

    @overload
    def __add__(self: Number[Union[bool, int]], other: Number[Union[bool, int]]) -> Number[int]:
        ...

    @overload
    def __add__(self: Number[Union[bool, int]], other: Number[float]) -> Number[float]:
        ...

    @overload
    def __add__(self: Number[float], other: Number[Union[bool, int]]) -> Number[float]:
        ...

    @overload
    def __add__(self: Number[float], other: Number[float]) -> Number[float]:
        ...

    def __add__(self, other: Number[Union[bool, int, float]]) -> Number[Union[int, float]]:
        return Number(self.value + other.value)

    @overload
    def __sub__(self: Number[Union[bool, int]], other: Number[Union[bool, int]]) -> Number[int]:
        ...

    @overload
    def __sub__(self: Number[Union[bool, int]], other: Number[float]) -> Number[float]:
        ...

    @overload
    def __sub__(self: Number[float], other: Number[Union[bool, int]]) -> Number[float]:
        ...

    @overload
    def __sub__(self: Number[float], other: Number[float]) -> Number[float]:
        ...

    def __sub__(self, other: Number[Union[bool, int, float]]) -> Number[Union[int, float]]:
        return Number(self.value - other.value)

    @overload
    def __mul__(self: Number[Union[bool, int]], other: Number[Union[bool, int]]) -> Number[int]:
        ...

    @overload
    def __mul__(self: Number[Union[bool, int]], other: Number[float]) -> Number[float]:
        ...

    @overload
    def __mul__(self: Number[float], other: Number[Union[bool, int]]) -> Number[float]:
        ...

    @overload
    def __mul__(self: Number[float], other: Number[float]) -> Number[float]:
        ...

    def __mul__(self, other: Number[Union[bool, int, float]]) -> Number[Union[int, float]]:
        return Number(self.value * other.value)

    @overload
    def __truediv__(self: Number[Union[bool, int]], other: Number[Union[bool, int]]) -> Number[float]:
        ...

    @overload
    def __truediv__(self: Number[Union[bool, int]], other: Number[float]) -> Number[float]:
        ...

    @overload
    def __truediv__(self: Number[float], other: Number[Union[bool, int]]) -> Number[float]:
        ...

    @overload
    def __truediv__(self: Number[float], other: Number[float]) -> Number[float]:
        ...

    def __truediv__(self, other: Number[Union[bool, int, float]]) -> Number[float]:
        return Number(self.value / other.value)

    @overload
    def __mod__(self: Number[Union[bool, int]], other: Number[Union[bool, int]]) -> Number[int]:
        ...

    @overload
    def __mod__(self: Number[Union[bool, int]], other: Number[float]) -> Number[float]:
        ...

    @overload
    def __mod__(self: Number[float], other: Number[Union[bool, int]]) -> Number[float]:
        ...

    @overload
    def __mod__(self: Number[float], other: Number[float]) -> Number[float]:
        ...

    def __mod__(self, other: Number[Union[bool, int, float]]) -> Number[Union[int, float]]:
        return Number(self.value % other.value)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Number):
            return NotImplemented
        return bool(self.value == other.value)

    def __ne__(self, other: object) -> bool:
        if not isinstance(other, Number):
            return NotImplemented
        return bool(self.value != other.value)

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, Number):
            return NotImplemented
        return bool(self.value < other.value)

    def __gt__(self, other: object) -> bool:
        if not isinstance(other, Number):
            return NotImplemented
        return bool(self.value > other.value)

    def __le__(self, other: object) -> bool:
        if not isinstance(other, Number):
            return NotImplemented
        return bool(self.value <= other.value)

    def __ge__(self, other: object) -> bool:
        if not isinstance(other, Number):
            return NotImplemented
        return bool(self.value >= other.value)

    def __abs__(self) -> Number[Union[int, float]]:
        return Number(abs(self.value))

    def __neg__(self) -> Number[Union[int, float]]:
        return Number(-self.value)

    def __bool__(self) -> bool:
        return bool(self.value)

    def __int__(self) -> int:
        return int(self.value)

    def __float__(self) -> float:
        return float(self.value)

    def __str__(self) -> str:
        return str(self.value)

    def __repr__(self) -> str:
        return f"Number({self.value!r})"

    def to_json(self) -> Union[bool, int, float]:
        return self.value


class Boolean(Number[bool]):
    ...


class String(str, Primitive):
    def __add__(self, other: Union[Number, String, Array, Object]) -> String:  # type: ignore[override]
        if not isinstance(other, String):
            other = String(json.dumps(other.to_json()))
        return String(super().__add__(other))

    def __mod__(self, other: Primitive) -> String:
        return String(super().__mod__(other))

    def to_json(self) -> str:
        return self


class Array(Generic[_PrimitiveType], List[_PrimitiveType], Primitive):
    def __add__(self, other: Array) -> Array:  # type: ignore[override]
        return Array(super().__add__(other))

    def to_json(self) -> List[JsonPrimitive]:
        return [item.to_json() for item in self]


class Object(Dict[String, Primitive], Primitive):
    class Visibility(enum.Enum):
        VISIBLE = enum.auto()
        HIDDEN = enum.auto()
        FORCE_VISIBLE = enum.auto()

    class Field(NamedTuple):
        key: String
        value: Primitive
        inherit: bool = False
        visibility: Optional[Object.Visibility] = None

    def __init__(self, *fields: Field) -> None:
        super().__init__(**{field.key: field.value for field in fields})
        self._inherits = {field.key: field.inherit for field in fields}
        self._visibilities = {field.key: field.visibility or Object.Visibility.VISIBLE for field in fields}

    def add(self, field: Field) -> Object:
        self[field.key] = field.value
        self._inherits[field.key] = field.inherit
        self._visibilities[field.key] = field.visibility or Object.Visibility.VISIBLE
        return self

    def inherit(self, key: String) -> bool:
        return self._inherits[key]

    def visibility(self, key: String) -> Object.Visibility:
        return self._visibilities[key]

    def __add__(self, other: Object) -> Object:
        raise NotImplementedError

    def to_json(self) -> Dict[str, JsonPrimitive]:
        return {key: value.to_json() for key, value in self.items() if self.visibility(key) != Object.Visibility.HIDDEN}


class Function(Generic[_PrimitiveType], Primitive):
    def __init__(self, func: Callable[..., _PrimitiveType]) -> None:
        self._func = func

    def __call__(self, *args: Primitive, **kwargs: Primitive) -> _PrimitiveType:
        return self._func(*args, **kwargs)


# Constants
NULL = Null()
TRUE = Boolean(True)
FALSE = Boolean(False)
