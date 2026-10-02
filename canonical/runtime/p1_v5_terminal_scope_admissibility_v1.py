"""Fail-closed admissibility gate for transporting verified P1 V5 prewave
proof into the three frozen P1 terminal direct surfaces.

V5 can prove a stronger synthetic envelope without automatically proving that the
frozen T0/T2 surfaces are contained in that envelope. This module requires a
claim-bound independently verified EXACT or SUPERSET relation for each surface.
Even complete scope transport is not itself P1 clearance: composite restoration
must still be independently reconciled.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

ROOT=Path(__file__).resolve().parents[2]
SCHEMA="PROJECT_BRAIN_P1_V5_TERMINAL_SCOPE_ADMISSIBILITY_V1"
BINDING="canonical/governance/P1_TRAJECTORY_T0_T2_MULTIPLEX_TERMINAL_BINDING_V1.json"
V5_ACTIVATION="canonical/governance/P1_TYPED_INTERVENTION_ENVELOPE_V5_ACTIVATION_V1.json"
RELATIONS="canonical/governance/P1_V5_TERMINAL_SCOPE_RELATIONS_V1.json"
EXPECTED_SURFACES={
    "T0/FRONTIERCODE_V1_1::P1_CAUSAL_FAILURE_LOCALIZATION_DIRECT_PROOF",
    "T0/CURSORBENCH_4_0::P1_CAUSAL_FAILURE_LOCALIZATION_DIRECT_PROOF",
    "T2/RECOVERY_SCOPE_COMPOSITION::P1_CAUSAL_FAILURE_LOCALIZATION_DIRECT_PROOF",
}

def _load(rel:str)->dict[str,Any]:
    v=json.loads((ROOT/rel).read_text(encoding="utf-8"))
    if not isinstance(v,dict):
        raise ValueError(rel+":NOT_OBJECT")
    return v

def _blob(rel:str)->str:
    data=(ROOT/rel).read_bytes()
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()

def evaluate(
    *,
    binding:Mapping[str,Any]|None=None,
    activation:Mapping[str,Any]|None=None,
    relations:Mapping[str,Any]|None=None,
)->dict[str,Any]:
    b=dict(binding or _load(BINDING))
    a=dict(activation or _load(V5_ACTIVATION))
    r=dict(relations or _load(RELATIONS))
    errors:list[str]=[]

    surfaces=set(b.get("direct_surface_bindings") or [])
    if surfaces!=EXPECTED_SURFACES:
        errors.append("FROZEN_DIRECT_SURFACE_SET_DRIFT")

    terminal=b.get("terminal_acceptance") or {}
    if terminal.get("standalone_synthetic_whole_domain_score_forbidden") is not True:
        errors.append("SYNTHETIC_SCORE_FIREWALL_MISSING")
    if terminal.get("parent_or_direct_surface_credit_only_for_declared_scope") is not True:
        errors.append("DECLARED_SCOPE_CREDIT_FIREWALL_MISSING")
    if "DIRECT_P1_INTERVENTION_RESCUE_INSTRUMENTATION_MUST_PASS" not in str(terminal.get("proof_rule") or ""):
        errors.append("FROZEN_DIRECT_INTERVENTION_RULE_MISSING")

    if not str(a.get("status") or "").startswith("ACTIVE_INDEPENDENT_PUBLIC_RUNNER_PASS__"):
        errors.append("V5_NOT_ACTIVE_INDEPENDENT_PREWAVE_AUTHORITY")
    vpath=a.get("verification_path")
    vsha=a.get("verification_git_blob_sha")
    if not isinstance(vpath,str) or not isinstance(vsha,str):
        errors.append("V5_VERIFICATION_PIN_MISSING")
    else:
        try:
            if _blob(vpath)!=vsha:
                errors.append("V5_VERIFICATION_PIN_DRIFT")
        except Exception:
            errors.append("V5_VERIFICATION_UNREADABLE")

    rows=r.get("relations")
    if not isinstance(rows,list):
        errors.append("RELATION_TABLE_INVALID")
        rows=[]
    seen=[x.get("direct_surface") for x in rows if isinstance(x,Mapping)]
    if set(seen)!=EXPECTED_SURFACES or len(seen)!=3 or len(set(seen))!=3:
        errors.append("RELATION_SURFACE_SET_DRIFT")

    if errors:
        return {
            "schema":SCHEMA,
            "status":"FAIL_CLOSED__SOURCE_OR_RELATION_DRIFT",
            "errors":sorted(set(errors)),
            "scope_transport_admissible":False,
            "p1_scope_quarantine_clearable":False,
            "execution_authority":False,
            "promotion_authority":False,
            "capability_credit_delta":0,
            "family_credit_delta":0,
            "new_reality_units_consumed":0,
        }

    detail=[]
    for row in rows:
        surface=str(row["direct_surface"])
        relation=str(row.get("relation") or "OPEN")
        witness=row.get("claim_bound_scope_witness")
        verification=row.get("independent_verification")
        relation_ok=relation in {"EXACT","SUPERSET"}
        witness_ok=isinstance(witness,Mapping) and bool(witness.get("path")) and bool(witness.get("claim_id"))
        verification_ok=(
            isinstance(verification,Mapping)
            and str(verification.get("status") or "").startswith("INDEPENDENT_PASS")
            and bool(verification.get("path"))
        )
        admissible=relation_ok and witness_ok and verification_ok
        detail.append({
            "direct_surface":surface,
            "relation":relation,
            "relation_admissible":admissible,
            "missing":[
                name for name,ok in (
                    ("EXACT_OR_SUPERSET_RELATION",relation_ok),
                    ("CLAIM_BOUND_SCOPE_WITNESS",witness_ok),
                    ("INDEPENDENT_RELATION_VERIFICATION",verification_ok),
                ) if not ok
            ],
        })

    admissible=all(x["relation_admissible"] for x in detail) and len(detail)==3
    return {
        "schema":SCHEMA,
        "status":(
            "PASS__ALL_THREE_V5_SCOPE_RELATIONS_ADMISSIBLE__COMPOSITE_RESTORATION_STILL_REQUIRED"
            if admissible
            else "PASS__V5_VERIFIED_BUT_TERMINAL_SCOPE_TRANSPORT_INCOMPLETE"
        ),
        "errors":[],
        "verified_v5_preflight_active":True,
        "surface_relations":detail,
        "open_surface_count":sum(not x["relation_admissible"] for x in detail),
        "scope_transport_admissible":admissible,
        "p1_scope_quarantine_clearable":False,
        "remaining_after_scope_transport":(
            ["P1_COMPOSITE_RESTORATION_INDEPENDENT_RECONCILIATION"]
            if admissible else
            ["P1_V5_SCOPE_RELATION:"+x["direct_surface"] for x in detail if not x["relation_admissible"]]
        ),
        "next":(
            "RECONCILE_P1_COMPOSITE_RESTORATION_AGAINST_VERIFIED_V5"
            if admissible else
            "PROVE_OR_FALSIFY_CLAIM_BOUND_EXACT_OR_SUPERSET_RELATION_FOR_EACH_OPEN_DIRECT_SURFACE"
        ),
        "terminal_results_replayed":0,
        "new_reality_units_consumed":0,
        "incremental_spend_usd":0,
        "capability_credit_delta":0,
        "family_credit_delta":0,
        "execution_authority":False,
        "promotion_authority":False,
    }

if __name__=="__main__":
    print(json.dumps(evaluate(),indent=2,sort_keys=True))
