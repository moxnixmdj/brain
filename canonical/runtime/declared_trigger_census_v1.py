"""Why the value algebra bought 5 pages and none outside its design set: the trigger is a phrase.

Last session measured the algebra at full suite scale (`DERIVED_VALUE_FULL_SUITE_20261116_V1`):

    added to the shipped vocabulary   +5 pages, 0 lost, 1917 fewer actions
    the same 5 pages                  all inside the 8 the operators were written on
    the other 121 pages               identical (77 vs 77)

That is a statement about a PART. Reading `canonical/runtime/derived_value_v1.derivations` says
why it cannot transfer, and the reason is not the algebra's arithmetic:

    LAST_WORD   fires on the instruction saying "last word" / "ends with"
    JOIN_SHOWN  fires on "below" / "shown" / "following" / "these"
    CLOCK24     fires on a `type=time` field, or the word "time"
    CASE_UPPER  fires on "upper" / "capital"

Every rule is gated on a hand-written English phrase. The phrase is a fact about the eight pages
the author read. It is not a fact about a page the author never saw, and the held-out number
agreed to the page. So the part was not a *method* that failed to generalise; it was a *lookup*
that had nothing to look up.

This module answers the question that decides what to build next, and it answers it BEFORE any
mechanism is written:

    1. Is there a trigger that is not this benchmark's English -- one the page DECLARES?
    2. If the declared surface is nearly empty, what do the unsolved pages actually lack?

Answer 1 is a count: of 123 pages with a usable observation, only SIX declare a non-text input
type (date, time, number, password), and 84 have no typeable field at all. A "declared format"
prior would cover six pages by construction. It is not a bottleneck; it is a rounding error.

Answer 2 is a taxonomy over every page the full hand cannot solve, decided by what the instruction
ASKS FOR. Its shape is the finding: sixteen classes, the largest holding six pages. There is no
single missing part large enough to be called the bottleneck. There is a long tail of parts.

Both answers are falsifiable by reading the pages, and the tests next to this module check that
the counts and the taxonomy still say what the record says they say.
"""
from __future__ import annotations

import collections
import json
import re

#: Where the full-suite measurement lives.
RECEIPT = "canonical/verification/DERIVED_VALUE_FULL_SUITE_20261116_V1.json"

#: Input types that DECLARE their format in the page rather than in the instruction's English.
#: `text` declares nothing, which is why 37 fields of it are the shipped hand's whole world.
DECLARING_INPUT_TYPES = frozenset({"date", "time", "number", "password", "email", "tel", "url",
                                   "range", "color", "datetime-local", "month", "week"})

#: Instruction shapes that name what the page lacks. ORDER MATTERS: the first match decides, and
#: the ordering puts the structural claims before the incidental ones so a page is classified by
#: the hardest thing it needs, not by a word it happens to share with an easier class.
RULES: tuple[tuple[str, str, re.Pattern[str]], ...] = (
    ("CONTINUOUS_TO_POSITION", "the value is derivable, the widget is not a text field",
     re.compile(r"\bwith the slider\b|\bsliders?\b.*\bcombination\b|\bcolor picker\b", re.I)),
    ("A_POINT_NOT_AN_ELEMENT", "no element names the answer; the answer is a location",
     re.compile(r"\bcenter of the circle\b|\bmid-?point\b|\bHOT area\b|\bdraw a (vertical )?line\b|"
                r"\bdraw a circle\b|\bthird point\b|\bcreate a right angle\b", re.I)),
    ("A_SUSTAINED_MOUSE_STATE", "the action is a held state, not a discrete step",
     re.compile(r"\bkeep your mouse\b|\bclick as many moving\b", re.I)),
    ("A_GEOMETRIC_CONSTRUCTION", "the answer is a placement satisfying a stated relation",
     re.compile(r"\bbisects the angle\b", re.I)),
    ("A_PERCEPTUAL_PROPERTY", "the element is present but only a look tells which",
     re.compile(r"\bshades of\b|\bsimilar to\b|\btriangles\b|\bblue shapes\b|\bstyle underlined\b|"
                r"\bhovered over the colored\b", re.I)),
    ("WORLD_KNOWLEDGE", "the answer is a fact about the world, not a function of the page",
     re.compile(r"\bodd or even\b|\bmeat\b|\bshortest one-way flight\b", re.I)),
    ("A_TIME_PLACED_ON_A_GRID", "the date is derivable, its cell must be located",
     re.compile(r"\bas the date\b|\bCreate a \d+ mins event\b", re.I)),
    ("FEEDBACK_ACROSS_TURNS", "no single action is correct; the page must be asked",
     re.compile(r"\bguess the number\b|\buse the feedback\b|\bwin a game\b|\bin the order displayed\b",
                re.I)),
    ("A_RENDERED_PATTERN", "the answer is a shape that must be built cell by cell",
     re.compile(r"\bdraw the number\b", re.I)),
    ("A_CONTINUOUS_SIZE", "the answer is a size, not a value or an element",
     re.compile(r"\bresize the textarea\b", re.I)),
    ("A_CONSTRAINED_SEARCH", "several conditions must hold at once over the page's records",
     re.compile(r"\bsearch for .+ directed by .+ from year\b", re.I)),
    ("A_NAMED_CONTROL", "the control is named; pressing it is the whole task",
     re.compile(r"\bclick on the .+ button\b|\bpress .agree.\b|\bscroll to the bottom\b", re.I)),
    ("A_VALUE_CARRIED_ACROSS_FIELDS", "the page holds the answer; it must be moved and constrained",
     re.compile(r"\bcopy the text\b|\benter the value that corresponds\b|\b5th word\b", re.I)),
    ("A_COUNT_OF_WHAT_IS_SHOWN", "the count is derivable, nothing else is missing",
     re.compile(r"\btotal number of blocks\b", re.I)),
    ("A_COORDINATED_SEQUENCE", "each step exists; the sequence is the missing thing",
     re.compile(r"\bradio button\b|\bclick the \d+(st|nd|rd|th)\b", re.I)),
    ("FIND_BY_CONTENT", "the target is present and named; finding it is the work",
     re.compile(r"\bemail from\b|\bbutton on all posts\b|\bposts by\b|\bselect milissent\b|"
                r"\bdelete a file\b", re.I)),
)

#: Pages jsdom would not reset during the census. Their instruction is read from the page file so
#: that no page is "unclassified because the instrument failed" -- an instrument limit must never
#: masquerade as a finding.
FROM_HTML = {
    "bisect-angle": "Create a line that bisects the angle evenly in two, then press submit.",
    "hover-shape": "Keep the mouse hovered over the colored square.",
    "moving-items": "Click as many moving circles as possible.",
}


def classify(utterance: str) -> dict[str, str]:
    """Which factor a page lacks, decided by what its instruction asks for."""
    text = str(utterance or "")
    for name, why, pattern in RULES:
        if pattern.search(text):
            return {"class": name, "missing_factor": why}
    return {"class": "UNCLASSIFIED", "missing_factor": "the instruction does not name its own answer"}


def declared_surface(census_rows) -> dict:
    """How much of the suite DECLARES its answer's format, independent of any English phrase."""
    types: collections.Counter = collections.Counter()
    pages_declaring: set[str] = set()
    pages_typeable: set[str] = set()
    for row in census_rows:
        if "error" in row:
            continue
        for field in row.get("fields") or []:
            name = str(field.get("type") or "").lower()
            types[name or "(none)"] += 1
            if name in DECLARING_INPUT_TYPES:
                pages_declaring.add(row["task"])
            if name in ("", "text"):
                pages_typeable.add(row["task"])
            else:
                pages_typeable.add(row["task"])
    usable = sum(1 for row in census_rows if "error" not in row)
    return {"pages_usable": usable,
            "pages_declaring_a_format": len(pages_declaring),
            "declaring_pages": sorted(pages_declaring),
            "pages_with_a_typeable_field": len(pages_typeable),
            "pages_with_no_typeable_field": usable - len(pages_typeable),
            "input_type_counts": dict(types.most_common())}


def taxonomy(receipt: dict, census_rows) -> dict:
    """Every page the full hand cannot solve, by the factor it lacks."""
    by_task = {row["task"]: row for row in census_rows}
    unsolved = [p["task"] for p in receipt["pages"] if not p["arms"]["U_union"]["pass"]]
    rows = []
    for task in sorted(unsolved):
        row = by_task.get(task, {})
        utterance = row.get("utterance") or FROM_HTML.get(task, "")
        rows.append({"task": task,
                     "typeable_fields": len(row.get("fields") or []),
                     "utterance": utterance, **classify(utterance)})
    grouped: dict[str, list[str]] = {}
    for row in rows:
        grouped.setdefault(row["class"], []).append(row["task"])
    ordered = sorted(grouped.items(), key=lambda kv: (-len(kv[1]), kv[0]))
    return {"pages_unsolved": len(rows),
            "classes": len(ordered),
            "largest_class": max((len(v) for v in grouped.values()), default=0),
            "by_class": {name: {"n": len(pages), "pages": pages} for name, pages in ordered},
            "rows": rows}


def load_census(path: str) -> list[dict]:
    import glob
    rows: list[dict] = []
    for file in sorted(glob.glob(path)):
        rows += json.loads(open(file).read())
    return rows


if __name__ == "__main__":
    import pathlib
    import sys
    root = pathlib.Path(__file__).resolve().parents[2]
    receipt = json.loads((root / RECEIPT).read_text())
    census = load_census(sys.argv[1] if len(sys.argv) > 1 else "/tmp/census_rows/*.json")
    print(json.dumps({"declared_surface": declared_surface(census),
                      "taxonomy": {k: v for k, v in taxonomy(receipt, census).items() if k != "rows"}},
                     indent=1))
