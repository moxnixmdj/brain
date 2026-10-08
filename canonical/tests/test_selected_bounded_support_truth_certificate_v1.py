from canonical.runtime.selected_bounded_support_truth_certificate_v1 import evaluate, TRUE_POLICY, FALSE_POLICY

def claim(text="Revenue growth is 12.", alias="CLAIM_SUPPORTED"):
    return {"predicate_id":alias,"claim":{"claim_id":"C1","text":text,"required":True}}

def ev(eid,text,verified=True):
    return {"evidence_id":eid,"text":text,"verified":verified,
            "provenance":[{"source_id":eid,"locator":"p1"}]}

def payload(evidence,text="Revenue growth is 12.",alias="CLAIM_SUPPORTED"):
    p=claim(text,alias);p["evidence"]=evidence;return p

def test_support_true():
    out=evaluate(payload([ev("E1","Report states Revenue growth is 12.")]))
    assert out["pass"] and out["predicate_truth"]=="TRUE"
    assert out["selected_policy_id"]==TRUE_POLICY
    assert out["support_evidence_ids"]==["E1"] and out["conflict_evidence_ids"]==[]

def test_conflict_false():
    out=evaluate(payload([ev("E1","Report states Revenue growth is 12."),ev("E2","Other states Revenue growth is 11.")]))
    assert out["pass"] and out["predicate_truth"]=="FALSE"
    assert out["selected_policy_id"]==FALSE_POLICY
    assert out["conflict_evidence_ids"]==["E2"]

def test_no_support_false():
    out=evaluate(payload([ev("E1","Report states Margin rate is 8.")]))
    assert out["pass"] and out["predicate_truth"]=="FALSE"

def test_unresolved_grammar_unknown():
    out=evaluate(payload([ev("E1","Revenue probably grew a lot.")]))
    assert not out["pass"] and out["predicate_truth"]=="UNKNOWN"
    assert out["selected_policy_id"] is None

def test_alias_relabel_has_no_truth_authority():
    a=evaluate(payload([ev("E1","Report states Revenue growth is 12.")],alias="A"))
    b=evaluate(payload([ev("E1","Report states Revenue growth is 12.")],alias="B"))
    assert a["predicate_id"]==b["predicate_id"]
    assert a["requested_predicate_id"]!=b["requested_predicate_id"]
    assert not a["requested_predicate_id_authority"]

def test_evidence_change_changes_observation_not_predicate_identity():
    a=evaluate(payload([ev("E1","Report states Revenue growth is 12.")]))
    b=evaluate(payload([ev("E1","Report states Revenue growth is 11.")]))
    assert a["predicate_id"]==b["predicate_id"]
    assert a["evidence_set_sha256"]!=b["evidence_set_sha256"]
    assert a["predicate_truth"]!=b["predicate_truth"]

def test_claim_change_changes_predicate_identity():
    a=evaluate(payload([ev("E1","Report states Revenue growth is 12.")]))
    b=evaluate(payload([ev("E1","Report states Margin rate is 8.")],text="Margin rate is 8."))
    assert a["predicate_id"]!=b["predicate_id"]

def test_evidence_order_invariant():
    rows=[ev("E1","Report states Revenue growth is 12."),ev("E2","Other states Margin rate is 8.")]
    a=evaluate(payload(rows));b=evaluate(payload(list(reversed(rows))))
    assert a["evidence_set_sha256"]==b["evidence_set_sha256"]
    assert a["predicate_truth"]==b["predicate_truth"]

def test_optional_claim_rejected():
    p=payload([ev("E1","Report states Revenue growth is 12.")]);p["claim"]["required"]=False
    assert evaluate(p)["reason"]=="CLAIM_NOT_STRUCTURALLY_REQUIRED"

def test_caller_include_or_relevance_metadata_rejected():
    p=payload([ev("E1","Report states Revenue growth is 12.")]);p["claim"]["include"]=True
    assert evaluate(p)["reason"]=="UNTRUSTED_CLAIM_METADATA_FORBIDDEN"
    p=payload([ev("E1","Report states Revenue growth is 12.")]);p["evidence"][0]["support"]="SUPPORTED"
    assert evaluate(p)["reason"]=="UNTRUSTED_EVIDENCE_METADATA_FORBIDDEN"

def test_unverified_evidence_rejected():
    p=payload([ev("E1","Report states Revenue growth is 12.",False)])
    assert evaluate(p)["reason"]=="UNVERIFIED_EVIDENCE_UNIT"

def test_duplicate_evidence_rejected():
    p=payload([ev("E1","Report states Revenue growth is 12."),ev("E1","Report states Margin rate is 8.")])
    assert evaluate(p)["reason"]=="DUPLICATE_EVIDENCE_ID"

def test_authority_boundaries_zero():
    out=evaluate(payload([ev("E1","Report states Revenue growth is 12.")]))
    assert out["source_authorization_verified"] is False
    assert out["policy_adequacy_authority"] is False
    assert out["db_admission_authority"] is False
    assert out["u_subtraction_authority"] is False
    assert out["terminal_authority"] is False
    assert out["terminal_credit_delta"]==0
