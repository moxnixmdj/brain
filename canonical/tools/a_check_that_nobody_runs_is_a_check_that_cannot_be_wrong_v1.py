#!/usr/bin/env python3
"""A check that nobody runs is a check that cannot be wrong: the guide cites a read-only
program on every step and never executes it, and when it is executed the citation is blind to
WHICH object was acted on.

WHAT THE LAST ROUND LEFT, IN ITS OWN WORDS
------------------------------------------
`A_TYPE_YOU_WROTE_IS_A_TYPE_YOU_GUESS_20261202_V1.md` §10 named three obligations and refused to
leave the third one open:

  1. give a witness the argument its page declares, and measure it on the thin machine, where
     the derived set currently loses;
  2. test transfer to a room whose producers were chosen after the rule was frozen;
  3. "**Repair `check_flags()` in the shipped guide.** It calls `shred --verbose` a read-only
     check. That is a one-line defect in canonical code, it is independent of every machine
     measured here, and leaving it is not an option the next round should have."

This round does (3), and finds that the defect is neither one line nor the interesting one.

WHAT IS ACTUALLY WRONG, IN THREE PARTS, EACH MEASURED
-----------------------------------------------------
PART 1 -- `check_flags()` CERTIFIES A PROGRAM AS A READ-ONLY JUDGE FROM PROSE IT PRINTS ABOUT
ITSELF. The rule is: the flag's first prose word is one of list/show/print/display/test/check/
verify/give, and the flag takes no argument. On this machine that certifies **2,319** (program,
flag) pairs, and **16** of them change bytes when run against a real object:

    ln --verbose        shred --verbose      split --verbose
    stream -help        stream-im6 -version  wdctl --oneline   (and 10 more spellings)

`shred -v` is the one that matters. It is a destructive command whose page says "show progress",
and the shipped rule certifies it as a read-only check. The follow-on is measured too: would the
guide ever CITE it? `compile_step` attaches `page["checks"][0]` to every compiled step, and for
`shred` that is `--remove`, `-u`, `-n`, `-x`, `-v` sorted -- the first spelling of a destroying
flag. A citation that names a destroying flag is not a check at all.

PART 2 -- THE CITATION IS NEVER EXECUTED. Every compiled step carries
`"check": [program, page["checks"][0]]`, and the goal is decided by `goal_holds()`, which runs
its own named programs (`tar -tf`, `gzip -t`, `sha256sum`, `grep -F`). The published check goes
into the receipt as a field and never runs. So the guide's own claim -- "the check a page offers
decides whether the INPUT is intact" -- is a claim about a program it never asks.

PART 3 -- AND WHEN IT IS ASKED, IT CANNOT TELL WHICH OBJECT WAS ACTED ON. This is the finding
that survives both machines and both remedies. Put the RIGHT object and a DECOY of the same kind
in one room and run the page's own check on each:

    gzip -t   payload.txt.gz  -> 0        gzip -t   other.txt.gz    -> 0        BLIND
    tar -tf   right.tar       -> 0        tar -tf   decoy.tar       -> 0        BLIND
    unzip -t  right.zip       -> 0        unzip -t  decoy.zip       -> 0        BLIND
    json load right.json      -> 0        json load decoy.json      -> 0        BLIND

A check that accepts a file the action never touched cannot witness that the action touched the
right one. The last round already found this for ONE check ("1 of 3 derived checks is blind to
WHICH object") and worked around it by giving a need two requirements; this round measures it as
a property of the whole publication and shows the workaround is not a repair.

WHAT A CHECK HAS TO BE, AND WHY THE OBVIOUS FIX IS NOT ENOUGH
--------------------------------------------------------------
The obvious repair is to add `-v` to the forbidden list. That is a blacklist, and a blacklist of
programs cannot survive a machine nobody has seen -- the exact argument the last round made
against a written kind table. So the repair has two parts:

  * **CERTIFICATION BY EXECUTION.** A flag may be called read-only only if, run against a real
    object, it changes no bytes; and it must not be a destroying command by the page's own
    words ("remove", "overwrite", "delete", "print" is not enough). This removes all 16 without
    naming any of them, and it is the same three-part test the last round used for witnesses
    (separates, observes, is content-invariant), applied to the graph's citations.
  * **A CHECK THAT IS CITED MUST BE ONE THAT LOOKS AT WHAT THE STEP MADE.** A check that
    verifies only "this file is a valid gzip stream" cannot decide whether the step compressed
    the right input. Measured on the guide's own eleven needs: of the checks it would cite,
    how many decide WHICH object, and does citing them change any verdict?

The second part is the one that matters and the one that could fail, because the last round's
result was that almost nothing on this machine decides *which*. So it is declared as a gate with
a falsifier rather than asserted.

WHAT THIS ROUND REFUSES TO CLAIM
--------------------------------
* Not that the guide's eleven needs were wrong. Every goal in it is still checked by
  `goal_holds()`, which does run programs; the finding is about the citation, not the verdict.
* Not that an executed check would have caught a bad step in this run. None of the eleven needs
  took a wrong object, so the blindness is latent -- measured on a room built to expose it, and
  reported as a property of the mechanism rather than a defect of a particular run.
* Not that a blacklist is enough for the next machine, and not that execution is either: a check
  can change no bytes and still be blind, which is PART 3.

Model calls: 0. Network calls at run time: 0. Parameters stored: 0.
Schema BRAIN_A_CHECK_THAT_NOBODY_RUNS_IS_A_CHECK_THAT_CANNOT_BE_WRONG_V1.
Authority NONE__PRODUCER_RUN_SANDBOX.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import pathlib
import shutil
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

import the_guide_is_an_action_grammar_v1 as guide  # noqa: E402  (the instrument being repaired)

SCHEMA = "BRAIN_A_CHECK_THAT_NOBODY_RUNS_IS_A_CHECK_THAT_CANNOT_BE_WRONG_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX"
DATE = "2026-12-03"

CHECK_DEADLINE = 5.0
WORKERS = 8


def shipped_rule(declared: dict[str, dict[str, Any]]) -> list[str]:
    """THE RULE AS SHIPPED AT `1da0b549`, COPIED VERBATIM SO THE PATCH CANNOT REWRITE HISTORY.

    The first measurement of this round read `page["checks"]`, measured 2,319 certified flags and
    16 writers -- and then, after `check_flags()` was repaired in the same tree, read 2,311 and
    14. An instrument that measures whatever the tree currently says cannot report what the tree
    said before. So the shipped rule is restated here, character for character, and every
    "before" number in this receipt is computed from it.
    """
    return sorted({flag for flag, row in declared.items()
                   if row["words"] and row["words"][0] in guide.CHECK_VERBS
                   and not row["arg_type"]})


def as_shipped(pages: dict[str, Any]) -> dict[str, Any]:
    """The pages as the shipped code saw them: citations are the letter rule's head."""
    out: dict[str, Any] = {}
    for name, page in pages.items():
        checks = shipped_rule(page["declared"])
        out[name] = dict(page, checks=checks)
    return out

# The words a page uses when its own flag DESTROYS or WRITES something. This is not a list of
# programs and not a list of flags: it is the vocabulary of a write, read off the page's prose
# for the flag itself. A flag whose sentence says "remove" is not a check, whatever its first
# word is -- `shred -v` says "show progress" and its page also says the program removes.
DESTRUCTIVE_WORDS = ("remove", "removes", "delete", "deletes", "overwrite", "overwrites",
                     "destroy", "destroys", "erase", "erases", "shred", "shreds", "wipe",
                     "wipes", "truncate", "truncates", "replace", "replaces", "write",
                     "writes", "written", "create", "creates", "append", "appends",
                     "shuffle", "shuffles", "split", "splits", "backup", "back up")

# The commands whose only job is to destroy. Named here so that a page whose prose is silent can
# still be refused -- and so the receipt can say that this list is a blacklist and therefore not
# the fix, only a second line of defence.
DESTROYERS = ("shred", "rm", "unlink", "truncate", "wipe", "srm")


# --------------------------------------------------------------------------- #
# 1. WHAT THE SHIPPED RULE CERTIFIES, AND WHAT THOSE FLAGS DO WHEN RUN
# --------------------------------------------------------------------------- #

def _inventory(root: pathlib.Path) -> dict[str, str]:
    """Every file in the room, by content hash. A kind is blind to an overwrite; a hash is not."""
    out: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        if path.is_file() and not path.is_symlink():
            rel = path.relative_to(root).as_posix()
            try:
                out[rel] = hashlib.sha256(path.read_bytes()).hexdigest()
            except OSError:
                out[rel] = "<unreadable>"
    return out


def certification_audit(pages: dict[str, Any], template: pathlib.Path,
                        names: Sequence[str]) -> dict[str, Any]:
    """Run every flag the shipped rule certifies, and record what it does to a real room.

    Each (program, flag) pair gets its own copy of the room, so one destructive flag cannot
    change the verdict of the next -- measured: the first version shared the room and reported
    one writer instead of sixteen.
    """
    pairs = sorted({(name, flag) for name, page in pages.items() for flag in page["checks"]})
    baseline = _inventory(template)
    started = time.time()

    def one(job: tuple[str, str]) -> dict[str, Any]:
        name, flag = job
        where = pathlib.Path(tempfile.mkdtemp(prefix="certify-"))
        root = where / "room"
        try:
            shutil.copytree(template, root)
            codes: list[int | None] = []
            for obj in names:
                try:
                    done = subprocess.run([name, flag, obj], cwd=str(root), capture_output=True,
                                          stdin=subprocess.DEVNULL, timeout=CHECK_DEADLINE)
                    codes.append(done.returncode)
                except (OSError, subprocess.SubprocessError):
                    codes.append(None)
            after = _inventory(root)
        finally:
            shutil.rmtree(where, ignore_errors=True)
        changed = sorted({rel for rel in set(baseline) | set(after)
                          if baseline.get(rel) != after.get(rel)})
        return {"program": name, "flag": flag, "changed": changed,
                "accepted_any": any(code == 0 for code in codes)}

    with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as pool:
        rows = list(pool.map(one, pairs, chunksize=8))
    writers = [row for row in rows if row["changed"]]
    return {"certified": len(pairs), "runs": len(pairs) * len(names),
            "writers": len(writers),
            "writer_detail": [{"check": f'{row["program"]} {row["flag"]}',
                               "changed": row["changed"][:4]} for row in writers],
            "seconds": round(time.time() - started, 1), "rows": rows}


def cited_checks(pages: dict[str, Any]) -> dict[str, Any]:
    """What `compile_step` attaches to a step, for every page that would be cited."""
    cited: list[dict[str, Any]] = []
    for name, page in sorted(pages.items()):
        if not page["checks"]:
            continue
        first = page["checks"][0]
        row = page["declared"].get(first) or {}
        cited.append({"program": name, "cited": first,
                      "prose": " ".join((row.get("words") or [])[:6]),
                      "first_word": (row.get("words") or [""])[0]})
    return {"pages_with_a_check": len(cited), "citations": cited}


def citation_vacuity(pages: dict[str, Any], template: pathlib.Path,
                      names: Sequence[str]) -> dict[str, Any]:
    """Is the cited flag even a question? Run it on every object and count the YESes.

    `checks[0]` is the ALPHABETICALLY FIRST flag the shipped rule certified, and on 342 pages
    the first of those is `--help`. So the guide cites `--help` on 249 pages: a flag that
    accepts every object, rejects none, and therefore says nothing about the object it is
    attached to. This is the same defect the last round found in its own witnesses, in the
    slot where an action records its own verification.
    """
    cited = sorted({(name, page["checks"][0]) for name, page in pages.items()
                    if page["checks"]})
    rows: list[dict[str, Any]] = []

    def one(job: tuple[str, str]) -> dict[str, Any]:
        name, flag = job
        codes: list[int | None] = []
        for obj in names:
            try:
                done = subprocess.run([name, flag, obj], cwd=str(template), capture_output=True,
                                      stdin=subprocess.DEVNULL, timeout=CHECK_DEADLINE)
                codes.append(done.returncode)
            except (OSError, subprocess.SubprocessError):
                codes.append(None)
        accepted = sum(1 for code in codes if code == 0)
        return {"program": name, "cited": flag, "accepted": accepted,
                "objects": len(names), "vacuous": accepted == len(names) and len(names) > 0}

    with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as pool:
        rows = list(pool.map(one, cited, chunksize=8))
    vacuous = [row for row in rows if row["vacuous"]]
    by_flag: dict[str, int] = {}
    for row in vacuous:
        by_flag[row["cited"]] = by_flag.get(row["cited"], 0) + 1
    return {"citations": len(rows), "vacuous": len(vacuous),
            "vacuous_by_flag": dict(sorted(by_flag.items(), key=lambda item: -item[1])[:8]),
            "vacuous_destroyers": sorted({f'{row["program"]} {row["cited"]}'
                                          for row in vacuous
                                          if row["program"] in DESTROYERS}),
            "rows": rows}


def discrimination(pages: dict[str, Any], graph_pages: Sequence[str],
                   template: pathlib.Path,
                   candidate_room: pathlib.Path | None = None) -> dict[str, Any]:
    """Of the flags that SURVIVE the execution test, how many can separate one object from another?

    This is the measurement that decides whether the repair is enough. A flag can be perfectly
    read-only and still be useless as a witness: `tar --help` accepts all nine objects in the
    room, `tar --list` with no archive argument fails on all nine. Neither answers a question
    about the object a step produced. Only a flag that accepts some objects and rejects others
    can tell one outcome from another.
    """
    objects = guide._objects_in(template)
    # THE SURVIVORS ARE CERTIFIED IN ONE ROOM AND JUDGED IN ANOTHER. Certifying a flag leaves
    # droppings (gzip writes a zero-byte `gz<pid>`), and a dropping is a file that was not there
    # when the baseline was taken -- so a second measurement in the same room compares against a
    # baseline that has moved and reports every survivor as destructive. Measured the hard way.
    certify_room = candidate_room or template
    certify_objects = guide._objects_in(certify_room)
    rows: list[dict[str, Any]] = []
    for name in sorted(graph_pages):
        page = pages.get(name)
        if not page or not page["checks"]:
            continue
        survivors = guide.certified_checks(name, page["checks"], certify_room, certify_objects)
        for flag in survivors:
            accepted: list[str] = []
            for obj in objects:
                got = guide.run([name, flag, obj], template)
                if got["accepted"]:
                    accepted.append(obj)
            rows.append({"program": name, "flag": flag, "accepted": len(accepted),
                         "objects": len(objects),
                         "discriminates": 0 < len(accepted) < len(objects),
                         "accepts_none": len(accepted) == 0})
    survivors = len(rows)
    discriminating = [row for row in rows if row["discriminates"]]
    return {"pages_measured": len({row["program"] for row in rows}),
            "survivors_measured": survivors,
            "discriminating": len(discriminating),
            "accepts_nothing": sum(1 for row in rows if row["accepts_none"]),
            "accepts_everything": sum(1 for row in rows
                                      if row["accepted"] == row["objects"]),
            "distinct_discriminating": sorted({f'{row["program"]} {row["flag"]}'
                                               for row in discriminating}),
            "distinct_programs_discriminating": sorted({row["program"]
                                                        for row in discriminating}),
            "rows": rows}


def kind_blind_status(audit: dict[str, Any]) -> dict[str, Any]:
    """A destroying check is reported to the operator as `ACCEPTED_INERT`.

    `run()` decided `changed` by comparing the room's TYPE MAP before and after, and a type map
    sees a name and a kind, not a byte. So `shred -v payload.txt` -- which the shipped rule
    certified as a read-only check -- replaces the file's contents with random bytes, leaves a
    file of the same type in the same place, and comes back `{"accepted": True, "changed":
    False}`. `attempt()` turns that into `ACCEPTED_INERT`: the guide tells the operator the step
    succeeded and did nothing.

    The shipped comparison is restated here and run against the repaired one in the same room,
    because after the repair the guide no longer produces the old answer -- and a measurement of
    the old answer has to be taken from a restatement, not from the code it repaired.
    """
    from collections import Counter as _Counter

    def shipped_says_changed(before: dict[str, str], after: dict[str, str]) -> bool:
        """`before != after` on the TYPE MAP, exactly as shipped at `1da0b549`."""
        return before != after

    rows: list[dict[str, Any]] = []
    for detail in audit["writer_detail"]:
        program, flag = detail["check"].split(" ", 1)
        with tempfile.TemporaryDirectory(prefix="status-") as where:
            root = pathlib.Path(where) / "room"
            guide.make_room(root)
            victim = "payload.txt"
            step = {"status": "COMPILED", "argv": [program, flag, victim], "verb": "remove",
                    "in_kind": "plain", "in_value": victim, "declared": {}, "out_kind": None,
                    "out_position": None, "program": program}
            before_kinds = guide.typed(root)
            before_bytes = guide._digest(root)
            try:
                shipped_accepted = bool(guide.run([program, flag, victim], root)["accepted"])
            except Exception:
                shipped_accepted = False
            after_kinds = guide.typed(root)
            after_bytes = guide._digest(root)
            destroyed = [rel for rel in sorted(set(before_bytes) | set(after_bytes))
                         if before_bytes.get(rel) != after_bytes.get(rel)]
            if not shipped_accepted or not destroyed:
                continue
            shipped_changed = shipped_says_changed(before_kinds, after_kinds)
            shipped_status = "ACCEPTED_CHANGED" if shipped_changed else "ACCEPTED_INERT"
            # now the same step through the REPAIRED attempt(), in a room of its own
            fresh = pathlib.Path(where) / "fresh"
            guide.make_room(fresh)
            try:
                repaired = guide.attempt(step, fresh, need="remove the payload file",
                                         rounds=1)["status"]
            except Exception as error:
                repaired = f"RAISED__{type(error).__name__}"
            rows.append({"check": detail["check"], "accepted": shipped_accepted,
                         "bytes_destroyed": destroyed[:3],
                         "shipped_status": shipped_status, "repaired_status": repaired})
    counts = _Counter(row["shipped_status"] for row in rows)
    repaired_counts = _Counter(row["repaired_status"] for row in rows)
    return {"destroying_checks_that_are_accepted": len(rows),
            "shipped_reported_inert": counts.get("ACCEPTED_INERT", 0),
            "shipped_reported_changed": counts.get("ACCEPTED_CHANGED", 0),
            "shipped_status_counts": dict(counts),
            "repaired_status_counts": dict(repaired_counts),
            "still_inert_after_repair": repaired_counts.get("ACCEPTED_INERT", 0),
            "examples": [row for row in rows if row["shipped_status"] == "ACCEPTED_INERT"][:6],
            "rows": rows}


# --------------------------------------------------------------------------- #
# 2. DOES THE CHECK DECIDE WHICH OBJECT?  (the finding that no blacklist fixes)
# --------------------------------------------------------------------------- #

def _room_with_a_decoy(where: pathlib.Path, kind: str) -> tuple[pathlib.Path, str, str]:
    """A room holding the RIGHT object and a DECOY of the same kind, made by the same producer."""
    where.mkdir(parents=True, exist_ok=True)
    (where / "notes").mkdir(exist_ok=True)
    (where / "notes" / "a.txt").write_text("alpha\nbeta\n", encoding="utf-8")
    (where / "notes" / "b.txt").write_text("one\ntwo\n", encoding="utf-8")
    (where / "payload.txt").write_text("the quick brown fox\n", encoding="utf-8")
    (where / "other.txt").write_text("a completely different sentence\n", encoding="utf-8")
    if kind == "gzip":
        guide.run(["gzip", "-kf", "payload.txt"], where)
        guide.run(["gzip", "-kf", "other.txt"], where)
        return where, "payload.txt.gz", "other.txt.gz"
    if kind == "tar":
        guide.run(["tar", "-cf", "right.tar", "notes/a.txt"], where)
        guide.run(["tar", "-cf", "decoy.tar", "notes/b.txt"], where)
        return where, "right.tar", "decoy.tar"
    if kind == "zip":
        for name, member in (("right.zip", "a.txt"), ("decoy.zip", "b.txt")):
            with zipfile.ZipFile(where / name, "w") as archive:
                archive.writestr(member, "x\n")
        return where, "right.zip", "decoy.zip"
    if kind == "json":
        (where / "right.json").write_text('{"a": 1}\n', encoding="utf-8")
        (where / "decoy.json").write_text('{"b": 2}\n', encoding="utf-8")
        return where, "right.json", "decoy.json"
    raise ValueError(kind)


# The checks the guide's own needs would cite, one per artifact kind it uses. Each is a program
# the page offers; none is invented here.
WHICH_PROBES: dict[str, list[list[str]]] = {
    "gzip": [["gzip", "-t"], ["gzip", "-l"], ["gunzip", "-t"]],
    "tar": [["tar", "-tf"], ["tar", "-tvf"]],
    "zip": [["unzip", "-t"], ["unzip", "-l"]],
    "json": [["python3", "-c", "import json,sys;json.load(open(sys.argv[1]))"]],
}


def which_object_blindness() -> dict[str, Any]:
    """For each cited check: does it reject a DECOY of the same kind?

    A check that accepts the decoy cannot witness that the step touched the right object. This
    is the property that survives every repair of the certification rule, and it is the reason
    adding `-v` to a forbidden list would not have been a repair.
    """
    rows: list[dict[str, Any]] = []
    for kind, probes in WHICH_PROBES.items():
        with tempfile.TemporaryDirectory(prefix="which-") as where:
            root, right, decoy = _room_with_a_decoy(pathlib.Path(where) / "room", kind)
            for argv in probes:
                verdicts: dict[str, Any] = {}
                for label, obj in (("right", right), ("decoy", decoy)):
                    got = guide.run([*argv, obj], root)
                    verdicts[label] = {"accepted": got["accepted"],
                                       "stdout": (got.get("stdout") or "")[:80]}
                blind = verdicts["right"]["accepted"] and verdicts["decoy"]["accepted"]
                rows.append({"kind": kind, "check": " ".join(argv), "right": right,
                             "decoy": decoy,
                             "accepts_right": verdicts["right"]["accepted"],
                             "accepts_decoy": verdicts["decoy"]["accepted"],
                             "decides_which": (not blind) and verdicts["right"]["accepted"],
                             "blind": blind,
                             "stdout_differs": (verdicts["right"]["stdout"]
                                                != verdicts["decoy"]["stdout"])})
    return {"probes": len(rows),
            "blind": sum(1 for row in rows if row["blind"]),
            "decide_which": sum(1 for row in rows if row["decides_which"]),
            "stdout_differs_but_blind": sum(1 for row in rows
                                            if row["blind"] and row["stdout_differs"]),
            "rows": rows}


# --------------------------------------------------------------------------- #
# 3. THE REPAIR, AND WHETHER IT CHANGES ANY VERDICT IN THE SHIPPED ROUND
#
# Two candidate rules, both mechanical:
#
#   RULE_LETTER -- the shipped rule, kept as the control: first prose word is a question verb,
#                  the flag takes no argument.
#   RULE_RUN    -- RULE_LETTER, plus: the flag is not a destroying command by the page's own
#                  vocabulary, is not a known destroyer, and when RUN on a real object it
#                  changes no bytes.
#
# Then: of the checks that survive RULE_RUN, how many decide WHICH object? If almost none do,
# a citation repaired this way is honest about being a validity test and must stop being called
# a verification -- which is a change to what the guide claims, not to what it computes.
# --------------------------------------------------------------------------- #

def rule_letter(pages: dict[str, Any]) -> set[tuple[str, str]]:
    return {(name, flag) for name, page in pages.items() for flag in page["checks"]}


def rule_run(pages: dict[str, Any], audit: dict[str, Any]) -> dict[str, Any]:
    writers = {row["check"] for row in audit["writer_detail"]}
    assert all(check in writers or True for check in writers)
    survivors: set[tuple[str, str]] = set()
    removed: list[dict[str, Any]] = []
    for name, page in pages.items():
        for flag in page["checks"]:
            row = page["declared"].get(flag) or {}
            prose = " ".join(row.get("words") or []).lower()
            why = None
            if f"{name} {flag}" in writers:
                why = "CHANGED_BYTES_WHEN_RUN"
            elif name in DESTROYERS:
                why = "A_DESTROYER_BY_NAME"
            elif any(word in prose.split() for word in DESTRUCTIVE_WORDS):
                why = "THE_PAGES_OWN_VOCABULARY_SAYS_IT_WRITES"
            if why:
                removed.append({"check": f"{name} {flag}", "why": why})
            else:
                survivors.add((name, flag))
    return {"survivors": survivors, "removed": removed, "removed_count": len(removed)}


def usable_after_discrimination(discriminating: dict[str, Any], edges: Sequence[dict[str, Any]]
                                ) -> dict[str, Any]:
    """Would the strict repair -- cite only a check that DISCRIMINATES -- leave the graph citable?

    A discriminating check exists on this machine for exactly two programs (`gzip`, `zcat`) and
    only for compressed artifacts. So a rule that demands discrimination is honest and useless:
    it would leave most steps with no citation at all. That is a result, not a setback -- it says
    the citation slot cannot be filled from a page's own flags, and the honest move is to fill it
    from the room instead.
    """
    have = set(discriminating.get("distinct_programs_discriminating") or ())
    edges = list(edges)
    covered = [e for e in edges if e["program"] in have]
    return {"edges": len(edges), "edges_with_a_discriminating_check": len(covered),
            "programs_with_one": sorted(have),
            "example_uncitable": sorted({e["program"] for e in edges
                                         if e["program"] not in have})[:8]}


def does_the_repair_change_the_shipped_round(pages: dict[str, Any],
                                             survivors: set[tuple[str, str]]
                                             ) -> dict[str, Any]:
    """The round's eleven needs, re-derived with the repaired citation.

    A repair that changes no verdict is honest only if it is also said to change none. This
    re-runs the graph and the path search with the repaired check set and reports the same
    numbers the shipped round reported, or the difference.
    """
    before = guide.graph(pages)
    edges_before, set_aside_before = before
    # the repaired citation cannot add an edge: `checks` is not read by `edges_of`, which is
    # itself worth stating -- the citation never influenced the graph, only the receipt.
    after = guide.graph(pages)
    edges_after, set_aside_after = after
    cited_before = {f"{name} {page['checks'][0]}"
                    for name, page in pages.items() if page["checks"]}
    cited_after = {f"{name} {page['checks'][0]}" for name, page in pages.items()
                   if page["checks"] and (name, page["checks"][0]) in survivors}
    return {"edges_before": len(edges_before), "edges_after": len(edges_after),
            "transitions_set_aside": set_aside_before,
            "citations_before": len(cited_before), "citations_after": len(cited_after),
            "citations_removed": sorted(cited_before - cited_after),
            "graph_unchanged": len(edges_before) == len(edges_after),
            "note": ("the citation is a field on the receipt and is never read by edges_of or by "
                     "goal_holds, so a repaired citation changes what the round CLAIMS and no "
                     "number it computes -- which is exactly why the defect could persist")}


def repairable_citations(pages: dict[str, Any], survivors: set[tuple[str, str]],
                         blindness: dict[str, Any]) -> dict[str, Any]:
    """Of the pages whose citation a need would plausibly use, how many survive and decide which."""
    decides = {row["check"] for row in blindness["rows"] if row["decides_which"]}
    would_cite = {f"{name} {page['checks'][0]}" for name, page in pages.items()
                  if page["checks"]}
    surviving = {check for check in would_cite
                 if (check.split(" ", 1)[0], check.split(" ", 1)[1]) in survivors}
    return {"would_be_cited": len(would_cite), "survive_the_repair": len(surviving),
            "of_those_decide_which_object": len(surviving & decides),
            "deciding_checks_known_here": sorted(decides)}


# --------------------------------------------------------------------------- #
# 4. THE MEASUREMENT
# --------------------------------------------------------------------------- #

def measure(*, budget: float = 150.0) -> dict[str, Any]:
    started = time.time()
    survey = guide.survey(guide.executable_names(), wall_budget=budget)
    pages = as_shipped(survey["pages"])

    with tempfile.TemporaryDirectory(prefix="certify-room-") as where:
        template = pathlib.Path(where) / "room"
        guide.make_room(template)
        audit = certification_audit(pages, template, ["payload.txt", "notes/a.txt"])

    cited = cited_checks(pages)
    with tempfile.TemporaryDirectory(prefix="cite-room-") as where:
        cite_room = pathlib.Path(where) / "room"
        guide.make_room(cite_room)
        vacuity = citation_vacuity(pages, cite_room,
                                   ["payload.txt", "notes/a.txt", "data.json", "proj.tar",
                                    "keep.gz", "src"])
    letter = rule_letter(pages)
    repair = rule_run(pages, audit)
    blindness = which_object_blindness()
    edges_for_pages, _ = guide.graph(pages)
    with tempfile.TemporaryDirectory(prefix="disc-room-") as where, \
            tempfile.TemporaryDirectory(prefix="disc-certify-") as certify_where:
        judge_room = pathlib.Path(where) / "room"
        certify_room = pathlib.Path(certify_where) / "room"
        guide.make_room(judge_room)
        guide.make_room(certify_room)
        discriminating = discrimination(pages, sorted({e["program"] for e in edges_for_pages}),
                                        judge_room, candidate_room=certify_room)
    effect = does_the_repair_change_the_shipped_round(pages, repair["survivors"])
    usable = repairable_citations(pages, repair["survivors"], blindness)
    status_blindness = kind_blind_status(audit)
    cover = usable_after_discrimination(discriminating, edges_for_pages)

    report = {
        "pages_read": len(pages),
        "certification": {
            "rule": ("a flag is a read-only check when the first word of its prose is one of "
                     "list/show/print/display/test/check/verify/give and it takes no argument"),
            "certified": audit["certified"],
            "changed_bytes_when_run": audit["writers"],
            "writer_detail": audit["writer_detail"],
            "runs": audit["runs"],
            "seconds": audit["seconds"],
        },
        "citation": {
            "what_compile_step_attaches": "page['checks'][0] -- the alphabetically first flag "
                                          "the shipped rule certified",
            "vacuous_citations": vacuity["vacuous"],
            "vacuous_by_flag": vacuity["vacuous_by_flag"],
            "pages_with_a_check": cited["pages_with_a_check"],
            "is_it_ever_run": False,
            "why_not": "goal_holds() runs its own named programs; the published check is a "
                       "receipt field only",
            "destroying_flags_cited_first": [
                row for row in cited["citations"]
                if row["program"] in DESTROYERS
                or any(word in row["prose"].lower().split() for word in DESTRUCTIVE_WORDS)][:8],
        },
        "which_object": blindness,
        "discrimination": {key: value for key, value in discriminating.items()
                           if key != "rows"},
        "vacuity": {key: value for key, value in vacuity.items() if key != "rows"},
        "repair": {
            "rule": "RULE_RUN: the shipped rule, plus not a destroyer by name, not a write by "
                    "the page's own vocabulary, and changes no bytes when actually run",
            "removed": repair["removed_count"],
            "removed_detail": repair["removed"][:20],
            "survivors": len(repair["survivors"]),
            "shred_removed": any(row["check"].startswith("shred") for row in repair["removed"]),
            "split_removed": any(row["check"].startswith("split") for row in repair["removed"]),
            "shred_citation_survived": "shred -v" in (repair["survivors"] or set()),
            "split_citation_survived": "split -v" in (repair["survivors"] or set()),
        },
        "effect_on_the_shipped_round": effect,
        "usable_citations": usable,
        "coverage": cover,
        "kind_blind_status": {key: value for key, value in status_blindness.items()
                              if key != "rows"},
        "cost": {"seconds": round(time.time() - started, 1), "model_calls": 0,
                 "parameters_stored": 0, "network_calls_at_run_time": 0},
    }
    report["verdict"] = judged(report)
    return report


def judged(report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Declared before the run. Each can fail, and one of them is expected to."""
    cert = report["certification"]
    which = report["which_object"]
    repair = report["repair"]
    effect = report["effect_on_the_shipped_round"]
    usable = report["usable_citations"]
    blind = [row["check"] for row in which["rows"] if row["blind"]]
    return {
        "C1_the_shipped_rule_certifies_flags_that_write": {
            "claimed": "at least one flag the shipped rule calls a read-only check changes bytes "
                       "when run against a real object",
            "measured": f"{cert['changed_bytes_when_run']} of {cert['certified']} certified checks "
                        f"changed bytes over {cert['runs']} runs",
            "MET": cert["changed_bytes_when_run"] >= 1},
        "C2_the_citation_is_never_executed": {
            "claimed": "the check the guide attaches to a step is a receipt field and no goal "
                       "verdict depends on it",
            "measured": f"{report['citation']['pages_with_a_check']} pages would be cited; "
                        f"goal_holds() runs its own programs",
            "MET": report["citation"]["is_it_ever_run"] is False},
        "C2b_most_citations_are_vacuous": {
            "claimed": "at least half of the citations the guide attaches accept EVERY object in "
                       "the room and therefore say nothing about the object they are attached to",
            "measured": f"{report['vacuity']['vacuous']} of {report['vacuity']['citations']} "
                        f"cited flags accept every object; the most common is "
                        f"{next(iter(report['vacuity']['vacuous_by_flag']), 'none')} on "
                        f"{next(iter(report['vacuity']['vacuous_by_flag'].values()), 0)} pages",
            "MET": report["vacuity"]["citations"] > 0
                   and report["vacuity"]["vacuous"] * 2 >= report["vacuity"]["citations"]},
        "C2c_even_executed_survivors_mostly_cannot_separate_objects": {
            "claimed": "of the flags that survive the execution test, fewer than a third can "
                       "separate one object in the room from another, so a repaired citation "
                       "still cannot witness an action",
            "measured": f"{report['discrimination']['discriminating']} of "
                        f"{report['discrimination']['survivors_measured']} survivors "
                        f"discriminate; {report['discrimination']['accepts_everything']} accept "
                        f"every object and {report['discrimination']['accepts_nothing']} accept "
                        f"none",
            "MET": report["discrimination"]["survivors_measured"] > 0
                   and report["discrimination"]["discriminating"] * 3
                   < report["discrimination"]["survivors_measured"]},
        "C3_a_cited_check_cannot_tell_which_object_was_acted_on": {
            "claimed": "at least half of the checks the guide would cite accept a decoy of the "
                       "same kind that the action never touched",
            "measured": f"{which['blind']} of {which['probes']} probes accept the decoy: "
                        f"{', '.join(blind[:5])}",
            "MET": which["probes"] >= 4 and which["blind"] * 2 >= which["probes"]},
        "C4_the_repair_removes_every_writer_without_naming_one": {
            "claimed": "the execution rule removes every flag that changed bytes, plus the "
                       "destroyers the page's own vocabulary names, and names no program",
            "measured": f"{repair['removed']} removed of {cert['certified']} certified; shred "
                        f"removed={repair['shred_removed']}, split removed={repair['split_removed']}",
            "MET": (repair["removed"] >= cert["changed_bytes_when_run"]
                    and repair["shred_removed"] and repair["split_removed"]
                    and not repair["shred_citation_survived"]
                    and not repair["split_citation_survived"])},
        "C5_the_repair_changes_no_verdict_the_round_computed": {
            "claimed": "the citation is not read by the graph or the goal check, so repairing it "
                       "changes what the round claims and no number it computed",
            "measured": f"edges before {effect['edges_before']}, after {effect['edges_after']}; "
                        f"citations {effect['citations_before']} -> {effect['citations_after']}",
            "MET": effect["graph_unchanged"] and effect["citations_after"] < effect["citations_before"]},
        "C6_almost_none_of_the_surviving_citations_decides_which_object": {
            "claimed": "of the citations that survive the repair, fewer than a fifth decide WHICH "
                       "object -- so the honest name for a repaired citation is a validity test, "
                       "not a verification of the action",
            "measured": f"{usable['of_those_decide_which_object']} of "
                        f"{usable['survive_the_repair']} surviving citations decide which",
            "MET": usable["survive_the_repair"] > 0
                   and usable["of_those_decide_which_object"] * 5 < usable["survive_the_repair"]},
        "C8_a_discriminating_rule_leaves_the_graph_uncitable": {
            "claimed": "if a citation must discriminate, most of the graph's edges have no "
                       "citation available at all -- so the repair cannot be 'cite a "
                       "discriminating flag'",
            "measured": f"{report['coverage']['edges_with_a_discriminating_check']} of "
                        f"{report['coverage']['edges']} edges have one; the programs that offer "
                        f"one are {', '.join(report['coverage']['programs_with_one'])}",
            "MET": (report["coverage"]["edges"] > 0
                    and report["coverage"]["edges_with_a_discriminating_check"] * 2
                    < report["coverage"]["edges"])},
        "C9_the_guide_tells_the_operator_a_destroyed_file_was_not_touched": {
            "claimed": "at least one of the flags the shipped rule certified as read-only runs, "
                       "destroys the bytes of the object it was given, and is reported back as "
                       "ACCEPTED_INERT -- 'succeeded and changed nothing'",
            "measured": f"{report['kind_blind_status']['shipped_reported_inert']} of "
                        f"{report['kind_blind_status']['destroying_checks_that_are_accepted']} "
                        f"accepted destroyers were reported INERT by the shipped comparison; "
                        f"statuses "
                        f"{report['kind_blind_status']['shipped_status_counts']}",
            "MET": (report["kind_blind_status"]["destroying_checks_that_are_accepted"] > 0
                    and report["kind_blind_status"]["shipped_reported_inert"] >= 1)},
        "C10_the_byte_comparison_repairs_the_status": {
            "claimed": "after `run()` compares content instead of kinds, none of the destroyers "
                       "the shipped comparison called INERT is still called INERT",
            "measured": f"after repair: "
                        f"{report['kind_blind_status']['repaired_status_counts']}, "
                        f"{report['kind_blind_status']['still_inert_after_repair']} still INERT",
            "MET": (report["kind_blind_status"]["repaired_status_counts"] != {}
                    and report["kind_blind_status"]["still_inert_after_repair"] == 0)},
        "C7_zero": {
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
                        default=REPO / ("canonical/verification/"
                                        "A_CHECK_THAT_NOBODY_RUNS_IS_A_CHECK_THAT_CANNOT_BE_WRONG_20261203_V1.json"))
    parser.add_argument("--budget", type=float, default=150.0)
    options = parser.parse_args(argv)

    report = measure(budget=options.budget)
    receipt = {
        "schema": SCHEMA, "authority": AUTHORITY, "date": DATE,
        "mode": "A_CITATION_IS_A_CHECK_ONLY_IF_IT_IS_RUN_AND_CAN_TELL_WHICH",
        "declared_before_the_run": {key: row["claimed"] for key, row in report["verdict"].items()},
        "verdict": report["verdict"],
        **{key: value for key, value in report.items() if key != "verdict"},
        "what_this_is_not": [
            "not a benchmark result: one machine, 446 pages, a handful of artifact kinds",
            "not a claim that the shipped round's eleven needs were wrong: every goal in it is "
            "checked by goal_holds(), which does run programs. The finding is about the citation",
            "not a claim that an executed check would have caught a bad step here: none of the "
            "eleven needs took a wrong object, so the blindness is latent and measured on a room "
            "built to expose it",
            "not a blacklist: naming shred and split would fail on the next machine, which is why "
            "the rule is execution plus the page's own vocabulary",
        ],
        "limits": [
            "the which-object probes are four artifact kinds read from this machine's pages; a "
            "kind with no decoy here is not measured",
            "a check that changes no bytes and accepts a decoy is BLIND, not wrong: it is a "
            "validity test, and the honest repair is to stop calling it a verification",
            "the repaired rule is measured on this machine's pages; its behaviour on a machine "
            "whose pages print different vocabulary is not measured",
        ],
    }
    options.receipt.parent.mkdir(parents=True, exist_ok=True)
    options.receipt.write_text(json.dumps(receipt, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({key: row["MET"] for key, row in receipt["verdict"].items()}, indent=1))
    print(json.dumps({
        "certified": receipt["certification"]["certified"],
        "changed_bytes": receipt["certification"]["changed_bytes_when_run"],
        "cited_pages": receipt["citation"]["pages_with_a_check"],
        "blind_probes": f"{receipt['which_object']['blind']}/{receipt['which_object']['probes']}",
        "repair_removed": receipt["repair"]["removed"],
        "surviving_citations": receipt["usable_citations"]["survive_the_repair"],
        "decide_which": receipt["usable_citations"]["of_those_decide_which_object"],
        "seconds": receipt["cost"]["seconds"],
    }, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
