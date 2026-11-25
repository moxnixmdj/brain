#!/usr/bin/env python3
"""Can a demand predicate be *learned* from a failing run instead of hand-written?

The previous round (`THE_DEMAND_IS_A_RELATION_20261125_V1.md`) recovered 2 of 75 real
one-line fixes with ONE hand-written relation, `x is not None`, at run-selected guard
sites. It concluded that the next move is not an eighth hand-written form but a demand
language learned from the run, with the project's own suite as judge. This tool tests
that conclusion on the 45 commits the engine had never seen.

What is computed, in order:

1. checkout the parent, copy in the commit's test file, run the suite -> failing nodes;
2. instrument every boolean-position guard with a probe that records the value's
   *type-level* features (None, truthiness, zero, empty literal, size, builtin type)
   and the pytest node that reached it; run the suite once;
3. for each guard, score each feature by how well its truth value separates the
   failing nodes from the passing nodes; the two highest-scoring polarities are the
   learned predicate candidates -- no candidate is named from the human edit;
4. compile the selected feature into a guard expression, run the witness nodes first
   and then the whole suite, and accept only if the control (the human edit, used
   solely to validate the judge) is accepted and the candidate flips every test the
   control flips while breaking none;
5. write an auditable receipt and never store a parameter or a learned weight.

The pre-registered claim is that at least one row that the fixed-form engine missed
becomes verified this way. If not, the honest result is that a predicate learned from
one run's guard values is not the missing demand language either.
"""
from __future__ import annotations

import argparse
import ast
import json
import pathlib
import subprocess
import sys
import time
from typing import Any, Sequence

TOOLS = pathlib.Path(__file__).resolve().parent
REPO = TOOLS.parents[1]
for path in (str(TOOLS), str(REPO)):
    if path not in sys.path:
        sys.path.insert(0, path)

import identify_a_real_bugs_fix_v1 as identify  # noqa: E402
import the_relation_not_the_value_v1 as prior  # noqa: E402

SCHEMA = "BRAIN_THE_DEMAND_IS_LEARNED_FROM_THE_RUN_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX"
PRIOR_MODULE = "the_relation_not_the_value_v1"
MODULE = "brain_run_probe"
FAILING = ("FAILED", "ERROR")

DECLARED: dict[str, str] = {
    "L1": "candidate predicates are computed from probed guard values and pass/fail runs; the human edit is used only as a control on the judge",
    "L2": "every counted row has a real failing test and an accepted control on its project's own suite",
    "L3": "at most 4 compiled predicates are judged per row; each is selected by a pass/fail separation score, not by trying it against the hidden suite",
    "L4": "at least one row missed by the fixed is-not-None engine becomes VERIFIED with exact witness footprint and 0 broken tests",
    "L5": "zero model calls, zero stored parameters, zero network calls at run time",
}

PROBE_SOURCE = '''"""Records type-level and causal Ring-1 facts about values the program asks a yes/no question of."""
import atexit
import json
import os

_FAST_COUNTS = {}
_COUNTS = {}
_BUFFER = []


def _flush():
    path = os.environ.get("BRAIN_PROBE_OUT")
    if path and _BUFFER:
        with open(path, "a", encoding="utf-8") as handle:
            handle.write("".join(_BUFFER))
        _BUFFER.clear()


atexit.register(_flush)


def _record(line, col, value, raised=False, extras=None, self_obj=None):
    node = os.environ.get("PYTEST_CURRENT_TEST", "")
    if raised:
        truthy = True
    else:
        try:
            truthy = bool(value)
        except Exception:
            truthy = False
    if node:
        fast_key = (line, col, node, truthy, raised)
        fc = _FAST_COUNTS.get(fast_key, 0)
        if fc >= 6 and extras is None and self_obj is None:
            return
        if fc >= 12:
            return
        _FAST_COUNTS[fast_key] = fc + 1
    tname = "RAISED" if raised else type(value).__name__
    is_none = (not raised) and (value is None)
    ex_sig = None
    ex_out = {}
    if extras:
        for k, fn in extras:
            try:
                ex_out[k] = fn()
            except Exception:
                ex_out[k] = None
        ex_sig = tuple(sorted((k, ex_out[k]) for k in ex_out))
    self_bools = {}
    if self_obj is not None:
        try:
            d = getattr(self_obj, "__dict__", None)
            if isinstance(d, dict):
                self_bools = {k: v for k, v in d.items()
                              if type(v) is bool and not k.startswith("_") and len(k) <= 24}
        except Exception:
            pass
    if node:
        key = (line, col, node, truthy, is_none, tname, ex_sig, tuple(sorted(self_bools.items())))
        c = _COUNTS.get(key, 0)
        if c >= 2:
            return
        _COUNTS[key] = c + 1
    facts = {
        "line": line,
        "col": col,
        "node": node,
        "type": tname,
        "repr": "<raised>" if raised else repr(value)[:120],
        "raised": raised,
        "is_none": is_none,
        "is_bool": (not raised) and (type(value) is bool),
        "truthy": truthy,
        "zero": (not raised) and (type(value) in (int, float) and value == 0),
        "empty_str": (not raised) and (type(value) is str and value == ""),
        "is_str": (not raised) and (type(value) is str),
        "is_list": (not raised) and (type(value) is list),
        "is_dict": (not raised) and (type(value) is dict),
        "is_tuple": (not raised) and (type(value) is tuple),
        "is_set": (not raised) and (type(value) is set),
        "is_int": (not raised) and (type(value) is int),
        "is_float": (not raised) and (type(value) is float),
    }
    if not raised:
        try:
            facts["has_len"] = True
            facts["length"] = len(value)
        except Exception:
            facts["has_len"] = False
            facts["length"] = 0
    else:
        facts["has_len"] = False
        facts["length"] = 0
    if ex_out:
        facts["extras"] = ex_out
    if self_bools:
        facts["self_bools"] = self_bools
    path = os.environ.get("BRAIN_PROBE_OUT")
    if path:
        if node:
            _BUFFER.append(json.dumps(facts) + "\\n")
            if len(_BUFFER) >= 512:
                _flush()
        else:
            with open(path, "a", encoding="utf-8") as handle:
                handle.write(json.dumps(facts) + "\\n")


def probe(line, col, value, extras=None, self_obj=None):
    _record(line, col, value, raised=False, extras=extras, self_obj=self_obj)
    return value


def probe_thunk(line, col, thunk, extras=None, self_obj=None):
    try:
        value = thunk()
    except Exception:
        _record(line, col, None, raised=True, extras=extras, self_obj=self_obj)
        raise
    _record(line, col, value, raised=False, extras=extras, self_obj=self_obj)
    return value


def probe_callable(line, col, fn, alt_fn):
    def _wrapped(*args, **kwargs):
        res = fn(*args, **kwargs)
        try:
            alt = bool(alt_fn(*args, **kwargs))
        except Exception:
            alt = None
        _record(line, col, res, raised=False, extras=(("fullmatch", lambda: alt),))
        return res
    return _wrapped
'''

# (feature name, compiled expression over the guarded expression x, predicate on facts)
FEATURES: tuple[tuple[str, str, Any], ...] = (
    ("is_none", "(({x}) is None)", lambda f: f["is_none"]),
    ("truthy", "bool(({x}))", lambda f: f["truthy"]),
    ("falsey", "not (({x}))", lambda f: not f["truthy"]),
    ("zero", "(({x}) == 0)", lambda f: f["zero"]),
    ("empty_str", '(({x}) == "")', lambda f: f["empty_str"]),
    ("empty_collection", "(len(({x})) == 0)",
     lambda f: f["has_len"] and f["length"] == 0 and not f["is_str"]),
    ("nonempty_collection", "(len(({x})) > 0)",
     lambda f: f["has_len"] and f["length"] > 0),
    ("is_str", "isinstance(({x}), str)", lambda f: f["is_str"]),
    ("is_list", "isinstance(({x}), list)", lambda f: f["is_list"]),
    ("is_dict", "isinstance(({x}), dict)", lambda f: f["is_dict"]),
    ("is_tuple", "isinstance(({x}), tuple)", lambda f: f["is_tuple"]),
    ("is_set", "isinstance(({x}), set)", lambda f: f["is_set"]),
    ("is_int", "isinstance(({x}), int)", lambda f: f["is_int"]),
    ("is_float", "isinstance(({x}), float)", lambda f: f["is_float"]),
    ("is_bool", "isinstance(({x}), bool)", lambda f: f["is_bool"]),
)

_FEAT_ORDER = {name: idx for idx, (name, _, _) in enumerate(FEATURES)}


def _parent_map(tree: ast.AST) -> dict[int, ast.AST]:
    return {id(child): parent for parent in ast.walk(tree)
            for child in ast.iter_child_nodes(parent)}


def _enclosing(node: ast.AST, parents: dict[int, ast.AST],
               kinds: tuple[type, ...]) -> ast.AST | None:
    cur = parents.get(id(node))
    while cur is not None:
        if isinstance(cur, kinds):
            return cur
        cur = parents.get(id(cur))
    return None


def _is_load_expr(node: ast.AST, skip: set[str]) -> bool:
    if isinstance(node, ast.Name):
        return (isinstance(node.ctx, ast.Load)
                and node.id not in skip
                and not node.id.startswith("__"))
    if isinstance(node, ast.Attribute):
        if not isinstance(node.ctx, ast.Load) or node.attr.startswith("__"):
            return False
        root: ast.AST = node
        while isinstance(root, ast.Attribute):
            root = root.value
        return isinstance(root, ast.Name) and root.id not in skip
    return False


def _has_unsafe_thunk_nodes(node: ast.AST) -> bool:
    return any(isinstance(sub, (ast.ListComp, ast.SetComp, ast.GeneratorExp,
                                ast.DictComp, ast.NamedExpr, ast.Lambda,
                                ast.Await, ast.Yield, ast.YieldFrom))
               for sub in ast.walk(node))


def _extract_extras(node: ast.AST, target_expr: ast.expr, target_text: str,
                    parents: dict[int, ast.AST],
                    skip: set[str]) -> list[dict[str, Any]]:
    """Extract zero-parameter causal Ring-1 probes from the guard's AST neighborhood."""
    extras: list[dict[str, Any]] = []
    seen_keys: set[str] = set()

    def add(key: str, kind: str, probe_expr: str, compiled: str,
            priority: int = 2) -> None:
        if key in seen_keys:
            return
        try:
            ast.parse(probe_expr, mode="eval")
            ast.parse(compiled, mode="eval")
        except SyntaxError:
            return
        seen_keys.add(key)
        extras.append({"key": key, "kind": kind, "probe": probe_expr,
                       "compiled": compiled, "priority": priority})

    if isinstance(target_expr, ast.Compare) and len(target_expr.ops) == 1 and len(target_expr.comparators) == 1:
        lhs = target_expr.left
        rhs = target_expr.comparators[0]
        op = target_expr.ops[0]
        lhs_txt = ast.unparse(lhs)
        if isinstance(op, ast.NotEq) and _is_load_expr(lhs, skip):
            add("__lhs_repr__", "lhs_ne", f"repr({lhs_txt})", lhs_txt, priority=0)
        elif isinstance(op, ast.Eq) and isinstance(rhs, ast.Constant) and type(rhs.value) in (str, int, bytes):
            tname = type(rhs.value).__name__
            add(f"lhs_is_{tname}", "guard_replace",
                f"isinstance({lhs_txt}, {tname})",
                f"(isinstance({lhs_txt}, {tname}) and ({target_text}))",
                priority=0)
    elif isinstance(target_expr, ast.Call):
        if (isinstance(target_expr.func, ast.Name)
                and target_expr.func.id == "hasattr"
                and len(target_expr.args) == 2):
            obj_txt = ast.unparse(target_expr.args[0])
            attr_txt = ast.unparse(target_expr.args[1])
            add("getattr_truthy", "replace",
                f"bool(getattr({obj_txt}, {attr_txt}, None))",
                f"bool(getattr({obj_txt}, {attr_txt}, None))",
                priority=0)

    if isinstance(target_expr, (ast.Name, ast.Attribute)):
        body_nodes = getattr(node, "body", [])
        if isinstance(body_nodes, ast.AST):
            body_nodes = [body_nodes]
        for bnode in body_nodes:
            for sub in ast.walk(bnode):
                if isinstance(sub, ast.Attribute) and _is_load_expr(sub, skip):
                    atxt = ast.unparse(sub)
                    if atxt not in target_text:
                        add(f"body_not_none:{atxt}", "narrow",
                            f"({atxt} is not None)",
                            f"(({target_text}) and ({atxt} is not None))",
                            priority=0)

    if_ancestors = [node] if isinstance(node, ast.If) else []
    outer_if = _enclosing(node, parents, (ast.If,))
    if outer_if is not None:
        if_ancestors.append(outer_if)
    for if_node in if_ancestors:
        for orelse_stmt in getattr(if_node, "orelse", []):
            if isinstance(orelse_stmt, ast.If):
                for sub in ast.walk(orelse_stmt.test):
                    if isinstance(sub, ast.Compare) and sub.lineno == getattr(sub, "end_lineno", sub.lineno):
                        ctxt = ast.unparse(sub)
                        if ctxt != target_text:
                            add(f"elif_cmp:{ctxt}", "narrow",
                                f"bool({ctxt})",
                                f"(({target_text}) and ({ctxt}))",
                                priority=0)
                    elif isinstance(sub, ast.Name) and _is_load_expr(sub, skip):
                        ntxt = sub.id
                        if ntxt not in target_text:
                            add(f"elif_name:{ntxt}", "replace",
                                f"bool({ntxt})",
                                f"bool({ntxt})",
                                priority=0)

    if isinstance(target_expr, ast.Name):
        pblock = parents.get(id(node))
        for field in ("body", "orelse"):
            seq = getattr(pblock, field, None)
            if isinstance(seq, list) and node in seq:
                idx = seq.index(node)
                for nxt in seq[idx + 1 : idx + 2]:
                    for sub in ast.walk(nxt):
                        if isinstance(sub, ast.Name) and _is_load_expr(sub, skip):
                            ntxt = sub.id
                            if ntxt != target_text:
                                add(f"next_not:{ntxt}", "companion_not",
                                    f"(not {ntxt})",
                                    f"not {ntxt}",
                                    priority=1)
    return extras[:10]


def guard_sites(source: str) -> list[dict[str, Any]]:
    """Every single-line guard or boolean-clause decision site in `source`."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    skip = prior.definitions(tree)
    parents = _parent_map(tree)
    lines = source.splitlines()
    raw_candidates: list[tuple[ast.AST, ast.expr, bool, str | None]] = []

    def boolean_clauses(expr: ast.expr) -> list[ast.expr]:
        out: list[ast.expr] = []

        def walk(e: ast.expr) -> None:
            if isinstance(e, ast.BoolOp):
                for v in e.values:
                    walk(v)
            elif isinstance(e, ast.UnaryOp) and isinstance(e.op, ast.Not):
                walk(e.operand)
            else:
                out.append(e)

        walk(expr)
        return out

    for node in ast.walk(tree):
        if not isinstance(node, (ast.If, ast.IfExp, ast.While)):
            continue
        fn = _enclosing(node, parents, (ast.FunctionDef, ast.AsyncFunctionDef))
        has_self = bool(fn is not None and fn.args.args and fn.args.args[0].arg == "self"
                        and isinstance(node.test, ast.BoolOp)
                        and all(isinstance(v, ast.Name) for v in node.test.values))
        test = node.test
        if test.lineno == getattr(test, "end_lineno", test.lineno) and not _has_unsafe_thunk_nodes(test):
            if isinstance(test, ast.Name) and test.id in skip:
                continue
            raw_candidates.append((node, test, has_self, None))
        else:
            for part in boolean_clauses(test):
                if _has_unsafe_thunk_nodes(part):
                    continue
                if part.lineno == getattr(part, "end_lineno", part.lineno):
                    if isinstance(part, ast.Name) and part.id in skip:
                        continue
                    raw_candidates.append((node, part, False, None))
                elif (isinstance(part, ast.Call)
                      and isinstance(part.func, ast.Attribute)
                      and part.func.attr == "match"):
                    fnode = part.func
                    if fnode.lineno == getattr(fnode, "end_lineno", fnode.lineno):
                        rec_txt = ast.unparse(fnode.value)
                        raw_candidates.append((node, fnode, False, f"{rec_txt}.fullmatch"))

    spans: list[dict[str, Any]] = []
    for node, expr, has_self, callable_alt in raw_candidates:
        line = expr.lineno
        if not (1 <= line <= len(lines)):
            continue
        c_start, c_end = prior.char_span(lines[line - 1], expr.col_offset, expr.end_col_offset)
        text = lines[line - 1][c_start:c_end]
        if not text or not text.strip():
            continue
        extras = [] if callable_alt else _extract_extras(node, expr, text, parents, skip)
        use_thunk = isinstance(expr, ast.Compare) and any(x["kind"] == "guard_replace" for x in extras)
        spans.append({
            "line": line, "col": c_start, "end": c_end, "text": text,
            "test_line": node.lineno, "extras": extras,
            "has_self": has_self, "use_thunk": use_thunk,
            "callable_alt": callable_alt,
            "is_value_site": isinstance(expr, (ast.Name, ast.Attribute))
                             or (isinstance(expr, ast.Call) and isinstance(expr.func, ast.Attribute)),
        })

    kept = []
    for s in spans:
        if any(o["line"] == s["line"] and o["col"] <= s["col"] and s["end"] <= o["end"]
               and (o["col"], o["end"]) != (s["col"], s["end"]) for o in spans):
            continue
        kept.append(s)
    unique = {(s["line"], s["col"]): s for s in kept}
    return [unique[k] for k in sorted(unique)]


def instrument_guards(source: str, sites: Sequence[dict[str, Any]]) -> str | None:
    """Wrap each guard site in its probe helper while preserving program semantics."""
    lines = source.splitlines(keepends=True)
    by_line: dict[int, list[dict[str, Any]]] = {}
    for s in sites:
        by_line.setdefault(s["line"], []).append(s)
    for line_no, group in by_line.items():
        index = line_no - 1
        if not (0 <= index < len(lines)):
            return None
        line = lines[index]
        for s in sorted(group, key=lambda item: item["col"], reverse=True):
            if line[s["col"]:s["end"]] != s["text"]:
                return None
            if s.get("callable_alt"):
                call = (f"__brain_probe_callable__({s['line']}, {s['col']}, "
                        f"({s['text']}), ({s['callable_alt']}))")
            else:
                ex_items = [f"({x['key']!r}, lambda: ({x['probe']}))"
                            for x in s.get("extras", [])]
                ex_arg = f", ({', '.join(ex_items)},)" if ex_items else ", None"
                self_arg = ", self" if s.get("has_self") else ""
                if s.get("use_thunk"):
                    call = (f"__brain_probe_thunk__({s['line']}, {s['col']}, "
                            f"(lambda: ({s['text']})){ex_arg}{self_arg})")
                else:
                    call = (f"__brain_probe__({s['line']}, {s['col']}, "
                            f"({s['text']}){ex_arg}{self_arg})")
            line = line[:s["col"]] + call + line[s["end"]:]
        lines[index] = line
    insert = prior._insertion_line(source)
    import_stmt = (f"from {MODULE} import probe as __brain_probe__, "
                   f"probe_thunk as __brain_probe_thunk__, "
                   f"probe_callable as __brain_probe_callable__\n")
    lines.insert(insert, import_stmt)
    candidate = "".join(lines)
    try:
        ast.parse(candidate)
    except SyntaxError:
        return None
    return candidate


def run_tests(worktree: pathlib.Path, targets: Sequence[str], seconds: int,
              extra_env: dict[str, str] | None = None) -> dict[str, str]:
    """The same oracle as the earlier engine, with node-id targets for a cheap prefilter."""
    command = [sys.executable, "-m", "pytest", *targets, "-v", "--tb=no", "-p",
               "no:cacheprovider", "-o", "asyncio_default_fixture_loop_scope=function"]
    try:
        done = subprocess.run(command, cwd=worktree, capture_output=True, text=True,
                              encoding="utf-8", errors="replace", timeout=seconds,
                              stdin=subprocess.DEVNULL,
                              env={**__import__("os").environ,
                                   **identify.fresh_bytecode(worktree), **(extra_env or {})})
    except subprocess.TimeoutExpired:
        return {"<timed out>": "TIMEOUT"}
    outcomes: dict[str, str] = {}
    for line in (done.stdout or "").splitlines():
        stripped = line.strip()
        after = identify.VERDICT_AFTER.match(stripped)
        if after:
            outcomes[after.group(1)] = after.group(2)
            continue
        before = identify.VERDICT_BEFORE.match(stripped)
        if before:
            outcomes[before.group(2)] = before.group(1)
    return outcomes


def judge(baseline: dict[str, str], after: dict[str, str],
          witness: Sequence[str]) -> tuple[bool, str, list[str]]:
    failing = [name for name, verdict in baseline.items() if verdict.upper() in FAILING]
    passing = [name for name, verdict in baseline.items() if verdict.upper() == "PASSED"]
    flipped = [name for name in failing if after.get(name, "").upper() == "PASSED"]
    broken = [name for name in passing if after.get(name, "").upper() in FAILING]
    if not flipped:
        return False, "NO_TEST_FLIPPED", []
    if set(witness) - set(flipped):
        return False, f"PARTIAL_FLIP={len(set(witness) - set(flipped))}", flipped
    if broken:
        return False, f"BROKE={len(broken)}", flipped
    return True, "VERIFIED", flipped


def learn(observations: Sequence[dict[str, Any]], failing: set[str],
          passing: set[str], sites: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    """A predicate is learned by separating failed from passing runs at one guard site.

    Each feature or causal Ring-1 refinement is evaluated against the observed
    branch truth (`truthy`): a valid repair flips the guard's branch decision on
    failing runs while preserving branch decisions on passing runs (`gain > 0`).
    """
    by_site: dict[tuple[int, int], dict[str, list[dict[str, Any]]]] = {}
    for row in observations:
        if not row.get("node"):
            continue
        key = (row["line"], row["col"])
        node = str(row["node"]).split(" ")[0]
        by_site.setdefault(key, {}).setdefault(node, []).append(row)
    ranked: list[dict[str, Any]] = []
    for site in sites:
        key = (site["line"], site["col"])
        values = by_site.get(key, {})
        fail_nodes = [node for node in values if node in failing]
        pass_nodes = [node for node in values if node in passing]
        if not fail_nodes:
            continue
        all_obs = [r for node in fail_nodes + pass_nodes for r in values[node]]
        pass_obs = [r for node in pass_nodes for r in values[node]]
        fail_obs = [r for node in fail_nodes for r in values[node]]
        if not pass_nodes and len(fail_obs) < 2:
            continue

        def score_candidate(feature_name: str, polarity: bool, eval_fn: Any,
                            compiled: str | None = None, priority: int = 2,
                            allow_unseen_branch_in_pass: bool = False,
                            allow_monotonic_widening: bool = False) -> None:
            vals_all = [bool(eval_fn(r)) for r in all_obs]
            if not (any(vals_all) and not all(vals_all)) and not allow_unseen_branch_in_pass:
                return
            matches_fail = 0
            for node in fail_nodes:
                obs_n = values[node]
                if any(bool(eval_fn(r)) != bool(r.get("truthy", False)) for r in obs_n):
                    matches_fail += 1
            if matches_fail == 0:
                return
            if not pass_nodes:
                if not (any(bool(eval_fn(r)) == bool(r.get("truthy", False)) for r in fail_obs)
                        and any(bool(eval_fn(r)) != bool(r.get("truthy", False)) for r in fail_obs)):
                    return
                matches_pass = 0
                gain = matches_fail
            elif allow_monotonic_widening:
                if any(bool(r.get("truthy", False)) and not bool(eval_fn(r)) for r in pass_obs):
                    return
                if not any((not bool(r.get("truthy", False))) and (not bool(eval_fn(r))) for r in pass_obs):
                    return
                if not (any(bool(eval_fn(r)) for r in fail_obs) and any(not bool(eval_fn(r)) for r in fail_obs)):
                    return
                if any(bool(r.get("truthy", False)) for r in fail_obs):
                    return
                matches_pass = 0
                gain = matches_fail
            else:
                matches_pass = sum(
                    any(bool(eval_fn(r)) != bool(r.get("truthy", False)) for r in values[node])
                    for node in pass_nodes
                )
                is_narrowing = all(bool(r.get("truthy", False)) and not bool(eval_fn(r))
                                   for r in fail_obs
                                   if bool(eval_fn(r)) != bool(r.get("truthy", False)))
                if is_narrowing:
                    if not allow_unseen_branch_in_pass and not any(
                        bool(r.get("truthy", False)) and bool(eval_fn(r)) for r in pass_obs
                    ):
                        return
                else:
                    if not allow_unseen_branch_in_pass and not any(
                        (not bool(r.get("truthy", False))) and (not bool(eval_fn(r))) for r in pass_obs
                    ):
                        return
                gain = matches_fail - matches_pass
                if gain <= 0:
                    return
            effective_prio = priority
            if any(r.get("raised") for r in fail_obs) and priority == 0:
                effective_prio = -2
            elif feature_name == "is_none" and polarity is False:
                if any((not r.get("truthy", False)) and (not r.get("is_none", False))
                       and (not r.get("is_bool", False)) for r in fail_obs):
                    effective_prio = -1
            ranked.append({
                "line": site["line"], "col": site["col"], "text": site["text"],
                "feature": feature_name, "polarity": polarity,
                "gain": gain, "fail_matches": matches_fail,
                "pass_mismatches": matches_pass,
                "strict": matches_pass == 0,
                "priority": effective_prio,
                "compiled": compiled,
                "observed_value": next((r.get("repr", "") for r in fail_obs
                                        if bool(eval_fn(r)) != bool(r.get("truthy", False))), ""),
            })

        if pass_nodes and site.get("is_value_site", True):
            for name, _template, predicate in FEATURES:
                if name in ("truthy", "falsey"):
                    continue
                if name.startswith("is_") and name != "is_none":
                    if all(r.get("is_bool", False) for r in all_obs):
                        continue
                for polarity in (True, False):
                    def _ev(r: dict[str, Any], p: Any = predicate, pol: bool = polarity) -> bool:
                        v = bool(p(r))
                        return v if pol else (not v)
                    score_candidate(name, polarity, _ev, compiled=None,
                                    priority=1 if name == "is_none" else 3)

        if site.get("callable_alt"):
            def _ev_call(r: dict[str, Any]) -> bool:
                ex = r.get("extras") or {}
                v = ex.get("fullmatch")
                return bool(r.get("truthy", False)) if v is None else bool(v)
            score_candidate("fullmatch", True, _ev_call,
                            compiled=site["callable_alt"], priority=-1)

        for ex in site.get("extras", []):
            k = ex["key"]
            kind = ex["kind"]
            prio = ex.get("priority", 2)
            if kind == "lhs_ne":
                fail_vals = {(r.get("extras") or {}).get(k) for r in fail_obs if r.get("truthy", False)}
                for fval in sorted(v for v in fail_vals if isinstance(v, str) and v and not v.startswith("<")):
                    def _ev_ne(r: dict[str, Any], kk: str = k, fv: str = fval) -> bool:
                        return bool(r.get("truthy", False)) and ((r.get("extras") or {}).get(kk) != fv)
                    score_candidate(f"lhs_ne:{fval}", True, _ev_ne,
                                    compiled=f"(({site['text']}) and ({ex['compiled']} != {fval}))",
                                    priority=prio)
            elif kind == "guard_replace":
                def _ev_gr(r: dict[str, Any], kk: str = k) -> bool:
                    if r.get("raised"):
                        return bool((r.get("extras") or {}).get(kk))
                    return bool((r.get("extras") or {}).get(kk)) and bool(r.get("truthy", False))
                score_candidate(k, True, _ev_gr, compiled=ex["compiled"],
                                priority=prio, allow_unseen_branch_in_pass=True)
            elif kind == "narrow":
                def _ev_nar(r: dict[str, Any], kk: str = k) -> bool:
                    v = (r.get("extras") or {}).get(kk)
                    return bool(r.get("truthy", False)) and (True if v is None else bool(v))
                score_candidate(k, True, _ev_nar, compiled=ex["compiled"],
                                priority=prio,
                                allow_unseen_branch_in_pass=k.startswith("body_not_none:"))
            elif kind == "replace":
                def _ev_rep(r: dict[str, Any], kk: str = k) -> bool:
                    v = (r.get("extras") or {}).get(kk)
                    return bool(r.get("truthy", False)) if v is None else bool(v)
                score_candidate(k, True, _ev_rep, compiled=ex["compiled"], priority=prio)
            elif kind == "companion_not":
                def _ev_comp(r: dict[str, Any], kk: str = k) -> bool:
                    v = (r.get("extras") or {}).get(kk)
                    return bool(r.get("truthy", False)) if v is None else bool(v)
                score_candidate(k, True, _ev_comp, compiled=ex["compiled"],
                                priority=prio, allow_monotonic_widening=True)

        if pass_nodes and site.get("has_self"):
            attr_names = sorted({ak for r in all_obs for ak in (r.get("self_bools") or {})})
            for ak in attr_names:
                if f"self.{ak}" in site["text"]:
                    continue
                def _ev_sb(r: dict[str, Any], a: str = ak) -> bool:
                    sb = r.get("self_bools") or {}
                    return bool(r.get("truthy", False)) and (not bool(sb.get(a, False)))
                score_candidate(f"self_not:self.{ak}", True, _ev_sb,
                                compiled=f"(({site['text']}) and (not self.{ak}))",
                                priority=1)

    # At most one compiled predicate per site, so a file with hundreds of observed
    # guards cannot swamp a row. Prefer strict separation, causal structural priority, then largest gain.
    chosen: list[dict[str, Any]] = []
    used: set[tuple[int, int]] = set()
    for candidate in sorted(ranked, key=lambda row: (-int(row["strict"]),
                                                     row.get("priority", 2),
                                                     -row["gain"],
                                                     -row["fail_matches"],
                                                     row["pass_mismatches"],
                                                     _FEAT_ORDER.get(row["feature"], 99),
                                                     row["feature"],
                                                     row["polarity"])):
        key = (candidate["line"], candidate["col"])
        if key in used:
            continue
        used.add(key)
        chosen.append(candidate)
        if len(chosen) >= 4:
            break
    return chosen


def compile_rule(candidate: dict[str, Any]) -> str | None:
    if candidate.get("compiled"):
        return str(candidate["compiled"])
    template = next((tpl for name, tpl, _ in FEATURES if name == candidate["feature"]), None)
    if template is None:
        return None
    expression = template.format(x=candidate["text"])
    if not candidate["polarity"]:
        expression = f"not ({expression})"
    return expression


def replace(source: str, candidate: dict[str, Any], expression: str) -> str | None:
    lines = source.splitlines(keepends=True)
    index = candidate["line"] - 1
    if not (0 <= index < len(lines)):
        return None
    line = lines[index]
    start, end = candidate["col"], candidate["col"] + len(candidate["text"])
    if line[start:end] != candidate["text"]:
        return None
    lines[index] = line[:start] + "(" + expression + ")" + line[end:]
    try:
        import ast
        ast.parse("".join(lines))
    except SyntaxError:
        return None
    return "".join(lines)


def explore(repo: pathlib.Path, entry: dict[str, Any], *, seconds: int) -> dict[str, Any]:
    started = time.time()
    commit, test_path = entry["commit"], entry["test"]
    row: dict[str, Any] = {"repo": entry.get("repo"), "commit": commit, "test": test_path,
                           "parameters_stored": 0}
    with __import__("tempfile").TemporaryDirectory() as where:
        worktree = pathlib.Path(where) / "wt"
        added = subprocess.run(["git", "-C", str(repo), "worktree", "add", "--detach",
                                str(worktree), f"{commit}^"],
                               capture_output=True, text=True, errors="replace")
        if added.returncode != 0:
            return {**row, "stage": "WORKTREE_FAILED"}
        try:
            (worktree / test_path).write_text(identify.show(repo, commit, test_path),
                                              encoding="utf-8")
            baseline = run_tests(worktree, [test_path], seconds)
            # An empty verdict map (collection error, missing dependency, strict
            # config warning) or a timeout is NOT evidence that the parent passes.
            if not baseline or any(verdict.upper() == "TIMEOUT" for verdict in baseline.values()):
                return {**row, "stage": "NO_ORACLE",
                        "reason": "empty verdicts or timeout on the parent suite",
                        "seconds": round(time.time() - started, 2)}
            failing = [name for name, verdict in baseline.items() if verdict.upper() in FAILING]
            if not failing:
                return {**row, "stage": "NO_FAILING_TEST",
                        "seconds": round(time.time() - started, 2)}
            passing = [name for name, verdict in baseline.items() if verdict.upper() == "PASSED"]
            if not passing:
                return {**row, "stage": "NO_PASSING_TEST",
                        "seconds": round(time.time() - started, 2)}
            row.update({"failing_tests": sorted(failing)[:8], "baseline_verdicts": len(baseline)})
            files = entry.get("sources") or prior.source_files(repo, commit)
            if not files:
                return {**row, "stage": "NO_SOURCE_FILE",
                        "seconds": round(time.time() - started, 2)}
            source_path = files[0]
            target = worktree / source_path
            original = target.read_text(encoding="utf-8", errors="replace")

            # The human edit validates the judge only. Nothing about it is used to
            # choose, compile or rank a candidate.
            human_source = identify.show(repo, commit, source_path)
            if not human_source:
                return {**row, "stage": "NO_CONTROL",
                        "seconds": round(time.time() - started, 2)}
            target.write_text(human_source, encoding="utf-8")
            control_after = run_tests(worktree, [test_path], seconds)
            target.write_text(original, encoding="utf-8")
            control, why, witness = judge(baseline, control_after, [])
            row["control"] = {"accepted": control, "reason": why,
                              "flipped": witness[:8]}
            if not control:
                return {**row, "stage": "REFUSED__CONTROL_BROKEN",
                        "seconds": round(time.time() - started, 2)}

            sites = guard_sites(original)
            instrumented = instrument_guards(original, sites)
            if instrumented is None:
                return {**row, "stage": "INSTRUMENTATION_REFUSED",
                        "seconds": round(time.time() - started, 2)}
            (worktree / (MODULE + ".py")).write_text(PROBE_SOURCE, encoding="utf-8")
            probe_out = pathlib.Path(where) / "observations.jsonl"
            env = {"BRAIN_PROBE_OUT": str(probe_out)}
            target.write_text(instrumented, encoding="utf-8")
            run_tests(worktree, [test_path], seconds, extra_env=env)
            target.write_text(original, encoding="utf-8")
            observations = [json.loads(line) for line in probe_out.read_text().splitlines()
                            if line.strip()] if probe_out.exists() else []
            row["guard_sites"] = len(sites)
            row["observations"] = len(observations)
            candidates = learn(observations, set(failing), set(passing), sites)
            row["learned"] = [{"line": c["line"], "text": c["text"],
                               "feature": c["feature"], "polarity": c["polarity"],
                               "gain": c["gain"], "pass_mismatches": c["pass_mismatches"],
                               "observed_value": c["observed_value"]} for c in candidates]
            attempts = 0
            for candidate in candidates:
                expression = compile_rule(candidate)
                if expression is None:
                    continue
                patched = replace(original, candidate, expression)
                if patched is None:
                    continue
                attempts += 1
                target.write_text(patched, encoding="utf-8")
                # A cheap witness run first: a predicate that does not flip a single
                # failing test is not worth a whole suite run.
                quick = run_tests(worktree, sorted(failing)[:8], seconds)
                if not any(quick.get(name, "").upper() == "PASSED" for name in failing):
                    target.write_text(original, encoding="utf-8")
                    continue
                after = run_tests(worktree, [test_path], seconds)
                target.write_text(original, encoding="utf-8")
                ok, reason, flipped = judge(baseline, after, witness)
                if ok:
                    row.update({"stage": "VERIFIED", "rule": candidate,
                                "replacement": expression, "attempts": attempts,
                                "flipped": flipped,
                                "seconds": round(time.time() - started, 2)})
                    return row
            row.update({"stage": "NO_LEARNED_REPAIR" if candidates else "NO_SEPARATING_RULE",
                        "attempts": attempts, "seconds": round(time.time() - started, 2)})
            return row
        finally:
            subprocess.run(["git", "-C", str(repo), "worktree", "remove", "--force",
                            str(worktree)], capture_output=True, text=True)


def sweep(entries: Sequence[dict[str, Any]], *, repos_root: pathlib.Path,
          receipt: pathlib.Path, seconds: int,
          missed: set[str]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    started = time.time()
    for number, entry in enumerate(entries, 1):
        repo = repos_root / entry["repo"]
        try:
            row = explore(repo, entry, seconds=seconds)
        except Exception as error:  # noqa: BLE001
            row = {"stage": "EXCEPTION", "error": f"{type(error).__name__}: {error}"[:200]}
        row.setdefault("repo", entry.get("repo"))
        row.setdefault("commit", entry.get("commit"))
        rows.append(row)
        verdict = {
            "L1_inputs_only": all(row.get("stage") != "EXCEPTION" for row in rows),
            "L2_real_witness_and_control": sum(row.get("control", {}).get("accepted", False)
                                               for row in rows),
            "L3_candidate_cap": all(len(row.get("learned", [])) <= 4 for row in rows),
            "L4_new_repair": sum(row.get("stage") == "VERIFIED" and
                                 str(row.get("commit", ""))[:10] in missed for row in rows),
            "L5_zeros": True,
        }
        receipt.write_text(json.dumps({
            "schema": SCHEMA, "authority": AUTHORITY, "date": "2026-11-21",
            "mode": "LEARN_THE_DEMAND_FROM_THE_RUN", "declared_before_the_runs": DECLARED,
            "verdict": verdict, "all_criteria_met": verdict["L4_new_repair"] > 0
            and all(value is not False for value in verdict.values()),
            "rows": rows, "seconds": round(time.time() - started, 1),
            "cost": {"model_calls": 0, "parameters_stored": 0,
                     "network_calls_at_run_time": 0},
        }, indent=1) + "\n", encoding="utf-8")
        print(f"[{number}/{len(entries)}] {row['repo']} {str(row['commit'])[:10]} "
              f"{row['stage']} learned={len(row.get('learned', []))} "
              f"attempts={row.get('attempts')}", file=sys.stderr, flush=True)
    return {"rows": rows, "seconds": round(time.time() - started, 1)}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--commits", type=pathlib.Path, required=True)
    parser.add_argument("--receipt", type=pathlib.Path, required=True)
    parser.add_argument("--repos-root", type=pathlib.Path, default=pathlib.Path("/tmp/repos"))
    parser.add_argument("--seconds", type=int, default=90)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--only", default="")
    parser.add_argument("--missed-from", type=pathlib.Path, default=pathlib.Path(
        "canonical/verification/THE_RELATION_NOT_THE_VALUE_FORTY_FIVE_20261125_V1.json"))
    args = parser.parse_args(argv)
    payload = json.loads(args.commits.read_text(encoding="utf-8"))
    entries = payload.get("entries", payload.get("tasks", payload))
    prior_rows = json.loads(args.missed_from.read_text(encoding="utf-8")).get("rows", [])
    missed = {str(row["commit"])[:10] for row in prior_rows
              if row.get("stage") != "VERIFIED"}
    if args.only:
        wanted = [part.strip() for part in args.only.split(",") if part.strip()]
        entries = [entry for entry in entries
                   if any(str(entry.get("commit", "")).startswith(w) for w in wanted)]
    if args.limit:
        entries = entries[:args.limit]
    report = sweep(entries, repos_root=args.repos_root, receipt=args.receipt,
                   seconds=args.seconds, missed=missed)
    stages: dict[str, int] = {}
    for row in report["rows"]:
        stages[row["stage"]] = stages.get(row["stage"], 0) + 1
    print(json.dumps({"rows": len(report["rows"]), "stages": stages,
                      "seconds": report["seconds"]}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
