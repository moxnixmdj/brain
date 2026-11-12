#!/usr/bin/env python3
"""A skill may only be learned about a defect that is actually present.

THE DEFECT THIS CLOSES
----------------------
`crystallize_code_fix` requires a *failing baseline* on `before_snippet`. That is a check on
the verifier, not on the code: a caller-supplied verifier can report a failure for any input,
including correct code, and the store will accept the "fix". Measured 2026-11-12:

    before: `def ok(x): return x < 10`      correct code, no defect
    after : `def ok(x): return x <= 10`     the "fix" makes it wrong
    crystallized: True   state: ACTIVE

and the resulting rule then applies to a different, correct function:

    victim (correct)   : return a < 100
    after skill applied: return a <= 100        INTRODUCED A BUG: True

So the missing precondition is not "was the verifier satisfied" but "is the defect actually
there". Without it, a skill is a rewrite whose justification is whatever the caller said.

WHAT THIS MODULE DOES
---------------------
`defect_is_present(before, after, field, accessor)` compares the BEFORE and AFTER snippets on
the *specific value* the fix is supposed to change:

    PRESENT      the observed values differ, and `before` holds the value the fix claims is wrong
    ABSENT       the values already agree -- there is nothing for the fix to repair
    REFUSED      the accessor raised on the before-snippet, so the defect cannot be established
    UNOBSERVABLE no accessor was supplied, so nothing can be established

PRESENT is the only verdict that permits learning. Everything else is a refusal, because a
rule learned against a defect that was not there is a rule with a false justification, and
the store has no way to notice later: it only knows the rule applied cleanly.

WHY THIS SHAPE
--------------
It is deliberately narrow and executable. `field` and `accessor` must be given by the caller
because the tree cannot know that `x < 10` versus `x <= 10` is a different predicate without
being told what to measure -- the same "a candidate cannot declare its domain" limit recorded
in `domain_of_verification_v1`, applied to a single edit instead of a hypothesis.

Authority: NONE. No capability is claimed; this is a precondition check, not a verifier.
"""
from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Callable, Mapping

SCHEMA = "PROJECT_BRAIN_SKILL_PRECONDITION_PRESENCE_V1"

PRESENT = "PRESENT"
ABSENT = "ABSENT"
REFUSED = "REFUSED"
UNOBSERVABLE = "UNOBSERVABLE"

#: Only this verdict permits learning. Kept as a set so a caller cannot widen it by accident.
PERMITS_LEARNING = frozenset({PRESENT})


def defect_is_present(
    before: str,
    after: str,
    *,
    field: str,
    accessor: Callable[[str], Any] | None = None,
) -> dict[str, Any]:
    """Establish that the defect a fix claims to repair is present in `before`.

    `accessor` extracts the observable the defect lives in -- a value, an AST node type, a
    call count. It must be deterministic or the verdict means nothing.
    """
    if accessor is None:
        return {"verdict": UNOBSERVABLE, "field": field,
                "reason": "NO_ACCESSOR",
                "detail": "nothing was measured, so nothing can be established"}

    try:
        before_value = accessor(before)
    except Exception as exc:
        return {"verdict": REFUSED, "field": field,
                "reason": f"ACCESSOR_RAISED_ON_BEFORE:{type(exc).__name__}"}

    try:
        after_value = accessor(after)
    except Exception as exc:
        return {"verdict": REFUSED, "field": field,
                "reason": f"ACCESSOR_RAISED_ON_AFTER:{type(exc).__name__}"}

    if before_value == after_value:
        return {"verdict": ABSENT, "field": field,
                "reason": "OBSERVED_VALUE_UNCHANGED",
                "before": before_value, "after": after_value,
                "detail": "the fix changes nothing this accessor can see; there is no defect"
                          " for it to repair"}

    return {"verdict": PRESENT, "field": field, "reason": None,
            "before": before_value, "after": after_value}


def gate(before: str, after: str, *, field: str,
         accessor: Callable[[str], Any] | None = None) -> dict[str, Any]:
    """The decision a learner should branch on: may this pair be learned from?"""
    outcome = defect_is_present(before, after, field=field, accessor=accessor)
    outcome["may_learn"] = outcome["verdict"] in PERMITS_LEARNING
    if not outcome["may_learn"]:
        outcome.setdefault("detail",
                           "the defect is not established, so the fix has no justification")
    return outcome


# ---------------------------------------------------------------------------
# a default accessor for the commonest case: a comparison operator in a snippet
# ---------------------------------------------------------------------------
def comparison_operator(text: str) -> tuple[str, ...]:
    """EVERY comparison operator in `text`, in order, as a tuple (empty when there are none).

    Measured while building this: returning only the FIRST operator made
    `x < 10` -> `x + 1` look like a boundary fix, because both snippets scored `<`. The
    observable is the whole sequence of comparisons, not the first one -- a partial read of
    the thing being changed is how a check reports a defect that is not the one it measured.
    """
    found: list[str] = []
    index = 0
    ordered = ("<=", ">=", "==", "!=", "<", ">")
    while index < len(text):
        for token in ordered:
            if text.startswith(token, index):
                found.append(token)
                index += len(token)
                break
        else:
            index += 1
    return tuple(found)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--before", required=True)
    parser.add_argument("--after", required=True)
    parser.add_argument("--field", default="comparison_operator")
    args = parser.parse_args(argv)

    outcome = gate(args.before, args.after, field=args.field,
                   accessor=comparison_operator)
    print(json.dumps(outcome, indent=2, sort_keys=True, default=str))
    return 0 if outcome.get("may_learn") else 1


if __name__ == "__main__":
    raise SystemExit(main())
