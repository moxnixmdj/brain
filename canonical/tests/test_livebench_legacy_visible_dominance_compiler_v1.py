from canonical.runtime.livebench_legacy_visible_dominance_compiler_v1 import (
    IntegerInterval, parse_visible_intervals, prove_visible_implies_scorer, scorer_interval
)

def test_scorer_intervals():
    assert scorer_interval("at least", 5).to_dict()["lower"] == 5
    assert scorer_interval("less than", 5).to_dict()["upper"] == 4
    assert scorer_interval("exactly", 5).to_dict()["upper"] == 5

def test_off_by_one_equivalence_words_at_most():
    r=prove_visible_implies_scorer(
        "Respond with at most 150 words.",
        "words","less than",151
    )
    assert r["status"]=="PROVED"
    assert r["equivalent"] is True

def test_off_by_one_equivalence_sentences_more_than():
    r=prove_visible_implies_scorer(
        "Have more than 30 sentences in your response.",
        "sentences","at least",31
    )
    assert r["status"]=="PROVED"
    assert r["equivalent"] is True

def test_visible_stronger_dominates_hidden():
    r=prove_visible_implies_scorer(
        "Your response must be at least 400 words.",
        "words","at least",336
    )
    assert r["status"]=="PROVED"
    assert r["strictly_stronger_visible"] is True

def test_visible_weaker_does_not_prove_hidden():
    r=prove_visible_implies_scorer(
        "Use at least 300 words.",
        "words","at least",400
    )
    assert r["status"]=="UNPROVED"
    assert r["visible_implies_scorer"] is False

def test_upper_bound_stronger_dominates():
    r=prove_visible_implies_scorer(
        "Use fewer than 5 sentences.",
        "sentences","less than",6
    )
    assert r["status"]=="PROVED"
    assert r["strictly_stronger_visible"] is True

def test_exact_bullet_parse():
    r=parse_visible_intervals("Your answer must contain exactly 6 bullet points.","bullets")
    assert r["status"]=="PASS"
    assert r["intersection"]["lower"]==6
    assert r["intersection"]["upper"]==6

def test_contradiction_fails_closed():
    r=parse_visible_intervals(
      "Use at least 10 words but less than 5 words.","words"
    )
    assert r["status"]=="CONTRADICTION"

def test_unrelated_number_not_bound():
    r=parse_visible_intervals(
      "In 2026 write a concise answer.","words"
    )
    assert r["status"]=="NO_MATCH"
