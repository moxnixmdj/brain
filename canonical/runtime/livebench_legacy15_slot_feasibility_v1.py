#!/usr/bin/env python3
"""Slot-level feasibility facts for the frozen active legacy-15 LiveBench surface.

This module repairs a proof-scope error: conflict-compatible instruction IDs do
not imply satisfiable concrete checker contracts. It uses only public frozen
checker semantics and visible contract slots. It reads no terminal row content,
hidden kwargs, case IDs, responses, frequencies, or scores.

The functions here intentionally certify only hard UNSAT classes that follow
directly from the pinned checker semantics. Absence of a reported contradiction
is NOT a satisfiability proof.
"""
from __future__ import annotations

import re
from typing import Any, Mapping, Sequence

from canonical.runtime import livebench_legacy15_composition_archetypes_v1 as archetypes

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_LEGACY15_SLOT_FEASIBILITY_V1"
PINNED_LIVEBENCH_COMMIT = "8f8e5c381a16e3f24257776edd53471fe86f8091"
PINNED_INSTRUCTIONS_BLOB = "4997bab885a676d92545fd91a9a20b48d234a2b2"
PINNED_REGISTRY_BLOB = "903ed738398648c7cfac61d5ffa478c22f1f0891"
HISTORICAL_GENERATOR_BLOB = "6ff390d6885cf90f88d9d36959735cb327613edc"

NTH = "length_constraints:nth_paragraph_first_word"
FORBIDDEN = "keywords:forbidden_words"
EXISTENCE = "keywords:existence"
END = "startend:end_checker"
SENTENCE = "length_constraints:number_sentences"
SECTIONS = "detectable_format:multiple_sections"
PUBLIC_END_PHRASES = ("Any other questions?", "Is there anything else I can help with?")


def _slots_by_id(contracts: Sequence[Mapping[str, Any]]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for contract in contracts:
        iid = str(contract["instruction_id"])
        if iid in out:
            raise ValueError("DUPLICATE_INSTRUCTION_ID")
        out[iid] = dict(contract.get("slots") or {})
    return out


def _literal_forbidden_hit(text: str, forbidden_words: Sequence[str]) -> str | None:
    """Return the first generated literal forbidden word forced by text.

    The pinned ForbiddenWords checker searches r"\b" + word + r"\b" with
    IGNORECASE. The historical generator draws plain WORD_LIST entries, so this
    function is exact for that admitted generator domain.
    """
    for raw in forbidden_words:
        word = str(raw)
        if re.search(r"\b" + re.escape(word) + r"\b", str(text), flags=re.IGNORECASE):
            return word
    return None


def hard_unsat_reasons(contracts: Sequence[Mapping[str, Any]]) -> tuple[str, ...]:
    """Certify direct slot-level contradictions from frozen checker semantics.

    This is deliberately incomplete: returned reasons are proofs of UNSAT;
    returning an empty tuple means UNKNOWN/NOT-CERTIFIED rather than SAT.
    """
    by_id = _slots_by_id(contracts)
    reasons: list[str] = []

    forbidden = by_id.get(FORBIDDEN, {}).get("forbidden_words", ())
    forbidden_words = [str(x) for x in forbidden]

    # Existence/forbidden overlap is NOT an UNSAT class. The pinned existence
    # checker performs raw regex substring search while ForbiddenWords wraps the
    # generated alphabetic word in word boundaries. A carrier such as "rock0"
    # therefore satisfies required "rock" while avoiding \\brock\\b. Keep this
    # asymmetry explicit so the feasibility layer never emits a false certificate.

    if NTH in by_id and FORBIDDEN in by_id:
        first_word = str(by_id[NTH].get("first_word", ""))
        if first_word and any(first_word.casefold() == w.casefold() for w in forbidden_words):
            reasons.append("NTH_FIRST_WORD_IS_FORBIDDEN_WORD")

    if END in by_id and FORBIDDEN in by_id:
        end_phrase = str(by_id[END].get("end_phrase", ""))
        hit = _literal_forbidden_hit(end_phrase, forbidden_words)
        if hit is not None:
            reasons.append("MANDATORY_END_PHRASE_CONTAINS_FORBIDDEN_WORD:" + hit.casefold())

    if SECTIONS in by_id and FORBIDDEN in by_id:
        splitter = str(by_id[SECTIONS].get("section_spliter", "")).strip()
        hit = _literal_forbidden_hit(splitter, forbidden_words)
        if hit is not None:
            reasons.append("MANDATORY_SECTION_SPLITTER_IS_FORBIDDEN_WORD:" + hit.casefold())

    if SENTENCE in by_id:
        sentence = by_id[SENTENCE]
        relation = str(sentence.get("relation", "")).strip().casefold()
        try:
            threshold = int(sentence.get("num_sentences"))
        except (TypeError, ValueError):
            threshold = -1

        if relation == "less than" and threshold == 1:
            # Exact NLTK 3.9.2 Punkt geometry used by the frozen checker:
            # _slices_from_text() always yields the final text.rstrip() slice,
            # and _realign_boundaries() emits that slice whenever it is
            # nonempty. Therefore count_sentences(text) == 0 implies
            # text.rstrip() == "", i.e. the response is whitespace-only.
            # Any compatible checker below that requires a non-whitespace
            # response is thus jointly UNSAT with sentence < 1.
            if END in by_id:
                end_phrase = str(by_id[END].get("end_phrase", "")).strip()
                if end_phrase in PUBLIC_END_PHRASES:
                    reasons.append("SENTENCE_LT_ONE_WITH_MANDATORY_END_PHRASE")

            positive_ids = (
                EXISTENCE,
                NTH,
                POSTSCRIPT,
                BULLETS,
                TITLE,
                SECTIONS,
                QUOTATION,
            )
            for iid in positive_ids:
                if iid in by_id:
                    reasons.append("SENTENCE_LT_ONE_WITH_NONEMPTY_REQUIREMENT:" + iid)

            # Historical NumberOfWords lower bounds are >=100, hence any
            # at-least word contract requires non-whitespace output.
            if WORDS in by_id:
                word_slots = by_id[WORDS]
                if str(word_slots.get("relation", "")).strip().casefold() == "at least":
                    try:
                        word_target = int(word_slots.get("num_words"))
                    except (TypeError, ValueError):
                        word_target = -1
                    if word_target > 0:
                        reasons.append("SENTENCE_LT_ONE_WITH_POSITIVE_WORD_LOWER_BOUND")

            # ParagraphChecker also requires non-whitespace for every generated
            # num_paragraphs >=1. It is ID-conflicting with NumberOfSentences in
            # the pinned registry, but keep the semantic fact explicit so this
            # kernel remains sound if called directly on an unfiltered subset.
            if PARAGRAPHS in by_id:
                try:
                    para_target = int(by_id[PARAGRAPHS].get("num_paragraphs"))
                except (TypeError, ValueError):
                    para_target = -1
                if para_target > 0:
                    reasons.append("SENTENCE_LT_ONE_WITH_POSITIVE_PARAGRAPH_REQUIREMENT")

    return tuple(reasons)


def classify_visible_contracts(contracts: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    ids = tuple(str(c["instruction_id"]) for c in contracts)
    if len(ids) != len(set(ids)):
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED_DUPLICATE_ID",
            "instruction_ids": sorted(ids),
            "hard_unsat_reasons": [],
            "terminal_data_used": False,
            "acceptance_credit": False,
        }
    if not archetypes.compatible(ids):
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED_ID_CONFLICT",
            "instruction_ids": sorted(ids),
            "hard_unsat_reasons": [],
            "terminal_data_used": False,
            "acceptance_credit": False,
        }
    reasons = hard_unsat_reasons(contracts)
    return {
        "schema": SCHEMA,
        "status": "PROVED_UNSAT" if reasons else "ID_COMPATIBLE__SLOT_FEASIBILITY_NOT_YET_PROVED",
        "instruction_ids": sorted(ids),
        "archetype": archetypes.archetype(ids),
        "hard_unsat_reasons": list(reasons),
        "terminal_data_used": False,
        "hidden_kwargs_used": False,
        "acceptance_credit": False,
    }


def prove_id_compatibility_is_not_satisfiability() -> dict[str, Any]:
    """Return an exact public counterexample to the old proof target.

    ParagraphFirstWordCheck requires the selected paragraph's first word to be
    exactly "alpha" (case-insensitive after its punctuation trimming). Therefore
    a passing response necessarily contains alpha as a standalone word at that
    position. ForbiddenWords(["alpha"]) rejects every response containing the
    standalone word alpha. The ID pair is nevertheless conflict-compatible in
    the pinned registry. Hence ID compatibility alone cannot imply SAT.
    """
    contracts = [
        {
            "instruction_id": NTH,
            "slots": {
                "num_paragraphs": 2,
                "nth_paragraph": 1,
                "first_word": "alpha",
            },
        },
        {
            "instruction_id": FORBIDDEN,
            "slots": {"forbidden_words": ["alpha"]},
        },
    ]
    ids = tuple(c["instruction_id"] for c in contracts)
    if not archetypes.compatible(ids):
        raise RuntimeError("COUNTEREXAMPLE_PAIR_UNEXPECTEDLY_ID_CONFLICTING")
    reasons = hard_unsat_reasons(contracts)
    if "NTH_FIRST_WORD_IS_FORBIDDEN_WORD" not in reasons:
        raise RuntimeError("COUNTEREXAMPLE_NOT_CERTIFIED")
    return {
        "schema": SCHEMA,
        "status": "PASS__ID_COMPATIBILITY_STRICTLY_WEAKER_THAN_SLOT_SATISFIABILITY",
        "counterexample_instruction_ids": sorted(ids),
        "counterexample_archetype": archetypes.archetype(ids),
        "hard_unsat_reasons": list(reasons),
        "consequence": (
            "THE_928_ID_SET_PARTITION_REMAINS_A_VALID_STRUCTURAL_REDUCTION_BUT_"
            "CANNOT_BY_ITSELF_SUPPORT_A_UNIVERSAL_CONSTRUCTIVE_COMPOSITION_PROOF"
        ),
        "corrected_proof_target": (
            "FOR_EACH_VISIBLE_GENERATOR_ADMITTED_CONTRACT_TUPLE_EITHER_PRODUCE_"
            "A_POSTVALIDATED_WITNESS_OR_A_CHECKER_SEMANTICS_UNSAT_CERTIFICATE"
        ),
        "terminal_data_used": False,
        "hidden_kwargs_used": False,
        "acceptance_credit": False,
    }


def run(args=None, root=None):
    return prove_id_compatibility_is_not_satisfiability()


if __name__ == "__main__":
    import json
    print(json.dumps(run(), indent=2, sort_keys=True))
