from canonical.runtime.proposal_generation_ownership_gate_v1 import classify

def exact_cap():
    return {
      "id":"solve","requires":[],"provides":["ANSWER_VERIFIED"],"cost":1,"result_fields":[],
      "action":{"type":"verified_policy","verifier_id":"EXACT_JSON_V1","verifier_payload":{"expected":{"answer":42}}}
    }

def p2_cap():
    return {
      "id":"p2","requires":[],"provides":["P2_VERIFIED"],"cost":1,"result_fields":[],
      "action":{"type":"verified_policy","verifier_id":"P2_AUTHENTICATED_TOP_LAW_V1","verifier_payload":{}}
    }

def test_exact_json_is_proposal_dependent():
    x=classify({"capabilities":[exact_cap()]})
    assert x["pass"] is True
    assert x["proposal_dependent_capability_ids"]==["solve"]
    assert x["solver_core_alone_generates_all_required_proposals"] is False

def test_p2_current_route_is_proposal_free():
    x=classify({"capabilities":[p2_cap()]})
    assert x["pass"] is True
    assert x["proposal_free_capability_ids"]==["p2"]
    assert x["proposal_dependent_capability_ids"]==[]

def test_current_registry_has_source_aligned_acceptance_verifier():
    x=classify({"capabilities":[exact_cap()]})
    assert "SOURCE_ALIGNED_ACCEPTANCE_PROGRAM_V1" in x["builtin_verifier_registry"]

def test_zero_credit():
    x=classify({"capabilities":[exact_cap()]})
    assert x["capability_credit_delta"]==0
    assert x["ownership_credit_delta"]==0
