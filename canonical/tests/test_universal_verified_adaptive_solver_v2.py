from canonical.runtime.universal_verified_adaptive_solver_v2 import run


def exact_cap(cid, requires, provides, expected):
    return {
        "id": cid,
        "requires": requires,
        "provides": provides,
        "cost": 1,
        "result_fields": [],
        "action": {
            "type": "verified_policy",
            "verifier_id": "EXACT_JSON_V1",
            "verifier_payload": {"expected": expected},
            "effect_contract": {
                "effects": provides,
                "verifier_success_condition": "CANDIDATE_EQUALS_EXPECTED",
            },
        },
    }


def exact_problem():
    return {
        "initial_facts": [],
        "target_effects": ["ANSWER_VERIFIED"],
        "capabilities": [
            exact_cap("solve", [], ["ANSWER_VERIFIED"], {"answer": 42})
        ],
    }


def test_correct_proposal_mints_exact_bound_effect():
    out = run(
        exact_problem(),
        proposal_packets={"solve": [{"candidate": {"answer": 42}}]},
    )
    assert out["pass"] is True, out
    assert out["status"] == "SOLVED__ALL_TARGET_EFFECTS_VERIFIER_BOUND"
    assert out["run_verified_target_effects"] == ["ANSWER_VERIFIED"]
    assert out["trace"][0]["new_verified_effects"] == ["ANSWER_VERIFIED"]
    assert len(out["trace"][0]["effect_contract_sha256"]) == 64


def test_wrong_proposal_cannot_mint_effect():
    out = run(
        exact_problem(),
        proposal_packets={"solve": [{"candidate": {"answer": 41}}]},
    )
    assert out["pass"] is False
    assert out["status"] == "ALL_AVAILABLE_PROPOSALS_FALSIFIED"
    assert out["run_verified_effects"] == []


def test_v1_style_unbound_provides_is_rejected():
    p = exact_problem()
    del p["capabilities"][0]["action"]["effect_contract"]
    out = run(p, proposal_packets={"solve": [{"candidate": {"answer": 42}}]})
    assert out["status"] == "FAIL_CLOSED"
    assert any("EFFECT_CONTRACT_REQUIRED" in x for x in out["errors"])


def test_provides_must_equal_effect_contract_exactly():
    p = exact_problem()
    p["capabilities"][0]["provides"] = [
        "ANSWER_VERIFIED",
        "OPUS55_PARITY_VERIFIED",
    ]
    out = run(p, proposal_packets={"solve": [{"candidate": {"answer": 42}}]})
    assert out["status"] == "FAIL_CLOSED"
    assert any("PROVIDES_EFFECT_CONTRACT_MISMATCH" in x for x in out["errors"])


def test_forged_success_condition_is_rejected():
    p = exact_problem()
    p["capabilities"][0]["action"]["effect_contract"][
        "verifier_success_condition"
    ] = "SOMETHING_NICER"
    out = run(p, proposal_packets={"solve": [{"candidate": {"answer": 42}}]})
    assert out["status"] == "FAIL_CLOSED"
    assert any("VERIFIER_SUCCESS_CONDITION_MISMATCH" in x for x in out["errors"])


def test_preloaded_target_cannot_self_certify_solve():
    p = exact_problem()
    p["initial_facts"] = ["ANSWER_VERIFIED"]
    out = run(p, proposal_packets={})
    assert out["pass"] is False
    assert out["status"] == "FAIL_CLOSED__PRELOADED_TARGET_EFFECT_UNAUTHENTICATED"


def test_caller_verified_target_cannot_self_certify_solve():
    out = run(exact_problem(), verified_facts=["ANSWER_VERIFIED"])
    assert out["pass"] is False
    assert out["status"] == "FAIL_CLOSED__PRELOADED_TARGET_EFFECT_UNAUTHENTICATED"


def test_two_step_chain_requires_both_verifier_bound_effects():
    p = {
        "initial_facts": [],
        "target_effects": ["B_VERIFIED"],
        "capabilities": [
            exact_cap("a", [], ["A_VERIFIED"], "a"),
            exact_cap("b", ["A_VERIFIED"], ["B_VERIFIED"], "b"),
        ],
    }
    out = run(
        p,
        proposal_packets={
            "a": [{"candidate": "a"}],
            "b": [{"candidate": "b"}],
        },
    )
    assert out["pass"] is True, out
    assert [x["capability_id"] for x in out["trace"]] == ["a", "b"]
    assert out["run_verified_target_effects"] == ["B_VERIFIED"]
