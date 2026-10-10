from __future__ import annotations
from copy import deepcopy
import json
from pathlib import Path
from canonical.runtime import professional_quality_r3_execution_property_truth_verify_v1 as v

ROOT=Path(__file__).resolve().parents[2]

def docs():
    out={}
    for key in ("manifest","catalog","r3_root_verify","render_verify"):
        rel,_=v.PINS[key]
        out[key]=json.loads((ROOT/rel).read_text(encoding="utf-8"))
    return out

def evaluate(d):
    return v.evaluate_documents(d["manifest"],d["catalog"],d["r3_root_verify"],d["render_verify"])

def test_current_exact_r3_execution_leaf_passes_only():
    out=v.verify()
    assert out["pass"] is True,out
    assert out["leaf_property_truth_authority"] is True
    assert out["adversarial_case_count"]==7
    assert out["near_miss_case_count"]==7
    assert out["real_task_render_receipt_pass"] is True
    assert out["detection_completeness_proved"] is False
    assert out["renderer_invariance_proved"] is False
    assert out["semantic_target_correctness_proved"] is False
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
    assert out["reason"]=="R3_EXECUTION_ACCEPTANCE_DRIFT"

def test_catalog_attack_loss_fails_closed():
    d=docs()
    rows=d["catalog"].get("defeaters") or d["catalog"].get("attack_classes") or d["catalog"].get("nodes") or d["catalog"].get("challenges") or []
    target=next(x for x in rows if x.get("id")=="C07_RENDER_CAPTURE_LOSS")
    target["root_ids"]=[x for x in target.get("root_ids",[]) if x!=v.ROOT_ID]
    out=evaluate(d)
    assert out["pass"] is False
    assert out["reason"]=="R3_CATALOG_NOT_EXACT"

def test_root_receipt_chain_must_remain_exact():
    d=docs()
    d["r3_root_verify"]["exact_blobs"]["exact_step_receipt"]="bad"
    out=evaluate(d)
    assert out["pass"] is False
    assert out["reason"]=="R3_REAL_TASK_RECEIPT_CHAIN_DRIFT"

def test_render_receipt_must_remain_independent_and_scope_verified():
    d=docs()
    d["render_verify"]["producer_verifier_distinct"]=False
    out=evaluate(d)
    assert out["pass"] is False
    assert out["reason"]=="R3_RENDER_RECEIPT_NOT_ADMISSIBLE"

def test_property_verifier_never_claims_global_realization_completeness():
    out=v.verify()
    assert out["pass"] is True
    assert out["whole_artifact_observation_completeness_proved"] is False
    assert out["renderer_invariance_proved"] is False
    assert out["semantic_target_correctness_proved"] is False
    assert out["domain_execution_closure"] is False
