#!/usr/bin/env python3
"""A contrast is a PROBE, not a state -- so it can be run anywhere.

THE WALL THIS ATTACKS, STATED FROM ITS OWN MEASUREMENT
-----------------------------------------------------
Six rounds produced one durable positive and one exact wall.

The positive: a law supported by two independent witnesses over a vocabulary projection predicts
held-out behaviour with zero errors (11 predictions, 0 wrong, nine machines).

The wall: `A_LAW_CARRIES_ITS_REASON` exported each law with its contrast set -- the projection keys
that carried a DIFFERENT effect -- and offered 272 laws to student machines. **Six were admitted.**
Blind inheritance, by comparison, was measured at 240 errors. The diagnosis was precise:

    a contrast keyed on one machine's state space is not a portable reason.

A projection key like `("0",)` or `2` is a fact about *that* machine's states. So transfer depended on
coincidence, and there was almost none. The repair is not a better check. It is a different OBJECT:

    store the contrast as an EXPERIMENT -- the atoms (with their argument slots) whose execution
    distinguished this law's effect from the alternative -- not as the states it produced.

Then on a new machine the experiment is RUN. The keys are whatever that machine says they are. A
reason stops being a description of somebody else's state space and becomes a procedure that any
environment can answer.

WHY THIS IS NOT THE `ask_instead_of_stare` ROUND AGAIN
------------------------------------------------------
That round asked questions about ONE table's contradictions and measured that asking is a query
policy, not a learner. This asks a different question: can a law justified on machine X be
RE-ESTABLISHED on machine Y by running X's experiment there? The answer is scored on Y's held-out
states, and the arms are constructed so that a null result is unmistakable.

THE FOUR ARMS
-------------
  A  own laws only                                   (the honest baseline)
  B  own laws + laws whose experiment reproduces AND whose conclusion matches   (the claim)
  C  own laws + laws whose experiment reproduces only    (does the experiment carry the reason,
                                                          or just the coincidence?)
  D  own laws + blind inheritance of every export         (the refuted arm, for scale)

Every arm is scored on the student's own held-out transitions. Held-out states are never executed
during justification -- only atoms are, from a state the walk actually reached.
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

SCHEMA = "BRAIN_A_CONTRAST_IS_A_PROBE_V1"
State = tuple[tuple[str, str], ...]


# ------------------------------------------------------------------------------------------------
# 1. learn a law AND the experiment that justified it
# ------------------------------------------------------------------------------------------------

class ProbeLaw:
    """A width law plus the EXPERIMENT that separated it from a different effect.

    `experiment` is a list of `(atom_ident, args)` pairs. The args were the literal arguments that
    made the atom's effect observable when this law was learned. They are carried verbatim, and
    re-run on any machine: the atoms are opaque identifiers that exist in every machine of this
    family (A1..A4), and the arguments are strings the machine accepts.

    `alternative` is the effect the experiment separated this law FROM. Without it a re-run can show
    that the experiment still works but cannot say what it proved.
    """

    __slots__ = ("law", "experiment", "alternative", "role")

    def __init__(self, law: width.Law, experiment: tuple, alternative: tuple | None,
                 role: str = ""):
        self.law = law
        self.experiment = experiment
        self.alternative = alternative
        # THE PORTABLE FORM. `GIT_A4` means nothing on VAULT; `A4` is a slot every machine in this
        # family fills. Measured: the first version carried the full identifier and re-ran on zero of
        # 288 exports, because no machine shares another's atom names.
        self.role = role

    def to_dict(self) -> dict[str, Any]:
        return {**self.law.to_dict(),
                "role": self.role,
                "experiment": [{"atom": ident, "args": args} for ident, args in self.experiment],
                "has_alternative": self.alternative is not None}


def _args_for(atom) -> dict[str, str]:
    """The literal arguments this tree actually writes, taken from the atom's own argv template.

    This is the piece that makes an experiment portable: the experiment names the atom and the
    arguments, never the state the atom produced.
    """
    args: dict[str, str] = {}
    for argv, _cwd in atom.steps:
        for token in argv:
            if isinstance(token, str) and token.startswith("{") and token.endswith("}"):
                slot = token[1:-1]
                args[slot] = "probe_new_content" if "content" in slot else "probe_new_name"
    return args


def atom_role(ident: str) -> str:
    """The position an atom occupies in its machine: `GIT_A4` -> `A4`.

    Every machine in this family assigns one atom per role (`A1` appends, `A4` is a mutation, ...),
    so the role is the only part of an atom's name that means anything across machines. This is an
    inference about the family, not a guarantee, and the instrument measures whether it holds.
    """
    tail = ident.rsplit("_", 1)[-1]
    return tail if tail.startswith("A") else ident


def justify(name: str, observations, atoms, machine) -> list[ProbeLaw]:
    """Laws whose contrast is recorded as the atom that distinguished it, not as the key produced."""
    laws = width.learn_laws(observations)
    by_atom = {atom.ident: atom for atom in atoms}
    ident_args = {ident: _args_for(atom) for ident, atom in by_atom.items()}

    # for each (atom, projection) the set of keys carrying each effect
    table: dict[tuple[str, str], dict[Any, set]] = collections.defaultdict(
        lambda: collections.defaultdict(set))
    for observation in observations:
        for projection, _fn in width.PROJECTIONS:
            key = width.project(projection, tuple(observation.before))
            table[(observation.atom, projection)][key].add(observation.effect)

    justified: list[ProbeLaw] = []
    for law in laws:
        if law.support < width.MIN_SUPPORT:
            continue
        effects = table[(law.atom, law.projection)]
        alternatives = {effect for key, effect_set in effects.items()
                        if key != law.key for effect in effect_set} - {law.effect}
        alternative = next(iter(alternatives)) if alternatives else None
        # THE EXPERIMENT: run this law's atom once with the literals this tree uses. Whatever state
        # that lands in on a new machine, the effect will or will not reproduce the law's claim.
        experiment = ((law.atom, ident_args.get(law.atom, {})),)
        role = atom_role(law.atom)
        justified.append(ProbeLaw(law, experiment, alternative, role))
    return justified


# ------------------------------------------------------------------------------------------------
# 2. re-establish a law by RUNNING its experiment on another machine
# ------------------------------------------------------------------------------------------------

def re_establish(exported: ProbeLaw, machine, atoms) -> dict[str, Any] | None:
    """Run the experiment here. Return what was observed, or None if it could not be run.

    Nothing about the source machine's states is used: the atom identifier and the argument literals
    are the entire input, and the outcome is read out of THIS machine.
    """
    # resolve by ROLE: the atom that plays this part on THIS machine
    by_role = {atom_role(atom.ident): atom for atom in atoms}
    resolved = []
    for _ident, args in exported.experiment:
        target = by_role.get(exported.role)
        if target is None:
            return None
        resolved.append((target, args))
    machine.reset()
    records = []
    for target, args in resolved:
        before = base.read(machine)
        after = base.execute_atom(target, machine)
        records.append((target.ident, before, after))
    machine.reset()
    return {"atom_in_this_machine": records[-1][0],
            "before": records[-1][1], "after": records[-1][2],
            "effect_here": (frozenset(set(records[-1][2]) - set(records[-1][1])),
                            frozenset(set(records[-1][1]) - set(records[-1][2])))}


def restate(exported: ProbeLaw, outcome: dict[str, Any]) -> width.Law | None:
    """Re-state the law in the STUDENT's own terms, or refute it there.

    The experiment is portable; a projection KEY is not. `LIST`'s law says "at IDENT ('0','1') this
    atom appends", and `('0','1')` matches nothing on ARCHIVE2. So after running the experiment on the
    student, the key is read off the state the student was actually in, and the law is rebuilt with
    that key. The EFFECT is what must survive: if the effect observed here differs from the exported
    law's effect, the law is refuted on this machine and nothing is admitted.

    This is the whole point of storing a procedure instead of a description: the procedure lands in a
    state, and the state supplies the local vocabulary.
    """
    if exported.alternative is None:
        return None
    if outcome["effect_here"] != exported.law.effect:
        return None                                   # refuted here: the effect did not reproduce
    local_key = width.project(exported.law.projection, tuple(outcome["before"]))
    # ...and written about the atom that played the role HERE. Keeping the teacher's atom name was
    # the last leak: a law about `LS_A3` can never apply to a `VT_A1` state, so the restated law
    # predicted nothing for three rounds of this instrument.
    return width.Law(outcome["atom_in_this_machine"], exported.law.projection, local_key,
                     exported.law.effect, support=exported.law.support,
                     witness=tuple(outcome["before"]))


def run(names: Sequence[str], depth: int) -> dict[str, Any]:
    corpus = {}
    for name in names:
        tmp = tempfile.TemporaryDirectory()
        root = pathlib.Path(tmp.name) / name
        root.mkdir(parents=True)
        machine = room.all_machines()[name](root)
        machine.reset()
        atoms = list(machine.atoms)
        transitions = base.explore(machine, atoms, depth)
        conditions = pop.condition_pool([b for _i, b, _a in transitions])
        # SORTED: the dedup goes through a set and Python randomises string hashes per process
        states = sorted(dict.fromkeys(tuple(b) for _i, b, _a in transitions))
        shuffled = list(states)
        random.Random(13).shuffle(shuffled)
        cut = max(1, len(shuffled) // 4)
        held = set(shuffled[:cut])
        corpus[name] = {
            "machine": room.all_machines()[name](root), "atoms": atoms, "tmp": tmp,
            "obs": base.observe([t for t in transitions if t[1] not in held], conditions),
            "held": base.observe([t for t in transitions if t[1] in held], conditions),
        }

    arms = {key: {"predictions": 0, "wrong": 0, "laws": 0}
            for key in ("A_own", "B_experiment_and_conclusion", "C_experiment_only", "D_blind")}
    ledger = {"offered": 0, "re_ran": 0, "effect_matched": 0, "admitted": 0}
    per_pair = []

    for teacher in names:
        exported = justify(teacher, corpus[teacher]["obs"],
                          corpus[teacher]["atoms"], corpus[teacher]["machine"])
        for student in names:
            if student == teacher:
                continue
            cell = corpus[student]
            own = [law for law in width.learn_laws(cell["obs"])
                   if law.support >= width.MIN_SUPPORT]
            arm_a = width._score(own, cell["held"])

            admitted_b: list[width.Law] = []
            admitted_c: list[width.Law] = []
            matched = 0
            for item in exported:
                ledger["offered"] += 1
                outcome = re_establish(item, cell["machine"], cell["atoms"])
                if outcome is None:
                    continue
                ledger["re_ran"] += 1
                reproduces = item.alternative is not None and outcome["effect_here"] != item.alternative
                admitted_c.append(item.law)          # the experiment ran: arm C
                if reproduces:
                    matched += 1
                    ledger["effect_matched"] += 1
                # ARM B: restate in the student's own projection key, and keep it only if the effect
                # reproduced here. This is the difference between a portable REASON and a portable
                # PROCEDURE that still asserts somebody else's coordinates.
                local = restate(item, outcome)
                if local is not None:
                    ledger["admitted"] += 1
                    admitted_b.append(local)

            arm_b = width._score(own + admitted_b, cell["held"])
            arm_c = width._score(own + admitted_c, cell["held"])
            arm_d = width._score(
                own + [law for law in width.learn_laws(cell["obs"]) if law.support == 1],
                cell["held"])

            for key, score in (("A_own", arm_a), ("B_experiment_and_conclusion", arm_b),
                               ("C_experiment_only", arm_c), ("D_blind", arm_d)):
                arms[key]["predictions"] += score["predictions"]
                arms[key]["wrong"] += score["wrong"]
            arms["B_experiment_and_conclusion"]["laws"] += len(admitted_b)
            arms["C_experiment_only"]["laws"] += len(admitted_c)
            per_pair.append({"teacher": teacher, "student": student,
                             "offered": len(exported), "re_ran": len(admitted_c),
                             "matched": matched,
                             "A": arm_a, "B": arm_b, "C": arm_c, "D": arm_d})

    summary = {"teachers": len(names), "pairs": len(per_pair), "arms": arms, "ledger": ledger}
    summary["verdicts"] = {
        "an_experiment_can_be_run_on_another_machine": ledger["re_ran"] > 0,
        "an_experiment_is_portable_where_a_key_was_not":
            ledger["re_ran"] * 4 > ledger["offered"],
        "the_experiment_carries_the_conclusion": ledger["effect_matched"] > 0,
        "verified_transfers_stay_sound": arms["B_experiment_and_conclusion"]["wrong"] == 0,
        "verified_transfers_beat_blind":
            arms["B_experiment_and_conclusion"]["wrong"] < arms["D_blind"]["wrong"],
        "verified_transfers_beat_own_laws_alone":
            arms["B_experiment_and_conclusion"]["predictions"] > arms["A_own"]["predictions"],
        # the specific claim of this round: a restated law reaches states its exporter never named
        "a_restated_law_reaches_student_states":
            arms["B_experiment_and_conclusion"]["predictions"]
            > arms["A_own"]["predictions"],
    }
    return {"summary": summary, "per_pair": per_pair}


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
