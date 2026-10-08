from canonical.runtime import observable_policy_cover_executor_v1 as ex

def test_cover_binding_is_required_before_any_selection():
    out=ex.evaluate({"problem":{
        "state_id":"S",
        "worlds":[{"world_id":"w0"}],
        "policies":[],
        "discriminators":[],
    }})
    assert out["pass"] is False
    assert out["status"]=="OPEN__POLICY_COVER_INPUT_BINDING_REQUIRED"
    assert out["policy_selection_authorized"] is False
