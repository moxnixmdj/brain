from fractions import Fraction

from canonical.runtime import livebench_legacy_generator_max5_completion_bound_v1 as b


def test_historical_generator_deletion_only_implies_max_five():
    out = b.prove()
    assert out["status"] == "PASS__CONDITIONAL_ON_HISTORICAL_GENERATOR_LINEAGE"
    assert out["derived"]["maximum_output_instruction_count"] == 5
    assert out["historical_generator_contract"]["draw_without_replacement"] is True
    assert out["historical_generator_contract"]["conflict_repair_operation"] == "DELETE_ONLY"


def test_exact_score_marginals_are_sharply_bounded():
    assert b.nonfinal_instruction_marginal(5) == Fraction(1, 10)
    assert b.final_completion_marginal(5) == Fraction(3, 5)
    for n in range(1, 6):
        assert b.final_completion_marginal(n) >= Fraction(3, 5)


def test_active15_composition_upper_bound_shrinks_to_size_at_most_five():
    assert b.valid_active_subsets_up_to_max_draw() == 928


def test_exact_opus_mass_and_full_case_sufficiency():
    out = b.prove()["derived"]
    assert out["target_percent"] == "65.73775"
    assert out["target_score_mass"] == "5259/40"
    assert out["fully_completed_rows_sufficient"] == 132


def test_zero_credit_without_lineage_binding():
    out = b.prove()
    assert out["terminal_data_used"] is False
    assert out["acceptance_credit"] is False
    assert out["capability_credit"] is False
    assert "NO_TERMINAL_CREDIT_UNLESS" in out["lineage_requirement"]
