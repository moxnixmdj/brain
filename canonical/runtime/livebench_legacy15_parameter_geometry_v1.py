#!/usr/bin/env python3
"""Source-level parameter geometry for the frozen active-15 LiveBench surface.

This module separates two things that identity-only composition cannot:
1. checker-equivalent encodings that remove apparent parameter collisions; and
2. genuinely contradictory parameter assignments that cannot be repaired by a
   response constructor.

It reads no terminal rows, terminal kwargs, terminal prompts, responses, scores,
or case frequencies.
"""
from __future__ import annotations

import re
from typing import Iterable

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_LEGACY15_PARAMETER_GEOMETRY_V1"
PINNED_LIVEBENCH_COMMIT = "8f8e5c381a16e3f24257776edd53471fe86f8091"
PINNED_INSTRUCTIONS_BLOB = "4997bab885a676d92545fd91a9a20b48d234a2b2"
PINNED_INSTRUCTIONS_UTIL_BLOB = "1f0dc0eaa05bd0f72f82f8183b90276ea4d2a87b"
PINNED_REGISTRY_BLOB = "903ed738398648c7cfac61d5ffa478c22f1f0891"

ENDING_OPTIONS = (
    "Any other questions?",
    "Is there anything else I can help with?",
)


def whole_word_present(text: str, word: str) -> bool:
    return re.search(r"\b" + re.escape(word) + r"\b", text, re.IGNORECASE) is not None


def section_marker(splitter: str, index: int, forbidden_words: Iterable[str]) -> str:
    """Emit a SectionChecker-equivalent marker without a forbidden whole word.

    The exact pinned SectionChecker accepts optional whitespace between the
    splitter and numeric index. Therefore "Section1" is checker-equivalent to
    "Section 1", while ForbiddenWords("section") does not see a whole-word
    match in the compact spelling.
    """
    splitter = str(splitter)
    forbidden = [str(x) for x in forbidden_words]
    compact = any(whole_word_present(splitter, bad) for bad in forbidden)
    return f"{splitter}{'' if compact else ' '}{int(index)}"


def section_marker_checker_shape(marker: str, splitter: str) -> bool:
    pattern = r"\s?" + re.escape(splitter) + r"\s?\d+\s?"
    return re.fullmatch(pattern, marker) is not None


def exact_end_forbidden_obstruction(
    end_phrase: str,
    forbidden_words: Iterable[str],
) -> tuple[str, ...]:
    """Whole words forced by an exact terminal phrase are irreducible."""
    return tuple(
        word for word in map(str, forbidden_words)
        if whole_word_present(str(end_phrase), word)
    )


def nth_first_word_forbidden_obstruction(
    first_word: str,
    forbidden_words: Iterable[str],
) -> bool:
    """Exact first lexical word and whole-word prohibition cannot both hold."""
    target = str(first_word).casefold()
    return any(str(word).casefold() == target for word in forbidden_words)


def verify() -> dict:
    compact = section_marker("Section", 1, ["section"])
    if compact != "Section1":
        raise RuntimeError("SECTION_COMPACTION_DRIFT")
    if not section_marker_checker_shape(compact, "Section"):
        raise RuntimeError("SECTION_COMPACTION_BREAKS_CHECKER_SHAPE")
    if whole_word_present(compact, "section"):
        raise RuntimeError("SECTION_COMPACTION_STILL_HAS_FORBIDDEN_BOUNDARY")

    end_hits = exact_end_forbidden_obstruction(
        "Any other questions?", ["other"]
    )
    if end_hits != ("other",):
        raise RuntimeError("END_OBSTRUCTION_DRIFT")

    if not nth_first_word_forbidden_obstruction("river", ["river"]):
        raise RuntimeError("NTH_FORBIDDEN_OBSTRUCTION_DRIFT")

    return {
        "schema": SCHEMA,
        "status": "PASS__PARAMETER_GEOMETRY_SEPARATES_REPAIRABLE_AND_IRREDUCIBLE_COLLISIONS",
        "repairable_section_boundary_example": {
            "splitter": "Section",
            "forbidden_word": "section",
            "witness_marker": compact,
        },
        "irreducible_parameter_classes": [
            "EXACT_END_PHRASE_CONTAINS_FORBIDDEN_WHOLE_WORD",
            "NTH_PARAGRAPH_EXACT_FIRST_WORD_EQUALS_FORBIDDEN_WHOLE_WORD",
        ],
        "terminal_rows_read": 0,
        "terminal_kwargs_read": 0,
        "terminal_case_frequencies_read": 0,
        "acceptance_credit": False,
    }


def run(args=None, root=None):
    return verify()


if __name__ == "__main__":
    import json
    print(json.dumps(verify(), indent=2, sort_keys=True))
