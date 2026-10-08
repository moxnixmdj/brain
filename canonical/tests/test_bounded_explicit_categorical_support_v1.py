from canonical.runtime.bounded_explicit_categorical_support_v1 import classify_support, parse_relation

def ev(i,text):
    return {"evidence_id":i,"text":text}

def test_direct_membership_support():
    out=classify_support("Tweety is a member of Bird.",[
        ev("E1","Report states that Tweety is a member of Bird.")
    ])
    assert out["status"]=="RESOLVED" and out["relation"]=="SUPPORTS"
    assert out["support_evidence_ids"]==["E1"]

def test_transitive_membership_support_keeps_proof_path():
    out=classify_support("Tweety is a member of Animal.",[
        ev("E1","Report states that Tweety is a member of Canary."),
        ev("E2","Taxonomy states that Canary is a subclass of Bird."),
        ev("E3","Taxonomy states that Bird is a subclass of Animal."),
    ])
    assert out["relation"]=="SUPPORTS"
    assert out["support_evidence_ids"]==["E1","E2","E3"]
    assert out["support_proof_paths"]==[["E1","E2","E3"]]

def test_negative_membership_propagates_downward_only():
    out=classify_support("Tweety is not a member of Canary.",[
        ev("E1","Report states that Tweety is not a member of Animal."),
        ev("E2","Taxonomy states that Canary is a subclass of Bird."),
        ev("E3","Taxonomy states that Bird is a subclass of Animal."),
    ])
    assert out["relation"]=="SUPPORTS"
    assert out["support_evidence_ids"]==["E1","E2","E3"]

    reverse=classify_support("Tweety is not a member of Animal.",[
        ev("E1","Report states that Tweety is not a member of Canary."),
        ev("E2","Taxonomy states that Canary is a subclass of Animal."),
    ])
    assert reverse["relation"]=="UNRELATED"
    assert reverse["support_evidence_ids"]==[]

def test_positive_membership_conflicted_by_negative_superclass():
    out=classify_support("Tweety is a member of Canary.",[
        ev("E1","A states that Tweety is a member of Canary."),
        ev("E2","B states that Tweety is not a member of Animal."),
        ev("E3","Taxonomy states that Canary is a subclass of Animal."),
    ])
    assert out["relation"]=="BOTH"
    assert out["support_evidence_ids"]==["E1"]
    assert out["conflict_evidence_ids"]==["E2","E3"]

def test_subclass_transitivity():
    out=classify_support("Canary is a subclass of Animal.",[
        ev("E1","Taxonomy states that Canary is a subclass of Bird."),
        ev("E2","Taxonomy states that Bird is a subclass of Animal."),
    ])
    assert out["relation"]=="SUPPORTS"
    assert out["support_evidence_ids"]==["E1","E2"]

def test_cycles_terminate_without_self_proof():
    out=classify_support("x is a member of b.",[
        ev("E1","R states that x is a member of a."),
        ev("E2","T states that a is a subclass of b."),
        ev("E3","T states that b is a subclass of a."),
    ])
    assert out["relation"]=="SUPPORTS"
    assert out["support_evidence_ids"]==["E1","E2"]

def test_every_sentence_is_outside_categorical_grammar():
    out=parse_relation("Every canary is a bird.")
    assert out["status"]=="UNRESOLVED"
    assert out["claim_in_scope"] is False

def test_unrelated_categorical_evidence_stays_unrelated():
    out=classify_support("Tweety is a member of Bird.",[
        ev("E1","Taxonomy states that Salmon is a member of Fish.")
    ])
    assert out["relation"]=="UNRELATED"

def test_authority_is_always_zero():
    out=classify_support("Tweety is a member of Bird.",[
        ev("E1","Report states that Tweety is a member of Bird.")
    ])
    assert out["terminal_authority"] is False
