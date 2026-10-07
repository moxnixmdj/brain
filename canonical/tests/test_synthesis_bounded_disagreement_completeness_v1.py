from canonical.runtime.synthesis_bounded_disagreement_completeness_v1 import compile_required_uncertainty

def ev(i,text):
    return {"evidence_id":i,"text":text,"provenance":[{"source_id":i,"locator":"p1"}]}

def test_no_conflict_yields_empty_complete_set():
    out=compile_required_uncertainty([ev("E1","Revenue growth is 12."),ev("E2","Revenue growth is 12.")])
    assert out["status"].startswith("PASS")
    assert out["scope_complete"] is True
    assert out["required_uncertainty_units"]==[]

def test_one_conflict_yields_one_complete_unit():
    out=compile_required_uncertainty([ev("E1","Revenue growth is 12."),ev("E2","Revenue growth is 9.")])
    assert out["scope_complete"] is True
    assert out["required_uncertainty_unit_count"]==1
    u=out["required_uncertainty_units"][0]
    assert u["entity"]=="revenue"
    assert u["field"]=="growth"
    assert u["values"]==["12","9"]
    assert u["evidence_ids"]==["E1","E2"]

def test_distinct_keys_do_not_create_false_conflict():
    out=compile_required_uncertainty([ev("E1","Revenue growth is 12."),ev("E2","Revenue margin is 9.")])
    assert out["required_uncertainty_units"]==[]

def test_multiple_conflicts_are_exhaustively_enumerated():
    out=compile_required_uncertainty([
      ev("E1","Revenue growth is 12."),
      ev("E2","Revenue growth is 9."),
      ev("E3","Margin rate is 5."),
      ev("E4","Margin rate is 6."),
    ])
    assert out["required_uncertainty_unit_count"]==2

def test_unparsed_evidence_fails_closed():
    out=compile_required_uncertainty([ev("E1","The company looks risky.")])
    assert out["status"]=="FAIL_CLOSED"
    assert out["reason"]=="EVIDENCE_OUTSIDE_BOUNDED_FACT_GRAMMAR"
    assert out["scope_complete"] is False

def test_missing_provenance_fails_closed():
    out=compile_required_uncertainty([{"evidence_id":"E1","text":"Revenue growth is 12.","provenance":[]}])
    assert out["status"]=="FAIL_CLOSED"
    assert out["reason"]=="EVIDENCE_PROVENANCE_REQUIRED"

def test_duplicate_evidence_id_fails_closed():
    out=compile_required_uncertainty([ev("E1","Revenue growth is 12."),ev("E1","Revenue growth is 9.")])
    assert out["status"]=="FAIL_CLOSED"
    assert out["reason"]=="EVIDENCE_ID_INVALID_OR_DUPLICATE"
