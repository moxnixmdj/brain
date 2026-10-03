"""Fail-closed proof router for the current Tool Discovery critical path.

No acceptance is granted. The router consumes independently verified receipts
for policy soundness, exact common-authority identity scope, the information
lower bound, and the exact observability-partition result. The partition receipt
is cryptographically bound to the result it authorizes.
"""
from __future__ import annotations
import hashlib,json
from typing import Any, Mapping

SCHEMA="PROJECT_BRAIN_TOOL_DISCOVERY_PROOF_ROUTER_V1"

def _canon(v:Any)->bytes:
    return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()

def _sha(v:Any)->str:
    return "sha256:"+hashlib.sha256(_canon(v)).hexdigest()

def _fail(*failures:str)->dict[str,Any]:
    return {
      "schema":SCHEMA,"status":"FAIL_CLOSED","failures":sorted(set(failures)),
      "acceptance_proved":False,"capability_credit_delta":0,"family_credit_delta":0,
      "execution_authority":False,"promotion_authority":False,
    }

def route(
    *,
    policy_receipt:Mapping[str,Any],
    identity_scope_receipt:Mapping[str,Any],
    partition_result:Mapping[str,Any],
    partition_receipt:Mapping[str,Any],
    lower_bound_receipt:Mapping[str,Any],
)->dict[str,Any]:
    failures=[]
    if policy_receipt.get("independent_verified") is not True:
        failures.append("POLICY_NOT_INDEPENDENTLY_VERIFIED")
    version=str(policy_receipt.get("policy_version") or "")
    if not (version.startswith("V") and version[1:].isdigit() and int(version[1:])>=6):
        failures.append("POLICY_NOT_V6_OR_SUCCESSOR")
    if identity_scope_receipt.get("independent_verified") is not True:
        failures.append("IDENTITY_SCOPE_NOT_INDEPENDENTLY_VERIFIED")
    if identity_scope_receipt.get("identity_scope_complete") is not True:
        failures.append("IDENTITY_SCOPE_NOT_COMPLETE")
    if identity_scope_receipt.get("scope_relation")!="EXACT":
        failures.append("IDENTITY_SCOPE_RELATION_NOT_EXACT")
    if lower_bound_receipt.get("independent_verified") is not True:
        failures.append("LOWER_BOUND_NOT_INDEPENDENTLY_VERIFIED")
    if lower_bound_receipt.get("lower_bound_verified") is not True:
        failures.append("LOWER_BOUND_THEOREM_NOT_VERIFIED")
    if partition_receipt.get("independent_verified") is not True:
        failures.append("PARTITION_NOT_INDEPENDENTLY_VERIFIED")
    if str(partition_receipt.get("partition_result_sha256") or "")!=_sha(partition_result):
        failures.append("PARTITION_RECEIPT_RESULT_DIGEST_MISMATCH")
    if partition_result.get("identity_scope_complete") is not True:
        failures.append("PARTITION_IDENTITY_PRECONDITION_NOT_MET")
    if failures:
        return _fail(*failures)

    matched=partition_result.get("matched_comparator_required") is True
    universal=partition_result.get("universal_proof_eligible") is True
    if matched==universal:
        return _fail("PARTITION_NOT_EXACTLY_ONE_REGION")

    if matched:
        ambiguous=partition_result.get("ambiguous_decision_relevant_routes")
        if not isinstance(ambiguous,list) or not ambiguous:
            return _fail("MATCHED_REGION_WITHOUT_AMBIGUITY_WITNESS")
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
