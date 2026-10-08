import pathlib
import tempfile
from copy import deepcopy

from canonical.runtime.p3_real_context_v3_admission_v9 import evaluate
from canonical.tests.test_p3_membership_frontdoor_v6 import base, req, ev
from canonical.tests.test_p3_real_context_v3_admission_v7 import dep_case


def opt(i, text):
    return {"claim_id": i, "text": text, "required": False}


def optional_case(max_items=3):
    public = base(
        [
            req("A", "Revenue growth is 12."),
            opt("B", "Margin rate is 8."),
            opt("C", "Debt ratio is 3."),
        ],
        [
            ev("E1", "Report states Revenue growth is 12."),
            ev("E2", "Report states Margin rate is 8."),
            ev("E3", "Report states Debt ratio is 3."),
        ],
    )
    public["task"]["audience_profile"]["constraints"]["max_items"] = max_items
    return {"context_id": "x", "v3_input": public}


def test_current_v8_positive_route_is_preserved():
    p = {
        "context_id": "x",
        "v3_input": base(
            [req("A", "Revenue growth is 12.")],
            [ev("E", "Report states Revenue growth is 12.")],
        ),
    }
    out = evaluate(p)
    assert out["pass"], out
    assert out["route"] == "MECHANICALLY_CLOSED_COMMON_POLICY_CELL_V1"
    assert out["v8_preserved_positive_route"] is True


def test_optional_without_weights_closes_when_capacity_nonbinding():
    out = evaluate(optional_case(3))
    assert out["pass"] is True, out
    assert out["route"] == "NONBINDING_CAPACITY_COMMON_POLICY_CELL_V1"
    assert out["selected_claim_ids"] == ["A", "B", "C"]
    assert out["selected_optional_claim_ids"] == ["B", "C"]
    assert out["explicit_authority_consumed"] is None


def test_capacity_binding_stays_fail_closed():
    out = evaluate(optional_case(2))
    assert out["pass"] is False
    assert out["nonbinding_capacity_fast_path_pass"] is False
    assert out["nonbinding_capacity_reason"] == "CAPACITY_BINDING_REQUIRES_RELEVANCE_POLICY"
    assert out["terminal_authority"] is False


def test_invalid_explicit_weights_never_fall_through_to_nonbinding():
    p = optional_case(3)
    p["objective_weights"] = {"A": 1}
    out = evaluate(p)
    assert out["pass"] is False
    assert out["reason"] == "OBJECTIVE_WEIGHTS_UNSATISFIED"
    assert out["nonbinding_capacity_fast_path_pass"] is False


def test_invalid_dependency_contract_never_falls_through():
    with tempfile.TemporaryDirectory() as td:
        p = dep_case(pathlib.Path(td))
        p["decision_dependency_contract"]["dependency_verification_ref"]["path"] = "not/canonical.json"
        out = evaluate(p, repo_root=td)
        assert out["pass"] is False
        assert out["reason"] == "DECISION_DEPENDENCY_CONTRACT_UNSATISFIED"
        assert out["nonbinding_capacity_fast_path_pass"] is False


def test_unmodeled_outer_field_fails_closed():
    p = optional_case(3)
    p["hidden_selection_rule"] = "prefer B"
    out = evaluate(p)
    assert out["pass"] is False
    assert out["reason"] == "UNMODELED_REAL_CONTEXT_ADMISSION_FIELDS"


def test_unmodeled_claim_semantics_fail_closed():
    p = optional_case(3)
    p["v3_input"]["task"]["claims"][1]["forbid_output"] = True
    out = evaluate(p)
    assert out["pass"] is False
    assert out["reason"] == "UNMODELED_CLAIM_REQUIREMENTS"


def test_context_id_remains_required_without_dependency_contract():
    p = optional_case(3)
    del p["context_id"]
    out = evaluate(p)
    assert out["pass"] is False
    assert out["reason"] == "CONTEXT_ID_REQUIRED"


def test_unsupported_optional_is_excluded_without_salience_choice():
    p = optional_case(3)
    p["v3_input"]["task"]["evidence"] = p["v3_input"]["task"]["evidence"][:2]
    out = evaluate(p)
    assert out["pass"] is True, out
    assert out["route"] == "NONBINDING_CAPACITY_COMMON_POLICY_CELL_V1"
    assert out["selected_claim_ids"] == ["A", "B"]


def test_conflict_does_not_get_hidden_by_nonbinding_route():
    p = optional_case(4)
    p["v3_input"]["task"]["evidence"].append(
        ev("E4", "Report states Margin rate is 9.")
    )
    out = evaluate(p)
    assert out["pass"] is False
    assert out["nonbinding_capacity_reason"] == "CONFLICT_REQUIRES_UNCERTAINTY_SEMANTICS"


def test_all_new_positive_authority_bits_remain_zero():
    out = evaluate(optional_case(3))
    assert out["pass"], out
    for field in (
        "source_authorization_verified",
        "policy_adequacy_authority",
        "db_admission_authority",
        "u_subtraction_authority",
        "terminal_authority",
    ):
        assert out[field] is False, (field, out)
    assert out["terminal_credit_delta"] == 0
