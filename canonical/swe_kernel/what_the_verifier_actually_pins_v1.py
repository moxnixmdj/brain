"""How much of a real fix does its own verifier actually pin? The answer decides what "verified" means.

THE QUESTION, AND WHY IT COMES BEFORE ANY MORE CAPABILITY
---------------------------------------------------------
Every measurement this project has made since round 9 ends in the same sentence: *the commit's own tests
pass*. That sentence has been treated as "the change is correct". It has never been audited. A fix has
parts -- an import, a sentinel, a docstring, a new method, a validation, a `deepcopy` -- and a suite that
passes can require some of those parts and be completely indifferent to the rest.

Reverting ONE part of the human's own change is the cheapest honest mutant there is: it is not a synthetic
operator, it is a subset of real work, and the question it answers is exact.

    suite fails without the part   -> the part is PINNED. The verifier requires it.
    suite passes without the part  -> the part is UNPINNED. The verifier would have accepted the fix
                                      with that part missing, i.e. it would have accepted a bug.

So this instrument reports the fraction of each real fix that is actually certified. It separates cosmetic
parts (comments, docstrings, unused imports) from behavioural ones, because "unpinned docstring" is not a
defect in the verifier while "unpinned validation" is.

WHAT THIS IS NOT
----------------
It is not the tree's mutation gate (`python_review_diff_mutation_gate`), which perturbs changed lines with
generated operators to ask whether the suite *observes* them. This asks a different and prior question:
which parts of the change the verifier *requires*. A part can be observed and not required; a part can be
required and only weakly observed. The two instruments compose, and neither replaces the other.

CONTROLS, BECAUSE A ZERO HERE WOULD BE UNREADABLE WITHOUT THEM
-------------------------------------------------------------
Per task, before any hunk is judged: the parent state must FAIL the suite and the repaired state must PASS
it. If either control breaks, the task is refused by name (`REFUSED__CONTROL_BROKEN`) rather than counted.
Nothing is written unless `try_candidate` restores the tree, which it always does.

Model calls 0, network calls 0, subprocesses: one suite run per hunk, plus two controls. Authority NONE.
"""

from __future__ import annotations

import ast
import difflib
import json
import pathlib
import sys
from typing import Any, Mapping, Sequence

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from canonical.swe_kernel import history_induced_edit_grammar_v1 as G  # noqa: E402
from canonical.swe_kernel import structural_rewrite_induction_v1 as SHAPE  # noqa: E402

SCHEMA = "BRAIN_VERIFIER_PINNING_V1"
MODEL_CALLS = 0
NETWORK_CALLS = 0
HUNK_CAP = 8

FULLY_PINNED = "FULLY_PINNED"
PARTIALLY_PINNED = "PARTIALLY_PINNED__THE_VERIFIER_WOULD_ACCEPT_A_BUG"
NOTHING_PINNED = "NOTHING_PINNED__THE_FIX_IS_UNCERTIFIED"
REFUSED_CONTROL = "REFUSED__CONTROL_BROKEN"
REFUSED_NO_GRAMMAR = "REFUSED__NO_GRAMMAR"


def hunks(defective: str, repaired: str) -> list[dict[str, Any]]:
    """The real change, split into its parts, with the line ranges needed to revert one part at a time."""
    old, new = defective.splitlines(keepends=True), repaired.splitlines(keepends=True)
    matcher = difflib.SequenceMatcher(None, old, new, autojunk=False)
    found: list[dict[str, Any]] = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            continue
        found.append({"tag": tag, "old": (i1, i2), "new": (j1, j2),
                      "removed": "".join(old[i1:i2]), "added": "".join(new[j1:j2])})
    return found


def revert(repaired: str, defective: str, hunk: Mapping[str, Any]) -> str:
    """The repaired text with exactly one part of the change undone."""
    new = repaired.splitlines(keepends=True)
    old = defective.splitlines(keepends=True)
    j1, j2 = hunk["new"]
    i1, i2 = hunk["old"]
    return "".join(new[:j1] + old[i1:i2] + new[j2:])


def _non_code_lines(source: str) -> set[int]:
    """Lines that carry no executable meaning: blanks, comments, and string-expression docstrings."""
    skip: set[int] = set()
    for number, line in enumerate(source.splitlines(), start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            skip.add(number)
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return skip
    for node in ast.walk(tree):
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant) \
                and isinstance(node.value.value, str):
            for number in range(node.lineno, (getattr(node, "end_lineno", node.lineno) or node.lineno) + 1):
                skip.add(number)
    return skip


def typing_only(source: str, hunk: Mapping[str, Any]) -> bool:
    """An import whose names appear ONLY inside annotations is not runtime behaviour.

    `from __future__ import annotations` makes annotations lazy strings, so removing such an import changes
    nothing that executes. Counting it as an unpinned behavioural part would overstate the finding, and this
    instrument's whole value is that its number is not overstated.
    """
    added = [line for line in hunk["added"].splitlines() if line.strip().startswith(("import ", "from "))]
    if not added:
        return False
    names: set[str] = set()
    for line in added:
        body = line.split(" import ", 1)[-1]
        for piece in body.replace("(", " ").replace(")", " ").split(","):
            piece = piece.strip().split(" as ")[-1].strip()
            if piece.isidentifier():
                names.add(piece)
    if not names:
        return False
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return False
    annotated: set[str] = set()
    runtime: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.arg) and node.annotation is not None:
            annotated |= {inner.id for inner in ast.walk(node.annotation) if isinstance(inner, ast.Name)}
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.returns is not None:
            annotated |= {inner.id for inner in ast.walk(node.returns) if isinstance(inner, ast.Name)}
        elif isinstance(node, ast.AnnAssign) and node.annotation is not None:
            annotated |= {inner.id for inner in ast.walk(node.annotation) if isinstance(inner, ast.Name)}
    skip = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
            skip.add(id(node))
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
            runtime.add(node.id)
    return bool(names & annotated) and not bool(names & (runtime - annotated))


def is_behavioural(source: str, hunk: Mapping[str, Any]) -> bool:
    """A part is behavioural unless every line it adds or removes is a comment, blank or docstring."""
    skip = _non_code_lines(source)
    j1, j2 = hunk["new"]
    for number in range(j1 + 1, j2 + 1):          # 1-based line numbers of the added text
        if number not in skip:
            return True
    return bool(hunk["removed"].strip()) and hunk["tag"] == "delete"


def pin_task(task: Mapping[str, Any], grammar: Sequence[Mapping[str, Any]], cap: int = HUNK_CAP) -> dict[str, Any]:
    tree = pathlib.Path(task["parent_tree"])
    source_rel, test_rel = task["source"], task["test"]
    row: dict[str, Any] = {"repo": task["repo"], "sha": task["sha"], "source": source_rel}
    entry = next((g for g in grammar if g["sha"] == task["sha"] and g["source"] == source_rel), None)
    if entry is None:
        return {**row, "state": REFUSED_NO_GRAMMAR}
    defective, repaired = entry["defective"], entry["repaired"]
    if not (tree / source_rel).is_file():
        return {**row, "state": REFUSED_NO_GRAMMAR}

    # controls first: a measurement whose controls are broken is not a measurement
    screen = G.try_candidate(tree, source_rel, test_rel, defective)
    repair = G.try_candidate(tree, source_rel, test_rel, repaired)
    if screen["passed"] or not repair["passed"]:
        return {**row, "state": REFUSED_CONTROL, "parent_passed": screen["passed"],
                "fixed_passed": repair["passed"]}

    parts = hunks(defective, repaired)[:cap]
    judged: list[dict[str, Any]] = []
    for index, hunk in enumerate(parts):
        partial = revert(repaired, defective, hunk)
        verdict = G.try_candidate(tree, source_rel, test_rel, partial)
        judged.append({
            "part": index, "tag": hunk["tag"], "added_lines": hunk["added"][:600],
            "behavioural": is_behavioural(repaired, hunk),
            "typing_only": typing_only(repaired, hunk),
            "pinned": not verdict["passed"],          # the suite FAILS without it -> the verifier requires it
        })
    behavioural = [part for part in judged if part["behavioural"] and not part["typing_only"]]
    typing = [part for part in judged if part["typing_only"]]
    pinned_behavioural = [part for part in behavioural if part["pinned"]]
    if not judged:
        state = NOTHING_PINNED
    elif all(part["pinned"] for part in judged):
        state = FULLY_PINNED
    else:
        state = PARTIALLY_PINNED
    return {**row, "state": state, "parts": judged, "parts_count": len(judged),
            "behavioural_parts": len(behavioural), "behavioural_pinned": len(pinned_behavioural),
            "unpinned_behavioural": sum(1 for part in behavioural if not part["pinned"]),
            "unpinned_cosmetic": sum(1 for part in judged if not part["behavioural"] and not part["pinned"]),
            "unpinned_typing_only": sum(1 for part in typing if not part["pinned"]),
            "typing_only_parts": len(typing)}


def measure(tasks: Sequence[Mapping[str, Any]], grammar: Sequence[Mapping[str, Any]],
            cap: int = HUNK_CAP) -> dict[str, Any]:
    rows = [pin_task(task, grammar, cap) for task in tasks]
    states: dict[str, int] = {}
    for row in rows:
        states[row["state"]] = states.get(row["state"], 0) + 1
    judged = [row for row in rows if row.get("parts") is not None]
    parts = sum(row["parts_count"] for row in judged)
    pinned = sum(sum(1 for part in row["parts"] if part["pinned"]) for row in judged)
    behavioural = sum(row["behavioural_parts"] for row in judged)
    behavioural_pinned = sum(row["behavioural_pinned"] for row in judged)
    return {
        "schema": SCHEMA, "rows": rows, "model_calls": MODEL_CALLS, "network_calls": NETWORK_CALLS,
        "authority": "NONE -- sandbox measurement, not independent verification",
        "totals": {
            "tasks": len(rows), "states": states, "tasks_with_controls": len(judged),
            "parts": parts, "parts_pinned": pinned,
            "behavioural_parts": behavioural, "behavioural_pinned": behavioural_pinned,
            "unpinned_behavioural": behavioural - behavioural_pinned,
            "pinned_share_of_behavioural": (round(behavioural_pinned / behavioural, 3) if behavioural else None),
            "suite_executions": 2 * len(judged) + parts,
        },
    }


def headline(report: Mapping[str, Any]) -> str:
    totals = report["totals"]
    worst = [row for row in report["rows"] if row.get("unpinned_behavioural")]
    detail = "; ".join(f"{row['repo'].split('/')[-1]} {row['sha'][:8]}: {row['unpinned_behavioural']} of "
                       f"{row['behavioural_parts']} behavioural parts accepted without" for row in worst)
    return (f"{totals['tasks_with_controls']} real fixes audited against their own suites in "
            f"{totals['suite_executions']} executions: {totals['parts_pinned']} of {totals['parts']} parts are "
            f"required by the verifier, and of the {totals['behavioural_parts']} behavioural parts "
            f"{totals['behavioural_pinned']} are pinned "
            f"({totals['pinned_share_of_behavioural']}). States: "
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
    grammar = json.loads(args.manifest.read_text(encoding="utf-8"))["grammar"]
    report = measure(tasks, grammar)
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(report, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        print(f"written: {args.json}")
    print(headline(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
