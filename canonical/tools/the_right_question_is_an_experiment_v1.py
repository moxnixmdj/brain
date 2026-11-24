#!/usr/bin/env python3
"""The right question is an experiment: compile a prose claim to a witness, and
admit only what separates a wrong version and repeats on a second room.

THE OWNER'S QUESTION, TAKEN WHOLE
---------------------------------
> "All he should do is just scan everything in the environment and then retrieve from his memory
> what he knows and what he doesn't know. What he doesn't know, he should get it instantly from the
> web... I don't know what the next step is, what he should exactly save, what is not, and what we
> should generalize and what is not."

The previous round answered the transcript half of that question: a guide's examples are tests the
author wrote by accident, 189 of them, 138 run, 130 matched the guide's own printed output, and
only 5.96% of 361,161 bytes of documentation is of that kind. That left 94% as prose, and prose was
not read.

This round reads it, and asks the only question that can make prose checkable:

    NOT "what does this sentence say?"
        "what experiment would make this claim TRUE or FALSE?"

A prose claim is admissible knowledge only when it compiles to a WITNESS that passes six gates:

    G1 NAMES_A_PROGRAM            the claim names a program this machine has, and the caller may do
    G2 NAMES_AN_OBJECT_KIND       the claim names or implies an object kind this machine can produce
    G3 NAMES_AN_OBSERVABLE        the claim names or implies an observable a read-only sensor can read
    G4 SEPARATES_A_WRONG_VERSION  the witness says TRUE for the claim and FALSE for a machine-made
                                  wrong version of it; a check that accepts both is not a witness
    G5 REPEATS_ON_A_SECOND_ROOM   the verdict is the same on a second room of the same kinds with
                                  different content; otherwise the claim is about content, not kind
    G6 OBSERVES                   the sensor changes nothing in the room; a check that writes the
                                  object it is asked about is not a question

What is SAVED is the RELATION -- program, object kind, observable, relation, witness, source digest,
verdict -- never the prose, never the trace, never the instance. What GENERALIZES is the
content-invariant relation, not the room it was verified in. The witness is re-run at use.

THE LIVE DEFECT THIS ROUND STARTS FROM
--------------------------------------
`perfect_algorithm_v1.run()` fetches instant knowledge and then passes the fetcher's documents to
`_plan_from_document` -- except it reads `instant["documents"]`, a key that is never set. The
documents are under `instant["local_guide"]["documents"]`, and those documents are one-paragraph
SNIPPETS, not the text that contains a transcript. So the previous round's circuit is still open:
a README whose transcript the guide test suite can replay yields `OPEN__NO_PLAN_AFTER_SCAN` through
`run()`, because nothing the fetcher returned ever reaches the extractor. This round fixes the
wiring, adds the full text to the local guide, and measures the before/after.

WHAT THIS DOES NOT CLAIM
------------------------
- Not that prose is mostly checkable. It is not, and the measurement says how much is.
- Not that a compiled witness is a proof. It is a discriminator that separated one wrong version
  and repeated on one second room; a third room is measured separately and may refuse it.
- Not that a stored relation is a capability. It is external knowledge, labelled with its source,
  and the machine re-verifies it at use.
- Not a benchmark result. One machine, one fleet of programs, zero GUI, zero network at run time.

Model calls: 0. Parameters stored: 0. Network at run time: 0.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, Mapping, Sequence

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

SCHEMA = "BRAIN_THE_RIGHT_QUESTION_IS_AN_EXPERIMENT_20261124_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX"
RELATION_SCHEMA = "PROJECT_BRAIN_VERIFIED_RELATION_V1"
MEMORY_SCHEMA = "PROJECT_BRAIN_ENVIRONMENTAL_COGNITION_V1"

DEFAULT_MEMORY = str(pathlib.Path(__file__).resolve().parents[2]
                     / "canonical" / "astra_runtime" / "state"
                     / "ENVIRONMENTAL_COGNITION_V1.json")

# --------------------------------------------------------------------------- #
# 0. CLOSED CLASSES OF ENGLISH WORDS. No program is named in this file.
# --------------------------------------------------------------------------- #
# A relation is a closed class of verbs a page uses to say what a program does to an object.
# A relation carries the observable it is about by default, because prose often says "sort the
# lines" without saying "order": the relation names the observable even when the sentence does not.
RELATIONS: dict[str, dict[str, Any]] = {
    "grows": {"words": ("increase", "increases", "increasing", "grow", "grows", "growing",
                        "larger", "expand", "expands", "expanding"),
              "observable": "size", "predicate": "size_gt"},
    "compresses": {"words": ("compress", "compresses", "compressing", "compressor",
                             "compressors", "pack", "packs"),
                   "observable": "size", "predicate": "size_lt"},
    "decompresses": {"words": ("decompress", "decompresses", "uncompress", "uncompresses",
                               "unpack", "unpacks"),
                     "observable": "content", "predicate": "content_equals_original"},
    "archives": {"words": ("archive", "archives", "archiving", "saves", "save", "saving"),
                 "observable": "valid", "predicate": "valid_archive"},
    "extracts": {"words": ("extract", "extracts", "extracting", "unarchive", "restore",
                           "restores", "restoring"),
                 "observable": "content", "predicate": "content_equals_member"},
    "lists": {"words": ("list", "lists", "listing", "enumerate", "enumerates"),
              "observable": "stdout", "predicate": "stdout_contains_member"},
    "sorts": {"words": ("sort", "sorts", "sorting", "order", "orders", "arrange", "arranges"),
              "observable": "order", "predicate": "sorted"},
    "reverses": {"words": ("reverse", "reverses", "reversing", "tac"),
                 "observable": "order", "predicate": "reversed"},
    "creates": {"words": ("create", "creates", "creating", "make", "makes", "making",
                          "produce", "produces", "generates"),
                "observable": "exists", "predicate": "exists_after"},
    "removes": {"words": ("remove", "removes", "removing", "delete", "deletes", "deleting",
                          "erase", "erases", "unlink", "unlinks"),
                "observable": "exists", "predicate": "not_exists_after"},
    "counts": {"words": ("count", "counts", "counting", "number", "numbers"),
               "observable": "stdout", "predicate": "stdout_reports_the_count"},
    "checks": {"words": ("check", "checks", "checking", "verify", "verifies",
                         "test", "tests", "testing", "validate", "validates"),
               "observable": "valid", "predicate": "distinguishes_valid_from_corrupt"},
    "searches": {"words": ("search", "searches", "searching", "find", "finds", "finding",
                           "match", "matches", "matching"),
                 "observable": "stdout", "predicate": "stdout_contains"},
    "compares": {"words": ("compare", "compares", "comparing", "diff", "diffs"),
                 "observable": "exit", "predicate": "exit_nonzero"},
    "applies": {"words": ("apply", "applies", "applying", "patch", "patches"),
                "observable": "content", "predicate": "content_equals_patched"},
    "prints": {"words": ("print", "prints", "printing", "output", "outputs", "display",
                         "displays", "dump", "dumps", "show", "shows", "emit", "emits",
                         "write", "writes", "writing"),
               "observable": "stdout", "predicate": "stdout_nonempty"},
    "copies": {"words": ("copy", "copies", "copying", "duplicate", "duplicates"),
               "observable": "content", "predicate": "content_equal"},
    "renames": {"words": ("rename", "renames", "renaming", "move", "moves", "moving"),
                "observable": "exists", "predicate": "source_gone_destination_there"},
    "reformats": {"words": ("reformat", "reformats", "reformatting", "reflow", "reflows"),
                  "observable": "content", "predicate": "content_changed"},
    "runs": {"words": ("run", "runs", "running", "execute", "executes", "executing"),
             "observable": "exit", "predicate": "exit_zero"},
}

# An observable is a closed class of nouns a page uses to say what can be read.
OBSERVABLES: dict[str, tuple[str, ...]] = {
    "size": ("size", "sizes", "bytes", "byte", "length", "lengths"),
    "content": ("content", "contents", "text", "data", "body"),
    "lines": ("line", "lines"),
    "count": ("count", "counts", "number", "numbers"),
    "order": ("order", "orders", "ordered", "sorted", "ascending", "descending"),
    "type": ("type", "types", "kind", "kinds", "format", "formats"),
    "stdout": ("stdout", "standard output", "stdout", "output"),
    "exit": ("exit", "exit status", "exit code", "status", "return code"),
    "checksum": ("checksum", "checksums", "digest", "hash", "hashes"),
    "name": ("name", "names", "filename", "filenames"),
    "member": ("member", "members", "entry", "entries"),
    "row": ("row", "rows", "record", "records"),
    "value": ("value", "values"),
    "valid": ("valid", "invalid", "corrupt", "corrupted", "integrity"),
    "exists": ("exist", "exists", "existence", "present", "absent"),
}

# An object kind is a closed class of nouns a page uses to say what the object is.
KINDS: dict[str, tuple[str, ...]] = {
    "text": ("text", "texts", "string", "strings", "character", "characters", "stdin"),
    "file": ("file", "files", "filesystem", "filesystems"),
    "line": ("line", "lines"),
    "archive": ("archive", "archives", "tarball", "tarballs", "tar", "zip", "zipped"),
    "compressed": ("compressed", "compressed file", "gzip", "gz", "xz", "bzip2", "bz2", "lzma"),
    "directory": ("directory", "directories", "folder", "folders", "dir", "dirs"),
    "json": ("json",),
    "xml": ("xml",),
    "csv": ("csv",),
    "database": ("database", "databases", "db", "table", "tables"),
    "image": ("image", "images", "png", "jpeg", "jpg", "bitmap"),
    "certificate": ("certificate", "certificates", "cert", "certs", "x509"),
    "key": ("key", "keys", "private key", "public key"),
    "patch": ("patch", "patches", "diff", "diffs"),
    "commit": ("commit", "commits"),
    "branch": ("branch", "branches"),
    "repository": ("repository", "repositories", "repo", "repos"),
}

# A predicate is the smallest thing a witness can decide. It is named, not coded per program.
PREDICATES: dict[str, Callable[[Mapping[str, Any]], bool]] = {
    "size_lt": lambda r: _num(r.get("after")) is not None and _num(r.get("before")) is not None
    and _num(r["after"]) < _num(r["before"]),
    "size_le": lambda r: _num(r.get("after")) is not None and _num(r.get("before")) is not None
    and _num(r["after"]) <= _num(r["before"]),
    "size_gt": lambda r: _num(r.get("after")) is not None and _num(r.get("before")) is not None
    and _num(r["after"]) > _num(r["before"]),
    "size_ge": lambda r: _num(r.get("after")) is not None and _num(r.get("before")) is not None
    and _num(r["after"]) >= _num(r["before"]),
    "stdout_nonempty": lambda r: bool(str(r.get("stdout") or "").strip()),
    "stdout_empty": lambda r: not str(r.get("stdout") or "").strip(),
    "stdout_contains": lambda r: str(r.get("needle") or "") in str(r.get("stdout") or ""),
    "stdout_contains_member": lambda r: str(r.get("needle") or "") in str(r.get("stdout") or ""),
    "stdout_not_contains_member": lambda r: str(r.get("needle") or "") not in str(r.get("stdout") or ""),
    "stdout_not_contains": lambda r: str(r.get("needle") or "") not in str(r.get("stdout") or ""),
    "content_contains": lambda r: str(r.get("needle") or "") in str(r.get("after") or ""),
    "content_not_contains": lambda r: str(r.get("needle") or "") not in str(r.get("after") or ""),
    # EVERY content predicate requires the value to be PRESENT. `str(None) == str(None)` made
    # an object that could not be read equal to itself, and that is how `cp copies a directory`
    # was true of the program that does nothing. Presence is `is not None and not empty`, not
    # truthiness: a reading of `0` is a value.
    "content_equals": lambda r: _present(r.get("after"))
    and str(r["after"]) == str(r.get("original")),
    "content_not_equals": lambda r: _present(r.get("after"))
    and str(r["after"]) != str(r.get("original")),
    "content_changed": lambda r: _present(r.get("after"))
    and str(r["after"]) != str(r.get("before")),
    "content_equal": lambda r: _present(r.get("after"))
    and str(r["after"]) == str(r.get("before")),
    "content_equals_original": lambda r: _present(r.get("after"))
    and str(r["after"]) == str(r.get("original")),
    "content_equals_member": lambda r: _present(r.get("after"))
    and _present(r.get("needle")) and str(r["needle"]) in str(r["after"]),
    "content_equals_patched": lambda r: _present(r.get("after"))
    and _present(r.get("needle")) and str(r["needle"]) in str(r["after"]),
    "sorted": lambda r: _code(r.get("after")) == 0 and _code(r.get("before")) != 0,
    "not_sorted": lambda r: not (_code(r.get("after")) == 0 and _code(r.get("before")) != 0),
    "reversed": lambda r: bool(r.get("reversed")),
    "exists_after": lambda r: bool(r.get("after_exists")),
    "not_exists_after": lambda r: not bool(r.get("after_exists")),
    "valid_check": lambda r: _code(r.get("after")) == 0,
    "distinguishes_valid_from_corrupt": lambda r: _code(r.get("after")) == 0
    and _code(r.get("corrupt_exit")) not in (None, 0),
    "does_not_distinguish": lambda r: not (_code(r.get("after")) == 0
                                           and _code(r.get("corrupt_exit")) not in (None, 0)),
    "invalid_check": lambda r: _code(r.get("after")) != 0,
    "valid_archive": lambda r: _code(r.get("after")) == 0,
    "stdout_reports_the_count": lambda r: _num(re.sub(r"[^0-9]", " ",
                                                       str(r.get("stdout") or "")).split()[0]
                                               if re.sub(r"[^0-9]", " ",
                                                         str(r.get("stdout") or "")).split()
                                               else "") == _num(r.get("expected"))
    if str(r.get("stdout") or "").strip() else False,
    "stdout_does_not_report_the_count": lambda r: not (
        _num(re.sub(r"[^0-9]", " ", str(r.get("stdout") or "")).split()[0]
             if re.sub(r"[^0-9]", " ", str(r.get("stdout") or "")).split() else "")
        == _num(r.get("expected")) if str(r.get("stdout") or "").strip() else False),
    "count_equals": lambda r: _num(r.get("after")) is not None
    and _num(r["after"]) == _num(r.get("expected")),
    "count_not_equals": lambda r: _num(r.get("after")) is not None
    and _num(r["after"]) != _num(r.get("expected")),
    "checksum_equal": lambda r: bool(r.get("after")) and r.get("after") == r.get("before"),
    "exit_zero": lambda r: _code(r.get("exit")) == 0,
    "source_gone_destination_there": lambda r: bool(r.get("after_exists"))
    and not bool(r.get("source_exists")),
    # A QUALIFIER IS AN ORDER OVER THE PROGRAM'S OWN OUTPUT, read with a read-only sensor.
    "order_alphabetical": lambda r: bool(r.get("stdout_order") == "ascending"),
    "order_ascending": lambda r: bool(r.get("stdout_order") == "ascending"),
    "order_descending": lambda r: bool(r.get("stdout_order") == "descending"),
    "order_numerical": lambda r: bool(r.get("stdout_order") == "ascending"
                                      and r.get("stdout_numeric") is True),
    "destination_absent_or_source_still_there": lambda r: not (
        bool(r.get("after_exists")) and not bool(r.get("source_exists"))),
    "exit_nonzero": lambda r: _code(r.get("exit")) not in (None, 0),
}

INVERSE: dict[str, str] = {
    "size_lt": "size_ge", "size_le": "size_gt", "size_gt": "size_le", "size_ge": "size_lt",
    "stdout_nonempty": "stdout_empty", "stdout_empty": "stdout_nonempty",
    "stdout_contains": "stdout_not_contains", "stdout_not_contains": "stdout_contains",
    "stdout_contains_member": "stdout_not_contains_member",
    "stdout_not_contains_member": "stdout_contains_member",
    "content_contains": "content_not_contains", "content_not_contains": "content_contains",
    "content_equals": "content_not_equals", "content_not_equals": "content_equals",
    "content_changed": "content_equal", "content_equal": "content_changed",
    "content_equals_original": "content_not_equals", "content_equals_member": "content_not_contains",
    "content_equals_patched": "content_not_contains",
    "sorted": "not_sorted", "not_sorted": "sorted",
    "reversed": "sorted",
    "exists_after": "not_exists_after", "not_exists_after": "exists_after",
    "valid_check": "invalid_check", "invalid_check": "valid_check",
    "distinguishes_valid_from_corrupt": "does_not_distinguish",
    "does_not_distinguish": "distinguishes_valid_from_corrupt",
    "valid_archive": "invalid_check",
    "count_equals": "count_not_equals", "count_not_equals": "count_equals",
    "stdout_reports_the_count": "stdout_does_not_report_the_count",
    "stdout_does_not_report_the_count": "stdout_reports_the_count",
    "checksum_equal": "content_changed",
    "source_gone_destination_there": "destination_absent_or_source_still_there",
    "order_alphabetical": "order_descending", "order_ascending": "order_descending",
    "order_descending": "order_ascending", "order_numerical": "order_descending",
    "destination_absent_or_source_still_there": "source_gone_destination_there",
    "exit_zero": "exit_nonzero", "exit_nonzero": "exit_zero",
}

def _assert_distinct_witnesses() -> None:
    """A relation whose witness is another relation's witness is not a relation.

    `computes` and `prints` both meant `stdout is not empty`, so a single sentence stored two
    relations and the count of admitted relations was really a count of synonyms. The
    vocabulary is only honest if each name is a different experiment.
    """
    seen: dict[tuple[str, str], str] = {}
    for name, spec in RELATIONS.items():
        key = (str(spec["observable"]), str(spec["predicate"]))
        if key in seen:
            raise AssertionError(f"{name} has the same witness as {seen[key]}: {key}")
        seen[key] = name


_assert_distinct_witnesses()


# An operation is a shape over kinds: `applies` is a patch, `archives` is an archive or a
# directory, `sorts` is a text or a line. A sentence that names a relation with an incompatible
# object is not a claim about that relation, and the witness refuses it before running.
RELATION_KINDS: dict[str, tuple[str, ...]] = {
    "grows": ("text", "file", "compressed", "line"),
    "compresses": ("text", "file", "compressed", "line"),
    "decompresses": ("compressed",),
    "archives": ("archive", "zip", "directory", "repository", "file", "text"),
    "extracts": ("archive", "zip"),
    "lists": ("archive", "zip", "directory", "repository"),
    "sorts": ("text", "line", "file"),
    "reverses": ("text", "line", "file"),
    "creates": ("text", "file", "directory", "archive", "compressed", "json", "xml",
                "csv", "image", "zip"),
    "removes": ("text", "file", "directory", "archive", "compressed"),
    "counts": ("text", "line", "file"),
    "checks": ("text", "file", "archive", "compressed", "json", "xml", "csv", "zip"),
    "searches": ("directory", "text", "file", "repository"),
    "compares": ("text", "file", "patch"),
    "applies": ("patch",),
    "prints": ("text", "file", "line"),
    "copies": ("text", "file", "directory"),
    "renames": ("text", "file", "directory"),
    "reformats": ("text", "line", "file"),
    "runs": ("text", "file"),
}

# The object a relation acts on, and the producer that makes it. The producer is a room
# preparation, not knowledge about any program: it is how one makes an object of a kind.
KIND_PRODUCER: dict[str, str] = {
    "text": "text", "file": "text", "line": "text",
    "archive": "archive", "zip": "zip", "compressed": "compressed", "directory": "directory",
    "json": "json", "xml": "xml", "csv": "csv", "database": "database",
    "image": "image", "certificate": "certificate", "key": "key",
    "patch": "patch", "commit": "commit", "branch": "commit", "repository": "commit",
}

# The sensor that reads an observable. The sensor is a read-only program the machine already has.
OBSERVABLE_SENSOR: dict[str, str] = {
    "size": "stat", "content": "cat", "lines": "wc", "count": "wc",
    "order": "sort_c", "type": "file", "stdout": "capture", "exit": "capture",
    "checksum": "sha256sum", "name": "basename", "member": "tar_t",
    "row": "sqlite", "value": "sqlite", "valid": "valid", "exists": "exists",
}

# The suffix a relation's output takes when the program writes a new object.
RELATION_OUTPUT: dict[str, str] = {
    "compresses": ".gz", "decompresses": "", "archives": ".tar", "extracts": "",
    "sorts": ".sorted", "creates": ".made", "copies": ".copy", "renames": ".moved",
}

# --------------------------------------------------------------------------- #
# 1. READ A DOCUMENT AS SENTENCES
# --------------------------------------------------------------------------- #

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+|\s{2,}|\n+")


def _num(value: Any) -> float | None:
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return None


def _code(value: Any) -> int | None:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None


_WRAPS = re.compile(r"[.!?]\s+")
_CONTINUES = re.compile(r"[,:;(\[{«—-]\s*$")


def _logical_lines(text: str) -> list[tuple[int, str]]:
    """Physical lines joined into the statements the author wrote.

    A terminal wraps prose at 80 columns, so `gzip reduces the size of the\\nnamed files` is one
    statement split across two physical lines. Reading each physical line as a sentence turned
    every wrapped clause into its own "claim" -- which is how `sort` produced a claim from
    `natural sort of (version) numbers within text`, the tail of an option row. Joining is
    therefore not formatting: it decides what counts as a statement.

    A line continues the previous one when it is indented (a wrapped description) or when the
    previous line ends mid-clause (no sentence punctuation) and this one begins lowercase.
    A new line that begins a sentence ends the block, so a heading or a blank line breaks it.
    """
    out: list[list[Any]] = []
    for line_no, raw in enumerate(text.splitlines(), 1):
        line = raw.rstrip()
        if not line.strip():
            continue
        indented = raw[:1] in (" ", "\t")
        # a flag row is never a continuation: `-d, --dictionary-order  consider only` is a
        # statement about an OPTION, and joining it to the heading above turned a page's
        # option catalogue into one enormous "sentence" that named seven relations.
        if re.match(r"^-{1,2}[A-Za-z0-9]", line.strip()):
            out.append([line_no, line.strip()])
            continue
        previous = out[-1] if out else None
        joins = previous is not None and (
            indented
            or (not _WRAPS.search(previous[1]) and not _CONTINUES.search(previous[1])
                and line[:1].islower())
        )
        if joins:
            previous[1] = previous[1].rstrip() + " " + line.strip()
        else:
            out.append([line_no, line.strip()])
    return [(int(n), str(t)) for n, t in out]


def sentences(text: Any) -> list[dict[str, Any]]:
    """Every sentence a document states, with the line it came from.

    A man page states one claim per line; a README states one per sentence. The splitter keeps
    both: a newline is a boundary, and so is a sentence-ending punctuation followed by space.
    Wrapped lines are joined first, so a wrapped clause is not its own claim.
    """
    if isinstance(text, (list, tuple)):
        text = "\n".join(str(x.get("text") if isinstance(x, Mapping) else x) for x in text)
    if not isinstance(text, str):
        return []
    out: list[dict[str, Any]] = []
    for line_no, logical in _logical_lines(text):
        for part in _WRAPS.split(logical):
            part = part.strip()
            if len(part) >= 8 and not _is_boilerplate(part):
                out.append({"line": line_no, "text": part})
    return out


def _first_relation(table: Mapping[str, Any], low: str) -> str | None:
    """The relation whose word appears EARLIEST in the sentence.

    A sentence's verb comes before its object: "tar lists the contents" is `lists`, not
    `contains`, even though "contents" is the longer word. Position is the rule; the longest
    noun is the rule for observables and kinds.
    """
    best: tuple[int, str] | None = None
    for name, spec in table.items():
        words = spec.get("words") if isinstance(spec, Mapping) else spec
        for word in words:
            found = re.search(r"(?<![A-Za-z0-9_])" + re.escape(word) + r"(?![A-Za-z0-9_])", low)
            if found and (best is None or found.start() < best[0]):
                best = (found.start(), name)
    return best[1] if best else None


def _word_span(low: str, word: str) -> tuple[int, int] | None:
    match = re.search(r"(?<![A-Za-z0-9_])" + re.escape(word) + r"(?![A-Za-z0-9_])", low)
    return (match.start(), match.end()) if match else None


def _subject_distance(low: str, program: str, words: Sequence[str]) -> int | None:
    """Characters from the program's name to the nearest relation word AFTER it, or None.

    A claim has a subject. `gzip reduces the size of files` puts the program before the verb;
    `check for sorted input; do not sort` puts the program after it, and is not a claim that
    sort sorts. Requiring subject position is what stops `The locale affects sort order` from
    compiling to `sort sorts ...`: "sort" there is a noun inside "sort order", and the only
    program name in the sentence appears after the relation word.
    """
    spans = [_word_span(low, str(program))]
    base = str(program).split("/")[-1].split(".")[-1]
    if base and base != str(program):
        spans.append(_word_span(low, base))
    best: int | None = None
    for start in (span[0] for span in spans if span):
        for word in words:
            span = _word_span(low, word)
            if span and span[0] > start:
                distance = span[0] - start
                if distance <= 80 and (best is None or distance < best):
                    best = distance
    return best


_VERB_ENDINGS = ("s", "es", "ing", "ed")


def _is_verb_form(low: str, span: tuple[int, int], sentence_start: int) -> bool:
    """A relation word must be a VERB in this sentence, not a noun that spells the same.

    `sort order` is a noun phrase; `sorts the lines` is a claim. English states a relation in a
    document as a third-person verb (`gzip reduces`), a participle (`block-sorting compressor`),
    or an imperative at the start of a sentence (`Compress or uncompress FILEs`). A bare word in
    the middle of a sentence is a noun, and matching it is how `The locale affects sort order`
    became a claim that sort sorts.
    """
    word = low[span[0]:span[1]]
    if word.endswith(_VERB_ENDINGS):
        return True
    return span[0] == sentence_start


#: A QUALIFIER is the part of a claim the relation cannot hold: `alphabetically`,
#: `numerically`, `in reverse order`. It is stored as a SECOND, OPTIONAL witness, because a
#: relation that drops it can open a door and cannot state a rule.
#:
#: THE VOCABULARY IS CLOSED, AND CLOSED ON PURPOSE. Matching every `-ly` word made `only`
#: a qualifier (`gzip will only attempt to compress regular files`), and a qualifier no
#: read-only sensor can decide is a word, not a test. So a qualifier is extracted only when the
#: sensor table below can decide it; every other adverb stays in the sentence and is not
#: pretended to be knowledge.
_QUALIFIERS: tuple[str, ...] = (
    "alphabetically", "lexicographically", "numerically",
    "in ascending order", "in descending order", "in reverse order",
)


def _qualifier_of(sentence: str) -> str:
    low = " " + sentence.lower() + " "
    for candidate in _QUALIFIERS:
        if re.search(r"(?<![a-z])" + re.escape(candidate) + r"(?![a-z])", low):
            return candidate
    return ""


def _all_relations(low: str, sentence_start: int = 0) -> list[str]:
    """Every relation whose VERB appears in the sentence, ordered by first appearance."""
    found: list[tuple[int, str]] = []
    for name, spec in RELATIONS.items():
        words = spec.get("words") if isinstance(spec, Mapping) else spec
        for word in words:
            span = _word_span(low, word)
            if span and _is_verb_form(low, span, sentence_start):
                found.append((span[0], name))
                break
    return [name for _, name in sorted(found)]


def _refine_relation(relation: str, kind: str) -> str:
    """A relation the object kind narrows: `creates` + `archive` is `archives`."""
    if relation == "creates" and kind in ("archive", "tar"):
        return "archives"
    if relation == "creates" and kind in ("compressed", "gzip", "xz", "bzip2", "bz2", "lzma"):
        return "compresses"
    if relation == "creates" and kind == "directory":
        return "creates"
    return relation


def _first_match(table: Mapping[str, Sequence[str]], low: str) -> str | None:
    """The first class whose word appears in the sentence, longest word first.

    Longest first matters: `standard output` must win over `output`, and `decompress` over
    `compress` (a decompressor's page also says "compress").
    """
    best: tuple[int, str] | None = None
    for name, spec in table.items():
        words = spec.get("words") if isinstance(spec, Mapping) else spec
        for word in words:
            if re.search(r"(?<![A-Za-z0-9_])" + re.escape(word) + r"(?![A-Za-z0-9_])", low):
                if best is None or len(word) > best[0]:
                    best = (len(word), name)
    return best[1] if best else None


# A line that is the SHAPE of a page, not a statement in it. Option rows, usage lines,
# copyright, cross-references. A sentence beginning "The" is a real sentence and is kept:
# dropping determiners was a hack for unwrapped fragments, and unwrapping (below) removes
# the fragments without losing the prose.
_BOILERPLATE = (
    "usage:", "options:", "or:", "copyright", "written by", "license", "report bugs",
    "full documentation", "info ", "note:", "warning:", "example", "examples",
)


def _is_boilerplate(sentence: str) -> bool:
    """A usage line, a flag row, an example, a cross-reference, or a copyright is not a claim.

    The extractor is generous about RELATIONS; it is strict about SENTENCES. `Usage: sort
    [OPTION]...` contains "sort" and would compile to a true witness, and counting it would
    be counting a page's shape as its knowledge. So would counting `-V, --version-sort
    natural sort of (version) numbers within text` as two statements about sorting.
    """
    low = sentence.strip().lower()
    if not low:
        return True
    if low.startswith(_BOILERPLATE):
        return True
    # a flag row: "-d, --dictionary-order  consider only blanks"
    if re.match(r"^\s*-{1,2}[A-Za-z0-9]", sentence):
        return True
    if "=>" in sentence or sentence.strip().startswith("#"):
        return True
    # a cross-reference, a heading, an epigraph
    if re.search(r"\b(see also|see the|refer to|info \(|man \w+\(\d+)|\*{2,}", low):
        return True
    # "Output options:" is a label for what follows, not a statement
    if sentence.rstrip().endswith(":"):
        return True
    return False


def _program_tokens(sentence: str) -> list[str]:
    """The identifiers a sentence could be naming as a program.

    `gzip`, `tar`, `git`, `jq` are words; `statistics.median` is dotted; a path ends in a name.
    A word that is not an identifier (`1`, `+`) is not a program.
    """
    return re.findall(r"[A-Za-z_][A-Za-z0-9_.+-]*", sentence)


def extract_claims(text: Any, *, actions: Sequence[Any] = (),
                   programs: Sequence[str] = (), max_claims: int = 2000,
                   default_kind: str = "", subject: str = "") -> list[dict[str, Any]]:
    """Every prose claim a document states that names a program and a relation.

    A claim is a candidate, not knowledge. The gates below decide which candidates are
    admissible. The extractor is deliberately generous: it is the gates that refuse, and the
    refusal reasons are the measurement.

    `subject` is the program the document is ABOUT. A man page's opening line is an imperative
    with the subject omitted -- `Compress or uncompress FILEs` is a claim about gzip, and gzip
    is named only in the `Usage:` line above it. Passing the document's owner recovers the
    subject without guessing it from the words.
    """
    offered = {str(a).strip() for a in actions if str(a).strip()}
    offered_programs = {a.split()[0] for a in offered if a.split()}
    known = {str(p).strip() for p in programs if str(p).strip()}
    out: list[dict[str, Any]] = []
    for sentence in sentences(text):
        low = sentence["text"].lower()
        program = None
        for token in _program_tokens(sentence["text"]):
            base = token.split("/")[0].split(".")[-1]
            if token in offered or base in offered or token in known or base in known:
                program = token
                break
        kind = _first_match(KINDS, low) or default_kind
        # The document's owner may be the implicit subject, but only of an IMPERATIVE: the
        # relation word must start the sentence. `sort order` in mid-sentence is a noun.
        implicit = False
        if program is None and subject and low.startswith(tuple(
                w for spec in RELATIONS.values()
                for w in (spec["words"] if isinstance(spec, Mapping) else spec))):
            program = subject
            implicit = True
        if program is None:
            continue
        # EVERY relation the sentence can name is a candidate, provided the program is the
        # SUBJECT of the verb. "bzip2, a block-sorting file compressor" names both `sorts` and
        # `compresses`; the witness decides which is true, and the extractor refuses to choose
        # by taste. This is the opposite of a parser that guesses one reading and is wrong
        # silently. But a program that merely appears near a relation word is not a claim:
        # `The locale affects sort order` names sort, and says nothing about what sort does.
        for relation in _all_relations(low):
            words = RELATIONS[relation]["words"]
            if not implicit and _subject_distance(low, program, words) is None:
                continue
            relation = _refine_relation(relation, kind)
            out.append({
                "schema": SCHEMA,
                "sentence": sentence["text"],
                "line": sentence["line"],
                "program": program,
                "relation": relation,
                "observable": RELATIONS[relation]["observable"],
                "object_kind": kind,
                "predicate": RELATIONS[relation]["predicate"],
                "qualifier": _qualifier_of(sentence["text"]),
                "authority": "NONE__CANDIDATE_NOT_ADMITTED",
            })
            if len(out) >= max_claims:
                return out
    return out


# --------------------------------------------------------------------------- #
# 2. THE ROOM: make an object of a kind, read an observable
# --------------------------------------------------------------------------- #

def _bound_child() -> None:  # pragma: no cover - runs in the child process
    """Bound the child's output FILE SIZE and CPU, not just its wall clock.

    `capture_output=True` buffers the whole stream before truncating it, so `yes file` (a
    program in the fleet) filled memory for ten seconds and the kernel killed the measurement
    with SIGKILL. A resource limit in the child stops the writer at the source.
    """
    import resource
    limit = 8 * 1024 * 1024
    resource.setrlimit(resource.RLIMIT_FSIZE, (limit, limit))
    resource.setrlimit(resource.RLIMIT_CPU, (20, 20))


def _run(argv: Sequence[str], cwd: str | pathlib.Path, *, timeout: float = 10.0,
         stdin: bytes | None = None) -> dict[str, Any]:
    """One bounded execution. stdin is closed unless bytes are supplied."""
    started = time.perf_counter()
    try:
        with tempfile.TemporaryFile() as out, tempfile.TemporaryFile() as err:
            done = subprocess.run([str(a) for a in argv], cwd=str(cwd),
                                  input=stdin,
                                  stdin=None if stdin is not None else subprocess.DEVNULL,
                                  stdout=out, stderr=err, timeout=timeout,
                                  preexec_fn=_bound_child)
            out.seek(0)
            captured_out = out.read(65536)
            err.seek(0)
            captured_err = err.read(65536)
    except (OSError, subprocess.SubprocessError) as error:
        return {"exit": None, "stdout": "", "stderr": "", "error": type(error).__name__,
                "seconds": round(time.perf_counter() - started, 4)}
    return {"exit": done.returncode,
            "stdout": captured_out.decode("utf-8", "replace"),
            "stderr": captured_err.decode("utf-8", "replace"),
            "seconds": round(time.perf_counter() - started, 4)}


def _which(program: str) -> str | None:
    return shutil.which(program)


_WORDS = ("delta", "alpha", "gamma", "beta", "omega", "zeta", "kappa", "iota", "eta", "theta")


def _write_text(path: pathlib.Path, variant: int) -> str:
    """A byte-stable text object that is UNSORTED, COMPRESSIBLE and different by variant.

    Three properties, each one load-bearing for a different claim, and each one easy to lose:
    a body of repeated identical lines is trivially sorted, so `sort sorts the lines` can never
    be true of it; a short body grows under gzip, so `gzip compresses` can never be true of it;
    and a body that ignores the variant makes every room the same room, so the second-room gate
    passes without testing anything. The words start out of order on purpose.
    """
    rotate = (variant * 3) % len(_WORDS)
    order = _WORDS[rotate:] + _WORDS[:rotate]
    body = "".join(f"{word} {index:04d} alpha beta gamma delta epsilon zeta eta theta\n"
                   for index, word in enumerate(order * 6))
    path.write_text(body, encoding="utf-8")
    return body


def make_object(kind: str, root: pathlib.Path, variant: int = 0,
                program: str = "") -> dict[str, Any]:
    """Make an object of a kind with a producer this machine has, and say what was made.

    The producer is a room preparation, not a claim about any program. A kind whose producer
    is absent is an honest `NO_PRODUCER`, not a quiet substitute.
    """
    root.mkdir(parents=True, exist_ok=True)
    producer = KIND_PRODUCER.get(kind)
    if not producer:
        return {"ok": False, "reason": "NO_PRODUCER_FOR_KIND", "kind": kind}
    producer_program = program
    if producer == "text":
        name = f"object-{variant}.txt"
        body = _write_text(root / name, variant)
        return {"ok": True, "kind": kind, "input": name, "output": name,
                "original": body, "members": [], "producer": "write_text"}
    if producer == "archive":
        # the archive speaks the FORMAT the claimed program speaks: a zip program cannot read
        # the tar this room would otherwise make, and refusing `unzip extracts an archive`
        # because the room handed it a tar would be a refusal about the room, not the program
        if str(producer_program).lower() in ("zip", "unzip"):
            return _make_zip(kind, root, variant)
        name = f"object-{variant}.tar"
        member = f"member-{variant}.txt"
        _write_text(root / member, variant)
        done = _run(["tar", "-cf", name, member], root)
        if done["exit"] != 0:
            return {"ok": False, "reason": "PRODUCER_FAILED", "kind": kind,
                    "error": done["stderr"][:200]}
        return {"ok": True, "kind": kind, "input": name, "output": name,
                "original": (root / member).read_text(encoding="utf-8"),
                "members": [member], "producer": "tar"}
    if producer == "zip":
        return _make_zip(kind, root, variant)
    if producer == "compressed":
        name = f"object-{variant}.txt.gz"
        source = f"object-{variant}.txt"
        body = _write_text(root / source, variant)
        compressor = {"bzip2": "bzip2", "xz": "xz", "gzip": "gzip"}.get(
            str(producer_program).lower(), "gzip")
        if compressor == "bzip2":
            name = f"object-{variant}.txt.bz2"
        elif compressor == "xz":
            name = f"object-{variant}.txt.xz"
        # bytes, not text: `_run` decodes stdout, and decoding a compressed stream destroys it.
        # That is why `gzip -t object.gz` said "not in gzip format" about a file gzip made.
        import subprocess as _subprocess
        made = _subprocess.run([compressor, "-c", source], cwd=str(root),
                               capture_output=True, timeout=20)
        if made.returncode != 0 or not made.stdout:
            return {"ok": False, "reason": "PRODUCER_FAILED", "kind": kind,
                    "error": made.stderr.decode("utf-8", "replace")[:200]}
        (root / name).write_bytes(made.stdout)
        # the source must not sit beside the compressed object: decompressing would collide
        # with it (`bzip2: Output file object-0.txt already exists`)
        (root / source).unlink()
        return {"ok": True, "kind": kind, "input": name, "output": name,
                "original": body, "members": [], "producer": compressor + " -c"}
    if producer == "zip":
        name = f"object-{variant}.zip"
        member = f"member-{variant}.txt"
        _write_text(root / member, variant)
        done = _run(["zip", "-q", name, member], root)
        if done["exit"] != 0:
            return {"ok": False, "reason": "PRODUCER_FAILED", "kind": kind,
                    "error": done["stderr"][:200]}
        return {"ok": True, "kind": kind, "input": name, "output": name,
                "original": (root / member).read_text(encoding="utf-8"),
                "members": [member], "producer": "zip"}
    if producer == "directory":
        name = f"object-{variant}.dir"
        (root / name).mkdir(exist_ok=True)
        _write_text(root / name / f"member-{variant}.txt", variant)
        return {"ok": True, "kind": kind, "input": name, "output": name,
                "original": "", "members": [f"member-{variant}.txt"], "producer": "mkdir"}
    if producer in ("json", "xml", "csv"):
        name = f"object-{variant}.{producer}"
        bodies = {"json": '{"a": 1, "b": [2, 3]}\n',
                  "xml": "<a><b/></a>\n",
                  "csv": "a,b\n1,2\n"}
        body = bodies[producer]
        (root / name).write_text(body, encoding="utf-8")
        return {"ok": True, "kind": kind, "input": name, "output": name,
                "original": body, "members": [], "producer": "write_" + producer}
    if producer == "database":
        name = f"object-{variant}.db"
        try:
            connection = sqlite3.connect(root / name)
            connection.execute("create table t(x)")
            connection.executemany("insert into t values (?)",
                                   [(f"row-{variant}-{i}",) for i in range(3)])
            connection.commit()
            connection.close()
        except Exception as error:  # noqa: BLE001
            return {"ok": False, "reason": "PRODUCER_FAILED", "kind": kind,
                    "error": str(error)[:200]}
        return {"ok": True, "kind": kind, "input": name, "output": name,
                "original": "row-0\nrow-1\nrow-2\n", "members": [], "producer": "sqlite3"}
    if producer == "image":
        convert = _which("convert")
        if not convert:
            return {"ok": False, "reason": "NO_PRODUCER_FOR_KIND", "kind": kind}
        name = f"object-{variant}.png"
        done = _run([convert, "-size", "8x8", "xc:red", name], root)
        if done["exit"] != 0:
            return {"ok": False, "reason": "PRODUCER_FAILED", "kind": kind}
        return {"ok": True, "kind": kind, "input": name, "output": name,
                "original": "", "members": [], "producer": "convert"}
    if producer == "certificate":
        openssl = _which("openssl")
        if not openssl:
            return {"ok": False, "reason": "NO_PRODUCER_FOR_KIND", "kind": kind}
        name = f"object-{variant}.pem"
        done = _run([openssl, "req", "-x509", "-newkey", "rsa:2048", "-keyout", name,
                     "-out", f"object-{variant}-cert.pem", "-days", "1", "-nodes",
                     "-subj", "/CN=x"], root, timeout=30)
        if done["exit"] != 0:
            return {"ok": False, "reason": "PRODUCER_FAILED", "kind": kind}
        return {"ok": True, "kind": kind, "input": name, "output": name,
                "original": "", "members": [], "producer": "openssl"}
    if producer == "key":
        openssl = _which("openssl")
        if not openssl:
            return {"ok": False, "reason": "NO_PRODUCER_FOR_KIND", "kind": kind}
        name = f"object-{variant}.key"
        done = _run([openssl, "genpkey", "-algorithm", "RSA", "-pkeyopt",
                     "rsa_keygen_bits:2048", "-out", name], root, timeout=30)
        if done["exit"] != 0:
            return {"ok": False, "reason": "PRODUCER_FAILED", "kind": kind}
        return {"ok": True, "kind": kind, "input": name, "output": name,
                "original": "", "members": [], "producer": "openssl"}
    if producer == "patch":
        left, right = f"left-{variant}.txt", f"right-{variant}.txt"
        _write_text(root / left, variant)
        _write_text(root / right, variant + 1)
        name = f"object-{variant}.patch"
        done = _run(["diff", "-u", left, right], root)
        if done["exit"] not in (0, 1) or not done["stdout"]:
            return {"ok": False, "reason": "PRODUCER_FAILED", "kind": kind}
        (root / name).write_text(done["stdout"], encoding="utf-8")
        target = (root / right).read_text(encoding="utf-8")
        # `base` is the file the patch is applied to and `target` is what it must become: a
        # patch is a RELATION between two files, and an object that names only the diff cannot
        # be applied by anyone.
        return {"ok": True, "kind": kind, "input": name, "output": name,
                "original": target, "base": left, "target": right,
                "members": [left, right], "producer": "diff"}
    if producer == "commit":
        git = _which("git")
        if not git:
            return {"ok": False, "reason": "NO_PRODUCER_FOR_KIND", "kind": kind}
        name = f"object-{variant}.git"
        done = _run([git, "init", "-q", name], root)
        if done["exit"] != 0:
            return {"ok": False, "reason": "PRODUCER_FAILED", "kind": kind}
        _write_text(root / name / "seed.txt", variant)
        for argv in (["git", "add", "-A"], ["git", "-c", "user.name=census",
                                             "-c", "user.email=c@c", "commit", "-qm", "seed"]):
            _run(argv, root / name)
        return {"ok": True, "kind": kind, "input": name, "output": name,
                "original": "", "members": [], "producer": "git"}
    return {"ok": False, "reason": "NO_PRODUCER_FOR_KIND", "kind": kind}


def _make_zip(kind: str, root: pathlib.Path, variant: int) -> dict[str, Any]:
    """A zip archive, made by the machine's own zip. A kind the room cannot make is refused."""
    name = f"object-{variant}.zip"
    member = f"member-{variant}.txt"
    _write_text(root / member, variant)
    done = _run(["zip", "-q", name, member], root)
    if done["exit"] != 0:
        return {"ok": False, "reason": "PRODUCER_FAILED", "kind": kind,
                "error": (done.get("stderr") or done.get("stdout") or "")[:200]}
    return {"ok": True, "kind": kind, "input": name, "output": name,
            "original": (root / member).read_text(encoding="utf-8"),
            "members": [member], "producer": "zip"}


def _digest(path: pathlib.Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()[:16]
    except OSError:
        return None


def read_observable(observable: str, root: pathlib.Path, obj: Mapping[str, Any],
                    action: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Read one observable with a read-only program the machine already has.

    The reading is a value, not a truth: the predicate decides what the value means. A sensor
    that cannot run returns `error`, and the gate refuses; it never guesses.
    """
    name = obj.get("output") or obj.get("input") or ""
    path = root / name if name else None
    if observable in ("stdout", "exit") and action is not None:
        return {"value": action.get("stdout", "") if observable == "stdout" else action.get("exit"),
                "raw": action.get("stdout", "") if observable == "stdout" else "",
                "exit": action.get("exit"), "sensor": "capture"}
    if observable == "size":
        if not path or not path.exists():
            return {"error": "OBJECT_ABSENT", "sensor": "stat"}
        done = _run(["stat", "-c", "%s", name], root)
        return {"value": _num(done["stdout"].strip()), "raw": done["stdout"].strip(),
                "exit": done["exit"], "sensor": "stat"}
    if observable in ("content", "checksum", "name", "type", "member", "row", "value"):
        if not path or not path.exists():
            return {"error": "OBJECT_ABSENT", "sensor": observable}
        if observable == "content":
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError as error:
                return {"error": type(error).__name__, "sensor": "cat"}
            return {"value": text, "raw": text[:1000], "sensor": "cat"}
        if observable == "checksum":
            done = _run(["sha256sum", name], root)
            return {"value": done["stdout"].split()[0] if done["stdout"].split() else None,
                    "raw": done["stdout"].strip(), "exit": done["exit"], "sensor": "sha256sum"}
        if observable == "name":
            return {"value": name, "raw": name, "sensor": "basename"}
        if observable == "type":
            done = _run(["file", "-b", name], root)
            return {"value": done["stdout"].strip(), "raw": done["stdout"].strip(),
                    "exit": done["exit"], "sensor": "file"}
        if observable == "member":
            done = _run(["tar", "-tf", name], root)
            return {"value": done["stdout"].strip(), "raw": done["stdout"].strip(),
                    "exit": done["exit"], "sensor": "tar -tf"}
        if observable in ("row", "value"):
            try:
                connection = sqlite3.connect(path)
                rows = connection.execute("select x from t order by x").fetchall()
                connection.close()
            except Exception as error:  # noqa: BLE001
                return {"error": str(error)[:120], "sensor": "sqlite3"}
            values = [str(row[0]) for row in rows]
            return {"value": "\n".join(values), "raw": "\n".join(values)[:1000],
                    "sensor": "sqlite3"}
    if observable in ("lines", "count"):
        if not path or not path.exists():
            return {"error": "OBJECT_ABSENT", "sensor": "wc"}
        done = _run(["wc", "-l", name], root)
        return {"value": _num(done["stdout"].split()[0]) if done["stdout"].split() else None,
                "raw": done["stdout"].strip(), "exit": done["exit"], "sensor": "wc -l"}
    if observable == "order":
        if not path or not path.exists():
            return {"error": "OBJECT_ABSENT", "sensor": "sort -c"}
        done = _run(["sort", "-c", name], root)
        return {"value": done["exit"], "raw": done["stderr"].strip()[:200],
                "exit": done["exit"], "sensor": "sort -c"}
    if observable == "valid":
        if not path or not path.exists():
            return {"error": "OBJECT_ABSENT", "sensor": "valid"}
        # The FORMAT is read from the object's BYTES, not inferred from its name. A zip file
        # named `.tar` is a zip file, and a sensor that trusts the suffix would run `tar -tf`
        # on it and report a valid archive as invalid -- a false refusal caused by the sensor.
        # (This machine has no `file(1)`; reading four magic bytes needs no program at all.)
        kind_text = _sniff_format(root / name)
        if kind_text == "zip":
            done = _run(["unzip", "-t", name], root)
            return {"value": done["exit"], "raw": done["stdout"].strip()[:200],
                    "exit": done["exit"], "sensor": "unzip -t", "format": "zip"}
        if kind_text == "tar":
            done = _run(["tar", "-tf", name], root)
            return {"value": done["exit"], "raw": done["stdout"].strip()[:200],
                    "exit": done["exit"], "sensor": "tar -tf", "format": "tar"}
        if kind_text == "gzip":
            done = _run(["gzip", "-t", name], root)
            return {"value": done["exit"], "raw": done["stderr"].strip()[:200],
                    "exit": done["exit"], "sensor": "gzip -t", "format": "gzip"}
        return {"value": None, "raw": "NO_CHECK_FOR_FORMAT:" + kind_text.strip()[:60],
                "exit": None, "sensor": "none", "format": kind_text.strip()[:40]}
    if observable == "exists":
        return {"value": bool(path and path.exists()), "raw": str(bool(path and path.exists())),
                "sensor": "os.path.exists"}
    return {"error": "NO_SENSOR_FOR_OBSERVABLE", "sensor": observable}


# --------------------------------------------------------------------------- #
# 3. THE ACTION: what the program does to the object
# --------------------------------------------------------------------------- #

_FLAG_ROW = re.compile(r"^\s*-{1,2}[A-Za-z0-9]")


def _flag_rows(help_text: str) -> list[tuple[str, str]]:
    """Every (flags, description) row a help page states, one row per flag.

    A help page is a TABLE, and its rows are separated by two or more spaces. Reading it one
    physical line at a time is wrong twice over: a two-column page (`unzip`, `zip`) puts two
    flags on one line, and a one-column page wraps a description onto the next. The first
    produced `-x` for "extract files into exdir" and `-Z` for "list"; the second is why the
    row is rejoined before it is split. Two or more spaces is the delimiter the page itself
    uses, so it is the one read here.
    """
    rows: list[tuple[str, str]] = []
    for line in (help_text or "").splitlines():
        if not _FLAG_ROW.match(line):
            continue
        parts = [part for part in re.split(r"\s{2,}", line.strip()) if part]
        index = 0
        while index < len(parts):
            flags = parts[index]
            description = parts[index + 1] if index + 1 < len(parts) else ""
            if _FLAG_ROW.match(flags):
                rows.append((flags, description))
            index += 2
    return rows


def _flag_for(role: str, help_text: str) -> str | None:
    """The flag the program's own help associates with a role, read from its own words.

    The role's words are matched against the DESCRIPTION, and the flag comes from the same
    row. A program whose help does not name the role gets no flag -- the bare program is then
    the action, and the witness measures whether that is true.
    """
    words = {
        "decompress": ("decompress", "uncompress", "unpack"),
        "extract": ("extract", "decompress", "unpack"),
        "list": ("list", "show", "display"),
        "create": ("create", "make", "build"),
        "check": ("test", "check", "verify"),
        "lines": ("lines", "line"),
        "output": ("output", "stdout", "standard output"),
        "recursive": ("recursive", "recurse", "subdirectories"),
    }.get(role, (role,))
    long_hit = short_hit = None
    for flags, description in _flag_rows(help_text):
        low = description.lower()
        if not any(word in low for word in words):
            continue
        # `unzip -p` is "extract files to pipe": extraction to a stream is not extraction
        # into a directory, and taking it made the witness write the archive to stdout.
        if role in ("extract", "decompress") and re.search(r"\bpipe\b|standard output", low):
            continue
        for candidate in re.findall(r"--[a-z][a-z0-9-]*", flags):
            if long_hit is None:
                long_hit = candidate
        for candidate in re.findall(r"(?<![\w-])-[a-zA-Z](?![\w-])", flags):
            if short_hit is None:
                short_hit = candidate
    return long_hit or short_hit


def _suffix_from_help(help_text: str) -> str | None:
    """The output suffix a compressor names on its own page (`.gz`, `.xz`, `.bz2`).

    Read, not assumed: `xz` says `.xz and .lzma`, `bzip2` says `.bz2`, `gzip` says `.gz`.
    A page that names none keeps the default, and the witness measures whether it is right.
    """
    found = re.findall(r"\.(gz|xz|bz2|lzma|z|zip)\b", help_text or "", re.IGNORECASE)
    return ("." + found[0].lower()) if found else None


def _usage_positionals(help_text: str, program: str) -> list[str]:
    """The operand slots the program's own usage line declares, in order.

    Read, not assumed: `tar` declares `[FILE]...` and keeps the archive in `-f`, `unzip`
    declares `file[.zip]` and keeps the extraction directory in `-d`. A grammar that hardcodes
    one of those is a grammar that is wrong about the other, which is exactly how `unzip
    extracts an archive` came back FALSE: the action had been built with tar's operands.
    """
    try:
        from canonical.runtime import tool_census_v1 as census
    except Exception:  # noqa: BLE001
        return []
    try:
        return [str(x) for x in census.parse_usage_positionals(help_text or "", program)]
    except Exception:  # noqa: BLE001
        return []


def _archive_operand(help_text: str, program: str, obj_name: str) -> list[str]:
    """How this program wants the archive named: as a positional, or through a flag."""
    positionals = _usage_positionals(help_text, program)
    # `[FILE]...` in tar's usage is the MEMBER, not the archive: the archive is `-f`. A slot
    # that names an archive (`file[.zip]`, `zipfile`, `archive`) is the archive.
    if any(re.search(r"zip|tar|archive|tgz", slot, re.IGNORECASE) for slot in positionals):
        return [obj_name]
    # The synopsis is the line that BEGINS with the program's name and has a bracket. A flag
    # row can contain a bracket and an archive word too (`--totals[=SIGNAL] ... archive`), and
    # taking that row made tar treat its archive as a positional.
    synopsis = next((line for line in (help_text or "").splitlines()
                     if line.strip().lower().startswith(program.lower())
                     and "[" in line
                     and re.search(r"zipfile|\.zip\b|\.tar\b|archive", line, re.IGNORECASE)), "")
    if synopsis:
        return [obj_name]
    return ["-f", obj_name]


#: The only spellings in use for "the directory an extractor writes into". Matching on the
#: DESCRIPTION instead picked `--recursive-unlink` ("empty hierarchies prior to extracting
#: directory"), which is not a directory flag at all.
_DIRECTORY_FLAGS = ("--directory", "-C", "-d", "--extract-dir", "--target-directory")


def _outdir_flag(help_text: str, program: str) -> tuple[str, bool]:
    """(flag, takes_a_value) for the directory an extractor writes into, from its own help."""
    for flags, description in _flag_rows(help_text):
        low = description.lower()
        if not re.search(r"extract|decompress|unpack|directory", low):
            continue
        for spelling in _DIRECTORY_FLAGS:
            if re.search(r"(?<![\w-])" + re.escape(spelling) + r"(?![\w-])", flags):
                return spelling, True
    return "-C", True


def _stable_suffix(obj: Mapping[str, Any]) -> str:
    """A stable name-part derived from the object, not from the sentence.

    The output name used to be `hash(sentence)`, so the same relation re-verified in a new room
    built a different argv than the one that had been admitted -- the witness could not be
    replayed from the store, which is the one thing a stored witness is for.
    """
    return hashlib.sha256(str(obj.get("input") or "").encode("utf-8")).hexdigest()[:6]


def action_for(claim: Mapping[str, Any], obj: Mapping[str, Any], root: pathlib.Path,
               help_text: str = "", role_flag: str | None = None) -> dict[str, Any]:
    """The argv that performs the claim's relation on the object, built from the relation.

    The relation is a closed class of operations, and the flag is read from the program's own
    help when the page names it. A program whose page does not name the flag is run bare, and
    the witness decides whether the bare program does the relation -- never assumed.
    """
    program = str(claim.get("program") or "")
    relation = str(claim.get("relation") or "")
    kind = str(claim.get("object_kind") or obj.get("kind") or "")
    if role_flag is None and not help_text:
        # re-verification at use: the flag the relation was admitted with is part of the
        # relation, and the page it was read from may not be on this machine
        stored = (claim.get("witness") or {}).get("role_flag")
        role_flag = stored if stored is not None else None
    inp = str(obj.get("input") or "")
    out = str(obj.get("output") or "")
    bare = [program]
    if relation in ("compresses", "grows"):
        # The program names its own output (`.gz`, `.bz2`, `.xz`, or none): the room is read
        # after the run to find which file appeared. Guessing the suffix from the program's
        # name made `bzip2` produce `object.txt.gz` and then look for a file that never existed.
        return {"argv": [program, inp], "reads": inp, "writes": out,
                "output_name": None, "role_flag": ""}
    if relation == "decompresses":
        flag = role_flag if role_flag is not None else _flag_for("decompress", help_text)
        argv = [program] + ([flag] if flag else []) + [inp]
        # the decompressor names its own output, exactly as the compressor does
        return {"argv": argv, "reads": inp, "writes": out, "output_name": None,
                "role_flag": flag or ""}
    if relation == "archives":
        flag = role_flag if role_flag is not None else _flag_for("create", help_text)
        archive = (f"made-{_stable_suffix(obj)}"
                   + (_suffix_from_help(help_text) or ".tar"))
        argv = [program] + ([flag] if flag else []) + _archive_operand(help_text, program, archive)
        if kind in ("directory", "repository"):
            recurse = _flag_for("recursive", help_text)
            argv += ([recurse] if recurse else []) + [inp]
        else:
            argv += [inp]
        return {"argv": argv, "reads": inp, "writes": out, "output_name": archive,
                "role_flag": flag or ""}
    if relation == "extracts":
        flag = role_flag if role_flag is not None else _flag_for("extract", help_text)
        outdir = f"out-{_stable_suffix(obj)}"
        directory_flag, takes_value = _outdir_flag(help_text, program)
        if flag == directory_flag:
            # `unzip -d exdir archive`: the extract flag IS the directory flag
            argv = [program, directory_flag, outdir] + _archive_operand(help_text, program, inp)
        else:
            argv = ([program] + ([flag] if flag else [])
                    + _archive_operand(help_text, program, inp)
                    + [directory_flag] + ([outdir] if takes_value else []))
        member = (obj.get("members") or [None])[0]
        output_name = str(pathlib.Path(outdir) / str(member)) if member else outdir
        return {"argv": argv, "reads": inp, "writes": outdir, "output_name": output_name,
                "pre": ["mkdir", "-p", outdir], "role_flag": flag or ""}
    if relation == "lists":
        flag = role_flag if role_flag is not None else _flag_for("list", help_text)
        argv = [program] + ([flag] if flag else []) + _archive_operand(help_text, program, inp)
        return {"argv": argv, "reads": inp, "writes": out, "output_name": inp,
                "role_flag": flag or ""}
    if relation == "sorts":
        output_name = inp + RELATION_OUTPUT["sorts"]
        return {"argv": [program, inp, "-o", output_name], "reads": inp, "writes": output_name,
                "output_name": output_name, "role_flag": ""}
    if relation == "reverses":
        output_name = inp + ".reversed"
        return {"argv": [program, inp], "reads": inp, "writes": out,
                "output_name": output_name, "capture_to": output_name}
    if relation == "creates":
        output_name = f"made-{_stable_suffix(obj)}.out"
        return {"argv": [program, output_name], "reads": inp, "writes": output_name,
                "output_name": output_name}
    if relation == "removes":
        return {"argv": [program, inp], "reads": inp, "writes": inp, "output_name": inp}
    if relation == "counts":
        flag = _flag_for("lines", help_text)
        argv = [program] + ([flag] if flag else ["-l"]) + [inp]
        return {"argv": argv, "reads": inp, "writes": out, "output_name": inp}
    if relation == "checks":
        flag = role_flag if role_flag is not None else _flag_for("check", help_text)
        argv = [program] + ([flag] if flag else []) + [inp]
        return {"argv": argv, "reads": inp, "writes": out, "output_name": inp}
    if relation == "contains":
        return {"argv": [program, "-F", "alpha", inp], "reads": inp, "writes": out,
                "output_name": inp, "needle": "alpha"}
    if relation == "searches":
        return {"argv": [program, "alpha", inp], "reads": inp, "writes": out,
                "output_name": inp, "needle": "alpha"}
    if relation == "encodes":
        return {"argv": [program, inp], "reads": inp, "writes": out, "output_name": inp}
    if relation == "decodes":
        flag = _flag_for("decompress", help_text)
        argv = [program] + ([flag] if flag else []) + [inp]
        return {"argv": argv, "reads": inp, "writes": out, "output_name": inp,
                "role_flag": flag or ""}
    if relation in ("converts", "prints", "computes", "reformats"):
        return {"argv": [program, inp], "reads": inp, "writes": out, "output_name": inp}
    if relation == "compares":
        other = f"other-{_stable_suffix(obj)}.txt"
        # not a second variant of the room (that can equal the first by construction) but the
        # object's own body with one line appended: different in every room, by construction
        body = str(obj.get("original") or "")
        (root / other).write_text(body + "the one line that differs\n", encoding="utf-8")
        return {"argv": [program, inp, other], "reads": inp, "writes": out,
                "output_name": inp}
    if relation == "applies":
        base = str(obj.get("base") or "")
        if not base:
            return {"argv": [program], "reads": inp, "writes": "", "output_name": ""}
        return {"argv": [program, base, inp], "reads": inp, "writes": base,
                "output_name": base}
    if relation == "copies":
        output_name = f"copy-{_stable_suffix(obj)}.txt"
        return {"argv": [program, inp, output_name], "reads": inp, "writes": output_name,
                "output_name": output_name}
    if relation == "renames":
        output_name = f"moved-{_stable_suffix(obj)}.txt"
        return {"argv": [program, inp, output_name], "reads": inp, "writes": output_name,
                "output_name": output_name, "removes_source": True}
    if relation == "runs":
        return {"argv": [program], "reads": inp, "writes": out, "output_name": inp}
    return {"argv": bare, "reads": inp, "writes": out, "output_name": inp}


# --------------------------------------------------------------------------- #
# 4. THE WITNESS: run the claim, run the wrong version, compare
# --------------------------------------------------------------------------- #

@dataclass
class WitnessResult:
    claim: dict[str, Any]
    verdict: str
    reason: str | None
    gates: dict[str, bool]
    readings: dict[str, Any] = field(default_factory=dict)
    relation: dict[str, Any] | None = None


def _sniff_format(path: pathlib.Path) -> str:
    """The container format of a file, from its magic bytes. `file(1)` is not installed here."""
    try:
        head = path.read_bytes()[:600]
    except OSError:
        return ""
    if head.startswith(b"PK\x03\x04") or head.startswith(b"PK\x05\x06"):
        return "zip"
    if head.startswith(b"\x1f\x8b"):
        return "gzip"
    if head.startswith(b"BZh"):
        return "bzip2"
    if head.startswith(b"\xfd7zXZ\x00"):
        return "xz"
    if len(head) > 262 and head[257:262] == b"ustar":
        return "tar"
    return ""


def _read(observable: str, root: pathlib.Path, obj: Mapping[str, Any],
          action: Mapping[str, Any] | None = None) -> Any:
    reading = read_observable(observable, root, obj, action)
    return reading.get("value") if "error" not in reading else None


# The program that does NOTHING to an observable. A claim about a program must be false of the
# program that does nothing to the thing the claim is about; if it is true of `cat` as well,
# then the claim is not about the program, it is about the object or about the sensor, and no
# witness built from it can teach anything. `prints` is true of `cat` on a file and false of
# `true` on a file, so it separates; `contains` is true of both, so it does not.
NULL_PROGRAM: dict[str, str] = {
    "order": "cat", "content": "cat", "count": "cat", "lines": "cat", "size": "cat",
    "checksum": "cat", "stdout": "true", "exists": "true", "valid": "true", "exit": "true",
}


def _run_witness(claim: Mapping[str, Any], root: pathlib.Path, variant: int,
                 help_text: str = "", null_program: str | None = None) -> dict[str, Any]:
    """Run one claim on one room and return the readings the predicate needs.

    With `null_program`, run the program that does nothing instead of the claimed one, and
    return the same shape of readings. Same object, same sensor, same predicate: only the
    program differs, so a difference in the verdict is attributable to the program.
    """
    obj = make_object(str(claim.get("object_kind") or ""), root, variant,
                      program=str(claim.get("program") or ""))
    if not obj.get("ok"):
        return {"ok": False, "reason": obj.get("reason"), "detail": obj}
    if null_program:
        # The null program reads the SAME object and is measured by the SAME sensor, so the
        # only difference between the two runs is the program. A relation whose whole claim is
        # "this program CREATES something" must be measured against a null that creates
        # nothing -- reading the input instead would make `cp copies a file` true of `cat`.
        creates = str(claim.get("relation")) in (
            "creates", "archives", "copies", "renames", "extracts", "removes")
        action = {"argv": [null_program, str(obj["input"])], "reads": obj["input"],
                  "output_name": (None if creates else obj["input"]),
                  "role_flag": "", "pre": None}
    else:
        action = action_for(claim, obj, root, help_text=help_text,
                            role_flag=(claim.get("witness") or {}).get("role_flag"))
    pre = action.get("pre")
    if pre:
        done = _run(pre, root)
        if done["exit"] != 0:
            return {"ok": False, "reason": "PRE_FAILED", "detail": done}
    before_obj = {"input": action.get("reads"), "output": action.get("reads"),
                  "kind": claim.get("object_kind")}
    before = _read(str(claim.get("observable") or ""), root, before_obj)
    before_exists = bool(action.get("reads") and (root / str(action.get("reads"))).exists())
    present_before = {entry.name for entry in root.iterdir()} if root.exists() else set()
    run = _run(action["argv"], root)
    output_name = action.get("output_name")
    if not output_name:
        # the program named its own output; the room is the authority on what it is
        created = sorted(entry.name for entry in root.iterdir()
                         if entry.name not in present_before) if root.exists() else []
        output_name = created[0] if created else None
        action = dict(action, output_name=output_name)
    after_obj = {"input": output_name, "output": output_name,
                 "kind": claim.get("object_kind")}
    after_exists = bool(output_name and (root / str(output_name)).exists())
    source_exists = bool(action.get("reads") and (root / str(action.get("reads"))).exists())
    # the object the sensor read, digested BEFORE the sensor and AFTER it, for G6. The action
    # may legitimately change the object; the sensor may not. This is the order that measures
    # the sensor rather than the action.
    watched = output_name or action.get("reads")
    before_sensor = _digest(root / str(watched)) if watched else None
    after = _read(str(claim.get("observable") or ""), root, after_obj, run)
    after_sensor = _digest(root / str(watched)) if watched else None
    corrupt_exit = None
    if claim.get("relation") == "checks" and action.get("output_name"):
        # A CHECK IS A DISCRIMINATION. `tar --list` exiting zero on a valid archive says nothing
        # about whether it can tell a broken one; the program that does nothing exits zero on
        # both. So the same argv is run against a corrupt copy of the same object, and the
        # verdict is the DIFFERENCE between the two exits.
        corrupt = f"corrupt-{output_name or action.get('reads')}"
        source = root / str(output_name or action.get("reads") or "")
        try:
            payload = source.read_bytes()
            (root / corrupt).write_bytes(payload[: max(1, len(payload) // 2)])
        except OSError:
            payload = b""
        argv = [str(x).replace(str(source.name), corrupt) for x in action["argv"]]
        corrupt_exit = _run(argv, root).get("exit")
    # The qualifier is an order over what the program PRODUCED. A program that writes a file
    # (`sort -o out`) produces nothing on stdout, so the order is read from the file it named.
    produced = str(run.get("stdout") or "")
    if not produced.strip() and output_name and (root / str(output_name)).is_file():
        try:
            produced = (root / str(output_name)).read_text(encoding="utf-8", errors="replace")
        except OSError:
            produced = ""
    stdout_lines = [line for line in produced.splitlines() if line.strip()]
    numeric = []
    for line in stdout_lines:
        head = line.split()[0] if line.split() else ""
        numeric.append(_num(head))
    stdout_numeric = bool(numeric) and all(value is not None for value in numeric)
    ordered = ""
    if len(stdout_lines) >= 2:
        keys = numeric if stdout_numeric else stdout_lines
        if keys == sorted(keys):
            ordered = "ascending"
        elif keys == sorted(keys, reverse=True):
            ordered = "descending"
    readings = {
        "before": before,
        "stdout_order": ordered,
        "stdout_numeric": stdout_numeric,
        "after": after,
        "stdout": run.get("stdout", ""),
        "exit": run.get("exit"),
        "before_exists": before_exists,
        "after_exists": after_exists,
        "source_exists": source_exists,
        "original": obj.get("original"),
        # `lists` reads the member's NAME from stdout; `extracts` reads the member's BODY
        # from the file. The needle is the thing the claim says will be there.
        "needle": ((obj.get("members") or ["alpha"])[0]
                   if claim.get("relation") == "lists"
                   else (obj.get("original") or "alpha")),
        # the content a patch must produce is the target file the room was made from
        "target": (obj.get("target") or ""),
        "expected": (len(str(obj.get("original") or "").splitlines())
                     if claim.get("observable") in ("count", "lines")
                     or claim.get("relation") == "counts" else None),
        "reversed": False,
        "run": run,
        "obj": obj,
        "action": action,
        "corrupt_exit": corrupt_exit,
        "sensor_wrote": bool(watched and before_sensor and after_sensor
                             and before_sensor != after_sensor),
    }
    # `content_equals_original` for a decompressor is about the OUTPUT content; the producer's
    # original is the text that was compressed.
    if claim.get("relation") == "decompresses":
        readings["original"] = obj.get("original")
    # `reversed` is computed from the sortedness of the reversed content, not asserted.
    if claim.get("relation") == "reverses":
        path = root / str(action.get("output_name") or "")
        if path.exists():
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
            readings["reversed"] = lines == sorted(lines, reverse=True)
    return {"ok": True, "readings": readings}


def _present(value: Any) -> bool:
    """A reading that exists. `0` is a value; `None` and `""` are absent."""
    return value is not None and str(value) != ""


#: How a qualifier is tested. Each entry is a read-only check over the program's own output;
#: there is no entry for a qualifier no read-only sensor can decide, and such a qualifier is
#: recorded as NOT_WITNESSED rather than stored as if it had been verified.
_QUALIFIER_SENSOR: dict[str, str] = {
    "alphabetically": "order_alphabetical",
    "lexicographically": "order_alphabetical",
    "numerically": "order_numerical",
    "in ascending order": "order_ascending",
    "in descending order": "order_descending",
    "in reverse order": "order_descending",
}


def _qualifier_verdict(qualifier: str, readings: Mapping[str, Any]) -> str:
    """`WITNESSED`, `CONTRADICTED`, or `NOT_WITNESSED` -- never a silent drop."""
    if not qualifier:
        return "NONE"
    sensor = _QUALIFIER_SENSOR.get(qualifier)
    if not sensor:
        return "NOT_WITNESSED"
    verdict = _predicate(sensor, readings)
    if verdict is True:
        return "WITNESSED"
    inverse = INVERSE.get(sensor, "")
    if inverse and _predicate(inverse, readings) is True:
        return "CONTRADICTED"
    return "NOT_WITNESSED"


def _predicate(name: str, readings: Mapping[str, Any]) -> bool:
    fn = PREDICATES.get(name)
    if fn is None:
        return False
    try:
        return bool(fn(readings))
    except Exception:  # noqa: BLE001
        return False


def evaluate_claim(claim: Mapping[str, Any], *, actions: Sequence[Any] = (),
                   programs: Sequence[str] = (), help_text: str = "",
                   root: pathlib.Path | None = None) -> WitnessResult:
    """The six gates, in order, each refusing with its own name.

    The order is deliberate: a claim that names no program, kind or observable is refused before
    anything is run; a claim that runs but accepts a wrong version is refused after. The receipt
    keeps every refusal's reason, so the measurement is a census, not a score.
    """
    gates = {name: False for name in (
        "NAMES_A_PROGRAM", "NAMES_AN_OBJECT_KIND", "NAMES_AN_OBSERVABLE",
        "SEPARATES_A_WRONG_VERSION", "IS_FALSE_OF_A_NULL_PROGRAM",
        "REPEATS_ON_A_SECOND_ROOM", "OBSERVES")}
    program = str(claim.get("program") or "")
    offered = {str(a).strip() for a in actions if str(a).strip()}
    offered_programs = {a.split()[0] for a in offered if a.split()}
    if not program or (_which(program) is None and program not in offered
                       and program not in set(programs)):
        return WitnessResult(dict(claim), "REFUSED", "NO_PROGRAM_ON_THIS_MACHINE", gates)
    if offered and program not in offered and program not in offered_programs \
            and program not in set(programs):
        return WitnessResult(dict(claim), "SEEN_NOT_PERMITTED",
                             "PROGRAM_OUTSIDE_THE_CALLERS_ACTION_SPACE", gates)
    gates["NAMES_A_PROGRAM"] = True

    kind = str(claim.get("object_kind") or "")
    if not kind or kind not in KIND_PRODUCER:
        return WitnessResult(dict(claim), "REFUSED", "NO_PRODUCER_FOR_KIND", gates,
                             {"kind": kind})
    if kind not in RELATION_KINDS.get(str(claim.get("relation") or ""), (kind,)):
        return WitnessResult(dict(claim), "REFUSED", "RELATION_KIND_MISMATCH", gates,
                             {"kind": kind, "relation": claim.get("relation")})
    gates["NAMES_AN_OBJECT_KIND"] = True

    observable = str(claim.get("observable") or "")
    if observable not in OBSERVABLE_SENSOR:
        return WitnessResult(dict(claim), "REFUSED", "NO_SENSOR_FOR_OBSERVABLE", gates,
                             {"observable": observable})
    gates["NAMES_AN_OBSERVABLE"] = True

    work = root or pathlib.Path(tempfile.mkdtemp(prefix="witness-"))
    # A witness that does not touch the object is true of nothing. `tar` run bare, or
    # `unexpand` run bare, changes no file and no stream, and a predicate over an unread object
    # is vacuously satisfied. The claim names an object; the argv must name it too.
    probe = make_object(kind, work / "probe", variant=0, program=program)
    if not probe.get("ok"):
        return WitnessResult(dict(claim), "REFUSED", "NO_PRODUCER_FOR_KIND", gates,
                             {"kind": kind})
    probe_action = action_for(claim, probe, work / "probe", help_text=help_text,
                              role_flag=(claim.get("witness") or {}).get("role_flag"))
    argv = [str(x) for x in (probe_action.get("argv") or [])]
    if not probe.get("input") or str(probe["input"]) not in argv:
        return WitnessResult(dict(claim), "REFUSED", "WITNESS_IGNORES_THE_OBJECT", gates,
                             {"argv": argv, "object": probe.get("input")})
    first = _run_witness(claim, work, variant=0, help_text=help_text)
    if not first.get("ok"):
        return WitnessResult(dict(claim), "REFUSED", first.get("reason", "WITNESS_FAILED"),
                             gates, first.get("detail", {}))
    readings = first["readings"]
    true_verdict = _predicate(str(claim.get("predicate") or ""), readings)
    wrong_name = INVERSE.get(str(claim.get("predicate") or ""), "")
    wrong_verdict = _predicate(wrong_name, readings) if wrong_name else None
    detail = {"true": true_verdict, "wrong": wrong_verdict,
              "predicate": claim.get("predicate"), "inverse": wrong_name,
              "readings": {k: v for k, v in readings.items()
                           if k not in ("run", "obj", "action")}}
    # THE ORDER OF THESE TWO REFUSALS IS THE WHOLE GATE. A witness that says FALSE for the
    # prose is not a witness that separates -- it is a witness that refutes the document. A
    # witness that says TRUE for both is not a witness either. Only TRUE for the claim AND
    # FALSE for the wrong version is admission.
    if true_verdict is not True:
        gates["SEPARATES_A_WRONG_VERSION"] = False
        return WitnessResult(dict(claim), "REFUSED", "CLAIM_IS_FALSE", gates, detail)
    if wrong_verdict is not False:
        gates["SEPARATES_A_WRONG_VERSION"] = False
        return WitnessResult(dict(claim), "REFUSED", "DID_NOT_SEPARATE_A_WRONG_VERSION", gates,
                             detail)
    gates["SEPARATES_A_WRONG_VERSION"] = True

    # THE GATE THAT MAKES A WITNESS A CLAIM ABOUT A PROGRAM. `prints` is true of `cat` on a
    # file and false of `true` on a file: the difference is the program. `contains` is true of
    # `cat` as well, so a `contains` witness never says anything about the program it names --
    # and admitting it would be counting the sensor as knowledge. The null program is the
    # machine-made wrong version of the CLAIM, not of the predicate: the previous gate's
    # inverse only asked whether the predicate could say FALSE at all.
    null_program = NULL_PROGRAM.get(observable)
    null = _run_witness(claim, work / "null", variant=0, null_program=null_program)
    null_verdict = (_predicate(str(claim.get("predicate") or ""), null["readings"])
                    if null.get("ok") else None)
    detail["null"] = null_verdict
    detail["null_program"] = null_program
    if null_verdict is not False:
        return WitnessResult(dict(claim), "REFUSED", "WITNESS_IS_TRUE_OF_A_NULL_PROGRAM",
                             gates, detail)
    gates["IS_FALSE_OF_A_NULL_PROGRAM"] = True

    second = _run_witness(claim, work / "second", variant=1, help_text=help_text)
    if not second.get("ok"):
        return WitnessResult(dict(claim), "REFUSED", second.get("reason", "SECOND_ROOM_FAILED"),
                             gates, second.get("detail", {}))
    second_verdict = _predicate(str(claim.get("predicate") or ""), second["readings"])
    if second_verdict != true_verdict:
        return WitnessResult(dict(claim), "REFUSED", "CONTENT_DEPENDENT", gates,
                             {"first": true_verdict, "second": second_verdict})
    gates["REPEATS_ON_A_SECOND_ROOM"] = True

    if readings.get("sensor_wrote"):
        return WitnessResult(dict(claim), "REFUSED", "SENSOR_WRITES", gates,
                             {"watched": readings.get("action", {}).get("output_name")})
    gates["OBSERVES"] = True

    qualifier = str(claim.get("qualifier") or "")
    qualifier_verdict = _qualifier_verdict(qualifier, readings)
    relation = {
        "schema": RELATION_SCHEMA,
        "relation_id": "rel-" + hashlib.sha256(json.dumps(
            {"program": program, "relation": claim.get("relation"),
             "observable": observable, "kind": kind, "predicate": claim.get("predicate")},
            sort_keys=True).encode("utf-8")).hexdigest()[:16],
        "program": program,
        "relation": claim.get("relation"),
        "object_kind": kind,
        "observable": observable,
        "predicate": claim.get("predicate"),
        "witness": {"argv": readings.get("action", {}).get("argv"),
                    "role_flag": readings.get("action", {}).get("role_flag") or "",
                    "sensor": OBSERVABLE_SENSOR.get(observable),
                    "output": readings.get("action", {}).get("output_name")},
        "source": {"sentence": claim.get("sentence"), "line": claim.get("line")},
        # The qualifier is stored with its VERDICT, never as if it had been verified. A claim
        # whose adverb no read-only sensor can decide keeps the door and loses the rule, and the
        # receipt says which of the two happened.
        "qualifier": {"text": qualifier, "verdict": qualifier_verdict},
        "source_sha256": hashlib.sha256(str(claim.get("sentence")).encode("utf-8")).hexdigest()[:16],
        "gates": dict(gates),
        "verdict": "ADMIT",
        "authority": "EXTERNAL_DOCUMENT_COMPILED_TO_A_WITNESS",
        "created_at": time.time(),
    }
    return WitnessResult(dict(claim), "ADMIT", None, gates,
                         {"true": true_verdict, "wrong": wrong_verdict,
                          "null": null_verdict, "second": second_verdict}, relation)


# --------------------------------------------------------------------------- #
# 5. THE STORE: save the relation, never the prose
# --------------------------------------------------------------------------- #

def load_memory(path: str | pathlib.Path | None = None) -> dict[str, Any]:
    path = pathlib.Path(path) if path else pathlib.Path(os.environ.get("BRAIN_RELATION_MEMORY",
                                                                      DEFAULT_MEMORY))
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {"schema": MEMORY_SCHEMA, "relations": [], "created_at": time.time()}
    except Exception:
        return {"schema": MEMORY_SCHEMA, "relations": [], "created_at": time.time(),
                "refused": f"MEMORY_CORRUPT:{path}"}
    if not isinstance(data, dict) or data.get("schema") != MEMORY_SCHEMA:
        return {"schema": MEMORY_SCHEMA, "relations": [], "created_at": time.time(),
                "refused": f"MEMORY_SCHEMA_MISMATCH:{path}"}
    if not isinstance(data.get("relations"), list):
        data["relations"] = []
    return data


def save_memory(memory: Mapping[str, Any], path: str | pathlib.Path | None = None) -> dict[str, Any]:
    path = pathlib.Path(path) if path else pathlib.Path(os.environ.get("BRAIN_RELATION_MEMORY",
                                                                      DEFAULT_MEMORY))
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(memory, indent=2, sort_keys=True), encoding="utf-8")
    tmp.replace(path)
    return {"schema": MEMORY_SCHEMA, "path": str(path),
            "relation_count": len(memory.get("relations") or [])}


def remember(memory: Mapping[str, Any], relation: Mapping[str, Any]) -> dict[str, Any]:
    """Append one admitted relation, idempotent by relation_id. A relation with no id is refused."""
    rid = str(relation.get("relation_id") or "")
    if not rid:
        return dict(memory)
    out = dict(memory)
    relations = [r for r in (out.get("relations") or [])
                 if str(r.get("relation_id")) != rid]
    relations.append(dict(relation))
    out["relations"] = relations
    out["updated_at"] = time.time()
    return out


def relations_for(memory: Mapping[str, Any], program: str | None = None,
                  relation: str | None = None, observable: str | None = None
                  ) -> list[dict[str, Any]]:
    out = [r for r in (memory.get("relations") or [])
           if (program is None or r.get("program") == program)
           and (relation is None or r.get("relation") == relation)
           and (observable is None or r.get("observable") == observable)]
    out.sort(key=lambda r: float(r.get("created_at") or 0.0), reverse=True)
    return out


# --------------------------------------------------------------------------- #
# 6. THE PLAN: a verified relation whose program is in the caller's action space
# --------------------------------------------------------------------------- #

def _command_for(relation: Mapping[str, Any]) -> str:
    argv = list((relation.get("witness") or {}).get("argv") or [])
    if not argv:
        return ""
    program = str(relation.get("program") or argv[0])
    # the argv is a room-specific instance; the durable command is the program plus the ROLE
    # flag plus the object placeholder. The object comes from the state, never from the store.
    # The role flag is the one that selects the relation (`-d` decompresses, `-t` lists); an
    # output flag like `-o` belongs to the witness, not to the command.
    flag = str((relation.get("witness") or {}).get("role_flag") or "")
    return " ".join([program] + ([flag] if flag else []) + ["{object}"])


def plan_from_relations(relations: Sequence[Mapping[str, Any]], actions: Sequence[Any]) -> dict[str, Any]:
    """A plan is a relation whose program the caller may do, with the object left to the state."""
    offered = {str(a).strip() for a in actions if str(a).strip()}
    offered_programs = {a.split()[0] for a in offered if a.split()}
    for relation in relations:
        program = str(relation.get("program") or "")
        if program not in offered and program not in offered_programs:
            continue
        return {"status": "PASS__PLAN_FROM_A_VERIFIED_CLAIM",
                "plan": [_command_for(relation)],
                "relation_id": relation.get("relation_id"),
                "program": program,
                "relation": relation.get("relation"),
                "observable": relation.get("observable"),
                "check": relation.get("witness"),
                "authority": "EXTERNAL_DOCUMENT_COMPILED_TO_A_WITNESS",
                "why_this_plan": ("a prose claim was compiled to a witness that separated a "
                                  "wrong version and repeated on a second room; the program is "
                                  "in the caller's action space and the object is left to the state")}
    if relations:
        return {"status": "REFUSED__NOTHING_MATCHED_INSIDE_THE_PLAN_SPACE",
                "seen_not_permitted": [r.get("program") for r in relations][:8]}
    return {"status": "REFUSED__NO_ADMITTED_RELATION"}


# --------------------------------------------------------------------------- #
# 7. THE COMPOSITION: claims -> witnesses -> relations -> plan
# --------------------------------------------------------------------------- #

def compile_claims(text: Any, *, actions: Sequence[Any] = (), programs: Sequence[str] = (),
                   help_text: str = "", root: pathlib.Path | None = None,
                   max_claims: int = 500, default_kind: str = "",
                   subject: str = "") -> dict[str, Any]:
    """Read a document as claims, compile each to a witness, admit or refuse with a reason."""
    started = time.perf_counter()
    claims = extract_claims(text, actions=actions, programs=programs, max_claims=max_claims,
                            default_kind=default_kind, subject=subject)
    work = root or pathlib.Path(tempfile.mkdtemp(prefix="claim-room-"))
    admitted: list[dict[str, Any]] = []
    seen_relation: set[str] = set()
    refusals: list[dict[str, Any]] = []
    false_claims: list[dict[str, Any]] = []
    seen_false: set[tuple[Any, ...]] = set()
    unique_claims: set[tuple[Any, ...]] = set()
    for claim in claims:
        unique_claims.add((claim.get("program"), claim.get("relation"),
                           claim.get("predicate"), claim.get("sentence")))
        result = evaluate_claim(claim, actions=actions, programs=programs,
                                help_text=help_text, root=work)
        row = {"claim": claim, "verdict": result.verdict, "reason": result.reason,
               "gates": result.gates}
        if result.verdict == "ADMIT" and result.relation is not None:
            rid = str(result.relation.get("relation_id") or "")
            if rid not in seen_relation:
                seen_relation.add(rid)
                admitted.append(result.relation)
        elif result.verdict == "REFUSED" and result.reason in (
                "DID_NOT_SEPARATE_A_WRONG_VERSION", "CLAIM_IS_FALSE"):
            # the witness ran and either refuted the prose or accepted the wrong version. Both
            # are recorded, never repaired by hand: one is a finding about the document, the
            # other a finding about the witness. One row per distinct claim, not per sentence.
            key = (claim.get("program"), claim.get("relation"), claim.get("predicate"),
                   claim.get("sentence"))
            if key not in seen_false:
                seen_false.add(key)
                false_claims.append(row)
        else:
            refusals.append(row)
    reasons: dict[str, int] = {}
    for row in refusals + false_claims:
        reasons[str(row.get("reason"))] = reasons.get(str(row.get("reason")), 0) + 1
    return {
        "schema": SCHEMA,
        "claims": len(claims),
        "claims_list": claims,
        "unique_claims": len(unique_claims),
        "admitted": len(admitted),
        "relations": admitted,
        "refusals": refusals,
        "false_claims": false_claims,
        "reasons": reasons,
        "seconds": round(time.perf_counter() - started, 3),
        "authority": "NONE__PRODUCER_RUN_SANDBOX",
    }


def compile_and_plan(text: Any, *, actions: Sequence[Any] = (), programs: Sequence[str] = (),
                     goal: str = "", help_text: str = "", root: pathlib.Path | None = None,
                     default_kind: str = "") -> dict[str, Any]:
    """The prose circuit, end to end: text -> claims -> witnesses -> relations -> a plan."""
    compiled = compile_claims(text, actions=actions, programs=programs, help_text=help_text,
                              root=root, default_kind=default_kind)
    plan = plan_from_relations(compiled["relations"], actions)
    return {**compiled, "plan": plan, "status": plan["status"], "goal": goal,
            "authority": plan.get("authority", "NONE__PRODUCER_RUN_SANDBOX")}


# --------------------------------------------------------------------------- #
# 8. THE MEASUREMENT
# --------------------------------------------------------------------------- #

# --------------------------------------------------------------------------- #
# 7. THE CORPUS: three different kinds of documentation, measured separately
# --------------------------------------------------------------------------- #
# `--help` is a flag catalogue, a stdlib docstring is prose about a Python function, and a
# texinfo manual is prose about a program. Mixing them into one yield number would let a
# corpus with no prose in it "prove" that prose cannot be read. So each is measured alone and
# the receipt says which is which.
PROSE_CACHE = pathlib.Path(__file__).resolve().parents[1] / "astra_runtime/state/prose_corpus_v1.json"
PROSE_SOURCES: dict[str, tuple[str, str]] = {
    # repository -> (tarball, subdirectory of the texinfo source)
    "coreutils": ("https://codeload.github.com/coreutils/coreutils/tar.gz/refs/heads/master",
                  "coreutils-master/doc/coreutils.texi"),
    "gzip": ("https://codeload.github.com/gnu-mirror-unofficial/gzip/tar.gz/refs/heads/master",
             "gzip-master/doc/gzip.texi"),
    "tar": ("https://codeload.github.com/Distrotech/tar/tar.gz/refs/heads/master",
            "tar-master/doc/tar.texi"),
}

_TEXI_BLOCK = re.compile(
    r"@(smallexample|example|verbatim|lisp|smalllisp)\b.*?@end\s+\1", re.S)
_TEXI_STRUCTURAL = re.compile(
    r"^@(node|section|subsection|subsubsection|chapter|appendix|menu|end|table|itemize|"
    r"enumerate|direntry|dircategory|ifinfo|iftex|tex|titlepage|setfilename|settitle|"
    r"documentencoding|syncodeindex|defcodeindex|printindex|summarycontents|contents|"
    r"shortcontents|paragraphindent|frenchspacing|allowcodebreaks|set |clear |"
    r"definfoenclose|unnumbered|top|center|sp |need |page|vskip|noindent|cindex|findex|"
    r"vindex|kindex|pindex|opindex|flindex|defcv|deffn|deftypefn|defvar|deftypevar|defop|"
    r"deftp|defspec|comment|c )\b")
_TEXI_INLINE = re.compile(
    r"@(code|option|var|file|command|samp|emph|strong|dfn|cite|email|url|uref|acronym|abbr|"
    r"env|kbd|key|t|indicateurl|math|sc|dircategory|ref|xref|pxref|footnote|footnotestyle)\{"
    r"([^{}]*)\}")


def texinfo_prose(text: str, *, subject: str = "") -> dict[str, str]:
    """Texinfo source -> one prose document per @node, with examples removed.

    Examples are removed on purpose: the previous round measured those, and this round is
    about the prose that remains. What is left is the author's sentences, with the markup
    reduced to words.
    """
    out: dict[str, str] = {}
    parts = re.split(r"^@node\s+(.*)$", text, flags=re.M)
    for index in range(1, len(parts), 2):
        node = parts[index].strip()
        body = _TEXI_BLOCK.sub(" ", parts[index + 1])
        lines: list[str] = []
        # An option table is a flag catalogue inside a prose document. `@optItem{cat,-b,}`
        # followed by `Number all nonempty output lines, starting with 1.` is a statement about
        # the OPTION, and reading it as a statement about cat is how `cat counts lines` got
        # admitted. The table's own structure says what it is: drop the whole table.
        skipping: str | None = None
        for line in body.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            if skipping:
                if re.match(r"^@end\s+" + skipping + r"\b", stripped):
                    skipping = None
                continue
            table = re.match(r"^@table\s+@(option|samp|code|asis|command)\b", stripped)
            if table:
                skipping = "table"
                continue
            if _TEXI_STRUCTURAL.match(stripped):
                continue
            # `@c` is a comment. `@command`, `@code`, `@cite` are markup, and dropping every
            # line that begins with "@c" deleted every sentence that named a program.
            if stripped == "@c" or stripped.startswith(("@c ", "@comment", "@optItem", "@optItemx")):
                continue
            if stripped.startswith("@item"):
                stripped = stripped[len("@item"):].strip()
                if not stripped:
                    continue
            stripped = _TEXI_INLINE.sub(r"\2", stripped)
            stripped = re.sub(r"@value\{[^{}]*\}", "X", stripped)
            stripped = re.sub(r"@[a-zA-Z]+\*?", " ", stripped)
            stripped = (stripped.replace("@@", "@").replace("@{", "{").replace("@}", "}")
                        .replace("@.", ".").replace("@:", " ").replace("@*", " "))
            stripped = re.sub(r"[ \t]+", " ", stripped).strip()
            if stripped:
                lines.append(stripped)
        if lines:
            name = f"{subject}:{node}" if subject else node
            out[name] = "\n".join(lines)
    return out


def fetch_prose_corpus(dest: pathlib.Path = PROSE_CACHE) -> dict[str, Any]:
    """Download the three manuals and reduce them to per-node prose.

    This is the instant-knowledge tier doing its job: the machine has no man pages, so the
    prose it needs is not on the disk and must be fetched. The result is cached machine-locally
    and is never committed, like `*.fingerprints.json`.
    """
    import io
    import tarfile
    import urllib.request

    docs: dict[str, str] = {}
    sources: dict[str, Any] = {}
    for repo, (url, member) in PROSE_SOURCES.items():
        with urllib.request.urlopen(url, timeout=120) as response:  # noqa: S310
            blob = response.read()
        with tarfile.open(fileobj=io.BytesIO(blob), mode="r:gz") as archive:
            extracted = next(m for m in archive.getmembers() if m.name.endswith(member))
            text = archive.extractfile(extracted).read().decode("utf-8", "replace")  # type: ignore[union-attr]
        if repo == "coreutils":
            for node, prose in texinfo_prose(text).items():
                if node.endswith(" invocation"):
                    docs[f"texi:{node.split()[0]}"] = prose
        else:
            docs.update(texinfo_prose(text, subject=repo))
        sources[repo] = {"url": url, "bytes": len(blob),
                         "sha256": hashlib.sha256(blob).hexdigest()}
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps({"schema": "BRAIN_PROSE_CORPUS_V1", "sources": sources,
                                "documents": docs}, indent=1), encoding="utf-8")
    return {"documents": len(docs), "sources": sources, "path": str(dest)}


def load_prose_corpus(path: pathlib.Path | None = None) -> dict[str, str]:
    cached = pathlib.Path(path or PROSE_CACHE)
    if not cached.exists():
        return {}
    try:
        payload = json.loads(cached.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    docs = payload.get("documents") if isinstance(payload, dict) else None
    return {str(k): str(v) for k, v in (docs or {}).items()}


FLEET = ("gzip", "tar", "sort", "grep", "sed", "jq", "openssl", "git", "find", "stat",
         "wc", "cut", "tr", "comm", "join", "paste", "nl", "fold", "expand", "diff",
         "patch", "base64", "md5sum", "sha256sum", "split", "cksum", "seq", "yes",
         "timeout", "pr", "fmt", "od", "zip", "unzip", "xz", "bzip2", "ar")


def _default_kind_from_help(help_text: str) -> str:
    """The object kind the page's own usage line names (`[FILE]`, `[ARCHIVE]`, `<FILE>`).

    A flag line says what a flag does but not what it acts on; the usage line says the object.
    Read, not guessed: the first uppercase placeholder that is a kind this file knows.
    """
    for token in re.findall(r"[\[<]([A-Z][A-Z_]+)[\]>]", help_text or ""):
        if token.lower() in KINDS:
            return token.lower()
    usage = re.search(r"(?im)^\s*usage:\s*(.+)$", help_text or "")
    if usage:
        for token in re.findall(r"\b([A-Z][A-Z_]+)\b", usage.group(1)):
            if token.lower() in KINDS:
                return token.lower()
    return ""


def _help_text(program: str) -> str:
    done = _run([program, "--help"], "/tmp", timeout=8)
    return (done.get("stdout", "") + "\n" + done.get("stderr", ""))[:65536]


def _stdlib_docstrings() -> dict[str, str]:
    import ast
    out: dict[str, str] = {}
    for name in ("statistics", "textwrap", "difflib", "fractions", "enum", "pickletools"):
        try:
            path = pathlib.Path(__import__(name).__file__)
            tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
            parts = [ast.get_docstring(tree) or ""]
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    doc = ast.get_docstring(node)
                    if doc:
                        parts.append(doc)
            out[f"stdlib:{name}"] = "\n\n".join(parts)
        except Exception:  # noqa: BLE001
            continue
    return out


def _corpus_groups(fleet: Sequence[str] = FLEET) -> dict[str, dict[str, str]]:
    """Every corpus this machine can measure, keyed by what kind of text it is."""
    groups: dict[str, dict[str, str]] = {"help": {}, "stdlib": {}, "prose": {}}
    for program in fleet:
        if _which(program):
            groups["help"][f"help:{program}"] = _help_text(program)
    groups["stdlib"].update(_stdlib_docstrings())
    groups["prose"].update(load_prose_corpus())
    return {name: docs for name, docs in groups.items() if docs}


def _document_owner(name: str) -> str:
    """The program a document is ABOUT, from its name.

    `help:sort` is about sort. `texi:sort` is about sort. `gzip:Invoking gzip` is about gzip,
    because every node of a program's own manual is about that program. A stdlib docstring is
    about a Python module and names no CLI program, so it has no owner.
    """
    if ":" not in name:
        return ""
    kind, _, rest = name.partition(":")
    if kind in ("help", "texi"):
        return rest
    if kind in ("gzip", "tar"):
        return kind
    return ""


def measure(*, budget: float = 240.0, fleet: Sequence[str] = FLEET,
            corpus: str = "all") -> dict[str, Any]:
    """The census: how much of each kind of documentation becomes an admitted relation.

    The three corpora are reported separately because they are not interchangeable. A `--help`
    page is a flag catalogue; a stdlib docstring is prose about a function; a texinfo manual is
    prose about a program. Pooling them would let the corpus with no prose in it answer for the
    corpus that is all prose.
    """
    started = time.time()
    groups = _corpus_groups(fleet)
    if corpus != "all":
        groups = {corpus: groups[corpus]} if corpus in groups else {}
    rows: list[dict[str, Any]] = []
    all_relations: list[dict[str, Any]] = []
    seen_relation: set[str] = set()
    per_corpus: dict[str, dict[str, int]] = {}
    reason_totals: dict[str, int] = {}
    gate_totals: dict[str, int] = {}
    operations: set[tuple[str, str]] = set()
    operations_admitted: set[tuple[str, str]] = set()
    qualifiers: dict[str, int] = {"WITNESSED": 0, "CONTRADICTED": 0, "NOT_WITNESSED": 0}
    for group_name, documents in groups.items():
        group_rows: list[dict[str, Any]] = []
        for name, text in documents.items():
            if time.time() - started > budget:
                break
            owner = _document_owner(name)
            programs = [owner] if owner else []
            # A MANUAL RARELY NAMES THE OBJECT. `cat normally reads and writes in binary mode`
            # says what cat does and leaves the object implicit, and 152 claims were refused with
            # NO_PRODUCER_FOR_KIND because the sentence named no kind at all. The object is not
            # guessed from the sentence: it is read from the PROGRAM'S OWN usage line, which is
            # the same reading the flag already gets.
            program_help = text if name.startswith("help:") else (
                _help_text(owner) if owner else "")
            default_kind = _default_kind_from_help(program_help)
            compiled = compile_claims(text, actions=programs, programs=programs,
                                      help_text=program_help,
                                      default_kind=default_kind, subject=owner)
            for claim in compiled["claims_list"]:
                operations.add((str(claim.get("program")), str(claim.get("relation"))))
            for relation in compiled["relations"]:
                rid = str(relation.get("relation_id") or "")
                operations.add((str(relation.get("program")), str(relation.get("relation"))))
                operations_admitted.add((str(relation.get("program")),
                                         str(relation.get("relation"))))
                verdict = str(((relation.get("qualifier") or {}).get("verdict")) or "")
                if verdict in qualifiers:
                    qualifiers[verdict] += 1
                if rid not in seen_relation:
                    seen_relation.add(rid)
                    all_relations.append(relation)
            for reason, count in compiled["reasons"].items():
                reason_totals[reason] = reason_totals.get(reason, 0) + count
            for relation in compiled["relations"]:
                for gate, passed in (relation.get("gates") or {}).items():
                    gate_totals[gate] = gate_totals.get(gate, 0) + int(bool(passed))
            row = {"corpus": group_name, "document": name, "bytes": len(text),
                   "sentences": len(sentences(text)),
                   "claims": compiled["claims"],
                   "unique_claims": compiled.get("unique_claims", compiled["claims"]),
                   "admitted": compiled["admitted"],
                   "false_claims": len(compiled["false_claims"]),
                   "relations": [r.get("relation_id") for r in compiled["relations"]],
                   "seconds": compiled["seconds"]}
            group_rows.append(row)
            rows.append(row)
        per_corpus[group_name] = {
            "documents": len(group_rows),
            "bytes": sum(r["bytes"] for r in group_rows),
            "sentences": sum(r["sentences"] for r in group_rows),
            "claims": sum(r["claims"] for r in group_rows),
            "unique_claims": sum(r["unique_claims"] for r in group_rows),
            "admitted": sum(r["admitted"] for r in group_rows),
            "false_claims": sum(r["false_claims"] for r in group_rows),
            "refused": max(0, sum(r["unique_claims"] - r["admitted"] - r["false_claims"]
                                  for r in group_rows)),
            "prose_yield": (round(sum(r["admitted"] for r in group_rows)
                                  / sum(r["sentences"] for r in group_rows), 6)
                            if group_rows and sum(r["sentences"] for r in group_rows) else None),
            "claim_yield": (round(sum(r["admitted"] for r in group_rows)
                                  / sum(r["unique_claims"] for r in group_rows), 6)
                            if group_rows and sum(r["unique_claims"] for r in group_rows) else None),
        }
    # TRANSFER: re-run every admitted relation on a THIRD room whose content and name it has
    # never seen. An admitted relation that fails here was about the room, not the kind.
    transfer_ok = transfer_total = 0
    transfer_failures: list[dict[str, Any]] = []
    for relation in all_relations:
        transfer_total += 1
        claim = {"schema": SCHEMA, "sentence": (relation.get("source") or {}).get("sentence"),
                 "line": (relation.get("source") or {}).get("line"),
                 "program": relation.get("program"), "relation": relation.get("relation"),
                 "observable": relation.get("observable"),
                 "object_kind": relation.get("object_kind"),
                 "predicate": relation.get("predicate"), "authority": "NONE"}
        room = pathlib.Path(tempfile.mkdtemp(prefix="transfer-room-"))
        result = evaluate_claim(claim, actions=[relation.get("program")],
                                programs=[relation.get("program")], root=room)
        if result.verdict == "ADMIT":
            transfer_ok += 1
        else:
            transfer_failures.append({"relation_id": relation.get("relation_id"),
                                      "verdict": result.verdict, "reason": result.reason})
    total_sentences = sum(r["sentences"] for r in rows)
    total_unique = sum(r["unique_claims"] for r in rows)
    total_admitted = sum(r["admitted"] for r in rows)
    return {
        "schema": SCHEMA,
        "authority": AUTHORITY,
        "date": time.strftime("%Y-%m-%d"),
        "corpus": corpus,
        "corpora": per_corpus,
        "qualifiers": dict(qualifiers),
        "operations": {
            "named": len(operations),
            "admitted": len(operations_admitted),
            "coverage": round(len(operations_admitted) / len(operations), 6) if operations else None,
            "unadmitted": sorted(f"{p}:{r}" for p, r in operations - operations_admitted)[:60],
        },
        "prose_corpus_present": bool(groups.get("prose")),
        "documents": sum(c["documents"] for c in per_corpus.values()),
        "bytes": sum(r["bytes"] for r in rows),
        "sentences": total_sentences,
        "claims": sum(r["claims"] for r in rows),
        "unique_claims": total_unique,
        "admitted": total_admitted,
        "false_claims": sum(r["false_claims"] for r in rows),
        "refused": max(0, total_unique - total_admitted - sum(r["false_claims"] for r in rows)),
        "reasons": dict(sorted(reason_totals.items(), key=lambda kv: -kv[1])),
        "gate_passes": gate_totals,
        "prose_yield": round(total_admitted / total_sentences, 6) if total_sentences else None,
        "claim_yield": round(total_admitted / total_unique, 6) if total_unique else None,
        "transfer": {"tested": transfer_total, "admitted": transfer_ok,
                     "failed": transfer_total - transfer_ok,
                     "failures": transfer_failures[:20]},
        "rows": rows,
        "seconds": round(time.time() - started, 1),
        "cost": {"model_calls": 0, "parameters": 0, "network_at_run_time": 0, "spend_usd": 0},
        "what_this_is_not": [
            "not a benchmark result: one machine, one fleet, zero GUI, zero network at run time",
            "not a claim that prose is mostly checkable: the yield is the measurement",
            "not a proof: a witness separated one wrong version, was false of a null program, "
            "and repeated on one second room",
            "not a capability: a stored relation is external knowledge, re-verified at use",
        ],
    }


def transfer(memory: Mapping[str, Any], *, actions: Sequence[Any] = (),
             programs: Sequence[str] = (), help_text: str = "",
             root: pathlib.Path | None = None) -> dict[str, Any]:
    """Re-run every admitted relation on a third room with content it has never seen."""
    work = root or pathlib.Path(tempfile.mkdtemp(prefix="transfer-room-"))
    ok = total = 0
    failures: list[dict[str, Any]] = []
    for relation in relations_for(memory):
        total += 1
        claim = {"schema": SCHEMA, "sentence": (relation.get("source") or {}).get("sentence"),
                 "line": (relation.get("source") or {}).get("line"),
                 "program": relation.get("program"), "relation": relation.get("relation"),
                 "observable": relation.get("observable"),
                 "object_kind": relation.get("object_kind"),
                 "predicate": relation.get("predicate"), "authority": "NONE"}
        result = evaluate_claim(claim, actions=actions, programs=programs,
                                help_text=help_text, root=work / f"transfer-{total}")
        if result.verdict == "ADMIT":
            ok += 1
        else:
            failures.append({"relation_id": relation.get("relation_id"),
                             "verdict": result.verdict, "reason": result.reason})
    return {"tested": total, "admitted": ok, "failed": total - ok,
            "failures": failures[:20]}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--receipt", type=pathlib.Path, default=None)
    parser.add_argument("--budget", type=float, default=240.0)
    parser.add_argument("--fleet", nargs="*", default=None)
    parser.add_argument("--text", type=str, default=None,
                        help="compile one document instead of running the census")
    parser.add_argument("--actions", nargs="*", default=[])
    parser.add_argument("--programs", nargs="*", default=[])
    parser.add_argument("--corpus", choices=("all", "help", "stdlib", "prose"), default="all",
                        help="which kind of documentation to measure (default: each alone)")
    parser.add_argument("--fetch-prose", action="store_true",
                        help="download the three manuals and cache their prose, then stop")
    args = parser.parse_args(argv)
    if args.fetch_prose:
        print(json.dumps(fetch_prose_corpus(), indent=2))
        return 0
    if args.text is not None:
        out = compile_and_plan(args.text, actions=args.actions, programs=args.programs)
        print(json.dumps(out, indent=2, default=str)[:20000])
        return 0
    report = measure(budget=args.budget, fleet=args.fleet or FLEET, corpus=args.corpus)
    if args.receipt:
        args.receipt.parent.mkdir(parents=True, exist_ok=True)
        args.receipt.write_text(json.dumps(report, indent=2, sort_keys=True, default=str),
                                encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "rows"}, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
