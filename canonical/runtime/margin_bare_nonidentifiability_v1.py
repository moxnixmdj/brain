"""Bounded semantic non-identifiability certificate for 'Margin increased.'.

For the exact bare source form, this module recomputes the pinned OEWN noun
sense inventory and constructs two distinct admissible interpretations:
- collateral margin;
- gross-profit margin.

Each interpretation admits a concrete numeric world in which the source sentence
is true. Therefore the source text alone cannot uniquely identify the intended
sense. This negative result does NOT require a complete open-world finance
hypothesis set.

No intended sense, downstream action, ontology completeness, or terminal
authority is claimed.
"""
from __future__ import annotations

from copy import deepcopy
import re
from typing import Any

from canonical.runtime import oewn_release_sense_universe_v1 as oewn

SCHEMA = "PROJECT_BRAIN_MARGIN_BARE_NONIDENTIFIABILITY_V1"
COLLATERAL_SENSE = "margin%1:21:01::"
COLLATERAL_SYNSET = "13372293-n"
PROFIT_SENSE = "margin%1:21:02::"
PROFIT_SYNSET = "13281661-n"
COLLATERAL_DEFINITION = (
    "the amount of collateral a customer deposits with a broker when borrowing "
    "from the broker to buy securities"
)
PROFIT_DEFINITION = (
    "(finance) the net sales minus the cost of goods and services sold"
)
_PATTERN = re.compile(r"^\s*margin\s+increased\.?\s*$", re.I)


def _norm(value: Any) -> str:
    return " ".join(str(value or "").strip().casefold().split())


def _base(status: str, *, passed: bool = False, **extra: Any) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": status,
        "pass": passed,
        "semantic_nonidentifiability_authority": False,
        "semantic_truth_authority": False,
        "unique_sense_identified": False,
        "open_world_finance_semantics_complete": False,
        "hypothesis_space_completeness_required_for_this_negative_result": False,
        "execution_authority": False,
        "acceptance_authority": False,
        "promotion_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        **extra,
    }


def _sense_by_id(universe: dict[str, Any], sense_id: str) -> dict[str, Any]:
    rows = [
        deepcopy(dict(x))
        for x in universe.get("senses", [])
        if isinstance(x, dict) and x.get("sense_id") == sense_id
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
    if "margin" not in members:
        raise ValueError("OEWN_MARGIN_MEMBER_MISSING:" + str(row.get("sense_id")))
    definitions = {_norm(x) for x in row.get("definitions", [])}
    if _norm(definition) not in definitions:
        raise ValueError("OEWN_DEFINITION_BINDING_MISMATCH:" + str(row.get("sense_id")))


def prove(
    source_text: str,
    *,
    oewn_archive: bytes | bytearray | str,
) -> dict[str, Any]:
    try:
        if not isinstance(source_text, str) or not source_text:
            return _base("FAIL_CLOSED", reason="SOURCE_TEXT_REQUIRED")
        if _PATTERN.fullmatch(source_text) is None:
            return _base(
                "NOT_APPLICABLE__SOURCE_OUTSIDE_BARE_MARGIN_SCOPE",
                source_text=source_text,
            )

        universe = oewn.enumerate_senses(
            oewn_archive,
            "margin",
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

        collateral = _sense_by_id(universe, COLLATERAL_SENSE)
        profit = _sense_by_id(universe, PROFIT_SENSE)
        _validate_sense(
            collateral,
            synset_id=COLLATERAL_SYNSET,
            definition=COLLATERAL_DEFINITION,
        )
        _validate_sense(
            profit,
            synset_id=PROFIT_SYNSET,
            definition=PROFIT_DEFINITION,
        )

        collateral_world = {
            "sense_id": COLLATERAL_SENSE,
            "semantic_quantity": "collateral_amount_deposited_with_broker",
            "before": 100,
            "after": 200,
            "predicate_check": 200 > 100,
            "source_sentence_true_under_interpretation": True,
        }
        profit_world = {
            "sense_id": PROFIT_SENSE,
            "semantic_quantity": "net_sales_minus_cost_of_goods_and_services_sold",
            "before": {
                "net_sales": 1000,
                "cost": 900,
                "gross_profit": 100,
            },
            "after": {
                "net_sales": 1100,
                "cost": 900,
                "gross_profit": 200,
            },
            "predicate_check": (1100 - 900) > (1000 - 900),
            "source_sentence_true_under_interpretation": True,
        }
        if collateral_world["predicate_check"] is not True:
            raise AssertionError("COLLATERAL_WITNESS_INVALID")
        if profit_world["predicate_check"] is not True:
            raise AssertionError("PROFIT_WITNESS_INVALID")
        if COLLATERAL_SENSE == PROFIT_SENSE or COLLATERAL_SYNSET == PROFIT_SYNSET:
            raise AssertionError("WITNESS_SENSES_NOT_DISTINCT")

        return _base(
            "PASS__BARE_MARGIN_UNIQUE_SENSE_NONIDENTIFIABILITY_PROVED",
            passed=True,
            semantic_nonidentifiability_authority=True,
            source_text=source_text,
            source_form="BARE_MARGIN_INCREASED",
            oewn_archive_sha256=universe["archive_sha256"],
            witness_sense_ids=[COLLATERAL_SENSE, PROFIT_SENSE],
            witness_synset_ids=[COLLATERAL_SYNSET, PROFIT_SYNSET],
            witness_worlds=[collateral_world, profit_world],
            at_least_two_distinct_authenticated_interpretations_admit_source=True,
            unique_sense_identifiable_from_source_alone=False,
            additional_information_required_for_unique_identity=True,
            open_world_remainder_may_contain_additional_interpretations=True,
            decision_recommendation="ACQUIRE_DECISIVE_CONTEXT_OR_ABSTAIN_FROM_SENSE_IDENTITY",
            proof_rule=(
                "TWO_DISTINCT_AUTHENTICATED_INTERPRETATIONS_THAT_BOTH_ADMIT_THE_"
                "EXACT_SOURCE_ARE_SUFFICIENT_TO_REFUTE_UNIQUE_IDENTIFIABILITY__"
                "EXHAUSTIVE_HYPOTHESIS_ENUMERATION_IS_NOT_REQUIRED_FOR_THIS_NEGATIVE_RESULT"
            ),
            boundary=(
                "EXACT_BARE_MARGIN_INCREASED_SOURCE_FORM_ONLY__PROVES_NONUNIQUENESS_"
                "NOT_THE_TRUE_SENSE__NO_GENERAL_WSD_OR_OPEN_WORLD_FINANCE_COMPLETENESS"
            ),
        )
    except Exception as exc:
        return _base("FAIL_CLOSED", reason=type(exc).__name__ + ":" + str(exc))
