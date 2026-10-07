from canonical.runtime.terminal_bstar_information_cut_v1 import verify


def test_exact_partition():
    out = verify()
    assert out["pass"], out
    assert out["truths"] == 29
    assert out["target_specific_upper_bound"] == 15
    assert out["zero_target_truths"] == 14


def test_zero_target_program_compression():
    out = verify()
    assert out["zero_target_programs"] == 4
    assert out["truths_deleted"] == 0


def test_irreducible_target_information_not_predeclared():
    out = verify()
    assert out["irreducible_target_specific_count"] is None
    assert out["terminal"] is False
    assert out["terminal_credit_delta"] == 0
