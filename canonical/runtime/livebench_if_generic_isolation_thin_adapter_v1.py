from __future__ import annotations
from typing import Any, Mapping
from canonical.runtime.generic_precommit_isolation_theorem_v1 import verify_benchmark_thin_adapter

SCHEMA="PROJECT_BRAIN_LIVEBENCH_IF_GENERIC_ISOLATION_THIN_ADAPTER_V1"
REQUIRED=(
    "population_identity_verified",
    "scorer_or_grader_equivalence_verified",
    "effort_and_context_semantics_verified",
    "tool_and_environment_boundary_verified",
    "exact_comparator_identity_verified",
    "no_proxy_substitution_verified",
    "zero_incremental_spend_or_entitlement_verified",
    "acceptance_rule_bound",
)
BASE_FIELDS={
    "population_identity_verified":True,
    "scorer_or_grader_equivalence_verified":True,
    "effort_and_context_semantics_verified":True,
    "tool_and_environment_boundary_verified":True,
    "exact_comparator_identity_verified":True,
    "no_proxy_substitution_verified":True,
    "zero_incremental_spend_or_entitlement_verified":False,
    "acceptance_rule_bound":True,
}

def evaluate(fields: Mapping[str,Any] | None=None)->dict[str,Any]:
    current=dict(BASE_FIELDS if fields is None else fields)
    verdict=verify_benchmark_thin_adapter(current)
    proved=[k for k in REQUIRED if current.get(k) is True]
    unproved=[k for k in REQUIRED if current.get(k) is not True]
    return {
        "schema":SCHEMA,
        "proved_field_count":len(proved),
        "required_field_count":len(REQUIRED),
        "proved_fields":proved,
        "unproved_fields":unproved,
        "thin_adapter_pass":bool(verdict["benchmark_thin_adapter_pass"]),
        "generic_checker_missing":list(verdict["missing"]),
        "exact_remaining_adapter_residual":[
            "ZERO_INCREMENTAL_SPEND_OR_ALREADY_ENTITLED_CARRIER_RECEIPT_FOR_THE_EXACT_PRECOMMITTED_BRAIN_EXECUTION"
        ] if unproved==["zero_incremental_spend_or_entitlement_verified"] else unproved,
        "execution_authority":False,
        "promotion_authority":False,
        "fresh_reality_authority":False,
        "acceptance_credit_authorized":False,
    }

def with_zero_spend_receipt_proved()->dict[str,Any]:
    fields=dict(BASE_FIELDS)
    fields["zero_incremental_spend_or_entitlement_verified"]=True
    return evaluate(fields)
