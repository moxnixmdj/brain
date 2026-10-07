from canonical.runtime.universal_structured_task_v1 import solve


def task():
    return {
        "source_text": 'name must equal "Alice". score must be at least 0.5. passed must be true.',
        "source_id": "task",
        "field_schema": {
            "name": {"type": "enum", "dimension": "dimensionless"},
            "score": {"type": "number", "dimension": "score"},
            "passed": {"type": "boolean", "dimension": "dimensionless"},
        },
        "candidate_domains": {
            "name": ["Alice", "Bob"],
            "score": [0.10, 0.75],
            "passed": [False, True],
        },
        "target_effect": "RESULT_VERIFIED",
        "effect": {
            "tool_id": "JSON_RECEIPT_WRITER_V1",
            "sandbox_rel": "structured-task",
        },
    }


def test_raw_requirements_to_search_verify_effect_readback_and_episode_candidate(tmp_path):
    out = solve(task(), effect_root=tmp_path)
    assert out["pass"] is True, out
    solver = out["solver_result"]
    assert solver["pass"] is True
    assert solver["trace"][0]["proposal_source"] == "BUILTIN_FINITE_COMPLETE_SEARCH"
    assert solver["trace"][0]["accepted_proposal"]["candidate_values"] == {
        "name": "Alice", "score": 0.75, "passed": True
    }
    assert (tmp_path / "structured-task" / "receipts" / "result.json").is_file()
    assert solver["state_target_verdict"]["pass"] is True
    assert out["episode_candidate"]["reuse_authorized"] is False


def test_unsupported_normative_language_blocks_before_search_or_effect(tmp_path):
    x = task()
    x["source_text"] += " report must explain strategic implications."
    out = solve(x, effect_root=tmp_path)
    assert out["pass"] is False
    assert out["status"] == "UNRESOLVED__ACCEPTANCE_PROGRAM_NOT_COMPILED"
    assert not (tmp_path / "structured-task" / "receipts" / "result.json").exists()


def test_no_accepted_candidate_means_no_effect(tmp_path):
    x = task()
    x["candidate_domains"]["score"] = [0.10]
    out = solve(x, effect_root=tmp_path)
    assert out["pass"] is False
    assert out["solver_result"]["status"] == "NO_PROPOSAL_IN_DECLARED_FINITE_SEARCH_DOMAIN"
    assert not (tmp_path / "structured-task" / "receipts" / "result.json").exists()


def test_success_does_not_self_promote_learned_skill(tmp_path):
    out = solve(task(), effect_root=tmp_path)
    assert out["pass"] is True
    assert out["episode_reuse_authorized"] is False
    assert out["episode_candidate"]["parameterization_claimed"] is False
