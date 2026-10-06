from canonical.runtime.k6_adequate_policy_set_compiler_v1 import (
    AdequatePolicySetError,
    compile_adequate_policy_sets,
)

def expect_error(fn, text):
    try:
        fn()
    except AdequatePolicySetError as exc:
        assert str(exc).startswith(text)
    else:
        raise AssertionError("expected AdequatePolicySetError")

def test_dominating_policy_enters_Fw_and_weaker_policy_does_not():
    out=compile_adequate_policy_sets(
        worlds=["w"],
        policy_ids=["good","bad"],
        brain_outcomes={"w":{
            "good":{"success":1.0,"failure":0.0},
            "bad":{"success":0.5,"failure":0.5},
        }},
        opus_outcomes={"w":{"success":0.9,"failure":0.1}},
        utilities={"success":{"success":1.0,"failure":0.0}},
        hard_violation_risks={},
    )
    assert out["status"]=="PASS"
    assert out["adequate_policy_sets"]["w"]==["good"]
    assert out["terminal_credit_delta"]==0

def test_hard_risk_regression_blocks_policy_even_with_higher_utility():
    out=compile_adequate_policy_sets(
        worlds=["w"],
        policy_ids=["risky"],
        brain_outcomes={"w":{"risky":{"high":0.9,"low":0.1}}},
        opus_outcomes={"w":{"high":0.8,"low":0.2}},
        utilities={"quality":{"high":1.0,"low":0.0}},
        hard_violation_risks={"violation":{"high":1.0,"low":0.0}},
    )
    assert out["status"]=="NO_TARGET_ADEQUATE_BRAIN_POLICY_IN_DECLARED_WORLD"
    assert out["adequate_policy_sets"]["w"]==[]
    assert out["empty_worlds"]==["w"]

def test_multiple_worlds_compile_independently():
    out=compile_adequate_policy_sets(
        worlds=["w0","w1"],
        policy_ids=["p0","p1"],
        brain_outcomes={
          "w0":{"p0":{"ok":1.0,"bad":0.0},"p1":{"ok":0.0,"bad":1.0}},
          "w1":{"p0":{"ok":0.0,"bad":1.0},"p1":{"ok":1.0,"bad":0.0}},
        },
        opus_outcomes={
          "w0":{"ok":0.9,"bad":0.1},
          "w1":{"ok":0.9,"bad":0.1},
        },
        utilities={"ok":{"ok":1.0,"bad":0.0}},
        hard_violation_risks={},
    )
    assert out["adequate_policy_sets"]=={"w0":["p0"],"w1":["p1"]}

def test_missing_world_outcome_fails_closed():
    expect_error(lambda: compile_adequate_policy_sets(
        worlds=["w0","w1"],
        policy_ids=["p"],
        brain_outcomes={"w0":{"p":{"ok":1.0}}},
        opus_outcomes={"w0":{"ok":1.0},"w1":{"ok":1.0}},
        utilities={"u":{"ok":1.0}},
        hard_violation_risks={},
    ),"BRAIN_WORLD_OUTCOMES_MISSING")

def test_missing_policy_outcome_fails_closed():
    expect_error(lambda: compile_adequate_policy_sets(
        worlds=["w"],
        policy_ids=["p0","p1"],
        brain_outcomes={"w":{"p0":{"ok":1.0}}},
        opus_outcomes={"w":{"ok":1.0}},
        utilities={"u":{"ok":1.0}},
        hard_violation_risks={},
    ),"BRAIN_POLICY_OUTCOME_MISSING")

def test_outcome_space_mismatch_fails_closed():
    expect_error(lambda: compile_adequate_policy_sets(
        worlds=["w"],
        policy_ids=["p"],
        brain_outcomes={"w":{"p":{"ok":1.0}}},
        opus_outcomes={"w":{"other":1.0}},
        utilities={"u":{"ok":1.0}},
        hard_violation_risks={},
    ),"OUTCOME_ORDER_INPUT_INVALID")

def test_empty_utility_family_fails_closed():
    expect_error(lambda: compile_adequate_policy_sets(
        worlds=["w"],
        policy_ids=["p"],
        brain_outcomes={"w":{"p":{"ok":1.0}}},
        opus_outcomes={"w":{"ok":1.0}},
        utilities={},
        hard_violation_risks={},
    ),"NONEMPTY_UTILITY_FAMILY_REQUIRED")

def test_no_terminal_authority_created():
    out=compile_adequate_policy_sets(
        worlds=["w"],
        policy_ids=["p"],
        brain_outcomes={"w":{"p":{"ok":1.0}}},
        opus_outcomes={"w":{"ok":1.0}},
        utilities={"u":{"ok":1.0}},
        hard_violation_risks={},
    )
    assert out["terminal_authority"] is False
