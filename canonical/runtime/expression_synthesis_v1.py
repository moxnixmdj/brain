# PROJECT_BRAIN
"""Bottom-up expression synthesis from input/output examples, with observational
equivalence pruning (the Transit / Escher / "enumerative PBE" idea, nothing new).

Where it sits in the repair loop: when the failing tests pin a function's value
on at least two inputs (`assert area(3, 4) == 12`, `assert area(2, 5) == 10`)
and no template edit explains them, the returned expression is a hole.  This
enumerates expressions over the function's parameters and a few constants,
smallest first, keeps one representative per OUTPUT VECTOR on the examples,
and returns the expressions whose vector equals the expected one.

Bounds: size <= 3 operators, enumeration cap, wall-clock cap, operand
magnitude cap (so `**` and `*` cannot build giants).  One example is not a
specification -- the caller requires >= 2 -- and the result is a CANDIDATE
list for the judge, the witness and the gate, never a verdict.
"""
from __future__ import annotations

import ast
import itertools
import time
from typing import Any

BINOPS: list[tuple[str, Any]] = [
    ("+", lambda a, b: a + b), ("-", lambda a, b: a - b), ("*", lambda a, b: a * b),
    ("//", lambda a, b: a // b), ("%", lambda a, b: a % b), ("/", lambda a, b: a / b),
]
MAX_ABS = 10 ** 9


class _Expr:
    __slots__ = ("src", "size", "consts", "params", "outs")

    def __init__(self, src: str, size: int, consts: int, params: frozenset, outs: tuple):
        self.src, self.size, self.consts, self.params, self.outs = src, size, consts, params, outs


def _ok(v: Any) -> bool:
    if isinstance(v, bool):
        return True
    if isinstance(v, int):
        return abs(v) <= MAX_ABS
    if isinstance(v, float):
        return v == v and abs(v) <= MAX_ABS
    return isinstance(v, (str, tuple, list, type(None))) and (not hasattr(v, "__len__") or len(v) <= 1000)


def _key(outs: tuple) -> tuple:
    return tuple((type(v).__name__, repr(v)) for v in outs)


def synthesize(params: list[str], examples: list[tuple[list[Any], Any]], *, constants: list[Any] = (),
               max_size: int = 3, max_results: int = 8, budget_s: float = 2.0, max_enum: int = 60000) -> dict[str, Any]:
    """examples: [(args, expected)] with args positional in ``params`` order."""
    if len(examples) < 2 or not params:
        return {"status": "UNDERSPECIFIED:" + str(len(examples)) + "_examples", "expressions": []}
    t0 = time.monotonic()
    expected = tuple(e for _, e in examples)
    want = _key(expected)
    by_size: dict[int, list[_Expr]] = {0: []}
    seen: set[tuple] = set()
    results: list[_Expr] = []

    def add(e: _Expr) -> bool:
        k = _key(e.outs)
        if k in seen:
            return False
        seen.add(k)
        by_size.setdefault(e.size, []).append(e)
        if k == want:
            results.append(e)
        return True

    for i, name in enumerate(params):
        add(_Expr(name, 0, 0, frozenset([name]), tuple(args[i] for args, _ in examples)))
    consts: list[Any] = []
    for c in [0, 1, 2, *constants]:
        if isinstance(c, (int, float)) and not isinstance(c, bool) and c not in consts:
            consts.append(c)
    for c in consts:
        add(_Expr(repr(c), 0, 1, frozenset(), tuple(c for _ in examples)))
    # unary: len(x), abs(x), -x  on the terminals
    for e in list(by_size[0]):
        for name, fn in (("len", len), ("abs", abs)):
            try:
                outs = tuple(fn(v) for v in e.outs)
            except Exception:
                continue
            if all(_ok(v) for v in outs):
                add(_Expr(name + "(" + e.src + ")", 1, e.consts, e.params, outs))
    enum = 0
    for size in range(1, max_size + 1):
        for ls in range(0, size):
            rs = size - 1 - ls
            for a, b in itertools.product(list(by_size.get(ls, [])), list(by_size.get(rs, []))):
                if a.consts and b.consts and not (a.params or b.params):
                    continue                       # constant folding is not synthesis
                for sym, fn in BINOPS:
                    enum += 1
                    if enum > max_enum or time.monotonic() - t0 > budget_s:
                        return _done(results, "BUDGET", enum, t0)
                    try:
                        outs = tuple(fn(x, y) for x, y in zip(a.outs, b.outs))
                    except Exception:
                        continue
                    if not all(_ok(v) for v in outs):
                        continue
                    src = "(" + a.src + " " + sym + " " + b.src + ")" if size > 1 else a.src + " " + sym + " " + b.src
                    add(_Expr(src, size, a.consts + b.consts, a.params | b.params, outs))
        if len(results) >= max_results:
            break
    return _done(results, "EXHAUSTED", enum, t0)


def _done(results: list[_Expr], why: str, enum: int, t0: float) -> dict[str, Any]:
    ranked = sorted(results, key=lambda e: (e.size, e.consts, -len(e.params), len(e.src)))
    return {"status": "FOUND:" + str(len(ranked)) if ranked else "NONE:" + why,
            "expressions": [_strip(e.src) for e in ranked[:8]], "enumerated": enum,
            "seconds": round(time.monotonic() - t0, 3), "stop": why}


def _strip(src: str) -> str:
    try:
        return ast.unparse(ast.parse(src, mode="eval"))
    except SyntaxError:
        return src


def examples_for(function: str, params: list[str], specs: list[dict[str, Any]]) -> list[tuple[list[Any], Any]]:
    """`assert f(<literals>) == <literal>` specs (from patch_inprocess_judge_v1.assert_specs) -> examples."""
    out: list[tuple[list[Any], Any]] = []
    for spec in specs:
        try:
            node = ast.parse(spec["expr"], mode="eval").body
        except SyntaxError:
            continue
        if not isinstance(node, ast.Call) or node.keywords or len(node.args) != len(params):
            continue
        f = node.func
        name = f.id if isinstance(f, ast.Name) else (f.attr if isinstance(f, ast.Attribute) else None)
        if name != function:
            continue
        try:
            args = [ast.literal_eval(a) for a in node.args]
        except (ValueError, TypeError, SyntaxError):
            continue
        row = (args, spec["expected"])
        if row not in out:
            out.append(row)
    return out
