import json
from canonical.runtime.p2_explicit_contract_membership_v1 import compile_membership, P2


def source(task_patch=None):
    task={
        "audience":"executive",
        "required_topics":["T1"],
        "evidence":[{"fact_id":"F1"}],
        "edit_candidates":[{
            "id":"E1","analysis_kind":"quantify","topic":"T1",
            "claims":["F1"],"intended_audience":"executive","cost":1,
        }],
        "edit_budget":1,
    }
    if task_patch:
        task.update(task_patch)
    return json.dumps({"contract":P2,"task":task},separators=(",",":"))


def test_valid_strict_source_passes():
    out=compile_membership(source(),source_id="root")
    assert out["pass"] is True
    assert out["scope"]=="STRICT_EXPLICIT_P2_JSON_SOURCE_CLASS_ONLY"
    assert out["extra_source_semantic_fields_permitted"] is False
    assert out["terminal_authority"] is False


def test_duplicate_json_key_rejected():
    raw='{"contract":"'+P2+'","contract":"'+P2+'","task":{}}'
    out=compile_membership(raw,source_id="root")
    assert out["pass"] is False
    assert any("DUPLICATE_JSON_KEY" in x for x in out["errors"])


def test_extra_task_dimension_rejected():
    out=compile_membership(source({"hidden_priority":"x"}),source_id="root")
    assert out["pass"] is False
    assert "TASK_KEYS_NOT_EXACT_P2_BASIS" in out["errors"]


def test_extra_evidence_semantics_rejected():
    d=json.loads(source()); d["task"]["evidence"][0]["text"]="semantic payload"
    out=compile_membership(json.dumps(d),source_id="root")
    assert out["pass"] is False
    assert any("EVIDENCE_ROW_KEYS_INVALID" in x for x in out["errors"])


def test_extra_edit_semantics_rejected():
    d=json.loads(source()); d["task"]["edit_candidates"][0]["style_priority"]="hidden"
    out=compile_membership(json.dumps(d),source_id="root")
    assert out["pass"] is False
    assert any("EDIT_ROW_KEYS_INVALID" in x for x in out["errors"])


def test_duplicate_fact_id_rejected():
    d=json.loads(source()); d["task"]["evidence"].append({"fact_id":"F1"})
    out=compile_membership(json.dumps(d),source_id="root")
    assert out["pass"] is False
    assert any("FACT_ID_DUPLICATE" in x for x in out["errors"])


def test_duplicate_edit_id_rejected():
    d=json.loads(source()); d["task"]["edit_candidates"].append(dict(d["task"]["edit_candidates"][0]))
    out=compile_membership(json.dumps(d),source_id="root")
    assert out["pass"] is False
    assert any("EDIT_ID_DUPLICATE" in x for x in out["errors"])


def test_boolean_cost_rejected_as_not_integer_cost():
    d=json.loads(source()); d["task"]["edit_candidates"][0]["cost"]=True
    out=compile_membership(json.dumps(d),source_id="root")
    assert out["pass"] is False
    assert any("EDIT_COST_INVALID" in x for x in out["errors"])


def test_wrong_contract_rejected():
    d=json.loads(source()); d["contract"]="OTHER"
    out=compile_membership(json.dumps(d),source_id="root")
    assert out["pass"] is False
    assert "P2_CONTRACT_REQUIRED" in out["errors"]


def test_membership_receipt_is_recomputed_from_bytes():
    a=compile_membership(source(),source_id="root")
    b=compile_membership(source(),source_id="other")
    assert a["pass"] and b["pass"]
    assert a["raw_source_sha256"]==b["raw_source_sha256"]
    assert a["membership_receipt"]!=b["membership_receipt"]
