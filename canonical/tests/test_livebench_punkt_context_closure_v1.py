from canonical.runtime import livebench_punkt_context_closure_v1 as p


def test_sentence_context_surface_is_nonempty_and_total():
    out = p.run()
    assert out["status"] == "READY_FOR_EXACT_PINNED_PUNKT_VERIFICATION"
    assert out["sentence_structural_id_sets"] > 0
    assert out["planned_context_cases"] > out["sentence_structural_id_sets"]
    assert out["satisfiable_sentence_slot_states"] == 39
    assert out["acceptance_credit"] is False


def test_no_forbidden_route_can_coexist_with_sentence():
    for ids in p.sentence_id_sets():
        assert p.comp.PARAGRAPHS not in ids
        assert p.comp.JSON_ID not in ids
        assert p.comp.REPEAT not in ids
        assert p.comp.TWO not in ids


def test_strict_lt_one_is_bound_to_exact_unsat_reason():
    reasons = p.feas.hard_unsat_reasons([
        {"instruction_id": p.comp.SENTENCES, "slots": {
            "num_sentences": 1, "relation": "less than"
        }}
    ])
    assert "STRICT_NONEMPTY_RESPONSE_IMPLIES_AT_LEAST_ONE_PUNKT_SENTENCE" in reasons
