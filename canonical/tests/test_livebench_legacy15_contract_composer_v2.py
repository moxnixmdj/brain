import re

from canonical.runtime import livebench_legacy15_contract_composer_v2 as c


def C(iid, **slots):
    return {"instruction_id": iid, "slots": slots}


def test_json_overlap_is_shielded_not_misclassified_unsat():
    out = c.compose_contracts([
        C(c.JSON_ID),
        C(c.EXIST, keywords=["brain", "proof"]),
        C(c.FORBIDDEN, forbidden_words=["brain", "proof", "section"]),
    ])
    assert out["status"] == "CANDIDATE_WITNESS"
    assert out["route"] == "JSON"
    assert "brain" in out["response"].lower()
    assert re.search(r"\bbrain\b", out["response"], re.I) is None


def test_two_response_overlap_and_title_constructs():
    out = c.compose_contracts([
        C(c.TWO),
        C(c.EXIST, keywords=["brain"]),
        C(c.FORBIDDEN, forbidden_words=["brain"]),
        C(c.TITLE),
    ])
    assert out["status"] == "CANDIDATE_WITNESS"
    assert out["response"].count("******") == 1
    assert "<<" in out["response"] and ">>" in out["response"]
    assert re.search(r"\bbrain\b", out["response"], re.I) is None


def test_section_word_can_be_deboundaried():
    out = c.compose_contracts([
        C(c.SECTIONS, section_spliter="Section", num_sections=3),
        C(c.FORBIDDEN, forbidden_words=["section"]),
    ])
    assert out["status"] == "CANDIDATE_WITNESS"
    assert out["response"].count("9Section ") == 3
    assert re.search(r"\bsection\b", out["response"], re.I) is None


def test_nth_first_word_forbidden_is_proved_unsat():
    out = c.compose_contracts([
        C(c.NTH, num_paragraphs=3, nth_paragraph=2, first_word="brain"),
        C(c.FORBIDDEN, forbidden_words=["brain"]),
    ])
    assert out["status"] == "PROVED_UNSAT"
    assert out["hard_unsat_reasons"] == ["NTH_FIRST_WORD_IS_FORBIDDEN_WORD"]


def test_end_internal_word_forbidden_is_proved_unsat():
    out = c.compose_contracts([
        C(c.END, end_phrase="Any other questions?"),
        C(c.FORBIDDEN, forbidden_words=["other"]),
    ])
    assert out["status"] == "PROVED_UNSAT"
    assert out["hard_unsat_reasons"] == [
        "MANDATORY_END_PHRASE_CONTAINS_FORBIDDEN_WORD:other"
    ]


def test_sentence_zero_case_constructs_empty_exact_witness():
    out = c.compose_contracts([
        C(c.SENTENCES, num_sentences=1, relation="less than"),
        C(c.FORBIDDEN, forbidden_words=["brain"]),
        C(c.WORDS, num_words=100, relation="less than"),
    ])
    assert out["status"] == "CANDIDATE_WITNESS"
    assert out["response"] == ""
    assert out["word_count"] == 0


def test_sentence_zero_output_requirement_is_proved_unsat_before_composition():
    out = c.compose_contracts([
        C(c.SENTENCES, num_sentences=1, relation="less than"),
        C(c.TITLE),
    ])
    assert out["status"] == "PROVED_UNSAT"
    assert any(
        reason.endswith(":detectable_format:title")
        for reason in out["hard_unsat_reasons"]
    )


def test_word_lower_bound_is_constructed_monotonically():
    out = c.compose_contracts([
        C(c.WORDS, num_words=100, relation="at least"),
        C(c.END, end_phrase="Any other questions?"),
    ])
    assert out["status"] == "CANDIDATE_WITNESS"
    assert out["word_count"] >= 100
    assert out["response"].endswith("Any other questions?")


def test_quote_bullets_keeps_bullet_lines_visible():
    out = c.compose_contracts([
        C(c.QUOTE),
        C(c.BULLETS, num_bullets=3),
        C(c.FORBIDDEN, forbidden_words=["brain"]),
    ])
    assert out["status"] == "CANDIDATE_WITNESS"
    assert out["response"][0] == '"' and out["response"][-1] == '"'
    assert len(re.findall(r"^\s*\*[^\*].*$", out["response"], flags=re.MULTILINE)) == 3
