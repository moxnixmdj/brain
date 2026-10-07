from canonical.runtime.source_positive_adequacy_db_admission_v1 import evaluate

def test_missing_route_premise_fails_closed():
    out=evaluate({"cell_id":"c","selected_policy_id":"p"})
    assert out["pass"] is False
    assert out["db_admission_authorized"] is False
    assert out["interpretation_set_enumeration_required"] is False

def test_no_interpretation_list_is_part_of_interface():
    out=evaluate({
        "cell_id":"c","selected_policy_id":"p",
        "cell_scope_sound":True,
        "brain_owned_policy_proved":True,
        "deployed_route_exactly_realizes_policy":True,
        "authorized_resource_bound_proved":True,
        "source_text":"x",
        "source_id":"s",
        "claims":[],
        "decision_basis":["a"],
        "policy_conditions":{"p":{"op":"ATOM","id":"a"}},
        "policy_adequacy_bindings":{"p":{}},
        "content_bindings":{"x":"sha"},
    })
    assert out["interpretation_set_enumeration_required"] is False
    assert out["db_admission_authorized"] is False
