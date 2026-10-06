from __future__ import annotations

from canonical.runtime.honesty_load_bearing_bypass_verifier_v1 import evaluate


def test_current_runtime_has_constructive_bypass_and_zero_credit():
    out = evaluate()
    assert out["pass"] is True, out
    assert out["current_honesty_mediation_totality_falsified"] is True
    assert out["shared_effect_escape_localized"] is True
    assert out["repair_implemented"] is False
    assert out["ledger_completeness_proved"] is False
    assert out["effect_boundary_closed"] is False
    assert out["execution_authority"] is False
    assert out["acceptance_credit_delta"] == 0


if __name__ == "__main__":
    test_current_runtime_has_constructive_bypass_and_zero_credit()
    print("PASS 1/1")
