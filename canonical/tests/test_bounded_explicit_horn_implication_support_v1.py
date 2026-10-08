from canonical.runtime.bounded_explicit_horn_implication_support_v1 import (
    evaluate_support, parse_rule,
)

def ev(i,text):
    return {"evidence_id":i,"text":text}

def test_parse_prefixed_rule():
    out=parse_rule(
        "Policy states that if Company status is active, then Company eligible is yes.",
        default_source="E1",
    )
    assert out["status"]=="RESOLVED"
    assert out["antecedent"]=={"entity":"company","field":"status","value":"active"}
    assert out["consequent"]=={"entity":"company","field":"eligible","value":"yes"}

def test_direct_forward_entailment():
    out=evaluate_support("Company eligible is yes.",[
        ev("E1","Report states Company status is active."),
        ev("E2","Policy states if Company status is active, then Company eligible is yes."),
    ])
    assert out["status"]=="RESOLVED"
    assert out["relation"]=="SUPPORTS"
    assert out["support_evidence_ids"]==["E1","E2"]

def test_transitive_forward_entailment():
    out=evaluate_support("Company priority is high.",[
        ev("E1","Report states Company status is active."),
        ev("E2","Policy states if Company status is active, then Company eligible is yes."),
        ev("E3","Policy states if Company eligible is yes, then Company priority is high."),
    ])
    assert out["relation"]=="SUPPORTS"
    assert out["support_evidence_ids"]==["E1","E2","E3"]
    assert out["forward_chain_steps"]>=2

def test_conflicting_conclusion_is_explicit():
    out=evaluate_support("Company eligible is yes.",[
        ev("E1","Report states Company status is inactive."),
        ev("E2","Policy states if Company status is inactive, then Company eligible is no."),
    ])
    assert out["relation"]=="CONFLICTS"
    assert out["conflict_evidence_ids"]==["E1","E2"]

def test_both_support_and_conflict_stays_both():
    out=evaluate_support("Company eligible is yes.",[
        ev("E1","Report states Company status is active."),
        ev("E2","Policy states if Company status is active, then Company eligible is yes."),
        ev("E3","Report states Company risk is high."),
        ev("E4","Policy states if Company risk is high, then Company eligible is no."),
    ])
    assert out["relation"]=="BOTH"
    assert out["support_evidence_ids"]==["E1","E2"]
    assert out["conflict_evidence_ids"]==["E3","E4"]

def test_no_converse_or_contraposition():
    out=evaluate_support("Company status is active.",[
        ev("E1","Report states Company eligible is yes."),
        ev("E2","Policy states if Company status is active, then Company eligible is yes."),
    ])
    assert out["status"]=="RESOLVED"
    assert out["relation"]=="UNRELATED"

def test_no_rule_means_not_this_route():
    out=evaluate_support("Company eligible is yes.",[
        ev("E1","Report states Company eligible is yes."),
    ])
    assert out["status"]=="UNRESOLVED"
    assert out["reason"]=="NO_EXPLICIT_HORN_RULE_PRESENT"

def test_malformed_rule_shaped_evidence_unknown():
    out=evaluate_support("Company eligible is yes.",[
        ev("E1","Report states Company status is active."),
        ev("E2","Policy states if nonsense, then Company eligible is yes."),
    ])
    assert out["status"]=="UNRESOLVED"
    assert out["reason"]=="MALFORMED_EXPLICIT_HORN_RULE_EVIDENCE"
    assert out["unresolved_evidence_ids"]==["E2"]

def test_unparsed_extra_evidence_blocks_positive_claim():
    out=evaluate_support("Company eligible is yes.",[
        ev("E1","Report states Company status is active."),
        ev("E2","Policy states if Company status is active, then Company eligible is yes."),
        ev("E3","This prose is not in the checked fact grammar."),
    ])
    assert out["status"]=="UNRESOLVED"
    assert out["unresolved_evidence_ids"]==["E3"]

def test_no_terminal_authority():
    out=evaluate_support("Company eligible is yes.",[
        ev("E1","Report states Company status is active."),
        ev("E2","Policy states if Company status is active, then Company eligible is yes."),
    ])
    assert out["terminal_authority"] is False
