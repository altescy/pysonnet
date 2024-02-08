import abc
import dataclasses
import enum
from typing import Any, Dict, Generic, List, Literal, TypeVar, Union

_T = TypeVar("_T")
_T_co = TypeVar("_T_co", covariant=True)


@dataclasses.dataclass(frozen=True)
class Node(abc.ABC):
    ...


@dataclasses.dataclass(frozen=True)
class Statement(Node):
    ...


@dataclasses.dataclass(frozen=True)
class Expression(Node, Generic[_T_co]):
    ...


@dataclasses.dataclass(frozen=True)
class LiteralExpression(Expression[_T_co]):
    value: _T_co


@dataclasses.dataclass(frozen=True)
class Identifier(Generic[_T_co], Expression[_T_co]):
    name: str


@dataclasses.dataclass(frozen=True)
class Null(LiteralExpression[Literal[None]]):
    value: Literal[None] = None


@dataclasses.dataclass(frozen=True)
class Boolean(LiteralExpression[bool]):
    ...


@dataclasses.dataclass(frozen=True)
class Number(LiteralExpression[Union[int, float]]):
    ...


@dataclasses.dataclass(frozen=True)
class String(LiteralExpression[str]):
    ...


@dataclasses.dataclass(frozen=True)
class BindStatement(Generic[_T], Statement):
    ident: Identifier
    expr: Expression[_T]


@dataclasses.dataclass(frozen=True)
class ObjlocalStatement(Statement):
    bind: BindStatement


@dataclasses.dataclass(frozen=True)
class FieldStatement(Generic[_T], Statement):
    class Visibility(enum.Enum):
        VISIBLE = enum.auto()
        HIDDEN = enum.auto()
        FORCE_VISIBLE = enum.auto()

    key: Expression[Union[str, None]]
    expr: Expression[_T]
    inherit: bool = False
    visibility: Visibility = Visibility.VISIBLE


@dataclasses.dataclass(frozen=True)
class ForStatement(Generic[_T], Statement):
    identifiler: Identifier[_T]
    expression: Expression[List[_T]]


@dataclasses.dataclass(frozen=True)
class IfStatement(Statement):
    condition: Expression[bool]


# TODO: add assert statement
MemberStatement = Union[ObjlocalStatement, FieldStatement]


@dataclasses.dataclass(frozen=True)
class Object(Expression[Dict[str, Any]]):
    members: List[MemberStatement]


@dataclasses.dataclass(frozen=True)
class Array(Expression[List[Any]]):
    elements: List[Expression[Any]]


@dataclasses.dataclass(frozen=True)
class ListComprehension(Expression[List[Any]]):
    expression: Expression[Any]
    forspec: ForStatement[Any]
    compspec: List[Union[ForStatement, IfStatement]]


@dataclasses.dataclass(frozen=True)
class LocalExpression(Expression[_T_co]):
    binds: List[BindStatement]
    expr: Expression


@dataclasses.dataclass(frozen=True)
class UnaryExpression(Expression[_T_co]):
    class Operator(enum.Enum):
        PLUS = enum.auto()
        MINUS = enum.auto()
        NOT = enum.auto()
        BITWISE_NOT = enum.auto()

    operator: Operator
    operand: Expression[_T_co]


@dataclasses.dataclass(frozen=True)
class BinaryExpression(Expression[_T_co]):
    class Operator(enum.Enum):
        ADD = enum.auto()
        SUB = enum.auto()
        MUL = enum.auto()
        DIV = enum.auto()
        MOD = enum.auto()
        BITWISE_AND = enum.auto()
        BITWISE_OR = enum.auto()
        BITWISE_XOR = enum.auto()
        LSHIFT = enum.auto()
        RSHIFT = enum.auto()
        AND = enum.auto()
        OR = enum.auto()
        EQ = enum.auto()
        NE = enum.auto()
        LT = enum.auto()
        LE = enum.auto()
        GT = enum.auto()
        GE = enum.auto()
        INDEX = enum.auto()

    operator: Operator
    left: Expression[_T_co]
    right: Expression[_T_co]


@dataclasses.dataclass(frozen=True)
class Super(Expression[None]):
    key: Expression[str]
