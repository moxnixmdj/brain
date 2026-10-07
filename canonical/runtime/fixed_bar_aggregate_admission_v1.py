from __future__ import annotations

import math
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_FIXED_BAR_AGGREGATE_ADMISSION_V1"
RECEIPT_SCHEMA = "PROJECT_BRAIN_FIXED_BAR_AGGREGATE_RECEIPT_V1"

FROZEN_BARS = {
    "CODING_TB4_GE_66_4": {"metric": "TERMINAL_BENCH_4_0_PERCENT", "bar": 66.4, "unit": "percent"},
    "CODING_FRONTIERCODE_GE_54_4": {"metric": "FRONTIERCODE_V1_1_MAIN_PERCENT", "bar": 54.4, "unit": "percent"},
    "CODING_CURSORBENCH_GE_57_8": {"metric": "CURSORBENCH_4_0_PERCENT", "bar": 57.8, "unit": "percent"},
    "PROWORK_GDPVAL_GE_1846": {"metric": "GDPVAL_AA_V2_1_ELO", "bar": 1846.0, "unit": "Elo"},
    "PROWORK_AA_BRIEFCASE_GE_1822": {"metric": "AA_BRIEFCASE_V1_1_ELO", "bar": 1822.0, "unit": "Elo"},
    "AUTOMATIONBENCH_GE_40": {"metric": "AUTOMATIONBENCH_PERCENT", "bar": 40.0, "unit": "percent"},
    "HLE_TOOLS_GE_67_7": {"metric": "HLE_WITH_TOOLS_PERCENT", "bar": 67.7, "unit": "percent"},
    "TB_SCIENCE_GE_58_7": {"metric": "TERMINAL_BENCH_SCIENCE_0_1_PERCENT", "bar": 58.7, "unit": "percent"},
    "CHARTOGRAPHY_TOOLS_GE_89": {"metric": "CHARTOGRAPHY_WITH_TOOLS_PERCENT", "bar": 89.0, "unit": "percent"},
    "OSWORLD_2_1_PARTIAL_GE_81_8": {"metric": "OSWORLD_2_1_PARTIAL_PERCENT", "bar": 81.8, "unit": "percent"},
    "FINANCE_ACCOUNTING_INDEX_GE_61": {"metric": "FINANCE_ACCOUNTING_INDEX", "bar": 61.0, "unit": "index"},
    "FINANCE_AGENT_V2_GE_58_59": {"metric": "FINANCE_AGENT_V2_PERCENT", "bar": 58.59, "unit": "percent"},
    "ARTIFACT_AA_BRIEFCASE_GE_1822": {"metric": "AA_BRIEFCASE_V1_1_ELO", "bar": 1822.0, "unit": "Elo"},
    "MYSTERYMECHANISM_GE_49_55": {"metric": "MYSTERYMECHANISM_PERCENT", "bar": 49.55, "unit": "percent"},
}

_REQUIRED_GATES = (
    "frozen_scope_bound",
    "scope_complete",
    "comparable_harness",
    "brain_owned_route",
    "contamination_safe",
    "predeclared_statistics",
    "independent_or_objective",
    "content_addressed_result",
)


def _finite_number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        x = float(value)
    except (TypeError, ValueError):
        return None
    return x if math.isfinite(x) else None


def evaluate_atom(receipt: Any, atom_id: str) -> dict[str, Any]:
    errors: list[str] = []
    spec = FROZEN_BARS.get(atom_id)
    if spec is None:
        return {
            "schema": SCHEMA,
            "pass": False,
            "state": "FAIL_CLOSED",
            "atom_id": atom_id,
            "errors": ["UNKNOWN_FIXED_BAR_ATOM"],
        }

    if not isinstance(receipt, Mapping):
        return {
            "schema": SCHEMA,
            "pass": False,
            "state": "FAIL_CLOSED",
            "atom_id": atom_id,
            "errors": ["RECEIPT_NOT_OBJECT"],
            "authorized_bar": spec["bar"],
        }

    if receipt.get("schema") != RECEIPT_SCHEMA:
        errors.append("RECEIPT_SCHEMA_INVALID")
    if receipt.get("metric") != spec["metric"]:
        errors.append("METRIC_MISMATCH")
    if receipt.get("unit") != spec["unit"]:
        errors.append("UNIT_MISMATCH")

    point = _finite_number(receipt.get("brain_point_value"))
    conservative = _finite_number(receipt.get("brain_conservative_value"))
    if point is None:
        errors.append("POINT_VALUE_INVALID")
    if conservative is None:
        errors.append("CONSERVATIVE_VALUE_INVALID")
    elif point is not None and conservative > point:
        errors.append("CONSERVATIVE_VALUE_EXCEEDS_POINT_VALUE")

    gates = receipt.get("gates")
    if not isinstance(gates, Mapping):
        errors.append("GATES_NOT_OBJECT")
        gates = {}
    for gate in _REQUIRED_GATES:
        if gates.get(gate) is not True:
            errors.append(f"GATE_NOT_PROVED:{gate}")

    bindings = receipt.get("scope_bindings")
    if not isinstance(bindings, Mapping):
        errors.append("SCOPE_BINDINGS_NOT_OBJECT")
        bindings = {}
    binding = bindings.get(atom_id)
    if not isinstance(binding, Mapping):
        errors.append("ATOM_SCOPE_BINDING_MISSING")
    else:
        if binding.get("verified") is not True:
            errors.append("ATOM_SCOPE_BINDING_NOT_VERIFIED")
        if binding.get("independent_or_objective") is not True:
            errors.append("ATOM_SCOPE_BINDING_NOT_INDEPENDENT_OR_OBJECTIVE")
        if binding.get("scope_relation") not in {"EXACT", "PROVEN_STRONGER"}:
            errors.append("ATOM_SCOPE_RELATION_INSUFFICIENT")
        if not isinstance(binding.get("source_path"), str) or not binding.get("source_path", "").strip():
            errors.append("ATOM_SCOPE_BINDING_SOURCE_MISSING")
        if not isinstance(binding.get("source_sha"), str) or len(binding.get("source_sha", "")) < 7:
            errors.append("ATOM_SCOPE_BINDING_SHA_MISSING")

    if not isinstance(receipt.get("result_source_path"), str) or not receipt.get("result_source_path", "").strip():
        errors.append("RESULT_SOURCE_PATH_MISSING")
    if not isinstance(receipt.get("result_source_sha"), str) or len(receipt.get("result_source_sha", "")) < 7:
        errors.append("RESULT_SOURCE_SHA_MISSING")

    bar_met = conservative is not None and conservative >= float(spec["bar"])
    if not bar_met:
        errors.append("CONSERVATIVE_BAR_NOT_MET")

    passed = not errors
    return {
        "schema": SCHEMA,
        "pass": passed,
        "state": "PROVED" if passed else "FAIL_CLOSED",
        "atom_id": atom_id,
        "metric": spec["metric"],
        "unit": spec["unit"],
        "authorized_bar": spec["bar"],
        "brain_point_value": point,
        "brain_conservative_value": conservative,
        "errors": sorted(set(errors)),
        "case_level_target_relation_required": False,
        "terminal_credit_delta": 0,
        "rule": (
            "ONLY_A_VALID_SCOPE_COMPLETE_CONTAMINATION_SAFE_BRAIN_AGGREGATE_RESULT_"
            "AT_OR_ABOVE_THE_FROZEN_BAR_CAN_PROVE_THIS_ATOM"
        ),
    }


def evaluate_receipt(receipt: Any) -> dict[str, Any]:
    if not isinstance(receipt, Mapping):
        return {
            "schema": SCHEMA,
            "pass": False,
            "state": "FAIL_CLOSED",
            "errors": ["RECEIPT_NOT_OBJECT"],
        }
    bindings = receipt.get("scope_bindings")
    atom_ids = sorted(bindings) if isinstance(bindings, Mapping) else []
    results = [evaluate_atom(receipt, atom_id) for atom_id in atom_ids]
    passed = bool(results) and all(x["pass"] for x in results)
    return {
        "schema": SCHEMA,
        "pass": passed,
        "state": "PROVED" if passed else "FAIL_CLOSED",
        "measurement_id": receipt.get("measurement_id"),
        "atom_results": results,
        "proved_atoms": [x["atom_id"] for x in results if x["pass"]],
        "terminal_credit_delta": 0,
    }
