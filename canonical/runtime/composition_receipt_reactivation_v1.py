"""Recompute currently admissible composition component receipts from verified bindings.

Fail closed. This compiler grants no family/acceptance credit. It only reactivates
previously independently verified component bindings when their source family is
currently PASS, and admits the separately declared memory-owned bridge when its
exact scoped ownership preconditions hold.
"""
from __future__ import annotations
import argparse, copy, json
from pathlib import Path

CLAIM="MULTI_CAPABILITY_COMPOSITION::FROZEN_PROTOCOL_V1"
PASS="PASS"

def load(path: Path):
    v=json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(v,dict):
        raise ValueError(f"{path} must contain a JSON object")
    return v

def evaluate(manifest, protocols, bridge, bridge_verification, memory_bridge, memory_package):
    errors=[]
    if manifest.get("claim_id")!=CLAIM: errors.append("MANIFEST_CLAIM_MISMATCH")
    if bridge.get("claim_id")!=CLAIM: errors.append("BRIDGE_CLAIM_MISMATCH")
    if memory_bridge.get("claim_id")!=CLAIM: errors.append("MEMORY_BRIDGE_CLAIM_MISMATCH")
    interfaces={(x.get("component_id"),x.get("interface_id")) for x in manifest.get("interfaces",[]) if isinstance(x,dict)}
    if len(interfaces)!=12: errors.append("INTERFACE_SET_NOT_EXACT_12")
    protos={x.get("family"):x for x in protocols.get("protocols",[]) if isinstance(x,dict) and isinstance(x.get("family"),str)}
    activated=set(bridge_verification.get("activated_components",[]))
    if not str(bridge_verification.get("status","")).startswith("INDEPENDENT_PUBLIC_RUNNER_PASS"):
        errors.append("HISTORICAL_BRIDGE_NOT_INDEPENDENTLY_VERIFIED")

    admitted=[]
    quarantined=[]
    for b in bridge.get("bindings",[]):
        if not isinstance(b,dict):
            errors.append("MALFORMED_BRIDGE_BINDING"); continue
        comp=b.get("component_id"); iface=b.get("interface_id"); fam=b.get("source_family")
        if (comp,iface) not in interfaces:
            errors.append(f"BRIDGE_INTERFACE_MISMATCH:{comp}"); continue
        if comp not in activated:
            errors.append(f"BRIDGE_COMPONENT_NOT_IN_VERIFIED_ACTIVATION:{comp}"); continue
        if "SCOPED_ACCEPTANCE_PROOF" not in (b.get("proved_properties") or []):
            errors.append(f"BRIDGE_REQUIRED_PROPERTY_MISSING:{comp}"); continue
        state=(protos.get(fam) or {}).get("status")
        if state==PASS:
            admitted.append({
                "receipt_id":f"COMPOSITION_REACTIVATED::{comp}",
                "component_id":comp,
                "interface_id":iface,
                "source_family":fam,
                "basis":"PREVIOUSLY_INDEPENDENTLY_VERIFIED_COMPONENT_BINDING_PLUS_CURRENT_SOURCE_FAMILY_PASS",
                "acceptance_scoped":True,
                "contamination_clean":True
            })
        else:
            quarantined.append({"component_id":comp,"source_family":fam,"source_family_status":state or "MISSING"})

    mb=memory_bridge.get("component_binding") or {}
    mr=memory_bridge.get("candidate_receipt") or {}
    md=memory_bridge.get("derivation") or {}
    pkg_dec=memory_package.get("decision") or {}
    memory_checks=[
        ("MEMORY_INTERFACE_MISMATCH",(mb.get("component_id"),mb.get("interface_id")) in interfaces),
        ("MEMORY_RECEIPT_COMPONENT_MISMATCH",mr.get("component_id")==mb.get("component_id") and mr.get("interface_id")==mb.get("interface_id")),
        ("MEMORY_RECEIPT_NOT_CONTAMINATION_CLEAN",mr.get("contamination_clean") is True),
        ("MEMORY_RECEIPT_NOT_ACCEPTANCE_SCOPED",mr.get("acceptance_scoped") is True),
        ("MEMORY_RECEIPT_CLAIM_MISMATCH",mr.get("binds_frozen_claim")==CLAIM),
        ("MEMORY_SOURCE_FAMILY_NOT_CURRENT_PASS",(protos.get(mr.get("source_family")) or {}).get("status")==PASS),
        ("MEMORY_PACKAGE_STATUS_NOT_OWNED",memory_package.get("status")=="VERIFIED_OWNED_EQUAL_OR_BETTER"),
        ("MEMORY_PARENT_FAMILY_NOT_CLOSED",pkg_dec.get("parent_family_closed_for_claim_scope") is True),
        ("MEMORY_DERIVATION_SCOPE_NOT_CLOSED",md.get("owned_memory_parent_family_closed_for_claim_scope") is True),
        ("MEMORY_SCOPE_DRIFT",memory_package.get("claim_scope")==(memory_bridge.get("scope_guard") or {}).get("included_scope")),
    ]
    bad=[name for name,ok in memory_checks if not ok]
    if bad:
        quarantined.append({"component_id":"memory","reasons":bad})
    else:
        admitted.append({
            "receipt_id":"COMPOSITION_OWNED_FAMILY_BRIDGE::LONG_HORIZON_MEMORY_AND_CONTINUITY::memory",
            "component_id":"memory",
            "interface_id":mb.get("interface_id"),
            "source_family":"LONG_HORIZON_MEMORY_AND_CONTINUITY",
            "basis":"EXACT_SCOPED_OWNERSHIP_PACKAGE_PLUS_CURRENT_SOURCE_FAMILY_PASS",
            "acceptance_scoped":True,
            "contamination_clean":True
        })

    comps=[x["component_id"] for x in admitted]
    if len(comps)!=len(set(comps)): errors.append("DUPLICATE_ADMITTED_COMPONENT")
    if any((x["component_id"],x["interface_id"]) not in interfaces for x in admitted):
        errors.append("ADMITTED_INTERFACE_OUTSIDE_FROZEN_MANIFEST")
    admitted=sorted(admitted,key=lambda x:x["component_id"])
    open_components=sorted({c for c,_ in interfaces}-{x["component_id"] for x in admitted})
    return {
        "schema":"PROJECT_BRAIN_COMPOSITION_RECEIPT_REACTIVATION_VERDICT_V1",
        "status":"PASS" if not errors else "FAIL_CLOSED",
        "errors":sorted(set(errors)),
        "claim_id":CLAIM,
        "scoped_proved_interface_count":len(admitted) if not errors else 0,
        "open_interface_count":len(open_components) if not errors else 12,
        "admitted_receipts":admitted if not errors else [],
        "quarantined_bindings":sorted(quarantined,key=lambda x:str(x.get("component_id"))),
        "open_components":open_components if not errors else sorted({c for c,_ in interfaces}),
        "parent_composition_predicate_closed":False,
        "atomic_acceptance_credit_delta":0,
        "family_credit_delta":0,
        "capability_credit_delta":0,
        "new_reality_units_consumed":0,
        "execution_authority":False,
        "promotion_authority":False,
        "rule":"REACTIVATE_ONLY_EXPLICIT_PREVERIFIED_COMPONENT_BINDINGS_WITH_CURRENT_SOURCE_FAMILY_PASS__MEMORY_ONLY_FROM_EXACT_SCOPED_OWNERSHIP_PACKAGE__NO_ANALOGY_OR_PARENT_CREDIT"
    }

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--manifest",type=Path,required=True)
    ap.add_argument("--protocols",type=Path,required=True)
    ap.add_argument("--bridge",type=Path,required=True)
    ap.add_argument("--bridge-verification",type=Path,required=True)
    ap.add_argument("--memory-bridge",type=Path,required=True)
    ap.add_argument("--memory-package",type=Path,required=True)
    a=ap.parse_args()
    out=evaluate(*(load(x) for x in [a.manifest,a.protocols,a.bridge,a.bridge_verification,a.memory_bridge,a.memory_package]))
    print(json.dumps(out,indent=2,sort_keys=True))
    raise SystemExit(0 if out["status"]=="PASS" else 1)

if __name__=="__main__":
    main()
