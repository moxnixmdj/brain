"""The grammar-closed expression pool a site can be asked about.

One part, used by `force_the_value_and_see_v1.py`: the material is the site's own operands and the
names already in scope, the grammar is Python's, and two expressions are the same question only when
their text is the same. Nothing here runs a test suite; nothing here knows the answer.
"""
from __future__ import annotations

import ast
from typing import Any, Iterator, Sequence

MAX_NODES = 7          # a candidate expression may not be larger than this, counted in AST nodes
SAFE_BUILTINS = ("len", "abs", "max", "min", "sum", "sorted", "int", "float", "bool", "str",
                 "tuple", "list", "reversed")
BINOPS = ("+", "-", "*", "//", "%", "**", "/")


def _value_key(value: Any) -> str:
    try:
        return f"{type(value).__name__}:{repr(value)[:120]}"
    except Exception:  # noqa: BLE001
        return "UNREPRESENTABLE"


def _signature(values: Sequence[Any]) -> tuple[str, ...]:
    return tuple(_value_key(value) for value in values)


def _evaluate_all(text: str, contexts: Sequence[dict[str, Any]],
                  namespace: dict[str, Any]) -> list[Any] | None:
    """The term's value in every context, or None if it does not even run in one of them."""
    values: list[Any] = []
    for context in contexts:
        try:
            values.append(eval(text, namespace, dict(context["locals"])))  # noqa: S307
        except Exception:  # noqa: BLE001
            return None
    return values



def base_terms(source: str, function_name: str, site_text: str,
               contexts: Sequence[dict[str, Any]]) -> list[str]:
    """Everything already sitting at the site: its own operands, the locals, the constants, the calls.

    Nothing is invented. This is the same law as the space: the material is the program's own, and the
    only thing added is the grammar that may combine it.
    """
    terms: list[str] = []
    try:
        site = ast.parse(site_text, mode="eval").body
        for node in ast.walk(site):
            if isinstance(node, ast.expr):
                text = ast.unparse(node)
                if text not in terms:
                    terms.append(text)
    except SyntaxError:
        pass
    names: set[str] = set()
    for context in contexts:
        names.update(context["locals"].keys())
    for name in sorted(names):
        if name not in terms:
            terms.append(name)
    for constant in ("0", "1", "2", "True", "False", "None", "[]", "-1"):
        if constant not in terms:
            terms.append(constant)
    for name in SAFE_BUILTINS + (function_name,):
        terms.append(name)
    return terms



def _size(text: str) -> int:
    """How many expression nodes the text contains -- not how many AST nodes.

    `ast.walk` also visits the `Load`/`Store` context attached to every name, so counting all nodes
    makes `arr` look like size 2 and a bare constant look like size 1. An atom test built on that
    number admits only constants, and a local can never become material: that is how `max(longest,
    length + 1)` was declared inexpressible with all three of its parts sitting at the site.
    """
    try:
        body = ast.parse(text, mode="eval").body
    except SyntaxError:
        return 10 ** 6
    return sum(1 for node in ast.walk(body) if isinstance(node, ast.expr))


def _combinations(left: str, right: str, function_name: str) -> Iterator[str]:
    """The grammar of the language, not a list of fixes: every form a Python expression may take."""
    for operator in BINOPS:
        yield f"({left}) {operator} ({right})"
    for operator in ("==", "!=", "<", "<=", ">", ">=", "is", "is not", "in", "not in"):
        yield f"({left}) {operator} ({right})"
    yield f"({left}) and ({right})"
    yield f"({left}) or ({right})"
    yield f"not ({left})"
    yield f"-({left})"
    yield f"({left})[({right})]"
    yield f"({left})[({right}):]"
    yield f"[({left})]"
    yield f"[({left}), ({right})]"
    yield f"(({left}), ({right}))"
    for name in SAFE_BUILTINS:
        yield f"{name}({left})"
        yield f"{name}({left}, {right})"
    yield f"{function_name}({left})"
    yield f"{function_name}({left}, {right})"
