import pytest
from canonical.runtime.gdpval_crowdbt_direct_sign_bridge_v1 import (
    CrowdBTSignBridgeError,
    certify,
)

R = [{"path": "canonical/evidence/x.json", "git_blob_sha": "a" * 40}]


def payload(judges):
    return {
        "crowd_bt_semantic_receipts": R,
        "direct_attachment_graph_receipts": R,
        "mle_objective_receipts": R,
        "judges": judges,
    }


def test_allows_losses_when_each_judge_aggregate_is_noninferior():
    out = certify(payload([
        {"id": "j1", "brain_wins": 7, "opus_wins": 5, "ties": 2, "eta_lower": "3/5"},
        {"id": "j2", "brain_wins": 6, "opus_wins": 6, "ties": 4, "eta_lower": "1/2"},
        {"id": "j3", "brain_wins": 9, "opus_wins": 8, "ties": 0, "eta_lower": "51/100"},
    ]))
    assert out["status"] == "PASS__CONDITIONAL_DIRECT_CROWDBT_NONINFERIORITY"
    assert out["conditional_brain_minus_opus_mle_nonnegative"] is True


def test_ties_are_half_wins_each_and_cancel_in_sign_check():
    out = certify(payload([
        {"id": "j1", "brain_wins": 3, "opus_wins": 3, "ties": 100, "eta_lower": "2/3"},
    ]))
    assert out["status"] == "PASS__CONDITIONAL_DIRECT_CROWDBT_NONINFERIORITY"
    row = out["judges"][0]
    assert row["brain_effective_wins_x2"] == row["opus_effective_wins_x2"]


def test_one_judge_aggregate_opus_majority_blocks_robust_sign_certificate():
    out = certify(payload([
        {"id": "j1", "brain_wins": 10, "opus_wins": 0, "ties": 0, "eta_lower": "3/4"},
        {"id": "j2", "brain_wins": 4, "opus_wins": 5, "ties": 20, "eta_lower": "3/4"},
    ]))
    assert out["status"] == "UNKNOWN__PREMISES_INSUFFICIENT"
    assert "AT_LEAST_ONE_JUDGE_HAS_MORE_EFFECTIVE_OPUS_WINS_THAN_BRAIN_WINS" in out["blockers"]


def test_eta_may_equal_half_for_some_judges_if_another_is_strictly_informative():
    out = certify(payload([
        {"id": "uninformative_possible", "brain_wins": 4, "opus_wins": 4, "ties": 1, "eta_lower": "1/2"},
        {"id": "informative", "brain_wins": 4, "opus_wins": 4, "ties": 1, "eta_lower": "5001/10000"},
    ]))
    assert out["conditional_brain_minus_opus_mle_nonnegative"] is True


def test_all_eta_only_known_ge_half_is_insufficient_for_identified_mle_sign():
    out = certify(payload([
        {"id": "j1", "brain_wins": 5, "opus_wins": 5, "ties": 5, "eta_lower": "1/2"},
        {"id": "j2", "brain_wins": 8, "opus_wins": 3, "ties": 0, "eta_lower": "1/2"},
    ]))
    assert out["status"] == "UNKNOWN__PREMISES_INSUFFICIENT"
    assert "NO_JUDGE_IS_PROVED_STRICTLY_INFORMATIVE_ABOVE_ETA_HALF" in out["blockers"]


def test_eta_below_half_rejected():
    with pytest.raises(CrowdBTSignBridgeError):
        certify(payload([
            {"id": "bad", "brain_wins": 10, "opus_wins": 0, "ties": 0, "eta_lower": "49/100"},
        ]))


def test_receipts_are_required_and_do_not_self_certify_semantics():
    out = certify(payload([
        {"id": "j", "brain_wins": 1, "opus_wins": 0, "ties": 0, "eta_lower": "3/4"},
    ]))
    assert out["semantic_premises_verified_by_this_runtime"] is False
    assert out["owner_exact_reproduction"] is False
    assert out["terminal_authority"] is False
    assert out["terminal_credit_delta"] == 0
