from canonical.runtime import livebench_legacy15_slot_feasibility_v2 as f


def test_sentence_less_than_one_plus_public_end_phrase_is_unsat():
    out = f.classify_visible_contracts([
        {
            "instruction_id": f.SENTENCE,
            "slots": {"num_sentences": 1, "relation": "less than"},
        },
        {
            "instruction_id": f.END,
            "slots": {"end_phrase": "Any other questions?"},
        },
    ])
    assert out["status"] == "PROVED_UNSAT"
    assert out["hard_unsat_reasons"] == [
        "LESS_THAN_ONE_SENTENCE_WITH_MANDATORY_PUBLIC_END_PHRASE"
    ]


def test_second_public_end_phrase_is_also_unsat():
    out = f.classify_visible_contracts([
        {
            "instruction_id": f.SENTENCE,
            "slots": {"num_sentences": 1, "relation": "less than"},
        },
        {
            "instruction_id": f.END,
            "slots": {"end_phrase": "Is there anything else I can help with?"},
        },
    ])
    assert out["status"] == "PROVED_UNSAT"


def test_threshold_two_is_not_falsely_certified():
    out = f.classify_visible_contracts([
        {
            "instruction_id": f.SENTENCE,
            "slots": {"num_sentences": 2, "relation": "less than"},
        },
        {
            "instruction_id": f.END,
            "slots": {"end_phrase": "Any other questions?"},
        },
    ])
    assert out["status"] == "ID_COMPATIBLE__SLOT_FEASIBILITY_NOT_YET_PROVED"
    assert out["hard_unsat_reasons"] == []


def test_non_generator_end_phrase_does_not_receive_v2_certificate():
    out = f.classify_visible_contracts([
        {
            "instruction_id": f.SENTENCE,
            "slots": {"num_sentences": 1, "relation": "less than"},
        },
        {
            "instruction_id": f.END,
            "slots": {"end_phrase": "x"},
        },
    ])
    assert out["status"] == "ID_COMPATIBLE__SLOT_FEASIBILITY_NOT_YET_PROVED"


def test_v1_unsat_classes_are_preserved():
    out = f.classify_visible_contracts([
        {
            "instruction_id": "length_constraints:nth_paragraph_first_word",
            "slots": {
                "num_paragraphs": 2,
                "nth_paragraph": 1,
                "first_word": "alpha",
            },
        },
        {
            "instruction_id": "keywords:forbidden_words",
            "slots": {"forbidden_words": ["alpha"]},
        },
    ])
    assert out["status"] == "PROVED_UNSAT"
    assert "NTH_FIRST_WORD_IS_FORBIDDEN_WORD" in out["hard_unsat_reasons"]


def test_proof_entrypoint_is_zero_terminal_and_zero_credit():
    out = f.prove_sentence_end_unsat()
    assert out["status"] == "PASS__THIRD_PUBLIC_SLOT_UNSAT_CLASS_CERTIFIED"
    assert out["terminal_data_used"] is False
    assert out["hidden_kwargs_used"] is False
    assert out["acceptance_credit"] is False
