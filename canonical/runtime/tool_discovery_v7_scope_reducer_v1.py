"""Tool Discovery V7 scope reducer.

Maps an exact V6 public state to the observability lower-bound partition after
discovery saturation. It does not grant acceptance. It proves exactly which
part of the matched Tool Discovery problem is program-side decidable and which
part still needs matched evidence.
"""
from __future__ import annotations
from typing import Any, Mapping

from canonical.runtime import tool_discovery_dynamic_candidate_v5 as v5
from canonical.runtime import tool_discovery_observability_partition_v1 as obs

def classify_public(public: Mapping[str,Any])->dict[str,Any]:
    if public.get("version_events"):
        return {
            "status":"RESTART_REQUIRED_BEFORE_SCOPE_CLASSIFICATION",
            "universal_proof_eligible":False,
            "matched_comparator_required":False,
            "restart_required":True,
            "capability_credit_delta":0,
            "family_credit_delta":0,
            "execution_authority":False,
            "promotion_authority":False,
        }
    required,query=v5._requirements(public)
    if query is None or not required:
        return {
            "status":"FAIL_CLOSED__INVALID_REQUIREMENTS",
            "universal_proof_eligible":False,
            "matched_comparator_required":True,
            "restart_required":False,
            "capability_credit_delta":0,
            "family_credit_delta":0,
            "execution_authority":False,
            "promotion_authority":False,
        }
    epoch=v5._decision_epoch(public)
    if epoch is None:
        return {
            "status":"FAIL_CLOSED__INVALID_DECISION_EPOCH",
            "universal_proof_eligible":False,
            "matched_comparator_required":True,
            "restart_required":False,
            "capability_credit_delta":0,
            "family_credit_delta":0,
            "execution_authority":False,
            "promotion_authority":False,
        }
    sources,digest,err=v5._active_sources(public)
    if err:
        return {
            "status":"FAIL_CLOSED__"+err,
            "universal_proof_eligible":False,
            "matched_comparator_required":True,
            "restart_required":False,
            "capability_credit_delta":0,
            "family_credit_delta":0,
            "execution_authority":False,
            "promotion_authority":False,
        }
    receipts,err=v5._valid_receipts(
        public,sources,decision_epoch=epoch,source_set_digest=digest,query=query
    )
    if err:
        return {
            "status":"FAIL_CLOSED__"+err,
            "universal_proof_eligible":False,
            "matched_comparator_required":True,
            "restart_required":False,
            "capability_credit_delta":0,
            "family_credit_delta":0,
            "execution_authority":False,
            "promotion_authority":False,
        }
    missing=[str(s["source_id"]) for s in sources if str(s["source_id"]) not in receipts]
    if missing:
        return {
            "status":"DISCOVERY_NOT_SATURATED",
            "missing_source_ids":missing,
            "universal_proof_eligible":False,
            "matched_comparator_required":False,
            "restart_required":False,
            "capability_credit_delta":0,
            "family_credit_delta":0,
            "execution_authority":False,
            "promotion_authority":False,
        }

    tools,err=v5._catalog(public,receipts)
    if err:
        return {
            "status":"FAIL_CLOSED__"+err,
            "universal_proof_eligible":False,
            "matched_comparator_required":True,
            "restart_required":False,
            "capability_credit_delta":0,
            "family_credit_delta":0,
            "execution_authority":False,
            "promotion_authority":False,
        }
    evidence,err=v5._evidence(public,tools)
    if err:
        return {
            "status":"FAIL_CLOSED__"+err,
            "universal_proof_eligible":False,
            "matched_comparator_required":True,
            "restart_required":False,
            "capability_credit_delta":0,
            "family_credit_delta":0,
            "execution_authority":False,
            "promotion_authority":False,
        }

    admissible=[]
    constraint=public.get("constraint")
    for tool in tools:
        if (
            tool.get("available") is True
            and tool.get("authorized") is True
            and v5._pred(constraint,tool)
        ):
            cap_state={}
            for cap in required:
                val=evidence.get((str(tool.get("tool_id") or ""),cap))
                cap_state[cap]=(
                    obs.TRUE if val is True else
                    obs.FALSE if val is False else
                    obs.UNKNOWN
                )
            admissible.append({
                "tool_id":str(tool.get("tool_id") or ""),
                "cost":float(tool.get("cost",0.0)),
                "capability_evidence":cap_state,
                "safe_probe_capabilities":list(tool.get("safe_probe_capabilities") or []),
            })
    return obs.classify({
        "identity_scope_complete":True,
        "required_capabilities":required,
        "admissible_tools":admissible,
    })
