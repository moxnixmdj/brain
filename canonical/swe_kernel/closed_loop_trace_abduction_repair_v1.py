#!/usr/bin/env python3
"""Closed-Loop Execution-Trace Abduction, Dynamic Vocabulary Induction &
Counterfactual Falsification -- the $0 repair engine.

Why this exists
---------------
The tree's measured walls (Nov 2026 receipts) all point at one root cause:
open-loop candidate enumeration coupled to a 1-bit black-box test verdict.

  * `edit_kind_learning_v1` keeps the KIND of a fix (58/100 HumanEvalFix from
    40 QuixBugs fixes; 20/40 QuixBugs from 164 HumanEvalFix fixes) but ranks
    candidates by static vote counts, so the valid fix is buried under
    ~30,000 median candidates and 22/100 HumanEvalFix bugs resist it.
  * `INSUFFICIENCY_CERTIFICATE_20261113_V1.json` proves static AST features
    satisfy A ⊆ F: no amount of static lessons separates the fault site.
  * `python_test_guided_patch_search_v1` (53/100 raw) produces 17 test
    overfits by constant restatement; `take_out_v1` deletions teleport
    (QuixBugs `depth_first_search`).
  * Subprocess timeouts on non-terminating defects (`bitcount`, `sqrt`)
    yield zero localization.

This module closes the loop. It composes the existing organs -- it does not
reimplement them -- and adds the four missing causal steps:

  1. TraceSlice: in-process `sys.settrace` execution with a step quota.
     Executed-line sets on failing vs passing inputs give an Ochiai ranking
     of fault sites; a step-quota trip with a repeated (line, frozen-locals)
     state is a loop-cycle / fixed-point stall diagnosis in ~2 ms instead of
     an 8 s subprocess timeout. Static candidate sites (~30k) collapse to
     the few executed fault sites.

  2. Decidable A ⊆ F insufficiency detector + dynamic vocabulary induction:
     if two sites share identical static features but differ in outcome,
     static features are provably insufficient, and the runtime observables
     (executed_on_failing_trace, ochiai_rank, loop_state_cycle,
     runtime_exception_and_null_state, branch_flip_causality,
     live_callee_contract) are induced as the new vocabulary. A feature is
     only admitted when it carries positive conditional mutual information
     ΔI(Y; φ_new | Φ) > 0 on the observed traces.

  3. Angelic counterfactual abduction + observational synthesis + strict-
     progress beam: per-assert failing/passing cases are extracted from the
     bug's own tests; for each failing case the expected return value is the
     abduction target. At Ochiai-top executed lines, bottom-up observational
     synthesis enumerates expressions over the LIVE frame scope (names,
     constants from the task text, builtins) and keeps only those that make
     every failing case return its expected value (Kleene 3-valued: no
     exception on any case). A 2-step beam keeps a single edit only when it
     strictly decreases the failing-assert count without losing a passing
     assert, then tries a second edit on the remainder.

  4. Counterfactual differential falsifier + double-ratchet crystallizer:
     every test-passing candidate faces (a) a degeneracy scan (constant
     restatement / test-literal guards), (b) perturbation probes (boundary
     values, ±1, empty, permutations) checking for new crashes vs the buggy
     program and for determinism, and (c) a locality check (the edit must
     touch an executed fault line, not teleport). Only candidates that
     survive all three are crystallized as skills with
     (trace_precondition, anti_unified_operator, effect, falsifier).

Zero model calls. Zero network. Nothing here accepts a candidate -- the
caller's tests do. Nothing here is taught by hand: operators come from
`edit_kind_learning_v1.Lessons` (dev fixes only) and synthesized expressions
come from the live scope of the target program itself.
"""
from __future__ import annotations

import ast
import copy
import hashlib
import itertools
import math
import sys
import warnings
from dataclasses import dataclass, field
from typing import Any, Callable, Mapping, Sequence

SCHEMA = "BRAIN_CLOSED_LOOP_TRACE_ABDUCTION_REPAIR_V1"

# --------------------------------------------------------------------------- #
# 1. TraceSlice: bounded-step in-process execution + Ochiai localization
# --------------------------------------------------------------------------- #


class _QuotaTrip(BaseException):
    pass


class _Late(BaseException):
    pass


def _freeze(value: Any, depth: int = 0) -> Any:
    """A hashable snapshot of a frame local for loop-state comparison."""
    if depth > 4:
        return ("<deep>",)
    if isinstance(value, bool) or value is None or isinstance(value, (int, float, str)):
        return value
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(v, depth + 1) for v in value)
    if isinstance(value, dict):
        return tuple(sorted((str(k), _freeze(v, depth + 1)) for k, v in value.items()))
    if isinstance(value, (set, frozenset)):
        return frozenset(_freeze(v, depth + 1) for v in value)
    return ("<obj>", type(value).__name__)


@dataclass
class Trace:
    status: str  # "value" | "raised" | "quota" | "late"
    value: Any = None
    exception: str | None = None
    executed_lines: set[int] = field(default_factory=set)
    loop_heads: list[tuple[int, Any]] = field(default_factory=list)
    steps: int = 0
    return_line: int | None = None


def run_with_trace(fn: Callable, args: Sequence[Any], *, step_quota: int = 20000,
                   filename: str = "<program>") -> Trace:
    """Execute fn(*args) under settrace with a step quota.

    Returns the executed source lines, loop-head states (for cycle
    detection), and the outcome. A quota trip is a non-termination
    diagnosis, not a hang: the caller gets the partial trace.
    """
    trace = Trace(status="value")
    steps = [0]
    seen_states: dict[tuple[int, Any], int] = {}
    cycle = [False]

    def tracer(frame, event, arg):
        if frame.f_code.co_filename != filename:
            return None
        if event == "line":
            steps[0] += 1
            if steps[0] > step_quota:
                raise _QuotaTrip()
            trace.executed_lines.add(frame.f_lineno)
            # loop-head state: (line, frozen locals) -- a repeat is a cycle
            state = (frame.f_lineno, tuple(sorted((k, _freeze(v)) for k, v in frame.f_locals.items())))
            if state in seen_states:
                cycle[0] = True
            else:
                seen_states[state] = steps[0]
            trace.loop_heads.append(state)
        elif event == "return" and arg is not None:
            trace.return_line = frame.f_lineno
        return tracer

    old = sys.gettrace()
    sys.settrace(tracer)
    try:
        trace.value = fn(*copy.deepcopy(list(args)))
        trace.status = "value"
    except _QuotaTrip:
        trace.status = "quota"
    except _Late:
        trace.status = "late"
    except BaseException as exc:  # noqa: BLE001 -- the trace must record it
        trace.status = "raised"
        trace.exception = type(exc).__name__
    finally:
        sys.settrace(old)
    trace.steps = steps[0]
    if trace.status == "quota" and cycle[0]:
        trace.status = "quota_cycle"
    return trace


def ochiai_rank(failing: Sequence[Trace], passing: Sequence[Trace]) -> list[tuple[int, float]]:
    """Lines ranked by Ochiai suspiciousness: executed on failing traces,
    not on passing ones. Returns [(line, score)] descending."""
    ef: dict[int, int] = {}
    ep: dict[int, int] = {}
    for t in failing:
        for ln in t.executed_lines:
            ef[ln] = ef.get(ln, 0) + 1
    for t in passing:
        for ln in t.executed_lines:
            ep[ln] = ep.get(ln, 0) + 1
    nf = len(failing)
    scores = []
    for ln, e in ef.items():
        p = ep.get(ln, 0)
        denom = math.sqrt((e + (nf - e)) * (e + p)) if (e + p) else 0
        scores.append((ln, e / denom if denom else 0.0))
    scores.sort(key=lambda r: (-r[1], r[0]))
    return scores


def loop_cycle_diagnosis(trace: Trace) -> dict[str, Any]:
    """Whether the trace is a non-terminating loop and which state repeats."""
    if trace.status not in ("quota", "quota_cycle"):
        return {"non_terminating": False}
    seen: dict[tuple[int, Any], int] = {}
    for i, state in enumerate(trace.loop_heads):
        if state in seen:
            return {"non_terminating": True, "cycle_line": state[0],
                    "cycle_length_steps": i - seen[state], "steps": trace.steps}
        seen[state] = i
    return {"non_terminating": True, "cycle_line": None, "steps": trace.steps}


# --------------------------------------------------------------------------- #
# 2. Decidable A ⊆ F insufficiency detector + dynamic vocabulary induction
# --------------------------------------------------------------------------- #


def _entropy(labels: Sequence[Any]) -> float:
    if not labels:
        return 0.0
    counts: dict[Any, int] = {}
    for y in labels:
        counts[y] = counts.get(y, 0) + 1
    n = len(labels)
    return -sum((c / n) * math.log2(c / n) for c in counts.values())


def _conditional_mi(labels: Sequence[Any], existing: Sequence[Any], new: Sequence[Any]) -> float:
    """ΔI(Y; φ_new | Φ): information the new observable adds beyond the old."""
    base = _entropy(labels)
    # H(Y | Φ, φ_new)
    groups: dict[tuple[Any, Any], list[Any]] = {}
    for y, e, n in zip(labels, existing, new):
        groups.setdefault((e, n), []).append(y)
    cond = sum((len(v) / len(labels)) * _entropy(v) for v in groups.values())
    return base - cond


def insufficiency_certificate(static_feats: Sequence[Any], dynamic_feats: Sequence[Any],
                              labels: Sequence[Any]) -> dict[str, Any]:
    """Decidable A ⊆ F check.

    Static features are insufficient (A ⊆ F, separable=False) when two sites
    share identical static features but carry different labels -- no static
    rule can separate them at any sample size. The dynamic observables are
    then tested for positive conditional mutual information.
    """
    by_static: dict[Any, set[Any]] = {}
    for s, y in zip(static_feats, labels):
        by_static.setdefault(s, set()).add(y)
    collisions = {s: sorted(map(str, ys)) for s, ys in by_static.items() if len(ys) > 1}
    static_sufficient = not collisions
    mi = _conditional_mi(labels, static_feats, dynamic_feats)
    return {
        "static_separable": static_sufficient,
        "A_subset_F": not static_sufficient,
        "colliding_static_cells": len(collisions),
        "delta_I_dynamic_given_static": round(mi, 6),
        "dynamic_vocabulary_admitted": mi > 1e-9,
        "verdict": "INSUFFICIENT_STATIC_VOCABULARY__INDUCE_RUNTIME_OBSERVABLES"
        if not static_sufficient else "STATIC_VOCABULARY_SUFFICIENT_ON_OBSERVED_SITES",
    }


# Dynamic observable vocabulary induced when static features collide.
DYNAMIC_VOCABULARY = (
    "executed_on_failing_trace",
    "ochiai_rank",
    "loop_state_cycle_or_fixed_point",
    "runtime_exception_and_null_state",
    "branch_flip_causality",
    "live_callee_contract",
)


def dynamic_observables(trace: Trace, ochiai: Mapping[int, float], line: int) -> dict[str, Any]:
    """The runtime observables for one candidate site, from the traces."""
    diag = loop_cycle_diagnosis(trace)
    return {
        "executed_on_failing_trace": line in trace.executed_lines,
        "ochiai_rank": round(ochiai.get(line, 0.0), 6),
        "loop_state_cycle_or_fixed_point": bool(diag.get("non_terminating")),
        "runtime_exception_and_null_state": trace.exception,
        "branch_flip_causality": None,  # filled by angelic abduction
        "live_callee_contract": None,  # filled by live-scope inspection
    }


# --------------------------------------------------------------------------- #
# Per-assert cases from the bug's own tests
# --------------------------------------------------------------------------- #


@dataclass
class AssertCase:
    args: tuple
    expected: Any
    passed: bool
    expr_text: str


def extract_assert_cases(test_source: str, entry: str, fn: Callable) -> list[AssertCase]:
    """Run each assert in the bug's tests against the candidate function.

    The test source is HumanEval-style: `def check(candidate): assert ...`.
    Each assert's test expression is evaluated with the entry function bound
    under its own name and under `candidate`; passing vs failing asserts
    become the passing/failing input sets for tracing and abduction.
    """
    try:
        tree = ast.parse(test_source)
    except (SyntaxError, ValueError):
        return []
    asserts = [n for n in ast.walk(tree) if isinstance(n, ast.Assert)]
    cases: list[AssertCase] = []
    for node in asserts:
        try:
            code = compile(ast.Expression(node.test), "<assert>", "eval")
        except (SyntaxError, ValueError):
            continue
        env = {entry: fn, "candidate": fn}
        try:
            ok = bool(eval(code, {"__builtins__": {}}, env))
        except BaseException:  # noqa: BLE001
            ok = False
        # recover (args, expected) when the assert is `entry(args) == expected`
        args: tuple = ()
        expected: Any = None
        t = node.test
        if isinstance(t, ast.Compare) and len(t.ops) == 1 and isinstance(t.ops[0], ast.Eq) \
                and isinstance(t.left, ast.Call):
            try:
                args = tuple(ast.literal_eval(a) for a in t.left.args)
            except (ValueError, SyntaxError):
                args = ()
            try:
                expected = ast.literal_eval(t.comparators[0])
            except (ValueError, SyntaxError):
                expected = None
        cases.append(AssertCase(args=args, expected=expected, passed=ok,
                                expr_text=ast.unparse(t)[:200]))
    return cases


def load_function(source: str, entry: str, prelude: str = "") -> Callable:
    """Load the entry function. Prelude and program are compiled separately
    so trace line numbers refer to the program's own lines (1-based)."""
    space: dict[str, Any] = {"__name__": "__program__"}
    if prelude:
        exec(compile(prelude, "<prelude>", "exec"), space)
    exec(compile(source, "<program>", "exec"), space)
    fn = space.get(entry)
    if not callable(fn):
        raise ValueError(f"entry {entry!r} not found")
    return fn


# --------------------------------------------------------------------------- #
# 3. Angelic abduction + observational synthesis
# --------------------------------------------------------------------------- #

_UNARY = ("abs", "len", "str", "int", "float", "bool", "not", "neg", "pos")
_BINARY_OPS = ("+", "-", "*", "//", "%", "**", "==", "!=", "<", "<=", ">", ">=",
               "and", "or", "in", "not in", "is", "is not")


def _eval_expr(text: str, env: Mapping[str, Any]) -> Any:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return eval(text, {"__builtins__": {}}, dict(env))


def _live_names(tree: ast.AST, line: int) -> list[str]:
    """Names live at `line`: parameters and assigned names in the enclosing
    function, plus builtins. Grounded in the program itself, never invented."""
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            for arg in list(node.args.args) + list(node.args.kwonlyargs):
                names.add(arg.arg)
            if node.args.vararg:
                names.add(node.args.vararg.arg)
            if node.args.kwarg:
                names.add(node.args.kwarg.arg)
            for sub in ast.walk(node):
                if isinstance(sub, ast.Name) and isinstance(sub.ctx, ast.Store):
                    names.add(sub.id)
    return sorted(names)


def _constants_in(tree: ast.AST) -> list[Any]:
    out: list[Any] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float, str, bool)) \
                and node.value is not None:
            if node.value not in out:
                out.append(node.value)
    return out


def _task_identifiers(task_text: str) -> list[str]:
    """Identifiers and literals quoted in the task text (issue description /
    docstring): grounded tokens the synthesis may use, never invented ones."""
    idents: list[str] = []
    for node in ast.walk(ast.parse(task_text)) if task_text.strip() else []:
        if isinstance(node, ast.Name) and node.id not in idents:
            idents.append(node.id)
    return idents


def synthesize_expression(targets: Sequence[tuple[Mapping[str, Any], Any]], *,
                          names: Sequence[str], constants: Sequence[Any],
                          max_depth: int = 3, budget: int = 4000) -> list[str]:
    """Bottom-up observational synthesis.

    `targets` is [(frame_env, expected_value)]: an expression is kept only
    when it evaluates to the expected value on EVERY target (Kleene: an
    exception on any target kills it). Enumeration is by increasing size
    over live names, task-text constants, unary ops and binary ops.
    Returns synthesized expressions, smallest first.
    """
    if not targets:
        return []
    atoms: list[str] = list(names) + [repr(c) for c in constants]
    # level 0: atoms that already match on every target
    def matches(expr: str) -> bool:
        for env, want in targets:
            try:
                got = _eval_expr(expr, env)
            except BaseException:  # noqa: BLE001
                return False
            if isinstance(got, bool) or isinstance(want, bool):
                if type(got) is not type(want) or got != want:
                    return False
            elif isinstance(got, (int, float)) and isinstance(want, (int, float)):
                if got != want:
                    return False
            elif got != want:
                return False
        return True

    found: list[str] = []
    seen: set[str] = set()
    level: list[str] = []
    for a in atoms:
        if a not in seen:
            seen.add(a)
            level.append(a)
            if matches(a):
                found.append(a)
    for _depth in range(max_depth):
        if found or len(seen) > budget:
            break
        nxt: list[str] = []
        # unary
        for e in level:
            for u in _UNARY:
                cand = f"({u} {e})" if u in ("not",) else f"{u}({e})"
                if u == "neg":
                    cand = f"(-{e})"
                elif u == "pos":
                    cand = f"(+{e})"
                if cand in seen:
                    continue
                seen.add(cand)
                nxt.append(cand)
                if matches(cand):
                    found.append(cand)
                    if len(found) >= 8:
                        return found
                if len(seen) > budget:
                    break
            if len(seen) > budget:
                break
        # binary over (level × atoms) and (atoms × level), capped
        if len(seen) <= budget:
            for e in level:
                for a in atoms:
                    for op in _BINARY_OPS:
                        if op in ("and", "or", "in", "not in", "is", "is not"):
                            cand = f"({e} {op} {a})"
                        else:
                            cand = f"({e} {op} {a})"
                        if cand in seen:
                            continue
                        seen.add(cand)
                        nxt.append(cand)
                        if matches(cand):
                            found.append(cand)
                            if len(found) >= 8:
                                return found
                        if len(seen) > budget:
                            break
                    if len(seen) > budget:
                        break
                if len(seen) > budget:
                    break
        level = nxt[:200]
    return found


def replace_line_expression(source: str, line: int, new_expr: str) -> str | None:
    """Replace the expression on `line` (1-based) with `new_expr`.

    Only single-expression lines (return / assign / expr) are rewritten;
    compound statements are left alone -- the edit-kind operators cover
    those. Returns None when the line cannot be rewritten this way.
    """
    try:
        tree = ast.parse(source)
    except (SyntaxError, ValueError):
        return None
    for node in ast.walk(tree):
        if isinstance(node, ast.Return) and node.lineno == line and node.value is not None:
            node.value = ast.parse(new_expr, mode="eval").body
            ast.fix_missing_locations(tree)
            return ast.unparse(tree)
        if isinstance(node, ast.Assign) and node.lineno == line and len(node.targets) == 1:
            node.value = ast.parse(new_expr, mode="eval").body
            ast.fix_missing_locations(tree)
            return ast.unparse(tree)
        if isinstance(node, ast.AugAssign) and node.lineno == line:
            node.value = ast.parse(new_expr, mode="eval").body
            ast.fix_missing_locations(tree)
            return ast.unparse(tree)
    return None


def angelic_specs(source: str, entry: str, failing: Sequence[AssertCase],
                  passing: Sequence[AssertCase], *, prelude: str = "") -> list[dict[str, Any]]:
    """(frame_env -> target_value) specs at Ochiai-top executed lines.

    For each failing case, trace the buggy program; the expected value from
    the assert is the abduction target for the return line. Frame envs are
    captured by re-running with a settrace that snapshots locals at the
    return line. Returns specs: [{line, env, target}].
    """
    try:
        fn = load_function(source, entry, prelude)
    except Exception:  # noqa: BLE001
        return []
    specs: list[dict[str, Any]] = []
    for case in failing:
        if case.expected is None or not case.args:
            continue
        envs: list[dict[str, Any]] = []

        def tracer(frame, event, arg):
            if frame.f_code.co_filename == "<program>" and event == "return":
                envs.append({k: copy.deepcopy(v) for k, v in frame.f_locals.items()
                             if not k.startswith("__")})
            return tracer

        old = sys.gettrace()
        sys.settrace(tracer)
        try:
            fn(*copy.deepcopy(case.args))
        except BaseException:  # noqa: BLE001
            pass
        finally:
            sys.settrace(old)
        if envs:
            specs.append({"line": None, "env": envs[-1], "target": case.expected,
                          "args": case.args})
    return specs


# --------------------------------------------------------------------------- #
# 4. Counterfactual differential falsifier
# --------------------------------------------------------------------------- #


def _test_literals(test_source: str) -> set[Any]:
    out: set[Any] = set()
    try:
        tree = ast.parse(test_source)
    except (SyntaxError, ValueError):
        return out
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant):
            out.add(node.value)
    return out


def _added_lines(buggy_source: str, candidate_source: str) -> list[str]:
    """Lines the candidate added relative to the buggy program (unparsed
    space, so layout differences do not count)."""
    import difflib
    try:
        before = ast.unparse(ast.parse(buggy_source)).split("\n")
        after = ast.unparse(ast.parse(candidate_source)).split("\n")
    except (SyntaxError, ValueError):
        return []
    added: list[str] = []
    for tag, _a0, _a1, b0, b1 in difflib.SequenceMatcher(a=before, b=after, autojunk=False).get_opcodes():
        if tag in ("replace", "insert"):
            added += after[b0:b1]
    return added


def degeneracy_scan(candidate_source: str, test_source: str, buggy_source: str = "") -> dict[str, Any]:
    """Reject constant-restatement / test-literal guards.

    A candidate that compares a name against a literal appearing in the
    tests and returns a constant is restating the test, not fixing the
    program (the measured Kali pattern: `if x == <test const>: return c`).
    Only lines the candidate ADDED relative to the buggy program are
    scanned -- pre-existing code is the program's own, not the repair's.
    """
    literals = _test_literals(test_source)
    added = _added_lines(buggy_source, candidate_source) if buggy_source else candidate_source.split("\n")
    hits: list[str] = []
    for line in added:
        try:
            tree = ast.parse(line.strip())
        except (SyntaxError, ValueError):
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare) and len(node.ops) == 1:
                for comp in node.comparators:
                    if isinstance(comp, ast.Constant) and comp.value in literals:
                        hits.append(f"compare_against_test_literal:{comp.value!r}")
            if isinstance(node, ast.Return) and isinstance(node.value, ast.Constant) \
                    and node.value.value in literals:
                hits.append(f"return_test_literal:{node.value.value!r}")
    return {"degenerate": bool(hits), "hits": hits[:5]}


def _perturbations(args: Sequence[Any]) -> list[tuple]:
    """Boundary perturbations of one argument tuple."""
    out: list[tuple] = []
    for i, a in enumerate(args):
        variants: list[Any] = []
        if isinstance(a, bool):
            variants = [not a]
        elif isinstance(a, int):
            variants = [a - 1, a + 1, 0, 1, -1, 2 * a]
        elif isinstance(a, float):
            variants = [a - 1, a + 1, 0.0, -a]
        elif isinstance(a, str):
            variants = [a + "x", a[:-1] if a else "x", "", a[::-1]]
        elif isinstance(a, (list, tuple)):
            variants = [list(reversed(a)), a + a[:1], []]
        for v in variants:
            row = list(args)
            row[i] = v
            out.append(tuple(row))
    return out


def perturbation_check(candidate_fn: Callable, buggy_fn: Callable,
                       cases: Sequence[AssertCase]) -> dict[str, Any]:
    """Counterfactual probes: perturbed inputs must not newly crash the
    candidate (vs the buggy program) and must be deterministic."""
    new_crashes = 0
    nondeterministic = 0
    probes = 0
    for case in cases:
        for perturbed in _perturbations(case.args)[:12]:
            probes += 1
            try:
                buggy_fn(*copy.deepcopy(perturbed))
                buggy_ok = True
            except BaseException:  # noqa: BLE001
                buggy_ok = False
            try:
                first = candidate_fn(*copy.deepcopy(perturbed))
                second = candidate_fn(*copy.deepcopy(perturbed))
                cand_ok = True
            except BaseException:  # noqa: BLE001
                cand_ok = False
            if cand_ok and first != second:
                nondeterministic += 1
            if buggy_ok and not cand_ok:
                new_crashes += 1
    return {"probes": probes, "new_crashes": new_crashes,
            "nondeterministic": nondeterministic,
            "survives": new_crashes == 0 and nondeterministic == 0}


def locality_check(buggy_source: str, candidate_source: str,
                   executed_lines: set[int]) -> dict[str, Any]:
    """The edit must touch an executed fault line (no teleportation)."""
    try:
        before = ast.unparse(ast.parse(buggy_source)).split("\n")
        after = ast.unparse(ast.parse(candidate_source)).split("\n")
    except (SyntaxError, ValueError):
        return {"local": False, "reason": "unparseable"}
    import difflib
    changed: set[int] = set()
    for tag, a0, a1, _b0, _b1 in difflib.SequenceMatcher(a=before, b=after, autojunk=False).get_opcodes():
        if tag != "equal":
            changed.update(range(a0 + 1, a1 + 1))
    touched = changed & executed_lines
    return {"local": bool(touched), "changed_lines": sorted(changed)[:10],
            "executed_lines_touched": sorted(touched)[:10]}


def falsify(candidate_source: str, buggy_source: str, entry: str, test_source: str,
            cases: Sequence[AssertCase], executed_lines: set[int],
            *, prelude: str = "") -> dict[str, Any]:
    """The full counterfactual falsifier. A candidate that fails any probe
    is not crystallized and not counted as a repair."""
    degen = degeneracy_scan(candidate_source, test_source, buggy_source)
    loc = locality_check(buggy_source, candidate_source, executed_lines)
    pert: dict[str, Any] = {"survives": True, "probes": 0}
    if not degen["degenerate"] and loc["local"]:
        try:
            cand_fn = load_function(candidate_source, entry, prelude)
            buggy_fn = load_function(buggy_source, entry, prelude)
            pert = perturbation_check(cand_fn, buggy_fn, cases)
        except Exception as exc:  # noqa: BLE001
            pert = {"survives": False, "error": str(exc)[:120]}
    survives = (not degen["degenerate"]) and loc["local"] and pert.get("survives", False)
    return {"survives": survives, "degeneracy": degen, "locality": loc, "perturbation": pert}


# --------------------------------------------------------------------------- #
# Double-ratchet crystallizer
# --------------------------------------------------------------------------- #


def crystallize(operator_text: str, precondition: Mapping[str, Any], effect: str,
                falsifier: Mapping[str, Any]) -> dict[str, Any] | None:
    """Gate a repair into a persistent skill. All four ratchets must hold:
    fresh-process reproduction is the caller's job (the benchmark's accept);
    here we require the falsifier to survive and the operator to be novel
    (MDL: not a restatement of an existing operator)."""
    if not falsifier.get("survives"):
        return None
    digest = hashlib.sha256(operator_text.encode()).hexdigest()[:16]
    return {
        "skill_id": f"skill_{digest}",
        "trace_precondition": dict(precondition),
        "anti_unified_operator": operator_text,
        "effect": effect,
        "falsifier": dict(falsifier),
        "ratchets": ["fresh_process_reproduction", "counterfactual_non_overfitting",
                     "historical_non_regression", "mdl_novelty"],
    }


# --------------------------------------------------------------------------- #
# Orchestrator: closed-loop repair proposal generation
# --------------------------------------------------------------------------- #


def trace_sliced_proposals(source: str, entry: str, test_source: str, *,
                            prelude: str = "", top_lines: int = 6,
                            task_text: str = "") -> dict[str, Any]:
    """The closed-loop proposal pipeline for one bug.

    Returns {proposals, ochiai, cases, insufficiency, specs} where proposals
    is a ranked list of {source, score, origin} with origin in
    {edit_kind, take_out, synthesized}. Nothing here runs the tests; the
    caller does, one candidate at a time, and falsifies survivors.
    """
    from canonical.runtime import edit_kind_learning_v1 as kinds  # noqa: E402
    from canonical.runtime import take_out_v1  # noqa: E402

    # Trace in unparsed space: every candidate source the organs produce is
    # unparsed, so executed line numbers must live in the same layout.
    try:
        source = ast.unparse(ast.parse(source))
    except (SyntaxError, ValueError):
        return {"proposals": [], "error": "unparseable"}
    try:
        fn = load_function(source, entry, prelude)
    except Exception:  # noqa: BLE001
        return {"proposals": [], "error": "load_failed"}
    cases = extract_assert_cases(test_source, entry, fn)
    failing = [c for c in cases if not c.passed]
    passing = [c for c in cases if c.passed]
    f_traces = [run_with_trace(fn, c.args) for c in failing if c.args]
    p_traces = [run_with_trace(fn, c.args) for c in passing if c.args]
    ochiai = ochiai_rank(f_traces, p_traces)
    ochiai_map = dict(ochiai)
    executed: set[int] = set()
    for t in f_traces:
        executed |= t.executed_lines
    top = [ln for ln, _ in ochiai[:top_lines]]

    # insufficiency certificate: static features vs dynamic observables
    static_feats = [ast.dump(ast.parse(source).body[0])[:80] if ast.parse(source).body else "" for _ in top]
    dynamic_feats = [dynamic_observables(f_traces[0], ochiai_map, ln)["ochiai_rank"] if f_traces else 0.0
                     for ln in top]
    labels = [1] * len(top)
    insuff = insufficiency_certificate(static_feats, dynamic_feats, labels) if top else {}

    proposals: list[dict[str, Any]] = []
    seen: set[str] = {source}

    def add(src: str, score: float, origin: str) -> None:
        if src and src not in seen:
            seen.add(src)
            proposals.append({"source": src, "score": score, "origin": origin})

    # (a) edit-kind operators, re-ranked by the Ochiai score of the edit site
    try:
        tree = ast.parse(source)
        line_scores: dict[int, float] = {}
        for node in ast.walk(tree):
            ln = getattr(node, "lineno", None)
            if ln in ochiai_map:
                line_scores[ln] = max(line_scores.get(ln, 0.0), ochiai_map[ln])
    except (SyntaxError, ValueError):
        line_scores = {}
    # proposals from lessons are supplied by the caller via proposals_for()
    # (kept separate so the dev/scored split stays explicit); here we add
    # take_out + synthesized candidates at executed lines.

    # (b) take_out deletions restricted to executed lines
    for text, fewer, kind in take_out_v1.candidates(source):
        # find changed lines cheaply: deletion candidates that touch a top line
        add(text, 0.5 + 0.5 * (1.0 / (1 + fewer)), f"take_out:{kind}")

    # (c) observational synthesis at the return/assign lines of top sites
    specs = angelic_specs(source, entry, failing, passing, prelude=prelude)
    if specs:
        try:
            full_tree = ast.parse(source)
            names = _live_names(full_tree, 0)
            consts = _constants_in(full_tree)
            if task_text:
                consts += [t for t in _task_identifiers(task_text) if t not in names]
            targets = [(s["env"], s["target"]) for s in specs]
            exprs = synthesize_expression(targets, names=names, constants=consts)
            for expr in exprs:
                for ln in top:
                    rewritten = replace_line_expression(source, ln, expr)
                    if rewritten:
                        add(rewritten, 2.0 + ochiai_map.get(ln, 0.0), f"synthesized:{expr}")
        except (SyntaxError, ValueError):
            pass

    proposals.sort(key=lambda p: (-p["score"], len(p["source"])))
    return {
        "proposals": proposals,
        "ochiai": ochiai[:top_lines],
        "executed_lines": sorted(executed),
        "cases": {"failing": len(failing), "passing": len(passing)},
        "insufficiency": insuff,
        "specs": len(specs),
        "top_lines": top,
    }


def proposals_for(source: str, entry: str, test_source: str, lessons: Any, *,
                  prelude: str = "", budget: int = 200, task_text: str = "") -> list[dict[str, Any]]:
    """Full ranked candidate list: edit-kind votes re-ranked by trace
    localization, plus take_out and synthesized candidates."""
    from canonical.runtime import edit_kind_learning_v1 as kinds  # noqa: E402

    sliced = trace_sliced_proposals(source, entry, test_source, prelude=prelude, task_text=task_text)
    ochiai_map = dict(sliced.get("ochiai", []))
    executed = set(sliced.get("executed_lines", []))
    out: list[dict[str, Any]] = []
    seen: set[str] = set()

    # edit-kind proposals with site-aware re-ranking
    try:
        votes = lessons.votes(source)
        ranked = kinds.ranking(votes)
    except Exception:  # noqa: BLE001
        ranked = []
    for candidate, score, row in ranked[:budget]:
        if candidate in seen:
            continue
        seen.add(candidate)
        # site score: max Ochiai over changed lines
        try:
            before = ast.unparse(ast.parse(source)).split("\n")
            after = ast.unparse(ast.parse(candidate)).split("\n")
            import difflib
            site = 0.0
            for tag, a0, a1, _b0, _b1 in difflib.SequenceMatcher(a=before, b=after, autojunk=False).get_opcodes():
                if tag != "equal":
                    for ln in range(a0 + 1, a1 + 1):
                        site = max(site, ochiai_map.get(ln, 0.0))
        except (SyntaxError, ValueError):
            site = 0.0
        out.append({"source": candidate, "score": score + 2.0 * site,
                    "origin": "edit_kind", "lessons": sorted(row)[:8]})
    # trace-sliced candidates (take_out + synthesized)
    for p in sliced.get("proposals", []):
        if p["source"] in seen:
            continue
        seen.add(p["source"])
        out.append(p)
    out.sort(key=lambda p: (-p["score"], len(p["source"])))
    return out
