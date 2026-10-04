from canonical.runtime import livebench_legacy_visible_constraint_compiler_v3 as v3


def test_repeated_keyword_frequency_instances_are_preserved():
    prompt = (
        "In your response, the word war should appear at least 8 times. "
        "In your response, the word peace should appear at least 10 times."
    )
    out = v3.compile_visible_constraints(prompt)
    rows = [
        c for c in out["constraints"]
        if c["instruction_id"] == "keywords:frequency"
    ]
    assert out["status"] == "PASS"
    assert len(rows) == 2
    assert out["duplicate_instruction_id_counts"] == {"keywords:frequency": 2}
    assert [r["slots"]["keyword"] for r in rows] == ["war", "peace"]
    assert [r["slots"]["frequency"] for r in rows] == [8, 10]


def test_repeated_sentence_constraints_are_not_rejected():
    prompt = (
        "Your response should contain at least 20 sentences. "
        "Your response should contain less than 26 sentences."
    )
    out = v3.compile_visible_constraints(prompt)
    rows = [
        c for c in out["constraints"]
        if c["instruction_id"] == "length_constraints:number_sentences"
    ]
    assert out["status"] == "PASS"
    assert len(rows) == 2
    assert out["duplicate_instruction_id_counts"] == {
        "length_constraints:number_sentences": 2
    }


def test_no_hidden_or_terminal_data_authority_added():
    out = v3.compile_visible_constraints(
        "In your response, the word alpha should appear at least 2 times."
    )
    assert out["terminal_data_used"] is False
    assert out["hidden_instruction_ids_used"] is False
    assert out["hidden_kwargs_used"] is False
    assert out["terminal_case_content_used"] is False
    assert out["model_dependency_count"] == 0
    assert out["network_used"] is False
