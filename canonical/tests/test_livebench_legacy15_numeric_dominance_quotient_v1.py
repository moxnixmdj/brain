import pytest

from canonical.runtime import livebench_legacy15_numeric_dominance_quotient_v1 as q


def test_exact_public_domain_counts_and_reduction():
    out = q.summary()
    assert out["raw_family_state_sum"] == 881
    assert out["reduced_proof_class_sum"] == 36
    assert out["nonreachable_cartesian_envelope_raw"] == 481_200_000
    assert out["nonreachable_cartesian_envelope_reduced"] == 18_000
    assert out["structural_word_upper_bound"] == 37
    assert out["word_upper_bound_margin_below_hardest_historical_threshold"] == 63
    assert out["terminal_data_used"] is False
    assert out["acceptance_credit"] is False


def test_all_802_word_settings_map_to_two_extremal_classes():
    reps = set()
    for n in range(100, 501):
        for rel in ("less than", "at least"):
            row = q.number_words_class(n, rel)
            rep = row["representative"]
            reps.add((rep["num_words"], rep["relation"]))
    assert reps == {(100, "less than"), (500, "at least")}


def test_all_40_sentence_settings_map_to_three_classes():
    reps = set()
    for n in range(1, 21):
        for rel in ("less than", "at least"):
            row = q.number_sentences_class(n, rel)
            rep = row["representative"]
            reps.add((rep["num_sentences"], rep["relation"]))
    assert reps == {
        (1, "less than"),
        (2, "less than"),
        (20, "at least"),
    }


def test_all_section_settings_map_to_strongest_count_preserving_case():
    reps = set()
    for n in range(1, 6):
        for splitter in ("Section", "SECTION"):
            row = q.section_class(n, splitter)
            rep = row["representative"]
            reps.add((rep["num_sections"], rep["section_spliter"]))
            assert row["boundary_safe_form"] in ("Section1", "SECTION1")
    assert reps == {(5, "Section"), (5, "SECTION")}


@pytest.mark.parametrize(
    "fn,args",
    [
        (q.number_words_class, (99, "less than")),
        (q.number_words_class, (501, "at least")),
        (q.number_sentences_class, (0, "less than")),
        (q.number_sentences_class, (21, "at least")),
        (q.section_class, (0, "Section")),
        (q.section_class, (6, "Section")),
        (q.section_class, (1, "chapter")),
    ],
)
def test_outside_frozen_domain_fails_closed(fn, args):
    with pytest.raises(ValueError):
        fn(*args)
