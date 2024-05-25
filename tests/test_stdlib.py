from io import StringIO
from typing import Any

import pytest

from pysonnet.evaluator import Evaluator
from pysonnet.lexer import Lexer
from pysonnet.parser import Parser


@pytest.mark.parametrize(
    "inputs, expected",
    [
        ("std.prune({'a': {b: [[]]}})", {}),
        ("std.prune({'a': {b: [], c: 1, d: null}})", {"a": {"c": 1}}),
    ],
)
def test_evaluate(inputs: str, expected: Any) -> None:
    parser = Parser(Lexer(StringIO(inputs)))
    evaluator = Evaluator()
    node = parser.parse()
    assert node is not None
    result = evaluator(node).to_json()
    print("result", result)
    assert result == expected
