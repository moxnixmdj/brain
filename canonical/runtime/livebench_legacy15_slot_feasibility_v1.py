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
from fractions import Fraction
from typing import Any, Mapping, Sequence

from canonical.runtime import livebench_legacy15_composition_archetypes_v1 as archetypes

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_LEGACY15_SLOT_FEASIBILITY_V1"
PINNED_LIVEBENCH_COMMIT = "8f8e5c381a16e3f24257776edd53471fe86f8091"
PINNED_INSTRUCTIONS_BLOB = "4997bab885a676d92545fd91a9a20b48d234a2b2"
PINNED_REGISTRY_BLOB = "903ed738398648c7cfac61d5ffa478c22f1f0891"
HISTORICAL_GENERATOR_BLOB = "6ff390d6885cf90f88d9d36959735cb327613edc"
OPUS55_COMPARATOR = Fraction(262951, 400000)  # 0.6573775

NTH = "length_constraints:nth_paragraph_first_word"
EXISTENCE = "keywords:existence"
FORBIDDEN = "keywords:forbidden_words"
END = "startend:end_checker"


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

    if EXISTENCE in by_id and FORBIDDEN in by_id:
        required = [str(x) for x in by_id[EXISTENCE].get("keywords", ())]
        forbidden_by_fold = {word.casefold(): word for word in forbidden_words}
        for keyword in required:
            if keyword.casefold() in forbidden_by_fold:
                reasons.append("REQUIRED_KEYWORD_IS_FORBIDDEN_WORD:" + keyword.casefold())

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


def prove_support_wide_threshold_floor_impossible() -> dict[str, Any]:
    """Falsify a uniform comparator floor over the full generator support.

    The public generator domain can emit the conflict-compatible two-checker
    tuple ForbiddenWords(["other"]) + EndChecker("Any other questions?").
    Slot feasibility certifies that tuple UNSAT: satisfying the required ending
    necessarily emits the whole word "other", which the forbidden checker
    rejects. Thus at most one of two checkers can pass.

    The frozen strict score is (all_true + true_fraction)/2, so the maximum
    score is (0 + 1/2)/2 = 1/4. Since 1/4 < 0.6573775, no theorem claiming a
    >= comparator per-case floor over every generator-supported parameterization
    can be true.

    This is a scheduler theorem only. It does not claim the fixed terminal
    population contains this parameterization.
    """
    contracts = [
        {
            "instruction_id": END,
            "slots": {"end_phrase": "Any other questions?"},
        },
        {
            "instruction_id": FORBIDDEN,
            "slots": {"forbidden_words": ["other"]},
        },
    ]
    classified = classify_visible_contracts(contracts)
    expected = "MANDATORY_END_PHRASE_CONTAINS_FORBIDDEN_WORD:other"
    if classified.get("status") != "PROVED_UNSAT":
        raise RuntimeError("SUPPORT_COUNTEREXAMPLE_NOT_UNSAT")
    if expected not in classified.get("hard_unsat_reasons", []):
        raise RuntimeError("SUPPORT_COUNTEREXAMPLE_REASON_DRIFT")

    maximum_true = 1
    instruction_count = 2
    maximum_score = (
        Fraction(0, 1) + Fraction(maximum_true, instruction_count)
    ) / 2
    if maximum_score != Fraction(1, 4):
        raise RuntimeError("SUPPORT_COUNTEREXAMPLE_SCORE_DRIFT")
    if not maximum_score < OPUS55_COMPARATOR:
        raise RuntimeError("SUPPORT_COUNTEREXAMPLE_NO_LONGER_BELOW_COMPARATOR")

    return {
        "schema": SCHEMA,
        "status": "PASS__SUPPORT_WIDE_COMPARATOR_FLOOR_FALSIFIED",
        "counterexample": {
            "instruction_ids": sorted([END, FORBIDDEN]),
            "visible_slots": {
                END: {"end_phrase": "Any other questions?"},
                FORBIDDEN: {"forbidden_words": ["other"]},
            },
            "conflict_compatible": True,
            "slot_status": "PROVED_UNSAT",
            "maximum_simultaneously_true": maximum_true,
        },
        "score": {
            "maximum_case_score_fraction": "1/4",
            "maximum_case_score": float(maximum_score),
            "opus55_comparator_fraction": "262951/400000",
            "opus55_comparator": float(OPUS55_COMPARATOR),
            "below_comparator": True,
        },
        "scheduler_consequence": (
            "FULL_GENERATOR_SUPPORT_CONSTRUCTOR_TOTALITY_MAY_REMAIN_A_FALSIFICATION_"
            "TARGET_BUT_CANNOT_BY_ITSELF_PROVE_A_UNIFORM_OPUS55_THRESHOLD_FLOOR"
        ),
        "acceptance_consequence": (
            "THRESHOLD_CREDIT_REQUIRES_POPULATION_SPECIFIC_CONTAMINATION_SAFE_"
            "SCORE_MASS_EVIDENCE_OR_A_VERIFIED_CLEAN_EQUIVALENT_ROUTE"
        ),
        "actual_terminal_population_contains_counterexample": "NOT_CLAIMED",
        "terminal_data_used": False,
        "hidden_kwargs_used": False,
        "acceptance_credit": False,
    }


def run(args=None, root=None):
    return prove_id_compatibility_is_not_satisfiability()


if __name__ == "__main__":
    import json
    print(json.dumps(run(), indent=2, sort_keys=True))
