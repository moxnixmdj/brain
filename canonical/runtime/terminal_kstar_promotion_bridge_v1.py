#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path
from typing import Any

RESULT_SCHEMA="PROJECT_BRAIN_TERMINAL_KSTAR_RESULT_V1"
VERIFY_SCHEMA="PROJECT_BRAIN_TERMINAL_KSTAR_INDEPENDENT_VERIFICATION_V1"
ALLOWED={"FULL_SCOPE_DB_COVER","TARGET_ESCAPE_NONOCCUPANCY","GENERATOR_CLOSURE_SCOPE_COMPLETE","SELECTED_COVER_COMPLEMENT_UNSAT"}
SEM=("observable_trace_scope_complete","all_useful_target_behaviors_in_scope","every_admission_sound","residual_complement_unsat","selected_cover_complete","u_empty","abc_closed","all_credited_routes_brain_owned","basis_complete","transforms_adequacy_preserving","universal_policy_total")
REDUCER_SEM=("observable_trace_scope_complete","all_useful_target_behaviors_in_scope","every_admission_sound","residual_complement_unsat","selected_cover_complete","u_empty","abc_closed","all_credited_routes_brain_owned")
COMMON=("exact_target_family_count_19","every_required_behavior_contracted","every_required_behavior_has_admissible_proof","donor_dependent_required_behaviors_zero","unexplained_required_behaviors_zero","unresolved_verifier_mutations_zero","unresolved_composition_failures_zero","contaminated_evidence_used_for_promotion_zero","resource_or_authority_violations_zero","final_donor_deletion_cleanroom_pass")
ZERO=("uncontracted_required_behaviors","unproved_required_behaviors","donor_dependent_required_behaviors","unresolved_verifier_mutations","unresolved_composition_failures","contaminated_promotion_evidence","resource_or_authority_violations")
GLOBAL_OWNERSHIP_REDUCER="canonical/runtime/terminal_global_ownership_postconditions_reducer_v1.py"
GLOBAL_OWNERSHIP_REQUIRED_PREDICATES=("final_donor_deletion_cleanroom_pass","donor_deletion_protocol_v2_bound","runtime_cognition_model_independent","zero_external_model_runtime_cognition_dependencies","copied_or_rehosted_teacher_absent","runtime_dependency_inventory_complete")
REQ={"canonical/governance/CURRENT_TERMINAL_AUTHORITY.json","canonical/governance/TERMINAL_ARCHITECTURE_SELF_TOURNAMENT_20261007_V1.json","canonical/governance/CURRENT_PRIMITIVE_U_FRONTIER_20261007_V1.json","canonical/governance/SELECTED_DISCRIMINATOR_POLICY_COVER_BRIDGE_20261007_V1.json","canonical/runtime/terminal_closure_reducer.py",GLOBAL_OWNERSHIP_REDUCER}
RESULT="canonical/astra_runtime/artifacts/TERMINAL_KSTAR_RESULT_20261007_V1.json"
INDEP="canonical/verification/TERMINAL_KSTAR_INDEPENDENT_VERIFICATION_20261007_V1.json"
MANIFEST="canonical/governance/TERMINAL_CLOSURE_MANIFEST_V1.json"
PROOF="canonical/governance/TERMINAL_KSTAR_UNIVERSAL_PROOF_20261007_V1.json"
VREC="canonical/verification/TERMINAL_KSTAR_UNIVERSAL_VERIFIER_RECEIPT_20261007_V1.json"
BUNDLE="canonical/governance/TERMINAL_KSTAR_FROZEN_PROOF_BUNDLE_20261007_V1.json"
RECEIPT="canonical/verification/TERMINAL_KSTAR_PROMOTION_BRIDGE_RECEIPT_20261007_V1.json"

def s256(raw:bytes)->str: return hashlib.sha256(raw).hexdigest()
def gblob(raw:bytes)->str: return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\\0"+raw).hexdigest()
def load(p:Path)->dict[str,Any]:
    x=json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(x,dict): raise ValueError("JSON_OBJECT_REQUIRED")
    return x
def write(p:Path,x:dict[str,Any])->bytes:
    raw=(json.dumps(x,indent=2,sort_keys=True)+"\\n").encode()
    p.parent.mkdir(parents=True,exist_ok=True); p.write_bytes(raw); return raw
def bind(root:Path,b:Any)->bool:
    if not isinstance(b,dict): return False
    rel=b.get("path"); want=b.get("git_blob_sha")
    if not isinstance(rel,str) or not isinstance(want,str) or len(want)!=40: return False
    try:
        p=(root/rel).resolve(); p.relative_to(root.resolve())
    except Exception: return False
    return p.is_file() and gblob(p.read_bytes())==want.lower()
def fail(root:Path,errs:list[str])->int:
    write(root/RECEIPT,{"schema":"PROJECT_BRAIN_TERMINAL_KSTAR_PROMOTION_BRIDGE_RECEIPT_V1","status":"FAIL_CLOSED","pass":False,"errors":sorted(set(errs)),"terminal_credit_delta":0,"terminal_claim":False})
    return 2

def promote(root:Path)->int:
    errs=[]
    rp=root/RESULT; vp=root/INDEP; mp=root/MANIFEST
    for p,label in ((rp,"KSTAR_RESULT_MISSING"),(vp,"KSTAR_INDEPENDENT_VERIFICATION_MISSING"),(mp,"TERMINAL_MANIFEST_MISSING")):
        if not p.is_file(): errs.append(label)
    if errs: return fail(root,errs)
    r=load(rp); v=load(vp); m=load(mp); rr=rp.read_bytes()
    if r.get("schema")!=RESULT_SCHEMA: errs.append("RESULT_SCHEMA_INVALID")
    if r.get("outcome")!="SCOPE_COMPLETE_PROOF" or r.get("conclusion")!="success": errs.append("RESULT_NOT_SCOPE_COMPLETE_PROOF")
    if r.get("proof_kind") not in ALLOWED: errs.append("PROOF_KIND_INVALID")
    if r.get("scope_id")!="scope://opus55/observable-trace": errs.append("SCOPE_ID_INVALID")
    if r.get("unresolved")!=[]: errs.append("RESULT_UNRESOLVED_NOT_EMPTY")
    if float(r.get("incremental_spend_usd",0))!=0.0 or r.get("terminal_credit_claim") is not False: errs.append("RESULT_AUTHORITY_VIOLATION")
    for k in SEM:
        if r.get(k) is not True: errs.append("RESULT_PREDICATE_NOT_TRUE:"+k)
    if not isinstance(r.get("generated_basis"),list) or not r["generated_basis"]: errs.append("GENERATED_BASIS_EMPTY")
    if not isinstance(r.get("transforms"),list): errs.append("TRANSFORMS_NOT_LIST")
    if not isinstance(r.get("policy"),dict) or not r["policy"]: errs.append("POLICY_MISSING")
    if not bind(root,r.get("runtime_binding")): errs.append("RUNTIME_BINDING_INVALID")
    bs=r.get("source_bindings")
    if not isinstance(bs,list) or not bs: errs.append("SOURCE_BINDINGS_MISSING"); bs=[]
    seen=set()
    for i,b in enumerate(bs):
        if not bind(root,b): errs.append("SOURCE_BINDING_INVALID:"+str(i))
        elif isinstance(b,dict): seen.add(b.get("path"))
    for rel in REQ:
        if rel not in seen: errs.append("REQUIRED_SOURCE_NOT_BOUND:"+rel)

    if v.get("schema")!=VERIFY_SCHEMA or v.get("status")!="PASS__INDEPENDENT_SCOPE_COMPLETE_KSTAR" or v.get("conclusion")!="success": errs.append("INDEPENDENT_VERIFY_NOT_PASS")
    if v.get("independent_verified") is not True or v.get("exact_byte_bound") is not True: errs.append("INDEPENDENCE_OR_BYTE_BIND_MISSING")
    if v.get("proof_sha256")!=s256(rr): errs.append("RESULT_SHA256_MISMATCH")
    if v.get("source_bindings_verified") is not True or v.get("falsification_complete") is not True: errs.append("INDEPENDENT_FALSIFICATION_INCOMPLETE")
    vv=v.get("verified_predicates")
    if not isinstance(vv,dict): vv={}; errs.append("VERIFIED_PREDICATES_MISSING")
    for k in SEM:
        if vv.get(k) is not True: errs.append("INDEPENDENT_PREDICATE_NOT_TRUE:"+k)
    if v.get("errors") not in ([],None): errs.append("INDEPENDENT_ERRORS_PRESENT")

    pr=m.get("terminal_predicates"); co=m.get("counters")
    if not isinstance(pr,dict): pr={}; errs.append("MANIFEST_PREDICATES_MISSING")
    if not isinstance(co,dict): co={}; errs.append("MANIFEST_COUNTERS_MISSING")
    for k in COMMON:
        if pr.get(k) is not True: errs.append("COMMON_FINALITY_NOT_TRUE:"+k)
    for k in ZERO:
        if co.get(k)!=0: errs.append("COMMON_COUNTER_NONZERO:"+k)

    gp=m.get("global_ownership_postconditions")
    if not isinstance(gp,dict):
        errs.append("GLOBAL_OWNERSHIP_POSTCONDITIONS_MISSING")
    else:
        evidence_path=gp.get("evidence"); evidence_sha=gp.get("evidence_blob_sha")
        evidence_binding={"path":evidence_path,"git_blob_sha":evidence_sha}
        if not bind(root,evidence_binding):
            errs.append("GLOBAL_OWNERSHIP_RECEIPT_BINDING_INVALID")
        else:
            gov=load(root/evidence_path)
            current_reducer_blob=gblob((root/GLOBAL_OWNERSHIP_REDUCER).read_bytes())
            if gov.get("brain_reducer_blob_sha")!=current_reducer_blob:
                errs.append("GLOBAL_OWNERSHIP_RECEIPT_REDUCER_BLOB_STALE")
            if "INDEPENDENT_PUBLIC_RUNNER_PASS" not in str(gov.get("status","")):
                errs.append("GLOBAL_OWNERSHIP_RECEIPT_NOT_INDEPENDENT_PASS")
            gr=gov.get("result")
            gpred=(gr.get("terminal_predicates") if isinstance(gr,dict) else None)
            if not isinstance(gpred,dict):
                errs.append("GLOBAL_OWNERSHIP_RECEIPT_PREDICATES_MISSING")
            else:
                for name in GLOBAL_OWNERSHIP_REQUIRED_PREDICATES:
                    if gpred.get(name) is not True:
                        errs.append("GLOBAL_OWNERSHIP_ZERO_MODEL_PREDICATE_NOT_TRUE:"+name)
    if errs: return fail(root,errs)

    proof={"schema":"PROJECT_BRAIN_TERMINAL_KSTAR_UNIVERSAL_PROOF_V1","proof_kind":r["proof_kind"],"scope_id":"scope://opus55/observable-trace","conclusion":"success","kstar_result":{"path":RESULT,"sha256":s256(rr)},"runtime_binding":r["runtime_binding"],"source_bindings":bs,"generated_basis":r["generated_basis"],"transforms":r["transforms"],"policy":r["policy"],"falsification":r.get("falsification",{}),"independent_semantic_verification":{"path":INDEP,"sha256":s256(vp.read_bytes())},"incremental_spend_usd":0}
    for k in REDUCER_SEM: proof[k]=True
    proof["donor_independence_closed"]=True; proof["clean_room_replay_pass"]=True
    praw=write(root/PROOF,proof); pb={"path":PROOF,"git_blob_sha":gblob(praw)}
    vr={"schema":"PROJECT_BRAIN_TERMINAL_KSTAR_UNIVERSAL_VERIFIER_RECEIPT_V1","conclusion":"success","independent_verified":True,"exact_byte_bound":True,"proof_artifact":pb,"semantic_verifier":{"path":INDEP,"sha256":s256(vp.read_bytes())},"source_result":{"path":RESULT,"sha256":s256(rr)},"rule":"INDEPENDENT_SEMANTIC_VERIFIER_PLUS_DETERMINISTIC_EXACT_BYTE_PROMOTION_BRIDGE","terminal_credit_claim":False,"incremental_spend_usd":0}
    vraw=write(root/VREC,vr); vb={"path":VREC,"git_blob_sha":gblob(vraw)}
    bun={"schema":"PROJECT_BRAIN_TERMINAL_KSTAR_FROZEN_PROOF_BUNDLE_V1","status":"FROZEN_PRE_REDUCER","universal_proof":pb,"universal_verifier":vb,"independent_semantic_verifier":{"path":INDEP,"git_blob_sha":gblob(vp.read_bytes())},"kstar_result":{"path":RESULT,"git_blob_sha":gblob(rr)},"terminal_closure_reducer":{"path":"canonical/runtime/terminal_closure_reducer.py","git_blob_sha":gblob((root/"canonical/runtime/terminal_closure_reducer.py").read_bytes())},"incremental_spend_usd":0,"terminal_credit_claim":False}
    braw=write(root/BUNDLE,bun); bb={"path":BUNDLE,"git_blob_sha":gblob(braw)}
    m["universal_cover_proof"]={"proof_artifact":pb,"verifier_receipt_artifact":vb,"proof_kind":r["proof_kind"],"scope_id":"scope://opus55/observable-trace","conclusion":"success"}
    m.setdefault("terminal_predicates",{})["proof_bundle_frozen"]=True
    m["final_proof_bundle_candidate"]=BUNDLE
    m["final_proof_bundle_state"]={"status":"KSTAR_FROZEN_PRE_REDUCER","path":BUNDLE,"git_blob_sha":bb["git_blob_sha"]}
    m["status"]="KSTAR_UNIVERSAL_PROOF_BOUND__TERMINAL_REDUCER_REQUIRED"
    write(mp,m)
    write(root/RECEIPT,{"schema":"PROJECT_BRAIN_TERMINAL_KSTAR_PROMOTION_BRIDGE_RECEIPT_V1","status":"PASS__UNIVERSAL_PROOF_BOUND__REDUCER_REQUIRED","pass":True,"errors":[],"proof_artifact":pb,"verifier_receipt_artifact":vb,"frozen_bundle":bb,"terminal_credit_delta":0,"terminal_claim":False})
    return 0

def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument("--root",type=Path,default=Path.cwd()); a=ap.parse_args()
    return promote(a.root.resolve())
if __name__=="__main__": raise SystemExit(main())
