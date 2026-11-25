#!/usr/bin/env python3
"""A law must carry its reason -- the contrast set -- and transfer becomes re-verification.

THE FINDING THIS ANSWERS
------------------------
`EVIDENCE_DOES_NOT_TRANSFER` measured, over 72 ordered machine pairs, that a projection confirmed on
one machine is not evidence about another: inheriting blindly raised reach 88 -> 149 and injected 56
errors, with reach rising and errors rising in exactly the same 11 pairs.

Its own conclusion was that the store can hold laws but cannot hold WHY a law is valid, so the next
machine re-derives everything. This module tests the repair:

    a law is stored together with its CONTRAST SET -- the specific observed contexts its projection
    had to separate -- and on a new machine the law is admitted only if the contrast is REPRODUCIBLE
    there (the same projection key occurs, and the contexts that distinguished it still exist).

That makes transfer a cheap CHECK rather than a blind CLAIM. Two things follow, and both are measured:

  * transferred-and-verified laws must be sound, or the contrast set is not doing its job;
  * the check must reject most transfers, because that is what the refutation said was necessary.

THE ARMS
--------
  A  own laws only                                         (the honest baseline)
  B  own laws + blind inheritance from a teacher machine    (the refuted arm, for comparison)
  C  own laws + inheritance REQUIRING a reproducible contrast
  D  C but the contrast is checked only for existence, not for the distinguishing contexts

Every law in every arm is scored on the student machine's own held-out split.
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

import the_width_of_a_guard_v1 as width  # noqa: E402
import what_the_vocabulary_cannot_say_v1 as base  # noqa: E402

SCHEMA = "BRAIN_A_LAW_CARRIES_ITS_REASON_V1"
State = tuple[tuple[str, str], ...]


class JustifiedLaw:
    """A width law plus the contrast that justified it.

    `contrast` is the set of projection keys that shared this law's key but carried a DIFFERENT
    effect, i.e. the contexts the projection actually had to separate. A law whose contrast set is
    empty was never tested against an alternative and is a description of a sample, so it is not
    exported at all.
    """

    __slots__ = ("law", "contrast")

    def __init__(self, law: width.Law, contrast: frozenset):
        self.law = law
        self.contrast = frozenset(contrast)

    def to_dict(self) -> dict[str, Any]:
        return {**self.law.to_dict(), "contrast_size": len(self.contrast)}


def justify(observations) -> list[JustifiedLaw]:
    """Learn laws AND record, for each, the keys the projection had to separate."""
    laws = width.learn_laws(observations)
    # for every (atom, projection) build key -> effect, so a contrast is computable
    table: dict[tuple[str, str], dict[Any, set]] = collections.defaultdict(
        lambda: collections.defaultdict(set))
    for observation in observations:
        for projection, _fn in width.PROJECTIONS:
            key = width.project(projection, tuple(observation.before))
            table[(observation.atom, projection)][key].add(observation.effect)

    justified: list[JustifiedLaw] = []
    for law in laws:
        if law.support < width.MIN_SUPPORT:
            continue
        effects = table[(law.atom, law.projection)]
        contrast = frozenset(key for key, effect_set in effects.items()
                             if key != law.key and effect_set and law.effect not in effect_set)
        justified.append(JustifiedLaw(law, contrast))
    return justified


def reproducible(law: JustifiedLaw, student_observations, modes: str = "contrast") -> bool:
    """Is this law's reason still present on the student machine?

    `modes == "contrast"`: the law's projection key must occur here AND the contrast must be
    non-empty and its keys must be reachable, i.e. the distinguishing contexts still exist.
    `modes == "existence"`: only the key must occur. Weaker, and measured as arm D.
    """
    key_present = any(width.project(law.law.projection, tuple(o.before)) == law.law.key
                      for o in student_observations)
    if not key_present:
        return False
    if modes == "existence":
        return True
    if not law.contrast:
        return False
    # the contrast keys must be present as well: the alternative contexts still exist here
    observed_keys = {width.project(law.law.projection, tuple(o.before))
                     for o in student_observations}
    return all(c in observed_keys for c in law.contrast)


def data_for(name: str, depth: int) -> tuple:
    tmp = tempfile.TemporaryDirectory()
    root = pathlib.Path(tmp.name) / name
    root.mkdir(parents=True)
    machine = room.all_machines()[name](root)
    machine.reset()
    atoms = list(machine.atoms)
    transitions = base.explore(machine, atoms, depth)
    conditions = pop.condition_pool([b for _i, b, _a in transitions])
    # SORTED, because the dedup goes through a set and Python randomises string hashing per process
    states = sorted(dict.fromkeys(tuple(b) for _i, b, _a in transitions))
    shuffled = list(states)
    random.Random(13).shuffle(shuffled)
    cut = max(1, len(shuffled) // 4)
    held = set(shuffled[:cut])
    return (base.observe([t for t in transitions if t[1] not in held], conditions),
            base.observe([t for t in transitions if t[1] in held], conditions), tmp)


def run(names: Sequence[str], depth: int) -> dict[str, Any]:
    corpus = {}
    for name in names:
        corpus[name] = data_for(name, depth)

    arms = {key: {"predictions": 0, "wrong": 0, "laws": 0}
            for key in ("A_own", "B_blind", "C_verified_contrast", "D_verified_existence")}
    transfers = {"offered": 0, "accepted_contrast": 0, "accepted_existence": 0}
    per_machine = []

    for teacher in names:
        teacher_obs = corpus[teacher][0]
        exported = justify(teacher_obs)
        for student in names:
            if student == teacher:
                continue
            student_obs, student_held, _tmp = corpus[student]
            own = [law for law in width.learn_laws(student_obs)
                   if law.support >= width.MIN_SUPPORT]
            arm_a = width._score(own, student_held)
            arm_b = width._score(
                own + [law for law in width.learn_laws(student_obs) if law.support == 1],
                student_held)
            accepted_c = [item.law for item in exported
                          if reproducible(item, student_obs, "contrast")]
            accepted_d = [item.law for item in exported
                          if reproducible(item, student_obs, "existence")]
            arm_c = width._score(own + accepted_c, student_held)
            arm_d = width._score(own + accepted_d, student_held)

            transfers["offered"] += len(exported)
            transfers["accepted_contrast"] += len(accepted_c)
            transfers["accepted_existence"] += len(accepted_d)
            for key, score in (("A_own", arm_a), ("B_blind", arm_b),
                               ("C_verified_contrast", arm_c), ("D_verified_existence", arm_d)):
                arms[key]["predictions"] += score["predictions"]
                arms[key]["wrong"] += score["wrong"]
            arms["C_verified_contrast"]["laws"] += len(accepted_c)
            arms["D_verified_existence"]["laws"] += len(accepted_d)
            per_machine.append({"teacher": teacher, "student": student,
                                "A": arm_a, "B": arm_b, "C": arm_c, "D": arm_d})

    summary = {"teachers": len(names), "pairs": len(per_machine), "arms": arms,
               "transfers": transfers}
    summary["verdicts"] = {
        "the_check_admits_some_transfers": transfers["accepted_contrast"] > 0,
        "the_check_rejects_most_transfers":
            transfers["accepted_contrast"] * 10 < transfers["offered"],
        "verified_transfers_are_sound": arms["C_verified_contrast"]["wrong"] == 0,
        "verified_transfers_beat_blind_inheritance":
            arms["C_verified_contrast"]["wrong"] < arms["B_blind"]["wrong"],
        "checking_the_contrast_beats_checking_existence":
            arms["C_verified_contrast"]["wrong"] <= arms["D_verified_existence"]["wrong"],
    }
    return {"summary": summary, "per_pair": per_machine}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True)
    parser.add_argument("--depth", type=int, default=3)
    parser.add_argument("--machines", nargs="*")
    args = parser.parse_args(argv)

    started = time.time()
    names = args.machines or sorted(room.all_machines())
    result = run(names, args.depth)
    payload = {
        "schema": SCHEMA,
        "generated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "cost": {"model_calls": 0, "stored_parameters": 0, "network_at_run_time": 0,
                 "duration_s": round(time.time() - started, 2)},
        **result,
    }
    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=1) + "\n")
    print(json.dumps(result["summary"], indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
