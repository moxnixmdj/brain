from canonical.runtime.executable_skill_program_v7 import (
    candidate_digest,
)
from canonical.runtime.verified_skill_macro_planner_v1 import (
    compile_macro,
    plan_with_skills,
)


def problem():
    return {
        "initial_facts": ["RAW"],
        "target_effects": ["DONE"],
        "capabilities": [
            {
                "id": "a", "requires": ["RAW"], "provides": ["MID"],
                "cost": 5, "result_fields": [], "action": {"type": "x"},
            },
            {
                "id": "b", "requires": ["MID"], "provides": ["DONE"],
                "cost": 5, "result_fields": [], "action": {"type": "x"},
            },
            {
                "id": "slow", "requires": ["RAW"], "provides": ["DONE"],
                "cost": 20, "result_fields": [], "action": {"type": "x"},
            },
        ],
    }


def skill():
    steps = [
        {"index": 0, "op": "a", "inputs": ["RAW"], "outputs": ["MID"]},
        {"index": 1, "op": "b", "inputs": ["MID"], "outputs": ["DONE"]},
    ]
    ids = ["e1", "e2"]
    digest = candidate_digest(
        source_episode_ids=ids,
        steps=steps,
        preconditions=["RAW"],
        postconditions=["DONE"],
        invalidators=[],
    )
    return {
        "schema": "PROJECT_BRAIN_EXECUTABLE_SKILL_PROGRAM_V7",
        "status": "VERIFIED_EXECUTABLE_SKILL",
        "source_episode_ids": ids,
        "steps": steps,
        "preconditions": ["RAW"],
        "postconditions": ["DONE"],
        "invalidators": [],
        "candidate_sha256": digest,
        "verified_skill": True,
        "reuse_authorized": True,
        "candidate_only": False,
        "scope_relation": "EXACT",
        "verification_receipt": "receipt-1",
    }


def test_verified_skill_compiles_to_planner_macro():
    out = compile_macro(problem(), skill())
    assert out["status"] == "VERIFIED_SKILL_MACRO_READY"
    assert out["underlying_capability_ids"] == ["a", "b"]
    assert out["cost"] == 10


def test_skill_aware_planner_expands_macro_back_to_live_capabilities():
    out = plan_with_skills(problem(), [skill()])
    assert out["pass"] is True, out
    assert out["expanded_execution_plan"] == ["a", "b"]
    assert len(out["used_verified_skill_macros"]) == 1
    assert out["execution_authority"] is False


def test_contract_drift_invalidates_skill():
    p = problem()
    p["capabilities"][0]["provides"] = ["SOMETHING_ELSE"]
    try:
        compile_macro(p, skill())
    except Exception as exc:
        assert "SKILL_STEP_OUTPUT_CONTRACT_DRIFT:a" in str(exc)
    else:
        raise AssertionError("drifted capability was accepted")


def test_active_invalidator_removes_skill_from_planner():
    s = skill()
    s["invalidators"] = ["API_CHANGED"]
    s["candidate_sha256"] = candidate_digest(
        source_episode_ids=s["source_episode_ids"],
        steps=s["steps"],
        preconditions=s["preconditions"],
        postconditions=s["postconditions"],
        invalidators=s["invalidators"],
    )
    out = plan_with_skills(problem(), [s], active_invalidators=["API_CHANGED"])
    assert out["pass"] is True
    assert out["used_verified_skill_macros"] == []
    assert out["planner_plan"] == ["a", "b"]


def test_tampered_skill_digest_is_rejected():
    s = skill()
    s["candidate_sha256"] = "sha256:" + "0" * 64
    try:
        compile_macro(problem(), s)
    except Exception as exc:
        assert "SKILL_CANDIDATE_DIGEST_INVALID" in str(exc)
    else:
        raise AssertionError("tampered skill was accepted")
