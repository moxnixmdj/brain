#!/usr/bin/env python3
"""Exact easy-layer reduction for the public LiveBench union25 extension.

This module extends the already-closed Active15 construction with the four
extra families whose checker semantics are purely syntactic:

* detectable_content:number_placeholders
* detectable_format:number_highlighted_sections
* punctuation:no_comma
* detectable_format:constrained_response

The key result is that 2,058 union25 structures containing only these extra
families collapse to 2,054 zero-new-loss structures plus exactly four
repeat_prompt + no_comma structures.  In those four, the only new semantic
coordinate is visible and exact: a comma in prompt_to_repeat.  Because the
RepeatPromptThenAnswer checker requires the response to start with the repeated
prompt (case-insensitively but punctuation-preservingly), a comma in that prompt
makes RepeatPromptThenAnswer and CommaChecker jointly impossible.  Without such
a comma, both are simultaneously satisfiable.

No terminal rows, hidden kwargs, frequencies, responses, or target scores are
read.  This module grants no acceptance credit by itself.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Mapping, Sequence

from canonical.runtime import livebench_legacy15_contract_composer_v2 as active
from canonical.runtime import livebench_union25_archetypes_v1 as union

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_UNION25_EASY_EXTENSION_V1"

EXPECTED_BLOBS = {
    "canonical/runtime/livebench_legacy15_contract_composer_v2.py":
        "d73ec366b32252996258eae6d10d67d4d6a5e042",
    "canonical/runtime/livebench_union25_archetypes_v1.py":
        "8c68e63bbc1e1b843f076dbcd8c4bfae11d4cc2a",
}

PLACEHOLDERS = union.PLACEHOLDERS
HIGHLIGHTS = union.HIGHLIGHTS
NO_COMMA = union.NO_COMMA
CONSTRAINED = union.CONSTRAINED

EASY_EXTRA = frozenset({PLACEHOLDERS, HIGHLIGHTS, NO_COMMA, CONSTRAINED})
EXPECTED_EASY_SIGNATURES = 8
EXPECTED_EASY_STRUCTURES = 2058
EXPECTED_REPEAT_NO_COMMA_STRUCTURES = 4
EXPECTED_ZERO_NEW_LOSS_STRUCTURES = 2054

CONSTRAINED_WITNESS = "My answer is yes."


class EasyExtensionError(ValueError):
    pass


def _root() -> Path:
    return Path(__file__).resolve().parents[2]


def _git_blob_sha(path: Path) -> str:
    raw = path.read_bytes()
    return hashlib.sha1(
        b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw
    ).hexdigest()


def _verify_bindings() -> dict[str, str]:
    root = _root()
    got = {rel: _git_blob_sha(root / rel) for rel in EXPECTED_BLOBS}
    bad = {
        rel: {"expected": EXPECTED_BLOBS[rel], "got": got[rel]}
        for rel in EXPECTED_BLOBS
        if got[rel] != EXPECTED_BLOBS[rel]
    }
    if bad:
        raise AssertionError("EXACT_SUBJECT_BLOB_MISMATCH:" + repr(bad))
    return got


def _by_id(contracts: Sequence[Mapping[str, Any]]) -> dict[str, Mapping[str, Any]]:
    out: dict[str, Mapping[str, Any]] = {}
    for c in contracts:
        iid = str(c.get("instruction_id") or "")
        if not iid or iid in out:
            raise EasyExtensionError("EMPTY_OR_DUPLICATE_INSTRUCTION_ID:" + iid)
        out[iid] = c
    return out


def _slots(c: Mapping[str, Any]) -> dict[str, Any]:
    return dict(c.get("slots") or {})


def _extra_ids(ids: set[str]) -> set[str]:
    return ids & set(union.EXTRA10)


def _easy_only_structure(ids: Sequence[str]) -> bool:
    s = set(ids)
    extra = _extra_ids(s)
    return bool(extra) and extra <= EASY_EXTRA


def _repeat_prompt_has_comma(by_id: Mapping[str, Mapping[str, Any]]) -> bool:
    c = by_id.get(active.REPEAT)
    if not c:
        return False
    return "," in str(_slots(c).get("prompt_to_repeat") or "")


def _insert_inside_terminal_wrappers(
    response: str,
    active_by_id: Mapping[str, Mapping[str, Any]],
    payload: str,
) -> str:
    """Insert syntax-only payload without disturbing quote/end/postscript gates."""
    if not payload:
        return response

    quote = active.QUOTE in active_by_id
    body = str(response)
    if quote:
        if len(body) < 2 or body[0] != '"' or body[-1] != '"':
            raise EasyExtensionError("ACTIVE_QUOTATION_WITNESS_DRIFT")
        body = body[1:-1]

    if active.END in active_by_id:
        phrase = str(_slots(active_by_id[active.END]).get("end_phrase") or "").strip()
        if not phrase or not body.rstrip().lower().endswith(phrase.lower()):
            raise EasyExtensionError("ACTIVE_END_WITNESS_DRIFT")
        trimmed = body.rstrip()
        prefix = trimmed[:-len(phrase)].rstrip()
        body = (prefix + " " + payload + " " + phrase).strip()
    else:
        body = (body.rstrip() + " " + payload).strip()

    if quote:
        body = '"' + body + '"'
    return body


def extend_post_sacrifice_contracts(
    contracts: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Construct a witness for easy-extra structures or expose the exact loss cut.

    The caller must provide a conflict-compatible set whose non-easy IDs are in
    Active15 and whose Active15 subset is already post-sacrifice satisfiable.
    """
    by_id = _by_id(contracts)
    ids = set(by_id)

    if not union.compatible(tuple(ids)):
        raise EasyExtensionError("ID_CONFLICT_OR_UNKNOWN")
    if not _easy_only_structure(tuple(ids)):
        raise EasyExtensionError("NOT_EASY_EXTENSION_STRUCTURE")

    extras = _extra_ids(ids)

    if CONSTRAINED in extras:
        if ids != {CONSTRAINED}:
            raise EasyExtensionError("CONSTRAINED_SINGLETON_CONFLICT_GRAPH_DRIFT")
        return {
            "schema": SCHEMA,
            "status": "CANDIDATE_WITNESS",
            "response": CONSTRAINED_WITNESS,
            "new_mandatory_losses": [],
            "route": "CONSTRAINED_SINGLETON",
            "terminal_data_used": False,
            "acceptance_credit": False,
        }

    active_contracts = [
        c for c in contracts
        if str(c.get("instruction_id") or "") in union.ACTIVE15
    ]
    active_by_id = _by_id(active_contracts) if active_contracts else {}

    if active_contracts:
        built = active.compose_contracts(active_contracts)
        if built.get("status") != "CANDIDATE_WITNESS":
            return {
                "schema": SCHEMA,
                "status": "ACTIVE_POST_SACRIFICE_PRECONDITION_NOT_MET",
                "active_result": built,
                "new_mandatory_losses": [],
                "terminal_data_used": False,
                "acceptance_credit": False,
            }
        response = str(built["response"])
    else:
        response = "9000001"

    if NO_COMMA in extras and _repeat_prompt_has_comma(active_by_id):
        # RepeatPromptThenAnswer requires the response to begin with the visible
        # prompt text. Therefore every repeat-passing response necessarily
        # contains this comma, while CommaChecker forbids every comma.
        return {
            "schema": SCHEMA,
            "status": "PROVED_ONE_NEW_MANDATORY_LOSS",
            "new_mandatory_losses": [
                {
                    "coordinate": "repeat_prompt_contains_comma",
                    "conflicting_ids": [active.REPEAT, NO_COMMA],
                    "minimum_sacrifice_count": 1,
                }
            ],
            "response": response,
            "terminal_data_used": False,
            "acceptance_credit": False,
        }

    payloads: list[str] = []
    if PLACEHOLDERS in extras:
        n = int(_slots(by_id[PLACEHOLDERS]).get("num_placeholders", 0))
        if not 1 <= n <= 4:
            raise EasyExtensionError("OUTSIDE_PUBLIC_PLACEHOLDER_DOMAIN")
        payloads.extend("[0]" for _ in range(n))

    if HIGHLIGHTS in extras:
        n = int(_slots(by_id[HIGHLIGHTS]).get("num_highlights", 0))
        if not 1 <= n <= 4:
            raise EasyExtensionError("OUTSIDE_PUBLIC_HIGHLIGHT_DOMAIN")
        payloads.extend("*0*" for _ in range(n))

    response = _insert_inside_terminal_wrappers(
        response, active_by_id, " ".join(payloads)
    )

    if NO_COMMA in extras and "," in response:
        # For the frozen Active15 composer the only uncontrolled comma carrier is
        # repeat_prompt, already handled above. Anything else is source drift.
        raise EasyExtensionError("UNEXPECTED_COMMA_OUTSIDE_REPEAT_PROMPT")

    return {
        "schema": SCHEMA,
        "status": "CANDIDATE_WITNESS",
        "response": response,
        "new_mandatory_losses": [],
        "route": "EASY_EXTENSION",
        "terminal_data_used": False,
        "acceptance_credit": False,
    }


def verify() -> dict[str, Any]:
    bindings = _verify_bindings()
    union_out = union.verify()
    if union_out["compatible_total"] != 14559:
        raise AssertionError("UNION25_STRUCTURE_DRIFT")

    structures = [
        ids for ids in union.enumerate_compatible_sets()
        if _easy_only_structure(ids)
    ]
    signatures = {
        tuple(iid for iid in union.ALL_IDS if iid in set(ids) & EASY_EXTRA)
        for ids in structures
    }
    repeat_no_comma = [
        ids for ids in structures
        if active.REPEAT in ids and NO_COMMA in ids
    ]

    if len(structures) != EXPECTED_EASY_STRUCTURES:
        raise AssertionError("EASY_STRUCTURE_COUNT_DRIFT")
    if len(signatures) != EXPECTED_EASY_SIGNATURES:
        raise AssertionError("EASY_SIGNATURE_COUNT_DRIFT")
    if len(repeat_no_comma) != EXPECTED_REPEAT_NO_COMMA_STRUCTURES:
        raise AssertionError("REPEAT_NO_COMMA_COUNT_DRIFT")

    zero_new_loss = len(structures) - len(repeat_no_comma)
    if zero_new_loss != EXPECTED_ZERO_NEW_LOSS_STRUCTURES:
        raise AssertionError("ZERO_NEW_LOSS_COUNT_DRIFT")

    return {
        "schema": SCHEMA,
        "status": (
            "PASS__2058_EASY_EXTRA_STRUCTURES_REDUCED_TO_"
            "2054_ZERO_NEW_LOSS_PLUS_4_VISIBLE_REPEAT_COMMA_CASES"
        ),
        "source_bindings": bindings,
        "easy_extra_families": sorted(EASY_EXTRA),
        "easy_extra_signature_count": len(signatures),
        "easy_extra_structure_count": len(structures),
        "zero_new_mandatory_loss_structure_count": zero_new_loss,
        "repeat_prompt_no_comma_structure_count": len(repeat_no_comma),
        "only_new_semantic_coordinate": {
            "name": "repeat_prompt_contains_comma",
            "visible_parameter": True,
            "if_false": "NO_NEW_MANDATORY_LOSS",
            "if_true": (
                "REPEAT_PROMPT_AND_NO_COMMA_ARE_JOINTLY_UNSAT__"
                "EXACTLY_ONE_OF_THE_TWO_CHECKERS_MUST_BE_SACRIFICED"
            ),
        },
        "syntactic_constructions": {
            "number_placeholders": "[0] repeated N times, N in 1..4",
            "number_highlighted_sections": "*0* repeated N times, N in 1..4",
            "constrained_response": CONSTRAINED_WITNESS,
            "no_comma": "preserved by every controlled Active15 constructor literal",
        },
        "word_upper_bound_effect": (
            "PLACEHOLDERS_AND_HIGHLIGHTS_ADD_AT_MOST_8_REGEX_WORDS; "
            "ACTIVE15_UNPADDED_CEILING_48_PLUS_8_EQUALS_56_LT_PUBLIC_WORD_MIN_100"
        ),
        "deleted_problem": (
            "NO_RAW_SLOT_CARTESIAN_SEARCH_IS_REQUIRED_FOR_THE_FOUR_EASY_EXTRA_FAMILIES"
        ),
        "next_load_bearing_problem": (
            "CLOSE_THE_REMAINING_148_EXTRA_SIGNATURES_INVOLVING_KEYWORD_FREQUENCY_"
            "LETTER_FREQUENCY_LANGUAGE_OR_CASE_FAMILIES"
        ),
        "terminal_rows_used": False,
        "hidden_kwargs_used": False,
        "target_scores_used": False,
        "acceptance_credit": False,
        "hard_nonclaims": [
            "EXACT_CHECKER_POSTVALIDATION_OF_THIS_EXTENSION_IS_STILL_REQUIRED",
            "THIS_MODULE_DOES_NOT_CLOSE_THE_REMAINING_148_EXTRA_SIGNATURES",
            "NO_LIVEBENCH_ACCEPTANCE_FAMILY_CAPABILITY_OR_OWNERSHIP_CREDIT",
        ],
    }


def run(args: Mapping[str, Any] | None = None, root=None) -> dict[str, Any]:
    args = args or {}
    contracts = list(args.get("contracts") or [])
    return extend_post_sacrifice_contracts(contracts) if contracts else verify()


if __name__ == "__main__":
    import json
    print(json.dumps(verify(), indent=2, sort_keys=True))
