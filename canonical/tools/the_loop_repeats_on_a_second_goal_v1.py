#!/usr/bin/env python3
"""The same loop closes a DIFFERENT residual in a DIFFERENT environment -- with no new parts.

Iteration 3 (this branch) found that a relation fitted for the content-count goal refuses on a
holder-history goal (`moved_judge`), and that the existing run grammar CAN state that goal with
**two** minimal statements:

    monotone[probe_seed_content] and present_then_absent[seed]
    no_decrease and present_then_absent[seed]

So the residual reappears. The honest response is not a bigger learner: it is to re-fit cheaply in
the new environment and repeat the identical loop. This round does that on real `mv/cp/rm` machines
with a fourth atom that removes an unrelated file (separating `monotone` from `no_decrease`), then
tests on a held-out machine whose fourth atom OVERWRITES the seed (cardinality constant, probe
content down). No parameters, no model, no network, no new mechanism.

PRE-REGISTERED (declared here before the receipt run)
----------------------------------------------------
P1  the second goal has its own residual class greater than one on the MOVE machine
P2  a new environment's executed runs separate the two carried relations; one judgment on a run
    collapses the class to one, with zero questions about statements
P3  the collapsed relation predicts moved_judge on a held-out environment with 0 false accepts,
    0 false rejects, 0 abstentions, and the discarded relation is wrong there at least once
P4  exact saved runs from the selecting environment abstain on the held-out environment; the
    relation does not
P5  0 model calls, 0 stored parameters, 0 network calls at run time; every run executed; the
    carried relation from iteration 1 still refuses on this goal (no cross-goal smuggling)

NOT CLAIMED: OSWorld 2.1, SWE-bench Pro, Terminal-Bench 2.0, GUI/browser, code repair, independent
verification, capability registration, terminal completion. Authority NONE, producer sandbox.
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
import the_relation_refuses_the_unstatable_v1 as unstatable  # noqa: E402

SCHEMA = "BRAIN_THE_LOOP_REPEATS_ON_A_SECOND_GOAL_V1"
OLD_STORE = REPO / "canonical" / "astra_runtime" / "state" / "CARRIED_RELATION_V1.json"

DECLARED_BEFORE_THE_RUN = {
    "P1": "the second goal has its own residual class greater than one",
    "P2": "one executed run in a new environment separates the carried relations; one judgment "
          "collapses the class to one with zero questions about statements",
    "P3": "the collapsed relation is exact on held-out runs and the discarded relation is wrong "
          "there at least once",
    "P4": "exact saved runs abstain on held-out; the relation does not",
    "P5": "zeros, all runs executed, and the iteration-1 relation still refuses on this goal",
}


def _list_state(root: pathlib.Path) -> list[tuple[str, str]]:
    return [(p.name, p.read_text(encoding="utf-8", errors="replace").strip())
            for p in sorted(root.iterdir()) if p.is_file()]


def _reset(root: pathlib.Path) -> None:
    for p in list(root.iterdir()):
        if p.is_file():
            p.unlink()
    (root / "seed").write_text(env.PROBE_OLD, encoding="utf-8")
    (root / "other").write_text("probe_second_content", encoding="utf-8")
    (root / "extra").write_text("probe_third_content", encoding="utf-8")


def build_extra(root: pathlib.Path) -> env.Machine:
    """A fourth atom removes an UNRELATED file: cardinality decreases, probe content does not."""
    root.mkdir(parents=True, exist_ok=True)
    return env.Machine(
        "EXTRA_FILE", root,
        (
            env.Atom("EXT_A1", ((("mv", "-f", "{name}", "{target}"), None),)),
            env.Atom("EXT_A2", ((("cp", "-f", "{name}", "{target}"), None),)),
            env.Atom("EXT_A3", ((("rm", "-f", "{name}"), None),)),
            env.Atom("EXT_A4", ((("rm", "-f", "extra"), None),)),
            env.Atom("EXT_A5", ((("ls", "-1"), None),)),
        ), lambda: _list_state(root), lambda: _reset(root))


def build_overwrite(root: pathlib.Path) -> env.Machine:
    """Held out: a fourth atom OVERWRITES the seed, so cardinality is constant and probe content falls."""
    root.mkdir(parents=True, exist_ok=True)
    return env.Machine(
        "OVERWRITE", root,
        (
            env.Atom("OVR_A1", ((("mv", "-f", "{name}", "{target}"), None),)),
            env.Atom("OVR_A2", ((("cp", "-f", "{name}", "{target}"), None),)),
            env.Atom("OVR_A3", ((("rm", "-f", "{name}"), None),)),
            env.Atom("OVR_A4", ((("sh", "-c", 'printf %s "$0" > seed',
                                  "replacement_content"), None),)),
            env.Atom("OVR_A5", ((("ls", "-1"), None),)),
        ), lambda: _list_state(root), lambda: _reset(root))


def fit_move(where: pathlib.Path) -> tuple[answers.Fit, list[Any]]:
    args = {"content": env.PROBE_NEW, "old": env.PROBE_OLD, "name": "seed", "target": "copy"}
    machine = unstatable.build_move(where / "move")
    machine.reset()
    traces = runs.traces_for(machine, args, depth=3)
    whole, end_only = runs.run_terms(traces)
    terms = list(whole) + list(end_only)
    masks = breadth.masks_on(terms, traces)
    truth = 0
    for index, trace in enumerate(traces):
        if quotient.moved_judge(trace):
            truth |= 1 << index
    analysis = breadth.Analysis(terms, [masks], [len(traces)])
    combos = analysis.minimal(truth, analysis.classes().get(truth, []))
    fit = answers.Fit(terms=terms, combos=combos,
                      texts=[" and ".join(analysis.texts[i] for i in combo) for combo in combos],
                      runs=len(traces), hypotheses=len(analysis.by_combo),
                      behaviours=len(analysis.classes()), truth=truth, seconds=0.0)
    return fit, traces


def carried_predicates(fit: answers.Fit, traces: list[Any]) -> tuple[list[tuple[str, Any]], list[str]]:
    """Re-derive every TERM of every carried conjunction from the new machine's own runs."""
    whole, end_only = runs.run_terms(traces)
    available = {term.text: term for term in list(whole) + list(end_only)}
    pairs: list[tuple[str, Any]] = []
    missing: list[str] = []
    for combo in fit.combos:
        texts = [fit.terms[i].text for i in combo]
        absent = [text for text in texts if text not in available]
        if absent:
            missing.extend(absent)
            continue
        parts = [available[text] for text in texts]
        pairs.append((" and ".join(texts),
                      lambda trace, parts=parts: all(p.holds(trace) for p in parts)))
    return pairs, missing


def measure(receipt: pathlib.Path) -> dict[str, Any]:
    started = time.time()
    where = pathlib.Path(tempfile.mkdtemp(prefix="brain-second-goal-"))
    store = where / "second_relation.json"
    judge = quotient.moved_judge
    args = {"content": env.PROBE_NEW, "old": env.PROBE_OLD, "name": "seed", "target": "copy"}

    fit, _ = fit_move(where)
    candidates = answers.candidates_for(fit)

    select = build_extra(where / "extra")
    select.reset()
    select_traces = runs.traces_for(select, args, depth=3)
    held = build_overwrite(where / "overwrite")
    held.reset()
    held_traces = runs.traces_for(held, args, depth=3)

    # carried texts -> predicates RE-DERIVED from the new machine, never trusted from the store
    pairs, missing = carried_predicates(fit, select_traces)
    if missing or len(pairs) != len(fit.combos):
        raise RuntimeError("SECOND_GOAL_TERMS_NOT_RECOMPUTED: " + repr(missing))
    carried = answers.gate.from_predicates(pairs)
    separating = answers.separating_runs(carried, select_traces)
    if not separating:
        raise RuntimeError("NO_SEPARATING_RUN_IN_THE_NEW_ENVIRONMENT")
    chosen_index = min(separating, key=lambda i: len(select_traces[i]))
    chosen = select_traces[chosen_index]
    verdict = bool(judge(chosen))
    survivors = [c for c in carried if bool(c.holds(chosen)) == verdict]
    discarded = [c for c in carried if c not in survivors]
    collapsed = len(survivors) == 1

    if collapsed:
        combo = next(combo for combo in fit.combos
                     if " and ".join(fit.terms[i].text for i in combo) == survivors[0].text)
        answers.save_relation(store, fit, combo,
                              {"evidence_sha256": "second-goal", "judgment_on_the_run": verdict,
                               "chosen_run_steps": len(chosen) - 1})
        prediction = answers.replay(store, held_traces, judge)
    else:
        prediction = {"status": "NOT_IDENTIFIED", "abstentions": len(held_traces)}
    discarded_wrong = sum(bool(c.holds(t)) != bool(judge(t))
                          for c in discarded for t in held_traces)

    raw = answers.raw_experience_control(select_traces, held_traces, judge)
    old_relation = answers.replay(OLD_STORE, held_traces, judge)

    # Name the failure, do not summarise it: which real runs did the survivor get wrong, and why.
    diagnostics: dict[str, Any] = {"false_reject_witnesses": 0, "named_cause": None}
    if collapsed:
        whole, end_only = runs.run_terms(held_traces)
        available = {term.text: term for term in list(whole) + list(end_only)}
        wanted = [fit.terms[i].text for i in combo]
        if all(text in available for text in wanted):
            parts = [available[text] for text in wanted]

            def survivor_holds(trace: Any) -> bool:
                return all(p.holds(trace) for p in parts)

            witnesses = [trace for trace in held_traces
                         if bool(judge(trace)) and not survivor_holds(trace)]
            recreated = [
                trace for trace in witnesses
                if any(ident == "seed" and content != env.PROBE_OLD
                       for ident, content in trace[-1])
                and any(ident == "copy" and content == env.PROBE_OLD
                        for ident, content in trace[-1])]
            diagnostics = {
                "false_reject_witnesses": len(witnesses),
                "witnesses_with_seed_recreated_under_different_content": len(recreated),
                "named_cause": ("the grammar has no term for `the holder of THIS content changed`; "
                                "present_then_absent[seed] is falsified when the identity seed is "
                                "re-created with different content after a real move")
                               if len(recreated) == len(witnesses) and witnesses else "UNKNOWN",
                "first_witness": [
                    {"state": [ident for ident, _content in state]}
                    for state in witnesses[0]] if witnesses else None,
            }

    verdict_rows = {
        "P1_second_goal_has_a_residual": {
            "class": len(candidates), "texts": fit.texts, "MET": len(candidates) > 1},
        "P2_one_run_collapses_it": {
            "separating_runs": len(separating), "chosen_run_steps": len(chosen) - 1,
            "judgments_on_runs": 1, "questions_about_statements": 0,
            "class_after": len(survivors), "MET": collapsed and len(separating) > 0},
        "P3_exact_on_held_out": {
            "prediction": prediction, "discarded_wrong": discarded_wrong,
            "MET": (prediction.get("status") == "PREDICTED"
                    and prediction.get("false_accepts") == 0
                    and prediction.get("false_rejects") == 0
                    and prediction.get("abstentions") == 0 and discarded_wrong > 0)},
        "P4_what_to_save": {
            "raw_abstentions": raw["abstentions"], "relation_abstentions": prediction.get("abstentions"),
            "MET": raw["abstentions"] > 0 and prediction.get("abstentions") == 0},
        "P5_zeros_and_no_cross_goal_smuggling": {
            "model_calls": 0, "parameters_stored": 0, "network_calls_at_run_time": 0,
            "old_relation_status": old_relation.get("status"),
            "fit_runs": fit.runs, "select_runs": len(select_traces), "held_runs": len(held_traces),
            "MET": old_relation.get("status") == "REFUSED__VOCABULARY_NOT_RECOMPUTED"},
    }
    out = {
        "schema": SCHEMA, "authority": "NONE__PRODUCER_RUN_SANDBOX", "date": "2026-11-23",
        "branch": "arena/6f8ac9ce-brain",
        "mode": "THE_SAME_LOOP_ON_A_SECOND_GOAL_AND_A_SECOND_RESIDUAL",
        "declared_before_the_run": DECLARED_BEFORE_THE_RUN,
        "fit": {"goal": "moved_judge", "runs": fit.runs, "class": len(candidates),
                "texts": fit.texts},
        "question": {"separating_runs": len(separating), "chosen_run_steps": len(chosen) - 1,
                     "judgment_on_the_run": verdict, "survivor": survivors[0].text if collapsed else None,
                     "discarded": [c.text for c in discarded]},
        "verdict": verdict_rows,
        "diagnostics_of_the_p3_failure": diagnostics,
        "all_criteria_met": all(row["MET"] for row in verdict_rows.values()),
        "cost": {"seconds": round(time.time() - started, 2), "model_calls": 0,
                 "parameters_stored": 0, "network_calls_at_run_time": 0},
        "limits": ["three real CLI machines (mv/cp/rm/ls/sh), no GUI, browser or code repair",
                   "the judge is the project's deterministic moved_judge, not a human",
                   "literal names seed/other/extra are shared so terms recompute; iteration 3 "
                   "measured the honest refusal when they are not"],
    }
    receipt.parent.mkdir(parents=True, exist_ok=True)
    receipt.write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({key: row["MET"] for key, row in verdict_rows.items()}, indent=1))
    print(json.dumps({"fit": fit.texts, "separating": len(separating),
                      "survivor": survivors[0].text if collapsed else None,
                      "prediction": prediction, "discarded_wrong": discarded_wrong}, indent=1))
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipt", type=pathlib.Path, required=True)
    options = parser.parse_args()
    measure(options.receipt)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
