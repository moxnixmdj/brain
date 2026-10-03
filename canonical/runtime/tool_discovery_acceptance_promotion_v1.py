"""Fail-closed verifier for the Tool Discovery 5/19 acceptance promotion."""
from __future__ import annotations
import hashlib, json
from pathlib import Path
from typing import Any

ROOT=Path(__file__).resolve().parents[2]
SCHEMA="PROJECT_BRAIN_TOOL_DISCOVERY_ACCEPTANCE_PROMOTION_VERIFIER_V1"
TARGET="TOOL_LEARNING_SUCCESS_ROUTE_NONINFERIOR"
FAMILY="TOOL_DISCOVERY_SELECTION_AND_LEARNING"
PROMO="canonical/governance/TOOL_DISCOVERY_ACCEPTANCE_PROMOTION_V1.json"
EVIDENCE="canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json"
CLOSURE="canonical/governance/TERMINAL_CLOSURE_MANIFEST_V1.json"
OWNERSHIP="canonical/capabilities/opus55/OPUS_5_5_CAPABILITY_OWNERSHIP_MATRIX_V1.json"
AUTHORITY="canonical/governance/CURRENT_TERMINAL_AUTHORITY_V1.json"
RECEIPT="canonical/verification/TOOL_DISCOVERY_ACCEPTANCE_REDUCTION_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json"
SCOPE="canonical/verification/TOOL_DISCOVERY_UNIVERSAL_SCOPE_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json"

def blob(path:str)->str:
    raw=(ROOT/path).read_bytes()
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

def load(path:str)->dict[str,Any]:
    x=json.loads((ROOT/path).read_text(encoding="utf-8"))
    if not isinstance(x,dict): raise ValueError(path+":NOT_OBJECT")
    return x

def evaluate()->dict[str,Any]:
    p=load(PROMO); e=load(EVIDENCE); c=load(CLOSURE); o=load(OWNERSHIP); a=load(AUTHORITY)
    r=load(RECEIPT); s=load(SCOPE)
    errors=[]
    def req(cond:bool,code:str):
        if not cond: errors.append(code)

    for path,want in p["exact_promoted_state_blobs"].items():
        req(blob(path)==want,"PROMOTED_BLOB_DRIFT:"+path)
    req(blob(RECEIPT)==p["independently_verified_basis"]["acceptance_reduction_blob"],"ACCEPTANCE_RECEIPT_DRIFT")
    req(blob(SCOPE)==p["independently_verified_basis"]["universal_scope_blob"],"SCOPE_RECEIPT_DRIFT")

    rr=r.get("independent_runner") or {}; rv=r.get("verified") or {}
    req(rr.get("conclusion")=="success","ACCEPTANCE_REDUCTION_NOT_INDEPENDENT_PASS")
    req(rv.get("target_predicate")==TARGET,"TARGET_MISMATCH")
    req(rv.get("candidate_target_state")=="PROVED","TARGET_NOT_VERIFIED_PROVED")
    req(rv.get("scope_complete") is True,"SCOPE_NOT_COMPLETE")
    req(rv.get("objective_ceiling") is True,"OBJECTIVE_CEILING_NOT_PROVED")
    req(rv.get("uses_empirical_generalization") is False,"EMPIRICAL_GENERALIZATION_REINTRODUCED")
    req(rv.get("source_180_of_180_load_bearing") is False,"FINITE_SAMPLE_LOAD_BEARING")
    req(rv.get("tool_discovery_family_candidate_state")=="PASS_3_OF_3","FAMILY_NOT_3_OF_3")

    sr=s.get("independent_runner") or {}; sv=s.get("verified") or {}
    req(sr.get("conclusion")=="success","UNIVERSAL_SCOPE_NOT_INDEPENDENT_PASS")
    req(sv.get("universal_scope_proved") is True,"UNIVERSAL_SCOPE_NOT_PROVED")
    req(sv.get("basis_kind")=="UNIVERSAL_FORMAL_SCOPE_PROOF","UNIVERSAL_SCOPE_BASIS_WRONG")

    claims={x.get("predicate_id"):x for x in e.get("claims",[]) if isinstance(x,dict)}
    t=claims.get(TARGET) or {}
    req(t.get("state")=="PROVED","LIVE_TARGET_NOT_PROVED")
    req(t.get("proof_kind")=="ABSOLUTE_CEILING_WITH_UNIVERSAL_FORMAL_SCOPE_COMPLETENESS","LIVE_PROOF_KIND")
    req(t.get("scope_complete") is True and t.get("objective_ceiling") is True,"LIVE_TARGET_BOUND_INCOMPLETE")
    sat=e.get("saturation") or {}
    req(sat.get("proved_predicate_count")==12,"LIVE_PROVED_COUNT")
    req(sat.get("unresolved_predicate_count")==26,"LIVE_UNRESOLVED_COUNT")
    req(sat.get("bound_blocker_count")==3,"LIVE_BOUND_BLOCKER_COUNT")

    fam=next((x for x in c.get("families",[]) if x.get("id")==FAMILY),{})
    req(fam.get("opus55_acceptance_state")=="PASS","CLOSURE_FAMILY_NOT_PASS")
    req(fam.get("opus55_acceptance_calibrated") is True,"CLOSURE_FAMILY_NOT_CALIBRATED")
    req(fam.get("unresolved")==[],"CLOSURE_FAMILY_STILL_UNRESOLVED")
    cs=c.get("opus55_acceptance_summary") or {}
    req(cs.get("calibrated_family_count")==5 and cs.get("pending_family_count")==14,"CLOSURE_FAMILY_COUNTS")
    req((cs.get("atomic_predicates") or {}).get("proved")==12,"CLOSURE_ATOMIC_PROVED")
    req((cs.get("atomic_predicates") or {}).get("unresolved")==26,"CLOSURE_ATOMIC_UNRESOLVED")
    req(FAMILY in set(cs.get("calibrated_families") or []),"CLOSURE_TOOL_FAMILY_MISSING")
    req(FAMILY not in set(cs.get("pending_families") or []),"CLOSURE_TOOL_FAMILY_STILL_PENDING")

    row=next((x for x in o.get("rows",[]) if x.get("family")==FAMILY),{})
    req(row.get("status")=="OWNED_COMPONENT_NOT_FULL_FAMILY","OWNERSHIP_OVERPROMOTED_ROW")
    os=o.get("postwave_acceptance_summary") or {}
    req(os.get("calibrated_family_count")==5 and os.get("pending_acceptance_family_count")==14,"OWNERSHIP_ACCEPTANCE_COUNTS")
    req(os.get("verified_owned_family_count")==2,"STRICT_OWNERSHIP_COUNT_CHANGED")
    req(FAMILY in set(o.get("summary",{}).get("owned_components_not_full_family") or []),"TOOL_DISCOVERY_NO_LONGER_COMPONENT_ONLY")
    req(FAMILY not in set(o.get("summary",{}).get("verified_owned_equal_or_better_capabilities") or []),"TOOL_DISCOVERY_OWNERSHIP_OVERCLAIM")

    truth=a.get("truth") or {}; af=a.get("atomic_acceptance_frontier") or {}
    req(truth.get("opus55_acceptance")=="5/19_PASS__14/19_OPEN","AUTHORITY_FAMILY_COUNTS")
    req(af.get("proved")==12 and af.get("unresolved")==26 and af.get("total")==38,"AUTHORITY_ATOMIC_COUNTS")
    req(truth.get("achieved") is False,"TERMINAL_FALSE_NOT_PRESERVED")

    ok=not errors
    return {
      "schema":SCHEMA,
      "status":"PASS__EXACT_TOOL_DISCOVERY_ACCEPTANCE_PROMOTION__5_OF_19__12_OF_38__OWNERSHIP_STILL_2_OF_19" if ok else "FAIL_CLOSED",
      "pass":ok,"errors":sorted(set(errors)),
      "before":{"proved_atomic":11,"unresolved_atomic":27,"accepted_families":4,"open_families":15,"verified_owned_families":2},
      "after":{"proved_atomic":12 if ok else 11,"unresolved_atomic":26 if ok else 27,"accepted_families":5 if ok else 4,"open_families":14 if ok else 15,"verified_owned_families":2},
      "newly_proved_predicates":[TARGET] if ok else [],
      "newly_closed_families":[FAMILY] if ok else [],
      "ownership_promotions":[],
      "new_reality_units_consumed":0,"terminal_results_replayed":0,"incremental_spend_usd":0,
      "execution_authority":False,"promotion_authority":False,"fresh_reality_authority":False
    }

if __name__=="__main__":
    print(json.dumps(evaluate(),indent=2,sort_keys=True))
