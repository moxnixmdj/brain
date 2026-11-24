#!/usr/bin/env python3
"""Bind a sentence to ONE of the machine's own doors, grounded in the workspace.

WHY THIS EXISTS
---------------
The registry answers "which of our 447 capabilities matches these words". For an ordinary
task that is the wrong question, and the measurement says so: 447 capabilities, zero
gzip/compress, and `python.source.definition_count.v1` chosen for three unrelated sentences
because "count" was the only shared word.

But the machine already knows how to do ordinary things, and it says so itself. `gzip`'s own
help declares `-k --keep`, `-c --stdout`, `-d --decompress`. `sha256sum`'s usage line declares
`[FILE]...`. So the candidate set for an ordinary sentence is not the registry -- it is the
doors the machine publishes, which `tool_census_v1` already enumerates and
`door_witness_search_v1` already proved can be driven.

This module is the smallest thing that joins those to a sentence:

    NAMED OBJECTS   the files the workspace actually holds and the sentence names
    NAMED ARTIFACT  the file the sentence asks for and the workspace does not yet hold
    NAMED PROGRAM   a word in the sentence that is an executable on this machine
    DOOR            one declared operation of that program, driven to exit 0
    PLAN            that door, with the named file where the door wants a file and the
                    artifact captured where the door writes to standard output
    JUDGE           the caller's verifier, never this module's opinion

WHAT IT REFUSES
---------------
It refuses when the sentence names no program, when the named program has no door that will
run, and when a door's operand cannot be grounded in the workspace. Each refusal names what
was missing -- `NO_NAMED_PROGRAM`, `NO_DRIVABLE_DOOR`, `NOTHING_TO_BIND` -- because a refusal
that names the gap is the only useful kind.

WHAT IT DOES NOT DO
-------------------
It composes exactly one door. A sentence needing a pipeline (`wc -l | ...`) or a small program
(to emit JSON) is out of reach, and this module says so rather than pretending: it will run
the single door and the caller's verifier will reject the artifact. That is a measured rung on
a ladder, not a success.

Zero model calls. Zero network. No parameters. Nothing here names a program, a flag or a
meaning: the program comes from the sentence, and the door comes from the program.
"""
from __future__ import annotations

import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
from typing import Any, Iterable, Mapping, Sequence

REPO = pathlib.Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from canonical.runtime import tool_census_v1 as C  # noqa: E402
from canonical.runtime import door_witness_search_v1 as W  # noqa: E402

SCHEMA = "PROJECT_BRAIN_GROUNDED_BINDER_V1"

#: A word that looks like a file name. Nothing about its meaning: an extension is a shape.
_NAME = re.compile(r"[A-Za-z0-9_.\-/]+\.[A-Za-z0-9]{1,8}\b")
#: Words a sentence uses that are never objects, programs or artifacts.
_STOP = frozenset("""a an the and or of to in on for with that this it is are be so which who
into from by as at its their there then than not no yes if when where what how all any each
every some more most other such only own same very can will just should would could may""".split())


# --------------------------------------------------------------------------- #
# what the sentence names, and whether the workspace agrees
# --------------------------------------------------------------------------- #

def _tokens(text: str) -> list[str]:
    raw = [word.strip(".,;:!?()[]\"'").lower() for word in str(text or "").split()]
    return raw


def _words_in(text: str) -> list[str]:
    """Words, with file names broken into their parts: `tar.gz` is `tar` and `gz`.

    A dotted token is a NAME, not a word, and treating it as one lost the program the gate's
    own task asked for: "logs.tar.gz" matched no program because the index knows `tar`.
    """
    return [part for token in _tokens(text)
            for part in re.split(r"[./_=]", token) if part]


def named_objects(instruction: str, root: pathlib.Path) -> dict[str, list[str]]:
    """Files the sentence names AND the workspace holds, and artifacts it names that are absent.

    Grounding is the whole point: a name that is not in the workspace is not an object, it is
    a word. This is the check the compiler did not make when it bound `source_root: "."` while
    the sentence said `data.txt`.
    """
    present: list[str] = []
    absent: list[str] = []
    for candidate in _NAME.findall(str(instruction or "")):
        candidate = candidate.strip("./")
        if not candidate:
            continue
        path = root / candidate
        if path.exists():
            present.append(candidate)
        else:
            absent.append(candidate)
    return {"files": sorted(set(present)), "artifacts": sorted(set(absent))}


def named_programs(instruction: str, *, which=shutil.which) -> list[str]:
    """Words in the sentence that are executables on THIS machine.

    Naming is not guessing: a word the sentence contains that the machine answers to is a
    candidate the sentence itself proposed. Nothing here holds a list of program names.
    """
    found: list[str] = []
    for token in _tokens(instruction):
        if token in _STOP or len(token) < 2 or "." in token or token in found:
            continue
        if which(token):
            found.append(token)
    return found


# --------------------------------------------------------------------------- #
# the door
# --------------------------------------------------------------------------- #

def drivable_doors(program: str, *, depth: int = 1, timeout: float = W.TRIAL_SECONDS,
                   budget: int = 24) -> list[dict[str, Any]]:
    """Every declared operation of `program` that actually runs, with its command form.

    The census declares; the search drives. An operation that will not run is not a door, and
    the search's own refusal is reused rather than re-decided here.
    """
    operations = W.operations_of(program, depth=depth)
    report = W.discover(program, operations, budget=budget, timeout=timeout)
    doors: list[dict[str, Any]] = []
    for row in report.get("rows") or []:
        if row.get("effect") not in ("DOOR", "SENSOR"):
            continue
        # A DOOR CHANGES THE WORLD; A PLAQUE DESCRIBES THE PROGRAM. The program says which is
        # which in its own words -- "display this help and exit", "output version information
        # and exit" -- so the two phrases are quoted from the machine, not from us. Without
        # this, `networkctl --version` was accepted as the way to count lines.
        said = str(row.get("description") or "").lower()
        if "this help" in said or "version information" in said:
            continue
        argv = row.get("winning_argv") or row.get("argv")
        if not argv:
            continue
        doors.append({"id": row["id"], "argv": list(argv), "aliases": row.get("aliases") or [],
                      "effect": row.get("effect"),
                      "description": row.get("description"),
                      "moved_by": row.get("moved_by")})
    return doors


def _tree_digest(root: pathlib.Path, exclude: str | None = None) -> str:
    """The workspace's content fingerprint, with one object left out.

    The object under test MUST be excluded: the differential writes different bytes into it on
    purpose, so including it makes every command look as though its answer depended on the
    input. That single mistake let `networkctl --version` pass the dependence test -- measured,
    and the reason the gate still reported eight failures after the plaques were filtered.
    """
    import hashlib
    accumulator = hashlib.sha256()
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        relative = str(path.relative_to(root))
        if exclude and relative == exclude:
            continue
        accumulator.update(relative.encode())
        try:
            accumulator.update(hashlib.sha256(path.read_bytes()).digest())
        except OSError:
            accumulator.update(b"<unreadable>")
    return accumulator.hexdigest()


def _answer_of(argv: Sequence[str], root: pathlib.Path,
               exclude: str | None = None) -> tuple[int, str, str]:
    """What one invocation answers: exit, stdout, and the workspace afterwards."""
    completed = subprocess.run(argv, cwd=str(root), capture_output=True, timeout=20.0,
                               stdin=subprocess.DEVNULL)
    return (completed.returncode, completed.stdout.decode("utf-8", "replace"),
            _tree_digest(root, exclude))


def depends_on(argv: Sequence[str], root: pathlib.Path, source: str) -> bool:
    """Does the invocation's answer CHANGE when the named object changes?

    This is the test that separates a door from a plaque. `sha256sum --version` exits 0 and
    prints a banner whatever file it is handed; run against the named object and against a
    byte-different object of the same name, the two answers are identical, so the door does
    not depend on the thing the sentence named and it is refused. `sha256sum data.txt` answers
    two different hashes, so it does.

    It is language-free (no help text, no flag meaning, no per-program table), cheap (two
    bounded runs) and it is the only test here that cannot be satisfied by printing a banner.
    """
    baseline_root = pathlib.Path(tempfile.mkdtemp(prefix="bind-base-"))
    perturbed_root = pathlib.Path(tempfile.mkdtemp(prefix="bind-pert-"))
    try:
        for folder in (baseline_root, perturbed_root):
            for item in root.iterdir():
                if item.is_file():
                    shutil.copy2(item, folder / item.name)
        pert = perturbed_root / source
        if pert.exists():
            pert.write_bytes(pert.read_bytes() + b"\nZZZ-differential-marker\n")
        first = _answer_of(argv, baseline_root, exclude=source)
        second = _answer_of(argv, perturbed_root, exclude=source)
        # Silence is not a plaque: `gzip --keep` prints nothing and still depends on its
        # input. The banner case is already excluded, because a banner answers the same for
        # both objects. Requiring non-empty output would have rejected every quiet writer.
        return first[0] == second[0] and (first[1] != second[1] or first[2] != second[2])
    finally:
        shutil.rmtree(baseline_root, ignore_errors=True)
        shutil.rmtree(perturbed_root, ignore_errors=True)


def _words(text: str) -> set[str]:
    return {word[:6] for word in re.findall(r"[a-z]+", str(text or "").lower())
            if word not in _STOP and len(word) > 2}


def speaks_to(door: Mapping[str, Any], instruction: str, program: str) -> int:
    """How many content words the door's OWN description shares with the sentence.

    `wc --lines` says "print the newline counts"; `wc --bytes` says "print the byte counts".
    The sentence "count the lines" shares `lines` with the first and nothing with the second,
    so the program's own words choose the measure -- not a rule we wrote. This is the tie-break
    the first version lacked: it took whichever door passed the dependence test first and
    answered 31 bytes when the sentence asked for 5 lines.
    """
    said = {word for word in re.findall(r"[a-z]+", str(instruction or "").lower())} - _words(program)
    # AN IDENTIFIER IS NOT A PROSE MATCH. `wc` publishes `--lines`; a sentence that says "lines"
    # has named that option exactly, and no stemming is needed or wanted. The description only
    # breaks ties between doors whose identifiers the sentence did not name.
    names = {token.strip("-").lower() for token in (door.get("argv") or []) if token.startswith("-")}
    names |= {alias.strip("-").lower() for alias in (door.get("aliases") or [])}
    named = len(said & names)
    described = len(said & {word for word in re.findall(r"[a-z]+", str(door.get("description") or "").lower())}
                     - _words(program))
    return 10 * named + described


def _slot_positions(argv: Sequence[str]) -> list[int]:
    """Where a value sits in a door's command form: the census's own binder vocabulary."""
    return [index for index, token in enumerate(argv)
            if token in W.BINDER_VALUES or (token.startswith("-") and "=" in token)]


def bind(door: Mapping[str, Any], *, source: str | None, artifact: str | None) -> list[str] | None:
    """Put the grounded objects where the door wants them; None if it cannot be grounded.

    A door that names a file gets the file the sentence named. A door that names an output
    gets the artifact the sentence named. A door with a value slot that the workspace cannot
    fill is refused rather than filled with something invented -- which is exactly the failure
    `in.txt`/`out.bin` produced across 4,352 declared operations.
    """
    argv = list(door["argv"])
    slots = _slot_positions(argv)
    if not slots:
        return argv if source is None and artifact is None else argv
    # a door that mentions out.bin is a writer: the artifact goes there
    if artifact:
        for index in slots:
            token = argv[index]
            if token.startswith("-") and "=" in token:
                head, _, _value = token.partition("=")
                argv[index] = f"{head}={artifact}"
            elif token == "out.bin":
                argv[index] = artifact
        # THE ARTIFACT IS NOT AN OPERAND UNLESS THE DOOR DECLARED A PLACE FOR IT.
        # Appending it made `sha256sum --binary data.txt digest.txt` exit 1 on a file that
        # does not exist; the artifact of a standard-output door is the redirection target,
        # which `run` writes. Adding it to the command was this module's own version of the
        # census's `in.txt` mistake.
    if source:
        for index in slots:
            token = argv[index]
            if token.startswith("-") and "=" in token:
                head, _, value = token.partition("=")
                if value in ("in.txt", "out.bin"):
                    argv[index] = f"{head}={source}"
            elif token in ("in.txt", "out.bin") and token != artifact:
                argv[index] = source
        # the caller tries the appended form as a separate variant, because whether a door
        # takes an operand is its own declaration and this function must not guess
    
    # a value slot still holding the census's canned filler is ungrounded
    if any(token in ("in.txt", "out.bin") for token in argv):
        return None
    return argv


def variants(door: Mapping[str, Any], *, source: str | None,
             artifact: str | None) -> list[list[str]]:
    """The bounded command forms one door may take, most specific first."""
    base = bind(door, source=source, artifact=artifact)
    if not base:
        return []
    forms = [base]
    if source and source not in base:
        forms.append([*base, source])
    return forms


# --------------------------------------------------------------------------- #
# running it
# --------------------------------------------------------------------------- #

def run(instruction: str, root: str | pathlib.Path, *, timeout: float = 20.0,
        routed: Sequence[str] | None = None, max_programs: int = 3,
        max_doors: int = 4) -> dict[str, Any]:
    """Try to satisfy the sentence with one grounded door. Say exactly what happened.

    SUCCESS HAS A SHAPE, and it is not "exit 0":

      * the sentence named a program the machine answers to, and
      * a door of that program DEPENDS ON the object the sentence named, and
      * when the sentence names an artifact, that artifact exists afterwards, and
      * when the sentence names no artifact, the workspace itself changed.

    A door that exits 0 and leaves nothing behind achieved nothing, so it is not counted.
    """
    root = pathlib.Path(root)
    named = named_objects(instruction, root)
    named_found = named_programs(instruction)
    # Naming the program is the caller choosing it; routing is the fallback, and its order is
    # kept so the measure reports how far routing had to guess.
    # NAMING IS A PREFERENCE, NOT AN EXCLUSION. "compressed copy ... that gunzip can restore"
    # names the decompressor; taking the named program as the only candidate refused the task
    # even though `gzip` was the very next candidate. The named one is tried first, then the
    # routed ones, and execution decides.
    ordered: list[str] = []
    for candidate in [*named_found, *(p for p in (routed or []) if shutil.which(p))]:
        if candidate and candidate not in ordered:
            ordered.append(candidate)
    programs = ordered[:max_programs]
    attempt: dict[str, Any] = {"schema": SCHEMA, "instruction": instruction,
                               "named": named, "programs": programs,
                               "named_programs": named_found, "tried": [],
                               "model_calls": 0, "parameters": 0}
    if not programs:
        attempt.update(outcome="REFUSED", reason="NO_NAMED_PROGRAM")
        return attempt
    source = (named["files"] or [None])[0]
    artifact = (named["artifacts"] or [None])[0]
    before = C._digest(str(root))
    for program in programs:
        doors = drivable_doors(program, timeout=min(1.0, timeout))[:max_doors]
        doors.sort(key=lambda door: (speaks_to(door, instruction, program),
                                     door["effect"] == "DOOR"), reverse=True)
        attempt["tried"].append({"program": program, "doors": len(doors),
                                 "speaks_to": [speaks_to(d, instruction, program) for d in doors]})
        for door in doors:
            for argv in variants(door, source=source, artifact=artifact)[:2]:
                if source and not depends_on(argv, root, source):
                    attempt["tried"].append({"program": program, "door": door["id"],
                                             "argv": argv,
                                             "skipped": "DOES_NOT_DEPEND_ON_NAMED_OBJECT"})
                    continue
                completed = subprocess.run(argv, cwd=str(root), capture_output=True,
                                           timeout=timeout, stdin=subprocess.DEVNULL)
                record: dict[str, Any] = {"program": program, "door": door["id"],
                                          "argv": argv, "exit": completed.returncode}
                if completed.returncode != 0:
                    attempt["tried"].append(record)
                    continue
                target = root / artifact if artifact else None
                if target is not None and not target.exists() and completed.stdout:
                    # A standard-output door is captured where the sentence asked. Redirection
                    # is the shell's operator; the value came from the door, not from us.
                    target.write_bytes(completed.stdout)
                    record["captured"] = artifact
                if target is not None and not target.exists():
                    attempt["tried"].append(record)
                    continue
                if target is None and C._digest(str(root)) == before:
                    record["ignored"] = "NO_EFFECT_ON_WORKSPACE"
                    attempt["tried"].append(record)
                    continue
                record["verified_by"] = "workspace_artifact_present"
                attempt["tried"].append(record)
                attempt.update(outcome="EXECUTED", plan=record,
                               artifact=str(target) if target else None)
                return attempt
    attempt.update(outcome="REFUSED",
                   reason="NOTHING_TO_BIND" if len(attempt["tried"]) <= len(programs)
                   else "NO_DEPENDENT_DOOR_PRODUCED_IT")
    return attempt


def main(argv: Sequence[str] | None = None) -> int:
    import argparse
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("instruction")
    parser.add_argument("--root", default=".")
    args = parser.parse_args(argv)
    print(json.dumps(run(args.instruction, args.root), indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
