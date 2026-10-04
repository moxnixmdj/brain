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
END = "startend:end_checker"\nSECTIONS = "detectable_format:multiple_sections"


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
