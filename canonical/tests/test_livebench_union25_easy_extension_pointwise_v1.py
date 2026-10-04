from canonical.runtime import livebench_union25_easy_extension_pointwise_v1 as p


def c(iid, **slots):
    return {"instruction_id": iid, "slots": slots}


def test_placeholders_and_highlights_are_neutral_added_witnesses():
    out = p.solve_contracts([
        c("length_constraints:number_words", num_words=100, relation="less than"),
        c("length_constraints:number_sentences", num_sentences=2, relation="less than"),
        c(p.PLACEHOLDERS, num_placeholders=4),
        c(p.HIGHLIGHTS, num_highlights=4),
    ])
    assert out["status"] == "CANDIDATE_POINTWISE_OPTIMAL_EASY4"
    assert out["sacrificed_instruction_ids"] == []
    assert out["theoretical_max_pass_count"] == 4
    assert out["response"].count("[0]") == 4
    assert out["response"].count("*0*") == 4


def test_neutral_payload_is_inserted_before_mandatory_suffixes():
    out = p.solve_contracts([
        c("detectable_content:postscript", postscript_marker="P.P.S"),
        c("startend:end_checker", end_phrase="Any other questions?"),
        c("startend:quotation"),
        c(p.PLACEHOLDERS, num_placeholders=2),
        c(p.HIGHLIGHTS, num_highlights=2),
    ])
    assert out["status"] == "CANDIDATE_POINTWISE_OPTIMAL_EASY4"
    response = out["response"]
    assert response.startswith('"') and response.endswith('"')
    assert response.strip('"').lower().endswith("any other questions?")
    assert response.lower().find("[0]") < response.lower().find("p.p.s")


def test_repeat_comma_is_exact_one_loss_with_no_comma():
    out = p.solve_contracts([
        c("combination:repeat_prompt", prompt_to_repeat="alpha, beta"),
        c("punctuation:no_comma"),
        c("detectable_format:title"),
    ])
    assert out["status"] == "CANDIDATE_POINTWISE_OPTIMAL_EASY4"
    assert out["sacrificed_instruction_ids"] == [p.NO_COMMA]
    assert out["theoretical_max_pass_count"] == 2
    assert out["proof_shape"]["repeat_comma_collision"] is True


def test_repeat_without_comma_keeps_no_comma():
    out = p.solve_contracts([
        c("combination:repeat_prompt", prompt_to_repeat="alpha beta"),
        c("punctuation:no_comma"),
        c("detectable_format:title"),
    ])
    assert out["status"] == "CANDIDATE_POINTWISE_OPTIMAL_EASY4"
    assert out["sacrificed_instruction_ids"] == []
    assert "," not in out["response"]


def test_constrained_response_is_isolated_singleton():
    out = p.solve_contracts([c(p.CONSTRAINED)])
    assert out["status"] == "CANDIDATE_POINTWISE_OPTIMAL_EASY4"
    assert out["theoretical_max_pass_count"] == 1
    assert "yes" in out["response"].lower()


def test_structurally_forbidden_json_plus_placeholder_fails_closed():
    out = p.solve_contracts([
        c("detectable_format:json_format"),
        c(p.PLACEHOLDERS, num_placeholders=1),
    ])
    assert out["status"] == "FAIL_CLOSED"
    assert out["error"] == "UNION25_STRUCTURAL_CONFLICT_OR_CARDINALITY_VIOLATION"
