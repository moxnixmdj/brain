from __future__ import annotations

import ast
import re
from typing import Any, Mapping

from canonical.runtime import livebench_legacy15_composition_archetypes_v1 as archetypes

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_LEGACY15_VISIBLE_PROMPT_COMPILER_V1"
PINNED_GENERATOR_BLOB = "6ff390d6885cf90f88d9d36959735cb327613edc"
PINNED_INSTRUCTIONS_BLOB = "4997bab885a676d92545fd91a9a20b48d234a2b2"

TASK_PROMPTS = (
    "Please paraphrase based on the sentences provided.",
    "Please summarize based on the sentences provided.",
    "Please explain in simpler terms what this text means.",
    "Please generate a story based on the sentences provided.",
)

EXIST = "keywords:existence"
FORBIDDEN = "keywords:forbidden_words"
PARAGRAPHS = "length_constraints:number_paragraphs"
WORDS = "length_constraints:number_words"
SENTENCES = "length_constraints:number_sentences"
NTH = "length_constraints:nth_paragraph_first_word"
POSTSCRIPT = "detectable_content:postscript"
BULLETS = "detectable_format:number_bullet_lists"
TITLE = "detectable_format:title"
SECTIONS = "detectable_format:multiple_sections"
JSON_ID = "detectable_format:json_format"
REPEAT = "combination:repeat_prompt"
TWO = "combination:two_responses"
END = "startend:end_checker"
QUOTE = "startend:quotation"

REPEAT_MARKER = "First repeat the request word for word without change,"


class PromptCompileError(ValueError):
    pass


def _literal_word_list(raw: str) -> list[str]:
    try:
        value = ast.literal_eval(raw)
    except (SyntaxError, ValueError) as exc:
        raise PromptCompileError("KEYWORD_LIST_LITERAL_PARSE_FAILED") from exc
    if not isinstance(value, list) or len(value) != 5:
        raise PromptCompileError("KEYWORD_LIST_NOT_EXACTLY_FIVE")
    words = [str(x) for x in value]
    if len(set(words)) != 5 or any(
        re.fullmatch(r"[A-Za-z]+", x) is None for x in words
    ):
        raise PromptCompileError("KEYWORD_LIST_OUTSIDE_PUBLIC_DOMAIN")
    return words


def _fixed(iid: str, text: str):
    return (
        iid,
        re.compile(r"(?:^| )" + re.escape(text) + r"$", re.DOTALL),
        lambda m: {},
    )


_SPECS = [
    (
        EXIST,
        re.compile(
            r"(?:^| )Include keywords (?P<items>\[[^\r\n]*\]) in the response\.$",
            re.DOTALL,
        ),
        lambda m: {"keywords": _literal_word_list(m.group("items"))},
    ),
    (
        FORBIDDEN,
        re.compile(
            r"(?:^| )Do not include keywords (?P<items>\[[^\r\n]*\]) in the response\.$",
            re.DOTALL,
        ),
        lambda m: {"forbidden_words": _literal_word_list(m.group("items"))},
    ),
    (
        PARAGRAPHS,
        re.compile(
            r"(?:^| )There should be (?P<n>[1-5]) paragraphs\. "
            r"Paragraphs are separated with the markdown divider: \*\*\*$",
            re.DOTALL,
        ),
        lambda m: {"num_paragraphs": int(m.group("n"))},
    ),
    (
        WORDS,
        re.compile(
            r"(?:^| )Answer with (?P<relation>less than|at least) "
            r"(?P<n>[1-9][0-9]{2}) words\.$",
            re.DOTALL,
        ),
        lambda m: {
            "num_words": int(m.group("n")),
            "relation": m.group("relation"),
        },
    ),
    (
        SENTENCES,
        re.compile(
            r"(?:^| )Your response should contain "
            r"(?P<relation>less than|at least) "
            r"(?P<n>[1-9]|1[0-9]|20) sentences\.$",
            re.DOTALL,
        ),
        lambda m: {
            "num_sentences": int(m.group("n")),
            "relation": m.group("relation"),
        },
    ),
    (
        NTH,
        re.compile(
            r"(?:^| )There should be (?P<p>[1-5]) paragraphs\. "
            r"Paragraphs and only paragraphs are separated with each other by two "
            r"new lines as if it was '\\n\\n' in python\. "
            r"Paragraph (?P<k>[1-5]) must start with word "
            r"(?P<word>[A-Za-z]+)\.$",
            re.DOTALL,
        ),
        lambda m: {
            "num_paragraphs": int(m.group("p")),
            "nth_paragraph": int(m.group("k")),
            "first_word": m.group("word"),
        },
    ),
    (
        POSTSCRIPT,
        re.compile(
            r"(?:^| )At the end of your response, please explicitly add a "
            r"postscript starting with (?P<marker>P\.S\.|P\.P\.S)$",
            re.DOTALL,
        ),
        lambda m: {"postscript_marker": m.group("marker")},
    ),
    (
        BULLETS,
        re.compile(
            r"(?:^| )Your answer must contain exactly (?P<n>[1-5]) bullet "
            r"points\. Use the markdown bullet points such as:\n"
            r"\* This is point 1\. \n"
            r"\* This is point 2$",
            re.DOTALL,
        ),
        lambda m: {"num_bullets": int(m.group("n"))},
    ),
    _fixed(
        TITLE,
        "Your answer must contain a title, wrapped in double angular brackets, "
        "such as <<poem of joy>>.",
    ),
    (
        SECTIONS,
        re.compile(
            r"(?:^| )Your response must have (?P<n>[1-5]) sections\. Mark the "
            r"beginning of each section with (?P<s>Section|SECTION) X, such as:\n"
            r"(?P=s) 1\n"
            r"\[content of section 1\]\n"
            r"(?P=s) 2\n"
            r"\[content of section 2\]$",
            re.DOTALL,
        ),
        lambda m: {
            "section_spliter": m.group("s"),
            "num_sections": int(m.group("n")),
        },
    ),
    _fixed(
        JSON_ID,
        "Entire output should be wrapped in JSON format. You can use markdown "
        "ticks such as " + "\x60\x60\x60" + ".",
    ),
    _fixed(
        REPEAT,
        "First repeat the request word for word without change, then give your "
        "answer (1. do not say any words or characters before repeating the "
        "request; 2. the request you need to repeat does not include this sentence)",
    ),
    _fixed(
        TWO,
        "Give two different responses. Responses and only responses should be "
        "separated by 6 asterisk symbols: ******.",
    ),
    (
        END,
        re.compile(
            r"(?:^| )Finish your response with this exact phrase "
            r"(?P<phrase>Any other questions\?|"
            r"Is there anything else I can help with\?)"
            r"\. No other words should follow this phrase\.$",
            re.DOTALL,
        ),
        lambda m: {"end_phrase": m.group("phrase")},
    ),
    _fixed(
        QUOTE,
        "Wrap your entire response with double quotation marks.",
    ),
]


def _validate_slots(iid: str, slots: Mapping[str, Any]) -> None:
    if iid == WORDS and not 100 <= int(slots["num_words"]) <= 500:
        raise PromptCompileError("WORD_THRESHOLD_OUTSIDE_PUBLIC_DOMAIN")
    if iid == NTH and not (
        1
        <= int(slots["nth_paragraph"])
        <= int(slots["num_paragraphs"])
        <= 5
    ):
        raise PromptCompileError("NTH_PARAGRAPH_OUTSIDE_PUBLIC_DOMAIN")


def compile_visible_prompt(prompt: str) -> dict[str, Any]:
    text = str(prompt)
    cursor = len(text)
    reverse_contracts: list[dict[str, Any]] = []
    spans: list[tuple[int, int, str]] = []

    for _ in range(archetypes.MAX_GENERATED_INSTRUCTIONS):
        prefix = text[:cursor]
        matches = []
        for iid, regex, slot_builder in _SPECS:
            match = regex.search(prefix)
            if match is not None:
                matches.append((iid, match, slot_builder))
        if not matches:
            break
        if len(matches) != 1:
            raise PromptCompileError("AMBIGUOUS_DESCRIPTOR_SUFFIX")

        iid, match, slot_builder = matches[0]
        slots = dict(slot_builder(match))
        _validate_slots(iid, slots)
        reverse_contracts.append(
            {
                "instruction_id": iid,
                "slots": slots,
                "parameter_complete": iid != REPEAT,
            }
        )
        spans.append((match.start(), match.end(), iid))
        cursor = match.start()

    if not reverse_contracts:
        raise PromptCompileError("NO_ACTIVE15_DESCRIPTOR_SUFFIX")

    remainder = text[:cursor]
    if not any(remainder.endswith(task + " ") for task in TASK_PROMPTS):
        raise PromptCompileError(
            "SUFFIX_DID_NOT_TERMINATE_AT_HISTORICAL_TASK_PROMPT"
        )

    contracts = list(reversed(reverse_contracts))
    ids = tuple(c["instruction_id"] for c in contracts)
    if len(ids) != len(set(ids)):
        raise PromptCompileError("DUPLICATE_ACTIVE15_DESCRIPTOR")
    if not archetypes.compatible(ids):
        raise PromptCompileError("INCOMPATIBLE_OR_OUTSIDE_ACTIVE15_SCOPE")

    if REPEAT in ids:
        # Historical generator semantics are split(...)[0], not an occurrence
        # anchored to the repeat descriptor. Mirror that exactly, including the
        # pathological case where article text itself contains the marker.
        repeat_prefix = text.split(REPEAT_MARKER, 1)[0]
        for contract in contracts:
            if contract["instruction_id"] == REPEAT:
                contract["slots"] = {"prompt_to_repeat": repeat_prefix}
                contract["parameter_complete"] = True
                break

    if any(not c["parameter_complete"] for c in contracts):
        raise PromptCompileError("PARAMETER_INCOMPLETE")

    return {
        "schema": SCHEMA,
        "status": "PASS__VISIBLE_ACTIVE15_CONTRACTS_COMPILED",
        "contracts": contracts,
        "instruction_ids": [c["instruction_id"] for c in contracts],
        "descriptor_count": len(contracts),
        "descriptor_suffix_start": cursor,
        "descriptor_spans_reverse": [
            {"start": start, "end": end, "instruction_id": iid}
            for start, end, iid in spans
        ],
        "source_binding": {
            "historical_generator_blob": PINNED_GENERATOR_BLOB,
            "instructions_blob": PINNED_INSTRUCTIONS_BLOB,
        },
        "terminal_rows_used": False,
        "hidden_kwargs_used": False,
        "acceptance_credit": False,
    }


def run(args: Mapping[str, Any] | None = None, root=None) -> dict[str, Any]:
    args = args or {}
    prompt = args.get("prompt")
    if not isinstance(prompt, str):
        raise PromptCompileError("PROMPT_STRING_REQUIRED")
    return compile_visible_prompt(prompt)
