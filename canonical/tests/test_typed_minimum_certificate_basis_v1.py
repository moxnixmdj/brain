import pytest
from canonical.runtime.typed_minimum_certificate_basis_v1 import solve


def test_prefers_shared_typed_certificate():
    predicates = [
        {"predicate_id":"A","admissible_proof_types":["ABSOLUTE"]},
        {"predicate_id":"B","admissible_proof_types":["ABSOLUTE"]},
    ]
    certs = [
        {"certificate_id":"a","proof_type":"ABSOLUTE","closes":["A"],"critical_path_cost":1},
        {"certificate_id":"b","proof_type":"ABSOLUTE","closes":["B"],"critical_path_cost":1},
        {"certificate_id":"shared","proof_type":"ABSOLUTE","closes":["A","B"],"critical_path_cost":1.5},
    ]
    out = solve(predicates, certs)
    assert out["complete_basis_exists"] is True
    assert out["selected_certificate_ids"] == ["shared"]
    assert out["minimum_total_declared_cost"] == 1.5


def test_relative_elo_rejects_absolute_certificate():
    predicates = [
        {"predicate_id":"GDPVAL","admissible_proof_types":["RELATIVE_SCORE_BRIDGE","OWNER_RESULT","MATCHED_COMPARISON"]},
    ]
    certs = [
        {"certificate_id":"absolute","proof_type":"ABSOLUTE","closes":["GDPVAL"],"critical_path_cost":0},
        {"certificate_id":"relative","proof_type":"RELATIVE_SCORE_BRIDGE","closes":["GDPVAL"],"critical_path_cost":2},
    ]
    out = solve(predicates, certs)
    assert out["selected_certificate_ids"] == ["relative"]
    assert out["rejected_candidates"][0]["certificate_id"] == "absolute"


def test_fail_closed_when_no_admissible_cover():
    predicates = [
        {"predicate_id":"X","admissible_proof_types":["MATCHED"]},
    ]
    certs = [
        {"certificate_id":"bad","proof_type":"ABSOLUTE","closes":["X"],"critical_path_cost":1},
    ]
    out = solve(predicates, certs)
    assert out["complete_basis_exists"] is False
    assert out["structurally_uncoverable_predicates"] == ["X"]


def test_invalid_cost_rejected():
    with pytest.raises(ValueError):
        solve(
            [{"predicate_id":"X","admissible_proof_types":["A"]}],
            [{"certificate_id":"c","proof_type":"A","closes":["X"],"critical_path_cost":-1}],
        )
