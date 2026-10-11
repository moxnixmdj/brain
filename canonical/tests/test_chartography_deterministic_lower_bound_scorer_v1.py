from canonical.runtime.chartography_deterministic_lower_bound_scorer_v1 import score_lower_bound

def test_exact_text_and_case_whitespace():
    assert score_lower_bound("Alpha", " alpha ").score == 1
    assert score_lower_bound("Alpha", "Beta").score == 0

def test_explicit_range_pass_and_edges():
    for x in ["140 mph","145 mph","150 mph"]:
        assert score_lower_bound("150 mph, acceptable range 140 to 150 mph",x).score == 1
    assert score_lower_bound("150 mph, acceptable range 140 to 150 mph","139 mph").score == 0
    assert score_lower_bound("150 mph, acceptable range 140 to 150 mph","151 mph").score == 0

def test_range_requires_marker_and_single_scalar():
    assert score_lower_bound("values 140-150 mph","145 mph").score == 0
    assert score_lower_bound("150 mph, acceptable range 140 to 150 mph","145 mph or 146 mph").score == 0

def test_unit_binding_fail_closed():
    assert score_lower_bound("150 mph, acceptable range 140 to 150 mph","145 km/h").score == 0
    assert score_lower_bound("150 mph, acceptable range 140 to 150 mph","145").score == 0

def test_cannot_determine():
    assert score_lower_bound("Cannot be determined from the chart","cannot be determined from the chart").score == 1
    assert score_lower_bound("Cannot be determined from the chart","unknown").score == 0

def test_no_fuzzy_or_partial_credit():
    assert score_lower_bound("A and B","A").score == 0
    assert score_lower_bound("North, South","South, North").score == 0
    assert score_lower_bound("4.2 million","4,200,000").score == 0  # sound but intentionally stricter

def test_adversarial_numbers_in_explanation_do_not_pass():
    g="150 mph, acceptable range 140 to 150 mph"
    assert score_lower_bound(g,"I considered 145 and 155 mph; final answer 145 mph").score == 0
    assert score_lower_bound(g,"145 mph because the chart spans 100 to 200").score == 0
