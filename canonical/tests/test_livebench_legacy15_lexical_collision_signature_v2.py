from canonical.runtime import livebench_legacy15_lexical_collision_signature_v2 as q


def test_exact_reachable_signature_count_is_446():
    out = q.prove_count()
    assert out["status"] == "PASS__EXACT_REACHABLE_LEXICAL_SIGNATURE_QUOTIENT"
    assert out["exact_reachable_signature_count"] == 446
    assert out["fixed_nth_category_signature_count"] == 320
    assert out["generic_nth_signature_count"] == 126


def test_prior_320_bound_is_not_sound_after_section_becomes_relevant():
    out = q.prove_count()
    assert out["prior_320_bound_is_sound_for_current_kernel"] is False
    assert out["conservative_cartesian_bound"] == 768


def test_fixed_nth_collision_bit_is_not_independent():
    signatures = q.enumerate_reachable_signatures()
    fixed_index = {word: i for i, word in enumerate(q.FIXED_RELEVANT_WORDS)}
    for _, nth_category, bits, nth_is_forbidden in signatures:
        if nth_category in fixed_index:
            assert nth_is_forbidden == bits[fixed_index[nth_category]]


def test_generic_nth_forbidden_collision_respects_five_slot_capacity():
    signatures = q.enumerate_reachable_signatures()
    generic = [
        s for s in signatures
        if s[1] == "generic"
    ]
    assert len(generic) == 126
    for _, _, bits, nth_is_forbidden in generic:
        if nth_is_forbidden:
            assert sum(bits) <= 4


def test_section_collision_is_explicitly_semantic():
    sig = (
        0,
        "generic",
        (False, False, False, False, True),
        False,
    )
    assert "MANDATORY_SECTION_SPLITTER_IS_FORBIDDEN_WORD:section" in q.lexical_unsat_reasons(sig)


def test_end_phrase_collision_words_match_current_kernel():
    first = (0, "generic", (True, False, False, False, False), False)
    second = (1, "generic", (False, True, True, True, False), False)

    assert q.lexical_unsat_reasons(first) == (
        "MANDATORY_END_PHRASE_CONTAINS_FORBIDDEN_WORD:other",
    )
    assert q.lexical_unsat_reasons(second) == (
        "MANDATORY_END_PHRASE_CONTAINS_FORBIDDEN_WORD:anything",
        "MANDATORY_END_PHRASE_CONTAINS_FORBIDDEN_WORD:can",
        "MANDATORY_END_PHRASE_CONTAINS_FORBIDDEN_WORD:help",
    )


def test_nth_collision_is_explicit():
    sig = (
        0,
        "generic",
        (False, False, False, False, False),
        True,
    )
    assert q.lexical_unsat_reasons(sig) == (
        "NTH_FIRST_WORD_IS_FORBIDDEN_WORD",
    )
