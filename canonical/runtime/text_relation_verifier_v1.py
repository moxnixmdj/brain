#!/usr/bin/env python3
"""Verify a text artifact by its RELATION TO ITS INPUT, with no reference answer.

Why this exists
---------------
`program_synthesis_v1.carries_content_evidence` refuses `.txt` and `.md`, and it is
right to: every text file opens as text, so "it is a text file" verifies nothing.
Measured over 13 ordinary goals, that single gate is why 10 were refused:

    sort notes.txt into sorted.txt          OPEN__FORMAT_CARRIES_NO_EVIDENCE
    deduplicate emails.txt into unique.txt  OPEN__A_QUESTION_IS_NOT_CLOSED_BY_A_FILE
    write a summary of notes.txt into out.md OPEN__FORMAT_CARRIES_NO_EVIDENCE

But for a class of goals the refusal is too broad, and 2026 verification work says
exactly where to widen it: property-based testing beat every alternative
(82.7% vs 58.3% baseline, and vs 77.3% for an agent judging its own output),
because it asks "does the output satisfy properties any correct output must
satisfy" instead of "does the output equal the reference".

For these verbs the property IS the definition:

    sort      every line of the output is a line of the input, the lines are
              non-decreasing, and the multisets are equal -- therefore the output
              is EXACTLY a sorted permutation of the input. No oracle required.
    reverse   output lines == input lines reversed.
    unique    output is a subsequence of the input, has no repeats, and keeps
              every distinct line the input had.
    upper /   output == input with case folded.
    lower
    head N    output == the first N lines of the input.
    tail N    output == the last N lines of the input.
    strip     output == input lines with blank lines removed.

Anything not in this table returns None, and the caller keeps its original
refusal. A goal that merely ENDS in .txt is still refused -- widening is per
recognised relation, never per suffix.

What this is NOT
----------------
Not a reference implementation: nothing here knows what the correct output is
before reading the input. Not a claim that "summarise this" is checkable -- it is
not, and it still refuses. Every relation here is an equality or a strict
ordering that either holds or does not.
"""
from __future__ import annotations

import pathlib
import re
from typing import Any

SCHEMA = "PROJECT_BRAIN_TEXT_RELATION_VERIFIER_V1"

# The verbs this module can decide, and how the goal is read to find them.
# Order matters: the first match wins, and they are written most-specific-first so
# "sort by length" (unsupported) does not silently become "sort".
_RELATIONS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("strip_blank", re.compile(r"\b(strip|remove|drop)\b[^.]*\b(blank|empty)\b[^.]*\blines?\b", re.I)),
    # "DEDUPLICATE" DOES NOT SAY IN WHAT ORDER, AND `uniq` CANNOT DO IT AT ALL.
    #
    # Measured: `uniq u.txt` removes only ADJACENT duplicates, so on
    # banana/apple/cherry/apple/... it prints the file unchanged. A goal that wants
    # the duplicate gone therefore cannot be closed by uniq, and a 121 s search over
    # single programs was correctly refusing every candidate -- they all returned the
    # input. The programs that can do it are `sort -u` (which reorders) and an
    # order-preserving awk. Which one is CORRECT depends on the goal, so the goal's
    # own words pick the relation:
    #     "deduplicate X into unique.txt"              -> set equality, order free
    #     "deduplicate X into unique.txt keeping order"-> a subsequence of the input
    # The order marker must appear AFTER the dedupe word, anywhere in the sentence,
    # and `[\s\S]` lets it cross punctuation and file names. An earlier version used
    # `[^.]*`, which stops at the FIRST FULL STOP -- and every one of these goals
    # contains one, because the output is "unique.txt". So the ordered variant never
    # matched and every dedupe goal silently took the unordered branch.
    ("unique_ordered", re.compile(
        r"\b(dedup\w*|unique|remove\s+duplicates?)\b[\s\S]*?\b(keeping|keep|preserv\w*|"
        r"same\s+order|original\s+order|in\s+order|order)\b", re.I)),
    ("unique", re.compile(r"\b(dedup\w*|unique|remove\s+duplicates?)\b", re.I)),
    # TWO DIFFERENT OPERATIONS SHARE THE WORD "REVERSE", AND CONFLATING THEM COST
    # 140 SECONDS OF SEARCH THAT COULD NOT SUCCEED.
    #
    # `rev` reverses the characters OF EACH LINE. `tac` reverses the ORDER OF LINES.
    # This table first mapped every "reverse" goal to line order, so for
    # "reverse list.txt into rev.txt" the installed program that does what the word
    # usually means was rejected every time, while the program that would have
    # passed was one no goal asked for. Both relations are kept, and the phrasing
    # decides which -- "reverse the lines"/"reverse the order of lines" vs "reverse
    # each line"/"reverse the characters".
    ("reverse_lines", re.compile(
        r"\b(reverse|invert)\b[^.]*\b(order|sequence)\b[^.]*\b(lines?|rows?)\b"
        r"|\breverse\s+the\s+lines?\b|\b(lines?\s+in\s+reverse)\b", re.I)),
    ("reverse_each_line", re.compile(
        r"\brev(erse)?\b[^.]*\b(each|every|characters?|chars?|letters?|text)\b"
        r"|\brev\b", re.I)),
    ("reverse", re.compile(r"\b(reverse|reversed|invert\s+the\s+order)\b", re.I)),
    ("upper", re.compile(r"\b(uppercase|upper[-\s]?case|to\s+upper)\b", re.I)),
    ("lower", re.compile(r"\b(lowercase|lower[-\s]?case|to\s+lower)\b", re.I)),
    ("head", re.compile(r"\b(head|first\s+(\d+)\s+lines?)\b", re.I)),
    ("tail", re.compile(r"\b(tail|last\s+(\d+)\s+lines?)\b", re.I)),
    ("sort", re.compile(r"\bsort(ed|ing)?\b", re.I)),
)

# Verbs that need a reference answer and must never be admitted by this module.
_NEEDS_ORACLE = re.compile(
    r"\b(summari[sz]e|summary|translate|rewrite|paraphrase|explain|describe|"
    r"improve|fix|clean|format|beautify|analysis|review|refactor)\b", re.I)


def _strip_output_name(goal: str) -> str:
    """The goal without its output filename.

    THE OUTPUT NAME IS NOT AN INSTRUCTION, AND IT KEEPS BEING MISTAKEN FOR ONE.
    Measured 2026-11-09, twice, in two different tables:
        "deduplicate emails.txt into unique.txt"  -> "unique" deleted as filename noise
                                                     (r152, flags_for_goal returned [])
        "strip blank lines from notes.txt into clean.txt"
                                                 -> "clean" matched the oracle-verb list
                                                    and the goal was refused in 0.0 s as
                                                    needing a reference answer
    The caller chooses what to CALL the file; that choice says nothing about what to DO.
    Every verb check here runs on the goal with the output name removed, so a file
    called clean.txt, summary.md or fixed.py cannot decide whether a goal is checkable.
    """
    import re as _re
    text = str(goal or "")
    m = _re.search(r"\b(?:into|to|as)\s+[\w./\-]*\.[a-z0-9]{1,6}\b", text, _re.I)
    if not m:
        return text
    return text[:m.start()] + " " + text[m.end():]


def relation_kind(goal: str) -> str | None:
    """Which relation, if any, does this goal ask for. None = not decidable here."""
    text = _strip_output_name(goal)
    if _NEEDS_ORACLE.search(text):
        return None
    for name, pattern in _RELATIONS:
        if pattern.search(text):
            return name
    return None


def _lines(data: bytes) -> list[str]:
    """Lines, with the trailing newline not counting as a line of its own.

    str.splitlines() drops nothing, but building a string with "\n".join() and
    reading it back does not round-trip when the source had a trailing newline:
    "banana\napple\n" is 2 lines, while "\n".join(sorted([...] )) of a list that
    already contains an empty string can end up 3. Measured on this module's own
    test fixture, that asymmetry made a correctly sorted file read as
    NOT_A_PERMUTATION_OF_THE_INPUT -- a false negative produced by bookkeeping,
    not by the relation. Whether a file ends with a newline is not part of sort,
    reverse, dedupe or case-folding, so exactly one trailing empty entry is
    dropped on both sides before comparing.
    """
    text = data.decode("utf-8", "surrogateescape")
    # A LINE TERMINATOR IS NOT A LINE. AN EMPTY FINAL LINE IS.
    #
    # "a\nb\n" is two lines; "a\nb\n\n" is three, the third being empty. Dropping a
    # trailing empty entry in both made them identical, and that broke `head`:
    # measured 2026-11-09, `head --lines 3` on a 7-line file ending in a blank line
    # returned "banana\napple\n\n" -- a CORRECT three-line answer -- and this
    # function read it as two lines, so the goal was rejected as
    # NOT_THE_FIRST_3_LINES and 289 s of search was spent failing to find a program
    # that had already been found.
    #
    # Exactly one trailing terminator is removed (the one that ends the final line);
    # any further empty entries are real lines and are kept.
    if text.endswith("\n"):
        text = text[:-1]
    lines = text.split("\n") if text != "" else []
    return lines


def _n_from(goal: str, default: int = 10) -> int:
    m = re.search(r"\b(\d+)\b", str(goal or ""))
    return int(m.group(1)) if m else default


def discriminates(goal: str, source: pathlib.Path) -> tuple[bool, str]:
    """Can this SOURCE tell a correct program from a wrong one?

    THE DEFECT THIS PREVENTS, measured before it was written.

    The seed file in computer_env_v1 is one line: "brain computer env sample\n".
    Reversing a one-line file returns the same line, so `patch` -- a diff tool that
    copies the input -- produced an output that satisfied "reverse" exactly, and
    discover("reverse list.txt into rev.txt") closed with plan ['run_patch'].

    The bug was not in the relation check; the relation check was right. The bug was
    that the FIXTURE could not distinguish reverse from copy. A property that holds
    trivially is not evidence, and a verifier that accepts it is a confident liar.

    So every relation here must be exercised by its input before it may be used:

        reverse   the source must differ from its own reverse   (>= 2 unequal lines)
        sort      the source must NOT already be sorted         (identity must fail)
        unique    the source must HAVE a duplicate              (identity must fail)
        upper     the source must contain a lowercase letter
        lower     the source must contain an uppercase letter
        head/tail the source must be LONGER than the number asked for
        strip     the source must contain a blank line

    When the source cannot discriminate, the verdict is refused, not passed.
    """
    kind = relation_kind(goal)
    if kind is None:
        return False, "NO_TEXT_RELATION_IN_GOAL"
    try:
        if not source.is_file():
            return False, "NO_SOURCE_TO_RELATE_TO"
        src = _lines(source.read_bytes())
    except Exception as exc:  # noqa: BLE001
        return False, "UNREADABLE:" + type(exc).__name__

    if kind == "reverse":
        return (src != list(reversed(src)),
                "SOURCE_DIFFERS_FROM_ITS_REVERSE" if src != list(reversed(src))
                else "SOURCE_EQUALS_ITS_OWN_REVERSE_SO_COPYING_PASSES")
    if kind == "reverse_lines":
        return (src != list(reversed(src)),
                "SOURCE_DIFFERS_FROM_ITS_LINE_REVERSE" if src != list(reversed(src))
                else "SOURCE_EQUALS_ITS_OWN_LINE_REVERSE_SO_COPYING_PASSES")
    if kind == "reverse_each_line":
        flipped = [l[::-1] for l in src]
        return (src != flipped,
                "SOURCE_DIFFERS_FROM_ITS_PER_LINE_REVERSE" if src != flipped
                else "SOURCE_EQUALS_ITS_OWN_PER_LINE_REVERSE_SO_COPYING_PASSES")
    if kind == "sort":
        return (src != sorted(src),
                "SOURCE_IS_UNSORTED" if src != sorted(src)
                else "SOURCE_ALREADY_SORTED_SO_COPYING_PASSES")
    if kind in ("unique", "unique_ordered"):
        return (len(set(src)) != len(src),
                "SOURCE_HAS_A_DUPLICATE" if len(set(src)) != len(src)
                else "SOURCE_ALREADY_UNIQUE_SO_COPYING_PASSES")
    if kind == "upper":
        return (any(l != l.upper() for l in src),
                "SOURCE_HAS_LOWERCASE" if any(l != l.upper() for l in src)
                else "SOURCE_ALREADY_UPPERCASE_SO_COPYING_PASSES")
    if kind == "lower":
        return (any(l != l.lower() for l in src),
                "SOURCE_HAS_UPPERCASE" if any(l != l.lower() for l in src)
                else "SOURCE_ALREADY_LOWERCASE_SO_COPYING_PASSES")
    if kind == "head":
        n = _n_from(goal)
        return (len(src) > n, "SOURCE_LONGER_THAN_%d" % n if len(src) > n
                else "SOURCE_NO_LONGER_THAN_%d_SO_COPYING_PASSES" % n)
    if kind == "tail":
        n = _n_from(goal)
        return (len(src) > n, "SOURCE_LONGER_THAN_%d" % n if len(src) > n
                else "SOURCE_NO_LONGER_THAN_%d_SO_COPYING_PASSES" % n)
    if kind == "strip_blank":
        return (any(not l.strip() for l in src),
                "SOURCE_HAS_A_BLANK_LINE" if any(not l.strip() for l in src)
                else "SOURCE_HAS_NO_BLANK_LINE_SO_COPYING_PASSES")
    return False, "UNHANDLED_RELATION:" + str(kind)


def verdict(goal: str, source: pathlib.Path, output: pathlib.Path) -> tuple[bool, str]:
    """(holds, why).  False with a reason is the honest default for anything odd.

    Reads both files as bytes, decodes leniently, and compares line lists. A
    relation either holds for this exact pair of files or it does not; there is
    no sample and no proof obligation beyond the files themselves.
    """
    kind = relation_kind(goal)
    if kind is None:
        return False, "NO_TEXT_RELATION_IN_GOAL"
    # REFUSE BEFORE COMPARING when the input cannot tell right from wrong.
    can, why_not = discriminates(goal, source)
    if not can:
        return False, "SOURCE_CANNOT_DISCRIMINATE:" + why_not
    try:
        if not output.is_file():
            return False, "NO_OUTPUT"
        if not source.is_file():
            return False, "NO_SOURCE_TO_RELATE_TO"
        src = _lines(source.read_bytes())
        out = _lines(output.read_bytes())
    except Exception as exc:  # noqa: BLE001 - a verifier never raises into a search
        return False, "UNREADABLE:" + type(exc).__name__

    if kind == "sort":
        if sorted(out) != sorted(src):
            return False, "NOT_A_PERMUTATION_OF_THE_INPUT"
        if any(out[i] > out[i + 1] for i in range(len(out) - 1)):
            return False, "NOT_ORDERED"
        return True, "SORTED_PERMUTATION_OF_INPUT"
    if kind == "reverse_lines":
        want = list(reversed(src))
        return (out == want, "LINE_ORDER_REVERSED" if out == want
                else "LINE_ORDER_NOT_REVERSED")
    if kind == "reverse_each_line":
        want = [l[::-1] for l in src]
        return (out == want, "EACH_LINE_REVERSED" if out == want
                else "NOT_EACH_LINE_REVERSED")
    if kind == "reverse":
        want = list(reversed(src))
        return (out == want, "REVERSED_INPUT" if out == want
                else "NOT_THE_REVERSE_OF_THE_INPUT")
    if kind == "unique_ordered":
        # ORDER IS REQUIRED HERE, so the output must be an order-preserving
        # subsequence: each distinct line once, in the order it first appeared.
        if len(set(out)) != len(out):
            return False, "STILL_CONTAINS_REPEATS"
        if set(out) != set(src):
            return False, "LOST_OR_INVENTED_A_DISTINCT_LINE"
        it = iter(src)
        if not all(any(line == s for s in it) for line in out):
            return False, "NOT_A_SUBSEQUENCE_OF_THE_INPUT"
        return True, "DEDUPLICATED_IN_ORDER"
    if kind == "unique":
        # NO LINE MAY REPEAT ANYWHERE IN THE OUTPUT.
        #
        # The first version of this check only compared NEIGHBOURS, so an output
        # that was the input unchanged passed whenever the repeated line was not
        # adjacent. Measured before the fix: input `banana/apple/cherry/apple`
        # produced verbatim as the "deduplicated" answer returned True, because
        # the two `apple` lines were not next to each other. A deduplicated file
        # has each distinct line exactly once, so len(set(out)) == len(out) is
        # the invariant -- not "no adjacent repeats".
        if len(set(out)) != len(out):
            return False, "STILL_CONTAINS_REPEATS"
        if set(out) != set(src):
            return False, "LOST_OR_INVENTED_A_DISTINCT_LINE"
        # ORDER IS UNSPECIFIED HERE, so it is not checked. Requiring it would
        # reject `sort -u`, which is a correct deduplication.
        return True, "DEDUPLICATED_SET_OF_INPUT_LINES"
    if kind == "upper":
        ok = out == [l.upper() for l in src]
        return ok, "UPPERCASED_INPUT" if ok else "NOT_THE_INPUT_UPPERCASED"
    if kind == "lower":
        ok = out == [l.lower() for l in src]
        return ok, "LOWERCASED_INPUT" if ok else "NOT_THE_INPUT_LOWERCASED"
    if kind == "head":
        n = _n_from(goal)
        ok = out == src[:n]
        return ok, ("FIRST_%d_LINES" % n) if ok else "NOT_THE_FIRST_%d_LINES" % n
    if kind == "tail":
        n = _n_from(goal)
        ok = out == src[-n:] if n else out == []
        return ok, ("LAST_%d_LINES" % n) if ok else "NOT_THE_LAST_%d_LINES" % n
    if kind == "strip_blank":
        want = [l for l in src if l.strip()]
        return (out == want, "BLANK_LINES_REMOVED" if out == want
                else "BLANK_LINES_STILL_PRESENT_OR_CONTENT_CHANGED")
    return False, "UNHANDLED_RELATION:" + str(kind)


# A relation goal must SAY WHERE THE RESULT GOES. Without this, a pure QUESTION
# admits itself: "the unique lines of the file a.txt" contains the word "unique"
# and the suffix .txt belonging to its INPUT, so an earlier version of admits()
# returned True and the goal was routed into construction instead of being
# answered. Measured: test_a_goal_that_asks_for_a_value_is_not_reported_closed
# failed with OPEN__EFFECT_NOT_VERIFIED where it required the question refusal.
_OUTPUT_PHRASE = re.compile(
    r"\b(?:into|to|as|in)\s+[\w./\-]*\.[a-z0-9]{1,6}\b", re.I)


def names_an_output(goal: str) -> bool:
    """Does the goal say where the result is written?"""
    return bool(_OUTPUT_PHRASE.search(str(goal or "")))


def admits(goal: str, suffix: str) -> bool:
    """May a goal/suffix pair that `carries_content_evidence` refused be tried anyway?

    All three must hold: a text suffix, a relation this module can decide, and an
    explicit output artifact. The third is what keeps a QUESTION a question.
    """
    if str(suffix or "").lower() not in (".txt", ".md"):
        return False
    if not names_an_output(goal):
        return False
    return relation_kind(goal) is not None


def status() -> dict[str, Any]:
    return {"schema": SCHEMA,
            "relations": [n for n, _ in _RELATIONS],
            "admits_suffixes": [".txt", ".md"],
            "refuses_verbs": _NEEDS_ORACLE.pattern}


# A probe input that can tell every relation in this module from "copy the input".
#
# Why a fixed probe rather than the caller's real file: the search has to run on
# SOMETHING, and computer_env_v1's default seed is one line, which no ordering
# relation can discriminate. The probe is only used to find and verify a program;
# the caller's own file is what the program is later applied to. It is deliberately
# adversarial to copy/sort/reverse/dedupe/upper/lower, and it round-trips through
# every check in `discriminates`.
_PROBE = (
    "banana\n"
    "apple\n"
    "\n"
    "cherry\n"
    "apple\n"
    "date\n"
    "elderberry\n"
)


def probe_seed(name: str = "input.txt") -> dict[str, bytes]:
    """A seed whose contents make every relation here non-trivial."""
    return {name: _PROBE.encode()}


def probe_seed_name(goal: str, default: str = "input.txt") -> str:
    """The SOURCE file name, so the program is invoked with a familiar argv.

    The source is whatever is named BEFORE "into"/"to"; the thing after it is the
    output and must never be used as the seed, or the search would train on the
    artifact it is supposed to produce.
    """
    import re as _re
    text = str(goal or "")
    head = _re.split(r"\b(?:into|to)\b", text, maxsplit=1, flags=_re.I)[0]
    m = _re.search(r"([\w.\-]+\.(?:txt|md))", head, _re.I)
    return m.group(1) if m else default


# The program whose manual defines each relation. This is a definition, not a hint:
# `sort` is the program that sorts. It is still PROVEN, not trusted -- the plan must
# execute and its bytes must satisfy the relation, and the fixture must discriminate.
#
# Why this table has to exist: candidate selection here works from the SUFFIX and from
# manual tokens. Measured 2026-11-09, for "sort notes.txt into sorted.txt":
#     programs_for('.txt') = ['gp-display-text','md5sum.textutils','pod2text',
#                             'pygettext3','systemd-sysext','addpart','addr2line',
#                             'animate','apt','apt-cache',...]      <- no `sort`
#     programs_for_goal(goal) omitted `sort` as well.
# `sort`, `rev` and `uniq` are all installed and work. The machine owned the programs
# it needed and its shortlist never named them, so a 126 s search could not succeed.
_CANONICAL_PROGRAM = {
    "sort": "sort", "reverse": "rev", "reverse_each_line": "rev",
    "reverse_lines": "tac", "unique": "sort", "unique_ordered": "awk",
    "upper": "tr", "lower": "tr", "head": "head", "tail": "tail",
    "strip_blank": "sed",
}


def canonical_programs(goal: str) -> list[str]:
    """The program that defines this goal's relation, first in the shortlist."""
    kind = relation_kind(goal)
    name = _CANONICAL_PROGRAM.get(kind or "")
    return [name] if name else []
