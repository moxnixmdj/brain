from canonical.runtime.gdpval_matched_epoch_receipt_gate_v1 import (
    BENCHMARK_ID,
    FROZEN_BAR,
    OWNER_ID,
    PREDICATE_ID,
    TARGET_MODEL_ID,
    verify,
)

H = "a" * 64
J = "b" * 64


def base(route):
    return {
        "predicate_id": PREDICATE_ID,
        "benchmark_id": BENCHMARK_ID,
        "score_owner": OWNER_ID,
        "task_count": 220,
        "frozen_before_brain_scoring": True,
        "harness_valid": True,
        "scoring_protocol_valid": True,
        "same_task_population": True,
        "brain_subject_sha256": H,
        "task_population_sha256": H,
        "harness_manifest_sha256": H,
        "submission_manifest_sha256": H,
        "score_receipt_sha256": H,
        "independent_verification_sha256": J,
        "route": route,
    }


def test_historical_exact_bar_passes():
    r = base("MATCHED_HISTORICAL_FIXED_BAR")
    r.update({
        "brain_score": FROZEN_BAR,
        "historical_bar": FROZEN_BAR,
        "brain_epoch_id": "AA_GDPVAL_V21_2026_09_22",
        "target_epoch_id": "AA_GDPVAL_V21_2026_09_22",
        "same_harness_as_target_epoch": True,
        "target_comparator_receipt_sha256": H,
        "epoch_equivalence_receipt_sha256": J,
    })
    out = verify(r)
    assert out["pass"] is True
    assert out["row_acceptance_ready"] is True
    assert out["acceptance_authority"] is False
    assert out["acceptance_credit_delta"] == 0


def test_historical_cross_epoch_fails():
    r = base("MATCHED_HISTORICAL_FIXED_BAR")
    r.update({
        "brain_score": 2000,
        "historical_bar": FROZEN_BAR,
        "brain_epoch_id": "NEW",
        "target_epoch_id": "OLD",
        "same_harness_as_target_epoch": True,
        "target_comparator_receipt_sha256": H,
        "epoch_equivalence_receipt_sha256": J,
    })
    out = verify(r)
    assert out["pass"] is False
    assert out["reason"] == "HISTORICAL_EPOCH_NOT_MATCHED"


def test_historical_below_bar_fails():
    r = base("MATCHED_HISTORICAL_FIXED_BAR")
    r.update({
        "brain_score": 1845.99,
        "historical_bar": FROZEN_BAR,
        "brain_epoch_id": "E",
        "target_epoch_id": "E",
        "same_harness_as_target_epoch": True,
        "target_comparator_receipt_sha256": H,
        "epoch_equivalence_receipt_sha256": J,
    })
    out = verify(r)
    assert out["pass"] is False
    assert out["reason"] == "BRAIN_SCORE_BELOW_FROZEN_BAR"


def test_same_fit_stronger_route_passes():
    r = base("SAME_FIT_OPUS55_NONINFERIORITY")
    r.update({
        "brain_score": 1900,
        "comparator_model_id": TARGET_MODEL_ID,
        "same_fit": True,
        "same_harness_as_comparator": True,
        "brain_fit_id": "CURRENT_FIT_X",
        "comparator_fit_id": "CURRENT_FIT_X",
        "comparator_score": 1866,
        "comparator_score_receipt_sha256": J,
    })
    out = verify(r)
    assert out["pass"] is True
    assert out["route"] == "SAME_FIT_OPUS55_NONINFERIORITY"


def test_same_fit_comparator_below_1846_does_not_bridge():
    r = base("SAME_FIT_OPUS55_NONINFERIORITY")
    r.update({
        "brain_score": 1900,
        "comparator_model_id": TARGET_MODEL_ID,
        "same_fit": True,
        "same_harness_as_comparator": True,
        "brain_fit_id": "X",
        "comparator_fit_id": "X",
        "comparator_score": 1830,
        "comparator_score_receipt_sha256": J,
    })
    out = verify(r)
    assert out["pass"] is False
    assert out["reason"] == "SAME_FIT_COMPARATOR_DOES_NOT_DOMINATE_FROZEN_BAR"


def test_same_fit_brain_below_opus_fails():
    r = base("SAME_FIT_OPUS55_NONINFERIORITY")
    r.update({
        "brain_score": 1860,
        "comparator_model_id": TARGET_MODEL_ID,
        "same_fit": True,
        "same_harness_as_comparator": True,
        "brain_fit_id": "X",
        "comparator_fit_id": "X",
        "comparator_score": 1866,
        "comparator_score_receipt_sha256": J,
    })
    out = verify(r)
    assert out["pass"] is False
    assert out["reason"] == "BRAIN_INFERIOR_TO_OPUS_IN_SAME_FIT"


def test_third_party_score_owner_fails():
    r = base("MATCHED_HISTORICAL_FIXED_BAR")
    r["score_owner"] = "THIRD_PARTY"
    out = verify(r)
    assert out["pass"] is False
    assert out["reason"] == "SCORE_OWNER_NOT_ARTIFICIAL_ANALYSIS"


def test_missing_content_address_fails():
    r = base("MATCHED_HISTORICAL_FIXED_BAR")
    r["submission_manifest_sha256"] = None
    out = verify(r)
    assert out["pass"] is False
    assert out["reason"] == "CONTENT_ADDRESS_MISSING_OR_INVALID"
