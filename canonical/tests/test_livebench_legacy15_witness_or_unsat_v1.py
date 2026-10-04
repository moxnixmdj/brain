from canonical.runtime import livebench_legacy15_witness_or_unsat_v1 as w


def c(iid, **slots):
    return {
        "instruction_id": iid,
        "slots": slots,
        "parameter_complete": True,
    }


def test_nth_forbidden_slot_collision_is_unsat_not_solver_failure():
    out = w.classify_constraints([
        c(
            "length_constraints:nth_paragraph_first_word",
            num_paragraphs=3,
            nth_paragraph=2,
            first_word="rock",
        ),
        c("keywords:forbidden_words", forbidden_words=["rock", "apple"]),
    ])
    assert out["status"] == "PROVED_UNSAT_VISIBLE_CONTRACT"
    assert out["archetype"] == "NTH_PARAGRAPH"
    assert out["hard_unsat_reasons"] == ["NTH_FIRST_WORD_IS_FORBIDDEN_WORD"]
    assert out["response"] is None


def test_end_phrase_forbidden_slot_collision_is_unsat_not_solver_failure():
    out = w.classify_constraints([
        c("startend:end_checker", end_phrase="Any other questions?"),
        c("keywords:forbidden_words", forbidden_words=["other", "apple"]),
    ])
    assert out["status"] == "PROVED_UNSAT_VISIBLE_CONTRACT"
    assert out["hard_unsat_reasons"] == [
        "MANDATORY_END_PHRASE_CONTAINS_FORBIDDEN_WORD:other"
    ]


def test_safe_general_contract_routes_to_general_witness_composer():
    out = w.classify_constraints([
        c("keywords:existence", keywords=["river"]),
        c("keywords:forbidden_words", forbidden_words=["apple"]),
        c("length_constraints:number_words", num_words=120, relation="at least"),
    ])
    assert out["status"] == "WITNESS_REQUIRED"
    assert out["composer"] == "GENERAL"
    assert out["archetype"] == "PLAIN"


def test_special_contract_routes_to_special_witness_composer():
    out = w.classify_constraints([
        c("detectable_format:json_format"),
        c("keywords:existence", keywords=["river"]),
    ])
    assert out["status"] == "WITNESS_REQUIRED"
    assert out["composer"] == "SPECIAL"
    assert out["archetype"] == "JSON"


def test_structural_conflict_fails_closed():
    out = w.classify_constraints([
        c("detectable_format:json_format"),
        c("length_constraints:number_words", num_words=120, relation="at least"),
    ])
    assert out["status"] == "FAIL_CLOSED"
    assert out["response"] is None


def test_section_splitter_forbidden_slot_collision_is_unsat():
    out = w.classify_constraints([
        c("detectable_format:multiple_sections", section_spliter="Section", num_sections=3),
        c("keywords:forbidden_words", forbidden_words=["section", "apple"]),
    ])
    assert out["status"] == "PROVED_UNSAT_VISIBLE_CONTRACT"
    assert out["hard_unsat_reasons"] == [
        "MANDATORY_SECTION_SPLITTER_IS_FORBIDDEN_WORD:section"
    ]


def test_required_forbidden_overlap_is_not_false_unsat():
    out = w.classify_constraints([
        c("keywords:existence", keywords=["rock"]),
        c("keywords:forbidden_words", forbidden_words=["rock", "apple"]),
    ])
    assert out["status"] == "WITNESS_REQUIRED"
    assert out["hard_unsat_reasons"] == []
