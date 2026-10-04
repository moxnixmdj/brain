from canonical.runtime import livebench_punkt_nonempty_unsat_v1 as f


SENTENCE_LT_ONE = {
    "instruction_id": f.SENTENCE,
    "slots": {"num_sentences": 1, "relation": "less than"},
}


def c(iid, **slots):
    return {"instruction_id": iid, "slots": slots}


def test_general_nonempty_forcers_are_certified_unsat():
    cases = [
        c(f.EXISTENCE, keywords=["rock", "signal"]),
        c(f.WORDS, num_words=100, relation="at least"),
        c(f.NTH, num_paragraphs=2, nth_paragraph=1, first_word="rock"),
        c(f.POSTSCRIPT, postscript_marker="P.S."),
        c(f.BULLETS, num_bullets=1),
        c(f.TITLE),
        c(f.SECTIONS, section_spliter="Section", num_sections=1),
        c(f.END, end_phrase="Any other questions?"),
        c(f.QUOTATION),
    ]
    for other in cases:
        out = f.classify_visible_contracts([SENTENCE_LT_ONE, other])
        assert out["status"] == "PROVED_UNSAT", other
        assert len(out["hard_unsat_reasons"]) == 1
        assert out["hard_unsat_reasons"][0].startswith(
            "SENTENCE_LT_ONE_WITH_NONEMPTY_REQUIRED:"
        )


def test_forbidden_words_does_not_force_nonempty():
    out = f.classify_visible_contracts([
        SENTENCE_LT_ONE,
        c("keywords:forbidden_words", forbidden_words=["rock"]),
    ])
    assert out["status"] == "NO_PUNKT_NONEMPTY_UNSAT_CERTIFICATE"
    assert out["hard_unsat_reasons"] == []


def test_less_than_word_bound_does_not_force_nonempty():
    out = f.classify_visible_contracts([
        SENTENCE_LT_ONE,
        c(f.WORDS, num_words=100, relation="less than"),
    ])
    assert out["status"] == "NO_PUNKT_NONEMPTY_UNSAT_CERTIFICATE"


def test_sentence_threshold_two_is_not_covered_by_zero_sentence_lemma():
    out = f.classify_visible_contracts([
        c(f.SENTENCE, num_sentences=2, relation="less than"),
        c(f.END, end_phrase="Any other questions?"),
    ])
    assert out["status"] == "NO_PUNKT_NONEMPTY_UNSAT_CERTIFICATE"


def test_structurally_conflicting_pair_fails_closed_before_semantic_certificate():
    out = f.classify_visible_contracts([
        SENTENCE_LT_ONE,
        c("detectable_format:json_format"),
    ])
    assert out["status"] == "FAIL_CLOSED_ID_CONFLICT"


def test_multiple_nonempty_forcers_emit_multiple_reasons():
    out = f.classify_visible_contracts([
        SENTENCE_LT_ONE,
        c(f.EXISTENCE, keywords=["rock"]),
        c(f.END, end_phrase="Any other questions?"),
    ])
    assert out["status"] == "PROVED_UNSAT"
    assert len(out["hard_unsat_reasons"]) == 2


def test_summary_is_zero_terminal_zero_credit():
    out = f.proof_summary()
    assert out["status"] == "PASS__GENERAL_PUNKT_NONEMPTY_UNSAT_LEMMA_ENCODED"
    assert len(out["certifiable_nonempty_checker_ids"]) == 9
    assert out["terminal_data_used"] is False
    assert out["hidden_kwargs_used"] is False
    assert out["acceptance_credit"] is False
