"""Proof router for the current Tool Discovery critical path.

This module grants no acceptance. It converts three independently verified
facts into a minimal proof route:
1. V6-or-successor program soundness is verified.
2. Exact common Brain/Opus authority identity scope is verified.
3. The observability partition is verified.

Universal-region cases stay on the formal proof path. Only genuinely
information-theoretically ambiguous cases are routed to matched evidence.
"""
from __future__ import annotations
from typing import Any, Mapping

SCHEMA="PROJECT_BRAIN_TOOL_DISCOVERY_PROOF_ROUTER_V1"

def route(
    *,
    policy_receipt:Mapping[str,Any],
    identity_scope_receipt:Mapping[str,Any],
    partition_result:Mapping[str,Any],
    lower_bound_receipt:Mapping[str,Any],
)->dict[str,Any]:
    failures=[]
    if policy_receipt.get("independent_verified") is not True:
        failures.append("POLICY_NOT_INDEPENDENTLY_VERIFIED")
    if str(policy_receipt.get("policy_version") or "") not in {"V6","V7","V8","V9"}:
        failures.append("POLICY_NOT_V6_OR_SUCCESSOR")
    if identity_scope_receipt.get("independent_verified") is not True:
        failures.append("IDENTITY_SCOPE_NOT_INDEPENDENTLY_VERIFIED")
    if identity_scope_receipt.get("identity_scope_complete") is not True:
        failures.append("IDENTITY_SCOPE_NOT_COMPLETE")
    if lower_bound_receipt.get("independent_verified") is not True:
        failures.append("LOWER_BOUND_NOT_INDEPENDENTLY_VERIFIED")
    if partition_result.get("identity_scope_complete") is not True:
        failures.append("PARTITION_IDENTITY_PRECONDITION_NOT_MET")
    if failures:
        return {
          "schema":SCHEMA,"status":"FAIL_CLOSED","failures":sorted(set(failures)),
          "acceptance_proved":False,"capability_credit_delta":0,"family_credit_delta":0,
          "execution_authority":False,"promotion_authority":False,
        }

    matched=partition_result.get("matched_comparator_required") is True
    universal=partition_result.get("universal_proof_eligible") is True
    if matched==universal:
        return {
          "schema":SCHEMA,"status":"FAIL_CLOSED","failures":["PARTITION_NOT_EXACTLY_ONE_REGION"],
          "acceptance_proved":False,"capability_credit_delta":0,"family_credit_delta":0,
          "execution_authority":False,"promotion_authority":False,
        }
    if matched:
        ambiguous=partition_result.get("ambiguous_decision_relevant_routes")
        if not isinstance(ambiguous,list) or not ambiguous:
            return {
              "schema":SCHEMA,"status":"FAIL_CLOSED","failures":["MATCHED_REGION_WITHOUT_AMBIGUITY_WITNESS"],
              "acceptance_proved":False,"capability_credit_delta":0,"family_credit_delta":0,
              "execution_authority":False,"promotion_authority":False,
            }
        return {
          "schema":SCHEMA,
          "status":"MATCHED_ONLY_RESIDUAL__UNIVERSAL_SEARCH_FORBIDDEN_ON_AMBIGUOUS_FACTS",
          "next_required_fact":"MATCHED_OPUS_EVIDENCE_ONLY_FOR_INFORMATION_THEORETICALLY_AMBIGUOUS_DECISION_RELEVANT_EQUIVALENCE_CLASSES",
          "ambiguous_route_count":len(ambiguous),
          "universal_program_proof_needed_for_this_partition":False,
          "acceptance_proved":False,
          "terminal_results_replayed":0,"new_reality_units_consumed":0,
          "capability_credit_delta":0,"family_credit_delta":0,
          "execution_authority":False,"promotion_authority":False,
        }
    return {
      "schema":SCHEMA,
      "status":"UNIVERSAL_REGION__NO_MATCHED_REALITY_NEEDED_FOR_THIS_PARTITION",
      "next_required_fact":"FORMAL_V6_OR_SUCCESSOR_CORRECTNESS_OVER_THIS_OBSERVABILITY_COMPLETE_COMMON_AUTHORITY_PARTITION",
      "matched_comparator_needed_for_this_partition":False,
      "acceptance_proved":False,
      "terminal_results_replayed":0,"new_reality_units_consumed":0,
      "capability_credit_delta":0,"family_credit_delta":0,
      "execution_authority":False,"promotion_authority":False,
    }
