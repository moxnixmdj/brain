from canonical.runtime.bound_capability_execution_verifier_v1 import verify
from canonical.runtime.capability_planner import plan_actions


def problem():
    return {
        "initial_facts": ["RAW"],
        "target_effects": ["DONE"],
        "capabilities": [{
            "id": "c",
            "requires": ["RAW"],
            "provides": ["DONE"],
            "cost": 1,
            "result_fields": ["value"],
            "action": {
                "type": "invoke_capability",
                "args": {"x": 1},
                "expect": {"field": "verified", "type": "field_equals", "value": True},
            },
        }],
    }


def good_execution():
    p = problem()
    planned = plan_actions(p)
    return {
        "trace": [
            {
                "cycle": 0,
                "plan": planned["actions"][0],
                "result": {"verified": True, "value": 7},
            },
            {
                "cycle": 1,
                "plan": planned["actions"][1],
                "result": {"summary": "CAPABILITY_PLAN_COMPLETE"},
            },
        ]
    }


def test_exact_recomputed_execution_trace_passes():
    out = verify({"problem": problem()}, {"execution": good_execution()})
    assert out["pass"] is True, out
    assert out["status"] == "VERIFIED"
    assert out["verified_output"]["all_target_effects_have_witnesses"] is True


def test_executor_cannot_swap_planned_action():
    ex = good_execution()
    ex["trace"][0]["plan"]["args"]["x"] = 999
    out = verify({"problem": problem()}, {"execution": ex})
    assert out["pass"] is False
    assert "RESOLVED_ACTION_MISMATCH" in str(out["reason"])


def test_failed_expectation_cannot_mint_target_effect():
    ex = good_execution()
    ex["trace"][0]["result"]["verified"] = False
    out = verify({"problem": problem()}, {"execution": ex})
    assert out["pass"] is False
    assert "ACTION_EFFECT_EXPECTATION_NOT_WITNESSED" in str(out["reason"])


def test_missing_target_producing_step_fails():
    ex = good_execution()
    ex["trace"] = [ex["trace"][1]]
    ex["trace"][0]["cycle"] = 0
    out = verify({"problem": problem()}, {"execution": ex})
    assert out["pass"] is False


def test_executor_cannot_insert_undeclared_extra_step():
    ex = good_execution()
    ex["trace"].insert(1, {
        "cycle": 1,
        "plan": {"type": "mystery", "args": {}},
        "result": {"verified": True},
    })
    ex["trace"][2]["cycle"] = 2
    out = verify({"problem": problem()}, {"execution": ex})
    assert out["pass"] is False
