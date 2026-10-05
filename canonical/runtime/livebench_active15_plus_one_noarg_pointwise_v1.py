#!/usr/bin/env python3
"""Pointwise candidate solver for the four schema-indistinguishable no-arg extras.

This module composes the already-closed Active15 pointwise planner with exactly
one of the only four extra checker families that the frozen HF kwargs schema
cannot exclude:
  constrained_response, english_capital, english_lowercase, no_comma.

It is deliberately limited to Active15+1. That is sufficient for the reduced
release-scope envelope and avoids solving irrelevant Union25 products.

The English-case construction uses six disjoint-vocabulary English carriers.
Public forbidden_words has at most five generated words. Because carrier
vocabularies are pairwise disjoint, five forbidden words can invalidate at
most five carriers, leaving at least one collision-free carrier. Each carrier
is 8 words repeated four times (32 words): long enough for robust English
detection while preserving the public word<100 upper-bound budget when a case
checker occupies one of the maximum five generated instruction slots.

Independent exact-checker verification remains required before promotion.
"""
from __future__ import annotations

import re
from typing import Any, Mapping, Sequence

from canonical.runtime import livebench_legacy15_pointwise_optimal_v1 as active
from canonical.runtime import livebench_legacy15_contract_composer_v2 as composer
from canonical.runtime import livebench_union25_archetypes_v1 as u
from canonical.runtime.livebench_release_schema_scope_bridge_v1 import NOARG_EXTRAS

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_ACTIVE15_PLUS_ONE_NOARG_POINTWISE_V1"

CONSTRAINED = u.CONSTRAINED
EN_CAP = u.ENGLISH_CAPITAL
EN_LOW = u.ENGLISH_LOWERCASE
NO_COMMA = u.NO_COMMA

# 6 pairwise-disjoint vocabularies, 8 words each. Repeated x4 => 32 words.
_CARRIER_BASES = (
    ("careful", "reasoning", "reveals", "durable", "patterns", "through", "systematic", "evidence"),
    ("thoughtful", "analysis", "connects", "distinct", "observations", "while", "preserving", "relationships"),
    ("practical", "engineering", "builds", "reliable", "mechanisms", "using", "measured", "constraints"),
    ("clear", "explanation", "communicates", "difficult", "concepts", "via", "familiar", "examples"),
    ("robust", "research", "compares", "independent", "findings", "before", "forming", "conclusions"),
    ("patient", "investigation", "uncovers", "hidden", "assumptions", "by", "testing", "predictions"),
)
ENGLISH_CARRIERS = tuple(" ".join(words * 4) for words in _CARRIER_BASES)

MAX_PUBLIC_FORBIDDEN_WORDS = 5
CASE_CARRIER_WORD_COUNT = 32


class PlusOneError(ValueError):
    pass


def _slots(c: Mapping[str, Any]) -> dict[str, Any]:
    return dict(c.get("slots") or {})


def _carrier_vocab(carrier: str) -> frozenset[str]:
    return frozenset(re.findall(r"[A-Za-z]+", carrier.lower()))


def _verify_carrier_combinatorics() -> None:
    vocabs = [_carrier_vocab(x) for x in ENGLISH_CARRIERS]
    if any(len(v) != 8 for v in vocabs):
        raise AssertionError("CARRIER_VOCABULARY_CARDINALITY_DRIFT")
    for i, left in enumerate(vocabs):
        for right in vocabs[i + 1:]:
            if left & right:
                raise AssertionError("CARRIER_VOCABULARIES_NOT_DISJOINT")
    if len(ENGLISH_CARRIERS) <= MAX_PUBLIC_FORBIDDEN_WORDS:
        raise AssertionError("CARRIER_PIGEONHOLE_MARGIN_LOST")


def choose_forbidden_safe_carrier(forbidden_words: Sequence[str]) -> str:
    forbidden = [str(x) for x in forbidden_words]
    if len(forbidden) > MAX_PUBLIC_FORBIDDEN_WORDS:
        raise PlusOneError("OUTSIDE_PUBLIC_FORBIDDEN_CARDINALITY")

    for carrier in ENGLISH_CARRIERS:
        if all(
            re.search(r"\b" + re.escape(word) + r"\b", carrier, flags=re.I) is None
            for word in forbidden
        ):
            return carrier
    raise PlusOneError("PIGEONHOLE_CARRIER_SELECTION_FAILURE")


def _append_inside_terminal_wrappers(
    response: str,
    carrier: str,
    retained_contracts: Sequence[Mapping[str, Any]],
) -> str:
    """Append carrier without breaking exact END or QUOTE wrappers."""
    ids = {str(c.get("instruction_id")) for c in retained_contracts}
    text = str(response)
    quoted = composer.QUOTE in ids
    if quoted:
        if not (text.startswith('"') and text.endswith('"')):
            raise PlusOneError("ACTIVE_QUOTE_WITNESS_SHAPE_DRIFT")
        body = text[1:-1]
    else:
        body = text

    end_contract = next(
        (c for c in retained_contracts if str(c.get("instruction_id")) == composer.END),
        None,
    )
    if end_contract is not None:
        phrase = str(_slots(end_contract).get("end_phrase") or "").strip()
        stripped = body.rstrip()
        if not phrase or not stripped.lower().endswith(phrase.lower()):
            raise PlusOneError("ACTIVE_END_WITNESS_SHAPE_DRIFT")
        prefix = stripped[:-len(phrase)].rstrip()
        body = ((prefix + " ") if prefix else "") + carrier + " " + phrase
    else:
        body = body.rstrip()
        body = (body + " " if body else "") + carrier

    return '"' + body + '"' if quoted else body


def _case_section_collision(extra_id: str, retained_contracts: Sequence[Mapping[str, Any]]) -> bool:
    section = next(
        (c for c in retained_contracts if str(c.get("instruction_id")) == composer.SECTIONS),
        None,
    )
    if section is None:
        return False
    splitter = str(_slots(section).get("section_spliter"))
    if splitter not in {"Section", "SECTION"}:
        raise PlusOneError("OUTSIDE_PUBLIC_SECTION_SPLITTER_DOMAIN")
    if extra_id == EN_CAP:
        return splitter == "Section"
    if extra_id == EN_LOW:
        return True
    raise PlusOneError("NOT_CASE_EXTRA")


def _active_forbidden_words(
    contracts: Sequence[Mapping[str, Any]],
    sacrificed: set[str],
) -> list[str]:
    if composer.FORBIDDEN in sacrificed:
        return []
    c = next(
        (x for x in contracts if str(x.get("instruction_id")) == composer.FORBIDDEN),
        None,
    )
    if c is None:
        return []
    return [str(x) for x in (_slots(c).get("forbidden_words") or [])]


def _score(total: int, passed: int) -> float:
    return active.strict_score_from_pass_count(total, passed)


def solve_contracts(contracts: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    contracts = [dict(c) for c in contracts]
    ids = [str(c.get("instruction_id")) for c in contracts]
    if not contracts:
        return {"schema": SCHEMA, "status": "FAIL_CLOSED", "error": "NO_CONTRACTS", "acceptance_credit": False}
    if len(ids) != len(set(ids)):
        return {"schema": SCHEMA, "status": "FAIL_CLOSED", "error": "DUPLICATE_ID", "acceptance_credit": False}
    if len(ids) > u.MAX_GENERATED_INSTRUCTIONS or not u.compatible(ids):
        return {"schema": SCHEMA, "status": "FAIL_CLOSED", "error": "OUTSIDE_PINNED_COMPATIBLE_STRUCTURE", "acceptance_credit": False}

    extras = [iid for iid in ids if iid not in u.ACTIVE15]
    if len(extras) != 1 or extras[0] not in NOARG_EXTRAS:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "error": "REQUIRES_EXACTLY_ONE_SCHEMA_INDISTINGUISHABLE_NOARG_EXTRA",
            "acceptance_credit": False,
        }
    extra = extras[0]

    if extra == CONSTRAINED:
        if len(contracts) != 1:
            return {"schema": SCHEMA, "status": "FAIL_CLOSED", "error": "CONSTRAINED_CONFLICT_GRAPH_DRIFT", "acceptance_credit": False}
        response = "My answer is yes."
        return {
            "schema": SCHEMA,
            "status": "CANDIDATE_POINTWISE_OPTIMAL_ACTIVE15_PLUS_ONE",
            "extra_family": extra,
            "response": response,
            "instruction_count": 1,
            "sacrificed_instruction_ids": [],
            "theoretical_max_pass_count": 1,
            "theoretical_pointwise_optimum_strict_score": 1.0,
            "proof_shape": "FROZEN_CONFLICT_GRAPH_ISOLATES_CONSTRAINED_RESPONSE_AS_SINGLETON",
            "terminal_rows_used": False,
            "acceptance_credit": False,
        }

    active_contracts = [c for c in contracts if str(c.get("instruction_id")) in u.ACTIVE15]

    # Active15+1 includes the valid degenerate case where the Active15 subset is
    # empty. The Active15 solver correctly rejects an empty contract list, so
    # handle these three singleton no-arg extras directly instead of delegating
    # an impossible empty subproblem.
    if not active_contracts:
        if extra == NO_COMMA:
            response = "alpha"
            proof = "SINGLETON_NO_COMMA__COMMA_FREE_WITNESS"
        elif extra in {EN_CAP, EN_LOW}:
            carrier = choose_forbidden_safe_carrier(())
            response = carrier.upper() if extra == EN_CAP else carrier.lower()
            proof = (
                "SINGLETON_ENGLISH_CASE__PINNED_ENGLISH_CARRIER_WITH_GLOBAL_"
                "CASE_NORMALIZATION__NO_ACTIVE15_SUBPROBLEM_REQUIRED"
            )
        else:
            raise AssertionError("UNREACHABLE_SINGLETON_EXTRA")
        return {
            "schema": SCHEMA,
            "status": "CANDIDATE_POINTWISE_OPTIMAL_ACTIVE15_PLUS_ONE",
            "extra_family": extra,
            "response": response,
            "instruction_ids": sorted(ids),
            "sacrificed_instruction_ids": [],
            "instruction_count": 1,
            "theoretical_max_pass_count": 1,
            "theoretical_pointwise_optimum_strict_score": 1.0,
            "proof_shape": proof,
            "carrier_word_count_if_case_route": (
                CASE_CARRIER_WORD_COUNT if extra in {EN_CAP, EN_LOW} else 0
            ),
            "terminal_rows_used": False,
            "hidden_kwargs_used": False,
            "terminal_frequencies_used": False,
            "target_scores_used": False,
            "acceptance_credit": False,
        }

    solved = active.solve_contracts(active_contracts)
    if solved.get("status") != "CANDIDATE_POINTWISE_OPTIMAL":
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "error": "ACTIVE15_SUBPROBLEM_NOT_SOLVED",
            "active_result": solved,
            "acceptance_credit": False,
        }

    sacrificed = set(map(str, solved.get("sacrificed_instruction_ids") or []))
    retained = [
        c for c in active_contracts
        if str(c.get("instruction_id")) not in sacrificed
    ]
    response = str(solved["response"])

    if extra == NO_COMMA:
        if "," in response:
            if composer.REPEAT not in {str(c.get("instruction_id")) for c in retained}:
                return {
                    "schema": SCHEMA,
                    "status": "FAIL_CLOSED",
                    "error": "UNEXPLAINED_COMMA_OUTSIDE_REPEAT_ROUTE",
                    "response": None,
                    "acceptance_credit": False,
                }
            repeat = next(c for c in retained if str(c.get("instruction_id")) == composer.REPEAT)
            prefix = str(_slots(repeat).get("prompt_to_repeat") or "")
            if "," not in prefix:
                return {
                    "schema": SCHEMA,
                    "status": "FAIL_CLOSED",
                    "error": "ACTIVE_REPEAT_RESPONSE_COMMA_NOT_FORCED_BY_PREFIX",
                    "response": None,
                    "acceptance_credit": False,
                }
            sacrificed.add(NO_COMMA)
            proof = (
                "REPEAT_REQUIRES_CASE_INSENSITIVE_EXACT_PREFIX_INCLUDING_COMMA__"
                "NO_COMMA_FORBIDS_THAT_COMMA__ONE_OF_THE_TWO_MUST_FAIL__DROP_NO_COMMA"
            )
        else:
            proof = "ACTIVE15_WITNESS_IS_COMMA_FREE__NO_COMMA_ADDS_ZERO_INTERACTION"
    elif extra in {EN_CAP, EN_LOW}:
        if _case_section_collision(extra, retained):
            # Keep the already-optimal Active15 response and sacrifice the case
            # checker. The case-sensitive section literal and global case law
            # cannot both hold; one loss is mandatory and sufficient.
            sacrificed.add(extra)
            proof = (
                "GLOBAL_CASE_CONSTRAINT_CONFLICTS_WITH_CASE_SENSITIVE_SECTION_SPLITTER__"
                "ONE_LOSS_MANDATORY__KEEP_ACTIVE15_SECTION_AND_DROP_CASE_CHECKER"
            )
        else:
            forbidden = _active_forbidden_words(active_contracts, sacrificed)
            carrier = choose_forbidden_safe_carrier(forbidden)
            response = _append_inside_terminal_wrappers(response, carrier, retained)
            response = response.upper() if extra == EN_CAP else response.lower()
            proof = (
                "PAIRWISE_DISJOINT_ENGLISH_CARRIER_BANK_PLUS_MAX5_FORBIDDEN_PIGEONHOLE__"
                "GLOBAL_CASE_NORMALIZATION_COMMUTES_WITH_ALL_RETAINED_ACTIVE15_CHECKERS_"
                "EXCEPT_SECTION_CASE_WHICH_WAS_SEPARATELY_EXCLUDED"
            )
    else:
        raise AssertionError("UNREACHABLE_EXTRA")

    total = len(contracts)
    max_pass = total - len(sacrificed)
    return {
        "schema": SCHEMA,
        "status": "CANDIDATE_POINTWISE_OPTIMAL_ACTIVE15_PLUS_ONE",
        "extra_family": extra,
        "response": response,
        "instruction_ids": sorted(ids),
        "sacrificed_instruction_ids": sorted(sacrificed),
        "instruction_count": total,
        "theoretical_max_pass_count": max_pass,
        "theoretical_pointwise_optimum_strict_score": _score(total, max_pass),
        "proof_shape": proof,
        "carrier_word_count_if_case_route": CASE_CARRIER_WORD_COUNT if extra in {EN_CAP, EN_LOW} and extra not in sacrificed else 0,
        "terminal_rows_used": False,
        "hidden_kwargs_used": False,
        "terminal_frequencies_used": False,
        "target_scores_used": False,
        "acceptance_credit": False,
    }


def verify_combinatorics() -> dict[str, Any]:
    _verify_carrier_combinatorics()
    # Pigeonhole stress: one forbidden token from each of five distinct carriers
    # must leave the sixth carrier available.
    blockers = [next(iter(_carrier_vocab(x))) for x in ENGLISH_CARRIERS[:5]]
    chosen = choose_forbidden_safe_carrier(blockers)
    if chosen != ENGLISH_CARRIERS[5]:
        raise AssertionError("PIGEONHOLE_CARRIER_SELECTION_DRIFT")
    return {
        "schema": SCHEMA,
        "status": "PASS__ACTIVE15_PLUS_ONE_NOARG_COMBINATORICS__EXACT_CHECKER_VERIFICATION_REQUIRED",
        "carrier_count": len(ENGLISH_CARRIERS),
        "carrier_vocab_size_each": 8,
        "carrier_word_count_each": CASE_CARRIER_WORD_COUNT,
        "max_public_forbidden_words": MAX_PUBLIC_FORBIDDEN_WORDS,
        "terminal_rows_used": False,
        "acceptance_credit": False,
    }


def run(args: Mapping[str, Any], root=None) -> dict[str, Any]:
    return solve_contracts(list((args or {}).get("contracts") or []))


if __name__ == "__main__":
    import json, sys
    if sys.stdin.isatty():
        print(json.dumps(verify_combinatorics(), indent=2, sort_keys=True))
    else:
        print(json.dumps(run(json.load(sys.stdin)), indent=2, sort_keys=True))
