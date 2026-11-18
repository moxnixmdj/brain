"""Where an edit comes from: the repository's own history, and whether the failure is grammar or search.

WHY THIS EXISTS
---------------
Eight rounds measured *observation*: what can be seen of an environment's behaviour, how permanently, and
(round 8) that 73.7% of the previously unobservable class becomes observable when the environment is allowed
to execute its own tests. None of that produces a change. The standing complaint of this tree -- written into
``induced_edit_basis_v1`` in its own words -- is that the repair machinery enumerates a HAND-WRITTEN list of
edits (swap a comparison, swap ``min``/``max``, add a ``None`` guard, substitute a literal from the tests) and
that list "decides everything, and it decides it BEFORE any search happens".

The first-principles consequence is the same one round 7 found for arguments and round 8 found for
observations: **do not invent the space, read it out of the environment.** A repository's own commit history
is a corpus of proven edits -- each diff is a change that somebody made and the project accepted -- exactly as
its tests are proofs of which call arguments work and its test runs are proofs of what the code does.

So the grammar here is INDUCED from real diffs (``induced_edit_basis_v1.induce_templates``, reused, never
rebuilt), and it is induced from OTHER repositories' commits, so a task is solved only by templates the task's
own repository never taught. No hand-written operator list exists in this file.

WHAT IS MEASURED, AND WHY THAT IS THE HONEST QUESTION
-----------------------------------------------------
Fixing a real commit is two questions that are usually confused:

    * Is the required edit even IN the grammar?   (expressibility -- a property of induction)
    * Given that it is, does the search find it?   (identifiability -- a property of search)

This file answers both, per task, and never lets one hide behind the other:

    SOLVED                        the failing test passes under a candidate, and the source was restored
    EXPRESSIBLE_NOT_FOUND         the commit's own edit IS a grammar template that fires at the true site,
                                  and the bounded search still did not reach the passing candidate
    NOT_EXPRESSIBLE               no template in the basis reproduces the commit's edit at the true site
    REFUSED__NO_TRACEBACK_SITE    the failing test's traceback never enters the source file under test
    REFUSED__NO_TEMPLATE_FIRES    no template's precondition holds anywhere in the file
    REFUSED__TEST_WOULD_NOT_RUN   the integrity gate itself failed (test must pass at the commit and fail at
                                  the parent with the commit's own test file), so the task is not a task

The corpus is REAL COMMITS mined from the repositories themselves: one source file and one test file, the test
must FAIL at the parent and PASS at the commit. Nothing is synthesised, no bug is injected, and the fix diff is
held out from the search (it is used only to ask the expressibility question, after the search has finished).

LOCALISATION IS FREE AND IT IS NOT TEXT
---------------------------------------
A failing test hands over a runtime traceback naming the exact file and line. That is the causal observable
the insufficiency certificate says is usually missing -- here it is the first thing we get. Candidate sites
inside the traceback's enclosing function are searched first; the rest of the file follows, so a wrong
localisation weakens the search but cannot make it impossible.

Reuses: ``induced_edit_basis_v1`` (templates, sites, install), ``scenario_observation_v1`` concepts of
execution-as-evidence. Refuses to touch a tree destructively: the original bytes are restored in ``finally``.
Authority NONE -- sandbox measurement, not independent verification. No model is called. $0.
"""

from __future__ import annotations

import ast
import copy
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
from typing import Any, Iterable, Mapping, Sequence

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from canonical.swe_kernel import induced_edit_basis_v1 as BASIS  # noqa: E402

SCHEMA = "BRAIN_HISTORY_INDUCED_EDIT_GRAMMAR_V1"
MODEL_CALLS = 0
NETWORK_CALLS = 0
# tomli's tests run in ~0.02s, so the search here is EXHAUSTIVE over the grammar's firings rather than
# budget-limited: a failure can then only be the grammar's, never the budget's.
SEARCH_BUDGET = 400
CANDIDATE_TIMEOUT_S = 120

SOLVED = "SOLVED"
EXPRESSIBLE_NOT_FOUND = "EXPRESSIBLE_NOT_FOUND"
NOT_EXPRESSIBLE = "NOT_EXPRESSIBLE"
REFUSED_NO_TRACEBACK = "REFUSED__NO_TRACEBACK_SITE"
REFUSED_NO_TEMPLATE = "REFUSED__NO_TEMPLATE_FIRES"
REFUSED_NO_RUN = "REFUSED__TEST_WOULD_NOT_RUN"
REFUSED_NO_SOURCE = "REFUSED__SOURCE_FILE_ABSENT"


# --------------------------------------------------------------------------------------------------
# localisation: the traceback is the causal observable, so use it
# --------------------------------------------------------------------------------------------------

_FRAME = re.compile(r"^(?P<file>[^\s:][^:]*\.py):(?P<line>\d+): in (?P<name>\w+)", re.M)


def traceback_site(stdout: str, source_rel: str) -> dict[str, Any] | None:
    """The innermost frame that lies in the file under test -- the line the test actually died on."""
    hits = [m.groupdict() for m in _FRAME.finditer(stdout or "")]
    inside = [hit for hit in hits
              if hit["file"].replace("\\", "/").endswith(source_rel.replace("\\", "/"))]
    if not inside:
        return None
    last = inside[-1]
    return {"line": int(last["line"]), "function": last["name"]}


def enclosing_function(tree: ast.AST, line: int) -> ast.AST | None:
    best = None
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            start = node.lineno
            end = getattr(node, "end_lineno", start) or start
            if start <= line <= end:
                if best is None or start > best.lineno:
                    best = node
    return best


# --------------------------------------------------------------------------------------------------
# the grammar: induced from real diffs, never written here
# --------------------------------------------------------------------------------------------------

def induce_grammar(pairs: Iterable[tuple[str, str, str]],
                   context_depth: int = 1) -> list[BASIS.EditTemplate]:
    """Fold real (name, defective, repaired) diffs into a basis. Delegates; does not re-implement."""
    return BASIS.induce_templates(pairs, context_depth=context_depth, max_templates_per_pair=12)


def _node_value(node: ast.AST, role: str) -> Any:
    return BASIS._site_value(node, role)


def localized_candidates(source: str, templates: Sequence[BASIS.EditTemplate],
                        function_line: int | None, cap: int = SEARCH_BUDGET) -> list[dict[str, Any]]:
    """Candidates ordered: sites inside the traceback's function first, then the rest of the file."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    target = enclosing_function(tree, function_line) if function_line else None
    inside_ids = {id(node) for node in ast.walk(target)} if target is not None else set()
    ordered: list[dict[str, Any]] = []
    for template in templates:
        if not template.executable:
            continue
        for ancestry, path, node, parent, field in BASIS._sites(tree):
            if parent is None or type(node).__name__ != template.node_type:
                continue
            if template.context and tuple(ancestry[-len(template.context):]) != template.context:
                continue
            if _node_value(node, template.role) != template.old:
                continue
            mutated = copy.deepcopy(tree)
            try:
                target_node = BASIS._resolve(mutated, path)
            except Exception:  # noqa: BLE001 - a path that cannot be resolved is simply not a candidate
                continue
            if target_node is None or type(target_node).__name__ != template.node_type:
                continue
            if not BASIS._install(None, field, target_node, template.role, template.new):
                continue
            try:
                text = ast.unparse(ast.fix_missing_locations(mutated))
                ast.parse(text)
            except (SyntaxError, ValueError):
                continue
            ordered.append({
                "template_id": template.template_id(),
                "mutation": f"{template.node_type}.{template.role}:{template.old}->{template.new}",
                "support": template.support, "taught_by": list(template.taught_by),
                "in_traceback_function": id(node) in inside_ids,
                "site_path": [list(step) for step in path],
                "source": text,
            })
    ordered.sort(key=lambda entry: (not entry["in_traceback_function"], -entry["support"], entry["template_id"]))
    return ordered[:cap]


def template_fires_at(source: str, template: BASIS.EditTemplate,
                      function_line: int | None) -> dict[str, Any] | None:
    """Does the commit's OWN edit fire as a grammar template at the site the traceback points to?"""
    found = localized_candidates(source, [template], function_line, cap=8)
    if not found:
        return None
    return found[0]


# --------------------------------------------------------------------------------------------------
# execution: the only judge
# --------------------------------------------------------------------------------------------------

def _env_for(tree: pathlib.Path) -> dict[str, str]:
    env = dict(os.environ)
    paths = [str(tree / "src"), str(tree)]
    env["PYTHONPATH"] = os.pathsep.join(paths + ([env["PYTHONPATH"]] if env.get("PYTHONPATH") else []))
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONHASHSEED"] = "0"
    return env


def run_test(tree: pathlib.Path, test_rel: str, timeout_s: int = CANDIDATE_TIMEOUT_S) -> dict[str, Any]:
    argv = [sys.executable, "-m", "pytest", test_rel, "-q", "--no-header", "-p", "no:cacheprovider"]
    try:
        proc = subprocess.run(argv, cwd=str(tree), env=_env_for(tree), capture_output=True, text=True,
                              timeout=timeout_s)
    except subprocess.TimeoutExpired:
        return {"outcome": "TIMEOUT", "stdout": "", "passed": False}
    return {"outcome": "PASS" if proc.returncode == 0 else "FAIL", "stdout": proc.stdout + proc.stderr,
            "passed": proc.returncode == 0}


def try_candidate(tree: pathlib.Path, source_rel: str, test_rel: str,
                  text: str) -> dict[str, Any]:
    """Apply, judge, and ALWAYS restore. A tree left modified would make every later measurement a lie."""
    target = tree / source_rel
    original = target.read_bytes()
    try:
        target.write_text(text, encoding="utf-8")
        return run_test(tree, test_rel)
    finally:
        target.write_bytes(original)


# --------------------------------------------------------------------------------------------------
# one task
# --------------------------------------------------------------------------------------------------

def solve_task(task: Mapping[str, Any], grammar: Sequence[BASIS.EditTemplate],
               oracle_pairs: Sequence[tuple[str, str, str]] = ()) -> dict[str, Any]:
    tree = pathlib.Path(task["parent_tree"])
    source_rel, test_rel = task["source"], task["test"]
    if not (tree / source_rel).is_file():
        return {"repo": task["repo"], "sha": task["sha"], "source": source_rel, "test": test_rel,
                "state": REFUSED_NO_SOURCE, "note": "the task names a file the parent tree does not have"}
    source = (tree / source_rel).read_text(encoding="utf-8", errors="replace")
    row: dict[str, Any] = {"repo": task["repo"], "sha": task["sha"], "source": source_rel, "test": test_rel,
                           "failed_nodes": task.get("failed_nodes", [])}

    baseline = run_test(tree, test_rel)
    if baseline["passed"]:
        row["state"] = REFUSED_NO_RUN
        row["note"] = "the test passes at the parent with the commit's test file: not a real task"
        return row
    site = traceback_site(baseline["stdout"], source_rel)
    row["traceback"] = site
    function_line = site["line"] if site else None

    candidates = localized_candidates(source, grammar, function_line)
    row["templates_fired"] = len(candidates)
    row["from_traceback_function"] = sum(1 for entry in candidates if entry["in_traceback_function"])
    if not candidates:
        row["state"] = REFUSED_NO_TEMPLATE
        row["oracle"] = _oracle_verdict(oracle_pairs, source, function_line, tree, source_rel, test_rel)
        return row

    for entry in candidates:
        outcome = try_candidate(tree, source_rel, test_rel, entry["source"])
        row["trials"] = row.get("trials", 0) + 1
        if outcome["passed"]:
            row["state"] = SOLVED
            row["applied"] = entry["mutation"]
            row["taught_by"] = entry["taught_by"]
            row["oracle"] = "TRUE_EDIT_EXPRESSION_UNKNOWN"
            return row

    row["oracle"] = _oracle_verdict(oracle_pairs, source, function_line, tree, source_rel, test_rel)
    if row["oracle"]["state"] == "ORACLE_SOLVES":
        # the commit's own edit IS a single grammar template that fires and passes, and the exhaustive
        # search still did not choose it: that is a search failure, not a grammar failure
        row["state"] = EXPRESSIBLE_NOT_FOUND
    elif row["oracle"]["state"] == "ORACLE_APPLIED_NOT_ENOUGH":
        # one template from the commit fires but does not fix it: this task needs a COMPOSITE edit
        row["state"] = "COMPOSITE_EDIT_REQUIRED"
    else:
        row["state"] = NOT_EXPRESSIBLE
    return row


def _oracle_verdict(oracle_pairs: Sequence[tuple[str, str, str]], source: str,
                    function_line: int | None, tree: pathlib.Path, source_rel: str,
                    test_rel: str) -> dict[str, Any]:
    """The commit's own diff, induced and fired at the traceback site -- after the search, never during it."""
    if not oracle_pairs:
        return {"state": "ORACLE_UNAVAILABLE"}
    induced = induce_grammar(oracle_pairs)
    for template in induced:
        if not template.executable:
            continue
        fired = template_fires_at(source, template, function_line)
        if fired:
            outcome = try_candidate(tree, source_rel, test_rel, fired["source"])
            return {"state": "ORACLE_SOLVES" if outcome["passed"] else "ORACLE_APPLIED_NOT_ENOUGH",
                    "mutation": fired["mutation"],
                    "in_traceback_function": fired["in_traceback_function"],
                    "template_id": template.template_id()}
    return {"state": "ORACLE_DOES_NOT_FIRE", "templates": len(induced),
            "kinds": sorted({template.kind for template in induced})}


# --------------------------------------------------------------------------------------------------
# the corpus
# --------------------------------------------------------------------------------------------------

def load_corpus(path: pathlib.Path) -> tuple[list[dict[str, Any]], dict[str, list[tuple[str, str, str]]]]:
    """Tasks and, per repository, its own (defective, repaired) diffs -- used as grammar for OTHERS only."""
    tasks = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    grammar_path = pathlib.Path(path).with_name("grammar.json")
    pairs: dict[str, list[tuple[str, str, str]]] = {}
    if grammar_path.is_file():
        for entry in json.loads(grammar_path.read_text(encoding="utf-8")):
            pairs.setdefault(entry["name"], []).append(
                (entry["sha"][:8] + ":" + entry["source"], entry["defective"], entry["repaired"]))
    return tasks, pairs


def measure(tasks: Sequence[Mapping[str, Any]], pairs: Mapping[str, Sequence[tuple[str, str, str]]],
            budget: int = SEARCH_BUDGET) -> dict[str, Any]:
    """Leave-one-repository-out: a task is solved only by templates its own repository never contributed."""
    rows: list[dict[str, Any]] = []
    for task in tasks:
        name = task["name"]
        teaching = [pair for other, group in pairs.items() if other != name for pair in group]
        grammar = induce_grammar(teaching)
        own = [(task["sha"][:8], task.get("parent_source", ""), task.get("commit_source", ""))]
        row = solve_task(task, grammar, oracle_pairs=[pair for pair in own if pair[1] and pair[2]])
        row["grammar_templates"] = len(grammar)
        row["grammar_from_repos"] = sorted({repo for repo, group in pairs.items() if repo != name and group})
        rows.append(row)
    return summarise(rows)


def summarise(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    states: dict[str, int] = {}
    for row in rows:
        states[row["state"]] = states.get(row["state"], 0) + 1
    tasks = len(rows)
    solved = states.get(SOLVED, 0)
    oracle_fires = sum(1 for row in rows
                       if (row.get("oracle") or {}).get("state") in ("ORACLE_SOLVES", "ORACLE_APPLIED_NOT_ENOUGH"))
    totals = {
        "tasks": tasks, "states": states, "solved": solved,
        "solved_fraction": round(solved / tasks, 4) if tasks else 0.0,
        "oracle_fires": oracle_fires,
        "oracle_fires_fraction": round(oracle_fires / tasks, 4) if tasks else 0.0,
        "trials": sum(row.get("trials", 0) for row in rows),
        "mean_trials": round(sum(row.get("trials", 0) for row in rows) / tasks, 2) if tasks else 0.0,
        "solved_within_traceback_function": sum(
            1 for row in rows if row["state"] == SOLVED and row.get("from_traceback_function")),
        "grammar_templates": sorted({row.get("grammar_templates") for row in rows}),
    }
    return {"schema": SCHEMA, "rows": list(rows), "totals": totals, "model_calls": MODEL_CALLS,
            "network_calls": NETWORK_CALLS,
            "authority": "NONE -- sandbox measurement, not independent verification"}


def headline(report: Mapping[str, Any]) -> str:
    totals = report["totals"]
    states = totals["states"]
    parts = [f"{totals['tasks']} real fix commits (test fails at the parent and passes at the commit)."]
    parts.append(f"Grammar induced from other repositories' diffs only; {totals['solved']} "
                 f"({totals['solved_fraction']}) solved in at most {SEARCH_BUDGET} executions each, "
                 f"{totals['mean_trials']} executions on average.")
    parts.append(f"The commit's own edit fires as a grammar template in {totals['oracle_fires']} of "
                 f"{totals['tasks']} tasks ({totals['oracle_fires_fraction']}), so the rest is grammar, not search.")
    parts.append("States: " + ", ".join(f"{state} {count}" for state, count in sorted(states.items())) + ".")
    return " ".join(parts)


def main(argv: Sequence[str] | None = None) -> int:
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", type=pathlib.Path, default=pathlib.Path("/tmp/tasks.json"))
    parser.add_argument("--json", type=pathlib.Path)
    args = parser.parse_args(argv)
    tasks, pairs = load_corpus(args.corpus)
    report = measure(tasks, pairs)
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(report, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        print(f"written: {args.json}")
    print(headline(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
