"""Give the tree's own repair engine a vocabulary learned from REAL commits, and measure it on real commits.

WHAT ALREADY EXISTED, AND WHY THAT DECIDED THIS ROUND
-----------------------------------------------------
Before writing anything, the tree was searched for the mechanism this round was about to build -- repair
driven by the failing assertion, with a vocabulary induced at repair time. It already exists, and its own
docstring names it:

    closed_loop_trace_abduction_repair_v1 -- "Closed-Loop Execution-Trace Abduction, Dynamic Vocabulary
    Induction & Counterfactual Falsification -- the $0 repair engine"

It composes TraceSlice, Ochiai ranking, dynamic observables, `extract_assert_cases`, expression synthesis,
`replace_line_expression`, degeneracy/perturbation/locality falsification -- and it was measured on
HumanEvalFix (58/100) and QuixBugs (20/40), i.e. on benchmark bugs with single-function shape.

Nine rounds of this series have shown repeatedly that the missing ingredient is not a new algorithm but the
environment's own evidence: arguments (round 7), observations (round 8), diffs (rounds 9-10). The engine's
`Lessons` object has never been fed anything but benchmark bugs. So this round does not rebuild the engine.
It hands the engine a vocabulary learned from **the environment's own real commits** -- leave-one-repository-out,
so a task can only be repaired by edit kinds taught by other repositories -- and measures the result on real
fix commits whose tests fail at the parent and pass at the commit.

THE TWO CONDITIONS, MEASURED AGAINST EACH OTHER
-----------------------------------------------
    VOCABULARY   Lessons learned from the other repositories' real diffs + the failing test's trace slice
    SLICE_ONLY   the same engine with an EMPTY vocabulary, i.e. trace slice and synthesis alone

The difference between them is the measured value of the vocabulary, which is the only thing this round adds.

WHAT WAS MEASURED, ON SEVEN REAL FIX COMMITS
--------------------------------------------
    edit-kind lessons from other repositories' real diffs    30 proposals per task, 0 solved in 90 executions
    empty vocabulary                                         0 proposals: the trace-slice path finds nothing
                                                             on a real repository file
    proposals that touch the real hunk                       all of them, at unrelated lines as well -- the
                                                             lessons graft the SOURCE's operands into the
                                                             TARGET: one candidate for tomli/_parser.py
                                                             contains packaging's own
                                                             `pathlib.PureWindowsPath(path).drive`
The last line is the finding. A lesson learned from a diff does not transfer its meaning; it transfers its
syntax together with the words of the place it was learned in. That is why experience does not accumulate
here, and it is measured rather than argued.

REFUSALS, NAMED
---------------
    REFUSED__NO_ENTRY_IN_TEST        the test file names no function the source file defines
    REFUSED__NO_PROPOSAL             the engine produced no candidate at all
    REFUSED__TEST_WOULD_NOT_RUN      the commit's test already passes at the parent (not a task)
    REFUSED__SOURCE_FILE_ABSENT      the task names a file the parent tree does not have

Reuses, never rebuilds: `closed_loop_trace_abduction_repair_v1.proposals_for`,
`edit_kind_learning_v1.Lessons`, `structural_rewrite_induction_v1.prepare_corpus`,
`history_induced_edit_grammar_v1.run_test/try_candidate`. No model. $0. Authority NONE.
"""

from __future__ import annotations

import ast
import difflib
import json
import pathlib
import re
import sys
from typing import Any, Mapping, Sequence

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from canonical.runtime import edit_kind_learning_v1 as KINDS  # noqa: E402
from canonical.swe_kernel import closed_loop_trace_abduction_repair_v1 as ENGINE  # noqa: E402
from canonical.swe_kernel import history_induced_edit_grammar_v1 as G  # noqa: E402
from canonical.swe_kernel import structural_rewrite_induction_v1 as SHAPE  # noqa: E402

SCHEMA = "BRAIN_REAL_COMMIT_REPAIR_V1"
MODEL_CALLS = 0
NETWORK_CALLS = 0
TRIAL_CAP = 30
MAX_LESSONS = 60

SOLVED = "SOLVED"
FAILED = "VOCABULARY_FIRES_NEVER_SOLVES"
REFUSED_NO_ENTRY = "REFUSED__NO_ENTRY_IN_TEST"
REFUSED_NO_PROPOSAL = "REFUSED__NO_PROPOSAL"
REFUSED_NO_RUN = "REFUSED__TEST_WOULD_NOT_RUN"
REFUSED_NO_SOURCE = "REFUSED__SOURCE_FILE_ABSENT"


def functions_in(source: str) -> list[str]:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    return [node.name for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))]


def entries_named_by_test(source: str, test_source: str) -> list[str]:
    """The functions the test actually names, public ones first: the only legitimate entry points."""
    defined = functions_in(source)
    named = [name for name in defined if re.search(rf"\b{re.escape(name)}\b", test_source)]
    named.sort(key=lambda name: (name.startswith("_"), defined.index(name)))
    return named


def changed_span(before: str, after: str) -> list[tuple[int, int]]:
    """The lines the change rewrites: zero-based, half-open. Empty when the two texts read the same."""
    old, new = before.splitlines(), after.splitlines()
    spans = []
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, old, new, autojunk=False).get_opcodes():
        if tag != "equal":
            spans.append((i1, max(i2, i1 + 1)))
    return spans


def touches(spans: Sequence[tuple[int, int]], hunk: Sequence[tuple[int, int]]) -> bool:
    return any(not (end <= start or stop <= begin) for begin, end in spans for start, stop in hunk)


def learn_lessons(pairs: Sequence[tuple[str, str, str]], cap: int = MAX_LESSONS) -> tuple[KINDS.Lessons, int]:
    """Edit-kind lessons from real diffs. Leave-one-repository-out is the caller's responsibility."""
    lessons = KINDS.Lessons()
    learned = 0
    for name, before, after in list(pairs)[:cap]:
        try:
            if lessons.learn(name, before, after):
                learned += 1
        except Exception:  # noqa: BLE001 - a diff that cannot teach is skipped, never counted
            continue
    return lessons, learned


def repair_task(task: Mapping[str, Any], lessons: KINDS.Lessons | None, evidence: bool = True) -> dict[str, Any]:
    tree = pathlib.Path(task["parent_tree"])
    source_rel, test_rel = task["source"], task["test"]
    row: dict[str, Any] = {"repo": task["repo"], "sha": task["sha"], "source": source_rel, "test": test_rel}
    if not (tree / source_rel).is_file():
        return {**row, "state": REFUSED_NO_SOURCE}
    baseline = G.run_test(tree, test_rel)
    if baseline["passed"]:
        return {**row, "state": REFUSED_NO_RUN}
    source = (tree / source_rel).read_text(encoding="utf-8", errors="replace")
    test_source = (tree / test_rel).read_text(encoding="utf-8", errors="replace") if (tree / test_rel).is_file() else ""
    entries = entries_named_by_test(source, test_source)[:2]
    row["entries"] = entries
    if not entries:
        return {**row, "state": REFUSED_NO_ENTRY}

    proposals: list[dict[str, Any]] = []
    for entry in entries:
        try:
            found = ENGINE.proposals_for(source, entry, test_source, lessons, budget=TRIAL_CAP)
        except Exception as exc:  # noqa: BLE001 - a refusal is a finding, never a crash
            row.setdefault("engine_errors", []).append(f"{entry}: {type(exc).__name__}: {str(exc)[:120]}")
            continue
        for proposal in found:
            proposals.append({**proposal, "entry": entry})
        if len(proposals) >= TRIAL_CAP:
            break
    row["proposals"] = len(proposals)
    row["origins"] = sorted({proposal.get("origin", "?") for proposal in proposals})
    if task.get("repaired") is not None:
        hunk = changed_span(source, task["repaired"])
        row["hunk"] = hunk
        row["site_hits"] = [proposal.get("rank", position) for position, proposal in enumerate(proposals)
                            if touches(changed_span(source, proposal["source"]), hunk)]
        row["any_site_hit"] = bool(row["site_hits"])
    if not proposals:
        return {**row, "state": REFUSED_NO_PROPOSAL}

    row["trials"] = 0
    for proposal in proposals[:TRIAL_CAP]:
        outcome = G.try_candidate(tree, source_rel, test_rel, proposal["source"])
        row["trials"] += 1
        if outcome["passed"]:
            return {**row, "state": SOLVED, "origin": proposal.get("origin"),
                    "entry": proposal.get("entry"), "score": round(float(proposal.get("score") or 0.0), 2),
                    "evidence": evidence}
    return {**row, "state": FAILED}


def measure(tasks: Sequence[Mapping[str, Any]], pairs: Mapping[str, Sequence[tuple[str, str, str]]],
            control: bool = True) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    repaired = {f"{entry['sha']}|{entry['source']}": entry["repaired"]
                for entry in getattr(measure, "grammar", [])}
    for task in tasks:
        teaching = [pair for name, group in pairs.items() if name != task["name"] for pair in group]
        lessons, learned = learn_lessons(teaching)
        task = {**task, "repaired": repaired.get(f"{task['sha']}|{task['source']}")}
        row = repair_task(task, lessons)
        row["lessons"] = learned
        if control:
            empty, _ = learn_lessons([])
            row["without_vocabulary"] = repair_task(task, empty)["state"]
        rows.append(row)
    return summarise(rows)


def summarise(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    states: dict[str, int] = {}
    for row in rows:
        states[row["state"]] = states.get(row["state"], 0) + 1
    solved = states.get(SOLVED, 0)
    control = {"SOLVED": 0, "FAILED": 0, "REFUSED": 0}
    for row in rows:
        verdict = row.get("without_vocabulary")
        if verdict is None:
            continue
        if verdict == SOLVED:
            control["SOLVED"] += 1
        elif verdict.startswith("REFUSED__"):
            control["REFUSED"] += 1
        else:
            control["FAILED"] += 1
    return {
        "schema": SCHEMA, "rows": list(rows), "model_calls": MODEL_CALLS, "network_calls": NETWORK_CALLS,
        "authority": "NONE -- sandbox measurement, not independent verification",
        "totals": {"tasks": len(rows), "states": states, "solved": solved,
                   "solved_fraction": round(solved / len(rows), 4) if rows else 0.0,
                   "trials": sum(row.get("trials", 0) for row in rows),
                   "proposals": sum(row.get("proposals", 0) for row in rows),
                   "tasks_proposing": sum(1 for row in rows if row.get("proposals")),
                   "tasks_with_site_hit": sum(1 for row in rows if row.get("any_site_hit")),
                   "site_hit_ranks": sorted(rank for row in rows for rank in row.get("site_hits", [])),
                   "without_vocabulary": control,
                   "lessons": sorted({row.get("lessons") for row in rows})},
    }


def headline(report: Mapping[str, Any]) -> str:
    totals = report["totals"]
    states = totals["states"]
    control = totals["without_vocabulary"]
    return (f"{totals['tasks']} real fix commits, engine fed edit-kind lessons learned from OTHER repositories' "
            f"real diffs: {totals['solved']} solved ({totals['solved_fraction']}) in {totals['trials']} executions "
            f"over {totals['proposals']} proposals. With an EMPTY vocabulary (trace slice only): "
            f"{control['SOLVED']} solved. States: "
            + ", ".join(f"{state} {count}" for state, count in sorted(states.items())) + ".")


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
    payload = json.loads(args.manifest.read_text(encoding="utf-8"))
    pairs: dict[str, list[tuple[str, str, str]]] = {}
    for entry in payload.get("grammar", []):
        pairs.setdefault(entry["name"], []).append(
            (entry["sha"][:8] + ":" + entry["source"], entry["defective"], entry["repaired"]))
    tasks = SHAPE.prepare_corpus(args.manifest, args.hist, args.work, limit=args.limit)
    measure.grammar = payload.get("grammar", [])
    report = measure(tasks, pairs)
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(report, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        print(f"written: {args.json}")
    print(headline(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
