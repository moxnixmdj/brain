from canonical.runtime import livebench_legacy15_universal_construction_reduction_v1 as r


def test_universal_construction_reduction_is_fail_closed_and_zero_credit():
    out = r.verify()
    assert out["status"] == (
        "PASS__UNIVERSAL_POST_SACRIFICE_CONSTRUCTION_REDUCED_TO_"
        "FOUR_CONTENT_ADDRESSED_SOURCE_LOCAL_LEMMAS"
    )
    assert out["reduction_basis"] == {
        "structural_id_sets": 928,
        "lexical_signatures": 192,
        "minimum_cut_classification_cases": 928 * 192 * 2,
        "mandatory_loss_coordinates": 2,
        "pointwise_exact_checker_matches_already_observed": 12489,
        "raw_slot_cartesian_required": False,
    }
    assert len(out["lemmas"]) == 4
    assert {x["id"] for x in out["lemmas"]} == {
        "L1_FORBIDDEN_ALPHA_SURFACE",
        "L2_WORD_COUNT_PARAMETRIC_TOTALITY",
        "L3_SENTENCE_PARAMETRIC_TOTALITY",
        "L4_SPECIAL_ROUTE_TOTALITY",
    }
    assert out["next_independent_discharge"]["required"] is True
    assert out["acceptance_credit"] is False
    assert out["capability_credit"] is False
    assert out["ownership_credit"] is False
    assert out["terminal_rows_read"] == 0
    assert out["hidden_kwargs_read"] == 0


def test_fixed_literal_collision_basis_is_exactly_partitioned():
    assert r.FIXED_LITERAL_WORDLIST_INTERSECTION == {
        "section", "other", "anything", "can", "help"
    }
    assert r.END_COLLISION_WORDS == {"other", "anything", "can", "help"}
    assert r.BOUNDARY_SHIELDED_FIXED_WORDS == {"section"}
    assert r.FIXED_LITERAL_WORDLIST_INTERSECTION == (
        r.END_COLLISION_WORDS | r.BOUNDARY_SHIELDED_FIXED_WORDS
    )
