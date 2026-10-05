from canonical.runtime.h100_unichart_storage_feasibility_v1 import (
    H100_BUDGET_BYTES,
    CHECKPOINT_BYTES,
    ANCILLARY_BYTES,
    compute_bound,
    audit,
)


def test_bound_matches_frozen_arithmetic():
    b=compute_bound()
    assert b.checkpoint_bytes == 809_199_995
    assert b.max_fp32_values_from_file_size == 202_299_998
    assert b.packed_weight_bytes == 75_862_500
    assert b.quant_metadata_bytes == 3_160_940
    assert b.ancillary_bytes == 5_317_996
    assert b.total_bytes == 84_341_436
    assert b.margin_bytes == 15_658_564
    assert b.total_bytes < H100_BUDGET_BYTES


def test_candidate_is_strictly_zero_credit():
    out=audit()
    assert out["status"]=="CONDITIONAL_STORAGE_FEASIBILITY_PASS"
    assert out["h100_credit_delta"]==0
    assert out["execution_authority"] is False
    assert out["promotion_authority"] is False
    assert "NO_CLAIM_W3_PRESERVES_UNICHART_CAPABILITY" in out["hard_nonclaims"]
