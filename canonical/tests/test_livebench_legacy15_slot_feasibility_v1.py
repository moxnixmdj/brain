import re

from canonical.runtime import livebench_legacy15_slot_feasibility_v1 as f


def test_id_compatibility_is_not_slot_satisfiability():
    out = f.prove_id_compatibility_is_not_satisfiability()
    assert out["status"] == "PASS__ID_COMPATIBILITY_STRICTLY_WEAKER_THAN_SLOT_SATISFIABILITY"
    assert out["counterexample_archetype"] == "NTH_PARAGRAPH"
    assert "NTH_FIRST_WORD_IS_FORBIDDEN_WORD" in out["hard_unsat_reasons"]
    assert out["terminal_data_used"] is False
    assert out["hidden_kwargs_used"] is False
    assert out["acceptance_credit"] is False


def test_required_keyword_forbidden_overlap_is_not_false_unsat():
    contracts = [
        {
            "instruction_id": f.EXISTENCE,
            "slots": {"keywords": ["signal", "Harbor", "world"]},
        },
        {
            "instruction_id": f.FORBIDDEN,
            "slots": {"forbidden_words": ["delta", "harbor"]},
        },
    ]
    out = f.classify_visible_contracts(contracts)
    assert out["status"] == "ID_COMPATIBLE__SLOT_FEASIBILITY_NOT_YET_PROVED"
    assert out["hard_unsat_reasons"] == []

    # Exact checker asymmetry: existence is raw regex substring search while
    # forbidden wraps the generated alphabetic word in word boundaries.
    carrier = "harbor0"
    assert re.search("harbor", carrier, flags=re.IGNORECASE)
    assert re.search(r"\bharbor\b", carrier, flags=re.IGNORECASE) is None


def test_required_and_forbidden_disjoint_stays_unknown():
    contracts = [
        {
            "instruction_id": f.EXISTENCE,
            "slots": {"keywords": ["signal", "harbor", "world"]},
        },
        {
            "instruction_id": f.FORBIDDEN,
            "slots": {"forbidden_words": ["delta", "ember"]},
        },
    ]
    out = f.classify_visible_contracts(contracts)
    assert out["status"] == "ID_COMPATIBLE__SLOT_FEASIBILITY_NOT_YET_PROVED"
    assert out["hard_unsat_reasons"] == []


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


def test_section_forbidden_overlap_is_not_false_unsat():
    contracts = [
        {
            "instruction_id": "detectable_format:multiple_sections",
            "slots": {"section_spliter": "Section", "num_sections": 3},
        },
        {
            "instruction_id": f.FORBIDDEN,
            "slots": {"forbidden_words": ["section"]},
        },
    ]
    out = f.classify_visible_contracts(contracts)
    assert out["status"] == "ID_COMPATIBLE__SLOT_FEASIBILITY_NOT_YET_PROVED"
    assert out["hard_unsat_reasons"] == []
    witness = "Section1\nz\nSection2\nz\nSection3\nz"
    assert len(re.findall(r"\\s?Section\\s?\\d+\\s?", witness)) >= 3
    assert re.search(r"\\bsection\\b", witness, flags=re.IGNORECASE) is None


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


def test_sentence_less_than_one_with_public_end_phrase_is_certified():
    contracts = [
        {
            "instruction_id": f.SENTENCE,
            "slots": {"num_sentences": 1, "relation": "less than"},
        },
        {
            "instruction_id": f.END,
            "slots": {"end_phrase": "Any other questions?"},
        },
    ]
    out = f.classify_visible_contracts(contracts)
    assert out["status"] == "PROVED_UNSAT"
    assert "SENTENCE_LT_ONE_WITH_MANDATORY_END_PHRASE" in out["hard_unsat_reasons"]


def test_sentence_less_than_one_rejects_every_active_nonempty_requirement():
    cases = [
        [{"instruction_id": f.EXISTENCE, "slots": {"keywords": ["rock"]}}],
        [{"instruction_id": f.NTH, "slots": {"num_paragraphs": 2, "nth_paragraph": 1, "first_word": "rock"}}],
        [{"instruction_id": f.POSTSCRIPT, "slots": {"postscript_marker": "P.S."}}],
        [{"instruction_id": f.BULLETS, "slots": {"num_bullets": 1}}],
        [{"instruction_id": f.TITLE, "slots": {}}],
        [{"instruction_id": f.SECTIONS, "slots": {"section_spliter": "Section", "num_sections": 1}}],
        [{"instruction_id": f.END, "slots": {"end_phrase": "Any other questions?"}}],
        [{"instruction_id": f.QUOTATION, "slots": {}}],
        [{"instruction_id": f.WORDS, "slots": {"num_words": 100, "relation": "at least"}}],
    ]
    sentence = {
        "instruction_id": f.SENTENCE,
        "slots": {"num_sentences": 1, "relation": "less than"},
    }
    for extra in cases:
        out = f.classify_visible_contracts([sentence, *extra])
        assert out["status"] == "PROVED_UNSAT"
        assert any(
            x.startswith("SENTENCE_LT_ONE_REQUIRES_EMPTY_BUT_CHECKER_REQUIRES_OUTPUT:")
            for x in out["hard_unsat_reasons"]
        )


def test_sentence_less_than_one_allows_empty_compatible_contracts():
    out = f.classify_visible_contracts([
        {
            "instruction_id": f.SENTENCE,
            "slots": {"num_sentences": 1, "relation": "less than"},
        },
        {
            "instruction_id": f.FORBIDDEN,
            "slots": {"forbidden_words": ["rock"]},
        },
        {
            "instruction_id": f.WORDS,
            "slots": {"num_words": 100, "relation": "less than"},
        },
    ])
    assert out["status"] == "ID_COMPATIBLE__SLOT_FEASIBILITY_NOT_YET_PROVED"
    assert out["hard_unsat_reasons"] == []


def test_sentence_less_than_one_does_not_overcertify_nonpublic_end_phrase():
    contracts = [
        {
            "instruction_id": f.SENTENCE,
            "slots": {"num_sentences": 1, "relation": "less than"},
        },
        {
            "instruction_id": f.END,
            "slots": {"end_phrase": "custom suffix"},
        },
    ]
    out = f.classify_visible_contracts(contracts)
    assert out["status"] == "ID_COMPATIBLE__SLOT_FEASIBILITY_NOT_YET_PROVED"
    assert "SENTENCE_LT_ONE_WITH_MANDATORY_END_PHRASE" not in out["hard_unsat_reasons"]
