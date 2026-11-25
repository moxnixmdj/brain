#!/usr/bin/env python3
"""What the vocabulary cannot say, computed rather than lamented.

THE QUESTION
------------
Every previous round in this tree hit the same wall from a different side:

  * `witness_inversion_v1`: invert the failure. 18 real witnesses, 0 verified -- "an inverter selects
    over existing content, and the answer is new content."
  * `THE_PLAN_IS_A_PARTIAL_ORDER`: induce operators. 8 of 12 plans refuted -- the guards admitted
    states the vocabulary could not tell apart.
  * `ONE_EXPERIENCE_EVERY_CONSEQUENCE`: be safe instead. 0 wrong predictions, 0 coverage -- the
    guard that keeps a model sound is a description of one state, because the vocabulary has no
    other way to name a state.

All three are one statement: **the representation is the artifact, and it is short by exactly those
distinctions the behaviour needs.** So the measurement this round makes is not "how much did we learn
from one experience" but "how many behavioural distinctions does the current vocabulary fail to
express, and can a computed extension remove them".

WHAT IS MEASURED, IN ORDER
--------------------------
  1. ALIASES   pairs of states the vocabulary gives the same signature, where some atom was
               OBSERVED to behave differently. Each is a fact the model must refuse or get wrong.
  2. EXTENSION the smallest computed set of discriminators that separates all of them (greedy set
               cover over a fixed, justified candidate set).
  3. PURITY    impure cells before and after. A cell is (atom, signature) -> set of observed
               effects; more than one effect is a context the vocabulary cannot express. This is
               the number that decides whether an induced operator is a description or a fiction.
  4. TRANSFER  the executive test. Learn a safe table on TRAIN with the old vocabulary and with the
               extended one, then predict held-out transitions. Right/wrong, and coverage.
               Predicted: wrong stays 0 (that is what safety buys) and coverage RISES (that is what
               a new column buys). If coverage does not rise, the extension is not the missing
               distinction and the report says so.
  5. ABLATION  the same with the extension REMOVED, and with each discriminator alone, so the gain
               is attributed to a named column rather than to "adding stuff".

Every number is produced by execution. Zero model calls, zero parameters, zero network.
"""
from __future__ import annotations

import argparse
import collections
import json
import pathlib
import random
import sys
import tempfile
import time
from typing import Any, Sequence

TOOLS = pathlib.Path(__file__).resolve().parent
REPO = TOOLS.parents[1]
for path in (str(TOOLS), str(REPO)):
    if path not in sys.path:
        sys.path.insert(0, path)

import frames_that_cross_machines_v1 as room  # noqa: E402
from canonical.swe_kernel import canonical_frame_v1 as cf  # noqa: E402
from canonical.swe_kernel import partial_order_planner_v1 as pop  # noqa: E402
from canonical.swe_kernel import safe_action_model_v1 as sam  # noqa: E402
from canonical.swe_kernel import the_distinction_is_created_v1 as distinct  # noqa: E402

SCHEMA = "BRAIN_WHAT_THE_VOCABULARY_CANNOT_SAY_V1"
State = tuple[tuple[str, str], ...]


def read(machine: Any) -> State:
    return tuple(map(tuple, machine.read()))


def execute_atom(atom: Any, machine: Any) -> State:
    room.base.execute(atom, machine, room.cell_args(machine.read(), "TARGET_ABSENT"))
    return read(machine)


def explore(machine: Any, atoms: Sequence[Any], depth: int) -> list[tuple[str, State, State]]:
    """Every (atom, before, after) reachable within `depth`, deduplicated by (atom, before)."""
    seen: set[tuple[str, State]] = set()
    transitions: list[tuple[str, State, State]] = []
    frontier: list[tuple[tuple[str, ...], State]] = [((), read(machine))]
    for _level in range(depth):
        nxt = []
        for prefix, state in frontier:
            for atom in atoms:
                machine.reset()
                for ident in prefix:
                    execute_atom(next(a for a in atoms if a.ident == ident), machine)
                after = execute_atom(atom, machine)
                key = (atom.ident, state)
                if key not in seen:
                    seen.add(key)
                    transitions.append((atom.ident, state, after))
                nxt.append((prefix + (atom.ident,), after))
        frontier = nxt
    machine.reset()
    return transitions


def vocabulary_transitions(transitions, conditions):
    """The same transitions, with each state replaced by its condition SET so the safe-model code can
    be reused unchanged. This is the bridge that keeps one machinery instead of two."""
    return [(ident, frozenset(c for c in conditions if sam.holds(c, before)),
             frozenset(c for c in conditions if sam.holds(c, after)))
            for ident, before, after in transitions]


def observe(transitions, conditions):
    """Observations in the safe model's own form, built from the transition list."""
    out = []
    for ident, before, after in transitions:
        out.append(sam.Observation(ident, tuple(before), tuple(after),
                                   frozenset(c for c in conditions
                                             if sam.holds(c, after) and not sam.holds(c, before)),
                                   frozenset(c for c in conditions
                                             if sam.holds(c, before) and not sam.holds(c, after))))
    return out


def score(table, held_out_observations) -> dict[str, Any]:
    made = right = wrong = refused = 0
    for held in held_out_observations:
        outcome = sam.apply(table, held.atom, held.before)
        if outcome.status != "APPLIES":
            refused += 1
            continue
        made += 1
        if (outcome.operator.added, outcome.operator.deleted) == held.effect:
            right += 1
        else:
            wrong += 1
    return {"predictions": made, "right": right, "WRONG": wrong, "refused": refused,
            "coverage": round(made / max(1, made + refused), 4), "sound": wrong == 0}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="what the vocabulary cannot say")
    parser.add_argument("--out", required=True)
    parser.add_argument("--depth", type=int, default=3)
    parser.add_argument("--machines", nargs="*")
    options = parser.parse_args(argv)
    started = time.time()

    for name, function in distinct.DISCRIMINATORS.items():
        sam.register_derived(name, function)

    builds = room.all_machines()
    names = options.machines or sorted(builds)
    rows: list[dict[str, Any]] = []

    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)
        for name in sorted(k for k in builds if k in names):
            (root / name).mkdir(parents=True, exist_ok=True)
            machine = builds[name](root / name)
            machine.reset()
            atoms = list(machine.atoms)
            transitions = explore(machine, atoms, options.depth)
            states = [before for _i, before, _a in transitions] + \
                     [after for _i, _b, after in transitions]
            base = pop.condition_pool(states)

            # An honest split: the learner never sees the held-out transitions.
            shuffled = list(transitions)
            random.Random(13).shuffle(shuffled)
            split = max(1, len(shuffled) // 4)
            held_raw, train_raw = shuffled[:split], shuffled[split:]

            aliases = distinct.find_aliases(train_raw, base, sam.holds)
            chosen, leftover, cover_report = distinct.minimal_extension(aliases)
            derived = distinct.derived_conditions(chosen, states)
            extended = list(base) + derived

            purity_before = distinct.purity(train_raw, base, sam.holds)
            purity_after = distinct.purity(train_raw, extended, sam.holds)

            def learn(conditions):
                observations = observe(train_raw, conditions)
                table = sam.specific_table(observations, conditions)
                table, _report = sam.generalize(table, observations, conditions)
                return table

            def learn_minimal(conditions):
                return sam.minimal_descriptor(observe(train_raw, conditions), conditions)

            def learn_minimal_then_trim(conditions):
                """The tension this round measured, built so it cannot be waved away.

                Generalization works by REMOVING redundant guard literals. A minimal descriptor has
                exactly the literals it needs, so the first removal leaves an empty guard -- and an
                empty guard asserts one context's effect in every state, which is the unsoundness
                that produced 10 wrong of 11 predictions two rounds ago. Compactness and
                trimmability are in direct tension, and this learner is the measurement of it.
                """
                observations = observe(train_raw, conditions)
                table = sam.minimal_descriptor(observations, conditions)
                trimmed = [sam.dataclasses.replace(op, guard=frozenset())
                           if len(op.guard) <= 1 else op for op in table]
                return trimmed

            held_base = observe(held_raw, base)
            held_ext = observe(held_raw, extended)
            score_base = score(learn(base), held_base)
            score_ext = score(learn(extended), held_ext)
            score_minimal = score(learn_minimal(base), held_base)
            score_minimal_trimmed = score(learn_minimal_then_trim(base), held_base)
            on_own_data = score(learn_minimal(base), observe(train_raw, base))
            literals = {
                "full_signature_then_trimmed": sum(len(op.guard) for op in learn(base)),
                "minimal_descriptor": sum(len(op.guard) for op in learn_minimal(base)),
                "minimal_then_trimmed": sum(len(op.guard)
                                            for op in learn_minimal_then_trim(base)),
            }

            # ABLATION: each discriminator alone, so the gain is attributed to a named column.
            ablation = {}
            for candidate in chosen:
                alone = list(base) + distinct.derived_conditions([candidate], states)
                ablation[candidate] = {
                    **score(learn(alone), observe(held_raw, alone)),
                    **distinct.purity(train_raw, alone, sam.holds),
                }

            rows.append({
                "machine": name,
                "atoms": len(atoms),
                "transitions": len(transitions),
                "held_out": len(held_raw),
                "conditions_from_frames": len(base),
                "aliases_observed": len(aliases),
                "aliased_atoms": sorted({alias.atom for alias in aliases}),
                "extension_chosen": chosen,
                "extension_left_over_pairs": len(leftover),
                "cover_report": cover_report,
                "purity_before": purity_before,
                "purity_after": purity_after,
                "literals": literals,
                "minimal_descriptor_on_its_own_training_data": on_own_data,
                "held_out_scored_with_minimal_descriptors": score_minimal,
                "held_out_scored_with_minimal_then_trimmed": score_minimal_trimmed,
                "held_out_scored_with_the_frames_only": score_base,
                "held_out_scored_with_the_created_distinction": score_ext,
                "ablation_each_column_alone": ablation,
            })
            machine.reset()

    summary = {
        "machines": len(rows),
        "aliases_observed": sum(row["aliases_observed"] for row in rows),
        "machines_with_an_alias": sum(1 for row in rows if row["aliases_observed"]),
        "aliases_left_unseparated": sum(row["extension_left_over_pairs"] for row in rows),
        "impure_cells_before": sum(row["purity_before"]["impure_cells"] for row in rows),
        "impure_cells_after": sum(row["purity_after"]["impure_cells"] for row in rows),
        "held_out_predictions_frames_only":
            sum(row["held_out_scored_with_the_frames_only"]["predictions"] for row in rows),
        "held_out_predictions_with_distinction":
            sum(row["held_out_scored_with_the_created_distinction"]["predictions"] for row in rows),
        "held_out_WRONG_frames_only":
            sum(row["held_out_scored_with_the_frames_only"]["WRONG"] for row in rows),
        "held_out_WRONG_with_distinction":
            sum(row["held_out_scored_with_the_created_distinction"]["WRONG"] for row in rows),
        "literals": {key: sum(row["literals"][key] for row in rows)
                     for key in ("full_signature_then_trimmed", "minimal_descriptor",
                                 "minimal_then_trimmed")},
        "minimal_on_its_own_data_WRONG":
            sum(row["minimal_descriptor_on_its_own_training_data"]["WRONG"] for row in rows),
        "minimal_on_its_own_data_predictions":
            sum(row["minimal_descriptor_on_its_own_training_data"]["predictions"] for row in rows),
        "minimal_held_out_WRONG":
            sum(row["held_out_scored_with_minimal_descriptors"]["WRONG"] for row in rows),
        "minimal_held_out_predictions":
            sum(row["held_out_scored_with_minimal_descriptors"]["predictions"] for row in rows),
        "minimal_then_trimmed_held_out_WRONG":
            sum(row["held_out_scored_with_minimal_then_trimmed"]["WRONG"] for row in rows),
        "columns_ever_needed": sorted({name for row in rows for name in row["extension_chosen"]}),
        "columns_never_needed": sorted(set(distinct.DISCRIMINATORS)
                                       - {name for row in rows
                                          for name in row["extension_chosen"]}),
    }
    summary["verdicts"] = {
        "the_frames_alone_cannot_separate_some_states": summary["aliases_observed"] > 0,
        "a_computed_extension_separates_them_all": summary["aliases_left_unseparated"] == 0,
        "the_extension_reduces_inexpressible_contexts":
            summary["impure_cells_after"] < summary["impure_cells_before"],
        "the_extension_buys_predictions_on_held_out_states":
            summary["held_out_predictions_with_distinction"]
            > summary["held_out_predictions_frames_only"],
        "safety_is_preserved_by_the_extension":
            summary["held_out_WRONG_with_distinction"] == 0,
        "the_frames_are_redundant_by_a_large_factor":
            summary["literals"]["minimal_descriptor"] * 8
            < summary["literals"]["full_signature_then_trimmed"] + 1,
        "a_minimal_descriptor_is_exact_on_what_it_saw":
            summary["minimal_on_its_own_data_WRONG"] == 0,
        "a_minimal_descriptor_is_WRONG_on_states_it_did_not_see":
            summary["minimal_held_out_WRONG"] > 0,
        # NOT a headline number: hoisting a guard to `True` never cites, so `WRONG == 0` is true by
        # definition and buys nothing. It is recorded because it is the degenerate end of the
        # soundness/coverage trade, and calling it a win would be exactly the kind of tautology this
        # repository's integrity guard exists to catch.
        "trimming_is_sound_only_because_it_never_cites":
            summary["minimal_then_trimmed_held_out_WRONG"] == 0
            and summary["literals"]["minimal_then_trimmed"] == 0
            and sum(row["held_out_scored_with_minimal_then_trimmed"]["predictions"]
                    for row in rows) == 0,
    }

    report = {"schema": SCHEMA, "authority": "NONE__PRODUCER_RUN_SANDBOX_MEASUREMENT",
              "date": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
              "results": {"summary": summary, "rows": rows},
              "cost": {"model_calls": 0, "stored_parameters": 0, "network_at_run_time": 0,
                       "duration_s": round(time.time() - started, 2)}}
    text = json.dumps(report, indent=2, default=str)
    pathlib.Path(options.out).write_text(text, encoding="utf-8")
    print(json.dumps(summary, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
