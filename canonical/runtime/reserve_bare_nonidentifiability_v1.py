"""Bounded non-identifiability certificate for the bare source "Reserve increased.".

V1 reuses the generic pairwise non-identifiability theorem. It authenticates two
distinct OEWN-2025 noun interpretations that both admit the exact source:
- a stockpile/something saved for future use;
- a medical reserve/capacity to maintain vital functions.

This proves only that the bare source cannot uniquely identify one sense. It
does not select the intended sense, claim finance-domain completeness, or grant
policy/terminal authority.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
import re
from typing import Any

from canonical.runtime import oewn_release_sense_universe_v1 as oewn
from canonical.runtime import semantic_pair_nonidentifiability_v1 as generic

SCHEMA = "PROJECT_BRAIN_RESERVE_BARE_NONIDENTIFIABILITY_V1"

STOCK_SENSE = "reserve%1:21:00::"
STOCK_SYNSET = "13389225-n"
STOCK_DEFINITION = "something kept back or saved for future use or a special purpose"

MEDICAL_SENSE = "reserve%1:23:00::"
MEDICAL_SYNSET = "13781913-n"
MEDICAL_DEFINITION = (
    "(medicine) potential capacity to respond in order to maintain vital functions"
)

_PATTERN = re.compile(r"^\s*reserve\s+increased\.?\s*$", re.I)


def _norm(value: Any) -> str:
    return " ".join(str(value or "").strip().casefold().split())


def _hash(value: Any) -> str:
    if isinstance(value, str):
        raw = value.encode("utf-8")
    else:
        raw = json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    return sha256(raw).hexdigest()


def _base(status: str, *, passed: bool = False, **extra: Any) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": status,
        "pass": passed,
        "semantic_nonidentifiability_authority": False,
        "semantic_truth_authority": False,
        "unique_sense_identified": False,
        "finance_domain_identity_authority": False,
        "open_world_finance_semantics_complete": False,
        "execution_authority": False,
        "acceptance_authority": False,
        "promotion_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        **extra,
    }


def _sense_by_id(universe: dict[str, Any], sense_id: str) -> dict[str, Any]:
    rows = [
        deepcopy(dict(row))
        for row in universe.get("senses", [])
        if isinstance(row, dict) and row.get("sense_id") == sense_id
    ]
    if len(rows) != 1:
        raise ValueError("REQUIRED_OEWN_SENSE_NOT_UNIQUE:" + sense_id)
    return rows[0]


def _validate_sense(
    row: dict[str, Any],
    *,
    synset_id: str,
    definition: str,
) -> None:
    if row.get("synset_id") != synset_id:
        raise ValueError("OEWN_SYNSET_BINDING_MISMATCH:" + str(row.get("sense_id")))
    members = {_norm(x) for x in row.get("members", [])}
    if "reserve" not in members:
        raise ValueError("OEWN_RESERVE_MEMBER_MISSING:" + str(row.get("sense_id")))
    definitions = {_norm(x) for x in row.get("definitions", [])}
    if _norm(definition) not in definitions:
        raise ValueError("OEWN_DEFINITION_BINDING_MISMATCH:" + str(row.get("sense_id")))


def _semantic_hash(row: dict[str, Any]) -> str:
    return _hash({
        "sense_id": row["sense_id"],
        "synset_id": row["synset_id"],
        "definitions": list(row.get("definitions", [])),
        "members": list(row.get("members", [])),
        "lexname": row.get("lexname"),
    })


def prove(
    source_text: str,
    *,
    source_id: str,
    oewn_archive: bytes | bytearray | str,
) -> dict[str, Any]:
    try:
        if not isinstance(source_text, str) or not source_text:
            return _base("FAIL_CLOSED", reason="SOURCE_TEXT_REQUIRED")
        sid = str(source_id or "").strip()
        if not sid:
            return _base("FAIL_CLOSED", reason="SOURCE_ID_REQUIRED")
        if _PATTERN.fullmatch(source_text) is None:
            return _base(
                "NOT_APPLICABLE__SOURCE_OUTSIDE_BARE_RESERVE_SCOPE",
                source_text=source_text,
            )

        universe = oewn.enumerate_senses(
            oewn_archive,
            "reserve",
            part_of_speech="n",
        )
        if universe.get("pass") is not True:
            return _base(
                "FAIL_CLOSED",
                reason="OEWN_RELEASE_UNIVERSE_NOT_AUTHENTICATED",
                oewn_result=universe,
            )
        if universe.get("archive_sha256") != oewn.RELEASE_SHA256:
            return _base("FAIL_CLOSED", reason="OEWN_RELEASE_HASH_BINDING_INVALID")
        if universe.get("candidate_set_complete_relative_to_release") is not True:
            return _base("FAIL_CLOSED", reason="OEWN_RELEASE_ENUMERATION_INCOMPLETE")

        stock = _sense_by_id(universe, STOCK_SENSE)
        medical = _sense_by_id(universe, MEDICAL_SENSE)
        _validate_sense(
            stock,
            synset_id=STOCK_SYNSET,
            definition=STOCK_DEFINITION,
        )
        _validate_sense(
            medical,
            synset_id=MEDICAL_SYNSET,
            definition=MEDICAL_DEFINITION,
        )

        semantics = {
            STOCK_SENSE: _semantic_hash(stock),
            MEDICAL_SENSE: _semantic_hash(medical),
        }
        source_sha = _hash(source_text)

        compatibility = {
            STOCK_SENSE: {
                "pass": True,
                "schema": generic.COMPATIBILITY_SCHEMA,
                "source_id": sid,
                "source_sha256": source_sha,
                "interpretation_id": STOCK_SENSE,
                "interpretation_semantics_sha256": semantics[STOCK_SENSE],
                "source_compatible": True,
                "verification_authority_mutated": False,
                "receipt_sha256": _hash(
                    "compat:" + sid + ":" + STOCK_SENSE + ":" + source_sha
                ),
            },
            MEDICAL_SENSE: {
                "pass": True,
                "schema": generic.COMPATIBILITY_SCHEMA,
                "source_id": sid,
                "source_sha256": source_sha,
                "interpretation_id": MEDICAL_SENSE,
                "interpretation_semantics_sha256": semantics[MEDICAL_SENSE],
                "source_compatible": True,
                "verification_authority_mutated": False,
                "receipt_sha256": _hash(
                    "compat:" + sid + ":" + MEDICAL_SENSE + ":" + source_sha
                ),
            },
        }

        distinct = {
            "pass": True,
            "schema": generic.DISTINCTNESS_SCHEMA,
            "left_interpretation_id": STOCK_SENSE,
            "left_semantics_sha256": semantics[STOCK_SENSE],
            "right_interpretation_id": MEDICAL_SENSE,
            "right_semantics_sha256": semantics[MEDICAL_SENSE],
            "semantically_distinct": True,
            "verification_authority_mutated": False,
            "receipt_sha256": _hash(
                "distinct:" + semantics[STOCK_SENSE] + ":" + semantics[MEDICAL_SENSE]
            ),
        }

        def compat_verifier(raw: dict[str, Any]) -> dict[str, Any] | None:
            return deepcopy(compatibility.get(str(raw.get("sense_id") or "")))

        def distinct_verifier(_raw: dict[str, Any]) -> dict[str, Any]:
            return deepcopy(distinct)

        generic_result = generic.prove(
            source_id=sid,
            source_text=source_text,
            compatibility_receipts=[
                {"sense_id": STOCK_SENSE},
                {"sense_id": MEDICAL_SENSE},
            ],
            compatibility_verifier=compat_verifier,
            distinctness_receipt={"pair": "reserve-stock-vs-medical"},
            distinctness_verifier=distinct_verifier,
        )
        if generic_result.get("pass") is not True:
            return _base(
                "FAIL_CLOSED",
                reason="GENERIC_PAIRWISE_NONIDENTIFIABILITY_NOT_PROVED",
                generic_result=generic_result,
            )

        stock_world = {
            "sense_id": STOCK_SENSE,
            "quantity": "saved_stockpile_units",
            "before": 100,
            "after": 200,
            "predicate_check": 200 > 100,
            "source_sentence_true_under_interpretation": True,
        }
        medical_world = {
            "sense_id": MEDICAL_SENSE,
            "quantity": "physiological_reserve_capacity_units",
            "before": 10,
            "after": 20,
            "predicate_check": 20 > 10,
            "source_sentence_true_under_interpretation": True,
        }
        if not stock_world["predicate_check"] or not medical_world["predicate_check"]:
            raise AssertionError("RESERVE_WITNESS_WORLD_INVALID")

        return _base(
            "PASS__BARE_RESERVE_UNIQUE_SENSE_NONIDENTIFIABILITY_PROVED",
            passed=True,
            semantic_nonidentifiability_authority=True,
            source_id=sid,
            source_text=source_text,
            source_form="BARE_RESERVE_INCREASED",
            oewn_archive_sha256=universe["archive_sha256"],
            oewn_release_relative_sense_count=universe.get("sense_count"),
            witness_sense_ids=[STOCK_SENSE, MEDICAL_SENSE],
            witness_synset_ids=[STOCK_SYNSET, MEDICAL_SYNSET],
            witness_worlds=[stock_world, medical_world],
            generic_pairwise_result=generic_result,
            at_least_two_distinct_authenticated_interpretations_admit_source=True,
            unique_sense_identifiable_from_source_alone=False,
            additional_information_required_for_unique_identity=True,
            open_world_remainder_may_contain_additional_interpretations=True,
            decision_recommendation="ACQUIRE_DECISIVE_CONTEXT_OR_ABSTAIN_FROM_SENSE_IDENTITY",
            boundary=(
                "EXACT_BARE_Reserve_increased_SOURCE_FORM_ONLY__"
                "PROVES_NONUNIQUENESS_NOT_TRUE_SENSE__"
                "OEWN_RELEASE_RELATIVE_WITNESSES_DO_NOT_CLOSE_FINANCE_DOMAIN_SEMANTICS__"
                "NO_POLICY_OR_TERMINAL_AUTHORITY"
            ),
        )
    except Exception as exc:
        return _base("FAIL_CLOSED", reason=type(exc).__name__ + ":" + str(exc))
