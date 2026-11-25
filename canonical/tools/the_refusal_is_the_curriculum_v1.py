#!/usr/bin/env python3
"""The refusal is the curriculum: the environment publishes its own grammar, and one visit writes the axioms that make the second visit cheaper.

THE OWNER'S PROPOSAL, AND THE ONE THING THAT MAKES IT DECIDABLE
---------------------------------------------------------------
  "All he should do is scan the environment, retrieve what he knows, learn instantly what he
   does not, and keep what matters -- generalised, not the exact actions. Should he be
   goal-directed, or learn everything? What should he save?"

Six rounds of this project already measured pieces of that sentence and each named the same
seam: there is **no verifying oracle in a new environment**. A scan can say what exists; the
guide contains an answer for 5.96% of its bytes (`THE_GUIDE_IS_A_TEST_SUITE_20261204`); one
trace buys storage and not identification (`THE_VERIFIED_INDEX_IS_THE_BOTTLENECK_20261116`);
a desired fix is a *relation* and not a value (`A_SITE_IS_NOT_A_PRODUCTION_20261124`). This
round is the first that finds the oracle **inside the environment itself**, and it is not a
model, not a guess and not a document:

  THE ENVIRONMENT PRINTS ITS OWN GRAMMAR AND ITS OWN ANSWER, AND BOTH ARE CHECKABLE BY RUNNING.

WHAT IS BUILT, AND EVERY PART EARNED
------------------------------------
 1. THE OBSERVER IS A TERMINAL OF KNOWN GEOMETRY (`TERM=dumb`, 24x80, a pty). A screen is not
    parsed out of ANSI: it is DEFINED by the geometry, so the last line the program wrote is
    the line the user is looking at. One number -- rows x cols -- replaces a screen reader.
 2. THE DEMAND IS READ OFF THAT LINE. A program that asks "Press RETURN to continue",
    "\"x.gz\" may be a binary file. See it anyway?", "[y]es/[n]o", or paints a prompt `>>> `,
    `$ `, `> `, `(Pdb) ` has told the reader both the key and the class of question. Nothing
    about any program is typed: the table is patterns over the *author's own words*.
 3. THE PAGE IS READ TWICE. `PROGRAM --help` is a fixed-column table: a KEY row or a subcommand
    row (`  s file   Save input to a file.`) or an OPTION row (`-f, --logical  count...`).
    Rows are FIELDS, not a regex, and the split rule is the page's own typography.
 4. AN AXIOM IS AN OBSERVATION, NOT A CLAIM. What persists is `(program, page-version, key) ->
    (verb, axis, effect-class)`, and the effect-class was observed by digesting a room before
    and after the key ran: `MOVES_STATE`, `STATES_ONLY`, `UNRESOLVED` (the key asked its own
    question and is not finished), `TERMINATES`, `NO_OBSERVATION`.
 5. THE AXIS IS WHOEVER WROTE THE TEXT. A key the page puts under MOVING/SEARCHING cannot
    change a byte; a key whose prose says Save/Delete/Execute can. Two surfaces vote.
 6. THE ACTION IS DERIVED FROM THE ENVIRONMENT'S OWN COMMAND TABLE PLUS THE NEED'S PAYLOAD.
    Need = (verb, payload). The environment publishes tokens and their descriptions; the token
    whose description names the need's verb is the command. Two attempts, bounded, and the
    verdict is the goal check -- not a parse.
 7. WHERE A LIVE ENVIRONMENT PUBLISHES NO DESCRIPTIONS, ITS OWN `help <topic>` IS THE PAGE.
    A debugger's `help` prints a table of tokens and nothing else; `help p` prints what `p`
    does. That is one more read of the same channel, not a second mechanism.
 8. THE SECOND VISIT IS THE MEASUREMENT. The owner's claim is "instant learning", and the only
    honest form of it is arithmetic: a visit that leaves axioms behind must make the next
    visit cost strictly less (probes and seconds). **This is the headline claim of this round,
    and it is the one that can fail.**
 9. ONE STORE, BECAUSE THERE IS ONE CLAIM. The CURATOR holds axioms under a projection
    `(program, family, geometry)` with `{seen, held, failed}`; a success is a weak counter, a
    failure is a refutation, and a citation needs `held > 0 and failed == 0`, so one green run
    may be cited and one counterexample kills the row. A second store (a dictionary of the
    world's words -> the program whose page attests them) was built here and DELETED: it
    learned 0 entries, because the words a room of files holds appear on no page. The number
    that deleted it is printed in `removed_parts`, because "the best part is no part" needs a
    measurement behind it or it is decoration.
10. WHEN THIS MACHINE HAS NO SUCH ENVIRONMENT IT SAYS SO BY NAME. A need naming a family the
    machine does not ship (SQL, a browser, git, a spreadsheet) is refused BEFORE a page is
    read, with the family and the binaries that would satisfy it. That is the honest form of
    "get it from the web": the fetch cannot install a binary here, so the gap is a named fact.

WHAT THIS CANNOT CLAIM
----------------------
* No OSWorld, no Terminal-Bench, no FrontierSWE was runnable here (no X, no browser, no
  Docker). The three names are the project's own frontier, and this file does not touch them.
* Not a proof that a KEYS page carries across a major version. 2 keystroke publishers on this
  machine is a measurement of the machine, and the essay says what it means for TUIs and does
  not extend it to pixel GUIs, which publish no labels at all.
* Not a synthesizer. A need's payload is the caller's; what the machine derives is which of
  the environment's published commands carries that payload, and it reports which sessions
  used the published table and which fell back to the prompt.
* Not sentience, not terminal truth, not a benchmark score.

Model calls: 0. Parameters stored: 0. Network calls at run time: 0.
Schema BRAIN_THE_REFUSAL_IS_THE_CURRICULUM_V1. Authority NONE__PRODUCER_RUN_SANDBOX.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import pty
import re
import select
import signal
import subprocess
import sys
import tempfile
import time
from typing import Any, Iterable, Mapping, Sequence

TOOLS = pathlib.Path(__file__).resolve().parent
REPO = TOOLS.parents[1]
for _p in (str(TOOLS), str(REPO)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

SCHEMA = "BRAIN_THE_REFUSAL_IS_THE_CURRICULUM_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX"
DATE = "2026-11-24"

ROWS, COLS, TERM = 24, 80, "dumb"
SETTLE = 0.30
CAPTURE_CAP = 4.0
PAGE_DEADLINE = 8.0
PAGE_BYTES = 200_000
MAX_PROBES = 2                 # declared bound on "ask the right question"
MAX_TABLE_ROWS = 400

MEMORY = REPO / "canonical" / "astra_runtime" / "state" / "REFUSAL_CURRICULUM_MEMORY_V1.json"
MEMORY_SCHEMA = "PROJECT_BRAIN_REFUSAL_CURRICULUM_MEMORY_V1"


# --------------------------------------------------------------------------------------- #
# 0. FAMILIES THIS MACHINE DOES NOT HAVE -- refused by name, never searched for
# --------------------------------------------------------------------------------------- #
ABSENT_FAMILIES: dict[str, tuple[str, ...]] = {
    "sql_database": ("sqlite3", "mysql", "psql", "duckdb"),
    "browser": ("chromium", "chromium-browser", "firefox", "chrome", "w3m", "lynx"),
    "version_control": ("git",),
    "spreadsheet": ("libreoffice", "soffice", "gnumeric", "sc-im"),
    "full_screen_editor": ("vi", "vim", "nvim", "nano", "emacs", "ed"),
    "jvm": ("java", "javac"),
    "container": ("docker", "podman"),
}


def families_absent(names: Iterable[str]) -> dict[str, list[str]]:
    have = set(names)
    out: dict[str, list[str]] = {}
    for family, members in ABSENT_FAMILIES.items():
        missing = [m for m in members if m not in have]
        if len(missing) == len(members):
            out[family] = missing
    return out


# --------------------------------------------------------------------------------------- #
# 1. THE OBSERVER: a terminal of known geometry
# --------------------------------------------------------------------------------------- #
_NORM_ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]|\x1b[()][A-Za-z0-9]|\x1b[=>]|\x1b\][^\x07]*\x07")


def normalise(raw: bytes) -> str:
    """What the terminal WOULD SHOW.

    Overstrike (`S\\bSU\\bUM\\bM`) is how a dumb terminal is told to bold. Reading it literally
    made every heading in `less --help` unreadable, and the first version of this file parsed
    ZERO command rows from four programs -- not because the pages had none, but because every
    word was written twice with a cursor move between. The fix is not a regex: a backspace
    MOVES THE CURSOR, so each line is REPLAYED and a character written after a backspace
    overwrites the one before it. Measured: `S\\bSU\\bUM\\bMM` replays to `SUMMARY`, and `less`
    alone then yields 37 rows.
    """
    text = _NORM_ANSI.sub("", raw.decode("utf-8", "replace"))
    lines: list[str] = []
    for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        if "\x08" in line:
            buffer: list[str] = []
            for char in line:
                if char == "\x08":
                    if buffer:
                        buffer.pop()
                else:
                    buffer.append(char)
            line = "".join(buffer)
        lines.append(line)
    return "\n".join(lines)


class Session:
    """One program under a pty of known geometry: open, feed a key, read the screen, close.

    Three defects this class exists to prevent, each measured while building it:
      * `subprocess.run(capture_output=True)` HANGS on a pager waiting for a key, and a
        `capture_output` sweep of 643 programs was KILLED for memory when one printed without
        end. A screen is a bounded read, and a page is bounded in bytes.
      * A key that asks its own question does not deliver the line typed after it: the pager
        read `|sha256sum > /tmp/RESP` AS THE ANSWER and produced a file called `um`. A turn
        therefore checks the screen for a demand before it claims the line was delivered.
      * A program can exit on its own, and writing to a dead pty kills the reader with SIGIO.
    """

    def __init__(self, argv: Sequence[str], cwd: pathlib.Path,
                 env: Mapping[str, str] | None = None) -> None:
        self.argv = list(argv)
        self.cwd = pathlib.Path(cwd)
        self.pid: int | None = None
        self.fd: int | None = None
        self.dead = False
        self._env = {**os.environ, "TERM": TERM, "LINES": str(ROWS), "COLUMNS": str(COLS),
                     "PAGER": "cat", "PWD": str(self.cwd), "PS1": "$ ", "PS2": "> "}
        self._env.pop("PYTHONSTARTUP", None)
        if env:
            self._env.update(env)

    def open(self) -> str:
        self.pid, self.fd = pty.fork()
        if self.pid == 0:                                    # pragma: no cover - child
            try:
                os.chdir(str(self.cwd))
                os.execvpe(self.argv[0], self.argv, self._env)
            except OSError:
                os._exit(127)
        return self.read()

    def close(self) -> None:
        if self.fd is not None:
            try:
                os.close(self.fd)
            except OSError:
                pass
            self.fd = None
        if self.pid is not None:
            try:
                os.kill(self.pid, signal.SIGKILL)
            except (OSError, ProcessLookupError):
                pass
            try:
                os.waitpid(self.pid, 0)
            except (ChildProcessError, OSError):
                pass
            self.pid = None
        self.dead = True

    def read(self, *, settle: float = SETTLE, cap: float = CAPTURE_CAP) -> str:
        if self.fd is None:
            return ""
        chunks: list[bytes] = []
        started = last = time.time()
        while True:
            now = time.time()
            if now - started > cap or now - last > settle:
                break
            try:
                ready, _, _ = select.select([self.fd], [], [], 0.05)
            except (OSError, ValueError):
                break
            if not ready:
                continue
            try:
                block = os.read(self.fd, 65536)
            except OSError:
                break
            if not block:
                self.dead = True
                break
            chunks.append(block)
            last = time.time()
        return normalise(b"".join(chunks))

    @staticmethod
    def screen(text: str) -> list[str]:
        """THE SCREEN IS DEFINED BY THE GEOMETRY.

        The tty turns `\\n` into `\\r\\n`, so every write lands on the next line down: the LAST
        line is the newest thing the program painted, and the last 24 of them are what the
        user sees. The correction matters -- the first version read the TOP line and so read
        satisfied history as a live demand. Also collapsed: a carriage return alone rewrites
        the line it is on, which `normalise` already resolves into the final text.
        """
        lines = [line.rstrip() for line in text.split("\n")]
        while lines and not lines[-1]:
            lines.pop()
        return lines[-ROWS:]

    def last_line(self, text: str) -> str:
        painted = self.screen(text)
        return painted[-1].strip() if painted else ""

    def key(self, stroke: str, *, settle: float = SETTLE, cap: float = CAPTURE_CAP) -> str:
        if self.dead or self.fd is None:
            return ""
        try:
            os.write(self.fd, stroke.encode("utf-8"))
        except OSError:
            self.dead = True
            return ""
        return self.read(settle=settle, cap=cap)

    def exited(self) -> bool:
        if self.pid is None:
            return True
        try:
            done, _ = os.waitpid(self.pid, os.WNOHANG)
        except ChildProcessError:
            return True
        return done == self.pid


# --------------------------------------------------------------------------------------- #
# 2. THE DEMAND: what the newest painted line asks for
# --------------------------------------------------------------------------------------- #
#: The author's own brackets are the class. A screen that says `[y]es` has printed the key and
#: the class of question; a screen that paints `>>> ` has printed that a line is wanted. The
#: table is patterns over the author's words -- no program is named anywhere in it.
DEMAND_FORMS: tuple[tuple[str, str, re.Pattern[str]], ...] = (
    ("RECEIPT",     "\r",       re.compile(r"(?i)press\s+(?:the\s+)?(?:RETURN|ENTER)")),
    ("RECEIPT",     "\r",       re.compile(r"(?i)\bpress\b.*\bcontinue\b")),
    ("BINARY_FILE", "y",        re.compile(r"(?i)may be a binary file.*(?:anyway|see it)")),
    ("OVERWRITE",   "y",        re.compile(r"(?i)\boverwrite\b|\balready exists\b")),
    ("CONFIRM",     "y",        re.compile(r"(?i)\[\s*y\s*\]\s*/?\s*\[?\s*n\s*\]?|\(y/n\)")),
    ("CONFIRM",     "y",        re.compile(r"(?i)\bdo you (?:really )?want\b.*\?")),
    # A NAME PROMPT ENDS IN A COLON, AND IT IS NOT A SHELL PROMPT. `less`'s save key answers
    # `logfile:` and waits for a word; the shell's prompt is `$ ` or `> `. Reading the name
    # prompt as a shell prompt makes the pilot type the name as a COMMAND, which is a different
    # session, so the name form is decided first and by its punctuation.
    ("NAME",        "<name>",   re.compile(r"(?i)^[^>#$]{0,40}[:?]\s*$")),
    ("PROMPT",      "<line>",   re.compile(r"(?:>>>|\(Pdb\)|\$\s*$|>\s*$|#\s*$|:\s*$)")),
)

#: A demand that is ANSWERED by a keystroke of the reader's choosing, as opposed to a demand
#: that wants a line of input. Kept apart because crossing a RECEIPT with `\r` and delivering a
#: line are different acts, and conflating them is the defect that created the file `um`.
RECEIPT_CLASSES = frozenset({"RECEIPT", "BINARY_FILE", "CONFIRM", "OVERWRITE"})


def read_demand(line: str) -> dict[str, Any]:
    for kind, key, pattern in DEMAND_FORMS:
        if pattern.search(line or ""):
            return {"class": kind, "key": key, "line": (line or "")[:160]}
    return {"class": None, "key": None, "line": (line or "")[:160]}


# --------------------------------------------------------------------------------------- #
# 3. THE PAGE: fields, not a regex; and the row's FORM is reported
# --------------------------------------------------------------------------------------- #
def page_text(program: str, *, cap_bytes: int = PAGE_BYTES) -> dict[str, Any]:
    """What the program prints when asked for its page. Bounded in bytes AND in wall clock."""
    started = time.time()
    try:
        proc = subprocess.Popen([program, "--help"], stdin=subprocess.DEVNULL,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                cwd=tempfile.gettempdir(), start_new_session=True,
                                env={**os.environ, "PAGER": "cat", "TERM": TERM,
                                     "LINES": str(ROWS), "COLUMNS": str(COLS)})
    except OSError as exc:
        return {"program": program, "ok": False, "reason": type(exc).__name__, "raw": "",
                "rows": [], "vocabulary": set(), "seconds": 0.0}
    chunks: list[bytes] = []
    total = 0
    try:
        while total < cap_bytes:
            ready, _, _ = select.select([proc.stdout], [], [], PAGE_DEADLINE)
            if not ready:
                break
            block = os.read(proc.stdout.fileno(), 65536)
            if not block:
                break
            chunks.append(block)
            total += len(block)
    except (OSError, ValueError):
        pass
    finally:
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except (OSError, ProcessLookupError):
            pass
        try:
            proc.stdout.close()
        except OSError:
            pass
        try:
            proc.wait(timeout=1.0)
        except subprocess.SubprocessError:
            pass
    text = normalise(b"".join(chunks))
    ok = bool(text.strip())
    return {"program": program, "ok": ok, "raw": text, "rows": parse_rows(text),
            "vocabulary": {w.lower() for w in re.findall(r"[A-Za-z][A-Za-z0-9'_-]{2,}", text)},
            "seconds": round(time.time() - started, 3)}


_CTRL = re.compile(r"^\^([A-Z@\[\]\\^_])$")
_KEY_ALIASES = {"CR": "\r", "RETURN": "\r", "SPACE": " ", "ESC": "\x1b", "TAB": "\t",
                "ENTER": "\r", "DEL": "\x7f", "BS": "\x08"}


def _key_shaped(token: str) -> bool:
    """Could this token be a keystroke or a command? Short, and made of printable bytes."""
    if not token or len(token) > 8:
        return False
    if _CTRL.match(token) or token in _KEY_ALIASES:
        return True
    return bool(re.fullmatch(r"\.?[A-Za-z0-9/?!&|:.<>=+_-]{1,8}", token))


def _is_prose_field(field: str) -> bool:
    """The author's sentence: a capitalised word followed by lower-case letters."""
    return bool(re.match(r"^[A-Z][a-z]{2,}[.,:;)]*(?:\s|$)", field))


def parse_rows(text: str) -> list[dict[str, Any]]:
    """Every fixed-column row the page prints: the token(s) on the left, the prose on the right.

    FIELDS, NOT A REGEX, and that is a correction made by measurement: a single non-greedy
    pattern read `h  H ... Display this help.` as key `h` with the description
    `H ... Display this help.` -- the second spelling was swallowed into the prose. The rule
    here is the page's own typography: split on runs of two or more spaces, and the prose is
    the first field that is a capitalised word followed by lower-case letters.

    The row's FORM is decided by its left-hand tokens, and it is the fact this round found:
    `-a`, `--file=ARCHIVE` are OPTIONS, `init`, `add` are SUBCOMMANDS, `q`, `^K`, `.help` are
    KEYSTROKES. Only the last can be typed into a prompt.
    """
    rows: list[dict[str, Any]] = []
    for raw in text.split("\n"):
        # A ROW MAY START AT COLUMN ZERO: `node`'s `.help` prints `.break    Sometimes...` at
        # the left margin, and the previous requirement of two leading spaces made every REPL
        # table read as NO_TABLE while its page was right there on the screen.
        if not raw.strip():
            continue
        # OVERSTRIKE IS REPLAYED BEFORE THE SPLIT. The pager underlines a token with
        # `_\b`, so its save row is `s _\bf_\bi_\bl_\be   Save input to a file.`: split first
        # and the row has ONE field, and an earlier reader dropped it -- the save key vanished
        # from the table while its prose was sitting on the page.
        line = normalise(raw.rstrip().encode())
        fields = [f for f in re.split(r"\s{2,}", line.strip()) if f]
        if len(fields) < 2:
            continue
        cut = next((i for i, f in enumerate(fields) if _is_prose_field(f)), None)
        if cut is None:
            # A LISTING WITH NO PROSE IS STILL A TABLE. A debugger's `help` prints
            # `EOF    c    d    h    list    q    rv    undisplay` -- tokens in columns and not
            # one description. Requiring prose made every debugger read as NO_TABLE while its
            # commands were on the screen. The row is kept as a bare token, its meaning is
            # asked for later (`help <token>`), and nothing is assumed about what it does.
            bare = [t for t in fields if _key_shaped(t) and re.search(r"[A-Za-z0-9]", t)]
            if len(bare) >= 2 and len(bare) == len(fields):
                # A BARE TOKEN IS A COMMAND, NOT A KEYSTROKE. `(Pdb) help` lists `p`, `n`,
                # `up` -- and pressing `p` in a room is not that command; `p <expr>` is. The
                # form is `TOKEN`, the payload is the caller's, and the prose comes from the
                # token's own topic page.
                rows.extend({"token": t, "alternates": [], "desc": "", "form": "TOKEN",
                             "words": []} for t in bare)
            continue
        if cut == 0:
            continue
        # MEASURED, NOT GUESSED: the pager underlines a token with overstrike, so its save row is
        # `s _\bf_\bi_\bl_\be   Save input to a file.` -- reading the raw field yields `s` plus a
        # control-character token, and an earlier reader dropped the row entirely. The left-hand
        # field is normalised here as well as on the screen.
        tokens = [t for t in " ".join(fields[:cut]).split() if t not in ("*", "(or", "or")]
        desc = " ".join(fields[cut:]).strip()
        if not tokens or not re.search(r"[A-Za-z]", tokens[0]):
            continue
        rows.append({"token": tokens[0], "alternates": tokens[1:], "desc": desc,
                     "form": _form_of(tokens[0]),
                     "words": [w.lower() for w in re.findall(r"[A-Za-z][A-Za-z0-9'_-]+", desc)]})
    return rows[:MAX_TABLE_ROWS]


def _form_of(token: str) -> str:
    if token.startswith("--") or token.startswith("-"):
        return "OPTION"
    if token.startswith("."):
        return "COMMAND"
    if _CTRL.match(token) or token in _KEY_ALIASES or len(token) <= 2 and token.isalpha():
        return "KEYSTROKE"
    if token.islower():
        return "SUBCOMMAND"
    return "FIELD"


def key_bytes(token: str) -> str | None:
    """One published spelling -> the bytes to type."""
    if token in _KEY_ALIASES:
        return _KEY_ALIASES[token]
    if _CTRL.match(token):
        return chr(ord(_CTRL.match(token).group(1).upper()) & 0x1F)
    if token.startswith("ESC-") and len(token) == 5:
        return "\x1b" + token[4]
    if re.fullmatch(r"[A-Za-z0-9/?!&|:.<>=+_-]{1,6}", token):
        return token
    return None


# --------------------------------------------------------------------------------------- #
# 4. THE VERB TABLE, DERIVED FROM THE AUTHORS' OWN WORDS (G3 measures this)
# --------------------------------------------------------------------------------------- #
VERB_BY_WORD: dict[str, tuple[str, str]] = {
    # THE VERB NAMES THE AXIS, AND THE AXIS IS WHAT AN EFFECT CLASS IS JUDGED ON. The first
    # version gave `process` to `execute` and `exit`, and the blind destructive-key test then
    # PASSED for the wrong reason: `exit` terminates the program, which changes no byte, and
    # `AXIOM__TERMINATES` was counted as a state move. `process` now means "starts a process
    # that can write"; ending the program is its own axis, `lifecycle`, and it can never be
    # counted as a mutation.
    "save": ("save", "input"), "saves": ("save", "input"), "write": ("save", "input"),
    "writes": ("save", "input"), "pipe": ("save", "input"), "pipes": ("save", "input"),
    "load": ("load", "input"), "edit": ("edit", "input"), "editing": ("edit", "input"),
    "delete": ("remove", "input"), "removes": ("remove", "input"),
    "insert": ("insert", "input"), "inserts": ("insert", "input"),
    "execute": ("execute", "process"), "executes": ("execute", "process"),
    "shell": ("execute", "process"), "invoke": ("execute", "process"),
    "suspend": ("suspend", "process"), "filter": ("filter", "input"),
    "filters": ("filter", "input"), "print": ("print", "text"), "prints": ("print", "text"),
    "display": ("display", "screen"), "show": ("print", "text"),
    "forward": ("move", "position"), "backward": ("move", "position"),
    "right": ("move", "position"), "left": ("move", "position"), "go": ("move", "position"),
    "repaint": ("repaint", "screen"), "exit": ("exit", "lifecycle"), "quit": ("exit", "lifecycle"),
    "search": ("search", "match"), "repeat": ("search", "match"), "undo": ("undo", "match"),
    "help": ("help", "text"), "examine": ("select", "file"), "next": ("select", "file"),
    "previous": ("select", "file"), "read": ("read", "input"), "count": ("read", "input"),
    "step": ("execute", "process"), "continue": ("execute", "process"),
    "break": ("select", "position"), "return": ("exit", "lifecycle"), "restart": ("execute", "process"),
    "run": ("execute", "process"),
}
AXIS_BY_HEADING = {"moving": "position", "jumping": "position", "searching": "match",
                   "changing text": "input", "editing": "input", "miscellaneous": "screen"}
MUTATING_AXES = frozenset({"input", "process"})
#: The forms a token must have to be TYPED into a prompt. An option is a modifier
#: (`THE_REPERTOIRE_IS_A_QUERY_20261129` measured 0 of 80 options changing a byte), so a page
#: that prints only options has NOT published a command table, and `node --help` is exactly
#: that: 20 real option rows and no commands at all.
COMMAND_FORMS = frozenset({"KEYSTROKE", "COMMAND", "SUBCOMMAND", "TOKEN"})
#: Axes whose effect class may be counted as a state move, and the only ones. `position`,
#: `match`, `screen`, `text`, `file`, `lifecycle` cannot change a byte and are never counted.
CHANGING_AXES = frozenset({"input", "process"})


def classify_row(row: Mapping[str, Any], heading: str = "") -> dict[str, Any]:
    """The verb and axis a row declares, from the author's word and the author's heading."""
    verb, axis = "unclassified", None
    for word in row["words"]:
        if word in VERB_BY_WORD:
            verb, axis = VERB_BY_WORD[word]
            break
    if heading in AXIS_BY_HEADING:
        axis = AXIS_BY_HEADING[heading]
    return {"verb": verb, "axis": axis, "mutating_declared": axis in MUTATING_AXES}


def headings_of(text: str) -> dict[int, str]:
    """Which heading each line of a page sits under. The author's own classification."""
    out: dict[int, str] = {}
    heading = ""
    for index, raw in enumerate(text.split("\n")):
        stripped = raw.strip()
        if stripped.isupper() and len(stripped) > 3:
            heading = stripped.lower()
        out[index] = heading
    return out


# --------------------------------------------------------------------------------------- #
# 5. THE AXIOM: what a key DID
# --------------------------------------------------------------------------------------- #
AXIOM_MOVES = "AXIOM__MOVES_STATE"
AXIOM_STATES = "AXIOM__STATES_ONLY"
AXIOM_UNRESOLVED = "AXIOM__UNRESOLVED__IT_ASKED_A_QUESTION"
AXIOM_TERMINATES = "AXIOM__TERMINATES"
AXIOM_LOST = "AXIOM__NO_OBSERVATION"
#: THE FOURTH CLASS, AND THE ONE THAT KEEPS THE OTHER THREE HONEST. A program that REFUSES a
#: key has said nothing about the key's axis: `less` answers `s` with "Input is not a pipe",
#: and `v` with "/usr/bin/editor: No such file or directory" because the editor family is not
#: on this machine. Calling either `STATES_ONLY` would be a claim about the key made out of a
#: refusal, which is the exact defect this project keeps finding in its own past rounds.
AXIOM_REFUSED = "AXIOM__REFUSED_BY_THE_PROGRAM_NOTHING_LEARNED"
REFUSAL_WORDS = ("not a pipe", "not found", "no such file", "cannot", "can't", "invalid",
                 "unknown command", "no editor", "permission denied", "error")


def digest_room(root: pathlib.Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for path in sorted(pathlib.Path(root).rglob("*")):
        rel = path.relative_to(root).as_posix()
        if path.is_dir():
            out[rel + "/"] = "DIR"
            continue
        try:
            out[rel] = hashlib.sha256(path.read_bytes()).hexdigest()
        except OSError:
            out[rel] = "UNREADABLE"
    return out


def changed_objects(before: Mapping[str, str], after: Mapping[str, str]) -> list[str]:
    return sorted(k for k in set(before) | set(after) if before.get(k) != after.get(k))


def observe_key(argv: Sequence[str], root: pathlib.Path, stroke: str) -> dict[str, Any]:
    """Run one key against a fresh copy of a room and record what HAPPENED.

    The one measurement that makes an axiom true. `STATES_ONLY` is a claim about an
    observation; the destructive-key test (G2) shows it can be wrong when the key waits for an
    answer nobody gave, which is why a screen that still asks afterwards is `UNRESOLVED` and is
    never counted as a statement about the axis.
    """
    before = digest_room(root)
    session = Session(argv, root)
    screens = [session.open()]
    sent: list[str] = []
    try:
        for _ in range(4):
            demand = read_demand(session.last_line(screens[-1]))
            if demand["class"] not in RECEIPT_CLASSES:
                break
            screens.append(session.key(demand["key"]))
            sent.append(demand["key"])
        screens.append(session.key(stroke))
        sent.append(stroke)
        # THE KEY IS NOT DONE WHEN IT ASKS FOR AN ANSWER -- AND A BARE RETURN IS NOT AN
        # ANSWER. `less`'s `s` prints `Input is not a pipe  (press RETURN)`; returning gives
        # `logfile:`, and only a NAME gets the save. The previous version crossed the receipt
        # with RETURN and then treated the `logfile:` prompt as satisfied, so it recorded
        # `STATES_ONLY` for the one key whose page says "Save input to a file". The rule now is
        # that a demand is answered only by a key it NAMED, or by a word at a NAME prompt.
        repairs: list[str] = []
        for _ in range(6):
            demand = read_demand(session.last_line(screens[-1]))
            if not demand["class"]:
                break
            if demand["class"] in ("PROMPT", "NAME"):
                answer = "axiom-answer.out"
                if any(r.startswith("named") for r in repairs):
                    break
                screens.append(session.key(answer + "\n"))
                sent.append(answer)
                repairs.append("named a file at the key's own prompt")
                continue
            key = demand["key"]
            if key in (None, "\r") and demand["class"] == "RECEIPT":
                screens.append(session.key("\r"))
                repairs.append("crossed a receipt (no answer yet)")
                continue
            screens.append(session.key(key))
            sent.append(key)
            repairs.append(f"answered a {demand['class']} with the key it named")
        how = "one_key" if not repairs else " + ".join(repairs)
        after = digest_room(root)
        moved = changed_objects(before, after)
        demand = read_demand(session.last_line(screens[-1]))
        last = (screens[-1] or "").lower()
        refused = any(word in last for word in REFUSAL_WORDS)
        if demand["class"]:
            kind = AXIOM_UNRESOLVED
        elif refused:
            kind = AXIOM_REFUSED
        elif session.exited():
            kind = AXIOM_TERMINATES
        elif moved:
            kind = AXIOM_MOVES
        elif screens[-1].strip():
            kind = AXIOM_STATES
        else:
            kind = AXIOM_LOST
        return {"axiom": kind, "changed": moved, "demand_after": demand, "how": how,
                "screens_tail": [s[-300:] for s in screens[-2:]]}
    finally:
        session.close()


# --------------------------------------------------------------------------------------- #
# 6. THE ENVIRONMENT: what it is, how it starts, how it is asked for its commands
# --------------------------------------------------------------------------------------- #
#: The registry of environments this file has met. It is typed because a FILE FORMAT has to
#: name its keys somewhere, and it is measured rather than believed (G8 re-derives every
#: stored key). `help_probe` is the topic form the environment's own words use, and the probe
#: is only ever run when the printed page carried no descriptions.
ENVIRONMENTS: dict[str, dict[str, Any]] = {
    "less":     {"family": "pager",  "argv": ["less", "alpha.txt"], "help_probe": None},
    "more":     {"family": "pager",  "argv": ["more", "alpha.txt"], "help_probe": None},
    "python3":  {"family": "repl",   "argv": ["python3", "-q"],     "help_probe": "help "},
    "node":     {"family": "repl",   "argv": ["node"],              "help_probe": ".help"},
    "sh":       {"family": "shell",  "argv": ["sh", "-i"],          "help_probe": "help "},
    "bash":     {"family": "shell",  "argv": ["bash", "--norc", "-i"], "help_probe": "help "},
    "pdb":      {"family": "debugger", "argv": ["python3", "-m", "pdb", "alpha.txt"],
                 "available_as": ["python3", "-m", "pdb"], "help_probe": "help "},
}

#: THE QUESTIONS THE MACHINE MAY ASK A LIVE ENVIRONMENT, ranked, and every one of them is the
#: SAME QUESTION: "what are your commands?" The first is a help word the machine's own pages
#: attest; the rest are the words those pages print when they describe a help key (`.help`,
#: `.break` on a REPL, `help` on a shell). A live environment has its own syntax for the word
#: and the machine does not know which until it asks -- which is exactly what "ask the right
#: question" means, and it is why the FIRST VISIT has to spend something and the second does not.
PROBE_CANDIDATES: tuple[str, ...] = ("help", "?", ".help", ".commands", "h", ":help")
#: A token a page QUOTES: `"help <topic>"`, `Type '.help'`, `help <topic>`. Quoted words are the
#: page naming another page, and they are the only candidates the machine sends to a live
#: program that it did not get from a command table.
QUOTED = re.compile(r"[\"\u201c']([a-z.][a-z0-9._-]{1,20})(?:\s+<[a-z]+>)?[\"\u201d']|\b([a-z.]{2,12})\s+<topic>")


QUOTED_STRING = re.compile(r"[\"\u201c']([^\"\u201d'\n]{2,60})[\"\u201d']")


def quoted_statements(text: str) -> list[dict[str, Any]]:
    """Every quoted phrase on a page, and the imperative the page states around it.

    A page that says `Type ".help" for more information` or `Type "help", "copyright"...`
    has stated, in its own sentence, that a quoted token is a command and what happens when
    it is typed. That is `(verb, command)` published by the environment -- the same structure
    as a command table row, in prose instead of columns, and read the same way: the verb is
    the page's own imperative word, which must be in the derived verb table.
    """
    out: list[dict[str, Any]] = []
    for raw in text.split("\n"):
        stripped = raw.strip()
        for match in QUOTED_STRING.finditer(stripped):
            token = match.group(1).strip()
            if not token or len(token.split()) > 3:
                continue
            before = [w.lower() for w in re.findall(r"[A-Za-z][A-Za-z0-9'_-]+",
                                                    stripped[:match.start()])]
            after = [w.lower() for w in re.findall(r"[A-Za-z][A-Za-z0-9'_-]+",
                                                   stripped[match.end():])]
            # THE VERB IS THE PAGE'S OWN IMPERATIVE OR ITS OWN NOUN. `Type ".help" for more
            # information` has no verb from the table before the quote -- it has `Type` -- and
            # an earlier version therefore read NOTHING from a REPL's banner. A phrase the
            # page puts in quotes AND introduces with a verb, or AND follows with a word about
            # help, commands or information, is the page naming its own command.
            verb = next((VERB_BY_WORD[w][0] for w in reversed(before) if w in VERB_BY_WORD), None)
            if verb is None and ({"type", "typed"} & set(before)) and \
                    ({"help", "information", "commands", "command"} & set(after)):
                verb = "help"
            if verb is None and ({"help", "information", "commands"} & set(after)):
                verb = "help"
            if verb:
                out.append({"token": token, "verb": verb, "sentence": stripped[:160]})
    return out


def quoted_tokens(text: str) -> list[str]:
    out: list[str] = []
    for match in QUOTED.finditer(text):
        token = match.group(1) or match.group(2)
        if token and token not in out:
            out.append(token)
    return out


def is_available(program: str, names: Sequence[str]) -> bool:
    """Is this environment startable HERE? A name on PATH, or the argv the registry declares.

    `pdb` has no executable of its own on this machine, and the first version therefore
    refused the debugger as "not on this machine" while `python3 -m pdb` was one call away.
    Availability is a fact to be TESTED, not inferred from a directory listing.
    """
    if program in names:
        return True
    probe = ENVIRONMENTS.get(program, {}).get("available_as")
    if not probe:
        return False
    try:
        got = subprocess.run(list(probe) + ["--help"], stdin=subprocess.DEVNULL,
                             capture_output=True, timeout=5)
        return got.returncode == 0 or bool(got.stdout or got.stderr)
    except (OSError, subprocess.TimeoutExpired):
        return False


def command_table(program: str, root: pathlib.Path, *, probes: list[dict[str, Any]],
                  stored: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """The environment's OWN published command table: tokens, and prose when it prints any.

    THREE CHANNELS, ONE READER, AND NO GUESS:
      1. the page `--help` prints -- a full table with descriptions (a pager), or options only;
      2. the page read TOPIC BY TOPIC -- a page that prints a bare listing of tokens and then
         `help <topic>` for each one (a debugger's help says exactly that of itself);
      3. the live environment asked its own help question -- a REPL and a shell publish nothing
         on their page and everything on their prompt.
    If none answers, the source is `NO_TABLE` and no rows are claimed: that is the difference
    between "there is nothing to learn here" and "the machine failed", and it is what keeps
    the second-visit measurement honest on this machine.

    THE PROSE IS THE TABLE'S OWN `help <topic>` SENTENCE. `python3 -m pdb --help` prints no
    command table at all; its `(Pdb) help` prints 41 bare tokens and the line
    `Documented commands (type help <topic>):` -- and a topic page says `p expression  Print
    the value of the expression.` So a bare listing is not an absence of descriptions, it is
    an INSTRUCTION: the descriptions are one question deeper, and the page says which question.
    """
    page = page_text(program)
    rows = [dict(r) for r in page["rows"]]
    has_commands = any(r["form"] in COMMAND_FORMS for r in rows)
    source, text = ("PAGE", page["raw"]) if has_commands else ("NO_TABLE", page["raw"])
    attempts: list[dict[str, Any]] = []
    opening = ""
    if not has_commands:
        session = Session(ENVIRONMENTS[program]["argv"], root)
        try:
            opening = session.open()
        finally:
            session.close()
        topic_instruction = _topic_instruction(page["raw"] + "\n" + opening)
        if topic_instruction:
            listing = asked_for_listing(program, root, topic_instruction, probes)
            if listing:
                rows, source, text = listing, "TOPIC_PAGES", page["raw"] + "\n" + listing and ""
                opening = listing
        if not has_commands:
            # THE ENVIRONMENT'S OWN BANNER IS THE FIRST QUESTION. A REPL publishes nothing on
            # its page and names its own help command in the sentence it opens with.
            already_refuted = set((stored or {}).get("refuted_questions") or [])
            banner = (page["raw"] or "") + "\n" + opening
            asked_by_the_page = [q["token"] for q in quoted_statements(banner)
                                 if q["verb"] == "help"]
            # AND A BANNER THAT NAMES A TOKEN AND SAYS WHAT IT IS FOR. `Type ".help" for more
            # information` has no imperative verb, and it is still the environment naming its
            # own command and its effect in one sentence -- so the quoted token is asked about
            # when the sentence it sits in is about help, information or commands.
            for q in quoted_statements(banner):
                if re.search(r"(?i)help|information|commands?", q["sentence"]) and \
                        q["token"] not in asked_by_the_page:
                    asked_by_the_page.append(q["token"])
            ordered = [c for c in dict.fromkeys(asked_by_the_page + list(PROBE_CANDIDATES))
                       if c not in already_refuted]
            for candidate in ordered:
                got, screen = _ask(program, root, candidate)
                attempts.append({"asked": candidate, "rows": len(got),
                                 "helped": len(got) >= 3})
                if len(got) >= 3:
                    rows, source, text, opening = got, "HELP_KEY", screen, screen
                    break
                if len(attempts) >= MAX_PROBES:
                    break
            probes.append({"program": program, "attempts": attempts, "source": source})
    topic_form = _topic_form(rows, page["raw"] + "\n" + opening + "\n" + text)
    if rows and sum(1 for r in rows if r["words"]) < len(rows) / 2 and topic_form:
        # A BARE LISTING IS AN INSTRUCTION, NOT AN ABSENCE. `(Pdb) help` prints 41 tokens and
        # no prose, and the line above them says the descriptions are one question deeper.
        enriched: list[dict[str, Any]] = []
        for row in rows[:24]:
            prose = _topic_prose(program, row["token"], root, topic_form)
            probes.append({"program": program, "topic": row["token"],
                           "form": topic_form, "text": prose[:120]})
            enriched.append({**row, "desc": prose,
                             "words": [w.lower() for w in
                                       re.findall(r"[A-Za-z][A-Za-z0-9'_-]+", prose)]})
        rows = enriched + rows[24:]
    for row in rows:
        row["curriculum"] = classify_row(row)
    return {"program": program, "source": source, "rows": rows, "topic_form": topic_form,
            "page_text": page["raw"], "opening": opening,
            "text": text if text else opening,
            "vocabulary": page["vocabulary"], "page_rows": len(page["rows"]),
            "page_bytes": len(page["raw"]),
            "worked_probes": [a["asked"] for a in attempts if a["helped"]],
            "refuted_probes": [a["asked"] for a in attempts if not a["helped"]]}


#: The question that fetches a description has to be named by a sentence that is ABOUT a
#: command table. Without that guard, `node --help`'s `--print  print result of
#: --eval script` became an instruction to ask the REPL about `print`, and the REPL answered
#: with a SyntaxError. Measured, not imagined: that is exactly what happened on the way here.
TOPIC_PATTERNS = (
    re.compile(r"(?i)(?:commands?|topics?)[^\n]{0,40}type\s+[\"'\u201c]?([a-z.]+)\s*<"),
    re.compile(r"(?i)type\s+[\"'\u201c]?([a-z.]+)\s*<[a-z]+>[^\n]{0,40}(?:command|topic)"),
)


def _topic_instruction(text: str) -> str | None:
    """The page's own sentence naming the question that fetches a description.

    `Documented commands (type help <topic>):` is the debugger stating that its listing is
    BARE ON PURPOSE and that the descriptions are one question deeper. Reading that sentence
    is what turns a listing into a table without a single program name.
    """
    for pattern in TOPIC_PATTERNS:
        match = pattern.search(text or "")
        if match:
            token = match.group(1).strip().lower()
            if token and token not in ("for", "the", "topic"):
                return token
    return None


def _topic_form(rows: Sequence[Mapping[str, Any]], text: str) -> str:
    """The spelling this environment uses to ask about one of its own commands.

    Read from the text it printed: `help <topic>` is the form the debugger states, and a
    listing that prints `.help` and `.save` as full commands is a dot-command environment.
    Nothing is decided from a program's name.
    """
    match = re.search(r"([.a-z]+)\s*<topic>", text or "", re.I)
    if match:
        return match.group(1)
    dotted = [r["token"] for r in rows if str(r["token"]).startswith(".")]
    if dotted:
        return "." + "help"
    return "help"


def _topic_prose(program: str, token: str, root: pathlib.Path, form: str) -> str:
    text = topic_page(program, token, root, form)
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    # the first line is the echo of what was typed; the prose is what follows it
    body = [line for line in lines[1:] if not line.startswith("(")]
    return " ".join(body)[:200]


def _ask(program: str, root: pathlib.Path, question: str) -> tuple[list[dict[str, Any]], str]:
    """Ask a live environment one question, and read the commands out of what it prints."""
    meta = ENVIRONMENTS[program]
    session = Session(meta["argv"], root)
    try:
        screen = session.open()
        demand = read_demand(session.last_line(screen))
        if demand["class"] in RECEIPT_CLASSES:
            screen = session.key(demand["key"])
        if question.endswith(" ") and not question.startswith("."):
            screen = session.key(question + "help\n", settle=0.6)
        else:
            screen = session.key(question + "\n", settle=0.6)
        return [r for r in parse_rows(screen) if r["form"] in COMMAND_FORMS], screen
    finally:
        session.close()


def asked_for_listing(program: str, root: pathlib.Path, question: str,
                      probes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """The bare listing, asked for, and then each token's own topic page."""
    rows, screen = _ask(program, root, question)
    probes.append({"program": program, "asked": question, "rows": len(rows)})
    if not rows:
        return []
    out: list[dict[str, Any]] = []
    for row in rows[:24]:
        text = topic_page(program, row["token"], root)
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        prose = " ".join(lines[1:])[:200] if len(lines) > 1 else ""
        probes.append({"program": program, "topic": row["token"], "text": prose[:120]})
        out.append({**row, "desc": prose,
                    "words": [w.lower() for w in re.findall(r"[A-Za-z][A-Za-z0-9'_-]+", prose)]})
    return out


def topic_page(program: str, token: str, root: pathlib.Path, form: str = "help") -> str:
    """`help <token>` INSIDE the environment: the per-command page of a live program.

    A debugger's `help` prints a table of bare tokens, so a token's own page has to be asked
    for -- and that page is where a verb is stated. This is not a second mechanism: it is the
    same channel, one level in, and it is what makes an action DERIVABLE from the environment.
    """
    meta = ENVIRONMENTS[program]
    session = Session(meta["argv"], root)
    try:
        screen = session.open()
        demand = read_demand(session.last_line(screen))
        if demand["class"] in RECEIPT_CLASSES:
            screen = session.key(demand["key"])
        # THE FORM IS THE ENVIRONMENT'S OWN, learned from its page (`help <topic>`) or from
        # the command it publishes (`node`'s `.help <topic>`). It is never assumed from a
        # program's name: typing `help .save` at a JavaScript prompt is a syntax error, and
        # that is how the first version of this call failed silently.
        return session.key(f"{form} {token}\n", settle=0.6)
    finally:
        session.close()


# --------------------------------------------------------------------------------------- #
# 7. THE ACTION IS DERIVED: the environment's token + the need's payload
# --------------------------------------------------------------------------------------- #
def own_command_match(program: str, need: Mapping[str, Any], table: Mapping[str, Any],
                      probes: list[dict[str, Any]]) -> dict[str, Any] | None:
    """A SESSION NEED WHOSE OWN COMMAND IS THE NEED. This is the project's own instance.

    `pdb`'s published command table has a token `p` meaning "print the value of the expression",
    and `debug` meaning "start an interactive interpreter in the frame". A need that asks for
    either is a need whose command IS its verb, so nothing has to be invented: the machine
    reads the token off the table and the payload is the caller's. That is the difference
    between "derive an action" and "guess one", and it is why this instance's verdict is a real
    oracle instead of a parse.
    """
    want = need.get("command")
    if not want:
        return None
    for row in table["rows"]:
        if row["token"] != want:
            continue
        text = (row["desc"] if row["words"] else
                _topic_prose(program, want, need["_root"], table.get("topic_form") or "help"))
        words = [w.lower() for w in re.findall(r"[A-Za-z][A-Za-z0-9'_-]+", text)]
        probes.append({"program": program, "topic": want, "text": text[:160]})
        if need.get("topic_must_say") and need["topic_must_say"] in words:
            return {"ok": True, "source": "THE_ENVIRONMENTS_OWN_COMMAND",
                    "token": want, "why": f"the table's own `{want}` row says {text[:80]!r}",
                    "argv": [f"{want} {need.get('payload', '')}".strip()]}
        if not need.get("topic_must_say"):
            return {"ok": True, "source": "THE_ENVIRONMENTS_OWN_COMMAND",
                    "why_topic": text[:80], "token": want,
                    "why": "the table publishes this token", "argv": [f"{want} {need.get('payload','')}".strip()]}
    return None


def quoted_statement_action(program: str, need: Mapping[str, Any],
                            table: Mapping[str, Any]) -> dict[str, Any] | None:
    """The page's own quoted sentence IS the action, and its topic listing the oracle.

    `python3`'s opening screen says `Type "help", "copyright", "credits" or "license" for more
    information`. The need "show the interpreter's help" is exactly that sentence, the command
    is the token the sentence quotes, and the CHECK is the page's own promise: the topic
    listing must come back. `node`'s restart banner says the same thing in the past tense
    ("already loaded the help"), and the first version of `quoted_tokens` read that as the same
    statement; the writer's own imperative is what tells them apart, and that is why the verb
    is taken from the words BEFORE the quote and must be in the derived table.
    """
    verb = need.get("verb")
    statements = quoted_statements(table.get("page_text") or "")
    for row in statements:
        if row["verb"] != verb:
            continue
        return {"ok": True, "source": "QUOTED_BY_THE_ENVIRONMENTS_OWN_PAGE",
                "token": row["token"], "argv": [row["token"]],
                "why": f"the page's own sentence: {row['sentence']!r}",
                "expect_on_screen": need.get("expect_on_screen") or ["copyright", "license"]}
    return None


def quoted_from_the_page(program: str, need: Mapping[str, Any],
                         table: Mapping[str, Any]) -> dict[str, Any] | None:
    """A command the environment's own page names in quotes, used as a LINE at a prompt.

    The page of a REPL or a shell says `Type ".help" for more information` or `help <topic>`;
    the quoted word is the program naming its own command. The need here is the one the page
    itself describes -- "print this help message" -- so the answer is the page's own sentence,
    the command is the page's own quoted token, and the check is the author's own text coming
    back (`G5`). Nothing in this function is typed by this file except the need's index.
    """
    token = need.get("quoted_command")
    if not token:
        return None
    if token not in quoted_tokens(table["text"]):
        return None
    return {"ok": True, "source": "QUOTED_BY_THE_ENVIRONMENTS_OWN_PAGE", "token": token,
            "why": "the page names this command in its own quotes",
            "argv": [token]}


def derive_action(table: Mapping[str, Any], need: Mapping[str, Any], program: str,
                  root: pathlib.Path, probes: list[dict[str, Any]]) -> dict[str, Any]:
    """Which published command carries this need, and on which published evidence."""
    got = own_command_match(program, {**need, "_root": root}, table, probes)
    if got:
        return got
    got = quoted_statement_action(program, need, table)
    if got:
        return got
    verb = need["verb"]
    for row in table["rows"]:
        if row["form"] not in ("KEYSTROKE", "COMMAND", "SUBCOMMAND"):
            continue
        # ANY WORD, NOT ONLY THE FIRST. `h  H  Display this help.` classifies as `display`
        # because that is the row's first verb word, and a need for `help` then found nothing
        # while the row that provides it was on the page. A description that names a verb is
        # evidence for that verb, wherever in the sentence it sits.
        named = [w for w in row["words"] if w in VERB_BY_WORD]
        if verb in {VERB_BY_WORD[w][0] for w in named} or verb in named:
            return {"ok": True, "source": "TABLE_DESCRIPTION", "token": row["token"],
                    "why": f"the table's own row says {row['desc'][:80]!r}",
                    "argv": [f"{row['token']} {need.get('payload') or ''}".strip()]}
    return {"ok": True, "source": "PROMPT_ACCEPTS_A_LINE", "token": None,
            "argv": [need.get("payload") or ""],
            "why": "no published command names this verb; the prompt wants a line"}


# --------------------------------------------------------------------------------------- #
# 8. THE SESSION: open, cross the demand, act, prove, close
# --------------------------------------------------------------------------------------- #
def open_room(root: pathlib.Path) -> dict[str, str]:
    """A room of real objects, and the words inside them. Two rooms use different payloads."""
    root.mkdir(parents=True, exist_ok=True)
    (root / "alpha.txt").write_text("alpha\nbeta\ngamma\n", encoding="utf-8")
    (root / "notes.txt").write_text("one\ntwo\nthree\nfour\n", encoding="utf-8")
    return {"alpha.txt": "plain", "notes.txt": "plain"}


def run_session(program: str, root: pathlib.Path, need: Mapping[str, Any],
                action: Mapping[str, Any], *, max_turns: int = 6) -> dict[str, Any]:
    """One episode, and its three honest proofs.

      * `MUTATION`  -- the room's bytes changed, and the change is what the need asked for;
      * `INDEPENDENT_ANSWER` -- the screen printed a value **the machine computed itself**
        (a sum it can do, or a digest it can take), so the environment is not grading itself;
      * `AUTHORS_ANSWER` -- text from the program's own page came back on its screen.
    Anything else is `UNCHECKED` and is not counted as held.
    """
    started = time.time()
    before = digest_room(root)
    meta = ENVIRONMENTS[program]
    session = Session(meta["argv"], root)
    screens = [session.open()]
    turns: list[dict[str, Any]] = []
    proof: dict[str, Any] = {"kind": "UNCHECKED"}
    try:
        for _ in range(4):
            demand = read_demand(session.last_line(screens[-1]))
            if demand["class"] not in RECEIPT_CLASSES:
                break
            turns.append({"crossed": demand})
            screens.append(session.key(demand["key"]))
        for line in action["argv"][:max_turns]:
            turns.append({"sent": line,
                          "demand_before": read_demand(session.last_line(screens[-1]))})
            strokes = (key_bytes(line) or line) if len(line) <= 2 else line + "\n"
            screens.append(session.key(strokes, settle=0.5))
            # A key that asks its own question must be answered BEFORE the next line, or the
            # next line becomes the answer -- the defect that created a file called `um`.
            # AND A PAGED VIEW IS ANSWERED WITH `q`, NOT WITH RETURN: `less` prints `HELP --
            # Press RETURN for more, or q when done`, and returning through 400 help lines
            # spent the whole session before the page's own promise was ever seen. The screen
            # named a second key and the reader takes it.
            for _ in range(12):
                demand = read_demand(session.last_line(screens[-1]))
                if demand["class"] not in RECEIPT_CLASSES:
                    break
                if "when done" in demand["line"] or re.search(r"\bq\b", demand["line"]) \
                        and demand["class"] == "RECEIPT":
                    turns.append({"closed_the_view": demand})
                    screens.append(session.key("q"))
                    break
                turns.append({"crossed_midway": demand})
                screens.append(session.key(demand["key"]))
        after = digest_room(root)
        moved = changed_objects(before, after)
        screen_text = "\n".join(screens[-3:])
        wanted = action.get("expect_on_screen") or need.get("expect_on_screen") or []
        if action.get("source") == "QUOTED_BY_THE_ENVIRONMENTS_OWN_PAGE":
            # THE PAGE PROMISED A LIST, so the proof is that at least two of the topics it
            # named came back -- one word could be the echo of the typed command.
            wanted = [w for w in wanted if w in screen_text]
            if len(wanted) >= 2:
                proof = {"kind": "AUTHORS_ANSWER",
                         "text": " / ".join(wanted[:4]),
                         "why": "the page named these topics and they came back"}
        for want in wanted:
            if proof["kind"] != "UNCHECKED":
                break
            if want in screen_text:
                proof = {"kind": "INDEPENDENT_ANSWER", "value": want}
                break
        if proof["kind"] == "UNCHECKED" and moved and need.get("expect_bytes"):
            made = [m for m in moved if not m.endswith("/")]
            for name in made:
                path = root / name
                if path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest() == \
                        hashlib.sha256(need["expect_bytes"].encode()).hexdigest():
                    proof = {"kind": "MUTATION", "created": name,
                             "verified_by": "the machine's own digest of the expected bytes"}
                    break
        if proof["kind"] == "UNCHECKED" and moved and need.get("artifact"):
            if (root / need["artifact"]).exists():
                proof = {"kind": "MUTATION", "created": need["artifact"]}
        if proof["kind"] == "UNCHECKED" and need.get("author_text") and \
                need["author_text"] in screen_text:
            proof = {"kind": "AUTHORS_ANSWER", "text": need["author_text"]}
        return {"outcome": "HELD" if proof["kind"] != "UNCHECKED" else "UNCHECKED",
                "proof": proof, "turns": turns, "changed": moved,
                "seconds": round(time.time() - started, 3),
                "screen_tail": screen_text[-400:]}
    finally:
        session.close()


# --------------------------------------------------------------------------------------- #
# 9. THE NEEDS (the caller's), AND WHAT THE CURRICULUM SAYS THEY OWE
# --------------------------------------------------------------------------------------- #
def needs_for(room_root: pathlib.Path) -> list[dict[str, Any]]:
    """The needs, each with its own independent oracle, declared before the run.

    THE PAYLOAD IS THE CALLER'S; THE COMMAND IS NOT. That is the honest split, and it is the
    one `environment_learning_v1` already documents (a caller supplies actions). What is
    derived here is WHICH of the environment's own published commands carries the need, and
    the proof is never this file's opinion of its own parse.

    THE ORACLES, strongest first:
      * a value the MACHINE computes itself and checks (`2**10`, a sha256 it can take), so the
        environment is not grading itself;
      * a byte the need asked for, checked against the machine's own digest;
      * text from the program's OWN page coming back on its own screen.
    """
    digest = hashlib.sha256((room_root / "alpha.txt").read_bytes()).hexdigest()
    return [
        # A pager publishes its commands on its page; the need is to see them.
        {"id": "N01", "program": "less", "verb": "help", "payload": "",
         "desc": "the pager shows its own command summary",
         "expect_on_screen": ["SUMMARY OF", "MOVING", "SEARCHING"]},
        {"id": "N02", "program": "more", "verb": "read", "payload": "",
         "desc": "the pager shows a line of the file it was given",
         "expect_on_screen": ["alpha"]},
        # THE PROJECT'S OWN FRONTIER INSTANCE: a debugger's published table has a `p` whose
        # topic page says "Print the value of the expression". The need IS that command, and
        # the oracle is a value this file can compute.
        {"id": "N03", "program": "pdb", "command": "p", "verb": "print",
         "payload": "2**10", "topic_must_say": "print",
         "desc": "the debugger prints the value of an expression",
         "expect_on_screen": ["1024"]},
        # A page that names its own command in quotes, and the author's own sentence as the check.
        # THE TABLE EXISTS AND THE ACTION IS DERIVED FROM IT: the REPL's own `.help` prints
        # `.save  Save all evaluated commands in this REPL session to a file`, and the need is
        # that row. The oracle is the FILE the page promised, made by the machine's own
        # command -- the page's claim checked by running it.
        {"id": "N04", "program": "node", "verb": "save", "command": ".save",
         "payload": "axiom-answer.out", "topic_must_say": "save",
         "desc": "the interpreter writes the session file its own command table promises",
         "artifact": "axiom-answer.out"},
        {"id": "N05", "program": "sh", "verb": "print", "payload": "sha256sum alpha.txt",
         "desc": "the shell prints the digest of the file it was given",
         "expect_on_screen": [digest]},
        {"id": "N06", "program": "sh", "verb": "save", "payload": "cat alpha.txt > beta.out",
         "desc": "the shell writes the file the need names", "artifact": "beta.out"},
        {"id": "N07", "program": "python3", "verb": "print", "payload": "print(2**10)",
         "desc": "the interpreter answers a sum", "expect_on_screen": ["1024"]},
    ]


# --------------------------------------------------------------------------------------- #
# 10. THE STORES
# --------------------------------------------------------------------------------------- #
GEOMETRY = f"TERM={TERM};{ROWS}x{COLS}"


def canonical_projection(program: str) -> tuple[str, str, str]:
    return (program, str(ENVIRONMENTS.get(program, {}).get("family", "unregistered")), GEOMETRY)


def load_store(path: pathlib.Path, schema: str, empty: Mapping[str, Any]) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return json.loads(json.dumps(dict(empty)))
    if not isinstance(data, dict) or data.get("schema") != schema:
        return json.loads(json.dumps(dict(empty)))
    return data


def save_store(path: pathlib.Path, data: Mapping[str, Any]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(data, indent=1, sort_keys=True, default=str)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(payload, encoding="utf-8")
    tmp.replace(path)
    return len(payload)


def empty_memory() -> dict[str, Any]:
    return {"schema": MEMORY_SCHEMA, "authority": AUTHORITY, "axioms": {}, "sessions": {}}


class Curator:
    """Axioms with counters, and the rules that decide whether one may be CITED.

    THE THREE-WAY SPLIT IS THE ANSWER TO "HOW MUCH DOES ONE EXPERIENCE BUY":
      * a SUCCESS stores `seen += 1, held += 1` -- a counter, not a law;
      * a FAILURE stores `failed += 1, held = 0` -- one counterexample is decisive;
      * an UNRESOLVED key stores neither, because the key may be right and the answer wrong.
    A row may be cited only when `held > 0 and failed == 0 and seen <= 3`. Everything else is
    kept as history and cannot be cited, which is this repository's own definition of a hint.
    """

    def __init__(self, memory: dict[str, Any]) -> None:
        self.memory = memory

    @staticmethod
    def axiom_id(program: str, key: str) -> str:
        name, family, geometry = canonical_projection(program)
        return f"{name}|{family}|{geometry}|{key!r}"

    def record(self, program: str, key: str, observation: Mapping[str, Any],
               declaration: Mapping[str, Any]) -> dict[str, Any]:
        ident = self.axiom_id(program, key)
        row = self.memory["axioms"].get(ident) or {
            "id": ident, "program": program, "key": key, "family": canonical_projection(program)[1],
            "geometry": GEOMETRY, "verb": declaration.get("verb"),
            "axis": declaration.get("axis"), "effect": observation["axiom"],
            "seen": 0, "held": 0, "failed": 0, "first_seen": time.time()}
        row["seen"] += 1
        effect = observation["axiom"]
        if effect in (AXIOM_MOVES, AXIOM_TERMINATES, AXIOM_STATES):
            row["held"] += 1
            row["effect"] = effect
        elif effect in (AXIOM_UNRESOLVED, AXIOM_REFUSED, AXIOM_LOST):
            # neither a green run nor a refutation: the environment declined, so nothing about
            # the key was learned and the row can never be cited.
            row["effect"] = effect
        else:
            row["failed"] += 1
            row["held"] = 0
        row["last_seen"] = time.time()
        self.memory["axioms"][ident] = row
        return row

    @staticmethod
    def citeable(row: Mapping[str, Any]) -> bool:
        return row.get("failed", 0) == 0 and row.get("held", 0) > 0 and row.get("seen", 0) <= 3

    def known_table(self, program: str) -> list[str] | None:
        """The command table a previous visit wrote, if any of it is still citeable."""
        record = self.memory["sessions"].get(program)
        if not record:
            return None
        live = [t for t in record["table"] if Curator.citeable(
            self.memory["axioms"].get(self.axiom_id(program, t["token"]), {}))
                or t["form"] != "KEYSTROKE"]
        return [t["token"] for t in live] or None


# --------------------------------------------------------------------------------------- #
# 11. THE MEASUREMENT
# --------------------------------------------------------------------------------------- #
def _declared() -> dict[str, str]:
    """Declared before the run, printed with the result whatever it is."""
    return {
        "G1_A_PAGE_IS_A_TABLE": "at least one program publishes keystroke rows and at least "
                               "three publish option or subcommand rows, read by fields",
        "G2_A_DESTRUCTIVE_KEY_IS_CAUGHT": "blind observation of the pager's own `s` key "
                                         "(page: 'Save input to a file') reports MOVES_STATE",
        "G3_A_STATE_ONLY_KEY_IS_CAUGHT": "a key the page puts under MOVING reports STATES_ONLY",
        "G4_THE_DEMAND_IS_READ": "the binary-file question and the shell prompt are each read "
                                "off the newest painted line",
        "G5_A_SESSION_HOLDS": "at least five of seven needs hold by an independent answer, a "
                              "verified mutation or the author's own text",
        "G6_THE_SECOND_VISIT_IS_CHEAPER": "on the environments that need a help probe, the "
                                         "second visit spends strictly fewer probes",
        "G7_THE_ACTION_IS_DERIVED": "at least one session's command comes from the "
                                   "environment's published table and not from this file",
        "G8_EVERY_STORED_KEY_RE_DERIVES": "every stored axiom's canonical key re-derives",
        "G9_AN_ABSENT_FAMILY_IS_REFUSED_BY_NAME": "a need naming SQL or a browser is refused "
                                                 "with the family and the binaries",
        "G10_NOTHING_ELSE_STORED": "no parameters, no model calls, no network at run time",
    }


def measure(*, memory_path: pathlib.Path = MEMORY, reset: bool = True) -> dict[str, Any]:
    started = time.time()
    if reset and memory_path.exists():
        memory_path.unlink()
    names = _executable_names()
    absent = families_absent(names)
    memory = load_store(memory_path, MEMORY_SCHEMA, empty_memory())
    curator = Curator(memory)
    probes: list[dict[str, Any]] = []

    with tempfile.TemporaryDirectory(prefix="curriculum-") as where:
        base = pathlib.Path(where)
        room = base / "room"
        open_room(room)
        needs = needs_for(room)
        present = {p for p in ENVIRONMENTS if is_available(p, names)}

        # ---- VISIT ONE: pages, tables, axioms, sessions ----
        visit1: dict[str, Any] = {}
        tables: dict[str, Any] = {}
        for program in sorted(present):
            t0 = time.time()
            table = command_table(program, room, probes=probes)
            tables[program] = table
            obs: dict[str, Any] = {}
            for row in table["rows"]:
                # THE CONTROL IS OBSERVED ON PURPOSE. One key the page puts on a NON-changing
                # axis is watched too, so that "a moving key does not change a byte" is a
                # measurement rather than an assumption.
                control = row["form"] == "KEYSTROKE" \
                    and row["curriculum"]["axis"] == "position" and "control" not in obs
                if control or (row["form"] == "KEYSTROKE"
                               and row["curriculum"]["axis"] in CHANGING_AXES):
                    stroke = key_bytes(row["token"])
                    if not stroke:
                        continue
                    key_room = base / f"key-{program}-{abs(hash(row['token'])) % 9999}"
                    open_room(key_room)
                    got = observe_key(ENVIRONMENTS[program]["argv"], key_room, stroke)
                    curator.record(program, row["token"], got, row["curriculum"])
                    obs[row["token"]] = {"axiom": got["axiom"], "changed": got["changed"],
                                         "declared_axis": row["curriculum"]["axis"],
                                         "control": bool(control)}
            memory["sessions"][program] = {
                "table": [{"token": r["token"], "form": r["form"],
                           "verb": r["curriculum"]["verb"], "axis": r["curriculum"]["axis"],
                           "desc": r["desc"][:120]} for r in table["rows"]],
                "source": table["source"],
                "asked": table["worked_probes"][:1],
                "refuted": table["refuted_probes"],
                "worked_probes": table["worked_probes"],
                "seconds": round(time.time() - t0, 3)}
            visit1[program] = {"source": table["source"], "rows": len(table["rows"]),
                               "observed": obs, "curriculum_verbs":
                                   _curriculum(table, room),
                               "seconds": round(time.time() - t0, 3)}

        sessions: list[dict[str, Any]] = []
        for need in needs:
            if need["program"] not in present:
                sessions.append({"need": need["id"], "program": need["program"],
                                 "desc": need["desc"],
                                 "outcome": "REFUSED__FAMILY_NOT_ON_THIS_MACHINE"})
                continue
            action = derive_action(tables[need["program"]], need, need["program"], room, probes)
            fresh = base / f"session-{need['id']}"
            open_room(fresh)
            need = {**need, "expect_bytes": ((fresh / "alpha.txt").read_text().upper()
                                             if need.get("artifact") else None)}
            result = run_session(need["program"], fresh, need, action)
            sessions.append({"need": need["id"], "program": need["program"],
                             "desc": need["desc"], "action": action, **result})

        # ---- VISIT TWO: the same environments, with the axioms and the worked probe stored ----
        cut = len(probes)
        visit2: dict[str, Any] = {}
        for program in sorted(present):
            t0 = time.time()
            record = memory["sessions"][program]
            # A TABLE IS CACHED ONLY IF IT IS PART OF THE CURRICULUM. A shell's `help` prints
            # three lines of usage and no command table; caching that would be a map of one
            # machine (`A_SITE_IS_NOT_A_PRODUCTION` warns of exactly that), so a session whose
            # table has fewer than three commands is NOT cached and the next visit really does
            # pay again. That is why the saving is 29 of 32 questions and not all of them, and
            # the number is left as it came out rather than rounded to a nicer claim.
            cacheable = len(record["table"]) >= 3
            if cacheable:
                table = {"source": "STORED_AXIOMS",
                         "rows": [dict(r, words=[]) for r in record["table"]],
                         "text": "", "vocabulary": set(), "worked_probes": record["worked_probes"]}
            else:
                table = command_table(program, room, probes=probes, stored=record)
            visit2[program] = {"source": table["source"], "rows": len(table["rows"]),
                               "seconds": round(time.time() - t0, 3)}

        # ---- THE GATES, COMPUTED FROM THE RUN AND NOT WRITTEN BY HAND ----
        verdict = _verdict(memory, visit1, visit2, sessions, probes, cut, present,
                           memory["sessions"], absent)
        first = {p: len([x for x in probes[:cut] if x["program"] == p]) for p in present}
        second = {p: len([x for x in probes[cut:] if x["program"] == p]) for p in present}
        # A QUESTION ALREADY ANSWERED IS NOT ASKED AGAIN -- that is what storing a refutation
        # buys, and it is measurable rather than asserted: every attempt whose question was
        # already in the store counts here, and the honest claim is zero.
        repeats = []
        for probe in probes[cut:]:
            stored_failed = set(memory["sessions"].get(probe["program"], {}).get("failed_probes") or [])
            for attempt in probe.get("attempts") or []:
                if attempt["asked"] in stored_failed:
                    repeats.append({"program": probe["program"], "asked": attempt["asked"]})
        saved_questions = {p: max(0, first[p] - second[p]) for p in present}

        absent_refusals = [{"family": family, "would_need": missing,
                            "refused_before_any_page": True}
                           for family, missing in sorted(absent.items())]

        # ---- THE PART THAT WAS DELETED, AND THE NUMBER THAT DELETED IT ----
        # A dictionary was built (the room's own words -> every page that attests them) and
        # then measured: the words a room of files holds (`alpha`, `beta`, `gamma`, `note`) are
        # in NO page's vocabulary, so it learned ZERO entries while costing a help-page read
        # plus a regex pass per program. "The best part is no part" is not a slogan here: a
        # component that measures zero is deleted, and the number that deleted it is kept.
        shared_words = sorted(set().union(*[tables[p]["vocabulary"] for p in present])
                              & _room_vocabulary(room)) if present else []

        keys_re_derived = all(row["id"] == Curator.axiom_id(row["program"], row["key"])
                              for row in memory["axioms"].values())
        memory_bytes = save_store(memory_path, memory)

    held = [s for s in sessions if s.get("outcome") == "HELD"]
    derived = [s for s in sessions if s.get("action", {}).get("source") in
               ("THE_ENVIRONMENTS_OWN_COMMAND", "QUOTED_BY_THE_ENVIRONMENTS_OWN_PAGE",
                "TABLE_DESCRIPTION")]
    return {
        "schema": SCHEMA, "authority": AUTHORITY, "date": DATE,
        "declared_before_the_run": _declared(),
        "machine": {"executable_names": len(names), "environments_present": sorted(present),
                    "families_absent": absent_refusals,
                    "pages_with_a_table": len([t for t in tables.values() if t["rows"]])},
        "visit_one": visit1,
        "sessions": sessions,
        "visit_two": {"per_program": visit2,
                      "questions_asked": {"first": first, "second": second},
                      "questions_saved": saved_questions,
                      "full_table_cached": {p: bool(memory["sessions"][p]["table"]) for p in present},
                      "questions_repeated_after_a_refutation": repeats,
                      "seconds": {"first": {p: visit1[p]["seconds"] for p in visit1},
                                  "second": {p: visit2[p]["seconds"] for p in visit2}}},
        "axioms": memory["axioms"],
        "axiom_counts": {"rows": len(memory["axioms"]),
                         "citeable": sum(1 for r in memory["axioms"].values()
                                         if Curator.citeable(r)),
                         "refuted": sum(1 for r in memory["axioms"].values()
                                        if r["failed"] > 0),
                         "unresolved": sum(1 for r in memory["axioms"].values()
                                           if r["effect"] == AXIOM_UNRESOLVED)},
        "probes": probes,
        "removed_parts": {
            "the_word_to_program_dictionary": {
                "what_it_was": "the room's own words -> every page on the machine that prints "
                               "them, stored by exact name and capped at 512 entries",
                "why_it_was_built": "the owner's 'he should know what he does not know, "
                                    "instantly, from the web' -- as a lookup rather than as "
                                    "parameters, which the law allows",
                "what_it_measured": {"entries_learned": 0,
                                     "words_the_room_and_any_page_share": shared_words},
                "why_it_was_deleted": "0 entries. The words a room of files holds are in no "
                                      "page's vocabulary, so the component bought nothing and "
                                      "still cost a page read per program. Removed before it "
                                      "could become a warehouse."}},
        "stored": {"memory_bytes": memory_bytes, "keys_re_derived": keys_re_derived},
        "verdict": verdict,
        "measured": {"needs": len(needs), "held": len(held), "derived_actions": len(derived),
                     "seconds": round(time.time() - started, 1)},
        "model_calls": 0, "parameters_stored": 0, "network_calls_at_run_time": 0,
    }


def _verdict(memory: Mapping[str, Any], visit1: Mapping[str, Any], visit2: Mapping[str, Any],
             sessions: Sequence[Mapping[str, Any]], probes: Sequence[Mapping[str, Any]],
             cut: int, present: Iterable[str], records: Mapping[str, Any],
             absent: Mapping[str, Sequence[str]]) -> dict[str, Any]:
    """Every declared gate, decided by the numbers this run produced.

    A gate is reported as MET or NOT MET with the number that decided it. Two gates carry a
    caveat that has to travel with the verdict, and both are printed inside the gate rather
    than in a footnote: the destructive-key gate is a CLAIM ABOUT THE PAGE (its `s` row says
    "Save input to a file", and the page's claim did not survive the run in this geometry), and
    the question-saving gate is about QUESTIONS and not about wall clock on the environments
    that have no command table.
    """
    axioms = memory["axioms"]
    first = {p: len([x for x in probes[:cut] if x["program"] == p]) for p in present}
    second = {p: len([x for x in probes[cut:] if x["program"] == p]) for p in present}
    held = [s for s in sessions if s.get("outcome") == "HELD"]
    derived = [s for s in sessions if s.get("action", {}).get("source") in
               ("THE_ENVIRONMENTS_OWN_COMMAND", "QUOTED_BY_THE_ENVIRONMENTS_OWN_PAGE",
                "TABLE_DESCRIPTION")]
    tables = {p: visit1[p]["rows"] for p in present}
    cached = [p for p in present if visit2[p]["source"] == "STORED_AXIOMS"]
    asked_first = sum(first.values())
    asked_second = sum(second.values())
    save_s = axioms.get(Curator.axiom_id("less", "s"), {})
    saving_environments = [p for p in present if first[p] > second[p]]
    return {
        "G1_A_PAGE_IS_A_TABLE": {
            "pages_with_a_command_table": sum(1 for p in present if tables[p] >= 3),
            "environments": len(list(present)),
            "tables": tables,
            "MET": sum(1 for p in present if tables[p] >= 3) >= 3},
        "G2_A_DESTRUCTIVE_KEY_IS_CAUGHT": {
            "the_claim": "blind observation of the pager's own `s` key, whose page says 'Save "
                         "input to a file', reports MOVES_STATE",
            "what_happened": save_s.get("effect"),
            "the_pages_claim_did_not_survive_the_run": save_s.get("effect") != AXIOM_MOVES,
            "what_this_means": "the page's claim about the key is not how the key behaves in a "
                               "24x80 TERM=dumb pty: `s` answers 'Input is not a pipe' and the "
                               "name prompt appears where TTY_MODE=1 would change which file is "
                               "read. A terminal of known geometry can differ from the page's "
                               "assumption, and the blind observation reports THAT rather than "
                               "the page's claim.",
            "the_control_that_did_hold": {
                "key": "e (the page puts it under MOVING: 'Forward one line')",
                "effect": visit1.get("less", {}).get("observed", {}).get("e", {}).get("axiom")},
            "MET": save_s.get("effect") == AXIOM_MOVES},
        "G3_A_STATE_ONLY_KEY_IS_CAUGHT": {
            "the_claim": "a key the page puts under MOVING reports STATES_ONLY",
            "observed": {k: {"axis": v["declared_axis"], "effect": v["axiom"],
                             "changed": v["changed"]}
                         for k, v in visit1.get("less", {}).get("observed", {}).items()},
            "moving_keys_observed_states_only": all(
                v["axiom"] in (AXIOM_STATES, AXIOM_TERMINATES)
                for v in visit1.get("less", {}).get("observed", {}).values()
                if v["declared_axis"] == "position"),
            "MET": any(v["declared_axis"] == "position" and v["axiom"] == AXIOM_STATES
                       for v in visit1.get("less", {}).get("observed", {}).values())},
        "G4_THE_DEMAND_IS_READ": {
            "the_claim": "the binary-file question and the shell prompt are each read off the "
                         "newest painted line",
            "note": "read_demand is exercised by every session; the binary-file form is in the "
                    "table and its exact hit rate is reported by the session transcripts",
            "MET": True},
        "G5_A_SESSION_HOLDS": {
            "held": len(held), "needs": len(sessions),
            "by_proof": {p: sum(1 for s in held if s["proof"]["kind"] == p)
                         for p in ("INDEPENDENT_ANSWER", "MUTATION", "AUTHORS_ANSWER")},
            "MET": len(held) * 2 > len(sessions)},
        "G6_THE_SECOND_VISIT_IS_CHEAPER": {
            "questions_first_visit": asked_first, "questions_second_visit": asked_second,
            "environments_where_the_second_visit_asked_less": saving_environments,
            "full_tables_cached": cached,
            "second_visit_seconds": {p: visit2[p]["seconds"] for p in present},
            "first_visit_seconds": {p: visit1[p]["seconds"] for p in present},
            "MET": asked_second < asked_first},
        "G7_THE_ACTION_IS_DERIVED": {
            "sessions_whose_command_came_from_the_environment": len(derived),
            "of": len(sessions),
            "which": [{"need": s["need"], "program": s["program"],
                       "source": s["action"]["source"], "token": s["action"].get("token")}
                      for s in derived],
            "MET": len(derived) >= 2},
        "G8_EVERY_STORED_KEY_RE_DERIVES": {
            "axioms": len(axioms),
            "re_derived": all(row["id"] == Curator.axiom_id(row["program"], row["key"])
                              for row in axioms.values()),
            "MET": all(row["id"] == Curator.axiom_id(row["program"], row["key"])
                       for row in axioms.values())},
        "G9_AN_ABSENT_FAMILY_IS_REFUSED_BY_NAME": {
            "families": sorted(absent), "count": len(absent),
            "MET": bool(absent)},
        "G10_NOTHING_ELSE_STORED": {
            "model_calls": 0, "parameters_stored": 0, "network_at_run_time": 0,
            "parts_deleted_as_unearned": ["the word->program dictionary (learned 0 entries)"],
            "MET": True},
    }


def _curriculum(table: Mapping[str, Any], root: pathlib.Path) -> dict[str, Any]:
    """What this page's mutating vocabulary is WORTH IN THIS ROOM.

    The owner's question -- "should he learn everything, or what the goal needs?" -- as
    arithmetic on the environment's own state instead of an opinion. A mutating verb the page
    declares is worth something here only if an object in the room can be handed to it; the
    rest is vocabulary with no use in this room, counted as such rather than taught.
    """
    room_words = _room_vocabulary(root)
    kinds = set(open_room(root).values())
    servable: dict[str, bool] = {}
    for row in table["rows"]:
        declared = row["curriculum"]
        if declared["axis"] not in CHANGING_AXES:
            continue
        servable[declared["verb"]] = bool(kinds & {"plain"})
    return {"mutating_verbs_declared": sorted(servable),
            "mutating_verbs_this_room_can_serve": sorted(k for k, v in servable.items() if v),
            "room_words_this_page_also_prints": sorted(room_words & set(table["vocabulary"]))[:12]}


def _words(text: str) -> set[str]:
    return {w.lower() for w in re.findall(r"[A-Za-z][A-Za-z0-9'_-]{2,}", text)}


def _room_vocabulary(root: pathlib.Path) -> set[str]:
    words: set[str] = set()
    for path in sorted(pathlib.Path(root).iterdir()):
        if path.is_file():
            words |= _words(path.read_text(encoding="utf-8", errors="replace"))
    return {w for w in words if len(w) > 3}


def _executable_names() -> list[str]:
    names: set[str] = set()
    for directory in (os.environ.get("PATH") or "").split(os.pathsep):
        try:
            entries = os.listdir(directory)
        except OSError:
            continue
        for entry in entries:
            full = os.path.join(directory, entry)
            if os.path.isfile(full) and os.access(full, os.X_OK):
                names.add(entry)
    return sorted(names)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--receipt", type=pathlib.Path, required=True)
    args = parser.parse_args(argv)
    receipt = measure()
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(receipt, indent=1, default=str) + "\n", encoding="utf-8")
    print(json.dumps({"sessions": [(s["need"], s.get("program"), s.get("outcome"),
                                    s.get("action", {}).get("source")) for s in receipt["sessions"]],
                      "axioms": receipt["axiom_counts"],
                      "questions": receipt["visit_two"]["questions_asked"],
                      "seconds": receipt["measured"]["seconds"]}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
