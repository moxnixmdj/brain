"""THE PROGRAM'S HELP AND THE PROJECT'S MANUAL NAME THE SAME THING DIFFERENTLY. That gap IS the relation.

THE WALL THIS REMOVES, MEASURED THREE TIMES IN A ROW.

    §A134   "write a new email"  vs the page's "Compose"          no shared word; needed a stated relation
    §A138   "count words"        vs `wc`'s "word ... counts"      a plural, fixed by one suffix rule
    §A138   "change permissions" vs `chmod`'s "Change the mode"   NOTHING in either text relates them

The third is not a stemming problem or a ranking problem. `chmod --help` says, in full:

    Change the mode of each FILE to MODE.

and a person says "permissions". "Mode" and "permission" are the same thing in UNIX, and neither string
contains the other, and no frequency weight can invent the link.

THE FACT. The relation IS written down, by the same authors, in a different document:

    GNU Coreutils manual, top node:
        chmod: (coreutils)chmod invocation.  Change access permissions.

So the program's own help says "mode" and the project's own manual says "permissions", about the same command.
**The disagreement between two authoritative sources is the means-relation**, and it is sourced on both sides
rather than asserted by anything.

WHY THIS IS THE RIGHT SHAPE AND A THESAURUS IS NOT. A thesaurus would put `mode ~ permission` in a table that
this repository cannot check and would have to take on trust -- exactly the "knowledge house" the constraints
forbid. Here each side is quoted from the authors: the help line, the manual line, and where each came from. If
the manual is missing or says nothing, no relation is derived and the caller is told so.

WHAT THIS DOES NOT DO. It does not make the two names identical everywhere: `chmod`'s help says "mode" and its
manual says "permissions", but `sort`'s help and manual both say "sort", and no relation is invented there
because there is nothing to relate. A relation is only ever the difference between two real documents.

AUTHORITY NONE. No model, no parameters, no dictionary, no network at call time unless asked. $0.
"""
from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

SCHEMA = "PROJECT_BRAIN_THE_MANUAL_AND_THE_HELP_DISAGREE_V1"

# The words a manual uses about a command rather than about the world. They are grammar for this purpose: the
# manual's index line is "chmod: (coreutils)chmod invocation. Change access permissions." and "invocation" and
# "access" say nothing that distinguishes this command from any other.
_INDEX_NOISE = frozenset("""
invocation command commands program program's access file file's etc option options see also the a an and or of
to for in on at by with from into its this that which who
""".split())


def _words(text: str) -> list[str]:
    return [w for w in re.findall(r"[a-z0-9][a-z0-9'-]*", str(text or "").lower()) if len(w) >= 3]


def _root(word: str) -> str:
    w = word.casefold()
    for suffix, floor in (("ies", 4), ("es", 4), ("s", 3)):
        if w.endswith(suffix) and len(w) - len(suffix) >= floor:
            return w[: -len(suffix)]
    return w


def manual_statement(manual_text: str, program: str) -> str:
    """The sentence a manual uses to describe `program`, taken from its own index line.

    A texinfo manual lists its commands as `name: (package)name invocation.  <what it does>` -- which is the
    manual stating the program's purpose in the authors' words. Nothing is paraphrased: the sentence is
    returned as written so the caller can check it.
    """
    if not manual_text or not program:
        return ""
    # MEASURED 2026-11-23: the entry is a menu line -- `* chmod: (coreutils)chmod invocation.   Change access
    # permissions.` -- prefixed with "* " and padded with runs of spaces before the description. Anchoring to
    # the start of the line and not allowing the "*" found nothing in a 685 KB manual, and every program
    # looked like it had no manual statement. The punctuation of the document is part of the document.
    pattern = re.compile(r"^\s*\*?\s*" + re.escape(program) +
                         r"\s*:\s*\([^)]*\)[^.\n]*\.\s+(.+)$", re.M | re.I)
    match = pattern.search(manual_text)
    if not match:
        return ""
    return " ".join(match.group(1).split())


@dataclass(frozen=True)
class Relation:
    """Two names for one thing, each quoted from an authoritative document, with where it came from."""
    word_in_help: str
    word_in_manual: str
    basis: str


def relation_between(help_text: str, manual_text: str, program: str) -> dict[str, Any]:
    """What the manual calls this program's subject, that the program's own help does not.

    Returns the relation or a refusal. A refusal is the normal answer: most programs' help and manual agree,
    and then there is nothing to relate.
    """
    stated = manual_statement(manual_text, program)
    if not stated:
        return {"schema": SCHEMA, "program": program, "relation": None,
                "why": "THE_MANUAL_SAYS_NOTHING_ABOUT_THIS_PROGRAM"}

    # what the HELP calls it -- its first plain description line, minus the words both share
    help_words = {_root(w) for w in _words(help_text) if w not in _INDEX_NOISE}
    manual_words = [_root(w) for w in _words(stated) if w not in _INDEX_NOISE]
    if not manual_words:
        return {"schema": SCHEMA, "program": program, "relation": None,
                "why": "THE_MANUAL_STATEMENT_HAS_NO_CONTENT_WORD"}

    # A DIFFERENT INFLECTION IS NOT A DIFFERENT WORD. Measured 2026-11-23: `sort`'s help says "FILE(s)" and its
    # manual says "text files", and a plain set difference reported "text" and "file" as words the manual added
    # -- so every program looked like it related two vocabularies. The comparison is on roots.
    help_roots = {_root(w) for w in _words(help_text)}
    novel = [w for w in manual_words if w not in help_roots]
    if not novel:
        return {"schema": SCHEMA, "program": program, "relation": None,
                "why": "THE_TWO_DOCUMENTS_AGREE"}
    return {
        "schema": SCHEMA,
        "program": program,
        "relation": Relation(word_in_help="", word_in_manual=novel[0],
                             basis=stated).__dict__,
        "manual_says": stated,
        "manual_words_not_in_help": novel,
        "why": "THE_MANUAL_NAMES_IT_DIFFERENTLY",
    }


def relations_from(programs: Sequence[str], helps: Mapping[str, str],
                   manuals: Mapping[str, str]) -> dict[str, list[str]]:
    """For every program with both documents, the words its manual uses that its help does not.

    This is the vocabulary bridge, read off real documents. It is not a thesaurus: each entry exists because
    two authoritative texts about the SAME program used different words, which is a fact about those texts.
    """
    out: dict[str, list[str]] = {}
    for program in programs:
        found = relation_between(helps.get(program, ""), manuals.get(program, ""), program)
        words = found.get("manual_words_not_in_help") or []
        if words:
            out[program] = words
    return out
