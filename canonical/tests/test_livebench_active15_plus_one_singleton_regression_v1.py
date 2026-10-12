from canonical.runtime import livebench_active15_plus_one_noarg_pointwise_v1 as p
from canonical.runtime import livebench_union25_archetypes_v1 as u


def c(iid):
    return {"instruction_id": iid, "slots": {}}


def test_no_comma_true_singleton_no_longer_delegates_to_empty_active15():
    out = p.solve_contracts([c(u.NO_COMMA)])
    assert out["status"] == "CANDIDATE_POINTWISE_OPTIMAL_ACTIVE15_PLUS_ONE"
    assert out["response"] == "9000001"
    assert "," not in out["response"]
    assert out["theoretical_max_pass_count"] == 1


def test_english_capital_true_singleton_uses_failopen_case_witness():
    out = p.solve_contracts([c(u.ENGLISH_CAPITAL)])
    assert out["status"] == "CANDIDATE_POINTWISE_OPTIMAL_ACTIVE15_PLUS_ONE"
    assert out["response"].isupper()
    assert out["response"] == p.ENGLISH_CARRIERS[0].upper()
    assert out["theoretical_max_pass_count"] == 1


def test_english_lowercase_true_singleton_uses_failopen_case_witness():
    out = p.solve_contracts([c(u.ENGLISH_LOWERCASE)])
    assert out["status"] == "CANDIDATE_POINTWISE_OPTIMAL_ACTIVE15_PLUS_ONE"
    assert out["response"].islower()
    assert out["response"] == p.ENGLISH_CARRIERS[0].lower()
    assert out["theoretical_max_pass_count"] == 1


def test_schema19_two_extra_empty_active_compositions_now_have_base():
    from canonical.runtime import livebench_schema19_pointwise_candidate_v1 as s

    for case in (u.ENGLISH_CAPITAL, u.ENGLISH_LOWERCASE):
        out = s.solve_contracts([c(case), c(u.NO_COMMA)])
        assert out["status"] == "CANDIDATE_POINTWISE_OPTIMAL_SCHEMA19"
        assert out["theoretical_max_pass_count"] == 2
        assert "," not in out["response"]
