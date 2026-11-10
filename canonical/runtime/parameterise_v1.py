"""What a demonstration should keep: the SHAPE, with holes where the goal fills in.

The measurement that forced this file.  A goal was solved and recorded:

    "show only the urgent messages"   ->  click filter, type "urgent", click APPLY
    recorded as                         click @(174,133), type "urgent", click @(436,133)

Then the same page, a different goal:

    "show only the messages about refund"

The learned trajectory types "urgent" again.  It cannot do anything else, because "urgent"
was recorded as PIXELS -- the type action carried a literal string -- and nothing in the
record says which part of the goal produced it.

That is the difference between a REHEARSAL and a PROCEDURE, and it is the same mistake this
repository has made in three other forms already:

    r64  replay keyed on a screen hash      -- a fact about one screenshot
    r65  anchors instead of coordinates     -- fixed that
    r70  a literal string instead of a slot  -- this file

A procedure is the trajectory with the goal-derived parts replaced by holes, plus a rule for
what fills each hole.  Then a new goal on the same page runs the same procedure with a
different value, and no model is needed for the reuse -- which is the only thing that ever
made "learn it once" worth anything.
"""
from __future__ import annotations

import pathlib
import re
from collections.abc import Mapping
from typing import Any

SCHEMA = "PARAMETERISE_V1"

# Words that describe the SHAPE of a request rather than its content.  A parameter must not
# be one of these: "show only the urgent messages" should not parameterise on "messages".
SHAPE_WORDS = frozenset("""show only the find get give put make list display all any
message messages item items thing things please me my it this that some about from
for with in on at to by of and or not no yes then when where what which who how""".split())


def _content_words(goal: str) -> list[str]:
    return [w for w in re.findall(r"[a-z0-9]+", goal.lower()) if w not in SHAPE_WORDS]


def learn_with_slots(goal: str, actions: list[Mapping[str, Any]]) -> dict[str, Any]:
    """Bind any typed value that came from the goal to the part of the goal it came from."""
    content = _content_words(goal)
    slots: list[dict[str, Any]] = []
    out = []
    for a in actions:
        a = dict(a)
        if a.get("action") == "type":
            text = str(a.get("text", ""))
            words = re.findall(r"[a-z0-9]+", text.lower())
            if words and all(w in content for w in words):
                # the typed value came from the goal: it is a PARAMETER, not a constant
                slot = f"{{slot{len(slots)}}}"
                slots.append({"slot": slot, "kind": "content_word",
                              "taught_value": text,
                              "from_goal": [w for w in words if w in content]})
                a["text"] = slot
        out.append(a)
    return {"schema": SCHEMA, "goal": goal, "actions": out, "slots": slots,
            "content_words_in_goal": content}


def fill(template: Mapping[str, Any], new_goal: str) -> dict[str, Any]:
    """Fill the holes from a new goal on the same page.  Refuses if it cannot."""
    content = _content_words(new_goal)
    taught = template["content_words_in_goal"]
    used = [w for s in template["slots"] for w in s["from_goal"]]
    # what in the new goal corresponds?  same position in the content-word list, else the
    # words that are not part of the shape of the request.
    values: dict[str, str] = {}
    for i, s in enumerate(template["slots"]):
        if not content:
            return {"schema": SCHEMA, "verdict": "CANNOT_FILL",
                    "because": "the new goal has no content words to bind"}
        if len(content) == len(taught):
            values[s["slot"]] = content[used.index(s["from_goal"][0])] if s["from_goal"] else content[0]
        else:
            # Fall back to words that differ from the taught goal.  Function words are
            # excluded, or "about" in "the messages about refund" gets bound as the value.
            # Found by running it: the first version filled the slot with "about", then
            # with "from".
            novel = [w for w in content if w not in taught and w not in SHAPE_WORDS]
            if not novel:
                return {"schema": SCHEMA, "verdict": "CANNOT_FILL",
                        "because": "no word in the new goal differs from the taught one"}
            values[s["slot"]] = novel[0]
    actions = []
    for a in template["actions"]:
        a = dict(a)
        if a.get("action") == "type" and a.get("text") in values:
            a["text"] = values[a["text"]]
        actions.append(a)
    return {"schema": SCHEMA, "verdict": "FILLED", "actions": actions, "values": values,
            "from_goal": new_goal}
