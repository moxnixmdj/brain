"""Fail-closed three-way proof router for the current Tool Discovery path.

The router grants no acceptance. It consumes independently verified receipts for:
* V8-or-successor policy soundness,
* exact common Brain/Opus authority identity scope,
* the information-theoretic lower-bound theorem, and
* the exact observability-partition V2 result.

Routing order is load-bearing:
UNIVERSAL_PROOF -> SAFE_PROBE -> MATCHED_COMPARATOR.
Matched evidence is forbidden while a safe decision-relevant observation remains.
"""
from __future__ import annotations
import hashlib
import json
from typing import Any, Mapping

SCHEMA="PROJECT_BRAIN_TOOL_DISCOVERY_PROOF_ROUTER_V2"

def _canon(v:Any)->bytes:
    return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()

def _sha(v:Any)->str:
    return "sha256:"+hashlib.sha256(_canon(v)).hexdigest()

def _fail(*failures:str)->dict[str,Any]:
    return {
      "schema":SCHEMA,
      "status":"FAIL_CLOSED",
      "failures":sorted(set(failures)),
      "acceptance_proved":False,
      "new_reality_units_consumed":0,
      "terminal_results_replayed":0,
      "incremental_spend_usd":0,
      "capability_credit_delta":0,
      "family_credit_delta":0,
      "execution_authority":False,
      "promotion_authority":False,
    }

def _policy_version(receipt:Mapping[str,Any])->int|None:
    version=str(receipt.get("policy_version") or "")
    if not (version.startswith("V") and version[1:].isdigit()):
        return None
    return int(version[1:])

def route(
    *,
    policy_receipt:Mapping[str,Any],
    identity_scope_receipt:Mapping[str,Any],
    partition_result:Mapping[str,Any],
    partition_receipt:Mapping[str,Any],
    lower_bound_receipt:Mapping[str,Any],
)->dict[str,Any]:
    failures:list[str]=[]

    if policy_receipt.get("independent_verified") is not True:
        failures.append("POLICY_NOT_INDEPENDENTLY_VERIFIED")
    version=_policy_version(policy_receipt)
    if version is None or version < 8:
        failures.append("POLICY_NOT_V8_OR_SUCCESSOR")

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

    action=str(partition_result.get("minimum_reality_action") or "")
    universal=partition_result.get("universal_proof_eligible") is True
    safe=partition_result.get("safe_progress_available") is True
    matched=partition_result.get("matched_comparator_required_now") is True

    expected={
      "UNIVERSAL_PROOF":(True,False,False),
      "SAFE_PROBE":(False,True,False),
      "MATCHED_COMPARATOR":(False,False,True),
    }
    if action not in expected:
        return _fail("PARTITION_ACTION_INVALID")
    if (universal,safe,matched)!=expected[action]:
        return _fail("PARTITION_FLAGS_INCONSISTENT_WITH_ACTION")

    common={
      "schema":SCHEMA,
      "policy_version":"V"+str(version),
      "minimum_reality_action":action,
      "acceptance_proved":False,
      "terminal_results_replayed":0,
      "new_reality_units_consumed":0,
      "incremental_spend_usd":0,
      "capability_credit_delta":0,
      "family_credit_delta":0,
      "execution_authority":False,
      "promotion_authority":False,
    }

    if action=="UNIVERSAL_PROOF":
        return {
          **common,
          "status":"UNIVERSAL_REGION__NO_SAFE_OR_MATCHED_REALITY_NEEDED_FOR_THIS_PARTITION",
          "next_required_fact":"FORMAL_V8_OR_SUCCESSOR_CORRECTNESS_OVER_THIS_OBSERVABILITY_COMPLETE_COMMON_AUTHORITY_PARTITION",
          "safe_probe_needed_for_this_partition":False,
          "matched_comparator_needed_for_this_partition":False,
        }

    if action=="SAFE_PROBE":
        probe=partition_result.get("recommended_safe_probe")
        if not isinstance(probe,Mapping):
            return _fail("SAFE_REGION_WITHOUT_PROBE")
        tool_id=str(probe.get("tool_id") or "")
        capability=str(probe.get("capability") or "")
        if not tool_id or not capability:
            return _fail("SAFE_PROBE_TARGET_INCOMPLETE")
        return {
          **common,
          "status":"SAFE_PROBE_REQUIRED__MATCHED_EVIDENCE_FORBIDDEN_BEFORE_SAFE_OBSERVATION_CLOSURE",
          "next_required_fact":"CURRENT_EPOCH_SAFE_PROBE_RECEIPT",
          "recommended_safe_probe":{"tool_id":tool_id,"capability":capability},
          "matched_comparator_needed_now":False,
        }

    irreducible=partition_result.get("irreducible_routes")
    if not isinstance(irreducible,list) or not irreducible:
        return _fail("MATCHED_REGION_WITHOUT_IRREDUCIBLE_WITNESS")
    return {
      **common,
      "status":"MATCHED_ONLY_RESIDUAL__SAFE_OBSERVATION_EXHAUSTED",
      "next_required_fact":"MATCHED_OPUS_EVIDENCE_ONLY_FOR_INFORMATION_THEORETICALLY_AMBIGUOUS_DECISION_RELEVANT_EQUIVALENCE_CLASSES",
      "irreducible_route_count":len(irreducible),
      "universal_program_proof_needed_for_this_partition":False,
      "safe_probe_needed_now":False,
      "matched_comparator_needed_now":True,
    }
