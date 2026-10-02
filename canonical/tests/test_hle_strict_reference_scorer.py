from canonical.runtime.hle_strict_reference_scorer import (
    extract_declared_answer,
    score_predictions,
    strict_reference_verdict,
)

def test_exact_reference_passes():
    v = strict_reference_verdict("Explanation: reason\nAnswer: canonical\nConfidence: 77%", "canonical")
    assert v.correct is True

def test_semantic_or_numeric_leniency_is_not_granted():
    assert strict_reference_verdict("Answer: four", "4").correct is False
    assert strict_reference_verdict("Answer: 0.5", "1/2").correct is False

def test_multiple_answer_lines_fail_closed():
    answer, reason = extract_declared_answer("Answer: A\nAnswer: B")
    assert answer is None
    assert reason == "ANSWER_LINE_COUNT_2"

def test_missing_prediction_is_wrong():
    r = score_predictions({}, [{"id": "q1", "answer": "A"}])
    assert r["accuracy_percent"] == 0.0
    assert r["rows"][0]["reason"] == "MISSING_PREDICTION"

def test_score_is_reference_exactness_not_official_judge_claim():
    r = score_predictions(
        {"q1": "Answer: A", "q2": "Answer: C"},
        [{"id": "q1", "answer": "A"}, {"id": "q2", "answer": "B"}],
    )
    assert r["accuracy_percent"] == 50.0
    assert r["official_score_equivalence_claimed"] is False
