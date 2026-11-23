"""Do this machine's refusals say WHAT is wrong, or only that something is?

WHY THIS IS THE BOTTLENECK AND NOT A NICETY. A repair loop can only answer a refusal that names the thing
it wants. Measured 2026-11-23, one row became verified by reading two refusals -- and the loop only worked
AFTER `TEST_ROOT_MISSING` was changed to `TEST_ROOT_MISSING:<the path it wants>`. Before that the code named
the missing kind and not its location, so an honest client could only guess, and the guess was wrong twice.

If most refusals are bare, then "the machine learns from what the environment tells it" has a ceiling set by
how much the environment says. That is measurable, so it is measured here rather than argued.

THE SCAN IS LEXICAL AND SAYS SO. It reads `raise SomeError("CODE")` versus `raise SomeError("CODE:...")`
from the adapter sources. It does not import or execute them: importing 330 adapters to ask a question about
their text would be slow and would answer a different question (which paths run, not what they say).

WHAT COUNTS AS LOCATED. Suffix after the code's colon, or a `+` concatenation. `PATH_OUTSIDE_REPOSITORY` with
no value is a true statement about the request and useless to a client; `PATH_OUTSIDE_REPOSITORY:<path>` is
a fact. The list of the most common bare codes is the work item, ordered by how often a client would hit it.
"""

from __future__ import annotations

import json
import pathlib
import re
from collections import Counter
from typing import Any

SCHEMA = "PROJECT_BRAIN_REFUSAL_LOCATION_V1"

# `raise <Name>("CODE..."` or `raise <Name>("CODE:" + ...` -- the two shapes an adapter uses.
# THREE SHAPES, measured rather than assumed:
#   raise X("CODE")                bare
#   raise X("CODE:" + value)       located, colon inside the literal
#   raise X("CODE" + ":" + value)  located, colon concatenated -- the first version of this scan could
#                                  not see this shape, so locating 7 refusals changed the report by
#                                  zero. A measurement blind to the improvement reports failure forever.
#
# THE SCAN COUNTS BOTH WAYS AN ADAPTER REFUSES. `raise X("CODE")` is one; `_fail("CODE")` is the helper
# shape used 293 times in this directory, and a scan that only looked at `raise` under-reported the total by
# about 18% while appearing complete.
_RAISE = re.compile(r"(?:raise\s+\w+|_fail)\(\s*[\"'](?P<code>[A-Z][A-Z0-9_]{3,})(?P<tail>:|[\"'])")
# A code followed by `%` or `.format(` or an f-string is located too, by a different spelling.
_RAISE_FORMATTED = re.compile(r"(?:raise\s+\w+|_fail)\(\s*f[\"'](?P<code>[A-Z][A-Z0-9_]{3,}):")


def _located_after(literal: str) -> bool:
    """Is this refusal's message literal carrying a value, or is it just the code?

    Called with the FULL STRING the raise is given is not available lexically, so this reads the line the
    code was found on: a located refusal has a `:` after the code's characters, or a `+` before the closing
    quote. Two earlier versions tried to infer this from match offsets and got both directions wrong; the
    lesson is that the check must be stated in terms of what is visible on the line.
    """
    return ":" in literal


def _root() -> pathlib.Path:
    return pathlib.Path(__file__).resolve().parents[2]


def scan(directory: pathlib.Path | None = None) -> dict[str, Any]:
    """Count refusals that locate themselves against refusals that do not."""
    directory = pathlib.Path(directory or (_root() / "canonical/runtime/bound_capabilities"))
    located = 0
    bare = 0
    bare_codes: Counter[str] = Counter()
    located_codes: Counter[str] = Counter()
    per_file: dict[str, dict[str, int]] = {}

    for path in sorted(directory.glob("*.py")):
        text = path.read_text(encoding="utf-8", errors="replace")
        file_located = 0
        file_bare = 0
        for match in _RAISE.finditer(text):
            code = match.group("code")
            line_start = text.rfind("\n", 0, match.start()) + 1
            line_end = text.find("\n", match.end())
            line = text[line_start:line_end if line_end != -1 else len(text)]
            # A CODE WITH A COLON AFTER IT IN THE SAME LITERAL IS LOCATED; a colon elsewhere on the line is
            # not. Two counts of this disagreed by 10 points (37.8% vs 27.5%) because one of them accepted a
            # colon anywhere on the line -- e.g. a dict literal or a type annotation -- and the other did
            # not. Neither may be reported until they agree, so the rule is written to be checkable:
            # the characters between the code and the closing quote must start with ":".
            tail = line[line.find(code) + len(code):] if code in line else ""
            if tail.startswith(":") or tail.startswith('" + ":"') or tail.startswith("' + ':'"):
                located += 1
                file_located += 1
                located_codes[code] += 1
            else:
                bare += 1
                file_bare += 1
                bare_codes[code] += 1
        for match in _RAISE_FORMATTED.finditer(text):
            located += 1
            file_located += 1
            located_codes[match.group("code")] += 1
        if file_located or file_bare:
            per_file[path.name] = {"located": file_located, "bare": file_bare}

    total = located + bare
    return {
        "schema": SCHEMA,
        "files": len(per_file),
        "refusals": total,
        "located": located,
        "bare": bare,
        "located_fraction": round(located / total, 4) if total else None,
        "distinct_bare_codes": len(bare_codes),
        "distinct_located_codes": len(located_codes),
        "most_common_bare": bare_codes.most_common(15),
        "note": ("A bare code names the KIND of problem and not the INSTANCE, so a client that can only "
                 "read messages cannot repair it. 'located' is a property of the message text, measured "
                 "lexically; it does not claim the value is the useful one."),
    }


def main() -> None:
    report = scan()
    print(json.dumps({k: report[k] for k in ("refusals", "located", "bare", "located_fraction",
                                             "distinct_bare_codes")}, indent=1))
    for code, count in report["most_common_bare"]:
        print("  %4d  %s" % (count, code))


if __name__ == "__main__":
    main()
