#!/usr/bin/env python3
"""The environment answers the question: a residual is a missing contrast, not a missing word.

WHAT THE LAST ROUND LEFT OPEN (pre-registered, do not re-argue)
--------------------------------------------------------------
`BREADTH_BUYS_WHAT_REPETITION_CANNOT_20261201_V1.md` fitted one grammar over 555 executed runs of
three real machines and found that the user's goal still has **two minimal statements**:

    created_once[probe_new_content]
    monotone[probe_new_content] and final:count[probe_new_content]==1

It priced the residual as `log2(2) = 1` question *of the user*, with "the number of runs that can
pay it is zero", and pre-registered: build the intake, put both sentences to a user, and check that
the chosen sentence predicts a machine it was never fitted on.

`intake/PURPOSE_GATE_20261121_V1.md` then built typed-answer intake and measured, on a fourth real
machine (`BULK_COPY`, one atom creates two copies at once), **one real run that separates the two
statements**, with goal mismatches {1, 0}. It still asked a user to *choose a sentence*.

WHAT THIS ROUND TESTS, AND WHAT IT DELETES
-----------------------------------------
Both rounds treat the residual as a matter of words. It is not. It is a matter of **reachable
contrast**: no run of the three fitted machines separates the statements, but a fourth environment
can. The "right question" is therefore asked of the machine, not of the user and not of the web:

    FIT (3 machines)  ->  carry 2 relations as an external, deletable store
    ENTER a new environment  ->  SCAN it by executing its own atoms, read the states
    FIND a run on which the carried relations disagree  ->  ASK ONE JUDGMENT ON THAT RUN
    COLLAPSE the class to 1  ->  SAVE only the relation (never the trace)
    REPLAY on a held-out environment  ->  RE-DERIVE the relation's vocabulary from that machine
    REFUSE to guess where no separating run exists  ->  act on the intersection of survivors

The dialogue intake is deleted: no English parser, no candidate shown to the owner, no typed
selection, no "permanent" catalogue of actions. The oracle is the user's verdict on **one run**,
exactly the judgment primitive the earlier rounds already used (`portable_judge`); it never sees a
statement's text. Zero parameters, zero model calls, zero network calls at run time.

PRE-REGISTERED CRITERIA (structural, declared here before any receipt is written)
--------------------------------------------------------------------------------
H1  the fitted residual class is greater than one (confirmatory: reproduces the known residual)
H2  a new environment's executed runs contain at least one separating run; one judgment on a run
    collapses the class to one, at a cost no greater than ceil(log2(class)) judgments, with zero
    questions about statements
H3  the collapsed relation predicts the goal judge on a held-out environment never used to fit
    and never used to choose, with zero false accepts and zero false rejects; and the held-out
    environment contains at least one run where the discarded statement disagrees with the judge
    (otherwise the test has no teeth)
H4  an environment with no separating run produces zero questions, acts on the intersection of
    survivors, and has zero false accepts
H5  the surviving relation is stored externally, replays with zero re-fit, and deleting the store
    restores the residual class (knowledge can be removed without retraining)
H6  saving the exact runs/actions from the selecting environment does not generalize to the
    held-out environment (abstentions > 0), while the relation does not abstain (what to save)
H7  zero model calls, zero stored parameters, zero network calls at run time; every run executed
    by a real program; the local instant-knowledge tier does not decide the choice

NOT CLAIMED
-----------
Not OSWorld 2.1, not SWE-bench Pro, not Terminal-Bench 2.0, not a GUI/browser, not a registered
capability, not independent verification, not terminal completion. Three CLI machines at depths
5/4/4 for the fit, two further real CLI machines and real git for the tests. Authority: NONE,
producer-run sandbox. `truth.achieved` stays false.
"""
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import math
import pathlib
import sys
import tempfile
import time
from dataclasses import dataclass
from typing import Any, Callable, Mapping, Sequence

TOOLS = pathlib.Path(__file__).resolve().parent
REPO = TOOLS.parents[1]
for path in (str(TOOLS), str(REPO)):
    if path not in sys.path:
        sys.path.insert(0, path)

import breadth_buys_what_repetition_cannot_v1 as breadth  # noqa: E402
import instant_learning_in_a_new_environment_v1 as env  # noqa: E402
import the_goal_is_a_discriminator_v1 as demand  # noqa: E402
import the_goal_is_a_quotient_of_the_trace_v1 as quotient  # noqa: E402
import the_goal_is_a_relation_over_the_run_v1 as runs  # noqa: E402
import the_vocabulary_is_the_artifact_v1 as vocab  # noqa: E402

from canonical.runtime import local_guide_v1 as local_guide  # noqa: E402
from intake import residual_question_gate_v1 as gate  # noqa: E402

SCHEMA = "BRAIN_THE_ENVIRONMENT_ANSWERS_THE_QUESTION_V1"
STORE_SCHEMA = "BRAIN_CARRIED_RELATION_V1"
FIT_MACHINES = ("TARBALL", "FILESYSTEM", "SQLITE")
FIT_DEPTHS = {"TARBALL": 5, "FILESYSTEM": 4, "SQLITE": 4}
SELECT_NAME = "COPY_TWO"
HELD_OUT_NAME = "TEE_COPY"
NO_CONTRAST_NAME = "GIT"
SCAN_DEPTHS = {SELECT_NAME: 3, HELD_OUT_NAME: 3, NO_CONTRAST_NAME: 3}

Judge = Callable[[Any], bool]
Trace = tuple[tuple[tuple[str, str], ...], ...]


DECLARED_BEFORE_THE_RUN = {
    "H1": "the fitted residual class is greater than one",
    "H2": "a new environment's executed runs contain a separating run; one judgment on a run "
          "collapses the class to one within ceil(log2(class)) judgments and zero questions about statements",
    "H3": "the collapsed relation has zero false accepts and zero false rejects on a held-out "
          "environment, which contains at least one run where the discarded statement is wrong",
    "H4": "no separating run implies zero questions, intersection action, zero false accepts",
    "H5": "the relation is externally stored, replays with zero re-fit, and deleting the store "
          "restores the residual class",
    "H6": "exact saved runs/actions abstain on the held-out environment; the relation does not",
    "H7": "zero model calls, zero stored parameters, zero network calls at run time; every run "
          "executed; the local instant-knowledge tier does not decide the choice",
}


# --------------------------------------------------------------------------------------------------
# two further real machines. Both are built from real programs (sh, cp, tee, rm, ls); neither is
# used to fit the residual. COPY_TWO chooses, TEE_COPY is held out from both fit and choice.
# --------------------------------------------------------------------------------------------------

def _list_state(root: pathlib.Path) -> list[tuple[str, str]]:
    return [(p.name, p.read_text(encoding="utf-8", errors="replace").strip())
            for p in sorted(root.iterdir()) if p.is_file()]


def _reset_two_seeds(root: pathlib.Path) -> None:
    for p in list(root.iterdir()):
        if p.is_file():
            p.unlink()
    (root / "seed").write_text(env.PROBE_OLD, encoding="utf-8")
    (root / "seed2").write_text("probe_second_content", encoding="utf-8")


def build_copy_two(root: pathlib.Path) -> env.Machine:
    """One atom adds two copies in a single action (write + cp); three other atoms are ordinary."""
    root.mkdir(parents=True, exist_ok=True)
    return env.Machine(
        "COPY_TWO", root,
        (
            env.Atom("C2_A1", ((("sh", "-c", 'printf %s "$0" > "$1"', "{content}", "{name}"), None),)),
            env.Atom("C2_A2", ((("rm", "-f", "{name}"), None),)),
            env.Atom("C2_A3", ((("sh", "-c", 'printf %s "$0" > "$1" && cp "$1" "$2"',
                                 "{content}", "{name}", "{target}"), None),)),
            env.Atom("C2_A4", ((("ls", "-1"), None),)),
        ),
        lambda: _list_state(root), lambda: _reset_two_seeds(root))


def _reset_tee_seeds(root: pathlib.Path) -> None:
    """A genuinely different initial state: different identities, one more holder. A new
    environment never arrives with the old machine's exact file names."""
    for p in list(root.iterdir()):
        if p.is_file():
            p.unlink()
    (root / "alpha").write_text(env.PROBE_OLD, encoding="utf-8")
    (root / "beta").write_text("probe_second_content", encoding="utf-8")
    (root / "gamma").write_text("probe_third_content", encoding="utf-8")


def build_tee_copy(root: pathlib.Path) -> env.Machine:
    """A different implementation of the same effect (tee), plus real write/remove/inert atoms."""
    root.mkdir(parents=True, exist_ok=True)
    return env.Machine(
        "TEE_COPY", root,
        (
            env.Atom("TEE_A1", ((("sh", "-c", 'printf %s "$0" > "$1"', "{content}", "{name}"), None),)),
            env.Atom("TEE_A2", ((("rm", "-f", "{name}"), None),)),
            env.Atom("TEE_A3", ((("sh", "-c", 'printf %s "$0" | tee "$1" "$2" >/dev/null',
                                 "{content}", "{name}", "{target}"), None),)),
            env.Atom("TEE_A4", ((("sh", "-c", "true"), None),)),
        ),
        lambda: _list_state(root), lambda: _reset_tee_seeds(root))


BUILDERS = {SELECT_NAME: build_copy_two, HELD_OUT_NAME: build_tee_copy,
            NO_CONTRAST_NAME: env.build_git}


# --------------------------------------------------------------------------------------------------
# fit: reuse the breadth instrument verbatim; nothing new is learned here
# --------------------------------------------------------------------------------------------------

@dataclass(frozen=True)
class Fit:
    terms: list[demand.Term]
    combos: list[tuple[int, ...]]
    texts: list[str]
    runs: int
    hypotheses: int
    behaviours: int
    truth: int
    seconds: float


def fit_residual(where: pathlib.Path, depths: Mapping[str, int] | None = None) -> Fit:
    depths = dict(depths or FIT_DEPTHS)
    started = time.time()
    args = {"content": env.PROBE_NEW, "old": env.PROBE_OLD, "name": "seed", "target": "copy"}
    pools: dict[str, list[Trace]] = {}
    for name in FIT_MACHINES:
        machine = vocab.MACHINES[name](where / name.lower())
        machine.root.mkdir(parents=True, exist_ok=True)
        machine.reset()
        pools[name] = runs.traces_for(machine, args, depth=depths[name])
    terms = breadth.union_terms(pools)
    per_machine = {name: breadth.masks_on(terms, pools[name]) for name in FIT_MACHINES}
    truth_by = {name: breadth.judge_mask(pools[name]) for name in FIT_MACHINES}
    analysis = breadth.Analysis(terms, [per_machine[n] for n in FIT_MACHINES],
                                [len(pools[n]) for n in FIT_MACHINES])
    truth, offset = 0, 0
    for name in FIT_MACHINES:
        truth |= truth_by[name] << offset
        offset += len(pools[name])
    grouped = analysis.classes()
    combos = analysis.minimal(truth, grouped.get(truth, []))
    if not combos:
        raise RuntimeError("FIT_FAILED__NO_STATEMENT_HAS_THE_GOAL_BEHAVIOUR")
    return Fit(terms=terms, combos=combos,
               texts=[" and ".join(analysis.texts[i] for i in combo) for combo in combos],
               runs=offset, hypotheses=len(analysis.by_combo), behaviours=len(grouped),
               truth=truth, seconds=round(time.time() - started, 2))


def candidates_for(fit: Fit) -> list[gate.Candidate]:
    return gate.from_combos(fit.terms, fit.combos,
                            lambda combo: " and ".join(fit.terms[i].text for i in combo))


def term_texts(fit: Fit, combo: Sequence[int]) -> list[str]:
    return [fit.terms[int(i)].text for i in combo]


# --------------------------------------------------------------------------------------------------
# scan a new environment: every run is executed by a real program; no catalogue is stored
# --------------------------------------------------------------------------------------------------

def scan(where: pathlib.Path, name: str, *, depth: int) -> tuple[list[Trace], int, int]:
    args = {"content": env.PROBE_NEW, "old": env.PROBE_OLD, "name": "seed", "target": "copy"}
    machine = BUILDERS[name](where / name.lower())
    machine.root.mkdir(parents=True, exist_ok=True)
    machine.reset()
    traces = runs.traces_for(machine, args, depth=depth)
    sequences = sum(len(machine.atoms) ** d for d in range(1, depth + 1))
    return traces, sequences, len(machine.atoms)


def separating_runs(candidates: Sequence[gate.Candidate], traces: Sequence[Trace]) -> list[int]:
    return [i for i, trace in enumerate(traces)
            if len({bool(c.holds(trace)) for c in candidates}) > 1]


def ask_the_environment(candidates: Sequence[gate.Candidate], traces: Sequence[Trace],
                        judge: Judge) -> dict[str, Any]:
    """One judgment on ONE run. The judge never sees a statement or a candidate id."""
    indices = separating_runs(candidates, traces)
    if not indices:
        return {"schema": SCHEMA, "action": "NO_QUESTION", "separating_runs": 0,
                "judgments_on_runs": 0, "questions_about_statements": 0,
                "survivors": [c.text for c in candidates], "class": len(candidates)}
    # cheapest question: the shortest executed run that separates the survivors
    chosen_index = min(indices, key=lambda i: len(traces[i]))
    chosen = traces[chosen_index]
    verdict = bool(judge(chosen))
    survivors = [c for c in candidates if bool(c.holds(chosen)) == verdict]
    return {
        "schema": SCHEMA, "action": "COLLAPSED" if len(survivors) == 1 else "PARTIAL",
        "separating_runs": len(indices), "chosen_run_index": chosen_index,
        "chosen_run_steps": len(chosen) - 1,
        "judgment_on_the_run": verdict, "judgments_on_runs": 1,
        "questions_about_statements": 0,
        "survivors": [c.text for c in survivors], "class": len(survivors),
        "discarded": [c.text for c in candidates if c not in survivors],
        "surviving_candidates": survivors,
        "evidence_sha256": hashlib.sha256(repr(chosen).encode("utf-8")).hexdigest()[:16],
    }


# --------------------------------------------------------------------------------------------------
# knowledge lives outside the weights: a relation stored as TEXT, re-derived from the machine at use
# --------------------------------------------------------------------------------------------------

def save_relation(path: pathlib.Path, fit: Fit, combo: Sequence[int],
                  evidence: Mapping[str, Any]) -> dict[str, Any]:
    record = {
        "schema": STORE_SCHEMA,
        "relation": {"texts": term_texts(fit, combo), "operator": "and"},
        "fit": {"machines": list(FIT_MACHINES), "runs": fit.runs,
                "grammar_sha256": hashlib.sha256(
                    "\n".join(t.text for t in fit.terms).encode("utf-8")).hexdigest()[:16]},
        "evidence": {key: evidence[key] for key in
                     ("evidence_sha256", "judgment_on_the_run", "chosen_run_steps")},
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, indent=1) + "\n", encoding="utf-8")
    return record


def load_relation(path: pathlib.Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    record = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(record, dict) or record.get("schema") != STORE_SCHEMA:
        raise ValueError("STORE_SCHEMA_MISMATCH")
    return record


def replay(path: pathlib.Path, traces: Sequence[Trace], judge: Judge) -> dict[str, Any]:
    """Re-derive the relation's predicates from THIS machine's executed runs, then predict."""
    record = load_relation(path)
    if record is None:
        return {"status": "REFUSED__NO_CARRIED_RELATION", "abstentions": len(traces)}
    whole, end_only = runs.run_terms(traces)
    available = {term.text: term for term in list(whole) + list(end_only)}
    wanted = list(record["relation"]["texts"])
    missing = [text for text in wanted if text not in available]
    if missing:
        return {"status": "REFUSED__VOCABULARY_NOT_RECOMPUTED", "missing": missing,
                "abstentions": len(traces)}
    predicates = [available[text] for text in wanted]
    false_accepts = false_rejects = 0
    for trace in traces:
        predicted = all(p.holds(trace) for p in predicates)
        actual = bool(judge(trace))
        false_accepts += int(predicted and not actual)
        false_rejects += int(not predicted and actual)
    return {"status": "PREDICTED", "runs": len(traces), "abstentions": 0,
            "false_accepts": false_accepts, "false_rejects": false_rejects,
            "texts": wanted, "terms_recomputed_from_this_machine": len(available)}


def raw_experience_control(select_traces: Sequence[Trace], held_traces: Sequence[Trace],
                           judge: Judge) -> dict[str, Any]:
    """What saving the exact experience buys: a lookup that cannot answer an unseen run."""
    memory = {trace: bool(judge(trace)) for trace in select_traces}
    abstained = errors = false_accepts = 0
    for trace in held_traces:
        if trace not in memory:
            abstained += 1
            continue
        predicted = memory[trace]
        actual = bool(judge(trace))
        errors += int(predicted != actual)
        false_accepts += int(predicted and not actual)
    return {"status": "LOOKUP_OVER_EXACT_RUNS", "memorised_runs": len(memory),
            "held_out_runs": len(held_traces), "abstentions": abstained,
            "errors_on_answered": errors, "false_accepts": false_accepts,
            "exact_action_transfer": "NOT_APPLICABLE__ACTION_VOCABULARY_DIFFERS"}


def intersection_predictions(candidates: Sequence[gate.Candidate], traces: Sequence[Trace],
                             judge: Judge) -> dict[str, Any]:
    """Act only where every surviving statement accepts. No guess, no question."""
    false_accepts = false_rejects = 0
    for trace in traces:
        predicted = all(bool(c.holds(trace)) for c in candidates)
        actual = bool(judge(trace))
        false_accepts += int(predicted and not actual)
        false_rejects += int(not predicted and actual)
    return {"runs": len(traces), "survivors": len(candidates), "false_accepts": false_accepts,
            "false_rejects": false_rejects}


# --------------------------------------------------------------------------------------------------
# one measurement
# --------------------------------------------------------------------------------------------------

def measure(receipt: pathlib.Path, store: pathlib.Path, *,
            depths: Mapping[str, int] | None = None,
            scan_depths: Mapping[str, int] | None = None) -> dict[str, Any]:
    started = time.time()
    where = pathlib.Path(tempfile.mkdtemp(prefix="brain-env-answers-"))
    judge: Judge = quotient.portable_judge

    fit = fit_residual(where, depths)
    candidates = candidates_for(fit)

    # K1 instant knowledge: asked, completeness-gated, and never allowed to decide the choice.
    guide = local_guide.lookup(
        "which action creates two copies of the content in one step so created_once and monotone disagree",
        root=REPO, deadline_s=6.0)
    guide_row = {"status": guide.get("status"), "pass": bool(guide.get("pass")),
                 "documents": len(guide.get("documents") or []),
                 "decided_the_choice": False,
                 "reason": "a guide is K1 information; only an executed run's judgment decides"}

    scan_depths = dict(scan_depths or SCAN_DEPTHS)
    select_traces, select_sequences, select_atoms = scan(where, SELECT_NAME,
                                                         depth=scan_depths[SELECT_NAME])
    held_traces, held_sequences, held_atoms = scan(where, HELD_OUT_NAME,
                                                   depth=scan_depths[HELD_OUT_NAME])
    git_traces, git_sequences, git_atoms = scan(where, NO_CONTRAST_NAME,
                                                depth=scan_depths[NO_CONTRAST_NAME])

    question = ask_the_environment(candidates, select_traces, judge)
    collapsed = question["class"] == 1
    if collapsed:
        survivor = question["surviving_candidates"][0]
        combo = next(combo for combo in fit.combos
                     if " and ".join(fit.terms[i].text for i in combo) == survivor.text)
        saved = save_relation(store, fit, combo, question)
    else:
        combo, saved = (), None

    # H3: held-out prediction + a control that the discarded statement is actually wrong there.
    prediction = replay(store, held_traces, judge) if saved else {"status": "NO_RELATION"}
    discarded_wrong = 0
    if collapsed:
        for text in question["discarded"]:
            discarded = next(c for c in candidates if c.text == text)
            discarded_wrong += sum(bool(discarded.holds(t)) != bool(judge(t)) for t in held_traces)

    # H4: no separating run -> refuse to ask, act on the intersection.
    no_contrast = gate.decide(candidates, git_traces, goal_judge=judge)
    intersection = intersection_predictions(candidates, git_traces, judge)

    # H5: replay, then delete and show the residual returns.
    replay_before = prediction
    store_existed = store.exists()
    backup = store.read_bytes() if store_existed else None
    if store_existed:
        store.unlink()
    after_delete = replay(store, held_traces, judge)
    if backup is not None:
        store.write_bytes(backup)

    # H6: exact experience as memory.
    raw = raw_experience_control(select_traces, held_traces, judge)

    ceil_questions = max(1, math.ceil(math.log2(len(candidates)))) if len(candidates) > 1 else 0
    verdict = {
        "H1_residual_is_a_class": {"class": len(candidates), "texts": fit.texts,
                                   "MET": len(candidates) > 1},
        "H2_one_run_collapses_it": {
            "separating_runs": question["separating_runs"],
            "judgments_on_runs": question["judgments_on_runs"],
            "questions_about_statements": question["questions_about_statements"],
            "price_ceiling": ceil_questions, "class_after": question["class"],
            "chosen_run_steps": question.get("chosen_run_steps"),
            "MET": (question["separating_runs"] > 0 and collapsed
                    and question["judgments_on_runs"] <= ceil_questions
                    and question["questions_about_statements"] == 0)},
        "H3_held_out_prediction": {
            "prediction": prediction, "discarded_statement_wrong_on": discarded_wrong,
            "MET": (prediction.get("status") == "PREDICTED"
                    and prediction.get("false_accepts") == 0
                    and prediction.get("false_rejects") == 0
                    and prediction.get("abstentions") == 0
                    and discarded_wrong > 0)},
        "H4_no_contrast_refuses": {
            "gate_action": no_contrast["action"], "distinguishing_runs": no_contrast["distinguishing_runs"],
            "questions": no_contrast["questions"], "intersection": intersection,
            "MET": (no_contrast["action"] == gate.NO_QUESTION
                    and no_contrast["questions"] == 0
                    and intersection["false_accepts"] == 0)},
        "H5_external_deletable_relation": {
            "stored": bool(saved), "replay_status": replay_before.get("status"),
            "after_delete_status": after_delete.get("status"),
            "MET": (bool(saved) and replay_before.get("status") == "PREDICTED"
                    and after_delete.get("status") == "REFUSED__NO_CARRIED_RELATION")},
        "H6_what_to_save": {
            "raw_experience": raw, "relation_abstentions": prediction.get("abstentions"),
            "MET": raw["abstentions"] > 0 and prediction.get("abstentions") == 0},
        "H7_zeros_and_real_execution": {
            "model_calls": 0, "parameters_stored": 0, "network_calls_at_run_time": 0,
            "fit_runs": fit.runs, "fit_seconds": fit.seconds,
            "select_sequences": select_sequences, "select_atoms": select_atoms,
            "held_out_sequences": held_sequences, "held_out_atoms": held_atoms,
            "no_contrast_sequences": git_sequences, "no_contrast_atoms": git_atoms,
            "guide": guide_row,
            "MET": guide_row["decided_the_choice"] is False},
    }

    out = {
        "schema": SCHEMA, "authority": "NONE__PRODUCER_RUN_SANDBOX",
        "date": "2026-11-23", "branch": "arena/6f8ac9ce-brain",
        "mode": "ONE_NEW_ENVIRONMENT_PAYS_THE_RESIDUAL_WITH_AN_EXECUTED_RUN",
        "declared_before_the_run": DECLARED_BEFORE_THE_RUN,
        "question": {key: value for key, value in question.items()
                     if key != "surviving_candidates"},
        "fit": {"machines": list(FIT_MACHINES), "depths": dict(depths or FIT_DEPTHS),
                "runs": fit.runs, "terms": len(fit.terms), "hypotheses": fit.hypotheses,
                "behaviours": fit.behaviours, "residual_class": len(candidates),
                "residual_texts": fit.texts, "seconds": fit.seconds},
        "scan": {"select": {"machine": SELECT_NAME, "traces": len(select_traces),
                            "sequences": select_sequences},
                 "held_out": {"machine": HELD_OUT_NAME, "traces": len(held_traces),
                              "sequences": held_sequences},
                 "no_contrast": {"machine": NO_CONTRAST_NAME, "traces": len(git_traces),
                                 "sequences": git_sequences}},
        "carried_relation": saved,
        "verdict": verdict,
        "all_criteria_met": all(row["MET"] for row in verdict.values()),
        "cost": {"seconds": round(time.time() - started, 2), "model_calls": 0,
                 "parameters_stored": 0, "network_calls_at_run_time": 0},
        "limits": [
            "three CLI machines for the fit at depths 5/4/4; two more CLI machines and real git for the tests",
            "the judge is the project's deterministic stand-in for the user's verdict on a run; it never sees a statement",
            "the local instant-knowledge tier is asked but never decides; the web tier is not called",
            "not OSWorld 2.1, SWE-bench Pro, Terminal-Bench 2.0, GUI or browser; no independent verifier",
            "the carried relation's vocabulary must be recomputed from the new machine or replay refuses",
        ],
    }
    receipt.parent.mkdir(parents=True, exist_ok=True)
    receipt.write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({key: row["MET"] for key, row in verdict.items()}, indent=1))
    print(json.dumps({"residual": len(candidates), "collapsed": question["class"],
                      "held_out": prediction, "raw_abstentions": raw["abstentions"],
                      "seconds": out["cost"]["seconds"]}, indent=1))
    return out


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipt", type=pathlib.Path, required=True)
    parser.add_argument("--store", type=pathlib.Path,
                        default=REPO / "canonical" / "astra_runtime" / "state" /
                                "CARRIED_RELATION_V1.json")
    args = parser.parse_args(argv)
    measure(args.receipt, args.store)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
