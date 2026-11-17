#!/usr/bin/env python3
"""The fix is not chosen from a list. It is built from what the failure leaves behind.

Where every previous repair mechanism in this tree starts from a *vocabulary* -- a hand-written
list of edit families, or a set of shapes induced from demonstrations -- this one starts from the
failure and asks a different question:

    at the point the program computes its answer, what expression over the values it already
    holds would have produced the right answer on every example?

That is synthesis, not rewriting. The space of candidate expressions is not enumerated by anyone;
it is generated bottom-up from the program's own live local scope (the names that are actually in
scope at the return, and small literals), and pruned by observation: an expression survives only if
it evaluates to the expected answer on *every* published example, in the scope the buggy program
itself produces. Nothing here names a bug, a variable, or a fix.

Why this is the honest answer to "give it the smartest actions once and it learns them":

  * an action LIST cannot grow without someone editing it (measured: 0/20 at any budget);
  * an action SHAPE learned from one demonstration fires only where its precondition literally
    holds and transferred to ~1-2 of 20 held-out bugs;
  * an expression built from the failure has no precondition to match -- it is derived from the
    evidence, which is why it can be correct on a program nobody demonstrated.

The cost is equally honest: it only reaches fixes that live in a value the program already computes
at a return. A defect that needs a new statement, a changed recurrence or a different algorithm is
reported NOT_IN_THIS_FAMILY rather than approximated.

Authority: NONE. Producer-run sandbox measurement. No model, no weights, no network at run time.
"""
from __future__ import annotations

import argparse
import ast
import copy
import itertools
import json
import pathlib
import signal
import sys
import time
from typing import Any, Sequence

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import grammar_closed_repair_v1 as gen  # noqa: E402

#: Everything an expression may be built from, in addition to the names already in scope.
LITERALS = (0, 1, 2, -1, "", None, True, False)
CALLABLE_NAMES = ("len", "sum", "abs", "min", "max", "sorted", "any", "all", "set", "list", "str")
BINOPS = (ast.Add, ast.Sub, ast.Mult, ast.FloorDiv, ast.Mod, ast.Eq, ast.NotEq, ast.Lt, ast.Gt,
          ast.LtE, ast.GtE, ast.And, ast.Or, ast.In, ast.NotIn)
UNOPS = (ast.Not, ast.USub)


# --------------------------------------------------------------------------------------------------
# observing the scope the program actually has when it answers
# --------------------------------------------------------------------------------------------------
def scope_at_return(source: str, function_name: str, args: Sequence[Any],
                    per_example_timeout: float) -> dict[str, Any] | None:
    """Run the defective program and keep the caller-visible locals at the moment it returns.

    This is the whole observable the synthesis gets. It is the same execution the tests already
    perform -- no instrumentation of the source, no rewrite of the program under test.
    """
    namespace: dict[str, Any] = {}
    try:
        exec(compile(source, "<observe>", "exec"), namespace)  # noqa: S102
        function = namespace[function_name]
    except Exception:  # noqa: BLE001
        return None
    captured: dict[str, Any] = {}

    def tracer(frame, event, arg):  # noqa: ANN001
        if event == "return" and frame.f_code.co_name == function_name:
            captured.update({k: copy.deepcopy(v) for k, v in frame.f_locals.items()})
        return tracer

    previous = sys.gettrace()
    sys.settrace(tracer)
    try:
        signal.setitimer(signal.ITIMER_REAL, per_example_timeout)
        function(*copy.deepcopy(list(args)))
        signal.setitimer(signal.ITIMER_REAL, 0)
    except gen._Timeout:
        signal.setitimer(signal.ITIMER_REAL, 0)
        return None
    except Exception:  # noqa: BLE001
        signal.setitimer(signal.ITIMER_REAL, 0)
        return None
    finally:
        sys.settrace(previous)
    return captured or None


def expression_space(scopes: Sequence[dict[str, Any]], *, depth: int = 2,
                     max_expressions: int = 4000) -> list[str]:
    """Bottom-up over the names in scope, pruned by arity and by repeated rejection.

    Depth 1 is every name and literal; depth 2 applies one operator; depth 3 applies one more.
    The list is deduplicated on the produced text, so equivalent spellings cost once.
    """
    names: set[str] = set()
    for scope in scopes:
        for key in scope:
            names.add(key)
    leaves = sorted(names) + [repr(x) for x in LITERALS]
    out: list[str] = []

    def add(text: str) -> bool:
        if text not in out:
            out.append(text)
        return len(out) >= max_expressions

    for leaf in leaves:
        if add(leaf):
            return out
    if depth >= 2:
        for name in CALLABLE_NAMES:
            for leaf in leaves:
                if add(f"{name}({leaf})"):
                    return out
        for op in UNOPS:
            for leaf in leaves:
                if add(f"({op.__name__.lower().replace('usub', '-')}{leaf})" if op is ast.USub
                       else f"(not {leaf})"):
                    return out
    if depth >= 3:
        simple = leaves[:40]
        for left, right in itertools.product(simple, repeat=2):
            for op in BINOPS:
                symbol = {
                    ast.Add: "+", ast.Sub: "-", ast.Mult: "*", ast.FloorDiv: "//", ast.Mod: "%",
                    ast.Eq: "==", ast.NotEq: "!=", ast.Lt: "<", ast.Gt: ">", ast.LtE: "<=",
                    ast.GtE: ">=", ast.And: "and", ast.Or: "or", ast.In: "in", ast.NotIn: "not in",
                }[op]
                if add(f"({left} {symbol} {right})"):
                    return out
    return out


def synthesize_return(source: str, function_name: str,
                      examples: Sequence[tuple[list[Any], Any]],
                      per_example_timeout: float, *, depth: int = 3,
                      max_expressions: int = 4000) -> dict[str, Any]:
    """Find expressions that produce every published answer from the observed scopes."""
    scopes = [scope_at_return(source, function_name, args, per_example_timeout)
              for args, _ in examples]
    if any(scope is None for scope in scopes):
        return {"status": "SCOPE_UNOBSERVABLE"}
    wanted = [want for _, want in examples]
    hits: list[str] = []
    tried = 0
    for expression in expression_space(scopes, depth=depth, max_expressions=max_expressions):
        tried += 1
        values = []
        ok = True
        for scope, want in zip(scopes, wanted):
            try:
                got = eval(expression, {"__builtins__": __builtins__}, scope)  # noqa: S307
            except Exception:  # noqa: BLE001
                ok = False
                break
            if not gen._equal(got, want):
                ok = False
                break
            values.append(got)
        if ok:
            hits.append(expression)
            if len(hits) >= 8:
                break
    return {"status": "FOUND" if hits else "NO_EXPRESSION", "expressions": hits,
            "expressions_tried": tried, "scopes": len(scopes)}


def install_return(source: str, function_name: str, expression: str) -> str | None:
    """Put the synthesized expression in place of the function's single return value."""
    tree = ast.parse(source)
    function = next((n for n in tree.body if isinstance(n, ast.FunctionDef)
                     and n.name == function_name), None)
    if function is None:
        return None
    # The fall-through return: a direct statement of the body, the last one. An early return inside
    # a loop is a different exit and is left alone -- replacing it with the expression observed at
    # the *fall-through* would be a hypothesis nothing supports.
    direct = [n for n in function.body if isinstance(n, ast.Return)]
    if not direct:
        nested = [n for n in function.body if isinstance(n, (ast.If, ast.Try))]
        for block in nested:
            direct.extend(n for n in ast.walk(block) if isinstance(n, ast.Return))
        if len(direct) != 1:
            return None
    returns = [direct[-1]]
    try:
        returns[0].value = ast.parse(expression, mode="eval").body
        ast.fix_missing_locations(tree)
        text = ast.unparse(tree)
        ast.parse(text)
    except (SyntaxError, ValueError):
        return None
    return text


# --------------------------------------------------------------------------------------------------
# measurement
# --------------------------------------------------------------------------------------------------
def measure_task(root: pathlib.Path, name: str, *, per_example_timeout: float,
                 verify_timeout: int, depth: int) -> dict[str, Any]:
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
    if not gen._install_alarm():
        row["stage"] = "UNMEASURABLE__NO_TIMER"
        return row
    baseline = gen.score(source, function.name, examples, per_example_timeout)
    row["baseline_examples_passed"] = baseline
    if baseline == len(examples):
        row["stage"] = "DEFECT_DOES_NOT_REPRODUCE"
        return row

    found = synthesize_return(source, function.name, examples, per_example_timeout, depth=depth)
    row.update({k: v for k, v in found.items() if k != "status"})
    row["synthesis_status"] = found["status"]
    if found["status"] != "FOUND":
        row["stage"] = "NOT_IN_THIS_FAMILY"
        row["seconds"] = round(time.time() - started, 1)
        return row

    # The only verdict that counts: the corpus's own pytest file, on a fresh copy of the task,
    # with the answer key absent from the directory (build_task refuses otherwise).
    import hashlib
    import tempfile

    for expression in found["expressions"]:
        patched = install_return(source, function.name, expression)
        if patched is None:
            continue
        if gen.score(patched, function.name, examples, per_example_timeout) != len(examples):
            continue
        with tempfile.TemporaryDirectory() as tmp:
            where = pathlib.Path(tmp)
            info = gen.build_task(root, name, where)
            (where / "python_programs" / f"{name}.py").write_text(patched)
            verdict = gen.verify_with_corpus_test(where, info["test_path"], verify_timeout)
        row["chosen_expression"] = expression
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


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--quixbugs", required=True)
    parser.add_argument("--tasks", nargs="*", default=None)
    parser.add_argument("--out", required=True)
    parser.add_argument("--receipt", default=None)
    parser.add_argument("--depth", type=int, default=3)
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
                                   verify_timeout=args.verify_timeout, depth=args.depth)
            except Exception as error:  # noqa: BLE001
                row = {"task": name, "kind": "task",
                       "stage": f"INSTRUMENT_ERROR:{type(error).__name__}"}
            rows.append(row)
            handle.write(json.dumps(row) + "\n")
            handle.flush()
            print(f"{name:<26} {row.get('stage',''):<42} "
                  f"tried={row.get('expressions_tried','?'):<6} {row.get('seconds','?')}s", flush=True)
    if args.receipt:
        receipt = {
            "schema": "BRAIN_SYNTHESIZED_EXPRESSION_FROM_THE_FAILURE_V1",
            "authority": "NONE__PRODUCER_RUN_SANDBOX",
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


def _tally(values) -> dict[str, int]:
    out: dict[str, int] = {}
    for value in values:
        out[str(value)] = out.get(str(value), 0) + 1
    return dict(sorted(out.items()))


if __name__ == "__main__":
    raise SystemExit(main())
