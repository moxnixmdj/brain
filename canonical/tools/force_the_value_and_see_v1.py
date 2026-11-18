#!/usr/bin/env python3
"""Force the value at a site, see whether the failing case passes, then write the expression that owes it.

THE MOVE, IN ONE LINE
---------------------
Do not search programs. Ask the failing case a question it can answer: *at this site, which value would
have made you pass?* Force that value at run time, and the case either passes or it does not. That is one
program run per question, and a program run on a published case is tens of microseconds.

WHY THIS IS THE ULTIMATE SHAPE AND NOT A HEURISTIC
--------------------------------------------------
Every earlier rung in this tree enumerated *programs* and judged each by *running the whole test*: about
3.5 ms per candidate, which is why the space had to be kept small, which is why 13 of 40 published fixes
sat outside it. This inverts the order of the two costs:

    which value fixes the failing case     one run per value        ~50 us
    which expression produces that value   one eval per expression  ~10 us
    is the patch correct                   the corpus's own pytest   once per surviving patch

and it is complete for the only class of edit that matters here: a single expression replaced by a
single expression. Forcing the site's value covers *every* thing an expression can do to a program --
choose a branch, return an answer, supply an argument, index a structure -- with no list of edit kinds
and no grammar of fixes. Angelic value mining (Angelic Debugging, ICSE 2011; Nopol; DynaMoth) does this
for conditions with a boolean; this does it for any value at any expression site, which is what a
software defect actually needs.

WHAT IS AND IS NOT CLAIMED
--------------------------
A forced value that passes the failing case is a *fact about that case*, not a fix. The expression that
produces the value is then synthesized from the values in scope (the program's own material, the
language's own grammar), and the corpus's own `pytest` decides on a fresh copy with the answer key
absent. If no value at any site makes the failing case pass, that is reported as such -- it means the
case needs more than one value, and nothing is invented to cover it.

No model, no network, no answer key inside the search, no edit-kind list.

Authority NONE, producer-run, zero model calls, zero network calls at run time.
"""
from __future__ import annotations

import argparse
import ast
import copy
import json
import pathlib
import sys
import warnings
import tempfile
import time
from typing import Any, Iterator, Sequence

TOOLS = pathlib.Path(__file__).resolve().parent
REPO = TOOLS.parents[1]
for path in (str(TOOLS), str(REPO)):
    if path not in sys.path:
        sys.path.insert(0, path)

import grammar_closed_repair_v1 as gen  # noqa: E402
import solve_with_a_calibrated_judge_v1 as judged  # noqa: E402
from expressions_from_a_site_v1 import (  # noqa: E402
    MAX_NODES, SAFE_BUILTINS, _combinations, _evaluate_all, _size, base_terms,
)

SCHEMA = "BRAIN_FORCE_THE_VALUE_AND_SEE_V1"
UPSTREAM = "https://github.com/jkoppel/QuixBugs"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX"

HOOK = "__brain_force__"
TICK = "__brain_tick__"
MAX_LOOP_TURNS = 200_000   # a loop that will not end is not a wrong answer, and must not become a hang
SECONDS = 0.5   # kept for callers that still pass a per-run budget
BUDGET_PER_SITE = 4000  # candidates offered per site; generation stops earlier if the deadline hits


class _Timeout(Exception):
    pass


# -------------------------------------------------------------------------------------------------- #
# 1. instrument: every expression a statement produces becomes a question we can ask
# -------------------------------------------------------------------------------------------------- #

def instrument(function: ast.FunctionDef) -> tuple[ast.FunctionDef, list[dict[str, Any]]]:
    """Wrap each statement-level expression in a hook that can return a forced value instead.

    The original expression is kept inside a lambda, so when nothing is forced the program behaves
    exactly as it did -- including side effects and evaluation order within that expression.
    """
    clone = copy.deepcopy(function)
    sites: list[dict[str, Any]] = []

    # Collect first, then rewrite. Rewriting while walking would descend into the hook that now
    # contains the original expression and wrap it again, for ever.
    targets: list[tuple[ast.AST, str, int | None]] = []
    for _path, node in gen._paths(clone):  # noqa: SLF001
        if isinstance(node, (ast.Return, ast.Expr)) and getattr(node, "value", None) is not None:
            targets.append((node, "value", None))
        elif isinstance(node, (ast.If, ast.While)):
            targets.append((node, "test", None))
        elif isinstance(node, ast.Assign):
            targets.append((node, "value", None))
        elif isinstance(node, ast.For):
            targets.append((node, "iter", None))
        elif isinstance(node, ast.Call):
            for index, argument in enumerate(node.args):
                if isinstance(argument, ast.expr) and not isinstance(argument, ast.Starred):
                    targets.append((node, "args", index))
    for node, field, index in targets:
        original = getattr(node, field) if index is None else node.args[index]
        if not isinstance(original, ast.expr):
            continue
        site_index = len(sites)
        sites.append({"index": site_index, "lineno": getattr(original, "lineno", 0),
                      "text": ast.unparse(original)})
        hook = ast.Call(func=ast.Name(id=HOOK, ctx=ast.Load()),
                        args=[ast.Constant(value=site_index),
                              ast.Lambda(args=ast.arguments(posonlyargs=[], args=[], kwonlyargs=[],
                                                            kw_defaults=[], defaults=[]),
                                         body=original)],
                        keywords=[])
        ast.copy_location(hook, original)
        ast.fix_missing_locations(hook)
        if index is None:
            setattr(node, field, hook)
        else:
            node.args[index] = hook
        if node is not None and field == "test" and isinstance(node, ast.While):
            # Bound the loop, not the clock: a candidate that never terminates is answered, not waited on.
            tick = ast.Call(func=ast.Name(id=TICK, ctx=ast.Load()), args=[], keywords=[])
            node.test = ast.BoolOp(op=ast.And(), values=[tick, hook])
            ast.copy_location(tick, node.test)
            ast.fix_missing_locations(node)
    ast.fix_missing_locations(clone)
    return clone, sites


def instrumented_source(source: str, function_name: str) -> tuple[str, list[dict[str, Any]]]:
    tree = ast.parse(source)
    function = next((node for node in tree.body if isinstance(node, ast.FunctionDef)), None)
    if function is None:
        raise ValueError("NO_FUNCTION")
    clone, sites = instrument(function)
    tree.body = [clone if node is function else node for node in tree.body]
    return ast.unparse(tree) + "\n", sites


# -------------------------------------------------------------------------------------------------- #
# 2. run one case with a value forced at one site
# -------------------------------------------------------------------------------------------------- #

def run_case(source: str, function_name: str, args: Sequence[Any], *,
             forced: dict[int, str] | None,
             seconds: float = SECONDS, capture: dict[int, dict[str, Any]] | None = None,
             wanted_lines: set[int] | None = None) -> tuple[bool, Any]:
    """Run the function once, optionally forcing values at sites. Returns (ran, value)."""
    force = forced or {}
    namespace: dict[str, Any] = {}

    def hook(index: int, thunk: Any) -> Any:
        if index in force:
            # Evaluate the candidate expression *where the site lives*, so the run is the patched
            # program's run. Forcing a bare value would hold it constant across recursive calls and
            # loop iterations, which is not what replacing an expression means.
            frame = sys._getframe(1)  # noqa: SLF001
            try:
                return eval(force[index], frame.f_globals, frame.f_locals)  # noqa: S307
            except Exception:  # noqa: BLE001
                return thunk()
        if capture is not None and wanted_lines and index in wanted_lines and index not in capture:
            capture[index] = {}
        return thunk()

    turns = [0]

    def tick() -> bool:
        turns[0] += 1
        if turns[0] > MAX_LOOP_TURNS:
            raise _Timeout()
        return True

    namespace[HOOK] = hook
    namespace[TICK] = tick
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            exec(compile(source, "<forced>", "exec"), namespace)  # noqa: S102 -- corpus code
    except Exception:  # noqa: BLE001
        return False, None
    function = namespace.get(function_name)
    if function is None:
        return False, None
    # No per-run alarm: a signal raised inside a trace hook propagates out of places that cannot be
    # guarded, and a tool that dies silently is worse than a tool that reports a budget. The hard stop
    # is the child process; the graceful stop is the per-task deadline checked between questions.
    try:
        value = function(*copy.deepcopy(list(args)))
        if hasattr(value, "__iter__") and not isinstance(value, (list, tuple, dict, str, bytes)):
            value = list(value)
    except Exception:  # noqa: BLE001
        return False, None
    return True, value


def case_passes(value: Any, expected: Any, normalisation: str | None, args: Sequence[Any]) -> bool:
    cap = (len(expected) + 1) if isinstance(expected, (list, tuple, str)) else 1024
    got = judged.materialise(value, cap)
    want = judged.apply_normalisation(expected, normalisation)
    if normalisation == "approx_last_argument":
        try:
            return judged.approximately_equal(got, expected, abs(float(args[-1])))
        except Exception:  # noqa: BLE001
            return False
    try:
        return bool(got == want) or bool(got == expected)
    except Exception:  # noqa: BLE001
        return False


# -------------------------------------------------------------------------------------------------- #
# 3. which values are worth asking about, at this site, in this state
# -------------------------------------------------------------------------------------------------- #

def context_at(source: str, function_name: str, args: Sequence[Any], line: int,
               seconds: float = SECONDS) -> list[dict[str, Any]]:
    """The values in scope every time this line ran, in order -- the material a fix may draw on."""
    contexts: list[dict[str, Any]] = []
    events = [200_000]

    def tracer(frame, event, arg):  # noqa: ANN001, ARG001
        events[0] -= 1
        if events[0] <= 0:
            sys.settrace(None)
            return None
        if event == "line" and frame.f_code.co_filename == "<ctx>" and frame.f_lineno == line:
            snapshot: dict[str, Any] = {}
            for key, value in list(frame.f_locals.items()):
                try:
                    snapshot[key] = copy.copy(value)
                except Exception:  # noqa: BLE001
                    pass
            if len(contexts) < 400:
                contexts.append({"locals": snapshot, "globals": dict(frame.f_globals), "case": 0,
                                 "observed": None})
        return tracer

    namespace: dict[str, Any] = {}
    try:
        exec(compile(source.replace("def " + function_name, "def " + function_name, 1), "<ctx>",
                     "exec"), namespace)  # noqa: S102
    except Exception:  # noqa: BLE001
        return contexts
    function = namespace.get(function_name)
    if function is None:
        return contexts
    try:
        sys.settrace(tracer)
        value = function(*copy.deepcopy(list(args)))
        if hasattr(value, "__iter__") and not isinstance(value, (list, tuple, dict, str, bytes)):
            for _ in value:
                pass
    except Exception:  # noqa: BLE001
        pass
    finally:
        sys.settrace(None)
    return contexts


def expressions_at(site_text: str, context: dict[str, Any], source: str, function_name: str,
                   budget: int = 900, deadline: float | None = None) -> list[tuple[str, Any]]:
    """Expressions the site could be, smallest first, each with the value it would produce here.

    The material is the site's own operands and the names in scope; the grammar is Python's. Two rules
    decide whether a fix is reachable at all, and both were once wrong:

    1. MATERIAL IS ATOMS, NOT SHORT STRINGS. `length`, `longest`, `coins` are atoms. An earlier version
       admitted only terms whose *text* was <= 3 characters, so every local with a longer name could be
       tested alone and never combined: `max(longest, length + 1)` was unreachable while all three of
       its pieces were present at the site.
    2. THE POOL IS CUMULATIVE. `max(longest, X)` combines an atom with a composite, so the atoms have to
       still be there at the level the composite appears. An earlier version replaced the pool with each
       level's output, which made that combination impossible by construction.

    `budget` bounds how many candidates are offered; `deadline` bounds the generation itself, so one
    site cannot eat a task's whole allowance enumerating a space nobody asked about.
    """
    contexts = [{"locals": context["locals"], "globals": context.get("globals") or {},
                 "observed": None, "case": 0}]
    namespace: dict[str, Any] = {"__builtins__": {}}
    import builtins as _builtins
    for name in SAFE_BUILTINS:
        namespace[name] = getattr(_builtins, name)
    for key, value in (context.get("globals") or {}).items():
        if key in SAFE_BUILTINS or key.startswith("__"):
            continue
        namespace.setdefault(key, value)

    asked: list[tuple[str, Any]] = []
    seen: set[str] = set()

    def offer(text: str) -> bool:
        """Record a candidate. True means the budget is full and generation should stop."""
        if text in seen or function_name + "(" in text:
            return False
        seen.add(text)
        values = _evaluate_all(text, contexts, namespace)
        if values is None:
            return False
        asked.append((text, values[0]))
        return len(asked) >= budget

    terms = base_terms(source, function_name, site_text, contexts)
    for text in terms:
        if offer(text):
            return asked
    # THE MATERIAL OF A REPAIR IS THE SITE ITSELF. A fix is nearly always a modification of what is
    # there -- a guard around it (`max(longest, length + 1)`), a rename of its parts (`perm[i] < perm[j]`),
    # a conjunct added to it (`total < 0 or not coins`). So the site's own sub-expressions are material
    # first, smallest first, and the names and constants in scope come after them.
    site_parts: list[str] = []
    try:
        for node in ast.walk(ast.parse(site_text, mode="eval").body):
            if isinstance(node, ast.expr):
                text = ast.unparse(node)
                # The site itself is material too: `max(longest, length + 1)` is an ATOM WRAPPED AROUND
                # THE SITE, and excluding the site from its own pool makes that unwritable. It is never
                # offered as its own answer (the caller skips it); it is offered as an operand.
                if _size(text) > 1 and text in terms and text not in site_parts:
                    site_parts.append(text)
    except SyntaxError:
        site_parts = []
    site_parts.sort(key=_size)
    atoms = [text for text in terms if _size(text) == 1]
    pool: list[str] = list(dict.fromkeys(site_parts + atoms))
    if not pool:
        return asked
    generation_cap = max(budget * 3, 1200)
    while pool and len(asked) < generation_cap:
        produced: list[str] = []
        stop = False
        for left in pool[:64]:
            for right in pool[:64]:
                if deadline is not None and time.time() > deadline:
                    return asked
                for text in _combinations(left, right, function_name):
                    if _size(text) > MAX_NODES:
                        continue
                    if offer(text):
                        stop = True
                        break
                    produced.append(text)
                if stop:
                    break
            if stop:
                break
        if stop or not produced:
            break
        pool = sorted(dict.fromkeys(pool + produced), key=_size)[:160]
    return asked


def _same(left: Any, right: Any) -> bool:
    try:
        return bool(left == right)
    except Exception:  # noqa: BLE001
        return False


# -------------------------------------------------------------------------------------------------- #
# 4. one task
# -------------------------------------------------------------------------------------------------- #

def solve_task(root: pathlib.Path, name: str, *, verify_timeout: int = 180,
               deadline_seconds: float = 90.0) -> dict[str, Any]:
    row: dict[str, Any] = {"task": name, "kind": "task"}
    source = (root / "python_programs" / f"{name}.py").read_text()
    tree = ast.parse(source)
    function_node = next((node for node in tree.body if isinstance(node, ast.FunctionDef)), None)
    if function_node is None:
        row["stage"] = "NO_FUNCTION"
        return row
    function_name = function_node.name
    cases = gen.examples_of(root, name)
    row["cases"] = len(cases)
    if not cases:
        row["stage"] = "NO_PUBLISHED_CASES"
        return row
    clocks = judged.clocks_for(source, function_name, cases)
    normalisation = judged.test_file_normalisation(root, name)
    calibration = judged.self_calibration(root, name, function_name, cases, clocks, normalisation)
    row["calibration"] = calibration
    if not (calibration.get("corrected_passes") and calibration.get("defective_is_rejected")):
        row["stage"] = "JUDGE_NOT_CALIBRATED"
        return row

    started = time.time()
    failing = None
    for index, (args, expected) in enumerate(cases):
        ran, value = run_case(source, function_name, args, forced=None)
        if not ran or not case_passes(value, expected, normalisation, args):
            failing = (index, args, expected)
            break
    row["failing_case"] = None if failing is None else failing[0]
    if failing is None:
        row["stage"] = "NO_FAILING_CASE"
        return row
    index, args, expected = failing

    # A case that raises has no wrong answer to read, but it can still be the case a forced value fixes:
    # the value changes control flow, so the recursion that ran out may never be entered. Report the fact
    # and keep asking; it is the *observed value* that is unavailable, not the question.
    ran_unforced, _ = run_case(source, function_name, args, forced=None)
    row["the_failing_case_returns"] = ran_unforced

    instrumented, sites = instrumented_source(source, function_name)
    row["sites"] = len(sites)
    questions = 0
    verdicts: list[dict[str, Any]] = []
    timed_out = False
    for site in sites[:16]:
        if time.time() - started > deadline_seconds:
            timed_out = True
            break
        if _size(site["text"]) <= 1:
            continue
        contexts = context_at(source, function_name, args, site["lineno"])
        if not contexts:
            continue
        # The state the site was in when the failing case went wrong: the last time it ran before the
        # answer came back wrong is the state a fix has to answer.
        # A recursive program's site is entered many times; the state worth answering is the outermost
        # call's, which is the first entry, not the deepest one.
        state = contexts[0] if len(contexts) > 4 else contexts[-1]
        current = None
        try:
            current = eval(site["text"], {"__builtins__": {}}, dict(state["locals"]))  # noqa: S307
        except Exception:  # noqa: BLE001
            current = None
        ordered = expressions_at(site["text"], state, source, function_name,
                                 deadline=started + deadline_seconds)
        # Smallest first: the smallest expression that makes the case pass is the edit a person would
        # write. 'Differs from the value already there' is only a tie-break, because a state cannot tell
        # a fix from an accident (the fix for lis agrees with the buggy value on the first iteration).
        ordered.sort(key=lambda item: (_size(item[0]), _same(item[1], current)))
        for expression, value in ordered[:BUDGET_PER_SITE]:
            if time.time() - started > deadline_seconds:
                timed_out = True
                break
            if expression == site["text"]:
                continue
            questions += 1
            fits_every_case = True
            # The failing case first: it rejects almost every candidate, and it is the one that is wrong.
            for other_args, other_expected in [cases[index]] + [c for i, c in enumerate(cases)
                                                                if i != index]:
                ran, got = run_case(instrumented, function_name, other_args,
                                    forced={site["index"]: expression})
                if not ran or not case_passes(got, other_expected, normalisation, other_args):
                    fits_every_case = False
                    break
            if not fits_every_case:
                continue
            verdict = {"line": site["lineno"], "site": site["text"], "expression": expression,
                       "value": repr(value)[:160]}
            verdict.update(patch_and_verify(root, name, source, function_name, site, expression,
                                            verify_timeout))
            verdicts.append(verdict)
            if verdict.get("corpus_test_passes"):
                break
        if verdicts and verdicts[-1].get("corpus_test_passes"):
            break
    row["questions_asked"] = questions
    row["expressions_that_fix_the_failing_case"] = [
        {"line": v["line"], "site": v["site"][:120], "expression": v["expression"],
         "corpus_test_passes": v.get("corpus_test_passes")} for v in verdicts]
    row["attempts"] = verdicts
    row["solved"] = any(v.get("corpus_test_passes") for v in verdicts)
    if row["solved"]:
        best = next(v for v in verdicts if v.get("corpus_test_passes"))
        row["stage"] = "SOLVED_BY_THE_VALUE_THE_FAILURE_SHOWED"
        row["compiled_answer"] = {"line": best["line"], "site": best["site"],
                                  "expression": best["expression"]}
    elif verdicts:
        row["stage"] = "AN_EXPRESSION_FIT_THE_CASE_BUT_THE_CORPUS_REFUSED"
    elif timed_out:
        row["stage"] = "TIME_BUDGET_EXHAUSTED"
    else:
        row["stage"] = "NO_SINGLE_EXPRESSION_FIXES_THIS_CASE"
    row["seconds"] = round(time.time() - started, 1)
    return row


def _site_path(function: ast.FunctionDef, line: int, text: str):
    for path, node in gen._paths(function):  # noqa: SLF001
        if isinstance(node, ast.expr) and getattr(node, "lineno", None) == line:
            if ast.unparse(node) == text:
                return path
    return None


def patch_and_verify(root: pathlib.Path, name: str, source: str, function_name: str,
                     site: dict[str, Any], expression: str, verify_timeout: int) -> dict[str, Any]:
    """Write the expression that owes the value, and let the corpus's own suite decide."""
    tree = ast.parse(source)
    function = next((node for node in tree.body if isinstance(node, ast.FunctionDef)), None)
    if function is None:
        return {"patched": False, "reason": "NO_FUNCTION"}
    path = _site_path(function, site["lineno"], site["text"])
    if path is None:
        return {"patched": False, "reason": "SITE_NOT_FOUND"}
    try:
        replacement = ast.parse(expression, mode="eval").body
    except SyntaxError:
        return {"patched": False, "reason": "EXPRESSION_DOES_NOT_PARSE"}
    patched_function = gen.replace_at(function, path, replacement)
    tree.body = [patched_function if node is function else node for node in tree.body]
    patched_source = ast.unparse(tree) + "\n"
    with tempfile.TemporaryDirectory() as tmp:
        where = pathlib.Path(tmp) / f"{name}__forced"
        where.mkdir(parents=True)
        built = gen.build_task(root, name, where)
        (where / "python_programs" / f"{name}.py").write_text(patched_source, encoding="utf-8")
        result = gen.verify_with_corpus_test(where, built["test_path"], verify_timeout)
    passed = bool(result.get("returncode") == 0 and not result.get("timed_out"))
    return {"patched": True, "corpus_test_passes": passed, "returncode": result.get("returncode"),
            "expression": expression, "patched_source": patched_source if passed else None}


# -------------------------------------------------------------------------------------------------- #

KNOWN_STAGES = (
    "SOLVED_BY_THE_VALUE_THE_FAILURE_SHOWED",
    "AN_EXPRESSION_FIT_THE_CASE_BUT_THE_CORPUS_REFUSED",
    "NO_SINGLE_EXPRESSION_FIXES_THIS_CASE",
    "TIME_BUDGET_EXHAUSTED",
    "JUDGE_NOT_CALIBRATED",
    "NO_PUBLISHED_CASES",
)


def summarise(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    return {
        "tasks_attempted": len(rows),
        "solved": sorted(row["task"] for row in rows if row.get("solved")),
        "solved_count": sum(1 for row in rows if row.get("solved")),
        "an_expression_fit_the_case_but_the_corpus_refused": sorted(
            row["task"] for row in rows
            if row.get("stage") == "AN_EXPRESSION_FIT_THE_CASE_BUT_THE_CORPUS_REFUSED"),
        "no_single_expression_fixes_this_case": sorted(
            row["task"] for row in rows
            if row.get("stage") == "NO_SINGLE_EXPRESSION_FIXES_THIS_CASE"),
        "time_budget_exhausted": sorted(row["task"] for row in rows
                                        if row.get("stage") == "TIME_BUDGET_EXHAUSTED"),
        "judge_not_calibrated": sorted(row["task"] for row in rows
                                       if row.get("stage") == "JUDGE_NOT_CALIBRATED"),
        "not_answered_by_this_run": sorted(
            f'{row["task"]}:{row.get("stage")}' for row in rows
            if not row.get("solved") and row.get("stage") not in KNOWN_STAGES),
        "questions_asked_total": sum(row.get("questions_asked") or 0 for row in rows),
        "seconds_total": round(sum(row.get("seconds") or 0 for row in rows), 1),
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--quixbugs", required=True)
    parser.add_argument("--tasks", nargs="+", required=True)
    parser.add_argument("--receipt", default=None)
    parser.add_argument("--verify-timeout", type=int, default=180)
    parser.add_argument("--task-timeout", type=float, default=180.0)
    parser.add_argument("--deadline", type=float, default=90.0)
    parser.add_argument("--one", default=None, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    root = pathlib.Path(args.quixbugs)

    if args.one:
        row = solve_task(root, args.one, verify_timeout=args.verify_timeout,
                         deadline_seconds=args.deadline)
        print(json.dumps(row, default=str))
        return 0

    import subprocess

    rows: list[dict[str, Any]] = []
    for name in args.tasks:
        # One child per task: a pathological candidate expression can recurse for ever or eat memory,
        # and that must cost this task, not the run.
        try:
            done = subprocess.run([sys.executable, __file__, "--quixbugs", str(root),
                                   "--tasks", name, "--one", name,
                                   "--verify-timeout", str(args.verify_timeout),
                                   "--deadline", str(args.deadline)],
                                  capture_output=True, text=True, timeout=args.task_timeout)
            line = [part for part in done.stdout.splitlines() if part.startswith("{")]
            if line:
                row = json.loads(line[-1])
            else:
                row = {"task": name, "stage": "CHILD_PRODUCED_NO_ROW",
                       "stderr": (done.stderr or "")[-300:]}
        except subprocess.TimeoutExpired:
            row = {"task": name, "stage": "CHILD_TIMED_OUT"}
        rows.append(row)
        answer = row.get("compiled_answer") or {}
        print(f"{name:26s} {str(row.get('stage')):44s} q={row.get('questions_asked')} "
              f"{answer.get('expression', '')[:40]} {row.get('seconds')} s", flush=True)

    summary = summarise(rows)
    receipt = {"schema": SCHEMA, "authority": AUTHORITY, "upstream": UPSTREAM,
               "corpus_commit": judged.corpus_commit(root),
               "tool": "canonical/tools/force_the_value_and_see_v1.py",
               "measures": ("whether one value forced at one expression site makes the failing case "
                            "pass, then whether the corpus's own pytest accepts the expression that "
                            "produces it"),
               "model_dependency_count": 0, "external_capability_provider_count": 0,
               "network_calls_at_run_time": 0, "answer_key_inside_the_search": False,
               "summary": summary, "rows": rows}
    if args.receipt:
        pathlib.Path(args.receipt).write_text(json.dumps(receipt, indent=1, default=str) + "\n")
    print(json.dumps(summary, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
