from canonical.runtime.tb_science_rank8_authority_v3_verifier import verify


def test_rank8_v3_authority_is_bound_to_current_v5_truth():
    out = verify()
    assert out["pass"], out["errors"]
    assert out["slot"] == "terminal-bench-science/linked-cell-suppression::trial-0"
    assert out["rank"] == 8
    assert out["current_consumed_slots"] == 7
    assert out["execution_authority"] is True


def test_rank8_v3_is_one_shot_zero_spend_and_epoch_gated():
    out = verify()
    assert out["fresh_reality_units_authorized"] == 1
    assert out["incremental_spend_usd_max"] == 0
    assert out["public_epoch_blob_required"] == "f95f513b0ad57b8b3398fcabba44beae6fd805f4"
    assert out["public_epoch_id_required"] == "TBSCI-RANK8-20261007-E3"
    assert out["acceptance_credit_delta"] == 0
    assert out["terminal_credit_delta"] == 0
