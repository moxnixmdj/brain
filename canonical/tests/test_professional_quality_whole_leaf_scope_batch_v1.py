from copy import deepcopy
from canonical.runtime import professional_quality_whole_leaf_scope_batch_v1 as b

def real_docs():
    import json
    from pathlib import Path
    root=Path(__file__).resolve().parents[2]
    return (
      json.loads((root/b.PINS["manifest"][0]).read_text()),
      json.loads((root/b.PINS["domain_verify"][0]).read_text()),
    )

def test_real_24_leaf_batch_passes_scope_only():
    m,v=real_docs(); out=b.project_documents(m,v)
    assert out["pass"] is True
    assert out["leaf_count"]==24 and out["domain_equivalence_pass_count"]==24
    assert out["scope_complete_count"]==24 and out["property_truth_count"]==0
    assert out["unique_claim_id_count"]==24

def test_rows_never_gain_property_truth():
    m,v=real_docs(); out=b.project_documents(m,v)
    assert all(r["leaf_property_truth_authority"] is False for r in out["rows"])

def test_epoch_changes_claim_ids_but_not_scope_count():
    m,v=real_docs()
    a=b.project_documents(m,v,epoch="E1"); c=b.project_documents(m,v,epoch="E2")
    assert a["scope_complete_count"]==c["scope_complete_count"]==24
    assert {x["claim_id"] for x in a["rows"]}!={x["claim_id"] for x in c["rows"]}

def test_global_receipt_must_be_independent_24_of_24():
    m,v=real_docs(); v=deepcopy(v); v["independent_replay"]["real_manifest_passed"]=23
    assert b.project_documents(m,v)["reason"]=="GLOBAL_DOMAIN_VERIFY_INDEPENDENT_REPLAY_INVALID"

def test_manifest_leaf_loss_fails_closed():
    m,v=real_docs(); m=deepcopy(m); m["roots"].pop()
    assert b.project_documents(m,v)["reason"]=="MANIFEST_LEAF_SET_INVALID"

def test_runtime_binding_drift_fails_closed():
    m,v=real_docs(); v=deepcopy(v); v["subject"]["runtime_git_blob_sha"]="0"*40
    assert b.project_documents(m,v)["reason"]=="GLOBAL_DOMAIN_VERIFY_RUNTIME_BINDING_STALE"
