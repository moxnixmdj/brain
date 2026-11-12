#!/usr/bin/env python3
"""Two expression operators learned from one example, and what each is worth.

The tree's one-example learner repeats a change inside one expression or one simple statement.
Two large classes of change it refuses are expression-shaped and can be written down as
operators:

* **method rename** -- the same receiver, the same arguments, one different attribute:
  ``logger.warn(...)`` -> ``logger.warning(...)``, ``self.assertEquals(...)`` ->
  ``self.assertEqual(...)``. The arguments are not touched, so the number of arguments is not
  evidence against the rename. The tree refused 50 askings in this class because the example
  showed one arity and the target had another.
* **string concatenation to an f-string** -- ``'prefix' + value`` -> ``f'prefix{value}'`` and
  ``value + 'suffix'`` -> ``f'{value}suffix'``. The tree refused whole pull requests in this
  class because the expression's node type changed.

The first is safe without an oracle: the receiver and the arguments are unchanged, and the
rename is the change the example showed. The second is a **candidate generator**, not a safe
action: it converts every concatenation of a string constant and an expression, and the
developers converted only some of them. Its precision is measured, not assumed, and it should
sit behind a test before a lesson is stored.

Neither operator guesses at runtime: a target that does not parse is refused, a bare-name
rename is only applied when the new name is defined or imported in the target, and a method
rename keeps the receiver exactly.
"""
from __future__ import annotations

import ast
import builtins
from typing import Any, Iterable

SCHEMA = "BRAIN_EXPRESSION_OPERATOR_PACK_V1"
BUILTINS = frozenset(dir(builtins))
SKIP_AS_VALUE = (ast.Constant, ast.Tuple, ast.List, ast.Dict, ast.Set, ast.JoinedStr)


def _callee(call: ast.Call) -> tuple[str | None, str] | None:
    """(the receiver as text, the called name), or None when the call is not a name/attribute."""
    func = call.func
    if isinstance(func, ast.Attribute):
        return ast.unparse(func.value), func.attr
    if isinstance(func, ast.Name):
        return None, func.id
    return None


def calls(tree: ast.AST) -> list[tuple[ast.Call, tuple[str | None, str], tuple[str, ...],
                                       tuple[tuple[str | None, str], ...]]]:
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            key = _callee(node)
            if key is None:
                continue
            out.append((node, key,
                        tuple(ast.unparse(arg) for arg in node.args),
                        tuple((word.arg, ast.unparse(word.value)) for word in node.keywords)))
    return out


def method_renames(before: str, after: str) -> dict[tuple[str | None, str], str]:
    """The method renames one example shows: same receiver, same arguments, one new name.

    A change that also changes an argument, adds a call, removes a call, or moves the receiver
    is not this operator and gives an empty mapping.
    """
    try:
        old, new = ast.parse(before), ast.parse(after)
    except (SyntaxError, ValueError):
        return {}
    one, two = calls(old), calls(new)
    if len(one) != len(two):
        return {}
    found: dict[tuple[str | None, str], set[str]] = {}
    for (_, key_a, args_a, words_a), (_, key_b, args_b, words_b) in zip(one, two):
        if key_a[0] != key_b[0] or key_a[1] == key_b[1]:
            continue
        if args_a != args_b or words_a != words_b:
            continue
        found.setdefault(key_a, set()).add(key_b[1])
    return {key: next(iter(names)) for key, names in found.items() if len(names) == 1}


def _defined(tree: ast.AST) -> set[str]:
    names = set(BUILTINS)
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(node.name)
        elif isinstance(node, ast.Name) and isinstance(node.ctx, (ast.Store, ast.Param)):
            names.add(node.id)
        elif isinstance(node, ast.arg):
            names.add(node.arg)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.asname or alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                names.add(alias.asname or alias.name)
    return names


class _Rename(ast.NodeTransformer):
    def __init__(self, mapping: dict[tuple[str | None, str], str], defined: set[str]):
        self.mapping, self.defined, self.count = mapping, defined, 0

    def visit_Call(self, node: ast.Call):
        self.generic_visit(node)
        key = _callee(node)
        if key in self.mapping:
            new = self.mapping[key]
            if key[0] is None and new not in self.defined:
                return node                      # a bare name the target does not define
            func = node.func
            if isinstance(func, ast.Attribute):
                node.func = ast.Attribute(value=func.value, attr=new, ctx=func.ctx)
            else:
                node.func = ast.Name(id=new, ctx=func.ctx)
            self.count += 1
        return node


def apply_method_renames(target: str,
                         mapping: dict[tuple[str | None, str], str]) -> tuple[str | None, int]:
    """The target with the renames, or (None, 0) when nothing applies or it would not parse."""
    if not mapping:
        return None, 0
    try:
        tree = ast.parse(target)
    except (SyntaxError, ValueError):
        return None, 0
    change = _Rename(mapping, _defined(tree))
    change.visit(tree)
    if not change.count:
        return None, 0
    ast.fix_missing_locations(tree)
    try:
        text = ast.unparse(tree)
        ast.parse(text)
    except (SyntaxError, ValueError):
        return None, 0
    return text, change.count


def _joined(node: ast.BinOp) -> ast.JoinedStr | None:
    """A string constant plus one expression, as an f-string's parts; None for every other shape."""
    if not isinstance(node.op, ast.Add):
        return None
    left, right = node.left, node.right
    if isinstance(left, ast.Constant) and isinstance(left.value, str) and not isinstance(right, SKIP_AS_VALUE):
        return ast.JoinedStr(values=[ast.Constant(value=left.value),
                                     ast.FormattedValue(value=right, conversion=-1)])
    if isinstance(right, ast.Constant) and isinstance(right.value, str) and not isinstance(left, SKIP_AS_VALUE):
        return ast.JoinedStr(values=[ast.FormattedValue(value=left, conversion=-1),
                                     ast.Constant(value=right.value)])
    return None


class _FString(ast.NodeTransformer):
    def __init__(self):
        self.count = 0

    def visit_BinOp(self, node: ast.BinOp):
        self.generic_visit(node)
        joined = _joined(node)
        if joined is None:
            return node
        self.count += 1
        return joined


def shows_fstring_change(before: str, after: str) -> bool:
    """Did the example turn a string concatenation into an f-string?"""
    try:
        old, new = ast.parse(before), ast.parse(after)
    except (SyntaxError, ValueError):
        return False
    if not any(isinstance(node, ast.JoinedStr) for node in ast.walk(new)):
        return False
    return any(_joined(node) is not None for node in ast.walk(old)
               if isinstance(node, ast.BinOp))


def apply_fstring(target: str) -> tuple[str | None, int]:
    """Every string-constant concatenation in the target as an f-string.

    This is the candidate generator: it does not know which concatenations the change was about.
    A caller with a test keeps only the candidates the test accepts.
    """
    try:
        tree = ast.parse(target)
    except (SyntaxError, ValueError):
        return None, 0
    change = _FString()
    change.visit(tree)
    if not change.count:
        return None, 0
    ast.fix_missing_locations(tree)
    try:
        text = ast.unparse(tree)
        ast.parse(text)
    except (SyntaxError, ValueError):
        return None, 0
    return text, change.count


def apply_pack(target: str, before: str, after: str,
               operators: Iterable[str] = ("rename", "fstring")) -> dict[str, Any]:
    """Apply the named operators to the target. Returns the text and what each operator did."""
    chosen = set(operators)
    text = target
    did: dict[str, int] = {}
    if "fstring" in chosen and shows_fstring_change(before, after):
        changed, count = apply_fstring(text)
        if changed is not None:
            text, did["fstring"] = changed, count
    if "rename" in chosen:
        mapping = method_renames(before, after)
        changed, count = apply_method_renames(text, mapping)
        if changed is not None:
            text, did["rename"] = changed, count
    return {"text": text if did else None, "did": did}
