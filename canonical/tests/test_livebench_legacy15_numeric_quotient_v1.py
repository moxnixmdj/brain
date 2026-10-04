from canonical.runtime import livebench_legacy15_numeric_quotient_v1 as q


def test_analytic_word_ceiling_is_below_public_minimum():
    assert q.ANALYTIC_WORD_CEILING == 48
    assert q.WORD_MIN - q.ANALYTIC_WORD_CEILING == 52


def test_numeric_quotient_exhausts_word_structural_sets():
    out = q.verify()
    assert out["status"] == "PASS__PARAMETRIC_NUMERIC_REDUCTION"
    ex = out["word_upper_bound"]["executable_structural_crosscheck"]
    assert ex["examined"] == ex["constructed"]
    assert ex["maximum"] <= 48
    assert out["word_upper_bound"]["minimum_safety_margin"] == 52


def test_sentence_partition_has_only_three_numeric_classes():
    out = q.verify()["sentence_partition"]
    assert set(out) == {
        "less_than_1",
        "less_than_2_to_20",
        "at_least_1_to_20",
    }
