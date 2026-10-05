"""Fail-closed reducer for extensional fixed-interface target coverage.

This module proves only a target-coverage relation U ⊆ A, where A is the
complete frozen profile-union interface trace language. It intentionally does
not require role taxonomy totality or 19-family semantic totality, because
those are optional factorization devices for the later dominance proof.

No acceptance, family, capability, ownership, execution, promotion, or fresh
reality authority is granted by this reducer.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

SCHEMA = "PROJECT_BRAIN_FIXED_INTERFACE_TRACE_COVERAGE_VERDICT_V1"

REQUIRED_TRACE_OPS = {
    "SEQUENCE",
    "BRANCH",
    "LOOP",
    "PARALLEL_TOOL_CALL_GROUP",
    "PAUSE_AND_CONTINUE",
    "STATE_CARRY_FORWARD",
}


def _nonempty_strings(value: Any) -> bool:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        return False
    items = list(value)
    return bool(items) and all(isinstance(x, str) and x.strip() for x in items)


def evaluate(cert: Mapping[str, Any]) -> dict[str, Any]:
    failures: list[str] = []

    if not isinstance(cert, Mapping):
        failures.append("CERT_NOT_OBJECT")
        cert = {}

    if cert.get("target_rule") != "USEFUL_BEHAVIOR_NOT_INTERNAL_IMPLEMENTATION":
        failures.append("TARGET_RULE_NOT_OBSERVABLE_BEHAVIOR")

    if cert.get("included_behavior_interface_mediated") is not True:
        failures.append("TARGET_BOUNDARY_NOT_INTERFACE_MEDIATED")

    if cert.get("profile_union_interface_complete") is not True:
        failures.append("PROFILE_UNION_INTERFACE_NOT_COMPLETE")

    if cert.get("interface_completeness_independently_verified") is not True:
        failures.append("INTERFACE_COMPLETENESS_NOT_INDEPENDENTLY_VERIFIED")

    alphabet = cert.get("interface_alphabet")
    if not isinstance(alphabet, Mapping):
        failures.append("INTERFACE_ALPHABET_MISSING")
    else:
        if not _nonempty_strings(alphabet.get("external_inputs")):
            failures.append("EXTERNAL_INPUT_ALPHABET_INVALID")
        if not _nonempty_strings(alphabet.get("model_emissions")):
            failures.append("MODEL_EMISSION_ALPHABET_INVALID")

    ops_raw = cert.get("trace_operations")
    if not _nonempty_strings(ops_raw):
        failures.append("TRACE_OPERATIONS_INVALID")
        ops = set()
    else:
        ops = set(ops_raw)
        missing = sorted(REQUIRED_TRACE_OPS - ops)
        if missing:
            failures.append("TRACE_OPERATIONS_INCOMPLETE:" + ",".join(missing))

    if cert.get("all_finite_well_formed_traces_in_domain") is not True:
        failures.append("TRACE_LANGUAGE_NOT_CLOSED")

    proved = not failures

    return {
        "schema": SCHEMA,
        "status": "PASS__U_SUBSET_A_TRACE_COVERAGE" if proved else "FAIL_CLOSED__TRACE_COVERAGE_NOT_PROVED",
        "target_coverage_proved": proved,
        "coverage_domain": "COMPLETE_FROZEN_PROFILE_UNION_INTERFACE_TRACE_LANGUAGE" if proved else None,
        "role_classification_totality_required_for_coverage": False,
        "family_semantic_totality_required_for_coverage": False,
        "domain_dominance_proved": False,
        "terminal_finality": False,
        "failures": sorted(set(failures)),
        "rule": (
            "IF EVERY INCLUDED USEFUL TARGET BEHAVIOR IS INTERFACE-MEDIATED, "
            "THE PROFILE-UNION MODEL-SIDE INTERFACE IS COMPLETE, AND A CONTAINS "
            "ALL FINITE WELL-FORMED TRACES OVER THAT INTERFACE, THEN U IS A SUBSET "
            "OF A WITHOUT REQUIRING ROLE OR FAMILY FACTORIZATION."
        ),
        "acceptance_credit_delta": 0,
        "family_credit_delta": 0,
        "capability_credit_delta": 0,
        "ownership_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
        "fresh_reality_authority": False,
    }
