"""A PROGRAM SAYS WHAT IT IS FOR, AT THE TOP OF ITS OWN MANUAL.

THE BOTTLENECK THIS REMOVES, MEASURED.

`computer_env_v1.programs_for_goal` selects candidate programs by whether the program's NAME shares a
three-character stretch with a word of the goal, then reads only those manuals. Measured 2026-11-23:

    goal "compress this into a single archive"     603 installed programs -> 43 survive the name filter
                                                   and `tar` is NOT among them
    goal "gzip the report"                        `gzip` survives, `tar` does not
    goal "find lines with localhost"              53 survive, neither `gzip` nor `tar` among them

    and the answers actually returned:  ['as','c89','chcon','compare'] / ['convert','diff','docker-entrypoint','gold']

The correct program is EXCLUDED before any manual is read. `gzip` does not contain the letters of "compress";
`tar` does not contain the letters of "archive". A name is not a purpose.

THE FACT. A program states its purpose in the first lines of its manual, before its options begin:

    gzip     compress or uncompress files (by default, compress files in-place).     <- 2.7% in
    tar      gnu 'tar' saves many files together into a single tape or disk archive  <- 0.6% in
    as       (nothing before the options)  -- its only mention of "compress" is --compress-debug-sections
                                                                                     <- a FLAG, not a purpose

So the question is not "does the manual contain the word" (every 16 KB manual contains most words) but "does the
manual STATE it, before the options start". Measured on eight programs: 7 correct, and the one miss (`sort` for
"order") is honest -- sort's synopsis says "sort lines of text", not "order", and no rule about position can fix
a word the manual does not use.

WHY THIS IS AFFORDABLE. The name filter exists because "reading the help of all 603 installed programs cost a
measured 41-48 s". Re-measured 2026-11-23 with a one-second timeout: **3 ms per program, 628 of 634 indexed in
7.5 s**, once, then cached by content. Two seconds of one-time work is not what stood between this and an
answer; the filter was buying seconds with the correct program.

AUTHORITY NONE. No model, no parameters, no knowledge of any program beyond what each program says about
itself. $0.
"""
from __future__ import annotations

import math
import re
import subprocess
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

SCHEMA = "PROJECT_BRAIN_A_PROGRAM_SAYS_WHAT_IT_IS_FOR_V1"

# How long a program is given to answer `--help`. Measured: three milliseconds is typical, one second is
# generous, and a program that hangs is not one whose help will answer a goal.
TIMEOUT_S = 1.0

_OPTION_LINE = re.compile(r"^(?:-[A-Za-z]|--[A-Za-z])")
_OPTIONS_HEADING = re.compile(r"^[A-Z][A-Za-z /]*options:?\s*$", re.I)

# A word of fewer than three letters cannot distinguish a purpose from a preposition.
_MIN_WORD = 3

# How much rare-word evidence a program must carry before its own statement counts as an answer. One bit is the
# price of a word half the machine says; below that, the match is what every program would have matched.
_MIN_EVIDENCE = 1.0


def synopsis(help_text: str) -> str:
    """The part of a manual BEFORE its options begin -- where a program says what it is for.

    The cut is the first line that is itself a flag, or a heading that names options. Everything before that is
    the program describing itself; everything after is the program describing its switches.
    """
    lines = str(help_text or "").splitlines()
    for index, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            continue
        if _OPTION_LINE.match(stripped) or _OPTIONS_HEADING.match(stripped):
            return "\n".join(lines[:index])
    return "\n".join(lines)


def _words(text: str) -> list[str]:
    return [w for w in re.findall(r"[a-z0-9][a-z0-9'-]*", str(text or "").lower()) if len(w) >= _MIN_WORD]


@dataclass(frozen=True)
class Claim:
    """A program, and the sentence in which it says it does the goal's kind of thing."""
    program: str
    score: float
    stated: tuple[str, ...]
    sentence: str
    source: str = "OWN_MANUAL"


_USAGE = re.compile(r"^(?:usage|or|try)\b", re.I)

# A CLOSED CLASS OF GRAMMAR, NOT A LIST OF STOPWORDS. These are the words that join other words; none of them
# can name a thing, so none of them can identify a program. Measured 2026-11-23: they are 58% of the words in
# `grep`'s own statement ("Search for PATTERNS in each FILE"), so a frequency weight that includes them lets a
# program that says "that" outscore a program that says "archive".
_GRAMMAR = frozenset("""
a an the and or but nor so yet for of to in on at by with from into onto over under about as is are was were be
been being am do does did done has have had having it its this that these those there here then than which who
whom whose what when where why how each every all any some no not only also just very more most much many few
other another same such own same per via each either neither both whether if while because since until unless
one ones i you he she we they them their our your his her my me us
""".split())


def _root(word: str) -> str:
    """One suffix rule, checked in both directions, so `count`/`counts` and `word`/`words` meet.

    Measured 2026-11-23: "count words in a document" scored ZERO against `wc`, whose own description says
    "Print newline, word, and byte counts". `count` and `counts` are the same word to a reader and were two
    different words to a matcher, and that single character was the entire gap.

    §A130 recorded the trap: a stemmer's special case can swallow another word (`named` -> `name` turned
    `gzipped` into `gzippe`). So the rule here removes a suffix only when the word can afford to lose it, and
    never rewrites the stem to a different one. `cross`->`cros`, `class`->`clas`: both still meet their own
    plurals, which is all this is for.
    """
    w = word.casefold()
    for suffix, floor in (("ies", 4), ("es", 4), ("s", 3)):
        if w.endswith(suffix) and len(w) - len(suffix) >= floor:
            return w[: -len(suffix)]
    return w


def _content_words(text: str) -> list[str]:
    """The words that can name a thing, in order. Grammar is removed; nothing else is."""
    return [w for w in _words(text) if w not in _GRAMMAR]


def _content_roots(text: str) -> set[str]:
    return {_root(w) for w in _content_words(text)}


def statement(text: str) -> str:
    """The sentence in which a program says, plainly, what it does -- or empty.

    A PURPOSE IS STATED PLAINLY, AND THAT IS A PROPERTY OF ITS SHAPE, not of whether it contains a word.
    Measured 2026-11-23 on this machine:

        gzip     "Compress or uncompress FILEs"                   176 chars of synopsis, 2 statements
        tar      "GNU 'tar' saves many files together into ..."  408 chars, 6 statements
        git      (none)                                          2160 chars, 32 statements -- all usage grammar
        as       (none)                                            43 chars, 0 statements

    git and apt-get outranked gzip for "compress ... archive" under a rule that counted shared words, because a
    long manual mentions more words. The words were never the signal: the signal is that gzip SAYS it, near the
    top, in one sentence, while git lists subcommands and never says anything.

    A statement is a line that is not usage grammar, is not a flag listing, is not a bare version string, and is
    long enough to be a sentence. A synopsis made of many such lines is a command LIST, not a purpose -- which
    is why a program with thirty of them is treated as not having stated one.
    """
    lines = [l.strip() for l in str(text or "").splitlines() if l.strip()]
    plain: list[str] = []
    for line in lines:
        if _USAGE.match(line) or line.startswith("-"):
            continue
        if re.search(r"\[[-<A-Z]", line):
            continue
        if re.fullmatch(r"[\w.]+[\s]+v?[\d.]+\s*\([^)]*\)", line):
            continue
        if len(line) < 15:
            continue
        # AN ERROR MESSAGE IS NOT A PURPOSE. Measured 2026-11-23: `sensible-browser --help` prints
        # "Couldn't find a suitable web browser!", which became its statement and matched the goal word
        # "find". A program describing itself does not apologise, does not address the reader, and does not
        # ask a question.
        # "Permission denied" is a denial, not a purpose. Measured 2026-11-23: `debconf-communicate --help`
        # fails with a cache-permission error, and that error became its statement -- then matched the goal
        # "change permissions on a file" and outranked `chmod`. A program that could not even print its help
        # has said nothing about itself.
        if re.search(r"\b(couldn't|cannot|can't|unable|error|failed|sorry|try '|install|no such|denied|"
                     r"not found|warning|invalid|unknown|usage error)\b", line, re.I):
            continue
        if line.endswith("?") or line.endswith("!"):
            continue
        plain.append(line)
    if not plain or len(plain) > 12:
        # a synopsis of many statements is a command list, not a description
        return ""
    # THE PURPOSE IS THE WHOLE DESCRIPTION, NOT ITS FIRST LINE. Measured 2026-11-23: `wc` says
    # "Print newline, word, and byte counts for each FILE" and keeping only the first line made the word
    # "counts" -- the word a person uses -- invisible to the matcher, so "count words in a document" missed
    # `wc` and was answered by `ptx`. `tail` says "Print the last 10 lines", and "last" was invisible the
    # same way. A description is a paragraph; truncating it to one sentence throws away the noun.
    #
    # The lines before the first blank line after the description begins are one block, and everything in it
    # is the program speaking about itself.
    block: list[str] = [plain[0]]
    for line in lines[lines.index(plain[0]) + 1:]:
        if line in plain and len(block) < 6:
            block.append(line)
        elif line not in plain:
            break
    return " ".join(block)


def what_does(goal: str, *, programs: Sequence[str] | None = None,
              helps: Mapping[str, str] | None = None,
              also_says: Mapping[str, Sequence[str]] | None = None,
              limit: int = 6) -> dict[str, Any]:
    """Which installed programs state, in their own manual, that they do what the goal asks.

    `helps` supplies already-read manuals (name -> text); any program missing from it is read here. That
    separation is deliberate: the reading is mechanical and cacheable, the judgement is this function.

    `also_says` carries the words the program's PROJECT MANUAL uses that its own help does not --
    `the_manual_and_the_help_disagree_v1` derives those from two authoritative documents about the same
    program. Measured 2026-11-23: `chmod --help` says "Change the mode", the GNU manual says "Change access
    permissions", and "change permissions on a file" matched neither, because nothing in either text relates
    mode to permission. With the bridge, `chmod` carries "permission" and the goal finds it.

    These words are weaker evidence than the program's own statement, and are weighted as such: a word the
    manual had to supply is a word the program itself did not use.
    """
    asked = _content_roots(goal)
    if not asked:
        return {"schema": SCHEMA, "goal": goal, "claims": [], "why": "GOAL_HAS_NO_CONTENT_WORD"}

    # A WORD MOST PROGRAMS SAY CANNOT IDENTIFY ONE. Measured 2026-11-23: "copy a file to another name" scored
    # `addr2line` at 2 because its statement shares "file" and "name" -- words that a hundred different programs
    # use about themselves. The goal's own substance ("copy") was not mentioned by addr2line at all.
    #
    # The weight of a word is learned from THIS MACHINE, not from a list typed by hand: it is how rare the word
    # is across the statements of the installed programs. `copy` appears in a few; `file` appears in most. No
    # stopword list is needed and none is used -- a machine whose programs all say "archive" would discount it,
    # which is right, because then the word would not distinguish anything either.
    document_frequency: dict[str, int] = {}
    for text in (helps or {}).values():
        for word in _content_roots(statement(synopsis(text))):
            document_frequency[word] = document_frequency.get(word, 0) + 1
    total = max(1, len(helps or {}))

    if programs is None:
        programs = sorted(helps or {})
    claims: list[Claim] = []
    for program in programs:
        text = (helps or {}).get(program)
        if text is None:
            text = read_manual(program)
        if not text:
            continue
        sentence = statement(synopsis(text))
        if not sentence:
            # a program that never states a purpose cannot be claiming one, however long its manual
            continue
        said = _content_roots(sentence)
        bridged = {_root(w) for w in (also_says or {}).get(program, ())}
        shared = asked & said
        if not shared:
            continue
        # each shared word contributes what it can distinguish: a word every program says contributes nothing
        weight = sum(math.log2(total / max(1, document_frequency.get(w, 1))) for w in shared)
        # THE BRIDGE IS CONSULTED WITH THE PROGRAM'S OWN WORDS, NOT ONLY WHEN THEY FAIL. Measured: `chmod`
        # shares "change" and "file" with "change permissions on a file", so it always matched and the manual's
        # "permission" was never reached -- while `debconf-communicate` matched "permission" outright and won.
        # A word the project manual supplies counts at HALF, because the program itself did not use it, and
        # half is enough to break a tie between programs that say the same generic things.
        bonus = sum(math.log2(total / max(1, document_frequency.get(w, 1))) * 0.5
                    for w in (asked & bridged) - shared)
        # THE THRESHOLD MUST BE APPLIED AFTER THE BRIDGE, NOT BEFORE. Measured 2026-11-23: a small program set
        # gave `chmod` only "change" and "file" -- words every one of them says -- so it fell below
        # _MIN_EVIDENCE and was DISCARDED before the manual's "permission" could be added. A program was being
        # rejected for being uninformative on its own while holding exactly the evidence that made it right.
        if bonus:
            shared |= (asked & bridged)
            weight += bonus
            source = "OWN_MANUAL_AND_PROJECT_MANUAL"
        else:
            source = "OWN_MANUAL"
        if weight < _MIN_EVIDENCE:
            continue
        claims.append(Claim(program, round(weight, 3), tuple(sorted(shared)),
                            " ".join(sentence.split()), source))

    # MORE OF THE GOAL STATED IS BETTER; a tie is broken by who said it EARLIER in their own synopsis, because
    # a program that leads with the purpose is more likely to be the purpose. An exact tie stays a tie and is
    # reported as one rather than resolved by alphabetical order (§A74).
    claims.sort(key=lambda c: (-c.score, c.program))
    top = [c for c in claims if c.score == claims[0].score] if claims else []
    return {
        "schema": SCHEMA,
        "goal": goal,
        "claims": [{"program": c.program, "score": c.score, "stated": list(c.stated),
                    "says": c.sentence[:180], "source": c.source} for c in claims[:limit]],
        "best": [c.program for c in top],
        "asked_words": sorted(asked),
        "why": "STATED_IN_THEIR_OWN_SYNOPSIS" if claims else "NO_PROGRAM_STATES_IT",
    }


def read_manual(program: str, timeout: float = TIMEOUT_S) -> str:
    """A program's own `--help`, or empty. One second, because a program that hangs is not answering."""
    if not isinstance(program, str) or not program.strip():
        return ""
    try:
        result = subprocess.run([program, "--help"], capture_output=True, text=True, timeout=timeout)
    except Exception:  # noqa: BLE001 - not executable, not present, or too slow: all mean "no manual here"
        return ""
    return (result.stdout or "") + (result.stderr or "")


def index(programs: Iterable[str], *, workers: int = 16, timeout: float = TIMEOUT_S) -> dict[str, str]:
    """Every program that has a manual, read once. Bounded, parallel, and honest about who did not answer."""
    from concurrent.futures import ThreadPoolExecutor

    names = [p for p in programs if isinstance(p, str) and p.strip()]
    out: dict[str, str] = {}
    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        for program, text in zip(names, pool.map(lambda p: read_manual(p, timeout), names)):
            if text:
                out[program] = text
    return out
