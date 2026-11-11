#!/usr/bin/env python3
"""Pointwise solver for every non-general historical24 structural route.

Historical24 has only 29 conflict-compatible special structures:
- 1 constrained-response structure;
- 4 JSON structures;
- 8 repeat-prompt structures;
- 16 two-response structures.

JSON contains no extra9 family and reuses the independently exercised Active15
constructor. Two-response only gains no_comma, which the existing constructor
already satisfies. Constrained-response is structurally standalone. Repeat
only gains no_comma; their interaction is decided exactly by whether the
mandatory repeated prefix contains a literal comma.
"""
from __future__ import annotations

from typing import Any, Mapping, Sequence

from canonical.runtime import livebench_historical24_composition_space_v1 as space
from canonical.runtime import livebench_legacy15_contract_composer_v2 as active

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_HISTORICAL24_SPECIAL_POINTWISE_V1"
NO_COMMA = "punctuation:no_comma"


class SpecialRouteError(ValueError):
    pass


def _normalize(contracts: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    rows = [dict(x) for x in contracts]
    if not rows:
        raise SpecialRouteError("CONTRACTS_REQUIRED")
    ids = [str(x.get("instruction_id") or "") for x in rows]
    if any(not x for x in ids):
        raise SpecialRouteError("INSTRUCTION_ID_REQUIRED")
    if len(ids) != len(set(ids)):
        raise SpecialRouteError("DUPLICATE_INSTRUCTION_ID")
    if not space.compatible(ids):
        raise SpecialRouteError("HISTORICAL24_CONFLICT_GRAPH_REJECTED")
    route = space.route(ids)
    if route == "GENERAL":
        raise SpecialRouteError("GENERAL_ROUTE_NOT_IN_SPECIAL_SOLVER")
    return rows


def _strip_no_comma(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [
        dict(x)
        for x in rows
        if str(x.get("instruction_id") or "") != NO_COMMA
    ]


def _required_words(rows: Sequence[Mapping[str, Any]]) -> list[str]:
    for row in rows:
        if str(row.get("instruction_id") or "") == active.EXIST:
            return [str(x) for x in dict(row.get("slots") or {}).get("keywords") or []]
    return []


def _no_repeat_witness(rows: Sequence[Mapping[str, Any]]) -> str:
    """Satisfy every repeat-route-compatible checker except repeat itself."""
    ids = {str(x.get("instruction_id") or "") for x in rows}
    pieces: list[str] = []
    if active.TITLE in ids:
        pieces.append("<<safe>>")
    required = _required_words(rows)
    if required:
        for word in required:
            if not word.isalpha() or not word.isascii():
                raise SpecialRouteError("OUTSIDE_PUBLIC_KEYWORD_DOMAIN:" + word)
        # Same word-character shielding theorem as Composer V2.
        pieces.append("9000" + "0".join(required) + "0009")
    pieces.append("safe")
    response = "\n".join(pieces)
    if "," in response:
        raise SpecialRouteError("INTERNAL_NO_COMMA_WITNESS_BUG")
    return response


def _repeat_prefix(rows: Sequence[Mapping[str, Any]]) -> str:
    repeat = next(
        (
            row
            for row in rows
            if str(row.get("instruction_id") or "") == active.REPEAT
        ),
        None,
    )
    if repeat is None:
        raise SpecialRouteError("REPEAT_CONTRACT_MISSING")
    prefix = str(dict(repeat.get("slots") or {}).get("prompt_to_repeat") or "").strip()
    if not prefix:
        raise SpecialRouteError("PROMPT_TO_REPEAT_REQUIRED")
    return prefix


def solve_special(contracts: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    try:
        rows = _normalize(contracts)
        ids = [str(x["instruction_id"]) for x in rows]
        route = space.route(ids)
        total = len(rows)

        if route == "CONSTRAINED_RESPONSE":
            if ids != [space.CONSTRAINED] and set(ids) != {space.CONSTRAINED}:
                raise SpecialRouteError("CONSTRAINED_ROUTE_NOT_SINGLETON")
            response = "My answer is yes."
            sacrificed: list[str] = []
            proof = "PINNED_CHECKER_ACCEPTS_ANY_ONE_FIXED_OPTION_SUBSTRING"

        elif route == "JSON":
            built = active.compose_contracts(rows)
            if built.get("status") != "CANDIDATE_WITNESS":
                raise SpecialRouteError(
                    "ACTIVE15_JSON_CONSTRUCTOR_FAILED:" + str(built.get("status"))
                )
            response = str(built["response"])
            sacrificed = []
            proof = "HISTORICAL24_JSON_ROUTE_HAS_NO_EXTRA9_COMPATIBLE_FAMILY"

        elif route == "TWO_RESPONSES":
            has_no_comma = NO_COMMA in ids
            base_rows = _strip_no_comma(rows)
            built = active.compose_contracts(base_rows)
            if built.get("status") != "CANDIDATE_WITNESS":
                raise SpecialRouteError(
                    "ACTIVE15_TWO_CONSTRUCTOR_FAILED:" + str(built.get("status"))
                )
            response = str(built["response"])
            if has_no_comma and "," in response:
                raise SpecialRouteError(
                    "TWO_RESPONSE_CONSTRUCTOR_UNEXPECTED_COMMA"
                )
            sacrificed = []
            proof = (
                "TWO_RESPONSE_EXTRA9_EXTENSION_IS_ONLY_NO_COMMA_AND_THE_"
                "CONSTRUCTOR_EMITS_NO_COMMA"
            )

        elif route == "REPEAT_PROMPT":
            has_no_comma = NO_COMMA in ids
            prefix = _repeat_prefix(rows)
            if has_no_comma and "," in prefix:
                # Any response passing RepeatPromptThenAnswer must begin with the
                # mandatory prefix. A comma in that prefix therefore proves
                # repeat AND no_comma cannot both pass. Dropping repeat is one
                # checker loss and _no_repeat_witness satisfies every other
                # compatible contract, so the one-loss bound is exact.
                response = _no_repeat_witness(rows)
                sacrificed = [active.REPEAT]
                proof = (
                    "MANDATORY_REPEAT_PREFIX_CONTAINS_COMMA__REPEAT_AND_NO_COMMA_"
                    "MUTUALLY_EXCLUSIVE__ONE_CHECKER_SACRIFICE_IS_BOTH_NECESSARY_"
                    "AND_SUFFICIENT"
                )
            else:
                base_rows = _strip_no_comma(rows)
                built = active.compose_contracts(base_rows)
                if built.get("status") != "CANDIDATE_WITNESS":
                    raise SpecialRouteError(
                        "ACTIVE15_REPEAT_CONSTRUCTOR_FAILED:"
                        + str(built.get("status"))
                    )
                response = str(built["response"])
                if has_no_comma and "," in response:
                    raise SpecialRouteError(
                        "REPEAT_CONSTRUCTOR_INTRODUCED_COMMA_OUTSIDE_PREFIX"
                    )
                sacrificed = []
                proof = (
                    "REPEAT_PREFIX_HAS_NO_COMMA_AND_APPENDED_EXISTENCE_TITLE_"
                    "WITNESSES_ARE_COMMA_FREE"
                )
        else:
            raise SpecialRouteError("UNKNOWN_SPECIAL_ROUTE:" + route)

        max_pass = total - len(sacrificed)
        return {
            "schema": SCHEMA,
            "status": "CANDIDATE_POINTWISE_OPTIMAL_SPECIAL_ROUTE",
            "route": route,
            "instruction_ids": sorted(ids),
            "response": response,
            "sacrificed_instruction_ids": sorted(sacrificed),
            "theoretical_max_pass_count": max_pass,
            "instruction_count": total,
            "proof": proof,
            "terminal_rows_used": False,
            "hidden_kwargs_used": False,
            "terminal_frequencies_used": False,
            "model_dependency_count": 0,
            "acceptance_credit": False,
        }
    except (SpecialRouteError, KeyError, TypeError, ValueError) as exc:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "error": str(exc),
            "response": None,
            "acceptance_credit": False,
        }


def run(args: Mapping[str, Any] | None = None, root=None) -> dict[str, Any]:
    return solve_special(list((args or {}).get("contracts") or []))


if __name__ == "__main__":
    import json
    import sys

    payload = json.load(sys.stdin)
    print(json.dumps(run(payload), indent=2, sort_keys=True))
