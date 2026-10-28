# PROJECT_BRAIN
"""Fault-prioritized candidate generation and parallel candidate evaluation.

The repair loop's bottleneck is neither localization nor the gate: on the
measured golden run 2.5 of 3.3 seconds were candidate tests, run one at a time,
in file order, from a mutation table that cannot express Add->Mult.  This module
is the generator and the evaluator; the loop around it lives in
software_diagnose_then_repair_v1.

Generator (what the literature calls template-based repair -- PAR, SPR/Prophet
templates, Kali's checks -- restricted to edits whose rendering is exact):

    COMPARE_SWAP      every comparison operator -> each of the other five
    BINOP_DROP        a - b -> a ; a - b -> b   (a spurious term removed)
    BINOP_SWAP        every arithmetic operator -> each other arithmetic operator
    BOOL_SWAP         and <-> or
    OPERAND_SWAP      a - b -> b - a   (non-commutative binops and comparisons)
    NOT_TOGGLE        cond -> not cond ; not cond -> cond   (if/while/return/assert tests)
    CONSTANT_REPLACE  bools flipped; numbers -> 0, 1, -1, n-1, n+1, test literals
    STRING_REPLACE    string literal -> each string literal the tests mention
    EXPR_EXTEND       return w -> return w * h   (one in-scope name joined to the
                      returned/assigned expression; the only template that adds code)
    GUARD_INSERT      if <param> is None: return <c> / if not <param>: return <c>
                      in front of a function's first statement
    EXPR_SYNTH        the returned expression replaced by one synthesized from the
                      tests' own input/output pairs (expression_synthesis_v1; >= 2
                      examples required), placed after the cheap edits on the top line
    COMPOSE           two single edits inside one statement (compose_pairs), tried
                      only after every single edit failed, ordered by the singles'
                      fitness (fewest failing tests), bounded

Ordering is spectrum-first: candidates on lines the localizer or the traceback
named come first in rank order; the rest in file order.  Measured on the golden
fixture: the winning edit moves from the 4th candidate tried to the 1st.

Evaluator: K scratch copies of the tree (one per worker), each candidate written
into its own copy, tested with the caller's pytest argv (confined under
confine_v1 when the host allows it), restored, and the first green candidate
replayed twice before it is reported.  A global deadline stops the search in
the middle of a batch; the result says how many were tested and why it stopped.
"""
from __future__ import annotations

import ast
import json
import concurrent.futures as cf
import hashlib
import os
import pathlib
import shutil
import threading
import time
from typing import Any, Callable, Iterable, Iterator

_ARITH = [ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv, ast.Mod, ast.Pow]
_CMP = [ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE]
_CMP_PAIRS = {ast.Is: ast.IsNot, ast.IsNot: ast.Is, ast.In: ast.NotIn, ast.NotIn: ast.In}
_BOOL = {ast.And: ast.Or, ast.Or: ast.And}
_SKIP = {".git", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", "node_modules"}


def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _descriptor(node: ast.AST, kind: str, detail: str) -> dict[str, Any]:
    return {"kind": kind, "detail": detail, "lineno": getattr(node, "lineno", None),
            "col_offset": getattr(node, "col_offset", None), "end_lineno": getattr(node, "end_lineno", None),
            "end_col_offset": getattr(node, "end_col_offset", None)}


def _span(node: ast.AST) -> tuple | None:
    vals = (getattr(node, "lineno", None), getattr(node, "col_offset", None),
            getattr(node, "end_lineno", None), getattr(node, "end_col_offset", None))
    return None if None in vals else vals


def _byte_offset(lines: list[bytes], lineno: int, col: int) -> int:
    return sum(len(x) for x in lines[: lineno - 1]) + col


class _Block(ast.AST):
    """Several statements rendered in place of one (used by GUARD_INSERT)."""
    _fields = ("body",)

    def __init__(self, body: list[ast.stmt]):
        super().__init__()
        self.body = body


def _first_statements(tree: ast.AST) -> set[int]:
    return {id(fn.body[0]) for fn in ast.walk(tree)
            if isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)) and fn.body
            and not (isinstance(fn.body[0], ast.Expr) and isinstance(getattr(fn.body[0], "value", None), ast.Constant))}


def _params_of(tree: ast.AST, stmt: ast.stmt) -> list[str]:
    for fn in ast.walk(tree):
        if isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)) and fn.body and fn.body[0] is stmt:
            return [a.arg for a in [*fn.args.posonlyargs, *fn.args.args] if a.arg not in ("self", "cls")]
    return []


def _unparse(node: ast.AST) -> str:
    if isinstance(node, _Block):
        return "\n".join(ast.unparse(b) for b in node.body)
    return ast.unparse(node)


_KEYWORDS_BEFORE_PAREN = {b"return", b"in", b"if", b"elif", b"while", b"else", b"and", b"or", b"not", b"yield",
                          b"await", b"assert", b"lambda", b"is", b"for", b"with", b"del", b"print"}


def _grouping_paren(raw: bytes, at: int) -> bool:
    """True when the ``(`` at ``at`` groups an expression rather than opening a call,
    a subscript's callee or a decorator: what precedes it is an operator, a delimiter,
    a keyword, or nothing."""
    i = at - 1
    while i >= 0 and raw[i:i + 1] in (b" ", b"\t"):
        i -= 1
    if i < 0 or raw[i:i + 1] in (b"\n", b"\r"):
        return True
    c = raw[i:i + 1]
    if c in b"=+-*/%<>!&|^~,(:[{@;":
        return True
    if c in b")]}.\"'":
        return False
    if c.isalnum() or c == b"_":
        j = i
        while j >= 0 and (raw[j:j + 1].isalnum() or raw[j:j + 1] == b"_"):
            j -= 1
        return raw[j + 1:i + 1] in _KEYWORDS_BEFORE_PAREN
    return True


def _render(source_text: str, node: ast.AST, replacement: ast.AST) -> str | None:
    span = _span(node)
    if span is None:
        return None
    ast.fix_missing_locations(replacement)
    try:
        text = _unparse(replacement)
    except Exception:  # noqa: BLE001
        return None
    raw = source_text.encode("utf-8")
    lines = raw.splitlines(keepends=True)
    start = _byte_offset(lines, span[0], span[1])
    end = _byte_offset(lines, span[2], span[3])
    if isinstance(replacement, (ast.Name, ast.Constant, ast.Attribute, ast.Call, ast.Subscript)):
        # the span sat inside its own GROUPING parentheses: (w + 1) -> (w) is not an edit
        # anyone writes; the parentheses of a call `f(w + 1)` are not grouping (measured:
        # stripping them rendered `out.append(x - 1)` as `out.appendx`)
        while raw[start - 1:start] == b"(" and raw[end:end + 1] == b")" and start > 0 \
                and _grouping_paren(raw, start - 1):
            start, end = start - 1, end + 1
    if "\n" in text:
        # a multi-line rendering (statement-level edit): continuation lines take
        # the column of the statement they replace, so the block stays inside it
        indent = " " * span[1]
        text = ("\n" + indent).join(text.split("\n"))
    candidate = (raw[:start] + text.encode("utf-8") + raw[end:]).decode("utf-8")
    try:
        ast.parse(candidate)
    except SyntaxError:
        return None
    return candidate


def test_literals(test_paths: Iterable[pathlib.Path]) -> tuple[list[Any], list[str]]:
    nums: list[Any] = []
    strings: list[str] = []
    for p in test_paths:
        try:
            tree = ast.parse(p.read_text(encoding="utf-8"))
        except (OSError, SyntaxError, UnicodeDecodeError):
            continue
        for n in ast.walk(tree):
            if isinstance(n, ast.Constant):
                v = n.value
                if isinstance(v, bool):
                    continue
                if isinstance(v, (int, float)) and v not in nums:
                    nums.append(v)
                elif isinstance(v, str) and v not in strings and len(v) <= 80:
                    strings.append(v)
    return nums, strings


def _scope_names(tree: ast.AST) -> dict[int, list[str]]:
    """id(node) -> names in scope at that node: the owning function's parameters and
    the locals assigned before the node's line.  Module level: assigned module names."""
    out: dict[int, list[str]] = {}
    for fn in ast.walk(tree):
        if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        params = [a.arg for a in [*fn.args.posonlyargs, *fn.args.args, *fn.args.kwonlyargs] if a.arg not in ("self", "cls")]
        assigned: list[tuple[int, str]] = []
        for n in ast.walk(fn):
            if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store):
                assigned.append((n.lineno, n.id))
        for n in ast.walk(fn):
            if n is fn or not hasattr(n, "lineno"):
                continue
            names = list(params)
            for ln, name in assigned:
                if ln < n.lineno and name not in names:
                    names.append(name)
            out[id(n)] = names
    return out


def _edits(tree: ast.AST, nums: list[Any], strings: list[str]) -> Iterator[tuple[ast.AST, str, str, Callable[[ast.AST], ast.AST]]]:
    """Yield (node, kind, detail, replacer).  Replacers build a NEW node from the original."""
    cond_tests = {id(n.test) for n in ast.walk(tree) if isinstance(n, (ast.If, ast.While, ast.IfExp, ast.Assert))}
    returns = {id(n.value) for n in ast.walk(tree) if isinstance(n, ast.Return) and n.value is not None}
    assigned_values = {id(n.value) for n in ast.walk(tree) if isinstance(n, (ast.Assign, ast.AugAssign, ast.AnnAssign)) and n.value is not None}
    scope = _scope_names(tree)
    guard_consts: list[Any] = [None, 0]
    for v in nums + strings:
        if v not in guard_consts:
            guard_consts.append(v)
    for node in ast.walk(tree):
        if _span(node) is None:
            continue
        # a missing term: extend the returned/assigned expression by one in-scope name
        # (return w -> return w * h).  The original stays a sub-expression: smallest edit
        # that adds code, and the one PAR/Prophet-style template that adds code at all.
        if id(node) in returns or id(node) in assigned_values:
            used = {n.id for n in ast.walk(node) if isinstance(n, ast.Name)}
            for name in scope.get(id(node), []):
                if name in used:
                    continue
                for t in (ast.Mult, ast.Add, ast.Sub, ast.FloorDiv, ast.Div, ast.Mod):
                    yield node, "EXPR_EXTEND", "<expr> " + t.__name__ + " " + name, (
                        lambda n, t=t, name=name: ast.BinOp(left=n, op=t(), right=ast.Name(id=name, ctx=ast.Load())))
                    if t in (ast.Sub, ast.FloorDiv, ast.Div, ast.Mod):
                        yield node, "EXPR_EXTEND", name + " " + t.__name__ + " <expr>", (
                            lambda n, t=t, name=name: ast.BinOp(left=ast.Name(id=name, ctx=ast.Load()), op=t(), right=n))
        # a missing guard: the function's first statement gets `if <param> is None: return <c>`
        # / `if not <param>: return <c>` in front of it (Kali/PAR null-check template)
        if isinstance(node, ast.stmt) and id(node) in _first_statements(tree):
            for name in _params_of(tree, node):
                for cond_kind in ("is None", "not"):
                    for c in guard_consts:
                        test = (ast.Compare(left=ast.Name(id=name, ctx=ast.Load()), ops=[ast.Is()], comparators=[ast.Constant(value=None)])
                                if cond_kind == "is None" else ast.UnaryOp(op=ast.Not(), operand=ast.Name(id=name, ctx=ast.Load())))
                        yield node, "GUARD_INSERT", ("if " + name + " is None" if cond_kind == "is None" else "if not " + name) + ": return " + repr(c), (
                            lambda n, test=test, c=c: _Block([ast.If(test=test, body=[ast.Return(value=ast.Constant(value=c))], orelse=[]), n]))
        if isinstance(node, ast.Compare) and len(node.ops) == 1:
            op = type(node.ops[0])
            targets = [t for t in _CMP if t is not op] if op in _CMP else ([_CMP_PAIRS[op]] if op in _CMP_PAIRS else [])
            for t in targets:
                yield node, "COMPARE_SWAP", op.__name__ + "->" + t.__name__, (
                    lambda n, t=t: ast.Compare(left=n.left, ops=[t()], comparators=n.comparators))
            if op in (ast.Lt, ast.LtE, ast.Gt, ast.GtE, ast.Sub, ast.In, ast.NotIn):
                yield node, "OPERAND_SWAP", op.__name__, (
                    lambda n: ast.Compare(left=n.comparators[0], ops=[type(n.ops[0])()], comparators=[n.left]))
        if isinstance(node, ast.BinOp) and type(node.op) in _ARITH:
            op = type(node.op)
            # the smallest edit first: a spurious term dropped (w * h - 1 -> w * h)
            yield node, "BINOP_DROP", "keep left", (lambda n: n.left)
            yield node, "BINOP_DROP", "keep right", (lambda n: n.right)
            for t in _ARITH:
                if t is not op:
                    yield node, "BINOP_SWAP", op.__name__ + "->" + t.__name__, (
                        lambda n, t=t: ast.BinOp(left=n.left, op=t(), right=n.right))
            if op in (ast.Sub, ast.Div, ast.FloorDiv, ast.Mod, ast.Pow):
                yield node, "OPERAND_SWAP", op.__name__, (
                    lambda n: ast.BinOp(left=n.right, op=type(n.op)(), right=n.left))
        if isinstance(node, ast.BoolOp):
            t = _BOOL[type(node.op)]
            yield node, "BOOL_SWAP", type(node.op).__name__ + "->" + t.__name__, (
                lambda n, t=t: ast.BoolOp(op=t(), values=n.values))
        if id(node) in cond_tests or id(node) in returns:
            if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
                yield node, "NOT_TOGGLE", "drop not", (lambda n: n.operand)
            elif not isinstance(node, ast.Constant):
                yield node, "NOT_TOGGLE", "add not", (lambda n: ast.UnaryOp(op=ast.Not(), operand=n))
        if isinstance(node, ast.Constant):
            v = node.value
            if isinstance(v, bool):
                reps: list[Any] = [not v]
            elif isinstance(v, int):
                reps = [x for x in [0, 1, -1, v - 1, v + 1, *nums] if x != v]
            elif isinstance(v, float):
                reps = [x for x in [0, 1, -1, *nums] if x != v]
            elif isinstance(v, str):
                reps = [s for s in strings if s != v]
            else:
                continue
            seen_vals: list[Any] = []
            for r in reps:
                if any(type(r) is type(s) and r == s for s in seen_vals):
                    continue
                seen_vals.append(r)
                kind = "STRING_REPLACE" if isinstance(v, str) else "CONSTANT_REPLACE"
                yield node, kind, repr(v) + "->" + repr(r), (lambda n, r=r: ast.Constant(value=r))


# within one line: the cheapest, most specific edits first; guards are the most
# speculative (many of them, any one of them plausible) and go last
_KIND_ORDER = {"BINOP_DROP": 0, "COMPARE_SWAP": 0, "BINOP_SWAP": 0, "BOOL_SWAP": 0, "NOT_TOGGLE": 0, "OPERAND_SWAP": 0,
               "EXPR_SYNTH": 0.5, "HOLE_SYNTH": 0.5,            # synthesized: after the cheap swaps, before constants
               "CONSTANT_REPLACE": 1, "STRING_REPLACE": 1, "EXPR_EXTEND": 1,
               "STMT_SWAP": 2, "STMT_DELETE": 2, "RETURN_INSERT": 2, "STMT_INSERT": 2, "GUARD_INSERT": 3}


def generate(source_text: str, nums: list[Any], strings: list[str],
             priority_lines: Iterable[int] = ()) -> list[tuple[dict[str, Any], str]]:
    """All distinct candidates for one file, spectrum-first, each parsed once."""
    tree = ast.parse(source_text)
    rank = {int(ln): i for i, ln in enumerate(priority_lines) if ln is not None}
    rows: list[tuple[tuple, dict[str, Any], str]] = []
    seen: set[str] = set()
    edits: dict[str, tuple[tuple, Callable[[ast.AST], ast.AST]]] = {}
    for node, kind, detail, replacer in _edits(tree, nums, strings):
        candidate = _render(source_text, node, replacer(node))
        if candidate is None or candidate == source_text:
            continue
        digest = _sha(candidate.encode("utf-8"))
        if digest in seen:
            continue
        seen.add(digest)
        line = getattr(node, "lineno", 10**9)
        key = (rank.get(line, len(rank)), line, _KIND_ORDER.get(kind, 1), getattr(node, "col_offset", 0), len(rows))
        edits[digest] = (_node_key(node), replacer)
        rows.append((key, {**_descriptor(node, kind, detail), "candidate_sha256": digest}, candidate))
    rows.sort(key=lambda r: r[0])
    out = [(d, c) for _, d, c in rows]
    _LAST_EDITS[id(out)] = edits
    if len(_EDITS_BY_SHA) > 200000:
        _EDITS_BY_SHA.clear()
    _EDITS_BY_SHA.update(edits)
    return out


_LAST_EDITS: dict[int, dict[str, tuple[tuple, Callable[[ast.AST], ast.AST]]]] = {}
_EDITS_BY_SHA: dict[str, tuple[tuple, Callable[[ast.AST], ast.AST]]] = {}   # survives list merges/insertions


def _node_key(node: ast.AST) -> tuple:
    return (type(node).__name__, *(_span(node) or (None,) * 4))


class _Apply(ast.NodeTransformer):
    def __init__(self, table: dict[tuple, Callable[[ast.AST], ast.AST]]):
        self.table = table
        self.applied = 0

    def generic_visit(self, node: ast.AST) -> ast.AST:
        k = _node_key(node) if hasattr(node, "lineno") else None
        node = super().generic_visit(node)   # inner edits first ...
        if k in self.table:
            self.applied += 1
            return self.table[k](node)       # ... then the outer one, on the edited subtree
        return node


def compose_pairs(source_text: str, singles: list[tuple[dict[str, Any], str]], order: list[int],
                  limit: int = 300) -> list[tuple[dict[str, Any], str]]:
    """Two single edits applied together, for pairs inside one statement.

    ``order`` indexes into ``singles`` (1-based, best first -- the caller's fitness
    ranking).  The statement that owns both edits is re-rendered from the AST
    and spliced over its own span, so formatting changes stay inside that one
    statement.  Nested edits compose outer-first on the original subtree.
    """
    edits = {**_EDITS_BY_SHA, **_LAST_EDITS.get(id(singles), {})}
    tree = ast.parse(source_text)
    stmt_of: dict[tuple, ast.stmt] = {}
    for st in ast.walk(tree):            # breadth-first: the last statement seen is the innermost
        if isinstance(st, ast.stmt):
            for n in ast.walk(st):
                if hasattr(n, "lineno"):
                    stmt_of[_node_key(n)] = st
    out: list[tuple[dict[str, Any], str]] = []
    seen: set[str] = {_sha(c.encode("utf-8")) for _, c in singles}   # a pair equal to a single is not new
    seen.add(_sha(source_text.encode("utf-8")))
    raw = source_text.encode("utf-8")
    lines = raw.splitlines(keepends=True)
    for a_i in range(len(order)):
        for b_i in range(a_i + 1, len(order)):
            if len(out) >= limit:
                return out
            da, ca = singles[order[a_i] - 1]
            db, cb = singles[order[b_i] - 1]
            ea, eb = edits.get(da["candidate_sha256"]), edits.get(db["candidate_sha256"])
            if not ea or not eb or ea[0] == eb[0]:
                continue
            if da["kind"] == "GUARD_INSERT" or db["kind"] == "GUARD_INSERT":
                continue
            sa, sb = stmt_of.get(ea[0]), stmt_of.get(eb[0])
            if sa is None or sa is not sb:
                continue
            import copy as _copy
            st = _copy.deepcopy(sa)
            ap = _Apply({ea[0]: ea[1], eb[0]: eb[1]})
            new_st = ap.visit(st)
            if ap.applied != 2:
                continue
            ast.fix_missing_locations(new_st)
            try:
                text = ast.unparse(new_st)
            except Exception:  # noqa: BLE001
                continue
            span = _span(sa)
            start, end = _byte_offset(lines, span[0], span[1]), _byte_offset(lines, span[2], span[3])
            indent = " " * span[1]
            text = ("\n" + indent).join(text.split("\n"))
            candidate = (raw[:start] + text.encode("utf-8") + raw[end:]).decode("utf-8")
            try:
                ast.parse(candidate)
            except SyntaxError:
                continue
            digest = _sha(candidate.encode("utf-8"))
            if candidate == source_text or digest in seen:
                continue
            seen.add(digest)
            out.append(({"kind": "COMPOSE", "detail": da["kind"] + " " + da["detail"] + " + " + db["kind"] + " " + db["detail"],
                         "lineno": sa.lineno, "col_offset": sa.col_offset, "end_lineno": sa.end_lineno,
                         "end_col_offset": sa.end_col_offset, "parts": [order[a_i], order[b_i]],
                         "candidate_sha256": digest}, candidate))
    return out


def _purge_bytecode(source: pathlib.Path) -> None:
    cache = source.parent / "__pycache__"
    if cache.is_dir():
        for f in cache.glob(source.stem + ".*.pyc"):
            try:
                f.unlink()
            except OSError:
                pass


Candidate = "str | dict[str, str]"   # one file's full text, or {rel: text} for a patch set


def candidate_files(target_rel: str, text: Any) -> dict[str, str]:
    """A candidate is the target file's text, or a patch set {rel: text} spanning files."""
    return dict(text) if isinstance(text, dict) else {target_rel: text}


def write_candidate(copy: pathlib.Path, target_rel: str, text: Any) -> None:
    for rel, t in candidate_files(target_rel, text).items():
        (copy / rel).write_text(t, encoding="utf-8")
        _purge_bytecode(copy / rel)


def originals_of(tree: pathlib.Path, target_rel: str, candidates: list[tuple[dict[str, Any], Any]]) -> dict[str, bytes]:
    rels = {target_rel}
    for _, t in candidates:
        if isinstance(t, dict):
            rels.update(t)
    return {rel: (tree / rel).read_bytes() for rel in sorted(rels)}


def restore_candidate(copy: pathlib.Path, originals: dict[str, bytes]) -> None:
    for rel, raw in originals.items():
        (copy / rel).write_bytes(raw)
        _purge_bytecode(copy / rel)


def _changed_ranges(original: list[str], text: list[str]) -> list[tuple[int, int, list[str]]]:
    import difflib
    out = []
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, original, text, autojunk=False).get_opcodes():
        if tag != "equal":
            out.append((i1, i2, text[j1:j2]))
    return out


def merge_disjoint(original_text: str, a: str, b: str) -> str | None:
    """Both edits spliced onto the original when their changed line ranges do not overlap
    (two hunks in one file); None when they touch the same lines."""
    orig = original_text.splitlines(keepends=True)
    ra, rb = _changed_ranges(orig, a.splitlines(keepends=True)), _changed_ranges(orig, b.splitlines(keepends=True))
    if not ra or not rb:
        return None
    for i1, i2, _ in ra:
        for k1, k2, _ in rb:
            if not (i2 <= k1 or k2 <= i1) or (i1 == k1 and i2 == k2):
                return None
    out, pos = [], 0
    for i1, i2, rep in sorted(ra + rb):
        out += orig[pos:i1] + rep
        pos = i2
    out += orig[pos:]
    merged = "".join(out)
    try:
        ast.parse(merged)
    except SyntaxError:
        return None
    return merged


def compose_hunks(originals: dict[str, str], pools: list[tuple[str, list[tuple[dict[str, Any], str]], list[int]]],
                  limit: int = 200) -> list[tuple[dict[str, Any], Any]]:
    """Two single edits on disjoint hunks -- different lines of one file, or two
    files -- applied together (GenProg's multi-edit patches, bounded to pairs).

    ``pools`` = [(rel, singles, order)] per file, ``order`` 1-based into ``singles``,
    best fitness first.  Pairs are emitted by the sum of their ranks, so the pair of
    the two best singles comes first, then (1st, 2nd) / (2nd, 1st) ...  Output
    candidates are patch sets {rel: text}; their descriptor names both parts.
    """
    items: list[tuple[int, str, dict[str, Any], str]] = []    # (rank, rel, desc, text)
    for rel, singles, order in pools:
        for r, idx in enumerate(order):
            d, t = singles[idx - 1]
            if d.get("kind") in ("GUARD_INSERT", "COMPOSE", "COMPOSE_HUNKS"):
                continue
            items.append((r, rel, d, t))
    pairs: list[tuple[int, int, int]] = []                    # (rank sum, i, j)
    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            pairs.append((items[i][0] + items[j][0], i, j))
    pairs.sort()
    out: list[tuple[dict[str, Any], Any]] = []
    seen: set[str] = set()
    for _, i, j in pairs:
        if len(out) >= limit:
            break
        (_, ra, da, ta), (_, rb, db, tb) = items[i], items[j]
        if ra == rb:
            merged = merge_disjoint(originals[ra], ta, tb)
            if merged is None:
                continue
            files = {ra: merged}
        else:
            files = {ra: ta, rb: tb}
        digest = _sha(json.dumps(files, sort_keys=True).encode("utf-8"))
        if digest in seen:
            continue
        seen.add(digest)
        out.append(({"kind": "COMPOSE_HUNKS", "lineno": da.get("lineno"), "files": sorted(files),
                     "detail": ra + ":" + str(da.get("lineno")) + " " + str(da.get("kind")) + " " + str(da.get("detail"))
                     + " + " + rb + ":" + str(db.get("lineno")) + " " + str(db.get("kind")) + " " + str(db.get("detail")),
                     "parts": [dict(da, file=ra), dict(db, file=rb)], "candidate_sha256": digest}, files))
    return out


def evaluate(tree: pathlib.Path, target_rel: str, candidates: list[tuple[dict[str, Any], str]],
             run_tests: Callable[[pathlib.Path], int], *, workers: int, deadline: float,
             max_candidates: int, scratch: pathlib.Path, green_budget: int = 4,
             choose: Callable[[list[tuple[int, str]]], int] | None = None) -> dict[str, Any]:
    """Test candidates in parallel on per-worker copies of ``tree``.

    ``run_tests(copy_root)`` returns pytest's verdict as an int (0 = green) for
    that copy; it is the caller's runner, so confinement and argv are decided
    once, outside.

    A green candidate does not end the search by itself: the suite is the
    weakest oracle in the loop, and the first green edit is only the first
    the generator emitted (measured: ``w != 0`` before ``w > 0``).  The search
    goes on through the remaining candidates on the SAME line until
    ``green_budget`` greens are in hand, then ``choose(greens)`` (default: the
    first) picks one, and that one is replayed twice before it is reported.
    """
    workers = max(1, int(workers))
    copies: list[pathlib.Path] = []
    for i in range(workers):
        c = scratch / ("w" + str(i))
        shutil.copytree(tree, c, ignore=shutil.ignore_patterns(*_SKIP), dirs_exist_ok=True)
        copies.append(c)
    originals = originals_of(tree, target_rel, candidates)
    free: list[pathlib.Path] = list(copies)
    lock = threading.Lock()
    stop = threading.Event()
    attempts: list[dict[str, Any]] = []
    greens: list[tuple[int, str]] = []
    green_line: int | None = None
    stop_reason = "EXHAUSTED"
    tested = 0

    def restore(copy: pathlib.Path) -> None:
        restore_candidate(copy, originals)

    def one(index: int, desc: dict[str, Any], text: str) -> tuple[int, dict[str, Any], str, int, float]:
        with lock:
            copy = free.pop()
        try:
            if stop.is_set() or time.monotonic() >= deadline:
                return index, desc, text, -1, 0.0
            write_candidate(copy, target_rel, text)
            t0 = time.monotonic()
            rc = run_tests(copy)
            restore(copy)
            return index, desc, text, rc, time.monotonic() - t0
        finally:
            with lock:
                free.append(copy)

    def record(index: int, desc: dict[str, Any], text: str, rc: int, took: float) -> None:
        nonlocal tested, green_line
        tested += 1
        attempts.append({"index": index, "mutation": desc, "returncode": rc, "elapsed_s": round(took, 3)})
        if rc == 0:
            greens.append((index, text))
            if green_line is None:
                green_line = desc.get("lineno")

    pool = cf.ThreadPoolExecutor(max_workers=workers)
    winner: dict[str, Any] | None = None
    try:
        queue = list(enumerate(candidates[:max_candidates], 1))
        pending: set = set()
        while queue or pending:
            if greens and (len(greens) >= green_budget or not queue
                           or (green_line is not None and queue[0][1][0].get("lineno") != green_line)):
                stop.set()
                queue = []
            while queue and len(pending) < workers and not stop.is_set():
                i, (d, t) = queue.pop(0)
                pending.add(pool.submit(one, i, d, t))
            if not pending:
                break
            done, pending = cf.wait(pending, return_when=cf.FIRST_COMPLETED)
            for fut in done:
                index, desc, text, rc, took = fut.result()
                if rc != -1:
                    record(index, desc, text, rc, took)
            if time.monotonic() >= deadline and not greens:
                stop.set()
                stop_reason = "DEADLINE"
                queue = []
                break
        for fut in cf.as_completed(list(pending)) if pending else []:
            try:
                index, desc, text, rc, took = fut.result()
            except cf.CancelledError:
                continue
            if rc != -1:
                record(index, desc, text, rc, took)
        attempts.sort(key=lambda a: a["index"])
        # in-flight runs can finish after the budget is reached; keep the budget
        # deterministic (by search order), whatever the thread timing was
        greens.sort(key=lambda g: g[0])
        del greens[green_budget:]
        if greens:
            chosen = choose(greens) if choose else greens[0][0]
            text = next(t for i, t in greens if i == chosen)
            desc = next(a["mutation"] for a in attempts if a["index"] == chosen)
            copy = copies[0]
            replay = []
            for _ in range(2):
                write_candidate(copy, target_rel, text)
                replay.append(run_tests(copy))
                restore(copy)
            if all(r == 0 for r in replay):
                winner = {"index": chosen, "mutation": desc, "candidate": text, "replay_returncodes": replay}
                stop_reason = "VERIFIED"
            else:
                stop_reason = "FLAKY_REPLAY:" + str(replay)
        elif stop_reason == "EXHAUSTED" and len(candidates) > max_candidates:
            stop_reason = "MAX_CANDIDATES"
    finally:
        pool.shutdown(wait=True, cancel_futures=True)
        for c in copies:
            shutil.rmtree(c, ignore_errors=True)
    return {"winner": winner, "attempts": attempts, "tested_candidate_count": tested,
            "green_indices": [i for i, _ in greens], "candidate_count": len(candidates),
            "workers": workers, "stop_reason": stop_reason}


def evaluate_batch(tree: pathlib.Path, target_rel: str, candidates: list[tuple[dict[str, Any], str]],
                   judge_batch: Callable[[pathlib.Path, list[str], float], dict[int, int]],
                   run_tests: Callable[[pathlib.Path], int], *, workers: int, deadline: float,
                   max_candidates: int, scratch: pathlib.Path, green_budget: int = 4,
                   choose: Callable[[list[tuple[int, str]]], int] | None = None, batch: int = 32) -> dict[str, Any]:
    """Judge candidates in batches -- one judge process per worker copy -- then replay
    the chosen green under ``run_tests`` (real pytest) exactly as ``evaluate`` does.

    ``judge_batch(copy_root, texts, deadline)`` returns {position: failed_count} or
    {position: (failed_count, assertion_distance)} for the texts it managed to
    judge (0 = green); the distance orders composition, never decides.  Candidates are dealt to the
    workers round-robin in search order, so the earliest candidates are judged
    first on every worker; the budget keeps search-order semantics.
    """
    workers = max(1, int(workers))
    todo = candidates[:max_candidates]
    copies: list[pathlib.Path] = []
    for i in range(workers):
        c = scratch / ("j" + str(i))
        shutil.copytree(tree, c, ignore=shutil.ignore_patterns(*_SKIP), dirs_exist_ok=True)
        copies.append(c)
    originals = originals_of(tree, target_rel, candidates)
    verdicts: dict[int, int] = {}
    distances: dict[int, float] = {}
    stop_reason = "EXHAUSTED"
    winner: dict[str, Any] | None = None

    def judged_greens() -> list[tuple[int, str]]:
        # same semantics as evaluate: greens on the first green's line, by search order
        g = [(i + 1, todo[i][1]) for i in sorted(verdicts) if verdicts[i] == 0]
        if g and green_budget > 0:
            line = todo[g[0][0] - 1][0].get("lineno")
            g = [x for x in g if todo[x[0] - 1][0].get("lineno") == line][:green_budget]
        return g

    try:
        # rounds of workers*batch candidates in search order, so a search that is
        # green on its first line stops early instead of judging everything
        pos = 0
        with cf.ThreadPoolExecutor(max_workers=workers) as pool:
            while pos < len(todo) and time.monotonic() < deadline:
                chunks: list[list[int]] = [[] for _ in range(workers)]
                for idx in range(pos, min(len(todo), pos + workers * batch)):
                    chunks[(idx - pos) % workers].append(idx)
                pos = min(len(todo), pos + workers * batch)

                def one(w: int, chunks=chunks) -> dict[int, int]:
                    if not chunks[w]:
                        return {}
                    res = judge_batch(copies[w], [todo[i][1] for i in chunks[w]], deadline)
                    return {chunks[w][k]: rc for k, rc in res.items()}

                for part in pool.map(one, range(workers)):
                    for i, rc in part.items():
                        if isinstance(rc, tuple):
                            verdicts[i], distances[i] = int(rc[0]), float(rc[1])
                        else:
                            verdicts[i] = int(rc)
                g = judged_greens()
                if g and (len(g) >= green_budget or
                          (pos < len(todo) and todo[pos][0].get("lineno") != todo[g[0][0] - 1][0].get("lineno"))):
                    break
        attempts = [{"index": i + 1, "mutation": todo[i][0], "returncode": verdicts[i], "judge": "in_process",
                     **({"distance": distances[i]} if i in distances else {})}
                    for i in sorted(verdicts)]
        greens = judged_greens()
        if not greens and len(verdicts) < len(todo):
            stop_reason = "DEADLINE"
        if greens:
            chosen = choose(greens) if choose else greens[0][0]
            text = next(t for i, t in greens if i == chosen)
            copy = copies[0]
            replay = []
            for _ in range(2):
                write_candidate(copy, target_rel, text)
                replay.append(run_tests(copy))
                restore_candidate(copy, originals)
            if all(r == 0 for r in replay):
                winner = {"index": chosen, "mutation": todo[chosen - 1][0], "candidate": text, "replay_returncodes": replay}
                stop_reason = "VERIFIED"
            else:
                stop_reason = "FLAKY_REPLAY:" + str(replay)
                for a in attempts:
                    if a["index"] == chosen:
                        a["pytest_replay"] = replay
        elif stop_reason == "EXHAUSTED" and len(candidates) > max_candidates:
            stop_reason = "MAX_CANDIDATES"
    finally:
        for c in copies:
            shutil.rmtree(c, ignore_errors=True)
    return {"winner": winner, "attempts": attempts, "tested_candidate_count": len(verdicts),
            "green_indices": [i for i, _ in greens] if greens else [], "candidate_count": len(candidates),
            "workers": workers, "stop_reason": stop_reason, "judge": "in_process"}


def synthesized_candidates(source_text: str, lineno: int, expressions: list[str]) -> list[tuple[dict[str, Any], str]]:
    """EXPR_SYNTH rows: the value of the `return` on ``lineno`` (else the owning
    function's last return) replaced by each synthesized expression."""
    tree = ast.parse(source_text)
    target: ast.Return | None = None
    for fn in ast.walk(tree):
        if isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)) and fn.lineno <= lineno <= (fn.end_lineno or fn.lineno):
            rets = [n for n in ast.walk(fn) if isinstance(n, ast.Return) and n.value is not None]
            on_line = [r for r in rets if r.lineno == lineno]
            target = (on_line or rets or [None])[-1]
            break
    if target is None or target.value is None:
        return []
    out: list[tuple[dict[str, Any], str]] = []
    seen: set[str] = set()
    for expr in expressions:
        try:
            node = ast.parse(expr, mode="eval").body
        except SyntaxError:
            continue
        cand = _render(source_text, target.value, node)
        if cand is None or cand == source_text:
            continue
        digest = _sha(cand.encode("utf-8"))
        if digest in seen:
            continue
        seen.add(digest)
        out.append(({**_descriptor(target.value, "EXPR_SYNTH", "-> " + expr), "candidate_sha256": digest}, cand))
    return out


def hole_candidates(source_text: str, sites: list[dict[str, Any]]) -> list[tuple[dict[str, Any], str]]:
    """HOLE_SYNTH rows from hole_synthesis_v1 output: each site's span replaced by each
    expression that made the function agree with the tests' examples."""
    out: list[tuple[dict[str, Any], str]] = []
    seen: set[str] = set()
    lines = source_text.splitlines(keepends=True)
    for row in sites:
        site = row.get("site") or {}
        for expr in row.get("expressions") or []:
            i = int(site["lineno"]) - 1
            if not (0 <= i < len(lines)):
                continue
            ln = lines[i]
            kind, detail, order = "HOLE_SYNTH", str(site.get("kind")) + " -> " + expr, 0.5
            if site.get("target") and expr == site["target"]:
                # the synthesizer says the assignment should not change its target:
                # the honest edit is removing the statement, not writing `x = x`
                cand = "".join([*lines[:i], *lines[i + 1:]])
                kind, detail = "STMT_DELETE", "via hole: " + ln.strip()[:60]
                order = 0.5
            else:
                cand = "".join([*lines[:i], ln[:site["col_offset"]] + expr + ln[site["end_col_offset"]:], *lines[i + 1:]])
            if cand == source_text:
                continue
            try:
                ast.parse(cand)
            except SyntaxError:
                continue
            digest = _sha(cand.encode("utf-8"))
            if digest in seen:
                continue
            seen.add(digest)
            out.append(({"kind": kind, "detail": detail, "lineno": site["lineno"], "order": order,
                         "col_offset": site["col_offset"], "end_lineno": site["lineno"],
                         "end_col_offset": site["end_col_offset"], "candidate_sha256": digest}, cand))
    return out


_SIMPLE_STMT = (ast.Assign, ast.AugAssign, ast.AnnAssign, ast.Expr, ast.Return, ast.Raise, ast.Continue, ast.Break)


def _block(lines: list[str], st: ast.stmt) -> tuple[int, int]:
    return st.lineno - 1, (st.end_lineno or st.lineno)


def _indent_of(line: str) -> str:
    return line[:len(line) - len(line.lstrip())]


def _reindent(block: list[str], indent: str) -> list[str]:
    base = _indent_of(block[0])
    return [(indent + ln[len(base):]) if ln.startswith(base) else (indent + ln.lstrip()) for ln in block]


def _load_names(node: ast.AST) -> set[str]:
    return {n.id for n in ast.walk(node) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)}


def statement_candidates(source_text: str, priority_lines: Iterable[int], *, max_lines: int = 4,
                         max_donors: int = 24) -> list[tuple[dict[str, Any], str]]:
    """Statement-level edits around the suspicious lines (GenProg's operators under the
    plastic-surgery hypothesis, Barr et al. 2014: most fixes are already written
    somewhere in the same file):
      STMT_DELETE   the suspicious simple statement removed (never the only one in its block)
      STMT_SWAP     swapped with its previous / next simple sibling
      STMT_INSERT   a simple statement from elsewhere in the file -- same function first,
                    then by distance -- copied before / after it at its indentation, only
                    when every name it reads is bound in the owning function or module
      RETURN_INSERT `return <local>` appended to a function that falls off its end
    Whole-line operations; the result is a candidate for the judge, never a verdict."""
    try:
        tree = ast.parse(source_text)
    except SyntaxError:
        return []
    lines = source_text.splitlines(keepends=True)
    if lines and not lines[-1].endswith("\n"):
        lines[-1] += "\n"
    module_names = {n.name.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.Import) for n in n.names}
    for n in tree.body:
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            module_names.add(n.name)
        elif isinstance(n, ast.ImportFrom):
            module_names |= {a.asname or a.name for a in n.names}
        elif isinstance(n, ast.Assign):
            module_names |= {t.id for t in n.targets if isinstance(t, ast.Name)}
    import builtins as _b
    builtins_ = set(dir(_b))
    # owning function, parent body and index for every statement
    owner: dict[int, ast.FunctionDef] = {}
    parent: dict[int, tuple[list[ast.stmt], int]] = {}

    def walk(body: list[ast.stmt], fn: ast.FunctionDef | None) -> None:
        for i, st in enumerate(body):
            parent[id(st)] = (body, i)
            if fn is not None:
                owner[id(st)] = fn
            f2 = st if isinstance(st, ast.FunctionDef) else fn
            for field in ("body", "orelse", "finalbody"):
                sub = getattr(st, field, None)
                if isinstance(sub, list) and sub and isinstance(sub[0], ast.stmt):
                    walk(sub, f2)
            for h in getattr(st, "handlers", []) or []:
                walk(h.body, f2)

    walk(tree.body, None)
    all_simple = [st for st in ast.walk(tree) if isinstance(st, _SIMPLE_STMT) and id(st) in parent]
    fn_bound: dict[int, set[str]] = {}
    for st in all_simple:
        fn = owner.get(id(st))
        if fn is not None and id(fn) not in fn_bound:
            bound = {a.arg for a in [*fn.args.posonlyargs, *fn.args.args, *fn.args.kwonlyargs]}
            bound |= {n.id for n in ast.walk(fn) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store)}
            bound |= {n.target.id for n in ast.walk(fn) if isinstance(n, ast.For) and isinstance(n.target, ast.Name)}
            fn_bound[id(fn)] = bound
    rank = {int(ln): i for i, ln in enumerate(priority_lines) if ln is not None}
    out: list[tuple[tuple, dict[str, Any], str]] = []
    seen: set[str] = {_sha(source_text.encode("utf-8"))}

    def emit(key: tuple, st: ast.stmt, kind: str, detail: str, new_lines: list[str]) -> None:
        cand = "".join(new_lines)
        try:
            ast.parse(cand)
        except SyntaxError:
            return
        digest = _sha(cand.encode("utf-8"))
        if digest in seen:
            return
        seen.add(digest)
        out.append((key, {"kind": kind, "detail": detail, "lineno": st.lineno, "col_offset": 0,
                          "end_lineno": st.end_lineno, "end_col_offset": 0, "candidate_sha256": digest}, cand))

    done_fns: set[int] = set()
    for ln in list(rank)[:max_lines]:
        # innermost simple statement covering the line, else the innermost statement
        covering = [st for st in ast.walk(tree) if isinstance(st, ast.stmt) and id(st) in parent
                    and st.lineno <= ln <= (st.end_lineno or st.lineno) and not isinstance(st, (ast.FunctionDef, ast.ClassDef))]
        if not covering:
            continue
        covering.sort(key=lambda st: ((st.end_lineno or st.lineno) - st.lineno, -st.lineno))
        st = covering[0]
        body, idx = parent[id(st)]
        a, b = _block(lines, st)
        indent = _indent_of(lines[a])
        fn = owner.get(id(st))
        base_key = (rank[ln], ln)
        if isinstance(st, _SIMPLE_STMT) and len(body) > 1:
            emit((*base_key, 2, 0), st, "STMT_DELETE", ast.unparse(st)[:60], lines[:a] + lines[b:])
        for j, name in ((idx - 1, "previous"), (idx + 1, "next")):
            if 0 <= j < len(body) and isinstance(body[j], _SIMPLE_STMT) and isinstance(st, _SIMPLE_STMT):
                oa, ob = _block(lines, body[j])
                lo, hi = (min(a, oa), max(b, ob))
                first, second = (lines[a:b], lines[oa:ob]) if a < oa else (lines[oa:ob], lines[a:b])
                emit((*base_key, 2, 1), st, "STMT_SWAP", "with " + name, lines[:lo] + second + first + lines[hi:])
        if fn is not None:
            bound = fn_bound.get(id(fn), set()) | module_names | builtins_
            donors = []
            for d in all_simple:
                if d is st or isinstance(d, (ast.Return, ast.Raise, ast.Continue, ast.Break)):
                    continue
                stores = {n.id for n in ast.walk(d) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store)}
                if d.lineno == d.end_lineno and (_load_names(d) | stores) <= bound:
                    donors.append(d)
            donors.sort(key=lambda d: (0 if owner.get(id(d)) is fn else 1, abs(d.lineno - st.lineno)))
            texts: list[str] = []
            for d in donors:
                t = lines[d.lineno - 1].strip()
                if t and t not in texts and t != lines[a].strip():
                    texts.append(t)
            for k, t in enumerate(texts[:max_donors]):
                emit((*base_key, 2, 2, k), st, "STMT_INSERT", "before: " + t[:60], lines[:a] + [indent + t + "\n"] + lines[a:])
                emit((*base_key, 2, 2, k), st, "STMT_INSERT", "after: " + t[:60], lines[:b] + [indent + t + "\n"] + lines[b:])
            if id(fn) not in done_fns and not isinstance(fn.body[-1], (ast.Return, ast.Raise)):
                done_fns.add(id(fn))
                last = fn.body[-1]
                la, lb = _block(lines, last)
                find = _indent_of(lines[la])
                stores = []
                for n in ast.walk(fn):
                    if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store) and n.id not in stores:
                        stores.append(n.id)
                for k, name in enumerate(stores[:6]):
                    emit((*base_key, 2, 3, k), last, "RETURN_INSERT", "return " + name,
                         lines[:lb] + [find + "return " + name + "\n"] + lines[lb:])
    out.sort(key=lambda r: r[0])
    return [(d, c) for _, d, c in out]


def merge_ranked(a: list[tuple[dict[str, Any], str]], b: list[tuple[dict[str, Any], str]],
                 priority_lines: Iterable[int]) -> list[tuple[dict[str, Any], str]]:
    """One spectrum-first list from two generators: (priority rank of the line, line,
    kind order, original position); duplicates by content dropped."""
    rank = {int(ln): i for i, ln in enumerate(priority_lines) if ln is not None}
    rows = []
    seen: set[str] = set()
    best: dict[str, tuple] = {}
    for pos, (d, c) in enumerate([*a, *b]):
        line = int(d.get("lineno") or 10**9)
        key = (rank.get(line, len(rank)), line, d.get("order", _KIND_ORDER.get(d.get("kind"), 1)), pos)
        sha = d["candidate_sha256"]
        if sha not in best or key < best[sha][0]:
            best[sha] = (key, d, c)
    rows = sorted(best.values(), key=lambda r: r[0])
    return [(d, c) for _, d, c in rows]


def insert_after_cheap_edits(candidates: list[tuple[dict[str, Any], str]], extra: list[tuple[dict[str, Any], str]]) -> list[tuple[dict[str, Any], str]]:
    """Place ``extra`` on the top-ranked line after its kind-order-0 edits (swaps, drops)
    and before constants/guards, keeping the spectrum-first order intact."""
    if not extra:
        return candidates
    if not candidates:
        return list(extra)
    top = candidates[0][0].get("lineno")
    have = {d["candidate_sha256"] for d, _ in candidates}
    extra = [(d, c) for d, c in extra if d["candidate_sha256"] not in have]
    pos = len(candidates)
    for i, (d, _) in enumerate(candidates):
        if d.get("lineno") != top or _KIND_ORDER.get(d.get("kind"), 1) >= 1:
            pos = i
            break
    return candidates[:pos] + extra + candidates[pos:]


def default_workers() -> int:
    n = os.cpu_count() or 1
    return max(1, min(n, 8))
