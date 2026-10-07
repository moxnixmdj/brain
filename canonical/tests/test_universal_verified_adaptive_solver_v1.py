from canonical.runtime.universal_verified_adaptive_solver_v1 import run


def exact_problem():
    return {
        "initial_facts": [],
        "target_effects": ["ANSWER_VERIFIED"],
        "capabilities": [{
            "id": "solve",
            "requires": [],
            "provides": ["ANSWER_VERIFIED"],
            "cost": 1,
            "result_fields": [],
            "action": {
                "type": "verified_policy",
                "verifier_id": "EXACT_JSON_V1",
                "verifier_payload": {"expected": {"answer": 42}},
            },
        }],
    }


def test_untrusted_correct_proposal_advances_only_after_verification():
    out = run(
        exact_problem(),
        proposal_packets={"solve": [{"candidate": {"answer": 42}}]},
    )
    assert out["pass"] is True, out
    assert out["status"] == "SOLVED__ALL_TARGET_EFFECTS_VERIFIED"
    assert "ANSWER_VERIFIED" in out["verified_facts"]
    assert len(out["trace"]) == 1


def test_wrong_proposal_is_falsified_and_does_not_advance_fact_state():
    out = run(
        exact_problem(),
        proposal_packets={"solve": [{"candidate": {"answer": 41}}]},
    )
    assert out["pass"] is False
    assert out["status"] == "ALL_AVAILABLE_PROPOSALS_FALSIFIED"
    assert "ANSWER_VERIFIED" not in out["verified_facts"]
    assert len(out["rejected_proposals"]) == 1


def test_missing_proposal_requests_proposal_without_granting_authority():
    out = run(exact_problem(), proposal_packets={})
    assert out["status"] == "NEED_PROPOSAL"
    assert out["proposal_has_authority"] is False
    assert out["verified_facts"] == []


def test_replans_after_verified_step():
    problem = {
        "initial_facts": [],
        "target_effects": ["B_VERIFIED"],
        "capabilities": [
            {
                "id": "a",
                "requires": [],
                "provides": ["A_VERIFIED"],
                "cost": 1,
                "result_fields": [],
                "action": {
                    "type": "verified_policy",
                    "verifier_id": "EXACT_JSON_V1",
                    "verifier_payload": {"expected": "a"},
                },
            },
            {
                "id": "b",
                "requires": ["A_VERIFIED"],
                "provides": ["B_VERIFIED"],
                "cost": 1,
                "result_fields": [],
                "action": {
                    "type": "verified_policy",
                    "verifier_id": "EXACT_JSON_V1",
                    "verifier_payload": {"expected": "b"},
                },
            },
        ],
    }
    out = run(
        problem,
        proposal_packets={
            "a": [{"candidate": "a"}],
            "b": [{"candidate": "b"}],
        },
    )
    assert out["pass"] is True, out
    assert [x["capability_id"] for x in out["trace"]] == ["a", "b"]


def test_unknown_verifier_cannot_be_registered_from_task_data():
    p = exact_problem()
    p["capabilities"][0]["action"]["verifier_id"] = "CALLER_SUPPLIED_MAGIC"
    out = run(p, proposal_packets={"solve": [{"candidate": {"answer": 42}}]})
    assert out["status"] == "FAIL_CLOSED"
    assert any("VERIFIER_NOT_BUILTIN" in x for x in out["errors"])


def test_verified_facts_may_resume_persistent_state_without_reproposal():
    out = run(
        exact_problem(),
        proposal_packets={},
        verified_facts=["ANSWER_VERIFIED"],
    )
    assert out["pass"] is True
    assert out["trace"] == []


def test_typed_acceptance_program_verifier_extends_solver_without_new_task_python():
    problem = {
        "initial_facts": [],
        "target_effects": ["QUALITY_VERIFIED"],
        "capabilities": [{
            "id": "quality",
            "requires": [],
            "provides": ["QUALITY_VERIFIED"],
            "cost": 1,
            "result_fields": [],
            "action": {
                "type": "verified_policy",
                "verifier_id": "TYPED_ACCEPTANCE_PROGRAM_V1",
                "verifier_payload": {
                    "program": {
                        "schema": "PROJECT_BRAIN_TYPED_ACCEPTANCE_PROGRAM_SPEC_V1",
                        "fields": [
                            {"id": "minimum", "type": "number", "dimension": "score", "source": "trusted"},
                            {"id": "score", "type": "number", "dimension": "score", "source": "candidate"},
                            {"id": "safe", "type": "boolean", "dimension": "dimensionless", "source": "candidate"},
                        ],
                        "accept_when": {
                            "op": "and",
                            "args": [
                                {
                                    "op": "ge",
                                    "left": {"op": "ref", "id": "score"},
                                    "right": {"op": "ref", "id": "minimum"},
                                },
                                {"op": "ref", "id": "safe"},
                            ],
                        },
                    },
                    "trusted_values": {"minimum": 10.0},
                },
            },
        }],
    }
    out = run(
        problem,
        proposal_packets={
            "quality": [{"candidate_values": {"score": 12.0, "safe": True}}],
        },
    )
    assert out["pass"] is True, out
    assert "QUALITY_VERIFIED" in out["verified_facts"]


def test_typed_acceptance_program_falsifies_bad_candidate():
    problem = {
        "initial_facts": [],
        "target_effects": ["QUALITY_VERIFIED"],
        "capabilities": [{
            "id": "quality",
            "requires": [],
            "provides": ["QUALITY_VERIFIED"],
            "cost": 1,
            "result_fields": [],
            "action": {
                "type": "verified_policy",
                "verifier_id": "TYPED_ACCEPTANCE_PROGRAM_V1",
                "verifier_payload": {
                    "program": {
                        "schema": "PROJECT_BRAIN_TYPED_ACCEPTANCE_PROGRAM_SPEC_V1",
                        "fields": [
                            {"id": "minimum", "type": "number", "dimension": "score", "source": "trusted"},
                            {"id": "score", "type": "number", "dimension": "score", "source": "candidate"},
                        ],
                        "accept_when": {
                            "op": "ge",
                            "left": {"op": "ref", "id": "score"},
                            "right": {"op": "ref", "id": "minimum"},
                        },
                    },
                    "trusted_values": {"minimum": 10.0},
                },
            },
        }],
    }
    out = run(
        problem,
        proposal_packets={
            "quality": [{"candidate_values": {"score": 9.0}}],
        },
    )
    assert out["pass"] is False
    assert out["status"] == "ALL_AVAILABLE_PROPOSALS_FALSIFIED"
