"""How many different repairs pass the same suite? That number is what "permanent" cannot mean.

THE QUESTION THIS SETTLES
-------------------------
A real commit's own tests are the only exact verifier this project has, and every mechanism in the tree is
judged by them. But a suite asserts *outcomes*, not *intent*, so it can accept more than one implementation.
Round 11 hit this and called it underdetermination: its solver satisfied `pypa/packaging` 022ae6c6 at a
neighbouring guard while the human's diff sits elsewhere, and both passed 344 tests.

One anecdote is not a measurement. This instrument counts it: for each real fix commit, enumerate every
repair the predicate machinery can build, keep **all** that pass the suite, and report how many distinct
places and predicates the suite accepts. If a suite admits k repairs, then "learn it once and keep it
forever" is a statement about k behaviours, not about the one intent the human had.

WHAT IT REUSES, AND WHAT IT DOES NOT DO
---------------------------------------
    operand_invention_v1   differential, sites_from_parameter, separating_terms, bind, rewritten
    edit_kind_learner      try_candidate -- apply, judge, always restore
Nothing is re-derived here and nothing new is learned. The only new thing is the *set* rather than the first
hit, which is exactly what every previous round discarded.

WHAT IT DOES NOT CLAIM
----------------------
Two repairs at two guards are *distinct implementations*. This instrument does not claim they are
*observably different* on the suite's inputs -- if they were, the suite would already reject one. That is the
point: the suite cannot tell them apart, so the difference is a decision the specification never made.

Model calls 0, network calls 0. Authority NONE.
"""

from __future__ import annotations

import json
import pathlib
import sys
from typing import Any, Mapping, Sequence

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from canonical.swe_kernel import history_induced_edit_grammar_v1 as G  # noqa: E402
from canonical.swe_kernel import operand_invention_v1 as OPERAND  # noqa: E402
from canonical.swe_kernel import structural_rewrite_induction_v1 as SHAPE  # noqa: E402

SCHEMA = "BRAIN_PASSING_REPAIRS_VERSION_SPACE_V1"
MODEL_CALLS = 0
NETWORK_CALLS = 0
TRIAL_CAP = 48
SEAT_CAP = 4
TERM_CAP = 4

UNDERDETERMINED = "UNDERDETERMINED_SUITE_ADMITS_MANY"
UNIQUE = "UNIQUE_REPAIR"
REFUSED_NO_PARTITION = "REFUSED__NO_PARTITION"


def passing_repairs(task: Mapping[str, Any]) -> dict[str, Any]:
    """Every repair this machinery can build that passes the commit's own suite."""
    tree = pathlib.Path(task["parent_tree"])
    source_rel, test_rel = task["source"], task["test"]
    row: dict[str, Any] = {"repo": task["repo"], "sha": task["sha"], "source": source_rel}
    if not (tree / source_rel).is_file():
        return {**row, "state": REFUSED_NO_PARTITION, "passing": []}
    source = (tree / source_rel).read_text(encoding="utf-8", errors="replace")
    test_source = (tree / test_rel).read_text(encoding="utf-8", errors="replace") if (tree / test_rel).is_file() else ""
    found = OPERAND.differential(test_source, task.get("failed_nodes") or [], source)
    if not found["terms"]:
        return {**row, "state": REFUSED_NO_PARTITION, "passing": [], "parameters": found["parameters"]}
    seats = OPERAND.sites_from_parameter(source, found["parameters"])[:SEAT_CAP]
    passing: list[dict[str, Any]] = []
    trials = 0
    for line_of, condition in seats:
        for raw in found["terms"][:TERM_CAP]:
            term = OPERAND.bind(raw, line_of, source)
            for operator in ("or", "and"):
                candidate = OPERAND.rewritten(source, line_of, condition, term, operator)
                if candidate is None:
                    continue
                trials += 1
                if G.try_candidate(tree, source_rel, test_rel, candidate)["passed"]:
                    passing.append({"at_line": line_of, "condition": condition, "term": term,
                                    "operator": operator})
                if trials >= TRIAL_CAP:
                    break
            if trials >= TRIAL_CAP:
                break
        if trials >= TRIAL_CAP:
            break
    question = question_from_repairs(passing, source, found["failing"]) if len(passing) > 1 else None
    seats_used = sorted({item["at_line"] for item in passing})
    terms_used = sorted({item["term"] for item in passing})
    return {**row, "state": UNDERDETERMINED if len(passing) > 1 else (UNIQUE if passing else REFUSED_NO_PARTITION),
            "passing": passing, "distinct_seats": seats_used, "distinct_terms": terms_used,
            "trials": trials, "parameters": found["parameters"], "question": question}


def _message_at(source: str, line_of: int) -> str:
    """What the guard at `line_of` says when it fires -- the only thing that differs between these repairs."""
    import ast
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return ""
    for node in ast.walk(tree):
        if isinstance(node, ast.If) and node.lineno == line_of:
            for inner in ast.walk(node):
                if isinstance(inner, ast.Raise) and inner.exc is not None:
                    return ast.unparse(inner.exc)[:200]
    return ""


def question_from_repairs(passing: Sequence[Mapping[str, Any]], source: str,
                          failing: Sequence[Any]) -> dict[str, Any] | None:
    """The version space as one question in the user's own terms.

    The repairs differ in WHERE they refuse and therefore in WHAT the user is told. A non-technical user
    cannot answer "line 766 or line 775"; they can answer "which message should this input produce".
    """
    said: dict[str, list[dict[str, Any]]] = {}
    for repair in passing:
        message = _message_at(source, int(repair["at_line"]))
        said.setdefault(message or "(silent: no raise found)", []).append(
            {"at_line": repair["at_line"], "term": repair["term"], "operator": repair["operator"]})
    if len(said) < 2:
        return None
    return {"about_input": (failing or [None])[0], "options": sorted(said),
            "repairs_behind_each_option": {key: len(value) for key, value in said.items()},
            "note": "answering this collapses the version space; guessing picks one behaviour and calls it intent"}


def measure(tasks: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    rows = [passing_repairs(task) for task in tasks]
    states: dict[str, int] = {}
    for row in rows:
        states[row["state"]] = states.get(row["state"], 0) + 1
    plural = [row for row in rows if len(row.get("passing") or []) > 1]
    return {
        "schema": SCHEMA, "rows": rows, "model_calls": MODEL_CALLS, "network_calls": NETWORK_CALLS,
        "authority": "NONE -- sandbox measurement, not independent verification",
        "totals": {
            "tasks": len(rows), "states": states,
            "tasks_admitting_many": len(plural),
            "repairs_accepted_total": sum(len(row.get("passing") or []) for row in rows),
            "max_repairs_accepted": max((len(row.get("passing") or []) for row in rows), default=0),
            "seats_per_task": {row["sha"][:8]: len(row.get("distinct_seats") or []) for row in rows},
            "tasks_with_a_discriminating_question": sum(1 for row in rows if row.get("question")),
            "trials": sum(row.get("trials") or 0 for row in rows),
        },
    }


def headline(report: Mapping[str, Any]) -> str:
    totals = report["totals"]
    plural = [row for row in report["rows"] if len(row.get("passing") or []) > 1]
    detail = "; ".join(
        f"{row['repo'].split('/')[-1]} accepted {len(row['passing'])} repairs at "
        f"{len(row.get('distinct_seats') or [])} guard(s)" for row in plural)
    return (f"{totals['tasks']} real fix commits judged by their own tests: "
            f"{totals['tasks_admitting_many']} admit more than one passing repair "
            f"({totals['repairs_accepted_total']} repairs accepted in {totals['trials']} executions, "
            f"max {totals['max_repairs_accepted']} for one commit). States: "
            + ", ".join(f"{state} {count}" for state, count in sorted(totals["states"].items()))
            + (f". {detail}" if detail else "") + ".")


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
