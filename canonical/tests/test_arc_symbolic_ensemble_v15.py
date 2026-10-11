from canonical.runtime.arc_symbolic_ensemble_v15 import solve_task


def test_identity_candidate_is_demo_verified_and_model_free():
    task = {
        "train": [
            {"input": [[1, 0], [0, 2]], "output": [[1, 0], [0, 2]]},
            {"input": [[3, 3], [0, 0]], "output": [[3, 3], [0, 0]]},
        ],
        "test": [{"input": [[4, 0], [0, 5]]}],
    }
    out = solve_task(task)
    assert out["status"] == "CANDIDATES"
    assert out["detector_count"] == 321
    assert out["all_candidates_demo_verified"] is True
    assert out["external_model_used"] is False
    assert [[4, 0], [0, 5]] in out["predictions"][0]


def test_invalid_task_fails_closed():
    out = solve_task({"train": [], "test": []})
    assert out["status"] == "FAIL_CLOSED"
    assert out["external_model_used"] is False
