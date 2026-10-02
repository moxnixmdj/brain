"""Exact-blob prewave guard for the post-OCR CAD T0 V2 refreeze."""
from __future__ import annotations
import argparse,hashlib,json
from pathlib import Path
from typing import Any

SCHEMA="PROJECT_BRAIN_CAD_T0_POST_REFREEZE_GUARD_V2"
FREEZE="canonical/governance/CAD_T0_CANDIDATE_FREEZE_V2.json"
BINDING="canonical/governance/CAD_T0_POST_REFREEZE_BINDING_V2.json"
OCR_VERIFY="canonical/verification/M1A_POSITIONED_OCR_TSV_BRIDGE_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json"
POP_VERIFY="canonical/verification/CAD_T0_POPULATION_ORACLE_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json"

def _load(root:Path,rel:str)->dict[str,Any]:
    x=json.loads((root/rel).read_text(encoding="utf-8"))
    if not isinstance(x,dict): raise ValueError(rel+":NOT_OBJECT")
    return x

def _git_blob_sha(path:Path)->str:
    b=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

def evaluate(root:Path)->dict[str,Any]:
    errors=[]
    try:
        freeze=_load(root,FREEZE); binding=_load(root,BINDING); ocr=_load(root,OCR_VERIFY); pop_verify=_load(root,POP_VERIFY)
    except Exception as exc:
        return {"schema":SCHEMA,"status":"FAIL_CLOSED","pass":False,"errors":[str(exc)],
                "execution_authority":False,"promotion_authority":False}

    if freeze.get("behavior_id")!="CAD_DRAWING_TO_GLOBAL_SOLID_TOPOLOGY_AND_ENVELOPE_001":
        errors.append("FREEZE_BEHAVIOR_ID")
    if binding.get("behavior_id")!=freeze.get("behavior_id"):
        errors.append("BINDING_BEHAVIOR_ID")

    cone=freeze.get("exact_cad_dependency_cone")
    if not isinstance(cone,dict) or not cone:
        errors.append("DEPENDENCY_CONE_INVALID")
    else:
        for rel,expected in sorted(cone.items()):
            if not isinstance(rel,str) or not isinstance(expected,str) or len(expected)!=40:
                errors.append("DEPENDENCY_ENTRY_INVALID:"+str(rel)); continue
            p=root/rel
            if not p.is_file():
                errors.append("DEPENDENCY_FILE_MISSING:"+rel); continue
            got=_git_blob_sha(p)
            if got!=expected:
                errors.append("DEPENDENCY_BLOB_MISMATCH:"+rel+":"+got)

    freeze_ref=binding.get("candidate_freeze")
    if not isinstance(freeze_ref,dict):
        errors.append("CANDIDATE_FREEZE_REF_MISSING")
    else:
        if freeze_ref.get("path")!=FREEZE:
            errors.append("CANDIDATE_FREEZE_PATH")
        if freeze_ref.get("blob_sha")!=_git_blob_sha(root/FREEZE):
            errors.append("CANDIDATE_FREEZE_BLOB_MISMATCH")

    contam=freeze.get("contamination_state")
    if not isinstance(contam,dict):
        errors.append("CONTAMINATION_STATE_MISSING")
    else:
        if contam.get("prior_freecad_platform_drawing")!="SPENT_NONPROMOTION_DIAGNOSTIC_ONLY_AFTER_RUNTIME_CHANGE":
            errors.append("SPENT_TASK_DISPOSITION_INVALID")
        if contam.get("prior_spent_task_reuse_for_promotion") is not False:
            errors.append("SPENT_TASK_REUSE_NOT_FALSE")
        if contam.get("post_freeze_beacon_known") is not False:
            errors.append("BEACON_ALREADY_KNOWN_AT_FREEZE")

    pop=binding.get("population")
    if not isinstance(pop,dict):
        errors.append("POPULATION_BINDING_MISSING")
    else:
        if pop.get("generator")!="canonical/runtime/cad_t0_geometry_population.py":
            errors.append("POPULATION_GENERATOR_PATH")
        if pop.get("generator_blob_sha")!="64ca276410e2c1dbcd55cfad057e3eec0709790a":
            errors.append("POPULATION_GENERATOR_BLOB")
        if pop.get("slot_count")!=128:
            errors.append("POPULATION_SLOT_COUNT")
        if pop.get("post_freeze_beacon_known") is not False:
            errors.append("POPULATION_BEACON_PREKNOWN")
        for k in ("case_replacement","adaptive_selection","tuning_replay","external_spent_task_used_for_promotion"):
            if pop.get(k) is not False:
                errors.append("POPULATION_POLICY_NOT_FALSE:"+k)

    ev=binding.get("evaluator")
    if not isinstance(ev,dict):
        errors.append("EVALUATOR_BINDING_MISSING")
    else:
        if ev.get("oracle_adapter_blob_sha")!="a6e76e1865b9bd9829dbbcf38886486636f76e8a":
            errors.append("ORACLE_ADAPTER_BLOB")
        if ev.get("scorer_blob_sha")!="89833581dc4ac67498753feb94e2ff69bad3b7f1":
            errors.append("SCORER_BLOB")
        if ev.get("hidden_reference_candidate_visible") is not False:
            errors.append("HIDDEN_REFERENCE_VISIBLE")
        if ev.get("candidate_self_reported_metrics_authoritative") is not False:
            errors.append("CANDIDATE_METRICS_AUTHORITY")

    bridge=binding.get("ocr_bridge")
    if not isinstance(bridge,dict):
        errors.append("OCR_BRIDGE_BINDING_MISSING")
    else:
        if bridge.get("runtime_blob_sha")!="19f3087489ce7f6f935fc7baaebdc8cd672f4b62":
            errors.append("OCR_BRIDGE_RUNTIME_BLOB")
        if bridge.get("verification_blob_sha")!=_git_blob_sha(root/OCR_VERIFY):
            errors.append("OCR_VERIFICATION_BLOB_MISMATCH")

    if not str(ocr.get("status","")).startswith("INDEPENDENT_PUBLIC_RUNNER_PASS"):
        errors.append("OCR_INDEPENDENT_VERIFICATION_NOT_PASS")
    if ocr.get("terminal_results_observed")!=0 or ocr.get("fresh_terminal_evidence_consumed")!=0:
        errors.append("OCR_RECEIPT_TERMINAL_EVIDENCE_NONZERO")

    for obj,name in ((freeze,"FREEZE"),(binding,"BINDING")):
        if obj.get("terminal_results_observed")!=0:
            errors.append(name+"_TERMINAL_RESULTS_NONZERO")
        if obj.get("fresh_terminal_evidence_consumed")!=0:
            errors.append(name+"_FRESH_EVIDENCE_NONZERO")
        if obj.get("execution_authority") is not False:
            errors.append(name+"_EXECUTION_AUTHORITY_NOT_FALSE")

    return {
      "schema":SCHEMA,
      "status":"PASS__CLEAN_POST_OCR_CAD_PREWAVE_BINDING_EXACT" if not errors else "FAIL_CLOSED",
      "pass":not errors,
      "errors":sorted(set(errors)),
      "execution_authority":False,
      "promotion_authority":False,
      "terminal_results_observed":0,
      "fresh_terminal_evidence_consumed":0,
      "capability_credit_delta":0,
      "family_credit_delta":0,
      "rule":"EXACT_DEPENDENCY_CONE_AND_INFORMATION_BOUNDARY_ONLY__NO_TERMINAL_CREDIT",
    }

def main()->int:
    ap=argparse.ArgumentParser();ap.add_argument("repo_root",type=Path);args=ap.parse_args()
    out=evaluate(args.repo_root);print(json.dumps(out,indent=2,sort_keys=True));return 0 if out["pass"] else 1
if __name__=="__main__": raise SystemExit(main())
