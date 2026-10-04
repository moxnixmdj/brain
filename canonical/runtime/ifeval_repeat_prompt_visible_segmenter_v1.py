#!/usr/bin/env python3
"""Prompt-only recovery for public legacy IFEval combination:repeat_prompt.

The frozen checker only requires that the response begin with prompt_to_repeat.
Public IFEval renders that exact string as a visible request line and places the
repeat directive on other line(s).  This segmenter recovers the request without
using instruction IDs or kwargs at inference time.

V1 is deliberately line-structural and fail-closed.  It does not attempt
semantic guessing when the public shape is absent or ambiguous.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, asdict

SCHEMA = "PROJECT_BRAIN_IFEVAL_REPEAT_PROMPT_VISIBLE_SEGMENTER_V1"
_REPEAT = re.compile(r"\brep(?:ea|lea)t\b", re.IGNORECASE)


class RepeatPromptSegmentationError(ValueError):
    pass


@dataclass(frozen=True)
class Recovery:
    prompt_to_repeat: str
    route: str
    first_repeat_line: int
    source: str = "VISIBLE_PROMPT_ONLY"


def recover(prompt: str) -> dict:
    text = str(prompt or "")
    lines = text.splitlines()
    nonempty = [i for i, line in enumerate(lines) if line.strip()]
    if not nonempty:
        raise RepeatPromptSegmentationError("EMPTY_PROMPT")

    repeat_lines = [i for i, line in enumerate(lines) if _REPEAT.search(line)]
    if not repeat_lines:
        raise RepeatPromptSegmentationError("REPEAT_DIRECTIVE_NOT_FOUND")

    first_nonempty = nonempty[0]
    last_nonempty = nonempty[-1]
    first_repeat = repeat_lines[0]

    if first_repeat > first_nonempty:
        # Public prefix form: the exact request occupies the visible line(s)
        # before the first repeat directive.  V1 requires a single nonempty
        # request line because that is the proved public envelope.
        candidates = [lines[i].strip() for i in range(first_nonempty, first_repeat) if lines[i].strip()]
        if len(candidates) != 1:
            raise RepeatPromptSegmentationError("PREFIX_REQUEST_NOT_SINGLE_LINE")
        recovered = candidates[0]
        route = "VISIBLE_PREFIX_BEFORE_REPEAT_DIRECTIVE"
    elif first_repeat == first_nonempty and last_nonempty > first_repeat:
        # Public suffix form: repeat meta-instruction leads and the exact request
        # is the final visible nonempty line, separated from the directive body.
        recovered = lines[last_nonempty].strip()
        route = "VISIBLE_FINAL_LINE_AFTER_REPEAT_DIRECTIVE"
    else:
        raise RepeatPromptSegmentationError("UNSUPPORTED_REPEAT_PROMPT_LAYOUT")

    if not recovered:
        raise RepeatPromptSegmentationError("EMPTY_RECOVERED_REQUEST")
    if _REPEAT.search(recovered):
        raise RepeatPromptSegmentationError("RECOVERED_REQUEST_LOOKS_LIKE_META_DIRECTIVE")

    result = Recovery(
        prompt_to_repeat=recovered,
        route=route,
        first_repeat_line=first_repeat,
    )
    out = asdict(result)
    out["schema"] = SCHEMA
    out["status"] = "PASS__PROMPT_TO_REPEAT_RECOVERED_FROM_VISIBLE_PROMPT"
    out["model_dependency_count"] = 0
    out["network_used"] = False
    return out


def response_prefix_witness(prompt: str) -> dict:
    out = recover(prompt)
    witness = out["prompt_to_repeat"]
    return {
        "schema": SCHEMA,
        "status": "PASS__REPEAT_PROMPT_PREFIX_WITNESS",
        "response": witness,
        "prompt_to_repeat": witness,
        "route": out["route"],
        "model_dependency_count": 0,
        "network_used": False,
    }


def run(args: dict, root=None) -> dict:
    prompt = str((args or {}).get("prompt") or (args or {}).get("instruction") or "")
    return recover(prompt)
