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
class AST(abc.ABC, Generic[_T_co]): ...


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
class Boolean(LiteralAST[bool]): ...


@dataclasses.dataclass(frozen=True)
class Number(LiteralAST[Union[int, float]]): ...


@dataclasses.dataclass(frozen=True)
class String(LiteralAST[str]): ...


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
class Bind(Generic[_T]):
    ident: Identifier
    expr: AST[_T]


@dataclasses.dataclass(frozen=True)
class LocalExpression(Generic[_T_co], AST[_T_co]):
    binds: List[Bind]
    expr: AST[_T_co]


@dataclasses.dataclass(frozen=True)
class AssertExpression(Generic[_T_co], AST[_T_co]):
    assert_: Assert
    expr: AST[_T_co]


@dataclasses.dataclass(frozen=True)
class Unary(Generic[_T_co], AST[_T_co]):
    class Operator(str, enum.Enum):
        PLUS = "PLUS"
        MINUS = "MINUS"
        NOT = "NOT"
        BITWISE_NOT = "BITWISE_NOT"

    operator: Operator
    operand: AST[_T_co]


@dataclasses.dataclass(frozen=True)
class Binary(Generic[_T_co], AST[_T_co]):
    class Operator(str, enum.Enum):
        ADD = "ADD"
        SUB = "SUB"
        MUL = "MUL"
        DIV = "DIV"
        MOD = "MOD"
        BITWISE_AND = "BITWISE_AND"
        BITWISE_OR = "BITWISE_OR"
        BITWISE_XOR = "BITWISE_XOR"
        LSHIFT = "LSHIFT"
        RSHIFT = "RSHIFT"
        AND = "AND"
        OR = "OR"
        EQ = "EQ"
        NE = "NE"
        LT = "LT"
        LE = "LE"
        GT = "GT"
        GE = "GE"
        IN = "IN"
        INDEX = "INDEX"

    operator: Operator
    left: AST[Any]
    right: AST[Any]


@dataclasses.dataclass(frozen=True)
class Self(AST[Dict[str, Any]]): ...


@dataclasses.dataclass(frozen=True)
class Dollar(AST[Dict[str, Any]]): ...


@dataclasses.dataclass(frozen=True)
class Super(AST[Dict[str, Any]]): ...


@dataclasses.dataclass(frozen=True)
class Param(Generic[_T_co]):
    ident: Identifier
    default: Optional[AST[_T_co]] = None


@dataclasses.dataclass(frozen=True)
class Function(Generic[_T_co], AST[Callable[..., _T_co]]):
    params: List[Param]
    expr: AST[_T_co]


@dataclasses.dataclass(frozen=True)
class Arg(Generic[_T_co]):
    expr: AST[_T_co]
    ident: Optional[Identifier] = None


@dataclasses.dataclass(frozen=True)
class Apply(Generic[_T_co], AST[_T_co]):
    callee: AST[Callable[..., _T_co]]
    args: List[Arg[Any]]
    tailstrict: bool = False


@dataclasses.dataclass(frozen=True)
class ApplyBrace(AST[Dict[str, Any]]):
    left: AST[Dict[str, Any]]
    right: AST[Dict[str, Any]]


@dataclasses.dataclass(frozen=True)
class ObjectLocal(Generic[_T_co]):
    bind: Bind[_T_co]


@dataclasses.dataclass(frozen=True)
class ObjectField(Generic[_T_co]):
    class Visibility(str, enum.Enum):
        VISIBLE = "VISIBLE"
        HIDDEN = "HIDDEN"
        FORCE_VISIBLE = "FORCE_VISIBLE"

    key: AST[Union[str, None]]
    expr: AST[_T_co]
    inherit: bool = False
    visibility: Visibility = Visibility.VISIBLE


ObjectMember = Union[ObjectField, ObjectLocal, Assert]


@dataclasses.dataclass(frozen=True)
class Object(AST[Dict[str, Any]]):
    members: List[ObjectMember]


@dataclasses.dataclass(frozen=True)
class ObjectComprehension(Generic[_T_co], AST[Dict[str, _T_co]]):
    locals_: List[ObjectLocal]
    key: AST[Optional[str]]
    value: AST[_T_co]
    forspec: ForSpec[Any]
    compspecs: List[ComprehensionSpec]


@dataclasses.dataclass(frozen=True)
class Array(Generic[_T_co], AST[List[_T_co]]):
    elements: List[AST[_T_co]]


@dataclasses.dataclass(frozen=True)
class ArrayComprehension(Generic[_T_co], AST[List[_T_co]]):
    expression: AST[Any]
    forspec: ForSpec[_T_co]
    compspecs: List[ComprehensionSpec]


@dataclasses.dataclass(frozen=True)
class Import(AST[Any]):
    filename: str


@dataclasses.dataclass(frozen=True)
class Importstr(AST[str]):
    filename: str


@dataclasses.dataclass(frozen=True)
class Importbin(AST[List[int]]):
    filename: str


def asdict(ast: AST) -> Dict[str, Any]:
    d: Dict[str, Any] = {"__AST__": ast.__class__.__name__}
    for field in dataclasses.fields(ast):
        value = getattr(ast, field.name)
        if dataclasses.is_dataclass(value):
            d[field.name] = asdict(value)
        elif isinstance(value, list):
            d[field.name] = [asdict(x) if dataclasses.is_dataclass(x) else x for x in value]
        elif isinstance(value, dict):
            d[field.name] = {k: asdict(v) if dataclasses.is_dataclass(v) else v for k, v in value.items()}
        else:
            d[field.name] = value
    return d
