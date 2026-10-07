from canonical.runtime.solver_candidate_measurement_gate_v1 import audit_problem


def cap(cid, verifier_id):
    return {
        "id": cid,
        "requires": [],
        "provides": [cid + "_VERIFIED"],
        "cost": 1,
        "result_fields": [],
        "action": {
            "type": "verified_policy",
            "verifier_id": verifier_id,
            "verifier_payload": {},
        },
    }


def test_raw_typed_acceptance_is_blocked_for_effect_promotion():
    out = audit_problem({"capabilities": [cap("quality", "TYPED_ACCEPTANCE_PROGRAM_V1")]})
    assert out["pass"] is False
    assert out["status"] == "FAIL_CLOSED__UNBOUND_CANDIDATE_MEASUREMENT"


def test_source_aligned_typed_acceptance_is_also_blocked():
    out = audit_problem({"capabilities": [cap("quality", "SOURCE_ALIGNED_ACCEPTANCE_PROGRAM_V1")]})
    assert out["pass"] is False
    assert out["blocked"][0]["verifier_id"] == "SOURCE_ALIGNED_ACCEPTANCE_PROGRAM_V1"


def test_exact_json_remains_admissible():
    out = audit_problem({"capabilities": [cap("exact", "EXACT_JSON_V1")]})
    assert out["pass"] is True


def test_instruction_constraint_verifier_remains_admissible():
    out = audit_problem({"capabilities": [cap("text", "INSTRUCTION_CONSTRAINTS_V1")]})
    assert out["pass"] is True


def test_structured_method_verifier_remains_admissible():
    out = audit_problem({"capabilities": [cap("method", "STRUCTURED_METHOD_EXPRESSION_AST_V2")]})
    assert out["pass"] is True


def test_mixed_problem_fails_if_one_capability_has_unbound_candidate_values():
    out = audit_problem({
        "capabilities": [
            cap("exact", "EXACT_JSON_V1"),
            cap("quality", "TYPED_ACCEPTANCE_PROGRAM_V1"),
        ]
    })
    assert out["pass"] is False
    assert [x["capability_id"] for x in out["blocked"]] == ["quality"]
