from canonical.runtime import livebench_legacy15_slot_feasibility_v1 as f


def test_id_compatibility_is_not_slot_satisfiability():
    out = f.prove_id_compatibility_is_not_satisfiability()
    assert out["status"] == "PASS__ID_COMPATIBILITY_STRICTLY_WEAKER_THAN_SLOT_SATISFIABILITY"
    assert out["counterexample_archetype"] == "NTH_PARAGRAPH"
    assert "NTH_FIRST_WORD_IS_FORBIDDEN_WORD" in out["hard_unsat_reasons"]
    assert out["terminal_data_used"] is False
    assert out["hidden_kwargs_used"] is False
    assert out["acceptance_credit"] is False


def test_nth_first_word_forbidden_collision_is_certified():
    contracts = [
        {
            "instruction_id": f.NTH,
            "slots": {
                "num_paragraphs": 3,
                "nth_paragraph": 2,
                "first_word": "Harbor",
            },
        },
        {
            "instruction_id": f.FORBIDDEN,
            "slots": {"forbidden_words": ["delta", "harbor"]},
        },
    ]
    out = f.classify_visible_contracts(contracts)
    assert out["status"] == "PROVED_UNSAT"
    assert out["archetype"] == "NTH_PARAGRAPH"
    assert out["hard_unsat_reasons"] == ["NTH_FIRST_WORD_IS_FORBIDDEN_WORD"]


def test_distinct_nth_first_word_is_not_falsely_promoted_to_sat():
    contracts = [
        {
            "instruction_id": f.NTH,
            "slots": {
                "num_paragraphs": 3,
                "nth_paragraph": 2,
                "first_word": "harbor",
            },
        },
        {
            "instruction_id": f.FORBIDDEN,
            "slots": {"forbidden_words": ["delta", "ember"]},
        },
    ]
    out = f.classify_visible_contracts(contracts)
    assert out["status"] == "ID_COMPATIBLE__SLOT_FEASIBILITY_NOT_YET_PROVED"
    assert out["hard_unsat_reasons"] == []


def test_mandatory_end_phrase_forbidden_collision_is_certified():
    contracts = [
        {
            "instruction_id": f.END,
            "slots": {"end_phrase": "Any other questions?"},
        },
        {
            "instruction_id": f.FORBIDDEN,
            "slots": {"forbidden_words": ["other"]},
        },
    ]
    out = f.classify_visible_contracts(contracts)
    assert out["status"] == "PROVED_UNSAT"
    assert out["hard_unsat_reasons"] == [
        "MANDATORY_END_PHRASE_CONTAINS_FORBIDDEN_WORD:other"
    ]


def test_unknown_or_structurally_conflicting_ids_fail_closed():
    unknown = f.classify_visible_contracts([
        {"instruction_id": "not:a_real_checker", "slots": {}},
    ])
    assert unknown["status"] == "FAIL_CLOSED_ID_CONFLICT"

    conflict = f.classify_visible_contracts([
        {"instruction_id": "detectable_format:json_format", "slots": {}},
        {"instruction_id": "length_constraints:number_words", "slots": {"num_words": 100, "relation": "at least"}},
    ])
    assert conflict["status"] == "FAIL_CLOSED_ID_CONFLICT"


def test_sentence_one_end_phrase_contradiction():
    contracts = [
        {"instruction_id": f.SENTENCE, "slots": {"num_sentences": 1, "relation": "less than"}},
        {"instruction_id": f.END, "slots": {"end_phrase": "Any other questions?"}},
    ]
    out = f.classify_visible_contracts(contracts)
    assert out["status"] == "PROVED_UNSAT"
    assert "SENTENCE_LT_ONE_WITH_MANDATORY_END_PHRASE" in out["hard_unsat_reasons"]
