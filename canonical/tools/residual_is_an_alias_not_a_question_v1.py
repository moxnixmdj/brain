#!/usr/bin/env python3
"""The residual is an alias, not a question: quotient the grammar before pricing it.

WHAT THE ROUND NAMED 20261201 MEASURED
--------------------------------------
One grammar, 244 terms, 29 890 conjunctions, 555 executed runs of a tarball, a
filesystem and a SQLite database.  The user's goal had four minimal statements on
one machine, two after a second, and two after a third.  It priced the remaining
two at log2(2) = 1 question of the user and pre-registered a language intake.

WHAT IS WRONG WITH THAT
-----------------------
The two survivors are

    created_once[c]
    monotone[c] AND final:count[c]==1

With c initially absent they are the same telescoping fact, not two intentions.
The round counted syntax where it should have counted meaning.  No dialogue can
recover a distinction the machine's own counting semantics never had.

WHAT IS BUILT
-------------
`computed_equivalence_quotient_v1` derives the identity from integer counts and
the initial reading; this tool applies it to the executed masks, reprices the
residual, and tests the identity's premise on a fourth machine that was not part
of the three-machine analysis: a filesystem that starts with one copy of c.
There c is present at step zero, so `created_once[c]` and
`monotone[c] AND final:count[c]==1` are different goals and a real run separates
them.  A reducer that merged them there would be false, so that is a falsifier.

CRITERIA, DECLARED BEFORE THE RECEIPT RUN
-----------------------------------------
C1 the goal's minimal class falls from two to one under the quotient, so no
   question of the user is left for this goal
C2 every proposed alias is observationally identical on all 555 runs; any
   disagreement refuses rewrites everywhere (fail closed)
C3 on the fourth machine the pair separates on a real run and is not merged,
   while an initially absent content is still merged and observed identical
C4 the quotient does not change any behaviour mask, and the number of behaviours
   with a unique minimal statement does not fall
C5 zero model calls, zero stored parameters, zero network calls at run time

Authority: NONE. Producer-run sandbox measurement, not independent verification.
"""
from __future__ import annotations

import argparse
import collections
import json
import pathlib
import sys
import tempfile
import time
from typing import Sequence

TOOLS = pathlib.Path(__file__).resolve().parent
REPO = TOOLS.parents[1]
RUNTIME = REPO / "canonical" / "runtime"
for path in (str(TOOLS), str(RUNTIME), str(REPO)):
    if path not in sys.path:
        sys.path.insert(0, path)

import breadth_buys_what_repetition_cannot_v1 as breadth  # noqa: E402
import computed_equivalence_quotient_v1 as quotient  # noqa: E402
import instant_learning_in_a_new_environment_v1 as env  # noqa: E402
import the_goal_is_a_quotient_of_the_trace_v1 as goal  # noqa: E402
import the_goal_is_a_relation_over_the_run_v1 as runs  # noqa: E402
import the_vocabulary_is_the_artifact_v1 as vocab  # noqa: E402

SCHEMA = "BRAIN_RESIDUAL_IS_AN_ALIAS_NOT_A_QUESTION_V1"
MACHINES = breadth.MACHINES
DEPTHS = breadth.DEPTHS
FOURTH = "PRELOADED"
FOURTH_DEPTH = 3
FOURTH_CONTENT = "probe_third_content"


def build_preloaded(root: pathlib.Path) -> env.Machine:
    """A real filesystem whose initial reading already holds one copy of PROBE_NEW."""

    def reset() -> None:
        for path in list(root.iterdir()):
            if path.is_file():
                path.unlink()
        (root / "seed").write_text(env.PROBE_OLD, encoding="utf-8")
        (root / "loaded").write_text(env.PROBE_NEW, encoding="utf-8")

    def read() -> list[tuple[str, str]]:
        return [(path.name, path.read_text(errors="replace").strip())
                for path in sorted(root.iterdir()) if path.is_file()]

    return env.Machine(FOURTH, root, (
        env.Atom("PRE_A1", ((env._write_via_sh("{content}", "{name}"), None),)),
        env.Atom("PRE_A2", ((("rm", "-f", "{name}"), None),)),
        env.Atom("PRE_A3", ((("mv", "-f", "{name}", "{target}"), None),)),
        env.Atom("PRE_A4", ((("cp", "-f", "{name}", "{target}"), None),)),
        env.Atom("PRE_A5", ((("ls", "-1"), None),)),
    ), read, reset)


def shared_counts(pools: dict[str, list[runs.Trace]]) -> dict[str, int]:
    """Only initial counts that agree on every machine may be used by a rewrite."""
    result: dict[str, int] | None = None
    for traces in pools.values():
        current = {content: count
                   for content, count in quotient.counts_with_absent(traces[0][0], traces).items()
                   if quotient.unit_increments(traces, content)}
        if result is None:
            result = current
            continue
        result = {content: count for content, count in result.items()
                  if current.get(content) == count}
    return result or {}


def meaning_report(analysis: breadth.Analysis, truth: int, texts: Sequence[str],
                   counts: dict[str, int]) -> dict[str, object]:
    """Reprice every behaviour after statements with one meaning are merged."""
    grouped = analysis.classes()
    before_sizes, after_sizes = [], []
    goal_before: list[tuple[int, ...]] = []
    goal_after: list[tuple[int, ...]] = []
    for mask, combos in grouped.items():
        minimal = analysis.minimal(mask, combos)
        after = quotient.dedupe_meanings(minimal, texts, counts)
        if mask in (0, analysis.full):
            continue
        before_sizes.append(len(minimal))
        after_sizes.append(len(after))
        if mask == truth:
            goal_before = minimal
            goal_after = after
    mean = lambda sizes: round(sum(sizes) / len(sizes), 2) if sizes else None
    after_grouped: dict[int, list[Combo]] = {
        mask: quotient.dedupe_meanings(analysis.minimal(mask, combos), texts, counts)
        for mask, combos in grouped.items()}
    ambiguous = [(mask, rows) for mask, rows in after_grouped.items()
                 if mask not in (0, analysis.full) and len(rows) > 1]

    def artifact(text: str) -> bool:
        # The tarball reader concatenates a repeated member's body into one
        # "content" literal. Such a literal is not a fact about the user's goal.
        return "probe_new_contentprobe_new_content" in text or (
            "probe_seed_contentprobe_new_content" in text)

    artifact_rows = [(mask, rows) for mask, rows in ambiguous
                     if any(artifact(texts[index]) for combo in rows for index in combo)]
    clean_rows = [(mask, rows) for mask, rows in ambiguous if (mask, rows) not in artifact_rows]
    return {
        "behaviours": len(grouped),
        "behaviours_with_a_unique_statement_before": sum(1 for n in before_sizes if n == 1),
        "behaviours_with_a_unique_statement_after": sum(1 for n in after_sizes if n == 1),
        "mean_class_before": mean(before_sizes),
        "mean_class_after": mean(after_sizes),
        "behaviours_still_ambiguous_after": sum(1 for n in after_sizes if n > 1),
        "ambiguous_with_concatenated_reader_literals": len(artifact_rows),
        "ambiguous_with_clean_literals": len(clean_rows),
        "example_clean_ambiguous_texts": next(
            ([" ∧ ".join(texts[i] for i in combo) for combo in rows[:6]]
             for _mask, rows in clean_rows), []),
        "largest_class_after": max(after_sizes) if after_sizes else None,
        "example_ambiguous_texts": next(
            ([" ∧ ".join(texts[i] for i in combo) for combo in
              quotient.dedupe_meanings(
                  analysis.minimal(mask, grouped[mask]), texts, counts)][:6]
             for mask in sorted(grouped)
             if mask not in (0, analysis.full)
             and len(quotient.dedupe_meanings(
                 analysis.minimal(mask, grouped[mask]), texts, counts)) > 1), []),
        "goal_minimal_before": len(goal_before),
        "goal_minimal_after": len(goal_after),
        "goal_texts_before": [" ∧ ".join(texts[i] for i in combo) for combo in goal_before],
        "goal_texts_after": [" ∧ ".join(texts[i] for i in combo) for combo in goal_after],
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipt", type=pathlib.Path, required=True)
    options = parser.parse_args(argv)
    started = time.time()
    where = pathlib.Path(tempfile.mkdtemp(prefix="brain-alias-quotient-"))
    args = {"content": env.PROBE_NEW, "old": env.PROBE_OLD,
            "name": "seed", "target": "copy"}

    pools: dict[str, list[runs.Trace]] = {}
    for name in MACHINES:
        machine = vocab.MACHINES[name](where / name.lower())
        machine.root.mkdir(parents=True, exist_ok=True)
        machine.reset()
        pools[name] = runs.traces_for(machine, args, depth=DEPTHS[name])

    terms = breadth.union_terms(pools)
    texts = [term.text for term in terms]
    per_machine = {name: breadth.masks_on(terms, pools[name]) for name in MACHINES}
    analysis = breadth.Analysis(terms, [per_machine[name] for name in MACHINES],
                                [len(pools[name]) for name in MACHINES])
    term_masks = {index: analysis.by_combo[(index,)] for index in range(len(texts))}
    statement_masks = quotient.combos_masks(quotient.all_combos(len(texts)), term_masks)
    truth = 0
    offset = 0
    for name in MACHINES:
        truth |= breadth.judge_mask(pools[name]) << offset
        offset += len(pools[name])

    counts = shared_counts(pools)
    proposed = quotient.alias_groups(texts, counts)
    checked = quotient.verify_aliases(proposed, statement_masks)
    verified = quotient.verified_groups(proposed, statement_masks)
    # A single unverified alias is a reason to refuse every rewrite, not to
    # hand-pick the convenient ones.
    effective_counts = counts if len(verified) == len(proposed) else {}
    priced = meaning_report(analysis, truth, texts, effective_counts)
    before = analysis.report(truth)

    # A machine the three-machine analysis never saw: c is present at step zero.
    fourth = build_preloaded(where / "preloaded")
    fourth.root.mkdir(parents=True, exist_ok=True)
    fourth.reset()
    args4 = dict(args, content=FOURTH_CONTENT, name="fresh", target="moved")
    traces4 = runs.traces_for(fourth, args4, depth=FOURTH_DEPTH)
    whole4, end4 = runs.run_terms(traces4)
    terms4: list = []
    seen4: set[str] = set()
    for term in list(whole4) + list(end4):
        if term.text not in seen4:
            seen4.add(term.text)
            terms4.append(term)
    texts4 = [term.text for term in terms4]
    masks4 = {index: mask for index, mask in enumerate(breadth.masks_on(terms4, traces4))}
    statement_masks4 = quotient.combos_masks(quotient.all_combos(len(texts4)), masks4)
    counts4 = {content: count
               for content, count in quotient.counts_with_absent(traces4[0][0], traces4).items()
               if quotient.unit_increments(traces4, content)}
    proposed4 = quotient.alias_groups(texts4, counts4)
    checked4 = quotient.verify_aliases(proposed4, statement_masks4)

    c = env.PROBE_NEW
    trio = (f"created_once[{c}]", f"monotone[{c}]", f"final:count[{c}]==1")
    first, second, final = (texts4.index(text) for text in trio)
    created_combo, pair_combo = (first,), tuple(sorted((second, final)))
    separate = {text: statement_masks4.get(combo) for text, combo in
                zip(trio, (created_combo, (second,), (final,)))}
    premise_detected = (
        counts4.get(c) == 1
        and all(value is not None for value in separate.values())
        and separate[trio[0]] != (statement_masks4[(second,)] & statement_masks4[(final,)])
        and not any(created_combo in alias.combos and pair_combo in alias.combos
                    for alias in proposed4)
    )
    absent = FOURTH_CONTENT
    absent_alias = [row for row in checked4
                    if row["observed_identical"]
                    and any(f"created_once[{absent}]" in statement for statement in row["texts"])
                    and any(f"final:count[{absent}]==1" in statement
                            for statement in row["texts"])]
    absent_aliases_ok = counts4.get(absent) == 0 and bool(absent_alias)

    verdict = {
        "C1_alias_removed_without_a_question": {
            "before": priced["goal_minimal_before"], "after": priced["goal_minimal_after"],
            "questions_of_the_user": 0 if priced["goal_minimal_after"] == 1 else "unresolved",
            "MET": priced["goal_minimal_before"] > 1 and priced["goal_minimal_after"] == 1},
        "C2_every_alias_observed_identical": {
            "proposed": len(proposed), "verified": len(verified),
            "MET": bool(proposed) and len(verified) == len(proposed)},
        "C3_fourth_machine_respects_the_premise": {
            "initial_count_of_probe_new": counts4.get(c),
            "masks": separate, "pair_not_merged": premise_detected,
            "initially_absent_content_merged": absent_aliases_ok,
            "MET": premise_detected and absent_aliases_ok},
        "C4_behaviours_are_unchanged": {
            "behaviours_before": before["behaviours"],
            "behaviours_after": priced["behaviours"],
            "unique_before": priced["behaviours_with_a_unique_statement_before"],
            "unique_after": priced["behaviours_with_a_unique_statement_after"],
            "mean_class_before": priced["mean_class_before"],
            "mean_class_after": priced["mean_class_after"],
            "MET": before["behaviours"] == priced["behaviours"]
            and priced["behaviours_with_a_unique_statement_after"]
            >= priced["behaviours_with_a_unique_statement_before"]
            and priced["mean_class_after"] <= priced["mean_class_before"]},
        "C5_zero": {"model_calls": 0, "parameters_stored": 0,
                    "network_calls_at_run_time": 0, "MET": True},
    }

    receipt = {
        "schema": SCHEMA,
        "authority": "NONE__PRODUCER_RUN_SANDBOX",
        "date": "2026-11-21",
        "mode": "COMPUTED_ALIAS_QUOTIENT_REPRICES_THE_GOAL_AND_TESTS_ITS_PREMISE_OFF_DISTRIBUTION",
        "retracted_claim": (
            "The round named 20261201 priced the residual at one question of the user. "
            "Its two statements are the same telescoping fact when the content starts absent; "
            "the bit was a counting artifact, not an intention the user must supply."),
        "criteria_were_declared_before_the_receipt_run": True,
        "declared_acceptance_before_the_receipt_run": {
            "C1": "the goal's minimal class falls from two to one under the quotient",
            "C2": "every proposed alias is observationally identical on all 555 runs",
            "C3": "on a machine that starts with one copy, the pair separates and is not merged",
            "C4": "no behaviour mask changes and unique statements do not decrease",
            "C5": "zero model calls, zero stored parameters, zero network at run time"},
        "theorem": quotient.__doc__.split("THE THEOREM, NOT A SAMPLE")[1].split(
            "The premise matters.")[0].strip(),
        "verdict": verdict,
        "residual": priced,
        "prior_residual": {
            "minimal_statements": before["goal_minimal_statements"],
            "texts": before["goal_minimal_texts"]},
        "aliases": [
            {"texts": row["texts"], "rule": row["rule"], "premise": row["premise"],
             "observed_identical": row["observed_identical"]}
            for row in checked[:40]],
        "fourth_machine": {
            "name": FOURTH, "runs": len(traces4), "depth": FOURTH_DEPTH,
            "initial_counts": counts4,
            "aliases_proposed": len(proposed4), "aliases_observed_identical":
            sum(1 for row in checked4 if row["observed_identical"]),
            "probe_new_masks": separate},
        "runs": {name: len(pools[name]) for name in MACHINES},
        "terms": len(texts),
        "cost": {"seconds": round(time.time() - started, 1), "model_calls": 0,
                 "parameters_stored": 0, "network_calls_at_run_time": 0},
        "limits": [
            "the identity is derived for integer entry counts, unit increments and a known, common "
            "initial reading; a machine that breaks a premise is refused before any merge",
            "the quotient removes aliases inside the supplied grammar. Goals outside the grammar "
            "are still undecided, and other residuals in it may be genuine",
            "no edit is synthesized and no benchmark is run; this prices what the goal means "
            "before an edit is attempted",
            "the fourth machine is a new initial condition on a known tool family, not a new OS"],
    }
    options.receipt.parent.mkdir(parents=True, exist_ok=True)
    options.receipt.write_text(json.dumps(receipt, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({key: value["MET"] for key, value in verdict.items()}, indent=1))
    print(json.dumps({"residual": priced["goal_minimal_after"],
                      "texts": priced["goal_texts_after"],
                      "seconds": receipt["cost"]["seconds"]}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
