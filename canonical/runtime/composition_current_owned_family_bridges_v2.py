"""Fail-closed current composition owned-family bridge derivation.

Derives exactly two candidate component receipts:
- memory, from the already-owned LONG_HORIZON_MEMORY_AND_CONTINUITY family;
- delegation, by restoring the previously independently verified component mapping
  after current universal-scope whole-family closure.

This runtime never self-authorizes either receipt. Independent verification must
reconstruct the exact source bindings before setting verified/independent true.
"""
from __future__ import annotations

import copy
import re
from typing import Any, Mapping

SCHEMA="PROJECT_BRAIN_COMPOSITION_CURRENT_OWNED_FAMILY_BRIDGES_V2"
CLAIM="MULTI_CAPABILITY_COMPOSITION::FROZEN_PROTOCOL_V1"
MEMORY_FAMILY="LONG_HORIZON_MEMORY_AND_CONTINUITY"
DELEGATION_FAMILY="SUBAGENT_DELEGATION_AND_COORDINATION"
TOOL_FAMILY="TOOL_DISCOVERY_SELECTION_AND_LEARNING"

def _fail(*errors: str) -> dict[str,Any]:
    return {
        "schema":SCHEMA,"status":"FAIL_CLOSED","errors":sorted(set(errors)),
        "candidate_receipts":[],
        "new_reality_units_consumed":0,"incremental_spend_usd":0,
        "capability_credit_delta":0,"family_credit_delta":0,
        "execution_authority":False,"promotion_authority":False,
    }

def _family(rows: list[Mapping[str,Any]], family: str) -> Mapping[str,Any] | None:
    xs=[x for x in rows if isinstance(x,Mapping) and x.get("family")==family]
    return xs[0] if len(xs)==1 else None

def _claim(rows: list[Mapping[str,Any]], predicate: str) -> Mapping[str,Any] | None:
    xs=[x for x in rows if isinstance(x,Mapping) and x.get("predicate_id")==predicate]
    return xs[0] if len(xs)==1 else None

def derive(
    envelope: Mapping[str,Any],
    protocols: Mapping[str,Any],
    manifest: Mapping[str,Any],
    baseline: Mapping[str,Any],
    memory_package: Mapping[str,Any],
    predicate_bindings: Mapping[str,Any],
    historical_bridge_verification: Mapping[str,Any],
    delegation_acceptance_verification: Mapping[str,Any],
    delegation_scope_verification: Mapping[str,Any],
) -> dict[str,Any]:
    errors=[]
    families=envelope.get("families")
    prows=protocols.get("protocols")
    interfaces=manifest.get("interfaces")
    base_interfaces=baseline.get("interfaces")
    claims=predicate_bindings.get("claims")
    if not isinstance(families,list) or envelope.get("target_family_count")!=19:
        errors.append("ENVELOPE_NOT_CLOSED_19_FAMILY_WORLD")
    if not isinstance(prows,list):
        errors.append("PROTOCOL_ROWS_INVALID")
    if not isinstance(interfaces,list) or len(interfaces)!=12:
        errors.append("MANIFEST_NOT_12_INTERFACES")
    if not isinstance(base_interfaces,list) or len(base_interfaces)!=12 or baseline.get("receipts")!=[]:
        errors.append("BASELINE_NOT_12_INTERFACE_ZERO_RECEIPT_INPUT")
    if not isinstance(claims,list):
        errors.append("PREDICATE_BINDINGS_INVALID")
    if errors:
        return _fail(*errors)

    composition=_family(prows,"MULTI_CAPABILITY_COMPOSITION")
    memory_protocol=_family(prows,MEMORY_FAMILY)
    delegation_protocol=_family(prows,DELEGATION_FAMILY)
    if not composition or not memory_protocol or not delegation_protocol:
        return _fail("REQUIRED_PROTOCOL_FAMILY_NOT_UNIQUE")

    if composition.get("task_dimensions")!=manifest.get("source_task_dimensions"):
        errors.append("CURRENT_COMPOSITION_DIMENSIONS_DIFFER_FROM_FROZEN_MANIFEST")
    if composition.get("acceptance")!=manifest.get("source_acceptance_literal"):
        errors.append("CURRENT_COMPOSITION_ACCEPTANCE_DIFFERS_FROM_FROZEN_MANIFEST")

    mem_lit=[x for x in families if isinstance(x,Mapping) and re.search(r"\bmemory\b", str(x.get("useful_behavior","")), flags=re.IGNORECASE)]
    mem_ids=sorted(str(x.get("id")) for x in mem_lit)
    if mem_ids!=sorted([MEMORY_FAMILY,"MULTI_CAPABILITY_COMPOSITION"]):
        errors.append("MEMORY_LITERAL_NOT_UNIQUE_TO_MEMORY_AND_COMPOSITION_FAMILIES")
    if memory_protocol.get("status")!="PASS":
        errors.append("MEMORY_PROTOCOL_NOT_PASS")
    if memory_package.get("family")!=MEMORY_FAMILY or memory_package.get("status")!="VERIFIED_OWNED_EQUAL_OR_BETTER":
        errors.append("MEMORY_OWNERSHIP_PACKAGE_NOT_CURRENTLY_OWNED")
    decision=memory_package.get("decision",{})
    if not isinstance(decision,Mapping) or decision.get("parent_family_closed_for_claim_scope") is not True:
        errors.append("MEMORY_PARENT_FAMILY_NOT_CLOSED_FOR_CLAIM_SCOPE")
    claim_scope=memory_package.get("claim_scope")
    excluded=memory_package.get("excluded_scope")
    if not isinstance(claim_scope,str) or not claim_scope or not isinstance(excluded,list) or not excluded:
        errors.append("MEMORY_SCOPE_OR_EXCLUSIONS_MISSING")

    del_claim=_claim(claims,"DELEGATION_TERMINAL_SUCCESS_NONINFERIOR")
    tool_claim=_claim(claims,"TOOL_LEARNING_SUCCESS_ROUTE_NONINFERIOR")
    if delegation_protocol.get("status")!="PASS":
        errors.append("DELEGATION_PROTOCOL_NOT_PASS")
    if delegation_protocol.get("closure_receipt")!="canonical/verification/DELEGATION_ACCEPTANCE_REDUCTION_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json":
        errors.append("DELEGATION_PROTOCOL_CLOSURE_RECEIPT_MISMATCH")
    if not del_claim or del_claim.get("state")!="PROVED" or del_claim.get("scope_complete") is not True or del_claim.get("objective_ceiling") is not True:
        errors.append("DELEGATION_ATOMIC_CLOSURE_NOT_SCOPE_COMPLETE")
    if not tool_claim or tool_claim.get("state")=="PROVED":
        errors.append("TOOL_DISCOVERY_MUST_REMAIN_UNPROVED_AND_EXCLUDED")

    if not str(historical_bridge_verification.get("status","")).startswith("INDEPENDENT_PUBLIC_RUNNER_PASS"):
        errors.append("HISTORICAL_COMPONENT_MAPPING_NOT_INDEPENDENTLY_VERIFIED")
    comps=historical_bridge_verification.get("independently_verified_components")
    if not isinstance(comps,list) or "delegation" not in comps:
        errors.append("DELEGATION_COMPONENT_MAPPING_NOT_VERIFIED")

    if not str(delegation_acceptance_verification.get("status","")).startswith("INDEPENDENT_PUBLIC_RUNNER_PASS"):
        errors.append("DELEGATION_ACCEPTANCE_CLOSURE_NOT_INDEPENDENT_PASS")
    vr=delegation_acceptance_verification.get("verified_result",{})
    if not isinstance(vr,Mapping) or DELEGATION_FAMILY not in vr.get("newly_closed_families",[]) or vr.get("scope_completeness_basis")!="UNIVERSAL_FORMAL_SCOPE_PROOF":
        errors.append("DELEGATION_WHOLE_FAMILY_CLOSURE_NOT_UNIVERSAL")

    if not str(delegation_scope_verification.get("status","")).startswith("INDEPENDENT_PUBLIC_RUNNER_PASS"):
        errors.append("DELEGATION_SCOPE_VERIFICATION_NOT_PASS")
    if delegation_scope_verification.get("target_predicate")!="DELEGATION_TERMINAL_SUCCESS_NONINFERIOR":
        errors.append("DELEGATION_SCOPE_TARGET_MISMATCH")
    verified=delegation_scope_verification.get("verified",[])
    if not isinstance(verified,list) or "UNIVERSAL_SCOPE_PROVED_TRUE" not in verified:
        errors.append("DELEGATION_UNIVERSAL_SCOPE_NOT_VERIFIED")

    base_keys={(x.get("component_id"),x.get("interface_id")) for x in base_interfaces if isinstance(x,Mapping)}
    memory_key=("memory","browser/computer action+memory+recovery")
    delegation_key=("delegation","delegation+evidence synthesis+artifact production")
    if memory_key not in base_keys or delegation_key not in base_keys:
        errors.append("TARGET_COMPONENT_INTERFACES_NOT_IN_FROZEN_BASELINE")
    if errors:
        return _fail(*errors)

    receipts=[
        {
            "receipt_id":"COMPOSITION_OWNED_FAMILY_BRIDGE_V2::LONG_HORIZON_MEMORY_AND_CONTINUITY::memory",
            "component_id":"memory",
            "interface_id":"browser/computer action+memory+recovery",
            "proved_properties":["SCOPED_ACCEPTANCE_PROOF"],
            "verified":False,
            "independent":False,
            "contamination_clean":True,
            "acceptance_scoped":True,
            "binds_frozen_claim":CLAIM,
            "source_family":MEMORY_FAMILY,
            "source_witness_path":"canonical/capabilities/opus55/OPUS55_LONG_HORIZON_MEMORY_AND_CONTINUITY_V1.json",
            "included_scope":claim_scope,
            "excluded_scope":copy.deepcopy(excluded),
        },
        {
            "receipt_id":"COMPOSITION_RESTORED_BRIDGE_V2::TASK_TO_DELEGATION_GRAPH_001::delegation",
            "component_id":"delegation",
            "interface_id":"delegation+evidence synthesis+artifact production",
            "proved_properties":["SCOPED_ACCEPTANCE_PROOF"],
            "verified":False,
            "independent":False,
            "contamination_clean":True,
            "acceptance_scoped":True,
            "binds_frozen_claim":CLAIM,
            "source_family":DELEGATION_FAMILY,
            "behavior_id":"TASK_TO_DELEGATION_GRAPH_001",
            "component_mapping_verification":"canonical/verification/COMPOSITION_BEHAVIORAL_BRIDGE_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json",
            "source_witness_path":"canonical/verification/DELEGATION_ACCEPTANCE_REDUCTION_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json",
            "scope_verification":"canonical/verification/DELEGATION_V4_UNIVERSAL_SCOPE_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json",
        },
    ]
    return {
        "schema":SCHEMA,
        "status":"PASS__EXACT_TWO_CURRENT_CANDIDATE_RECEIPTS__INDEPENDENT_VERIFICATION_REQUIRED__ZERO_CREDIT",
        "errors":[],
        "claim_id":CLAIM,
        "candidate_receipts":receipts,
        "forbidden_component_receipts":["tool discovery"],
        "expected_after_independent_verification":{
            "scoped_proved_components":["delegation","memory"],
            "scoped_proved_interface_count":2,
            "open_interface_count":10,
            "parent_composition_predicate_closed":False,
        },
        "rules":[
            "CANDIDATE_RECEIPTS_ARE_NOT_SELF_VERIFIED",
            "MEMORY_BINDING_PRESERVES_OWNED_PACKAGE_SCOPE_AND_ALL_EXCLUSIONS",
            "DELEGATION_MAPPING_REUSES_PRIOR_INDEPENDENT_COMPONENT_MAPPING_ONLY_AFTER_NEW_UNIVERSAL_SCOPE_WHOLE_FAMILY_CLOSURE",
            "TOOL_DISCOVERY_RECEIPT_REMAINS_QUARANTINED",
            "NO_PARENT_COMPOSITION_ACCEPTANCE_FROM_TWO_OF_TWELVE_COMPONENTS",
        ],
        "new_reality_units_consumed":0,"incremental_spend_usd":0,
        "capability_credit_delta":0,"family_credit_delta":0,
        "execution_authority":False,"promotion_authority":False,
    }
