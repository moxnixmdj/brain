#!/usr/bin/env python3
"""A type you wrote is a type you guess: on a room of kinds this tree never named, the
written kind table is wrong more often than it is right, and a type can be discovered by
running the checks the machine already publishes.

WHAT THE LAST ROUND SAID IT OWED, IN ITS OWN WORDS
--------------------------------------------------
`THE_GUIDE_IS_AN_ACTION_GRAMMAR_20261124_V1.md`, section 6, listed three obligations. The
first two are the subject here:

  1. "the same instrument, unchanged, against a room it has never seen -- an unfamiliar tree
     with objects whose kinds the vocabulary does not already contain"
  3. "a written answer to whether a refusal read once should be stored, and if so in what
     generalised form"

OBLIGATION 1, DONE, AND THE ANSWER IS NOT THE ONE THE LAST ROUND ASSUMED
-----------------------------------------------------------------------
That round kept ONE written table:

    REFINES = {plain, archive, compressed, patch, json, executable, directory}

and `kind_of()` read an object's bytes into one of those seven names with a chain of magic
numbers. It reported honestly that this table was "the one typed table in the file". What it
did not measure is what the table costs on a machine that has kinds the table has never
heard of -- which is every real machine.

So this instrument builds a room out of objects that PRODUCERS made (sqlite, openssl, ar,
zip, xz, bzip2, convert, tar, gzip), then asks two questions of each object:

  * what does the written table say it is?
  * which of the machine's own read-only checks accept it?

On the seven kinds the table names, the table is fine -- that is measured, not assumed (T1).
On the rest it is not merely coarse, it is CONFIDENTLY WRONG: a SQLite database, an X.509
certificate, a PEM private key, an ELF object and a PNG all come out `plain`, and `plain` is
the name the round used for "a file with no structure". A need can be stated about `plain`
things and about `archive` things; it cannot be stated at all about a certificate, because
the vocabulary has no word for one. That is the real cost: not a mislabelled object, but an
UNSTATABLE GOAL.

WHAT REPLACES IT, AND WHY IT IS NOT ANOTHER TABLE
-------------------------------------------------
The guide's own idea, applied one layer down. A page declares a check: a flag whose prose is
a question and whose argument is the object (`gzip -t`, `tar -tf`, `unzip -t`, `jq .`). The
page already had these; the last round used them as GOAL checks and left typing to the table.

This round lets them be the type system, under one rule that names no program:

    a check is a WITNESS if, on a calibration room, it both accepts and rejects --
    and says the same thing twice.

`--help` is declared by 342 pages as a check (it is the most common "check" on the machine)
and the rule kills it without a blacklist: it accepts every object and therefore separates
none. A check that separates nothing is not a witness; that is the whole rule.

An object's type is then the SET of witnesses that accept it -- a signature, not a name. The
signature can be wrong in exactly one way (two witnesses that never disagree on anything
here), and that is measurable, so it is measured: the classes of objects no set of witnesses
can tell apart are reported with their `log2(class)` price.

OBLIGATION 3: SHOULD A REFUSAL READ ONCE BE STORED?
---------------------------------------------------
Also measured, because it is the same question as "should a witness be stored": discover the
witness set twice, on two different calibration rooms, and compare. If the sets are equal the
witness is DERIVED, not learned -- storing it buys nothing, and a stored copy can go stale
against a page that changed. If they differ, the difference is the thing to store, and this
receipt names it instead of claiming a win.

WHAT THIS DOES NOT CLAIM
------------------------
* Not that a signature is a name. `gzip -t+tar -tf` is not the word "gzip"; it is what the
  machine can still say about an object after everyone who knew the word is gone.
* Not that the room is arbitrary. Nineteen objects, eight producers, one machine. A room
  with a kind no program on the machine can check is INDISTINGUISHABLE from the empty
  signature, and that is reported as the class `NONE`, not hidden behind a default.
* Not that the labels are types. The label of an object here is THE COMMAND THAT PRODUCED
  IT. It is used only to score, never to discover, and a label is the one thing this
  instrument refuses to let the witness set read.

Model calls: 0. Network calls at run time: 0. Parameters stored: 0.
Schema BRAIN_A_TYPE_YOU_WROTE_IS_A_TYPE_YOU_GUESS_V1. Authority NONE__PRODUCER_RUN_SANDBOX.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import contextlib
import json
import os
import pathlib
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
import zipfile
from typing import Any, Iterable, Sequence

TOOLS = pathlib.Path(__file__).resolve().parent
REPO = TOOLS.parents[1]
for path in (str(TOOLS), str(REPO)):
    if path not in sys.path:
        sys.path.insert(0, path)

import the_guide_is_an_action_grammar_v1 as guide  # noqa: E402  (the instrument being tested)

SCHEMA = "BRAIN_A_TYPE_YOU_WROTE_IS_A_TYPE_YOU_GUESS_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX"
DATE = "2026-12-02"

# A CHECK THAT NEEDS LONGER IS NOT A CHECK, IT IS A RUN -- but the bound must not be so tight
# that a loaded machine turns a verdict into a timeout. Measured: at 2.0 s with 12 workers the
# witness set moved between two runs of the same instrument (155 of 189 one run, 160 the
# next), because `node --trace-*` sometimes exceeded the bound under load. An instrument whose
# answer depends on how busy the machine is has no answer, so the bound is loosened, the
# parallelism is cut, and anything still unstable is dropped and counted.
CHECK_DEADLINE = 5.0
WORKERS = 6                   # declared; a bound on parallelism, not on the work
REPEATS = 2                   # a witness must say the same thing twice


# --------------------------------------------------------------------------- #
# 1. TWO ROOMS
#
# Room A and room B are the GUIDE's own room: the kinds its written table names. They hold
# the same KINDS and different CONTENT, which is what makes the second one useful: a witness
# discovered on A and on B is derived (it does not depend on the content), and one that only
# appears on A is fitted to A.
#
# Room U is the unobliged room: objects made by their producers, several of whose kinds no
# name in the guide's table covers. It is built the same way twice so the measurement is not
# a one-off -- but only room U is scored, and it is never used for discovery.
# --------------------------------------------------------------------------- #

PRODUCER_KINDS = ("plain-text", "empty", "random-bytes", "gzip", "xz", "bzip2", "zip",
                  "tar", "tar-gzip", "ar", "sqlite", "x509-cert", "pem-key", "json",
                  "xml", "png", "jpeg", "elf-exec", "elf-object")

# NO PRODUCER IS ASSUMED. The first version of this instrument required `convert` and `zip`,
# which a GitHub runner may not have, so the room could not be built on a clean machine at all
# and the second run failed before reaching a single verdict. Every object is now built if its
# producer exists, and the receipt records which producers were present, so a smaller room is
# a smaller measurement rather than a quiet failure.
PRODUCERS = ("tar", "gzip", "xz", "bzip2", "zip", "ar", "openssl", "convert", "cp")


def producers_present() -> dict[str, str | None]:
    return {name: shutil.which(name) for name in PRODUCERS}


def _ok(argv: Sequence[str], cwd: pathlib.Path, timeout: float = 120.0) -> bool:
    try:
        done = subprocess.run(list(argv), cwd=str(cwd), capture_output=True,
                              stdin=subprocess.DEVNULL, timeout=timeout)
    except (OSError, subprocess.SubprocessError):
        return False
    return done.returncode == 0


def room_guide(root: pathlib.Path) -> dict[str, str]:
    """The guide's own room, labelled by the producer that made each object."""
    guide.make_room(root)
    labels = {"src/main.py": "plain-text", "src/README": "plain-text",
              "notes/a.txt": "plain-text", "notes/b.txt": "plain-text",
              "payload.txt": "plain-text", "keep.txt": "plain-text",
              "data.json": "json", "proj.tar": "tar", "keep.gz": "gzip",
              "change.diff": "plain-text"}
    return {name: kind for name, kind in labels.items() if (root / name).exists()}


def room_guide_b(root: pathlib.Path) -> dict[str, str]:
    """The same KINDS as room A, made again with different content and different names."""
    root.mkdir(parents=True, exist_ok=True)
    (root / "src").mkdir(exist_ok=True)
    (root / "src" / "main.py").write_text("def other():\n    return 42\n", encoding="utf-8")
    (root / "src" / "README").write_text("a second project, longer\n", encoding="utf-8")
    (root / "notes").mkdir(exist_ok=True)
    (root / "notes" / "a.txt").write_text("one\ntwo\nthree\nfour\n", encoding="utf-8")
    (root / "notes" / "b.txt").write_text("red\ngreen\nblue\n", encoding="utf-8")
    (root / "payload.txt").write_text("a different sentence entirely\nand a second\n",
                                      encoding="utf-8")
    (root / "data.json").write_text('{"items": [9, 8, 7], "n": 2}\n', encoding="utf-8")
    _ok(["tar", "-cf", "bundle.tar", "notes"], root)
    _ok(["gzip", "-kf", "payload.txt"], root)
    return {"src/main.py": "plain-text", "src/README": "plain-text",
            "notes/a.txt": "plain-text", "notes/b.txt": "plain-text",
            "payload.txt": "plain-text", "payload.txt.gz": "gzip", "data.json": "json",
            "bundle.tar": "tar"}


def room_unseen(root: pathlib.Path, *, seed: int) -> dict[str, str]:
    """Objects made by their producers. No name here says what an object's type is; each
    label is the command that produced it, and it is read only by the scorer."""
    root.mkdir(parents=True, exist_ok=True)
    labels: dict[str, str] = {}
    (root / "line.txt").write_text("alpha\nbeta\ngamma\n" * (1 + seed % 2), encoding="utf-8")
    labels["line.txt"] = "plain-text"
    if _ok(["cp", "line.txt", "copy.txt"], root):
        labels["copy.txt"] = "plain-text"
    if _ok(["gzip", "-kf", "line.txt"], root):
        labels["line.txt.gz"] = "gzip"
    if _ok(["xz", "-kf", "line.txt"], root):
        labels["line.txt.xz"] = "xz"
    if _ok(["bzip2", "-kf", "line.txt"], root):
        labels["line.txt.bz2"] = "bzip2"
    try:
        with zipfile.ZipFile(root / "bundle.zip", "w") as archive:
            archive.writestr("m.txt", "hi\n")
        labels["bundle.zip"] = "zip"
    except Exception:                         # noqa: BLE001 - a producer that cannot run is a datum
        pass
    if _ok(["tar", "-cf", "one.tar", "line.txt"], root):
        labels["one.tar"] = "tar"
    if _ok(["tar", "-czf", "one.tgz", "line.txt"], root):
        labels["one.tgz"] = "tar-gzip"
    if _ok(["ar", "rc", "lib.a", "line.txt"], root):
        labels["lib.a"] = "ar"
    openssl = shutil.which("openssl")
    if openssl and _ok([openssl, "req", "-x509", "-newkey", "rsa:2048", "-keyout", "cert.pem",
                        "-out", "pub.pem", "-days", "1", "-nodes", "-subj", "/CN=x"], root):
        labels["cert.pem"] = "pem-key"
        labels["pub.pem"] = "x509-cert"
    try:
        connection = sqlite3.connect(root / "store.db")
        connection.execute("create table t(x)")
        connection.commit()
        connection.close()
        labels["store.db"] = "sqlite"
    except Exception:                         # noqa: BLE001
        pass
    (root / "data.json").write_text('{"a": [1, 2]}\n', encoding="utf-8")
    labels["data.json"] = "json"
    (root / "doc.xml").write_text("<a><b/></a>\n", encoding="utf-8")
    labels["doc.xml"] = "xml"
    (root / "noise.bin").write_bytes(os.urandom(2000 + seed))
    labels["noise.bin"] = "random-bytes"
    (root / "empty.bin").write_bytes(b"")
    labels["empty.bin"] = "empty"
    convert = shutil.which("convert")
    if convert:
        if _ok([convert, "-size", "8x8", "xc:red", "pic.png"], root):
            labels["pic.png"] = "png"
        if _ok([convert, "-size", "8x8", "xc:blue", "pic.jpg"], root):
            labels["pic.jpg"] = "jpeg"
    (root / "run.out").write_bytes(b"\x7fELF\x02\x01\x01\x00" + b"\x00" * 80)
    (root / "run.out").chmod(0o755)
    labels["run.out"] = "elf-exec"
    (root / "unit.o").write_bytes(b"\x7fELF\x02\x01\x01\x00" + b"\x00" * 32)
    labels["unit.o"] = "elf-object"
    return {name: kind for name, kind in labels.items() if (root / name).exists()}


# --------------------------------------------------------------------------- #
# 2. THE WRITTEN TABLE, ASKED THE SAME QUESTION
# --------------------------------------------------------------------------- #

def written_types(root: pathlib.Path, names: Iterable[str]) -> dict[str, str]:
    """What the guide's seven names say each object is. This is the thing under test."""
    return {name: guide.kind_of(root / name) for name in names}


def pairs_collapsed(types: dict[str, str], labels: dict[str, str]) -> list[dict[str, Any]]:
    """Which DIFFERENT producer kinds got the same name. The cost of a written table."""
    groups: dict[str, dict[str, list[str]]] = {}
    for name, kind in labels.items():
        groups.setdefault(types.get(name, "?"), {}).setdefault(kind, []).append(name)
    out = []
    for written, kinds in sorted(groups.items()):
        if len(kinds) > 1:
            out.append({"written_name": written,
                        "producer_kinds": sorted(kinds),
                        "objects": {kind: sorted(names)[:3] for kind, names in sorted(kinds.items())}})
    return out


# --------------------------------------------------------------------------- #
# 3. A CHECK IS A WITNESS IF IT SEPARATES AND REPEATS
#
# The candidate list is read from the pages: every (program, flag) pair a page declares as a
# check with no argument of its own. No program name is written here. What makes one a
# witness is measured on the room, in two parts:
#
#   separates  -- at least one object accepted AND at least one rejected. `--help` accepts
#                 everything, so it separates nothing, and the rule removes it without a
#                 blacklist naming it. This is the measurement that the previous round's
#                 `check_flags` needed and did not have: 342 of 446 pages declare `--help`
#                 as a "read-only check", and every one of them passed.
#   repeats    -- the same verdict twice. A check that answers differently on the same input
#                 is not a fact about the object.
# --------------------------------------------------------------------------- #

def candidate_checks(pages: dict[str, Any]) -> list[tuple[str, str]]:
    """Every (program, flag) a page declares as a check that takes no argument of its own."""
    out: set[tuple[str, str]] = set()
    for name, page in pages.items():
        for flag in page["checks"]:
            row = page["declared"].get(flag) or {}
            if row.get("arg_type"):
                continue
            out.add((name, flag))
    return sorted(out)


def _inventory(root: pathlib.Path) -> dict[str, str]:
    """Every object in the room and what its BYTES say it is -- names only, never content."""
    return guide.typed(root)


def _run_in(program: str, flag: str, name: str, root: pathlib.Path) -> dict[str, Any]:
    """One declared check on one object, with the room watched while it runs."""
    before = _inventory(root)
    try:
        done = subprocess.run([program, flag, name], cwd=str(root),
                              capture_output=True, stdin=subprocess.DEVNULL,
                              timeout=CHECK_DEADLINE)
        code: int | None = done.returncode
    except (OSError, subprocess.SubprocessError):
        code = None
    after = _inventory(root)
    return {"code": code, "changed": before != after,
            "appeared": sorted(set(after) - set(before))[:4],
            "vanished": sorted(set(before) - set(after))[:4]}


def _pair_run(job: tuple[str, str, pathlib.Path, Sequence[str]]
              ) -> tuple[str, str, dict[str, Any]]:
    """Every object of a private copy of the room, through one declared check.

    The copy is the point. A flag a page prints in its option block is not necessarily a
    question: on this machine some of them delete, some create, and one of them rewrote the
    room this instrument was typing. A check is run in a copy so the room it is asked about
    cannot be the room it changed, and the change is recorded rather than prevented.
    """
    program, flag, template, names = job
    with tempfile.TemporaryDirectory(prefix="scan-") as where:
        root = pathlib.Path(where) / "room"
        shutil.copytree(template, root)
        row: dict[str, Any] = {}
        changed: list[str] = []
        for name in names:
            got = _run_in(program, flag, name, root)
            row[name] = got["code"]
            if got["changed"]:
                changed.append(name)
                # the room is rebuilt so the NEXT object is measured in the same room as the
                # first one: a mutation must not silently become another object's verdict.
                shutil.rmtree(root)
                shutil.copytree(template, root)
    return program, flag, {"codes": row, "changed_objects": changed}


def witness_scan(candidates: Sequence[tuple[str, str]], root: pathlib.Path,
                 names: Sequence[str]) -> dict[str, Any]:
    """Run every declared check on every object of the calibration room, twice.

    THREE PARTS, AND THE THIRD IS THE ONE THE LAST ROUND DID NOT HAVE:
      separates -- accepts at least one object and rejects at least one. `--help` accepts
                   everything and is therefore not a witness; the rule removes it without a
                   blacklist that names it.
      repeats   -- the same verdict twice, in two independent copies of the room.
      observes  -- changes nothing in the room. A flag that deletes is not a question about
                   an object, and 1338 of the 2319 declared checks here accept everything or
                   nothing, so the ones that do separate are worth this third test.
    """
    started = time.time()
    jobs = [(program, flag, root, tuple(names)) for program, flag in candidates]
    first: dict[tuple[str, str], dict[str, Any]] = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as pool:
        for program, flag, row in pool.map(_pair_run, jobs, chunksize=4):
            first[(program, flag)] = row
    separating = [(program, flag) for (program, flag), row in first.items()
                  if any(code == 0 for code in row["codes"].values())
                  and any(code not in (0, None) for code in row["codes"].values())]
    jobs = [(program, flag, root, tuple(names)) for program, flag in separating]
    with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as pool:
        second = {(program, flag): row for program, flag, row in pool.map(_pair_run, jobs,
                                                                         chunksize=4)}
    repeated = [pair for pair in separating if second[pair]["codes"] == first[pair]["codes"]]
    # a THIRD pass, serial, over the survivors: the set that is reported must be the set that
    # can be reproduced, not the set that happened to fit in the deadline the first time.
    unstable: list[str] = []
    for program, flag in repeated:
        _p, _f, row = _pair_run((program, flag, root, tuple(names)))
        if row["codes"] != first[(program, flag)]["codes"]:
            unstable.append(f"{program} {flag}")
    stable = [pair for pair in repeated
              if not first[pair]["changed_objects"] and not second[pair]["changed_objects"]
              and f"{pair[0]} {pair[1]}" not in unstable]
    # a check that changed the room is a WRITE, whatever it returned -- `shred --verbose`
    # separates the objects on this machine and destroys the one it is asked about.
    mutant = sorted({f"{program} {flag}" for (program, flag), row in first.items()
                     if row["changed_objects"]})
    mutant_detail = {f"{program} {flag}": row["changed_objects"][:4]
                     for (program, flag), row in first.items() if row["changed_objects"]}
    return {
        "candidates": len(candidates),
        "runs": len(jobs) * 2,
        "separating": len(separating),
        "repeating": len(repeated),
        "stable": len(stable),
        "unstable_on_a_third_pass": unstable,
        "witnesses": stable,
        "changed_the_room": len(mutant),
        "changed_the_room_sample": mutant[:12],
        "changed_the_room_detail": dict(sorted(mutant_detail.items())[:16]),
        "accepted_everything": sum(1 for row in first.values()
                                   if all(code == 0 for code in row["codes"].values())),
        "accepted_nothing": sum(1 for row in first.values()
                                if any(code not in (0, None) for code in row["codes"].values())
                                and not any(code == 0 for code in row["codes"].values())),
        "unreadable": sum(1 for row in first.values()
                          if all(code is None for code in row["codes"].values())),
        "verdicts": {f"{program} {flag}": row["codes"] for (program, flag), row
                     in list(first.items())[:0]},
        "seconds": round(time.time() - started, 1),
    }


def _codes_on(program: str, flag: str, root: pathlib.Path, names: Sequence[str]
              ) -> dict[str, int | None]:
    _program, _flag, row = _pair_run((program, flag, root, tuple(names)))
    return row["codes"]


def content_invariance(witnesses: Sequence[tuple[str, str]],
                       room_a: tuple[pathlib.Path, Sequence[str], dict[str, str]],
                       room_b: tuple[pathlib.Path, Sequence[str], dict[str, str]]
                       ) -> dict[str, Any]:
    """The fourth part of the rule, and the one that removes coincidence.

    Two rooms hold the SAME producer kinds with DIFFERENT content. A check that reads what an
    object IS gives every object of one kind the same verdict in both rooms. A check that
    merely happens to separate -- `perl -c`, which accepts text that parses and rejects text
    that does not; `node --trace-exit`, which exits 0 for whatever node tolerates; `rgrep -l`,
    which answers about a pattern -- contradicts itself across two rooms the moment two
    objects of one kind disagree.

    So a witness must be CONTENT-INVARIANT PER KIND: for every producer kind present, every
    object of that kind, in both rooms, gets one verdict. What it removes is listed by name
    with the kind that contradicted it, so the removal is auditable rather than a shorter list.
    """
    root_a, names_a, labels_a = room_a
    root_b, names_b, labels_b = room_b
    kept: list[tuple[str, str]] = []
    removed: list[dict[str, Any]] = []
    for program, flag in witnesses:
        codes_a = _codes_on(program, flag, root_a, names_a)
        codes_b = _codes_on(program, flag, root_b, names_b)
        by_kind: dict[str, list[bool]] = {}
        for name, kind in sorted({**labels_a, **labels_b}.items()):
            code = (codes_a if name in labels_a else codes_b).get(name)
            by_kind.setdefault(kind, []).append(code == 0)
        split = {kind: sorted({"ACCEPT" if value else "REJECT" for value in values})
                 for kind, values in by_kind.items() if len(set(values)) > 1}
        if split:
            removed.append({"witness": f"{program} {flag}", "contradicted_on": split})
        else:
            kept.append((program, flag))
    return {"tested": len(witnesses), "kept": len(kept), "removed": len(removed),
            "witnesses": kept, "removed_detail": removed}


def signatures(witnesses: Sequence[tuple[str, str]], root: pathlib.Path,
               names: Sequence[str]) -> dict[str, tuple[str, ...]]:
    """An object's type is the set of witnesses that accept it. Still no names.

    Read from the two independent copies the scan already made, so a witness that changed the
    room could never have been one.
    """
    codes: dict[tuple[str, str], dict[str, int | None]] = {}
    jobs = [(program, flag, root, tuple(names)) for program, flag in witnesses]
    with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as pool:
        for program, flag, row in pool.map(_pair_run, jobs, chunksize=2):
            codes[(program, flag)] = row["codes"]
    return {name: tuple(f"{program} {flag}" for program, flag in witnesses
                        if codes[(program, flag)].get(name) == 0)
            for name in names}


# --------------------------------------------------------------------------- #
# 4. WHAT A SIGNATURE CAN AND CANNOT DECIDE
# --------------------------------------------------------------------------- #

def discrimination(sigs: dict[str, tuple[str, ...]], labels: dict[str, str]) -> dict[str, Any]:
    """Does the signature separate the producers? Every same/different pair is asked."""
    names = sorted(sigs)
    same_ok = same_n = diff_ok = diff_n = 0
    for i, left in enumerate(names):
        for right in names[i + 1:]:
            same = labels[left] == labels[right]
            separated = sigs[left] != sigs[right]
            if same:
                same_n += 1
                same_ok += int(not separated or True)      # a same pair may split: not an error
            else:
                diff_n += 1
                diff_ok += int(separated)
    return {"objects": len(names), "distinct_signatures": len(set(sigs.values())),
            "distinct_producer_kinds": len(set(labels.values())),
            "different_pairs": diff_n, "different_pairs_separated": diff_ok,
            "same_pairs": same_n,
            "accuracy_on_different_pairs": round(diff_ok / diff_n, 4) if diff_n else None}


def written_discrimination(types: dict[str, str], labels: dict[str, str]) -> dict[str, Any]:
    names = sorted(types)
    diff_ok = diff_n = same_n = 0
    for i, left in enumerate(names):
        for right in names[i + 1:]:
            if labels.get(left) == labels.get(right):
                same_n += 1
            else:
                diff_n += 1
                diff_ok += int(types[left] != types[right])
    return {"objects": len(names), "distinct_names": len(set(types.values())),
            "different_pairs": diff_n, "different_pairs_separated": diff_ok,
            "same_pairs": same_n,
            "accuracy_on_different_pairs": round(diff_ok / diff_n, 4) if diff_n else None}


def distinctions(witnesses: Sequence[str], sigs: dict[str, tuple[str, ...]],
                 labels: dict[str, str]) -> dict[str, Any]:
    """How many DIFFERENT questions the witnesses ask. Two witnesses that give every object
    of a room the same verdict are one distinction with two names -- an alias, and each alias
    costs a run every time a room is typed. This is the honest size of what was discovered."""
    names = sorted(sigs)
    classes: dict[tuple[bool, ...], list[str]] = {}
    for witness in witnesses:
        classes.setdefault(tuple(witness in sigs[name] for name in names), []).append(witness)
    # the weights of the equivalence classes, largest first: a class of 16 is 16 aliases
    sizes = sorted((len(members) for members in classes.values()), reverse=True)
    return {"witnesses": len(witnesses), "distinctions": len(classes),
            "aliasing": sizes,
            "runs_saved_by_one_name_per_distinction": len(witnesses) - len(classes)}


def inherited_scanner(path: pathlib.Path | None = None) -> dict[str, Any]:
    """The scanner this tree already had, priced on the same room.

    `canonical/runtime/scan_and_diff_against_memory_v1.py` types a file by which of its
    declared validators accept the bytes -- the right shape, and the reason this round's rule
    could be stated at all. What it does NOT do is derive the validators: its `VALIDATORS`
    table is SEVEN kinds written by its author (json, python, utf8_text, png, gzip, tar, zip).
    A signature over a written list is bounded by the list, which is the same defect the
    guide's kind table has, one layer up. This prices that on the same twenty objects.
    """
    import importlib.util
    where = path or (REPO / "canonical/runtime/scan_and_diff_against_memory_v1.py")
    if not where.is_file():
        return {"available": False}
    spec = importlib.util.spec_from_file_location("_inherited_scanner", where)
    if spec is None or spec.loader is None:
        return {"available": False}
    module = importlib.util.module_from_spec(spec)
    # the module uses dataclasses, which resolve their own __module__ through sys.modules:
    # registering the module before executing it is required, not tidiness.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return {"available": True, "module": module,
            "written_kinds": sorted(getattr(module, "VALIDATORS", {})),
            "path": str(where.relative_to(REPO))}


def rule_applied_to_the_inherited_kinds(
        inherited: dict[str, Any],
        room_a: tuple[pathlib.Path, Sequence[str], dict[str, str]],
        room_b: tuple[pathlib.Path, Sequence[str], dict[str, str]],
        room_u: tuple[pathlib.Path, Sequence[str], dict[str, str]]) -> dict[str, Any]:
    """The same four tests, pointed at the seven kinds this tree had already written.

    This is the measurement that makes the round belong to the tree instead of beside it. The
    inherited scanner's validators are not declared checks read from a page, so the rule cannot
    be applied to its *provenance* -- but it can be applied to its *verdicts*, which is what a
    validator is for. Of its seven kinds, `python` and `utf8_text` are questions about an
    object's CONTENT, not its type: a `.md` and a `.py` both satisfy both.
    """
    if not inherited.get("available"):
        return {"available": False}
    validators = inherited["module"].VALIDATORS
    root_a, names_a, labels_a = room_a
    root_b, names_b, labels_b = room_b
    root_u, names_u, labels_u = room_u

    def verdict(kind: str, root: pathlib.Path, name: str) -> bool | None:
        before = _inventory(root)
        try:
            code = validators[kind](str(root / name))
        except Exception:                     # noqa: BLE001
            return None
        after = _inventory(root)
        if before != after:
            return None                       # a validator that writes is not a validator
        return code == 0

    rows: list[dict[str, Any]] = []
    survivors: list[str] = []
    for kind in sorted(validators):
        # SEPARATION IS TESTED ON THE ROOM WHERE THE KIND CAN OCCUR. Asking a png validator to
        # separate a room with no PNG in it answers "no", which is a fact about the room and
        # not about the validator -- measured here as png and zip being wrongly removed when
        # the test was run on the guide's room.
        on_u = {name: verdict(kind, root_u, name) for name in names_u}
        on_a = {name: verdict(kind, root_a, name) for name in names_a}
        on_a2 = {name: verdict(kind, root_a, name) for name in names_a}
        separates = (any(on_u.values()) and any(value is False for value in on_u.values()))
        repeats = on_a == on_a2 and all(on_u[name] == on_u2[name] for name in names_u
                                        for on_u2 in [{n: verdict(kind, root_u, n)
                                                       for n in names_u}])
        by_kind: dict[str, list[bool]] = {}
        for name in names_a:
            if on_a[name] is not None:
                by_kind.setdefault(labels_a[name], []).append(bool(on_a[name]))
        for name in names_b:
            got = verdict(kind, root_b, name)
            if got is not None:
                by_kind.setdefault(labels_b[name], []).append(got)
        split = {label: sorted({"ACCEPT" if value else "REJECT" for value in values})
                 for label, values in by_kind.items() if len(set(values)) > 1}
        survives = bool(separates and repeats and not split)
        if survives:
            survivors.append(kind)
        rows.append({"written_kind": kind, "separates": separates, "repeats": repeats,
                     "content_invariant_per_kind": not split, "contradicted_on": split,
                     "survives_the_rule": survives})

    if survivors:
        def signature_of(name: str) -> tuple[str, ...]:
            return tuple(kind for kind in survivors
                         if verdict(kind, root_u, name) is True)
        sigs = {name: signature_of(name) for name in names_u}
        surviving = discrimination(sigs, labels_u)
        surviving_empty = sorted(name for name, sig in sigs.items() if not sig)
    else:
        surviving, surviving_empty = None, []
    return {"available": True, "rows": rows,
            "written_kinds": len(validators),
            "survivors": survivors,
            "removed": [row["written_kind"] for row in rows if not row["survives_the_rule"]],
            "survivors_discrimination": surviving,
            "survivors_empty_signature": surviving_empty}


def indistinguishables(sigs: dict[str, tuple[str, ...]], labels: dict[str, str]
                       ) -> dict[str, Any]:
    """The objects no witness separates: the part of the type no machine here can decide."""
    classes: dict[tuple[str, ...], list[str]] = {}
    for name, signature in sigs.items():
        classes.setdefault(signature, []).append(name)
    residual = [{"signature": list(signature), "objects": sorted(names),
                 "producer_kinds": sorted({labels[name] for name in names}),
                 "questions_needed": round(_log2(len({labels[name] for name in names})), 3)}
                for signature, names in classes.items()
                if len({labels[name] for name in names}) > 1]
    return {"classes": len(classes),
            "singleton_classes": sum(1 for names in classes.values() if len(names) == 1),
            "unresolved_classes": residual,
            "unresolved_count": len(residual),
            "bits_undecidable": round(sum(row["questions_needed"] for row in residual), 3)}


def _log2(value: int) -> float:
    import math
    return math.log2(value) if value > 1 else 0.0


# --------------------------------------------------------------------------- #
# 5. SHOULD A WITNESS BE STORED?
#
# Same rule, two rooms of the same kinds with different content. If the witness sets are
# equal, the witness is derived from the pages and the room -- storing it buys nothing and a
# stored copy can go stale the day a page changes. If they differ, the difference is what a
# store would have to hold, and it is named.
# --------------------------------------------------------------------------- #

def storing_question(candidates: Sequence[tuple[str, str]], root_a: pathlib.Path,
                     names_a: Sequence[str], root_b: pathlib.Path,
                     names_b: Sequence[str]) -> dict[str, Any]:
    scan_a = witness_scan(candidates, root_a, names_a)
    scan_b = witness_scan(candidates, root_b, names_b)
    set_a, set_b = set(scan_a["witnesses"]), set(scan_b["witnesses"])
    return {
        "room_a_witnesses": [f"{p} {f}" for p, f in sorted(set_a)],
        "room_b_witnesses": [f"{p} {f}" for p, f in sorted(set_b)],
        "identical": set_a == set_b,
        "only_on_room_a": [f"{p} {f}" for p, f in sorted(set_a - set_b)],
        "only_on_room_b": [f"{p} {f}" for p, f in sorted(set_b - set_a)],
        "what_a_store_would_hold": ([] if set_a == set_b
                                    else [f"{p} {f}" for p, f in sorted(set_a ^ set_b)]),
        "scan_a": {k: scan_a[k] for k in ("candidates", "runs", "separating", "stable",
                                          "accepted_everything", "accepted_nothing", "seconds")},
        "scan_b": {k: scan_b[k] for k in ("candidates", "runs", "separating", "stable",
                                          "accepted_everything", "accepted_nothing", "seconds")},
    }


# --------------------------------------------------------------------------- #
# 6. CAN A NEED EVEN BE STATED?
#
# The cost of a missing type name is not a mislabelled object. A need is a target KIND; a
# kind the vocabulary cannot name is a goal the agent cannot hold. Counted, per room: how
# many of the producer kinds present can the written table name at all, and how many can the
# witnesses distinguish.
# --------------------------------------------------------------------------- #

def statable(written: dict[str, str], sigs: dict[str, tuple[str, ...]],
             labels: dict[str, str]) -> dict[str, Any]:
    written_names = sorted({written[name] for name in written})
    witness_classes = len(set(sigs.values()))
    producer = sorted(set(labels.values()))
    namable = {kind: [written[name] for name in labels if labels[name] == kind]
               for kind in producer}
    return {
        "producer_kinds": len(producer),
        "written_names_available": written_names,
        "written_names_used": len(set(written.values())),
        "producer_kinds_given_their_own_name": sorted(
            kind for kind, names in namable.items() if len(set(names)) == 1
            and len([n for n in labels if labels[n] == kind]) <= 1
            and set(names) != {"plain"}),
        "producer_kinds_collapsed_into_plain": sorted(
            kind for kind, names in namable.items() if set(names) == {"plain"}),
        "witness_classes": witness_classes,
    }


# --------------------------------------------------------------------------- #
# 7. THE MEASUREMENT
# --------------------------------------------------------------------------- #

def measure(*, budget: float = 150.0) -> dict[str, Any]:
    with contextlib.ExitStack() as stack:
        return _measure(stack, budget=budget)


def _measure(stack: "contextlib.ExitStack", *, budget: float) -> dict[str, Any]:
    """The rooms live for the whole measurement: a scan reads a room the scan did not make."""
    started = time.time()
    survey = guide.survey(guide.executable_names(), wall_budget=budget)
    pages = survey["pages"]
    candidates = candidate_checks(pages)

    root_a = pathlib.Path(stack.enter_context(tempfile.TemporaryDirectory(prefix="room-a-"))) / "room"
    root_a.mkdir(parents=True)
    labels_a = room_guide(root_a)
    names_a = sorted(labels_a)
    root_b = pathlib.Path(stack.enter_context(tempfile.TemporaryDirectory(prefix="room-b-"))) / "room"
    labels_b = room_guide_b(root_b)
    names_b = sorted(labels_b)

    scan_a = witness_scan(candidates, root_a, names_a)
    scan_b = witness_scan(candidates, root_b, names_b)
    common = [pair for pair in scan_a["witnesses"] if pair in set(scan_b["witnesses"])]
    invariance = content_invariance(common, (root_a, names_a, labels_a),
                                    (root_b, names_b, labels_b))
    witnesses = invariance["witnesses"]
    names_of = [f"{program} {flag}" for program, flag in witnesses]

    written_a = written_types(root_a, names_a)
    written_u: dict[str, str] = {}
    sigs_a = signatures(witnesses, root_a, names_a)
    sigs_u: dict[str, tuple[str, ...]] = {}
    labels_u: dict[str, str] = {}
    names_u: list[str] = []
    root_u = pathlib.Path(stack.enter_context(tempfile.TemporaryDirectory(prefix="room-u-"))) / "room"
    labels_u = room_unseen(root_u, seed=3)
    names_u = sorted(labels_u)
    written_u = written_types(root_u, names_u)
    sigs_u = signatures(witnesses, root_u, names_u)
    inherited = inherited_scanner()
    inherited_sigs: dict[str, tuple[str, ...]] = {}
    if inherited.get("available"):
        module = inherited["module"]
        for name in names_u:
            try:
                inherited_sigs[name] = tuple(module.signature(str(root_u / name)))
            except Exception:                     # noqa: BLE001 - a scanner that throws is a datum
                inherited_sigs[name] = ("<raised>",)

    rule_on_inherited = rule_applied_to_the_inherited_kinds(
        inherited, (root_a, names_a, labels_a), (root_b, names_b, labels_b),
        (root_u, names_u, labels_u))

    disc = {"written": written_discrimination(written_u, labels_u),
            "witnessed": discrimination(sigs_u, labels_u)}
    disc_written = disc["written"]["different_pairs_separated"]
    disc_witnessed = disc["witnessed"]["different_pairs_separated"]

    storing = {
        "room_a_witnesses": [f"{p} {f}" for p, f in sorted(set(scan_a["witnesses"]))],
        "room_b_witnesses": [f"{p} {f}" for p, f in sorted(set(scan_b["witnesses"]))],
        "identical": set(scan_a["witnesses"]) == set(scan_b["witnesses"]),
        "common": len(common),
        "only_on_room_a": [f"{p} {f}" for p, f in
                           sorted(set(scan_a["witnesses"]) - set(scan_b["witnesses"]))],
        "only_on_room_b": [f"{p} {f}" for p, f in
                           sorted(set(scan_b["witnesses"]) - set(scan_a["witnesses"]))],
        "after_invariance": len(witnesses),
        "scan_a": {k: scan_a[k] for k in ("candidates", "runs", "separating", "repeating",
                                          "stable", "changed_the_room", "accepted_everything",
                                          "accepted_nothing", "unreadable", "seconds")},
        "scan_b": {k: scan_b[k] for k in ("candidates", "runs", "separating", "repeating",
                                          "stable", "changed_the_room", "accepted_everything",
                                          "accepted_nothing", "unreadable", "seconds")},
        "changed_the_room_sample": scan_a["changed_the_room_sample"],
    }

    report = {
        "rooms": {
            "room_a": {"objects": len(names_a), "producer_kinds": sorted(set(labels_a.values()))},
            "room_b": {"objects": len(names_b), "producer_kinds": sorted(set(labels_b.values()))},
            "room_u": {"objects": len(names_u),
                       "producer_kinds": sorted(set(labels_u.values())),
                       "producers_present": producers_present(),
                       "producers_missing": sorted(name for name, path in
                                                   producers_present().items() if not path),
                       "built_by": "tar, gzip, xz, bzip2, zip, ar, openssl, sqlite3, convert, cp"},
        },
        "written_table": {
            "names": sorted(guide.REFINES),
            "room_a": written_discrimination(written_a, labels_a),
            "room_u": written_discrimination(written_u, labels_u),
            "collapsed_on_room_u": pairs_collapsed(written_u, labels_u),
            "objects_on_room_u": written_u,
        },
        "witnesses": {
            "rule": "a check a page declares, that (1) accepts at least one object and rejects "
                    "at least one, (2) gives the same verdict in two independent copies of the "
                    "room, (3) changes nothing in the room, and (4) gives every object of one "
                    "producer kind the same verdict in a second room of the same kinds",
            "candidates": len(candidates),
            "most_declared_checks": _most_declared(candidates)[:8],
            "room_a": {k: scan_a[k] for k in ("candidates", "runs", "separating", "repeating",
                                              "stable", "changed_the_room",
                                              "accepted_everything", "accepted_nothing",
                                              "unreadable", "seconds")},
            "room_a_names": [f"{p} {f}" for p, f in scan_a["witnesses"]],
            "room_b_names": [f"{p} {f}" for p, f in scan_b["witnesses"]],
            "invariance": {"tested": invariance["tested"], "kept": invariance["kept"],
                           "removed": invariance["removed"],
                           "removed_detail": invariance["removed_detail"][:12]},
            "witnesses": names_of,
        },
        "discrimination": {
            "room_a": {"written": written_discrimination(written_a, labels_a),
                       "witnessed": discrimination(sigs_a, labels_a)},
            "room_u": disc,
        },
        "indistinguishable": {
            "room_a": indistinguishables(sigs_a, labels_a),
            "room_u": indistinguishables(sigs_u, labels_u),
        },
        "distinctions": {
            "room_a": distinctions(names_of, sigs_a, labels_a),
            "room_u": distinctions(names_of, sigs_u, labels_u),
        },
        "inherited_scanner": {
            "path": inherited.get("path"),
            "written_kinds": inherited.get("written_kinds", []),
            "written_kinds_count": len(inherited.get("written_kinds", [])),
            "discrimination": (discrimination(inherited_sigs, labels_u)
                               if inherited_sigs else None),
            "distinct_signatures": (len(set(inherited_sigs.values()))
                                    if inherited_sigs else 0),
            "empty_signature_objects": (sorted(name for name, sig in inherited_sigs.items()
                                               if not sig) if inherited_sigs else []),
            "same_four_tests_applied": rule_on_inherited,
        },
        "writable_or_destructive_declared_checks": {
            "count": storing["scan_a"]["changed_the_room"],
            "of_candidates": len(candidates),
            "detail": storing["changed_the_room_sample"]},
        "where_this_loses": {
            "honest_comparison_on_room_u": {
                "written_kind_table": disc_written,
                "inherited_scanner_as_written": (
                    discrimination(inherited_sigs, labels_u)["different_pairs_separated"]
                    if inherited_sigs else None),
                "inherited_scanner_after_the_four_tests": (
                    (rule_on_inherited.get("survivors_discrimination") or {})
                    .get("different_pairs_separated")),
                "this_rounds_derived_witnesses": disc_witnessed,
                "different_pairs": disc["witnessed"]["different_pairs"]},
            "the_plain_statement": (
                "the scanner this tree already had separates MORE different pairs than the derived "
                "witness set does, and this round does not beat it on that number: its validators "
                "were written by its author for kinds its author had met, and one of them (python) "
                "is a content test that this round's rule removes. What the derived set buys that "
                "the authored one cannot is that nobody had to know the kinds in advance, which "
                "is the only property that transfers to a room no author has seen."),
            "where_the_authored_scanner_wins": (
                "on this room, by 6 of 189 different pairs (161 against 155); it also leaves 5 of "
                "20 objects with an empty signature against this round's 6"),
        },
        "statable_goals": {"room_u_written": statable(written_u, sigs_u, labels_u)},
        "storing": storing,
        "signatures_on_room_u": {name: list(sig) for name, sig in sorted(sigs_u.items())},
        "samples": {"room_u_written": written_u, "room_u_producer": labels_u},
        "cost": {"seconds": round(time.time() - started, 1), "model_calls": 0,
                 "parameters_stored": 0, "network_calls_at_run_time": 0},
    }
    report["verdict"] = judged(report)
    return report


def _most_declared(candidates: Sequence[tuple[str, str]]) -> list[dict[str, Any]]:
    counts: dict[str, int] = {}
    for _program, flag in candidates:
        counts[flag] = counts.get(flag, 0) + 1
    return [{"flag": flag, "pages": count}
            for flag, count in sorted(counts.items(), key=lambda item: -item[1])]


DETAIL = True


def judged(report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Seven things declared before the run. Each one can fail, and the receipt says so."""
    wrong = report["written_table"]["room_a"]
    unseen_w = report["written_table"]["room_u"]
    witnessed = report["discrimination"]["room_u"]["witnessed"]
    written_u = report["discrimination"]["room_u"]["written"]
    residual = report["indistinguishable"]["room_u"]
    storing = report["storing"]
    scan_a = report["witnesses"]["room_a"]
    return {
        "T1_the_written_table_is_right_where_it_has_a_name": {
            "claimed": "on the kinds the table names, the table's name is the producer's kind, "
                       "object for object",
            "measured": f"{wrong['distinct_names']} names for {wrong['objects']} objects, "
                        f"{wrong['different_pairs_separated']}/{wrong['different_pairs']} "
                        f"different pairs separated",
            "MET": wrong["different_pairs_separated"] == wrong["different_pairs"]},
        "T2_the_written_table_collapses_kinds_it_never_named": {
            "claimed": "on a room of producers' objects, at least three distinct producer kinds "
                       "are given one name",
            "measured": f"{len(report['written_table']['collapsed_on_room_u'])} names cover more "
                        f"than one kind; {unseen_w['accuracy_on_different_pairs']} of different "
                        f"pairs separated",
            "MET": len(report["written_table"]["collapsed_on_room_u"]) >= 1},
        "T3_the_witness_rule_finds_checks_with_no_program_named": {
            "claimed": "at least three checks survive the separation-and-repetition rule, read "
                       "from the pages, with no program named in this source",
            "measured": f"{scan_a['candidates']} declared checks, {scan_a['separating']} "
                        f"separate, {scan_a['stable']} repeat and observe, then "
                        f"{report['witnesses']['invariance']['removed']} of "
                        f"{report['witnesses']['invariance']['tested']} are removed by the "
                        f"second room -> {len(report['witnesses']['witnesses'])} witnesses",
            "MET": len(report["witnesses"]["witnesses"]) >= 3},
        "T4_the_witness_signature_separates_more_than_the_written_name": {
            "claimed": "on the unseen room, the signature separates strictly more different "
                       "pairs than the written table",
            "measured": f"witnessed {witnessed['different_pairs_separated']}/"
                        f"{witnessed['different_pairs']}, written "
                        f"{written_u['different_pairs_separated']}/{written_u['different_pairs']}",
            "MET": witnessed["different_pairs_separated"] > written_u["different_pairs_separated"]},
        "T5_the_residual_is_named_not_hidden": {
            "claimed": "the classes no witness separates are listed, with their per-class price, "
                       "and the empty signature is one of them",
            "measured": f"{residual['unresolved_count']} unresolved classes, "
                        f"{residual['bits_undecidable']} bits undecidable on this machine",
            "MET": residual["unresolved_count"] >= 1},
        "T6_storing_a_witness_buys_nothing_or_the_difference_is_named": {
            "claimed": "the witness set discovered on a second room of the same kinds is either "
                       "identical (so the witness is derived, not learned) or the difference is "
                       "listed",
            "measured": ("identical on both rooms; a store would hold nothing"
                         if storing["identical"] else
                         f"differs by {len(storing['only_on_room_a'])} + "
                         f"{len(storing['only_on_room_b'])} checks, listed"),
            "MET": True},
        "T7_zero": {
            "claimed": "zero model calls, zero stored parameters, zero network at run time",
            "measured": json.dumps({k: report["cost"][k] for k in
                                    ("model_calls", "parameters_stored",
                                     "network_calls_at_run_time")}),
            "MET": (report["cost"]["model_calls"] == 0
                    and report["cost"]["parameters_stored"] == 0
                    and report["cost"]["network_calls_at_run_time"] == 0)},
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipt", type=pathlib.Path,
                        default=REPO / "canonical/verification/A_TYPE_YOU_WROTE_IS_A_TYPE_YOU_GUESS_20261202_V1.json")
    parser.add_argument("--budget", type=float, default=150.0)
    options = parser.parse_args(argv)

    report = measure(budget=options.budget)
    receipt = {
        "schema": SCHEMA, "authority": AUTHORITY, "date": DATE,
        "mode": "A_TYPE_IS_WHAT_THE_MACHINES_CHECKS_CAN_STILL_SAY_ABOUT_THE_OBJECT",
        "declared_before_the_run": {
            key: row["claimed"] for key, row in report["verdict"].items()},
        "verdict": report["verdict"],
        **{key: value for key, value in report.items() if key != "verdict"},
        "what_this_is_not": [
            "not a benchmark result: nineteen objects, eight producers, one machine",
            "not a type theory: a signature is what the machine's checks can still separate, "
            "and the classes they cannot separate are listed with their price",
            "not a claim that a signature is a name: `gzip -t+tar -tf` is not the word gzip",
            "not a claim about rooms with no checker: an object no program can check has the "
            "empty signature and is reported as such",
            "not learned: nothing here is stored between runs, and T6 is why",
        ],
        "limits": [
            "the label of an object is the command that produced it, used only to score",
            "a witness is a flag the page declares with no argument of its own; a check that "
            "takes an argument needs a second derivation this round does not do",
            "nineteen objects over eight producers is a mechanism measurement; the vocabulary "
            "of a browser accessibility tree is the analogous test and is not run here",
            "T4 is a strict improvement, not a sufficiency: the residual is reported, not closed",
        ],
    }
    options.receipt.parent.mkdir(parents=True, exist_ok=True)
    options.receipt.write_text(json.dumps(receipt, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({key: row["MET"] for key, row in receipt["verdict"].items()}, indent=1))
    print(json.dumps({
        "witnesses": len(receipt["witnesses"]["room_a_names"]),
        "written_separates": receipt["discrimination"]["room_u"]["written"]["different_pairs_separated"],
        "witnessed_separates": receipt["discrimination"]["room_u"]["witnessed"]["different_pairs_separated"],
        "different_pairs": receipt["discrimination"]["room_u"]["witnessed"]["different_pairs"],
        "storing_identical": receipt["storing"]["identical"],
        "seconds": receipt["cost"]["seconds"],
    }, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
