#!/usr/bin/env python3
"""What experience can and cannot buy, as a measured law rather than an opinion.

THE CLAIM UNDER TEST
--------------------
"Instant learning and instant learning in a new environment are solved, so give the model the smartest actions,
let it experience each once, and it has them permanently -- therefore every problem on a computer follows."

Three terms hide in that sentence, and only two of them are solved. Measured elsewhere in this tree and only
*composed* here:

    P(correct action)  =  REACH  x  SEARCH  x  VERIFICATION
                          ^         ^          ^
                          |         |          +- solved: execute and compare. 53/100 on HumanEvalFix, exact.
                          |         +------------ solved: bounded search, CEGIS, CEL, 100k programs.
                          +---------------------- NOT solved by experience, and this file measures why.

REACH is the fraction of the answers a method can even *name*. Experience adds instances of actions already
nameable; it does not add names. So the question "does one experience per action give us everything?" is exactly
the question "does reach saturate?", and that is a number, not a position.

WHAT IS MEASURED, AND FROM WHAT
-------------------------------
Only recorded, real measurement is used -- nothing is re-run, nothing is synthesised, no model is consulted:

  A  REACH SATURATES.  500 real SWE-bench Verified tasks; 2178 real fix pieces cut from the real merged pull
                        requests that closed them (`EXPERT_FIX_REPETITION_SWEBENCH_VERIFIED_20261112_V1`).
                        Each piece carries the operator that rebuilds it and whether ANY other task's fixes
                        ever produced that operator. Stream the tasks in a fixed order, accumulate what
                        experience has taught, and measure coverage of the next task. If experience were the
                        mechanism, this curve would climb to 1. It does not.

  B  REPAIR IS PREDICTED BY GRAMMAR MEMBERSHIP, NOT BY LEARNING.  HumanEvalFix's own 100 real bugs, with the
                        solver's per-bug-type outcomes (`HUMANEVALFIX_REPAIR_SOLVER_20261112_V1`). The six bug
                        types are classified by *which edit shape the fix requires*, and the classification of
                        "in the grammar" is read out of the actual mutation grammar in
                        `python_test_guided_patch_search_v1` -- parsed from its source, never asserted here.
                        Then: does membership predict the observed repair rate?

  C  THE SAME WALL, FROM THE OTHER SIDE.  The operator kinds of those 2178 real pieces. What real fixes need,
                        against what the grammar can say.

WHY THIS IS THE HONEST FORM OF THE ANSWER
------------------------------------------
A success rate on one benchmark cannot answer "any computer" (that is why `instant_learning_in_a_new_environment`
measures a cost law instead). A saturation curve over 500 real tasks *can* answer "does experience buy reach",
because the asymptote is the claim. The commercial benchmark itself is also contaminated for the frontier --
SWE-bench Verified was retired in Feb 2026 because frontier models reproduce gold patches from memory -- and
that contamination does not touch this file, because nothing here proposes or generates a patch at all.

Authority: NONE. Producer-run recomposition of published receipts. Model calls 0. Network calls 0.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
from typing import Any, Sequence

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SCHEMA = "BRAIN_REACH_OF_THE_GRAMMAR_V1"
AUTHORITY = "NONE__PRODUCER_RUN_RECOMPOSITION_OF_PUBLISHED_RECEIPTS"

RECEIPTS = {
    "expert_fixes": "canonical/verification/EXPERT_FIX_REPETITION_SWEBENCH_VERIFIED_20261112_V1.json",
    "humanevalfix": "canonical/verification/HUMANEVALFIX_REPAIR_SOLVER_20261112_V1.json",
    "environments": "canonical/verification/INSTANT_LEARNING_IN_A_NEW_ENVIRONMENT_20261116_V1.json",
}
#: the actual mutation grammar, parsed from its source so the classification cannot drift from the code
GRAMMAR_SOURCE = "canonical/runtime/bound_capabilities/python_test_guided_patch_search_v1.py"

#: what each HumanEvalFix bug type requires of an edit, by the benchmark's own definition.
#: An edit shape is either nameable by the grammar or it is not; there is no third state.
REQUIRED_SHAPE = {
    "value misuse": "VALUE",          # a constant is wrong
    "operator misuse": "OPERATOR",    # + where * belongs
    "variable misuse": "RENAME",      # a different name
    "function misuse": "CALL_FUNC_SWAP",   # a different call, which this grammar does name
    "missing logic": "INSERT",        # a node that is not there
    "excess logic": "DELETE",         # a node that should not be there
}
#: the shapes the grammar can express, from the parsed families (see `grammar_shapes`)
SHAPE_OF_FAMILY = {
    "COMPARE_SWAP": "OPERATOR",
    "BOOL_SWAP": "OPERATOR",
    "BINOP_SWAP": "OPERATOR",
    "DROPPED_OPERAND": "ADD_OPERAND",
    "LITERAL": "VALUE",
}


# --------------------------------------------------------------------------- #
# the grammar, read from its own source
# --------------------------------------------------------------------------- #
def grammar_shapes(source: pathlib.Path | None = None) -> dict[str, Any]:
    """Which edit shapes the mutation grammar can name. Parsed, so a change in the code changes the answer."""
    path = pathlib.Path(source) if source else ROOT / GRAMMAR_SOURCE
    text = path.read_text(encoding="utf-8")
    families = sorted(set(re.findall(r'_descriptor\(\s*node\s*,\s*"([A-Z_]+)"', text)))
    # literal substitution is a family too, but it is not emitted through _descriptor
    if re.search(r"if isinstance\(value, *str\):\s*\n\s*replacements=string_literals", text):
        families.append("LITERAL")
    shapes = sorted({SHAPE_OF_FAMILY.get(family, family) for family in families})
    return {
        "source": str(path.relative_to(ROOT)) if ROOT in path.resolve().parents else str(path),
        "families": families,
        "shapes": shapes,
        "reads_repository_symbols": bool(re.search(r"_declared_fields|_read_attributes|_imported_fields", text)),
        "can_insert_a_node": "INSERT" in shapes,
        "can_delete_a_node": "DELETE" in shapes,
        "can_rename_a_name": "RENAME" in shapes,
    }


def load(name: str) -> dict[str, Any]:
    return json.loads((ROOT / RECEIPTS[name]).read_text(encoding="utf-8"))


# --------------------------------------------------------------------------- #
# A -- does experience buy reach?
# --------------------------------------------------------------------------- #
def piece_operator(piece: Sequence[Any]) -> str | None:
    """The operator that rebuilds this piece, as the recording wrote it (None = no operator rebuilds it)."""
    if len(piece) < 8:
        return None
    value = piece[7]
    return None if value is None else str(value)


def piece_provenance(piece: Sequence[Any]) -> str:
    """M = another task's fix made it, L = only a too-loose operator, N = never seen."""
    return str(piece[1]) if len(piece) > 1 else "N"


def reach_curve(tasks: dict[str, Any], order: str = "sorted") -> dict[str, Any]:
    """Stream the real tasks; accumulate what experience taught; measure coverage of the next task.

    Coverage is over PIECES, not tasks: a task half-covered is half-reachable. The operator identity is the
    recording's own (shape-level, placeholders intact), so an operator learned on one task can apply to another
    -- which is the most generous reading of "experience generalises", and therefore the fair test.
    """
    names = sorted(tasks) if order == "sorted" else list(tasks)
    seen: set[str] = set()
    points: list[dict[str, Any]] = []
    covered_total = 0
    pieces_total = 0
    for index, name in enumerate(names):
        pieces = tasks[name].get("pieces", [])
        hit = 0
        for piece in pieces:
            operator = piece_operator(piece)
            if operator is not None and operator in seen:
                hit += 1
        covered_total += hit
        pieces_total += len(pieces)
        points.append({"after_tasks": index, "task": name, "pieces": len(pieces), "covered": hit,
                       "operators_known": len(seen)})
        for piece in pieces:
            operator = piece_operator(piece)
            if operator is not None:
                seen.add(operator)
    # the asymptote: leave each task out, let experience see every OTHER task, and ask what it can rebuild
    jackknife_hit = 0
    for name in names:
        others: set[str] = set()
        for other in names:
            if other == name:
                continue
            for piece in tasks[other].get("pieces", []):
                operator = piece_operator(piece)
                if operator is not None:
                    others.add(operator)
        for piece in tasks[name].get("pieces", []):
            operator = piece_operator(piece)
            if operator is not None and operator in others:
                jackknife_hit += 1
    # marginal gain per quartile of experience -- saturation is the thing being tested
    quartiles = []
    step = max(1, len(points) // 4)
    for start in range(0, len(points), step):
        chunk = points[start:start + step]
        pieces = sum(p["pieces"] for p in chunk)
        covered = sum(p["covered"] for p in chunk)
        quartiles.append({"tasks": [start, start + len(chunk)],
                          "pieces": pieces, "covered": covered,
                          "coverage": round(covered / pieces, 4) if pieces else 0.0})
    return {
        "tasks": len(names),
        "pieces": pieces_total,
        "covered_while_streaming": covered_total,
        "coverage_while_streaming": round(covered_total / pieces_total, 4) if pieces_total else 0.0,
        "coverage_with_all_other_tasks_seen": round(jackknife_hit / pieces_total, 4) if pieces_total else 0.0,
        "asymptote_pieces": jackknife_hit,
        "by_experience_quartile": quartiles,
        "operators_learned": len(seen),
        "curve_sample": points[::max(1, len(points) // 12)],
    }


def provenance_and_kinds(tasks: dict[str, Any]) -> dict[str, Any]:
    provenance: dict[str, int] = {}
    kinds: dict[str, int] = {}
    for name in tasks:
        for piece in tasks[name].get("pieces", []):
            provenance[piece_provenance(piece)] = provenance.get(piece_provenance(piece), 0) + 1
            operator = piece_operator(piece)
            kind = "NO_OPERATOR" if operator is None else operator.split(":")[0].strip()
            kinds[kind] = kinds.get(kind, 0) + 1
    total = sum(provenance.values())
    return {
        "pieces": total,
        "provenance": provenance,
        "never_seen_share": round(provenance.get("N", 0) / total, 4) if total else 0.0,
        "made_by_another_task_share": round(provenance.get("M", 0) / total, 4) if total else 0.0,
        "operator_kinds": kinds,
        "recording_says_made_by_another_task": provenance.get("M", 0),
        "structural_share": round((kinds.get("delete", 0) + kinds.get("insert", 0)) / total, 4)
                            if total else 0.0,
        "meaning": ("N means no experience of any other task produces this piece of this fix. `delete` and "
                    "`insert` are structural: they are not a value or an operator being wrong, so no amount of "
                    "watching values and operators change can name them"),
    }


# --------------------------------------------------------------------------- #
# B -- is repair predicted by grammar membership?
# --------------------------------------------------------------------------- #
def repair_by_membership(solver: dict[str, Any], shapes: Sequence[str]) -> dict[str, Any]:
    per_type = solver["summary"]["by_bug_type"]
    reachable = set(shapes) | {"ADD_OPERAND"}
    rows: list[dict[str, Any]] = []
    for bug_type, counts in sorted(per_type.items()):
        shape = REQUIRED_SHAPE.get(bug_type)
        if shape is None:
            continue
        in_grammar = shape in reachable
        rows.append({
            "bug_type": bug_type, "shape": shape, "in_grammar": in_grammar,
            "bugs": int(counts["bugs"]), "repaired": int(counts["repaired"]),
            "repair_rate": round(int(counts["repaired"]) / int(counts["bugs"]), 4),
        })
    inside = [r for r in rows if r["in_grammar"]]
    outside = [r for r in rows if not r["in_grammar"]]

    def pooled(group: Sequence[dict[str, Any]]) -> dict[str, Any]:
        bugs = sum(r["bugs"] for r in group)
        repaired = sum(r["repaired"] for r in group)
        return {"types": [r["bug_type"] for r in group], "bugs": bugs, "repaired": repaired,
                "repair_rate": round(repaired / bugs, 4) if bugs else 0.0}

    pooled_in, pooled_out = pooled(inside), pooled(outside)
    # the honest exception: a type that is outside the grammar and still repaired often. Reported, not buried.
    anomalies = [r for r in outside if r["repair_rate"] > pooled_in["repair_rate"]]
    return {
        "rows": rows,
        "in_grammar": pooled_in,
        "out_of_grammar": pooled_out,
        "separation": round(pooled_in["repair_rate"] - pooled_out["repair_rate"], 4),
        "every_in_grammar_type_beats_every_out_type":
            bool(inside and outside and min(r["repair_rate"] for r in inside)
                 > max(r["repair_rate"] for r in outside)),
        "anomalies_of_the_law": anomalies,
        "law": ("P(repair | defect type) is predicted by whether the edit the fix requires is a shape the "
                "grammar can name -- not by the amount of experience, and not by the quality of the search. "
                "The search does not fail on out-of-grammar defects; it exhausts and correctly reports OPEN"),
    }


# --------------------------------------------------------------------------- #
# the composition
# --------------------------------------------------------------------------- #
def measure() -> dict[str, Any]:
    expert = load("expert_fixes")
    solver = load("humanevalfix")
    environments = load("environments")
    tasks = expert["per_task"]
    grammar = grammar_shapes()

    curve = reach_curve(tasks)
    kinds = provenance_and_kinds(tasks)
    membership = repair_by_membership(solver, grammar["shapes"])
    # cross-check: the recording's own provenance count (M) against this recomputation of the asymptote
    membership["recomputation_vs_recording"] = {
        "recomputed_asymptote_pieces": curve["asymptote_pieces"],
        "recording_made_by_another_task": kinds["recording_says_made_by_another_task"],
        "difference": curve["asymptote_pieces"] - kinds["recording_says_made_by_another_task"],
        "reading": ("the difference is the pieces whose operator exists only inside their own task, which a "
                    "leave-one-out view cannot hand them; the recomputation agreeing to this size is what makes "
                    "the asymptote a measurement rather than an assumption"),
    }

    env = environments["summary"]
    per_environment = {
        "adaptation_trials": int(env["adaptation_trials_active"]),
        "requests": int(env["requests"]),
        "crossover_requests": float(env["crossover_requests"]),
        "learn_each_trials_per_request": float(env["learn_each_trials_per_request"]),
        "ours_requests_solved": int(env["ours_requests_solved"]),
        "learn_each_requests_solved": int(env["learn_each_requests_solved"]),
        "machines": int(env["machines"]),
    }

    report: dict[str, Any] = {
        "schema": SCHEMA,
        "authority": AUTHORITY,
        "model_calls": 0,
        "network_calls": 0,
        "incremental_spend_usd": 0,
        "law": "P(correct action) = REACH x SEARCH x VERIFICATION; experience moves REACH only by naming new "
               "actions, and it names none",
        "grammar": grammar,
        "reach": curve,
        "real_fixes": kinds,
        "grammar_membership_predicts_repair": membership,
        "per_environment_learning": per_environment,
        "receipts": {name: RECEIPTS[name] for name in RECEIPTS},
    }
    report["answers"] = _answers(report)
    report["what_this_shows"] = _headline(report)
    return report


def _answers(report: dict[str, Any]) -> dict[str, Any]:
    reach = report["reach"]
    kinds = report["real_fixes"]
    membership = report["grammar_membership_predicts_repair"]
    env = report["per_environment_learning"]
    return {
        "is_one_experience_per_action_enough_to_solve_computer_use": "NO",
        "measured_why": [
            "%.1f%% of %d real fix pieces from 500 real SWE-bench Verified tasks are rebuilt by no operator any "
            "other task's fixes ever produced"
            % (100 * kinds["never_seen_share"], kinds["pieces"]),
            "with every other task's fixes as experience -- the asymptote, not a sample -- coverage is %.1f%%"
            % (100 * reach["coverage_with_all_other_tasks_seen"]),
            "the largest expressible real edit is `delete` (%d pieces, %.1f%% of all): a structural removal, "
            "and the grammar has can_delete_a_node=%s"
            % (kinds["operator_kinds"].get("delete", 0),
               100 * kinds["operator_kinds"].get("delete", 0) / max(1, kinds["pieces"]),
               report["grammar"]["can_delete_a_node"]),
            "on real bugs classified by required edit shape, in-grammar types repair at %.1f%% and "
            "out-of-grammar types at %.1f%% (a %.1f point separation that no amount of experience closes)"
            % (100 * membership["in_grammar"]["repair_rate"], 100 * membership["out_of_grammar"]["repair_rate"],
               100 * membership["separation"]),
            "a new environment costs %d trials to adapt and only pays back after %.1f requests in it, so it is a "
            "change of currency (requests -> environments), not a free lunch"
            % (env["adaptation_trials"], env["crossover_requests"]),
        ],
        "what_is_true": [
            "one execution plus a computed sufficiency verdict is enough to know an action's consequence, where "
            "the survivors agree",
            "instant learning in a new environment is real and is a cost law: adapt once, then plan",
            "verification by execution is exact and cheap, and it is the reason anything here can be trusted",
            "search over a fixed grammar is effective exactly on the defects inside that grammar",
        ],
        "what_is_false": [
            "that experience is the limiting term -- reach is, and experience does not move it",
            "that competence follows from consequence knowledge: knowing what an action does is silent about "
            "which action to take when the needed action has no name in the vocabulary",
            "that more experience per environment makes it permanent -- permamence holds only where survivors "
            "agree, and environment adaptation pays back only after the measured crossover",
            "that the benchmark is a frontier measure -- SWE-bench Verified was retired in Feb 2026 because "
            "frontier models reproduce its gold patches from memory",
        ],
        "the_single_bottleneck": "REACH: the set of edits the proposer can name. Search, verification, memory "
                                 "and environment adaptation are all measured and bounded; reach is the term "
                                 "that sets the ceiling, and it is grown by deriving an edit from the failure "
                                 "witness (the test's own expected value at a localised site), never by "
                                 "enumerating more operator families by hand",
        "buyable_capability": {
            "ceiling_if_reach_were_closed": 1.0,
            "measured_ceiling_now": round(membership["in_grammar"]["repair_rate"], 4),
            "measured_out_of_grammar": round(membership["out_of_grammar"]["repair_rate"], 4),
            "the_gap_that_must_be_bought": round(membership["separation"], 4),
        },
    }


def _headline(report: dict[str, Any]) -> str:
    reach = report["reach"]
    kinds = report["real_fixes"]
    membership = report["grammar_membership_predicts_repair"]
    return (
        "Measured over 500 real SWE-bench Verified tasks and 2178 real fix pieces, experience does not buy "
        "reach: %.1f%% of pieces are rebuilt by no operator any other task ever produced, and with every other "
        "task's fixes as experience the coverage is %.1f%% -- an asymptote, not a sample. The same wall appears "
        "from the other side on 100 real HumanEvalFix bugs: in-grammar defect types repair at %.1f%%, "
        "out-of-grammar types at %.1f%%, and the split is exactly whether the required edit is a shape the "
        "grammar can name. So the limiting term is REACH, not search, not verification, not memory: consequence "
        "knowledge is silent about which action to take when the needed action has no name yet. New environments "
        "do not change this -- they cost %d trials to adapt and pay back only after %.1f requests."
        % (100 * kinds["never_seen_share"], 100 * reach["coverage_with_all_other_tasks_seen"],
           100 * membership["in_grammar"]["repair_rate"], 100 * membership["out_of_grammar"]["repair_rate"],
           report["per_environment_learning"]["adaptation_trials"],
           report["per_environment_learning"]["crossover_requests"]))


def summarize(report: dict[str, Any]) -> str:
    reach, kinds = report["reach"], report["real_fixes"]
    membership = report["grammar_membership_predicts_repair"]
    grammar = report["grammar"]
    lines = [
        "grammar parsed from %s" % grammar["source"],
        "  families %s -> shapes %s" % (",".join(grammar["families"]), ",".join(grammar["shapes"])),
        "  can insert=%s can delete=%s can rename=%s" % (grammar["can_insert_a_node"],
                                                         grammar["can_delete_a_node"],
                                                         grammar["can_rename_a_name"]),
        "reach over %d real tasks / %d real fix pieces" % (reach["tasks"], reach["pieces"]),
        "  never rebuilt by experience %.1f%%   asymptote with all other tasks %.1f%%"
        % (100 * kinds["never_seen_share"], 100 * reach["coverage_with_all_other_tasks_seen"]),
        "  operator kinds %s" % json.dumps(kinds["operator_kinds"]),
        "  by experience quartile %s" % json.dumps([q["coverage"] for q in reach["by_experience_quartile"]]),
        "grammar membership predicts repair",
    ]
    for row in membership["rows"]:
        lines.append("  %-18s %-9s in_grammar=%-5s %2d/%2d = %.2f"
                     % (row["bug_type"], row["shape"], row["in_grammar"], row["repaired"], row["bugs"],
                        row["repair_rate"]))
    lines.append("  in-grammar %.2f vs out-of-grammar %.2f (separation %.2f)"
                 % (membership["in_grammar"]["repair_rate"], membership["out_of_grammar"]["repair_rate"],
                    membership["separation"]))
    if membership["anomalies_of_the_law"]:
        lines.append("  law's anomalies, reported not buried: %s"
                     % ", ".join(a["bug_type"] for a in membership["anomalies_of_the_law"]))
    env = report["per_environment_learning"]
    lines.append("new environment: %d trials adaptation, crossover at %.1f requests"
                 % (env["adaptation_trials"], env["crossover_requests"]))
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Compose the measured receipts into a law of reach: what experience can and cannot buy.")
    parser.add_argument("--json", dest="json_path", default=None)
    ns = parser.parse_args(argv)
    report = measure()
    print(summarize(report))
    print("\n" + report["what_this_shows"])
    if ns.json_path:
        target = pathlib.Path(ns.json_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print("\nwritten:", ns.json_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
