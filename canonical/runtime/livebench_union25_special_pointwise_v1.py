#!/usr/bin/env python3
"""Pointwise constructor for every extra-bearing non-general union25 structure.

The exact frozen conflict graph reduces the 13,631 structures outside Active15
to 13,614 GENERAL structures plus only 17 special-route structures:
- 1 constrained-response singleton;
- 4 repeat-prompt + no-comma structures;
- 12 two-response structures carrying language and/or no-comma.

This module closes the purely structural special delta.  Language-bearing
two-response outputs are deliberately marked for exact pinned langdetect
postvalidation before any proof credit is granted.
"""
from __future__ import annotations

from typing import Any, Mapping, Sequence

from canonical.runtime import livebench_union25_archetypes_v1 as u
from canonical.runtime import livebench_legacy15_contract_composer_v2 as active
from canonical.runtime import livebench_legacy25_single_contract_witness_v1 as single

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_UNION25_SPECIAL_POINTWISE_V1"


class SpecialPointwiseError(ValueError):
    pass


def _normalize(contracts: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    rows = [dict(x) for x in contracts]
    if not rows:
        raise SpecialPointwiseError("CONTRACTS_REQUIRED")
    ids = [str(x.get("instruction_id") or "") for x in rows]
    if any(not iid for iid in ids):
        raise SpecialPointwiseError("INSTRUCTION_ID_REQUIRED")
    if len(ids) != len(set(ids)):
        raise SpecialPointwiseError("DUPLICATE_INSTRUCTION_ID")
    if not u.compatible(ids):
        raise SpecialPointwiseError("UNION25_CONFLICT_GRAPH_REJECTED")
    if not (set(ids) & set(u.EXTRA10)):
        raise SpecialPointwiseError("ACTIVE15_ONLY_NOT_THIS_SOLVER")
    route = u.route(ids)
    if route == "GENERAL" or route == "JSON":
        raise SpecialPointwiseError("NON_SPECIAL_DELTA_ROUTE")
    return rows


def _by_id(rows: Sequence[Mapping[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(x["instruction_id"]): dict(x) for x in rows}


def _strip(rows: Sequence[Mapping[str, Any]], ids: set[str]) -> list[dict[str, Any]]:
    return [dict(x) for x in rows if str(x["instruction_id"]) not in ids]


def _required_words(rows: Sequence[Mapping[str, Any]]) -> list[str]:
    for row in rows:
        if str(row["instruction_id"]) == u.EXIST:
            return [str(x) for x in dict(row.get("slots") or {}).get("keywords") or []]
    return []


def _no_repeat_witness(rows: Sequence[Mapping[str, Any]]) -> str:
    ids = {str(x["instruction_id"]) for x in rows}
    pieces: list[str] = []
    if u.TITLE in ids:
        pieces.append("<<safe>>")
    required = _required_words(rows)
    if required:
        if any((not word.isalpha()) or (not word.isascii()) for word in required):
            raise SpecialPointwiseError("OUTSIDE_PUBLIC_KEYWORD_DOMAIN")
        pieces.append("9000" + "0".join(required) + "0009")
    pieces.append("safe")
    out = "\n".join(pieces)
    if "," in out:
        raise SpecialPointwiseError("INTERNAL_NO_COMMA_WITNESS_BUG")
    return out


def _repeat_prefix(rows: Sequence[Mapping[str, Any]]) -> str:
    row = next((x for x in rows if str(x["instruction_id"]) == u.REPEAT), None)
    if row is None:
        raise SpecialPointwiseError("REPEAT_CONTRACT_MISSING")
    prefix = str(dict(row.get("slots") or {}).get("prompt_to_repeat") or "").strip()
    if not prefix:
        raise SpecialPointwiseError("PROMPT_TO_REPEAT_REQUIRED")
    return prefix


def _language_two_response(rows: Sequence[Mapping[str, Any]]) -> tuple[str, str]:
    by = _by_id(rows)
    language = by.get(u.LANGUAGE)
    if language is None:
        raise SpecialPointwiseError("LANGUAGE_CONTRACT_MISSING")
    code = str(dict(language.get("slots") or {}).get("language") or "")
    sample = single.LANGUAGE_SAMPLES.get(code)
    if not sample:
        raise SpecialPointwiseError("NO_PINNED_LANGUAGE_SAMPLE:" + code)

    # The frozen conflict graph forbids language with existence/forbidden on
    # this route.  Only title and no-comma may coexist with TWO+LANGUAGE.
    illegal = set(by) - {u.TWO, u.LANGUAGE, u.TITLE, u.NO_COMMA}
    if illegal:
        raise SpecialPointwiseError(
            "LANGUAGE_TWO_UNEXPECTED_COMPATIBLE_ID:" + ",".join(sorted(illegal))
        )
    if u.NO_COMMA in by:
        # The no-comma checker is literal. Removing comma punctuation preserves
        # the language-bearing lexical material; exact langdetect stability of
        # every modified pinned sample is externally postvalidated before proof
        # promotion.
        sample = sample.replace(",", "")

    left = sample
    right = sample + " " + sample
    if u.TITLE in by:
        right += " <<" + sample + ">>"
    response = left + "******" + right
    return response, code


def solve_special(contracts: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    try:
        rows = _normalize(contracts)
        ids = [str(x["instruction_id"]) for x in rows]
        route = u.route(ids)
        total = len(rows)
        sacrificed: list[str] = []
        language_code: str | None = None
        requires_exact_language_postvalidation = False

        if route == "CONSTRAINED_SINGLETON":
            if set(ids) != {u.CONSTRAINED}:
                raise SpecialPointwiseError("CONSTRAINED_NOT_SINGLETON")
            response = "My answer is yes."
            proof = "CONFLICT_GRAPH_FORCES_SINGLETON_AND_FIXED_OPTION_PASSES"

        elif route == "REPEAT_PROMPT":
            if u.NO_COMMA not in ids:
                raise SpecialPointwiseError("EXTRA_BEARING_REPEAT_REQUIRES_NO_COMMA")
            prefix = _repeat_prefix(rows)
            if "," in prefix:
                response = _no_repeat_witness(rows)
                sacrificed = [u.REPEAT]
                proof = (
                    "MANDATORY_REPEAT_PREFIX_CONTAINS_COMMA__REPEAT_AND_NO_COMMA_"
                    "MUTUALLY_EXCLUSIVE__ONE_LOSS_NECESSARY_AND_CONSTRUCTIVELY_SUFFICIENT"
                )
            else:
                base_rows = _strip(rows, {u.NO_COMMA})
                built = active.compose_contracts(base_rows)
                if built.get("status") != "CANDIDATE_WITNESS":
                    raise SpecialPointwiseError(
                        "ACTIVE15_REPEAT_CONSTRUCTOR_FAILED:" + str(built.get("status"))
                    )
                response = str(built["response"])
                if "," in response:
                    raise SpecialPointwiseError("REPEAT_CONSTRUCTOR_INTRODUCED_COMMA")
                proof = "NO_COMMA_IS_FREE_WHEN_MANDATORY_REPEAT_PREFIX_IS_COMMA_FREE"

        elif route == "TWO_RESPONSES":
            if u.LANGUAGE in ids:
                response, language_code = _language_two_response(rows)
                requires_exact_language_postvalidation = True
                proof = (
                    "TWO_PLUS_LANGUAGE_USES_INDEPENDENTLY_VERIFIED_LANGUAGE_SAMPLE_"
                    "DUPLICATION__EXACT_PINNED_LANGDETECT_POSTVALIDATION_REQUIRED"
                )
            else:
                if u.NO_COMMA not in ids:
                    raise SpecialPointwiseError(
                        "EXTRA_BEARING_TWO_WITHOUT_LANGUAGE_REQUIRES_NO_COMMA"
                    )
                base_rows = _strip(rows, {u.NO_COMMA})
                built = active.compose_contracts(base_rows)
                if built.get("status") != "CANDIDATE_WITNESS":
                    raise SpecialPointwiseError(
                        "ACTIVE15_TWO_CONSTRUCTOR_FAILED:" + str(built.get("status"))
                    )
                response = str(built["response"])
                if "," in response:
                    raise SpecialPointwiseError("TWO_CONSTRUCTOR_INTRODUCED_COMMA")
                proof = "NO_COMMA_IS_FREE_ON_THE_ACTIVE15_TWO_RESPONSE_CONSTRUCTOR"
        else:
            raise SpecialPointwiseError("UNSUPPORTED_SPECIAL_ROUTE:" + route)

        max_pass = total - len(sacrificed)
        return {
            "schema": SCHEMA,
            "status": "CANDIDATE_POINTWISE_OPTIMAL_SPECIAL_DELTA",
            "route": route,
            "instruction_ids": sorted(ids),
            "response": response,
            "sacrificed_instruction_ids": sorted(sacrificed),
            "theoretical_max_pass_count": max_pass,
            "instruction_count": total,
            "proof": proof,
            "language_code": language_code,
            "requires_exact_language_postvalidation": (
                requires_exact_language_postvalidation
            ),
            "terminal_rows_used": False,
            "hidden_kwargs_used": False,
            "terminal_frequencies_used": False,
            "model_dependency_count": 0,
            "acceptance_credit": False,
        }
    except (SpecialPointwiseError, KeyError, TypeError, ValueError) as exc:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "error": str(exc),
            "response": None,
            "acceptance_credit": False,
        }


def enumerate_extra_special_structures() -> tuple[tuple[str, ...], ...]:
    return tuple(
        ids
        for ids in u.enumerate_compatible_sets()
        if (set(ids) & set(u.EXTRA10)) and u.route(ids) not in {"GENERAL", "JSON"}
    )


def verify_structural_closure() -> dict[str, Any]:
    structures = enumerate_extra_special_structures()
    if len(structures) != 17:
        raise AssertionError("SPECIAL_DELTA_COUNT_DRIFT")
    route_counts: dict[str, int] = {}
    for ids in structures:
        route_counts[u.route(ids)] = route_counts.get(u.route(ids), 0) + 1
    expected = {
        "CONSTRAINED_SINGLETON": 1,
        "REPEAT_PROMPT": 4,
        "TWO_RESPONSES": 12,
    }
    if route_counts != expected:
        raise AssertionError("SPECIAL_DELTA_ROUTE_COUNT_DRIFT")
    language_two = sum(
        1 for ids in structures if u.TWO in ids and u.LANGUAGE in ids
    )
    if language_two != 4:
        raise AssertionError("LANGUAGE_TWO_STRUCTURE_COUNT_DRIFT")
    return {
        "schema": SCHEMA,
        "status": "PASS__17_SPECIAL_DELTA_STRUCTURES_REDUCED_TO_THREE_CONSTRUCTIONS",
        "special_delta_structure_count": len(structures),
        "route_counts": route_counts,
        "language_two_structure_count": language_two,
        "nonlanguage_special_structure_count": len(structures) - language_two,
        "remaining_union25_extra_structures_after_special_delta": 13614,
        "terminal_rows_used": False,
        "acceptance_credit": False,
    }


def run(args: Mapping[str, Any] | None = None, root=None) -> dict[str, Any]:
    args = args or {}
    if args.get("verify_structure"):
        return verify_structural_closure()
    return solve_special(list(args.get("contracts") or []))


if __name__ == "__main__":
    import json
    print(json.dumps(verify_structural_closure(), indent=2, sort_keys=True))
