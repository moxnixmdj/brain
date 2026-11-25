#!/usr/bin/env python3
"""How much of a real fix is LOAD-BEARING?  A judge-side measurement, not a solver.

WHY THIS EXISTS
---------------
`real_fix_oracle_baseline_v1.py` established that 70/87 corpus tasks are
well-formed and that 79% of the *upstream diffs* are large (multi-hunk, >3 lines
a side).  That number is about what the upstream author wrote.  It is NOT a
statement about what the failing tests *require*.

A fix commit often carries refactoring, docstrings, new helpers used only by
later commits, and formatting.  The recorded `failed_nodes` are the only
specification of the repair.  So the question that actually decides whether the
"single expression" wall is real is:

    what is the smallest subset of the upstream diff that still makes
    the recorded nodes pass?

This tool answers it by delta debugging (Zeller) the patch itself: start from the
full diff and greedily revert diff hunks, largest first, keeping every revert
that the tests still accept.

INTEGRITY -- READ THIS BEFORE QUOTING A NUMBER
----------------------------------------------
This is a MEASUREMENT and it uses `after`, which the solver arm never sees.
It computes an upper bound on the required repair size, not a solve rate.
A task whose minimal patch is 2 lines is NOT thereby solved: finding those 2
lines without seeing the fix is the whole problem.  Any report must keep those
two claims apart.

The oracle during minimisation is the corpus's own rule (`failed_nodes` pass).
That is weaker than "the repair breaks nothing", so the final minimal patch is
re-checked against the whole test FILE as a failure-subset test, and that
result is recorded per task (`file_subset_ok`).  A minimal patch that satisfies
the recorded nodes but breaks the rest of its own file is reported, not hidden.

AUTHORITY: NONE.  Producer-run sandbox measurement.  No model, no network at
decision time, no spend.

Usage
-----
    python3 canonical/tools/real_fix_minimal_repair_census_v1.py --limit 10
    python3 canonical/tools/real_fix_minimal_repair_census_v1.py --offset 20 --limit 20 --out /tmp/min20.json
"""
from __future__ import annotations

import argparse
import ast
import difflib
import json
import pathlib
import sys
import time
from typing import Any

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from real_fix_oracle_baseline_v1 import CORPUS, DEFAULT_WORKDIR, Oracle  # noqa: E402

SCHEMA = "PROJECT_BRAIN_REAL_FIX_MINIMAL_REPAIR_CENSUS_V1"

# a task is not measured if the whole-file oracle is unusable (collection error)
FILE_ORACLE_UNUSABLE = "<COLLECTION_ERROR>"


def _ops(before: str, after: str) -> list[tuple[str, int, int, int, int]]:
    b, a = before.splitlines(keepends=True), after.splitlines(keepends=True)
    return difflib.SequenceMatcher(None, b, a, autojunk=False).get_opcodes()


def _apply(before: str, after: str, ops: list[tuple[str, int, int, int, int]],
           keep: set[int]) -> str:
    """Rebuild the text applying only the kept non-equal opcodes."""
    b, a = before.splitlines(keepends=True), after.splitlines(keepends=True)
    out: list[str] = []
    for k, (tag, i1, i2, j1, j2) in enumerate(ops):
        if tag == "equal":
            out.extend(b[i1:i2])
        elif k in keep:
            out.extend(a[j1:j2])
        else:
            out.extend(b[i1:i2])
    return "".join(out)


def _lines(ops, idx: int, before: str, after: str) -> tuple[int, int]:
    """(added, removed) line counts contributed by one opcode."""
    b, a = before.splitlines(), after.splitlines()
    tag, i1, i2, j1, j2 = ops[idx]
    return (j2 - j1, i2 - i1) if tag != "equal" else (0, 0)


def minimise(o: Oracle, t: dict[str, Any], *, passes: int = 3,
             deadline: float | None = None) -> dict[str, Any]:
    """Greedy delta-debug of the upstream patch.  Never raises."""
    before, after = t["before"], t["after"]
    if not t.get("failed_nodes"):
        return {"error": "NO_FAILED_NODES", "runs": 0, "opcodes": 0,
                "full_added": 0, "full_removed": 0, "min_lines": None}
    ops = _ops(before, after)
    edited = [k for k, op in enumerate(ops) if op[0] != "equal"]
    full_added = sum(_lines(ops, k, before, after)[0] for k in edited)
    full_removed = sum(_lines(ops, k, before, after)[1] for k in edited)

    keep = set(edited)
    runs = 0

    def passes_nodes(keep_set: set[int]) -> bool:
        nonlocal runs
        runs += 1
        text = _apply(before, after, ops, keep_set)
        o.write_source(t["source"], text)
        return o.test(t["failed_nodes"])["passed"]

    # sanity: the full patch must pass, and reverting everything must fail
    if not passes_nodes(keep):
        return {"error": "FULL_PATCH_DOES_NOT_PASS", "runs": runs,
                "full_added": full_added, "full_removed": full_removed,
                "opcodes": len(edited)}
    if passes_nodes(set()):
        return {"error": "EMPTY_PATCH_PASSES", "runs": runs,
                "full_added": full_added, "full_removed": full_removed,
                "opcodes": len(edited)}

    # largest hunks first: a big revert is the most informative single test
    order = sorted(edited, key=lambda k: -sum(_lines(ops, k, before, after)))
    for _ in range(passes):
        changed = False
        for k in order:
            if k not in keep:
                continue
            if deadline and time.perf_counter() > deadline:
                break
            trial = keep - {k}
            if passes_nodes(trial):
                keep = trial
                changed = True
        if not changed:
            break

    text = _apply(before, after, ops, keep)
    min_added = sum(_lines(ops, k, before, after)[0] for k in keep)
    min_removed = sum(_lines(ops, k, before, after)[1] for k in keep)

    # whole-file check: does the minimal patch break anything else in its file?
    test_file = (t["failed_nodes"][0].split("::")[0]
                 if t.get("failed_nodes") and "::" in t["failed_nodes"][0] else "")
    file_subset_ok: bool | None = None
    base_fail: set[str] | None = None
    if test_file and (o.path / test_file).exists():
        o.write_source(t["source"], before)
        base_fail = o.fail_set([test_file])
        if FILE_ORACLE_UNUSABLE not in base_fail:
            o.write_source(t["source"], text)
            cand_fail = o.fail_set([test_file])
            file_subset_ok = (FILE_ORACLE_UNUSABLE not in cand_fail
                              and cand_fail <= base_fail)

    stmt = statement_minimise(o, t, text, deadline=deadline) if text != after else \
        {"statements_total": 0, "statements_kept": 0, "runs": 0}
    o.write_source(t["source"], before)
    return {
        "opcodes": len(edited), "opcodes_kept": len(keep),
        "statements_touched": _touched_statements(before, text),
        **stmt,
        "full_added": full_added, "full_removed": full_removed,
        "min_added": min_added, "min_removed": min_removed,
        "min_lines": min_added + min_removed,
        "runs": runs,
        "file_subset_ok": file_subset_ok,
        "baseline_file_failures": len(base_fail) if base_fail is not None else None,
        "minimal_patch": _diff_text(before, text),
    }


def _added_ranges(before: str, text: str) -> list[tuple[int, int]]:
    """1-based (first, last) line ranges present in `text` but not `before`."""
    b, a = before.splitlines(), text.splitlines()
    out = []
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(
            None, b, a, autojunk=False).get_opcodes():
        if tag in ("replace", "insert") and j2 > j1:
            out.append((j1 + 1, j2))
    return out


def _added_statements(before: str, text: str) -> list[tuple[int, int, int, bool]]:
    """(first, last, indent_len, is_toplevel) for statements the patch ADDED.

    A statement counts as added only when its whole extent sits inside a range
    the diff introduced; a pre-existing statement the patch merely touched is
    not deletable on its own.
    """
    ranges = _added_ranges(before, text)
    if not ranges:
        return []
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return []
    out: list[tuple[int, int, int, bool]] = []
    lines = text.splitlines(keepends=True)
    for node in ast.walk(tree):
        if not isinstance(node, ast.stmt):
            continue
        end = getattr(node, "end_lineno", node.lineno)
        if not any(lo <= node.lineno and end <= hi for lo, hi in ranges):
            continue
        raw = lines[node.lineno - 1]
        indent = len(raw) - len(raw.lstrip())
        out.append((node.lineno, end, indent, indent == 0))
    # outermost first, and longest first, so a function is tried before its body
    return sorted(set(out), key=lambda t: (t[3], -(t[1] - t[0])))


def _touched_statements(before: str, text: str) -> int:
    """Count the INNERMOST statements the repair edits.

    A change to one line of a 12-line `def` is one edit site, not thirteen:
    counting every ancestor would make every repair look huge.  So a statement
    counts only when none of its own child statements also changed.
    """
    ranges = _added_ranges(before, text)
    if not ranges:
        return 0
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return -1

    def hits(node: ast.stmt) -> bool:
        end = getattr(node, "end_lineno", node.lineno)
        return any(not (end < lo or node.lineno > hi) for lo, hi in ranges)

    changed = {id(n): n for n in ast.walk(tree)
               if isinstance(n, ast.stmt) and hits(n)}
    innermost = 0
    for n in changed.values():
        kids = [c for c in ast.iter_child_nodes(n) if isinstance(c, ast.stmt)]
        if not any(id(c) in changed for c in kids):
            innermost += 1
    return innermost


def _drop_statement(text: str, first: int, last: int, indent: int,
                    toplevel: bool) -> str:
    """Remove one statement: delete it outright, or `pass` if it is nested."""
    lines = text.splitlines(keepends=True)
    if toplevel:
        return "".join(lines[: first - 1] + lines[last:])
    pad = " " * indent
    return "".join(lines[: first - 1] + [pad + "pass\n"] + lines[last:])


def statement_minimise(o: Oracle, t: dict[str, Any], text: str, *,
                       deadline: float | None = None) -> dict[str, Any]:
    """How many ADDED STATEMENTS does the repair actually need?

    Statement granularity is the honest unit for "could one expression express
    this repair": a line is too fine (deleting one line of a function is usually
    a syntax error, which says nothing about whether the code is needed) and a
    hunk is too coarse (a helper plus its call site is atomic).
    """
    before = t["before"]
    stmts = [st for st in _added_statements(before, text) if st[3]]
    # nested statements are only tried after the top-level ones are settled
    nested = [st for st in _added_statements(before, text) if not st[3]]
    runs = 0

    def ok(txt: str) -> bool:
        nonlocal runs
        runs += 1
        o.write_source(t["source"], txt)
        return o.test(t["failed_nodes"])["passed"]

    if not ok(text):
        return {"error": "MINIMAL_TEXT_FAILS", "statements_total": len(stmts) + len(nested),
                "runs": 0}

    cur = text
    removed = 0
    # two passes: dropping a caller can free its callee
    for _ in range(2):
        changed = False
        for first, last, indent, top in stmts:
            if deadline and time.perf_counter() > deadline:
                break
            # re-locate the statement in the CURRENT text by its content
            cand = _relocate_and_drop(cur, before, first, last, indent, top)
            if cand is None or cand == cur:
                continue
            if ok(cand):
                cur = cand
                removed += 1
                changed = True
        if not changed:
            break

    kept = _added_statements(before, cur)
    kept_top = [x for x in kept if x[3]]
    o.write_source(t["source"], before)
    return {
        "statements_total": len(stmts),
        "statements_removed": removed,
        "statements_kept": len(kept_top),
        "runs": runs,
        "statement_patch": _diff_text(before, cur)[:3000],
    }


def _relocate_and_drop(cur: str, before: str, first: int, last: int,
                       indent: int, top: bool) -> str | None:
    """Find the same statement in `cur` (line numbers shift) and drop it.

    Matches on the statement's own source text, which is stable across
    deletions elsewhere in the file.
    """
    src_lines = before.splitlines()
    stmts = _added_statements(before, cur)
    for f, l, ind, t in stmts:
        if (ind, t) == (indent, top):
            cand = _drop_statement(cur, f, l, ind, t)
            if cand != cur:
                return cand
    return None


def _diff_text(before: str, text: str) -> str:
    d = list(difflib.unified_diff(before.splitlines(keepends=True),
                                  text.splitlines(keepends=True),
                                  fromfile="before", tofile="minimal", n=2))
    return "".join(d)[:4000]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", default=str(CORPUS))
    ap.add_argument("--workdir", default=str(DEFAULT_WORKDIR))
    ap.add_argument("--well-formed", default="/tmp/wf_idx.json",
                    help="JSON list of corpus indices that are well-formed")
    ap.add_argument("--offset", type=int, default=0)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--per-task-budget", type=float, default=180.0)
    ap.add_argument("--out", default=None)
    ns = ap.parse_args(argv)

    idxs = json.loads(pathlib.Path(ns.well_formed).read_text())
    tasks = json.loads(pathlib.Path(ns.corpus).read_text())["tasks"]
    idxs = idxs[ns.offset:]
    if ns.limit:
        idxs = idxs[:ns.limit]

    oracles: dict[str, Oracle] = {}
    rows: list[dict[str, Any]] = []
    for i in idxs:
        t = tasks[i]
        slug = t["repo"]
        if slug not in oracles:
            oracles[slug] = Oracle(slug, pathlib.Path(ns.workdir))
            oracles[slug].ensure()
        o = oracles[slug]
        t0 = time.perf_counter()
        o.checkout(t["sha"])
        res = minimise(o, t, deadline=t0 + ns.per_task_budget)
        res.update({
            "idx": i, "repo": slug, "sha": t["sha"][:10], "source": t["source"],
            "seconds": round(time.perf_counter() - t0, 2),
        })
        rows.append(res)
        ml = res.get("min_lines")
        print(f"[{i:2d}] {slug:20s} ops {res.get('opcodes_kept') or 0:3d}/{res.get('opcodes') or 0:3d} "
              f"lines {ml if ml is not None else '-':>4} (full {res.get('full_added', 0)}+/"
              f"{res.get('full_removed', 0)}-) file_ok={res.get('file_subset_ok')} "
              f"{res.get('error', '')}")
        sys.stdout.flush()

    ok = [r for r in rows if "error" not in r and r.get("min_lines") is not None]
    summary = {
        "schema": SCHEMA,
        "authority": "NONE__PRODUCER_RUN_SANDBOX",
        "model_dependency_count": 0,
        "network_calls_at_decision_time": 0,
        "measured": len(ok),
        "attempted": len(rows),
        "median_min_lines": sorted(r["min_lines"] for r in ok)[len(ok) // 2] if ok else None,
        "median_full_lines": sorted(r["full_added"] + r["full_removed"] for r in ok)[len(ok) // 2] if ok else None,
        "file_subset_ok": sum(1 for r in ok if r.get("file_subset_ok") is True),
        "file_subset_bad": sum(1 for r in ok if r.get("file_subset_ok") is False),
        "file_subset_unchecked": sum(1 for r in ok if r.get("file_subset_ok") is None),
        "rows": rows,
    }
    text = json.dumps(summary, indent=1, default=str)
    if ns.out:
        pathlib.Path(ns.out).write_text(text)
    print(text[:1200])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
