from canonical.runtime.tb_science_rank20_logical_attempt_binding_v1 import (
    EXECUTION_CLAIM_BINDING_DIGEST,
    EXPECTED_LOGICAL_ATTEMPT_ID,
    execution_claim_binding_digest,
    logical_attempt_id,
    verify,
)


def test_rank20_claim_binding_and_v2_identity_are_exact():
    assert EXECUTION_CLAIM_BINDING_DIGEST == "sha256:0d61d00d8b5dfd829397c801428f2c287d05deeb0fab318e6a0377b10d851b63"
    assert EXPECTED_LOGICAL_ATTEMPT_ID == "205b4f35a594b98d3d307ff077e510dbe94ba9e8ceb5c41b869af50042a99e8c"
    assert execution_claim_binding_digest() == EXECUTION_CLAIM_BINDING_DIGEST
    assert logical_attempt_id() == EXPECTED_LOGICAL_ATTEMPT_ID
    out = verify()
    assert out["pass"] is True, out
    assert out["task_read"] is False
    assert out["task_started"] is False
    assert out["benchmark_trials_consumed"] == 0
    assert out["execution_authority"] is False
    assert out["terminal_credit_delta"] == 0
