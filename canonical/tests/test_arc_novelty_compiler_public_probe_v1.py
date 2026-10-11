from canonical.evaluation.arc_novelty_compiler_public_probe_v1 import evaluate_task


def test_two_attempt_and_oracle_success_on_rotation():
    task = {
        "train": [
            {"input": [[1, 0], [1, 1]], "output": [[1, 1], [1, 0]]},
            {"input": [[2, 2, 0], [0, 2, 0]], "output": [[0, 2], [2, 2], [0, 0]]},
        ],
        "test": [
            {"input": [[3, 0], [3, 3]], "output": [[3, 3], [3, 0]]},
        ],
    }
    out = evaluate_task(task)
    assert out["status"] == "SCORED"
    assert out["two_attempt_solved"] is True
    assert out["grammar_oracle_solved"] is True


def test_no_hypothesis_is_scored_as_unsolved_not_invalid():
    task = {
        "train": [{"input": [[1, 0], [0, 0]], "output": [[1, 1], [1, 1], [1, 1]]}],
        "test": [{"input": [[2]], "output": [[2, 2]]}],
    }
    out = evaluate_task(task)
    assert out["status"] == "SCORED"
    assert out["hypothesis_count"] == 0
    assert out["two_attempt_solved"] is False
    assert out["grammar_oracle_solved"] is False
