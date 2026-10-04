from canonical.runtime import livebench_legacy15_universal_construction_reduction_v1 as proof


def test_universal_post_sacrifice_construction_reduction_closes_raw_cartesian_gap():
    out = proof.verify()
    assert out["status"].startswith("PASS__UNIVERSAL_POST_SACRIFICE_CONSTRUCTION")
    assert out["structural_id_sets"] == 928
    assert out["lexical_signatures"] == 192
    assert out["proof_lemmas"]["word_less_than_global_ceiling"] == 48
    assert out["proof_lemmas"]["word_less_than_public_minimum"] == 100
    assert out["proof_lemmas"]["word_less_than_minimum_margin"] == 52
    assert out["proof_lemmas"]["sentence_numeric_classes"] == 3
    assert out["acceptance_credit"] is False


def test_special_branch_partner_sets_are_exactly_conflict_isolated():
    out = proof.verify()["special_branch_partner_unions"]
    assert set(out["detectable_format:json_format"]) == {
        "detectable_format:json_format",
        "keywords:existence",
        "keywords:forbidden_words",
    }
    assert set(out["combination:repeat_prompt"]) == {
        "combination:repeat_prompt",
        "keywords:existence",
        "detectable_format:title",
    }
    assert set(out["combination:two_responses"]) == {
        "combination:two_responses",
        "keywords:existence",
        "keywords:forbidden_words",
        "detectable_format:title",
    }
