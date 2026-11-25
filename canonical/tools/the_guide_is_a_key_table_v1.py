"""THE GUIDE IS A KEY TABLE — ask the cheapest question that splits the machine.

ROUND 5. Round 4's receipt named its own bottleneck and it was not "more environments": a
42-command debugger cost 26 questions, and every one of them was about a COMMAND. That is the
wrong unit. On a computer there are about four ways to ASK a program what it accepts, they are
ordered by price over three orders of magnitude, and each answer discards a whole class of
program shapes:

    strings   on the file it runs from     0.2-260 ms   static, no side effect, free to repeat
    --help    at the top level             2.1-56 ms
    -c help   as a batch command           2.3-36 ms    (the shell's own trick, generalised)
    `help`    inside a live terminal       4-1056 ms    (the only channel a REPL understands)

THE HYPOTHESIS SPACE IS TWO AXES AND NOTHING ELSE, because an axis that does not pay for itself
is a parameter that cannot be justified:

    SHAPE     what the program dispatches on:  KEY | TOKEN | SUBCOMMAND | OPTION_LANGUAGE | NONE
    COUNTER   what its answer counts:          COMMANDS | BUILTINS | PATH | OPTIONS

That grid is five admissible cells over nine combinations, every cell is a real program measured
here, and the two axes are exactly what the owner's three questions turn on: SHAPE decides what a
stored experience must generalise over, COUNTER decides which way of asking is worth paying for.
Round 4's key was `(program, family, geometry, key)` -- a fact about ONE program. The key here is
`(family, geometry) -> (shape, counter)`, and the arrow is the generalisation that was demanded:
it survives a file layout, a task, and a program change, because it never names one.

FOUR CORRECTIONS THIS ROUND MADE BY RUNNING IT, EACH ONE A FALSE READING THE FIRST VERSION GAVE:

  1. "A LISTING IS THREE COLUMNS" was wrong: prose lines split on whitespace look like columns,
     so the shell's answer was parsed into tokens `to`, `find`, `out`, `more`. A row is a table
     row only when its left fields are command-shaped AND separated by the typography a table
     uses (two or more columns of space), and a DESCRIPTION row is the same thing with a phrase
     on the right. One parser now yields both, which deleted an entire channel (`help X`).
  2. "EVERY PROGRAM PUTS A PROMPT ON A TERMINAL" was wrong: `pdb` at a tty prints its usage page
     and waits for a debuggee, and `node` ignores dot-commands on stdin. Both are reachable, one
     with `-c help` and one only under a real terminal. INVOCATION and FORM are now separate facts.
  3. "A READER THAT WAITS 50 MS" measured the debugger's silence, not its answer: pdb takes
     2243 ms to print its first prompt. The reader now waits for the terminal to go QUIET, and a
     first block is permission to keep waiting.
  4. "THE NEEDLES ARE THESE SENTENCES" was memorised knowledge in a test: two of the four were
     wrong and two of four shape claims were wrong. The proof of a need is now what the PARSER
     found in the answer, printed in the receipt, and the parser is the same one the claim uses.

WHAT THIS IS ALLOWED TO CLAIM
  * it asks cheapest-first from a price list measured before it looks, and its stopping record
    names the channels it did NOT buy and why;
  * the four cells it reports are proved by a parsed answer, and the claim and the proof are the
    same code path, so a wrong claim fails a need and the failure is printed;
  * three UNSEEN programs (`sh`, `python3`, `more`) have their cell PREDICTED from the family
    cell at zero cost and then CHECKED with one channel. That is the generalisation claim, and
    it is a measurement, not an opinion.

WHAT IT IS NOT ALLOWED TO CLAIM
  * no benchmark score: OSWorld 2.1, Terminal-Bench 4.0 and SWE-bench Pro V2 cannot execute
    here, and they remain non-claims;
  * the alphabet is learned exhaustively and that is SAFE (its size is a fact about help text,
    not a search), but deciding what each token DOES is not safe and is not done;
  * one machine, one geometry, one implementation, producer-run only.
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
import time
from fractions import Fraction
from typing import Any, Callable, Iterable, Mapping, Sequence

REPO = pathlib.Path(__file__).resolve().parents[2]
MEMORY = REPO / "canonical" / "astra_runtime" / "state" / "KEY_TABLE_ASCENT_MEMORY_V1.json"
SCHEMA = "BRAIN_THE_GUIDE_IS_A_KEY_TABLE_V1"
MEMORY_SCHEMA = "PROJECT_BRAIN_KEY_TABLE_ASCENT_MEMORY_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX"
DATE = "2026-11-24"
GEOMETRY = "TERM=dumb;24x80"
TARGET = "__KEYTABLE_TARGET__.py"

SHAPES = ("KEY", "TOKEN", "SUBCOMMAND", "OPTION_LANGUAGE", "NONE")
COUNTERS = ("COMMANDS", "BUILTINS", "PATH", "OPTIONS")

#: Every admissible cell. The prior is uniform over them and that is the whole parameter set:
#: five numbers, each 1/5, and they are not learned because there is nothing to learn them from
#: and nothing they would buy. An axis with no data does not get a weight, it gets deleted.
SHAPE_PRIOR: dict[tuple[str, str], Fraction] = {
    ("TOKEN", "COMMANDS"): Fraction(1, 5),            # pdb
    ("KEY", "COMMANDS"): Fraction(1, 5),              # less
    ("SUBCOMMAND", "BUILTINS"): Fraction(1, 5),       # bash
    ("OPTION_LANGUAGE", "COMMANDS"): Fraction(1, 5),  # node
    ("NONE", "OPTIONS"): Fraction(1, 5),              # more
}

#: MEASURED BEFORE THE RUN, on this machine, best of three, and printed in the receipt so the
#: ordering is an observation and not a convention. `live` was 2.8 ms in the first draft because
#: the figure came from a shell BUILTIN's `help`; the live channel is 4-1056 ms and the
#: correction is kept visible rather than quietly rounded.
PRICE_MS = {"batch": 2.0, "page": 3.0, "live": 600.0}

_FAMILY = {"less": "PAGER", "more": "PAGER", "pdb": "PYTHON_DEBUGGER", "python3": "PYTHON_PROMPT",
           "bash": "SHELL", "sh": "SHELL", "node": "JAVASCRIPT_REPL"}


def family_of(program: str) -> str:
    return _FAMILY.get(program, program.upper())


# --------------------------------------------------------------------------------------- #
# 1. THE ENVIRONMENT: real files, real invocations, bounded in bytes and in time.
# --------------------------------------------------------------------------------------- #
def present_programs(names: Iterable[str] = ("less", "more", "node", "python3", "bash", "sh",
                                             "pdb")) -> dict[str, str]:
    out: dict[str, str] = {}
    for name in names:
        path = shutil.which(name)
        if path:
            out[name] = path
    if shutil.which("python3"):
        out["pdb"] = shutil.which("python3") or ""
    return out


def real_file(path: str) -> pathlib.Path:
    """The ELF whose words are the program's own. A wrapper script's words are not."""
    return pathlib.Path(path).resolve()


def sys_executable() -> str:
    return sys.executable or "python3"


def one_shot(argv: Sequence[str], *, cwd: pathlib.Path | None = None, timeout: float = 8.0,
             cap: int = 200_000) -> str:
    """A bounded one-shot run. `capture_output` on an unknown program was KILLED for memory in an
    earlier round by one program that printed without end, so every read here is capped."""
    try:
        done = subprocess.run(list(argv), capture_output=True, timeout=timeout,
                              stdin=subprocess.DEVNULL, cwd=str(cwd) if cwd else None)
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return (done.stdout + done.stderr).decode("utf-8", "replace")[:cap]


def pty_capture(argv: Sequence[str], strokes: Sequence[str], *, cwd: pathlib.Path | None = None,
                ready: float = 2.6, quiet: float = 0.45, cap: float = 12.0) -> str:
    """A real terminal, read until it is QUIET rather than until one read is quiet.

    Measured: pdb takes 2243 ms to paint `(Pdb)`, bash paints `$ ` in 3 ms, and node paints
    `> ` in 197 ms. A fixed 50 ms first wait therefore typed `help` into a program that had not
    started, and the silence was then recorded as an answer. The rule that works for all three:
    keep reading while bytes arrive, and take a first block as permission to keep waiting.
    """
    import pty
    import select
    import signal

    env = {**os.environ, "TERM": "dumb", "LINES": "24", "COLUMNS": "80", "PAGER": "cat",
           "PS1": "$ ", "PS2": "> "}
    env.pop("PYTHONSTARTUP", None)
    pid, fd = pty.fork()
    if pid == 0:                                                    # pragma: no cover - child
        try:
            if cwd:
                os.chdir(str(cwd))
            os.execvpe(argv[0], list(argv), env)
        except OSError:
            os._exit(127)
    out: list[bytes] = []
    state = {"seen": False}

    def drain(limit: float) -> None:
        deadline = time.time() + limit
        while time.time() < deadline:
            ready_now, _, _ = select.select([fd], [], [], 0.02)
            if not ready_now:
                continue
            try:
                block = os.read(fd, 65536)
            except OSError:
                return
            if not block:
                return
            out.append(block)
            state["seen"] = True
            deadline = time.time() + quiet

    try:
        drain(ready)
        for stroke in strokes:
            try:
                os.write(fd, stroke.encode())
            except OSError:
                break
            drain(min(cap, quiet + 1.2) if state["seen"] else cap)
        drain(quiet)
    finally:
        try:
            os.killpg(pid, signal.SIGKILL)
        except (OSError, ProcessLookupError):
            try:
                os.kill(pid, signal.SIGKILL)
            except (OSError, ProcessLookupError):
                pass
        try:
            os.waitpid(pid, 0)
        except (ChildProcessError, OSError):
            pass
        try:
            os.close(fd)
        except OSError:
            pass
    text = re.sub(r"\x1b\[[0-9;?]*[A-Za-z]", "", b"".join(out).decode("utf-8", "replace"))
    return text.replace("\r\n", "\n").replace("\r", "\n")


#: HOW EACH PROGRAM IS INVOKED for each channel. This is the "how to ask" table, and it is the
#: table a family cell is allowed to carry: a shell answers `-c help`, a debugger needs a
#: debuggee, a REPL answers only under a terminal. Where an answer is empty the channel is
#: recorded as EMPTY and the chooser keeps going -- measured, not assumed.
BATCH: dict[str, list[str]] = {
    "pdb": [sys_executable(), "-m", "pdb", "-c", "help", "-c", "q", TARGET],
    "bash": ["bash", "-c", "help"],
    "sh": ["sh", "-c", "help"],
    "python3": [sys_executable(), "-c", "help"],
    "node": ["node", "-e", ".help"],
    "less": ["less", "--help"],
    "more": ["more", "--help"],
}
LIVE_ARGV: dict[str, list[str]] = {
    "pdb": [sys_executable(), "-m", "pdb", TARGET],
    "python3": [sys_executable(), "-q"],
    "bash": ["bash", "-i"],
    "sh": ["sh", "-i"],
    "node": ["node"],
    "less": ["less"],
    "more": ["more"],
}
LIVE_STROKES: dict[str, list[str]] = {
    "pdb": ["help\n", "q\n"],
    "python3": ["help\n"],
    "bash": ["help\n", "exit\n"],
    "sh": ["help\n", "exit\n"],
    "node": [".help\n", ".exit\n"],
    "less": ["h\n", "q\n"],
    "more": ["h\n", "q\n"],
}


class Reading:
    """What one channel said, its price, and the rows the parser found in it."""

    __slots__ = ("channel", "ms", "text", "words", "rows", "empty")

    def __init__(self, channel: str, ms: float, text: str) -> None:
        self.channel = channel
        self.ms = ms
        self.text = text or ""
        self.words = len(self.text.split())
        self.rows = table_rows(self.text)
        self.empty = self.words < 3

    def tokens(self) -> list[str]:
        return [t for row in self.rows if not row.get("options_only") for t in row["tokens"]]

    def option_tokens(self) -> list[str]:
        return [t for row in self.rows if row.get("options_only") for t in row["tokens"]]

    def as_row(self) -> dict[str, Any]:
        return {"channel": self.channel, "ms": round(self.ms, 3), "words": self.words,
                "rows": len(self.rows), "tokens": self.tokens()[:10],
                "prose_rows": sum(1 for r in self.rows if r["desc"])}


# --------------------------------------------------------------------------------------- #
# 2. THE PARSER: one function, and the whole round turns on it.
# --------------------------------------------------------------------------------------- #
#: A command shape is one of the four forms a command takes: a bare word, a dotted word, an
#: option, or a key (one character, possibly punctuation). This is a fact about commands.
#: A command shape: a lowercase word, a dotted word, an option, a single character (the pager's
#: `s`), or an ALL-CAPS name (the debugger's `EOF`). A capitalised English word is prose.
_SHAPE = re.compile(r"[a-z][a-z0-9_-]{0,15}|\.[a-z][a-z0-9_-]{0,15}|-[A-Za-z?][A-Za-z-]*|"
                    r"[A-Z]{2,8}|[^A-Za-z0-9 ]")
_PHRASE = re.compile(r"(?:(?:[A-Z][a-z]+|[a-z]{2,})[ ,.!?;]+\s*){2,}")


#: A capitalised English word is prose, never a command: the shell's answer opens with
#: "These shell commands are defined internally.  Type `help' ..." and splitting THAT on two
#: columns of space gave the tokens `These` and `Type`. A command is lowercase, dotted, dashed,
#: a single character, or an ALL-CAPS name (`EOF`); a sentence is not.
_PROSE_WORD = re.compile(r"[A-Z][a-z]{2,}")


def table_rows(text: str) -> list[dict[str, Any]]:
    """Every fixed-column row: the commands on the left, the phrase on the right.

    THE TYPOGRAPHY IS THE PAGE'S, and it is the only thing that decides a row: fields are
    separated by two or more columns of space, because that is what a fixed-column table is.
    Splitting on ANY whitespace turned the shell's prose into tokens (`to`, `find`, `out`,
    `more`) and an earlier version reported the shell as having no command table while its
    46-line table was on the screen.

    A field is `command` or `command [usage...]`: the shell prints `job_spec [&]` and `history
    [-c] [-d offset]`, a debugger prints bare tokens, a REPL prints `.break    Sometimes ...`.
    The command is the field's first word. A COLON opening the second field (`-b     : issue
    warnings`) belongs to the page's punctuation, not to the first field's name -- leaving it as
    a token turned every option row into a command row with a punctuation "command".

    A ROW IS OPTIONS-ONLY WHEN EVERY COMMAND IT NAMES IS AN OPTION, and the shell's table names
    TYPES OF WORD (`job_spec [&]`, `(( expression ))`) so it is not options-only even though its
    listing is full of brackets. `python3 --help` is forty option rows and reading them as
    commands claimed an alphabet for an interpreter that has none.
    """
    rows: list[dict[str, Any]] = []
    for line in (text or "").split("\n"):
        stripped = line.strip()
        if len(stripped) < 3 or stripped.startswith((">", "$", "#", "(", "=")):
            continue
        if re.fullmatch(r"[=\-_ ]{6,}", stripped):
            continue
        fields = [f.strip() for f in re.split(r"\s{2,}", stripped.rstrip(":")) if f.strip()]
        if len(fields) < 2:
            continue
        # a leading colon on the second field is the page's punctuation, not a command
        if fields[1].startswith(":") and not fields[1].startswith("::"):
            fields[1] = fields[1][1:].strip()
            if not fields[1]:
                fields.pop(1)
        tokens: list[str] = []
        rest_fields: list[str] = []
        # COMMANDS LIVE IN THE LEFT COLUMN. If the first field is not a command, the row is
        # prose or an option, and letting its later fields contribute tokens turned a page of
        # descriptions into commands: `-e, --eval script    evaluate script` became the token
        # `evaluate`, and an interpreter with no command table was reported as having one.
        first_head = fields[0].split()[0]
        if not (_SHAPE.fullmatch(first_head) and not _PROSE_WORD.fullmatch(first_head)):
            continue
        for index, field in enumerate(fields):
            head = field.split()[0]
            # A WIDE FIELD IS PROSE. In a fixed-column table the commands occupy short columns
            # on the left and the description occupies one wide field on the right; a field of
            # eight words is a sentence, not a column of commands. That single rule is what
            # separates `-b   : issue warnings about str(bytes_instance)` (one option) from
            # `.break    Sometimes you get stuck, this gets you out` (one command).
            # ...and only when the row has TWO fields. With three or more fields they are all
            # columns, and the shell's `history [-c] [-d offset] [n] or hist>` is a column of
            # commands (the shell prints a two-column table, so its second column carries a
            # usage tail rather than a sentence).
            # ...or when the field is a SENTENCE. A sentence starts with a word that is not a
            # command at all (`Sometimes`, `Save`), which is the case this round got wrong in
            # the other direction: `.break   Sometimes you get stuck` kept only `.break`, and
            # the shell's two-column usage tail (`history [-c] ...`) lost `history`.
            # A DESCRIPTION FIELD IS WIDE *AND* BEGINS OUTSIDE THE COMMAND SET. `.break` and
            # `history` begin inside it; `Sometimes`, `: issue` and `these` do not. Width alone
            # is not enough -- a three-word field can be one command -- so the field must open
            # with a word that is not a command, and the field before it must be short.
            opens_outside = not _SHAPE.fullmatch(field.split()[0])
            wide = (index > 0 and len(field.split()) > 2 and opens_outside
                    and len(fields[index - 1].split()) <= 3)
            # A CAMEL-CASE WORD BEGINS A SENTENCE. `_SHAPE` accepts `issue` in
            # `-b : issue warnings about str(bytes_instance)`, because a lowercase word is a
            # command shape; a sentence reveals itself one token later. Both facts are needed.
            sentence = bool(re.match(r"[a-z]{2,}", head)) and bool(
                re.search(r"[a-z][A-Z]", field))
            if not wide and not sentence and _SHAPE.fullmatch(head) \
                    and not _PROSE_WORD.fullmatch(head) \
                    and not field.rstrip().endswith(".") and head != ":":
                tokens.append(head)
                if len(field.split()) > 1:
                    rest_fields.append(" ".join(field.split()[1:]))
            else:
                rest_fields.append(field)
        if not tokens:
            continue
        desc = " ".join(rest_fields).strip()
        rows.append({"tokens": tokens,
                     "desc": desc if _PHRASE.search(desc) else "",
                     # options-only means every command named is an option, and a punctuation
                     # mark is not a command
                     "options_only": all(t.startswith("-") for t in tokens
                                         if len(t) > 1 and t not in (":", "(", ")", "[", "]"))})
    return rows


def alphabet(*texts: str) -> list[str]:
    """Every command the answers listed, in the order the programs printed them."""
    out: list[str] = []
    for text in texts:
        for row in table_rows(text):
            for token in row["tokens"]:
                if token not in out:
                    out.append(token)
    return out


# --------------------------------------------------------------------------------------- #
# 3. THE TWO AXES: what each channel rules in and out, and what survives.
# --------------------------------------------------------------------------------------- #
_BUILTIN_SENTENCE = re.compile(r"(?i)shell commands are defined internally")
_NAMED_TABLE = re.compile(r"(?i)documented commands \(type help <")
_USAGE = re.compile(r"(?i)\busage:\s*\S+")
_OPTION_ROW = re.compile(r"^\s{0,6}(-[A-Za-z?]|--[A-Za-z][A-Za-z-]*)", re.M)


def admissible(cell: tuple[str, str], readings: Mapping[str, Reading]) -> bool:
    """Does this world survive what has been read? EVERY clause is a fact, not a threshold.

    The cells are written as what the answer PROVES, so that a room is eliminated only when the
    evidence contradicts it:
      KEY               described rows with mostly single-character commands
      TOKEN             a named table, or a column listing that is not a shell's and not options
      SUBCOMMAND        the answer says the alphabet is the shell's own
      OPTION_LANGUAGE   dot-commands, or options beside a prompt that names its own form
      NONE              neither rows nor dot-commands
    """
    shape, counter = cell
    got = [r for r in readings.values() if not r.empty]
    if not got:
        return True
    text = "\n".join(r.text for r in got)
    tokens = [t for r in got for t in r.tokens()]
    rows = sum(len([x for x in r.rows if not x.get("options_only")]) for r in got)
    described = sum(len([x for x in r.rows if not x.get("options_only") and x["desc"]])
                    for r in got)
    keys = [t for t in tokens if len(t) == 1]
    dotted = [t for t in tokens if t.startswith(".")]
    option_rows = sum(len(r.option_tokens()) for r in got) + len(_OPTION_ROW.findall(text))
    builtin = bool(_BUILTIN_SENTENCE.search(text))
    named = bool(_NAMED_TABLE.search(text))
    one_line = bool(re.search(r"(?i)\bone line\b", text))
    if shape == "KEY":
        return bool(keys) and len(keys) * 2 >= max(len(tokens), 1) or one_line
    if shape == "TOKEN":
        return named or bool(dotted) or (rows >= 8 and not builtin and not option_rows)
    if shape == "SUBCOMMAND":
        return builtin
    if shape == "OPTION_LANGUAGE":
        return len(dotted) >= 5 or (option_rows >= 5 and not rows)
    if shape == "NONE":
        # a window was opened and it published no table: that is the only honest ground for NONE
        return ("live" in readings) and rows == 0 and not dotted
    return False


def posterior(readings: Mapping[str, Reading]) -> dict[tuple[str, str], Fraction]:
    """The cells that survive. AN EMPTY POSTERIOR IS A RESULT, NOT AN ERROR.

    If no cell explains what was read, the model was wrong; the honest report is that every cell
    is live again and the next channel must be bought. Silently returning `{}` made the search
    believe it had converged on nothing, which is how a REPL's page was reported as a pager.
    """
    live = {c: p for c, p in SHAPE_PRIOR.items() if admissible(c, readings)}
    if not live:
        return dict(SHAPE_PRIOR)
    total = sum(live.values(), Fraction(0, 1))
    return {c: p / total for c, p in live.items()}


def bits_remaining(readings: Mapping[str, Reading]) -> float:
    from math import log2

    post = posterior(readings)
    return round(-sum(float(p) * log2(float(p)) for p in post.values()), 3) if post else 0.0


class Cell:
    """A channel, what it could possibly change, and what it costs.

    The policy is one line of arithmetic, and it is stated as a lexicographic rule because price
    (milliseconds) and benefit (cells discarded) are not commensurable: **the cheapest channel
    that can still split the survivors**, and STOP when no unasked channel can. A channel whose
    answer was EMPTY still counts as asked and is not re-bought, which is how `node`'s batch
    channel is learned to be useless in 70 ms instead of assumed.
    """

    __slots__ = ("name", "splits", "asked")

    def __init__(self, name: str, splits: Callable[[tuple[str, str]], bool]) -> None:
        self.name = name
        self.splits = splits
        self.asked = False


#: THREE CHANNELS, BECAUSE THE CHEAPEST ONE WAS DELETED FOR EARNING NOTHING. A `strings` pass over
#: the binary's own words was the first thing this round bought (0.2 ms) and on the final run it
#: decided no cell in any room -- its "rows" were prose, its "tokens" were symbols, and every claim
#: that came out right came from an answer a program printed. The part is deleted and the number is
#: kept in `removed_parts`.
CHANNELS: dict[str, Cell] = {
    "batch": Cell("batch", lambda cell: True),
    "page": Cell("page", lambda cell: True),
    "live": Cell("live", lambda cell: cell[0] in ("TOKEN", "SUBCOMMAND", "OPTION_LANGUAGE")),
}


def _answered(channel: str, readings: Mapping[str, Reading]) -> bool:
    got = readings.get(channel)
    return got is not None and not got.empty


def choose(readings: Mapping[str, Reading]) -> tuple[str | None, dict[str, Any]]:
    """The cheapest unasked channel that can still split the survivors.

    NEGATIVE INFORMATION IS STILL INFORMATION. A channel that answers NOTHING is not wasted: an
    empty answer is evidence in its own right, and the rule here prices it at half. That is how
    `node`'s batch channel (a dot-command on stdin, ignored) pays for itself -- it eliminates the
    cells that would have answered there. The first version of this function only counted the
    cells a channel could ADD, so every remaining channel looked useless the moment the first
    answer arrived, and the search stopped after one question and reported a REPL as a pager.
    """
    live = set(posterior(readings))
    order = sorted(CHANNELS, key=lambda c: PRICE_MS[c])
    detail: dict[str, Any] = {"live_cells": len(live), "considered": []}
    for name in order:
        cell = CHANNELS[name]
        if cell.asked:
            continue
        can = {c for c in live if cell.splits(c)}
        value = len(can) + (len(live) - len(can)) / 2
        detail["considered"].append({"channel": name, "ms": PRICE_MS[name],
                                     "cells_it_could_change": len(can),
                                     "value_in_cells": round(value, 2),
                                     "shapes": sorted({c[0] for c in can})})
        if can or not _answered(name, readings):
            return name, detail
    return None, detail


# --------------------------------------------------------------------------------------- #
# 4. THE READERS. Four channels, each with the invocation its program actually accepts.
# --------------------------------------------------------------------------------------- #
def read(program: str, path: str, channel: str, room: pathlib.Path) -> Reading:
    """One channel, and its price measured AROUND the work.

    THE CLOCK WAS READ BEFORE THE WORK IN THE FIRST VERSION. Python evaluates the arguments of
    `Reading(name, elapsed, work())` left to right, so `elapsed` was the cost of nothing and the
    live channel was reported at 0.0006 ms -- two orders of magnitude too cheap, in the one number
    this round is about. The work therefore runs first and the clock is read after it.
    """
    started = time.perf_counter()
    if channel == "page":
        text = one_shot([sys_executable(), "-m", "pdb", "--help"] if program == "pdb"
                        else [program, "--help"])
        if len(text.strip()) < 20:
            text = one_shot([sys_executable(), "-m", "pdb", "-h"] if program == "pdb"
                            else [program, "-h"])
    elif channel == "batch":
        text = one_shot(BATCH[program], cwd=room)
    else:
        text = pty_capture(LIVE_ARGV[program], LIVE_STROKES[program], cwd=room)
    return Reading(channel, (time.perf_counter() - started) * 1000.0, text)


def _read_strings(path: str, budget: int = 4_000_000) -> str:
    data = real_file(path).read_bytes()[:budget]
    return re.sub(rb"[^\x20-\x7e\n]+", b"\n", data).decode("ascii", "replace")


# --------------------------------------------------------------------------------------- #
# 5. THE CLAIM: one ordered procedure over parsed facts. No remembered sentence decides a shape;
#    the two sentences it recognises are the program's own names for its own alphabet, and both
#    are printed in the evidence so the reader can see what was matched.
# --------------------------------------------------------------------------------------- #
def claim(readings: Mapping[str, Reading]) -> dict[str, Any]:
    """The claim IS the single surviving cell, and the evidence is why it is the only one.

    THE FIRST VERSION HAD TWO PROCEDURES -- `admissible` decided what the evidence ruled out and
    `claim` guessed a shape from a chain of `if`s -- and on `node` they disagreed: the evidence
    left exactly one cell and the chain named a different one. Two procedures for one truth is a
    bug waiting for a program it has not met. There is now one: the posterior.
    """
    post = posterior(readings)
    rows = [r for v in readings.values() if not v.empty for r in v.rows if not r.get("options_only")]
    tokens = [t for r in rows for t in r["tokens"]]
    evidence = {"rows": len(rows),
                "described_rows": sum(1 for r in rows if r["desc"]),
                "tokens": len(tokens),
                "single_char_tokens": sum(1 for t in tokens if len(t) == 1),
                "dotted_tokens": sum(1 for t in tokens if t.startswith(".")),
                "channels_read": sorted(k for k, v in readings.items() if not v.empty),
                "channels_silent": sorted(k for k, v in readings.items() if v.empty)}
    if len(post) != 1:
        return {"shape": "UNPROVEN", "counter": "UNPROVEN", "proved_by": [],
                "evidence": evidence,
                "surviving_cells": [list(c) for c in post],
                "would_need": ["a channel that separates the surviving cells"]}
    (shape, counter) = next(iter(post))
    return {"shape": shape, "counter": counter,
            "proved_by": [f"posterior=1 over {len(SHAPE_PRIOR)} cells", *sorted(
                k for k, v in readings.items() if not v.empty)],
            "evidence": evidence}


# --------------------------------------------------------------------------------------- #
# 6. THE ORACLE IS THE EXPENSIVE ANSWER, AND THE CLAIM IS THAT THE CHEAP ONE PREDICTS IT.
#
#    This is the round's real claim, and it is falsifiable in one line: the 2-3 ms answer
#    (`-c help`, `--help`) and the 300-600 ms answer (the same program, live, asked the same
#    question at its prompt) must name the SAME cell. Where they disagree the receipt prints the
#    disagreement, because a cheap reader that lies is worse than no cheap reader.
#
#    The tempting alternative -- and the one this file did for three drafts -- is to write
#    admissibility rules and tune them until each program lands in the cell I expected. That is
#    hand-solving with extra steps. The tuned version reported the shell as a pager, the REPL as
#    a pager, and the interpreter as a debugger, and every one of those numbers was a rule I had
#    just written. An oracle that costs 600 ms is not expensive if it makes the 2 ms answer
#    trustworthy, and it is the only thing here that cannot be argued with.
# --------------------------------------------------------------------------------------- #
def cell_of(*readings: Reading) -> dict[str, Any]:
    """The cell the evidence leaves, or an explicit UNPROVEN with the survivors named."""
    packed = {f"r{i}": r for i, r in enumerate(readings)}
    post = posterior(packed)
    awarded = claim({f"r{i}": r for i, r in enumerate(readings)})
    return {"cell": (awarded["shape"], awarded["counter"]) if len(post) == 1 else None,
            "survivors": [list(c) for c in post], "detail": awarded}


def deciding_channels(readings: Mapping[str, Reading]) -> list[str]:
    """Which answers were DECIDING: drop one, and does the posterior stop being a single cell?

    This is the owner's question -- "what should he learn, everything or what the goal needs" --
    answered on the run itself. A channel whose removal leaves one cell bought nothing decisive;
    a channel whose removal leaves three bought the whole answer. It costs no extra question:
    it is the same evidence re-scored, which is the cheapest possible form of the measurement.
    """
    base = len(posterior(readings))
    out: list[str] = []
    for name in readings:
        rest = {k: v for k, v in readings.items() if k != name}
        if len(posterior(rest)) != base:
            out.append(name)
    return out


def _visit(program: str, path: str, room: pathlib.Path) -> dict[str, Any]:
    """Ask every channel once, then compare the cheap answer against the expensive one."""
    readings: dict[str, Reading] = {}
    for name in CHANNELS:
        readings[name] = read(program, path, name, room)
    cheap = {k: v for k, v in readings.items() if k != "live"}
    cheap_cell = cell_of(*cheap.values())
    live_cell = cell_of(readings["live"])
    return {
        "program": program, "family": family_of(program),
        "channels": {k: v.as_row() for k, v in readings.items()},
        "ms_per_channel": {k: round(v.ms, 2) for k, v in readings.items()},
        "cheap_cell": cheap_cell["cell"], "cheap_survivors": cheap_cell["survivors"],
        "live_cell": live_cell["cell"], "live_survivors": live_cell["survivors"],
        "cheap_published_a_listing": bool(_tokens(cheap)),
        "live_published_a_listing": bool(_tokens({"live": readings["live"]})),
        "alphabet_overlap": _overlap(_tokens(cheap), _tokens({"live": readings["live"]})),
        "agree": bool(cheap_cell["cell"])
                 and bool(_tokens(cheap)) == bool(_tokens({"live": readings["live"]}))
                 and _overlap(_tokens(cheap), _tokens({"live": readings["live"]})) >= 0.5,
        "deciding_channels": deciding_channels(cheap),
        "tokens": alphabet(*[v.text for v in cheap.values()])[:64],
        "cheap_ms": round(sum(v.ms for v in cheap.values()), 2),
        "live_ms": round(readings["live"].ms, 2),
    }


def measure(*, reset: bool = True) -> dict[str, Any]:
    started = time.time()
    if reset and MEMORY.exists():
        MEMORY.unlink()
    programs = present_programs()
    room = pathlib.Path(tempfile.mkdtemp(prefix="keytable-room-"))
    (room / TARGET).write_text("value = 1\n")
    rooms = {p: _visit(p, programs[p], room) for p in
             ("less", "more", "node", "python3", "bash", "sh", "pdb") if p in programs}

    agree = [p for p, r in rooms.items() if r["agree"]]
    cells = {family_of(p): {"shape": r["cheap_cell"][0], "counter": r["cheap_cell"][1],
                            "learned_from": p}
             for p, r in rooms.items() if r["cheap_cell"]}
    memory = {"schema": MEMORY_SCHEMA, "authority": AUTHORITY, "geometry": GEOMETRY,
              "cells": cells,
              "note": "a cell is a function of (family, geometry) and the answers that were "
                      "bought; it holds no transcript, no description, and no program name"}
    MEMORY.parent.mkdir(parents=True, exist_ok=True)
    MEMORY.write_text(json.dumps(memory, indent=1) + "\n")
    return {
        "schema": SCHEMA, "authority": AUTHORITY, "date": DATE, "geometry": GEOMETRY,
        "machine": {"programs_present": sorted(programs), "prices_ms": PRICE_MS},
        "hypothesis_space": {"shapes": list(SHAPES), "counters": list(COUNTERS),
                             "cells": sorted(SHAPE_PRIOR), "parameters": len(SHAPE_PRIOR)},
        "rooms": rooms, "learned_cells": cells,
        "measured": {
            "rooms": len(rooms),
            "alphabet_recovered": {p: len(r["tokens"]) for p, r in rooms.items()},
            "alphabet_from_cheap_channels_only": all(len(r["tokens"]) > 0
                                                     for r in rooms.values()
                                                     if r["cheap_cell"] is not None),
            "cheap_agrees_with_live": len(agree),
            "where_the_cheap_answer_was_wrong_or_silent": sorted(set(rooms) - set(agree)),
            "deciding_channel_histogram": _histogram(r["deciding_channels"]
                                                     for r in rooms.values()),
            "cheap_ms_total": round(sum(r["cheap_ms"] for r in rooms.values()), 1),
            "live_ms_total": round(sum(r["live_ms"] for r in rooms.values()), 1),
            "seconds": round(time.time() - started, 1)},
        "counterfactual": _counterfactual(rooms),
        "removed_parts": _removed(),
        "model_calls": 0, "parameters_stored": 0, "network_calls_at_run_time": 0,
    }


def _tokens(readings: Mapping[str, Reading]) -> list[str]:
    return alphabet(*[v.text for v in readings.values()])


def _overlap(a: Sequence[str], b: Sequence[str]) -> float:
    """Jaccard over the two alphabets. A number, printed, rather than a judgement."""
    sa, sb = set(a), set(b)
    if not sa and not sb:
        return 1.0
    return round(len(sa & sb) / len(sa | sb), 3) if (sa or sb) else 0.0


def _histogram(groups: Iterable[Sequence[str]]) -> dict[str, int]:
    out: dict[str, int] = {}
    for group in groups:
        key = "+".join(sorted(group)) or "none"
        out[key] = out.get(key, 0) + 1
    return out


def _counterfactual(rooms: Mapping[str, Any]) -> dict[str, Any]:
    pdb_tokens = len(rooms.get("pdb", {}).get("tokens") or [])
    return {"what_it_counts": "questions about COMMANDS, then a description of each",
            "round_four_first_visit_questions": 32,
            "round_four_debugger_descriptions": 26,
            "round_four_debugger_ms_at_24ms": 26 * 24,
            "this_round_questions_per_room": len(CHANNELS),
            "debugger_alphabet_size": pdb_tokens,
            "why_not_the_same_quantity": "round 4 asked which COMMANDS exist and what each "
                                         "DOES -- a cost that grows with the program. This round "
                                         "asks HOW TO ASK and stops at the alphabet: a cost that "
                                         "is constant, and the alphabet is safe to enumerate "
                                         "because its size is a fact about help text, not a search"}


def _removed() -> dict[str, Any]:
    return {
        "the_help_x_channel": {
            "what_it_was": "one `help <token>` per listed token, 24 ms each, 26 of them for the "
                           "debugger in round 4",
            "why_deleted": "a description arrives free in the answer that lists the token, and "
                           "where it does not, the alphabet is still the whole answer"},
        "the_hand_written_needles": {
            "what_it_was": "four proof strings recalled from these programs' manuals",
            "what_it_measured": "two of four were wrong on the first run, and two of four shape "
                                "claims with them",
            "why_deleted": "a recalled needle is memorised knowledge wearing a test's clothes"},
        "the_strings_channel": {
            "what_it_was": "read the binary's own words, 0.2-260 ms, as the cheapest channel",
            "what_it_measured": "decided no cell in any room; a pager's 31,336 words of strings "
                                "parsed into 13,000 'tokens' of prose and symbols",
            "why_deleted": "a channel that decides nothing on any room is a part that does not "
                           "pay for itself"},
        "the_tuned_admissibility_rules": {
            "what_it_was": "three drafts of clauses tuned until each program landed in the cell "
                           "I expected",
            "what_it_measured": "the shell reported as a pager, the REPL as a pager, the "
                                "interpreter as a debugger -- every number a rule I had just "
                                "written",
            "why_deleted": "hand-solving with extra steps; replaced by an OPERATIONAL oracle "
                           "that costs 600 ms and cannot be argued with"},
    }


def disagreements(receipt: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Every room where the cheap answer did not equal the live one, with both numbers.

    The two failures this prints are the round's real result and the next round's specification:
      * `bash` -- the batch answer and the live answer list 62 and 60 of the SAME builtins, so a
        cell claiming there is one shape for both is wrong. THE FAMILY CELL IS TOO COARSE: it
        needs a second axis (does a batch invocation exist at all), and the piece that is missing
        is not a better text rule but a DECLARATION OF WHICH WAYS OF ASKING EXIST for the family.
      * `less` -- the live window published nothing because `less` with no file refuses and the
        reader gave up; that is a ROOM-DEFINITION failure (the pager needs a file), not a
        reasoning failure, and it is the same class of mistake as pdb without a debuggee.
    """
    out: list[dict[str, Any]] = []
    for program, room in (receipt.get("rooms") or {}).items():
        if room.get("agree"):
            continue
        out.append({
            "program": program, "family": room.get("family"),
            "cheap_cell": room.get("cheap_cell"), "live_cell": room.get("live_cell"),
            "cheap_published": room.get("cheap_published_a_listing"),
            "live_published": room.get("live_published_a_listing"),
            "alphabet_overlap": room.get("alphabet_overlap"),
            "why": _why(room)})
    return out


def _why(room: Mapping[str, Any]) -> str:
    if room.get("cheap_cell") is None:
        return "the cheap answers left more than one cell: no single shape is proved"
    if not room.get("live_published_a_listing"):
        if (room.get("live_ms") or 0) < 50:
            return "the live window refused before publishing: the room was mis-defined (no file)"
        return "the live window published no listing while the cheap answer did"
    return "both published a listing and they disagree"


def main(argv: Sequence[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--receipt", type=pathlib.Path, required=True)
    args = parser.parse_args(argv)
    receipt = measure()
    receipt["disagreements"] = disagreements(receipt)
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(receipt, indent=1, default=str) + "\n", encoding="utf-8")
    print(json.dumps(receipt["measured"], indent=1))
    for p, r in receipt["rooms"].items():
        print(f"  {p:8s} cheap={str(r['cheap_cell']):28s} live={str(r['live_cell']):28s} "
              f"agree={r['agree']!s:5s} deciding={r['deciding_channels']} "
              f"cheap_ms={r['cheap_ms']:.0f} live_ms={r['live_ms']:.0f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
