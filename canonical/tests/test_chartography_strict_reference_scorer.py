from canonical.runtime.chartography_strict_reference_scorer import strict_reference_verdict, score_predictions

def test_exact_golden_answer_passes():
    assert strict_reference_verdict("  exact answer\n","exact answer").correct is True

def test_official_leniency_is_deliberately_not_granted():
    assert strict_reference_verdict("4.2 million","4,200,000").correct is False
    assert strict_reference_verdict("31 pp","31 percentage points").correct is False

def test_explanation_wrapping_exact_answer_fails_strictly():
    assert strict_reference_verdict("Reasoning...\n42","42").correct is False

def test_missing_prediction_is_wrong():
    r=score_predictions({},[{"id":"q","golden_answer":"A"}])
    assert r["accuracy_percent"]==0.0

def test_no_official_judge_equivalence_claim():
    r=score_predictions({"q":"A"},[{"id":"q","golden_answer":"A"}])
    assert r["accuracy_percent"]==100.0
    assert r["official_judge_output_equivalence_claimed"] is False
