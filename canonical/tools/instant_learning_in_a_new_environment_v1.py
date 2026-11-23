#!/usr/bin/env python3
"""What "instant learning in a new environment" actually costs, measured on four real machines.

THE CLAIM UNDER TEST
--------------------
"Give the model the most advanced actions, let it experience each once, and it learns them
permanently. Give it any new environment and it learns that too. So it solves everything on a
computer." Three propositions hide in that paragraph and they do not share a truth value:

  P1  one verified experience in a FIXED environment is enough for permanent correct reuse;
  P2  one experience per NEW ENVIRONMENT is enough for competence in that environment;
  P3  therefore every problem on a computer follows.

P1 was measured earlier in this tree (`THE_INVARIANCE_IS_THE_REACH_20261116_V1.md`): one verified
repair becomes a rule that reaches other code **only after the representation is told what does not
matter** -- 0 of 304 candidates survived the target's own examples without that, 4 of 384 with it.
This file measures P2, the one his question turns on, and it measures a COST LAW rather than a
success rate, because a success rate on one environment cannot say anything about "any environment".

WHAT IS MEASURED, AND WHERE
---------------------------
Four machines, each a REAL tool over REAL state, each with its own reader:

  FILESYSTEM  files;             reader: the directory listing and the bytes
  GIT         commit history;    reader: `git log --format=%H%x09%s`
  TARBALL     archive members;   reader: `tar -tf` plus `tar -xOf` per member
  SQLITE      rows of a table;   reader: `SELECT id, value FROM t ORDER BY id`

The engine gets, per machine: the atom list (commands as argv, with placeholders), the machine's
reader, and nothing else. Atom identifiers are opaque (`FS_A1`, `GIT_A3`, ...) and carry no meaning --
if the name said "create", the name would be the knowledge. What an atom DOES is learned by executing
it once and reading the machine's own state before and after.

An effect is therefore a measured object: the change in the machine's attested state, described so
that the surface's private names are not part of it:

  PERSIST  one entity arrived
  REMOVE   one entity left
  REPLACE  one left and one arrived

Those three are also what the user may ask for, in the same words, on every machine. That shared
vocabulary is the invariant. Nothing else is shared: commands, arguments, identity schemes (path,
commit hash, member name, rowid) and state formats differ completely across the four.

TWO COSTS, AND THE BASELINE THEY ARE COMPARED AGAINST
-----------------------------------------------------
  ADAPTATION  trials spent learning what the machine's atoms do, once, before any request
  PER REQUEST what the engine spends on each subsequent request

The baseline is the current paradigm: **learn each request by demonstration** -- try atoms in a fixed
order, with that request's own arguments, until the reader agrees. That agent pays per request for
ever and remembers nothing the next request could use.

Reported per machine: atoms offered, atoms that cannot change the state, atoms whose effect ignores
the argument it was given, trials to adapt (probing every atom, and the active form that stops once
each required effect has been witnessed once), trials for the same four requests under both regimes,
and the crossover where adapting once beats learning each request. The crossover is the honest
answer to "is this revolutionary": it is, from the second or third request in an environment onward,
and it is strictly WORSE for the first request, always, because measurement is a fixed tax and a
demonstration is not.

WHAT THIS DOES NOT CLAIM
------------------------
- Four CLI/database surfaces, not four GUI applications: there is no display in this sandbox. The law
  is the same law; its constant is much larger on a screen -- OSExpert (arXiv 2603.07978, Mar 2026)
  measured computer-use agents at 0-10% on unseen UIs and needed explicit exploration of an
  environment's unit functions before any transfer appeared.
- Adaptation is a tax per machine and a general computer has unboundedly many machines, so the total
  is O(machines x adaptation) + O(requests). That is a change of currency from requests to
  environments, not "everything is solved".
- The portable projection is blind to an effect that only moves identity (a rename that preserves
  content). Those atoms are counted and named: the blindness is the price of portability.
- Every verdict is the machine's own reader, before and after. A command that prints "ok" and changes
  nothing is REFUSED; that is tested.

Authority: NONE. Producer-run sandbox measurement. No model, no weights, no network at run time.
"""
from __future__ import annotations

import argparse
import collections
import dataclasses
import json
import pathlib
import subprocess
import sys
import tempfile
import time
from typing import Any, Callable, Sequence

REPO = pathlib.Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from canonical.runtime import attested_state_v1 as attested  # noqa: E402

SCHEMA = "BRAIN_INSTANT_LEARNING_IN_A_NEW_ENVIRONMENT_V1"
PERSIST, REMOVE, REPLACE, APPEND, INERT, UNCLASSIFIED = (
    "PERSIST", "REMOVE", "REPLACE", "APPEND", "INERT", "UNCLASSIFIED")
EFFECT_VOCABULARY = (PERSIST, REMOVE, REPLACE)
TOP = 40
PROBE_NEW = "probe_new_content"
#: an action's effect can depend on the state it is run in, so one experience per action is one cell
#: of a table, not the table. These are the two state classes this experiment can distinguish.
STATE_CLASSES = ("TARGET_ABSENT", "TARGET_EXISTS")
PROBE_OLD = "probe_seed_content"
TASK_TOKENS = ("alpha_one", "beta_two", "gamma_three", "delta_four")


@dataclasses.dataclass(frozen=True)
class Atom:
    """One offered command. The ident is opaque on purpose; the steps are what gets executed."""
    ident: str
    steps: tuple[tuple[tuple[str, ...], str | None], ...]


@dataclasses.dataclass
class Machine:
    name: str
    root: pathlib.Path
    atoms: tuple[Atom, ...]
    read: Callable[[], list[tuple[str, str]]]
    reset: Callable[[], None]


# --------------------------------------------------------------------------------------------------
# the four machines: real tools, real state, their own readers
# --------------------------------------------------------------------------------------------------

def _run(argv: Sequence[str], *, cwd: pathlib.Path, stdin: str | None = None) -> dict[str, Any]:
    try:
        done = subprocess.run(list(argv), cwd=str(cwd), input=(stdin or ""),
                              capture_output=True, text=True, timeout=TOP)
    except (subprocess.TimeoutExpired, FileNotFoundError) as error:
        return {"exit": 124, "stdout": "", "stderr": type(error).__name__}
    return {"exit": done.returncode, "stdout": done.stdout, "stderr": done.stderr}


def _write_via_sh(content: str, name: str) -> tuple[str, ...]:
    # sh -c 'printf %s "$0" > "$1"' CONTENT NAME  -- argv positional, no quoting games
    return ("sh", "-c", 'printf %s "$0" > "$1"', content, name)


def build_git(root: pathlib.Path) -> Machine:
    machine: Machine

    def git(*argv: str) -> dict[str, Any]:
        return _run(("git", *argv), cwd=root)

    def reset() -> None:
        if (root / ".git").is_dir():
            import shutil
            shutil.rmtree(root / ".git")
        git("init", "-q")
        git("config", "user.email", "brain@example.invalid")
        git("config", "user.name", "brain")
        git("commit", "-q", "--allow-empty", "-m", PROBE_OLD)
        git("commit", "-q", "--allow-empty", "-m", "probe_second_content")

    def read() -> list[tuple[str, str]]:
        rows = []
        for line in git("log", "--format=%H%x09%s")["stdout"].splitlines():
            if "\t" in line:
                sha, message = line.split("\t", 1)
                rows.append((sha, message))
        return rows

    machine = Machine("GIT", root, (
        Atom("GIT_A1", ((("git", "commit", "--allow-empty", "-m", "{content}"), None),)),
        Atom("GIT_A2", ((("git", "reset", "--hard", "HEAD~1"), None),)),
        Atom("GIT_A3", ((("git", "commit", "--amend", "--allow-empty", "-m", "{content}"), None),)),
        Atom("GIT_A4", ((("git", "status", "--short"), None),)),
        Atom("GIT_A5", ((("git", "add", "-A"), None),)),
    ), read, reset)
    return machine


def build_tarball(root: pathlib.Path) -> Machine:
    archive = root / "pack.tar"

    def reset() -> None:
        for path in list(root.iterdir()):
            if path.is_file():
                path.unlink()
        (root / "seed").write_text(PROBE_OLD)
        (root / "seed2").write_text("probe_second_content")
        _run(("tar", "-cf", str(archive), "seed", "seed2"), cwd=root)
        (root / "seed").unlink()
        (root / "seed2").unlink()

    def read() -> list[tuple[str, str]]:
        rows = []
        for name in _run(("tar", "-tf", str(archive)), cwd=root)["stdout"].split():
            body = _run(("tar", "-xOf", str(archive), name), cwd=root)
            rows.append((name, body["stdout"].strip()))
        return rows

    machine = Machine("TARBALL", root, (
        Atom("TAR_A1", ((_write_via_sh("{content}", "{name}"), None),
                        (("tar", "-rf", str(archive), "{name}"), None),
                        (("rm", "-f", "{name}"), None))),
        Atom("TAR_A2", ((("tar", "--delete", "-f", str(archive), "{name}"), None),)),
        Atom("TAR_A3", ((("tar", "-tf", str(archive)), None),)),
        Atom("TAR_A4", ((("tar", "-xf", str(archive)), None),)),
    ), read, reset)
    return machine


def build_filesystem(root: pathlib.Path) -> Machine:
    def reset() -> None:
        for path in list(root.iterdir()):
            if path.is_file():
                path.unlink()
        (root / "seed").write_text(PROBE_OLD)
        (root / "seed2").write_text("probe_second_content")

    def read() -> list[tuple[str, str]]:
        return [(path.name, path.read_text(errors="replace").strip())
                for path in sorted(root.iterdir()) if path.is_file()]

    machine = Machine("FILESYSTEM", root, (
        Atom("FS_A1", ((_write_via_sh("{content}", "{name}"), None),)),
        Atom("FS_A2", ((("rm", "-f", "{name}"), None),)),
        Atom("FS_A3", ((("mv", "-f", "{name}", "{target}"), None),)),
        Atom("FS_A4", ((("cp", "-f", "{name}", "{target}"), None),)),
        Atom("FS_A5", ((("ls", "-1"), None),)),
    ), read, reset)
    return machine


def _sql_argv(database: pathlib.Path, statement: str, *, select: bool = False) -> tuple[str, ...]:
    if select:
        code = ("import sqlite3,sys;"
                "c=sqlite3.connect(sys.argv[1]);"
                "print('\\n'.join('\\t'.join(str(x) for x in r)"
                " for r in c.execute(sys.argv[2]).fetchall()));c.close()")
    else:
        code = ("import sqlite3,sys;"
                "c=sqlite3.connect(sys.argv[1]);c.execute(sys.argv[2]);c.commit();c.close()")
    return (sys.executable, "-c", code, str(database), statement)


def build_sqlite(root: pathlib.Path) -> Machine:
    database = root / "store.db"

    def exec_sql(statement: str) -> dict[str, Any]:
        return _run(_sql_argv(database, statement), cwd=root)

    def reset() -> None:
        if database.exists():
            database.unlink()
        exec_sql("CREATE TABLE t (id INTEGER PRIMARY KEY, value TEXT)")
        exec_sql(f"INSERT INTO t (value) VALUES ('{PROBE_OLD}')")
        exec_sql("INSERT INTO t (value) VALUES ('probe_second_content')")

    def read() -> list[tuple[str, str]]:
        rows = []
        for line in _run(_sql_argv(database, "SELECT id, value FROM t ORDER BY id", select=True),
                         cwd=root)["stdout"].splitlines():
            if "\t" in line:
                ident, value = line.split("\t", 1)
                rows.append((ident, value))
        return rows

    machine = Machine("SQLITE", root, (
        Atom("SQL_A1", ((_sql_argv(database, "INSERT INTO t (value) VALUES ('{content}')"), None),)),
        Atom("SQL_A2", ((_sql_argv(database, "DELETE FROM t WHERE value='{old}'"), None),)),
        Atom("SQL_A3", ((_sql_argv(database, "UPDATE t SET value='{content}' WHERE value='{old}'"), None),)),
        Atom("SQL_A4", ((_sql_argv(database, "SELECT count(*) FROM t"), None),)),
    ), read, reset)
    return machine


MACHINES: dict[str, Callable[[pathlib.Path], Machine]] = {
    "FILESYSTEM": build_filesystem,
    "GIT": build_git,
    "TARBALL": build_tarball,
    "SQLITE": build_sqlite,
}


# --------------------------------------------------------------------------------------------------
# what an atom does: measured, never declared
# --------------------------------------------------------------------------------------------------

def contents_of(state: Sequence[tuple[str, str]]) -> collections.Counter:
    return collections.Counter(content for _ident, content in state)


def classify(change: int, arrived: int, departed: int) -> str:
    """Five shapes, and the fifth was missing.

    `(1, 2, 1)` -- one more entity, one arrived, one departed -- was UNCLASSIFIED, and the one
    atom that produced it was `tar -rf` run against a name that already existed: a copy is made
    into the archive and the ORIGINAL stays, so the archive GAINS an entity while the target is
    not consumed. That is an append, and it is the shape every append-only store produces
    (an archive, a log, an event table, a commit history). Leaving it unclassified made a real,
    portable, repeatable effect look like a measurement failure -- the atom was then counted in
    `unclassified_atoms` and could not be asked for.
    """
    shape = (change, arrived, departed)
    return {(0, 0, 0): INERT,
            (1, 1, 0): PERSIST,
            (-1, 0, 1): REMOVE,
            (0, 1, 1): REPLACE,
            (1, 2, 1): APPEND}.get(shape, UNCLASSIFIED)


def effect_of(before: Sequence[tuple[str, str]], after: Sequence[tuple[str, str]],
              args: dict[str, str]) -> dict[str, Any]:
    """The atom's effect in the surface-neutral vocabulary, computed from the two readings.

    Roles are what make it portable: the surface's private identity is not part of the description,
    and the argument the call was given is ARG on every machine. `addressable` records whether the
    effect actually depended on that argument -- an atom that changes the world the same way no
    matter what it is told cannot be aimed, and saying so is part of the measurement.
    """
    was, now = contents_of(before), contents_of(after)
    arrived = sorted((now - was).elements())
    departed = sorted((was - now).elements())

    def role(text: str) -> str:
        if args.get("content") is not None and text == args["content"]:
            return "ARG"
        if args.get("old") is not None and text == args["old"]:
            return "OLD"
        if text in (PROBE_NEW, PROBE_OLD, "probe_second_content"):
            return "PROBE"
        return "OTHER"

    roles = [role(text) for text in arrived] + [role(text) for text in departed]
    effect = classify(len(after) - len(before), len(arrived), len(departed))
    return {"effect": effect,
            "addressable": effect in EFFECT_VOCABULARY and all(r in ("ARG", "OLD") for r in roles),
            "delta": {"cardinality_change": len(after) - len(before),
                      "arrived": [role(text) for text in arrived],
                      "departed": [role(text) for text in departed]},
            "identity_changed": sorted(i for i, _c in before) != sorted(i for i, _c in after)}


def bind(text: str | None, args: dict[str, str]) -> str | None:
    if text is None:
        return None
    for key, value in args.items():
        text = text.replace("{" + key + "}", value)
    return text


def execute(atom: Atom, machine: Machine, args: dict[str, str]) -> dict[str, Any]:
    runs = [_run(tuple(bind(step, args) for step in argv), cwd=machine.root, stdin=bind(stdin, args))
            for argv, stdin in atom.steps]
    return {"exit": runs[-1]["exit"], "steps": len(runs),
            "stdout": "".join(run["stdout"] for run in runs)[:400],
            "all_exit_zero": all(run["exit"] == 0 for run in runs)}


# --------------------------------------------------------------------------------------------------
# adaptation: one trial per atom, or active probing that stops once the vocabulary is witnessed
# --------------------------------------------------------------------------------------------------

def probe_args(state: Sequence[tuple[str, str]], state_class: str) -> dict[str, str]:
    """Arguments for one cell of the (atom, state class) table.

    The identity used for `name` is read out of the machine, never invented: in TARGET_EXISTS it is
    the entity that actually holds the probe seed, in TARGET_ABSENT it is a name nobody holds.
    """
    holder = next((ident for ident, content in state if content == PROBE_OLD), None)
    return {"content": PROBE_NEW, "old": PROBE_OLD,
            "name": holder if state_class == "TARGET_EXISTS" and holder else PROBE_NEW + "_fresh",
            "target": PROBE_NEW + "_path"}


def adapt(machine: Machine, *, active: bool,
          needed: Sequence[str] = EFFECT_VOCABULARY) -> dict[str, Any]:
    """Learn what the offered atoms do, one cell of the (atom, state class) table at a time.

    Every field here came from executing something. The table is the point: if an atom behaves
    differently depending on whether its target already exists, then "experience it once" gives one
    cell and the other cell stays unknown -- which is a cost, and it is counted as one.
    """
    library: list[dict[str, Any]] = []
    witnessed: set[tuple[str, str]] = set()
    trials = 0
    cells = [(atom, state_class) for atom in machine.atoms for state_class in STATE_CLASSES]
    for atom, state_class in cells:
        if active and all((effect, state_class) in witnessed for effect in needed):
            continue
        machine.reset()
        before = machine.read()
        args = probe_args(before, state_class)
        result = execute(atom, machine, args)
        effect = effect_of(before, machine.read(), args)
        trials += 1
        library.append({"atom": atom.ident, "state_class": state_class,
                        "steps": [[list(argv), stdin] for argv, stdin in atom.steps],
                        "exit": result["exit"], **effect})
        if effect["effect"] in EFFECT_VOCABULARY:
            witnessed.add((effect["effect"], state_class))
    machine.reset()
    return {"trials": trials, "atoms_offered": len(machine.atoms), "cells": len(cells),
            "library": library,
            "witnessed": sorted(f"{effect}@{state_class}" for effect, state_class in witnessed),
            "missing": sorted(f"{effect}@{state_class}" for effect in needed for state_class in STATE_CLASSES
                              if (effect, state_class) not in witnessed)}


# --------------------------------------------------------------------------------------------------
# requests: stated in the shared vocabulary, decided by the machine's own reader
# --------------------------------------------------------------------------------------------------

@dataclasses.dataclass(frozen=True)
class Request:
    effect: str
    content: str = ""
    old: str = ""
    index: int = 0


def satisfied(request: Request, before: Sequence[tuple[str, str]],
              after: Sequence[tuple[str, str]]) -> bool:
    """Read the machine. Do not ask it.

    The verdict is the difference between what the reader said before and after -- never an exit
    code and never a line of stdout, both of which the command under test can produce at will.
    """
    was, now = contents_of(before), contents_of(after)
    if request.effect == PERSIST:
        return now[request.content] == was[request.content] + 1
    if request.effect == REMOVE:
        return was[request.old] >= 1 and now[request.old] == was[request.old] - 1
    if request.effect == REPLACE:
        return now[request.content] == was[request.content] + 1 and \
            was[request.old] >= 1 and now[request.old] == was[request.old] - 1
    return False


def bindings_for(request: Request, state: Sequence[tuple[str, str]]) -> dict[str, str]:
    """Identity is used for BINDING an argument, never for classifying an effect."""
    holder = next((ident for ident, content in state if content == request.old), None)
    return {"content": request.content, "old": request.old,
            "name": holder if holder and request.effect != PERSIST else request.content + "_member",
            "target": request.content + "_path"}


def class_of(request: "Request") -> str:
    """Which cell of the table this request starts in. A request that names an entity that must
    already exist is answered by the measurements taken with the target present."""
    return "TARGET_ABSENT" if request.effect == PERSIST else "TARGET_EXISTS"


def ordered_atoms(machine: Machine, library: Sequence[dict[str, Any]],
                  effect: str, state_class: str) -> list[str]:
    rows = [row for row in library
            if row["effect"] == effect and row["state_class"] == state_class]
    rows.sort(key=lambda row: (not row["addressable"], row["atom"]))
    return [row["atom"] for row in rows]


def solve(machine: Machine, request: Request, library: Sequence[dict[str, Any]]) -> dict[str, Any]:
    """One trial, then read. A refusal is a refusal; the request is not retried into passing."""
    before = machine.read()
    candidates = ordered_atoms(machine, library, request.effect, class_of(request))
    if not candidates:
        return {"request": request, "status": "UNREACHABLE__NO_MEASURED_ATOM_HAS_THIS_EFFECT",
                "trials": 0}
    trials = 0
    for ident in candidates:
        atom = next(a for a in machine.atoms if a.ident == ident)
        execute(atom, machine, bindings_for(request, before))
        trials += 1
        after = machine.read()
        if satisfied(request, before, after):
            return {"request": request, "status": "SOLVED", "trials": trials, "atom": ident}
        before = after
    return {"request": request, "status": "REFUSED__THE_READER_DISAGREED", "trials": trials}


def by_demonstration(machine: Machine, request: Request) -> dict[str, Any]:
    """The current paradigm: try until it works, then forget, then start over on the next one."""
    before = machine.read()
    for trials, atom in enumerate(machine.atoms, start=1):
        execute(atom, machine, bindings_for(request, before))
        after = machine.read()
        if satisfied(request, before, after):
            return {"request": request, "status": "SOLVED", "trials": trials, "atom": atom.ident}
        before = after
    return {"request": request, "status": "REFUSED__EXHAUSTED", "trials": len(machine.atoms)}


# --------------------------------------------------------------------------------------------------
# the run
# --------------------------------------------------------------------------------------------------

def requests_for() -> list[Request]:
    """The same four requests of every machine, in the shared vocabulary."""
    return [Request(PERSIST, content=TASK_TOKENS[0], index=0),
            Request(PERSIST, content=TASK_TOKENS[1], index=1),
            Request(REPLACE, content=TASK_TOKENS[2], old=PROBE_OLD, index=2),
            Request(REMOVE, old=PROBE_OLD, index=3)]


def measure(machine: Machine, *, with_demonstration: bool) -> dict[str, Any]:
    started = time.time()
    full = adapt(machine, active=False)
    active = adapt(machine, active=True)
    library = active["library"]
    requests: list[dict[str, Any]] = []
    for request in requests_for():
        machine.reset()  # the starting state, not charged to either regime
        outcome = solve(machine, request, library)
        requests.append({"index": request.index, "effect": request.effect,
                         "status": outcome["status"], "trials": outcome["trials"],
                         "atom": outcome.get("atom")})
    demonstration: list[dict[str, Any]] = []
    if with_demonstration:
        for request in requests_for():
            machine.reset()
            outcome = by_demonstration(machine, request)
            demonstration.append({"index": request.index, "effect": request.effect,
                                  "status": outcome["status"], "trials": outcome["trials"],
                                  "atom": outcome.get("atom")})
    machine.reset()
    ours = active["trials"] + sum(row["trials"] for row in requests)
    theirs = sum(row["trials"] for row in demonstration) if demonstration else None
    solved_theirs = sum(1 for row in demonstration if row["status"] == "SOLVED")
    per_request_theirs = (theirs / len(demonstration)) if demonstration else None
    return {
        "machine": machine.name,
        "atoms_offered": full["atoms_offered"],
        "adaptation_trials_probing_every_atom": full["trials"],
        "adaptation_trials_active": active["trials"],
        "effects_witnessed_by_probing": full["witnessed"],
        "atoms_that_cannot_change_the_state": sum(1 for row in full["library"]
                                                  if row["effect"] == INERT),
        "atoms_whose_effect_ignores_the_argument": sum(
            1 for row in full["library"]
            if row["effect"] in EFFECT_VOCABULARY and not row["addressable"]),
        "atoms_whose_only_effect_moves_identity": sum(
            1 for row in full["library"] if row["effect"] == INERT and row["identity_changed"]),
        "unclassified_atoms": [row["atom"] for row in full["library"]
                               if row["effect"] == UNCLASSIFIED],
        "context_sensitive_atoms": sorted({atom for atom in
                                           {row["atom"] for row in full["library"]}
                                           if len({row["effect"] for row in full["library"]
                                                   if row["atom"] == atom}) > 1}),
        "measured_table": full["library"],
        "requests": requests,
        "requests_solved": sum(1 for row in requests if row["status"] == "SOLVED"),
        "ours_trials_for_four_requests": ours,
        "demonstration": demonstration,
        "learn_each_requests_solved": solved_theirs,
        "learn_each_trials": theirs,
        "crossover_requests": (round(active["trials"] / (per_request_theirs - 1), 2)
                               if per_request_theirs and per_request_theirs > 1 else None),
        "trials_to_break_even": (round(active["trials"] / (per_request_theirs - 1) + 1e-9, 2)
                                 if per_request_theirs and per_request_theirs > 1 else None),
        "seconds": round(time.time() - started, 2),
    }


def _shuffled(machine: Machine, seed: int) -> Machine:
    """Relabel and reorder the atoms. If anything about the result changes, the label was knowledge."""
    import random
    order = list(machine.atoms)
    random.Random(seed).shuffle(order)
    labels = [f"{machine.name[:3]}_X{i}" for i in range(1, len(order) + 1)]
    random.Random(seed + 1).shuffle(labels)
    machine.atoms = tuple(Atom(label, atom.steps) for label, atom in zip(labels, order))
    return machine


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", required=True)
    parser.add_argument("--receipt", default=None)
    parser.add_argument("--machines", nargs="*", default=list(MACHINES))
    parser.add_argument("--no-demonstration", action="store_true")
    parser.add_argument("--shuffle", type=int, default=None,
                        help="permute atom order AND names with this seed: no atom may be identified "
                             "by its label or by its position")
    args = parser.parse_args(argv)

    rows: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory() as tmp:
        base = pathlib.Path(tmp)
        with pathlib.Path(args.out).open("w") as handle:
            for name in args.machines:
                root = base / name.lower()
                root.mkdir(parents=True, exist_ok=True)
                machine = MACHINES[name](root)
                if args.shuffle is not None:
                    machine = _shuffled(machine, args.shuffle)
                machine.reset()
                row = measure(machine, with_demonstration=not args.no_demonstration)
                row["attested_state_seal"] = attested.seal(
                    {"machine": name, "atoms": row["atoms_offered"], "requests": 4})
                rows.append(row)
                handle.write(json.dumps(row, default=str) + "\n")
                handle.flush()
                print(f"{name:<11} atoms={row['atoms_offered']:>2} "
                      f"adapt={row['adaptation_trials_active']:>2} "
                      f"ours={row['ours_trials_for_four_requests']:>2} "
                      f"learn-each={row['learn_each_trials']} "
                      f"solved={row['requests_solved']}/4 "
                      f"inert={row['atoms_that_cannot_change_the_state']} "
                      f"identity-only={row['atoms_whose_only_effect_moves_identity']}", flush=True)

    requests_n = 4 * len(rows)
    theirs = sum(row["learn_each_trials"] or 0 for row in rows)
    adaptation = sum(row["adaptation_trials_active"] for row in rows)
    summary = {
        "machines": len(rows),
        "atoms_offered": sum(row["atoms_offered"] for row in rows),
        "adaptation_trials_active": adaptation,
        "adaptation_trials_probing_every_atom":
            sum(row["adaptation_trials_probing_every_atom"] for row in rows),
        "requests": requests_n,
        "requests_solved": sum(row["requests_solved"] for row in rows),
        "ours_trials": sum(row["ours_trials_for_four_requests"] for row in rows),
        "learn_each_trials": theirs,
        "learn_each_requests_solved": sum(row["learn_each_requests_solved"] for row in rows),
        "ours_requests_solved": sum(row["requests_solved"] for row in rows),
        "per_machine": {row["machine"]: {"adaptation": row["adaptation_trials_active"],
                                         "ours": row["ours_trials_for_four_requests"],
                                         "learn_each": row["learn_each_trials"],
                                         "solved": row["requests_solved"],
                                         "solved_by_demonstration": row["learn_each_requests_solved"],
                                         "context_sensitive_atoms": row["context_sensitive_atoms"]}
                        for row in rows},
        "atoms_that_cannot_change_the_state":
            sum(row["atoms_that_cannot_change_the_state"] for row in rows),
        "atoms_whose_effect_ignores_the_argument":
            sum(row["atoms_whose_effect_ignores_the_argument"] for row in rows),
        "atoms_whose_only_effect_moves_identity":
            sum(row["atoms_whose_only_effect_moves_identity"] for row in rows),
        "unclassified_atoms": sum(len(row["unclassified_atoms"]) for row in rows),
    }
    # THE CROSSOVER IS A PER-MACHINE NUMBER AND WAS COMPUTED FROM AGGREGATES.
    #
    # `theirs` and `adaptation` are summed over every machine, but `requests_n` counts FOUR
    # requests in TOTAL (one per machine), so `theirs / requests_n` was a per-machine trials
    # figure divided by a global request count -- 38 / 4 = 9.5 "trials per request".
    # `adaptation / (per_request - 1)` then reported 25.78. The honest quantity is computed
    # per machine and pooled: for each machine, how many requests must it answer before
    # adapting once has spent fewer trials than demonstrating each one.
    REQUESTS_PER_MACHINE = 4
    per_machine_crossover = []
    for row in rows:
        per_req = (row["learn_each_trials"] / REQUESTS_PER_MACHINE
                   if REQUESTS_PER_MACHINE else 0)
        if per_req > 1:
            per_machine_crossover.append(row["adaptation_trials_active"] / (per_req - 1))
    per_request = theirs / requests_n if requests_n else 0
    summary["learn_each_trials_per_request_AGGREGATE_WRONG"] = round(per_request, 3)
    summary["crossover_requests"] = (round(sum(per_machine_crossover) / len(per_machine_crossover), 2)
                                     if per_machine_crossover else None)
    summary["crossover_requests_per_machine"] = [
        round(x, 2) for x in per_machine_crossover]
    # the question the user actually asks: is adapting once cheaper for THIS FEW requests?
    summary["adaptation_total_vs_demonstration_total"] = {
        "adaptation": adaptation, "demonstration": theirs,
        "adaptation_is_cheaper_within_four_requests":
            bool(adaptation < theirs)}
    receipt = {
        "schema": SCHEMA,
        "authority": "NONE__PRODUCER_RUN_SANDBOX",
        "model_dependency_count": 0,
        "external_capability_provider_count": 0,
        "network_calls_at_run_time": 0,
        "shared_effect_vocabulary": list(EFFECT_VOCABULARY),
        "atom_identifiers_are_opaque": True,
        "effects_learned_only_by_execution": True,
        "verdict_source": "each machine's own reader, before and after the command",
        "summary": summary,
        "rows": rows,
    }
    if args.receipt:
        pathlib.Path(args.receipt).write_text(json.dumps(receipt, indent=1, default=str) + "\n")
    print(json.dumps(summary, indent=1, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
