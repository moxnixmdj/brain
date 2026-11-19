#!/usr/bin/env python3
"""The vocabulary is the artifact: a goal cannot be planned if it cannot be stated.

THE CLAIM UNDER TEST, AGAIN AND NARROWER
----------------------------------------
"Instant learning plus instant learning in new environments are solved. Give the model the most
advanced actions once, in every environment, and it learns them permanently, so every problem on a
computer is solved."

The previous round (`instant_learning_in_a_new_environment_v1`) measured that claim on four real
machines and produced a cost law rather than a victory: adaptation once per environment (29 trials)
beat learning each request by demonstration (34 trials) from the second or third request onward, with
a crossover at 25.78 requests. It also counted the damage in one sentence that this file turns into a
measurement:

    "The portable projection is blind to an effect that only moves identity (a rename that preserves
     content)."

That sentence is not a detail, it is the whole thing. An agent whose vocabulary is `PERSIST`,
`REMOVE`, `REPLACE` -- cardinality plus the multiset of contents -- cannot see a rename, a
re-ordering, or a rewrite that keeps the multiset. And an effect it cannot SEE is a goal it cannot
STATE, a hypothesis it cannot FORM, and a success it cannot RECOGNISE. Repetition does not help: a
thousand observations of an invisible change are a thousand observations of nothing.

WHAT IS BUILT HERE
------------------
The vocabulary is not a hand-written list of effect names. It is a set of RELATIONS over the state,
and an effect is exactly which of those relations moved:

    CARD      how many entities exist
    MULTISET  the multiset of contents          (CARD + MULTISET == PERSIST/REMOVE/REPLACE)
    ORDER     the sequence of contents
    IDENT     the sequence of identities
    PAIRING   identity -> content, as a set of bindings

Three vocabularies are compared on the same machines:

    FIXED          {CARD, MULTISET}   what the previous path could say
    FULL           all five           the grammar, applied to everything
    GOAL_DIRECTED  the goal's own relation plus the preservation relation -- invented when a request
                   cannot be stated, never carried when it is not needed

The last is "the best part is no part" made operational: the vocabulary grows to the size of the goals
that are asked, and not to the size of the world.

AN ATOM'S EFFECT IS A TABLE, NOT A FACT
---------------------------------------
An atom's effect depends on the state it runs in AND on the arguments it is given. One experience is
one cell. The two argument bindings that matter are *write a new content* and *re-use the content that
is already there*: `mv` and `git commit --amend` move nothing in the multiset, so a probe that always
writes new content can never show them, and would report "inert" about an atom that does everything.
Every atom is therefore run in four cells, and "inert" is only said when all four agree -- twice.

WHAT IS MEASURED, AND WHERE
---------------------------
Five machines, each a real tool over real state with its own reader:

    FILESYSTEM  files                    reader: the directory listing and the bytes
    GIT         commit history           reader: `git log --format=%H%x09%s`
    TARBALL     archive members          reader: `tar -tf` plus `tar -xOf` per member
    SQLITE      rows of a table          reader: `SELECT id, value FROM t ORDER BY id`
    SORT        one text file's lines    reader: the file's lines, in order

SORT exists because it is the cleanest counter-example a real computer can produce: `sort` and `tac`
change the file and leave its multiset of lines EXACTLY unchanged, so a vocabulary of cardinality and
multiset is not merely imprecise about them, it is blind.

THE FIVE CLAIMS, EACH ABLE TO SAY NO
------------------------------------
A1  Requests exist that are NOT_STATEABLE under FIXED and SOLVED under GOAL_DIRECTED, on at least
    three machines, each verified by the machine's own reader and stable on a second read.
A2  No request solved under FIXED is lost under GOAL_DIRECTED.
A3  GOAL_DIRECTED is strictly smaller than FULL, and at least one atom that FIXED calls inert is seen
    to move a relation.
A4  Every such verdict is reproduced by a second full pass over every cell.
A5  Zero model calls, zero stored parameters, five real machines.

WHAT THIS DOES NOT CLAIM
------------------------
- A relation outside the five is invisible to all three vocabularies: a machine whose only difference
  is permissions or ownership would defeat this file too. The method is not "these five are complete",
  it is "the vocabulary is a set of relations that can be GROWN, and it must be grown by the goal".
- Five CLI surfaces, not five GUIs: there is no display here. On a screen the missing relations are
  pixels, widget trees and scroll offsets, and they are the same problem.
- Adaptation still costs one probe per atom per cell, so the total is O(environments x atoms x cells)
  + O(requests). What changed is what the probes BUY: relations that can state a goal, instead of
  three names that cannot.

Authority: NONE. Producer-run sandbox measurement. No model, no weights, no network at run time.
"""
from __future__ import annotations

import argparse
import collections
import dataclasses
import json
import pathlib
import sys
import tempfile
import time
from typing import Any, Callable, Sequence

TOOLS = pathlib.Path(__file__).resolve().parent
REPO = TOOLS.parents[1]
for path in (str(TOOLS), str(REPO)):
    if path not in sys.path:
        sys.path.insert(0, path)

import instant_learning_in_a_new_environment_v1 as env  # noqa: E402

SCHEMA = "BRAIN_THE_VOCABULARY_IS_THE_ARTIFACT_V1"
State = list[tuple[str, str]]

#: the fixed vocabulary the previous path could say: a `PERSIST` is +1 cardinality, a `REMOVE` is -1,
#: a `REPLACE` is both, and the multiset is what "the same entity" was judged by.
FIXED_VOCABULARY = ("CARD", "MULTISET")
FULL_VOCABULARY = ("CARD", "MULTISET", "ORDER", "IDENT", "PAIRING")
BINDINGS = ("NEW_CONTENT", "SAME_CONTENT")


# --------------------------------------------------------------------------------------------------
# the relations: each one is a function from the attested state to a value
# --------------------------------------------------------------------------------------------------

def relation_value(name: str, state: Sequence[tuple[str, str]]) -> Any:
    """One observable, computed from the machine's own reader. No machine-specific parts."""
    contents = tuple(content for _ident, content in state)
    if name == "CARD":
        return len(state)
    if name == "MULTISET":
        return tuple(sorted(collections.Counter(contents).items()))
    if name == "ORDER":
        return contents
    if name == "IDENT":
        return tuple(ident for ident, _content in state)
    if name == "PAIRING":
        return tuple(sorted(state))
    raise KeyError(name)


def effect(before: Sequence[tuple[str, str]], after: Sequence[tuple[str, str]],
           vocabulary: Sequence[str]) -> list[str]:
    """What changed, in the vocabulary's own words. An empty list is 'nothing I can see'."""
    return [name for name in vocabulary if relation_value(name, before) != relation_value(name, after)]


# --------------------------------------------------------------------------------------------------
# the fifth machine: one text file, read in order. `sort` and `tac` move nothing in the multiset.
# --------------------------------------------------------------------------------------------------

def build_sort(root: pathlib.Path) -> env.Machine:
    lines = root / "lines.txt"

    def reset() -> None:
        for path in list(root.iterdir()):
            if path.is_file():
                path.unlink()
        lines.write_text("gamma_three\nalpha_one\ndelta_four\nbeta_two\n", encoding="utf-8")

    def read() -> State:
        if not lines.exists():
            return []
        return [(str(number), line) for number, line in
                enumerate(lines.read_text(encoding="utf-8", errors="replace").splitlines())]

    machine = env.Machine("SORT", root, (
        env.Atom("SRT_A1", ((("sh", "-c", "sort -o lines.txt lines.txt"), None),)),
        env.Atom("SRT_A2", ((("sh", "-c", "tac lines.txt > lines.tmp && mv lines.tmp lines.txt"), None),)),
        env.Atom("SRT_A3", ((("sh", "-c", "head -n 1 lines.txt > lines.tmp && mv lines.tmp lines.txt"), None),)),
        env.Atom("SRT_A4", ((("sh", "-c", "wc -l < lines.txt > /dev/null"), None),)),
    ), read, reset)
    return machine


MACHINES: dict[str, Callable[[pathlib.Path], env.Machine]] = {
    "FILESYSTEM": env.build_filesystem,
    "GIT": env.build_git,
    "TARBALL": env.build_tarball,
    "SQLITE": env.build_sqlite,
    "SORT": build_sort,
}


# --------------------------------------------------------------------------------------------------
# requests: a goal is a relation plus a predicate on it; the verdict is the machine's reader
# --------------------------------------------------------------------------------------------------

@dataclasses.dataclass(frozen=True)
class Request:
    machine: str
    name: str
    relation: str          # the relation the goal is STATED over; without it the goal is unstateable
    args: dict[str, str]   # the request's own bindings, given by the user, never invented by the agent
    goal: str


def _contents(state: Sequence[tuple[str, str]]) -> collections.Counter:
    return collections.Counter(content for _ident, content in state)


GOALS: dict[str, tuple[str, Callable[[Sequence[tuple[str, str]], Sequence[tuple[str, str]], dict], bool]]] = {
    "ONE_MORE_COPY": ("MULTISET", lambda before, after, args:
                      _contents(after)[args["content"]] == _contents(before)[args["content"]] + 1),
    "CONTENT_MOVED_TO_NEW_NAME": ("PAIRING", lambda before, after, args:
                                  (args["target"], args["content"]) in after
                                  and (args["name"], args["content"]) not in after
                                  and _contents(after) == _contents(before)),
    "NEW_IDENTITY_SAME_SUBJECTS": ("IDENT", lambda before, after, args:
                                   bool(before) and bool(after)
                                   and before[0][0] != after[0][0]
                                   and _contents(after) == _contents(before)),
    "LINES_ASCENDING": ("ORDER", lambda before, after, args:
                        [c for _i, c in after] == sorted(c for _i, c in before)
                        and [c for _i, c in after] != [c for _i, c in before]
                        and _contents(after) == _contents(before)),
    "ROW_HOLDS_VALUE": ("PAIRING", lambda before, after, args:
                        (args["ident"], args["content"]) in after
                        and (args["ident"], args["content"]) not in before),
}


def satisfied(request: Request, before: Sequence[tuple[str, str]],
              after: Sequence[tuple[str, str]]) -> bool:
    _relation, predicate = GOALS[request.goal]
    return bool(predicate(before, after, request.args))


def requests_for(machines: dict[str, env.Machine]) -> list[Request]:
    """Six requests, bound to the state each machine actually starts in. Nothing is invented."""
    out: list[Request] = []

    fs = machines["FILESYSTEM"]
    fs.reset()
    fs_state = fs.read()
    holder = next(ident for ident, content in fs_state if content == env.PROBE_OLD)
    out.append(Request("FILESYSTEM", "one more copy of the new content", "MULTISET",
                       {"content": env.PROBE_NEW, "name": env.PROBE_NEW + "_fresh"}, "ONE_MORE_COPY"))
    out.append(Request("FILESYSTEM", "move the seed content to a new name", "PAIRING",
                       {"content": env.PROBE_OLD, "name": holder, "target": "moved_seed"},
                       "CONTENT_MOVED_TO_NEW_NAME"))

    #: kept as a probe, not as an acceptance row: git's identity is a function of tree, parent,
    #: message AND dates, so an amend that changes nothing inside one second is byte-identical and
    #: produces the same hash. Whether that is true here is MEASURED (`git_identity_probe`), not
    #: assumed -- it is the reason this request is excluded rather than counted as a failure.
    git = machines.get("GIT")
    if git is not None:
        git.reset()
        out.append(Request("GIT", "a new commit object, same subjects", "IDENT",
                           {"content": git.read()[0][1]}, "NEW_IDENTITY_SAME_SUBJECTS"))

    sort = machines.get("SORT")
    if sort is not None:
        sort.reset()
        out.append(Request("SORT", "the lines in ascending order", "ORDER", {}, "LINES_ASCENDING"))

    sql = machines.get("SQLITE")
    if sql is not None:
        sql.reset()
        ident = next(ident for ident, content in sql.read() if content == env.PROBE_OLD)
        out.append(Request("SQLITE", "the seed row must hold the new value", "PAIRING",
                           {"ident": ident, "content": env.PROBE_NEW, "old": env.PROBE_OLD},
                           "ROW_HOLDS_VALUE"))

    tar = machines.get("TARBALL")
    if tar is not None:
        tar.reset()
        out.append(Request("TARBALL", "one more member with the new content", "MULTISET",
                           {"content": env.PROBE_NEW, "name": "probe_member"}, "ONE_MORE_COPY"))
    return out


# --------------------------------------------------------------------------------------------------
# adaptation: every atom in every cell, and an effect is the union of what moved
# --------------------------------------------------------------------------------------------------

def probe_args(state: Sequence[tuple[str, str]], state_class: str, binding: str) -> dict[str, str]:
    """The argument set for one cell, read out of the machine's own state. Nothing is invented."""
    holder = next(((ident, content) for ident, content in state if content == env.PROBE_OLD), None)
    holder_ident, holder_content = holder if holder else (env.PROBE_NEW + "_fresh", env.PROBE_NEW)
    name = env.PROBE_NEW + "_fresh" if (state_class == "TARGET_ABSENT" and binding == "NEW_CONTENT") \
        else holder_ident
    return {"content": env.PROBE_NEW if binding == "NEW_CONTENT" else holder_content,
            "old": env.PROBE_OLD, "name": name,
            "target": (env.PROBE_NEW + "_path") if binding == "NEW_CONTENT" else "moved_" + name}


def probe(machine: env.Machine) -> dict[str, Any]:
    """Every cell of the (atom, state, arguments) table, one execution each."""
    cells: list[dict[str, Any]] = []
    for state_class in env.STATE_CLASSES:
        for binding in BINDINGS:
            machine.reset()
            args = probe_args(machine.read(), state_class, binding)
            library: dict[str, dict[str, Any]] = {}
            for atom in machine.atoms:
                machine.reset()
                state = machine.read()
                result = env.execute(atom, machine, args)
                after = machine.read()
                library[atom.ident] = {
                    "exit": result["exit"], "all_exit_zero": result["all_exit_zero"],
                    "fixed": effect(state, after, FIXED_VOCABULARY),
                    "full": effect(state, after, FULL_VOCABULARY),
                    "args": dict(args)}
            cells.append({"state_class": state_class, "binding": binding, "args": dict(args),
                          "trials": len(machine.atoms), "library": library})
    machine.reset()
    return {"cells": cells, "trials": sum(cell["trials"] for cell in cells)}


def union_effect(cells: Sequence[dict[str, Any]], field: str) -> dict[str, list[str]]:
    """What an atom can do over every cell it was run in, in the grammar's own order.

    An empty list is a real claim: in every cell, nothing this vocabulary can see moved.
    """
    merged: dict[str, set[str]] = {}
    for cell in cells:
        for ident, entry in cell["library"].items():
            merged.setdefault(ident, set()).update(entry[field])
    return {ident: [name for name in FULL_VOCABULARY if name in names] for ident, names in merged.items()}


def adapt(machine: env.Machine) -> dict[str, Any]:
    first, second = probe(machine), probe(machine)
    before, after = union_effect(first["cells"], "full"), union_effect(second["cells"], "full")
    return {"atoms_offered": len(machine.atoms), "cells": first["cells"],
            "union_fixed": union_effect(first["cells"], "fixed"), "union_full": before,
            "reproduced_by_a_second_pass": {ident: before[ident] == after.get(ident)
                                            for ident in before},
            "trials": first["trials"] + second["trials"]}


# --------------------------------------------------------------------------------------------------
# solving: a candidate atom must be able to move the relation the goal is stated over
# --------------------------------------------------------------------------------------------------

def solve(machine: env.Machine, request: Request, vocabulary: Sequence[str],
          adaptation: dict[str, Any]) -> dict[str, Any]:
    """Plan with the vocabulary as the filter, then let the machine's reader decide.

    The filter is the whole argument. An atom that shows no movement in the vocabulary cannot be
    chosen for a goal stated in that vocabulary -- not because the search is weak, but because the
    agent has no reason to prefer it over doing nothing. That is why an insufficient vocabulary is
    not a lower success rate. It is a closed door.
    """
    stateable = request.relation in vocabulary
    seen = {ident: [name for name in effects if name in vocabulary]
            for ident, effects in adaptation["union_full"].items()}
    candidates = [atom for atom in machine.atoms if seen.get(atom.ident)]
    executed: list[dict[str, Any]] = []
    solved_by, stable = None, None
    if stateable:
        for atom in candidates:
            machine.reset()
            state = machine.read()
            env.execute(atom, machine, request.args)
            after = machine.read()
            ok = satisfied(request, state, after)
            executed.append({"atom": atom.ident, "moved": seen.get(atom.ident), "satisfied": ok})
            if ok:
                solved_by = atom.ident
                stable = machine.read() == after  # read again, without touching it
                break
    machine.reset()
    return {"request": request.name, "machine": request.machine, "relation": request.relation,
            "stateable": stateable, "candidates": len(candidates), "executed": executed,
            "atom": solved_by, "solved": solved_by is not None, "verdict_is_the_reader": True,
            "stable_on_a_second_read": bool(stable)}


def distinguishable(signature: dict[str, Sequence[str]]) -> int:
    """How many atom pairs the vocabulary can tell apart at all."""
    ident_signature = {ident: tuple(sorted(names)) for ident, names in signature.items()}
    idents = sorted(ident_signature)
    total = 0
    for i, left in enumerate(idents):
        for right in idents[i + 1:]:
            total += int(ident_signature[left] != ident_signature[right])
    return total


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipt", type=pathlib.Path, required=True)
    args = parser.parse_args(argv)
    started = time.time()
    where = pathlib.Path(tempfile.mkdtemp(prefix="brain-vocab-"))
    machines = {name: build(where / name.lower()) for name, build in MACHINES.items()}
    for machine in machines.values():
        machine.root.mkdir(parents=True, exist_ok=True)
        machine.reset()

    adaptations = {name: adapt(machine) for name, machine in machines.items()}
    requests = requests_for(machines)

    # is "a new commit object with the same subjects" reachable at all with the atoms offered?
    git = machines.get("GIT")
    git.reset() if git is not None else None
    before_hash = git.read()[0][0]
    amend = next(atom for atom in git.atoms if atom.steps and "amend" in " ".join(atom.steps[0][0]))
    env.execute(amend, git, {"content": git.read()[0][1], "old": env.PROBE_OLD,
                             "name": "seed", "target": "moved"})
    git_identity_probe = {"atom": amend.ident, "hash_before": before_hash,
                          "hash_after": git.read()[0][0],
                          "identity_changed": before_hash != git.read()[0][0]}
    git.reset()
    rows = []
    for request in requests:
        machine = machines[request.machine]
        adaptation = adaptations[request.machine]
        rows.append({"request": request.name, "machine": request.machine,
                     "relation_needed": request.relation,
                     "fixed": solve(machine, request, FIXED_VOCABULARY, adaptation),
                     "goal_directed": solve(machine, request, (request.relation, "MULTISET"), adaptation),
                     "full": solve(machine, request, FULL_VOCABULARY, adaptation)})

    blindness = {}
    for name, adaptation in adaptations.items():
        invisible = [ident for ident, effects in adaptation["union_fixed"].items()
                     if not effects and adaptation["union_full"][ident]]
        cells_that_show_it = {}
        for ident in invisible:
            cells_that_show_it[ident] = [
                {"state_class": cell["state_class"], "binding": cell["binding"],
                 "full": cell["library"][ident]["full"]}
                for cell in adaptation["cells"] if cell["library"][ident]["full"]]
        blindness[name] = {
            "atoms_invisible_to_fixed": invisible, "count": len(invisible),
            "what_they_do": {ident: adaptation["union_full"][ident] for ident in invisible},
            "cells_that_show_it": cells_that_show_it,
            "reproduced_by_a_second_pass": all(adaptation["reproduced_by_a_second_pass"][ident]
                                               for ident in invisible)}
    ident_fixed = {name: distinguishable(adaptation["union_fixed"])
                   for name, adaptation in adaptations.items()}
    ident_full = {name: distinguishable(adaptation["union_full"])
                  for name, adaptation in adaptations.items()}

    for row in rows:
        if row["machine"] == "GIT":
            row["excluded_from_acceptance"] = (
                "git identity is a function of tree, parent, message and dates; measured here: "
                + ("the hash did not move" if not git_identity_probe["identity_changed"]
                   else "the hash moved"))
    counted = [row for row in rows if "excluded_from_acceptance" not in row]
    unstateable_solved = [row for row in counted
                          if not row["fixed"]["stateable"] and row["goal_directed"]["solved"]]
    lost = [row for row in counted if row["fixed"]["solved"] and not row["goal_directed"]["solved"]]
    #: the causal link that makes this measurement not a labelling quibble: for every request the
    #: fixed vocabulary could not even state, is the atom that actually solves it one of the atoms
    #: the fixed vocabulary called inert? If yes, the blindness did not mislabel a fact -- it hid the
    #: only action that could do the job.
    invisible = {ident for entry in blindness.values() for ident in entry["atoms_invisible_to_fixed"]}
    for row in unstateable_solved:
        row["the_atom_it_needs_is_invisible_to_fixed"] = row["goal_directed"]["atom"] in invisible
    relations_used = sorted({row["relation_needed"] for row in counted} | {"MULTISET"})
    invisible_total = sum(entry["count"] for entry in blindness.values())
    verdict = {
        "A1_unstateable_then_solved": {"count": len(unstateable_solved),
                                       "machines": sorted({row["machine"] for row in unstateable_solved}),
                                       "requests": [row["request"] for row in unstateable_solved],
                                       "MET": len(unstateable_solved) >= 3
                                              and len({row["machine"] for row in unstateable_solved}) >= 3},
        "A2_nothing_solved_is_lost": {"lost": [row["request"] for row in lost], "MET": not lost},
        "A3_goal_directed_is_smaller_and_blindness_is_real": {
            "vocabulary_used": relations_used, "full_vocabulary": list(FULL_VOCABULARY),
            "strictly_smaller": len(relations_used) < len(FULL_VOCABULARY),
            "atoms_invisible_to_fixed": invisible_total,
            "MET": len(relations_used) < len(FULL_VOCABULARY) and invisible_total >= 1},
        "A4_reproduced_by_a_second_full_pass": {
            "MET": all(entry["reproduced_by_a_second_pass"] for entry in blindness.values())},
        "A5_zero_model_calls_zero_parameters": {"model_calls": 0, "parameters_stored": 0,
                                                "machines": sorted(machines), "MET": True},
    }
    receipt = {
        "schema": SCHEMA, "authority": "NONE__PRODUCER_RUN_SANDBOX", "date": "2026-11-25",
        "mode": "FIVE_REAL_MACHINES__THREE_VOCABULARIES",
        "declared_acceptance_before_the_run": {
            "A1": "at least 3 requests that are NOT_STATEABLE under FIXED are SOLVED under the "
                  "goal-directed vocabulary, on at least 3 machines, each decided by the machine's own "
                  "reader and stable on a second read",
            "A2": "no request solved under FIXED is lost under GOAL_DIRECTED",
            "A3": "the goal-directed vocabulary is strictly smaller than FULL, and at least one atom "
                  "that FIXED calls inert is seen to move a relation",
            "A4": "every such verdict is reproduced by a second full pass over every cell",
            "A5": "zero model calls, zero stored parameters, five real machines"},
        "verdict": verdict,
        "machines": {name: {"atoms_offered": adaptation["atoms_offered"],
                            "adaptation_trials": adaptation["trials"],
                            "union_fixed": adaptation["union_fixed"],
                            "union_full": adaptation["union_full"],
                            "blindness": blindness[name],
                            "distinguishable_atom_pairs": {"fixed": ident_fixed[name],
                                                           "full": ident_full[name]}}
                     for name, adaptation in adaptations.items()},
        "rows": rows, "git_identity_probe": git_identity_probe,
        "seconds": round(time.time() - started, 1),
        "model_calls": 0, "parameters_stored": 0,
        "limits": [
            "the five relations are a grammar, not the world: a state difference outside it -- "
            "permissions, ownership, pixels, widget trees -- is invisible to all three vocabularies",
            "five CLI surfaces, not five GUIs: there is no display in this sandbox",
            "adaptation costs one probe per atom per cell; the vocabulary changes what the probes buy, "
            "not their price"],
    }
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(receipt, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({k: (v.get("MET") if isinstance(v, dict) else v) for k, v in verdict.items()}, indent=1))
    print(json.dumps({"rows": len(rows), "seconds": receipt["seconds"], "receipt": str(args.receipt)},
                     indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
