import copy
from pathlib import Path
from canonical.runtime import unknown_domain_v6_acceptance_reducer_v1 as r

ROOT=Path(__file__).resolve().parents[2]

def good_receipt():
    return {
        "schema":r.EXPECTED_RECEIPT_SCHEMA,
        "status":r.EXPECTED_RECEIPT_STATUS,
        "target_predicate":r.TARGET,
        "exact_subject_blobs":dict(r.EXPECTED_SUBJECT_BLOBS),
        "surrogate_codepoints_exhausted":2048,
        "forced_total_token_collision_survives":True,
        "nonproduction_falsification_cases":3888,
        "production_or_terminal_cases_generated":0,
        "acceptance_credit_delta":0,
    }

def test_exact_good_receipt_promotes_one_atom_only():
    out=r.reduce(good_receipt(),ROOT)
    assert out["status"]=="PROVED"
    assert out["proved_predicate_count_delta"]==1
    assert out["unresolved_predicate_count_delta"]==-1
    assert out["family_credit_delta"]==0
    assert out["capability_credit_delta"]==0
    assert out["ownership_credit_delta"]==0
    assert all(out["checks"].values())

def test_each_receipt_gate_fails_closed():
    mutations={
        "schema":"bad",
        "status":"bad",
        "target_predicate":"OTHER",
        "surrogate_codepoints_exhausted":2047,
        "forced_total_token_collision_survives":False,
        "nonproduction_falsification_cases":3887,
        "production_or_terminal_cases_generated":1,
        "acceptance_credit_delta":1,
    }
    for key,val in mutations.items():
        x=good_receipt(); x[key]=val
        out=r.reduce(x,ROOT)
        assert out["status"]=="FAIL_CLOSED",(key,out)
        assert out["proved_predicate_count_delta"]==0

def test_subject_map_mismatch_fails_closed():
    x=good_receipt()
    x["exact_subject_blobs"]=dict(x["exact_subject_blobs"])
    x["exact_subject_blobs"]["canonical/runtime/unknown_domain_direct_hidden_generator_v5.py"]="0"*40
    out=r.reduce(x,ROOT)
    assert out["status"]=="FAIL_CLOSED"
    assert out["checks"]["subject_map"] is False
