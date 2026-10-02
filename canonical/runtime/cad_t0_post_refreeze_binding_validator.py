"""Fail-closed validator for the clean CAD T0 post-refreeze prewave binding.

Checks that the frozen candidate dependency cone still matches live Brain blobs,
the post-beacon geometry population/oracle/scorer are exactly the independently
verified implementations, the positioned OCR bridge remains independently verified,
and no spent diagnostic case is reused for promotion.
"""
from __future__ import annotations
import hashlib,json
from pathlib import Path
from typing import Any, Mapping

SCHEMA="PROJECT_BRAIN_CAD_T0_POST_REFREEZE_BINDING_VALIDATION_V1"
FREEZE="canonical/governance/CAD_T0_CANDIDATE_FREEZE_V2.json"
BINDING="canonical/governance/CAD_T0_POST_REFREEZE_BINDING_V2.json"
POP_RECEIPT="canonical/verification/CAD_T0_POPULATION_ORACLE_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json"
OCR_RECEIPT="canonical/verification/M1A_POSITIONED_OCR_TSV_BRIDGE_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json"

def _read(root:Path,rel:str)->dict[str,Any]:
    x=json.loads((root/rel).read_text(encoding="utf-8"))
    if not isinstance(x,dict): raise ValueError(rel+":NOT_OBJECT")
    return x

def _blob(path:Path)->str:
    b=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

def _matches(root:Path,rel:Any,expected:Any)->bool:
    if not isinstance(rel,str) or not rel or not isinstance(expected,str) or not expected:
        return False
    p=root/rel
    return p.exists() and _blob(p)==expected

def validate(root:Path)->dict[str,Any]:
    errors=[]
    try:
        freeze=_read(root,FREEZE); binding=_read(root,BINDING)
        pop=_read(root,POP_RECEIPT); ocr=_read(root,OCR_RECEIPT)
    except Exception as exc:
        return {"schema":SCHEMA,"status":"FAIL_CLOSED","pass":False,
                "errors":["INPUT_READ_FAILURE:"+type(exc).__name__],
                "execution_authority":False,"promotion_authority":False,
                "capability_credit_delta":0,"family_credit_delta":0}

    behavior="CAD_DRAWING_TO_GLOBAL_SOLID_TOPOLOGY_AND_ENVELOPE_001"
    if freeze.get("behavior_id")!=behavior or binding.get("behavior_id")!=behavior or pop.get("behavior_id")!=behavior:
        errors.append("BEHAVIOR_ID_MISMATCH")
    if not str(freeze.get("status","")).startswith("IMMUTABLE_CLEAN_POST_OCR_BRIDGE"):
        errors.append("CANDIDATE_FREEZE_STATUS_INVALID")
    cone=freeze.get("exact_cad_dependency_cone")
    if not isinstance(cone,Mapping) or not cone:
        errors.append("DEPENDENCY_CONE_INVALID")
    else:
        for rel,expected in cone.items():
            p=root/rel
            if not p.exists(): errors.append("DEPENDENCY_MISSING:"+rel); continue
            if _blob(p)!=expected: errors.append("DEPENDENCY_DRIFT:"+rel)

    cf=binding.get("candidate_freeze")
    if not isinstance(cf,Mapping) or cf.get("path")!=FREEZE or not _matches(root,FREEZE,cf.get("blob_sha")):
        errors.append("CANDIDATE_FREEZE_BINDING_INVALID")

    population=binding.get("population")
    evaluator=binding.get("evaluator")
    if not isinstance(population,Mapping): errors.append("POPULATION_BINDING_INVALID"); population={}
    if not isinstance(evaluator,Mapping): errors.append("EVALUATOR_BINDING_INVALID"); evaluator={}
    if population.get("post_freeze_beacon_known") is not False:
        errors.append("POST_FREEZE_BEACON_PREEXPOSED")
    for k in ("case_replacement","adaptive_selection","tuning_replay","external_spent_task_used_for_promotion"):
        if population.get(k) is not False: errors.append("POPULATION_POLICY_INVALID:"+k)
    if evaluator.get("hidden_reference_candidate_visible") is not False:
        errors.append("HIDDEN_REFERENCE_BOUNDARY_INVALID")
    if evaluator.get("candidate_self_reported_metrics_authoritative") is not False:
        errors.append("CANDIDATE_METRICS_AUTHORITY_INVALID")

    exact=pop.get("exact_brain_blobs")
    if not isinstance(exact,Mapping) or not str(pop.get("status","")).startswith("INDEPENDENT_PUBLIC_RUNNER_PASS"):
        errors.append("POPULATION_ORACLE_RECEIPT_INVALID")
        exact={}
    pairs=[
        ("generator","generator_blob_sha"),
    ]
    gen=population.get("generator"); gsha=population.get("generator_blob_sha")
    if not _matches(root,gen,gsha) or exact.get(gen)!=gsha:
        errors.append("GENERATOR_NOT_COVERED_BY_INDEPENDENT_RECEIPT")
    for path_key,sha_key in (("oracle_adapter","oracle_adapter_blob_sha"),("scorer","scorer_blob_sha")):
        rel=evaluator.get(path_key); sha=evaluator.get(sha_key)
        if not _matches(root,rel,sha) or exact.get(rel)!=sha:
            errors.append(path_key.upper()+"_NOT_COVERED_BY_INDEPENDENT_RECEIPT")

    bridge=binding.get("ocr_bridge")
    if not isinstance(bridge,Mapping): errors.append("OCR_BRIDGE_BINDING_INVALID"); bridge={}
    if bridge.get("independent_verification")!=OCR_RECEIPT:
        errors.append("OCR_RECEIPT_POINTER_INVALID")
    if not str(ocr.get("status","")).startswith("INDEPENDENT"):
        errors.append("OCR_RECEIPT_NOT_PASS")
    rel=bridge.get("runtime"); sha=bridge.get("runtime_blob_sha")
    if not _matches(root,rel,sha):
        errors.append("OCR_RUNTIME_DRIFT")

    policy=binding.get("fresh_evidence_policy")
    if not isinstance(policy,Mapping) or policy.get("spent_external_task_role")!="NONPROMOTION_DIAGNOSTIC_ONLY":
        errors.append("SPENT_TASK_POLICY_INVALID")

    if binding.get("prewave_admissible") is not False:
        errors.append("SOURCE_BINDING_SELF_PROMOTION_FORBIDDEN")
    if binding.get("independent_verification")!="PENDING_PUBLIC_RUNNER":
        errors.append("SOURCE_BINDING_VERIFICATION_STATE_INVALID")

    return {
        "schema":SCHEMA,
        "status":"CAD_T0_POST_REFREEZE_BINDING_VALID" if not errors else "FAIL_CLOSED",
        "pass":not errors,
        "behavior_id":behavior,
        "dependency_cone_count":len(cone) if isinstance(cone,Mapping) else 0,
        "terminal_results_observed":0,
        "fresh_terminal_evidence_consumed":0,
        "execution_authority":False,
        "promotion_authority":False,
        "capability_credit_delta":0,
        "family_credit_delta":0,
        "errors":sorted(set(errors)),
    }

if __name__=="__main__":
    import argparse
    ap=argparse.ArgumentParser();ap.add_argument("repo_root",type=Path);a=ap.parse_args()
    out=validate(a.repo_root);print(json.dumps(out,indent=2,sort_keys=True))
    raise SystemExit(0 if out["pass"] else 1)
