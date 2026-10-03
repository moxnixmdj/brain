"""Fail-closed Tool Discovery scope-quantifier firewall.

The frozen-scope receipt proves a complete tool-identity universe *inside each
bound evaluator case*.  That proposition is not the same as proving that the
180 executed cases are the complete population of the family protocol.

This verifier prevents identity completeness (forall tools in one case) from
being relabeled as protocol-population completeness (forall admissible cases).
It consumes no terminal case and grants no credit.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[2]

SCOPE_RECEIPT = (
    "canonical/verification/"
    "TOOL_DISCOVERY_FROZEN_SCOPE_COMPLETENESS_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json"
)
TERMINAL_BINDING = "canonical/governance/TOOL_DISCOVERY_T2_T3_OBJECTIVE_TERMINAL_BINDING_V1.json"
PROTOCOLS = "canonical/governance/OPUS55_TERMINAL_PROOF_PROTOCOLS_V1.json"
ACCEPTANCE_INPUT = "canonical/governance/OPUS55_TOOL_DISCOVERY_SCOPE_COMPLETE_ACCEPTANCE_INPUT_V1.json"

FAMILY = "TOOL_DISCOVERY_SELECTION_AND_LEARNING"

IDENTITY_FACTS = {
    "V1_PUBLIC_EXPOSES_COMPLETE_CASE_TOOL_IDENTITY_LIST",
    "V1_ORACLE_RANGES_OVER_EXACT_SAME_CASE_TOOL_LIST",
    "V2_INHERITS_V1_GENERATED_IDENTITY_UNIVERSE",
    "V2_DOES_NOT_REPLACE_GENERATED_TOOL_IDENTITY_UNIVERSE",
}

# Any one of these must be independently established before a finite 180/180
# sample can be promoted as a whole-protocol absolute ceiling.
POPULATION_FACTS = {
    "ALL_ADMISSIBLE_PROTOCOL_CASES_PROVED",
    "EXHAUSTIVE_FINITE_PROTOCOL_POPULATION_PROVED",
    "UNIVERSAL_FORMAL_PROTOCOL_SCOPE_PROVED",
}


def _load(path: str) -> dict[str, Any]:
    value = json.loads((ROOT / path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(path + ":NOT_OBJECT")
    return value


def evaluate(
    *,
    scope_override: Mapping[str, Any] | None = None,
    binding_override: Mapping[str, Any] | None = None,
    acceptance_override: Mapping[str, Any] | None = None,
    protocols_override: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    scope = copy.deepcopy(dict(scope_override)) if scope_override is not None else _load(SCOPE_RECEIPT)
    binding = copy.deepcopy(dict(binding_override)) if binding_override is not None else _load(TERMINAL_BINDING)
    acceptance = copy.deepcopy(dict(acceptance_override)) if acceptance_override is not None else _load(ACCEPTANCE_INPUT)
    protocols = copy.deepcopy(dict(protocols_override)) if protocols_override is not None else _load(PROTOCOLS)

    verified = set(scope.get("verified") or [])
    identity_complete = IDENTITY_FACTS <= verified

    source_pool = binding.get("source_pool") or {}
    terminal_scope_claim = str(source_pool.get("terminal_scope_claim") or "")
    finite_sample_explicitly_nonexhaustive = "NOT_EXHAUSTIVE" in terminal_scope_claim
    sample_count = source_pool.get("terminal_sample_count")

    protocol = next(
        (
            row for row in protocols.get("protocols", [])
            if isinstance(row, Mapping) and row.get("family") == FAMILY
        ),
        None,
    )
    protocol_has_unknown_tool_dimension = (
        isinstance(protocol, Mapping)
        and "unknown tool discovery" in (protocol.get("task_dimensions") or [])
    )

    population_fact_present = bool(POPULATION_FACTS & verified)
    population_complete = population_fact_present and not finite_sample_explicitly_nonexhaustive

    injected_complete_target_case_set = False
    for e in acceptance.get("evidence", []):
        if not isinstance(e, Mapping) or e.get("family") != FAMILY:
            continue
        sc = e.get("scope_completeness")
        if isinstance(sc, Mapping) and sc.get("complete_target_case_set") is True:
            injected_complete_target_case_set = True
            break

    receipt_claims_complete_target_case_set = scope.get("complete_target_case_set") is True

    quantifier_mismatch = bool(
        identity_complete
        and finite_sample_explicitly_nonexhaustive
        and not population_fact_present
        and (receipt_claims_complete_target_case_set or injected_complete_target_case_set)
    )

    if quantifier_mismatch:
        status = "FAIL_CLOSED__IDENTITY_COMPLETENESS_IS_NOT_PROTOCOL_POPULATION_COMPLETENESS"
    elif not identity_complete:
        status = "FAIL_CLOSED__IDENTITY_SCOPE_NOT_PROVED"
    elif not population_complete:
        status = "FAIL_CLOSED__PROTOCOL_POPULATION_COMPLETENESS_OPEN"
    else:
        status = "PASS__PROTOCOL_POPULATION_SCOPE_PROVED"

    promotable = status.startswith("PASS__")
    return {
        "schema": "PROJECT_BRAIN_TOOL_DISCOVERY_SCOPE_QUANTIFIER_FIREWALL_V1",
        "status": status,
        "family": FAMILY,
        "identity_universe_complete_within_bound_case": identity_complete,
        "protocol_population_complete": population_complete,
        "terminal_sample_count": sample_count,
        "terminal_sample_explicitly_nonexhaustive": finite_sample_explicitly_nonexhaustive,
        "protocol_has_unknown_tool_discovery_dimension": protocol_has_unknown_tool_dimension,
        "receipt_claims_complete_target_case_set": receipt_claims_complete_target_case_set,
        "acceptance_input_injects_complete_target_case_set": injected_complete_target_case_set,
        "verified_population_fact_present": population_fact_present,
        "quantifier_mismatch": quantifier_mismatch,
        "tool_discovery_acceptance_promotion_allowed": promotable,
        "current_acceptance_must_remain": "3_OF_19__8_OF_38" if not promotable else "RECOMPUTE_AFTER_INDEPENDENT_REDUCTION",
        "minimum_missing_fact": (
            "INDEPENDENT_EXHAUSTIVE_OR_UNIVERSAL_PROTOCOL_POPULATION_SCOPE_PROOF__"
            "IDENTITY_COMPLETENESS_INSIDE_EACH_CASE_IS_ALREADY_PROVED"
            if not promotable
            else None
        ),
        "hard_nonclaims": [
            "DOES_NOT_REVOKE_THE_IMMUTABLE_180_OF_180_SAMPLE_RESULT",
            "DOES_NOT_REVOKE_PER_CASE_TOOL_IDENTITY_COMPLETENESS",
            "DOES_NOT_ASSERT_TOOL_DISCOVERY_ACCEPTANCE_CAN_NEVER_CLOSE",
            "DOES_NOT_CONSUME_NEW_TERMINAL_REALITY",
        ],
        "new_reality_units_consumed": 0,
        "terminal_results_replayed": 0,
        "incremental_spend_usd": 0,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
    }


if __name__ == "__main__":
    print(json.dumps(evaluate(), indent=2, sort_keys=True))
