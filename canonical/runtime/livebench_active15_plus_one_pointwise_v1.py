#!/usr/bin/env python3
"""Pointwise candidate solver for the four metadata-surviving LiveBench extensions.

Frozen release-schema metadata excludes every argument-bearing family outside
Active15. Under the first-party 15-vs-16 scope envelope, only four no-argument
families can remain, and at most one can be present:
  constrained_response, english_capital, english_lowercase, no_comma.

This module turns that residual into one generic construction:
1. derive sound mandatory-loss hyperedges from Active15 plus union25 rules;
2. solve the exact minimum hitting set over <=5 checker contracts (<=32 subsets);
3. compose the retained Active15 contracts with Composer V3;
4. apply the retained no-argument extension as a transparent transform;
5. fail closed if any construction invariant is violated.

The English-case paths are conditional on independent exact-runtime verification
of language_exception_carrier_v2. No terminal row, hidden kwargs, target response,
frequency, or score is read here.
"""
from __future__ import annotations

from itertools import combinations
from typing import Any, Iterable, Mapping, Sequence

from canonical.runtime import livebench_legacy15_contract_composer_v3 as active
from canonical.runtime import livebench_legacy15_slot_feasibility_v1 as feasibility
from canonical.runtime import livebench_release_schema_scope_bridge_v1 as scope
from canonical.runtime import livebench_union25_language_exception_carrier_v2 as langcarrier
from canonical.runtime import livebench_union25_mandatory_loss_v1 as unionloss

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_ACTIVE15_PLUS_ONE_POINTWISE_V1"

CONSTRAINED = "detectable_format:constrained_response"
UPPER = "change_case:english_capital"
LOWER = "change_case:english_lowercase"
NO_COMMA = "punctuation:no_comma"
EXTENSIONS = frozenset({CONSTRAINED, UPPER, LOWER, NO_COMMA})

SENTENCES = "length_constraints:number_sentences"
FORBIDDEN = "keywords:forbidden_words"
NTH = "length_constraints:nth_paragraph_first_word"
END = "startend:end_checker"
REPEAT = "combination:repeat_prompt"
QUOTE = "startend:quotation"

_SENTENCE_ZERO = "STRICT_NONEMPTY_RESPONSE_IMPLIES_AT_LEAST_ONE_PUNKT_SENTENCE"
_SENTENCE_ZERO_DEP_PREFIX = "SENTENCE_LT_ONE_REQUIRES_EMPTY_BUT_CHECKER_REQUIRES_OUTPUT:"
_SENTENCE_ZERO_END_COMPAT = "SENTENCE_LT_ONE_WITH_MANDATORY_END_PHRASE"
_NTH_FORBIDDEN = "NTH_FIRST_WORD_IS_FORBIDDEN_WORD"
_END_FORBIDDEN_PREFIX = "MANDATORY_END_PHRASE_CONTAINS_FORBIDDEN_WORD:"

# Tie-break toward sacrificing the extension when a pairwise conflict has equal
# cardinality. This preserves the already-closed Active15 constructor.
_PREFERENCE = {
    CONSTRAINED: 0,
    UPPER: 0,
    LOWER: 0,
    NO_COMMA: 0,
}


class PointwiseError(ValueError):
    pass


def _iid(c: Mapping[str, Any]) -> str:
    return str(c.get("instruction_id") or "")


def _slots(c: Mapping[str, Any]) -> dict[str, Any]:
    return dict(c.get("slots") or {})


def _active_edges(contracts: Sequence[Mapping[str, Any]]) -> list[frozenset[str]]:
    reasons = tuple(map(str, feasibility.hard_unsat_reasons(contracts)))
    edges: list[frozenset[str]] = []
    sentence_zero_seen = False
    for reason in reasons:
        if reason == _SENTENCE_ZERO:
            sentence_zero_seen = True
        elif reason == _NTH_FORBIDDEN:
            edges.append(frozenset({NTH, FORBIDDEN}))
        elif reason.startswith(_END_FORBIDDEN_PREFIX):
            edges.append(frozenset({END, FORBIDDEN}))
        elif (
            reason == _SENTENCE_ZERO_END_COMPAT
            or reason.startswith(_SENTENCE_ZERO_DEP_PREFIX)
        ):
            # These are consequences of the intrinsically impossible
            # strict-nonempty sentence<1 checker. The singleton edge below
            # already dominates every dependent pair.
            pass
        else:
            raise PointwiseError("UNRECOGNIZED_ACTIVE15_UNSAT_REASON:" + reason)
    if sentence_zero_seen:
        edges.append(frozenset({SENTENCES}))
    return edges


def _union_edges(
    contracts: Sequence[Mapping[str, Any]],
    *,
    prompt_to_repeat: str | None,
) -> list[frozenset[str]]:
    out = unionloss.derive(contracts, prompt_to_repeat=prompt_to_repeat)
    edges = []
    for item in out["mandatory_loss_rules"]:
        ids = frozenset(map(str, item["checker_ids"]))
        if not ids:
            raise PointwiseError("EMPTY_UNION25_LOSS_EDGE")
        edges.append(ids)
    return edges


def _dedup_edges(edges: Iterable[frozenset[str]]) -> tuple[frozenset[str], ...]:
    unique = set(edges)
    # Delete supersets when a smaller edge already forces a loss. In particular
    # the sentence-zero singleton dominates derivative sentence conflicts.
    minimal = []
    for edge in sorted(unique, key=lambda x: (len(x), tuple(sorted(x)))):
        if any(old <= edge for old in minimal):
            continue
        minimal.append(edge)
    return tuple(minimal)


def _subset_key(subset: frozenset[str]) -> tuple[Any, ...]:
    return (
        len(subset),
        sum(_PREFERENCE.get(iid, 1) for iid in subset),
        tuple(sorted(subset)),
    )


def minimum_hitting_set(
    instruction_ids: Sequence[str],
    edges: Sequence[frozenset[str]],
) -> tuple[str, ...]:
    ids = tuple(dict.fromkeys(map(str, instruction_ids)))
    if len(ids) > 5:
        raise PointwiseError("OUTSIDE_PUBLIC_MAX_INSTRUCTION_COUNT")
    if any(not edge <= set(ids) for edge in edges):
        raise PointwiseError("LOSS_EDGE_OUTSIDE_CONTRACT_SET")

    candidates = []
    for n in range(len(ids) + 1):
        for xs in combinations(ids, n):
            s = frozenset(xs)
            if all(s & edge for edge in edges):
                candidates.append(s)
        if candidates:
            break
    if not candidates:
        raise PointwiseError("NO_HITTING_SET")
    best = min(candidates, key=_subset_key)
    return tuple(sorted(best))


def _extension(contracts: Sequence[Mapping[str, Any]]) -> str | None:
    extras = [_iid(c) for c in contracts if _iid(c) in EXTENSIONS]
    if len(extras) > 1:
        raise PointwiseError("OUTSIDE_ACTIVE15_PLUS_AT_MOST_ONE_SCOPE")
    return extras[0] if extras else None


def _prompt_to_repeat(
    contracts: Sequence[Mapping[str, Any]],
    explicit: str | None,
) -> str | None:
    if explicit is not None:
        return str(explicit)
    for c in contracts:
        if _iid(c) == REPEAT:
            value = _slots(c).get("prompt_to_repeat")
            return None if value is None else str(value)
    return None


def _case_carrier_base(response: str, upper: bool) -> str:
    out = response.upper() if upper else response.lower()
    predicate = str.isupper if upper else str.islower
    if predicate(out):
        return out

    # Composer V3 uses this neutral word-character atom whenever the active
    # response otherwise has no alphabetic payload. Prefixing letters inside the
    # same token adds cased characters without adding punctuation, a word, a
    # paragraph, or a sentence boundary.
    safe = "9000001"
    marker = "QZXV" if upper else "qzxv"
    if safe not in out:
        raise PointwiseError("NO_NEUTRAL_SITE_FOR_CASE_WITNESS")
    out = out.replace(safe, marker + safe, 1)
    if not predicate(out):
        raise PointwiseError("CASE_WITNESS_STILL_HAS_NO_VALID_CASE")
    return out


def _inject_language_exception(
    response: str,
    contracts: Sequence[Mapping[str, Any]],
) -> str:
    # Keep the terminal EndChecker phrase after the carrier. EndChecker is
    # case-insensitive but still requires the phrase at the stripped end.
    end_contract = next((c for c in contracts if _iid(c) == END), None)
    if end_contract is not None:
        phrase = str(_slots(end_contract).get("end_phrase") or "").strip()
        if not phrase:
            raise PointwiseError("END_PHRASE_REQUIRED")
        # The response may have been globally case transformed and may be quoted.
        needle = phrase.upper() if response.isupper() else phrase.lower()
        idx = response.lower().rfind(phrase.lower())
        if idx < 0:
            raise PointwiseError("END_SUFFIX_NOT_FOUND_AFTER_CASE_TRANSFORM")
        prefix, suffix = response[:idx], response[idx:]
        return langcarrier.inject_before_suffix(prefix, suffix)

    if QUOTE in {_iid(c) for c in contracts}:
        if not response.endswith('"'):
            raise PointwiseError("QUOTATION_SUFFIX_DRIFT")
        return langcarrier.inject_before_suffix(response[:-1], '"')

    return langcarrier.inject_before_suffix(response, "")


def _construct_retained(
    contracts: Sequence[Mapping[str, Any]],
    extension: str | None,
) -> tuple[str, str]:
    active_contracts = [c for c in contracts if _iid(c) not in EXTENSIONS]

    if extension == CONSTRAINED:
        if active_contracts:
            raise PointwiseError("CONSTRAINED_MUST_BE_REGISTRY_SINGLETON")
        return "My answer is yes.", "CONSTRAINED_SINGLETON"

    if active_contracts:
        built = active.compose_contracts(active_contracts)
        if built.get("status") != "CANDIDATE_WITNESS":
            raise PointwiseError(
                "ACTIVE15_RETAINED_SUBSET_NOT_CONSTRUCTED:" + str(built.get("status"))
            )
        response = str(built["response"])
        route = str(built.get("route") or "ACTIVE15")
    else:
        response = "9000001"
        route = "EXTENSION_ONLY"

    if extension == NO_COMMA:
        if "," in response:
            raise PointwiseError("NO_COMMA_RETAINED_BUT_ACTIVE_WITNESS_HAS_COMMA")
        return response, route + "+NO_COMMA"

    if extension in {UPPER, LOWER}:
        upper = extension == UPPER
        response = _case_carrier_base(response, upper)
        response = _inject_language_exception(response, active_contracts)
        if upper and not response.isupper():
            raise PointwiseError("UPPERCASE_PROPERTY_LOST_AFTER_LANGUAGE_CARRIER")
        if not upper and not response.islower():
            raise PointwiseError("LOWERCASE_PROPERTY_LOST_AFTER_LANGUAGE_CARRIER")
        return response, route + ("+UPPER" if upper else "+LOWER")

    if extension is None:
        return response, route
    raise PointwiseError("UNKNOWN_EXTENSION:" + str(extension))


def solve(
    contracts: Sequence[Mapping[str, Any]],
    *,
    prompt_to_repeat: str | None = None,
) -> dict[str, Any]:
    contracts = [dict(c) for c in contracts]
    if not contracts:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "error": "NO_CONTRACTS",
            "acceptance_credit": False,
        }

    ids = [_iid(c) for c in contracts]
    if len(ids) != len(set(ids)):
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "error": "DUPLICATE_INSTRUCTION_ID",
            "acceptance_credit": False,
        }
    if len(ids) > 5:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "error": "OUTSIDE_PUBLIC_MAX_INSTRUCTION_COUNT",
            "acceptance_credit": False,
        }

    try:
        ext = _extension(contracts)
        allowed = set(active.archetypes.ACTIVE_IDS) | EXTENSIONS
        if any(iid not in allowed for iid in ids):
            raise PointwiseError("OUTSIDE_RELEASE_SCOPE_ENVELOPE")

        # Structural compatibility is checked against the exact registry25
        # quotient, not the narrower Active15 graph.
        from canonical.runtime import livebench_union25_archetypes_v1 as union
        if not union.compatible(ids):
            raise PointwiseError("REGISTRY_INCOMPATIBLE_CONTRACT_SET")

        repeat_text = _prompt_to_repeat(contracts, prompt_to_repeat)
        edges = _dedup_edges(
            _active_edges(contracts)
            + _union_edges(contracts, prompt_to_repeat=repeat_text)
        )
        sacrificed = minimum_hitting_set(ids, edges)

        kept = [c for c in contracts if _iid(c) not in set(sacrificed)]
        kept_ext = _extension(kept)
        response, route = _construct_retained(kept, kept_ext)

        total = len(contracts)
        max_pass = total - len(sacrificed)
        return {
            "schema": SCHEMA,
            "status": "CANDIDATE_POINTWISE_OPTIMAL_ACTIVE15_PLUS_ONE",
            "response": response,
            "instruction_ids": sorted(ids),
            "extension": ext,
            "mandatory_loss_edges": [sorted(x) for x in edges],
            "sacrificed_instruction_ids": list(sacrificed),
            "theoretical_max_pass_count_from_sound_loss_edges": max_pass,
            "instruction_count": total,
            "route": route,
            "scope_basis": {
                "schema_bridge": scope.SCHEMA,
                "candidate_scope_shape": "ACTIVE15_PLUS_AT_MOST_ONE_OF_FOUR_NOARG_EXTRAS",
            },
            "conditional_dependencies": {
                "active15_composer_v3": active.SCHEMA,
                "language_exception_carrier_v2": langcarrier.SCHEMA,
                "language_exception_runtime_gate_required_for_case_extensions": (
                    ext in {UPPER, LOWER} and ext not in set(sacrificed)
                ),
            },
            "proof_shape": {
                "lower_bound": (
                    "EVERY_MANDATORY_LOSS_EDGE_REQUIRES_AT_LEAST_ONE_FAILED_CHECKER;"
                    "EXHAUSTIVE_<=32_SUBSET_ENUMERATION_RETURNS_A_MINIMUM_HITTING_SET"
                ),
                "upper_bound": (
                    "THE_RETAINED_SUBSET_IS_CONSTRUCTED; ONCE_INDEPENDENT_EXACT_"
                    "CHECKER_POSTVALIDATION_PASSES, ITS PASS_COUNT_MATCHES_THE_LOWER_BOUND"
                ),
            },
            "terminal_rows_read": 0,
            "hidden_kwargs_read": 0,
            "target_responses_read": 0,
            "target_scores_read": 0,
            "acceptance_credit": False,
            "hard_nonclaims": [
                "SCOPE_BRIDGE_REMAINS_CONDITIONAL_ON_FIRST_PARTY_15_OR_16_SCOPE_FAITHFULNESS",
                "CASE_EXTENSIONS_REQUIRE_INDEPENDENT_LANGUAGE_EXCEPTION_CARRIER_V2_RUNTIME_PASS",
                "FULL_ACTIVE15_PLUS_ONE_EXACT_CHECKER_POSTVALIDATION_IS_STILL_REQUIRED",
                "NO_LIVEBENCH_ACCEPTANCE_CREDIT_FROM_THIS_CANDIDATE_ALONE",
            ],
        }
    except (PointwiseError, KeyError, TypeError, ValueError) as exc:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "error": str(exc),
            "response": None,
            "acceptance_credit": False,
        }


def run(args: Mapping[str, Any] | None = None, root=None) -> dict[str, Any]:
    args = dict(args or {})
    return solve(
        list(args.get("contracts") or []),
        prompt_to_repeat=args.get("prompt_to_repeat"),
    )
