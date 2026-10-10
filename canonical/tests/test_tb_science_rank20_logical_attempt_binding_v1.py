from canonical.runtime.tb_science_rank20_logical_attempt_binding_v1 import (
    EXECUTION_CLAIM_BINDING_DIGEST,
    EXPECTED_LOGICAL_ATTEMPT_ID,
    execution_claim_binding_digest,
    logical_attempt_id,
    verify,
)


def test_rank20_claim_binding_and_v2_identity_are_exact():
    assert EXECUTION_CLAIM_BINDING_DIGEST == "sha256:426dd1c0cc9b21b35b793f2c5154e62eb74fb05cafa2c7e344843d93fbd367a3"
    assert EXPECTED_LOGICAL_ATTEMPT_ID == "62741de107152d9dba8d890d0294ed4c1d7d07a080c7a4d158231b10d98b052d"
    assert execution_claim_binding_digest() == EXECUTION_CLAIM_BINDING_DIGEST
    assert logical_attempt_id() == EXPECTED_LOGICAL_ATTEMPT_ID
    out = verify()
    assert out["pass"] is True, out
    assert out["task_read"] is False
    assert out["task_started"] is False
    assert out["benchmark_trials_consumed"] == 0
    assert out["execution_authority"] is False
    assert out["terminal_credit_delta"] == 0
