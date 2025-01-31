"""Helper functions used in several visitor classes.

Also contains the decorator definitions used to register error classes.
"""

from __future__ import annotations

import ast
from fnmatch import fnmatch
from typing import TYPE_CHECKING, TypeVar

from ..base import Statement
from . import ERROR_CLASSES, default_disabled_error_codes

if TYPE_CHECKING:
    from collections.abc import Iterable

    from .flake8triovisitor import Flake8TrioVisitor

    T = TypeVar("T", bound=Flake8TrioVisitor)


def error_class(error_class: type[T]) -> type[T]:
    ERROR_CLASSES.add(error_class)
    return error_class


def disabled_by_default(error_class: type[T]) -> type[T]:
    default_disabled_error_codes.extend(error_class.error_codes)
    return error_class


# ignores module and only checks the unqualified name of the decorator
# used in 101 and 107/108
def has_decorator(decorator_list: list[ast.expr], *names: str):
    return any(
        (isinstance(dec, ast.Name) and dec.id in names)
        or (isinstance(dec, ast.Attribute) and dec.attr in names)
        for dec in decorator_list
    )


# matches the fully qualified name against fnmatch pattern
# used to match decorators and methods to user-supplied patterns
# used in 107/108 and 200
def fnmatch_qualified_name(name_list: list[ast.expr], *patterns: str) -> str | None:
    for name in name_list:
        if isinstance(name, ast.Call):
            name = name.func
        qualified_name = ast.unparse(name)

        for pattern in patterns:
            # strip leading "@"s for when we're working with decorators
            if fnmatch(qualified_name, pattern.lstrip("@")):
                return pattern
    return None


# used in 103/104 and 107/108
def iter_guaranteed_once(iterable: ast.expr) -> bool:
    # static container with an "elts" attribute
    if hasattr(iterable, "elts"):
        elts: Iterable[ast.expr] = iterable.elts  # type: ignore
        for elt in elts:
            assert isinstance(elt, ast.expr)
            # recurse starred expression
            if isinstance(elt, ast.Starred):
                if iter_guaranteed_once(elt.value):
                    return True
            else:
                return True
        return False

    if isinstance(iterable, ast.Constant):
        return hasattr(iterable.value, "__len__") and len(iterable.value) > 0

    if isinstance(iterable, ast.Dict):
        for key, val in zip(iterable.keys, iterable.values):
            # {**{...}, **{<...>}} is parsed as {None: {...}, None: {<...>}}
            if key is None and isinstance(val, ast.Dict):
                if iter_guaranteed_once(val):
                    return True
            else:
                return True
    # check for range() with literal parameters
    if (
        isinstance(iterable, ast.Call)
        and isinstance(iterable.func, ast.Name)
        and iterable.func.id == "range"
    ):
        try:
            return len(range(*[ast.literal_eval(a) for a in iterable.args])) > 0
        except Exception:  # noqa: PIE786
            return False
    return False


# used in 102, 103 and 104
def critical_except(node: ast.ExceptHandler) -> Statement | None:
    def has_exception(node: ast.expr | None) -> str:
        if isinstance(node, ast.Name) and node.id == "BaseException":
            return "BaseException"
        if (
            isinstance(node, ast.Attribute)
            and isinstance(node.value, ast.Name)
            and node.value.id == "trio"
            and node.attr == "Cancelled"
        ):
            return "trio.Cancelled"
        return ""

    # bare except
    if node.type is None:
        return Statement("bare except", node.lineno, node.col_offset)
    # several exceptions
    if isinstance(node.type, ast.Tuple):
        for element in node.type.elts:
            name = has_exception(element)
            if name:
                return Statement(name, element.lineno, element.col_offset)
    # single exception, either a Name or an Attribute
    name = has_exception(node.type)
    if name:
        return Statement(name, node.type.lineno, node.type.col_offset)
    return None


# used in 100, 101 and 102
cancel_scope_names = (
    "fail_after",
    "fail_at",
    "move_on_after",
    "move_on_at",
    "CancelScope",
)


# convenience function used in a lot of visitors
def get_matching_call(
    node: ast.AST, *names: str, base: str = "trio"
) -> tuple[ast.Call, str] | None:
    if (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == base
        and node.func.attr in names
    ):
        return node, node.func.attr
    return None
