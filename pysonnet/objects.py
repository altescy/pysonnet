from __future__ import annotations

import copy
import enum
import json
from typing import Callable, Dict, Generic, List, NamedTuple, Optional, TypeVar, Union, overload

from pysonnet.types import JsonPrimitive

_Self = TypeVar("_Self", bound="Primitive")
_Real_co = TypeVar("_Real_co", bound=Union[bool, int, float], covariant=True)
_Real_contra = TypeVar("_Real_contra", bound=Union[bool, int, float], contravariant=True)
_PrimitiveType = TypeVar("_PrimitiveType", bound="Primitive")


class Primitive:
    def __str__(self) -> str:
        return json.dumps(self.to_json())

    def __repr__(self) -> str:
        return self.__str__()

    def to_json(self) -> JsonPrimitive:
        """Convert the object to a JSON-serializable object."" """
        raise NotImplementedError

    def clone(self: _Self) -> _Self:
        return copy.deepcopy(self)

    @staticmethod
    def from_json_primitive(value: JsonPrimitive) -> Primitive:
        if isinstance(value, bool):
            return Boolean(value)
        if isinstance(value, (int, float)):
            return Number(value)
        if isinstance(value, str):
            return String(value)
        if value is None:
            return Null()
        if isinstance(value, list):
            return Array([Primitive.from_json_primitive(v) for v in value])
        if isinstance(value, dict):
            return Object(*(Object.Field(key, Primitive.from_json_primitive(val)) for key, val in value.items()))
        raise ValueError(f"Invalid JSON primitive: {value}")


class Lazy(Primitive):
    def __init__(self, constructor: Callable[[], Primitive]) -> None:
        self._constructor = constructor

    def __call__(self) -> Primitive:
        value = self._constructor()
        while isinstance(value, Lazy):
            value = value()
        return value

    def __str__(self) -> str:
        value = self.to_json()
        if isinstance(value, str):
            return value
        return json.dumps(value)

    def __repr__(self) -> str:
        return f"Lazy({self._constructor})"

    def to_json(self) -> JsonPrimitive:
        return self().to_json()

    def clone(self) -> "Lazy":
        return self


class Null(Primitive):
    def to_json(self) -> None:
        return None


class Number(Generic[_Real_co], Primitive):
    def __init__(self, value: _Real_co) -> None:
        self.value: _Real_co = value

    @overload
    def __add__(self: Number[Union[bool, int]], other: Number[Union[bool, int]]) -> Number[int]: ...

    @overload
    def __add__(self: Number[Union[bool, int]], other: Number[float]) -> Number[float]: ...

    @overload
    def __add__(self: Number[float], other: Number[Union[bool, int]]) -> Number[float]: ...

    @overload
    def __add__(self: Number[float], other: Number[float]) -> Number[float]: ...

    @overload
    def __add__(self, other: String) -> String: ...

    def __add__(
        self, other: Union[Number[Union[bool, int, float]], String]
    ) -> Union[Number[Union[int, float]], String]:
        if isinstance(other, String):
            return String(json.dumps(self.to_json())) + other
        return Number(self.value + other.value)

    @overload
    def __sub__(self: Number[Union[bool, int]], other: Number[Union[bool, int]]) -> Number[int]: ...

    @overload
    def __sub__(self: Number[Union[bool, int]], other: Number[float]) -> Number[float]: ...

    @overload
    def __sub__(self: Number[float], other: Number[Union[bool, int]]) -> Number[float]: ...

    @overload
    def __sub__(self: Number[float], other: Number[float]) -> Number[float]: ...

    def __sub__(self, other: Number[Union[bool, int, float]]) -> Number[Union[int, float]]:
        return Number(self.value - other.value)

    @overload
    def __mul__(self: Number[Union[bool, int]], other: Number[Union[bool, int]]) -> Number[int]: ...

    @overload
    def __mul__(self: Number[Union[bool, int]], other: Number[float]) -> Number[float]: ...

    @overload
    def __mul__(self: Number[float], other: Number[Union[bool, int]]) -> Number[float]: ...

    @overload
    def __mul__(self: Number[float], other: Number[float]) -> Number[float]: ...

    def __mul__(self, other: Number[Union[bool, int, float]]) -> Number[Union[int, float]]:
        return Number(self.value * other.value)

    @overload
    def __truediv__(self: Number[Union[bool, int]], other: Number[Union[bool, int]]) -> Number[float]: ...

    @overload
    def __truediv__(self: Number[Union[bool, int]], other: Number[float]) -> Number[float]: ...

    @overload
    def __truediv__(self: Number[float], other: Number[Union[bool, int]]) -> Number[float]: ...

    @overload
    def __truediv__(self: Number[float], other: Number[float]) -> Number[float]: ...

    def __truediv__(self, other: Number[Union[bool, int, float]]) -> Number[float]:
        return Number(self.value / other.value)

    @overload
    def __mod__(self: Number[Union[bool, int]], other: Number[Union[bool, int]]) -> Number[int]: ...

    @overload
    def __mod__(self: Number[Union[bool, int]], other: Number[float]) -> Number[float]: ...

    @overload
    def __mod__(self: Number[float], other: Number[Union[bool, int]]) -> Number[float]: ...

    @overload
    def __mod__(self: Number[float], other: Number[float]) -> Number[float]: ...

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

    def to_json(self) -> Union[bool, int, float]:
        return self.value


class Boolean(Number[bool]): ...


class String(str, Primitive):
    def __add__(self, other: Union[Number, String, Array, Object]) -> String:  # type: ignore[override]
        if not isinstance(other, String):
            other = String(json.dumps(other.to_json()))
        return String(super().__add__(other))

    def __radd__(self, other: Union[Number, String, Array, Object]) -> String:  # type: ignore[override]
        if not isinstance(other, String):
            other = String(json.dumps(other.to_json()))
        return other + self

    def __mod__(self, other: Primitive) -> String:
        if isinstance(other, Lazy):
            other = other()
        if isinstance(other, Number):
            other = other.to_json()  # type: ignore[assignment]
        if isinstance(other, Array):
            other = tuple(other)  # type: ignore[assignment]
        return String(super().__mod__(other))

    def to_json(self) -> str:
        return str(self)


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
        self._properties = {
            field.key: (field.inherit, field.visibility or Object.Visibility.VISIBLE) for field in fields
        }

    def add_field(self, field: Field) -> None:
        key = field.key
        value = field.value
        inherit = field.inherit
        visibility = field.visibility or Object.Visibility.VISIBLE
        if key in self:
            if inherit:
                current_value = self[key]

                def _add(left: Primitive = current_value, right: Primitive = value) -> Primitive:
                    if isinstance(left, Lazy):
                        left = left()
                    if isinstance(right, Lazy):
                        right = right()
                    return left + right  # type: ignore[operator, no-any-return]

                value = Lazy(_add)
            if self.hidden(key) and visibility != Object.Visibility.FORCE_VISIBLE:
                visibility = Object.Visibility.HIDDEN
            inherit = self.inherit(key) and inherit
        self[key] = value
        self._properties[key] = (inherit, visibility)

    def get_field(self, key: String) -> Optional[Field]:
        if key in self:
            return Object.Field(key, self[key], *self._properties[key])
        return None

    def inherit(self, key: String) -> bool:
        return self._properties[key][0]

    def visibility(self, key: String) -> Object.Visibility:
        return self._properties[key][1]

    def hidden(self, key: String) -> bool:
        return self.visibility(key) == Object.Visibility.HIDDEN

    @property
    def fields(self) -> List[Field]:
        return [Object.Field(key, value, self.inherit(key), self.visibility(key)) for key, value in self.items()]

    @overload
    def __add__(self, other: Object) -> Object:  # type: ignore[override]
        ...

    @overload
    def __add__(self, other: String) -> String:  # type: ignore[override]
        ...

    def __add__(self, other: Union[Object, String]) -> Union[Object, String]:  # type: ignore[override]
        if isinstance(other, String):
            return String(json.dumps(self.to_json())) + other
        obj = self
        for field in other.fields:
            obj.add_field(field)
        return obj

    def to_json(self) -> Dict[str, JsonPrimitive]:
        return {key: value.to_json() for key, value in self.items() if self.visibility(key) != Object.Visibility.HIDDEN}


class Function(Generic[_PrimitiveType], Primitive):
    def __init__(self, func: Callable[..., _PrimitiveType]) -> None:
        self._func = func

    def __call__(self, *args: Primitive, **kwargs: Primitive) -> _PrimitiveType:
        return self._func(*args, **kwargs)

    def __str__(self) -> str:
        raise NotImplementedError

    def to_json(self) -> None:
        raise NotImplementedError

    @staticmethod
    def from_native_function(func: Callable[..., JsonPrimitive]) -> Function[Primitive]:
        def wrapper(*args: Primitive, **kwargs: Primitive) -> Primitive:
            native_args = [arg.to_json() for arg in args]
            native_kwargs = {key: value.to_json() for key, value in kwargs.items()}
            return Primitive.from_json_primitive(func(*native_args, **native_kwargs))

        return Function(wrapper)


# Constants
NULL = Null()
TRUE = Boolean(True)
FALSE = Boolean(False)
