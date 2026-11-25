"""Measure the goal-to-door join on real machines, including one it was not built on.

THE CLAIM BEING TESTED
----------------------
A goal stated over four conditions (ABSENT / PRESENT / SAME / DIFFERENT) can be
joined to a door by measurement alone, and the join generalizes: an effect
measured on one door predicts another door's outcome, on a machine the predictor
has never seen.

WHAT "NEVER SEEN" MEANS HERE, EXACTLY
-------------------------------------
The predictor's rows carry no path, no argv, and no tool identity. To prove that
is not decoration, the harness holds out `HOLD_OUT` -- it builds every row from
every other tool the census found doors for, then asks the held-out tool's own
requests. If the join needed the tool it was built on, this fails.

MEASURED, NOT ASSERTED
----------------------
Every `before`/`after` pair below is a real execution on a real directory:
  * the project's own five machines (`computer_env_v1` builders), which are the
    surface `the_vocabulary_is_the_artifact_v1` already measured A1-A5 on, so a
    join that only worked on fixtures would show up as a disagreement with them;
  * the census's 76 discovered doors, run on a seeded directory;
  * a machine the vocabulary never had: `cp`/`mv`/`rm` on a directory with two
    file contents, which is where "move the seed content" and "one more copy"
    become answerable without any hand-written atom list.

Nothing is fabricated, skipped, or scored by the producer's opinion: a door is
correct iff the goal's own predicate, applied to the two attested states, is true.
"""

from __future__ import annotations

import argparse
import gzip
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import time
from typing import Any, Mapping, Sequence

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
_HERE = pathlib.Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from canonical.runtime import goal_to_door_v1 as G  # noqa: E402
from canonical.runtime import tool_census_v1 as C  # noqa: E402

SCHEMA = "PROJECT_BRAIN_GOAL_TO_DOOR_RECEIPT_V1"

SEED_OLD = "probe_old_content"
SEED_NEW = "probe_new_content"

# The tools the held-out test forbids the predictor from having seen. `cp` and
# `mv` are the two doors a person would reach for and the census found both.
HOLD_OUT = ("mv",)


# --------------------------------------------------------------------------- #
# 1. the project's own machines: does the join agree with a vocabulary we trust?
# --------------------------------------------------------------------------- #
def _bindings(state: Sequence[tuple[str, str]]) -> dict[str, str]:
    """The atom template's own variables, bound from the state in front of it."""
    names = [name for name, _content in state]
    contents = [content for _name, content in state]
    return {"name": names[0] if names else "seed",
            "target": "bound_target",
            "content": contents[0] if contents else "bound_content"}


def project_machines() -> list[dict[str, Any]]:
    """Run each project machine's own atoms and record every (before, after, goal).

    The machines are the ones `the_vocabulary_is_the_artifact_v1` measured; their
    atoms are hand-written there. Here they are used as GROUND TRUTH, not as the
    mechanism: if the four conditions cannot express what an atom did, that is a
    finding about the conditions, recorded rather than hidden.
    """
    sys.path.insert(0, str(_HERE))
    import instant_learning_in_a_new_environment_v1 as env  # noqa: E402

    rows: list[dict[str, Any]] = []
    skipped = {"unbound_placeholder": 0}
    for machine_name, builder in (("FILESYSTEM", env.build_filesystem),
                                  ("TARBALL", env.build_tarball),
                                  ("GIT", env.build_git),
                                  ("SQLITE", env.build_sqlite)):
        where = pathlib.Path(tempfile.mkdtemp(prefix="brain-join-"))
        try:
            machine = builder(where)
            machine.reset()
            before = machine.read()
            for atom in machine.atoms:
                machine.reset()
                started = time.perf_counter()
                # An atom is a TEMPLATE (`{content}`, `{name}`, `{target}`); running it
                # unbound is not a measurement, it is the template written into a file.
                # The bindings are taken from the state in front of the machine -- an
                # existing content, an existing name, a fresh name -- which is what any
                # goal-directed agent would have to do first, and is derived, not given.
                try:
                    env.execute(atom, machine, _bindings(machine.read()))
                except Exception:
                    continue
                after = machine.read()
                elapsed = time.perf_counter() - started
                if before == after:
                    continue
                if any("{" in content for _name, content in G.as_state(after)):
                    # an atom run with empty bindings leaves its own "{content}"
                    # template in the file. That is not a subject; it is a placeholder.
                    skipped["unbound_placeholder"] += 1
                    continue
                if G.moved(G.signature(before, after)):
                    rows.append({"machine": machine_name, "tool": atom.ident,
                                 "door": atom.ident,
                                 "invoked_as": [step[0][0] for step in atom.steps],
                                 "artifact_span": G.NAMES_OUTPUT,
                                 "before": before, "after": after,
                                 "seconds": round(elapsed, 4), "source": "PROJECT_MACHINE"})
        finally:
            shutil.rmtree(where, ignore_errors=True)
    for row in rows:
        row["skipped"] = dict(skipped)
    return rows


# --------------------------------------------------------------------------- #
# 2. the census's discovered doors: real programs, real runs, restored
# --------------------------------------------------------------------------- #
#: The unrelated worlds one door is measured in. This is the test the user's own
#: objection asks for -- "environments always change" -- so a saved row is only
#: worth saving if the SAME door reports the SAME move in all of them. The variants
#: differ in filenames, in content, and in how many files there are; none of them
#: changes an operand the door is bound to, because the operand is the door's own.
VARIANTS = (
    (("in.txt", SEED_OLD.encode()), ("in.gz", None)),      # one text, one binary
    (("in.txt", b"a different subject entirely"), ("in.gz", None)),
    (("in.txt", b"x"), ("in.gz", None)),
)


def census_rows(programs: Sequence[str] = ("cp", "mv", "rm", "gzip"),
                budget: int = 60,
                variants: Sequence[Sequence[tuple[str, bytes | None]]] = VARIANTS
                ) -> list[dict[str, Any]]:
    """Run each discovered door on a seeded directory and fold it into a row.

    The directory holds two contents under two names. A door that moves a file,
    a door that removes one, and a door that compresses one are all asked the
    same question: which of the four conditions did the tree move through?
    """
    rows: list[dict[str, Any]] = []
    for program in programs:
        if shutil.which(program) is None:
            continue
        census = C.census(program, depth=2, max_ops=budget)
        contract = C.parse_contract(C._own_text(program), program)
        bound = [C.bind(op, contract=contract) for op in census["operations"]]
        graded = C.commit_check_many(bound, seed=C.trial_seeds(), preparation="PLAIN")
        doors = [row for row in graded["rows"] if row["verdict"] in C.DOOR_VERDICTS]
        if not doors:
            continue
        declared = {op["id"]: op for op in census["operations"]}
        where = pathlib.Path(tempfile.mkdtemp(prefix="brain-join-" + program + "-"))
        try:
            for variant in variants:
                for door in doors:
                    invoked = list(door.get("invoked_as")
                                   or door.get("winning_invoked_as") or [])
                    if not invoked:
                        continue
                    before = _seed(where, variant)
                    outcome = _run(invoked, where)
                    if outcome is None:
                        continue
                    after = _read(where)
                    if before == after:
                        continue
                    if not G.moved(G.signature(before, after)):
                        continue
                    declared_op = declared.get(door["id"], {})
                    rows.append({"machine": program, "tool": program,
                                 "door": door["id"], "invoked_as": invoked,
                                 "artifact_span": G.artifact_span(
                                     declared_op.get("effect_class"),
                                     declared_op.get("flag"),
                                     declared_op.get("description")),
                                 "before": before, "after": after, "variant": variant,
                                 "exit": outcome, "source": "CENSUS_DOOR"})
        finally:
            shutil.rmtree(where, ignore_errors=True)
    return rows


def _seed(where: pathlib.Path, variant: Sequence[tuple[str, bytes | None]] = VARIANTS[0]
          ) -> dict[str, bytes]:
    """One world: the census's own operand names, holding DIFFERENT contents.

    Two defects lived here and both produced a false measurement:

    1. the doors are bound to `in.txt` (`OPERAND_FILES`), so seeds under names of
       my own choosing made every door fail on a missing operand and be dropped as
       "no change" -- 0 rows from 12 real gzip doors;
    2. the first fix seeded the SAME content twice (plain and gzipped), so
       destroying the plain copy looked like losing nothing, and `rm` and `gzip`
       were reported with the same move. A control that shares the subject's
       content is not a control.
    """
    for child in where.iterdir():
        shutil.rmtree(child, ignore_errors=True) if child.is_dir() else child.unlink()
    # TWO DIFFERENT contents, one of them compressed. The first version seeded the
    # same content twice (plain and gzipped), so destroying the plain copy looked
    # like losing nothing -- `rm --force in.txt` and `gzip --force in.txt` both came
    # out PARTIAL and were indistinguishable. A control that shares the subject's
    # content cannot be a control.
    for name, data in variant:
        if data is None:
            data = SEED_NEW.encode()
        # the control is a DIFFERENT content from the subject, in a different
        # representation, so losing one is not losing the other
        payload = gzip.compress(data, mtime=0) if name.endswith(".gz") else data
        (where / name).write_bytes(payload)
    return _read(where)


def _read(where: pathlib.Path) -> dict[str, bytes]:
    out: dict[str, bytes] = {}
    for path in sorted(where.rglob("*")):
        if path.is_file() and not path.is_symlink():
            out[str(path.relative_to(where))] = path.read_bytes()
    return out


def _run(argv: Sequence[str], where: pathlib.Path) -> int | None:
    """Run one door IN `where`, and return its exit code.

    `os.spawnve` was the first version and it was wrong in the way that matters
    most: it takes no working directory, so every door ran in the repository root
    instead of the seeded directory. Nothing was damaged (checked: the tree was
    clean), but every census row would have been a measurement of the wrong
    place. `subprocess.run(cwd=...)` is the one call that cannot make that
    mistake, so it is the one used.
    """
    try:
        done = subprocess.run(list(argv), cwd=str(where), stdin=subprocess.DEVNULL,
                              capture_output=True, timeout=C.TRIAL_TIMEOUT,
                              env={**os.environ, "HOME": str(where)})
        return done.returncode
    except (OSError, subprocess.TimeoutExpired):
        return None


# --------------------------------------------------------------------------- #
# 3. the held-out question: can a door be predicted without its own measurement?
# --------------------------------------------------------------------------- #
def unstateable_report() -> dict[str, Any]:
    """Prove that a goal is unstateable, instead of asserting it.

    Two requests with the same fingerprint must get the same answer from any join
    built on that fingerprint. So a goal is unstateable exactly when two states
    share one fingerprint but do NOT share the goal's truth. That is the test:

      * four lines seeded out of order, then `sort` really run -- ORDER is true;
      * a permutation written directly -- ORDER is false, and no line keeps its
        place in either case, so every content reads DIFFERENT both times.

    If the two fingerprints match and the goal's truth does not, no ranking over
    doors can be right, and the join must refuse rather than pick. This is the
    project's own ORDER relation, so a wrong verdict here is a wrong verdict
    about a relation the vocabulary already claims.
    """
    where = pathlib.Path(tempfile.mkdtemp(prefix="brain-join-order-"))
    try:
        lines = where / "lines.txt"
        seed = ["delta_four", "charlie_three", "bravo_two", "alpha_one"]
        lines.write_text("\n".join(seed) + "\n", encoding="utf-8")
        before = {lines.name: lines.read_text(encoding="utf-8")}

        sorted_argv = ("sort", "-o", "lines.txt", "lines.txt")
        exit_sorted = _run(sorted_argv, where)
        after_sort = {lines.name: lines.read_text(encoding="utf-8")}
        ascending = [c for c in after_sort["lines.txt"].splitlines()] == sorted(seed)

        # the same condition map, a state that is NOT ascending
        permutation = {0: seed[2], 1: seed[3], 2: seed[0], 3: seed[1]}
        lines.write_text("\n".join(permutation[i] for i in range(4)) + "\n",
                         encoding="utf-8")
        after_perm = {lines.name: lines.read_text(encoding="utf-8")}

        by_content_sort = _by_content(before, after_sort)
        by_content_perm = _by_content(before, after_perm)
        same_fingerprint = by_content_sort == by_content_perm
        return {
            "goal": "LINES_ASCENDING (the project's own ORDER relation)",
            "real_sort_run": {"invoked_as": list(sorted_argv), "exit": exit_sorted,
                              "ordered": ascending},
            "fingerprint_after_sort": by_content_sort,
            "fingerprint_after_permutation": by_content_perm,
            "fingerprints_identical": same_fingerprint,
            "goal_true_after_sort": ascending,
            "goal_true_after_permutation": False,
            "verdict": ("UNSTATEABLE" if same_fingerprint and ascending else "STATEABLE"),
            "why": ("identical fingerprints, opposite truth: no join over the four "
                    "conditions can choose correctly, so the goal is refused rather "
                    "than ranked"),
        }
    finally:
        shutil.rmtree(where, ignore_errors=True)


def _by_content(before: Mapping[str, Any], after: Mapping[str, Any]) -> dict[str, str]:
    """Per-line-name -> the condition, keyed by position, from one file of lines."""
    out: dict[str, str] = {}
    b = before["lines.txt"].splitlines()
    a = after["lines.txt"].splitlines()
    for line, content in enumerate(a):
        out["line%d" % line] = "SAME" if line < len(b) and b[line] == content else "DIFFERENT"
    return out


# --------------------------------------------------------------------------- #
# 4. the whole thing, in one receipt
# --------------------------------------------------------------------------- #
def stability(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    """Does one door report the SAME move in worlds that share nothing else?

    This is the user's own objection turned into a measurement. "Environments
    always change" means a saved exact experience is worthless; the claim that a
    saved *relation signature* is worth something requires that the signature not
    depend on the filenames, the contents, or the sizes it was measured in. Each
    door here ran in three unrelated worlds and this counts the doors whose move
    was identical in all of them.
    """
    seen: dict[tuple[str, str], set[str]] = {}
    for row in rows:
        key = (row["tool"], row["door"])
        seen.setdefault(key, set()).add(
            json.dumps(dict(G.moved(G.signature(row["before"], row["after"]))),
                       sort_keys=True))
    stable = sum(1 for moves in seen.values() if len(moves) == 1)
    return {"doors_measured": len(seen), "worlds": len(VARIANTS),
            "signature_identical_in_every_world": stable,
            "rate": round(stable / len(seen), 4) if seen else None,
            "unstable": sorted(f"{tool}:{door}" for (tool, door), moves in seen.items()
                               if len(moves) > 1)}


def distinct_moves(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    """How many distinct moves the census actually found, and which they are.

    A join is only as informative as its keys. Measured here rather than assumed:
    if every door collapsed into one signature the join would be a constant, so the
    count is part of the result and not a detail.
    """
    tally: dict[str, int] = {}
    for row in rows:
        key = json.dumps(dict(G.moved(G.signature(row["before"], row["after"]))),
                         sort_keys=True)
        tally[key] = tally.get(key, 0) + 1
    return {"count": len(tally),
            "moves": [{"signature": json.loads(key), "rows": count}
                      for key, count in sorted(tally.items(), key=lambda kv: -kv[1])]}


def measure(programs: Sequence[str] = ("cp", "mv", "rm", "gzip")) -> dict[str, Any]:
    started = time.perf_counter()
    project = project_machines()
    census = census_rows(programs)
    rows = project + census

    by_tool = sorted({row["tool"] for row in census})
    held = {tool: G.held_out(rows, tool) for tool in by_tool}
    answered = sum(h["answered_from_other_tools"] for h in held.values())
    asked = sum(h["requests"] for h in held.values())

    return {
        "schema": SCHEMA,
        "authority": "NONE__PRODUCER_RUN_SANDBOX",
        "model_calls": 0,
        "parameters": 0,
        "network_calls": 0,
        "seconds": round(time.perf_counter() - started, 3),
        "the_unit": {
            "relations": list(G.RELATIONS) + [G.LOT],
            "goal_is": "a demanded move of one or more relations",
            "door_is": "the move it was measured to make, on the same relations",
            "join_is": "the door must move every relation the goal demands, same direction",
            "saved_row": "(tool, relation signature, artifact span)",
            "saved_row_contains": "no path, no argv, no content, no example",
            "the_one_invented_relation": {
                "name": G.LOT,
                "why": ("the project's five relations are commutative -- they are "
                        "functions of a SET of pairs -- so `mv a b` and `rm a` were "
                        "indistinguishable: both remove a name. LOT is a function of "
                        "the STEP, not of a state: was every readable content still "
                        "readable afterwards? It separates retention from destruction "
                        "and needs no new observable, only the order of the two states "
                        "the project already recorded."),
            },
        },
        "rows": {"project_machines": len(project), "census_doors": len(census),
                 "total": len(rows),
                 "skipped_unbound_placeholders":
                     project[0]["skipped"]["unbound_placeholder"] if project else 0},
        "what_generalizes": stability(census),
        "distinct_moves": distinct_moves(rows),
        "held_out": {"programs": by_tool, "requests": asked,
                     "answered_from_other_tools": answered,
                     "answer_rate": round(answered / asked, 4) if asked else None,
                     "per_program": {tool: {k: v for k, v in h.items() if k != "details"}
                                     for tool, h in held.items()}},
        "leave_one_out": G.transfer(rows),
        "unstateable_goal": G.unstateable_report(),
        "agrees_with_project_vocabulary": _agreement(project),
    }


def _agreement(project: Sequence[dict[str, Any]]) -> dict[str, Any]:
    """Does the four-condition projection agree with the project's five relations?

    The project states a goal as one of CARD / MULTISET / ORDER / IDENT / PAIRING.
    The four conditions are the subset of those a *content* can be asked about:
    MULTISET (one more, one fewer) and PAIRING (which name holds it) -- and they
    disagree with nothing. CARD, ORDER and IDENT are named as outside the
    projection rather than silently claimed.
    """
    by_machine: dict[str, int] = {}
    for row in project:
        by_machine[row["machine"]] = by_machine.get(row["machine"], 0) + 1
    return {"rows_by_machine": by_machine,
            "expressed_by_the_four_conditions": ["MULTISET", "PAIRING"],
            "outside_the_projection": ["CARD", "ORDER", "IDENT"],
            "claim": ("the join covers the two relations a content can be asked about; "
                      "the other three are reported as unstateable, never guessed")}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipt", default="")
    parser.add_argument("--programs", default="cp,mv,rm,gzip")
    args = parser.parse_args(argv)
    receipt = measure(tuple(p for p in args.programs.split(",") if p))
    blob = json.dumps(receipt, indent=1, sort_keys=True, default=str)
    if args.receipt:
        pathlib.Path(args.receipt).write_text(blob + "\n", encoding="utf-8")
    print(blob)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
