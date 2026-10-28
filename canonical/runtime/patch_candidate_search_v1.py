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


def _render(source_text: str, node: ast.AST, replacement: ast.AST) -> str | None:
    span = _span(node)
    if span is None:
        return None
    ast.fix_missing_locations(replacement)
    try:
        text = ast.unparse(replacement)
    except Exception:  # noqa: BLE001
        return None
    raw = source_text.encode("utf-8")
    lines = raw.splitlines(keepends=True)
    start = _byte_offset(lines, span[0], span[1])
    end = _byte_offset(lines, span[2], span[3])
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


def _edits(tree: ast.AST, nums: list[Any], strings: list[str]) -> Iterator[tuple[ast.AST, str, str, Callable[[ast.AST], ast.AST]]]:
    """Yield (node, kind, detail, replacer).  Replacers build a NEW node from the original."""
    cond_tests = {id(n.test) for n in ast.walk(tree) if isinstance(n, (ast.If, ast.While, ast.IfExp, ast.Assert))}
    returns = {id(n.value) for n in ast.walk(tree) if isinstance(n, ast.Return) and n.value is not None}
    for node in ast.walk(tree):
        if _span(node) is None:
            continue
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


def generate(source_text: str, nums: list[Any], strings: list[str],
             priority_lines: Iterable[int] = ()) -> list[tuple[dict[str, Any], str]]:
    """All distinct candidates for one file, spectrum-first, each parsed once."""
    tree = ast.parse(source_text)
    rank = {int(ln): i for i, ln in enumerate(priority_lines) if ln is not None}
    rows: list[tuple[tuple, dict[str, Any], str]] = []
    seen: set[str] = set()
    for node, kind, detail, replacer in _edits(tree, nums, strings):
        candidate = _render(source_text, node, replacer(node))
        if candidate is None or candidate == source_text:
            continue
        digest = _sha(candidate.encode("utf-8"))
        if digest in seen:
            continue
        seen.add(digest)
        line = getattr(node, "lineno", 10**9)
        key = (rank.get(line, len(rank)), line, getattr(node, "col_offset", 0), len(rows))
        rows.append((key, {**_descriptor(node, kind, detail), "candidate_sha256": digest}, candidate))
    rows.sort(key=lambda r: r[0])
    return [(d, c) for _, d, c in rows]


def _purge_bytecode(source: pathlib.Path) -> None:
    cache = source.parent / "__pycache__"
    if cache.is_dir():
        for f in cache.glob(source.stem + ".*.pyc"):
            try:
                f.unlink()
            except OSError:
                pass


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
    original = (tree / target_rel).read_bytes()
    free: list[pathlib.Path] = list(copies)
    lock = threading.Lock()
    stop = threading.Event()
    attempts: list[dict[str, Any]] = []
    greens: list[tuple[int, str]] = []
    green_line: int | None = None
    stop_reason = "EXHAUSTED"
    tested = 0

    def restore(copy: pathlib.Path) -> None:
        (copy / target_rel).write_bytes(original)
        _purge_bytecode(copy / target_rel)

    def one(index: int, desc: dict[str, Any], text: str) -> tuple[int, dict[str, Any], str, int, float]:
        with lock:
            copy = free.pop()
        try:
            if stop.is_set() or time.monotonic() >= deadline:
                return index, desc, text, -1, 0.0
            src = copy / target_rel
            src.write_text(text, encoding="utf-8")
            _purge_bytecode(src)
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
                (copy / target_rel).write_text(text, encoding="utf-8")
                _purge_bytecode(copy / target_rel)
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


def default_workers() -> int:
    n = os.cpu_count() or 1
    return max(1, min(n, 8))
