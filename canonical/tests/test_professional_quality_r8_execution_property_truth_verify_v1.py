from __future__ import annotations
import json
from copy import deepcopy
from pathlib import Path
from canonical.runtime import professional_quality_r8_execution_property_truth_verify_v1 as v

ROOT=Path(__file__).resolve().parents[2]

def docs():
    out={}
    for key in ("manifest","catalog","scope_batch","r8_root_verify","population_verify"):
        rel,_=v.PINS[key]
        out[key]=json.loads((ROOT/rel).read_text(encoding="utf-8"))
    return out

def evaluate(d):
    return v.evaluate_documents(d["manifest"],d["catalog"],d["scope_batch"],
                                d["r8_root_verify"],d["population_verify"])

def test_current_exact_r8_execution_leaf_passes_only():
    out=v.verify()
    assert out["pass"] is True,out
    assert out["leaf_property_truth_authority"] is True
    assert out["whole_leaf_scope_complete"] is True
    assert out["adversarial_case_count"]==12
    assert out["near_miss_case_count"]==12
    assert out["population_preflight_pass"] is True
    assert out["detection_completeness_proved"] is False
    assert out["constituency_support_proved"] is False
    assert out["operator_generalization_proved"] is False
    assert out["measurement_invariance_proved"] is False
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
    assert out["reason"]=="R8_EXECUTION_ACCEPTANCE_DRIFT"

def test_catalog_attack_loss_fails_closed():
    d=docs()
    rows=d["catalog"].get("defeaters") or d["catalog"].get("attack_classes") or d["catalog"].get("nodes") or d["catalog"].get("challenges") or []
    target=next(x for x in rows if x.get("id")=="C32_PRESENTER_CONFOUNDING")
    target["root_ids"]=[x for x in target.get("root_ids",[]) if x!=v.ROOT_ID]
    out=evaluate(d)
    assert out["pass"] is False
    assert out["reason"]=="R8_CATALOG_NOT_EXACT"

def test_scope_batch_must_remain_24_of_24():
    d=docs()
    d["scope_batch"]["independent_replay"]["scope_complete_count"]=23
    out=evaluate(d)
    assert out["pass"] is False
    assert out["reason"]=="WHOLE_LEAF_SCOPE_BATCH_NOT_CURRENT_24_OF_24"

def test_root_binding_must_keep_conditional_population_support():
    d=docs()
    d["r8_root_verify"]["conditional_population_transport_support"]=False
    out=evaluate(d)
    assert out["pass"] is False
    assert out["reason"]=="R8_ROOT_BINDING_NOT_ADMISSIBLE"

def test_population_receipt_cannot_lose_case_class_coverage():
    d=docs()
    d["population_verify"]["verified"]=[
        x for x in d["population_verify"]["verified"]
        if x!="ALL_SIX_FROZEN_DELEGATION_CASE_CLASSES_PRESENT"
    ]
    out=evaluate(d)
    assert out["pass"] is False
    assert out["reason"]=="R8_POPULATION_PREFLIGHT_NOT_ADMISSIBLE"

def test_property_verifier_never_claims_population_generalization():
    out=v.verify()
    assert out["pass"] is True
    assert out["constituency_support_proved"] is False
    assert out["operator_generalization_proved"] is False
    assert out["measurement_invariance_proved"] is False
    assert out["social_reactivity_closure_proved"] is False
    assert out["post_freeze_terminal_result_proved"] is False
    assert out["domain_execution_closure"] is False
