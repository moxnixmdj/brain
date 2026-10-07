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


def test_instruction_constraint_verifier_is_generic_over_explicit_text_rules():
    problem = {
        "initial_facts": [],
        "target_effects": ["FORMAT_VERIFIED"],
        "capabilities": [{
            "id": "format",
            "requires": [],
            "provides": ["FORMAT_VERIFIED"],
            "cost": 1,
            "result_fields": [],
            "action": {
                "type": "verified_policy",
                "verifier_id": "INSTRUCTION_CONSTRAINTS_V1",
                "verifier_payload": {
                    "instruction": 'Response must start with "OK" and contain the word "done".'
                },
            },
        }],
    }
    out = run(
        problem,
        proposal_packets={"format": [{"response": "OK done"}]},
    )
    assert out["pass"] is True, out


def test_instruction_constraint_verifier_falsifies_violation():
    problem = {
        "initial_facts": [],
        "target_effects": ["FORMAT_VERIFIED"],
        "capabilities": [{
            "id": "format",
            "requires": [],
            "provides": ["FORMAT_VERIFIED"],
            "cost": 1,
            "result_fields": [],
            "action": {
                "type": "verified_policy",
                "verifier_id": "INSTRUCTION_CONSTRAINTS_V1",
                "verifier_payload": {
                    "instruction": 'Response must start with "OK".'
                },
            },
        }],
    }
    out = run(
        problem,
        proposal_packets={"format": [{"response": "NO"}]},
    )
    assert out["status"] == "ALL_AVAILABLE_PROPOSALS_FALSIFIED"


def test_structured_method_route_compiles_requirement_to_verified_output_without_proposal():
    public = {
        "schema_fields": [
            {"id": "x", "type": "number", "dimension": "score", "value": 2.0},
        ],
        "requirements": [
            {"id": "R1", "source_kind": "constraint"},
        ],
        "common_rules": [
            {
                "id": "RULE1",
                "expr": {
                    "op": "add",
                    "left": {"op": "ref", "id": "x"},
                    "right": {"op": "const", "type": "number", "dimension": "score", "value": 1.0},
                },
                "output": "y",
                "output_type": "number",
                "output_dimension": "score",
                "consumes_requirements": ["R1"],
                "invariants": [],
            },
        ],
        "branches": [
            {
                "id": "ONLY",
                "when": {"op": "const", "type": "boolean", "dimension": "dimensionless", "value": True},
                "rules": [],
            },
        ],
        "required_outputs": ["y"],
    }
    problem = {
        "initial_facts": [],
        "target_effects": ["METHOD_VERIFIED"],
        "capabilities": [{
            "id": "method",
            "requires": [],
            "provides": ["METHOD_VERIFIED"],
            "cost": 1,
            "result_fields": [],
            "action": {
                "type": "verified_policy",
                "verifier_id": "STRUCTURED_METHOD_EXPRESSION_AST_V2",
                "verifier_payload": {"public": public},
            },
        }],
    }
    out = run(problem, proposal_packets={})
    assert out["pass"] is True, out
    row = out["trace"][0]["verified_output"]
    assert row["outputs"][0]["id"] == "y"
    assert row["outputs"][0]["value"] == 3.0
    assert row["requirement_lineage"][0]["requirement_id"] == "R1"


def test_source_aligned_requirements_compile_and_verify_inside_universal_loop():
    problem = {
        "initial_facts": [],
        "target_effects": ["STRUCTURED_OUTPUT_VERIFIED"],
        "capabilities": [{
            "id": "structured-output",
            "requires": [],
            "provides": ["STRUCTURED_OUTPUT_VERIFIED"],
            "cost": 1,
            "result_fields": [],
            "action": {
                "type": "verified_policy",
                "verifier_id": "SOURCE_ALIGNED_ACCEPTANCE_PROGRAM_V1",
                "verifier_payload": {
                    "source_text": "score must be at least 10. safe must be true.",
                    "source_id": "task",
                    "field_schema": {
                        "score": {"type": "number", "dimension": "score"},
                        "safe": {"type": "boolean", "dimension": "dimensionless"},
                    },
                },
            },
        }],
    }
    out = run(
        problem,
        proposal_packets={
            "structured-output": [{"candidate_values": {"score": 12.0, "safe": True}}],
        },
    )
    assert out["pass"] is True, out


def test_unparsed_normative_requirement_requests_more_information_not_false_success():
    problem = {
        "initial_facts": [],
        "target_effects": ["STRUCTURED_OUTPUT_VERIFIED"],
        "capabilities": [{
            "id": "structured-output",
            "requires": [],
            "provides": ["STRUCTURED_OUTPUT_VERIFIED"],
            "cost": 1,
            "result_fields": [],
            "action": {
                "type": "verified_policy",
                "verifier_id": "SOURCE_ALIGNED_ACCEPTANCE_PROGRAM_V1",
                "verifier_payload": {
                    "source_text": "score must be at least 10. report must explain strategic implications.",
                    "source_id": "task",
                    "field_schema": {
                        "score": {"type": "number", "dimension": "score"},
                    },
                },
            },
        }],
    }
    out = run(
        problem,
        proposal_packets={
            "structured-output": [{"candidate_values": {"score": 12.0}}],
        },
    )
    assert out["status"] == "NEED_MORE_INFORMATION"
    assert "STRUCTURED_OUTPUT_VERIFIED" not in out["verified_facts"]


def _effect_problem():
    return {
        "initial_facts": [],
        "target_effects": ["RECEIPT_WRITTEN_AND_VERIFIED"],
        "capabilities": [{
            "id": "write-receipt",
            "requires": [],
            "provides": ["RECEIPT_WRITTEN_AND_VERIFIED"],
            "cost": 1,
            "result_fields": [],
            "action": {
                "type": "verified_effect_tool",
                "pre_verifier_id": "TYPED_ACCEPTANCE_PROGRAM_V1",
                "pre_verifier_payload": {
                    "program": {
                        "schema": "PROJECT_BRAIN_TYPED_ACCEPTANCE_PROGRAM_SPEC_V1",
                        "fields": [
                            {"id": "name", "type": "enum", "dimension": "dimensionless", "source": "candidate"},
                            {"id": "score", "type": "number", "dimension": "score", "source": "candidate"},
                            {"id": "passed", "type": "boolean", "dimension": "dimensionless", "source": "candidate"},
                        ],
                        "accept_when": {
                            "op": "and",
                            "args": [
                                {
                                    "op": "eq",
                                    "left": {"op": "ref", "id": "name"},
                                    "right": {"op": "const", "type": "enum", "dimension": "dimensionless", "value": "Alice"},
                                },
                                {
                                    "op": "ge",
                                    "left": {"op": "ref", "id": "score"},
                                    "right": {"op": "const", "type": "number", "dimension": "score", "value": 0.5},
                                },
                                {"op": "ref", "id": "passed"},
                            ],
                        },
                    },
                    "trusted_values": {},
                },
                "executor_id": "H100_VERIFIED_EFFECT_TOOL_REGISTRY_V1",
                "executor_payload": {
                    "tool_id": "JSON_RECEIPT_WRITER_V1",
                    "sandbox_rel": "mission-1",
                },
            },
        }],
    }


def test_verified_effect_executes_then_readback_advances_state(tmp_path):
    out = run(
        _effect_problem(),
        proposal_packets={
            "write-receipt": [{
                "candidate_values": {"name": "Alice", "score": 0.75, "passed": True},
            }],
        },
        effect_root=str(tmp_path),
    )
    assert out["pass"] is True, out
    assert "RECEIPT_WRITTEN_AND_VERIFIED" in out["verified_facts"]
    assert (tmp_path / "mission-1" / "receipts" / "result.json").is_file()
    assert out["trace"][0]["effect_outcome_sha256"]


def test_falsified_effect_proposal_never_reaches_carrier(tmp_path):
    out = run(
        _effect_problem(),
        proposal_packets={
            "write-receipt": [{
                "candidate_values": {"name": "Alice", "score": 0.10, "passed": True},
            }],
        },
        effect_root=str(tmp_path),
    )
    assert out["pass"] is False
    assert out["status"] == "ALL_AVAILABLE_PROPOSALS_FALSIFIED"
    assert not (tmp_path / "mission-1" / "receipts" / "result.json").exists()
    assert "RECEIPT_WRITTEN_AND_VERIFIED" not in out["verified_facts"]


def test_effect_that_passes_precheck_still_cannot_run_without_effect_root():
    out = run(
        _effect_problem(),
        proposal_packets={
            "write-receipt": [{
                "candidate_values": {"name": "Alice", "score": 0.75, "passed": True},
            }],
        },
    )
    assert out["pass"] is False
    assert out["status"] == "BLOCKED__EFFECT_ROOT_REQUIRED"
    assert "RECEIPT_WRITTEN_AND_VERIFIED" not in out["verified_facts"]


def test_builtin_finite_search_generates_then_solver_reverifies_candidate():
    problem = {
        "initial_facts": [],
        "target_effects": ["VALUE_VERIFIED"],
        "capabilities": [{
            "id": "choose-value",
            "requires": [],
            "provides": ["VALUE_VERIFIED"],
            "cost": 1,
            "result_fields": [],
            "action": {
                "type": "verified_policy",
                "verifier_id": "TYPED_ACCEPTANCE_PROGRAM_V1",
                "verifier_payload": {
                    "program": {
                        "schema": "PROJECT_BRAIN_TYPED_ACCEPTANCE_PROGRAM_SPEC_V1",
                        "fields": [
                            {"id": "x", "type": "integer", "dimension": "score", "source": "candidate"},
                        ],
                        "accept_when": {
                            "op": "ge",
                            "left": {"op": "ref", "id": "x"},
                            "right": {"op": "const", "type": "number", "dimension": "score", "value": 2},
                        },
                    },
                    "trusted_values": {},
                },
                "proposal_generator_id": "TYPED_ACCEPTANCE_FINITE_SEARCH_V1",
                "proposal_generator_payload": {
                    "candidate_domains": {"x": [0, 1, 2, 3]},
                    "max_candidates": 10,
                },
            },
        }],
    }
    out = run(problem, proposal_packets={})
    assert out["pass"] is True, out
    assert out["trace"][0]["proposal_source"] == "BUILTIN_FINITE_COMPLETE_SEARCH"
    assert out["trace"][0]["accepted_proposal"] == {"candidate_values": {"x": 2}}
    assert out["proposal_searches"][0]["complete_over_declared_domains"] is True
