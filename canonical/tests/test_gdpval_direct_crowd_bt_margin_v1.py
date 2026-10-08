import pytest

from canonical.runtime.gdpval_direct_crowd_bt_margin_v1 import (
    DirectCrowdBTError,
    certify,
)


def receipt(tag):
    return {"path": f"proof/{tag}.json", "git_blob_sha": "a" * 40}


def test_allows_losses_when_each_judge_margin_nonnegative():
    out = certify({"judges": [
        {"id": "j1", "wins": 80, "ties": 20, "losses": 70,
         "expected_comparisons": 170, "quality_gt_half_receipt": receipt("j1")},
        {"id": "j2", "wins": 10, "ties": 2, "losses": 10,
         "expected_comparisons": 22, "quality_gt_half_receipt": receipt("j2")},
        {"id": "j3", "wins": 15, "ties": 3, "losses": 10,
         "expected_comparisons": 28, "quality_gt_half_receipt": receipt("j3")},
    ]})
    assert out["status"] == "PASS__DIRECT_CROWD_BT_NONINFERIOR"
    assert out["conditional_noninferiority"] is True
    assert out["strict_positive_direction"] is True


def test_equal_wins_losses_certifies_weak_noninferiority():
    out = certify({"judges": [
        {"id": "j", "wins": 5, "ties": 7, "losses": 5,
         "quality_gt_half_receipt": receipt("j")},
    ]})
    assert out["conditional_noninferiority"] is True
    assert out["strict_positive_direction"] is False


def test_one_negative_judge_margin_fails_closed():
    out = certify({"judges": [
        {"id": "j1", "wins": 6, "ties": 0, "losses": 5,
         "quality_gt_half_receipt": receipt("j1")},
        {"id": "j2", "wins": 4, "ties": 9, "losses": 5,
         "quality_gt_half_receipt": receipt("j2")},
    ]})
    assert out["status"] == "FAIL_CLOSED__PER_JUDGE_MARGIN_NEGATIVE"
    assert out["conditional_noninferiority"] is False


def test_requires_quality_orientation_receipt():
    with pytest.raises(DirectCrowdBTError):
        certify({"judges": [{"id": "j", "wins": 1, "ties": 0, "losses": 0}]})


def test_count_mismatch_rejected():
    with pytest.raises(DirectCrowdBTError):
        certify({"judges": [
            {"id": "j", "wins": 1, "ties": 1, "losses": 0,
             "expected_comparisons": 3, "quality_gt_half_receipt": receipt("j")}
        ]})


def test_no_terminal_authority():
    out = certify({"judges": [
        {"id": "j", "wins": 1, "ties": 0, "losses": 0,
         "quality_gt_half_receipt": receipt("j")}
    ]})
    assert out["terminal_authority"] is False
    assert out["promotion_authority"] is False
    assert out["terminal_credit_delta"] == 0
