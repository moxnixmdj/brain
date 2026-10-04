from canonical.runtime import livebench_legacy15_pointwise_solver_v1 as solver


def _compiled_forbidden():
    return {
        "schema": "TEST_COMPILER",
        "status": "PASS",
        "constraints": [
            {
                "instruction_id": "keywords:forbidden_words",
                "slots": {"forbidden_words": ["omega"]},
                "parameter_complete": True,
            }
        ],
    }


def _certified(response="alpha"):
    return {
        "status": "PASS__POINTWISE_OPTIMAL_CANDIDATE_CERTIFIED",
        "pointwise_optimal": True,
        "best_candidate": {"response": response, "checker_results": [True]},
        "certificate": {"required_next_cardinality_subset_count": 0},
        "exact_checker_binding": {
            "livebench_commit": solver.exact_checker.PINNED_LIVEBENCH_COMMIT,
            "instructions_blob": solver.exact_checker.PINNED_INSTRUCTIONS_BLOB,
            "registry_blob": solver.exact_checker.PINNED_REGISTRY_BLOB,
            "instructions_util_blob": solver.exact_checker.PINNED_UTIL_BLOB,
            "evaluation_main_blob": solver.exact_checker.PINNED_EVALUATION_MAIN_BLOB,
            "strict_nonempty_response_gate_bound": True,
        },
    }


def test_prompt_to_certified_response_pipeline(monkeypatch):
    monkeypatch.setattr(
        solver.compiler,
        "compile_visible_constraints",
        lambda prompt: _compiled_forbidden(),
    )
    monkeypatch.setattr(
        solver.pointwise,
        "solve_with_pinned_livebench",
        lambda *args, **kwargs: _certified(),
    )

    out = solver.solve_prompt("visible prompt", "/fake/livebench")
    assert out["status"] == "PASS__POINTWISE_OPTIMAL_RESPONSE_CERTIFIED"
    assert out["pointwise_optimal"] is True
    assert out["response"] == "alpha"
    assert out["search"]["certificate"]["required_next_cardinality_subset_count"] == 0
    assert out["pinned_source_binding"]["evaluation_main_blob"] == (
        solver.exact_checker.PINNED_EVALUATION_MAIN_BLOB
    )
    assert out["case_frequency_used"] is False
    assert out["comparator_response_used"] is False


def test_compiler_failure_never_reaches_exact_pointwise_solver(monkeypatch):
    monkeypatch.setattr(
        solver.compiler,
        "compile_visible_constraints",
        lambda prompt: {"status": "FAIL_CLOSED", "error": "bad envelope"},
    )

    called = {"pointwise": False}

    def impossible(*args, **kwargs):
        called["pointwise"] = True
        raise AssertionError("pointwise solver must not run")

    monkeypatch.setattr(solver.pointwise, "solve_with_pinned_livebench", impossible)
    out = solver.solve_prompt("bad", "/fake/livebench")
    assert out["status"] == "FAIL_CLOSED"
    assert out["response"] is None
    assert called["pointwise"] is False


def test_source_binding_failure_fails_closed(monkeypatch):
    monkeypatch.setattr(
        solver.compiler,
        "compile_visible_constraints",
        lambda prompt: _compiled_forbidden(),
    )

    def drift(*args, **kwargs):
        raise solver.exact_checker.ExactPostvalidationError(
            "PINNED_CHECKER_BLOB_MISMATCH:evaluation_main.py"
        )

    monkeypatch.setattr(solver.pointwise, "solve_with_pinned_livebench", drift)
    out = solver.solve_prompt("visible prompt", "/fake/livebench")
    assert out["status"] == "FAIL_CLOSED"
    assert out["response"] is None
    assert "evaluation_main.py" in out["error"]


def test_uncertified_search_never_emits_response(monkeypatch):
    monkeypatch.setattr(
        solver.compiler,
        "compile_visible_constraints",
        lambda prompt: _compiled_forbidden(),
    )
    monkeypatch.setattr(
        solver.pointwise,
        "solve_with_pinned_livebench",
        lambda *args, **kwargs: {
            "status": "FAIL_CLOSED__BEST_CANDIDATE_OPTIMALITY_NOT_CERTIFIED",
            "pointwise_optimal": False,
            "best_candidate": {"response": "must-not-escape"},
            "exact_checker_binding": {
                "evaluation_main_blob": solver.exact_checker.PINNED_EVALUATION_MAIN_BLOB
            },
        },
    )

    out = solver.solve_prompt("visible prompt", "/fake/livebench")
    assert out["status"] == "FAIL_CLOSED"
    assert out["response"] is None
    assert out["search"]["best_candidate"]["response"] == "must-not-escape"
