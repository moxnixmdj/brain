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


def test_negative_subclass_transitive_conflict():
    # Canary ⊆ Bird ⊆ Animal ⊆ Living conflicts with Canary ⊈ Living.
    rows=[
        ev("E1","T states that Canary is a subclass of Bird."),
        ev("E2","T states that Bird is a subclass of Animal."),
        ev("E3","T states that Animal is a subclass of Living."),
        ev("E4","T states that Canary is not a subclass of Living."),
    ]
    p=classify_support("Bird is a subclass of Animal.",rows)
    assert p["relation"]=="BOTH",p
    assert p["support_evidence_ids"]==["E2"]
    assert set(p["conflict_evidence_ids"])=={"E1","E3","E4"}
    n=classify_support("Bird is not a subclass of Animal.",rows)
    assert n["relation"]=="BOTH",n
    assert set(n["support_evidence_ids"])=={"E1","E3","E4"}
    assert n["conflict_evidence_ids"]==["E2"]


def test_negative_subclass_without_all_edges_stays_unrelated():
    out=classify_support("Bird is not a subclass of Animal.",[
        ev("E1","T states that Canary is not a subclass of Living."),
        ev("E2","T states that Canary is a subclass of Bird."),
    ])
    assert out["relation"]=="UNRELATED",out


def test_reflexive_negative_subset_never_supported():
    out=classify_support("Bird is not a subset of Bird.",[
        ev("E1","T states that Bird is not a subset of Bird."),
    ])
    assert out["status"]=="UNRESOLVED" and out["relation"]=="UNKNOWN",out
    assert out["terminal_authority"] is False


def test_quantified_member_surface_is_outside_categorical_grammar():
    out=parse_relation("Every canary is a member of Bird.")
    assert out["status"]=="UNRESOLVED"
    assert out["claim_in_scope"] is False


def test_namespaced_terms_are_not_misread_as_source_prefixes():
    out=parse_relation("ex:Tweety is a member of ex:Bird.")
    assert out["status"]=="RESOLVED",out
    assert out["subject"]=="ex:tweety"
    assert out["category"]=="ex:bird"
    assert out["source"] is None

    prefixed=parse_relation("Taxonomy: ex:Canary is a subclass of ex:Bird.")
    assert prefixed["status"]=="RESOLVED",prefixed
    assert prefixed["subclass"]=="ex:canary"
    assert prefixed["superclass"]=="ex:bird"
    assert prefixed["source"]=="Taxonomy"


def test_explicit_reflexive_subclass_keeps_provenance():
    out=classify_support("Bird is a subclass of Bird.",[
        ev("E1","Taxonomy states that Bird is a subclass of Bird.")
    ])
    assert out["relation"]=="SUPPORTS",out
    assert out["support_evidence_ids"]==["E1"]

def test_unevidenced_reflexivity_does_not_mint_grounded_support():
    out=classify_support("Bird is a subclass of Bird.",[
        ev("E1","Taxonomy states that Canary is a subclass of Bird.")
    ])
    assert out["relation"]=="UNRELATED",out
    assert out["support_evidence_ids"]==[]
