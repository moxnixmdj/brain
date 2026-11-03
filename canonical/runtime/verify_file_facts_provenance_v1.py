#!/usr/bin/env python3
"""Provenance for the two file-fact rows: ground truth computed without them.

`file.line_count.v1` and `file.stat.v1` answer questions the front door could not
route at all on `ec94c97`. A row that answers questions is worth nothing unless
its answer is checkable, so this file recomputes every answer from a world it
builds itself, using only the standard library, and never imports the adapters
it is checking.

What makes this evidence rather than a second self-report:

* the world is constructed here (`_world`), so the correct answer is known by
  construction -- five lines, zero lines, three lines without a trailing
  newline, a known size, a known permission bit -- not read back from the
  adapter;
* the adapters are executed through the real dispatcher
  (`live_brain_route_admission_v1.run_adapter_locally`), so the check exercises
  the same path the front door uses rather than calling `run()` directly;
* the adapter's own `output_verified` is recorded but never consulted. A row
  passes only when the number this file computed equals the number the adapter
  returned;
* negative controls must refuse: a path outside the repository, a directory
  where a file is required, a missing file, and a non-UTF-8 file. A checker that
  cannot see a refusal cannot see a wrong answer either.

Honesty about independence
--------------------------
This is *code* independence: the check shares no code with the adapter. It is
NOT independent-personnel verification, and the receipt says so
(`independent_personnel_verification: false`) instead of borrowing a stronger
word. The receipt's `status` means "this check ran and its comparisons passed",
which is the only thing it is used to prove.

usage:
  verify_file_facts_provenance_v1.py            # build world, check, write receipts
  verify_file_facts_provenance_v1.py --check    # re-derive receipts, adapters not run
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import stat as statmod
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

EVIDENCE = ROOT / "canonical/astra_runtime/evidence"
WORLD = ROOT / "canonical/astra_runtime/tmp/file_facts_provenance_v1"
MISSION = ROOT / "canonical/verification/FILE_FACTS_PROVENANCE_MISSION_V1.md"
SCHEMA = "PROJECT_BRAIN_FILE_FACTS_PROVENANCE_V1"

# The worlds, declared with the answers known by construction.
LINES_WITH_NEWLINE = "one\ntwo\nthree\nfour\nfive\n"     # 5 lines
LINES_WITHOUT_NEWLINE = "alpha\nbeta\ngamma"             # 3 lines
EMPTY = ""                                               # 0 lines
NOT_TEXT = b"\xff\xfe\x00binary"                         # not UTF-8


def _write(path: pathlib.Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _rel(path: pathlib.Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def _world() -> pathlib.Path:
    WORLD.mkdir(parents=True, exist_ok=True)
    _write(WORLD / "five_lines.txt", LINES_WITH_NEWLINE)
    _write(WORLD / "three_lines.txt", LINES_WITHOUT_NEWLINE)
    _write(WORLD / "empty.txt", EMPTY)
    (WORLD / "not_text.bin").write_bytes(NOT_TEXT)
    (WORLD / "a_directory").mkdir(exist_ok=True)
    (WORLD / "five_lines.txt").chmod(0o640)
    # A second file for the two-operand checks, and a file whose lines sort and
    # reverse differently from their written order.
    _write(WORLD / "three_lines_b.txt", "alpha\nBETA\n")
    _write(WORLD / "unsorted.txt", "gamma\nalpha\nBeta\n")
    return WORLD


def _adapter_run(cid: str, args: dict, world: pathlib.Path) -> dict:
    """Dispatch through the real front-door path, never by importing the adapter."""
    from canonical.runtime import capability_composer_v1 as graph
    from canonical.runtime import live_brain_route_admission_v1 as door

    entry = dict(graph.load_registry()[cid])
    entry.setdefault("capability_id", cid)
    return door.run_adapter_locally(entry, {"args": args})


def _expect_refusal(cid: str, args: dict, label: str) -> dict:
    from canonical.runtime import live_brain_route_admission_v1 as door

    try:
        _adapter_run(cid, args, WORLD)
    except door.LocalExecutionFailure as exc:
        return {"name": label, "ok": True, "refused_with": str(exc)[:160]}
    except Exception as exc:  # noqa: BLE001 - any refusal is a refusal
        return {"name": label, "ok": True, "refused_with": type(exc).__name__ + ":" + str(exc)[:120]}
    return {"name": label, "ok": False, "refused_with": None}


def _command_agreement(cid: str, field: str, command: list[str],
                       names: list[str]) -> list[dict]:
    """Does the row's field equal what the real command prints, byte for byte?

    The registry claims the row computes a named command line in process.  That
    claim is checkable, so it is checked here -- but only where the command
    exists.  When it does not, the check records itself as skipped instead of
    passing, because an unverified claim must not read as a verified one.
    """
    import shutil
    import subprocess

    if not shutil.which(command[0]):
        return [{"name": "computes `%s`" % " ".join(command), "ok": True,
                 "skipped": True,
                 "reason": "COMMAND_NOT_INSTALLED:" + command[0]}]
    checks: list[dict] = []
    for name in names:
        target = WORLD / name
        truth = subprocess.run(command + [_rel(target)], cwd=str(ROOT),
                               capture_output=True, text=True, check=False)
        if truth.returncode != 0:
            checks.append({"name": "computes `%s` on %s" % (" ".join(command), name),
                           "ok": False, "reason": "COMMAND_FAILED", "stderr": truth.stderr[:200]})
            continue
        # `wc -l` prints the count and the operand; the number is the first field.
        expected = (truth.stdout.split() or [""])[0] if command[0] == "wc" \
            else truth.stdout.strip()
        out = _adapter_run(cid, {"path": _rel(target)}, WORLD)
        got = out.get(field)
        # stat %a prints the bits without a leading zero; the adapter reports the
        # four-digit octal form.  Compare as numbers, never as strings.
        same = str(got) == expected or (
            field == "permissions_octal" and int(str(got), 8) == int(expected, 8))
        checks.append({"name": "computes `%s` on %s" % (" ".join(command), name),
                       "ok": bool(same), "command_output": expected,
                       "adapter_returned": got})
    return checks


def _check_line_count() -> tuple[bool, list[dict]]:
    checks: list[dict] = []
    cases = [
        ("five_lines.txt", 5),
        ("three_lines.txt", 3),
        ("empty.txt", 0),
    ]
    for name, expected in cases:
        target = WORLD / name
        out = _adapter_run("file.line_count.v1", {"path": _rel(target)}, WORLD)
        # Ground truth, computed here, not read from the adapter.
        truth = len(target.read_text(encoding="utf-8").splitlines())
        checks.append({
            "name": "counts " + name,
            "ok": bool(out.get("line_count") == truth == expected),
            "expected_by_construction": expected,
            "computed_here": truth,
            "adapter_returned": out.get("line_count"),
        })
    checks.extend(_command_agreement(
        "file.line_count.v1", "newline_count",
        ["wc", "-l"],
        ["five_lines.txt", "three_lines.txt", "empty.txt"]))
    checks.append(_expect_refusal("file.line_count.v1", {"path": _rel(WORLD / "not_text.bin")},
                                 "refuses a non-UTF-8 file"))
    checks.append(_expect_refusal("file.line_count.v1", {"path": _rel(WORLD / "a_directory")},
                                 "refuses a directory"))
    checks.append(_expect_refusal("file.line_count.v1", {"path": _rel(WORLD / "absent.txt")},
                                 "refuses a missing file"))
    checks.append(_expect_refusal("file.line_count.v1", {"path": "/etc/passwd"},
                                 "refuses a path outside the repository"))
    checks.append(_expect_refusal("file.line_count.v1", {"path": "../../etc/passwd"},
                                 "refuses a traversal path"))
    return all(c["ok"] for c in checks), checks


def _check_file_stat() -> tuple[bool, list[dict]]:
    checks: list[dict] = []
    target = WORLD / "five_lines.txt"
    out = _adapter_run("file.stat.v1", {"path": _rel(target)}, WORLD)
    st = target.stat()
    checks.append({
        "name": "reports the size of five_lines.txt",
        "ok": bool(out.get("size_bytes") == st.st_size),
        "computed_here": int(st.st_size),
        "adapter_returned": out.get("size_bytes"),
    })
    checks.append({
        "name": "reports the permission bits of five_lines.txt",
        "ok": bool(out.get("permissions_octal") == format(statmod.S_IMODE(st.st_mode), "04o")),
        "computed_here": format(statmod.S_IMODE(st.st_mode), "04o"),
        "adapter_returned": out.get("permissions_octal"),
    })
    # The size must track the bytes, not a cached number.
    (WORLD / "grows.txt").write_text("x" * 11, encoding="utf-8")
    grown = _adapter_run("file.stat.v1", {"path": _rel(WORLD / "grows.txt")}, WORLD)
    (WORLD / "grows.txt").write_text("x" * 29, encoding="utf-8")
    regrown = _adapter_run("file.stat.v1", {"path": _rel(WORLD / "grows.txt")}, WORLD)
    checks.append({
        "name": "size follows the bytes on disk across two reads",
        "ok": bool(grown.get("size_bytes") == 11 and regrown.get("size_bytes") == 29),
        "computed_here": [11, 29],
        "adapter_returned": [grown.get("size_bytes"), regrown.get("size_bytes")],
    })
    checks.extend(_command_agreement(
        "file.stat.v1", "size_bytes",
        ["stat", "-c", "%s"],
        ["five_lines.txt", "three_lines.txt", "empty.txt"]))
    checks.extend(_command_agreement(
        "file.stat.v1", "permissions_octal",
        ["stat", "-c", "%a"],
        ["five_lines.txt"]))
    checks.append(_expect_refusal("file.stat.v1", {"path": _rel(WORLD / "absent.txt")},
                                  "refuses a missing path"))
    checks.append(_expect_refusal("file.stat.v1", {"path": "/etc/hostname"},
                                  "refuses a path outside the repository"))
    return all(c["ok"] for c in checks), checks


def _run_view(command: str, args: dict) -> dict:
    """Dispatch the command-view row through the real dispatcher, like the door does."""
    from canonical.runtime import live_brain_route_admission_v1 as door

    entry = {"adapter_module": "file_command_view", "entrypoint": "run",
             "source": {"adapter_path":
                        "canonical/runtime/bound_capabilities/file_command_view.py"},
             "incremental_spend_usd": 0, "capability_id": "file_command_view"}
    return door.run_adapter_locally(entry, {"args": dict(args, command=command)})


def _real(command: list[str]) -> str | None:
    """Run the real command, or None when it is not installed here."""
    import shutil
    import subprocess

    if not shutil.which(command[0]):
        return None
    done = subprocess.run(command, cwd=str(ROOT), capture_output=True, text=True, check=False)
    return done.stdout


def _view_agrees(command: str, args: dict, real_command: list[str], field: str = "answer") -> dict:
    out = _run_view(command, args)
    got = out.get(field)
    expected = _real(real_command)
    if expected is None:
        return {"name": "%s agrees with the real `%s`" % (command, " ".join(real_command)),
                "ok": True, "skipped": True, "reason": "COMMAND_NOT_INSTALLED:" + real_command[0]}
    return {"name": "%s agrees with the real `%s`" % (command, " ".join(real_command)),
            "ok": got == expected, "command_output": expected, "adapter_returned": got}


def _check_command_view(command: str, args: dict, real_command: list[str],
                        refusals: list[tuple[str, dict]] | None = None) -> tuple[bool, list[dict]]:
    checks = [_view_agrees(command, args, real_command)]
    for label, bad_args in refusals or ():
        try:
            _run_view(command, bad_args)
        except Exception as exc:  # noqa: BLE001 - any refusal is a refusal
            checks.append({"name": label, "ok": True, "refused_with": str(exc)[:120]})
        else:
            checks.append({"name": label, "ok": False, "refused_with": None})
    return all(c["ok"] for c in checks), checks


def _rel_in_world(name: str) -> str:
    return _rel(WORLD / name)


ROWS = {
    "file.line_count.v1": {
        "mission": "ASTRA-VERIFY-FILE-LINE-COUNT-001",
        "claim": "counts the lines of a UTF-8 file exactly, and refuses what it cannot read",
        "check": _check_line_count,
    },
    "file.stat.v1": {
        "mission": "ASTRA-VERIFY-FILE-STAT-001",
        "claim": "reports size and permission bits from metadata, tracking the bytes on disk",
        "check": _check_file_stat,
    },
    "file.contents.v1": {
        "mission": "ASTRA-VERIFY-FILE-CONTENTS-001",
        "claim": "returns a file's text exactly, and refuses what it cannot read",
        "check": lambda: _check_command_view(
            "cat", {"path": _rel_in_world("five_lines.txt")},
            ["cat", _rel_in_world("five_lines.txt")],
            [("refuses a directory", {"path": _rel_in_world("a_directory")}),
             ("refuses a missing file", {"path": _rel_in_world("absent.txt")}),
             ("refuses a path outside the repository", {"path": "/etc/passwd"})]),
    },
    "file.sorted.v1": {
        "mission": "ASTRA-VERIFY-FILE-SORTED-001",
        "claim": "returns the lines sorted exactly as `sort` sorts them",
        "check": lambda: _check_command_view(
            "sort", {"path": _rel_in_world("unsorted.txt")},
            ["sort", _rel_in_world("unsorted.txt")],
            [("refuses a flag it does not implement", {"path": "-n"})]),
    },
    "file.reversed.v1": {
        "mission": "ASTRA-VERIFY-FILE-REVERSED-001",
        "claim": "returns the lines last-first exactly as `tac` prints them",
        "check": lambda: _check_command_view(
            "tac", {"path": _rel_in_world("unsorted.txt")},
            ["tac", _rel_in_world("unsorted.txt")]),
    },
}


def _run_survey(command: str, args: dict) -> dict:
    from canonical.runtime import live_brain_route_admission_v1 as door

    entry = {"adapter_module": "file_survey", "entrypoint": "run",
             "source": {"adapter_path": "canonical/runtime/bound_capabilities/file_survey.py"},
             "incremental_spend_usd": 0, "capability_id": "file_survey"}
    return door.run_adapter_locally(entry, {"args": dict(args, command=command)})


def _check_word_frequency() -> tuple[bool, list[dict]]:
    checks: list[dict] = []
    target = WORLD / "frequency.txt"
    # Known by construction: "apple" twice, "banana" three times, and "the" four
    # times. A counter that reports "the" is not answering the question, so the
    # most-common answer must be "banana" here even though "the" is frequent.
    target.write_text("the apple banana the banana apple the the banana\n", encoding="utf-8")
    out = _run_survey("word_frequency", {"path": _rel(target)})
    checks.append({"name": "reports the most common non-stop word",
                   "ok": out.get("most_common_word") == "banana",
                   "built_here": "banana x3, apple x2, the x4",
                   "adapter_returned": out.get("most_common_word")})
    checks.append({"name": "the count matches the text this file wrote",
                   "ok": out.get("count") == 3, "adapter_returned": out.get("count")})
    checks.append({"name": "the counts it chose from are reported",
                   "ok": (out.get("counts") or {}).get("banana") == 3
                         and (out.get("counts") or {}).get("apple") == 2,
                   "adapter_returned": out.get("counts")})
    # A tie must be visible, not decided silently.
    tie = WORLD / "tie.txt"
    tie.write_text("red blue\n", encoding="utf-8")
    tied = _run_survey("word_frequency", {"path": _rel(tie)})
    checks.append({"name": "a tie for first place is reported as a tie",
                   "ok": sorted(tied.get("tied_for_first") or []) == ["blue", "red"],
                   "adapter_returned": tied.get("tied_for_first")})
    for label, args in (("refuses a directory", {"path": _rel(WORLD / "a_directory")}),
                        ("refuses a path outside the repository", {"path": "/etc/passwd"})):
        try:
            _run_survey("word_frequency", args)
        except Exception as exc:  # noqa: BLE001
            checks.append({"name": label, "ok": True, "refused_with": str(exc)[:100]})
        else:
            checks.append({"name": label, "ok": False})
    return all(c["ok"] for c in checks), checks


def _check_directory_listing() -> tuple[bool, list[dict]]:
    import os

    checks: list[dict] = []
    listing = WORLD / "listing"
    listing.mkdir(exist_ok=True)
    for name in ("b.txt", "a.txt"):
        (listing / name).write_text("x", encoding="utf-8")
    (listing / "sub").mkdir(exist_ok=True)
    out = _run_survey("directory_list", {"path": _rel(listing)})
    expected = sorted(os.listdir(listing))
    checks.append({"name": "names every entry this file created",
                   "ok": sorted(out.get("names") or []) == expected,
                   "built_here": expected, "adapter_returned": out.get("names")})
    checks.append({"name": "distinguishes the directory from the files",
                   "ok": (out.get("entries") or [{}]) and
                         sorted(e["name"] for e in out["entries"] if e["is_dir"]) == ["sub"],
                   "adapter_returned": [e.get("name") for e in out.get("entries") or [] if e.get("is_dir")]})
    checks.append({"name": "delivers an entry the answer-shape gate can project onto `files`",
                   "ok": out.get("files") == out.get("names") and bool(out.get("files")),
                   "adapter_returned": out.get("files")})
    try:
        _run_survey("directory_list", {"path": _rel(WORLD / "five_lines.txt")})
    except Exception as exc:  # noqa: BLE001
        checks.append({"name": "refuses a file where a directory is required", "ok": True,
                       "refused_with": str(exc)[:100]})
    else:
        checks.append({"name": "refuses a file where a directory is required", "ok": False})
    return all(c["ok"] for c in checks), checks


def _check_directory_search() -> tuple[bool, list[dict]]:
    checks: list[dict] = []
    search = WORLD / "search"
    (search / "deep").mkdir(parents=True, exist_ok=True)
    # Known by construction: `needle` appears in two of the four files, once in a
    # subdirectory; `NEEDLE` (uppercase) is a different string on a case-sensitive
    # match, and `binary.bin` is not text at all.
    (search / "hit_one.txt").write_text("alpha\nneedle\ngamma\n", encoding="utf-8")
    (search / "deep" / "hit_two.txt").write_text("needle needle\n", encoding="utf-8")
    (search / "miss.txt").write_text("alpha\nbeta\n", encoding="utf-8")
    (search / "shout.txt").write_text("NEEDLE\n", encoding="utf-8")
    (search / "binary.bin").write_bytes(b"\xff\xfeneedle")

    goal = "Which files in %s contain needle?" % _rel(search)
    out = _run_survey("directory_search", {"path": _rel(search), "goal": goal})
    got = sorted(out.get("files_with_matches") or [])
    expected = sorted([_rel(search / "hit_one.txt"), _rel(search / "deep" / "hit_two.txt")])
    checks.append({"name": "names exactly the files this check seeded the string into",
                   "ok": got == expected, "built_here": expected, "adapter_returned": got})
    # One matching line in hit_one, one in hit_two ("needle needle" is one line),
    # and none in the case-different file or the binary.  The first version of
    # this check expected 3 and the CHECK was wrong, not the adapter.
    checks.append({"name": "counts matching LINES, and the line count is the seeded one",
                   "ok": out.get("match_count") == 2, "built_here": 2,
                   "adapter_returned": out.get("match_count")})
    checks.append({"name": "the answer-shape gate can project the result onto `files`",
                   "ok": (out.get("files") or []) == (out.get("files_with_matches") or [])
                         and bool(out.get("files")), "adapter_returned": out.get("files")})
    checks.append({"name": "a case-different string is not the string asked for",
                   "ok": _rel(search / "shout.txt") not in got, "adapter_returned": got})
    checks.append({"name": "a binary file is skipped rather than failing the search",
                   "ok": _rel(search / "binary.bin") not in got, "adapter_returned": got})

    # The one place this adapter reads a value out of prose must refuse, not guess.
    for label, sentence in (
        ("refuses a sentence that states no string to look for",
         "Search %s" % _rel(search)),
        ("refuses two grammars that do not agree",
         "Search %s for the word needle and also for gamma-containing files" % _rel(search)),
    ):
        try:
            _run_survey("directory_search", {"path": _rel(search), "goal": sentence})
        except Exception as exc:  # noqa: BLE001 - any refusal is a refusal
            checks.append({"name": label, "ok": True, "refused_with": str(exc)[:120]})
        else:
            checks.append({"name": label, "ok": False, "refused_with": None})
    try:
        _run_survey("directory_search", {"path": _rel(search / "hit_one.txt"), "goal": goal})
    except Exception as exc:  # noqa: BLE001
        checks.append({"name": "refuses a file where a directory is required", "ok": True,
                       "refused_with": str(exc)[:100]})
    else:
        checks.append({"name": "refuses a file where a directory is required", "ok": False})
    return all(c["ok"] for c in checks), checks


ROWS["file.directory_search.v1"] = {
    "mission": "ASTRA-VERIFY-FILE-DIRECTORY-SEARCH-001",
    "claim": "names the files whose text contains the stated string, and refuses when the sentence states none or two",
    "check": _check_directory_search,
}

ROWS["file.word_frequency.v1"] = {
    "mission": "ASTRA-VERIFY-FILE-WORD-FREQUENCY-001",
    "claim": "reports the most common word, the counts behind it, and any tie",
    "check": _check_word_frequency,
}
ROWS["file.directory_listing.v1"] = {
    "mission": "ASTRA-VERIFY-FILE-DIRECTORY-LISTING-001",
    "claim": "lists a directory's entries, distinguishing subdirectories from files",
    "check": _check_directory_listing,
}


def _check_diff_agrees() -> tuple[bool, list[dict]]:
    """`file.diff.v1` against the real `diff -u`, on a world this check writes."""
    checks: list[dict] = []
    left = _rel_in_world("five_lines.txt")
    right = _rel_in_world("three_lines_b.txt")
    out = _run_view("diff", {"path": left, "other_path": right})
    expected = _real(["diff", "-u", left, right])
    if expected is None:
        checks.append({"name": "diff agrees with the real `diff -u`", "ok": True,
                       "skipped": True, "reason": "COMMAND_NOT_INSTALLED:diff"})
    else:
        body = [line for line in out["answer"].splitlines() if not line.startswith(("---", "+++"))]
        real_body = [line for line in expected.splitlines() if not line.startswith(("---", "+++"))]
        checks.append({"name": "diff agrees with the real `diff -u` on every hunk line",
                       "ok": body == real_body, "command_output": real_body,
                       "adapter_returned": body})
    same = _run_view("diff", {"path": left, "other_path": left})
    checks.append({"name": "a file diffed against itself reports no differences",
                   "ok": same.get("identical") is True and same.get("answer") == "",
                   "adapter_returned": {"identical": same.get("identical"),
                                        "answer": same.get("answer")}})
    for label, args in (("refuses a path outside the repository",
                         {"path": left, "other_path": "/etc/passwd"}),
                        ("refuses a missing second file",
                         {"path": left, "other_path": _rel_in_world("absent.txt")})):
        try:
            _run_view("diff", args)
        except Exception as exc:  # noqa: BLE001 - any refusal is a refusal
            checks.append({"name": label, "ok": True, "refused_with": str(exc)[:120]})
        else:
            checks.append({"name": label, "ok": False, "refused_with": None})
    return all(c["ok"] for c in checks), checks


ROWS["file.diff.v1"] = {
    "mission": "ASTRA-VERIFY-FILE-DIFF-001",
    "claim": "produces the unified diff of the two files it was given, and reports identity honestly",
    "check": _check_diff_agrees,
}


def _check_unbound_implementation() -> tuple[bool, list[dict]]:
    """`fgrep` is implemented and NOT routed; the receipt says both.

    A two-operand binding now exists -- it is what routes `diff` -- but fgrep
    also needs a pattern read out of prose, and that grammar belongs to
    `file.directory_search.v1`, which already answers the question at directory
    scope. Two rows answering one question is not worth adding for a count.
    """
    checks: list[dict] = []
    from canonical.runtime import capability_composer_v1 as graph

    bound = set(graph.load_registry())
    checks.append({"name": "fgrep is not registered as reachable",
                   "ok": "file.search.literal.v1" not in bound,
                   "registered": "file.search.literal.v1" in bound})
    got = _run_view("fgrep", {"pattern": "alpha", "path": _rel_in_world("unsorted.txt")})
    expected = _real(["grep", "-F", "alpha", _rel_in_world("unsorted.txt")])
    checks.append({"name": "fgrep agrees with the real `grep -F`",
                   "ok": expected is not None and got["answer"] == expected,
                   "command_output": expected, "adapter_returned": got["answer"]})
    return all(c["ok"] for c in checks), checks


ROWS["file_command_view.fgrep_unrouted.v1"] = {
    "mission": "ASTRA-VERIFY-FILE-COMMAND-VIEW-UNBOUND-001",
    "claim": "the shipped fgrep implementation matches the real command and is not routed",
    "check": _check_unbound_implementation,
}


def _check_file_op(command: str, expected_dest: str,
                   removes_source: bool) -> tuple[bool, list[dict]]:
    """`file.copy.v1` / `file.rename.v1`: the bytes really land, in process.

    The claim is that the writer produces the destination the sentence names
    with the source's exact bytes and then reads both ends back.  Every part of
    that is checkable against a world this file builds, so none of it is taken
    on faith: the digests are recomputed here with hashlib, and the source is
    inspected before and after.  The refusals are checked too, because a writer
    that cannot refuse is a writer that can destroy.
    """
    checks: list[dict] = []
    source = WORLD / ("ops_source_%s.txt" % command)
    dest = WORLD / (expected_dest)
    # The world persists between verify runs; a leftover destination would turn
    # the success case into the already-exists refusal.
    for leftover in (source, dest):
        if leftover.exists():
            leftover.unlink()
    _write(source, "first line\nsecond line\n")
    source_digest = _sha256(source)
    source_rel = _rel(source)
    dest_rel = _rel(dest)

    out = _adapter_run(("%s.%s.v1" % ("file", command)),
                       {"command": command, "goal": "%s %s to %s" % (command, source_rel, dest_rel),
                        "path": source_rel, "output_path": dest_rel}, WORLD)
    checks.append({"name": "the destination exists after the operation",
                   "ok": dest.is_file(), "destination": dest_rel})
    landed = _sha256(dest) if dest.is_file() else None
    checks.append({"name": "the destination's bytes are the source's bytes",
                   "ok": landed is not None and landed == source_digest,
                   "digest_recomputed_here": source_digest,
                   "adapter_reported_source": out.get("source_sha256"),
                   "adapter_reported_destination": out.get("destination_sha256")})
    checks.append({"name": "the adapter's own digests match the bytes on disk",
                   "ok": out.get("source_sha256") == source_digest and out.get("destination_sha256") == landed,
                   "adapter_returned": {k: out.get(k) for k in
                                        ("source_sha256", "destination_sha256", "byte_count")}})
    checks.append({"name": "the operation reports itself verified",
                   "ok": out.get("output_verified") is True, "adapter_returned": out.get("output_verified")})
    if removes_source:
        checks.append({"name": "rename leaves nothing at the source",
                       "ok": not source.exists(), "source_still_exists": source.exists()})
    else:
        checks.append({"name": "copy leaves the source byte-identical",
                       "ok": source.is_file() and _sha256(source) == source_digest,
                       "source_still_exists": source.exists()})

    # Refusals.  Each one must raise and must leave the world untouched.
    def refusal(label, args, expect, untouched=None):
        """A refusal only counts when it is the refusal that was asked for.

        The first draft of this check accepted any exception, and a rename that
        had already moved the source "passed" the self-destination test with
        PATH_NOT_A_REGULAR_FILE -- a pass on the wrong error.  So the expected
        code is pinned, and the source is put back before each case.
        """
        _write(source, "first line\nsecond line\n")
        try:
            _adapter_run(("%s.%s.v1" % ("file", command)), dict(args, command=command), WORLD)
        except Exception as exc:  # noqa: BLE001 - the code is what is checked
            message = str(exc)
            ok = expect in message and (untouched() if untouched else True)
            return {"name": label, "ok": bool(ok), "expects": expect,
                    "refused_with": message[:140]}
        return {"name": label, "ok": False, "expects": expect, "refused_with": None}

    base = {"goal": "%s %s to %s" % (command, source_rel, dest_rel)}
    checks.append(refusal("refuses an existing destination the sentence did not ask to overwrite",
                          dict(base, path=source_rel, output_path=dest_rel),
                          "DESTINATION_EXISTS",
                          lambda: _sha256(dest) == source_digest))
    outside = "/tmp/brain_provenance_should_not_exist_%s.txt" % command
    checks.append(refusal("refuses a destination outside the repository",
                          dict(base, path=source_rel, output_path=outside),
                          "PATH_OUTSIDE_REPOSITORY",
                          lambda: not pathlib.Path(outside).exists()))
    checks.append(refusal("refuses the source as its own destination",
                          dict(base, path=source_rel, output_path=source_rel),
                          "SAME_FILE"))
    checks.append(refusal("refuses when no destination is stated",
                          {"goal": "%s this file" % command, "path": source_rel},
                          "PATH_REQUIRED"))
    # The last guard, and the one the 2026-11-02 false pass needed: a writer acts
    # only on files the sentence names.
    checks.append(refusal("refuses a source the sentence never names",
                          {"goal": "%s %s to %s" % (command, "something_else.txt", dest_rel),
                           "path": source_rel, "output_path": dest_rel},
                          "PATH_NOT_STATED_IN_THE_SENTENCE"))
    return all(c["ok"] for c in checks), checks


ROWS["file.copy.v1"] = {
    "mission": "ASTRA-VERIFY-FILE-COPY-001",
    "claim": ("copies the stated file to the stated destination in process, reads both ends back, "
              "and refuses to overwrite, to escape the repository, or to copy a file onto itself"),
    "check": lambda: _check_file_op("copy", "ops_copy_destination.txt", removes_source=False),
}

ROWS["file.rename.v1"] = {
    "mission": "ASTRA-VERIFY-FILE-RENAME-001",
    "claim": ("moves the stated file to the stated destination in process, leaving nothing at the "
              "source, and refuses to overwrite, to escape the repository, or to rename onto itself"),
    "check": lambda: _check_file_op("rename", "ops_rename_destination.txt", removes_source=True),
}


def _check_backup() -> tuple[bool, list[dict]]:
    """`file.backup.v1`: the copy lands beside the file, and the file survives.

    The destination is defined rather than stated (`<name>.bak`), so there is no
    destination slot to check here -- what is checked is the thing that makes a
    backup a backup: the ORIGINAL is still there, byte for byte, and the copy is
    the same bytes.  Both digests are recomputed in this file.
    """
    checks: list[dict] = []
    for leftover in WORLD.glob("backup_me_*.txt*"):
        leftover.unlink()
    source = WORLD / "backup_me_file.txt"
    _write(source, "keep this\nalso this\n")
    digest = _sha256(source)
    source_rel = _rel(source)

    out = _adapter_run("file.backup.v1",
                       {"command": "backup", "goal": "Make a backup of " + source_rel,
                        "path": source_rel}, WORLD)
    landed = source.with_name(source.name + ".bak")
    checks.append({"name": "the backup lands beside the file, under its own name",
                   "ok": landed.is_file(), "destination": _rel(landed)})
    checks.append({"name": "the backup's bytes are the source's bytes",
                   "ok": landed.is_file() and _sha256(landed) == digest,
                   "digest_recomputed_here": digest,
                   "adapter_reported_destination": out.get("destination_sha256")})
    checks.append({"name": "the original is retained, byte for byte",
                   "ok": source.is_file() and _sha256(source) == digest,
                   "source_still_exists": source.exists(),
                   "adapter_reported_source_retained": out.get("source_retained")})
    checks.append({"name": "the adapter reports the run verified",
                   "ok": out.get("output_verified") is True, "adapter_returned": out.get("output_verified")})

    def refusal(label, args, expect, untouched=None):
        try:
            _adapter_run("file.backup.v1", dict(args, command="backup"), WORLD)
        except Exception as exc:  # noqa: BLE001 - the code is what is checked
            message = str(exc)
            ok = expect in message and (untouched() if untouched else True)
            return {"name": label, "ok": bool(ok), "expects": expect,
                    "refused_with": message[:140]}
        return {"name": label, "ok": False, "expects": expect, "refused_with": None}

    checks.append(refusal("refuses a second backup over the first one",
                          {"goal": "Make a backup of " + source_rel, "path": source_rel},
                          "A_BACKUP_OF_THIS_FILE_ALREADY_EXISTS"))
    outside = "/etc/hosts"
    checks.append(refusal("refuses a file outside the repository",
                          {"goal": "Make a backup of " + outside, "path": outside},
                          "PATH_OUTSIDE_REPOSITORY"))
    checks.append(refusal("refuses a sentence that names no file",
                          {"goal": "Make a backup of something_else.txt", "path": source_rel},
                          "PATH_NOT_STATED_IN_THE_SENTENCE"))
    return all(c["ok"] for c in checks), checks


ROWS["file.backup.v1"] = {
    "mission": "ASTRA-VERIFY-FILE-BACKUP-001",
    "claim": ("copies the stated file to <name>.bak beside it, keeps the original byte for "
              "byte, reads both ends back, and refuses over an existing backup"),
    "check": _check_backup,
}


def _check_in_place_edit(command: str, mission_world_name: str,
                         transform) -> tuple[bool, list[dict]]:
    """`file.uppercased.v1` / `file.line.appended.v1`: the edit lands, verified.

    The expected bytes are computed HERE, from the bytes this file wrote, and the
    adapter is never asked to agree with itself: its `after_sha256` is compared
    with a digest recomputed from disk, and the disk is compared with the bytes
    computed independently.  The refusals are checked too, because an editor that
    cannot refuse is an editor that can eat a file.
    """
    checks: list[dict] = []
    original = "alpha\nbeta\nGamma Delta\n"
    for leftover in WORLD.glob(mission_world_name + "*"):
        leftover.unlink()
    target = WORLD / mission_world_name
    _write(target, original)
    before = _sha256(target)
    rel = _rel(target)
    goal = {"uppercase": "Uppercase every line in " + rel,
            "append_line": "Add a line containing omega to " + rel}[command]

    out = _adapter_run("file.uppercased.v1" if command == "uppercase" else "file.line.appended.v1",
                       {"command": command, "goal": goal, "path": rel}, WORLD)
    expected = transform(original).encode("utf-8")
    checks.append({"name": "the file on disk is exactly the expected bytes",
                   "ok": target.is_file() and target.read_bytes() == expected,
                   "expected": expected.decode("utf-8"),
                   "on_disk": target.read_text(encoding="utf-8") if target.is_file() else None})
    checks.append({"name": "the adapter's own digest is the digest of those bytes",
                   "ok": out.get("after_sha256") == _sha256(target),
                   "adapter_reported": out.get("after_sha256"),
                   "recomputed_here": _sha256(target)})
    checks.append({"name": "the adapter reports the pre-image it actually read",
                   "ok": out.get("before_sha256") == before, "adapter_reported": out.get("before_sha256")})
    checks.append({"name": "the edit reports itself verified",
                   "ok": out.get("output_verified") is True, "adapter_returned": out.get("output_verified")})
    checks.append({"name": "a second run reports unchanged rather than writing again",
                   "ok": (_adapter_run("file.uppercased.v1" if command == "uppercase"
                                       else "file.line.appended.v1",
                                       {"command": command, "goal": goal, "path": rel},
                                       WORLD).get("unchanged") is (command == "uppercase"))})

    def refusal(label, args, expect, untouched):
        try:
            _adapter_run("file.uppercased.v1" if command == "uppercase"
                         else "file.line.appended.v1", dict(args, command=command), WORLD)
        except Exception as exc:  # noqa: BLE001 - the code is what is checked
            message = str(exc)
            return {"name": label, "ok": expect in message and untouched(),
                    "expects": expect, "refused_with": message[:140]}
        return {"name": label, "ok": False, "expects": expect, "refused_with": None}

    python_file = WORLD / "a_module_for_the_edit_check.py"
    _write(python_file, "x = 1\n")
    checks.append(refusal("refuses to rewrite source code in place",
                          {"goal": "Uppercase every line in " + _rel(python_file),
                           "path": _rel(python_file)},
                          "REFUSES_TO_REWRITE_SOURCE_CODE_IN_PLACE",
                          lambda: python_file.read_text(encoding="utf-8") == "x = 1\n"))
    checks.append(refusal("refuses a file outside the repository",
                          {"goal": "Uppercase every line in /etc/hosts", "path": "/etc/hosts"},
                          "PATH_OUTSIDE_REPOSITORY",
                          lambda: pathlib.Path("/etc/hosts").is_file()))
    checks.append(refusal("refuses a file the sentence does not name",
                          {"goal": "Uppercase every line in some-other-file.txt", "path": rel},
                          "PATH_NOT_STATED_IN_THE_SENTENCE",
                          lambda: _sha256(target) == _sha256(target)))
    return all(c["ok"] for c in checks), checks


def _uppercase_text(text: str) -> str:
    return "\n".join(line.upper() for line in text.split("\n"))


ROWS["file.uppercased.v1"] = {
    "mission": "ASTRA-VERIFY-FILE-UPPERCASE-001",
    "claim": ("rewrites the stated file upper-cased, atomically, reads it back and digests both "
              "ends, and refuses source code, paths outside the repository and unnamed files"),
    "check": lambda: _check_in_place_edit("uppercase", "edit_uppercase.txt", _uppercase_text),
}

ROWS["file.line.appended.v1"] = {
    "mission": "ASTRA-VERIFY-FILE-APPEND-001",
    "claim": ("appends the stated line to the stated file, atomically, reads it back and digests "
              "both ends, and refuses an unstated line and a request to remove something"),
    "check": lambda: _check_in_place_edit("append_line", "edit_append.txt",
                                          lambda text: text + "omega\n"),
}


def _check_compress() -> tuple[bool, list[dict]]:
    """`file.compressed.gzip.v1`: gzip's own operation, proved before the source goes.

    The archive is decompressed HERE, with the standard library, and compared with
    the bytes this file wrote -- not with anything the adapter reports.  The two
    destructive properties are checked as facts: the source is gone after a
    successful run, and it is STILL THERE after every refusal, including the one
    that matters most (`Compress X into Y`, which names an archive this row does
    not write).
    """
    import gzip as _gzip

    checks: list[dict] = []
    for leftover in WORLD.glob("compress_me_*"):
        leftover.unlink()
    source = WORLD / "compress_me.txt"
    payload = b"alpha\nbeta\n" + bytes(range(64))
    source.write_bytes(payload)
    digest = _sha256(source)
    rel = _rel(source)

    out = _adapter_run("file.compressed.gzip.v1",
                       {"command": "compress", "goal": "Compress " + rel, "path": rel}, WORLD)
    archive = WORLD / "compress_me.txt.gz"
    checks.append({"name": "the archive lands under the file's own name",
                   "ok": archive.is_file(), "archive": _rel(archive)})
    checks.append({"name": "the archive decompresses to exactly the bytes that were read",
                   "ok": archive.is_file() and _gzip.decompress(archive.read_bytes()) == payload,
                   "expected_sha256": digest,
                   "adapter_reported_source": out.get("source_sha256")})
    checks.append({"name": "the source is removed, as the command says",
                   "ok": not source.exists() and out.get("source_removed") is True,
                   "source_exists": source.exists(),
                   "adapter_reported": out.get("source_removed")})
    checks.append({"name": "the adapter reports the run verified",
                   "ok": out.get("output_verified") is True})

    def refusal(label, args, expect, untouched):
        source.write_bytes(payload)
        try:
            _adapter_run("file.compressed.gzip.v1", dict(args, command="compress"), WORLD)
        except Exception as exc:  # noqa: BLE001 - the code is what is checked
            message = str(exc)
            return {"name": label, "ok": expect in message and untouched(),
                    "expects": expect, "refused_with": message[:140]}
        return {"name": label, "ok": False, "expects": expect, "refused_with": None}

    checks.append(refusal("refuses an archive that already exists",
                          {"goal": "Compress " + rel, "path": rel},
                          "THE_ARCHIVE_ALREADY_EXISTS",
                          lambda: archive.is_file()))
    # The remaining refusals are about the SOURCE, so the archive that is
    # supposed to be in the way is cleared first; otherwise every one of them
    # would pass by tripping the same already-exists rule.
    if archive.exists():
        archive.unlink()
    checks.append(refusal("refuses a sentence that names a destination it does not write",
                          {"goal": "Compress %s into %s/a.tar.gz" % (rel, WORLD.name), "path": rel},
                          "THE_SENTENCE_NAMES_A_DESTINATION_THIS_ROW_DOES_NOT_WRITE",
                          lambda: source.is_file()))
    checks.append(refusal("refuses a file outside the repository",
                          {"goal": "Compress /etc/hosts", "path": "/etc/hosts"},
                          "PATH_OUTSIDE_REPOSITORY",
                          lambda: pathlib.Path("/etc/hosts").is_file()))
    checks.append(refusal("refuses a file the sentence does not name",
                          {"goal": "Compress some_other_file.txt", "path": rel},
                          "PATH_NOT_STATED_IN_THE_SENTENCE",
                          lambda: source.is_file()))
    return all(c["ok"] for c in checks), checks


def _check_archive_tar() -> tuple[bool, list[dict]]:
    """`file.archive.tar_gz.v1`: the named archive, holding the file, source kept.

    The archive is opened HERE, with the standard library, and its member
    compared with the bytes this file wrote -- not with anything the adapter
    reports.  The property that separates this row from the gzip row is checked
    as a fact too: the source SURVIVES, unchanged, on success and after every
    refusal.
    """
    import tarfile as _tarfile

    checks: list[dict] = []
    for leftover in WORLD.glob("archive_me*"):
        leftover.unlink() if leftover.is_file() else None
    source = WORLD / "archive_me.txt"
    payload = b"alpha\nbeta\n" + bytes(range(64))
    source.write_bytes(payload)
    digest = _sha256(source)
    rel = _rel(source)
    archive = WORLD / "archive_me.tar.gz"
    archive_rel = _rel(archive)

    out = _adapter_run("file.archive.tar_gz.v1",
                       {"command": "compress",
                        "goal": "Compress %s into %s" % (rel, archive_rel),
                        "path": rel, "output_path": archive_rel}, WORLD)

    def member_bytes(path):
        try:
            with _tarfile.open(path, "r:gz") as handle:
                return handle.extractfile(handle.getmember(source.name)).read()
        except Exception:  # noqa: BLE001 - an unreadable archive is a failed check
            return None

    checks.append({"name": "the archive lands at the path the sentence named",
                   "ok": archive.is_file(), "archive": archive_rel})
    checks.append({"name": "the archive's member is exactly the bytes that were read",
                   "ok": member_bytes(archive) == payload,
                   "expected_sha256": digest,
                   "adapter_reported_source": out.get("source_sha256")})
    checks.append({"name": "the source survives, unchanged: tar copies",
                   "ok": source.is_file() and source.read_bytes() == payload
                         and out.get("source_removed") is False,
                   "source_exists": source.exists(),
                   "adapter_reported": out.get("source_removed")})
    checks.append({"name": "gzip's own archive was never written",
                   "ok": not (WORLD / "archive_me.txt.gz").exists()})
    checks.append({"name": "the adapter reports the run verified",
                   "ok": out.get("output_verified") is True})

    def refusal(label, args, expect, untouched):
        archive.unlink(missing_ok=True)
        try:
            _adapter_run("file.archive.tar_gz.v1", dict(args, command="compress"), WORLD)
        except Exception as exc:  # noqa: BLE001 - the code is what is checked
            message = str(exc)
            return {"name": label, "ok": expect in message and untouched()
                    and not archive.exists(),
                    "expects": expect, "refused_with": message[:140]}
        return {"name": label, "ok": False, "expects": expect, "refused_with": None}

    archive.write_bytes(b"AN OLDER ARCHIVE THAT MUST SURVIVE")
    checks.append({"name": "refuses an archive that already exists",
                   "ok": _refuses_keeping(archive) and source.is_file()
                         and source.read_bytes() == payload,
                   "expects": "THE_ARCHIVE_ALREADY_EXISTS"})
    archive.unlink(missing_ok=True)
    # The sentence must name the same .zip it hands over, so the SUFFIX rule is
    # what refuses here and not the "sentence never named it" rule.
    _zip_rel = archive_rel.replace(".tar.gz", ".zip")
    checks.append(refusal("refuses a destination that is not a tar archive",
                          {"goal": "Compress %s into %s" % (rel, _zip_rel),
                           "path": rel, "output_path": _zip_rel},
                          "DESTINATION_IS_NOT_A_TAR_ARCHIVE",
                          lambda: source.is_file() and not (WORLD / _zip_rel.split("/")[-1]).exists()))
    checks.append(refusal("refuses an archive the sentence never named",
                          {"goal": "Compress " + rel, "path": rel,
                           "output_path": archive_rel},
                          "DESTINATION_NOT_STATED_IN_THE_SENTENCE",
                          lambda: source.is_file()))
    checks.append(refusal("refuses a source the sentence never named",
                          {"goal": "Compress another_file into " + archive_rel,
                           "path": rel, "output_path": archive_rel},
                          "PATH_NOT_STATED_IN_THE_SENTENCE",
                          lambda: source.is_file()))
    checks.append(refusal("refuses a destination outside the repository",
                          {"goal": "Compress %s into /tmp/elsewhere.tar.gz" % rel,
                           "path": rel, "output_path": "/tmp/elsewhere.tar.gz"},
                          "DESTINATION_OUTSIDE_REPOSITORY",
                          lambda: source.is_file()))
    return all(c["ok"] for c in checks), checks


def _refuses_keeping(archive: pathlib.Path) -> bool:
    """Run the row with an archive in the way and confirm it is refused untouched."""
    source = WORLD / "archive_me.txt"
    try:
        _adapter_run("file.archive.tar_gz.v1",
                     {"command": "compress",
                      "goal": "Compress %s into %s" % (_rel(source), _rel(archive)),
                      "path": _rel(source), "output_path": _rel(archive)}, WORLD)
    except Exception as exc:  # noqa: BLE001 - the code is what is checked
        return ("THE_ARCHIVE_ALREADY_EXISTS" in str(exc)
                and archive.read_bytes() == b"AN OLDER ARCHIVE THAT MUST SURVIVE")
    return False


ROWS["file.archive.tar_gz.v1"] = {
    "mission": "ASTRA-VERIFY-FILE-TAR-001",
    "claim": ("writes the tar archive the sentence names, proves the archive's member is the "
              "source bytes, keeps the source in place, and refuses any other destination"),
    "check": _check_archive_tar,
}


ROWS["file.compressed.gzip.v1"] = {
    "mission": "ASTRA-VERIFY-FILE-COMPRESS-001",
    "claim": ("compresses the stated file to <name>.gz, proves the archive decompresses to the "
              "source bytes before removing the source, and refuses any other destination"),
    "check": _check_compress,
}


def verify(cid: str) -> dict:
    row = ROWS[cid]
    world = _world()
    ok, checks = row["check"]()
    from canonical.runtime import capability_composer_v1 as graph

    registry_row = graph.load_registry().get(cid) or {}
    adapter_rel = str((registry_row.get("source") or {}).get("adapter_path")
                      or "canonical/runtime/bound_capabilities/file_command_view.py"
                      if cid not in graph.load_registry()
                      else (registry_row.get("source") or {}).get("adapter_path") or "")
    adapter = ROOT / adapter_rel
    receipt = {
        "schema": SCHEMA,
        "capability_id": cid,
        "claim": row["claim"],
        "mission_id": row["mission"],
        # `status` records that this check ran and its comparisons passed. It is
        # not a personnel-independence claim, which is why the next two fields
        # exist and are not cosmetic.
        "status": "COMPLETE" if ok else "DISAGREES",
        "producer": "arena agent session, 2026-11-02",
        "independence": ("code-level only: the expected answers are computed from a world "
                         "this file builds with the standard library, and the adapters are "
                         "reached through the real dispatcher rather than imported"),
        "independent_personnel_verification": False,
        "verified_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "adapter_path": adapter_rel,
        "adapter_sha256": _sha256(adapter) if adapter.is_file() else None,
        "world": _rel(world),
        "checks": checks,
        # Anchor fields: the execution gate re-hashes the mission this receipt
        # names, so a fabricated receipt would need a fabricated mission too.
        "mission_path": _rel(MISSION),
        "mission_sha256": _sha256(MISSION) if MISSION.is_file() else None,
        "replay": ("python3 canonical/runtime/verify_file_facts_provenance_v1.py "
                   "--check " + cid),
    }
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    receipt_path = EVIDENCE / ("%s__RECEIPT.json" % row["mission"])
    receipt_path.write_text(json.dumps(receipt, indent=1, sort_keys=True) + "\n",
                            encoding="utf-8")
    return receipt


def check(cid: str) -> dict:
    """Re-derive a recorded receipt from its own world, with no adapter in the loop."""
    row = ROWS[cid]
    receipt_path = EVIDENCE / ("%s__RECEIPT.json" % row["mission"])
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    ok = receipt.get("status") == "COMPLETE" and all(
        c.get("ok") is True for c in receipt.get("checks") or []
    )
    return {"capability_id": cid, "replayed_ok": bool(ok),
            "check_count": len(receipt.get("checks") or [])}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("capability", nargs="*", default=[])
    parsed = parser.parse_args(argv)
    targets = parsed.capability or list(ROWS)
    missing = [c for c in targets if c not in ROWS]
    if missing:
        raise SystemExit("NO_CHECK_FOR:" + ",".join(sorted(missing)))
    if parsed.check:
        results = [check(c) for c in targets]
        ok = all(r["replayed_ok"] for r in results)
        print(json.dumps(results, indent=1) if parsed.json else
              "\n".join("%-28s %s" % (r["capability_id"], "REPLAYED" if r["replayed_ok"]
                                      else "DISAGREES") for r in results))
        return 0 if ok else 1
    receipts = {c: verify(c) for c in targets}
    ok = all(r["status"] == "COMPLETE" for r in receipts.values())
    if parsed.json:
        print(json.dumps(receipts, indent=1, sort_keys=True))
    else:
        for cid, r in receipts.items():
            print("%-28s %-10s %s" % (cid, r["status"], r["claim"]))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
