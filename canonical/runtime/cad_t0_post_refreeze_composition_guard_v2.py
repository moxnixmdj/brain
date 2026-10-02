"""Fail-closed composition guard for CAD T0 post-refreeze prewave admission V2.

This guard composes already-independent component receipts. It does not execute
terminal CAD cases, inspect hidden terminal content, or grant capability/family
credit. A pass means only that the clean candidate freeze, post-beacon population,
evaluator oracle/scorer, and positioned OCR bridge are cryptographically and
semantically bound well enough to enter the existing promotion law.
"""
from __future__ import annotations
import hashlib, json
from pathlib import Path
from typing import Any, Mapping

SCHEMA="PROJECT_BRAIN_CAD_T0_POST_REFREEZE_COMPOSITION_GUARD_V2"
BEHAVIOR="CAD_DRAWING_TO_GLOBAL_SOLID_TOPOLOGY_AND_ENVELOPE_001"
FREEZE="canonical/governance/CAD_T0_CANDIDATE_FREEZE_V2.json"
BINDING="canonical/governance/CAD_T0_POST_REFREEZE_BINDING_V2.json"
OCR_RECEIPT="canonical/verification/M1A_POSITIONED_OCR_TSV_BRIDGE_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json"
POP_RECEIPT="canonical/verification/CAD_T0_POPULATION_ORACLE_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json"

def _read(root:Path,rel:str)->dict[str,Any]:
    obj=json.loads((root/rel).read_text(encoding="utf-8"))
    if not isinstance(obj,dict):
        raise ValueError(rel+":NOT_OBJECT")
    return obj

def _git_blob_sha(path:Path)->str:
    raw=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(raw)).encode("ascii")+b"\0"+raw).hexdigest()

def _pass_receipt(receipt:Mapping[str,Any], behavior:str)->bool:
    return (
        receipt.get("behavior_id")==behavior
        and str(receipt.get("status","")).startswith("INDEPENDENT_PUBLIC_RUNNER_PASS")
        and receipt.get("workflow_conclusion")=="success"
        and receipt.get("terminal_results_observed")==0
        and receipt.get("fresh_terminal_evidence_consumed")==0
    )

def evaluate(root:Path)->dict[str,Any]:
    errors:list[str]=[]
    try:
        freeze=_read(root,FREEZE)
        binding=_read(root,BINDING)
        ocr=_read(root,OCR_RECEIPT)
        pop=_read(root,POP_RECEIPT)
    except Exception as exc:
        return {
            "schema":SCHEMA,"status":"FAIL_CLOSED","pass":False,
            "errors":["INPUT_READ_FAILURE:"+type(exc).__name__],
            "prewave_route_ready_for_promotion_law":False,
            "execution_authority":False,"promotion_authority":False,
            "capability_credit_delta":0,"family_credit_delta":0,
        }

    if any(x.get("behavior_id")!=BEHAVIOR for x in (freeze,binding,ocr,pop)):
        errors.append("BEHAVIOR_ID_MISMATCH")

    if binding.get("candidate_freeze",{}).get("path")!=FREEZE:
        errors.append("FREEZE_PATH_MISMATCH")
    if binding.get("candidate_freeze",{}).get("blob_sha")!=_git_blob_sha(root/FREEZE):
        errors.append("FREEZE_BLOB_MISMATCH")

    if freeze.get("terminal_results_observed")!=0 or freeze.get("fresh_terminal_evidence_consumed")!=0:
        errors.append("FREEZE_ALREADY_CONSUMED_TERMINAL_EVIDENCE")
    contam=freeze.get("contamination_state")
    if not isinstance(contam,Mapping):
        errors.append("FREEZE_CONTAMINATION_STATE_INVALID")
        contam={}
    for k,v in {
        "prior_spent_task_reuse_for_promotion":False,
        "fresh_generated_population_selected":False,
        "post_freeze_beacon_known":False,
        "terminal_results_observed":0,
        "fresh_terminal_evidence_consumed":0,
    }.items():
        if contam.get(k)!=v:
            errors.append("FREEZE_CONTAMINATION_INVALID:"+k)

    cone=freeze.get("exact_cad_dependency_cone")
    if not isinstance(cone,Mapping):
        errors.append("FREEZE_DEPENDENCY_CONE_INVALID")
        cone={}

    population=binding.get("population")
    if not isinstance(population,Mapping):
        errors.append("POPULATION_BINDING_INVALID")
        population={}
    if population.get("slot_count")!=128:
        errors.append("POPULATION_SLOT_COUNT_INVALID")
    if population.get("selector")!="GLOBAL_TERMINAL_REPLACEMENT_POPULATION_PROTOCOL_V2_POST_FREEZE_BEACON_RULE":
        errors.append("POPULATION_SELECTOR_INVALID")
    for key in ("post_freeze_beacon_known","case_replacement","adaptive_selection","tuning_replay","external_spent_task_used_for_promotion"):
        if population.get(key) is not False:
            errors.append("POPULATION_FAIL_CLOSED_FLAG_INVALID:"+key)
    if population.get("independent_verification")!=POP_RECEIPT:
        errors.append("POPULATION_RECEIPT_PATH_MISMATCH")
    if population.get("independent_verification_blob_sha")!=_git_blob_sha(root/POP_RECEIPT):
        errors.append("POPULATION_RECEIPT_BLOB_MISMATCH")

    evaluator=binding.get("evaluator")
    if not isinstance(evaluator,Mapping):
        errors.append("EVALUATOR_BINDING_INVALID")
        evaluator={}
    if evaluator.get("hidden_reference_candidate_visible") is not False:
        errors.append("HIDDEN_REFERENCE_VISIBLE")
    if evaluator.get("candidate_self_reported_metrics_authoritative") is not False:
        errors.append("CANDIDATE_SELF_METRICS_AUTHORITY")
    for key,path_key,receipt_key in (
        ("generator_blob_sha","canonical/runtime/cad_t0_geometry_population.py","canonical/runtime/cad_t0_geometry_population.py"),
        ("oracle_adapter_blob_sha","canonical/runtime/cad_t0_oracle_adapter.py","canonical/runtime/cad_t0_oracle_adapter.py"),
        ("scorer_blob_sha","canonical/runtime/cad_t0_multiplex_scorer.py","canonical/runtime/cad_t0_multiplex_scorer.py"),
    ):
        declared = population.get(key) if key=="generator_blob_sha" else evaluator.get(key)
        if declared!=cone.get(path_key):
            errors.append("FREEZE_BINDING_HASH_MISMATCH:"+path_key)
        exact=pop.get("exact_brain_blobs")
        if not isinstance(exact,Mapping) or declared!=exact.get(receipt_key):
            errors.append("POP_RECEIPT_HASH_MISMATCH:"+path_key)

    ocr_binding=binding.get("ocr_bridge")
    if not isinstance(ocr_binding,Mapping):
        errors.append("OCR_BINDING_INVALID")
        ocr_binding={}
    ocr_runtime="canonical/runtime/bound_capabilities/image_ocr_tesseract_positioned.py"
    if ocr_binding.get("independent_verification")!=OCR_RECEIPT:
        errors.append("OCR_RECEIPT_PATH_MISMATCH")
    if ocr_binding.get("verification_blob_sha")!=_git_blob_sha(root/OCR_RECEIPT):
        errors.append("OCR_RECEIPT_BLOB_MISMATCH")
    if ocr_binding.get("runtime")!=ocr_runtime:
        errors.append("OCR_RUNTIME_PATH_MISMATCH")
    if ocr_binding.get("runtime_blob_sha")!=cone.get(ocr_runtime):
        errors.append("OCR_FREEZE_HASH_MISMATCH")
    ocr_exact=ocr.get("exact_brain_blobs")
    if not isinstance(ocr_exact,Mapping) or ocr_binding.get("runtime_blob_sha")!=ocr_exact.get(ocr_runtime):
        errors.append("OCR_RECEIPT_RUNTIME_HASH_MISMATCH")

    if not _pass_receipt(ocr,BEHAVIOR):
        errors.append("OCR_RECEIPT_NOT_INDEPENDENT_PASS")
    if not _pass_receipt(pop,BEHAVIOR):
        errors.append("POPULATION_RECEIPT_NOT_INDEPENDENT_PASS")

    policy=binding.get("fresh_evidence_policy")
    if not isinstance(policy,Mapping):
        errors.append("FRESH_EVIDENCE_POLICY_INVALID")
        policy={}
    if policy.get("spent_external_task_role")!="NONPROMOTION_DIAGNOSTIC_ONLY":
        errors.append("SPENT_TASK_PROMOTION_LEAK")
    if "POST_FREEZE_BEACON" not in str(policy.get("fresh_geometry_population_role","")):
        errors.append("FRESH_POPULATION_BEACON_RULE_MISSING")

    if binding.get("terminal_results_observed")!=0 or binding.get("fresh_terminal_evidence_consumed")!=0:
        errors.append("BINDING_ALREADY_CONSUMED_TERMINAL_EVIDENCE")
    if binding.get("execution_authority") is not False or binding.get("promotion_authority") is not False:
        errors.append("PREMATURE_AUTHORITY")

    passed=not errors
    return {
        "schema":SCHEMA,
        "status":"PASS__POST_REFREEZE_COMPONENTS_COMPOSED_FOR_PREWAVE_PROMOTION_LAW" if passed else "FAIL_CLOSED",
        "pass":passed,
        "behavior_id":BEHAVIOR,
        "prewave_route_ready_for_promotion_law":passed,
        "terminal_results_observed":0,
        "fresh_terminal_evidence_consumed":0,
        "execution_authority":False,
        "promotion_authority":False,
        "capability_credit_delta":0,
        "family_credit_delta":0,
        "errors":sorted(set(errors)),
        "rule":"COMPOSITION_ONLY__NO_TERMINAL_CASE_EXECUTION__NO_WHOLE_OPEN_DOMAIN_CAD_CLAIM__NO_CAPABILITY_CREDIT",
    }

if __name__=="__main__":
    import argparse
    ap=argparse.ArgumentParser(); ap.add_argument("repo_root",type=Path); a=ap.parse_args()
    out=evaluate(a.repo_root)
    print(json.dumps(out,indent=2,sort_keys=True))
    raise SystemExit(0 if out["pass"] else 1)
