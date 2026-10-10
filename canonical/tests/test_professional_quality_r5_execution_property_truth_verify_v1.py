from __future__ import annotations
import json
from copy import deepcopy
from pathlib import Path
from canonical.runtime import professional_quality_r5_execution_property_truth_verify_v1 as v

ROOT=Path(__file__).resolve().parents[2]

def docs():
    out={}
    for key in ("manifest","catalog","scope_batch","r5_root_verify","evaluator_verify"):
        rel,_=v.PINS[key]
        out[key]=json.loads((ROOT/rel).read_text(encoding="utf-8"))
    return out

def evaluate(d):
    return v.evaluate_documents(d["manifest"],d["catalog"],d["scope_batch"],
                                d["r5_root_verify"],d["evaluator_verify"])

def test_current_exact_r5_execution_leaf_passes_only():
    out=v.verify()
    assert out["pass"] is True,out
    assert out["leaf_property_truth_authority"] is True
    assert out["whole_leaf_scope_complete"] is True
    assert out["adversarial_case_count"]==16
    assert out["near_miss_case_count"]==16
    assert out["bounded_evaluator_mechanics_pass"] is True
    assert out["detection_completeness_proved"] is False
    assert out["true_owner_evaluator_containment_proved"] is False
    assert out["reference_correctness_proved"] is False
    assert out["cross_model_calibration_proved"] is False
    assert out["real_task_comparative_evaluation_step_receipt_proved"] is False
    assert out["semantic_leaf_closed"] is False
    assert out["root_closed"] is False
    assert out["quality_authority"] is False
    assert out["terminal_authority"] is False

def test_execution_acceptance_drift_fails_closed():
    d=docs()
    row=next(x for x in d["manifest"]["roots"] if x["root_id"]==v.ROOT_ID)
    row["execution_leaf"]["acceptance"]="WEAKER_ACCEPTANCE"
    out=evaluate(d)
    assert out["pass"] is False
    assert out["reason"]=="R5_EXECUTION_ACCEPTANCE_DRIFT"

def test_catalog_attack_loss_fails_closed():
    d=docs()
    rows=d["catalog"].get("defeaters") or d["catalog"].get("attack_classes") or d["catalog"].get("nodes") or d["catalog"].get("challenges") or []
    target=next(x for x in rows if x.get("id")=="C17_REFERENCE_STANDARD_ERROR")
    target["root_ids"]=[x for x in target.get("root_ids",[]) if x!=v.ROOT_ID]
    out=evaluate(d)
    assert out["pass"] is False
    assert out["reason"]=="R5_CATALOG_NOT_EXACT"

def test_scope_batch_must_remain_24_of_24():
    d=docs()
    d["scope_batch"]["independent_replay"]["scope_complete_count"]=23
    out=evaluate(d)
    assert out["pass"] is False
    assert out["reason"]=="WHOLE_LEAF_SCOPE_BATCH_NOT_CURRENT_24_OF_24"

def test_root_binding_must_remain_admissible_without_owner_containment_claim():
    d=docs()
    d["r5_root_verify"]["root_subject_binding_authority"]=False
    out=evaluate(d)
    assert out["pass"] is False
    assert out["reason"]=="R5_ROOT_BINDING_NOT_ADMISSIBLE"
    d=docs()
    d["r5_root_verify"]["true_owner_evaluator_containment_proved"]=True
    out=evaluate(d)
    assert out["pass"] is False
    assert out["reason"]=="R5_ROOT_BINDING_NOT_ADMISSIBLE"

def test_evaluator_mechanics_receipt_cannot_lose_required_behavior():
    d=docs()
    d["evaluator_verify"]["verified_mechanics"]=[
        x for x in d["evaluator_verify"]["verified_mechanics"]
        if x!="UNPROVED_DECOMPOSITION_FAILS_CLOSED"
    ]
    out=evaluate(d)
    assert out["pass"] is False
    assert out["reason"]=="R5_EVALUATOR_MECHANICS_NOT_ADMISSIBLE"

def test_property_verifier_never_claims_owner_or_root_closure():
    out=v.verify()
    assert out["pass"] is True
    assert out["true_owner_evaluator_containment_proved"] is False
    assert out["reference_correctness_proved"] is False
    assert out["cross_model_calibration_proved"] is False
    assert out["domain_execution_closure"] is False
    assert out["domain_semantic_closure"] is False
