from canonical.runtime.semantic_elision_db_admission_v1 import evaluate

def test_invalid_route_fails_closed():
    out=evaluate({"route":"NOPE","payload":{}})
    assert out["pass"] is False
    assert out["db_admission_authorized"] is False

def test_direct_acceptance_missing_fields_fails_closed():
    out=evaluate({
        "route":"C_DIRECT_END_TO_END_ACCEPTANCE",
        "payload":{},
        "cell_id":"c",
        "policy_id":"p",
        "brain_owned_candidate_proved":True,
        "deployed_route_exactly_realizes_candidate":True,
        "authorized_resource_bound_proved":True,
    })
    assert out["pass"] is False
    assert out["db_admission_authorized"] is False

def test_robust_route_does_not_need_objective_identity():
    out=evaluate({
        "route":"B_ROBUST_COMMON_POLICY",
        "payload":{
            "cell_id":"c",
            "policy_id":"p",
            "cell_scope_sound":True,
            "possibility_set_complete":True,
            "all_load_bearing_terminal_dimensions_bound":True,
            "brain_owned_policy_proved":True,
            "deployed_route_exactly_realizes_policy":True,
            "authorized_resource_bound_proved":True,
            "worlds":[
                {"world_id":"w1","policy_adequate":True,"adequacy_independently_verified":True,"hard_constraints_satisfied":True},
                {"world_id":"w2","policy_adequate":True,"adequacy_independently_verified":True,"hard_constraints_satisfied":True},
            ],
            "content_bindings":{"adequacy":"sha"},
        },
    })
    assert out["pass"] is True
    assert out["db_admission_authorized"] is True
    assert out["semantic_world_reconstruction_required"] is False
    assert out["target_identity_required"] is False
