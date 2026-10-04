import re

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


def test_prompt_to_certified_response_pipeline(monkeypatch):
    monkeypatch.setattr(
        solver.compiler,
        "compile_visible_constraints",
        lambda prompt: _compiled_forbidden(),
    )
    monkeypatch.setattr(
        solver.exact_checker,
        "verify_pinned_source",
        lambda root: {
            "status": "PASS__EXACT_PINNED_CHECKER_SOURCE_BOUND",
            "registry_git_blob_sha": solver.exact_checker.PINNED_REGISTRY_BLOB,
            "instructions_git_blob_sha": solver.exact_checker.PINNED_INSTRUCTIONS_BLOB,
        },
    )

    def checker(response, contracts):
        return (re.search(r"\bomega\b", response, re.I) is None,)

    monkeypatch.setattr(
        solver.exact_checker,
        "checker_for_root",
        lambda root: checker,
    )

    out = solver.solve_prompt("visible prompt", "/fake/livebench")
    assert out["status"] == "PASS__POINTWISE_OPTIMAL_RESPONSE_CERTIFIED"
    assert out["pointwise_optimal"] is True
    assert isinstance(out["response"], str)
    assert re.search(r"\bomega\b", out["response"], re.I) is None
    assert out["search"]["certificate"]["required_next_cardinality_subset_count"] == 0
    assert out["case_frequency_used"] is False
    assert out["comparator_response_used"] is False


def test_compiler_failure_never_reaches_checker(monkeypatch):
    monkeypatch.setattr(
        solver.compiler,
        "compile_visible_constraints",
        lambda prompt: {"status": "FAIL_CLOSED", "error": "bad envelope"},
    )

    called = {"checker": False}

    def impossible(root):
        called["checker"] = True
        raise AssertionError("checker must not load")

    monkeypatch.setattr(solver.exact_checker, "checker_for_root", impossible)
    out = solver.solve_prompt("bad", "/fake/livebench")
    assert out["status"] == "FAIL_CLOSED"
    assert out["response"] is None
    assert called["checker"] is False


def test_source_binding_failure_fails_closed(monkeypatch):
    monkeypatch.setattr(
        solver.compiler,
        "compile_visible_constraints",
        lambda prompt: _compiled_forbidden(),
    )

    def drift(root):
        raise solver.exact_checker.ExactContractCheckerError("REGISTRY_BLOB_DRIFT")

    monkeypatch.setattr(solver.exact_checker, "verify_pinned_source", drift)
    out = solver.solve_prompt("visible prompt", "/fake/livebench")
    assert out["status"] == "FAIL_CLOSED"
    assert out["response"] is None
    assert "REGISTRY_BLOB_DRIFT" in out["error"]


def test_uncertified_search_never_emits_response(monkeypatch):
    monkeypatch.setattr(
        solver.compiler,
        "compile_visible_constraints",
        lambda prompt: _compiled_forbidden(),
    )
    monkeypatch.setattr(
        solver.exact_checker,
        "verify_pinned_source",
        lambda root: {"status": "PASS__EXACT_PINNED_CHECKER_SOURCE_BOUND"},
    )
    monkeypatch.setattr(
        solver.exact_checker,
        "checker_for_root",
        lambda root: (lambda response, contracts: (True,)),
    )
    monkeypatch.setattr(
        solver.pointwise,
        "solve_with_checker",
        lambda *args, **kwargs: {
            "status": "FAIL_CLOSED__BEST_CANDIDATE_OPTIMALITY_NOT_CERTIFIED",
            "pointwise_optimal": False,
            "best_candidate": {"response": "must-not-escape"},
        },
    )

    out = solver.solve_prompt("visible prompt", "/fake/livebench")
    assert out["status"] == "FAIL_CLOSED"
    assert out["response"] is None
    assert out["search"]["best_candidate"]["response"] == "must-not-escape"
