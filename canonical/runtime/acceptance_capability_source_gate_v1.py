"""Fail-closed capability-source gate for Opus 5.5 acceptance benchmark execution.

A public/free benchmark harness is not enough. The candidate being measured must
also be a Brain-owned, donor-independent capability route. This gate prevents
spending clean benchmark cases on adapters whose operative cognition is external.
"""
from __future__ import annotations
from typing import Any, Mapping

SCHEMA="PROJECT_BRAIN_ACCEPTANCE_CAPABILITY_SOURCE_GATE_V1"

def evaluate(route:Mapping[str,Any])->dict[str,Any]:
    errors:list[str]=[]
    if route.get("benchmark_harness_zero_cost") is not True:
        errors.append("HARNESS_ZERO_COST_NOT_PROVEN")
    if route.get("scorer_frozen") is not True:
        errors.append("SCORER_NOT_FROZEN")
    if route.get("brain_candidate_bound") is not True:
        errors.append("BRAIN_CANDIDATE_NOT_BOUND")
    if route.get("candidate_donor_independent") is not True:
        errors.append("CANDIDATE_DONOR_INDEPENDENCE_NOT_PROVEN")
    if route.get("opaque_external_capability_provider") is not False:
        errors.append("OPAQUE_EXTERNAL_CAPABILITY_PROVIDER_NOT_ZERO")
    md=route.get("model_dependency_count")
    if md != 0:
        errors.append("MODEL_DEPENDENCY_COUNT_NOT_ZERO")
    if route.get("incremental_spend_usd") != 0:
        errors.append("INCREMENTAL_SPEND_NOT_ZERO")
    ok=not errors
    return {
      "schema":SCHEMA,
      "status":"ADMISSIBLE_FOR_CLEAN_ACCEPTANCE_EXECUTION" if ok else "BLOCKED_BEFORE_CASE_SPEND",
      "pass":ok,
      "errors":errors,
      "clean_case_execution_authority":ok,
      "capability_credit_delta":0,
      "family_credit_delta":0,
      "rule":"FREE_PUBLIC_HARNESS_DOES_NOT_IMPLY_OWNERSHIP_ADMISSIBILITY__OPERATIVE_CANDIDATE_COGNITION_MUST_BE_BRAIN_OWNED_DONOR_INDEPENDENT_AND_MODEL_DEPENDENCY_ZERO"
    }
