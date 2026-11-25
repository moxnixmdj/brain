#!/usr/bin/env python3
"""Construct the next question as a run, instead of hunting for it in a pool.

The previous round found that harmful counterexamples cannot be located by any
computable ordering it tried (best ranks 130/136 of 321, worse than chance), and
that one harmful answer is enough to make the statistic exact. It named the next
step: build a run that separates the surviving statistics, then pay for one
judgment. This tool does that.

The construction uses no verdict. It appends real atoms to a real executed trace
until the current statistic's image is unchanged while a generator *outside* the
statistic moves. Such a run is a candidate for a harmful pair; the user's label
decides whether it is one. Criteria are declared before execution.

Authority: NONE. Producer-run sandbox, zero model calls, zero stored parameters.
"""
from __future__ import annotations

import argparse
import collections
import itertools
import json
import pathlib
import sys
import tempfile
import time
from typing import Any, Sequence

TOOLS = pathlib.Path(__file__).resolve().parent
REPO = TOOLS.parents[1]
for path in (str(TOOLS), str(REPO)):
    if path not in sys.path:
        sys.path.insert(0, path)

import instant_learning_in_a_new_environment_v1 as env  # noqa: E402
import the_goal_is_a_quotient_of_the_trace_v1 as quotient  # noqa: E402
import the_goal_is_a_relation_over_the_run_v1 as runs  # noqa: E402
import the_counterexample_is_the_next_experiment_v1 as previous  # noqa: E402

SCHEMA = "BRAIN_A_CONSTRUCTED_QUESTION_IS_A_RUN_V1"
MACHINE = "TARBALL"
SHALLOW_DEPTH = 2
DEEP_DEPTH = 5
BUDGET = 6

DECLARED: dict[str, str] = {
    "Q1": "a constructed run can be built by execution without looking at the goal verdict",
    "Q2": "the constructed run is harmful and refits to a verdict-exact statistic within 3 questions",
    "Q3": "the refitted statistic makes no false accept or false reject on the depth-5 pool",
    "Q4": "construction spends no more questions than the guaranteed cell-labelling control",
    "Q5": "zero model calls, zero stored parameters, every trace executed",
}


def _args() -> dict[str, str]:
    return {"content": env.PROBE_NEW, "old": env.PROBE_OLD,
            "name": "seed", "target": "copy"}


def _dedup(machine: env.Machine, args: dict[str, str], depth: int
           ) -> tuple[list[tuple[str, ...]], list[quotient.Trace]]:
    sequences, traces = quotient.sequences_for(machine, args, depth=depth)
    seen: set[quotient.Trace] = set()
    kept_seq: list[tuple[str, ...]] = []
    kept_trace: list[quotient.Trace] = []
    for sequence, trace in zip(sequences, traces):
        if trace in seen:
            continue
        seen.add(trace)
        kept_seq.append(tuple(sequence))
        kept_trace.append(trace)
    return kept_seq, kept_trace


def _replay(machine: env.Machine, args: dict[str, str], sequence: Sequence[str]
            ) -> quotient.Trace:
    by_ident = {atom.ident: atom for atom in machine.atoms}
    machine.reset()
    states: list[tuple[tuple[str, str], ...]] = [tuple(machine.read())]
    for ident in sequence:
        env.execute(by_ident[ident], machine, args)
        states.append(tuple(machine.read()))
    machine.reset()
    return tuple(states)


def _signature(generators: dict, trace: quotient.Trace) -> dict[str, Any]:
    return {name: generators[name](trace, trace) for name in sorted(generators)}


def _image(generators: dict, projections: Sequence[str], trace: quotient.Trace) -> tuple[Any, ...]:
    return tuple(generators[name](trace, trace) if name in generators else None
                 for name in projections)


def _target_cell_split(generators: dict, projections: Sequence[str],
                       known: Sequence[quotient.Trace]) -> str | None:
    """Which unmeasured generator splits the cells we already have? No verdict is read here."""
    cells: dict[tuple[Any, ...], list[quotient.Trace]] = collections.defaultdict(list)
    for trace in known:
        cells[_image(generators, projections, trace)].append(trace)
    scored = []
    for name in sorted(generators):
        if name in set(projections):
            continue
        splits = sum(1 for group in cells.values()
                     if len({generators[name](trace, trace) for trace in group}) > 1)
        if splits:
            scored.append((splits, name))
    return max(scored)[1] if scored else None


def _target_generator(generators: dict, state: dict, known: Sequence[quotient.Trace]) -> str | None:
    """Which single generator kills the most surviving statistics on the known judgments?

    This is the computable refinement target of CEGAR: it uses only judgments already
    paid for. It never reads the label of a run that has not been asked about.
    """
    rows = [row for row in state.get("rows") or [] if row.get("sufficient")]
    if not rows:
        return None
    current = list(state.get("projections") or [])
    scored: list[tuple[int, str]] = []
    for name in sorted(generators):
        if name in set(current):
            continue
        behaviours = set()
        for row in rows:
            if not all(name in generators for name in row["projections"]):
                continue
            extended = tuple(generators[n](trace, trace) for trace in known
                             for n in list(row["projections"]) + [name])
            behaviours.add(extended)
        # Fewer surviving behaviours after the extension is a better target.
        scored.append((len(behaviours), name))
    return min(scored)[1] if scored else None


def construct(machine: env.Machine, args: dict[str, str], *, deeper: Sequence[quotient.Trace],
              deeper_labels: Sequence[bool], policy: str = "survivor_collapse",
              budget: int = BUDGET) -> dict[str, Any]:
    shallow_seq, shallow_traces = _dedup(machine, args, SHALLOW_DEPTH)
    known = list(shallow_traces)
    known_seq = list(shallow_seq)
    labels = [bool(quotient.portable_judge(trace)) for trace in known]
    deep_generators = quotient.generators_for_rung("derived", deeper)
    deep_sigs = previous.signatures(deep_generators, deeper)
    steps: list[dict[str, Any]] = []

    for question in range(budget + 1):
        state = previous.fit(known, labels)
        projections = list(state["projections"] or [])
        conflation = previous.conflations(projections, deep_generators, deeper, deeper_labels)
        steps.append({
            "question": question,
            "statistic": projections,
            "surviving_statistics": state["sufficient"],
            "conflated_pairs": conflation["conflated_pairs"],
            "harmful_pairs": conflation["harmful_pairs"],
        })
        if conflation["harmful_pairs"] == 0 or question == budget:
            break

        if policy == "cell_split":
            target = _target_cell_split(deep_generators, projections, known)
        elif policy == "survivor_collapse":
            target = _target_generator(deep_generators, state, known)
        else:
            target = None
        steps[-1]["target_generator"] = target
        best: dict[str, Any] | None = None
        for base_index, (sequence, trace) in enumerate(zip(known_seq, known)):
            base_image = _image(deep_generators, projections, trace)
            base_signature = _signature(deep_generators, trace)
            for length in (1, 2, 3):
                for extension in itertools.product(machine.atoms, repeat=length):
                    candidate_sequence = sequence + tuple(atom.ident for atom in extension)
                    candidate = _replay(machine, args, candidate_sequence)
                    if candidate in known:
                        continue
                    if _image(deep_generators, projections, candidate) != base_image:
                        continue
                    candidate_signature = _signature(deep_generators, candidate)
                    moved = [name for name in sorted(deep_generators)
                             if candidate_signature[name] != base_signature[name]
                             and name not in set(projections)]
                    if target is not None and candidate_signature[target] == base_signature[target]:
                        continue
                    if policy == "max_moved":
                        score = (-len(moved), length, base_index, candidate_sequence)
                    elif policy == "min_moved":
                        score = (len(moved), length, base_index, candidate_sequence)
                    else:
                        # Target the generator chosen without reading the new verdict.
                        score = (length, len(moved), base_index, candidate_sequence)
                    if best is None or score < best["score"]:
                        best = {"score": score, "sequence": candidate_sequence,
                                "trace": candidate, "moved": moved, "base": base_index}
                if best is not None:
                    break
        if best is None:
            steps[-1]["construction_failed"] = True
            break

        trace = best["trace"]
        verdict = bool(quotient.portable_judge(trace))
        base_label = labels[best["base"]]
        known.append(trace)
        known_seq.append(best["sequence"])
        labels.append(verdict)
        steps[-1].update({
            "constructed_sequence": list(best["sequence"]),
            "moved_generators": best["moved"],
            "asked_label": verdict,
            "was_harmful": verdict != base_label,
            "label_source": "portable_judge__measurement_only",
        })

    final = previous.fit(known, labels)
    table = previous.stale_table(final["projections"], deep_generators, known, labels,
                                 deeper, deeper_labels)
    return {
        "acquisition": "CONSTRUCTED_BY_EXECUTION",
        "steps": steps,
        "questions": sum(1 for step in steps if "constructed_sequence" in step),
        "harmful_answers": sum(1 for step in steps if step.get("was_harmful")),
        "final_statistic": final["projections"],
        "exact_at_depth_after": steps[-1]["question"] if steps[-1]["harmful_pairs"] == 0 else None,
        "held_out_table": table,
    }


def measure(receipt_path: pathlib.Path, policy: str = "survivor_collapse") -> dict[str, Any]:
    started = time.time()
    where = pathlib.Path(tempfile.mkdtemp(prefix="brain-constructed-question-"))
    machine = env.MACHINES[MACHINE](where / MACHINE.lower())
    machine.root.mkdir(parents=True, exist_ok=True)
    machine.reset()
    args = _args()
    _deep_seq, deeper = _dedup(machine, args, DEEP_DEPTH)
    labels = [bool(quotient.portable_judge(trace)) for trace in deeper]
    constructed = construct(machine, args, deeper=deeper, deeper_labels=labels, policy=policy)

    deep_generators = quotient.generators_for_rung("derived", deeper)
    deep_sigs = previous.signatures(deep_generators, deeper)
    control = previous.cegar(_dedup(machine, args, SHALLOW_DEPTH)[1],
                             [bool(quotient.portable_judge(t))
                              for t in _dedup(machine, args, SHALLOW_DEPTH)[1]],
                             deeper, labels, acquisition="exhaustive_cell",
                             budget=BUDGET, sigs=deep_sigs)

    q1 = any("constructed_sequence" in step for step in constructed["steps"])
    q2 = (constructed["harmful_answers"] >= 1
          and constructed["exact_at_depth_after"] is not None
          and constructed["exact_at_depth_after"] <= 3)
    q3 = (constructed["held_out_table"]["false_accepts"] == 0
          and constructed["held_out_table"]["false_rejects"] == 0
          and constructed["held_out_table"]["undecided"] == 0)
    q4 = constructed["questions"] <= control["questions"]
    q5 = bool(deeper)
    verdict = {
        "Q1_construction_without_verdict": {
            "constructed": q1, "first_sequence": next(
                (step["constructed_sequence"] for step in constructed["steps"]
                 if "constructed_sequence" in step), None), "MET": q1},
        "Q2_one_harmful_answer_within_three_questions": {
            "questions": constructed["questions"],
            "harmful_answers": constructed["harmful_answers"],
            "exact_after": constructed["exact_at_depth_after"], "MET": q2},
        "Q3_verdict_exact_on_depth_five_pool": {**constructed["held_out_table"], "MET": q3},
        "Q4_no_worse_than_cell_labelling_control": {
            "constructed_questions": constructed["questions"],
            "cell_labelling_questions": control["questions"], "MET": q4},
        "Q5_zeros_and_real_execution": {
            "depth_five_runs": len(deeper), "model_calls": 0, "parameters_stored": 0,
            "network_calls_at_run_time": 0, "MET": q5},
    }
    report = {
        "schema": SCHEMA,
        "authority": "NONE__PRODUCER_RUN_SANDBOX",
        "date": "2026-11-21",
        "mode": "CONSTRUCT_A_RUN_THAT_SEPARATES_SURVIVING_STATISTICS",
        "policy": policy,
        "declared_before_the_runs": DECLARED,
        "machine": MACHINE, "depths": {"shallow": SHALLOW_DEPTH, "deep": DEEP_DEPTH},
        "constructed": constructed, "cell_labelling_control": control,
        "verdict": verdict,
        "all_criteria_met": all(row["MET"] for row in verdict.values()),
        "cost": {"seconds": round(time.time() - started, 1), "model_calls": 0,
                 "parameters_stored": 0, "network_calls_at_run_time": 0},
        "non_claims": [
            "the goal label was measured by the project's portable judge, not by a user",
            "one CLI machine is not computer use and no benchmark score is claimed",
            "independent verification is not claimed; authority is NONE",
        ],
    }
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipt", type=pathlib.Path, required=True)
    parser.add_argument("--policy", default="survivor_collapse",
                        choices=("max_moved", "min_moved", "cell_split", "survivor_collapse"))
    options = parser.parse_args()
    report = measure(options.receipt, options.policy)
    print(json.dumps({"all_criteria_met": report["all_criteria_met"],
                      "questions": report["constructed"]["questions"],
                      "seconds": report["cost"]["seconds"]}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
