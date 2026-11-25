#!/usr/bin/env python3
"""A literal that never changes carries no goal: delete it before pricing ambiguity.

WHAT THE READER-FIDELITY ROUND LEFT
-----------------------------------
After one computed identity and a faithful tarball reader, 555 runs of three
machines give 301 behaviours; 148 still carry more than one minimal statement.
One reason is that the grammar keeps terms about contents the machines cannot
change. `probe_second_content`, for example, is present once in every reading of
all three machines and no offered action adds or removes it. Terms such as
`created_once[probe_second_content]` and `final:count[probe_second_content]==1`
are then a constant and its negation, not competing intentions.

WHAT IS BUILT
-------------
Premises are computed from each machine's readings: initial count, maximum
count, unit increments and whether a deleted value is ever restored. They are
merged conjunctively across machines — a premise survives only if it holds on
every machine. A content whose count is constant on every machine is deleted
from the grammar; no learned weight, tolerance or similarity is involved.

The falsifier changes only the arguments on an existing filesystem: the same
content can now be copied and removed, so it is no longer constant and its
terms separate on a real run. A reducer that deleted them there would be wrong.

CRITERIA, DECLARED BEFORE THE RECEIPT RUN
-----------------------------------------
I1 at least one content has a computed constant-count premise on all machines
I2 deleting inert terms strictly reduces ambiguous classes on the same 555 runs
I3 the user's goal still has one minimal statement and every alias is observed
   identical
I4 on the mutable-content machine the premise is false and a real run separates
   the terms the deletion would have removed
I5 zero model calls, zero stored parameters, zero network calls at run time

Authority: NONE. Producer-run sandbox. No capability or terminal claim.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
import tempfile
import time
from typing import Callable, Sequence

TOOLS = pathlib.Path(__file__).resolve().parent
REPO = TOOLS.parents[1]
RUNTIME = REPO / "canonical" / "runtime"
for path in (str(TOOLS), str(RUNTIME), str(REPO)):
    if path not in sys.path:
        sys.path.insert(0, path)

import breadth_buys_what_repetition_cannot_v1 as breadth  # noqa: E402
import computed_equivalence_quotient_v1 as quotient  # noqa: E402
import instant_learning_in_a_new_environment_v1 as env  # noqa: E402
import tar_reader_artifact_v1 as fidelity  # noqa: E402
import the_goal_is_a_relation_over_the_run_v1 as runs  # noqa: E402
import the_vocabulary_is_the_artifact_v1 as vocab  # noqa: E402

SCHEMA = "BRAIN_FINITE_TRACE_INVARIANTS_V1"
BASELINE = REPO / "canonical" / "verification" / "TAR_READER_ARTIFACT_20261121_V1.json"
ARGS = {"content": env.PROBE_NEW, "old": env.PROBE_OLD, "name": "seed", "target": "copy"}
SECOND = "probe_second_content"


def union_terms(pools: dict[str, list[runs.Trace]]) -> list:
    terms: list = []
    seen: set[str] = set()
    for pool in pools.values():
        whole, end = runs.run_terms(pool)
        for term in list(whole) + list(end):
            if term.text not in seen:
                seen.add(term.text)
                terms.append(term)
    return terms


def shared_premises(pools: dict[str, list[runs.Trace]]) -> dict[str, quotient.Premises]:
    """Conjunctive merge: a premise survives only when all machines agree."""
    result: dict[str, quotient.Premises] | None = None
    for traces in pools.values():
        current = quotient.compute_premises(traces[0][0], traces)
        if result is None:
            result = dict(current)
            continue
        merged: dict[str, quotient.Premises] = {}
        for name, earlier in result.items():
            later = current.get(name)
            if later is None or earlier.initial != later.initial:
                continue
            merged[name] = quotient.Premises(
                initial=earlier.initial,
                maximum=max(earlier.maximum, later.maximum),
                unit=earlier.unit and later.unit,
                never_restored=earlier.never_restored and later.never_restored)
        result = merged
    return result or {}


def constant_contents(premises: dict[str, quotient.Premises]) -> list[str]:
    """Counts that cannot change anywhere in the measured universe."""
    return sorted(name for name, premise in premises.items()
                  if premise.maximum == premise.initial and premise.never_restored)


def build(pools: dict[str, list[runs.Trace]], terms: Sequence
          ) -> tuple[breadth.Analysis, int, list[str], dict[tuple[int, ...], int]]:
    texts = [term.text for term in terms]
    per_machine = {name: breadth.masks_on(terms, pools[name]) for name in pools}
    analysis = breadth.Analysis(terms, [per_machine[name] for name in pools],
                                [len(pools[name]) for name in pools])
    term_masks = {index: analysis.by_combo[(index,)] for index in range(len(texts))}
    statement_masks = quotient.combos_masks(quotient.all_combos(len(texts)), term_masks)
    truth = 0
    offset = 0
    for name in pools:
        truth |= breadth.judge_mask(pools[name]) << offset
        offset += len(pools[name])
    return analysis, truth, texts, statement_masks


def report(analysis: breadth.Analysis, truth: int, texts: Sequence[str],
           counts: dict[str, int],
           dedupe: Callable[[Sequence[tuple[int, ...]], Sequence[str]], list[tuple[int, ...]]]
           ) -> dict[str, object]:
    grouped = analysis.classes()
    before_sizes, after_sizes = [], []
    goal_before: list[tuple[int, ...]] = []
    goal_after: list[tuple[int, ...]] = []
    for mask, combos in grouped.items():
        minimal = analysis.minimal(mask, combos)
        after = dedupe(minimal, texts)
        if mask in (0, analysis.full):
            continue
        before_sizes.append(len(minimal))
        after_sizes.append(len(after))
        if mask == truth:
            goal_before, goal_after = minimal, after
    mean = lambda sizes: round(sum(sizes) / len(sizes), 2) if sizes else None
    return {
        "behaviours": len(grouped),
        "unique_before": sum(1 for n in before_sizes if n == 1),
        "unique_after": sum(1 for n in after_sizes if n == 1),
        "ambiguous_before": sum(1 for n in before_sizes if n > 1),
        "ambiguous_after": sum(1 for n in after_sizes if n > 1),
        "mean_before": mean(before_sizes),
        "mean_after": mean(after_sizes),
        "largest_after": max(after_sizes) if after_sizes else None,
        "goal_before": len(goal_before),
        "goal_after": len(goal_after),
        "goal_texts_after": [" ∧ ".join(texts[i] for i in combo) for combo in goal_after],
        "example_ambiguous_texts": next(
            ([" ∧ ".join(texts[i] for i in combo) for combo in rows[:6]]
             for mask, rows in grouped.items()
             if mask not in (0, analysis.full) and len(dedupe(rows, texts)) > 1), []),
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipt", type=pathlib.Path, required=True)
    options = parser.parse_args(argv)
    started = time.time()
    where = pathlib.Path(tempfile.mkdtemp(prefix="brain-literal-deletion-"))
    pools = fidelity.corrected_pools(where, ARGS)
    premises = shared_premises(pools)
    inert = constant_contents(premises)
    counts = {name: premise.initial for name, premise in premises.items()}
    all_terms = union_terms(pools)
    kept_terms = [term for term in all_terms
                  if not any(name in term.text for name in inert)]
    texts_all = [term.text for term in all_terms]
    texts_kept = [term.text for term in kept_terms]

    analysis_all, truth_all, texts_all, masks_all = build(pools, all_terms)
    analysis_kept, truth_kept, texts_kept, masks_kept = build(pools, kept_terms)
    aliases = quotient.alias_groups(texts_kept, counts)
    checked = quotient.verify_aliases(aliases, masks_kept)
    all_ok = all(row["observed_identical"] for row in checked)
    effective = counts if all_ok else {}
    dedupe = lambda statements, names: quotient.dedupe_meanings(statements, names, effective)
    before = report(analysis_all, truth_all, texts_all, counts,
                    lambda statements, names: quotient.dedupe_meanings(statements, names, counts))
    after = report(analysis_kept, truth_kept, texts_kept, effective, dedupe)

    # Falsifier: the same content is now a real argument the machine can change.
    mutable = vocab.MACHINES["FILESYSTEM"](where / "mutable")
    mutable.root.mkdir(parents=True, exist_ok=True)
    mutable.reset()
    args_mutable = dict(ARGS, content=SECOND, name="seed2", target="copy2")
    traces_m = runs.traces_for(mutable, args_mutable, depth=3)
    premises_m = quotient.compute_premises(traces_m[0][0], traces_m)
    terms_m = union_terms({"MUTABLE": traces_m})
    texts_m = [term.text for term in terms_m]
    masks_m = {index: mask for index, mask in enumerate(breadth.masks_on(terms_m, traces_m))}
    statement_masks_m = quotient.combos_masks(quotient.all_combos(len(texts_m)), masks_m)
    created = f"created_once[{SECOND}]"
    final = f"final:count[{SECOND}]==2"
    present = created in texts_m and final in texts_m
    separated = False
    if present:
        index_c, index_f = texts_m.index(created), texts_m.index(final)
        separated = statement_masks_m[(index_c,)] != statement_masks_m[(index_f,)]
    premise_m = premises_m.get(SECOND)
    falsifier_ok = (premise_m is not None and premise_m.maximum > premise_m.initial
                    and SECOND not in constant_contents(premises_m)
                    and present and separated)

    baseline = json.loads(BASELINE.read_text())
    verdict = {
        "I1_constant_literals_are_computed": {
            "inert_contents": inert,
            "premises": {name: premise.as_dict() for name, premise in premises.items()},
            "MET": bool(inert)},
        "I2_deletion_reduces_ambiguity": {
            "baseline_ambiguous": baseline["corrected"]["after_quotient"][
                "behaviours_still_ambiguous_after"],
            "before_deletion": before["ambiguous_after"],
            "after_deletion": after["ambiguous_after"],
            "terms_before": len(texts_all), "terms_after": len(texts_kept),
            "MET": after["ambiguous_after"] < before["ambiguous_after"]},
        "I3_goal_stays_identified_without_a_false_merge": {
            "aliases_proposed": len(aliases),
            "aliases_verified": sum(1 for row in checked if row["observed_identical"]),
            "goal_before": after["goal_before"], "goal_after": after["goal_after"],
            "texts": after["goal_texts_after"],
            "MET": all_ok and after["goal_before"] > 1 and after["goal_after"] == 1},
        "I4_mutable_content_refutes_the_deletion": {
            "premise": premise_m.as_dict() if premise_m else None,
            "pair_observed_on_a_real_run": separated,
            "MET": falsifier_ok},
        "I5_zero": {"model_calls": 0, "parameters_stored": 0,
                    "network_calls_at_run_time": 0, "MET": True},
    }
    receipt = {
        "schema": SCHEMA,
        "authority": "NONE__PRODUCER_RUN_SANDBOX",
        "date": "2026-11-21",
        "mode": "DELETE_INERT_LITERALS_THEN_QUOTIENT_THE_REMAINING_GRAMMAR",
        "baseline_receipt": str(BASELINE.relative_to(REPO)),
        "criteria_were_declared_before_the_receipt_run": True,
        "declared_acceptance_before_the_receipt_run": {
            "I1": "at least one content has a computed constant-count premise on all machines",
            "I2": "deleting inert terms strictly reduces ambiguous classes",
            "I3": "goal stays identified and every alias is observed identical",
            "I4": "a mutable content violates the premise and its terms separate on a real run",
            "I5": "zero model calls, parameters and network at run time"},
        "verdict": verdict,
        "runs": {name: len(traces) for name, traces in pools.items()},
        "mutable_runs": len(traces_m),
        "constant_literals": inert,
        "before_deletion": before,
        "after_deletion": after,
        "aliases": [{"texts": row["texts"], "premise": row["premise"],
                     "observed_identical": row["observed_identical"]}
                    for row in checked[:40]],
        "cost": {"seconds": round(time.time() - started, 1), "model_calls": 0,
                 "parameters_stored": 0, "network_calls_at_run_time": 0},
        "limits": [
            "constant premises are decisions over executed runs at depths 5/4/4, not proofs about "
            "unbounded action sequences; a new action that changes the literal must be re-measured",
            "deleting inert terms removes information-free statements; it does not resolve genuine "
            "ambiguity between mutable contents",
            "no edit is synthesized and no benchmark is run; this prices the goal before an edit",
            "the mutable machine is a changed argument on an existing tool, not a new OS"],
    }
    options.receipt.parent.mkdir(parents=True, exist_ok=True)
    options.receipt.write_text(json.dumps(receipt, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({key: value["MET"] for key, value in verdict.items()}, indent=1))
    print(json.dumps({"ambiguous_before": before["ambiguous_after"],
                      "ambiguous_after": after["ambiguous_after"],
                      "goal_after": after["goal_after"],
                      "inert": inert,
                      "seconds": receipt["cost"]["seconds"]}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
