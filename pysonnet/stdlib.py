import base64
import hashlib
import inspect
import itertools
import json
import math
import shlex
import sys
from functools import reduce, wraps
from typing import Any, Callable, List, Mapping, Set, TypeVar, Union

from pysonnet.errors import PysonnetRuntimeError
from pysonnet.objects import (
    FALSE,
    NULL,
    TRUE,
    Array,
    Boolean,
    Function,
    Lazy,
    Null,
    Number,
    Object,
    Optional,
    Primitive,
    String,
)
from pysonnet.types import JsonPrimitive

_T = TypeVar("_T", bound=Primitive)
_T_co = TypeVar("_T_co", covariant=True, bound=Primitive)
_T_contra = TypeVar("_T_contra", contravariant=True, bound=Primitive)


def _eval_args(func: Callable[..., _T]) -> Callable[..., _T]:
    signature = inspect.signature(func)

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> _T:
        # TODO: check types

        # Some parameter names has trailing underscores to avoid conflicts with
        # Python keywords (e.g. from_).
        kwargs = {k if k in signature.parameters else k + "_": v for k, v in kwargs.items()}

        try:
            bound_args = signature.bind(*args, **kwargs)
            bound_args.apply_defaults()
            params = bound_args.arguments
        except TypeError:
            raise PysonnetRuntimeError(f"Invalid arguments of {func.__name__}")
        evaluated_params = {k: v() if isinstance(v, Lazy) else v for k, v in params.items()}
        return func(**evaluated_params)

    return wrapper


class StdLib:
    def __init__(
        self,
        ext_vars: Mapping[str, str] = {},
        native_callbacks: Mapping[str, Callable[..., Primitive]] = {},
    ) -> None:
        self._ext_vars = ext_vars
        self._native_callbacks = native_callbacks

    @_eval_args
    def _ext_var(self, x: String) -> String:
        if x not in self._ext_vars:
            raise PysonnetRuntimeError(f"Undefined external variable: {x}")
        return String(self._ext_vars[x])

    @_eval_args
    def _native(self, name: String) -> Function[Primitive]:
        if name not in self._native_callbacks:
            raise PysonnetRuntimeError(f"Undefined native callback: {name}")
        return Function(self._native_callbacks[name])

    @_eval_args
    def _type(self, x: Primitive) -> String:
        if isinstance(x, Null):
            return String("null")
        if isinstance(x, Boolean):
            return String("boolean")
        if isinstance(x, Number):
            return String("number")
        if isinstance(x, String):
            return String("string")
        if isinstance(x, Array):
            return String("array")
        if isinstance(x, Object):
            return String("object")
        if isinstance(x, Function):
            return String("function")
        raise TypeError(type(x))

    @_eval_args
    def _length(self, x: Primitive) -> Number[int]:
        if isinstance(x, String):
            return Number(len(x))
        if isinstance(x, Array):
            return Number(len(x))
        if isinstance(x, Object):
            return Number(len(x))
        raise PysonnetRuntimeError(f"Cannot get length of {self._type(x)}")

    @_eval_args
    def _codepoint(self, value: String) -> Number[int]:
        return Number(ord(value))

    @_eval_args
    def _char(self, n: Number[int]) -> String:
        return String(chr(n.value))

    @_eval_args
    def _substr(self, str: String, from_: Number[int], len: Number[int]) -> String:
        return String(str[from_.value : from_.value + len.value])

    @_eval_args
    def _find_substr(self, pat: String, str: String) -> Array[Number[int]]:
        return Array([Number(i) for i in range(len(str) - len(pat) + 1) if str[i : i + len(pat)] == pat])

    @_eval_args
    def _startsWith(self, a: String, b: String) -> Boolean:
        return Boolean(a.startswith(b))

    @_eval_args
    def _endsWith(self, a: String, b: String) -> Boolean:
        return Boolean(a.endswith(b))

    @_eval_args
    def _strip_chars(self, str: String, chars: String) -> String:
        return String(str.strip(chars))

    @_eval_args
    def _lstrip_chars(self, str: String, chars: String) -> String:
        return String(str.lstrip(chars))

    @_eval_args
    def _rstrip_chars(self, str: String, chars: String) -> String:
        return String(str.rstrip(chars))

    @_eval_args
    def _split(self, str: String, c: String) -> Array[String]:
        return Array([String(part) for part in str.split(c)])

    @_eval_args
    def _split_limit(self, str: String, c: String, maxsplits: Number[int]) -> Array[String]:
        return Array([String(part) for part in str.split(c, maxsplits.value)])

    @_eval_args
    def _split_limit_r(self, str: String, c: String, maxsplits: Number[int]) -> Array[String]:
        return Array([String(part) for part in str.rsplit(c, maxsplits.value)])

    @_eval_args
    def _str_replace(self, str: String, from_: String, to: String) -> String:
        return String(str.replace(from_, to))

    @_eval_args
    def _is_empty(self, str: String) -> Boolean:
        return TRUE if len(str) == 0 else FALSE

    @_eval_args
    def _trim(self, str: String) -> String:
        return String(str.strip())

    @_eval_args
    def _equals_ignore_case(self, str1: String, str2: String) -> Boolean:
        return Boolean(str1.lower() == str2.lower())

    @_eval_args
    def _ascii_upper(self, str: String) -> String:
        return String(str.upper())

    @_eval_args
    def _ascii_lower(self, str: String) -> String:
        return String(str.lower())

    @_eval_args
    def _string_chars(self, str: String) -> Array[String]:
        return Array([String(c) for c in str])

    @_eval_args
    def _format(self, str: String, vals: Union[Null, Number, String, Array, Object]) -> String:
        return str % vals

    @_eval_args
    def _escape_string_bash(self, str: String) -> String:
        return String(shlex.quote(str))

    @_eval_args
    def _escape_string_dollars(self, str: String) -> String:
        return String(str.replace("$", "$$"))

    @_eval_args
    def _escape_string_json(self, str: String) -> String:
        return String(json.dumps(str))

    @_eval_args
    def _escape_string_xml(self, str: String) -> String:
        charmap = {
            "<": "&lt;",
            ">": "&gt;",
            "&": "&amp;",
            '"': "&quot;",
            "'": "&apos;",
        }
        return String("".join(charmap.get(c, c) for c in str))

    @_eval_args
    def _mod(self, a: Number, b: Number) -> Number:
        return Number(a.value % b.value)

    @_eval_args
    def _abs(self, n: Number) -> Number:
        return abs(Number(n.value))  # type: ignore[type-var]

    @_eval_args
    def _sign(self, n: Number) -> Number:
        return Number(1 if n.value > 0 else -1 if n.value < 0 else 0)

    @_eval_args
    def _max(self, a: Number, b: Number) -> Number:
        return Number(max(a.value, b.value))

    @_eval_args
    def _min(self, a: Number, b: Number) -> Number:
        return Number(min(a.value, b.value))

    @_eval_args
    def _pow(self, x: Number, n: Number[Union[int, float]]) -> Number:
        return Number(x.value**n.value)

    @_eval_args
    def _exp(self, x: Number) -> Number:
        return Number(math.exp(x.value))

    @_eval_args
    def _log(self, x: Number) -> Number:
        return Number(math.log(x.value))

    @_eval_args
    def _exponent(self, x: Number) -> Number:
        return Number(math.frexp(x.value)[1])

    @_eval_args
    def _mantissa(self, x: Number) -> Number:
        return Number(math.frexp(x.value)[0])

    @_eval_args
    def _floor(self, x: Number) -> Number:
        return Number(math.floor(x.value))

    @_eval_args
    def _ceil(self, x: Number) -> Number:
        return Number(math.ceil(x.value))

    @_eval_args
    def _sqrt(self, x: Number) -> Number:
        return Number(math.sqrt(x.value))

    @_eval_args
    def _sin(self, x: Number) -> Number:
        return Number(math.sin(x.value))

    @_eval_args
    def _cos(self, x: Number) -> Number:
        return Number(math.cos(x.value))

    @_eval_args
    def _tan(self, x: Number) -> Number:
        return Number(math.tan(x.value))

    @_eval_args
    def _asin(self, x: Number) -> Number:
        return Number(math.asin(x.value))

    @_eval_args
    def _acos(self, x: Number) -> Number:
        return Number(math.acos(x.value))

    @_eval_args
    def _atan(self, x: Number) -> Number:
        return Number(math.atan(x.value))

    @_eval_args
    def _round(self, x: Number) -> Number:
        return Number(round(x.value))

    @_eval_args
    def _is_even(self, x: Number) -> Boolean:
        return Boolean(x.value % 2 == 0)

    @_eval_args
    def _is_odd(self, x: Number) -> Boolean:
        return Boolean(x.value % 2 != 0)

    @_eval_args
    def _is_integer(self, x: Number) -> Boolean:
        return Boolean(type(x.value) is int)

    @_eval_args
    def _is_decimal(self, x: Number) -> Boolean:
        return Boolean(type(x.value) is float)

    @_eval_args
    def _clamp(self, a: Number, minVal: Number, maxVal: Number) -> Number:
        return Number(max(min(a, maxVal), minVal))

    @_eval_args
    def _assert_equal(self, a: Primitive, b: Primitive) -> Boolean:
        if a != b:
            raise PysonnetRuntimeError(f"Assertion failed: {a} != {b}")
        return TRUE

    @_eval_args
    def _to_string(self, a: Primitive) -> String:
        return String(a)

    @_eval_args
    def _trace(self, str: String, rest: _T) -> _T:
        print("TRACE:", str, file=sys.stderr)
        return rest

    @_eval_args
    def _prune(self, a: Primitive) -> Primitive:
        def is_empty(obj: Primitive) -> bool:
            if isinstance(obj, Lazy):
                obj = obj()
            if isinstance(obj, Null):
                return True
            if isinstance(obj, Array):
                return len(obj) == 0
            if isinstance(obj, Object):
                return len(obj) == 0 or all(is_empty(field.value) for field in obj.fields)
            print("is_empty", obj, type(obj))
            return False

        def prune_recursively(obj: Primitive) -> Primitive:
            if isinstance(obj, Lazy):
                obj = obj()
            if isinstance(obj, Array):
                obj = Array([prune_recursively(item) for item in obj if not is_empty(item)])
                obj = Array([item for item in obj if not is_empty(item)])
            if isinstance(obj, Object):
                for field in obj.fields:
                    print(field.key, field.value, is_empty(field.value))
                obj = Object(
                    *[
                        Object.Field(
                            field.key,
                            prune_recursively(field.value),
                            field.inherit,
                            field.visibility,
                        )
                        for field in obj.fields
                        if not is_empty(field.value)
                    ]
                )
                obj = Object(
                    *[
                        Object.Field(
                            field.key,
                            field.value,
                            field.inherit,
                            field.visibility,
                        )
                        for field in obj.fields
                        if not is_empty(field.value)
                    ]
                )
            return obj

        return prune_recursively(a)

    @_eval_args
    def _parse_int(self, str: String) -> Number[int]:
        return Number(int(str))

    @_eval_args
    def _parse_octal(self, str: String) -> Number[int]:
        return Number(int(str, 8))

    @_eval_args
    def _parse_hex(self, str: String) -> Number[int]:
        return Number(int(str, 16))

    @_eval_args
    def _parse_json(self, str: String) -> Primitive:
        return Primitive.from_json_primitive(json.loads(str))

    @_eval_args
    def _encode_utf8(self, str: String) -> Array[Number[int]]:
        return Array([Number(ord(c)) for c in str])

    @_eval_args
    def _decode_utf8(self, arr: Array[Number[int]]) -> String:
        return String("".join(chr(i.value) for i in arr))

    @_eval_args
    def _manifest_ini(self, ini: Object) -> String:
        def body_lines(body: Primitive) -> Array[String]:
            if isinstance(body, Lazy):
                body = body()
            if not isinstance(body, Object):
                raise PysonnetRuntimeError("Invalid data format")
            lines: List[str] = []
            for key, val in sorted(body.items()):
                if isinstance(val, Lazy):
                    val = val()
                if isinstance(val, Array):
                    lines.extend(f"{key} = {item}" for item in val)
                else:
                    lines.append(f"{key} = {val}")
            return Array([String(line.strip()) for line in lines])

        def section_lines(name: str, body: Primitive) -> Array[String]:
            if isinstance(body, Lazy):
                body = body()
            if not isinstance(body, Object):
                raise PysonnetRuntimeError("Invalid data format")
            return Array([String(f"[{name}]")] + body_lines(body))

        main_obj = ini.get(String("main"), Object())
        sections_obj = ini.get(String("sections"), Object())
        if isinstance(main_obj, Lazy):
            main_obj = main_obj()
        if isinstance(sections_obj, Lazy):
            sections_obj = sections_obj()
        if not isinstance(main_obj, Object) or not isinstance(sections_obj, Object):
            raise PysonnetRuntimeError("Invalid data format")

        main = body_lines(main_obj)
        sections = Array([line for name, body in sorted(sections_obj.items()) for line in section_lines(name, body)])
        return String("\n".join(main + sections))

    @_eval_args
    def _manifest_python(self, v: Primitive) -> String:
        return String(repr(v.to_json()))

    @_eval_args
    def _manifest_python_vars(self, conf: Object) -> String:
        lines = [f"{key} = {repr(val.to_json())}" for key, val in conf.items()]
        return String("\n".join(lines))

    @_eval_args
    def _manifest_json_ex(
        self,
        value: Primitive,
        indent: String,
        newline: String = String("\n"),
        key_val_sep: String = String(": "),
    ) -> String:
        return String(
            json.dumps(
                value.to_json(),
                indent=str(indent),
                separators=(",", str(key_val_sep)),
                sort_keys=True,
                ensure_ascii=False,
            )
        )

    @_eval_args
    def _manifest_json(self, value: Primitive) -> String:
        return String(
            json.dumps(
                value.to_json(),
                indent=4,
                separators=(",", ": "),
                sort_keys=True,
                ensure_ascii=False,
            )
        )

    @_eval_args
    def _manifest_json_minified(self, value: Primitive) -> String:
        return String(
            json.dumps(
                value.to_json(),
                indent=None,
                separators=(",", ":"),
                sort_keys=True,
                ensure_ascii=False,
            )
        )

    @_eval_args
    def _make_array(self, size: int, func: Function[_T]) -> Array[_T]:
        return Array([func(Number(i)) for i in range(size)])

    @_eval_args
    def _member(self, arr: Union[Array, String], x: Primitive) -> Boolean:
        x_json = x.to_json()
        return Boolean(any(v if isinstance(v, str) else v.to_json() == x_json for v in arr))

    @_eval_args
    def _count(self, value: Primitive, arr: Union[Array, String]) -> Number[int]:
        value_json = value.to_json()
        return Number(sum(v if isinstance(v, str) else v.to_json() == value_json for v in arr))

    @_eval_args
    def _find(self, value: Primitive, arr: Union[Array, String]) -> Array[Number[int]]:
        value_json = value.to_json()
        return Array([Number(i) for i, v in enumerate(arr) if v.to_json() == value_json])

    @_eval_args
    def _map(self, func: Function, arr: Union[String, Array]) -> Array:
        if isinstance(arr, String):
            return Array([func(String(c)) for c in arr])
        return Array(map(func, arr))

    @_eval_args
    def _map_with_index(self, func: Function, arr: Primitive) -> Primitive:
        if isinstance(arr, Array):
            return Array(itertools.starmap(Function(lambda i, v: func(Number(i), v)), enumerate(arr)))
        raise PysonnetRuntimeError(f"Cannot map over {self._type(arr)}")

    @_eval_args
    def _filter(self, func: Function, arr: Array[_T]) -> Array[_T]:
        return Array([item for item in arr if func(item)])

    @_eval_args
    def _filter_map(self, filter_func: Function, map_func: Function, arr: Array) -> Array:
        return Array([map_func(item) for item in arr if filter_func(item)])

    @_eval_args
    def _flat_map(self, func: Function, arr: Union[String, Array]) -> Union[String, Array]:
        result: List[Primitive] = []
        for value in arr:
            if isinstance(value, str):
                value = String(value)
            out = func(value)
            if not isinstance(out, type(arr)):
                raise PysonnetRuntimeError(f"Unexpected type {type(out)}, expected {type(arr)}")
            result.extend(out)
        if isinstance(arr, String):
            result_string = ""
            for val in result:
                if not isinstance(val, str):
                    raise PysonnetRuntimeError(f"Unexpected type {type(val)}, expected String")
                result_string += val
            return String(result_string)
        return Array(result)

    @_eval_args
    def _foldl(self, func: Function, arr: Array[_T], init: _T) -> _T:
        return reduce(func, arr, init)

    @_eval_args
    def _foldr(self, func: Function, arr: Array[_T], init: _T) -> _T:
        return reduce(func, reversed(arr), init)

    @_eval_args
    def _range(
        self,
        from_: Number[int],
        to: Number[int],
        step: Union[Number[int], Null] = NULL,
    ) -> Array[Number[int]]:
        return Array(
            [
                Number(i)
                for i in range(
                    from_.value,
                    to.value + 1,
                    step.value if isinstance(step, Number) else 1,
                )
            ]
        )

    @_eval_args
    def _repeat(self, what: Union[String, Array], count: Number[int]) -> Union[String, Array]:
        if isinstance(what, String):
            return String("".join(itertools.repeat(what, count.value)))
        return Array([v for _ in range(count.value) for v in what])

    @_eval_args
    def _slice(
        self,
        indexable: Union[String, Array[_T]],
        index: Union[Number[int], Null],
        end: Union[Number[int], Null],
        step: Union[Number[int], Null],
    ) -> Union[String, Array[_T]]:
        s = slice(
            index.value if isinstance(index, Number) else None,
            end.value if isinstance(end, Number) else None,
            step.value if isinstance(step, Number) else None,
        )
        if isinstance(indexable, String):
            return String(indexable[s])
        return Array(indexable[s])

    @_eval_args
    def _join(self, sep: Union[String, Array], arr: Array) -> Union[String, Array]:
        results: List[Primitive] = []
        for i, value in enumerate(arr):
            if type(sep) is not type(value):
                raise PysonnetRuntimeError(f"Unexpected type {type(value)}, expected {type(sep)}")
            if i > 0:
                results += sep if isinstance(sep, Array) else [sep]
            results += list(value) if isinstance(value, Array) else [value]
        if isinstance(sep, String):
            return String("".join(str(val) for val in results))
        return Array(results)

    @_eval_args
    def _lines(self, arr: Array[String]) -> String:
        return String("\n".join(arr) + "\n")

    @_eval_args
    def _flatten_arrays(self, arr: Array[Array[_T]]) -> Array[_T]:
        return Array([val for inner in arr for val in inner])

    @_eval_args
    def _flatten_deep_array(self, value: Array) -> Array:
        def flatten_recuesively(x: Array) -> Array:
            results: List[Primitive] = []
            for val in x:
                if isinstance(val, Array):
                    results += list(flatten_recuesively(val))
                else:
                    results.append(val)
            return Array(results)

        return flatten_recuesively(value)

    @_eval_args
    def _reverse(self, arrs: Union[String, Array]) -> Union[String, Array]:
        if isinstance(arrs, String):
            return String(arrs[::-1])
        return Array(arrs[::-1])

    @_eval_args
    def _sort(self, arr: Array[_T], keyF: Optional[Function] = None) -> Array[_T]:
        def key(x: Primitive) -> Primitive:
            if keyF is None:
                return x
            if isinstance(x, Lazy):
                x = x()
            o: Primitive = keyF(x)
            if isinstance(o, Lazy):
                o = o()
            return o

        return Array(sorted(arr, key=key))  # type: ignore

    @_eval_args
    def _uniq(self, arr: Array[_T], keyF: Optional[Function] = None) -> Array[_T]:
        def get_key(x: Primitive) -> JsonPrimitive:
            if keyF is None:
                return x.to_json()
            if isinstance(x, Lazy):
                x = x()
            o: Primitive = keyF(x)
            if isinstance(o, Lazy):
                o = o()
            return o.to_json()

        seen: Set[JsonPrimitive] = set()
        results: List[_T] = []
        for val in arr:
            key = get_key(val)
            if key in seen:
                continue
            seen.add(key)
            results.append(val)
        return Array(results)

    @_eval_args
    def _all(self, arr: Array[Boolean]) -> Boolean:
        if not all(isinstance(v, Boolean) for v in arr):
            raise PysonnetRuntimeError("All values must be boolean")
        return Boolean(all(v.to_json() for v in arr))

    @_eval_args
    def _any(self, arr: Array[Boolean]) -> Boolean:
        if not all(isinstance(v, Boolean) for v in arr):
            raise PysonnetRuntimeError("All values must be boolean")
        return Boolean(any(v.to_json() for v in arr))

    @_eval_args
    def _sum(self, arr: Array[Number]) -> Number:
        return Number(sum(v.value for v in arr))

    @_eval_args
    def _contains(self, arr: Array[_T], elem: _T) -> Boolean:
        return Boolean(any(v == elem for v in arr))

    @_eval_args
    def _avg(self, arr: Array[Number]) -> Number:
        if not arr:
            raise PysonnetRuntimeError("Cannot calculate average of an empty array.")
        return Number(sum(v.value for v in arr) / len(arr))

    @_eval_args
    def _remove(self, arr: Array[_T], elem: _T) -> Array[_T]:
        index = -1
        for i, value in enumerate(arr):
            if value == elem:
                index = i
                break
        return Array([v for i, v in enumerate(arr) if i != index])

    @_eval_args
    def _remove_at(self, arr: Array[_T], idx: Number[int]) -> Array[_T]:
        return Array([v for i, v in enumerate(arr) if i != idx.value])

    @_eval_args
    def _set(self, arr: Array[_T], keyF: Optional[Function] = None) -> Array[_T]:
        return self._uniq(self._sort(arr, keyF), keyF)

    @_eval_args
    def _set_inter(self, a: Array, b: Array, keyF: Optional[Function] = None) -> Array:
        set_a = {}
        set_b = {}
        for val in a:
            key = (keyF(val) if keyF else val).to_json()
            if key not in set_a:
                set_a[key] = val
        for val in b:
            key = (keyF(val) if keyF else val).to_json()
            if key not in set_b:
                set_b[key] = val
        inter_keys = sorted(set(set_a.keys()) & set(set_b.keys()))
        return Array([set_a[key] for key in inter_keys])

    @_eval_args
    def _set_union(self, a: Array, b: Array, keyF: Optional[Function] = None) -> Array:
        set_a = {}
        set_b = {}
        for val in a:
            key = (keyF(val) if keyF else val).to_json()
            if key not in set_a:
                set_a[key] = val
        for val in b:
            key = (keyF(val) if keyF else val).to_json()
            if key not in set_b:
                set_b[key] = val
        union_keys = sorted(set(set_a.keys()) | set(set_b.keys()))
        return Array([set_a[key] if key in set_a else set_b[key] for key in union_keys])

    @_eval_args
    def _set_diff(self, a: Array, b: Array, keyF: Optional[Function] = None) -> Array:
        set_a = {}
        set_b = {}
        for val in a:
            key = (keyF(val) if keyF else val).to_json()
            if key not in set_a:
                set_a[key] = val
        for val in b:
            key = (keyF(val) if keyF else val).to_json()
            if key not in set_b:
                set_b[key] = val
        diff_keys = sorted(set(set_a.keys()) - set(set_b.keys()))
        return Array([set_a[key] for key in diff_keys])

    @_eval_args
    def _set_member(self, x: _T, arr: Array[_T], keyF: Optional[Function] = None) -> Boolean:
        set_arr = {}
        for val in arr:
            key = (keyF(val) if keyF else val).to_json()
            set_arr[key] = val
        key_x = (keyF(x) if keyF else x).to_json()
        return Boolean(key_x in set_arr)

    @_eval_args
    def _get(
        self,
        o: Object,
        f: String,
        default: Primitive = NULL,
        inc_hidden: Boolean = TRUE,
    ) -> Primitive:
        value = o.get(f)
        if value is None or (not inc_hidden and o.hidden(f)):
            return default
        return value

    @_eval_args
    def _object_has(self, o: Object, f: String) -> Boolean:
        field = o.get_field(f)
        return Boolean(field is not None and field.visibility != Object.Visibility.HIDDEN)

    @_eval_args
    def _object_fields(self, o: Object) -> Array[String]:
        return Array([f.key for f in o.fields if f.visibility != Object.Visibility.HIDDEN])

    @_eval_args
    def _object_values(self, o: Object) -> Array[Primitive]:
        return Array([f.value for f in o.fields if f.visibility != Object.Visibility.HIDDEN])

    @_eval_args
    def _object_keys_values(self, o: Object) -> Array[Object]:
        return Array(
            [
                Object(Object.Field(String("key"), f.key), Object.Field(String("value"), f.value))
                for f in o.fields
                if f.visibility != Object.Visibility.HIDDEN
            ]
        )

    @_eval_args
    def _object_has_all(self, o: Object, f: String) -> Boolean:
        return Boolean(o.get_field(f) is not None)

    @_eval_args
    def _object_fields_all(self, o: Object) -> Array[String]:
        return Array([f.key for f in o.fields])

    @_eval_args
    def _object_values_all(self, o: Object) -> Array[Primitive]:
        return Array([f.value for f in o.fields])

    @_eval_args
    def _object_keys_values_all(self, o: Object) -> Array[Object]:
        return Array(
            [Object(Object.Field(String("key"), f.key), Object.Field(String("value"), f.value)) for f in o.fields]
        )

    @_eval_args
    def _object_remove_key(self, obj: Object, key: String) -> Object:
        return Object(*[field for field in obj.fields if field.key != key])

    @_eval_args
    def _map_with_key(self, func: Function, obj: Object) -> Object:
        return Object(*[Object.Field(field.key, func(field.key, field.value)) for field in obj.fields])

    @_eval_args
    def _base64(self, input: Union[String, Array[Number[int]]]) -> String:
        if isinstance(input, String):
            return String(base64.b64encode(input.encode()).decode())
        return String(base64.b64encode(bytes([n.value for n in input])).decode())

    @_eval_args
    def _base64_decode_bytes(self, str: String) -> Array[Number[int]]:
        return Array([Number(b) for b in base64.b64decode(str)])

    @_eval_args
    def _base64_decode(self, str: String) -> String:
        return String(base64.b64decode(str).decode())

    @_eval_args
    def _md5(self, s: String) -> String:
        return String(hashlib.md5(s.encode()).hexdigest())

    @_eval_args
    def _sha1(self, s: String) -> String:
        return String(hashlib.sha1(s.encode()).hexdigest())

    @_eval_args
    def _sha256(self, s: String) -> String:
        return String(hashlib.sha256(s.encode()).hexdigest())

    @_eval_args
    def _sha512(self, s: String) -> String:
        return String(hashlib.sha512(s.encode()).hexdigest())

    @_eval_args
    def _sha3(self, s: String) -> String:
        return String(hashlib.sha3_512(s.encode()).hexdigest())

    def as_object(self) -> Object:
        return Object(
            Object.Field(String("extVar"), Function(self._ext_var)),
            Object.Field(String("native"), Function(self._native)),
            Object.Field(String("type"), Function(self._type)),
            Object.Field(String("length"), Function(self._length)),
            Object.Field(String("codepoint"), Function(self._codepoint)),
            Object.Field(String("char"), Function(self._char)),
            Object.Field(String("substr"), Function(self._substr)),
            Object.Field(String("findSubstr"), Function(self._find_substr)),
            Object.Field(String("startsWith"), Function(self._startsWith)),
            Object.Field(String("endsWith"), Function(self._endsWith)),
            Object.Field(String("stripChars"), Function(self._strip_chars)),
            Object.Field(String("lstripChars"), Function(self._lstrip_chars)),
            Object.Field(String("rstripChars"), Function(self._rstrip_chars)),
            Object.Field(String("split"), Function(self._split)),
            Object.Field(String("splitLimit"), Function(self._split_limit)),
            Object.Field(String("splitLimitR"), Function(self._split_limit_r)),
            Object.Field(String("strReplace"), Function(self._str_replace)),
            Object.Field(String("isEmpty"), Function(self._is_empty)),
            Object.Field(String("trim"), Function(self._trim)),
            Object.Field(String("equalsIgnoreCase"), Function(self._equals_ignore_case)),
            Object.Field(String("asciiUpper"), Function(self._ascii_upper)),
            Object.Field(String("asciiLower"), Function(self._ascii_lower)),
            Object.Field(String("stringChars"), Function(self._string_chars)),
            Object.Field(String("format"), Function(self._format)),
            Object.Field(String("escapeStringBash"), Function(self._escape_string_bash)),
            Object.Field(String("escapeStringDollars"), Function(self._escape_string_dollars)),
            Object.Field(String("escapeStringJson"), Function(self._escape_string_json)),
            Object.Field(String("escapeStringPython"), Function(self._escape_string_json)),  # alias
            Object.Field(String("escapeStringXml"), Function(self._escape_string_xml)),
            Object.Field(String("mod"), Function(self._mod)),
            Object.Field(String("abs"), Function(self._abs)),
            Object.Field(String("sign"), Function(self._sign)),
            Object.Field(String("max"), Function(self._max)),
            Object.Field(String("min"), Function(self._min)),
            Object.Field(String("pow"), Function(self._pow)),
            Object.Field(String("exp"), Function(self._exp)),
            Object.Field(String("log"), Function(self._log)),
            Object.Field(String("exponent"), Function(self._exponent)),
            Object.Field(String("mantissa"), Function(self._mantissa)),
            Object.Field(String("floor"), Function(self._floor)),
            Object.Field(String("ceil"), Function(self._ceil)),
            Object.Field(String("sqrt"), Function(self._sqrt)),
            Object.Field(String("sin"), Function(self._sin)),
            Object.Field(String("cos"), Function(self._cos)),
            Object.Field(String("tan"), Function(self._tan)),
            Object.Field(String("asin"), Function(self._asin)),
            Object.Field(String("acos"), Function(self._acos)),
            Object.Field(String("atan"), Function(self._atan)),
            Object.Field(String("round"), Function(self._round)),
            Object.Field(String("isEven"), Function(self._is_even)),
            Object.Field(String("isOdd"), Function(self._is_odd)),
            Object.Field(String("isInteger"), Function(self._is_integer)),
            Object.Field(String("isDecimal"), Function(self._is_decimal)),
            Object.Field(String("clamp"), Function(self._clamp)),
            Object.Field(String("assertEqual"), Function(self._assert_equal)),
            Object.Field(String("toString"), Function(self._to_string)),
            Object.Field(String("trace"), Function(self._trace)),
            Object.Field(String("prune"), Function(self._prune)),
            Object.Field(String("parseInt"), Function(self._parse_int)),
            Object.Field(String("parseOctal"), Function(self._parse_octal)),
            Object.Field(String("parseHex"), Function(self._parse_hex)),
            Object.Field(String("parseJson"), Function(self._parse_json)),
            Object.Field(String("encodeUTF8"), Function(self._encode_utf8)),
            Object.Field(String("decodeUTF8"), Function(self._decode_utf8)),
            Object.Field(String("manifestIni"), Function(self._manifest_ini)),
            Object.Field(String("manifestPython"), Function(self._manifest_python)),
            Object.Field(String("manifestPythonVars"), Function(self._manifest_python_vars)),
            Object.Field(String("manifestJsonEx"), Function(self._manifest_json_ex)),
            Object.Field(String("manifestJson"), Function(self._manifest_json)),
            Object.Field(String("manifestJsonMinified"), Function(self._manifest_json_minified)),
            Object.Field(String("makeArray"), Function(self._make_array)),
            Object.Field(String("member"), Function(self._member)),
            Object.Field(String("count"), Function(self._count)),
            Object.Field(String("find"), Function(self._find)),
            Object.Field(String("map"), Function(self._map)),
            Object.Field(String("mapWithIndex"), Function(self._map_with_index)),
            Object.Field(String("filter"), Function(self._filter)),
            Object.Field(String("filterMap"), Function(self._filter_map)),
            Object.Field(String("flatMap"), Function(self._flat_map)),
            Object.Field(String("foldl"), Function(self._foldl)),
            Object.Field(String("foldr"), Function(self._foldr)),
            Object.Field(String("range"), Function(self._range)),
            Object.Field(String("repeat"), Function(self._repeat)),
            Object.Field(String("slice"), Function(self._slice)),
            Object.Field(String("join"), Function(self._join)),
            Object.Field(String("lines"), Function(self._lines)),
            Object.Field(String("flattenArrays"), Function(self._flatten_arrays)),
            Object.Field(String("flattenDeepArray"), Function(self._flatten_deep_array)),
            Object.Field(String("reverse"), Function(self._reverse)),
            Object.Field(String("sort"), Function(self._sort)),
            Object.Field(String("uniq"), Function(self._uniq)),
            Object.Field(String("all"), Function(self._all)),
            Object.Field(String("any"), Function(self._any)),
            Object.Field(String("sum"), Function(self._sum)),
            Object.Field(String("contains"), Function(self._contains)),
            Object.Field(String("avg"), Function(self._avg)),
            Object.Field(String("remove"), Function(self._remove)),
            Object.Field(String("removeAt"), Function(self._remove_at)),
            Object.Field(String("set"), Function(self._set)),
            Object.Field(String("setInter"), Function(self._set_inter)),
            Object.Field(String("setUnion"), Function(self._set_union)),
            Object.Field(String("setMember"), Function(self._set_member)),
            Object.Field(String("get"), Function(self._get)),
            Object.Field(String("objectHas"), Function(self._object_has)),
            Object.Field(String("objectFields"), Function(self._object_fields)),
            Object.Field(String("objectValues"), Function(self._object_values)),
            Object.Field(String("objectKeysValues"), Function(self._object_keys_values)),
            Object.Field(String("objectHasAll"), Function(self._object_has_all)),
            Object.Field(String("objectFieldsAll"), Function(self._object_fields_all)),
            Object.Field(String("objectValuesAll"), Function(self._object_values_all)),
            Object.Field(String("objectKeysValuesAll"), Function(self._object_keys_values_all)),
            Object.Field(String("objectRemoveKey"), Function(self._object_remove_key)),
            Object.Field(String("mapWithKey"), Function(self._map_with_key)),
            Object.Field(String("base64"), Function(self._base64)),
            Object.Field(String("base64DecodeBytes"), Function(self._base64_decode_bytes)),
            Object.Field(String("base64Decode"), Function(self._base64_decode)),
            Object.Field(String("md5"), Function(self._md5)),
            Object.Field(String("sha1"), Function(self._sha1)),
            Object.Field(String("sha256"), Function(self._sha256)),
            Object.Field(String("sha512"), Function(self._sha512)),
            Object.Field(String("sha3"), Function(self._sha3)),
        )
