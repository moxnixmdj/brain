from canonical.runtime.selected_support_truth_certificate_v5 import evaluate as support_v5
from canonical.runtime.p3_real_context_v3_admission_v6 import evaluate as front
from canonical.runtime.synthesis_certified_visible_support_policy_v3 import INPUT_SCHEMA

def ev(i,text,source=None):
    return {"evidence_id":i,"text":text,"verified":True,
            "provenance":[{"source_id":source or i,"locator":"p1"}]}

def req(i,text):
    return {"claim_id":i,"text":text,"required":True}

def constraints():
    return {"output_format":"BULLETS","citation_mode":"INLINE_SOURCE_IDS",
            "style":"VERBATIM_GROUNDED","required_sections":[],"allowed_sections":None,
            "max_items":3,"max_chars":5000,"heading_level":2,"require_title":False}

def v3(claim,evidence):
    return {"schema":INPUT_SCHEMA,"task":{"claims":[req("C",claim)],"evidence":evidence,
      "audience_profile":{"profile_id":"EXPLICIT","constraints":constraints()},
      "required_uncertainty_units":[]}}

def cert(claim,evidence):
    return support_v5({"predicate_id":"X","claim":req("C",claim),"evidence":evidence})

def test_transitive_categorical_support_added_without_authority():
    out=cert("Tweety is a member of Animal.",[
      ev("E1","Report states that Tweety is a member of Canary."),
      ev("E2","Taxonomy states Canary is a subclass of Bird."),
      ev("E3","Taxonomy states Bird is a subclass of Animal."),
    ])
    assert out["pass"] and out["predicate_truth"]=="TRUE",out
    assert out["support_evidence_ids"]==["E1","E2","E3"]
    assert out["terminal_authority"] is False and out["terminal_credit_delta"]==0

def test_categorical_conflict_fails_positive_assertion():
    out=cert("Tweety is a member of Canary.",[
      ev("E1","Report states that Tweety is a member of Canary."),
      ev("E2","Report states that Tweety is not a member of Bird."),
      ev("E3","Taxonomy states Canary is a subclass of Bird."),
    ])
    assert out["pass"] and out["predicate_truth"]=="FALSE"
    assert out["conflict_evidence_ids"]==["E2","E3"]

def test_existing_set_membership_route_preserved():
    out=cert("Asset category is in {equity, bond}.",[
      ev("E","Report states Asset category is equity.")
    ])
    assert out["pass"] and out["predicate_truth"]=="TRUE",out
    assert out["relation_audit"][0]["grammar"]=="SET_MEMBERSHIP_V1"
    assert "categorical_support_receipt" not in out

def test_existing_numeric_route_preserved():
    out=cert("Revenue growth is at least 10.",[
      ev("E","Report states Revenue growth is 12.")
    ])
    assert out["pass"] and out["predicate_truth"]=="TRUE",out
    assert out["relation_audit"][0]["grammar"]=="NUMERIC_RELATION_V1"

def test_current_v6_front_door_consumes_transitive_categorical_support():
    out=front({"context_id":"x","v3_input":v3("Tweety is a member of Animal.",[
      ev("E1","Report states that Tweety is a member of Canary.","REPORT"),
      ev("E2","Taxonomy states Canary is a subclass of Bird.","TAXONOMY"),
      ev("E3","Taxonomy states Bird is a subclass of Animal.","TAXONOMY"),
    ])})
    assert out["pass"],out
    assert out["route"]=="REQUIRED_SUPPORT_V5_REALIZATION_CELL_V3"
    assert out["p3_contract_cell_authorized"] is True
    assert out["terminal_authority"] is False and out["terminal_credit_delta"]==0
