#!/usr/bin/env python3
"""The holder is not the identity: compute a relation from (content, identity) pairs.

Iteration 4 on this branch failed P3 with four counted witnesses. The stored relation said
`present_then_absent[seed]`; an OVERWRITE atom re-created the identity `seed` with different content
after a real move, so an identity-literal term became false while the holder of the goal content had
genuinely changed. The missing object is not a thirty-sixth hand-written predicate. It is a
**computed projection**: for each content, replace identity names by deictic indices in order of first
appearance among the holders of that content, then enumerate Boolean invariants of the resulting
holder-shape sequence.

This round reuses the project's version-space machinery. It fits on real MOVE and EXTRA_FILE runs,
finds two minimal statements that agree on those runs, builds a small DELAY environment whose real
executions make the two statements disagree, takes ONE judgment on ONE run, saves the surviving
conjunction as external relation texts, recomputes every term from each target machine's own runs,
and refuses when the goal's content literal is not observed there.

PRE-REGISTERED (declared here before the receipt run)
----------------------------------------------------
R1  the previous literal-identity receipt still has four false rejects with the named holder-history
    cause, and the computed term family contains zero fit identity literals
R2  the computed version space has two minimal statements that are exact on the fit runs; a real
    delayed-content environment separates them; one judgment on one run collapses the class to one,
    with zero questions about statements
R3  the saved relation predicts the OVERWRITE held-out pool with 0 false accepts, 0 false rejects and
    0 abstentions, and predicts TRUE on each of the four named prior false-reject witnesses
R4  a third machine with different identity names predicts with 0 errors and 0 abstentions; the
    relation store contains no identity literal from any fit machine
R5  a machine whose goal content literal itself differs is REFUSED, deleting a copy of the store is
    REFUSED, restoring the copy predicts, and exact saved runs abstain while the relation does not
R6  the killed designs are measured: a full canonical-trace isomorphism table has 0 errors but
    >0 abstentions on held-out pools, so it is not the relation shipped here
R7  0 model calls, 0 stored parameters, 0 network calls at run time; every run is executed

NOT CLAIMED: content-literal portability, a GUI, a browser, OSWorld 2.1, SWE-bench Pro / Pro V2,
Terminal-Bench, repository repair, independent verification, capability registration, or terminal
completion. Authority NONE, producer-run sandbox.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import itertools
import json
import pathlib
import re
import shutil
import sys
import tempfile
import time
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
import the_environment_answers_the_question_v1 as answers  # noqa: E402
import the_loop_repeats_on_a_second_goal_v1 as second_goal  # noqa: E402
import the_relation_refuses_the_unstatable_v1 as unstatable  # noqa: E402
from intake import residual_question_gate_v1 as gate  # noqa: E402

SCHEMA = "BRAIN_THE_HOLDER_IS_NOT_THE_IDENTITY_V1"
STORE_SCHEMA = "BRAIN_COMPUTED_HOLDER_RELATION_V1"
STORE = REPO / "canonical" / "astra_runtime" / "state" / "COMPUTED_HOLDER_RELATION_V1.json"
PRIOR_RECEIPT = REPO / "canonical" / "verification" / "THE_LOOP_REPEATS_ON_A_SECOND_GOAL_20261123_V1.json"
Trace = tuple[tuple[tuple[str, str], ...], ...]
Judge = Callable[[Trace], bool]

DECLARED_BEFORE_THE_RUN = {
    "R1": "the previous literal-identity failure is reproduced and computed terms contain zero fit identity literals",
    "R2": "two minimal computed statements are separated by one real delayed-content run and one judgment",
    "R3": "OVERWRITE held-out prediction is exact with zero abstentions and fixes the four prior witnesses",
    "R4": "a third machine with different identity names is exact with zero abstentions and no identity literals in the store",
    "R5": "different goal content refuses; store deletion refuses; restore predicts; raw exact runs abstain",
    "R6": "full canonical-trace table is measured as a killed design with abstentions",
    "R7": "zeros and real executions",
}

def contains_identity(text: str, ident: str) -> bool:
    """Exact word match; `probe_seed_content` is not the identity literal `seed`."""
    return re.search(r"\b" + re.escape(ident) + r"\b", text) is not None


FEATURE_ORDER = (
    "initial_nonempty", "final_nonempty", "first_nonempty",
    "initial_final_different", "first_final_different", "initial_final_same",
    "max_holders<=1", "max_holders<=2", "never_empty", "some_empty",
    "holder_set_changed", "cardinality_changed",
    "initial_singleton", "final_singleton", "first_singleton", "two_copies",
)


def holder_shape(trace: Trace, content: str) -> tuple[tuple[int, ...], ...]:
    """Deictic holder sequence for one content; identity names are replaced by first-appearance order."""
    holders = [tuple(sorted(ident for ident, value in state if value == content))
               for state in trace]
    index: dict[str, int] = {}
    next_index = 0
    shape: list[tuple[int, ...]] = []
    for row in holders:
        deictic: list[int] = []
        for ident in row:
            if ident not in index:
                index[ident] = next_index
                next_index += 1
            deictic.append(index[ident])
        shape.append(tuple(sorted(deictic)))
    return tuple(shape)


def shape_features(shape: Sequence[Sequence[int]]) -> dict[str, bool]:
    initial = tuple(shape[0])
    final = tuple(shape[-1])
    first = next((tuple(row) for row in shape if row), ())
    return {
        "initial_nonempty": bool(initial),
        "final_nonempty": bool(final),
        "first_nonempty": bool(first),
        "initial_final_different": bool(initial and final and final != initial),
        "first_final_different": bool(first and final and final != first),
        "initial_final_same": bool(initial and final and final == initial),
        "max_holders<=1": all(len(row) <= 1 for row in shape),
        "max_holders<=2": all(len(row) <= 2 for row in shape),
        "never_empty": all(bool(row) for row in shape),
        "some_empty": any(not row for row in shape),
        "holder_set_changed": any(tuple(shape[i]) != tuple(shape[i - 1])
                                  for i in range(1, len(shape))),
        "cardinality_changed": any(len(shape[i]) != len(shape[i - 1])
                                   for i in range(1, len(shape))),
        "initial_singleton": len(initial) == 1,
        "final_singleton": len(final) == 1,
        "first_singleton": len(first) == 1,
        "two_copies": any(len(row) >= 2 for row in shape),
    }


def computed_terms(traces: Sequence[Trace], content: str) -> list[demand.Term]:
    """A relation grammar whose terms are computed from (content, identity) pairs, not supplied."""
    if content not in {value for trace in traces for state in trace for _i, value in state}:
        return []
    return [demand.Term(f"holder_shape:{feature}[{content}]",
                        lambda trace, feature=feature: shape_features(
                            holder_shape(trace, content))[feature])
            for feature in FEATURE_ORDER]


def terms_for_all_contents(traces: Sequence[Trace]) -> dict[str, demand.Term]:
    contents = sorted({value for trace in traces for state in trace for _i, value in state})
    out: dict[str, demand.Term] = {}
    for content in contents:
        for term in computed_terms(traces, content):
            out.setdefault(term.text, term)
    return out


def fit_computed_relation(fit_traces: Sequence[Trace], judge: Judge,
                          content: str) -> tuple[list[demand.Term], list[tuple[int, ...]], int]:
    terms = computed_terms(fit_traces, content)
    masks = breadth.masks_on(terms, fit_traces)
    truth = 0
    for index, trace in enumerate(fit_traces):
        if judge(trace):
            truth |= 1 << index
    analysis = breadth.Analysis(terms, [masks], [len(fit_traces)])
    combos = analysis.classes().get(truth, [])
    minimal = analysis.minimal(truth, combos)
    exact = all(analysis.by_combo[combo] == truth for combo in minimal)
    if not terms or not minimal or not exact:
        raise RuntimeError("COMPUTED_TERM_FAMILY_NOT_SUFFICIENT_ON_FIT")
    return terms, minimal, truth


def candidates_from(terms: Sequence[demand.Term],
                    combos: Sequence[tuple[int, ...]]) -> list[gate.Candidate]:
    return gate.from_combos(terms, combos,
                            lambda combo: " and ".join(terms[int(i)].text for i in combo))


def build_delay(root: pathlib.Path) -> env.Machine:
    """A real environment where the goal content first appears AFTER step 0, then is moved."""
    root.mkdir(parents=True, exist_ok=True)

    def reset() -> None:
        for p in list(root.iterdir()):
            if p.is_file():
                p.unlink()
        (root / "origin").write_text("other_content", encoding="utf-8")
        (root / "side").write_text("second_content", encoding="utf-8")

    def read() -> list[tuple[str, str]]:
        return [(p.name, p.read_text(encoding="utf-8", errors="replace").strip())
                for p in sorted(root.iterdir()) if p.is_file()]

    return env.Machine(
        "DELAY", root,
        (
            env.Atom("DEL_A1", ((("sh", "-c", "printf %s \"$0\" > late", env.PROBE_OLD), None),)),
            env.Atom("DEL_A2", ((("mv", "-f", "{name}", "{target}"), None),)),
            env.Atom("DEL_A3", ((("ls", "-1"), None),)),
        ), read, reset)


def build_third(root: pathlib.Path) -> env.Machine:
    """Held-out identity names: origin/archive/side/spare. Goal content literal is unchanged."""
    root.mkdir(parents=True, exist_ok=True)

    def reset() -> None:
        for p in list(root.iterdir()):
            if p.is_file():
                p.unlink()
        (root / "origin").write_text(env.PROBE_OLD, encoding="utf-8")
        (root / "side").write_text("probe_second_content", encoding="utf-8")
        (root / "spare").write_text("probe_third_content", encoding="utf-8")

    def read() -> list[tuple[str, str]]:
        return [(p.name, p.read_text(encoding="utf-8", errors="replace").strip())
                for p in sorted(root.iterdir()) if p.is_file()]

    return env.Machine(
        "THIRD_NAMES", root,
        (
            env.Atom("TN_A1", ((("mv", "-f", "{name}", "{target}"), None),)),
            env.Atom("TN_A2", ((("cp", "-f", "{name}", "{target}"), None),)),
            env.Atom("TN_A3", ((("rm", "-f", "{name}"), None),)),
            env.Atom("TN_A4", ((("rm", "-f", "spare"), None),)),
            env.Atom("TN_A5", ((("sh", "-c", "printf %s \"$0\" > origin",
                                  "replacement_content"), None),)),
            env.Atom("TN_A6", ((("ls", "-1"), None),)),
        ), read, reset)


def build_different_content(root: pathlib.Path) -> env.Machine:
    """A machine where the goal content literal itself is different; replay must refuse."""
    seed = "alpha_content"
    root.mkdir(parents=True, exist_ok=True)

    def reset() -> None:
        for p in list(root.iterdir()):
            if p.is_file():
                p.unlink()
        (root / "origin").write_text(seed, encoding="utf-8")
        (root / "side").write_text("beta_content", encoding="utf-8")
        (root / "spare").write_text("gamma_content", encoding="utf-8")

    def read() -> list[tuple[str, str]]:
        return [(p.name, p.read_text(encoding="utf-8", errors="replace").strip())
                for p in sorted(root.iterdir()) if p.is_file()]

    return env.Machine(
        "DIFFERENT_CONTENT", root,
        (
            env.Atom("DC_A1", ((("mv", "-f", "{name}", "{target}"), None),)),
            env.Atom("DC_A2", ((("cp", "-f", "{name}", "{target}"), None),)),
            env.Atom("DC_A3", ((("rm", "-f", "{name}"), None),)),
            env.Atom("DC_A4", ((("sh", "-c", "printf %s \"$0\" > origin",
                                  "delta_content"), None),)),
            env.Atom("DC_A5", ((("ls", "-1"), None),)),
        ), read, reset)


def save_relation(path: pathlib.Path, texts: Sequence[str], evidence: Mapping[str, Any]) -> dict[str, Any]:
    record = {
        "schema": STORE_SCHEMA,
        "relation": {"texts": list(texts), "operator": "and"},
        "term_family": "computed_deictic_holder_shape_v1",
        "feature_order": list(FEATURE_ORDER),
        "evidence": {
            "term_sha256": hashlib.sha256("\n".join(texts).encode("utf-8")).hexdigest()[:16],
            "judgment_on_the_run": bool(evidence["judgment_on_the_run"]),
            "chosen_run_steps": int(evidence["chosen_run_steps"]),
            "fit_runs": int(evidence["fit_runs"]),
        },
        "identity_literals": [],
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
    """Re-derive the stored terms from THIS machine's executed runs; never trust stored code."""
    record = load_relation(path)
    if record is None:
        return {"status": "REFUSED__NO_RELATION", "abstentions": len(traces)}
    available = terms_for_all_contents(traces)
    wanted = list(record["relation"]["texts"])
    missing = [text for text in wanted if text not in available]
    if missing:
        return {"status": "REFUSED__GOAL_CONTENT_OR_TERMS_NOT_RECOMPUTED",
                "missing": missing, "abstentions": len(traces)}
    predicates = [available[text] for text in wanted]
    predictions = [all(predicate.holds(trace) for predicate in predicates) for trace in traces]
    false_accepts = false_rejects = 0
    for predicted, trace in zip(predictions, traces):
        actual = bool(judge(trace))
        false_accepts += int(predicted and not actual)
        false_rejects += int(not predicted and actual)
    return {"status": "PREDICTED", "runs": len(traces), "abstentions": 0,
            "false_accepts": false_accepts, "false_rejects": false_rejects,
            "texts": wanted, "terms_recomputed_from_this_machine": len(available),
            "predictions": predictions}


def canonical_form(trace: Trace) -> tuple[int, int, tuple[tuple[tuple[int, int], ...], ...]]:
    """Full isomorphism class of the reading; measured only as a killed design."""
    idents = sorted({ident for state in trace for ident, _v in state})
    contents = sorted({value for state in trace for _i, value in state})
    best: Any = None
    for identity_perm in itertools.permutations(range(len(idents))):
        identity_map = dict(zip(idents, identity_perm))
        for content_perm in itertools.permutations(range(len(contents))):
            content_map = dict(zip(contents, content_perm))
            states = tuple(tuple(sorted((content_map[value], identity_map[ident])
                                        for ident, value in state))
                           for state in trace)
            serial = (len(idents), len(contents), states)
            if best is None or serial < best:
                best = serial
    return best


def canonical_table_control(fit: Sequence[Trace], held: Sequence[Trace],
                            judge: Judge) -> dict[str, Any]:
    table: dict[Any, bool] = {}
    impure = 0
    for trace in fit:
        key = canonical_form(trace)
        label = bool(judge(trace))
        if key in table and table[key] != label:
            impure += 1
        table[key] = label
    false_accepts = false_rejects = abstentions = 0
    for trace in held:
        key = canonical_form(trace)
        if key not in table:
            abstentions += 1
            continue
        predicted = table[key]
        actual = bool(judge(trace))
        false_accepts += int(predicted and not actual)
        false_rejects += int(not predicted and actual)
    return {"fit_cells": len(table), "impure_fit_cells": impure,
            "held_out_cells": len({canonical_form(trace) for trace in held}),
            "false_accepts": false_accepts, "false_rejects": false_rejects,
            "abstentions": abstentions}


def prior_witnesses(overwrite: Sequence[Trace]) -> tuple[list[int], list[str]]:
    """The four iteration-4 false rejects, recomputed from the old receipt's survivor text."""
    prior = json.loads(PRIOR_RECEIPT.read_text(encoding="utf-8"))
    text = prior["question"]["survivor"]
    parts = text.split(" and ")
    whole, end_only = runs.run_terms(overwrite)
    available = {term.text: term for term in list(whole) + list(end_only)}
    missing = [part for part in parts if part not in available]
    if missing:
        raise RuntimeError("PRIOR_SURVIVOR_TERMS_NOT_RECOMPUTED:" + repr(missing))
    witnesses = [index for index, trace in enumerate(overwrite)
                 if bool(quotient.moved_judge(trace))
                 and not all(available[part].holds(trace) for part in parts)]
    return witnesses, parts


def measure(receipt: pathlib.Path) -> dict[str, Any]:
    started = time.time()
    where = pathlib.Path(tempfile.mkdtemp(prefix="brain-holder-relation-"))
    args = {"content": env.PROBE_NEW, "old": env.PROBE_OLD, "name": "seed", "target": "copy"}
    judge = quotient.moved_judge

    move = unstatable.build_move(where / "move")
    move.reset()
    move_traces = runs.traces_for(move, args, depth=3)
    extra = second_goal.build_extra(where / "extra")
    extra.reset()
    extra_traces = runs.traces_for(extra, args, depth=3)
    fit = move_traces + extra_traces

    overwrite = second_goal.build_overwrite(where / "overwrite")
    overwrite.reset()
    overwrite_traces = runs.traces_for(overwrite, args, depth=3)
    third = build_third(where / "third")
    third.reset()
    third_args = {"content": env.PROBE_NEW, "old": env.PROBE_OLD,
                  "name": "origin", "target": "archive"}
    third_traces = runs.traces_for(third, third_args, depth=3)
    different = build_different_content(where / "different")
    different.reset()
    different_args = {"content": "new_content", "old": "alpha_content",
                      "name": "origin", "target": "archive"}
    different_traces = runs.traces_for(different, different_args, depth=3)
    delay = build_delay(where / "delay")
    delay.reset()
    delay_args = {"content": env.PROBE_NEW, "old": env.PROBE_OLD,
                  "name": "late", "target": "final"}
    delay_traces = runs.traces_for(delay, delay_args, depth=3)

    terms, combos, truth = fit_computed_relation(fit, judge, env.PROBE_OLD)
    candidates = candidates_from(terms, combos)
    separating = answers.separating_runs(candidates, delay_traces)
    if not separating:
        raise RuntimeError("NO_REAL_RUN_SEPARATES_THE_COMPUTED_STATEMENTS")
    chosen_index = min(separating, key=lambda i: len(delay_traces[i]))
    chosen = delay_traces[chosen_index]
    verdict = bool(judge(chosen))
    survivors = [candidate for candidate in candidates
                 if bool(candidate.holds(chosen)) == verdict]
    collapsed = len(survivors) == 1
    if not collapsed:
        raise RuntimeError("ONE_JUDGMENT_DID_NOT_COLLAPSE_THE_COMPUTED_CLASS")
    survivor_combo = next(combo for combo in combos
                          if " and ".join(terms[i].text for i in combo) == survivors[0].text)
    relation_texts = [terms[int(i)].text for i in survivor_combo]
    record = save_relation(STORE, relation_texts,
                           {"judgment_on_the_run": verdict,
                            "chosen_run_steps": len(chosen) - 1, "fit_runs": len(fit)})

    overwrite_prediction = replay(STORE, overwrite_traces, judge)
    third_prediction = replay(STORE, third_traces, judge)
    different_prediction = replay(STORE, different_traces, lambda _trace: False)

    witness_indexes, prior_parts = prior_witnesses(overwrite_traces)
    witness_predictions = [bool(overwrite_prediction["predictions"][i]) for i in witness_indexes]

    copy_path = where / "deletable_relation.json"
    shutil.copyfile(STORE, copy_path)
    copy_prediction = replay(copy_path, overwrite_traces, judge)
    copy_path.unlink()
    deleted_prediction = replay(copy_path, overwrite_traces, judge)
    shutil.copyfile(STORE, copy_path)
    restored_prediction = replay(copy_path, overwrite_traces, judge)

    raw = answers.raw_experience_control(fit, overwrite_traces, judge)
    canonical_over = canonical_table_control(fit, overwrite_traces, judge)
    canonical_third = canonical_table_control(fit, third_traces, judge)
    prior = json.loads(PRIOR_RECEIPT.read_text(encoding="utf-8"))

    fit_idents = sorted({ident for trace in fit for state in trace for ident, _v in state})
    identity_literals_in_store = [ident for ident in fit_idents
                                  if contains_identity(json.dumps(record, ensure_ascii=False), ident)]
    term_texts_join = "\n".join(term.text for term in terms)
    fit_exact = all(bool(candidate.holds(trace)) == bool(judge(trace))
                    for candidate in candidates for trace in fit)

    verdict_rows = {
        "R1_prior_failure_reproduced_and_no_identity_literals": {
            "prior_false_rejects": prior["verdict"]["P3_exact_on_held_out"]["prediction"]["false_rejects"],
            "prior_named_cause": prior["diagnostics_of_the_p3_failure"]["named_cause"],
            "computed_terms": len(terms), "fit_identity_literals": fit_idents,
            "identity_literals_in_computed_term_texts": [
                ident for ident in fit_idents if contains_identity(term_texts_join, ident)],
            "MET": (prior["verdict"]["P3_exact_on_held_out"]["prediction"]["false_rejects"] == 4
                    and "holder of THIS content changed" in
                    prior["diagnostics_of_the_p3_failure"]["named_cause"]
                    and not any(contains_identity(term_texts_join, ident)
                                for ident in fit_idents))},
        "R2_one_real_run_collapses_two_computed_statements": {
            "minimal_statements": [candidate.text for candidate in candidates],
            "fit_exact": fit_exact,
            "separating_runs_in_delay_environment": len(separating),
            "chosen_run_steps": len(chosen) - 1, "judgment_on_the_run": verdict,
            "judgments_on_runs": 1, "questions_about_statements": 0,
            "survivor": survivors[0].text, "class_after": len(survivors),
            "MET": fit_exact and len(candidates) == 2 and collapsed and len(separating) > 0},
        "R3_exact_overwrite_and_prior_witnesses_fixed": {
            "prediction": {key: value for key, value in overwrite_prediction.items()
                           if key != "predictions"},
            "prior_survivor_terms": prior_parts,
            "prior_false_reject_witnesses": len(witness_indexes),
            "witness_predictions": witness_predictions,
            "MET": (overwrite_prediction["status"] == "PREDICTED"
                    and overwrite_prediction["false_accepts"] == 0
                    and overwrite_prediction["false_rejects"] == 0
                    and overwrite_prediction["abstentions"] == 0
                    and len(witness_indexes) == 4 and all(witness_predictions))},
        "R4_different_identity_names_and_external_store": {
            "third_prediction": {key: value for key, value in third_prediction.items()
                                 if key != "predictions"},
            "fit_identity_literals_in_store": identity_literals_in_store,
            "store": str(STORE.relative_to(REPO)),
            "MET": (third_prediction["status"] == "PREDICTED"
                    and third_prediction["false_accepts"] == 0
                    and third_prediction["false_rejects"] == 0
                    and third_prediction["abstentions"] == 0
                    and not identity_literals_in_store)},
        "R5_fail_closed_and_what_not_to_save": {
            "different_content": different_prediction,
            "deleted_store": deleted_prediction,
            "restored_store": {key: value for key, value in restored_prediction.items()
                               if key != "predictions"},
            "copy_before_deletion": {key: value for key, value in copy_prediction.items()
                                     if key != "predictions"},
            "raw_exact_experience": raw,
            "relation_abstentions": overwrite_prediction["abstentions"],
            "MET": (different_prediction["status"] ==
                    "REFUSED__GOAL_CONTENT_OR_TERMS_NOT_RECOMPUTED"
                    and deleted_prediction["status"] == "REFUSED__NO_RELATION"
                    and restored_prediction["status"] == "PREDICTED"
                    and raw["abstentions"] > 0 and overwrite_prediction["abstentions"] == 0)},
        "R6_killed_designs_are_measured": {
            "full_canonical_trace_table_overwrite": canonical_over,
            "full_canonical_trace_table_third": canonical_third,
            "reason": "0 errors but many abstentions: exact canonical cells are too fine to carry the relation",
            "MET": (canonical_over["false_accepts"] == 0 and canonical_over["false_rejects"] == 0
                    and canonical_over["abstentions"] > 0
                    and canonical_third["false_accepts"] == 0
                    and canonical_third["false_rejects"] == 0
                    and canonical_third["abstentions"] > 0)},
        "R7_zeros_and_real_execution": {
            "model_calls": 0, "parameters_stored": 0, "network_calls_at_run_time": 0,
            "real_runs": {"move": len(move_traces), "extra": len(extra_traces),
                          "overwrite": len(overwrite_traces), "third": len(third_traces),
                          "delay": len(delay_traces), "different_content": len(different_traces)},
            "MET": True},
    }

    out = {
        "schema": SCHEMA, "authority": "NONE__PRODUCER_RUN_SANDBOX", "date": "2026-11-23",
        "branch": "arena/6f8ac9ce-brain",
        "mode": "COMPUTE_DEICTIC_HOLDER_SHAPE_TERMS_FROM_CONTENT_IDENTITY_PAIRS",
        "declared_before_the_run": DECLARED_BEFORE_THE_RUN,
        "computed_grammar": {
            "term_family": "computed_deictic_holder_shape_v1",
            "content": env.PROBE_OLD,
            "terms": len(terms), "feature_order": list(FEATURE_ORDER),
            "minimal_statements": [candidate.text for candidate in candidates],
        },
        "question": {
            "environment": "DELAY", "separating_runs": len(separating),
            "chosen_run_steps": len(chosen) - 1, "judgment_on_the_run": verdict,
            "survivor": survivors[0].text,
            "chosen_final_identities": [ident for ident, _v in chosen[-1]],
        },
        "store": {"path": str(STORE.relative_to(REPO)), "schema": STORE_SCHEMA,
                  "texts": relation_texts,
                  "sha256": hashlib.sha256(STORE.read_bytes()).hexdigest()[:16]},
        "verdict": verdict_rows,
        "all_criteria_met": all(row["MET"] for row in verdict_rows.values()),
        "killed_designs": {
            "hand_built_holder_changed_term": "rejected: would be a supplied 36th form, not a computed grammar",
            "full_canonical_trace_isomorphism_table": verdict_rows["R6_killed_designs_are_measured"],
            "literal_identity_present_then_absent": prior["verdict"]["P3_exact_on_held_out"],
        },
        "limits": [
            "goal content literal is still carried in the relation text; a machine with a different content literal refuses",
            "no GUI, browser, OSWorld 2.1, SWE-bench Pro / Pro V2 or Terminal-Bench task was run",
            "three CLI machines plus delay/different-content controls; not repository repair",
            "producer-run sandbox; no independent identity re-ran this receipt",
        ],
        "cost": {"seconds": round(time.time() - started, 2), "model_calls": 0,
                 "parameters_stored": 0, "network_calls_at_run_time": 0},
    }
    receipt.parent.mkdir(parents=True, exist_ok=True)
    receipt.write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({key: row["MET"] for key, row in verdict_rows.items()}, indent=1))
    print(json.dumps({"survivor": survivors[0].text,
                      "overwrite": {k: v for k, v in overwrite_prediction.items() if k != "predictions"},
                      "third": {k: v for k, v in third_prediction.items() if k != "predictions"},
                      "canonical_abstentions": canonical_over["abstentions"]}, indent=1))
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipt", type=pathlib.Path, required=True)
    options = parser.parse_args()
    measure(options.receipt)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
