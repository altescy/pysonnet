from typing import Any, Dict

import pytest

from pysonnet.objects import Array, Null, Number, Object, Primitive, String


def test_null() -> None:
    null = Null()
    assert str(null) == "null"
    assert null.to_json() is None  # type: ignore[func-returns-value]


def test_number() -> None:
    a = Number(1)
    b = Number(2)
    c = a + b
    assert c == Number(3)
    assert str(c) == "3"
    assert c.to_json() == 3


def test_string() -> None:
    text = String("hello")
    assert text == String("hello")
    assert text.to_json() == "hello"


def test_array() -> None:
    array = Array([Number(1), Number(2), Number(3)])
    assert array == Array([Number(1), Number(2), Number(3)])
    assert array.to_json() == [1, 2, 3]


def test_array_operations() -> None:
    x = Array([Number(1), Number(2), Number(3)])
    b = x + Array([Number(4), Number(5)])
    assert len(b) == 5
    assert b == Array([Number(1), Number(2), Number(3), Number(4), Number(5)])


def test_object() -> None:
    obj = Object(Object.Field(String("a"), Number(1)), Object.Field(String("b"), Number(2)))
    assert obj == Object(Object.Field(String("a"), Number(1)), Object.Field(String("b"), Number(2)))
    assert obj.to_json() == {"a": 1, "b": 2}


def test_object_visibility() -> None:
    obj = Object(
        Object.Field(String("a"), Number(1), visibility=Object.Visibility.HIDDEN),
        Object.Field(String("b"), Number(2)),
    )
    assert String("a") in obj
    assert obj.to_json() == {"b": 2}


@pytest.mark.parametrize(
    "a,b,expected,expected_json",
    [
        (
            Object(Object.Field(String("a"), Number(1))),
            Object(Object.Field(String("b"), Number(2))),
            Object(
                Object.Field(String("a"), Number(1)),
                Object.Field(String("b"), Number(2)),
            ),
            {"a": 1, "b": 2},
        ),
        (
            Object(Object.Field(String("a"), Number(1))),
            Object(Object.Field(String("a"), Number(2))),
            Object(Object.Field(String("a"), Number(2))),
            {"a": 2},
        ),
        (
            Object(Object.Field(String("a"), Number(1))),
            Object(Object.Field(String("a"), Number(2), inherit=True)),
            Object(Object.Field(String("a"), Number(3))),
            {"a": 3},
        ),
    ],
)
def test_object_addition(
    a: Object,
    b: Object,
    expected: Object,
    expected_json: Dict[str, Any],
) -> None:
    c = a + b
    assert c.to_json() == expected_json


@pytest.mark.parametrize(
    "template,values,expected",
    [
        (
            String("Hello, %s! This is %s."),
            Array([String("world"), String("pysonnet")]),
            String("Hello, world! This is pysonnet."),
        ),
        (
            String("Hello, %(you)s! This is %(me)s."),
            Object(
                Object.Field(String("you"), String("world")),
                Object.Field(String("me"), String("pysonnet")),
            ),
            String("Hello, world! This is pysonnet."),
        ),
        (
            String("Number: %d, Float: %.1f, String: %s, Array: %s, Object: %s"),
            Array(
                [
                    Number(1),
                    Number(3.1415),
                    String("hello"),
                    Array([Number(1), Number(2)]),
                    Object(Object.Field(String("a"), Number(5))),
                ]
            ),
            String('Number: 1, Float: 3.1, String: hello, Array: [1, 2], Object: {"a": 5}'),
        ),
        (
            String("mysql2://%(user)s@%(host)s:%(port)s/%(db)s?%(option)s"),
            Object(
                Object.Field(String("user"), String("root")),
                Object.Field(String("host"), String("localhost")),
                Object.Field(String("port"), Number(3306)),
                Object.Field(String("db"), String("test")),
                Object.Field(String("option"), String("charset=utf8")),
            ),
            String("mysql2://root@localhost:3306/test?charset=utf8"),
        ),
    ],
)
def test_string_format(
    template: String,
    values: Primitive,
    expected: String,
) -> None:
    output = template % values
    assert output == expected
