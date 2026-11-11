#!/usr/bin/env python3
"""Hand a QUESTION to the route that can answer it, without pretending it made a file.

Why a separate module and not a branch inside discover()
--------------------------------------------------------
`discover()` answers one question: "which command produces the named output file?"
Its `closed=True` is consumed by `composer_route_v1` as
`DISCOVERED_BY_ACTING_AND_EFFECT_VERIFIED`. A question has no output file, and its
answer is a VALUE. Returning one from `discover()` would make `closed=True` mean two
different things and let a verified number travel as a verified artifact -- the exact
false claim that made `md5sum` an accepted answer to "the different lines of a.txt"
and that `OPEN__A_QUESTION_IS_NOT_CLOSED_BY_A_FILE_APPEARING` exists to prevent.

So the handoff is a SEPARATE call with a SEPARATE result shape. It says `answered`,
never `closed`. A caller that wants an artifact still gets a refusal from discover();
a caller that asked a question gets the number.

Measured 2026-11-09, computer_env_v1.answer_query called directly on a 7-line file:
    count the lines               -> 7      0.01 s
    count the words               -> 6      0.91 s
    the different lines           -> 6      0.01 s
while discover() on the same three goals returned the question refusal in 0.00 s and
never called it. The refusal message itself says "this route cannot answer questions
-- answer_query does", and nothing did the handoff.
"""
from __future__ import annotations

import pathlib
from typing import Any

SCHEMA = "PROJECT_BRAIN_QUESTION_HANDOFF_V1"

# What makes a goal a question rather than a request for an artifact.
_ANSWERED = "ANSWERED__VALUE_MEASURED"


def is_question(goal: str) -> bool:
    """True when the goal asks to be TOLD something rather than to be GIVEN a file.

    Delegated to computer_env_v1.query_kind, which owns that classification and
    already refuses goals that name two quantities at once.
    """
    from canonical.runtime import computer_env_v1 as cenv
    return cenv.query_kind(str(goal or "")) is not None


def answer(goal: str, input_file: str | pathlib.Path | None = None,
           **kw: Any) -> dict[str, Any]:
    """Answer the goal if it is a question about a real file. Never claims an artifact.

    `answered` is the field to read. `closed` is present for symmetry and is ALWAYS
    False, because no file was produced; making it True would put a number on the
    artifact path.
    """
    from canonical.runtime import computer_env_v1 as cenv

    goal = str(goal or "")
    if not is_question(goal):
        return {"schema": SCHEMA, "answered": False, "closed": False,
                "status": "NOT_A_QUESTION"}

    src = pathlib.Path(input_file) if input_file is not None else _input_from_goal(goal)
    if src is None or not src.is_file():
        return {"schema": SCHEMA, "answered": False, "closed": False,
                "status": "OPEN__NO_EXISTING_INPUT_FILE_IN_GOAL",
                "detail": "a question about a file needs the file"}

    got = cenv.answer_query(goal, src, **kw)
    ok = bool(got.get("pass") or got.get("answered"))
    out = {
        "schema": SCHEMA,
        "answered": ok,
        "closed": False,                      # a value is not an artifact
        "status": _ANSWERED if ok else str(got.get("status") or "OPEN__UNANSWERED"),
        "value": got.get("value"),
        "answer": got.get("answer"),
        "kind": cenv.query_kind(goal),
        "input": str(src),
        "verification": got.get("verification"),
    }
    if not ok:
        out["detail"] = got.get("detail") or got.get("status")
    return out


def _input_from_goal(goal: str) -> pathlib.Path | None:
    """The file the goal names, if it names one that exists."""
    import re
    for tok in re.findall(r"[A-Za-z0-9_][A-Za-z0-9_./-]*\.[A-Za-z0-9_]{1,8}", goal):
        p = pathlib.Path(tok)
        if p.is_file():
            return p
    return None


def route(goal: str, input_file: str | pathlib.Path | None = None,
          **kw: Any) -> dict[str, Any]:
    """One entry point: answer a question, or say plainly that this is not one.

    This is the function a curriculum or a door should call INSTEAD of asking
    discover() to do something it cannot do.
    """
    if not is_question(goal):
        return {"schema": SCHEMA, "answered": False, "closed": False,
                "status": "NOT_A_QUESTION",
                "detail": "this goal asks for an artifact; use discover()"}
    return answer(goal, input_file, **kw)
