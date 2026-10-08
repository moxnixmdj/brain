from canonical.runtime.bounded_set_inclusion_membership_closure_v1 import evaluate

def e(i,text): return {"evidence_id":i,"text":text}

def test_one_hop_subset_support():
    out=evaluate({"claim_text":"alpha is a member of Approved.",
      "evidence":[e("E1","Tier A contains alpha."),e("E2","Tier A is a subset of Approved.")]})
    assert out["pass"] and out["predicate_truth"]=="TRUE"
    assert out["support_evidence_ids"]==["E1","E2"]
    assert out["proof"]["set_path"]==["tier a","approved"]

def test_multi_hop_subset_support():
    out=evaluate({"claim_text":"alpha is a member of Eligible.",
      "evidence":[
        e("E1","Tier A contains alpha."),
        e("E2","Tier A is a subset of Approved."),
        e("E3","Approved is a subset of Eligible."),
      ]})
    assert out["predicate_truth"]=="TRUE"
    assert out["proof"]["path_length"]==2
    assert out["support_evidence_ids"]==["E1","E2","E3"]

def test_cycle_is_safe():
    out=evaluate({"claim_text":"alpha is a member of Eligible.",
      "evidence":[
        e("E1","Tier A contains alpha."),
        e("E2","Tier A is a subset of Approved."),
        e("E3","Approved is a subset of Tier A."),
        e("E4","Approved is a subset of Eligible."),
      ]})
    assert out["predicate_truth"]=="TRUE"

def test_no_path_is_not_false_nonmembership():
    out=evaluate({"claim_text":"alpha is a member of Eligible.",
      "evidence":[e("E1","Tier A contains alpha."),e("E2","Other is a subset of Eligible.")]})
    assert out["predicate_truth"]=="FALSE"
    assert out["relation"]=="UNSUPPORTED_OPEN_WORLD"
    assert out["proof"]["absence_not_interpreted_as_nonmembership"] is True

def test_complete_target_absence_conflicts():
    out=evaluate({"claim_text":"alpha is a member of Eligible.",
      "evidence":[e("E1","The complete members of Eligible are {beta, gamma}.")]})
    assert out["predicate_truth"]=="FALSE"
    assert out["relation"]=="CONFLICTS"

def test_support_path_plus_complete_absence_is_inconsistent_unknown():
    out=evaluate({"claim_text":"alpha is a member of Eligible.",
      "evidence":[
        e("E1","Tier A contains alpha."),
        e("E2","Tier A is a subset of Eligible."),
        e("E3","The complete members of Eligible are {beta, gamma}."),
      ]})
    assert not out["pass"]
    assert out["predicate_truth"]=="UNKNOWN"
    assert out["status"]=="UNRESOLVED__EVIDENCE_INCONSISTENT"

def test_conflicting_complete_definitions_unknown():
    out=evaluate({"claim_text":"alpha is a member of Eligible.",
      "evidence":[
        e("E1","The complete members of Eligible are {alpha}."),
        e("E2","The complete members of Eligible are {beta}."),
      ]})
    assert not out["pass"] and out["predicate_truth"]=="UNKNOWN"

def test_unparsed_evidence_prevents_silent_closure():
    out=evaluate({"claim_text":"alpha is a member of Eligible.",
      "evidence":[
        e("E1","Tier A contains alpha."),
        e("E2","Tier A is a subset of Eligible."),
        e("E3","Someone informally doubts this categorization."),
      ]})
    assert not out["pass"] and out["predicate_truth"]=="UNKNOWN"

def test_taxonomic_language_not_parsed_as_subset():
    out=evaluate({"claim_text":"sparrow is a member of animals.",
      "evidence":[e("E1","sparrow is a kind of bird."),e("E2","birds are animals.")]})
    assert not out["pass"] and out["predicate_truth"]=="UNKNOWN"

def test_zero_terminal_authority():
    out=evaluate({"claim_text":"alpha is a member of Approved.",
      "evidence":[e("E1","Approved contains alpha.")]})
    assert out["terminal_authority"] is False
