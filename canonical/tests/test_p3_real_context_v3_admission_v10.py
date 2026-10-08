import pathlib
import tempfile

from canonical.runtime.p3_real_context_v3_admission_v10 import evaluate
from canonical.tests.test_p3_policy_influence_relevance_cell_v1 import make_payload, public_case


def test_v9_positive_route_is_preserved():
    public = public_case(max_items=3)
    out = evaluate({"context_id": "ctx", "v3_input": public})
    assert out["pass"] is True, out
    assert out["route"] == "NONBINDING_CAPACITY_COMMON_POLICY_CELL_V1"
    assert out["v9_preserved_positive_route"] is True


def test_v10_closes_exact_capacity_binding_relevance_frontier():
    with tempfile.TemporaryDirectory() as td:
        root = pathlib.Path(td)
        out = evaluate(make_payload(root, max_items=2), repo_root=root)
        assert out["pass"] is True, out
        assert out["route"] == "POLICY_INFLUENCE_NONINTERFERENCE_RELEVANCE_CELL_V1"
        assert out["selected_claim_ids"] == ["A", "B"]
        assert out["relevance_bits"] == {"D": "RELEVANT", "E": "IRRELEVANT"}


def test_capacity_binding_without_contract_stays_fail_closed():
    public = public_case(max_items=2)
    out = evaluate({"context_id": "ctx", "v3_input": public})
    assert out["pass"] is False
    assert out["nonbinding_capacity_reason"] == "CAPACITY_BINDING_REQUIRES_RELEVANCE_POLICY"
    assert out["policy_influence_fast_path_pass"] is False


def test_failed_explicit_weights_never_fall_through():
    with tempfile.TemporaryDirectory() as td:
        root = pathlib.Path(td)
        p = make_payload(root, max_items=2)
        p["objective_weights"] = {"A": 1}
        out = evaluate(p, repo_root=root)
        assert out["pass"] is False
        assert out["policy_influence_fast_path_pass"] is False
        assert out["reason"] == "OBJECTIVE_WEIGHTS_UNSATISFIED"


def test_policy_influence_route_does_not_swallow_conflict_failure():
    with tempfile.TemporaryDirectory() as td:
        root = pathlib.Path(td)
        p = make_payload(root, max_items=2)
        p["v3_input"]["task"]["evidence"].append({
            "evidence_id": "E4",
            "text": "Report states Margin rate is 9.",
            "verified": True,
            "provenance": [{"source_id": "E4", "locator": "p"}],
        })
        out = evaluate(p, repo_root=root)
        assert out["pass"] is False
        assert out["policy_influence_not_applicable_reason"] == "V9_DID_NOT_REACH_CAPACITY_BINDING_RELEVANCE_FRONTIER"


def test_invalid_policy_influence_contract_fails_closed():
    with tempfile.TemporaryDirectory() as td:
        root = pathlib.Path(td)
        p = make_payload(root, max_items=2)
        p["policy_influence_contract"]["current_discriminator_values"]["E"] = "X0"
        out = evaluate(p, repo_root=root)
        assert out["pass"] is False
        assert out["reason"] == "POLICY_INFLUENCE_CONTRACT_UNSATISFIED"
        assert out["detail"]["policy_influence_result"]["reason"] == "POLICY_INFLUENCE_CONTRACT_DIGEST_MISMATCH"


def test_v10_positive_route_keeps_all_outer_authority_zero():
    with tempfile.TemporaryDirectory() as td:
        root = pathlib.Path(td)
        out = evaluate(make_payload(root, max_items=2), repo_root=root)
        assert out["pass"] is True, out
        assert out["top_law_eligible"] is False
        for field in (
            "source_authorization_verified",
            "policy_adequacy_authority",
            "db_admission_authority",
            "u_subtraction_authority",
            "terminal_authority",
        ):
            assert out[field] is False
        assert out["terminal_credit_delta"] == 0
