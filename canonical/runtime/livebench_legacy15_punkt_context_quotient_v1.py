#!/usr/bin/env python3
"""Finite Punkt-context quotient for frozen LiveBench Active15.

After the parametric non-sentence reduction, sentence correctness depends only
on sentence-boundary-relevant material emitted by the deterministic composer.

All omitted generated variability is punctuation-neutral at the only places
where it can affect Punkt:
- existence/forbidden public words are ASCII alphabetic and appear before the
  sentence scaffold (or do not emit text);
- title, sections, bullets and their counts introduce no '.', '?' or '!';
- NTH first-word identity is ASCII alphabetic and occurs before the scaffold;
- NTH location matters only by whether punctuation-free trailing paragraphs
  follow the last generated sentence;
- WORDS less-than/absent adds no suffix, while WORDS at-least always pads because
  the independently proved unpadded upper bound is < public minimum 100; the
  number of pad tokens is irrelevant because every token is punctuation-free;
- postscript and end-phrase are the only generated suffixes containing sentence
  punctuation; quotation can change Punkt boundary context and remains explicit.

Thus the raw slot Cartesian product maps to a finite quotient over five context
coordinates plus the sentence relation/threshold.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from itertools import product
from typing import Any, Iterable, Mapping, Sequence

from canonical.runtime import livebench_legacy15_composition_archetypes_v1 as arch
from canonical.runtime import livebench_legacy15_contract_composer_v2 as comp
from canonical.runtime import livebench_post_sacrifice_parametric_reduction_v1 as reduction

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_LEGACY15_PUNKT_CONTEXT_QUOTIENT_V1"

NTH_MODES = ("ABSENT", "TARGET_LAST", "TRAILING_PARAGRAPH")
WORD_MODES = ("ABSENT", "LESS_THAN", "AT_LEAST_PADDED")
POSTSCRIPT_MODES = ("ABSENT", "P.S.", "P.P.S")
END_MODES = (
    "ABSENT",
    "Any other questions?",
    "Is there anything else I can help with?",
)


@dataclass(frozen=True, order=True)
class PunktContext:
    nth_mode: str
    word_mode: str
    postscript_mode: str
    end_mode: str
    quotation: bool


def _modes_for_ids(ids: set[str]) -> Iterable[PunktContext]:
    nth = (
        ("TARGET_LAST", "TRAILING_PARAGRAPH")
        if comp.NTH in ids
        else ("ABSENT",)
    )
    words = (
        ("LESS_THAN", "AT_LEAST_PADDED")
        if comp.WORDS in ids
        else ("ABSENT",)
    )
    posts = (
        ("P.S.", "P.P.S")
        if comp.POSTSCRIPT in ids
        else ("ABSENT",)
    )
    ends = (
        (
            "Any other questions?",
            "Is there anything else I can help with?",
        )
        if comp.END in ids
        else ("ABSENT",)
    )
    quotes = (True,) if comp.QUOTE in ids else (False,)
    for values in product(nth, words, posts, ends, quotes):
        yield PunktContext(*values)


def reachable_contexts() -> tuple[PunktContext, ...]:
    out: set[PunktContext] = set()
    for ids_tuple in arch.enumerate_compatible_sets():
        ids = set(ids_tuple)
        if comp.SENTENCES not in ids:
            continue
        for context in _modes_for_ids(ids):
            out.add(context)
    return tuple(sorted(out))


def representative_contracts(
    context: PunktContext,
    *,
    relation: str,
    threshold: int,
) -> list[dict[str, Any]]:
    if relation not in {"less than", "at least"}:
        raise ValueError("UNSUPPORTED_SENTENCE_RELATION")
    if not 1 <= int(threshold) <= 20:
        raise ValueError("SENTENCE_THRESHOLD_OUTSIDE_PUBLIC_DOMAIN")

    contracts: list[dict[str, Any]] = [
        {
            "instruction_id": comp.SENTENCES,
            "slots": {
                "num_sentences": int(threshold),
                "relation": relation,
            },
        }
    ]

    if context.nth_mode == "TARGET_LAST":
        contracts.append({
            "instruction_id": comp.NTH,
            "slots": {
                "num_paragraphs": 2,
                "nth_paragraph": 2,
                "first_word": "river",
            },
        })
    elif context.nth_mode == "TRAILING_PARAGRAPH":
        contracts.append({
            "instruction_id": comp.NTH,
            "slots": {
                "num_paragraphs": 2,
                "nth_paragraph": 1,
                "first_word": "river",
            },
        })
    elif context.nth_mode != "ABSENT":
        raise ValueError("UNKNOWN_NTH_MODE")

    if context.word_mode == "LESS_THAN":
        contracts.append({
            "instruction_id": comp.WORDS,
            "slots": {
                "num_words": 100,
                "relation": "less than",
            },
        })
    elif context.word_mode == "AT_LEAST_PADDED":
        contracts.append({
            "instruction_id": comp.WORDS,
            "slots": {
                "num_words": 100,
                "relation": "at least",
            },
        })
    elif context.word_mode != "ABSENT":
        raise ValueError("UNKNOWN_WORD_MODE")

    if context.postscript_mode != "ABSENT":
        if context.postscript_mode not in {"P.S.", "P.P.S"}:
            raise ValueError("UNKNOWN_POSTSCRIPT_MODE")
        contracts.append({
            "instruction_id": comp.POSTSCRIPT,
            "slots": {"postscript_marker": context.postscript_mode},
        })

    if context.end_mode != "ABSENT":
        if context.end_mode not in END_MODES[1:]:
            raise ValueError("UNKNOWN_END_MODE")
        contracts.append({
            "instruction_id": comp.END,
            "slots": {"end_phrase": context.end_mode},
        })

    if context.quotation:
        contracts.append({
            "instruction_id": comp.QUOTE,
            "slots": {},
        })

    ids = tuple(c["instruction_id"] for c in contracts)
    if not arch.compatible(ids):
        raise ValueError("REPRESENTATIVE_CONTEXT_NOT_STRUCTURALLY_REACHABLE")
    if len(ids) > arch.MAX_GENERATED_INSTRUCTIONS:
        raise ValueError("REPRESENTATIVE_EXCEEDS_PUBLIC_INSTRUCTION_BOUND")
    return contracts


def verify_quotient() -> dict[str, Any]:
    base = reduction.verify()
    if "ONLY_PINNED_PUNKT_CONTEXT_REMAINS" not in base["status"]:
        raise AssertionError("PARAMETRIC_REDUCTION_NOT_BOUND")

    contexts = reachable_contexts()
    if not contexts:
        raise AssertionError("NO_REACHABLE_PUNKT_CONTEXTS")

    for context in contexts:
        # Representative is required only for semantically reachable coordinate
        # combinations. Threshold 2 exercises the less-than candidate and 20
        # exercises the maximal at-least scaffold without terminal data.
        representative_contracts(
            context,
            relation="less than",
            threshold=2,
        )
        representative_contracts(
            context,
            relation="at least",
            threshold=20,
        )

    return {
        "schema": SCHEMA,
        "status": "PASS__RAW_SENTENCE_SLOT_PRODUCT_REDUCED_TO_FINITE_PUNKT_CONTEXT_QUOTIENT",
        "reachable_context_count": len(contexts),
        "contexts": [asdict(x) for x in contexts],
        "coordinate_domains": {
            "nth_mode": list(NTH_MODES),
            "word_mode": list(WORD_MODES),
            "postscript_mode": list(POSTSCRIPT_MODES),
            "end_mode": list(END_MODES),
            "quotation": [False, True],
        },
        "sentence_obligations": {
            "less_than_1": (
                "ALREADY_PROVED_UNSAT_BY_STRICT_NONEMPTY_PLUS_PINNED_PUNKT"
            ),
            "less_than_n_ge_2": (
                "ONE_EXACT_CONTEXT_CHECK_AT_THRESHOLD_2_SUFFICES_PER_CONTEXT; "
                "THE COMPOSER RESPONSE IS THRESHOLD-INDEPENDENT FOR ALL N>=2 "
                "AND CHECKER ACCEPTANCE IS MONOTONE IN THE UPPER THRESHOLD"
            ),
            "at_least": (
                "EXACTLY 20 PUBLIC THRESHOLDS REMAIN PER CONTEXT BECAUSE THE "
                "COMPOSER EMITS N EXPLICIT SENTENCE TERMINATORS"
            ),
        },
        "quotient_lemmas": [
            "ASCII_GENERATED_WORD_IDENTITY_CANNOT_INTRODUCE_SENTENCE_TERMINAL_PUNCTUATION",
            "SECTION_BULLET_TITLE_AND_EXISTENCE_PREFIX_VARIABILITY_IS_PUNCTUATION_NEUTRAL",
            "NTH_LOCATION_COLLAPSES_TO_TRAILING_PARAGRAPH_BOOLEAN_AFTER_LAST_GENERATED_SENTENCE",
            "WORD_AT_LEAST_THRESHOLD_COLLAPSES_TO_PADDING_PRESENT_BECAUSE_UNPADDED_WORD_BOUND_IS_BELOW_100",
            "WORD_PADDING_CARDINALITY_IS_PUNCTUATION_NEUTRAL",
            "POSTSCRIPT_END_AND_QUOTATION_REMAIN_EXPLICIT_BECAUSE_THEY_CAN_AFFECT_PUNKT",
        ],
        "independent_verification_required": True,
        "terminal_rows_used": False,
        "hidden_kwargs_used": False,
        "target_scores_used": False,
        "acceptance_credit": False,
        "hard_nonclaims": [
            "THIS_QUOTIENT_DOES_NOT_ITSELF EXECUTE_OR_CERTIFY_PINNED_PUNKT",
            "LIVEBENCH_ACCEPTANCE_REMAINS_UNCHANGED_UNTIL_INDEPENDENT_CONTEXT_EXHAUSTION",
        ],
    }


def run(args: Mapping[str, Any] | None = None, root=None) -> dict[str, Any]:
    return verify_quotient()


if __name__ == "__main__":
    import json
    print(json.dumps(verify_quotient(), indent=2, sort_keys=True))
