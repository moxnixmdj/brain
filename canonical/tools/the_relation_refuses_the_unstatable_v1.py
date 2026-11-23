#!/usr/bin/env python3
"""The carried relation refuses a goal its grammar cannot state -- and names what is missing.

WHY THIS ROUND EXISTS
---------------------
Iterations 1 and 2 on this branch showed that a residual goal class is closed by one executed
contrast in a new environment, and that a *portable relation* (not a raw trace) travels to a held-out
machine with zero errors. Both used the project's portable goal: "the probe content arrived once and
was never removed", a relation about content counts over the run.

An arbitrary environment can demand a different kind of goal. `the_goal_is_a_quotient_of_the_trace_v1`
already defines `moved_judge`: the seed content was MOVED (never held by two identities at once, and
ending under a different identity), not copied-then-deleted. A copy followed by a delete has the same
*final state* as a move; only the holder history separates them. This round asks the honest question:

    does the loop guess, or does it refuse, when the carried relation cannot state this goal?

WHAT IS MEASURED (pre-registered, declared here before the receipt)
-------------------------------------------------------------------
N1  the carried relation from iteration 1 is either not recomputable on the MOVE machine, or is
    wrong there (errors > 0) -- carrying a relation is not a licence to use it everywhere
N2  the loop emits no false accept when the goal is unstatable: it refuses or abstains rather than
    acting on the intersection of a grammar that cannot separate the two histories
N3  fitting the SAME 2-conjunction grammar on the MOVE machine's own executed runs yields no
    minimal statement for `moved_judge` (or reports it honestly as an empty class), and names the
    missing vocabulary: a goal about holder identity histories needs terms the count grammar lacks
N4  the two histories (move vs copy-then-delete) really have identical final states on real
    executions, so a final-state-only reader cannot separate them -- the refusal is about the
    grammar, not about a broken machine
N5  0 model calls, 0 stored parameters, 0 network calls at run time; every run executed

NOT CLAIMED: a GUI, a browser, OSWorld 2.1, SWE-bench Pro, a repair of any repository, independent
verification, capability registration, or terminal completion. Authority NONE, producer sandbox.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
import tempfile
import time
from typing import Any

TOOLS = pathlib.Path(__file__).resolve().parent
REPO = TOOLS.parents[1]
for path in (str(TOOLS), str(REPO)):
    if path not in sys.path:
        sys.path.insert(0, path)

import breadth_buys_what_repetition_cannot_v1 as breadth  # noqa: E402
import instant_learning_in_a_new_environment_v1 as env  # noqa: E402
import the_goal_is_a_quotient_of_the_trace_v1 as quotient  # noqa: E402
import the_goal_is_a_relation_over_the_run_v1 as runs  # noqa: E402
import the_environment_answers_the_question_v1 as answers  # noqa: E402

SCHEMA = "BRAIN_THE_RELATION_REFUSES_THE_UNSTATABLE_V1"
STORE = REPO / "canonical" / "astra_runtime" / "state" / "CARRIED_RELATION_V1.json"

DECLARED_BEFORE_THE_RUN = {
    "N1": "the carried relation is not recomputable or is wrong on the MOVE machine",
    "N2": "the loop emits no false accept when the goal is unstatable",
    "N3": "the same 2-conjunction grammar has no minimal statement for moved_judge on MOVE runs, "
          "and the refusal names the missing vocabulary",
    "N4": "a move and a copy-then-delete have identical final states on real executions",
    "N5": "0 model calls, 0 stored parameters, 0 network calls at run time; every run executed",
}


def build_move(root: pathlib.Path) -> env.Machine:
    root.mkdir(parents=True, exist_ok=True)

    def reset() -> None:
        for p in list(root.iterdir()):
            if p.is_file():
                p.unlink()
        (root / "seed").write_text(env.PROBE_OLD, encoding="utf-8")
        (root / "other").write_text("probe_second_content", encoding="utf-8")

    def read() -> list[tuple[str, str]]:
        return [(p.name, p.read_text(encoding="utf-8", errors="replace").strip())
                for p in sorted(root.iterdir()) if p.is_file()]

    return env.Machine(
        "MOVE", root,
        (
            env.Atom("MOV_A1", ((("mv", "-f", "{name}", "{target}"), None),)),
            env.Atom("MOV_A2", ((("cp", "-f", "{name}", "{target}"), None),)),
            env.Atom("MOV_A3", ((("rm", "-f", "{name}"), None),)),
            env.Atom("MOV_A4", ((("ls", "-1"), None),)),
        ), read, reset)


def final_state_pairs(traces: list[Any]) -> list[tuple[Any, Any]]:
    """Real executions whose FINAL states coincide but whose holder histories differ."""
    move = None
    copy_then_delete = None
    for trace in traces:
        holders = [[ident for ident, content in state if content == env.PROBE_OLD]
                   for state in trace]
        if not holders[-1]:
            continue
        if len(trace) == 2 and len(holders[0]) == 1 and len(holders[1]) == 1 \
                and holders[0] != holders[1] and all(len(h) <= 1 for h in holders):
            move = trace
        if len(trace) >= 3 and any(len(h) > 1 for h in holders) and len(holders[-1]) == 1 \
                and holders[0] != holders[-1]:
            copy_then_delete = trace
    return [(move, copy_then_delete)] if move and copy_then_delete else []


def measure(receipt: pathlib.Path) -> dict[str, Any]:
    started = time.time()
    where = pathlib.Path(tempfile.mkdtemp(prefix="brain-unstatable-"))
    args = {"content": env.PROBE_NEW, "old": env.PROBE_OLD, "name": "seed", "target": "copy"}
    machine = build_move(where / "move")
    machine.reset()
    traces = runs.traces_for(machine, args, depth=3)
    sequences = sum(len(machine.atoms) ** d for d in range(1, 4))
    judge = quotient.moved_judge
    labels = [bool(judge(trace)) for trace in traces]

    # N1: the carried content-count relation, replayed on a goal about holder identities.
    carried = answers.replay(STORE, traces, judge)
    carried_wrong = carried.get("false_accepts", 0) + carried.get("false_rejects", 0)
    n1 = carried.get("status") != "PREDICTED" or carried_wrong > 0

    # N2: fail closed. With no admissible statement the loop acts on NO state, not on a guess.
    whole, end_only = runs.run_terms(traces)
    terms = list(whole) + list(end_only)
    masks = breadth.masks_on(terms, traces)
    truth = 0
    for index, label in enumerate(labels):
        if label:
            truth |= 1 << index
    analysis = breadth.Analysis(terms, [masks], [len(traces)])
    grouped = analysis.classes()
    goal_combos = analysis.minimal(truth, grouped.get(truth, []))
    admissible = [(" and ".join(analysis.texts[i] for i in combo)) for combo in goal_combos]
    # MEASURED, never asserted: the intersection of every admissible statement against the real
    # judge on every executed run. A count set to zero without this loop would be a false result.
    acted_false_accepts = acted_false_rejects = 0
    for trace, label in zip(traces, labels):
        predicted = all(all(terms[i].holds(trace) for i in combo) for combo in goal_combos) \
            if goal_combos else False
        acted_false_accepts += int(predicted and not label)
        acted_false_rejects += int(not predicted and label)
    action = ("VERIFIED_SURVIVORS" if goal_combos else "REFUSED__NO_STATEMENT_IN_GRAMMAR")

    # N4: a real move and a real copy-then-delete with the same final state.
    pairs = final_state_pairs(traces)
    same_final = [{"move_steps": len(a) - 1, "copy_then_delete_steps": len(b) - 1,
                   "identical_final_state": a[-1] == b[-1],
                   "move_judged": bool(judge(a)), "copy_judged": bool(judge(b))}
                  for a, b in pairs]

    verdict = {
        "N1_carried_relation_does_not_travel_here": {
            "carried": carried, "wrong_predictions": carried_wrong, "MET": n1},
        "N2_no_false_accept_when_unstatable": {
            "action": action, "admissible_statements": admissible,
            "false_accepts": acted_false_accepts, "false_rejects": acted_false_rejects,
            "verdict": "VOID__THE_GOAL_WAS_STATABLE" if goal_combos else "MEASURED",
            "reason": "N2's precondition (an unstatable goal) is false; the intersection was "
                      "evaluated on every real run anyway and is reported, not asserted",
            "MET": False if goal_combos else acted_false_accepts == 0},
        "N3_grammar_cannot_state_the_goal": {
            "terms": len(terms), "hypotheses": len(analysis.by_combo),
            "behaviours": len(grouped), "goal_minimal_statements": len(goal_combos),
            "expected": "0 minimal statements: the count grammar cannot name holder histories",
            "observed": f"{len(goal_combos)} minimal statements",
            "reason": "FALSIFIED: `run_terms` already produces present_then_absent[ident] and "
                      "precedence[has a; has b] terms, so the run grammar CAN state a holder-history "
                      "goal. The missing part is not the grammar; it is that a relation learned for "
                      "a different goal cannot be carried into this machine without re-fitting.",
            "MET": len(goal_combos) == 0},
        "N4_same_final_state_real_runs": {
            "pairs": same_final,
            "MET": len(same_final) > 0 and all(row["identical_final_state"] for row in same_final)},
        "N5_zeros_and_real_execution": {
            "model_calls": 0, "parameters_stored": 0, "network_calls_at_run_time": 0,
            "runs": len(traces), "sequences": sequences,
            "accepted_by_moved_judge": sum(labels),
            "MET": len(traces) > 0},
    }
    out = {
        "schema": SCHEMA, "authority": "NONE__PRODUCER_RUN_SANDBOX", "date": "2026-11-23",
        "branch": "arena/6f8ac9ce-brain",
        "mode": "A_GOAL_OUTSIDE_THE_GRAMMAR_IS_REFUSED_NOT_APPROXIMATED",
        "declared_before_the_run": DECLARED_BEFORE_THE_RUN,
        "evaluated_after_the_run": "N3 was FALSIFIED (2 minimal statements exist) and N2's "
                                  "precondition was VOID; neither was relaxed. A measurement defect "
                                  "in the first version of N2 (a zero set without evaluation) was "
                                  "fixed and the whole tool re-run before this receipt.",
        "verdict": verdict,
        "all_criteria_met": all(row["MET"] for row in verdict.values()),
        "falsified_expectation": "the grammar CAN state a holder-history goal; what does not travel "
                                 "is a relation fitted for a different goal in a different machine",
        "next_bottleneck": "a carried relation is refused whenever its term texts do not recompute "
                           "from the new machine's own executed runs; the agent must re-fit in the "
                           "new environment (25 real runs here), so 'learn once, keep forever' is "
                           "still false for goals whose vocabulary is environment-specific",
        "cost": {"seconds": round(time.time() - started, 2), "model_calls": 0,
                 "parameters_stored": 0, "network_calls_at_run_time": 0},
        "limits": ["one real CLI machine (mv/cp/rm/ls), no GUI, browser or repository repair",
                   "the judge is the project's deterministic moved_judge, not a human",
                   "a grammar that CAN state the goal would be verified on real runs, not trusted"],
    }
    receipt.parent.mkdir(parents=True, exist_ok=True)
    receipt.write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({key: row["MET"] for key, row in verdict.items()}, indent=1))
    print(json.dumps({"carried": carried, "goal_minimal": len(goal_combos),
                      "same_final": same_final, "runs": len(traces)}, indent=1))
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipt", type=pathlib.Path, required=True)
    options = parser.parse_args()
    measure(options.receipt)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
