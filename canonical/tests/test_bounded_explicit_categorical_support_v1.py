from canonical.runtime.bounded_explicit_categorical_support_v1 import (
    evaluate_support,
    parse_categorical_claim,
)

def ev(i, text):
    return {"evidence_id": i, "text": text}

def test_claim_scope_detection():
    assert parse_categorical_claim("Tweety is a member of Canary.")["claim_in_scope"] is True
    assert parse_categorical_claim("Every canary is a bird.")["claim_in_scope"] is False

def test_direct_membership_support():
    out=evaluate_support("Tweety is a member of Canary.",[
        ev("E1","Report states that Tweety is a member of Canary.")
    ])
    assert out["status"]=="RESOLVED"
    assert out["relation"]=="SUPPORTS"
    assert out["support_evidence_ids"]==["E1"]

def test_transitive_membership_support_with_provenance_path():
    out=evaluate_support("Tweety is a member of Animal.",[
        ev("E1","Report states that Tweety is a member of Canary."),
        ev("E2","Taxonomy states Canary is a subclass of Bird."),
        ev("E3","Taxonomy states Bird is a subclass of Animal."),
    ])
    assert out["relation"]=="SUPPORTS",out
    assert out["support_evidence_ids"]==["E1","E2","E3"]
    assert out["support_proof_paths"]==[["E1","E2","E3"]]

def test_subclass_transitive_support():
    out=evaluate_support("Canary is a subclass of Animal.",[
        ev("E1","Taxonomy states Canary is a subclass of Bird."),
        ev("E2","Taxonomy states Bird is a subclass of Animal."),
    ])
    assert out["relation"]=="SUPPORTS"
    assert out["support_proof_paths"]==[["E1","E2"]]

def test_no_illegal_downward_positive_inference():
    out=evaluate_support("Tweety is a member of Canary.",[
        ev("E1","Report states that Tweety is a member of Bird."),
        ev("E2","Taxonomy states Canary is a subclass of Bird."),
    ])
    assert out["relation"]=="UNRELATED"

def test_negative_membership_propagates_downward():
    out=evaluate_support("Tweety is not a member of Canary.",[
        ev("E1","Report states that Tweety is not a member of Bird."),
        ev("E2","Taxonomy states Canary is a subclass of Bird."),
    ])
    assert out["relation"]=="SUPPORTS",out
    assert out["support_evidence_ids"]==["E1","E2"]

def test_negative_membership_does_not_propagate_upward():
    out=evaluate_support("Tweety is not a member of Bird.",[
        ev("E1","Report states that Tweety is not a member of Canary."),
        ev("E2","Taxonomy states Canary is a subclass of Bird."),
    ])
    assert out["relation"]=="UNRELATED"

def test_positive_membership_conflicts_with_negative_superclass():
    out=evaluate_support("Tweety is a member of Canary.",[
        ev("E1","Report states that Tweety is not a member of Bird."),
        ev("E2","Taxonomy states Canary is a subclass of Bird."),
    ])
    assert out["relation"]=="CONFLICTS"
    assert out["conflict_evidence_ids"]==["E1","E2"]

def test_both_support_and_conflict_preserved():
    out=evaluate_support("Tweety is a member of Canary.",[
        ev("E1","Report states that Tweety is a member of Canary."),
        ev("E2","Report states that Tweety is not a member of Bird."),
        ev("E3","Taxonomy states Canary is a subclass of Bird."),
    ])
    assert out["relation"]=="BOTH"
    assert out["support_evidence_ids"]==["E1"]
    assert out["conflict_evidence_ids"]==["E2","E3"]

def test_cycle_terminates_and_supports_reachable_class():
    out=evaluate_support("Tweety is a member of Bird.",[
        ev("E1","Report states that Tweety is a member of Canary."),
        ev("E2","Taxonomy states Canary is a subclass of Finch."),
        ev("E3","Taxonomy states Finch is a subclass of Canary."),
        ev("E4","Taxonomy states Finch is a subclass of Bird."),
    ])
    assert out["relation"]=="SUPPORTS"
    assert out["support_evidence_ids"]==["E1","E2","E4"]

def test_noncategory_evidence_is_unrelated_not_authoritative():
    out=evaluate_support("Tweety is a member of Canary.",[
        ev("E1","Report states Revenue growth is 12.")
    ])
    assert out["relation"]=="UNRELATED"
    assert out["support_evidence_ids"]==[]
    assert out["conflict_evidence_ids"]==[]

def test_malformed_category_shaped_evidence_is_unknown():
    out=evaluate_support("Tweety is a member of Canary.",[
        ev("E1","Report states that Tweety is a member of.")
    ])
    assert out["status"]=="UNRESOLVED"
    assert out["relation"]=="UNKNOWN"

def test_generic_copula_is_outside_scope():
    out=evaluate_support("Every canary is a bird.",[
        ev("E1","Report states that Every canary is a bird.")
    ])
    assert out["status"]=="UNRESOLVED"
    assert out["claim_in_scope"] is False

def test_direct_negative_subclass_only_no_closed_world():
    out=evaluate_support("Canary is not a subclass of Bird.",[
        ev("E1","Taxonomy states Canary is not a subclass of Bird.")
    ])
    assert out["relation"]=="SUPPORTS"
    out2=evaluate_support("Canary is not a subclass of Animal.",[
        ev("E1","Taxonomy states Canary is a subclass of Bird.")
    ])
    assert out2["relation"]=="UNRELATED"
