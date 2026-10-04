from canonical.runtime.unknown_domain_direct_hidden_scorer_v1 import (
    TRANSFER, ABSTAIN, score_case
)

def transfer_hidden():
    return {
      "leaf_id":TRANSFER,"case_id":"T-X","gold_terminal_consequence":"GO",
      "domain_a_earned_receipt_ids":["R1"],"full_rediscovery_probe_floor":3,
      "transfer_relevant_feature_ids":["F1","F2"],"distractor_feature_ids":["D1","D2"],
    }

def transfer_trace():
    return {
      "decision":"CONCLUDE","terminal_consequence":"GO",
      "domain_a_source_receipt_ids":["R1"],"transferred_primitive_fingerprint":"prim:abc","domain_b_discovery_probe_count":1,
      "support_feature_ids":["F1","F2"],"negative_transfer_rejected_feature_ids":["D1","D2"],
      "mapping_basis":"CAUSAL_ISOMORPHISM",
      "evidence_provenance":[
        {"evidence_id":"R1","source":"A","receipt":"sha:R1"},
        {"evidence_id":"F1","source":"B","receipt":"sha:F1"},
        {"evidence_id":"F2","source":"B","receipt":"sha:F2"},
        {"evidence_id":"D1","source":"B","receipt":"sha:D1"},
        {"evidence_id":"D2","source":"B","receipt":"sha:D2"},
      ]
    }

def test_transfer_exact_good_passes():
    assert score_case(transfer_hidden(),transfer_trace())["pass"] is True

def test_transfer_distractor_support_fails():
    t=transfer_trace();t["support_feature_ids"]=["F1","F2","D1"]
    assert score_case(transfer_hidden(),t)["pass"] is False

def test_transfer_full_rediscovery_fails():
    t=transfer_trace();t["domain_b_discovery_probe_count"]=3
    assert score_case(transfer_hidden(),t)["pass"] is False

def abst_hidden(status):
    x={"leaf_id":ABSTAIN,"case_id":"A-"+status,"identifiability_status":status}
    if status=="IDENTIFIABLE":x["gold_terminal_consequence"]="YES"
    if status=="UNDERSPECIFIED":x["minimum_discriminator_id"]="P2"
    return x

def test_identifiable_requires_exact_conclusion():
    assert score_case(abst_hidden("IDENTIFIABLE"),{"decision":"CONCLUDE","terminal_consequence":"YES"})["pass"] is True
    assert score_case(abst_hidden("IDENTIFIABLE"),{"decision":"ABSTAIN","nonidentifiability_witness":"x"})["pass"] is False

def test_nonidentifiable_requires_abstention_witness():
    assert score_case(abst_hidden("NONIDENTIFIABLE"),{"decision":"ABSTAIN","nonidentifiability_witness":"two survivors"})["pass"] is True
    assert score_case(abst_hidden("NONIDENTIFIABLE"),{"decision":"CONCLUDE","terminal_consequence":"X"})["pass"] is False

def test_underspecified_accepts_exact_discriminator_or_witnessed_abstention():
    assert score_case(abst_hidden("UNDERSPECIFIED"),{"decision":"REQUEST_DISCRIMINATOR","discriminator":"P2"})["pass"] is True
    assert score_case(abst_hidden("UNDERSPECIFIED"),{"decision":"ABSTAIN","nonidentifiability_witness":"missing P2"})["pass"] is True
    assert score_case(abst_hidden("UNDERSPECIFIED"),{"decision":"REQUEST_DISCRIMINATOR","discriminator":"P9"})["pass"] is False

def test_transfer_wrong_primitive_fingerprint_fails():
    t=transfer_trace();t["transferred_primitive_fingerprint"]="prim:wrong"
    assert score_case(transfer_hidden(),t)["pass"] is False

def test_transfer_unbound_receipt_fails():
    h=transfer_hidden();h["domain_a_receipt_primitive_bindings"]={"R1":"prim:other"}
    assert score_case(h,transfer_trace())["pass"] is False
