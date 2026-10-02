"""Fail-closed activation candidate for independently verified composition behavioral bridge."""
from __future__ import annotations
from typing import Any, Mapping
from canonical.runtime.composition_component_proof_slicer_v1 import evaluate as slice_evaluate

SCHEMA="PROJECT_BRAIN_COMPOSITION_BEHAVIORAL_BRIDGE_ACTIVATION_VERDICT_V1"
CLAIM="MULTI_CAPABILITY_COMPOSITION::FROZEN_PROTOCOL_V1"
EXPECTED_VERIFY_STATUS="INDEPENDENT_PUBLIC_RUNNER_PASS__EXACT_TWO_COMPONENT_BEHAVIORAL_BRIDGE__ZERO_CREDIT"

def _fail(*errors:str)->dict[str,Any]:
    return {"schema":SCHEMA,"status":"FAIL_CLOSED","pass":False,"errors":sorted(set(errors)),
            "candidate_receipt_count":0,"projected_scoped_proved_interface_count":0,
            "projected_open_interface_count":0,"slice_input_authorized":False,
            "capability_credit_delta":0,"family_credit_delta":0,"new_reality_units_consumed":0,
            "execution_authority":False,"promotion_authority":False}

def derive_receipts(bridge:Mapping[str,Any], verification:Mapping[str,Any])->list[dict[str,Any]]:
    verified_components=verification.get("independently_verified_components")
    bindings=bridge.get("bindings")
    if not isinstance(verified_components,list) or not isinstance(bindings,list):
        return []
    allowed=set(verified_components)
    out=[]
    for b in bindings:
        if not isinstance(b,Mapping) or b.get("component_id") not in allowed:
            continue
        out.append({
            "receipt_id":f"COMPOSITION_BRIDGE::{b.get('closure_evidence_id')}::{b.get('component_id')}",
            "component_id":b.get("component_id"),
            "interface_id":b.get("interface_id"),
            "proved_properties":list(b.get("proved_properties") or []),
            "verified":True,
            "independent":True,
            "contamination_clean":True,
            "acceptance_scoped":True,
            "binds_frozen_claim":CLAIM,
            "source_behavior_id":b.get("behavior_id"),
            "source_family":b.get("source_family"),
            "source_closure_evidence_id":b.get("closure_evidence_id"),
            "source_bridge_verification":"canonical/verification/COMPOSITION_BEHAVIORAL_BRIDGE_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json",
        })
    return sorted(out,key=lambda x:(x["component_id"],x["interface_id"],x["receipt_id"]))

def evaluate(*,bridge:Mapping[str,Any],verification:Mapping[str,Any],base_slice:Mapping[str,Any],
             activation:Mapping[str,Any],bridge_sha:str,verification_sha:str,base_slice_sha:str,slicer_sha:str)->dict[str,Any]:
    errors=[]
    if verification.get("status")!=EXPECTED_VERIFY_STATUS:
        errors.append("BRIDGE_INDEPENDENT_VERIFICATION_NOT_PASS")
    exact=verification.get("exact_brain_blobs")
    if not isinstance(exact,Mapping) or exact.get("canonical/governance/COMPOSITION_BEHAVIORAL_BRIDGE_V1.json")!=bridge_sha:
        errors.append("VERIFICATION_BRIDGE_SHA_MISMATCH")
    if verification.get("derived_binding_count")!=2:
        errors.append("VERIFIED_BINDING_COUNT_NOT_TWO")
    if sorted(verification.get("independently_verified_components") or [])!=["delegation","tool discovery"]:
        errors.append("VERIFIED_COMPONENT_SET_DRIFT")
    if bridge.get("claim_id")!=CLAIM or base_slice.get("claim_id")!=CLAIM:
        errors.append("CLAIM_ID_DRIFT")
    auth=activation.get("authority")
    expected_auth={
      "bridge":{"path":"canonical/governance/COMPOSITION_BEHAVIORAL_BRIDGE_V1.json","git_blob_sha":bridge_sha},
      "bridge_verification":{"path":"canonical/verification/COMPOSITION_BEHAVIORAL_BRIDGE_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json","git_blob_sha":verification_sha},
      "base_slice":{"path":"canonical/governance/COMPOSITION_COMPONENT_PROOF_SLICE_INPUT_V1.json","git_blob_sha":base_slice_sha},
      "slicer":{"path":"canonical/runtime/composition_component_proof_slicer_v1.py","git_blob_sha":slicer_sha},
    }
    if auth!=expected_auth:
        errors.append("ACTIVATION_AUTHORITY_MISMATCH")
    expected=derive_receipts(bridge,verification)
    actual=activation.get("candidate_receipts")
    if not isinstance(actual,list) or sorted(actual,key=lambda x:(x.get("component_id"),x.get("interface_id"),x.get("receipt_id")))!=expected:
        errors.append("CANDIDATE_RECEIPTS_NOT_EXACT_DERIVATION")
    state=activation.get("verification_state")
    if not isinstance(state,Mapping) or state.get("independent_verification") is not False or state.get("slice_input_authorized") is not False:
        errors.append("CANDIDATE_SELF_AUTHORIZATION_FORBIDDEN")
    if errors:
        return _fail(*errors)
    projected=dict(base_slice)
    projected["receipts"]=expected
    sliced=slice_evaluate(projected)
    scoped=sum(1 for x in sliced.get("interfaces",[]) if x.get("state")=="SCOPED_PROVED")
    open_count=sum(1 for x in sliced.get("interfaces",[]) if x.get("state")=="OPEN")
    if scoped!=2 or open_count!=10:
        return _fail("PROJECTED_SLICE_NOT_2_PROVED_10_OPEN")
    if {x["component_id"] for x in sliced["interfaces"] if x["state"]=="SCOPED_PROVED"}!={"delegation","tool discovery"}:
        return _fail("PROJECTED_PROVED_COMPONENT_SET_DRIFT")
    return {"schema":SCHEMA,"status":"PASS__TWO_EXACT_COMPONENT_RECEIPTS_PROJECT_TO_2_PROVED_10_OPEN__INDEPENDENT_ACTIVATION_REQUIRED",
            "pass":True,"errors":[],"candidate_receipts":expected,"candidate_receipt_count":2,
            "projected_slice_result":sliced,"projected_scoped_proved_interface_count":2,
            "projected_open_interface_count":10,"slice_input_authorized":False,
            "capability_credit_delta":0,"family_credit_delta":0,"new_reality_units_consumed":0,
            "execution_authority":False,"promotion_authority":False}
