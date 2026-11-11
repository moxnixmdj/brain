from canonical.runtime import livebench_legacy15_universal_construction_v1 as proof


def test_universal_construction_reduction():
    out = proof.verify()
    assert out["status"].startswith(
        "PASS__UNIVERSAL_POST_SACRIFICE_CONSTRUCTION_REDUCTION"
    )
    assert out["structural_id_sets"] == 928
    assert out["pointwise_loss_classification_cases"] == 928 * 192 * 2
    assert out["route_partition"] == {
        "JSON": 4,
        "REPEAT_PROMPT": 4,
        "TWO_RESPONSES": 8,
        "GENERAL": 912,
    }
    assert out["post_sacrifice_structural_closure_cases"] == 928 * 4
    assert out["word_upper_bound"] == 48
    assert out["minimum_word_threshold"] == 100
    assert out["minimum_word_safety_margin"] == 52
    assert out["acceptance_credit"] is False


def test_scaffold_hazard_basis_is_explicit():
    assert proof.SCAFFOLD_PUBLIC_WORD_HAZARDS == {
        "section", "other", "anything", "can", "help"
    }
    assert proof.END_PUBLIC_WORD_HAZARDS == {
        "other", "anything", "can", "help"
    }
