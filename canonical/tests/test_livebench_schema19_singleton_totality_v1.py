from canonical.runtime import livebench_active15_plus_one_noarg_pointwise_v1 as plus1
from canonical.runtime import livebench_schema19_pointwise_candidate_v1 as schema19
from canonical.runtime import livebench_union25_archetypes_v1 as u


def _contract(iid):
    return {"instruction_id": iid, "slots": {}}


def test_plus_one_solver_is_total_on_valid_singleton_noarg_extras():
    for iid in (u.ENGLISH_CAPITAL, u.ENGLISH_LOWERCASE, u.NO_COMMA):
        out = plus1.solve_contracts([_contract(iid)])
        assert out["status"] == "CANDIDATE_POINTWISE_OPTIMAL_ACTIVE15_PLUS_ONE"
        assert out["theoretical_max_pass_count"] == 1
        assert out["sacrificed_instruction_ids"] == []
        assert out["response"]


def test_singleton_case_witnesses_have_required_global_case():
    upper = plus1.solve_contracts([_contract(u.ENGLISH_CAPITAL)])["response"]
    lower = plus1.solve_contracts([_contract(u.ENGLISH_LOWERCASE)])["response"]
    assert upper.isupper()
    assert lower.islower()


def test_schema19_case_plus_no_comma_degenerate_pairs_are_closed():
    for iid in (u.ENGLISH_CAPITAL, u.ENGLISH_LOWERCASE):
        out = schema19.solve_contracts([_contract(iid), _contract(u.NO_COMMA)])
        assert out["status"] == "CANDIDATE_POINTWISE_OPTIMAL_SCHEMA19"
        assert out["route"] == "ACTIVE15_PLUS_CASE_PLUS_NO_COMMA"
        assert out["theoretical_max_pass_count"] == 2
        assert out["sacrificed_instruction_ids"] == []
        assert "," not in out["response"]


def test_schema19_all_extra_only_valid_signatures_have_witnesses():
    signatures = (
        (u.CONSTRAINED,),
        (u.ENGLISH_CAPITAL,),
        (u.ENGLISH_LOWERCASE,),
        (u.NO_COMMA,),
        (u.ENGLISH_CAPITAL, u.NO_COMMA),
        (u.ENGLISH_LOWERCASE, u.NO_COMMA),
    )
    for signature in signatures:
        out = schema19.solve_contracts([_contract(iid) for iid in signature])
        assert out["status"] == "CANDIDATE_POINTWISE_OPTIMAL_SCHEMA19"
        assert out["theoretical_max_pass_count"] == len(signature)
        assert out["sacrificed_instruction_ids"] == []
