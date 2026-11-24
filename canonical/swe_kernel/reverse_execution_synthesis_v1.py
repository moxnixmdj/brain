#!/usr/bin/env python3
"""Reverse execution synthesis + CEGIS(T) lite + cross-modal Petri net + tomography.

WHY THIS EXISTS
---------------
Witness inversion (witness_inversion_v1) selects a value the artifact
already contains; it cannot create a distinction the artifact does not
have (0/16 on the real corpus, all refusals correct). Repo-native
mining (repo_native_mining_v1) widens the alphabet so the synthesizer
can NAME repo helpers, but selection still cannot COMPUTE a missing
body. Forward enumeration over the mined vocabulary is exponential and
repeats the depth-3 wall.

This module computes the missing body directly: propagate constraints
backward from the failing test's expected output through the Semantic
IR (AST) to the faulty point, invert operators from language semantics
(derived, not per-bug rules), and recurse through call chains so
multi-function bugs are targeted. CEGIS(T) lite generalizes
counterexamples into constraints over constants (blocking whole
families, not one candidate) instead of concrete-only feedback.

DISCIPLINE
----------
- Proposal untrusted; real test has last word; refuse stays in denominator.
- Operator inversion table is derived from Python semantics (small,
  justified, no per-bug rules). Anything outside it is refused.
- CEGIS loop bounded; no solution -> REFUSE, store nothing.
- Petri net solve is shortest-path over typed edges; no path -> refuse.
- Tomography diffs real state; no transition observed -> no machine inferred.

Authority: NONE. Producer-run sandbox measurement. Model calls 0.
Network calls 0 at decision time. Incremental spend $0.
"""
from __future__ import annotations

import ast
import heapq
import hashlib
import json
import os
import pathlib
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
from typing import Any, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_REVERSE_EXECUTION_SYNTHESIS_V1"

# ---------------------------------------------------------------------------
# 1. Backward constraint propagation (reverse execution synthesis)
# ---------------------------------------------------------------------------
# Operator inversion derived from Python semantics. Each entry maps
# (op, known_side) -> function(expected, known) -> missing value.
# This is language semantics, not per-bug rules: 6 operators, justified
# by arithmetic, no memorized world facts.


def _invert_add(expected: Any, known: Any) -> Any:
    return expected - known


def _invert_sub_left(expected: Any, known: Any) -> Any:
    # expected = missing - known  => missing = expected + known
    return expected + known


def _invert_sub_right(expected: Any, known: Any) -> Any:
    # expected = known - missing  => missing = known - expected
    return known - expected


def _invert_mul(expected: Any, known: Any) -> Any:
    if known == 0:
        raise ValueError("DIV_ZERO")
    # Exact division only; non-exact -> refuse (no guessing)
    if isinstance(expected, int) and isinstance(known, int):
        if expected % known != 0:
            raise ValueError("NON_EXACT")
        return expected // known
    return expected / known


def _invert_floordiv(expected: Any, known: Any) -> Any:
    # expected = missing // known  => missing in [expected*known, expected*known+known-1]
    # Return the lower bound (canonical witness); verifier decides.
    if known == 0:
        raise ValueError("DIV_ZERO")
    return expected * known


def _invert_mod(expected: Any, known: Any) -> Any:
    # expected = missing % known  => missing = expected (smallest witness)
    # Only valid if 0 <= expected < known
    if known == 0:
        raise ValueError("DIV_ZERO")
    if not (0 <= expected < known):
        raise ValueError("MOD_RANGE")
    return expected


_BINOP_INVERTERS: dict[str, Any] = {
    "Add": _invert_add,
    "Sub_left": _invert_sub_left,
    "Sub_right": _invert_sub_right,
    "Mult": _invert_mul,
    "FloorDiv": _invert_floordiv,
    "Mod": _invert_mod,
}


def backward_propagate(
    expression: str,
    expected: Any,
    known_env: Mapping[str, Any],
    *,
    unknown_name: str | None = None,
) -> dict[str, Any]:
    """Propagate expected output backward to the unknown operand.

    Given a single return expression and the required value, compute the
    missing operand directly by inversion (not enumeration). Returns
    {"status": "COMPUTED", "missing_value": ..., "missing_name": ...}
    or {"status": "REFUSE", "reason": ...}.
    """
    try:
        tree = ast.parse(expression, mode="eval")
    except SyntaxError:
        return {"status": "REFUSE", "reason": "REFUSE__SYNTAX"}
    body = tree.body
    # Find unknowns: names in expression not in known_env
    names = {n.id for n in ast.walk(body) if isinstance(n, ast.Name)}
    unknowns = sorted(names - set(known_env.keys()))
    if unknown_name is not None:
        unknowns = [unknown_name] if unknown_name in unknowns else []
    if len(unknowns) != 1:
        return {"status": "REFUSE", "reason": f"REFUSE__UNKNOWN_COUNT_{len(unknowns)}"}
    target = unknowns[0]
    try:
        value = _backward_eval(body, expected, dict(known_env), target)
    except Exception as exc:
        return {"status": "REFUSE", "reason": f"REFUSE__{type(exc).__name__}"}
    return {"status": "COMPUTED", "missing_value": value, "missing_name": target}


def _backward_eval(node: ast.AST, expected: Any, env: dict[str, Any], target: str) -> Any:
    if isinstance(node, ast.Name):
        if node.id == target:
            return expected
        return env[node.id]
    if isinstance(node, ast.Constant):
        if node.value != expected:
            raise ValueError("CONST_MISMATCH")
        return node.value
    if isinstance(node, ast.BinOp):
        op_name = type(node.op).__name__
        left_has = _contains_target(node.left, target)
        right_has = _contains_target(node.right, target)
        if left_has and not right_has:
            known = _forward_eval(node.right, env)
            if op_name == "Add":
                return _invert_add(expected, known)
            if op_name == "Sub":
                return _invert_sub_left(expected, known)
            if op_name == "Mult":
                return _invert_mul(expected, known)
            if op_name == "FloorDiv":
                return _invert_floordiv(expected, known)
            if op_name == "Mod":
                return _invert_mod(expected, known)
            raise ValueError(f"UNSUPPORTED_BINOP_{op_name}")
        if right_has and not left_has:
            known = _forward_eval(node.left, env)
            if op_name == "Add":
                return _invert_add(expected, known)
            if op_name == "Sub":
                return _invert_sub_right(expected, known)
            if op_name == "Mult":
                return _invert_mul(expected, known)
            if op_name == "FloorDiv":
                # expected = known // missing => missing in (known/(expected+1), known/expected]
                # Return known // expected as witness when expected != 0
                if expected == 0:
                    raise ValueError("FLOORDIV_RIGHT_ZERO")
                return known // expected
            if op_name == "Mod":
                # expected = known % missing => missing > expected, missing <= known
                # Return known as witness when valid
                if not (expected < known):
                    raise ValueError("MOD_RIGHT_RANGE")
                return known
            raise ValueError(f"UNSUPPORTED_BINOP_{op_name}")
        if left_has and right_has:
            raise ValueError("TARGET_BOTH_SIDES")
        # No target: check forward value matches expected
        got = _forward_eval(node, env)
        if got != expected:
            raise ValueError("FORWARD_MISMATCH")
        return got
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        return -_backward_eval(node.operand, expected, env, target)
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
        # expected is bool; invert
        return not bool(expected)
    if isinstance(node, ast.Compare) and len(node.ops) == 1:
        # expected is bool; propagate to operands via known side
        left_has = _contains_target(node.left, target)
        right_has = _contains_target(node.comparators[0], target)
        op = node.ops[0]
        if left_has and not right_has:
            known = _forward_eval(node.comparators[0], env)
            return _invert_compare(expected, op, known, side="left")
        if right_has and not left_has:
            known = _forward_eval(node.left, env)
            return _invert_compare(expected, op, known, side="right")
        raise ValueError("COMPARE_TARGET")
    if isinstance(node, ast.Call):
        # Calls are handled by call-chain propagation (see propagate_through_call).
        # Here refuse: backward through arbitrary calls needs callee body.
        raise ValueError("CALL_NEEDS_CALLEE")
    if isinstance(node, ast.IfExp):
        # expected = (body if test else orelse). Try both branches.
        # If test is known, pick the taken branch.
        try:
            test_val = _forward_eval(node.test, env)
        except Exception:
            test_val = None
        if test_val is True:
            return _backward_eval(node.body, expected, env, target)
        if test_val is False:
            return _backward_eval(node.orelse, expected, env, target)
        raise ValueError("IFEXP_TEST_UNKNOWN")
    raise ValueError(f"UNSUPPORTED_NODE_{type(node).__name__}")


def _invert_compare(expected: bool, op: ast.AST, known: Any, *, side: str) -> Any:
    # Return a witness value for the unknown side that satisfies the comparison.
    # Witnesses are canonical (known itself, known+1, known-1) — verifier decides.
    if isinstance(op, ast.Eq):
        return known
    if isinstance(op, ast.NotEq):
        return known + 1 if isinstance(known, int) else (known + "x" if isinstance(known, str) else known)
    if isinstance(op, ast.Lt):
        # left < right
        if side == "left":
            return known - 1
        return known + 1
    if isinstance(op, ast.LtE):
        if side == "left":
            return known
        return known
    if isinstance(op, ast.Gt):
        if side == "left":
            return known + 1
        return known - 1
    if isinstance(op, ast.GtE):
        if side == "left":
            return known
        return known
    raise ValueError("UNSUPPORTED_COMPARE")


def _contains_target(node: ast.AST, target: str) -> bool:
    return any(isinstance(n, ast.Name) and n.id == target for n in ast.walk(node))


def _forward_eval(node: ast.AST, env: dict[str, Any]) -> Any:
    if isinstance(node, ast.Name):
        return env[node.id]
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.BinOp):
        left = _forward_eval(node.left, env)
        right = _forward_eval(node.right, env)
        op = node.op
        if isinstance(op, ast.Add):
            return left + right
        if isinstance(op, ast.Sub):
            return left - right
        if isinstance(op, ast.Mult):
            return left * right
        if isinstance(op, ast.FloorDiv):
            return left // right
        if isinstance(op, ast.Mod):
            return left % right
        if isinstance(op, ast.Div):
            return left / right
        raise ValueError("UNSUPPORTED_BINOP_FWD")
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        return -_forward_eval(node.operand, env)
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
        return not bool(_forward_eval(node.operand, env))
    if isinstance(node, ast.Compare):
        left = _forward_eval(node.left, env)
        for op, comp in zip(node.ops, node.comparators):
            right = _forward_eval(comp, env)
            if isinstance(op, ast.Eq):
                ok = left == right
            elif isinstance(op, ast.NotEq):
                ok = left != right
            elif isinstance(op, ast.Lt):
                ok = left < right
            elif isinstance(op, ast.LtE):
                ok = left <= right
            elif isinstance(op, ast.Gt):
                ok = left > right
            elif isinstance(op, ast.GtE):
                ok = left >= right
            else:
                raise ValueError("UNSUPPORTED_COMPARE_FWD")
            if not ok:
                return False
            left = right
        return True
    if isinstance(node, ast.BoolOp):
        vals = [_forward_eval(v, env) for v in node.values]
        if isinstance(node.op, ast.And):
            return all(bool(v) for v in vals)
        return any(bool(v) for v in vals)
    if isinstance(node, ast.IfExp):
        return _forward_eval(node.body if bool(_forward_eval(node.test, env)) else node.orelse, env)
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "len":
        return len(_forward_eval(node.args[0], env))
    raise ValueError(f"UNSUPPORTED_FWD_{type(node).__name__}")


def propagate_through_call(
    caller_expr: str,
    expected: Any,
    known_env: Mapping[str, Any],
    callee_source: str,
    callee_name: str,
    *,
    callee_param: str,
) -> dict[str, Any]:
    """Propagate expected backward through a single call to the callee's parameter.

    caller_expr is like "helper(x)" or "helper(x) + 1". callee_source is the
    callee's full function source. Returns the required value for callee_param.
    """
    # Step 1: backward through caller_expr to the call argument.
    # Parse caller_expr, find the Call node, invert outer ops.
    try:
        tree = ast.parse(caller_expr, mode="eval")
    except SyntaxError:
        return {"status": "REFUSE", "reason": "REFUSE__SYNTAX"}
    # Find call args: caller_expr should be helper(arg) possibly wrapped.
    # Simplify: if caller_expr is exactly helper(arg), expected is the arg's required value.
    body = tree.body
    if isinstance(body, ast.Call) and isinstance(body.func, ast.Name) and body.func.id == callee_name:
        if len(body.args) != 1:
            return {"status": "REFUSE", "reason": "REFUSE__ARITY"}
        arg_node = body.args[0]
        # arg_node should be a Name (the caller's variable)
        if not isinstance(arg_node, ast.Name):
            return {"status": "REFUSE", "reason": "REFUSE__ARG_NOT_NAME"}
        arg_name = arg_node.id
        # Step 2: backward through callee body to callee_param.
        # callee_source: def helper(param): return <expr>
        try:
            ctree = ast.parse(callee_source)
        except SyntaxError:
            return {"status": "REFUSE", "reason": "REFUSE__CALLEE_SYNTAX"}
        ret_expr = None
        for node in ast.walk(ctree):
            if isinstance(node, ast.Return) and node.value is not None:
                ret_expr = ast.unparse(node.value)
                break
        if ret_expr is None:
            return {"status": "REFUSE", "reason": "REFUSE__NO_RETURN"}
        back = backward_propagate(ret_expr, expected, {}, unknown_name=callee_param)
        if back["status"] != "COMPUTED":
            return back
        return {
            "status": "COMPUTED",
            "missing_value": back["missing_value"],
            "missing_name": callee_param,
            "caller_arg": arg_name,
        }
    # Wrapped call (e.g. helper(x) + 1): backward through outer BinOp first.
    # Find the call inside and invert.
    for node in ast.walk(body):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == callee_name:
            # Invert outer expression to get required call result.
            # Replace call with a fresh name, backward-propagate.
            call_src = ast.unparse(node)
            fresh = "__call_result__"
            outer_src = caller_expr.replace(call_src, fresh)
            outer_back = backward_propagate(outer_src, expected, dict(known_env), unknown_name=fresh)
            if outer_back["status"] != "COMPUTED":
                return outer_back
            call_expected = outer_back["missing_value"]
            # Now recurse with direct call
            direct = f"{callee_name}({ast.unparse(node.args[0]) if node.args else ''})"
            return propagate_through_call(direct, call_expected, known_env, callee_source, callee_name, callee_param=callee_param)
    return {"status": "REFUSE", "reason": "REFUSE__CALL_NOT_FOUND"}


# ---------------------------------------------------------------------------
# 2. CEGIS(T) lite: skeleton + generalized constraints over constants
# ---------------------------------------------------------------------------


def cegis_synthesize(
    skeleton: str,
    examples: Sequence[tuple[Mapping[str, Any], Any]],
    *,
    constant_names: Sequence[str] = (),
    max_iters: int = 8,
    verify_fn: Any | None = None,
) -> dict[str, Any]:
    """CEGIS loop with generalized constraints (not concrete-only).

    skeleton contains holes like ?c0, ?c1 (rendered as {c0} for eval).
    examples are (env, expected) pairs. verify_fn(candidate_source, env, expected)
    -> bool, or None to use forward evaluation only.

    Returns {"status": "SOLVED", "source": ..., "constraints": ...} or
    {"status": "REFUSE", "reason": ..., "iters": n}.
    """
    if not examples:
        return {"status": "REFUSE", "reason": "REFUSE__NO_EXAMPLES"}
    # Constraint store: for each constant, allowed interval [lo, hi] (inclusive)
    # and forbidden values. Generalized: a counterexample blocks a family.
    # Seed with backward propagation from the first example when possible
    # (compute, don't enumerate from -1e9).
    lo: dict[str, int | float] = {}
    hi: dict[str, int | float] = {}
    forbidden: dict[str, set[Any]] = {c: set() for c in constant_names}
    for c in constant_names:
        lo[c] = -10**6
        hi[c] = 10**6
    # Seed: try backward propagation on first example with skeleton holes as unknowns.
    # Skeleton like "x + {c0}" -> expression "x + c0" with c0 unknown.
    if constant_names and examples:
        env0, exp0 = examples[0]
        seed_expr = skeleton
        for c in constant_names:
            seed_expr = seed_expr.replace("{" + c + "}", c)
        for c in constant_names:
            back = backward_propagate(seed_expr, exp0, dict(env0), unknown_name=c)
            if back["status"] == "COMPUTED" and isinstance(back["missing_value"], (int, float)):
                v = back["missing_value"]
                lo[c] = v
                hi[c] = v
                break
    iters = 0
    for it in range(max_iters):
        iters = it + 1
        # Propose: pick smallest allowed value not forbidden (deterministic).
        # First proposal prefers 0 (clamped) for fast convergence when no seed.
        assignment: dict[str, Any] = {}
        for c in constant_names:
            v = lo[c] if lo[c] == hi[c] else max(lo[c], min(0, hi[c]))
            while v in forbidden[c]:
                v += 1
            if v > hi[c]:
                return {"status": "REFUSE", "reason": "REFUSE__CONSTRAINT_UNSAT", "iters": iters}
            assignment[c] = v
        candidate = skeleton
        for c in constant_names:
            candidate = candidate.replace("{" + c + "}", repr(assignment[c]))
        # Verify on all examples
        failed: list[tuple[Mapping[str, Any], Any, Any]] = []
        for env, expected in examples:
            try:
                got = _forward_eval(ast.parse(candidate, mode="eval").body, dict(env))
            except Exception as exc:
                failed.append((env, expected, f"ERROR:{exc}"))
                continue
            if verify_fn is not None:
                ok = bool(verify_fn(candidate, env, expected))
            else:
                ok = got == expected
            if not ok:
                failed.append((env, expected, got))
        if not failed:
            return {
                "status": "SOLVED",
                "source": candidate,
                "assignment": assignment,
                "constraints": {c: {"lo": lo[c], "hi": hi[c], "forbidden": sorted(forbidden[c], key=repr)} for c in constant_names},
                "iters": iters,
            }
        # Generalize: for each failed example, derive a constraint blocking the family.
        # If got < expected, the constant is too small (for + skeletons); if got > expected, too large.
        # This is the CEGIS(T) step: propagate a generalized constraint, not just block one candidate.
        for env, expected, got in failed:
            if isinstance(got, (int, float)) and isinstance(expected, (int, float)):
                for c in constant_names:
                    # Heuristic: if increasing c would increase output, direction follows sign.
                    # Probe: evaluate with c+1.
                    probe_env = dict(env)
                    probe_assignment = dict(assignment)
                    probe_assignment[c] = assignment[c] + 1
                    probe_src = skeleton
                    for cc in constant_names:
                        probe_src = probe_src.replace("{" + cc + "}", repr(probe_assignment[cc]))
                    try:
                        probe_got = _forward_eval(ast.parse(probe_src, mode="eval").body, probe_env)
                    except Exception:
                        continue
                    if probe_got > got:
                        # c increases output: got < expected => c must be larger
                        if got < expected:
                            lo[c] = max(lo[c], assignment[c] + 1)
                        else:
                            hi[c] = min(hi[c], assignment[c] - 1)
                    elif probe_got < got:
                        if got < expected:
                            hi[c] = min(hi[c], assignment[c] - 1)
                        else:
                            lo[c] = max(lo[c], assignment[c] + 1)
                    else:
                        forbidden[c].add(assignment[c])
            else:
                for c in constant_names:
                    forbidden[c].add(assignment[c])
    return {"status": "REFUSE", "reason": "REFUSE__BUDGET", "iters": iters}


# ---------------------------------------------------------------------------
# 3. Cross-modal Petri net (unified typed transitions)
# ---------------------------------------------------------------------------


def build_petri_net(
    transitions: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Build a typed transition graph. Each transition: {id, from_type, to_type, cost, kind}.

    Kinds: GUI, CLI, SQL, PY (all just typed edges in one graph).
    """
    nodes: set[str] = set()
    edges: list[dict[str, Any]] = []
    for t in transitions:
        frm = str(t["from_type"])
        to = str(t["to_type"])
        nodes.add(frm)
        nodes.add(to)
        edges.append(
            {
                "id": str(t["id"]),
                "from": frm,
                "to": to,
                "cost": float(t.get("cost", 1.0)),
                "kind": str(t.get("kind", "PY")),
            }
        )
    return {"nodes": sorted(nodes), "edges": edges}


def solve_petri_net(
    net: Mapping[str, Any],
    start_type: str,
    goal_type: str,
) -> dict[str, Any]:
    """Shortest-path (Dijkstra) over the unified net. Returns the morphism (edge list)."""
    adj: dict[str, list[dict[str, Any]]] = {}
    for e in net.get("edges") or []:
        adj.setdefault(str(e["from"]), []).append(e)
    # Dijkstra
    dist: dict[str, float] = {start_type: 0.0}
    prev: dict[str, tuple[str, dict[str, Any]]] = {}
    pq: list[tuple[float, str]] = [(0.0, start_type)]
    visited: set[str] = set()
    while pq:
        d, u = heapq.heappop(pq)
        if u in visited:
            continue
        visited.add(u)
        if u == goal_type:
            break
        for e in adj.get(u, []):
            v = str(e["to"])
            nd = d + float(e["cost"])
            if v not in dist or nd < dist[v]:
                dist[v] = nd
                prev[v] = (u, e)
                heapq.heappush(pq, (nd, v))
    if goal_type not in dist:
        return {"status": "REFUSE", "reason": "REFUSE__NO_PATH"}
    # Reconstruct morphism
    path: list[dict[str, Any]] = []
    cur = goal_type
    while cur != start_type:
        pu, e = prev[cur]
        path.append(e)
        cur = pu
    path.reverse()
    return {
        "status": "SOLVED",
        "morphism": path,
        "cost": dist[goal_type],
        "types": [start_type] + [str(e["to"]) for e in path],
    }


# ---------------------------------------------------------------------------
# 4. Differential state tomography (turn app into deterministic API)
# ---------------------------------------------------------------------------


def snapshot_state(root: pathlib.Path) -> dict[str, Any]:
    """Snapshot files + SQLite tables + env. Returns a comparable dict."""
    root = pathlib.Path(root)
    files: dict[str, str] = {}
    for p in sorted(root.rglob("*")):
        if p.is_file() and "__pycache__" not in p.parts and ".git" not in p.parts:
            try:
                files[str(p.relative_to(root))] = hashlib.sha256(p.read_bytes()).hexdigest()
            except OSError:
                continue
    tables: dict[str, Any] = {}
    for p in sorted(root.rglob("*.db")) + sorted(root.rglob("*.sqlite")) + sorted(root.rglob("*.sqlite3")):
        try:
            conn = sqlite3.connect(str(p))
            names = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
            for name in names:
                try:
                    rows = conn.execute(f"SELECT * FROM \"{name}\"").fetchall()
                    tables[f"{p.name}:{name}"] = [list(r) for r in rows]
                except sqlite3.Error:
                    continue
            conn.close()
        except sqlite3.Error:
            continue
    return {"files": files, "tables": tables, "env": dict(os.environ)}


def diff_states(before: Mapping[str, Any], after: Mapping[str, Any]) -> dict[str, Any]:
    """Diff two snapshots. Returns changed files/tables/env keys."""
    changed_files = sorted(
        k for k in set(before.get("files", {})) | set(after.get("files", {}))
        if before.get("files", {}).get(k) != after.get("files", {}).get(k)
    )
    changed_tables = sorted(
        k for k in set(before.get("tables", {})) | set(after.get("tables", {}))
        if before.get("tables", {}).get(k) != after.get("tables", {}).get(k)
    )
    changed_env = sorted(
        k for k in set(before.get("env", {})) | set(after.get("env", {}))
        if before.get("env", {}).get(k) != after.get("env", {}).get(k)
    )
    return {
        "changed_files": changed_files,
        "changed_tables": changed_tables,
        "changed_env": changed_env,
        "transition_observed": bool(changed_files or changed_tables or changed_env),
    }


def infer_state_machine(
    transitions: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Infer a Mealy table from observed (state, action) -> (next_state, diff) transitions.

    transitions: [{state, action, next_state, diff}]. Returns deterministic table.
    """
    table: dict[str, Any] = {}
    conflicts = 0
    for t in transitions:
        key = f"{t['state']} --{t['action']}-->"
        if key in table and table[key] != t["next_state"]:
            conflicts += 1
        table[key] = t["next_state"]
    return {
        "table": table,
        "transitions": len(transitions),
        "conflicts": conflicts,
        "deterministic": conflicts == 0,
    }


# ---------------------------------------------------------------------------
# 5. Self-play delta-debug (minimal failing inputs from hard failures)
# ---------------------------------------------------------------------------


def delta_debug_minimize(
    items: Sequence[Any],
    is_failing: Any,
    *,
    max_evals: int = 64,
) -> dict[str, Any]:
    """ddmin-style minimization: shrink items while is_failing holds.

    is_failing(subset) -> bool (True = still failing). Returns minimal subset.
    """
    current = list(items)
    evals = 0
    # Granularity loop (classic ddmin)
    n = 2
    while len(current) >= 2:
        chunk_size = max(1, len(current) // n)
        reduced = False
        i = 0
        while i < len(current):
            if evals >= max_evals:
                break
            candidate = current[:i] + current[i + chunk_size :]
            if candidate and is_failing(candidate):
                current = candidate
                evals += 1
                n = max(2, n - 1)
                reduced = True
                break
            evals += 1
            i += chunk_size
        if not reduced:
            if n >= len(current):
                break
            n = min(len(current), n * 2)
        if evals >= max_evals:
            break
    return {"minimal": current, "evals": evals, "original_size": len(items)}


def _env(repo: pathlib.Path) -> dict[str, str]:
    return {
        "PYTHONPATH": ":".join([str(repo), str(repo / "src"), str(repo / "tests")]),
        "PATH": "/usr/local/bin:/usr/bin:/bin",
        "HOME": str(repo),
        "PYTHONDONTWRITEBYTECODE": "1",
    }


def verify_with_real_test(
    repo: pathlib.Path,
    command: Sequence[str],
    file_path: pathlib.Path,
    original: str,
    candidate_source: str,
    timeout: float = 60.0,
) -> bool:
    try:
        file_path.write_text(candidate_source, encoding="utf-8")
        for stale in repo.rglob("__pycache__"):
            shutil.rmtree(stale, ignore_errors=True)
        try:
            done = subprocess.run(
                list(command),
                cwd=str(repo),
                capture_output=True,
                text=True,
                timeout=timeout,
                env=_env(repo),
            )
        except subprocess.TimeoutExpired:
            return False
        return done.returncode == 0
    finally:
        file_path.write_text(original, encoding="utf-8")
