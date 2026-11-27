from canonical.runtime import livebench_legacy15_lexical_collision_quotient_v1 as q


def test_exact_reachable_quotient_is_74_not_loose_320_bound():
    out = q.verify()
    assert out["status"] == "PASS__EXACT_REACHABLE_LEXICAL_COLLISION_QUOTIENT_74"
    assert out["reachable_signature_count"] == 74
    assert out["first_end_signature_count"] == 18
    assert out["second_end_signature_count"] == 56
    assert out["prior_conservative_signature_upper_bound"] == 320


def test_every_signature_has_exact_five_word_roundtrip_representative():
    signatures = q.enumerate_reachable_signatures()
    assert len(signatures) == 74
    for sig in signatures:
        row = q.representative(sig)
        assert len(row["forbidden_words"]) == 5
        assert len(set(row["forbidden_words"])) == 5
        assert q.project(**row) == sig


def test_generic_word_identity_quotients_away():
    a = q.project(
        nth_first_word="western",
        forbidden_words=["sentence", "signal", "dump", "spot", "opposite"],
        end_phrase=q.FIRST_END,
    )
    b = q.project(
        nth_first_word="potato",
        forbidden_words=["sentence", "signal", "dump", "spot", "opposite"],
        end_phrase=q.FIRST_END,
    )
    assert a == b
    assert a.nth_category == q.OTHER
    assert a.nth_is_forbidden is False


def test_nth_end_word_membership_is_not_an_independent_bit():
    # For the second end phrase, nth='can' and the end collision bit for 'can'
    # are the same forbidden-set membership fact.
    signatures = [
        s
        for s in q.enumerate_reachable_signatures()
        if s.end_phrase == q.SECOND_END and s.nth_category == "can"
    ]
    assert len(signatures) == 8
    relevant = q._END_RELEVANT[q.SECOND_END]
    i = relevant.index("can")
    assert all(s.nth_is_forbidden == s.end_forbidden_mask[i] for s in signatures)


def test_end_phrase_relevance_deletes_irrelevant_special_bits():
    # 'can' membership is irrelevant to the first fixed end phrase unless can
    # itself is the NTH word; changing an unrelated generic forbidden identity
    # cannot alter the signature.
    a = q.project(
        nth_first_word="western",
        forbidden_words=["other", "can", "sentence", "signal", "dump"],
        end_phrase=q.FIRST_END,
    )
    b = q.project(
        nth_first_word="western",
        forbidden_words=["other", "help", "sentence", "signal", "dump"],
        end_phrase=q.FIRST_END,
    )
    assert a == b


def test_invalid_generator_shapes_fail_closed():
    import pytest

    with pytest.raises(ValueError):
        q.project(
            nth_first_word="western",
            forbidden_words=["a", "b"],
            end_phrase=q.FIRST_END,
        )
    with pytest.raises(ValueError):
        q.project(
            nth_first_word="western",
            forbidden_words=["sentence"] * 5,
            end_phrase=q.FIRST_END,
        )
    with pytest.raises(ValueError):
        q.project(
            nth_first_word="western",
            forbidden_words=["sentence", "signal", "dump", "spot", "opposite"],
            end_phrase="not a frozen end phrase",
        )
