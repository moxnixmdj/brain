import pytest

from canonical.runtime import livebench_legacy15_lexical_slot_quotient_v1 as q


def test_exact_reachable_signature_count_is_192():
    signatures = q.enumerate_signatures()
    assert len(signatures) == 192
    assert len(set(signatures)) == 192


def test_exact_partition_counts_and_collision_counts():
    out = q.verify()
    assert out["status"].startswith("PASS__EXACT_192_REACHABLE")
    assert out["counts_by_end_phrase_index"] == {0: 96, 1: 96}
    assert out["counts_by_nth_category"] == {
        "other": 32,
        "anything": 32,
        "can": 32,
        "help": 32,
        "__generic__": 64,
    }
    assert out["nth_forbidden_collision_signature_count"] == 96
    assert out["end_forbidden_collision_signature_count"] == 132
    assert out["any_lexical_hard_collision_signature_count"] == 155


def test_every_representative_has_exactly_five_distinct_forbidden_words():
    for sig in q.enumerate_signatures():
        words = q.representative_forbidden_words(sig)
        assert len(words) == 5
        assert len(set(words)) == 5
        bits = sig.special_bits
        for word in q.SPECIAL_WORDS:
            assert (word in words) is bits[word]
        assert (sig.nth_word in words) is sig.nth_in_forbidden


def test_special_nth_membership_is_not_an_independent_bit():
    for sig in q.enumerate_signatures():
        if sig.nth_category in q.SPECIAL_SET:
            assert (
                sig.nth_in_forbidden
                is sig.special_bits[sig.nth_category]
            )


def test_generic_nth_membership_has_both_reachable_states():
    generic = [
        sig
        for sig in q.enumerate_signatures()
        if sig.nth_category == "__generic__"
    ]
    assert len(generic) == 64
    assert {sig.nth_in_forbidden for sig in generic} == {False, True}


def test_inconsistent_external_special_signature_fails_closed():
    sig = q.LexicalSignature(
        end_phrase_index=0,
        nth_category="other",
        forbidden_other=False,
        forbidden_anything=False,
        forbidden_can=False,
        forbidden_help=False,
        nth_in_forbidden=True,
    )
    with pytest.raises(ValueError, match="INCONSISTENT_SPECIAL_NTH_MEMBERSHIP"):
        q.representative_forbidden_words(sig)


def test_end_phrase_collision_predictions_are_exact_for_public_fixed_phrases():
    first = q.LexicalSignature(
        end_phrase_index=0,
        nth_category="__generic__",
        forbidden_other=True,
        forbidden_anything=False,
        forbidden_can=False,
        forbidden_help=False,
        nth_in_forbidden=False,
    )
    assert q.predicted_hard_collisions(first) == (
        "MANDATORY_END_PHRASE_CONTAINS_FORBIDDEN_WORD:other",
    )

    second = q.LexicalSignature(
        end_phrase_index=1,
        nth_category="__generic__",
        forbidden_other=False,
        forbidden_anything=True,
        forbidden_can=True,
        forbidden_help=True,
        nth_in_forbidden=False,
    )
    assert q.predicted_hard_collisions(second) == (
        "MANDATORY_END_PHRASE_CONTAINS_FORBIDDEN_WORD:anything",
        "MANDATORY_END_PHRASE_CONTAINS_FORBIDDEN_WORD:can",
        "MANDATORY_END_PHRASE_CONTAINS_FORBIDDEN_WORD:help",
    )
