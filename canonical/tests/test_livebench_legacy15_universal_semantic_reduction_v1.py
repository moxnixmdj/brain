from canonical.runtime import livebench_legacy15_universal_semantic_reduction_v1 as reduction


def test_universal_semantic_reduction_v1():
    out = reduction.verify()
    assert out["status"] == (
        "PASS__RAW_SLOT_CARTESIAN_PRODUCT_COLLAPSED_TO_SYMBOLIC_LEMMAS_"
        "PLUS_EXACT_PUNKT_RESIDUAL"
    )
    assert out["structural_identity_sets"] == 928
    assert out["word_upper_bound"][
        "maximum_unpadded_words_over_every_compatible_words_set"
    ] == 48
    assert out["word_upper_bound"]["minimum_public_less_than_threshold"] == 100
    assert out["word_upper_bound"]["margin_words"] == 52
    assert out["remaining_exact_runtime_residual"]["family"] == (
        "NLTK_PUNKT_SENTENCE_TOKENIZATION"
    )
    assert out["acceptance_credit"] is False
    assert out["capability_credit"] is False
    assert out["ownership_credit"] is False
