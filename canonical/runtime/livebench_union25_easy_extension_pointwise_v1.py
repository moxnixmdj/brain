#!/usr/bin/env python3
"""Pointwise-preserving closure for four easy union25 extension families.

This module lifts the already-closed Active15 pointwise planner across:
- detectable_content:number_placeholders
- detectable_format:number_highlighted_sections
- detectable_format:constrained_response
- punctuation:no_comma

The first two are added as punctuation-free numeric witnesses inserted before
any mandatory postscript/end suffix.  Together they add at most eight regex
word tokens, preserving the proved public words(<n) margin because the frozen
Active15 general constructor is bounded below 100 by far more than eight words.

Constrained-response is an isolated structural branch.

No-comma is construction-free on every frozen Active15 route except repeat
prompt.  If a repeat payload itself contains a comma and no-comma is coactive,
the pair is intrinsically incompatible: any string satisfying the exact repeat
prefix checker necessarily contains that comma.  Sacrificing no-comma is then
one provably minimal loss.

This is a candidate until independently postvalidated against the exact frozen
checker bytes.  It grants no acceptance credit by itself.
"""
from __future__ import annotations

import re
from typing import Any, Mapping, Sequence

from canonical.runtime import livebench_legacy15_pointwise_optimal_v1 as active_planner
from canonical.runtime import livebench_legacy15_contract_composer_v2 as active_composer
from canonical.runtime import livebench_union25_extension_structural_quotient_v1 as structural

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_UNION25_EASY_EXTENSION_POINTWISE_V1"

PLACEHOLDERS = "detectable_content:number_placeholders"
HIGHLIGHTS = "detectable_format:number_highlighted_sections"
CONSTRAINED = "detectable_format:constrained_response"
NO_COMMA = "punctuation:no_comma"
EASY4 = frozenset((PLACEHOLDERS, HIGHLIGHTS, CONSTRAINED, NO_COMMA))

REPEAT = active_composer.REPEAT
POSTSCRIPT = active_composer.POSTSCRIPT
END = active_composer.END
QUOTE = active_composer.QUOTE
WORDS = active_composer.WORDS

MAX_PLACEHOLDERS = 4
MAX_HIGHLIGHTS = 4
MIN_PUBLIC_WORD_THRESHOLD = 100


class EasyExtensionError(ValueError):
    pass


def _slots(c: Mapping[str, Any]) -> dict[str, Any]:
    return dict(c.get("slots") or {})


def _by_id(contracts: Sequence[Mapping[str, Any]]) -> dict[str, Mapping[str, Any]]:
    out: dict[str, Mapping[str, Any]] = {}
    for c in contracts:
        iid = str(c.get("instruction_id") or "")
        if not iid or iid in out:
            raise EasyExtensionError("MISSING_OR_DUPLICATE_INSTRUCTION_ID:" + iid)
        out[iid] = c
    return out


def _word_count(text: str) -> int:
    return len(re.findall(r"\w+", str(text), flags=re.UNICODE))


def _neutral_payload(by_id: Mapping[str, Mapping[str, Any]]) -> str:
    pieces: list[str] = []
    if PLACEHOLDERS in by_id:
        n = int(_slots(by_id[PLACEHOLDERS]).get("num_placeholders"))
        if not 1 <= n <= MAX_PLACEHOLDERS:
            raise EasyExtensionError("PLACEHOLDER_DOMAIN_OUTSIDE_1_TO_4")
        pieces.extend("[0]" for _ in range(n))
    if HIGHLIGHTS in by_id:
        n = int(_slots(by_id[HIGHLIGHTS]).get("num_highlights"))
        if not 1 <= n <= MAX_HIGHLIGHTS:
            raise EasyExtensionError("HIGHLIGHT_DOMAIN_OUTSIDE_1_TO_4")
        pieces.extend("*0*" for _ in range(n))
    return " ".join(pieces)


def _insert_before_mandatory_suffix(
    response: str,
    active_by_id: Mapping[str, Mapping[str, Any]],
    payload: str,
) -> str:
    if not payload:
        return response

    text = str(response)
    quoted = QUOTE in active_by_id
    if quoted:
        stripped = text.strip()
        if len(stripped) < 2 or not (
            stripped.startswith('"') and stripped.endswith('"')
        ):
            raise EasyExtensionError("ACTIVE_QUOTATION_SHAPE_DRIFT")
        text = stripped[1:-1]

    insertion = len(text)

    if POSTSCRIPT in active_by_id:
        marker = str(_slots(active_by_id[POSTSCRIPT]).get("postscript_marker") or "")
        if not marker:
            raise EasyExtensionError("POSTSCRIPT_MARKER_REQUIRED")
        idx = text.lower().rfind(marker.lower())
        if idx < 0:
            raise EasyExtensionError("ACTIVE_POSTSCRIPT_MARKER_NOT_FOUND")
        insertion = idx
    elif END in active_by_id:
        phrase = str(_slots(active_by_id[END]).get("end_phrase") or "").strip()
        if not phrase:
            raise EasyExtensionError("END_PHRASE_REQUIRED")
        lowered = text.lower().rstrip()
        if not lowered.endswith(phrase.lower()):
            raise EasyExtensionError("ACTIVE_END_SUFFIX_DRIFT")
        insertion = len(text.rstrip()) - len(phrase)

    left = text[:insertion].rstrip()
    right = text[insertion:].lstrip()
    if right:
        text = left + " " + payload + "\n" + right
    else:
        text = left + " " + payload
    text = text.strip()

    if quoted:
        text = '"' + text + '"'
    return text


def _strict_score(total: int, passed: int) -> float:
    if total <= 0 or not 0 <= passed <= total:
        raise EasyExtensionError("INVALID_PASS_COUNT")
    return ((1.0 if passed == total else 0.0) + passed / total) / 2.0


def solve_contracts(contracts: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    contracts = [dict(c) for c in contracts]
    try:
        by_id = _by_id(contracts)
    except EasyExtensionError as exc:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "error": str(exc),
            "response": None,
            "acceptance_credit": False,
        }

    ids = set(by_id)
    allowed = set(active_planner.composer.archetypes.ACTIVE_IDS) | set(EASY4)
    unknown = sorted(ids - allowed)
    if unknown:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "error": "OUTSIDE_EASY_EXTENSION_SCOPE:" + ",".join(unknown),
            "response": None,
            "acceptance_credit": False,
        }
    if len(ids) > structural.MAX_PUBLIC_INSTRUCTIONS or not structural.compatible(ids):
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "error": "UNION25_STRUCTURAL_CONFLICT_OR_CARDINALITY_VIOLATION",
            "response": None,
            "acceptance_credit": False,
        }

    # The frozen registry makes constrained-response conflict with every family,
    # including itself. Therefore its only admissible set is the singleton.
    if CONSTRAINED in ids:
        if ids != {CONSTRAINED}:
            return {
                "schema": SCHEMA,
                "status": "FAIL_CLOSED",
                "error": "CONSTRAINED_RESPONSE_NOT_SINGLETON",
                "response": None,
                "acceptance_credit": False,
            }
        response = "My answer is yes."
        return {
            "schema": SCHEMA,
            "status": "CANDIDATE_POINTWISE_OPTIMAL_EASY4",
            "response": response,
            "instruction_ids": [CONSTRAINED],
            "sacrificed_instruction_ids": [],
            "theoretical_max_pass_count": 1,
            "instruction_count": 1,
            "theoretical_pointwise_optimum_strict_score": 1.0,
            "proof_shape": "CONSTRAINED_RESPONSE_IS_STRUCTURALLY_ISOLATED",
            "acceptance_credit": False,
            "terminal_rows_used": False,
        }

    active_contracts = [
        c for c in contracts if str(c.get("instruction_id") or "") not in EASY4
    ]
    active_by_id = _by_id(active_contracts) if active_contracts else {}

    if not active_contracts:
        # Easy-only compatible sets. Use one neutral base word so strict
        # evaluation remains nonempty.
        response = "9000001"
        active_sacrificed: list[str] = []
    else:
        planned = active_planner.solve_contracts(active_contracts)
        if planned.get("status") != "CANDIDATE_POINTWISE_OPTIMAL":
            return {
                "schema": SCHEMA,
                "status": "FAIL_CLOSED",
                "error": "ACTIVE15_PLANNER_FAILED:" + str(planned.get("error")),
                "active_planner": planned,
                "response": None,
                "acceptance_credit": False,
            }
        response = str(planned["response"])
        active_sacrificed = list(planned.get("sacrificed_instruction_ids") or [])

    try:
        payload = _neutral_payload(by_id)
        if payload:
            before_words = _word_count(response)
            response = _insert_before_mandatory_suffix(response, active_by_id, payload)
            after_words = _word_count(response)
            added_words = after_words - before_words
            expected_added = (
                int(_slots(by_id[PLACEHOLDERS])["num_placeholders"])
                if PLACEHOLDERS in by_id
                else 0
            ) + (
                int(_slots(by_id[HIGHLIGHTS])["num_highlights"])
                if HIGHLIGHTS in by_id
                else 0
            )
            if added_words != expected_added:
                raise EasyExtensionError(
                    "NEUTRAL_PAYLOAD_WORD_DELTA_DRIFT:"
                    + str(added_words)
                    + ":"
                    + str(expected_added)
                )

            if WORDS in active_by_id:
                ws = _slots(active_by_id[WORDS])
                if str(ws.get("relation")) == "less than":
                    threshold = int(ws.get("num_words"))
                    if threshold < MIN_PUBLIC_WORD_THRESHOLD:
                        raise EasyExtensionError("PUBLIC_WORD_THRESHOLD_DRIFT")
                    if not after_words < threshold:
                        raise EasyExtensionError(
                            "NEUTRAL_PAYLOAD_BROKE_WORD_UPPER_BOUND"
                        )
    except EasyExtensionError as exc:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "error": str(exc),
            "response": None,
            "acceptance_credit": False,
        }

    sacrificed = set(active_sacrificed)
    no_comma_repeat_collision = False
    if NO_COMMA in by_id:
        if "," in response:
            if REPEAT not in active_by_id:
                return {
                    "schema": SCHEMA,
                    "status": "FAIL_CLOSED",
                    "error": "UNEXPECTED_COMMA_OUTSIDE_REPEAT_PAYLOAD",
                    "response": None,
                    "acceptance_credit": False,
                }
            repeat_payload = str(
                _slots(active_by_id[REPEAT]).get("prompt_to_repeat") or ""
            ).strip()
            if "," not in repeat_payload:
                return {
                    "schema": SCHEMA,
                    "status": "FAIL_CLOSED",
                    "error": "COMMA_NOT_EXPLAINED_BY_REPEAT_PAYLOAD",
                    "response": None,
                    "acceptance_credit": False,
                }
            # Exact lower bound: any response passing RepeatPromptThenAnswer must
            # start with the literal prompt_to_repeat, so a comma in that prefix
            # makes NoComma impossible simultaneously.
            sacrificed.add(NO_COMMA)
            no_comma_repeat_collision = True

    total = len(contracts)
    max_pass = total - len(sacrificed)
    return {
        "schema": SCHEMA,
        "status": "CANDIDATE_POINTWISE_OPTIMAL_EASY4",
        "response": response,
        "instruction_ids": sorted(ids),
        "sacrificed_instruction_ids": sorted(sacrificed),
        "theoretical_max_pass_count": max_pass,
        "instruction_count": total,
        "theoretical_pointwise_optimum_strict_score": _strict_score(
            total, max_pass
        ),
        "proof_shape": {
            "placeholders": (
                "AT_MOST_FOUR_PUNCTUATION_FREE_NUMERIC_BRACKET_WITNESSES"
            ),
            "highlights": (
                "AT_MOST_FOUR_PUNCTUATION_FREE_NUMERIC_MARKDOWN_WITNESSES"
            ),
            "combined_added_regex_word_tokens_max": 8,
            "word_upper_bound_guard": (
                "RUNTIME_RECHECKED_AFTER_INSERTION__PUBLIC_LESS_THAN_THRESHOLD_MIN_100"
            ),
            "constrained_response": "STRUCTURALLY_ISOLATED_SINGLETON",
            "no_comma": (
                "FREE_ON_FROZEN_CONSTRUCTED_ROUTES_EXCEPT_LITERAL_REPEAT_PREFIX"
            ),
            "repeat_comma_collision": no_comma_repeat_collision,
        },
        "terminal_rows_used": False,
        "hidden_kwargs_used": False,
        "terminal_frequencies_used": False,
        "target_scores_used": False,
        "model_dependency_count": 0,
        "acceptance_credit": False,
        "capability_credit": False,
        "ownership_credit": False,
        "hard_nonclaims": [
            "THIS_CLOSES_ONLY_EASY4_OF_THE_UNION25_MINUS_ACTIVE15_EXTENSION",
            "THE_SIX_HARD_EXTENSION_FAMILIES_REMAIN_OPEN",
            "UNION25_POINTWISE_OPTIMALITY_IS_NOT_YET_PROVED",
        ],
    }


def run(args: Mapping[str, Any] | None = None, root=None) -> dict[str, Any]:
    return solve_contracts(list((args or {}).get("contracts") or []))


if __name__ == "__main__":
    import json
    import sys
    payload = json.load(sys.stdin)
    print(json.dumps(run(payload), indent=2, sort_keys=True))
