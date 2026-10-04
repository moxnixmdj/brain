import math

from canonical.runtime import livebench_legacy15_pointwise_optimal_v1 as o
from canonical.runtime import livebench_legacy15_contract_composer_v2 as c


def C(iid, **slots):
    return {"instruction_id": iid, "slots": slots}


def test_satisfiable_case_targets_full_score():
    out = o.solve_contracts([
        C(c.EXIST, keywords=["brain", "proof", "signal", "world", "analysis"]),
        C(c.FORBIDDEN, forbidden_words=["brain", "proof", "signal", "world", "analysis"]),
    ])
    assert out["status"] == "CANDIDATE_POINTWISE_OPTIMAL"
    assert out["sacrificed_instruction_ids"] == []
    assert out["theoretical_max_pass_count"] == 2
    assert out["theoretical_pointwise_optimum_strict_score"] == 1.0


def test_sentence_zero_singleton_has_zero_theoretical_max_score():
    out = o.solve_contracts([
        C(c.SENTENCES, num_sentences=1, relation="less than"),
    ])
    assert out["status"] == "CANDIDATE_POINTWISE_OPTIMAL"
    assert out["sacrificed_instruction_ids"] == [c.SENTENCES]
    assert out["theoretical_max_pass_count"] == 0
    assert out["theoretical_pointwise_optimum_strict_score"] == 0.0
    assert out["response"].strip()


def test_nth_forbidden_collision_drops_shared_forbidden_checker():
    out = o.solve_contracts([
        C(c.NTH, num_paragraphs=2, nth_paragraph=1, first_word="brain"),
        C(c.FORBIDDEN, forbidden_words=["brain"]),
    ])
    assert out["status"] == "CANDIDATE_POINTWISE_OPTIMAL"
    assert out["sacrificed_instruction_ids"] == [c.FORBIDDEN]
    assert out["theoretical_max_pass_count"] == 1
    assert math.isclose(out["theoretical_pointwise_optimum_strict_score"], 0.25)


def test_two_forbidden_collisions_still_cost_only_one_checker():
    out = o.solve_contracts([
        C(c.NTH, num_paragraphs=2, nth_paragraph=1, first_word="other"),
        C(c.END, end_phrase="Any other questions?"),
        C(c.FORBIDDEN, forbidden_words=["other"]),
    ])
    assert out["status"] == "CANDIDATE_POINTWISE_OPTIMAL"
    assert out["sacrificed_instruction_ids"] == [c.FORBIDDEN]
    assert out["theoretical_max_pass_count"] == 2
    assert math.isclose(out["theoretical_pointwise_optimum_strict_score"], 1.0 / 3.0)


def test_sentence_zero_plus_forbidden_cluster_has_two_mandatory_losses():
    out = o.solve_contracts([
        C(c.SENTENCES, num_sentences=1, relation="less than"),
        C(c.END, end_phrase="Any other questions?"),
        C(c.FORBIDDEN, forbidden_words=["other"]),
        C(c.TITLE),
    ])
    assert out["status"] == "CANDIDATE_POINTWISE_OPTIMAL"
    assert out["sacrificed_instruction_ids"] == sorted([c.SENTENCES, c.FORBIDDEN])
    assert out["theoretical_max_pass_count"] == 2
    assert math.isclose(out["theoretical_pointwise_optimum_strict_score"], 0.25)


def test_score_formula_matches_livebench_shape():
    assert o.strict_score_from_pass_count(5, 5) == 1.0
    assert o.strict_score_from_pass_count(5, 4) == 0.4
    assert o.strict_score_from_pass_count(2, 1) == 0.25


def test_sentence_zero_multi_constraint_reason_family_is_recognized():
    out = o.solve_contracts([
        C(c.SENTENCES, num_sentences=1, relation="less than"),
        C(c.EXIST, keywords=["brain", "proof", "signal", "world", "analysis"]),
        C(c.TITLE),
    ])
    assert out["status"] == "CANDIDATE_POINTWISE_OPTIMAL"
    assert out["sacrificed_instruction_ids"] == [c.SENTENCES]
    assert out["theoretical_max_pass_count"] == 2
    assert math.isclose(out["theoretical_pointwise_optimum_strict_score"], 1.0 / 3.0)
