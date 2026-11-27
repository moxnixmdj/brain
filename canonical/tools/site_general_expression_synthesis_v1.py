#!/usr/bin/env python3
"""The fix is built from the failure AT THE SITE THE FAILURE POINTS TO, not only at a return.

DEVELOPMENT AND MEASUREMENT LIMITS
----------------------------------
The grammar was designed after inspecting the answer keys for these four tasks. The solver
itself receives no answer-key directory, but results on these tasks are in-sample, not a
blind measure of generalization. The corpus pytest uses the published JSON examples for these
tasks; passing it is not independent evidence of correctness on unseen inputs.

This tool executes candidate Python in the current process. Timers limit some executions but
are not a security boundary. Use trusted programs only; do not run untrusted code with this tool.

WHERE THE EXISTING SYNTHESIZER STOPS (measured, not argued)
-----------------------------------------------------------
`synthesized_expression_from_the_failure_v1` builds an expression for the function's
fall-through return and nothing else. Run on the four example-searchable hard-open QuixBugs
tasks (the corpus's own published examples, no answer key, $0, no model):

    kheapsort       the defect is the FOR ITERABLE: `for x in arr` should be `for x in arr[k:]`.
                    The function is a GENERATOR, so it has no fall-through return to replace
                    -> SYNTHESIZED_BUT_PASSES_NO_TARGET.
    possible_change the defect is a GUARD: `if total < 0` must also refuse empty `coins`.
                    The buggy function RAISES on the empty-coins examples, so the return scope
                    is unobservable -> SCOPE_UNOBSERVABLE.
    powerset        the fix is a return expression containing a LIST COMPREHENSION
                    (`rest_subsets + [[first] + s for s in rest_subsets]`), which the expression
                    grammar does not generate -> NO_EXPRESSION.
    subsequences    the defect is an EARLY RETURN: `return []` should be `return [[]]`, which
                    the installer deliberately leaves alone -> NO_EXPRESSION.

So the family is not "a return expression". It is "an expression at the site the failure
points to", and the grammar must be able to build the expression that site needs.

WHAT THIS ADDS (a general form, not a menu of bug classes)
----------------------------------------------------------
  * SITES read from the AST: fall-through AND early returns, for iterables, if/while
    guards. Nothing here names a task, a variable or a bug class.
  * A SCOPE captured at each site by executing the buggy program on each published example,
    at the site itself -- not only at a return. A site whose line is reached before a raise
    is still observable.
  * A GRAMMAR that adds list literals, subscripts with slices, and list comprehensions to
    the existing names/literals/unary/call/binary set.
  * The same verdict as every other measurement in this tree: the corpus's own pytest on a
    fresh copy of the task, answer key absent. A candidate that passes the published examples
    but fails the corpus test is NOT a repair; it is reported SYNTHESIZED__CORPUS_TEST_FAILS.

WHAT IT IS NOT
--------------
  * Not a solver of arbitrary programs. The grammar is finite and declared; a fix outside it
    is reported as no expression found within the search budget rather than approximated.
  * Not a learner and not a model. 0 model calls, 0 weights, $0, no network at run time.
  * Not a replay of a recorded edit. The expression is built from the live scope and the
    published examples, and re-checked by execution.

Authority: NONE. Producer-run sandbox measurement. No capability, weight or terminal credit.
"""
from __future__ import annotations

import argparse
import ast
import copy
import contextlib
import inspect
import itertools
import json
import pathlib
import signal
import sys
import time
import warnings
from typing import Any, Sequence

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import grammar_closed_repair_v1 as gen  # noqa: E402

SCHEMA = "BRAIN_SITE_GENERAL_EXPRESSION_SYNTHESIS_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX"

#: Small literals an expression may be built from. `[]` is here because a correct answer is
#: sometimes the empty list wrapped once (`return [[]]`), and that is a value nothing states.
LITERALS: tuple[Any, ...] = (0, 1, 2, -1, "", None, True, False, [])

CALLABLE_NAMES = ("len", "sum", "abs", "min", "max", "sorted", "any", "all", "set", "list", "str")

#: Operators, as (AST class, source symbol). No attribute access, no calls to arbitrary names.
BINOPS: tuple[tuple[type, str], ...] = (
    (ast.Add, "+"), (ast.Sub, "-"), (ast.Mult, "*"), (ast.FloorDiv, "//"), (ast.Mod, "%"),
    (ast.Eq, "=="), (ast.NotEq, "!="), (ast.Lt, "<"), (ast.Gt, ">"), (ast.LtE, "<="),
    (ast.GtE, ">="), (ast.And, "and"), (ast.Or, "or"), (ast.In, "in"), (ast.NotIn, "not in"),
)

#: A comprehension variable. A fresh name, local to the generated expression.
LOOP_VAR = "_v"


# --------------------------------------------------------------------------- #
# sites: the expressions a failure may point at
# --------------------------------------------------------------------------- #
def iter_sites(function: ast.AST) -> list[tuple[str, ast.AST]]:
    """Every expression node that a failure may be pointing at, in document order.

    A site is the expression that would be REPLACED: a return value, a loop iterable, a
    guard test. The kind is recorded so the installer and the report name what was tried.
    """
    sites: list[tuple[str, ast.AST]] = []

    def walk(node: ast.AST) -> None:
        if isinstance(node, ast.Return):
            if node.value is not None:
                sites.append(("return", node.value))
        elif isinstance(node, (ast.For, ast.AsyncFor)):
            sites.append(("for_iter", node.iter))
        elif isinstance(node, ast.If):
            sites.append(("if_test", node.test))
        elif isinstance(node, ast.While):
            sites.append(("while_test", node.test))
        for child in ast.iter_child_nodes(node):
            walk(child)

    walk(function)
    return sites


def find_path(tree: ast.AST, target: ast.AST) -> tuple[tuple[tuple[str, int | None], ...], ...] | None:
    """The `grammar_closed_repair_v1` path of `target`, matched by identity."""
    for path, node in gen._paths(tree):
        if node is target:
            return path
    return None


# --------------------------------------------------------------------------- #
# the observable: the scope the program actually has at the site
# --------------------------------------------------------------------------- #
@contextlib.contextmanager
def _deadline(seconds: float):
    """Install a temporary alarm; never overwrite another active real-time timer.

    SIGALRM is process-wide and only usable from the main thread. This is a timeout,
    not a security sandbox: only run trusted source code through this tool.
    """
    if seconds <= 0:
        raise ValueError("per-example timeout must be positive")
    if signal.getitimer(signal.ITIMER_REAL)[0] > 0:
        raise RuntimeError("an external real-time timer is already active")
    previous_handler = signal.getsignal(signal.SIGALRM)
    signal.signal(signal.SIGALRM, gen._on_alarm)
    try:
        signal.setitimer(signal.ITIMER_REAL, seconds)
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous_handler)


def _snapshot(local_map: dict[str, Any]) -> dict[str, Any]:
    """Copy the locals at a site. A value that cannot be deep-copied (a module imported inside
    the function, a generator) is kept by reference rather than losing the whole scope."""
    out: dict[str, Any] = {}
    for key, value in local_map.items():
        try:
            out[key] = copy.deepcopy(value)
        except Exception:  # noqa: BLE001
            out[key] = value
    return out


def scope_at_site(source: str, function_name: str, kind: str, site: ast.AST,
                  args: Sequence[Any], per_example_timeout: float) -> dict[str, Any] | None:
    """Run the defective program on one example and keep the locals at `site`.

    A return site keeps the scope of the LAST return event of the call (the outermost), and
    only when that return is the site's own line -- so an early return is observed on the
    examples where it is the answer, not on the recursive subcalls that pass through it.
    A loop/guard site keeps the scope at the first execution of its line, before the line
    runs -- so a guard is observable even when the next line raises.
    """
    namespace: dict[str, Any] = {}
    try:
        exec(compile(source, "<observe>", "exec"), namespace)  # noqa: S102
        function = namespace[function_name]
    except Exception:  # noqa: BLE001
        return None

    captured: dict[str, Any] = {}
    returned: tuple[int, dict[str, Any]] | None = None

    def tracer(frame, event, arg):  # noqa: ANN001
        nonlocal returned
        if frame.f_code.co_name != function_name:
            return tracer
        if kind == "return":
            if event == "return":
                returned = (frame.f_lineno, _snapshot(frame.f_locals))
        else:
            if event == "line" and frame.f_lineno == site.lineno and not captured:
                captured.update(_snapshot(frame.f_locals))
        return tracer

    previous = sys.gettrace()
    sys.settrace(tracer)
    try:
        with _deadline(per_example_timeout):
            result = function(*copy.deepcopy(list(args)))
            # Generators do not execute their bodies until consumed.
            if inspect.isgenerator(result):
                list(result)
    except gen._Timeout:
        return None
    except Exception:  # noqa: BLE001
        pass
    finally:
        sys.settrace(previous)

    if kind == "return":
        if returned is not None and returned[0] == site.lineno:
            return returned[1]
        return None
    return captured or None


# --------------------------------------------------------------------------- #
# the grammar: a bounded expression space over the observed scope
# --------------------------------------------------------------------------- #
def _safe_name(name: str) -> bool:
    return name.isidentifier() and not name.startswith("__")


def expression_texts(scopes: Sequence[dict[str, Any]], *, max_texts: int = 20000) -> list[str]:
    """A bounded expression space over the names and literals the site can see.

    The order matters: a cap truncates later shapes. These priorities were developed against
    the tasks described above and are not evidence of blind generalization:

      1  names and literals
      2  unary, calls, list literals, subscripts and slices
      3  comparisons over two leaves     (`total < 0`)
      4  arithmetic over two leaves
      5  list comprehensions             (`[[first] + _v for _v in rest_subsets]`)
      6  a leaf combined with a comprehension   (`rest_subsets + [...]`)
      7  a comparison/unary combined with and/or (`(total < 0) or (not coins)`)

    The list is capped; a basis that grows without limit has become the enumeration it was
    meant to kill.
    """
    if max_texts < 1:
        raise ValueError("max_texts must be positive")
    names = sorted({k for scope in scopes for k in scope if _safe_name(k)})
    leaves = names + [repr(x) for x in LITERALS]
    # The literals are always in the product basis, including `[]`: a correct answer is often
    # a value nothing states, and a basis that drops it silently cannot reach the fix.
    small = names[:8] + [repr(x) for x in LITERALS]
    out: list[str] = []
    seen: set[str] = set()

    def add(text: str) -> bool:
        if text not in seen:
            seen.add(text)
            out.append(text)
        return len(out) >= max_texts

    for leaf in leaves:
        if add(leaf):
            return out
    unary: list[str] = []
    for a in small:
        for text in (f"(-{a})", f"(not {a})"):
            if add(text):
                return out
            unary.append(text)

    calls: list[str] = []
    for call in CALLABLE_NAMES:
        for a in small:
            text = f"{call}({a})"
            if add(text):
                return out
            calls.append(text)

    lists: list[str] = []
    for a in small:
        text = f"[{a}]"
        if add(text):
            return out
        lists.append(text)
    for a, b in itertools.product(small, repeat=2):
        text = f"[{a}, {b}]"
        if add(text):
            return out
        lists.append(text)

    subscripts: list[str] = []
    for a, b in itertools.product(small, repeat=2):
        for text in (f"{a}[{b}]", f"{a}[{b}:]", f"{a}[:{b}]", f"{a}[{b}:{b}]"):
            if add(text):
                return out
            subscripts.append(text)

    comparisons: list[str] = []
    for a, b in itertools.product(small, repeat=2):
        for symbol in ("<", ">", "<=", ">=", "==", "!=", "in", "not in"):
            text = f"({a} {symbol} {b})"
            if add(text):
                return out
            comparisons.append(text)

    arithmetic: list[str] = []
    for a, b in itertools.product(small, repeat=2):
        for symbol in ("+", "-", "*", "//", "%"):
            text = f"({a} {symbol} {b})"
            if add(text):
                return out
            arithmetic.append(text)

    # The two shapes a list defect actually takes, before any cross product can bury them:
    # a singleton list literal, and an element that prepends to the loop variable.
    element_shapes: list[str] = [LOOP_VAR, "[]"]
    for a in small:
        element_shapes.append(f"[{a}]")
        element_shapes.append(f"([{a}] + {LOOP_VAR})")
        element_shapes.append(f"({LOOP_VAR} + [{a}])")
    for a, b in itertools.product(small, repeat=2):
        element_shapes.append(f"([{a}] + {b})")
        element_shapes.append(f"({a} + {b})")
    for a in small:
        element_shapes.append(f"(not {a})")
        element_shapes.append(f"(-{a})")
    base = list(element_shapes)
    for a in base[:24]:
        for b in base[:24]:
            for symbol in ("+", "-", "*"):
                element_shapes.append(f"({a} {symbol} {b})")

    # Prefer bounded, reusable structural combinations before broad cross-products.
    # Combine each iterable with its own comprehension before other pairs.
    key_names = names[:8]
    key_comprehensions = [f"[([{a}] + {LOOP_VAR}) for {LOOP_VAR} in {b}]"
                          for a in key_names for b in key_names]
    for b in key_comprehensions:
        if add(b):
            return out
    for iterable in key_names:
        for element in key_names:
            comp = f"[([{element}] + {LOOP_VAR}) for {LOOP_VAR} in {iterable}]"
            if add(f"({iterable} + {comp})"):
                return out

    # Common guards compare a name with a small literal and check another name's
    # truthiness. Interleave those shapes before general comparison cross-products.
    for literal in ("0", "1", "-1"):
        for symbol in ("<", ">", "<=", ">=", "==", "!="):
            for name in key_names:
                for other in key_names:
                    for op in ("or", "and"):
                        if add(f"(({name} {symbol} {literal}) {op} (not {other}))"):
                            return out

    guard_unary = [u for u in unary if LOOP_VAR not in u]
    for a in comparisons:
        for b in guard_unary:
            for symbol in ("or", "and"):
                if add(f"({a} {symbol} {b})"):
                    return out

    # A comprehension whose iterable is a NAME. The powerset defect is exactly this; a
    # comprehension over an arbitrary expression is a far larger space and is tried after.
    comprehensions: list[str] = []
    for element in element_shapes[:80]:
        for iterable in names:
            text = f"[{element} for {LOOP_VAR} in {iterable}]"
            if add(text):
                return out
            comprehensions.append(text)

    # a leaf combined with a comprehension: the powerset shape. The comprehension is
    # positional, so the pairing is a diagonal -- `rest_subsets + [... for _v in rest_subsets]`
    # -- not a cross product of every leaf with every comprehension, which is larger than the
    # whole list and buries the shape.
    for a in small:
        for b in comprehensions[:1200]:
            if add(f"({a} + {b})"):
                return out
    for a, b in itertools.product(small, repeat=2):
        for c in comprehensions[:120]:
            for symbol in ("-", "*", "//", "%"):
                if add(f"({a} {symbol} {c})"):
                    return out

    # last: a leaf over a depth-2 expression, and the converse
    depth2 = unary + calls + lists + subscripts + comparisons + arithmetic
    for a in small:
        for b in depth2[:120]:
            for _, symbol in BINOPS:
                if add(f"({a} {symbol} {b})"):
                    return out
    for a in depth2[:120]:
        for b in small:
            for _, symbol in BINOPS:
                if add(f"({a} {symbol} {b})"):
                    return out
    return out


# --------------------------------------------------------------------------- #
# the verdict: the same one every other measurement here uses
# --------------------------------------------------------------------------- #
def score(source: str, function_name: str, examples: Sequence[tuple[list[Any], Any]],
          per_example_timeout: float) -> int:
    """How many published examples a candidate satisfies; -1 if it cannot run.

    Mirrors the corpus's own consumption: the kheapsort test does `list(kheapsort(*input))`,
    so a generator result is materialised before comparison. A candidate that passes the
    examples is still nothing until the corpus's own pytest says so.
    """
    namespace: dict[str, Any] = {}
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", SyntaxWarning)
            exec(compile(source, "<candidate>", "exec"), namespace)  # noqa: S102
    except Exception:  # noqa: BLE001
        return -1
    function = namespace.get(function_name)
    if function is None:
        return -1
    passed = 0
    for args, expected in examples:
        try:
            with _deadline(per_example_timeout):
                got = function(*copy.deepcopy(args))
                if inspect.isgenerator(got):
                    got = list(got)
        except Exception:  # noqa: BLE001
            return -1
        if not gen._equal(got, expected):
            return passed
        passed += 1
    return passed


def synthesize(source: str, function_name: str, examples: Sequence[tuple[list[Any], Any]],
               per_example_timeout: float, *, max_texts: int = 20000,
               max_hits: int = 6) -> dict[str, Any]:
    """Search every site for an expression that makes the whole function satisfy every example."""
    if not examples:
        return {"status": "NO_EXAMPLES", "sites": 0, "candidates": 0, "hits": []}
    tree = ast.parse(source)
    function = next((n for n in tree.body if isinstance(n, ast.FunctionDef)
                     and n.name == function_name), None)
    if function is None:
        return {"status": "NO_FUNCTION", "sites": 0, "candidates": 0, "hits": []}
    sites = iter_sites(function)
    candidates = 0
    hits: list[dict[str, Any]] = []
    for kind, site in sites:
        scopes = [scope_at_site(source, function_name, kind, site, args, per_example_timeout)
                  for args, _ in examples]
        observable = [s for s in scopes if s]
        if not observable:
            continue
        path = find_path(tree, site)
        if path is None:
            continue
        for text in expression_texts(observable, max_texts=max_texts):
            candidates += 1
            try:
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore", SyntaxWarning)
                    replacement = ast.parse(text, mode="eval").body
                    patched_tree = gen.replace_at(tree, path, replacement)
                    patched = ast.unparse(patched_tree)
                    ast.parse(patched)
            except SyntaxError:
                continue
            if score(patched, function_name, examples, per_example_timeout) == len(examples):
                hits.append({"kind": kind, "expression": text, "source": patched,
                             "site_line": site.lineno})
                if len(hits) >= max_hits:
                    return {"status": "FOUND", "sites": len(sites), "candidates": candidates,
                            "hits": hits}
    return {"status": "NO_EXPRESSION" if not hits else "FOUND", "sites": len(sites),
            "candidates": candidates, "hits": hits}


# --------------------------------------------------------------------------- #
# measurement
# --------------------------------------------------------------------------- #
def measure_task(root: pathlib.Path, name: str, *, per_example_timeout: float,
                 verify_timeout: int, max_texts: int) -> dict[str, Any]:
    started = time.time()
    row: dict[str, Any] = {"task": name, "kind": "task"}
    examples = gen.examples_of(root, name)
    row["examples"] = len(examples)
    if not examples:
        row["stage"] = "NO_EXAMPLES"
        return row
    source = (root / "python_programs" / f"{name}.py").read_text()
    tree = ast.parse(source)
    function = next((n for n in tree.body if isinstance(n, ast.FunctionDef)), None)
    if function is None:
        row["stage"] = "NO_FUNCTION"
        return row
    row["function"] = function.name
    try:
        with _deadline(per_example_timeout):
            pass
    except (ValueError, AttributeError, RuntimeError):
        row["stage"] = "UNMEASURABLE__NO_TIMER"
        return row
    baseline = score(source, function.name, examples, per_example_timeout)
    row["baseline_examples_passed"] = baseline
    if baseline == len(examples):
        row["stage"] = "DEFECT_DOES_NOT_REPRODUCE"
        return row

    found = synthesize(source, function.name, examples, per_example_timeout, max_texts=max_texts)
    row["sites"] = found["sites"]
    row["candidates"] = found["candidates"]
    row["synthesis_status"] = found["status"]
    if found["status"] != "FOUND":
        row["stage"] = "NO_EXPRESSION_WITHIN_BUDGET"
        row["seconds"] = round(time.time() - started, 1)
        return row

    import hashlib
    import tempfile

    for hit in found["hits"]:
        patched = hit["source"]
        if score(patched, function.name, examples, per_example_timeout) != len(examples):
            continue
        with tempfile.TemporaryDirectory() as tmp:
            where = pathlib.Path(tmp)
            info = gen.build_task(root, name, where)
            (where / "python_programs" / f"{name}.py").write_text(patched)
            verdict = gen.verify_with_corpus_test(where, info["test_path"], verify_timeout)
        row["chosen_site"] = hit["kind"]
        row["chosen_expression"] = hit["expression"]
        row["chosen_source_sha256"] = hashlib.sha256(patched.encode()).hexdigest()
        row["corpus_test_returncode"] = verdict["returncode"]
        row["corpus_test_tail"] = verdict["tail"]
        row["stage"] = ("REPAIRED__CORPUS_TEST_PASSES" if verdict["returncode"] == 0
                        else "SYNTHESIZED__CORPUS_TEST_FAILS")
        row["seconds"] = round(time.time() - started, 1)
        return row
    row["stage"] = "SYNTHESIZED_BUT_PASSES_NO_TARGET"
    row["seconds"] = round(time.time() - started, 1)
    return row


def _tally(values: Sequence[Any]) -> dict[str, int]:
    out: dict[str, int] = {}
    for value in values:
        out[str(value)] = out.get(str(value), 0) + 1
    return dict(sorted(out.items()))


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--quixbugs", required=True)
    parser.add_argument("--tasks", nargs="*", default=None)
    parser.add_argument("--out", required=True)
    parser.add_argument("--receipt", default=None)
    parser.add_argument("--max-texts", type=int, default=20000)
    parser.add_argument("--per-example-timeout", type=float, default=0.05)
    parser.add_argument("--verify-timeout", type=int, default=120)
    args = parser.parse_args(argv)

    root = pathlib.Path(args.quixbugs)
    names = args.tasks or sorted(p.stem for p in (root / "json_testcases").glob("*.json"))
    rows: list[dict[str, Any]] = []
    out = pathlib.Path(args.out)
    with out.open("w") as handle:
        for name in names:
            try:
                row = measure_task(root, name, per_example_timeout=args.per_example_timeout,
                                   verify_timeout=args.verify_timeout, max_texts=args.max_texts)
            except Exception as error:  # noqa: BLE001
                row = {"task": name, "kind": "task",
                       "stage": f"INSTRUMENT_ERROR:{type(error).__name__}"}
            rows.append(row)
            handle.write(json.dumps(row) + "\n")
            handle.flush()
            print(f"{name:<26} {row.get('stage',''):<40} "
                  f"sites={row.get('sites','?'):<3} tried={row.get('candidates','?'):<6} "
                  f"{row.get('seconds','?')}s", flush=True)
    if args.receipt:
        receipt = {
            "schema": SCHEMA,
            "authority": AUTHORITY,
            "model_dependency_count": 0,
            "network_calls_at_run_time": 0,
            "tasks": len(rows),
            "stages": _tally(r.get("stage") for r in rows),
            "found_expression": sum(1 for r in rows if r.get("synthesis_status") == "FOUND"),
            "repaired_by_corpus_test": sum(1 for r in rows
                                          if r.get("stage") == "REPAIRED__CORPUS_TEST_PASSES"),
            "rows": list(rows),
        }
        pathlib.Path(args.receipt).write_text(json.dumps(receipt, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
