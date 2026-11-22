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

QUOTED = re.compile(r"[\"'`\u201c\u2018]([^\"'`\u201c\u201d\u2018\u2019]{1,200})[\"'`\u201d\u2019]")

# A tool may put two option rows on one physical line; an option starts a new cell only
# after two spaces and a dash (never inside `--foo=BAR` or `[-x xlist]`).
CELL = re.compile(r"\s{2,}(?=-[A-Za-z0-9?])")

# One rule for every option-list layout a real tool uses (GNU, argparse, click, busybox).
OPTION_LINE = re.compile(
    r"^(?P<indent>\s*)"
    r"(?P<flags>(?:-(?P<short>[A-Za-z0-9?])(?![A-Za-z0-9]))(?:\s*,\s*--[A-Za-z][\w-]*)*"
    r"|--[A-Za-z][\w-]*(?:\s*,\s*--[A-Za-z][\w-]*)*)"
    # the separator is optional because a document may write `--fold[=NUM]`, `--width=NUM`,
    # `-d exdir` or `--output FILE` -- all four are the same fact about the same slot
    r"(?:\s*[= ]?\s*(?P<meta>[\[\]=-]*[A-Z][A-Z0-9_<>.|-]*\]?))?"
    r"(?P<rest>(?:\s{2,}|\t+).*)?$"
)
ALIAS = re.compile(r"--[A-Za-z][\w-]*|(?<![\w-])-[A-Za-z0-9](?![\w-])")
# In a usage line an option is followed by the word that names its argument, e.g. `[-d exdir]`.
USAGE_SLOT = re.compile(r"(?P<option>--[A-Za-z][\w-]*|-[A-Za-z0-9])[ =]?(?P<meta>[a-z][a-z0-9_-]*)")
# a usage statement starts a line, or follows the program naming itself in a sentence
# (`Zip 3.0 (July 5th 2008). Usage:`). `give a short usage message` is not one.
USAGE_LINE = re.compile(
    r"^\s*(?:usage|USAGE|Usage)\s*:?\s*(?P<rest>.+)$"
    r"|^.{0,60}?\.\s*(?:Usage|usage)\s*:?\s*(?P<after>.*)$")
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
    positional = [t for t in tokens
                  if t.startswith(("[", "<", "{")) or (t.isupper() and t not in
                                                       ("OPTION", "OPTIONS", "USAGE"))]
    return {"usage": rest[:400], "commands": commands, "positional": positional[:8]}


def parse_usage(text: str) -> dict[str, Any]:
    """The grammar a tool states about itself, including every alternative form it lists.

    A program that offers more than one arrangement of its arguments says so with `or:`.
    `cp` is the plain case: SOURCE DEST, SOURCE... DIRECTORY, and -t DIRECTORY SOURCE are three
    grammars, and using only the first one is how a copy ends up in the wrong place.
    """
    variants: list[dict[str, Any]] = []
    first = None
    for line in text.splitlines():
        for pattern in (USAGE_LINE, USAGE_NAME, OR_LINE):
            m = pattern.match(line)
            if not m:
                continue
            fields = m.groupdict()
            said = fields.get("rest") or fields.get("after") or ""
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
CELL = re.compile(r"\s{2,}(?=-[A-Za-z0-9?])")

# One rule for every option-list layout a real tool uses (GNU, argparse, click, busybox).
OPTION_LINE = re.compile(
    r"^(?P<indent>\s*)"
    r"(?P<flags>(?:-(?P<short>[A-Za-z0-9?])(?![A-Za-z0-9]))(?:\s*,\s*--[A-Za-z][\w-]*)*"
    r"|--[A-Za-z][\w-]*(?:\s*,\s*--[A-Za-z][\w-]*)*)"
    # the separator is optional because a document may write `--fold[=NUM]`, `--width=NUM`,
    # `-d exdir` or `--output FILE` -- all four are the same fact about the same slot
    r"(?:\s*[= ]?\s*(?P<meta>[\[\]=-]*[A-Z][A-Z0-9_<>.|-]*\]?))?"
    r"(?P<rest>(?:\s{2,}|\t+).*)?$"
)
ALIAS = re.compile(r"--[A-Za-z][\w-]*|(?<![\w-])-[A-Za-z0-9](?![\w-])")
# In a usage line an option is followed by the word that names its argument, e.g. `[-d exdir]`.
USAGE_SLOT = re.compile(r"(?P<option>--[A-Za-z][\w-]*|-[A-Za-z0-9])[ =]?(?P<meta>[a-z][a-z0-9_-]*)")
# a usage statement starts a line, or follows the program naming itself in a sentence
# (`Zip 3.0 (July 5th 2008). Usage:`). `give a short usage message` is not one.
USAGE_LINE = re.compile(
    r"^\s*(?:usage|USAGE|Usage)\s*:?\s*(?P<rest>.+)$"
    r"|^.{0,60}?\.\s*(?:Usage|usage)\s*:?\s*(?P<after>.*)$")
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
    return {"flag": flag, "aliases": aliases[:6], "meta": meta, "words": words[:400],
            "acts": acts_in(words)[:2], "takes_value": bool(meta), "heading": heading}


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
            demos.append({"call": " ".join(tokens),
                          "options": [t for t in tokens[1:] if t.startswith("-") and t != "-"],
                          "values": [t for t in tokens[1:] if not t.startswith("-")],
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
            if token.startswith("-") or re.match(r"^\[?OPTIONS?\b", token.upper()):
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
          acts: Iterable[tuple[str, str]] = ()) -> dict[str, Any]:
    """The document the request is about: by the words it spends, then by the act it states."""
    wanted = set(request_words)
    wanted_acts = [tuple(a) for a in acts]
    current = tree.get("root") or {}
    path: list[str] = []
    nodes = [current]
    scores: list[dict[str, Any]] = []
    while True:
        best, best_score = None, 0
        for child in current.get("children") or []:
            own = words_of(child.get("title", "") + " " + child.get("summary", ""))
            score = 2 * len(wanted & own)
            stated = acts_in(child.get("summary") or "")
            if wanted_acts and stated and stated[0][0] in {a[0] for a in wanted_acts}:
                score += 1
            scores.append({"child": child.get("title"), "score": score})
            if score > best_score:
                best, best_score = child, score
        if best is None:
            return {"document": current, "path": path, "nodes": nodes, "scores": scores,
                    "root": tree.get("root") or {}}
        path.append(best["title"])
        nodes.append(best)
        current = best


# --------------------------------------------------------------------------- require


def require(text: str) -> dict[str, Any]:
    """The instruction as (ACT, VALUES): what to do, in the class, and the objects it names."""
    instruction = str(text or "")
    values: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()

    def add(kind: str, value: str, context: str, position: int) -> None:
        key = (kind, value)
        if key in seen:
            return
        seen.add(key)
        values.append({"kind": kind, "value": value, "position": position,
                       "words": sorted(words_of(context))[:24], "context": context.strip()[:240]})

    for m in QUOTED.finditer(instruction):
        add("literal", m.group(1), instruction[max(0, m.start() - 140): m.end() + 140], m.start())
    unquoted = QUOTED.sub(lambda m: " " * len(m.group(0)), instruction)
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
                       "words": sorted(words_of(clause))[:24],
                       "context": clause[:240]})
        seen.add(("path", token))
    for m in re.finditer(r"\b(\d{1,6})\b", unquoted):
        if not re.match(r"\s+[A-Za-z]", unquoted[m.end(): m.end() + 50]):
            continue
        add("number", m.group(1),
            unquoted[max(0, m.start() - 90): m.end() + 90], m.start())
    # an ordinal is a word of the instruction, not a fragment of a path: `first` in
    # `/tmp/h/first.txt` is a file name, and counting it would add an object nobody named
    for m in re.finditer(r"(?<![\w./-])(" + "|".join(ORDINALS) + r")(?![\w./-])",
                         unquoted, re.I):
        if re.match(r"\s+\d+\s*[A-Za-z]", unquoted[m.end(): m.end() + 16]):
            continue  # "the first 2 lines": the count is 2, and `first` only selects the end
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

    reasons: list[str] = []
    if not acts:
        reasons.append("NO_ACT_IN_THE_CLOSED_CLASS")
    if not values:
        reasons.append("NO_EXPLICIT_OBJECT_IN_THE_INSTRUCTION")
    return {"schema": SCHEMA, "instruction": instruction, "acts": acts, "values": values,
            "reasons": reasons}


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
    named = [v for v in values if v["kind"] == "path"]
    ordered = sorted(named, key=lambda v: (0 if v.get("role") == "product" else
                                           2 if v.get("role") == "source" else 1,
                                           int(v["position"]))) if role_first \
        else sorted(named, key=lambda v: int(v["position"]))
    pairs: list[tuple[Mapping[str, Any], str]] = []
    for index, value in enumerate(ordered):
        means = picture[index] if picture and index < len(picture) else ""
        if means == "option":
            continue
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
            bound: Sequence[Mapping[str, Any]]) -> list[str]:
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
    ordered = sorted(values, key=lambda v: (0 if v.get("role") == "product" else
                                            2 if v.get("role") == "source" else 1,
                                            int(v["position"])))
    filled = [str(v["value"]) for v in ordered]
    if len(filled) > len(demo["values"]):
        return None
    argv = [tool] + list(prefix) + list(demo["options"]) + filled
    return {"argv": argv, "operation": None,
            "bound": [{"role": "demonstration", "call": demo["call"]}],
            "unbound": [], "complete": True, "document": " >> ".join(["root"] + list(prefix)),
            "reason": "PLANNED_FROM_A_DEMONSTRATION"}


def _product_slots(options: Sequence[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    return [o for o in options if is_product_slot(o)]


def _bind_product(values: Sequence[Mapping[str, Any]], options: Sequence[Mapping[str, Any]]
                  ) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[Mapping[str, Any]]]:
    """The reading that explains 'into Y': the destination takes the slot that means a place."""
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
    return out


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
            # a place in the program's own picture named for the product is where it goes:
            # `stitch OUTFILE [PATCH]...` says so, and a picture with no such place means the
            # shell carries the result instead. The place is named either by the request's own
            # words about it (`bundle.zip` and `zipfile` share `zip`) or by what it means.
            index = place_named_by(value)
            if index is None:
                index = next((i for i, place in enumerate(places)
                              if place and i not in taken
                              and re.match(r"^(out|output|outfile|dest|destination|target|"
                                           r"archive|result)$", place)), None)
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
    writes_into_a_named_place = any(
        item["role"] == "positional"
        and re.match(r"^(out|outfile|output|dest|destination|target|archive|result)$",
                     str(item.get("means") or ""))
        for item in bound)
    if not writes_into_a_named_place and \
            not any(item["role"] in ("redirect", "stdin_from") for item in bound):
        return []
    return [(bound, "PLANNED_BY_A_COMPOSED_READING")]


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


def plan(requirement: Mapping[str, Any], tree: Mapping[str, Any]) -> dict[str, Any]:
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
    if not acts:
        return {"schema": SCHEMA, "tool": tool, "plans": [], "complete": False,
                "reason": "NO_ACT_THE_REQUEST_NAMES", "path": [],
                "refusals": [{"reason": "NO_ACT_IN_THE_CLOSED_CLASS",
                              "instruction": requirement.get("instruction")}]}

    root = tree.get("root") or {}
    picture = positional_grammar((root.get("usage") or {}))
    routed = route(tree, words_of(requirement.get("instruction") or ""), acts) \
        if root.get("children") else {"path": [], "nodes": [root], "scores": []}
    nodes: list[dict[str, Any]] = routed["nodes"]
    plans: list[dict[str, Any]] = []
    refusals: list[dict[str, Any]] = []
    seen: set[tuple[tuple[str, ...], str, str]] = set()
    explained: dict[tuple[tuple[str, ...], str, str], int] = {}

    def prefix_of(depth: int) -> list[str]:
        return [nodes[i]["title"] for i in range(1, depth + 1)]

    def add(argv: list[str], *, operation: Any, bound: Any, depth: int,
            reason: str) -> None:
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
        plans.append(candidate)
        for item in unbound:
            refusals.append({"reason": "NO_SLOT_ACCEPTS_" + str(item["kind"]).upper(),
                             "value": item["value"], "context": item.get("context", "")[:160]})

    # R1 -- a worked example, deepest document first: it is the only whole act on offer
    for depth in range(len(nodes) - 1, -1, -1):
        for demo in nodes[depth].get("demos") or []:
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
                add(_render(tool, prefix_of(depth), operation, bound),
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
            bound, unbound = _bind(values, [], product_first=False, picture=picture)
            add(_render(tool, prefix_of(depth), None, bound), operation=None, bound=bound,
                depth=depth, reason="PLANNED_BY_THE_SUBCOMMAND")
            break

    # R5 -- the program's own order, both readings the evidence supports
    spare = [v for v in values if v["kind"] != "path" and v["kind"] != "number"]
    for reading in _positional_readings(values, picture, root.get("usage") or {}):
        bound = list(reading)
        for extra in spare:
            holder = next((o for o in _product_slots(root.get("options") or [])
                           if slot_kind(o) == "number"), None)
            if holder is not None:
                bound.append({"role": "value_slot", "option": holder["flag"],
                              "value": str(extra["value"])})
            else:
                bound.append({"role": "unbound", "kind": extra["kind"],
                              "value": extra["value"], "context": extra.get("context", "")})
        add(_render(tool, [], None, bound), operation=None, bound=bound, depth=0,
            reason="PLANNED_BY_ARGUMENT_ORDER")

    good = [p for p in plans if p["complete"]]
    return {
        "schema": SCHEMA, "tool": tool, "path": routed["path"],
        "route_scores": routed.get("scores") or [],
        "document_usage": (nodes[-1].get("usage") or {}).get("usage"),
        "plans": plans, "complete": bool(good), "refusals": refusals,
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


def require_survey_plan(tool: str, instruction: str, **survey_kwargs: Any) -> dict[str, Any]:
    """The one call: require the instruction, survey the tool, route, plan."""
    req = require(instruction)
    survey_kwargs.setdefault("want", sorted(words_of(instruction)))
    tree = survey(tool, **survey_kwargs)
    result = plan(req, tree)
    result["instruction"] = instruction
    result["acts"] = req["acts"]
    result["values"] = req["values"]
    result["requirement_reasons"] = req["reasons"]
    result["survey"] = {k: tree[k] for k in ("documents_ok", "document_bytes", "seconds",
                                             "stored_bytes")}
    result["documents_asked"] = tree["documents_asked"]
    return result


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
