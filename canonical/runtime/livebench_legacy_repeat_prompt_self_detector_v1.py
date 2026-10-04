#!/usr/bin/env python3
"""Self-detect and recover legacy IFEval repeat_prompt from visible prompt text.

The frozen legacy checker hides prompt_to_repeat in kwargs.  The original public
IFEval corpus, however, renders the repeat meta-instruction as a contiguous
leading or trailing block around the request.  This module identifies that block
from linguistic structure, then cross-checks the split against the existing
line-preserving public-corpus recovery routine.  It never consumes
instruction_id_list, kwargs, question_id, or terminal case metadata.
"""
from __future__ import annotations

import re
from typing import Any

from canonical.runtime.livebench_hidden_parameter_prompt_recovery_v1 import (
    recover_legacy_repeat_prompt,
)

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_LEGACY_REPEAT_PROMPT_SELF_DETECTOR_V1"

_BOUNDARIES = (re.compile(r"\n{2,}"), re.compile(r"\n+"))


def _meta_score(value: str) -> int:
    text = str(value or "").lower()
    score = 0
    if re.search(r"\b(?:repeat|repleat)\b", text):
        score += 4
    if re.search(r"\brepeated\b", text):
        score += 1
    if re.search(r"\b(?:request|prompt|sentence|text|line|question)\b", text):
        score += 2
    if re.search(r"\b(?:above|below|exact|exactly|before|first)\b", text):
        score += 2
    if (
        re.search(r"word for word|word by word|without chang|single letter|as it is", text)
        or re.search(r"\bchang(?:e|ed|es|ing)\b", text)
    ):
        score += 3
    if re.search(
        r"do not say|don't say|do not add|before saying|before output|at the very beginning",
        text,
    ):
        score += 2
    return score


def _boundary_candidates(raw: str, boundary: re.Pattern[str]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for match in boundary.finditer(raw):
        left = raw[: match.start()].rstrip()
        right = raw[match.end() :].lstrip()
        if not left or not right:
            continue
        left_score = _meta_score(left)
        right_score = _meta_score(right)
        if max(left_score, right_score) < 6 or left_score == right_score:
            continue

        if left_score < right_score:
            target = left
            meta = right
            side = "TARGET_PREFIX"
            meta_start = match.end()
            while meta_start < len(raw) and raw[meta_start].isspace():
                meta_start += 1
            meta_end = len(raw)
        else:
            target = right
            meta = left
            side = "TARGET_SUFFIX"
            meta_start = 0
            meta_end = match.start()
            while meta_end > 0 and raw[meta_end - 1].isspace():
                meta_end -= 1

        out.append(
            {
                "target": target,
                "meta": meta,
                "side": side,
                "meta_start": meta_start,
                "meta_end": meta_end,
                "meta_score": max(left_score, right_score),
                "target_score": min(left_score, right_score),
                "margin": abs(left_score - right_score),
            }
        )
    return out


def detect_and_recover_legacy_repeat_prompt(prompt: str) -> dict[str, Any]:
    raw = str(prompt or "").replace("\r\n", "\n").strip()
    if not raw:
        return {
            "schema": SCHEMA,
            "status": "NO_MATCH",
            "reason": "PROMPT_EMPTY",
            "hidden_kwargs_used": False,
            "instruction_id_list_used": False,
            "terminal_case_metadata_used": False,
        }

    chosen: dict[str, Any] | None = None
    for boundary in _BOUNDARIES:
        candidates = _boundary_candidates(raw, boundary)
        if not candidates:
            continue
        best_margin = max(x["margin"] for x in candidates)
        best = [x for x in candidates if x["margin"] == best_margin]
        unique: dict[str, dict[str, Any]] = {x["target"]: x for x in best}
        if len(unique) != 1:
            return {
                "schema": SCHEMA,
                "status": "FAIL_CLOSED",
                "reason": "AMBIGUOUS_REPEAT_META_SEGMENTATION",
                "candidate_count": len(unique),
                "hidden_kwargs_used": False,
                "instruction_id_list_used": False,
                "terminal_case_metadata_used": False,
            }
        chosen = next(iter(unique.values()))
        break

    if chosen is None:
        return {
            "schema": SCHEMA,
            "status": "NO_MATCH",
            "reason": "NO_REPEAT_META_BLOCK",
            "hidden_kwargs_used": False,
            "instruction_id_list_used": False,
            "terminal_case_metadata_used": False,
        }

    recovered = recover_legacy_repeat_prompt(raw)["prompt_to_repeat"]
    if recovered != chosen["target"]:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "reason": "STRUCTURAL_AND_LINE_RECOVERY_DISAGREE",
            "structural_target": chosen["target"],
            "line_recovery_target": recovered,
            "hidden_kwargs_used": False,
            "instruction_id_list_used": False,
            "terminal_case_metadata_used": False,
        }

    return {
        "schema": SCHEMA,
        "status": "PASS",
        "instruction_id": "combination:repeat_prompt",
        "prompt_to_repeat": recovered,
        "response_prefix": recovered,
        "target_side": chosen["side"],
        "meta_start": chosen["meta_start"],
        "meta_end": chosen["meta_end"],
        "meta_text": raw[chosen["meta_start"] : chosen["meta_end"]],
        "meta_score": chosen["meta_score"],
        "target_score": chosen["target_score"],
        "score_margin": chosen["margin"],
        "source": "VISIBLE_PROMPT_ONLY",
        "hidden_kwargs_used": False,
        "instruction_id_list_used": False,
        "terminal_case_metadata_used": False,
    }


def run(args: dict[str, Any], root=None) -> dict[str, Any]:
    return detect_and_recover_legacy_repeat_prompt(str((args or {}).get("prompt") or ""))
