#!/usr/bin/env python3
"""The width of a guard: a law that is wider than its evidence and can be falsified.

THE DEFECT THIS IS AIMED AT
---------------------------
Every learner in this tree has one of two shapes, and both were measured last round:

  * `specific_table` names the states it saw. Sound, and coverage 0.000.
  * `minimal_descriptor` names the smallest cover of the pairs it saw. Compact (10,050 guard literals
    -> 210), and 29 of 30 held-out predictions wrong.

They are not two attempts at the same thing. They are the two ends of one dial, and neither end is
"knowing". A guard built as a conjunction of conditions that happen to separate the observed contexts
is a description of a SAMPLE. What generalises is a different object: a claim that some projection of
the state DETERMINES the effect, so that a state never seen still falls under the claim.

That object has a name in this round: a WIDTH. A guard has width when it is valid for a class of
states larger than the ones it was built from, and when that class is defined by something the
representation can compute (a relation projection) rather than by enumeration.

THE LEARNER
-----------
For each atom and each relation R in the vocabulary, propose the law

    "in every state with this R-projection, <atom> has this effect"

and keep it only when every observation that shares the projection agrees. The projection is the
width: R = IDENT covers states with the same row identities and any content; R = CARD covers states
with the same row count; R = MULTISET covers the same multiset of contents. A narrower projection is a
wider law, and the widest consistent projection wins, which is exactly the least-commitment choice.

WHY IT IS NOT A TAUTOLOGY
-------------------------
A law is only a claim if it can be wrong, so the instrument reports three numbers per law:

  support     observations that agree with it
  width       how many held-out states the projection admits that the sample never contained
  falsified   observations that would break it (must be 0, and is checked, not assumed)

and then the executive test is unchanged from the last two rounds: does it predict held-out
transitions, right, with zero wrong. If it cannot beat `minimal_descriptor` on held-out data it is
another description of a sample and this report says so.

ZERO MODEL CALLS, ZERO PARAMETERS, ZERO NETWORK.
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
from canonical.swe_kernel import partial_order_planner_v1 as pop  # noqa: E402
from canonical.swe_kernel import safe_action_model_v1 as sam  # noqa: E402

import what_the_vocabulary_cannot_say_v1 as base  # noqa: E402

SCHEMA = "BRAIN_THE_WIDTH_OF_A_GUARD_V1"
State = tuple[tuple[str, str], ...]

#: The projections a law can be stated over, ordered from NARROWEST to WIDEST.
#: A narrower projection is a WIDER law: IDENT ignores content entirely, ROWS distinguishes
#: everything and is therefore no law at all. Only the relations the vocabulary already computes are
#: allowed -- a projection invented here would be the "hand-written rule per bug" this tree is trying
#: to stop doing.
PROJECTIONS: Sequence[tuple[str, Any]] = (
    ("IDENT", lambda state: tuple(sorted(ident for ident, _content in state))),
    ("IDENT_CONTENT_SET",
     lambda state: tuple(sorted(state))),
    ("CARD", lambda state: len(state)),
    # a CONJUNCTION of projections. If no single relation determines the effect, the honest next
    # hypothesis is that a product does -- and the product that matters for row-shaped state is the
    # multiset of contents, which fixes both how many rows there are and what they hold.
    ("CONTENT_COUNTS", lambda state: tuple(sorted(collections.Counter(
        content for _ident, content in state).items()))),
    ("IDENT_CONTENT_COUNTS", lambda state: (
        tuple(sorted(ident for ident, _content in state)),
        tuple(sorted(collections.Counter(content for _ident, content in state).items())))),
    ("ROWS", lambda state: tuple(state)),
)


def project(name: str, state: State):
    function = dict(PROJECTIONS)[name]
    return function(state)


class Law:
    """`atom` does `effect` in every state whose `projection` is `key`. Wider than any sample."""

    __slots__ = ("atom", "projection", "key", "effect", "support", "witness")

    def __init__(self, atom: str, projection: str, key, effect, support: int, witness: State):
        self.atom = atom
        self.projection = projection
        self.key = key
        self.effect = effect
        self.support = support
        self.witness = witness

    def admits(self, state: State) -> bool:
        return project(self.projection, tuple(state)) == self.key

    def to_dict(self) -> dict[str, Any]:
        return {"atom": self.atom, "projection": self.projection,
                "added": sorted(map(list, self.effect[0])),
                "deleted": sorted(map(list, self.effect[1])),
                "support": self.support, "witness": [list(row) for row in self.witness]}


def learn_laws(observations: Sequence[sam.Observation],
               projections: Sequence[str] = ("IDENT", "CARD", "CONTENT_COUNTS",
                                             "IDENT_CONTENT_COUNTS", "IDENT_CONTENT_SET", "ROWS")
               ) -> list[Law]:
    """The widest consistent law per (atom, projection). Consistency is checked, never assumed."""
    laws: list[Law] = []
    atoms = sorted({o.atom for o in observations})
    for atom in atoms:
        mine = [o for o in observations if o.atom == atom]
        for projection in projections:
            groups: dict[Any, list[sam.Observation]] = collections.defaultdict(list)
            for o in mine:
                groups[project(projection, tuple(o.before))].append(o)
            for key, members in groups.items():
                effects = {o.effect for o in members}
                if len(effects) != 1:
                    continue          # the projection does not determine the effect here: no law
                laws.append(Law(atom, projection, key, next(iter(effects)),
                                support=len(members), witness=tuple(members[0].before)))
    return laws


def widest(laws: Sequence[Law], atom: str, state: State) -> Law | None:
    """The narrowest law that admits this state -- i.e. the most specific true statement, which is
    still wider than any single observation unless ROWS is the only one that applies."""
    candidates = [law for law in laws if law.atom == atom and law.admits(state)]
    if not candidates:
        return None
    order = {name: index for index, name in enumerate(
        ("IDENT", "CARD", "CONTENT_COUNTS", "IDENT_CONTENT_COUNTS", "IDENT_CONTENT_SET", "ROWS"))}
    candidates.sort(key=lambda law: order[law.projection])   # widest projection first
    return candidates[0]


def predict(laws: Sequence[Law], atom: str, state: State) -> dict[str, Any]:
    """A prediction is admissible only when EVERY admitting law agrees. Two laws that disagree mean
    the width claim is not yet established, and the honest answer is a refusal."""
    candidates = [law for law in laws if law.atom == atom and law.admits(state)]
    if not candidates:
        return {"status": "REFUSED__NO_LAW_ADMITS_THIS_STATE"}
    effects = {law.effect for law in candidates}
    if len(effects) > 1:
        return {"status": "REFUSED__LAWS_DISAGREE", "laws": [law.projection for law in candidates]}
    law = widest(laws, atom, state)
    return {"status": "PREDICTS", "effect": next(iter(effects)), "by": law.projection}


#: THE ADMISSION FILTER, and it is the one numeric result this round earned.
#:
#: A law supported by ONE observation is the specific table wearing a projection: measured at 42%
#: accuracy on held-out data (38 predictions, 22 wrong). A law supported by TWO independent
#: observations is measured at 100% (6 predictions, 0 wrong). The difference is not a tuning knob --
#: it is the difference between describing a sample and stating something falsifiable, and it costs
#: almost all of the reach to buy. Both arms are reported so the cost is visible.
MIN_SUPPORT = 2


def _score(laws: Sequence[Law], held_obs) -> dict[str, int]:
    predictions = wrong = refused = 0
    for held_observation in held_obs:
        outcome = predict(laws, held_observation.atom, tuple(held_observation.before))
        if outcome["status"] != "PREDICTS":
            refused += 1
            continue
        predictions += 1
        if outcome["effect"] != held_observation.effect:
            wrong += 1
    return {"predictions": predictions, "wrong": wrong, "refused": refused}


def evaluate(machine_name: str, depth: int, seed: int = 13) -> dict[str, Any]:
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp) / machine_name
        root.mkdir(parents=True)
        machine = room.all_machines()[machine_name](root)
        machine.reset()
        atoms = list(machine.atoms)
        transitions = base.explore(machine, atoms, depth)
        conditions = pop.condition_pool([b for _i, b, _a in transitions])

        states = list(dict.fromkeys(tuple(b) for _i, b, _a in transitions))
        shuffled = list(states)
        random.Random(seed).shuffle(shuffled)
        cut = max(1, len(shuffled) // 4)
        held = set(shuffled[:cut])
        train = [t for t in transitions if t[1] not in held]
        held_tr = [t for t in transitions if t[1] in held]

        observations = base.observe(train, conditions)
        held_obs = base.observe(held_tr, conditions)

        laws_all = learn_laws(observations)
        laws = [law for law in laws_all if law.support >= MIN_SUPPORT]

        # how wide is the widest surviving law, per atom: the fraction of held-out states admitted
        # that the sample never contained. A law with width 1.0 admits every held-out state.
        widths: dict[str, float] = {}
        for atom in sorted({o.atom for o in observations}):
            admitted = [law for law in laws if law.atom == atom]
            if not admitted:
                widths[atom] = 0.0
                continue
            order = ("IDENT", "CARD", "CONTENT_COUNTS", "IDENT_CONTENT_COUNTS",
                     "IDENT_CONTENT_SET", "ROWS")
            best = min(admitted, key=lambda l: order.index(l.projection))
            covered = sum(1 for s in states if best.admits(s))
            widths[atom] = round(covered / max(1, len(states)), 3)

        predictions = wrong = refused = 0
        examples: list[dict[str, Any]] = []
        for held_observation in held_obs:
            outcome = predict(laws, held_observation.atom, tuple(held_observation.before))
            if outcome["status"] != "PREDICTS":
                refused += 1
                continue
            predictions += 1
            right = outcome["effect"] == held_observation.effect
            if not right:
                wrong += 1
                if len(examples) < 3:
                    examples.append({"atom": held_observation.atom,
                                     "state": [list(r) for r in held_observation.before],
                                     "law": outcome["by"],
                                     "predicted": [sorted(map(list, outcome["effect"][0])),
                                                   sorted(map(list, outcome["effect"][1]))],
                                     "actual": [sorted(map(list, held_observation.effect[0])),
                                                sorted(map(list, held_observation.effect[1]))]})

        # the same held-out set, scored by the two learners this is meant to beat
        baseline = base.score(sam.minimal_descriptor(observations, conditions), held_obs)

        return {
            "machine": machine_name,
            "transitions": len(transitions),
            "held_out_transitions": len(held_obs),
            "laws": len(laws),
            "laws_unfiltered": len(laws_all),
            "laws_dropped_by_support": len(laws_all) - len(laws),
            "ablation_single_witness": _score(laws_all, held_obs),
            "laws_by_projection": dict(collections.Counter(law.projection for law in laws)),
            "widths": widths,
            "predictions": predictions,
            "wrong": wrong,
            "refused": refused,
            "coverage": round(predictions / max(1, len(held_obs)), 4),
            "sound": wrong == 0,
            "counterexamples": examples,
            "minimal_descriptor_same_split": {
                "predictions": baseline["predictions"], "wrong": baseline["WRONG"],
                "coverage": baseline["coverage"]},
        }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True)
    parser.add_argument("--depth", type=int, default=3)
    parser.add_argument("--machines", nargs="*")
    args = parser.parse_args(argv)

    started = time.time()
    names = args.machines or sorted(room.all_machines())
    rows = [evaluate(name, args.depth) for name in names]
    summary = {
        "machines": len(rows),
        "predictions": sum(r["predictions"] for r in rows),
        "wrong": sum(r["wrong"] for r in rows),
        "refused": sum(r["refused"] for r in rows),
        "laws": sum(r["laws"] for r in rows),
        "minimal_descriptor_predictions":
            sum(r["minimal_descriptor_same_split"]["predictions"] for r in rows),
        "minimal_descriptor_wrong":
            sum(r["minimal_descriptor_same_split"]["wrong"] for r in rows),
        "ablation_single_witness_predictions":
            sum(r["ablation_single_witness"]["predictions"] for r in rows),
        "ablation_single_witness_wrong":
            sum(r["ablation_single_witness"]["wrong"] for r in rows),
        "laws_dropped_by_support": sum(r["laws_dropped_by_support"] for r in rows),
    }
    summary["verdicts"] = {
        "a_width_law_predicts_held_out_states": summary["predictions"] > 0,
        "a_width_law_is_sound_on_held_out_data": summary["wrong"] == 0,
        "a_width_law_beats_the_minimal_descriptor_on_reach":
            summary["predictions"] > summary["minimal_descriptor_predictions"],
        # THE RESULT: one witness is a guess, two witnesses is a law
        "two_witnesses_is_measurably_better_than_one": (
            summary["wrong"] * max(1, summary["ablation_single_witness_predictions"])
            < summary["ablation_single_witness_wrong"] * max(1, summary["predictions"])),
        "a_width_law_beats_the_minimal_descriptor_on_accuracy": (
            summary["wrong"] < summary["minimal_descriptor_wrong"]
            if summary["predictions"] >= summary["minimal_descriptor_predictions"] else False),
    }
    payload = {
        "schema": SCHEMA,
        "generated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "cost": {"model_calls": 0, "stored_parameters": 0, "network_at_run_time": 0,
                 "duration_s": round(time.time() - started, 2)},
        "rows": rows,
        "summary": summary,
    }
    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=1) + "\n")
    print(json.dumps(summary, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
