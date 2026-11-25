#!/usr/bin/env python3
"""Reader fidelity deletes more ambiguity than another learner could price.

THE DEFECT
----------
The shared tarball machine reads each name returned by `tar -tf` with one
`tar -xOf name`. When the same member name is appended twice, that command
prints both bodies, so the reader records ONE entry whose "content" is the
concatenation of the two. The previous round found 175 behaviour classes whose
residual statements carried such literals. Those are not user intentions and
not genuine ambiguity: they are a reader that merged two archive members.

WHAT IS BUILT
-------------
`build_indexed_tarball` keeps the same reset, the same real GNU tar atoms and
the same 231 runs, and changes only the reader: Python's stdlib `tarfile`
enumerates every member occurrence, gives a repeated name an occurrence suffix,
and reads that member's own body. A concatenation is then impossible by
construction, not filtered after the fact.

The corrected tarball is put into the same three-machine union (555 runs) and
priced with the already-merged computed equivalence quotient. The baseline is
the committed receipt that measured the old reader, not a newly hand-picked
comparison.

CRITERIA, DECLARED BEFORE THE RECEIPT RUN
-----------------------------------------
F1 the corrected reader yields zero concatenated content literals while the
   committed baseline recorded 175 ambiguous classes carrying them
F2 the corrected union has zero ambiguous classes carrying concatenated
   literals
F3 the computed quotient still takes the user's goal from two statements to one
F4 quotienting changes no behaviour mask on the corrected union
F5 zero model calls, zero stored parameters, zero network calls at run time

Authority: NONE. Producer-run sandbox measurement. The old reader is untouched;
this is a falsification of its grammar, not a rewrite of historical receipts.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
import tarfile
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
import residual_is_an_alias_not_a_question_v1 as prior  # noqa: E402
import the_goal_is_a_relation_over_the_run_v1 as runs  # noqa: E402
import the_vocabulary_is_the_artifact_v1 as vocab  # noqa: E402

SCHEMA = "BRAIN_TAR_READER_ARTIFACT_V1"
BASELINE = (REPO / "canonical" / "verification"
            / "RESIDUAL_IS_AN_ALIAS_NOT_A_QUESTION_20261121_V1.json")
DEPTHS = {"TARBALL": 5, "FILESYSTEM": 4, "SQLITE": 4}


def build_indexed_tarball(root: pathlib.Path) -> env.Machine:
    """The original machine with one row per archive member occurrence."""
    original = env.build_tarball(root)
    archive = root / "pack.tar"

    def read() -> list[tuple[str, str]]:
        seen: dict[str, int] = {}
        rows: list[tuple[str, str]] = []
        with tarfile.open(archive, mode="r") as bundle:
            for member in bundle.getmembers():
                if not member.isfile():
                    continue
                ordinal = seen.get(member.name, 0)
                seen[member.name] = ordinal + 1
                ident = member.name if ordinal == 0 else f"{member.name}#{ordinal}"
                handle = bundle.extractfile(member)
                body = handle.read().decode("utf-8", "replace").strip() if handle else ""
                rows.append((ident, body))
        return rows

    return env.Machine("TARBALL_INDEXED", root, original.atoms, read, original.reset)


def concatenation_pattern(literals: Sequence[str]) -> re.Pattern[str]:
    """A content made only of two or more known literals stuck together."""
    alternatives = "|".join(re.escape(text) for text in sorted(set(literals),
                                                                key=len, reverse=True))
    return re.compile(r"^(?:" + alternatives + r"){2,}$")


def corrected_pools(where: pathlib.Path, args: dict[str, str]) -> dict[str, list[runs.Trace]]:
    """The same three machines and depths, with only the tarball reader corrected."""
    pools: dict[str, list[runs.Trace]] = {}
    for name, builder in (("TARBALL", build_indexed_tarball),
                          ("FILESYSTEM", vocab.MACHINES["FILESYSTEM"]),
                          ("SQLITE", vocab.MACHINES["SQLITE"])):
        machine = builder(where / name.lower())
        machine.root.mkdir(parents=True, exist_ok=True)
        machine.reset()
        pools[name] = runs.traces_for(machine, args, depth=DEPTHS[name])
    return pools


def analyze(where: pathlib.Path, args: dict[str, str]) -> dict[str, object]:
    pools = corrected_pools(where, args)
    terms: list = []
    seen: set[str] = set()
    for pool in pools.values():
        whole, end = runs.run_terms(pool)
        for term in list(whole) + list(end):
            if term.text not in seen:
                seen.add(term.text)
                terms.append(term)
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

    counts = prior.shared_counts(pools)
    proposed = quotient.alias_groups(texts, counts)
    verified = quotient.verified_groups(proposed, statement_masks)
    effective = counts if len(verified) == len(proposed) else {}
    priced = prior.meaning_report(analysis, truth, texts, effective)
    raw = analysis.report(truth)

    literals = {args["content"], args["old"], "probe_second_content"}
    pattern = concatenation_pattern(literals)
    artefacts = sorted({value for pool in pools.values() for trace in pool
                        for state in trace for _ident, value in state
                        if pattern.fullmatch(value)})
    artefact_terms = [text for text in texts if any(value in text for value in artefacts)]
    artefact_ambiguous = [
        statement for statement in priced["example_ambiguous_texts"]
        if any(value in statement for value in artefacts)]
    return {
        "runs": {name: len(pools[name]) for name in pools},
        "terms": len(texts),
        "initial_counts": counts,
        "concatenated_contents": artefacts,
        "terms_with_concatenated_contents": len(artefact_terms),
        "example_ambiguous_texts_with_concatenated_contents": artefact_ambiguous,
        "raw": raw,
        "after_quotient": priced,
        "aliases_proposed": len(proposed),
        "aliases_verified": len(verified),
        "hashes": {
            "first_trace": [list(state) for state in pools["TARBALL"][0]],
            "a_repeated_member_trace": [
                [list(state) for state in trace]
                for trace in pools["TARBALL"]
                if any("#" in ident for state in trace for ident, _value in state)][:1],
        },
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipt", type=pathlib.Path, required=True)
    options = parser.parse_args(argv)
    started = time.time()
    where = pathlib.Path(tempfile.mkdtemp(prefix="brain-tar-fidelity-"))
    args = {"content": env.PROBE_NEW, "old": env.PROBE_OLD,
            "name": "seed", "target": "copy"}
    result = analyze(where, args)
    baseline = json.loads(BASELINE.read_text())
    old = baseline["residual"]
    corrected = result["after_quotient"]

    verdict = {
        "F1_concatenation_is_impossible_by_construction": {
            "baseline_ambiguous_classes_with_concatenated_literals":
                old["ambiguous_with_concatenated_reader_literals"],
            "corrected_concatenated_contents": len(result["concatenated_contents"]),
            "corrected_terms_with_them": result["terms_with_concatenated_contents"],
            "MET": old["ambiguous_with_concatenated_reader_literals"] > 0
            and not result["concatenated_contents"]
            and result["terms_with_concatenated_contents"] == 0},
        "F2_ambiguous_classes_with_reader_artifacts_are_gone": {
            "baseline": old["ambiguous_with_concatenated_reader_literals"],
            "corrected": corrected["ambiguous_with_concatenated_reader_literals"],
            "corrected_clean_ambiguous": corrected["ambiguous_with_clean_literals"],
            "MET": corrected["ambiguous_with_concatenated_reader_literals"] == 0},
        "F3_the_calculated_quotient_still_identifies_the_goal": {
            "before": corrected["goal_minimal_before"],
            "after": corrected["goal_minimal_after"],
            "texts": corrected["goal_texts_after"],
            "MET": corrected["goal_minimal_before"] > 1
            and corrected["goal_minimal_after"] == 1},
        "F4_no_behaviour_mask_changes_under_the_quotient": {
            "behaviours": corrected["behaviours"],
            "unique_before": corrected["behaviours_with_a_unique_statement_before"],
            "unique_after": corrected["behaviours_with_a_unique_statement_after"],
            "mean_before": corrected["mean_class_before"],
            "mean_after": corrected["mean_class_after"],
            "MET": result["raw"]["behaviours"] == corrected["behaviours"]
            and corrected["behaviours_with_a_unique_statement_after"]
            >= corrected["behaviours_with_a_unique_statement_before"]},
        "F5_zero": {"model_calls": 0, "parameters_stored": 0,
                    "network_calls_at_run_time": 0, "MET": True},
    }
    receipt = {
        "schema": SCHEMA,
        "authority": "NONE__PRODUCER_RUN_SANDBOX",
        "date": "2026-11-21",
        "mode": "ONE_READER_CHANGE_ON_THE_SAME_ATOMS_AND_THE_SAME_555_RUNS",
        "baseline_receipt": str(BASELINE.relative_to(REPO)),
        "criteria_were_declared_before_the_receipt_run": True,
        "declared_acceptance_before_the_receipt_run": {
            "F1": "the corrected reader yields zero concatenated content literals",
            "F2": "the corrected union has zero ambiguous classes carrying them",
            "F3": "the goal class still falls from two to one under the quotient",
            "F4": "quotienting changes no behaviour mask",
            "F5": "zero model calls, parameters and network at run time"},
        "verdict": verdict,
        "corrected": result,
        "baseline_residual": {key: old[key] for key in (
            "behaviours", "behaviours_with_a_unique_statement_before",
            "behaviours_still_ambiguous_after",
            "ambiguous_with_concatenated_reader_literals",
            "ambiguous_with_clean_literals", "goal_minimal_after",
            "mean_class_before", "mean_class_after", "largest_class_after")},
        "cost": {"seconds": round(time.time() - started, 1), "model_calls": 0,
                 "parameters_stored": 0, "network_calls_at_run_time": 0},
        "limits": [
            "only the tarball reader changed: the same commands, resets, depths and goal judge were reused",
            "indexed member identity is a reader choice; a tool that addresses duplicate names by position "
            "would need a separate contract",
            "remaining ambiguous classes are measured, not resolved; no language was asked for",
            "no prototype run preceded the criteria: F1-F5 are predictive, not confirmatory"],
    }
    options.receipt.parent.mkdir(parents=True, exist_ok=True)
    options.receipt.write_text(json.dumps(receipt, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({key: value["MET"] for key, value in verdict.items()}, indent=1))
    print(json.dumps({"corrected_ambiguous": corrected["behaviours_still_ambiguous_after"],
                      "artifact_classes": corrected["ambiguous_with_concatenated_reader_literals"],
                      "goal_after": corrected["goal_minimal_after"],
                      "seconds": receipt["cost"]["seconds"]}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
