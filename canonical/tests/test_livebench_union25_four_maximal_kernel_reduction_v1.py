from canonical.runtime import (
    livebench_union25_four_maximal_kernel_reduction_v1 as reduction,
)
from canonical.runtime import livebench_union25_archetypes_v1 as u


def test_four_maximal_kernel_downset_is_exact():
    out = reduction.verify()
    assert out["hard_signature_count"] == 20
    assert out["maximal_hard_kernel_count"] == 4
    assert len(reduction.expected_hard_signature_downset()) == 20
    assert reduction.actual_hard_signatures() == (
        reduction.expected_hard_signature_downset()
    )


def test_exact_maximal_hard_kernels():
    actual = {
        frozenset(row)
        for row in reduction.verify()["maximal_hard_kernels"]
    }
    expected = {
        frozenset(
            {u.KEYWORD_FREQUENCY, u.LETTER_FREQUENCY, u.CAPITAL_FREQUENCY}
        ),
        frozenset(
            {u.KEYWORD_FREQUENCY, u.LETTER_FREQUENCY, u.ENGLISH_CAPITAL}
        ),
        frozenset(
            {u.KEYWORD_FREQUENCY, u.LETTER_FREQUENCY, u.ENGLISH_LOWERCASE}
        ),
        frozenset(
            {u.LETTER_FREQUENCY, u.LANGUAGE, u.CAPITAL_FREQUENCY}
        ),
    }
    assert actual == expected


def test_numeric_overlay_word_margin_is_strict():
    overlay = reduction.verify()["overlay_reduction"]
    assert overlay["active15_max_unpadded_words"] == 48
    assert overlay["overlay_max_added_words"] == 8
    assert overlay["combined_max_unpadded_words"] == 56
    assert overlay["minimum_public_less_than_word_threshold"] == 100
    assert overlay["remaining_word_margin"] == 44


def test_fail_closed_nonclaims_preserved():
    out = reduction.verify()
    assert out["acceptance_credit"] is False
    assert out["family_credit"] is False
    assert out["capability_credit"] is False
    assert out["ownership_credit"] is False
    assert "FOUR_MAXIMAL_KERNELS_ARE_NOT_YET_SEMANTICALLY_CLOSED" in (
        out["hard_nonclaims"]
    )
    assert "LANGDETECT_NUMERIC_OVERLAY_INVARIANCE_IS_NOT_YET_PROVED" in (
        out["hard_nonclaims"]
    )
