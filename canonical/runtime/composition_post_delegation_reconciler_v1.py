"""Fail-closed post-delegation composition component reconciliation.

This module grants no terminal credit. It checks whether two candidate component
receipts are mechanically admissible against current content-addressed authority:
(1) delegation after universal scope-complete family closure, and
(2) the already-owned scoped continuity family for the literal memory component.
"""
from __future__ import annotations
import hashlib, json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]

FILES = {
    "manifest": ("canonical/governance/FROZEN_COMPOSITION_COMPONENT_INTERFACE_MANIFEST_V1.json", "9efbf3e81e67fbd15e34be2fcd86fbfc626b246d"),
    "historical_bridge": ("canonical/governance/COMPOSITION_BEHAVIORAL_BRIDGE_ACTIVATION_V1.json", "59504f4608f9490022c1aa58214e34191fb0b6e9"),
    "acceptance": ("canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json", "7885a827b1483bfb38315c1f492848f7e4680285"),
    "delegation_verification": ("canonical/verification/DELEGATION_ACCEPTANCE_REDUCTION_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json", "d04f2a8c5594d261158835db1cae3822411b6b23"),
    "protocols": ("canonical/governance/OPUS55_TERMINAL_PROOF_PROTOCOLS_V1.json", "62394e5b7d221ec9f69c3458f669e40e253a9d09"),
    "envelope": ("canonical/capabilities/opus55/OPUS_5_5_USEFUL_CAPABILITY_ENVELOPE_V1.json", "661a57f839101fbf54c7e4edc76166c65ce9327d"),
    "memory_package": ("canonical/capabilities/opus55/OPUS55_LONG_HORIZON_MEMORY_AND_CONTINUITY_V1.json", "2d912cf8df64bd806fffb6a1070d95644d005470"),
    "delegation_candidate": ("canonical/governance/COMPOSITION_DELEGATION_SCOPE_COMPLETE_BRIDGE_V1.json", None),
    "memory_candidate": ("canonical/governance/COMPOSITION_MEMORY_OWNED_FAMILY_BRIDGE_V2.json", None),
}

CLAIM = "MULTI_CAPABILITY_COMPOSITION::FROZEN_PROTOCOL_V1"

def _blob_sha(path: str) -> str:
    data=(ROOT/path).read_bytes()
    return hashlib.sha1(f"blob {len(data)}\0".encode()+data).hexdigest()

def _load(path: str) -> dict[str, Any]:
    value=json.loads((ROOT/path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(path+":NOT_OBJECT")
    return value

def _row(items: list[dict[str, Any]], key: str, value: str) -> dict[str, Any] | None:
    return next((x for x in items if x.get(key)==value), None)

def _fail(*errors: str) -> dict[str, Any]:
    return {
        "schema":"PROJECT_BRAIN_COMPOSITION_POST_DELEGATION_RECONCILER_V1",
        "status":"FAIL_CLOSED",
        "errors":sorted(set(errors)),
        "current_admissible_scoped_proved":0,
        "current_open_or_quarantined":12,
        "scoped_proved_components":[],
        "parent_composition_predicate_closed":False,
        "new_reality_units_consumed":0,
        "terminal_results_replayed":0,
        "capability_credit_delta":0,
        "family_credit_delta":0,
        "execution_authority":False,
        "promotion_authority":False,
    }

def evaluate(*, acceptance_override: dict[str, Any] | None=None, memory_package_override: dict[str, Any] | None=None) -> dict[str, Any]:
    drift=[path for path,expected in FILES.values() if expected and _blob_sha(path)!=expected]
    if drift:
        return _fail(*["SOURCE_BLOB_DRIFT:"+x for x in drift])

    manifest=_load(FILES["manifest"][0])
    bridge=_load(FILES["historical_bridge"][0])
    acceptance=acceptance_override or _load(FILES["acceptance"][0])
    delegation_verification=_load(FILES["delegation_verification"][0])
    protocols=_load(FILES["protocols"][0])
    envelope=_load(FILES["envelope"][0])
    memory_package=memory_package_override or _load(FILES["memory_package"][0])
    delegation_candidate=_load(FILES["delegation_candidate"][0])
    memory_candidate=_load(FILES["memory_candidate"][0])

    errors=[]

    interfaces=manifest.get("interfaces") or []
    delegation_interface=_row(interfaces,"component_id","delegation")
    memory_interface=_row(interfaces,"component_id","memory")
    if not delegation_interface or delegation_interface.get("interface_id")!="delegation+evidence synthesis+artifact production":
        errors.append("FROZEN_DELEGATION_INTERFACE_MISSING_OR_DRIFTED")
    if not memory_interface or memory_interface.get("interface_id")!="browser/computer action+memory+recovery":
        errors.append("FROZEN_MEMORY_INTERFACE_MISSING_OR_DRIFTED")

    historical_receipts=bridge.get("receipts") or []
    mapped=_row(historical_receipts,"component_id","delegation")
    if not mapped:
        errors.append("VERIFIED_LITERAL_DELEGATION_MAPPING_MISSING")
    else:
        if mapped.get("source_family")!="SUBAGENT_DELEGATION_AND_COORDINATION":
            errors.append("DELEGATION_MAPPING_SOURCE_FAMILY_DRIFT")
        if mapped.get("binds_frozen_claim")!=CLAIM:
            errors.append("DELEGATION_MAPPING_CLAIM_DRIFT")
        if mapped.get("acceptance_scoped") is not True or mapped.get("contamination_clean") is not True:
            errors.append("DELEGATION_MAPPING_NOT_ACCEPTANCE_SCOPED_CLEAN")

    claims=acceptance.get("claims") or []
    dclaim=_row(claims,"predicate_id","DELEGATION_TERMINAL_SUCCESS_NONINFERIOR")
    tclaim=_row(claims,"predicate_id","TOOL_LEARNING_SUCCESS_ROUTE_NONINFERIOR")
    if not dclaim or dclaim.get("state")!="PROVED" or dclaim.get("scope_complete") is not True or dclaim.get("objective_ceiling") is not True:
        errors.append("CURRENT_DELEGATION_SCOPE_COMPLETE_ACCEPTANCE_NOT_PROVED")
    if not dclaim or dclaim.get("source_path")!="canonical/verification/DELEGATION_ACCEPTANCE_REDUCTION_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json":
        errors.append("CURRENT_DELEGATION_ACCEPTANCE_SOURCE_NOT_BOUND")
    if not tclaim or tclaim.get("state")=="PROVED":
        errors.append("TOOL_DISCOVERY_MUST_REMAIN_QUARANTINED")

    vr=delegation_verification
    if not str(vr.get("status","")).startswith("INDEPENDENT_PUBLIC_RUNNER_PASS"):
        errors.append("DELEGATION_CURRENT_CLOSURE_NOT_INDEPENDENT_PASS")
    if "SUBAGENT_DELEGATION_AND_COORDINATION" not in ((vr.get("verified_result") or {}).get("newly_closed_families") or []):
        errors.append("DELEGATION_FAMILY_NOT_NEWLY_CLOSED_IN_CURRENT_RECEIPT")
    if ((vr.get("verified_result") or {}).get("scope_completeness_basis"))!="UNIVERSAL_FORMAL_SCOPE_PROOF":
        errors.append("DELEGATION_SCOPE_BASIS_NOT_UNIVERSAL_FORMAL")

    plist=protocols.get("protocols") or []
    dp=_row(plist,"family","SUBAGENT_DELEGATION_AND_COORDINATION")
    mp=_row(plist,"family","LONG_HORIZON_MEMORY_AND_CONTINUITY")
    if not dp or dp.get("status")!="PASS":
        errors.append("DELEGATION_PROTOCOL_NOT_CURRENT_PASS")
    if not mp or mp.get("status")!="PASS":
        errors.append("MEMORY_PROTOCOL_NOT_CURRENT_PASS")

    families=envelope.get("families") or []
    if len(families)!=19:
        errors.append("TERMINAL_ENVELOPE_NOT_19_FAMILIES")
    memory_role_families=[
        x for x in families
        if x.get("id")!="MULTI_CAPABILITY_COMPOSITION"
        and "memory" in str(x.get("useful_behavior","")).lower()
    ]
    if [x.get("id") for x in memory_role_families] != ["LONG_HORIZON_MEMORY_AND_CONTINUITY"]:
        errors.append("MEMORY_ROLE_NOT_UNIQUE_CLOSED_WORLD_FAMILY")
    comp=_row(families,"id","MULTI_CAPABILITY_COMPOSITION")
    if not comp or "memory" not in str(comp.get("useful_behavior","")).lower():
        errors.append("COMPOSITION_ENVELOPE_MEMORY_ROLE_MISSING")

    if memory_package.get("status")!="VERIFIED_OWNED_EQUAL_OR_BETTER":
        errors.append("MEMORY_PACKAGE_NOT_VERIFIED_OWNED_EQUAL_OR_BETTER")
    if memory_package.get("family")!="LONG_HORIZON_MEMORY_AND_CONTINUITY":
        errors.append("MEMORY_PACKAGE_FAMILY_DRIFT")
    if ((memory_package.get("decision") or {}).get("parent_family_closed_for_claim_scope")) is not True:
        errors.append("MEMORY_PARENT_FAMILY_NOT_CLOSED_FOR_CLAIM_SCOPE")
    if memory_candidate.get("scope_guard",{}).get("included_scope")!=memory_package.get("claim_scope"):
        errors.append("MEMORY_INCLUDED_SCOPE_NOT_EXACT_PACKAGE_SCOPE")
    if memory_candidate.get("scope_guard",{}).get("excluded_scope")!=memory_package.get("excluded_scope"):
        errors.append("MEMORY_EXCLUDED_SCOPE_NOT_PRESERVED")

    dc=delegation_candidate.get("candidate_receipt") or {}
    mc=memory_candidate.get("candidate_receipt") or {}
    for label,rec,component,interface in [
        ("DELEGATION",dc,"delegation","delegation+evidence synthesis+artifact production"),
        ("MEMORY",mc,"memory","browser/computer action+memory+recovery"),
    ]:
        if rec.get("component_id")!=component or rec.get("interface_id")!=interface:
            errors.append(label+"_CANDIDATE_RECEIPT_INTERFACE_DRIFT")
        if rec.get("proved_properties")!=["SCOPED_ACCEPTANCE_PROOF"]:
            errors.append(label+"_CANDIDATE_RECEIPT_PROPERTY_DRIFT")
        if rec.get("verified") is not False or rec.get("independent") is not False:
            errors.append(label+"_CANDIDATE_MUST_NOT_SELF_ASSERT_VERIFICATION")
        if rec.get("acceptance_scoped") is not True or rec.get("contamination_clean") is not True:
            errors.append(label+"_CANDIDATE_NOT_ACCEPTANCE_SCOPED_CLEAN")
        if rec.get("binds_frozen_claim")!=CLAIM:
            errors.append(label+"_CANDIDATE_CLAIM_DRIFT")

    if errors:
        return _fail(*errors)

    return {
        "schema":"PROJECT_BRAIN_COMPOSITION_POST_DELEGATION_RECONCILER_V1",
        "status":"PASS__CURRENT_POST_DELEGATION_TRUTH_RECONCILED__TWO_COMPONENT_RECEIPTS_ELIGIBLE_AFTER_INDEPENDENT_VERIFICATION__ZERO_PARENT_CREDIT",
        "errors":[],
        "source_blob_drift":[],
        "current_acceptance":"3_OF_19__8_OF_38",
        "stale_v3_zero_of_12_invalidated_by_current_delegation_closure":True,
        "tool_discovery_remains_quarantined":True,
        "candidate_receipts":[dc,mc],
        "current_admissible_scoped_proved":2,
        "current_open_or_quarantined":10,
        "scoped_proved_components":["delegation","memory"],
        "parent_composition_predicate_closed":False,
        "new_reality_units_consumed":0,
        "terminal_results_replayed":0,
        "incremental_spend_usd":0,
        "capability_credit_delta":0,
        "family_credit_delta":0,
        "execution_authority":False,
        "promotion_authority":False,
    }

def main() -> int:
    out=evaluate()
    print(json.dumps(out,indent=2,sort_keys=True))
    return 0 if str(out.get("status","")).startswith("PASS") else 1

if __name__=="__main__":
    raise SystemExit(main())
