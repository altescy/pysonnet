import abc
import dataclasses
import enum
from typing import Any, Callable, Dict, Generic, List, Literal, Optional, TypeVar, Union

_PRIMITIVE = Union[str, int, float, bool, None, dict, list, Callable]
_T = TypeVar("_T", bound=_PRIMITIVE)
_S = TypeVar("_S", bound=_PRIMITIVE)
_T_co = TypeVar("_T_co", covariant=True, bound=_PRIMITIVE)
_S_co = TypeVar("_S_co", covariant=True, bound=_PRIMITIVE)


@dataclasses.dataclass(frozen=True)
class AST(abc.ABC, Generic[_T_co]):
    ...


@dataclasses.dataclass(frozen=True)
class LiteralAST(AST[_T_co]):
    value: _T_co


@dataclasses.dataclass(frozen=True)
class Identifier(Generic[_T_co], AST[_T_co]):
    name: str


@dataclasses.dataclass(frozen=True)
class Null(LiteralAST[Literal[None]]):
    value: Literal[None] = None


@dataclasses.dataclass(frozen=True)
class Boolean(LiteralAST[bool]):
    ...


@dataclasses.dataclass(frozen=True)
class Number(LiteralAST[Union[int, float]]):
    ...


@dataclasses.dataclass(frozen=True)
class String(LiteralAST[str]):
    ...


@dataclasses.dataclass(frozen=True)
class Error(Generic[_T_co], AST[_T_co]):
    expr: AST[_T_co]


@dataclasses.dataclass(frozen=True)
class Assert:
    condition: AST[bool]
    message: Optional[AST[Any]] = None


@dataclasses.dataclass(frozen=True)
class IfExpression(Generic[_T_co, _S_co], AST[Union[_T_co, _S_co, None]]):
    condition: AST[bool]
    then_expr: AST[_T_co]
    else_expr: Optional[AST[_S_co]] = None


@dataclasses.dataclass(frozen=True)
class ForSpec(Generic[_T_co]):
    ident: Identifier[_T_co]
    expr: AST[_T_co]


@dataclasses.dataclass(frozen=True)
class IfSpec:
    condition: AST[bool]


ComprehensionSpec = Union[ForSpec, IfSpec]


@dataclasses.dataclass(frozen=True)
class LocalExpression(Generic[_T_co], AST[_T_co]):
    @dataclasses.dataclass(frozen=True)
    class Bind(Generic[_T]):
        ident: Identifier
        expr: AST[_T]

    binds: List[Bind]
    expr: AST[_T_co]


@dataclasses.dataclass(frozen=True)
class AssertExpression(Generic[_T_co], AST[_T_co]):
    assert_: Assert
    expr: AST[_T_co]


@dataclasses.dataclass(frozen=True)
class Unary(Generic[_T_co], AST[_T_co]):
    class Operator(enum.Enum):
        PLUS = enum.auto()
        MINUS = enum.auto()
        NOT = enum.auto()
        BITWISE_NOT = enum.auto()

    operator: Operator
    operand: AST[_T_co]


@dataclasses.dataclass(frozen=True)
class Binary(Generic[_T_co], AST[_T_co]):
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
    left: AST[Any]
    right: AST[Any]


@dataclasses.dataclass(frozen=True)
class SuperIndex(Generic[_T_co], AST[_T_co]):
    key: AST[str]


@dataclasses.dataclass(frozen=True)
class Param(Generic[_T_co]):
    ident: Identifier
    default: Optional[AST[_T_co]] = None


@dataclasses.dataclass(frozen=True)
class Function(Generic[_T_co], AST[Callable[..., _T_co]]):
    params: List[Param]
    expr: AST[_T_co]


@dataclasses.dataclass(frozen=True)
class Call(Generic[_T_co], AST[_T_co]):
    callee: AST[Callable[..., _T_co]]
    args: List[AST]
    kwargs: Dict[Identifier, AST]


@dataclasses.dataclass(frozen=True)
class ObjectLocal(Generic[_T_co]):
    ident: Identifier
    expr: AST[_T_co]


@dataclasses.dataclass(frozen=True)
class ObjectField(Generic[_T]):
    class Visibility(enum.Enum):
        VISIBLE = enum.auto()
        HIDDEN = enum.auto()
        FORCE_VISIBLE = enum.auto()

    key: AST[Union[str, None]]
    expr: AST[_T]
    inherit: bool = False
    visibility: Visibility = Visibility.VISIBLE


ObjectMember = Union[ObjectField, ObjectLocal, Assert]


@dataclasses.dataclass(frozen=True)
class Object(AST[Dict[str, Any]]):
    members: List[ObjectMember]


@dataclasses.dataclass(frozen=True)
class Array(Generic[_T_co], AST[List[_T_co]]):
    elements: List[AST[_T_co]]


@dataclasses.dataclass(frozen=True)
class ArrayComprehension(Generic[_T_co], AST[List[_T_co]]):
    expression: AST[Any]
    forspec: ForSpec[_T_co]
    compspec: List[ComprehensionSpec]
