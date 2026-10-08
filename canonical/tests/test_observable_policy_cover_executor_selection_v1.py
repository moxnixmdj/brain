from unittest.mock import patch
from canonical.runtime import observable_policy_cover_executor_v1 as ex

def test_selected_observation_routes_to_only_covering_policy():
    problem={
        "state_id":"S",
        "worlds":[{"world_id":"w0"},{"world_id":"w1"}],
        "policies":[
            {"policy_id":"p0","adequate_world_ids":["w0"]},
            {"policy_id":"p1","adequate_world_ids":["w1"]},
        ],
        "discriminators":[{"discriminator_id":"d","outcomes":{"w0":"a","w1":"b"}}],
    }
    tree={"pass":True,"bound_state_totality_proved":True,
          "decision_tree":{"discriminator_id":"d","outcome_partitions":[
              {"world_ids":["w0"],"next":{"terminal_policy_id":"p0"}},
              {"world_ids":["w1"],"next":{"terminal_policy_id":"p1"}},
          ]}}
    obs={"pass":True,"outcome":"b","outcome_sha256":"sha256:b",
         "receipt_path":"canonical/governance/o.json","receipt_git_blob_sha":"a",
         "verification_path":"canonical/verification/ov.json",
         "verification_git_blob_sha":"b","independent_verifier_id":"v"}
    with patch.object(ex,"_authenticate_cover_binding",return_value={"pass":True}),          patch.object(ex,"evaluate_cover",return_value=tree),          patch.object(ex,"_authenticate_observation",return_value=obs):
        out=ex.evaluate({"problem":problem,
            "observation_bindings_by_discriminator_id":{"d":{"bound":True}}})
    assert out["pass"] is True,out
    assert out["selected_policy_id"]=="p1"
    assert out["surviving_world_ids"]==["w1"]
    assert out["selected_policy_adequacy_verified"] is True
    assert out["actual_goal_satisfaction_verified"] is False
    assert out["terminal_authority"] is False
