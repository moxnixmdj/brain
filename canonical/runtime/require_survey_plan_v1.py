#!/usr/bin/env python3
"""The document is the plan: read the tool's own guide, route it, bind, and let the world judge.

    "It enters any new environment knowing nothing ... asks the right questions and gets what
     it doesn't know instantly, because everything on a computer already has a guide."

Nothing here stores a guide. A tool's documents are re-derived from the tool on every use,
bounded in bytes and time (this tree's own lessons: an unbounded reader was OOM-killed, and a
buffered read hung a run for 900 s). The mechanism has five parts, and the fifth is what keeps
the other four honest.

    ROUTE      a tool states its own index: a root page naming its subcommands, each a document
               of its own, each naming sub-subcommands. The request's own content words choose
               the branch, at every level, by the words the document spends on that branch.
               No tool name is known in advance and no synonym table is consulted.

    REQUIRE    the instruction as (ACT, VALUES). The act is read from a closed class of 80
               English act words with the document's own inverse convention (`un-`, `de-`).
               A value is an explicit path, filename, quoted literal or counted number. A
               request whose act is not in the class is refused, never guessed.

    DEMONSTRATE the document's own worked examples, aligned onto the request: bind the request's
               values by kind and order into the example's own shape, and reuse the example's
               options that do not carry a value. A demonstration is a whole act; it is the
               only place a document states an act rather than the meaning of a flag.

    COMPOSE    otherwise, the option whose own words name the act is the operation (first word
               takes precedence); the routed subcommand is the operation when its own index
               line names the act; failing both, the tool's own positional grammar is the
               operation. Each value binds to a slot whose metadata says it takes that kind --
               product-shaped metadata first for the earlier paths -- and the rest positionally.

    EXECUTE    a plan is a claim. `verify_plans` runs each candidate in a COPY of the world and
               hands the result to the caller's own predicate. Nothing in this module asserts
               that a plan worked; the world does, and `chosen` records which one it was.

A second order rather than a second mechanism is produced (`prior` vs `act_first`) because the
document gives prior and no evidence about which order is right; the world is asked instead.

Nothing in this module names a tool, a flag, or an answer; a test enforces it by reading the
source. Authority NONE__PRODUCER_RUN_SANDBOX; zero model calls; zero parameters; zero network.
"""
from __future__ import annotations

import argparse
from collections import Counter
import itertools
import json
import os
import pathlib
import re
import select
import shlex
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from typing import Any, Callable, Iterable, Mapping, Sequence

SCHEMA = "BRAIN_REQUIRE_SURVEY_PLAN_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX"

# The asking convention: how this mechanism *addresses* a program's document. These are not
# knowledge about what any program does -- they are the request protocol, the same for every
# program, and without one first move nothing could be read at all. A test enforces that this
# is the only flag-shaped knowledge in the module.
ASK_CONVENTION = (["--help"], ["-h"], ["help"], [])

DEFAULT_BUDGET = 65_536
DEFAULT_DEADLINE = 4.0
DEFAULT_PROBES = 14
MAX_CANDIDATES = 6

# --------------------------------------------------------------------------- the act class

# A closed class of English acts, and nothing else: no tool, no product, no version. It is
# grammar -- the words a request uses to name what it wants done -- and it is the only place a
# request's meaning is allowed to be read from.
ACTS = frozenset("""
compress uncompress decompress pack unpack encode decode print check sort reverse translate
convert wrap write output render format extract concatenate display search list show find grep
report inspect dump strip analyze measure count compare describe query test verify summarise
summarize split join merge copy move rename remove delete create make build append insert
replace edit update add set install download upload start stop run open save export import
archive unarchive rotate resize reduce enlarge crop trim adjust fill highlight underline
italicize center align indent number paginate fold wrap dedupe
get fetch read load send post put view read browse lookup approve reject publish notify message
acknowledge resolve escalate assign link label tag comment annotate mention reply forward archive
subscribe unsubscribe enable disable pause resume retry cancel revoke grant invite share embed
mount unmount build deploy provision configure schedule trigger dispatch enqueue dequeue
""".split())

INVERSE_PREFIXES = ("un", "de")


def act_of(word: str) -> tuple[str, str] | None:
    """(stem, form) for an act word, or None. `form` keeps the word's own direction."""
    w = str(word or "").strip().lower()
    if not w:
        return None
    if w in ACTS:
        return w, w
    for prefix in INVERSE_PREFIXES:
        stem = w[len(prefix):]
        if w.startswith(prefix) and len(stem) > 2 and stem in ACTS:
            return stem, w
    return None


def acts_in(text: str) -> list[tuple[str, str]]:
    """Every act a phrase names, in the order the words appear."""
    out: list[tuple[str, str]] = []
    for word in re.findall(r"[A-Za-z][A-Za-z-]+", str(text or "")):
        got = act_of(word)
        if got and got not in out:
            out.append(got)
    return out


STOP = frozenset("""
a an the this that these those it its is are was were be been being do does did done
and or but if then than so as at by for from in into of on to with without please could
would should can may might will shall help me my we our you your i he she they them their
some any all each every no not only just also very more most less least same other another
given file files use using used need want wants needed optionally option optional via there
here what which who whom whose when where why how
""".split())


def words_of(text: str) -> set[str]:
    """Content words, singularised by one spelling rule (no synonym table)."""
    out: set[str] = set()
    for word in re.findall(r"[A-Za-z][A-Za-z0-9_'-]*", str(text or "").lower()):
        if word in STOP or len(word) < 2:
            continue
        for suffix in ("ing", "ed", "es", "s"):
            if len(word) > 4 and word.endswith(suffix) and not word.endswith("ss"):
                word = word[: -len(suffix)]
                break
        out.add(word)
    return out


# A slot's type as the tool's own metadata spells it: a vocabulary of type names, not tools.
META_KINDS: dict[str, str] = {
    "FILE": "path", "PATH": "path", "DIR": "path", "DIRECTORY": "path", "OUTPUT": "path",
    "INPUT": "path", "SRC": "path", "SOURCE": "path", "DEST": "path", "DESTINATION": "path",
    "ARCHIVE": "path", "DOCX": "path", "XLSX": "path", "PPTX": "path", "PDF": "path",
    "TXT": "path", "CSV": "path", "EXDIR": "path", "ZIPFILE": "path", "BACKUP": "path",
    "FILENAME": "path", "OUTFILE": "path", "INFILE": "path", "IMAGE": "path", "VIDEO": "path",
    "NUM": "number", "N": "number", "COUNT": "number", "LINES": "number", "BYTES": "number",
    # `<int>` and its spellings were missing, so `--priority <int>` -- whose own documentation is
    # `(0=none, 1=urgent, 2=high, ...)` -- was "untyped" and accepted the *label* `urgent`. The
    # program does `int(priority)` and raised: cb-006 could not run at all. A flag that says it
    # takes an integer takes an integer, and the document already said which integer means
    # "urgent".
    "INT": "number", "INTEGER": "number", "UINT": "number", "LONG": "number", "FLOAT": "number",
    "DECIMAL": "number", "POSITIVE_INT": "number", "INT32": "number", "INT64": "number",
    "WIDTH": "number", "HEIGHT": "number", "LEVEL": "number", "SIZE": "number",
    "PORT": "number", "AMOUNT": "number", "TIME": "number", "SECONDS": "number",
    "NUMBER": "number", "PERCENT": "number", "DEGREES": "number",
    "TEXT": "literal", "STRING": "literal", "STR": "literal", "MSG": "literal",
    "MESSAGE": "literal", "PATTERN": "literal", "REGEX": "literal", "QUERY": "literal",
    "TITLE": "literal", "BODY": "literal", "TYPE": "literal", "FORMAT": "literal",
    "REPO": "literal", "REPOSITORY": "literal", "OWNER": "literal", "NAME": "literal",
    "USER": "literal", "LABEL": "literal", "ASSIGNEE": "literal", "BRANCH": "literal",
    "STATE": "literal", "VALUE": "literal", "ARG": "literal", "ARGS": "literal",
    "IDENTIFIER": "literal", "ID": "literal", "COLOR": "literal", "FONT": "literal",
    # a list of names is a name, written several times: `-f LIST` takes `2`, `1,3`, `a-b`
    "LIST": "literal", "FIELDS": "literal", "FIELD": "literal", "COLS": "literal",
    "COLUMNS": "literal", "CHARS": "literal", "CHARSET": "literal", "SET": "literal",
    "SETS": "literal", "WORDS": "literal", "WORD": "literal", "NAMES": "literal",
    "NAME": "literal", "ARRAY": "literal", "ARRAYS": "literal", "DELIM": "literal",
    "SUF": "literal", "SUFFIX": "literal", "PROG": "literal", "KEY": "literal",
    "KEYDEF": "literal", "SEP": "literal", "MODE": "literal", "ATTR_LIST": "literal",
    "WHEN": "literal", "CONTROL": "literal", "NMERGE": "literal",
}

# Metadata that names a product: used only to decide which of several paths a product-shaped
# slot receives, never to invent a slot.
PRODUCT_META = frozenset({"OUTPUT", "DEST", "DESTINATION", "ARCHIVE", "OUTFILE", "BACKUP",
                          "EXDIR", "DIR", "DIRECTORY"})


def is_product_slot(option: Mapping[str, Any]) -> bool:
    """A slot that names where the result goes.

    Two independent statements count, and only these two: metadata that names a product
    (`DEST`, `OUTPUT`, `ARCHIVE`...), or a phrase in the option's own words that puts a result
    somewhere (`write result to FILE`, `extract files into exdir`, `... destination`). A bare
    preposition is not enough -- `sort according to WORD` contains one and is no destination,
    which is exactly the mistake this rule exists to avoid.
    """
    if not option.get("takes_value"):
        return False
    if slot_kind(option) != "path":
        return False
    meta = re.sub(r"[^A-Z_].*$", "", str(option.get("meta") or "").strip("[]").upper())
    if meta in PRODUCT_META:
        return True
    return bool(DESTINATION_PHRASE.search(str(option.get("words") or "").lower()))


# The request's own grammar for direction: English, not a tool's vocabulary. A path after one
# of these words is the thing produced; after a source word, the thing consumed.
# Note the overlapping spellings: `into` must be tested before `in`, and `to` must not match
# the tail of `into`. Both are handled by matching the whole word before the object, not by a
# separate "in" entry -- the first version of this list had one and read `to` as a destination.
DEST_MARKERS = ("into", "to", "onto", "inside", "as", "named")
# `in` is deliberately absent: it occurs inside ordinary words ("lines"), and a request that
# names a destination says so with `into`/`to`, not with a bare `in`.
SOURCE_MARKERS = ("from", "using", "of")

DESTINATION_PHRASE = re.compile(
    r"\b(?:write|output|save|place|put|store|extract|unpack|dump|redirect|move|copy|create)\b"
    r".{0,48}?\b(?:to|into|in|at)\b|\bdestination\b|\bdirectory\b|\btarget dir")

PATH_TOKEN = re.compile(r"^(?:~(?=/)|\.{0,2}/)[^\s'\"`]*$|^[A-Za-z0-9_.+-]+\.[A-Za-z0-9]{1,8}$")
NUMBER_TOKEN = re.compile(r"^-?\d+(?:\.\d+)?$")
# A count can be written as a word. It is still a count, and a document that declares `NUM` or
# `LIST` has a place for it. Ordinals keep the number, not the order.
ENDS = ("first", "last", "head", "tail", "leading", "trailing")
STARTS = ("first", "leading", "head")

ORDINALS = {"first": "1", "second": "2", "third": "3", "fourth": "4", "fifth": "5",
            "sixth": "6", "seventh": "7", "eighth": "8", "ninth": "9", "tenth": "10"}

# A quote opens a quoted value. An apostrophe inside a word does not: in `the Linear project's
# target date`, the `'` is the possessive, and reading it as an opening quote made
# `s target date to match the milestone` a value of the request -- which the planner then put in
# a flag and the world refused. A straight quote therefore opens a value only where it is not
# preceded by a letter. The closing quote is whichever of the three forms comes next, with no
# such condition: a possessive apostrophe has no matching partner, so it cannot become a value on
# its own, and the next two plain quotes in a sentence balance each other.
QUOTED = re.compile(r"(?:(?<![A-Za-z])[\"'`\u201c\u2018])"
                    r"([^\"'`\u201c\u201d\u2018\u2019]{1,200})"
                    r"[\"'`\u201d\u2019]")

# A tool may put two option rows on one physical line; an option starts a new cell only
# after two spaces and a dash (never inside `--foo=BAR` or `[-x xlist]`).
CELL = re.compile(r"\s{2,}(?=-[A-Za-z0-9?])")

# One rule for every option-list layout a real tool uses (GNU, argparse, click, busybox).
OPTION_LINE = re.compile(
    r"^(?P<indent>\s*)"
    r"(?P<flags>(?:-(?P<short>[A-Za-z0-9?])(?![A-Za-z0-9]))(?:\s*,\s*--[A-Za-z][\w-]*)*"
    r"|--[A-Za-z][\w-]*(?:\s*,\s*--[A-Za-z][\w-]*)*)"
    # the separator is optional because a document may write `--fold[=NUM]`, `--width=NUM`,
    # `-d exdir` or `--output FILE` -- all four are the same fact about the same slot. Angle
    # brackets are as common as caps for the same fact (`--limit <int>`), and are spelled here.
    r"(?:\s*[= ]?\s*(?P<meta>(?:<[A-Za-z][A-Za-z0-9_-]*>)|[\[\]=-]*[A-Z][A-Z0-9_<>.|\[-]*\]?))?"
    # a row may mark itself as required in the same place a description would start, and two
    # spellings are in use: `(required)` where the description begins, and `[required]` where it
    # ends -- `--name=TEXT  record label  [required]`. Only the parenthesised form was read, so
    # `zonectl record remove`, whose page marks both of its flags `[required]`, reported a command
    # missing a required flag as `complete: True`. That is the verifier lying, which is worse than
    # the command being wrong. The marker is the document's own word either way.
    r"(?:\s*\((?P<required>required|optional)\))?"
    r"(?P<rest>(?:\s{2,}|\t+).*)?$"
)
ALIAS = re.compile(r"--[A-Za-z][\w-]*|(?<![\w-])-[A-Za-z0-9](?![\w-])")
# In a usage line an option is followed by the word that names its argument, e.g. `[-d exdir]`.
USAGE_SLOT = re.compile(r"(?P<option>--[A-Za-z][\w-]*|-[A-Za-z0-9])[ =]?(?P<meta>[a-z][a-z0-9_-]*)")
# a usage statement starts a line, or follows the program naming itself in a sentence
# (`Zip 3.0 (July 5th 2008). Usage:`). `give a short usage message` is not one.
USAGE_LINE = re.compile(
    # a usage statement may be the line's own heading in any case (`USAGE:`, `Usage:`, `usage`),
    # with the grammar on the same line or the next; a heading alone is matched with `rest=None`
    r"^\s*(?:[Uu][Ss][Aa][Gg][Ee])\s*(?::\s*(?P<rest>.*))?$"
    r"|^.{0,60}?\.\s*(?:[Uu]sage)\s*:\s*(?P<after>.*)$")
# a usage statement that names the program on its own line, as Info-ZIP does under its banner
USAGE_NAME = re.compile(r"^\s*(?P<name>[A-Za-z][A-Za-z0-9_.+-]*)\s+(?P<grammar>\[-.*)$")
OR_LINE = re.compile(r"^\s*(?:or|OR)\s*:\s*(?P<rest>.+)$")
INDEX_LINE = re.compile(r"^\s{2,}(?P<name>[a-z][a-z0-9][a-z0-9_-]{0,29})(?:\s{2,}|\t+)(?P<what>\S.*)$")
EXAMPLE_HEADER = re.compile(r"^\s*(?:examples?|e\.g\.)\s*:?\s*$", re.I)
HEADING = re.compile(r"^\s{0,2}(?P<title>[A-Z][^:]{2,60}):\s*$")

# What a program says when it cannot render a page, as opposed to having none.
NOT_A_DOCUMENT = ("no man viewer", "failed to exec 'man'", "man: not found",
                  "command not found", "no such file or directory: 'man'",
                  "cannot find the 'man' command")

# --------------------------------------------------------------------------- document reader


def read_document(argv: Sequence[str], *, timeout: float = DEFAULT_DEADLINE,
                  budget: int = DEFAULT_BUDGET, cwd: str | None = None,
                  env: Mapping[str, str] | None = None) -> dict[str, Any]:
    """Ask one program for one document. Bounded in bytes, time, and process group."""
    started = time.perf_counter()
    try:
        proc = subprocess.Popen(list(argv), stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                stdin=subprocess.DEVNULL, cwd=cwd, start_new_session=True,
                                env=dict(env) if env is not None else None)
    except (OSError, ValueError) as exc:
        return {"ok": False, "text": "", "reason": type(exc).__name__, "bytes": 0,
                "seconds": round(time.perf_counter() - started, 4), "argv": list(argv)}
    chunks: list[bytes] = []
    total = 0
    fd = proc.stdout.fileno()
    try:
        while total < budget:
            remaining = timeout - (time.perf_counter() - started)
            if remaining <= 0:
                break
            try:
                ready, _, _ = select.select([fd], [], [], remaining)
            except (OSError, ValueError):
                break
            if not ready:
                break
            try:
                block = os.read(fd, min(4096, budget - total))
            except OSError:
                break
            if not block:
                break
            chunks.append(block)
            total += len(block)
    finally:
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except (OSError, ProcessLookupError):
            pass
        try:
            proc.wait(timeout=1.0)
        except subprocess.SubprocessError:
            pass
        try:
            proc.stdout.close()
        except OSError:
            pass
    text = b"".join(chunks).decode("utf-8", "replace")
    return {"ok": bool(text.strip()), "text": text, "reason": "OK" if text.strip() else "EMPTY",
            "bytes": len(text.encode("utf-8", "replace")),
            "seconds": round(time.perf_counter() - started, 4), "argv": list(argv)}


# --------------------------------------------------------------------------- document parsing


def _usage_variant(text: str) -> dict[str, Any]:
    """One usage statement: its command words, its positional picture, its option slots."""
    rest = re.split(r"\s{2,}(?=[A-Z][a-z])", text)[0].strip()
    tokens = rest.split()
    commands: list[str] = []
    for token in tokens:
        if token.startswith(("[", "-", "<", "{", "(")) or token.isupper():
            break
        if re.match(r"^[A-Za-z][A-Za-z0-9_.+-]*$", token):
            commands.append(token)
        else:
            break
    # A positional is whatever the grammar leaves over once every option and its metavariable are
    # taken: `[<directory>]` at the end of `git init` is a directory, while `<template-directory>`
    # two words after `--template=` is that option's value and not an argument at all. Reading
    # every bracketed token as positional made `git init` look like a command that takes no
    # directory, and the plan dropped the one thing the request named.
    without_options = re.sub(r"(?<![\w-])-{1,2}[A-Za-z0-9][\w-]*(?:=\S+)?\s*(<[^>]+>)?",
                             " ", rest)
    # Brackets come in glued to the metavariable (`[<directory>]`), so compare on the token with
    # its punctuation removed rather than on its first character.
    # `[<options>]` is where the options go, not an argument: git writes it in every usage line
    # and the option list is the real statement of what it holds. Keeping it makes every command
    # look like it takes an object it does not take, and a plan then fills it.
    placeholder = {"options", "option", "flags", "flag", "args", "arguments", "arg"}
    positional: list[str] = []
    for token in without_options.split():
        bare = token.strip("[()]<>").rstrip(".")
        if token.lstrip("[(").startswith(("<", "{")):
            if bare.lower() not in placeholder:
                positional.append(token)
        elif token.isupper() and token not in ("OPTION", "OPTIONS", "USAGE"):
            positional.append(token)
    return {"usage": rest[:400], "commands": commands, "positional": positional[:8]}


def parse_usage(text: str) -> dict[str, Any]:
    """The grammar a tool states about itself, including every alternative form it lists.

    A program that offers more than one arrangement of its arguments says so with `or:`.
    `cp` is the plain case: SOURCE DEST, SOURCE... DIRECTORY, and -t DIRECTORY SOURCE are three
    grammars, and using only the first one is how a copy ends up in the wrong place.
    """
    variants: list[dict[str, Any]] = []
    first = None
    upcoming: str | None = None
    # A usage statement is often wider than the terminal and is printed over several lines, with
    # the continuation indented under the first. GNU git is the plain case: `git init -h` puts
    # `[<directory>]` -- the only positional it has -- on the fifth line, so a parser that reads one
    # line at a time sees a command that takes no directory at all and quietly drops it. Joining a
    # run of continuation lines whose indentation exceeds the `usage:` label's turns the wrapped
    # statement back into the one grammar the program wrote.
    lines = text.splitlines()
    joined: list[str] = []
    for line in lines:
        if joined and re.match(r"^\s{2,}\S", line) and re.match(
                r"^\s*(usage|usages?|usage:|or):", joined[-1], re.I):
            joined[-1] = joined[-1].rstrip() + " " + line.strip()
            continue
        if joined and re.match(r"^\s{2,}\S", line) and joined[-1] == "__USAGE_CONT__":
            joined[-1] = line.strip()
            continue
        joined.append(line)
    for line in joined:
        if upcoming is not None:
            # the usage heading stood alone (`USAGE:`), so the grammar is the line it heads
            said, upcoming = line.strip(), None
            variant = _usage_variant(said)
            if variant["usage"]:
                variants.append(variant)
                if first is None:
                    first = variant
                continue
        for pattern in (USAGE_LINE, USAGE_NAME, OR_LINE):
            m = pattern.match(line)
            if not m:
                continue
            fields = m.groupdict()
            said = fields.get("rest") or fields.get("after") or ""
            if not said.strip():
                # `USAGE:` alone on its line: the grammar is the very next line
                upcoming = ""
                break
            if fields.get("name") and fields.get("grammar"):
                said = fields["name"] + " " + fields["grammar"]
            variant = _usage_variant(said)
            if not variant["usage"]:
                continue
            variants.append(variant)
            if first is None:
                first = variant
            break
        else:
            continue
        if first is not None and len(variants) >= 6 and not OR_LINE.match(line):
            break
    if first is None:
        return {"usage": "", "commands": [], "positional": [], "slots": [], "variants": []}
    whole = " ".join(v["usage"] for v in variants)
    slots = [{"option": m.group("option"), "meta": m.group("meta")}
             for m in USAGE_SLOT.finditer(whole)]
    # a metavariable a program writes beside its options without a flag: `cut OPTION... [FILE]`
    # and `cut -f LIST` say the same thing in the same grammar; the word is the declaration,
    # and the option list is where the program says which option owns it
    declared = [m.group(1) for m in
                re.finditer(r"(?<![\w-])([A-Z][A-Z0-9]{2,}(?:S|ES)?)(?![\w-])", whole)]
    return {**first, "slots": slots[:24], "variants": variants[:6],
            "metavariables": list(dict.fromkeys(declared))[:24]}


# A tool may put two option rows on one physical line; an option starts a new cell only
# after two spaces and a dash (never inside `--foo=BAR` or `[-x xlist]`).
def parse_options(text: str) -> list[dict[str, Any]]:
    """Every option the document declares: flag, slots, words, act, section."""
    options: list[dict[str, Any]] = []
    by_flag: dict[str, dict[str, Any]] = {}
    expecting: dict[str, Any] | None = None
    heading = ""
    for raw in text.splitlines():
        line = raw.rstrip()
        if not line.strip():
            expecting = None
            continue
        h = HEADING.match(line)
        if h and not line.lstrip().startswith("-"):
            heading = h.group("title")[:80]
            expecting = None
            continue
        m = OPTION_LINE.match(line)
        if m is None:
            if expecting is not None and line.startswith((" ", "\t")) and len(expecting["words"]) < 400:
                expecting["words"] = (expecting["words"] + " " + line.strip())[:400]
                continue
            expecting = None
            continue
        row = line[m.start("flags"):]
        cells = [c for c in CELL.split(row) if c.strip()]
        expecting = None
        for cell in cells:
            got = _option_cell(cell, heading)
            if got is None:
                continue
            flag = got["flag"]
            if flag in by_flag:
                entry = by_flag[flag]
                if got["words"] and not entry["words"]:
                    entry.update(words=got["words"][:400], acts=acts_in(got["words"])[:2])
                expecting = entry
                continue
            options.append(got)
            by_flag[flag] = got
            expecting = got
    return options


def _option_cell(cell: str, heading: str) -> dict[str, Any] | None:
    """One option row: its aliases, the kind its metadata names, and its own words."""
    m = OPTION_LINE.match(cell if cell.startswith("-") else " " + cell)
    if m is None:
        return None
    aliases = ALIAS.findall(m.group("flags") or "")
    if not aliases:
        return None
    flag = next((a for a in aliases if a.startswith("--")), aliases[0])
    raw_meta = re.sub(r"^\[?-?\]?", "", (m.group("meta") or "").strip("[]="))
    meta = raw_meta.strip("[]=")
    words = re.sub(r"^\s*[-\u2014]{1,2}\s*", "", (m.group("rest") or "")).strip()
    # A document that marks a flag `(required)` has said the command cannot be formed without
    # it. The parser already matched that word and then discarded it, so the planner could emit
    # `flowctl gate approve gate-001` -- a command this document states is malformed -- in
    # preference to the form the document demonstrates. Keeping what the document says costs
    # nothing and is not an inference.
    stated = (m.group("required") or "").strip().lower()
    if not stated:
        # the trailing bracketed marker, if the description ends with one
        tail = re.search(r"\[(required|optional)\]\s*$", words, re.I)
        if tail:
            stated = tail.group(1).lower()
            words = words[:tail.start()].strip()
    return {"flag": flag, "aliases": aliases[:6], "meta": meta, "words": words[:400],
            "acts": acts_in(words)[:2], "takes_value": bool(meta), "heading": heading,
            "required": True if stated == "required" else (False if stated == "optional" else None)}


def _with_usage_slots(options: list[dict[str, Any]],
                      usage: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Let the usage line declare what an option takes, whichever way the program spells it."""
    """Let the usage line say what an option takes, when the option list did not."""
    by_alias: dict[str, dict[str, Any]] = {}
    for option in options:
        for alias in [option["flag"]] + list(option.get("aliases") or []):
            by_alias.setdefault(alias, option)
    claimed = {re.sub(r"[^A-Z_].*$", "", str(o.get("meta") or "").upper()) for o in options
               if o.get("takes_value")}
    for slot in usage.get("slots") or []:
        option = by_alias.get(slot["option"])
        if option is None or option.get("takes_value"):
            continue
        option["meta"] = slot["meta"]
        option["takes_value"] = True
        option["meta_from"] = "usage"
        claimed.add(str(slot["meta"]).upper())
    # the usage line's own words are a declaration: a token it declares and the list does not
    # is a slot of the option whose words in the list name that token (`--fields=LIST`)
    for option in options:
        if option.get("takes_value"):
            continue
        # an option the usage line already spoke about has its answer; asking again would
        # re-type `--output-delimiter=STRING` as a list because `-f LIST` is also declared
        if option.get("meta_from") in ("usage", "usage-word"):
            continue
        words = str(option.get("words") or "").upper()
        for token in sorted(claimed):
            if token and re.search(r"(?<![A-Z])" + re.escape(token) + r"(?![A-Z])", words):
                option.update(meta=token, takes_value=True, meta_from="usage-word")
                break
    return options


def parse_demos(text: str, tool: str) -> list[dict[str, Any]]:
    """Every whole call a document demonstrates, with its own gloss."""
    base = pathlib.Path(tool).name
    demos: list[dict[str, Any]] = []
    in_block = False
    for raw in text.splitlines():
        line = raw.rstrip()
        if EXAMPLE_HEADER.match(line):
            in_block = True
            continue
        stripped = line.strip()
        if not stripped:
            in_block = False
            continue
        if line.startswith(("  ", "\t")) and stripped.split()[0] == base:
            body, _, gloss = stripped.partition("#")
            for arrow in ("=>", "->", "\u2192"):
                if arrow in body:
                    body, _, said = body.partition(arrow)
                    gloss = (said + " " + gloss).strip()
                    break
            tokens = shlex_split(body)
            # A demonstration states three separate facts, and the third is the one an argument
            # list alone does not: which value belongs to which flag (`--type postgres`). Keeping
            # the pairing is what lets the request's own values fill the same flags.
            pairs: list[tuple[str, str]] = []
            valued: list[str] = []
            previous = ""
            for token in tokens[1:]:
                # `--flag=value` states the pairing in the token itself, and it is the spelling
                # most modern CLIs use. Read as one word it became neither a flag nor a value:
                # `zonectl zone add --origin=example.org --ttl=3600` produced no pairs at all, so
                # the demonstration contributed nothing and the request's values were then emitted
                # positionally beside the flags they had already filled. The `=` is the document
                # saying which value belongs to which flag, which is the whole reason to keep a
                # demonstration.
                head, eq, tail = token.partition("=")
                if eq and head.startswith("-") and head != "-" and tail:
                    pairs.append((head, tail))
                    valued.append(tail)
                    previous = ""
                    continue
                if token.startswith("-") and token != "-":
                    previous = token
                    continue
                if previous:
                    pairs.append((previous, token))
                    previous = ""
                valued.append(token)
            # A USAGE line is a *shape*, not a demonstration: `meshctl service list [flags]` and
            # `git log [<options>] [<revision-range>]` name no object at all. Read as a
            # demonstration it contributed one value, `[flags]`, and that candidate outranked the
            # page's own EXAMPLES line -- the request's values then filled nothing and the plan
            # came out as a bare positional (`meshctl service list production`, complete=True,
            # --status healthy lost). A bracketed token or a metavariable is not an object.
            metavariable = (
                lambda t: (t.startswith("[") or t.startswith("<") or t.endswith("]")
                           or t.endswith(">") or t.startswith("(") or "..." in t
                           or t.lower() in ("options", "flags", "args", "arguments"))
            )
            if not in_block and any(metavariable(t) for t in tokens[1:]):
                continue
            demos.append({"call": " ".join(tokens),
                          "options": [t for t in tokens[1:] if t.startswith("-") and t != "-"],
                          "values": valued, "pairs": pairs,
                          "gloss": gloss.strip()[:300], "tools": tokens[:1],
                          "source": "examples" if in_block else "line"})
            continue
        if in_block:
            in_block = False
    return demos


def shlex_split(text: str) -> list[str]:
    try:
        return shlex.split(text)
    except ValueError:
        return text.split()


def parse_index(text: str) -> list[dict[str, str]]:
    """The document's own index: `  <word>    <what it is for>` rows."""
    out: list[dict[str, str]] = []
    for line in text.splitlines():
        m = INDEX_LINE.match(line)
        if not m:
            continue
        name, what = m.group("name"), m.group("what").strip()
        if name in ("usage", "options", "examples", "flags", "commands", "help", "note",
                    "see", "the", "and", "for", "with", "modifiers"):
            continue
        if len(what) < 6 or what.startswith("-"):
            continue
        out.append({"name": name, "what": what[:200]})
    return out


# --------------------------------------------------------------------------- the document tree


def _probe_ladder(tool: str, prefix: Sequence[str],
                  read: Callable[[Sequence[str]], str]) -> tuple[str, list[str], str]:
    """Ask a program for its own page, shortest-to-longest form, and take the first real one.

    A program that answers a document request with an error (a missing pager, a missing
    viewer) is saying it cannot render a page that way here, not that it has none; the next
    rung asks for a shorter form. The ladder is a property of programs, not of any program:
    every rung is the same for every tool, and no tool name appears in it.
    """
    for suffix in ASK_CONVENTION:
        argv = [tool] + list(prefix) + suffix
        text = read(argv)
        if not text:
            continue
        low = text.lower()
        if any(marker in low for marker in NOT_A_DOCUMENT):
            continue
        if (parse_usage(text)["usage"] or parse_options(text) or parse_index(text)
                or parse_demos(text, tool)):
            # the signature is the *content*, normalized: a program that ignores an unknown
            # subcommand answers its parent's page again, and only the bytes say so
            return text, argv, re.sub(r"\s+", " ", text).strip()[:2000]
    return "", [], ""


def repeatable_places(usage: Mapping[str, Any]) -> set[str]:
    """The places a usage line shows as repeatable (`[PATCH]...`, `SOURCE...`).

    A repeatable place can take every leftover object; a single place takes exactly one. The
    document says which is which with an ellipsis, and nothing else does.
    """
    out: set[str] = set()
    for variant in usage.get("variants") or [usage]:
        for token in str(variant.get("usage") or "").split():
            if token.endswith("..."):
                # `[PATCH]...` and `SOURCE...` are the same fact; the ellipsis is the signal
                word = re.sub(r"[^A-Za-z]", "", token.replace("...", ""))
                if word:
                    out.add(word.lower())
    return out


def positional_grammar(usage: Mapping[str, Any]) -> list[str] | None:
    """The argument picture a usage line draws: FILE SOURCE DEST, SOURCE... DIRECTORY, ...

    A program that writes one place from another says so here and nowhere else. The picture is
    returned with each word lowercased and `...` dropped, or None when the program states no
    arrangement at all (a program with only options has no picture, and nothing is invented).
    """
    best: list[str] | None = None
    for variant in usage.get("variants") or [usage]:
        picture: list[str] = []
        tokens = str(variant.get("usage") or "").split()
        # the first word is the program (and may be followed by its subcommands); a position
        # is what comes after the program has named itself
        while tokens and re.match(r"^[A-Za-z][A-Za-z0-9_.+-]*$", tokens[0]) \
                and tokens[0].lower() in {c.lower() for c in (variant.get("commands") or [])}:
            tokens = tokens[1:]
        joined: list[str] = []
        carry = ""
        for token in tokens:
            if carry:
                carry = carry + " " + token
                if "]" in token:
                    joined.append(carry.replace("[", "").replace("]", ""))
                    carry = ""
                continue
            if token.startswith("[") and token.endswith("]") is False and "] " not in token \
                    and token.count("[") > token.count("]"):
                carry = token
                continue
            joined.append(token)
        for token in joined:
            # `[OPTION]...` and `[flags]` are the same position: where the program's own
            # options sit. Both spellings mean "options here", not an operand.
            if token.startswith("-") or re.match(r"^\[?(?:OPTIONS?|FLAGS?)\b", token.upper()):
                # `[OPTION]...` in a usage line means the program's options sit here. That is a
                # position in the grammar, and a picture that drops it silently shifts every
                # object after it one place to the left.
                picture.append("option")
                continue
            if " " in token and not token.startswith("["):
                # a bracketed phrase that was rejoined and is all words: each word is a place
                for word in re.findall(r"[A-Za-z][A-Za-z0-9_.|-]*", token):
                    if word.lower() not in STOP:
                        picture.append(word.lower())
                continue
            if re.match(r"^\[?<\s*(?:OPTIONS?|FLAGS?|ARGS?|ARGUMENTS?)\s*>\]?\.*$", token, re.I):
                # `[<options>]` is the position `[OPTION]...` already means: where the program's own
                # options sit, not an operand. Read as a bracketed word it took the first object in
                # the request and shifted every real place one to the left.
                picture.append("option")
                continue
            if token.startswith("[") or token.endswith(("]", "...")):
                # a bracketed word is still a place: `[FILE]`, `[list]`, `[FILE]...` -- the
                # bracket means optional, not absent, and the ellipsis can live outside it
                # `.strip("[]")` is a trap here: it removes characters until neither end is a
                # bracket, which on `[FILE]...` eats the closing bracket and then the `]` inside
                # it. Removing one bracket from each side, in order, is the whole operation.
                inner = token.rstrip(".").rstrip("]").lstrip("[")
                inner = re.split(r"[\[\]|]", inner)[0].lstrip(".") or inner
                inner = inner.rstrip("]")
                if inner and not inner.startswith("-") and not inner.endswith("*") \
                        and not inner.startswith("%"):
                    picture.append(inner.lower())
                continue
            if token.startswith("<") or token.startswith("{"):
                # A bare metavariable is a place: the flag-owned ones were removed with their
                # flags. `git mv ... <source>... <destination>` lost `<destination>` here.
                inner = token.strip("<{}>").strip()
                if inner and not re.match(r"^[A-Z_]+$", inner):
                    picture.append(token.lower())
                continue
            if re.match(r"^[A-Za-z]", token) and not token.startswith("%"):
                bare = token.rstrip(".")
                if bare.lower() in {"and", "or", "or:"} or bare.lower() in STOP:
                    continue
                picture.append(bare.lower())
        if best is None or len(picture) > len(best):
            best = picture
    return best or None


def _node(argv: list[str], text: str, tool: str, title: str, summary: str,
          level: int) -> dict[str, Any]:
    """One document of the tree, parsed into the four things a plan needs from it."""
    base = pathlib.Path(tool).name
    usage = parse_usage(text)
    return {"argv": argv, "title": title, "summary": summary[:200], "level": level,
            "usage": usage, "commands": [c for c in usage["commands"] if c != base],
            "index": parse_index(text), "options": _with_usage_slots(parse_options(text), usage),
            "demos": parse_demos(text, tool),
            "bytes": len(text.encode("utf-8", "replace")), "children": []}


def resolve_tool(tool: str) -> str:
    """The program's absolute path, or the name unchanged when it is on PATH.

    A path with a separator is located now, against the caller's directory; a bare name is left
    for the probe to find on PATH, because that is how it was meant.
    """
    text = str(tool)
    if os.sep in text or (os.altsep and os.altsep in text):
        return os.path.abspath(text)
    return text


def survey(tool: str, *, want: Iterable[str] = (), probes: int = DEFAULT_PROBES,
           timeout: float = DEFAULT_DEADLINE, budget: int = DEFAULT_BUDGET,
           depth: int = 3, breadth_per_level: int = 4, visit: int = 12,
           cwd: str | None = None) -> dict[str, Any]:
    """The tool's documents, re-derived now and spent where the request points.

    The root is always read. Each level is then expanded in the order the request's own words
    rank it, and the probe budget is spent depth-first, so a request about one subcommand
    reaches that subcommand's page (and its sub-subcommands) instead of paying for siblings it
    will never read. Every probe runs in a throwaway directory: reading a document must not
    change the world, and this host proved that a `--help` can write a file. Nothing is
    persisted between calls -- this is a cost, not a store.
    """
    # The program is located once, absolutely. Every probe runs in a throwaway directory, so a
    # relative path names nothing there and the survey reads one page and reports that the
    # program has no subcommands -- measured: `canonical/tests/programs/bin/flowctl` read 1 page
    # and the same file by absolute path read 11. Resolving here costs one call and makes the
    # reading independent of the caller's working directory.
    tool = resolve_tool(tool)
    started = time.perf_counter()
    asked: list[dict[str, Any]] = []
    wanted = set(want)
    visits = 0
    scratch = tempfile.mkdtemp(prefix="plan-read-")
    # The budget is documents, not arguments: `probes` bounds how many *documents* this survey
    # may ask for, and the rungs spent finding one document's shortest form are its cost. A
    # global argument budget would let one four-rung program consume the whole survey before a
    # single subcommand was reached.
    budget_left = [probes]

    def read(argv: Sequence[str]) -> str:
        if len(asked) >= probes:
            return ""
        got = read_document(argv, timeout=timeout, budget=budget, cwd=os.path.join(scratch, ""),
                            env={**os.environ, "PWD": scratch})
        asked.append({"argv": list(argv), "bytes": got["bytes"], "ok": got["ok"],
                      "seconds": got["seconds"], "reason": got["reason"]})
        return got["text"] if got["ok"] else ""

    def expand(parent: dict[str, Any]) -> list[dict[str, Any]]:
        nonlocal visits
        names: list[tuple[str, str]] = [(i["name"], i["what"]) for i in parent["index"]]
        known = {n for n, _ in names}
        names.extend((c, "") for c in parent["commands"] if c not in known)
        ranked = sorted(names, key=lambda item: -len(wanted & words_of(item[0] + " " + item[1])))
        prefix = [a for a in parent["argv"][1:] if not a.startswith("-") and a != "help"]
        made: list[dict[str, Any]] = []
        for name, what in ranked[:breadth_per_level]:
            if visits >= visit:
                break
            visits += 1
            text, child_argv, signature = _probe_ladder(tool, prefix + [name], read)
            if not text:
                continue
            if signature and any(a.get("signature") == signature for a in asked[:-1]):
                # the program answered its parent's page again -- it has no page of its own
                continue
            asked[-1]["signature"] = signature
            child = _node(child_argv, text, tool, name, what, parent["level"] + 1)
            if not (child["options"] or child["index"] or child["demos"]
                    or child["commands"] or child["usage"]["positional"]):
                continue
            parent["children"].append(child)
            made.append(child)
        return made

    try:
        root_text, root_argv, root_signature = _probe_ladder(tool, [], read)
        if asked:
            asked[-1]["signature"] = root_signature
        root = _node(root_argv, root_text, tool, "root", "", 0)
        frontier = [root]
        for _ in range(depth):
            nxt: list[dict[str, Any]] = []
            for parent in frontier:
                nxt.extend(expand(parent))
            frontier = nxt
            if not frontier:
                break
    finally:
        shutil.rmtree(scratch, ignore_errors=True)

    return {"schema": SCHEMA, "tool": tool, "root": root, "documents_asked": asked,
            "document_bytes": sum(a["bytes"] for a in asked),
            "documents_ok": sum(1 for a in asked if a["ok"]),
            "probes_left": max(0, probes - len(asked)),
            "seconds": round(time.perf_counter() - started, 4), "stored_bytes": 0}


def route(tree: Mapping[str, Any], request_words: Iterable[str],
          acts: Iterable[tuple[str, str]] = (), *, said: str = "") -> dict[str, Any]:
    """The document the request is about: by the words it spends, then by the act it states."""
    wanted = set(request_words)
    # The program's own name is in its pages' summaries because those summaries are about it, so
    # "in the **git** repository" scores `git init`, whose summary says "Create an empty Git
    # repository", for a request about renaming a file. The caller named the program by invoking
    # it; the word says nothing about which of its commands is wanted. Only the name is removed --
    # the wider genre list (`repository`, `project`) was measured and costs more than it returns.
    wanted = wanted - words_of(str(tree.get("tool") or "").rsplit("/", 1)[-1])
    wanted_acts = [tuple(a) for a in acts]
    current = tree.get("root") or {}
    path: list[str] = []
    nodes = [current]
    scores: list[dict[str, Any]] = []
    # A command can live below a page that says nothing about the request: `wright forge set`
    # has `forge` in the middle, which the request never mentions. Scoring only the children of
    # the page we are on would stop at `forge` -- and "no route" reads as "this program has no
    # such command". So every page is scored, and the path to the best one is walked; a page on
    # that path may be unremarkable without being wrong.
    by_path: dict[tuple[str, ...], dict[str, Any]] = {}

    def walk(node: Mapping[str, Any], prefix: tuple[str, ...]) -> None:
        for child in node.get("children") or []:
            here = prefix + (str(child.get("title") or ""),)
            by_path[here] = dict(child)
            walk(child, here)

    walk(tree.get("root") or {}, ())
    best_path: tuple[str, ...] = ()
    best_score = 0
    best_near = 1 << 20
    wanted_acts_words = {w for a in wanted_acts for w in words_of(" ".join(a))}
    for here, page in by_path.items():
        # The page's own name is what the page *is*; its summary says what the page can be told
        # about. Both are evidence, and they are not equal: `issue list` summarises itself as
        # "List issues with optional filtering by project, assignee, or status", so the word
        # `project` -- a filter this command accepts -- scored as highly as the title of
        # `project list`, and a request to "list all projects" routed to `issue list` (7 to 5).
        # Naming a thing outranks mentioning it, because a parameter is not the subject.
        # A page's name is its whole path, not its last title: `issue list` and `project list`
        # are both titled `list`, and only the path says which one the request means.
        named = words_of(" ".join(here))
        mentioned = words_of(str(page.get("summary") or ""))
        score = 4 * len(wanted & named) + 2 * len(wanted & (mentioned - named))
        # The act the page says it performs is the strongest single statement available: `Move or
        # rename a file`, against a request that says "Rename the file". It was worth +1 against a
        # noun worth 4, so `git init` -- whose summary contains `repository`, a word every request
        # about git uses -- outscored `git mv` for "rename the file a.txt to c.txt". A page stating
        # the requested act is stating the thing the request is *doing*, where a shared noun states
        # only its subject. Worth as much as naming the noun, and only when it is the page's own
        # first act rather than a verb buried in its description.
        # Any act the summary states, not only its first. "Move or rename a file" states two, and a
        # request saying "rename" matches the second; testing only `stated[0]` meant the page that
        # answers the request contributed nothing for saying so. This is the difference between
        # reading what a document states and reading the first word of it, and it costs nothing
        # where the act already matched.
        stated = acts_in(page.get("summary") or "")
        if wanted_acts and any(s[0] in {a[0] for a in wanted_acts} for s in stated):
            score += 1
        # A page that *documents a flag the request names* is a page the request is written in.
        # `List all issues in the "Platform" team with status "Todo"` names `--team` and `--status`
        # only on `issue list`; `team list` has neither, and scoring the request's words alone put
        # `team list` first (9 to 7) because `team` is a noun the page is named after. Naming a
        # flag is not naming a subject -- it is the request stating which page's grammar it is
        # written in, which is the strongest routing evidence there is.
        flags_here = {str(o.get("flag") or "").lstrip("-").lower()
                      for o in page.get("options") or []}
        if flags_here:
            score += 3 * len(wanted & flags_here)
        scores.append({"child": " ".join(here), "score": score})
        # Ties are broken by how close the candidate's *distinguishing* word sits to the act word
        # in the request. `Add a record "www" ... in the zone "example.org"` scores `zone add` and
        # `record add` identically at 8, and insertion order picked `zone add` -- the wrong command,
        # answered from a prepositional phrase. The request names its object right after its verb:
        # `record` at character 6, `zone` at 65. English puts the thing acted on before the
        # circumstance, so proximity to the verb is stated evidence about which noun is the
        # subject, where insertion order is a property of how the document happened to be written.
        # The shorter path remains the last tie-break, unchanged, and `project list` vs `issue
        # list` is decided earlier by A25's weighting (9 to 7) so it is not affected.
        low = said.lower()
        act_at = min([low.find(w) for w in wanted_acts_words] or [0])
        apart = [abs(low.find(w) - act_at) if w in low else 1 << 20
                 for w in (named - wanted_acts_words)]
        near = min(apart) if apart else 1 << 20
        if (score, -near, -len(here)) > (best_score, -best_near, -len(best_path)):
            best_path, best_score, best_near = here, score, near
    for depth in range(1, len(best_path) + 1):
        here = best_path[:depth]
        page = by_path.get(here)
        if page is None:
            break
        path.append(str(page.get("title") or ""))
        nodes.append(page)
        current = page
    return {"document": current, "path": path, "nodes": nodes, "scores": scores,
            "root": tree.get("root") or {}}


# --------------------------------------------------------------------------- require


# A document spells an argument's own choices as a list after a colon or inside parentheses:
# `mode: strict, loose, sealed`, `(values: docker, npm, pypi)`, `(0=none, 1=urgent, 2=high)`,
# `record type, one of A, AAAA, CNAME, MX`. The list is the program's own vocabulary, and it is the
# only place a bare request word can be recognised as a value of a particular option without the
# request quoting it -- so the ways a document introduces one are worth spelling out. `one of` is
# as common as `values:` and writes its list without a bracket or a colon, and reading only the
# bracketed forms lost `--type` entirely on a program whose documentation is otherwise complete.
# A choice may be several words: `(values: Todo, In Progress, Done, Cancelled)` is four
# choices and one of them has a space in it. Allowing only single tokens made the match start
# after the first multi-word choice -- the list read `Progress, Done, Cancelled`, `Todo` was lost,
# and a request saying `status "Todo"` had nothing to bind to. A choice is a run of words with no
# comma in it, at most four of them, optionally `label=value`.
ENUM_ITEM = r"[A-Za-z0-9_+-]{1,20}(?:\s+[A-Za-z0-9_+-]{1,20}){0,3}(?:\s*=\s*[A-Za-z0-9_+-]{1,20})?"
ENUM_LIST = re.compile(r"(?::|\bone of|[^(\n]{0,40}\()[^)\n]{0,60}?"
                       r"(?P<list>" + ENUM_ITEM + r"(?:\s*,\s*" + ENUM_ITEM + r"){1,12})"
                       r"(?:\s*(?:\)|\.|;|$))", re.M)


def enum_pairs(option: Mapping[str, Any]) -> list[tuple[str, str]]:
    """The choices a document lists for one option, each with the value the flag wants.

    `--priority <int>` documents itself as `Priority level (0=none, 1=urgent, 2=high, 3=medium,
    4=low)`. Two different things are being said there, and treating them as one is a bug with a
    measured cost: the *label* is `urgent`, and the *value* the flag accepts is `1`. Feeding the
    label to a flag whose documented type is `<int>` makes the program raise, which is how
    cb-006 stopped running at all (0.4572 -> 0.4509, that task a backend error).

    So a choice is kept as a pair -- the label, and the spelling the flag will actually take -- and
    the label is only offered where the flag's own type accepts a word.
    """
    words = str(option.get("words") or "") + " " + str(option.get("rest") or "")
    found = ENUM_LIST.search(words)
    if not found:
        return []
    out: list[tuple[str, str]] = []
    for item in found.group("list").split(","):
        item = item.strip(" .;'\"")
        left, eq, right = item.partition("=")
        if eq and left.strip() and right.strip():
            out.append((right.strip().lower(), left.strip()))      # label, value
        elif item:
            out.append((item.lower(), item.strip()))
    # Two characters or more. A one-letter choice sounds harmless -- a DNS record's `--type` is
    # documented `one of A, AAAA, CNAME, MX` -- but admitting it made the *article* `a` a label,
    # and `Add a record "www" of type CNAME` then bound `--type a`: the sentence's own grammar
    # beat the document's vocabulary. Measured: cb-style record creation dropped from correct to
    # `--type a` when this was loosened. A one-letter label is not worth that trade; a request
    # that truly means it can say so in a spelling the flag's own list still matches.
    return [(w, v) for w, v in out if 1 < len(w) < 30]


def enum_choices(option: Mapping[str, Any]) -> list[str]:
    """The labels a document lists for one option, if it lists any."""
    return [label for label, _ in enum_pairs(option)]


def vocabulary_in(text: str) -> set[str]:
    """Every word a document offers as a choice somewhere, from its own lines."""
    out: set[str] = set()
    for line in str(text or "").splitlines():
        for match in ENUM_LIST.finditer(line):
            for item in match.group("list").split(","):
                out.add(item.strip(" .;'\"").split("=", 1)[-1].strip().lower())
    return {w for w in out if 1 < len(w) < 30}


def claim_vocabulary(requirement: Mapping[str, Any],
                     vocabulary: Iterable[tuple[str, str]]) -> dict[str, Any]:
    """Move bare request words that are a document's own choices out of `unclaimed`.

    A value does not have to be quoted. `wrap ... with mode loose` names `loose`, and the
    document's own list (`strict, loose, sealed`) is what makes that word a value of that
    option rather than an object of the request. A word the document does **not** list stays
    unclaimed -- which is the difference between "this program accepts it" and "we hope it does".
    """
    known: dict[str, str] = {}
    for flag, word in vocabulary:
        known.setdefault(str(word).lower(), str(flag))
    values = list(requirement.get("values") or [])
    already = {str(v["value"]).lower() for v in values}
    added: list[dict[str, Any]] = []
    left: list[str] = []
    for word in requirement.get("unclaimed") or []:
        if word.lower() in known and word.lower() not in already:
            # the document says which option owns this word: the one whose list it is
            added.append({"kind": "literal", "value": word, "position": 0,
                          "step": 0, "words": [word.lower()], "context": word,
                          "value_of": known[word.lower()], "from_vocabulary": True})
        else:
            left.append(word)
    return {**requirement, "values": values + added, "unclaimed": left,
            "claimed_vocabulary": [v["value"] for v in added]}


def step_of(text: str, position: int) -> int:
    """Which numbered step a position sits under: the last `N.` marker before it, or 0.

    An instruction that writes its acts as `1. ... 2. ...` states a boundary between them, and a
    boundary is the only thing that makes one act's values inapplicable to another's. An
    instruction with no numbering is one step, and this returns 0 for every position in it.
    """
    markers = list(re.finditer(r"(?m)^\s*(\d{1,2})[.)]\s", str(text or "")[:position]))
    return int(markers[-1].group(1)) if markers else 0


def require(text: str) -> dict[str, Any]:
    """The instruction as (ACT, VALUES): what to do, in the class, and the objects it names."""
    instruction = str(text or "")
    values: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    # A JSON object or array in the request is *one argument*, not a bag of words. `with config
    # {"bucket": "analytics-output", "prefix": "daily/"}` was read as four literals -- bucket,
    # analytics-output, prefix, daily/ -- and the program received them as trailing operands
    # (`sink create --name analytics-lake --type S3 bucket analytics-output prefix daily/`) when
    # the whole document's argument is a single `--config`. The braces are the request stating
    # its own boundary, exactly as quotes are, and nothing inside needs re-reading.
    structures: list[tuple[int, int, str]] = []
    for open_ch, close_ch in (("{", "}"), ("[", "]")):
        start = 0
        while True:
            at = instruction.find(open_ch, start)
            if at < 0:
                break
            depth, end = 0, -1
            for cursor in range(at, len(instruction)):
                char = instruction[cursor]
                if char == open_ch:
                    depth += 1
                elif char == close_ch:
                    depth -= 1
                    if depth == 0:
                        end = cursor
                        break
            if end < 0:
                break
            blob = instruction[at:end + 1]
            if len(blob) > 2 and (":" in blob or "," in blob):
                structures.append((at, end + 1, blob))
                start = end + 1
            else:
                start = at + 1

    def add(kind: str, value: str, context: str, position: int) -> None:
        key = (kind, value)
        if key in seen:
            return
        seen.add(key)
        values.append({"kind": kind, "value": value, "position": position,
                       "step": step_of(instruction, position),
                       "words": sorted(words_of(context))[:24], "context": context.strip()[:240]})

    # A structure is blanked out of the text the later passes read, so its own keys and values are
    # never re-read as separate objects. It is registered as one value below, at its own position.
    masked_instruction = instruction
    # Where every quoted value sits, so one value's phrase can stop at its neighbour. Two quoted
    # values in one sentence (`titled "Payment Service Degradation" with severity "P1"`) each
    # carry the words of their own phrase and not the other's -- without this, both windows
    # contain `title` and `severity` alike and neither flag can be told from the other. The span
    # is computed from positions, not by searching for a separator, because the text between two
    # values may be a line break or nothing at all.
    quotes = list(QUOTED.finditer(masked_instruction))
    for index, m in enumerate(quotes):
        # A value's own words are the words immediately around it, not the sentence's: in
        # `... team "Platform" with the title "Fix it", set the priority to "urgent"` every
        # quoted value would otherwise carry `title`, `priority` and `team` alike, and no
        # option could be told apart from any other. The window is the phrase it sits in.
        previous_end = quotes[index - 1].end() if index else 0
        next_start = quotes[index + 1].start() if index + 1 < len(quotes) else len(instruction)
        before = instruction[previous_end:m.start()]
        cut = max([before.rfind(sep) for sep in (", ", "; ", ". ", " and ", " with ", " to ",
                                                 " in ", " set ")] + [-1])
        start = previous_end + (cut + 1 if cut >= 0 else max(0, len(before) - 60))
        after = instruction[m.end():next_start]
        stop = min([i for i in (after.find(", "), after.find("; "), after.find(". "),
                                after.find(" and "), after.find(" with "),
                                after.find(" set "), after.find(" to ")) if i >= 0]
                   + [len(after)])
        # the phrase is what sits between the two nearest separators, and no further
        add("literal", m.group(1), instruction[start: m.end() + stop], m.start())
    unquoted = QUOTED.sub(lambda m: " " * len(m.group(0)), masked_instruction)
    # A URL is the most recognisable thing a request can name and it contains characters no path
    # pattern expects: `https://example.com/x.git` was read as `//example.com/x.git`, with the
    # scheme silently gone, and a clone then asked for a source that does not exist. Matched whole
    # and before anything else, and blanked so the path pattern cannot report a second, mangled
    # copy of the same object.
    url_span = [(m.start(), m.end(), m.group(0)) for m in
                re.finditer(r"(?:[a-zA-Z][a-zA-Z0-9+.\-]*://|git@)[^\s'\"`,;]*[^\s'\"`,;.)]", instruction)]
    for start, end, url in url_span:
        role = "source"
        before = instruction[max(0, start - 40): start].lower()
        if re.search(r"\b(" + "|".join(DEST_MARKERS) + r")\s+[\"\'`]?$", before):
            role = "product"
        clause_start = max([-1] + [unquoted.rfind(sep, 0, start)
                                   for sep in (". ", " from ", " into ", " and ", " with ", ", ")]) + 1
        clause = unquoted[clause_start:start].strip()
        add("path", url, clause or instruction[start: end], start)
        if values and values[-1]["value"] == url:
            values[-1]["role"] = role
        unquoted = unquoted[:start] + " " * (end - start) + unquoted[end:]
    marked: list[int] = []
    for m in re.finditer(r"(?:~(?=/)|[./][^\s'\"`,;:)]+|[A-Za-z0-9_.+-]+\.[A-Za-z0-9]{1,8})",
                         unquoted):
        token = m.group(0).rstrip(".,;:)")
        if len(token) < 2 or token.lower() in STOP:
            continue
        start = m.start()
        before = unquoted[max(0, start - 40): start].lower()
        role = ""
        if re.search(r"\b(" + "|".join(DEST_MARKERS) + r")\s+[\"'`]?$", before):
            role = "product"
        elif re.search(r"\b(" + "|".join(SOURCE_MARKERS) + r")\s+[\"'`]?$", before):
            role = "source"
        # a spelling the world uses for things made from other things: an archive, an encoded
        # stream. The hint is the request's own phrasing; the spelling is the world's, and when
        # the world is available the copy's own existence check decides
        if role == "product":
            marked.append(len(values))
        if role == "" and re.search(r"\.(?:gz|tgz|zip|tar|bz2|xz|zst|b64|enc)$", token.lower()):
            role = "product"
        starts = [unquoted.rfind(sep, 0, start) for sep in (". ", " from ", " into ", " and ",
                                                            " with ", ", ")]
        clause_start = max([-1] + starts) + 1
        clause_end = min([i for i in (len(unquoted), unquoted.find(". ", start),
                                      unquoted.find(" and ", start))
                          if i >= 0] or [len(unquoted)])
        clause = unquoted[clause_start:clause_end].strip()
        values.append({"kind": "path", "value": token, "position": start, "role": role,
                       "step": step_of(unquoted, start),
                       "words": sorted(words_of(clause))[:24],
                       "context": clause[:240]})
        seen.add(("path", token))
    for m in re.finditer(r"\b(\d{1,6})\b", unquoted):
        # A count is a number the request uses, and English puts its name on either side of it:
        # "with 3 nodes" names it after, and "port 5432", "90% of traffic", "database analytics"
        # name it before. Requiring a word *after* the number dropped every one of those, which is
        # why a request naming a port, a percentage split and a host reached the program as a
        # command with none of them. A bare number with no word on either side is an ordinal in a
        # list and is still skipped -- that is what the lookahead was protecting against.
        after = unquoted[m.end(): m.end() + 50]
        before = unquoted[max(0, m.start() - 50): m.start()]
        named_after = bool(re.match(r"\s+[A-Za-z]", after))
        named_before = bool(re.search(r"[A-Za-z][\s\-]+$", before))
        if not (named_after or named_before):
            continue
        add("number", m.group(1),
            unquoted[max(0, m.start() - 90): m.end() + 90], m.start())
    # an ordinal is a word of the instruction, not a fragment of a path: `first` in
    # `/tmp/h/first.txt` is a file name, and counting it would add an object nobody named
    for m in re.finditer(r"(?<![\w./-])(" + "|".join(ORDINALS) + r")(?![\w./-])",
                         unquoted, re.I):
        if re.match(r"\s+\d+\s*[A-Za-z]", unquoted[m.end(): m.end() + 16]):
            continue  # "the first 2 lines": the count is 2, and `first` only selects the end
        # An ordinal is a count only when it modifies an object -- "the first 5 files". Where it
        # opens a clause it is the request placing a step: `First, list available artifacts to
        # find the most recent successful build` is the request's first *instruction*, and there
        # is no number in it at all. Reading it as `1` invented a value and put it in a required
        # flag (`artifact list --namespace 1`), which is the one thing the project forbids
        # outright. The test is local and needs no vocabulary: a clause-opening ordinal is
        # followed by a comma, or stands at the start of the text.
        tail = unquoted[m.end():]
        if re.match(r"\s*,", tail) or not unquoted[: m.start()].strip():
            continue
        add("number", ORDINALS[m.group(1).lower()],
            unquoted[max(0, m.start() - 90): m.end() + 50], m.start())

    clauses = [c for c in re.split(r";|,\s*(?=and\b)|\band\b(?=\s+[a-z]+(?:e|ed|ing)\b)",
                                   instruction) if c.strip()]
    acts: list[dict[str, Any]] = []
    for index, clause in enumerate(clauses):
        for act in acts_in(clause):
            if any(item["act"] == act for item in acts):
                continue
            acts.append({"act": act, "clause": index, "text": clause.strip()[:240],
                         "words": sorted(words_of(clause))[:24]})
    # only the last destination is the request's own; a program extracts an archive "into" a
    # directory named in the same sentence, and reading both as the goal loses the real one.
    # This runs after every value has been added, because `add` appends to the same list.
    for index in [i for i, v in enumerate(values) if v.get("role") == "product"
                  and i not in marked]:
        values[index]["role"] = ""

    # The closed class is the seed, not the boundary. An instruction may use a verb the class
    # does not carry (`register`, `configure`, `route`), and a document may use exactly that
    # verb in its own summary. What is left over is kept so a document can claim it later --
    # the alternative is to refuse a request the world would have let us carry out.
    claimed = {form for _, form in
               [act for item in acts for act in [tuple(item["act"])]]} | \
              {stem for _, stem in
               [act for item in acts for act in [tuple(item["act"])]]}
    # A coordinated value is named by the same words as the value it is coordinated with.
    # `have the label "priority:critical" or "priority:high"` names two values of one thing: the
    # second one's own phrase window begins at `or`, so it contains no word that names a flag, and
    # `--label` -- which names the first -- looked like it named only that one. Carrying the head's
    # naming words forward is not a synonym guess: the coordinator is the request's own statement
    # that both values fill the same role, and the words are the ones it already wrote.
    for index in range(1, len(values)):
        gap = instruction[int(values[index - 1].get("position") or 0):int(values[index].get("position") or 0)]
        # Only two *alternatives* share a role. `the label "a" or "b"` names one thing twice;
        # `the files a.txt and b.txt` names two things, each its own object, and folding their
        # words together handed `b.txt` to `--catenate` (whose own description mentions files) and
        # broke the tar plans. A comma or `or`/`plus`/`not` coordinates; a bare `and` between two
        # paths does not.
        coordinate = re.search(r"(?:,|\bor\b|\bplus\b|\bnot\b)\s*[\"'\u201c]?\s*$", gap[-24:])
        coordinate = coordinate or (re.search(r"\band\b\s*[\"'\u201c]?\s*$", gap[-24:])
                                    and values[index]["kind"] != "path"
                                    and values[index - 1]["kind"] != "path")
        if coordinate:
            inherited = dict(values[index])
            inherited["words"] = sorted(set(values[index].get("words") or [])
                                        | set(values[index - 1].get("words") or []))
            inherited["context"] = (str(values[index - 1].get("context") or "") + " "
                                    + str(values[index].get("context") or ""))
            values[index] = inherited
    unclaimed = sorted(w for w in words_of(instruction) if w not in STOP and w not in claimed)


    reasons: list[str] = []
    if not acts:
        reasons.append("NO_ACT_IN_THE_CLOSED_CLASS")
    if not values:
        reasons.append("NO_EXPLICIT_OBJECT_IN_THE_INSTRUCTION")
    return {"schema": SCHEMA, "instruction": instruction, "acts": acts, "values": values,
            "unclaimed": unclaimed, "reasons": reasons}


# --------------------------------------------------------------------------- plan


def slot_kind(option: Mapping[str, Any]) -> str:
    meta = re.sub(r"[^A-Z_].*$", "", str(option.get("meta") or "").strip("[]<>=").upper())
    if not meta:
        return "untyped"
    if meta in META_KINDS:
        return META_KINDS[meta]
    if meta.endswith("S") and meta[:-1] in META_KINDS:
        return META_KINDS[meta[:-1]]
    return "untyped"


def _accepts(kind: str, value_kind: str) -> bool:
    if kind == "path":
        return value_kind == "path"
    if kind == "number":
        return value_kind == "number"
    if kind == "literal":
        return value_kind in ("literal", "path", "number")
    return False


# Verbs that carry an act but say nothing about which act: they may introduce a sentence
# ("using datapipe, ...") and never select one. Excluding them is the same discipline as STOP.
ACT_NOISE = frozenset("use using tool discover yourself provided documentation".split())


def _acts_stated_by_documents(tree: Mapping[str, Any], requirement: Mapping[str, Any]
                             ) -> tuple[list[tuple[str, str]], list[dict[str, Any]]]:
    """Acts the documents themselves state, named by the request's own leftover words.

    A program's page says what it does in its first sentence: `Register a new data source
    connection`, `Configure a traffic split`. When the request uses that same verb and the plan
    the document supports carries out that same act, the document has answered the question the
    request asked. The document is the authority, and the returned record says which one.
    """
    wanted = {w for w in requirement.get("unclaimed") or []
              if len(w) > 3 and w not in ACT_NOISE}
    if not wanted:
        return [], []
    nodes = every_page(tree)
    found: list[tuple[str, str]] = []
    authority: list[dict[str, Any]] = []
    for node in nodes:
        said = " ".join([str(node.get("title") or ""), str(node.get("summary") or "")])
        for word in sorted(wanted & words_of(said)):
            found.append((word, word))
            authority.append({"act": word, "document": node.get("title") or "root",
                              "said": said.strip()[:160]})
    if not found:
        return [], []
    return found[:4], authority[:4]


def _act_first(option: Mapping[str, Any], act: tuple[str, str]) -> bool:
    """Whether the option's own words name the act as their first act."""
    return tuple(option.get("acts") or [])[:1] == [act]


def _paths_with_places(values: Sequence[Mapping[str, Any]], picture: Sequence[str] | None,
                       *, role_first: bool) -> list[tuple[Mapping[str, Any], str]]:
    """Pair each named object with the picture word for its place, and drop the non-objects.

    The usage line is the only place that says what each position *means*. An object whose
    place means `option` is not an argument -- the program takes it through an option, or not
    at all -- so it is not pushed into a position where the program would read it as a file.
    """
    named = [v for v in values if v["kind"] == "path" and not v.get("value_of")]
    # The picture is the grammar, and when it says what each place *is* it has already said which
    # object goes where: `git mv <source>... <destination>` puts the source first whatever the
    # request's own phrasing was, and reordering products to the front turned `mv a.txt c.txt`
    # into `mv c.txt a.txt` -- a command that renames the destination onto the source. So role
    # ordering only applies where the picture does not name the roles; where it does, the request's
    # own order is mapped onto the places it describes.
    # When the picture itself names the roles -- `<source>... <destination>` -- it has already said
    # which object goes where, and reordering products to the front fights it: `git mv a.txt c.txt`
    # became `mv c.txt a.txt`, which renames the destination onto the source. Role ordering is for
    # pictures that say nothing about roles (`FILE DEST`); where the picture speaks, it decides.
    picture_names_roles = any(re.search(r"source|dest|target|output|input|orig|from|to\b",
                                        str(place), re.I) for place in (picture or []))
    ordered = sorted(named, key=lambda v: int(v["position"])) \
        if (not role_first or picture_names_roles) \
        else sorted(named, key=lambda v: (0 if v.get("role") == "product" else
                                          2 if v.get("role") == "source" else 1,
                                          int(v["position"])))
    # The `option` position is where the program's *flags* sit; it is not an argument, and it
    # must not consume one. Moving past it is what lets `halcyon tally [OPTION]... LEDGER` take
    # a ledger at all -- otherwise a single leading option place swallows every object.
    seat = [place for place in (picture or []) if place != "option"]
    pairs: list[tuple[Mapping[str, Any], str]] = []
    for index, value in enumerate(ordered):
        means = seat[index] if index < len(seat) else ""
        pairs.append((value, means))
    return pairs


def _bind(values: Sequence[Mapping[str, Any]], options: Sequence[Mapping[str, Any]],
          *, product_first: bool, picture: Sequence[str] | None = None
          ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Fill typed slots with the values they accept; return (bound, unbound).

    An object with no slot of an accepting kind is *unbound* and stays so: it is reported by
    its own word rather than pushed into a slot that cannot carry it. An object whose place in
    the usage picture means `option` is not an argument, so it never becomes a slot's value
    merely because the slot takes a path -- `--output-delimiter` takes a string, and a file is
    not a delimiter because both are spelled `STRING`.
    """
    paths = [v for v, _ in _paths_with_places(values, picture, role_first=True)]
    others = [v for v in values if v["kind"] != "path"]
    typed = [o for o in options if o.get("takes_value")]
    typed_paths = [o for o in typed if slot_kind(o) == "path" or is_product_slot(o)]
    typed_paths.sort(key=lambda o: 0 if is_product_slot(o) else 1)
    bound: list[dict[str, Any]] = []
    used: set[int] = set()
    rest_paths = list(paths)
    if product_first:
        for option in typed_paths:
            if not rest_paths:
                break
            value = rest_paths.pop(0)
            bound.append({"role": "path_slot", "option": option["flag"],
                          "value": value["value"], "product": is_product_slot(option)})
            used.add(id(option))
    for value in rest_paths:
        bound.append({"role": "positional", "value": value["value"]})
    unbound: list[dict[str, Any]] = []
    for value in others:
        holder = next((o for o in typed if id(o) not in used
                       and _accepts(slot_kind(o), value["kind"])), None)
        if holder is None:
            unbound.append({"kind": value["kind"], "value": value["value"],
                            "context": value.get("context", "")})
            continue
        used.add(id(holder))
        bound.append({"role": "value_slot", "option": holder["flag"], "value": value["value"]})
    return bound, unbound


def _render(tool: str, prefix: Sequence[str], operation: Mapping[str, Any] | None,
            bound: Sequence[Mapping[str, Any]],
            declared: Sequence[str] | None = None) -> list[str]:
    argv = [tool] + list(prefix)
    slots: list[str] = []
    positional: list[str] = []
    # positionals keep the order of the *places* they sit in, not the order the request named
    # them in: `stitch OUTFILE [PATCH]...` is a grammar, and the thing made comes first
    placed: list[tuple[int, str]] = []
    for item in bound:
        if item["role"] in ("path_slot", "value_slot"):
            slots.extend([str(item["option"]), str(item["value"])])
        elif item["role"] in ("redirect", "stdin_from"):
            continue  # the shell carries these, never the program's argument list
        else:
            index = item.get("place_index")
            placed.append((len(positional) if index is None else int(index),
                           str(item["value"])))
    positional.extend(value for _, value in sorted(placed, key=lambda pair: pair[0]))
    if operation is not None:
        argv.append(str(operation["flag"]))
    # A flag list is not a set: the order the document prints is the order it publishes, and a
    # reader who reports `--state open --repo acme-corp/web-platform` for a page that says
    # `--repo ... --state ...` has reordered the program's own contract for no reason. Measured:
    # `gh issue list` wanted `--repo ... --state open`, this emitted the reverse, and the task
    # scored 0.5 with the right values in the wrong sequence. Ordering by the document's
    # declaration costs nothing and is the only order the page itself endorses.
    if declared and slots:
        rank = {str(flag): i for i, flag in enumerate(declared)}
        pairs = [(slots[i], slots[i + 1]) for i in range(0, len(slots) - 1, 2)]
        pairs.sort(key=lambda pair: rank.get(str(pair[0]), len(rank)))
        slots = [x for pair in pairs for x in pair]
    argv.extend(slots)
    argv.extend(positional)
    return argv


def _shape(text: str) -> str:
    """A word's kind from its own spelling: a path names a place, a number is counted."""
    if PATH_TOKEN.match(text) or "/" in text:
        return "path"
    if NUMBER_TOKEN.match(text):
        return "number"
    return "literal"


def _flag_names_value(value: Mapping[str, Any], slot: Mapping[str, Any]) -> bool:
    """Does this flag's own description name this value -- by a word, or by one stem?

    A demonstration shows *which* flags travel together; it does not say that whichever flag is
    being read accepts whatever object the request names next. `--repo` is described "Repository
    in owner/repo format" and does not name `priority:critical`; `--label` is "Filter by label
    name" and does. Two spellings of one stem count as one word (`assignee`/`assigned`), because
    both spellings are printed somewhere in the document or the request -- nothing is added from
    outside.
    """
    words = words_of(str(slot.get("words") or ""))
    if not words:
        return False
    said = words_of(str(value.get("value") or ""))
    context = words_of(str(value.get("context") or ""))
    if words & (said | context):
        return True
    for a in words:
        for b in said | context:
            if a == b:
                continue
            short, long = (a, b) if len(a) <= len(b) else (b, a)
            if len(short) >= 4 and long.startswith(short) and len(long) - len(short) <= 4:
                return True
            if len(a) >= 5 and len(b) >= 5 and a[:5] == b[:5]:
                return True
    return False


# Flags whose value is a whole piece of prose rather than a name. Their clauses may contain
# commas; a list of field names after any other flag may not.
PROSE_FLAG_WORDS = ("body", "content", "description", "summary", "comment", "message",
                    "note", "text", "details", "reason")


def _labelled_prose(requirement: Mapping[str, Any], tree: Mapping[str, Any]) -> dict[str, Any]:
    """Prose the request labels with an option's own name becomes a value of that option.

    `Create an issue with the title "X" and a body that describes the need to prevent abuse`
    names two things: a quoted title, and a body whose content is a clause rather than a quote.
    The quote becomes a value by itself; the clause is prose, and it stayed in `unclaimed`, so
    `--body` was dropped from a command whose page says it takes one, and the issue was created
    with no body at all.

    The request did state the association: the option's own name appears, and content words
    follow it that nothing else claimed. That is evidence of the same order as a quote -- the
    request said which option and said what goes in it -- so it becomes a value of that option.
    The clause ends at a sentence end or at the next option the request names, takes two or more
    words (`a body` alone is a mention, not content), and is refused if any of its words is
    already inside another value: then the prose belongs to something already placed.
    """
    by_name: dict[str, dict[str, Any]] = {}
    for node in every_page(tree):
        for option in node.get("options") or []:
            flag = str(option.get("flag") or "").lstrip("-")
            if flag and flag not in by_name:
                by_name[flag] = option
    if not by_name:
        return dict(requirement)
    instruction = str(requirement.get("instruction") or "")
    words = [str(v.get("value") or "") for v in requirement.get("values") or []]
    spent: set[str] = set()
    for value in words:
        spent |= set(words_of(value))
    # words that are printed inside a value's own text, which no clause may repeat
    in_a_value: list[set[str]] = [set(words_of(str(v.get("value") or "")))
                                  for v in requirement.get("values") or []]
    # The page's own vocabulary. A clause made of these is a *field list* -- `lead, and target
    # date` names two options, it does not say what either one contains -- and binding it as a
    # value replaces a demo that was already right. Prose is made of words the document does not
    # use: `describes the need to prevent abuse` is a sentence, `target date` is a form.
    documented_words: set[str] = set()
    for node in every_page(tree):
        documented_words |= words_of(" ".join([
            str(node.get("title") or ""), str(node.get("summary") or ""),
            str((node.get("usage") or {}).get("usage") or ""),
            " ".join(str(o.get("words") or "") for o in node.get("options") or [])]))
        documented_words |= {w for o in node.get("options") or [] for w in enum_choices(o)}
        documented_words |= {str(o.get("flag") or "").lstrip("-").lower()
                             for o in node.get("options") or []}
    sequence = list(re.finditer(r"[A-Za-z][A-Za-z'-]*", instruction))
    added: list[dict[str, Any]] = []
    spans: list[tuple[int, int]] = []
    for index, hit in enumerate(sequence):
        option = by_name.get(hit.group(0).lower())
        if option is None:
            continue
        # The clause is the run of words after the name, up to a sentence end or up to the next
        # option the request names. Stop words inside it are ordinary words: `describes the need
        # to prevent abuse` loses everything but three words if `the` and `to` end it.
        tail: list[int] = []
        j = index + 1
        while j < len(sequence):
            gap = instruction[sequence[j - 1].end():sequence[j].start()]
            if "." in gap or ";" in gap or ":" in gap and sequence[j].group(0).lower() in by_name:
                break
            word = sequence[j].group(0).lower()
            if word in by_name:
                break
            tail.append(j)
            j += 1
        # trailing stop words are not part of the content
        while tail and sequence[tail[-1]].group(0).lower() in STOP:
            tail.pop()
        if len([w for w in tail if sequence[w].group(0).lower() not in STOP]) < 2:
            continue
        span = (sequence[tail[0]].start(), sequence[tail[-1]].end())
        if any(span[0] < b and a < span[1] for a, b in spans):
            continue
        clause = instruction[span[0]:span[1]].strip()
        content = words_of(clause)
        if len(content) < 2:
            continue
        # A comma inside the clause usually makes it a list of *fields*, not a statement of
        # content: `sender, timestamp, and message` names three things to display, where `that
        # describes the need to prevent abuse` says what one thing contains. The exception is a
        # flag that carries a whole document -- `--content`, `--body`, `--description`. Its value
        # is prose by nature and prose has commas: `total issues, completed vs in-progress ... ,
        # and lists any blocked items` is exactly a body, and refusing it dropped the only word
        # the Notion page was checked for.
        prose_flag = str(option.get("flag") or "").lstrip("-").lower()
        if "," in clause and not any(w in prose_flag for w in PROSE_FLAG_WORDS):
            continue
        # A field list is not prose: if the document already uses these words, the request is
        # naming the page's own options rather than saying what goes inside one. A flag that
        # carries a whole document is exempt -- its prose legitimately reuses the program's
        # vocabulary (`total issues, completed vs in-progress` is a body written in the words of
        # the things being counted), and it is the flag itself that says a document goes here.
        is_prose = any(w in prose_flag for w in PROSE_FLAG_WORDS)
        if not is_prose and len(content & documented_words) * 2 >= len(content):
            continue
        # Refused only when a word already *inside another value* -- its own quoted text, not
        # every word of its wider phrase. `Add rate limiting to public API endpoints` shares
        # `api` with the body's clause `unauthenticated API routes`; the title's own words are
        # what must not be re-spoken, or the title swallows the body it is merely adjacent to.
        # Refused when the clause is *mostly* words already printed inside one value -- a
        # second phrasing of the same object. One shared word is not that: `Add rate limiting to
        # public API endpoints` and `unauthenticated API routes` are two different objects that
        # happen to share `api`, and refusing on any shared word loses the second one.
        if any(len(content & set(one)) * 2 >= len(content) for one in in_a_value):
            continue
        # The page's own description must be *silent* about the content for a clause to belong
        # there. `--status` is documented "Filter by issue status (values: ...)", so a clause
        # after the word `status` is a field list, not the status's content; `--body` is
        # documented only "Issue body text", so a clause after `body` can only be the body.
        # Without this, an unbound value leaks into the sequence planner as a positional noun and
        # the plan grows a step that runs the clause as an argument (measured: cb-009 0.90->0.70).
        if enum_choices(option):
            continue
        added.append({"kind": "literal", "labelled": True, "value": clause, "position": span[0],
                      "step": str(requirement.get("step") or 0),
                      "words": sorted(content)[:24], "context": clause[:240],
                      "of": str(option.get("flag") or "")})
        spans.append(span)
    if not added:
        return dict(requirement)
    settled = set(spent)
    for item in added:
        settled |= set(words_of(str(item["value"])))
    unclaimed = [w for w in (requirement.get("unclaimed") or []) if w not in settled]
    return {**requirement, "values": list(requirement.get("values") or []) + added,
            "unclaimed": unclaimed, "labelled": added}


def _only_names_documented_nouns(argv: Sequence[str], tree: Mapping[str, Any]) -> bool:
    """Is this command nothing but a routing word and words the pages already use?

    `linear project lead, and target date` has no flag and no value the request supplied by
    quotation -- every word after the route is vocabulary the document prints somewhere. A
    command like that is a field list read as an argument, and running it does nothing. A
    command with any quoted, numeric, or path value carries an object and is left alone.
    """
    if not argv:
        return False
    documented: set[str] = set()
    for node in every_page(tree):
        documented |= words_of(" ".join([str(node.get("title") or ""),
                                         str(node.get("summary") or "")]))
        documented |= {w for o in node.get("options") or [] for w in enum_choices(o)}
    # every word must be one the pages print, and none may be a flag or a number
    words = [str(a) for a in argv]
    if any(w.startswith("-") for w in words):
        return False
    if any(w.replace(".", "").isdigit() for w in words):
        return False
    spoken = [w for w in words if w not in {str(n.get("command") or "") for n in every_page(tree)}]
    if not spoken:
        return False
    content = words_of(" ".join(spoken))
    # A comma list of nouns the pages print is a field list, whether or not every single word is
    # documented: `the channel, sender, timestamp, and message text` is four fields and no object.
    if len(content) >= 3 and len(content & documented) * 2 >= len(content):
        return True
    return all(w.lower() in documented for w in content)


def _demo_plan(demo: Mapping[str, Any], requirement: Mapping[str, Any], tool: str,
               prefix: Sequence[str]) -> dict[str, Any] | None:
    """The document's own worked example, re-filled from the request -- evidence, not a guess.

    A demonstration is the one place a document states a whole act (which options travel
    together, and in what order the objects appear), while a flag's description only states a
    meaning. Reusing it is sound when the instruction supplies the example's objects: the
    instruction's values fill the example's value positions in order, and an example position
    with nothing left to fill it is dropped -- the instruction names its own objects and we do
    not invent one. A drop that mattered is not hidden: the candidate is executed like any
    other, and the world rejects it.
    """
    values = list(requirement.get("values") or [])
    if not demo.get("values") or not values:
        return None
    # A demonstration whose own gloss says it leaves something *out* is an exclusion example:
    # `unzip data1 -x joe` is glossed "extract all files except joe". Filling that flag with the
    # thing the request asked to be made would carry out the opposite of the request. The
    # document said which flag excludes; nothing here has to know what `-x` means.
    gloss_words = {w.lower() for w in re.findall(r"[A-Za-z]+", str(demo.get("gloss") or ""))}
    if gloss_words & _EXCLUSION_WORDS:
        return None
    # A gloss names the act it demonstrates by opening with its verb: "Create archive.tar from
    # files foo and bar", "quietly replace existing ReadMe". The words after that head verb are
    # nouns `acts_in` also returns (`archive` in "if archive file newer"), and a shared noun is
    # not a shared act -- only the head verb is the demonstration's claim.
    stated = [a[0] for a in acts_in(str(demo.get("gloss") or "")) if a[0] not in ACT_NOISE]
    demo_act = stated[0] if stated else None
    request_acts = {tuple(a["act"])[0] for a in requirement.get("acts") or []}
    if demo_act and request_acts and demo_act not in request_acts:
        return None
    ordered = sorted([v for v in values if not v.get("value_of")],
                     key=lambda v: (0 if v.get("role") == "product" else
                                    2 if v.get("role") == "source" else 1,
                                    int(v["position"])))
    # When the example pairs its flags with values, that pairing is the shape to keep: each flag
    # takes the request value whose own words name what the flag's description names, and the
    # values that find no flag are the leftover the example does not cover.
    pairs = list(demo.get("pairs") or [])
    if pairs:
        slots = {str(o.get("flag")): o for o in demo.get("_options") or []}
        by_word: dict[str, list[Mapping[str, Any]]] = {}
        for value in ordered:
            for word in value.get("words") or []:
                by_word.setdefault(word, []).append(value)
        spent: set[str] = set()
        filled_pairs: list[str] = []
        # The strongest evidence a document offers about a flag's value is the list of choices it
        # writes for that flag, and it is evidence about the *flag*, not about the order the
        # demonstration happens to list things in. Applied here as a pass over every flag before
        # any word matching, so a choice cannot be lost because an earlier flag took the value, or
        # because the reading ended before reaching it. `record add` documents `--type` as
        # "record type, one of A, AAAA, CNAME, MX" and the request says "of type CNAME": the
        # document has already said that word belongs to that flag.
        said_text = str(requirement.get("instruction") or "")
        # A demonstration may legitimately write the same spelling in two slots -- `record add`
        # demonstrates `--origin=example.org --name=www --type=CNAME --value=example.org`, because
        # a record's data is very often its own zone. Spending each value once is right in general
        # and wrong exactly there: the request says "value example.org in the zone example.org",
        # naming it twice, and the document says it twice. Two independent statements agreeing is
        # the licence. One repetition in the demonstration is not enough on its own -- a document
        # repeating a placeholder says nothing about the request -- so both sides must show the
        # second occurrence.
        repeated = Counter(v for _, v in pairs)
        reusable = {v for v, n in repeated.items() if n > 1}
        for flag, _ in pairs:
            if str(flag) in filled_pairs[::2]:
                continue
            choice_slot = slots.get(str(flag)) or {}
            kind = slot_kind(choice_slot)
            for label, spelling in enum_pairs(choice_slot):
                found = re.search(r"(?<![\w.-])" + re.escape(label) + r"(?![\w.-])",
                                  said_text, re.I)
                if not found:
                    # The request may name the choice with the spelling the world uses for it.
                    # `--type` lists `postgres` and the request says "PostgreSQL": the stems are
                    # `postgr` and `postgresql`, so neither word-matching nor an exact list lookup
                    # connects them, and `--type` then fell through to taking the hostname. One
                    # being a prefix of the other, on the last six characters or more, is the
                    # document's own vocabulary being spoken with its full name.
                    for word in re.findall(r"[A-Za-z][A-Za-z0-9]*", said_text):
                        low = word.lower()
                        if (len(label) >= 4 and (low.startswith(label) or label.startswith(low))
                                and min(len(low), len(label)) >= 4
                                and abs(len(low) - len(label)) <= 4):
                            found = re.search(r"(?<![\w.-])" + re.escape(word) + r"(?![\w.-])",
                                              said_text, re.I)
                            break
                if not found:
                    continue
                # What the request writes is the *label*; what the flag takes is the spelling the
                # document paired with it. `--priority <int>` takes `1` for "urgent", and sending
                # the word is what made the program raise. Where the flag accepts a word, the
                # request's own spelling is kept rather than the document's, because the document
                # capitalises for display (`CNAME`) and the request's form is the one it wants.
                if kind == "number" and re.match(r"-?\d+$", str(spelling)):
                    value = str(spelling)
                elif said_text[found.start():found.end()].lower() == str(label).lower():
                    # The request named the choice exactly, case aside. Its own spelling is the one
                    # to send: a document capitalises for display (`Progress`, `Done`) while its
                    # parser usually takes the word as written, and the request said `Done`.
                    value = said_text[found.start():found.end()]
                elif re.search(r"\benum\b", str(choice_slot.get("meta") or ""), re.I):
                    # The request named the choice by a longer or shorter form -- "PostgreSQL" for
                    # a list that says `postgres`. A flag documented `<enum>` accepts only the words
                    # it lists, so the document's spelling is what goes on the line.
                    value = str(spelling)
                else:
                    value = said_text[found.start():found.end()]
                if value.lower() in {str(x).lower() for x in spent}:
                    continue
                filled_pairs.extend([str(flag), value])
                spent.add(value.lower())
                break
        # A demonstrated value that is a *structure* -- `{"host": ..., "port": 5432}` -- is filled
        # from the request before any scalar flag competes for the same values. The shape is the
        # document saying which request word goes where *inside one argument*, and letting a scalar
        # flag take one of those words first leaves the structure unfillable: a data-source
        # connection came out with `--type` holding the hostname and no `--config` at all, because
        # `--name` and `--type` are listed before `--config` in the demonstration.
        for flag, example in pairs:
            if not any(ch in str(example) for ch in "{}[]:"):
                continue
            shaped = _shape_filled(str(example), ordered, spent)
            if shaped is not None:
                spent.update(_tokens_in(str(example)) & {str(v["value"]) for v in ordered})
                filled_pairs.extend([str(flag), shaped])
        # A bare word the request names and the demonstration *also* writes in a flag's place is
        # that flag's value. `zonectl record remove --help` demonstrates
        # `--origin=example.org --name=www`, and the request says "Remove the record www from the
        # zone example.org". `www` is neither quoted, nor a path, nor a number, so the extractor
        # never saw it, `--name` stayed empty, and a required flag was left out of the command.
        # The licence here is the strongest the document can offer -- the request and the example
        # write the same word, and the example states which flag takes it -- so nothing is
        # inferred from the word's shape or meaning.
        if pairs:
            written_words = set(re.findall(r"[A-Za-z0-9][A-Za-z0-9._-]*",
                                           str(requirement.get("instruction") or "")))
            for flag, example in pairs:
                shown = str(example).strip()
                if (str(flag) in [str(x) for x in filled_pairs[::2]]
                        or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", shown)
                        or shown.lower() in {"true", "false", "none", "null"}):
                    continue
                if shown not in written_words:
                    continue
                if any(str(v["value"]) == shown for v in ordered):
                    continue
                filled_pairs.extend([str(flag), shown])
                spent.add(shown)
        # A flag the demonstration does not name but the page documents, whose *vocabulary* the
        # request states, takes that value. `linear issue list` demonstrates only `--team
        # Platform`; the request also says `status "Todo"`, and `--status` lists Todo among its
        # choices. Nothing here is inferred from the word: the page says Todo belongs to
        # `--status`, the request says Todo, and the demonstration had no place for it. Without
        # this the value was reported unplaced and silently dropped from a command the page
        # documents the flag on.
        for other in demo.get("_options") or []:
            other_flag = str(other.get("flag") or "")
            if not other_flag or other_flag in {str(f) for f in filled_pairs[::2]}:
                continue
            choices = enum_choices(other)
            if not choices:
                continue
            said = str(requirement.get("instruction") or "")
            for choice in choices:
                found = re.search(r"(?<![\w.-])" + re.escape(choice) + r"(?![\w.-])", said, re.I)
                if not found:
                    continue
                placed = said[found.start():found.end()]
                if str(choice).lower() in {str(x).lower() for x in spent}:
                    continue
                if str(choice) in spent:
                    continue
                filled_pairs.extend([other_flag, placed])
                spent.add(str(choice))
                break
        # The request states a value the demonstration already writes: that pairing is settled.
        # `notion page create` demonstrates `--title Weekly Report --parent Engineering Wiki`; a
        # request saying `titled "Weekly Report" under "Engineering Wiki"` names both values, so
        # both flags keep what the document put there. Without this the second pairing was
        # dropped -- `--parent` vanished and `Engineering Wiki` was emitted as a bare positional,
        # because a two-word example value is split by the tokeniser and never matches one value.
        said_now = str(requirement.get("instruction") or "")
        for flag, example in pairs:
            if str(flag) in filled_pairs[::2]:
                continue
            shown = str(example).strip()
            if not shown or shown.startswith("-"):
                continue
            if re.search(r"(?<![\w.-])" + re.escape(shown) + r"(?![\w.-])", said_now):
                filled_pairs.extend([str(flag), shown])
                spent.update(words_of(shown))
                spent.add(shown)
        for _i, (flag, example) in enumerate(pairs):
            if str(flag) in filled_pairs[::2]:
                continue
            slot = slots.get(flag) or {}
            want = words_of(str(slot.get("words") or ""))
            pick, score = None, 0
            # A document that lists an option's choices (`--severity (values: critical,
            # warning, info)`) has said exactly which values belong there. If the request
            # states one of them, that is this flag's value -- no word matching needed, and an
            # unrelated value cannot take the place.
            listed = enum_choices(slot)
            if listed:
                listed_lower = {c.lower() for c in listed}
                pick = next((v for v in ordered if str(v["value"]).lower() in listed_lower
                             and str(v["value"]) not in spent), None)
                if pick is None:
                    # The request may state a choice without the value extractor having kept it.
                    # `zonectl record add` documents `--type` as "record type, one of A, AAAA,
                    # CNAME, MX", and `Add a record "www" of type CNAME ...` names one of them --
                    # but `CNAME` is an all-caps bare word, which the extractor deliberately does
                    # not treat as a value, because an all-caps word is usually a program or a
                    # placeholder. Here the document has already said this exact word belongs to
                    # this exact flag, which is the identification, and it costs no matching to
                    # use it. Only words the option itself lists are admitted, and only when they
                    # appear in the instruction as whole words.
                    said = str(requirement.get("instruction") or "")
                    # A choice is taken by the spelling the request uses, and a longer choice
                    # wins over one of its letters: the list `A, AAAA, CNAME, MX` contains both
                    # `A` and `CNAME`, and a request saying "of type CNAME" matched `A` first
                    # (case-insensitively, inside "Add a record") and wrote `--type a`. Ordering
                    # by length and then taking the first spelling actually present is the
                    # document's own ordering of what a word *is*: the longest label that occurs
                    # is the one the sentence used.
                    # Exact spelling first, longest first: the request wrote `CNAME` in the
                    # document's own capitals, so a case-sensitive search finds it and `A` -- the
                    # article in "Add a record" -- is not even a candidate. The case-insensitive
                    # pass is the fallback for a document that capitalises for display and a
                    # request that does not (`--type` lists `postgres`, the request says
                    # "PostgreSQL").
                    # The *spelling* the document prints, not the lowercased label: `enum_pairs`
                    # returns ("a", "A") and ("cname", "CNAME"), and searching for the label broke
                    # on a request that wrote the display form. Longest first, exact first.
                    spellings = [(label, shown) for label, shown in enum_pairs(choice_slot)]
                    for exact in (True, False):
                        for label, shown in sorted(spellings, key=lambda p: (-len(p[1]), p[1])):
                            for needle in (shown, label):
                                pattern = (r"(?<![\w.-])" + re.escape(needle) + r"(?![\w.-])")
                                found = re.search(pattern, said, 0 if exact else re.I)
                                if not found:
                                    continue
                                if label.lower() in {str(x).lower() for x in spent}:
                                    continue
                                filled_pairs.extend([flag, said[found.start():found.end()]])
                                spent.add(label.lower())
                                break
                            if any(str(f).lower() == flag.lower() for f in filled_pairs[::2]):
                                break
                        if any(str(f).lower() == flag.lower() for f in filled_pairs[::2]):
                            break
                    if any(str(f).lower() == flag.lower() for f in filled_pairs[::2]):
                        continue
                if pick is not None:
                    spent.add(str(pick["value"]))
                    filled_pairs.extend([flag, str(pick["value"])])
                    continue
            # Which of the flag's own words carries the pairing? Every word here is a word the
            # flag's description uses, so all of them are candidates and they cannot be ranked
            # by that. They are ranked by the description's own order -- the flag's name comes
            # first, its elaboration after -- which is the document's statement of what the flag
            # is chiefly called. Ordering by that, not by set iteration, is the difference
            # between a plan that is reproducible and one that changes with the process.
            # A word that names *every* flag on the page distinguishes none of them. `record add`
            # describes `--origin` as "zone the record lives in", `--name` as "record label",
            # `--type` as "record type, one of ...", `--value` as "record data": the word `record`
            # is in all four, so it can never say which one a value belongs to, yet under
            # description-order ranking it is the first candidate for each. Dropping words the
            # other flags also use leaves `zone`, `label`, `type`, `data` -- each true of exactly
            # one flag, which is what a discriminator is.
            # "Also used by another flag", not "used by all of them": `--help` explains itself
            # with words no other flag shares, so requiring the intersection of *every* sibling
            # removes nothing and the filter silently does nothing. A word two flags both claim
            # already fails to distinguish them, which is the whole property being asked for.
            counts: dict[str, int] = {}
            for other in demo.get("_options") or []:
                if str(other.get("flag")) == flag:
                    continue
                for word in words_of(str(other.get("words") or "")):
                    counts[word] = counts.get(word, 0) + 1
            ambiguous = {w for w, n in counts.items() if n >= 2} if len(counts) else set()
            want = {w for w in want if w not in ambiguous} or want
            description = str(slot.get("words") or "").lower()
            ordered_want = sorted(want, key=lambda w: (description.find(w), w))
            best: tuple[int, int, int] | None = None
            for rank, word in enumerate(ordered_want):
                for value in by_word.get(word, []):
                    v_text = str(value["value"])
                    if v_text in spent and not (v_text in reusable
                                                and said_text.lower().count(v_text.lower()) > 1):
                        continue
                    # Among words equally able to name the pairing, the one the value actually
                    # follows is the one it belongs to: `titled "X" with severity "P1"` binds P1
                    # to `severity` at ten characters and to `incident` at a hundred and sixty.
                    # Proximity in the request is stated evidence; a tie broken by iteration
                    # order is not evidence at all.
                    # The word that names a value is the one the request puts *immediately before*
                    # it, not the nearest occurrence anywhere. `Add a record "www" of type CNAME
                    # with value "example.org"` has `record` at 6 and `www` at 13; `type` at 22 and
                    # `value` at 38 sit just ahead of `example.org` at 44. Reading only the first
                    # occurrence of each word, or an unsigned distance, lets `--type` -- whose
                    # description lists CNAME, a word that appears in `www`'s own context -- take
                    # the record's name. A label follows the noun, a field follows its field name.
                    said_text = str(requirement.get("instruction") or "").lower()
                    at = said_text.rfind(word, 0, int(value.get("position") or 0))
                    if at < 0:
                        at = said_text.find(word)
                    gap = abs(int(value.get("position") or 0) - at) if at >= 0 else 1 << 30
                    # proximity first: the value belongs to the word it follows. Description
                    # order and the value's own position only separate exact ties, so no two
                    # seed orders can disagree.
                    key = (gap, rank, int(value.get("position") or 0))
                    if best is None or key < best:
                        best, pick, score = key, value, 1
            if pick is not None and str(pick["value"]) in spent:
                if not (str(pick["value"]) in reusable
                        and said_text.lower().count(str(pick["value"]).lower()) > 1):
                    pick = None
            if pick is None:
                # The example's flag has no description to match on. Before using its *shape*,
                # the example's own values must have something to do with the request's: a
                # demonstration of `unzip -p foo | more` is about a pipe to `more`, and if
                # nothing in it is named in the instruction, its shape is evidence about some
                # other act. Reusing a shape with no shared word is how a destination ends up in
                # an exclusion flag.
                example_text = " ".join([str(demo.get("call") or ""),
                                         str(demo.get("gloss") or ""),
                                         " ".join(str(v) for v in demo.get("values") or [])])
                example_words = {w.lower() for w in re.findall(r"[A-Za-z][A-Za-z0-9_.-]+",
                                                              example_text)}
                request_words = words_of(str(requirement.get("instruction") or ""))
                overlaps = example_words & request_words
                # the program's own name is not evidence about the act
                overlaps -= words_of(str(tool.rsplit("/", 1)[-1]))
                if not overlaps:
                    continue
                # a value the document already assigned to a flag is not a leftover object
                rest = [str(v["value"]) for v in ordered
                        if (str(v["value"]) not in spent
                            or (str(v["value"]) in reusable
                                and said_text.lower().count(str(v["value"]).lower()) > 1))
                        and not v.get("value_of")]
                if not rest:
                    # The example's flag has nothing left to take. Discarding the whole reading
                    # throws away the flags it *did* fill, which is how `entry list --cluster
                    # session-store` was lost to a positional `entry list session-store`: the
                    # page demonstrated `--cluster <x> --limit 20`, the request named only a
                    # cluster, and the unfilled `--limit` cancelled the filled `--cluster`. A
                    # flag the request supplies nothing for is a flag the command omits; the
                    # census still reports any *required* flag left empty. Only a reading that
                    # filled nothing at all is no reading.
                    # Skipping to the *next* flag, not out of the loop: `record add` demonstrates
                    # four flags and the request fills three, and leaving on the first unfilled
                    # one dropped `--value` as well as `--type`. A flag with nothing to take is
                    # omitted; the flags after it are still the demonstration's.
                    if filled_pairs:
                        continue
                    return None
                filled_pairs.extend([flag, rest[0]])
                spent.add(rest[0])
                # The rest are *positional* objects for the command as a whole, and a spelling the
                # demonstration itself gives two flags is not one of them: it is already spoken for
                # and will be filled where the document puts it. Dumping it here is how
                # `record add` came out with `--name www example.org --value example.org`.
                leftover = [v for v in rest[1:]
                            if not (v in reusable and said_text.lower().count(v.lower()) > 1)]
                # A demonstration shows a flag once; a request may name several values for it.
                # `have the label "priority:critical" or "priority:high"` names two labels, the
                # example shows `--label bug` once, and the second value trailed the command as a
                # bare operand (`issue list ... --label priority:critical priority:high`) -- where
                # a program reads it as a positional and refuses. Repeating the flag is the
                # idiom every list-valued option uses (`--label a --label b`), and it invents
                # nothing: the flag and each value are already on the page and in the request.
                # Only when the demonstration's own flag carries a single value, and only for the
                # values that have no other flag to take them.
                # A demonstration shows a flag once; a request may name several values for it.
                # `have the label "priority:critical" or "priority:high"` names two labels while
                # the example shows `--label bug` once. The second value then trailed the command
                # as a bare operand, where the program reads it as a positional and refuses.
                # Repeating the flag is the idiom every list-valued option uses, and it invents
                # nothing -- the flag and each value are already on the page and in the request.
                # The flag is the one whose own description *names* the value, never the flag that
                # happened to be current: repeating the labels on `--repo` is what produced
                # `--repo acme-corp/web-platform --repo priority:critical --repo priority:high`.
                remaining: list[str] = []
                for value in leftover:
                    mapped = next((m for m in ordered if str(m["value"]) == str(value)), None)
                    # A path is an operand, never a repeated flag: `the files a.txt and b.txt`
                    # names two objects the program positions, and `tar --help` lists
                    # `--catenate` described with the word "files", so repeating anything on a
                    # path-named flag turned a correct `tar -cf out.tar a.txt b.txt` into
                    # `-cf out.tar --catenate a.txt`. Only non-path values repeat.
                    if mapped is not None and mapped.get("kind") == "path":
                        remaining.append(value)
                        continue
                    target = None
                    if mapped is not None:
                        target = next((o for o in (demo.get("_options") or [])
                                       if o.get("takes_value")
                                       and not enum_choices(o)
                                       and _flag_names_value(mapped, o)),
                                      None)
                    if target is None:
                        remaining.append(value)
                        continue
                    # A flag the demonstration fills with a *structure* is filled by the structure
                    # pass, never by repetition: `--config {"bucket": ..., "prefix": ...}` came
                    # out as `--config bucket --config analytics-output --config prefix --config
                    # daily/` -- one JSON argument written four times, and wrong each time.
                    shown = next((str(x) for f, x in pairs if str(f) == str(target.get("flag"))),
                                 "")
                    if any(ch in shown for ch in "{}[]:"):
                        remaining.append(value)
                        continue
                    filled_pairs.extend([str(target.get("flag")), str(value)])
                    spent.add(str(value))
                leftover = remaining
                filled_pairs.extend(leftover)
                spent.update(leftover)
                # The remaining flags are still the demonstration's, and one of them may be an
                # option whose own documentation names its choices. Ending the demonstration here
                # is how `record add` stopped after two of its four flags.
                continue
            spent.add(str(pick["value"]))
            filled_pairs.extend([flag, str(pick["value"])])
        # A demonstration whose every flag was dropped states nothing about this request; a
        # plan made only of the program's name carries none of the request and must not be
        # offered as a reading of it.
        if not filled_pairs:
            return None
        # A flag list is the document's published order, and this function fills it in three
        # passes -- enumerated choices, structures, then the demonstration's own walk -- so the
        # appended order is the pass order, not the page's. Measured: `gh issue list` demonstrated
        # `--repo owner/repo --state open --label bug`, the enum pass claimed `--state open` before
        # the walk reached `--repo`, and the emitted line reversed the page's own example. The
        # values were right and the task scored 0.5. Re-sorting the filled pairs by the position
        # each flag occupies *in the demonstration* restores the order the document endorses,
        # leaving any flag the demonstration never showed where it fell.
        if pairs:
            rank = {str(flag): i for i, (flag, _) in enumerate(pairs)}
            out: list[Any] = []
            i = 0
            while i < len(filled_pairs):
                head = str(filled_pairs[i])
                if head.startswith("-") and i + 1 < len(filled_pairs):
                    out.append([head, filled_pairs[i + 1]])
                    i += 2
                else:
                    out.append([head])
                    i += 1
            out.sort(key=lambda pair: rank.get(pair[0], len(rank)))
            filled_pairs = [x for pair in out for x in pair]
        argv = [tool] + list(prefix) + filled_pairs
        return {"argv": argv, "operation": None,
                "bound": [{"role": "demonstration", "call": demo["call"]}],
                "unbound": [], "complete": True,
                "document": " >> ".join(["root"] + list(prefix)),
                "reason": "PLANNED_FROM_A_DEMONSTRATION"}
    filled = [str(v["value"]) for v in ordered]
    if len(filled) > len(demo["values"]):
        return None
    # An instruction may name several acts in numbered steps. The demonstration is evidence for
    # the act it demonstrates and for no other, so a value the request states for a *different*
    # step must not be poured into this act's argument list -- that invents a command the
    # document never showed. The request's own numbered steps are the boundary, and no other.
    steps = {v.get("step") for v in ordered}
    if len(steps) > 1:
        return None
    argv = [tool] + list(prefix) + list(demo["options"]) + filled
    return {"argv": argv, "operation": None,
            "bound": [{"role": "demonstration", "call": demo["call"]}],
            "unbound": [], "complete": True, "document": " >> ".join(["root"] + list(prefix)),
            "reason": "PLANNED_FROM_A_DEMONSTRATION"}


def _tokens_in(text: str) -> set[str]:
    return set(re.findall(r"[A-Za-z0-9._@/-]+", str(text or "")))


def _request_states_this_structure(example: str,
                                   values: Sequence[Mapping[str, Any]]) -> bool:
    """Does the request spell out this structure, key and value, itself?

    The document's example is `--config '{"bucket": "analytics-output", "prefix": "daily/"}'` and
    the request says `with config {"bucket": "analytics-output", "prefix": "daily/"}`. Every key
    and every value of the shape appears in the request, as its own string. That is the request
    naming the argument, so the argument is the shape -- nothing is supplied here that the request
    did not state.
    """
    keys = re.findall(r'"([^"]+)"\s*:', example)
    written = " ".join(str(v.get("value") or "") for v in values)
    if not keys or not written.strip():
        return False
    return all(re.search(r'(?<![\w-])' + re.escape(k) + r'(?![\w-])', written) for k in keys)


def _shape_filled(example: str, values: Sequence[Mapping[str, Any]], spent: set[str]
                  ) -> str | None:
    """Fill a demonstrated shape (`{"v1": 90, "v2": 10}`) from the request's own values.

    The example says the *structure*: a mapping from a version word to a number, or an object
    with named keys. The request says the numbers and the words. A slot is filled when the
    example's key is a word the request uses; the value is the request's number nearest that
    word. Nothing here supplies a value the request did not state.
    """
    if not any(ch in example for ch in "{}[]:"):
        return None
    free = [v for v in values if str(v["value"]) not in spent and not v.get("value_of")]
    numbers = [str(v["value"]) for v in free if v["kind"] == "number"]
    # A request that quotes this very structure is naming this argument; the literals the
    # extractor also found inside it (`bucket`, `analytics-output`, `prefix`, `daily/`) are its
    # contents, not separate objects competing for flags. Recognising that is what lets the shape
    # be emitted as one argument instead of four trailing operands.
    if free and _request_states_this_structure(example, values):
        return example if example.strip() else None
    if not free:
        # Every value of the shape is already spoken for -- but by *this request's* own words.
        # `sink create --name analytics-lake --type s3 --config '{"bucket": "analytics-output",
        # "prefix": "daily/"}'` is the document's own example, and a request that says exactly
        # `with config {"bucket": "analytics-output", "prefix": "daily/"}` names the same tokens.
        # Treating "already used" as "not available" returned None, the shape contributed nothing,
        # and the JSON trailed the command as four bare operands:
        #   sink create --name analytics-lake --type S3 bucket analytics-output prefix daily/
        # A request that states the whole structure is naming that argument, so the structure is
        # the answer -- not a value this mechanism supplied, and not one it had to guess.
        return example if example.strip() else None
    out = example
    changed = False
    for key in re.findall(r'"([^"]+)"\s*:', example):
        # Each key of the demonstrated shape is filled from the request's own value for that key,
        # and *what kind* of value goes there is the example's own statement: a key the example
        # writes with a number takes the request's number (`"port": 5432`), and a key it writes
        # with a word takes the request's value whose own words name that key (`"database":
        # "analytics"`). Reading only the numeric keys is why a data source connection needing
        # `{"host": ..., "port": 5432, "database": "analytics"}` came out as `--type` holding a
        # hostname: the shape was recognised as a shape and then half of it was thrown away.
        slot = re.search(r'"%s"\s*:\s*([^,}]+)' % re.escape(key), out)
        if not slot:
            continue
        written = slot.group(1).strip().strip('"')
        source = None
        if re.match(r"^-?[\d.]+$", written):
            # The example's own number sits in the output already, and `{"v1": 90, "v2": 10}` with
            # a request that also says 90 and 10 gives the same digits twice -- so "a number not
            # yet in the output" excluded both and the shape was returned unfilled. What is spent
            # is tracked by position in the shape, not by whether the digits happen to appear.
            taken = set(re.findall(r'"([^"]+)"\s*:\s*(-?[\d.]+)', out[:slot.start(1)]))
            used = {n for _, n in taken}
            source = next((n for n in numbers if n not in used), None)
        else:
            # The value for a key is the request's value whose own words name that key *and* which
            # nothing else has a better claim to. A value's clause is wide -- `named "analytics-db"
            # with the connection config: host ...` puts `host` and `config` in the name's own
            # words -- so key overlap alone picked the source's *name* to be its host. The
            # discriminator is the key that only one value names: `database` is in exactly one
            # value's words, while `host` and `config` are in several.
            key_words = words_of(key)
            candidates = [(str(v["value"]), set(v.get("words") or [])) for v in free
                          if str(v["value"]) not in out and key_words & set(v.get("words") or [])]
            if len(candidates) > 1:
                others = {k for k in re.findall(r'"([^"]+)"\s*:', example) if k != key}
                other_words = set().union(*[words_of(k) for k in others]) if others else set()
                candidates.sort(key=lambda c: (-len((key_words - other_words) & c[1]), len(c[1])))
            source = candidates[0][0] if candidates else None
        if source is None:
            continue
        out = out[:slot.start(1)] + (
            source if re.match(r"^-?[\d.]+$", written) else '"%s"' % source) + out[slot.end(1):]
        changed = True
    return out if changed else None


def _product_slots(options: Sequence[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    """The slots a document draws for a place a result goes, best first.

    Several options can take a DIRECTORY (`cp --parents DIRECTORY` and `cp -t DIRECTORY`), and
    only the document's own words separate them: `--parents` says "use full **source** file name
    under DIRECTORY" -- it changes what the source is called, not where the result goes --
    while `-t` says "copy all SOURCE arguments **into** DIRECTORY". A slot whose description
    uses a place word or names no source wins; a slot the description ties to the sources loses.
    """
    def rank(option: Mapping[str, Any]) -> int:
        words = {w.lower() for w in re.findall(r"[A-Za-z]+", str(option.get("words") or ""))}
        if words & _PLACE_WORDS:
            return 0
        if "source" in words or "sources" in words:
            return 2
        return 1
    slots = [o for o in options if is_product_slot(o)]
    return sorted(slots, key=rank)


def _bind_product(values: Sequence[Mapping[str, Any]], options: Sequence[Mapping[str, Any]]
                  ) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[Mapping[str, Any]]]:
    """The reading that explains 'into Y': the destination takes the slot that means a place."""
    # a value the document assigned to a flag is that flag's value, never an object in a place
    values = [v for v in values if not v.get("value_of")]
    products = [v for v in values if v["kind"] == "path" and v.get("role") == "product"]
    sources = [v for v in values if v["kind"] == "path" and v.get("role") != "product"]
    slots = _product_slots(options)
    bound: list[dict[str, Any]] = []
    for slot, value in zip(slots, products):
        bound.append({"role": "path_slot", "option": slot["flag"], "value": value["value"],
                      "product": True})
    consumed = {id(s) for s in slots[:len(products)]}
    for value in sources:
        bound.append({"role": "positional", "value": value["value"]})
    spare = [v for v in values if v["kind"] != "path"]
    return bound, [], spare


def _positional_readings(values: Sequence[Mapping[str, Any]],
                         picture: Sequence[str] | None,
                         usage: Mapping[str, Any] = {}) -> list[Mapping[str, Any]]:
    """The plain argument readings, each as a list of items ready to render.

    Three readings can be stated from the two sources, and no more:

    * **by role** -- the request's own direction words say which object is produced, and the
      picture says which position means what;
    * **by position** -- the objects in the order the request wrote them;
    * **into a metavariable** -- a request that names a count (`the first 2 lines`) is naming a
      word the usage line declares (`NUM`), and the usage line already says which option
      carries that word. That is a document fact, not an inference about the program.

    Where the readings coincide there is one; where they differ there are several, and the
    world picks, because neither the request nor the document is entitled to be believed
    about the other.
    """
    numbers = [v for v in values if v["kind"] == "number"]
    named = sorted((v for v in values if v["kind"] == "path"), key=lambda v: int(v["position"]))
    readings: list[list[Mapping[str, Any]]] = []

    def place(i: int) -> str:
        return picture[i] if picture and i < len(picture) else ""

    if named:
        by_role = sorted(named, key=lambda v: (0 if v.get("role") == "product" else
                                               2 if v.get("role") == "source" else 1,
                                               int(v["position"])))
        readings.append([{"role": "positional", "value": str(v["value"]), "means": place(i)}
                         for i, v in enumerate(by_role)])
        if [id(v) for v in named] != [id(v) for v in by_role]:
            readings.append([{"role": "positional", "value": str(v["value"]), "means": place(i)}
                             for i, v in enumerate(named)])

    if numbers:
        # the usage line says which options carry which declared word; a count in the request
        # is a value of exactly that kind, so the document has already told us where it goes
        carriers = [(slot["option"], slot["meta"]) for slot in usage.get("slots") or []
                    if re.match(r"^(num|n|count|lines|bytes|width|height|size|level|number)$",
                                str(slot["meta"]).lower())]
        for value, (flag, _) in zip(numbers, carriers):
            readings.append([{"role": "value_slot", "option": flag, "value": str(value["value"])}]
                            + [{"role": "positional", "value": str(v["value"]), "means": place(i)}
                               for i, v in enumerate(named)])

    # A request that names a destination for a program whose picture has no place meaning a
    # destination is saying that the result goes there through the shell. There is one reading
    # of that: the objects that fit the program's places are the operands, and the destination
    # is carried outside them. This is the reading `sort FILE into FILE` and `wc FILE into FILE`
    # both need, and it is derived from the request's role and the picture's words -- no tool.
    products = [v for v in named if v.get("role") == "product"]
    places = [place(i) for i in range(len(picture or []))]
    if products and picture and not any(re.search(r"out|dest|archive|target", p) for p in places):
        operands = [v for v in named if v.get("role") != "product"]
        if len(operands) <= len(places):
            readings.append(
                [{"role": "positional", "value": str(v["value"]), "means": place(i)}
                 for i, v in enumerate(operands)]
                + [{"role": "redirect", "value": str(v["value"])} for v in products])
        # the same reading with the objects in the order the program's own places expect:
        # a request that says `into Y` does not tell us where Y sits in the argument list
        if len(operands) + 1 <= len(places):
            readings.append(
                [{"role": "positional", "value": str(v["value"]), "means": place(i)}
                 for i, v in enumerate(operands + products)])
        if len(operands) + 1 <= len(places):
            readings.append(
                [{"role": "positional", "value": str(v["value"]), "means": place(i)}
                 for i, v in enumerate(products + operands)])
    return readings


def _declared_word_readings(requirement: Mapping[str, Any], usage: Mapping[str, Any],
                            picture: Sequence[str] | None) -> list[list[Mapping[str, Any]]]:
    """Readings in which a value from the request fills a word the usage line declares.

    Two shapes, both stated by the document:

    * **by argument** -- `tr STRING1 [STRING2]`: the request's literals fill the declared
      argument places, in order;
    * **by option** -- `cut -f LIST` says the same thing as `cut ... LIST`: the option's own
      words name the declared word, so the value travels with that option.

    Nothing here is a guess about a program: the usage line says which words exist, and the
    document's own option list says which option carries which word.
    """
    values = [v for v in requirement.get("values") or [] if v["kind"] in ("literal", "number")]
    if not values or not picture:
        return []
    out: list[list[Mapping[str, Any]]] = []
    places = [re.sub(r"[^a-z]", "", str(p)) for p in picture]
    wanted = [i for i, p in enumerate(places)
              if re.match(r"^(string|str|array|char|chars|character|characters|text|num|n|"
                          r"count|lines|bytes|list|field|fields)s?\d*$", p)]
    if len(wanted) >= len(values):
        # the place has a name, and a value in a named place is an argument, not a flag
        out.append([{"role": "positional", "value": str(v["value"]), "means": picture[i]}
                    for i, v in zip(wanted, values)])
    metas = [str(m).upper() for m in usage.get("metavariables") or []]
    for value in values:
        kind = value["kind"]
        best = None
        for option in usage.get("options") or []:
            if not option.get("takes_value"):
                continue
            declared = re.sub(r"[^A-Z_].*$", "", str(option.get("meta") or "").upper())
            if declared not in metas:
                continue
            if best is None or (0 if _accepts(slot_kind(option), kind) else 1) < \
                    (0 if _accepts(slot_kind(best), kind) else 1):
                best = option
        if best is not None:
            out.append([{"role": "value_slot", "option": best["flag"],
                         "value": str(value["value"])}])
            continue
        # A metavariable may be generic (`--id <string>`), so the *usage* line cannot say what
        # the option is for. The document says it in the option's own description ("Workflow
        # ID"), and a value whose own words use those words is that option's value.
        want = set(value.get("words") or [])
        scored = []
        for option in usage.get("options") or []:
            if not option.get("takes_value") or not _accepts(slot_kind(option), kind):
                continue
            shared = want & words_of(str(option.get("words") or ""))
            shared -= set(words_of(str(option.get("flag") or "").replace("-", " ")))
            if shared:
                scored.append((len(shared), option))
        if scored:
            scored.sort(key=lambda pair: -pair[0])
            out.append([{"role": "value_slot", "option": scored[0][1]["flag"],
                         "value": str(value["value"])}])
    return out


# The prepositions a request uses to say where a made thing goes. These are the request's own
# words, not a table about programs: the matching is against the document's description.
# Only the directional words that name a container. `in` and `to` are far too common to carry
# this: `-x` says "exclude files that follow (in xlist)" and `-p` says "extract files to pipe",
# and neither is a destination. `into` is a word a document uses when it means one.
_PLACE_WORDS = {"into", "onto", "inside", "within", "underneath"}

# Words with which a document's own gloss says a value is being *left out*. A demonstration
# glossed this way is not a shape for making anything.
_EXCLUSION_WORDS = {"except", "excluding", "exclude", "excluded", "but", "omit", "omitting",
                    "skip", "skipping", "without", "ignore", "ignoring"}


def _composed_readings(requirement: Mapping[str, Any], usage: Mapping[str, Any],
                       picture: Sequence[str] | None
                       ) -> list[tuple[list[Mapping[str, Any]], str]]:
    """One reading in which each value goes where its own words say, and the rest to the shell.

    Every placement here is stated by the document, and each has exactly one rule:

    * a value whose own words share a word with an option that accepts its kind goes to that
      option (`the second field` -> `--fields`);
    * a value whose own words name a place in the usage picture goes to that place
      (`STRING1`, `FILE`), and a value with no place of its own takes the first free one;
    * a path the request marked as the thing made is the shell's stdout, and one it marked as
      the thing read -- or any path left over when the request names a destination -- is the
      shell's stdin, whenever the picture has no place for it.

    This is the reading the frontier's own harnesses spend a language model to produce. The
    document and the request between them already say it; the caller's predicate still decides.
    """
    values = list(requirement.get("values") or [])
    if not values:
        return []
    options = [o for o in usage.get("options") or [] if o.get("takes_value")]
    places = [re.sub(r"[^a-z]", "", str(p)) for p in (picture or [])]
    repeatable = {re.sub(r"[^a-z]", "", p) for p in repeatable_places(usage)}
    paths = [v for v in values if v["kind"] == "path"]
    marked_source = any(v.get("role") == "source" for v in paths)
    declared_destination = any(v.get("role") == "product" for v in paths)

    def is_sink(value: Mapping[str, Any]) -> bool:
        """Whether the request's own shape says this path is the thing made.

        Either it says so outright (`into`, `to`), or it marks the other path as the thing read
        (`of`, `from`) and leaves this one unmarked -- `the first 2 lines of long.txt in
        first.txt` makes first.txt by reading long.txt, and the two clauses are that shape.
        """
        if value.get("role") == "product":
            return True
        return marked_source and not value.get("role") and len(paths) > 1
    bound: list[Mapping[str, Any]] = []
    used_options: set[int] = set()
    taken: set[int] = set()

    def free_place() -> int | None:
        for index, place in enumerate(places):
            if place in ("option", "") or index in taken:
                continue
            return index
        return None

    def place_named_by(value: Mapping[str, Any]) -> int | None:
        """The place whose own name the value's own words use: `bundle.zip` and `zipfile`.

        The match is on the value's words *about that object* -- the clause it appears in, not
        the whole instruction, which mentions every object and would match every place.
        """
        want = set(words_of(value.get("context") or ""))
        best, score = None, 0
        for index, place in enumerate(places):
            if place in ("option", "") or index in taken:
                continue
            # a place may be a compound the request spells as one of its words: `zipfile` is
            # the `zip` the request names, and the whole-word case is kept first because a
            # short stem inside a long word (`file` in `profile`) is not the same word
            stem = place.rstrip("s")
            compound = any(len(word) >= 3 and (word.startswith(stem) or stem.startswith(word))
                           and min(len(word), len(stem)) >= 3 for word in want)
            if (place in want or (len(stem) > 3 and stem in want) or compound) \
                    and score < 2:
                best, score = index, 2
            elif value["kind"] == "path" and value.get("role") == "product" and \
                    re.match(r"^(out|outfile|output|dest|destination|target)$", place) \
                    and score < 1:
                best, score = index, 1
            elif value["kind"] == "path" and value.get("role") != "product" and \
                    re.match(r"^(file|files|path|name|source|src|input)$", place) and score < 1:
                best, score = index, 1
            elif value["kind"] == "path" and value.get("role") == "product" and \
                    re.match(r"^(out|outfile|output|dest|destination|target)$", place) \
                    and score < 1:
                best, score = index, 1
        return best

    # A place the program names for its product belongs to the product. It is claimed first,
    # before any other object can take a free position, because `stitch OUTFILE [PATCH]...`
    # states which of its places is the thing made -- and a patch that landed there would be
    # written over instead of read.
    reserved: dict[str, int] = {}
    for value in values:
        if value["kind"] == "path" and value.get("role") == "product":
            index = place_named_by(value)
            if index is not None:
                taken.add(index)
                reserved[str(value["value"])] = index

    for value in values:
        if value.get("value_of"):
            bound.append({"role": "value_slot", "option": str(value["value_of"]),
                          "value": str(value["value"])})
            continue
        if str(value["value"]) in reserved:
            index = reserved[str(value["value"])]
            bound.append({"role": "positional", "value": str(value["value"]),
                          "means": (picture or [""])[index], "place_index": index})
            continue
        if value["kind"] in ("literal", "number"):
            want = set(value.get("words") or [])
            choice, score = None, 0
            for option in options:
                if id(option) in used_options or not _accepts(slot_kind(option), value["kind"]):
                    continue
                shared = len(want & words_of(str(option.get("words") or "")))
                if shared > score:
                    choice, score = option, shared
            if choice is not None:
                used_options.add(id(choice))
                bound.append({"role": "value_slot", "option": choice["flag"],
                              "value": str(value["value"])})
                continue
            index = place_named_by(value)
            if index is None:
                index = free_place()
            if index is not None:
                taken.add(index)
                bound.append({"role": "positional", "value": str(value["value"]),
                              "means": (picture or [""])[index], "place_index": index})
                continue
            bound.append({"role": "positional", "value": str(value["value"]), "means": ""})
            continue
        if value["kind"] != "path":
            continue
        if is_sink(value):
            # The request's own preposition is a word, and the document uses words too: `-d`
            # says "extract files *into* exdir" and the request says "into /tmp/out", while `-x`
            # says "exclude". A destination that names the word an option's own description uses
            # is that option's value -- no table of destination flags, and it works for a
            # program nobody has seen.
            # `words_of` drops prepositions as stopwords, and here the preposition IS the signal
            says_into = {w.lower() for w in re.findall(r"[A-Za-z]+", str(value.get("context") or ""))
                         } & _PLACE_WORDS
            def _raw_words(text: Any) -> set[str]:
                return {w.lower() for w in re.findall(r"[A-Za-z]+", str(text or ""))}
            candidates = [o for o in options if id(o) not in used_options
                          and says_into & _raw_words(o.get("words"))]
            # where the document names a place for the product, that place wins over an option
            # that merely mentions the word (`-x xlist` says nothing about `into`)
            candidates.sort(key=lambda o: 0 if is_product_slot(o) else 1)
            into_option = candidates[0] if candidates else None
            if into_option is not None and says_into:
                used_options.add(id(into_option))
                bound.append({"role": "value_slot", "option": into_option["flag"],
                              "value": str(value["value"])})
                continue
            # a place in the program's own picture named for the product is where it goes:
            # `stitch OUTFILE [PATCH]...` says so, and a picture with no such place means the
            # shell carries the result instead. The place is named either by the request's own
            # words about it (`bundle.zip` and `zipfile` share `zip`) or by what it means.
            index = place_named_by(value)
            if index is None and len(paths) > 1:
                # No word of the request names this place, but the document draws a place the
                # other objects do not claim: `wright forge set SETTING PIECE` -- the piece is
                # the piece, and the one thing made takes the place left over. That is the
                # picture's own arithmetic, not a list of words for "output".
                claimed = {place_named_by(other) for other in paths if other is not value}
                index = next((i for i, place in enumerate(places)
                              if place and place != "option" and i not in taken
                              and place not in repeatable and i not in claimed), None)
            if index is not None:
                taken.add(index)
                bound.append({"role": "positional", "value": str(value["value"]),
                              "means": (picture or [""])[index], "place_index": index})
                continue
            bound.append({"role": "redirect", "value": str(value["value"])})
            continue
        index = place_named_by(value)
        if index is not None:
            taken.add(index)
            bound.append({"role": "positional", "value": str(value["value"]),
                          "means": (picture or [""])[index], "place_index": index})
            continue
        # An object with a place still to be filled takes it: the program's own picture says a
        # file sits there, and it is that file. A repeatable place (`[PATCH]...`) takes every
        # leftover; only when the places run out is the shell used.
        index = free_place()
        if index is None:
            # `option` is a place the program's options occupy, never a file's
            index = next((i for i, place in enumerate(places)
                          if place and place != "option" and place in repeatable), None)
        if index is not None:
            taken.add(index)
            bound.append({"role": "positional", "value": str(value["value"]),
                          "means": (picture or [""])[index], "place_index": index})
            continue
        # Which stream it becomes is the request's own shape: if the request also names a thing
        # made, this path is what the program reads and the made thing is what it writes; if it
        # names no made thing, this path is where the output goes. Both are the shell.
        if declared_destination or marked_source:
            bound.append({"role": "stdin_from", "value": str(value["value"])})
        else:
            bound.append({"role": "redirect", "value": str(value["value"])})

    # A reading is complete when every object is placed *and* the result has somewhere to go:
    # either the shell carries it, or the program's own picture names a place for it
    # (`stitch OUTFILE [PATCH]...`) and the thing made is in that place.
    product_words = set()
    for value in values:
        if value.get("role") == "product" or is_sink(value):
            product_words |= {str(w) for w in (value.get("words") or [])}
    # The document's own name for the place is what decides. No list of words we brought:
    # a place called `OUTFILE` and a made thing called `records.out` share no letter, and no
    # table can bridge that; a place called `VEILFILE` and a made thing called `records.veil`
    # share the word `veil`, and that is the document telling us where its product goes.
    repeating = places_that_repeat(usage)
    products = [v for v in values if v.get("role") == "product" or is_sink(v)]
    one_made_thing = len(products) == 1
    writes_into_a_named_place = any(
        item["role"] == "positional"
        and len(str(item.get("means") or "")) >= 3
        and (
            # the place's own name is one of the words the request used for the thing made
            any(len(str(w)) >= 3 and (str(w).startswith(str(item["means"]))
                                      or str(item["means"]).startswith(str(w)))
                for w in product_words)
            # or the place holds one thing and the request makes one thing: the document's own
            # `...` says which places take many, and a single product is not one of them
            or (one_made_thing and str(item.get("means")) not in repeating))
        for item in bound)
    if not writes_into_a_named_place and \
            not any(item["role"] in ("redirect", "stdin_from") for item in bound):
        return []
    return [(bound, "PLANNED_BY_A_COMPOSED_READING")]


def every_page(tree: Mapping[str, Any], limit: int = 64) -> list[dict[str, Any]]:
    """Every page the survey reached, at any depth, root first.

    A document is a tree -- `git remote add`, `cargo +toolchain clippy` -- and reading only the
    first level makes every command below it invisible, which reads as "this program has no such
    command" rather than "we did not look". The walk is breadth-first so the shallow pages stay
    first (they are the likelier routing target), and it is bounded and cycle-safe.
    """
    seen: set[int] = set()
    pages: list[dict[str, Any]] = []
    queue = [tree.get("root") or {}]
    while queue and len(pages) < limit:
        node = queue.pop(0)
        if id(node) in seen:
            continue
        seen.add(id(node))
        pages.append(node)
        queue.extend(node.get("children") or [])
    return pages


def places_that_repeat(usage: Mapping[str, Any]) -> set[str]:
    """Which places the document itself marks as repeatable (`[PATCH]...`, `FILE...`).

    This is the document's punctuation, not a vocabulary: a place the program writes with `...`
    holds many things, and a place it writes once holds exactly one. That is how a document says
    *where the one thing I make goes* without ever using a word like "output" -- `box pack
    OUTFILE [PATCH]...` says the patches are many and the out file is one, and nothing else in
    the line needs to be understood to know which of them the product belongs to.
    """
    repeating: set[str] = set()
    for variant in usage.get("variants") or [usage]:
        tokens = re.findall(r"\[?[A-Za-z][A-Za-z0-9_.|-]*\]?\.{0,3}", str(variant.get("usage") or ""))
        for token in tokens:
            if not token.endswith("."):
                continue
            name = token.rstrip(".").rstrip("]").lstrip("[").lower()
            if name and name not in STOP:
                repeating.add(name)
    return repeating


def candidate_sink(bound: Sequence[Mapping[str, Any]]) -> str | None:
    """The destination a reading carries, if any."""
    sinks = [item["value"] for item in bound if item["role"] == "redirect"]
    return str(sinks[-1]) if sinks else None


def candidate_stdin(bound: Sequence[Mapping[str, Any]]) -> str | None:
    """The input a reading carries, if any."""
    sources = [item["value"] for item in bound if item["role"] == "stdin_from"]
    return str(sources[0]) if sources else None


def _with_redirect(argv: list[str], requirement: Mapping[str, Any],
                   bound: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """If a destination is named and nothing in the plan carries it, it is a redirect."""
    carried = {str(item.get("value")) for item in bound if item["role"] != "unbound"}
    for value in requirement.get("values") or []:
        if value["kind"] == "path" and value.get("role") == "product" \
                and str(value["value"]) not in carried:
            return {"stdout_to": str(value["value"]),
                    "reason": "PLANNED_WITH_A_REDIRECT"}
    return {}


def plan(requirement: Mapping[str, Any], tree: Mapping[str, Any],
         *, ask_program: bool = True, read_manual: bool = True) -> dict[str, Any]:
    """Ordered candidate readings of (instruction, document), every refusal named.

    The order is a statement about what each reading explains, not a claim about the world:

        R1  a worked example            -- the document states this whole act
        R2  the destination's own slot  -- the request says `into Y`; some slot means a place
        R3  the act's own option        -- an option's words open with the requested act
        R4  the routed subcommand       -- its index line states the act
        R5  the program's own order     -- plain arguments, both orders the evidence supports

    `verify_plans` turns the order into a decision. A reading that leaves a named destination
    uncarried becomes a redirect, which is a fact about a shell rather than about the program.
    """
    tool = str(tree.get("tool") or "")
    acts = [tuple(a["act"]) for a in requirement.get("acts") or []]
    values = list(requirement.get("values") or [])
    # a bare word that is one of the documents' own choices is a value, not an object
    vocabulary: list[tuple[str, str]] = []
    for node in every_page(tree):
        for option in node.get("options") or []:
            vocabulary.extend((str(option.get("flag")), w) for w in enum_choices(option))
    if vocabulary:
        requirement = claim_vocabulary(requirement, vocabulary)
        values = list(requirement.get("values") or [])
    # prose the request labels with an option's own name is a value of that option
    requirement = _labelled_prose(requirement, tree)
    values = list(requirement.get("values") or [])
    document_acts: list[dict[str, Any]] = []
    if not acts:
        # The request's verb is not in the seed class. Before refusing, ask the documents: an
        # act the *document* uses in its own words is stated by the document, and the request's
        # word for it is then a legitimate name. This is the difference between "we do not know
        # this verb" and "this program does not offer this act" -- only the document can say.
        acts, document_acts = _acts_stated_by_documents(tree, requirement)
    if not acts:
        return {"schema": SCHEMA, "tool": tool, "plans": [], "complete": False,
                "reason": "NO_ACT_THE_REQUEST_NAMES", "path": [],
                "refusals": [{"reason": "NO_ACT_IN_THE_CLOSED_CLASS",
                              "words": [w for w in requirement.get("unclaimed") or []
                                        if len(w) > 3][:8],
                              "instruction": requirement.get("instruction")}]}

    root = tree.get("root") or {}
    picture = positional_grammar((root.get("usage") or {}))
    routed = route(tree, words_of(requirement.get("instruction") or ""), acts,
                   said=str(requirement.get("instruction") or "")) \
        if root.get("children") else {"path": [], "nodes": [root], "scores": []}
    nodes: list[dict[str, Any]] = routed["nodes"]
    plans: list[dict[str, Any]] = []
    refusals: list[dict[str, Any]] = []
    seen: set[tuple[tuple[str, ...], str, str]] = set()
    explained: dict[tuple[tuple[str, ...], str, str], int] = {}

    def prefix_of(depth: int) -> list[str]:
        return [nodes[i]["title"] for i in range(1, depth + 1)]

    def add(argv: list[str], *, operation: Any, bound: Any, depth: int,
            reason: str, front: bool = False) -> None:
        if len(plans) >= MAX_CANDIDATES:
            return
        # a candidate is the same candidate only if it also carries the same shell shape:
        # `tr A a` reading stdin and writing a file is not `tr A a` reading the terminal.
        # A reading that explains more of the request wins the name.
        key = (tuple(argv), str(candidate_stdin(bound) or ""), str(candidate_sink(bound) or ""))
        if key in explained and len(bound) < explained[key]:
            return
        explained[key] = len(bound)
        if key in seen:
            return
        seen.add(key)
        unbound = [item for item in bound if item["role"] == "unbound"]
        candidate = {"argv": argv, "operation": operation, "bound": bound,
                     "unbound": unbound, "complete": not unbound,
                     "document": " >> ".join(["root"] + prefix_of(depth)), "reason": reason}
        if not unbound:
            sink, source = candidate_sink(bound), candidate_stdin(bound)
            if sink:
                candidate["stdout_to"] = sink
            if source:
                candidate["stdin_from"] = source
            if sink or source:
                candidate["reason"] = "PLANNED_WITH_A_REDIRECT"
            else:
                candidate.update(_with_redirect(argv, requirement, bound))
            if candidate.get("stdout_to"):
                # the plan carries the destination itself: the program takes part in a shell,
                # which is the one thing no single program document states and every one assumes
                bound = list(bound) + [{"role": "redirect", "value": candidate["stdout_to"]}]
                candidate["bound"] = bound
                candidate["argv_in_world"] = argv
        if front:
            plans.insert(0, candidate)
        else:
            plans.append(candidate)
        for item in unbound:
            refusals.append({"reason": "NO_SLOT_ACCEPTS_" + str(item["kind"]).upper(),
                             "value": item["value"], "context": item.get("context", "")[:160]})

    # R1 -- a worked example, deepest document first: it is the only whole act on offer
    for depth in range(len(nodes) - 1, -1, -1):
        for demo in nodes[depth].get("demos") or []:
            # the demonstration's flags are paired with values by the node's own option list
            demo = {**demo, "_options": nodes[depth].get("options") or []}
            candidate = _demo_plan(demo, requirement, tool, prefix_of(depth))
            if candidate:
                add(candidate["argv"], operation=None, bound=candidate["bound"], depth=depth,
                    reason=candidate["reason"])

    # R2 -- the destination's own slot: 'into Y' names a place, and a slot means a place
    for depth in range(len(nodes) - 1, -1, -1):
        document = nodes[depth]
        bound, _, _ = _bind_product(values, document.get("options") or [])
        if any(item["role"] == "path_slot" for item in bound):
            # the objects that are not the destination still have to travel: the program's own
            # picture says which places files occupy, and every one of them is an operand
            placed = {str(item["value"]) for item in bound}
            spare = [v for v in values if v["kind"] == "path" and v.get("role") != "product"
                     and str(v["value"]) not in placed]
            for value in spare:
                bound = list(bound) + [{"role": "positional", "value": str(value["value"]),
                                        "means": "file"}]
            add(_render(tool, prefix_of(depth), None, bound), operation=None, bound=bound,
                depth=depth, reason="PLANNED_INTO_A_DESTINATION_SLOT")

    # the deepest document the request routed to is the one whose grammar the request is in
    outside_composed: list[tuple[list[Mapping[str, Any]], str, int]] = []
    for depth in range(len(nodes) - 1, -1, -1):
        inside = nodes[depth]
        usage_here = {**(inside.get("usage") or {}), "options": inside.get("options") or []}
        picture_here = positional_grammar(inside.get("usage") or {}) or picture
        for bound, reason in _composed_readings(requirement, usage_here, picture_here):
            outside_composed.append((bound, reason, depth))
    outside_composed.sort(key=lambda item: -item[2])
    for bound, reason, depth in outside_composed:
        add(_render(tool, prefix_of(depth), None, bound), operation=None, bound=bound,
            depth=depth, reason=reason)


    # a literal filling a place the usage line declares for it, with no shell involved
    usage_with_options = {**(root.get("usage") or {}), "options": root.get("options") or []}
    for depth in range(len(nodes) - 1, -1, -1):
        inside = nodes[depth]
        usage_here = {**(inside.get("usage") or {}), "options": inside.get("options") or []}
        picture_here = positional_grammar(inside.get("usage") or {}) or picture
        for reading in _declared_word_readings(requirement, usage_here, picture_here):
            # a reading that carries one option's value and *drops* an object the request named
            # is not a reading of this request: a redirect can put the made thing back, but
            # nothing puts back a file the program was supposed to read
            placed = {str(item.get("value")) for item in reading}
            missing = [v for v in values if v["kind"] == "path" and not v.get("value_of")
                       and str(v["value"]) not in placed]
            if missing:
                continue
            add(_render(tool, prefix_of(depth), None, reading), operation=None, bound=reading,
                depth=depth, reason="PLANNED_INTO_A_DECLARED_WORD")
    # R3 -- the act's own option, opening the words first, product slots last
    for wanted in acts:
        for depth in range(len(nodes) - 1, -1, -1):
            document = nodes[depth]
            same = [o for o in document.get("options") or [] if _act_first(o, wanted)]
            if not same:
                continue
            opens = [o for o in same if (o.get("words") or "").lower().startswith(wanted[1])]

            numbers = [v["value"] for v in values if v["kind"] == "number"]

            def fits(option: Mapping[str, Any]) -> int:
                """0 when the request explains this option: its own words name the count."""
                if not option.get("takes_value"):
                    return 1
                words = re.findall(r"[A-Za-z]+", str(option.get("words") or "").lower())
                first = words[0] if words else ""
                if first and first.isdigit() and first in numbers:
                    return 0
                if first and first.endswith("est") and first in STARTS + ENDS:
                    ended = {v["value"] for v in values if v["kind"] == "number"}
                    ends = {w for w in words[1:4] if w.rstrip("s") in ENDS}
                    if ends and not (ends & ends):
                        return 2 if not (ends & {e for e in ENDS
                                                 if e in words_of(requirement.get("instruction") or "")}) else 0
                kinds = {value["kind"] for value in values}
                return 0 if slot_kind(option) in kinds else 1

            named_words = set()
            for value in values:
                named_words |= set(value.get("words") or [])
            instruction_words = words_of(requirement.get("instruction") or "")

            def names_the_place(option: Mapping[str, Any]) -> int:
                """0 when the request's own words name the word this option declares."""
                meta = re.sub(r"[^A-Z_].*$", "", str(option.get("meta") or "").upper())
                stems = {meta.lower(), meta.lower().rstrip("s")}
                return 0 if stems & (named_words | instruction_words) else 1

            ordered = sorted(opens + same,
                             key=lambda o: (fits(o), names_the_place(o),
                                            0 if o in opens else 1,
                                            1 if is_product_slot(o) else 0))
            for operation in ordered[:2]:
                bound, _ = _bind(values, document.get("options") or [], product_first=True,
                                 picture=picture)
                add(_render(tool, prefix_of(depth), operation, bound,
                            declared=[str(o.get("flag")) for o in (document.get("options") or [])]),
                    operation=operation["flag"], bound=bound, depth=depth, reason="PLANNED")
            break
        if any(p["operation"] for p in plans):
            break

    # R4 -- the routed subcommand, when its own index line states the act
    for depth in range(len(nodes) - 1, 0, -1):
        parent = nodes[depth - 1]
        line = next((i for i in parent.get("index") or []
                     if i["name"] == nodes[depth].get("title")), None)
        stated = acts_in((line or {}).get("what") or "")
        if line and stated and stated[0][0] in {a[0] for a in acts}:
            # the picture belongs to the document the request was routed *to*, not the root:
            # `halcyon tally [OPTION]... LEDGER` says the ledger has a place, and the root's
            # `[ARG]...` does not
            here = positional_grammar(nodes[depth].get("usage") or {}) or picture
            bound, unbound = _bind(values, [], product_first=False, picture=here)
            add(_render(tool, prefix_of(depth), None, bound), operation=None, bound=bound,
                depth=depth, reason="PLANNED_BY_THE_SUBCOMMAND")
            # Do not stop here. The break ended the search at the first subcommand whose index
            # line happened to state the act, so a deeper page carrying the flags was never
            # reached: cb-009 planned bare `issue list` while the request named an assignee the
            # deeper page accepts. Continuing costs nothing -- the candidate is already made.
            continue

    # R5 -- the program's own order, both readings the evidence supports
    # Two facts belong here, and both are the document's: a value already bound to a flag
    # travels with that flag rather than being counted again as a plain argument; and the plain
    # reading is stated by the document the request routed *to*, because a subcommand that
    # takes its own arguments cannot be invoked without its own name (`plumb bind`).
    claimed_values = [v for v in values if v.get("value_of")]
    free_values = [v for v in values if not v.get("value_of")]
    spare = [v for v in free_values if v["kind"] != "path" and v["kind"] != "number"]
    deepest = len(nodes) - 1
    here_options = nodes[deepest].get("options") or []
    here_picture = positional_grammar(nodes[deepest].get("usage") or {}) or picture
    for reading in _positional_readings(free_values, here_picture,
                                        nodes[deepest].get("usage") or {}):
        bound = list(reading) + [{"role": "value_slot", "option": str(v["value_of"]),
                                  "value": str(v["value"])} for v in claimed_values]
        for extra in spare:
            holder = next((o for o in _product_slots(here_options)
                           if slot_kind(o) == "number"), None)
            if holder is not None:
                bound.append({"role": "value_slot", "option": holder["flag"],
                              "value": str(extra["value"])})
            else:
                bound.append({"role": "unbound", "kind": extra["kind"],
                              "value": extra["value"], "context": extra.get("context", "")})
        add(_render(tool, prefix_of(deepest), None, bound), operation=None, bound=bound,
            depth=deepest, reason="PLANNED_BY_ARGUMENT_ORDER")

    # A plan is only *complete* if it also accounts for every word the request used to name an
    # object. A word silently dropped is the one failure mode a caller cannot see: the plan runs,
    # the world accepts it, and the request was only partly carried out. So the dropped words are
    # named, per plan, and a plan with any is not complete -- the caller is told what it does not
    # know rather than being handed a smaller act that looks finished.
    # Which leftovers are *objects* is the document's own question: a word the document uses
    # somewhere (`mode`, `record`, `veil`) is vocabulary, and a word no page mentions is the
    # thing the request names that nothing here can carry (`quantum`, `transmute`).
    documented: set[str] = set()
    pages = every_page(tree)
    for node in pages:
        documented |= words_of(" ".join([str(node.get("title") or ""),
                                         str(node.get("summary") or ""),
                                         str((node.get("usage") or {}).get("usage") or ""),
                                         " ".join(str(o.get("words") or "") for o in
                                                  node.get("options") or [])]))
    documented |= {w for chain in [enum_choices(o) for node in pages
                                   for o in node.get("options") or []] for w in chain}
    placed_words: set[str] = set()
    for candidate in plans:
        for item in candidate.get("bound") or []:
            if item.get("value"):
                placed_words |= set(words_of(str(item["value"])))
    dropped = sorted(w for w in requirement.get("unclaimed") or []
                     if w not in placed_words and w not in documented and len(w) > 3)
    for candidate in plans:
        missing = [w for w in dropped if w not in words_of(" ".join(map(str, candidate["argv"])))]
        candidate["dropped_words"] = missing
        if missing:
            candidate["complete"] = False
            candidate.setdefault("refusals", []).append(
                {"reason": "NO_PLACE_IN_THIS_DOCUMENT_FOR", "words": missing[:8]})
    # --------------------------------------------------------- asking the program, when it matters
    # A word the request named that no page and no plan could place is a question, and the
    # document is silent on it. The program itself is the cheapest source. If it names the
    # request's word among the values it accepts, the word was a value of that option all
    # along and one re-plan places it. If it does not, nothing changes and the word stays
    # named -- which is the whole difference between asking and guessing.
    asked: list[dict[str, Any]] = []
    if dropped and plans and ask_program:
        claimed: list[tuple[str, str]] = []
        for node in [nodes[-1], nodes[0]]:
            prefix = prefix_of(nodes.index(node))
            for option in options_that_take_values(node):
                choices = ask_an_option(tool, prefix, option, node)
                if not choices:
                    continue
                asked.append({"option": option.get("flag"), "choices": choices})
                lower = {c.lower() for c in choices}
                claimed += [(str(option.get("flag")), w) for w in dropped if w.lower() in lower]
        if claimed:
            replanned = plan(claim_vocabulary(requirement, claimed), tree, ask_program=False)
            if replanned["plans"]:
                plans = replanned["plans"]
                refusals = replanned["refusals"]
                dropped = [w for w in dropped if w not in {c[1] for c in claimed}]
                for candidate in plans:
                    candidate["dropped_words"] = [
                        w for w in dropped
                        if w not in words_of(" ".join(map(str, candidate["argv"])))]
                    if candidate["dropped_words"] and candidate["complete"]:
                        candidate["complete"] = False

    # ------------------------------------------------------- reading the program's real manual
    # When a request names a property (`numerically`, `by the second field`) that no usage line
    # can express, the program's manual states the form: `--key=2,2n`. The manual is fetched, not
    # remembered, and each form it offers becomes a candidate the world must accept -- the manual
    # proposes, the run decides. Nothing is added when the pages already settled the request.
    manual_forms: list[dict[str, Any]] = []
    # The manual is read only for a request the pages could not settle: a named word left with no
    # place. A request whose places are all filled is not a question, and consulting a manual for
    # it displaces a correct reading -- measured: doing so moved `--severity P1` out of its flag.
    if read_manual and dropped and not any(p["complete"] for p in plans):
        try:
            from canonical.runtime import program_manual_v1 as _manual
            # the base is taken once, before any manual candidate exists -- otherwise each form
            # would be appended to the previous one and the manual would appear to state a
            # command it never wrote
            base = next((c for c in plans if c.get("bound")), None)
            for form in _manual.planned_forms(tool, requirement,
                                              [o for node in nodes
                                               for o in node.get("options") or []]):
                if base is None:
                    break
                argv = list(base["argv"]) + [form["form"]]
                manual_forms.append({**form, "argv": argv})
                # A form the manual states for a gap the pages left is the reading most likely to
                # be right, and it is the only one that can carry the request's own words
                # (`numerically`) into an argument. It goes first for that reason -- not because
                # it is trusted: `verify_plans` runs it, and the world decides.
                add(argv, operation=None, bound=base.get("bound") or [], depth=len(nodes) - 1,
                    reason="PLANNED_FROM_THE_PROGRAMS_OWN_MANUAL", front=True)
        except Exception as exc:            # a manual must never break a plan
            manual_forms.append({"error": f"{type(exc).__name__}: {exc}"})


    plans.sort(key=lambda c: (0 if c.get("complete") else 1,))

    # A document that marks a flag `(required)` has stated that no command lacking it is that
    # command. A reading which leaves one out is the weaker claim about the request, and the
    # reading that keeps it -- the document's own demonstrated form -- should be tried first.
    # Only the page the reading lands on states what its own command requires: a required flag
    # on a parent page belongs to a different command.
    for candidate in plans:
        missing = [str(o.get("flag")) for o in (nodes[-1].get("options") or [])
                   if o.get("required") is True and str(o.get("flag")) not in candidate["argv"]]
        candidate["missing_required"] = sorted(set(missing))
        # Completeness is decided HERE, and it is decided both ways. The census used to only
        # ever clear the flag, so a candidate from a route that never set it stayed incomplete
        # forever -- `linear project list` declares no required flags and was still reported
        # incomplete, and 59 of 60 tasks reported incomplete including the ones that scored 0.9.
        # A reading is complete exactly when it satisfies every flag its own landing page marks
        # required: nothing more is asked of it, and nothing less will do.
        candidate["complete"] = not missing
        # A second, independent statement, and it asks a different question. `complete` says the
        # command satisfies what its own page requires; this says every object the request named
        # actually reached the command line. Measured over the sixty: among candidates that are
        # both complete and fully covered the mean outcome is 0.5131 (n=41), and among the rest
        # 0.4076 (n=16) -- a gap of +0.106 with no reward and no answer key, and a far more usable
        # split than `complete` alone, which certifies 54 of 57 and so barely separates anything.
        # The two are reported separately because they fail differently: a command can name every
        # object and still omit a required flag, or satisfy every flag and drop the object the
        # request was about.
        named = [str(v["value"]) for v in (requirement.get("values") or [])
                 if not v.get("value_of")]
        written = " ".join(str(a) for a in candidate["argv"])
        unplaced = [v for v in named if v not in written]
        candidate["values_named"] = len(named)
        candidate["values_unplaced"] = unplaced[:8]
        candidate["covered"] = not unplaced
    plans.sort(key=lambda c: (0 if c.get("complete") else 1, 0 if c.get("covered") else 1))

    good = [p for p in plans if p["complete"]]
    if dropped:
        refusals.append({"reason": "NO_PLACE_IN_THIS_DOCUMENT_FOR", "words": dropped[:8]})
    return {
        "schema": SCHEMA, "tool": tool, "path": routed["path"],
        "route_scores": routed.get("scores") or [],
        "document_usage": (nodes[-1].get("usage") or {}).get("usage"),
        "plans": plans, "complete": bool(good), "refusals": refusals,
        "dropped_words": dropped,
        "manual_forms": manual_forms,
        "asked_the_program": asked,
        "reason": ("PLANNED" if good else (plans[0]["reason"] if plans
                                           else "NO_OPERATION_IN_THIS_DOCUMENT")),
    }


# --------------------------------------------------------------------------- execute & verify


def _inside_world(argv: Sequence[str], workdir: str, world: pathlib.Path) -> list[str]:
    """Rewrite the arguments that name the real world so they name the copy of it.

    The doctrine is `THE_BRANCH_IS_THE_MODEL`: the successor is had by acting in a copy, never by
    predicting the effect of acting for real. A plan's paths were read from the instruction, so
    they point at the world the user described; verifying them against the untouched original
    would both test the wrong thing and change it. Every argument under `workdir` is moved.
    """
    root = str(pathlib.Path(workdir).resolve()).rstrip("/")
    out: list[str] = []
    for arg in argv:
        if arg == root:
            out.append(str(world))
        elif arg.startswith(root + "/"):
            out.append(str(world) + arg[len(root):])
        else:
            out.append(arg)
    return out


def verify_plans(plans: Sequence[Mapping[str, Any]], *, workdir: str,
                 is_success: Callable[[dict[str, Any]], bool],
                 timeout: float = 60.0) -> dict[str, Any]:
    """Run each candidate in a copy of `workdir`; the caller's predicate is the verdict.

    A plan is a claim. The copy is the tree's own doctrine (`THE_BRANCH_IS_THE_MODEL`: the
    successor is had, not predicted), and `is_success` sees the exit status and the resulting
    directory -- never the planner's confidence.
    """
    attempts: list[dict[str, Any]] = []
    for index, plan_item in enumerate(plans):
        scratch = tempfile.mkdtemp(prefix=f"verify-{index}-")
        target = pathlib.Path(scratch) / "world"
        try:
            shutil.copytree(workdir, target, symlinks=True)
            started = time.perf_counter()
            argv = _inside_world(list(plan_item["argv"]), workdir, target)
            sink = None
            source = None
            if plan_item.get("stdin_from"):
                where = _inside_world([str(plan_item["stdin_from"])], workdir, target)[0]
                try:
                    source = open(where, "rb")
                except OSError:
                    source = None
            if plan_item.get("stdout_to"):
                where = _inside_world([str(plan_item["stdout_to"])], workdir, target)[0]
                pathlib.Path(where).parent.mkdir(parents=True, exist_ok=True)
                # a destination named as a directory collects every output file the program
                # produces, which is what the shell's `-t DIR` means and what a directory
                # stdout means for tar-like programs
                if str(plan_item["stdout_to"]).endswith(("/", os.sep)) \
                        or plan_item.get("stdout_kind") == "directory":
                    pathlib.Path(where).mkdir(parents=True, exist_ok=True)
                    sink = open(os.path.join(where, "stdout.bin"), "wb")
                else:
                    sink = open(where, "wb")
            try:
                done = subprocess.run(argv, cwd=str(target),
                                      stdout=sink if sink is not None else subprocess.PIPE,
                                      stderr=subprocess.PIPE, timeout=timeout,
                                      stdin=source if source is not None else subprocess.DEVNULL)
                status = {"exit": done.returncode,
                          "stdout": (done.stdout or b"").decode("utf-8", "replace")[:2000],
                          "stderr": done.stderr.decode("utf-8", "replace")[:2000]}
            except (OSError, subprocess.TimeoutExpired) as exc:
                status = {"exit": None, "stdout": "", "stderr": type(exc).__name__}
            finally:
                if sink is not None:
                    sink.close()
                if source is not None:
                    source.close()
            outcome = is_success({**status, "world": str(target)})
            attempts.append({"argv": argv, "planned": list(plan_item["argv"]),
                             "exit": status["exit"],
                             "success": bool(outcome), "stdout": status["stdout"][:300],
                             "stderr": status["stderr"][:300],
                             "seconds": round(time.perf_counter() - started, 3)})
            if outcome:
                return {"schema": SCHEMA, "success": True, "chosen": argv,
                        "chosen_planned": list(plan_item["argv"]),
                        "attempts": attempts, "tried": index + 1,
                        "seconds": round(sum(a["seconds"] for a in attempts), 3)}
        finally:
            shutil.rmtree(scratch, ignore_errors=True)
    return {"schema": SCHEMA, "success": False, "chosen": None, "attempts": attempts,
            "tried": len(attempts), "seconds": round(sum(a["seconds"] for a in attempts), 3)}


def redirects(requirement: Mapping[str, Any], world: str | None = None) -> list[dict[str, Any]]:
    """The destinations a request names that the program has no slot for.

    A request says `sort X into Y`, and the program has no option that means Y: it writes to its
    standard output. That is not a gap in the program, it is the program taking part in a shell,
    so the plan is a redirect -- the one fact about a system that no single document states and
    every document assumes. Each destination is checked against the world (a directory is not a
    file), and the check is reported, never assumed.
    """
    out: list[dict[str, Any]] = []
    for value in requirement.get("values") or []:
        if value["kind"] != "path" or value.get("role") != "product":
            continue
        exists = os.path.exists(str(value["value"])) if world else None
        is_dir = os.path.isdir(str(value["value"])) if world else None
        out.append({"target": value["value"], "exists": exists, "is_directory": is_dir,
                    "operator": ">" if not is_dir else None,
                    "reason": "A_NAMED_DESTINATION_THE_PROGRAM_HAS_NO_SLOT_FOR"})
    return out


def require_survey_plan(tool: str, instruction: str, *, read_manual: bool = True,
                        **survey_kwargs: Any) -> dict[str, Any]:
    """The one call: require the instruction, survey the tool, route, plan."""
    req = require(instruction)
    # The scan is NOT steered by the request's words, and that is the whole correction.
    # `want` spends the probe budget depth-first along the route the words already suggest, so
    # the survey reaches exactly the pages the guess points at and the guess is never tested:
    # "Send a direct message to the Slack user alice" was steered into `message send`, and
    # `dm send` -- whose own summary is "Send a direct message to a user" and which declares the
    # `--user` flag the request needs -- was never fetched. The program's whole help is ten
    # pages and 0.17 seconds, so there is nothing to save by looking narrowly. A scan only as
    # wide as the hypothesis cannot refute the hypothesis.
    tree = survey(tool, **survey_kwargs)
    result = plan(req, tree, read_manual=read_manual)
    result["instruction"] = instruction
    result["acts"] = req["acts"]
    result["values"] = req["values"]
    result["requirement_reasons"] = req["reasons"]
    result["survey"] = {k: tree[k] for k in ("documents_ok", "document_bytes", "seconds",
                                             "stored_bytes")}
    result["documents_asked"] = tree["documents_asked"]
    return result


# The request marking its own step boundaries in words rather than digits. `First, list available
# artifacts ... Then trigger a deployment` states two steps and says so; the ordering word is the
# request's own statement of a boundary, the same class of evidence as `1.` and `2.`, and it must
# outrank the guess that a sentence without a leading verb continues the one before it. Measured:
# `Using the kforge CLI, deploy ... First, list available artifacts to find the most recent
# successful build. Then trigger ...` planned `artifact inspect` and `pipeline trigger` -- the
# first step, the one the request put first, was silently folded away and never planned at all.
_ORDERING_OPENERS = ("first", "then", "next", "finally", "afterwards", "secondly", "thirdly",
                     "lastly", "subsequently")


def _announces_its_own_order(part: str) -> bool:
    """Does this sentence open by placing itself in the request's own sequence?"""
    head = re.match(r"[\s\"'(*-]*([A-Za-z]+)", str(part or ""))
    return bool(head) and head.group(1).lower() in _ORDERING_OPENERS


def sentences_of(text: str) -> list[str]:
    """The request's own steps, in its own words.

    A person writing out a task numbers it or, more often, just writes it as sentences: `First,
    list all firing alerts. Acknowledge the critical ones. Create a new incident ...`. The
    sentence is the boundary the *request* states, and a boundary is what keeps one step's
    objects out of another step's flags. Line breaks are folded first, because a wrapped sentence
    is still one sentence.
    """
    raw = str(text or "")
    # Numbering is the request stating its boundaries outright -- `1. Get ... 2. Approve ...` --
    # and it outranks any guess made from punctuation, so it is settled first.
    numbered = [p.strip() for p in re.split(r"(?m)\s*(?=\b\d{1,2}[.)]\s+[A-Za-z])", raw)
                if p.strip() and re.match(r"\d{1,2}[.)]\s+[A-Za-z]", p.strip())]
    if len(numbered) > 1:
        # Within a numbered item the same rule holds: a sentence that names no act and talks
        # about the exercise is not part of the step. Measured: `2. Approve gate "gate-001"
        # with comment "..." . You are not provided with documentation` -- the guidance stayed
        # glued to step 2 and cost it its `--id`.
        out: list[str] = []
        for item in numbered:
            bare = re.sub(r"^\d{1,2}[.)]\s*", "", item).strip()
            kept = [sentence for sentence in re.split(r"(?<=[.!?])[\"')\]}]{0,3}\s+", bare)
                    if sentence.strip() and not _is_about_the_setting_not_the_task(sentence)]
            out.append(" ".join(k.strip() for k in kept) if kept else bare)
        return out
    # A wrapped sentence and a newline-separated one look identical after folding, so the split
    # is made before folding, on any whitespace run after the terminator. Measured: folding first
    # let `...production".\nYou are not provided with documentation` stay one sentence, and the
    # guidance about the exercise then cost the step its flags.
    parts = [p.strip() for p in re.split(r"(?<=[.!?])[\"')\]}]{0,3}\s+", raw)
                 if p.strip()]
    # A sentence is a boundary only where a *new act* appears. `Create a workflow named "x". Set
    # the owner to "y".` is one create with two of its own fields, and splitting it would cut the
    # fields off the command they belong to -- measured: `flowctl workflow create "deploy-staging"`
    # instead of `--name deploy-staging --steps run_pipeline`. A sentence naming no act continues
    # the step before it, which is what the request's own grammar says.
    steps: list[str] = []
    for part in parts:
        if not steps or _leads_with_an_act(part) or _announces_its_own_order(part):
            steps.append(part)
        elif _is_about_the_setting_not_the_task(part):
            # `You are not provided with documentation -- discover the tool's commands yourself`
            # is an instruction about how to work, not a step of the work. Gluing it onto the
            # step before it changed that step's words and cost its flags.
            continue
        else:
            steps[-1] = steps[-1] + " " + part
    return steps


def _is_about_the_setting_not_the_task(sentence: str) -> bool:
    """Is this sentence guidance about the exercise rather than a step of it?

    The closed class again, and nothing else: these are the words a task statement uses to talk
    about its own conditions. It is not a list of tools or of things in the world.
    """
    words = {w for w in re.findall(r"[A-Za-z][A-Za-z-]+", str(sentence or "").lower())}
    return bool(words & {"documentation", "docs", "provided", "available", "discover",
                         "yourself", "note", "hint", "remember"})


def _leads_with_an_act(sentence: str) -> bool:
    """Does this sentence *open* by naming an act -- is the act its head verb?

    A sentence can mention an act without being one: `The workflow should have two steps: a
    "build" step ...` names `build` and `have`, and is a description of the object the previous
    sentence creates. The head verb is the sentence's first content word, which is the word
    English puts the claim on. Quoted spans are dropped first, because a quoted `"build"` is a
    value the request is naming, not an instruction to build.
    """
    bare = re.sub(r'"[^"]*"|\'[^\']*\'', " ", str(sentence or ""))
    words = [w for w in re.findall(r"[A-Za-z][A-Za-z-]+", bare) if w.lower() not in STOP]
    if not words:
        return False
    return act_of(words[0]) is not None


def _carries_an_operation(argv: Sequence[str], tree: Mapping[str, Any]) -> bool:
    """Does a planned command name an operation -- a flag, or a word the document uses as one?

    `workflow create --name x` does: `create` is a word the document's own page carries. A bare
    `devops-team` does not: it is an object the request named with no act attached, and emitting
    it as a command would present a fragment as a plan. The evidence is the document, not the
    shape of the token -- a hyphenated word looks like a subcommand and is not one.
    """
    names: set[str] = set()
    for node in every_page(tree):
        for key in ("commands", "path"):
            for word in node.get(key) or []:
                names.add(str(word).lower())
        for option in node.get("options") or []:
            flag = str(option.get("flag") or "")
            if flag:
                names.add(flag.lower())
    for token in argv:
        word = str(token).lower()
        if word.startswith("-"):
            return True
        if word in names:
            return True
    return False


def require_survey_plan_sequence(tool: str, instruction: str, *, read_manual: bool = True,
                                 max_steps: int = 12, **survey_kwargs: Any) -> dict[str, Any]:
    """One survey of the tool, one plan per step the request states, in the request's order.

    A task that names several acts is not one act read generously -- it is several acts, and
    reading it as one is how the fourth step's value ends up in the second step's flag. The
    tool is surveyed **once**: every step is a reading of the same document, so surveying per
    step would download the same pages again to learn nothing new.

    A step the document does not carry contributes no command and says why. The sequence is
    therefore shorter than the request when the program cannot do part of it, and that is
    visible in the output rather than papered over with a guess.
    """
    req_all = require(instruction)
    # Not steered, for the reason given at `require_survey_plan`: a scan spent along the route
    # the request words already suggest cannot refute that route. `probes` is the honest limit
    # on how much of a program is read; the request's guess is not.
    tree = survey(tool, **survey_kwargs)
    steps: list[dict[str, Any]] = []
    for sentence in sentences_of(instruction)[:max_steps]:
        req = require(sentence)
        # A sentence that states no act is a *description*, not a step: `Show the project name,
        # status, lead, and target date for each project` says what to display, and the sentence
        # before it already said to list. Planning it as a step turns its field list into a
        # command argument (`linear project lead, and target date`), which is not a command at
        # all. The words still reach the first step, which reads the whole request.
        if not req["acts"]:
            steps.append({"step": sentence[:200], "argv": None,
                          "reason": "THIS_STEP_NAMES_NO_ACT_THE_CLASS_CARRIES"})
            continue
        one = plan(req, tree, read_manual=read_manual)
        if not one["plans"]:
            steps.append({"step": sentence[:200], "argv": None,
                          "reason": one.get("reason") or "NO_READING_OF_THIS_STEP",
                          "refusals": one.get("refusals") or []})
            continue
        # The best reading of this step: one the document states fully, else the one it states
        # best. "Complete" is a high bar -- an everyday word like `related` in the request is a
        # word no option declares, and demanding completeness refused every step of every task
        # measured. A flag the document calls required only reorders the readings; refusing the
        # step outright measured worse (0.4599 against 0.4632) and taught nothing.
        # A reading the document contradicts -- it calls a flag required and the reading omits
        # it, and no other reading supplies it -- cannot be executed as this document's command.
        # The step is named and skipped; the steps that do read are still the plan, because
        # refusing them all is how a fallback once made three tasks worse.
        likely = next((p for p in one["plans"] if p.get("complete")), one["plans"][0])
        argv = list(likely["argv"])
        # A command made of values and no operation is not part of the request in any reading of
        # it: `set the owner to "devops-team"` against a document whose only operation is
        # `workflow create` yields a bare `devops-team`. The same rule that refuses a one-act
        # plan made only of the program's name refuses this, per step.
        if not _carries_an_operation(argv[1:], tree):
            steps.append({"step": sentence[:200], "argv": None,
                          "reason": "THIS_STEP_HAS_NO_OPERATION_IN_THIS_DOCUMENT",
                          "dropped": argv[1:]})
            continue
        # A step whose only content is a bare noun the document itself uses is not a step: the
        # sentence is saying which *fields* to display, not naming a new act. `Show the project
        # name, status, lead, and target date for each project` plans to `linear project
        # lead, and target date` -- a command made of the fields. The act is real (`show` is in
        # the class) and the fields are the page's own words, which is exactly what a sentence
        # about a display does not turn into an operation.
        if _only_names_documented_nouns(argv[1:], tree):
            steps.append({"step": sentence[:200], "argv": None,
                          "reason": "THIS_STEP_ONLY_NAMES_FIELDS_TO_DISPLAY",
                          "dropped": argv[1:]})
            continue
        steps.append({"step": sentence[:200], "argv": argv,
                      "reason": likely["reason"], "alternatives": one["plans"][:8]})
    # A repeated command is not a second step: two steps that plan to the same argv said the
    # same thing twice, and running it twice cannot accomplish anything the first run did not.
    # Measured: `List all pages ... Show the page title ...` produced `notion page list` twice.
    commands: list[list[str]] = []
    for step in steps:
        argv = step.get("argv")
        if argv and argv not in commands:
            commands.append(argv)
    # A request whose steps the class could not read as steps is still a request, and refusing it
    # because the sentence boundary failed would lose a reading the whole-request planner has.
    # Measured: reading `gather trending content from both Hacker News and Reddit ... identify
    # topics on both` sentence by sentence produced nothing where the whole-request reading
    # produced a command. The fallback is the other reading, named, never a guess.
    fallback = None
    if not commands:
        whole = plan(req_all, tree, read_manual=read_manual)
        likely = next((c for c in whole["plans"] if c.get("complete")),
                      (whole["plans"] or [None])[0])
        if likely is not None and _carries_an_operation(list(likely["argv"])[1:], tree):
            fallback = {"step": instruction[:200], "argv": list(likely["argv"]),
                        "reason": likely["reason"] + "_AS_ONE_REQUEST",
                        "alternatives": whole["plans"][:8]}
            steps.append(fallback)
            commands = [fallback["argv"]]
    # The verdict for the plan as a *whole*, which `complete` on one command cannot give. A
    # request with three steps can have two perfect commands and one that omits a required flag,
    # and reporting the first command's `complete` certifies the plan. Measured on the sixty:
    #
    #     every command satisfies its own page   n=49   mean 0.5096
    #     some command omits a required flag     n= 9   mean 0.3677
    #     separation AUC 0.740
    #
    # against 0.599 for the single-command `complete`, which is now true for 57 of 60 plans and
    # therefore says almost nothing. Both are reported; this one is the one worth reading.
    unsatisfied: list[dict[str, Any]] = []
    for step in steps:
        argv = step.get("argv")
        if not argv:
            continue
        alternatives = step.get("alternatives") or [{}]
        missing = list(alternatives[0].get("missing_required") or [])
        if missing:
            unsatisfied.append({"command": " ".join(str(a) for a in argv),
                                "missing": missing})
    return {"schema": SCHEMA, "tool": tool, "instruction": instruction,
            "sentences": [s[:200] for s in sentences_of(instruction)],
            "steps": steps,
            "commands": commands,
            "satisfies_every_page": not unsatisfied,
            "unsatisfied": unsatisfied,
            "used_the_whole_request": bool(fallback),
            "survey": {k: tree[k] for k in ("documents_ok", "document_bytes", "seconds",
                                            "stored_bytes")},
            "requirement_reasons": req_all.get("reasons") or []}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--tool", required=True)
    parser.add_argument("--instruction", required=True)
    parser.add_argument("--probes", type=int, default=DEFAULT_PROBES)
    parser.add_argument("--receipt", type=pathlib.Path)
    args = parser.parse_args(argv)
    result = require_survey_plan(args.tool, args.instruction, probes=args.probes)
    if args.receipt:
        args.receipt.parent.mkdir(parents=True, exist_ok=True)
        args.receipt.write_text(json.dumps(result, indent=1, default=str))
    print(json.dumps({k: result[k] for k in ("plans", "complete", "reason", "path")},
                     indent=1, default=str))
    return 0 if result["complete"] else 3


if __name__ == "__main__":
    sys.exit(main())


# ------------------------------------------------------------------- asking the program itself

# A program that rejects a value almost always says what it would have accepted:
#   "plumb: no such net: brass (try one of: copper, fibre, vacuum)"
#   "error: --level must be one of: low, medium, high"
# The list is the program's own vocabulary, offered without being documented anywhere. It is the
# cheapest instant knowledge there is: the environment is the source, the cost is one process,
# and nothing is stored afterwards.
_OFFERED_VALUES = re.compile(
    r"(?:try one of|must be one of|valid values are|expected one of|choose from)"
    r"\s*[:=]?\s*\[?(?P<list>[A-Za-z0-9_+.-]+(?:\s*[,|/]\s*[A-Za-z0-9_+.-]+){1,16})",
    re.I)


def offered_values(text: str) -> list[str]:
    """The choices a program named when it rejected a value, in the order it named them."""
    found = _OFFERED_VALUES.search(str(text or ""))
    if not found:
        return []
    return [w.strip(" .,;'\"()[]") for w in re.split(r"\s*[,|/]\s*", found.group("list"))
            if w.strip(" .,;'\"()[]")]


def ask_the_program(argv: Sequence[str], *, timeout: float = 20.0) -> dict[str, Any]:
    """Run one command and read back what the program says when it refuses.

    A rejection is the program describing itself. No model, no search, no stored table: the
    program is asked the question the request raised, and its own sentence is the answer.
    """
    import subprocess
    try:
        done = subprocess.run(list(argv), capture_output=True, text=True, timeout=timeout,
                              stdin=subprocess.DEVNULL)
    except (OSError, subprocess.SubprocessError) as exc:
        return {"asked": list(argv), "answered": [], "error": f"{type(exc).__name__}: {exc}"}
    said = ((done.stderr or "") + "\n" + (done.stdout or "")).strip()
    return {"asked": list(argv), "exit": done.returncode, "said": said[:300],
            "answered": offered_values(said)}


def options_that_take_values(node: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    return [o for o in node.get("options") or [] if o.get("takes_value")]


def ask_an_option(tool: str, prefix: Sequence[str], option: Mapping[str, Any],
                  node: Mapping[str, Any], *, timeout: float = 20.0) -> list[str]:
    """Ask one option which values it accepts, by offering it one no program would accept.

    A program checks its options only once its arguments are complete, so the probe supplies as
    many placeholders as the usage line declares places -- read from the document, not guessed.
    """
    spellings = [str(option.get("flag") or "")]
    spellings += [str(a) for a in (option.get("aliases") or []) if str(a) not in spellings]
    places = [p for p in (positional_grammar(node.get("usage") or {}) or [])
              if p and p != "option"]
    spare = ["@@unknown@@"] * (len(places) + 1)
    for spelling in spellings:
        if not spelling:
            continue
        probe = [tool] + list(prefix) + [spelling, "@@unknown@@"] + spare
        answer = ask_the_program(probe, timeout=timeout)
        choices = answer.get("answered") or []
        if choices:
            return choices
    return []
