"""The discriminating pair, captured from execution one test case at a time.

WHY THIS EXISTS, AND WHAT IT DOES NOT REBUILD
---------------------------------------------
The tree already holds every other piece of this chain, and searching for them first was the whole point:

    exact verifier                     history_induced_edit_grammar_v1.try_candidate / run_test
    predicates invented from imports    operand_invention_v1.separating_terms  (round 11)
    seat + binding + adjoin             operand_invention_v1.sites_from_parameter / bind / rewritten
    runtime value capture               bound_capabilities.python_interprocedural_value_provenance_v1

The last one is the one that looked like it closed the gap, and it does not, for a reason that is measurable
rather than aesthetic: it partitions **test files**. Run on `pypa/packaging` 022ae6c6 it returns
`failing_test_count=1, passing_test_count=0` -- one file fails, no file passes -- so the failing-versus-passing
differential it is built to compute is empty on the exact case that matters. A real commit fails *two cases*
out of 344 inside one file, and the discriminating pair lives at case granularity, not file granularity.

Round 11 could only read literal `@pytest.mark.parametrize` tables, which is why six of seven real commits were
refused with `REFUSED__NO_OPERAND`: their failing value is constructed inside the test body, not written in a
table. This module reads the value from the running test instead.

WHAT IT MEASURES
----------------
    partition   for one (function, argument): the values observed on failing cases vs on passing cases
    predicate   an expression over that value, read from the target's own imports, TRUE on every failing
                value and FALSE on every passing one
    seat        a guard inside the function that actually received the bad value -- not a name match
    verdict     the commit's own test file, unmodified, one pass = solved

The control arm is round 11 measured on the same tasks, so the single changed variable is where the
discriminating pair comes from: a literal table, or the running execution.

REFUSALS, NAMED
---------------
    REFUSED__NO_PARTITION        no argument differs between failing and passing cases
    REFUSED__NO_PREDICATE        a partition exists, but nothing in the target's imports separates it
    REFUSED__NO_SEAT             the receiving function has no guard to adjoin
    REFUSED__COLLECTION          pytest could not enumerate the file's cases

Model calls 0, network calls 0. Authority NONE.
"""

from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys
import tempfile
from typing import Any, Mapping, Sequence

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from canonical.swe_kernel import history_induced_edit_grammar_v1 as G  # noqa: E402
from canonical.swe_kernel import operand_invention_v1 as OPERAND  # noqa: E402
from canonical.swe_kernel import structural_rewrite_induction_v1 as SHAPE  # noqa: E402

SCHEMA = "BRAIN_CASE_WITNESS_V1"
MODEL_CALLS = 0
NETWORK_CALLS = 0
PASSING_CASES = 6
TRIAL_CAP = 60

SOLVED = "SOLVED"
NO_SOLVE = "PARTITION_FOUND_NEVER_SOLVES"
REFUSED_NO_PARTITION = "REFUSED__NO_PARTITION"
REFUSED_NO_PREDICATE = "REFUSED__NO_PREDICATE"
REFUSED_NO_SEAT = "REFUSED__NO_SEAT"
REFUSED_COLLECTION = "REFUSED__COLLECTION"

PLUGIN = r'''import json, os, sys

TARGET = os.path.abspath(os.environ["BRAIN_WITNESS_TARGET"])
OUT = os.environ["BRAIN_WITNESS_OUT"]
_rows = []


def _value(v):
    if isinstance(v, bool) or v is None or isinstance(v, (int, float)):
        return {"value": v}
    if isinstance(v, str):
        return {"value": v} if len(v) <= 300 else {"repr": v[:300]}
    if isinstance(v, (list, tuple)) and len(v) <= 50 and all(
            isinstance(x, (str, int, float, bool)) or x is None for x in v):
        return {"value": list(v)}
    try:
        return {"repr": repr(v)[:200]}
    except Exception:
        return {"repr": "<unrepresentable>"}


def _profile(frame, event, arg):
    if event != "call":
        return
    try:
        if os.path.abspath(frame.f_code.co_filename) != TARGET:
            return
    except Exception:
        return
    code = frame.f_code
    args = {}
    for name in code.co_varnames[:code.co_argcount]:
        if name in frame.f_locals:
            args[name] = _value(frame.f_locals[name])
    _rows.append({"function": code.co_name, "args": args})


def _flush(item):
    sys.setprofile(None)
    with open(OUT, "a", encoding="utf-8") as fh:
        fh.write(json.dumps({"node": item.nodeid, "calls": _rows}) + "\n")


def pytest_runtest_setup(item):
    del _rows[:]
    sys.setprofile(_profile)


def pytest_runtest_teardown(item, nextitem):
    _flush(item)
'''


def _env_for(tree: pathlib.Path, work: pathlib.Path) -> dict[str, str]:
    """The tree's own runner environment, plus the directory the witness plugin lives in.

    This must delegate to `history_induced_edit_grammar_v1._env_for`, and not be re-derived: a first attempt
    at this module built its own environment, forgot `tree/src`, and `packaging` resolved from site-packages
    instead of the repository under test -- the tests ran, they passed or failed, and they were not testing
    the tree at all. Silent, and fatal to every number.
    """
    env = G._env_for(tree)
    env["PYTHONPATH"] = os.pathsep.join([str(work), env["PYTHONPATH"]])
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return env


def collect_cases(tree: pathlib.Path, test_rel: str, timeout_s: int = 120) -> list[str]:
    try:
        proc = subprocess.run([sys.executable, "-m", "pytest", test_rel, "-q", "--collect-only",
                               "-p", "no:cacheprovider"], cwd=str(tree), env=_env_for(tree, tree),
                              capture_output=True, text=True, timeout=timeout_s)
    except subprocess.TimeoutExpired:
        return []
    return [line.strip() for line in proc.stdout.splitlines() if "::" in line and not line.startswith(" ")][:400]


def capture(tree: pathlib.Path, test_rel: str, nodes: Sequence[str], target_rel: str,
            work: pathlib.Path, timeout_s: int = 120) -> dict[str, list[dict[str, Any]]]:
    """Run each case alone, recording the arguments every call into the target file received."""
    plugin = work / "brain_witness_plugin.py"
    if not plugin.is_file():
        plugin.write_text(PLUGIN, encoding="utf-8")
    out_path = work / "witness.jsonl"
    if out_path.exists():
        out_path.unlink()
    env = _env_for(tree, work)
    env["BRAIN_WITNESS_TARGET"] = str((tree / target_rel).resolve())
    env["BRAIN_WITNESS_OUT"] = str(out_path)
    env["PYTEST_PLUGINS"] = "brain_witness_plugin"
    for node in nodes:
        try:
            subprocess.run([sys.executable, "-m", "pytest", node, "-q", "--no-header", "--tb=no",
                            "-p", "no:cacheprovider"], cwd=str(tree), env=env,
                           capture_output=True, text=True, timeout=timeout_s)
        except subprocess.TimeoutExpired:
            continue
    rows: dict[str, list[dict[str, Any]]] = {}
    if out_path.is_file():
        for line in out_path.read_text(encoding="utf-8").splitlines():
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            rows[record["node"]] = record["calls"]
    return rows


def _plain(cell: Any) -> Any:
    return cell["value"] if isinstance(cell, Mapping) and "value" in cell else None


def partition(rows: Mapping[str, Sequence[Mapping[str, Any]]], failing: Sequence[str],
              passing: Sequence[str]) -> list[dict[str, Any]]:
    """Every (function, argument) whose observed values differ between failing and passing cases."""
    def collect(nodes, key):
        seen: dict[tuple[str, str], list[Any]] = {}
        for node in nodes:
            for call in rows.get(node, []):
                for name, cell in call.get("args", {}).items():
                    value = _plain(cell)
                    if value is None:
                        continue
                    bucket = seen.setdefault((call["function"], name), [])
                    if value not in bucket:
                        bucket.append(value)
        return seen

    bad, good = collect(failing, "bad"), collect(passing, "good")
    found: list[dict[str, Any]] = []
    for key in sorted(bad):
        if key not in good:
            continue
        if not isinstance(key[0], str) or key[0].startswith("<"):
            continue
        if bad[key] == good[key]:                      # present in both, but not different: not evidence
            continue
        if set(map(repr, bad[key])) & set(map(repr, good[key])):
            continue                                   # a value on both sides cannot separate them
        found.append({"function": key[0], "argument": key[1],
                      "failing": bad[key][:8], "passing": good[key][:8]})
    return found


def sibling_cases(cases: Sequence[str], failing: Sequence[str]) -> list[str]:
    """Passing cases of the SAME test function. A sibling is the only honest negative: it is the case the
    code went on to accept after the same entry point accepted nothing -- sampling arbitrary passing cases
    from the file finds cases that never reach the function at all, and the partition comes back empty."""
    broken = set(failing)
    stems = {node.split("[")[0] for node in failing}
    siblings = [case for case in cases if case.split("[")[0] in stems and case not in broken]
    return siblings or [case for case in cases if case not in broken]


def sites_in(source: str, function: str) -> list[tuple[int, str]]:
    """The guards inside the function that actually received the bad value."""
    import ast
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    seats: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == function:
            for inner in ast.walk(node):
                if isinstance(inner, (ast.If, ast.While)):
                    text = ast.unparse(inner.test)
                    if (inner.lineno, text) not in seats:
                        seats.append((inner.lineno, text))
    return seats[:4]


def solve_task(task: Mapping[str, Any], work: pathlib.Path) -> dict[str, Any]:
    tree = pathlib.Path(task["parent_tree"])
    source_rel, test_rel = task["source"], task["test"]
    row: dict[str, Any] = {"repo": task["repo"], "sha": task["sha"], "source": source_rel, "test": test_rel}
    if not (tree / source_rel).is_file():
        return {**row, "state": REFUSED_NO_PARTITION}
    source = (tree / source_rel).read_text(encoding="utf-8", errors="replace")
    failing = [node for node in task.get("failed_nodes") or [] if node.endswith("]") or "::" in node]
    cases = collect_cases(tree, test_rel)
    if not cases:
        return {**row, "state": REFUSED_COLLECTION}
    passing = sibling_cases(cases, failing)[:PASSING_CASES]
    rows = capture(tree, test_rel, list(failing) + passing, source_rel, work)
    row["captured"] = sorted(set(rows) & set(failing)), len(passing)
    parts = partition(rows, failing, passing)
    row["partitions"] = [{k: part[k] for k in ("function", "argument")} for part in parts][:4]
    if not parts:
        return {**row, "state": REFUSED_NO_PARTITION}
    row["trials"] = 0
    for part in parts:
        terms = OPERAND.separating_terms(part["failing"], part["passing"], source)
        row.setdefault("terms", {})[f"{part['function']}.{part['argument']}"] = len(terms)
        if not terms:
            continue
        seats = sites_in(source, part["function"])
        if not seats:
            continue
        row["seat_function"] = part["function"]
        for line_of, condition in seats:
            for raw in terms[:6]:
                term = OPERAND.bind(raw, line_of, source)
                for operator in ("or", "and"):
                    candidate = OPERAND.rewritten(source, line_of, condition, term, operator)
                    if candidate is None:
                        continue
                    row["trials"] += 1
                    if G.try_candidate(tree, source_rel, test_rel, candidate)["passed"]:
                        return {**row, "state": SOLVED, "operand": term, "operator": operator,
                                "at_line": line_of, "condition": condition}
                    if row["trials"] >= TRIAL_CAP:
                        return {**row, "state": NO_SOLVE}
    return {**row, "state": REFUSED_NO_PREDICATE if not row.get("terms") or not any(row["terms"].values())
            else NO_SOLVE}


def measure(tasks: Sequence[Mapping[str, Any]], control: bool = True) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for task in tasks:
        with tempfile.TemporaryDirectory() as tmp:
            row = solve_task(task, pathlib.Path(tmp))
        if control:
            row["literal_params_only"] = OPERAND.invent(task)["state"]
        rows.append(row)
    states: dict[str, int] = {}
    for row in rows:
        states[row["state"]] = states.get(row["state"], 0) + 1
    solved = states.get(SOLVED, 0)
    return {"schema": SCHEMA, "rows": rows, "model_calls": MODEL_CALLS, "network_calls": NETWORK_CALLS,
            "authority": "NONE -- sandbox measurement, not independent verification",
            "totals": {"tasks": len(rows), "states": states, "solved": solved,
                       "solved_fraction": round(solved / len(rows), 4) if rows else 0.0,
                       "trials": sum(row.get("trials", 0) for row in rows),
                       "partitioned": sum(1 for row in rows if row.get("partitions")),
                       "literal_params_only_solved": sum(1 for row in rows
                                                         if row.get("literal_params_only") == SOLVED)}}


def headline(report: Mapping[str, Any]) -> str:
    totals = report["totals"]
    won = [row for row in report["rows"] if row["state"] == SOLVED]
    detail = "; ".join(f"{row['repo'].split('/')[-1]} line {row.get('at_line')}: {row.get('operand')}"
                       for row in won)
    return (f"{totals['tasks']} real fix commits, discriminating pair captured from the running cases: "
            f"{totals['partitioned']} produced a failing-versus-passing value partition, {totals['solved']} "
            f"solved ({totals['solved_fraction']}) in {totals['trials']} executions; the same tasks reading only "
            f"literal parametrize tables solved {totals['literal_params_only_solved']}. States: "
            + ", ".join(f"{state} {count}" for state, count in sorted(totals["states"].items()))
            + (f". Solved by: {detail}" if detail else "") + ".")


def main(argv: Sequence[str] | None = None) -> int:
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=pathlib.Path,
                        default=pathlib.Path("canonical/corpus/real_fix_commits_20261116_V1.json"))
    parser.add_argument("--hist", type=pathlib.Path, default=pathlib.Path("/tmp/hist"))
    parser.add_argument("--work", type=pathlib.Path, default=pathlib.Path("/tmp/histwork"))
    parser.add_argument("--json", type=pathlib.Path)
    parser.add_argument("--limit", type=int, default=9)
    args = parser.parse_args(argv)
    tasks = SHAPE.prepare_corpus(args.manifest, args.hist, args.work, limit=args.limit)
    report = measure(tasks)
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(report, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        print(f"written: {args.json}")
    print(headline(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
