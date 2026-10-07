from canonical.runtime import astra_runtime as ar
from canonical.runtime import honesty_envelope_v1 as honesty


class FakePlanner:
    @staticmethod
    def plan_actions(problem):
        return {
            "planning": {"initial_facts": []},
            "actions": [{"type": "finish", "args": {"summary": "DONE"}}],
            "composition_contract": [],
        }


def test_capability_plan_attaches_actual_composition_receipt_to_honesty(monkeypatch):
    head = "a" * 64
    monkeypatch.setattr(ar, "_inherit_verified_capabilities", lambda problem: problem)
    monkeypatch.setattr(ar, "_load_capability_planner", lambda: FakePlanner)
    monkeypatch.setattr(
        ar,
        "_run_model_independent_goal",
        lambda derived, mission, goal: {
            "composition_state_capsule": {"head_hash": head},
        },
    )

    result = ar._run_capability_planned_goal(
        {
            "id": "execute-plan",
            "capability_problem": {
                "initial_facts": [],
                "target_effects": ["DONE"],
                "capabilities": [],
            },
        },
        {"mission_id": "MISSION-1"},
        "execute bounded plan",
    )

    assert result["honesty_record"]["task_contract"]["task_id"] == "MISSION-1::step::execute-plan"
    assert result["terminal_honesty_record"]["task_contract"]["task_id"] == "MISSION-1"
    assert result["honesty_record"]["obligations"][0]["receipts"] == [head]
    assert honesty.adjudicate(result["honesty_record"])["status"] == "PASS"
    assert honesty.adjudicate(result["terminal_honesty_record"])["status"] == "PASS"
    assert "DOES_NOT_CERTIFY_GLOBAL_TASK_SEMANTIC_ADEQUACY" in result["honesty_scope_boundary"]


def test_capability_plan_without_composition_receipt_fails_closed(monkeypatch):
    monkeypatch.setattr(ar, "_inherit_verified_capabilities", lambda problem: problem)
    monkeypatch.setattr(ar, "_load_capability_planner", lambda: FakePlanner)
    monkeypatch.setattr(
        ar,
        "_run_model_independent_goal",
        lambda derived, mission, goal: {
            "composition_state_capsule": {"head_hash": None},
        },
    )

    try:
        ar._run_capability_planned_goal(
            {
                "id": "execute-plan",
                "capability_problem": {
                    "initial_facts": [],
                    "target_effects": ["DONE"],
                    "capabilities": [],
                },
            },
            {"mission_id": "MISSION-1"},
            "execute bounded plan",
        )
    except Exception as exc:
        assert "CAPABILITY_PLAN_COMPOSITION_RECEIPT_MISSING" in str(exc)
    else:
        raise AssertionError("missing composition receipt was accepted")
