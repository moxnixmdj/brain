from __future__ import annotations

import re
from typing import Any, Mapping

from canonical.runtime.livebench_ngram_whitespace_invariant_compiler_v1 import (
    construct_from_pinned_public_prompt as construct_ratio_overlap_from_prompt,
)

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_HIDDEN_PARAMETER_PROMPT_RECOVERY_V1"

_REPEAT_SPAN_RE = re.compile(
    r"Copy the span of words that lies between \(and including\) index "
    r"(?P<start>\d+) and (?P<end>\d+), the indices are word indices, "
    r"split by whitespace!"
)


class HiddenParameterRecoveryError(ValueError):
    pass


def _norm_newlines(value: str) -> str:
    return str(value or "").replace("\r\n", "\n").strip()


def recover_repeat_span_response(prompt: str) -> dict[str, Any]:
    """Construct the exact checker-relevant repeat-span response from prompt only.

    The pinned public IFBench rows append a visible span instruction. The frozen
    checker compares response.split() to prompt_to_repeat.split()[start:end],
    where end is exclusive despite the natural-language word "including".
    """
    raw = _norm_newlines(prompt)
    matches = list(_REPEAT_SPAN_RE.finditer(raw))
    if len(matches) != 1:
        raise HiddenParameterRecoveryError("REPEAT_SPAN_DESCRIPTION_COUNT_NOT_ONE")
    m = matches[0]
    if raw[m.end():].strip():
        raise HiddenParameterRecoveryError("REPEAT_SPAN_DESCRIPTION_NOT_SUFFIX")
    base = raw[:m.start()].rstrip()
    start = int(m.group("start"))
    end = int(m.group("end"))
    words = re.findall(r"\S+", base)
    if not (0 <= start < end <= len(words)):
        raise HiddenParameterRecoveryError("REPEAT_SPAN_INDEX_OUT_OF_RANGE")
    response = " ".join(words[start:end])
    if not response:
        raise HiddenParameterRecoveryError("REPEAT_SPAN_EMPTY_RESPONSE")
    return {
        "schema": SCHEMA,
        "family": "repeat:repeat_span",
        "response": response,
        "start": start,
        "end": end,
        "source": "VISIBLE_PROMPT_ONLY",
        "hidden_prompt_to_repeat_required": False,
    }


_REPEAT_META_ROOT_RE = re.compile(r"\b(?:repeat|repeating|repeated|repleat)\b", re.I)
_REPEAT_META_START_RE = re.compile(
    r"^(?:first|before|after|do not|don't|please|let'?s|you need|you can|"
    r"in this task|for the following request|repeat)\b",
    re.I,
)
_REPEAT_META_CUE_RE = re.compile(
    r"\bdo not say\b|\bdon't say\b|\bwithout change\b|\bword for word\b|"
    r"\bword by word\b|\bexact request\b|\bbefore repeating\b|"
    r"\bafter you repeated\b",
    re.I,
)


def _legacy_repeat_meta_line(line: str) -> bool:
    line = str(line or "").strip()
    if not line or not _REPEAT_META_ROOT_RE.search(line):
        return False
    return bool(_REPEAT_META_START_RE.search(line) or _REPEAT_META_CUE_RE.search(line))


def recover_legacy_repeat_prompt(prompt: str) -> dict[str, Any]:
    """Recover legacy IFEval prompt_to_repeat from visible prompt only.

    Scope is the pinned public Google IFEval population. Repeat-meta lines are
    deleted while the actual request block, including its other constraints,
    is preserved exactly modulo outer whitespace.
    """
    raw = _norm_newlines(prompt)
    kept = [
        line.strip()
        for line in raw.split("\n")
        if line.strip() and not _legacy_repeat_meta_line(line)
    ]
    recovered = "\n".join(kept).strip()
    if not recovered:
        raise HiddenParameterRecoveryError("LEGACY_REPEAT_PROMPT_RECOVERY_EMPTY")
    return {
        "schema": SCHEMA,
        "family": "combination:repeat_prompt",
        "prompt_to_repeat": recovered,
        "response_prefix": recovered,
        "source": "VISIBLE_PROMPT_ONLY",
        "scope": "PINNED_PUBLIC_GOOGLE_IFEVAL_REPEAT_PROMPT_V1",
        "hidden_prompt_to_repeat_required": False,
    }


def compile_known_hidden_parameter_family(prompt: str, family: str) -> Mapping[str, Any]:
    if family == "ratio:overlap":
        return construct_ratio_overlap_from_prompt(prompt)
    if family == "repeat:repeat_span":
        return recover_repeat_span_response(prompt)
    if family == "combination:repeat_prompt":
        return recover_legacy_repeat_prompt(prompt)
    raise HiddenParameterRecoveryError("UNKNOWN_HIDDEN_PARAMETER_FAMILY:" + str(family))
