from canonical.runtime.p3_binary_top_law_policy_adequacy_verifier_v1 import (
    CONDITION,
    POLICY_ID,
    verify,
)


def test_repository_normalization_verifies():
    out = verify()
    assert out["pass"] is True, out
    assert out["policy_id"] == POLICY_ID
    assert out["policy_condition"] == CONDITION
    assert out["brain_owned"] is True
    assert out["load_bearing_constraints_preserved"] is True


def test_normalization_preserves_scope_boundary():
    out = verify()
    assert out["whole_p3_closed"] is False
    assert out["u_empty"] is False
    assert out["root_task_authority_self_proved"] is False
    assert out["terminal_authority"] is False
    assert out["terminal_credit_delta"] == 0
