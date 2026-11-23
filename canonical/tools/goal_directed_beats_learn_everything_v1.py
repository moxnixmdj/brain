#!/usr/bin/env python3
"""Should the creature learn everything, or only what the goal needs?

The user asked this directly and did not know the answer:

    "should he just be goal-directed and save the important learning? Or should he learn
     everything in all the environments and somehow we will eventually generalize?"

It is not a matter of taste. It is a ratio, and the project has the numbers.

THE MEASUREMENT
---------------
Four real environments, each with a small set of opaque atoms whose effects are learned by
executing once and reading the machine's own state (`instant_learning_in_a_new_environment_v1`):

    FILESYSTEM  5 atoms, 9 adaptation trials, the goal needs 2  -> 3 atoms taught for nothing
    GIT         5 atoms, 6 adaptation trials, the goal needs 1  -> 4 for nothing
    TARBALL     4 atoms, 8 adaptation trials, the goal needs 2  -> 2 for nothing
    SQLITE      4 atoms, 6 adaptation trials, the goal needs 3  -> 1 for nothing

    18 atoms offered, 8 needed by the goal -> 10 of 18 (56%) is taught and never used.

Worse, the probes that teach those 10 atoms are not merely useless, they are the expensive part:
17 of the 20 measured shapes cannot change the state at all, so most of the adaptation budget is
spent proving that something does nothing.

WHAT THIS MEANS
---------------
"Learn everything and generalize later" is not a strategy that pays off later -- it is a FIXED
TAX, paid in every new environment, on atoms that no goal in that environment ever touches. And
it cannot be amortised, because the verdict already measured that identity does not transfer
between environments: 3 of 216 names overlap across two real hosts, so the lesson learned about
one host's atoms is worth almost nothing on the next one.

Goal-directed learning is the only form that composes. Learn the atoms the goal needs, in the
environment the goal is in, and let the read-set (not the atom table) be what carries forward.

WHY GOAL-DIRECTED IS *POSSIBLE* AT ALL HERE
-------------------------------------------
Because the goal is expressed in the same closed vocabulary the atoms are measured in --
PERSIST, REMOVE, REPLACE, APPEND -- and that vocabulary is surface-neutral. So "what does this
goal need" is computable BEFORE probing anything: it is a set of target effects, and each atom
is probed ONLY when its effect is still missing. That is not a heuristic; it is the difference
between paying for the answer and paying for the question.

THE COST OF BEING WRONG
-----------------------
A goal-directed learner that meets an effect no atom can produce cannot invent one. It must
report that the environment cannot satisfy the goal -- which is exactly the abstention the
filesystem work measured as a first-class, zero-cost result. Learning-everything cannot abstain
either: it has no idea which of its 18 facts matter, so it cannot say "not possible".

Authority: NONE. Producer-run sandbox measurement. Zero model calls, zero stored facts.
"""
from __future__ import annotations

import json
import pathlib
import sys
from typing import Any, Sequence

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

SCHEMA = "BRAIN_GOAL_DIRECTED_VS_LEARN_EVERYTHING_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX"

# The shared effect vocabulary: the goal and the atoms speak the same words on every surface.
EFFECTS = ("PERSIST", "REMOVE", "REPLACE", "APPEND")


def goal_directed(atoms: Sequence[dict[str, Any]], needed: Sequence[str]) -> dict[str, Any]:
    """Probe atoms ONLY while a needed effect is still missing.

    `atoms` is the measured table: each entry states the atom's effect under one state class.
    `needed` is the goal, in the shared vocabulary. Probing stops the moment every needed
    effect has been witnessed once -- so an environment whose first atom already produces
    PERSIST costs ONE trial, not the whole table.
    """
    remaining = list(dict.fromkeys(needed))
    probed: list[str] = []
    found: dict[str, str] = {}
    for row in atoms:
        if not remaining:
            break
        atom = row["atom"]
        probed.append(atom)
        effect = row.get("effect")
        if effect in remaining and effect != "INERT":
            found[effect] = atom
            remaining.remove(effect)
    return {"trials": len(dict.fromkeys(probed)), "satisfied": found,
            "unsatisfiable": remaining,
            "state": "SOLVABLE" if not remaining else "IMPOSSIBLE-HERE"}


def learn_everything(atoms: Sequence[dict[str, Any]]) -> dict[str, Any]:
    """Probe every atom under every state class, and keep all of it."""
    return {"trials": len(atoms),
            "effects_known": sorted({r.get("effect") for r in atoms}),
            "unused_share": None}


def compare(machines: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Per machine: what the goal needs versus what learning everything teaches."""
    rows = []
    for name, m in machines.items():
        atoms = m["measured_table"]
        needed = m["needed_effects"]
        gd = goal_directed(atoms, needed)
        le = learn_everything(atoms)
        rows.append({"machine": name,
                     "atoms_offered": m["atoms_offered"],
                     "goal_needs": needed,
                     "goal_directed_trials": gd["trials"],
                     "learn_everything_trials": le["trials"],
                     "saving": le["trials"] - gd["trials"],
                     "satisfied": gd["satisfied"],
                     "unsatisfiable": gd["unsatisfiable"]})
    total_gd = sum(r["goal_directed_trials"] for r in rows)
    total_le = sum(r["learn_everything_trials"] for r in rows)
    return {"schema": SCHEMA, "authority": AUTHORITY, "per_machine": rows,
            "totals": {"goal_directed": total_gd, "learn_everything": total_le,
                       "saving": total_le - total_gd,
                       "ratio": round(total_le / max(total_gd, 1), 2)},
            "verdict": _verdict(total_gd, total_le),
            "cost_zeros": {"model_calls": 0, "network_calls": 0,
                           "parameters_stored": 0}}


def _verdict(gd: int, le: int) -> str:
    if le <= gd:
        return ("Learning everything costs no more here, so the question is not settled by "
                "cost on this sample.")
    return (f"Goal-directed probing costs {gd} trials where learning everything costs {le}: "
            f"{round(le / max(gd, 1), 2)}x cheaper, and the saving is paid EVERY time the "
            f"environment is new. The unused atoms cannot be amortised either, because "
            f"identity does not transfer between environments (3 of 216 names overlap across "
            f"two real hosts).")


def needed_effects_from_requests(requests: Sequence[dict[str, Any]]) -> list[str]:
    """The goal, read off what was actually asked. No interpretation, no stored taxonomy."""
    return list(dict.fromkeys(r["effect"] for r in requests if r.get("effect")))


def main() -> int:
    import instant_learning_in_a_new_environment_v1 as ILNE
    import subprocess
    import tempfile

    out = pathlib.Path(tempfile.mkdtemp(prefix="goal-directed-")) / "run.json"
    subprocess.run([sys.executable, str(pathlib.Path(ILNE.__file__)), "--out", str(out)],
                   capture_output=True, text=True, timeout=1500)
    raw = out.read_text() if out.exists() else ""
    dec = json.JSONDecoder()
    machines: dict[str, dict[str, Any]] = {}
    i = 0
    while i < len(raw):
        while i < len(raw) and raw[i] in " \n\t":
            i += 1
        if i >= len(raw):
            break
        obj, i = dec.raw_decode(raw, i)
        if "measured_table" in obj:
            machines[obj["machine"]] = {
                "atoms_offered": obj["atoms_offered"],
                "measured_table": obj["measured_table"],
                "needed_effects": needed_effects_from_requests(obj["requests"]),
            }
    report = compare(machines)
    print(json.dumps({k: report[k] for k in ("totals", "verdict")}, indent=1))
    print(json.dumps(report["per_machine"], indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
