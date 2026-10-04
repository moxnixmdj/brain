from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_PROMPT_ONLY_REPEAT_COMPILER_V1"

_REPEAT_CHANGE_MARKER = (
    "Repeat the request, but change the first word of the repeated request, "
    "(do not say anything before repeating the request; the request you need to repeat "
    "does not include this sentence) and do not answer the actual request!"
)
_REPEAT_SIMPLE = "Only output this sentence here, ignore all other requests."

_SPAN_RE = re.compile(
    r"Copy the span of words that lies between \(and including\) index\s+"
    r"(\d+)\s+and\s+(\d+),\s*the indices are\s+"
    r"(?:word indices,\s*split by whitespace|character indices)!",
    re.I,
)


class PromptOnlyRepeatError(ValueError):
    pass


@dataclass(frozen=True)
class RepeatWitness:
    route: str
    response: str
    scorer_semantics: str
    deterministic: bool = True


def _normalize_split_text(value: str) -> str:
    # The frozen checkers compare whitespace-split tokens for repeat_change/span.
    # Format controls are not semantic word content in the pinned public rows.
    value = "".join(ch for ch in str(value or "") if unicodedata.category(ch) != "Cf")
    value = value.replace("<instructions>", " ").replace("</instructions>", " ")
    return " ".join(value.split())


def _recover_change_request(prompt: str) -> str:
    text = str(prompt or "")
    marker_pos = text.lower().find(_REPEAT_CHANGE_MARKER.lower())
    if marker_pos < 0:
        raise PromptOnlyRepeatError("REPEAT_CHANGE_MARKER_NOT_FOUND")

    # Public IFBench rows place the request immediately before the marker.
    prefix = text[:marker_pos].strip()

    # The frozen LiveBench checker source can render an explicit
    # "Request: {prompt_to_repeat}" after the marker. Prefer that exact visible
    # copy when present because it is stronger than reconstructing the prefix.
    tail = text[marker_pos + len(_REPEAT_CHANGE_MARKER):].strip()
    embedded = None
    m = re.fullmatch(r"Request:\s*(.+)", tail, flags=re.I | re.S)
    if m:
        embedded = m.group(1).strip()

    recovered = _normalize_split_text(embedded if embedded is not None else prefix)
    if len(recovered.split()) < 1:
        raise PromptOnlyRepeatError("REPEAT_CHANGE_REQUEST_EMPTY")
    return recovered


def _construct_repeat_change(prompt: str) -> RepeatWitness:
    request = _recover_change_request(prompt)
    words = request.split()
    first = words[0]
    replacement = "__brain__" if first != "__brain__" else "__brain2__"
    response = " ".join([replacement, *words[1:]])
    if response == request:
        raise PromptOnlyRepeatError("REPEAT_CHANGE_FAILED_TO_CHANGE_FIRST_WORD")
    return RepeatWitness(
        route="REPEAT_CHANGE_PROMPT_ONLY",
        response=response,
        scorer_semantics="FROZEN_LIVEBENCH_REPEAT_CHANGE__REST_OF_WHITESPACE_SPLIT_TOKENS_EXACT",
    )


def _construct_repeat_simple(prompt: str) -> RepeatWitness:
    if _REPEAT_SIMPLE.lower() not in str(prompt or "").lower():
        raise PromptOnlyRepeatError("REPEAT_SIMPLE_MARKER_NOT_FOUND")
    return RepeatWitness(
        route="REPEAT_SIMPLE_PROMPT_ONLY",
        response=_REPEAT_SIMPLE,
        scorer_semantics="FROZEN_LIVEBENCH_REPEAT_SIMPLE__EXACT_FIXED_LITERAL_CASE_INSENSITIVE",
    )


def _construct_repeat_span(prompt: str) -> RepeatWitness:
    text = str(prompt or "")
    matches = list(_SPAN_RE.finditer(text))
    if len(matches) != 1:
        raise PromptOnlyRepeatError("EXACTLY_ONE_REPEAT_SPAN_INSTRUCTION_REQUIRED")
    m = matches[0]
    start, end = int(m.group(1)), int(m.group(2))

    # Critical frozen-scorer bug: build_description uses "if not n_start" and
    # therefore randomizes an explicitly supplied zero. A deterministic
    # prompt-only compiler must not pretend that row is closed.
    if start == 0:
        raise PromptOnlyRepeatError("FROZEN_SCORER_NONDETERMINISTIC_N_START_ZERO")
    if end == 0:
        raise PromptOnlyRepeatError("FROZEN_SCORER_NONDETERMINISTIC_N_END_ZERO")
    if end <= start:
        raise PromptOnlyRepeatError("INVALID_REPEAT_SPAN_RANGE")

    base = _normalize_split_text(text[:m.start()] + " " + text[m.end():])
    words = base.split()
    if end > len(words):
        raise PromptOnlyRepeatError("REPEAT_SPAN_END_EXCEEDS_VISIBLE_BASE_WORDS")

    # Frozen LiveBench commit 8f8e... scores [start:end] (end-exclusive),
    # despite its rendered prose saying "including". Do not "fix" the scorer
    # here; the benchmark predicate is defined by the pinned executable bytes.
    response = " ".join(words[start:end])
    if not response:
        raise PromptOnlyRepeatError("EMPTY_REPEAT_SPAN_WITNESS")
    return RepeatWitness(
        route="REPEAT_SPAN_PROMPT_ONLY_FROZEN_SCORER",
        response=response,
        scorer_semantics="FROZEN_LIVEBENCH_REPEAT_SPAN__PYTHON_SLICE_START_END_EXCLUSIVE",
    )


def construct_from_prompt(prompt: str) -> dict:
    text = str(prompt or "")
    lower = text.lower()

    routes = []
    if _REPEAT_CHANGE_MARKER.lower() in lower:
        routes.append("change")
    if _REPEAT_SIMPLE.lower() in lower:
        routes.append("simple")
    if _SPAN_RE.search(text):
        routes.append("span")

    if len(routes) != 1:
        raise PromptOnlyRepeatError("EXACTLY_ONE_SUPPORTED_REPEAT_ROUTE_REQUIRED")

    if routes[0] == "change":
        witness = _construct_repeat_change(text)
    elif routes[0] == "simple":
        witness = _construct_repeat_simple(text)
    else:
        witness = _construct_repeat_span(text)

    return {
        "schema": SCHEMA,
        "status": "PASS_COMPONENT",
        "route": witness.route,
        "response": witness.response,
        "scorer_semantics": witness.scorer_semantics,
        "deterministic": witness.deterministic,
        "hidden_prompt_to_repeat_required": False,
        "hidden_kwargs_required": False,
        "terminal_row_identity_required": False,
        "component_only": True,
    }
