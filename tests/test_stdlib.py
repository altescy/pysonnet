import math
from io import StringIO
from typing import Any

import pytest

from pysonnet.errors import PysonnetRuntimeError
from pysonnet.evaluator import Evaluator
from pysonnet.lexer import Lexer
from pysonnet.parser import Parser


@pytest.mark.parametrize(
    "inputs, expected",
    [
        ("std.prune({'a': {b: [[]]}})", {}),
        ("std.prune({'a': {b: [], c: 1, d: null}})", {"a": {"c": 1}}),
        ("std.codepoint('a')", 97),
        ("std.char(97)", "a"),
        ("std.substr('hello', 1, 2)", "el"),
        ("std.findSubstr('bb', 'abbbc')", [1, 2]),
        ("std.startsWith('hello', 'he')", True),
        ("std.endsWith('hello', 'lo')", True),
        ("std.stripChars(' test  ', ' ')", "test"),
        ("std.lstripChars(' test  ', ' ')", "test  "),
        ("std.rstripChars(' test  ', ' ')", " test"),
        ("std.split('a,b,c', ',')", ["a", "b", "c"]),
        ("std.splitLimit('a,b,c', ',', 1)", ["a", "b,c"]),
        ("std.splitLimitR('a,b,c', ',', 1)", ["a,b", "c"]),
        ("std.strReplace('I like to skate with my skateboard', 'skate', 'surf')", "I like to surf with my surfboard"),
        ("std.isEmpty('')", True),
        ("std.isEmpty('x')", False),
        ("std.trim(' hello  ')", "hello"),
        ("std.equalsIgnoreCase('aBc', 'AbC')", True),
        ("std.asciiUpper('100 Cats!')", "100 CATS!"),
        ("std.asciiLower('100 Cats!')", "100 cats!"),
        ("std.stringChars('foo')", ["f", "o", "o"]),
        ("std.escapeStringBash(\"echo 'foo'\")", "'echo '\"'\"'foo'\"'\"''"),
        ("std.escapeStringDollars('hello $name')", "hello $$name"),
        ("std.escapeStringJson('Multiline\\nc:\\\\path')", '"Multiline\\nc:\\\\path"'),
        ("std.escapeStringPython('Multiline\\nc:\\\\path')", '"Multiline\\nc:\\\\path"'),
        ("std.escapeStringXml('<test>')", "&lt;test&gt;"),
        # Mathematical functions
        ("std.mod(5, 2)", 1),
        ("std.abs(1)", 1),
        ("std.abs(-1)", 1),
        ("std.sign(10)", 1),
        ("std.sign(-5)", -1),
        ("std.sign(0)", 0),
        ("std.max(1, 2)", 2),
        ("std.min(1, 2)", 1),
        ("std.pow(2, 3)", 8),
        ("std.exp(1)", math.exp(1)),
        ("std.log(10)", math.log(10)),
        ("std.exponent(5)", 3),
        ("std.mantissa(5)", 0.625),
        ("std.floor(1.5)", 1),
        ("std.ceil(1.5)", 2),
        ("std.sqrt(4)", 2),
        ("std.sin(0)", 0),
        ("std.cos(0)", 1),
        ("std.tan(0)", 0),
        ("std.asin(0)", 0),
        ("std.acos(1)", 0),
        ("std.atan(0)", 0),
        ("std.round(1.5)", 2),
        ("std.isEven(2)", True),
        ("std.isEven(3)", False),
        ("std.isOdd(2)", False),
        ("std.isOdd(3)", True),
        ("std.isInteger(2)", True),
        ("std.isInteger(2.5)", False),
        ("std.isDecimal(2)", False),
        ("std.isDecimal(2.5)", True),
        # parsing functions
        ("std.parseInt('123')", 123),
        ("std.parseOctal('755')", 493),
        ("std.parseHex('ff')", 255),
        ('std.parseJson(\'{"foo": "bar"}\')', {"foo": "bar"}),
        ("std.encodeUTF8('test')", [116, 101, 115, 116]),
        ("std.decodeUTF8([116, 101, 115, 116])", "test"),
        # manifest functions
        (
            """
            local config = {
                main: { a: "1", b: "2" },
                sections: {
                    s1: {x: "11", y: "22", z: "33"},
                    s2: {p: "yes", q: ""},
                    empty: {},
                }
            };
            std.manifestIni(config)
            """,
            """a = 1
b = 2
[empty]
[s1]
x = 11
y = 22
z = 33
[s2]
p = yes
q =""",
        ),
        (
            """
            local config = {
              b: ['foo', 'bar'],
              c: true,
              d: null,
              e: { f1: false, f2: 42 },
            };
            std.manifestPython(config)
            """,
            "{'b': ['foo', 'bar'], 'c': True, 'd': None, 'e': {'f1': False, 'f2': 42}}",
        ),
        (
            """
            local config = {
                b: ["foo", "bar"],
                c: true,
                d: null,
                e: { f1: false, f2: 42 },
            };
            std.manifestPythonVars(config)
            """,
            "b = ['foo', 'bar']\nc = True\nd = None\ne = {'f1': False, 'f2': 42}",
        ),
        (
            'std.manifestJson( { x: [1, 2, 3, true, false, null, "string"], y: { a: 1, b: 2, c: [1, 2] }, })',
            """{
    "x": [
        1,
        2,
        3,
        true,
        false,
        null,
        "string"
    ],
    "y": {
        "a": 1,
        "b": 2,
        "c": [
            1,
            2
        ]
    }
}""",
        ),
        (
            'std.manifestJsonMinified( { x: [1, 2, 3, true, false, null, "string"], y: { a: 1, b: 2, c: [1, 2] }, })',
            '{"x":[1,2,3,true,false,null,"string"],"y":{"a":1,"b":2,"c":[1,2]}}',
        ),
        # array functions
        ("std.member([1, 2, 3], 2)", True),
        ("std.member([{a: 1}, {a: 2}], {a: 1})", True),
        ("std.member([{a: 1}, {a: 2}], {a: 3})", False),
        ("std.count(1, [1, 2, 1, 3])", 2),
        ("std.find(1, [1, 2, 1, 3])", [0, 2]),
        ("local f(x) = x + 1; std.map(f, [1, 2])", [2, 3]),
        ("local f(i, x) = x + i; std.mapWithIndex(f, [1, 2])", [1, 3]),
        ("local f(x) = x % 2 == 0; std.filter(f, [0, 1, 2])", [0, 2]),
        ("local f(x) = x % 2 == 0, g(x) = x + 1; std.filterMap(f, g, [0, 1, 2])", [1, 3]),
        ("std.flatMap(function(x) [x, x], [1, 2, 3])", [1, 1, 2, 2, 3, 3]),
        ("std.flatMap(function(x) if x == 2 then [] else [x], [1, 2, 3])", [1, 3]),
        ("std.flatMap(function(x) if x == 2 then [] else [x * 3, x * 2], [1, 2, 3])", [3, 2, 9, 6]),
        ("std.flatMap(function(x) x+x, 'foo')", "ffoooo"),
        ("std.foldl(function(a, b) std.pow(b, a), [1, 2, 3], 1)", 9),
        ("std.foldr(function(a, b) std.pow(b, a), [1, 2, 3], 1)", 1),
        ("std.repeat([1, 2, 3], 3)", [1, 2, 3, 1, 2, 3, 1, 2, 3]),
        ("std.repeat('blah', 2)", "blahblah"),
        ("std.slice([1, 2, 3, 4, 5, 6], 0, 4, 1)", [1, 2, 3, 4]),
        ("std.slice([1, 2, 3, 4, 5, 6], 1, 6, 2)", [2, 4, 6]),
        ("std.slice('jsonnet', 0, 4, 1)", "json"),
        ("std.slice('jsonnet', -3, null, null)", "net"),
        ("std.join('.', ['www', 'google', 'com'])", "www.google.com"),
        ("std.join([9, 9], [[1], [2, 3]])", [1, 9, 9, 2, 3]),
        ("std.lines(['foo', 'bar'])", "foo\nbar\n"),
        ("std.flattenArrays([[1, 2], [3, 4], [[5, 6], [7, 8]]])", [1, 2, 3, 4, [5, 6], [7, 8]]),
        ("std.flattenDeepArray([[1, 2], [], [3, [4]], [[5, 6, [null]], [7, 8]]])", [1, 2, 3, 4, 5, 6, None, 7, 8]),
        ("std.reverse([1, 2, 3])", [3, 2, 1]),
        ("std.reverse('abc')", "cba"),
        ("std.sort([3, 1, 2])", [1, 2, 3]),
        (
            "std.sort([{name: 'foo', age: 30}, {name: 'bar', age: 20}], function(x) x.age)",
            [{"name": "bar", "age": 20}, {"name": "foo", "age": 30}],
        ),
        ("std.uniq([2, 2, 1, 4])", [2, 1, 4]),
        ("std.all([])", True),
        ("std.all([true, true, true])", True),
        ("std.all([true, false, true])", False),
        ("std.any([])", False),
        ("std.any([true, false, true])", True),
        ("std.any([false, false, false])", False),
        ("std.sum([1, 2, 3])", 6),
        ("std.contains([1, 2, 3], 2)", True),
        ("std.contains([1, 2, 3], 4)", False),
        ("std.avg([1, 2, 3])", 2.0),
        ("std.remove([1, 2, 3, 2], 2)", [1, 3, 2]),
        ("std.removeAt([1, 2, 3], 1)", [1, 3]),
        # set functions
        ("std.set([3, 1, 2, 1])", [1, 2, 3]),
        ("std.setInter([3, 1, 2], [4, 1, 3])", [1, 3]),
        ("std.setUnion([3, 1, 2], [4, 1, 3])", [1, 2, 3, 4]),
        ("std.setMember(2, [3, 1, 2, 2])", True),
        ("std.setMember(0, [3, 1, 2, 2])", False),
        # object functions
        ("std.get({a: 1, b: 2}, 'a')", 1),
        ("std.objectHas({a: 1, b: 2}, 'a')", True),
        ("std.objectHas({a: 1, b: 2}, 'c')", False),
        ("std.objectFields({a: 1, b: 2})", ["a", "b"]),
        ("std.objectFields({a: 1, b:: 2})", ["a"]),
        ("std.objectValues({a: 1, b: 2})", [1, 2]),
        ("std.objectValues({a: 1, b:: 2})", [1]),
        ("std.objectKeysValues({a: 1, b: 2})", [{"key": "a", "value": 1}, {"key": "b", "value": 2}]),
        ("std.objectKeysValues({a: 1, b:: 2})", [{"key": "a", "value": 1}]),
        ("std.objectFieldsAll({a: 1, b:: 2})", ["a", "b"]),
        ("std.objectValuesAll({a: 1, b:: 2})", [1, 2]),
        ("std.objectKeysValuesAll({a: 1, b:: 2})", [{"key": "a", "value": 1}, {"key": "b", "value": 2}]),
        ("std.objectRemoveKey({a: 1, b: 2}, 'a')", {"b": 2}),
        ("std.mapWithKey(function(k, v) k+v, {'a': 'foo', 'b': 'bar'})", {"a": "afoo", "b": "bbar"}),
        ("std.base64('hello')", "aGVsbG8="),
        ("std.base64(std.map(std.codepoint, 'hello'))", "aGVsbG8="),
        ("std.base64DecodeBytes('aGVsbG8=')", [104, 101, 108, 108, 111]),
        ("std.base64Decode('aGVsbG8=')", "hello"),
        ("std.md5('hello')", "5d41402abc4b2a76b9719d911017c592"),
        ("std.sha1('hello')", "aaf4c61ddcc5e8a2dabede0f3b482cd9aea9434d"),
        ("std.sha256('hello')", "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"),
        (
            "std.sha512('hello')",
            "9b71d224bd62f3785d96d46ad3ea3d73319bfbc2890caadae2dff72519673ca72323c3d99ba5c11d7c7acc6e14b8c5da0c4663475c2e5c3adef46f73bcdec043",
        ),
        (
            "std.sha3('hello')",
            "75d527c368f2efe848ecf6b073a36767800805e9eef2b1857d5f984f036eb6df891d75f72d9b154518c1cd58835286d1da9a38deba3de98b5a53e5ed78a84976",
        ),
        ("std.xor(true, false)", True),
        ("std.xor(false, false)", False),
        ("std.xnor(true, false)", False),
        ("std.xnor(false, false)", True),
        ("std.mergePatch({a: 1, b: 2}, {b: 3, c: 4})", {"a": 1, "b": 3, "c": 4}),
        ("std.mergePatch({a: 1, b: 2}, {b:: 3, c: 4})", {"a": 1, "b": 2, "c": 4}),
    ],
)
def test_evaluate(inputs: str, expected: Any) -> None:
    parser = Parser(Lexer(StringIO(inputs)))
    evaluator = Evaluator()
    node = parser.parse()
    assert node is not None
    result = evaluator(node).to_json()
    assert result == expected


def test_assert_equal() -> None:
    evaluator = Evaluator()

    parser = Parser(Lexer(StringIO("std.assertEqual(1, 1)")))
    node = parser.parse()
    assert node is not None
    result = evaluator(node).to_json()
    assert result

    parser = Parser(Lexer(StringIO("std.assertEqual(1, 2)")))
    node = parser.parse()
    assert node is not None
    with pytest.raises(PysonnetRuntimeError):
        evaluator(node)
